"""T-0055: ein gescheiterter Push darf nicht den ganzen Lauf verwerfen.

`sende()` laesst urllib-Fehler durch, und in der Ortsschleife stand kein
try/except.  Persistiert wird erst ganz am Ende von `main()`.  Ein
ntfy-Timeout NACH vollstaendiger Rechnung riss deshalb alles mit:

  * die Push-Buchung (`alarme`) - der naechste Tick pusht denselben Abend
    erneut, Idempotenz futsch,
  * den `laeufe`-Eintrag - und weil der fehlt, haelt `im_laufenster()` das
    Fenster fuer offen und der naechste stuendliche Tick rechnet ALLES neu:
    rund 3.500 Kontingenteinheiten fuer Zahlen, die schon dastanden,
  * `stand` und das Tagesarchiv des Laufs.

Der Kommentar an der Buchungsstelle ("Erst NACH erfolgreichem Durchlauf
eintragen") ist gegen den Kontingenttod gedacht - und arbeitete hier gegen
sich selbst: ein toter Push ist kein toter Lauf.

Lauf:  python3 skripte/test_alarm_versand.py
"""
import json
import os
import shutil
import sys
import tempfile
import urllib.error

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import alarm  # noqa: E402
import test_abruf  # noqa: E402  (nur der erfundene Abruf, kein Netz)

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


def lauf(sende_wirft):
    """Einen vollstaendigen Alarmlauf fahren.  Rueckgabe: der Zustand."""
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "daten"), exist_ok=True)
    kfg = json.load(open(os.path.join(BASIS, "konfig.json")))
    # Schwelle auf 0, damit der Push-Zweig sicher erreicht wird - sonst
    # haengt der Test an der Wetterlage und prueft an den meisten Tagen
    # nichts (genau der Fehler aus T-0053).
    kfg["schwelle_wahrscheinlichkeit"] = 0.0
    kfg["seiten_basis"] = "https://example.invalid"
    for o in kfg["orte"]:
        o["ntfy_alarm"] = "topic-test"
    kp = os.path.join(d, "konfig.json")
    with open(kp, "w") as f:
        json.dump(kfg, f)

    gesendet = []

    def sende(topic, titel, text, prio="default", klick=None):
        gesendet.append(topic)
        if sende_wirft:
            raise urllib.error.URLError("ntfy nicht erreichbar (Test)")
        return 200

    alt = (alarm.BASIS, alarm.abfrage, alarm.modelllauf, alarm.sende,
           alarm.warte_auf_netz)
    alarm.BASIS = d
    alarm.abfrage = test_abruf.falscher_abruf
    alarm.modelllauf = lambda m: "2026-01-01T00:00+00:00"
    alarm.sende = sende
    alarm.warte_auf_netz = lambda *a, **k: None
    sicher, sys.argv = sys.argv, ["alarm.py", "--konfig", kp]
    try:
        alarm.main()
    finally:
        sys.argv = sicher
        (alarm.BASIS, alarm.abfrage, alarm.modelllauf, alarm.sende,
         alarm.warte_auf_netz) = alt
    zp = os.path.join(d, "daten", "zustand.json")
    z = json.load(open(zp)) if os.path.exists(zp) else {}
    archiv = os.path.join(d, "daten", "archiv")
    dateien = []
    for w, _, fs in os.walk(archiv):
        dateien += [os.path.join(w, f) for f in fs]
    shutil.rmtree(d, ignore_errors=True)
    return z, gesendet, dateien


print("T-0055  Ein toter Push ist kein toter Lauf\n")

print("1. Der gute Fall - damit der Rest ueberhaupt etwas beweist")
z, ges, dat = lauf(sende_wirft=False)
e = z.get("berlin", {})
pruefe(bool(ges), "es wurde gesendet (%d mal)" % len(ges))
pruefe(bool(e.get("alarme")), "Push ist gebucht (%d Abende)"
       % len(e.get("alarme", {})))
pruefe(bool(e.get("laeufe")), "Lauf ist gebucht")
pruefe(bool(e.get("stand")), "Stand ist geschrieben")
pruefe(len(dat) == 1, "Tagesarchiv ist entstanden (%d Datei(en))" % len(dat))

print("\n2. Der Versand scheitert - der Rest des Laufs muss stehen bleiben")
z, ges, dat = lauf(sende_wirft=True)
e = z.get("berlin", {})
pruefe(bool(ges), "der Versand wurde versucht (%d mal)" % len(ges))
pruefe(bool(z), "die Zustandsdatei wurde ueberhaupt geschrieben")
pruefe(bool(e.get("laeufe")),
       "der Lauf ist gebucht - der naechste Tick rechnet NICHT alles neu")
pruefe(bool(e.get("stand")), "Stand ist geschrieben (die Seite bleibt aktuell)")
pruefe(len(dat) == 1, "das Tagesarchiv ist trotzdem entstanden (%d)" % len(dat))
pruefe(bool(e.get("abende")),
       "die gerechneten Abende sind da (%d)" % len(e.get("abende", {})))

print("\n3. Aber der gescheiterte Push wird NICHT als gesendet gebucht")
# Sonst waere der Fix schlimmer als der Fehler: ein Abend gaelte als
# gemeldet, ohne dass je eine Meldung ankam - und die Idempotenzsperre
# verhindert dauerhaft, dass er nachgeholt wird.
pruefe(not e.get("alarme"),
       "keine Alarmbuchung fuer einen Push, der nie ankam (%s)"
       % (sorted(e.get("alarme", {})) or "-"))

print("\n4. Dieselbe Klasse in erinnerung.py (Isomorphie-Check)")
# Bei EINEM Ort ist der alte Code folgenlos: nichts gesendet, nichts gebucht,
# der naechste Tick versucht es erneut.  Ab dem ZWEITEN Ort geht die Buchung
# des ersten verloren, weil main() abbricht, bevor geschrieben wird - und der
# erste Ort bekommt seine Aufforderung ein zweites Mal.
import datetime as _dt                                       # noqa: E402
import erinnerung                                            # noqa: E402
from sonnen.geometrie import sonnenuntergang as _su          # noqa: E402


def lauf_erinnerung(wirft_bei):
    """Zwei Orte; `sende` wirft beim Ort mit diesem Namen."""
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "daten"), exist_ok=True)
    orte = [{"name": "berlin", "anzeige": "Berlin", "breite": 52.52,
             "laenge": 13.405, "zeitzone": "Europe/Berlin",
             "ntfy_bewertung": "t-a"},
            {"name": "zweitort", "anzeige": "Zweitort", "breite": 52.52,
             "laenge": 13.405, "zeitzone": "Europe/Berlin",
             "ntfy_bewertung": "t-b"}]
    kp = os.path.join(d, "konfig.json")
    with open(kp, "w") as f:
        json.dump({"orte": orte, "seiten_basis": "",
                   "bewertung_tage_pro_woche": 7}, f)
    zpfad = os.path.join(d, "daten", "zustand.json")
    with open(zpfad, "w") as f:
        json.dump({o["name"]: {"abende": {}, "alarme": {}} for o in orte}, f)

    reihe = []

    def sende(topic, titel, text, klick=None):
        reihe.append(topic)
        if topic == wirft_bei:
            raise urllib.error.URLError("ntfy weg (Test)")
        return 200

    heute = _dt.date.today()
    std, _ = _su(heute, 52.52, 13.405)
    jetzt = (_dt.datetime.combine(heute, _dt.time(0), _dt.timezone.utc)
             + _dt.timedelta(hours=std + 0.75))
    alt_b, alt_s = erinnerung.BASIS, erinnerung.sende
    erinnerung.BASIS, erinnerung.sende = d, sende
    sicher, sys.argv = sys.argv, ["erinnerung.py", "--konfig", kp,
                                  "--jetzt", jetzt.isoformat()]
    try:
        erinnerung.main()
    except Exception as ex:
        print("      (main() ist gestorben: %s)" % type(ex).__name__)
    finally:
        sys.argv = sicher
        erinnerung.BASIS, erinnerung.sende = alt_b, alt_s
    z = json.load(open(zpfad))
    shutil.rmtree(d, ignore_errors=True)
    return z, reihe


z2, reihe = lauf_erinnerung(wirft_bei="t-b")
pruefe(len(reihe) == 2, "beide Orte wurden versucht (%d)" % len(reihe))
pruefe(bool(z2.get("berlin", {}).get("erinnerungen")),
       "der ERSTE Ort bleibt gebucht, obwohl der zweite scheiterte")
pruefe(not z2.get("zweitort", {}).get("erinnerungen"),
       "der gescheiterte Ort wird nicht gebucht")

print()
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
