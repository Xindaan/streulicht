"""Offline-Pruefung des WeatherNext-3-Lesers - kein Netz, kein Kontingent.

Der Leser laeuft in us-east1 und kostet dort echte Chunks; ein Test, der
dafuer Daten holt, waere teuer und langsam.  Also wird `Quelle` mit einem
kuenstlichen Speicher gefuettert, dessen Werte ihre eigenen Indizes
kodieren - dann sagt das ERGEBNIS, ob richtig gegriffen wurde, und nicht
der Quelltext.

Fuenf Dinge, die still falsch sein koennen:
  1. Vorzeichen von `lead_subtime` - ein Versatz von bis zu fuenf Stunden
  2. Laengenumrechnung -180..180 gegen WN3s 0..359,9
  3. Bedeckung 0..1 gegen Open-Meteos 0..100
  4. Windrichtung meteorologisch gegen mathematisch
  5. Wind-Chunks haben eine ANDERE Form als Wolken-Chunks
  6. Windbetrag in km/h (alarm.py), nicht in m/s (WN3) - T-0083, physik#1
  7. Zielzeiten mit Minuten (echte Sonnenuntergaenge) - T-0083, wn3#F4

Der Test ist NETZFREI: `in_region()` ist gestubbt, und `urlopen` sowie
`subprocess` (gcloud, zstd) werfen eine `NetzVerboten`, die kein
`except Exception` verschluckt.  Vorher rief `quelle()` ohne Budget das
echte `in_region()` und damit metadata.google.internal an (wn3#F10).

Zu jedem Punkt gehoert unten eine eigene Negativprobe: der Fehler wird
absichtlich eingebaut und es wird nachgewiesen, dass GENAU diese Pruefung
anschlaegt.  Ein Waechter ohne eigenen Fall gilt als ungeprueft.

Lauf:  .venv/bin/python3 skripte/test_wn3.py
"""
import importlib.util
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

_hier = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _hier)
sys.path.insert(0, os.path.dirname(_hier))
import alarm  # noqa: E402  (nur fuer den Einheitenvertrag, keine Netzzugriffe)

_p = os.path.join(_hier, "wn3.py")
_s = importlib.util.spec_from_file_location("wn3", _p)
wn3 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(wn3)

fehler = 0


# --- Netzsperre --------------------------------------------------------
#
# BaseException, nicht Exception: `in_region()` faengt Exception und
# wuerde einen verbotenen Netzzugriff als "nicht in der Region" schlucken -
# der Test bliebe gruen und haette trotzdem das Netz angefasst.

class NetzVerboten(BaseException):
    pass


def _verboten(*a, **k):
    raise NetzVerboten("Netz-/Prozesszugriff im netzfreien Test")


import urllib.request  # noqa: E402
urllib.request.urlopen = _verboten
wn3.subprocess.run = _verboten
wn3.subprocess.Popen = _verboten

# Das ECHTE in_region bleibt fuer Abschnitt 6 erhalten (dort mit eigener
# `_holen`-Funktion, also ohne Netz); alles andere sieht den Stub.
_echt_in_region = wn3.in_region
_ir_aufrufe = []


def _ir_stub(*a):
    _ir_aufrufe.append(a)
    return False


wn3.in_region = _ir_stub


def pruefe(bedingung, text):
    global fehler
    if not bedingung:
        fehler += 1
        print("  FEHLER: %s" % text)
    else:
        print("  ok: %s" % text)


# --- kuenstlicher Speicher --------------------------------------------
#
# Winzige Achsen, aber dieselbe STRUKTUR wie echte Laeufe: Wolken auf dem
# feinen Gitter mit sechs Stunden je Chunk, Wind auf dem groben Gitter mit
# EINER Stunde je Chunk und der Druckflaeche als eigener Chunkachse.

LAT01 = np.array([52.0, 52.5, 53.0], dtype="<f4")
LON01 = np.array([13.0, 13.5, 357.0], dtype="<f4")
LAT025 = np.array([52.5, 53.0], dtype="<f4")
LON025 = np.array([13.5, 357.0], dtype="<f4")
LEVEL = np.array([300, 600, 925], dtype="<i4")
LEAD = np.array([6, 12, 18], dtype="<i8")
SUB = np.array([-5, -4, -3, -2, -1, 0], dtype="<i8")
SAMPLE = np.array([0, 1], dtype="<i8")

NSUB, NLAT, NLON = 6, len(LAT01), len(LON01)


def _wolkenfeld(member, block):
    """Wert kodiert (Stunde, Breitenindex, Laengenindex) und Herkunft."""
    f = np.zeros((NSUB, NLAT, NLON), dtype="<f4")
    for s in range(NSUB):
        for i in range(NLAT):
            for j in range(NLON):
                f[s, i, j] = (s * 100 + i * 10 + j) / 1000.0
    return f + member * 0.001 + block * 0.0001


def _windfeld(richtung, k):
    """u zeigt nach Osten, v nach Norden - Werte je Druckflaeche eindeutig."""
    f = np.zeros((len(LAT025), len(LON025)), dtype="<f4")
    for i in range(len(LAT025)):
        for j in range(len(LON025)):
            f[i, j] = (1.0 if richtung == "u" else 0.0) + k
    return f


def _meta():
    def arr(shape, dtype):
        return {"shape": list(shape), "data_type": dtype}
    m = {}
    for v in ("low_cloud_cover", "medium_cloud_cover", "high_cloud_cover"):
        m[v] = arr([len(SAMPLE), len(LEAD), NSUB, NLAT, NLON], "float32")
    for v in ("u_component_of_wind", "v_component_of_wind"):
        m[v] = arr([len(SAMPLE), len(LEAD), len(LEVEL),
                    len(LAT025), len(LON025)], "float32")
    return {"consolidated_metadata": {"metadata": m}}


def leser(pfad, entpacken=True):
    """Ersetzt `_lies`: liefert rohe Bytes wie nach dem Auspacken.

    `entpacken` wird hier ignoriert - der kuenstliche Speicher haelt alles
    ungepackt.  Der Parameter muss aber DA sein, sonst weicht die Signatur
    vom echten `_lies` ab und der Test prueft eine Schnittstelle, die es so
    nicht gibt.  Genau daran ist der erste Lauf gegen echte Daten
    gescheitert (zarr.json ist Klartext, Chunks sind zstd).
    """
    rel = pfad.split("predictions.zarr/", 1)[1]
    if rel == "zarr.json":
        return json.dumps(_meta()).encode("utf-8")
    achsen = {"lat_0p1/c/0": LAT01, "lon_0p1/c/0": LON01,
              "lat_0p25/c/0": LAT025, "lon_0p25/c/0": LON025,
              "level/c/0": LEVEL, "lead_time/c/0": LEAD,
              "lead_subtime/c/0": SUB, "sample/c/0": SAMPLE}
    if rel in achsen:
        return achsen[rel].tobytes()
    var, rest = rel.split("/c/", 1)
    teile = [int(x) for x in rest.split("/")]
    if var.endswith("_cloud_cover"):
        return _wolkenfeld(teile[0], teile[1]).tobytes()
    if var.endswith("_component_of_wind"):
        return _windfeld(var[0], teile[2]).tobytes()
    raise KeyError(pfad)


def quelle():
    return wn3.Quelle("20260908_00hr", lies=leser)


UTC = timezone.utc
INIT = datetime(2026, 9, 8, tzinfo=UTC)
ZELLE = (round(52.52 / wn3.GITTER), round(13.405 / wn3.GITTER))   # 52.5/13.5


# --- 1  Zeitachse ------------------------------------------------------

print("\n1  Zeitachse: lead_subtime ist relativ zum BLOCKENDE")
q = quelle()
z = q.zeiten(1)                                   # lead_time[1] = 12 h
pruefe(z[-1] == INIT + timedelta(hours=12),
       "letzte Stunde des Blocks ist init+lead_time (%s)" % z[-1].isoformat())
pruefe(z[0] == INIT + timedelta(hours=7),
       "erste Stunde ist init+lead_time-5 (%s)" % z[0].isoformat())
pruefe([t.hour for t in z] == [7, 8, 9, 10, 11, 12],
       "sechs aufsteigende Stunden, keine Luecke")
pruefe(q.block(INIT + timedelta(hours=9)) == 1,
       "block() findet den Block, der die Zielzeit enthaelt")
# Achtung, hier stand zuerst 13 h - das ist ein TREFFER, nicht eine Luecke:
# lead_time[2]=18 deckt 13..18 h ab.  Die echten Luecken liegen VOR dem
# ersten Block (init selbst, denn Block 0 beginnt bei +1 h) und HINTER dem
# letzten.  Der erste Entwurf dieses Tests waere sonst aus dem falschen
# Grund gruen geworden.
pruefe(q.block(INIT + timedelta(hours=19)) is None,
       "block() meldet None hinter dem Vorlaufende")
pruefe(q.block(INIT) is None,
       "block() meldet None vor dem ersten Block")

# Echte Sonnenuntergaenge haben Minuten (T-0083, wn3#F4): die Achse ist
# stuendlich, also muss die NAECHSTE Stunde gelten, nicht die gleiche.
H = timedelta(hours=1)
M = timedelta(minutes=1)
pruefe(q.block(INIT + 9 * H + 20 * M) == 1,
       "block() nimmt fuer 09:20 die Stunde 09 (Block 1), nicht None")
pruefe(q.block(INIT + 12 * H + 20 * M) == 1,
       "12:20 rundet auf 12 und bleibt im Block 1")
pruefe(q.block(INIT + 12 * H + 40 * M) == 2,
       "12:40 rundet auf 13 und landet im Block 2 (Blockgrenze)")
pruefe(q.block(INIT + 18 * H + 20 * M) == 2,
       "18:20 hinter dem letzten Schritt, aber in der Toleranz: Block 2")
pruefe(q.block(INIT + 18 * H + 40 * M) is None,
       "18:40 liegt zu weit hinter dem Vorlauf: None")
pruefe(q.block(INIT + 40 * M) == 0 and q.block(INIT + 20 * M) is None,
       "vor dem ersten Schritt gilt dieselbe Toleranz (00:40 ja, 00:20 nein)")

meldungen = []
d_min = wn3.abfrage(quelle(), [ZELLE], [INIT + 9 * H + 20 * M],
                    schichten=("high",), member=[0],
                    melde=lambda t: meldungen.append(t))
d_voll = wn3.abfrage(quelle(), [ZELLE], [INIT + 9 * H],
                     schichten=("high",), member=[0], melde=lambda *a: None)
pruefe(d_min[ZELLE] == d_voll[ZELLE] and len(d_min[ZELLE]["time"]) == 6,
       "abfrage() mit 09:20 liefert denselben Block wie mit 09:00")
pruefe(not any("Ausserhalb" in m for m in meldungen),
       "und meldet 09:20 nicht als 'Ausserhalb des Vorlaufs'")
meldungen = []
d_aus = wn3.abfrage(quelle(), [ZELLE], [INIT + 19 * H],
                    schichten=("high",), member=[0],
                    melde=lambda t: meldungen.append(t))
pruefe(d_aus[ZELLE]["time"] == [] and any("Ausserhalb" in m for m in meldungen),
       "was wirklich hinter dem Vorlauf liegt, wird weiter gemeldet")

# Bei groesserer Toleranz gewinnt die NAECHSTE Stunde, nicht die erste im
# Toleranzfenster.  Bei 0,5 h gibt es nie zwei Kandidaten; erst eine weite
# Toleranz macht den Unterschied sichtbar.
_alt_tol = wn3.ZEIT_TOLERANZ_H
wn3.ZEIT_TOLERANZ_H = 3.0
try:
    pruefe(q.block(INIT + 12 * H + 40 * M) == 2,
           "mit weiter Toleranz gewinnt die naechste Stunde (13:00, Block 2)"
           " statt der ersten im Fenster")
finally:
    wn3.ZEIT_TOLERANZ_H = _alt_tol


# --- 2  Gitter und Laenge ---------------------------------------------

print("\n2  Gitter: Laengen -180..180 gegen WN3s 0..359,9")
pruefe(wn3._index(LON01, wn3._laenge(-3.0)) == 2,
       "-3,0 Grad trifft 357,0 (Index 2), nicht 13,0")
pruefe(wn3._index(LON01, wn3._laenge(13.5)) == 1,
       "13,5 Grad trifft 13,5 (Index 1)")
pruefe(wn3._index(LAT01, 52.52) == 1,
       "52,52 trifft die naechste Breite 52,5")


# --- 3  Bedeckung ------------------------------------------------------

print("\n3  Bedeckung: WN3 fuehrt 0..1, alarm.py erwartet 0..100")
d = wn3.abfrage(quelle(), [ZELLE], [INIT + timedelta(hours=9)],
                schichten=("high",), member=[0], melde=lambda *a: None)
reihe = d[ZELLE]["cloud_cover_high_member00"]
# Zelle 52,5/13,5 -> i=1, j=1; Block 1; Stunde 9 ist subtime-Index 2.
erwartet = wn3.prozent((2 * 100 + 1 * 10 + 1) / 1000.0 + 0.0001)
pruefe(reihe[2] == erwartet,
       "Wert an der richtigen Zelle und Stunde: %s (erwartet %s)"
       % (reihe[2], erwartet))
pruefe(max(reihe) > 1.0,
       "Reihe liegt in Prozent, nicht in Anteilen (max %s)" % max(reihe))
pruefe(len(reihe) == len(d[ZELLE]["time"]) == 6,
       "Reihe und Zeitachse sind gleich lang")


# --- 4  Windrichtung ---------------------------------------------------

print("\n4  Wind: meteorologische Richtung, aus der es weht")
pruefe(wn3.richtung(1.0, 0.0) == 270.0, "Wind nach Osten kommt aus West (270)")
pruefe(wn3.richtung(0.0, 1.0) == 180.0, "Wind nach Norden kommt aus Sued (180)")
pruefe(wn3.geschwindigkeit(3.0, 4.0) == 18.0,
       "Betrag ist die Hypotenuse in km/h (5 m/s = 18 km/h)")


# --- 4b  Einheit: km/h wie bei Open-Meteo ------------------------------

print("\n4b Wind: die Reihe in der Open-Meteo-Form ist km/h")
# Erwartung aus der Physik, nicht aus wn3: Schicht mid = 600 hPa = Index 1
# im Test-Speicher -> u = 2 m/s (nach Osten), v = 1 m/s (nach Norden).
# Eine Stunde Wind traegt die Luft 7,2 km nach Osten und 3,6 km nach Norden.
# Das Ergebnis geht durch alarm.versatz_km - den Verbraucher, der km/h
# erwartet - und nicht durch einen Vergleich mit wn3s eigener Formel.
d = wn3.abfrage(quelle(), [ZELLE], [INIT + timedelta(hours=9)],
                schichten=("mid",), member=[0], wind_zelle=ZELLE,
                melde=lambda *a: None)
sp = d[ZELLE]["wind_speed_600hPa_member00"][2]
ri = d[ZELLE]["wind_direction_600hPa_member00"][2]


dx, dy = alarm.versatz_km(sp, ri, 1.0)
pruefe(abs(sp - math.hypot(2.0, 1.0) * 3.6) < 0.01,
       "wind_speed ist %.2f km/h (erwartet %.2f)"
       % (sp, math.hypot(2.0, 1.0) * 3.6))
pruefe(abs(dx - 7.2) < 0.05 and abs(dy - 3.6) < 0.05,
       "alarm.versatz_km: 1 h Wind traegt die Luft (%.2f, %.2f) km, "
       "erwartet (7,2 / 3,6)" % (dx, dy))


# --- 5  Wind-Chunks haben eine andere Form ----------------------------

print("\n5  Wind: eigene Chunkform und nur EINE Zelle")
d = wn3.abfrage(quelle(), [ZELLE], [INIT + timedelta(hours=9)],
                schichten=("high",), member=[0], wind_zelle=ZELLE,
                melde=lambda *a: None)
pruefe("wind_speed_300hPa_member00" in d[ZELLE],
       "Wind haengt an der angeforderten Zelle")
pruefe(len(d[ZELLE]["wind_speed_300hPa_member00"]) == 6,
       "Windreihe ist auf die sechs Stunden des Blocks gestreckt")
d2 = wn3.abfrage(quelle(), [ZELLE], [INIT + timedelta(hours=9)],
                 schichten=("high",), member=[0], melde=lambda *a: None)
pruefe(not any(k.startswith("wind_") for k in d2[ZELLE]),
       "ohne wind_zelle wird kein Wind geholt")


# --- Negativproben -----------------------------------------------------
#
# Je Waechter EINE, und jede entfernt genau einen Schutz.  Bestehen sie,
# ist bewiesen, dass die Pruefung oben nicht aus einem anderen Grund
# gruen war.

# --- 6  Kostenriegel ---------------------------------------------------
#
# Der teuerste denkbare Fehler ist kein Rechenfehler, sondern ein
# Massenabruf am falschen Ort: 223 GB kosten in us-east1 nichts und ueber
# das Internet rund 27 USD.  Der Riegel darf deshalb nicht davon abhaengen,
# dass jemand aufpasst.
#
# ACHTUNG: dieser Abschnitt laeuft ausschliesslich gegen den kuenstlichen
# Speicher.  Das ist kein Zufall - in der Negativprobe unten FAELLT der
# Riegel weg, und ein Testkoerper, der sich auf ihn verlassen wuerde, haette
# dann echte Chunks gezogen.

print("\n6  Kostenriegel: Massenabruf nur in der Region")

pruefe(_echt_in_region(lambda: "projects/1/zones/us-east1-b") is True,
       "Zone in us-east1 wird als Region erkannt")
pruefe(_echt_in_region(lambda: "projects/1/zones/europe-west3-a") is False,
       "Zone anderswo gilt nicht als Region")
pruefe(_echt_in_region(lambda: "projects/1/zones/us-east1000-a") is False,
       "Praefixtreffer allein genuegt nicht (us-east1000 ist nicht us-east1)")


def _wirft():
    raise OSError("kein Metadatendienst")


pruefe(_echt_in_region(_wirft) is False,
       "kein Metadatendienst -> False, nicht Absturz")

eng = wn3.Budget(frei=False, grenze_mb=0)
try:
    wn3.Quelle("20260908_00hr", lies=leser, budget=eng)
    ok = False
except wn3.Budgetueberschreitung:
    ok = True
pruefe(ok, "ausserhalb der Region bricht schon das Einlesen der Achsen ab")

weit = wn3.Budget(frei=True, grenze_mb=0)
wn3.Quelle("20260908_00hr", lies=leser, budget=weit)
pruefe(weit.bytes > 0, "in der Region wird gezaehlt, aber nicht gebremst")

# Der eigentliche Nachweis: haelt der Riegel VOR der Uebertragung?
# Ein Riegel, der erst hinterher bucht, hat schon bezahlt.  Genau so war
# die erste Fassung, und es ist nur aufgefallen, weil die Meldung "148 MB
# geholt" bei einer Grenze von 1 MB auftauchte.
geholt = []


def zaehlleser(pfad, entpacken=True):
    if "/c/" in pfad and "cloud_cover" in pfad:
        geholt.append(pfad)
    return leser(pfad, entpacken)


q_eng = wn3.Quelle("20260908_00hr", lies=zaehlleser,
                   budget=wn3.Budget(frei=False, grenze_mb=99))
q_eng.budget.bytes = q_eng.budget.grenze          # Budget aufgebraucht
try:
    q_eng.wolke("high", 0, 1)
    warf = False
except wn3.Budgetueberschreitung:
    warf = True
pruefe(warf, "erschoepftes Budget bricht den Chunkabruf ab")
pruefe(geholt == [],
       "und zwar OHNE zu uebertragen (%d Chunks geholt, erwartet 0)"
       % len(geholt))

# Ohne uebergebenes Budget fragt Quelle selbst, wo sie laeuft.  Beide
# Antworten werden eingespielt (gestubbt, ohne Netz), damit das Ergebnis
# wirklich aus der Frage kommt und nicht aus einem festen Wert.
_alt_ir = wn3.in_region
try:
    wn3.in_region = lambda *a: False
    q_aus = wn3.Quelle("20260908_00hr", lies=leser)
    wn3.in_region = lambda *a: True
    q_drin = wn3.Quelle("20260908_00hr", lies=leser)
finally:
    wn3.in_region = _alt_ir
pruefe(q_aus.budget.frei is False and q_drin.budget.frei is True,
       "ohne uebergebenes Budget stellt Quelle selbst fest, wo sie laeuft")

# Die Netzsperre dieses Tests muss selbst halten.  Das echte in_region()
# MIT Netzpfad (ohne `_holen`) wuerde urlopen aufrufen - hier verboten.
try:
    _echt_in_region()
    ok = False
except NetzVerboten:
    ok = True
pruefe(ok, "Netzsperre: das echte in_region() erreicht urlopen nicht")
try:
    wn3.Quelle("20260908_00hr", budget=wn3.Budget(frei=False))
    ok = False
except NetzVerboten:
    ok = True
pruefe(ok, "Netzsperre: ohne gestubbtes `lies` startet kein gcloud-Prozess")
pruefe(len(_ir_aufrufe) > 0,
       "und die Tests oben liefen ueber den Stub (%d Aufrufe), nicht ueber "
       "das Netz" % len(_ir_aufrufe))

# --- 7  Statistik-Quelle ----------------------------------------------

print("\n7  Statistik-Quelle: andere Form, kein Member, kostenlos")

STAT_LEAD = np.array([1, 2, 3], dtype="<i8")


def _statmeta():
    m = {}
    for v in ("low_cloud_cover", "medium_cloud_cover", "high_cloud_cover"):
        for st in ("mean", "p10", "p25", "p50", "p75", "p90"):
            m["%s_%s" % (v, st)] = {"shape": [len(STAT_LEAD), NLAT, NLON],
                                    "data_type": "float32"}
    return {"consolidated_metadata": {"metadata": m}}


def statleser(pfad, entpacken=True):
    rel = pfad.split("predictions.zarr/", 1)[1]
    if rel == "zarr.json":
        return json.dumps(_statmeta()).encode("utf-8")
    achsen = {"lat_0p1/c/0": LAT01, "lon_0p1/c/0": LON01,
              "lead_time/c/0": STAT_LEAD}
    if rel in achsen:
        return achsen[rel].tobytes()
    var, rest = rel.split("/c/", 1)
    i = int(rest.split("/")[0])
    f = np.zeros((NLAT, NLON), dtype="<f4")
    for a in range(NLAT):
        for b in range(NLON):
            f[a, b] = (i * 100 + a * 10 + b) / 1000.0
    return f.tobytes()


def statquelle():
    return wn3.Statistik("20260908_00hr", lies=statleser)


sq = statquelle()
pruefe(sq.zeiten()[0] == INIT + timedelta(hours=1),
       "Stunde 1 ist init+1 - hier gibt es KEIN lead_subtime")
pruefe(sq.schritt(INIT + timedelta(hours=2)) == 1, "schritt() trifft")
pruefe(sq.schritt(INIT + timedelta(hours=9)) is None,
       "schritt() meldet None ausserhalb des Vorlaufs")
pruefe(sq.schritt(INIT + 2 * H + 25 * M) == 1
       and sq.schritt(INIT + 2 * H + 35 * M) == 2,
       "schritt() nimmt die naechste Stunde (02:25 -> 02, 02:35 -> 03)")
pruefe(sq.schritt(INIT + 3 * H + 25 * M) == 2
       and sq.schritt(INIT + 3 * H + 35 * M) is None,
       "hinter dem letzten Schritt gilt die Toleranz (03:25 ja, 03:35 nein)")
pruefe(sq.schritt(INIT + 40 * M) == 0 and sq.schritt(INIT + 20 * M) is None,
       "vor dem ersten Schritt ebenso (00:40 ja, 00:20 nein)")
_alt_tol = wn3.ZEIT_TOLERANZ_H
wn3.ZEIT_TOLERANZ_H = 3.0
try:
    pruefe(sq.schritt(INIT + 2 * H + 25 * M) == 1
           and sq.schritt(INIT + 2 * H + 35 * M) == 2,
           "mit weiter Toleranz gewinnt die naechste Stunde, nicht die erste")
finally:
    wn3.ZEIT_TOLERANZ_H = _alt_tol

d = sq.punkte([ZELLE], [INIT + timedelta(hours=2)], schichten=("mid",),
              statistik="p50", melde=lambda *a: None)
pruefe("cloud_cover_mid" in d[ZELLE],
       "Name ist schlicht, ohne Memberkennung")
pruefe(not any("_member" in k for k in d[ZELLE]),
       "keine Reihe gibt sich als Member aus")
pruefe(d[ZELLE]["cloud_cover_mid"][0] == wn3.prozent((1 * 100 + 1 * 10 + 1)
                                                     / 1000.0),
       "Wert an der richtigen Zelle und Stunde")

d_min = sq.punkte([ZELLE], [INIT + 2 * H + 20 * M], schichten=("mid",),
                  statistik="p50", melde=lambda *a: None)
pruefe(d_min[ZELLE]["cloud_cover_mid"] == d[ZELLE]["cloud_cover_mid"]
       and len(d_min[ZELLE]["time"]) == 1,
       "punkte() mit 02:20 liefert dieselbe Stunde wie mit 02:00")

try:
    sq.punkte([ZELLE], [INIT + timedelta(hours=2)], statistik="p42",
              melde=lambda *a: None)
    ok = False
except ValueError:
    ok = True
pruefe(ok, "unbekannte Statistik wird abgewiesen, nicht stillschweigend leer")

pruefe(statquelle().budget.grenze == wn3.STAT_BUDGET_MB * 1024 * 1024,
       "Statistik hat ihre eigene Reissleine, nicht den Regionsriegel")

print("\n8  Negativproben: jeder Fehler einzeln eingebaut")


def negativ(text, kaputt, pruefung):
    """kaputt() baut den Fehler ein, pruefung() muss dann False liefern."""
    global fehler
    sicher = kaputt()
    try:
        ok = pruefung()
    except (Exception, NetzVerboten):
        ok = False
    finally:
        sicher()
    if ok:
        fehler += 1
        print("  FEHLER: %s - Test blieb gruen OHNE den Schutz" % text)
    else:
        print("  ok: %s - schlaegt an" % text)


def _sub_vorzeichen():
    alt = wn3.Quelle.zeiten

    def falsch(self, i):
        ende = self.init + timedelta(hours=int(self.lead[i]))
        return [ende - timedelta(hours=int(s)) for s in self.sub]   # Vorzeichen
    wn3.Quelle.zeiten = falsch
    return lambda: setattr(wn3.Quelle, "zeiten", alt)


negativ("1 Vorzeichen von lead_subtime", _sub_vorzeichen,
        lambda: quelle().zeiten(1)[0] == INIT + timedelta(hours=7))


def _laenge_ohne_modulo():
    alt = wn3._laenge
    wn3._laenge = lambda lon: lon
    return lambda: setattr(wn3, "_laenge", alt)


negativ("2 Laengenumrechnung", _laenge_ohne_modulo,
        lambda: wn3._index(LON01, wn3._laenge(-3.0)) == 2)


def _prozent_ohne_faktor():
    alt = wn3.prozent
    wn3.prozent = lambda x: None if x != x else round(float(x), 1)
    return lambda: setattr(wn3, "prozent", alt)


def _prozentprobe():
    d = wn3.abfrage(quelle(), [ZELLE], [INIT + timedelta(hours=9)],
                    schichten=("high",), member=[0], melde=lambda *a: None)
    return max(d[ZELLE]["cloud_cover_high_member00"]) > 1.0


negativ("3 Prozentumrechnung", _prozent_ohne_faktor, _prozentprobe)


def _richtung_mathematisch():
    alt = wn3.richtung
    import math as _m
    wn3.richtung = lambda u, v: round(_m.degrees(_m.atan2(v, u)) % 360.0, 1)
    return lambda: setattr(wn3, "richtung", alt)


negativ("4 Windrichtungskonvention", _richtung_mathematisch,
        lambda: wn3.richtung(1.0, 0.0) == 270.0)


def _wind_wie_wolke():
    alt = wn3.Quelle.wind

    def falsch(self, richtung, hpa, member, i):
        var = "%s_component_of_wind" % richtung
        k = int(list(self.level).index(hpa))
        n_lat, n_lon = self.form(var)[3:]
        b = self._roh("%s/c/%d/%d/%d/0/0" % (var, member, i, k))
        # Wolkenform unterstellt: sechs Stunden statt einer
        return np.frombuffer(b, dtype="<f4").reshape(6, n_lat, n_lon)
    wn3.Quelle.wind = falsch
    return lambda: setattr(wn3.Quelle, "wind", alt)


def _windprobe():
    d = wn3.abfrage(quelle(), [ZELLE], [INIT + timedelta(hours=9)],
                    schichten=("high",), member=[0], wind_zelle=ZELLE,
                    melde=lambda *a: None)
    return len(d[ZELLE]["wind_speed_300hPa_member00"]) == 6


negativ("5 Chunkform des Windes", _wind_wie_wolke, _windprobe)


def _riegel_aus():
    alt = wn3.Budget.bucht
    wn3.Budget.bucht = lambda self, n: None
    return lambda: setattr(wn3.Budget, "bucht", alt)


def _riegelprobe():
    """Ohne Riegel laeuft das Einlesen durch - MIT Riegel wirft es."""
    eng = wn3.Budget(frei=False, grenze_mb=0)
    try:
        wn3.Quelle("20260908_00hr", lies=leser, budget=eng)
        return False
    except wn3.Budgetueberschreitung:
        return True


negativ("6 Kostenriegel", _riegel_aus, _riegelprobe)


def _statzeit_falsch():
    alt = wn3.Statistik.zeiten
    wn3.Statistik.zeiten = lambda self: [
        self.init + timedelta(hours=int(h) - 1) for h in self.lead]
    return lambda: setattr(wn3.Statistik, "zeiten", alt)


negativ("7 Zeitrechnung der Statistik", _statzeit_falsch,
        lambda: statquelle().zeiten()[0] == INIT + timedelta(hours=1))


def _statistik_ungeprueft():
    alt = wn3.Statistik.punkte
    stat = wn3.Statistik.STATISTIKEN
    wn3.Statistik.STATISTIKEN = tuple(list(stat) + ["p42"])
    return lambda: setattr(wn3.Statistik, "STATISTIKEN", stat)


def _statistikprobe():
    try:
        statquelle().punkte([ZELLE], [INIT + timedelta(hours=2)],
                            statistik="p42", melde=lambda *a: None)
        return False
    except ValueError:
        return True
    except Exception:
        # KeyError aus den Metadaten waere ein ANDERER Grund - der Test
        # darf nicht aus Versehen gruen werden.
        return False


negativ("8 Pruefung der Statistikwahl", _statistik_ungeprueft,
        _statistikprobe)


def _kmh_ohne_faktor():
    alt = wn3.geschwindigkeit
    wn3.geschwindigkeit = lambda u, v: round(math.hypot(float(u), float(v)), 2)
    return lambda: setattr(wn3, "geschwindigkeit", alt)


def _kmhprobe():
    d = wn3.abfrage(quelle(), [ZELLE], [INIT + 9 * H], schichten=("mid",),
                    member=[0], wind_zelle=ZELLE, melde=lambda *a: None)
    dx, dy = alarm.versatz_km(d[ZELLE]["wind_speed_600hPa_member00"][2],
                              d[ZELLE]["wind_direction_600hPa_member00"][2],
                              1.0)
    return abs(dx - 7.2) < 0.05 and abs(dy - 3.6) < 0.05


negativ("9 Einheit km/h (Faktor 3,6)", _kmh_ohne_faktor, _kmhprobe)


def _block_gleichheit():
    alt = wn3.Quelle.block

    def falsch(self, ziel):                       # der alte Stand
        for i in range(len(self.lead)):
            if ziel in self.zeiten(i):
                return i
        return None
    wn3.Quelle.block = falsch
    return lambda: setattr(wn3.Quelle, "block", alt)


negativ("10 Toleranz in block()", _block_gleichheit,
        lambda: quelle().block(INIT + 9 * H + 20 * M) == 1)


def _schritt_gleichheit():
    alt = wn3.Statistik.schritt

    def falsch(self, ziel):                       # der alte Stand
        for i, t in enumerate(self.zeiten()):
            if t == ziel:
                return i
        return None
    wn3.Statistik.schritt = falsch
    return lambda: setattr(wn3.Statistik, "schritt", alt)


negativ("11 Toleranz in schritt()", _schritt_gleichheit,
        lambda: statquelle().schritt(INIT + 2 * H + 25 * M) == 1)


def _toleranz_unbegrenzt():
    alt = wn3.ZEIT_TOLERANZ_H
    wn3.ZEIT_TOLERANZ_H = 1e6
    return lambda: setattr(wn3, "ZEIT_TOLERANZ_H", alt)


negativ("12 Toleranzgrenze (hinter dem Vorlauf bleibt None)",
        _toleranz_unbegrenzt,
        lambda: quelle().block(INIT + 18 * H + 40 * M) is None
        and statquelle().schritt(INIT + 3 * H + 35 * M) is None)


def _erste_im_fenster():
    alt_b, alt_s = wn3.Quelle.block, wn3.Statistik.schritt

    def block(self, ziel):                  # erste Stunde im Fenster, nicht naechste
        for i in range(len(self.lead)):
            for t in self.zeiten(i):
                if abs((t - ziel).total_seconds()) / 3600.0 <= wn3.ZEIT_TOLERANZ_H:
                    return i
        return None

    def schritt(self, ziel):
        for i, t in enumerate(self.zeiten()):
            if abs((t - ziel).total_seconds()) / 3600.0 <= wn3.ZEIT_TOLERANZ_H:
                return i
        return None
    wn3.Quelle.block, wn3.Statistik.schritt = block, schritt

    def zurueck():
        wn3.Quelle.block, wn3.Statistik.schritt = alt_b, alt_s
    return zurueck


def _naechsteprobe():
    alt = wn3.ZEIT_TOLERANZ_H
    wn3.ZEIT_TOLERANZ_H = 3.0
    try:
        return (quelle().block(INIT + 12 * H + 40 * M) == 2
                and statquelle().schritt(INIT + 2 * H + 35 * M) == 2)
    finally:
        wn3.ZEIT_TOLERANZ_H = alt


negativ("13 naechste statt erste Stunde im Toleranzfenster",
        _erste_im_fenster, _naechsteprobe)


def _stub_weg():
    alt = wn3.in_region
    wn3.in_region = _echt_in_region
    return lambda: setattr(wn3, "in_region", alt)


negativ("14 Netzfreiheit (in_region ohne Stub wuerde urlopen rufen)",
        _stub_weg, lambda: quelle() is not None)


print("\n%s" % ("Alles gruen." if fehler == 0 else "%d Fehler." % fehler))
sys.exit(1 if fehler else 0)
