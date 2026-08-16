"""Die eigentliche Produktseite: was Andre abends anschaut.

Bewusst KEINE Prozentzahl als Hauptaussage.  Nach allem, was gemessen ist,
kann der Score aussergewoehnliche Abende von gewoehnlichen trennen
(Anreicherung n = 43, p = 0.0001), aber ob er unter den guten ordnet, ist
offen.  Eine Zahl wie "71 %" behauptet eine Trennschaerfe, die nicht belegt
ist.  Deshalb drei Stufen, an Perzentilen der Klimatologie festgemacht:

    unauffaellig   unter dem 80. Perzentil
    auffaellig     80. bis 95.
    selten         ab dem 95. (= s*, rund 18 Abende im Jahr)

Laeuft mit Prognosedaten (Standard) und mit historischen Abenden
(--rueckschau, Kennzeichnung "Rueckschau").

GESTALTUNG.  Hausstandard aus poisson-dor und rezept-grid, Werte in
stil/tokens.css, Begruendung in docs/ui-referenz.md.  Nur Dunkel.  Der
Aufbau folgt seit 16.08.2026 dem Entwurf in
docs/entwurf/handoff-ux-2026-08-16.md; die vier tragenden Entscheidungen:

1. ACHSE STATT BALKEN (unveraendert seit T-0010).  Der Balken war als
   Fuellstand von null gezeichnet.  Gemessen ueber zehn Abende lagen die
   Perzentile aber zwischen 0.592 und 0.971 - die unteren 59 % jedes
   Balkens waren tote Flaeche.  Eine Marke auf einer Achse codiert dieselbe
   Zahl als Position statt als Fuellstand.

2. ZONEN STATT ZWEI LINIEN.  Die zehn Abende liegen typischerweise weit
   unter beiden Schwellen.  Mit gestrichelten Linien allein sieht man
   Punkte im Nichts; mit gefuellten warmen Zonen sieht man, WIE WEIT es bis
   dorthin ist - und wenn ein seltener Abend kommt, klettert seine Marke
   sichtbar hinein.

3. DIE SEITE DARF SCHOEN SEIN.  Das Himmelsband (skripte/band.py) mischt
   zwischen einem stumpfen und einem gluehenden Farbsatz, Anteil
   median / s*.  Kein Dekor: eine gewoehnliche Woche bleibt stumpf.

4. DIE SEITE SAGT, OB EIN PUSH KOMMT.  Das war bis 16.08.2026 nirgends zu
   lesen, obwohl "kein Push" der haeufigste Zustand ist - rund 18 Abende im
   Jahr sind es nicht.  Ohne diesen Absatz sieht Schweigen aus wie ein
   Defekt.

VORAUSWAHL, entschieden gegen den Entwurf (T-0033).  Der Entwurf waehlt den
besten Abend im Fenster vor.  Andre hat am 16.08.2026 ausdruecklich das
Gegenteil verlangt ("das ausgewaehlte Datum ist nicht heute, sondern ein Tag
eher weit in der Zukunft - sollte natuerlich umgekehrt sein"), und das ist
auch die richtige Antwort auf die Frage, mit der man die Seite aufmacht:
"wie wird es HEUTE ABEND".  Vom Entwurf bleibt sein Eyebrow-Text: faellt die
Vorauswahl zufaellig auf den besten Abend, sagt die Seite das.
"""
import argparse
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import band  # noqa: E402
import faecher  # noqa: E402
import tokens  # noqa: E402
from alarm import begruendung  # noqa: E402
from schnitt import lade_feld, schnitt_neu, svg  # noqa: E402
from sonnen.geometrie import sonnenuntergang, tangentendistanz_km  # noqa: E402
from sonnen.score import SCHIRME  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WOCHENTAG = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
WOCHENTAG_LANG = ("Montag", "Dienstag", "Mittwoch", "Donnerstag",
                  "Freitag", "Samstag", "Sonntag")
MONAT = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
         "August", "September", "Oktober", "November", "Dezember")

# REGEL, teuer gelernt: HTML-Entities NUR im statischen Vorlagentext.
# Alles, was durch json.dumps in die Seite und dort ueber textContent
# ausgegeben wird, muss echtes UTF-8 sein - textContent dekodiert keine
# Entities und zeigt "unauff&auml;llig" woertlich an.  Betroffen waren
# stufe() (sofort sichtbar) und MONAT (waere erst im Maerz aufgefallen).
# Die Seite meldet charset=utf-8 und wird als UTF-8 geschrieben.
#
# Und im SVG gilt es doppelt: dort sind BENANNTE Entities gar nicht
# definiert.  &middot; laesst eine eigenstaendige .svg-Datei mit
# "Entity 'middot' not defined" abbrechen (16.08.2026).  Numerisch, also
# &#183;, ist ueberall gueltig.

# --- Ort als URL-Parameter: vorbereitet, NICHT gebaut ---------------------
#
# E0 hat "Ort als Parameter, auch fuer Freunde" entschieden, die
# Zweitreferenz macht es als ?sky=bilbao-es vor.  Das Ziel waere
# ?ort=berlin.  Hier steht nur, was dafuer anzufassen ist:
#
#   1. Ein Ortsregister {kuerzel: (Anzeigename, Breite, Laenge, Zeitzone,
#      Klimatologiedatei)}.  Gehoert nach konfig.json, nicht in den Code.
#   2. seite.py: der feste Dateiname score_berlin_g0.5_2022_2025.json in
#      main(), die Koordinaten 52.52/13.405 in lokalzeit(), und das feste
#      "Berlin" in der Ortspille der Topbar.
#   3. schnitt.py und faecher.py: die Modulkonstanten BREITE, LAENGE -
#      heute global, also pro Ort zu uebergeben statt zu setzen - und die
#      Ortsbeschriftung am Nullpunkt.
#   4. Erzeugung: je Ort eine Seite (web/berlin.html ...), weil GitHub Pages
#      statisch ausliefert und den Parameter nicht serverseitig aufloesen
#      kann.  Der Parameter waere dann eine Weiche im Skript, nicht zur
#      Laufzeit im Browser.
#
# Zwei offene Abhaengigkeiten: T-0013 (streut s* ueber Ankerorte weniger als
# 15 %? sonst braucht jeder Ort eine eigene Klimatologie) und T-0007
# (Gelaende im Fensterterm - ab freier Ortswahl zwingend).

# Geometrie der Achse in Pixeln.  Bewusst hier und nicht im CSS: Zonen,
# Verlaufslinie und Marken muessen exakt EIN Koordinatensystem benutzen,
# und das rechnet sich in Python einmal statt in CSS dreimal.
# ACHSE_PX steht nur noch IM STYLESHEET.  Die Marken werden in Prozent
# gesetzt, sonst haette der Wechsel auf 260 px im Desktopsatz jede einzelne
# verschoben - das war laut Handoff der einzige Umbau an bestehendem Code.
ACHSE_PX = 200
ACHSE_PX_GROSS = 260
SCHWELLE_SELTEN = 0.95
SCHWELLE_AUFFAELLIG = 0.80


def lokalzeit(tag):
    """Sonnenuntergang in Ortszeit - Sommerzeit nicht raten, sondern rechnen."""
    from datetime import datetime, timezone
    std, _ = sonnenuntergang(date.fromisoformat(tag), 52.52, 13.405)
    dt = datetime.fromisoformat(tag + "T00:00").replace(tzinfo=timezone.utc) \
        + timedelta(hours=std)
    try:
        from zoneinfo import ZoneInfo
        dt = dt.astimezone(ZoneInfo("Europe/Berlin"))
    except Exception:
        pass
    return dt.strftime("%H:%M")


def stufe(rang):
    """(Anzeigename, CSS-Klasse).  Klasse ASCII, Anzeige echtes UTF-8."""
    if rang >= SCHWELLE_SELTEN:
        return "selten", "selten"
    if rang >= SCHWELLE_AUFFAELLIG:
        return "auffällig", "auffaellig"
    return "unauffällig", "unauffaellig"


# Ausgeschrieben liest sich die Korpuszeile wie Sprache, als Ziffer wie ein
# Zaehlerstand.  Nur bis zwoelf - darueber wird das Wort laenger als die Zahl
# nuetzlich ist, und ein Fenster mit mehr als zwoelf Abenden gibt es nicht.
ANZAHL_WORT = {n: "%s ABENDE" % w for n, w in enumerate(
    ("NULL", "EIN", "ZWEI", "DREI", "VIER", "FUENF", "SECHS", "SIEBEN",
     "ACHT", "NEUN", "ZEHN", "ELF", "ZWOELF"))}


def kurzmarke(d, erster):
    """Tageszahl auf der Achse - mit Monat nur beim ersten und am Monatsersten."""
    if erster or d.day == 1:
        return "%d.%d." % (d.day, d.month)
    return "%d." % d.day


def satz(text):
    """Halbsatz aus begruendung() zu einem Satz machen: gross, mit Punkt."""
    if not text:
        return ""
    return text[0].upper() + text[1:] + "."


def _bilder(tag, feld, segmente, azimut, schirm):
    """(Vertikalschnitt, Faecherkarte) - beides aus dem FELD, keine Zahl daraus.

    Faellt eine der beiden aus, bleibt sie leer statt die Seite zu kippen:
    ein fehlendes Bild ist ein Schoenheitsfehler, eine fehlende Seite nicht.
    """
    schnitt_bild = karte_bild = ""
    try:
        schnitt_bild = schnitt_neu(tag, feld, segmente)[0]
    except Exception:                                            # noqa: BLE001
        pass
    try:
        hoehe = dict(SCHIRME)[schirm or SCHIRME[0][0]]
        karte_bild = faecher.svg(feld, azimut, schirm or SCHIRME[0][0],
                                 tangentendistanz_km(hoehe))
    except Exception:                                            # noqa: BLE001
        pass
    return schnitt_bild, karte_bild


def prognose_eintraege(ort_name, perzentil, s_stern):
    """Die kommenden Abende aus daten/zustand.json - was der Alarm gerechnet hat.

    WARUM ZWEI ZAHLEN JE ABEND, und warum sie nicht dasselbe sind:

      Wahrscheinlichkeit  Anteil der Ensemble-Member ueber s*.  "Wie sicher?"
      Perzentil           Klimatologischer Rang des Member-MEDIANS. "Wie selten?"

    Die Achse der Seite ist auf den Perzentilrang gebaut (Zonen bei 80. und
    95.), also steht der Punkt dort.  Die Wahrscheinlichkeit ist die Zahl,
    nach der Andre gefragt hat, und steht als Text daneben.

    Die Bilder rechnen aus dem gespeicherten MEDIANFELD.  Das ist fuer das
    BILD richtig und fuer die ZAHL falsch: S ist ein Produkt nichtlinearer
    Terme, der Score des Medianfelds ist nicht der Median der Scores
    (Jensen).  Deshalb kommt das Bild aus dem Feld und jede Zahl aus dem
    Zustand.
    """
    zp = os.path.join(BASIS, "daten", "zustand.json")
    if not os.path.exists(zp):
        return []
    with open(zp) as f:
        zustand = json.load(f)
    abende = (zustand.get(ort_name) or {}).get("abende", {})
    aus = []
    for t in sorted(abende):
        e = abende[t]
        if e.get("p") is None or e.get("median") is None:
            continue                       # bewertet, aber nie prognostiziert
        schnitt_bild, karte_bild = ("", "")
        if e.get("feld"):
            schnitt_bild, karte_bild = _bilder(
                t, e["feld"], e.get("segmente"), e.get("azimut", 270.0),
                e.get("schirm"))
        rang = perzentil(e["median"])
        name, klasse = stufe(rang)
        d = date.fromisoformat(t)
        aus.append({"tag": t, "wt": WOCHENTAG[d.weekday()],
                    "kurz": kurzmarke(d, not aus),
                    "lang": "%s, %d. %s" % (WOCHENTAG_LANG[d.weekday()],
                                            d.day, MONAT[d.month - 1]),
                    "p": rang, "stufe": name, "klasse": klasse,
                    "zeit": lokalzeit(t), "svg": schnitt_bild,
                    "karte": karte_bild,
                    "band": band.svg(e["median"], s_stern, len(aus)),
                    "grund": satz(begruendung(e)),
                    "wahrsch": e["p"], "vorlauf_h": e.get("dt_h")})
    return aus


def rueckschau_eintraege(von, tage, klima, perzentil, s_stern):
    """Historische Abende aus dem Blockcache - das Entwurfsmuster von T-0010.

    Kein Prognosezustand, also auch keine Wahrscheinlichkeit: es war nichts
    vorherzusagen.  Der Score des Feldes traegt hier beides, Achse und Band -
    das ist zulaessig, weil es kein Ensemble gibt, ueber das zu mitteln waere.
    """
    aus = []
    liste = [(date.fromisoformat(von) + timedelta(days=k)).isoformat()
             for k in range(tage)]
    for t in [x for x in liste if x in klima]:
        feld = lade_feld(t)
        if not feld:
            continue
        try:
            _, s, det = svg(t, feld, kompakt=True)
        except Exception:                                        # noqa: BLE001
            continue
        schirm = (det or {}).get("schirm")
        # score() liefert keinen Azimut zurueck - er wird hier neu gerechnet.
        # Ein Vorgabewert (270 Grad, exakt West) waere im August 19 Grad
        # daneben und schoebe den Strahl auf der Faecherkarte sichtbar
        # ueber die falschen Zellen.
        _, azimut = sonnenuntergang(date.fromisoformat(t), 52.52, 13.405)
        schnitt_bild, karte_bild = _bilder(
            t, feld, (det or {}).get("segmente"), azimut, schirm)
        p = perzentil(s)
        name, klasse = stufe(p)
        d = date.fromisoformat(t)
        aus.append({"tag": t, "wt": WOCHENTAG[d.weekday()],
                    "kurz": kurzmarke(d, not aus),
                    "lang": "%s, %d. %s" % (WOCHENTAG_LANG[d.weekday()],
                                            d.day, MONAT[d.month - 1]),
                    "p": p, "stufe": name, "klasse": klasse,
                    "zeit": lokalzeit(t), "svg": schnitt_bild,
                    "karte": karte_bild,
                    "band": band.svg(s, s_stern, len(aus)),
                    "grund": satz(begruendung({
                        "schirm": schirm,
                        "A": (det or {}).get("A"),
                        "weg": (det or {}).get("weg"),
                        "sicht": (det or {}).get("sicht")})),
                    "wahrsch": None, "vorlauf_h": None})
    return aus


VORLAGE = """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>Streulicht</title><style>
__TOKENS__
*{box-sizing:border-box}
html{color-scheme:dark}
body{margin:0;background:var(--papier);color:var(--tinte);
 font-family:var(--schrift);font-size:var(--grad-basis);
 line-height:var(--zeilen-basis);letter-spacing:var(--sperrung-eng);
 font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
.rahmen{max-width:390px;margin:0 auto;padding-bottom:var(--s8)}
/* Zwei Fassungen, EIN Dokument.  Was nur die eine braucht, traegt eine der
   beiden Klassen; der Breakpoint schaltet sie um.  Zwei Dateien waeren
   sauberer zu lesen, kosteten aber eine zweite URL und eine Weiche beim
   Ausliefern - fuer ein privates Werkzeug der schlechtere Tausch. */
.nurgross{display:none}

/* --- Kopfleiste ----------------------------------------------------- */
/* Klebend, weil die Seite gerollt wird und der Ort dabei aus dem Bild
   liefe - und der Ort ist ab dem zweiten Nutzer die wichtigste Angabe
   ueberhaupt (die Prognose gilt fuer genau einen Punkt). */
.topbar{position:sticky;top:0;z-index:20;
 background:rgba(0,0,0,.72);
 -webkit-backdrop-filter:blur(18px) saturate(1.4);
 backdrop-filter:blur(18px) saturate(1.4);
 border-bottom:1px solid var(--karte)}
.topbar-inhalt{display:flex;align-items:center;justify-content:space-between;
 gap:24px;padding:calc(14px + env(safe-area-inset-top)) 18px 12px}
.wortmarke{display:flex;align-items:baseline;gap:12px}
.marke-wort{margin:0;font-size:17px;font-weight:800;
 letter-spacing:var(--sperrung-enger)}
.ortspille{padding:3px 11px;border-radius:var(--radius-pille);
 background:var(--karte);color:var(--tinte2);font-size:12px;font-weight:700}
.leiste-nav{display:none;align-items:center;gap:26px}

/* --- Korpuszeile: benennt den Bestand, statt ihn vorauszusetzen ----- */
.korpus{margin:0;padding:20px 18px 0;color:var(--gedaempft);
 font-size:12px;font-weight:700;letter-spacing:var(--sperrung-label);
 text-transform:uppercase}

/* --- Kopfbild: Hero und Himmelsband ---------------------------------- */
/* Auf dem Telefon stehen sie UNTEREINANDER (Text, dann Band, dann
   Bandfuss) - die Reihenfolge macht `order`, nicht das Markup, damit die
   Desktopfassung dieselben Knoten uebereinanderlegen kann. */
.kopfbild{display:flex;flex-direction:column;margin-top:16px}
.heroinhalt{order:1;padding:0 18px}
.bandflaeche{order:2;height:76px;margin-top:20px;line-height:0}
.bandflaeche svg{display:block;width:100%;height:100%}
.bandfuss{order:3;margin:8px 18px 0;color:var(--gedaempft);font-size:12px}
.schleier{display:none}
.etikett{margin:0;color:var(--gedaempft);font-size:12px;font-weight:700;
 letter-spacing:var(--sperrung-label);text-transform:uppercase}
.datum{margin:2px 0 0;font-size:23px;font-weight:700;
 letter-spacing:var(--sperrung-enger);color:var(--tinte)}
.stufe{margin:8px 0 0;font-size:44px;font-weight:800;line-height:1.02;
 letter-spacing:-.04em}
.grund{margin:6px 0 0;color:var(--tinte2);font-size:14px;text-wrap:pretty}
.zahlen{margin:10px 0 0;color:var(--gedaempft);font-size:13px}
/* Die drei Zahlen zweimal im Dokument: als Punktkette (Telefon) und als
   beschriftete Bloecke (Desktop).  Bewusst zwei Darstellungen und EINE
   Quelle - die Wortstellung unterscheidet sich ("Sonnenuntergang 20:30 Uhr"
   gegen Label SONNENUNTERGANG ueber "20:30 Uhr"), das laesst sich nicht mit
   CSS ineinander ueberfuehren.  waehle() schreibt beide. */
.kennzahlen{display:none;gap:56px;margin:26px 0 0}
.kzlabel{margin:0;color:var(--gedaempft);font-size:11px;font-weight:700;
 letter-spacing:var(--sperrung-label);text-transform:uppercase}
.kzwert{margin:3px 0 0;font-size:26px;font-weight:700;
 letter-spacing:var(--sperrung-enger);color:var(--tinte)}
.selten{color:var(--akzent-tinte)}
.auffaellig{color:var(--akzent)}
.unauffaellig{color:var(--gedaempft)}

/* --- Zeitachse ------------------------------------------------------ */
.achsenkopf{display:flex;justify-content:space-between;
 padding:0 18px 10px;font-size:12px;color:var(--gedaempft)}
.achsenkopf b{font-weight:700;letter-spacing:var(--sperrung-label);
 text-transform:uppercase}
.achsenkopf span{font-weight:400}
.achsenblock{margin-top:26px}
/* Die Achsenhoehe steht im CSS, die Marken stehen in PROZENT.  Vorher
   rechnete Python `top:%.1fpx` aus einer Konstante - bei zwei Hoehen (200
   auf dem Telefon, 260 auf dem Desktop) haette keine einzige Marke mehr
   gestimmt.  Prozent loest zugleich die Zonen: 5 % und 15 % sind bei 200 px
   genau 10 und 30, bei 260 px genau 13 und 39 - also exakt die Masse aus
   beiden Entwuerfen, ohne sie zweimal zu pflegen. */
.achse{position:relative;height:__ACHSE__px;margin:0 18px}
.zone{position:absolute;left:0;right:0;pointer-events:none}
.zone-selten{top:0;height:5%;background:rgba(255,159,10,.18);
 border-bottom:1px solid var(--akzent)}
.zone-auffaellig{top:5%;height:15%;background:rgba(255,159,10,.07);
 border-bottom:1px dashed var(--gitter)}
.zonenname{position:absolute;right:0;transform:translateY(-100%);
 padding-bottom:2px;font-size:11px;font-weight:700;letter-spacing:.04em;
 pointer-events:none}
.linie{position:absolute;inset:0;width:100%;height:100%;
 overflow:visible;pointer-events:none}
.marken{position:absolute;inset:0;display:flex}
.marke{flex:1;min-width:0;height:100%;position:relative;border:0;
 background:transparent;border-radius:var(--radius-mikro);padding:0;
 cursor:pointer;font:inherit;letter-spacing:inherit;color:var(--gedaempft)}
.fahne{position:absolute;left:50%;width:1px;margin-left:-.5px;bottom:0;
 background:linear-gradient(to bottom,rgba(142,142,147,.16),transparent)}
.punkt{position:absolute;left:50%;width:11px;height:11px;
 margin:-5.5px 0 0 -5.5px;border:1.5px solid currentColor;
 border-radius:var(--radius-pille);background:var(--papier);
 transition:transform var(--zeit) var(--kurve),box-shadow var(--zeit)}
.selten .punkt{background:var(--akzent-tinte);
 box-shadow:0 0 12px rgba(255,179,64,.7)}
.marke.an .fahne{width:2px;margin-left:-1px;
 background:linear-gradient(to bottom,rgba(255,179,64,.62),transparent)}
.marke.an .punkt{transform:scale(1.45)}
/* Die Rangzahl unter der Marke gibt es nur auf dem grossen Schirm.  Auf
   36 px Spaltenbreite ist dafuer kein Platz - genau deshalb musste man auf
   dem Telefon jeden Abend antippen, um sein Perzentil zu erfahren. */
.rang{display:none;position:absolute;left:0;right:0;font-size:12px;
 font-weight:600;letter-spacing:0;text-align:center;color:var(--gedaempft);
 transition:color var(--zeit) var(--kurve)}
.marke.an .rang{color:var(--tinte)}
@media (hover:hover){.marke:hover .punkt{transform:scale(1.2)}}
.marke:focus-visible{outline:2px solid var(--akzent);outline-offset:2px}
/* Die Beschriftung steht in einer EIGENEN Flexzeile mit denselben
   flex:1-Spalten.  Im Knopf saesse sie sonst innerhalb der Tastflaeche und
   verschoebe die Marken. */
.achsenfuss{display:flex;margin:8px 18px 0}
.achsenfuss div{flex:1;min-width:0;text-align:center}
.achsenfuss .wt{font-size:11px;color:var(--gedaempft)}
.achsenfuss .dt{font-size:12px;font-weight:600;color:var(--tinte2)}
.achsenfuss .an .wt{color:var(--tinte2)}
.achsenfuss .an .dt{color:var(--tinte)}

/* --- Grafikkarten --------------------------------------------------- */
.grafiken{display:block}
.karte{margin:26px 18px 0;padding:14px 12px 12px;background:var(--karte);
 border:1px solid var(--achse);border-radius:var(--radius-karte);
 box-shadow:var(--schatten-ruhe)}
.karte + .karte{margin-top:16px}
.kartentitel{margin:0 4px 10px;color:var(--gedaempft);font-size:12px;
 font-weight:700;letter-spacing:var(--sperrung-label);text-transform:uppercase}
.karte svg{display:block;width:100%;height:auto}
.kartenfuss{margin:10px 4px 0;color:var(--gedaempft);font-size:12px;
 text-wrap:pretty}

/* --- Fusstext und Push-Auskunft ------------------------------------- */
.schluss{display:block}
.fuss{margin:26px 18px 0;color:var(--gedaempft);font-size:13px;
 line-height:1.55;text-wrap:pretty}
.fuss b{color:var(--tinte2)}
/* Ohne diesen Verweis waere die Bilanzseite unerreichbar - eine Seite, die
   nur kennt, wer die URL kennt, ist keine. */
.weiter{display:flex;align-items:center;justify-content:center;
 margin:16px 18px 0;min-height:var(--tastflaeche);padding:0 18px;
 border-radius:var(--radius-pille);border:1px solid var(--achse);
 color:var(--tinte2);font-size:14px;font-weight:600;text-decoration:none}
.push{margin:22px 18px 0;padding:14px 16px;background:var(--karte);
 border-radius:var(--radius-kachel);color:var(--tinte2);font-size:13px;
 line-height:1.55;text-wrap:pretty}

/* ====================================================================
   DESKTOPFASSUNG.  Der Inhalt ist identisch - kein Bauteil, keine Zahl,
   kein Satz kommt hinzu.  Was sich aendert, ist die Anordnung an den fuenf
   Stellen, an denen 390 px die Einschraenkung waren.
   1000 px als Schwelle: darunter passt das Grafikraster (2 x 420 + 20) nicht.
   ==================================================================== */
@media (min-width:1000px){
 .rahmen{max-width:none;padding-bottom:72px}
 .nurgross{display:inline}
 .nurklein{display:none}
 .spalte{max-width:var(--breite-gross);margin:0 auto;
  padding:0 var(--rand-gross)}

 .topbar-inhalt{height:56px;padding:0 var(--rand-gross);
  max-width:var(--breite-gross);margin:0 auto}
 .leiste-nav{display:flex}
 .leiste-korpus{color:var(--gedaempft);font-size:12px;font-weight:700;
  letter-spacing:var(--sperrung-label);text-transform:uppercase}
 .leiste-nav a{color:var(--tinte2);font-size:14px;font-weight:600;
  text-decoration:none}
 .korpus{display:none}

 /* Das Himmelsband wird der Kopf der Seite: randlos, 400 px hoch, mit dem
    Hero darauf.  Zwei Schleier, weil das Band seine Helligkeit aendern
    SOLL - der waagerechte haelt die linke Haelfte dunkel, damit der Text
    an einem gluehenden Abend lesbar bleibt, der senkrechte setzt oben und
    unten ab.  Auf 76 px sah man den Unterschied zwischen einem stumpfen
    und einem seltenen Abend gar nicht. */
 .kopfbild{display:block;position:relative;height:400px;overflow:hidden;
  margin-top:0}
 .bandflaeche{position:absolute;inset:0;height:auto;margin:0}
 .schleier{display:block;position:absolute;inset:0;pointer-events:none}
 .s-quer{background:linear-gradient(100deg,rgba(0,0,0,.92) 0%,
  rgba(0,0,0,.74) 34%,rgba(0,0,0,.18) 68%,rgba(0,0,0,.35) 100%)}
 .s-hoch{background:linear-gradient(to bottom,rgba(0,0,0,.45) 0%,
  transparent 26%,transparent 62%,rgba(0,0,0,.7) 100%)}
 /* box-sizing ist hier nicht optional: height:100% plus 38 px Polsterung
    ergaebe unter content-box 438 px in einer 400er Section mit
    overflow:hidden - die Bodenluft verschwaende an JEDER Fensterbreite.
    Der Reset ganz oben loest es mit. */
 .heroinhalt{position:relative;height:100%;max-width:var(--breite-gross);
  margin:0 auto;padding:0 var(--rand-gross) 38px;display:flex;
  flex-direction:column;justify-content:flex-end}
 .datum{margin:6px 0 0;font-size:28px}
 .stufe{margin:10px 0 0;font-size:76px;line-height:1}
 .grund{margin:12px 0 0;max-width:46ch;font-size:17px;line-height:1.45}
 .zahlen{display:none}
 .kennzahlen{display:flex}
 /* Die Bandbeschriftung sitzt oben rechts IM Hero, muss also mit der
    Inhaltsspalte fluchten und nicht mit dem Fensterrand. */
 .bandfuss{position:absolute;top:26px;margin:0;
  right:max(var(--rand-gross),
   calc((100% - var(--breite-gross)) / 2 + var(--rand-gross)))}

 .achsenblock{margin-top:48px}
 .achsenkopf{padding:0 0 14px;align-items:baseline}
 .achsenkopf span{font-size:13px}
 .achse{height:__ACHSE_GROSS__px;margin:0}
 .punkt{width:12px;height:12px;margin:-6px 0 0 -6px}
 .marke.an .punkt{transform:scale(1.5)}
 .selten .punkt{box-shadow:0 0 14px rgba(255,179,64,.7)}
 .rang{display:block}
 .achsenfuss{margin:12px 0 0}
 .achsenfuss .wt{font-size:12px}
 .achsenfuss .dt{font-size:13px}

 /* minmax(420px,...) statt eines festen Verhaeltnisses: die Faecherkarte
    ist die schmalere Spalte, ihre Beschriftung sitzt mit 13 Einheiten in
    einer 420er viewBox und skaliert mit.  Ohne untere Schranke fiel sie in
    einem halbbreiten Fenster auf 6,9 px - dieselbe Fehlerklasse, die
    T-0010 schon einmal behoben hat.  Unterhalb ~900 px bricht das Raster
    auf eine Spalte um, die Grafiken werden dabei GROESSER. */
 .grafiken{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));
  gap:20px;align-items:start;margin:44px 0 0}
 .karte{margin:0;padding:16px 16px 14px}
 .karte + .karte{margin-top:0}
 .kartentitel{margin:0 0 12px}
 .kartenfuss{margin:12px 2px 0}
 .schluss{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));
  gap:20px;align-items:start;margin:34px 0 0}
 .fuss{margin:0;font-size:14px;line-height:1.6}
 .push{margin:0;padding:16px 18px;font-size:14px;line-height:1.6}
 .weiter{display:none}
}

@media (prefers-reduced-motion:reduce){
 *{transition:none!important;animation:none!important}}
</style></head><body>
<div class="rahmen">
<header class="topbar"><div class="topbar-inhalt">
<div class="wortmarke"><p class="marke-wort">Streulicht</p>
<span class="ortspille">__ORT__</span></div>
<nav class="leiste-nav"><span class="leiste-korpus">__KORPUS__</span>
<a href="bisher.html">Was bisher gemessen ist</a></nav>
</div></header>

<p class="korpus">__KORPUS__</p>

<main>
<section class="kopfbild">
<div class="bandflaeche" id="bandflaeche">__BAND__</div>
<i class="schleier s-quer"></i><i class="schleier s-hoch"></i>
<div class="heroinhalt">
<p class="etikett" id="etikett">__ETIKETT__</p>
<h1 class="datum" id="datum">__DATUM__</h1>
<p class="stufe __KLASSE__" id="stufe">__STUFE__</p>
<p class="grund" id="grund">__GRUND__</p>
<p class="zahlen" id="zahlen">__ZAHLEN__</p>
<div class="kennzahlen">
<div><p class="kzlabel">Perzentil des Jahres</p>
<p class="kzwert" id="kz0">__KZ0__</p></div>
<div><p class="kzlabel">Wahrscheinlichkeit</p>
<p class="kzwert" id="kz1">__KZ1__</p></div>
<div><p class="kzlabel">Sonnenuntergang</p>
<p class="kzwert" id="kz2">__KZ2__</p></div>
</div></div>
<p class="bandfuss">Lichteindruck, schematisch &#8212; aus dem Score dieses
Abends.</p>
</section>

<div class="spalte">
<section class="achsenblock">
<div class="achsenkopf"><b>__ANZAHL_WORT__</b><span>Perzentil des
Jahres<span class="nurgross"> &#183; &#8592; &#8594; bl&auml;ttert</span></span></div>
<div class="achse">
<i class="zone zone-selten"></i><i class="zone zone-auffaellig"></i>
<b class="zonenname" style="top:5%;color:var(--akzent-tinte)">SELTEN 95.</b>
<b class="zonenname" style="top:20%;color:var(--gedaempft)">AUFF&Auml;LLIG 80.</b>
<svg class="linie" viewBox="0 0 100 100" preserveAspectRatio="none"
 aria-hidden="true"><polyline points="__LINIE__" fill="none"
 stroke="__LINIENFARBE__" stroke-width=".7"
 vector-effect="non-scaling-stroke"/></svg>
<div class="marken">__MARKEN__</div></div>
<div class="achsenfuss">__ACHSENFUSS__</div></section>

<section class="grafiken">
<div class="karte"><p class="kartentitel">Der Weg des Lichts</p>
<div id="schnitt">__SCHNITT__</div>
<p class="kartenfuss">Der Strahl, der bei Sonnenuntergang von Westen
ankommt, und die Wolkenschichten auf seinem Weg. H&ouml;he
__UEBERHOEHT__-fach &uuml;berh&ouml;ht.</p></div>

<div class="karte"><p class="kartentitel">Von oben</p>
<div id="karte">__KARTE__</div>
<p class="kartenfuss">Die Wolkendecke westlich von __ORT__ auf dem
Abfrage&shy;f&auml;cher, und der Azimut des Sonnenuntergangs.</p></div>
</section>

<section class="schluss">
<p class="fuss">Die Stufe kommt aus der Position in der Jahresverteilung:
<b>selten</b> ab dem 95. Perzentil (rund 18 Abende im Jahr),
<b>auff&auml;llig</b> ab dem 80. Bewusst keine Prozentzahl &mdash; belegt ist,
dass der Score au&szlig;ergew&ouml;hnliche Abende von gew&ouml;hnlichen
trennt, nicht dass er unter den guten ordnet.</p>

<p class="push">__PUSHTEXT__</p>
</section>

<a class="weiter" href="bisher.html">Was bisher gemessen ist</a>
</div></main></div>
<script>
const META=__META__, BESTER=__BESTER__;
const marken=[...document.querySelectorAll(".marke")];
const fuesse=[...document.querySelectorAll(".achsenfuss div")];
let gewaehlt=__GEWAEHLT__;
function waehle(i){
  gewaehlt=i;
  marken.forEach((x,k)=>x.classList.toggle("an",k===i));
  fuesse.forEach((x,k)=>x.classList.toggle("an",k===i));
  const m=META[i];
  document.getElementById("etikett").textContent=
    i===BESTER?"Bester Abend im Fenster":"Gew\\u00e4hlter Abend";
  document.getElementById("datum").textContent=m.lang;
  const st=document.getElementById("stufe");
  st.textContent=m.stufe; st.className="stufe "+m.klasse;
  document.getElementById("grund").textContent=m.grund||"";
  // Drei Zahlen, und sie duerfen nicht verwechselt werden: das Perzentil
  // ist der klimatologische Rang des Member-Medians ("wie selten"), die
  // Wahrscheinlichkeit der Anteil der Ensemble-Member ueber der Schwelle
  // ("wie sicher").  In der Rueckschau gibt es nur das Perzentil - dort
  // war nichts vorherzusagen.
  const hatW=m.wahrsch!==null&&m.wahrsch!==undefined;
  const rang=Math.round(m.p*100)+".";
  const wahr=hatW?Math.round(m.wahrsch*100)+" %":"\\u2014";
  const teile=[rang+" Perzentil des Jahres"];
  if(hatW) teile.push(Math.round(m.wahrsch*100)+" % Wahrscheinlichkeit");
  teile.push("Sonnenuntergang "+m.zeit+" Uhr");
  document.getElementById("zahlen").textContent=teile.join(" \\u00b7 ");
  document.getElementById("kz0").textContent=rang;
  document.getElementById("kz1").textContent=wahr;
  document.getElementById("kz2").textContent=m.zeit+" Uhr";
  document.getElementById("bandflaeche").innerHTML=m.band;
  document.getElementById("schnitt").innerHTML=m.svg;
  document.getElementById("karte").innerHTML=m.karte;
}
marken.forEach((b,i)=>b.onclick=()=>waehle(i));
// Pfeiltasten: auf einem Geraet mit Tastatur ist Durchblaettern die
// natuerliche Bewegung durch die Abende.  preventDefault NUR bei einem
// Treffer, sonst nimmt die Seite auch das Rollen mit den Pfeilen weg.
document.addEventListener("keydown",e=>{
  let z=gewaehlt;
  if(e.key==="ArrowRight") z=Math.min(META.length-1,gewaehlt+1);
  else if(e.key==="ArrowLeft") z=Math.max(0,gewaehlt-1);
  else return;
  e.preventDefault();
  if(z!==gewaehlt) waehle(z);
});
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--von", default="2025-08-25")
    ap.add_argument("--tage", type=int, default=10)
    ap.add_argument("--rueckschau", action="store_true",
                    help="historische Abende statt der Prognose (Entwurfsmuster)")
    ap.add_argument("--ort", default="berlin")
    ap.add_argument("--konfig", default=os.path.join(BASIS, "konfig.json"))
    a = ap.parse_args()

    with open(a.konfig) as f:
        kfg = json.load(f)
    s_stern = kfg["schwelle_score"]
    schwelle_p = kfg["schwelle_wahrscheinlichkeit"]
    ort = next((o for o in kfg["orte"] if o["name"] == a.ort), None)
    anzeige = (ort or {}).get("anzeige", a.ort.capitalize())

    with open(os.path.join(BASIS, "daten",
                           "score_berlin_g0.5_2022_2025.json")) as f:
        klima = json.load(f)
    alle = sorted(v["s"] for v in klima.values())

    def perzentil(s):
        return sum(1 for x in alle if x < s) / len(alle)

    if a.rueckschau:
        eintraege = rueckschau_eintraege(a.von, a.tage, klima, perzentil,
                                         s_stern)
    else:
        eintraege = prognose_eintraege(a.ort, perzentil, s_stern)
        if not eintraege:
            print("Keine Prognose in daten/zustand.json - der Alarmlauf war "
                  "noch nicht erfolgreich.\nEntwurfsmuster mit historischen "
                  "Abenden: --rueckschau", file=sys.stderr)
            raise SystemExit(2)
    if not eintraege:
        raise SystemExit("keine Abende")

    # Vorauswahl: der NAECHSTE Abend (siehe Modul-Docstring, T-0033).  Die
    # Liste ist aufsteigend sortiert; ist der Lauf aelter als sein letzter
    # Abend, faellt die Wahl auf den letzten.
    heute_iso = date.today().isoformat()
    kuenftig = [i for i, e in enumerate(eintraege) if e["tag"] >= heute_iso]
    gewaehlt = kuenftig[0] if kuenftig else len(eintraege) - 1
    bester = max(range(len(eintraege)), key=lambda i: eintraege[i]["p"])

    n = len(eintraege)
    # Die Korpuszeile nennt eine DATUMSSPANNE, keine Vorlauftage.  Der
    # Entwurf sah "2 BIS 10 TAGE" vor; gerechnet aus dt_h ergab das "0 BIS
    # 0 TAGE", weil der erste Abend am Lauftag selbst liegt (dt_h ~ 12) und
    # das Runden ihn auf null drueckt.  Ein Datum kann nicht falsch runden.
    korpus = "%d ABENDE %s &#183; %s BIS %s" % (
        n, "R&Uuml;CKGERECHNET" if a.rueckschau else "VORAUSGERECHNET",
        date.fromisoformat(eintraege[0]["tag"]).strftime("%d.%m."),
        date.fromisoformat(eintraege[-1]["tag"]).strftime("%d.%m."))

    # PROZENT, nicht Pixel: dieselbe Marke muss in einer 200 px und in einer
    # 260 px hohen Achse sitzen.  y(p) ist damit dimensionslos und die
    # Achsenhoehe eine reine CSS-Angabe.
    y = lambda p: (1.0 - p) * 100.0                               # noqa: E731
    marken = "".join(
        '<button class="marke %s%s" data-i="%d" '
        'aria-label="%s, %s, %d. Perzentil">'
        '<i class="fahne" style="top:%.3f%%"></i>'
        '<i class="punkt" style="top:%.3f%%"></i>'
        '<b class="rang" style="top:calc(%.3f%% + 14px)">%d.</b></button>'
        % (e["klasse"], " an" if i == gewaehlt else "", i,
           e["lang"], e["stufe"], round(e["p"] * 100),
           y(e["p"]), y(e["p"]), y(e["p"]), round(e["p"] * 100))
        for i, e in enumerate(eintraege))
    achsenfuss = "".join(
        '<div%s><div class="wt">%s</div><div class="dt">%s</div></div>'
        % (' class="an"' if i == gewaehlt else "", e["wt"], e["kurz"])
        for i, e in enumerate(eintraege))
    linie = " ".join("%.2f,%.2f" % ((i + 0.5) / n * 100.0,
                                    (1.0 - e["p"]) * 100.0)
                     for i, e in enumerate(eintraege))

    # Push-Auskunft.  Das ist der Absatz, den die alte Seite nirgends hatte -
    # und "kein Push" ist der haeufigste Zustand.  Ohne ihn sieht Schweigen
    # aus wie ein Defekt.
    hoechste = max((e["wahrsch"] or 0.0) for e in eintraege)
    if a.rueckschau:
        pushtext = ("R&uuml;ckschau: hier wurde nichts vorhergesagt und "
                    "nichts gepusht.")
    elif hoechste >= schwelle_p:
        pushtext = ("Mindestens ein Abend rei&szlig;t die Schwelle von "
                    "%d&nbsp;%% (h&ouml;chstens %d&nbsp;%%). Der Push geht "
                    "morgens um 7:30&nbsp;Uhr raus &mdash; einmal, nicht "
                    "zweimal." % (round(schwelle_p * 100), round(hoechste * 100)))
    else:
        pushtext = ("Kein Abend im Fenster rei&szlig;t die Schwelle von "
                    "%d&nbsp;%% (h&ouml;chstens %d&nbsp;%%). Es kommt kein "
                    "Push. Das ist der normale Zustand: rund 18 Abende im "
                    "Jahr sind es nicht."
                    % (round(schwelle_p * 100), round(hoechste * 100)))

    # ANFANGSZUSTAND STEHT IM MARKUP, nicht erst im Skript.  Vorher baute
    # waehle() beim Laden Hero, Band und beide Bilder auf; bis dahin war die
    # Seite leer, und ohne JavaScript blieb sie es.  Serverseitig gefuellt
    # ist sie sofort lesbar, und das Skript aendert nur noch bei einem Klick.
    from html import escape
    g = eintraege[gewaehlt]
    zahlen = ["%d. Perzentil des Jahres" % round(g["p"] * 100)]
    if g["wahrsch"] is not None:
        zahlen.append("%d %% Wahrscheinlichkeit" % round(g["wahrsch"] * 100))
    zahlen.append("Sonnenuntergang %s Uhr" % g["zeit"])
    # Dieselben Werte noch einmal als beschriftete Kennzahlen (Desktopsatz).
    # In der Rueckschau gibt es keine Wahrscheinlichkeit - dort steht ein
    # Gedankenstrich, keine Null: null Prozent waere eine Aussage.
    kz = ["%d." % round(g["p"] * 100),
          "%d %%" % round(g["wahrsch"] * 100) if g["wahrsch"] is not None
          else "&#8212;",
          "%s Uhr" % g["zeit"]]

    meta = json.dumps([{k: e[k] for k in ("tag", "lang", "p", "stufe",
                                          "klasse", "zeit", "wahrsch",
                                          "vorlauf_h", "grund", "svg",
                                          "karte", "band")}
                       for e in eintraege], ensure_ascii=False)

    html = (VORLAGE
            .replace("__TOKENS__", tokens.quelltext())
            .replace("__ORT__", anzeige)
            .replace("__KORPUS__", korpus)
            .replace("__ANZAHL_WORT__", ANZAHL_WORT.get(n, "%d ABENDE" % n))
            .replace("__ACHSE_GROSS__", str(ACHSE_PX_GROSS))
            .replace("__ACHSE__", str(ACHSE_PX))
            .replace("__LINIE__", linie)
            .replace("__LINIENFARBE__", tokens.werte()["--achse"])
            .replace("__MARKEN__", marken)
            .replace("__ACHSENFUSS__", achsenfuss)
            .replace("__UEBERHOEHT__", "%.0f" % ueberhoehung_neu())
            .replace("__PUSHTEXT__", pushtext)
            .replace("__ETIKETT__", "Bester Abend im Fenster"
                     if gewaehlt == bester else "Gew&auml;hlter Abend")
            .replace("__DATUM__", escape(g["lang"]))
            .replace("__KLASSE__", g["klasse"])
            .replace("__STUFE__", escape(g["stufe"]))
            .replace("__GRUND__", escape(g["grund"] or ""))
            .replace("__ZAHLEN__", escape(" \u00b7 ".join(zahlen)))
            .replace("__BAND__", g["band"])
            .replace("__SCHNITT__", g["svg"])
            .replace("__KARTE__", g["karte"])
            .replace("__KZ0__", kz[0])
            .replace("__KZ1__", kz[1])
            .replace("__KZ2__", kz[2])
            .replace("__META__", meta)
            .replace("__BESTER__", str(bester))
            .replace("__GEWAEHLT__", str(gewaehlt)))
    ziel = os.path.join(BASIS, "web", "index.html")
    with open(ziel, "w", encoding="utf-8") as f:
        f.write(html)
    print("geschrieben: %s (%d Abende, %.2f MB, gewaehlt %s, bester %s)"
          % (ziel, n, os.path.getsize(ziel) / 1e6,
             eintraege[gewaehlt]["tag"], eintraege[bester]["tag"]))


def ueberhoehung_neu():
    """Wieviel die Hoehe im neuen Schnitt gestreckt ist.

    Muss aus der Flaeche gerechnet werden, nicht abgeschrieben: die Zahl
    steht als Aussage auf der Seite, und eine handnotierte Zahl neben einer
    geaenderten Geometrie ist genau die Sorte Fehler, die niemand sieht.
    """
    from schnitt import FL_NEU, XMAX, YMAX
    px_pro_km_x = FL_NEU["br"] / XMAX
    px_pro_km_y = FL_NEU["ho"] / YMAX
    return px_pro_km_y / px_pro_km_x


if __name__ == "__main__":
    main()
