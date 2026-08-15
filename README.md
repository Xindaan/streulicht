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

**Alarm empfangen.** ntfy-App installieren (iOS/Android, kostenlos), das
Alarm-Topic aus `konfig_geheim.json` abonnieren — es steht bewusst NICHT in
der versionierten Konfiguration, weil wer es hat beliebige Pushs senden kann. Der Push kommt, sobald ein Abend im Vorlauf die
Schwelle reisst — hoechstens einmal je Abend.

**Bewerten.** `web/bewerten-<ort>.html` auf dem Telefon oeffnen. Fuenf
Knoepfe, sonst nichts. Die Seite zeigt bewusst **keine** Prognose: wer vorher
die Vorhersage sieht, bewertet die Vorhersage statt den Himmel. Erst bewerten,
dann nachsehen.

**Noch nicht ausgeliefert.** Das Repo ist privat, und GitHub Pages gibt es im
kostenlosen Tarif nur aus oeffentlichen Repos — siehe T-0015. Bis dahin bleibt
`seiten_basis` leer und die Bewertungsaufforderung kommt ohne Link.

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

## Betrieb: wo laeuft der Cron?

Die Cron-Zeilen unten stehen auf `/volume1/wetter`, also einem Synology-NAS.
**Das ist eine geerbte Annahme aus der ersten Fassung dieser Datei, keine
gepruefte Tatsache.**  Was der Betrieb wirklich braucht:

- eine Maschine, die abends laeuft (die Bewertungsaufforderung kommt zur
  Sonnenuntergangszeit) und morgens (der Alarmlauf braucht den 00z-Lauf),
- Python 3 mit Standardbibliothek,
- Netz.

Ein Mac tut es, solange er an ist; verpasste Laeufe holt nichts nach.  Ein
NAS oder ein Kleinrechner ist der robustere Ort, aber keine Voraussetzung.
Pfade unten entsprechend anpassen.

## Cron

```cron
# Alarmlauf, nach der Bereitstellung des 00z-Laufs
30 7 * * *   cd /volume1/streulicht && /usr/bin/python3 skripte/alarm.py >> daten/alarm.log 2>&1

# Bewertungsaufforderung - STUENDLICH, das Skript prueft selbst das Fenster.
# Eine feste Uhrzeit ginge nicht: der Sonnenuntergang wandert im Jahr um
# mehr als vier Stunden. Idempotent, je Abend hoechstens eine Aufforderung.
15 * * * *   cd /volume1/streulicht && /usr/bin/python3 skripte/erinnerung.py >> daten/erinnerung.log 2>&1

# Bewertungen einsammeln - ALLE DREI STUNDEN, nicht taeglich:
# ntfy.sh haelt Nachrichten nur rund 12 h vor
5 */3 * * *  cd /volume1/streulicht && /usr/bin/python3 skripte/bewertungen_holen.py >> daten/bewertung.log 2>&1

# Ensemble-Archivierung - AB TAG 1 DES LIVEGANGS, nicht spaeter.
# Das Archiv reicht nur 93 Tage zurueck und wandert; was heute nicht
# weggeschrieben wird, ist in drei Monaten weg. Ohne dieses Archiv laesst
# sich die Quantilbruecke (T-0020) nie messen - siehe unten.
0 8 * * *    cd /volume1/streulicht && /usr/bin/python3 skripte/archiviere.py >> daten/archiv.log 2>&1
```

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
| `skripte/satellit.py` | MSG-Wolkenmaske als Beobachtungswahrheit |
| `skripte/fensterterm.py` | Fensterterm gegen die Maske: Phantom oder bestaetigt (T-0027) |
| `sonnen/grib2.py` | GRIB2-Leser fuer die Wolkenmaske, ohne Fremdbibliothek |

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
