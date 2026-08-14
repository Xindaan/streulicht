"""Der Score: Schirm mal Fenster, multiplikativ, pro Schirmniveau.

    S = max ueber Schirmniveau h von  [ A_h * B_h ]

A_h  Schirm      Bewoelkung auf Niveau h im Nahbereich (Faecher, d <= 120 km).
B_h  Fenster     zwei Mechanismen in einem Produkt:
                 (a) Sichtfaktor: Wolken ZWISCHEN Dir und dem Schirm (d <= 60 km,
                     alle Niveaus unter h),
                 (b) Beleuchtungsweg: Produkt ueber Segmente von 60 km bis zur
                     Tangentendistanz D(h), je Segment das Niveau, das der
                     Strahl dort durchlaeuft.

Multiplikativ, weil es eine Konjunktion ist: ohne Schirm kein Bild, ohne
Fenster kein Licht.  Additiv gaebe einem perfekten Schirm ueber geschlossener
Westdecke 0.5 - physikalisch ist das eine 0.

Der Exponent K_SEGMENT im Wegprodukt war in E0 als unsicherste Konstante
benannt.  Die Ueberlappungskalibrierung (siehe feuchte.py) will nahezu
Zufallsueberlapp, also K = 1 (reines Produkt).  Einschraenkung: dort wurden
NIVEAUS an einem Ort ueberlappt, hier SEGMENTE laengs eines Strahls.

DIESE DATEI IST DIE 3-SCHICHT-VARIANTE (low/mid/high).  Sie ist das, was ERA5
ueber Open-Meteo hergibt, und damit die einzige Basis fuer eine mehrjaehrige
Klimatologie.  Die niveauaufgeloeste Variante braucht Druckflaechen und laeuft
nur auf gfs_global (ab 2022) bzw. im Betrieb auf ECMWF ENS.  Der Vergleich
beider ist T-0006 und entscheidet, ob s* uebertragbar ist.
"""
import math

from .geometrie import (sonnenuntergang, tangentendistanz_km, strahlhoehe_km,
                        zielpunkt)

# Faechergeometrie
FAECHER_AZIMUTE = (-24.0, -12.0, 0.0, 12.0, 24.0)
DISTANZEN_KM = (0.0, 60.0, 120.0, 180.0, 240.0, 300.0, 360.0, 420.0)
SIGMA_AZIMUT_GRAD = 15.0   # Gaussgewicht fuer den Beleuchtungsweg
NAHBEREICH_KM = 120.0      # bis hierher zaehlt der Schirm

# Gewichtung der Schirmpunkte im Nahbereich.  DREI Modi, und die Unterscheidung
# zwischen den ersten beiden ist nicht akademisch: sie war der erste Anlauf
# eines Vergleichs, der deshalb die gespeicherte Klimatologie nicht reproduzierte.
# "punkt"      - jeder Fanpunkt gleich; war die urspruengliche Wahl und ist
#                nachweislich falsch: eine Wolkendecke, die nur ueber dem
#                Standort steht, wird mit zehn Nullen weggemittelt.  Realfall
#                29.03.2025: 90 % Mittelbewoelkung ueber Berlin, freier Westen
#                bis 400 km - Term A kam auf 8 % (d=0 hat nur 1/11 Gewicht).
# "ring"       - jeder Entfernungsring gleich, Azimute teilen sich den Ring.
#                d=0 bekommt damit 1/3 statt 1/11.
# "raumwinkel" - Gewicht = Raumwinkel, den der von der Stuetzstelle vertretene
#                Ring am Himmel einnimmt.  Fuer eine Schicht in Hoehe h ist die
#                Raumwinkeldichte proportional zu d*h/(d^2+h^2)^{3/2}, mit
#                Maximum bei d = h/sqrt(2) und Abfall wie 1/d^2.  Der Punkt
#                ueber dem Kopf bekommt damit rund 89 % statt 9 %.
#                Aus Geometrie hergeleitet, nicht gefittet.
GEWICHTUNG = "raumwinkel"
SICHT_KM = 60.0            # bis hierher zaehlt die Sichtblockade
K_SEGMENT = 1.0

# Schichtgrenzen wie bei ECMWF/ERA5: low bis 800 hPa, mid 800..450, high darueber
GRENZE_LOW_MID_KM = 2.0
GRENZE_MID_HIGH_KM = 6.3

# Repraesentative Schirmhoehen der beiden nutzbaren Schichten
SCHIRME = (("high", 9.5), ("mid", 4.2))


def _schicht(z_km: float) -> str:
    if z_km < GRENZE_LOW_MID_KM:
        return "low"
    if z_km < GRENZE_MID_HIGH_KM:
        return "mid"
    return "high"


def _schichten_im_segment(z_fern: float, z_nah: float):
    """Alle Schichten, die der Strahl zwischen zwei Stuetzstellen durchlaeuft."""
    lo, hi = min(z_fern, z_nah), max(z_fern, z_nah)
    treffer = []
    for name, (u, o) in (("low", (0.0, GRENZE_LOW_MID_KM)),
                         ("mid", (GRENZE_LOW_MID_KM, GRENZE_MID_HIGH_KM)),
                         ("high", (GRENZE_MID_HIGH_KM, 99.0))):
        if hi > u and lo < o:
            treffer.append(name)
    return treffer or [_schicht(lo)]


def faecherpunkte(breite, laenge, azimut):
    """[(d_km, az_versatz, lat, lon)] fuer den ganzen Faecher."""
    aus = []
    for dv in FAECHER_AZIMUTE:
        for d in DISTANZEN_KM:
            if d == 0.0:
                aus.append((0.0, dv, breite, laenge))
            else:
                la, lo = zielpunkt(breite, laenge, (azimut + dv) % 360.0, d)
                aus.append((d, dv, la, lo))
    return aus


def _gewicht(az_versatz):
    return math.exp(-0.5 * (az_versatz / SIGMA_AZIMUT_GRAD) ** 2)


def _nahdistanzen():
    return [d for d in DISTANZEN_KM if d <= NAHBEREICH_KM]


def _schirmgewichte(hoehe_km):
    """Raumwinkel je Stuetzstelle, integriert ueber den vertretenen Ring."""
    nah = _nahdistanzen()
    if GEWICHTUNG == "punkt":
        # d=0 zaehlt einmal, jede weitere Distanz mit allen Azimuten
        return {d: (1.0 if d == 0.0 else float(len(FAECHER_AZIMUTE))) for d in nah}
    if GEWICHTUNG == "ring":
        return {d: 1.0 for d in nah}
    g = {}
    for i, d in enumerate(nah):
        d0 = 0.0 if i == 0 else 0.5 * (nah[i - 1] + d)
        d1 = 0.5 * (d + nah[i + 1]) if i + 1 < len(nah) else d + 30.0
        g[d] = (1.0 / math.sqrt(d0 * d0 + hoehe_km * hoehe_km)
                - 1.0 / math.sqrt(d1 * d1 + hoehe_km * hoehe_km))
    summe = sum(g.values())
    return {d: v / summe for d, v in g.items()}


def score(hole):
    """hole(d_km, az_versatz, schicht) -> Bedeckung 0..1  (oder None).

    Rueckgabe: (S, Detail-dict). Detail traegt die Terme fuer Diagnose und
    fuer den Vertikalschnitt in E3.
    """
    bestes, detail = 0.0, None
    for name, hoehe in SCHIRME:
        d_tan = tangentendistanz_km(hoehe)

        # --- Term A: Schirm im Nahbereich, raumwinkelgewichtet
        # d == 0 ist fuer alle Faecherazimute derselbe Punkt (der Standort) und
        # wuerde sonst fuenffach zaehlen.
        gw = _schirmgewichte(hoehe)
        werte, gew = 0.0, 0.0
        for dv in FAECHER_AZIMUTE:
            for d in DISTANZEN_KM:
                if d > NAHBEREICH_KM or (d == 0.0 and dv != 0.0):
                    continue
                c = hole(d, dv, name)
                if c is None:
                    continue
                w = gw[d] / (1.0 if d == 0.0 else len(FAECHER_AZIMUTE))
                werte += w * c
                gew += w
        if gew == 0.0:
            continue
        a = werte / gew

        # --- Term B (a): Sichtfaktor - was steht zwischen Dir und dem Schirm
        unter = ["low"] if name == "mid" else ["low", "mid"]
        sicht_c, sicht_n = 0.0, 0
        for dv in FAECHER_AZIMUTE:
            for d in DISTANZEN_KM:
                if d > SICHT_KM or (d == 0.0 and dv != 0.0):
                    continue
                cs = [hole(d, dv, s) for s in unter]
                cs = [c for c in cs if c is not None]
                if not cs:
                    continue
                rest = 1.0
                for c in cs:
                    rest *= (1.0 - c)
                sicht_c += 1.0 - rest
                sicht_n += 1
        sicht = 1.0 - (sicht_c / sicht_n if sicht_n else 0.0)

        # --- Term B (b): Beleuchtungsweg, Produkt ueber Segmente
        # Die erste Stuetzstelle JENSEITS der Tangente kommt mit dazu, sonst
        # bleibt das Stueck zwischen der letzten Stuetze und dem Tangentenpunkt
        # unbewertet - und genau dort laeuft der Strahl am tiefsten, es ist die
        # kritischste Zone ueberhaupt.  Beispiel Schirm "high": d_tan = 402 km,
        # ohne diese Zeile endete die Abtastung bei 360 km.
        stuetzen = [d for d in DISTANZEN_KM if SICHT_KM <= d < d_tan]
        jenseits = [d for d in DISTANZEN_KM if d >= d_tan]
        if jenseits:
            stuetzen.append(jenseits[0])
        weg, segmente = 1.0, []
        for i in range(len(stuetzen) - 1):
            d_nah, d_fern = stuetzen[i], stuetzen[i + 1]
            schichten = _schichten_im_segment(
                strahlhoehe_km(d_fern, d_tan), strahlhoehe_km(d_nah, d_tan))
            # Die Schirmschicht blockiert sich nicht selbst.  Zwei Gruende:
            # (1) Innerhalb einer 3-Schicht-Aufloesung ist "high bei 9.5 km
            #     ueber Berlin" und "high bei 6.5 km in 100 km Entfernung"
            #     dieselbe Variable - Selbstblockade waere ein Artefakt der
            #     Aufloesung, keine Physik.  Ohne diese Zeile loescht eine
            #     geschlossene hohe Decke ihren eigenen Score auf exakt 0.
            # (2) Physikalisch sitzt echter Cirrus (8-11 km) in 60-120 km
            #     Entfernung UEBER dem Strahl (dort 4.7-6.9 km), blockiert ihn
            #     also ohnehin nicht.
            # In der niveauaufgeloesten Variante ist die Unterscheidung echt
            # (300-hPa-Schirm, von 400 hPa blockiert) und muss zurueck.
            schichten = [s for s in schichten if s != name] or None
            if schichten is None:
                continue
            zc, zg = 0.0, 0.0
            for dv in FAECHER_AZIMUTE:
                cs = [hole(d_fern, dv, s) for s in schichten]
                cs = [c for c in cs if c is not None]
                if not cs:
                    continue
                w = _gewicht(dv)
                zc += w * max(cs)   # Maximalueberlapp innerhalb des Segments
                zg += w
            if zg == 0.0:
                continue
            c_seg = zc / zg
            weg *= (1.0 - c_seg) ** K_SEGMENT
            segmente.append((d_nah, d_fern, schichten, c_seg))

        b = sicht * weg
        s = a * b
        if s >= bestes:
            bestes = s
            detail = {"schirm": name, "hoehe_km": hoehe, "d_tangente": d_tan,
                      "A": a, "B": b, "sicht": sicht, "weg": weg,
                      "segmente": segmente}
    return bestes, detail


def score_fuer_abend(tag, breite, laenge, feld):
    """feld(lat, lon, schicht) -> Bedeckung 0..1 zur Sonnenuntergangsstunde."""
    stunde, azimut = sonnenuntergang(tag, breite, laenge)
    if stunde is None:
        return None, None
    punkte = {(d, dv): (la, lo) for d, dv, la, lo in
              faecherpunkte(breite, laenge, azimut)}

    def hole(d, dv, schicht):
        p = punkte.get((d, dv))
        return None if p is None else feld(p[0], p[1], schicht)

    s, detail = score(hole)
    if detail is not None:
        detail["stunde_utc"] = stunde
        detail["azimut"] = azimut
    return s, detail
