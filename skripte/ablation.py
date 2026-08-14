"""T-0006: traegt die 3-Schicht-Variante dieselbe Rangfolge wie die
niveauaufgeloeste?

Das ist load-bearing, nicht kosmetisch: s* kommt aus der 3-Schicht-Klimatologie
(ERA5, vier Jahre), der Betrieb laeuft niveauaufgeloest auf ECMWF.  Wenn die
Rangfolgen auseinanderlaufen, ist der Schwellwert nicht uebertragbar und E2
haette keine Zahl.

Quelle: `gfs_global` im historical-forecast-api - das einzige Archiv, das
Druckflaechen UND natives low/mid/high fuer denselben Zeitpunkt liefert.
Beide Scores sehen damit exakt denselben Modellzustand; verglichen wird die
Score-Formulierung, nicht zwei Wetterlagen.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import sonnenuntergang  # noqa: E402
from sonnen.score import faecherpunkte, score as score3  # noqa: E402
from sonnen.score_niveaus import ALLE_NIVEAUS, score as scoreN  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITTER = 0.5
SCHICHTEN = ("low", "mid", "high")


def variablen():
    v = ["cloud_cover_%s" % s for s in SCHICHTEN]
    for p in ALLE_NIVEAUS:
        v += ["relative_humidity_%dhPa" % p, "temperature_%dhPa" % p]
    return v


def zelle(lat, lon):
    return (round(lat / GITTER), round(lon / GITTER))


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
                print("      Minutenlimit, warte 65 s ...", flush=True)
                time.sleep(65)
                continue
            raise SystemExit("Kontingent erschoepft: %s\n"
                             "Cache bleibt, naechster Lauf setzt dort an." % grund)
    raise SystemExit("unerreichbar")


def hole(zellen, von, bis, gesucht, block=20):
    aus = {}
    liste = sorted(zellen)
    cd = os.path.join(BASIS, "daten", "roh_ablation")
    os.makedirs(cd, exist_ok=True)
    vs = ",".join(variablen())
    for i in range(0, len(liste), block):
        teil = liste[i:i + block]
        cache = os.path.join(cd, "%s_%04d.json" % (von, i))
        if os.path.exists(cache):
            with open(cache) as f:
                aus.update(json.load(f))
            print("      %d/%d (Cache)" % (min(i + block, len(liste)), len(liste)),
                  flush=True)
            continue
        u = ("https://historical-forecast-api.open-meteo.com/v1/forecast"
             "?latitude=%s&longitude=%s&models=gfs_global&hourly=%s"
             "&start_date=%s&end_date=%s"
             % (",".join("%.4f" % (z[0] * GITTER) for z in teil),
                ",".join("%.4f" % (z[1] * GITTER) for z in teil), vs, von, bis))
        d = _hole(u)
        if isinstance(d, dict):
            d = [d]
        teilaus = {}
        for z, e in zip(teil, d):
            h = e["hourly"]
            idx = {t: k for k, t in enumerate(h["time"])}
            teilaus["%d/%d" % z] = {
                v: {tag: h[v][idx[st]] for tag, st in gesucht.items() if st in idx}
                for v in variablen() if v in h}
        with open(cache, "w") as f:
            json.dump(teilaus, f)
        aus.update(teilaus)
        print("      %d/%d Zellen" % (min(i + block, len(liste)), len(liste)),
              flush=True)
        time.sleep(2)
    return aus


def spearman(x, y):
    def raenge(v):
        s = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(s):
            j = i
            while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
                j += 1
            mittel = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[s[k]] = mittel
            i = j + 1
        return r
    rx, ry = raenge(x), raenge(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    sx = sum((a - mx) ** 2 for a in rx) ** 0.5
    sy = sum((b - my) ** 2 for b in ry) ** 0.5
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sx * sy)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--von", default="2025-09-15")
    ap.add_argument("--bis", default="2025-10-26")
    ap.add_argument("--breite", type=float, default=52.52)
    ap.add_argument("--laenge", type=float, default=13.405)
    a = ap.parse_args()

    von, bis = date.fromisoformat(a.von), date.fromisoformat(a.bis)
    zellen, proTag, gesucht = set(), {}, {}
    t = von
    while t <= bis:
        std, az = sonnenuntergang(t, a.breite, a.laenge)
        karte = {}
        for d, dv, la, lo in faecherpunkte(a.breite, a.laenge, az):
            z = zelle(la, lo)
            zellen.add(z)
            karte[(d, dv)] = z
        proTag[str(t)] = karte
        gesucht[str(t)] = "%sT%02d:00" % (t, int(round(std)) % 24)
        t += timedelta(days=1)
    print("%d Abende, %d Zellen, %d Variablen" % (len(proTag), len(zellen),
                                                  len(variablen())))

    feld = hole(zellen, a.von, a.bis, gesucht)

    s3, sN, tage_, ohne_daten = [], [], [], []
    for tag, karte in proTag.items():
        def hole3(d, dv, schicht, _t=tag, _k=karte):
            z = _k.get((d, dv))
            if z is None:
                return None
            v = feld.get("%d/%d" % z, {}).get("cloud_cover_%s" % schicht, {}).get(_t)
            return None if v is None else v / 100.0

        def holeN(d, dv, p, _t=tag, _k=karte):
            z = _k.get((d, dv))
            if z is None:
                return None
            e = feld.get("%d/%d" % z, {})
            rh = e.get("relative_humidity_%dhPa" % p, {}).get(_t)
            tt = e.get("temperature_%dhPa" % p, {}).get(_t)
            return None if rh is None or tt is None else (rh, tt)

        x, dx = score3(hole3)
        y, dy = scoreN(holeN)
        # Ein Abend OHNE Daten liefert aus beiden Verfahren 0.0 - sie stimmen
        # dort also perfekt ueberein und treiben rho nach oben.  Genau das
        # soll die Ablation aber messen.  Phantomnullen wuerden die Antwort
        # in die bequeme Richtung biegen ("die Rangfolgen fallen zusammen,
        # s* ist uebertragbar").  detail is None heisst: nichts war belegt.
        if dx is None or dy is None:
            ohne_daten.append((tag, dx is None, dy is None))
            continue
        s3.append(x)
        sN.append(y)
        tage_.append(tag)

    n = len(s3)
    if ohne_daten:
        print("\n%d Abende ohne Daten uebersprungen (nicht als Null gewertet):"
              % len(ohne_daten))
        for tag, k3, kN in ohne_daten[:8]:
            print("   %s  3-Schicht %s  niveauaufgeloest %s"
                  % (tag, "leer" if k3 else "ok", "leer" if kN else "ok"))
        if len(ohne_daten) > 8:
            print("   ... und %d weitere" % (len(ohne_daten) - 8))
    if n < 12:
        raise SystemExit("nur %d auswertbare Abende - keine Aussage" % n)
    print("\n=== %d Abende ausgewertet" % n)
    print("Spearman rho(3-Schicht, niveauaufgeloest) = %+.3f" % spearman(s3, sN))
    print("Mittel: 3-Schicht %.3f   niveauaufgeloest %.3f"
          % (sum(s3) / n, sum(sN) / n))

    k = max(1, round(n * 0.15))
    top3 = {tage_[i] for i in sorted(range(n), key=lambda i: -s3[i])[:k]}
    topN = {tage_[i] for i in sorted(range(n), key=lambda i: -sN[i])[:k]}
    print("Top-%d-Ueberlappung: %d von %d (%.0f %%)"
          % (k, len(top3 & topN), k, 100 * len(top3 & topN) / k))
    print("\nnur 3-Schicht:      %s" % ", ".join(sorted(top3 - topN)) or "-")
    print("nur niveauaufgel.:  %s" % ", ".join(sorted(topN - top3)) or "-")

    # Dateiname traegt das Fenster.  Vorher hiess die Datei immer
    # "ablation.json" - der zweite Lauf mit einem anderen Zeitraum
    # ueberschrieb den ersten stillschweigend, und zwei Ergebnisse mit
    # verschiedenem n sahen hinterher aus wie eines.
    ziel = os.path.join(BASIS, "daten", "ablation_%s.json" % a.von)
    with open(ziel, "w") as f:
        json.dump({"tage": tage_, "s3": s3, "sN": sN}, f)
    print("\ngeschrieben: %s" % ziel)


if __name__ == "__main__":
    main()
