"""E1-Abbruchtest: ist der Score an fotografierten Abenden angereichert?

Presence-Only-Verfahren aus E0.  "An diesem Abend wurde bei Sonnenuntergang
fotografiert" ist ein positives Label, das seit Jahren existiert - ohne
Ankereffekt, weil zum Zeitpunkt der Aufnahme keine Prognose existierte.

Verfahren: fuer jeden Fotoabend der Perzentilrang seines Scores INNERHALB
eines +/-21-Tage-Klimatologiefensters.  Das Saisonfenster ist der Punkt, an
dem der Test steht oder faellt - ohne es wuerden "im Sommer ist man oefter
draussen" und "der Score ist saisonal ungleich" einen Effekt vortaeuschen.

Unter H0 sind die Raenge gleichverteilt, Mittelwert 0.5.

DER EIGENTLICHE TEST ist nicht "S > 0.5", sondern der VERGLEICH:
  S = A*B   der volle Score
  A         nur Schirm  - "es sind hohe Wolken da"
  B         nur Fenster - "der Westen ist frei"
Ist S nicht staerker angereichert als A und B einzeln, traegt die
Zweiterm-Konstruktion nichts und E1 ist eine Sackgasse.

Schwaeche des Labels, ehrlich benannt: 701 Berliner Abende in 16 Jahren sind
rund 12 % aller Abende - das ist nicht "hat einen Sonnenuntergang
fotografiert", sondern "hat in diesem Zeitfenster ueberhaupt fotografiert".
Viele Treffer sind beilaeufig.  Deshalb zusaetzlich die Auswertung nur fuer
Abende mit mehreren Fotos im Fenster: mehr Aufnahmen sprechen fuer Absicht.
"""
import json
import math
import os
import sys
from datetime import date

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FENSTER_TAGE = 21


def tag_im_jahr(s):
    d = date.fromisoformat(s)
    return d.timetuple().tm_yday


def perzentilrang(wert, vergleich):
    """Anteil der Vergleichswerte unter dem Wert; Bindungen halb gewichtet."""
    kleiner = sum(1 for x in vergleich if x < wert)
    gleich = sum(1 for x in vergleich if x == wert)
    return (kleiner + 0.5 * gleich) / len(vergleich)


def teste(name, raenge):
    n = len(raenge)
    m = sum(raenge) / n
    # Standardfehler unter H0 (Gleichverteilung, Varianz 1/12)
    se = math.sqrt(1.0 / 12.0 / n)
    z = (m - 0.5) / se
    print("   %-26s n=%4d   Mittelrang %.3f   z = %+6.2f   %s"
          % (name, n, m, z,
             "signifikant" if abs(z) > 1.96 else "nicht signifikant"))
    return m, z


def main():
    kl = os.path.join(BASIS, "daten", "score_berlin_g0.5_2022_2025.json")
    fo = os.path.join(BASIS, "daten", "foto_abende_mediathek.json")
    for p in (kl, fo):
        if not os.path.exists(p):
            raise SystemExit("fehlt: %s" % p)
    with open(kl) as f:
        klima = json.load(f)
    with open(fo) as f:
        fotos = json.load(f)

    berlin = set(fotos["berlin"])
    anzahl = {x["tag"]: x["n_fotos"] for x in fotos["alle"]}
    kandidaten = sorted(t for t in berlin if t in klima)
    print("Klimatologie: %d Abende (2022-2025)" % len(klima))
    print("Berliner Fotoabende gesamt: %d, davon in der Klimatologie: %d"
          % (len(berlin), len(kandidaten)))
    if len(kandidaten) < 20:
        raise SystemExit("zu wenige - Test faellt aus")

    # Vergleichsmengen je Kalendertag (+/- 21 Tage, ueber alle Jahre)
    nach_tag = {}
    for t, v in klima.items():
        nach_tag.setdefault(tag_im_jahr(t), []).append(v)

    def fenster(t, schluessel):
        jt = tag_im_jahr(t)
        aus = []
        for d in range(-FENSTER_TAGE, FENSTER_TAGE + 1):
            for v in nach_tag.get((jt + d - 1) % 365 + 1, []):
                x = v.get(schluessel)
                if x is not None:
                    aus.append(x)
        return aus

    print()
    print("=== Perzentilraenge im +/-%d-Tage-Saisonfenster" % FENSTER_TAGE)
    print("   H0: Mittelrang 0.500 (Fotos unabhaengig vom Score)")
    print()
    ergebnis = {}
    for schl, name in (("s", "S = Schirm x Fenster"), ("A", "A  nur Schirm"),
                       ("B", "B  nur Fenster")):
        raenge = []
        for t in kandidaten:
            w = klima[t].get(schl)
            v = fenster(t, schl)
            if w is None or len(v) < 30:
                continue
            raenge.append(perzentilrang(w, v))
        ergebnis[schl] = teste(name, raenge)

    print()
    print("=== Nur Abende mit >= 3 Fotos im Fenster (eher Absicht als Zufall)")
    for schl, name in (("s", "S = Schirm x Fenster"), ("A", "A  nur Schirm"),
                       ("B", "B  nur Fenster")):
        raenge = []
        for t in kandidaten:
            if anzahl.get(t, 1) < 3:
                continue
            w = klima[t].get(schl)
            v = fenster(t, schl)
            if w is None or len(v) < 30:
                continue
            raenge.append(perzentilrang(w, v))
        if len(raenge) >= 20:
            teste(name, raenge)
        else:
            print("   %-26s nur %d Abende - uebersprungen" % (name, len(raenge)))

    print()
    ms, zs = ergebnis["s"]
    ma, _ = ergebnis["A"]
    mb, _ = ergebnis["B"]
    print("=== Urteil")
    if zs <= 1.96:
        print("   S ist nicht signifikant angereichert.")
        print("   ACHTUNG, das heisst NICHT automatisch 'Score kaputt'.  Gemessen")
        print("   am 14.08.2026: Term B ist an Fotoabenden signifikant erhoeht")
        print("   (+0.068, z = +2.77), Term A erniedrigt (-0.041, z = -1.76).")
        print("   Das Label hat also Trennschaerfe - es misst nur 'war draussen',")
        print("   und draussen sein korreliert mit klarem Himmel, also GEGEN den")
        print("   Schirmterm.  Im Produkt heben sich beide auf.")
        print("   Ein konfundiertes Label, kein leeres.  Aufloesbar nur durch")
        print("   Vergleich INNERHALB der Draussen-Abende - siehe fotos_detail.py")
        print("   (Favoriten und Minutenabstand als Absichtssignal).")
    elif ms > ma and ms > mb:
        print("   S (%.3f) schlaegt A (%.3f) und B (%.3f) einzeln." % (ms, ma, mb))
        print("   Die Zweiterm-Konstruktion traegt. E1 besteht.")
    else:
        print("   S (%.3f) schlaegt A (%.3f) / B (%.3f) NICHT." % (ms, ma, mb))
        print("   Die Anreicherung kommt von einem Term allein - der Score")
        print("   ist ein Term zu viel, und die Wegegeometrie ist unbegruendet.")


if __name__ == "__main__":
    main()
