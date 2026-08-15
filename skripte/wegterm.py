"""T-0029: den Beleuchtungsweg anders aggregieren - traegt das?

DIE FRAGE.  Befund 35 hat die Wegwolken an den toten Albumabenden bestaetigt,
Befund 36 die Schichtzuordnung.  Uebrig blieb der Term selbst: das Produkt
ueber vier bis sechs Segmente rechnet ein gebrochenes Feld mit 66-91 %
Bedeckung auf 0.001 herunter, waehrend innerhalb der Saeule Maximalueberlapp
gilt.  Wenn der Term zu hart ist, muesste eine weichere Aggregation die
toten Albumabende retten, OHNE die Trennung Album/Referenz und die
Trefferquote bei gleicher Alarmrate zu verschlechtern.

WAS GERECHNET WIRD.  Der volle Score (beide Schirme, gleiche Felder, gleicher
Sichtterm) fuer alle Abende der Klimatologie 2015-2026, je Variante des
Wegterms:

  produkt   Betrieb: Produkt (1 - c_i)                          [Referenz]
  wurzel    Produkt (1 - c_i)^0.5   - weichere Kopplung, K = 0.5
  mittel    1 - Mittel(c_i)         - Licht durch ein gebrochenes Feld
  max       1 - max(c_i)            - Maximalueberlapp wie in der Saeule
  kurz      Produkt, aber ohne die Stuetzstelle jenseits der Tangente
            - kuerzere Reichweite, der bodennahe Abschnitt faellt weg

Beide Schirme muessen mit, weil die gespeicherten Segmentwerte nur den
GEWINNENDEN Schirm tragen: an drei der vier Toeter-Abende ist das `mid` mit
A = 0.02 bis 0.27 - dort hilft kein Fenster der Welt.  Retten koennte nur der
`high`-Zweig (2018-07-09: A = 0.89), und der steht nur in der Neurechnung.

WORAN GEMESSEN WIRD.  Jede Variante bekommt IHRE eigene Schwelle (95.
Perzentil ihrer Klimatologie, also dieselbe Alarmrate 18/Jahr), dann:

  * Trefferquote im Album (Andres benotete Abende) bei 18/25/37 Alarmen
    pro Jahr, mit Wilson-Intervall, plus die gepaarte Bilanz gegen produkt
    (wie viele Albumabende gewinnt/verliert die Variante bei 18/Jahr).
  * Anreicherung: mittlerer saisonaler Perzentilrang von S im Album (wie
    albumtest.py, +/-21 Tage ueber alle Jahre).
  * Tote Fenster (B < 0.1) im Album gegen die Referenzabende aus T-0027 -
    das Fenster traegt Signal (3 gegen 14); bleibt das erhalten?
  * Spearman S gegen Note innerhalb des Albums.
  * Die vier Toeter-Abende einzeln: S, Schirm, A, B, Alarm ja/nein.

Vorbehalt wie in Abschnitt 20-23: Album = draussen = eher klares Wetter.
Eine Variante, die bewoelkte Wege oeffnet, kann deshalb im Album schlechter
aussehen als sie ist.  Deshalb steht die Referenz mit auf dem Tisch.

Kosten: 0 EUR, alles aus dem Rohcache.

Pruefbefehl:  python3 skripte/wegterm.py            (rechnet, cacht, berichtet)
              python3 skripte/wegterm.py --bericht  (nur Bericht aus dem Cache)
"""
import argparse
import json
import math
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sonnen.score as sc  # noqa: E402
from sonnen.score import WEG_AGGREGATIONEN, score  # noqa: E402
from fensterterm import (albumabende, hole_modell,  # noqa: E402
                         referenzabende, _rangkorrelation)

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KLIMA = os.path.join(BASIS, "daten", "score_berlin_g0.5_2015_2025.json")
NOTEN = os.path.join(BASIS, "daten", "bewertung_andre.json")
ZIEL = os.path.join(BASIS, "daten", "wegterm_varianten.json")
FENSTER_TOT = 0.10
FENSTER_TAGE = 21
TOETER = ("2018-07-09", "2023-04-24", "2024-05-03", "2024-09-15")
ALARMRATEN = ((95.0, "18/Jahr"), (93.2, "25/Jahr"), (90.0, "37/Jahr"))

# (Name, Aggregation, ohne Tangentensegment)
VARIANTEN = (
    ("produkt", "produkt", False),
    ("wurzel", "wurzel", False),
    ("mittel", "mittel", False),
    ("max", "max", False),
    ("kurz", "produkt", True),
)


# ------------------------------------------------------------------ Rechnung

def rechne(klima, breite, laenge):
    """{tag: {variante: {s, schirm, A, B, sicht, weg}}} fuer alle Abende."""
    aus = {}
    tage = sorted(klima)
    for i, tag in enumerate(tage):
        hole, _ = hole_modell(tag, breite, laenge)
        if hole is None:
            continue
        je = {}
        for name, agg, ohne in VARIANTEN:
            s, det = score(hole, weg_agg=WEG_AGGREGATIONEN[agg],
                           ohne_tangentensegment=ohne)
            if det is None:
                je[name] = None
                continue
            je[name] = {"s": s, "schirm": det["schirm"], "A": det["A"],
                        "B": det["B"], "sicht": det["sicht"],
                        "weg": det["weg"]}
        aus[tag] = je
        if (i + 1) % 500 == 0:
            print("  %d/%d" % (i + 1, len(tage)), flush=True)
    return aus


def pruefe_replik(erg, klima):
    """Die Variante produkt muss die Klimatologie bitgenau reproduzieren."""
    n = abweichend = fehlend = 0
    schlimmste = 0.0
    for tag, v in klima.items():
        e = erg.get(tag, {}).get("produkt")
        if e is None or v.get("s") is None:
            fehlend += 1
            continue
        n += 1
        d = abs(e["s"] - v["s"])
        schlimmste = max(schlimmste, d)
        if d > 1e-12:
            abweichend += 1
    return n, abweichend, fehlend, schlimmste


# ---------------------------------------------------------------- Auswertung

def tag_im_jahr(s):
    return date.fromisoformat(s).timetuple().tm_yday


def rang(wert, vergleich):
    kl = sum(1 for x in vergleich if x < wert)
    gl = sum(1 for x in vergleich if x == wert)
    return (kl + 0.5 * gl) / len(vergleich)


def wilson(tr, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    ph = tr / n
    mitte = (ph + z * z / (2 * n)) / (1 + z * z / n)
    halb = (z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
            / (1 + z * z / n))
    return max(0.0, mitte - halb), min(1.0, mitte + halb)


def werte(erg, name, feld="s"):
    return {t: v[name][feld] for t, v in erg.items()
            if v.get(name) is not None}


def saisonrang(s_alle, tag, wert):
    j = tag_im_jahr(tag)
    fenster = []
    for dd in range(-FENSTER_TAGE, FENSTER_TAGE + 1):
        jj = (j + dd - 1) % 365 + 1
        fenster.extend(s_alle.get(jj, []))
    return rang(wert, fenster) if fenster else None


def bericht(erg, klima, noten, referenz):
    album = [t for t in albumabende(klima, noten) if t in erg]
    ref = [referenz[t] for t in album if referenz.get(t) in erg]
    namen = [n for n, _, _ in VARIANTEN]

    n, ab, fehl, schlimm = pruefe_replik(erg, klima)
    print("Replik produkt gegen Klimatologie: %d Abende, %d abweichend "
          "(max |dS| = %.1e), %d ohne Vergleich" % (n, ab, schlimm, fehl))
    print("Album: %d benotete Abende in der Klimatologie, %d Referenzabende"
          % (len(album), len(ref)))

    s_prod = werte(erg, "produkt")
    schwellen = {}
    print("\n=== Schwellen je Variante (eigene Klimatologie, gleiche Alarmrate)"
          " und Rangstabilitaet gegen produkt")
    print("   %-8s %8s %8s %8s   %s" % ("Variante", "18/Jahr", "25/Jahr",
                                        "37/Jahr", "Spearman S gegen produkt"))
    for name in namen:
        s = werte(erg, name)
        sortiert = sorted(s.values())
        schwellen[name] = {lab: sortiert[int(len(sortiert) * pz / 100)]
                           for pz, lab in ALARMRATEN}
        gemeinsam = [t for t in s if t in s_prod]
        rho = _rangkorrelation([s[t] for t in gemeinsam],
                               [s_prod[t] for t in gemeinsam])
        print("   %-8s %8.3f %8.3f %8.3f   %+.3f" % (
            name, schwellen[name]["18/Jahr"], schwellen[name]["25/Jahr"],
            schwellen[name]["37/Jahr"], rho))

    print("\n=== Trefferquote im Album bei gleicher Alarmrate  (Wilson 95 %)")
    print("   %-8s %-22s %-22s %-22s  %s" % (
        "Variante", "18/Jahr", "25/Jahr", "37/Jahr",
        "gepaart gegen produkt bei 18/Jahr"))
    treffer_prod = None
    for name in namen:
        s = werte(erg, name)
        zellen = []
        for pz, lab in ALARMRATEN:
            sw = schwellen[name][lab]
            tr = sum(1 for t in album if s[t] >= sw)
            lo, hi = wilson(tr, len(album))
            zellen.append("%2d/%d = %2.0f %% [%2.0f..%2.0f]" % (
                tr, len(album), 100 * tr / len(album), 100 * lo, 100 * hi))
        sw = schwellen[name]["18/Jahr"]
        drin = {t for t in album if s[t] >= sw}
        if treffer_prod is None:
            treffer_prod = drin
            paar = "(Referenz)"
        else:
            neu = sorted(drin - treffer_prod)
            weg = sorted(treffer_prod - drin)
            paar = "+%d / -%d" % (len(neu), len(weg))
            if neu:
                paar += "  neu: " + ", ".join(neu)
            if weg:
                paar += "  weg: " + ", ".join(weg)
        print("   %-8s %-22s %-22s %-22s  %s" % (name, *zellen, paar))

    print("\n=== Anreicherung: mittlerer saisonaler Perzentilrang von S im Album"
          " (H0 = 0.500)")
    for name in namen:
        s = werte(erg, name)
        nach = {}
        for t, v in s.items():
            nach.setdefault(tag_im_jahr(t), []).append(v)
        r = [saisonrang(nach, t, s[t]) for t in album]
        r = [x for x in r if x is not None]
        m = sum(r) / len(r)
        z = (m - 0.5) / math.sqrt(1.0 / 12.0 / len(r))
        print("   %-8s n=%3d   Mittelrang %.3f   z = %+5.2f" % (
            name, len(r), m, z))

    print("\n=== Tote Fenster (B < %.1f) und Fenster im Mittel: Album gegen "
          "Referenz" % FENSTER_TOT)
    print("   %-8s %-18s %-18s   %-14s %-14s" % (
        "Variante", "Album tot", "Referenz tot", "Album B med.",
        "Referenz B med."))
    for name in namen:
        b = werte(erg, name, "B")
        ta = sum(1 for t in album if b[t] < FENSTER_TOT)
        tr = sum(1 for t in ref if b[t] < FENSTER_TOT)
        ma = sorted(b[t] for t in album)[len(album) // 2]
        mr = sorted(b[t] for t in ref)[len(ref) // 2] if ref else float("nan")
        print("   %-8s %3d von %3d (%3.0f %%)  %3d von %3d (%3.0f %%)   "
              "%-14.3f %-14.3f" % (
                  name, ta, len(album), 100 * ta / len(album),
                  tr, len(ref), 100 * tr / len(ref) if ref else 0, ma, mr))

    print("\n=== Spearman innerhalb des Albums: S bzw. B gegen Andres Note")
    for name in namen:
        s, b = werte(erg, name), werte(erg, name, "B")
        rs = _rangkorrelation([noten[t] for t in album], [s[t] for t in album])
        rb = _rangkorrelation([noten[t] for t in album], [b[t] for t in album])
        print("   %-8s rho(S, Note) = %+.3f   rho(B, Note) = %+.3f   (n = %d)"
              % (name, rs, rb, len(album)))

    print("\n=== Die vier Toeter-Abende (Befund 35) je Variante")
    print("   %-11s %-8s %5s %5s %5s %5s %5s  %-6s %s" % (
        "Abend", "Variante", "S", "A", "B", "sicht", "weg", "Schirm",
        "Alarm 18/Jahr?"))
    for t in TOETER:
        for name in namen:
            e = erg.get(t, {}).get(name)
            if e is None:
                print("   %-11s %-8s -" % (t, name))
                continue
            sw = schwellen[name]["18/Jahr"]
            print("   %-11s %-8s %5.3f %5.2f %5.3f %5.2f %5.3f  %-6s %s" % (
                t, name, e["s"], e["A"], e["B"], e["sicht"], e["weg"],
                e["schirm"], "JA" if e["s"] >= sw else "nein"))
        print()


def zweige(breite, laenge):
    """Beide Schirmzweige der Toeter-Abende einzeln, je Variante.

    Der Score behaelt nur den gewinnenden Zweig.  Ob ein weicheres Fenster
    einen Abend retten KOENNTE, entscheidet aber der Zweig mit dem Schirm -
    und der verliert unter Umstaenden gerade am Fenster.  Deshalb hier jeder
    Zweig fuer sich: score() mit auf einen Schirm eingeschraenkter SCHIRME.
    """
    print("=== Beide Schirmzweige an den Toeter-Abenden "
          "(A = Schirm, B = sicht x weg)")
    print("   %-11s %-5s %5s | %s" % (
        "Abend", "Zweig", "A", "  ".join("%-16s" % ("B/weg %s" % n)
                                          for n, _, _ in VARIANTEN)))
    alt = sc.SCHIRME
    try:
        for t in TOETER:
            hole, _ = hole_modell(t, breite, laenge)
            if hole is None:
                continue
            for zweig in alt:
                sc.SCHIRME = (zweig,)
                zellen, a_wert = [], None
                for name, agg, ohne in VARIANTEN:
                    _, det = score(hole, weg_agg=WEG_AGGREGATIONEN[agg],
                                   ohne_tangentensegment=ohne)
                    if det is None:
                        zellen.append("%-16s" % "-")
                        continue
                    a_wert = det["A"]
                    zellen.append("%-16s" % ("%.3f / %.3f"
                                             % (det["B"], det["weg"])))
                print("   %-11s %-5s %5s | %s" % (
                    t, zweig[0], "-" if a_wert is None else "%.2f" % a_wert,
                    "  ".join(zellen)))
            print()
    finally:
        sc.SCHIRME = alt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--breite", type=float, default=52.52)
    ap.add_argument("--laenge", type=float, default=13.405)
    ap.add_argument("--bericht", action="store_true",
                    help="nur Bericht aus dem Cache, nichts rechnen")
    ap.add_argument("--neu", action="store_true",
                    help="Cache ignorieren und alles neu rechnen")
    a = ap.parse_args()

    with open(KLIMA) as f:
        klima = json.load(f)
    with open(NOTEN) as f:
        noten = json.load(f)

    if a.bericht or (os.path.exists(ZIEL) and not a.neu):
        with open(ZIEL) as f:
            erg = json.load(f)
        print("Cache: %s (%d Abende)" % (os.path.relpath(ZIEL, BASIS), len(erg)))
    else:
        print("rechne %d Abende x %d Varianten ..." % (len(klima), len(VARIANTEN)))
        erg = rechne(klima, a.breite, a.laenge)
        with open(ZIEL, "w") as f:
            json.dump(erg, f)
        print("geschrieben: %s" % os.path.relpath(ZIEL, BASIS))

    album = albumabende(klima, noten)
    referenz = referenzabende(album, klima, noten)
    bericht(erg, klima, noten, referenz)
    zweige(a.breite, a.laenge)


if __name__ == "__main__":
    main()
