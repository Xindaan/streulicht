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
ACHSE_PX = 200
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

/* --- Topbar -------------------------------------------------------- */
/* Klebend, weil die Seite gerollt wird und der Ort dabei aus dem Bild
   liefe - und der Ort ist ab dem zweiten Nutzer die wichtigste Angabe
   ueberhaupt (die Prognose gilt fuer genau einen Punkt). */
.topbar{position:sticky;top:0;z-index:5;display:flex;
 align-items:center;justify-content:space-between;
 padding:calc(14px + env(safe-area-inset-top)) 18px 12px;
 background:rgba(0,0,0,.72);
 -webkit-backdrop-filter:blur(18px) saturate(1.4);
 backdrop-filter:blur(18px) saturate(1.4);
 border-bottom:1px solid var(--karte)}
.marke-wort{margin:0;font-size:17px;font-weight:800;
 letter-spacing:var(--sperrung-enger)}
.ortspille{padding:3px 11px;border-radius:var(--radius-pille);
 background:var(--karte);color:var(--tinte2);font-size:12px;font-weight:700}

/* --- Korpuszeile: benennt den Bestand, statt ihn vorauszusetzen ----- */
.korpus{margin:0;padding:20px 18px 0;color:var(--gedaempft);
 font-size:12px;font-weight:700;letter-spacing:var(--sperrung-label);
 text-transform:uppercase}

/* --- Hero ----------------------------------------------------------- */
.hero{margin-top:16px;padding:0 18px}
.etikett{margin:0;color:var(--gedaempft);font-size:12px;font-weight:700;
 letter-spacing:var(--sperrung-label);text-transform:uppercase}
.datum{margin:2px 0 0;font-size:23px;font-weight:700;
 letter-spacing:var(--sperrung-enger);color:var(--tinte)}
.stufe{margin:8px 0 0;font-size:44px;font-weight:800;line-height:1.02;
 letter-spacing:-.04em}
.grund{margin:6px 0 0;color:var(--tinte2);font-size:14px;text-wrap:pretty}
.zahlen{margin:10px 0 0;color:var(--gedaempft);font-size:13px}
.selten{color:var(--akzent-tinte)}
.auffaellig{color:var(--akzent)}
.unauffaellig{color:var(--gedaempft)}

/* --- Himmelsband ---------------------------------------------------- */
.bandflaeche{margin-top:20px;height:76px;line-height:0}
.bandflaeche svg{display:block;width:100%;height:76px}
.bandfuss{margin:8px 18px 0;color:var(--gedaempft);font-size:12px}

/* --- Zeitachse ------------------------------------------------------ */
.achsenkopf{display:flex;justify-content:space-between;
 padding:0 18px 10px;font-size:12px;color:var(--gedaempft)}
.achsenkopf b{font-weight:700;letter-spacing:var(--sperrung-label);
 text-transform:uppercase}
.achsenkopf span{font-weight:400}
.achsenblock{margin-top:26px}
.achse{position:relative;height:__ACHSE__px;margin:0 18px}
/* Gefuellte Zonen statt zweier Linien: sie zeigen, wie weit es bis zur
   Schwelle ist.  Mit Linien allein saehe man Punkte im Nichts. */
.zone{position:absolute;left:0;right:0;pointer-events:none}
.zone-selten{top:0;height:__ZS__px;background:rgba(255,159,10,.18);
 border-bottom:1px solid var(--akzent)}
.zone-auffaellig{top:__ZS__px;height:__ZA__px;background:rgba(255,159,10,.07);
 border-bottom:1px dashed var(--gitter)}
.zonenname{position:absolute;right:0;transform:translateY(-100%);
 font-size:11px;font-weight:700;letter-spacing:.04em;pointer-events:none}
.linie{position:absolute;inset:0;width:100%;height:100%;
 overflow:visible;pointer-events:none}
.marken{position:absolute;inset:0;display:flex}
.marke{flex:1;min-width:0;height:100%;position:relative;border:0;
 background:transparent;border-radius:var(--radius-mikro);padding:0;
 cursor:pointer;font:inherit;color:var(--gedaempft)}
.fahne{position:absolute;left:50%;width:1px;bottom:0;
 background:linear-gradient(to bottom,rgba(142,142,147,.16),transparent)}
.punkt{position:absolute;left:50%;width:11px;height:11px;
 margin:-5.5px 0 0 -5.5px;border:1.5px solid currentColor;
 border-radius:var(--radius-pille);background:var(--papier);
 transition:transform var(--zeit) var(--kurve),box-shadow var(--zeit)}
.selten .punkt{background:var(--akzent-tinte);
 box-shadow:0 0 12px rgba(255,179,64,.7)}
.marke.an .fahne{width:2px;
 background:linear-gradient(to bottom,rgba(255,179,64,.62),transparent)}
.marke.an .punkt{transform:scale(1.45)}
@media (hover:hover){.marke:hover .punkt{transform:scale(1.2)}}
.marke:focus-visible{outline:2px solid var(--akzent);outline-offset:2px}
/* Die Beschriftung steht in einer EIGENEN Flexzeile mit denselben
   flex:1-Spalten.  Im Knopf saesse sie sonst innerhalb der 200 px hohen
   Tastflaeche und verschoebe die Marken. */
.achsenfuss{display:flex;margin:8px 18px 0}
.achsenfuss div{flex:1;min-width:0;text-align:center}
.achsenfuss .wt{font-size:11px;color:var(--gedaempft)}
.achsenfuss .dt{font-size:12px;font-weight:600;color:var(--tinte2)}
.achsenfuss .an .wt{color:var(--tinte2)}
.achsenfuss .an .dt{color:var(--tinte)}

/* --- Grafikkarten --------------------------------------------------- */
.karte{margin:26px 18px 0;padding:14px 12px 12px;background:var(--karte);
 border:1px solid var(--achse);border-radius:var(--radius-karte);
 box-shadow:var(--schatten-ruhe)}
.karte + .karte{margin-top:16px}
.kartentitel{margin:0 4px 10px;color:var(--gedaempft);font-size:12px;
 font-weight:700;letter-spacing:var(--sperrung-label);text-transform:uppercase}
.karte svg{display:block;width:100%;height:auto}
.kartenfuss{margin:10px 4px 0;color:var(--gedaempft);font-size:12px}

/* --- Fusstext und Push-Auskunft ------------------------------------- */
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
 line-height:1.55}

@media (prefers-reduced-motion:reduce){
 *{transition:none!important;animation:none!important}}
</style></head><body>
<div class="rahmen">
<header class="topbar"><p class="marke-wort">Streulicht</p>
<span class="ortspille">__ORT__</span></header>

<p class="korpus">__KORPUS__</p>

<main>
<section class="hero"><p class="etikett" id="etikett">__ETIKETT__</p>
<p class="datum" id="datum">__DATUM__</p>
<p class="stufe __KLASSE__" id="stufe">__STUFE__</p>
<p class="grund" id="grund">__GRUND__</p>
<p class="zahlen" id="zahlen">__ZAHLEN__</p></section>

<div class="bandflaeche" id="bandflaeche">__BAND__</div>
<p class="bandfuss">Lichteindruck, schematisch &#8212; aus dem Score dieses
Abends.</p>

<section class="achsenblock">
<div class="achsenkopf"><b>__ANZAHL_WORT__</b><span>Perzentil des
Jahres</span></div>
<div class="achse">
<i class="zone zone-selten"></i><i class="zone zone-auffaellig"></i>
<b class="zonenname" style="top:__ZS__px;color:var(--akzent-tinte)">SELTEN
95.</b>
<b class="zonenname" style="top:__ZAU__px;color:var(--gedaempft)">AUFF&Auml;LLIG
80.</b>
<svg class="linie" viewBox="0 0 100 100" preserveAspectRatio="none"
 aria-hidden="true"><polyline points="__LINIE__" fill="none"
 stroke="__LINIENFARBE__" stroke-width=".7"
 vector-effect="non-scaling-stroke"/></svg>
<div class="marken">__MARKEN__</div></div>
<div class="achsenfuss">__ACHSENFUSS__</div></section>

<section class="karte"><p class="kartentitel">Der Weg des Lichts</p>
<div id="schnitt">__SCHNITT__</div>
<p class="kartenfuss">Der Strahl, der bei Sonnenuntergang von Westen
ankommt, und die Wolkenschichten auf seinem Weg. H&ouml;he
__UEBERHOEHT__-fach &uuml;berh&ouml;ht.</p></section>

<section class="karte"><p class="kartentitel">Von oben</p>
<div id="karte">__KARTE__</div>
<p class="kartenfuss">Die Wolkendecke westlich von __ORT__ auf dem
Abfrage&shy;f&auml;cher, und der Azimut des Sonnenuntergangs.</p></section>

<p class="fuss">Die Stufe kommt aus der Position in der Jahresverteilung:
<b>selten</b> ab dem 95. Perzentil (rund 18 Abende im Jahr),
<b>auff&auml;llig</b> ab dem 80. Bewusst keine Prozentzahl &mdash; belegt ist,
dass der Score au&szlig;ergew&ouml;hnliche Abende von gew&ouml;hnlichen
trennt, nicht dass er unter den guten ordnet.</p>

<p class="push">__PUSHTEXT__</p>

<a class="weiter" href="bisher.html">Was bisher gemessen ist</a>
</main></div>
<script>
const META=__META__;
const marken=[...document.querySelectorAll(".marke")];
const fuesse=[...document.querySelectorAll(".achsenfuss div")];
function waehle(i){
  marken.forEach((x,k)=>x.classList.toggle("an",k===i));
  fuesse.forEach((x,k)=>x.classList.toggle("an",k===i));
  const m=META[i];
  document.getElementById("etikett").textContent=
    i===__BESTER__?"Bester Abend im Fenster":"Gew\\u00e4hlter Abend";
  document.getElementById("datum").textContent=m.lang;
  const st=document.getElementById("stufe");
  st.textContent=m.stufe; st.className="stufe "+m.klasse;
  document.getElementById("grund").textContent=m.grund||"";
  // Drei Zahlen, und sie duerfen nicht verwechselt werden: das Perzentil
  // ist der klimatologische Rang des Member-Medians ("wie selten"), die
  // Wahrscheinlichkeit der Anteil der Ensemble-Member ueber der Schwelle
  // ("wie sicher").  In der Rueckschau gibt es nur das Perzentil - dort
  // war nichts vorherzusagen.
  const teile=[Math.round(m.p*100)+". Perzentil des Jahres"];
  if(m.wahrsch!==null&&m.wahrsch!==undefined)
    teile.push(Math.round(m.wahrsch*100)+" % Wahrscheinlichkeit");
  teile.push("Sonnenuntergang "+m.zeit+" Uhr");
  document.getElementById("zahlen").textContent=teile.join(" \\u00b7 ");
  document.getElementById("bandflaeche").innerHTML=m.band;
  document.getElementById("schnitt").innerHTML=m.svg;
  document.getElementById("karte").innerHTML=m.karte;
}
marken.forEach((b,i)=>b.onclick=()=>waehle(i));
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

    y = lambda p: ACHSE_PX * (1.0 - p)                            # noqa: E731
    marken = "".join(
        '<button class="marke %s%s" data-i="%d" '
        'aria-label="%s, %s, %d. Perzentil">'
        '<i class="fahne" style="top:%.1fpx"></i>'
        '<i class="punkt" style="top:%.1fpx"></i></button>'
        % (e["klasse"], " an" if i == gewaehlt else "", i,
           e["lang"], e["stufe"], round(e["p"] * 100), y(e["p"]), y(e["p"]))
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

    meta = json.dumps([{k: e[k] for k in ("tag", "lang", "p", "stufe",
                                          "klasse", "zeit", "wahrsch",
                                          "vorlauf_h", "grund", "svg",
                                          "karte", "band")}
                       for e in eintraege], ensure_ascii=False)

    zs = y(SCHWELLE_SELTEN)
    za = y(SCHWELLE_AUFFAELLIG) - zs
    html = (VORLAGE
            .replace("__TOKENS__", tokens.quelltext())
            .replace("__ORT__", anzeige)
            .replace("__KORPUS__", korpus)
            .replace("__ANZAHL_WORT__",
                     {10: "ZEHN ABENDE"}.get(n, "%d ABENDE" % n))
            .replace("__ACHSE__", str(ACHSE_PX))
            .replace("__ZS__", "%.0f" % zs)
            .replace("__ZAU__", "%.0f" % (zs + za))
            .replace("__ZA__", "%.0f" % za)
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
            .replace("__META__", meta)
            .replace("__BESTER__", str(bester)))
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
