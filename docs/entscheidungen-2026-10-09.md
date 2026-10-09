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

**Nachtrag 09.10.2026 (T-0084 umgesetzt): die Auswertung, die oben fehlte.**
Die Empfehlung kippt nicht: mit einem Memberanteil von 37 % (19 von 51) kommt
B auf 19,3 % "auffaellig", also auf das, was das 80. Perzentil verspricht.

*Wie gerechnet.* Alle Abendvorhersagen aus `daten/archiv/berlin/*.json`, die
nach dem Advektionsfix geholt wurden (ab 04.09.2026 14:50 UTC): 440
Vorhersagen aus 40 Archivdateien fuer 44 Zielabende, je 51 Member (keine
datenlosen). Je Vorhersage der Anteil der Member, deren Score in der
Klimatologie (`score_berlin_g0.5_2022_2025.json`) den Rang >= 0,80 hat (Rang =
Anteil der Abende strikt darunter, wie `seite.perzentil`). Vorlauf = Zielabend
minus Lauftag. Das Rechenskript liegt nicht im Repo (Einmalauswertung); der
Rechenweg steht hier vollstaendig.

*Haeufigkeit von "Memberanteil >= q" (Anteil der Vorhersagen in %):*

| q | alle (440) | Vorlauf 0-1 (80) | Vorlauf 2-4 (120) | Vorlauf >= 5 (240) |
|---|---|---|---|---|
| 12/51 = 0,235 | 46,8 | 42,5 | 49,2 | 47,1 |
| 14/51 = 0,275 | 36,6 | 37,5 | 44,2 | 32,5 |
| 16/51 = 0,314 | 27,5 | 32,5 | 37,5 | 20,8 |
| 17/51 = 0,333 | 24,5 | 31,2 | 35,8 | 16,7 |
| 18/51 = 0,353 | 21,4 | 27,5 | 34,2 | 12,9 |
| **19/51 = 0,373 (gewaehlt)** | **19,3** | **27,5** | **32,5** | **10,0** |
| 20/51 = 0,392 | 17,5 | 26,2 | 31,7 | 7,5 |
| 22/51 = 0,431 | 15,5 | 25,0 | 29,2 | 5,4 |
| 26/51 = 0,510 (Haelfte) | 9,5 | 16,2 | 22,5 | 0,8 |

Dazu "selten" (p >= 0,5): 2 von 440 (0,5 %), beide bei Vorlauf 0-1 (2 von 80 =
2,5 %); ab Vorlauf 2 nie. Und zur Gegenprobe: "Median im Rang >= 0,80" ist
mathematisch dasselbe wie "Memberanteil >= 26/51" (die Mitte von 51 ist der
26. Wert) und bestaetigt die 9,5 % der Vorlage Zeile fuer Zeile.

*Gewaehlt: Q_AUFFAELLIG = 0,37* (19 von 51 genuegen, 18 von 51 nicht): 19,3 %
liegen am naechsten an den 20 % der Definition (18/51 ergaeben 21,4 %, 20/51
17,5 %). **Die Haelfte als Anteil taugt nicht** (9,5 %, bei Vorlauf >= 5 Tage
0,8 %), ein Viertel ist zu viel (41 %).

*Vorbehalte.* (1) Duenne Basis: 44 Zielabende zwischen September und Oktober,
nur Spaetsommer/Herbst; Vorhersagen desselben Abends aus verschiedenen Laeufen
sind keine unabhaengigen Stichproben (nimmt man je Zielabend nur die letzte
Vorhersage, sind es bei 19/51 sogar 29,5 % = 13 von 44; korrigiert vom Gate, die erste
Zaehlung sortierte "_abends" vor "_morgens" desselben Tages). Die Grenze ist eine
Setzung und gehoert nach Winter und Fruehjahr neu gemessen. (2) Die Rate
haengt stark am Vorlauf: gesamt 19 %, aber 27,5 % bei Vorlauf 0-1 und nur
10 % ab Vorlauf 5. Weit voraus streuen die Member ueber die Klimatologie, ein
hoher Memberanteil ist dort selten - "auffaellig" erscheint deshalb weit
voraus selten, nah dran haeufiger. Eine vorlaufabhaengige Grenze waere
moeglich, ist aber bei dieser Datenmenge nicht gedeckt. (3) Die Klimatologie
liegt auf dem 0,5-Grad-Gitter, der Betrieb rechnet auf 0,25 Grad (Befund
methodik#F12); der Effekt auf den Rang ist ungemessen.

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

### Nachtrag 09.10.2026: Messung (Option A, `skripte/sichtfaktor_messung.py`)

**Kippbedingung nicht eingetreten.** Die Rohdaten in `daten/roh/` (IFS-Analysen,
22 Blockdateien, 2015-2025) enthalten alle 118 Zellen, die der Faecher in
4018 Abenden braucht, darunter die 6 Sichtzellen; 0 Luecken (geprueft je Zelle,
Tag und Schicht). Es wurde nichts bei Open-Meteo abgerufen, das Kontingent ist
unberuehrt. `sonnen/score.py` ist unveraendert.

**Rechenweg.** Das Skript laedt `score.py` als Kopie im Speicher und ersetzt
genau die zwei Stellen des Sichtfaktors (je Zelle ein Gewicht, Nenner = Summe
der Gewichte). Drei Varianten:

- `gleich` (heute): 6 Sichtzellen je 1/6.
- `raumwinkel`: Gewichte von Term A (`_schirmgewichte`, je Schirmhoehe), auf die
  Sichtzellen renormiert; der Standort bekommt rund 78 % (hoher Schirm).
- `raumwinkel_abs`: dieselben Gewichte ohne Renormierung, Zellen jenseits
  60 km zaehlen als frei. So kam die 0,229 der Vorlage zustande; "gleiche
  Gewichte wie Term A" laesst beide Lesarten zu, deshalb beide gerechnet.

**Gegenproben (jede bricht den Lauf ab, wenn sie reisst):**
(1) `gleich` reproduziert die gespeicherte `score_berlin_g0.5_2015_2025.json`
Abend fuer Abend (4018 Abende, groesste Abweichung 2e-16, gleiche Schirmwahl);
(2) Konstruktionsfall der Vorlage (hoher Schirm 0,9, tiefe Decke nur am
Standort): `gleich` 0,750, `raumwinkel_abs` 0,229 (Vorlage: 0,75 / 0,229),
`raumwinkel` renormiert 0,198; (3) die Albumprobe in der Variante `gleich`
reproduziert die Ausgabe von `skripte/albumtest.py` (43 Abende, Mittelrang
0,674, z = +3,95, 4 von 43 bei p95).

**Score-Verteilung** (alle 4018 Abende; s\* = 95. Perzentil 2022-2025, so
entstand 0,7065):

| | Mittel | p50 | p90 | p95 = s\* (2022-25) | p95 (2015-25) | S >= 0,5 (2022-25) |
|---|---|---|---|---|---|---|
| gleich (heute) | 0,147 | 0,037 | 0,498 | **0,7065** | 0,630 | 9,9 % |
| raumwinkel | 0,142 | 0,034 | 0,466 | **0,6928** | 0,626 | 9,4 % |
| raumwinkel_abs | 0,143 | 0,035 | 0,469 | 0,6930 | 0,628 | 9,4 % |

s\* wandert um -0,014. Der Sichtfaktor selbst aendert sich im Mittel um
+0,002; an 215 von 4018 Abenden (5,4 %) weicht S um mehr als 0,05 ab, an 37
um mehr als 0,2 (groesste Abweichung 0,735).

**Abende ueber s\* je Jahr** (2015 bis 2025):

| Variante / Schwelle | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | Mittel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gleich @ 0,7065 | 8 | 6 | 7 | 8 | 12 | 12 | 10 | 20 | 21 | 16 | 17 | 12,5 |
| raumwinkel @ 0,6928 | 7 | 5 | 9 | 8 | 12 | 12 | 12 | 18 | 22 | 17 | 17 | 12,6 |
| raumwinkel @ 0,7065 (s\* nicht neu) | 6 | 5 | 9 | 8 | 12 | 11 | 10 | 18 | 19 | 17 | 17 | 12,0 |

Alarmmengen gegeneinander (s\* je Variante): 125 Abende in beiden, 12 nur bei
`gleich`, 14 nur bei `raumwinkel`.

**Wie oft kommt der Fall vor?** Definition (Schwellen gesetzt, nicht gefittet;
"Standort" ist die 0,5-Grad-Zelle, rechnerisch rund 55 x 34 km):
tiefe Decke in der Standortzelle `low(d=0) >= 0,9`; Umgebung frei = mittlere
Blockade (`1-(1-low)(1-mid)`) der 5 Zellen bei 60 km `<= 0,2`; Schirm hoch =
Term A des hohen Schirms `>= 0,7`. "Weit": 0,8 / 0,3 / 0,5. Dazu der Fall mit
dem mittleren Schirm (blockiert nur die tiefe Schicht): `low(d=0) >= 0,9`,
Umgebung `low <= 0,2`, Term A des mittleren Schirms `>= 0,7`.

| Fall | Abende in 11 Jahren | davon ueber s\* (gleich) | ueber s\* (raumwinkel) | mittleres S gleich / raumwinkel |
|---|---|---|---|---|
| hoher Schirm, streng | 2 (0,05 %) | 0 | 0 | 0,062 / 0,016 |
| hoher Schirm, weit | 6 (0,15 %) | 0 | 0 | 0,253 / 0,080 |
| mittlerer Schirm, streng | 25 (0,6 %) | **2** (2022-07-01, 2023-10-10) | 0 | 0,249 / 0,036 |
| mittlerer Schirm, weit | 45 (1,1 %) | 2 | 0 | 0,222 / 0,040 |

Der Fall aus der Vorlage (hoher Schirm) ist **real, aber sehr selten**: 2 Abende
in 11 Jahren, keiner davon ueber s\*. Die zwei tatsaechlichen Fehlalarme sind
die Spielart mit dem mittleren Schirm (Standort 100 % tief, Umgebung frei,
S = 0,77 und 0,83 bei `gleich`, 0,09 und 0,10 bei `raumwinkel`). Das sind 2 von
137 Alarmen in 11 Jahren (rund 1,5 %), also etwa ein Fehlalarm alle fuenf
Jahre. Unter den 12 Abenden, die nur bei `gleich` ueber s\* liegen, haben
ausserdem 4 Teildeckung am Standort (low 0,28 bis 0,74); die uebrigen 6 liegen
knapp ueber s\* (S 0,71 bis 0,76) und fallen um 0,03 bis 0,09 darunter.
Umgekehrt entstehen 14 neue Alarme, alle mit freiem Standort (low <= 0,04),
meist mit Bewoelkung in der Umgebung (Sichtfaktor steigt meist von 0,86-0,99 auf
0,96-1,0, Ausreisser 2025-11-12: 0,62 auf 0,85; S vorher 0,53 bis 0,705). Ob diese 14 bessere Abende sind, laesst die Messung
offen.

**Albumprobe** (Album "Sonnenuntergaenge", ohne die zirkulaeren Abende,
saisonaler Perzentilrang wie `albumtest.py`):

| Referenz | Variante | n | Mittelrang | z | Treffer bei p95 |
|---|---|---|---|---|---|
| 2022-2025 | gleich | 43 | 0,674 | +3,95 | 4 |
| | raumwinkel | 43 | 0,667 | +3,79 | 4 |
| | raumwinkel_abs | 43 | 0,666 | +3,77 | 4 |
| 2015-2025 | gleich | 70 | 0,694 | +5,61 | 10 |
| | raumwinkel | 70 | 0,691 | +5,54 | 10 |
| | raumwinkel_abs | 70 | 0,691 | +5,54 | 9 |

Gepaarte Rangdifferenz `raumwinkel` minus `gleich`: -0,007 (95-%-Bootstrap
-0,037 bis +0,013; 24 Abende besser, 12 schlechter, 7 gleich) bei n = 43 und
-0,0025 (-0,022 bis +0,011) bei n = 70. Das Intervall schliesst 0 ein; ein
Gewinn durch die Raumwinkel-Gewichtung ist nicht erkennbar, der Punktwert liegt
leicht darunter.

**Lesart fuer die Entscheidung** (die Entscheidung bleibt bei dir): Die Messung
spricht nicht fuer Option B. Der Gewinn waere etwa ein vermiedener Fehlalarm
alle fuenf Jahre, die Albumprobe wird nicht besser, und s\* verschiebt sich um
-0,014 (alle Kalibrierzahlen vom 09.10. liefen dann auf einer neuen Basis).
Das stuetzt eher C: gleich gewichtet lassen und im Code mit "2 Faelle in 11
Jahren, beide mit mittlerem Schirm" begruenden.

**Grenzen:** (1) Datenbasis sind IFS-Analysen auf 0,5 Grad; im Betrieb rechnen
68 Member, ein Fall kann dort in einzelnen Membern haeufiger auftreten, ohne
dass der Median ihn zeigt (nicht gemessen, das Archiv speichert keine
Zellwerte). (2) Die Fall-Schwellen sind gesetzt; die weite Fassung steht zur
Gegenprobe daneben. (3) Albumprobe: n = 43 bzw. 70, nur positive Abende.
(4) Der Betrieb ist nicht abgeglichen: ob `raumwinkel` bei Membern anders
wirkt als bei Analysen, folgt aus dieser Messung nicht.

**Negativproben des Skripts** (auf einer Kopie des Baums): geaenderter
Ersetzungsanker in `score.py` bricht ab; geaenderte Produktivrechnung
(`K_SEGMENT = 2`) reisst die Archiv-Gegenprobe (162 andere Schirmwahlen, 0,249
Abweichung); `raumwinkel_abs` ohne Nenner-Sonderfall und `gleich` mit
doppeltem Standortgewicht reissen die Konstruktionsfall-Gegenprobe; eine
entfernte Zelle, ein `null`-Wert und ein fehlendes Jahr stoppen die
Abdeckungspruefung; ein ungewichtetes Term A reisst die A-Gegenprobe.

Aufruf: `.venv/bin/python3 skripte/sichtfaktor_messung.py` (2 s, kein Netz).

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
