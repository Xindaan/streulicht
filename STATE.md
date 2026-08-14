# STATE

Stand: 14.08.2026 abends (Aufloesungstest gegen ICON-D2 gerechnet,
drei Fehler derselben Klasse behoben, einer davon im Betrieb)

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

**KORREKTUR 14.08.2026 nachmittags: die Limits gelten NICHT
endpunktuebergreifend.**  Hier stand das Gegenteil.  Zweimal in
entgegengesetzter Richtung gemessen, was Zufall ausschliesst:

| Wann | `archive` / `historical-forecast` | `ensemble` |
|---|---|---|
| vormittags | gesperrt | laeuft |
| nachmittags | laeuft | gesperrt |

Die Budgets sind getrennt.  Die Betriebsregel bleibt trotzdem bestehen,
aber aus einem anderen Grund: der Alarm laeuft auf `ensemble-api`, die
Kalibrierung auf den historischen - sie behindern sich nicht, aber jeder
Topf ist fuer sich schnell leer.

**Ausserdem: 429 ist nicht gleich 429.**  Derselbe Code steht fuer "zu viele
gleichzeitig" (warten), "Minutenlimit" (warten) und "Kontingent" (Schluss).
Wer alle drei gleich behandelt, bricht bei voller Quote ab - siehe README.

## Abbruchtest: unentschieden, Label konfundiert

272 Berliner Fotoabende 2022-2025.  S: Mittelrang 0.510, z +0.57 - nichts.
Aber die Terme einzeln zeigen den Grund:

    Term B (freier Westen)  Fotoabende 0.466 vs 0.398  z = +2.77  signifikant
    Term A (hohe Wolken)               0.413 vs 0.454  z = -1.76

Das Label misst "war draussen".  Draussen sein korreliert mit klarem Himmel,
also MIT Term B und GEGEN Term A; im Produkt heben sich beide auf.  Kein
leeres Label, ein konfundiertes.  Kein Trend ueber die Fotozahl, die
Verduennungshypothese traegt also nicht allein.

**Aufgeloest am 14.08.2026 (Befund 28), Ergebnis: unentschieden bleibt
unentschieden.**  `fotos_detail.py` ist gelaufen.  Innerhalb der 768
Draussen-Abende scoren Favoritenabende hoeher (Mittelrang 0.558 gegen 0.515,
A = 0.545), aber nicht signifikant - und die Nachweisgrenze dieses Tests
liegt bei A = 0.593, es braeuchte 364 statt 86 Favoritenabende.

Die Erkenntnis liegt woanders: dasselbe Modell erreicht gegen das kuratierte
Album z = +5.61.  **Das Album ist das schaerfere Instrument, nicht der
Notbehelf.**  `python3 skripte/absicht.py`

## Oberflaeche: E3 gestalterisch fertig (14.08.2026)

Die Produktseite laeuft auf Andres Hausstandard aus `poisson-dor` und
`rezept-grid`. Neu: `stil/tokens.css` als einzige Farb- und Massquelle, von
`seite.py` in die Seite inlined; `schnitt.py` hat danach keine feste Farbe
mehr. Entscheidungen und Herleitung in `docs/ui-referenz.md`, Ergebnis in
T-0010.

Drei Sachen waren echte Fehler, keine Geschmacksfragen, und sind behoben:
der Fusstext lag bei 2,28:1 Kontrast (AA verlangt 4,5), die Beschriftung im
Vertikalschnitt bei 3,5-4,3 px auf dem Telefon, und der Balken war ein
Fuellstand von null, obwohl kein Abend je unter das 59. Perzentil faellt.

**Offen bleibt T-0015: die Seite ist nirgends ausgeliefert.** Das Repo hat
kein Remote, also auch keinen Pages-Zweig. Erst danach ist E3 zu.

## Naechster Lauf, wenn Kontingent zurueck ist

**HINFAELLIG (Befund 25, 14.08.2026).**  Hier stand die niveauaufgeloeste
Klimatologie als naechster grosser Lauf, begruendet mit der Saettigung von
ERA5s Bedeckungsfeld.  Ueber Berlin allein stimmt das (0/5/5 im Feld gegen
0/61/46 aus der Feuchte), ueber den ganzen Faecher nicht: dort sieht auch die
Feuchte nur A = 0.04 bis 0.30.  Der Score steigt an vier von fuenf
Problemabenden - von praktisch null auf praktisch null.

Der Aufloesungstest (Befund 29) hat danach ICON-D2 mit 2.2 km geprueft und
das vorab gesetzte Kriterium knapp verfehlt (+0.064, KI [-0.037, +0.165]).

**Damit sind Darstellung und Aufloesung beide durch.  Offen bleibt
Beobachtung statt Modell (T-0019, MSG/MTG-Infrarot).**  Feineres Gitter,
erweiterter Faecher und Folgestunde bleiben moeglich, aber ohne Befund,
der sie priorisiert.

Entscheidung 14.08.: kein kommerzielles Kontingent, es dauert eben laenger.
Ebenfalls gestrichen: die Sichtbarkeitszeile im Alarm - Andre geht zur Not
vor die Tuer und braucht nur zu wissen, ob es gut wird.

## Next actions

Alle drei haengen an etwas, das ich nicht selbst entscheiden oder
beschaffen kann.

1. **T-0015 Seite ausliefern** — braucht ein Repo-Remote, das nur Du anlegen
   kannst. Die Seite steht lokal, rendert korrekt (nachgesehen 14.08.) und
   ist self-contained. Danach ist E3 zu.
2. **T-0003 Archivierung** als Cron auf dem NAS — `ensemble-api` war am
   14.08. nachmittags erschoepft. Vor dem Einrichten `--trocken` pruefen.
3. **T-0019 MSG/MTG-Infrarot** — die letzte offene Antwort auf die
   Datenluecke, nachdem Darstellung (Befund 25) und Aufloesung (Befund 29)
   beide nichts getragen haben. Braucht vermutlich eine EUMETSAT-Anmeldung,
   also Deine Entscheidung.

**T-0006 ist erledigt (Befund 31):** s\* ist NICHT uebertragbar. Im
ereignisreichen Sommerfenster rho = +0.504, nur 1 von 6 Spitzenabenden
gemeinsam, und mit demselben s\* loest die 3-Schicht dreimal aus, die
niveauaufgeloeste kein einziges Mal. Der Betrieb laeuft auf der richtigen
Variante; ein Wechsel braeuchte eine eigene Klimatologie.

## Letzte Done

- Repo angelegt, `sonnen/geometrie.py` und `sonnen/feuchte.py` verifiziert.
- Sonnenuntergangszeiten gegen Open-Meteo unabhaengig bestaetigt (19:33 UTC
  im Juni — die E0-Korrektur haelt).
- Kalibrierung Eiszweig: Training 2023-24, Test 2025 ausgehalten.
- Klimatologie gerechnet, s* = 0.6325 (18.5 Ausloesungen/Jahr).
- Interpolation gemessen: Semi-Lagrange 42 % besser auf 300 hPa.
- Beide Score-Varianten implementiert und an Grenzfaellen geprueft.
- `docs/befunde-e1.md` mit allen Messungen und Pruefbefehlen.
- T-0010 Produktseite auf den Hausstandard portiert: Token-Datei, Zeitachse
  statt Balken, telefonfester Vertikalschnitt, alle Kontraste ueber AA.
