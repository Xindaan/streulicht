"""Tagessicherung der Zustandsdatei (T-0081, betrieb#6).

WARUM DAS EINEN TEST BRAUCHT.  Die Noten sind die einzige Messgroesse des
Projekts, die sich nicht nachproduzieren laesst; die Sicherung ist der einzige
Schutz davor, dass eine kaputte Zustandsdatei, ein Plattenfehler oder ein
Loeschen sie mitnimmt.  Eine Sicherung, die bei genau diesem Fall die letzte
gute Kopie ueberschreibt, ist schlimmer als keine - sie wiegt in Sicherheit.

Geprueft wird, was die Sicherung TUT (echte Dateien in einem Temp-Verzeichnis,
kein Netz, keine Betriebsdaten), je Waechter einzeln:
  * ungueltiges JSON wird nicht kopiert,
  * die Kopie ist atomar (Fehler beim Tausch hinterlaesst nichts Halbes),
  * nur 14 Tageskopien, und nur solche, die dem Namensmuster entsprechen,
  * der Zusatzordner legt nie einen neuen Verzeichnisbaum an,
  * ein Fehler an einem Ziel verhindert das andere nicht.

Lauf:  .venv/bin/python3 skripte/test_sicherung.py
"""
import json
import os
import shutil
import sys
import tempfile
from datetime import date, timedelta

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import sicherung  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


def dateien(ordner):
    return sorted(os.listdir(ordner)) if os.path.isdir(ordner) else None


def schreibe(pfad, inhalt):
    with open(pfad, "w") as f:
        f.write(inhalt)


d = tempfile.mkdtemp()
try:
    zp = os.path.join(d, "zustand.json")
    lokal = os.path.join(d, "sicherung")
    tag = date(2026, 10, 9)
    noten1 = json.dumps({"berlin": {"abende": {"2026-10-06": {"note": 3}}}})

    print("1. Eine Tageskopie, mit dem Inhalt der Zustandsdatei")
    schreibe(zp, noten1)
    f = sicherung.sichere(zp, lokal, heute=tag)
    pruefe(f == [], "keine Fehler (%s)" % f)
    pruefe(dateien(lokal) == ["zustand-2026-10-09.json"],
           "Name zustand-JJJJ-MM-TT.json (%s)" % dateien(lokal))
    pruefe(open(os.path.join(lokal, "zustand-2026-10-09.json")).read()
           == noten1, "Inhalt byteidentisch")

    print("\n2. Gleicher Tag, neue Note: die Tageskopie traegt den letzten Stand")
    noten2 = json.dumps({"berlin": {"abende": {"2026-10-06": {"note": 3},
                                               "2026-10-09": {"note": 4}}}})
    schreibe(zp, noten2)
    sicherung.sichere(zp, lokal, heute=tag)
    pruefe(dateien(lokal) == ["zustand-2026-10-09.json"]
           and open(os.path.join(lokal, "zustand-2026-10-09.json")).read()
           == noten2, "eine Datei, mit dem neuen Stand")

    print("\n3. Naechster Tag: neue Datei, die alte bleibt")
    sicherung.sichere(zp, lokal, heute=tag + timedelta(days=1))
    pruefe(dateien(lokal) == ["zustand-2026-10-09.json",
                              "zustand-2026-10-10.json"],
           "zwei Tageskopien (%s)" % dateien(lokal))

    print("\n4. Waechter: ungueltiges JSON ueberschreibt die gute Kopie nicht")
    gut = open(os.path.join(lokal, "zustand-2026-10-10.json")).read()
    for muell, name in (("", "leere Datei"), ('{"berlin": {"abende"', "abgeschnitten")):
        schreibe(zp, muell)
        f = sicherung.sichere(zp, lokal, heute=tag + timedelta(days=1))
        pruefe(len(f) == 1 and "ungueltig" in f[0],
               "%s: wird gemeldet (%s)" % (name, f))
        pruefe(open(os.path.join(lokal, "zustand-2026-10-10.json")).read()
               == gut, "%s: die letzte gute Kopie bleibt unveraendert" % name)
    os.unlink(zp)
    f = sicherung.sichere(zp, lokal, heute=tag)
    pruefe(len(f) == 1 and "fehlt" in f[0],
           "fehlende Zustandsdatei wird gemeldet (%s)" % f)

    print("\n5. Waechter: atomar - scheitert der Tausch, bleibt nichts Halbes")
    schreibe(zp, noten2)
    ziel = os.path.join(lokal, "zustand-2026-10-10.json")
    vorher = open(ziel).read()
    echt = os.replace

    def kaputt(*a, **k):
        raise OSError("Platte voll (Test)")

    schreibe(zp, json.dumps({"berlin": {"neu": 1}}))      # anderer Inhalt
    os.replace = kaputt
    try:
        f = sicherung.sichere(zp, lokal, heute=tag + timedelta(days=1))
    finally:
        os.replace = echt
    pruefe(len(f) == 1 and "fehlgeschlagen" in f[0],
           "Fehler wird gemeldet, nicht geworfen (%s)" % f)
    pruefe(open(ziel).read() == vorher,
           "die bisherige Tageskopie ist unberuehrt")
    pruefe(not [n for n in os.listdir(lokal) if n.endswith(".tmp")],
           "und es bleibt keine Temp-Datei liegen (%s)" % dateien(lokal))
    schreibe(zp, noten2)

    print("\n6. Waechter: nur 14 Tageskopien, nur nach Namensmuster")
    voll = os.path.join(d, "voll")
    os.makedirs(voll)
    schreibe(os.path.join(voll, "notizen.txt"), "gehoert mir")
    schreibe(os.path.join(voll, "zustand-alt.json"), "{}")
    schreibe(os.path.join(voll, "zustand-2026-13-45.json"), "{}")
    for i in range(30):
        sicherung.sichere(zp, voll, heute=date(2026, 9, 1) + timedelta(days=i))
    kopien = [n for n in os.listdir(voll) if sicherung.MUSTER.match(n)
              and n != "zustand-2026-13-45.json"]
    pruefe(len(kopien) == 14, "nach 30 Tagen genau 14 Kopien (%d)" % len(kopien))
    pruefe(min(kopien) == "zustand-2026-09-17.json"
           and max(kopien) == "zustand-2026-09-30.json",
           "die letzten 14 Tage: %s ... %s" % (min(kopien), max(kopien)))
    pruefe({"notizen.txt", "zustand-alt.json", "zustand-2026-13-45.json"}
           <= set(os.listdir(voll)),
           "Fremdes im Ordner (anderer Name, unmoegliches Datum) bleibt")

    print("\n7. Zusatzordner (z. B. iCloud)")
    zusatz = os.path.join(d, "icloud", "streulicht")
    os.makedirs(os.path.dirname(zusatz))
    f = sicherung.sichere(zp, lokal, zusatz, heute=tag)
    pruefe(f == [] and dateien(zusatz) == ["zustand-2026-10-09.json"]
           and open(os.path.join(zusatz, "zustand-2026-10-09.json")).read()
           == noten2, "zusaetzlich dort, byteidentisch (%s)" % f)
    # Waechter: Eltern fehlen (Laufwerk nicht eingehaengt, Tippfehler)
    fehlt = os.path.join(d, "nicht_da", "tief", "streulicht")
    f = sicherung.sichere(zp, lokal, fehlt, heute=tag)
    pruefe(len(f) == 1 and "nicht_da" in f[0], "wird gemeldet (%s)" % f)
    pruefe(not os.path.exists(os.path.join(d, "nicht_da")),
           "und legt KEINEN neuen Verzeichnisbaum an")
    # Unabhaengigkeit: lokal kaputt -> Zusatz bekommt trotzdem seine Kopie
    kaputt_lokal = os.path.join(d, "datei_statt_ordner")
    schreibe(kaputt_lokal, "ich bin eine Datei")
    zusatz2 = os.path.join(d, "icloud", "zwei")
    f = sicherung.sichere(zp, kaputt_lokal, zusatz2, heute=tag)
    pruefe(len(f) == 1 and dateien(zusatz2) == ["zustand-2026-10-09.json"],
           "lokales Ziel kaputt: Fehler gemeldet, Zusatz trotzdem gesichert")
    # ... und umgekehrt
    f = sicherung.sichere(zp, os.path.join(d, "lokal2"), fehlt, heute=tag)
    pruefe(len(f) == 1 and dateien(os.path.join(d, "lokal2"))
           == ["zustand-2026-10-09.json"],
           "Zusatz kaputt: Fehler gemeldet, lokal trotzdem gesichert")

    print("\n8. Konfigschluessel sicherung_ordner")
    kp = os.path.join(d, "konfig.json")
    schreibe(kp, json.dumps({"orte": []}))
    pruefe(sicherung.aus_konfig(kp) is None, "nicht gesetzt: None")
    schreibe(kp, json.dumps({"sicherung_ordner": "~/x/streulicht"}))
    pruefe(sicherung.aus_konfig(kp) == os.path.expanduser("~/x/streulicht"),
           "gesetzt: Pfad mit aufgeloestem ~")
    schreibe(kp, "{kaputt")
    pruefe(sicherung.aus_konfig(kp) is None,
           "kaputte Konfig: None (die lokale Sicherung laeuft trotzdem)")
finally:
    shutil.rmtree(d, ignore_errors=True)

print("")
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
