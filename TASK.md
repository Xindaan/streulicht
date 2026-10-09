# TASK

Sonnenuntergangs-Alarm Berlin. Zwei bis zehn Tage im Voraus eine
Wahrscheinlichkeit fuer einen aussergewoehnlichen Sonnenuntergang melden.

Etappen: E0 Score-Design (fertig) · E1 Backfill und Kalibrierung (laeuft) ·
E2 Alarm · E3 Oberflaeche.

## Doing

### T-0072 WeatherNext 3 anbinden - ENTSCHIEDEN 08.09.2026
Zuschnitt (a): die Faecherextraktion laeuft in us-east1, der Mac liest nur
eine kleine JSON-Datei. `ecmwf_ifs025` bleibt Rueckfall - er ist genau ein
Konfigwert entfernt. Messwerte, Kostenrechnung und die verworfenen Wege
stehen im Backlog-Block T-0072.
- [x] Zeitzuordnung `lead_subtime` = [-5..0] relativ zum Blockende, gegen
      das `datetime`-Array gegengeprueft (nicht geraten)
- [x] `skripte/wn3.py` - Leser mit austauschbarem Speicher
- [x] `skripte/test_wn3.py` - 18 Pruefungen, 5 Negativproben, alle gruen
- [x] Gegen echte Daten gefahren: Lauf 20260908_00hr, drei Schichten,
      stuendliche Zeitachse, plausible Werte
- [x] **Kostenriegel** (08.09.2026, auf Ansage "keine Kostenrisiken"):
      `in_region()` fragt den GCE-Metadatendienst - ein Nachweis, keine
      Annahme. Ausserhalb us-east1 gilt eine harte Grenze von 500 MB je
      Prozess, bewusst hebbar mit `--budget-mb`. Gebucht wird VOR der
      Uebertragung aus der in den Metadaten bekannten Chunkgroesse; die
      erste Fassung buchte danach und hatte bei Grenze 1 MB schon
      148 MB bezahlt, als sie anschlug.
- [x] **Reihenfolge gedreht (08.09.2026, auf Ansage "keine Kostenrisiken"):
      erst kostenlos messen, dann ueber Infrastruktur entscheiden.**
      `Statistik` in `skripte/wn3.py` liest das NICHT requester-pays
      Bucket - Mittel und fuenf Perzentile, 0,1 Grad, stuendlich, von
      hier aus gratis. Kein p (Perzentile je Gitterpunkt geben keinen
      kohaerenten Member her) und keine Druckflaechen, also kein
      Alarmbetrieb - aber genug fuer die Vorfrage, ob WN3 unsere Abende
      ueberhaupt besser trifft als ECMWF.
- [x] **Kreuzvalidierung der beiden Leser gegeneinander** (10.09., 16Z,
      Berlin): Ensemble-Member 0 meldet mid 86,8 %, die unabhaengig
      gerechnete Statistik p50 = 53,1 und p90 = 99,4. Der Member sitzt
      zwischen Median und p90 - zwei getrennte Leser auf zwei getrennten
      Produkten stimmen ueberein.
- [x] **Vergleich gerechnet, 08.09.2026** (`skripte/wn3_vergleich.py`,
      818 MB kostenlos, 5 min). Elf Abende mit Note UND Archiv, gleicher
      Score, gleicher Faecher, WN3-Lauf jeweils so gewaehlt, wie er zum
      Abrufzeitpunkt verfuegbar gewesen waere.

      | Ergebnis | Wert |
      |---|---|
      | Korrelation der Scorereihen | **r = 0,868** |
      | WN3 hoeher als ECMWF | **8 von 11 Abenden** |
      | mittlere Abweichung | **+0,135**, groesste +0,620 |
      | ECMWF reisst s* = 0,7065 | **0 von 11** |
      | WN3 reisst s* | **3 von 11**, bei Noten 1, 4 und **0** |

      **Deutung.** Die beiden Modelle ordnen die Abende aehnlich (r hoch),
      aber WN3 liegt systematisch HOEHER. Ein Modellwechsel ohne neue
      Schwelle wuerde aus null Ausloesungen drei in elf Abenden machen -
      eine davon an einem Abend mit Note 0. Das ist kein Argument gegen
      WN3, sondern die Bestaetigung dessen, was `konfig.json` ohnehin
      festhaelt: **s* ist modellspezifisch und waere neu zu bestimmen.**

      **NICHT beantwortet ist, welches Modell besser trifft.** 14 Noten,
      davon eine gute - das traegt keine Aussage. Wer aus dieser Tabelle
      "WN3 ist besser" liest, liest Rauschen.

- [ ] **Neuer Blocker, groesser als die Kosten: s* laesst sich fuer WN3
      nicht so bestimmen wie fuer ECMWF.** s* = 0,7065 kommt aus vier
      Jahren und 74 Ereignissen; das Album reicht von 2014 bis 2022. WN3s
      Archiv beginnt am 01.01.2026 - diese Abende sind fuer WN3
      unerreichbar. Ausweg waere die Quantilabbildung, die Befund E1 schon
      fuer GFS->ECMWF vorgesehen hat, ueber eine Ueberlappungsperiode.
      Das ist zu klaeren, BEVOR ueber eine Instanz geredet wird.
- [ ] Ab sofort je Lauf das WN3-Medianfeld mitschreiben (kostenlos), damit
      die Ueberlappung waechst statt zu warten. Dieselbe Lehre wie in
      Befund E1: "jeder Tag Wartezeit ist ein verlorener Kalibrierungstag".
- [ ] Betriebsvehikel - nur falls der Vergleich dafuer spricht: e2-micro
      (Freikontingent nach Instanzstunden, langsam) gegen Cloud Run Job
      (schnell, Freikontingent knapp). Compute Engine ist in
      `gardena-wetter` noch gar nicht aktiviert, die freie e2-micro also
      unangetastet.
- [ ] Uebergabe: kleines Bucket in `gardena-wetter`, Mac zieht die JSON
- [ ] `alarm.py`: zweiter Weg neben `abfrage()`, gesteuert ueber `modell`
- [ ] Zeitbudget echt messen statt hochrechnen (meine 1,5-2,5 h je Lauf
      sind eine Schaetzung vom Mac aus, keine Messung auf der Instanz)

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
Load-bearing: s\* UND der Betrieb laufen beide auf der 3-Schicht-Variante
(`alarm.py` importiert `sonnen.score`, siehe Modulkopf dort). Hier stand bis
zum 23.08.2026 "der Betrieb laeuft niveauaufgeloest" - das war falsch und hat
die Dringlichkeit dieses Tasks ueberzeichnet. Richtig ist: die Rangfolgen
entscheiden, ob s\* beim geplanten WECHSEL uebertragbar waere, nicht ob der
laufende Betrieb einen falschen Schwellwert benutzt.

**VERMERK 23.08.2026 zur Lueckenbehandlung (Entscheidung: NICHT neu
rechnen).** Die Zahlen oben sind unter ASYMMETRISCHER Lueckenbehandlung
entstanden: `ablation.py:173` verwarf schon immer Abende, bei denen eine der
beiden Varianten `detail is None` lieferte - aber `score_niveaus` gab bei
einer TEILluecke (Daten nur im Nahbereich) noch ein Detail zurueck, wo
`score` verwarf. Solche Abende blieben also in der Stichprobe, mit einem
ueberhoehten Niveaus-Wert. Seit T-0054 verwerfen beide gleich.

Wie viele Abende das in den ERA5-Daten 2022-2025 betrifft, ist **nicht
gemessen** - der historische Abruf kostet Kontingent. Nicht neu gerechnet,
weil die Richtung des Fehlers gegen die Antwort spricht, nicht fuer sie: ein
ueberhoehter Niveaus-Wert bei Teilluecken konnte zufaellig mit der
3-Schicht-Variante uebereinstimmen und rho damit nach OBEN ziehen. Das
gemessene rho ist also eher eine Obergrenze, und mit +0.697 bzw. +0.504 im
Sommerfenster liegt schon die Obergrenze weit unter jeder Wechselschwelle.
Die Antwort "NEIN" wird durch den Fix fester, nicht wackliger.

Wer den Wechsel doch ernsthaft erwaegt, rechnet vorher neu - dann aber mit
der heutigen Fassung beider Scorer, und der Vermerk hier faellt weg.
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

### T-0074 Abruf inkrementell und gedeckelt (Kontingent) - aus Review 09.10.2026
Seit 16.09. gelangen 18 von 76 Fensterlaeufen; an 13 von 38 Abenden seit 01.09.
fehlt der Abendlauf. Ein 429 (Stunde/Tag) verwirft alles Geholte, jeder
stuendliche Nachhol-Tick zahlt Pass 1 und Pass 2 erneut. Der Lauf wuchs von 217
auf 378-383 Ortsabrufe, getrieben vom saisonalen Abstand Sonnenuntergang zu
Modellschritt (Spitze Anfang Oktober, wieder Maerz/Juni), Pass 2 ohne Deckel.
Befunde alarm#1, #2, #3, #4, #10, #12, tests#6 in `docs/review-2026-10-09.md`.
- Blockcache je Modelllauf/Variablen/Zellen: ein Retry holt nur Fehlendes.
- Nach "Hourly" Sperrvermerk bis zur vollen Stunde, nach "Daily" bis 00 UTC,
  im Zustand; Ticks davor beenden sich ohne Abruf.
- Obergrenze fuer Pass 2 mit lauter Logzeile; Kostenzahlen in README, STATE
  (Abschnitt Kontingent, "Memberzahl multipliziert NICHT") und alarm.py auf die
  Messung bringen.
- Akzeptanz: Verhaltenstest "429 mitten in Pass 2, Folge-Tick holt nur die
  fehlenden Bloecke", mit Negativprobe je Waechter.
- Stand 09.10.2026: umgesetzt - Blockcache je Modelllauf
  (`daten/cache/abruf/`), Kontingentsperre im Zustand (`_kontingent`),
  Pass-2-Deckel `pass2_max_zellen` = 320, eigenes Wartebudget fuer
  Minutenlimit/concurrent; Test `skripte/test_kontingent.py` mit 18
  Negativproben (Commit c493481).
- Stand 09.10.2026: umgesetzt - Gate-Nachbesserung: Cacheschluessel traegt
  jetzt auch den UTC-Abruftag (`daten/cache/abruf/<Modelllauf>/<JJJJMMTT>/`),
  weil Open-Meteo die Zeitachse ohne Startdatum am Abruftag beginnt; derselbe
  Modelllauf nach Mitternacht UTC haette sonst den Windblock vom Vortag
  bekommen. Test h) in `test_kontingent.py` (Folgecommit zu c493481).
- OFFEN: STATE.md (Abschnitt Kontingent) sagt noch "Die Memberzahl
  multipliziert NICHT" - widerspricht README/alarm.py und dem Log (alarm#3);
  STATE war in diesem Schritt ausgenommen, Satz beim naechsten STATE-Pass
  korrigieren. Der Done-Block "Kontingent vollstaendig vermessen" ("210.000
  im Monat - es passt") beruht auf 216 Ortsabrufen; er bleibt als
  Zeitdokument stehen, gueltig ist README "Was die Grenze kostet". Die
  Gewichtung selbst bleibt ungemessen (alarm#4).

### T-0075 Ausfall sichtbar machen (ergaenzt T-0040) - aus Review 09.10.2026
Kein Melder; `last exit code` wird vom naechsten Leerlauf-Tick mit 0
ueberschrieben; ein Waechter auf dem Mac faellt mit dem Mac aus. Der
Altersstreifen entsteht nur beim Bauen - Mac ganz aus heisst alte Seite ohne
Warnung. Befunde alarm#5, #6, #8, seiten#1, betrieb#3, tests#10.
- Seite traegt den Abrufzeitpunkt maschinenlesbar, ein kleines Skript
  vergleicht ihn mit der Uhr der Betrachter:innen.
- Waechter AUSSERHALB des Macs (Mac-Ausfall ist die haeufigste Ursache).
- Ein Lauf ohne ein einziges Ergebnis darf nicht als Erfolg gebucht werden
  (alarm#8); die Nachtluecke nach zwei gescheiterten Laeufen entscheiden
  (alarm#6).
Stand 09.10.2026: umgesetzt - Lauf ohne Ergebnis wird nicht gebucht (Exit 1,
leere Bloecke nicht gecacht, Wind paarweise, Abend ohne Wind uebersprungen);
Seite traegt `streulicht-geholt` und prueft ihr Alter im Browser; Waechter
`.github/workflows/waechter.yml` auf GitHub (bb686b7). Offen: Secret
`NTFY_WAECHTER` (Andre), alarm#6 Nachtluecke nicht entschieden.

### T-0076 Commit-Rueckstand seit 26.08.2026 aufloesen - aus Review 09.10.2026
22 Dateien geaendert, 5 ungetrackt; die Plists in HEAD zeigen auf das nicht
mehr vorhandene `/usr/local/bin/python3`, es gibt keinen Rueckfallpunkt; das
oeffentliche Repo zeigt noch den Advektionsfehler. **Vor dem Push** die private
E-Mail-Adresse aus dem Messblock von T-0072 entfernen (wn3#F8). Entscheidung
Andre (oeffentliches Repo). Befunde betrieb#7, architektur#5, wn3#F8.

## Backlog

- T-0077 Bewertungskanal haerten (Review 09.10.2026). Das oeffentliche
  Bewertungs-Topic ist zugleich das abonnierte Erinnerungs-Topic: jede:r kann
  Pushs mit Titel, Text und Klickziel an Andres Telefon schicken (bewertung#3).
  Dazu: `plausibel()` nimmt auch 20260915 und 2026-W38-2 (bewertung#2); die
  Sonnentafel der Bewertungsseite liefert ausserhalb von +-4 Tagen still den
  letzten Tafeltag (bewertung#1, Randfall mit stillem Datenschaden); die als
  erledigt gemeldete Umbuchung aus T-0043 fehlt im Zustand (bewertung#4);
  Quittung nach stillem Nachsenden (bewertung#6).
- T-0078 Methodik-Paket (Review 09.10.2026, Befunde methodik#F1-F13,
  physik#4, physik#13). Die Seite ordnet den Member-MEDIAN in die Verteilung
  einzelner Analysen ein - "auffaellig"/"selten" treffen der Median nur in 10 %
  bzw. 0,3 % (F3). Album-Trefferquote gilt fuer S >= 0,630, nicht s* (F4).
  T-0006 verglich zwei verschieden gewichtete Scores; neu gerechnet: Sommer
  rho 0,690 statt 0,504, Kernaussage NEIN haelt (physik#13). Sichtfaktor
  gewichtet den Standort 1/6, Term A 75-89 % (physik#4). WN3-Blocker-Begruendung
  falsch: das Album reicht bis 2026 (F8). Beide Alarme kamen erst bei Lead 0
  (F11). Noten bisher ohne Zusammenhang, Abgabe selektiv (F9, F10). Datum des
  Advektionsfixes in README/alarm.py: 04.09., nicht 02.09. (F6).
- T-0079 Testluecken (Review 09.10.2026): ausliefern.py ungetestet
  (Allow-Liste, Zweigriegel; tests#9); netz.warte_auf_netz (tests#8);
  bewertungen_holen.hole() und vier Eingangswaechter (bewertung#8, tests#7);
  Advektion nur mit Westwind (tests#1); test_ortsfilter jedes Jahr 10.05.-02.08.
  rot (tests#4); test_seiten haengt an der Wanduhr (tests#5); test_erinnerung
  liest die Produktiv-Konfig (bewertung#9); test_ortsfilter ersetzt
  `alarm.sende` nicht - pruefen, ob ein echter ntfy-POST moeglich ist;
  test_wn3 nicht netzfrei, 13 von 13 Verdrahtungsmutanten ueberleben (wn3#F7).
- T-0080 UI/UX-Paket (Review 09.10.2026): Bilanz ohne Nenner, ohne die beiden
  Alarmabende, ohne Laufalter (uiux#5, #6); Hero zeigt nach Sonnenuntergang den
  vergangenen Abend (uiux#2); Textwidersprueche ("18 im Jahr" gegen
  "unbekannt", "keine Prozentzahl" neben Prozent, "0 %" bei 0/51; uiux#4);
  Push-Text und fehlender Deep-Link (uiux#9, #10); Tippziele 31 px, Markenfarbe
  (uiux#13); Tastatur schluckt Cmd/Alt+Pfeil (uiux#12); SVG-Style ueberschreibt
  die Hervorhebung (seiten#8); Faecherkarte schneidet den Faecher ab (physik#5).
- T-0081 Betriebsrobustheit (Review 09.10.2026): die 27 Noten liegen nur in
  `daten/zustand.json`, Time-Machine-Netzziel seit 29.05.2026 ohne Sicherung
  (betrieb#6); Logs ohne Datum und ohne Rotation (architektur#14);
  erinnerung.py wartet nicht aufs Netz und endet bei Fehler mit 0 (bewertung#5);
  git push ohne Timeout (seiten#9); ein Absturz von seite.py stoppt auch
  Bewertungs- und Bilanzseite (seiten#4, architektur#6).
  Stand 09.10.2026: umgesetzt - 7690b2f. Logs mit Datum+Uhrzeit und Rotation
  (`skripte/logbuch.py`), erinnerung.py wartet aufs Netz und endet bei
  Versandfehler != 0, ausliefern.py baut jede Seite fuer sich und pusht mit
  Zeitgrenze, Tageskopie der Noten nach `daten/sicherung/` (`skripte/sicherung.py`).
  OFFEN bei Andre: `sicherung_ordner` in konfig.json setzen (z. B. iCloud).
- T-0082 Doku und Steuerdateien (Review 09.10.2026): STATE.md 335 Zeilen statt
  Kurzstand, Next actions doppelt nummeriert und ueberfaellig (architektur#2);
  Doing mit 5 statt 3 Eintraegen, T-0003/T-0001/T-0006 erledigt bzw.
  entschieden, T-0014 laengst gebaut (architektur#1); README-Drift: "Ein Cron",
  Henyey-Greenstein im Betriebsscore, `faecher` optional, "E3 offen",
  Mehrortliste (architektur#3, #4, #11, #16); Kommentare mit 3-h-Takt (#17).
- T-0083 WN3-Befunde aus dem Review 09.10.2026 (zu T-0072): Windfeld in m/s
  statt km/h (physik#1); Zielzeit per Gleichheit, echte Sonnenuntergaenge
  fallen durch (wn3#F4); der Zuschnitt (a) kennt die ~300 Pass-2-Zellen nicht
  (wn3#F6); Vergleich misst Medianfeld gegen eine Schwelle fuer Memberscores,
  ECMWF-Seite auf 0,5 Grad vergroebert (wn3#F1, #F2); r = 0,868 bei n = 11
  traegt "systematisch hoeher" nicht (wn3#F3); Testzahlen veraltet (wn3#F10).

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

- T-0072 WeatherNext 3 (erschienen 03.09.2026). Haelt die Modellentscheidung
  aus Befund 2 gegen: `ecmwf_ifs025` wurde **allein wegen C3** gewaehlt
  (3-h-Raster; WN2 nur 6 h). WN3 laeuft stuendlich, 64 Member, Wolken auf
  0.1 Grad, Druckflaechen auf 0.25 Grad, 15 Tage.

  **Zugang ist da** (Google-Freischaltung 14.08.2026, Andres Google-Konto;
  gcloud lokal angemeldet, Projekt `gardena-wetter`). Die Freischaltung deckt
  auch WN3, obwohl sie aelter ist als das Modell — geprueft 08.09.2026:
  anonym HTTP 401, mit Konto lesbar.

  **Alles Folgende gemessen am 08.09.2026, nicht aus der Doku:**

  | Groesse | Wert |
  |---|---|
  | Verzug Init -> Datei fertig | **6 h 33 min** (23z) / **7 h 05 min** (00z), gegen heute 9,3-22,3 h bei ECMWF |
  | Laufdichte | stuendlich, 6002 Laeufe zurueck bis 2026-01-01 |
  | `gs://weathernext3_spatial` | requester-pays, volles 64-Member-Ensemble |
  | Chunk `high_cloud_cover` | `[1 Member, 1 lead_time, 6 h, 1801, 3600]` = **116,2 MB** je Chunk, gemessen an `c/0/10/0/0/0` |
  | Chunk `u_component_of_wind` | `[1, 1, 1 Level, 721, 1440]` = **3,70 MB**, 13 Druckflaechen vorhanden |
  | `gs://weathernext3_statistics_spatial` | frei lesbar (kein requester-pays), Chunk **20,91 MB** je Stunde und Groesse |
  | Statistik-Variablen | nur `mean`,`p10`,`p25`,`p50`,`p75`,`p90`; `total/low/medium/high_cloud_cover` vorhanden, **keine Druckflaechen** |

  **Der Blocker ist die Chunk-Geometrie, nicht der Zugang.** Kein Chunk ist
  raeumlich unterteilt: ein Abruf fuer Berlin laedt jedes Mal die ganze Erde.
  Unser 5x8-Faecher liegt komplett in EINEM Chunk — er kostet exakt so viel
  wie der Planet. Daraus folgt (Rechnung, keine Messung; Egress-Listenpreis
  0,12 USD/GB):

  - p ueber 64 Member, 3 Wolkenschichten, EIN Abend: 64x3x116,2 MB =
    **22,3 GB = rund 2,70 USD je Lauf**
  - fuer alle 10 Vorlauftage: **223 GB = rund 27 USD je Lauf**, bei zwei
    Laeufen taeglich rund **1.600 USD im Monat**
  - Advektionswind ist dagegen billig: 64 Member x 1 Druckflaeche = 237 MB

  Das Statistik-Bucket kostet nichts (627 MB je Lauf fuer 3 Schichten x 10
  Abende), traegt aber **weder p noch Advektion**: Perzentile je Gitterpunkt
  zerstoeren die Memberzuordnung, und unser p ist der Memberanteil, dessen
  SCORE ueber s\* liegt — eine nichtlineare Funktion ueber 40 Faecherpunkte
  und drei Schichten. Aus Perzentilen ist kein einziger kohaerenter Member
  rekonstruierbar.

  **Damit ist Open-Meteo doch der Weg — aber aus einem anderen Grund, als
  hier zuerst stand.** Nicht weil der Zugang fehlt, sondern weil Open-Meteo
  global gechunkte Gitter in Zeitreihen je Punkt umbaut. Genau diese
  Umchunkung ist der Wert, und sie ist nichts, was wir fuer 40 Punkte selbst
  nachbauen wollen.

  **Ungeprueft geblieben:** ob Earth Engine oder BigQuery fuer WN3
  serverseitigen Punktausschnitt mit **Membern** liefert. `bq ls` auf
  `gcp-public-data-weathernext` gab mit diesem Konto nichts zurueck; die
  Google-Doku nennt fuer beide nur Mittel und Perzentile. Faende sich dort
  ein Memberzugang, kippt die Empfehlung sofort — dann ist WN3 ohne
  Egress-Kosten nutzbar. Das ist der einzige offene Punkt, der es wert ist.

  **KORREKTUR 08.09.2026, noch am selben Tag.** Die Rechnung oben (223 GB =
  27 USD je Lauf, 1.600 USD im Monat) unterstellt stillschweigend, dass die
  Daten ins INTERNET fliessen. Das ist der teuerste denkbare Weg und nicht
  der noetige. Gemessen: **beide Buckets liegen in `US-EAST1`**, einer
  einzelnen Region. Egress von Cloud Storage zu einer Recheneinheit in
  DERSELBEN Region kostet 0 USD/GB — unabhaengig von jedem Freikontingent.
  Laeuft die Faecherextraktion in us-east1, verlassen die 223 GB die Region
  nie; nach Hause reisen nur die 40 Punkte.

  Was dann noch anfaellt (Requester-pays traegt Operationen und Egress):
  - Class-B-Operationen: 64 Member x 3 Schichten x 10 Abende = 1.920 GETs je
    Lauf, plus Wind rund 640 = ~2.560. Bei zwei Laeufen taeglich ~154.000 im
    Monat, davon 50.000 im Always-Free-Kontingent, Rest zu 0,004 USD je
    10.000 -> **rund 0,04 USD im Monat**.
  - Egress in der Region: **0 USD**.
  - Rechenzeit: Always Free gibt genau in us-east1 eine e2-micro (720 h/Monat,
    30 GB Platte) und bei Cloud Run 180.000 vCPU-Sekunden im Monat.

  **Zeitbudget ist der neue Engpass, nicht Geld.** Gemessen auf dem Mac:
  Dekompression eines Chunks 0,18 s, also ~346 s reine CPU je Lauf fuer die
  1.920 Wolkenchunks. Auf einer e2-micro (0,25 vCPU Grundlast) grob
  hochgerechnet 45-60 min CPU plus Netz — realistisch **1,5 bis 2,5 h je
  Lauf**. Der Alarm rechnet drei Stunden vor Sonnenuntergang; das ginge auf,
  laesst aber kaum Reserve. Stellschrauben, beide linear: weniger Abende
  (3 statt 10 -> 67 GB) oder weniger Member (16 statt 64 -> p mit rund
  +/-12 % statt +/-6 %). Cloud Run mit 4 vCPU passt rechnerisch knapp ins
  Freikontingent (60 Laeufe x ~2.900 vCPU-s = ~174.000 von 180.000).

  **Member-Frage abschliessend geklaert (08.09.2026).** Es gibt KEINEN Dienst
  mit serverseitigem Punktausschnitt UND Membern:
  - BigQuery: Schema ist `init_time`, `geography`, `forecast` (RECORD) mit
    `_mean/_p10/_p25/_p50/_p75/_p90`. Die Doku verweist fuer die 64 Rohmember
    ausdruecklich auf GCS/Zarr. Partitioniert nach `init_time`, geclustert
    nach `geography`; 1 TiB Abfragevolumen im Monat frei.
  - Earth Engine: dieselben Assets `weathernext_3_0_0_0p1deg` /
    `_0p05deg`, dieselben sechs Statistiken. Keine Member.
  - GCS/Zarr: einziger Ort mit Membern. Dimension `sample` = 64, selbst
    gemessen.

  **End-to-End-Nachweis gefuehrt, nicht behauptet.** Chunk
  `high_cloud_cover/c/0/10/0/0/0` geladen (116.238.817 B), mit dem
  `zstd`-Kommandozeilenwerkzeug entpackt -> 155.606.400 B = exakt
  6 x 1801 x 3600 x 4. Achsen entpackt: `lat_0p1` laeuft von -90 aufsteigend,
  `lon_0p1` von 0 bis 359,9. Berlin trifft `lat[1425]=52,50`,
  `lon[134]=13,40`. `datetime[lead_time=10]` = 2026-09-10T18:00Z, also
  Init +66 h. Member 0 liefert dort sechs Stundenwerte hohe Bewoelkung
  (alle 0,0), globaler Wertebereich 0,0 bis 1,0, in 1 Grad Umkreis bis 0,15.
  **Der ganze 5x8-Faecher liegt in genau diesem einen Chunk** — 441 Punkte im
  2-Grad-Quadrat stammen alle daraus, die Faechergeometrie kostet also nichts
  extra. Kein `zarr`- oder `xarray`-Paket noetig: `zstd` plus
  `numpy.fromfile` mit `reshape` reicht.

  Damit ist A aus der Entscheidungsvorlage vom 08.09. nicht mehr an den
  Kosten gescheitert. Was bleibt, ist eine Betriebsfrage, und die zerfaellt
  in zwei sehr verschiedene Zuschnitte:

  - **(a) nur die Extraktion zieht um.** Etwas Kleines in us-east1 schneidet
    die 40 Faecherpunkte heraus und legt wenige kB als JSON ab; der Mac holt
    die Datei und macht ab da alles wie bisher — Score, Schwelle, Push,
    Seiten, Archiv. `konfig_geheim.json` und der `gh-pages`-Push bleiben
    lokal.
  - **(b) der ganze Alarm zieht um**, der Mac ist nur noch
    Entwicklungsrechner.

  Sinnvoll ist (a). **Aber Vorsicht mit einem Argument, das hier zuerst
  stand:** (a) loest die WLAN- und Schlafprobleme aus `skripte/netz.py` und
  T-0070 NICHT — der Mac muss weiter wach sein und rechnen. Das ist ein
  Argument fuer (b) und gehoert nicht an (a).

  Der Preis von (a) ist ein ZWEITER Betriebsort. Das Projekt hat heute genau
  einen, und die Fehlerklasse ist bekannt (Memory `streulicht-agenten-
  scheitern-still`: kaputter Programmpfad schreibt nichts ins Log, nur der
  Exitcode verraet ihn). Dazu haengt ein Google-Rechnungskonto am Betrieb und
  es entsteht der neue Fehlerfall "Cloud-Datei fehlt oder ist von gestern".
  Die Entscheidung lautet deshalb nicht "Mac oder Cloud", sondern: **nehmen
  wir einen zweiten Betriebsort in Kauf, um an WN3 zu kommen?**

- T-0073 WeatherNext 2 als Zweitmeinung tatsaechlich bauen. Befund 2 haelt
  seit E1 fest "WN2 bleibt als Zweitmeinung: 64 Member, physikalisch
  unabhaengiger Ansatz, adressiert die Unterdispersionsfrage besser als zwei
  Varianten derselben Physik" — geprueft 08.09.2026: **`weathernext` kommt in
  keiner .py, .js oder .json vor**, nur in `docs/` und `STATE.md`. Die
  Zweitmeinung ist entschieden und nie gebaut worden. Sie ist heute
  erreichbar (siehe Tabelle in T-0072), kostet einen zweiten `models=`-Wert
  im selben Abruf und beantwortet die Frage, die WN3 spaeter im Grossen
  stellt, schon jetzt im Kleinen: weichen die 64 ML-Member an unseren
  Faecherpunkten systematisch von den 51 IFS-Membern ab? Offen und vorher zu
  klaeren: Kontingentkosten des zweiten Modells, und der 6-h-Versatz
  (`skripte/interpolation.py` misst genau diesen Fall).

## Done

### 04.09.2026 &mdash; Fremdreview umgesetzt (T-0063 bis T-0071)

Ein fremdes Modell (Fable 5.1) hat die Codebase gelesen und zehn Befunde
gemeldet. Neun sind hier abgearbeitet, einer braucht eine Entscheidung von
Andre. **Stand danach: 310 Python-Pruefungen + 41 JS, alle gruen.**

Jeder neue Waechter hat eine EIGENE Negativprobe bekommen &mdash; die Regel
aus T-0054 (ein Waechter ohne eigenen Fall ist ungeprueft) ist hier viermal
angewandt worden, und zweimal hat sie einen zu schwachen Test entlarvt.

#### T-0063 Advektion tastete stromab statt stromauf ab &mdash; Korrektheit

`skripte/alarm.py`. Das Modellfeld liegt zu einem nativen 3-h-Schritt vor,
der Sonnenuntergang liegt daneben. Gesucht ist die Wolke, die zum
Sonnenuntergang ueber dem Fanpunkt steht &mdash; zum frueheren Modellschritt
war dieselbe Luft noch **stromauf**. Der Lauf hat den Transportvektor aber
ADDIERT statt ihn abzuziehen und damit die Zelle auf der falschen Seite
gelesen, mit dem doppelten Fehler 2&middot;v&middot;|dt|: bei 100 km/h und
dt = 0,5 h sind das 100 km daneben.

Aufgefallen ist es nie, weil ein verschobener Faecher genauso plausible
Zahlen liefert wie ein richtiger. `versatz_km()` selbst war korrekt; der
Fehler sass eine Ebene darueber, und der bestehende Test prueft genau die
richtige Funktion und deshalb am Fehler vorbei.

**Warum das dringend war:** die Livekalibrierung von s\* und p\* nach sechs
bis acht Wochen haette einen verschobenen Score kalibriert, und das ist
rueckwirkend nicht mehr trennbar.

- [x] Vorzeichen gedreht, Fundstelle ausfuehrlich kommentiert
- [x] `test_advektion.py`: Pass-2-Zellen muessen bei Westwind westlich der
      Pass-1-Zellen liegen, und zwar deutlich (> 0,25 Grad, nicht um eine
      Rundung)
- [x] Negativprobe: altes Plus wieder eingebaut &rarr; 2 Pruefungen rot
      (11,333 gegen 10,020 Grad Ost)

**Erster Testentwurf war zu schwach und ist verworfen worden.** Er legte
Wolke nur westlich des Ortes an und erwartete, dass Term A steigt. A kam auf
0,034 &mdash; nicht wegen der Richtung, sondern weil A im Nahbereich
raumwinkelgewichtet ist und der Standortpunkt allein rund drei Viertel
traegt. Ein Test, dessen Ergebnis mehr an der Gewichtung haengt als an der
geprueften Eigenschaft, misst nicht das Gemeinte.

#### T-0064 Die Begruendung kam vom besten Member, die Zahl vom Median

`skripte/alarm.py`, `verdichte()`. Schirm, A, Sicht, Weg und die
Segmentliste stammten aus `max(gueltig, key=...)`. Stufe und
Wahrscheinlichkeit beschrieben also die Mitte der Verteilung, der Satz
darunter ihr optimistisches Ende &mdash; auf der Seite jeden Abend ein
Widerspruch.

**Beleg** (ausgelieferte Seite vom 01.09.2026 fuer den 11.09.): Median 0,03,
Wahrscheinlichkeit 2 %, Stufe "unauffaellig", darunter "Mittelhohe Wolken,
Licht kommt von Westen frei durch". Ein einziger von 51 Membern kam auf
S = 0,88.

Jetzt kommt alles aus demselben Member. Beim Push ist das kein Verlust: der
geht erst ab p >= 0,5 raus, und dann liegt der Medianmember ohnehin ueber
s\*. Die Streuung geht nicht verloren &mdash; das Tagesarchiv haelt
weiterhin je Member eine eigene Zeile mit S, A, B, Sicht und Weg.

- [x] `verdichte()` sortiert nach Score und nimmt Median samt Detail aus
      demselben Member (`key=lambda x: x[0]`, sonst vergleicht `sorted` bei
      Gleichstand die Detail-dicts und stirbt am TypeError)
- [x] `test_member.py` Abschnitt 4, vier Faelle inkl. Datenluecken
- [x] Negativprobe: `max()` wieder eingesetzt &rarr; 4 Pruefungen rot

#### T-0065 Modelllauf-Verfuegbarkeit: gemessen statt behauptet

Zwei Dinge in einem. Erstens holte `alarm.py` den Modelllauf ERST nach der
Ortsschleife, also rund vier Minuten nach dem Abruf &mdash; genau dazwischen
kann ein neuer Lauf verfuegbar werden, und dann trugen Archiv und
Standzeile eine Initialisierung, aus der die Zahlen nicht stammten. Das ist
ausgerechnet das Feld, auf dem alle Verzugsaussagen des Projekts beruhen.

Zweitens stand in `konfig.json` "der 00z-Lauf wird 08:44 UTC verfuegbar",
aus **einer** Probe vom 18.08.2026. **Nachgezaehlt am Tagesarchiv, 27 Laeufe
vom 21.08. bis 04.09.2026:**

| Fenster | n | benutzter Lauf | Verzug min/Median/max |
|---|---|---|---|
| `morgens` 09:20 UTC | 13 | **13x 18z des Vortags, 0x 00z** | 15,3 / 15,3 / 15,6 h |
| `abends` ~3 h vor SU | 14 | 8x 06z, 4x 00z, 2x 18z | 9,3 / 11,3 / 22,3 h |

Der Vormittagslauf sieht den 00z also **nie**; 09:20 UTC ist zu frueh. Wie
viel spaeter er liegen muesste, ist nicht gemessen &mdash; und genau deshalb
wird `lauf_morgens_utc` jetzt NICHT auf Verdacht verschoben.

- [x] `modelllauf()` vor den Abruf gezogen
- [x] Jeder stuendliche Leerlauf-Tick schreibt den verfuegbaren Modelllauf
      ins Log (statische Datei, kein Kontingent). Nach zwei Wochen ist
      `lauf_morgens_utc` belegbar statt geraten.
- [x] `konfig.json` und README auf die gemessenen Zahlen
- [ ] **offen:** nach zwei Wochen Logdaten `lauf_morgens_utc` nachziehen

#### T-0066 Bewertungsabruf stuendlich statt alle drei Stunden

ntfy.sh haelt rund 12 h vor; die Bewertungsseite markiert eine Note nach dem
ersten erfolgreichen POST als erledigt und sendet nie wieder nach. Im
Alarmlog stehen ueber 318 Laeufe **17 Luecken von mehr als 70 Minuten, die
laengste 724 Minuten** &mdash; knapp unter der 12-h-Grenze, aber eben knapp.

- [x] `betrieb/de.greatbelow.streulicht.bewertung.plist` auf 24 stuendliche
      Termine, `plutil -lint` sauber
- [x] **Geladen am 04.09.2026** (bootout + bootstrap durch Andre).
      Gegenprobe: 24 Kalendertermine, alle 24 Stunden belegt, installierte
      plist identisch mit der im Repo.
- [x] **Geplantes Aufwecken gesetzt am 04.09.2026** (Andre, mit Passwort).
      Erst 08:00, nach der Rechnung unten korrigiert auf **02:00**.
      Gegenprobe `pmset -g sched`: `wakepoweron at 2:00AM every day`.

**Die Weckzeit ist eine Rechnung, keine Gewohnheit.** Ich hatte 08:00
vorgeschlagen, weil man morgens aufsteht, und nicht nachgerechnet. Die
Bedingung lautet: der naechste Abruf nach dem Wecken muss innerhalb von 12 h
nach der Bewertung liegen. Frueheste Bewertung ist der Sonnenuntergang
selbst (spontan, ohne Aufforderung), und der wandert in Berlin um mehr als
fuenfeinhalb Stunden. Gerechnet mit `sonnen.geometrie` ueber ein volles Jahr,
schlimmster Tag jeweils der 13.12.2026:

| Weckzeit | kleinste Luft im Jahr | |
|---|---|---|
| 08:00 | −4,2 h | Luecke |
| 06:00 | −2,2 h | Luecke |
| 04:00 | −0,2 h | Luecke |
| **03:00** | **+0,8 h** | traegt |
| **02:00** | **+1,8 h** | traegt, mit Reserve |

Ab etwa dem 01.10.2026 verliert 08:00 die erste Note; am 05.09. lag die Luft
noch bei +0,2 h, also eine Zufallsmehrheit. Gewaehlt ist **02:00**: ntfy haelt
"rund 12 h", keine zugesicherten 12,0 h, und 03:00 liesse dafuer nur
48 Minuten. `pmset repeat` ersetzt den bestehenden Eintrag, es braucht kein
Loeschen davor. Preis: der Rechner wacht jede Nacht kurz auf (Ruhezustand
nach 10 min Leerlauf, der Abruf dauert Sekunden).

**Noch nicht beobachtet:** dass der 02:05-Abruf nach einem geplanten Wecken
wirklich laeuft. Erwartet wird eine Zeile in `daten/bewertung.log` gegen
02:05; `launchctl print ... | grep runs` zaehlt mit. Falls nicht: der
Rechner schlaeft nach dem `wakepoweron` moeglicherweise zu schnell wieder
ein, dann muss der Abruf naeher an die Weckzeit (Minute 0 statt 5).

Dieselbe Fehlerklasse wie die falsche launchctl-Gegenprobe eine Stunde
vorher: **eine Zahl, die plausibel klingt, statt einer, die nachgerechnet
ist.** Beide Male hat erst die Gegenprobe den Fehler gezeigt.

**Die Gegenprobe war beim ersten Anlauf falsch dokumentiert** und meldete
einen Fehlschlag, den es nicht gab. Empfohlen war
`launchctl print ... | grep -c "minute = 5"` &rarr; Ergebnis 0, obwohl alles
richtig geladen war. `launchctl print` schreibt die Kalendertermine als
`"Minute" => 5`, nicht als `minute = 5`. Richtig ist:

```bash
launchctl print gui/$UID/de.greatbelow.streulicht.bewertung | grep -c '"Minute" => 5'
```

Merksatz derselben Klasse wie in `~/src/CLAUDE.md` zur ID-Suche: **ein
Pruefbefehl, der still zu wenig findet, ist schlimmer als keiner.** Hier
hat er in die andere Richtung geirrt - er meldete einen Defekt statt ihn zu
verschweigen, was billiger ist, aber dieselbe Ursache hat: das Suchmuster
war geraten und nie gegen eine echte Ausgabe gehalten.

#### T-0067 Erinnerung wird bis Mitternacht nachgeholt

Das Fenster ist 75 Minuten breit, der Agent tickt stuendlich. Schlaeft der
Rechner darueber hinweg, gab es an diesem Abend gar keine Aufforderung und
damit sehr wahrscheinlich keine Note. Der Alarmlauf holt seinen verpassten
Tick seit T-0048 nach, die Erinnerung tat es nicht &mdash; obwohl sie an
derselben Maschine haengt und die Bewertungen die **einzige nicht
nachproduzierbare** Messgroesse des Projekts sind.

Nachgeholt wird bis zum **lokalen** Mitternacht und nur der heutige Abend.
Die Grenze ergibt sich von selbst, weil nur mit dem heutigen lokalen Datum
aufgerufen wird; nach Mitternacht bewertet niemand mehr den vorletzten
Sonnenuntergang.

- [x] `verstrichen()` in `skripte/erinnerung.py`, Log sagt "(nachgeholt, +N min)"
- [x] Neuer Test `skripte/test_erinnerung.py`, 9 Pruefungen, kein Netz,
      eigenes Temp-Verzeichnis &mdash; inkl. Winterabend (21.12., SU 14:53 UTC)
- [x] Negativprobe A: Nachhol-Zweig tot &rarr; 4 Pruefungen rot
- [x] Negativprobe B: Mitternachtsgrenze aufgeweicht &rarr; 5 Pruefungen rot

#### T-0068 Testhygiene: keine Betriebsdaten, keine Uhrzeitabhaengigkeit

Drei Tests, zwei Fehlerklassen.

**`test_abruf.py` lief gegen die produktive Zustandsdatei.** Er startete
einen vollstaendigen `alarm.main()` OHNE `--trocken`, sicherte
`daten/zustand.json` weg und schrieb sie danach mit `open(zp, "w")` zurueck
&mdash; truncierend und ohne Sperre. Faellt in diese Sekunden ein
Bewertungsabruf oder eine Erinnerung, ist deren Schreibvorgang verloren.
Ausserdem ueberschrieb er ein vorhandenes `<heute>_vonhand.json` im echten
Tagesarchiv. Laeuft jetzt in einem eigenen Temp-Verzeichnis
(`alarm.BASIS` umgebogen, Muster aus T-0058), plus Riegel auf `sende`.

**Zwei Tests haengen an der Uhr und waren regelmaessig rot, ohne dass am
Code etwas falsch war:**
- `test_zustandspflege.py` erwartete eine Zahl fuer den heutigen Abend, den
  `alarm.py` nach Sonnenuntergang aber ueberspringt &mdash; jeden Abend rot.
- `test_bewertungsseite.js` suchte den festen Monatsnamen "August" &mdash;
  ab dem 1. September rot.

Ein Test, der einmal am Tag oder einmal im Monat von selbst umkippt, wird
nicht mehr gelesen, und dann faellt auch der echte Fehler nicht auf.

- [x] `test_abruf.py` auf Temp-BASIS; verifiziert: `daten/zustand.json`
      md5 und Archivstand vor und nach dem Lauf identisch
- [x] `lauf_ort(ort, kfg, jetzt)` &mdash; `--jetzt` steuerte bisher nur die
      Fensterpruefung, waehrend im Lauf die echte Uhr lief. Die nie
      gelesenen Parameter `zustand` und `trocken` sind dabei entfallen.
- [x] `test_zustandspflege.py` faehrt gegen feste 06:00 UTC
- [x] `test_bewertungsseite.js` prueft gegen alle zwoelf Monatsnamen

#### T-0069 Voruebergehende Netzstoerungen kippten den Lauf

`_hole()` behandelte NUR 429. Ein Timeout, ein abgebrochener
Verbindungsaufbau oder ein 502 riss den ganzen Lauf mit Traceback ab &mdash;
und jeder gescheiterte Versuch hatte sein Kontingent schon verbraucht. Der
Abendlauf wird vom naechsten Tick nachgeholt, der Vormittagslauf nicht.
Zweiter Fehler an derselben Stelle: ein 429 ohne JSON-Rumpf starb am
`json.loads` statt die gemeinte Kontingentmeldung auszugeben.

Wiederholt werden 5xx, URLError, Timeout und truncierte Antworten
(5/15/45 s). **Nicht** wiederholt werden 4xx &mdash; eine kaputte Anfrage
wird beim Wiederholen nicht besser, verbrennt aber Kontingent und verdeckt
den eigenen Fehler. Kontingent (429 stuendlich/taeglich) bleibt terminal.

- [x] `test_abruf.py` Abschnitt 7, 7 Faelle gegen gestubbtes `urlopen`
- [x] Negativprobe C: alte `_hole`-Fassung &rarr; 4 Pruefungen rot
- [x] Negativprobe D: auch 4xx wiederholen &rarr; 1 Pruefung rot
      (der Fall hat also seinen eigenen Waechter, nicht nur Deckung durch
      die anderen)

#### T-0070 `netz.py` zaehlte Wachzeit statt Wanduhrzeit

`time.monotonic()` steht auf macOS im Ruhezustand still. Schlaeft der
Rechner mitten im Warten ein, laeuft die Frist nicht weiter, und aus den
zugesagten 20 Minuten werden real Stunden. Belegt im Log vom 01.09.2026:
"Warte bis zu 20 Minuten" um 18:28, "Netz ist da" um 18:57.

- [x] `time.time()` statt `time.monotonic()`

#### T-0071 Aufraeumen und Doku

- [x] **Winterlauf-Widerspruch aufgeloest.** `konfig.json` sagte "beide
      Laeufe benutzen denselben 00z", README sagte "18z". Richtig ist 18z
      (Abendfenster im Dezember 11:53 UTC, da ist der 00z noch nicht da).
- [x] **Vertikalschnitt bekommt den Schirm aus dem Zustand.** `schnitt_neu`
      rechnete `score()` aus dem Medianfeld neu und waehlte daraus sein
      Niveau &mdash; das kann ein anderes sein als das, auf das sich Stufe
      und Text beziehen. Dann zeigt das Bild eine Tangente bei 402 km,
      waehrend daneben "mittelhohe Wolken" steht.
- [x] **Ein-Ort-Grenze benannt.** `orte[]` ist eine Liste, aber
      Prognoseseite, Bilanz, Schnitt und Karte sind auf Berlin fest
      verdrahtet. Ein zweiter Ort bekaeme Pushs gegen Berlins s\* und eine
      Seite, die Berlin zeigt &mdash; beide Laeufe enden mit Exitcode 0.
      `ausliefern.py` warnt jetzt; bewusst KEIN Abbruch, weil
      Mehrortfaehigkeit ein erklaertes Ziel aus E0 ist.
- [x] Tote Funktionen `nachrichten()` und `_abschnitte()` aus
      `sonnen/grib2.py` entfernt (nirgends aufgerufen)
- [x] `ERSTER_ABEND` hatte zwei Kopien &mdash; `bisher.py` importiert es
      jetzt aus `bewertungen_holen.py`
- [x] Doppelter `ZoneInfo`-Import in `lokalzeit()` entfernt
- [x] `verlaufszeile` traegt `jetzt.date()` statt `date.today()`

**Bewusst NICHT geaendert** (Befund war richtig, Aufwand lohnt nicht):
`feld_seite` schluesselt die Fanpunkte auf das 0.5-Grad-Gitter um; zwei
Punkte koennen dieselbe Zelle treffen, der letzte gewinnt. Betrifft nur das
BILD, und beide Punkte tragen ohnehin Medianwerte derselben Datenlage. Eine
Zusammenfassung (max? Mittel?) waere eine willkuerliche Entscheidung an
einer Stelle, an der nichts davon abhaengt.

### 30.08.2026 &mdash; T-0062 Automationen auf gepflegtes Python umgestellt
Die vier Agenten liefen auf `/usr/local/bin/python3` &mdash; einem Symlink auf
das python.org-Framework **3.10.11**, dessen Sicherheitsunterstuetzung im
Oktober 2026 endet. Ziel war Homebrew `python@3.13` (3.13.15).

**Umgestellt auf `/Users/Andre/src/wetter/.venv/bin/python3`** &mdash; acht
Dateien, je Agent die Repo-Kopie in `betrieb/` UND die installierte in
`~/Library/LaunchAgents/` (beide waren byteweise identisch und sind es
wieder). Danach je `launchctl bootout` + `bootstrap`; `launchctl print`
meldet fuer alle vier den neuen `program`-Pfad.

**Der Umweg ueber eine venv ist Absicht, nicht Paketverwaltung.** Der
Automationspfad braucht **keine einzige Fremdbibliothek**: der transitive
Import-Baum der vier Einstiegsskripte, inklusive der drei per `subprocess`
gestarteten Generatoren (`seite.py`, `bewertungsseite.py`, `bisher.py`),
erreicht 15 lokale Module und ausser der stdlib nichts. Die venv liefert
statt dessen einen **stabilen Pfad**: sie ist ueber den unversionierten
`/opt/homebrew/opt/python@3.13/bin/python3.13` angelegt, ihr Symlink zeigt
auf genau diesen Pfad, und ein brew-Minorupdate von 3.13.15 auf 3.13.16
bricht sie deshalb nicht. Die Plists muessen nie wieder angefasst werden.

**Billig war die Migration wegen `ausliefern.py:64`:** die Kindprozesse
werden ueber `sys.executable` gestartet, nicht ueber einen verdrahteten
Pfad. Der Interpreterwechsel in der Plist erbt sich damit von selbst auf
`seite.py`, `bewertungsseite.py` und `bisher.py`. Nachgewiesen: Eltern- und
Kindprozess melden beide `.venv/bin/python3` und 3.13.15.

`numpy` und `matplotlib` sind trotzdem in die venv gekommen, aber aus einem
anderen Grund: `sonnen/grib2.py` importiert `numpy` lazy, und ohne das faellt
`skripte/test_grib2.py` aus. Unter dem alten 3.10 war es da (numpy 1.26.4,
matplotlib 3.10.8, aus dem projektuebergreifenden site-packages-Sammelsurium);
ohne Nachinstallation waere die Migration eine **stille Regression** im
Testlauf gewesen. Jetzt numpy 2.5.2 / matplotlib 3.11.1, festgehalten in
`betrieb/anforderungen.txt`.

**Verifikation, inhaltlich statt Exitcode.**
- Rauchtest vorab: alle 15 erreichten Module unter 3.13 importierbar (15/15).
- Testlauf: **273 Python-Pruefungen + 42 JS gruen** &mdash; identisch zur
  Baseline vom 23.08.2026, kein Verlust durch den Versionssprung.
- `bewertung`: echter ntfy-Abruf, 10 Bewertungen verarbeitet, Histogramm.
- `alarm`: Volllauf mit `--trocken` &mdash; 186 Ortsabrufe, 51 Member, 88
  native Schritte, Prognosetabelle ueber 11 Tage. Der geplante Lauf selbst
  faellt ausserhalb seiner Fenster und beweist fuer sich zu wenig.
- `erinnerung`: der geplante Lauf lag ausserhalb des Fensters, deshalb den
  Sendepfad zusaetzlich mit `--jetzt` ins Fenster gelegt (`--trocken`, kein
  POST): Sonnenuntergangsgeometrie, Text und Klick-URL werden korrekt
  gebaut (+28 bis +58 min nach SU).
- `seite`: alle drei Seiten neu gebaut (index 0.29 MB, bewerten-berlin
  44.7 kB, bisher 15.0 kB), danach korrekt "unveraendert seit dem letzten
  Push". Der `push --force` blieb also aus, weil der Inhalt gleich war &mdash;
  das ist die Idempotenz des Jobs, kein ausgelassener Test.

**Negativprobe, einzeln pro Agent** (nicht eine, die alle vier abdeckt):
Interpreterpfad je Job auf einen nicht existierenden verbogen, neu geladen,
angestossen. Alle vier scheitern mit `last exit code = 78: EX_CONFIG`,
danach zurueckgenommen und ein Bestaetigungslauf gefahren &mdash; alle vier
wieder auf 0.

**Nebenbefund, der eine eigene Aufgabe verdient (siehe T-0040):** ein
kaputter Interpreterpfad schreibt **nichts** ins Log. `daten/alarm.log` &
Co. bleiben beim Fehlschlag leer; sichtbar ist er nur in `launchctl print`.
Genau die Logs sind aber das, was hier von Hand gelesen wird.

**Nicht angefasst, bewusst:** `/usr/local/bin/python3` und das
python.org-3.10-Framework bleiben, wie sie sind &mdash; daran haengt noch das
Mailarchiv-Projekt. Ebenso `de.xindaan.strapazierrasen-fern.plist.disabled`:
der ruft zwar auch `/usr/local/bin/python3`, gehoert aber zu Gardena und ist
deaktiviert. Die zentrale Entfernung des alten Interpreters erst, wenn beide
Projekte umgestellt sind.


### 23.08.2026 &mdash; Backlog des Reviews abgearbeitet (T-0056 bis T-0059, T-0061)
Tests: **273 Python-Pruefungen + 42 JS**, alle gruen (Baseline vor dem Review:
153). Vier neue Testdateien.

- T-0058 **Wachstum und verlorene Schreibvorgaenge (erledigt).** Zwei
  Probleme, die gleich aussehen und verschiedene Mittel brauchen.
  *Wachstum:* `raeume()` in `alarm.py` entfernt unbewertete Abende aelter als
  `BEHALTEN_TAGE = 30`; ihre Prognosedaten liegen im Tagesarchiv (T-0003).
  **Bewertetes bleibt unbefristet** - eine Note ist die einzige Messgroesse
  ohne zweite Quelle. `verlauf` wird auf `VERLAUF_MAX = 10` gekuerzt.
  *Verlorene Schreibvorgaenge:* neu `gesperrt()` und `aktualisiere()` in
  `zustandsdatei.py` (`fcntl.flock` auf einer eigenen `.lock`-Datei - ein Lock
  auf der Zustandsdatei selbst zeigt nach `os.replace` ins Leere).
  **Der atomare Schreibvorgang aus T-0051 half hier nicht:** er verhindert
  halbe Dateien, nicht das Dazwischenkommen. Belegt: 12 parallele Prozesse,
  ohne Sperre kamen 4 von 12 Erhoehungen an.
  Alle drei Agenten rechnen/senden jetzt AUSSERHALB der Sperre und mergen ihr
  Ergebnis gegen den frischen Stand - `alarm.py` bewahrt dabei ausdruecklich
  die Bewertungsfelder, denn genau dort ging eine gerade eingesammelte Note
  verloren (nachgestellt und behoben).
- T-0056 **`--geplant` rechnet nur faellige Orte (erledigt).** Gemessen mit
  zwei Orten (Berlin/Bilbao, Fenster ueberlappen nicht): vorher 246 Zellen in
  6 Anfragen, jetzt 103 in 3. Ungefragte Orte werden auch nicht mehr als
  "vonhand" gebucht - ihr Fenster bleibt fuer den Tag offen. Ein Lauf von
  Hand rechnet weiterhin alle Orte.
- T-0057 **Sparfaecher abgeschafft statt repariert (erledigt).**
  `fan_setzen` hat `sonnen.score.FAECHER_AZIMUTE/DISTANZEN_KM` zur Laufzeit
  ueberschrieben; zwoelf Module importieren sie by value und sahen das nie.
  **Entscheidung, bewusst:** der saubere Weg waere, die Geometrie durch
  `score()` zu reichen - die liest die Konstanten an dreizehn Stellen, das ist
  ein Umbau der Kernfunktion des Betriebsscores. Fuer einen Hebel, der in
  `konfig.json` auf `null` steht, nie benutzt wurde und ausserdem s* = 0.7065
  ungueltig macht, ist das ein schlechtes Verhaeltnis. Eine alte Konfiguration
  bricht jetzt mit Erklaerung ab, statt still ignoriert zu werden.
- T-0059 **Abendwahl meldet sich bei assistiver Technik (erledigt).** Der Hero
  ist `role="status"` + `aria-live="polite"` (nicht "assertive": Blaettern ist
  Erkundung, keine Warnung). Die Achse ist eine Tabliste mit `role="tab"`,
  `aria-selected` und Roving Tabindex - EIN Tabstopp statt elf. Fahne, Punkt,
  Rangzahl und der Achsenfuss sind als Dekoration ausgezeichnet. Home/End
  ergaenzt, und die Pfeiltasten nehmen den Fokus mit, aber nur wenn er in der
  Achse liegt (ungefragtes Fokussieren ist selbst ein Fehler). Der
  Anfangszustand steht im MARKUP - ohne das ist die Seite bis zum ersten
  `waehle()` zustandslos. Visuell gegengeprueft: unveraendert.
- T-0061 **`score_distanz.py`: drei Befunde (erledigt).** Nicht im
  Betriebspfad (kein Modul importiert es), aber sie sassen an einer Zeile.
  (1) Die Deckung teilte einen STUETZSTELLENZAEHLER durch eine LAENGE - volle
  Belegung meldete 0.899 statt 1.00. **Diesen Fehler hat der Test gefunden,
  nicht ich:** meine erste Fassung setzte `noetig` ein und war damit nur
  weniger falsch. (2) `noetig` war eine tote Variable - ein halber Reparatur-
  versuch fuer (1); mit `erfasst / moeglich` entfaellt sie ersatzlos.
  (3) Die Luecken-Klasse aus T-0054/T-0060: `sicht` und `weg` blieben bei 1.0,
  wenn nichts beobachtet war.

### 23.08.2026 &mdash; Phantomnullen (T-0060), und was die Messung ergab
- T-0060 **Datenluecken werden nicht mehr zu Nullen (erledigt).** Beide
  Score-Varianten liefern `(s, detail)`; `detail is None` heisst "nicht
  auswertbar", der Score ist dann 0.0. `icond2_test.py:187` nahm nur `[0]`.
  Gefixt dort (Bloecke werden verworfen und **im Kopf des Berichts
  genannt**) und &mdash; Isomorphie-Check &mdash; in `klimatologie.py:206`.
  **Die Messung hat meine eigene Einschaetzung korrigiert.** Ich hatte den
  Befund als wichtigsten offenen Punkt gemeldet; am echten Cache
  (166 Dateien) ist er beim Standardlauf **wirkungslos**: der Deckungsfilter
  `>= 0.9` laesst 0 von 55 Abenden mit fehlendem Detail durch. Die von mir
  genannten "36 von 175" waren genau die Abende, die `hat_druck` ohnehin
  ausschliesst.
  **Erreichbar ist er trotzdem, und dann unsichtbar:** die Deckung ist
  bimodal (rund 1.0 oder rund 0.0). Wer `--mindestdeckung` senkt, um mehr
  Bloecke zu bekommen, holt sich 36 von 175 Phantomnullen (21 %) herein -
  und der Bericht meldete dabei weiter "0 mit Datenluecken" und gab
  `icon_niv 0.496` als Ergebnis aus. Genau dieser Lauf ist jetzt der Test
  (`skripte/test_phantomnullen.py`, gegen den echten Cache).
  **s\* ist NICHT betroffen, und das ist gemessen:** in allen fuenf
  vorliegenden `score_berlin_g0.5_*.json` steht `schirm: null` kein einziges
  Mal. Die 677 bzw. 308 Nullen darin sind echte dichte Bewoelkung. Der
  `klimatologie.py`-Riegel gilt kuenftigen Laeufen (anderer Ort, anderes
  Jahr, am Kontingent abgebrochener Abruf), nicht dem Bestand.
  **Drei Fehlalarme aus dem Sweep**, selbst nachgelesen und verworfen:
  `schnitt.py:207` stuerzt bei `det is None` laut ab (TypeError, kein
  stiller Wert), `seite.py:236` verwirft Score und Detail ohnehin,
  `test_seiten.py:70` prueft nur den Wertebereich.
  Regression: der Standardlauf liefert unveraendert 0.593 / 0.657 bei
  35 Bloecken. Tests: 206 Python-Pruefungen + 42 JS gruen.
- **Nebenbefund, nicht gefixt:** `seite.py:234-237` faengt jede Exception aus
  `schnitt_neu` mit `except Exception: pass` ab. Das Bild fehlt dann
  kommentarlos - andere Fehlerklasse (stiller Ausfall), eigener Task waere
  faellig, wenn es je auftritt.

### 23.08.2026 &mdash; Externer Review abgearbeitet (T-0051 bis T-0055)
Ox Alpha (stealth/ox-alpha via OpenRouter) hat am 22.08.2026 zehn Befunde
gemeldet, ohne den Code auszufuehren. Triage: **alle zehn an der Fundstelle
nachgelesen**, vier davon reproduziert. Ergebnis: acht BESTAETIGT, einer
BEKANNT/GEWOLLT (verstreute Ortskonstanten &mdash; D4 ist in `seite.py`
ausdruecklich als "vorbereitet, NICHT gebaut" dokumentiert, blockiert durch
T-0013 und T-0007), keiner FALSCH. Nachtrag zur Methode: **keine einzige
Zeilenangabe des Reviews stimmte** (durchgehend 20 bis 75 Zeilen zu niedrig)
&mdash; der Inhalt an der gemeinten Stelle jedes Mal.

Umgesetzt wurden die fuenf mit Schaden; T-0056 bis T-0059 liegen im Backlog.
Tests: 192 Python-Pruefungen + 42 JS, alle gruen (vorher 153).

- T-0051 **Zustandsdatei atomar (erledigt).** Neuer Helfer
  `skripte/zustandsdatei.py`: tmp im selben Verzeichnis, `flush` + `fsync`
  auf Datei UND Verzeichnis, dann `os.replace`. Belegt: 25 von 25
  SIGKILL-Abbruechen zerlegen den naiven Weg, 25 von 25 lassen den atomaren
  heil. **Isomorphie-Check ueber alle 24 `json.dump`-Stellen im Repo:** zwei
  weitere derselben Klasse gefunden und mitgefixt &mdash;
  `klimatologie.py:215` (die Klimatologie lesen SIEBZEHN Module, darunter
  alle drei Seitenbauer des 10-Minuten-Agenten) und `alarm.py:131`
  (Tagesarchiv, stiller Datenverlust im Bestand fuer T-0008). Die uebrigen
  20 sind Caches und Ausgaben manueller Analyseskripte &mdash; ein Abbruch
  dort haelt keine Betriebskette an.
- T-0052 **Bewertungs-Nutzlast validiert (erledigt).** `gueltige_note()`:
  int, kein bool, 0..5. `anlass` gegen die Werte, die die Erinnerung
  ueberhaupt erzeugen kann; `erfasst` als Text begrenzter Laenge. Zweite
  Verteidigungslinie in `bisher.py`: was VOR dem Fix hereinkam, liegt noch
  in der Datei, und `%d` auf einer Zeichenkette liess den ganzen Seitenbau
  sterben &mdash; nicht nur die eine Karte. **NICHT uebernommen:** der vom
  Review vorgeschlagene `erfasst`-Monotonie-Riegel; er bricht das
  Nachsende-Verhalten (T-0023) und den Widerruf. Restrisiko steht ehrlich im
  Modulkopf: gegen einen Willensangreifer hilft nur Auth, und eine statische
  oeffentliche Seite kann kein Geheimnis tragen.
- T-0053 **Push-Auskunft aus der Konfiguration (erledigt).** Neue Funktion
  `seite.pushauskunft()`, Zeit aus `lauf_vorlauf_stunden`. **Korrektur am
  Review:** er nennt das eine "taeglich sichtbare Falschaussage" &mdash; sie
  war es nicht. Der Satz erscheint nur im Alarmfall, also rund 18 Abende im
  Jahr, und genau deshalb ist er seit T-0041 unbemerkt falsch geblieben. Der
  Test erzwingt den Zweig, statt ihn der Wetterlage zu ueberlassen.
  **Isomorphie-Check** fand eine zweite Fundstelle: `README.md` nannte den
  "regulaeren 07:30-Lauf" als aktuelle Betriebsanweisung fuers Nachholen.
  Die uebrigen 07:30-Stellen sind historisch korrekt (Vorfall 17.08.2026).
- T-0054 **Datenluecken in `score_niveaus` (erledigt).** Beide Waechter aus
  `score.py` portiert, `weg_deckung`/`sicht_zellen` ins Detail. Belegt: mit
  Daten nur auf dem Schirmniveau im Nahbereich lieferte die Variante **0.9**
  (sicht=1.0, weg=1.0), wo `score` verwirft. **Die Negativprobe hat einen
  Testmangel aufgedeckt:** den `sicht`-Waechter allein zu entfernen liess
  alles gruen &mdash; der erste Testfall wurde schon vom `weg`-Waechter
  abgefangen. Ein Waechter ohne eigenen Fall ist ungeprueft, auch wenn er
  dasteht. Jetzt schlaegt jeder einzeln an.
- T-0055 **Versandfehler reisst den Lauf nicht mehr mit (erledigt).**
  try/except je Ort in `alarm.py`, Buchung nur bei Erfolg &mdash; sonst
  gaelte ein Abend als gemeldet, ohne dass eine Meldung ankam, und die
  Idempotenzsperre verhinderte dauerhaft das Nachholen. **Isomorphie-Check:**
  dieselbe Klasse in `erinnerung.py`, mitgefixt (bei einem Ort folgenlos, ab
  dem zweiten geht die Buchung des ersten verloren).

### 20.08.2026 &mdash; Archiv als Nebenprodukt (T-0003 erledigt), zwei Fehler dabei
- T-0003 **Taegliche Ensemble-Archivierung &mdash; erledigt, aber anders als
  entworfen.** `skripte/archiviere.py` hat NIE funktioniert: es holte die
  Felder ein zweites Mal (76 Zellen x 43 Variablen x 51 Member x 11 Tage),
  Open-Meteo antwortete durchgehend mit `HTTP 400: "Your API call requests
  too much data."`, und nachgerechnet waren es **16.720 Einheiten am Tag bei
  einem Budget von 10.000**. Der Ordner `daten/archiv/` war seit dem 15.08.
  leer, und aufgefallen ist es nur ueber `launchctl list`.
  Der Fehler war der zweite Abruf: **der Alarmlauf hat die Daten schon.**
  Er schreibt jetzt nach jedem erfolgreichen Durchlauf
  `daten/archiv/<ort>/<tag>_<fenster>.json` - je Abend eine Zeile pro Member
  (Score, Schirm, A, B, Sicht, Weg) und das Medianfeld. 60 kB je Lauf, rund
  44 MB im Jahr, **null zusaetzliche Abrufe**. Umfang nach Andres
  Entscheidung (Variante 1+2); Rohfelder je Member bleiben draussen, das
  waere ueber ein Gigabyte im Jahr fuer den Fall, dass die Score-Formel
  rueckwirkend geaendert wird.
  `skripte/archiviere.py` und der Agent `de.greatbelow.streulicht.archiv`
  sind entfallen. **Der Agent muss ausgeladen werden**, siehe STATE.
- T-0050 **Ein-Minuten-Fehler im Altersstreifen, gefunden von der
  Negativprobe.** Der Streifen verglich `stand["geholt"]` mit dem
  FENSTERZIEL. Der Agent tickt aber zur vollen 20. Minute, waehrend das Ziel
  bei Sonnenuntergang minus drei Stunden liegt - am 20.08. also 15:21:58 UTC
  gegen einen Lauf um 15:20:00. Zwei Minuten, und die Seite erklaerte ihre
  eigenen frischen Zahlen fuer veraltet. Verglichen wird jetzt gegen den
  ANFANG des Fensters.
  **Der Test hat den Fehler getarnt statt ihn zu zeigen**: er verglich noch
  Tag mit Tag, waehrend der Code laengst Zeitpunkte verglich. Er benutzt
  jetzt dieselbe Funktion wie `seite.py` - eine Regel, nicht zwei.
- **Und die Leck-Kontrolle im Archivtest war blind.** Sie las die
  Zustandsdatei NACH dem Zuruecksetzen, also die Sicherung statt des
  Geschriebenen. Die Negativprobe schlug deshalb nicht an. Behoben: der
  Zustand wird vor dem Zuruecksetzen festgehalten. Beide Negativproben
  greifen jetzt.


### 20.08.2026 &mdash; Fertig gerechnet, aber nicht gezeigt (T-0050)
- T-0050 **Die Auslieferung laeuft jetzt alle zehn Minuten.** Der Abendlauf
  am 20.08. war um 17:23 fertig und hatte den 00z-Lauf desselben Tages -
  genau wie vorhergesagt. Die Seite zeigte trotzdem bis 17:50 den
  Vormittagsstand, weil der Auslieferungsagent stuendlich zur 50. Minute
  lief. 27 Minuten lang war alles richtig gerechnet und nichts davon
  sichtbar; Andre hat es um 17:30 gemeldet.
  Ein Bauen ohne Push kostet **0,27 s** (gemessen), und gepusht wird nur bei
  geaendertem Fingerabdruck - alle zehn Minuten kostet also praktisch
  nichts und senkt die Obergrenze fuer veraltete Seiten von 59 auf 10 min.
  `test_lauffenster.py` prueft das Intervall mit; Negativprobe (zurueck auf
  stuendlich) schlaegt an.
  **Braucht ein `launchctl bootout`/`bootstrap` des Seiten-Agenten.**

### 20.08.2026 &mdash; Der Verzug des Ensembles war zu guenstig gerechnet (T-0049)
- T-0049 **8,7 h waren eine Einzelprobe, nicht der Verzug.** Andre ist ueber
  die Standzeile gestolpert: "Modelllauf 19.08., 18 UTC &#183; geholt 20.08.,
  11:20 Uhr" - 15,3 Stunden. Nachgemessen am 20.08. um 15:15 UTC:

  | | Initialisierung | verfuegbar | Verzug |
  |---|---|---|---|
  | `ecmwf_ifs025_ensemble` | 20.08. 00z | 20.08. 12:51 | **12,9 h** |
  | `ecmwf_ifs025` (determ.) | 20.08. 06z | 20.08. 13:13 | 7,2 h |

  Das Ensemble ist also deutlich langsamer als der deterministische Lauf
  desselben Modells, und der Verzug schwankt: am 18.08. waren es 8,7 h
  (18z-Lauf), am 20.08. 12,9 h (00z-Lauf). Die Standzeile war damit richtig
  - die Zahlen WAREN 15,3 h alt.
  **Folge fuer die Begruendung von T-0041:** die dort genannten "12 bis 17 h
  Vorlauf" waren mit 8,7 h gerechnet und zu guenstig. Real:

  | Abruf | Lauf | Vorlauf auf SU |
  |---|---|---|
  | alt 07:30, August | 12z des Vortags | 30,4 h |
  | neu 3 h vor SU, August | 00z desselben Tages | 18,4 h |
  | alt 07:30, Dezember | 12z des Vortags | 26,9 h |
  | neu 3 h vor SU, Dezember | 18z des Vortags | 20,9 h |

  Die Umstellung bleibt richtig, sie spart im August zwoelf Stunden - aber
  sie halbiert den Vorlauf nicht, wie ich geschrieben hatte. README
  korrigiert.
  **Und das ist genau der Zweck der Standzeile**: sie hat eine falsche
  Annahme binnen zweier Tage sichtbar gemacht. Waere sie nicht da, stuende
  die 8,7-h-Rechnung weiter unbemerkt in der README.
- **Nebenbefund fuer den Winter.** Bei 13 h Verzug wird der 00z-Lauf gegen
  14:51 Ortszeit verfuegbar. Im Sommer liegt das Abendfenster danach, im
  Winter (12:53) davor - dort benutzen beide Tageslaeufe denselben 18z des
  Vortags. Frueher geht es nicht: bei Sonnenuntergang um 15:53 gibt es
  nichts Frischeres. Kein Handlungsbedarf, aber es erklaert, warum der
  zweite Lauf im Winter nichts beitraegt.


### 19.08.2026 &mdash; Ein verschlafener Tick kostete den ganzen Abendlauf (T-0048)
- T-0048 **Der Abendlauf wird nachgeholt, wenn sein Tick ausfaellt.** Am
  18.08.2026 hat der stuendliche Agent genau den einen Tick verschlafen,
  der ins Abendfenster fiel: im Log stehen 16:20 und 18:20 Ortszeit, der um
  17:20 fehlt (Rechner im Ruhezustand; launchd holt einen verpassten
  Kalendertermin beim Aufwachen nach, aber da war das Fenster laengst zu).
  Ergebnis: kein Abendlauf am ganzen Tag.
  Jetzt: ist das Abendfenster verstrichen und noch nicht bedient, laeuft der
  naechste Tick nach - **bis zum Sonnenuntergang, nicht darueber hinaus**.
  Ein Lauf zwei Stunden vorher ist schlechter als einer drei Stunden vorher,
  aber unvergleichlich besser als keiner. Der Vormittagslauf wird bewusst
  NICHT nachgeholt: er ist Beiwerk, und ein Nachholen kurz vor dem
  Abendfenster brauchte zwei Laeufe in einer Stunde - das traegt das
  Stundenkontingent nicht.
- **Der Altersstreifen hat den Ausfall nicht gemeldet**, und das war der
  zweite Fehler. Er verglich TAG mit TAG; weil am 18.08. vormittags
  gerechnet worden war, stimmte das Datum noch. Die Zahlen waren trotzdem
  einen halben Tag alt. Jetzt wird ZEITPUNKT mit ZEITPUNKT verglichen
  (`stand["geholt"]` gegen das letzte geschlossene Abendfenster), und der
  Streifen nennt beide Uhrzeiten:
  *"Diese Zahlen sind von gestern (18.08., 11:59 Uhr). Der Lauf vom 18.08.,
  17:26 ist nicht durchgekommen."*
  Negativprobe: zurueck auf Tagesvergleich, und der Streifen verschwindet
  wieder - der verschlafene Lauf bliebe unbemerkt.
- **Erzeugte Seiten aus dem Repo genommen.** `web/bewerten-*.html` und
  `web/bisher.html` sind Bauartefakte wie `index.html`. Seit die
  Auslieferung stuendlich laeuft, schreibt der Agent sie staendig neu; die
  Sonnentafel in der Bewertungsseite wandert taeglich um einen Eintrag.
  Gegenprobe vor dem Entfernen: alle drei geloescht, `ausliefern.py
  --trocken` gestartet - sie entstehen vollstaendig neu, Fingerabdruck
  identisch mit dem zuletzt veroeffentlichten.


### 18.08.2026 &mdash; Die Seite zeigte Vergangenheit (T-0046, T-0047)
- T-0046 **Der heutige Abend wurde nie gerechnet.** Die Schleife in
  `alarm.py` begann bei `k = 1`, also bei morgen - der heutige Abend trug
  immer die Zahlen des Vortags. Am 18.08. stand fuer heute noch der Lauf vom
  **16.08.**, also zwei Tage alt. Solange der Lauf morgens um 07:30 lag,
  fiel das kaum auf; seit er drei Stunden vor Sonnenuntergang liegt, ist es
  der Kern der Sache - der frischeste Modelllauf soll GENAU diesem Abend
  gelten. Jetzt `range(0, ...)`, und ein Abend, dessen Sonnenuntergang schon
  vorbei ist, faellt raus.
  **Das relativiert meine eigene Begruendung von heute frueh**: die
  Umstellung auf sonnenuntergangsrelativ hat den Vorlauf fuer *kuenftige*
  Abende halbiert, fuer den *heutigen* aber gar nichts gebracht, weil er
  nicht mitgerechnet wurde.
- T-0047 **Vergangene Abende gehoeren nicht auf die Prognoseseite.** Der
  Zustand sammelt sie, weil dort die Bewertungen haengen - die Seite zeigte
  deshalb am 18.08. den 16. und 17. mit und schrieb "13 ABENDE
  VORAUSGERECHNET &#183; 16.08. BIS 28.08." darueber. Vorausgerechnet waren
  es 11. Jetzt filtert `prognose_eintraege` auf heute und spaeter; der Test
  prueft zusaetzlich, dass die Korpuszeile Anzahl und Spanne der wirklich
  gezeigten Abende nennt.
- **Standzeile: von wann die Wetterdaten sind.** Zwei Zeiten, und sie sind
  nicht dasselbe: `Modelllauf 18.08., 06 UTC &#183; geholt 18.08., 17:26 Uhr`.
  Der Modelllauf ist die Initialisierung des ECMWF-Laufs, auf dem die Zahlen
  beruhen; das Abrufen nur der Moment, in dem wir sie geholt haben.
  `alarm.modelllauf()` liest ihn aus `meta.json` - eine statische Datei, die
  nicht aufs Kontingent zaehlt. Nebenbefund dabei: der Verzug zwischen
  Initialisierung und Verfuegbarkeit ist NICHT konstant 8,7 h wie am
  Vormittag aus einer einzigen Probe geschaetzt - um 13:00 war der 06z-Lauf
  schon da, also rund 5 h. Die Standzeile macht das kuenftig beobachtbar,
  statt es schaetzen zu muessen.


### 18.08.2026 &mdash; Zweiter Lauf (T-0045), Kontingentgrenzen vollstaendig
- T-0045 **Zweiter Alarmlauf am Vormittag.** Fenster `morgens` um 09:20 UTC,
  kurz nachdem der 00z-Lauf verfuegbar wird (08:44 UTC, gemessen); das
  bisherige sonnenuntergangsrelative Fenster heisst jetzt `abends`.
  `zustand[ort]["laeufe"][tag]` ist von einer Zeichenkette auf
  `{fenster: zeit}` umgestellt; der alte Eintrag blockiert nichts (im Test
  abgedeckt).
  **Kein zweiter Push:** je Abend hoechstens ein Alarm, das haelt
  `zustand["alarme"]` fest. Der Vormittagslauf bringt aktuelle Zahlen auf
  die Seite und meldet einen Abend ueber der Schwelle frueher.
  Im Winter benutzen beide denselben 00z-Lauf - bewusst hingenommen, eine
  Sonderregel waere mehr Code als Nutzen.
  `test_lauffenster.py` prueft jetzt ueber ein Jahr, dass JEDER Tag genau
  einmal `morgens` und einmal `abends` traegt, und dass die Fenster sich nie
  naeher kommen als ihre Breite. Negativprobe: `lauf_morgens_utc` auf 12:00
  kostet 97 Abendlaeufe.
- **Kontingent vollstaendig vermessen.** Frei: 600/min, 5.000/h, 10.000/Tag
  und **300.000/Monat**. Zwei Laeufe taeglich sind rund 210.000 im Monat -
  es passt, ohne viel Luft.
  Ein Abo waere **Professional**, nicht Standard: die Ensemble-API ist in
  Standard ausdruecklich nicht enthalten (Preistabelle und FAQ auf
  open-meteo.com/en/pricing). Preis laut Open-Meteos eigenem Blog vom
  12.06.2023: Standard 29 USD, Professional 99 USD im Monat. Die aktuelle
  Tabelle laedt ueber ein Stripe-Widget und war hier nicht auslesbar - die
  Zahl ist also drei Jahre alt und vor einer Entscheidung nachzusehen.


### 18.08.2026 &mdash; Lauf ans Ereignis geruecht (T-0041), Kontingent gemessen
- T-0041 **Der Alarmlauf ist sonnenuntergangsrelativ statt fest um 07:30.**
  Zwei Messungen dahinter:
  1. **Frische.** ECMWF ENS rechnet viermal taeglich, die Daten sind erst
     8,7 h nach Initialisierung abrufbar (`meta.json`, gemessen). Um 07:30
     war der 18z des Vorabends der juengste Lauf: 21-24 h Vorlauf. Drei
     Stunden vor Sonnenuntergang sind es 12-17 h, ganzjaehrig.
  2. **Kontingent.** Ein vollstaendiger Lauf = ~10 Anfragen ueber 216
     Ortsabrufe, danach ist das Stundenbudget (5.000) leer; das Tagesbudget
     (10.000) traegt GENAU ZWEI Laeufe. Es gibt also keinen Zweitlauf zur
     Sicherheit - der eine muss sitzen, also liegt er so spaet wie moeglich.
  Keine feste Uhrzeit, weil der Sonnenuntergang in Berlin um mehr als
  fuenfeinhalb Stunden wandert (21:33 im Juni, 15:53 im Dezember) - 17:00
  laege im Dezember hinter dem Ereignis. Stuendlicher Agent mit
  `--geplant`, Entscheidung in `alarm.im_laufenster()`; dasselbe Muster wie
  bei der Erinnerung.
  Mitgezogen: `ausliefern.py` laeuft stuendlich und pusht nur bei
  Aenderung (Fingerabdruck der gebauten Seiten); die Altersregel der Seite
  vergleicht nicht mehr gegen "heute", sondern gegen das letzte
  GESCHLOSSENE Laufenster - sonst stuende der Warnstreifen jeden Tag bis
  nachmittags da und wuerde nicht mehr gelesen.
  `skripte/test_lauffenster.py` (neu) prueft ueber ein ganzes Jahr, dass je
  Tag genau ein Termin ins Fenster faellt. Negativprobe gemacht: Fenster
  auf 30 min verengt -> 168 Tage ohne Lauf; auf 150 min geweitet -> 365
  Tage mit zwei Laeufen. Beides schlaegt an.
  **Braucht ein `launchctl`-Nachladen beider Agenten** (siehe STATE).
- T-0044 **`cp` plus `kickstart` laedt eine plist NICHT nach.** Am
  18.08.2026 stand die neue Definition in `~/Library/LaunchAgents`, launchd
  kannte aber weiter die alte: `launchctl print` zeigte `Hour 7, Minute 30`
  und keine Argumente. `kickstart -k` startet den Job mit der GELADENEN
  Definition neu, nicht mit der Datei - der Alarm lief deshalb mittags ohne
  `--geplant` los und ignorierte sein Zeitfenster. Richtig ist
  `bootout` + `bootstrap`, mit `launchctl print` als Gegenprobe. In README
  und STATE korrigiert; die alte Anleitung stammte von mir.
  Nebenbei hat der Fehllauf etwas Gutes gezeigt: er ist mit dem billigeren
  Abruf **durchgelaufen** - 10 Anfragen, 217 Ortsabrufe, nur drei
  Minutenlimit-Pausen, 13 Abende im Zustand. T-0042 wirkt also im Betrieb.
- T-0043 **Bewertung datiert nach dem letzten Sonnenuntergang.** Die Seite
  entschied bis heute nach der Uhr: "vor 04:00 zaehlt der Abend als
  gestern". Am 18.08.2026 um 04:26 hat Andre den Sonnenuntergang des 17.
  bewertet - die Regel hat daraus den 18. gemacht, also einen Abend, der
  noch gar nicht stattgefunden hatte. Jede feste Uhrzeit liegt irgendwann
  schief: SU 21:33 im Juni, 15:53 im Dezember.
  Jetzt: `bewertungsseite.py` bettet eine Sonnentafel ein, die Seite waehlt
  den letzten VERGANGENEN Sonnenuntergang. Dazu ein Riegel in
  `bewertungen_holen.py` - eine Bewertung fuer einen Abend, dessen
  Sonnenuntergang noch aussteht, wird verworfen und im Log benannt.
  Bewusst an beiden Stellen: die Seite kann im Cache veralten, der Poller
  nicht. Live geprueft, der Poller verwirft die Nachricht jetzt.
  Der falsche Eintrag ist auf den 17.08. umgebucht, mit `bewertung_korrektur`
  am Datensatz - warum umgebucht wurde, steht am Datum selbst.
- T-0042 **Wind nur noch am Ort geholt.** Der Lauf holte die sechs
  Windvariablen fuer alle 68 Faecherzellen, gelesen werden sie
  ausschliesslich am Heimatpunkt - der Advektionsversatz ist ein
  Ensemble-Mittelwind je Schicht, kein Feld. Und Open-Meteo zaehlt
  Ensemble-Member wie zusaetzliche Variablen, 9 x 51 wiegt dreimal so viel
  wie 3 x 51. Kosten vorher rund 5.500 Einheiten (Stundenlimit 5.000, riss
  bei der vorletzten Anfrage), jetzt rund 3.500.
  `skripte/test_abruf.py` (neu) fuehrt den echten Ablauf mit erfundenen
  Daten aus und prueft BEIDES: dass gespart wird UND dass die Advektion
  weiter greift - ein Lauf, der billiger ist und dabei still die Advektion
  abschaltet, saehe sonst erfolgreich aus. Negativprobe: Wind wieder fuer
  alle Zellen -> drei Pruefungen schlagen an; Wind gar nicht geholt -> die
  eingebaute Gegenprobe nennt die fehlenden Variablen (ohne sie gaebe es
  einen nackten IndexError tief in der Advektion).
- **Buchhaltung in `alarm.py`**: jede Zeile im Log traegt jetzt eine
  Uhrzeit, und der Lauf meldet Anfragen, Ortsabrufe, Variablen, Tage und
  Member. Ohne das war jede Erklaerung der Kontingentfehler eine Vermutung
  - der Log hatte nicht einmal eine Uhr.


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
