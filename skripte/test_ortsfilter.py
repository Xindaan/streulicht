"""T-0056: `--geplant` rechnet nur die Orte, deren Fenster offen ist.

Ohne den Filter loeste EIN faelliger Ort den vollen Abruf fuer ALLE aus -
rund 3.500 Kontingenteinheiten je Ort fuer Zahlen, die niemand angefordert
hat.  Nebenwirkung: die `laeufe` der ungefragten Orte wurden als "vonhand"
gebucht und verbrauchten damit ihr eigenes Fenster fuer den Tag.

Der Test faehrt `alarm.main()` mit ZWEI Orten und einem erfundenen Abruf und
liest hinterher das Abrufprotokoll - er zaehlt also echte Anfragen, statt den
Quelltext zu lesen.

Feste Zeit statt Wanduhr (T-0079, Review tests#4): der Test lief bis hierher
mit `date.today()` und war vom 10.05. bis 02.08. jedes Jahr rot, weil sich die
Abendfenster von Berlin und Bilbao im Sommer ueberlappen (Berlin geht dann
spaet unter, Bilbao nur wenig spaeter) - bei unveraendertem Code.  Jetzt ist
der Tag fest (FEST, ein Novembertag mit gut anderthalb Stunden Abstand), und
die Voraussetzung "nur Berlin ist faellig" wird in Abschnitt 1 gemessen statt
angenommen.  Wert-Huerde: aendert jemand die Fensterlogik so, dass beide Orte
faellig werden, oder faellt der Ortsfilter in `--geplant` weg, wird Abschnitt 2
bzw. 3 rot - und zwar an jedem Kalendertag gleich.

Kein ntfy-POST: `alarm.sende` ist durch einen Aufzeichner ersetzt.  Die
Schwelle 2.0 verhindert ohnehin jeden Push (eine Wahrscheinlichkeit ist <= 1);
der Aufzeichner macht das zum geprueften Riegel (Abschnitt 6): wuerde ein Push
ausgeloest, ginge er ins Leere statt an ein echtes Topic.

Lauf:  python3 skripte/test_ortsfilter.py
"""
import datetime as dt
import json
import os
import shutil
import sys
import tempfile

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import alarm  # noqa: E402
import test_abruf  # noqa: E402
from sonnen.geometrie import sonnenuntergang  # noqa: E402
from zustandsdatei import lade, schreibe  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


FEST = dt.date(2026, 11, 10)         # fester Bezugstag, siehe Docstring
VORLAUF_H = 3                        # lauf_vorlauf_stunden, fest statt Produktivwert
GESENDET = []                        # jeder Aufruf von alarm.sende landet hier
test_abruf.ZEITACHSE_START = dt.datetime.combine(     # Zeitachse zum festen Tag
    FEST, dt.time(0), dt.timezone.utc)


# Zwei Orte weit auseinander: Berlin und Bilbao gehen rund eine Stunde
# auseinander unter, ihre Abendfenster ueberlappen also nicht.
ORTE = [{"name": "berlin", "anzeige": "Berlin", "breite": 52.52,
         "laenge": 13.405, "zeitzone": "Europe/Berlin",
         "ntfy_alarm": "t-berlin"},
        {"name": "bilbao", "anzeige": "Bilbao", "breite": 43.26,
         "laenge": -2.93, "zeitzone": "Europe/Madrid",
         "ntfy_alarm": "t-bilbao"}]


def lauf(geplant, jetzt):
    """alarm.main() fahren.  Rueckgabe: (Abrufprotokoll, Zustand)."""
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "daten"), exist_ok=True)
    kfg = json.load(open(os.path.join(BASIS, "konfig.json")))
    kfg["orte"] = [dict(o) for o in ORTE]
    kfg["schwelle_wahrscheinlichkeit"] = 2.0        # kein Push
    kfg["lauf_vorlauf_stunden"] = VORLAUF_H
    kp = os.path.join(d, "konfig.json")
    with open(kp, "w") as f:
        json.dump(kfg, f)
    schreibe(os.path.join(d, "daten", "zustand.json"),
             {o["name"]: {"abende": {}, "alarme": {}} for o in ORTE})

    del test_abruf.ABRUFE[:]
    alt = (alarm.BASIS, alarm.abfrage, alarm.modelllauf, alarm.warte_auf_netz,
           alarm.sende)
    alarm.BASIS = d
    alarm.abfrage = test_abruf.falscher_abruf
    alarm.modelllauf = lambda m: "2026-01-01T00:00+00:00"
    alarm.warte_auf_netz = lambda *a, **k: None
    alarm.sende = lambda *a, **k: GESENDET.append((a, k)) or 200
    argv = ["alarm.py", "--konfig", kp, "--jetzt", jetzt.isoformat()]
    if geplant:
        argv.append("--geplant")
    sicher, sys.argv = sys.argv, argv
    try:
        alarm.main()
    finally:
        sys.argv = sicher
        (alarm.BASIS, alarm.abfrage, alarm.modelllauf,
         alarm.warte_auf_netz, alarm.sende) = alt
    z = lade(os.path.join(d, "daten", "zustand.json"))
    shutil.rmtree(d, ignore_errors=True)
    return list(test_abruf.ABRUFE), z


def zellen_von(ort):
    return {alarm.zelle(ort["breite"], ort["laenge"])}


print("T-0056  --geplant rechnet nur faellige Orte\n")

heute = FEST
kfg0 = json.load(open(os.path.join(BASIS, "konfig.json")))
kfg0["lauf_vorlauf_stunden"] = VORLAUF_H
vorlauf = VORLAUF_H

print("1. Ein Zeitpunkt, an dem GENAU Berlin faellig ist")
std, _ = sonnenuntergang(heute, 52.52, 13.405)
jetzt = (dt.datetime.combine(heute, dt.time(0), dt.timezone.utc)
         + dt.timedelta(hours=std - vorlauf + 0.1))
fenster = {}
for o in ORTE:
    name, grund = alarm.im_laufenster(jetzt, kfg0, o, {})
    print("      %-8s %s" % (o["name"], grund))
    if name:
        fenster[o["name"]] = name
pruefe(set(fenster) == {"berlin"},
       "nur Berlin liegt im Fenster (%s)" % (sorted(fenster) or "-"))

print("\n2. Der geplante Lauf holt NUR Berlins Zellen")
abrufe, z = lauf(geplant=True, jetzt=jetzt)
geholt = set()
for x in abrufe:
    geholt |= x["zellen"]
pruefe(bool(abrufe), "es wurde ueberhaupt abgerufen (%d Anfragen)" % len(abrufe))
pruefe(zellen_von(ORTE[0]) <= geholt, "Berlins Heimatzelle ist dabei")
pruefe(not (zellen_von(ORTE[1]) & geholt),
       "Bilbaos Heimatzelle ist NICHT dabei")

print("\n3. Und bucht auch nur fuer Berlin")
pruefe(bool(z["berlin"].get("laeufe")), "Berlin ist gebucht")
pruefe(not z["bilbao"].get("laeufe"),
       "Bilbao ist NICHT gebucht - sein Fenster bleibt fuer heute offen")
pruefe(not z["bilbao"].get("stand"), "und hat keinen Stand bekommen")
pruefe(bool(z["berlin"].get("abende")), "Berlin hat gerechnete Abende")
pruefe(not z["bilbao"].get("abende"), "Bilbao hat keine")

print("\n4. Ein Lauf VON HAND rechnet weiterhin alle Orte")
# Wer ihn startet, meint ihn - dieselbe Begruendung wie beim Fenster-Check.
abrufe2, z2 = lauf(geplant=False, jetzt=jetzt)
geholt2 = set()
for x in abrufe2:
    geholt2 |= x["zellen"]
pruefe(zellen_von(ORTE[0]) <= geholt2 and zellen_von(ORTE[1]) <= geholt2,
       "beide Heimatzellen werden geholt")
pruefe(bool(z2["berlin"].get("abende")) and bool(z2["bilbao"].get("abende")),
       "und beide Orte haben gerechnete Abende")

print("\n5. Die Ersparnis in Zahlen")
print("      geplant: %d Anfragen, %d Zellen | von Hand: %d Anfragen, %d Zellen"
      % (len(abrufe), len(geholt), len(abrufe2), len(geholt2)))
pruefe(len(geholt) < len(geholt2),
       "der geplante Lauf holt weniger Zellen (%d gegen %d)"
       % (len(geholt), len(geholt2)))

print("\n6. Riegel: kein einziger ntfy-Versand in allen Laeufen")
pruefe(not GESENDET, "alarm.sende wurde nie aufgerufen (%d Aufrufe)"
       % len(GESENDET))

print()
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
