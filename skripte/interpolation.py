"""T-0005: taugt lineare Zeitinterpolation, oder braucht es Advektion?

Versuchsaufbau ohne fremde Wahrheit: ECMWF ENS liefert nativ 3-h-Schritte.
Wir duennen auf 6 h aus, rekonstruieren die uebersprungenen Mittelpunkte und
vergleichen gegen die echten 3-h-Werte.  Die Wahrheit ist also das Modell
selbst - kein ERA5 noetig, keine Modellvergleichsfehler im Ergebnis.

Der 6-h-Abstand ist bewusst konservativ: er misst den WeatherNext-Fall.
ECMWF im Betrieb hat nur 3 h und damit die halbe Luecke.

Zwei Rekonstruktionen:
  Euler   0.5 * (F(x, t) + F(x, t+6))                     - Feld steht still
  SemiLag 0.5 * (F(x - u*3h, t) + F(x + u*3h, t+6))       - Feld wandert mit

Das Gitter ist in Laenge breit und in Breite schmal, weil der Wind hier
ueberwiegend zonal weht: bei 30 m/s sind 3 h rund 324 km, also ~19 Zellen in
Laenge - ein quadratisches Gitter waere zur Haelfte Verschwendung.
"""
import argparse
import json
import math
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITTER = 0.25
N_LON, N_LAT = 25, 5          # Zellen je Richtung (ungerade, Mitte = Zielpunkt)
NIVEAUS = (850, 300)
CACHE = os.path.join(BASIS, "daten", "interp_roh.json")


def gitter(breite, laenge):
    la0, lo0 = round(breite / GITTER), round(laenge / GITTER)
    return [(la0 + i - N_LAT // 2, lo0 + j - N_LON // 2)
            for i in range(N_LAT) for j in range(N_LON)]


def lade(breite, laenge, tage=8):
    if os.path.exists(CACHE):
        with open(CACHE) as f:
            return json.load(f)
    z = gitter(breite, laenge)
    vs = []
    for p in NIVEAUS:
        vs += ["relative_humidity_%dhPa" % p, "wind_speed_%dhPa" % p,
               "wind_direction_%dhPa" % p]
    aus = {}
    for i in range(0, len(z), 25):
        teil = z[i:i + 25]
        u = ("https://ensemble-api.open-meteo.com/v1/ensemble?latitude=%s&longitude=%s"
             "&models=ecmwf_ifs025&hourly=%s&forecast_days=%d"
             "&temporal_resolution=native"
             % (",".join("%.4f" % (c[0] * GITTER) for c in teil),
                ",".join("%.4f" % (c[1] * GITTER) for c in teil), ",".join(vs), tage))
        with urllib.request.urlopen(u, timeout=600) as f:
            d = json.load(f)
        if isinstance(d, dict):
            d = [d]
        for c, e in zip(teil, d):
            aus["%d/%d" % c] = e["hourly"]
        print("   %d/%d Zellen" % (min(i + 25, len(z)), len(z)), flush=True)
    with open(CACHE, "w") as f:
        json.dump(aus, f)
    return aus


def hole(feld, zelle, var, k):
    e = feld.get("%d/%d" % zelle)
    if e is None:
        return None
    r = e.get(var)
    return None if r is None or r[k] is None else r[k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--breite", type=float, default=52.52)
    ap.add_argument("--laenge", type=float, default=13.405)
    ap.add_argument("--member", default="_member01")
    a = ap.parse_args()

    feld = lade(a.breite, a.laenge)
    zeit = feld[next(iter(feld))]["time"]
    print("native Schritte: %d, Abstand %s -> %s" % (len(zeit), zeit[0], zeit[1]))

    la0, lo0 = round(a.breite / GITTER), round(a.laenge / GITTER)
    km_pro_lon = 111.32 * math.cos(math.radians(a.breite))

    for p in NIVEAUS:
        vr = "relative_humidity_%dhPa%s" % (p, a.member)
        vs = "wind_speed_%dhPa%s" % (p, a.member)
        vd = "wind_direction_%dhPa%s" % (p, a.member)
        eul, sem, wahr, verschiebung = [], [], [], []
        # k-1, k, k+1 sind 3 h auseinander; k ist der zu rekonstruierende Punkt
        for k in range(1, len(zeit) - 1, 2):
            w = hole(feld, (la0, lo0), vr, k)
            f0 = hole(feld, (la0, lo0), vr, k - 1)
            f2 = hole(feld, (la0, lo0), vr, k + 1)
            sp = hole(feld, (la0, lo0), vs, k)
            ri = hole(feld, (la0, lo0), vd, k)
            if None in (w, f0, f2, sp, ri):
                continue
            # Windrichtung ist die Richtung, AUS der es weht (meteorologisch).
            u_ms = -sp / 3.6 * math.sin(math.radians(ri))   # nach Osten
            v_ms = -sp / 3.6 * math.cos(math.radians(ri))   # nach Norden
            dx = u_ms * 3 * 3600 / 1000.0
            dy = v_ms * 3 * 3600 / 1000.0
            verschiebung.append(math.hypot(dx, dy))
            dlo = int(round(dx / km_pro_lon / GITTER))
            dla = int(round(dy / 111.32 / GITTER))
            s0 = hole(feld, (la0 - dla, lo0 - dlo), vr, k - 1)   # stromauf, t
            s2 = hole(feld, (la0 + dla, lo0 + dlo), vr, k + 1)   # stromab, t+6
            if s0 is None or s2 is None:
                continue
            wahr.append(w)
            eul.append(0.5 * (f0 + f2))
            sem.append(0.5 * (s0 + s2))

        if len(wahr) < 5:
            print("%d hPa: zu wenige verwendbare Faelle (%d)" % (p, len(wahr)))
            continue

        def masse(x):
            n = len(x)
            rmse = math.sqrt(sum((xi - yi) ** 2 for xi, yi in zip(x, wahr)) / n)
            mx, my = sum(x) / n, sum(wahr) / n
            sx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
            sy = math.sqrt(sum((yi - my) ** 2 for yi in wahr))
            r = (sum((xi - mx) * (yi - my) for xi, yi in zip(x, wahr)) / (sx * sy)
                 if sx > 0 and sy > 0 else float("nan"))
            return rmse, r

        re, rr = masse(eul)
        se, sr = masse(sem)
        vm = sum(verschiebung) / len(verschiebung)
        print()
        print("%d hPa  n=%d  mittlere Verschiebung in 3 h: %.0f km (%.1f Zellen)"
              % (p, len(wahr), vm, vm / (km_pro_lon * GITTER)))
        print("   Euler       RMSE %6.2f %%RH   r %+.3f" % (re, rr))
        print("   SemiLagrange RMSE %6.2f %%RH   r %+.3f" % (se, sr))
        print("   Gewinn: RMSE %+.1f %%   r %+.3f"
              % (100 * (re - se) / re if re else 0, sr - rr))


if __name__ == "__main__":
    main()
