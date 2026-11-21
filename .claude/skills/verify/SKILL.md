---
name: verify
description: Streulicht Ende-zu-Ende pruefen - Seiten aus echten Betriebsdaten bauen und alle Tests fahren, im Sandkasten, ohne Netz und ohne Push. Vor jedem Commit verwenden, nach jeder Aenderung an skripte/, sonnen/, web/bewerten.html, stil/ oder konfig.json, und bevor "gruen" gemeldet wird.
---

# verify

Ein Befehl, ein Urteil. Aus dem Arbeitsbaum, der geprueft werden soll:

```bash
"$(git worktree list --porcelain | sed -n '1s/^worktree //p')/.venv/bin/python3" .claude/skills/verify/verify.py
```

Letzte Zeile `VERIFY GRUEN: ...` und Exitcode 0, sonst `VERIFY ROT (n): ...`
mit je einer Zeile Grund (Exitcode 1). Exitcode 2 heisst: eine Voraussetzung
fehlt (venv, Betriebsdaten, node) - das ist kein Befund am Code.
Dauer rund 20 Sekunden.

## Was dabei laeuft

1. **Sandkasten.** Der Arbeitsbaum wird so, wie er jetzt dasteht (getrackte
   und neue Dateien, mit ungespeicherten Aenderungen), in ein Temp-Verzeichnis
   kopiert. `daten/` kommt als eingefrorener Schnappschuss der Betriebsdaten
   dazu (aus dem eigenen Baum, sonst aus dem Haupt-Checkout). Arbeitsbaum und
   Betriebsdaten werden nur gelesen; die vier launchd-Agenten merken nichts.
2. **Bau.** `skripte/ausliefern.py --trocken` erzeugt aus dem Schnappschuss
   Prognoseseite, Bewertungsseite je Ort und Bilanzseite. `--trocken` sichert
   nicht und pusht nicht.
3. **Ergebnis.** Jede erwartete Seite ist in diesem Lauf neu entstanden und
   nicht leer; `skripte/waechter.py` findet in der Prognoseseite einen
   lesbaren Abrufzeitpunkt.
4. **Tests.** Jede `skripte/test_*.py` und `skripte/test_*.js` einzeln und
   nacheinander. Gezaehlt werden die `ok`-Zeilen; eine Datei ohne `ok`-Zeile
   gilt als rot, auch mit Exitcode 0.

## Warum es nicht flackert

- Kein Netz: die Seitenbauer holen nichts, die Tests bringen ihr Netz selbst
  mit. Der echte Abruf (`skripte/alarm.py`) laeuft hier NIE - ein Lauf kostet
  rund 4.160 Kontingent-Einheiten, zwei am Tag sind der Betrieb, ein dritter
  sprengt das Tageslimit.
- Feste Daten: der Schnappschuss wird einmal gezogen und bis zu 20 Stunden
  wiederverwendet. Zwei Laeufe ueber demselben Code liefern dieselben Zahlen.
  `--frisch` zieht ihn neu.
- Keine Parallelitaet: einige Tests messen Fristen und toeten Kindprozesse.
- Kein Bytecode: `-B`, und der Sandkasten wird je Lauf neu aufgebaut.
- Der Waechter prueft hier nur, DASS ein Abrufzeitpunkt da ist. Wie alt er
  ist, haengt am Betrieb und nicht am Code.

## Lesen

- Die Pruefzahl in der letzten Zeile ist der Pass-Count fuer Chat und
  STATE.md. Sinkt sie ohne Absicht, ist eine Pruefung verschwunden.
- Bei Rot stehen die letzten Zeilen jeder roten Datei direkt in der Ausgabe,
  die vollen Ausgaben unter `<Sandkasten>/ausgaben/`. Der Pfad des
  Sandkastens ist die erste Ausgabezeile.
- `--nur MUSTER` faehrt nur Testdateien, deren Name das Muster enthaelt (Bau
  und Ergebnis laufen immer). Zum Eingrenzen, nicht als Freigabe: vor dem
  Commit laeuft alles.

## Negativprobe

Gruen zaehlt erst, wenn die Pruefung den Fehler auch findet: den behobenen
Fehler in einem Wegwerf-Worktree wieder einbauen (`git worktree add --detach
<pfad> HEAD`), dort denselben Befehl mit dem `verify.py` dieses Baums
aufrufen, Rot nachweisen, Worktree entfernen. Nicht im Arbeitsbaum proben, in
dem gerade gearbeitet wird.

## Grenzen

- Geprueft wird der Weg Zustand -> Seiten und das Verhalten der Skripte gegen
  erfundenes Netz. Nicht geprueft: der echte Abruf, der echte ntfy-Versand,
  der echte Push nach `gh-pages`, die installierten launchd-Agenten.
- Die Analyse- und Forschungsskripte ohne eigene Testdatei laufen hier nicht
  (nur `test_syntax.py` uebersetzt sie).
- `STREULICHT_VERIFY_DIR` legt den Sandkasten an einen anderen Ort.
