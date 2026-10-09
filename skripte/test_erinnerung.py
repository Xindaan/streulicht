"""Das Aufforderungsfenster - und das Nachholen danach (T-0067).

WARUM DAS EINEN TEST BRAUCHT.  Die Bewertungen sind die einzige Messgroesse
des Projekts, die sich nicht nachproduzieren laesst: fuer einen Abend ohne
Note gibt es keinen zweiten Abruf und keine zweite Quelle.  Das Fenster ist
75 Minuten breit, der Agent tickt stuendlich - schlaeft der Rechner darueber
hinweg, faellt der ganze Abend aus.  Seit dem 02.09.2026 wird bis zum
lokalen Mitternacht nachgeholt.

Die Grenze ist der Punkt: nachgeholt wird der HEUTIGE lokale Abend, nie der
von gestern.  Nach Mitternacht bewertet niemand mehr den vorletzten
Sonnenuntergang, und die Frage waere dann irrefuehrend statt hilfreich.

Kein Netz, kein Zugriff auf Betriebsdaten: eigenes Temp-Verzeichnis, eigener
Zustand, `sende` durch eine Attrappe ersetzt.

Lauf:  .venv/bin/python3 skripte/test_erinnerung.py
"""
import json
import os
import sys
import tempfile

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import erinnerung  # noqa: E402
from zustandsdatei import lade, schreibe  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


# Berlin, 02.09.2026: Sonnenuntergang 17:52 UTC (19:52 Ortszeit).
# Fenster: Start 18:22 UTC, Ende 19:37 UTC.
GESENDET = []


def falscher_versand(topic, titel, text, klick=None):
    GESENDET.append({"topic": topic, "titel": titel, "klick": klick})


def lauf(jetzt_iso, vorzustand=None):
    """Einen Erinnerungslauf fahren.  Rueckgabe: (Zahl Sendungen, Zustand)."""
    GESENDET.clear()
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "daten"), exist_ok=True)
    kfg = json.load(open(os.path.join(BASIS, "konfig.json")))
    kp = os.path.join(d, "konfig.json")
    with open(kp, "w") as f:
        json.dump(kfg, f)
    zp = os.path.join(d, "daten", "zustand.json")
    schreibe(zp, vorzustand or {})

    alt_basis, alt_sende = erinnerung.BASIS, erinnerung.sende
    erinnerung.BASIS = d
    erinnerung.sende = falscher_versand
    sicher, sys.argv = sys.argv, ["erinnerung.py", "--konfig", kp,
                                  "--jetzt", jetzt_iso]
    try:
        erinnerung.main()
    finally:
        sys.argv = sicher
        erinnerung.BASIS, erinnerung.sende = alt_basis, alt_sende
    return len(GESENDET), lade(zp)


print("1. Im Fenster wird gefragt (unveraendert)")
n, z = lauf("2026-09-02T18:40")
pruefe(n == 1, "eine Aufforderung im Fenster (%d)" % n)
pruefe("2026-09-02" in (z.get("berlin") or {}).get("erinnerungen", {}),
       "und sie ist fuer den 02.09. gebucht")

print("\n2. Vor dem Fenster wird nicht gefragt")
n, _ = lauf("2026-09-02T16:00")
pruefe(n == 0, "nichts vor Sonnenuntergang (%d)" % n)

print("\n3. NACH dem Fenster wird nachgeholt - solange es lokal derselbe Tag ist")
# 21:30 UTC = 23:30 Ortszeit, also fast vier Stunden nach Fensterende und
# eine halbe Stunde vor dem lokalen Tageswechsel.  Genau der Fall, der
# bis zum 02.09.2026 ersatzlos ausfiel.
n, z = lauf("2026-09-02T21:30")
pruefe(n == 1, "eine nachgeholte Aufforderung (%d)" % n)
pruefe("2026-09-02" in (z.get("berlin") or {}).get("erinnerungen", {}),
       "und zwar fuer den HEUTIGEN Abend, nicht fuer gestern")

print("\n4. Nach lokalem Mitternacht wird NICHT mehr nachgeholt")
# 22:30 UTC = 00:30 Ortszeit des 03.09.  Der Abend des 02.09. ist damit
# vorbei; eine Frage danach waere irrefuehrend.  Zugleich liegt der
# Sonnenuntergang des 03.09. noch 17 Stunden in der Zukunft.
n, z = lauf("2026-09-02T22:30")
pruefe(n == 0, "keine Aufforderung nach Mitternacht (%d)" % n)

print("\n5. Idempotenz: der naechste Tick fragt nicht noch einmal")
vor = {"berlin": {"abende": {}, "alarme": {},
                  "erinnerungen": {"2026-09-02": "2026-09-02T18:40:00+00:00"}}}
n, _ = lauf("2026-09-02T21:30", vor)
pruefe(n == 0, "schon gefragt, also Ruhe (%d)" % n)

print("\n6. Der Winterabend wird genauso nachgeholt")
# 21.12.2026, Sonnenuntergang 14:53 UTC.  Fensterende 16:38 UTC; 22:00 UTC
# ist 23:00 Ortszeit, also noch derselbe lokale Tag.  Eine feste Uhrzeit
# haette hier entweder im Sommer oder im Winter danebengelegen.
n, z = lauf("2026-12-21T22:00")
pruefe(n == 1, "auch im Dezember nachgeholt (%d)" % n)
pruefe("2026-12-21" in (z.get("berlin") or {}).get("erinnerungen", {}),
       "und fuer den richtigen Abend gebucht")

print("")
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
