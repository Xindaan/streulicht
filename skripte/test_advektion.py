"""Offline-Pruefung der Advektionsmechanik - kein Netz noetig.

Drei Dinge, die still falsch sein koennen und dann nicht auffallen:
  1. Windrichtungskonvention (meteorologisch = Richtung, AUS der es weht)
  2. Mittelung von Windrichtungen ueber den Nordsprung hinweg
  3. Wahl des naechsten nativen Schritts zum Sonnenuntergang
  4. Stromauf-Abtastung in ALLE Himmelsrichtungen und das zirkulaere
     Richtungsmittel - beides im PRODUKTIONSLAUF (alarm.main()), nicht in
     einer Nachbildung (T-0079, Review tests#1)
"""
import contextlib
import importlib.util
import io
import json
import math
import os
import sys
import tempfile
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
    else:
        print("   ok    %s" % text)
    return bedingung


print("Windrichtungskonvention")
for ri, sdx, sdy in ((270, +36, 0), (90, -36, 0), (180, 0, +36), (0, 0, -36)):
    dx, dy = alarm.versatz_km(36.0, ri, 1.0)
    pruefe(abs(dx - sdx) < 0.1 and abs(dy - sdy) < 0.1,
           "Richtung %d: erwartet (%+d,%+d), bekommen (%+.1f,%+.1f)"
           % (ri, sdx, sdy, dx, dy))

# Das zirkulaere Richtungsmittel (Nordsprung) wird weiter unten am echten
# Lauf geprueft.  Frueher stand hier eine Kopie der Formel im Test: sie bewies
# nur, dass die Kopie stimmt, und blieb gruen, wenn alarm.py wieder arithmetisch
# mittelte.
# Der arithmetische Mittelwert MUSS fuer die Testfaelle falsch liegen - sonst
# prueft der Lauf unten nichts:
pruefe(abs((350 + 10) / 2 - 0) > 100 and abs((170 + 190) / 2 - 180) < 1,
       "Testfall trifft den Nordsprung: arithmetisch 350/10 -> 180, nicht 0")

print("Naechster nativer Schritt (3-h-Raster)")
z = ["2026-08-15T%02d:00" % h for h in range(0, 24, 3)]
for su in (18.47, 14.90, 17.10, 19.55, 13.05):
    ziel = datetime(2026, 8, 15, tzinfo=timezone.utc) + timedelta(hours=su)
    i, dt = alarm.naechster_schritt(z, ziel)
    pruefe(dt <= 1.5 + 1e-9, "Sonnenuntergang %.2f: |dt| = %.2f h (hoechstens 1.5)" % (su, dt))

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


# WERT-HUERDE (T-0079, tests#1).  Bis hierher lief der Stromauf-Test nur mit
# Westwind und las nur die Laengenrichtung.  Ungeschuetzt waren
#   * das Vorzeichen der Breitenkomponente (`la - dy / 111.32`): ein Plus
#     dort verschiebt Nord-/Suedwind-Abende auf die falsche Seite und laesst
#     den Westwind-Test gruen;
#   * das zirkulaere Richtungsmittel: mittelt alarm.py wieder arithmetisch,
#     wird aus Members bei 350 und 10 Grad ein Mittelwind aus SUED.
# Der Lauf fuehrt alarm.main() mit gestubbtem Abruf aus; gemessen werden
# (a) die Richtung, mit der der Lauf versatz_km() aufruft (Spion um die
# Produktionsfunktion, die echte rechnet weiter), und (b) wohin Pass 2
# tatsaechlich abtastet.
BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMBER = [""] + ["%02d" % n for n in range(1, 51)]

# Das native Raster wird um 1.5 h gegen Mitternacht versetzt, damit der
# Sonnenuntergang moeglichst WEIT von einem Schritt entfernt liegt.  Bei
# einem Raster auf der vollen Stunde ist dt ~ 0.1 h, der Versatz betraegt
# dann wenige Kilometer und bleibt innerhalb einer 0.25-Grad-Zelle - der
# Test koennte die Richtung gar nicht sehen.
RASTERVERSATZ_H = 1.5
WIND_KMH = 60.0


def pass2_lauf(richtung_je_member):
    """alarm.main() mit Wind aus `richtung_je_member(m)` Grad.

    Rueckgabe: dict(wolken=Anzahl Wolkenabrufe, mitte1=(lat, lon) der Zellen
    aus Pass 1, mitte2=(lat, lon) der NEUEN Zellen aus Pass 2,
    richtungen=Gradwerte, mit denen versatz_km aufgerufen wurde)."""
    abrufe, aufrufe = [], []

    def abruf(zellen, variablen, modell, tage, block=25):
        abrufe.append({"zellen": set(zellen), "variablen": list(variablen)})
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
                        w = [float(richtung_je_member(m))] * len(zeiten)
                    else:
                        w = [50.0] * len(zeiten)
                    h[alarm.feldname(v, m)] = w
            aus[z] = h
        return aus

    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "daten"), exist_ok=True)
    kfg = json.load(open(os.path.join(BASIS, "konfig.json")))
    kfg["vorlauf_tage"] = 1
    kp = os.path.join(d, "konfig.json")
    with open(kp, "w") as f:
        json.dump(kfg, f)
    echt_versatz = alarm.versatz_km

    def spion(sp, richtung, stunden):
        aufrufe.append(richtung)
        return echt_versatz(sp, richtung, stunden)

    alt = (alarm.BASIS, alarm.abfrage, alarm.modelllauf,
           alarm.warte_auf_netz, alarm.versatz_km)
    alarm.BASIS = d
    alarm.abfrage = abruf
    alarm.modelllauf = lambda m: "2026-09-02T00:00+00:00"
    alarm.warte_auf_netz = lambda *a_, **k_: None
    alarm.versatz_km = spion
    sicher, sys.argv = sys.argv, ["alarm.py", "--konfig", kp,
                                  "--jetzt", "2026-09-02T06:00"]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            alarm.main()
    finally:
        sys.argv = sicher
        (alarm.BASIS, alarm.abfrage, alarm.modelllauf,
         alarm.warte_auf_netz, alarm.versatz_km) = alt
    wolke = [a for a in abrufe
             if all(v.startswith("cloud_") for v in a["variablen"])]
    erg = {"wolken": len(wolke), "richtungen": aufrufe,
           "mitte1": None, "mitte2": None}
    if len(wolke) >= 2:
        eins = wolke[0]["zellen"]
        neu = wolke[-1]["zellen"] - eins

        def mittel(zs):
            return (sum(alarm.mitte(z)[0] for z in zs) / len(zs),
                    sum(alarm.mitte(z)[1] for z in zs) / len(zs))
        if neu:
            erg["mitte1"], erg["mitte2"] = mittel(eins), mittel(neu)
    return erg


def kreisabstand(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


# 60 km/h ueber gut 1.3 h sind ~80 km, also ~0.7 Grad Breite bzw. ~1.2 Grad
# Laenge: gemessen 0.77 / 1.3.  Ein Versatz unter 0.25 Grad waere ein
# Rundungsartefakt und kein Beleg fuer die Richtung; quer zur Windrichtung
# darf sich der Schwerpunkt kaum bewegen.
FAELLE = (
    # Name, Richtung je Member, Vorzeichen (dlat, dlon) der erwarteten
    # Verschiebung der Abtastung gegen Pass 1.  STROMAUF: bei Wind AUS
    # Westen wird westlich abgetastet.
    ("Wind aus Westen (270)", lambda m: 270, (0, -1)),
    ("Wind aus Osten (90)", lambda m: 90, (0, +1)),
    ("Wind aus Norden (0)", lambda m: 0, (+1, 0)),
    ("Wind aus Sueden (180)", lambda m: 180, (-1, 0)),
    # Zirkulaeres Mittel: 25 Member bei 350, 26 bei 10 Grad -> ~0.2 Grad =
    # Nordwind.  Arithmetisch waeren es 180 Grad, also Suedwind.
    ("Members bei 350/10 Grad -> Nordwind (Nordsprung)",
     lambda m: 350 if int(m or 0) % 2 else 10, (+1, 0)),
    ("Members bei 170/190 Grad -> Suedwind",
     lambda m: 170 if int(m or 0) % 2 else 190, (-1, 0)),
)
SOLL_RICHTUNG = {"Members bei 350/10 Grad -> Nordwind (Nordsprung)": 0.0,
                 "Members bei 170/190 Grad -> Suedwind": 180.0}
for name, richtung, (sl, so) in FAELLE:
    r = pass2_lauf(richtung)
    pruefe(r["wolken"] >= 2 and r["mitte2"] is not None,
           "%s: Pass 2 hat stattgefunden (%d Wolkenabrufe)"
           % (name, r["wolken"]))
    if r["mitte2"] is None:
        continue
    dlat = r["mitte2"][0] - r["mitte1"][0]
    dlon = r["mitte2"][1] - r["mitte1"][1]
    if sl:
        pruefe(sl * dlat > 0.5 and abs(dlon) < 0.2,
               "%s: Pass 2 tastet %s von Pass 1 ab (%+.2f Grad Breite, "
               "%+.2f Grad Laenge)"
               % (name, "NOERDLICH" if sl > 0 else "SUEDLICH", dlat, dlon))
    else:
        pruefe(so * dlon > 0.5 and abs(dlat) < 0.2,
               "%s: Pass 2 tastet %s von Pass 1 ab (%+.2f Grad Breite, "
               "%+.2f Grad Laenge)"
               % (name, "OESTLICH" if so > 0 else "WESTLICH", dlat, dlon))
    if name in SOLL_RICHTUNG:
        soll = SOLL_RICHTUNG[name]
        pruefe(r["richtungen"]
               and all(kreisabstand(x, soll) < 1.0 for x in r["richtungen"]),
               "%s: der Lauf rechnet mit %.0f Grad Mittelwind (%s)"
               % (name, soll, sorted({round(x, 1) for x in r["richtungen"]})))

print("\n%s" % ("alle Pruefungen bestanden" if fehler == 0
                else "%d Pruefung(en) fehlgeschlagen" % fehler))
sys.exit(1 if fehler else 0)
