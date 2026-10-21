# STATE

Stand 21.10.2026. Langtext bis 13.10.: `docs/state_archiv_2026-10-21.md` (wortgleich).

## Ziel

Bis zu zehn Abende voraus eine Wahrscheinlichkeit fuer einen
aussergewoehnlichen Sonnenuntergang in Berlin melden (belastbar ab etwa ein
bis drei Tagen, weiter voraus nur Tendenz; T-0085) — und den Abend danach
zeigen.

Erfolgskriterium (Vorschlag, von Andre unbestaetigt): Nach 6-8 Wochen
Livebetrieb zeigt die Bilanzseite Trefferquote und Alarmrate gegen Andres
Noten; die Alarmrate liegt in der Naehe der geeichten 18,5 Ausloesungen/Jahr
(T-0020, T-0035), und kein Tag bleibt ohne Lauf, ohne dass der Waechter es meldet.

## Status

- Betrieb: vier launchd-Agenten (alarm, bewertung, erinnerung, seite;
  `betrieb/*.plist`, Interpreter `.venv/bin/python3`) plus GitHub-Action
  `.github/workflows/waechter.yml` (alle 6 h, prueft das Alter der Seite).
- Review-Block T-0074 bis T-0087 abgeschlossen (Done, 13.10.2026). Pass-2-Deckel
  `pass2_max_zellen` = 200 (`konfig.json`); ein Lauf kostet ca. 4.160
  Kontingent-Einheiten, die 51 Member zaehlen mit. Stand 13.10.: seit 11.10.
  kein Kontingentabbruch, Waechter gruen. Danach kein Commit; Betrieb seither
  nicht erneut geprueft.
- Modell `ecmwf_ifs025` (51 Member); s\* = 0.7065 (ca. 18,5 Ausloesungen/Jahr).
  Fotoabend-Test bleibt unentschieden (T-0001b), das Album ist das schaerfere Instrument.
- Teststand 13.10.: 888 Python in 29 Dateien + 64 JS gruen (nicht neu gelaufen).
- WeatherNext 3 (T-0072): Leser `skripte/wn3.py` steht, netzfrei getestet;
  Betrieb nicht verdrahtet, `ecmwf_ifs025` bleibt Rueckfall.

## Live-Risiken / Stolpersteine

- Kontingent: Memberzahl multipliziert (siehe README "Was die Grenze kostet"). Zwei volle Laeufe am Tag (8.320) liegen
  knapp unter dem Tageslimit 10.000; ein dritter Abruf reisst es.
- Agenten scheitern still: ein kaputter Interpreterpfad schreibt nichts ins Log,
  nur `launchctl print` zeigt `last exit code` (T-0040, offen; T-0075 deckt nur
  das Seitenalter ab). Mac ganz aus = alte Seite, der Waechter meldet es.
- s\* ist modellspezifisch: WN3 wuerde s\* 3 von 11 Abenden reissen (ECMWF 0),
  einmal bei Note 0. Kein Modellwechsel ohne neue Schwelle (T-0072).
- Die Quantilbruecke (s\* aus Analysen, Betrieb auf ENS-Membern) ist nie
  gemessen; der Livegang ist die Messung (T-0020).

## Bei Dir

- Optional Repo-Secret `NTFY_WAECHTER` (T-0075), sonst meldet der Waechter per Mail.
- Neues Topic als `ntfy_erinnerung` in `konfig_geheim.json`, abonnieren, altes
  Bewertungs-Topic abbestellen (T-0077, README "Abenderinnerung empfangen").
- `sicherung_ordner` in `konfig.json` setzen (z. B. iCloud) und das
  Time-Machine-Netzziel reparieren (T-0081).
- Erfolgskriterium oben bestaetigen oder korrigieren.
- Beobachten: `daten/alarm.log` auf "Kontingent nach" (soll nicht kommen) und
  "GEDECKELT" (Deckel 200 greift); Platz von `daten/cache/abruf/`.

## Next actions

1. T-0072 weiterbauen: erst s\* fuer WN3 klaeren (Quantilabbildung ueber eine
   Ueberlappungsperiode), WN3-Medianfeld je Lauf mitschreiben, dann Betriebsvehikel.
2. T-0008 Dispersion und Skill ueber Vorlauf (traegt die Pruefung der
   Vorlauf-Aussage T-0085 und des Quantils "auffaellig" T-0084, nach Winter/Fruehjahr).
3. T-0040 Ueberwachung der Exitcodes (Backlog, ergaenzt durch T-0075).

## Termine

- Ab ca. 23.10.2026 (abgeleitet: zwei Wochen nach T-0087 vom 09.10.): Cache-Teilung
  des Nachtlaufs im `alarm.log` nachzaehlen (T-0088).
- 16.10. bis 30.10.2026 (abgeleitet: 04.09. + 6-8 Wochen): Fenster, in dem
  s\*/p\* aus dem Livearchiv nachgezogen werden koennen (T-0020).
- Winter/Fruehjahr 2026/27, undatiert: Q fuer "auffaellig" (T-0084) und die
  Vorlauf-Aussage (T-0085) neu messen.

## Letzte Done

- 13.10.2026 T-0074 bis T-0087 Review-Block: Blockcache und Kontingentsperre,
  Pass-2-Deckel 200, Waechter, Stufen aus Memberanteil, Nachtlauf, Sichtfaktor C.
- 09.10.2026 T-0077/T-0079/T-0080/T-0081/T-0083: Topic, Tests, UI, Logrotation, WN3-Leser.
- 04.09.2026 T-0063 bis T-0071 Fremdreview (Advektion, Median statt Bestmember).
- 30.08.2026 T-0062 Agenten auf Homebrew python@3.13; 04.09. T-0063 Advektion stromauf.
<!-- snapshot-ende -->
