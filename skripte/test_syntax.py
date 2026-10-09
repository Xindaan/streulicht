"""T-0078: kein Modul traegt eine ungueltige Escape-Sequenz.

`sonnen/score_niveaus.py` hatte im Modulkopf einen Backslash vor dem
Sternchen in einem normalen String-Literal.  Python 3.13 meldet das beim
Kompilieren als SyntaxWarning, und eine kuenftige Version macht daraus einen
Fehler - dann laeuft das Modul nicht mehr an.  Im Betrieb faellt die
Warnung nicht auf, weil sie nur beim ERSTEN Kompilieren erscheint und danach
der Bytecode-Cache greift.

Der Test kompiliert deshalb jede .py-Datei in `sonnen/` und `skripte/` frisch
aus dem Quelltext (kein Cache) mit Warnungen als Fehlern.

Lauf:  python3 skripte/test_syntax.py
"""
import glob
import os
import warnings

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


def kompiliere_streng(pfad, text=None):
    """None bei Erfolg, sonst die Meldung."""
    if text is None:
        with open(pfad, encoding="utf-8") as f:
            text = f.read()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        try:
            compile(text, pfad, "exec")
        except (SyntaxError, SyntaxWarning) as e:
            return "%s: %s" % (type(e).__name__, e)
    return None


print("T-0078  Keine ungueltigen Escape-Sequenzen\n")

print("1. Das Messverfahren schlaegt an einer ungueltigen Escape-Sequenz an")
pruefe(kompiliere_streng("<probe>", 'x = "s\\* = 0.7"\n') is not None,
       "'s\\*' im normalen String wird gemeldet")
pruefe(kompiliere_streng("<probe>", 'x = r"s\\* = 0.7"\n') is None,
       "dasselbe als raw-String ist sauber")

print("\n2. Jede Quelldatei ist sauber")
dateien = sorted(glob.glob(os.path.join(BASIS, "sonnen", "*.py"))
                 + glob.glob(os.path.join(BASIS, "skripte", "*.py")))
pruefe(len(dateien) > 20, "Dateien gefunden (n = %d)" % len(dateien))
for pflicht in ("sonnen/score_niveaus.py", "skripte/alarm.py"):
    pruefe(os.path.join(BASIS, pflicht) in dateien,
           "%s ist in der Auswahl" % pflicht)
for d in dateien:
    meldung = kompiliere_streng(d)
    pruefe(meldung is None, "%s%s" % (os.path.relpath(d, BASIS),
                                      "" if meldung is None else " - " + meldung))

print()
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
