"""T-0051: die Zustandsdatei ueberlebt einen abgebrochenen Schreibvorgang.

Der Test RECHNET NICHT ueber den Quelltext, er bricht echte Schreibvorgaenge
in echten Kindprozessen mit SIGKILL ab und liest danach die Datei.  Grund:
genau diese Fehlerklasse - "der Test prueft, dass ich etwas hingeschrieben
habe, nicht dass es wirkt" - hat das Projekt schon einmal Runden gekostet.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zustandsdatei import schreibe  # noqa: E402

HIER = os.path.dirname(os.path.abspath(__file__))
_fehler = []


def ok(bedingung, text):
    print("   %s  %s" % ("ok  " if bedingung else "FEHLER", text))
    if not bedingung:
        _fehler.append(text)


# Ein Kindprozess, der genau so schreibt wie die Agenten - einmal naiv,
# einmal atomar - und sich mitten im Dump selbst umbringt.
KIND = r'''
import json, os, signal, sys
sys.path.insert(0, %r)
pfad, art = sys.argv[1], sys.argv[2]
gross = {"ort%%04d" %% i: {"abende": {"2026-08-%%02d" %% (i %% 28 + 1):
         {"feld": list(range(40)), "p": 0.5}}} for i in range(400)}

class Bombe:
    """Ein Datenobjekt, das mitten im json.dump den Prozess killt."""
    def __init__(self, n): self.n = n
    def __len__(self): return self.n

class Killer(dict):
    def items(self):
        paare = list(super().items())
        for i, (k, v) in enumerate(paare):
            if i == len(paare) // 2:
                os.kill(os.getpid(), signal.SIGKILL)
            yield k, v

nutzlast = Killer(gross)
if art == "naiv":
    with open(pfad, "w") as f:
        json.dump(nutzlast, f, indent=1)
else:
    from zustandsdatei import schreibe
    schreibe(pfad, nutzlast)
''' % (HIER,)


def lauf(pfad, art):
    """Kind starten, das mitten im Schreiben stirbt.  Rueckgabe: Signal."""
    p = subprocess.run([sys.executable, "-c", KIND, pfad, art],
                       capture_output=True)
    return p.returncode


def lesbar(pfad):
    try:
        with open(pfad) as f:
            json.load(f)
        return True
    except (ValueError, OSError):
        return False


print("T-0051  Atomarer Schreibvorgang der Zustandsdatei\n")

print("1. Grundverhalten")
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "zustand.json")
    schreibe(p, {"berlin": {"abende": {"2026-08-23": {"p": 0.4}}}})
    with open(p) as f:
        z = json.load(f)
    ok(z["berlin"]["abende"]["2026-08-23"]["p"] == 0.4,
       "geschriebener Inhalt kommt unveraendert zurueck")
    schreibe(p, {"berlin": {"abende": {}}})
    with open(p) as f:
        ok(json.load(f)["berlin"]["abende"] == {},
           "zweiter Schreibvorgang ersetzt den ersten")
    ok(not [x for x in os.listdir(d) if x.endswith(".tmp")],
       "keine .tmp-Reste im Verzeichnis")
    tief = os.path.join(d, "neu", "tiefer", "zustand.json")
    schreibe(tief, {"a": 1})
    ok(os.path.exists(tief), "fehlendes Verzeichnis wird angelegt")

print("\n2. Abbruch mitten im Schreibvorgang (echtes SIGKILL)")
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "zustand.json")
    schreibe(p, {"stand": "gueltig"})
    rc = lauf(p, "naiv")
    ok(rc == -signal.SIGKILL, "Kind wurde tatsaechlich im Dump gekillt")
    naiv_kaputt = not lesbar(p)
    ok(naiv_kaputt,
       "NEGATIVPROBE: der naive Weg hinterlaesst eine unlesbare Datei")

with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "zustand.json")
    schreibe(p, {"stand": "gueltig"})
    rc = lauf(p, "atomar")
    ok(rc == -signal.SIGKILL, "Kind wurde tatsaechlich im Dump gekillt")
    ok(lesbar(p), "atomar geschrieben bleibt die Datei lesbar")
    with open(p) as f:
        ok(json.load(f) == {"stand": "gueltig"},
           "und traegt noch den ALTEN, vollstaendigen Stand")
    ok(not [x for x in os.listdir(d) if x.endswith(".tmp")]
       or True, "(.tmp-Rest nach SIGKILL ist erlaubt, er stoert keinen Leser)")

print("\n3. Wiederholt - ein Einzeltreffer waere Zufall")
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "zustand.json")
    schreibe(p, {"stand": "gueltig"})
    kaputt = 0
    for _ in range(25):
        lauf(p, "atomar")
        if not lesbar(p):
            kaputt += 1
    ok(kaputt == 0, "25 Abbrueche, 25-mal lesbar geblieben")

with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "zustand.json")
    schreibe(p, {"stand": "gueltig"})
    kaputt = 0
    for _ in range(25):
        lauf(p, "naiv")
        if not lesbar(p):
            kaputt += 1
        else:
            schreibe(p, {"stand": "gueltig"})
    ok(kaputt > 0,
       "NEGATIVPROBE: naiv zerlegt es die Datei (%d von 25)" % kaputt)

print("\n4. Der ECHTE Schreibweg der Agenten ist atomar")
# Nicht "kennt das Modul den Import" - das war die erste Fassung dieses
# Abschnitts, und sie ist durch die Negativprobe gefallen, ohne
# anzuschlagen: ein Modul kann `schreibe` importieren und trotzdem daneben
# mit json.dump schreiben.  Hier laeuft stattdessen `main()` der Agenten
# mit gestubbtem Netz, und beobachtet wird, WAS der Lauf am Dateisystem tut:
#   - die Zieldatei darf NIE mit Modus "w" geoeffnet werden (das truncatet),
#   - es MUSS ein os.replace auf sie geben (das ist der atomare Tausch).
import builtins                                            # noqa: E402
import erinnerung                                          # noqa: E402


def beobachte(zpfad, ruf):
    """`ruf()` ausfuehren und protokollieren, wie `zpfad` angefasst wurde."""
    prot = {"truncate": 0, "replace": 0}
    echt_open, echt_replace = builtins.open, os.replace

    def mein_open(datei, modus="r", *a, **k):
        if os.path.abspath(str(datei)) == os.path.abspath(zpfad) \
                and "w" in str(modus):
            prot["truncate"] += 1
        return echt_open(datei, modus, *a, **k)

    def mein_replace(src, dst, *a, **k):
        if os.path.abspath(str(dst)) == os.path.abspath(zpfad):
            prot["replace"] += 1
        return echt_replace(src, dst, *a, **k)

    builtins.open, os.replace = mein_open, mein_replace
    try:
        ruf()
    finally:
        builtins.open, os.replace = echt_open, echt_replace
    return prot


with tempfile.TemporaryDirectory() as d:
    zp = os.path.join(d, "zustand.json")
    schreibe(zp, {"berlin": {"abende": {}, "alarme": {}, "erinnerungen": {}}})
    kfg = {"orte": [{"name": "berlin", "anzeige": "Berlin", "breite": 52.52,
                     "laenge": 13.405, "zeitzone": "Europe/Berlin",
                     "ntfy_bewertung": "topic-test"}],
           "seiten_basis": "", "bewertung_tage_pro_woche": 7}
    kp = os.path.join(d, "konfig.json")
    with open(kp, "w") as f:
        json.dump(kfg, f)

    # erinnerung.py: Versand stubben, Zustandspfad umbiegen, main() fahren.
    erinnerung.sende = lambda *a, **k: 200
    erinnerung.BASIS = d
    os.makedirs(os.path.join(d, "daten"), exist_ok=True)
    schreibe(os.path.join(d, "daten", "zustand.json"),
             {"berlin": {"abende": {}, "alarme": {}}})
    zp2 = os.path.join(d, "daten", "zustand.json")
    # Ein Zeitpunkt sicher IM Aufforderungsfenster nach Sonnenuntergang.
    import datetime as _dt                                  # noqa: E402
    from sonnen.geometrie import sonnenuntergang as _su     # noqa: E402
    heute = _dt.date.today()
    std, _ = _su(heute, 52.52, 13.405)
    jetzt = (_dt.datetime.combine(heute, _dt.time(0), _dt.timezone.utc)
             + _dt.timedelta(hours=std + 0.75))
    sicher, sys.argv = sys.argv, [
        "erinnerung.py", "--konfig", kp, "--jetzt", jetzt.isoformat()]
    try:
        prot = beobachte(zp2, erinnerung.main)
    finally:
        sys.argv = sicher
    ok(prot["truncate"] == 0,
       "erinnerung.py truncatet die Zustandsdatei nie (%d mal)"
       % prot["truncate"])
    ok(prot["replace"] >= 1,
       "erinnerung.py tauscht sie per os.replace (%d mal)" % prot["replace"])
    with open(zp2) as f:
        ok(json.load(f)["berlin"].get("erinnerungen"),
           "und der Lauf hat wirklich etwas gebucht (sonst prueft das nichts)")

    # bewertungen_holen.py: ntfy-Abruf stubben, echte Note einspeisen.
    import bewertungen_holen as bh                          # noqa: E402
    bh.BASIS = d
    bh.warte_auf_netz = lambda *a, **k: None
    gestern = str(heute - _dt.timedelta(days=1))
    bh.hole = lambda topic, seit="12h": [
        ("2026-08-23T18:00:00Z", {"ort": "berlin", "tag": gestern, "note": 4})]
    schreibe(zp2, {"berlin": {"abende": {}, "alarme": {}}})
    sicher, sys.argv = sys.argv, ["bewertungen_holen.py", "--konfig", kp]
    try:
        prot = beobachte(zp2, bh.main)
    finally:
        sys.argv = sicher
    ok(prot["truncate"] == 0,
       "bewertungen_holen.py truncatet die Zustandsdatei nie (%d mal)"
       % prot["truncate"])
    ok(prot["replace"] >= 1,
       "bewertungen_holen.py tauscht sie per os.replace (%d mal)"
       % prot["replace"])
    with open(zp2) as f:
        ok(json.load(f)["berlin"]["abende"].get(gestern, {}).get("bewertung") == 4,
           "und der Lauf hat die Note wirklich eingetragen")

print("\n   (alarm.py wird in test_abruf.py Abschnitt 6 genauso geprueft -")
print("    dort laeuft main() mit gestubbtem Abruf ohnehin echt durch.)")

print()
if _fehler:
    print("FEHLGESCHLAGEN: %d" % len(_fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
