"""Ein Lauf ohne Ergebnis ist kein Erfolg (T-0075, Review alarm#8, physik#14).

Bis zum 09.10.2026 buchte alarm.main() einen Lauf, der fuer keinen einzigen
Abend ein Ergebnis hatte, trotzdem als gelaufen: `laeufe` bekam das Fenster,
`stand.geholt` wurde frisch, Exitcode 0.  Das Fenster war damit verbraucht,
nichts wurde nachgeholt, und die Seite hielt die alten Abende fuer frisch.
Fehlte der Wind am Ort ganz, war die Advektion still aus (Versatz 0, 0);
fehlte nur die Richtung, brach der Lauf mit ZeroDivisionError ab.

Der Test faehrt den ECHTEN alarm.main() mit einem erfundenen Netz (urlopen
gestubbt, formgleich wie Open-Meteo) und misst den ZUSTAND danach:

  a) nur None in den Wolken -> Zustand unveraendert, Exitcode != 0, Logzeile;
  b) Wind ganz None -> kein Abend mit Versatz 0 gebucht, Logzeile je Abend;
  c) nur die Richtung None -> kein ZeroDivisionError, sondern sauberer Abbruch;
  d) zwei Orte, einer leer -> der volle wird gebucht, der leere nicht;
  e) der Nachhol-Tick auf demselben Modelllauf fragt wieder das Netz, statt
     die leeren Bloecke aus dem Cache zu lesen - und bucht dann.

Alles in einem eigenen Temp-Verzeichnis (alarm.BASIS umgebogen), ohne Netz.

Lauf:  .venv/bin/python3 skripte/test_ausfall.py
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import urllib.parse
from datetime import datetime, timedelta, timezone

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import alarm  # noqa: E402
from zustandsdatei import schreibe  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


MEMBER = [""] + ["%02d" % n for n in range(1, 5)]
JETZT = "2026-10-09T12:00"                  # vor Sonnenuntergang
INIT = "2026-10-09T00:00+00:00"
ALT_STAND = {"geholt": "2026-10-07T15:20+00:00",
             "modelllauf": "2026-10-07T06:00+00:00", "fenster": "abend"}


def utc(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def wolke(la, lo, var, m, k):
    return float((int(la * 100) * 7 + int(lo * 100) * 13 + len(var) * 3
                  + (int(m) if m else 0) * 11 + k * 5) % 101)


class Netz:
    """Erfundenes Open-Meteo.  `wert(la, lo, var, m, k)` darf None liefern."""

    def __init__(self, wert):
        self.wert = wert
        self.urls = []

    def __call__(self, u, timeout=None):
        self.urls.append(u)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
        las = [float(x) for x in q["latitude"][0].split(",")]
        los = [float(x) for x in q["longitude"][0].split(",")]
        start = utc(JETZT).replace(hour=0)
        zeiten = [start + timedelta(hours=3 * k)
                  for k in range(8 * int(q["forecast_days"][0]))]
        aus = []
        for la, lo in zip(las, los):
            h = {"time": [t.strftime("%Y-%m-%dT%H:%M") for t in zeiten]}
            for v in q["hourly"][0].split(","):
                for m in MEMBER:
                    h[alarm.feldname(v, m)] = [self.wert(la, lo, v, m, k)
                                               for k in range(len(zeiten))]
            aus.append({"latitude": la, "longitude": lo, "hourly": h})
        rumpf = json.dumps(aus[0] if len(aus) == 1 else aus).encode()

        class Antwort:
            def __enter__(self_):
                return io.BytesIO(rumpf)

            def __exit__(self_, *x):
                return False
        return Antwort()


def gut(la, lo, v, m, k):
    if v.startswith("wind_speed"):
        return 60.0
    if v.startswith("wind_direction"):
        return 250.0
    return wolke(la, lo, v, m, k)


def ohne_wolken(la, lo, v, m, k):
    return None if v.startswith("cloud") else gut(la, lo, v, m, k)


def ohne_wind(la, lo, v, m, k):
    return None if v.startswith("wind") else gut(la, lo, v, m, k)


def ohne_richtung(la, lo, v, m, k):
    return None if v.startswith("wind_direction") else gut(la, lo, v, m, k)


def neue_basis(orte=None):
    d = tempfile.mkdtemp(prefix="ausfall_")
    os.makedirs(os.path.join(d, "daten"))
    kfg = json.load(open(os.path.join(BASIS, "konfig.json")))
    kfg["vorlauf_tage"] = 2
    if orte:
        kfg["orte"] = orte
    with open(os.path.join(d, "konfig.json"), "w") as f:
        json.dump(kfg, f)
    # Ein alter, gueltiger Stand: genau der darf nicht ueberschrieben werden.
    z = {o["name"]: {"abende": {}, "alarme": {}, "laeufe": {},
                     "stand": dict(ALT_STAND)} for o in kfg["orte"]}
    schreibe(os.path.join(d, "daten", "zustand.json"), z)
    return d


def zustand(basis):
    return json.load(open(os.path.join(basis, "daten", "zustand.json")))


def lauf(basis, netz):
    """alarm.main() einmal von Hand fahren.  Rueckgabe: (Ausnahme, Log)."""
    alt = (alarm.BASIS, alarm.modelllauf, alarm.warte_auf_netz, alarm.sende,
           alarm._jetzt_utc, alarm.urllib.request.urlopen, alarm.time.sleep,
           sys.argv)
    alarm.BASIS = basis
    alarm.modelllauf = lambda m: INIT
    alarm.warte_auf_netz = lambda *a, **k: None
    alarm.sende = lambda *a, **k: 200          # Riegel: nie ein echtes Topic
    alarm._jetzt_utc = lambda: utc(JETZT)
    alarm.urllib.request.urlopen = netz
    alarm.time.sleep = lambda s: None
    sys.argv = ["alarm.py", "--konfig", os.path.join(basis, "konfig.json"),
                "--jetzt", JETZT]
    for k in alarm.LAST:
        alarm.LAST[k] = 0
    puffer = io.StringIO()
    ausnahme = None
    try:
        with contextlib.redirect_stdout(puffer):
            alarm.main()
    except BaseException as ex:            # auch ZeroDivisionError zaehlen
        ausnahme = ex
    finally:
        (alarm.BASIS, alarm.modelllauf, alarm.warte_auf_netz, alarm.sende,
         alarm._jetzt_utc, alarm.urllib.request.urlopen, alarm.time.sleep,
         sys.argv) = alt
    return ausnahme, puffer.getvalue()


def ist_fehlschlag(ex):
    """Exitcode != 0 so, wie der Interpreter ihn setzen wuerde."""
    return (isinstance(ex, SystemExit) and ex.code not in (None, 0))


def unveraendert(basis, vorher, name="berlin"):
    e = zustand(basis).get(name, {})
    return e.get("stand") == ALT_STAND and not e.get("laeufe") \
        and not e.get("abende") and zustand(basis) == vorher


basen = []
try:
    print("a) Wolken nur None: kein Erfolg buchen")
    b = neue_basis()
    basen.append(b)
    vorher = zustand(b)
    ex, log = lauf(b, Netz(ohne_wolken))
    pruefe(ist_fehlschlag(ex), "Exitcode != 0 (war: %r)" % (ex,))
    pruefe(unveraendert(b, vorher),
           "Zustand unveraendert: kein laeufe-Eintrag, stand.geholt alt")
    pruefe("KEIN Abend mit Ergebnis" in log, "Logzeile nennt den Grund")
    pruefe(not os.path.isdir(os.path.join(b, "daten", "archiv")),
           "kein Tagesarchiv geschrieben")

    print("e) Nachhol-Tick auf demselben Modelllauf fragt das Netz neu")
    netz = Netz(gut)
    ex, log = lauf(b, netz)
    pruefe(ex is None, "zweiter Lauf ohne Ausnahme (war: %r)" % (ex,))
    pruefe(len(netz.urls) > 0, "Netz wieder gefragt (%d Aufrufe), nicht "
           "die leeren Bloecke aus dem Cache gelesen" % len(netz.urls))
    e = zustand(b).get("berlin", {})
    pruefe(e.get("stand", {}).get("geholt", "").startswith("2026-10-09T12:00")
           and e.get("laeufe", {}).get("2026-10-09"),
           "jetzt gebucht: stand.geholt frisch, laeufe eingetragen")

    print("b) Wind ganz None: Advektion nicht still abschalten")
    b = neue_basis()
    basen.append(b)
    vorher = zustand(b)
    ex, log = lauf(b, Netz(ohne_wind))
    pruefe(ist_fehlschlag(ex), "Exitcode != 0 (war: %r)" % (ex,))
    pruefe(unveraendert(b, vorher), "kein Abend mit Versatz 0 gebucht")
    pruefe(log.count("KEIN Wind am Ort") >= 2,
           "Logzeile je Abend ohne Wind (%d)" % log.count("KEIN Wind am Ort"))

    print("c) nur die Richtung None: kein ZeroDivisionError")
    b = neue_basis()
    basen.append(b)
    vorher = zustand(b)
    ex, log = lauf(b, Netz(ohne_richtung))
    pruefe(not isinstance(ex, ZeroDivisionError),
           "kein ZeroDivisionError (war: %s)" % type(ex).__name__)
    pruefe(ist_fehlschlag(ex) and unveraendert(b, vorher),
           "sauberer Abbruch, Zustand unveraendert")

    print("d) zwei Orte, einer ohne Daten: nur der volle wird gebucht")
    orte = [{"name": "berlin", "anzeige": "Berlin", "breite": 52.52,
             "laenge": 13.405, "zeitzone": "Europe/Berlin"},
            {"name": "muenchen", "anzeige": "Muenchen", "breite": 48.14,
             "laenge": 11.58, "zeitzone": "Europe/Berlin"}]

    def sued_leer(la, lo, v, m, k):
        return None if la < 50.0 else gut(la, lo, v, m, k)
    b = neue_basis(orte)
    basen.append(b)
    ex, log = lauf(b, Netz(sued_leer))
    z = zustand(b)
    pruefe(ist_fehlschlag(ex) and "muenchen" in str(ex.code),
           "Exitcode != 0 und Grund nennt den leeren Ort")
    pruefe(z["berlin"]["stand"]["geholt"].startswith("2026-10-09T12:00")
           and z["berlin"]["laeufe"].get("2026-10-09"),
           "Berlin gebucht")
    pruefe(z["muenchen"]["stand"] == ALT_STAND
           and not z["muenchen"].get("laeufe"),
           "Muenchen nicht gebucht (Fenster bleibt offen)")
finally:
    for b in basen:
        shutil.rmtree(b, ignore_errors=True)

print()
if fehler:
    print("%d FEHLER" % len(fehler))
    sys.exit(1)
print("alle Pruefungen gruen")
