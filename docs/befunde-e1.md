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
