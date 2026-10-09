"""E2: der taegliche Alarmlauf.

Ablauf je Ort:
  1. Fanpunkte fuer jeden Vorlaufabend aus dem Sonnenuntergangsazimut.
  2. Pass 1 - Bewoelkung und Wind an den Fanpunkten, native 3-h-Schritte.
  3. Advektionsversatz je Schicht und Abend aus dem Ensemble-MITTELwind.
  4. Pass 2 - Bewoelkung an den versetzten Punkten.
  5. Score je Member, p = Anteil der Member ueber s*.
  6. Push, falls p >= p* und dieser Abend noch nicht gemeldet wurde.

ENTSCHEIDUNGEN, bewusst getroffen:

* Betriebsscore ist die 3-SCHICHT-Variante, nicht die niveauaufgeloeste.
  Grund: s* = 0.7065 ist auf der 3-Schicht-Klimatologie kalibriert.  Ein
  Betrieb auf der anderen Variante haette einen Schwellwert, der nicht zu
  ihm gehoert.  Wechsel erst, wenn die Ablation (T-0006) zeigt, dass die
  Rangfolgen zusammenfallen.

* Advektion mit dem Ensemble-MITTELwind je Schicht, nicht je Member.  Pro
  Member waeren es 40 Punkte x 3 Schichten x 51 Member x 10 Abende = 61 200
  Abfragepositionen; mit Mittelwind sind es 1 200 vor Dedup.  Preis: die
  Streuung der Verlagerung zwischen Membern (auf 300 hPa etwa +/- 30 km bei
  1.5 h) geht verloren, die Verlagerung selbst (rund 160 km) nicht.  Der
  zweitbeste Weg, aber um Groessenordnungen billiger als der beste.

* Der Score wird PRO MEMBER gerechnet, nie aus Mittelfeldern.  S ist ein
  Produkt nichtlinearer Terme; der Score des Mittelfelds ist nicht der
  Mittelwert der Scores (Jensen).

* Idempotenz ueber die Zustandsdatei: je (Ort, Abend) hoechstens ein Alarm.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from datetime import time as dtzeit
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import sonnenuntergang, zielpunkt  # noqa: E402
import sonnen.score as sc  # noqa: E402
from sonnen.score import score  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netz import warte_auf_netz  # noqa: E402
from zustandsdatei import aktualisiere, schreibe  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITTER = 0.25
SCHICHTEN = ("low", "mid", "high")
# Repraesentatives Windniveau je Schicht (Schichtmitte)
WINDNIVEAU = {"low": 925, "mid": 600, "high": 300}
NTFY = "https://ntfy.sh"
WOCHENTAG = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


def fan_setzen(kfg):
    """Der Sparfaecher ist abgeschafft - hier bleibt nur der Riegel.

    ENTFERNT 23.08.2026 (T-0057).  Die Funktion hat frueher `sc.FAECHER_AZIMUTE`
    und `sc.DISTANZEN_KM` im Modul `sonnen.score` UEBERSCHRIEBEN.  Zwoelf
    Module importieren diese Konstanten aber by value (`from sonnen.score
    import DISTANZEN_KM, ...`), sehen die Aenderung also nie.  Vorgefuehrt:
    nach einem `fan_setzen` rechnete `sonnen.score` auf dem Sparfaecher,
    waehrend `sonnen.score_niveaus`, `skripte.schnitt` und `skripte.fensterterm`
    weiter die Originalgeometrie hielten - Analyse und Bild in einem Prozess
    auf verschiedenen Faechern, ohne dass irgendetwas auffaellt.

    WARUM STREICHEN STATT REPARIEREN.  Der saubere Weg waere, die Geometrie
    als Parameter durch `score()` zu reichen.  `score()` liest die beiden
    Konstanten an dreizehn Stellen; das ist ein Umbau der Kernfunktion des
    Betriebsscores - fuer einen Hebel, der in `konfig.json` auf `null` steht,
    nie benutzt wurde, und der ausserdem s* = 0.7065 ungueltig macht: dieser
    Schwellwert gilt fuer den Faecher der Klimatologie (5 Azimute, 8
    Distanzen).  Eine Konfiguration, die den Schwellwert ungueltig macht und
    davor nur warnt, ist keine Konfiguration.

    Wer den Sparfaecher wirklich braucht, rechnet zuerst die Klimatologie mit
    demselben Faecher neu und leitet s* daraus her - dann ist die Geometrie
    ohnehin die neue Normalgeometrie und gehoert in `sonnen/score.py`, nicht
    in eine Laufzeitmutation.
    """
    if kfg.get("faecher"):
        raise SystemExit(
            "konfig.json enthaelt `faecher` - der Sparfaecher ist seit dem\n"
            "23.08.2026 abgeschafft (T-0057).  Er hat nur `sonnen.score`\n"
            "veraendert, nicht die zwoelf Module, die dieselben Konstanten\n"
            "by value importieren - Analyse und Bild liefen danach auf\n"
            "verschiedenen Faechern.  Ausserdem macht ein anderer Faecher\n"
            "s* = 0.7065 ungueltig.\n"
            "Wer wirklich einen anderen Faecher will: `sonnen/score.py`\n"
            "aendern UND die Klimatologie damit neu rechnen.")
    return False


def zelle(lat, lon):
    return (round(lat / GITTER), round(lon / GITTER))


def mitte(z):
    return (z[0] * GITTER, z[1] * GITTER)


# --- Buchhaltung ueber die API-Last ------------------------------------
#
# WARUM (18.08.2026).  Zwei von vier planmaessigen Laeufen sind am
# Kontingent gescheitert, und der Log konnte nicht sagen warum: er hatte
# keine Uhrzeit und keine Zahl darueber, wie viel ein Lauf ueberhaupt
# anfordert.  Damit war jede Erklaerung eine Vermutung.  Ab jetzt schreibt
# jeder Lauf mit, wann er was geholt hat - die naechsten Laeufe sind dann
# Messungen statt Anekdoten.
#
# WAS DAS KONTINGENT ZAEHLT, IST NICHT GEKLAERT (korrigiert 09.10.2026,
# Review alarm#3/#4).  Hier stand "nach Variablen und Zeitraum, nicht nach
# Orten" - das widersprach dem Kommentar in lauf_ort() (Member zaehlen wie
# Variablen) und dem Log.  Gemessen ist: das Log stuetzt meist eine
# Gewichtung mit Variablen x Member je Ort (3 x 51 / 10 = 15,3 Einheiten je
# Ortsabruf), aber nicht ausnahmslos.  Kein additives Modell aus dem eigenen
# Verbrauch erklaert alle Abbrueche: am 21.09.2026 scheiterte der erste Lauf
# des Tages nach hoechstens 329 Ortsabrufen, am 08.10.2026 liefen
# 378 und 383 Ortsabrufe je in einer Uhrstunde und zusammen an EINEM UTC-Tag
# durch (nach dem 15,3-Gewicht 11.600 Einheiten bei 10.000 am Tag).  Gardena
# fragt vom selben Rechner stuendlich dieselbe API ab.  LAST ist deshalb die
# Buchhaltung UNSERER Abrufe, keine Nachbildung ihrer Formel: gut zum
# Vergleichen von Laeufen, nicht zum Vorhersagen des Limits.
LAST = {"anfragen": 0, "orte": 0, "variablen": 0, "member": 0, "tage": 0,
        "aus_cache": 0}


def schreibe_archiv(name, tag, fenster, init, jetzt, kfg, abende):
    """Den Tagesabzug wegschreiben - ohne einen einzigen zusaetzlichen Abruf.

    T-0003, NEUFASSUNG 20.08.2026.  Die erste Fassung (`skripte/archiviere.py`)
    hat die Felder ein ZWEITES Mal geholt: 76 Zellen x 43 Variablen x 51
    Member x 11 Tage.  Sie hat nie funktioniert - Open-Meteo antwortete
    durchgehend mit

        HTTP 400: "Your API call requests too much data."

    und nachgerechnet waren es 16.720 Kontingenteinheiten am Tag, bei einem
    Tagesbudget von 10.000.  Der Fehler war nicht die Blockgroesse, sondern
    der zweite Abruf: der Alarmlauf HAT die Daten schon.

    Archiviert wird deshalb, was er ohnehin gerechnet hat - je Abend die
    Scorezeile jedes Members (fuer Rangdiagramm und Skill, T-0008) und das
    Medianfeld (fuer Bilder im Nachhinein).  Nicht archiviert werden die
    Rohfelder je Member: das waeren ueber ein Gigabyte im Jahr, und
    gebraucht wuerden sie nur, um die Score-Formel rueckwirkend zu aendern.
    Entscheidung Andres am 20.08.2026.
    """
    ordner = os.path.join(BASIS, "daten", "archiv", name)
    os.makedirs(ordner, exist_ok=True)
    ziel = os.path.join(ordner, "%s_%s.json" % (tag, fenster))
    d = {"ort": name, "lauf": str(tag), "fenster": fenster,
         "modelllauf": init, "geholt": jetzt.isoformat(timespec="minutes"),
         "modell": kfg["modell"], "schwelle_score": kfg["schwelle_score"],
         "abende": abende}
    # T-0051: atomar wie die Zustandsdatei.  Ein truncierter Archivtag legt
    # zwar keinen Agenten lahm, ist aber stiller Datenverlust im Bestand,
    # aus dem T-0008 (Skill ueber Vorlauf) spaeter rechnen soll - und faellt
    # erst auf, wenn Monate spaeter jemand darueber laeuft.
    schreibe(ziel, d, indent=None, separators=(",", ":"))
    return ziel, os.path.getsize(ziel)


def modelllauf(modell):
    """Initialisierungszeit des juengsten verfuegbaren Modelllaufs, oder None.

    Kommt aus einer STATISCHEN Datei und zaehlt nicht aufs Kontingent.  Sie
    ist die einzige ehrliche Antwort auf "von wann sind die Wetterdaten":
    unser Abrufzeitpunkt sagt nur, wann WIR geholt haben - der Modelllauf
    sagt, worauf die Zahlen beruhen.  Zwischen beiden liegen 8,7 Stunden
    (gemessen 18.08.2026).
    """
    u = ("https://api.open-meteo.com/data/%s_ensemble/static/meta.json"
         % modell)
    try:
        with urllib.request.urlopen(u, timeout=30) as f:
            d = json.load(f)
        return datetime.fromtimestamp(d["last_run_initialisation_time"],
                                      timezone.utc).isoformat(timespec="minutes")
    except Exception:                                            # noqa: BLE001
        return None                     # kein Grund, den Lauf daran zu haengen


def uhr():
    return datetime.now().strftime("%H:%M:%S")


def melde(text):
    print("%s %s" % (uhr(), text), flush=True)


# Wartezeiten fuer VORUEBERGEHENDE Stoerungen (T-0069).  Kurz genug, dass
# ein Abendlauf sie sich leisten kann, lang genug, dass ein WLAN nach dem
# Aufwachen zurueckkommt.
RUHEPAUSEN = (5, 15, 45)
# Wie oft _hole() je Anfrage ein Minutenlimit oder "Too many concurrent
# requests" abwartet.  EIGENES Budget, nicht die Versuche fuer Netzstoerungen
# (Review 09.10.2026, alarm#10): vorher teilten sich beide die vier Versuche,
# und ein Minutenlimit im vierten Versuch endete als "Kontingent".
MINUTENWARTEN = 5


# --- Kontingentsperre (T-0074) -----------------------------------------
#
# WARUM (09.10.2026, Review alarm#1).  Nach "Hourly/Daily API request limit
# exceeded" bot im_laufenster() den Abendlauf bei jedem stuendlichen Tick bis
# Sonnenuntergang erneut an, und jeder Versuch begann wieder bei Pass 1.  Seit
# 16.09. stehen 41 Kontingentabbrueche im Log, davon 29 volle Fehllaeufe mit
# zusammen 10.175 Ortsabrufen.  Jetzt merkt sich der Lauf, bis wann die Wand
# steht, und die Ticks davor beenden sich ohne einen einzigen Abruf.
SPERRSCHLUESSEL = "_kontingent"       # Eintrag in daten/zustand.json


class Kontingent(SystemExit):
    """Abbruch am Kontingent.  `sperre_bis` ist None, wenn keine Sperre folgt.

    Unterklasse von SystemExit, damit sich fuer jeden bisherigen Aufrufer
    nichts aendert: der Lauf endet weiter mit der Meldung als Exitgrund.
    """

    def __init__(self, text, sperre_bis=None, grund=None):
        super().__init__(text)
        self.sperre_bis = sperre_bis
        self.grund = grund


def _jetzt_utc():
    """Die echte Uhr - eigene Funktion, damit ein Test sie stellen kann."""
    return datetime.now(timezone.utc)


def sperre_bis(grund, jetzt):
    """Bis wann nach diesem 429-Grund kein Abruf lohnt, oder None.

    Stundenlimit: volle naechste UTC-Stunde + 2 min.  Tageslimit: 00:02 UTC
    des Folgetags.  Die zwei Minuten sind Abstand zur Uhr der Gegenseite.
    Der stuendliche Agent tickt um :20 - eine Sperre bis :02 kostet also nie
    den naechsten Tick.  Alles andere (Minute, Gleichzeitigkeit, unbekannt)
    bekommt keine Sperre.
    """
    g = (grund or "").lower()
    if "hourly" in g:
        return (jetzt.replace(minute=0, second=0, microsecond=0)
                + timedelta(hours=1, minutes=2))
    if "daily" in g:
        return datetime.combine(jetzt.date() + timedelta(days=1),
                                dtzeit(0, 2), timezone.utc)
    return None


def aktive_sperre(zustand, jetzt):
    """(bis, grund), solange eine vermerkte Sperre noch gilt, sonst None.

    Ein unlesbarer Eintrag zaehlt als KEINE Sperre: das Schlimmste, was dann
    passiert, ist ein Abruf, der am 429 endet - mit dem Blockcache eine
    einzige Anfrage.  Andersherum wuerde ein kaputter Eintrag den Alarm
    stilllegen, und das faellt niemandem auf.
    """
    e = (zustand or {}).get(SPERRSCHLUESSEL)
    if not isinstance(e, dict):
        return None
    try:
        bis = datetime.fromisoformat(e["sperre_bis"])
    except (KeyError, TypeError, ValueError):
        return None
    if bis.tzinfo is None:
        bis = bis.replace(tzinfo=timezone.utc)
    return (bis, e.get("grund")) if bis > jetzt else None


def vermerke_sperre(zpfad, bis, grund):
    """Die Sperre unter Sperre in den FRISCHEN Zustand schreiben (T-0058).

    Auch bei --trocken: das Limit ist echt, egal ob der Lauf senden wollte.
    Eine spaetere Sperre wird nie durch eine fruehere ersetzt (Tageslimit
    vermerkt, dann meldet ein Handlauf das Stundenlimit).
    """
    def eintragen(z):
        if aktive_sperre(z, bis):
            return                     # eine spaetere Sperre steht schon
        z[SPERRSCHLUESSEL] = {
            "sperre_bis": bis.isoformat(timespec="minutes"),
            "grund": grund,
            "vermerkt": _jetzt_utc().isoformat(timespec="seconds")}
    aktualisiere(zpfad, eintragen)


def _hole(u, versuche=4):
    LAST["anfragen"] += 1
    n = 0                    # gestoerte Versuche (Netz, 5xx)
    gewartet = 0             # abgewartete Minuten-/Gleichzeitigkeitslimits
    while True:
        try:
            with urllib.request.urlopen(u, timeout=600) as f:
                return json.load(f)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                # Der Rumpf ist die einzige Stelle, an der steht, WELCHES der
                # drei 429 gemeint ist.  Fehlt er oder ist er kein JSON, darf
                # das nicht den Abbruch ERSETZEN - vorher warf json.loads hier
                # einen JSONDecodeError statt der gemeinten Meldung.
                try:
                    grund = json.loads(e.read()).get("reason", "429")
                except Exception:                            # noqa: BLE001
                    grund = "429 ohne lesbaren Grund"
                # Minutenlimit und "Too many concurrent requests" sind
                # voruebergehend: warten, mit eigenem Budget (alarm#10).
                # Vorher brach "concurrent" sofort ab, obwohl die README
                # dafuer "kurz warten" nennt.
                kurz = "oncurrent" in grund
                if ("inutely" in grund or kurz) and gewartet < MINUTENWARTEN:
                    gewartet += 1
                    warte = RUHEPAUSEN[0] if kurz else 65
                    melde("   %s, warte %d s ... (Anfrage %d)"
                          % ("Zu viele gleichzeitig" if kurz else "Minutenlimit",
                             warte, LAST["anfragen"]))
                    time.sleep(warte)
                    continue
                raise Kontingent("%s Kontingent nach %d Anfragen "
                                 "(%d Ortsabrufe, %d Variablen, %d Tage): %s"
                                 % (uhr(), LAST["anfragen"], LAST["orte"],
                                    LAST["variablen"], LAST["tage"], grund),
                                 sperre_bis(grund, _jetzt_utc()), grund)
            # 5xx ist die Gegenseite, nicht wir: das lohnt einen zweiten
            # Versuch.  4xx ist unsere Anfrage und wird beim Wiederholen
            # nicht besser - durchreichen, damit es auffaellt.
            if e.code < 500 or n >= versuche - 1:
                raise
            fehler = "HTTP %d" % e.code
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            # T-0069.  Bis zum 02.09.2026 stand hier nur der 429-Zweig, alles
            # andere riss den Lauf mit Traceback ab: ein abgebrochener
            # Verbindungsaufbau, ein Timeout, eine halbe Antwort.  Der
            # Abendlauf wird dann zwar vom naechsten stuendlichen Tick
            # nachgeholt, der Vormittagslauf aber nicht - und jeder
            # gescheiterte Versuch hat sein Kontingent schon verbraucht.
            # ValueError faengt die truncierte JSON-Antwort mit ab; sie ist
            # in der Praxis ein Netzabbruch, kein Formatfehler.
            if n >= versuche - 1:
                raise
            fehler = "%s: %s" % (type(e).__name__, e)
        warte = RUHEPAUSEN[min(n, len(RUHEPAUSEN) - 1)]
        n += 1
        melde("   Abruf gestoert (%s), neuer Versuch in %d s (Anfrage %d, "
              "Versuch %d von %d)" % (fehler, warte, LAST["anfragen"],
                                      n + 1, versuche))
        time.sleep(warte)


# --- Blockcache (T-0074) -----------------------------------------------
#
# WARUM (09.10.2026, Review alarm#1, tests#6).  abfrage() sammelte nur im
# Speicher.  Ein 429 oder Netzabbruch in Block 14 von 17 verwarf die 13
# geholten Bloecke, und der naechste Tick zahlte sie noch einmal.  Jetzt
# liegt jeder erfolgreich geholte Block als eigene Datei auf der Platte, und
# ein Wiederholungslauf holt nur, was fehlt.
#
# SCHLUESSEL IST DER MODELLLAUF, NICHT DER TAG.  Ein Tag hat bis zu vier
# Modelllaeufe; ein Cache je Tag lieferte einem Abendlauf auf dem 06z die
# Bloecke des Vormittagslaufs auf dem 18z des Vortags - still, und mit
# genau dem Verzug, den die Seite als Modelllauf ausweist.  Der Ordner traegt
# deshalb die Initialisierung aus modelllauf(), und die Datei den SHA-1 der
# vollstaendigen Anfrage-URL (Zellen, Variablen, Modell, Tage).
#
# DAZU DER UTC-ABRUFTAG (Gate 09.10.2026).  Die URL nennt forecast_days, aber
# kein Startdatum; die Zeitachse beginnt dann am Abruftag um 00:00 UTC.
# Derselbe Modelllauf an zwei UTC-Tagen (Handlauf um Mitternacht, Hourly-
# Sperre von 23:xx bis 00:02, Modelllauf mit mehr als 27 h Verzug) haette
# vor allem den Windblock aus dem Cache bekommen - seine URL haengt nur an
# der Heimatzelle - mit einer um 24 h verschobenen Zeitachse, und die
# Advektion waere still mit dem Wind des Vortags gerechnet worden.  Deshalb
# liegt unter dem Modelllauf je Abruftag ein Unterordner (_cache_pfad), und
# ein Block wird nur am Tag gelesen, an dem er geholt wurde.
#
# Ist der Modelllauf UNBEKANNT (meta.json nicht erreichbar), gibt es keinen
# Cache - weder lesen noch schreiben.  Lieber einmal voll bezahlen als Daten
# eines anderen Laufs unter falschem Namen rechnen.
#
# Bekannte Restluecke, nicht neu: modelllauf() wird VOR dem Abruf gelesen
# (T-0065).  Wird dazwischen ein neuer Lauf verfuegbar, landen seine Bloecke
# unter dem alten Namen.  Gelesen werden sie nur von einem Lauf, der denselben
# alten Namen sieht - also von einem, der ohnehin schon gemischt haette.
ABRUF_CACHE = {"init": None}          # setzt main(); None = kein Cache
CACHE_HALTEN_TAGE = 2


def _cache_ordner(init=None):
    """Cacheordner fuer diesen Modelllauf, oder None (kein Cache)."""
    init = init if init is not None else ABRUF_CACHE.get("init")
    if not init:
        return None
    try:
        t = datetime.fromisoformat(init)
    except (TypeError, ValueError):
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return os.path.join(BASIS, "daten", "cache", "abruf",
                        t.astimezone(timezone.utc).strftime("%Y%m%dT%H%MZ"))


def _cache_pfad(ordner, u):
    """Cachedatei fuer die Anfrage `u`: <Modelllauf>/<UTC-Abruftag>/<SHA-1>.

    Der Tag kommt von der echten Uhr, nicht aus --jetzt: die Zeitachse der
    Antwort richtet sich danach, WANN Open-Meteo gefragt wurde.
    """
    if not ordner:
        return None
    return os.path.join(ordner, _jetzt_utc().strftime("%Y%m%d"),
                        hashlib.sha1(u.encode()).hexdigest() + ".json")


def _aus_cache(pfad, n):
    """Den gespeicherten Block lesen; jede Unstimmigkeit ist ein Fehltreffer."""
    if not pfad or not os.path.exists(pfad):
        return None
    try:
        with open(pfad) as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if isinstance(d, dict):
        d = [d]
    if not isinstance(d, list) or len(d) != n \
            or not all(isinstance(e, dict) and "hourly" in e for e in d):
        return None
    return d


def raeume_cache(jetzt, halten_tage=CACHE_HALTEN_TAGE):
    """Cacheordner von Modelllaeufen, die aelter als `halten_tage` sind, loeschen.

    Das Alter kommt aus dem Ordnernamen (der Initialisierung); ein Name, der
    sich nicht lesen laesst, faellt auf die Aenderungszeit zurueck.  Ein
    Block wiegt rund 2 MB, ein voller Lauf rund 17 Bloecke.
    """
    wurzel = os.path.join(BASIS, "daten", "cache", "abruf")
    if not os.path.isdir(wurzel):
        return 0
    grenze = jetzt - timedelta(days=halten_tage)
    weg = 0
    for name in sorted(os.listdir(wurzel)):
        pfad = os.path.join(wurzel, name)
        if not os.path.isdir(pfad):
            continue
        try:
            t = datetime.strptime(name, "%Y%m%dT%H%MZ").replace(
                tzinfo=timezone.utc)
        except ValueError:
            t = datetime.fromtimestamp(os.path.getmtime(pfad), timezone.utc)
        if t < grenze:
            shutil.rmtree(pfad, ignore_errors=True)
            weg += 1
    return weg


def _hat_daten(d):
    """Steht in der Antwort `d` (Liste je Zelle) irgendein Wert ausser None?"""
    for e in d:
        for k, reihe in (e.get("hourly") or {}).items():
            if k != "time" and isinstance(reihe, list) \
                    and any(x is not None for x in reihe):
                return True
    return False


def abfrage(zellen, variablen, modell, tage, block=25):
    aus = {}
    liste = sorted(zellen)
    LAST["variablen"] = max(LAST["variablen"], len(variablen))
    LAST["tage"] = max(LAST["tage"], tage)
    ordner = _cache_ordner()
    melde("   Abruf: %d Zellen, %d Variablen, %d Tage, Bloecke zu %d"
          % (len(liste), len(variablen), tage, block))
    treffer = 0
    for i in range(0, len(liste), block):
        teil = liste[i:i + block]
        u = ("https://ensemble-api.open-meteo.com/v1/ensemble?latitude=%s&longitude=%s"
             "&models=%s&hourly=%s&forecast_days=%d&temporal_resolution=native"
             % (",".join("%.4f" % mitte(z)[0] for z in teil),
                ",".join("%.4f" % mitte(z)[1] for z in teil),
                modell, ",".join(variablen), tage))
        pfad = _cache_pfad(ordner, u)
        d = _aus_cache(pfad, len(teil))
        if d is not None:
            treffer += 1
            LAST["aus_cache"] += len(teil)
        else:
            LAST["orte"] += len(teil)
            d = _hole(u)
            if isinstance(d, dict):
                d = [d]
            if pfad and not _hat_daten(d):
                # T-0075: ein Block ohne einen einzigen Wert wird NICHT
                # gecacht.  Sonst laese der Nachhol-Tick dieselben Luecken
                # aus dem Cache und scheiterte bis zum naechsten Modelllauf
                # an ihnen, ohne Open-Meteo noch einmal zu fragen.
                melde("   Block ohne Daten - nicht gecacht")
            elif pfad:
                # Ein Cache, der nicht geschrieben werden kann, kostet beim
                # naechsten Abbruch Kontingent - aber nicht DIESEN Lauf.
                try:
                    schreibe(pfad, d, indent=None, separators=(",", ":"))
                except OSError as ex:
                    melde("   Blockcache nicht geschrieben (%s)" % ex)
            time.sleep(1)
        for z, e in zip(teil, d):
            aus[z] = e["hourly"]
    if treffer:
        melde("   davon %d Bloecke aus dem Cache (%s)"
              % (treffer, os.path.basename(ordner)))
    return aus


KONTROLLLAUF = ""      # der unstoerte Lauf: Schluessel OHNE _memberNN-Suffix


def feldname(basis, m):
    """Variablenname je Member.  Der Kontrolllauf hat kein Suffix."""
    return basis if m == KONTROLLLAUF else "%s_member%s" % (basis, m)


def member_liste(h):
    """Memberkennungen aus den Schluesselnamen, KONTROLLLAUF eingeschlossen.

    T-0026, gemessen 15.08.2026: ECMWF ENS liefert ueber Open-Meteo 51
    Reihen je Variable - 50 mit `_memberNN` und **eine ohne Suffix**.  Die
    ohne ist der Kontrolllauf, also der unstoerte und damit einzeln beste
    Lauf.  Die fruehere Fassung filterte auf `"_member" in k` und warf ihn
    weg: p wurde ueber 50 statt 51 Member gebildet, und ausgerechnet der
    informativste fehlte.  Kein Fehler, keine Warnung - nur ein Nenner, der
    nicht zur Modellbeschreibung passt.

    ACHTUNG, unveraendert gueltig: das zaehlt Schluessel, nicht Daten.  Ein
    Member mit durchgehend None steht hier trotzdem drin; erst verdichte()
    nimmt ihn aus Zaehler und Nenner.
    """
    mem = {k.split("_member")[1] for k in h if "_member" in k}
    # Gibt es eine suffixlose Reihe derselben Variable, ist das der Kontrolllauf.
    basen = {k.split("_member")[0] for k in h if "_member" in k}
    if basen & set(h):
        mem.add(KONTROLLLAUF)
    return sorted(mem)


def _rund(x, n=5):
    return None if x is None else round(x, n)


def verdichte(werte, schwelle):
    """(Score, Detail) je Member -> Wahrscheinlichkeit, Median, Mediandetail.

    Herausgeloest, weil hier der Fehler sass: score() gibt (0.0, None) zurueck,
    wenn KEINE Faecherzelle Daten hatte, und diese Null lief frueher in den
    Nenner.  Fehlende Daten stimmten damit still gegen den Sonnenuntergang -
    kein Fehler, keine Warnung, nur eine zu kleine Zahl und ein Alarm, der
    nicht ausloest.

    DAS DETAIL GEHOERT ZUM MEDIAN, NICHT ZUM BESTEN MEMBER (T-0064, geaendert
    02.09.2026).  Bis dahin stand hier `max(gueltig, key=...)`: Median und
    Wahrscheinlichkeit beschrieben die Mitte der Verteilung, die Begruendung
    daneben aber ihr optimistisches Ende.  Auf der Seite las sich das jeden
    Abend als Widerspruch - Beleg vom 01.09.2026 fuer den 11.09.: Median
    0.03, Wahrscheinlichkeit 2 %, Stufe "unauffaellig", und darunter
    "Mittelhohe Wolken, Licht kommt von Westen frei durch", weil ein einziger
    von 51 Membern auf S = 0.88 kam.

    Jetzt kommt alles aus demselben Member: p, Median, Schirm, A, Sicht, Weg
    und die Segmentliste, aus der der Vertikalschnitt seine Transmission
    zeichnet.  Beim Push ist das kein Verlust - der geht erst ab p >= 0.5
    raus, und dann liegt der Medianmember ohnehin ueber s*.

    Die Streuung geht dabei nicht verloren: das Tagesarchiv haelt weiterhin
    je Member eine eigene Zeile mit S, A, B, Sicht und Weg.

    Rueckgabe None, wenn kein einziger Member Daten hatte.
    """
    # Nach Score sortieren, aber NUR nach ihm: `sorted` auf den Tupeln selbst
    # wuerde bei gleichem Score die Detail-dicts vergleichen und mit
    # TypeError abbrechen.
    gueltig = sorted((x for x in werte if x[1] is not None),
                     key=lambda x: x[0])
    if not gueltig:
        return None
    mitte = gueltig[len(gueltig) // 2]
    return {"p": sum(1 for x in gueltig if x[0] >= schwelle) / len(gueltig),
            "median": mitte[0],
            "detail": mitte[1],
            "n_member": len(gueltig), "n_member_gesamt": len(werte)}


def versatz_km(sp_kmh, richtung_grad, stunden):
    """TRANSPORTweg der Luft in `stunden`: (dx nach Osten, dy nach Norden), km.

    `richtung_grad` ist meteorologisch, also die Richtung, AUS der es weht -
    daher die Vorzeichen.  Wind aus 270 Grad traegt die Luft nach OSTEN, die
    Rueckgabe ist dann (+x, 0).

    ACHTUNG beim Benutzen: das ist der Weg, den ein Luftpaket ZURUECKLEGT,
    nicht die Stelle, an der man es vorher abtastet.  Wer wissen will, welche
    Luft spaeter ueber einem Punkt steht, muss STROMAUF schauen, also den
    Versatz ABZIEHEN.  Siehe die Fundstelle in lauf_ort() - genau dort stand
    bis zum 02.09.2026 ein Plus (T-0063).
    """
    ms = sp_kmh / 3.6
    return (-ms * math.sin(math.radians(richtung_grad)) * stunden * 3.6,
            -ms * math.cos(math.radians(richtung_grad)) * stunden * 3.6)


def naechster_schritt(zeiten, ziel_dt):
    best, bi = None, None
    for i, t in enumerate(zeiten):
        dt = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        d = abs((dt - ziel_dt).total_seconds())
        if best is None or d < best:
            best, bi = d, i
    return bi, best / 3600.0


# Obergrenze fuer Pass 2 (T-0074, Review alarm#2), ueberschreibbar per
# `pass2_max_zellen` in konfig.json (null = kein Deckel).
#
# WARUM 320.  Gemessen im Log: Pass 2 hatte im August 110-150 Zellen, Anfang
# Oktober 290-320 (Hoechstwert im ganzen Log 319, am 07.10.).  Dazu kommen 72
# Zellen Pass 1 und eine Windzelle; mit Deckel ist ein Lauf also hoechstens
# rund 390 Ortsabrufe gross - so gross wie die groessten Laeufe, die
# nachweislich in einer Uhrstunde durchgingen (378 und 383 am 08.10.2026).
# Heute schneidet der Deckel nichts ab.  Er faengt, was die Messung nicht
# abdeckt: eine Starkwindlage im Maerz oder Juni, wenn dt wieder gross ist,
# koennte Pass 2 ueber jeden beobachteten Lauf treiben, und dann riss bisher
# der ganze Lauf am Limit, statt nur die fernen Abende ungenauer zu machen.
# Ein Deckel unter 320 wuerde schon viele Oktoberlaeufe beschneiden, ohne
# dass belegt ist, dass er das Stundenlimit verhindert (siehe LAST: das
# Gewicht ist offen).
PASS2_MAX_ZELLEN = 320


def deckle_pass2(neu, karte, abende, grenze):
    """Pass 2 auf `grenze` Zellen begrenzen, naechste Abende zuerst.

    Rueckgabe: die Zellen, die geholt werden.  Jede Zelle bekommt den Rang
    des FRUEHESTEN Abends, der sie braucht; behalten wird von vorn.  Fuer
    die verworfenen Zellen zeigt `karte` danach auf die unversetzte
    Faecherzelle aus Pass 1 - an diesen Punkten rechnet der Abend also wie
    mit `advektion: false`, statt mit einer Luecke.  Eine Luecke wuerde
    score() still aus dem Gewicht nehmen, und der Faecher waere an genau den
    Stellen duenn, an denen niemand nachsieht.
    """
    if grenze is None or len(neu) <= grenze:
        return set(neu)
    grenze = max(0, int(grenze))
    erster = {}
    for (t, _s, _schl), z in karte.items():
        if z in neu and (z not in erster or t < erster[z]):
            erster[z] = t
    rang = sorted(neu, key=lambda z: (erster[z], z))
    verworfen = set(rang[grenze:])
    betroffen = {}
    for (t, s, schl), z in list(karte.items()):
        if z in verworfen:
            karte[(t, s, schl)] = zelle(*abende[t]["punkte"][schl])
            betroffen[t] = betroffen.get(t, 0) + 1
    melde("   ACHTUNG Pass 2 GEDECKELT: %d von %d Zellen verworfen (Grenze %d)."
          " Ohne Advektion: %s"
          % (len(verworfen), len(neu), grenze,
             ", ".join("%s %d Punkte" % (t.strftime("%d.%m."), n)
                       for t, n in sorted(betroffen.items()))))
    return set(rang[:grenze])


def lauf_ort(ort, kfg, jetzt):
    """Die Abende dieses Ortes rechnen.  `jetzt` ist der Bezugszeitpunkt.

    `jetzt` statt `datetime.now()` (T-0068, 02.09.2026): `--jetzt` steuerte
    bisher nur die Fensterpruefung, waehrend hier die echte Uhr lief.  Ein
    Test konnte den Lauf damit nicht auf eine feste Zeit stellen - und
    `test_zustandspflege.py` war abends rot, weil der heutige Abend nach
    Sonnenuntergang wegfaellt.  Die frueheren Parameter `zustand` und
    `trocken` wurden nie gelesen und sind entfallen.
    """
    breite, laenge = ort["breite"], ort["laenge"]
    heute = jetzt.date()
    km_lon = 111.32 * math.cos(math.radians(breite))

    abende = {}
    fan_zellen = set()
    # AB HEUTE, nicht ab morgen.  Bis zum 18.08.2026 begann die Schleife bei
    # k = 1 - der heutige Abend wurde also nie gerechnet, sondern trug immer
    # die Zahlen vom Vortag.  Solange der Lauf morgens um 07:30 lag, fiel das
    # kaum auf; seit er drei Stunden vor Sonnenuntergang liegt, ist es der
    # Kern der Sache: der frischeste Modelllauf soll GENAU diesem Abend
    # gelten.  Am 18.08. stand fuer heute noch der Lauf vom 16.08.
    #
    # Ein Abend, dessen Sonnenuntergang schon vorbei ist, faellt raus - sonst
    # rechnet ein Lauf von Hand um Mitternacht eine Vergangenheit vor.
    for k in range(0, kfg["vorlauf_tage"] + 1):
        t = heute + timedelta(days=k)
        std, az = sonnenuntergang(t, breite, laenge)
        if std is not None and k == 0:
            su = datetime.combine(t, dtzeit(0), timezone.utc) + timedelta(hours=std)
            if su <= jetzt:
                melde("   heutiger Abend: Sonnenuntergang vorbei, uebersprungen")
                continue
        if std is None:
            continue
        punkte = {}
        for dv in sc.FAECHER_AZIMUTE:
            for d in sc.DISTANZEN_KM:
                p = ((breite, laenge) if d == 0.0
                     else zielpunkt(breite, laenge, (az + dv) % 360.0, d))
                punkte[(d, dv)] = p
                fan_zellen.add(zelle(*p))
        abende[t] = {"stunde": std, "azimut": az, "punkte": punkte}

    # WIND NUR AM ORT.  Die sechs Windvariablen werden ausschliesslich am
    # Heimatpunkt gelesen (`zentrum` weiter unten) - der Advektionsversatz
    # ist ein Ensemble-Mittelwind je Schicht, kein Feld.  Sie fuer alle 68
    # Faecherzellen zu holen war also reine Verschwendung, und keine
    # billige: nach dem Log zaehlt Open-Meteo Ensemble-Member meist wie
    # zusaetzliche Variablen, 9 Variablen x 51 Member wiegen dann dreimal so
    # viel wie 3 x 51 (siehe LAST oben: nicht ausnahmslos belegt).
    #
    # Gemessen am 18.08.2026: der Lauf kostete rund 5.500 Einheiten und riss
    # damit das Stundenlimit von 5.000 bei der vorletzten Anfrage.  Ohne den
    # Windballast waren es damals 217 Ortsabrufe, rund 3.500 Einheiten.
    # STAND 09.10.2026 (Review alarm#2): inzwischen 378-383 Ortsabrufe je
    # Lauf, nach demselben Gewicht rund 5.800 Einheiten.  Treiber ist Pass 2
    # (August 110-150 Zellen, Oktober 290-320), und der waechst mit dem
    # saisonalen Abstand dt zwischen Sonnenuntergang und naechstem
    # 3-h-Modellschritt (Versatz = v * dt): Spitze Anfang Oktober, Ende
    # November nahe 0, wieder hoch im Maerz und Juni.  Pass 2 ist deshalb
    # gedeckelt (`pass2_max_zellen`, unten).
    wolken = ["cloud_cover_%s" % s for s in SCHICHTEN]
    winde = []
    for s in SCHICHTEN:
        winde += ["wind_speed_%dhPa" % WINDNIVEAU[s],
                  "wind_direction_%dhPa" % WINDNIVEAU[s]]
    tage = kfg["vorlauf_tage"] + 1
    melde("   Pass 1: %d Zellen Wolken (%d Variablen)"
          % (len(fan_zellen), len(wolken)))
    feld = abfrage(fan_zellen, wolken, kfg["modell"], tage)
    heim = zelle(breite, laenge)
    melde("   Wind: 1 Zelle (%d Variablen)" % len(winde))
    feld[heim].update(abfrage({heim}, winde, kfg["modell"], tage)[heim])
    zeiten = feld[next(iter(feld))]["time"]
    mem = member_liste(feld[next(iter(feld))])
    # Gegenprobe: ohne Wind am Ort waere der Advektionsversatz still null,
    # und der Lauf saehe trotzdem erfolgreich aus.
    fehlend = [v for v in winde if not any(k.startswith(v) for k in feld[heim])]
    if fehlend:
        raise SystemExit("Wind am Ort fehlt: %s" % ", ".join(fehlend))
    LAST["member"] = len(mem)
    melde("   %d Member, %d native Schritte" % (len(mem), len(zeiten)))

    # Advektionsversatz je (Abend, Schicht) aus dem Ensemble-Mittelwind am Ort
    zentrum = feld[heim]
    versatz = {}
    for t, info in abende.items():
        ziel_dt = datetime(t.year, t.month, t.day, tzinfo=timezone.utc) \
            + timedelta(hours=info["stunde"])
        i, dt_h = naechster_schritt(zeiten, ziel_dt)
        info["schritt"], info["dt_h"] = i, dt_h
        vz = ziel_dt - datetime.fromisoformat(zeiten[i]).replace(tzinfo=timezone.utc)
        stunden = vz.total_seconds() / 3600.0
        for s in SCHICHTEN:
            # PAARWEISE filtern (T-0075, Review physik#14): nur Member, die
            # Geschwindigkeit UND Richtung haben.  Bis zum 09.10.2026 liefen
            # zwei getrennte Filter - bei Teilluecken mittelte der Lauf dann
            # Tempo und Richtung ueber verschiedene Membermengen, und fehlte
            # nur die Richtung, riss die Division durch len(ri) den Lauf mit
            # ZeroDivisionError ab.
            paare = []
            for m in mem:
                v = (zentrum.get(feldname("wind_speed_%dhPa" % WINDNIVEAU[s], m))
                     or [None] * (i + 1))
                r = (zentrum.get(feldname("wind_direction_%dhPa" % WINDNIVEAU[s], m))
                     or [None] * (i + 1))
                v = v[i] if i < len(v) else None
                r = r[i] if i < len(r) else None
                if v is not None and r is not None:
                    paare.append((v, r))
            if not paare:
                # Kein Wind am Ort fuer diese Schicht.  Bis zum 09.10.2026
                # stand hier still (0, 0): die Advektion war fuer den Abend
                # aus, und der Lauf meldete trotzdem Erfolg, pushte und
                # archivierte.  ENTSCHEIDUNG (T-0075): der Abend wird wie
                # einer ohne Wolkendaten uebersprungen - eine Zahl ohne
                # Advektion sieht genauso plausibel aus wie eine richtige
                # (siehe T-0063).  Fehlt der Wind an JEDEM Abend, bleibt
                # kein Ergebnis, und main() bucht den Lauf als gescheitert.
                versatz[(t, s)] = None
                info.setdefault("ohne_wind", []).append(s)
                continue
            # Richtungsmittel ueber Einheitsvektoren, nicht ueber Grad
            sx = sum(math.sin(math.radians(r)) for _, r in paare) / len(paare)
            cy = sum(math.cos(math.radians(r)) for _, r in paare) / len(paare)
            versatz[(t, s)] = versatz_km(sum(v for v, _ in paare) / len(paare),
                                         math.degrees(math.atan2(sx, cy)) % 360.0,
                                         stunden)

    # Pass 2: versetzte Positionen
    versetzt_zellen, karte = set(), {}
    for t, info in abende.items():
        if info.get("ohne_wind"):
            continue                       # wird unten uebersprungen
        for s in SCHICHTEN:
            dx, dy = versatz[(t, s)]
            for schl, (la, lo) in info["punkte"].items():
                # STROMAUF, nicht stromab (T-0063, korrigiert 02.09.2026).
                #
                # Gesucht ist die Wolke, die zum SONNENUNTERGANG ueber dem
                # Fanpunkt steht.  Das Modellfeld liegt aber zum nativen
                # Schritt `i` vor, also `stunden` frueher.  Zu diesem
                # frueheren Zeitpunkt war dieselbe Luft noch STROMAUF - bei
                # Westwind also westlich.  Abgetastet wird deshalb
                # Fanpunkt MINUS Transportversatz.
                #
                # Bis zum 02.09.2026 stand hier ein Plus.  Der Lauf las damit
                # die Zelle auf der falschen Seite, mit dem doppelten Fehler
                # 2*v*|dt| - bei 100 km/h und dt = 0.5 h also 100 km daneben.
                # Aufgefallen ist es nie, weil ein verschobener Faecher
                # genauso plausible Zahlen liefert wie ein richtiger.
                z = zelle(la - dy / 111.32, lo - dx / km_lon)
                karte[(t, s, schl)] = z
                versetzt_zellen.add(z)
    neu = versetzt_zellen - fan_zellen
    if kfg.get("advektion", True) and neu:
        print("   Pass 2: %d zusaetzliche Zellen" % len(neu), flush=True)
        neu = deckle_pass2(neu, karte, abende,
                           kfg.get("pass2_max_zellen", PASS2_MAX_ZELLEN))
        if neu:
            feld.update(abfrage(neu, wolken, kfg["modell"], tage))

    ergebnisse = {}
    for t, info in abende.items():
        if kfg.get("advektion", True) and info.get("ohne_wind"):
            melde("   %s: KEIN Wind am Ort (%s) - Abend uebersprungen, ohne "
                  "Advektion waere die Zahl still falsch"
                  % (t, ", ".join(info["ohne_wind"])))
            continue
        i = info["schritt"]
        werte = []
        for m in mem:
            def hole(d, dv, schicht, _i=i, _m=m, _t=t):
                z = (karte.get((_t, schicht, (d, dv))) if kfg.get("advektion", True)
                     else zelle(*info["punkte"][(d, dv)]))
                e = feld.get(z)
                if e is None:
                    return None
                r = e.get(feldname("cloud_cover_%s" % schicht, _m))
                if r is None or _i >= len(r) or r[_i] is None:
                    return None
                return r[_i] / 100.0
            s, det = score(hole)
            werte.append((s, det))

        # Wolkenfeld fuer den Vertikalschnitt der Produktseite mitschreiben.
        # Ohne das kann die Seite die Prognose zwar als Zahl zeigen, aber
        # nicht als Bild - und das Bild ist der Punkt: es zeigt, WARUM.
        # Gespeichert wird der MemberMEDIAN je Faecherpunkt und Schicht,
        # umgeschluesselt auf das 0.5-Grad-Gitter, das schnitt.py erwartet.
        # Rund 120 Zahlen je Abend.
        feld_seite = {}
        for (d_, dv_), (la_, lo_) in info["punkte"].items():
            schluessel = "%d/%d" % (round(la_ / 0.5), round(lo_ / 0.5))
            eintrag = feld_seite.setdefault(schluessel, {})
            for schicht in SCHICHTEN:
                vals = []
                for m in mem:
                    z_ = (karte.get((t, schicht, (d_, dv_)))
                          if kfg.get("advektion", True) else zelle(la_, lo_))
                    e_ = feld.get(z_)
                    if e_ is None:
                        continue
                    r_ = e_.get(feldname("cloud_cover_%s" % schicht, m))
                    if r_ is None or i >= len(r_) or r_[i] is None:
                        continue
                    vals.append(r_[i])
                if vals:
                    vals.sort()
                    eintrag[schicht] = vals[len(vals) // 2]

        v = verdichte(werte, kfg["schwelle_score"])
        if v is None:
            print("   %s: KEIN Member mit Daten - Abend uebersprungen" % t,
                  flush=True)
            continue
        if v["n_member"] < v["n_member_gesamt"]:
            print("   %s: %d von %d Membern ohne Daten, aus dem Nenner genommen"
                  % (t, v["n_member_gesamt"] - v["n_member"],
                     v["n_member_gesamt"]), flush=True)

        besterdet = v["detail"]
        ergebnisse[str(t)] = {
            "p": v["p"], "median": v["median"], "stunde_utc": info["stunde"],
            "azimut": info["azimut"], "dt_h": info["dt_h"],
            "schirm": besterdet["schirm"] if besterdet else None,
            "A": besterdet["A"] if besterdet else None,
            "sicht": besterdet["sicht"] if besterdet else None,
            "weg": besterdet["weg"] if besterdet else None,
            # Die Segmentliste des besten Members: (d_nah, d_fern, Schichten,
            # Bedeckung).  Der Vertikalschnitt zeichnet damit die ECHTE
            # Transmission je Ring, statt sie aus dem Medianfeld nachzurechnen -
            # letzteres ist fuer das Bild vertretbar, aber es ist eine zweite
            # Rechnung neben der, die den Score gemacht hat.
            "segmente": [[a, b, list(sch), c]
                         for a, b, sch, c in (besterdet["segmente"]
                                              if besterdet else [])],
            "n_member": v["n_member"], "n_member_gesamt": v["n_member_gesamt"],
            "feld": feld_seite,
            # Fuers Archiv (T-0003, Neufassung 20.08.2026): eine Zeile je
            # Member.  Die Wahrscheinlichkeit ist ein Anteil ueber diese 51
            # Zahlen - ohne sie laesst sich spaeter weder ein Rangdiagramm
            # noch ein Brier-Skill rechnen, nur die Trefferquote.
            # `segmente` bleibt draussen: das waere je Member eine eigene
            # Ringliste und blaeht das Archiv um ein Vielfaches.
            "member": [
                {"s": round(sc_, 6),
                 "schirm": (dt_ or {}).get("schirm"),
                 "A": _rund((dt_ or {}).get("A")),
                 "B": _rund((dt_ or {}).get("B")),
                 "sicht": _rund((dt_ or {}).get("sicht")),
                 "weg": _rund((dt_ or {}).get("weg"))}
                for sc_, dt_ in werte]}
    return ergebnisse


def begruendung(e):
    """Halbsatz fuers Push.

    Bewusst NICHT "klarer Westhorizont": der Score prueft nicht, ob man den
    Horizont sieht, sondern ob das Licht 200-400 km westlich in 1-2 km Hoehe
    durchkommt.  Man muss die Sonne gar nicht sehen koennen - und sie darf
    laengst untergegangen sein, waehrend hohe Wolken noch eine halbe Stunde
    weiterglueht.  Die alte Formulierung behauptete eine Sichtbedingung, die
    das Modell nirgends stellt.
    """
    teile = []
    schirm = {"high": "hohe Wolken", "mid": "mittelhohe Wolken"}.get(e["schirm"], "Wolken")
    teile.append(schirm if (e["A"] or 0) >= 0.35 else "wenig " + schirm)
    if (e["weg"] or 0) >= 0.6:
        teile.append("Licht kommt von Westen frei durch")
    elif (e["weg"] or 0) >= 0.3:
        teile.append("Lichtweg nach Westen teils frei")
    if (e["sicht"] or 1) < 0.5:
        teile.append("aber tiefe Decke ueber der Stadt")
    return ", ".join(teile)


def lokalzeit(tag, stunde_utc, zone):
    dt = datetime(int(tag[:4]), int(tag[5:7]), int(tag[8:]), tzinfo=timezone.utc) \
        + timedelta(hours=stunde_utc)
    try:
        dt = dt.astimezone(ZoneInfo(zone))
    except Exception:                                            # noqa: BLE001
        pass                      # unbekannte Zone: dann eben UTC anzeigen
    return dt


def sende(topic, titel, text, prio="default", klick=None):
    kopf = {"Title": titel.encode("utf-8").decode("latin-1", "replace"),
            "Priority": prio, "Tags": "sunrise"}
    # Ein Alarm ohne Ziel ist eine Sackgasse: er sagt "heute abend lohnt es
    # sich" und laesst den Leser dann selbst die Seite suchen.
    if klick:
        kopf["Click"] = klick
    req = urllib.request.Request(
        "%s/%s" % (NTFY, topic), data=text.encode("utf-8"), headers=kopf)
    with urllib.request.urlopen(req, timeout=30) as f:
        return f.status


def laufziele(jetzt, kfg, ort):
    """[(Name, Zielzeitpunkt UTC)] - die geplanten Laeufe dieses Tages.

    ZWEI Fenster seit dem 18.08.2026:

    "abends"   SONNENUNTERGANGSRELATIV, drei Stunden vorher.  Der wichtige:
               er sieht den juengsten Modelllauf und traegt den Push.  Keine
               feste Uhrzeit, weil der Sonnenuntergang in Berlin ueber das
               Jahr um mehr als fuenfeinhalb Stunden wandert - ein Termin um
               17:00 laege im Dezember HINTER dem Ereignis (SU 15:53).
    "morgens"  feste UTC-Zeit, kurz nachdem der 00z-Lauf verfuegbar wird
               (08:44 UTC, gemessen).  Damit stehen vormittags schon
               aktuelle Zahlen auf der Seite.
    """
    tag = jetzt.astimezone(ZoneInfo(ort.get("zeitzone", "UTC"))).date()
    aus = []
    hh, mm = (kfg.get("lauf_morgens_utc") or "09:20").split(":")
    aus.append(("morgens",
                datetime.combine(tag, dtzeit(int(hh), int(mm)), timezone.utc)))
    std, _ = sonnenuntergang(tag, ort["breite"], ort["laenge"])
    if std is not None:
        su = datetime.combine(tag, dtzeit(0), timezone.utc) + timedelta(hours=std)
        aus.append(("abends",
                    su - timedelta(hours=kfg.get("lauf_vorlauf_stunden", 3))))
    return tag, aus


def gelaufen(zustand, ort, tag):
    """Welche Fenster hat dieser Ort heute schon bedient?

    Vertraegt den alten Zustand, in dem `laeufe[tag]` eine Zeichenkette war:
    ein solcher Eintrag blockiert kein Fenster, er ist nur Historie.
    """
    e = (zustand.get(ort["name"], {}).get("laeufe", {}) or {}).get(str(tag))
    return set(e) if isinstance(e, dict) else set()


def im_laufenster(jetzt, kfg, ort, zustand):
    """(Fenstername oder None, Grund) - ist JETZT ein geplanter Lauf faellig?

    Dasselbe Muster wie in erinnerung.py: der Agent laeuft stuendlich, die
    Entscheidung faellt hier.  Das ist der einzige Weg, der Sommer und
    Winter mit EINER Regel bedient.
    """
    tag, ziele = laufziele(jetzt, kfg, ort)
    schon = gelaufen(zustand, ort, tag)
    halb = timedelta(minutes=kfg.get("lauf_fenster_min", 60)) / 2
    offen = []
    for name, ziel in ziele:
        if name in schon:
            continue
        if ziel - halb <= jetzt <= ziel + halb:
            return name, "im Fenster %s" % name
        offen.append("%s %s" % (name, ziel.strftime("%H:%M")))

    # NACHHOLEN, aber nur den Abendlauf und nur bis zum Sonnenuntergang.
    #
    # Am 18.08.2026 hat der stuendliche Agent den einen Tick verschlafen,
    # der ins Abendfenster fiel: die Ticks stehen um 16:20 und 18:20
    # Ortszeit im Log, der um 17:20 fehlt (Rechner im Ruhezustand; launchd
    # holt einen verpassten Kalendertermin beim Aufwachen nach, aber da war
    # das Fenster laengst zu). Ergebnis: kein Abendlauf, und weil derselbe
    # Tag vormittags schon gerechnet worden war, hat es auch der
    # Altersstreifen nicht gemeldet.
    #
    # Ein Lauf zwei Stunden vor Sonnenuntergang ist schlechter als einer
    # drei Stunden vorher - aber unvergleichlich besser als keiner. Der
    # Vormittagslauf wird NICHT nachgeholt: er ist Beiwerk, und ein
    # Nachholen kurz vor dem Abendfenster brauchte zwei Laeufe in einer
    # Stunde, was das Stundenkontingent nicht traegt.
    if "abends" not in schon:
        for name, ziel in ziele:
            if name != "abends" or jetzt <= ziel + halb:
                continue
            std, _ = sonnenuntergang(tag, ort["breite"], ort["laenge"])
            su = (datetime.combine(tag, dtzeit(0), timezone.utc)
                  + timedelta(hours=std)) if std is not None else None
            if su and jetzt < su:
                return "abends", ("nachgeholt (Fenster verpasst, noch %.1f h "
                                  "bis Sonnenuntergang)"
                                  % ((su - jetzt).total_seconds() / 3600))

    if not offen:
        return None, "heute schon gerechnet"
    return None, ("ausserhalb der Fenster (offen: %s; jetzt %s UTC)"
                  % (", ".join(offen), jetzt.strftime("%H:%M")))


# T-0058: Grenzen fuer die Zustandsdatei.
#
# GEMESSEN 23.08.2026: 156 kB nach neun Betriebstagen, 18 Abende, keine
# Raeumung - hochgerechnet rund 6 MB im Jahr.  Und `bisher.py` und
# `bewertungsseite.py` iterieren bei JEDEM Seitenbau ueber alles, also alle
# zehn Minuten.  Das waechst nicht nur, es wird auch jedes Mal gelesen.
#
# Was weg darf: unbewertete Abende, die lange vorbei sind.  Ihre
# Prognosedaten liegen vollstaendig im Tagesarchiv (T-0003) - je Abend die
# Scorezeile jedes Members und das Medianfeld.  Die Zustandsdatei ist
# Betriebszustand, kein Archiv.
#
# Was BLEIBT: alles Bewertete, unbefristet.  Eine Note ist die einzige
# Messgroesse, die nicht nachproduzierbar ist - dafuer gibt es keinen
# zweiten Abruf und keine zweite Quelle.
BEHALTEN_TAGE = 30
VERLAUF_MAX = 10


def raeume(eintrag, heute):
    """Alte, unbewertete Abende entfernen.  Rueckgabe: wie viele.

    Bewusst NUR die Abende - `alarme` und `laeufe` sind je Eintrag ein paar
    Bytes und tragen die Idempotenz bzw. die Fensterbuchhaltung.  Wer sie
    raeumt, riskiert einen doppelten Push oder einen doppelten Lauf, und
    spart dafuer nichts Messbares.
    """
    grenze = heute - timedelta(days=BEHALTEN_TAGE)
    weg = []
    for t, e in (eintrag.get("abende") or {}).items():
        if e.get("bewertung") is not None:
            continue                       # bewertet: bleibt, immer
        try:
            d = date.fromisoformat(t)
        except (TypeError, ValueError):
            continue                       # unlesbarer Schluessel: nicht anfassen
        if d < grenze:
            weg.append(t)
    for t in weg:
        del eintrag["abende"][t]
    return len(weg)


def main():
    """Der Lauf.  Die Huelle setzt den Blockcache-Schluessel danach zurueck.

    Sonst schriebe ein spaeterer Aufruf von lauf_ort() im selben Prozess (ein
    Test, ein Analyseskript) still in den Cache eines Laufs, der laengst
    vorbei ist.
    """
    try:
        _main()
    finally:
        ABRUF_CACHE["init"] = None


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trocken", action="store_true",
                    help="rechnen und anzeigen, aber nichts senden")
    ap.add_argument("--geplant", action="store_true",
                    help="der stuendliche Agent: nur im Laufenster arbeiten")
    ap.add_argument("--jetzt", help="ISO-Zeit UTC statt jetzt (fuer Tests)")
    ap.add_argument("--konfig", default=os.path.join(BASIS, "konfig.json"))
    a = ap.parse_args()

    # Erst Netz, dann rechnen: der Rechner kann gerade erst
    # aufgewacht sein (siehe skripte/netz.py).
    melde("Lauf beginnt.")
    warte_auf_netz(melde=melde)

    with open(a.konfig) as f:
        kfg = json.load(f)
    # Das Alarm-Topic steht in konfig_geheim.json (gitignoriert), nicht in der
    # versionierten Konfiguration: wer es hat, kann beliebige Pushs schicken.
    # Das Bewertungs-Topic bleibt oeffentlich - es steht ohnehin im Klartext in
    # der ausgelieferten Seite und laesst sich gar nicht verbergen.
    gpfad = os.path.join(BASIS, "konfig_geheim.json")
    geheim = {}
    if os.path.exists(gpfad):
        with open(gpfad) as f:
            geheim = json.load(f)
    for _o in kfg["orte"]:
        _t = (geheim.get("ntfy_alarm") or {}).get(_o["name"])
        if _t:
            _o["ntfy_alarm"] = _t
    fan_setzen(kfg)          # T-0057: bricht ab, wenn `faecher` gesetzt ist
    zpfad = os.path.join(BASIS, "daten", "zustand.json")
    zustand = {}
    if os.path.exists(zpfad):
        with open(zpfad) as f:
            zustand = json.load(f)

    jetzt = (datetime.fromisoformat(a.jetzt).replace(tzinfo=timezone.utc)
             if a.jetzt else datetime.now(timezone.utc))
    archive = {}                      # je Ort die Abende fuers Tagesarchiv
    # Welches Fenster bedient dieser Lauf?  Fuer die Buchhaltung am Ende.
    fenster = {}
    if a.geplant:
        # Der stuendliche Agent fragt hier, ob er dran ist.  Ein Lauf von
        # Hand fragt NICHT - wer ihn startet, meint ihn.
        for o in kfg["orte"]:
            name, grund = im_laufenster(jetzt, kfg, o, zustand)
            melde("   %s: %s" % (o["name"], grund))
            if name:
                fenster[o["name"]] = name
        if not fenster:
            # T-0065: auch der Leerlauf schreibt den Modelllauf mit.  Er
            # kommt aus einer STATISCHEN Datei und zaehlt nicht aufs
            # Kontingent - eine Zeile je Stunde, und nach zwei Wochen ist
            # belegt, wann der 00z-Lauf tatsaechlich verfuegbar wird.
            # Bisher stand diese Zahl nur an den zwei Laufzeitpunkten im
            # Log, und `konfig.json` behauptete daraus "08:44 UTC" - eine
            # Groesse aus einer einzigen Probe, an der `lauf_morgens_utc`
            # haengt.
            melde("   Modelllauf jetzt: %s"
                  % (modelllauf(kfg["modell"]) or "unbekannt"))
            return

    # T-0058: Die Rechnung dauert Minuten - der Zustand wird deshalb NICHT
    # waehrenddessen veraendert.  Alles Neue sammelt sich hier und wird ganz
    # am Ende unter Sperre gegen den FRISCHEN Stand eingemergt.  Sonst
    # ueberschreibt dieser Lauf eine Bewertung, die der Poller in der
    # Zwischenzeit eingesammelt hat - nachgestellt und belegt.
    neue_abende = {}          # {ort: {tag: (eintrag, verlaufszeile)}}
    neue_alarme = {}          # {ort: {tag: buchung}}
    # T-0075 (Review alarm#8): Orte, fuer die der Lauf KEINEN einzigen Abend
    # geliefert hat.  Sie werden nicht gebucht - kein `laeufe`-Eintrag, kein
    # frisches `stand.geholt` - und der Lauf endet mit Exitcode 1.  Bis zum
    # 09.10.2026 galt so ein Lauf als Erfolg: das Fenster war verbraucht,
    # nichts wurde nachgeholt, und die Seite hielt die alten Abende fuer
    # frisch.
    leer = []

    # Der Modelllauf wird VOR dem Abruf geholt (T-0065, 02.09.2026).  Vorher
    # stand er hinter der Ortsschleife, also rund vier Minuten spaeter - und
    # genau dazwischen kann ein neuer Lauf verfuegbar werden.  Dann trugen
    # Archiv und Standzeile eine Initialisierung, aus der die Zahlen gar
    # nicht stammten.  Das ist ausgerechnet das Feld, auf dem alle
    # Verzugsaussagen des Projekts beruhen.
    # T-0074: Kontingentsperre VOR jedem Abruf.  Steht noch ein Vermerk aus
    # einem Abbruch am Stunden- oder Tageslimit, endet der Lauf hier - ohne
    # Abruf und ohne Buchung, damit das Fenster nach Ablauf der Sperre noch
    # offen ist.  Geprueft gegen die ECHTE Uhr, nicht gegen --jetzt: die
    # Sperre beschreibt die Gegenseite, nicht den simulierten Zeitpunkt.
    gesperrt = aktive_sperre(zustand, _jetzt_utc())
    if gesperrt:
        melde("   Kontingentsperre bis %s UTC (%s) - kein Abruf"
              % (gesperrt[0].strftime("%d.%m. %H:%M"), gesperrt[1]))
        return
    # Alte Cacheordner weg, bevor neue entstehen (T-0074).
    weg = raeume_cache(_jetzt_utc())
    if weg:
        melde("   Blockcache: %d alte Modelllaeufe geraeumt" % weg)

    init = modelllauf(kfg["modell"])
    melde("   Modelllauf: %s" % (init or "unbekannt"))
    # Blockcache je Modelllauf (T-0074).  Unbekannter Lauf: kein Cache.
    ABRUF_CACHE["init"] = init
    if not init:
        melde("   Blockcache aus: Modelllauf unbekannt")

    for ort in kfg["orte"]:
        name = ort["name"]
        # T-0056: Beim geplanten Lauf nur die Orte rechnen, deren Fenster
        # wirklich offen ist.  Ohne diesen Filter loeste EIN faelliger Ort
        # den vollen Abruf fuer ALLE aus - je Ort ein ganzer Lauf (im Oktober
        # 2026 rund 380 Ortsabrufe, siehe lauf_ort) fuer Zahlen, die niemand
        # angefordert hat, und ihre `laeufe`
        # wurden dabei als "vonhand" gebucht, was ihr eigenes Fenster fuer
        # den Tag verbraucht haette.  Bei drei Orten waere das Tagesbudget
        # nach einem Abendlauf weitgehend weg.
        # Ein Lauf VON HAND rechnet weiter alle Orte: wer ihn startet,
        # meint ihn (dieselbe Begruendung wie beim Fenster-Check oben).
        if a.geplant and name not in fenster:
            continue
        print("=== %s" % ort["anzeige"], flush=True)
        try:
            erg = lauf_ort(ort, kfg, jetzt)
        except Kontingent as k:
            # T-0074: die Sperre festhalten, dann wie bisher abbrechen.  Die
            # geholten Bloecke liegen im Blockcache; der erste Tick nach der
            # Sperre holt nur, was fehlt.
            if k.sperre_bis:
                vermerke_sperre(zpfad, k.sperre_bis, k.grund)
                melde("   Kontingentsperre vermerkt bis %s UTC"
                      % k.sperre_bis.strftime("%d.%m. %H:%M"))
            raise
        if not erg:
            melde("   %s: KEIN Abend mit Ergebnis - Lauf gescheitert, nichts "
                  "gebucht, das Fenster bleibt offen" % name)
            leer.append(name)
            continue
        eintrag = zustand.setdefault(name, {"abende": {}, "alarme": {}})
        archiv_abende = archive.setdefault(name, {})
        meine = neue_abende.setdefault(name, {})

        for tag in sorted(erg):
            e = erg[tag]
            alt = eintrag["abende"].get(tag, {})
            # T-0022: den GANZEN Prognosestand je Lauf festhalten, nicht nur p.
            # Vorher stand hier {"lauf", "p"}; Median, Schirm, A, sicht, weg und
            # die Memberzahl wurden beim naechsten Lauf ueberschrieben.  Nach
            # einer Saison waere damit nur die Trefferquote je Vorlauf
            # auswertbar gewesen, nicht WARUM ein Alarm danebenlag - und genau
            # das ist die Frage, fuer die der Livegang ueberhaupt stattfindet.
            verlaufszeile = dict(
                {k: v for k, v in e.items()
                 # `feld` bleibt draussen: 120 Zahlen je Lauf und Abend
                 # blaehen die Zustandsdatei, und fuer die Rueckschau
                 # zaehlen die Terme, nicht das Rohfeld.
                 if k not in ("verlauf", "bewertung", "feld", "member")},
                # Der Tag des LAUFS, aus `jetzt` - nicht aus der Systemuhr.
                # Sonst traegt ein Lauf mit --jetzt eine Verlaufszeile mit
                # dem echten Datum und ist im Nachhinein nicht zuzuordnen.
                lauf=str(jetzt.date()))
            archiv_abende[tag] = {
                k: e[k] for k in ("p", "median", "stunde_utc", "azimut",
                                  "dt_h", "schirm", "A", "sicht", "weg",
                                  "n_member", "n_member_gesamt", "member",
                                  "feld")}
            e.pop("member", None)
            meine[tag] = (e, verlaufszeile)
            lz = lokalzeit(tag, e["stunde_utc"], ort.get("zeitzone", "UTC"))
            marke = "*" if e["p"] >= kfg["schwelle_wahrscheinlichkeit"] else " "
            print("   %s %s %s %2.0f %%  Median %.2f  (%s, dt %.1f h)"
                  % (marke, WOCHENTAG[lz.weekday()], lz.strftime("%d.%m. %H:%M"),
                     100 * e["p"], e["median"], e["schirm"], e["dt_h"]))

            if e["p"] < kfg["schwelle_wahrscheinlichkeit"]:
                continue
            if tag in eintrag["alarme"]:
                continue          # Idempotenz: je Abend hoechstens ein Alarm
            titel = "Streulicht %s" % ort["anzeige"]
            text = "%s %s, %s Uhr - %.0f %%. %s" % (
                WOCHENTAG[lz.weekday()], lz.strftime("%d.%m."),
                lz.strftime("%H:%M"), 100 * e["p"], begruendung(e))
            if a.trocken:
                print("     [trocken] wuerde senden: %s" % text)
            else:
                basis_url = (kfg.get("seiten_basis") or "").rstrip("/")
                # T-0055: der Versand darf den Lauf nicht mitreissen.  Vorher
                # stand hier kein try/except, und persistiert wird erst ganz
                # am Ende - ein ntfy-Timeout nach vollstaendiger Rechnung
                # verwarf also Buchung, Stand UND Tagesarchiv.  Weil dann
                # auch `laeufe` fehlt, haelt im_laufenster() das Fenster fuer
                # offen und der naechste stuendliche Tick rechnet alles neu:
                # ein ganzer Lauf (Oktober 2026 rund 380 Ortsabrufe; seit
                # T-0074 meist aus dem Blockcache) fuer Zahlen, die schon da
                # waren.  Ein toter Push ist kein toter Lauf.
                try:
                    sende(ort["ntfy_alarm"], titel, text, "high",
                          "%s/index.html" % basis_url if basis_url else None)
                except Exception as ex:
                    # NICHT buchen.  Ein Abend, der als gemeldet gilt, ohne
                    # dass eine Meldung ankam, wird durch die Idempotenz-
                    # sperre nie nachgeholt - das waere schlimmer als der
                    # Fehler, den dieser Block behebt.  Der naechste Lauf
                    # findet den Abend unbedient und versucht es erneut.
                    melde("     -> Push FEHLGESCHLAGEN (%s: %s) - nicht "
                          "gebucht, naechster Lauf versucht es erneut"
                          % (type(ex).__name__, ex))
                else:
                    neue_alarme.setdefault(name, {})[tag] = {
                        "gesendet": datetime.now(timezone.utc).isoformat(
                            timespec="seconds"), "p": e["p"]}
                    print("     -> Push gesendet")

    # Erst NACH erfolgreichem Durchlauf eintragen: ein am Kontingent
    # gestorbener Lauf darf das Fenster fuer heute nicht verbrauchen.
    for ort in kfg["orte"]:
        if a.geplant and ort["name"] not in fenster:
            continue                       # T-0056: nicht gerechnet, nichts zu buchen
        tag = jetzt.astimezone(ZoneInfo(ort.get("zeitzone", "UTC"))).date()
        abende = archive.get(ort["name"])
        if abende and not a.trocken:
            ziel, gr = schreibe_archiv(
                ort["name"], tag, fenster.get(ort["name"], "vonhand"),
                init, jetzt, kfg, abende)
            melde("   Archiv: %s (%.0f kB)" % (os.path.basename(ziel), gr / 1000))

    def einmerge(z):
        """Das Ergebnis dieses Laufs in den FRISCHEN Zustand eintragen.

        Laeuft unter Sperre (siehe zustandsdatei.aktualisiere) und bekommt den
        Stand von JETZT, nicht den vom Laufbeginn.  Alles, was ein anderer
        Agent inzwischen geschrieben hat, ist hier sichtbar und wird bewahrt.
        """
        geraeumt = gekuerzt = 0
        for ort in kfg["orte"]:
            name = ort["name"]
            if a.geplant and name not in fenster:
                continue                   # T-0056: nicht gerechnet, nichts zu mergen
            if name in leer:
                continue                   # T-0075: gescheitert, nicht buchen
            tag = jetzt.astimezone(ZoneInfo(ort.get("zeitzone", "UTC"))).date()
            eintrag = z.setdefault(name, {"abende": {}, "alarme": {}})

            for t, (e, verlaufszeile) in neue_abende.get(name, {}).items():
                alt_e = eintrag["abende"].get(t, {})
                # Die Bewertungsfelder gehoeren dem Bewertungsagenten.  Sie
                # kommen IMMER aus dem frischen Stand - genau hier ging vorher
                # eine gerade eingesammelte Note verloren.
                for k in ("bewertung", "bewertung_anlass", "bewertung_zeit",
                          "bewertung_erfasst"):
                    if k in alt_e:
                        e[k] = alt_e[k]
                e.setdefault("bewertung", None)
                verlauf = (alt_e.get("verlauf") or []) + [verlaufszeile]
                if len(verlauf) > VERLAUF_MAX:
                    gekuerzt += len(verlauf) - VERLAUF_MAX
                    verlauf = verlauf[-VERLAUF_MAX:]
                e["verlauf"] = verlauf
                eintrag["abende"][t] = e

            for t, buchung in neue_alarme.get(name, {}).items():
                eintrag["alarme"][t] = buchung

            heute = eintrag.setdefault("laeufe", {}).get(str(tag))
            if not isinstance(heute, dict):
                heute = {}
            heute[fenster.get(name, "vonhand")] = \
                jetzt.isoformat(timespec="seconds")
            eintrag["laeufe"][str(tag)] = heute
            eintrag["stand"] = {"geholt": jetzt.isoformat(timespec="minutes"),
                                "modelllauf": init,
                                "fenster": fenster.get(name, "vonhand")}
            geraeumt += raeume(eintrag, tag)
        if SPERRSCHLUESSEL in z and not aktive_sperre(z, _jetzt_utc()):
            del z[SPERRSCHLUESSEL]          # abgelaufen: kein Vermerk mehr noetig
        if geraeumt or gekuerzt:
            melde("   Geraeumt: %d alte Abende, %d Verlaufszeilen gekuerzt"
                  % (geraeumt, gekuerzt))

    melde("   Bilanz: %d HTTP-Anfragen, %d Ortsabrufe, bis %d Variablen, "
          "%d Tage, %d Member, %d Orte aus dem Blockcache"
          % (LAST["anfragen"], LAST["orte"], LAST["variablen"],
             LAST["tage"], LAST["member"], LAST["aus_cache"]))
    if not a.trocken:
        # T-0051 atomar UND T-0058 unter Sperre: `aktualisiere` laedt frisch,
        # wendet den Merge an und tauscht die Datei per os.replace ein.
        aktualisiere(zpfad, einmerge)
        print("\nZustand: %s" % zpfad)
    if leer:
        # Exitcode 1 MIT Grund im Log.  Die Orte mit Ergebnis sind oben
        # schon gebucht; nur die leeren bleiben offen.
        raise SystemExit("Kein Ergebnis fuer %s - nicht gebucht, das "
                         "Fenster bleibt offen"
                         % ", ".join(leer))


if __name__ == "__main__":
    main()
