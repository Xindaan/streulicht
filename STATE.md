# STATE

Stand: 18.08.2026 vormittags. **Der Betrieb laeuft, die Oberflaeche ist neu -
auf beiden Schirmgroessen.** Repo oeffentlich, Pages liefert Prognose-,
Bewertungs- und Bilanzseite, ntfy eingerichtet, fuenf launchd-Agenten
geladen. Der UX-Overhaul (T-0031 bis T-0034) ist vollstaendig umgesetzt, die
Echo-Pushs sind weg, und die Desktopfassung (T-0037) laeuft als Breakpoint
in derselben Datei.
Fachlich unveraendert: Anwesenheit der Wegwolken (35), ihre Hoehe (36) und
der Term selbst (37) sind alle drei geprueft und erklaeren die toten Fenster
nicht. Der Score bleibt, wie er ist.

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
- **Das Archiv auf Open-Meteo hat keine Druckflaechen.** Klimatologie
  laeuft deshalb als 3-Schicht-Variante. **Die Quelle ist NICHT ERA5,
  sondern `ecmwf_ifs` (IFS-Analysen, rund 9 km)** - `archive-api` liefert
  ohne `models=` dieses Produkt. Vier Wochen lang falsch benannt, siehe
  Befund 32.1. Ausserdem: Regimebruch 2022, der 100-%-Anteil bei `high`
  verdoppelt sich. Die Anreicherung haelt aera-gepaart (0.671 -> 0.657). Ensemble-Archiv nur 93 Tage tief.
- **s\* = 0.7065 → 18.5 Ausloesungen/Jahr** (4 Jahre, 74 Ereignisse, +/-12 %).
  (0.6325 galt nur fuer GEWICHTUNG="punkt", siehe Befund 10.3.)
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

**T-0015 erledigt 15.08.2026.** Repo oeffentlich auf
`github.com/Xindaan/streulicht`, Pages ab `main` aus der Wurzel (GitHub
erlaubt nur `/` oder `/docs`, nicht `/web`). Die Bewertungsseite liegt unter
<https://xindaan.github.io/streulicht/web/bewerten-berlin.html>, `seiten_basis`
ist gesetzt, der Live-Abruf wurde gegen die lokale Datei verglichen: identisch.

Die **Produktseite** bleibt bewusst draussen - Bauartefakt (0.3 MB,
gitignoriert) und Verankerungsrisiko: sie zeigt die Prognose, die die
Bewertungsseite verbirgt.

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

**Nachtrag 15.08. (Befunde 35 und 36):** Auch die Wegdaten sind durch.  Die
Wolkenmaske bestaetigt an allen vier toten Abenden die Wolke auf dem
Lichtweg, im ganzen Album gibt es kein Phantom.  Die Wolkenoberkante sollte
danach die Hoehe klaeren und erwies sich als falsches Instrument: der Strahl
laeuft dort bei 0.00-1.54 km, also liegt fast jede Oberkante darueber, und
CTH sieht ohnehin nur die oberste Wolke - waehrend laut Modell die tiefe
Decke darunter blockiert.

**Damit ist der Term die einzige verbliebene Erklaerung (T-0029).**

**Nachtrag 15.08. spaet (Befund 37): auch der Term ist durch.**  Fuenf
Aggregationen des Wegs ueber alle 4058 Abende, beide Schirmzweige, gleiche
Alarmrate: kein Toeter-Abend erreicht eine Schwelle, Trefferquote im
Rauschen, Anreicherung unter dem Produkt am hoechsten.  An zwei der vier
Abende ist der Weg im Modell auch im Mittel zu 64-83 % dicht und vom
Satelliten bestaetigt; einer hat keinen Schirm im Modell; einer ist T-0018.
Kein Umbau.  `python3 skripte/wegterm.py`.

Entscheidung 14.08.: kein kommerzielles Kontingent, es dauert eben laenger.
Ebenfalls gestrichen: die Sichtbarkeitszeile im Alarm - Andre geht zur Not
vor die Tuer und braucht nur zu wissen, ob es gut wird.

## Next actions

1. **Beide Agenten wirklich nachladen** - `cp` allein reicht nicht, und
   `kickstart` auch nicht: es startet die ALTE, in launchd geladene
   Definition neu. Am 18.08.2026 lief der Alarm deshalb mittags ohne
   `--geplant` los.

       cp betrieb/de.greatbelow.streulicht.{alarm,seite}.plist ~/Library/LaunchAgents/
       for n in alarm seite; do
         launchctl bootout gui/$UID/de.greatbelow.streulicht.$n
         launchctl bootstrap gui/$UID ~/Library/LaunchAgents/de.greatbelow.streulicht.$n.plist
       done
       launchctl print gui/$UID/de.greatbelow.streulicht.alarm | grep -A4 arguments

   Die letzte Zeile ist die Gegenprobe: dort muss `--geplant` stehen.
2. **Den ersten sonnenuntergangsrelativen Lauf ansehen** (heute gegen 17:20
   Ortszeit): kommt er durch, verschwindet der Warnstreifen auf der Seite.
3. **T-0040** Ueberwachung der Exitcodes - zwei von vier Laeufen sind
   gescheitert, gemerkt hat es ein Mensch.
4. **T-0038** Rundung an der 80er-Schwelle, wenn der Fall wieder auftritt.

## Letzte Done

- **18.08.2026 Lauf ans Ereignis geruecht (T-0041).** Statt fest 07:30 jetzt
  rund drei Stunden vor Sonnenuntergang - halbiert den Modellvorlauf von
  21-24 h auf 12-17 h. Dahinter zwei Messungen: die Verfuegbarkeit der
  ECMWF-Laeufe (8,7 h nach Initialisierung) und das Kontingent (ein Lauf
  leert das Stundenbudget, das Tagesbudget traegt genau zwei).

- **17.08.2026 Stiller Ausfall behoben (T-0039).** Kein Netz am Morgen,
  vier Agenten tot, Seite zeigte den ganzen Tag den Vortag - und sah dabei
  frisch aus. Jetzt: `netz.py` wartet auf Namensaufloesung, `ausliefern.py`
  wiederholt den Push und nennt den git-Fehler, und die Seite schreibt ihr
  eigenes Alter hin, wenn die Zahlen nicht von heute sind.

- **16.08.2026 Desktopfassung (T-0037).** Prognoseseite und Bilanzseite
  schalten ab 1000 px auf einen breiten Satz um - eine Datei, ein
  Breakpoint. Achsenmarken stehen dafuer jetzt in Prozent statt in Pixeln;
  das war der einzige Eingriff in bestehenden Code.
- **16.08.2026 T-0036 beantwortet.** Der 07:30-Lauf schreibt `segmente`, und
  der Vertikalschnitt sieht damit nachweislich anders aus als mit der
  Ringnachrechnung. Der Zweig greift.

- **16.08.2026 UX-Overhaul komplett (T-0031 bis T-0034).** Neue
  Prognoseseite (Topbar, Hero mit `begruendung()`, Himmelsband, Zeitachse
  mit Zonen, Vertikalschnitt und Faecherkarte, Push-Auskunft), neue
  Bewertungsseite (Note 0 als echte Antwort, Prognose erst NACH der Abgabe),
  neue Bilanzseite `bisher.html`. Neue Module `faecher.py`, `band.py`,
  `bisher.py`; `schnitt_neu()` in `schnitt.py`.
- **16.08.2026 Echo-Pushs behoben.** Die Bewertungsquittung ging als Push an
  dasselbe Geraet zurueck, von dem sie kam - Andre ist auf das
  Bewertungstopic abonniert, weil die Abenderinnerung darueber laeuft. Sie
  geht jetzt mit Prioritaet 1 (min) raus: der Poller liest weiter, das
  Telefon schweigt. Ausserdem: der Alarm-Push hat ein Klickziel bekommen
  (er war eine Sackgasse), und die Erinnerung haengt `?a=2` an, wenn fuer
  den Abend ein Alarm rausging - der Anlass "alarm" konnte vorher gar nicht
  entstehen.

- Repo angelegt, `sonnen/geometrie.py` und `sonnen/feuchte.py` verifiziert.
- Sonnenuntergangszeiten gegen Open-Meteo unabhaengig bestaetigt (19:33 UTC
  im Juni — die E0-Korrektur haelt).
- Kalibrierung Eiszweig: Training 2023-24, Test 2025 ausgehalten.
- Klimatologie gerechnet, s* = 0.7065 (18.5 Ausloesungen/Jahr).
- Interpolation gemessen: Semi-Lagrange 42 % besser auf 300 hPa.
- Beide Score-Varianten implementiert und an Grenzfaellen geprueft.
- `docs/befunde-e1.md` mit allen Messungen und Pruefbefehlen.
- T-0010 Produktseite auf den Hausstandard portiert: Token-Datei, Zeitachse
  statt Balken, telefonfester Vertikalschnitt, alle Kontraste ueber AA.
- T-0027 Fensterterm gegen die Satellitenwahrheit: 158 Masken, kein Phantom
  im Album, Modellsaeule gegen Maske r bis +0.84 auf dem Weg (Befund 35).
- T-0028 Wolkenoberkante: falsches Instrument, Strahl bei 0-1.5 km, CTH
  sieht nur die oberste Wolke (Befund 36).
- T-0029 Wegterm anders aggregiert: fuenf Fassungen, 4058 Abende, kein
  Toeter-Abend gerettet, Betrieb bleibt beim Produkt (Befund 37).
