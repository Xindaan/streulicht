#!/usr/bin/env python3
"""Streulicht Ende-zu-Ende pruefen - im Sandkasten, ohne Netz, ohne Push.

Was laeuft (siehe SKILL.md daneben):

  1. Sandkasten: der aktuelle Arbeitsbaum (getrackte + neue, nicht ignorierte
     Dateien, MIT ungespeicherten Aenderungen) wird in ein Temp-Verzeichnis
     kopiert; `daten/` kommt als eingefrorener Schnappschuss der Betriebsdaten
     dazu.  Der Arbeitsbaum und die Betriebsdaten werden nur GELESEN.
  2. Bau: `skripte/ausliefern.py --trocken` erzeugt aus dem Schnappschuss die
     drei Seitenarten (Prognose, Bewertung je Ort, Bilanz).  Kein Push.
  3. Ergebnis: jede erwartete Seite ist in DIESEM Lauf neu entstanden, und
     der Waechter findet in der Prognoseseite einen lesbaren Abrufzeitpunkt.
  4. Tests: jede `skripte/test_*.py` und `skripte/test_*.js` einzeln,
     nacheinander; gezaehlt werden die `ok`-Zeilen.

Exitcode 0 = gruen, 1 = rot, 2 = Voraussetzung fehlt (venv, Daten, node).

Nur Standardbibliothek.  Aufruf aus dem Arbeitsbaum, der geprueft wird:

    "$(git worktree list --porcelain | sed -n '1s/^worktree //p')/.venv/bin/python3" \
        .claude/skills/verify/verify.py [--frisch] [--nur MUSTER]
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

OK_ZEILE = re.compile(r"^\s*ok\b")
SCHNAPPSCHUSS_MAX_H = 20          # aelter: neu ziehen (zehn Abende Vorlauf
                                  # im Zustand, der Bau bleibt also sinnvoll)
FRIST_S = 300                     # je Testdatei
WAECHTER_GRENZE_H = 10 ** 6       # prueft nur: Zeitpunkt da und lesbar.  Das
                                  # ALTER haengt am Betrieb, nicht am Code.


def git(*args, cwd=None):
    r = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True,
                       text=True)
    if r.returncode != 0:
        raise SystemExit("git %s: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout


def voraussetzung(text):
    print("VERIFY NICHT MOEGLICH: " + text)
    sys.exit(2)


def schnappschuss(quelle, ziel, frisch):
    """Betriebsdaten einfrieren.  -> (Pfad, Alter in h, neu gezogen?)"""
    marke = os.path.join(ziel, ".gezogen")
    alter_h = None
    if os.path.exists(marke):
        alter_h = (time.time() - os.path.getmtime(marke)) / 3600.0
    if alter_h is not None and alter_h < SCHNAPPSCHUSS_MAX_H and not frisch:
        return ziel, alter_h, False
    shutil.rmtree(ziel, ignore_errors=True)
    kopiere_baum(quelle, ziel)
    with open(marke, "w") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S\n"))
    return ziel, 0.0, True


def kopiere_baum(quelle, ziel):
    """Verzeichnis kopieren; auf APFS als Klon (sofort, ohne Platz)."""
    if sys.platform == "darwin":
        r = subprocess.run(["cp", "-Rc", quelle, ziel], capture_output=True)
        if r.returncode == 0:
            return
        shutil.rmtree(ziel, ignore_errors=True)
    shutil.copytree(quelle, ziel, symlinks=True)


def kopiere_arbeitsbaum(wurzel, ziel):
    """Getrackte und neue, nicht ignorierte Dateien, so wie sie JETZT im
    Arbeitsbaum stehen (also mit ungespeicherten Aenderungen)."""
    namen = git("ls-files", "-z", "-c", "-o", "--exclude-standard",
                cwd=wurzel).split("\0")
    n = 0
    for name in sorted(set(x for x in namen if x)):
        von = os.path.join(wurzel, name)
        if not os.path.isfile(von):          # geloescht, aber noch im Index
            continue
        nach = os.path.join(ziel, name)
        os.makedirs(os.path.dirname(nach), exist_ok=True)
        shutil.copy2(von, nach)
        n += 1
    return n


def lauf(befehl, cwd, frist=FRIST_S):
    """-> (Exitcode oder None bei Fristablauf, Ausgabe, Sekunden)"""
    umgebung = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    t0 = time.time()
    try:
        r = subprocess.run(befehl, cwd=cwd, capture_output=True, text=True,
                           timeout=frist, env=umgebung, errors="replace")
        return r.returncode, r.stdout + r.stderr, time.time() - t0
    except subprocess.TimeoutExpired as ex:
        aus = (ex.stdout or b"")
        if isinstance(aus, bytes):
            aus = aus.decode("utf-8", "replace")
        return None, aus + "\n[Frist %d s abgelaufen]" % frist, time.time() - t0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--frisch", action="store_true",
                    help="Schnappschuss der Betriebsdaten neu ziehen")
    ap.add_argument("--nur", default="",
                    help="nur Testdateien, deren Name MUSTER enthaelt "
                         "(Bau und Ergebnis laufen immer)")
    a = ap.parse_args()

    wurzel = git("rev-parse", "--show-toplevel").strip()
    haupt = git("worktree", "list", "--porcelain",
                cwd=wurzel).split("\n")[0].replace("worktree ", "", 1)
    py = next((p for p in (os.path.join(w, ".venv", "bin", "python3")
                           for w in (wurzel, haupt)) if os.path.exists(p)),
              None)
    if py is None:
        voraussetzung("kein .venv/bin/python3 im Arbeitsbaum oder im "
                      "Haupt-Checkout (README, Quickstart)")
    quelle = next((p for p in (os.path.join(w, "daten")
                               for w in (wurzel, haupt))
                   if os.path.isfile(os.path.join(p, "zustand.json"))), None)
    if quelle is None:
        voraussetzung("keine Betriebsdaten (daten/zustand.json) im "
                      "Arbeitsbaum oder im Haupt-Checkout")
    if shutil.which("node") is None:
        voraussetzung("node fehlt (drei Testdateien brauchen es)")

    kennung = hashlib.sha1(wurzel.encode()).hexdigest()[:10]
    kasten = os.environ.get("STREULICHT_VERIFY_DIR") or os.path.join(
        tempfile.gettempdir(), "streulicht-verify-" + kennung)
    os.makedirs(kasten, exist_ok=True)
    baum = os.path.join(kasten, "baum")
    ausgaben = os.path.join(kasten, "ausgaben")
    for d in (baum, ausgaben):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(ausgaben)

    t_start = time.time()
    snap, alter_h, neu = schnappschuss(quelle, os.path.join(kasten, "daten"),
                                       a.frisch)
    os.makedirs(baum)
    n_dateien = kopiere_arbeitsbaum(wurzel, baum)
    kopiere_baum(snap, os.path.join(baum, "daten"))
    kopf = git("rev-parse", "--short", "HEAD", cwd=wurzel).strip()
    schmutz = len([z for z in git("status", "--porcelain",
                                  cwd=wurzel).splitlines() if z])
    print("Sandkasten: %s" % kasten)
    print("   Code: %s @ %s, %d Dateien, %d ungespeicherte Aenderungen"
          % (wurzel, kopf, n_dateien, schmutz))
    print("   Daten: Schnappschuss %s, Alter %.1f h"
          % ("NEU gezogen" if neu else "wiederverwendet", alter_h))

    rot = []

    # --- 2. Bau -----------------------------------------------------------
    t_bau = time.time()
    rc, aus, sek = lauf([py, "-B", "skripte/ausliefern.py", "--trocken"], baum)
    with open(os.path.join(ausgaben, "bau.txt"), "w") as f:
        f.write(aus)
    print("Bau (ausliefern.py --trocken): rc=%s, %.1f s" % (rc, sek))
    if rc != 0:
        rot.append("Bau: Exitcode %s" % rc)
        print("\n".join("   | " + z for z in aus.strip().splitlines()[-15:]))
    if "[trocken] kein Push" not in aus and "unveraendert seit" not in aus:
        rot.append("Bau: die Trocken-Quittung fehlt in der Ausgabe")

    # --- 3. Ergebnis ------------------------------------------------------
    with open(os.path.join(baum, "konfig.json")) as f:
        orte = [o["name"] for o in json.load(f).get("orte") or []]
    erwartet = ["index.html", "bisher.html"] + [
        "bewerten-%s.html" % o for o in orte]
    for name in erwartet:
        p = os.path.join(baum, "web", name)
        if not os.path.isfile(p):
            rot.append("Ergebnis: web/%s ist nicht entstanden" % name)
        elif os.path.getmtime(p) < t_bau - 1:
            rot.append("Ergebnis: web/%s stammt nicht aus diesem Lauf" % name)
        elif os.path.getsize(p) < 1000:
            rot.append("Ergebnis: web/%s ist fast leer (%d Bytes)"
                       % (name, os.path.getsize(p)))
        else:
            print("   web/%-22s %7.1f kB" % (name, os.path.getsize(p) / 1e3))
    if os.path.isfile(os.path.join(baum, "web", "index.html")):
        rc, aus, _ = lauf([py, "-B", "skripte/waechter.py", "web/index.html",
                           "--grenze-h", str(WAECHTER_GRENZE_H)], baum)
        print("   Waechter: rc=%s, %s" % (rc, aus.strip().splitlines()[-1:]))
        if rc != 0:
            rot.append("Ergebnis: Waechter findet keinen Abrufzeitpunkt")

    # --- 4. Tests ---------------------------------------------------------
    dateien = sorted(glob.glob(os.path.join(baum, "skripte", "test_*.py"))
                     + glob.glob(os.path.join(baum, "skripte", "test_*.js")))
    dateien = [d for d in dateien if a.nur in os.path.basename(d)]
    summe = {"py": 0, "js": 0}
    zahl = {"py": 0, "js": 0}
    print("Tests (%d Dateien, nacheinander):" % len(dateien))
    for d in dateien:
        name = os.path.basename(d)
        art = "js" if name.endswith(".js") else "py"
        befehl = (["node", d] if art == "js" else [py, "-B", d])
        rc, aus, sek = lauf(befehl, baum)
        with open(os.path.join(ausgaben, name + ".txt"), "w") as f:
            f.write(aus)
        n_ok = sum(1 for z in aus.splitlines() if OK_ZEILE.match(z))
        summe[art] += n_ok
        zahl[art] += 1
        gut = rc == 0 and n_ok > 0
        print("   %-4s %-34s rc=%-4s ok=%-4d %5.1f s"
              % ("ok" if gut else "ROT", name, rc, n_ok, sek))
        if not gut:
            grund = ("Exitcode %s" % rc) if rc != 0 else "keine ok-Zeile"
            rot.append("Test %s: %s" % (name, grund))
            print("\n".join("      | " + z
                            for z in aus.strip().splitlines()[-12:]))
    if not dateien:
        rot.append("Tests: keine Testdatei gefunden (--nur %r)" % a.nur)

    gesamt = time.time() - t_start
    bilanz = ("%d Python-Pruefungen in %d Dateien + %d JS in %d Dateien, "
              "%.0f s" % (summe["py"], zahl["py"], summe["js"], zahl["js"],
                          gesamt))
    print()
    if rot:
        print("VERIFY ROT (%d): %s" % (len(rot), bilanz))
        for r in rot:
            print("   - " + r)
        print("   volle Ausgaben: %s" % ausgaben)
        return 1
    print("VERIFY GRUEN: Bau + %d Seiten + %s%s"
          % (len(erwartet), bilanz,
             " [nur %r]" % a.nur if a.nur else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
