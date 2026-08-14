# E1 — gemessene Befunde

Alles hier ist gemessen, nicht angenommen. Stand 14.08.2026.
Pruefbefehle stehen jeweils dabei; jede Behauptung ist nachrechenbar.

## 1 Datenlage bei Open-Meteo

### 1.1 Nur zwei Ensembles tragen ueberhaupt Daten

| Modell | Member | Druckflaechen | low/mid/high |
|---|---|---|---|
| `ecmwf_ifs025` | 51 | ja | ja |
| `google_weathernext2_ensemble` | 64 | ja | ja |
| `gfs025`, `icon_eu`, `icon_global`, `gem_global`, … | 31/40/40/21 | **alle Werte null** | **null** |

`temperature_2m` funktioniert bei allen elf Ensemblemodellen — die Modelle sind
live, Open-Meteo ingestiert fuer die uebrigen aber nur eine Oberflaechenteilmenge.

**Folge: die Multi-Modell-Idee (ENS + GEFS + ICON = 122 Member) ist tot.**
Es bleiben ECMWF + WeatherNext = 115 Member aus zwei wirklich unabhaengigen
Ansaetzen (physikalisches IFS vs. diffusionsbasiertes ML).

*Fallstrick:* Ein Schluesseltest allein taeuscht — die Schluessel EXISTIEREN bei
allen Modellen, sie enthalten nur `null`. Immer Nicht-Null zaehlen.

### 1.2 Natives Zeitraster

| Modell | nativ | ueber die vollen 360 h |
|---|---|---|
| `ecmwf_ifs025` | **3 h** | ja (119 Schritte à 3 h) |
| `google_weathernext2_ensemble` | 6 h | ja (59 Schritte à 6 h) |

Die Default-Stundenwerte sind Open-Meteos eigene Interpolation.
`&temporal_resolution=native` liefert die echten Schritte.

ECMWF ist ueber die **volle** Vorlaufzeit 3-stuendig, nicht nur bis +144 h.
Damit sinkt max |Δt| zum Sonnenuntergang von 3 h auf 1,5 h, das Mittel von
1,5 h auf 0,75 h; Restadvektion bei 30 m/s auf 300 hPa: 162 statt 324 km.
Im Dezember trifft es fast exakt — Sonnenuntergang 14:54 UTC liegt 6 min vor
dem 15z-Schritt, also 11 km.

### 1.3 Archivtiefen

| Zweck | Quelle | Tiefe |
|---|---|---|
| Klimatologie, s\*, Saisonzyklus | `archive-api` ERA5, 3 Schichten | 1940+ (genutzt: 2022-2025) |
| Druckflaechen historisch (fuer T-0006) | `historical-forecast-api`, `gfs_global` | **≥ 2022** |
| Gegenprobe Wolkenfeld | `archive-api` ERA5, nur `cloud_cover_low/mid/high` | 1940+ |
| Dispersion, Skill ueber Vorlauf | `ensemble-api`, `past_days` | **nur 93 Tage** |

- **ERA5 auf Open-Meteo hat keine Druckflaechen** — alle null. (E0-Konfidenz
  war 80 %, das war zu hoch.)
- Ensemble-Archiv: `start_date` erlaubt ab 2026-05-13, also 93 Tage.
- Im `historical-forecast-api` tragen nur `gfs_global`/`gfs_seamless` und
  `jma_gsm` Druckflaechen bis 2022 zurueck; `icon_*`, `gem`, `arpege` erst ab
  ca. 2025, `ecmwf_ifs04`/`aifs` gar nicht.
- `best_match` hat zwar Druckflaechen ab 2021, ist aber ueber Modellwechsel
  hinweg **nicht homogen** (streuende, abweichende CC-RH-Beziehung) und faellt
  fuer eine Klimatologie aus.

**Folgen:**
1. Die BSS-Kurve ueber Vorlauf ist heute nicht rechenbar (93 Tage × 5 %
   Basisrate = 4,6 Ereignisse je Stufe). Ersatz: Korrelation des
   Ensemble-Median-Scores bei Vorlauf L gegen den Score bei kuerzestem
   Vorlauf, n = 93 je Stufe, KI auf r etwa ±0,15.
2. **Ab sofort taeglich archivieren** — das Fenster wandert, jeder Tag
   Wartezeit ist ein verlorener Kalibrierungstag.
3. s\* aus GFS uebertraegt sich nicht direkt auf ECMWF. Bruecke:
   Quantilabbildung ueber die 93 Tage Ueberlappung.

## 2 Modellentscheidung: `ecmwf_ifs025`

Getroffen wegen **C3 allein** (3-h-Raster). C1/C2 sind unentschieden, C4 faellt
fuer beide aus (siehe 3.1). Der in E0 genannte Hauptgrund — ECMWF habe eine
native kondensatbasierte Bewoelkung — **war falsch**.

WeatherNext 2 bleibt als Zweitmeinung: 64 Member, physikalisch unabhaengiger
Ansatz, adressiert die Unterdispersionsfrage besser als zwei Varianten
derselben Physik.

## 3 Wolkendiagnostik

### 3.1 `cloud_cover_XXXhPa` ist keine Modellgroesse

Bei **beiden** Modellen exakt eine Funktion der RH desselben Niveaus — Spanne
0,0 innerhalb jedes 1-%-RH-Bins, ueber 47 bzw. 100 Bins, quer ueber alle Member:

    C = 1 - sqrt((1 - RH_wasser) / 0.30)

Sundqvist, RH_crit = 0,70, ueber Wasser, niveauunabhaengig. Sieben Stuetzstellen
auf ±0,4 Prozentpunkte getroffen.

`cloud_cover_high` bei `gfs_global` ist dagegen **nativ** (Streuung bis 95
Prozentpunkte innerhalb eines RH-Profil-Bins) — kondensatbasiert und damit als
Kalibrierziel brauchbar.

### 3.2 Die Ausgangsannahme wurde widerlegt

**Angenommen (E0/E1):** Die Wasser-Diagnostik sei an den Schirmniveaus schief,
weil Eissaettigung viel frueher erreicht wird (−44 °C: 65 %, −57 °C: 58 %
Wasser-RH); also auf RH ueber Eis mit Schwelle nahe 100 % umstellen.

**Gemessen** (GFS Berlin, 26 304 h 2023–2025, Training 2023–24, Test 2025):

| Familie | Test-RMSE | Test-r |
|---|---|---|
| Eis, feste Schwelle 0,85/1,30 — *die Annahme* | **0,4227** | 0,655 |
| Open-Meteo im Ist 0,70/1,00 | 0,2763 | 0,801 |
| Wasser nachgefittet 0,675/1,025, w=1,0 | 0,2666 | 0,807 |
| **Eis nukleationsfoermig — gewaehlt** | **0,2626** | **0,813** |

**Warum:** Cirrus-Entstehung haengt an der **Nukleations**schwelle, nicht an der
Saettigung — eisuebersaettigte, wolkenfreie Gebiete sind haeufig. Eine feste
Schwelle bei Eissaettigung erzeugt Wolke, wo Eis sublimiert.

Open-Meteos feste 70-%-Wasserschwelle entspricht in Eis-Einheiten:

| T | RH_eis |
|---|---|
| −32 °C | 96,0 % |
| −44 °C | 107,5 % |
| −57 °C | 120,3 % |
| −62 °C | 125,0 % |

Sie folgt damit **unbeabsichtigt dem heterogenen Nukleationsband (105–130 %)** —
deshalb ist sie so schwer zu schlagen. Die Gittersuche hat dieselbe Kurve
unabhaengig wiedergefunden: RH_crit_eis von 95 % bei −40 °C auf 125 % bei −60 °C.

**Gewinn gegenueber dem Ist-Zustand: 5 % RMSE.** Der Rest ist die prinzipielle
Grenze einer RH-Diagnostik ohne Kondensat — r ≈ 0,81 ist die Decke.

### 3.3 Gegenprobe: nicht zirkulaer

Gefittet wurde gegen GFS. Gegen **ERA5** (fremdes Modell, natives Feld,
dieselben 26 304 Stunden, Eingangsfeuchte aus GFS):

| | gegen ERA5 |
|---|---|
| diese Diagnostik | **r 0,768** |
| Open-Meteo im Ist | r 0,754 |
| GFS' **eigenes** Wolkenschema | r 0,730 |

Die Diagnostik uebertraegt sich auf ein fremdes Modell **besser als das Schema,
gegen das sie gefittet wurde**. Sie beschreibt also Wolken, nicht GFS.

### 3.4 Ueberlappung

Mitgefittet: C = (1−w)·max + w·(1−∏(1−C_i)). Beste Werte **w = 0,75–1,0**, also
nahezu **Zufallsueberlapp**, nicht Maximalueberlapp.

Das stuetzt die Produktform des Fensterterms (Exponent k ≈ 1, nicht k > 1).
**Vorsicht:** gefittet wurde die Ueberlappung von NIVEAUS an einem Ort, der
Fensterterm ueberlappt SEGMENTE laengs eines Strahls. Anhaltspunkt, kein Beweis.

## 4 Geometrie verifiziert

Sonnenuntergangszeiten gegen Open-Meteos unabhaengige Berechnung:

| Datum | eigen | Open-Meteo |
|---|---|---|
| 2026-06-21 | 19:33 UTC, Az 312,3° | 19:33 |
| 2026-08-17 | 18:28 UTC, Az 293,4° | 18:28 |
| 2026-12-21 | 14:54 UTC, Az 230,6° | (ausserhalb Horizont) |

Bestaetigt die E0-Korrektur: Juni-Sonnenuntergang ist 19:33 UTC, nicht 17:30 —
das Schrittpaar ist im Sommer 18z/00z (bzw. 18z/21z bei ECMWF), und der
00z-Schritt gehoert zum **Folgetag**.

Tangentendistanzen (R_eff = 4/3 R): 600 hPa 267 km · 500 308 · 400 349 ·
300 395 · 250 420 · 200 447 km. Deckt sich mit der E0-Handrechnung.

## 5 Offen

- **Fotogate blockiert:** macOS verweigert den Zugriff auf die Fotomediathek
  (TCC). Braucht Festplattenvollzugriff fuer die Terminal-App.
  Ohne dieses Gate gibt es keinen Abbruchtest.
- T-0005 Interpolationsexperiment: Skript steht, noch nicht gelaufen.
- T-0006 Ablation 3-Schicht gegen niveauaufgeloest: entscheidet, ob s* aus
  Abschnitt 6 auf den Betriebsscore uebertragbar ist.
- T-0003 taegliche Ensemble-Archivierung: Skript steht, Cron noch nicht
  eingerichtet.

*Korrektur gegenueber einer frueheren Fassung dieses Dokuments:* hier stand,
die Klimatologie laufe auf `gfs_global`.  Sie laeuft auf ERA5 als
3-Schicht-Variante — `gfs_global` haette Druckflaechen, aber das Kontingent
traegt keine vier Jahre mit 20 Variablen je Punkt.  `gfs_global` bleibt die
Quelle fuer die Ablation T-0006.

## 6 Klimatologie und Schwellwert (T-0002, gerechnet 14.08.2026)

ERA5, 2022-2025, 1461 Abende, 3-Schicht-Variante, 0.5-Grad-Gitter (118 Zellen),
ausgewertet zur naechstliegenden vollen Stunde am Sonnenuntergang.

### 6.1 Die Zahl

    s* = 0.6325   (95. Perzentil)   ->   18.5 Ausloesungen/Jahr

74 Ereignisse in 4 Jahren; Poisson-Standardfehler sqrt(74)/74 = 12 %, also
18.5 +/- 2.2 pro Jahr.  Zielband des Auftrags war 10-25 - das haelt auch am
Rand des Konfidenzintervalls.

| Perzentil | s | Abende/Jahr |
|---|---|---|
| 90 | 0.4444 | 36.8 |
| 93.2 | 0.5376 | 25.0 |
| **95** | **0.6325** | **18.5** |
| 97.3 | 0.7560 | 10.0 |
| 99 | 0.9046 | 3.8 |

21.1 % aller Abende ergeben exakt S = 0 (geschlossene tiefe Decke oder voellig
klarer Himmel - beides korrekt eine Null).

### 6.2 Saisonalitaet: eine echte Ueberraschung

| Monat | Jan | Feb | Mrz | Apr | Mai | Jun | Jul | Aug | Sep | Okt | Nov | Dez |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Ausloesungen | **0** | 5 | 5 | 6 | 8 | **10** | 8 | 3 | 9 | 9 | 6 | 5 |

**Januar: null Ausloesungen in 124 Abenden.**  Unter Gleichverteilung waeren
6.2 zu erwarten, P(0) = e^-6.2 = 0.002.  Das ist kein Rauschen, sondern ein
Befund: die winterliche Hochdruck-Stratusdecke ueber Norddeutschland schliesst
sowohl den Schirm als auch das Fenster.

Sonst ist die Verteilung **viel flacher als in E0 vorhergesagt**.  Erwartet
war ein Doppelmaximum April/Mai und September/Oktober; beobachtet ist
September/Oktober (je 9) bestaetigt, April/Mai nicht besonders, und das
Maximum liegt im **Juni** (10).  Fuer die Entscheidung D1 (absoluter
Schwellwert) ist das die gute Nachricht: die Demo-Saison im Sommer wird
nicht ausgehungert, im Gegenteil.

### 6.3 Traegt der Fensterterm? Ja.

    r(A, B) = -0.259     (E0-Erwartung: -0.3 bis -0.5)

Negativ und stabil (ueber 1 Jahr: -0.246, ueber 4 Jahre: -0.259), aber
schwaecher als vorhergesagt.  Die Antikorrelation ist der Grund, warum das
Produkt trennscharf ist: vor der Warmfront Cirrus ohne Fenster, hinter der
Kaltfront Fenster mit Restbewoelkung.  Der Score ist damit KEIN Term zu viel.

Beide Schirmniveaus loesen aus (high 42, mid 32) - das Maximum ueber
Schirmniveaus leistet also Arbeit und faellt nicht auf eines zurueck.

### 6.4 Kontingent: drei Limits, nicht eines

Open-Meteo drosselt minuetlich (600), stuendlich (5000) und taeglich (10000)
und nennt im Fehlertext das jeweils greifende.  **Nur das minuetliche lohnt
Warten.**  Zwei Versuche, die Gewichtungsformel zu schaetzen (400 bzw. 2500
Calls je Request), waren beide falsch - deshalb ertastet das Skript das
Kontingent jetzt, statt es zu modellieren: nehmen was geht, Block cachen,
sauber aussteigen, naechster Lauf setzt am Cache an.

### 6.5 Was diese Zahl noch nicht ist

- **0.5-Grad-Gitter statt 0.25.**  Vom Kontingent erzwungen (0.25 Grad ueber
  4 Jahre = 73 572 gewichtete Calls, also 7 Tagesbudgets).  ERA5 hat effektiv
  ~31 km Aufloesung, 0.5 Grad sind 34 x 56 km - vertretbar, aber nicht
  identisch mit dem Betriebsscore.
- **3-Schicht-Variante.**  Keine Dickenstrafe in Term A moeglich; eine dicke
  Mittelschichtdecke wird als eigener Schirm ohne Abzug gewertet.  Die
  Ablation T-0006 muss zeigen, ob sich s* auf die niveauaufgeloeste Variante
  uebertraegt.
- **Keine Schoenheitsvalidierung.**  Das Fotogate ist blockiert (TCC).  s*
  sagt bis dahin nur: "so selten wie gewuenscht", nicht "trifft das Richtige".

## 7 Zeitinterpolation (T-0005, gemessen 14.08.2026)

ECMWF ENS, nativ 3-stuendig, auf 6 h ausgeduennt, Mittelpunkte rekonstruiert
und gegen die echten 3-h-Werte geprueft.  Wahrheit ist das Modell selbst.
Berlin, 64 native Schritte, 3 Member, n = 93 Faelle je Niveau.

| Niveau | Verschiebung 3 h (Median / p90) | Euler | Semi-Lagrange | Gewinn RMSE |
|---|---|---|---|---|
| 850 hPa | 102 / 153 km (6 Zellen) | RMSE 6.32, r 0.961 | RMSE 5.32, r 0.973 | 16 % |
| **300 hPa** | **338 / 504 km (20 Zellen)** | RMSE 19.76, **r 0.667** | RMSE 11.50, **r 0.904** | **42 %** |

**Semi-Lagrange ist auf Schirmniveau Pflicht, auf Fensterniveau Kuer.**  Das
folgt direkt der Physik: Hoehenwind ist rund dreimal staerker, die Verschiebung
entsprechend groesser, und ab ~20 Gitterzellen sind die zwei umschliessenden
Felder praktisch unabhaengige Stichproben - lineares Mitteln daempft dann genau
die Extreme weg, auf die der Alarm zielt (Euler r 0.667 heisst: 44 % der
Varianz erklaert).

E0 hatte r 0.4-0.6 (Euler) und 0.8-0.9 (Semi-Lagrange) geschaetzt; gemessen
sind 0.667 und 0.904.

Einschraenkungen: Die 6-h-Luecke ist der WeatherNext-Fall und damit
konservativ - ECMWF hat im Betrieb 3 h, dort faellt der Gewinn kleiner aus.
n = 93 sind 3 Member x 31 Schritte, also nicht unabhaengig; der Effekt ist
aber weit groesser als jedes plausible Rauschen.

Nebenbefund: Der Versuch nutzt das **Zwei-Pass-Verfahren** aus E0 (erst Mitte
holen fuer den Wind, dann nur die stromauf/-abwaerts liegenden Punkte).  Ein
Gitter, das 60-m/s-Jetwind abdeckt, braeuchte bei 0.25 Grad 47x47 = 2209
Punkte; Zwei-Pass kam mit 370 aus.  Die Betriebsmechanik ist damit
mitvalidiert.

## 8 Traegt der Fensterterm? (offline, 14.08.2026)

Unabhaengig von der Schoenheitsfrage: aendert B ueberhaupt die Rangfolge?

| | |
|---|---|
| rho(S, A) | +0.399 |
| rho(S, B) | **+0.594** |
| rho(A, B) | −0.246 |
| Top-5-%-Ueberlappung S gegen A | **7 von 73 = 10 %** |
| Abende mit A ≥ s\*, von B unter s\* gedrueckt | **419 von 494 = 85 %** |
| B bei hohem A | Median 0.15, p10 0.00, p90 0.83 |

**Der Fensterterm ist nicht dekorativ.** S und A waehlen nahezu disjunkte
Mengen; 66 der 73 besten Abende nach S kaemen nach A gar nicht vor.  B legt
bei 85 % der Abende mit gutem Schirm ein Veto ein.

**Korrektur der Lesart von Abschnitt 7b:** Aus "S schlaegt A im Fototest nicht"
(+0.066 gegen +0.063) hatte ich geschlossen, die Zweiterm-Konstruktion
verdiene sich nichts.  Das war falsch.  S und A sind in ihrer Auswahl fast
orthogonal - dass beide dieselbe schwache Anreicherung auf dem Fotolabel
zeigen, ist eine Aussage ueber das LABEL, nicht ueber die Terme.

**Ueberraschung:** rho(S,B) > rho(S,A).  Der Score wird staerker vom Fenster
getrieben als vom Schirm.  Bei einem Rueckbau auf einen Term waere B zu
behalten, nicht A - das Gegenteil der Intuition.

## 9 Validierung gegen kuratierte Sonnenuntergaenge (14.08.2026)

Andre hat per semantischer Suche ("sonnenuntergang berlin") in der iOS-Fotos-App
eine Liste echter Sonnenuntergangsaufnahmen geliefert.  Das ist ein
Absichtslabel, das jede Heuristik schlaegt.

**Vier der genannten Abende stammten aus der Durchsicht hoher Balken in der
Rueckschau - also vom Score selbst ausgewaehlt und damit zirkulaer.  Sie sind
ausgeschlossen.**  Es bleiben 11 unabhaengige Abende.

### 9.1 Der Score traegt

| | Mittelrang | z | p |
|---|---|---|---|
| S = Schirm x Fenster | **0.677** | +2.04 | **0.042** |
| A nur Schirm | 0.670 | +1.95 | 0.051 |
| B nur Fenster | 0.451 | −0.56 | 0.574 |

Zum Vergleich dasselbe Mass auf 272 UNkuratierten Fotoabenden: 0.510 (z +0.57).
Der Unterschied ist der Wert eines guten Labels.

**S schlaegt jede einfache Alternative** aus denselben Daten:

| Merkmal | Mittelrang | z |
|---|---|---|
| **S** | **0.677** | **+2.04** |
| hohe Wolken nah | 0.582 | +0.94 |
| hoch + mittel | 0.582 | +0.94 |
| Buckel "50 % optimal" | 0.549 | +0.56 |
| tiefe Wolken negiert | 0.543 | +0.49 |
| freier Westen allein | 0.532 | +0.37 |
| mittelhohe Wolken | 0.473 | −0.31 |

Damit ist das E0-Abbruchkriterium bestanden.

### 9.2 Aber er ist nicht scharf genug fuer das bestellte Produkt

| Alarmrate | faengt von 11 erinnerten Abenden |
|---|---|
| **18/Jahr (s\* wie kalibriert)** | **0** |
| 37/Jahr | 1 (9 %) |
| 73/Jahr | 5 (45 %) |
| 110/Jahr | 7 (64 %) |

Der Score hebt gute Abende von Rang 0.50 auf 0.68.  Ein 5-%-Alarm braucht sie
bei 0.95.  Obere 95-%-Grenze der wahren Trefferquote bei 0 von 11: **24 %**.

**Andres 29.03.2025** ("spektakulaer"): absolut S = 0.212, saisonal aber
Rang 0.81.  Der Score hat den Abend erkannt; versenkt hat ihn Entscheidung D1
(absoluter Schwellwert) - im Maerz sind alle Scores niedrig.

### 9.3 Zwei Erklaerungen geprueft und verworfen

**Parameter.** Sweep ueber die Fensterhaerte K_SEGMENT (0.4 bis 2.0): der
Mittelrang bewegt sich zwischen 0.660 und 0.705, die Trefferquote bleibt bei
0-1 von 11.  Um das Produkt zu retten braeuchte es +0.25, nicht +0.03.
Gegenprobe: bei K = 1.0 reproduziert die Neurechnung die gespeicherte
Klimatologie auf 1e-6 genau.

**Loecher.** Hypothese: bei 0.5 Grad und 3 Schichten sieht der Score keine
Risse in einer sonst geschlossenen Decke.  Gemessen an der Spannweite der
tiefen Bewoelkung quer ueber den Faecher im Band 240-420 km: kuratierte
Abende 0.390, alle Abende 0.392, z = −0.02.  **Nicht bestaetigt.**

### 9.4 Was daraus folgt

Der Score ist das Beste, was aus diesen Daten zu holen ist, und er ist
messbar besser als jede Alternative - aber die Luecke zwischen "selten genug"
und "trifft die guten Abende" bleibt.  Drei Wege, keiner offensichtlich:
niveauaufgeloeste Variante mit Dickenstrafe (nie gegen Schoenheit getestet),
Ruecknahme von D1, oder ein anderes Produkt (taegliche Zahl statt seltener
Alarm).

**Alles hier steht auf n = 11.**  Ein Album mit der vollstaendigen Suchliste
wuerde es auf n = 50-80 bringen und die Produktentscheidung tragfaehig machen.

## 10 Raumwinkelgewichtung des Schirmterms (14.08.2026)

**Ausgeloest durch einen Gegenfall von Andre:** der 29.03.2025 war
"spektakulaer", der Score gab 0.212.  Was ERA5 sah:

| d [km] | hoch | mittel | tief |
|---|---|---|---|
| **0** | 0 % | **90 %** | 20 % |
| 60 | 14 % | 0 % | 0 % |
| 120 | 43 % | 0 % | 3 % |
| 180–420 | ~0 % | 0 % | ~0 % |

Eine mittelhohe Decke direkt ueber Berlin, freier Westen bis 400 km - das
Lehrbuchbild.  **Term A mittelte sie weg:** ein 90-%-Wert bei d=0 und zehn
Nullen bei d=60/120 ergeben 8 %, weil jeder Fanpunkt gleich zaehlte und d=0
nur 1/11 des Gewichts hatte.

### 10.1 Die Korrektur folgt aus Geometrie, nicht aus Fitting

Eine Wolkenschicht in Hoehe h traegt zum sichtbaren Himmel mit ihrem
Raumwinkel bei.  Die Raumwinkeldichte ist proportional zu
d·h/(d²+h²)^{3/2}, mit Maximum bei d = h/√2 und Abfall wie 1/d².
Integriert ueber die von jeder Stuetzstelle vertretenen Ringe:

| Schirmhoehe | d=0 | d=60 | d=120 |
|---|---|---|---|
| 4.2 km (mid) | **0.886** | 0.095 | 0.019 |
| 9.5 km (high) | **0.745** | 0.210 | 0.045 |

Kein freier Parameter.

### 10.2 Wirkung, gegen die kuratierten Abende gemessen

| Gewichtung | Mittelrang n=11 | z | Treffer bei 18/37/73 Alarmen | 29.03.2025 |
|---|---|---|---|---|
| punkt (bisher) | 0.677 | +2.04 | 0 / 1 / 5 | S 0.212, Rang 0.81 |
| ring | 0.700 | +2.30 | 0 / 1 / 6 | S 0.263, Rang 0.83 |
| **raumwinkel** | **0.737** | **+2.72** | **0 / 3 / 7** | **S 0.699, Rang 0.96** |

**Leave-one-out** ohne den Abend, an dem die Korrektur gefunden wurde (n=10):
punkt 0.664 (z +1.80) → raumwinkel 0.715 (z +2.35), Treffer bei 37/Jahr
1 → 2.  Der Gewinn ist also kein Artefakt des Fundfalls.

*Fallstrick beim Messen:* Der erste Vergleich reproduzierte die gespeicherte
Klimatologie nicht (Abweichung 0.238), weil "uniform" versehentlich als
"jeder RING gleich" implementiert war statt "jeder PUNKT gleich" - das ist
selbst schon ein halber Fix.  Erst die Dreiteilung punkt/ring/raumwinkel mit
exakter Gegenprobe machte den Vergleich belastbar.

### 10.3 Folgen

- **s\* neu: 0.7065** (95. Perzentil, 18.5 Ausloesungen/Jahr).
  Alter Wert 0.6325 gilt nur fuer GEWICHTUNG="punkt".
- Beide Schirme loesen weiterhin aus (high 35, mid 39) - der mid-Schirm
  gewinnt jetzt sogar oefter, weil ueberkopfstehende Decken nicht mehr
  wegge­mittelt werden.
- Die Luecke zum Produkt bleibt: bei 18 Alarmen/Jahr immer noch 0 von 11.

## 11 Albumtest, n = 43 (14.08.2026)

Andre hat die semantische Suche "sonnenuntergang" in ein Album gelegt.
80 Abende in Berlin, 43 davon in der Klimatologie 2022-2025.  Drei Abende
aus der Score-Balken-Durchsicht sind als zirkulaer ausgeschlossen.

| | Mittelrang | z | p |
|---|---|---|---|
| **S = Schirm x Fenster** | **0.674** | **+3.95** | **0.0001** |
| A nur Schirm | 0.623 | +2.80 | 0.0052 |
| B nur Fenster | 0.515 | +0.33 | 0.74 |

**S schlaegt A deutlich.**  B allein traegt nichts - und das ist die Rolle,
die der Fensterterm haben SOLL: er sagt nicht vorher, er filtert.  Abende mit
gutem Schirm aber verbautem Westen fallen raus, und die stehen nicht im Album.

### 11.1 Trefferquote (Wilson-Intervall, weil n klein bleibt)

| Alarmrate | Schwelle | Treffer |
|---|---|---|
| 18/Jahr | S ≥ 0.707 | 4 von 43 = 9 % [4–22 %] |
| 25/Jahr | 0.640 | 5 = 12 % [5–24 %] |
| 37/Jahr | 0.498 | 10 = 23 % [13–38 %] |
| 55/Jahr | 0.371 | 16 = 37 % [24–52 %] |
| 73/Jahr | 0.273 | 20 = 47 % [33–61 %] |

### 11.2 Der strukturelle Fehler: der Schirm darf entfernt stehen

Die zehn schlechtesten Albumabende waren ueber Berlin nahezu **wolkenfrei**
(hoch 0-26 %, mittel 0-25 %, tief 0-16 %).  Erste Hypothese - eine tiefe,
von unten angestrahlte Decke, die der Score nur als Blocker kennt - ist
widerlegt: 0 von 10 hatten ueber 40 % tiefe Bewoelkung.

**Aber 8 von 10 hatten ueber 50 % Bewoelkung im Band 180-360 km West.**

Physikalisch ist das ein Standardfall: 250 km westlich geht die Sonne rund
15 Minuten spaeter unter (3.7 Grad Laenge).  Zum Berliner Sonnenuntergang
steht sie dort noch ueber dem Horizont und beleuchtet die Wolkenbank, die
man von Berlin aus bei 1-2 Grad Elevation genau in Blickrichtung glaenzen
sieht.

**Der Score zaehlt diese Wolke ausschliesslich als Blocker.**  Term A tastet
nur bis 120 km ab und ist seit der Raumwinkelgewichtung noch staerker auf
d = 0 konzentriert.  Das, was man tatsaechlich ansieht, kommt darin nicht vor.

### 11.3 Vorgeschlagene Verallgemeinerung (noch nicht gebaut)

Statt "Schirm nah, Fenster fern" ein Schirm in Entfernung d_s:

    S = max ueber (Niveau h, Entfernung d_s) von [ A(h, d_s) * B(h, d_s) ]

wobei B nur noch den Weg JENSEITS von d_s bewertet.  Der heutige Score ist
der Spezialfall d_s = 0.

Offene Designfrage dabei: eine ferne Bank nimmt wenig Raumwinkel ein, steht
aber genau in Blickrichtung.  Reine Raumwinkelgewichtung wuerde sie
unterschaetzen - es braucht vermutlich einen Richtungsanteil.  Das ist ein
Entwurf, kein Handgriff, und wird nicht nebenbei gemacht.

## 12 Distanz-Schirm: Vorab-Kriterien verfehlt (14.08.2026)

**Vorher festgelegt:** Mittelrang > 0.70 bei z > 4.0; Treffer bei 18
Alarmen/Jahr >= 8 von 43; S muss A weiter schlagen; keine gefitteten Parameter.

| Variante | Mittelrang | z | Treffer 18/37/73 |
|---|---|---|---|
| alt (Schirm nah) | 0.674 | +3.95 | 4 / 10 / 20 |
| Distanz, nur Raumwinkel | 0.650 | +3.40 | 4 / 6 / 14 |
| Distanz + Phasenfunktion | 0.674 | +3.95 | **7** / 12 / 20 |

**Kriterien nicht erfuellt** (0.674 < 0.70, 7 < 8).  Nicht uebernommen.

### 12.1 Warum die reine Raumwinkelfassung scheitert

Der Ring bei 300 km hat 1/110 des Raumwinkels des Rings ueber dem Kopf.  Die
ferne Bank kann den Score gar nicht bewegen, egal wie hell sie ist.  Das war
als Risiko benannt und hat sich bestaetigt.

### 12.2 Warum die Phasenfunktion physikalisch dazugehoert

Wolkentropfen streuen stark vorwaerts.  Am Wolkenort in Entfernung d steht
die Sonne noch d/R_eff hoch; die Blickrichtung von Berlin trifft die Wolke
unter arctan(h/d).  Beide Winkel sind fast gleich:

| d [km] | Sonnenhoehe | Blickwinkel | Streuwinkel | HG(g=0.85) |
|---|---|---|---|---|
| 0 | 0.00° | 90.00° | 90.00° | 0.0098 |
| 120 | 0.81° | 4.53° | 3.72° | 5.24 |
| 250 | 1.69° | 2.18° | **0.49°** | **6.52** |

Verhaeltnis vorwaerts zu quer: 670 zu 1.  Gegen 1/110 Raumwinkel bleibt netto
Faktor 6 zugunsten der fernen Bank.  g = 0.85 ist Literaturwert fuer
Wasserwolken, nicht an diese Daten angepasst.

### 12.3 Selbstkritik

Die Phasenfunktion kam NACH dem ersten Fehlschlag.  Die Analyse ist damit
adaptiv statt vorab festgelegt; der Befund ist entsprechend schwaecher, auch
wenn die Physik unstrittig ist.

### 12.4 Was den Fall entscheiden wuerde

Die Fanabtastung endet bei 420 km.  Fuer einen Schirm bei 250 km liegt der
Tangentenpunkt bei 652 km - der Beleuchtungsweg ist nur zu 87 % (Median)
abgetastet, der Rest gilt als frei und beguenstigt ferne Schirme.
**Eine Erweiterung der Distanzen auf 600-700 km ist die Voraussetzung dafuer,
diese Variante ueberhaupt fair zu bewerten.**  Kostet Kontingent und eine
neue Klimatologie.

## 13 Nachglut-Geometrie und tiefe Wolken als Schirm (14.08.2026)

Andres Einwand: "Ich muss die Sonne nicht sehen koennen.  Spektakulaer
leuchtende Wolken gehen auch ohne.  Dafuer kann die Sonne sogar schon
untergegangen sein."

### 13.1 Wie lange bleibt was beleuchtet

Eine Wolke in Hoehe h wird beleuchtet, bis die Sonne um ihren Kimmwinkel
sqrt(2h/R) unter dem Horizont steht.  Bei Berlins Breite sinkt die Sonne mit
rund 6.8 Grad/h:

| Hoehe | Kimmwinkel | noch beleuchtet nach SU |
|---|---|---|
| 1.2 km | 1.11° | 10 min |
| 4.2 km | 2.08° | 18 min |
| **9.5 km** | **3.13°** | **28 min** |

Zum Zeitpunkt "Sonne 1.7 Grad unter Horizont" ist ueber Berlin alles unter
3.75 km im Schatten, bei 2.3 Grad alles unter 6.8 km.  Tiefe Bewoelkung ist
dann kein Blocker mehr, sondern **Silhouette**.

### 13.2 Getestet - und die Haelfte der Idee ist nicht testbar

Die geometrische Haelfte (welche Hoehen bekommen noch Licht) laesst sich mit
vorhandenen Daten pruefen, weil nur die Auswahl der Schirmschichten sich
aendert.  Ergebnis: zwischen 1.5 und 2.5 Grad Sonnentiefe bewegt sich der
Mittelrang nicht (0.683 / 0.675 / 0.678), die Trefferquote wackelt zwischen
4 und 6 - im Rauschen.

**Die zeitliche Haelfte ist damit NICHT getestet.**  Das Wolkenfeld im Cache
ist das zur Sonnenuntergangsstunde; wie der Himmel 15 Minuten spaeter
aussieht, steht dort nicht.  Genau darin liegt Andres Beobachtung.  Ein
echter Test braucht Wolkenfelder zur Folgestunde - neue Klimatologie.

### 13.3 Nebenbefund: tiefe Wolken taugen nicht als Schirm

Beim Umbau habe ich testweise "low" als Schirmschicht zugelassen.  Der
Mittelrang faellt von 0.674 auf **0.615**.  Die Designentscheidung
SCHIRME = (high, mid) ist damit erstmals empirisch bestaetigt statt nur
begruendet - passend zum frueheren Befund, dass 0 von 10 Fehlschlaegen eine
tiefe Decke ueber Berlin hatten.

### 13.4 Sprachkorrektur im ganzen Projekt

"Klarer Westhorizont" stand im Alarmtext, in der README und in
Modulkoepfen.  Der Score prueft das nirgends: er verlangt, dass das Licht
200-400 km westlich in 1-2 km Hoehe durchkommt.  Ob man von seinem Fenster
den Horizont sieht, ist irrelevant - man muss die Sonne gar nicht sehen.
Die Formulierung behauptete eine Bedingung, die das Modell nicht stellt, und
ist ueberall ersetzt.

### 13.5 Grenze des Albums als Messlatte

Andre wohnt mit Blick nach NNW (rund 337 Grad).  Der Sonnenuntergangsazimut
laeuft von 229 Grad (Dez) bis 312 Grad (Jun) - im Dezember also 108 Grad
neben dem Fenster.  Die Albumverteilung zeigt das direkt:

    Jan 0 · Feb 0 · Mrz 4 · Apr 10 · Mai 15 · **Jun 25** · Jul 12 · Aug 5
    Sep 7 · Okt 3 · Nov 0 · Dez 0

Oktober bis Februar zusammen 3 von 81.  Das ist keine Wetteraussage, sondern
eine Fensteraussage.  **Der Score darf deshalb nicht auf dieses Label
optimiert werden** - er wuerde ein Detektor fuer sommerliche
NNW-Sonnenuntergaenge.  Das Album taugt zur Richtungspruefung, nicht zum
Feinschliff.

## 14 Drei Hypothesen offline getestet, alle widerlegt (14.08.2026)

Ausgangspunkt: Andres 03.05.2024.  Foto zeigt einen angeleuchteten
Makrelenhimmel mit orangem Horizontband, das Modell HAT die hohen Wolken -
und der Score gibt S = 0.000, Rang 0.14.  Also kein Datenfehler.

| Hypothese | Test | Ergebnis |
|---|---|---|
| Loecher im Feld, bei 0.5 Grad unaufgeloest | Spannweite der tiefen Bewoelkung ueber den Faecher, 240-420 km | kuratierte Abende 0.390 gegen alle 0.392, z −0.02 — **widerlegt** |
| Wegprodukt zu hart | K_SEGMENT von 0.2 bis 1.5 gegen das Album | K = 1.0 ist bereits optimal (0.674); K = 0.2 bringt den 03.05. nur auf Rang 0.25 — **widerlegt** |
| Harte Null durch 100-%-Segmente | Transmissionsboden 0.00 bis 0.20 | Mittelrang bleibt 0.674, der 03.05. bleibt bei Rang 0.13-0.16 — **widerlegt** |

Der dritte Test erklaert sich selbst: ein Boden hebt ALLE blockierten Abende
gleich an, ihre Reihenfolge untereinander bleibt.  Ein Skalierungstrick kann
keine Information erzeugen, die im Feld nicht steckt.

### 14.1 Wo die Information fehlt

Die Bedeckung im Sperrband ist fast binaer verteilt:

    0-9 %: 1641 Faelle    ...    100 %: 1862 Faelle

**32 % aller Faelle melden 100 %.**  Dort ist der Score per Konstruktion null,
unabhaengig davon, ob undurchdringlicher Stratocumulus oder duenner
Altostratus dortsteht.  Open-Meteo liefert die optische Dicke nicht mit.

### 14.2 Warum die niveauaufgeloeste Variante das aufloesen koennte

Gemessen an 26 304 gemeinsamen Stunden Berlin 2023-2025:

| | exakt 100 % | exakt 0 % | dazwischen |
|---|---|---|---|
| ERA5 `cloud_cover_high` | 23.0 % | 38.9 % | 25.2 % |
| eigene RH-Diagnostik | **5.6 %** | 28.7 % | **50.0 %** |

Die eigene Rechnung liefert doppelt so oft einen Zwischenwert.  Das ist ein
mechanischer Grund, kein aesthetischer: wo ERA5 auf 100 % saettigt und den
Score auf null zwingt, gibt die RH-Rechnung noch eine Abstufung her.

**Damit ist die niveauaufgeloeste Klimatologie (gfs_global, Druckflaechen)
der naechste Lauf, nicht das feinere Gitter und nicht der erweiterte Faecher.**

## 15 Fotos angesehen: drei Fehlerklassen (14.08.2026)

Sechs der schlechtesten Albumabende mit dem Foto verglichen.

| Abend | Rang | Foto | Diagnose |
|---|---|---|---|
| 2023-04-24 | 0.17 | schwere Decke, oranger Schlitz am Horizont | **Daten** — ERA5 high 0 %, GFS-Feuchte 300 hPa 96 %, eigene Diagnostik 58 % |
| 2022-09-20 | 0.19 | ganzer Himmel voll angeleuchteter Wolken | **Daten** — ERA5 meldet nirgends im Faecher etwas |
| 2023-06-13 | 0.44 | dichte Decke, oranges Band darunter | **Daten** — ERA5 0/11/0, eigene Diagnostik 14 % |
| 2024-05-03 | 0.14 | Makrelenhimmel, spektakulaer | **Modell** — Wolken vorhanden, Wegterm auf exakt null |
| 2024-09-15 | 0.34 | Himmel brennt tiefrot | **Modell** — Sichtterm toetet es (100 % tief ueber Berlin); auf dem Foto ist genau diese Decke das, was brennt |
| 2025-06-25 | 0.22 | Sonne am Horizont, duenner Cirrus, viel Blau | **Label** — huebsch, nicht aussergewoehnlich |

### 15.1 Die Datenkette wurde vorher geprueft

Drei Fehltreffer hintereinander rochen nach eigenem Bug.  Geprueft und
verworfen:

- **Off-by-one im Datum:** Nachbartage zeigen andere Werte, der Fototag ist
  wirklich der gemeldete.
- **Falsche Zuordnung bei Mehrfachort-Abfragen:** raeumliche Korrelation
  benachbarter Zellen r = +0.863 (0.5 Grad), +0.775 (1.0 Grad), +0.412 (weit),
  zeitlich Lag-1 r = +0.352.  Genau das Muster echter Felder - bei
  vertauschten Antworten laege alles bei 0.
- **Systematischer Bias:** mittlere Gesamtbedeckung ueber Berlin 65 %, exakt
  die DWD-Klimatologie.

**Die Kette ist sauber.  ERA5 sieht diese Wolken wirklich nicht.**

### 15.2 Warum das die Prioritaet bestaetigt

An den Fehlschlaegen selbst gemessen, nicht nur statistisch:

| Abend | GFS-RH 400/300/250/200 | eigene Diagnostik | ERA5 high |
|---|---|---|---|
| 2023-04-24 | 33 / **96** / 27 / 5 | **58 %** | **0 %** |
| 2023-06-13 | 70 / 38 / 20 / 3 | 14 % | 0 % |
| 2025-06-25 | 20 / 28 / **82** / 50 | 24 % | 0 % |
| 2024-05-03 | 92 / **100** / 89 / 38 | 94 % | 72 % |

Die Wolke steckt im Feuchtefeld.  ERA5s Bedeckungsfeld hat sie verworfen.

### 15.3 Der Sichtterm ist falsch konstruiert

Er behandelt tiefe Bewoelkung ausschliesslich als Sichtblockade.  Der
15.09.2024 zeigt, dass eine von unten angestrahlte tiefe Decke DAS EREIGNIS
sein kann - 100 % tief ueber Berlin, Score 0.028, und auf dem Foto brennt
genau diese Decke.

Der frueherer Test "low als Schirm zulassen" hatte global verschlechtert
(0.674 -> 0.615).  Der Effekt ist also real, aber selten; wholesale
hinzuzufuegen bringt mehr Rauschen als Signal.  Was fehlt, ist die
Unterscheidung "tiefe Decke im Licht" gegen "tiefe Decke im Schatten" - und
die haengt daran, ob der Weg auf 1.2 km Hoehe (D = 143 km) frei ist.

### 15.4 Das Album ist keine Liste von Ausnahmen

Mindestens einer von sechs angesehenen Abenden ist ein normal schoener
Sonnenuntergang.  Das Album heisst "Sonnenuntergaenge", nicht "spektakulaere
Sonnenuntergaenge".  Die gemessene Trefferquote von 9 % bei 18 Alarmen/Jahr
ist damit zu pessimistisch: ein Teil der Messlatte gehoert gar nicht in die
obersten 5 %.
