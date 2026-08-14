"""Niveauaufgeloeste Score-Variante - der eigentliche Betriebsscore.

Unterschied zur 3-Schicht-Variante in score.py:
  * Sechs Schirmniveaus (600..200 hPa) statt zwei, jedes mit eigener
    Tangentendistanz D(h) - der willkuerliche Parameter "Schirmhoehe" aus E0
    entfaellt dadurch ersatzlos.
  * Je Segment das Druckniveau, das der Strahl DORT durchlaeuft, statt einer
    Drei-Schicht-Naeherung.
  * Dickenstrafe in Term A moeglich: die Maechtigkeit der zusammenhaengenden
    gesaettigten Schicht ist der beste Proxy fuer optische Dicke, den reine
    Feuchte hergibt (das Modell liefert kein Kondensat).
  * Die Schirmschicht blockiert sich hier ZU RECHT selbst nicht - der
    Wegabschnitt beginnt bei 60 km, und dort liegt der Strahl bereits unter
    dem Schirmniveau.  Es braucht also keine Sonderregel wie in score.py.
"""
import math

from .feuchte import bedeckung, ueberlappung
from .geometrie import (NIVEAU_HOEHE_KM, sonnenuntergang, strahlhoehe_km,
                        tangentendistanz_km, zielpunkt)
from .score import (DISTANZEN_KM, FAECHER_AZIMUTE, K_SEGMENT, NAHBEREICH_KM,
                    SICHT_KM, SIGMA_AZIMUT_GRAD)

SCHIRM_NIVEAUS = (600, 500, 400, 300, 250, 200)
ALLE_NIVEAUS = tuple(sorted(NIVEAU_HOEHE_KM, reverse=True))   # 1000 .. 200

# Dickenstrafe: bis 1.5 km volle Wertung, ab 4 km auf 0.3 gedaempft.
DICKE_VOLL_KM, DICKE_MAX_KM, DICKE_BODEN = 1.5, 4.0, 0.3
SAT_SCHWELLE = 0.30   # ab hier zaehlt ein Niveau als "gesaettigt"


def _niveaus_im_bereich(z_unten, z_oben, hoehen=NIVEAU_HOEHE_KM):
    """Druckflaechen, deren Hoehe im Intervall liegt; sonst die naechstgelegene."""
    niveaus = tuple(sorted(hoehen, reverse=True))
    lo, hi = min(z_unten, z_oben), max(z_unten, z_oben)
    treffer = [p for p in niveaus if lo <= hoehen[p] <= hi]
    if treffer:
        return treffer
    mitte = 0.5 * (lo + hi)
    return [min(niveaus, key=lambda p: abs(hoehen[p] - mitte))]


def _dicke_km(profil, h, hoehen=NIVEAU_HOEHE_KM):
    """Maechtigkeit der zusammenhaengenden gesaettigten Schicht um h herum."""
    niveaus = tuple(sorted(hoehen, reverse=True))
    idx = niveaus.index(h)
    if profil.get(h, 0.0) < SAT_SCHWELLE:
        return 0.0
    u = o = idx
    while u > 0 and profil.get(niveaus[u - 1], 0.0) >= SAT_SCHWELLE:
        u -= 1
    while o < len(niveaus) - 1 and \
            profil.get(niveaus[o + 1], 0.0) >= SAT_SCHWELLE:
        o += 1
    return abs(hoehen[niveaus[o]] - hoehen[niveaus[u]])


def _strafe(dicke):
    if dicke <= DICKE_VOLL_KM:
        return 1.0
    if dicke >= DICKE_MAX_KM:
        return DICKE_BODEN
    f = (dicke - DICKE_VOLL_KM) / (DICKE_MAX_KM - DICKE_VOLL_KM)
    return 1.0 - f * (1.0 - DICKE_BODEN)


def score(hole, mit_dickenstrafe=True, direkt=False, hoehen=None,
          schirm_niveaus=None):
    """Score aus Druckflaechendaten.

    hole(d_km, az_versatz, druck_hpa) liefert normalerweise (rh_prozent,
    t_celsius); die Bedeckung wird daraus diagnostiziert.  Mit direkt=True
    liefert hole stattdessen die Bedeckung 0..1 unmittelbar - dafuer gebaut,
    dass ICON-D2 sein EIGENES Wolkenschema je Druckflaeche mitliefert und
    dann nichts zu diagnostizieren ist.

    hoehen/schirm_niveaus erlauben einen anderen Flaechensatz als den des
    Projekts.  Ohne diese Parameter waere die ICON-Auswertung an 900 und
    800 hPa gescheitert: die Projekttabelle kennt 925 und 850.
    """
    hoehen = NIVEAU_HOEHE_KM if hoehen is None else hoehen
    alle = tuple(sorted(hoehen, reverse=True))
    schirme = (tuple(p for p in SCHIRM_NIVEAUS if p in hoehen)
               if schirm_niveaus is None else tuple(schirm_niveaus))

    def c(d, dv, p):
        w = hole(d, dv, p)
        if w is None:
            return None
        return w if direkt else bedeckung(w[0], w[1], p)

    bestes, detail = 0.0, None
    for h in schirme:
        d_tan = tangentendistanz_km(hoehen[h])

        # Term A: Schirm im Nahbereich (d == 0 nur einmal zaehlen)
        werte = []
        for dv in FAECHER_AZIMUTE:
            for d in DISTANZEN_KM:
                if d > NAHBEREICH_KM or (d == 0.0 and dv != 0.0):
                    continue
                x = c(d, dv, h)
                if x is not None:
                    werte.append(x)
        if not werte:
            continue
        a = sum(werte) / len(werte)

        if mit_dickenstrafe:
            profil = {p: c(0.0, 0.0, p) or 0.0 for p in alle}
            a *= _strafe(_dicke_km(profil, h, hoehen))

        # Term B (a): Sichtfaktor - alles UNTER dem Schirm im Nahbereich
        unter = [p for p in alle if p > h]
        sicht_w = []
        for dv in FAECHER_AZIMUTE:
            for d in DISTANZEN_KM:
                if d > SICHT_KM or (d == 0.0 and dv != 0.0):
                    continue
                cs = [c(d, dv, p) for p in unter]
                cs = [x for x in cs if x is not None]
                if cs:
                    sicht_w.append(ueberlappung(cs))
        sicht = 1.0 - (sum(sicht_w) / len(sicht_w) if sicht_w else 0.0)

        # Term B (b): Beleuchtungsweg
        stuetzen = [d for d in DISTANZEN_KM if SICHT_KM <= d < d_tan]
        jenseits = [d for d in DISTANZEN_KM if d >= d_tan]
        if jenseits:
            stuetzen.append(jenseits[0])
        weg, segmente = 1.0, []
        for i in range(len(stuetzen) - 1):
            d_nah, d_fern = stuetzen[i], stuetzen[i + 1]
            niv = _niveaus_im_bereich(strahlhoehe_km(d_fern, d_tan),
                                      strahlhoehe_km(d_nah, d_tan), hoehen)
            zc = zg = 0.0
            for dv in FAECHER_AZIMUTE:
                cs = [c(d_fern, dv, p) for p in niv]
                cs = [x for x in cs if x is not None]
                if not cs:
                    continue
                w = math.exp(-0.5 * (dv / SIGMA_AZIMUT_GRAD) ** 2)
                zc += w * max(cs)      # Maximalueberlapp im Segment
                zg += w
            if zg == 0.0:
                continue
            c_seg = zc / zg
            weg *= (1.0 - c_seg) ** K_SEGMENT
            segmente.append((d_nah, d_fern, niv, c_seg))

        s = a * sicht * weg
        if s > bestes or detail is None:
            bestes, detail = s, {
                "schirm": h, "hoehe_km": hoehen[h], "d_tangente": d_tan,
                "A": a, "B": sicht * weg, "sicht": sicht, "weg": weg,
                "segmente": segmente}
    return bestes, detail


def score_fuer_abend(tag, breite, laenge, feld, mit_dickenstrafe=True):
    """feld(lat, lon, druck) -> (rh, t) zur Sonnenuntergangsstunde."""
    stunde, azimut = sonnenuntergang(tag, breite, laenge)
    if stunde is None:
        return None, None
    punkte = {}
    for dv in FAECHER_AZIMUTE:
        for d in DISTANZEN_KM:
            punkte[(d, dv)] = ((breite, laenge) if d == 0.0
                               else zielpunkt(breite, laenge,
                                              (azimut + dv) % 360.0, d))

    def hole(d, dv, p):
        q = punkte.get((d, dv))
        return None if q is None else feld(q[0], q[1], p)

    s, detail = score(hole, mit_dickenstrafe)
    if detail is not None:
        detail["stunde_utc"], detail["azimut"] = stunde, azimut
    return s, detail
