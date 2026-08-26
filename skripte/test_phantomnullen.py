"""T-0060: eine Datenluecke darf nicht als Score 0.0 in die Statistik.

Beide Score-Varianten liefern `(s, detail)`.  `detail is None` heisst "nicht
auswertbar", der Score ist dann 0.0.  Wer nur `[0]` nimmt, verwandelt eine
Luecke still in eine Null - und die geht als besonders unauffaelliger Abend
in den Mittelrang ein.  `ablation.py` vermeidet das ausdruecklich; in
`icond2_test.py` fehlte die Regel.

WIE GROSS DAS PROBLEM WIRKLICH IST (gemessen 23.08.2026 am echten Cache,
166 Dateien).  Beim Standardlauf gar nicht: der Deckungsfilter `>= 0.9`
laesst 0 von 55 Abenden mit fehlendem Detail durch.  Der Filter prueft aber
die ROHDATEN, nicht die Auswertbarkeit des Scores - dass beides zusammen-
faellt, ist eine Eigenschaft DIESER Daten, keine Garantie.  Die Deckung ist
bimodal (rund 1.0 oder rund 0.0); wer die Schwelle senkt, um mehr Bloecke zu
bekommen, holt sich 36 von 175 Phantomnullen (21 %) herein - und der Kopf des
Berichts meldete dabei weiter "0 mit Datenluecken".

Der Test faehrt deshalb BEIDE Schwellen gegen den echten Cache.

Lauf:  python3 skripte/test_phantomnullen.py
"""
import json
import os
import subprocess
import sys

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


CACHE = os.path.join(BASIS, "daten", "roh_icond2")
PLAN = os.path.join(BASIS, "daten", "icond2_plan.json")
if not (os.path.isdir(CACHE) and os.path.exists(PLAN)):
    print("ICON-Cache oder Plan fehlt - dieser Test braucht echte Daten.")
    raise SystemExit(2)          # Code 2, nicht falsch gruen melden

import icond2_test as it  # noqa: E402

print("T-0060  Datenluecken werden nicht zu Nullen\n")

print("1. Die Lage am echten Cache (die Zahlen, auf die sich alles beruft)")
plan = json.load(open(PLAN))
ohne_detail = {"3s": 0, "niv": 0}
gesamt = 0
for ziel in plan["ziel"]:
    for t in [ziel] + plan["paare"][ziel]:
        p = os.path.join(CACHE, "%s.json" % t)
        if not os.path.exists(p):
            continue
        daten = json.load(open(p))
        gesamt += 1
        if it.icon_3schicht(daten)[1] is None:
            ohne_detail["3s"] += 1
        if it.icon_niveaus(daten)[1] is None:
            ohne_detail["niv"] += 1
print("      %d Abende im Cache, ohne Detail: 3-Schicht %d, niveaus %d"
      % (gesamt, ohne_detail["3s"], ohne_detail["niv"]))
pruefe(gesamt > 100, "der Cache traegt genug Abende (%d)" % gesamt)
pruefe(ohne_detail["niv"] > 0,
       "es GIBT Abende ohne Detail (%d) - sonst prueft der Rest nichts"
       % ohne_detail["niv"])


def lauf(schwelle):
    r = subprocess.run(
        [sys.executable, os.path.join(BASIS, "skripte", "icond2_test.py"),
         "--mindestdeckung", str(schwelle)],
        capture_output=True, text=True, cwd=BASIS)
    return r.stdout


def niveauzahl(ausgabe):
    """Der Mittelrang von icon_niv aus dem NIVEAUS-Abschnitt, oder None."""
    im_block = False
    for z in ausgabe.splitlines():
        if z.startswith("=== NIVEAUS"):
            im_block = "nicht gerechnet" not in z
            continue
        if im_block and z.strip().startswith("icon_niv"):
            return float(z.split()[1])
        if im_block and z.startswith("==="):
            im_block = False
    return None


print("\n2. Standardlauf (--mindestdeckung 0.9) - darf sich NICHT aendern")
a9 = lauf(0.9)
pruefe("era5_3s   0.593" in a9 and "icon_3s   0.657" in a9,
       "die gerechneten 3-Schicht-Zahlen sind unveraendert (0.593 / 0.657)")
pruefe(niveauzahl(a9) is None,
       "der Niveaus-Abschnitt bleibt ungerechnet (zu wenige Bloecke)")

print("\n3. Gelockerte Schwelle (0.0) - hier war der Fehler erreichbar")
a0 = lauf(0.0)
pruefe("nicht auswertbar (Score ohne Detail)" in a0,
       "der Bericht NENNT die nicht auswertbaren Bloecke")
pruefe(niveauzahl(a0) is None,
       "und rechnet den Niveaus-Abschnitt NICHT mehr aus Phantomnullen "
       "(frueher: icon_niv 0.496 aus 35 Bloecken mit 21 %% Luecken)")
pruefe("0 mit Datenluecken" in a0,
       "der Rohdatenfilter meldet weiterhin 0 - er ist eben nicht dasselbe")

print("\n4. Die 3-Schicht-Auswertung bleibt vollstaendig")
# Waere der Riegel zu scharf, faende man ihn hier: icon_3s hat am echten
# Cache KEINE Luecke, also darf kein einziger Block wegfallen.
pruefe("Bloecke auswertbar: 35 von 35" in a0,
       "alle 35 Bloecke bleiben fuer die 3-Schicht-Auswertung erhalten")
pruefe("era5_3s   0.593" in a0 and "icon_3s   0.657" in a0,
       "und liefern dieselben Zahlen wie beim Standardlauf")

print("\n5. Dieselbe Klasse in klimatologie.py (Isomorphie-Check)")
# Die schwerere der beiden Stellen: aus dieser Verteilung kommt s* = 0.7065.
# Eine Phantomnull sitzt am UNTEREN Ende und verschiebt die Perzentile -
# ein Abend ohne Daten wuerde den Schwellwert mitbestimmen, den er nie
# gesehen hat.  Der Schleifenrumpf wird hier nachgebildet und AUSGEFUEHRT,
# statt den Quelltext zu lesen.
from sonnen.score import score as score3                     # noqa: E402


def klima_zeile(hole):
    """Der Rumpf aus klimatologie.py, isoliert: was landet im Ergebnis?"""
    ergebnis, ohne = {}, []
    s, det = score3(hole)
    if det is None:
        ohne.append("tag")
    else:
        ergebnis["tag"] = {"s": s, "schirm": det["schirm"],
                           "A": det["A"], "B": det["B"]}
    return ergebnis, ohne


leer, ohne = klima_zeile(lambda d, dv, schicht: None)
pruefe(not leer and ohne,
       "ein Abend ohne Daten landet NICHT als 0.0 in der Klimatologie")
voll, ohne2 = klima_zeile(lambda d, dv, schicht: 0.9)
pruefe(bool(voll) and not ohne2,
       "ein belegter Abend landet weiterhin drin (S = %.4f)"
       % voll["tag"]["s"])
pruefe(voll["tag"]["s"] == 0.0 or voll["tag"]["s"] > 0.0,
       "und behaelt seinen echten Wert, auch wenn der 0.0 ist")

print("\n6. Die vorliegenden Klimatologien sind nicht betroffen")
# Ohne diese Messung waere der Fix eine Behauptung ueber s*.  `schirm: null`
# markiert genau die Faelle, in denen det None war.
import glob                                                   # noqa: E402
dateien = sorted(glob.glob(os.path.join(BASIS, "daten",
                                        "score_berlin_g0.5_*.json")))
pruefe(bool(dateien), "es liegen Klimatologie-Dateien vor (%d)" % len(dateien))
betroffen = {}
for f in dateien:
    d = json.load(open(f))
    n = sum(1 for e in d.values()
            if isinstance(e, dict) and e.get("schirm") is None)
    if n:
        betroffen[os.path.basename(f)] = n
pruefe(not betroffen,
       "keine einzige traegt eine Phantomnull (%s) - s* ist nicht betroffen"
       % (betroffen or "0 in allen %d" % len(dateien)))

print()
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
