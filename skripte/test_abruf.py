"""Der Alarmlauf holt Wind nur am Ort - und rechnet trotzdem richtig (T-0042).

Am 18.08.2026 gemessen: ein vollstaendiger Lauf kostete rund 5.500
Kontingenteinheiten und riss damit das Stundenlimit von 5.000 bei der
vorletzten Anfrage.  Ursache war kein Fehler in der Rechnung, sondern im
Abruf: die sechs Windvariablen wurden fuer alle 68 Faecherzellen geholt,
gelesen aber ausschliesslich am Heimatpunkt (der Advektionsversatz ist ein
Ensemble-Mittelwind je Schicht, kein Feld).  Und Open-Meteo zaehlt
Ensemble-Member wie zusaetzliche Variablen - 9 x 51 wiegt dreimal so viel
wie 3 x 51.

Dieser Test fuehrt den echten Ablauf mit erfundenen Daten aus, statt den
Quelltext zu lesen.  Er prueft genau zwei Dinge:

  * WIRD gespart - Wind nur an einer einzigen Zelle;
  * OHNE Schaden - der Wind kommt am Ort an und der Advektionsversatz ist
    nicht still null.  Genau das waere der teure Fehler: ein Lauf, der
    billiger ist und dabei die Advektion abschaltet, saehe erfolgreich aus.

Lauf:  python3 skripte/test_abruf.py
"""
import datetime as dt
import json
import os
import sys

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import alarm  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


MEMBER = [""] + ["%02d" % n for n in range(1, 51)]      # 51 wie ECMWF ENS
ABRUFE = []                                             # Protokoll der Aufrufe


def falscher_abruf(zellen, variablen, modell, tage, block=25):
    """Erfundene, aber formgleiche Antwort - und ein Protokolleintrag."""
    ABRUFE.append({"zellen": set(zellen), "variablen": list(variablen)})
    start = dt.datetime.now(dt.timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0)
    zeiten = [(start + dt.timedelta(hours=3 * k)).strftime("%Y-%m-%dT%H:%M")
              for k in range(8 * tage)]
    aus = {}
    for z in zellen:
        h = {"time": zeiten}
        for v in variablen:
            for m in MEMBER:
                if v.startswith("wind_speed"):
                    w = [40.0] * len(zeiten)          # kraeftig, damit es versetzt
                elif v.startswith("wind_direction"):
                    w = [270.0] * len(zeiten)         # aus Westen
                else:
                    w = [50.0] * len(zeiten)          # halbe Bedeckung
                h[alarm.feldname(v, m)] = w
        aus[z] = h
    return aus


def main():
    kfg = json.load(open(os.path.join(BASIS, "konfig.json")))
    ort = kfg["orte"][0]

    alarm.abfrage = falscher_abruf
    sicher, sys.argv = sys.argv, ["alarm.py", "--trocken"]
    try:
        alarm.main()
    finally:
        sys.argv = sicher

    print("\n=== 1. Wind wird nur an einer Zelle geholt")
    wind = [a for a in ABRUFE if any(v.startswith("wind_") for v in a["variablen"])]
    wolke = [a for a in ABRUFE if all(v.startswith("cloud_") for v in a["variablen"])]
    pruefe(len(wind) == 1, "genau ein Windabruf (%d)" % len(wind))
    pruefe(bool(wind) and len(wind[0]["zellen"]) == 1,
           "und der holt genau eine Zelle (%d)"
           % (len(wind[0]["zellen"]) if wind else -1))
    heim = alarm.zelle(ort["breite"], ort["laenge"])
    pruefe(bool(wind) and heim in wind[0]["zellen"],
           "und zwar den Heimatpunkt (%r)" % (heim,))
    pruefe(bool(wind) and not any(v.startswith("cloud_")
                                  for v in wind[0]["variablen"]),
           "keine Wolken im Windabruf")
    pruefe(all(not any(v.startswith("wind_") for v in a["variablen"])
               for a in wolke),
           "kein Wind in den Wolkenabrufen (%d Stueck)" % len(wolke))

    print("\n=== 2. Die Ersparnis, in Kontingenteinheiten")
    import math

    def gewicht(a):
        je = max(1, math.ceil(len(a["variablen"]) * len(MEMBER) / 10))
        return len(a["zellen"]) * je
    jetzt = sum(gewicht(a) for a in ABRUFE)
    # Wie es vor dem 18.08.2026 war: neun Variablen fuer ALLE Faecherzellen.
    faecher = max(len(a["zellen"]) for a in wolke)
    vorher = jetzt - gewicht(wolke[0]) + faecher * math.ceil(9 * len(MEMBER) / 10)
    pruefe(jetzt < 5000, "unter dem Stundenlimit: %d Einheiten" % jetzt)
    print("        vorher rund %d, jetzt rund %d" % (vorher, jetzt))

    print("\n=== 3. Der Wind kommt an: Advektion ist nicht still null")
    # Pass 2 gibt es nur, wenn der Versatz Zellen verschiebt.  Kaeme der
    # Wind nicht an, waere der Versatz (0,0) und es gaebe keinen zweiten
    # Wolkenabruf - der Lauf waere billig und falsch.
    pruefe(len(wolke) >= 2,
           "es gibt einen zweiten Wolkenabruf (Advektion greift): %d"
           % len(wolke))
    if len(wolke) >= 2:
        pruefe(not (wolke[-1]["zellen"] & wolke[0]["zellen"]),
               "Pass 2 holt nur Zellen, die Pass 1 nicht hatte")

    print("")
    if fehler:
        print("FEHLGESCHLAGEN: %d" % len(fehler))
        raise SystemExit(1)
    print("alle Pruefungen bestanden")


if __name__ == "__main__":
    main()
