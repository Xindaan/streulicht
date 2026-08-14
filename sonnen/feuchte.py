"""Feuchte und Wolkendiagnostik.

WARUM EIGENE DIAGNOSTIK
Open-Meteos cloud_cover_XXXhPa ist (gemessen 14.08.2026, alle Modelle, alle
Niveaus) exakt  C = 1 - sqrt((1 - RH_wasser)/0.30), also Sundqvist mit
RH_crit = 0.70 ueber WASSER, niveauunabhaengig.  Kein Modellfeld, sondern
Nachbearbeitung.

WAS DABEI WIDERLEGT WURDE (14.08.2026)
Die urspruengliche Annahme war: das sei an den Schirmniveaus schief, weil
Eissaettigung bei viel niedrigerer Wasser-RH erreicht wird (-44 C: 65 %,
-57 C: 58 %), also muesse man auf RH ueber Eis mit Schwelle nahe 100 %
umstellen.  Gegen GFS' natives cloud_cover_high gemessen ist das FALSCH:

    eis, feste Schwelle 0.85/1.30   RMSE 0.4227  r 0.655   <- die Annahme
    Open-Meteo im Ist  0.70/1.00    RMSE 0.2763  r 0.801
    eis, nukleationsfoermig         RMSE 0.2626  r 0.813   <- gewaehlt

Grund: Cirrus-ENTSTEHUNG haengt an der Nukleationsschwelle, nicht an der
Saettigung - eisuebersaettigte, wolkenfreie Gebiete sind haeufig.  Eine feste
Schwelle bei Eissaettigung erzeugt Wolke, wo Eis sublimiert.  Open-Meteos
feste 70-%-Wasserschwelle entspricht in Eis-Einheiten 96 % bei -32 C und
125 % bei -62 C und trifft damit unbeabsichtigt das heterogene
Nukleationsband (105..130 %) - deshalb ist sie so schwer zu schlagen.

Die Gittersuche hat diese Kurve unabhaengig wiedergefunden:
RH_crit_eis(T) laeuft von 95 % bei -40 C auf 125 % bei -60 C.  Gewonnen wird
gegenueber dem Ist-Zustand nur 5 % RMSE - der Rest ist die prinzipielle Grenze
einer RH-Diagnostik ohne Kondensat (r ~ 0.81 ist die Decke).

GEGENPROBE gegen ERA5 (unabhaengiges Modell, natives Feld), gleiche Stunden:
    diese Diagnostik aus GFS-Feuchte   r 0.768
    GFS' EIGENES Wolkenschema          r 0.730
Die Kalibrierung ist also nicht zirkulaer: sie uebertraegt sich auf ein fremdes
Modell besser als das Schema, gegen das sie gefittet wurde.

Kalibrierung: Berlin, GFS, 26304 Stunden 2023-2025, Training 2023-2024,
Test 2025 ausgehalten.  Skript: skripte/kalibriere_eis2.py
"""

import math

# Magnus-Koeffizienten (Sonntag). Der Wasserzweig gilt bis -45 C und wird
# darunter extrapoliert - genau das tut das Modell beim Melden von RH auch,
# die Umrechnung bleibt also selbstkonsistent.
_A_W, _B_W = 17.62, 243.12
_A_I, _B_I = 22.46, 272.62

# Wasserzweig: unveraendert wie Open-Meteo. Ein Nachfitten brachte auf
# ausgehaltenen Daten 0.2666 statt 0.2763 RMSE - zu wenig, um eine Zahl ohne
# physikalische Lesart einzufuehren.
RH_CRIT_WASSER, RH_SAT_WASSER = 0.70, 1.00

# Eiszweig, nukleationsfoermig: RH_crit_eis(T) = K0 + K1*(-T-40)/20
K0_EIS, K1_EIS, SPANNE_EIS = 0.95, 0.30, 0.55

# Grenze zwischen den Zweigen. Bewusst nach DRUCK, nicht nach Temperatur:
# genau so wurde kalibriert (Eiszweig auf 400/300/250/200 hPa), damit sind
# Kalibrierung und Betrieb identisch. Ein Temperaturmischbereich waere
# physikalisch huebscher, aber dann gaelten die gefitteten Zahlen nicht mehr.
DRUCK_EISZWEIG_HPA = 400


def saettigungsdruck_wasser(t_c: float) -> float:
    return 6.112 * math.exp(_A_W * t_c / (_B_W + t_c))


def saettigungsdruck_eis(t_c: float) -> float:
    return 6.112 * math.exp(_A_I * t_c / (_B_I + t_c))


def rh_eis_aus_wasser(rh_wasser: float, t_c: float) -> float:
    """RH ueber Eis (0..1+) aus gemeldeter RH ueber Wasser (0..1)."""
    if t_c >= 0.0:
        return rh_wasser
    return rh_wasser * saettigungsdruck_wasser(t_c) / saettigungsdruck_eis(t_c)


def _sundqvist(rh: float, rh_crit: float, rh_sat: float) -> float:
    if rh <= rh_crit:
        return 0.0
    if rh >= rh_sat:
        return 1.0
    return 1.0 - math.sqrt((rh_sat - rh) / (rh_sat - rh_crit))


def rh_crit_eis(t_c: float) -> float:
    """Nukleationsfoermige Schwelle in RH_eis: 0.95 bei -40 C, 1.25 bei -60 C."""
    return K0_EIS + K1_EIS * (-t_c - 40.0) / 20.0


def bedeckung(rh_wasser_prozent: float, t_c: float, druck_hpa: float) -> float:
    """Wolkenbedeckungsgrad 0..1 aus RH (ueber Wasser, Prozent), T und Niveau."""
    rh_w = rh_wasser_prozent / 100.0
    if druck_hpa > DRUCK_EISZWEIG_HPA:
        return _sundqvist(rh_w, RH_CRIT_WASSER, RH_SAT_WASSER)
    crit = rh_crit_eis(t_c)
    return _sundqvist(rh_eis_aus_wasser(rh_w, t_c), crit, crit + SPANNE_EIS)


def ueberlappung(bedeckungen, w: float = 0.75) -> float:
    """Mehrere Niveaus zu einer Schicht zusammenfassen.

    C = (1-w)*max + w*(1 - prod(1-C_i));  w=0 Maximal-, w=1 Zufallsueberlapp.
    w = 0.75 ist gefittet (siehe Modulkopf) - die Daten wollen also nahezu
    Zufallsueberlapp.  Vorsicht beim Uebertragen auf den Fensterterm: dort
    ueberlappen SEGMENTE laengs eines Strahls, nicht Niveaus an einem Ort.
    Der Wert ist ein Anhaltspunkt, kein Beweis.
    """
    if not bedeckungen:
        return 0.0
    rest = 1.0
    for c in bedeckungen:
        rest *= (1.0 - c)
    return (1.0 - w) * max(bedeckungen) + w * (1.0 - rest)


def bedeckung_openmeteo(rh_wasser_prozent: float) -> float:
    """Open-Meteos Diagnostik, nachgebaut - nur fuer Vergleichsrechnungen."""
    return _sundqvist(rh_wasser_prozent / 100.0, 0.70, 1.00)


def eissaettigung_bei_rh_wasser(t_c: float) -> float:
    """Bei welcher Wasser-RH (Prozent) ist Eissaettigung erreicht?"""
    return 100.0 * saettigungsdruck_eis(t_c) / saettigungsdruck_wasser(t_c)
