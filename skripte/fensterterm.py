"""T-0027: der Fensterterm gegen die Satellitenwahrheit.

DIE FRAGE.  Befund 34 hat fuer zwei der fuenf Problemabende gezeigt, dass das
Modell die Schirmwolke hatte und der Score sie trotzdem weggerechnet hat - der
Fensterterm B war praktisch null.  Offen war, WARUM:

  (a) Datenfehler auf dem Weg: das Modell setzt Wolken auf den Lichtweg nach
      Westen, die dort nicht waren.  Dann ist der Term in Ordnung und die
      Vorhersage schlecht.
  (b) Termfehler: die Wolken waren da, und das Licht kam trotzdem durch.  Dann
      rechnet der Term Abende tot, die es nicht sind - egal wie gut das Modell.

Die Wolkenmaske von MSG entscheidet das je Abend, denn sie sieht den ganzen
Faecher bis 420 km.  Gerechnet wird der Fensterterm DREIMAL mit derselben
Formel (nachgebildet und gegen `sonnen.score.score` bitgenau geprueft):

  B_mod   Modellfelder - das B der Klimatologie.
  B_hyb   HYBRID: Hoehen und Schichten vom Modell, aber je Faecherpunkt
          gedeckelt durch die Saeulenbedeckung der Maske.  Was der Satellit
          nicht sieht, darf nicht blockieren.  Immer >= B_mod.
  B_sat   nur die Maske, jede Wolke zaehlt als Blockade - Untergrenze.

Fuer jeden Albumabend mit totem Modellfenster (B_mod < 0.1) gilt dann:

  B_hyb gross   ->  PHANTOM: die blockierende Modellwolke war nicht da (a)
  B_hyb klein   ->  BESTAETIGT: die Wolke war da, der Term rechnet den Abend
                    trotzdem tot (b)

WAS DIE MASKE NICHT KANN.  Sie kennt nur "Wolke in der Saeule ja/nein",
keine Hoehe.  Der Schirm ueber Berlin ist fuer sie dieselbe Wolke wie eine
tiefe Decke - deshalb ist B_sat fuer sich allein fast immer null, sobald ein
Schirm da ist, und taugt nur als Untergrenze.  Der Hybrid umgeht das, indem
er die Hoehenzuordnung dem Modell laesst.  Fall (b) heisst damit nicht "der
Term ist falsch", sondern "der Term ODER die Hoehenzuordnung des Modells";
die Trennung braucht Wolkenoberkantentemperatur (T-0028).

VERGLEICHBARKEIT.  Das Modell liefert je Faecherpunkt den Mittelwert einer
0.5-Grad-Zelle.  Die Maske hat 3 km; ein einzelner Pixel am Faecherpunkt
waere gegen die Zelle unfair.  Deshalb wird die Maske ueber genau die
Modellzelle gemittelt (7 x 7 Stuetzstellen, unbestimmte Pixel ausgeschlossen).

REFERENZ.  Albumabende sind Positive.  Um zu wissen, ob "Modell dicht,
Satellit offen" eine Eigenart guter Abende ist oder ein allgemeiner Hang des
Modells, laeuft dieselbe Rechnung fuer je einen Referenzabend: gleicher
Kalendertag, anderes Jahr, nicht im Album (Saison bleibt gleich, denn die
Daemmerung entscheidet mit, wie viel die Maske entscheiden kann).

KOSTEN.  0 EUR, alles offline bzw. gebuehrenfrei (Meteosat ab 1 h Latenz).

Pruefbefehl:  python3 skripte/fensterterm.py            (Albumabende + Referenz)
              python3 skripte/fensterterm.py --nur-cache (ohne Nachladen)
"""
import argparse
import json
import math
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sonnen.geometrie import (sonnenuntergang, strahlhoehe_km,  # noqa: E402
                              tangentendistanz_km)
from sonnen.grib2 import wert_bei  # noqa: E402
from sonnen.score import (DISTANZEN_KM, FAECHER_AZIMUTE, SCHIRME,  # noqa: E402
                          SICHT_KM, K_SEGMENT, _gewicht, _schichten_im_segment,
                          faecherpunkte, score)
import satellit  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITTER = 0.5
SCHICHTEN = ("low", "mid", "high")
ZELL_STUETZEN = 7          # 7 x 7 Maskenproben je Modellzelle
MIN_ENTSCHIEDEN = 0.5      # darunter gilt die Zelle als unbeobachtet
FENSTER_TOT = 0.10         # B unter dieser Marke: das Fenster hat den Abend gekillt
FENSTER_OFFEN = 0.50       # B ueber dieser Marke: das Fenster war offen
ZIEL = os.path.join(BASIS, "daten", "fensterterm_satellit.json")


# --------------------------------------------------------------- Modellfelder

def zelle(lat, lon):
    return (round(lat / GITTER), round(lon / GITTER))


def zellmitte(z):
    return (z[0] * GITTER, z[1] * GITTER)


_jahrescache = {}


def modellfeld(tag):
    """{Zelle: {schicht: Wert 0..100}} zur Sonnenuntergangsstunde des Tages.

    Zwei Quellen, beide bereits auf der Platte: der Blockcache der
    Klimatologie (`daten/roh`, ein Jahr je Datei) und der Tagescache des
    Nachtrags (`daten/roh_era5_nachtrag`, ein Tag je Datei).  Beides sind
    IFS-Analysen ueber `archive-api` (Befund 32.1).
    """
    p = os.path.join(BASIS, "daten", "roh_era5_nachtrag", "%s.json" % tag)
    if os.path.exists(p):
        with open(p) as f:
            return {tuple(int(x) for x in k.split("/")): v
                    for k, v in json.load(f).items()}
    jahr = tag[:4]
    if jahr not in _jahrescache:
        feld = {}
        d = os.path.join(BASIS, "daten", "roh")
        for name in sorted(os.listdir(d)):
            if not name.startswith("g%g_%s_" % (GITTER, jahr)):
                continue
            with open(os.path.join(d, name)) as f:
                for k, v in json.load(f).items():
                    feld[tuple(int(x) for x in k.split("/"))] = v
        _jahrescache[jahr] = feld
    feld = _jahrescache[jahr]
    aus = {}
    for z, schichten in feld.items():
        w = {s: schichten[s].get(tag) for s in SCHICHTEN}
        if all(v is None for v in w.values()):
            continue
        aus[z] = w
    return aus


def hole_modell(tag, breite, laenge):
    """(hole(d, dv, schicht), karte {(d,dv): Zelle}) oder (None, None)."""
    feld = modellfeld(tag)
    if not feld:
        return None, None
    _, azimut = sonnenuntergang(date.fromisoformat(tag), breite, laenge)
    karte = {(d, dv): zelle(la, lo)
             for d, dv, la, lo in faecherpunkte(breite, laenge, azimut)}

    def hole(d, dv, schicht):
        z = karte.get((d, dv))
        if z is None or z not in feld:
            return None
        v = feld[z].get(schicht)
        return None if v is None else v / 100.0
    return hole, karte


# ------------------------------------------------------------- Satellitenfeld

def zellanteil(feld, gp, z):
    """(Wolkenanteil, entschiedener Anteil) der Maske ueber der Modellzelle z.

    Unbestimmte Pixel (Klasse 3) fallen aus dem Nenner - dieselbe Regel wie
    in satellit.faecher_anteil.  Unter MIN_ENTSCHIEDEN gilt die Zelle als
    unbeobachtet (None), damit fehlende Beobachtung nicht als freier Himmel
    zaehlt.
    """
    la0, lo0 = zellmitte(z)
    n = ZELL_STUETZEN
    schritt = GITTER / n
    wolke = entschieden = gesamt = 0
    for i in range(n):
        for j in range(n):
            la = la0 - GITTER / 2 + (i + 0.5) * schritt
            lo = lo0 - GITTER / 2 + (j + 0.5) * schritt
            v = wert_bei(feld, gp, la, lo)
            gesamt += 1
            if v is None or int(v) == satellit.UNBESTIMMT:
                continue
            entschieden += 1
            wolke += 1 if int(v) == satellit.WOLKE else 0
    if gesamt == 0 or entschieden / gesamt < MIN_ENTSCHIEDEN:
        return None, (entschieden / gesamt if gesamt else 0.0)
    return wolke / entschieden, entschieden / gesamt


def hole_satellit(tag, breite, laenge, karte, nur_cache=False):
    """(hole(d, dv, schicht), Meta) - hole ignoriert die Schicht (Saeule)."""
    d = date.fromisoformat(tag)
    std, _ = sonnenuntergang(d, breite, laenge)
    ziel = (datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
            + timedelta(hours=std))
    if nur_cache:
        pid, abstand = _produkt_im_cache(ziel)
    else:
        pid, abstand = satellit.naechstes_produkt(ziel)
    if pid is None:
        return None, {"produkt": None}
    feld, gp = satellit.maske(pid)
    werte, deckung = {}, {}
    for (dd, dv), z in karte.items():
        if z in werte:
            continue
        werte[z], deckung[z] = zellanteil(feld, gp, z)
    zellen = sorted(werte)
    beobachtet = sum(1 for z in zellen if werte[z] is not None)

    def hole(dd, dv, schicht):
        z = karte.get((dd, dv))
        return None if z is None else werte.get(z)
    meta = {"produkt": pid, "abstand_min": abstand,
            "zellen_beobachtet": beobachtet, "zellen": len(zellen),
            "deckung_mittel": (sum(deckung.values()) / len(zellen)
                               if zellen else 0.0)}
    return hole, meta


def _produkt_im_cache(ziel):
    """Naechstes gecachtes Produkt (ohne API), fuer --nur-cache."""
    best, bestd = None, None
    if not os.path.isdir(satellit.CACHE):
        return None, None
    for name in os.listdir(satellit.CACHE):
        if not name.endswith(".zip") or "MSGCLMK" not in name:
            continue
        stempel = name.split("-")[5][:14]
        try:
            t = datetime.strptime(stempel, "%Y%m%d%H%M%S").replace(
                tzinfo=timezone.utc)
        except ValueError:
            continue
        dt = abs((t - ziel).total_seconds()) / 60.0
        if dt <= 40 and (bestd is None or dt < bestd):
            best, bestd = name[:-4], dt
    return best, bestd


# --------------------------------------------------------- Fensterterm-Replik

def fenster(hole, name, hoehe, unter, deckel=None):
    """Sicht- und Wegterm wie in sonnen.score.score, fuer EINEN Schirm.

    Nachbildung von score.py (Term B (a) und (b)), damit dieselbe Formel mit
    einem schichtlosen Feld laufen kann.  Fuer das Modell muss sie den
    Produktions-Score exakt reproduzieren - das prueft `pruefe_replik`.
    `unter` sind die Schichten unter dem Schirm; fuer die Saeulenmaske ist es
    eine einzige Pseudoschicht, und `hole` ignoriert den Schichtnamen.

    `deckel(d, dv)` ist optional eine Obergrenze je Faecherpunkt: die
    Blockade an einem Punkt kann nicht groesser sein als die dort beobachtete
    Saeulenbedeckung.  Mit dem Modell als `hole` und der Maske als `deckel`
    entsteht der HYBRID: Hoehen vom Modell, Anwesenheit vom Satelliten.
    Liefert der Deckel None (Zelle unbeobachtet), bleibt der Modellwert.

    Rueckgabe None, wenn die Sicht oder der Weg unbeobachtet ist (dieselben
    Ausschlussregeln wie im Score).
    """
    def _kappe(wert, d, dv):
        if deckel is None:
            return wert
        o = deckel(d, dv)
        return wert if o is None else min(wert, o)

    d_tan = tangentendistanz_km(hoehe)
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
            sicht_c += _kappe(1.0 - rest, d, dv)
            sicht_n += 1
    if sicht_n == 0:
        return None
    sicht = 1.0 - sicht_c / sicht_n

    stuetzen = [d for d in DISTANZEN_KM if SICHT_KM <= d < d_tan]
    jenseits = [d for d in DISTANZEN_KM if d >= d_tan]
    if jenseits:
        stuetzen.append(jenseits[0])
    weg, segmente = 1.0, []
    weg_moeglich = weg_erfasst = 0
    for i in range(len(stuetzen) - 1):
        d_nah, d_fern = stuetzen[i], stuetzen[i + 1]
        schichten = _schichten_im_segment(
            strahlhoehe_km(d_fern, d_tan), strahlhoehe_km(d_nah, d_tan))
        schichten = [s for s in schichten if s != name] or None
        if schichten is None:
            continue
        weg_moeglich += 1
        zc, zg = 0.0, 0.0
        for dv in FAECHER_AZIMUTE:
            cs = [hole(d_fern, dv, s) for s in schichten]
            cs = [c for c in cs if c is not None]
            if not cs:
                continue
            w = _gewicht(dv)
            zc += w * _kappe(max(cs), d_fern, dv)
            zg += w
        if zg == 0.0:
            continue
        c_seg = zc / zg
        weg *= (1.0 - c_seg) ** K_SEGMENT
        weg_erfasst += 1
        segmente.append((d_nah, d_fern, schichten, c_seg))
    if weg_moeglich > 0 and weg_erfasst == 0:
        return None
    return {"sicht": sicht, "weg": weg, "B": sicht * weg,
            "segmente": segmente,
            "weg_deckung": (weg_erfasst / weg_moeglich if weg_moeglich else 1.0)}


def pruefe_replik(hole, detail):
    """Die Nachbildung muss den Produktions-Score bit-genau treffen."""
    name = detail["schirm"]
    unter = ["low"] if name == "mid" else ["low", "mid"]
    r = fenster(hole, name, detail["hoehe_km"], unter)
    if r is None:
        raise AssertionError("Replik liefert None, Score nicht")
    for k in ("sicht", "weg", "B"):
        if abs(r[k] - detail[k]) > 1e-12:
            raise AssertionError("Replik weicht ab: %s %r != %r"
                                 % (k, r[k], detail[k]))
    return r


def ringe(hole, saeule):
    """Bedeckung je Entfernungsring, azimutgewichtet wie der Wegterm.

    saeule=True: hole ist schichtlos.  Sonst wird die Gesamtbedeckung der
    Saeule aus den drei Schichten mit Zufallsueberlapp gebildet -
    1 - (1-l)(1-m)(1-h) - damit sie mit der Maske vergleichbar ist.
    """
    aus = {}
    for d in DISTANZEN_KM:
        zc, zg = 0.0, 0.0
        for dv in FAECHER_AZIMUTE:
            if d == 0.0 and dv != 0.0:
                continue
            if saeule:
                c = hole(d, dv, None)
            else:
                cs = [hole(d, dv, s) for s in SCHICHTEN]
                if any(c is None for c in cs):
                    c = None
                else:
                    c = 1.0
                    for v in cs:
                        c *= (1.0 - v)
                    c = 1.0 - c
            if c is None:
                continue
            w = _gewicht(dv)
            zc += w * c
            zg += w
        aus[d] = (zc / zg) if zg > 0 else None
    return aus


# ------------------------------------------------------------------- Auswahl

def albumabende(klima, noten):
    return sorted(t for t in noten if t in klima)


def referenzabende(abende, klima, noten, saat=27):
    """Je Albumabend ein Nicht-Albumabend am selben Kalendertag, anderes Jahr."""
    rnd = random.Random(saat)
    jahre = sorted({int(t[:4]) for t in klima if t < "2026"})
    aus = {}
    for t in abende:
        j0, rest = int(t[:4]), t[4:]
        kandidaten = [("%d%s" % (j, rest)) for j in jahre if j != j0]
        kandidaten = [k for k in kandidaten if k in klima and k not in noten]
        if kandidaten:
            aus[t] = rnd.choice(kandidaten)
    return aus


# ----------------------------------------------------------------- Auswertung

def rechne_abend(tag, breite, laenge, nur_cache):
    hole_m, karte = hole_modell(tag, breite, laenge)
    if hole_m is None:
        return {"fehler": "kein Modellfeld"}
    s, det = score(hole_m)
    if det is None:
        return {"fehler": "Score ohne Detail"}
    replik = pruefe_replik(hole_m, det)
    name, hoehe = det["schirm"], det["hoehe_km"]

    hole_s, meta = hole_satellit(tag, breite, laenge, karte, nur_cache)
    aus = {"s": s, "schirm": name, "A": det["A"], "B": det["B"],
           "sicht": det["sicht"], "weg": det["weg"],
           "segmente_modell": [(a, b, c) for a, b, _, c in replik["segmente"]],
           "ringe_modell": ringe(hole_m, saeule=False),
           "satellit": meta}
    if hole_s is None:
        return aus
    fs = fenster(hole_s, name, hoehe, ["saeule"])
    # HYBRID: Modellhoehen, aber je Punkt durch die beobachtete Saeule
    # gedeckelt.  Nur Wolken, die der Satellit sieht, duerfen blockieren.
    unter = ["low"] if name == "mid" else ["low", "mid"]
    fh = fenster(hole_m, name, hoehe, unter,
                 deckel=lambda d, dv: hole_s(d, dv, None))
    aus.update({
        "B_sat": None if fs is None else fs["B"],
        "sicht_sat": None if fs is None else fs["sicht"],
        "weg_sat": None if fs is None else fs["weg"],
        "segmente_sat": ([] if fs is None else
                         [(a, b, c) for a, b, _, c in fs["segmente"]]),
        "B_hyb": None if fh is None else fh["B"],
        "sicht_hyb": None if fh is None else fh["sicht"],
        "weg_hyb": None if fh is None else fh["weg"],
        "segmente_hyb": ([] if fh is None else
                         [(a, b, c) for a, b, _, c in fh["segmente"]]),
        "ringe_sat": ringe(hole_s, saeule=True),
        # Rohwerte je Faecherpunkt, damit spaetere Auswertungen ohne
        # Neurechnung auskommen: Saeule laut Maske und die drei Modellschichten.
        "punkte": {"%g/%g" % (d, dv): {
            "sat": hole_s(d, dv, None),
            "modell": [hole_m(d, dv, s) for s in SCHICHTEN]}
            for d in DISTANZEN_KM for dv in FAECHER_AZIMUTE
            if not (d == 0.0 and dv != 0.0)},
    })
    return aus


def diagnose(e):
    """Was hat das Fenster an diesem Abend gemacht - und stimmt das?"""
    b, h = e.get("B"), e.get("B_hyb")
    if b is None:
        return "-"
    if b >= FENSTER_OFFEN:
        return "offen"
    if h is None:
        return "unbeobachtet"
    if b < FENSTER_TOT:
        if h >= FENSTER_OFFEN:
            return "PHANTOM"          # Modellwolke, die der Satellit nicht sieht
        if h < FENSTER_TOT:
            return "BESTAETIGT"       # Wolke da, Term rechnet trotzdem tot
        return "teils Phantom"
    return "halb"


def _rangkorrelation(x, y):
    """Spearman ohne Bibliothek (Mittelraenge bei Bindungen)."""
    def raenge(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2.0 + 1.0
            i = j + 1
        return r
    if len(x) < 3:
        return None
    rx, ry = raenge(x), raenge(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    zx = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    nx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    ny = math.sqrt(sum((b - my) ** 2 for b in ry))
    return zx / (nx * ny) if nx > 0 and ny > 0 else None


def bericht(erg, noten, referenz):
    album = [t for t in sorted(erg) if t in noten]
    ref = [referenz[t] for t in album if referenz.get(t) in erg]

    print("\n%-11s %4s %5s  %5s %5s %5s | %5s %5s %5s | %5s  %4s  %s"
          % ("Abend", "Note", "Schirm", "A", "sicht", "weg", "B_mod",
             "B_hyb", "B_sat", "sat<=60", "Deck", "Diagnose"))
    for t in album:
        e = erg[t]
        if "fehler" in e:
            print("%-11s %4s  %s" % (t, noten[t], e["fehler"]))
            continue
        print("%-11s %4d %5s  %5.2f %5.2f %5.2f | %5.2f %5s %5s | %5s  %3.0f%%  %s"
              % (t, noten[t], e["schirm"], e["A"], e["sicht"], e["weg"],
                 e["B"], _z(e.get("B_hyb")), _z(e.get("B_sat")),
                 _z(1.0 - e["sicht_sat"]
                    if e.get("sicht_sat") is not None else None),
                 100 * e["satellit"].get("deckung_mittel", 0.0),
                 diagnose(e)))

    def zaehle(tage):
        k = {}
        for t in tage:
            kl = diagnose(erg.get(t, {}))
            k[kl] = k.get(kl, 0) + 1
        return k

    print("\nDiagnose je Abend  (tot < %.2f, offen >= %.2f)"
          % (FENSTER_TOT, FENSTER_OFFEN))
    print("  offen        Fenster war laut Modell offen, nichts zu klaeren")
    print("  PHANTOM      Modell rechnet tot, ohne Satellit-Deckel offen -> Daten")
    print("  BESTAETIGT   Modell rechnet tot, Satellit bestaetigt die Wolke -> Term/Hoehe")
    ka, kr = zaehle(album), zaehle(ref)
    for kl in sorted(set(ka) | set(kr)):
        print("  %-13s Album %3d   Referenz %3d" % (kl, ka.get(kl, 0),
                                                    kr.get(kl, 0)))

    # Wie viel oeffnet der Satellit-Deckel das Modellfenster - im Album
    # gegenueber der Referenz?  Gleich viel heisst: Phantomwolken sind ein
    # allgemeiner Hang des Modells, keine Eigenart guter Abende.
    def hebung(tage):
        ds = [erg[t]["B_hyb"] - erg[t]["B"] for t in tage
              if erg.get(t, {}).get("B_hyb") is not None]
        if not ds:
            return None
        ds.sort()
        return (len(ds), sum(ds) / len(ds), ds[len(ds) // 2],
                sum(1 for d in ds if d > 0.1) / len(ds))
    for name, tage in (("Album", album), ("Referenz", ref)):
        h = hebung(tage)
        if h:
            print("  %-9s n=%d  B_hyb - B_mod: Mittel %+.3f, Median %+.3f, "
                  "Anteil > 0.1: %.0f %%" % (name, h[0], h[1], h[2], 100 * h[3]))

    # Rangkorrelation mit Andres Noten
    paare = [(noten[t], erg[t]["B"], erg[t]["B_hyb"], erg[t]["B_sat"])
             for t in album if erg[t].get("B_hyb") is not None]
    if len(paare) >= 5:
        r = [_rangkorrelation([p[0] for p in paare], [p[i] for p in paare])
             for i in (1, 2, 3)]
        print("\nSpearman gegen Andres Note (n=%d):  B_modell %s   B_hybrid %s"
              "   B_sat %s" % (len(paare), _f(r[0]), _f(r[1]), _f(r[2])))

    # Wo sitzt der Toeter?  Fuer Abende mit engem Weg (weg_hyb < 0.5): das
    # Segment mit der groessten bestaetigten Bedeckung, nach Aussenrand.
    print("\nToeter-Segment (weg_hyb < 0.5): Aussenrand des Segments mit der "
          "groessten bestaetigten Bedeckung")
    for name, tage in (("Album", album), ("Referenz", ref)):
        k = {}
        for t in tage:
            e = erg.get(t, {})
            if e.get("weg_hyb") is None or e["weg_hyb"] >= 0.5:
                continue
            if not e.get("segmente_hyb"):
                continue
            a, b, c = max(e["segmente_hyb"], key=lambda s: s[2])
            k[b] = k.get(b, 0) + 1
        if k:
            print("  %-9s " % name + "  ".join(
                "%.0f km: %d" % (b, k[b]) for b in sorted(k)))

    # Uebereinstimmung je Ring: Modellsaeule gegen Maske
    print("\nRing   n    r(Modellsaeule, Maske)   Modell-Mittel  Masken-Mittel")
    for d in DISTANZEN_KM:
        xs, ys = [], []
        for t in album + ref:
            e = erg.get(t, {})
            rm, rs = e.get("ringe_modell"), e.get("ringe_sat")
            if not rm or not rs:
                continue
            a, b = rm.get(d), rs.get(d)
            if a is None or b is None:
                continue
            xs.append(a)
            ys.append(b)
        if len(xs) >= 5:
            r = _pearson(xs, ys)
            print("%4.0f  %3d   %s               %5.2f          %5.2f"
                  % (d, len(xs), _f(r), sum(xs) / len(xs), sum(ys) / len(ys)))


def _f(x):
    return "%+.3f" % x if x is not None else "   -  "


def _z(x):
    return "%5.2f" % x if x is not None else "    -"


def _pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sxy / (sx * sy) if sx > 0 and sy > 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tage", nargs="*", help="ISO-Daten; leer = Albumabende")
    ap.add_argument("--breite", type=float, default=52.52)
    ap.add_argument("--laenge", type=float, default=13.405)
    ap.add_argument("--nur-cache", action="store_true",
                    help="keine API-Zugriffe; nur gecachte Masken")
    ap.add_argument("--ohne-referenz", action="store_true")
    ap.add_argument("--neu", action="store_true",
                    help="Ergebnisdatei ignorieren und alles neu rechnen")
    a = ap.parse_args()

    with open(os.path.join(BASIS, "daten",
                           "score_berlin_g0.5_2015_2025.json")) as f:
        klima = json.load(f)
    with open(os.path.join(BASIS, "daten", "bewertung_andre.json")) as f:
        noten = json.load(f)

    tage = a.tage or albumabende(klima, noten)
    referenz = ({} if (a.tage or a.ohne_referenz)
                else referenzabende(tage, klima, noten))
    alle = list(tage) + sorted(set(referenz.values()))

    erg = {}
    if os.path.exists(ZIEL) and not a.neu:
        with open(ZIEL) as f:
            erg = json.load(f)
        # JSON macht aus den Ringschluesseln Strings
        for e in erg.values():
            for k in ("ringe_modell", "ringe_sat"):
                if k in e:
                    e[k] = {float(d): v for d, v in e[k].items()}

    for i, t in enumerate(alle):
        if t in erg and erg[t].get("B_hyb") is not None:
            continue
        print("[%3d/%3d] %s ..." % (i + 1, len(alle), t), end=" ", flush=True)
        try:
            e = rechne_abend(t, a.breite, a.laenge, a.nur_cache)
        except Exception as ex:  # ein Abend darf den Lauf nicht kippen
            e = {"fehler": "%s: %s" % (type(ex).__name__, ex)}
        erg[t] = e
        if "fehler" in e:
            print(e["fehler"])
        else:
            print("B_mod %.3f  B_sat %s" % (
                e["B"], "%.3f" % e["B_sat"] if e.get("B_sat") is not None
                else "-"))
        with open(ZIEL, "w") as f:
            json.dump(erg, f, indent=1)

    bericht(erg, noten, referenz)
    print("\ngeschrieben: %s" % os.path.relpath(ZIEL, BASIS))


if __name__ == "__main__":
    main()
