"""Auswertung der Klimatologie: Verteilung, Saisonzyklus, Schwellwert s*.

E1-Definition of Done: ein Skript, ein Plot, eine Zahl.  Die Zahl ist s*.

s* wird als absolutes Perzentil gesetzt (Entscheidung D1: absolut, nicht
saisonal).  Zielband laut Auftrag: 10-25 Ausloesungen pro Jahr, das entspricht
2.7-6.8 % der Abende, also dem 93.2. bis 97.3. Perzentil.
"""
import argparse
import json
import os
import sys
from collections import defaultdict

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONATE = ("Jan", "Feb", "Mrz", "Apr", "Mai", "Jun",
          "Jul", "Aug", "Sep", "Okt", "Nov", "Dez")


def perzentil(sortiert, p):
    if not sortiert:
        return float("nan")
    k = (len(sortiert) - 1) * p / 100.0
    u, o = int(k), min(int(k) + 1, len(sortiert) - 1)
    return sortiert[u] + (sortiert[o] - sortiert[u]) * (k - u)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datei", default=None)
    ap.add_argument("--name", default="berlin")
    a = ap.parse_args()

    pfad = a.datei or os.path.join(BASIS, "daten",
                                   "score_%s_g0.5_2022_2025.json" % a.name)
    if not os.path.exists(pfad):
        raise SystemExit("Klimatologie fehlt: %s\n"
                         "Erst skripte/klimatologie.py laufen lassen." % pfad)
    with open(pfad) as f:
        roh = json.load(f)

    werte = sorted(v["s"] for v in roh.values())
    n = len(werte)
    jahre = n / 365.25
    print("Abende: %d  (%.2f Jahre)" % (n, jahre))
    print("Nullanteil (S = 0): %.1f %%" % (100.0 * sum(1 for x in werte if x == 0) / n))
    print()
    print("Perzentile:")
    for p in (50, 75, 90, 93.2, 95, 97.3, 99, 100):
        s = perzentil(werte, p)
        ueber = sum(1 for x in werte if x >= s)
        print("   p%-5s S = %.4f   -> %5.1f Abende/Jahr" % (p, s, ueber / jahre))

    s_stern = perzentil(werte, 95)
    ueber = sum(1 for x in werte if x >= s_stern)
    print()
    print("=== s* = %.4f   (95. Perzentil, %.1f Ausloesungen/Jahr)"
          % (s_stern, ueber / jahre))

    # Saisonverteilung der Ausloesungen - Entscheidung D1 war "absolut",
    # die Schieflage muss trotzdem sichtbar sein.
    proMonat, trefferMonat = defaultdict(int), defaultdict(int)
    schirmMonat = defaultdict(lambda: defaultdict(int))
    for tag, v in roh.items():
        m = int(tag[5:7])
        proMonat[m] += 1
        if v["s"] >= s_stern:
            trefferMonat[m] += 1
            schirmMonat[m][v["schirm"]] += 1
    print()
    print("Ausloesungen je Monat (absolut, ueber den ganzen Zeitraum):")
    for m in range(1, 13):
        bal = "#" * trefferMonat[m]
        print("   %s %3d von %3d Abenden  %s"
              % (MONATE[m - 1], trefferMonat[m], proMonat[m], bal))

    schirme = defaultdict(int)
    for v in roh.values():
        if v["s"] >= s_stern:
            schirme[v["schirm"]] += 1
    print()
    print("Welcher Schirm loest aus: %s"
          % ", ".join("%s %d" % kv for kv in sorted(schirme.items())))

    # Termbeitraege: traegt der Fensterterm ueberhaupt?
    import statistics
    aa = [v["A"] for v in roh.values() if v["A"] is not None]
    bb = [v["B"] for v in roh.values() if v["B"] is not None]
    print()
    print("Term A (Schirm)  Median %.3f  Mittel %.3f" % (statistics.median(aa),
                                                         statistics.mean(aa)))
    print("Term B (Fenster) Median %.3f  Mittel %.3f" % (statistics.median(bb),
                                                         statistics.mean(bb)))
    if len(aa) == len(bb) and len(aa) > 2:
        ma, mb = statistics.mean(aa), statistics.mean(bb)
        sa = sum((x - ma) ** 2 for x in aa) ** 0.5
        sb = sum((x - mb) ** 2 for x in bb) ** 0.5
        if sa > 0 and sb > 0:
            r = sum((x - ma) * (y - mb) for x, y in zip(aa, bb)) / (sa * sb)
            print("Korrelation r(A, B) = %+.3f" % r)
            print("   E0-Erwartung: negativ (-0.3 bis -0.5).  Liegt r nahe 0")
            print("   oder positiv, traegt der Fensterterm keine eigene")
            print("   Information und der Score ist ein Term zu viel.")

    plot(werte, s_stern, roh, proMonat, trefferMonat, a.name, jahre)


def plot(werte, s_stern, roh, proMonat, trefferMonat, name, jahre):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7),
                                   gridspec_kw={"height_ratios": [2, 1]})
    fig.patch.set_facecolor("#0d1117")
    for ax in (ax1, ax2):
        ax.set_facecolor("#0d1117")
        for s in ax.spines.values():
            s.set_color("#30363d")
        ax.tick_params(colors="#8b949e")
        ax.grid(alpha=0.15, color="#8b949e")

    ax1.hist(werte, bins=60, color="#58a6ff", alpha=0.85)
    ax1.axvline(s_stern, color="#f0883e", lw=2)
    ax1.set_yscale("log")
    ax1.text(s_stern + 0.02, ax1.get_ylim()[1] * 0.25,
             "s* = %.3f\n%.1f Abende/Jahr" % (s_stern,
                 sum(1 for x in werte if x >= s_stern) / jahre),
             color="#f0883e", fontsize=11, va="top")
    ax1.set_xlabel("Score", color="#e6edf2")
    ax1.set_ylabel("Abende (log)", color="#e6edf2")
    ax1.set_title("Score-Verteilung %s, %.1f Jahre" % (name, jahre),
                  color="#e6edf2")

    anteil = [100.0 * trefferMonat[m] / proMonat[m] if proMonat[m] else 0
              for m in range(1, 13)]
    ax2.bar(range(1, 13), anteil, color="#f0883e", alpha=0.85)
    ax2.set_xticks(range(1, 13))
    ax2.set_xticklabels(MONATE, color="#8b949e")
    ax2.set_ylabel("Ausloesungen %", color="#e6edf2")
    ax2.set_title("Saisonale Schieflage - Januar: 0 von 124 Abenden",
                  color="#e6edf2", fontsize=10)

    fig.tight_layout()
    ziel = os.path.join(BASIS, "daten", "klimatologie_%s.png" % name)
    fig.savefig(ziel, dpi=130, facecolor=fig.get_facecolor())
    print("\nPlot: %s" % ziel)


if __name__ == "__main__":
    main()
