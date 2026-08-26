"""T-0057: es gibt genau EINE Faechergeometrie, nicht zwei.

`alarm.fan_setzen` hat frueher `sonnen.score.FAECHER_AZIMUTE` und
`.DISTANZEN_KM` zur Laufzeit ueberschrieben.  Zwoelf Module importieren diese
Konstanten aber by value - sie sahen die Aenderung nie.  In einem Prozess,
der beides benutzt, rechneten Analyse und Bild danach auf verschiedenen
Faechern, ohne dass irgendetwas auffiel.

Der Sparfaecher ist deshalb abgeschafft (Begruendung im Docstring von
`fan_setzen`).  Dieser Test haelt fest, dass die Mutation weg ist UND dass
eine alte Konfiguration nicht still ignoriert wird, sondern abbricht.

Lauf:  python3 skripte/test_faechergeometrie.py
"""
import os
import sys

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import alarm  # noqa: E402
import schnitt  # noqa: E402
import sonnen.score as sc  # noqa: E402
import sonnen.score_niveaus as sn  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


SPAR = {"faecher": {"azimute": [0.0], "distanzen_km": [0.0, 60.0]}}

print("T-0057  Eine Geometrie, nicht zwei\n")

print("1. Vor jedem Aufruf sind sich alle Module einig")
vorher = {
    "sonnen.score": (sc.FAECHER_AZIMUTE, sc.DISTANZEN_KM),
    "sonnen.score_niveaus": (sn.FAECHER_AZIMUTE, sn.DISTANZEN_KM),
    "skripte.schnitt": (None, schnitt.DISTANZEN_KM),
}
pruefe(vorher["sonnen.score"][0] == vorher["sonnen.score_niveaus"][0],
       "score und score_niveaus haben dieselben Azimute")
pruefe(vorher["sonnen.score"][1] == vorher["skripte.schnitt"][1],
       "score und schnitt haben dieselben Distanzen")

print("\n2. Eine leere Konfiguration aendert nichts")
pruefe(alarm.fan_setzen({}) is False, "fan_setzen({}) meldet False")
pruefe((sc.FAECHER_AZIMUTE, sc.DISTANZEN_KM) == vorher["sonnen.score"],
       "und hat nichts veraendert")

print("\n3. Eine ALTE Sparfaecher-Konfiguration bricht ab, statt still zu wirken")
# Der gefaehrliche Fall waere ein stilles Weiterlaufen: eine konfig.json aus
# der Zeit vor dem 23.08.2026 wuerde dann kommentarlos ignoriert - und der
# Betreiber glaubte weiter, er spare Kontingent.
try:
    alarm.fan_setzen(SPAR)
    pruefe(False, "fan_setzen mit `faecher` haette abbrechen muessen")
except SystemExit as e:
    pruefe("T-0057" in str(e), "SystemExit nennt den Task")
    pruefe("s*" in str(e) or "0.7065" in str(e),
           "und erklaert, warum: s* gehoert zum Faecher der Klimatologie")
except Exception as e:                                    # noqa: BLE001
    pruefe(False, "falscher Fehlertyp: %s" % type(e).__name__)

print("\n4. Und danach ist die Geometrie UNVERAENDERT - in allen Modulen")
# Das ist der eigentliche Punkt: frueher standen hier zwei Wahrheiten.
pruefe((sc.FAECHER_AZIMUTE, sc.DISTANZEN_KM) == vorher["sonnen.score"],
       "sonnen.score unveraendert")
pruefe((sn.FAECHER_AZIMUTE, sn.DISTANZEN_KM)
       == vorher["sonnen.score_niveaus"],
       "sonnen.score_niveaus unveraendert")
pruefe(schnitt.DISTANZEN_KM == vorher["skripte.schnitt"][1],
       "skripte.schnitt unveraendert")
pruefe(sc.FAECHER_AZIMUTE == sn.FAECHER_AZIMUTE
       and sc.DISTANZEN_KM == sn.DISTANZEN_KM == schnitt.DISTANZEN_KM,
       "alle drei sind sich weiterhin einig")

print("\n5. Niemand schreibt mehr in die Score-Konstanten")
# Kein Textvergleich am Quelltext: die Attribute werden vor und nach einem
# echten fan_setzen-Aufruf per Identitaet verglichen.
a_vorher, d_vorher = sc.FAECHER_AZIMUTE, sc.DISTANZEN_KM
try:
    alarm.fan_setzen(SPAR)
except SystemExit:
    pass
pruefe(sc.FAECHER_AZIMUTE is a_vorher and sc.DISTANZEN_KM is d_vorher,
       "dieselben Tupel-Objekte wie vorher (keine Neuzuweisung)")

print()
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
