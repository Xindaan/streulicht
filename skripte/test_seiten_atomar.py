"""Die drei Seitenbauer schreiben ihre HTML-Datei atomar (09.10.2026).

WARUM.  `ausliefern.py` veroeffentlicht seit T-0081 auch dann, wenn ein
Seitenbauer scheitert.  Das ist nur sicher, solange ein gescheiterter Bauer
die alte Seite UNVERAENDERT liegen laesst.  Schrieb er mit
`open(ziel, "w")` und starb mitten im Text, stuende die halbe Seite im
Ordner - und ginge live.

Der Test laesst `main()` von seite.py, bisher.py und bewertungsseite.py
gegen ein Temp-Verzeichnis laufen (`BASIS` umgebogen, `daten/` nur gelesen,
`web/` mit einer Marke als "alter Seite") und laesst jedes Schreiben in
dieses `web/` nach der Haelfte des Textes abbrechen.  Gemessen wird, WAS
danach in der Datei steht - nicht, ob ein Import da ist.

Lauf:  python3 skripte/test_seiten_atomar.py
"""
import builtins
import os
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
BASIS = os.path.dirname(HIER)
sys.path.insert(0, HIER)
sys.path.insert(0, BASIS)

import bewertungsseite                                           # noqa: E402
import bisher                                                    # noqa: E402
import seite                                                     # noqa: E402

_fehler = []
ALT = "<html>ALTE SEITE</html>"


def ok(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        _fehler.append(text)


class Absturz(BaseException):
    """Wie ein SIGKILL mitten im Schreiben: faengt kein `except Exception`."""


class HalbSchreiber:
    """Datei, die beim ersten write() nur die Haelfte schreibt und stirbt."""

    def __init__(self, f):
        self._f = f

    def write(self, text):
        self._f.write(text[:len(text) // 2])
        self._f.flush()
        raise Absturz()

    def __getattr__(self, name):
        return getattr(self._f, name)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self._f.close()
        return False


def lauf(modul, argv, zielname, abbrechen):
    """main() des Bauers; Rueckgabe: (Absturz?, Inhalt der Zieldatei)."""
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "web"))
        os.symlink(os.path.join(BASIS, "daten"), os.path.join(d, "daten"))
        ziel = os.path.join(d, "web", zielname)
        with open(ziel, "w") as f:
            f.write(ALT)
        echt_open, alt_basis = builtins.open, modul.BASIS
        web = os.path.join(d, "web")

        def mein_open(datei, modus="r", *a, **k):
            f = echt_open(datei, modus, *a, **k)
            if abbrechen and "w" in str(modus) \
                    and os.path.abspath(str(datei)).startswith(web + os.sep):
                return HalbSchreiber(f)
            return f

        modul.BASIS = d
        sicher, sys.argv = sys.argv, [modul.__name__ + ".py"] + argv
        gestorben = False
        builtins.open = mein_open
        try:
            modul.main()
        except Absturz:
            gestorben = True
        finally:
            builtins.open = echt_open
            modul.BASIS = alt_basis
            sys.argv = sicher
        with open(ziel, encoding="utf-8") as f:
            return gestorben, f.read()


KFG = ["--konfig", os.path.join(BASIS, "konfig.json")]
FAELLE = [("seite.py", seite, KFG, "index.html"),
          ("bisher.py", bisher, KFG, "bisher.html"),
          ("bewertungsseite.py", bewertungsseite, KFG, "bewerten-berlin.html")]

if not os.path.isdir(os.path.join(BASIS, "daten")):
    print("daten/ fehlt - ohne Betriebsdaten laeuft kein Seitenbauer")
    raise SystemExit(2)

print("Seiten werden atomar geschrieben\n")
for name, modul, argv, zielname in FAELLE:
    print("%s" % name)
    _, neu = lauf(modul, argv, zielname, abbrechen=False)
    ok(neu != ALT and len(neu) > 1000,
       "Kontrolle: ohne Absturz ersetzt der Lauf die alte Seite (%d Zeichen)"
       % len(neu))
    gestorben, rest = lauf(modul, argv, zielname, abbrechen=True)
    ok(gestorben, "der simulierte Absturz mitten im Schreiben traf den Bauer")
    ok(rest == ALT, "danach steht die ALTE Seite unveraendert da")

print()
if _fehler:
    print("FEHLGESCHLAGEN: %d" % len(_fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
