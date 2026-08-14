"""Testet den Aerosol-Term, den E0 mit drei Argumenten verworfen hat.

E0 argumentierte: (1) CAMS reicht nur 5 Tage voraus, unser Zielhorizont ist
10; (2) CAMS ist deterministisch und zerstoert die Member-Struktur;
(3) teilredundant zur bodennahen Feuchte, weil hygroskopisches Wachstum die
AOD ab RH ~75 % hochzieht.  Punkt 1 und 2 gelten weiter.  Punkt 3 war eine
Vermutung - hier wird sie gemessen.

Physik dahinter: bei streifendem Einfall ist die Chapman-Verstaerkung fuer
grenzschichtgebundenes Aerosol rund 80-100.  AOD 0.10 ergibt schraeg tau = 10
(Transmission 4.5e-5), AOD 0.03 ergibt tau = 3 (0.05).  Faktor 1000 im
direkten Strahl - also groesser als der Effekt, den es moduliert.

CAMS-Archiv beginnt am 04.08.2022, ueberlappt also mit 3.4 Jahren der
Klimatologie.
"""
import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import sonnenuntergang  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(BASIS, "daten", "aerosol_berlin.json")
ZIRKULAER = {"2025-06-29", "2023-06-14", "2023-05-29", "2022-11-11"}
VARIABLEN = "aerosol_optical_depth,dust,pm2_5"


def hole(von, bis):
    u = ("https://air-quality-api.open-meteo.com/v1/air-quality"
         "?latitude=52.52&longitude=13.405&hourly=%s&start_date=%s&end_date=%s"
         % (VARIABLEN, von, bis))
    for n in range(4):
        try:
            with urllib.request.urlopen(u, timeout=300) as f:
                return json.load(f)["hourly"]
        except urllib.error.HTTPError as e:
            grund = json.loads(e.read()).get("reason", "429")
            if e.code == 429 and "inutely" in grund and n < 3:
                print("   Minutenlimit, warte 65 s ...", flush=True)
                time.sleep(65)
                continue
            raise SystemExit("Kontingent: %s" % grund)
    raise SystemExit("unerreichbar")


def lade():
    if os.path.exists(CACHE):
        with open(CACHE) as f:
            return json.load(f)
    zus = {}
    for jahr in (2022, 2023, 2024, 2025):
        von = "%d-08-04" % jahr if jahr == 2022 else "%d-01-01" % jahr
        bis = "%d-12-31" % jahr
        print("   %s .. %s" % (von, bis), flush=True)
        h = hole(von, bis)
        for k, v in h.items():
            zus.setdefault(k, []).extend(v)
        time.sleep(2)
    with open(CACHE, "w") as f:
        json.dump(zus, f)
    return zus


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--klima", default=os.path.join(
        BASIS, "daten", "score_berlin_g0.5_2022_2025.json"))
    a = ap.parse_args()
    with open(a.klima) as f:
        klima = json.load(f)
    album = {x["tag"] for x in json.load(open(os.path.join(
        BASIS, "daten", "foto_detail.json")))
        if "Sonnenuntergänge" in x.get("alben", [])
        and 52.2 <= x["lat"] <= 52.8 and 13.0 <= x["lon"] <= 13.9}
    album -= ZIRKULAER

    print("Lade CAMS ...")
    h = lade()
    idx = {t: i for i, t in enumerate(h["time"])}

    werte = {}
    for tag in klima:
        std, _ = sonnenuntergang(date.fromisoformat(tag), 52.52, 13.405)
        i = idx.get("%sT%02d:00" % (tag, int(round(std)) % 24))
        if i is None:
            continue
        aod = h["aerosol_optical_depth"][i]
        if aod is None:
            continue
        werte[tag] = {"aod": aod, "dust": h["dust"][i], "pm25": h["pm2_5"][i]}
    print("Abende mit Aerosolwert: %d von %d" % (len(werte), len(klima)))

    def jt(s):
        return date.fromisoformat(s).timetuple().tm_yday

    nach = {}
    for t, v in werte.items():
        nach.setdefault(jt(t), []).append(v["aod"])

    def rang_aod(t):
        j = jt(t)
        v = []
        for dd in range(-21, 22):
            v += nach.get((j + dd - 1) % 365 + 1, [])
        w = werte[t]["aod"]
        return (sum(1 for x in v if x < w) + 0.5 * sum(1 for x in v if x == w)) / len(v)

    kand = sorted(t for t in album if t in werte)
    print("davon im Album: %d" % len(kand))
    if len(kand) < 15:
        raise SystemExit("zu wenige")

    r = [rang_aod(t) for t in kand]
    m = sum(r) / len(r)
    z = (m - 0.5) / math.sqrt(1.0 / 12.0 / len(r))
    print()
    print("=== These aus E0: klare Luft gibt gesaettigte Farben")
    print("   Erwartung waere ein Mittelrang DEUTLICH UNTER 0.5 (wenig Aerosol).")
    print("   Gemessen: Mittelrang %.3f   z = %+.2f   %s"
          % (m, z, "signifikant" if abs(z) > 1.96 else "nicht signifikant"))

    aa = [werte[t]["aod"] for t in kand]
    rest = [v["aod"] for t, v in werte.items() if t not in album]
    aa.sort()
    rest.sort()
    print()
    print("   AOD Albumabende:  Median %.3f  p10 %.3f  p90 %.3f"
          % (aa[len(aa) // 2], aa[len(aa) // 10], aa[9 * len(aa) // 10]))
    print("   AOD uebrige:      Median %.3f  p10 %.3f  p90 %.3f"
          % (rest[len(rest) // 2], rest[len(rest) // 10], rest[9 * len(rest) // 10]))

    print()
    print("=== Traegt Aerosol ZUSAETZLICH zum Score?")
    gemeinsam = [t for t in werte if t in klima]
    s = [klima[t]["s"] for t in gemeinsam]
    ao = [werte[t]["aod"] for t in gemeinsam]
    n = len(s)
    ms, ma = sum(s) / n, sum(ao) / n
    ss = math.sqrt(sum((x - ms) ** 2 for x in s))
    sa = math.sqrt(sum((x - ma) ** 2 for x in ao))
    rr = sum((x - ms) * (y - ma) for x, y in zip(s, ao)) / (ss * sa)
    print("   Korrelation r(S, AOD) = %+.3f  (E0 vermutete Teilredundanz)" % rr)


if __name__ == "__main__":
    main()
