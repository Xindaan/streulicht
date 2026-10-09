"""Sichtfaktor gleich gewichtet oder raumwinkelgewichtet: erst messen (T-0086).

Reine Messung, KEINE Aenderung an sonnen/score.py.  Rechnet die Klimatologie
aus den Rohdaten in daten/roh/ (IFS-Analysen, 3 Schichten, 118 Zellen) neu und
vergleicht drei Sichtfaktor-Varianten:

  gleich          heute: die 6 Sichtzellen (Standort + 5 Zellen bei 60 km)
                  zaehlen je 1/6.
  raumwinkel      Gewichte wie Term A (score._schirmgewichte, Schirmhoehe des
                  jeweiligen Schirms), auf die Sichtzellen renormiert: d=0
                  bekommt rund 78 % (hoher Schirm), die 5 Zellen bei 60 km
                  teilen sich den Rest.
  raumwinkel_abs  dieselben Gewichte OHNE Renormierung, d.h. die Zellen jenseits
                  60 km zaehlen als frei.  So ist die Vorlage-Rechnung
                  (S = 0,229 im Konstruktionsfall) entstanden; mitgerechnet,
                  damit die beiden Lesarten von "gleiche Gewichte wie Term A"
                  nebeneinander stehen.

Die Varianten laufen ueber eine KOPIE von score.py im Speicher: der Quelltext
wird eingelesen, an genau zwei Stellen ersetzt (Ersetzung muss je einmal
treffen, sonst Abbruch) und als eigenes Modul geladen.  Im Modus "gleich"
gewichtet die Kopie jede Zelle mit 1.0 und teilt durch deren Zahl - das ist
exakt der heutige Rechenweg.  Zwei Gegenproben brechen den Lauf ab, wenn die
Kopie nicht stimmt:

  1. Der Konstruktionsfall der Vorlage (hoher Schirm 0,9, tiefe Decke nur am
     Standort) muss 0,75 / 0,229 ergeben.
  2. Modus "gleich" muss die gespeicherte Klimatologie
     daten/score_berlin_g0.5_2015_2025.json Abend fuer Abend reproduzieren.

"Der Fall" (Definition, siehe fall_flags):
  tiefe Decke nur in der Standortzelle   low(d=0) >= 0,9
  Umgebung frei                          Mittel der Blockade der 5 Zellen bei
                                         60 km <= 0,2   (Blockade = 1-(1-low)(1-mid),
                                         wie im Sichtfaktor fuer den hohen Schirm)
  Schirm hoch                            Term A des hohen Schirms (9,5 km) >= 0,7
  "weit" gefasst: 0,8 / 0,3 / 0,5.
Als Gegenstueck derselbe Fall fuer den mittleren Schirm (4,2 km; blockiert
nur die tiefe Schicht): low(d=0) >= 0,9, Umgebung low <= 0,2, A_mid >= 0,7.

Aufruf (Netz ist nicht noetig, es wird nichts abgerufen):
    .venv/bin/python3 skripte/sichtfaktor_messung.py
"""
import argparse
import glob
import json
import math
import os
import random
import sys
import types
from datetime import date

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASIS)
sys.path.insert(0, os.path.join(BASIS, "skripte"))
import albumtest  # noqa: E402  (nur die Hilfen; main() laeuft nicht)
import klimatologie as K  # noqa: E402
from sonnen.score import SICHT_KM  # noqa: E402

BREITE, LAENGE = 52.52, 13.405
MODI = ("gleich", "raumwinkel", "raumwinkel_abs")
SCHICHTEN = ("low", "mid", "high")
S_STERN_JAHRE = (2022, 2025)   # s* = 95. Perzentil dieser Jahre (so ist 0,7065 entstanden)

# Genau zwei Ersetzungen im Quelltext von score.py; jede muss einmal treffen.
ERSETZUNGEN = (
    ("                sicht_c += 1.0 - rest\n"
     "                sicht_n += 1\n",
     "                w_s = _sicht_gewicht(d, hoehe)\n"
     "                sicht_c += w_s * (1.0 - rest)\n"
     "                sicht_n += w_s\n"),
    ("        sicht = 1.0 - sicht_c / sicht_n\n",
     "        sicht = 1.0 - sicht_c / _sicht_nenner(sicht_n)\n"),
)
ANHANG = '''

SICHT_MODUS = "gleich"


def _sicht_gewicht(d, hoehe_km):
    if SICHT_MODUS == "gleich":
        return 1.0
    gw = _schirmgewichte(hoehe_km)
    return gw[d] / (1.0 if d == 0.0 else len(FAECHER_AZIMUTE))


def _sicht_nenner(sicht_n):
    return 1.0 if SICHT_MODUS == "raumwinkel_abs" else sicht_n
'''


def lade_kopie():
    pfad = os.path.join(BASIS, "sonnen", "score.py")
    with open(pfad) as f:
        quelle = f.read()
    for alt, neu in ERSETZUNGEN:
        if quelle.count(alt) != 1:
            raise SystemExit("score.py hat sich geaendert: Ersetzungsanker trifft "
                             "%dx statt 1x:\n%s" % (quelle.count(alt), alt))
        quelle = quelle.replace(alt, neu)
    import sonnen.geometrie  # noqa: F401  (Paket muss vor der Kopie geladen sein)
    mod = types.ModuleType("sonnen.score_sichtkopie")
    mod.__package__ = "sonnen"
    mod.__file__ = pfad
    exec(compile(quelle + ANHANG, pfad + " (Sichtkopie)", "exec"), mod.__dict__)
    return mod


# --------------------------------------------------------------- Rohdaten

def lade_roh(jahr):
    """{Zelle: {schicht: {Tag: Prozent}}} aus den Blockdateien eines Jahres."""
    aus = {}
    dateien = sorted(glob.glob(os.path.join(BASIS, "daten", "roh",
                                            "g%g_%d_*.json" % (K.GITTER, jahr))))
    if not dateien:
        raise SystemExit("Rohdaten fuer %d fehlen in daten/roh/ - es wird "
                         "NICHT nachgeladen." % jahr)
    for pfad in dateien:
        with open(pfad) as f:
            for k, v in json.load(f).items():
                la, lo = k.split("/")
                aus[(int(la), int(lo))] = v
    return aus


def pruefe_abdeckung(von, bis):
    """Alle Zellen und Tage, die der Score braucht, mit Werten in den Rohdaten?"""
    zellen, pro_tag = K.punktbedarf(date(von, 1, 1), date(bis, 12, 31),
                                    BREITE, LAENGE)
    sicht = set()
    luecken = []
    for jahr in range(von, bis + 1):
        feld = lade_roh(jahr)
        for t, karte in pro_tag.items():
            if t.year != jahr:
                continue
            for (d, dv), z in karte.items():
                if z not in feld:
                    luecken.append((str(t), z, "Zelle fehlt"))
                    continue
                if d <= SICHT_KM:
                    sicht.add(z)
                for s in SCHICHTEN:
                    if feld[z][s].get(str(t)) is None:
                        luecken.append((str(t), z, "%s ohne Wert" % s))
    return zellen, pro_tag, sicht, luecken


# ---------------------------------------------------------- Gegenproben

def konstruktionsfall(mod):
    """Vorlage Abschnitt 3: hoher Schirm 0,9 ueberall, tiefe Decke nur am Standort."""
    def hole(d, dv, schicht):
        if schicht == "high":
            return 0.9
        if schicht == "low":
            return 1.0 if d == 0.0 else 0.0
        return 0.0
    aus = {}
    for modus in MODI:
        mod.SICHT_MODUS = modus
        aus[modus] = mod.score(hole)[0]
    mod.SICHT_MODUS = "gleich"
    return aus


def gegenprobe_konstruktionsfall(mod):
    s = konstruktionsfall(mod)
    if abs(s["gleich"] - 0.75) > 1e-9 or abs(s["raumwinkel_abs"] - 0.2295) > 1e-3:
        raise SystemExit("Gegenprobe Konstruktionsfall FAELLT DURCH: %r" % s)
    return s


# -------------------------------------------------------------- Rechnung

def term_a(mod, hole, hoehe, name):
    """Term A wie in score(): Schirm im Nahbereich, raumwinkelgewichtet."""
    gw = mod._schirmgewichte(hoehe)
    werte = gew = 0.0
    for dv in mod.FAECHER_AZIMUTE:
        for d in mod.DISTANZEN_KM:
            if d > mod.NAHBEREICH_KM or (d == 0.0 and dv != 0.0):
                continue
            c = hole(d, dv, name)
            if c is None:
                continue
            w = gw[d] / (1.0 if d == 0.0 else len(mod.FAECHER_AZIMUTE))
            werte += w * c
            gew += w
    return werte / gew


def fall_flags(mod, hole):
    """Die Fall-Kennzahlen eines Abends (Definition im Modulkopf)."""
    low0 = hole(0.0, 0.0, "low")
    ring_low = [hole(60.0, dv, "low") for dv in mod.FAECHER_AZIMUTE]
    ring_blk = [1.0 - (1.0 - hole(60.0, dv, "low")) * (1.0 - hole(60.0, dv, "mid"))
                for dv in mod.FAECHER_AZIMUTE]
    umg_blk = sum(ring_blk) / len(ring_blk)
    umg_low = sum(ring_low) / len(ring_low)
    a_high = term_a(mod, hole, 9.5, "high")
    a_mid = term_a(mod, hole, 4.2, "mid")
    return {
        "low0": low0, "umg_blk": umg_blk, "umg_low": umg_low,
        "a_high": a_high, "a_mid": a_mid,
        "fall": low0 >= 0.9 and umg_blk <= 0.2 and a_high >= 0.7,
        "fall_weit": low0 >= 0.8 and umg_blk <= 0.3 and a_high >= 0.5,
        "fall_mid": low0 >= 0.9 and umg_low <= 0.2 and a_mid >= 0.7,
        "fall_mid_weit": low0 >= 0.8 and umg_low <= 0.3 and a_mid >= 0.5,
    }


def rechne(mod, pro_tag, von, bis):
    """{Tag: {modus: {s, A, B, sicht, schirm}, 'fall': {...}}} fuer alle Abende."""
    aus = {}
    for jahr in range(von, bis + 1):
        feld = lade_roh(jahr)
        for t, karte in pro_tag.items():
            if t.year != jahr:
                continue
            tag = str(t)

            def hole(d, dv, schicht, _t=tag, _k=karte):
                z = _k.get((d, dv))
                if z is None or z not in feld:
                    return None
                v = feld[z][schicht].get(_t)
                return None if v is None else v / 100.0

            satz = {}
            for modus in MODI:
                mod.SICHT_MODUS = modus
                s, det = mod.score(hole)
                if det is None:
                    satz[modus] = None
                    continue
                satz[modus] = {"s": s, "A": det["A"], "B": det["B"],
                               "sicht": det["sicht"], "schirm": det["schirm"]}
            mod.SICHT_MODUS = "gleich"
            if any(v is None for v in satz.values()):
                continue
            satz["fall"] = fall_flags(mod, hole)
            # Gegenprobe der Fall-Kennzahl: Term A, hier neu gerechnet, muss der
            # A aus score() fuer den gewinnenden Schirm entsprechen.
            ref = (satz["fall"]["a_high"] if satz["gleich"]["schirm"] == "high"
                   else satz["fall"]["a_mid"])
            if abs(ref - satz["gleich"]["A"]) > 1e-12:
                raise SystemExit("Gegenprobe Term A FAELLT DURCH am %s: %.6f vs %.6f"
                                 % (tag, ref, satz["gleich"]["A"]))
            aus[tag] = satz
    return aus


def gegenprobe_archiv(erg):
    """Modus "gleich" muss die gespeicherte 11-Jahres-Klimatologie reproduzieren."""
    pfad = os.path.join(BASIS, "daten", "score_berlin_g0.5_2015_2025.json")
    with open(pfad) as f:
        archiv = json.load(f)
    fehlt = [t for t in erg if t not in archiv]
    maxabw = max(abs(erg[t]["gleich"]["s"] - archiv[t]["s"])
                 for t in erg if t in archiv)
    anders = sum(1 for t in erg if t in archiv
                 and erg[t]["gleich"]["schirm"] != archiv[t]["schirm"])
    if fehlt or maxabw > 1e-9 or anders:
        raise SystemExit("Gegenprobe Archiv FAELLT DURCH: %d Abende nicht im "
                         "Archiv, max. Abweichung %.3g, %d andere Schirme"
                         % (len(fehlt), maxabw, anders))
    return len(erg), maxabw


# ------------------------------------------------------------ Auswertung

def quantil(werte, p):
    """Gleicher Index wie albumtest/auswertung: sortiert[int(n*p)]."""
    w = sorted(werte)
    return w[min(int(len(w) * p), len(w) - 1)]


def verteilung(erg, modus, jahre):
    s = [v[modus]["s"] for t, v in erg.items() if jahre[0] <= int(t[:4]) <= jahre[1]]
    return {"n": len(s), "mittel": sum(s) / len(s),
            "p50": quantil(s, 0.50), "p75": quantil(s, 0.75),
            "p90": quantil(s, 0.90), "p95": quantil(s, 0.95),
            "p99": quantil(s, 0.99), "max": max(s),
            "ueber_0_5": sum(1 for x in s if x >= 0.5) / len(s)}


def je_jahr(erg, modus, schwelle, von, bis):
    zahl = {j: 0 for j in range(von, bis + 1)}
    for t, v in erg.items():
        if v[modus]["s"] >= schwelle:
            zahl[int(t[:4])] += 1
    return zahl


def album_abende(jahre):
    with open(os.path.join(BASIS, "daten", "foto_detail.json")) as f:
        detail = json.load(f)
    b = albumtest.BERLIN
    tage = sorted({x["tag"] for x in detail
                   if "Sonnenuntergänge" in x.get("alben", [])
                   and b[0] <= x["lat"] <= b[1] and b[2] <= x["lon"] <= b[3]})
    return [t for t in tage if t not in albumtest.ZIRKULAER
            and jahre[0] <= int(t[:4]) <= jahre[1]]


def album_probe(erg, modus, jahre, abende, schluessel="s"):
    """Wie albumtest.py: saisonaler Perzentilrang der Album-Abende."""
    ref = {t: v[modus] for t, v in erg.items() if jahre[0] <= int(t[:4]) <= jahre[1]}
    nach = {}
    for t, v in ref.items():
        nach.setdefault(albumtest.tag_im_jahr(t), []).append(v[schluessel])

    def fenster(t):
        j = albumtest.tag_im_jahr(t)
        aus = []
        for dd in range(-albumtest.FENSTER_TAGE, albumtest.FENSTER_TAGE + 1):
            aus.extend(nach.get((j + dd - 1) % 365 + 1, []))
        return aus

    drin = [t for t in abende if t in ref]
    raenge = {t: albumtest.rang(ref[t][schluessel], fenster(t)) for t in drin}
    m = sum(raenge.values()) / len(raenge)
    z = (m - 0.5) / math.sqrt(1.0 / 12.0 / len(raenge))
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    schwelle = quantil([v["s"] for v in ref.values()], 0.95)
    treffer = sum(1 for t in drin if ref[t]["s"] >= schwelle)
    return {"n": len(drin), "mittel": m, "z": z, "p": p, "schwelle": schwelle,
            "treffer": treffer, "raenge": raenge}


def bootstrap_differenz(r_a, r_b, n_boot=5000, seed=20261009):
    """95-%-Intervall der mittleren Rangdifferenz (b - a), gepaart je Abend."""
    tage = sorted(r_a)
    diff = [r_b[t] - r_a[t] for t in tage]
    rnd = random.Random(seed)
    mittel = sorted(sum(rnd.choice(diff) for _ in diff) / len(diff)
                    for _ in range(n_boot))
    return (sum(diff) / len(diff), mittel[int(0.025 * n_boot)],
            mittel[int(0.975 * n_boot)],
            sum(1 for x in diff if x > 1e-12), sum(1 for x in diff if x < -1e-12))


# ------------------------------------------------------------------ Lauf

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--von", type=int, default=2015)
    ap.add_argument("--bis", type=int, default=2025)
    a = ap.parse_args()

    zellen, pro_tag, sicht, luecken = pruefe_abdeckung(a.von, a.bis)
    print("=== 1. Abdeckung der Rohdaten (daten/roh/, %d-%d)" % (a.von, a.bis))
    print("   Abende %d, benoetigte Zellen %d, davon Sichtzellen %d"
          % (len(pro_tag), len(zellen), len(sicht)))
    print("   Luecken (Zelle/Tag/Schicht ohne Wert): %d" % len(luecken))
    if luecken:
        print("   erste Luecken: %s" % luecken[:5])
        raise SystemExit("Rohdaten reichen NICHT - Abbruch, es wird nichts abgerufen.")

    mod = lade_kopie()
    kf = gegenprobe_konstruktionsfall(mod)
    print("\n=== 2. Gegenprobe Konstruktionsfall (hoher Schirm 0,9, Decke nur am Standort)")
    for m in MODI:
        print("   %-15s S = %.4f" % (m, kf[m]))

    erg = rechne(mod, pro_tag, a.von, a.bis)
    n, maxabw = gegenprobe_archiv(erg)
    print("\n=== 3. Gegenprobe Archiv: Modus 'gleich' reproduziert %d Abende, "
          "max. Abweichung %.2e, Schirm-Wahl identisch" % (n, maxabw))

    j0, j1 = S_STERN_JAHRE
    print("\n=== 4. Score-Verteilung (alle %d Klimatologie-Abende %d-%d / "
          "Referenzjahre %d-%d)" % (len(erg), a.von, a.bis, j0, j1))
    kopf = "   %-15s %-9s %6s %6s %6s %6s %6s %6s %6s %8s"
    print(kopf % ("Variante", "Jahre", "Mittel", "p50", "p75", "p90", "p95",
                  "p99", "max", "S>=0,5"))
    sstern = {}
    for m in MODI:
        for lab, jj in (("%d-%d" % (a.von, a.bis), (a.von, a.bis)),
                        ("%d-%d" % (j0, j1), (j0, j1))):
            d = verteilung(erg, m, jj)
            if jj == (j0, j1):
                sstern[m] = d["p95"]
            print("   %-15s %-9s %6.3f %6.3f %6.3f %6.3f %6.3f %6.3f %6.3f %7.1f%%"
                  % (m, lab, d["mittel"], d["p50"], d["p75"], d["p90"], d["p95"],
                     d["p99"], d["max"], 100 * d["ueber_0_5"]))

    print("\n   s* je Variante = 95. Perzentil %d-%d (so ist 0,7065 entstanden): %s"
          % (j0, j1, ", ".join("%s %.4f" % (m, sstern[m]) for m in MODI)))
    unterschied = [abs(v["raumwinkel"]["s"] - v["gleich"]["s"]) for v in erg.values()]
    print("   Abende mit |S_raumwinkel - S_gleich| > 0,05: %d (%.1f %%), > 0,2: %d; "
          "groesste Abweichung %.3f"
          % (sum(1 for x in unterschied if x > 0.05),
             100 * sum(1 for x in unterschied if x > 0.05) / len(unterschied),
             sum(1 for x in unterschied if x > 0.2), max(unterschied)))
    gr = [v["raumwinkel"]["sicht"] - v["gleich"]["sicht"] for v in erg.values()]
    print("   Sichtfaktor raumwinkel - gleich: Mittel %+.3f, min %+.3f, max %+.3f"
          % (sum(gr) / len(gr), min(gr), max(gr)))

    print("\n=== 5. Abende ueber s* je Jahr")
    zeilen = [("gleich     @ s*_gleich %.4f" % sstern["gleich"], "gleich", sstern["gleich"]),
              ("raumwinkel @ s*_rw     %.4f" % sstern["raumwinkel"], "raumwinkel", sstern["raumwinkel"]),
              ("raumwinkel_abs @ s*_abs %.4f" % sstern["raumwinkel_abs"], "raumwinkel_abs", sstern["raumwinkel_abs"]),
              ("raumwinkel @ heutiges s* %.4f" % sstern["gleich"], "raumwinkel", sstern["gleich"])]
    jahre = list(range(a.von, a.bis + 1))
    print("   %-34s %s  | Mittel/Jahr" % ("", " ".join("%4d" % j for j in jahre)))
    for lab, m, sw in zeilen:
        z = je_jahr(erg, m, sw, a.von, a.bis)
        print("   %-34s %s  | %5.1f" % (lab, " ".join("%4d" % z[j] for j in jahre),
                                      sum(z.values()) / len(jahre)))

    print("\n=== 6. Alarmmengen gegeneinander (s* je Variante, %d-%d)" % (a.von, a.bis))
    for m in ("raumwinkel", "raumwinkel_abs"):
        nur_g = [t for t, v in erg.items()
                 if v["gleich"]["s"] >= sstern["gleich"] and v[m]["s"] < sstern[m]]
        nur_m = [t for t, v in erg.items()
                 if v["gleich"]["s"] < sstern["gleich"] and v[m]["s"] >= sstern[m]]
        beide = sum(1 for v in erg.values()
                    if v["gleich"]["s"] >= sstern["gleich"] and v[m]["s"] >= sstern[m])
        print("   gleich vs %-15s beide %3d | nur gleich %3d | nur %s %3d"
              % (m, beide, len(nur_g), m, len(nur_m)))
        if m == "raumwinkel":
            for lab, liste in (("nur gleich", nur_g), ("nur raumwinkel", nur_m)):
                print("      %s: Abend, S gleich/raumwinkel, Sichtfaktor "
                      "gleich/raumwinkel, A, low(Standort), Blockade Umgebung, Schirm"
                      % lab)
                for t in sorted(liste):
                    v, fl = erg[t], erg[t]["fall"]
                    print("         %s  S %.3f/%.3f  sicht %.2f/%.2f  A %.2f  "
                          "low0 %.2f  Umg. %.2f  %s"
                          % (t, v["gleich"]["s"], v[m]["s"], v["gleich"]["sicht"],
                             v[m]["sicht"], v["gleich"]["A"], fl["low0"],
                             fl["umg_blk"], v["gleich"]["schirm"]))
        if nur_g:
            print("      nur gleich, davon Fall hoher Schirm %d (weit %d), Fall "
                  "mittlerer Schirm %d (weit %d); mittlerer Sichtfaktor "
                  "gleich %.3f vs %s %.3f"
                  % (sum(1 for t in nur_g if erg[t]["fall"]["fall"]),
                     sum(1 for t in nur_g if erg[t]["fall"]["fall_weit"]),
                     sum(1 for t in nur_g if erg[t]["fall"]["fall_mid"]),
                     sum(1 for t in nur_g if erg[t]["fall"]["fall_mid_weit"]),
                     sum(erg[t]["gleich"]["sicht"] for t in nur_g) / len(nur_g), m,
                     sum(erg[t][m]["sicht"] for t in nur_g) / len(nur_g)))

    print("\n=== 7. Wie oft kommt der Fall vor?  (%d Abende, %d-%d)"
          % (len(erg), a.von, a.bis))
    for schl, lab in (("fall", "Fall, hoher Schirm (low0>=0,9, Umg.<=0,2, A_hoch>=0,7)"),
                      ("fall_weit", "Fall weit (0,8 / 0,3 / 0,5)"),
                      ("fall_mid", "Fall, mittlerer Schirm (low0>=0,9, Umg.<=0,2, A_mid>=0,7)"),
                      ("fall_mid_weit", "Fall mittlerer Schirm weit")):
        tage = [t for t, v in erg.items() if v["fall"][schl]]
        ueber = {m: sum(1 for t in tage if erg[t][m]["s"] >= sstern[m]) for m in MODI}
        mittel = {m: (sum(erg[t][m]["s"] for t in tage) / len(tage)) if tage else 0.0
                  for m in MODI}
        print("   %-62s %3d Abende (%.2f %% aller Abende)"
              % (lab, len(tage), 100 * len(tage) / len(erg)))
        if tage:
            print("      ueber s*: gleich %d, raumwinkel %d, raumwinkel_abs %d | "
                  "mittleres S: %.3f / %.3f / %.3f"
                  % (ueber["gleich"], ueber["raumwinkel"], ueber["raumwinkel_abs"],
                     mittel["gleich"], mittel["raumwinkel"], mittel["raumwinkel_abs"]))
            print("      Abende: %s" % ", ".join(sorted(tage)[:8])
                  + (" ..." if len(tage) > 8 else ""))
            ue = [t for t in sorted(tage) if erg[t]["gleich"]["s"] >= sstern["gleich"]]
            if ue:
                print("      davon ueber s* (gleich): %s" % ", ".join(ue))
    # Hintergrund: wie haeufig ist jede Teilbedingung allein?
    f = [v["fall"] for v in erg.values()]
    print("   Teilbedingungen einzeln: low0>=0,9 %d | Umg.<=0,2 %d | A_hoch>=0,7 %d | "
          "low0>=0,9 und Umg.<=0,2 %d"
          % (sum(1 for x in f if x["low0"] >= 0.9),
             sum(1 for x in f if x["umg_blk"] <= 0.2),
             sum(1 for x in f if x["a_high"] >= 0.7),
             sum(1 for x in f if x["low0"] >= 0.9 and x["umg_blk"] <= 0.2)))

    print("\n=== 8. Albumprobe (wie albumtest.py: saisonaler Perzentilrang, "
          "Album 'Sonnenuntergaenge', ohne zirkulaere Abende)")
    for lab, jj in (("Referenz %d-%d (= albumtest.py)" % (j0, j1), (j0, j1)),
                    ("Referenz %d-%d" % (a.von, a.bis), (a.von, a.bis))):
        abende = album_abende(jj)
        print("   -- %s, %d Album-Abende im Zeitraum" % (lab, len(abende)))
        res = {m: album_probe(erg, m, jj, abende) for m in MODI}
        for m in MODI:
            r = res[m]
            print("   %-15s n=%2d  Mittelrang %.3f  z=%+5.2f  p=%.4f  "
                  "Treffer bei p95 (S>=%.3f): %d von %d"
                  % (m, r["n"], r["mittel"], r["z"], r["p"], r["schwelle"],
                     r["treffer"], r["n"]))
        for m in ("raumwinkel", "raumwinkel_abs"):
            d, lo, hi, besser, schlechter = bootstrap_differenz(
                res["gleich"]["raenge"], res[m]["raenge"])
            print("   Rangdifferenz %s - gleich: %+.4f  [95%%-Bootstrap %+.4f..%+.4f]"
                  "  verbessert %d, verschlechtert %d, gleich %d"
                  % (m, d, lo, hi, besser, schlechter,
                     res[m]["n"] - besser - schlechter))
        # A und B getrennt: B enthaelt den Sichtfaktor
        rb = {m: album_probe(erg, m, jj, abende, "B") for m in MODI}
        print("   nur Fenster B: " + " | ".join(
            "%s Mittelrang %.3f z=%+.2f" % (m, rb[m]["mittel"], rb[m]["z"]) for m in MODI))


if __name__ == "__main__":
    main()
