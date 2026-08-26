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
import json
import math
import os
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
# Open-Meteo zaehlt nach eigener Doku nach VARIABLEN und ZEITRAUM, nicht
# nach Orten - die Rechnung unten ist deshalb ausdruecklich eine SCHAETZUNG
# und keine Nachbildung ihrer Formel.  Sie taugt zum Vergleichen von
# Laeufen untereinander, nicht zum Vorhersagen des Limits.
LAST = {"anfragen": 0, "orte": 0, "variablen": 0, "member": 0, "tage": 0}


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


def _hole(u, versuche=4):
    LAST["anfragen"] += 1
    for n in range(versuche):
        try:
            with urllib.request.urlopen(u, timeout=600) as f:
                return json.load(f)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            grund = json.loads(e.read()).get("reason", "429")
            if "inutely" in grund and n < versuche - 1:
                melde("   Minutenlimit, warte 65 s ... (Anfrage %d)"
                      % LAST["anfragen"])
                time.sleep(65)
                continue
            raise SystemExit("%s Kontingent nach %d Anfragen "
                             "(%d Ortsabrufe, %d Variablen, %d Tage): %s"
                             % (uhr(), LAST["anfragen"], LAST["orte"],
                                LAST["variablen"], LAST["tage"], grund))
    raise SystemExit("unerreichbar")


def abfrage(zellen, variablen, modell, tage, block=25):
    aus = {}
    liste = sorted(zellen)
    LAST["variablen"] = max(LAST["variablen"], len(variablen))
    LAST["tage"] = max(LAST["tage"], tage)
    melde("   Abruf: %d Zellen, %d Variablen, %d Tage, Bloecke zu %d"
          % (len(liste), len(variablen), tage, block))
    for i in range(0, len(liste), block):
        teil = liste[i:i + block]
        LAST["orte"] += len(teil)
        u = ("https://ensemble-api.open-meteo.com/v1/ensemble?latitude=%s&longitude=%s"
             "&models=%s&hourly=%s&forecast_days=%d&temporal_resolution=native"
             % (",".join("%.4f" % mitte(z)[0] for z in teil),
                ",".join("%.4f" % mitte(z)[1] for z in teil),
                modell, ",".join(variablen), tage))
        d = _hole(u)
        if isinstance(d, dict):
            d = [d]
        for z, e in zip(teil, d):
            aus[z] = e["hourly"]
        time.sleep(1)
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
    """(Score, Detail) je Member -> Wahrscheinlichkeit, Median, bestes Detail.

    Herausgeloest, weil hier der Fehler sass: score() gibt (0.0, None) zurueck,
    wenn KEINE Faecherzelle Daten hatte, und diese Null lief frueher in den
    Nenner.  Fehlende Daten stimmten damit still gegen den Sonnenuntergang -
    kein Fehler, keine Warnung, nur eine zu kleine Zahl und ein Alarm, der
    nicht ausloest.

    Rueckgabe None, wenn kein einziger Member Daten hatte.
    """
    gueltig = [x for x in werte if x[1] is not None]
    if not gueltig:
        return None
    punkte = sorted(x[0] for x in gueltig)
    return {"p": sum(1 for x in punkte if x >= schwelle) / len(punkte),
            "median": punkte[len(punkte) // 2],
            "detail": max(gueltig, key=lambda x: x[0])[1],
            "n_member": len(gueltig), "n_member_gesamt": len(werte)}


def versatz_km(sp_kmh, richtung_grad, stunden):
    """Meteorologische Windrichtung: Richtung, AUS der es weht."""
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


def lauf_ort(ort, kfg, zustand, trocken):
    breite, laenge = ort["breite"], ort["laenge"]
    heute = datetime.now(timezone.utc).date()
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
            if su <= datetime.now(timezone.utc):
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
    # billige: Open-Meteo zaehlt Ensemble-Member wie zusaetzliche
    # Variablen, 9 Variablen x 51 Member wiegen dreimal so viel wie 3 x 51.
    #
    # Gemessen am 18.08.2026: der Lauf kostete rund 5.500 Einheiten und riss
    # damit das Stundenlimit von 5.000 bei der vorletzten Anfrage. Ohne den
    # Windballast sind es rund 3.500 - der Lauf passt wieder, und es bleibt
    # Luft fuer einen Nachholversuch.
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
            sp = [zentrum.get(feldname("wind_speed_%dhPa" % WINDNIVEAU[s], m),
                              [None])[i] for m in mem]
            ri = [zentrum.get(feldname("wind_direction_%dhPa" % WINDNIVEAU[s], m),
                              [None])[i] for m in mem]
            sp = [x for x in sp if x is not None]
            ri = [x for x in ri if x is not None]
            if not sp:
                versatz[(t, s)] = (0.0, 0.0)
                continue
            # Richtungsmittel ueber Einheitsvektoren, nicht ueber Grad
            sx = sum(math.sin(math.radians(x)) for x in ri) / len(ri)
            cy = sum(math.cos(math.radians(x)) for x in ri) / len(ri)
            versatz[(t, s)] = versatz_km(sum(sp) / len(sp),
                                         math.degrees(math.atan2(sx, cy)) % 360.0,
                                         stunden)

    # Pass 2: versetzte Positionen
    versetzt_zellen, karte = set(), {}
    for t, info in abende.items():
        for s in SCHICHTEN:
            dx, dy = versatz[(t, s)]
            for schl, (la, lo) in info["punkte"].items():
                z = zelle(la + dy / 111.32, lo + dx / km_lon)
                karte[(t, s, schl)] = z
                versetzt_zellen.add(z)
    neu = versetzt_zellen - fan_zellen
    if kfg.get("advektion", True) and neu:
        print("   Pass 2: %d zusaetzliche Zellen" % len(neu), flush=True)
        feld.update(abfrage(neu, wolken, kfg["modell"], tage))

    ergebnisse = {}
    for t, info in abende.items():
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
        from zoneinfo import ZoneInfo
        dt = dt.astimezone(ZoneInfo(zone))
    except Exception:
        pass
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
            return

    # T-0058: Die Rechnung dauert Minuten - der Zustand wird deshalb NICHT
    # waehrenddessen veraendert.  Alles Neue sammelt sich hier und wird ganz
    # am Ende unter Sperre gegen den FRISCHEN Stand eingemergt.  Sonst
    # ueberschreibt dieser Lauf eine Bewertung, die der Poller in der
    # Zwischenzeit eingesammelt hat - nachgestellt und belegt.
    neue_abende = {}          # {ort: {tag: (eintrag, verlaufszeile)}}
    neue_alarme = {}          # {ort: {tag: buchung}}
    for ort in kfg["orte"]:
        name = ort["name"]
        # T-0056: Beim geplanten Lauf nur die Orte rechnen, deren Fenster
        # wirklich offen ist.  Ohne diesen Filter loeste EIN faelliger Ort
        # den vollen Abruf fuer ALLE aus - rund 3.500 Kontingenteinheiten je
        # Ort fuer Zahlen, die niemand angefordert hat, und ihre `laeufe`
        # wurden dabei als "vonhand" gebucht, was ihr eigenes Fenster fuer
        # den Tag verbraucht haette.  Bei drei Orten waere das Tagesbudget
        # nach einem Abendlauf weitgehend weg.
        # Ein Lauf VON HAND rechnet weiter alle Orte: wer ihn startet,
        # meint ihn (dieselbe Begruendung wie beim Fenster-Check oben).
        if a.geplant and name not in fenster:
            continue
        print("=== %s" % ort["anzeige"], flush=True)
        erg = lauf_ort(ort, kfg, zustand, a.trocken)
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
                lauf=str(date.today()))
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
                # rund 3.500 Kontingenteinheiten fuer Zahlen, die schon da
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

    # Der Modelllauf wird VOR der Buchung geholt - sie schreibt ihn mit.
    init = modelllauf(kfg["modell"])
    melde("   Modelllauf: %s" % (init or "unbekannt"))

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
        if geraeumt or gekuerzt:
            melde("   Geraeumt: %d alte Abende, %d Verlaufszeilen gekuerzt"
                  % (geraeumt, gekuerzt))

    melde("   Bilanz: %d HTTP-Anfragen, %d Ortsabrufe, bis %d Variablen, "
          "%d Tage, %d Member"
          % (LAST["anfragen"], LAST["orte"], LAST["variablen"],
             LAST["tage"], LAST["member"]))
    if not a.trocken:
        # T-0051 atomar UND T-0058 unter Sperre: `aktualisiere` laedt frisch,
        # wendet den Merge an und tauscht die Datei per os.replace ein.
        aktualisiere(zpfad, einmerge)
        print("\nZustand: %s" % zpfad)


if __name__ == "__main__":
    main()
