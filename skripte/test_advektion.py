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

print("\n%s" % ("alle Pruefungen bestanden" if fehler == 0
                else "%d Pruefung(en) fehlgeschlagen" % fehler))
sys.exit(1 if fehler else 0)
