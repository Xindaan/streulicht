"""Faecherkarte von oben: die Wolkendecke westlich von Berlin.

WOZU.  Der Vertikalschnitt (skripte/schnitt.py) zeigt, WIEVIEL Wolke der
Lichtweg trifft, aber nicht, WO westlich sie liegt.  Genau diese Frage ist
der Grund, warum eine Punktabfrage am Ort nicht reicht: eine Luecke bei
280 km Nordwest traegt den Abend, eine gleich grosse bei 280 km Suedwest
nicht, wenn die Sonne dort nicht untergeht.

Gezeichnet wird das FELD (ein Bild), beziffert wird nichts - jede Zahl auf
der Seite kommt aus dem Zustand, nicht aus dieser Datei.

Lauf einzeln:  .venv/bin/python3 skripte/faecher.py --tag 2026-08-25
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens  # noqa: E402
from sonnen.geometrie import zielpunkt  # noqa: E402
from sonnen.score import SCHIRME, faecherpunkte  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITTER = 0.5
BREITE, LAENGE = 52.52, 13.405
XMAX = 460.0                                    # km, wie im Vertikalschnitt

# Zeichenflaeche.  Der Ausschnitt richtet sich nach dem Azimut (ansicht()):
# bis zum 09.10.2026 stand Berlin fest rechts unten (392 | 186) fuer einen
# Faecher genau nach Westen - ausser um die Tagundnachtgleiche lag der
# Grossteil des Faechers ausserhalb des Bildes (Review physik#5: am 21.12.
# 4 von 35 Faecherpunkten im Bild, am 15.01. 6, am 08.10. 21).
# 420 x 258 wie der Vertikalschnitt (schnitt.FL_NEU): beide Karten sind im
# Desktopraster gleich hoch, und der Faecher bekommt genug Hoehe, um bei
# jedem Azimut mit rund 0,5 px/km hineinzupassen (bei 214 waren es 0,35-0,4).
VB = (420, 258)
SK_MAX = 0.60                                   # px je km, hoechstens
# Rand in px: links, oben, rechts, unten.  Oben bleibt Platz fuer die
# Zeile "Norden oben", unten fuer "Berlin" unter dem Ort.
RAND = (10.0, 30.0, 10.0, 24.0)
# Die Zellen werden etwas groesser gezeichnet als sie sind (siehe svg()).
UEBERSTAND = 1.18

KM_PRO_GRAD_LAT = 110.57
# cos(53.5 Grad): Mitte des Faechers, nicht Berlins Breite.  Auf 8 Grad
# Spannweite verzieht die Zellenbreite sonst sichtbar nach Norden.
KM_PRO_GRAD_LON = 111.32 * math.cos(math.radians(53.5))


def _tok(name):
    return tokens.werte()[name]


def _km(lat, lon):
    """(Ost, Nord) in km von Berlin."""
    return ((lon - LAENGE) * 111.32 * math.cos(math.radians(BREITE)),
            (lat - BREITE) * KM_PRO_GRAD_LAT)


def ansicht(azimut):
    """(cx, cy, sk): Lage von Berlin im Bild und Massstab (px je km).

    Eingepasst wird, was die Karte zeigen muss: die Kaestchen des Faechers
    (so gerastert wie im Alarmlauf: Mitte der 0,5-Grad-Zelle, plus ihre
    gezeichnete halbe Breite), Berlin und das Strahlende bei XMAX.  Der
    Massstab bleibt 0,60 px/km, solange alles hineinpasst, und schrumpft
    sonst gerade so weit, dass es passt (Suedwest im Winter).  Zentriert
    wird in dem Raum, den der Rand laesst.
    """
    punkte = [_km(BREITE, LAENGE),
              _km(*zielpunkt(BREITE, LAENGE, azimut, XMAX))]
    halb_x = GITTER * KM_PRO_GRAD_LON * UEBERSTAND / 2.0
    halb_y = GITTER * KM_PRO_GRAD_LAT * UEBERSTAND / 2.0
    ecken = []
    for _d, _dv, la, lo in faecherpunkte(BREITE, LAENGE, azimut):
        x, y = _km(round(la / GITTER) * GITTER, round(lo / GITTER) * GITTER)
        ecken += [(x - halb_x, y - halb_y), (x + halb_x, y + halb_y)]
    xs = [p[0] for p in punkte + ecken]
    ys = [p[1] for p in punkte + ecken]
    br_km, ho_km = max(xs) - min(xs), max(ys) - min(ys)
    frei_x = VB[0] - RAND[0] - RAND[2]
    frei_y = VB[1] - RAND[1] - RAND[3]
    sk = min(SK_MAX, frei_x / br_km, frei_y / ho_km)
    cx = RAND[0] + (frei_x - br_km * sk) / 2.0 - min(xs) * sk
    cy = RAND[1] + (frei_y - ho_km * sk) / 2.0 + max(ys) * sk
    return cx, cy, sk


# Ansicht fuer einen Faecher genau nach Westen: Vorgabe fuer punkt() ohne
# Ansicht, und der Bezugspunkt der Tests.
CX, CY, SK = ansicht(270.0)


def punkt(lat, lon, lage=None):
    """Bildpunkt (x, y) zu Breite und Laenge; `lage` = (cx, cy, sk)."""
    cx, cy, sk = lage or (CX, CY, SK)
    dx, dy = _km(lat, lon)
    return cx + dx * sk, cy - dy * sk


def svg(feld, azimut, schirm, d_tan):
    """Die Karte als SVG-Zeichenkette.

    `feld`   {"lat2/lon2": {schicht: prozent}} - die Zellen des Abfragefaechers
    `azimut` Sonnenuntergangsazimut in Grad
    `schirm` "low" | "mid" | "high" - das Niveau, das den Score getragen hat
    `d_tan`  Tangentendistanz in km; dort steht die Sonne am Horizont
    """
    VBW, VBH = VB
    # 1.18: die Zellen werden bewusst etwas groesser gezeichnet als sie sind.
    # Der Faecher tastet nicht jede Zelle des Rechtecks ab - zwischen zwei
    # abgetasteten liegen ungemessene, und exakt kantengenaue Rechtecke lassen
    # die Karte dadurch als Konfetti lesen statt als Decke.  Der Ueberstand
    # laesst benachbarte GEMESSENE Zellen verschmelzen; ungemessene Bereiche
    # bleiben dunkel, behaupten also weiterhin nichts.
    ueber = UEBERSTAND
    lage = ansicht(azimut)
    cx, cy, sk = lage
    cw = GITTER * KM_PRO_GRAD_LON * sk * ueber
    ch = GITTER * KM_PRO_GRAD_LAT * sk * ueber

    HIMMEL = _tok("--himmel-oben")
    DUMPF = _tok("--band-dumpf")
    GLUT = _tok("--band-glut")

    o = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" '
         'role="img" aria-label="Karte der Wolkendecke westlich von Berlin">'
         % (VBW, VBH),
         # `text:not([fill])`: eine Regel `text{fill}` schlaegt als Stylesheet
         # das fill-Attribut und machte die hervorgehobene Ortsmarke "Berlin"
         # grau (Review seiten#8).
         '<style>text{font-family:%s}text:not([fill]){fill:%s}</style>'
         % (_tok("--schrift"), _tok("--gedaempft")),
         '<defs>',
         '<filter id="decke" x="-15%" y="-15%" width="130%" height="130%">'
         '<feGaussianBlur stdDeviation="6"/></filter>',
         '<filter id="fweich" x="-30%" y="-60%" width="160%" height="220%">'
         '<feGaussianBlur stdDeviation="5"/></filter>',
         '<linearGradient id="fray" x1="1" x2="0" y1="0" y2="0">'
         '<stop offset="0" stop-color="%s" stop-opacity=".25"/>'
         '<stop offset=".58" stop-color="%s" stop-opacity=".9"/>'
         '<stop offset="1" stop-color="%s" stop-opacity=".12"/>'
         '</linearGradient>' % (_tok("--akzent"), GLUT, GLUT),
         '<clipPath id="frahmen"><rect width="%d" height="%d" rx="8"/>'
         '</clipPath>' % (VBW, VBH),
         '</defs>',
         '<rect width="%d" height="%d" rx="8" fill="%s"/>' % (VBW, VBH, HIMMEL),
         '<g clip-path="url(#frahmen)">']

    # --- Entfernungsringe --------------------------------------------------
    for km in (200, 400):
        o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" '
                 'stroke-width="0.9" stroke-dasharray="1 5"/>'
                 % (cx, cy, km * sk, _tok("--achse")))

    # --- Zellen: EINE Gruppe, EIN Blur ------------------------------------
    # Pro Zelle geblurrt saehe man 29 Kacheln mit weichen Kanten.  Erst der
    # Blur ueber die ganze Gruppe laesst sie zu einer Decke zusammenlaufen -
    # und das ist die Aussage: eine Decke mit Loechern, kein Mosaik.
    o.append('<g filter="url(#decke)" fill="%s">' % DUMPF)
    for schluessel, e in sorted(feld.items()):
        w = e.get(schirm)
        if w is None:
            continue
        a, b = schluessel.split("/")
        lat, lon = int(a) * GITTER, int(b) * GITTER
        x, y = punkt(lat, lon, lage)
        deck = max(0.0, min(1.0, w / 100.0))
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="5" '
                 'opacity="%.3f"/>'
                 % (x - cw / 2, y - ch / 2, cw, ch,
                    max(0.06, min(0.6, 0.6 * deck))))
    o.append('</g>')

    # --- Azimutstrahl bis zum Kartenrand -----------------------------------
    zx, zy = punkt(*zielpunkt(BREITE, LAENGE, azimut, XMAX), lage=lage)
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
             'stroke="url(#fray)" stroke-width="5" stroke-linecap="round" '
             'opacity=".45" filter="url(#fweich)"/>' % (cx, cy, zx, zy))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
             'stroke="url(#fray)" stroke-width="1.4" stroke-linecap="round"/>'
             % (cx, cy, zx, zy))

    # --- Tangentenpunkt: dort steht die Sonne auf dem Horizont -------------
    tx, ty = punkt(*zielpunkt(BREITE, LAENGE, azimut, d_tan), lage=lage)
    o.append('<circle cx="%.1f" cy="%.1f" r="13" fill="%s" opacity=".2" '
             'filter="url(#fweich)"/>' % (tx, ty, GLUT))
    o.append('<circle cx="%.1f" cy="%.1f" r="4.5" fill="%s"/>' % (tx, ty, GLUT))
    o.append('</g>')

    # --- Ort und Beschriftung ---------------------------------------------
    o.append('<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>'
             % (cx, cy, _tok("--tinte")))
    o.append('<text x="%.1f" y="%.1f" font-size="14" text-anchor="end" '
             'fill="%s">Berlin</text>' % (cx - 9, cy + 17, _tok("--tinte2")))
    # Die Ringzahlen sitzen dort, wo der Ring den Strahl kreuzt, knapp
    # darunter - bei festem Westfaecher lagen sie am Bildrand, mit
    # wandernder Ansicht kaeme der Ring dort nicht mehr vorbei.
    for km in (200, 400):
        rx, ry = punkt(*zielpunkt(BREITE, LAENGE, azimut, km), lage=lage)
        o.append('<text x="%.1f" y="%.1f" font-size="13" text-anchor="middle">'
                 '%d</text>' % (rx, ry + 16, km))
    # &#183; statt &middot;: benannte HTML-Entities sind in SVG/XML NICHT
    # definiert.  Inline in der HTML-Seite faellt das nicht auf, eine
    # eigenstaendige .svg-Datei bricht damit ab (geprueft 16.08.2026).
    o.append('<text x="12" y="20" font-size="13">Norden oben &#183; '
             'km von Berlin</text>')
    o.append('</svg>')
    return "".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--ort", default="berlin")
    ap.add_argument("--ziel", default="")
    a = ap.parse_args()

    with open(os.path.join(BASIS, "daten", "zustand.json")) as f:
        z = json.load(f)
    e = z[a.ort]["abende"][a.tag]
    schirm = e.get("schirm") or SCHIRME[0][0]
    from sonnen.geometrie import tangentendistanz_km
    bild = svg(e["feld"], e["azimut"], schirm,
               tangentendistanz_km(dict(SCHIRME)[schirm]))
    if a.ziel:
        with open(a.ziel, "w") as f:
            f.write(bild)
        print("%s (%.1f kB)" % (a.ziel, len(bild.encode()) / 1000))
    else:
        print(bild)


if __name__ == "__main__":
    main()
