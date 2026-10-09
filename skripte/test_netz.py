"""netz.warte_auf_netz: die Frist laeuft an der WANDUHR (T-0070, T-0079/tests#8).

WERT-HUERDE.  Geschuetzt wird eine einzige, teure Eigenschaft: die zugesagte
Frist ("bis zu 20 Minuten") gilt in Minuten an der Wand, nicht in Minuten, die
der Rechner wach war.  `time.monotonic()` steht auf macOS im Ruhezustand still;
schlaeft der Mac mitten im Warten ein, wurden am 01.09.2026 aus 20 Minuten
real 29.  Regression, die diesen Test rot macht: jemand stellt die Fristrechnung
auf `time.monotonic()` zurueck (der naheliegende "Aufraeum"-Umbau).  Kein
anderer Test fuehrt die Funktion aus: alle ersetzen sie durch ein Lambda.

Namensaufloesung, Uhr und Schlaf sind Attrappen - kein Netz, keine echte
Wartezeit.  Die Uhr-Attrappe bildet den Ruhezustand nach: `monotonic()` steht
STILL, `time()` laeuft weiter.  Eine Fristrechnung ueber monotonic wuerde
endlos warten; der Test bricht darum nach MAX_SCHLAF Schlafaufrufen mit einem
Befund ab, statt zu haengen.

Lauf:  .venv/bin/python3 skripte/test_netz.py
"""
import os
import socket
import sys
import types

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))

import netz  # noqa: E402

fehler = []
MAX_SCHLAF = 500


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


class Endlos(Exception):
    """Die Funktion wartet unbegrenzt - Befund, kein Testabsturz."""


def fahre(aufloesen_ab=None, minuten=20, pause=30, ruhezustand_s=0,
          ruhe_beim_schlaf=1, name=None):
    """warte_auf_netz() mit Attrappen fahren.

    aufloesen_ab:  Wanduhr-Sekunde, ab der die Namensaufloesung gelingt
                   (None = nie).
    ruhezustand_s: so viele Sekunden springt die Wanduhr waehrend des
                   `ruhe_beim_schlaf`-ten Schlafs ZUSAETZLICH (der Mac
                   schlaeft ein); monotonic() bleibt dabei stehen.
    Rueckgabe: dict(ergebnis, meldungen, schlaefe, aufgeloest_name, wand).
    """
    uhr = {"wand": 1000.0, "mono": 50.0}
    prot = {"schlaefe": [], "namen": [], "meldungen": []}

    def zeit():
        return uhr["wand"]

    def monotonic():
        # steht still, solange der Rechner schlaeft - hier: immer, die
        # Attrappe tickt nur ueber den (wachen) Schlafaufruf, nie darueber
        # hinaus.  Der Ruhezustand addiert nichts.
        return uhr["mono"]

    def schlaf(s):
        prot["schlaefe"].append(s)
        if len(prot["schlaefe"]) > MAX_SCHLAF:
            raise Endlos()
        uhr["wand"] += s
        uhr["mono"] += s            # wach verbrachte Zeit zaehlt auch dort
        if len(prot["schlaefe"]) == ruhe_beim_schlaf and ruhezustand_s:
            uhr["wand"] += ruhezustand_s      # Ruhezustand: nur die Wand

    def getaddrinfo(host, port, *a, **k):
        prot["namen"].append((host, port))
        if aufloesen_ab is not None and uhr["wand"] - 1000.0 >= aufloesen_ab:
            return [("ok",)]
        raise socket.gaierror(8, "nodename nor servname provided")

    echt = (netz.time, netz.socket)
    netz.time = types.SimpleNamespace(time=zeit, monotonic=monotonic,
                                      sleep=schlaf)
    netz.socket = types.SimpleNamespace(
        getaddrinfo=getaddrinfo, gaierror=socket.gaierror,
        IPPROTO_TCP=socket.IPPROTO_TCP)
    kw = dict(minuten=minuten, pause=pause, melde=prot["meldungen"].append)
    if name:
        kw["name"] = name
    try:
        try:
            erg = netz.warte_auf_netz(**kw)
        except Endlos:
            erg = "ENDLOS"
    finally:
        netz.time, netz.socket = echt
    prot.update(ergebnis=erg, wand=uhr["wand"] - 1000.0)
    return prot


print("1. Netz sofort da")
p = fahre(aufloesen_ab=0)
pruefe(p["ergebnis"] is True and not p["schlaefe"],
       "True, ohne zu schlafen (%r, %d Schlaefe)"
       % (p["ergebnis"], len(p["schlaefe"])))
pruefe(p["meldungen"] == [], "und ohne Meldung (%s)" % p["meldungen"])
pruefe(p["namen"] and p["namen"][0] == (netz.PROBE, 443),
       "es wird %s auf Port 443 aufgeloest (%s)" % (netz.PROBE, p["namen"][:1]))
p = fahre(aufloesen_ab=0, name="beispiel.invalid")
pruefe(p["namen"][0][0] == "beispiel.invalid",
       "der Name ist ein Parameter (%s)" % (p["namen"][:1],))

print("\n2. Netz kommt nach einer Weile")
p = fahre(aufloesen_ab=100, pause=30)
pruefe(p["ergebnis"] is True, "True, sobald aufgeloest wird (%r)"
       % (p["ergebnis"],))
pruefe(p["schlaefe"] == [30, 30, 30, 30],
       "geschlafen wird in Schritten von `pause` (%s)" % p["schlaefe"])
pruefe(len(p["meldungen"]) == 2 and "Warte bis zu 20 Minuten" in
       p["meldungen"][0] and "Netz ist da" in p["meldungen"][1],
       "Meldungen: erst Warten (einmal), dann 'Netz ist da' (%s)"
       % p["meldungen"])

print("\n3. Netz kommt nie: nach der Frist False, trotz allem")
p = fahre(aufloesen_ab=None, minuten=20, pause=30)
pruefe(p["ergebnis"] is False, "False nach Fristablauf (%r)" % (p["ergebnis"],))
pruefe(1200 <= p["wand"] <= 1230,
       "nach 20 Wandminuten, nicht frueher und nicht viel spaeter "
       "(%.0f s)" % p["wand"])
pruefe("Kein Netz nach 20 Minuten" in p["meldungen"][-1],
       "die Schlussmeldung nennt die Frist (%s)" % p["meldungen"][-1:])
p = fahre(aufloesen_ab=None, minuten=1, pause=10)
pruefe(p["ergebnis"] is False and 60 <= p["wand"] <= 70,
       "`minuten` wird beachtet: 1 Minute (%.0f s)" % p["wand"])

print("\n4. Ruhezustand mitten im Warten: die Wanduhr zaehlt (T-0070)")
# Der Mac schlaeft waehrend des zweiten Schlafs 25 Minuten.  Wanduhr: die
# Frist ist danach um.  monotonic haette stillgestanden und weiter gewartet.
p = fahre(aufloesen_ab=None, minuten=20, pause=30, ruhezustand_s=25 * 60,
          ruhe_beim_schlaf=2)
pruefe(p["ergebnis"] is False,
       "nach dem Ruhezustand ist die Frist um: False, nicht endlos (%r)"
       % (p["ergebnis"],))
pruefe(len(p["schlaefe"]) == 2 and p["wand"] < 1600,
       "es wird NICHT weitergewartet: %d Schlaefe, %.0f Wandsekunden "
       "(eine Fristrechnung ueber monotonic braeuchte 40 Schlaefe und "
       "~2700 s)" % (len(p["schlaefe"]), p["wand"]))
pruefe(len(p["meldungen"]) == 2 and "Kein Netz nach 20 Minuten"
       in p["meldungen"][-1], "mit Schlussmeldung (%s)" % p["meldungen"])
# Gegenprobe: ein kurzer Ruhezustand (Frist nicht um) bricht nichts ab.
p = fahre(aufloesen_ab=4 * 60, minuten=20, pause=30, ruhezustand_s=60,
          ruhe_beim_schlaf=2)
pruefe(p["ergebnis"] is True,
       "kuerzerer Ruhezustand: es wird weitergewartet, Netz kommt (%r)"
       % (p["ergebnis"],))

print()
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
