"""Offline-Pruefung der Quantilabbildung fuer s*_WN3 (T-0072) - kein Netz.

Die Abbildung erzeugt eine SCHWELLE; ein still falscher Rechenkern verschiebt
die Alarmrate, ohne dass irgendein Lauf scheitert.  Geprueft wird am
ERGEBNIS mit Reihen, deren richtige Antwort von vornherein feststeht:

  1. Verschiebung: Ziel = Referenz + 0,1  ->  s*_Ziel = s* + 0,1
     (faengt vertauschte Rollen und eine umgedrehte Richtung von q)
  2. Monotone Verzerrung: Ziel = Referenz^2  ->  s*_Ziel = s*^2
     (faengt "Quantil aus der falschen Reihe": bei Verschiebung waere der
     Fehler unsichtbar, wenn beide Reihen gleich verteilt waeren)
  3. q ist der Anteil UNTER s* (strikt), wie s* als Perzentil definiert ist
  4. Rand: s* ueber allen Referenzwerten -> q = 1, Maximum der Zielreihe
  5. ungleich lange Reihen werden abgewiesen, nicht still abgeschnitten
  6. Bootstrap: reproduzierbar, enthaelt den Punktwert, wird mit n enger

Lauf:  .venv/bin/python3 skripte/test_wn3_quantil.py
"""
import importlib.util
import os
import sys

_hier = os.path.dirname(os.path.abspath(__file__))
_s = importlib.util.spec_from_file_location("wn3_quantil", os.path.join(_hier, "wn3_quantil.py"))
m = importlib.util.module_from_spec(_s)
_s.loader.exec_module(m)

fehler = 0


def pruefe(bedingung, text):
    global fehler
    if not bedingung:
        fehler += 1
        print("  FEHLER: %s" % text)
    else:
        print("  ok: %s" % text)


S = 0.7065
# 400 Abende, gleichmaessig zwischen 0 und 1 - die richtige Antwort ist bekannt
ref = [(i + 0.5) / 400.0 for i in range(400)]
# gemischte Reihenfolge: die Abbildung darf nicht von der Sortierung leben
ref = ref[1::2] + ref[0::2]
schritt = 1.0 / 400.0

print("1. Verschiebung")
q, s_z = m.quantilabbildung(ref, [r + 0.1 for r in ref], S)
pruefe(abs(s_z - (S + 0.1)) <= schritt, "s*_Ziel = %.4f, erwartet %.4f" % (s_z, S + 0.1))

print("2. monotone Verzerrung")
q, s_z = m.quantilabbildung(ref, [r * r for r in ref], S)
pruefe(abs(s_z - S * S) <= 2 * schritt, "s*_Ziel = %.4f, erwartet %.4f" % (s_z, S * S))

print("3. q strikt unter s*")
gitter = [i / 100.0 for i in range(100)]
q, _ = m.quantilabbildung(gitter, gitter, 0.95)
pruefe(abs(q - 0.95) < 1e-12, "q = %.4f bei s* auf einem Datenpunkt (erwartet 0,95)" % q)

print("4. Rand")
q, s_z = m.quantilabbildung([0.1, 0.2, 0.3], [0.5, 0.9, 0.7], 0.8)
pruefe(q == 1.0 and s_z == 0.9, "q = %s, s*_Ziel = %s (erwartet 1,0 und 0,9)" % (q, s_z))

print("5. ungleich lange Reihen")
try:
    m.quantilabbildung([0.1, 0.2], [0.1], S)
    pruefe(False, "ungleich lange Reihen wurden angenommen")
except ValueError:
    pruefe(True, "ungleich lange Reihen -> ValueError")

print("6. Bootstrap")
ziel = [r + 0.1 for r in ref]
a = m.bootstrap(ref, ziel, S, n=300, seed=7)
b = m.bootstrap(ref, ziel, S, n=300, seed=7)
pruefe(a == b, "gleicher Seed, gleiches Intervall")
_, punkt = m.quantilabbildung(ref, ziel, S)
pruefe(a[0] <= punkt <= a[1], "Intervall [%.4f, %.4f] enthaelt %.4f" % (a[0], a[1], punkt))
# 40 Abende (so viele hat die Klimatologie heute fuer 2026) gegen 400
klein = ref[::10]
k = m.bootstrap(klein, [r + 0.1 for r in klein], S, n=300, seed=7)
pruefe((k[1] - k[0]) > 2 * (a[1] - a[0]),
       "n = 40 breiter als n = 400: %.4f gegen %.4f" % (k[1] - k[0], a[1] - a[0]))

print("\n%s" % ("Alles gruen." if fehler == 0 else "%d Fehler." % fehler))
sys.exit(1 if fehler else 0)
