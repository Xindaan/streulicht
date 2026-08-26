"""T-0061: `score_distanz` behandelt Luecken wie die anderen zwei Varianten.

Das Modul wird heute von keinem anderen importiert (nur in
`docs/befunde-e1.md` erwaehnt) - es ist ein E1-Experiment, kein Betriebspfad.
Es trug aber dieselbe Fehlerklasse wie score.py (T-0054) und icond2_test.py
(T-0060): `sicht` und `weg` starten bei 1.0 und bleiben dort, wenn nichts
beobachtet wurde - fehlende Daten wirken dann wie ein freies Fenster.

Und einen zweiten, eigenstaendigen Rechenfehler: `noetig` wurde berechnet und
nie benutzt.  Die Deckung rechnete stattdessen ohne den Deckel bei
DISTANZEN_KM[-1] und verlangte damit Stuetzstellen jenseits von 420 km, die
der Faecher gar nicht hat.

Lauf:  python3 skripte/test_score_distanz.py
"""
import os
import sys

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASIS)

from sonnen.geometrie import tangentendistanz_km  # noqa: E402
from sonnen.score import DISTANZEN_KM  # noqa: E402
from sonnen.score_distanz import score  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


print("T-0061  Luecken und die tote Deckungsformel\n")

print("1. Grundverhalten - sonst prueft der Rest nichts")
s_voll, d_voll = score(lambda d, dv, schicht: 0.5)
pruefe(d_voll is not None and 0.0 < s_voll < 1.0,
       "voll belegt -> auswertbar, S = %.4f" % s_voll)
s_leer, d_leer = score(lambda d, dv, schicht: None)
pruefe(s_leer == 0.0, "gar nichts belegt -> S = 0.0")
pruefe(not (d_leer or {}).get("beitraege"),
       "und kein einziger Beitrag")

print("\n2. Ein unbeobachteter Beleuchtungsweg zaehlt nicht als freier")
# Nur der Nahbereich belegt: der Schirm ist da, der Weg dahinter unbekannt.
# Frueher ging er mit weg = 1.0 in die Summe - fehlende Daten schlugen
# bekannte Wolke.


def nur_nah(d, dv, schicht):
    return 0.5 if d <= 60.0 else None


s_nah, d_nah = score(nur_nah)
beitraege = (d_nah or {}).get("beitraege") or []
mit_vollem_weg = [b for b in beitraege if b["weg"] == 1.0 and b["d_km"] > 0.0]
pruefe(not mit_vollem_weg,
       "kein Beitrag mit unbeobachtetem, voll durchlaessigem Weg (%d)"
       % len(mit_vollem_weg))

print("\n3. Volle Belegung heisst Deckung 1.00 - ueberall")
# Der eigentliche Fehler: `erfasst` zaehlt Stuetzstellen, der alte Nenner war
# eine LAENGE (Intervall / 60 km).  Bei d_s = 0 und h = 4.2 km liegen vier
# Stuetzstellen im Intervall, der Nenner ergab 4.45 - volle Belegung meldete
# 0.899 statt 1.00.  Geprueft wird das Ergebnis, nicht die Formel.
pruefe(abs((d_voll or {}).get("deckung", 0.0) - 1.0) < 1e-9,
       "Gesamtdeckung bei voller Belegung: %.4f"
       % (d_voll or {}).get("deckung", -1))
schlecht = [b for b in (d_voll or {}).get("beitraege", [])
            if abs(b["deckung"] - 1.0) > 1e-9]
pruefe(not schlecht,
       "kein einzelner Beitrag meldet weniger als 1.00 (%d)" % len(schlecht))

# Und der Deckel ist trotzdem wirksam: Beitraege, deren Tangente ueber den
# Faecherrand hinausreicht, duerfen nicht bestraft werden.
tiefe = [b for b in (d_voll or {}).get("beitraege", [])
         if b["d_km"] + tangentendistanz_km(b["hoehe_km"]) > DISTANZEN_KM[-1]]
pruefe(bool(tiefe),
       "es gibt Beitraege mit Tangente jenseits %d km (%d) - sonst prueft "
       "das nichts" % (DISTANZEN_KM[-1], len(tiefe)))
pruefe(all(abs(b["deckung"] - 1.0) < 1e-9 for b in tiefe),
       "auch die melden 1.00: jenseits des Faechers gibt es nichts zu decken")

print("\n4. Teilbelegung wird ehrlich ausgewiesen")
# Der Waechter darf nicht zu scharf sein: teilweise beobachtet bleibt
# bewertbar, meldet aber unter 1.00.  Sonst haette ich den Fehler durch
# einen schlimmeren ersetzt.
def loechrig(d, dv, schicht):
    return None if d in (180.0, 300.0) else 0.5


s_teil, d_teil = score(loechrig)
pruefe(d_teil is not None and s_teil > 0.0,
       "teilweise belegt bleibt bewertbar (S = %.4f)" % s_teil)
pruefe(0.0 < (d_teil or {}).get("deckung", 0.0) < 1.0,
       "und meldet eine Deckung zwischen 0 und 1 (%.3f)"
       % (d_teil or {}).get("deckung", -1))

print("\n5. `noetig` ist ersatzlos weg, nicht bloss ungenutzt")
quelle = open(os.path.join(BASIS, "sonnen", "score_distanz.py")).read()
code = "\n".join(z for z in quelle.split("\n")
                 if not z.strip().startswith("#"))
pruefe("noetig" not in code,
       "keine tote Variable mehr im Code (nur noch im Kommentar erklaert)")

print()
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
