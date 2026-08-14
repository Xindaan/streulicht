"""Abbruchtest, zweiter Anlauf: Vergleich INNERHALB der Draussen-Abende.

Der erste Anlauf (abbruchtest.py) scheiterte an einem konfundierten Label.
Fotoabende gegen alle Abende zu stellen misst "war draussen" - und draussen
sein korreliert mit klarem Himmel, also MIT dem Fensterterm und GEGEN den
Schirmterm.  Im Produkt hoben sich beide auf (z = +0.57).

Hier ist die Grundgesamtheit deshalb NUR die Menge der Fotoabende.  Alle
waren draussen; der Konfounder ist damit konstant gehalten.  Verglichen wird
zwischen Abenden mit und ohne Absichtssignal:

  Favorit          mindestens eine als Favorit markierte Aufnahme im Fenster
  Naehe            kuerzester Abstand zum Sonnenuntergang unter 10 min
                   (gegen: ueber 20 min - beilaeufige Aufnahmen)

Wenn der Score traegt, muessen absichtsvolle Sonnenuntergangsabende einen
hoeheren Perzentilrang haben als beilaeufige.  Das ist der eigentliche Test.

Weiterhin gilt: nicht "S > 0.5" ist die Frage, sondern ob S staerker trennt
als A und B einzeln.  Sonst ist ein Term zu viel.
"""
import json
import math
import os
from datetime import date

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FENSTER_TAGE = 21
BERLIN = (52.2, 52.8, 13.0, 13.9)


def tag_im_jahr(s):
    return date.fromisoformat(s).timetuple().tm_yday


def rang(wert, vergleich):
    kleiner = sum(1 for x in vergleich if x < wert)
    gleich = sum(1 for x in vergleich if x == wert)
    return (kleiner + 0.5 * gleich) / len(vergleich)


def zwei_gruppen(name, a, b, la, lb):
    """Zwei-Stichproben-z auf Perzentilraengen."""
    if len(a) < 15 or len(b) < 15:
        print("   %-22s zu wenige (%d / %d)" % (name, len(a), len(b)))
        return None
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    z = (ma - mb) / se
    print("   %-22s %s %.3f (n=%3d)   %s %.3f (n=%3d)   Diff %+.3f  z = %+5.2f  %s"
          % (name, la, ma, len(a), lb, mb, len(b), ma - mb, z,
             "signifikant" if abs(z) > 1.96 else "-"))
    return z


def main():
    kl = os.path.join(BASIS, "daten", "score_berlin_g0.5_2022_2025.json")
    fo = os.path.join(BASIS, "daten", "foto_detail.json")
    for p in (kl, fo):
        if not os.path.exists(p):
            raise SystemExit("fehlt: %s" % p)
    with open(kl) as f:
        klima = json.load(f)
    with open(fo) as f:
        detail = json.load(f)

    # Nur Berlin, nur Abende, fuer die es einen Klimatologie-Score gibt
    abende = {}
    for x in detail:
        if not (BERLIN[0] <= x["lat"] <= BERLIN[1]
                and BERLIN[2] <= x["lon"] <= BERLIN[3]):
            continue
        if x["tag"] not in klima:
            continue
        alt = abende.get(x["tag"])
        if alt is None or x["min_abstand"] < alt["min_abstand"]:
            abende[x["tag"]] = x
        if alt is not None:
            abende[x["tag"]]["favoriten"] = max(alt["favoriten"], x["favoriten"])

    print("Berliner Fotoabende in der Klimatologie: %d" % len(abende))
    print("   davon mit Favorit: %d" % sum(1 for v in abende.values()
                                           if v["favoriten"] > 0))
    print("   davon <10 min am Sonnenuntergang: %d"
          % sum(1 for v in abende.values() if v["min_abstand"] < 10))

    nach_tag = {}
    for t, v in klima.items():
        nach_tag.setdefault(tag_im_jahr(t), []).append(v)

    def fenster(t, k):
        j = tag_im_jahr(t)
        aus = []
        for d in range(-FENSTER_TAGE, FENSTER_TAGE + 1):
            for v in nach_tag.get((j + d - 1) % 365 + 1, []):
                if v.get(k) is not None:
                    aus.append(v[k])
        return aus

    raenge = {}
    for k in ("s", "A", "B"):
        raenge[k] = {}
        for t in abende:
            w = klima[t].get(k)
            v = fenster(t, k)
            if w is not None and len(v) >= 30:
                raenge[k][t] = rang(w, v)

    print()
    print("=== Test 1: Favoritenabende gegen uebrige - beide draussen")
    for k, name in (("s", "S = Schirm x Fenster"), ("A", "A  nur Schirm"),
                    ("B", "B  nur Fenster")):
        fav = [raenge[k][t] for t in raenge[k] if abende[t]["favoriten"] > 0]
        rest = [raenge[k][t] for t in raenge[k] if abende[t]["favoriten"] == 0]
        zwei_gruppen(name, fav, rest, "Favorit", "ohne")

    print()
    print("=== Test 2: dicht am Sonnenuntergang (<10 min) gegen beilaeufig (>20 min)")
    for k, name in (("s", "S = Schirm x Fenster"), ("A", "A  nur Schirm"),
                    ("B", "B  nur Fenster")):
        nah = [raenge[k][t] for t in raenge[k] if abende[t]["min_abstand"] < 10]
        fern = [raenge[k][t] for t in raenge[k] if abende[t]["min_abstand"] > 20]
        zwei_gruppen(name, nah, fern, "nah   ", "fern")

    print()
    print("=== Test 3: beides zusammen (Favorit UND <10 min) gegen den Rest")
    for k, name in (("s", "S = Schirm x Fenster"), ("A", "A  nur Schirm"),
                    ("B", "B  nur Fenster")):
        ja = [raenge[k][t] for t in raenge[k]
              if abende[t]["favoriten"] > 0 and abende[t]["min_abstand"] < 10]
        nein = [raenge[k][t] for t in raenge[k]
                if not (abende[t]["favoriten"] > 0 and abende[t]["min_abstand"] < 10)]
        zwei_gruppen(name, ja, nein, "beides ", "Rest")

    print()
    print("=== Kontrolle: Absolutniveau gegen die Klimatologie")
    for k, name in (("s", "S"), ("A", "A"), ("B", "B")):
        alle = list(raenge[k].values())
        m = sum(alle) / len(alle)
        z = (m - 0.5) / math.sqrt(1.0 / 12.0 / len(alle))
        print("   %-3s alle Fotoabende: Mittelrang %.3f  z = %+5.2f" % (name, m, z))


if __name__ == "__main__":
    main()
