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

## Kontingent: geklaert (14.08.2026)

Die Memberzahl multipliziert NICHT.  Gemessen: 10x3, 25x3 und 10x9 Variablen
liefen nacheinander durch - unter der Member-Hypothese waeren das kumulativ
9945 gewichtete Calls gewesen und der zweite Test haette scheitern muessen.

Die Limits gelten aber **endpunktuebergreifend**.  Die frueheren Fehlschlaege
des Alarmlaufs waren Kollateralschaden des Klimatologie-Backfills, nicht ein
Problem des Alarms.  Pass 1 (75 Zellen x 9 Variablen) laeuft sauber durch;
Pass 2 braucht 147 zusaetzliche Zellen und passt ins Tagesbudget, solange am
selben Tag kein Backfill laeuft.

**Regel fuer den Betrieb: Kalibrierungslaeufe nie am selben Tag wie der
Alarmlauf.**

## Abbruchtest: unentschieden, Label konfundiert

272 Berliner Fotoabende 2022-2025.  S: Mittelrang 0.510, z +0.57 - nichts.
Aber die Terme einzeln zeigen den Grund:

    Term B (freier Westen)  Fotoabende 0.466 vs 0.398  z = +2.77  signifikant
    Term A (hohe Wolken)               0.413 vs 0.454  z = -1.76

Das Label misst "war draussen".  Draussen sein korreliert mit klarem Himmel,
also MIT Term B und GEGEN Term A; im Produkt heben sich beide auf.  Kein
leeres Label, ein konfundiertes.  Kein Trend ueber die Fotozahl, die
Verduennungshypothese traegt also nicht allein.

Aufloesung nur durch Vergleich INNERHALB der Draussen-Abende - dafuer
`skripte/fotos_detail.py` aus Terminal.app laufen lassen (Favoriten und
Minutenabstand als Absichtssignal).

## Next actions

1. **T-0001b Absichtssignal** — `fotos_detail.py` aus Terminal.app.
   Ohne das bleibt der Abbruchtest unentschieden.
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
