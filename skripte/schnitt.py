"""Vertikalschnitt entlang des Sonnenuntergangsazimuts als SVG.

Das Bild, das die Idee in einer Sekunde erklaert: x = Entfernung nach Westen,
y = Hoehe, Wolken als Baender, und der Beleuchtungsstrahl als Kurve, die einige
hundert Kilometer westlich den Boden streift.  "Das Licht muss da hinten
drunter durch" ist als Zeichnung sofort verstanden und als Satz nicht.

Zweiter, unabhaengiger Zweck: Diagnose.  Bei einer danebengegangenen
Vorhersage sieht man im Schnitt sofort, ob der Schirm oder das Fenster schuld
war.

Datenquelle ist der Klimatologie-Blockcache - echte ERA5-Felder zur
Sonnenuntergangsstunde, kein Kontingent noetig.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import (NIVEAU_HOEHE_KM, sonnenuntergang,  # noqa: E402
                              strahlhoehe_km, tangentendistanz_km, zielpunkt)
from sonnen.score import (DISTANZEN_KM, GRENZE_LOW_MID_KM,  # noqa: E402
                          GRENZE_MID_HIGH_KM, SCHIRME, faecherpunkte, score)

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITTER = 0.5
BREITE, LAENGE = 52.52, 13.405
X0, Y0, BR, HO = 70, 40, 700, 380          # Zeichenflaeche
XMAX, YMAX = 460.0, 12.5                   # km
WOCHENTAG = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


def zelle(lat, lon):
    return "%d/%d" % (round(lat / GITTER), round(lon / GITTER))


def lade_feld(tag):
    """{zelle: {schicht: wert}} fuer diesen Abend aus dem Blockcache."""
    jahr = tag[:4]
    feld = {}
    cd = os.path.join(BASIS, "daten", "roh")
    for name in sorted(os.listdir(cd)):
        if not name.startswith("g%g_%s_" % (GITTER, jahr)):
            continue
        with open(os.path.join(cd, name)) as f:
            for z, e in json.load(f).items():
                w = {s: e[s].get(tag) for s in ("low", "mid", "high") if s in e}
                if any(v is not None for v in w.values()):
                    feld[z] = w
    return feld


def px(d_km, z_km):
    return (X0 + BR * d_km / XMAX, Y0 + HO * (1.0 - z_km / YMAX))


def svg(tag, feld):
    from datetime import date as _d
    t = _d.fromisoformat(tag)
    stunde, azimut = sonnenuntergang(t, BREITE, LAENGE)
    punkte = {(d, dv): (la, lo) for d, dv, la, lo in
              faecherpunkte(BREITE, LAENGE, azimut)}

    def hole(d, dv, schicht):
        p = punkte.get((d, dv))
        if p is None:
            return None
        e = feld.get(zelle(*p))
        if e is None or e.get(schicht) is None:
            return None
        return e[schicht] / 100.0

    s, det = score(hole)

    o = ['<svg viewBox="0 0 840 490" xmlns="http://www.w3.org/2000/svg" '
         'font-family="sans-serif">',
         '<rect width="840" height="490" fill="#0d1117"/>']
    for _z in (2, 4, 6, 8, 10, 12):
        _, _y = px(0, _z)
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#30363d" '
                 'stroke-width="0.5"/>' % (X0, _y, X0 + BR, _y))

    # Wolkenbaender: je Schicht ein Polygon aus den Fanwerten laengs d
    # Realistische Teilbaender statt voller Schichtdicke: die 3-Schicht-
    # Aufloesung sagt NICHTS ueber die Maechtigkeit, also eine plausible
    # zeichnen statt der maximalen - eine 6 km dicke Cirrusplatte waere
    # sichtbar falsch und wuerde eine Genauigkeit behaupten, die es nicht gibt.
    BAENDER = (("high", 7.6, 10.4), ("mid", 2.9, 5.4), ("low", 0.25, 1.6))
    SCHRITT = 6.0                      # km, Spaltenbreite fuer weiche Uebergaenge

    def wert(schicht, d):
        """Linear zwischen den Fanstuetzstellen - das Feld ist stetig."""
        vs = [(x, hole(x, 0.0, schicht)) for x in DISTANZEN_KM]
        vs = [(x, c) for x, c in vs if c is not None]
        if not vs:
            return 0.0
        if d <= vs[0][0]:
            return vs[0][1]
        for (x0, c0), (x1, c1) in zip(vs, vs[1:]):
            if x0 <= d <= x1:
                f = (d - x0) / (x1 - x0) if x1 > x0 else 0.0
                return c0 + f * (c1 - c0)
        return vs[-1][1] if d <= vs[-1][0] + 60 else 0.0

    # Ein Rechteck je Schicht mit horizontalem UND vertikalem Verlauf.
    # Gestapelte Spalten erzeugten an jedem Spaltenrand doppelte Opazitaet
    # und damit eine Riffelung, die wie Struktur aussah, aber keine war.
    defs = []
    for nr, (schicht, unten, oben) in enumerate(BAENDER):
        stops = []
        d = 0.0
        while d <= XMAX:
            c = wert(schicht, d) or 0.0
            stops.append('<stop offset="%.4f" stop-color="#58a6ff" '
                         'stop-opacity="%.3f"/>' % (d / XMAX, min(0.80, 0.62 * c)))
            d += SCHRITT
        if not any('stop-opacity="0.0' not in x for x in stops):
            continue
        defs.append('<linearGradient id="g%d" x1="0" x2="1" y1="0" y2="0">%s'
                    '</linearGradient>' % (nr, "".join(stops)))
        # vertikale Weichzeichnung der Ober- und Unterkante
        defs.append('<linearGradient id="v%d" x1="0" x2="0" y1="0" y2="1">'
                    '<stop offset="0" stop-color="#000"/>'
                    '<stop offset="0.25" stop-color="#fff"/>'
                    '<stop offset="0.75" stop-color="#fff"/>'
                    '<stop offset="1" stop-color="#000"/></linearGradient>' % nr)
        defs.append('<mask id="m%d"><rect x="%.1f" y="%.1f" width="%.1f" '
                    'height="%.1f" fill="url(#v%d)"/></mask>'
                    % (nr, X0, px(0, oben)[1], BR,
                       px(0, unten)[1] - px(0, oben)[1], nr))
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                 'fill="url(#g%d)" mask="url(#m%d)"/>'
                 % (X0, px(0, oben)[1], BR, px(0, unten)[1] - px(0, oben)[1],
                    nr, nr))
    if defs:
        o.insert(1, "<defs>%s</defs>" % "".join(defs))

    # Beleuchtungsstrahl des gewaehlten Schirms
    hoehe = dict(SCHIRME)[det["schirm"]]
    d_tan = tangentendistanz_km(hoehe)
    pfad = " ".join("%s%.1f %.1f" % ("M" if i == 0 else "L", *px(d, strahlhoehe_km(d, d_tan)))
                    for i, d in enumerate(range(0, int(d_tan) + 1, 10)))
    o.append('<path d="%s" fill="none" stroke="#f0883e" stroke-width="2.5"/>' % pfad)
    xs, ys = px(d_tan, 0)
    o.append('<circle cx="%.1f" cy="%.1f" r="9" fill="#f0883e"/>' % (xs, ys))
    for a in range(0, 360, 45):
        import math
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#f0883e" '
                 'stroke-width="1.5" opacity=".7"/>'
                 % (xs + 12 * math.cos(math.radians(a)), ys + 12 * math.sin(math.radians(a)),
                    xs + 17 * math.cos(math.radians(a)), ys + 17 * math.sin(math.radians(a))))

    # Boden, Achsen
    gx0, gy = px(0, 0)
    gx1, _ = px(XMAX, 0)
    o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="10" fill="#21262d" '
             'stroke="#8b949e" stroke-width="0.7"/>' % (gx0, gy, gx1 - gx0))
    for z in (0, 2, 4, 6, 8, 10, 12):
        _, y = px(0, z)
        o.append('<text x="%.1f" y="%.1f" fill="#8b949e" font-size="11" '
                 'text-anchor="end">%d</text>' % (X0 - 8, y + 4, z))
    o.append('<text x="%.1f" y="%.1f" fill="#8b949e" font-size="11">km</text>'
             % (X0 - 30, Y0 - 8))
    for d in (0, 100, 200, 300, 400):
        x, _ = px(d, 0)
        o.append('<text x="%.1f" y="%.1f" fill="#8b949e" font-size="11" '
                 'text-anchor="middle">%d</text>' % (x, Y0 + HO + 28, d))
    o.append('<text x="%.1f" y="%.1f" fill="#8b949e" font-size="11" '
             'text-anchor="middle">km westlich</text>' % (X0 + BR + 30, Y0 + HO + 28))
    o.append('<text x="%.1f" y="%.1f" fill="#e6edf2" font-size="11" '
             'text-anchor="middle">Berlin</text>' % (X0, Y0 + HO + 44))

    # Beschriftung
    o.append('<text x="%d" y="26" fill="#e6edf2" font-size="15">%s %s · Azimut %.0f° '
             '· SU %02d:%02d UTC</text>'
             % (X0, WOCHENTAG[t.weekday()], t.strftime("%d.%m.%Y"), azimut,
                int(stunde), round((stunde % 1) * 60)))
    o.append('<text x="810" y="26" fill="#f0883e" font-size="20" text-anchor="end" '
             'font-weight="500">S = %.2f</text>' % s)
    o.append('<text x="810" y="44" fill="#8b949e" font-size="11" text-anchor="end">'
             'Schirm %s · Sicht %.2f · Weg %.2f</text>'
             % (det["schirm"], det["sicht"], det["weg"]))
    o.append('<text x="%.1f" y="%.1f" fill="#f0883e" font-size="11">Tangente %.0f km'
             '</text>' % (xs - 100, ys - 22, d_tan))
    o.append('<text x="%d" y="482" fill="#484f58" font-size="10">'
             'Hoehe %.0f-fach ueberhoeht · Wolken aus ERA5, Baenderdicke '
             'schematisch</text>' % (X0, (HO / YMAX) / (BR / XMAX)))
    o.append("</svg>")
    return "\n".join(o), s, det


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tage", nargs="+", help="YYYY-MM-DD")
    a = ap.parse_args()
    for tag in a.tage:
        feld = lade_feld(tag)
        if not feld:
            print("%s: keine Cachedaten" % tag)
            continue
        bild, s, det = svg(tag, feld)
        ziel = os.path.join(BASIS, "daten", "schnitt_%s.svg" % tag)
        with open(ziel, "w") as f:
            f.write(bild)
        print("%s  S=%.3f  %s" % (tag, s, ziel))


if __name__ == "__main__":
    main()
