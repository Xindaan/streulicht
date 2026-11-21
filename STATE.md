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
  20 s, ohne Netz, ohne Push). Teststand 21.11.: 931 Python-Pruefungen in
  32 Dateien + 64 JS gruen.
- Aufraeumlauf + T-0091/92/94-Teile am 21.11. lokal in main gemergt, nicht
  gepusht. Offene Befunde: T-0090 bis T-0096.
- Repo ist PUBLIC, pre-push-Guard aktiv (`tools/install_push_guard.sh`).
- WN3 (T-0072): s*_WN3 = 0,7144, 90-%-Intervall [0,6293; 0,8364], aus
  305 gepaarten Abenden 2026 mit 14 Ereignissen ueber ECMWF s* = 0,7065
  (`skripte/wn3_quantil.py`).

## Live-Risiken / Stolpersteine

- Kontingent: zwei volle Laeufe (8.320) liegen knapp unter dem Tageslimit
  10.000; Gardena teilt die IP. Jeder Zusatzabruf muss in diese Bilanz.
- Alarm kann bei zwei Orten doppelt gehen (T-0090); ohne `web/index.html`
  verschwindet die Prognoseseite beim Force-Push (T-0091-Rest).
- Agenten scheitern still (T-0040, offen; T-0075 deckt nur das Seitenalter ab).
- s* ist modellspezifisch: kein Modellwechsel ohne neue Schwelle (T-0072).
- Die Quantilbruecke Analyse -> ENS-Member ist nie gemessen (T-0020); fuer
  WN3 gilt dieselbe offene Bruecke p50-Feld -> Member.

## Bei Dir

- Push von main nach origin (Guard prueft jetzt fail-closed).
- T-0072: Traegt s*_WN3 = 0,7144? Nur 14 Ereignisse, Intervall 0,63-0,84.
  Davon haengen Betriebsvehikel und der WN3-Weg in `alarm.py` ab.
- `gardena-wetter` steht in der veroeffentlichten Historie (e5a2480), in
  TASK.md und `docs/review-2026-10-09.md`: so lassen oder auch dort tilgen?
- Optional Repo-Secret `NTFY_WAECHTER` (T-0075); neues Topic `ntfy_erinnerung`
  (T-0077); `sicherung_ordner` und Time-Machine-Ziel (T-0081).
- Erfolgskriterium oben bestaetigen oder korrigieren.

## Next actions

1. T-0072: nach der Entscheidung zu s*_WN3 Betriebsvehikel und Uebergabe
   klaeren, dann zweiter Weg in `alarm.py`.
2. T-0008 Dispersion und Skill ueber Vorlauf (nach Winter/Fruehjahr).
3. Vorschlag: T-0090 (Versand), danach T-0091-Rest (Auslieferung).

## Termine

- 16.10. bis 30.10.2026 verstrichen: s*/p* aus dem Livearchiv nachziehen (T-0020) offen.
- Winter/Fruehjahr 2026/27, undatiert: Q fuer "auffaellig" (T-0084) und
  Vorlauf-Aussage (T-0085) neu messen.

## Letzte Done

- 21.11.2026 T-0091/T-0092/T-0094 (Teile): Guard fail-closed, Deckel 200, `wn3.py` ohne Vorgabe.
- 21.11.2026 Aufraeumlauf: verify-Skill, 4 Fehler, Tests, toter Code, Dopplungen.
- 05.11.2026 T-0072 (Teil): Referenz 2026 komplett, s*_WN3 = 0,7144 [0,63; 0,84].
- 04.11.2026 T-0089: Klarname aus dem Stand, pre-push-Guard, Option B (Notendatei, Commit-Adresse).
- 04.11.2026 T-0072 (Teil): s*-Verfahren fuer WN3, Mitschreib-Praemisse widerlegt.
<!-- snapshot-ende -->
