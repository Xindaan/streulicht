# STATE

Stand 04.11.2026. Langtext bis 13.10.: `docs/state_archiv_2026-10-21.md` (wortgleich).

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
  ca. 4.160 Kontingent-Einheiten; Betrieb seit 13.10. nicht erneut geprueft.
- Repo ist PUBLIC: Klarname im aktuellen Stand ersetzt, pre-push-Guard aktiv
  (`tools/install_push_guard.sh`, Marker lokal in `.private/`). Historie bleibt
  unveraendert (entschieden 04.11.); Betriebsbezeichner offen (T-0089).
- WN3 (T-0072): s*-Verfahren gebaut (`skripte/wn3_quantil.py`,
  Quantilabbildung an denselben Abenden); WN3-Seite holt sich kostenlos,
  Vollabruf 2026 laeuft (`daten/wn3_quantil.log`). Referenz 2026: Block 1
  von 2 geholt (04.11.), Block 2 am 05.11.
- Teststand 04.11.: 912 Python-Pruefungen in 31 Dateien + 64 JS gruen.

## Live-Risiken / Stolpersteine

- Kontingent: zwei volle Laeufe (8.320) liegen knapp unter dem Tageslimit
  10.000; Gardena teilt die IP. Jeder Zusatzabruf (auch Klimatologie-Nachholen)
  muss in diese Bilanz.
- Agenten scheitern still (T-0040, offen; T-0075 deckt nur das Seitenalter ab).
- s* ist modellspezifisch: kein Modellwechsel ohne neue Schwelle (T-0072).
- Die Quantilbruecke Analyse -> ENS-Member ist nie gemessen (T-0020); fuer
  WN3 gilt dieselbe offene Bruecke p50-Feld -> Member.

## Bei Dir

- T-0089: Betriebsbezeichner (Home-Pfade in Plists, Labels, Datendateiname)
  umstellen oder lassen. (Historie bleibt, entschieden 04.11.)
- T-0072: Block 2 der Klimatologie 2026 am 05.11. vor 09:50 Uhr anstossen
  (Befehl in TASK.md T-0072); Planen per Aufgabe war hier nicht erlaubt.
- Optional Repo-Secret `NTFY_WAECHTER` (T-0075); neues Topic `ntfy_erinnerung`
  (T-0077); `sicherung_ordner` und Time-Machine-Ziel (T-0081).
- Erfolgskriterium oben bestaetigen oder korrigieren.

## Next actions

1. T-0072: Block 2 Klimatologie 2026 (05.11.), dann `wn3_quantil.py`
   auswerten und s*_WN3 mit Intervall festhalten.
2. T-0089 nach Entscheidung umsetzen.
3. T-0008 Dispersion und Skill ueber Vorlauf (nach Winter/Fruehjahr).

## Termine

- 16.10. bis 30.10.2026 verstrichen: s*/p* aus dem Livearchiv nachziehen (T-0020) offen.
- Winter/Fruehjahr 2026/27, undatiert: Q fuer "auffaellig" (T-0084) und
  Vorlauf-Aussage (T-0085) neu messen.

## Letzte Done

- 04.11.2026 T-0089 (Teil): Klarname aus dem aktuellen Stand, pre-push-Guard.
- 04.11.2026 T-0072 (Teil): s*-Verfahren fuer WN3, Mitschreib-Praemisse widerlegt.
- 13.10.2026 T-0074 bis T-0087 Review-Block (Blockcache, Deckel 200, Waechter, Stufen).
- 09.10.2026 T-0077/T-0079/T-0080/T-0081/T-0083: Topic, Tests, UI, Logrotation, WN3-Leser.
- 04.09.2026 T-0063 bis T-0071 Fremdreview (Advektion, Median statt Bestmember).
<!-- snapshot-ende -->
