"""Erzeugt je konfiguriertem Ort eine Bewertungsseite aus der Vorlage.

WARUM ES DAS BRAUCHT (15.08.2026).  `web/bewerten.html` war immer schon eine
Vorlage mit Platzhaltern, aber es gab kein Skript, das sie fuellt -
`bewerten-berlin.html` war von Hand ausgefuellt.  Das faellt spaetestens bei
Entscheidung D4 auf die Fuesse: der Ort ist ein Parameter, und fuer
Freund:innen an anderen Orten muesste jemand die Datei kopieren und zwei
Zeichenketten tauschen, ohne sie zu vergessen.

Ein Ort, der in `konfig.json` steht, hat ab jetzt automatisch eine Seite.

Lauf:  python3 skripte/bewertungsseite.py
"""
import argparse
import json
import os
import sys

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VORLAGE = os.path.join(BASIS, "web", "bewerten.html")


def erzeuge(ort, vorlage):
    fehlend = [s for s in ("__NTFY_BEWERTUNG__", "__ORT__") if s not in vorlage]
    if fehlend:
        raise SystemExit("Vorlage ohne Platzhalter %s - schon gefuellt?"
                         % ", ".join(fehlend))
    return (vorlage.replace("__NTFY_BEWERTUNG__", ort["ntfy_bewertung"])
                   .replace("__ORT__", ort["name"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--konfig", default=os.path.join(BASIS, "konfig.json"))
    a = ap.parse_args()

    with open(a.konfig) as f:
        kfg = json.load(f)
    with open(VORLAGE) as f:
        vorlage = f.read()

    for ort in kfg["orte"]:
        fehlt = [k for k in ("name", "ntfy_bewertung") if not ort.get(k)]
        if fehlt:
            print("   %s: uebersprungen, %s fehlt"
                  % (ort.get("name", "?"), ", ".join(fehlt)))
            continue
        ziel = os.path.join(BASIS, "web", "bewerten-%s.html" % ort["name"])
        seite = erzeuge(ort, vorlage)
        with open(ziel, "w") as f:
            f.write(seite)
        print("   %-10s -> %s (%.1f kB)"
              % (ort["name"], os.path.relpath(ziel, BASIS),
                 len(seite.encode()) / 1000))

    # Gegenprobe: keine erzeugte Seite darf noch einen Platzhalter tragen.
    rest = []
    for ort in kfg["orte"]:
        p = os.path.join(BASIS, "web", "bewerten-%s.html" % ort["name"])
        if os.path.exists(p):
            with open(p) as f:
                s = f.read()
            if "__NTFY" in s or "__ORT__" in s:
                rest.append(ort["name"])
    if rest:
        raise SystemExit("Platzhalter uebrig in: %s" % ", ".join(rest))
    print("Alle Seiten ohne Platzhalter.")


if __name__ == "__main__":
    main()
