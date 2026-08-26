"""Regressionstest fuer die Fehlerklasse "Schluessel vorhanden = Daten vorhanden".

Diese Klasse hat im Projekt inzwischen viermal zugeschlagen:
  Juli 2026   Modellauswahl - "Variable im Antwortdict" als Beleg gelesen,
              haette vier Ensembles faelschlich qualifiziert.
  14.08.2026  ICON-Deckungspruefung - meldete 100 %, weil das Wertedict der
              Zelle nicht leer war; die Druckflaechen darin waren alle None.
  14.08.2026  alarm.member_liste - zaehlt Member an Schluesselnamen.  Ein
              Member ohne Daten lief mit Score 0.0 in den NENNER der
              Wahrscheinlichkeit und stimmte still gegen den Sonnenuntergang.
  (der vierte ist der hier getestete Pfad selbst)

Zwei Dinge werden geprueft, und das zweite ist das eigentlich wichtige:

1. verdichte() nimmt datenlose Member aus dem Nenner.
2. Der Diskriminator taugt ueberhaupt: score() liefert detail=None GENAU
   dann, wenn keine einzige Faecherzelle Daten hatte - und ein echtes Detail,
   sobald auch nur eine belegt ist.  Ohne diese Eigenschaft waere der Fix
   falsch, egal wie gut die Arithmetik darueber aussieht.

Lauf:  python3 skripte/test_member.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alarm import verdichte                                      # noqa: E402
from sonnen.score import DISTANZEN_KM, FAECHER_AZIMUTE, score    # noqa: E402

fehler = []


def pruefe(bedingung, text):
    print("   %s  %s" % ("ok  " if bedingung else "FEHL", text))
    if not bedingung:
        fehler.append(text)


print("=== 1. Datenlose Member gehoeren nicht in den Nenner")
D = {"schirm": "high", "A": 0.5, "sicht": 1.0, "weg": 1.0}

# Zehn Member: drei reissen die Schwelle, zwei haben gar keine Daten.
werte = ([(0.9, D)] * 3 + [(0.1, D)] * 5 + [(0.0, None)] * 2)
v = verdichte(werte, 0.6)
pruefe(v["n_member"] == 8 and v["n_member_gesamt"] == 10,
       "8 von 10 Membern gueltig erkannt")
pruefe(abs(v["p"] - 3 / 8) < 1e-12,
       "p = 3/8 = %.4f  (alte Rechnung waere 3/10 = 0.3000 gewesen)" % v["p"])
pruefe(v["p"] > 3 / 10, "die alte Rechnung unterschaetzte p - Richtung stimmt")

v2 = verdichte([(0.9, D)] * 3 + [(0.1, D)] * 7, 0.6)
pruefe(abs(v2["p"] - 0.3) < 1e-12,
       "ohne datenlose Member unveraendert p = 0.3000 (keine Regression)")

pruefe(verdichte([(0.0, None)] * 5, 0.6) is None,
       "gar keine Daten -> None statt p = 0.0")

# Der Median darf ebenfalls nicht von Phantom-Nullen nach unten gezogen werden.
vm = verdichte([(0.8, D)] * 3 + [(0.0, None)] * 6, 0.6)
pruefe(abs(vm["median"] - 0.8) < 1e-12,
       "Median aus gueltigen Membern: %.2f (mit Phantomnullen waere 0.00)"
       % vm["median"])

print()
print("=== 2. Taugt der Diskriminator? score() -> detail is None")


def feld(belegt):
    def hole(d, dv, schicht):
        return 0.5 if (d, dv) in belegt else None
    return hole


alle = {(d, dv) for d in DISTANZEN_KM for dv in FAECHER_AZIMUTE}
s, det = score(feld(set()))
pruefe(det is None and s == 0.0,
       "keine einzige Zelle belegt -> (0.0, None)")

s, det = score(feld(alle))
pruefe(det is not None, "voller Faecher -> Detail vorhanden")

# DIESER FALL STAND HIER UMGEKEHRT UND WAR FALSCH (gefunden 15.08.2026 im
# Fable-Gutachten).  Der Test forderte "Detail vorhanden" und zementierte
# damit ein Loch: bei belegtem Standort, aber leerem Beleuchtungsweg blieb
# weg auf seinem Startwert 1.0 und sicht fiel auf 1.0 - fehlende Fensterdaten
# wirkten als FREIES Fenster.  Gemessen: bei ueberall 90 % Bewoelkung gibt der
# volle Faecher S = 0.0000, ein Faecher mit nur der Standortzelle S = 0.0900.
# Fehlende Daten schlugen also bekannte Wolke.  Exaktes Spiegelbild des
# Memberfehlers, den dieselbe Datei prueft - und mein eigener Test hat es
# als "ok" abgehakt.
s, det = score(feld({(0.0, 0.0)}))
pruefe(det is None,
       "nur der Standort belegt -> None (Beleuchtungsweg unbeobachtet)")

# Dieser Fall lief beim ersten Lauf auf FEHL, und die Erwartung war falsch,
# nicht der Code: Term A ist nur im Nahbereich (d <= 120 km) definiert.  Ist
# dort nichts belegt, gibt es keinen Schirmwert - der Score ist dann nicht
# null, sondern UNDEFINIERT.  Genau solche Member gehoeren aus dem Nenner.
s, det = score(feld({(420.0, 24.0)}))
pruefe(det is None,
       "nur eine ferne Zelle belegt -> None (Term A ohne Nahbereich undefiniert)")

s, det = score(feld({(0.0, 0.0), (420.0, 24.0)}))
pruefe(det is not None,
       "Nahbereich belegt, Rest fern -> Detail vorhanden")

# Und der kritische Gegenfall: eine echte Null darf NICHT wie fehlende
# Daten aussehen, sonst nimmt der Fix richtige Nullen aus dem Nenner.
def nullfeld(d, dv, schicht):
    return 0.0


s, det = score(nullfeld)
pruefe(det is not None and s == 0.0,
       "ueberall exakt 0 %% Bewoelkung -> S = 0, aber Detail VORHANDEN")

print()
print("=== 3. Fehlende Fensterdaten duerfen NIE guenstiger sein als Wolke")
# Die Zahl, die den Fehler sichtbar gemacht hat: identische Bewoelkung,
# einmal voll abgetastet, einmal nur am Standort.  Frueher 0.0000 gegen
# 0.0900 - zugunsten des unbeobachteten Falls.
alle_zellen = {(d, dv) for d in DISTANZEN_KM for dv in FAECHER_AZIMUTE}
s_voll, d_voll = score(feld(alle_zellen))
s_duenn, d_duenn = score(feld({(0.0, 0.0)}))
pruefe(d_voll is not None,
       "voller Faecher, ueberall belegt -> bewertbar, S = %.4f" % s_voll)
pruefe(d_duenn is None,
       "nur Standort -> nicht bewertbar (frueher S = 0.0900 bei 90 %%)")

# Der eigentliche Beleg, mit derselben Bewoelkung in beiden Faellen:
# frueher schlug der unbeobachtete Faecher den vollstaendigen.
def dicht(d, dv, schicht):
    return 0.9


s_dicht, d_dicht = score(dicht)
# NICHT auf == 0.0 pruefen: die Anzeige mit %.4f zeigte 0.0000, der Wert ist
# 9e-06.  Eine gerundete Ausgabe ist nicht der Wert - derselbe Fehler wie bei
# einem Kontrastverhaeltnis ohne seine Bezugsflaeche (Befund 30).
pruefe(d_dicht is not None and s_dicht < 1e-4,
       "90 %% ueberall, voll abgetastet -> S = %.3g, praktisch zu" % s_dicht)
pruefe(s_dicht < 0.09,
       "und das schlaegt die alte Luecke: dieselbe Wolke gab dort S = 0.0900")

teil = {(0.0, 0.0)} | {(d, dv) for d in (60.0, 120.0)
                       for dv in FAECHER_AZIMUTE}
s_teil, d_teil = score(feld(teil))
pruefe(d_teil is not None and "weg_deckung" in d_teil,
       "Teildeckung bleibt bewertbar und meldet weg_deckung")
pruefe(d_teil is not None and d_teil["weg_deckung"] < 1.0,
       "und die Deckung ist ehrlich unter 1.0 (%.2f)"
       % (d_teil["weg_deckung"] if d_teil else -1))
pruefe(d_voll is not None and d_voll["weg_deckung"] == 1.0,
       "voller Faecher meldet Deckung 1.00")

print()
print("=== 4. Beide Score-Varianten behandeln Luecken gleich (T-0054)")
# Der Wachhund aus Abschnitt 3 sass bis zum 22.08.2026 NUR in sonnen/score.py.
# sonnen/score_niveaus.py - die Variante, auf die der Betrieb wechseln soll -
# hatte den behobenen Fehler noch eingebaut: `sicht = 1.0 - (... if sicht_w
# else 0.0)` macht aus fehlenden Daten freie Sicht, und `weg` blieb ohne
# Segmentzaehlung auf 1.0.  Ein Member mit Daten nur im Nahbereich bekam
# damit B = 1.0 und zaehlte mit vollem Score.
#
# Warum das KEIN Zukunftsproblem war: skripte/ablation.py rechnet mit
# score_niveaus - das ist das Skript, das T-0006 gerechnet hat, also die
# Entscheidung ueber den Wechsel selbst.  Bei einer TEILluecke lieferte
# score_niveaus ein Detail (der Abend blieb also in der Stichprobe), score
# verwarf (der Abend flog raus).  Verglichen wurde unter asymmetrischer
# Lueckenbehandlung - dieselbe Fehlerklasse, die die Zahlen laut T-0006
# schon einmal verbogen hat.
from sonnen.score_niveaus import score as scoreN   # noqa: E402


def feldN(belegt, niveaus=None, wert=0.9):
    """Wie feld(), aber fuer die niveauaufgeloeste Signatur (direkt=True)."""
    def hole(d, dv, p):
        if (d, dv) not in belegt:
            return None
        return wert if (niveaus is None or p in niveaus) else None
    return hole


# (a) Der Fall, der den Fehler sichtbar macht: Daten NUR auf dem
#     Schirmniveau im Nahbereich - nichts darunter, nichts in der Ferne.
nur_nah = {(0.0, 0.0)} | {(d, dv) for d in (30.0,) for dv in FAECHER_AZIMUTE}
sN, dN = scoreN(feldN(nur_nah, niveaus={600}), direkt=True,
                mit_dickenstrafe=False)
pruefe(dN is None,
       "nur Schirmniveau im Nahbereich -> nicht bewertbar "
       "(frueher S = 0.900 mit sicht=weg=1.0)")

# (a2) Der Fall, der GENAU den sicht-Waechter isoliert.  Ohne ihn faellt (a)
#      schon durch den weg-Waechter - die Negativprobe hat das aufgedeckt:
#      den sicht-Waechter allein zu entfernen liess den Test gruen.  Ein
#      Waechter ohne eigenen Fall ist ungeprueft, auch wenn er dasteht.
#      Konstruktion: Schirm 600 hPa im Nahbereich belegt (Term A traegt), die
#      Ferne vollstaendig belegt (der Weg traegt) - aber NICHTS unter dem
#      Schirm im Sichtbereich.  Frueher wurde daraus sicht = 1.0, also freie
#      Sicht aus fehlenden Daten.
def nur_schirm_und_ferne(d, dv, p):
    if d <= 60.0:
        return 0.2 if p == 600 else None
    return 0.2


sS, dS = scoreN(nur_schirm_und_ferne, direkt=True, mit_dickenstrafe=False,
                schirm_niveaus=(600,))
pruefe(dS is None,
       "Sichtbereich unter dem Schirm unbeobachtet -> verworfen "
       "(frueher sicht = 1.0 aus fehlenden Daten)")

# Gegenprobe zum Waechter selbst: liegen dort Daten, bleibt der Abend
# bewertbar - sonst haette ich einen zu scharfen Riegel eingebaut.
def auch_darunter(d, dv, p):
    return 0.2


sA, dA = scoreN(auch_darunter, direkt=True, mit_dickenstrafe=False,
                schirm_niveaus=(600,))
pruefe(dA is not None and dA["sicht"] < 1.0,
       "mit Daten unter dem Schirm bewertbar, sicht = %.3f"
       % (dA["sicht"] if dA else -1))

# (b) Gar nichts belegt: beide Varianten muessen (0.0, None) liefern.
s3_leer, d3_leer = score(feld(set()))
sN_leer, dN_leer = scoreN(feldN(set()), direkt=True)
pruefe(d3_leer is None and dN_leer is None,
       "leerer Faecher -> beide Varianten verwerfen")

# (c) Nur der Standort belegt - der Fall aus Abschnitt 3, jetzt gegen BEIDE.
#     Genau hier liefen sie vorher auseinander: score verwarf, score_niveaus
#     gab einen Wert zurueck.  Das ist die Asymmetrie in der Ablation.
s3_p, d3_p = score(feld({(0.0, 0.0)}))
sN_p, dN_p = scoreN(feldN({(0.0, 0.0)}), direkt=True, mit_dickenstrafe=False)
pruefe(d3_p is None, "nur Standort -> 3-Schicht verwirft")
pruefe(dN_p is None, "nur Standort -> niveauaufgeloest verwirft AUCH")
pruefe((d3_p is None) == (dN_p is None),
       "beide Varianten sind sich einig (das ist der Punkt)")

# (d) Der Wachhund darf nicht zu scharf sein: voll belegt bleibt bewertbar,
#     sonst haette ich den Fehler durch einen schlimmeren ersetzt.
alle_zellen2 = {(d, dv) for d in DISTANZEN_KM for dv in FAECHER_AZIMUTE}
sN_voll, dN_voll = scoreN(feldN(alle_zellen2), direkt=True,
                          mit_dickenstrafe=False)
pruefe(dN_voll is not None,
       "voller Faecher bleibt bewertbar, S = %.4f" % sN_voll)
pruefe(dN_voll is not None and dN_voll.get("weg_deckung") == 1.0,
       "und meldet weg_deckung 1.00 wie die 3-Schicht-Variante")

# (e) Teildeckung: bewertbar, aber ehrlich ausgewiesen - gleiche Regel wie
#     in score.py.  Ohne die Zahl misst man ein Artefakt und merkt es nicht.
teil2 = {(0.0, 0.0)} | {(d, dv) for d in (60.0, 120.0)
                        for dv in FAECHER_AZIMUTE}
sN_teil, dN_teil = scoreN(feldN(teil2), direkt=True, mit_dickenstrafe=False)
pruefe(dN_teil is not None and "weg_deckung" in dN_teil,
       "Teildeckung bleibt bewertbar und meldet weg_deckung")
pruefe(dN_teil is not None and dN_teil["weg_deckung"] < 1.0,
       "und die Deckung ist ehrlich unter 1.0 (%.2f)"
       % (dN_teil["weg_deckung"] if dN_teil else -1))

print()
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    sys.exit(1)
print("alle Pruefungen bestanden")
