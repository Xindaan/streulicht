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
/opt/homebrew/opt/python@3.13/bin/python3.13 -m venv .venv
.venv/bin/python3 -m pip install -r betrieb/anforderungen.txt
.venv/bin/python3 skripte/alarm.py --trocken   # rechnen, nichts senden
.venv/bin/python3 skripte/alarm.py             # rechnen und pushen
```

Nur `numpy` und `matplotlib` werden gebraucht, und die nur fuer Kalibrierung
und Auswertung — der Alarmlauf selbst kommt mit der Standardbibliothek aus.

**Warum `.venv/bin/python3` und nicht einfach `python3`** (seit 30.08.2026,
T-0062): die vier Agenten liefen bis dahin auf `/usr/local/bin/python3`, dem
python.org-Framework 3.10, dessen Sicherheitsunterstuetzung im Oktober 2026
endet. Sie laufen jetzt auf Homebrew `python@3.13`. Ein blankes `python3` in
der Shell zeigt auf dieser Maschine **nicht** darauf: bis Anfang Oktober 2026
auf das alte 3.10, seitdem (der alte Pfad ist entfernt) auf das
Apple-System-Python 3.9.6 — wer also von Hand mit `python3 ...` startet,
testet einen anderen Interpreter als den, unter dem der Betrieb laeuft.
Deshalb ueberall der explizite venv-Pfad.
Die venv ist ueber den unversionierten Pfad `/opt/homebrew/opt/python@3.13`
angelegt: ein brew-Minorupdate von 3.13.15 auf 3.13.16 bricht sie damit
nicht.

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

Unter der Kopfzeile steht, **von wann die Wetterdaten sind** &mdash; zwei
Zeiten, weil sie Verschiedenes sagen:

> Modelllauf 18.08., 06 UTC &middot; geholt 18.08., 17:26 Uhr

Der **Modelllauf** ist die Initialisierung des ECMWF-Laufs, auf dem die
Zahlen beruhen; **geholt** der Moment, in dem wir sie abgerufen haben.
Dazwischen liegen mehrere Stunden Rechenzeit im Rechenzentrum. Wer nur eine
Zeit sieht, haelt die Daten fuer so frisch wie den Abruf.

Gezeigt werden nur Abende **ab heute**. Der Zustand fuehrt auch vergangene
&mdash; dort haengen die Bewertungen &mdash; aber auf einer Prognoseseite
haben sie nichts zu suchen.

Die Prognoseseite zeigt je Abend **zwei Zahlen, die nicht dasselbe sind**:

- **Wahrscheinlichkeit** — Anteil der Ensemble-Member ueber s\*. "Wie sicher?"
- **Perzentil** — klimatologischer Rang des Member-MEDIANS. "Wie selten?"

Die Achse traegt das Perzentil (Schwellen bei 80. und 95.), weil sie danach
gebaut ist; die Wahrscheinlichkeit steht als Text daneben.

**Die Begruendung daneben gehoert zum MEDIAN-Member** (seit 02.09.2026,
T-0064). Bis dahin kamen Schirm, A, Sicht, Weg und die Segmentliste vom
BESTEN der 51 Member — Stufe und Zahl beschrieben also die Mitte der
Verteilung, der Satz darunter ihr optimistisches Ende. Auf der Seite las
sich das jeden Abend als Widerspruch. Beleg vom 01.09.2026 fuer den 11.09.:
Median 0,03, Wahrscheinlichkeit 2 %, Stufe "unauffaellig" — und darunter
"Mittelhohe Wolken, Licht kommt von Westen frei durch", weil ein einziger
Member auf S = 0,88 kam. Jetzt stammt alles aus demselben Member. Die
Streuung geht nicht verloren: das Tagesarchiv haelt weiterhin je Member eine
eigene Zeile. Der Vertikalschnitt
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

### Das Tagesarchiv (T-0003)

Der Alarmlauf schreibt nach jedem erfolgreichen Durchlauf
`daten/archiv/<ort>/<tag>_<fenster>.json` &mdash; **ohne einen einzigen
zusaetzlichen Abruf**. Drin steht je Abend eine Zeile pro Ensemble-Member
(Score, Schirm, A, B, Sicht, Weg) und das Medianfeld. Rund 60 kB je Lauf,
also etwa 44 MB im Jahr.

Die Memberzeilen sind der Punkt: die Wahrscheinlichkeit ist ein Anteil ueber
51 Zahlen, und ohne sie liesse sich spaeter weder ein Rangdiagramm noch ein
Brier-Skill rechnen, nur die Trefferquote. Nicht archiviert werden die
Rohfelder je Member &mdash; das waere ueber ein Gigabyte im Jahr und wuerde
nur gebraucht, um die Score-Formel rueckwirkend zu aendern.

> **Die erste Fassung hat nie funktioniert.** `skripte/archiviere.py` holte
> die Felder ein ZWEITES Mal: 76 Zellen x 43 Variablen x 51 Member x 11 Tage.
> Open-Meteo antwortete durchgehend mit
> `HTTP 400: "Your API call requests too much data."`, und nachgerechnet
> waren es **16.720 Kontingenteinheiten am Tag bei einem Budget von 10.000**.
> Der Fehler war nicht die Blockgroesse, sondern der zweite Abruf. Skript und
> Agent sind am 20.08.2026 entfallen.

**Die erzeugten Seiten sind nicht im Repo.** `web/index.html`,
`web/bewerten-*.html` und `web/bisher.html` sind Bauartefakte und
gitignoriert &mdash; der stuendliche Agent schreibt sie neu, und schon die
Sonnentafel in der Bewertungsseite wandert dabei taeglich um einen Eintrag.
Getrackt erzeugten sie jeden Tag einen Diff, der nichts bedeutet. Quelle
sind die Vorlage `web/bewerten.html` und die Generatoren in `skripte/`;
`python3 skripte/ausliefern.py --trocken` baut alle drei aus dem Nichts neu.

Was veroeffentlicht wird, steht dort als **ausdrueckliche Liste**. Der erste
Anlauf nahm "jede .html ausser der Vorlage" und haette `diagnose.html`
(Albumabende neben Bewertungen) und `rueckschau.html` (9.5 MB) mit ins Netz
gestellt. Dass beide gitignoriert sind, hat NICHT geschuetzt - kopiert wird
aus dem Arbeitsverzeichnis, nicht aus dem Repo.

**Vor 4 Uhr morgens** zaehlt die Bewertung noch zum Vorabend — wer um eins
bewertet, meint den Sonnenuntergang von gestern.

### Bekannte Grenze: die Seiten koennen nur EINEN Ort

`konfig.json` fuehrt `orte[]` als Liste, und Alarm, Erinnerung und
Bewertungsseite arbeiten sie auch wirklich durch. Die **Prognoseseite, die
Bilanz, der Vertikalschnitt und die Faecherkarte nicht**: Berlins
Koordinaten und die Berliner Klimatologie stehen dort fest im Quelltext
(`skripte/seite.py`, `skripte/bisher.py`, `skripte/schnitt.py`,
`skripte/faecher.py`). Ein zweiter Ort bekaeme also Pushs, die gegen Berlins
s\* gerechnet sind, und eine Prognoseseite, die Berlin zeigt — beide Laeufe
enden dabei mit Exitcode 0, es faellt nirgends auf.

`ausliefern.py` sagt es seit dem 02.09.2026 wenigstens laut, wenn mehr als
ein Ort konfiguriert ist. Ein harter Abbruch waere falsch: die
Mehrortfaehigkeit ist ein erklaertes Ziel aus E0 ("Ort als Parameter, auch
fuer Freunde"), und der Weg dorthin ist halb gebaut, nicht verworfen.

### Bekannte Grenze: eine Note kann verlorengehen

ntfy.sh haelt Nachrichten rund **12 Stunden** vor. Die Bewertungsseite
markiert eine Note nach dem ersten erfolgreichen POST als erledigt und
sendet sie nie wieder — ist der Mac zwischen Abgabe und Abruf laenger als
12 h im Ruhezustand, ist die Note weg, und zwar lautlos. Im Alarmlog stehen
ueber 318 Laeufe 17 Luecken von mehr als 70 Minuten, die laengste 724
Minuten; das ist knapp unter der Grenze, aber eben knapp.

Der Abruf laeuft seit dem 02.09.2026 **stuendlich** statt alle drei Stunden.
Das verkleinert das Fenster, schliesst es aber nicht: gegen einen Schlaf von
mehr als 12 h hilft nur ein geplantes Aufwecken
(`pmset repeat wakeorpoweron ...`), und das ist eine Systemeinstellung, die
Andre selbst setzen muss.

## Konfiguration

`konfig.json`:

| Schluessel | Bedeutung |
|---|---|
| `schwelle_score` | s\* — ab diesem Score gilt ein Abend als Ereignis |
| `schwelle_wahrscheinlichkeit` | p\* — ab diesem Memberanteil wird gepusht |
| `vorlauf_tage` | wie weit voraus gerechnet wird |
| `advektion` | semi-Lagrangesche Zeitinterpolation an/aus (siehe unten) |
| `pass2_max_zellen` | Obergrenze fuer Pass 2 (Standard 320, `null` = kein Deckel); darueber rechnen die fernen Abende teilweise ohne Advektion, Logzeile `ACHTUNG Pass 2 GEDECKELT` |
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

Vier Agenten in `~/Library/LaunchAgents/`, alle mit `WorkingDirectory` und
absolutem Interpreterpfad (launchd hat kein PATH). Der Interpreter ist seit
dem 30.08.2026 `/Users/Andre/src/wetter/.venv/bin/python3` (Homebrew 3.13);
die Vorlagen dazu liegen versioniert in `betrieb/`. `ausliefern.py` startet
seine Kindprozesse ueber `sys.executable`, der Wechsel erbt sich also von
selbst auf `seite.py`, `bewertungsseite.py` und `bisher.py`:

| Label | Skript | Wann |
|---|---|---|
| `de.greatbelow.streulicht.alarm` | `alarm.py --geplant` | stuendlich zur 20. Minute, **rechnet zweimal: 09:20 UTC und rund 3 h vor Sonnenuntergang** |
| `de.greatbelow.streulicht.erinnerung` | `erinnerung.py` | stuendlich zur 15. Minute |
| `de.greatbelow.streulicht.bewertung` | `bewertungen_holen.py` | **stuendlich** zur 5. Minute |
| `de.greatbelow.streulicht.seite` | `ausliefern.py` | **alle 10 Minuten**, pusht nur bei Aenderung |

### Warum der Alarm sonnenuntergangsrelativ laeuft

Bis zum 18.08.2026 lief er fest um 07:30. Zwei Messungen haben das gekippt:

**Erstens die Frische.** ECMWF ENS rechnet viermal am Tag (00z/06z/12z/18z),
aber die Daten stehen erst Stunden nach der Initialisierung zur Verfuegung.
Der Verzug ist **nicht konstant**, und das ist der Punkt: gemessen an
`ecmwf_ifs025_ensemble/static/meta.json` waren es 8,7 h fuer einen
18z-Lauf (18.08.2026) und 12,9 h fuer einen 00z-Lauf (20.08.2026). Das
ENSEMBLE ist dabei deutlich langsamer als der deterministische Lauf
desselben Modells (7,2 h in derselben Messung).

**Nachgezaehlt am Tagesarchiv (02.09.2026, 27 Laeufe vom 21.08. bis 04.09.):**

| Fenster | n | benutzter Lauf | Verzug (min / Median / max) |
|---|---|---|---|
| `morgens` 09:20 UTC | 13 | **13x 18z des Vortags, 0x 00z** | 15,3 / 15,3 / 15,6 h |
| `abends` ~3 h vor SU | 14 | 8x 06z, 4x 00z, 2x 18z | 9,3 / 11,3 / 22,3 h |

Zwei Dinge stehen damit fest, die vorher Vermutung waren. Erstens: **der
Vormittagslauf sieht den 00z nie** — 09:20 UTC ist zu frueh, entgegen der
Zahl "08:44 UTC", die aus einer einzigen Probe stammte und in `konfig.json`
stand. Zweitens: der Abendlauf erwischt meist den **06z**, nicht den 00z.

Wie viel spaeter der Vormittagslauf liegen muesste, ist **noch nicht
gemessen**. Seit T-0065 schreibt deshalb jeder stuendliche Tick den gerade
verfuegbaren Modelllauf ins Log — die Datei ist statisch und kostet kein
Kontingent. Nach zwei Wochen ist `lauf_morgens_utc` belegbar statt geraten.
Bis dahin bleibt 09:20 stehen: ein Vormittagslauf auf dem 18z ist immer noch
frischer als der Vorabendstand.

**Korrektur zur ersten Fassung dieses Abschnitts:** hier stand 8,7 h als
feste Groesse, aus einer einzigen Probe. Damit war auch die Folgerechnung
zu guenstig. Mit dem realistischeren Wert:

| Abruf | benutzter Lauf | Vorlauf auf den Sonnenuntergang |
|---|---|---|
| alt, 07:30 (August) | 12z des Vortags | 30,4 h |
| **neu, 3 h vor SU (August)** | **06z desselben Tages** | **12,4 h** |
| alt, 07:30 (Dezember) | 12z des Vortags | 26,9 h |
| **neu, 3 h vor SU (Dezember)** | 18z des Vortags | 20,9 h |

Die Umstellung bleibt richtig - sie spart im August rund achtzehn Stunden
Vorlauf. Die Augustzeile stand hier zweimal falsch: erst mit 8,7 h Verzug
gerechnet (zu guenstig), dann mit dem 00z angesetzt (zu pessimistisch).
Gemessen wird tatsaechlich meist der **06z** benutzt, siehe die Zaehlung
oben.

**Was die Grenze kostet.** Die freie Stufe erlaubt 600 Aufrufe/Minute,
5.000/Stunde, 10.000/Tag und **300.000/Monat**. Wie Open-Meteo einen
Ensemble-Abruf gewichtet, ist **nicht geklaert** (Review 09.10.2026,
alarm#3/#4). Das Log stuetzt meist die Rechnung "Variablen x Member / 10 je
Ort", also 15,3 Einheiten je Ortsabruf, aber nicht ausnahmslos: Nach diesem
Gewicht waeren zwei Laeufe zu je rund 380 Ortsabrufen rund 350.000 im Monat,
also ueber der Grenze - am 08.10.2026 liefen aber zwei solche Laeufe an einem
UTC-Tag durch, nach demselben Gewicht 11.600 Einheiten bei 10.000 am Tag.
Gardena fragt vom selben Rechner dieselbe API ab, ist aber zu klein, um das
zu erklaeren. Eine belastbare Monatsrechnung gibt es deshalb nicht; die
fruehere Zahl "210.000 im Monat, es passt" beruhte auf 216 Ortsabrufen je
Lauf und ist ueberholt. Ein Abo waere die
**Professional**-Stufe, nicht Standard: die Ensemble-API ist in Standard
ausdruecklich nicht enthalten (Preistabelle und FAQ auf open-meteo.com/en/pricing).

**Zweitens das Kontingent.** Ein vollstaendiger Lauf sind im Oktober 2026
16-17 HTTP-Anfragen ueber **378-383 Ortsabrufe**: 72 Faecherzellen in Pass 1,
eine Windzelle und 290-320 versetzte Zellen in Pass 2. Im August waren es
rund zehn Anfragen ueber 216 Ortsabrufe. Treiber ist Pass 2, und der waechst
nicht mit der Windlage, sondern mit dem **saisonalen Abstand dt** zwischen
Sonnenuntergang und dem naechsten 3-h-Modellschritt (Versatz = v * dt):
Spitze Anfang Oktober, Ende November nahe null, wieder hoch im Maerz und
Juni. Pass 2 ist deshalb gedeckelt (`pass2_max_zellen`, siehe
Konfiguration). Nach dem Log zaehlt Open-Meteo Ensemble-Member meist wie
zusaetzliche Variablen - neun Variablen mal 51 Member wiegen dann dreimal so
viel wie drei mal 51. Bis zum 18.08.2026 holte der Lauf die sechs
Windvariablen fuer alle 68 Faecherzellen, obwohl sie **nur am Heimatpunkt
gelesen** werden (der Advektionsversatz ist ein Ensemble-Mittelwind je
Schicht, kein Feld). Das kostete damals rund 5.500 Einheiten und riss das
Stundenlimit bei der vorletzten Anfrage. Es gibt also keinen zweiten Lauf
"zur Sicherheit" - es gibt einen, und der muss sitzen. Deshalb liegt er so
spaet wie moeglich.

**Abbruch am Kontingent (seit 09.10.2026, T-0074).** Jeder erfolgreich
geholte Block liegt in `daten/cache/abruf/<Modelllauf>/<UTC-Abruftag>/`;
ein Wiederholungslauf auf **demselben** Modelllauf am **selben** UTC-Tag
holt nur, was fehlt. Ein neuer Modelllauf bekommt nie alte Bloecke, und
nach Mitternacht UTC wird neu geholt, weil Open-Meteo die Zeitachse am
Abruftag beginnen laesst. Ist der Modelllauf unbekannt
(`meta.json` nicht erreichbar), laeuft der Abruf ohne Cache. Cacheordner,
deren Modelllauf aelter als zwei Tage ist, raeumt der naechste Lauf. Nach
`Hourly ... exceeded` vermerkt der Lauf in `daten/zustand.json` unter
`_kontingent` eine Sperre bis zur naechsten vollen UTC-Stunde + 2 min, nach
`Daily ... exceeded` bis 00:02 UTC. Jeder Lauf davor - auch einer von Hand -
endet mit `Kontingentsperre bis ... - kein Abruf` und bucht nichts, das
Fenster bleibt also offen. Eine Sperre von Hand aufheben: den Eintrag
`_kontingent` aus der Zustandsdatei loeschen.

**Warum keine feste Uhrzeit.** Der Sonnenuntergang wandert in Berlin ueber
das Jahr um mehr als fuenfeinhalb Stunden: 21:33 am 21. Juni, 15:53 am
21. Dezember. Ein fester Termin um 17:00 laege im Dezember **hinter** dem
Ereignis, vor dem er warnen soll. Der Agent laeuft deshalb stuendlich und
`alarm.im_laufenster()` entscheidet - dasselbe Muster wie bei der
Erinnerung. `skripte/test_lauffenster.py` prueft ueber ein ganzes Jahr, dass
genau ein Termin je Tag ins Fenster faellt, keiner und keine zwei.

### Zwei Laeufe am Tag

Seit dem 18.08.2026 gibt es **zwei** Fenster:

| Fenster | Wann | Modelllauf | Wozu |
|---|---|---|---|
| `morgens` | 09:20 UTC, fest | 18z des Vortags | vormittags aktuelle Zahlen auf der Seite |
| `abends` | rund 3 h vor Sonnenuntergang | meist 06z desselben Tages (im Sommer) | der wichtige: kuerzester Vorlauf |

Die Spalte "Modelllauf" ist **gemessen, nicht hergeleitet** (27 Laeufe, siehe
Tabelle weiter oben). Im Sommer liegt das Abendfenster nach der
Verfuegbarkeit des 06z, im Winter davor &mdash; dort benutzen beide Laeufe
denselben 18z und der zweite bringt nichts Neues. Frueher geht es nicht: bei
Sonnenuntergang um 15:53 gibt es schlicht nichts Frischeres.

**Der zweite Lauf schiebt keinen zweiten Push nach.** Je Abend geht
hoechstens ein Alarm raus, das haelt `zustand["alarme"]` fest. Der
Vormittagslauf sorgt dafuer, dass ein Abend ueber der Schwelle frueher
gemeldet wird und die Seite vormittags nicht den Vorabend zeigt.

Im Winter benutzen beide Laeufe denselben 18z-Lauf des Vortags - der zweite
ist dann redundant. Seit dem Blockcache (T-0074) kostet er dann auch nichts
mehr: derselbe Modelllauf mit denselben Abenden liefert dieselben Anfragen,
und die liegen schon in `daten/cache/abruf/`. (Vorher: rund 7.000 der
10.000 Tageseinheiten fuer zwei Laeufe, damals bei 216 Ortsabrufen je Lauf.)

**Verschlaeft der Agent den Tick, wird nachgeholt.** Am 18.08.2026 fehlte
genau der eine stuendliche Tick, der ins Abendfenster fiel (Rechner im
Ruhezustand) &mdash; damit fiel der ganze Abendlauf aus. Ist das
Abendfenster verstrichen und noch nicht bedient, laeuft deshalb der naechste
Tick nach, **bis zum Sonnenuntergang**. Der Vormittagslauf wird nicht
nachgeholt: zwei Laeufe in einer Stunde traegt das Stundenkontingent nicht.

Steuergroessen in `konfig.json`: `lauf_vorlauf_stunden` (3),
`lauf_morgens_utc` (09:20) und `lauf_fenster_min` (60). Das Fenster darf
**nicht** schmaler werden als der Abstand der Agenten-Termine, sonst faellt
an manchen Tagen kein Tick hinein - und die beiden Fenster duerfen sich
nicht naeher kommen als ihre eigene Breite. `test_lauffenster.py` prueft
beides ueber ein ganzes Jahr; die Gegenprobe mit `lauf_morgens_utc` auf
12:00 kostet 97 Abendlaeufe.

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
- die Auslieferung laeuft alle zehn Minuten und pusht nur, wenn sich der
  gebaute Stand geaendert hat - sie kann den Alarm also nicht mehr
  verpassen, egal wie lange er braucht.

**Warum alle zehn Minuten und nicht stuendlich:** am 20.08.2026 war der
Abendlauf um 17:23 fertig, die Auslieferung lief erst um 17:50 - 27 Minuten
lang war alles richtig gerechnet und nichts davon sichtbar. Ein Bauen ohne
Push kostet **0,27 s** (gemessen), gepusht wird nur bei geaendertem
Fingerabdruck. Der Preis ist also praktisch null, die Obergrenze fuer
veraltete Seiten sinkt von 59 auf 10 Minuten.

```bash
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/de.greatbelow.streulicht.alarm.plist
```

```bash
launchctl kickstart -k gui/$UID/de.greatbelow.streulicht.erinnerung
```

Der zweite Befehl stoesst einen Agenten sofort an — der Funktionstest, ohne
auf die naechste Kalenderzeit zu warten. Logs liegen unter `daten/*.log`.

> **EINE GEAENDERTE PLIST WIRD NICHT VON SELBST GELESEN**, und `kickstart`
> hilft dabei nicht. Am 18.08.2026 hat `cp` plus `kickstart -k` einen Lauf
> gestartet — aber mit der ALTEN, noch in launchd geladenen Definition:
> ohne `--geplant` und mit dem alten 07:30-Kalender. Der Lauf lief also
> mittags los und ignorierte sein Zeitfenster. `launchctl print` zeigte
> weiterhin `Hour 7, Minute 30` und keine Argumente.
>
> Zum Nachladen gehoert **bootout, dann bootstrap**:
>
> ```bash
> launchctl bootout gui/$UID/de.greatbelow.streulicht.alarm
> launchctl bootstrap gui/$UID ~/Library/LaunchAgents/de.greatbelow.streulicht.alarm.plist
> launchctl print gui/$UID/de.greatbelow.streulicht.alarm | grep -A4 arguments
> ```
>
> Die dritte Zeile ist die Gegenprobe — ohne sie glaubt man, es sei
> nachgeladen.

**Warum die Erinnerung stuendlich laeuft und nicht zur Sonnenuntergangszeit:**
die wandert im Jahr um mehr als vier Stunden. Das Skript prueft selbst, ob
sie gerade im Fenster liegt, und ist je Abend idempotent.

**Und sie wird nachgeholt** (seit 02.09.2026, T-0067). Das Fenster ist 75
Minuten breit, der Agent tickt stuendlich — schlaeft der Rechner darueber
hinweg, gab es an diesem Abend gar keine Aufforderung und damit sehr
wahrscheinlich keine Note. Der Alarmlauf holt seinen verpassten Tick seit
T-0048 nach, die Erinnerung tat es nicht, obwohl sie an derselben Maschine
haengt. Nachgeholt wird bis zum **lokalen Mitternacht** und nur der heutige
Abend: nach Mitternacht bewertet niemand mehr den vorletzten
Sonnenuntergang, die Frage waere dann irrefuehrend statt hilfreich.

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
| `Too many concurrent requests` | zu viele gleichzeitig | kurz warten, wenige Faeden (`alarm.py`: 5 s) |
| `Minutely ... exceeded` | Minutenfenster voll | 20-65 s warten (`alarm.py`: 65 s, hoechstens fuenfmal je Anfrage) |
| `Hourly` / `Daily ... exceeded` | Kontingent | abbrechen, Cache haelt (`alarm.py`: Sperre bis volle Stunde + 2 min bzw. 00:02 UTC) |

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
er, ist der naechste sinnvolle Zeitpunkt der regulaere Vormittagslauf
(`lauf_morgens_utc`, heute 09:20 UTC) am Folgetag — das Tagesbudget setzt um 00:00 UTC zurueck. Die Seite zeigt in
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
| `skripte/zustandsdatei.py` | atomarer Schreibvorgang fuer Zustand, Archiv und Klimatologie (T-0051) |
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
| `skripte/netz.py` | wartet auf Namensaufloesung, bevor ein Lauf beginnt |
| `skripte/ausliefern.py` | baut die Seiten und pusht nach `gh-pages` |
| `skripte/fensterterm.py` | Fensterterm gegen die Maske: Phantom oder bestaetigt (T-0027) |
| `skripte/wegterm.py` | Wegterm anders aggregiert, fuenf Varianten gegen Album/Referenz (T-0029) |
| `sonnen/grib2.py` | GRIB2-Leser fuer die Wolkenmaske, ohne Fremdbibliothek |
| `betrieb/*.plist` | Vorlagen der vier launchd-Agenten (Kopie dessen, was installiert ist) |
| `betrieb/anforderungen.txt` | die zwei Fremdpakete, mit Begruendung wofuer |

### Tests

```bash
.venv/bin/python3 skripte/test_member.py      # Member-Verdichtung, Faecher, Deckung
.venv/bin/python3 skripte/test_advektion.py   # semi-Lagrangesche Verschiebung
.venv/bin/python3 skripte/test_grib2.py       # GRIB2-Leser, Vorzeichen-Betrag, Sektionen
.venv/bin/python3 skripte/test_seiten.py      # erzeugte Seiten und die neuen Grafiken
.venv/bin/python3 skripte/test_lauffenster.py # ein Lauf je Tag, ueber ein ganzes Jahr
.venv/bin/python3 skripte/test_abruf.py       # Wind nur am Ort, Advektion trotzdem aktiv
.venv/bin/python3 skripte/test_wn3.py         # WeatherNext-3-Leser, Zeitachse, Negativproben
.venv/bin/python3 skripte/test_zustandsdatei.py    # atomarer Schreibvorgang (T-0051)
.venv/bin/python3 skripte/test_bewertung_nutzlast.py  # Notenvalidierung (T-0052)
.venv/bin/python3 skripte/test_alarm_versand.py    # Versandfehler kippt den Lauf nicht (T-0055)
.venv/bin/python3 skripte/test_phantomnullen.py    # Datenluecken werden nicht zu Nullen (T-0060)
.venv/bin/python3 skripte/test_zustandspflege.py   # Raeumung und Sperre der Zustandsdatei (T-0058)
.venv/bin/python3 skripte/test_ortsfilter.py       # --geplant rechnet nur faellige Orte (T-0056)
.venv/bin/python3 skripte/test_faechergeometrie.py # eine Faechergeometrie, nicht zwei (T-0057)
.venv/bin/python3 skripte/test_score_distanz.py    # Deckung und Luecken in score_distanz (T-0061)
.venv/bin/python3 skripte/test_erinnerung.py       # Fenster und Nachholen bis Mitternacht (T-0067)
.venv/bin/python3 skripte/test_kontingent.py       # Blockcache, Kontingentsperre, Pass-2-Deckel (T-0074)
node   skripte/test_bewertungsseite.js   # Warteschlange und Freilegung
```

Stand 04.09.2026: **310 Python-Pruefungen + 41 JS, alle gruen**
(`test_phantomnullen.py` mit ICON-Cache mitgezaehlt).

**Kein Test darf von der Uhrzeit abhaengen.** Zwei taten es bis zum
02.09.2026 und waren deshalb regelmaessig rot, ohne dass am Code etwas
falsch war: `test_zustandspflege.py` erwartete eine Zahl fuer den heutigen
Abend, den `alarm.py` nach Sonnenuntergang aber ueberspringt, und
`test_bewertungsseite.js` suchte den festen Monatsnamen "August". Beide
laufen jetzt gegen eine feste Zeit bzw. gegen alle zwoelf Monatsnamen. Ein
Test, der einmal am Tag oder einmal im Monat von selbst umkippt, wird nicht
mehr gelesen - und dann faellt auch der echte Fehler nicht mehr auf.

**Kein Test fasst Betriebsdaten an.** `test_abruf.py` lief bis zum
02.09.2026 gegen das echte `daten/zustand.json`: er startete einen
vollstaendigen `alarm.main()` ohne `--trocken`, sicherte die Datei vorher
weg und schrieb sie danach truncierend und ohne Sperre zurueck. Faellt in
diese Sekunden ein Bewertungsabruf, ist die Note weg. Alle Tests arbeiten
jetzt in einem eigenen Temp-Verzeichnis (`alarm.BASIS` umgebogen).

`test_zustandsdatei.py` startet Kindprozesse und killt sie mit `SIGKILL`
mitten im Schreiben &mdash; er dauert deshalb ein paar Sekunden laenger als
die uebrigen. Das ist Absicht: ein Test, der nur den Quelltext liest,
haette den Fehler nicht gefunden, gegen den er geschrieben ist.

`test_phantomnullen.py` braucht den ICON-Cache (`daten/roh_icond2/`, 166 Dateien) und endet ohne ihn mit Code 2.

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

**Die Advektion tastet STROMAUF ab** (korrigiert 02.09.2026, T-0063). Das
Modellfeld liegt zu einem nativen 3-h-Schritt vor, der Sonnenuntergang liegt
daneben. Gesucht ist die Wolke, die zum Sonnenuntergang ueber dem Fanpunkt
steht — zum frueheren Modellschritt war dieselbe Luft noch stromauf, bei
Westwind also westlich. Abgetastet wird deshalb **Fanpunkt minus
Transportversatz**.

Bis zum 02.09.2026 stand dort ein Plus: der Lauf las die Zelle auf der
falschen Seite, mit dem doppelten Fehler 2·v·|Δt| — bei 100 km/h und
Δt = 0,5 h also 100 km daneben. Aufgefallen ist es nie, weil ein
verschobener Faecher genauso plausible Zahlen liefert wie ein richtiger.
`test_advektion.py` prueft die Richtung jetzt am Verhalten des Laufs: bei
Wind aus Westen muessen die Zellen aus Pass 2 westlich derer aus Pass 1
liegen.

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
