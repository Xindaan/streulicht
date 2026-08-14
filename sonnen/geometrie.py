"""Sonnenstand und Strahlgeometrie.

Zwei Dinge:
  (1) Wann und in welchem Azimut geht die Sonne unter (NOAA-Algorithmus).
  (2) Welches Druckniveau blockiert den Beleuchtungsstrahl in welcher Entfernung.

Zu (2): Ein Strahl, der bei Sonnenuntergang eine Wolke in Hoehe h ueber dem
Beobachter beleuchtet, beruehrt die Erdoberflaeche in der Entfernung
D = sqrt(2*R_eff*h) und verlaeuft bei Entfernung d in der Hoehe
z(d) = (D-d)^2 / (2*R_eff).  R_eff = 4/3*R beruecksichtigt die Refraktion
naeherungsweise; bei bodennahen Inversionen ist das eher eine Unter- als eine
Ueberschaetzung (Groessenordnung 10 %).
"""
import math
from datetime import date as _date

R_ERDE_KM = 6371.0
R_EFF_KM = 4.0 / 3.0 * R_ERDE_KM  # 8494.7 km, Standardrefraktion
HOEHE_SONNENUNTERGANG_GRAD = -0.833  # Sonnenoberkante plus Refraktion


def _julianischer_tag(tag: _date) -> float:
    y, m, d = tag.year, tag.month, tag.day
    if m <= 2:
        y, m = y - 1, m + 12
    a = y // 100
    b = 2 - a + a // 4
    return (math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1))
            + d + b - 1524.5)


def sonnenparameter(tag: _date):
    """Deklination (Grad) und Zeitgleichung (Minuten) fuer 12 UTC des Tages."""
    t = (_julianischer_tag(tag) + 0.5 - 2451545.0) / 36525.0
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360.0
    m = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    mr = math.radians(m)
    c = (math.sin(mr) * (1.914602 - t * (0.004817 + 0.000014 * t))
         + math.sin(2 * mr) * (0.019993 - 0.000101 * t)
         + math.sin(3 * mr) * 0.000289)
    lam = l0 + c - 0.00569 - 0.00478 * math.sin(math.radians(125.04 - 1934.136 * t))
    eps0 = 23.0 + (26.0 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60.0) / 60.0
    eps = eps0 + 0.00256 * math.cos(math.radians(125.04 - 1934.136 * t))
    dekl = math.degrees(math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(lam))))
    y = math.tan(math.radians(eps / 2.0)) ** 2
    l0r = math.radians(l0)
    zgl = 4.0 * math.degrees(
        y * math.sin(2 * l0r) - 2 * e * math.sin(mr)
        + 4 * e * y * math.sin(mr) * math.cos(2 * l0r)
        - 0.5 * y * y * math.sin(4 * l0r) - 1.25 * e * e * math.sin(2 * mr))
    return dekl, zgl


def sonnenuntergang(tag: _date, breite: float, laenge: float):
    """(Stunden UTC als Float, Azimut in Grad von Nord im Uhrzeigersinn).

    laenge positiv nach Osten.  Gibt (None, None) bei Polartag/-nacht.
    """
    dekl, zgl = sonnenparameter(tag)
    phi, dlt = math.radians(breite), math.radians(dekl)
    h0 = math.radians(HOEHE_SONNENUNTERGANG_GRAD)
    arg = (math.sin(h0) - math.sin(phi) * math.sin(dlt)) / (math.cos(phi) * math.cos(dlt))
    if arg <= -1.0 or arg >= 1.0:
        return None, None
    ha = math.degrees(math.acos(arg))
    minuten = 720.0 - 4.0 * laenge - zgl + 4.0 * ha
    cos_a = ((math.sin(dlt) - math.sin(h0) * math.sin(phi))
             / (math.cos(h0) * math.cos(phi)))
    cos_a = max(-1.0, min(1.0, cos_a))
    azimut = 360.0 - math.degrees(math.acos(cos_a))  # Nachmittag
    return (minuten / 60.0) % 24.0, azimut


def zielpunkt(breite: float, laenge: float, azimut: float, distanz_km: float):
    """Grosskreis-Zielpunkt: von (breite, laenge) distanz_km weit auf azimut."""
    d = distanz_km / R_ERDE_KM
    phi1, lam1, th = math.radians(breite), math.radians(laenge), math.radians(azimut)
    phi2 = math.asin(math.sin(phi1) * math.cos(d)
                     + math.cos(phi1) * math.sin(d) * math.cos(th))
    lam2 = lam1 + math.atan2(math.sin(th) * math.sin(d) * math.cos(phi1),
                             math.cos(d) - math.sin(phi1) * math.sin(phi2))
    return math.degrees(phi2), (math.degrees(lam2) + 540.0) % 360.0 - 180.0


def tangentendistanz_km(hoehe_km: float) -> float:
    """D: wo der Strahl, der hoehe_km ueber dem Beobachter ankommt, den Boden streift."""
    return math.sqrt(2.0 * R_EFF_KM * hoehe_km)


def strahlhoehe_km(distanz_km: float, tangentendistanz: float) -> float:
    """Hoehe des Strahls ueber Grund in Entfernung distanz_km vom Beobachter."""
    if distanz_km >= tangentendistanz:
        return 0.0
    return (tangentendistanz - distanz_km) ** 2 / (2.0 * R_EFF_KM)


# Standardatmosphaere: Druckflaeche -> geometrische Hoehe (km).
# Nur als Vorabbildung; im Betrieb kommt die Hoehe aus geopotential_height_*.
NIVEAU_HOEHE_KM = {
    1000: 0.111, 925: 0.762, 850: 1.457, 700: 3.012, 600: 4.206, 500: 5.574,
    400: 7.185, 300: 9.164, 250: 10.363, 200: 11.784,
}


def blockierendes_niveau(distanz_km: float, tangentendistanz: float):
    """Druckflaechen, die der Strahl im Segment um distanz_km durchlaeuft."""
    z = strahlhoehe_km(distanz_km, tangentendistanz)
    kandidaten = sorted(NIVEAU_HOEHE_KM, key=lambda p: abs(NIVEAU_HOEHE_KM[p] - z))
    return kandidaten[0], z
