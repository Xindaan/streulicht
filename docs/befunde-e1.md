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
| Klimatologie, s\*, Saisonzyklus | `historical-forecast-api`, `gfs_global` | **≥ 2022** |
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
- Klimatologie auf `gfs_global` (4 Jahre) → s\* — noch nicht gerechnet.
- Taegliche Ensemble-Archivierung — noch nicht eingerichtet.
