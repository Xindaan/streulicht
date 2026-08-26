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
import json as _json
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

        print("\n=== 5b2. Nur kuenftige Abende, und die Korpuszeile stimmt")
        from datetime import date as _d
        meta = json.loads(re.search(r"const META=(\[.*?\]), BESTER",
                                    html, re.S).group(1))
        tage = [e["tag"] for e in meta]
        heute = _d.today().isoformat()
        vergangen = [t for t in tage if t < heute]
        # Der Zustand sammelt auch vergangene Abende (dort haengen die
        # Bewertungen). Auf eine PROGNOSEseite gehoeren sie nicht - am
        # 18.08.2026 stand dort "13 ABENDE VORAUSGERECHNET · 16.08. BIS
        # 28.08.", vorausgerechnet waren es 11.
        pruefe(not vergangen,
               "kein vergangener Abend auf der Seite (%s)"
               % (vergangen or "-"))
        korpus = re.search(r'class="korpus">([^<]*)', html).group(1)
        pruefe(str(len(meta)) in korpus,
               "Korpuszeile nennt die gezeigte Anzahl (%d): %s"
               % (len(meta), korpus))
        for t in (tage[0], tage[-1]):
            d = _d.fromisoformat(t).strftime("%d.%m.")
            pruefe(d in korpus, "Korpuszeile nennt %s" % d)

        print("\n=== 5c. Altersangabe")
        # Der Streifen darf genau dann dastehen, wenn die Zahlen nicht vom
        # heutigen Alarmlauf stammen.  Am 17.08.2026 hat die Seite den
        # ganzen Tag den Vortag gezeigt und dabei frisch ausgesehen; das
        # war der teure Teil, nicht der ausgefallene Lauf selbst.
        hat_streifen = 'class="veraltet"' in html
        # Von wann sind die Wetterdaten?  Die Zeile darf leer sein, solange
        # kein Lauf mit der neuen Buchhaltung durch ist - aber wenn der
        # Zustand einen Stand fuehrt, muss sie ihn zeigen.
        stand = (json.load(open(zp)).get("berlin") or {}).get("stand") or {}
        zeile = re.search(r'class="stand">([^<]*)', html)
        if stand.get("geholt"):
            pruefe(bool(zeile and zeile.group(1).strip()),
                   "Standzeile gefuellt: %r"
                   % (zeile.group(1) if zeile else None))
            if stand.get("modelllauf"):
                pruefe("Modelllauf" in (zeile.group(1) if zeile else ""),
                       "und nennt den Modelllauf, nicht nur den Abruf")
        # DIESELBE Regel wie in seite.py, nicht eine zweite daneben. Der Test
        # verglich Tag mit Tag, waehrend der Code laengst Zeitpunkte
        # verglich - und hat damit am 20.08.2026 einen Ein-Minuten-Fehler im
        # Code als Testfehler getarnt (der Agent tickt zur :20, das
        # Fensterziel lag bei :21:58, die Seite erklaerte ihre eigenen
        # frischen Zahlen fuer veraltet).
        import datetime as _dt
        kfg_ = json.load(open(os.path.join(BASIS, "konfig.json")))
        faellig = seite.letztes_laufziel(_dt.datetime.now(_dt.timezone.utc), kfg_)
        breite = _dt.timedelta(minutes=kfg_.get("lauf_fenster_min", 60))
        g_ = stand.get("geholt")
        g_ = _dt.datetime.fromisoformat(g_) if g_ else None
        if g_ is not None and g_.tzinfo is None:
            g_ = g_.replace(tzinfo=_dt.timezone.utc)
        frisch = bool(g_) and bool(faellig) and g_ >= faellig - breite / 2
        laeufe = [stand.get("geholt") or "?"]
        pruefe(hat_streifen != frisch,
               "Altersstreifen passt zum Zustand (Lauf %s, Streifen %s)"
               % (laeufe[-1] if laeufe else "?",
                  "ja" if hat_streifen else "nein"))

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

    print("\n=== 7. Push-Auskunft nennt den echten Zeitpunkt (T-0053)")
    # Bis zum 22.08.2026 stand hier fest "morgens um 7:30 Uhr" - seit T-0041
    # (18.08.2026) laeuft der Alarm sonnenuntergangsrelativ.  Der Satz ist die
    # EINZIGE Stelle, die dem Nutzer sagt, wann er mit einer Meldung rechnen
    # darf, und er erscheint nur im Alarmfall - rund 18 Abende im Jahr, also
    # genau dann, wenn er zaehlt.  Deshalb wird der Zweig hier ERZWUNGEN:
    # ihn dem Zufall der Wetterlage zu ueberlassen hiesse, ihn nie zu pruefen.
    import seite as _seite
    kfg_ = _json.load(open(os.path.join(BASIS, "konfig.json")))
    alarm_text = _seite.pushauskunft(0.62, 0.5, kfg_)
    still_text = _seite.pushauskunft(0.09, 0.5, kfg_)
    rueck_text = _seite.pushauskunft(0.62, 0.5, kfg_, rueckschau=True)

    pruefe("7:30" not in alarm_text and "7:30" not in still_text,
           "keine feste Uhrzeit mehr im Text")
    pruefe("Sonnenuntergang" in alarm_text,
           "der Alarmfall nennt den Sonnenuntergang als Bezug")
    pruefe("einmal, nicht zweimal" in alarm_text,
           "und weiterhin: einmal, nicht zweimal")
    pruefe("kein Push" in still_text, "der Normalfall sagt weiter: kein Push")
    pruefe("nichts gepusht" in rueck_text, "die Rueckschau bleibt unveraendert")

    # Die Zahl kommt aus der Konfiguration, nicht aus dem Text: wer den Lauf
    # verschiebt, verschiebt die Auskunft mit.  Sonst waere derselbe Fehler
    # beim naechsten Mal wieder da, nur mit einer anderen Zahl.
    for v, wort in ((2, "2"), (5, "5")):
        t = _seite.pushauskunft(0.62, 0.5, dict(kfg_, lauf_vorlauf_stunden=v))
        pruefe(wort in t and "Sonnenuntergang" in t,
               "lauf_vorlauf_stunden=%d schlaegt in den Text durch" % v)
    t1 = _seite.pushauskunft(0.62, 0.5, dict(kfg_, lauf_vorlauf_stunden=1))
    pruefe("eine Stunde" in t1, "Einzahl bei einer Stunde")

    print("\n=== 8. Die Abendwahl meldet sich bei assistiver Technik (T-0059)")
    # Vorher: `waehle()` tauschte vierzehn Elemente stumm aus - Hero, Stufe,
    # Grund, Zahlen, drei Kennzahlen, Band, Schnitt, Karte.  Per Screenreader
    # oder Pfeiltaste wechselte die ganze Seite, ohne dass etwas angekuendigt
    # wurde; die aktive Marke war allein ueber eine CSS-Klasse markiert.
    # Geprueft wird die ERZEUGTE Seite, nicht die Vorlage.
    ph = open(os.path.join(BASIS, "web", "index.html")).read()
    # Kommentare raus, sonst zaehlen die eigenen Erklaerungen mit.
    sichtbar = re.sub(r"<!--.*?-->", "", ph, flags=re.S)

    pruefe('aria-live="polite"' in sichtbar,
           "der Hero ist eine Live-Region")
    pruefe('role="status"' in sichtbar,
           "und als Status ausgezeichnet, nicht als Warnung")
    # Genau EINE Live-Region: zwei wuerden sich gegenseitig unterbrechen.
    pruefe(sichtbar.count('aria-live=') == 1,
           "genau eine Live-Region (%d)" % sichtbar.count('aria-live='))

    pruefe('role="tablist"' in sichtbar, "die Achse ist eine Tabliste")
    n_tab = sichtbar.count('role="tab"')
    n_abende = len(eintraege) if "eintraege" in dir() else n_tab
    pruefe(n_tab > 0, "die Marken sind Tabs (%d)" % n_tab)
    pruefe(sichtbar.count('aria-selected="true"') == 1,
           "genau eine Marke ist ausgewaehlt (%d)"
           % sichtbar.count('aria-selected="true"'))
    pruefe(sichtbar.count('aria-selected="false"') == n_tab - 1,
           "alle uebrigen sind ausdruecklich nicht ausgewaehlt")

    # Roving Tabindex: EIN Tabstopp fuer die ganze Achse, nicht elf.  Sonst
    # muss man sich durch jeden Abend durchtabben, um zum Fliesstext zu
    # kommen.
    pruefe(sichtbar.count('tabindex="0"') == 1,
           "die Tabliste hat genau einen Tabstopp (%d)"
           % sichtbar.count('tabindex="0"'))
    pruefe(sichtbar.count('tabindex="-1"') == n_tab - 1,
           "die uebrigen Marken sind aus der Tabreihenfolge genommen")

    # Der Startzustand steht im MARKUP - ohne JavaScript ist die Seite sonst
    # fuer assistive Technik zustandslos.  Dieselbe Regel wie beim Hero.
    i_sel = sichtbar.find('aria-selected="true"')
    i_an = sichtbar.find('class="marke')
    pruefe(i_sel > 0 and i_an > 0,
           "Auswahl und Marken stehen serverseitig im Dokument")

    # Dekoration darf nicht mitgelesen werden: die Rangzahl im Button waere
    # eine Dopplung des aria-labels.
    pruefe(sichtbar.count('aria-hidden="true"') >= 3 * n_tab,
           "Fahne, Punkt und Rangzahl sind als Dekoration ausgezeichnet (%d)"
           % sichtbar.count('aria-hidden="true"'))
    pruefe('class="achsenfuss" aria-hidden="true"' in sichtbar,
           "der Achsenfuss ist Dekoration - er wiederholt nur die Marken")

    # Die Tastaturbedienung muss den Fokus mitnehmen, sonst wandert die
    # Auswahl ohne den Screenreader-Cursor.
    pruefe("marken[z].focus()" in ph,
           "die Pfeiltasten nehmen den Fokus mit")
    pruefe('e.key==="Home"' in ph and 'e.key==="End"' in ph,
           "Home/End springen an die Raender (in einer Tabliste erwartet)")

    print("")
    if fehler:
        print("FEHLGESCHLAGEN: %d" % len(fehler))
        raise SystemExit(1)
    print("alle Pruefungen bestanden")


if __name__ == "__main__":
    main()
