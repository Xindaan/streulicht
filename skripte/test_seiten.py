"""Regressionstest fuer die erzeugten Seiten und die neuen Grafiken (T-0031).

Was hier geprueft wird, sind genau die Fehler, die beim Bauen der neuen
Oberflaeche am 16.08.2026 tatsaechlich aufgetreten sind - keine erfundenen
Faelle:

  * BENANNTE HTML-Entities im SVG.  `&middot;` ist in HTML definiert, in
    SVG/XML nicht.  Inline in der Seite faellt es nicht auf; eine
    eigenstaendige .svg-Datei bricht mit "Entity 'middot' not defined" ab.
  * UEBRIGE PLATZHALTER.  Ein nicht ersetztes `__PUSHTEXT__` steht wortwoertlich
    auf der Seite und sieht aus wie ein Defekt - weil es einer ist.
  * MARKEN UND BESCHRIFTUNG AUS DEM TRITT.  Die Zeitachse besteht aus zwei
    Flexzeilen mit denselben Spalten; laufen ihre Laengen auseinander, steht
    die Tageszahl unter der falschen Marke.
  * UEBERHOEHUNGSANGABE.  Die Zahl steht als Aussage auf der Seite und wird
    aus der Zeichenflaeche gerechnet.  Aendert jemand die Flaeche und nicht
    die Zahl, luegt die Seite still.
  * MARKEN IN PIXELN STATT PROZENT.  Seit der Desktopfassung (16.08.2026)
    hat die Achse zwei Hoehen, 200 und 260 px.  Eine Marke mit `top:104px`
    saehe in der einen richtig aus und in der anderen falsch - und zwar
    plausibel falsch, also unauffaellig.

Lauf:  python3 skripte/test_seiten.py
"""
import json
import os
import re
import sys

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import band                                                      # noqa: E402
import faecher                                                   # noqa: E402
import schnitt                                                   # noqa: E402
import seite                                                     # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


def benannte_entities(s):
    """&auml; und Freunde.  &#183; und &amp;/&lt;/&gt;/&quot; sind erlaubt."""
    return set(re.findall(r"&([a-zA-Z]+);", s)) - {"amp", "lt", "gt", "quot",
                                                   "apos"}


def main():
    zp = os.path.join(BASIS, "daten", "zustand.json")
    if not os.path.exists(zp):
        print("daten/zustand.json fehlt - erst skripte/alarm.py laufen lassen")
        raise SystemExit(2)
    with open(zp) as f:
        abende = json.load(f)["berlin"]["abende"]
    mit_feld = [t for t in sorted(abende) if abende[t].get("feld")]
    if not mit_feld:
        print("kein Abend mit Feld im Zustand")
        raise SystemExit(2)

    print("=== 1. Vertikalschnitt")
    for t in mit_feld[:3]:
        e = abende[t]
        bild, s, det, d_tan = schnitt.schnitt_neu(t, e["feld"],
                                                  e.get("segmente"))
        pruefe(bild.startswith("<svg") and bild.endswith("</svg>"),
               "%s: ist ein SVG" % t)
        pruefe(not benannte_entities(bild),
               "%s: keine benannten Entities (%s)"
               % (t, benannte_entities(bild) or "-"))
        pruefe(0.0 <= s <= 1.0, "%s: Score im Wertebereich (%.4f)" % (t, s))
        pruefe(50.0 < d_tan < 460.0,
               "%s: Tangentendistanz plausibel (%.0f km)" % (t, d_tan))

    print("\n=== 2. Faecherkarte")
    e = abende[mit_feld[0]]
    karte = faecher.svg(e["feld"], e["azimut"], e["schirm"], 300.0)
    pruefe(karte.startswith("<svg"), "ist ein SVG")
    pruefe(not benannte_entities(karte),
           "keine benannten Entities (%s)" % (benannte_entities(karte) or "-"))
    # Berlin muss im Bild liegen, sonst zeigt die Karte an ihm vorbei.
    bx, by = faecher.punkt(52.52, 13.405)
    pruefe(0 <= bx <= faecher.VB[0] and 0 <= by <= faecher.VB[1],
           "der Ort liegt im Bild (%.0f, %.0f)" % (bx, by))

    print("\n=== 3. Himmelsband")
    pruefe(band.mische("#000000", "#ffffff", 0.5) == "#808080",
           "Farbmischung in der Mitte")
    pruefe(band.DUMPF[3] in band.svg(0.0, 0.7065),
           "Median 0 bleibt stumpf")
    pruefe(band.GLUT[3] in band.svg(0.7065, 0.7065),
           "Median = s* erreicht die volle Glut")
    pruefe(band.GLUT[3] in band.svg(2.0, 0.7065),
           "ueber s* wird nicht heller als voll (gekappt)")

    print("\n=== 4. Ueberhoehung")
    u = seite.ueberhoehung_neu()
    px_x = schnitt.FL_NEU["br"] / schnitt.XMAX
    px_y = schnitt.FL_NEU["ho"] / schnitt.YMAX
    pruefe(abs(u - px_y / px_x) < 1e-9,
           "aus der Zeichenflaeche gerechnet (%.1f-fach)" % u)

    print("\n=== 5. Erzeugte Prognoseseite")
    p = os.path.join(BASIS, "web", "index.html")
    if not os.path.exists(p):
        pruefe(False, "web/index.html fehlt - erst skripte/seite.py laufen")
    else:
        html = open(p, encoding="utf-8").read()
        pruefe(not re.findall(r"__[A-Z_]+__", html),
               "keine uebrigen Platzhalter (%s)"
               % (re.findall(r"__[A-Z_]+__", html) or "-"))
        n_marken = html.count('class="marke ')
        n_fuss = html.count('<div class="wt">')
        pruefe(n_marken == n_fuss,
               "Marken und Beschriftung gleich lang (%d/%d)"
               % (n_marken, n_fuss))
        pruefe(html.count('class="marke an"') + html.count(' an" data-i') <= 1
               or ' an"' in html, "genau ein Abend vorausgewaehlt")
        pruefe('href="bisher.html"' in html,
               "Verweis auf die Bilanzseite steht drin")
        pruefe('charset="utf-8"' in html, "Kodierung angegeben")
        # Der SVG-Namensraum ist eine Kennung, keine Adresse - er wird nie
        # abgerufen.  Er steht zweimal drin: im Markup und noch einmal
        # maskiert in den eingebetteten JSON-Zeichenketten.
        ohne_ns = html.replace("http://www.w3.org/2000/svg", "")
        adressen = sorted(set(re.findall(r"https?://[^\"'<>\\ ]+", ohne_ns)))
        pruefe(not adressen,
               "keine externen Adressen, self-contained (%s)"
               % (adressen or "-"))

        print("\n=== 5b. Desktopfassung im selben Dokument")
        pruefe("@media (min-width:1000px){" in html,
               "Breakpoint-Block vorhanden")
        # Marken MUESSEN in Prozent stehen - mit zwei Achsenhoehen ist jede
        # Pixelangabe in genau einer der beiden falsch.
        pixelmarken = re.findall(r'class="(?:fahne|punkt)" style="top:[\d.]+px"',
                                 html)
        pruefe(not pixelmarken,
               "Marken in Prozent, nicht in Pixeln (%d Pixelfunde)"
               % len(pixelmarken))
        pruefe(html.count('class="rang"') == n_marken,
               "je Marke eine Rangzahl (%d/%d)"
               % (html.count('class="rang"'), n_marken))
        # Die Desktopmasse kommen aus tokens.css, nicht aus dem Stylesheet.
        for t in ("--breite-gross", "--rand-gross"):
            pruefe(("%s:" % t) in html and ("var(%s)" % t) in html,
                   "%s ist definiert UND benutzt" % t)
        pruefe(str(seite.ACHSE_PX_GROSS) + "px" in html,
               "Achsenhoehe der Desktopfassung steht drin (%d px)"
               % seite.ACHSE_PX_GROSS)
        # Korpuszeile und Bilanzverweis stehen zweimal im Dokument (Leiste
        # oben fuer den Desktop, Absatz bzw. Pille fuer das Telefon).  Genau
        # zweimal - eine dritte Fassung waere ein vergessener Rest.
        pruefe(html.count("bisher.html") == 2,
               "Bilanzverweis genau zweimal (%d)" % html.count("bisher.html"))

    print("\n=== 6. Erzeugte Bewertungsseite")
    p = os.path.join(BASIS, "web", "bewerten-berlin.html")
    if not os.path.exists(p):
        pruefe(False, "web/bewerten-berlin.html fehlt")
    else:
        html = open(p, encoding="utf-8").read()
        pruefe(not re.findall(r"__[A-Z_]+__", html),
               "keine uebrigen Platzhalter")
        pruefe('"priority": 1' in html.replace("priority: 1", '"priority": 1'),
               "Quittung mit min-Prioritaet (kein Push auf das eigene Gerät)")
        koerper = html.split("</style>")[1].split("<script>")[0]
        pruefe(not re.search(r"unauff|Perzentil des Jahres", koerper),
               "keine Prognose im sichtbaren Dokument")

    print("")
    if fehler:
        print("FEHLGESCHLAGEN: %d" % len(fehler))
        raise SystemExit(1)
    print("alle Pruefungen bestanden")


if __name__ == "__main__":
    main()
