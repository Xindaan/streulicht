# TASK

Sonnenuntergangs-Alarm Berlin. Zwei bis zehn Tage im Voraus eine
Wahrscheinlichkeit fuer einen aussergewoehnlichen Sonnenuntergang melden.

Etappen: E0 Score-Design (fertig) · E1 Backfill und Kalibrierung (laeuft) ·
E2 Alarm · E3 Oberflaeche.

## Doing

### T-0001b Absichtssignal fuer den Abbruchtest
Der Presence-Only-Test scheiterte an einem konfundierten Label (siehe STATE).
Favoriten und Minutenabstand extrahieren, dann INNERHALB der Draussen-Abende
vergleichen statt gegen alle Abende.
- [ ] `skripte/fotos_detail.py` aus Terminal.app
- [ ] Test: Favoritenabende gegen Nicht-Favoritenabende, beide "draussen"

### T-0001 Fotoarchiv-Gate
Zaehlen, wie viele geotaggte Abendfotos (SU ±30 min) in der Mediathek liegen.
Entscheidet, ob der Presence-Only-Abbruchtest aus E0 existiert.
**BLOCKIERT:** macOS-TCC verweigert den Zugriff. Braucht Festplattenvollzugriff
fuer die Terminal-App in den Systemeinstellungen.
- [ ] n >= 40 komfortabel, n >= 20 grenzwertig, darunter faellt der Test aus
- Skript: `skripte/fotos_zaehlen.py`

### T-0006 Ablation 3-Schicht gegen niveauaufgeloest
**GERECHNET 14.08.2026, Antwort: NEIN (Befund 31).** rho = +0.697
[0.499, 0.826], Top-15-%-Ueberlappung 4 von 6, Verteilungen verschoben.
s\* muss bei einem Wechsel neu hergeleitet werden. **Sommerfenster am selben
Abend nachgeholt** (01.06.-12.07.2023, 8 Ereignisse): dort rho = +0.504 und
nur 1 von 6 Spitzenabenden gemeinsam. Mit s\* = 0.7065 loest die 3-Schicht
dreimal aus, die niveauaufgeloeste kein einziges Mal - ihr Maximum (0.488)
liegt unter der Schwelle. Fuer gleiche Rate braeuchte es dort s\* ~ 0.4224.
Historisch: `historical-forecast-api` war frei.
**Vorher war das Skript verzerrt** — es zaehlte Abende ohne Daten als 0.0,
wo BEIDE Verfahren uebereinstimmen, was rho nach oben trieb und damit genau
auf 'die Rangfolgen fallen zusammen' zeigte. Behoben, siehe Befunde 27b.
Load-bearing: s* kommt aus der 3-Schicht-Klimatologie, der Betrieb laeuft
niveauaufgeloest. Laufen die Rangfolgen auseinander, ist s* nicht uebertragbar.
- [ ] Spearman rho und Top-15-%-Ueberlappung ueber 42 Abende

### T-0003 Taegliche Ensemble-Archivierung
Das Ensemble-Archiv reicht nur 93 Tage zurueck und wandert. Ein Cron, der
nichts tut ausser den Tagesabzug wegschreiben. Haengt an keiner Entscheidung.
- [ ] ECMWF ENS, native 3-h-Schritte, Fanpunkte, taeglich nach dem 00z-Lauf

## Next

### T-0014 Score pro Member und Zwei-Pass-Advektion verdrahten
Die Score-Formeln stehen (`sonnen/score_niveaus.py`), es fehlt die
Betriebsschleife: pro Member rechnen (nie aus Mittelfeldern, Jensen), Felder
semi-Lagrangesch auf die Sonnenuntergangszeit advehieren.

### T-0007 Gelaende in den Fensterterm
DEM-Freigaengigkeit des Strahls. Ab freier Ortswahl zwingend, nicht optional
(Muenchen im Dezember: Alpen bei 250 km, Strahl bei 1,22 km).

### T-0008 Dispersion und Skill ueber Vorlauf
Rangdiagramm des Scores; Korrelation Ensemble-Median gegen Kurzfrist-Score
je Vorlaufstufe. BSS erst, wenn genug Archiv da ist (T-0003).

## Backlog

- T-0009 Eigene Bewertungsseite und ntfy-Rueckkanal (E2)
- T-0015 Seiten ausliefern. **ERLEDIGT 15.08.2026.** Repo oeffentlich,
  Pages ab `main` aus der Wurzel (GitHub erlaubt nur `/` oder `/docs`, nicht
  `/web`), `seiten_basis` gesetzt, Live-Abruf gegen die lokale Datei
  verglichen: identisch. Die Produktseite bleibt bewusst draussen -
  Bauartefakt und Verankerungsrisiko.
- T-0016 Horizontsilhouette aus DEM als zweites Bild neben dem Schnitt.
  Bewusst zurueckgestellt (T-0010, Entscheidung d): Schnitt und Silhouette
  beantworten verschiedene Fragen — der Schnitt zeigt WARUM (das Licht muss
  unter der Decke durch), die Silhouette WAS MAN SAEHE. Fuer Berlin
  ausserdem fast wirkungslos, das Gelaende nach Westen ist flach. Lohnt erst
  mit T-0007 (Gelaende im Fensterterm) und freier Ortswahl.
- T-0011 Aerosol als Partialkorrelation pruefen (CAMS, nur Vorlauf <= 5 d)
- T-0012 Kondensstreifen: RH_eis 100..130 % auf 250/200 hPa als Zusatzsignal
- T-0013 s\*-Portabilitaet ueber 3-5 Ankerorte pruefen (streut s\* < 15 %?)
- T-0017 Fensterterm-Umbau — **ERLEDIGT DURCH MESSUNG, nicht gebaut**
  (14.08.2026). Die harte Null trifft 0 von 70 Albumabenden und 17 % der
  uebrigen (Befunde 26). Der Term funktioniert; der notierte Umbau haette
  ihn verschlechtert.
- T-0018 Beleuchtete tiefe Decke als Ereignis statt als Hindernis. Genau ein
  Albumabend hat guten Schirm bei totem Fenster (2024-09-15, A 0.87,
  B 0.032). n = 1 — erst angehen, wenn ein zweiter Fall auftaucht.
- T-0020 **Quantilbruecke messen.** s\* = 0.7065 ist das 95. Perzentil der
  Klimatologie (IFS-Analysen, 0.5-Grad-Gitter). Der Betrieb rechnet auf
  ENS-Membern mit anderer Gitterweite und bildet p = Anteil ueber s\*.
  Ob dieselbe Schwelle dort dieselbe Rate ergibt, ist NIE gemessen worden -
  es gibt kein Ensemble-Archiv (T-0003 nie gestartet). Vorab nicht messbar:
  der Livegang IST die Messung. `archiviere.py` ab Tag 1, nach 6-8 Wochen
  s\*/p\* nachziehen.
- T-0021 **Bewertungsaufforderung an JEDEM Abend**, nicht nur bei Alarm.
  **GEBAUT** (`skripte/erinnerung.py`, launchd-Agent), im Betrieb noch
  nicht beobachtet — Nachtrag 15.08.2026 beim T-0029-Statuspass.
  Sonst entstehen nur Labels fuer Alarmabende - dieselbe Presence-only-Falle,
  die den ersten Abbruchtest unentscheidbar gemacht hat. Ohne Negative gibt
  es keine Trefferquote.
- T-0022 **Prognosestand je Lauf vollstaendig festschreiben.** **GEBAUT**
  (`alarm.py` haengt seit 15.08. den ganzen Stand an `verlauf`), im Betrieb
  noch nicht beobachtet. Urspruenglicher Befund: `alarm.py`
  haengt nur `p` an `verlauf`; Median, A, sicht, weg werden ueberschrieben.
  Nach der Saison laesst sich sonst nicht rekonstruieren, was am Alarmtag
  vorhergesagt war.
- T-0023 **Bewertungsverlust ausschliessen.** ntfy haelt rund 12 h vor, der
  Einsammel-Cron laeuft alle 3 h - steht das NAS still, fehlen Zeilen ohne
  Meldung. `localStorage` plus Nachsende-Knopf auf der Bewertungsseite.
- T-0024 **Aufloesungstest neu aufsetzen, wenn er wiederholt wird.** Zwei
  Gruende: die Baseline war 9 km, nicht 25 (Befund 32.1), und die 27 %
  Foto-Kontrollen sind ergebnisentscheidend - ohne sie +0.154
  [+0.028, +0.279], also Kriterium erfuellt. Post hoc, reicht aber, um
  "Aufloesung ist als Erklaerung gefallen" NICHT zu behaupten.
- T-0025 **Modellsprung gegen Variantensprung.** Aus denselben Ablationsdaten:
  Klimatologie-3-Schicht gegen GFS-3-Schicht (gleiche Score-Variante, anderes
  Modell) ergibt rho 0.483 - mindestens so gross wie der Variantensprung, den
  T-0006 gemessen hat. Der Betrieb macht genau diesen Modellsprung
  (Klimatologie auf IFS-Analysen, Alarm auf ENS). "Laeuft auf der richtigen
  Variante" beruhigt also zu Unrecht.
- T-0026 **`member_liste()` liefert 50 statt 51.** Der Kontrolllauf hat keinen
  `_memberNN`-Suffix und faellt still heraus. Kein Fehler im Ergebnis, aber
  eine stille Abweichung zwischen erwarteter und tatsaechlicher Memberzahl.
- T-0028 Wolkenoberkante — **GERECHNET 15.08.2026, Antwort: falsches
  Instrument** (Befund 36). 48 Toeter-Segmente, 0 mit Oberkante unter dem
  Strahl. Das entlastet den Term aber NICHT: der Strahl laeuft dort bei
  0.00-1.54 km, also liegt fast jede Oberkante darueber - der Test kann
  kaum ablehnen. Und CTH sieht nur die OBERSTE Wolke; blockiert wird laut
  Modell die tiefe Decke darunter (47 von 48 Segmenten fragen `low` ab).
  Belegt hat der Lauf trotzdem, dass die Schichtzuordnung des Scores
  richtig ist, und zwei Fehler im eigenen GRIB2-Leser aufgedeckt.
- T-0029 Wegterm anders aggregieren — **GERECHNET 15.08.2026, Antwort:
  traegt nicht** (Befund 37, `skripte/wegterm.py`). Fuenf Fassungen des
  Beleuchtungswegs (Produkt = Betrieb, Wurzel, Mittel, Maximum, ohne
  Tangentensegment) ueber alle 4058 Abende, beide Schirmzweige, je Fassung
  eigene Schwelle bei 18/Jahr. Kein Toeter-Abend erreicht unter irgendeiner
  Fassung die Schwelle (bestes S 0.37 gegen 0.79); Trefferquote im Album
  13-16 von 79, Unterschiede im Rauschen (bestes Paar +4/-1, p 0.375);
  Anreicherung unter Produkt am hoechsten (z +5.71); tote Fenster
  Album/Referenz 3/14 schrumpfen beim Weichmachen auf 1/5, das Verhaeltnis
  bleibt. **Damit sind alle drei Erklaerungen aus Befund 35 durch** (Wegdaten
  35, Hoehe 36, Term 37). Rest heterogen: 2023-04-24 kein Schirm im Modell,
  2024-09-15 = T-0018, 2018-07-09 und 2024-05-03 Weg auch im Mittel zu
  64-83 % dicht und satellitenbestaetigt. Hook `weg_agg` in `score()`
  bleibt, Default bitgenau (4058/4058). Betrieb unveraendert.
- T-0035 **Zweite Bewertungsquelle fuer die Bilanzseite.** `bisher.html`
  zeigt heute nur die eigenen Noten. Trefferquote und Alarmrate brauchen
  ausserdem die Alarme (`zustand["alarme"]`) und eine Schwelle, gegen die
  gemessen wird — beides erst nach sechs bis acht Wochen Betrieb sinnvoll
  (Quantilbruecke, T-0020). Bis dahin sagt die Seite ausdruecklich, dass die
  Alarmrate unbekannt ist.
- T-0038 **Rundung an der Schwelle.** Ein Abend mit p = 0,798 zeigt auf der
  Achse die Rangzahl "80." und liegt sichtbar an der gestrichelten Linie
  "AUFFAELLIG 80." - der Hero sagt trotzdem "unauffaellig", denn 0,798 < 0,80.
  Beides stimmt, zusammen liest es sich wie ein Widerspruch. Auf dem Telefon
  fiel es nicht auf, weil dort keine Rangzahl steht; mit der Desktopfassung
  steht sie da. Moeglichkeiten: abrunden statt kaufmaennisch runden (79.),
  eine Nachkommastelle nahe der Schwelle, oder die Stufenfarbe auf die
  Rangzahl legen. Keine ist offensichtlich - erst ansehen, wie oft der Fall
  eintritt.
- T-0040 **Der Betrieb meldet seinen eigenen Ausfall nicht.** Am 17.08.2026
  sind vier Agenten am fehlenden Netz gestorben, jeder mit Exitcode 1 - und
  aufgefallen ist es erst, weil Andre auf die Seite geschaut hat. `launchctl
  list` fuehrt den Code, niemand liest ihn. Denkbar: ein sechster Agent, der
  einmal taeglich die Exitcodes und das Alter von `daten/zustand.json`
  prueft und bei Auffaelligkeit EINEN Push schickt. Vorsicht bei der
  Schwelle - eine Ueberwachung, die zu oft piept, wird stummgeschaltet und
  ist dann schlechter als keine.
- T-0030 **Wolkentyp oder -unterkante als richtiges Instrument.** Was
  T-0028 gebraucht haette: ein Produkt, das low/mid/high trennt oder die
  Unterkante liefert. Kandidaten aus dem Data Store: `EO:EUM:DAT:0617`
  (Optimal Cloud Analysis, MSG, Klimadatensatz) und die MTG-Nachfolger
  `EO:EUM:DAT:0684` / `EO:EUM:DAT:0681`. Erst pruefen, ob eines davon eine
  Unterkante oder Schichtzuordnung fuehrt - sonst bleibt die Frage offen.
  Nach T-0029 die letzte offene Spur fuer 2018-07-09 und 2024-05-03 (die
  vertikale Struktur unter der Oberkante) — aber n = 2, und beide sind
  satellitenbestaetigt dicht. Nur angehen, wenn das Produkt billig zu
  pruefen ist; sonst zaehlt "nicht vorhersagbar mit diesem Ansatz".

- T-0019 MSG/MTG-Infrarot als Beobachtungswahrheit — **GEBAUT 15.08.2026**
  (Befund 34). Zugang, GRIB2-Leser und Faecherabtastung stehen;
  `python3 skripte/satellit.py`. Die Anwendung auf alle Albumabende ist mit
  T-0027 erledigt (158 Masken in `daten/satellit/`). (3 km, 15 min, kostenlos).
  Beantwortet fuer jeden Albumabend, ob die Wolke ueberhaupt da war — die
  Frage, die am 14.08. fuenfmal von Hand am Foto beantwortet wurde.

## Done

### 17.08.2026 &mdash; Der Morgen ohne Netz (T-0039)
- T-0039 **Stiller Ausfall der Auslieferung behoben.** Der Mac hatte von
  07:30 bis nach 08:15 keine Namensaufloesung. `alarm.py`, `archiviere.py`,
  `bewertungen_holen.py` und der `git push` aus `ausliefern.py` sind alle
  vier daran gestorben, jeder **genau einmal, ohne Wiederholung** - und die
  ausgelieferte Seite zeigte den ganzen Tag den Vortag, ohne dass irgendwo
  etwas rot geworden waere. Drei Aenderungen:
  1. `skripte/netz.py` (neu): die netzabhaengigen Skripte warten bis zu
     20 Minuten auf Namensaufloesung, statt am ersten Fehlversuch zu
     sterben. launchd hilft hier nicht - es holt VERPASSTE Laeufe nach,
     aber ein gestarteter und fehlgeschlagener Lauf gilt als erledigt.
  2. `ausliefern.py` wiederholt den Push dreimal und **nennt den
     git-Fehler**. Vorher meldete die Ausnahme nur "exit status 128" und
     warf genau die Zeile weg, die erklaert warum; die Ursache liess sich
     nur aus den Logs der drei anderen Agenten rekonstruieren.
  3. Die Seite sagt ihr eigenes Alter: steht der neueste `lauf` im Zustand
     nicht auf heute, erscheint ein Streifen unter der Kopfleiste
     ("Diese Zahlen sind vom 16.08. (gestern)."). Ohne ihn sah eine Seite
     mit Vortagsdaten genauso aus wie eine frische - **das** war der teure
     Teil, nicht der ausgefallene Lauf.
  Ausserdem: `de.greatbelow.streulicht.seite` laeuft jetzt 08:10 **und**
  12:10, fuer den Fall, dass der Alarm laenger gebraucht hat als bis 08:10.
  Nachgeladen am 17.08.2026; der Kickstart-Lauf um 13:20 hat gepusht und
  damit belegt, dass der Push aus dem launchd-Kontext funktioniert - die
  Stoerung um 08:15 war das Netz, kein Zugriffsproblem.
  **Nachgetragene Messung zum Kontingent:** die Zahlen von heute liessen
  sich nicht nachholen. Drei Versuche (12:25, 13:03, 14:15), der dritte
  meldete "Daily API request limit exceeded". Ein Alarmlauf wiegt schwer
  (51 Member x 88 Schritte x 9 Variablen ueber ~210 Zellen); es sind zwei
  bis drei pro Tag drin, nicht mehr. Beim Nachholen also EINEN Versuch,
  nicht drei - sonst ist das Budget fuer den naechsten Morgen mit
  verbrannt. Steht in der README unter Troubleshooting.


### 16.08.2026 &mdash; Desktopfassung (T-0037) und T-0036
- T-0037 **Desktopfassung der Prognoseseite** nach
  `docs/entwurf/handoff-desktop-2026-08-16.md`. Umgesetzt als **eine Datei
  mit Breakpoint** (Variante (a) des Handoffs, ab 1000 px), nicht als zweite
  Seite: eine URL, ein Lauf, und die Datenaufbereitung war ohnehin identisch.
  Fuenf Aenderungen, alle rein raeumlich - kein Bauteil, keine Zahl, kein
  Satz kommt hinzu: Himmelsband als 400-px-Kopf mit zwei Schleiern und dem
  Hero darauf; die drei Zahlen als beschriftete Kennzahlen statt Punktkette;
  Achse 260 px mit Rangzahl je Marke; Schnitt und Faecherkarte nebeneinander
  (`repeat(auto-fit,minmax(420px,1fr))`); Korpuszeile und Bilanzverweis in
  die Kopfleiste.
  **Der einzige Umbau an bestehendem Code**, wie vom Handoff angekuendigt:
  die Marken stehen jetzt in PROZENT statt in Pixeln. Nebengewinn - die
  Zonen ebenfalls (5 % und 15 % sind bei 200 px genau 10/30, bei 260 px
  genau 13/39, also beide Entwuerfe ohne zweite Pflegestelle).
  Zwei Tokens neu: `--breite-gross` (1240) und `--rand-gross` (40).
  `bisher.html` hat denselben Breakpoint bekommen (Kopfleiste im
  1240er-Container, 720er Lesespalte) - nicht im Handoff, aber sie haette
  sonst neben der neuen Prognoseseite wie ein Telefon-Bildschirmfoto
  ausgesehen. Die Bewertungsseite bleibt bewusst auf 390 px: sie wird aus
  dem Push heraus auf dem Telefon geoeffnet.
- T-0036 **Segmenttransmission greift** (erledigt 16.08.2026). Der
  07:30-Lauf hat `segmente` geschrieben (10 von 11 Abenden), und die
  Gegenprobe zeigt: mit echten Segmenten faellt das Bild anders aus als mit
  der Ringnachrechnung aus dem Medianfeld. Der Zweig ist also nicht nur
  vorhanden, sondern wirksam.


### 16.08.2026 — UX-Overhaul (T-0031 bis T-0034)
- T-0031 **UX-Overhaul umgesetzt** (16.08.2026, Handoff
  `docs/entwurf/handoff-ux-2026-08-16.md`). Alle sieben Punkte der
  Umsetzungsreihenfolge:
  Tokens (`--himmel-oben/-unten`, `--band-dumpf/-glut`) ·
  `skripte/schnitt.py` bekommt `schnitt_neu()` mit Polygonbaendern,
  doppeltem Strahl, Sonnenhalo, Horizontwaesche und Himmelsverlauf auf
  420x258 — die alte `svg()` bleibt unveraendert fuer `diagnose.html` und
  `rueckschau.html` ·
  `skripte/faecher.py` (neu, Draufsicht) · `skripte/band.py` (neu,
  Himmelsband) · `skripte/seite.py` neu aufgebaut (Topbar, Korpuszeile,
  Hero mit `begruendung()`, Himmelsband, Zeitachse mit Zonen und
  Verlaufslinie, zwei Grafikkarten, Fusstext, Push-Auskunft) ·
  `web/bewerten.html` mit Note `null`/0/1-5 und Freilegung nach der Abgabe ·
  `skripte/bisher.py` (neu) statt `rueckschau.py` — siehe T-0035 ·
  `skripte/ausliefern.py` mit erweiterter Liste.
  Zwei Abweichungen vom Entwurf, beide begruendet: Vorauswahl (T-0033) und
  Anfangszustand serverseitig statt per Skript (die Seite war ohne
  JavaScript leer).
- T-0032 **Push-Auskunft auf der Prognoseseite** — erledigt mit T-0031. Sagt
  jetzt beide Faelle: "Kein Abend im Fenster reisst die Schwelle von 50 %
  (hoechstens 12 %). Es kommt kein Push." bzw. den Alarmfall mit Uhrzeit.
- T-0033 **Vorauswahl: entschieden fuer den naechsten Abend** (16.08.2026).
  Andres Meldung wiegt schwerer als der Entwurf: wer die Seite aufmacht,
  fragt zuerst "wie wird es heute abend". Vom Entwurf uebernommen ist sein
  Eyebrow-Text - faellt die Vorauswahl auf den besten Abend im Fenster,
  sagt die Seite "Bester Abend im Fenster" statt "Gewaehlter Abend".
- T-0034 **Handoff-Punkt 7 ueberholt, nicht zurueckgedreht.** Die
  Prognoseseite bleibt ausgeliefert; `ausliefern.py` fuehrt sie weiter in
  der Liste, dazu neu `bisher.html`.


- **T-0027 Fensterterm gegen die Satellitenwahrheit** (15.08.2026, Befund 35)
  — `skripte/fensterterm.py`: der Fensterterm dreimal mit derselben Formel
  (Nachbildung bitgenau gegen `score.py` geprueft): Modell, Hybrid (Hoehen
  vom Modell, Anwesenheit je Faecherzelle vom Satelliten gedeckelt), reine
  Maske. 79 Albumabende plus 79 saisongleiche Referenzabende, 158 MSG-Masken.
  **Ergebnis:** kein Albumabend, den eine Phantomwolke auf dem Weg gekillt
  haette (0 von 3 toten Fenstern, 1 von 14 bei lockerer Schwelle); die vier
  Toeter-Abende aus Befund 34 sind saeulenbestaetigt (88-100 %). Modellsaeule
  gegen Maske je Ring r = +0.61 (Berlin) bis +0.84 (420 km), kein Bias.
  Deckelhebung im Album nicht groesser als in der Referenz. **Verworfen: die
  Wegdaten als Erklaerung. Offen: Term oder Hoehenzuordnung** - trennt erst
  T-0028; Termumbau als T-0029 notiert.

- **T-0010 Produktseite auf den Hausstandard** (14.08.2026) — Portierung
  von Andres Designsprache aus `poisson-dor` und `rezept-grid`, Werte und
  Herleitung in `docs/ui-referenz.md`. Neu: `stil/tokens.css` als einzige
  Farb- und Massquelle, von `skripte/tokens.py` gelesen und von `seite.py`
  in die Seite inlined; `schnitt.py` enthaelt danach keine feste Farbe mehr
  (nur noch `#000`/`#fff` als Maskenwerte, also Deckkraft 0 und 1).
  **Gewaehlt:** (a) nur Dunkel, Apple-Neutrale statt GitHub-Blaugrau;
  (b) eine Akzentfamilie mit drei Zustaenden — selten gefuellt, auffaellig
  offen, unauffaellig farblos — statt der Ampel Orange/Gold/Grau;
  (c) Zeitachse mit Schwellenlinien bei 80. und 95. statt Kachelstreifen;
  (d) Vertikalschnitt behalten, aber telefonfeste Fassung (viewBox 420x300,
  Grad 15, Diagnosezahlen raus); (e) deutsche Tokennamen.
  **NACHTRAG 14.08.2026 abends:** die Behauptung "alle Kontraste ueber AA"
  war falsch. Die zwei Schwellenlinien im Zeitstreifen tragen Information
  (80. und 95. Perzentil) und standen mit `--gitter` bei 2.84:1 auf
  `--karte`; WCAG 1.4.11 verlangt 3.0. Der Tokenkommentar bescheinigte
  3.51:1 - gemessen gegen `--papier`, nicht gegen die Flaeche, auf der die
  Linien liegen. `--gitter` ist auf `#8e8e93` angehoben (6.44:1 auf Papier,
  5.22:1 auf Karte), der alte Wert bleibt als `--gitter-schwach` fuer rein
  Dekoratives. Gefunden beim Uebertragen derselben Pruefung auf eine neue
  Seite - nicht beim Bau der Produktseite selbst.
  Dazu 44-px-Tastflaechen (ueber dem Hausstandard von 34-40),
  `prefers-reduced-motion`-Guard (den `rezept-grid` nicht hat) und neutrale
  statt blauer Wolkenbaender.
  **Verworfen:** 3D-Ortsmodell — in der Zweitreferenz Mapbox GL, also
  Fremddienst mit Token, und beim Ansehen selbst mit HTTP 403 ausgefallen;
  eigene Webfonts — der Hausstandard nutzt den Systemstack plus
  `tabular-nums`; Hellmodus — waere kein Token-Tausch, sondern ein eigener
  Entwurf fuer Wolkenbaender und Strahl.
  **Gemessen vorher/nachher:** Fusstext-Kontrast 2,28:1 -> 7,31:1 (AA
  verlangt 4,5); Schriftgrade im Bild auf dem Telefon 3,5-4,3 px -> 11,3 px;
  Tastflaechen 44 px auf 375 px Breite, 63 px am Desktop; kein horizontales
  Ueberlaufen in beiden Breiten. Der alte Balken war als Fuellstand von null
  gezeichnet, obwohl die Perzentile ueber zehn Abende zwischen 0,592 und
  0,971 lagen — die unteren 59 % waren tote Flaeche, und ein Score von 0,072
  zeigte einen zu 59 % gefuellten Balken.
  **Nebenbefund, behoben:** HTML-Entities in Zeichenketten, die durch JSON
  in `textContent` laufen, erscheinen woertlich. Betraf `stufe()` (sofort
  sichtbar) und `MONAT` mit "Maerz" (waere erst im Maerz aufgefallen).
- **T-0000 E0 Score-Design** (14.08.2026) — Zweiterm-Score multiplikativ,
  entfernungsabhaengige Niveauzuordnung, semi-Lagrangesche Interpolation,
  Validierungsplan. Korrekturen: Juni-Sonnenuntergang 19:33 statt 17:30 UTC;
  Fensterband 200-400 km statt 100-200 km.
- **T-0002 Klimatologie und Schwellwert** (14.08.2026) — dem Archiv (ecmwf_ifs) 2022-2025,
  1461 Abende, 3-Schicht auf 0.5-Grad-Gitter. **s\* = 0.7065 → 18.5
  Ausloesungen/Jahr.** Januar null von 124. r(A,B) = -0.259. Offen bleibt die
  Quantilbruecke auf ECMWF (haengt an T-0006).
- **T-0004 Score implementiert** (14.08.2026) — 3-Schicht (`sonnen/score.py`)
  und niveauaufgeloest (`sonnen/score_niveaus.py`), beide gegen synthetische
  Grenzfaelle geprueft. Dickenstrafe wirkt (dickes Deck 400-250 hPa auf 0.53).
- **T-0005 Interpolation** (14.08.2026) — Semi-Lagrange senkt RMSE auf
  300 hPa um **42 %** (r 0.667 -> 0.904), auf 850 hPa um 16 %. Zwei-Pass-
  Verfahren aus E0 dabei mitvalidiert.
- **T-0001 Fotogate** (14.08.2026) — Mediathek liefert 1199 Abende, 701
  Berlin. Abbruchtest gelaufen, Ergebnis unentschieden wegen konfundiertem
  Label; Aufloesung ueber T-0001b.
- **E2 gebaut** (14.08.2026) — Alarmlauf mit Zwei-Pass-Advektion, ntfy-Push,
  blinde Bewertungsseite, Rueckkanal, Idempotenz, README, Cron-Vorlage.
  Pass 1 verifiziert (75 Zellen, 50 Member, 88 native Schritte); ein
  vollstaendiger Lauf steht aus.
- **Gates E1** (14.08.2026) — Modellverifikation, Wolkendiagnostik kalibriert,
  Geometrie gegen unabhaengige Quelle geprueft. Siehe `docs/befunde-e1.md`.
