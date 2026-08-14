# UI-Referenz fuer die Produktseite (14.08.2026)

Zwei Quellen, klar gewichtet.

**Primaer: Andres eigene Designsprache.** Sie existiert bereits, ist
dokumentiert und ueber zwei Projekte konsistent — `poisson-dor` (oeffentlich,
github.com/Xindaan/poisson-dor) und `rezept-grid` (~/src/rezept-grid, dessen
`css/stil.css` ausdruecklich auf `poisson-dor/assets/tokens.css` als Herkunft
verweist). Das ist kein Geschmack, sondern ein Hausstandard.

**Sekundaer: eclipses.bogachev.fr** (`?sky=bilbao-es`) — liefert das, was der
Hausstandard nicht hat, weil dessen Projekte Dashboards und Rezepte sind und
kein Himmelsprodukt.

Alles unten ist ausgelesen, nicht geschaetzt: CSS-Variablen aus den laufenden
Dateien, Konsolenausgabe aus dem Browser.

---

# Teil 1 — Der Hausstandard (verbindlich)

Belegstellen: `poisson-dor/assets/tokens.css`,
`poisson-dor/analysis/ui_review.md` Abschnitt A1 (dort mit Herkunft je
Zeile), `rezept-grid/css/stil.css`.

## 1.1 Der entscheidende Befund: es ist ein System, keine Optik

Die Produktseite benutzt heute **denselben Schriftstack** wie Andres
Projekte. Sie sieht trotzdem generisch aus. Der Unterschied ist nicht die
Schrift, sondern die Disziplin dahinter:

| | Produktseite heute | Hausstandard |
|---|---|---|
| Grund | `#0d1117` GitHub-Dunkelgrau | `#fbfbfd` bzw. Apple-Dunkelmodus |
| Farben | vier Literale, ad hoc | Tokens, Semantik als Tripel Basis/soft/deep |
| Abstaende | Literale je Regel | Leiter `4 8 12 16 20 26 34 56` |
| Radien | 4/8/10 gemischt | Leiter `8 13 18 22 999` |
| Schatten | keine | drei Stufen mit Regel |
| Ziffern | proportional | `tabular-nums` global |
| Tracking | keins | `-.022em` Basis, `-.03/-.04em` gross |
| Bewegung | keine | `.15-.16s`, `cubic-bezier(.2,.7,.2,1)` |

**Die Aufgabe ist also Portierung, nicht Neuentwurf.**

## 1.2 Architektur — der wichtigste Uebertrag

`poisson-dor/assets/tokens.css` sagt im Kopfkommentar:

> Diese Datei wird auch von den Python-Generatoren gelesen und in deren
> Style-Block inlined -- die generierten Seiten bleiben dadurch
> self-contained: kein Stylesheet-Verweis, kein Netzzugriff.

Das ist **exakt die Architektur von `skripte/seite.py`**: ein
Python-Generator, der eine einzelne self-contained HTML-Datei schreibt. Das
Muster ist eins zu eins uebernehmbar — eine Token-Datei im Repo, von
`seite.py` **und** `schnitt.py` gelesen und inlined. Damit loesen sich die
24 fest verdrahteten Farben in `schnitt.py` von selbst auf.

## 1.3 Schrift — hier lag meine frueher gegebene Empfehlung falsch

Ich hatte am 14.08. eine charaktervolle Groteske plus eine Mono als
selbst gehostete woff2 empfohlen. **Das widerspricht dem Hausstandard und
ist zurueckgezogen.** Tatsaechlich:

    -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
    "Segoe UI", system-ui, Roboto, sans-serif

Ein Stack fuer alles. `rezept-grid/css/stil.css` schreibt dazu: *"Ein
Schriftstack fuer alles — ersetzt Serif, Sans und Monospace. Tabellenziffern
global, damit Mengen und Zeiten ohne eigene Schrift buendig stehen."*

Statt einer Mono also `font-variant-numeric: tabular-nums` global, dazu
`-webkit-font-smoothing: antialiased`. Kein Webfont, keine woff2, null Bytes
Schriftgewicht — und die Auflage "kein CDN" ist ohne Verzicht erfuellt.

Grade: Basis **15px**, Zeilenhoehe **1.5**. Stufenleiter
`34/26/19/15/13/12/11.5` plus KPI-Grad **44**. Ueberschriften Gewicht 700-800
mit Tracking `-.022em`, bei grossen Graden `-.03em` bis `-.04em`. Label und
Eyebrow: 12px, Gewicht 700, `letter-spacing .06em`, versal.

## 1.4 Farbe

    Flaechen   --bg #fbfbfd   --bg2 #f1f1f4   --card #ffffff
    Text       --ink #1d1d1f  --ink2 #3c3c43  --muted #6e6e73  --faint #a5a5ac
    Linien     --line #e6e6ea    --line2 #efeff2
    Akzent     --acc #059669  --acc-d #047857  --acc-soft #e6f8ec

Regeln, die dabei gelten:

- **Genau ein Akzent** — "was zusammengehoert, und die eine Haupthandlung"
  (`rezept-grid/css/stil.css`).
- **Semantikfarben als Tripel** Basis / -soft (Fuellung) / -d (Text):
  `--blue #007aff/#e6f0ff/#0a62cc`, `--amber #ff9500/#fff1dc/#a25e00`,
  `--red #ff3b30/#ffe6e4/#bf271e`, `--gold #c39214/#faf1d6`.
  ui_review.md A1 nennt das den wichtigsten strukturellen Unterschied zu
  einem System mit nur einem Wert je Farbe.
- **Chip und Badge: weiche Fuellung plus kraeftiger Text**, nicht Rand mit
  Farbe.
- Fuer Wahrscheinlichkeiten existiert eine **sechsstufige sequentielle
  Rampe** `#f3f4f2 … #0f7d5d`.

## 1.5 Dunkelmodus

`poisson-dor` hat keinen. `rezept-grid` hat einen nachgeruesteten, aus
Apple-Systemfarben abgeleitet und **auf AA-Kontrast nachgerechnet**, ueber
`@media (prefers-color-scheme: dark)`:

    --papier #000000  --karte #1c1c1e  --flaeche2 #2c2c2e
    --tinte #f2f2f7   --tinte2 #d1d1d6  --gedaempft #98989d
    --akzent #30d158  --akzent-flaeche #0f2a1c

Fuer ein Produkt, das **abends** angeschaut wird, ist das der fertige
Baustein. Uebernehmen, nicht neu erfinden.

## 1.6 Mass, Schatten, Bewegung

    Abstaende  --s1..--s8  4 8 12 16 20 26 34 56
    Radien     8 (Mikro) / 13 (Kachel) / 18 (Karte) / 22 (Sektion) / 999 (Pille)
    Container  max-width 1120px, padding 0 18px
    Breakpoints 560px (Dichte) und 860px (Layout-Kollaps) — beide
    Bewegung   .15-.16s, cubic-bezier(.2,.7,.2,1),
               Hover translateY(-1px..-2px) plus Schattenwechsel,
               @media (prefers-reduced-motion: reduce) haertet alles ab

**Schattenregel:** Karten in Ruhe tragen `sh-sm`, nicht `sh`. Der grosse
Schatten ist Hover- beziehungsweise Overlay-Zustand.

    --sh-sm  0 .5px 1.5px rgba(0,0,0,.04), 0 1px 2px rgba(0,0,0,.05)
    --sh     0 1px 2px rgba(0,0,0,.04),    0 8px 22px rgba(0,0,0,.06)
    --sh-lg  0 2px 8px rgba(0,0,0,.05),    0 22px 50px rgba(0,0,0,.1)

## 1.7 Bauteile, die direkt passen

- **Sticky-Topbar** halbtransparent mit `backdrop-filter: blur(18px)
  saturate(1.4)` und `env(safe-area-inset-top)`.
- **Pill-Nav**: randlose Pille, Zustand ueber Fuellung, `min-height` 38-40px.
- **KPI-Karte**: kleines leises Label **ueber** grosser Zahl, Farbe nur auf
  der Zahl. Das ist das Muster fuer Stufe plus Perzentil.
- **Horizontale Scroller ohne sichtbare Scrollbar** (`scrollbar-width: none`)
  — der Abendstreifen ist genau das.
- **Bottom-Sheet** fuer Details statt Inline-Aufklappen, `22px 22px 0 0`,
  `max-height 78vh`, ab 560px zentriert.
- **Zahlen rechts, Text links, Tabellenkopf leise und klein.**

---

# Teil 2 — Was die Finsternisseite beisteuert

Der Hausstandard ist fuer Dashboards und Rezepte gebaut. Vier Dinge fehlen
ihm, die diese Seite hat:

1. **Die Zeitachse ist die Navigation, nicht der Kachelstreifen.** Dort
   liegen Ereignisse als Marken auf einer Achse mit Bereichsschieber. Daran
   haengt der Dashboard-Eindruck: eine Achse liest sich als Zeit, Kaestchen
   lesen sich als Kacheln.
2. **Warm gegen kuehl statt Ampel.** Ihre Ereignisfarben: total `#fff6da`
   (fast weiss, warm), ringfoermig `#ff9a3c`, partiell `#6b86a8` — das
   schwaechste Ereignis ist das einzige kuehle. Uebertragen auf selten /
   auffaellig / unauffaellig ist das treffender als unser jetziges
   `#f0883e / #d29922 / #8b949e`, das eine Ampel mit Grau am Ende ist.
   Im Hausstandard laesst sich das als Semantik-Tripel ausdruecken
   (Gold fuer selten, Amber fuer auffaellig, `--muted` fuer unauffaellig).
3. **Ort als URL-Parameter**: `?sky=bilbao-es` plus Kopfzeile "54 eclipses
   seen from Bilbao · 1700–2100". Deckt sich mit der E0-Entscheidung "Ort als
   Parameter, auch fuer Freunde".
4. **Ehrlicher Ersatz statt Fehlermeldung**, im Klartext auf der Seite: "The
   3D city could not load, so this is the offline horizon."

Was **nicht** uebertragbar ist, siehe naechster Abschnitt.

## 2.1 Das 3D-Modell traegt nicht

Es ist nicht selbst gebaut, sondern **Mapbox GL JS 3.26.0** mit dem Tileset
`mapbox.mapbox-3dbuildings`. Aus der Browserkonsole am 14.08.2026:

    citysky_mapbox: FALLING BACK to the terrain skyview — fatal map error 403
    https://api.mapbox.com/v4/mapbox.mapbox-3dbuilding...  status 403

**Beim Ansehen lief genau dieser Fehler.** Das 3D-Modell war nicht zu sehen;
sichtbar war die Ersatzansicht. Der Zugriffstoken steht zwangslaeufig im
Quelltext und liefert 403 — abgelaufen, ueber Kontingent oder auf fremde
Domains gesperrt.

Also: ein fremder, kostenpflichtiger Dienst, kein Stueck Code. Er
widerspricht "eine statische Datei, kein Build, kein CDN" im Kern und ist die
unzuverlaessigste Komponente der Referenz. Die belastbare Variante ist deren
Rueckfallebene — und die haben wir in `skripte/schnitt.py` in Ansaetzen
schon.

## 2.2 Deren Palette und Schrift: bewusst NICHT uebernehmen

Pergament `#eae0cd` mit Sepia `#3a2f24` und Gold, Schriften Space Grotesk
plus Space Mono als woff2. Schoen, aber ein Fremdkoerper neben dem
Hausstandard — und Space Grotesk nennt der `frontend-design`-Skill
namentlich als Schrift, auf die alle konvergieren. Was uebertragbar ist, ist
oben unter 1-4 aufgezaehlt; die Optik selbst nicht.

---

# Teil 3 — Entschieden am 14.08.2026 (T-0010)

a) **Nur Dunkel**, Apple-Neutrale statt GitHub-Blaugrau. Der Anwendungsfall
   ist eindeutig (abends, Telefon, im Dunkeln), und die Bildlogik des
   Schnitts lebt davon: ein Lichtstrahl liest sich als Licht nur gegen
   Dunkelheit. Ein Hellsatz waere kein Token-Tausch, sondern ein eigener
   Entwurf fuer Wolkenbaender und Strahl — deshalb bewusst auch kein
   `prefers-color-scheme`-Block, der eine Zweimodigkeit vortaeuschen wuerde.
b) **Eine Akzentfamilie, drei Zustaende** ueber das Chip-Muster des
   Hausstandards: selten = gefuellte Marke, auffaellig = offene Marke in
   derselben Farbe, unauffaellig = `--gedaempft` und farblos. Haelt "genau
   ein Akzent" ein und trennt besser als Orange gegen Gold.
c) **Zeitachse mit Schwellenlinien** bei 80. und 95. statt Kachelstreifen.
   Der Grund ist gemessen, nicht aesthetisch: der alte Balken war ein
   Fuellstand von null, die Perzentile lagen aber zwischen 0,592 und 0,971 —
   die unteren 59 % waren tote Flaeche, und ein Score von 0,072 zeigte einen
   zu 59 % gefuellten Balken.
d) **Vertikalschnitt behalten**, telefonfeste Fassung. Silhouette
   zurueckgestellt als T-0016: sie beantwortet eine andere Frage (was man
   saehe statt warum), und fuer Berlin ist das Gelaende nach Westen flach.
e) **Deutsche Tokennamen** nach `~/src/CLAUDE.md` §7, mit Zuordnungstabelle
   zu `poisson-dor` im Kopf von `stil/tokens.css`.

Dazu drei Abweichungen vom Hausstandard, bewusst nach oben: 44-px-
Tastflaechen (Hausstandard 34-40, aber einhaendige Abendbedienung),
`prefers-reduced-motion`-Guard (hat `rezept-grid` nicht, die Zweitreferenz
fuenfmal), und neutrale statt blauer Wolkenbaender.

# Teil 4 — Nachtrag: die Zweitreferenz in Bewegung und auf dem Telefon

Am 14.08.2026 nachgeholt, was hier zuvor als ungeprueft stand.

**Bewegung.** 64 Transition-Regeln, 5 Animationen, drei benannte Keyframes
(`cmb-moon-slide`, `cmb-hint-bob`, `cmb-card-rise`). Genau **eine**
Easing-Kurve: `cubic-bezier(0.22, 0.61, 0.36, 1)` — stark abbremsend, also
derselbe Charakter wie die Hauskurve `cubic-bezier(.2,.7,.2,1)`. Die beiden
Designsprachen sind sich bei der Bewegung schon einig; hier war nichts zu
uebersetzen. Dauern: 120-180 ms Mikrointeraktion, 220-450 ms mittel,
0,8-1,2 s Auftritte. Und **fuenf `prefers-reduced-motion: reduce`-Bloecke** —
darin ist sie sorgfaeltiger als `rezept-grid`, das keinen hat.

**Telefon.** Echte responsive Arbeit: Bruchpunkt 620 px, dazu
`(pointer: coarse)`, 900 px und 1000 px, kein horizontales Ueberlaufen.
Trotzdem kollidierte bei 375 px die Beschriftung sichtbar — der Ortsname auf
"Bil..." gekuerzt, der Fallback-Satz quer ueber den Filterwoertern
"TOTAL/ANNULAR", die Horizontrose ueber den Jahreszahlen der Zeitleiste.

**Einschraenkung:** Das 3D-Modell lud auch beim zweiten Ansehen nicht (403,
siehe 2.1). Gesehen wurde also die **degradierte** Mobilansicht, nicht ihre
normale. Ueber deren eigentliches Telefonverhalten ist weiterhin nichts
gesagt.

**Was daraus folgt:** Andres Punkt "man kann sich gut bewegen" beschreibt
eine Breitbild-Erfahrung. Ihre Struktur — Ereignisse an ihrer echten
Himmelsposition, freie Umsicht — auf 375 px zu uebertragen, reproduziert
genau diese Kollision. Das ist der zweite, unabhaengige Grund gegen das
Ortsmodell, neben dem Fremddienst aus 2.1.

# Teil 5 — Was der Hausstandard nicht abdeckt

Er hat **keine Regeln fuer erzeugte Grafik**. `poisson-dor` und
`rezept-grid` bestehen aus Karten, Tabellen, Chips und Pillen; dieses
Projekt besteht zu zwei Dritteln aus einem generierten SVG. Dort greifen die
Hausregeln nicht: Schrift im SVG kennt kein `rem` und skaliert nicht mit der
Seite, das Bild bringt seinen eigenen Hintergrund mit, und Abstands- wie
Radienleiter haben im `viewBox`-Koordinatensystem keine Bedeutung.

Die Regeln, die in T-0010 dafuer erfunden wurden — sie sind kein Hausgut,
sondern eine Ergaenzung fuer dieses Projekt:

1. **Mindestgrad 11 px im gerenderten Zustand**, nicht im `viewBox`. Daraus
   rueckwaerts der zulaessige `viewBox`: Bilddeckel 480 px, Telefonanzeige
   319 px, also 420er `viewBox` und Grad 15 -> 11,4 px.
2. **Text, den man lesen muss, gehoert ins HTML.** Im SVG bleibt nur, was
   von seiner Position lebt: Achsenzahlen und der Ortsname. Datum, Stufe,
   Uhrzeit und der Ueberhoehungshinweis stehen als echter Text daneben.
3. **Farbe ausnahmslos aus den Tokens**, geschrieben als
   `var(--name, <Fallback>)`, wobei der Fallback ebenfalls aus der
   Token-Datei gelesen wird — er traegt `diagnose.html` und
   `rueckschau.html`, die `tokens.css` nicht inlinen. Ausgenommen sind
   `#000`/`#fff` in Masken: das sind Deckkraftwerte 0 und 1, keine Farben.
