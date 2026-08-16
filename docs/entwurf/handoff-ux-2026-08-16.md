# Handoff: Streulicht UX-Overhaul

## Überblick

Neuentwurf der Oberfläche von **Streulicht** (`github.com/Xindaan/streulicht`) — dem
Sonnenuntergangs-Alarm für Berlin. Betroffen sind fünf Flächen:

1. **Prognoseseite** (heute `web/index.html`, erzeugt von `skripte/seite.py`)
2. **Bewertungsseite vor der Abgabe** (heute `web/bewerten-berlin.html`, erzeugt von
   `skripte/bewertungsseite.py`)
3. **Bewertungsseite nach der Abgabe** — neu: die Prognose wird erst nach der
   Abgabe freigelegt (Entscheidung vom 15.08.2026, ersetzt „bleibt blind")
4. **Rückschau** (heute `web/rueckschau.html` / `diagnose.html`)
5. **Push-Nachricht** auf dem Sperrbildschirm (`skripte/alarm.py`,
   `skripte/erinnerung.py`)

Der Auftrag lautete: „modern, clever, angenehm zum Anschauen, schöne Grafik". Die
alte Seite hat denselben Schriftstack und dieselben Token wie der Entwurf — sie
sah trotzdem generisch aus, weil sie zehn identische Punkte und ein abstraktes
Diagramm zeigte und die eigentliche Frage („lohnt sich diese Woche?") nie
beantwortete.

## Zu den Entwurfsdateien

Die Dateien in diesem Paket sind **Entwurfsreferenzen in HTML** — Prototypen, die
Aussehen und Verhalten zeigen. Sie sind **kein Produktionscode zum Kopieren**.

Die Umsetzung gehört in die bestehende Architektur des Repos, und die ist
ungewöhnlich, aber bindend (bestätigt in der Rückfrage vom 15.08.2026):

- **Ein Python-Generator schreibt eine einzelne self-contained HTML-Datei.**
  `skripte/seite.py` baut `web/index.html`, `skripte/bewertungsseite.py` baut
  `web/bewerten-<ort>.html`. Kein Build, kein Bundler, kein CDN, kein Netzzugriff
  zur Laufzeit.
- **`stil/tokens.css` ist die einzige Farb- und Maßquelle.** Sie wird von
  `skripte/tokens.py` gelesen und von `seite.py` in den `<style>`-Block der
  erzeugten Seite **inlined**. `skripte/schnitt.py` liest dieselben Werte, damit
  im SVG keine feste Farbe steht — geschrieben als `var(--name, <Fallback>)`,
  wobei der Fallback ebenfalls aus der Token-Datei kommt (er trägt
  `diagnose.html` und `rueckschau.html`, die `tokens.css` nicht inlinen).
- **Die Grafiken werden in Python erzeugt**, nicht im Browser. Der Vertikalschnitt
  entsteht heute in `skripte/schnitt.py`; die neue Fassung und die Fächerkarte
  gehören dorthin.
- **Ausgeliefert wird über `skripte/ausliefern.py`** nach `gh-pages`, als
  einzelner Commit mit `--force`, mit einer **ausdrücklichen Dateiliste**.
  `diagnose.html` und `rueckschau.html` dürfen nicht mit ins Netz (Albumabende
  neben Bewertungen; 9,5 MB).

**Die JavaScript-Logik in den Entwurfsdateien ist Dokumentation der Rechenwege,
nicht die Zielsprache.** Alles, was dort in JS steht — Strahlgeometrie,
Transmission, Bänderdicke, Farbmischung — ist in Python zu portieren und läuft
zur Erzeugungszeit, nicht im Browser. Im Browser bleibt nur, was auf Tippen
reagiert: Abendauswahl, Notenknöpfe.

## Fidelity

**Hi-fi.** Farben, Grade, Abstände, Radien, Schatten und Bewegungskurven sind
exakt und stammen ausnahmslos aus `stil/tokens.css`. Der Entwurf ist
pixelgenau nachzubauen.

Zusätzlich liegt im Paket **`Streulicht heute (Bestand).dc.html`** — der
pixelgenaue Nachbau der *heutigen* Seite, gebaut aus `web/index.html` und
`daten/zustand.json`. Er dient als Vergleichsmaßstab: was sich ändert und was
absichtlich gleich bleibt.

## Daten in den Entwürfen

**Alle Zahlen sind echt**, bis auf zwei ausdrücklich gekennzeichnete Ausnahmen.

Quelle ist `daten/zustand.json` (Lauf vom 15.08.2026, Ort `berlin`), zehn Abende
16.08.–25.08.2026. Aufbereitet liegen sie hier als:

| Datei | Inhalt |
|---|---|
| `daten/abende.json` | die `META`-Liste, wie `seite.py` sie in die Seite schreibt |
| `daten/entwurf.json` | dieselben Abende plus `median`, `schirm`, `A`, `sicht`, `weg`, `azimut`, `zellen` |
| `daten/felder.json` | je Abend die 31 Fächerzellen als `[lat, lon, low, mid, high]` |
| `daten/schnitte.json` | die zehn **originalen** SVGs aus `web/index.html` (für den Bestandsnachbau) |

Die zehn Abende in Zahlen:

| Tag | Perzentil | Wahrsch. | Median | Schirm | Azimut | SU (Ortszeit) |
|---|---|---|---|---|---|---|
| So 16.08. | 0,481 | 2 % | 0,0305 | mid | 293,98° | 20:30 |
| Mo 17.08. | 0,682 | 0 % | 0,1257 | mid | 293,39° | 20:28 |
| Di 18.08. | 0,478 | 4 % | 0,0285 | mid | 292,88° | 20:26 |
| Mi 19.08. | 0,695 | 4 % | 0,1327 | mid | 292,31° | 20:24 |
| Do 20.08. | 0,655 | 6 % | 0,1083 | high | 291,73° | 20:21 |
| Fr 21.08. | 0,633 | 6 % | 0,0973 | mid | 291,16° | 20:19 |
| Sa 22.08. | 0,624 | 4 % | 0,0908 | high | 290,58° | 20:17 |
| **So 23.08.** | **0,792** | **6 %** | **0,2519** | mid | 290,00° | 20:15 |
| Mo 24.08. | 0,519 | 8 % | 0,0419 | high | 289,42° | 20:13 |
| Di 25.08. | 0,722 | 8 % | 0,1590 | high | 288,84° | 20:11 |

Der 23.08. ist der beste Abend im Fenster und die Vorauswahl.

**Zwei gekennzeichnete Erfindungen:**

1. **Push-Mock, „62 %".** Kein Abend im Fenster erreicht
   `schwelle_wahrscheinlichkeit` = 0,5 (Maximum 7,8 %). Ohne einen konstruierten
   Wert wäre der Alarmfall nicht zu zeigen. Der Entwurf trägt die Kennzeichnung
   **auf dem Schirm**: „KONSTRUIERTE 62 % — KEIN ECHTER ABEND". Diese
   Kennzeichnung ist Teil des Entwurfs und darf in der Umsetzung entfallen, weil
   dort ein echter Abend eingesetzt wird.
2. **Note „4 von 5" auf Schirm 3.** Die einzige echte Bewertung in
   `zustand.json` ist der 15.08. mit Note 3 — für diesen Abend wurde aber
   **keine Prognose gerechnet** (`prognose_eintraege()` überspringt ihn:
   „bewertet, aber nie prognostiziert"). Um die Freilegungsmechanik zu zeigen,
   braucht Schirm 3 einen Abend *mit* Prognose. Gewählt: der 23.08. mit einer
   angenommenen Note 4. Die freigelegten Prognosewerte (79. Perzentil, 6 %,
   Median 0,2519) sind echt. Schirm 4 zeigt weiter die echte Bewertung vom
   15.08. samt korrektem Hinweis, dass dafür nichts gerechnet wurde.

## Design-Tokens

Vollständig in `tokens.css` (im Paket beigelegt). Nur Dunkel — bewusst **kein**
`prefers-color-scheme`-Block, weil ein Hellsatz kein Token-Tausch, sondern ein
eigener Entwurf für Wolkenbänder und Strahl wäre.

### Flächen
```
--papier    #000000
--karte     #1c1c1e
--flaeche2  #2c2c2e
```

### Tinte
```
--tinte     #f2f2f7   18,82:1 auf Papier
--tinte2    #d1d1d6   11,18:1 auf Karte
--gedaempft #98989d    7,31:1 auf Papier
```

### Linien
```
--linie          #2c2c2e   dekorativ
--achse          #38383a   dekorativ, 1,79:1 — trägt NIE Information
--gitter         #8e8e93   6,44:1 auf Papier, 5,22:1 auf Karte — alles
                           Informationstragende nimmt diesen Wert
--gitter-schwach #636366   nur Dekoratives
```

### Akzent — genau einer, und der ist warm
```
--akzent         #ff9f0a
--akzent-tinte   #ffb340
--akzent-flaeche #332412
```
Drei Zustände statt einer Ampel: **selten** = gefüllte Marke, **auffällig** =
offene Marke in derselben Farbe, **unauffällig** = `--gedaempft`, gar keine Farbe.

### Himmel (nur für die Grafik)
```
--wolke         #c7c7cc
--strahl-hell   #ffb340
--strahl-dunkel #3a2a12
--boden         #2c2c2e
```

### Typografie
```
--schrift: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
           "Segoe UI", system-ui, Roboto, sans-serif
--grad-basis     15px
--zeilen-basis   1.5
--sperrung-eng   -.022em    Basis
--sperrung-enger -.03em     ab großen Graden
--sperrung-label .06em      Eyebrow, versal
```
Kein Webfont, keine woff2. `font-variant-numeric: tabular-nums` global,
`-webkit-font-smoothing: antialiased`.

Gradleiter im Entwurf: 68 / 44 / 32 / 26 / 23 / 19 / 17 / 15 / 14 / 13 / 12 / 11.

### Maß
```
--s1..--s8   4 8 12 16 20 26 34 56
Radien       8 (Mikro) / 13 (Kachel) / 18 (Karte) / 22 (Tafel) / 999 (Pille)
--breite-schmal 720px
--breite-bild   480px
--tastflaeche   44px
```

### Schatten
Regel: Karten in Ruhe tragen `--schatten-ruhe`. Der große Schatten ist Hover-
oder Overlay-Zustand.
```
--schatten-ruhe    0 .5px 1.5px rgba(0,0,0,.5), 0 1px 2px rgba(0,0,0,.4)
--schatten-hover   0 1px 2px  rgba(0,0,0,.5), 0 8px 22px rgba(0,0,0,.5)
--schatten-leiste  0 2px 8px  rgba(0,0,0,.5), 0 22px 50px rgba(0,0,0,.6)
```

### Bewegung
```
--zeit-schnell .12s
--zeit         .15s
--kurve        cubic-bezier(.2, .7, .2, 1)
```
`@media (prefers-reduced-motion: reduce) { *{transition:none!important;
animation:none!important} }` — im Entwurf vorhanden, im Hausstandard
(`rezept-grid`) nicht.

---

# Schirme

## 1 · Prognose

**Zweck.** Beantwortet „lohnt sich diese Woche?" — und sagt ausdrücklich, wenn
die Antwort nein ist.

**Breite.** 390 px (Telefon zuerst). Einspaltig.

### 1.1 Topbar

`position: sticky; top: 0; z-index: 5`, `padding: 14px 18px 12px`,
`background: rgba(0,0,0,.72)`, `backdrop-filter: blur(18px) saturate(1.4)`
(mit `-webkit-`-Präfix), `border-bottom: 1px solid #1c1c1e`.
Flex, `space-between`.

- links Wortmarke „Streulicht", 17px/800, `letter-spacing: -.03em`
- rechts Ortspille „Berlin", `padding: 3px 11px`, `border-radius: 999px`,
  `background: #1c1c1e`, `color: #d1d1d6`, 12px/700

In der Umsetzung zusätzlich `env(safe-area-inset-top)` aufs Padding.

### 1.2 Korpuszeile

`padding: 20px 18px 0`. 12px/700, `letter-spacing: .06em`, versal,
`color: #98989d`:

> 10 ABENDE VORAUSGERECHNET · 2 BIS 10 TAGE

Das Muster stammt aus der Zweitreferenz (`eclipses.bogachev.fr`: „54 eclipses
seen from Bilbao · 1700–2100"). Es benennt den Korpus, statt ihn vorauszusetzen.

### 1.3 Hero

`margin-top: 16px`.

| Element | Stil | Inhalt |
|---|---|---|
| Eyebrow | 12px/700, `.06em`, versal, `#98989d` | „BESTER ABEND IM FENSTER" bzw. „GEWÄHLTER ABEND" |
| Datum | 23px/700, `-.03em`, `#f2f2f7`, `margin-top: 2px` | „Sonntag, 23. August" |
| **Stufe** | **44px/800**, `line-height: 1.02`, `-.04em`, Farbe nach Stufe, `margin-top: 8px` | „unauffällig" |
| Grund | 14px, `#d1d1d6`, `text-wrap: pretty`, `margin-top: 6px` | „Mittelhohe Wolken, Licht kommt von Westen frei durch." |
| Zahlen | 13px, `#98989d`, `margin-top: 10px` | „79. Perzentil des Jahres · 6 % Wahrscheinlichkeit · Sonnenuntergang 20:15 Uhr" |

**Die Stufe führt, die Prozentzahl steht daneben** — bestätigte Regel. Begründung
unverändert aus dem Docstring von `seite.py`: belegt ist, dass der Score
außergewöhnliche Abende von gewöhnlichen trennt, nicht dass er unter den guten
ordnet.

Stufenschwellen und Farben:
```python
if rang >= 0.95: ("selten",       "#ffb340")   # --akzent-tinte
if rang >= 0.80: ("auffällig",    "#ff9f0a")   # --akzent
else:            ("unauffällig",  "#98989d")   # --gedaempft
```

**Die Grundzeile ist `begruendung()` aus `alarm.py`, wörtlich** — dieselben
Schwellen, nur satzinitial großgeschrieben und mit Punkt:

```python
schirm = {"high": "Hohe Wolken", "mid": "Mittelhohe Wolken"}.get(e["schirm"], "Wolken")
teile = [schirm if (e["A"] or 0) >= 0.35 else "Wenig " + schirm.lower()]
if (e["weg"] or 0) >= 0.6:   teile.append("Licht kommt von Westen frei durch")
elif (e["weg"] or 0) >= 0.3: teile.append("Lichtweg nach Westen teils frei")
if (e["sicht"] or 1) < 0.5:  teile.append("aber tiefe Decke über der Stadt")
```

Bewusst **nicht** „klarer Westhorizont": der Score prüft keine Sichtbedingung.

### 1.4 Himmelsband

Volle Breite, **76 px hoch**, randlos, direkt unter dem Hero (`margin-top: 20px`).
Darunter 12px/`#98989d`, `margin: 8px 18px 0`:

> Lichteindruck, schematisch — aus dem Score dieses Abends.

Das ist die Stelle, an der die Seite schön wird. Ein SVG mit
`viewBox="0 0 100 20" preserveAspectRatio="none"`, zwei übereinanderliegende
Verläufe:

**Waagerecht** — fünf Stopps, die zwischen einem stumpfen und einem glühenden
Satz interpoliert werden, Mischanteil `t`:

```python
t = clamp(median / 0.7065 * staerke, 0, 1)      # 0.7065 = s* aus konfig.json
DUMPF = ["#1e1e22", "#26262a", "#2e2d2b", "#28282b", "#202024"]
GLUT  = ["#1c1226", "#5e2a28", "#c8661c", "#ffb340", "#ffe6bd"]
stop[i] = mix(DUMPF[i], GLUT[i], t)   at offset i/4
```

**Senkrecht** darüber, damit das Band Volumen bekommt statt flach zu liegen:
```
#000 @ 0.00  opacity .55
#000 @ 0.62  opacity  0
#000 @ 1.00  opacity .35
```

Damit ist das Band **kein Dekor**: eine gewöhnliche Woche bleibt sichtbar stumpf
(23.08.: t = 0,357), ein seltener Abend glüht. Genau diese Spannweite fehlte der
alten Seite. `GLUT` und `DUMPF` sind aus `--wolke`, `--strahl-dunkel`,
`--strahl-hell` und `--akzent` abgeleitet und gehören nach `tokens.css`, sobald
sie im Betrieb stehen.

### 1.5 Zeitachse — die Hauptgrafik

Ersetzt den Kachelstreifen. **Die Achse ist die Navigation.** Übernahme aus der
Zweitreferenz: eine Achse liest sich als Zeit, Kästchen lesen sich als Kacheln.

`margin-top: 26px`. Kopfzeile darüber, `padding: 0 18px 10px`, flex
`space-between`, beide 12px:
- links „ZEHN ABENDE", 700, `.06em`, versal, `#98989d`
- rechts „Perzentil des Jahres", 400, `#98989d`

**Achsenkörper**: `padding: 0 18px`, `position: relative`, **Höhe 200 px**.
`y(p) = 200 * (1 - p)`, also Position = Perzentilrang, linear über 0…1.

Zonen (absolut, volle Breite):

| Zone | Bereich | Stil |
|---|---|---|
| selten | `p ≥ 0.95` | `top: 0; height: 10px; background: rgba(255,159,10,.18); border-bottom: 1px solid #ff9f0a` |
| auffällig | `0.80 ≤ p < 0.95` | `top: 10px; height: 30px; background: rgba(255,159,10,.07); border-bottom: 1px dashed #8e8e93` |

Zonenbeschriftung rechtsbündig, 11px/700, `letter-spacing: .04em`,
`transform: translateY(-100%)`, jeweils auf der Zonenunterkante:
„SELTEN 95." in `#ffb340`, „AUFFÄLLIG 80." in `#98989d`.

**Warum gefüllte Zonen und nicht zwei gestrichelte Linien:** die zehn Abende
liegen zwischen dem 48. und 79. Perzentil, also sichtbar weit unter beiden
Schwellen. Das ist die Aussage. Mit Linien allein sieht man Punkte im Nichts;
mit warmen Zonen sieht man, wie weit es bis dorthin ist. Und wenn ein seltener
Abend kommt, klettert seine Marke in die warme Zone — der Moment, für den die
Seite existiert.

**Verlaufslinie**: ein `<svg viewBox="0 0 100 100" preserveAspectRatio="none">`
über der ganzen Fläche, `overflow: visible`, `pointer-events: none`.
`<polyline>` mit `fill: none`, `stroke: #48484a`, `stroke-width: .7`,
`vector-effect: non-scaling-stroke`. Punkte in Prozent:
`x = (i + 0.5) / 10 * 100`, `y = (1 - p) * 100`.

**Marken**: `position: absolute; inset: 0; display: flex`, zehn `<button>` mit
`flex: 1; min-width: 0; height: 100%`, `background: transparent`,
`border-radius: 8px`. Jeder Knopf enthält zwei absolut positionierte `<i>`:

- **Fahne** — `left: 50%; width: 1px` (gewählt 2px), `top: y(p); bottom: 0`,
  `background: linear-gradient(to bottom, rgba(142,142,147,.16), transparent)`;
  gewählt `rgba(255,179,64,.62)`
- **Punkt** — `left: 50%; top: y(p)`, 11×11, `margin: -5.5px 0 0 -5.5px`,
  `border: 1.5px solid <Stufenfarbe>`, `border-radius: 999px`.
  `p ≥ 0.95`: `background: <Stufenfarbe>` **plus**
  `box-shadow: 0 0 12px rgba(255,179,64,.7)`; sonst `background: #000`.
  Gewählt: `transform: scale(1.45)`, Übergang
  `transform .15s cubic-bezier(.2,.7,.2,1), box-shadow .15s`

**Beschriftung** unter der Achse, `margin-top: 8px`, eigene Flexzeile mit
denselben `flex: 1`-Spalten (damit sie mit den Marken fluchtet):
Wochentag 11px/400 über Tageszahl 12px/600. Gewählt: `#f2f2f7`, sonst `#d1d1d6`;
Wochentag gewählt `#d1d1d6`, sonst `#98989d`.

> **Bewusste Abweichung vom Hausstandard, zu entscheiden.** Zehn Spalten in
> 358 px ergeben **35,8 px** Spaltenbreite, der Hausstandard verlangt 44 px
> Tastfläche. Dafür passt die ganze Achse ohne Rollen aufs Telefon, und die
> Tastfläche ist 36 × 200 px — vertikal weit über dem Mindestmaß. Die Alternative
> ist der Roller der heutigen Seite (`overflow-x: auto`,
> `scrollbar-width: none`, Abblendmasken links/rechts, `scrollLeft` direkt
> statt `scrollIntoView`) mit 44 px Spalten. Der Entwurf entscheidet sich gegen
> das Rollen, weil „Zeitachse als Hauptgrafik" das Ganze verlangt.

### 1.6 Vertikalschnitt — „Der Weg des Lichts"

Karte: `margin: 26px 18px 0`, `padding: 14px 12px 12px`, `background: #1c1c1e`,
`border: 1px solid #38383a`, `border-radius: 18px`, `--schatten-ruhe`.
Überschrift 12px/700 `.06em` versal `#98989d`, `margin: 0 4px 10px`.
Fußzeile 12px `#98989d`, `margin: 10px 4px 0`:

> Das Licht streift den Boden **267** km westlich. Höhe 22-fach überhöht,
> Bänderdicke schematisch.

Die 267 km sind die Tangentendistanz des gewählten Abends, gerechnet, nicht
gesetzt. Die 22-fache Überhöhung ist `(HO/YMAX)/(BR/XMAX)`.

**Dasselbe Bild wie heute, anders gezeichnet.** Geometrie:

```
viewBox 420 × 258     X0 = 44   Y0 = 16   BR = 346   HO = 190
XMAX = 460 km         YMAX = 12.5 km
px(d, z) = (X0 + BR*d/XMAX,  Y0 + HO*(1 - z/YMAX))
```

Grade im SVG **mindestens 15** (gerendert auf 358 px: 15 × 0,85 = 12,8 px). Regel
aus T-0010: Text, den man lesen muss, gehört ins HTML. Im SVG bleiben nur
Achsenzahlen und der Ortsname.

Was gegenüber `schnitt.py` neu ist:

1. **Himmel als Verlauf statt als Fläche.**
   `<linearGradient id="himmel" x1=0 x2=0 y1=0 y2=1>`: `#101014` → `#1d1d20`.
   Rechteck über den Plotrahmen, `rx: 6`.
2. **Wolkenbänder als Polygon statt als Rechteck mit Maske.** Ein graues
   Rechteck behauptet eine gleichmäßige Platte. Die Kontur wird dort schmal, wo
   weniger Wolke ist, und liest sich dadurch als Wolke:
   ```
   BAENDER = (("high", 7.6, 10.4), ("mid", 2.9, 5.4), ("low", 0.25, 1.6))
   zc = (unten + oben)/2      halb = (oben - unten)/2
   f(d) = 0.28 + 0.72 * min(1, deckung(d))
   Oberkante:  px(d, zc + halb*f(d))   d = 0..460 Schritt 10
   Unterkante: px(d, zc - halb*f(d))   rückwärts
   fill = url(#cg<nr>)   filter = feGaussianBlur stdDeviation 2.6
   ```
   Waagerechter Verlauf `cg<nr>`, Stopp alle 6 km:
   `stop-color: #c7c7cc`, `stop-opacity: min(0.85, 0.72 * deckung(d))`.
   Bänder ohne Bedeckung > 0,02 entfallen ganz.
3. **Deckung linear zwischen den Fächerstützstellen interpoliert** — wie
   `schnitt.wert()`. Ohne das rastet jede Abfrage auf die 0,5-Grad-Zelle und die
   Bänder bekommen Treppenkanten, die wie Struktur aussehen, aber keine sind.
   Stützstellen: `DISTANZEN_KM = (0, 60, 120, 180, 240, 300, 360, 420)`, jeweils
   auf der Mittelachse (`dv = 0`). Jenseits der letzten Stützstelle + 60 km: 0.
4. **Strahl doppelt gezeichnet** — Glut darunter, klare Linie darüber:
   ```
   Glut:  stroke-width 3 + 6*tr,   opacity 0.18 + 0.42*tr,  filter blur 3.2
   Linie: stroke-width 1.3 + 1.9*tr, ohne Filter
   Farbe: mix("#3a2a12", "#ffb340", tr)      # --strahl-dunkel → --strahl-hell
   Schritt 6 km
   ```
5. **Sonne mit Halo statt mit acht Zacken.** Kreis r = 16 in `#ffb340`,
   `opacity .22`, `filter blur 3.2`; darüber Kern r = 6,5 voll. Dazu eine
   Ellipse `rx 54 ry 30` mit Radialverlauf `#ffb340` `.55 → 0`.
6. **Horizontwäsche** — das Licht, das unter der Decke bis zum Beobachter kommt.
   Ellipse auf der Bodenlinie, zentriert auf dem Tangentenpunkt,
   `rx = (sx - X0 + 30)`, `ry = 38`, Radialverlauf
   `#ffb340` `0.55*t0 → 0.22*t0 @ .55 → 0`, wobei `t0` die Transmission bei
   d = 0 ist — dieselbe Zahl, die auch die Strahlhelligkeit trägt, keine freie
   Dekoration. **Auf den Plotrahmen beschnitten** (`clipPath`), sonst läuft der
   Schein über die Kartenkante.
7. **Boden** 5 px, `fill: #2c2c2e`, `stroke: #8e8e93` 0,7; dazu ein Ortsstrich
   bei d = 0, `stroke: #d1d1d6` 1,2, von 7 px über bis 5 px unter die Linie.

**Physik — unverändert aus dem Repo**, keine eigene Formel:

```python
R_ERDE_KM = 6371.0
R_EFF_KM  = 4/3 * R_ERDE_KM        # 8494.7, Standardrefraktion
SCHIRME   = (("high", 9.5), ("mid", 4.2))
GRENZE_LOW_MID_KM  = 2.0
GRENZE_MID_HIGH_KM = 6.3

D    = sqrt(2 * R_EFF_KM * h)             # Tangentendistanz
z(d) = (D - d)**2 / (2 * R_EFF_KM)        # Strahlhöhe
```

Transmission, ein Wert je 60-km-Ring, Schicht nach der Strahlhöhe in der
Ringmitte (Aufbau wie `score.py`):

```python
for a, b in zip(DISTANZEN_KM, DISTANZEN_KM[1:]):
    b = min(b, D)
    if a >= D: break
    m  = 0.5 * (a + b)
    zh = z(m)
    s  = "low" if zh < 2.0 else ("mid" if zh < 6.3 else "high")
    ringe.append((a, b, deckung(m, s)))

rest(d) = prod(1 - c for a, b, c in ringe if d < b)
```

> **Abweichung, bewusst:** `schnitt.py` nimmt heute die Segmentliste aus
> `det["segmente"]` des Score-Laufs. Die steht in `zustand.json` nicht (nur `A`,
> `sicht`, `weg` des besten Members), also rechnet der Entwurf die Ringe aus dem
> gespeicherten **Medianfeld** nach. Für das **Bild** ist das richtig; für die
> **Zahl** wäre es falsch (Jensen: der Score des Medianfelds ist nicht der
> Median der Scores). In der Umsetzung liegen die Segmente vor — dann die
> echten nehmen. Die Regel bleibt: **Bild aus dem Feld, jede Zahl aus dem
> Zustand.**

**Beschriftung.** Höhen 0/4/8/12 rechtsbündig bei `X0 - 9`, Grad 15; „km" bei
`X0 - 26`, Grad 14; Weiten 0/200/400 mittig bei `gy + 26`, Grad 15;
„km westlich" rechtsbündig und „Berlin" mittig über dem Nullpunkt bei
`gy + 46`, Grad 15, „Berlin" in `#d1d1d6`.

### 1.7 Fächerkarte — „Von oben"

Zweite Karte, `margin: 16px 18px 0`, sonst wie 1.6. Fußzeile:

> Die Wolkendecke westlich von Berlin auf dem Abfragefächer, und der Azimut des
> Sonnenuntergangs.

Beantwortet die Frage, die der Schnitt offenlässt: *wo* westlich. Sie ist der
Grund, warum eine Punktabfrage nicht reicht.

```
viewBox 420 × 214    SK = 0.60 px/km    Berlin bei (392, 186)
dx = (lon - 13.405) * 111.32 * cos(52.52°)      # West → negativ → links
dy = (lat - 52.52) * 110.57                      # Nord → oben
x = 392 + dx*SK      y = 186 - dy*SK
```

- Grund `#101014`, `rx 8`
- **Entfernungsringe** 200 und 400 km: `<circle>` um Berlin, `fill: none`,
  `stroke: #38383a` 0,9, `stroke-dasharray: 1 5`. Beschriftung 13px unten
  (`y = VBH - 8`), mittig auf dem linken Ringdurchstoß
- **Zellen**: je Fächerzelle ein `<rect>` von 0,5° × 0,5°
  (`cw = 0.5*111.32*cos(53.5°)*SK`, `ch = 0.5*110.57*SK`), `rx 5`,
  `fill: #c7c7cc`, `opacity = clamp(0.6 * deckung, 0.06, 0.6)`. Bedeckung ist
  die des **Schirmniveaus** dieses Abends (`mid` oder `high`). Alle Zellen in
  **einer Gruppe mit `feGaussianBlur stdDeviation 6`** — so lesen sie als Decke
  statt als Kacheln
- **Azimutstrahl** von Berlin zum Zielpunkt bei 460 km, zweifach: `stroke-width 5`
  `opacity .45` mit Blur 5, darüber `stroke-width 1.4` scharf. Verlauf
  `fray` von rechts nach links: `#ff9f0a` `.25` → `#ffb340` `.9` @ 0,58 →
  `#ffb340` `.12`
- **Tangentenpunkt** bei D km: Kreis r 13 `opacity .2` mit Blur, darüber r 4,5 voll
  `#ffb340`
- **Berlin**: Punkt r 3,5 `#f2f2f7`, Label rechtsbündig 14px `#d1d1d6` bei
  `(CX - 9, CY + 17)`
- oben links 13px: „Norden oben · km von Berlin"

Zielpunkt auf der Großkreisbahn (wie `sonnen/geometrie.zielpunkt`):
```python
dr = d / 6371.0
lat2 = asin(sin(lat)*cos(dr) + cos(lat)*sin(dr)*cos(azimut))
lon2 = lon + atan2(sin(azimut)*sin(dr)*cos(lat), cos(dr) - sin(lat)*sin(lat2))
```
Zellenschlüssel: `"%d/%d" % (round(lat/0.5), round(lon/0.5))`.

### 1.8 Fußtext

`margin: 26px 18px 0`, 13px, `line-height: 1.55`, `#98989d`,
`text-wrap: pretty`, `selten`/`auffällig` fett in `#d1d1d6`. **Wörtlich wie
heute**, unverändert:

> Die Stufe kommt aus der Position in der Jahresverteilung: **selten** ab dem
> 95. Perzentil (rund 18 Abende im Jahr), **auffällig** ab dem 80. Bewusst keine
> Prozentzahl — belegt ist, dass der Score außergewöhnliche Abende von
> gewöhnlichen trennt, nicht dass er unter den guten ordnet.

### 1.9 Push-Auskunft — das eigentlich Neue

`margin: 22px 18px 0`, `padding: 14px 16px`, `background: #1c1c1e`,
`border-radius: 13px`, 13px `#d1d1d6`.

Kein Abend über der Schwelle:

> Kein Abend im Fenster reißt die Schwelle von 50 % (höchstens 8 %). Es kommt
> kein Push. Das ist der normale Zustand: rund 18 Abende im Jahr sind es nicht.

Mindestens einer darüber:

> Dieser Abend reißt die Schwelle von 50 %. Der Push geht morgens um 7:30 raus —
> einmal, nicht zweimal.

Das sagt die heutige Seite nirgends, und es ist der häufigste Fall. Die 50 %
sind `schwelle_wahrscheinlichkeit` aus `konfig.json`, die 7:30 der
launchd-Termin von `de.greatbelow.streulicht.alarm`, „einmal, nicht zweimal" die
Idempotenz über `zustand["alarme"]`.

---

## 2 · Bewerten — vor der Abgabe

**Zweck.** Eine Zahl abgeben, ohne die Prognose zu sehen.

390 px, `min-height: 720px`, Flex-Spalte, `align-items: center`,
`justify-content: center`, `gap: 22px`, `padding: 34px 26px`.

Von oben:
1. Datum, 12px/700 `.06em` versal `#98989d`
2. „Wie war der Sonnenuntergang?", 23px/700, `line-height: 1.3`, `-.03em`,
   zentriert, `text-wrap: balance`, `max-width: 15ch` (erzwingt den Umbruch auf
   zwei Zeilen und damit eine berechenbare Kastenhöhe)
3. **Fünf Notenknöpfe**, flex `gap: 10px`: 48 × 48, `min-width/min-height: 44px`,
   `border-radius: 999px`, `border: 1px solid #38383a`, `background: #1c1c1e`,
   `color: #f2f2f7`, 19px/600.
   Gewählt: `border-color: #ff9f0a`, `background: #332412`, `color: #ffb340`.
   Übergang `transform .12s cubic-bezier(.2,.7,.2,1), background .15s,
   border-color .15s`; `:active { transform: scale(.92) }`
4. Legende, flex `space-between`, `max-width: 262px`, 12px `#98989d`:
   „1 = nichts" / „5 = spektakulär"
5. **„Nicht gesehen"** — Pille, `min-height: 44px`, `padding: 0 20px`,
   `border-radius: 999px`, `border: 1px solid #38383a`, transparent,
   `color: #98989d`, 14px. Gewählt: derselbe Akzentzustand wie die Ziffern.
   Hover: `border-color: #8e8e93`
6. Fotohinweis, `padding: 12px 16px`, `background: #1c1c1e`,
   `border-radius: 13px`, 13px `#d1d1d6`, zentriert — **wörtlich aus
   `bewerten-berlin.html`**
7. Blindheitshinweis, 12px `#98989d`, `max-width: 26ch`, zentriert — ebenfalls
   wörtlich

> **Note 0 ist eine echte Antwort**, nicht „nichts abgegeben":
> `bewerten-berlin.html` schreibt `eintrag.note === 0 ? "nicht gesehen" :
> eintrag.note + " von 5"` und setzt den ntfy-Tag `grey_question`. Der
> Anfangszustand muss deshalb ein anderer Wert sein (`null`), sonst ist der
> Knopf ein Blindgänger und der Schirm widerspricht sich.

Alles aus `bewerten-berlin.html` bleibt: `?a=1` aufgefordert / `?a=2` alarm /
sonst spontan; vor 04:00 zählt der Abend als gestern; lokale Warteschlange als
**Spiegel, nicht Quelle** (`liste` im Arbeitsspeicher, `localStorage`
zusätzlich); ntfy-Angaben im JSON-**Rumpf**, nicht als Kopfzeilen (sonst
CORS-Vorabflug); `AbortSignal.timeout(12000)`.

---

## 3 · Bewerten — danach freigelegt

**Zweck.** Die geänderte Entscheidung: die Prognose wird **nach** der Abgabe
gezeigt. Vorher bleibt sie verdeckt — das trägt die Blindheit, ohne die
Neugier zu bestrafen.

390 px, `min-height: 720px`, Flex-Spalte, `padding: 34px 0`.

1. `padding: 0 26px`: „ANGEKOMMEN" 12px/700 `.06em` versal in **`#ffb340`**;
   „Danke — 4 von 5" 26px/700 `-.03em`; „Sonntag, 23. August · auf Nachfrage
   bewertet" 14px `#98989d`
2. **Himmelsband**, `margin-top: 26px`, volle Breite, 76 px — mit dem
   **echten** Median dieses Abends (0,2519)
3. `padding: 20px 26px 0`: „VORHERGESAGT WAR" 12px/700 `.06em` versal
   `#98989d`; Stufe 32px/800 `-.03em` in der Stufenfarbe; „79. Perzentil des
   Jahres · 6 % Wahrscheinlichkeit" 13px `#98989d`; dann 13px `#d1d1d6`,
   `line-height: 1.55`:
   > Jetzt gehört die Zahl dem Himmel und nicht der Vorhersage. Genau dafür lag
   > sie vorher verdeckt.
4. `flex: 1` als Schub, dann CTA `padding: 0 26px`: Pille `min-height: 44px`,
   `background: #332412`, `color: #ffb340`, 14px/700, „Prognose der nächsten
   Abende" → Prognoseseite

> **Umsetzungshinweis.** Die Bewertungsseite kennt die Prognose heute nicht —
> sie wird von `bewertungsseite.py` erzeugt und enthält bewusst keine. Für die
> Freilegung muss `bewertungsseite.py` den Stand des **jeweiligen Abends** aus
> `zustand.json` mitschreiben, aber **verborgen** (nicht im DOM sichtbar vor der
> Abgabe, sonst ist die Blindheit nur optisch). Und: ist für den Abend keine
> Prognose gerechnet — genau der Fall des 15.08. — muss der Text das sagen,
> nicht schätzen. Wortlaut wie auf Schirm 4:
> „keine Prognose für diesen Abend gerechnet".

---

## 4 · Rückschau

**Zweck.** Was bisher gemessen ist. Und ehrlich sagen, was noch nicht.

390 px, `min-height: 720px`. Topbar wie 1.1, Wortmarke „Rückschau".
Inhalt `padding: 20px 18px 0`.

1. Korpuszeile: „1 BEWERTUNG SEIT DEM 15. AUGUST 2026", 12px/700 `.06em` versal
2. **Bewertungskarte**, `margin-top: 14px`, `padding: 16px`,
   `background: #1c1c1e`, `border: 1px solid #38383a`, `border-radius: 18px`:
   - Kopf flex `space-between`, `align-items: baseline`: „Sa 15.08." 15px/700;
     rechts „**3**/5" — die 3 in 26px/800 `-.03em` `#ffb340`, „/5" 13px `#98989d`
   - **Notenbalken**, flex `gap: 3px`, `margin-top: 12px`: fünf `<i>`,
     `flex: 1; height: 6px; border-radius: 999px`; drei in `#ffb340`, zwei in
     `#2c2c2e`
   - „Spontan bewertet · keine Prognose für diesen Abend gerechnet", 13px
     `#98989d`, `margin-top: 12px`
3. „WAS HIER SPÄTER STEHT", 12px/700 `.06em` versal, `margin-top: 22px`; darunter
   14px `#d1d1d6`:
   > Trefferquote, Alarmrate und die Schwelle, gegen die beide gemessen werden.
   > Alle drei brauchen Abende, die es noch nicht gibt.
4. Erläuterungskasten, `padding: 14px 16px`, `background: #1c1c1e`,
   `border-radius: 13px`, 13px `#98989d` — die Quantilbrücke (T-0020) in
   Klartext:
   > Die Schwelle stammt aus Analysefeldern, der Alarm rechnet auf
   > Ensemble-Membern. Ob dieselbe Schwelle dieselbe Rate ergibt, ist nie
   > gemessen worden — der Livegang ist die Messung. Nach sechs bis acht Wochen
   > wird sie nachgezogen.
5. `margin-top: 22px`, 13px `#98989d`:
   > Bis dahin gilt die Alarmrate als unbekannt, nicht als 18,5 pro Jahr.

**Kein leerer Zustand mit Platzhaltern.** Das Muster ist „ehrlicher Ersatz statt
Fehlermeldung" aus der Zweitreferenz — dort im Klartext auf der Seite. Hier: was
fehlt, warum es fehlt, und wann es kommt.

---

## 5 · Push auf dem Sperrbildschirm

**Zweck.** Prüfen, ob die zwei Nachrichten auf dem Sperrbildschirm taugen — sie
sind der eigentliche Auslieferungskanal.

390 px, `min-height: 720px`, Flex-Spalte, `align-items: center`,
`padding: 44px 16px 26px`. Grund:
```css
radial-gradient(120% 60% at 50% 100%, #241a0d 0%, #0b0b0d 55%, #000 100%)
```

1. Datum 13px/600 `#d1d1d6`; Uhrzeit **68px/300**, `-.04em`,
   `line-height: 1.05`
2. Zwei Benachrichtigungen, `margin-top: 34px`, flex-Spalte `gap: 10px`,
   volle Breite. Je `padding: 13px 15px`, `border-radius: 18px`,
   `backdrop-filter: blur(18px) saturate(1.4)`:
   - **Alarm** (`alarm.py`): `background: rgba(44,44,46,.72)`,
     `border: 1px solid rgba(142,142,147,.18)`. Kopf flex `gap: 8px`:
     App-Kachel 20 × 20 `border-radius: 6px` `background: #332412` mit Punkt
     8 × 8 `#ffb340`; Titel „Streulicht Berlin" 13px/700; rechts „jetzt" 12px
     `#98989d`. Rumpf 14px, `line-height: 1.45`:
     „So 23.08., 20:15 Uhr — 62 %. Mittelhohe Wolken, Licht kommt von Westen
     frei durch."
     Titel = `"Streulicht %s" % ort["anzeige"]`; Rumpf =
     `"%s %s, %s Uhr - %.0f %%. %s"` mit `begruendung(e)`; Priority `high`,
     Tag `sunrise`
   - **Erinnerung** (`erinnerung.py`): `background: rgba(44,44,46,.5)`,
     `border-color: rgba(142,142,147,.12)`, Kachel `#1c1c1e` mit Punkt
     `#8e8e93`, Titel „Wie war er?", rechts „gestern". Rumpf `#d1d1d6`:
     „Sonnenuntergang Berlin ist durch. Eine Zahl von 1 bis 5 — und ein Foto
     nach Westen, wenn Du magst."
     Priority `low`, Tag `sunny`, `Click` = `<basis>/bewerten-berlin.html?a=1`
3. `flex: 1`, dann Kennzeichnungspille (11px/700 `.06em` versal,
   `border: 1px solid #38383a`, `color: #8e8e93`): „KONSTRUIERTE 62 % — KEIN
   ECHTER ABEND"; darunter 12px `#98989d`, zentriert, `max-width: 30ch`:
   > Ein Alarm je Abend, höchstens. Die Aufforderung kommt jeden Abend — sonst
   > entstehen nur Labels für Alarmabende. In dieser Woche reißt kein Abend die
   > Schwelle; ohne einen erfundenen Wert wäre hier nichts zu zeigen.

---

## Interaktion und Verhalten

| Auslöser | Wirkung |
|---|---|
| Tippen auf eine Achsenmarke | wählt den Abend: Hero (Eyebrow, Datum, Stufe, Grund, Zahlen), Himmelsband, Vertikalschnitt und Fächerkarte aktualisieren; Punkt `scale(1.45)`, Fahne warm |
| Tippen auf eine Note 1–5 | Akzentzustand auf diesem Knopf, alle anderen zurück |
| Tippen auf „Nicht gesehen" | Note 0, Akzentzustand auf der Pille, Ziffern zurück |
| Hover auf Marke/Knopf | nur `@media (hover: hover)` |
| Fokus | `outline: 2px solid #ff9f0a; outline-offset: 2px` |

Übergänge ausschließlich `.12s` / `.15s` mit `cubic-bezier(.2,.7,.2,1)`, plus
der `prefers-reduced-motion`-Riegel. Keine Auftrittsanimationen — die Seite wird
mehrmals täglich geöffnet.

Vorauswahl beim Laden: der Abend mit dem höchsten Perzentil
(`beste = max(range(len(eintraege)), key=lambda i: eintraege[i]["p"])`, wie
heute). Kein `scrollIntoView` — es rollt alle scrollbaren Vorfahren mit.

## Zustand

| Größe | Werte | Auslöser |
|---|---|---|
| gewählter Abend | 0…9, Start = bester | Tippen auf Marke |
| Note | `null` (nichts abgegeben), 0 (nicht gesehen), 1…5 | Tippen |
| Fächerkarte sichtbar | `bool`, Standard an | Prop |
| Bandstärke | 0,4…1,6, Standard 1 | Prop |
| Demoabend | „Echte Woche" / „Seltener Abend (Demo)" | Prop |

Kein Datenholen zur Laufzeit: alles steht in der erzeugten Datei.
(Im Entwurf lädt `daten/felder.json` per `fetch`, weil eine `.dc.html` kein
Python-Generator ist. **Das ist ein Artefakt der Entwurfsumgebung** und in der
Umsetzung ersatzlos zu streichen — die Werte werden eingebettet.)

Die beiden Demo-Props gehören **nicht** ins Produkt. Sie existieren, damit sich
die Spannweite des Himmelsbandes und der Achse begutachten lässt, ohne auf einen
seltenen Abend zu warten. „Seltener Abend (Demo)" setzt für den gewählten Abend
`median = 0.781`, `p = 0.972`, `wahrsch = 0.62`.

## Assets

Keine. Keine Bilder, keine Icons, keine Webfonts, keine externen Dateien —
gewollt: „eine statische Datei, kein Build, kein CDN". Alles Grafische ist
erzeugtes SVG; alles Typografische kommt aus dem Systemstack.

## Dateien in diesem Paket

| Datei | Was |
|---|---|
| `Streulicht Entwurf.dc.html` | **der Entwurf**, fünf Schirme nebeneinander |
| `Streulicht heute (Bestand).dc.html` | pixelgenauer Nachbau der heutigen Seite |
| `support.js` | Laufzeit der Entwurfsumgebung — **nur** damit die beiden HTML-Dateien im Browser aufgehen. Nicht Teil des Entwurfs, nichts davon portieren |
| `tokens.css` | Kopie von `stil/tokens.css`, Stand 15.08.2026 |
| `daten/abende.json` | die zehn Abende als `META`, wie `seite.py` sie schreibt |
| `daten/entwurf.json` | dieselben Abende plus Termen, Azimut und Fächerzellen |
| `daten/felder.json` | Fächerzellen je Abend, `[lat, lon, low, mid, high]` |
| `daten/schnitte.json` | die zehn originalen SVGs aus `web/index.html` |
| `quelle/index.html` | die heutige Prognoseseite, unverändert |
| `quelle/bewerten-berlin.html` | die heutige Bewertungsseite, unverändert |
| `quelle/zustand.json` | Zustand vom 15.08.2026 |
| `quelle/konfig.json` | Konfiguration (Schwellen, Modell, Orte) |

Die Entwurfsdateien öffnen direkt im Browser (Doppelklick), `support.js` muss
daneben liegen.

## Reihenfolge der Umsetzung

1. **`stil/tokens.css` ergänzen**: die Bandrampen (`DUMPF`, `GLUT`) und die
   Himmelsverlaufsfarben `#101014` / `#1d1d20` als Token aufnehmen, damit auch
   die neue Grafik keine feste Farbe trägt.
2. **`skripte/schnitt.py`**: Polygonbänder, doppelter Strahl, Sonnenhalo,
   Horizontwäsche, Himmelsverlauf. Neue Fläche `viewBox 420 × 258`. Die
   ausführliche Fassung (840 × 490) für `diagnose.html` mitziehen oder
   ausdrücklich unverändert lassen.
3. **`skripte/faecher.py`** (neu) oder eine zweite Funktion in `schnitt.py` für
   die Draufsicht.
4. **`skripte/seite.py`**: Topbar, Korpuszeile, Hero mit `begruendung()`,
   Himmelsband, Zeitachse mit Zonen und Verlaufslinie, die zwei Grafikkarten,
   Fußtext, Push-Auskunft. Die Achsengeometrie bleibt in Python
   (`SAEULE_PX`-Nachfolger: 200), damit Zonen, Linie und Marken **ein**
   Koordinatensystem benutzen.
5. **`skripte/bewertungsseite.py`**: Notenknöpfe auf den neuen Zustand
   (`null` / 0 / 1–5), „Nicht gesehen" als echter Zustand, Freilegung nach der
   Abgabe samt verborgenem Prognosestand und dem ehrlichen Sonderfall.
6. **`skripte/rueckschau.py`**: Korpuszeile, Bewertungskarten, Erläuterungskästen.
7. **`skripte/ausliefern.py`**: Dateiliste prüfen — die Prognoseseite bleibt
   draußen (Bauartefakt und Verankerungsrisiko: sie zeigt die Prognose, die die
   Bewertungsseite verbirgt).

## Offene Entscheidungen für die Umsetzung

1. **35,8 px Spaltenbreite** in der Zeitachse gegen 44 px plus Roller (1.5).
2. **Segmenttransmission**: die echten `det["segmente"]` verdrahten statt der
   Ringnachrechnung aus dem Medianfeld (1.6).
3. **Prognosestand auf der Bewertungsseite** verbergen, ohne ihn ins DOM zu
   schreiben — oder erst nach der Abgabe nachladen, was dem Grundsatz „kein
   Netzzugriff" widerspricht (3).
4. **Ort als URL-Parameter** (`?ort=berlin`): im Entwurf steht „Berlin" als
   Pille in der Topbar, also die Stelle, an der ein Ortswechsel sitzen würde.
   Vorbereitet, nicht gebaut — die Notizen dazu stehen im Kopf von `seite.py`,
   die Abhängigkeiten sind T-0013 und T-0007.
