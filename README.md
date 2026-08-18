# Streulicht

Meldet zwei bis zehn Tage im Voraus eine Wahrscheinlichkeit dafuer, dass in
Berlin ein aussergewoehnlicher Sonnenuntergang stattfindet — und schickt einen
Push aufs Telefon, wenn sie hoch genug ist.

**Zum Namen.** In der Optik ist Streulicht der Parasit: das, was man aus einem
Instrument herauskonstruiert. Hier ist es das Produkt. Der Score integriert
eine Henyey-Greenstein-Phasenfunktion ueber den Vorwaertspeak — es geht
ausschliesslich um Licht, das gestreut wird, statt geradeaus zu laufen.

Kein Produkt: keine Nutzerverwaltung, keine Datenbank, kein Docker. Ein Cron,
ein paar Skripte, eine JSON-Datei.

## Quickstart

```bash
git clone https://github.com/Xindaan/streulicht.git && cd streulicht
python3 skripte/alarm.py --trocken          # rechnen, nichts senden
python3 skripte/alarm.py                    # rechnen und pushen
```

Nur `numpy` und `matplotlib` werden gebraucht, und die nur fuer Kalibrierung
und Auswertung — der Alarmlauf selbst kommt mit der Standardbibliothek aus.

## Nutzung

**Alarm empfangen.** ntfy-App installieren (iOS/Android, kostenlos), dann das
Alarm-Topic aus `konfig_geheim.json` abonnieren. Es steht bewusst NICHT in der
versionierten Konfiguration: ohne Anmeldung ist der Topicname bei ntfy das
Passwort, und wer ihn hat, kann beliebige Pushs schicken. Der Push kommt,
sobald ein Abend im Vorlauf die Schwelle reisst — hoechstens einmal je Abend.

**Bewerten.** `web/bewerten-<ort>.html` auf dem Telefon oeffnen. Fuenf
Ziffern und "Nicht gesehen" — Note 0 ist eine echte Antwort, kein leeres Feld.
Vorher zeigt die Seite **keine** Prognose: wer die Vorhersage sieht, bevor er
bewertet, bewertet die Vorhersage statt den Himmel. **Nach** der Abgabe legt
sie frei, was vorhergesagt war (seit 16.08.2026) — das traegt die Blindheit,
ohne die Neugier zu bestrafen.

**Warum die Quittung nicht klingelt.** Die abgegebene Note reist als
ntfy-Nachricht zum Poller; sie geht damit an dasselbe Topic, das auch die
Abenderinnerung traegt, und landete deshalb als Push auf demselben Telefon,
von dem sie kam. Sie laeuft jetzt mit Prioritaet 1 (min): zugestellt, aber
ohne Benachrichtigung. Loeschen ginge nicht — die Nachricht IST der
Transportweg.

## Die Seiten

| Was | URL |
|---|---|
| **Prognose** | <https://xindaan.github.io/streulicht/> |
| **Bewerten** | <https://xindaan.github.io/streulicht/bewerten-berlin.html> |
| **Bisher** | <https://xindaan.github.io/streulicht/bisher.html> |

**Zwei Saetze, eine Datei.** Bis 1000 px Fensterbreite laeuft die
Telefonfassung, darueber die Desktopfassung
(`docs/entwurf/handoff-desktop-2026-08-16.md`): das Himmelsband wird zum
400 px hohen Kopf mit dem Hero darauf, die drei Zahlen werden beschriftete
Kennzahlen, die Achse waechst auf 260 px und traegt die Rangzahl je Abend,
Schnitt und Faecherkarte liegen nebeneinander, Korpuszeile und
Bilanzverweis sitzen in der Kopfleiste. Pfeiltasten blaettern durch die
Abende. **Der Inhalt ist in beiden Saetzen derselbe** - kein Bauteil, keine
Zahl, kein Satz kommt hinzu. Die Bewertungsseite bleibt auf Telefonmass:
sie wird aus dem Push heraus geoeffnet.

Die Prognoseseite ist seit dem 16.08.2026 nach dem Entwurf in
`docs/entwurf/handoff-ux-2026-08-16.md` gebaut: Hero mit Stufe und
Klartextbegruendung, Himmelsband (Farbe traegt `median / s*`, eine
gewoehnliche Woche bleibt sichtbar stumpf), Zeitachse mit den beiden warmen
Zonen, Vertikalschnitt, Faecherkarte von oben — und ein Absatz, der sagt, **ob
ein Push kommt**. Das war vorher nirgends zu lesen, obwohl "keiner reisst die
Schwelle" der haeufigste Fall ist.

`bisher.html` ist die Bilanz: die bisherigen Bewertungen und eine ehrliche
Auskunft darueber, was noch fehlt. **Nicht zu verwechseln mit
`rueckschau.html`** — das ist die lokale Diagnose ueber vier Jahre
Klimatologie (9,5 MB, gitignoriert, nie ausgeliefert).

Die Prognoseseite zeigt je Abend **zwei Zahlen, die nicht dasselbe sind**:

- **Wahrscheinlichkeit** — Anteil der Ensemble-Member ueber s\*. "Wie sicher?"
- **Perzentil** — klimatologischer Rang des Member-MEDIANS. "Wie selten?"

Die Achse traegt das Perzentil (Schwellen bei 80. und 95.), weil sie danach
gebaut ist; die Wahrscheinlichkeit steht als Text daneben. Der Vertikalschnitt
wird aus dem gespeicherten Medianfeld gezeichnet - fuer das BILD richtig, fuer
die ZAHL nicht: S ist ein Produkt nichtlinearer Terme, der Score des
Medianfelds ist nicht der Median der Scores (Jensen). Deshalb kommt jede Zahl
aus dem Zustand, nur das Bild aus dem Feld.

`python3 skripte/seite.py --rueckschau` baut dieselbe Seite aus historischen
Abenden statt aus der Prognose — nuetzlich, um die Darstellung an Abenden zu
sehen, die tatsaechlich ausgeloest haetten.

**Ausgeliefert wird ueber einen Wegwerfzweig.** `skripte/ausliefern.py` baut
alle drei Seiten und schreibt sie als EINZELNEN Commit nach `gh-pages`, mit
`--force`. Grund: die Prognoseseite ist 220 kB und wird taeglich neu erzeugt -
taeglich nach `main` waeren das ueber 100 MB im Jahr fuer Staende, die
niemanden interessieren. Auf dem Wegwerfzweig gibt es keine Historie, die
wachsen koennte.

Was veroeffentlicht wird, steht dort als **ausdrueckliche Liste**. Der erste
Anlauf nahm "jede .html ausser der Vorlage" und haette `diagnose.html`
(Albumabende neben Bewertungen) und `rueckschau.html` (9.5 MB) mit ins Netz
gestellt. Dass beide gitignoriert sind, hat NICHT geschuetzt - kopiert wird
aus dem Arbeitsverzeichnis, nicht aus dem Repo.

**Vor 4 Uhr morgens** zaehlt die Bewertung noch zum Vorabend — wer um eins
bewertet, meint den Sonnenuntergang von gestern.

## Konfiguration

`konfig.json`:

| Schluessel | Bedeutung |
|---|---|
| `schwelle_score` | s\* — ab diesem Score gilt ein Abend als Ereignis |
| `schwelle_wahrscheinlichkeit` | p\* — ab diesem Memberanteil wird gepusht |
| `vorlauf_tage` | wie weit voraus gerechnet wird |
| `advektion` | semi-Lagrangesche Zeitinterpolation an/aus |
| `orte[]` | Name, Koordinaten, Zeitzone, Bewertungs-Topic |
| `faecher` | optional: reduzierte Abfragegeometrie |

**Zwei Fallen in dieser Datei.**

`schwelle_score` gehoert zur **Faechergeometrie**, mit der die Klimatologie
gerechnet wurde (5 Azimute, 8 Distanzen, 0.5-Grad-Gitter). Wer `faecher`
setzt, macht s\* ungueltig und muss `skripte/klimatologie.py` mit demselben
Faecher neu laufen lassen. Das Skript warnt beim Start.

`schwelle_score` gehoert ausserdem zur **3-Schicht-Variante** des Scores. Der
Betrieb laeuft deshalb auf `sonnen/score.py`, nicht auf der niveauaufgeloesten
`sonnen/score_niveaus.py` — auch wenn letztere physikalisch besser ist. Der
Wechsel steht aus, bis die Ablation (T-0006) zeigt, dass die Rangfolgen
zusammenfallen.

## Betrieb: launchd, nicht cron

**Auf macOS ist cron die falsche Wahl, und der Grund ist nicht Geschmack.**
Diese Maschine steht auf `sleep 10` — sie schlaeft nach zehn Minuten ein.
Cron feuert im Schlaf nicht und holt einen verpassten Lauf auch nicht nach;
`launchd` mit `StartCalendarInterval` startet ihn beim Aufwachen nach. Genau
das braucht ein Alarm, dessen Fenster einmal am Tag offen steht.

Fuenf Agenten in `~/Library/LaunchAgents/`, alle mit
`WorkingDirectory` und absolutem Interpreterpfad (launchd hat kein PATH):

| Label | Skript | Wann |
|---|---|---|
| `de.greatbelow.streulicht.alarm` | `alarm.py --geplant` | stuendlich zur 20. Minute, **rechnet rund 3 h vor Sonnenuntergang** |
| `de.greatbelow.streulicht.erinnerung` | `erinnerung.py` | stuendlich zur 15. Minute |
| `de.greatbelow.streulicht.bewertung` | `bewertungen_holen.py` | alle 3 h zur 5. Minute |
| `de.greatbelow.streulicht.archiv` | `archiviere.py` | 08:00 |
| `de.greatbelow.streulicht.seite` | `ausliefern.py` | stuendlich zur 50. Minute, **pusht nur bei Aenderung** |

### Warum der Alarm sonnenuntergangsrelativ laeuft

Bis zum 18.08.2026 lief er fest um 07:30. Zwei Messungen haben das gekippt:

**Erstens die Frische.** ECMWF ENS rechnet viermal am Tag (00z/06z/12z/18z),
und die Daten sind erst **8,7 Stunden nach der Initialisierung** abrufbar
(gemessen an `ecmwf_ifs025_ensemble/static/meta.json`, 18.08.2026). Um 07:30
war damit der 18z-Lauf des Vorabends der juengste - **21 bis 24 Stunden**
Vorlauf auf den Sonnenuntergang. Rechnet man stattdessen rund drei Stunden
vor Sonnenuntergang, sind es **12 bis 17 Stunden**, das ganze Jahr ueber.

**Zweitens das Kontingent.** Ein vollstaendiger Lauf sind rund zehn
HTTP-Anfragen ueber 216 Ortsabrufe, und danach ist das Stundenbudget von
Open-Meteo (5.000) leer. Das Tagesbudget (10.000) traegt **genau zwei
Laeufe**. Es gibt also keinen zweiten Lauf "zur Sicherheit" - es gibt einen,
und der muss sitzen. Deshalb liegt er so spaet wie moeglich.

**Warum keine feste Uhrzeit.** Der Sonnenuntergang wandert in Berlin ueber
das Jahr um mehr als fuenfeinhalb Stunden: 21:33 am 21. Juni, 15:53 am
21. Dezember. Ein fester Termin um 17:00 laege im Dezember **hinter** dem
Ereignis, vor dem er warnen soll. Der Agent laeuft deshalb stuendlich und
`alarm.im_laufenster()` entscheidet - dasselbe Muster wie bei der
Erinnerung. `skripte/test_lauffenster.py` prueft ueber ein ganzes Jahr, dass
genau ein Termin je Tag ins Fenster faellt, keiner und keine zwei.

Steuergroessen in `konfig.json`: `lauf_vorlauf_stunden` (3) und
`lauf_fenster_min` (60). Das Fenster darf **nicht** schmaler werden als der
Abstand der Agenten-Termine, sonst faellt an manchen Tagen kein Tick hinein.

**Die ausgelieferte Seite haengt also an zwei Laeufen**, und beide koennen
einzeln ausfallen: `alarm.py` holt die Zahlen, `ausliefern.py` baut daraus
die Seiten und schiebt sie nach `gh-pages`. Faellt der Alarm aus, baut
`ausliefern.py` trotzdem — dann aber aus dem Zustand vom Vortag. Die Seite
sagt das seit dem 17.08.2026 selbst, mit einem Streifen unter der
Kopfleiste: *"Diese Zahlen sind vom 16.08. (gestern)."*

**Wie es dazu kam:** am Morgen des 17.08.2026 hatte der Mac von
07:30 bis nach 08:15 keine Namensaufloesung. Alarm, Archiv, Bewertungsabruf
und der Push sind alle vier daran gestorben, jeder genau einmal — und die
Seite zeigte den ganzen Tag den Vortag. Seitdem:

- `skripte/netz.py` laesst die netzabhaengigen Skripte bis zu 20 Minuten
  auf Namensaufloesung warten, statt am ersten Fehlversuch zu sterben;
- `ausliefern.py` wiederholt den Push dreimal und **nennt den git-Fehler**
  (vorher schluckte `capture_output` genau die Zeile, die erklaert, warum);
- die Auslieferung laeuft stuendlich und pusht nur, wenn sich der gebaute
  Stand geaendert hat - sie kann den Alarm also nicht mehr verpassen, egal
  wie lange er braucht.

```bash
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/de.greatbelow.streulicht.alarm.plist
```

```bash
launchctl kickstart -k gui/$UID/de.greatbelow.streulicht.erinnerung
```

Der zweite Befehl stoesst einen Agenten sofort an — der Funktionstest, ohne
auf die naechste Kalenderzeit zu warten. Logs liegen unter `daten/*.log`.

**Warum die Erinnerung stuendlich laeuft und nicht zur Sonnenuntergangszeit:**
die wandert im Jahr um mehr als vier Stunden. Das Skript prueft selbst, ob
sie gerade im Fenster liegt, und ist je Abend idempotent.

Auf einem NAS oder Linux-Rechner tut es stattdessen ein gewoehnlicher Cron;
die Zeiten sind dieselben.

**Die Quantilbruecke ist die zentrale Unbekannte des Betriebs.**  s\* stammt
aus einer Klimatologie auf IFS-**Analysen**; der Alarm rechnet auf
ECMWF-**ENS-Membern**.  Der Sprung zwischen zwei Modellen ist gemessen
genauso gross wie der zwischen zwei Score-Varianten (Befund 33: rho 0.483
gegen 0.504, bei den Ausloesungen 8 gegen 2).  Ob dieselbe Schwelle dieselbe
Rate ergibt, ist **nie gemessen worden** und vorab auch nicht messbar - es
gibt kein Ensemble-Archiv.  Der Livegang ist die Messung: `archiviere.py` ab
Tag 1, nach 6-8 Wochen s\* und p\* nachziehen.  Bis dahin gilt die Alarmrate
als unbekannt, nicht als 18.5 pro Jahr.

**Kontingent beachten.** Open-Meteo drosselt minuetlich (600), stuendlich
(5000) und taeglich (10000). Die **historischen** Endpunkte (`archive-api`,
`historical-forecast-api`) teilen sich ein Budget; `ensemble-api`,
`forecast-api` und `air-quality-api` haben ein eigenes. Zweimal in
entgegengesetzter Richtung gemessen, was den Zufall ausschliesst:

| Wann | `archive` / `historical-forecast` | `ensemble` |
|---|---|---|
| 14.08.2026 vormittags | gesperrt | laeuft |
| 14.08.2026 nachmittags | laeuft | gesperrt |

Das schuetzt den Betrieb aber **nicht**: am Vormittag war eine halbe Stunde
nach der Messung auch `ensemble-api` erschoepft. **Vor jedem groesseren Lauf
`--trocken` pruefen statt auf eine Theorie ueber das Kontingent zu bauen.**

**429 ist nicht gleich 429.** Derselbe Statuscode traegt drei verschiedene
Bedeutungen, und nur eine ist terminal — im `reason`-Feld nachsehen:

| `reason` enthaelt | heisst | richtige Antwort |
|---|---|---|
| `Too many concurrent requests` | zu viele gleichzeitig | kurz warten, wenige Faeden |
| `Minutely ... exceeded` | Minutenfenster voll | 20-65 s warten |
| `Hourly` / `Daily ... exceeded` | Kontingent | abbrechen, Cache haelt |

Wer alle drei gleich behandelt, bricht bei voller Quote ab: `icond2.py` kam
so im ersten Lauf ueber 5 von 166 Abenden nicht hinaus.

## Satellitenwahrheit (T-0019)

Die MSG-Wolkenmaske beantwortet fuer jeden vergangenen Abend, ob die Wolke
ueberhaupt da war - also ob ein Fehlschlag am MODELL lag oder am SCORE.
Kosten 0 EUR: Meteosat-Daten ab einer Stunde Latenz sind gebuehrenfrei.

Einrichtung, einmalig:

1. Konto auf <https://user.eumetsat.int> (kostenlos).
2. Consumer Key und Secret unter <https://api.eumetsat.int/api-key/>.
3. `konfig_geheim.json` anlegen (ist gitignoriert):

```json
{"eumetsat": {"consumer_key": "...", "consumer_secret": "..."}}
```

`eumdac` wird **nicht** gebraucht - der Data Store ist gewoehnliches HTTP,
und der GRIB2-Leser steht in `sonnen/grib2.py`.

```bash
python3 skripte/satellit.py 2025-09-15
```

Darauf setzt `skripte/fensterterm.py` auf (T-0027, Befund 35): es rechnet
den Fensterterm fuer alle Albumabende plus saisongleiche Referenzabende
dreimal — mit dem Modell, mit der Maske als Deckel je Faecherzelle (Hybrid)
und mit der Maske allein — und sagt je Abend, ob eine Phantomwolke oder eine
bestaetigte Wolke das Fenster geschlossen hat. Die Masken werden in
`daten/satellit/` gecacht; mit `--nur-cache` laeuft es ohne Netz.

```bash
python3 skripte/fensterterm.py --nur-cache
```

`skripte/wegterm.py` (T-0029, Befund 37) rechnet den Score fuer alle Abende
der Klimatologie mit fuenf Fassungen des Beleuchtungswegs (Produkt, Wurzel,
Mittel, Maximum, ohne Tangentensegment) und misst je Fassung Trefferquote,
Anreicherung und tote Fenster bei gleicher Alarmrate. Ergebnis: keine
Fassung rettet die toten Albumabende, der Betrieb bleibt beim Produkt.

```bash
python3 skripte/wegterm.py
```

## Troubleshooting

**Kein Push angekommen.** Topic in der ntfy-App abonniert? `--trocken` zeigt,
ob ueberhaupt ein Abend die Schwelle reisst. Idempotenz: fuer einen Abend, der
schon gemeldet wurde, kommt kein zweiter Push — `daten/zustand.json` unter
`alarme` nachsehen.

**`Kontingent: ... limit exceeded`.** Minuetlich wird automatisch abgewartet;
stuendlich und taeglich nicht. Der Blockcache der Kalibrierungsskripte haelt
den Fortschritt, ein spaeterer Lauf setzt dort an.

**Fotogate: kein Zugriff auf die Mediathek.** Eine Freigabe fuer
`/Applications/Claude.app` genuegt nicht — gelesen wird unter dem
eingebetteten Bundle `com.anthropic.claude-code`, dessen Pfad die
Versionsnummer traegt. Die Skripte `fotos_zaehlen.py` und `fotos_detail.py`
deshalb aus **Terminal.app** starten.

**„Kontingent: Daily API request limit exceeded".** Ein Alarmlauf ist teuer:
51 Member x 88 Zeitschritte x 9 Variablen ueber rund 210 Zellen. Open-Meteo
zaehlt nach Gewicht, nicht nach Aufrufen — **zwei bis drei vollstaendige
Laeufe pro Tag, dann ist das Tagesbudget weg.** Gemessen am 17.08.2026: nach
drei Versuchen (12:25, 13:03, 14:15) meldete der dritte nicht mehr das
Stunden-, sondern das Tageslimit.

Konsequenz fuers Nachholen: **einen** manuellen Lauf, nicht drei. Scheitert
er, ist der naechste sinnvolle Zeitpunkt der regulaere 07:30-Lauf am
Folgetag — das Tagesbudget setzt um 00:00 UTC zurueck. Die Seite zeigt in
der Zwischenzeit den Hinweisstreifen mit dem Alter der Zahlen; das ist der
richtige Zustand, kein Defekt.

## Entwicklung

| Datei | Zweck |
|---|---|
| `sonnen/geometrie.py` | Sonnenstand, Azimut, Strahlgeometrie |
| `sonnen/feuchte.py` | Wolkendiagnostik (kalibriert, siehe Modulkopf) |
| `sonnen/score.py` | Score, 3-Schicht-Variante (Betrieb) |
| `sonnen/score_niveaus.py` | Score, niveauaufgeloest (kuenftig) |
| `skripte/alarm.py` | taeglicher Alarmlauf |
| `skripte/klimatologie.py` | Score ueber Jahre → Verteilung |
| `skripte/auswertung.py` | Verteilung → s\*, Plot |
| `skripte/abbruchtest.py` | Validierung gegen Fotoarchiv |
| `skripte/erinnerung.py` | taegliche Bewertungsaufforderung (T-0021) |
| `skripte/bewertungsseite.py` | erzeugt `web/bewerten-<ort>.html` je Ort |
| `skripte/seite.py` | erzeugt die Prognoseseite `web/index.html` |
| `skripte/bisher.py` | erzeugt die Bilanzseite `web/bisher.html` |
| `skripte/schnitt.py` | Vertikalschnitt als SVG (`schnitt_neu` fuer die Seite) |
| `skripte/faecher.py` | Faecherkarte von oben als SVG |
| `skripte/band.py` | Himmelsband: Lichteindruck als Farbverlauf |
| `skripte/satellit.py` | MSG-Wolkenmaske als Beobachtungswahrheit |
| `skripte/ausliefern.py` | baut die Seiten und pusht nach `gh-pages` |
| `skripte/fensterterm.py` | Fensterterm gegen die Maske: Phantom oder bestaetigt (T-0027) |
| `skripte/wegterm.py` | Wegterm anders aggregiert, fuenf Varianten gegen Album/Referenz (T-0029) |
| `sonnen/grib2.py` | GRIB2-Leser fuer die Wolkenmaske, ohne Fremdbibliothek |

### Tests

```bash
python3 skripte/test_member.py      # Member-Verdichtung, Faecher, Deckung
python3 skripte/test_advektion.py   # semi-Lagrangesche Verschiebung
python3 skripte/test_grib2.py       # GRIB2-Leser, Vorzeichen-Betrag, Sektionen
python3 skripte/test_seiten.py      # erzeugte Seiten und die neuen Grafiken
python3 skripte/test_lauffenster.py # ein Lauf je Tag, ueber ein ganzes Jahr
node   skripte/test_bewertungsseite.js   # Warteschlange und Freilegung
```

`test_seiten.py` braucht `daten/zustand.json` und die erzeugten Seiten (also
einen Alarmlauf und `skripte/ausliefern.py --trocken` davor); ohne sie endet
er mit Code 2 statt falsch gruen zu melden.

Messwerte und Begruendungen: `docs/befunde-e1.md`. Jede Zahl dort ist mit
ihrem Pruefbefehl belegt, auch die drei, bei denen die erste Annahme falsch war.

## Architektur

Der Score ist ein Produkt zweier Terme, ausgewertet je Ensemble-Member:

    S = max ueber Schirmniveau h von [ A_h * B_h ]

**A — Schirm.** Bewoelkung auf Niveau h im Nahbereich, **raumwinkelgewichtet**:
eine Schicht traegt zum sichtbaren Himmel mit d·h/(d²+h²)^{3/2} bei, der Punkt
ueber dem Kopf bekommt damit 75-89 % statt 9 %. Ohne diese Gewichtung wird eine
Decke, die nur ueber dem Standort steht, mit den Fanpunkten weggemittelt.

Schirm sind nur **mid und high**, nicht low - empirisch bestaetigt: tiefe
Wolken als Schirm zuzulassen senkt den Mittelrang von 0.674 auf 0.615.

**B — Fenster.** Zwei Mechanismen: Wolken zwischen Beobachter und Schirm
(Sicht) mal Produkt ueber die Segmente des Beleuchtungswegs bis zur
Tangentendistanz D(h) = sqrt(2·R_eff·h).

Wichtig gegen ein naheliegendes Missverstaendnis: der Score verlangt **keinen
freien Blick zum Horizont**. Er prueft, ob das Licht 200-400 km westlich in
1-2 km Hoehe durchkommt. Die Sonne muss nicht sichtbar sein und darf laengst
untergegangen sein - Cirrus auf 9,5 km glueht noch rund 28 Minuten weiter.

Multiplikativ, weil es eine Konjunktion ist: ohne Schirm kein Bild, ohne
Fenster kein Licht. Der entscheidende Punkt ist die Geometrie — fuer einen
Cirrus-Schirm auf 9 km muss das Licht **200 bis 400 km westlich** unter der
tiefen Bewoelkung durch, nicht ueber Berlin. Deshalb reicht keine Punktabfrage.

Dass beide Terme noetig sind, ist gemessen: r(A, B) = −0.230 ueber vier Jahre,
und gegen ein kuratiertes Album schlaegt S den Schirmterm allein deutlich
(Mittelrang 0.674 gegen 0.623, n = 43).
Die Antikorrelation kommt aus dem Frontenzyklus — vor der Warmfront Cirrus
ohne Fenster, hinter der Kaltfront Fenster mit Restbewoelkung.

## Stand

E1 (Kalibrierung) weitgehend abgeschlossen, E2 (Alarm) gebaut, E3
(Oberflaeche) offen. Was fehlt und warum: `STATE.md`.
