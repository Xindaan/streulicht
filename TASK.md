# TASK

Sonnenuntergangs-Alarm Berlin. Zwei bis zehn Tage im Voraus eine
Wahrscheinlichkeit fuer einen aussergewoehnlichen Sonnenuntergang melden.

Etappen: E0 Score-Design (fertig) · E1 Backfill und Kalibrierung (laeuft) ·
E2 Alarm · E3 Oberflaeche.

## Doing

### T-0001 Fotoarchiv-Gate
Zaehlen, wie viele geotaggte Abendfotos (SU ±30 min) in der Mediathek liegen.
Entscheidet, ob der Presence-Only-Abbruchtest aus E0 existiert.
**BLOCKIERT:** macOS-TCC verweigert den Zugriff. Braucht Festplattenvollzugriff
fuer die Terminal-App in den Systemeinstellungen.
- [ ] n >= 40 komfortabel, n >= 20 grenzwertig, darunter faellt der Test aus
- Skript: `skripte/fotos_zaehlen.py`

### T-0003 Taegliche Ensemble-Archivierung
Das Ensemble-Archiv reicht nur 93 Tage zurueck und wandert. Ein Cron, der
nichts tut ausser den Tagesabzug wegschreiben. Haengt an keiner Entscheidung.
- [ ] ECMWF ENS, native 3-h-Schritte, Fanpunkte, taeglich nach dem 00z-Lauf

## Next

### T-0004 Score implementieren
Term A (Schirm) und Term B (Fenster) nach E0, pro Member, pro Schirmniveau.
- [ ] Fanpunkte: 5 Azimute A+{-24,-12,0,12,24}°, Distanzen 0..450 km
- [ ] Zwei-Pass-Abfrage fuer die semi-Lagrangesche Advektion
- [ ] Score pro Member rechnen, nie aus Mittelfeldern (Jensen)

### T-0005 Interpolationsexperiment
ECMWF native 3 h auf 6 h ausduennen, Mittelpunkte per Euler und per
Semi-Lagrange rekonstruieren, gegen die echten 3-h-Werte messen.
Braucht kein ERA5 — die 3-h-Werte sind selbst die Wahrheit.

### T-0006 Ablation volle Niveauzuordnung gegen 3-Schicht-Aggregat
Entscheidet, ob die Druckflaechen-Maschinerie noetig ist. Load-bearing:
die Klimatologie kommt aus einem anderen Modell als der Betrieb.

### T-0007 Gelaende in den Fensterterm
DEM-Freigaengigkeit des Strahls. Ab freier Ortswahl zwingend, nicht optional
(Muenchen im Dezember: Alpen bei 250 km, Strahl bei 1,22 km).

### T-0008 Dispersion und Skill ueber Vorlauf
Rangdiagramm des Scores; Korrelation Ensemble-Median gegen Kurzfrist-Score
je Vorlaufstufe. BSS erst, wenn genug Archiv da ist (T-0003).

## Backlog

- T-0009 Eigene Bewertungsseite und ntfy-Rueckkanal (E2)
- T-0010 Streifen + Vertikalschnitt als statische Seite auf GitHub Pages (E3)
- T-0011 Aerosol als Partialkorrelation pruefen (CAMS, nur Vorlauf <= 5 d)
- T-0012 Kondensstreifen: RH_eis 100..130 % auf 250/200 hPa als Zusatzsignal
- T-0013 s\*-Portabilitaet ueber 3-5 Ankerorte pruefen (streut s\* < 15 %?)

## Done

- **T-0000 E0 Score-Design** (14.08.2026) — Zweiterm-Score multiplikativ,
  entfernungsabhaengige Niveauzuordnung, semi-Lagrangesche Interpolation,
  Validierungsplan. Korrekturen: Juni-Sonnenuntergang 19:33 statt 17:30 UTC;
  Fensterband 200-400 km statt 100-200 km.
- **T-0002 Klimatologie und Schwellwert** (14.08.2026) — ERA5 2022-2025,
  1461 Abende, 3-Schicht auf 0.5-Grad-Gitter. **s\* = 0.6325 → 18.5
  Ausloesungen/Jahr.** Januar null von 124. r(A,B) = -0.259. Offen bleibt die
  Quantilbruecke auf ECMWF (haengt an T-0006).
- **Gates E1** (14.08.2026) — Modellverifikation, Wolkendiagnostik kalibriert,
  Geometrie gegen unabhaengige Quelle geprueft. Siehe `docs/befunde-e1.md`.
