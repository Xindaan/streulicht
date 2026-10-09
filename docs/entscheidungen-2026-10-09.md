# Entscheidungsvorlagen zum Review 09.10.2026 (T-0084 bis T-0087)

Stand 09.10.2026. Grundlage: `docs/review-2026-10-09.md` (gegengepruefte
Befunde). Andre hat am 09.10. per Kurzfrage schon gewaehlt; diese Vorlage
liefert die Begruendung nach und **korrigiert zwei Punkte meiner Kurzfrage**
(bei 1 eine fehlende Option, bei 4 eine falsche Kostenaussage). Die vier
Entscheidungen sind getrennt entscheidbar; nur 1 und 3 beruehren beide die
Klimatologie und sollten nicht gleichzeitig umgebaut werden.

## Kurzfassung

| # | Entscheidung | Andres Wahl 09.10. | Empfehlung jetzt | Umkehrbar | Aufwand |
|---|---|---|---|---|---|
| 1 | Wie werden "auffaellig"/"selten" auf der Seite bestimmt? | A: aus Median-Verteilung neu eichen | **B: an die Member-Anteile koppeln** (neue Option) | ja, Konstanten | 2-3 h |
| 2 | "Zwei bis zehn Tage im Voraus" abschwaechen? | A: abschwaechen | **A** (unveraendert) | ja, Text | 30 min |
| 3 | Sichtfaktor raumwinkelgewichten? | A: erst messen | **A** (unveraendert) | ja | 0,5-1 Tag Messung |
| 4 | Nachhol-Lauf nach 00 UTC, wenn ein Tag ohne Ergebnis blieb? | A: einbauen | **A, mit Kostenbedingung** | ja, Konfig | 2-3 h |

Bei 2 und 3 bleibt alles wie gewaehlt. Bei 1 und 4 bitte einmal pruefen, ob die
Wahl mit den Korrekturen weiter traegt.

---

## 1. Perzentil-Zonen auf der Prognoseseite (T-0084)

**Entscheidungssatz:** Sollen die Stufen "auffaellig" und "selten" kuenftig aus
dem Anteil der Modelllaeufe (Member) bestimmt werden, die im obersten Fuenftel
bzw. ueber der Push-Schwelle liegen (B) - statt wie gewaehlt aus einer neu
geeichten Median-Verteilung (A)?

**Problem.** Symptom: "selten" erscheint praktisch nie, "auffaellig" halb so oft
wie der Name verspricht. Ursache (belegt): `skripte/seite.py:327` ordnet den
**Median der 51 Member** in die Verteilung **einzelner** Analyse-Abende der
Klimatologie ein (`seite.py:828-833`, Zonen 0,80/0,95 in `seite.py:116-117`).
Ein Median streut weniger als ein Einzelwert, er erreicht die oberen Raender
deshalb seltener.

**Faktenlage** (Methodik-Gate, gemessen am Tagesarchiv `daten/archiv/berlin/`,
737 Abendvorhersagen aus 59 Zielabenden - Fachaussage, kein Artefakt):

| | Rang >= 0,80 ("auffaellig") | Rang >= 0,95 ("selten") |
|---|---|---|
| Median der Member, alle Vorlaeufe | 10,0 % | 0,3 % |
| Median, Vorlauf 0-1 Tage | 17,9 % | 1,5 % |
| Median, Vorlauf >= 5 Tage | 2,2 % | 0 % |
| einzelne Member | 24,7 % | 5,0 % |
| Klimatologie, gleiches Saisonfenster | 25,4 % | 5,9 % |

Die einzelnen Member treffen die Klimatologie also gut; nur der Median nicht.
Zusaetzlich (seiten#2): "selten" haengt am Rang, der Push an s\* - beide stimmen
heute nur ueberein, weil s\* zufaellig fast genau auf dem 95. Perzentil liegt.
**Vorbehalt:** 59 Abende, nur Spaetsommer/Herbst, untereinander korreliert; 27
der 67 Archivdateien stammen aus der Zeit vor dem Advektionsfix (04.09.).

**Folgen, wenn es bleibt.** Die Seite untertreibt systematisch; die Bilanz
vergleicht Noten mit einer verzerrten Stufe; aendert sich s\* (z. B. fuer
WeatherNext 3, T-0072), laufen Stufe und Push auseinander.

**Bis wann:** keine harte Frist. Sinnvoll vor der naechsten Auswertung der
Noten (T-0078/F9), sonst rechnet sie mit der verzerrten Stufe.

**Warum jetzt:** muessen wir nicht - ich frage, weil T-0084 sonst nach A gebaut
wuerde und A an der duennen Datenbasis haengt.

**Alternativen**

| | Was | Aufwand | Umkehrbar | Preis / Risiko |
|---|---|---|---|---|
| A | Zonen aus der Verteilung archivierter Median-Werte neu eichen (deine Wahl) | 2-3 h + Auswertung | ja | Sauber nutzbar sind nur Laeufe ab 04.09. (~40 Archivtage, nur Herbst): Schwellen saisonal verzerrt, muessen nach Winter und Fruehjahr nachgezogen werden. Push und Stufe bleiben entkoppelt. |
| B | Zonen aus dem **Anteil der Member**: "selten" = mindestens die Haelfte ueber s\* (= genau die Push-Bedingung), "auffaellig" = mindestens die Haelfte im obersten Fuenftel des Jahres - oder ein niedrigerer Anteil, z. B. ein Viertel | 2-3 h | ja | Kein neuer Datenbedarf, Push und "selten" koennen nie auseinanderlaufen. Bedeutung aendert sich von "Position im Jahr" zu "wie viele Modelllaeufe sehen es so" - Seitentexte muessen mit. Der Anteil fuer "auffaellig" ist eine Setzung. |
| C | Zahlen lassen, Beschriftung ehrlich machen ("Median der Modelllaeufe gegen Einzelabende") | 30 min | ja | Seite bleibt untertreibend, nur erklaert. |
| D | Nichts tun | 0 | - | "selten" erscheint praktisch nie (ab Vorlauf 1 Tag in den Daten nie), "auffaellig" in 10 statt rund 25 % der Faelle. |

**Empfehlung: B.** Es nutzt die Groesse, die nachweislich kalibriert ist (die
einzelnen Member), braucht keine Daten, die wir noch nicht haben, und behebt
nebenbei den Strukturfehler seiten#2. **Preis:** Die Stufe heisst kuenftig etwas
anderes; wer die Seite kennt, muss umlernen, und der Anteil fuer "auffaellig"
ist eine Wahl, keine Messung.

**Was gegen B spricht:** "Perzentil des Jahres" ist eine anschauliche Aussage,
"Anteil der Modelllaeufe" eine technische - fuer Freund:innen als Nutzer:innen
ist A naeher an dem, was sie verstehen.

**Was ich nicht weiss:** wie haeufig "auffaellig" unter B mit Anteil Haelfte
bzw. Viertel waere (nicht gerechnet). **Kippt die Empfehlung**, wenn B mit
keinem vernuenftigen Anteil auf rund 20-25 % "auffaellig" kommt - dann A.

---

## 2. Vorlauf-Versprechen (T-0085)

**Entscheidungssatz:** README Zeile 3 und die Seitentexte von "zwei bis zehn
Tage im Voraus" auf "ab etwa 1-3 Tagen belastbar, weiter voraus nur Tendenz"
aendern: ja oder nein?

**Problem.** Symptom: Das Produktversprechen passt nicht zu dem, was der
Betrieb liefert. Ursache (wahrscheinlich): Die Vorhersagbarkeit von hohen
Wolken und Fenstern auf 200-400 km faellt nach 1-2 Tagen stark ab; belegt ist
nur das Ergebnis, nicht der Mechanismus.

**Faktenlage** (Methodik-Gate, Tagesarchiv, Fachaussage): p >= 0,5 (Push) kam
bisher zweimal vor, **beide Male erst am Abend selbst** (Vorlauf 0; 26.09. und
30.09., je p = 0,57). Am 26.09. lag p bei Vorlauf 1-3 bei 0,20-0,27, am 30.09.
bei Vorlauf 2-7 bei 0,04-0,25. p >= 0,3 kam nie bei Vorlauf > 3 vor.
Uebereinstimmung mit Vorlauf 0: rho 0,84 bei 1 Tag, ~0,6 bei 2-4 Tagen, danach
verrauscht. **Vorbehalt:** zwei Alarme, 59 Abende, ein Herbst.

**Folgen, wenn es bleibt.** Nutzer:innen planen nach einer Zahl von vor fuenf
Tagen, die fast nie Bestand hat; der erste Push kommt praktisch immer am selben
Nachmittag.

**Bis wann / warum jetzt:** keine Frist; reine Ehrlichkeit nach aussen.

| | Was | Aufwand | Umkehrbar | Preis / Risiko |
|---|---|---|---|---|
| A | Versprechen abschwaechen (deine Wahl) | 30 min | ja | Produkt klingt bescheidener; bei mehr Daten evtl. zu vorsichtig. |
| B | Text bleibt, als **Ziel** gekennzeichnet | 15 min | ja | Ehrlich, aber das Versprechen steht weiter vorn. |
| C | Vorlauf aktiv verlaengern: zusaetzliche "Vorwarnung" bei p >= 0,3 ab 2 Tagen | 0,5 Tag + Kalibrierung | ja | Mehr Pushs mit niedriger Trefferquote; p >= 0,3 trat bei Vorlauf > 3 nie auf, also wenig Gewinn. |
| D | Nichts tun | 0 | - | Versprechen und Leistung bleiben auseinander. |

**Empfehlung: A.** Billig, umkehrbar, und die Daten tragen nichts anderes.
**Preis:** Nach Winter und Fruehjahr kann sich zeigen, dass 3-4 Tage oefter
tragen - dann den Text wieder anheben.
**Gegenargument:** Zwei Alarme sind keine Statistik; ein schlechter Herbst
koennte das Bild verzerren.
**Was die Empfehlung kippt:** wenn ueber den Winter Pushs regelmaessig schon bei
Vorlauf 2-3 kommen und halten.

---

## 3. Sichtfaktor-Gewichtung (T-0086)

**Entscheidungssatz:** Vor jeder Aenderung am Score zuerst messen, wie oft der
Fall vorkommt und wie sich Klimatologie und s\* mit raumwinkelgewichtetem
Sichtfaktor verschieben: ja oder nein?

**Problem.** Symptom (konstruiert, nicht beobachtet): Eine geschlossene tiefe
Decke nur ueber der Stadt unter einem hohen Schirm 0,9 ergibt S = 0,75, also
einen Member ueber s\*. Ursache (belegt): `sonnen/score.py:185-208` mittelt die
6 Sichtzellen gleich gewichtet, der Standort zaehlt 1/6; Term A gewichtet
denselben Standort mit 75 % (hohe) bzw. 89 % (mittlere Schicht). Mit
Raumwinkelgewichten waere S = 0,229 (Physik-Gate, nachgerechnet). Eine bewusste
Entscheidung fuer die Gleichgewichtung ist nirgends dokumentiert.

**Faktenlage:** Wie oft der Fall real vorkommt, ist **ungemessen** - das Archiv
speichert keine Zellwerte je Member. Die Klimatologie-Rohdaten liegen in
`daten/roh/` (24 MB, IFS-Analysen 2015-2025); ob sie alle 6 Sichtzellen
enthalten, ist nicht geprueft.

**Folgen, wenn es bleibt.** Moegliche Fehlalarme bei "Deckel ueber der Stadt,
draussen frei". Groesse unbekannt.

**Bis wann / warum jetzt:** keine Frist. Aber nicht gleichzeitig mit
Entscheidung 1 umbauen: beide verschieben, was "ueber der Schwelle" heisst.

| | Was | Aufwand | Umkehrbar | Preis / Risiko |
|---|---|---|---|---|
| A | Erst messen: Haeufigkeit aus den Rohdaten, Klimatologie und s\* fuer beide Varianten (deine Wahl) | 0,5-1 Tag | ja | Reichen die Rohdaten nicht, braucht es Archivabrufe bei Open-Meteo - Kontingent, mit Gardena geteilt. |
| B | Sofort raumwinkelgewichten, s\* neu bestimmen | 1 Tag | ja, mit Arbeit | Aendert jede Zahl der Kalibrierung; ohne Messung unklar, ob es besser wird. |
| C | Bewusst gleich gewichtet lassen und das im Code begruenden | 15 min | ja | Moegliche Fehlalarme bleiben, aber dokumentiert. |
| D | Nichts tun | 0 | - | Wie C, nur undokumentiert - die naechste Durchsicht findet es wieder. |

**Empfehlung: A.** Ohne Haeufigkeit ist jede Aenderung am Score eine Wette.
**Preis:** Ein halber bis ganzer Tag, unter Umstaenden Kontingent.
**Gegenargument:** Der Fall ist konstruiert; vielleicht kommt er nie vor, dann
ist die Messung verschwendet und C waere billiger.
**Was die Empfehlung kippt:** Zeigt ein erster Blick in `daten/roh/`, dass die
Sichtzellen fehlen und nur Abrufe helfen, dann erst C und spaeter messen.

---

## 4. Nachtluecke (T-0087)

**Entscheidungssatz:** Soll `alarm.py` nach 00 UTC einen Nachhol-Lauf fuer die
Folgetage machen, wenn der Vortag ohne erfolgreichen Lauf blieb - auch wenn er
einen vollen Abruf kosten kann?

**Korrektur meiner Kurzfrage.** Ich hatte ihn "mit dem neuen Zwischenspeicher
billig" genannt. Das stimmt nur halb: Der Blockcache aus T-0074 gilt je
**Modelllauf und UTC-Abruftag** (`skripte/alarm.py:402-426`). Nach Mitternacht
UTC beginnt also ein neuer Cache; der Nachhol-Lauf kostet einen vollen Abruf
(heute rund 380 Ortsabrufe) - allerdings aus dem frischen Tageskontingent. Er
kann den Vormittagslauf um 09:20 UTC verbilligen, wenn beide denselben
Modelllauf bekommen (dann holt der Vormittagslauf alles aus dem Cache).

**Problem.** Symptom: Scheitern Vormittags- und Abendlauf, wird bis zum
naechsten Vormittag gar nicht gerechnet - auch nicht fuer die Folgetage.
Ursache (belegt): `im_laufenster()` kennt nur das Vormittagsfenster und das
Nachholen des Abendlaufs bis Sonnenuntergang (`alarm.py`, Review alarm#6).

**Faktenlage** (Alarm-Gate, `daten/alarm.log`): Seit 16.09. gab es zehn Tage
ohne einen einzigen erfolgreichen Lauf. Der Vormittagslauf bekam in 13 von 13
Faellen den 18z-Lauf des Vortags (Messung T-0065). Ab wann der 18z nachts
verfuegbar ist, ist **nicht gemessen** - davon haengt ab, ob Nacht- und
Vormittagslauf denselben Cache teilen. Das Wecken um 02:00 wirkt
(in allen 6 im Energielog sichtbaren Naechten, betrieb#8), und alle 50 Laeufe
ohne Netz seit 24.09. lagen zwischen 07 und 22 Uhr, keiner nachts (betrieb#4).

**Folgen, wenn es bleibt.** Nach einem gescheiterten Tag bleibt die
Prognoseseite bis zum naechsten Vormittag mindestens einen Tag alt; ein
moeglicher Alarm fuer die Folgetage kommt einen halben Tag spaeter.

**Bis wann / warum jetzt:** keine Frist; der Nutzen ist am groessten, solange
die Ausfallserie anhaelt.

| | Was | Aufwand | Umkehrbar | Preis / Risiko |
|---|---|---|---|---|
| A | Nachhol-Lauf nach 00 UTC (z. B. um 02:20 lokal, nach dem Wecken), nur wenn der Vortag ohne Erfolg blieb (deine Wahl) | 2-3 h + Test | ja, Konfigschalter | Ein voller Abruf aus dem neuen Tageskontingent; teilen Nacht- und Vormittagslauf den Modelllauf nicht, kostet der Tag zwei volle Laeufe. |
| B | Wie A, aber nur, wenn der Nachtlauf denselben Modelllauf bekommt wie voraussichtlich der Vormittagslauf - sonst warten | 3-4 h | ja | Spart Kontingent, kann aber gerade dann ausfallen, wenn er gebraucht wird; haengt an der ungemessenen Verfuegbarkeit. |
| C | Vormittagsfenster verbreitern (Nachholen bis Mittag statt Nachtlauf) | 1-2 h | ja | Kein Nachtlauf, aber der Mac ist tagsueber oft ohne Netz - genau dort scheiterten die Laeufe. |
| D | Nichts tun | 0 | - | Nach jedem gescheiterten Tag bis zu ~14 h ohne neue Prognose. |

**Empfehlung: A, mit einer Kostenbedingung:** Der Nachtlauf startet nur, wenn
keine Kontingentsperre aus T-0074 aktiv ist, und schreibt den bekommenen
Modelllauf ins Log, damit nach zwei Wochen messbar ist, ob Nacht- und
Vormittagslauf den Cache teilen. **Preis:** im schlechtesten Fall ein voller
Abruf mehr pro Ausfalltag.
**Gegenargument:** Das Kontingent ist der Hauptgrund der Ausfaelle; jeder
zusaetzliche Lauf verschaerft es, solange die Gewichtung der Abrufe ungeklaert
ist (alarm#3/#4).
**Was die Empfehlung kippt:** wenn die ersten Wochen mit T-0074 zeigen, dass
schon der normale Tageslauf das Kontingent knapp ausreizt - dann B.

---

## Nach der Entscheidung

Andres Antworten zu 1 und 4 bitte in TASK.md bei T-0084 und T-0087 nachtragen
(oder mir sagen); 2 und 3 stehen dort schon. Kein Beschluss bleibt nur im Chat.
