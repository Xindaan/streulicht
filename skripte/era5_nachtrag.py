"""Traegt einzelne Abende in die ERA5-Klimatologie nach.

WARUM.  Die Klimatologie endet am 31.12.2025, der Aufloesungstest (icond2.py)
zieht seine Kontrollabende aber bis August 2026.  Von 35 gepaarten Bloecken
haetten deshalb nur 11 einen ERA5-Vergleichswert gehabt - unter der eigenen
Mindestgrenze von 12.

Warum nicht `klimatologie.py`: das holt immer ganze Jahre (start_date
fest auf 01-01).  Fuer 44 einzelne Abende ist das um Groessenordnungen zu
teuer, und `archive-api` teilt sich sein Tagesbudget mit
`historical-forecast-api`, aus dem gerade der ICON-Faecher kommt.

WICHTIG - dieselbe Rasterung wie die bestehende Klimatologie.  Dort wird auf
ein 0.5-Grad-Gitter gerundet und die Zellmitte abgefragt, nicht der exakte
Faecherpunkt.  Wer hier exakt abfragt, erzeugt Werte, die mit 2015-2025 nicht
vergleichbar sind - und der gepaarte Vergleich wuerde einen Rasterungseffekt
als Modellunterschied ausweisen.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import sonnenuntergang  # noqa: E402
from sonnen.score import faecherpunkte, score  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(BASIS, "daten", "roh_era5_nachtrag")
GITTER = 0.5
SCHICHTEN = ("low", "mid", "high")
VARIABLEN = ",".join("cloud_cover_%s" % s for s in SCHICHTEN)


def zelle(lat, lon):
    return (round(lat / GITTER), round(lon / GITTER))


def zellmitte(z):
    return (z[0] * GITTER, z[1] * GITTER)


def _hole(u):
    for n in range(6):
        try:
            with urllib.request.urlopen(u, timeout=300) as f:
                return json.load(f)
        except urllib.error.HTTPError as e:
            try:
                grund = json.loads(e.read()).get("reason", "")
            except Exception:                                    # noqa: BLE001
                grund = ""
            if e.code == 429 and "oncurrent" in grund:
                time.sleep(2.0 + 2.0 * n)
                continue
            if e.code == 429 and "inutely" in grund and n < 5:
                print("      Minutenlimit, warte 65 s ...", flush=True)
                time.sleep(65)
                continue
            if e.code == 429:
                raise SystemExit("Kontingent: %s (Cache haelt)" % grund)
            raise
        except Exception:                                        # noqa: BLE001
            if n < 5:
                time.sleep(3)
                continue
            raise
    raise SystemExit("unerreichbar")


def hole_tag(tag, breite, laenge, block=40):
    """{Zelle: {schicht: Wert}} zur Sonnenuntergangsstunde des Abends."""
    p = os.path.join(CACHE, "%s.json" % tag)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    d = date.fromisoformat(tag)
    stunde, azimut = sonnenuntergang(d, breite, laenge)
    marke = "%sT%02d:00" % (tag, int(round(stunde)) % 24)
    zellen = sorted({zelle(la, lo)
                     for _, _, la, lo in faecherpunkte(breite, laenge, azimut)})

    aus = {}
    for i in range(0, len(zellen), block):
        teil = zellen[i:i + block]
        mitten = [zellmitte(z) for z in teil]
        u = ("https://archive-api.open-meteo.com/v1/archive?latitude=%s&longitude=%s"
             "&hourly=%s&start_date=%s&end_date=%s"
             % (",".join("%.4f" % m[0] for m in mitten),
                ",".join("%.4f" % m[1] for m in mitten), VARIABLEN, tag, tag))
        e = _hole(u)
        if isinstance(e, dict):
            e = [e]
        for z, eintrag in zip(teil, e):
            h = eintrag["hourly"]
            try:
                k = h["time"].index(marke)
            except ValueError:
                continue
            aus["%d/%d" % z] = {s: h["cloud_cover_%s" % s][k] for s in SCHICHTEN}
    os.makedirs(CACHE, exist_ok=True)
    with open(p, "w") as f:
        json.dump(aus, f)
    return aus


def score_fuer(tag, breite, laenge):
    felder = hole_tag(tag, breite, laenge)
    d = date.fromisoformat(tag)
    _, azimut = sonnenuntergang(d, breite, laenge)
    karte = {(dd, dv): zelle(la, lo)
             for dd, dv, la, lo in faecherpunkte(breite, laenge, azimut)}

    def hole(dd, dv, schicht):
        z = karte.get((dd, dv))
        if z is None:
            return None
        v = felder.get("%d/%d" % z, {}).get(schicht)
        return None if v is None else v / 100.0
    return score(hole)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ziel", default=os.path.join(
        BASIS, "daten", "score_berlin_g0.5_2015_2025.json"))
    ap.add_argument("--breite", type=float, default=52.52)
    ap.add_argument("--laenge", type=float, default=13.405)
    a = ap.parse_args()

    with open(os.path.join(BASIS, "daten", "icond2_plan.json")) as f:
        plan = json.load(f)
    with open(a.ziel) as f:
        klima = json.load(f)

    noetig = sorted({t for t in
                     set(plan["ziel"]) | {k for v in plan["paare"].values()
                                          for k in v}
                     if t not in klima})
    print("Abende ohne ERA5-Wert: %d" % len(noetig))
    if not noetig:
        return

    neu = 0
    for i, tag in enumerate(noetig, 1):
        s, det = score_fuer(tag, a.breite, a.laenge)
        if det is None:
            print("   %s  keine Daten - nicht eingetragen" % tag, flush=True)
            continue
        # Genau die Felder und genau den Ausdruck der bestehenden
        # Klimatologie verwenden (klimatologie.py nimmt det["B"], nicht
        # sicht*weg) - sonst sind die 2026er Eintraege nicht vergleichbar.
        klima[tag] = {"s": s, "schirm": det["schirm"], "A": det["A"],
                      "B": det["B"]}
        neu += 1
        if i % 10 == 0:
            print("   %d/%d" % (i, len(noetig)), flush=True)

    with open(a.ziel, "w") as f:
        json.dump(klima, f)
    print("%d Abende nachgetragen, Datei hat jetzt %d" % (neu, len(klima)))


if __name__ == "__main__":
    main()
