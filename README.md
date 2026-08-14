# Sonnenuntergang

Meldet zwei bis zehn Tage im Voraus eine Wahrscheinlichkeit dafuer, dass in
Berlin ein aussergewoehnlicher Sonnenuntergang stattfindet — und schickt einen
Push aufs Telefon, wenn sie hoch genug ist.

Kein Produkt: keine Nutzerverwaltung, keine Datenbank, kein Docker. Ein Cron,
ein paar Skripte, eine JSON-Datei.

## Quickstart

```bash
git clone <repo> && cd wetter
python3 skripte/alarm.py --trocken          # rechnen, nichts senden
python3 skripte/alarm.py                    # rechnen und pushen
```

Nur `numpy` und `matplotlib` werden gebraucht, und die nur fuer Kalibrierung
und Auswertung — der Alarmlauf selbst kommt mit der Standardbibliothek aus.

## Nutzung

**Alarm empfangen.** ntfy-App installieren (iOS/Android, kostenlos), das Topic
aus `konfig.json` abonnieren. Der Push kommt, sobald ein Abend im Vorlauf die
Schwelle reisst — hoechstens einmal je Abend.

**Bewerten.** `web/bewerten-<ort>.html` auf dem Telefon oeffnen (per GitHub
Pages ausgeliefert). Fuenf Knoepfe, sonst nichts. Die Seite zeigt bewusst
**keine** Prognose: wer vorher die Vorhersage sieht, bewertet die Vorhersage
statt den Himmel. Erst bewerten, dann nachsehen.

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
| `orte[]` | Name, Koordinaten, Zeitzone, ntfy-Topics |
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

## Cron auf dem NAS

```cron
# Alarmlauf, nach der Bereitstellung des 00z-Laufs
30 7 * * *   cd /volume1/wetter && /usr/bin/python3 skripte/alarm.py >> daten/alarm.log 2>&1

# Bewertungen einsammeln - ALLE DREI STUNDEN, nicht taeglich:
# ntfy.sh haelt Nachrichten nur rund 12 h vor
5 */3 * * *  cd /volume1/wetter && /usr/bin/python3 skripte/bewertungen_holen.py >> daten/bewertung.log 2>&1

# Ensemble-Archivierung - das Archiv reicht nur 93 Tage zurueck und wandert
0 8 * * *    cd /volume1/wetter && /usr/bin/python3 skripte/archiviere.py >> daten/archiv.log 2>&1
```

**Kontingent beachten.** Open-Meteo drosselt minuetlich (600), stuendlich
(5000) und taeglich (10000). Die **historischen** Endpunkte (`archive-api`,
`historical-forecast-api`) teilen sich ein Budget; `ensemble-api`,
`forecast-api` und `air-quality-api` haben ein eigenes — gemessen am
14.08.2026, als die historischen gesperrt waren und die uebrigen liefen.
Die Endpunkte hatten dabei unterschiedliche Zustaende, teilen sich also kein
einziges Konto — aber das schuetzt den Betrieb **nicht**: eine halbe Stunde
spaeter war auch `ensemble-api` erschoepft. **Vor jedem groesseren Lauf
`--trocken` pruefen statt auf eine Theorie ueber das Kontingent zu bauen.**

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
