"""Offline-Pruefung der Advektionsmechanik - kein Netz noetig.

Drei Dinge, die still falsch sein koennen und dann nicht auffallen:
  1. Windrichtungskonvention (meteorologisch = Richtung, AUS der es weht)
  2. Mittelung von Windrichtungen ueber den Nordsprung hinweg
  3. Wahl des naechsten nativen Schritts zum Sonnenuntergang
"""
import importlib.util
import math
import os
import sys
from datetime import datetime, timedelta, timezone

_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarm.py")
_s = importlib.util.spec_from_file_location("alarm", _p)
alarm = importlib.util.module_from_spec(_s)
_s.loader.exec_module(alarm)

fehler = 0


def pruefe(bedingung, text):
    global fehler
    if not bedingung:
        fehler += 1
        print("   FEHLER: %s" % text)
    return bedingung


print("Windrichtungskonvention")
for ri, sdx, sdy in ((270, +36, 0), (90, -36, 0), (180, 0, +36), (0, 0, -36)):
    dx, dy = alarm.versatz_km(36.0, ri, 1.0)
    pruefe(abs(dx - sdx) < 0.1 and abs(dy - sdy) < 0.1,
           "Richtung %d: erwartet (%+d,%+d), bekommen (%+.1f,%+.1f)"
           % (ri, sdx, sdy, dx, dy))

print("Zirkulaeres Richtungsmittel (Nordsprung)")


def zirk(ri):
    sx = sum(math.sin(math.radians(x)) for x in ri) / len(ri)
    cy = sum(math.cos(math.radians(x)) for x in ri) / len(ri)
    return math.degrees(math.atan2(sx, cy)) % 360.0


for ri, soll in (([350, 10], 0), ([170, 190], 180), ([355, 5, 15], 5)):
    pruefe(abs((zirk(ri) - soll + 180) % 360 - 180) < 1.0,
           "Mittel von %s soll %d sein, ist %.1f" % (ri, soll, zirk(ri)))
# Der arithmetische Mittelwert MUSS hier falsch liegen - sonst pruefen wir nichts
pruefe(abs(sum([355, 5, 15]) / 3 - 5) > 100,
       "Testfall trifft den Nordsprung nicht")

print("Naechster nativer Schritt (3-h-Raster)")
z = ["2026-08-15T%02d:00" % h for h in range(0, 24, 3)]
for su in (18.47, 14.90, 17.10, 19.55, 13.05):
    ziel = datetime(2026, 8, 15, tzinfo=timezone.utc) + timedelta(hours=su)
    i, dt = alarm.naechster_schritt(z, ziel)
    pruefe(dt <= 1.5 + 1e-9, "Sonnenuntergang %.2f: |dt| = %.2f h > 1.5" % (su, dt))

print("Abtastrichtung: STROMAUF, nicht stromab (T-0063)")
# Der eigentliche Fehler sass nicht in versatz_km, sondern eine Ebene
# darueber: die Funktion liefert richtig, WOHIN die Luft zieht - der Lauf
# hat diesen Vektor aber ADDIERT, statt ihn abzuziehen.
#
# Gesucht ist die Wolke, die zum Sonnenuntergang ueber dem Fanpunkt steht.
# Das Modellfeld liegt frueher vor; dieselbe Luft war da noch stromauf.  Bei
# Wind aus Westen muss also WESTLICH des Fanpunkts abgetastet werden.
#
# Geprueft wird das VERHALTEN des Laufs, nicht der Quelltext: welche Zellen
# fordert Pass 2 an?  Bei Wind aus Westen muessen sie WESTLICH der Zellen
# aus Pass 1 liegen.  Term A taugt dafuer nicht - er ist im Nahbereich
# raumwinkelgewichtet, der Standortpunkt traegt allein rund drei Viertel,
# und das Ergebnis haengt dann mehr an der Gewichtung als an der Richtung.
import json                                                      # noqa: E402
import os                                                        # noqa: E402
import tempfile                                                  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMBER = [""] + ["%02d" % n for n in range(1, 51)]
ABRUFE = []

# Das native Raster wird um 1.5 h gegen Mitternacht versetzt, damit der
# Sonnenuntergang moeglichst WEIT von einem Schritt entfernt liegt.  Bei
# einem Raster auf der vollen Stunde ist dt ~ 0.1 h, der Versatz betraegt
# dann wenige Kilometer und bleibt innerhalb einer 0.25-Grad-Zelle - der
# Test koennte die Richtung gar nicht sehen.
RASTERVERSATZ_H = 1.5
WIND_KMH = 60.0


def protokollierender_abruf(zellen, variablen, modell, tage, block=25):
    ABRUFE.append({"zellen": set(zellen),
                   "variablen": list(variablen)})
    start = (datetime(2026, 9, 2, tzinfo=timezone.utc)
             + timedelta(hours=RASTERVERSATZ_H))
    zeiten = [(start + timedelta(hours=3 * k)).strftime("%Y-%m-%dT%H:%M")
              for k in range(8 * tage)]
    aus = {}
    for z in zellen:
        h = {"time": zeiten}
        for v in variablen:
            for m in MEMBER:
                if v.startswith("wind_speed"):
                    w = [WIND_KMH] * len(zeiten)
                elif v.startswith("wind_direction"):
                    w = [270.0] * len(zeiten)      # aus Westen
                else:
                    w = [50.0] * len(zeiten)
                h[alarm.feldname(v, m)] = w
        aus[z] = h
    return aus


d = tempfile.mkdtemp()
os.makedirs(os.path.join(d, "daten"), exist_ok=True)
_kfg = json.load(open(os.path.join(BASIS, "konfig.json")))
_kfg["vorlauf_tage"] = 1
_kp = os.path.join(d, "konfig.json")
with open(_kp, "w") as _f:
    json.dump(_kfg, _f)
_alt = (alarm.BASIS, alarm.abfrage, alarm.modelllauf, alarm.warte_auf_netz)
alarm.BASIS = d
alarm.abfrage = protokollierender_abruf
alarm.modelllauf = lambda m: "2026-09-02T00:00+00:00"
alarm.warte_auf_netz = lambda *a_, **k_: None
_sicher, sys.argv = sys.argv, ["alarm.py", "--konfig", _kp,
                               "--jetzt", "2026-09-02T06:00"]
try:
    alarm.main()
finally:
    sys.argv = _sicher
    (alarm.BASIS, alarm.abfrage, alarm.modelllauf, alarm.warte_auf_netz) = _alt

_wolke = [a for a in ABRUFE if all(v.startswith("cloud_") for v in a["variablen"])]
pruefe(len(_wolke) >= 2, "Pass 2 hat ueberhaupt stattgefunden (%d Wolkenabrufe)"
       % len(_wolke))
if len(_wolke) >= 2:
    _pass1 = _wolke[0]["zellen"]
    _neu = _wolke[-1]["zellen"] - _pass1
    _lon1 = sum(alarm.mitte(z)[1] for z in _pass1) / len(_pass1)
    _lon2 = sum(alarm.mitte(z)[1] for z in _neu) / len(_neu)
    pruefe(_lon2 < _lon1,
           "Pass 2 tastet WESTLICH von Pass 1 ab (%.3f gegen %.3f Grad Ost)"
           % (_lon2, _lon1))
    # Groessenordnung mitpruefen: 60 km/h ueber rund 1.4 h sind gut 80 km,
    # also mehrere Zellen.  Ein Versatz von einer halben Zelle waere ein
    # Rundungsartefakt und kein Beleg fuer die Richtung.
    pruefe(_lon1 - _lon2 > 0.25,
           "und zwar deutlich, nicht um eine Rundung (%.3f Grad)"
           % (_lon1 - _lon2))

print("\n%s" % ("alle Pruefungen bestanden" if fehler == 0
                else "%d Pruefung(en) fehlgeschlagen" % fehler))
sys.exit(1 if fehler else 0)
