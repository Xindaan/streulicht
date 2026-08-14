"""Der eigentliche Validierungstest: kuratiertes Album gegen die Klimatologie.

Presence-Only, und das ist Absicht.  Ein fehlendes Foto heisst nicht
"schlechter Abend" - Andre war vielleicht nicht in Berlin oder hat nicht
hingesehen.  Die offene Frage ist aber einseitig: haette der Alarm an den
Abenden gefeuert, die er als gut erinnert?  Dafuer reichen Positive.  Die
Gegenseite, wie oft der Alarm daneben feuert, steht per Konstruktion fest -
s* ist auf 18 Ausloesungen im Jahr kalibriert.

Zwei Fallen, beide schon einmal zugeschnappt:

* ZIRKULARITAET.  Abende, die durch Ansehen der Score-Balken gefunden wurden,
  sind vom Score selbst ausgewaehlt.  Sie gehoeren ausgeschlossen; beim ersten
  Anlauf waren es vier von fuenfzehn.
* SAISON.  Ohne Vergleich innerhalb eines +/-21-Tage-Fensters wuerde
  "im Sommer fotografiert man oefter" als Score-Signal durchgehen.
"""
import argparse
import json
import math
import os
from datetime import date

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FENSTER_TAGE = 21
BERLIN = (52.2, 52.8, 13.0, 13.9)
# Aus der Rueckschau-Durchsicht gefunden, also vom Score ausgewaehlt
ZIRKULAER = {"2025-06-29", "2023-06-14", "2023-05-29", "2022-11-11"}


def tag_im_jahr(s):
    return date.fromisoformat(s).timetuple().tm_yday


def rang(wert, vergleich):
    kl = sum(1 for x in vergleich if x < wert)
    gl = sum(1 for x in vergleich if x == wert)
    return (kl + 0.5 * gl) / len(vergleich)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--album", default="Sonnenuntergänge")
    ap.add_argument("--mit-zirkulaeren", action="store_true")
    ap.add_argument("--klima", default=os.path.join(
        BASIS, "daten", "score_berlin_g0.5_2022_2025.json"))
    a = ap.parse_args()

    with open(a.klima) as f:
        klima = json.load(f)
    fp = os.path.join(BASIS, "daten", "foto_detail.json")
    if not os.path.exists(fp):
        raise SystemExit("foto_detail.json fehlt - Skript aus Terminal.app laufen lassen")
    with open(fp) as f:
        detail = json.load(f)

    alben = {}
    for x in detail:
        for t in x.get("alben", []):
            alben[t] = alben.get(t, 0) + 1
    if not alben:
        raise SystemExit("Keine Albumdaten in foto_detail.json - alte Fassung?\n"
                         "fotos_detail.py neu laufen lassen (aus Terminal.app).")
    if a.album not in alben:
        print("Album '%s' nicht gefunden. Vorhanden:" % a.album)
        for t, k in sorted(alben.items(), key=lambda x: -x[1])[:20]:
            print("   %-40s %d" % (t[:40], k))
        raise SystemExit(1)

    kandidaten = sorted({x["tag"] for x in detail
                         if a.album in x.get("alben", [])
                         and BERLIN[0] <= x["lat"] <= BERLIN[1]
                         and BERLIN[2] <= x["lon"] <= BERLIN[3]})
    drin = [t for t in kandidaten if t in klima]
    if not a.mit_zirkulaeren:
        raus = [t for t in drin if t in ZIRKULAER]
        drin = [t for t in drin if t not in ZIRKULAER]
        if raus:
            print("ausgeschlossen (aus der Balken-Durchsicht, zirkulaer): %s"
                  % ", ".join(raus))
    print("Album '%s': %d Abende in Berlin, %d davon in der Klimatologie"
          % (a.album, len(kandidaten), len(drin)))
    if len(drin) < 8:
        raise SystemExit("zu wenige fuer einen Test")

    nach = {}
    for t, v in klima.items():
        nach.setdefault(tag_im_jahr(t), []).append(v)

    def fenster(t, k):
        j = tag_im_jahr(t)
        aus = []
        for dd in range(-FENSTER_TAGE, FENSTER_TAGE + 1):
            for v in nach.get((j + dd - 1) % 365 + 1, []):
                if v.get(k) is not None:
                    aus.append(v[k])
        return aus

    print()
    print("=== Anreicherung (saisonaler Perzentilrang, H0 = 0.500)")
    for k, name in (("s", "S = Schirm x Fenster"), ("A", "A  nur Schirm"),
                    ("B", "B  nur Fenster")):
        r = [rang(klima[t][k], fenster(t, k)) for t in drin
             if klima[t].get(k) is not None]
        m = sum(r) / len(r)
        z = (m - 0.5) / math.sqrt(1.0 / 12.0 / len(r))
        p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
        print("   %-22s n=%3d   Mittelrang %.3f   z = %+5.2f   p = %.4f  %s"
              % (name, len(r), m, z, p, "SIGNIFIKANT" if abs(z) > 1.96 else ""))

    alle = sorted(v["s"] for v in klima.values())
    print()
    print("=== Wuerde der Alarm sie melden?")
    print("   %-26s %-14s %s" % ("Alarmrate", "Schwelle", "Treffer"))
    for pz, lab in ((95, "18/Jahr"), (93.2, "25/Jahr"), (90, "37/Jahr"),
                    (85, "55/Jahr"), (80, "73/Jahr")):
        sw = alle[int(len(alle) * pz / 100)]
        tr = sum(1 for t in drin if klima[t]["s"] >= sw)
        # Wilson-Intervall, damit die Unsicherheit sichtbar bleibt
        n, ph = len(drin), tr / len(drin)
        zz = 1.96
        mitte = (ph + zz * zz / (2 * n)) / (1 + zz * zz / n)
        halb = zz * math.sqrt(ph * (1 - ph) / n + zz * zz / (4 * n * n)) / (1 + zz * zz / n)
        print("   p%-4s (%-9s) S >= %.3f    %2d von %2d = %2.0f %%  "
              "[%.0f..%.0f %%]"
              % (pz, lab, sw, tr, n, 100 * ph,
                 100 * max(0, mitte - halb), 100 * min(1, mitte + halb)))

    print()
    print("=== Die einzelnen Abende, schlechtester zuerst")
    zeilen = sorted(drin, key=lambda t: rang(klima[t]["s"], fenster(t, "s")))
    for t in zeilen:
        v = klima[t]
        print("   %s  S=%.3f  Rang %.2f  A=%.2f B=%.2f  %s"
              % (t, v["s"], rang(v["s"], fenster(t, "s")), v["A"] or 0,
                 v["B"] or 0, v["schirm"]))


if __name__ == "__main__":
    main()
