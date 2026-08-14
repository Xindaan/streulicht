"""Traegt der Fensterterm operativ etwas bei? Rein offline, kein Kontingent.

Der Abbruchtest fragt "korreliert S mit Schoenheit". Diese Analyse fragt etwas
Anderes und Unabhaengiges: aendert B ueberhaupt die RANGFOLGE gegenueber A?
Ein Term, der die Auswahl nicht veraendert, ist unabhaengig von jeder
Validierung ueberfluessig.
"""
import json
import math
import os
import statistics
import sys

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHWELLE = 0.6325


def raenge(v):
    o = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        m = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            r[o[k]] = m
        i = j + 1
    return r


def spearman(x, y):
    n = len(x)
    rx, ry = raenge(x), raenge(y)
    mx, my = sum(rx) / n, sum(ry) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    sy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sx * sy)


def main():
    pfad = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        BASIS, "daten", "score_berlin_g0.5_2022_2025.json")
    with open(pfad) as f:
        d = json.load(f)
    tage = sorted(d)
    n = len(tage)
    S = [d[t]["s"] for t in tage]
    A = [d[t]["A"] or 0 for t in tage]
    B = [d[t]["B"] or 0 for t in tage]

    print("%d Abende aus %s" % (n, os.path.basename(pfad)))
    print()
    print("Rangkorrelationen")
    print("   rho(S, A) = %+.3f   nahe 1 hiesse: B ist dekorativ"
          % spearman(S, A))
    print("   rho(S, B) = %+.3f" % spearman(S, B))
    print("   rho(A, B) = %+.3f   Frontenzyklus-Antikorrelation" % spearman(A, B))

    k = round(n * 0.05)
    topS = {tage[i] for i in sorted(range(n), key=lambda i: -S[i])[:k]}
    topA = {tage[i] for i in sorted(range(n), key=lambda i: -A[i])[:k]}
    print()
    print("Top-%d (5 %%): waehlt S andere Abende als A?" % k)
    print("   Ueberlappung %d von %d = %.0f %%"
          % (len(topS & topA), k, 100 * len(topS & topA) / k))

    hoch = [i for i in range(n) if A[i] >= SCHWELLE]
    veto = [i for i in hoch if S[i] < SCHWELLE]
    print()
    print("Vetowirkung des Fensterterms")
    print("   Abende mit A >= s*:               %4d" % len(hoch))
    print("   davon durch B unter s* gedrueckt: %4d = %.0f %%"
          % (len(veto), 100 * len(veto) / len(hoch)))
    bh = sorted(B[i] for i in hoch)
    print("   B bei hohem A: Median %.2f, p10 %.2f, p90 %.2f"
          % (statistics.median(bh), bh[len(bh) // 10], bh[9 * len(bh) // 10]))


if __name__ == "__main__":
    main()
