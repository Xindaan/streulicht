"""Minimaler GRIB2-Leser fuer die MSG-Wolkenmaske - ohne Fremdbibliothek.

WARUM SELBST GESCHRIEBEN.  Die uebliche Antwort waere `eccodes` plus
`cfgrib`; eccodes ist eine C-Bibliothek mit eigener Installationskette.  Fuer
GENAU EIN Produkt lohnt das nicht: die Wolkenmaske benutzt Packvorlage 5.0
(einfache Packung, 2 Bit je Punkt) und Gittervorlage 3.90 (geostationaere
Sicht).  Beides ist in der WMO-Spezifikation vollstaendig beschrieben und in
rund hundert Zeilen umsetzbar.

GRENZEN, damit niemand mehr erwartet als da ist:
- NUR Packvorlage 5.0 und NUR Gittervorlage 3.90.  Alles andere wirft.
- Keine Bitmap-Behandlung (die Wolkenmaske hat keine, Indikator 255).
- Kein Zeitbezug, keine Ensembles, keine Mehrfachnachrichten je Datei.
Wer ein anderes GRIB2-Produkt einliest, bekommt eine Ausnahme statt stiller
Falschwerte - genau die Fehlerklasse, die dieses Projekt viermal getroffen hat.

Projektion nach CGMS 03, wie sie EUMETSAT fuer SEVIRI verwendet.
"""
import math
import struct

# Erdfigur nach CGMS/SEVIRI
GROSSE_HALBACHSE_KM = 6378.1370
KLEINE_HALBACHSE_KM = 6356.5838
ABSTAND_KM = 42164.0            # Satellit vom Erdmittelpunkt


class NichtUnterstuetzt(Exception):
    pass


def _abschnitte(daten):
    """(Nummer, Bytes) je GRIB2-Sektion der ERSTEN Nachricht in der Datei."""
    o = daten.find(b"GRIB")
    if o < 0:
        raise NichtUnterstuetzt("keine GRIB-Marke gefunden")
    if daten[o + 7] != 2:
        raise NichtUnterstuetzt("GRIB-Edition %d, erwartet 2" % daten[o + 7])
    gesamt = int.from_bytes(daten[o + 8:o + 16], "big")
    i = o + 16
    aus = []
    while i < o + gesamt - 4:
        laenge = int.from_bytes(daten[i:i + 4], "big")
        if laenge <= 0:
            break
        aus.append((daten[i + 4], daten[i:i + laenge]))
        i += laenge
    return aus


def gitter(s3):
    """Parameter der geostationaeren Sicht aus Sektion 3 (Vorlage 3.90).

    Byteposition nach WMO-Spezifikation, dort 1-basiert gezaehlt; hier also
    jeweils eins weniger.  Die Offsets sind der haeufigste Fehler an dieser
    Stelle - ein um drei verschobenes Feld liefert eine Zahl, die plausibel
    aussieht und falsch ist.
    """
    vorlage = int.from_bytes(s3[12:14], "big")
    if vorlage != 90:
        raise NichtUnterstuetzt("Gittervorlage 3.%d, erwartet 3.90" % vorlage)
    g = lambda a, b, vz=False: int.from_bytes(s3[a:b], "big", signed=vz)
    return {
        "nx": g(30, 34), "ny": g(34, 38),
        "lap": g(38, 42, True) / 1e6, "lop": g(42, 46, True) / 1e6,
        "dx": g(47, 51), "dy": g(51, 55),          # Erddurchmesser in Gitterlaengen
        "xp": g(55, 59) / 1000.0, "yp": g(59, 63) / 1000.0,
        "nr": g(68, 72) / 1e6,                     # Kamerahoehe in Erdradien
    }


def werte(daten):
    """(flaches Wertefeld, Gitterparameter).  Nur Packvorlage 5.0."""
    import numpy as np
    s = dict()
    for nr, roh in _abschnitte(daten):
        s.setdefault(nr, roh)
    if 3 not in s or 5 not in s or 7 not in s:
        raise NichtUnterstuetzt("Sektion 3, 5 oder 7 fehlt")

    gp = gitter(s[3])
    s5 = s[5]
    n = int.from_bytes(s5[5:9], "big")
    vorlage = int.from_bytes(s5[9:11], "big")
    if vorlage != 0:
        raise NichtUnterstuetzt("Packvorlage 5.%d, erwartet 5.0" % vorlage)
    R = struct.unpack(">f", s5[11:15])[0]
    E = int.from_bytes(s5[15:17], "big", signed=True)
    D = int.from_bytes(s5[17:19], "big", signed=True)
    bits = s5[19]
    if s[6][5] != 255:
        raise NichtUnterstuetzt("Bitmap vorhanden (Indikator %d)" % s[6][5])

    roh = s[7][5:]
    if bits == 0:
        feld = np.zeros(n, dtype=np.float64)
    else:
        b = np.unpackbits(np.frombuffer(roh, dtype=np.uint8))
        b = b[:n * bits].reshape(n, bits)
        gewicht = (1 << np.arange(bits - 1, -1, -1)).astype(np.int64)
        feld = (b.astype(np.int64) * gewicht).sum(axis=1)
    # Y = (R + X * 2^E) / 10^D
    feld = (R + feld * (2.0 ** E)) / (10.0 ** D)
    if feld.size != gp["nx"] * gp["ny"]:
        raise NichtUnterstuetzt("Werteanzahl %d passt nicht zu %dx%d"
                                % (feld.size, gp["nx"], gp["ny"]))
    return feld, gp


def pixel(lat, lon, gp):
    """Geografische Lage -> (Spalte, Zeile) im geostationaeren Bild.

    CGMS 03.  Rueckgabe None, wenn der Punkt hinter dem Erdrand liegt - das
    ist kein Fehlerfall, sondern Geometrie: von 0 Grad Laenge aus ist etwa
    ab 81 Grad Abstand nichts mehr zu sehen.
    """
    lat_r = math.radians(lat)
    dlon = math.radians(lon - gp["lop"])
    # geodaetisch -> geozentrisch
    verh = (KLEINE_HALBACHSE_KM / GROSSE_HALBACHSE_KM) ** 2
    c_lat = math.atan(verh * math.tan(lat_r))
    rl = KLEINE_HALBACHSE_KM / math.sqrt(
        1.0 - (1.0 - verh) * math.cos(c_lat) ** 2)
    r1 = ABSTAND_KM - rl * math.cos(c_lat) * math.cos(dlon)
    r2 = -rl * math.cos(c_lat) * math.sin(dlon)
    r3 = rl * math.sin(c_lat)
    rn = math.sqrt(r1 * r1 + r2 * r2 + r3 * r3)
    # Sichtbarkeit: der Punkt muss vor der Tangentialebene liegen
    if r1 * (r1 - ABSTAND_KM) + r2 * r2 + r3 * r3 > 0:
        return None
    x = math.atan(-r2 / r1)
    y = math.asin(-r3 / rn)
    # dx ist der Erddurchmesser in Gitterlaengen; daraus die Winkelaufloesung.
    # Der Sehwinkel der Erde vom Satelliten aus ist 2*asin(1/nr).
    winkel_je_pixel = 2.0 * math.asin(1.0 / gp["nr"]) / gp["dx"]
    spalte = gp["xp"] - x / winkel_je_pixel
    zeile = gp["yp"] - y / winkel_je_pixel
    if not (0 <= spalte < gp["nx"] and 0 <= zeile < gp["ny"]):
        return None
    return spalte, zeile


def wert_bei(feld, gp, lat, lon):
    """Wert am geografischen Ort, naechster Nachbar.  None ausserhalb."""
    p = pixel(lat, lon, gp)
    if p is None:
        return None
    spalte, zeile = int(round(p[0])), int(round(p[1]))
    if not (0 <= spalte < gp["nx"] and 0 <= zeile < gp["ny"]):
        return None
    return float(feld[zeile * gp["nx"] + spalte])
