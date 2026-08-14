"""T-0005: taugt lineare Zeitinterpolation, oder braucht es Advektion?

Versuchsaufbau ohne fremde Wahrheit: ECMWF ENS liefert nativ 3-h-Schritte.
Wir duennen auf 6 h aus, rekonstruieren die uebersprungenen Mittelpunkte und
vergleichen gegen die echten 3-h-Werte.  Die Wahrheit ist das Modell selbst -
kein ERA5 noetig, keine Modellvergleichsfehler im Ergebnis.

Der 6-h-Abstand ist bewusst konservativ: er misst den WeatherNext-Fall.
ECMWF im Betrieb hat nur 3 h und damit die halbe Luecke.

Zwei Rekonstruktionen des Feldes bei t:
  Euler    0.5 * (F(x, t-3h) + F(x, t+3h))                  Feld steht still
  SemiLag  0.5 * (F(x-u*3h, t-3h) + F(x+u*3h, t+3h))        Feld wandert mit

ZWEI-PASS statt Gitter: ein Gitter, das 60-m/s-Jetwind abdeckt, braucht bei
0.25 Grad 47x47 = 2209 Punkte.  Stattdessen erst den Mittelpunkt holen (liefert
den Wind), daraus die stromauf-/stromabwaerts liegenden Positionen berechnen
und nur die abfragen.  Das ist zugleich exakt das Verfahren, das E0 fuer den
Betrieb vorsieht - der Versuch validiert also auch die Betriebsmechanik.

Restliche Quantisierung: Open-Meteo rastet jede Koordinate auf die
Modellgitterzelle (0.25 Grad).  Das ist die Eigenaufloesung der Daten, kein
selbst eingebauter Fehler.
"""
import argparse
import json
import math
import os
import sys
import time
import urllib.request

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NIVEAUS = (850, 300)
MEMBER = ("_member01", "_member02", "_member03")
TAGE = 8
CACHE1 = os.path.join(BASIS, "daten", "interp_mitte.json")
CACHE2 = os.path.join(BASIS, "daten", "interp_versetzt.json")
BASIS_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"


def _hole(u):
    for n in range(4):
        try:
            with urllib.request.urlopen(u, timeout=600) as f:
                return json.load(f)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            grund = json.loads(e.read()).get("reason", "429")
            if "inutely" in grund and n < 3:
                print("   Minutenlimit, warte 65 s ...", flush=True)
                time.sleep(65)
                continue
            raise SystemExit("Kontingent: %s" % grund)
    raise SystemExit("unerreichbar")


def pass1(breite, laenge):
    if os.path.exists(CACHE1):
        with open(CACHE1) as f:
            return json.load(f)
    vs = []
    for p in NIVEAUS:
        vs += ["relative_humidity_%dhPa" % p, "wind_speed_%dhPa" % p,
               "wind_direction_%dhPa" % p]
    u = ("%s?latitude=%.4f&longitude=%.4f&models=ecmwf_ifs025&hourly=%s"
         "&forecast_days=%d&temporal_resolution=native"
         % (BASIS_URL, breite, laenge, ",".join(vs), TAGE))
    h = _hole(u)["hourly"]
    with open(CACHE1, "w") as f:
        json.dump(h, f)
    return h


def versatz_km(sp_kmh, richtung_grad, stunden):
    """Windrichtung ist meteorologisch (Richtung, AUS der es weht)."""
    ms = sp_kmh / 3.6
    u = -ms * math.sin(math.radians(richtung_grad))   # nach Osten
    v = -ms * math.cos(math.radians(richtung_grad))   # nach Norden
    return u * stunden * 3.6, v * stunden * 3.6       # km


def pass2(punkte, breite):
    if os.path.exists(CACHE2):
        with open(CACHE2) as f:
            return json.load(f)
    vs = ",".join("relative_humidity_%dhPa" % p for p in NIVEAUS)
    aus = {}
    liste = sorted(punkte)
    for i in range(0, len(liste), 50):
        teil = liste[i:i + 50]
        u = ("%s?latitude=%s&longitude=%s&models=ecmwf_ifs025&hourly=%s"
             "&forecast_days=%d&temporal_resolution=native"
             % (BASIS_URL, ",".join("%.4f" % p[0] for p in teil),
                ",".join("%.4f" % p[1] for p in teil), vs, TAGE))
        d = _hole(u)
        if isinstance(d, dict):
            d = [d]
        for p, e in zip(teil, d):
            aus["%.4f,%.4f" % p] = e["hourly"]
        print("   Pass 2: %d/%d Punkte" % (min(i + 50, len(liste)), len(liste)),
              flush=True)
        time.sleep(2)
    with open(CACHE2, "w") as f:
        json.dump(aus, f)
    return aus


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--breite", type=float, default=52.52)
    ap.add_argument("--laenge", type=float, default=13.405)
    a = ap.parse_args()

    mitte = pass1(a.breite, a.laenge)
    zeit = mitte["time"]
    print("Pass 1: %d native Schritte, %s -> %s" % (len(zeit), zeit[0], zeit[1]))
    km_lon = 111.32 * math.cos(math.radians(a.breite))

    # Faelle sammeln und die noetigen versetzten Punkte bestimmen
    faelle, punkte = [], set()
    for p in NIVEAUS:
        for m in MEMBER:
            rh = mitte.get("relative_humidity_%dhPa%s" % (p, m))
            sp = mitte.get("wind_speed_%dhPa%s" % (p, m))
            ri = mitte.get("wind_direction_%dhPa%s" % (p, m))
            if rh is None or sp is None or ri is None:
                continue
            for k in range(1, len(zeit) - 1, 2):
                if None in (rh[k], rh[k - 1], rh[k + 1], sp[k], ri[k]):
                    continue
                dx, dy = versatz_km(sp[k], ri[k], 3)
                auf = (round(a.breite - dy / 111.32, 4),
                       round(a.laenge - dx / km_lon, 4))
                ab = (round(a.breite + dy / 111.32, 4),
                      round(a.laenge + dx / km_lon, 4))
                punkte.add(auf)
                punkte.add(ab)
                faelle.append((p, m, k, auf, ab, math.hypot(dx, dy)))
    print("%d Faelle, %d eindeutige versetzte Punkte" % (len(faelle), len(punkte)))

    versetzt = pass2(punkte, a.breite)

    for p in NIVEAUS:
        eul, sem, wahr, weg = [], [], [], []
        for pp, m, k, auf, ab, d in faelle:
            if pp != p:
                continue
            rh = mitte["relative_humidity_%dhPa%s" % (p, m)]
            e_auf = versetzt.get("%.4f,%.4f" % auf)
            e_ab = versetzt.get("%.4f,%.4f" % ab)
            if e_auf is None or e_ab is None:
                continue
            s0 = e_auf.get("relative_humidity_%dhPa%s" % (p, m), [None] * 99)[k - 1]
            s2 = e_ab.get("relative_humidity_%dhPa%s" % (p, m), [None] * 99)[k + 1]
            if s0 is None or s2 is None:
                continue
            wahr.append(rh[k])
            eul.append(0.5 * (rh[k - 1] + rh[k + 1]))
            sem.append(0.5 * (s0 + s2))
            weg.append(d)

        if len(wahr) < 10:
            print("%d hPa: zu wenige Faelle (%d)" % (p, len(wahr)))
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

        re_, rr = masse(eul)
        se_, sr = masse(sem)
        weg.sort()
        print()
        print("%d hPa   n=%d   Verschiebung in 3 h: Median %.0f km, p90 %.0f km "
              "(%.1f Gitterzellen)"
              % (p, len(wahr), weg[len(weg) // 2], weg[9 * len(weg) // 10],
                 weg[len(weg) // 2] / (km_lon * 0.25)))
        print("   Euler          RMSE %6.2f %%RH   r %+.3f" % (re_, rr))
        print("   Semi-Lagrange  RMSE %6.2f %%RH   r %+.3f" % (se_, sr))
        print("   Gewinn: RMSE %+.1f %%,  r %+.3f"
              % (100 * (re_ - se_) / re_ if re_ else 0, sr - rr))


if __name__ == "__main__":
    main()
