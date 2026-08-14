"""Kalibriert den Eiszweig der Wolkendiagnostik.

Ziel: GFS' NATIVE cloud_cover_high (kondensatbasiert, am 14.08.2026 als nativ
verifiziert - Streuung bis 95 Prozentpunkte innerhalb eines RH-Profil-Bins).
Eingang: GFS' eigene RH und T auf 400/300/250/200 hPa, gleicher Lauf, gleiche
Stunde.  Damit ist der Vergleich modellintern konsistent; verglichen wird nur
die Diagnostik, nicht zwei Modellzustaende.

Mitgefittet wird das Ueberlappungsschema - dieselbe Frage steckt im
Fensterterm des Scores (Exponent k), also faellt die Antwort hier gratis ab.
"""
import json
import math
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen import feuchte as f  # noqa: E402

NIVEAUS = (400, 300, 250, 200)
ORT = (52.52, 13.405)
JAHRE = ("2023", "2024", "2025")
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "daten", "gfs_hoch_berlin.json")


def lade():
    if os.path.exists(CACHE):
        with open(CACHE) as fh:
            return json.load(fh)
    vs = (["relative_humidity_%dhPa" % p for p in NIVEAUS]
          + ["temperature_%dhPa" % p for p in NIVEAUS] + ["cloud_cover_high"])
    zus = {}
    for jahr in JAHRE:
        u = ("https://historical-forecast-api.open-meteo.com/v1/forecast"
             "?latitude=%s&longitude=%s&models=gfs_global&hourly=%s"
             "&start_date=%s-01-01&end_date=%s-12-31"
             % (ORT[0], ORT[1], ",".join(vs), jahr, jahr))
        with urllib.request.urlopen(u, timeout=300) as fh:
            h = json.load(fh)["hourly"]
        for k, v in h.items():
            zus.setdefault(k, []).extend(v)
        print("  %s: %d Stunden" % (jahr, len(h["time"])))
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w") as fh:
        json.dump(zus, fh)
    return zus


def zeilen(h):
    """(Liste[(rh, t)] je Niveau, beobachtete Hochbewoelkung 0..1)."""
    for i in range(len(h["time"])):
        y = h["cloud_cover_high"][i]
        if y is None:
            continue
        prof = []
        for p in NIVEAUS:
            rh = h["relative_humidity_%dhPa" % p][i]
            t = h["temperature_%dhPa" % p][i]
            if rh is None or t is None:
                prof = None
                break
            prof.append((rh, t))
        if prof:
            yield prof, y / 100.0


def aggregiere(cs, modus):
    if modus == "max":
        return max(cs)
    if modus == "zufall":
        p = 1.0
        for c in cs:
            p *= (1.0 - c)
        return 1.0 - p
    raise ValueError(modus)


def guete(daten, rc, rs, modus):
    n = sq = 0.0
    sx = sy = sxx = syy = sxy = 0.0
    for prof, y in daten:
        cs = []
        for rh, t in prof:
            rhi = f.rh_eis_aus_wasser(rh / 100.0, t)
            cs.append(f._sundqvist(rhi, rc, rs))
        x = aggregiere(cs, modus)
        n += 1
        sq += (x - y) ** 2
        sx += x
        sy += y
        sxx += x * x
        syy += y * y
        sxy += x * y
    rmse = math.sqrt(sq / n)
    nen = math.sqrt(max(1e-12, (n * sxx - sx * sx) * (n * syy - sy * sy)))
    return rmse, (n * sxy - sx * sy) / nen, sx / n, sy / n


def main():
    print("Lade GFS-Archiv Berlin ...")
    h = lade()
    daten = list(zeilen(h))
    print("verwendbare Stunden: %d\n" % len(daten))

    # Vergleichsmassstab: Open-Meteos Diagnostik (Wasser, RH_crit 0.70)
    n = sq = 0.0
    sx = sy = sxx = syy = sxy = 0.0
    for prof, y in daten:
        x = aggregiere([f.bedeckung_openmeteo(rh) for rh, _ in prof], "max")
        n += 1
        sq += (x - y) ** 2
        sx += x
        sy += y
        sxx += x * x
        syy += y * y
        sxy += x * y
    rm = math.sqrt(sq / n)
    rr = (n * sxy - sx * sy) / math.sqrt((n * sxx - sx * sx) * (n * syy - sy * sy))
    print("Referenz Open-Meteo (Wasser, RHc=0.70, max-Ueberlapp):")
    print("   RMSE %.4f   r %.4f   Mittel Diagnose %.3f / GFS %.3f\n"
          % (rm, rr, sx / n, sy / n))

    best = None
    print("Gittersuche Eiszweig:")
    for modus in ("max", "zufall"):
        for rc10 in range(60, 101, 5):
            for rs10 in range(105, 165, 5):
                rc, rs = rc10 / 100.0, rs10 / 100.0
                if rs <= rc:
                    continue
                res = guete(daten, rc, rs, modus)
                if best is None or res[0] < best[0]:
                    best = (res[0], res[1], rc, rs, modus, res[2], res[3])
    print("   bestes RMSE %.4f  r %.4f  bei RH_crit_eis=%.2f  RH_sat_eis=%.2f  "
          "Ueberlapp=%s" % (best[0], best[1], best[2], best[3], best[4]))
    print("   Mittel Diagnose %.3f / GFS %.3f" % (best[5], best[6]))
    print("\n   Verbesserung RMSE: %.1f %%   r: %+.3f"
          % (100 * (rm - best[0]) / rm, best[1] - rr))

    print("\nSensitivitaet um das Optimum (RMSE):")
    for rc in (best[2] - 0.05, best[2], best[2] + 0.05):
        zeile = []
        for rs in (best[3] - 0.10, best[3], best[3] + 0.10):
            if rs <= rc:
                zeile.append("     -")
                continue
            zeile.append("%.4f" % guete(daten, rc, rs, best[4])[0])
        print("   RHc=%.2f : %s" % (rc, "  ".join(zeile)))


if __name__ == "__main__":
    main()
