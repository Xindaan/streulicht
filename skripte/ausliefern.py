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
import hashlib
import shutil
import subprocess
import sys
import tempfile
import time

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZWEIG = "gh-pages"                 # fest verdrahtet, siehe Sicherung oben
VERBOTEN = {"main", "master", "HEAD"}


def lauf(*args, **kw):
    """Wie subprocess.run, aber ein Fehlschlag NENNT den Grund.

    Vorher stand hier `check=True` und `capture_output=True` - die
    Ausnahme meldete damit nur "returned non-zero exit status 128" und warf
    genau die Zeile weg, die erklaert, warum.  Am Morgen des 17.08.2026 war
    das der einzige Hinweis auf einen fehlgeschlagenen Push, und die Ursache
    liess sich nur ueber die Logs der drei anderen Agenten rekonstruieren.
    Ein Werkzeug, das im Fehlerfall schweigt, kostet mehr als es spart.
    """
    kw.setdefault("cwd", BASIS)
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    kw["check"] = False
    r = subprocess.run(list(args), **kw)
    if r.returncode != 0:
        raise SystemExit("FEHLGESCHLAGEN (%d): %s\n%s"
                         % (r.returncode, " ".join(args),
                            (r.stderr or r.stdout or "").strip()[-1200:]))
    return r


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


def veroeffentliche(trocken, immer=False):
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
    # Nur pushen, wenn sich wirklich etwas geaendert hat.  Seit der Agent
    # stuendlich laeuft (der Alarm ist sonnenuntergangsrelativ, also ist
    # sein Zeitpunkt nicht mehr fest), waeren das sonst 24 Force-Pushs am
    # Tag mit identischem Inhalt.  Verglichen wird der GEBAUTE Stand, nicht
    # das Alter von zustand.json: nach einer Codeaenderung aendert sich die
    # Seite auch ohne neue Zahlen.
    h = hashlib.sha256()
    for n in seiten:
        with open(os.path.join(web, n), "rb") as f:
            h.update(f.read())
    fingerabdruck = h.hexdigest()
    stempel = os.path.join(BASIS, "daten", ".ausgeliefert")
    vorher = ""
    if os.path.exists(stempel):
        with open(stempel) as f:
            vorher = f.read().strip()
    if fingerabdruck == vorher and not immer:
        print("   unveraendert seit dem letzten Push - nichts zu tun")
        return
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
        # Wiederholen, aber nur ein paar Mal: der haeufigste Fehlschlag ist
        # kein Zugriffsproblem, sondern ein Rechner, der noch kein Netz hat.
        # Am 17.08.2026 war der Mac von 07:30 bis nach 08:15 ohne
        # Namensaufloesung - Alarm, Archiv, Bewertungsabruf und dieser Push
        # sind alle vier daran gescheitert, jeder genau einmal.
        for versuch in range(1, 4):
            r = subprocess.run(["git", "push", "--force", "-q", fern,
                                "%s:%s" % (ZWEIG, ZWEIG)],
                               cwd=tmp, capture_output=True, text=True)
            if r.returncode == 0:
                break
            grund = (r.stderr or "").strip()
            print("   Push-Versuch %d fehlgeschlagen: %s"
                  % (versuch, grund.splitlines()[-1] if grund else "?"))
            if versuch == 3:
                raise SystemExit("Push endgueltig fehlgeschlagen:\n" + grund)
            time.sleep(120)
        with open(stempel, "w") as f:
            f.write(fingerabdruck + "\n")
        print("   nach %s gepusht (Wegwerfzweig, ein Commit)" % ZWEIG)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trocken", action="store_true")
    ap.add_argument("--immer", action="store_true",
                    help="auch pushen, wenn sich nichts geaendert hat")
    a = ap.parse_args()
    print("Bauen ...")
    baue(a.trocken)
    print("Veroeffentlichen ...")
    veroeffentliche(a.trocken, a.immer)


if __name__ == "__main__":
    main()
