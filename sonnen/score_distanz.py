"""Score mit Schirm in Entfernung - Verallgemeinerung von score.py.

WARUM (14.08.2026, aus Andres Album):
Die zehn schlechtesten Albumabende waren ueber Berlin nahezu wolkenfrei, aber
8 von 10 hatten ueber 50 % Bewoelkung im Band 180-360 km West.  250 km
westlich geht die Sonne rund 15 min spaeter unter; die Bank steht dort noch
im Licht und ist von Berlin aus bei 1-2 Grad Elevation genau in Blickrichtung
zu sehen.  Der alte Score zaehlt sie ausschliesslich als Blocker.

ANSATZ: kein "Schirm nah, Fenster fern" mehr, sondern eine Summe ueber den
sichtbaren Himmel.  Fuer jedes Paar (Schicht, Entfernung):

    Beitrag = Bewoelkung * Raumwinkel * Phasenfunktion * Sicht * Weg

    Sicht - Transmission auf der SICHTLINIE von Berlin bis zum Schirm
    Weg   - Transmission auf dem BELEUCHTUNGSWEG vom Tangentenpunkt
            (bei d_s + D(h)) bis zum Schirm

    S = Summe(Beitraege) / Summe(Raumwinkel)

Das ist der Anteil des sichtbaren Himmels, der aus beleuchteter Wolke
besteht - eine Zahl in [0,1] mit physikalischer Lesart.  Der alte Score ist
der Spezialfall "nur d_s = 0".

DREI GEOMETRISCHE NEBENBEDINGUNGEN, die im alten Score nicht vorkamen:

1. SICHTBARKEIT.  Eine Wolke in Entfernung d ist nur sichtbar, wenn sie
   hoeher steht als d^2/(2*R_eff).  Bei 240 km sind das 3.4 km (tiefe
   Bewoelkung faellt weg), bei 360 km 7.6 km (nur noch hohe).
2. Die SICHTLINIE haengt durch: von (0,0) nach (d, h) verlaeuft sie ueber
   der gekruemmten Erde bei z(x) = x*h/d - x*(d-x)/(2*R_eff).  Bei d=250,
   h=4 km liegt der Tiefpunkt bei 1.1 km - dort blockt tiefe Bewoelkung.
3. Der BELEUCHTUNGSWEG verschiebt sich mit: der Tangentenpunkt liegt bei
   d_s + D(h), nicht bei D(h).

BEKANNTE GRENZE: die Fanabtastung endet bei 420 km.  Fuer einen fernen hohen
Schirm liegt der Tangentenpunkt jenseits davon (250 + 402 = 652 km), der
Beleuchtungsweg ist dann nur teilweise abgetastet.  Nicht abgetastete
Abschnitte gelten als frei, was ferne Schirme systematisch beguenstigt.
Deshalb gibt score() die Abtastdeckung mit zurueck - wer sie ignoriert,
misst ein Artefakt.
"""
import math

from .geometrie import R_EFF_KM, tangentendistanz_km
from .score import (DISTANZEN_KM, FAECHER_AZIMUTE, GRENZE_LOW_MID_KM,
                    GRENZE_MID_HIGH_KM, K_SEGMENT, SIGMA_AZIMUT_GRAD)

# Schichten: Name, Untergrenze, Obergrenze, repraesentative Hoehe (km)
SCHICHTEN = (("low", 0.25, GRENZE_LOW_MID_KM, 1.2),
             ("mid", GRENZE_LOW_MID_KM, GRENZE_MID_HIGH_KM, 4.2),
             ("high", GRENZE_MID_HIGH_KM, 12.0, 9.5))


def horizonthoehe_km(d_km):
    """Mindesthoehe, ab der eine Wolke in Entfernung d ueberhaupt sichtbar ist."""
    return d_km * d_km / (2.0 * R_EFF_KM)


def sichtbare_hoehe(schicht, d_km):
    """Repraesentative Hoehe des SICHTBAREN Teils der Schicht, oder None."""
    _, unten, oben, rep = schicht
    hmin = horizonthoehe_km(d_km)
    if oben <= hmin:
        return None
    if rep > hmin:
        return rep
    return 0.5 * (hmin + oben)


# Asymmetrieparameter fuer Wasserwolken, Literaturwert - nicht an diese Daten
# angepasst.  Ohne Phasenfunktion ist der Ansatz nachweislich schlechter als
# der alte Score (Mittelrang 0.650 gegen 0.674): der Ring bei 300 km hat nur
# 1/110 des Raumwinkels des Rings ueber dem Kopf und kann den Score gar nicht
# bewegen - egal wie hell die Bank ist.
G_HENYEY_GREENSTEIN = 0.85


def phasenfunktion(theta_grad, g=G_HENYEY_GREENSTEIN):
    """Henyey-Greenstein. Wolkentropfen streuen stark vorwaerts: eine ferne
    Bank in Blickrichtung wird im Vorwaertspeak gesehen (Streuwinkel unter
    1 Grad), eine Wolke ueber dem Kopf bei rund 90 Grad, wo die
    Phasenfunktion ihr Minimum hat.  Verhaeltnis rund 670 zu 1."""
    c = math.cos(math.radians(theta_grad))
    return (1.0 - g * g) / (4.0 * math.pi * (1.0 + g * g - 2.0 * g * c) ** 1.5)


def streuwinkel_grad(d_km, hoehe_km):
    """Winkel zwischen einfallendem Sonnenlicht und Blickrichtung am Wolkenort.

    Am Ort d geht die Sonne spaeter unter; ihre Hoehe dort ist naeherungsweise
    d/R_eff.  Die Blickrichtung von Berlin trifft die Wolke unter
    arctan(h/d).  Beide zeigen nach Osten und leicht abwaerts.
    """
    if d_km <= 0.0:
        return 90.0
    sonne = math.degrees(d_km / R_EFF_KM)
    blick = math.degrees(math.atan2(hoehe_km, d_km))
    return abs(sonne - blick)


def raumwinkel(d0, d1, hoehe):
    """Raumwinkel des Rings [d0,d1] fuer eine Schicht in Hoehe hoehe."""
    return (1.0 / math.sqrt(d0 * d0 + hoehe * hoehe)
            - 1.0 / math.sqrt(d1 * d1 + hoehe * hoehe))


def _schicht_bei(z_km):
    for name, unten, oben, _rep in SCHICHTEN:
        if unten <= z_km < oben:
            return name
    return "high" if z_km >= GRENZE_MID_HIGH_KM else "low"


def _ring(i):
    d = DISTANZEN_KM[i]
    d0 = 0.0 if i == 0 else 0.5 * (DISTANZEN_KM[i - 1] + d)
    d1 = (0.5 * (d + DISTANZEN_KM[i + 1]) if i + 1 < len(DISTANZEN_KM)
          else d + 30.0)
    return d0, d1


def score(hole):
    """hole(d_km, az_versatz, schicht) -> Bedeckung 0..1 oder None.

    Rueckgabe (S, Detail).  Detail["deckung"] ist der Anteil des
    Beleuchtungswegs, der von der Fanabtastung ueberhaupt erfasst wurde -
    gewichtet mit den Beitraegen.  Weit unter 1 heisst: das Ergebnis haengt
    an unbeobachteten Abschnitten.
    """
    def mittel(d, schicht):
        """Gaussgewichteter Faechermittelwert; d=0 nur einmal."""
        zc = zg = 0.0
        for dv in FAECHER_AZIMUTE:
            if d == 0.0 and dv != 0.0:
                continue
            c = hole(d, dv, schicht)
            if c is None:
                continue
            w = 1.0 if d == 0.0 else math.exp(-0.5 * (dv / SIGMA_AZIMUT_GRAD) ** 2)
            zc += w * c
            zg += w
        return zc / zg if zg else None

    summe = gesamt_omega = 0.0
    deckung_zaehler = deckung_nenner = 0.0
    beitraege = []

    for i, d_s in enumerate(DISTANZEN_KM):
        d0, d1 = _ring(i)
        for schicht in SCHICHTEN:
            name = schicht[0]
            h = sichtbare_hoehe(schicht, d_s)
            if h is None:
                continue                      # hinter dem Horizont
            omega = raumwinkel(d0, d1, h) * phasenfunktion(
                streuwinkel_grad(d_s, h))
            gesamt_omega += omega
            c = mittel(d_s, name)
            if not c:
                continue

            # --- Sichtlinie von Berlin bis zum Schirm
            sicht = 1.0
            for x in DISTANZEN_KM:
                if not 0.0 < x < d_s:
                    continue
                z = x * h / d_s - x * (d_s - x) / (2.0 * R_EFF_KM)
                if z <= 0.0:
                    sicht = 0.0
                    break
                cs = mittel(x, _schicht_bei(z))
                if cs:
                    sicht *= (1.0 - cs)

            # --- Beleuchtungsweg vom Tangentenpunkt bis zum Schirm
            d_tan = d_s + tangentendistanz_km(h)
            weg = 1.0
            erfasst = 0.0
            for x in DISTANZEN_KM:
                if not d_s < x <= d_tan:
                    continue
                z = (d_tan - x) ** 2 / (2.0 * R_EFF_KM)
                cs = mittel(x, _schicht_bei(z))
                if cs is not None:
                    weg *= (1.0 - cs) ** K_SEGMENT
                    erfasst += 1.0
            noetig = max(1.0, (min(d_tan, DISTANZEN_KM[-1]) - d_s) / 60.0)
            deckung = min(1.0, erfasst / max(1.0, (d_tan - d_s) / 60.0))

            beitrag = c * omega * sicht * weg
            summe += beitrag
            deckung_zaehler += beitrag * deckung
            deckung_nenner += beitrag
            if beitrag > 0:
                beitraege.append({"schicht": name, "d_km": d_s, "hoehe_km": h,
                                  "C": c, "sicht": sicht, "weg": weg,
                                  "omega": omega / max(gesamt_omega, 1e-9),
                                  "beitrag": beitrag, "deckung": deckung})

    if gesamt_omega <= 0:
        return 0.0, None
    s = summe / gesamt_omega
    beitraege.sort(key=lambda b: -b["beitrag"])
    return s, {"beitraege": beitraege[:8],
               "deckung": (deckung_zaehler / deckung_nenner
                           if deckung_nenner > 0 else 1.0)}
