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
    (UEBERHOLT: gilt nur fuer GEWICHTUNG="punkt", siehe 10.3 -> 0.7065)

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

## 16 Kontingent: die Limits sind NICHT endpunktuebergreifend (14.08.2026)

Fruehere Behauptung in Abschnitt 6.4 und in der README: die Limits gaelten
endpunktuebergreifend.  **Falsch.**  Gemessen um 11:17 UTC, nachdem das
Tageslimit gerissen war:

| Endpunkt | Status |
|---|---|
| `archive-api` (ERA5) | gesperrt |
| `historical-forecast-api` | gesperrt |
| `ensemble-api` | **frei** |
| `forecast-api` | **frei** |
| `air-quality-api` (CAMS) | **frei** |

Um 11:34 UTC, nach einem CAMS-Zug ueber vier Jahre, war auch `ensemble-api`
gesperrt - und zwar fuer JEDE Groesse, bis hinunter zu 1 Ort x 1 Variable x
1 Tag.

**Was daraus sicher folgt:** die Endpunkte hatten um 11:17 unterschiedliche
Zustaende, teilen sich also kein einziges Konto.  **Was NICHT folgt:** dass
der Betrieb dadurch geschuetzt waere - das Ensemble-Budget war schlicht
ebenfalls fast leer und ist es dann geworden.

Ich habe an diesem Tag zweimal eine Theorie ueber dieses Kontingent
aufgestellt (erst "Memberzahl multipliziert", dann "endpunktuebergreifend")
und beide Male danebengelegen.  Deshalb steht hier nur noch, was gemessen
wurde, mit Uhrzeit.  Wer die Kapazitaet fuer einen Lauf wissen will, misst
sie vorher - `--trocken` genuegt.

## 17 Aerosol: Entscheidung richtig, Begruendung falsch (14.08.2026)

CAMS ueber `air-quality-api` reicht bis 04.08.2022 zurueck - 1246 Abende
Ueberlappung mit der Klimatologie, davon 33 im Album.

| | AOD Median | p10 | p90 |
|---|---|---|---|
| Albumabende | **0.230** | 0.100 | 0.390 |
| uebrige | 0.140 | 0.050 | 0.330 |

E0 argumentierte: klare Luft gibt gesaettigte Farben, gute Abende muessten
also WENIG Aerosol haben.  Gemessen ist es umgekehrt.  Nach Saisonbereinigung
(+/-21-Tage-Rang) bleibt Mittelrang 0.552, z = +1.04 - **nicht signifikant**.
Der Rohunterschied ist fast vollstaendig Jahreszeit.

E0 nannte drei Gruende gegen den Term: (1) CAMS reicht nur 5 Tage voraus,
(2) deterministisch, zerstoert die Memberstruktur, (3) teilredundant zur
bodennahen Feuchte.  (1) und (2) gelten weiter.  **(3) ist widerlegt:**
r(S, AOD) = +0.158, also nahezu unabhaengig.

Die Entscheidung war richtig, die Begruendung nicht.  Der Term traegt kein
Schoenheitssignal - weder in die eine noch in die andere Richtung.

## 18 Zwei Faehigkeiten, nur eine gemessen (14.08.2026)

Acht Albumfotos angesehen und mit dem Rang verglichen:

| Rang | Eindruck |
|---|---|
| 0.14 | spektakulaer (Makrelenhimmel) |
| 0.17 | dramatisch (Decke mit Horizontschlitz) |
| 0.19 | spektakulaer (voller angeleuchteter Himmel) |
| 0.22 | mild |
| 0.34 | spektakulaer (Himmel brennt tiefrot) |
| 0.44 | dramatisch |
| 0.95 | spektakulaer (Magenta ueber die Kuppel) |
| 0.99 | mild (spaete Daemmerung, schmales Band) |

**Die beiden Aussagen sind verschieden, und nur eine ist belegt:**

1. *Albumabende scoren hoeher als zufaellige Abende.*  Gemessen, n = 43,
   z = +3.95, p = 0.0001.  Steht.
2. *Innerhalb guter Abende bedeutet hoeherer Score besseren Sonnenuntergang.*
   **Nie getestet** - und nach diesen acht Bildern zweifelhaft.

Fuer den Alarm zaehlt (2).  Er feuert auf die obersten 5 %; unterscheidet er
dort nicht mehr, waehlt er unter den guten Abenden zufaellig aus.  Die
Anreicherung aus (1) waere dann trotzdem echt - sie kommt daher, dass der
Score die VOELLIG schlechten Abende zuverlaessig aussortiert, und das ist
eine schwaechere Leistung als sie klingt.

**Was das entscheiden wuerde:** eine Qualitaetsordnung INNERHALB des Albums.
Nicht "war es schoen" (das sagt schon die Albumzugehoerigkeit), sondern "wie
schoen im Vergleich zu den anderen".  Meine eigene Einschaetzung aus acht
Fotos taugt dafuer nicht - sie ist subjektiv und zu klein.

*Vorsicht bei der Interpretation dieser Tabelle: acht Fotos, mein Urteil,
keine Verblindung.  Sie ist ein Warnsignal, kein Befund.*

## 19 Blindbewertung der Albumfotos (14.08.2026)

Andre bat um eine eigene Bewertung.  Durchgefuehrt **blind**: die 41 Bilder
wurden gemischt, nummeriert und als Kontaktboegen bewertet; die Zuordnung
Nummer->Datum wurde erst nach der letzten Note geoeffnet.  Ohne das haette
die Kenntnis des Scores die Noten geankert - dieselbe Disziplin, die die
Bewertungsseite fuer Andre erzwingt.

Notenverteilung: 1x0, 2x13, 3x15, 4x11, 5x2.

### 19.1 Ordnet der Score innerhalb guter Abende?

| Auswahl | n | Spearman rho | z |
|---|---|---|---|
| alle | 41 | **+0.074** | +0.47 |
| ohne die 4 belegten Datenfehler | 37 | **+0.257** | +1.54 |
| ohne die zwei Fuenfen | 39 | +0.235 | +1.45 |

Note 4-5 liegt bei Score-Rang 0.770, Note 1-2 bei 0.643 - Differenz +0.127,
z = +1.60, **nicht signifikant**.

**Beide Fuenfen sind belegte Datenfehler** (22.09.2022 und 15.09.2024): dort
hatte ERA5 die Wolken nicht.  Der Score kann nicht ordnen, was er nicht sieht.
Nach deren Ausschluss steigt rho von 0.07 auf 0.26 - fuer Signifikanz braeuchte
es bei dieser Effektgroesse n ~ 113, vorhanden sind 37.

### 19.2 Was daraus folgt

**Die Frage bleibt offen, aber die Richtung hat sich gedreht.**  Vor der
Blindbewertung sah es aus, als ordne der Score gar nicht.  Nach Korrektur um
die Faelle, in denen die Datenbasis fehlte, deutet sich eine schwache
Ordnung an - zu schwach fuer ein Urteil.

**Nebenbefund mit Gewicht:** 4 von 41 Albumabenden (10 %) sind belegte
Datenfehler.  Wenn ERA5 an jedem zehnten guten Abend die Wolken nicht hat,
deckelt das die erreichbare Trefferquote unabhaengig von jeder
Score-Verbesserung.

### 19.3 Grenzen dieser Bewertung

- Ein Foto je Abend (das alphabetisch erste), nicht das beste.
- Vorschaubilder, kein Original.
- Ein Bewerter, konservative Skala (2 von 41 bekamen die Hoechstnote).
- Blind gegenueber dem Score, aber nicht gegenueber dem Projektziel.

Sie ersetzt Andres eigenes Urteil nicht - sie liefert eine zweite, unabhaengige
Ordnung, und ihre Uebereinstimmung mit seiner waere selbst eine Messung wert.

## 20 Zwei Bewerter, ein Score - und die eigentliche Obergrenze (14.08.2026)

Andre hat 80 Abende selbst benotet (2014-2026), 46 davon liegen in der
Klimatologie, 40 ueberlappen mit meiner Blindbewertung.

### 20.1 Die Betrachter sind sich uneinig

    rho(ich, Andre) = +0.243   n = 40   z = +1.52   NICHT signifikant
    exakt gleiche Note: 14 von 40 (35 %)
    hoechstens 1 daneben: 34 von 40 (85 %)
    Mittel: ich 3.00, Andre 3.55 - ich benote strenger

**Das ist der wichtigste Wert des ganzen Projekts.**  Zwei Betrachter, dieselben
Fotos, kein Zeitdruck - und die Rangfolge stimmt kaum ueberein.

### 20.2 Der Score gegen beide Bewerter

| Gegen | alle | ohne belegte Datenfehler |
|---|---|---|
| Andre | rho +0.106 (n=46) | **rho +0.205** (n=43) |
| ich | rho +0.074 (n=41) | **rho +0.257** (n=37) |

Keiner signifikant.  Aber: **der Score sagt Andres Urteil fast so gut vorher
wie ich es tue** (0.205 gegen 0.243) - und ich hatte die Fotos vor Augen.

### 20.3 Die Obergrenze

Wenn zwei Betrachter mit rho = 0.24 uebereinstimmen, kann ein PERFEKTES Modell
mit einem einzelnen Betrachter hoechstens rho = sqrt(0.24) = **0.49**
erreichen.  Der Score liegt bei 0.205, also bei **42 % des theoretisch
Moeglichen**.

Minderungskorrigiert waere rho gegen ein rauschfreies Ziel etwa 0.42.
*Vorsicht:* rho(ich, Andre) ist selbst nur mit n = 40 geschaetzt und nicht
signifikant (KI etwa −0.07 bis +0.52).  Die Korrektur ist eine
Groessenordnung, keine Zahl.  Und der Vergleich zweier nicht signifikanter
Korrelationen traegt wenig - was traegt, ist das Argument ueber die
Obergrenze, und das gilt unabhaengig von Signifikanz.

### 20.4 Was das fuer das Produkt heisst

"Wird es ein toller Sonnenuntergang?" ist bei der Praezision, die ein Alarm
braucht, **keine wohldefinierte Frage** - zwei Menschen beantworten sie
unterschiedlich, mit dem Foto vor Augen.

Was der Score belegbar kann: aussergewoehnliche Abende von gewoehnlichen
trennen (Anreicherung, n = 43, p = 0.0001).
Was er nicht kann: unter den guten die besseren finden - und ein zweiter
Mensch kann das auch nicht.

**Die ehrliche Produktaussage ist damit nicht "das wird spektakulaer",
sondern "heute ist ungewoehnlich, schau hin".**  Bei dieser Formulierung ist
eine hoehere Alarmrate kein Fehler, sondern angemessen: 37 Alarme im Jahr
fangen 23 % der Albumabende, und mehr Trennschaerfe gibt das Ziel nicht her.

### 20.5 Der Nachtlauf ist wieder wertvoller geworden

Andres Noten in der jetzigen Klimatologie (2022-2025): 46.
Im Bereich des Nachtlaufs (2015-2025): **72** - plus 57 %.

## 21 Die Obergrenzen-Rechnung aus 20.3 ist ungueltig (14.08.2026)

Andre vermutete einen Reihenfolgeneffekt in seiner eigenen Bewertung (er ging
von neu nach alt und koennte strenger geworden sein).  **Nicht bestaetigt:**
rho(Position, Note) = −0.047, z = −0.42.  Viertel-Mittelwerte 3.65 / 3.55 /
3.60 / 3.40.

Die groessten Deltas sind dagegen einseitig: Andre hoeher in 20 Faellen, ich
in 6, gleich in 14.  Die zwei groessten (Delta +3):

- **2025-05-26** - graue Decke mit hellem Spalt, und **Strahlenbuescheln**,
  die durch die Luecke nach unten faechern.  Ich: Note 2.
- **2024-05-25** - breites goldenes Licht, weiche Textur, Sonne sichtbar.
  Ich: Note 2.

**Meine Bewertungskriterien waren Farbsaettigung und Anteil angeleuchteter
Wolkenflaeche - also Term A, woertlich.**  Ich hatte in Abschnitt 19.3
befuerchtet, nach den Kriterien des Modells zu bewerten; an diesen beiden
Bildern ist es belegt.  Strahlenbuescheln, Lichtstruktur und Kontrast kommen
in meinem Maszstab nicht vor, in Andres offensichtlich schon.

### 21.1 Was das entwertet

Abschnitt 20.3 rechnete: "zwei Betrachter stimmen mit rho = 0.24 ueberein,
also kann ein perfektes Modell hoechstens sqrt(0.24) = 0.49 erreichen, der
Score liegt bei 42 % davon."

**Diese Rechnung setzt voraus, dass ich ein UNABHAENGIGER zweiter Betrachter
bin.  Bin ich nicht.**  Meine Noten sind die Modellkriterien von Hand
angewandt.  Dass rho(ich, Andre) = 0.243 und rho(Score, Andre) = 0.205 so
dicht beieinander liegen, ist deshalb kein Zufall, sondern der Beleg: beide
Zahlen messen ungefaehr dasselbe.

Die Reliabilitaet des Ziels - wie gut zwei MENSCHEN uebereinstimmen - ist
damit **unbekannt**.  Sie kann deutlich hoeher liegen als 0.24.  Und wenn sie
das tut, ist auch die Produktaussage aus 20.4 ("wird es spektakulaer ist keine
wohldefinierte Frage") nicht mehr getragen.

### 21.2 Was einen echten Wert liefern wuerde

- **Test-Retest:** Andre benotet in einigen Wochen dieselben Fotos noch
  einmal, blind gegenueber seiner ersten Liste.  Die Uebereinstimmung mit
  sich selbst ist die obere Schranke fuer jede Vorhersage.  Billig und sauber.
- **Zweiter Mensch:** jemand, der das Projekt nicht kennt.
- **Nicht geeignet:** ich - solange ich weiss, worauf der Score schaut.

## 22 Andres Kriterium "Varianz im Himmel" (14.08.2026)

Auf die Frage, was seine 3 von seiner 5 unterscheidet, wenn beide zur Familie
"goldenes Licht bricht unter einer Decke durch" gehoeren:

> "Es geht auch um Varianz im Himmel. Links hast Du einen duennen Streifen
> mit Action, und sonst ist es eher monoton."

Das trifft eine echte Luecke: **Term A ist ein Mittelwert ueber den Nahbereich,
und ein Mittelwert loescht Varianz per Konstruktion.**  Ein duenner heller
Streifen und ein durchgehend angeleuchteter Himmel koennen denselben
Mittelwert haben.

### 22.1 Zwei Umsetzungen, beide ohne Gewinn

**Erste Fassung** - Verteilung der WOLKE ueber Elevationsbaender
(0-5, 5-15, 15-35, 35-90 Grad), gemessen als 1 minus Herfindahl:

    Andre  Score bisher rho +0.205  ->  x Ausdehnung rho +0.193
    ich    Score bisher rho +0.257  ->  x Ausdehnung rho +0.197

Und bei zwei der drei Paare **identisch** (0.66 gegen 0.66, 0.51 gegen 0.51).
Fehler in der Umsetzung: gemessen wurde, wo die Wolke ist, nicht wo das Licht
ist.

**Zweite Fassung** - Verteilung der BELEUCHTETEN Beitraege (aus
score_distanz, also Wolke x Raumwinkel x Sicht x Weg):

| Paar (links Note 3, rechts Note 5) | Lichtausdehnung |
|---|---|
| 2024-07-08 / 2025-05-26 | **0.00 / 0.50** richtig |
| 2023-06-16 / 2024-05-25 | 0.35 / 0.28 falsch |
| 2022-06-20 / 2022-08-03 | **0.15 / 0.31** richtig |

Zwei von drei Paaren in der richtigen Richtung - aber ueber alle 43 Abende
kein Gewinn (rho +0.205 -> +0.200 bei Andre, +0.257 -> +0.182 bei mir).

### 22.2 Warum hier Schluss ist

Die Baseline ist nicht signifikant (z = +1.33).  An einer nicht signifikanten
Baseline Termformulierungen durchzuprobieren, bis rho steigt, ist
Rauschenanpassung - und genau das habe ich in Abschnitt 20.4 fuer mich
ausgeschlossen.  Der dritte Versuch waere der erste gewesen, bei dem ich es
trotzdem getan haette.

**Das Kriterium bleibt notiert und unerledigt.**  Es ist artikuliert,
physikalisch sinnvoll und trifft zwei von drei Testfaellen - aber mit n = 43
an einem Ziel dieser Reliabilitaet nicht entscheidbar.  Wieder aufnehmen,
wenn (a) der Nachtlauf n auf 72 hebt und (b) Andres Test-Retest die
Reliabilitaet des Ziels kennt.

## 23 Varianzeinschraenkung - die Frage war falsch gestellt (14.08.2026)

Andre: *"Vielleicht ist es aber so, dass ALLE Sonnenuntergaenge schon ganz gut
sind.  Sonst haette ich sie nicht ausgewaehlt (oder fotografiert)."*

Das ist Varianzeinschraenkung, und sie erklaert die niedrigen Korrelationen
aus Abschnitt 20 vollstaendig.  Seine Noten reichen von 2 bis 5 - **keine
einzige 1**.  Innerhalb einer nach Qualitaet vorausgewaehlten Menge brechen
Korrelationen systematisch ein, auch wenn der Zusammenhang in der Gesamtheit
stark ist.

### 23.1 Simulation

Bivariat normal, Auswahl der besten X Prozent nach Qualitaet:

| rho in der Gesamtheit | rho im Album | mittlerer Perzentilrang |
|---|---|---|
| 0.30 | 0.13-0.15 | 0.62-0.65 |
| **0.40** | **0.18-0.20** | **0.66-0.70** |
| 0.50 | 0.24-0.27 | 0.70-0.75 |
| 0.60 | 0.29-0.32 | 0.74-0.79 |

Beobachtet: rho im Album **+0.205**, mittlerer Perzentilrang **0.674**.

**Beide Groessen zusammen zeigen auf rho = 0.40-0.50 in der Gesamtheit** - und
das sind zwei unabhaengige Beobachtungen, die auf denselben Wert deuten, keine
Anpassung.

### 23.2 Was rho = 0.45 operativ bedeutet

"gut" = die besten 5 % aller Abende (rund 18 im Jahr):

| Alarmrate | faengt davon | davon war gut |
|---|---|---|
| 18/Jahr | 22 % | 22 % |
| 37/Jahr | 35 % | 18 % |
| 55/Jahr | 45 % | 15 % |
| 73/Jahr | 54 % | 13 % |

Die reale Messung (37 Alarme fingen 10 von 43 Albumabenden = 23 %) liegt in
derselben Groessenordnung.

### 23.3 Was das an frueheren Abschnitten korrigiert

- **Abschnitt 18** ("zwei Faehigkeiten, nur eine gemessen"): die zweite
  Faehigkeit war nicht abwesend, sie war nur nicht messbar, weil das Album
  eine Vorauswahl ist.
- **Abschnitt 20.4** ("wird es spektakulaer ist keine wohldefinierte Frage"):
  hinfaellig.  Die niedrige Korrelation kam aus der Auswahl, nicht aus der
  Unschaerfe des Ziels.
- **Abschnitt 9.2** (Trefferquote "zu pessimistisch gerechnet"): jetzt
  quantifiziert - bei rho 0.45 sind 22 % bei 18 Alarmen im Jahr das
  Erwartbare, nicht ein Defizit.

### 23.4 Vorbehalte

Bivariat normal angenommen.  Die Auswahl erfolgte nicht rein nach Qualitaet
(Verfuegbarkeit, Blickrichtung NNW, ueberhaupt zu Hause sein) - unreine
Auswahl schwaecht den Einschraenkungseffekt, das wahre rho laege dann
niedriger als geschaetzt.  Und rho ist gegen ANDRES Note gemessen, die ihre
eigene Unzuverlaessigkeit hat; gegen ein rauschfreies Ziel waere es hoeher.

## 24 Elf Jahre Klimatologie: alles neu gerechnet (14.08.2026)

Der Nachtlauf ist durch - `score_berlin_g0.5_2015_2025.json`, 4018 Abende.
Andres Noten darin: **72** statt 46.  Albumabende: **70** statt 43.

### 24.1 Anreicherung, deutlich staerker

| | n = 43 | **n = 70** |
|---|---|---|
| S | 0.674, z +3.95 | **0.694, z +5.61** |
| A | 0.623, z +2.80 | 0.618, z +3.43 |
| B | 0.515, z +0.33 | 0.556, z +1.64 |

S schlaegt A jetzt deutlicher (0.694 gegen 0.618).

### 24.2 Trefferquote

| Alarmrate | n = 43 | **n = 70** |
|---|---|---|
| 18/Jahr | 9 % | **14 %** [8–24] |
| 25/Jahr | 12 % | 21 % [13–32] |
| 37/Jahr | 23 % | **31 %** [22–43] |
| 55/Jahr | 37 % | 41 % [31–53] |
| 73/Jahr | 47 % | 51 % [40–63] |

Alle Werte gestiegen und die Intervalle enger.  Vergleichbar mit der
Erwartung aus Abschnitt 23.2 (bei rho 0.45: 22 % bei 18 Alarmen).

### 24.3 Die Ordnung: 2 < 3 < 4 klar, 5 nicht aufloesbar

Mechanisches Ausschlusskriterium, **symmetrisch auf alle Abende angewandt**:
"Modell sieht keinen Schirm" = max(A) < 0.15.  Trifft 9 von 72, verteilt
ueber alle Noten (2/2/2/3) - keine Rosinenpickerei.

| Note | n | mittlerer Rang |
|---|---|---|
| 2 | 5 | 0.632 |
| 3 | 28 | 0.741 |
| 4 | 19 | **0.810** |
| 5 | 11 | 0.761 |

rho(Note, Rang) steigt von +0.133 auf **+0.207** (z +1.63, p 0.10) - immer
noch nicht signifikant, aber passend zur Varianzeinschraenkung aus 23.

### 24.4 Warum Andres Fuenfen einbrechen

Die 14 Fuenfen zerfallen sauber:

**Acht mit Rang 0.73 bis 0.99** - bei allen sieht das Modell substantielle
Bewoelkung (A = 0.35 bis 0.99).  Wenn die Daten stimmen, setzt der Score
Andres Fuenfen ganz nach oben.

**Fuenf mit Rang 0.10 bis 0.58**, und die Ursachen sind benannt:

| Abend | A hoch | Ursache |
|---|---|---|
| 2018-07-09 | **0.89** | Schirm da, **Weg blockiert** (0.02) |
| 2022-09-20 | 0.00 | Datenfehler (per Foto belegt) |
| 2025-09-15 | 0.00 | Datenfehler |
| 2020-07-12 | 0.01 | Datenfehler |
| 2024-05-25 | 0.68 | Schirm da, Terme mittel |

Das Foto vom 09.07.2018 zeigt intensiv rosa angeleuchtete Wolken unter einer
grauen Decke - und das Modell HATTE 85 % hohe Bewoelkung ueber Berlin.  Kein
Datenfehler, sondern der Fensterterm.

**Datenfehlerquote unter Andres Fuenfen: 3 von 14 = 21 %**, deutlich hoeher
als die 12.5 % ueber alle bewerteten Abende.  Gerade bei den besten Abenden
sieht ERA5 am haeufigsten nichts.

## 25 Niveauaufgeloest getestet - die Hypothese ist widerlegt (14.08.2026)

Erwartung aus Abschnitt 14.2: ERA5s Bedeckungsfeld saettigt bei 23 % der
Stunden auf exakt 100 % und zwingt den Score auf null; die eigene
RH-Diagnostik liefert doppelt so oft einen Zwischenwert.  **Also muesste die
niveauaufgeloeste Variante die Fehlschlaege aufloesen.**

### 25.1 Ueber Berlin allein: bestaetigt

GFS-Druckflaechen fuer Berlin, 2022-2025 (35 064 Stunden):

| Abend | GFS-Bedeckungsfeld h/m/t | eigene RH-Diagnostik h/m/t |
|---|---|---|
| 2022-09-20 | 0 / 5 / 5 | **0 / 61 / 46** |
| 2023-04-24 | 9 / 0 / 60 | **58 / 0 / 100** |

Systematisch: in **18 %** der Stunden, in denen das Bedeckungsfeld praktisch
leer ist (<5 %), sieht die Feuchtediagnostik >= 25 % Wolke.

### 25.2 Ueber den ganzen Faecher: widerlegt

Fanzellen der Problemabende geladen (58 Zellen x 20 Variablen x 5 Tage) und
`score_niveaus` gegen `score` gerechnet:

| Abend | Note | 3-Schicht S | niveauaufgeloest S |
|---|---|---|---|
| 2022-09-20 | 5 | 0.002 | 0.017 |
| 2023-04-24 | 4 | 0.000 | 0.003 |
| 2024-05-03 | 3 | 0.000 | 0.003 |
| 2024-09-15 | - | 0.028 | 0.008 |
| 2025-09-15 | 5 | 0.013 | 0.062 |

Vier von fuenf besser - **aber von praktisch null auf praktisch null**.
Die Saettigung ist weg (Weg steigt von 0.00 auf 0.11, A von 0.02 auf 0.17),
aber das Produkt zweier kleiner Zahlen bleibt klein.

**Ueber den Faecher sieht auch die Feuchte fast nichts** (A = 0.04 bis 0.30).
Beide Darstellungen desselben Modells verfehlen diese Himmel.

### 25.3 Was das fuer die Prioritaeten heisst

Die Datenluecke ist **nicht** ein Darstellungsproblem und damit nicht durch
eine andere Variable desselben Modells zu schliessen.  Sie braucht

- **ein anderes Modell** - ICON-D2 mit 2 km loest Strukturen auf, die GFS
  und ERA5 bei 25-30 km wegmitteln; Vorlauf nur 48 h, fuer den Alarm also
  nur die letzten zwei Tage, aber fuer die VALIDIERUNG voll brauchbar;
- **oder Beobachtung statt Modell** - MSG/MTG-Infrarot, 3 km, alle 15 min,
  kostenlos.  Damit waere pruefbar, ob die Wolke ueberhaupt da war.

Der Hybrid (nur die Zelle ueber Berlin aus der Feuchte, Rest wie bisher)
bringt marginal: Album-Anreicherung 0.674 -> 0.690, rho gegen Andres Noten
unveraendert.  Nicht uebernommen.

## 26 Die harten Nullen sind Signal, kein Fehler (14.08.2026)

Notiert war ein Umbau des Fensterterms: 32 % der Abende melden irgendwo
100 % Bedeckung, und 0^k ist null, egal welcher Exponent.  Der Verdacht war,
dass gute Abende daran sterben.  **Gemessen, bevor gebaut wurde:**

| | Album (n = 70) | uebrige (n = 3948) |
|---|---|---|
| Schirm A == 0 | **0.0 %** [0.0, 5.2] | 8.1 % [7.3, 9.0] |
| Fenster B == 0 | **0.0 %** [0.0, 5.2] | 9.9 % [9.0, 10.9] |
| Score s == 0 | **0.0 %** [0.0, 5.2] | 17.0 % [15.9, 18.3] |

**KORREKTUR am selben Abend, im Selbstreview gefunden.**  Der Vergleich oben
stellt das Album ALLEN uebrigen Abenden gegenueber - auch den Winterabenden.
Andres Album reicht aber nur von Maerz bis Oktober, Schwerpunkt Juni, und
zwischen November und Februar liegt **kein einziger** Abend darin.  Genau
dort wird der Score am haeufigsten null.  Der Vergleich mass also zu einem
grossen Teil Jahreszeit.

Saisonal gepaart (fuer jeden Albumabend nur sein eigenes +/-21-Tage-Fenster
ueber alle Jahre, n = 76 nach dem 2026-Nachtrag):

| | beobachtet | saisonal erwartet | z |
|---|---|---|---|
| Schirm A = 0 | 1 | 4.1 | -1.59 nicht sig. |
| Fenster B = 0 | 0 | 2.0 | -1.44 nicht sig. |
| Score s = 0 | 1 | 6.1 | **-2.19 signifikant** |

Der Effekt bleibt, aber er ist deutlich kleiner als die Rohzahlen suggerieren,
und fuer die EINZELTERME reicht es nicht mehr.  Belastbar ist nur noch: der
**Gesamtscore** wird bei Albumabenden seltener null, als die Jahreszeit
erwarten liesse.

Genau ein Albumabend hat guten Schirm bei totem Fenster (2024-09-15,
A = 0.87, B = 0.032) - der Fall, der ohnehin als eigene Baustelle notiert
ist (beleuchtete tiefe Decke als Ereignis statt als Hindernis).

**Der geplante Umbau entfaellt trotzdem** - und zwar aus dem Befund, der die
Korrektur ueberlebt: unter 76 Albumabenden stirbt **kein einziger** an einer
harten Fensternull (0 beobachtet, 2.0 saisonal erwartet).  Der Umbau sollte
genau diese Faelle retten.  Es gibt sie nicht.

Was NICHT mehr behauptet werden kann: dass die harte Null "jeden sechsten
gewoehnlichen Abend trifft und keinen Albumabend" ein starker Trennbeleg
sei.  Das war zum grossen Teil Jahreszeit.

Nebenbefund zur Sorgfalt: die erste Fassung dieser Auswertung behandelte
fehlende Werte in zwei Zeilen verschieden (`(v["A"] or 0) == 0` zaehlt None
mit, `v["B"] == 0.0` nicht).  Nachgeprueft: die Klimatologie enthaelt keinen
Eintrag ohne Daten, die Zahlen aendern sich dadurch nicht.  Der Einwand war
richtig, die Zahlen waren es auch.

Pruefbefehl: siehe `skripte/termanalyse.py` bzw. die Auswertung im
Sessionprotokoll vom 14.08.

## 27 Eine Fehlerklasse, vier Fundorte - einer davon im Betrieb

Beim ICON-Abruf meldete meine Deckungspruefung 100 % fuer Abende, deren
Druckflaechen durchgehend `None` waren: sie fragte, ob das Wertedict der
Zelle nicht leer ist, und das trug ja die drei Schichten.  Ein Test, der
bestanden aussieht, ohne etwas geprueft zu haben - dieselbe Klasse wie bei
der Modellauswahl im Juli ("Schluessel vorhanden" als "Daten vorhanden").

Der faellige Isomorphie-Check hat drei weitere Stellen gefunden:

**(a) `alarm.py` - Betriebspfad, stille Fehlrichtung.**  `member_liste()`
zaehlt Member an ihren SCHLUESSELNAMEN.  Ein Member ohne Daten steht damit in
der Liste, `score()` gibt fuer ihn sauber `(0.0, None)` zurueck, und diese
Null lief in den **Nenner** der Wahrscheinlichkeit `p = Anteil ueber s*`.
Fehlende Daten wirkten also wie eine Stimme gegen den Sonnenuntergang.  Bei
2 von 10 datenlosen Membern wird aus p = 3/8 = 0.375 eine 0.300 - kein
Fehler, keine Warnung, nur ein Alarm, der nicht ausloest.

Behoben durch `verdichte()`, herausgeloest weil die Aggregation vorher
zwischen zwei Netzabfragen sass und nicht pruefbar war.
Regressionstest `skripte/test_member.py`, 11 Pruefungen.

Der Test prueft nicht nur die Arithmetik, sondern den **Diskriminator**:
`score()` liefert `detail is None` genau dann, wenn nichts belegt war.  Ein
Fall lief dabei auf FEHL, und die Erwartung war falsch, nicht der Code - ohne
Daten im Nahbereich ist Term A **undefiniert**, nicht null.  Solche Member
gehoeren aus dem Nenner.

**(b) `ablation.py` - Verzerrung in die bequeme Richtung.**  Jeder Score
wurde angehaengt, auch die Nullen datenloser Abende.  Dort liefern *beide*
Verfahren exakt 0.0, stimmen also perfekt ueberein und treiben Spearman nach
oben - waehrend die Ablation genau diese Uebereinstimmung messen soll.  Die
Verzerrung zeigte auf "die Rangfolgen fallen zusammen, s* ist uebertragbar",
also auf das Ergebnis, das weniger Arbeit macht.  T-0006 waere mit einer
zu freundlichen Zahl abgeschlossen worden.

**(c) `icond2.py` - 429 ist nicht gleich 429.**  Open-Meteo verwendet den
Code fuer "Too many concurrent requests", fuer das Minutenlimit und fuer
erschoepfte Kontingente.  Alle drei als terminal gelesen: der erste Lauf kam
ueber 5 von 166 Abenden nicht hinaus, bei voller Tagesquote.

**Merksatz:** Ein Test, der nicht scheitern kann, ist kein Test.  Die
Frage ist nie "ist der Schluessel da", sondern immer "wie viele Werte sind
nicht None" - und die Antwort gehoert in die Ausgabe, nicht in eine
Bedingung.

## 28 T-0001b: das Absichtssignal traegt in die richtige Richtung, aber zu schwach

Der urspruengliche Presence-Only-Test verglich Abende MIT Fotos gegen alle
uebrigen - und mass damit vor allem, ob Andre draussen war.  Konfundiert.

Sauberer Aufbau: nur die **768 Draussen-Abende** in Berlin (Fotos innerhalb
+/- 45 min um den Sonnenuntergang, 2015-2025).  Innerhalb dieser Menge ist
"war er ueberhaupt draussen" konstant.  Uebrig bleibt die Absicht - hat er
ein Bild als Favorit markiert?  86 Abende mit, 682 ohne.

| | Favorit (n=86) | ohne (n=682) |
|---|---|---|
| Median S | 0.0625 | 0.0460 |
| Mittel S | 0.1876 | 0.1398 |
| saisonaler Mittelrang | 0.558 | 0.515 |

A = 0.545 auf Raengen (z = +1.35), 5 von 8 Jahrgaengen mit A > 0.5,
KI [0.31, 0.86].  **Nicht signifikant.**

**Und das heisst hier ausdruecklich nicht "kein Effekt".**  Der Test hat bei
86 gegen 682 eine Nachweisgrenze von A = 0.593 (Power 80 %, alpha 0.05).
Ein echter Effekt von 0.545 liegt darunter - fuer den Nachweis braeuchte es
rund 364 Favoritenabende.  Das Ergebnis ist mit "kein Zusammenhang" und mit
"schwacher Zusammenhang" gleichermassen vertraeglich.

**Die eigentliche Erkenntnis ist eine ueber das Messinstrument.**  Dasselbe
Modell erreicht gegen das kuratierte Album z = +5.61.  Der Favoritenstern ist
ein viel verrauschteres Label - man markiert ein Bild auch wegen der Personen
darauf, wegen des Anlasses, wegen der Schaerfe.  Das kuratierte Album ist
nicht der schwaechere Ersatz fuer ein "objektives" Signal, sondern das
schaerfere Instrument.

Pruefbefehl: `python3 skripte/absicht.py`

Nebenbefund zur Sorgfalt: die erste Fassung beschriftete A in die
Gegenrichtung (`mannwhitney(ohne, favorit)` liefert P(ohne > Favorit), die
Prosa behauptete das Gegenteil).  Die Jahrgangstabelle haette damit "3 von 8"
statt "5 von 8" gemeldet - ein Vorzeichenfehler in der Beschriftung, nicht in
der Rechnung, und genau deshalb keiner, den ein Testlauf findet.

## 29 Aufloesungstest: ICON-D2 gegen ERA5 - knapp am eigenen Kriterium vorbei

Nach Befund 25 (Feuchte statt Bedeckung traegt nicht) blieb die Frage eine
Ebene tiefer: liegt es an der **Gitterweite**?  ERA5 und GFS rechnen auf
25-30 km und mitteln genau die Strukturen weg, die das Ereignis ausmachen -
eine Wolkenbank mit scharfer Westkante, ein Loch im Stratocumulus.
ICON-D2 rechnet auf 2.2 km.

**Aufbau.**  Gepaart, nicht gegen eine Klimatologie.  Jeder Albumabend ab
2023 bildet einen Block mit vier Kontrollabenden aus seinem +/- 21-Tage-
Fenster; gemessen wird sein Rang INNERHALB des Blocks.  Das haelt Jahreszeit,
Sonnenstand und Tageslaenge konstant.  35 Bloecke, 166 Abende, 5976 Abfragen.

Beide Verfahren rechnen **denselben Score auf derselben Faechergeometrie** -
es unterscheidet sich nur die Gitterweite der Quelle.

**Gueltigkeitspruefung vorweg** (korrigiert 15.08., siehe 32.4 - die erste
Fassung stand auf einem Teilcache mitten im Abruf): ueber alle **166** Abende
Spearman **+0.698**, Pearson +0.554.  Die Mittel sind NICHT praktisch gleich
(0.222 gegen 0.186, ICON liegt 16 % niedriger).  Bei rho 0.70 misst die Kette
Meteorologie und kein Artefakt; die zuerst berichteten Zahlen waren falsch.

**Und die Ueberschrift dieses Abschnitts traegt nicht.**  "ERA5 25 km" ist
falsch: die Klimatologie steht auf `ecmwf_ifs`, also IFS-ANALYSEN auf rund
9 km (Befund 32.1).  Der Test vergleicht Faktor 4, nicht Faktor 11.  Richtig
formuliert lautet das Ergebnis: **bei Faktor 4 in der Gitterweite ist kein
Effekt nachweisbar** - nicht "Aufloesung ist als Erklaerung gefallen".

| Verfahren | Mittelrang | 95 %-KI | z |
|---|---|---|---|
| ERA5, 25 km | 0.593 | [0.492, 0.693] | +1.81 nicht sig. |
| **ICON-D2, 2.2 km** | **0.657** | [0.545, 0.769] | **+2.75 signifikant** |

Gepaarte Differenz **+0.064**, KI **[-0.037, +0.165]**.
Vorzeichen: 13 Bloecke besser mit ICON, 9 schlechter, 13 unentschieden.

**Vorab festgelegt war: Wechsel nur bei >= +0.05 UND Konfidenzintervall ohne
Null.**  Der Punktschaetzer erfuellt die Schwelle, das Intervall nicht.
**Also kein Wechsel.**

Bemerkenswert bleibt, dass ICON-D2 als einziges der beiden Verfahren fuer
sich genommen Signifikanz erreicht - ERA5 verfehlt sie.  Fuer 80 % Power auf
die Differenz braeuchte es 177 Bloecke statt 35: 885 Abende, rund 32 000
Abfragen, etwa 3.2 Tagesbudgets.

**Gegenlaeufiger Nebenbefund.**  Innerhalb des Albums ordnet ICON-D2
schlechter (Spearman gegen Andres Noten +0.259 gegen +0.411 bei ERA5).  Es
trennt Album von Kontrolle besser und ordnet innerhalb des Albums schlechter.
Bei n = 34 und der bekannten Varianzeinschraenkung ist dieser Unterschied
nicht belastbar - aber er passt zu Befund 22: Anreicherung und Ordnung sind
verschiedene Faehigkeiten.

**Und der Punkt, der den Rest erledigt:** ICON-D2 hat **48 h Vorlauf** und
existiert nur ueber Mitteleuropa.  Der Alarm braucht 2 bis 10 Tage, und
Andre will die App fuer Freundinnen und Freunde an beliebigen Orten.  Selbst
ein klar positives Ergebnis haette den Betriebsscore nicht ersetzen koennen,
sondern nur als Validierungswerkzeug getaugt.  Die 3.2 Tagesbudgets fuer den
Nachweis lohnen sich damit nur, wenn man wissen will, WARUM es klemmt - nicht,
um es zu beheben.

Pruefbefehle:
`python3 skripte/icond2.py --kontrollen 4` (Abruf, gecacht)
`python3 skripte/icond2_test.py` (Auswertung)

## 30 Ein Kontrastwert ohne seine Flaeche ist keine Angabe

Beim Bau des Sitzungsberichts fiel ein Fehler in der ausgelieferten
Produktseite auf.  `stil/tokens.css` schrieb `--gitter` fuer alles
Informationstragende vor und bescheinigte dem Wert **3.51:1, erfuellt
WCAG 1.4.11**.  Diese 3.51:1 gelten gegen `--papier` (#000000).

Die zwei gestrichelten Schwellenlinien im Zeitstreifen liegen aber in
`.achse-karte`, und die hat `background: var(--karte)` (#1c1c1e).  Dort
faellt derselbe Wert auf **2.84:1** - unter die 3.0, die WCAG 1.4.11 fuer
grafische Objekte verlangt.  Und die Linien sind nicht dekorativ: sie
markieren das 80. und 95. Perzentil, ohne sie ist die Position des Punktes
so unverankert wie eine nackte Prozentzahl (so steht es im Kommentar des
Skripts selbst).

| Wert | auf `--papier` | auf `--karte` | auf `--boden` |
|---|---|---|---|
| #636366 (alt) | 3.51:1 | **2.84:1** | 2.30:1 |
| #8e8e93 (neu) | 6.44:1 | 5.22:1 | 4.27:1 |

`--gitter` ist auf `#8e8e93` angehoben (Apple systemGray, dieselbe Familie).
Der alte Wert bleibt als `--gitter-schwach` fuer rein dekorative Feinlinien.
Der Done-Eintrag zu T-0010 behauptete "alle Kontraste ueber AA" und ist
korrigiert.

**Warum das hier steht und nicht nur im Tokenfile:** der Fehler war nicht
Nachlaessigkeit beim Messen, sondern eine unvollstaendige Angabe.  Eine Zahl
wie "3.51:1" sieht aus wie ein Faktum und ist in Wahrheit eine Relation
zwischen zwei Farben.  Wer sie ohne die zweite Farbe notiert, hat sie fuer
jede andere Flaeche falsch notiert - und merkt es nie, weil die Notiz
selbstbewusst aussieht.  Dieselbe Form von Fehler wie bei 429 (ein Code,
drei Bedeutungen) und bei "Schluessel vorhanden" (ein Test, der nicht
scheitern kann).

Gefunden wurde er nicht beim Bau der Produktseite, sondern beim
**Uebertragen derselben Pruefung auf eine zweite Seite**.

## 31 T-0006 Ablation: s* ist NICHT uebertragbar - und der Test hat ein Loch

Load-bearing, weil s* = 0.7065 aus der **3-Schicht**-Klimatologie stammt.
Falls der Betrieb je auf die niveauaufgeloeste Variante wechselt, muss die
Rangfolge dieselbe sein - sonst bedeutet der Schwellwert dort etwas anderes.

Gerechnet auf `gfs_global`, das als einziges Archiv Druckflaechen UND natives
low/mid/high fuer denselben Zeitpunkt liefert.  Beide Scores sehen damit exakt
denselben Modellzustand.  42 Abende, 15.09. bis 26.10.2025, 67 Zellen,
23 Variablen.  **Kein Abend wurde wegen fehlender Daten uebersprungen** - die
Entzerrung aus Befund 27b hat hier also nichts veraendert, haette es aber,
sobald Luecken auftreten.

| | Median | p75 | p90 | Max |
|---|---|---|---|---|
| 3-Schicht | 0.0000 | 0.0030 | 0.1094 | 0.3919 |
| niveauaufgeloest | 0.0090 | 0.0619 | 0.1644 | 0.4591 |

Spearman **rho = +0.697**, 95 %-KI [0.499, 0.826].
Top-15-%-Ueberlappung: **4 von 6**.

**Antwort: nein.**  Rho 0.70 heisst deutlicher Zusammenhang, aber nicht
austauschbar - dafuer braeuchte es 0.95 aufwaerts.  Zwei von sechs Spitzen-
abenden unterscheiden sich, und die Verteilung liegt niveauaufgeloest
durchweg hoeher (Median 0.0090 gegen 0.0000, p90 um die Haelfte).  Ein
Perzentilschwellwert aus der einen Verteilung bedeutet in der anderen etwas
anderes.  **Bei einem Wechsel muss s\* neu hergeleitet werden.**

Praktisch ist gerade nichts kaputt: `alarm.py` rechnet auf `sonnen/score.py`,
also derselben Variante, aus der s\* stammt.  Die Warnung in der README war
richtig.

**Das Loch im Test, und es ist gross.**  In diesen 42 Herbstabenden erreicht
**kein einziger** Abend s\* = 0.7065 - die Maxima liegen bei 0.39 und 0.46.
Das Fenster enthaelt also null Ereignisse.  Gemessen wurde damit die
Uebereinstimmung im **Mittelfeld**, waehrend der Alarm ausschliesslich im
**Schwanz** lebt.  Ueber die Rangfolge dort sagt rho = 0.697 nichts.

### 31.1 Nachgeholt am selben Abend: das Sommerfenster

Das Loch war in einer Stunde zu schliessen.  Gewaehlt wurde 01.06.-12.07.2023,
das ereignisreichste 42-Tage-Fenster der Klimatologie (8 Ausloesungen).

| Fenster | rho | 95 %-KI | Top-6 gemeinsam | Max 3-Schicht | Max niveau |
|---|---|---|---|---|---|
| Herbst, 0 Ereignisse | +0.697 | [0.498, 0.826] | 4 von 6 | 0.392 | 0.459 |
| **Sommer, 8 Ereignisse** | **+0.504** | [0.236, 0.701] | **1 von 6** | 0.757 | 0.488 |

Die Intervalle ueberschneiden sich, der Unterschied ZWISCHEN den Fenstern ist
also selbst nicht gesichert.  Entscheidend ist der Absolutwert im Sommer:
**rho 0.50 und genau ein gemeinsamer Spitzenabend von sechs.**  Dort, wo der
Alarm lebt, sind sich die beiden Varianten praktisch uneinig darueber, welche
Abende die besten sind.

**Und die Zahl, die es endgueltig entscheidet.**  Im selben Sommerfenster,
mit demselben s\* = 0.7065:

    3-Schicht          2 Ausloesungen   (Maximum 0.757)
    niveauaufgeloest   0 Ausloesungen   (Maximum 0.488)

Das Maximum der niveauaufgeloesten Variante liegt **unter der Schwelle**.
Derselbe Schwellwert erzeugt auf der einen Variante Alarme und auf der
anderen keinen einzigen - das ist kein Randfall, das sind zwei Massstaebe.
Fuer dieselbe Ausloeserate muesste s\* dort deutlich niedriger liegen.

**KORREKTUR 15.08.2026 (Fable-Gutachten).**  Dieser Abschnitt rechnete
zunaechst mit s\* = 0.6325 und meldete 3 statt 2 Ausloesungen.  0.6325 gilt
nur fuer GEWICHTUNG="punkt" und ist seit der Umstellung auf
Raumwinkelgewichtung durch 0.7065 ersetzt - **im selben Dokument, Abschnitt
10.3**.  Ich habe den ueberholten Wert aus dem Gedaechtnis wiedereingefuehrt,
statt in konfig.json nachzusehen.  Die Folgerung aendert sich nicht (die
niveauaufgeloeste Variante loest in beiden Faellen nie aus), die Zahl schon.
Derselbe Wert steckte fest verdrahtet in `termanalyse.py` und `rueckschau.py`
und ist dort jetzt durch einen Lesezugriff auf konfig.json ersetzt.

**T-0006 ist damit klar beantwortet: nicht uebertragbar, und zwar am
staerksten genau dort, wo es zaehlt.**  Ein Wechsel auf die
niveauaufgeloeste Variante ist ohne eigene Klimatologie und eigenes s\*
nicht moeglich - was den Aufwand dieses Wechsels erheblich erhoeht und ihn
gegenueber Befund 25 (der ihm ohnehin keinen Gewinn bescheinigt) endgueltig
nach hinten schiebt.

Nebenbefund zur Werkzeugpflege: `ablation.py` schrieb immer nach
`daten/ablation.json` und haette den Herbstlauf still ueberschrieben - zwei
Ergebnisse mit verschiedenem Zeitraum haetten hinterher wie eines ausgesehen.
Der Dateiname traegt jetzt das Fenster.

Pruefbefehl: `python3 skripte/ablation.py --von 2023-06-01 --bis 2023-07-12`

Pruefbefehl: `python3 skripte/ablation.py`

## 32 Vier Korrekturen aus dem Fable-Gutachten (15.08.2026)

Ein externes Gate mit vollem Repo-Zugriff hat vier Dinge gefunden, die ich
selbst nicht gefunden hatte.  Alle vier sind hier nachgerechnet und bestaetigt.

### 32.1 Die Klimatologie ist NICHT ERA5

`klimatologie.py` ruft `archive-api` **ohne `models=`** auf.  Der Default ist
nicht ERA5.  Live geprueft, vier Junimonate, byte-identisch verglichen:

| Jahr | ohne `models=` gegen `models=era5` | gegen `models=ecmwf_ifs` |
|---|---|---|
| 2019 | abweichend | **gleich** |
| 2021 | abweichend | **gleich** |
| 2022 | abweichend | **gleich** |
| 2023 | abweichend | **gleich** |

Die gesamte Klimatologie (11 Jahre, 4058 Abende) steht auf **ECMWF-IFS-
Analysen**.  Jede Stelle im Projekt, die "ERA5" sagte, war falsch.

**Folge fuer Befund 29, die ich selbst ziehen muss:** dort steht "ERA5 25 km
gegen ICON-D2 2.2 km".  IFS-Analysen laufen auf rund **9 km**.  Der
Aufloesungstest verglich also Faktor 4, nicht Faktor 11 - was erklaert, warum
der Effekt klein ausfiel, und die Ueberschrift "Gitterweite ist als Erklaerung
gefallen" nicht traegt.  Richtig ist: **bei Faktor 4 nicht nachweisbar.**

### 32.2 Regimebruch 2022 im selben Datenprodukt

Anteil exakt 100 % Bedeckung im Rohcache der Klimatologie:

| Jahr | low | mid | high |
|---|---|---|---|
| 2015-2021 | 9-16 % | 4-10 % | **7-12 %** |
| 2022-2025 | 15-19 % | 11-17 % | **19-27 %** |

Der `high`-Anteil verdoppelt sich.  Das ist kein Wetter.  Das Album liegt
schief dazu: 27 Abende vor 2022, 49 danach.

Aera-gepaart nachgerechnet (Rang nur gegen Abende derselben Aera):

    gepoolt        Mittelrang 0.671
    aera-gepaart   Mittelrang 0.657

**Die Anreicherung haelt.**  Sie ist kein Artefakt des Regimewechsels.

### 32.3 Mein z war mit der falschen Streuung gerechnet

Ich habe die **Stichproben**-SD in den Nenner gesetzt (0.2545).  Unter H0
sind die Raenge gleichverteilt, ihre SD ist **0.2887**.  Wer die kleinere
beobachtete Streuung nimmt, testet gegen etwas, das H0 nicht behauptet.

    z mit Stichproben-SD   +5.86   (berichtet, zu gross)
    z mit Null-SD          +5.16   (richtig)

Alle frueher berichteten z-Werte dieser Bauart sind entsprechend zu gross.
Keine Schlussfolgerung kippt dadurch, aber die Zahlen sind zu korrigieren.

### 32.4 Meine Gueltigkeitspruefung in Befund 29 stand auf einem Teilcache

Dort steht "ERA5 und ICON-D2 stimmen ueber **77** gemeinsame Abende mit
rho = +0.746 ueberein, bei praktisch gleichem Mittel (0.230 gegen 0.221)".

Diese Zahl entstand **mitten im Abruf**, als erst 77 von 166 Abenden im Cache
lagen.  Ich habe sie nach Abschluss nie neu gerechnet.  Endstand:

    n = 166   Spearman +0.698   Pearson +0.554
    Mittel: Klimatologie 0.222   ICON 0.186

Die Mittel sind **nicht** praktisch gleich - ICON liegt 16 % niedriger.  Die
Folgerung (die Kette misst Meteorologie) haelt bei rho 0.70, die Zahlen sind
falsch berichtet.

**Merksatz:** eine Zwischenzahl aus einem laufenden Abruf ist ein Messwert
ueber einen Teilcache, kein Ergebnis.  Wer sie nicht am Ende wiederholt,
berichtet den Zustand einer Baustelle.
