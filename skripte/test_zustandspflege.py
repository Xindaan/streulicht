"""T-0058: die Zustandsdatei waechst nicht unbegrenzt und verliert nichts.

ZWEI Probleme, die nach aussen gleich aussehen und verschiedene Mittel
brauchen:

  * WACHSTUM.  Jeder vergangene Abend blieb liegen, mit `feld` und einer
    Verlaufszeile je Lauf.  Gemessen 23.08.2026: 156 kB nach neun Tagen,
    hochgerechnet rund 6 MB im Jahr - und `bisher.py`/`bewertungsseite.py`
    lesen bei JEDEM Seitenbau alles, also alle zehn Minuten.
  * VERLORENE SCHREIBVORGAENGE.  Drei Agenten lesen die Datei, aendern ihren
    Ausschnitt und schreiben alles zurueck.  Ueberlappen zwei, gewinnt der
    langsamere.  Der atomare Schreibvorgang aus T-0051 hilft hier NICHT: er
    verhindert halbe Dateien, nicht das Dazwischenkommen.

Lauf:  python3 skripte/test_zustandspflege.py
"""
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import alarm  # noqa: E402
from zustandsdatei import aktualisiere, lade, schreibe  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


HEUTE = dt.date.today()


def tag(minus):
    return str(HEUTE - dt.timedelta(days=minus))


print("T-0058  Wachstum und verlorene Schreibvorgaenge\n")

print("1. Raeumung: alt und unbewertet faellt weg, bewertet bleibt")
eintrag = {"abende": {
    tag(1):   {"p": 0.2},                        # frisch
    tag(29):  {"p": 0.2},                        # knapp innerhalb
    tag(31):  {"p": 0.2},                        # alt, unbewertet
    tag(400): {"p": 0.2},                        # sehr alt, unbewertet
    tag(365): {"p": 0.2, "bewertung": 4},        # alt, ABER bewertet
    tag(500): {"p": 0.2, "bewertung": 0},        # Note 0 ist eine Antwort
    "kaputt": {"p": 0.2},                        # unlesbarer Schluessel
}, "alarme": {}}
n = alarm.raeume(eintrag, HEUTE)
uebrig = set(eintrag["abende"])
pruefe(n == 2, "zwei Abende geraeumt (%d)" % n)
pruefe(tag(1) in uebrig and tag(29) in uebrig,
       "frische Abende bleiben")
pruefe(tag(31) not in uebrig and tag(400) not in uebrig,
       "alte unbewertete sind weg")
pruefe(tag(365) in uebrig, "ein bewerteter Abend bleibt, egal wie alt")
pruefe(tag(500) in uebrig,
       "Note 0 (\"nicht gesehen\") ist eine Antwort und schuetzt auch")
pruefe("kaputt" in uebrig,
       "ein unlesbarer Schluessel wird nicht angefasst statt zu crashen")

print("\n2. Die Grenzen sind benannt, nicht verstreut")
pruefe(alarm.BEHALTEN_TAGE >= 14,
       "BEHALTEN_TAGE deckt mehr als eine Nachbewertungsfrist (%d)"
       % alarm.BEHALTEN_TAGE)
pruefe(alarm.VERLAUF_MAX >= 5,
       "VERLAUF_MAX laesst genug Vorlaufstufen stehen (%d)" % alarm.VERLAUF_MAX)

print("\n3. Verlorene Schreibvorgaenge - der Fall, der eine Note gekostet hat")
# Nachgestellt wird der ECHTE Ablauf: Agent A liest, rechnet lange, Agent B
# schreibt in der Zwischenzeit eine Note, A schreibt danach seinen Stand.
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "zustand.json")
    schreibe(p, {"berlin": {"abende": {tag(1): {"p": 0.1}}, "alarme": {}}})

    naiv = lade(p)                       # A liest (der alte Weg)
    b = lade(p)                          # B liest
    b["berlin"]["abende"][tag(1)]["bewertung"] = 4
    schreibe(p, b)                       # B schreibt die Note
    naiv["berlin"]["abende"][tag(1)]["p"] = 0.9
    schreibe(p, naiv)                    # A schreibt seinen alten Stand
    e = lade(p)["berlin"]["abende"][tag(1)]
    pruefe("bewertung" not in e,
           "NEGATIVPROBE: der alte Weg verliert die Note (%s)" % sorted(e))

with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "zustand.json")
    schreibe(p, {"berlin": {"abende": {tag(1): {"p": 0.1}}, "alarme": {}}})

    lade(p)                              # A liest und rechnet lange ...
    b = lade(p)                          # B kommt dazwischen
    b["berlin"]["abende"][tag(1)]["bewertung"] = 4
    schreibe(p, b)

    def a_merged(z):                     # ... und mergt gegen den FRISCHEN Stand
        z["berlin"]["abende"][tag(1)]["p"] = 0.9
    aktualisiere(p, a_merged)
    e = lade(p)["berlin"]["abende"][tag(1)]
    pruefe(e.get("bewertung") == 4, "mit Merge ueberlebt die Note")
    pruefe(e.get("p") == 0.9, "und der neue Prognosewert steht auch drin")

print("\n4. Der echte Alarmlauf bewahrt eine dazwischengekommene Note")
# Kein nachgebauter Ablauf mehr, sondern alarm.main() mit gestubbtem Abruf.
import test_abruf  # noqa: E402

with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, "daten"), exist_ok=True)
    zp = os.path.join(d, "daten", "zustand.json")
    kfg = json.load(open(os.path.join(BASIS, "konfig.json")))
    kfg["schwelle_wahrscheinlichkeit"] = 2.0        # kein Push noetig
    kp = os.path.join(d, "konfig.json")
    with open(kp, "w") as f:
        json.dump(kfg, f)
    name = kfg["orte"][0]["name"]
    heute = str(HEUTE)
    # Alter Ballast, den der Lauf raeumen SOLL bzw. behalten muss.  Ohne das
    # hier prueft nichts, ob raeume() im Lauf ueberhaupt gerufen wird - die
    # erste Fassung dieses Tests pruefte die Funktion isoliert und blieb
    # gruen, als ich den Aufruf entfernte.
    schreibe(zp, {name: {"abende": {
        tag(90): {"p": 0.3, "feld": list(range(30))},
        tag(120): {"p": 0.3, "bewertung": 5},
    }, "alarme": {}}})

    # Waehrend der Lauf rechnet, traegt der Poller eine Note fuer HEUTE ein.
    echt_lauf_ort = alarm.lauf_ort

    def lauf_ort_mit_stoerung(*a_, **k_):
        erg = echt_lauf_ort(*a_, **k_)
        def stoerung(z):
            ab = z.setdefault(name, {"abende": {}, "alarme": {}})["abende"]
            ab.setdefault(heute, {})["bewertung"] = 4
            ab[heute]["bewertung_zeit"] = "2026-08-23T19:00:00Z"
        aktualisiere(zp, stoerung)
        return erg

    alt = (alarm.BASIS, alarm.abfrage, alarm.modelllauf, alarm.warte_auf_netz,
           alarm.lauf_ort)
    alarm.BASIS = d
    alarm.abfrage = test_abruf.falscher_abruf
    alarm.modelllauf = lambda m: "2026-01-01T00:00+00:00"
    alarm.warte_auf_netz = lambda *a_, **k_: None
    alarm.lauf_ort = lauf_ort_mit_stoerung
    sicher, sys.argv = sys.argv, ["alarm.py", "--konfig", kp]
    try:
        alarm.main()
    finally:
        sys.argv = sicher
        (alarm.BASIS, alarm.abfrage, alarm.modelllauf, alarm.warte_auf_netz,
         alarm.lauf_ort) = alt

    z = lade(zp)
    e = z[name]["abende"].get(heute, {})
    pruefe(e.get("bewertung") == 4,
           "die waehrend des Laufs eingetragene Note steht noch da (%s)"
           % e.get("bewertung"))
    pruefe(e.get("p") is not None,
           "und der Lauf hat seine eigene Rechnung trotzdem geschrieben")
    pruefe(bool(z[name].get("laeufe")), "der Lauf ist gebucht")
    pruefe(tag(90) not in z[name]["abende"],
           "der Lauf hat den alten unbewerteten Abend geraeumt")
    pruefe(tag(120) in z[name]["abende"],
           "und den alten BEWERTETEN behalten")

print("\n5. Der Verlauf waechst nicht ueber die Grenze")
with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, "daten"), exist_ok=True)
    zp = os.path.join(d, "daten", "zustand.json")
    kfg = json.load(open(os.path.join(BASIS, "konfig.json")))
    kfg["schwelle_wahrscheinlichkeit"] = 2.0
    kp = os.path.join(d, "konfig.json")
    with open(kp, "w") as f:
        json.dump(kfg, f)
    name = kfg["orte"][0]["name"]
    schreibe(zp, {name: {"abende": {}, "alarme": {}}})

    alt = (alarm.BASIS, alarm.abfrage, alarm.modelllauf, alarm.warte_auf_netz)
    alarm.BASIS = d
    alarm.abfrage = test_abruf.falscher_abruf
    alarm.modelllauf = lambda m: "2026-01-01T00:00+00:00"
    alarm.warte_auf_netz = lambda *a_, **k_: None
    sicher, sys.argv = sys.argv, ["alarm.py", "--konfig", kp]
    try:
        for _ in range(alarm.VERLAUF_MAX + 4):     # mehr Laeufe als erlaubt
            alarm.main()
    finally:
        sys.argv = sicher
        (alarm.BASIS, alarm.abfrage, alarm.modelllauf,
         alarm.warte_auf_netz) = alt

    laengen = [len(e.get("verlauf") or [])
               for e in lade(zp)[name]["abende"].values()]
    pruefe(laengen and max(laengen) <= alarm.VERLAUF_MAX,
           "kein Verlauf laenger als %d (laengster: %d)"
           % (alarm.VERLAUF_MAX, max(laengen or [0])))
    pruefe(max(laengen or [0]) == alarm.VERLAUF_MAX,
           "und die Grenze wird auch wirklich erreicht (sonst prueft das nichts)")

print("\n6. Die Sperre ist echt: ein zweiter Prozess wartet")
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "zustand.json")
    schreibe(p, {"n": 0})
    # 12 Prozesse erhoehen denselben Zaehler.  Ohne Sperre gehen Erhoehungen
    # verloren (klassisches lost update); mit Sperre kommen exakt 12 an.
    kind = (
        "import sys, time\n"
        "sys.path.insert(0, %r)\n"
        "from zustandsdatei import aktualisiere\n"
        "def f(z):\n"
        "    n = z['n']\n"
        "    time.sleep(0.02)\n"        # Fenster fuer die Kollision
        "    z['n'] = n + 1\n"
        "aktualisiere(%r, f)\n" % (os.path.join(BASIS, "skripte"), p))
    kinder = [subprocess.Popen([sys.executable, "-c", kind])
              for _ in range(12)]
    for k in kinder:
        k.wait()
    pruefe(lade(p)["n"] == 12,
           "12 parallele Erhoehungen, %d angekommen" % lade(p)["n"])

print()
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
