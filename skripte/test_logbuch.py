"""Logzeilen mit Datum+Uhrzeit, Rotation unter launchd (T-0081).

WARUM DAS EINEN TEST BRAUCHT.  Die Rotation hat eine Falle, die man nur
sieht, wenn man sie so nachbaut, wie launchd den Agenten startet: launchd
oeffnet die Logdatei (StandardOutPath UND StandardErrorPath, dieselbe) VOR
dem Prozess.  Benennt der Lauf sie nur um, schreibt er danach in
`<name>.log.1` weiter - das aktuelle Log bliebe leer, und die Zeilen, die
erklaeren sollen, was heute passiert ist, stuenden in der Altdatei.  Darum
laeuft die Probe in einem echten Unterprozess mit umgeleitetem stdout/stderr.

Dazu: Stempel auf jeder Zeile (auch Tracebacks und stderr), kein Doppelstempel
auf Zeilen, die schon einen tragen (alarm.melde), und die Logdatei, die jeder
Agent rotiert, ist wirklich die, die seine plist beschreibt.

Kein Netz, keine Betriebsdaten: alles in einem Temp-Verzeichnis.

Lauf:  .venv/bin/python3 skripte/test_logbuch.py
"""
import ast
import io
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKRIPTE = os.path.join(BASIS, "skripte")
sys.path.insert(0, SKRIPTE)
sys.path.insert(0, BASIS)

import logbuch  # noqa: E402

fehler = []
STEMPEL = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ")


def lies(pfad, modus="r"):
    """Dateiinhalt, oder leer, wenn es die Datei nicht gibt (Probe nicht abbrechen)."""
    try:
        with open(pfad, modus) as f:
            return f.read()
    except OSError:
        return b"" if "b" in modus else ""


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


print("1. Der Stempel steht auf jeder Zeile - aber nur einmal")
ziel = io.StringIO()
w = logbuch.Stempelschreiber(ziel, uhr=lambda: "2026-10-09 08:00:00")
w.write("erste Zeile\n")
w.write("zweite ")
w.write("Zeile in Teilen\n")
w.write("a\nb\n")
w.write("2026-10-09 07:59:59 schon gestempelt (alarm.melde)\n")
zeilen = ziel.getvalue().splitlines()
pruefe(zeilen[0] == "2026-10-09 08:00:00 erste Zeile",
       "Zeile mit Datum und Uhrzeit (%r)" % zeilen[0])
pruefe(zeilen[1] == "2026-10-09 08:00:00 zweite Zeile in Teilen",
       "in Teilen geschrieben: nur der Zeilenanfang wird gestempelt")
pruefe(zeilen[2:4] == ["2026-10-09 08:00:00 a", "2026-10-09 08:00:00 b"],
       "mehrere Zeilen in einem Aufruf: jede bekommt einen Stempel")
pruefe(zeilen[4] == "2026-10-09 07:59:59 schon gestempelt (alarm.melde)",
       "eine schon gestempelte Zeile bleibt, wie sie ist (%r)" % zeilen[4])

print("\n2. Im Unterprozess: stdout, stderr und Traceback tragen den Stempel")
d = tempfile.mkdtemp()
try:
    log = os.path.join(d, "x.log")
    code = ("import sys; sys.path.insert(0, %r); import logbuch; "
            "logbuch.einrichten(None); print('ausgabe'); "
            "print('meldung', file=sys.stderr); raise SystemExit('grund')"
            % SKRIPTE)
    with open(log, "ab") as f:
        r = subprocess.run([sys.executable, "-B", "-c", code], stdout=f,
                           stderr=f)
    zeilen = open(log).read().splitlines()
    pruefe(r.returncode == 1, "SystemExit(str) bleibt Exitcode 1")
    pruefe(len(zeilen) == 3 and all(STEMPEL.match(z) for z in zeilen),
           "alle %d Zeilen gestempelt: %s" % (len(zeilen), zeilen))
    code = ("import sys; sys.path.insert(0, %r); import logbuch; "
            "logbuch.einrichten(None); raise ValueError('kaputt')" % SKRIPTE)
    open(log, "w").close()
    with open(log, "ab") as f:
        subprocess.run([sys.executable, "-B", "-c", code], stdout=f, stderr=f)
    zeilen = open(log).read().splitlines()
    pruefe(len(zeilen) >= 3 and all(STEMPEL.match(z) for z in zeilen),
           "auch jede Zeile eines Tracebacks (%d Zeilen)" % len(zeilen))

    print("\n3. Rotation, wie launchd den Agenten startet")

    def unter_launchd(logpfad, grenze, vorinhalt):
        """Logdatei mit `vorinhalt` anlegen, Agent mit stdout=stderr=Datei."""
        with open(logpfad, "wb") as f:
            f.write(vorinhalt)
        code = ("import sys; sys.path.insert(0, %r); import logbuch; "
                "logbuch.einrichten(%r, %d); print('NEU eins'); "
                "print('NEU zwei (stderr)', file=sys.stderr)"
                % (SKRIPTE, logpfad, grenze))
        with open(logpfad, "ab") as f:
            subprocess.run([sys.executable, "-B", "-c", code], stdout=f,
                           stderr=f, check=True)

    gross = b"ALT " + b"x" * 400 + b"\n"
    log = os.path.join(d, "alarm.log")
    unter_launchd(log, 200, gross)
    pruefe(lies(log + ".1", "rb") == gross,
           "die grosse Datei liegt unveraendert in <name>.1")
    aktuell = lies(log).splitlines()
    pruefe(len(aktuell) == 2 and "NEU eins" in aktuell[0]
           and "NEU zwei" in aktuell[1],
           "die eigenen Zeilen (stdout UND stderr) landen im NEUEN Log, nicht "
           "in .1 (%s)" % aktuell)
    pruefe(b"NEU" not in lies(log + ".1", "rb"),
           "in .1 steht nichts vom laufenden Lauf")
    pruefe(all(STEMPEL.match(z) for z in aktuell),
           "und sie sind gestempelt")

    log2 = os.path.join(d, "klein.log")
    unter_launchd(log2, 100000, b"alt\n")
    aktuell = lies(log2).splitlines()
    pruefe(not os.path.exists(log2 + ".1") and aktuell[0] == "alt"
           and len(aktuell) == 3,
           "unter der Grenze: keine Rotation, es wird angehaengt")

    # Zweite Rotation: genau EINE Generation, die aeltere wird ersetzt.
    unter_launchd(log, 200, b"ZWEITE GENERATION " + b"y" * 400 + b"\n")
    pruefe(lies(log + ".1", "rb").startswith(b"ZWEITE GENERATION"),
           "<name>.1 wird beim naechsten Drehen ersetzt (eine Generation)")

    print("\n4. Ein Lauf im Terminal oder Test fasst das Betriebslog nicht an")
    log3 = os.path.join(d, "betrieb.log")
    with open(log3, "wb") as f:
        f.write(gross)
    code = ("import sys; sys.path.insert(0, %r); import logbuch; "
            "logbuch.einrichten(%r, 200); print('Terminallauf')"
            % (SKRIPTE, log3))
    r = subprocess.run([sys.executable, "-B", "-c", code],
                       capture_output=True, text=True)    # stdout = Pipe
    pruefe(not os.path.exists(log3 + ".1")
           and lies(log3, "rb") == gross,
           "stdout ist nicht die Logdatei: nichts gedreht, nichts angehaengt")
    pruefe(STEMPEL.match(r.stdout) is not None,
           "gestempelt wird trotzdem (%r)" % r.stdout.strip())
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\n5. alarm.melde stempelt mit Datum, nicht nur mit der Uhrzeit")
import alarm  # noqa: E402

umgelenkt, sys.stdout = sys.stdout, io.StringIO()
try:
    alarm.melde("Probe")
    zeile = sys.stdout.getvalue()
finally:
    sys.stdout = umgelenkt
pruefe(STEMPEL.match(zeile) is not None and zeile.rstrip().endswith("Probe"),
       "melde() ohne Stempelschreiber stempelt selbst (%r)" % zeile.strip())

print("\n6. Jeder Agent rotiert genau die Datei, die seine plist beschreibt")
# launchd hat die Datei beim Start schon offen; die Rotation erkennt sie am
# Inode.  Zeigt LOGDATEI im Skript auf einen anderen Namen als die plist,
# dreht der Agent nie - und merkt es keiner, weil nichts fehlschlaegt.
agenten = [("alarm", "alarm"), ("ausliefern", "seite"),
           ("bewertungen_holen", "bewertung"), ("erinnerung", "erinnerung")]
for modul, plistname in agenten:
    pl = os.path.join(BASIS, "betrieb",
                      "de.greatbelow.streulicht.%s.plist" % plistname)
    with open(pl, "rb") as f:
        p = plistlib.load(f)
    m = __import__(modul)
    soll = os.path.basename(p["StandardOutPath"])
    pruefe(os.path.basename(m.LOGDATEI) == soll
           and p["StandardErrorPath"] == p["StandardOutPath"],
           "%s: LOGDATEI %s = StandardOutPath %s (= StandardErrorPath)"
           % (modul, os.path.basename(m.LOGDATEI), soll))
    # Verdrahtung: der __main__-Block ruft einrichten(LOGDATEI) vor main().
    baum = ast.parse(open(os.path.join(SKRIPTE, modul + ".py")).read())
    rumpf = [n for n in baum.body if isinstance(n, ast.If)
             and "__main__" in ast.dump(n.test)][0].body
    namen = [ast.unparse(n.value.func) for n in rumpf
             if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)]
    pruefe(namen[:2] == ["logbuch.einrichten", "main"],
           "%s: __main__ ruft erst logbuch.einrichten, dann main (%s)"
           % (modul, namen))

print("")
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
