"""Teiljahr und Blockdeckel in klimatologie.hole_jahr (T-0072) - netzfrei.

Das Nachholen der Klimatologie 2026 laeuft in Tagesportionen, weil es sich
das Open-Meteo-Tageslimit mit den Alarmlaeufen und Gardena teilt. Drei
Dinge koennen dabei still falsch sein:

  1. Der Blockdeckel greift nicht -> ein Aufruf holt alles und reisst das
     Tageslimit (der Alarmlauf danach scheitert).
  2. Das Enddatum geht nicht in die Anfrage -> die API bekommt 12-31 eines
     laufenden Jahres und antwortet mit Fehler oder Luecken.
  3. Der Teiljahr-Block landet unter dem Ganzjahres-Cachenamen -> ein
     spaeterer Ganzjahreslauf liest ihn als vollstaendig.

`_hole` ist durch eine Attrappe ersetzt, die URLs mitschreibt; BASIS zeigt
in ein Temp-Verzeichnis. Kein Netz, kein Kontingent.

Lauf:  .venv/bin/python3 skripte/test_klima_teiljahr.py
"""
import importlib.util
import os
import sys
import tempfile
from datetime import date

_hier = os.path.dirname(os.path.abspath(__file__))
_s = importlib.util.spec_from_file_location("klimatologie", os.path.join(_hier, "klimatologie.py"))
k = importlib.util.module_from_spec(_s)
_s.loader.exec_module(k)

fehler = 0


def pruefe(bedingung, text):
    global fehler
    if not bedingung:
        fehler += 1
        print("  FEHLER: %s" % text)
    else:
        print("  ok: %s" % text)


urls = []


def attrappe(u, versuche=4):
    urls.append(u)
    n = u.split("latitude=")[1].split("&")[0].count(",") + 1
    return [{"hourly": {"time": ["2026-03-01T17:00"],
                        "cloud_cover_low": [10], "cloud_cover_mid": [20],
                        "cloud_cover_high": [30]}} for _ in range(n)]


k._hole = attrappe
k.time.sleep = lambda s: None
k.BASIS = tempfile.mkdtemp(prefix="klima_teiljahr_")
zellen = {(100 + i, 20 + i) for i in range(118)}          # 118 wie fuer Berlin
gesucht = {"2026-03-01": "2026-03-01T17:00"}
ende = date(2026, 11, 1)

print("1. Blockdeckel")
try:
    k.hole_jahr(zellen, 2026, gesucht, ende=ende, max_bloecke=1)
    pruefe(False, "kein Blockdeckel ausgeloest")
except k.Blockdeckel:
    pruefe(len(urls) == 1, "genau ein Netzblock, dann Blockdeckel (%d)" % len(urls))
pruefe(issubclass(k.Blockdeckel, k.KontingentErschoepft),
       "Blockdeckel nimmt den Kontingent-Ausstieg in main()")

print("2. Enddatum in der Anfrage")
pruefe(urls and "end_date=2026-11-01" in urls[0] and "end_date=2026-12-31" not in urls[0],
       "end_date=2026-11-01 statt 12-31")

print("3. zweiter Tag setzt am Cache an")
aus = k.hole_jahr(zellen, 2026, gesucht, ende=ende, max_bloecke=1)
pruefe(len(urls) == 2, "zweiter Aufruf holt nur den Restblock (%d Anfragen gesamt)" % len(urls))
pruefe(len(aus) == 118, "danach alle 118 Zellen da (%d)" % len(aus))

print("4. Cachename")
namen = sorted(os.listdir(os.path.join(k.BASIS, "daten", "roh")))
pruefe(namen and all("_bis20261101" in n for n in namen),
       "Teiljahr-Bloecke tragen _bis20261101: %s" % ", ".join(namen))

print("\n%s" % ("Alles gruen." if fehler == 0 else "%d Fehler." % fehler))
sys.exit(1 if fehler else 0)
