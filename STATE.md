# STATE

Stand: 14.08.2026 (E2 gebaut, Kontingent blockiert)

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
  deshalb als 3-Schicht-Variante auf ERA5. Ensemble-Archiv nur 93 Tage tief.
- **s\* = 0.6325 → 18.5 Ausloesungen/Jahr** (4 Jahre, 74 Ereignisse, +/-12 %).
  Januar: null Ausloesungen in 124 Abenden (P = 0.002, kein Rauschen).
  r(A,B) = -0.259 — der Fensterterm traegt eigene Information.

## Offenes Risiko: API-Kontingent

Die Ensemble-API scheint mit der MEMBERZAHL zu gewichten (Hypothese, noch
nicht bestaetigt).  Dann kostet ein Alarmlauf 75 Zellen x 9 Variablen x 51
Member = 34 425 gewichtete Calls bei 5000/Stunde und 10 000/Tag - der
Betrieb passt dann NICHT ins Gratiskontingent.  Meine fruehere Aussage
"Betrieb passt, nur der Backfill nicht" beruhte auf einer Schaetzung ohne
Member und ist damit hinfaellig.  Eine saubere Skalierungsmessung steht aus.

## Next actions

1. **T-0001 Fotogate** — Spotlight-Weg liefert 33 Abende (18 Berlin), knapp
   ueber der Grenzwertigkeit. Mehr gibt es nur aus der Mediathek, und die
   braucht einen Lauf aus Terminal.app (nicht aus Claude Code: dort liest
   das eingebettete Bundle com.anthropic.claude-code, das keine Freigabe hat).
2. **T-0006 Ablation** — blockiert bis morgen (Tageskontingent erschoepft).
   `python3 skripte/ablation.py` setzt am Cache fort. Entscheidet, ob s*
   auf den Betriebsscore uebertragbar ist.
3. **T-0003 Archivierung** als Cron einrichten — ebenfalls kontingentblockiert,
   aber ab morgen taeglich noetig.

## Letzte Done

- Repo angelegt, `sonnen/geometrie.py` und `sonnen/feuchte.py` verifiziert.
- Sonnenuntergangszeiten gegen Open-Meteo unabhaengig bestaetigt (19:33 UTC
  im Juni — die E0-Korrektur haelt).
- Kalibrierung Eiszweig: Training 2023-24, Test 2025 ausgehalten.
- Klimatologie gerechnet, s* = 0.6325 (18.5 Ausloesungen/Jahr).
- Interpolation gemessen: Semi-Lagrange 42 % besser auf 300 hPa.
- Beide Score-Varianten implementiert und an Grenzfaellen geprueft.
- `docs/befunde-e1.md` mit allen Messungen und Pruefbefehlen.
