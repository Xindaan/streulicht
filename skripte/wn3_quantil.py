"""s* fuer WeatherNext 3 ueber eine Quantilabbildung (T-0072).

WARUM NICHT EINFACH DAS 95. PERZENTIL VON WN3.  s* = 0,7065 ist ein Quantil
der Klimatologie (`klimatologie.py`, ECMWF IFS ueber `archive-api`, 0,5 Grad).
WN3s Archiv beginnt am 01.01.2026; ein Perzentil ueber Januar bis Oktober
waere jahreszeitlich schief (November und Dezember fehlen).  Die
Quantilabbildung umgeht das: sie vergleicht beide Modelle an DENSELBEN
Abenden.  Der Unterschreitungsanteil q, den s* in der Referenz an diesen
Abenden hat, wird auf die WN3-Verteilung derselben Abende uebertragen:

    q       = Anteil der Referenzabende mit s < s*
    s*_WN3  = empirisches Quantil der WN3-Scores bei q

Dieselbe Bruecke, die Befund E1 fuer GFS -> ECMWF vorgesehen hatte.

WAS DIE ZAHL IST UND WAS NICHT.
* Auf der WN3-Seite steht der Score des p50-FELDES (Statistik-Bucket,
  kostenlos), nicht der Median der Memberscores (Review wn3#F1).  Das ist
  das Gegenstueck zur Referenz, die ebenfalls ein einzelnes Feld bewertet
  (IFS), nicht ein Ensemble.  Die Frage, ob dieselbe Schwelle auf Membern
  dieselbe Rate ergibt, ist fuer WN3 dieselbe offene Bruecke wie T-0020
  fuer ECMWF - sie wird hier NICHT beantwortet.
* Vorlauf: der WN3-Lauf, der VORLAUF_H Stunden vor der Sonnenuntergangs-
  stunde initialisiert wurde.  Kurz, weil die Referenz analysenah ist.
  Keine Verfuegbarkeitsregel wie in `wn3_vergleich.py`: hier wird das
  Modell kalibriert, nicht das Produkt zum Abrufzeitpunkt.
* Gitter: Referenz auf 0,5-Grad-Zellmitten, WN3 am naechsten 0,1-Grad-Punkt.
  Diesen Unterschied soll die Abbildung gerade mit aufnehmen.
* Unsicherheit: gepaarter Bootstrap ueber Abende.  Liegen weniger als
  MIN_EREIGNISSE Referenzabende ueber s*, ist die Zahl ein Platzhalter und
  wird so ausgegeben.

Lauf:
  .venv/bin/python3 skripte/wn3_quantil.py --holen     # WN3-Scores je Abend (kostenlos, Cache)
  .venv/bin/python3 skripte/wn3_quantil.py             # Abbildung aus Cache + Klimatologie
"""
import argparse
import datetime as dt
import glob
import importlib.util
import json
import os
import random
import sys

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASIS)

BREITE, LAENGE = 52.52, 13.405
VORLAUF_H = 6
MIN_EREIGNISSE = 10
ABENDE_AB = dt.date(2026, 1, 1)          # Beginn des WN3-Archivs
CACHE = os.path.join(BASIS, "daten", "wn3_p50", "berlin.json")


# --- Rechenkern (netzfrei, getestet in test_wn3_quantil.py) ---------------

def quantil(werte, q):
    """Empirisches Quantil, lineare Interpolation (Hyndman-Fan Typ 7)."""
    if not werte:
        raise ValueError("leere Reihe")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q ausserhalb [0, 1]: %r" % q)
    x = sorted(werte)
    h = (len(x) - 1) * q
    i = int(h)
    if i + 1 >= len(x):
        return x[-1]
    return x[i] + (h - i) * (x[i + 1] - x[i])


def quantilabbildung(ref, ziel, s_stern):
    """(q, s*_ziel) aus gepaarten Reihen derselben Abende.

    q ist der Anteil der Referenzwerte UNTER s* - wie s* als Perzentil
    definiert ist.  Liegt s* ueber allen Referenzwerten (q = 1), ist die
    Abbildung am Rand und liefert nur das Maximum der Zielreihe.
    """
    if len(ref) != len(ziel):
        raise ValueError("Reihen ungleich lang: %d gegen %d" % (len(ref), len(ziel)))
    if not ref:
        raise ValueError("keine gepaarten Abende")
    q = sum(1 for r in ref if r < s_stern) / float(len(ref))
    return q, quantil(ziel, q)


def bootstrap(ref, ziel, s_stern, n=2000, seed=1, niveau=0.90):
    """Gepaarter Bootstrap ueber Abende: (untere, obere) Grenze von s*_ziel."""
    rng = random.Random(seed)
    paare = list(zip(ref, ziel))
    werte = []
    for _ in range(n):
        stich = [paare[rng.randrange(len(paare))] for _ in paare]
        werte.append(quantilabbildung([a for a, _ in stich],
                                      [b for _, b in stich], s_stern)[1])
    rand = (1.0 - niveau) / 2.0
    return quantil(werte, rand), quantil(werte, 1.0 - rand)


# --- Daten ----------------------------------------------------------------

def referenz(jahr_ab=ABENDE_AB):
    """{Tag: s} aus allen Klimatologie-Dateien, nur Abende ab `jahr_ab`."""
    aus = {}
    for pfad in sorted(glob.glob(os.path.join(BASIS, "daten", "score_berlin_g0.5_*.json"))):
        if pfad.endswith("_punkt.json"):
            continue
        with open(pfad) as f:
            for tag, v in json.load(f).items():
                if tag >= str(jahr_ab) and v.get("s") is not None:
                    aus[tag] = v["s"]
    return aus


def lies_cache():
    if not os.path.exists(CACHE):
        return {}
    with open(CACHE) as f:
        return json.load(f)


def schreibe_cache(d):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    tmp = CACHE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=0, sort_keys=True)
    os.replace(tmp, CACHE)


def lauf_fuer(tag, laeufe, vorlauf_h=VORLAUF_H):
    """(Lauf, Zielzeit) - Init genau vorlauf_h vor der Sonnenuntergangsstunde."""
    from sonnen.geometrie import sonnenuntergang
    std, _ = sonnenuntergang(tag, BREITE, LAENGE)
    ziel = dt.datetime(tag.year, tag.month, tag.day, int(round(std)) % 24,
                       tzinfo=dt.timezone.utc)
    init = (ziel - dt.timedelta(hours=vorlauf_h)).strftime("%Y%m%d_%Hhr")
    return (init if init in laeufe else None), ziel


def holen(grenze_mb, vorlauf_h=VORLAUF_H, bis=None):
    from sonnen.score import score_fuer_abend
    spec = importlib.util.spec_from_file_location(
        "wn3_vergleich", os.path.join(BASIS, "skripte", "wn3_vergleich.py"))
    v = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v)
    wn3 = v.wn3

    laeufe = set(v.stat_laeufe())
    cache = lies_cache()
    budget = wn3.Budget(frei=False, grenze_mb=grenze_mb)
    bis = bis or dt.date.today() - dt.timedelta(days=1)
    tag, neu = ABENDE_AB, 0
    while tag <= bis:
        k = str(tag)
        if k in cache and cache[k].get("vorlauf_h") == vorlauf_h:
            tag += dt.timedelta(days=1)
            continue
        lauf, ziel = lauf_fuer(tag, laeufe, vorlauf_h)
        if lauf is None:
            print("%s  kein Lauf %d h vorher" % (k, vorlauf_h), flush=True)
            tag += dt.timedelta(days=1)
            continue
        try:
            q = wn3.Statistik(lauf, budget=budget)
            i = q.schritt(ziel)
            if i is None:
                print("%s  Zielstunde ausserhalb des Vorlaufs" % k, flush=True)
                tag += dt.timedelta(days=1)
                continue
            s, det = score_fuer_abend(tag, BREITE, LAENGE, v.feld_wn3(q, i))
        except wn3.Budgetueberschreitung as e:
            print("Budget erreicht (%s) - Rest beim naechsten Lauf." % e, flush=True)
            break
        if det is None:
            print("%s  nicht auswertbar (keine Phantomnull, T-0060)" % k, flush=True)
        else:
            cache[k] = {"s": s, "lauf": lauf, "vorlauf_h": vorlauf_h,
                        "schirm": det["schirm"]}
            schreibe_cache(cache)
            neu += 1
            print("%s  s=%.4f  %s  (%.0f MB)" % (k, s, lauf, budget.bytes / 1048576.0),
                  flush=True)
        tag += dt.timedelta(days=1)
    print("neu: %d Abende, Cache: %d, geholt %.0f MB (kostenlos)"
          % (neu, len(cache), budget.bytes / 1048576.0))


def auswerten(s_stern):
    ref = referenz()
    w = {t: e["s"] for t, e in lies_cache().items()}
    tage = sorted(set(ref) & set(w))
    if len(tage) < 2:
        raise SystemExit("zu wenige gepaarte Abende: %d (Referenz %d, WN3 %d)"
                         % (len(tage), len(ref), len(w)))
    r = [ref[t] for t in tage]
    z = [w[t] for t in tage]
    q, s_w = quantilabbildung(r, z, s_stern)
    lo, hi = bootstrap(r, z, s_stern)
    ueber = sum(1 for x in r if x >= s_stern)
    print("gepaarte Abende: %d (%s .. %s)" % (len(tage), tage[0], tage[-1]))
    print("Referenzabende ueber s* = %.4f: %d" % (s_stern, ueber))
    print("q = %.4f   s*_WN3 = %.4f   90-%%-Intervall [%.4f, %.4f]" % (q, s_w, lo, hi))
    if ueber < MIN_EREIGNISSE:
        print("PLATZHALTER: weniger als %d Ereignisse in der Referenz - die Zahl "
              "traegt keine Schwelle." % MIN_EREIGNISSE)
    return {"n": len(tage), "q": q, "s_wn3": s_w, "intervall": [lo, hi], "ereignisse": ueber}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--holen", action="store_true")
    p.add_argument("--grenze-mb", type=int, default=30000)
    p.add_argument("--vorlauf-h", type=int, default=VORLAUF_H)
    p.add_argument("--bis", type=dt.date.fromisoformat, default=None,
                   help="letzter Abend (Default: gestern)")
    a = p.parse_args()
    if a.holen:
        holen(a.grenze_mb, a.vorlauf_h, a.bis)
        return
    with open(os.path.join(BASIS, "konfig.json")) as f:
        s_stern = json.load(f)["schwelle_score"]
    auswerten(s_stern)


if __name__ == "__main__":
    main()
