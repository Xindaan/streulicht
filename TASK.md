# TASK

Sonnenuntergangs-Alarm Berlin. Bis zu zehn Abende voraus eine Wahrscheinlichkeit
fuer einen aussergewoehnlichen Sonnenuntergang melden - belastbar ab etwa ein
bis drei Tagen, weiter voraus nur Tendenz (T-0085).

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
- [x] `skripte/test_wn3.py` - Stand 09.10.2026: 55 Pruefungen, 14
      Negativproben, alle gruen und netzfrei (vorher stand hier "18 + 5";
      gezaehlt waren schon vor dem Review 35 + 8, wn3#F10). Einheit km/h
      und Zielzeiten mit Minuten sind seit T-0083 abgedeckt.
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
      **Nachtrag 09.10.2026 (Review methodik#F8):** Die Begruendung "Album
      2014 bis 2022" ist falsch. Das Album umfasst 81 Fotos an 80 Abenden
      von 2014-10-07 bis 2026-06-28 (2023: 14, 2024: 11, 2025: 7, 2026: 6). s* stammt
      ohnehin nicht aus dem Album, sondern ist das 95. Perzentil der
      Klimatologie. Der Ausweg (Quantilabbildung) steht schon oben und bleibt
      richtig; falsch war nur die Begruendung. Fuer 2026 enthaelt die
      Klimatologie nur 40 Abende; der Kontingentbedarf zum Nachholen ist
      UNBELEGT. (Gleiche Begruendung in STATE.md "Album (2014-2022)"; dort am 09.10.2026
      nachgezogen.)
- [x] **s* fuer WN3: Verfahren geklaert und gebaut (04.11.2026).**
      `skripte/wn3_quantil.py`: q = Anteil der Referenzabende unter s*,
      s*_WN3 = Quantil der WN3-Scores bei q, an DENSELBEN Abenden; gepaarter
      Bootstrap (90 %); unter 10 Referenzereignissen ueber s* wird die Zahl
      als PLATZHALTER ausgegeben. WN3-Seite: Score des p50-Feldes, Lauf 6 h
      vor der Sonnenuntergangsstunde (analysenah wie die Referenz), Cache
      `daten/wn3_p50/berlin.json`. `skripte/test_wn3_quantil.py` 8 Pruefungen,
      vier Mutanten (q mit <=, Quantil aus der Referenz, q umgedreht, ohne
      Laengenpruefung) je rot genau an ihrer Pruefung.
      Gemessen: 75 MB und ~27 s je Abend, kostenlos; Vollabruf 01.01.-02.11.
      laeuft (Log `daten/wn3_quantil.log`).
- [x] **Referenzseite 2026 nachholen - der eigentliche Engpass.** Die
      Klimatologie hatte fuer 2026 nur 40 Abende. **Freigegeben 04.11.2026
      (Maintainer): ein Block je Tag.** `klimatologie.py` kann jetzt
      `--bis-datum` (Teiljahr, eigene Cache- und Teil-Dateinamen) und
      `--max-bloecke` (Blockdeckel, gleicher Ausstieg wie beim Kontingent);
      `test_klima_teiljahr.py` 7 Pruefungen, drei Mutanten je rot.
      116 Zellen = zwei Bloecke, geschaetzt je hoechstens 1.310 Einheiten
      (Formel unbelegt); Alarmlaeufe 03.11. je 208 Orte = rund 3.200.
      - [x] Block 1 am 04.11. 08:39 (vor dem Lauf 10:20): 60 Zellen,
            305 Tage, keine Luecke.
      - [x] Block 2 am 05.11. 09:00 (geplante Aufgabe; `alarm.log` heute
            ohne "Kontingent"/429): 56 Zellen nachgeholt, 116/116.
            `daten/score_berlin_g0.5_2026_2026_bis20261101.json`: 305 von 305
            Abenden (01.01.-01.11.), 305 `s`-Werte, keine Teildatei.
            Auswertung `skripte/wn3_quantil.py` (WN3-Cache 306 Abende):
            305 gepaarte Abende, 14 Referenzabende ueber s* = 0,7065,
            q = 0,9541, **s*_WN3 = 0,7144, 90-%-Intervall [0,6293; 0,8364]**
            (kein PLATZHALTER, Mindestzahl 10). Zum Vergleich: am 08.09.2026
            lag WN3 im Mittel +0,135 hoeher (n = 11); im oberen Quantil
            liegt die Schwelle nur +0,008 ueber ECMWF.
- [ ] **Entscheidung Maintainer: traegt s*_WN3 = 0,7144?** 14 Ereignisse,
      Intervall 0,63-0,84 (Breite 0,21). Erst danach Betriebsvehikel und
      zweiter Weg in `alarm.py` (unten).
- [x] ~~Je Lauf das WN3-Medianfeld mitschreiben~~ - **Praemisse widerlegt
      04.11.2026:** das Statistik-Bucket haelt alle Laeufe seit 01.01.2026,
      stuendlich, 7.368 Laeufe bis 03.11. (gemessen per Listing). Die
      Ueberlappung waechst auf der WN3-Seite von selbst; der Engpass ist die
      Referenz (siehe oben). Restrisiko: Aufbewahrungsregel des Buckets
      unbekannt - der Cache von `wn3_quantil.py` sichert die Scores.
- [ ] Betriebsvehikel - nur falls der Vergleich dafuer spricht: e2-micro
      (Freikontingent nach Instanzstunden, langsam) gegen Cloud Run Job
      (schnell, Freikontingent knapp). Compute Engine ist in
      `gardena-wetter` noch gar nicht aktiviert, die freie e2-micro also
      unangetastet.
- [ ] Uebergabe: kleines Bucket in `gardena-wetter`, Mac zieht die JSON
- [ ] `alarm.py`: zweiter Weg neben `abfrage()`, gesteuert ueber `modell`
- [ ] Zeitbudget echt messen statt hochrechnen (meine 1,5-2,5 h je Lauf
      sind eine Schaetzung vom Mac aus, keine Messung auf der Instanz)

- [ ] **Review 09.10.2026, bewusst NICHT umgebaut (T-0083), erst bei der
      Verdrahtung bzw. vor einer Entscheidung auf Basis der Zahlen:**
      - wn3#F6: Der Zuschnitt (a) kennt die ~300 stromauf versetzten
        Pass-2-Zellen von `alarm.py` nicht; fehlende Zellen fallen in
        `score()` still heraus (Gewichte werden renormiert). Die Zahl
        "68 Zellen" in `wn3.py` ist veraltet (Log: 72).
      - wn3#F1: Der Vergleich misst den Score des Medianfeldes, nicht den
        Median der Memberscores; "reisst s*" ist nur eine Naeherung.
      - wn3#F2: ECMWF-Seite des Vergleichs liegt auf dem vergroeberten
        0,5-Grad-Faecher, WN3 auf echten 0,1-Grad-Punkten; die Differenz
        +0,135 enthaelt ungemessene Anteile aus Vergroeberung und Advektion.
      - wn3#F3: r = 0,868 bei n = 11 (95-%-Intervall 0,56 bis 0,97) und
        "8 von 11" (einseitig p = 0,11) tragen "systematisch hoeher" nicht.

## Next

### T-0089 Namens-Leak im public Repo: Rest und Historie (04.11.2026)
Aktueller Stand bereinigt (Klarname -> "Maintainer", Home-Pfad -> `~`), Guard
`tools/public_push_guard.sh` als pre-push aktiv (README "Pre-Push-Guard").
Offen, je eine Entscheidung des Maintainers:
- [x] Historie: 146 Commits, 38 Pfade in alten Commits und 48 Message-Zeilen
      tragen den Klarnamen. **ENTSCHIEDEN 04.11.2026 (Maintainer): bleibt wie
      sie ist** - kein Rewrite, kein force-push, keine Neuanlage. Umschreiben
      haette alte SHAs bei GitHub ohnehin abrufbar gelassen.
- [x] Betriebsbezeichner: **ENTSCHIEDEN 04.11.2026 (Maintainer): B.**
      Ersetzt: Notendatei heisst `daten/bewertung_maintainer.json` (Datei
      umbenannt, Lesepfade in fensterterm.py, icond2_test.py, satellit.py,
      wegterm.py; kein Schreiber im Code, Datei seit 14.08. unveraendert);
      Commit-Adresse der Pages-Auslieferung `noreply@streulicht.invalid`
      (`.invalid` ist reserviert, kann keinem GitHub-Konto zufallen).
      **Bewusst belassen:** Home-Pfade in `betrieb/*.plist` und die
      launchd-Labels mit Privatdomain - Umstellen hiesse Agenten neu laden
      (bootout/bootstrap). Der Guard duldet Home-Pfade nur dort und blockt
      den Klarnamen jetzt auch in Bezeichnern (`_name`).

### T-0088 Restpunkte aus dem Review-Block ohne eigene Task-ID (21.10.2026)
Beim STATE-Snapshot gesammelt; bisher standen sie nur in STATE-Stand-Zeilen.
- [ ] 44-px-Tippziele der Abendachse (Rest von T-0080)
- [ ] bewertung#4: fehlende Umbuchung 18.08. -> 17.08. (T-0077)
- [ ] Q fuer "auffaellig" neu messen, Winter/Fruehjahr 2026/27 (T-0084)
- [ ] Cache-Teilung des Nachtlaufs im `alarm.log` nachzaehlen, ab ca. 23.10. (T-0087)

### T-0007 Gelaende in den Fensterterm
DEM-Freigaengigkeit des Strahls. Ab freier Ortswahl zwingend, nicht optional
(Muenchen im Dezember: Alpen bei 250 km, Strahl bei 1,22 km).

### T-0008 Dispersion und Skill ueber Vorlauf
Rangdiagramm des Scores; Korrelation Ensemble-Median gegen Kurzfrist-Score
je Vorlaufstufe. BSS erst, wenn genug Archiv da ist (T-0003).

## Backlog

### Befunde aus dem Aufraeumlauf vom 21.11.2026 (T-0090 bis T-0096)
Lesepass ueber den ganzen Code, danach selbst nachgemessen, was sich
ausfuehren liess. Behoben ist, was belegbar war und nicht auf dem Versand-
oder Push-Pfad liegt (Branch `aufraeumen-fable-2026-11`). Die folgenden
Punkte sind bewusst NUR Befund: Versand-, Push- und Schwellenpfade, oder
ohne Messung nicht entscheidbar. Zeilen beziehen sich auf den Stand des
Branches; `alarm.py`, `erinnerung.py`, `ausliefern.py` und `tools/` sind dort
unveraendert.

### T-0090 Versandpfad: Alarm kann doppelt gesendet oder still verschluckt werden (21.11.2026)
Nur gelesen, nicht reproduziert (jeder Beleg braeuchte einen Test mit
erfundenem Netz auf dem Versandpfad). Latent, solange nur ein Ort konfiguriert ist.
- [ ] `alarm.py:1392-1400`, `:784`, `:1563`: Ort 1 sendet (`:1473`) und haelt
      den Alarm nur im Speicher; bricht danach Ort 2 am Kontingent oder am
      fehlenden Wind ab, laeuft `aktualisiere()` nie - der naechste Lauf
      sendet Ort 1 noch einmal. Akzeptanz: Test mit zwei Orten, zweiter wirft
      `Kontingent`; nach dem Lauf steht der Alarm von Ort 1 im Zustand.
- [ ] `alarm.py:1297-1300`, `:1447`: "je Abend hoechstens ein Alarm" prueft
      gegen den Stand vom Laufbeginn, gelesen ohne Sperre; ein Handlauf neben
      dem Agentenlauf sendet doppelt.
- [ ] `alarm.py:1473`: fehlt `ntfy_alarm` in `konfig_geheim.json`, wird der
      KeyError als "Push FEHLGESCHLAGEN" geloggt, Exitcode 0, jeder Lauf
      erneut; `erinnerung.py:144-148` hat dafuer einen Rueckfall mit Warnung.
- [ ] `alarm.py:1286-1290`: kaputte `konfig_geheim.json` beendet den Lauf vor
      jeder Rechnung (`erinnerung.py:112-128` faengt denselben Fall ab).
- [ ] `alarm.py:1043-1053` und `erinnerung.py:151-158`: zwei Sendefunktionen,
      der Titel-Header ist verschieden kodiert (latin-1-Ersatz gegen UTF-8).
- [ ] `alarm.py:1302`, `erinnerung.py:177`: `--jetzt` mit Offset wird
      ueberschrieben statt umgerechnet. Gemessen: `2026-07-01T20:00+02:00`
      wird zu `20:00+00:00` (`fromisoformat(...).replace(tzinfo=utc)`).
- [ ] `alarm.py:1406`, `:1447`, `:1518`, `:1538`: `setdefault` greift nur,
      wenn der Ort ganz fehlt; ein Ortseintrag ohne `alarme` gaebe KeyError.

### T-0091 Push-Pfad: Guard laesst bei technischem Fehler durch, Auslieferung ohne Prognoseseite (21.11.2026)
- [ ] `tools/public_push_guard.sh:91`, `:98-100`, `:119`: `git grep ...
      2>/dev/null | head -25 || true` macht einen git-grep-Fehler
      ununterscheidbar von "kein Treffer". Gemessen: `git grep -nIE '(' HEAD`
      endet mit Exitcode 128 ("unmatched ( for expression group"), der
      Treffertext ist leer - der Guard meldete "sauber". Der Kopf (`:10-11`)
      verspricht das Gegenteil. Dieselbe Form bei `git rev-list ... || neu=""`
      (`:50`, `:57`): schlaegt die Bereichsbestimmung fehl, wird nichts
      geprueft. Akzeptanz: Guard mit `LM_HART_RE='('` gegen einen
      Wegwerf-Remote verweigert den Push.
- [ ] `tools/public_push_guard.sh:85-91`, `:109`: je Commit der ganze Baum
      statt des Diffs; Aufwand waechst mit Commits x Dateien.
- [ ] `ausliefern.py:204-211`, `:243-256`: `gh-pages` wird mit genau den
      Seiten neu geschrieben, die in `web/` liegen. Fehlt `web/index.html`
      (frischer Klon; die Datei ist gitignoriert), wird trotzdem gepusht und
      die Prognoseseite ist aus dem Netz. Abbruch nur bei ganz leerer Liste.
- [ ] `ausliefern.py:224-228`: der Fingerabdruck hasht nur Inhalte, keine
      Dateinamen. `:257-258`: der Stempel wird nicht atomar geschrieben.
- [ ] `ausliefern.py:85`, `:315`: Parameter `trocken` von `baue()` ungenutzt,
      Rueckgabe `prognose` verworfen. `:219` ("Seit der Agent stuendlich
      laeuft ... 24 Force-Pushs am Tag") ist falsch: der Seiten-Agent laeuft
      alle 10 Minuten (`betrieb/...seite.plist`, 144 Termine), `:48` sagt es
      richtig.

### T-0092 Alarmkern: Deckel 320 gegen 200, UTC- gegen Ortsdatum, Dopplungen (21.11.2026)
- [ ] `alarm.py:648-660`: der Kommentar begruendet `PASS2_MAX_ZELLEN = 320`
      ("ein Deckel unter 320 wuerde schon viele Oktoberlaeufe beschneiden");
      der Betrieb faehrt seit 13.10. mit `pass2_max_zellen: 200`
      (`konfig.json:16-17`). Faellt der Schluessel weg, gilt still 320.
      Entscheidung: Default und Begruendung an 200 angleichen oder den
      Rueckfall streichen.
- [ ] `alarm.py:707`, `:1428` (UTC-Datum) gegen `:1071`, `:1495`, `:1517`
      (Ortsdatum): Abendliste und Verlaufszeile gegen `laeufe` und Archivname.
      Zwischen 22:00 und 24:00 UTC meinen beide verschiedene Tage; ob ein
      Lauffenster dort liegen kann, ist nicht gemessen.
- [ ] `alarm.py:776-784`: der Wind wird immer geholt und sein Fehlen bricht
      immer ab, auch bei `advektion: false`.
- [ ] Dopplungen: Faecherpunkte `alarm.py:740-745` und
      `sonnen/score_niveaus.py:212-217` neben `sonnen/score.py:87-97`;
      Sonnenuntergang als UTC-Zeitpunkt siebenmal (`alarm.py:733`,
      `:792-793`, `:1078`, `:1196-1197`, `erinnerung.py:65-66`, `:90-91`,
      `bewertungen_holen.py:127-128`); Zustand lesen `alarm.py:1297-1300`
      neben `zustandsdatei.lade`; atomar schreiben `sicherung.py:49-64` ohne
      Verzeichnis-fsync neben `zustandsdatei.py:33-64`.
- [ ] `zustandsdatei.py:44`: fester tmp-Name; Archiv (`alarm.py:174`) und
      Blockcache (`:520`) schreiben ohne Sperre - zwei gleichzeitige Laeufe
      teilen sich die tmp-Datei (Verdacht, nicht reproduziert).
- [ ] Kommentare in `alarm.py`, die dem Code widersprechen: `:6` (Wind "an den
      Fanpunkten", geholt wird nur die Heimatzelle `:748-777`), `:926`/`:934`
      ("bester Member", seit T-0064 der Median `:576-588`), `:1412`
      (`alt = ...` wird nie gelesen); `erinnerung.py:15-16` ("vier Stunden"
      gegen "fuenfeinhalb" in `alarm.py:1063-1064`), `:35`/`:37` (`urllib.parse`,
      `date` ungenutzt).

### T-0093 Seiten: Widersprueche, die eine Entscheidung brauchen (21.11.2026)
- [ ] `web/bewerten.html:423` zeigt "0 % Wahrscheinlichkeit", die
      Prognoseseite fuer denselben Abend "< 6 %" (`seite.py` `wahrsch_text`);
      `bewertungsseite.prognosestand()` gibt `n_member` nicht mit.
- [ ] "Bester Abend im Fenster" (`seite.py`, `max(..., key=...["p"])`) waehlt
      nach dem Perzentil des Medians, die Stufe seit T-0084 nach dem Anteil
      der Modelllaeufe: ein "unauffaelliger" Abend kann "Bester Abend" heissen.
- [ ] Prognoseseite ueberspringt Abende ohne `p` ODER ohne `median`, die
      Bewertungsseite nur ohne `median` (`bewertungsseite.py:65`). Im
      Zustand vom 21.11. kommt der Fall nicht vor (76 Abende, 0 mit median
      ohne p).
- [ ] Drei Zeitzonen-Quellen auf einer Seite: fest `Europe/Berlin`
      (`lokalzeit`), Zone des Rechners (`astimezone()` in der Standzeile),
      Zone aus der Konfig (Veraltet-Streifen); dazu `date.today()`. Gehoert
      zur Ein-Ort-Grenze (T-0071).
- [ ] `stil/tokens.css`: ohne Leser im Repo sind `--linie`, `--gitter-schwach`,
      `--radius-tafel`, `--schatten-hover`, `--schatten-leiste`,
      `--zeit-schnell`, `--breite`, `--breite-schmal`, `--breite-bild`,
      `--s1` bis `--s7`; `:48` nennt eine Klasse `.achse-karte`, die es nicht
      gibt. `seite.py` schreibt Token-Farben an sechs Stellen als feste
      `rgba(...)`, `bisher.py` die Breite 720px. Vokabular oder Ballast?
- [ ] `seite.py`: META traegt `wahrsch` und `vorlauf_h` in jede Seite, das
      Seitenskript liest sie nicht; CSS-Regel `.nurklein` ohne Element.
      `web/bewerten.html:174`: Konstante `ANZEIGE` unbenutzt, der Platzhalter
      wird trotzdem gefuellt und geprueft.
- [ ] `rueckschau.py`, `diagnose.py`, `absicht.py`: kein Aufrufer. Die ersten
      beiden schreiben nicht atomar und mit eigenen Farben;
      `rueckschau.py:101` beschriftet den Filter fest mit "0,63", gefiltert
      wird mit s* aus der Konfig. Behalten als Handwerkzeug oder streichen?
- [ ] `seite.py --rueckschau` schreibt nach `web/index.html`, also ueber die
      Prognoseseite (gemessen im Sandkasten); im Betrieb ueberschreibt der
      naechste Tick sie wieder.

### T-0094 Analyse- und Abrufskripte: Fehler und Dopplungen ohne Testdeckung (21.11.2026)
Keines dieser Skripte hat einen Test, die meisten brauchen Netz und
Kontingent; deshalb nur Befund. Importe gegen `sonnen/` geprueft: kein Bitrot.
- [ ] `wn3.py:43`: Vorgabe fuer das Abrechnungsprojekt ist `"gardena-wetter"`
      - Name eines anderen Projekts, im public Repo. Entscheidung Maintainer.
- [ ] `era5_nachtrag.py:169-170` schreibt die Klimatologie nicht atomar
      (dieselbe Datei schreibt `klimatologie.py` atomar, T-0051);
      `:106-113` cacht leere Ergebnisse dauerhaft.
- [ ] Cache-Schluessel ohne Ort oder Zeitraum: `ablation.py:71`,
      `klimatologie.py` (Blockname ohne `--breite/--laenge`),
      `era5_nachtrag.py:83`.
- [ ] `daten/bewertung_maintainer.json`: vier Leser (`fensterterm.py`,
      `icond2_test.py`, `satellit.py`, `wegterm.py`), kein Schreiber.
- [ ] Verdacht auf Absturz bei Randfaellen: `fensterterm.py:520-526` (None in
      der Rangkorrelation), `wegterm.py:162`/`:200`/`:240`/`:246`,
      `termanalyse.py:54`/`:82`/`:90` (Nullnenner), `aerosol.py:44-50` (jeder
      HTTP-Fehler heisst "Kontingent").
- [ ] Feste Messwerte im Ausgabetext: `auswertung.py:140` ("0 von 124"),
      `abbruchtest.py`; `icond2.py:59-61` Kommentar 9/s, Code 7/s.
- [ ] "ERA5" als Name fuer die IFS-Analysen steht noch in den Docstrings
      von `icond2_test.py`, `diagnose.py`, `kalibriere_eis.py` und den
      Abbruchtests (`klimatologie.py` ist angeglichen).
- [ ] Dopplungen: Spearman viermal mit vier Randverhalten (`ablation.py`,
      `icond2_test.py`, `termanalyse.py`, `fensterterm.py`); Tag-im-Jahr,
      Rang und das +-21-Tage-Fenster sechsmal (das Fenster trifft Tag 366
      nie); HTTP-Abruf mit 429-Behandlung sechsmal; Zelle/Zellmitte viermal;
      Foto-Hilfen in `fotos_zaehlen.py` und `fotos_detail.py`; Satelliten-
      Download in `satellit.py` und `oberkante.py`.
- [ ] Drei Anlaeufe nebeneinander: `abbruchtest.py` -> `abbruchtest2.py` ->
      `albumtest.py`; `kalibriere_eis.py` (laedt) / `kalibriere_eis2.py`
      (wertet aus). Ohne jede Referenz im Repo: `abbruchtest2.py`,
      `aerosol.py`, `era5_nachtrag.py`, `fotos_spotlight.py`, `oberkante.py`,
      `termanalyse.py`. Archivieren oder behalten?
- [ ] `icond2.py:146-147`: ein HTTP-Aufruf je Zelle, die anderen Abrufe
      buendeln 40-60 Orte je Anfrage.

### T-0095 Tests: Geruest, Betriebsdaten, schwache Proben (21.11.2026)
- [ ] Die Tests brauchen gitignorierte Betriebsdaten: im nackten Worktree
      sind 4 von 32 Dateien rot und 3 enden mit Code 2 (gemessen 21.11.);
      `test_grib2.py` ueberspringt still (5 statt 12 Pruefungen);
      `test_seiten_atomar.py:71` haengt das echte `daten/` per Symlink ein.
      Der verify-Skill umgeht das mit einem Schnappschuss. Offen: ein
      kleiner, getrackter Testdatensatz.
- [ ] `test_wn3.py:520-534`: `negativ()` wertet JEDE Ausnahme als "schlaegt
      an", auch einen Tippfehler in der Probe.
- [ ] Quelltext statt Verhalten: `test_score_distanz.py:102-106`,
      `test_logbuch.py:171-192`, `test_seiten.py` (Zeichenketten im JS).
- [ ] `test_advektion.py:51-52`: reine Arithmetik, zaehlt als Pruefung.
- [ ] Geruest kopiert: `pruefe()` in 29 Dateien (drei Ausgabeformen), das
      erfundene Netz in `test_ausfall.py` und `test_kontingent.py`,
      `basis_mit()`/`baue()` in `test_frische.py`, `test_ui_paket.py`,
      `test_stufen.py`; `test_abruf.py` dient fuenf Tests als Bibliothek.
- [ ] Temp-Verzeichnisse ohne Aufraeumen: `test_advektion.py`,
      `test_bewertung_nutzlast.py`, `test_bewertungen_holen.py`,
      `test_erinnerung.py`, `test_klima_teiljahr.py`.
- [ ] Uhr: gemessen mit verstellter Prozessuhr (time.time, datetime.now,
      date.today), 15 uhrabhaengige Testdateien (am 21.11. dazu
      `test_seiten.py`), jede volle Stunde: am 21.11.2026 sowie an sechs
      kuenftigen Tagen (Jahreswechsel, beide Zeitumstellungen 2027,
      Sonnenwende, 29.02.2028; 2.160 Laeufe) kein einziger roter Lauf, jede
      Datei mit derselben Pruefzahl. Rueckwaerts gestellt (29.03.
      und 21.06.2026, also vor dem Projektstart) sind zwei Dateien zu jeder
      Stunde rot: `test_bewertung_nutzlast.py` (Ursache: `ERSTER_ABEND`
      15.08.2026 in `bewertungen_holen.plausibel`) und `test_frische.py`
      (Ursache nicht untersucht). Vorwaerts tritt das nicht auf.
      Offen bleibt die Lastabhaengigkeit von `test_ausliefern.py:73-80`
      (echte Zeitmessung).

### T-0096 README: Widersprueche und Aufbau (21.11.2026)
Die README ist Text des Maintainers; richtiggestellt sind nur einzelne
Tatsachen. Offen:
- [ ] Kontingent an fuenf Stellen mit teils ueberholten Zahlen (Abschnitte
      "Was die Grenze kostet", "Zweitens das Kontingent", "Kontingent
      beachten", "429 ist nicht gleich 429", Troubleshooting: "210 Zellen",
      "zwei bis drei Laeufe").
- [ ] "97 Abendlaeufe" als Preis der 12:00-Gegenprobe ist im Repo nirgends
      belegt.
- [ ] Quickstart verlangt ueberall den venv-Pfad, fuenf spaetere Befehle
      nennen blankes `python3`.
- [ ] Abschnitt "## Stand" am Ende traegt den 09.10.2026 ("wird in T-0074
      bis T-0083 abgearbeitet"); der Block ist seit 13.10. erledigt.
- [ ] "Kein Test fasst Betriebsdaten an ... alle im Temp-Verzeichnis"
      stimmt fuer das Schreiben; gelesen werden `daten/` und `web/` von
      sieben Testdateien (siehe T-0095).
- [ ] Korrekturgeschichte im Text ("erste Fassung", "bis zum 04.09. stand
      dort") statt des Stands; "Betrieb" und "Satellitenwahrheit" stehen
      zwischen Konfiguration und Troubleshooting.

- T-0001 Fotoarchiv-Gate (aus Doing nach Backlog verschoben 09.10.2026,
  Review architektur#1 / T-0082). Vermerk: Der Doing-Text meldete BLOCKIERT
  (macOS-TCC), der Done-Eintrag vom 14.08.2026 meldet den Abbruchtest als
  gelaufen (Ergebnis unentschieden wegen konfundiertem Label). Ob der
  Zugriffsblock heute noch besteht, ist nicht gemessen; die Fortfuehrung
  laeuft ueber T-0001b in Doing. Urspruenglicher Text:
  Zaehlen, wie viele geotaggte Abendfotos (SU ±30 min) in der Mediathek liegen.
  Entscheidet, ob der Presence-Only-Abbruchtest aus E0 existiert.
  **BLOCKIERT:** macOS-TCC verweigert den Zugriff. Braucht Festplattenvollzugriff
  fuer die Terminal-App in den Systemeinstellungen.
  - [ ] n >= 40 komfortabel, n >= 20 grenzwertig, darunter faellt der Test aus
  - Skript: `skripte/fotos_zaehlen.py`

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
  aufgefallen ist es erst, weil Maintainer auf die Seite geschaut hat. `launchctl
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

  **Zugang ist da** (Google-Freischaltung 14.08.2026, Maintainers Google-Konto;
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

Aeltere Done-Eintraege (vor 2026-10-01): `docs/task_done_bis_2026-Q3.md`.

### 21.11.2026 &mdash; Aufraeumlauf (Branch `aufraeumen-fable-2026-11`)

Lesepass ueber den ganzen Code, Befunde nachgemessen, belegbare behoben;
alles andere steht als T-0090 bis T-0096 im Backlog. Jede Aenderung lief vor
dem Commit durch `.claude/skills/verify` (Bau im Sandkasten + alle Tests),
jeder Fix hat eine Negativprobe im Wegwerf-Worktree.
- verify-Skill: ein Befehl baut die Seiten aus einem Schnappschuss der
  Betriebsdaten und faehrt alle Tests, ohne Netz und ohne Push.
- Fehler: "EIN ABENDE" auf der Prognoseseite; ein Ort ohne `name` kippte alle
  Bewertungsseiten (KeyError); eine ntfy-Nachricht ohne `time` oder eine
  JSON-Zeile, die kein Objekt ist, riss den Notenabruf ab und verwarf die
  guten Noten derselben Antwort; `ablation.py` druckte bei leerer Menge
  nichts statt "-".
- Tests: `test_phantomnullen` pruefte eine Kopie des Klimatologie-Rumpfs
  (blieb gruen, wenn der Riegel in `klimatologie.py` fehlte) - jetzt
  `klimatologie.buche_abend()` selbst; eine immer wahre Pruefung in
  `test_zustandsdatei` entfernt; `test_seiten` meldet eine fehlende Seite
  als Pruefzeile.
- Toter Code: drei Funktionen ohne Aufrufer, zehn ungenutzte Importe,
  `skripte/ueber_nacht.sh`, der nie gelesene Schluessel `stufe_neu`.
- Dopplungen im Seitenbau zusammengelegt (`schnitt.py`, Farbmischung und
  Tokenzugriff in `tokens.py`); die erzeugten Seiten und SVGs sind byteweise
  gleich geblieben.
- Kommentare, Docstrings und README-Tatsachen an den Code angeglichen
  (Syntaxbaum ohne Docstrings unveraendert).
- Teststand: 917 Python-Pruefungen in 31 Dateien + 64 JS gruen.

### 13.10.2026 &mdash; Gesamtreview umgesetzt (T-0074 bis T-0087)

Bericht `docs/review-2026-10-09.md`, Entscheidungen `docs/entscheidungen-2026-10-09.md`.
Bloecke unveraendert aus Next/Backlog hierher verschoben; offene Restpunkte stehen in den
jeweiligen Stand-Zeilen.

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
- STATE.md (Abschnitt Kontingent) sagte "Die Memberzahl multipliziert NICHT" -
  widerspricht README/alarm.py und dem Log (alarm#3); am 09.10.2026 mit einem
  datierten Hinweis versehen (Formel ungeklaert). Der Done-Block "Kontingent vollstaendig vermessen" ("210.000
  im Monat - es passt") beruht auf 216 Ortsabrufen; er bleibt als
  Zeitdokument stehen, gueltig ist README "Was die Grenze kostet". Die
  Gewichtung selbst bleibt ungemessen (alarm#4).
Stand 11.10.2026: Pass-2-Deckel von 320 auf 120 gesenkt (Maintainer, Commit 11b2e25) - ein
voller Lauf kostete 5.900 Einheiten (Member zaehlen mit) und passte weder in eine
Stunde noch zweimal in einen Tag; der Waechter (T-0075) hatte die Seite am 10.10. als
31,7 h alt gemeldet. Wirkung an den naechsten Tagen im alarm.log pruefen.
Stand 13.10.2026: Deckel auf 200 angehoben - mit 120 liefen 11.-13.10. alle Laeufe
durch, aber schon der uebernaechste Abend verlor die Advektion; 200 = 4.160 Einheiten
je Lauf, zwei Laeufe 8.320. Seit 11.10. kein Kontingentabbruch, Waechter gruen.

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
`NTFY_WAECHTER` (Maintainer), alarm#6 Nachtluecke nicht entschieden.

### 09.10.2026 &mdash; Aus Doing und Next hierher verschoben (Review architektur#1, T-0082)

Inhalt unveraendert, nur die Ueberschriftsebene ist tiefer. T-0006 war
entschieden (Antwort NEIN), T-0003 steht oben als erledigt (20.08.2026) und
der Doing-Entwurf ist ueberholt, T-0014 laeuft laut `skripte/alarm.py`
(`member_liste`, Zwei-Pass-Advektion) und laut Done-Bullet "E2 gebaut".

#### T-0006 Ablation 3-Schicht gegen niveauaufgeloest
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

**NACHTRAG 09.10.2026 (Review physik#13 / methodik#F1; Original oben
unveraendert):** `sonnen/score_niveaus.py` mittelt Term A UNGEWICHTET ueber
die Nahpunkte (= GEWICHTUNG "punkt"), `sonnen/score.py` rechnet seit dem
14.08.2026 raumwinkelgewichtet. Die Ablation verglich damit zwei verschieden
gewichtete Scores. Neu gerechnet im Review mit raumwinkelgewichtetem Term A:
Sommer rho +0.690 (statt +0.504), Niveau-Maximum im Sommer 0.808 (statt 0.488,
also ein Abend >= s*, 3-Schicht loest 2-mal aus, nicht 3-mal), Herbst rho
+0.651 (statt +0.697), Top-6 bleibt 4/6 bzw. 1/6. "Kein einziger Abend",
"zwei Massstaebe" und "s* ~ 0.4224" tragen bezueglich der Gewichtung nicht
(0.4224 ist der dritthoechste Niveau-Wert; fuer gleiche Rate ergibt sich
0.511). Die **Kernaussage NEIN haelt**. Auch "rho eher Obergrenze / NEIN wird
fester" (Vermerk 23.08.) gilt nur mit dieser Einschraenkung. Auf den
Live-Betrieb ohne Einfluss; `icond2_test.py` erbt dieselbe Mittelung.

#### T-0003-alt (ueberholt) Taegliche Ensemble-Archivierung &mdash; Entwurf aus Doing
Das Ensemble-Archiv reicht nur 93 Tage zurueck und wandert. Ein Cron, der
nichts tut ausser den Tagesabzug wegschreiben. Haengt an keiner Entscheidung.
- [ ] ECMWF ENS, native 3-h-Schritte, Fanpunkte, taeglich nach dem 00z-Lauf

#### T-0014 Score pro Member und Zwei-Pass-Advektion verdrahten
Die Score-Formeln stehen (`sonnen/score_niveaus.py`), es fehlt die
Betriebsschleife: pro Member rechnen (nie aus Mittelfeldern, Jensen), Felder
semi-Lagrangesch auf die Sonnenuntergangszeit advehieren.

