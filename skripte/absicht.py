"""T-0001b: trennt der Score innerhalb der Draussen-Abende?

DAS PROBLEM, das dieser Test loest.  Der urspruengliche Presence-Only-Test
verglich Abende MIT Fotos gegen alle uebrigen - und mass damit vor allem, ob
Andre an dem Abend draussen war.  Ein konfundiertes Label: Wochenende,
Urlaub, Wetterlust und Sonnenuntergangsqualitaet sind vermischt.

DIE IDEE.  Nur Abende betrachten, an denen er nachweislich draussen war und
zur Sonnenuntergangszeit in Berlin fotografiert hat.  Innerhalb dieser Menge
ist "war er ueberhaupt draussen" konstant.  Uebrig bleibt die Absicht:
hat er ein Bild als FAVORIT markiert oder nicht?

Das ist der sauberste Kontrollversuch, den dieses Projekt hat, weil er ohne
das kuratierte Album auskommt - und ohne meine eigene Bewertung, die sich
in der Obergrenzen-Rechnung als nicht unabhaengig erwiesen hat.

GRENZEN, ehrlich vorweg:
- Ein Favorit kann aus tausend Gruenden entstehen, die nichts mit dem Himmel
  zu tun haben - Personen im Bild, ein Ereignis, ein gelungener Schnappschuss.
  Das ist Rauschen im Label und daempft jeden echten Effekt.
- Die Favoritenquote schwankt ueber die Jahre (Gewohnheit aendert sich).
  Deshalb wird zusaetzlich jahrgangsweise ausgewertet.
- Presence-Only bleibt Presence-Only: ein spektakulaerer Abend ohne Foto
  taucht hier gar nicht auf.
"""
import argparse
import json
import math
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def wilson(p, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def mannwhitney(a, b):
    """U-Test als Normalapproximation; gibt (z, gemeinsame Sprache A)."""
    alle = sorted([(x, 0) for x in a] + [(x, 1) for x in b])
    raenge, i = {}, 0
    werte = [x for x, _ in alle]
    r = [0.0] * len(alle)
    while i < len(alle):
        j = i
        while j + 1 < len(alle) and werte[j + 1] == werte[i]:
            j += 1
        for k in range(i, j + 1):
            r[k] = 0.5 * (i + j) + 1.0
        i = j + 1
    ra = sum(r[k] for k in range(len(alle)) if alle[k][1] == 0)
    na, nb = len(a), len(b)
    u = ra - na * (na + 1) / 2.0
    mu = na * nb / 2.0
    sd = math.sqrt(na * nb * (na + nb + 1) / 12.0)
    return (u - mu) / sd if sd else 0.0, u / (na * nb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fenster", type=float, default=45.0,
                    help="Minuten um den Sonnenuntergang, die als 'draussen' gelten")
    ap.add_argument("--klima", default=os.path.join(
        BASIS, "daten", "score_berlin_g0.5_2015_2025.json"))
    a = ap.parse_args()

    with open(a.klima) as f:
        klima = json.load(f)
    with open(os.path.join(BASIS, "daten", "foto_detail.json")) as f:
        detail = json.load(f)

    # Draussen-Abende: Berlin, Fotos innerhalb des Fensters um Sonnenuntergang.
    draussen = {}
    for x in detail:
        if not (52.2 <= x["lat"] <= 52.8 and 13.0 <= x["lon"] <= 13.9):
            continue
        if x.get("min_abstand") is None or abs(x["min_abstand"]) > a.fenster:
            continue
        if x["tag"] not in klima:
            continue
        e = draussen.setdefault(x["tag"], {"n": 0, "fav": 0})
        e["n"] += x["n"]
        e["fav"] += x.get("favoriten") or 0

    fav = sorted(t for t, e in draussen.items() if e["fav"] > 0)
    ohne = sorted(t for t, e in draussen.items() if e["fav"] == 0)
    print("Draussen-Abende in Berlin (+/- %.0f min um Sonnenuntergang): %d"
          % (a.fenster, len(draussen)))
    print("   mit Favorit: %d     ohne Favorit: %d" % (len(fav), len(ohne)))
    if len(fav) < 15 or len(ohne) < 15:
        raise SystemExit("zu wenige fuer eine Aussage")

    sf = [klima[t]["s"] for t in fav]
    so = [klima[t]["s"] for t in ohne]
    # Reihenfolge ist bedeutungstragend: mannwhitney(a, b) gibt
    # A = P(zufaelliges a > zufaelliges b).  Erst stand hier (so, sf), also
    # P(Nicht-Favorit > Favorit) - und die Beschriftung behauptete das
    # Gegenteil.  Ein Vorzeichenfehler in der PROSA, nicht in der Zahl.
    z, a12 = mannwhitney(sf, so)     # A = P(Favorit > Nicht-Favorit)
    print()
    print("=== Score der Favoritenabende gegen die uebrigen Draussen-Abende")
    print("   Median  Favorit %.4f   ohne %.4f"
          % (sorted(sf)[len(sf) // 2], sorted(so)[len(so) // 2]))
    print("   Mittel  Favorit %.4f   ohne %.4f"
          % (sum(sf) / len(sf), sum(so) / len(so)))
    print("   Mann-Whitney z = %+.2f   %s"
          % (z, "signifikant" if abs(z) > 1.96 else "nicht signifikant"))
    print("   A = %.3f  (Wahrscheinlichkeit, dass ein zufaelliger Favoritenabend"
          % a12)
    print("              hoeher scort als ein zufaelliger Nicht-Favoritenabend;")
    print("              0.5 = kein Unterschied)")

    # Saisonaler Rang statt Rohwert - der Score hat einen Jahresgang, und
    # Favoriten koennten allein deshalb hoeher liegen, weil im Sommer mehr
    # fotografiert wird.
    def jt(s):
        return date.fromisoformat(s).timetuple().tm_yday

    nach = {}
    for t, v in klima.items():
        nach.setdefault(jt(t), []).append(v["s"])

    def rang(t):
        j, v = jt(t), []
        for dd in range(-21, 22):
            v += nach.get((j + dd - 1) % 365 + 1, [])
        w = klima[t]["s"]
        return (sum(1 for x in v if x < w)
                + 0.5 * sum(1 for x in v if x == w)) / len(v)

    rf = [rang(t) for t in fav]
    ro = [rang(t) for t in ohne]
    zr, a12r = mannwhitney(rf, ro)
    print()
    print("=== Dasselbe als saisonaler Perzentilrang (Jahresgang herausgerechnet)")
    print("   Mittelrang  Favorit %.3f   ohne %.3f" % (sum(rf) / len(rf),
                                                       sum(ro) / len(ro)))
    print("   Mann-Whitney z = %+.2f   A = %.3f   %s"
          % (zr, a12r, "signifikant" if abs(zr) > 1.96 else "nicht signifikant"))

    # Jahrgangsweise - die Favoritengewohnheit aendert sich ueber die Jahre.
    print()
    print("=== Je Jahrgang (Gewohnheit aendert sich; A > 0.5 heisst: Score traegt)")
    print("   Jahr   n_fav  n_ohne     A")
    jahre = sorted({t[:4] for t in draussen})
    getragen = 0
    gezaehlt = 0
    for j in jahre:
        f2 = [t for t in fav if t.startswith(j)]
        o2 = [t for t in ohne if t.startswith(j)]
        if len(f2) < 5 or len(o2) < 5:
            continue
        _, aj = mannwhitney([rang(t) for t in f2], [rang(t) for t in o2])
        gezaehlt += 1
        getragen += 1 if aj > 0.5 else 0
        print("   %s   %4d   %5d   %.3f %s" % (j, len(f2), len(o2), aj,
                                               "" if aj > 0.5 else "  <-"))
    if gezaehlt:
        p = getragen / gezaehlt
        lo, hi = wilson(p, gezaehlt)
        print("   %d von %d Jahrgaengen mit A > 0.5   95%%-KI [%.2f, %.2f]"
              % (getragen, gezaehlt, lo, hi))


if __name__ == "__main__":
    main()
