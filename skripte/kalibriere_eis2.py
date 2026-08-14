"""Kalibrierung, zweiter Anlauf - mit Trainings-/Testtrennung und drei Familien.

Der erste Anlauf (kalibriere_eis.py) hat die Ausgangsannahme widerlegt: ein
Eiszweig mit fester Schwelle bei Eissaettigung ist SCHLECHTER als Open-Meteos
Wasserdiagnostik.  Grund, nachgerechnet: Cirrus-Entstehung haengt an der
NUKLEATIONS-Schwelle, nicht an der Saettigung - eisuebersaettigte, wolkenfreie
Gebiete sind haeufig.  Open-Meteos feste 70-%-Wasserschwelle entspricht in
Eis-Einheiten 96 % bei -32 C und 125 % bei -62 C und trifft damit zufaellig
das heterogene Nukleationsband.

Familien:
  wasser    Sundqvist ueber Wasser, RH_crit/RH_sat frei
  eis_fix   Sundqvist ueber Eis, feste Schwellen
  eis_nuk   Sundqvist ueber Eis, Schwelle linear in T (nukleationsfoermig)
Dazu in allen Faellen der Ueberlappungsparameter w:
  C = (1-w)*max(C_i) + w*(1 - prod(1-C_i))     w=0 Maximal-, w=1 Zufallsueberlapp
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen import feuchte as fe  # noqa: E402

NIVEAUS = (400, 300, 250, 200)
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "daten", "gfs_hoch_berlin.json")


def daten():
    with open(CACHE) as fh:
        h = json.load(fh)
    rh = np.array([[v if v is not None else np.nan
                    for v in h["relative_humidity_%dhPa" % p]] for p in NIVEAUS]).T
    t = np.array([[v if v is not None else np.nan
                   for v in h["temperature_%dhPa" % p]] for p in NIVEAUS]).T
    y = np.array([v if v is not None else np.nan for v in h["cloud_cover_high"]]) / 100.0
    jahr = np.array([int(s[:4]) for s in h["time"]])
    ok = ~(np.isnan(rh).any(1) | np.isnan(t).any(1) | np.isnan(y))
    return rh[ok] / 100.0, t[ok], y[ok], jahr[ok]


def sundqvist(rh, crit, sat):
    return np.clip(1.0 - np.sqrt(np.clip((sat - rh) / (sat - crit), 0.0, 1.0)), 0.0, 1.0)


def zusammen(c, w):
    return (1.0 - w) * c.max(1) + w * (1.0 - np.prod(1.0 - c, axis=1))


def masse(x, y):
    rmse = float(np.sqrt(np.mean((x - y) ** 2)))
    r = float(np.corrcoef(x, y)[0, 1])
    return rmse, r


def main():
    rh_w, t, y, jahr = daten()
    # RH ueber Eis, vektorisiert
    ew = 6.112 * np.exp(fe._A_W * t / (fe._B_W + t))
    ei = 6.112 * np.exp(fe._A_I * t / (fe._B_I + t))
    rh_i = rh_w * ew / ei

    tr, te = jahr < 2025, jahr == 2025
    print("Training %d h (2023-2024)   Test %d h (2025)\n" % (tr.sum(), te.sum()))

    kand = []
    # Familie wasser
    for crit in np.arange(0.50, 0.86, 0.025):
        for sat in np.arange(0.85, 1.16, 0.025):
            if sat <= crit + 0.05:
                continue
            c = sundqvist(rh_w, crit, sat)
            for w in (0.0, 0.25, 0.5, 0.75, 1.0):
                kand.append(("wasser", (round(crit, 3), round(sat, 3), w),
                             zusammen(c, w)))
    # Familie eis_fix
    for crit in np.arange(0.85, 1.31, 0.05):
        for spanne in np.arange(0.10, 0.71, 0.10):
            c = sundqvist(rh_i, crit, crit + spanne)
            for w in (0.0, 0.25, 0.5, 0.75, 1.0):
                kand.append(("eis_fix", (round(crit, 2), round(spanne, 2), w),
                             zusammen(c, w)))
    # Familie eis_nuk: crit(T) = k0 + k1*(-T-40)/20
    steig = (-t - 40.0) / 20.0
    for k0 in np.arange(0.95, 1.31, 0.05):
        for k1 in np.arange(0.0, 0.41, 0.05):
            crit = k0 + k1 * steig
            for spanne in np.arange(0.10, 0.71, 0.15):
                c = sundqvist(rh_i, crit, crit + spanne)
                for w in (0.0, 0.25, 0.5, 0.75, 1.0):
                    kand.append(("eis_nuk", (round(k0, 2), round(k1, 2),
                                             round(spanne, 2), w), zusammen(c, w)))

    print("%d Kandidaten\n" % len(kand))
    bestes = {}
    for fam, par, x in kand:
        rm, r = masse(x[tr], y[tr])
        if fam not in bestes or rm < bestes[fam][0]:
            bestes[fam] = (rm, r, par, x)

    print("%-9s %-34s %-16s %s" % ("Familie", "Parameter", "Training", "Test (2025)"))
    for fam in ("wasser", "eis_fix", "eis_nuk"):
        rm, r, par, x = bestes[fam]
        trm, tr_ = masse(x[te], y[te])
        print("%-9s %-34s RMSE %.4f r %.3f   RMSE %.4f r %.3f"
              % (fam, str(par), rm, r, trm, tr_))

    # Ausgangszustand zum Vergleich
    c0 = sundqvist(rh_w, 0.70, 1.00)
    x0 = zusammen(c0, 0.0)
    print("\n%-9s %-34s RMSE %.4f r %.3f   RMSE %.4f r %.3f"
          % ("(OM ist)", "(0.70, 1.00, max)", *masse(x0[tr], y[tr]), *masse(x0[te], y[te])))
    c1 = sundqvist(rh_i, 0.85, 1.30)
    x1 = zusammen(c1, 0.0)
    print("%-9s %-34s RMSE %.4f r %.3f   RMSE %.4f r %.3f"
          % ("(E1 war)", "(eis 0.85, 1.30, max)", *masse(x1[tr], y[tr]), *masse(x1[te], y[te])))


if __name__ == "__main__":
    main()
