# STATE

Stand: 14.08.2026

## Ziel

Zwei bis zehn Tage im Voraus eine Wahrscheinlichkeit fuer einen
aussergewoehnlichen Sonnenuntergang in Berlin melden — und den Abend danach
zeigen.

## Status

- E0 abgeschlossen und freigegeben. Entscheidungen: absoluter Schwellwert,
  keine Kamera, nichts Kommerzielles, Ort als Parameter (auch fuer Freunde),
  GitHub Pages, ntfy.
- E1 laeuft. Gates durch, zwei Kernmodule stehen und sind verifiziert.
- **Modell entschieden: `ecmwf_ifs025`** (51 Member, 3-h-Raster ueber die vollen
  360 h). WeatherNext 2 als Zweitmeinung. Alle anderen Ensembles liefern fuer
  unsere Variablen nur `null` — Multi-Modell-Idee ist tot.
- **Wolkendiagnostik kalibriert und gegengeprueft.** Die Ausgangsannahme
  (RH ueber Eis mit Schwelle bei Saettigung) war falsch und ist widerlegt;
  gewaehlt ist eine nukleationsfoermige Schwelle. Gegen ERA5 erreicht sie
  r 0,768 — mehr als GFS' eigenes Wolkenschema (0,730).
- **ERA5 auf Open-Meteo hat keine Druckflaechen.** Klimatologie laeuft
  stattdessen auf `gfs_global` (ab 2022). Ensemble-Archiv nur 93 Tage tief.

## Next actions

1. **T-0001 Fotogate** — blockiert, braucht Festplattenvollzugriff (Andre).
   Ohne dieses Gate gibt es keinen Abbruchtest fuer E1.
2. **T-0003 Taegliche Ensemble-Archivierung** einrichten — haengt an nichts,
   jeder Tag Wartezeit ist ein verlorener Kalibrierungstag.
3. **T-0002 Klimatologie** auf `gfs_global`, 4 Jahre, Berlin → s\*.

## Letzte Done

- Repo angelegt, `sonnen/geometrie.py` und `sonnen/feuchte.py` verifiziert.
- Sonnenuntergangszeiten gegen Open-Meteo unabhaengig bestaetigt (19:33 UTC
  im Juni — die E0-Korrektur haelt).
- Kalibrierung Eiszweig: Training 2023-24, Test 2025 ausgehalten.
- `docs/befunde-e1.md` mit allen Messungen und Pruefbefehlen.
