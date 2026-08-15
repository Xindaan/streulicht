"""Die eigentliche Produktseite: was Andre abends anschaut.

Bewusst KEINE Prozentzahl als Hauptaussage.  Nach allem, was gemessen ist,
kann der Score aussergewoehnliche Abende von gewoehnlichen trennen
(Anreicherung n = 43, p = 0.0001), aber ob er unter den guten ordnet, ist
offen.  Eine Zahl wie "71 %" behauptet eine Trennschaerfe, die nicht belegt
ist.  Deshalb drei Stufen, an Perzentilen der Klimatologie festgemacht:

    unauffaellig   unter dem 80. Perzentil
    auffaellig     80. bis 95.
    selten         ab dem 95. (= s*, rund 18 Abende im Jahr)

Laeuft mit historischen Abenden (Kennzeichnung "Rueckschau") und spaeter
unveraendert mit Prognosedaten.

GESTALTUNG (T-0010, 14.08.2026): Hausstandard aus poisson-dor und
rezept-grid, Werte in stil/tokens.css, Begruendung in docs/ui-referenz.md.
Nur Dunkel.  Drei Entscheidungen, die den frueheren Entwurf ersetzen:

1. ACHSE STATT BALKEN.  Der Balken war als Fuellstand von null gezeichnet.
   Gemessen ueber zehn Abende lagen die Perzentile aber zwischen 0.592 und
   0.971 - die unteren 59 % jedes Balkens waren tote Flaeche, und der
   schlechteste Abend (Score 0.072) zeigte einen zu 59 % gefuellten Balken.
   Das liest sich als "mehr als die Haelfte" und behauptet damit genau die
   Trennschaerfe, die der Docstring oben ablehnt.  Eine Marke auf einer
   Achse codiert dieselbe Zahl als Position statt als Fuellstand; die zwei
   Schwellenlinien (80. und 95.) liefern den Bezug mit.

2. EINE FARBFAMILIE, DREI ZUSTAENDE.  Statt der Ampel Orange/Gold/Grau:
   selten = gefuellte Marke, auffaellig = offene Marke in derselben Farbe,
   unauffaellig = gedaempft und farblos.  Haelt den Hausgrundsatz "genau ein
   Akzent" ein und trennt besser, weil Orange gegen Gold zu nah beieinander
   lag.

3. TEXT AUS DEM BILD HERAUS.  Datum, Stufe, Uhrzeit und der
   Ueberhoehungshinweis standen im SVG und schrumpften auf dem Telefon auf
   4 px.  Sie stehen jetzt als echter Text in der Seitentypografie; im SVG
   bleibt nur, was von seiner Position lebt.
"""
import argparse
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tokens  # noqa: E402
from schnitt import lade_feld, svg, ueberhoehung  # noqa: E402
sys.path.insert(0, BASIS_ELTERN := os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import sonnenuntergang  # noqa: E402

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

# --- Ort als URL-Parameter: vorbereitet, NICHT gebaut ---------------------
#
# E0 hat "Ort als Parameter, auch fuer Freunde" entschieden, die
# Zweitreferenz macht es als ?sky=bilbao-es vor.  Das Ziel waere
# ?ort=berlin.  Gebaut wird es NICHT in T-0010 (Gestaltung); hier steht nur,
# was dafuer angefasst werden muss, damit die Suche spaeter entfaellt:
#
#   1. Ein Ortsregister {kuerzel: (Anzeigename, Breite, Laenge, Zeitzone,
#      Klimatologiedatei)}.  Gehoert nach konfig.json, nicht in den Code.
#   2. seite.py: der feste Dateiname score_berlin_g0.5_2022_2025.json in
#      main(), die Koordinaten 52.52/13.405 und "Europe/Berlin" in
#      lokalzeit(), und das feste "Berlin" in der Kopfzeile der Vorlage.
#   3. schnitt.py: die Modulkonstanten BREITE, LAENGE - heute global, also
#      pro Ort zu uebergeben statt zu setzen - und die Ortsbeschriftung am
#      Nullpunkt der x-Achse.
#   4. Erzeugung: je Ort eine Seite (web/berlin.html ...), weil GitHub Pages
#      statisch ausliefert und den Parameter nicht serverseitig aufloesen
#      kann.  Der Parameter waere dann eine Weiche im Skript, nicht zur
#      Laufzeit im Browser.
#
# Zwei offene Abhaengigkeiten, die vorher geklaert sein muessen: T-0013
# (streut s* ueber Ankerorte weniger als 15 %? sonst braucht jeder Ort eine
# eigene Klimatologie) und T-0007 (Gelaende im Fensterterm - ab freier
# Ortswahl zwingend, nicht optional).

# Geometrie der Achse in Pixeln.  Bewusst hier und nicht im CSS: die
# Schwellenlinien und die Marken muessen exakt dasselbe Koordinatensystem
# benutzen, und das rechnet sich in Python einmal statt in CSS dreimal.
SAEULE_PX = 132
ACHSE_OBEN_PX = 12
SCHWELLEN = ((0.95, "95."), (0.80, "80."))


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
    if rang >= 0.95:
        return "selten", "selten"
    if rang >= 0.80:
        return "auffällig", "auffaellig"
    return "unauffällig", "unauffaellig"


def kurzmarke(d, erster):
    """Tageszahl auf der Achse - mit Monat nur beim ersten und am Monatsersten.

    Auf dem Telefon steht je Marke rund eine Tastflaeche Breite zur
    Verfuegung; "25.08." passt dort nicht, "25." schon.  Der Monat kommt
    dort mit, wo er sich aendert, sonst waere die Folge 31. 01. 02. nicht
    eindeutig.
    """
    if erster or d.day == 1:
        return "%d.%d." % (d.day, d.month)
    return "%d." % d.day


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--von", default="2025-08-25")
    ap.add_argument("--tage", type=int, default=10)
    a = ap.parse_args()
    with open(os.path.join(BASIS, "daten",
                           "score_berlin_g0.5_2022_2025.json")) as f:
        klima = json.load(f)
    alle = sorted(v["s"] for v in klima.values())

    def perzentil(s):
        return sum(1 for x in alle if x < s) / len(alle)

    tage = [(date.fromisoformat(a.von) + timedelta(days=k)).isoformat()
            for k in range(a.tage)]
    tage = [t for t in tage if t in klima]
    eintraege = []
    for t in tage:
        feld = lade_feld(t)
        if not feld:
            continue
        try:
            bild, s, det = svg(t, feld, kompakt=True)
        except Exception:                                        # noqa: BLE001
            continue
        p = perzentil(s)
        name, klasse = stufe(p)
        d = date.fromisoformat(t)
        eintraege.append({"tag": t, "wt": WOCHENTAG[d.weekday()],
                          "kurz": kurzmarke(d, not eintraege),
                          "lang": "%s, %d. %s" % (WOCHENTAG_LANG[d.weekday()],
                                                  d.day, MONAT[d.month - 1]),
                          "p": p, "stufe": name, "klasse": klasse,
                          "zeit": lokalzeit(t), "svg": bild})
    if not eintraege:
        raise SystemExit("keine Abende")

    beste = max(range(len(eintraege)), key=lambda i: eintraege[i]["p"])
    spanne = "%s bis %s" % (
        date.fromisoformat(eintraege[0]["tag"]).strftime("%d.%m."),
        date.fromisoformat(eintraege[-1]["tag"]).strftime("%d.%m."))

    # Linien und Beschriftung sind getrennt, und das ist kein Schoenheits-
    # detail: die Linien liegen IM Roller und muessen die volle Breite aller
    # Marken spannen (440 px bei zehn Abenden), die Beschriftung steht
    # DANEBEN und darf nicht mitrollen, sonst schiebt sie sich beim ersten
    # Wisch aus dem Bild.
    schwellen = "".join(
        '<i class="schwelle" style="top:%.1fpx"></i>'
        % (ACHSE_OBEN_PX + SAEULE_PX * (1.0 - p)) for p, _ in SCHWELLEN)
    skala = "".join(
        '<b style="top:%.1fpx">%s</b>'
        % (ACHSE_OBEN_PX + SAEULE_PX * (1.0 - p), text)
        for p, text in SCHWELLEN)
    marken = "".join(
        '<button class="marke %s" data-i="%d" aria-label="%s, %s">'
        '<span class="saeule"><i class="punkt" style="top:%.1fpx"></i></span>'
        '<span class="wt">%s</span><span class="dt">%s</span></button>'
        % (e["klasse"], i, e["lang"], e["stufe"],
           SAEULE_PX * (1.0 - e["p"]), e["wt"], e["kurz"])
        for i, e in enumerate(eintraege))
    svgs = json.dumps({str(i): e["svg"] for i, e in enumerate(eintraege)})
    meta = json.dumps([{k: e[k] for k in ("tag", "lang", "p", "stufe",
                                          "klasse", "zeit")}
                       for e in eintraege])

    html = """<!doctype html><html lang="de"><head><meta charset="utf-8">
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
.rahmen{max-width:var(--breite-schmal);margin:0 auto;
 padding:var(--s6) var(--s4) var(--s8)}

/* --- Kopf ---------------------------------------------------------- */
h1{margin:0;font-size:26px;font-weight:700;
 letter-spacing:var(--sperrung-enger)}
h1 span{color:var(--gedaempft);font-weight:400}
.spanne{display:flex;align-items:center;flex-wrap:wrap;gap:var(--s2);
 margin:var(--s1) 0 0;color:var(--gedaempft);font-size:13px}
.pille{padding:2px 10px;border-radius:var(--radius-pille);
 background:var(--flaeche2);color:var(--gedaempft);font-size:12px;
 font-weight:700;letter-spacing:var(--sperrung-label);text-transform:uppercase}

/* --- Achse --------------------------------------------------------- */
/* Marke statt Balken: die Position traegt den Wert, nicht der Fuellstand.
   Die zwei gestrichelten Linien sind der Bezug - ohne sie waere die
   Position so unverankert wie eine nackte Prozentzahl. */
.achse-karte{position:relative;margin:var(--s6) 0;
 padding:var(--s4) var(--s3) var(--s3);
 background:var(--karte);border:1px solid var(--achse);
 border-radius:var(--radius-karte);box-shadow:var(--schatten-ruhe)}
.achse-rollen{overflow-x:auto;scrollbar-width:none;margin-right:30px;
 -webkit-overflow-scrolling:touch}
.achse-rollen::-webkit-scrollbar{display:none}
/* Abblendung an der Seite, an der noch etwas liegt.  Ohne sie sieht eine
   halb angeschnittene Marke nach Schaden aus statt nach Fortsetzung; die
   Klassen setzt das Skript beim Rollen, damit am Ende nicht abgeblendet
   wird, wo nichts mehr kommt. */
.mehr-rechts{-webkit-mask-image:linear-gradient(to right,#000 calc(100% - 28px),transparent);
 mask-image:linear-gradient(to right,#000 calc(100% - 28px),transparent)}
.mehr-links{-webkit-mask-image:linear-gradient(to right,transparent,#000 28px);
 mask-image:linear-gradient(to right,transparent,#000 28px)}
.mehr-links.mehr-rechts{
 -webkit-mask-image:linear-gradient(to right,transparent,#000 28px,
  #000 calc(100% - 28px),transparent);
 mask-image:linear-gradient(to right,transparent,#000 28px,
  #000 calc(100% - 28px),transparent)}
/* width:max-content, damit die Schwellenlinien unter ALLEN Marken
   durchlaufen und nicht am sichtbaren Rand enden. */
.achse{position:relative;display:flex;width:max-content;min-width:100%;
 padding-top:__OBEN__px}
.schwelle{position:absolute;left:0;right:0;height:0;
 border-top:1px dashed var(--gitter);pointer-events:none}
.skala{position:absolute;top:var(--s4);right:var(--s3);width:30px;
 pointer-events:none}
.skala b{position:absolute;right:0;transform:translateY(-50%);
 color:var(--gedaempft);font-size:11px;font-weight:600;letter-spacing:0}
.marke{flex:1 0 var(--tastflaeche);min-width:var(--tastflaeche);
 display:flex;flex-direction:column;align-items:center;
 padding:0 0 var(--s2);border:0;background:none;color:var(--gedaempft);
 font:inherit;letter-spacing:inherit;cursor:pointer;
 border-radius:var(--radius-kachel);
 transition:background-color var(--zeit) var(--kurve)}
.saeule{position:relative;width:100%;height:__SAEULE__px}
.punkt{position:absolute;left:50%;width:10px;height:10px;margin:-5px 0 0 -5px;
 border:1.5px solid currentColor;border-radius:var(--radius-pille);
 transition:transform var(--zeit) var(--kurve)}
.wt{margin-top:var(--s2);font-size:11px}
.dt{font-size:12px;font-weight:600;color:var(--tinte2)}
.selten{color:var(--akzent-tinte)}
.selten .punkt{background:var(--akzent-tinte)}
.auffaellig{color:var(--akzent)}
.unauffaellig{color:var(--gedaempft)}
.marke.an{background:var(--flaeche2)}
.marke.an .punkt{transform:scale(1.5)}
.marke.an .dt{color:var(--tinte)}
@media (hover:hover){.marke:hover{background:var(--flaeche2)}}
.marke:focus-visible{outline:2px solid var(--akzent);outline-offset:2px}

/* --- Gewaehlter Abend: Hausmuster kleines Etikett ueber grosser Zahl -- */
.etikett{margin:0;color:var(--gedaempft);font-size:12px;font-weight:700;
 letter-spacing:var(--sperrung-label);text-transform:uppercase}
.stufe{margin:var(--s1) 0 0;font-size:40px;font-weight:800;line-height:1.05;
 letter-spacing:var(--sperrung-enger)}
.unter{margin:var(--s2) 0 0;color:var(--gedaempft);font-size:14px}
.bild{max-width:var(--breite-bild);margin:var(--s6) 0 0;padding:var(--s3);
 background:var(--karte);border:1px solid var(--achse);
 border-radius:var(--radius-karte);box-shadow:var(--schatten-ruhe)}
.bild svg{display:block;width:100%;height:auto}
.bildfuss{max-width:var(--breite-bild);margin:var(--s2) 0 0;
 color:var(--gedaempft);font-size:12px}
.fuss{max-width:44rem;margin:var(--s7) 0 0;color:var(--gedaempft);
 font-size:13px;line-height:1.55}

@media (prefers-reduced-motion:reduce){
 *{transition:none!important;animation:none!important}}
</style></head><body>
<div class="rahmen">
<header><h1>Streulicht <span>Berlin</span></h1>
<p class="spanne">__SPANNE__<span class="pille">R&uuml;ckschau</span></p></header>

<div class="achse-karte"><div class="achse-rollen">
<div class="achse" id="achse">__SCHWELLEN____MARKEN__</div></div>
<div class="skala">__SKALA__</div></div>

<main><p class="etikett" id="etikett"></p>
<p class="stufe" id="stufe"></p>
<p class="unter" id="unter"></p>
<div class="bild" id="bild"></div>
<p class="bildfuss">H&ouml;he __UEBERHOEHT__-fach &uuml;berh&ouml;ht &middot;
Wolken aus ERA5, B&auml;nderdicke schematisch.</p>
<p class="fuss">Die Stufe kommt aus der Position in der Jahresverteilung:
<b>selten</b> ab dem 95. Perzentil (rund 18 Abende im Jahr),
<b>auff&auml;llig</b> ab dem 80. Bewusst keine Prozentzahl &mdash; belegt ist,
dass der Score au&szlig;ergew&ouml;hnliche Abende von gew&ouml;hnlichen
trennt, nicht dass er unter den guten ordnet.</p></main>
</div>
<script>
const SVG=__SVGS__, META=__META__;
const roller=document.querySelector(".achse-rollen");
const marken=[...document.querySelectorAll(".marke")];
// scrollLeft direkt statt scrollIntoView: letzteres rollt ALLE scrollbaren
// Vorfahren mit, also auch die Seite, und blieb hier wirkungslos
// (gemessen: scrollLeft 0, gewaehlte Marke bei 308 in einem 287 breiten
// Fenster).  Und nur so weit wie noetig statt mittig - zentrieren schoebe
// den Fensteranfang aus dem Bild, obwohl die Kopfzeile ihn nennt.
function heranrollen(b){
  if(!b)return;
  const rand=44, l=b.offsetLeft, r=l+b.offsetWidth, w=roller.clientWidth;
  if(r+rand>roller.scrollLeft+w) roller.scrollLeft=r+rand-w;
  else if(l-rand<roller.scrollLeft) roller.scrollLeft=Math.max(0,l-rand);
  raender();
}
function raender(){
  const l=roller.scrollLeft, max=roller.scrollWidth-roller.clientWidth;
  roller.classList.toggle("mehr-links", l>1);
  roller.classList.toggle("mehr-rechts", l<max-1);
}
function waehle(i,rollen){
  marken.forEach(x=>x.classList.remove("an"));
  const b=marken[i]; b.classList.add("an");
  const m=META[i];
  document.getElementById("etikett").textContent=m.lang;
  const st=document.getElementById("stufe");
  st.textContent=m.stufe; st.className="stufe "+m.klasse;
  document.getElementById("unter").textContent=
    "Sonnenuntergang "+m.zeit+" Uhr \\u00b7 "+Math.round(m.p*100)+
    ". Perzentil des Jahres";
  document.getElementById("bild").innerHTML=SVG[i];
  if(rollen)heranrollen(b);
}
marken.forEach((b,i)=>b.onclick=()=>waehle(i,false));
roller.addEventListener("scroll",raender,{passive:true});
waehle(__BESTE__,false);
// Das erste Heranrollen haengt an der Layout-Messung, nicht an "load":
// zum Skriptzeitpunkt ist scrollWidth noch gleich clientWidth, jedes
// Setzen von scrollLeft wird dann auf 0 gekappt und sieht hinterher aus
// wie Absicht.  Der Beobachter feuert, sobald die Breite wirklich steht,
// und deckt Drehung und Groessenaenderung gleich mit ab.
let ersteRollung=true;
new ResizeObserver(()=>{
  raender();
  if(ersteRollung&&roller.scrollWidth>roller.clientWidth){
    ersteRollung=false;
    heranrollen(marken[__BESTE__]);
  }
}).observe(roller);
</script></body></html>"""
    html = (html.replace("__TOKENS__", tokens.quelltext())
            .replace("__SCHWELLEN__", schwellen)
            .replace("__SKALA__", skala)
            .replace("__MARKEN__", marken)
            .replace("__SPANNE__", "%d Abende &middot; %s"
                     % (len(eintraege), spanne))
            .replace("__UEBERHOEHT__", "%.0f" % ueberhoehung(True))
            .replace("__OBEN__", str(ACHSE_OBEN_PX))
            .replace("__SAEULE__", str(SAEULE_PX))
            .replace("__SVGS__", svgs).replace("__META__", meta)
            .replace("__BESTE__", str(beste)))
    ziel = os.path.join(BASIS, "web", "index.html")
    with open(ziel, "w", encoding="utf-8") as f:
        f.write(html)
    print("geschrieben: %s (%d Abende, %.1f MB)"
          % (ziel, len(eintraege), os.path.getsize(ziel) / 1e6))


if __name__ == "__main__":
    main()
