# Handoff: Streulicht Desktop-Fassung

## Überblick

Die Prognoseseite von **Streulicht** (`github.com/Xindaan/streulicht`) für den
großen Schirm. Sie ergänzt die am 16.08.2026 umgesetzte Telefonfassung
(T-0031 bis T-0034) — sie ersetzt sie nicht.

Anlass: `web/index.html` ist auf `max-width: 390px` zentriert. Auf einem
MacBook steht die Seite damit als schmales Band in einem schwarzen Feld, und
alles, was der Overhaul gewonnen hat — Himmelsband, Achse mit Zonen, die
beiden Grafiken — bleibt auf Telefonmaß.

**Der Inhalt ist unverändert.** Kein neues Bauteil, keine neue Zahl, kein
neuer Satz. Was sich ändert, ist ausschließlich die Anordnung, und zwar an
fünf Stellen, an denen die Telefonfassung durch ihre Breite eingeschränkt war.

## Zu dieser Entwurfsdatei

`Streulicht Desktop.dc.html` ist eine **Entwurfsreferenz in HTML** — ein
Prototyp, der Aussehen und Verhalten zeigt. Kein Produktionscode zum
Kopieren.

Die Umsetzung gehört in die bestehende Architektur, und die ist unverändert
bindend:

- **`skripte/seite.py` schreibt eine einzelne self-contained HTML-Datei.**
  Kein Build, kein Bundler, kein CDN, kein Netzzugriff zur Laufzeit.
- **`stil/tokens.css` bleibt die einzige Farb- und Maßquelle**, von
  `skripte/tokens.py` gelesen und in den Style-Block inlined.
- **Die Grafiken entstehen in Python** (`schnitt.py`, `faecher.py`,
  `band.py`) zur Erzeugungszeit, nicht im Browser.
- **`skripte/ausliefern.py`** liefert mit ausdrücklicher Dateiliste aus. Die
  Produktseite bleibt draußen (Bauartefakt, Verankerungsrisiko).

**Das JavaScript in der Entwurfsdatei dokumentiert Rechenwege, es ist nicht
die Zielsprache.** Im Browser bleibt nur, was auf Eingabe reagiert:
Abendauswahl per Klick und per Pfeiltaste.

## Fidelity

**Hi-fi.** Alle Farben, Grade, Abstände, Radien und Schatten stammen aus
`stil/tokens.css`. Zwei Werte sind gegenüber dem ersten Entwurf ausdrücklich
korrigiert worden, weil sie die Token-Regel verletzt hatten:

| Element | falsch | richtig | Regel |
|---|---|---|---|
| Rangzahlen auf der Achse | `#636366` (3,51:1) | `--gedaempft` `#98989d` (7,31:1) | informationstragender Text nimmt nie `--gitter-schwach` |
| Verlaufslinie der Achse | `#48484a` (frei erfunden) | `--achse` `#38383a` | genau der Wert, den `seite.py` über `tokens.werte()["--achse"]` setzt |

## Daten

**Alle Zahlen sind echt und nichts ist erfunden.** Quelle ist die `META` aus
`web/index.html`, Stand 16.08.2026 — also der Lauf, der heute ausgeliefert
wird. Elf Abende, 16.08. bis 26.08.2026. Die Vertikalschnitte und
Fächerkarten sind **die originalen SVGs aus dieser Datei**, nicht
nachgerechnet.

| Tag | Perzentil | Wahrsch. | Median | SU | Grund |
|---|---|---|---|---|---|
| So 16.08. | 48. | 2 % | 0,0305 | 20:30 | Mittelhohe Wolken, Licht kommt von Westen frei durch. |
| Mo 17.08. | 75. | 0 % | 0,1928 | 20:28 | Mittelhohe Wolken, Lichtweg nach Westen teils frei. |
| Di 18.08. | 59. | 0 % | 0,0706 | 20:26 | Mittelhohe Wolken, Lichtweg nach Westen teils frei. |
| Mi 19.08. | 68. | 2 % | 0,1265 | 20:24 | Hohe Wolken, Licht kommt von Westen frei durch. |
| Do 20.08. | 79. | 4 % | 0,2485 | 20:21 | Mittelhohe Wolken, Licht kommt von Westen frei durch. |
| Fr 21.08. | 61. | 4 % | 0,0853 | 20:19 | Mittelhohe Wolken, Licht kommt von Westen frei durch. |
| Sa 22.08. | 59. | 4 % | 0,0687 | 20:17 | Mittelhohe Wolken, Licht kommt von Westen frei durch. |
| So 23.08. | 64. | 12 % | 0,1025 | 20:15 | Mittelhohe Wolken, Licht kommt von Westen frei durch. |
| Mo 24.08. | 65. | 6 % | 0,1073 | 20:13 | Mittelhohe Wolken, Licht kommt von Westen frei durch. |
| **Di 25.08.** | **80.** | 12 % | 0,2685 | 20:11 | Mittelhohe Wolken, Licht kommt von Westen frei durch. |
| Mi 26.08. | 76. | 2 % | 0,1958 | 20:09 | Mittelhohe Wolken, Licht kommt von Westen frei durch. |

Vorauswahl ist der **16.08.** — der nächste Abend, nach T-0033. Der 25.08.
ist der beste im Fenster und bekommt dann das Eyebrow „Bester Abend im
Fenster". Kein Abend reißt die 50-%-Schwelle.

Aufbereitet liegen die Daten hier als `daten2/abende.json` (Text je Abend)
und `daten2/bilder.json` (Schnitt, Fächerkarte, Band je Abend).

---

# Was die Breite ändert

Fünf Stellen. Jede löst eine Einschränkung, die es nur auf 390 px gab.

## 1 · Das Himmelsband wird der Kopf der Seite

**Telefon:** ein 76 px hoher Streifen zwischen Hero und Achse.
**Desktop:** randlos über die volle Fensterbreite, **400 px hoch**, mit dem
Hero-Text darauf.

```
section  position:relative; height:400px; overflow:hidden
  div#band   position:absolute; inset:0
  div        position:absolute; inset:0
             linear-gradient(100deg,
               rgba(0,0,0,.92) 0%, rgba(0,0,0,.74) 34%,
               rgba(0,0,0,.18) 68%, rgba(0,0,0,.35) 100%)
  div        position:absolute; inset:0
             linear-gradient(to bottom,
               rgba(0,0,0,.45) 0%, transparent 26%,
               transparent 62%, rgba(0,0,0,.7) 100%)
  div        box-sizing:border-box; position:relative; height:100%
             max-width:1240px; margin:0 auto; padding:0 40px 38px
             display:flex; flex-direction:column; justify-content:flex-end
```

Zwei Schleier, weil das Band seine Helligkeit ändern **soll**: der
waagerechte hält die linke Hälfte dunkel, damit der Text bei einem glühenden
Abend lesbar bleibt; der senkrechte setzt oben und unten ab. Ohne sie wäre
entweder der Text am 25.08. unlesbar oder das Band am 16.08. sinnlos
aufgehellt.

Das Band selbst bleibt **unverändert `band.py`** — dieselbe Rampe, derselbe
Anteil `t = median / s*`, `s* = 0.7065`. Es glüht nicht schöner, es ist nur
groß genug, dass man den Unterschied zwischen 16.08. (t = 0,043) und 25.08.
(t = 0,380) sieht. Auf 76 px sah man ihn nicht.

> **`box-sizing: border-box` ist hier nicht optional.** Der Container ist
> `height:100%` in einer 400-px-Section mit `overflow:hidden`. Unter
> `content-box` addiert sich die Polsterung auf 438 px, die unteren 38 px
> werden abgeschnitten, und die Bodenluft verschwindet an **jeder**
> Fensterbreite. `seite.py` hat den Reset `*{box-sizing:border-box}` als
> erste Regel nach `__TOKENS__` — er löst das mit.

Bandbeschriftung („Lichteindruck, schematisch — aus dem Score dieses
Abends.") sitzt oben rechts im Hero, 12 px `--gedaempft`, nicht mehr unter
dem Streifen.

## 2 · Die drei Zahlen werden beschriftete Kennzahlen

**Telefon:** eine Zeile Fließtext, mit `·` verkettet —
„48. Perzentil des Jahres · 2 % Wahrscheinlichkeit · Sonnenuntergang 20:30 Uhr".

**Desktop:** drei Blöcke nebeneinander, `display:flex; gap:56px`.

```
Label   11px / 700 / letter-spacing .06em / uppercase / --gedaempft
Wert    26px / 700 / letter-spacing -.03em / --tinte / margin-top 3px
```

| PERZENTIL DES JAHRES | WAHRSCHEINLICHKEIT | SONNENUNTERGANG |
|---|---|---|
| 48. | 2 % | 20:30 Uhr |

Die drei Zahlen dürfen nicht verwechselt werden, und die Punktkette lädt
genau dazu ein: das **Perzentil** ist der klimatologische Rang des
Member-Medians („wie selten"), die **Wahrscheinlichkeit** der Anteil der
Ensemble-Member über s\* („wie sicher"). Mit eigener Beschriftung sagt jede
Zahl selbst, was sie ist.

Übriger Hero, von oben:

| Element | Stil |
|---|---|
| Eyebrow | 12px/700, `.06em`, versal, `--gedaempft` |
| Datum | 28px/700, `-.03em`, `--tinte`, `margin-top: 6px` |
| **Stufe** | **76px/800**, `line-height: 1`, `-.04em`, Stufenfarbe, `margin-top: 10px` |
| Grund | 17px, `--tinte2`, `max-width: 46ch`, `line-height: 1.45`, `text-wrap: pretty` |
| Kennzahlen | `margin-top: 26px` |

Stufenschwellen unverändert: ≥ 0,95 „selten" `--akzent-tinte`, ≥ 0,80
„auffällig" `--akzent`, sonst „unauffällig" `--gedaempft`.

## 3 · Die Achse trägt den Perzentilrang je Abend

Das ist der eigentliche Gewinn. Auf dem Telefon waren die Spalten 36 px
breit — für eine Zahl unter der Marke war kein Platz, also musste man jeden
Abend antippen, um sein Perzentil zu erfahren. Bei elf Spalten auf 1160 px
sind es **105 px**, und die Zahl passt.

```
Achsenhöhe    260px          y(p) = 260 * (1 - p)
Zone selten       top 0     height 13px   rgba(255,159,10,.18)  border-bottom 1px solid --akzent
Zone auffällig    top 13px  height 39px   rgba(255,159,10,.07)  border-bottom 1px dashed --gitter
```

Kopfzeile darüber, `space-between`: links „ELF ABENDE" (12px/700, `.06em`,
versal), rechts „Perzentil des Jahres · ← → blättert" (13px).

Je Marke ein `<button>` mit `flex:1; height:100%`, darin drei absolute
Kinder:

- **Fahne** — `left:50%`, `top:y(p)`, `bottom:0`, 1 px (gewählt 2 px),
  `linear-gradient(to bottom, rgba(142,142,147,.16), transparent)`;
  gewählt `rgba(255,179,64,.62)`
- **Punkt** — 12 × 12, `border: 1.5px solid` Stufenfarbe, `background: --papier`;
  ab dem 95. Perzentil gefüllt **plus** `box-shadow: 0 0 14px rgba(255,179,64,.7)`.
  Gewählt `transform: scale(1.5)`
- **Rangzahl** — `top: y(p) + 14px`, 12px/600, zentriert,
  gewählt `--tinte`, sonst **`--gedaempft`**

Verlaufslinie unverändert als `<svg viewBox="0 0 100 100"
preserveAspectRatio="none">`, `stroke="var(--achse)"`, `stroke-width .7`,
`vector-effect: non-scaling-stroke`.

Beschriftung darunter in einer eigenen Flexzeile mit denselben
`flex:1`-Spalten: Wochentag 12 px über Tageszahl 13px/600.

**Die 44-px-Frage ist damit erledigt.** Der erste Entwurf musste auf 35,8 px
Spaltenbreite abweichen, weil zehn Spalten sonst nicht aufs Telefon passten.
Auf dem Desktop sind es 105 px — über dem Hausmaß, ohne Zugeständnis.

## 4 · Schnitt und Fächerkarte liegen nebeneinander

Auf dem Telefon scrollt man zwischen zwei Ansichten **derselben Wolkendecke**
hin und her: der Schnitt zeigt, was auf dem Lichtweg liegt, die Karte, wo
westlich es liegt. Nebeneinander liest man sie zusammen.

```css
display: grid;
grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
gap: 20px;
align-items: start;
```

> **Die Mindestbreite ist die eigentliche Regel, nicht das Verhältnis.** Der
> erste Entwurf hatte `1.42fr 1fr` — ohne untere Schranke. Die Karte ist die
> schmale Spalte, ihre Beschriftung sitzt mit 13 Einheiten in einer
> 420er-viewBox und skaliert proportional mit. Gemessen: bei 720 px
> Fensterbreite (ein halbbreites Safari-Fenster auf genau dem 1440er-Display,
> für das die Fassung gebaut ist) fiel sie auf **6,9 px**. Das ist dieselbe
> Fehlerklasse, die T-0010 als einen der drei echten Fehler behoben hat
> (Beschriftung im Vertikalschnitt bei 3,5–4,3 px).
>
> Mit `minmax(420px, 1fr)` bricht das Raster unterhalb ~900 px auf eine
> Spalte um; die Grafiken werden dabei **größer** statt kleiner. Nachgemessen
> über 1440 / 1024 / 860 / 720 / 600 px: die Kartenbeschriftung liegt
> nirgends unter 13 px.
>
> Der Preis ist das 1,42:1-Verhältnis — die Spalten sind jetzt gleich breit.
> Kein Verlust: beide SVGs sind 420 Einheiten breit, gleiche Spalten sind die
> natürliche Paarung.

Karten: `padding: 16px 16px 14px`, `background: --karte`,
`border: 1px solid --achse`, `border-radius: --radius-karte`,
`box-shadow: --schatten-ruhe`. Titel 12px/700 `.06em` versal `--gedaempft`.
Fußzeilen 12 px `--gedaempft`, Wortlaut **unverändert aus `seite.py`**:

> Der Strahl, der bei Sonnenuntergang von Westen ankommt, und die
> Wolkenschichten auf seinem Weg. Höhe 20-fach überhöht.

> Die Wolkendecke westlich von Berlin auf dem Abfragefächer, und der Azimut
> des Sonnenuntergangs.

## 5 · Kopfzeile statt Korpuszeile und Fußpille

Drei Dinge, die auf dem Telefon über die Seite verteilt lagen, sitzen auf dem
Desktop in einer Leiste:

```
[ Streulicht  (Berlin) ]        [ 11 ABENDE … 16.08. BIS 26.08. ]  [ Was bisher gemessen ist ]
```

`position: sticky; top: 0; height: 56px`, `background: rgba(0,0,0,.72)`,
`backdrop-filter: blur(18px) saturate(1.4)` (mit `-webkit-`-Präfix),
`border-bottom: 1px solid --karte`.

Die Korpuszeile („11 ABENDE VORAUSGERECHNET · 16.08. BIS 26.08.") war auf dem
Telefon ein eigener Absatz über dem Hero; sie benennt den Bestand und gehört
damit in die Leiste. Der Verweis auf die Bilanzseite war eine Pille ganz
unten; auf dem Desktop ist die Leiste oben rechts der Ort dafür.

> **Die Leiste ist randlos, ihr Inhalt fluchtet.** Der erste Entwurf hatte
> `padding: 0 40px` auf der Leiste selbst — die Wortmarke stand damit auf
> einem 1440er-Schirm 100 px links der Inhaltsspalte, und die linke Kante der
> Seite brach direkt unter dem Kopf. Der Inhalt liegt jetzt im **selben
> 1240er-Container** wie alles darunter; die Fläche der Leiste bleibt
> randlos.

Nachgemessen bei 1440 px: Kopfzeile, Hero-Überschrift, Achse und beide
Grafikkarten beginnen alle bei **x = 140**. Versatz 0.

---

## Interaktion

| Auslöser | Wirkung |
|---|---|
| Klick auf eine Achsenmarke | wählt den Abend: Hero, Kennzahlen, Himmelsband, Vertikalschnitt und Fächerkarte aktualisieren |
| **← / →** | blättert einen Abend zurück/vor, an den Enden gedeckelt |
| Hover | nur `@media (hover: hover)` |
| Fokus | `outline: 2px solid --akzent; outline-offset: 2px` |

Die Pfeiltasten sind der einzige Zusatz gegenüber der Telefonfassung, und sie
sind kein Zierrat: auf einem Gerät mit Tastatur ist Durchblättern die
natürliche Bewegung durch zehn Abende. Sie stehen in der Achsenkopfzeile
angeschrieben („← → blättert"), sonst findet sie niemand.

Übergänge ausschließlich `--zeit` (.15s) mit `--kurve`, plus der
`prefers-reduced-motion`-Riegel. Keine Auftrittsanimationen — die Seite wird
mehrmals täglich geöffnet.

## Zustand

| Größe | Werte | Auslöser |
|---|---|---|
| gewählter Abend | 0…10, Start = nächster Abend | Klick, Pfeiltaste |
| Demoabend | „Echte Woche" / „Seltener Abend (Demo)" | Prop, **nicht fürs Produkt** |
| Bandstärke | 0,4…1,8, Standard 1 | Prop, **nicht fürs Produkt** |

Die beiden Props existieren, damit sich die Spannweite des Himmelsbandes
begutachten lässt, ohne auf einen seltenen Abend zu warten. „Seltener Abend
(Demo)" setzt für den gewählten Abend `p = 0.972`, `wahrsch = 0.62` und das
Band auf `t = 1`.

Kein Datenholen zur Laufzeit im Produkt: alles steht in der erzeugten Datei.
(Die Entwurfsdatei lädt `daten2/bilder.json` per `fetch`, weil eine
`.dc.html` kein Python-Generator ist. **Artefakt der Entwurfsumgebung**, in
der Umsetzung ersatzlos zu streichen.)

## Assets

Keine. Keine Bilder, keine Icons, keine Webfonts. Alles Grafische ist
erzeugtes SVG, alles Typografische kommt aus dem Systemstack.

---

## Umsetzung

Die offene Frage zuerst: **eine Datei oder zwei.**

Der Entwurf ist als eigene Desktop-Fassung gebaut, nicht als Breakpoint der
Telefonseite. Beides ist möglich:

**(a) Eine Datei mit Media Query.** `seite.py` schreibt beide Layouts in
denselben Style-Block, `@media (min-width: 1000px)` schaltet um. Ein
Dateiname, ein Lauf, eine URL. Der Style-Block wird dafür deutlich größer,
und die Achse braucht **zwei Höhen** (200 px und 260 px) — die Marken werden
in Python mit `top:%.1fpx` inline gesetzt, also müsste `ACHSE_PX` als
CSS-Variable in beide Regelsätze statt als Python-Konstante in die Marken.

**(b) Zwei Dateien aus denselben Daten.** `seite.py` bekommt eine zweite
Vorlage und schreibt `web/index.html` und `web/desktop.html`. Die
Datenaufbereitung (`prognose_eintraege`, Bilder, Band) bleibt unangetastet,
nur `VORLAGE` und der Markup-Aufbau in `main()` gibt es zweimal. Kostet eine
Weiche beim Ausliefern und die Frage, welche URL die Hauptadresse ist.

Ich empfehle **(a)**, weil eine URL für ein privates Werkzeug weniger
Verwaltung ist als zwei, und weil die Datenaufbereitung ohnehin identisch
bleibt. Aber die Entscheidung hängt daran, wie unangenehm der doppelte
Style-Block in `seite.py` werden darf — das ist eher Deine Frage als meine.

Danach, in dieser Reihenfolge:

1. **`ACHSE_PX` beweglich machen.** Heute steht die Achsenhöhe als
   Python-Konstante und wandert über `y(p)` in jeden Marken-Inlinestil. Für
   zwei Höhen muss sie eine CSS-Variable werden und die Marken müssen
   prozentual statt in Pixeln positioniert werden (`top: %.2f%%`), sonst
   stimmt bei 260 px keine einzige Marke. **Das ist der einzige Umbau, der
   bestehenden Code anfasst; alles andere ist Markup und CSS.**
2. **Kopfzeile** mit Wortmarke, Ortspille, Korpuszeile und dem Verweis auf
   `bisher.html`; Inhalt im 1240er-Container, Fläche randlos.
3. **Hero** mit dem Band als Grund, den zwei Schleiern und den drei
   Kennzahlenblöcken. `box-sizing: border-box` beachten (siehe 1).
4. **Achse** auf 260 px mit Rangzahlen unter den Marken.
5. **Grafikraster** mit `repeat(auto-fit, minmax(420px, 1fr))`.
6. **Pfeiltasten** im Skriptblock: `keydown` auf `document`, links/rechts,
   an den Enden gedeckelt, `preventDefault` nur bei Treffer.
7. **`skripte/test_seiten.py`** um die Desktop-Ausgabe erweitern, falls (b).

## Was bewusst NICHT geändert wurde

- Die Stufen und ihre Schwellen (95. / 80. Perzentil).
- Die Regel „keine Prozentzahl als Hauptaussage" — die Stufe führt weiter,
  die Wahrscheinlichkeit steht daneben.
- Der Wortlaut sämtlicher Texte: Grundzeile aus `begruendung()`, Fußtext zur
  Stufe, beide Kartenfußzeilen, die Push-Auskunft.
- Die Vorauswahl (nächster Abend, T-0033) und das Eyebrow „Bester Abend im
  Fenster".
- Sämtliche Grafiken: `schnitt_neu()`, `faecher.svg()`, `band.svg()` liefern
  unverändert dieselben Bilder.
- Nur Dunkel. Ein Hellsatz wäre kein Token-Tausch, sondern ein eigener
  Entwurf für Wolkenbänder und Strahl.

## Dateien in diesem Paket

| Datei | Was |
|---|---|
| `Streulicht Desktop.dc.html` | **der Entwurf** |
| `support.js` | Laufzeit der Entwurfsumgebung — nur damit die Datei im Browser aufgeht. Nichts davon portieren |
| `tokens.css` | Kopie von `stil/tokens.css`, Stand 16.08.2026 |
| `daten2/abende.json` | die elf Abende, Text |
| `daten2/bilder.json` | Schnitt, Fächerkarte und Band je Abend, aus `web/index.html` |
| `quelle2/index.html` | die heutige Telefonfassung, unverändert |
| `quelle2/bisher.html` | die Bilanzseite, unverändert |
| `quelle2/zustand.json` | Zustand vom 16.08.2026 |

Die Entwurfsdatei öffnet direkt im Browser (Doppelklick), `support.js` und
`daten2/` müssen daneben liegen. Fenster auf mindestens 1200 px ziehen.
