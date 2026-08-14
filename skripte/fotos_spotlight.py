"""Fotogate ohne Mediathek-Zugriff: geotaggte Bilder im Dateisystem via Spotlight.

Die Photos-Mediathek ist TCC-geschuetzt (Festplattenvollzugriff fuer
/Applications/Claude.app).  Exportierte und abgelegte Bilder daneben sind es
nicht - und Spotlight hat ihre Geodaten laengst indiziert.

Der GPS-Filter loest nebenbei ein zweites Problem: Spiegelreflexkameras
speichern Ortszeit ohne Zonenangabe, Telefone speichern Zone und GPS.  Wer
Geodaten hat, hat meist auch einen vertrauenswuerdigen Zeitstempel.

EINGEBAUTE GEGENPROBE: ausgegeben wird die Verteilung von (Aufnahmezeit minus
Sonnenuntergang).  Liegt deren Gipfel nicht nahe null, sondern bei +/- 1 oder
2 Stunden, ist die Zeitzonenbehandlung falsch - dann steht das im Ergebnis,
statt still die Trefferzahl zu druecken.
"""
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import sonnenuntergang  # noqa: E402

ORTE = ["~/Pictures", "~/Documents", "~/Desktop", "~/Downloads"]
FENSTER_MIN = 30
BERLIN = (52.2, 52.8, 13.0, 13.9)


def finde():
    treffer = set()
    for ort in ORTE:
        p = os.path.expanduser(ort)
        if not os.path.isdir(p):
            continue
        r = subprocess.run(
            ["mdfind", "-onlyin", p,
             'kMDItemLatitude > -91 && kMDItemContentTypeTree == "public.image"'],
            capture_output=True, text=True)
        treffer.update(x for x in r.stdout.splitlines() if x)
    return sorted(treffer)


def metadaten(dateien, block=150):
    """[(zeitpunkt_utc, lat, lon)] via `mdls -raw`.

    Bei mehreren Dateien gibt mdls die Datensaetze OHNE Trennzeile und ohne
    Dateinamen aus - reine Konkatenation.  Mit -raw sind die Werte
    NUL-getrennt und in der Reihenfolge der -name-Argumente, das ist
    eindeutig.  (Die zeilenbasierte Variante hat 1283 von 1290 Dateien
    verschluckt, ohne einen Fehler zu melden.)
    """
    felder = ["kMDItemContentCreationDate", "kMDItemLatitude",
              "kMDItemLongitude"]
    aus = []
    for i in range(0, len(dateien), block):
        teil = dateien[i:i + block]
        r = subprocess.run(
            ["mdls", "-raw", "-nullMarker", "-"]
            + [x for f in felder for x in ("-name", f)] + teil,
            capture_output=True, text=True)
        werte = r.stdout.split("\0")
        for k in range(0, len(werte) - len(felder) + 1, len(felder)):
            roh, sla, slo = werte[k:k + len(felder)]
            try:
                la, lo = float(sla), float(slo)
                wann = datetime.strptime(roh.strip()[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            if abs(la) > 90 or abs(lo) > 180:
                continue
            aus.append((wann.replace(tzinfo=timezone.utc), la, lo))
    return aus


def main():
    dateien = finde()
    print("geotaggte Bilddateien laut Spotlight: %d" % len(dateien))
    if not dateien:
        raise SystemExit("keine gefunden")
    punkte = metadaten(dateien)
    print("davon mit lesbarem Zeitstempel und Koordinaten: %d" % len(punkte))

    versatz, treffer = [], []
    for wann, la, lo in punkte:
        h, _ = sonnenuntergang(wann.date(), la, lo)
        if h is None:
            continue
        su = wann.replace(hour=0, minute=0, second=0, microsecond=0) \
            + timedelta(hours=h)
        dmin = (wann - su).total_seconds() / 60.0
        if abs(dmin) <= 6 * 60:
            versatz.append(dmin)
        if abs(dmin) <= FENSTER_MIN:
            treffer.append((wann, la, lo))

    print()
    print("=== Gegenprobe Zeitzone: Aufnahmezeit minus Sonnenuntergang")
    eimer = Counter(int(d // 60) for d in versatz)
    for s in range(-6, 6):
        n = eimer.get(s, 0)
        print("   %+3d..%+3d h  %4d  %s" % (s, s + 1, n, "#" * min(60, n // 2)))
    if versatz:
        gipfel = max(eimer, key=lambda k: eimer[k])
        print("   Gipfel bei %+d..%+d h - %s" % (
            gipfel, gipfel + 1,
            "plausibel" if gipfel in (-1, 0) else
            "VERDAECHTIG, moeglicher Zeitzonenfehler"))

    print()
    abende = {}
    for wann, la, lo in treffer:
        abende.setdefault((wann.date(), round(la, 1), round(lo, 1)), 0)
        abende[(wann.date(), round(la, 1), round(lo, 1))] += 1
    berlin = {k for k in abende
              if BERLIN[0] <= k[1] <= BERLIN[1] and BERLIN[2] <= k[2] <= BERLIN[3]}
    print("=== Fotos im Fenster SU +/- %d min: %d" % (FENSTER_MIN, len(treffer)))
    print("=== eindeutige (Abend, Ort)-Paare: %d" % len(abende))
    print("=== davon Raum Berlin: %d" % len(berlin))
    print()
    print("Schwelle laut E0: n >= 40 komfortabel, n >= 20 grenzwertig.")
    print()
    print("Jahresverteilung (alle Orte / Berlin):")
    for j in sorted({k[0].year for k in abende}):
        a = sum(1 for k in abende if k[0].year == j)
        b = sum(1 for k in berlin if k[0].year == j)
        print("   %d: %3d / %d" % (j, a, b))

    import json
    ziel = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "daten", "foto_abende.json")
    with open(ziel, "w") as f:
        json.dump({"alle": [{"tag": str(k[0]), "lat": k[1], "lon": k[2],
                             "n_fotos": v} for k, v in sorted(abende.items())],
                   "berlin": [str(k[0]) for k in sorted(berlin)]}, f, indent=1)
    print("\ngeschrieben: %s" % ziel)


if __name__ == "__main__":
    main()
