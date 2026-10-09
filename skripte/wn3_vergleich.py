"""Weicht WeatherNext 3 ueberhaupt von ECMWF ab? - die billige Vorfrage.

WAS HIER NICHT BEANTWORTET WIRD.  Ob WN3 BESSER ist.  Das braucht Noten,
und davon gibt es am 08.09.2026 genau 14 - Bewertungsseite seit 15.08. -,
davon 11 mit Archivueberdeckung, und darunter eine einzige gute (Note 4).
Der Schwellwert s* entspricht rund 18,5 Ausloesungen im Jahr; mit elf
Abenden und einem Ereignis hat ein Guetevergleich keine Trennschaerfe.
Dieselbe Rechnung hat in Befund E1 schon die BSS-Kurve gekippt.  Wer hier
trotzdem "besser" herausliest, liest Rauschen.

WAS HIER BEANTWORTET WIRD.  Ob die beiden Modelle an unseren Faecherpunkten
UEBERHAUPT etwas Verschiedenes sagen.  Sagen sie dasselbe, eruebrigt sich
der ganze Betriebsumbau - dann ist WN3 ein anderer Weg zum selben Ergebnis.
Sagen sie Verschiedenes, ist das noch kein Argument fuer WN3, aber die
Voraussetzung dafuer, dass es eines geben kann.

FAIRNESS.  Beide bekommen denselben Score, denselben Faecher, denselben
Abend.  ECMWF steuert sein archiviertes MEDIANFELD bei (`feld` im Archiv),
WN3 sein p50-Feld - beide also "Score des Medianfeldes", nicht Median der
Memberscores.  Der WN3-Lauf wird so gewaehlt, wie er zum Abrufzeitpunkt des
Archivlaufs verfuegbar GEWESEN WAERE (7 h Verzug, gemessen).  Damit misst
der Vergleich das Produkt, nicht das Modell im Labor.

Ungleich bleibt die Aufloesung: ECMWF liegt bei uns auf 0,25 Grad, WN3 auf
0,1 Grad.  Beide werden an ihrem eigenen naechsten Gitterpunkt gelesen -
ein Teil jeder Abweichung ist also Aufloesung, nicht Modell.

Kostet nichts: das Statistik-Bucket ist nicht requester-pays.

Lauf:  .venv/bin/python3 skripte/wn3_vergleich.py
"""
import argparse
import datetime as dt
import glob
import importlib.util
import json
import os
import sys

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASIS)
sys.path.insert(0, os.path.join(BASIS, "skripte"))

from sonnen.score import score_fuer_abend                       # noqa: E402

_s = importlib.util.spec_from_file_location(
    "wn3", os.path.join(BASIS, "skripte", "wn3.py"))
wn3 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(wn3)

BREITE, LAENGE = 52.52, 13.405
# Raster des ARCHIVIERTEN Feldes - 0,5 Grad, nicht die 0,25 aus alarm.py.
# `feld_seite` wird dort mit `round(la_ / 0.5)` gebaut und ist nach den
# FAECHERPUNKTEN geschluesselt.  Der erste Entwurf hier nahm 0,25 und traf
# damit keinen einzigen Schluessel: elf Abende ergaben brav 0,0000, und das
# sah aus wie ein Ergebnis.  Daher unten der Fehlschlagzaehler.
GITTER = 0.5
VERZUG_H = 7                        # gemessener Verzug WN3: 6,5 bis 7,1 h


def bewertungen():
    z = json.load(open(os.path.join(BASIS, "daten", "zustand.json")))
    ab = z.get("berlin", {}).get("abende", {})
    return {t: v["bewertung"] for t, v in ab.items()
            if v.get("bewertung") is not None}


def archivabende():
    """Je Abend der FRISCHESTE archivierte Lauf, der ihn enthaelt.

    Frischer heisst: der Lauf desselben Tages, abends.  Nur der hat den
    kurzen Vorlauf, um den es im Betrieb geht.
    """
    aus = {}
    for pfad in sorted(glob.glob(os.path.join(
            BASIS, "daten", "archiv", "berlin", "*.json"))):
        d = json.load(open(pfad))
        tag = d["lauf"]
        if tag in d.get("abende", {}) and d["abende"][tag].get("feld"):
            # abends schlaegt morgens - spaeterer Lauf, kuerzerer Vorlauf
            if tag not in aus or d["fenster"] == "abends":
                aus[tag] = d
    return aus


def feld_ecmwf(archiv_abend, zaehler):
    """feld(lat, lon, schicht) aus dem archivierten Medianfeld.

    Das Archiv fuehrt Prozent als ganze Zahl je Zelle; `score()` will 0..1.
    `zaehler` zaehlt Treffer und Fehlschlaege - ein Nachschlagen, das
    durchgehend daneben greift, liefert einen Score von 0,0 und sieht damit
    aus wie eine Aussage.  Genau das ist im ersten Entwurf passiert.
    """
    zellen = archiv_abend["feld"]

    def hole(lat, lon, schicht):
        k = "%d/%d" % (round(lat / GITTER), round(lon / GITTER))
        e = zellen.get(k)
        if e is None:
            zaehler["daneben"] += 1
            return None
        zaehler["treffer"] += 1
        return e[schicht] / 100.0
    return hole


def feld_wn3(quelle, stunde_index, schichten=("low", "mid", "high")):
    """feld(lat, lon, schicht) aus den p50-Feldern - drei Chunks, einmal."""
    import numpy as np
    felder = {s: quelle.feld(s, "p50", stunde_index) for s in schichten}

    def hole(lat, lon, schicht):
        f = felder[schicht]
        i = wn3._index(quelle.lat01, lat)
        j = wn3._index(quelle.lon01, wn3._laenge(lon))
        v = float(f[i, j])
        return None if v != v else v          # WN3 fuehrt schon 0..1
    return hole


def wn3_lauf_vor(laeufe, zeitpunkt):
    """Juengster WN3-Lauf, der `zeitpunkt` bereits verfuegbar gewesen waere."""
    grenze = zeitpunkt - dt.timedelta(hours=VERZUG_H)
    passend = [l for l in laeufe
               if dt.datetime.strptime(l, "%Y%m%d_%Hhr").replace(
                   tzinfo=dt.timezone.utc) <= grenze]
    return passend[-1] if passend else None


def stat_laeufe():
    zeilen = wn3._lauf(["gcloud", "storage", "ls", wn3.STAT_BUCKET + "/"])
    return sorted(t.rstrip("/").rsplit("/", 1)[-1].replace("_01_preds", "")
                  for t in zeilen.splitlines() if t.endswith("_preds/"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--grenze-mb", type=int, default=wn3.STAT_BUDGET_MB)
    a = p.parse_args()

    noten = bewertungen()
    archiv = archivabende()
    tage = sorted(set(noten) & set(archiv))
    print("Bewertete Abende: %d, davon mit Archiv: %d" % (len(noten), len(tage)))
    if not tage:
        raise SystemExit("keine Ueberdeckung - nichts zu vergleichen")

    print("WN3-Laeufe auflisten ...")
    laeufe = stat_laeufe()
    print("   %d Laeufe, %s bis %s" % (len(laeufe), laeufe[0], laeufe[-1]))

    budget = wn3.Budget(frei=False, grenze_mb=a.grenze_mb)
    zaehler = {"treffer": 0, "daneben": 0}
    print("\n%-12s %4s %9s %9s %8s   %s"
          % ("Abend", "Note", "s_ECMWF", "s_WN3", "Diff", "WN3-Lauf"))
    print("-" * 66)
    zeilen = []
    for tag in tage:
        av = archiv[tag]["abende"][tag]
        geholt = dt.datetime.fromisoformat(archiv[tag]["geholt"])
        lauf = wn3_lauf_vor(laeufe, geholt)
        if lauf is None:
            print("%-12s %4s   kein WN3-Lauf so weit zurueck" % (tag, noten[tag]))
            continue
        d = dt.date.fromisoformat(tag)
        s_e, _ = score_fuer_abend(d, BREITE, LAENGE, feld_ecmwf(av, zaehler))

        q = wn3.Statistik(lauf, budget=budget)
        ziel_h = int(round(av["stunde_utc"]))
        ziel = dt.datetime(d.year, d.month, d.day, min(ziel_h, 23),
                           tzinfo=dt.timezone.utc)
        i = q.schritt(ziel)
        if i is None:
            print("%-12s %4s   Zielstunde ausserhalb des WN3-Vorlaufs"
                  % (tag, noten[tag]))
            continue
        s_w, _ = score_fuer_abend(d, BREITE, LAENGE, feld_wn3(q, i))

        print("%-12s %4d %9.4f %9.4f %8.4f   %s"
              % (tag, noten[tag], s_e, s_w, s_w - s_e, lauf))
        zeilen.append((tag, noten[tag], s_e, s_w))

    if len(zeilen) < 2:
        raise SystemExit("\nZu wenige Zeilen fuer eine Aussage.")

    gesamt = zaehler["treffer"] + zaehler["daneben"]
    if gesamt and zaehler["daneben"] > gesamt * 0.05:
        raise SystemExit(
            "\nABBRUCH: %d von %d Nachschlagen im ECMWF-Feld gingen daneben. "
            "Die Scores oben sind wertlos - vermutlich stimmt GITTER nicht "
            "mit dem Raster des Archivs ueberein."
            % (zaehler["daneben"], gesamt))

    import statistics as st
    se = [z[2] for z in zeilen]
    sw = [z[3] for z in zeilen]
    diff = [b - a_ for a_, b in zip(se, sw)]
    print("-" * 66)
    print("n = %d   mittlere Abweichung %+.4f   groesste %+.4f"
          % (len(zeilen), st.mean(diff), max(diff, key=abs)))
    if len(zeilen) > 2:
        try:
            r = st.correlation(se, sw)
            print("Korrelation der beiden Scorereihen: r = %.3f" % r)
        except st.StatisticsError:
            print("Korrelation nicht berechenbar (eine Reihe ist konstant)")
    print("Geholt: %.0f MB (kostenlos - das Bucket ist nicht requester-pays)"
          % (budget.bytes / 1048576.0))
    print("\nDies sagt NICHT, welches Modell besser ist. Dafuer fehlen die")
    print("Noten: 1 gute unter 11 Abenden traegt keine Aussage.")


if __name__ == "__main__":
    main()
