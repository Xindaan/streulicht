# Gutachten zur Richtungsentscheidung (15.08.2026)

Verifikations-Gate auf Commit 22b6c3e.  Alles unten ist nachgerechnet, nicht
aus dem Dokument uebernommen.  Datenbasis: `daten/` im Haupt-Checkout,
Skripte identisch mit dem Worktree.

## 0 Kurzfassung

**Die Empfehlung "Live gehen, bevor am Modell weitergearbeitet wird" traegt
in der Richtung, aber nicht mit den Zahlen, mit denen sie begruendet ist.**
Drei load-bearing Zahlen tragen die Folgerung nicht, die aus ihnen gezogen
wird:

| Behauptung im Repo | Nachgerechnet | Folge |
|---|---|---|
| "Aufloesung (Gitterweite) ist als Erklaerung gefallen" (STATE Z. 106) | Test unentschieden. Ohne die 39 Kontrollabende mit Foto erfuellt er das vorab gesetzte Kriterium: **+0.154 [+0.028, +0.279]** | Gitterweite ist NICHT gefallen, eher das Gegenteil. Aendert die Livegang-Empfehlung nicht (ICON-D2 ist ohnehin kein Betriebsmodell), aendert aber, was T-0019 zu klaeren hat |
| "18.5 Ausloesungen/Jahr -> ~20 bewertete Alarme nach einer Saison" | s\* = 0.7065 ist auf 2022-2025 kalibriert. Ueber 2015-2021 gibt derselbe s\* **9.0/Jahr**, ueber elf Jahre 12.4/Jahr. Der Betrieb rechnet zudem auf 25-km-ENS-Membern mit p >= 0.5, die Quantilbruecke ist nie gemessen | Erwartung eher **einstellig pro Saison**. Ein Labelplan, der an Alarmen haengt, liefert zu wenig |
| "ERA5-Klimatologie", "ERA5 25 km gegen ICON-D2 2.2 km", "ERA5 saettigt bei 23 %" | `archive-api` ohne `models=` liefert **`ecmwf_ifs`, nicht ERA5** (Default == `ecmwf_ifs` in 2019, 2021, 2022, 2023 exakt; `models=era5` weicht ab). Und dieses Produkt bricht **2022** (Anteil exakt 100 % bei `high`: 7-12 % -> 19-27 %) | Klimatologie heterogen; Anreicherung haelt (0.671 -> 0.657 aera-gepaart), Term B allein kippt (z 1.99 -> 1.40), s\* haengt am Regime |

Dazu ein Dokumentations-Drift, der bereits einmal zugeschlagen hat: `konfig.json`
traegt s\* = **0.7065** (richtig, Befund 10.3), STATE/TASK/`alarm.py`-Kommentare/
`termanalyse.py`/`rueckschau.py` und **Befund 31** rechnen mit dem alten
0.6325.  Mit 0.7065 werden aus "3 gegen 0 Ausloesungen" 2 gegen 0 - die
Folgerung von T-0006 haelt, die Zahl nicht.

## 1 Die fuenf Nachrechnungen

### 1.1 `icond2_test.py` - reproduziert, Aufbau geprueft

Reproduziert exakt: 35 Bloecke, ERA5\* 0.593 / ICON 0.657, Differenz +0.064
[-0.037, +0.165].  (\*"ERA5" = `ecmwf_ifs`, s. 1.5.)

Aufbau: saisonkontrolliert ja (+/-21 Tage um denselben Kalendertag, ueber
alle Jahre 2023-2026), Ziehung mit festem Seed, Albumtage ausgeschlossen,
zirkulaere Abende korrekt aus dem Album entfernt und **nicht** als Kontrolle
gezogen (geprueft: leere Schnittmenge).  9 Kontrollabende dienen mehreren
Bloecken - Bloecke sind also nicht ganz unabhaengig, fuer die z-Statistik
zweitrangig.

**Die 27 % stimmen: 39 von 140 Kontrollen (27.9 %) sind Berliner Fotoabende
im Sonnenuntergangsfenster; Basisrate in der Kandidatenmenge 24.2 %, also
keine Ueberziehung.**  Aber "verzerrt konservativ" ist nur die halbe Wahrheit.
Sensitivitaet (post hoc, kein neuer Test):

| Kontrollen | n Bloecke | ERA5\* | ICON | Differenz |
|---|---|---|---|---|
| alle (Repro) | 35 | 0.593 | 0.657 | +0.064 [-0.037, +0.165] |
| **nur ohne Foto** | 32 | 0.544 | 0.698 | **+0.154 [+0.028, +0.279]** |
| nur mit Foto | 9 | 0.778 | 0.648 | -0.130 |

Ohne die Foto-Kontrollen erfuellt der Test das vorab gesetzte Kriterium
(>= +0.05, KI ohne Null).  Die Kontamination daempft die Differenz nicht nur,
sie **entscheidet das Ergebnis**.  Das ist post hoc und deshalb kein Nachweis
fuer ICON - aber es reicht, um "Gitterweite gefallen" zurueckzunehmen.
Sauber waere: Kontrollen ohne jeden Fotoabend ziehen (Kandidatenmenge 854,
davon 647 ohne Foto - reicht fuer 4 je Block) und den Test einmal
neu registrieren.  Kosten: ~40 neue Abende, ~1450 Calls, ein Tagesbudget.

Nicht reproduzierbar: "77 gemeinsame Abende, rho +0.746, Mittel 0.230 gegen
0.221" (Befund 29, Gueltigkeitspruefung).  Ueber die 166 Abende des
Endstands: rho **0.698**, Mittel 0.222 gegen **0.186** (ICON 16 % tiefer,
nicht "praktisch gleich").  Offenbar ein Zwischenstand ohne Pruefbefehl.
Richtung haelt.

### 1.2 `ablation.py --von 2023-06-01 --bis 2023-07-12` - reproduziert, Folgerung zu eng

Reproduziert: rho +0.504, Top-6 1 von 6, mit s\* = 0.6325 3 gegen 0
Ausloesungen, sN-Drittwert 0.4224.  Mit dem gueltigen s\* = 0.7065: **2 gegen 0**.

Was das Dokument nicht sagt, obwohl es in denselben Daten steht - im selben
Fenster gegen die Klimatologie (`ecmwf_ifs`-Analyse, 3-Schicht):

| Paar | rho | Top-6 gemeinsam | Ausloesungen bei s\* |
|---|---|---|---|
| GFS-3-Schicht vs GFS-niveauaufgeloest (Befund 31) | 0.504 | 1 | 3 vs 0 |
| **Klimatologie-3-Schicht vs GFS-3-Schicht** (gleiche Variante, anderes Modell) | **0.483** | **1** | **8 vs 3** |
| Klimatologie-3-Schicht vs GFS-niveauaufgeloest | 0.610 | 2 | 8 vs 0 |

Der Sprung zwischen **Modellen** ist mindestens so gross wie der zwischen
**Varianten** - und genau den Modellsprung macht der Betrieb: s\* aus der
IFS-Analyse, Alarm auf ECMWF-ENS-Membern (25 km).  "Der Betrieb laeuft auf
der richtigen Variante" (STATE Z. 133) ist wahr und beruhigt zu Unrecht:
die Quantilbruecke, die T-0002 als offen notiert ("haengt an T-0006"), ist mit
T-0006 nicht geschlossen, sondern durch dieselben Daten als Problem belegt.

### 1.3 `test_member.py` - gruen, prueft das Richtige, und schreibt ein Loch fest

11 von 11 gruen.  Der Diskriminator `detail is None` greift genau dann, wenn
KEIN Schirmniveau Nahbereichsdaten hatte (`gew == 0` fuer alle Schirme,
`score.py:151`).  Das ist korrekt getestet.

Aber der Testfall "Nahbereich belegt, Rest fern -> Detail vorhanden" schreibt
folgendes Verhalten als richtig fest (`score.py:171` und `:211`):

    sicht = 1.0 - (sicht_c / sicht_n if sicht_n else 0.0)   -> sicht = 1.0
    if zg == 0.0: continue                                   -> weg bleibt 1.0

Ein Member mit Nahbereichsdaten und leerem Faecher bekommt **B = 1.0**, also
S = A, zaehlt voll im Nenner UND stimmt mit voller Staerke dafuer.  Fehlende
Fensterdaten wirken als freies Fenster - das Spiegelbild von Befund 27a
(dort: fehlende Daten als Stimme dagegen).  In der Klimatologie ist das
harmlos (Rohdaten lueckenlos geprueft: 0 von 129 210 Werten je Stichjahr
fehlen), im Live-Pfad latent.  Siehe Abschnitt 5.

### 1.4 z = +5.61 (Befund 24.1) - reproduziert im Stand von gestern, heute +5.17

`albumtest.py --klima score_berlin_g0.5_2015_2025.json`: n = **76** (nach dem
2026-Nachtrag), Mittelrang 0.671, **z = +5.17**.  Der Wert +5.61 gilt fuer
n = 70; STATE zitiert ihn ohne den Nachtrag.  Sechs 2026-Abende, zwei davon
unter den drei schlechtesten - der Nachtrag hat den Befund abgeschwaecht,
nicht verstaerkt.

Ausschluesse: 4 zirkulaere Abende (2022-11-11 liegt ausserdem vor 2023 und
faellt im ICON-Test ohnehin raus).  Album = semantische Suche
"Sonnenuntergang" in Fotos, Berlin-Box 52.2-52.8 N / 13.0-13.9 E.  Die
2026-Abende (bis 28.06.) liegen vor dem Projektstart (alle Commits 14.08.2026),
also nicht score-gewaehlt.  Der Ausschluss ist vollstaendig, soweit die
Zirkularitaet ueber die Balken-Durchsicht lief; eine andere Quelle von
Zirkularitaet habe ich nicht gefunden.

Saisonpaarung ist drin (Tag-im-Jahr-Fenster ueber alle Jahre).  Was NICHT
drin ist: das Regime (1.5).  Aera-gepaart (2015-2021 nur gegen 2015-2021,
2022-2026 nur gegen 2022-2026): S 0.657, z **+4.73**; nur gleiches Jahr:
0.629, z +3.90.  **Die Anreicherung ist echt.**  A: 0.595 -> 0.591 (haelt).
B: 0.566 -> 0.546, z 1.99 -> **1.40** (kippt; STATE/README stuetzen sich
nicht darauf).

### 1.5 Befund 26 - Korrektur traegt; die Konfundierung steckt woanders

Reproduziert exakt: A==0 1/4.1 (z -1.59), B==0 0/2.0 (z -1.44), s==0 1/6.1
(z **-2.19**).  Aera-gepaart: 1/4.3, 0/2.2, 1/6.4 (z -2.28) - haelt.

Saisonale Konfundierung anderswo: **nein.**  `abbruchtest.py`,
`abbruchtest2.py`, `albumtest.py`, `icond2_test.py` (Bloecke) und
`absicht.py` ("saisonaler Mittelrang") paaren alle ueber +/-21 Tage.

Aber dieselbe **Klasse** (Album ungleich verteilt ueber eine Achse, entlang
derer der Score sich systematisch aendert) trifft an einer Achse zu, die
niemand geprueft hat: **das Datenregime.**

    Jahr        2015 16 17 18 19 20 21 | 22 23 24 25
    >= 0.7065      8  6  7  8 12 12 10 | 20 21 16 17
    high == 100%   8  8  9  8  9  8 13 | 24 27 26 19  (% der Zellstunden)

Bestaetigt per Live-Abfrage (eine Zelle, je ein Junimonat): `archive-api`
ohne `models=` liefert in 2019/2021/2022/2023 wertgleich `ecmwf_ifs`;
`models=era5` weicht ab (2022: p100 7.5 % statt 20.0 %).  Die gesamte
"ERA5"-Klimatologie ist die Open-Meteo-IFS-Analyse, und die wechselt 2022
den Charakter.  Das Album liegt zu 52 von 79 Abenden im neuen Regime.

Folgen, der Groesse nach: (a) s\* = 0.7065 ist das 95. Perzentil des NEUEN
Regimes; im alten waere es 0.557-0.577; (b) Aufloesungsbaseline im ICON-Test
war IFS 9 km, nicht ERA5 25 km - "Gitterweite 25 -> 2.2 km" hat so nie
stattgefunden; (c) Anreicherung um 0.014 ueberschaetzt, unkritisch;
(d) "ERA5 saettigt bei 23 %" (Befund 14.2) beschreibt IFS ab 2022, nicht ERA5.

## 2 Antworten auf die vier Fragen

### 2.1 Traegt die Empfehlung?

**Ja, als Reihenfolge.  Nein, als Begruendung.**  Der Livegang kostet 0 EUR,
ist die einzige Quelle prospektiver Labels und wird durch keinen der Befunde
oben in Frage gestellt.  Was nicht traegt: dass er "rund 20 bewertete Alarme"
liefert und dass "weitere Modellarbeit" pauschal unbegruendet ist.

Zwei Dinge sind keine Modellarbeit und trotzdem faellig:

1. **Quantilbruecke auf das Betriebsmodell.**  Ohne sie ist die Alarmrate
   unbekannt (Bandbreite nach 1.2/1.5: irgendwo zwischen 3 und 18 im Jahr).
   Es gibt keinen Weg, sie vorab zu messen - kein Ensemble-Archiv (T-0003
   nie gestartet), `previous-runs` traegt keine Ensembles.  Also: **der
   Livegang IST die Messung.**  Nach 6-8 Wochen Betrieb die Verteilung der
   Member-Scores je Vorlauf gegen die IFS-Analyse desselben Zeitraums legen
   und s\*/p\* nachziehen.  `archiviere.py` (T-0003) muss dafuer vom ersten
   Tag an laufen - sonst ist der Livegang keine Messung.
2. **Alarmrate fuer die Saison sichern.**  Bei p\* = 0.5 auf 50 Membern und
   einer 95.-Perzentil-Schwelle im Tail werden Pushs selten sein (Trockenlauf
   heute, 10 Tage: Maximum 18 %).  Fuer die Saison als Messinstrument ist das
   zu wenig.  Entscheidung fuer Andre: gestufter Push (z. B. ab p >= 0.25 mit
   Prozentzahl im Text, wie er ohnehin drinsteht) - Produktentscheidung, kein
   Modell.  Alternative ohne Produktaenderung: taegliche Bewertung (2.2 a),
   dann braucht es die Alarme als Label-Trigger gar nicht.

Erwarteter Gewinn einer Saison mit taeglicher Bewertung: ~245 bewertete
Abende Maerz-Oktober, davon ~10 Analyse-Ereignisse.  Ein Rangtest (10 gegen
235) weist bei 80 % Power A >= ~0.75 nach.  Das ist derselbe n wie das Album,
aber mit Negativen, prospektiv, unverfaelscht.  Zwei Saisons halbieren die
Nachweisgrenze fast.

### 2.2 Was vor dem Livegang stehen muss (Pflicht, nach Schaden bei Fehlen)

Die Bewertungsseite (`web/bewerten-berlin.html`, statisch, aus dem
E2-Commit - nicht aus `skripte/` erzeugt) verbirgt die Prognose.  **Das
reicht nicht gegen Zirkularitaet, weil der Alarm selbst die Prognose ist**
und Tage vorher auf dem Telefon lag.  Strukturell fehlt:

- **(a) Bewertungsaufforderung an JEDEM Abend, unabhaengig vom Alarm.**
  Push zu Sonnenuntergang + 30 min mit Link auf die Seite (Cron-Zeile,
  ~20 Zeilen).  Ohne das werden nur Alarmabende bewertet - keine
  Trefferquote, keine Basisrate, dieselbe Presence-only-Falle wie das Album.
  Wenn taeglich zu viel ist: feste Zufallsstichprobe (>= 3 Abende/Woche,
  Seed in `konfig.json`), und im Zustand vermerken, ob eine Bewertung
  **aufgefordert oder spontan** kam.
- **(b) Foto je Aufforderung, spaeter blind benoten.**  Auf der Seite ein
  Satz "und ein Foto nach Westen".  Nach der Saison im Stapel ohne Datum
  benoten (Methode aus `daten/blind/`).  Einziger Weg, die Verankerung durch
  den Alarm herauszurechnen.  0 EUR.
- **(c) Prognosestand je Lauf vollstaendig festschreiben.**  `alarm.py:351`
  haengt je Lauf nur `{"lauf", "p"}` an `verlauf`; Median, A, sicht, weg,
  n_member werden beim naechsten Lauf ueberschrieben.  Den ganzen
  Ergebnis-Dict (ohne `verlauf`) anhaengen - drei Zeilen.  Sonst ist nach
  der Saison nur die Trefferquote je Vorlauf auswertbar, nicht warum.
- **(d) Bewertungen duerfen nicht still verloren gehen.**  ntfy.sh haelt
  12 h, der Cron laeuft alle 3 h; NAS aus / Netz weg / Kontingent = weniger
  Zeilen, kein Fehler.  Das ist der stille Ausfall des Livegangs schlechthin.
  Loesung ohne Server: die Seite protokolliert jede Bewertung in
  `localStorage` und bietet "alle nachsenden"; der Poller ist ohnehin
  idempotent (spaetere Note ueberschreibt).
- **(e) `archiviere.py` als Cron ab Tag 1** (Begruendung 2.1).
- **(f) Trockenlauf bestanden** - heute erstmals komplett: 74 Zellen, 9
  Variablen, **50 Member** (nicht 51: der Kontrolllauf hat kein
  `_member`-Suffix und faellt in `member_liste()` still raus - harmlos, aber
  dieselbe Klasse), 88 Schritte, Pass 2 mit 140 Zellen, ~5 min wegen vier
  Minutenlimit-Wartezeiten.  Cron-Slot passt.
- **(g) s\*-Drift bereinigen** (0.6325 -> 0.7065 in STATE, TASK, `alarm.py`
  Kommentare, `termanalyse.py:15`, `rueckschau.py:112/125`) und "ERA5" ->
  "IFS-Analyse (Open-Meteo best_match)" in Befunden/README.  Nicht
  funktional - aber Befund 31 hat gestern bereits mit dem falschen s\*
  gerechnet.

Nicht noetig vor dem Livegang: Satellit (2.3), Neuregistrierung des
ICON-Tests, jede Aenderung an Score oder Varianten.

### 2.3 Satellit (T-0019): Schaden, wenn er unterbleibt

Er beantwortet je Abend "war die Wolke da" und - mit Helligkeitstemperatur -
"wie hoch", also die Eingangsgroessen von A und B getrennt vom Score.  Das
kann eine Saison Labels **nicht**: Labels pruefen nur das Produkt.  Die
Frage "ist Offline-Modellarbeit gerechtfertigt" ist genau die Frage
"Modellfehler oder Scorefehler", und die entscheidet nur der Satellit (oder
Fotos + Modellfelder derselben Abende, langsamer und lauter).

Aber er ist **keine Voraussetzung fuer den Livegang** und aendert bis zur
Quantilbruecke keine Handlung: solange der Betrieb auf ENS 25 km laeuft, ist
ein bezifferter Modellfehler nur beziffert.  Empfehlung: **nach** dem
Livegang, in der Wartezeit, parallel.  Aufwand: EUMETSAT Data Store
(kostenlos, Anmeldung durch Andre), MSG-SEVIRI/MTG-FCI IR 10.8 um
Sonnenuntergang fuer 80 Abende + Kontrollen, Ausschnitt Faecher; 1-2 Tage.
Ausserdem der einzige Pfad, der bei freier Ortswahl weiterhilft (MSG deckt
Europa/Afrika, GOES/Himawari den Rest) - ICON-D2 nicht.

Schaden bei Verzicht: nach der Saison weiss man, WIE OFT der Alarm trifft,
aber nicht, WARUM er verfehlt - und die Frage, ob Modellarbeit lohnt, steht
dann genauso da wie heute, nur mit besseren Labels.

### 2.4 Wo das Projekt am ehesten STILL scheitert - die fuenfte Stelle

**`sonnen/score.py:171` und `:211`: fehlende Fensterdaten = freies
Fenster.**  Beleg in 1.3.  `test_member.py` bestaetigt dieses Verhalten
sogar als erwuenscht ("Nahbereich belegt, Rest fern -> Detail vorhanden").
Ausloeser im Live-Pfad: Member mit `None`-Werten in Faecherzellen (heute
nicht aufgetreten; die Klimatologie ist lueckenlos).  Wirkung, wenn es
auftritt: S = A statt S = A * B, Stimme fuer den Sonnenuntergang, kein
Hinweis in der Ausgabe.  Fix: `sicht_n == 0` oder alle Segmente
uebersprungen -> B undefiniert -> `detail = None` (Member aus dem Nenner,
wie 27a), plus Ausgabezeile "n Member ohne Fensterdaten", plus den
Testfall umdrehen.  Eine Stunde.

Drei weitere Fundstellen derselben Klasse ("es kam etwas zurueck, also
sind es Daten"), aufsteigend nach Schaden:

1. `member_liste()` zaehlt Suffixe - 50 statt 51 Member, Kontrolllauf weg.
2. `bewertungen_holen.py`: 12-h-Cache gegen 3-h-Cron ohne Verlustmeldung
   (2.2 d).  Das ist die Stelle, an der der ganze Sinn des Livegangs still
   verschwindet.
3. **`klimatologie.py:117`: `archive-api` ohne `models=`.**  Vier Wochen lang
   "ERA5" geschrieben, weil die Abfrage funktioniert hat.  Kein Test kann das
   finden; nur der Vergleich zweier Antworten.  Dieselbe Klasse wie
   "3.51:1 ohne Flaeche" (Befund 30): eine Zahl, die aussieht wie ein
   Faktum und eine Relation zu einer nicht notierten zweiten Groesse ist.

## 3 Was ich NICHT gefunden habe

- Keinen Rechenfehler in den reproduzierten Zahlen selbst (icond2, ablation,
  albumtest, termanalyse) - alle Ausgaben stimmen mit dem Dokument ueberein,
  soweit derselbe Datenstand vorliegt.
- Keine weitere saisonale Konfundierung.
- Keine Zirkularitaet jenseits der vier ausgeschlossenen Abende.
- Kein Hinweis, dass Andres Album-Auswahl vom Score beeinflusst war
  (Projektstart nach dem letzten Albumabend).

## 4 Annahmen, an denen Aussagen haengen

- Sensitivitaet 1.1 ist post hoc; sie belegt "unentschieden", nicht
  "ICON gewinnt".
- "Regime 2022" ist am Datenprodukt gemessen (drei Junimonate live), nicht
  an Open-Meteo-Dokumentation.  Ob Open-Meteo `best_match` vor 2017 auf ERA5
  faellt, habe ich nicht abgefragt; fuer die Aussage reicht der Bruch 2022.
- Erwartete Alarmzahl "einstellig" ist eine Bandbreite aus 1.2/1.5 und einem
  Trockenlauf, keine Messung.  Genau deshalb 2.1 Punkt 1.
- Power-Angabe in 2.1 (A >= 0.75 bei 10 gegen 235) ist eine
  Mann-Whitney-Naeherung.

## 5 Pruefbefehle

    python3 skripte/icond2_test.py
    python3 skripte/ablation.py --von 2023-06-01 --bis 2023-07-12
    python3 skripte/test_member.py
    python3 skripte/albumtest.py --klima daten/score_berlin_g0.5_2015_2025.json
    python3 skripte/alarm.py --trocken

Sensitivitaeten (Foto-Kontrollen, Aera-Paarung, Regime-Statistik,
Modellvergleich in der Ablation, `models=era5`-Gegenprobe) sind Einzeiler
gegen `daten/icond2_ergebnis.json`, `daten/ablation_2023-06-01.json`,
`daten/score_berlin_g0.5_2015_2025.json`, `daten/foto_detail.json` und
`daten/roh/g0.5_*.json`; die Werte stehen oben mit ihren Eingaben.
