"""Regressionstest fuer sonnen/grib2.py.

Beide geprueften Fehler waren an der Wolkenmaske UNSICHTBAR und fielen erst
am Oberkantenprodukt auf. Genau deshalb stehen sie hier: ein Test, der nur
mit der Maske laeuft, haette beide durchgelassen.

Lauf:  python3 skripte/test_grib2.py
"""
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen.grib2 import felder, vorzeichen_betrag, werte  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fehler = []


def pruefe(b, text):
    print("   %s  %s" % ("ok  " if b else "FEHL", text))
    if not b:
        fehler.append(text)


print("=== 1. Vorzeichen-Betrag, nicht Zweierkomplement")
pruefe(vorzeichen_betrag(b"\x80\x01") == -1,
       "0x8001 -> -1 (Zweierkomplement gaebe -32767)")
pruefe(vorzeichen_betrag(b"\x00\x05") == 5, "0x0005 -> 5")
pruefe(vorzeichen_betrag(b"\x80\x00") == 0, "0x8000 -> 0 (negative Null)")
pruefe(vorzeichen_betrag(b"\xff\xff") == -32767, "0xffff -> -32767")
pruefe(vorzeichen_betrag(b"\x00\x00") == 0,
       "0x0000 -> 0 (der Fall, der den Fehler versteckt hat)")

print()
print("=== 2. Echte Produkte, wenn sie im Cache liegen")
c = os.path.join(BASIS, "daten", "satellit")
cth = sorted(x for x in os.listdir(c) if "MSGCLTH" in x) if os.path.isdir(c) else []
clm = sorted(x for x in os.listdir(c) if "MSGCLMK" in x) if os.path.isdir(c) else []

if cth:
    z = zipfile.ZipFile(os.path.join(c, cth[0]))
    d = z.read([n for n in z.namelist() if n.endswith(".grb")][0])
    fs = felder(d)
    pruefe(len(fs) == 2,
           "Oberkante: %d Felder erkannt (wiederholte Sektionen 4-7)" % len(fs))
    f0, gp, _ = werte(d, 0)
    gut = f0[f0 == f0]
    pruefe(300 < gut.min() and gut.max() < 20000,
           "Feld 0 in Metern: %.0f .. %.0f" % (gut.min(), gut.max()))
    pruefe(gut.size < f0.size,
           "Bitmap greift: %d von %d Punkten belegt" % (gut.size, f0.size))
    f1, _, _ = werte(d, 1)
    g1 = f1[f1 == f1]
    pruefe(g1.max() <= 1,
           "Feld 1 ist ein Flag (Bitmap 254 aufgeloest), Max %.0f" % g1.max())
else:
    print("   uebersprungen: kein CTH im Cache")

if clm:
    z = zipfile.ZipFile(os.path.join(c, clm[0]))
    d = z.read([n for n in z.namelist() if n.endswith(".grb")][0])
    f, gp, _ = werte(d, 0)
    pruefe(len(felder(d)) == 1, "Maske: genau ein Feld")
    pruefe(set(int(x) for x in set(f.tolist())) <= {0, 1, 2, 3},
           "Maske hat nur die Klassen 0-3")
    pruefe(gp["nx"] == 3712 and abs(gp["xp"] - 1856.0) < 1e-9,
           "Maskengitter 3712, Subsatellitenpunkt in der Mitte")
else:
    print("   uebersprungen: keine Maske im Cache")

print()
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    sys.exit(1)
print("alle Pruefungen bestanden")
