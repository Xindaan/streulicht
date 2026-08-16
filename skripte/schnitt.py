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

ZWEI FASSUNGEN (T-0010, 14.08.2026).  Gemessen auf dem Telefon: bei
viewBox-Breite 840 auf 343 px Anzeige schrumpft Grad 11 auf 4.3 px, Grad 9
auf 3.5 px - das Bild, das "die Idee in einer Sekunde erklaert", war auf dem
Hauptgeraet unlesbar.  Deshalb:

    kompakt=False   ausfuehrlich, 840x490, alle Diagnosezahlen.
                    Fuer diagnose.html und rueckschau.html.
    kompakt=True    420x300, grosse Grade, NUR Bild und Achsen.
                    Fuer die Produktseite.

Grundsatz dahinter: Text, den man lesen muss, gehoert ins HTML, nicht ins
SVG.  Im SVG steht nur, was von seiner Position lebt - Achsenzahlen und der
Ortsname.  Datum, Stufe, S-Wert und der Ueberhoehungshinweis stehen auf der
Produktseite als echter Text in der Seitentypografie.

Farben kommen ausnahmslos aus stil/tokens.css (siehe skripte/tokens.py).
Geschrieben wird var(--name, <Fallback>); der Fallback stammt ebenfalls aus
der Token-Datei und traegt die Seiten, die sie nicht inlinen.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens  # noqa: E402
from sonnen.geometrie import (NIVEAU_HOEHE_KM, sonnenuntergang,  # noqa: E402
                              strahlhoehe_km, tangentendistanz_km, zielpunkt)
from sonnen.score import (DISTANZEN_KM, GRENZE_LOW_MID_KM,  # noqa: E402
                          GRENZE_MID_HIGH_KM, SCHIRME, faecherpunkte, score)

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITTER = 0.5
BREITE, LAENGE = 52.52, 13.405
XMAX, YMAX = 460.0, 12.5                   # km
WOCHENTAG = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")

# Zeichenflaechen.  vb = viewBox, x0/y0/br/ho = Plotrahmen darin.
FLAECHEN = {
    False: dict(vb=(840, 490), x0=70, y0=40, br=700, ho=380,
                grad=11, grad_klein=10, strich=0.5,
                hoehen=(0, 2, 4, 6, 8, 10, 12),
                weiten=(0, 100, 200, 300, 400),
                sonne=(9, 12, 17)),
    # grad=15: die Produktseite deckelt das Bild auf --breite-bild und
    # zeigt es auf dem Telefon auf rund 319 px.  420 -> 319 ist Faktor
    # 0.76, also landet Grad 15 bei 11.4 px - knapp ueber der Grenze, ab
    # der Beschriftung anfaengt, Dekoration zu werden.
    True: dict(vb=(420, 300), x0=40, y0=22, br=350, ho=208,
               grad=15, grad_klein=13, strich=0.8,
               hoehen=(0, 4, 8, 12),
               weiten=(0, 200, 400),
               sonne=(7, 9, 13)),
}


def farbe(name):
    """var(--name, <Wert aus stil/tokens.css>).

    Der Fallback ist kein Duplikat von Hand - er wird aus derselben Datei
    gelesen.  Er traegt diagnose.html und rueckschau.html, die tokens.css
    nicht inlinen und in denen var(--papier) sonst ins Leere liefe.
    """
    return "var(%s, %s)" % (name, tokens.werte()[name])


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


def svg(tag, feld, kompakt=False):
    from datetime import date as _d
    fl = FLAECHEN[bool(kompakt)]
    X0, Y0, BR, HO = fl["x0"], fl["y0"], fl["br"], fl["ho"]
    VBW, VBH = fl["vb"]

    def px(d_km, z_km):
        return (X0 + BR * d_km / XMAX, Y0 + HO * (1.0 - z_km / YMAX))

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

    # Die Schrift kommt aus dem Token, nicht als Attribut: so erbt das
    # eingebettete SVG die Seitentypografie, und die Einzeldatei faellt auf
    # denselben Stack zurueck.
    o = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">'
         % (VBW, VBH),
         '<style>text{font-family:%s;fill:%s}</style>'
         % (tokens.werte()["--schrift"], farbe("--gedaempft")),
         '<rect width="%d" height="%d" fill="%s"/>'
         % (VBW, VBH, farbe("--karte"))]
    for _z in fl["hoehen"]:
        if _z == 0:
            continue
        _, _y = px(0, _z)
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                 'stroke-width="%.1f"/>'
                 % (X0, _y, X0 + BR, _y, farbe("--achse"), fl["strich"]))

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
            stops.append('<stop offset="%.4f" stop-color="%s" '
                         'stop-opacity="%.3f"/>'
                         % (d / XMAX, farbe("--wolke"), min(0.80, 0.62 * c)))
            d += SCHRITT
        if not any('stop-opacity="0.0' not in x for x in stops):
            continue
        defs.append('<linearGradient id="g%d" x1="0" x2="1" y1="0" y2="0">%s'
                    '</linearGradient>' % (nr, "".join(stops)))
        # vertikale Weichzeichnung der Ober- und Unterkante.  Schwarz/Weiss
        # sind hier keine Farben, sondern Maskenwerte (0 und 1) - die duerfen
        # nicht aus der Palette kommen.
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
        o.insert(2, "<defs>%s</defs>" % "".join(defs))

    # Beleuchtungsstrahl. Die HELLIGKEIT je Abschnitt ist die verbleibende
    # Transmission - der Strahl IST das Licht, nicht seine Illustration.
    # Ohne das zeichnet man eine gleichmaessig helle Kurve durch eine
    # geschlossene Wolkendecke und behauptet damit das Gegenteil dessen,
    # was der Score gerade ausgerechnet hat.
    hoehe = dict(SCHIRME)[det["schirm"]]
    d_tan = tangentendistanz_km(hoehe)

    def transmission_bei(d):
        """Anteil des Lichts, der von der Tangente bis hierher uebrig ist."""
        rest = 1.0
        for d_nah, d_fern, _sch, c in reversed(det.get("segmente", [])):
            if d >= d_fern:
                continue
            rest *= (1.0 - c)
        return rest

    schritt = 8
    for d in range(0, int(d_tan), schritt):
        d1 = min(d + schritt, d_tan)
        x0, y0 = px(d, strahlhoehe_km(d, d_tan))
        x1, y1 = px(d1, strahlhoehe_km(d1, d_tan))
        tr = transmission_bei(0.5 * (d + d1))
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                 'stroke="%s" stroke-width="%.1f" stroke-linecap="round"/>'
                 % (x0, y0, x1, y1,
                    tokens.mischen("--strahl-dunkel", "--strahl-hell", tr),
                    1.4 + 2.2 * tr))

    # Segmentmarken: wo genau geht wie viel verloren.  Diagnose, nicht
    # Produkt - auf dem Telefon waeren die Zahlen 3.5 px hoch.
    if not kompakt:
        for d_nah, d_fern, _sch, c in det.get("segmente", []):
            if c < 0.05 or 0.5 * (d_nah + d_fern) > d_tan - 45:
                continue
            xm, ym = px(0.5 * (d_nah + d_fern),
                        strahlhoehe_km(0.5 * (d_nah + d_fern), d_tan))
            o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" '
                     'stroke="%s" stroke-width="1.2" opacity="%.2f"/>'
                     % (xm, ym, 3 + 7 * c, farbe("--akzent"), 0.35 + 0.5 * c))
            o.append('<text x="%.1f" y="%.1f" fill="%s" font-size="9" '
                     'text-anchor="middle">-%.0f%%</text>'
                     % (xm, ym - 12 - 7 * c, farbe("--akzent"), 100 * c))

    r_kern, r_innen, r_aussen = fl["sonne"]
    xs, ys = px(d_tan, 0)
    o.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="%s"/>'
             % (xs, ys, r_kern, farbe("--akzent-tinte")))
    for a in range(0, 360, 45):
        import math
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                 'stroke-width="1.5" opacity=".7"/>'
                 % (xs + r_innen * math.cos(math.radians(a)),
                    ys + r_innen * math.sin(math.radians(a)),
                    xs + r_aussen * math.cos(math.radians(a)),
                    ys + r_aussen * math.sin(math.radians(a)),
                    farbe("--akzent-tinte")))

    # Boden, Achsen
    gx0, gy = px(0, 0)
    gx1, _ = px(XMAX, 0)
    o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%d" fill="%s" '
             'stroke="%s" stroke-width="0.7"/>'
             % (gx0, gy, gx1 - gx0, 6 if kompakt else 10,
                farbe("--boden"), farbe("--gitter")))
    for z in fl["hoehen"]:
        _, y = px(0, z)
        o.append('<text x="%.1f" y="%.1f" font-size="%d" '
                 'text-anchor="end">%d</text>'
                 % (X0 - 8, y + 4, fl["grad"], z))
    o.append('<text x="%.1f" y="%.1f" font-size="%d">km</text>'
             % (X0 - (22 if kompakt else 30), Y0 - 8, fl["grad"]))
    y_zahlen = Y0 + HO + (26 if kompakt else 28)
    y_namen = Y0 + HO + (46 if kompakt else 44)
    for d in fl["weiten"]:
        x, _ = px(d, 0)
        o.append('<text x="%.1f" y="%.1f" font-size="%d" '
                 'text-anchor="middle">%d</text>' % (x, y_zahlen, fl["grad"], d))
    # Kompakt sitzt die Achsenbeschriftung eine Zeile tiefer und rechtsbuendig
    # am Plotrand - rechts daneben ist im 420er Kasten kein Platz mehr.
    if kompakt:
        o.append('<text x="%.1f" y="%.1f" font-size="%d" text-anchor="end">'
                 'km westlich</text>' % (X0 + BR, y_namen, fl["grad"]))
    else:
        o.append('<text x="%.1f" y="%.1f" font-size="%d" '
                 'text-anchor="middle">km westlich</text>'
                 % (X0 + BR + 30, y_zahlen, fl["grad"]))
    o.append('<text x="%.1f" y="%.1f" font-size="%d" fill="%s" '
             'text-anchor="middle">Berlin</text>'
             % (X0, y_namen, fl["grad"], farbe("--tinte2")))

    # Beschriftung.  Nur ausfuehrlich - auf der Produktseite steht das alles
    # als echter Text in der Seitentypografie ueber und unter dem Bild.
    if not kompakt:
        o.append('<text x="%d" y="26" fill="%s" font-size="15">%s %s '
                 '&#183; Azimut %.0f&#176; &#183; SU %02d:%02d UTC</text>'
                 % (X0, farbe("--tinte"), WOCHENTAG[t.weekday()],
                    t.strftime("%d.%m.%Y"), azimut,
                    int(stunde), round((stunde % 1) * 60)))
        o.append('<text x="810" y="26" fill="%s" font-size="20" '
                 'text-anchor="end" font-weight="500">S = %.2f</text>'
                 % (farbe("--akzent-tinte"), s))
        o.append('<text x="810" y="44" font-size="11" text-anchor="end">'
                 'Schirm %s &#183; Sicht %.2f &#183; Weg %.2f</text>'
                 % (det["schirm"], det["sicht"], det["weg"]))
        o.append('<text x="%.1f" y="%.1f" fill="%s" font-size="11" '
                 'text-anchor="middle">Tangente %.0f km</text>'
                 % (xs, ys - 46, farbe("--akzent-tinte"), d_tan))
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                 'stroke-width="0.5" stroke-dasharray="2 2" opacity=".6"/>'
                 % (xs, ys - 40, xs, ys - 20, farbe("--akzent-tinte")))
        o.append('<text x="%d" y="482" font-size="10">'
                 'Hoehe %.0f-fach ueberhoeht &#183; Wolken aus ERA5, '
                 'Baenderdicke schematisch</text>'
                 % (X0, (HO / YMAX) / (BR / XMAX)))
    o.append("</svg>")
    return "\n".join(o), s, det


def ueberhoehung(kompakt=False):
    """Faktor, um den die Hoehenachse gestreckt ist.

    Die Produktseite schreibt ihn als echten Text unter das Bild - im SVG
    waere er auf dem Telefon 3.9 px hoch, und ohne ihn behauptet die
    Zeichnung eine Geometrie, die sie nicht hat.
    """
    fl = FLAECHEN[bool(kompakt)]
    return (fl["ho"] / YMAX) / (fl["br"] / XMAX)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tage", nargs="+", help="YYYY-MM-DD")
    ap.add_argument("--kompakt", action="store_true",
                    help="kleine Fassung fuer die Produktseite")
    a = ap.parse_args()
    for tag in a.tage:
        feld = lade_feld(tag)
        if not feld:
            print("%s: keine Cachedaten" % tag)
            continue
        bild, s, det = svg(tag, feld, kompakt=a.kompakt)
        ziel = os.path.join(BASIS, "daten", "schnitt_%s.svg" % tag)
        with open(ziel, "w") as f:
            f.write(bild)
        print("%s  S=%.3f  %s" % (tag, s, ziel))


if __name__ == "__main__":
    main()


# ===========================================================================
# Neue Fassung des Vertikalschnitts (Entwurf 16.08.2026, Handoff 1.6).
#
# Warum daneben statt darin: die alte Fassung traegt diagnose.html und
# rueckschau.html in 840 x 490 und ist dort richtig.  Der Handoff laesst sie
# ausdruecklich unveraendert; hier entsteht nur die Telefonfassung.
#
# Der Unterschied ist nicht Kosmetik.  Ein graues Rechteck behauptet eine
# gleichmaessige Platte - die Kontur wird jetzt dort schmal, wo weniger Wolke
# ist, und liest sich dadurch als Wolke.  Der Strahl wird doppelt gezeichnet
# (Glut darunter, klare Linie darueber), weil eine einzelne Linie bei hoher
# Transmission duenn und unwichtig aussieht, obwohl sie das Ereignis ist.
# ===========================================================================

from datetime import date as _datum  # noqa: E402

FL_NEU = dict(vb=(420, 258), x0=44, y0=16, br=346, ho=190)
BAENDER = (("high", 7.6, 10.4), ("mid", 2.9, 5.4), ("low", 0.25, 1.6))


def _mische(a, b, t):
    """Farbmischung zweier #rrggbb, t in [0,1]."""
    t = max(0.0, min(1.0, t))
    ha, hb = a.lstrip("#"), b.lstrip("#")
    return "#%02x%02x%02x" % tuple(
        round(int(ha[i:i + 2], 16) + t * (int(hb[i:i + 2], 16)
                                          - int(ha[i:i + 2], 16)))
        for i in (0, 2, 4))


def _tok(name):
    """Reiner Tokenwert ohne var() - fuer Berechnungen und Verlaufsstopps."""
    return tokens.werte()[name]


def schnitt_neu(tag, feld, segmente=None, breite=BREITE, laenge=LAENGE):
    """Vertikalschnitt fuer die Produktseite.  Gibt nur das SVG zurueck.

    `segmente` ist die Segmentliste des Score-Laufs [(d_nah, d_fern, Schichten,
    Bedeckung)].  Liegt sie vor, traegt sie die Transmission - das ist DIE
    Rechnung, die auch den Score gemacht hat.  Fehlt sie, werden die Ringe aus
    dem Feld nachgerechnet; fuer das Bild vertretbar, aber eine zweite Rechnung
    neben der ersten.
    """
    fl = FL_NEU
    X0, Y0, BR, HO = fl["x0"], fl["y0"], fl["br"], fl["ho"]
    VBW, VBH = fl["vb"]

    def px(d_km, z_km):
        return (X0 + BR * d_km / XMAX, Y0 + HO * (1.0 - z_km / YMAX))

    t = _datum.fromisoformat(tag) if isinstance(tag, str) else tag
    stunde, azimut = sonnenuntergang(t, breite, laenge)
    punkte = {(d, dv): (la, lo) for d, dv, la, lo in
              faecherpunkte(breite, laenge, azimut)}

    def hole(d, dv, schicht):
        p = punkte.get((d, dv))
        if p is None:
            return None
        e = feld.get(zelle(*p))
        if e is None or e.get(schicht) is None:
            return None
        return e[schicht] / 100.0

    def deckung(d, schicht):
        """Linear zwischen den Stuetzstellen.  Ohne das rasten die Baender auf
        die 0.5-Grad-Zelle und bekommen Treppenkanten, die wie Struktur
        aussehen und keine sind."""
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

    s_wert, det = score(hole)
    name = (det or {}).get("schirm") or SCHIRME[0][0]
    hoehe = dict(SCHIRME)[name]
    d_tan = tangentendistanz_km(hoehe)

    # --- Transmission je Ring ---------------------------------------------
    if segmente:
        ringe = [(a, b, c) for a, b, _sch, c in segmente]
    else:
        ringe = []
        for a, b in zip(DISTANZEN_KM, DISTANZEN_KM[1:]):
            if a >= d_tan:
                break
            b = min(b, d_tan)
            zh = strahlhoehe_km(0.5 * (a + b), d_tan)
            sch = ("low" if zh < GRENZE_LOW_MID_KM
                   else ("mid" if zh < GRENZE_MID_HIGH_KM else "high"))
            ringe.append((a, b, deckung(0.5 * (a + b), sch)))

    def rest(d):
        r = 1.0
        for a, b, c in ringe:
            if d < b:
                r *= (1.0 - (c or 0.0))
        return r

    HIMMEL_O, HIMMEL_U = _tok("--himmel-oben"), _tok("--himmel-unten")
    DUMPF, GLUT = _tok("--band-dumpf"), _tok("--band-glut")
    DUNKEL = _tok("--strahl-dunkel")

    o = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" '
         'role="img" aria-label="Vertikalschnitt nach Westen">' % (VBW, VBH),
         '<style>text{font-family:%s;fill:%s}</style>'
         % (_tok("--schrift"), farbe("--gedaempft")),
         '<defs>',
         '<linearGradient id="himmel" x1="0" x2="0" y1="0" y2="1">'
         '<stop offset="0" stop-color="%s"/>'
         '<stop offset="1" stop-color="%s"/></linearGradient>' % (HIMMEL_O, HIMMEL_U),
         '<filter id="weich" x="-20%" y="-40%" width="140%" height="180%">'
         '<feGaussianBlur stdDeviation="2.6"/></filter>',
         '<filter id="glut" x="-20%" y="-60%" width="140%" height="220%">'
         '<feGaussianBlur stdDeviation="3.2"/></filter>',
         '<clipPath id="rahmen"><rect x="%.1f" y="%.1f" width="%.1f" '
         'height="%.1f" rx="6"/></clipPath>' % (X0, Y0, BR, HO)]

    # Verlauf je Band: die Deckkraft traegt die Bedeckung, nicht die Farbe.
    sichtbar = []
    for nr, (sch, unten, oben) in enumerate(BAENDER):
        werte_b = [deckung(d, sch) for d in range(0, int(XMAX) + 1, 10)]
        if max(werte_b) <= 0.02:
            continue
        sichtbar.append((nr, sch, unten, oben))
        stopps = []
        for d in range(0, int(XMAX) + 1, 60):
            c = deckung(d, sch)
            stopps.append('<stop offset="%.3f" stop-color="%s" '
                          'stop-opacity="%.3f"/>'
                          % (d / XMAX, DUMPF, min(0.85, 0.72 * c)))
        o.append('<linearGradient id="cg%d" x1="0" x2="1" y1="0" y2="0">%s'
                 '</linearGradient>' % (nr, "".join(stopps)))

    sx, sy = px(d_tan, 0.0)
    t0 = rest(0.0)
    o.append('<radialGradient id="halo"><stop offset="0" stop-color="%s" '
             'stop-opacity=".55"/><stop offset="1" stop-color="%s" '
             'stop-opacity="0"/></radialGradient>' % (GLUT, GLUT))
    o.append('<radialGradient id="waesche"><stop offset="0" stop-color="%s" '
             'stop-opacity="%.3f"/><stop offset=".55" stop-color="%s" '
             'stop-opacity="%.3f"/><stop offset="1" stop-color="%s" '
             'stop-opacity="0"/></radialGradient>'
             % (GLUT, 0.55 * t0, GLUT, 0.22 * t0, GLUT))
    o.append('</defs>')

    o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="6" '
             'fill="url(#himmel)"/>' % (X0, Y0, BR, HO))
    o.append('<g clip-path="url(#rahmen)">')

    # --- Wolkenbaender als Polygon ----------------------------------------
    for nr, sch, unten, oben in sichtbar:
        zc, halb = 0.5 * (unten + oben), 0.5 * (oben - unten)
        obe, unt = [], []
        for d in range(0, int(XMAX) + 1, 10):
            f = 0.28 + 0.72 * min(1.0, deckung(d, sch))
            obe.append(px(d, zc + halb * f))
            unt.append(px(d, zc - halb * f))
        pfad = " ".join("%.1f,%.1f" % p for p in obe + list(reversed(unt)))
        o.append('<polygon points="%s" fill="url(#cg%d)" filter="url(#weich)"/>'
                 % (pfad, nr))

    # --- Horizontwaesche: das Licht, das unter der Decke ankommt -----------
    o.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="38" '
             'fill="url(#waesche)"/>' % (sx, sy, max(30.0, sx - X0 + 30.0)))

    # --- Strahl, doppelt: Glut darunter, klare Linie darueber -------------
    # Der Filter haengt am GRUPPENelement, nicht an jeder Linie.  Pro Linie
    # waere es eine eigene Filterflaeche - bei ~50 Segmenten sichtbar traege
    # auf dem Telefon, und die Ueberlappungen addieren sich zu Baendern.
    stufen = []
    for d in range(0, int(d_tan), 8):
        d2 = min(d + 8, d_tan)
        tr = rest(0.5 * (d + d2))
        stufen.append((px(d, strahlhoehe_km(d, d_tan)),
                       px(d2, strahlhoehe_km(d2, d_tan)),
                       tr, _mische(DUNKEL, GLUT, tr)))
    o.append('<g filter="url(#glut)" stroke-linecap="round">')
    for (x1, y1), (x2, y2), tr, f in stufen:
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                 'stroke-width="%.2f" opacity="%.3f"/>'
                 % (x1, y1, x2, y2, f, 3.0 + 6.0 * tr, 0.18 + 0.42 * tr))
    o.append('</g><g stroke-linecap="round">')
    for (x1, y1), (x2, y2), tr, f in stufen:
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                 'stroke-width="%.2f"/>' % (x1, y1, x2, y2, f, 1.3 + 1.9 * tr))
    o.append('</g>')

    # --- Sonne: Halo statt Zacken -----------------------------------------
    o.append('<ellipse cx="%.1f" cy="%.1f" rx="54" ry="30" fill="url(#halo)"/>'
             % (sx, sy - 6))
    o.append('<circle cx="%.1f" cy="%.1f" r="16" fill="%s" opacity=".22" '
             'filter="url(#glut)"/>' % (sx, sy - 6, GLUT))
    o.append('<circle cx="%.1f" cy="%.1f" r="6.5" fill="%s"/>'
             % (sx, sy - 6, GLUT))
    o.append('</g>')

    # --- Boden und Ortsstrich ---------------------------------------------
    gx0, gy = px(0.0, 0.0)
    gx1, _ = px(XMAX, 0.0)
    o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="5" fill="%s" '
             'stroke="%s" stroke-width="0.7"/>'
             % (gx0, gy, gx1 - gx0, farbe("--boden"), farbe("--gitter")))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
             'stroke-width="1.2"/>' % (gx0, gy - 7, gx0, gy + 5, farbe("--tinte2")))

    # --- Beschriftung: nur Achsenzahlen, alles Lesbare gehoert ins HTML ----
    for z in (0, 4, 8, 12):
        _, y = px(0.0, z)
        o.append('<text x="%.1f" y="%.1f" font-size="15" text-anchor="end">%d'
                 '</text>' % (X0 - 9, y + 5, z))
    # "km" gehoert UEBER die Zahlenspalte, nicht daneben: neben der 12 stossen
    # beide zusammen, weil beide rechtsbuendig auf dieselbe Kante laufen.
    o.append('<text x="%.1f" y="%.1f" font-size="13" text-anchor="end">km</text>'
             % (X0 - 9, Y0 - 4))
    for d in (0, 200, 400):
        x, _ = px(d, 0.0)
        o.append('<text x="%.1f" y="%.1f" font-size="15" text-anchor="middle">'
                 '%d</text>' % (x, gy + 26, d))
    o.append('<text x="%.1f" y="%.1f" font-size="15" text-anchor="end">'
             'km westlich</text>' % (gx1, gy + 46))
    o.append('<text x="%.1f" y="%.1f" font-size="15" text-anchor="middle" '
             'fill="%s">Berlin</text>' % (gx0, gy + 46, farbe("--tinte2")))
    o.append('</svg>')
    return "".join(o), s_wert, det, d_tan
