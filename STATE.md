# STATE

Stand 21.11.2026. Langtext bis 13.10.: `docs/state_archiv_2026-10-21.md` (wortgleich).

## Ziel

Bis zu zehn Abende voraus eine Wahrscheinlichkeit fuer einen
aussergewoehnlichen Sonnenuntergang in Berlin melden (belastbar ab etwa ein
bis drei Tagen, weiter voraus nur Tendenz; T-0085) — und den Abend danach
zeigen.

Erfolgskriterium (Vorschlag, vom Maintainer unbestaetigt): Nach 6-8 Wochen
Livebetrieb zeigt die Bilanzseite Trefferquote und Alarmrate gegen die Noten
des Maintainers; die Alarmrate liegt in der Naehe der geeichten 18,5
Ausloesungen/Jahr (T-0020, T-0035), und kein Tag bleibt ohne Lauf, ohne dass
der Waechter es meldet.

## Status

- Betrieb: vier launchd-Agenten (alarm, bewertung, erinnerung, seite;
  `betrieb/*.plist`, Interpreter `.venv/bin/python3`) plus GitHub-Action
  `.github/workflows/waechter.yml` (alle 6 h). Pass-2-Deckel 200, ein Lauf
  ca. 4.160 Kontingent-Einheiten. Gesehen am 21.11.: alle vier Agenten
  installiert, ausgelieferter Datenstand vom 21.11. 09:20 UTC.
- Pruefung: `.claude/skills/verify` baut die Seiten im Sandkasten aus einem
  Schnappschuss der Betriebsdaten und faehrt alle Tests (ein Befehl, rund
  20 s, ohne Netz, ohne Push). Teststand 21.11.: 917 Python-Pruefungen in
  31 Dateien + 64 JS gruen.
- Branch `aufraeumen-fable-2026-11` (lokal, nicht gemergt, nicht gepusht):
  vier Fehler behoben, Tests geschaerft, toter Code und Dopplungen entfernt,
  Kommentare und README angeglichen. Befunde ohne Fix: T-0090 bis T-0096.
- Repo ist PUBLIC, pre-push-Guard aktiv (`tools/install_push_guard.sh`).
- WN3 (T-0072): s*_WN3 = 0,7144, 90-%-Intervall [0,6293; 0,8364], aus
  305 gepaarten Abenden 2026 mit 14 Ereignissen ueber ECMWF s* = 0,7065
  (`skripte/wn3_quantil.py`).

## Live-Risiken / Stolpersteine

- Kontingent: zwei volle Laeufe (8.320) liegen knapp unter dem Tageslimit
  10.000; Gardena teilt die IP. Jeder Zusatzabruf muss in diese Bilanz.
- Der pre-push-Guard laesst bei einem technischen Fehler durch: ein
  ungueltiges Markermuster ergibt Exitcode 128 und leeren Treffertext, der
  Guard meldet "sauber" (T-0091, gemessen 21.11.).
- Agenten scheitern still (T-0040, offen; T-0075 deckt nur das Seitenalter ab).
- s* ist modellspezifisch: kein Modellwechsel ohne neue Schwelle (T-0072).
- Die Quantilbruecke Analyse -> ENS-Member ist nie gemessen (T-0020); fuer
  WN3 gilt dieselbe offene Bruecke p50-Feld -> Member.

## Bei Dir

- Branch `aufraeumen-fable-2026-11` ansehen und mergen oder verwerfen.
- T-0072: Traegt s*_WN3 = 0,7144? Nur 14 Ereignisse, Intervall 0,63-0,84.
  Davon haengen Betriebsvehikel und der WN3-Weg in `alarm.py` ab.
- T-0094: `wn3.py` nennt als Vorgabe das Projekt `gardena-wetter` - gewollt?
- T-0092: Pass-2-Deckel im Code 320, im Betrieb 200 - welcher Rueckfall gilt?
- Optional Repo-Secret `NTFY_WAECHTER` (T-0075); neues Topic `ntfy_erinnerung`
  (T-0077); `sicherung_ordner` und Time-Machine-Ziel (T-0081).
- Erfolgskriterium oben bestaetigen oder korrigieren.

## Next actions

1. T-0072: nach der Entscheidung zu s*_WN3 Betriebsvehikel und Uebergabe
   klaeren, dann zweiter Weg in `alarm.py`.
2. T-0008 Dispersion und Skill ueber Vorlauf (nach Winter/Fruehjahr).
3. Vorschlag: T-0091 vorziehen (Guard fail-closed), danach T-0090 (Versand).

## Termine

- 16.10. bis 30.10.2026 verstrichen: s*/p* aus dem Livearchiv nachziehen (T-0020) offen.
- Winter/Fruehjahr 2026/27, undatiert: Q fuer "auffaellig" (T-0084) und
  Vorlauf-Aussage (T-0085) neu messen.

## Letzte Done

- 21.11.2026 Aufraeumlauf: verify-Skill, 4 Fehler, Tests, toter Code, Dopplungen (Branch).
- 05.11.2026 T-0072 (Teil): Referenz 2026 komplett, s*_WN3 = 0,7144 [0,63; 0,84].
- 04.11.2026 T-0089: Klarname aus dem Stand, pre-push-Guard, Option B (Notendatei, Commit-Adresse).
- 04.11.2026 T-0072 (Teil): s*-Verfahren fuer WN3, Mitschreib-Praemisse widerlegt.
- 13.10.2026 T-0074 bis T-0087 Review-Block (Blockcache, Deckel 200, Waechter, Stufen).
<!-- snapshot-ende -->
