"""Werte den Aufloesungstest aus: ICON-D2 (2.2 km) gegen ERA5 (25 km).

FRAGE.  Abschnitt 25 der Befunde zeigte, dass beide Darstellungen desselben
grobmaschigen Modells Andres beste Abende verfehlen.  Bleibt die Aufloesung.
Sieht ein 2.2-km-Modell die Wolkenstrukturen, die 25 km wegmitteln?

AUFBAU.  Gepaart, nicht gegen eine Klimatologie.  Jeder Albumabend bildet
einen Block mit vier Kontrollabenden aus seinem +/- 21-Tage-Fenster.  Der
Rang des Albumabends INNERHALB seines Blocks ist die Messgroesse; unter der
Nullhypothese ist er gleichverteilt, der Mittelrang also 0.5.

Der gepaarte Aufbau ist hier nicht Zierde: er haelt Jahreszeit, Sonnenstand
und Tageslaenge konstant.  Ein Verfahren, das im Sommer generell hoehere
Werte liefert, gewinnt dadurch nichts.

DREI VERFAHREN, damit der Gewinn dem richtigen Faktor zugeschrieben wird:

    era5_3s    ERA5 25 km, drei Schichten      - der Status quo
    icon_3s    ICON-D2 2.2 km, drei Schichten  - isoliert die AUFLOESUNG
    icon_niv   ICON-D2 2.2 km, neun Flaechen   - Aufloesung PLUS Niveaus

era5_3s gegen icon_3s misst die Aufloesung allein, weil Geometrie, Score und
Faecher identisch sind und sich nur die Gitterweite der Quelle unterscheidet.
icon_3s gegen icon_niv misst, was die Niveauaufloesung obendrauf bringt.

VORAB FESTGELEGT, bevor die Zahlen da waren:
Ein Wechsel auf ICON-D2 lohnt nur, wenn der Mittelrang um mindestens 0.05
steigt UND das gepaarte 95-%-Intervall der Differenz die Null nicht enthaelt.
Alles darunter ist ein Messergebnis, kein Grund fuer einen Umbau - zumal
ICON-D2 nur 48 h Vorlauf hat und ausserhalb Mitteleuropas gar nicht existiert.
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen import score as s3                                   # noqa: E402
from sonnen import score_niveaus as sn                           # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(BASIS, "daten", "roh_icond2")

# ICAO-Standardatmosphaere, dieselbe Quelle wie die Projekttabelle - die
# aber 925/850 fuehrt, waehrend ICON-D2 hier auf 900/800 abgefragt wurde.
HOEHEN = {900: 0.988, 800: 1.949, 700: 3.012, 600: 4.206, 500: 5.574,
          400: 7.185, 300: 9.164, 250: 10.363, 200: 11.784}
SCHIRME_HPA = (600, 500, 400, 300, 250, 200)


def lade(tag):
    p = os.path.join(CACHE, "%s.json" % tag)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def _zelle(daten, d, dv):
    z = daten["zellen"].get("%.1f_%.1f" % (d, dv))
    return None if z is None else z.get("w")


def icon_3schicht(daten):
    def hole(d, dv, schicht):
        w = _zelle(daten, d, dv)
        if not w:
            return None
        v = w.get("cloud_cover_%s" % schicht)
        return None if v is None else v / 100.0
    return s3.score(hole)


def icon_niveaus(daten, mit_dickenstrafe=True):
    def hole(d, dv, p):
        w = _zelle(daten, d, dv)
        if not w:
            return None
        v = w.get("cloud_cover_%dhPa" % p)
        return None if v is None else v / 100.0
    return sn.score(hole, mit_dickenstrafe=mit_dickenstrafe, direkt=True,
                    hoehen=HOEHEN, schirm_niveaus=SCHIRME_HPA)


DREI_SCHICHTEN = ("cloud_cover_low", "cloud_cover_mid", "cloud_cover_high")
DRUCKFLAECHEN = tuple("cloud_cover_%dhPa" % p for p in sorted(HOEHEN))


def deckung(daten, gruppe):
    """Anteil der Faecherzellen, in denen JEDE Variable der Gruppe belegt ist.

    Die erste Fassung fragte nur, ob das Wertedict der Zelle nicht leer ist -
    und meldete 100 % fuer Abende, deren Druckflaechen durchgehend None waren
    (das Dict trug ja die drei Schichten).  Derselbe Fehler wie bei der
    Modellauswahl im Juli: "Schluessel vorhanden" als "Daten vorhanden"
    gelesen.  Deshalb hier je Variable zaehlen, nicht je Zelle.
    """
    z = daten["zellen"]
    da = sum(1 for v in z.values()
             if v.get("w") and all(v["w"].get(k) is not None for k in gruppe))
    return da / len(z)


def vollstaendig(daten, mindest=0.9, gruppe=DREI_SCHICHTEN):
    d = deckung(daten, gruppe)
    return d >= mindest, d


def rang_im_block(wert, kontrollen):
    """Normierter Rang: 0 = schlechtester, 1 = bester im Block."""
    kl = sum(1 for x in kontrollen if x < wert)
    gl = sum(1 for x in kontrollen if x == wert)
    return (kl + 0.5 * gl) / len(kontrollen)


def mittel_ki(werte, z=1.96):
    n = len(werte)
    m = sum(werte) / n
    if n < 2:
        return m, m, m
    sd = math.sqrt(sum((x - m) ** 2 for x in werte) / (n - 1))
    h = z * sd / math.sqrt(n)
    return m, m - h, m + h


def spearman(a, b):
    def rang(v):
        paare = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(paare):
            j = i
            while j + 1 < len(paare) and v[paare[j + 1]] == v[paare[i]]:
                j += 1
            for k in range(i, j + 1):
                r[paare[k]] = 0.5 * (i + j) + 1.0
            i = j + 1
        return r
    ra, rb = rang(a), rang(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    za = math.sqrt(sum((x - ma) ** 2 for x in ra))
    zb = math.sqrt(sum((x - mb) ** 2 for x in rb))
    if za == 0 or zb == 0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / (za * zb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mindestdeckung", type=float, default=0.9)
    a = ap.parse_args()

    with open(os.path.join(BASIS, "daten", "icond2_plan.json")) as f:
        plan = json.load(f)
    with open(os.path.join(BASIS, "daten",
                           "score_berlin_g0.5_2015_2025.json")) as f:
        era5 = json.load(f)
    with open(os.path.join(BASIS, "daten", "bewertung_andre.json")) as f:
        noten = json.load(f)

    # ICON-D2 hat ZWEI verschiedene Verfuegbarkeitsgrenzen, gemessen am
    # 14.08.2026: die drei Schichten ab 2023, die Druckflaechen erst ab 2024.
    # Deshalb zwei Auswertungen mit verschiedenem n statt einer mit stiller
    # Verkleinerung auf den Durchschnitt beider.
    bloecke, verworfen = [], {"fehlt": 0, "luecken": 0, "kein_era5": 0,
                              "phantom3": 0, "phantomN": 0}
    for ziel in plan["ziel"]:
        tage = [ziel] + plan["paare"][ziel]
        daten = {t: lade(t) for t in tage}
        if any(v is None for v in daten.values()):
            verworfen["fehlt"] += 1
            continue
        if any(t not in era5 for t in tage):
            verworfen["kein_era5"] += 1
            continue
        if not all(deckung(v, DREI_SCHICHTEN) >= a.mindestdeckung
                   for v in daten.values()):
            verworfen["luecken"] += 1
            continue
        hat_druck = all(deckung(v, DRUCKFLAECHEN) >= a.mindestdeckung
                        for v in daten.values())
        # T-0060: `[0]` allein reicht nicht.  Beide Score-Varianten liefern
        # (s, detail), und `detail is None` heisst "nicht auswertbar, es lagen
        # keine Daten vor" - der Score ist dann 0.0.  Wer nur die Zahl nimmt,
        # macht aus einer Datenluecke eine Null, und die geht als "besonders
        # unauffaelliger Abend" in den Mittelrang ein.  Genau diese
        # Phantomnullen vermeidet ablation.py ausdruecklich; hier fehlte die
        # Regel.
        #
        # Der Deckungsfilter oben ist KEIN Ersatz: er prueft die Rohdaten,
        # nicht die Auswertbarkeit des Scores.  Gemessen am Cache
        # (23.08.2026) faellt er zwar zusammen - bei `--mindestdeckung 0.9`
        # sind 0 von 55 Abenden betroffen -, aber die Deckung ist bimodal
        # (rund 1.0 oder rund 0.0), und wer die Schwelle senkt, um mehr
        # Bloecke zu bekommen, holt sich 36 von 175 Phantomnullen (21 %)
        # herein, waehrend der Kopf des Berichts weiter "0 mit Datenluecken"
        # meldet.
        w = {}
        phantom3 = phantomN = False
        for t in tage:
            s3, d3 = icon_3schicht(daten[t])
            if d3 is None:
                phantom3 = True
            if hat_druck:
                sn, dn = icon_niveaus(daten[t])
                if dn is None:
                    phantomN = True
            else:
                sn = None
            w[t] = {"era5_3s": era5[t]["s"], "icon_3s": s3, "icon_niv": sn}
        if phantom3:
            # Ohne icon_3s traegt der Block gar nichts - wie bei einer
            # Datenluecke wird er ganz verworfen, nicht halb ausgewertet.
            verworfen["phantom3"] += 1
            continue
        if phantomN:
            verworfen["phantomN"] += 1
        bloecke.append({"ziel": ziel, "kontrollen": plan["paare"][ziel],
                        "werte": w, "druck": hat_druck and not phantomN})

    mit_druck = [b for b in bloecke if b["druck"]]
    print("Bloecke auswertbar: %d von %d   (davon mit Druckflaechen: %d)"
          % (len(bloecke), len(plan["ziel"]), len(mit_druck)))
    print("  verworfen: %d ohne Cache, %d mit Datenluecken, %d ohne ERA5"
          % (verworfen["fehlt"], verworfen["luecken"], verworfen["kein_era5"]))
    # Getrennt ausweisen, nicht unter "Datenluecken" mitzaehlen: das hier ist
    # eine Luecke, die erst der SCORE bemerkt, nicht schon der Rohdatenfilter.
    if verworfen["phantom3"] or verworfen["phantomN"]:
        print("  nicht auswertbar (Score ohne Detail): %d Bloecke ganz "
              "verworfen, %d nur ohne Niveaus-Verfahren"
              % (verworfen["phantom3"], verworfen["phantomN"]))
    if len(bloecke) < 12:
        raise SystemExit("zu wenige Bloecke fuer eine Aussage")

    def raenge_von(bl, verfahren):
        r = {v: [] for v in verfahren}
        for b in bl:
            for v in verfahren:
                r[v].append(rang_im_block(
                    b["werte"][b["ziel"]][v],
                    [b["werte"][t][v] for t in b["kontrollen"]]))
        return r

    def berichte(bl, verfahren, titel):
        if len(bl) < 12:
            print()
            print("=== %s: nur %d Bloecke - keine Aussage, nicht gerechnet."
                  % (titel, len(bl)))
            return None
        r = raenge_von(bl, verfahren)
        n = len(bl)
        print()
        print("=== %s  (n = %d Bloecke)" % (titel, n))
        print("  Mittelrang des Albumabends im eigenen Block (0.5 = Zufall)")
        for v in verfahren:
            m, lo, hi = mittel_ki(r[v])
            sd = math.sqrt(sum((x - m) ** 2 for x in r[v]) / (n - 1))
            z = (m - 0.5) / (sd / math.sqrt(n) or 1e-9)
            print("   %-9s %.3f   95%%-KI [%.3f, %.3f]   z = %+.2f  %s"
                  % (v, m, lo, hi, z,
                     "signifikant" if abs(z) > 1.96 else "nicht sig."))
        print("  Gepaarte Differenzen (dieselben Bloecke, dieselben Abende)")
        for i in range(len(verfahren) - 1):
            for j in range(i + 1, len(verfahren)):
                a_, b_ = verfahren[i], verfahren[j]
                d = [y - x for x, y in zip(r[a_], r[b_])]
                m, lo, hi = mittel_ki(d)
                print("   %-9s -> %-9s  %+.3f  95%%-KI [%+.3f, %+.3f]   %s"
                      % (a_, b_, m, lo, hi,
                         "TRAEGT" if (lo > 0.0 and m >= 0.05) else
                         ("sig., aber unter 0.05" if lo > 0 else "nicht sig.")))
        return r

    print()
    print("Vorab festgelegt: Wechsel nur bei >= +0.05 UND KI ohne Null.")
    r_aufl = berichte(bloecke, ("era5_3s", "icon_3s"),
                      "AUFLOESUNG: ERA5 25 km gegen ICON-D2 2.2 km, gleicher Score")
    berichte(mit_druck, ("era5_3s", "icon_3s", "icon_niv"),
             "NIVEAUS obendrauf (nur Bloecke ab 2024)")

    mit_note = [b for b in bloecke if b["ziel"] in noten]
    if r_aufl is not None and len(mit_note) >= 12:
        print()
        print("=== Ordnung: Spearman gegen Andres Noten (n = %d)" % len(mit_note))
        no = [noten[b["ziel"]] for b in mit_note]
        for v in ("era5_3s", "icon_3s"):
            r = spearman([b["werte"][b["ziel"]][v] for b in mit_note], no)
            print("   %-9s rho = %+.3f" % (v, r))
        print("   Achtung Varianzeinschraenkung: alle Abende sind kuratiert,")
        print("   das daempft rho gegenueber der Gesamtheit systematisch.")

    with open(os.path.join(BASIS, "daten", "icond2_ergebnis.json"), "w") as f:
        json.dump({"bloecke": bloecke, "raenge_aufloesung": r_aufl}, f, indent=1)


if __name__ == "__main__":
    main()
