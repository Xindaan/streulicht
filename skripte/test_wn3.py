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

Zu jedem Punkt gehoert unten eine eigene Negativprobe: der Fehler wird
absichtlich eingebaut und es wird nachgewiesen, dass GENAU diese Pruefung
anschlaegt.  Ein Waechter ohne eigenen Fall gilt als ungeprueft.

Lauf:  .venv/bin/python3 skripte/test_wn3.py
"""
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wn3.py")
_s = importlib.util.spec_from_file_location("wn3", _p)
wn3 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(wn3)

fehler = 0


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
pruefe(wn3.geschwindigkeit(3.0, 4.0) == 5.0, "Betrag ist die Hypotenuse")


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

pruefe(wn3.in_region(lambda: "projects/1/zones/us-east1-b") is True,
       "Zone in us-east1 wird als Region erkannt")
pruefe(wn3.in_region(lambda: "projects/1/zones/europe-west3-a") is False,
       "Zone anderswo gilt nicht als Region")
pruefe(wn3.in_region(lambda: "projects/1/zones/us-east1000-a") is False,
       "Praefixtreffer allein genuegt nicht (us-east1000 ist nicht us-east1)")


def _wirft():
    raise OSError("kein Metadatendienst")


pruefe(wn3.in_region(_wirft) is False,
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

_alt_ir = wn3.in_region
wn3.in_region = lambda *a: False
try:
    q_auto = wn3.Quelle("20260908_00hr", lies=leser)
    pruefe(q_auto.budget.frei is False,
           "ohne uebergebenes Budget stellt Quelle selbst fest, wo sie laeuft")
finally:
    wn3.in_region = _alt_ir

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

d = sq.punkte([ZELLE], [INIT + timedelta(hours=2)], schichten=("mid",),
              statistik="p50", melde=lambda *a: None)
pruefe("cloud_cover_mid" in d[ZELLE],
       "Name ist schlicht, ohne Memberkennung")
pruefe(not any("_member" in k for k in d[ZELLE]),
       "keine Reihe gibt sich als Member aus")
pruefe(d[ZELLE]["cloud_cover_mid"][0] == wn3.prozent((1 * 100 + 1 * 10 + 1)
                                                     / 1000.0),
       "Wert an der richtigen Zelle und Stunde")

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
    except Exception:
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


print("\n%s" % ("Alles gruen." if fehler == 0 else "%d Fehler." % fehler))
sys.exit(1 if fehler else 0)
