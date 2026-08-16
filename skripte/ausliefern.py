"""Baut die Seiten und veroeffentlicht sie ueber GitHub Pages.

WARUM EIN EIGENER ZWEIG.  Die Prognoseseite wird nach jedem Alarmlauf neu
erzeugt und ist rund 280 kB gross - fast alles davon eingebettete
Vertikalschnitte.  Taeglich nach `main` committet waeren das ueber 100 MB im
Jahr, fuer Dateien, deren aeltere Staende niemanden interessieren.

Deshalb ein WEGWERFZWEIG: `gh-pages` wird bei jedem Lauf als EINZELNER
Commit neu geschrieben und mit --force gepusht.  Die Historie waechst nicht,
weil es keine gibt.  Der Quellcode in `main` bleibt davon unberuehrt.

Nebeneffekt, der die URL verbessert: der Zweig traegt die Seiten in seiner
WURZEL, nicht unter `web/`.  Aus

    https://xindaan.github.io/streulicht/web/bewerten-berlin.html
wird
    https://xindaan.github.io/streulicht/bewerten-berlin.html

SICHERUNG.  Ein `push --force` ist die einzige zerstoererische Operation im
ganzen Projekt.  Sie ist hier an einen fest verdrahteten Zweignamen gebunden
und prueft vorher, dass er nicht der Hauptzweig ist - ein vertippter
Parameter darf `main` nicht treffen koennen.

Lauf:  python3 skripte/ausliefern.py [--trocken]
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZWEIG = "gh-pages"                 # fest verdrahtet, siehe Sicherung oben
VERBOTEN = {"main", "master", "HEAD"}


def lauf(*args, **kw):
    kw.setdefault("cwd", BASIS)
    kw.setdefault("check", True)
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    return subprocess.run(list(args), **kw)


def baue(trocken):
    """Beide Seiten erzeugen.  Die Prognose darf fehlen, die Bewertung nicht."""
    py = sys.executable
    r = subprocess.run([py, os.path.join(BASIS, "skripte", "seite.py")],
                       cwd=BASIS, capture_output=True, text=True)
    if r.returncode == 2:
        print("   Prognoseseite: noch keine Prognose vorhanden, wird "
              "ausgelassen")
        prognose = False
    elif r.returncode != 0:
        raise SystemExit("seite.py fehlgeschlagen:\n" + r.stderr[-800:])
    else:
        print("   Prognoseseite: " + r.stdout.strip().splitlines()[-1])
        prognose = True
    r = lauf(py, os.path.join(BASIS, "skripte", "bewertungsseite.py"))
    print("   Bewertungsseiten:\n" + "\n".join(
        "      " + z for z in r.stdout.strip().splitlines()))
    r = lauf(py, os.path.join(BASIS, "skripte", "bisher.py"))
    print("   " + r.stdout.strip().splitlines()[-1])
    return prognose


def veroeffentliche(trocken):
    # AUSDRUECKLICHE Liste, kein "alles ausser ...".  Der erste Anlauf nahm
    # jede .html im Ordner - und haette damit `diagnose.html` (Andres
    # Albumabende neben meinen Bewertungen) und `rueckschau.html` (9.5 MB)
    # ins Netz gestellt.  Beide sind lokale Diagnosen und gitignoriert; dass
    # sie nicht im Repo stehen, hat sie hier NICHT geschuetzt, weil hier aus
    # dem Arbeitsverzeichnis kopiert wird.
    #
    # Regel: was oeffentlich wird, wird benannt.  Wer eine Seite ergaenzt,
    # traegt sie hier ein und denkt dabei einmal darueber nach.
    web = os.path.join(BASIS, "web")
    seiten = [n for n in sorted(os.listdir(web))
              if n in ("index.html", "bisher.html")
              or (n.startswith("bewerten-") and n.endswith(".html"))]
    # ACHTUNG beim Ergaenzen: `rueckschau.html` ist die LOKALE Diagnose ueber
    # vier Jahre (9,5 MB, Andres Albumabende).  Die ausgelieferte Bilanzseite
    # heisst `bisher.html`.  Wer die beiden verwechselt, veroeffentlicht
    # Privates - deshalb heissen sie verschieden (siehe skripte/bisher.py).
    if not seiten:
        raise SystemExit("nichts zu veroeffentlichen")
    gesamt = sum(os.path.getsize(os.path.join(BASIS, "web", n))
                 for n in seiten)
    print("   %d Seiten, %.1f kB" % (len(seiten), gesamt / 1000.0))
    for n in seiten:
        print("      %s" % n)
    if trocken:
        print("   [trocken] kein Push")
        return

    if ZWEIG in VERBOTEN:
        raise SystemExit("Zweigname %r ist gesperrt" % ZWEIG)
    tmp = tempfile.mkdtemp(prefix="streulicht-pages-")
    try:
        lauf("git", "init", "-q", "-b", ZWEIG, tmp, cwd=tmp)
        for n in seiten:
            shutil.copy2(os.path.join(BASIS, "web", n), os.path.join(tmp, n))
        # Jekyll aus dem Weg raeumen: sonst schluckt es Dateien mit Unterstrich
        # und baut ungefragt um.
        open(os.path.join(tmp, ".nojekyll"), "w").close()
        fern = lauf("git", "remote", "get-url", "origin").stdout.strip()
        lauf("git", "add", "-A", cwd=tmp)
        lauf("git", "-c", "user.name=streulicht",
             "-c", "user.email=noreply@greatbelow.de",
             "commit", "-q", "-m", "Seiten", cwd=tmp)
        lauf("git", "push", "--force", "-q", fern,
             "%s:%s" % (ZWEIG, ZWEIG), cwd=tmp)
        print("   nach %s gepusht (Wegwerfzweig, ein Commit)" % ZWEIG)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trocken", action="store_true")
    a = ap.parse_args()
    print("Bauen ...")
    baue(a.trocken)
    print("Veroeffentlichen ...")
    veroeffentliche(a.trocken)


if __name__ == "__main__":
    main()
