"""Auslieferung: Push mit Zeitgrenze, Fehler stoppen die anderen Seiten nicht (T-0081).

WARUM DAS EINEN TEST BRAUCHT.  Zwei Dinge, die nur im Fehlerfall zaehlen und
deshalb nie auffallen:

* seiten#9: ein haengender `git push` haette den Seiten-Agenten unbegrenzt
  blockiert (launchd startet keine zweite Instanz).  `subprocess.run(timeout=)`
  allein haengt trotzdem - es toetet nur `git`, nicht den Enkel
  `git-remote-https`, der die Ausgaberohre offen haelt.  Die Probe baut genau
  diese Lage nach: ein Kindprozess mit langlebigem Enkel.
* seiten#4 / architektur#6: scheiterte seite.py, brach ausliefern.py ab, bevor
  die Bewertungsseite (auf der die Noten abgegeben werden) und die Bilanz
  gebaut und veroeffentlicht wurden.

Kein Netz, kein echter Push, keine Betriebsdaten: eigenes Temp-Verzeichnis mit
erfundenen Seitenbauern; die Veroeffentlichung wird durch eine Attrappe
ersetzt, ausser dort, wo sie selbst (mit lokalem git) geprueft wird.

Lauf:  .venv/bin/python3 skripte/test_ausliefern.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import ausliefern  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


def lebt(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # Zombie? (Elternprozess ist init oder wir) - ps fragt den Zustand
    z = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)],
                       capture_output=True, text=True).stdout.strip()
    return bool(z) and not z.startswith("Z")


print("1. lauf_mit_frist: Exitcode und Ausgabe")
rc, aus = ausliefern.lauf_mit_frist(["echo", "hallo"], BASIS, 10)
pruefe(rc == 0 and "hallo" in aus,
       "Erfolg: Exitcode 0 (%r, %r)" % (rc, aus))
rc, aus = ausliefern.lauf_mit_frist(
    ["sh", "-c", "echo grund >&2; exit 3"], BASIS, 10)
pruefe(rc == 3 and "grund" in aus,
       "Fehlschlag: Exitcode und Fehlerausgabe bleiben (%r, %r)" % (rc, aus))

print("\n2. Ein haengender Push wird samt Enkelprozess beendet")
d = tempfile.mkdtemp()
try:
    pidfile = os.path.join(d, "enkel.pid")
    # Wie git push: der Elternprozess wartet auf einen Enkel, der die
    # Ausgaberohre erbt und lange lebt.
    skript = "sleep 25 & echo $! > %s; wait" % pidfile
    t0 = time.time()
    rc, aus = ausliefern.lauf_mit_frist(["sh", "-c", skript], d, 1)
    dauer = time.time() - t0
    pruefe(rc is None, "Fristablauf wird als None gemeldet (%r)" % (rc,))
    pruefe(dauer < 10, "und kehrt rechtzeitig zurueck (%.1f s statt 25)" % dauer)
    enkel = int(open(pidfile).read().strip())
    time.sleep(0.3)
    pruefe(not lebt(enkel), "der Enkelprozess ist tot (pid %d)" % enkel)
    if lebt(enkel):
        os.kill(enkel, 9)
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\n3. pushe: Wiederholung, Zeitgrenze je Versuch, endgueltiger Fehler")
echt_lauf, echt_sleep = ausliefern.lauf_mit_frist, time.sleep


def mit_antworten(antworten):
    """pushe() fahren; `antworten` = Exitcodes der Reihe nach (None = Frist)."""
    aufrufe, pausen = [], []
    folge = list(antworten)

    def falsch(befehl, cwd, frist):
        aufrufe.append((list(befehl), frist))
        rc = folge.pop(0)
        return rc, ("" if rc in (0, None) else "fatal: Test")

    ausliefern.lauf_mit_frist = falsch
    time.sleep = lambda s: pausen.append(s)
    ende = None
    try:
        ausliefern.pushe("ssh://fern", "/tmp")
    except SystemExit as ex:
        ende = ex
    finally:
        ausliefern.lauf_mit_frist, time.sleep = echt_lauf, echt_sleep
    return aufrufe, pausen, ende


a, p, e = mit_antworten([0])
pruefe(len(a) == 1 and not p and e is None,
       "gleich geklappt: ein Versuch, keine Pause")
pruefe(a[0][0][:3] == ["git", "push", "--force"]
       and a[0][0][-1] == "gh-pages:gh-pages",
       "es wird nur der Wegwerfzweig gepusht (%s)" % a[0][0][-1])
a, p, e = mit_antworten([None, 0])
pruefe(len(a) == 2 and len(p) == 1 and e is None,
       "ein haengender Versuch zaehlt als Fehlschlag und wird wiederholt")
a, p, e = mit_antworten([None, None, None])
pruefe(len(a) == ausliefern.PUSH_VERSUCHE and e is not None
       and e.code not in (None, 0),
       "nur Zeitueberschreitungen: nach %d Versuchen endgueltig, mit Grund "
       "(%d Versuche)" % (ausliefern.PUSH_VERSUCHE, len(a)))
pruefe(len(p) == ausliefern.PUSH_VERSUCHE - 1,
       "Pausen nur ZWISCHEN den Versuchen (%d)" % len(p))
a, p, e = mit_antworten([1, 1, 1])
pruefe(len(a) == 3 and e is not None, "echte Fehler genauso")
pruefe(all(f == ausliefern.PUSH_FRIST and f is not None for _, f in a),
       "jeder Versuch hat eine Zeitgrenze (%s s)"
       % sorted({f for _, f in a}))
pruefe(ausliefern.PUSH_VERSUCHE * ausliefern.PUSH_FRIST
       + (ausliefern.PUSH_VERSUCHE - 1) * ausliefern.PUSH_PAUSE <= 600,
       "schlimmstenfalls weniger als ein Tick (10 Minuten)")

print("\n4. Fingerabdruck wird nur nach erfolgreichem Push gestempelt")
d = tempfile.mkdtemp()
alt_basis = ausliefern.BASIS
try:
    os.makedirs(os.path.join(d, "web"))
    os.makedirs(os.path.join(d, "daten"))
    with open(os.path.join(d, "web", "index.html"), "w") as f:
        f.write("<html>probe</html>")
    subprocess.run(["git", "init", "-q", "-b", "main", d], check=True)
    subprocess.run(["git", "-C", d, "remote", "add", "origin",
                    "file:///gibt/es/nicht"], check=True)
    ausliefern.BASIS = d
    stempel = os.path.join(d, "daten", ".ausgeliefert")

    def pushe_kaputt(fern, cwd):
        raise SystemExit("Push endgueltig fehlgeschlagen (Test)")

    echt_pushe = ausliefern.pushe
    ausliefern.pushe = pushe_kaputt
    try:
        try:
            ausliefern.veroeffentliche(False)
            ende = None
        except SystemExit as ex:
            ende = ex
        pruefe(ende is not None and not os.path.exists(stempel),
               "Push scheitert: kein Stempel, der naechste Tick versucht es "
               "wieder")
        ausliefern.pushe = lambda fern, cwd: None
        ausliefern.veroeffentliche(False)
        pruefe(os.path.exists(stempel), "Push gelingt: Stempel gesetzt")
    finally:
        ausliefern.pushe = echt_pushe
finally:
    ausliefern.BASIS = alt_basis
    shutil.rmtree(d, ignore_errors=True)


# ----------------------------------------------------------------------
# baue() und main() mit erfundenen Seitenbauern in einem Temp-BASIS
# ----------------------------------------------------------------------
def neues_basis(seite_rc=0, bewertung_rc=0, bisher_rc=0):
    """Temp-BASIS mit drei Seitenbauern, die ihren Lauf in ein Protokoll
    schreiben und mit dem gewuenschten Exitcode enden."""
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "skripte"))
    os.makedirs(os.path.join(d, "web"))
    os.makedirs(os.path.join(d, "daten"))
    with open(os.path.join(d, "konfig.json"), "w") as f:
        json.dump({"orte": [{"name": "berlin"}]}, f)
    for name, rc in (("seite", seite_rc), ("bewertungsseite", bewertung_rc),
                     ("bisher", bisher_rc)):
        with open(os.path.join(d, "skripte", name + ".py"), "w") as f:
            f.write("import sys\n"
                    "open(%r, 'a').write(%r + '\\n')\n"
                    "print('%s fertig')\n"
                    "if %d:\n"
                    "    print('Absturz in %s', file=sys.stderr)\n"
                    "sys.exit(%d)\n"
                    % (os.path.join(d, "lauf.log"), name, name, rc, name, rc))
    return d


def gelaufen(d):
    p = os.path.join(d, "lauf.log")
    return open(p).read().split() if os.path.exists(p) else []


print("\n5. baue(): jeder Seitenbauer laeuft, auch nach einem Fehler")


def baue_in(d):
    """baue() gegen ein Temp-BASIS.  -> (Prognose, Fehlerliste, Abbruch)."""
    alt = ausliefern.BASIS
    ausliefern.BASIS = d
    try:
        prognose, fl = ausliefern.baue(False)
        return prognose, fl, None
    except SystemExit as ex:
        return None, None, ex
    finally:
        ausliefern.BASIS = alt


for bezeichnung, kw, erwartet in (
        ("seite.py scheitert", dict(seite_rc=1), "seite.py"),
        ("bewertungsseite.py scheitert", dict(bewertung_rc=1),
         "bewertungsseite.py"),
        ("bisher.py scheitert", dict(bisher_rc=1), "bisher.py")):
    d = neues_basis(**kw)
    prognose, fl, abbruch = baue_in(d)
    pruefe(abbruch is None and gelaufen(d) == ["seite", "bewertungsseite",
                                               "bisher"],
           "%s: baue() bricht nicht ab, alle drei Bauer sind gelaufen (%s)"
           % (bezeichnung, gelaufen(d)))
    pruefe(fl is not None and len(fl) == 1 and fl[0].startswith(erwartet),
           "%s: genau dieser Fehler wird gemeldet (%s)" % (bezeichnung, fl))
    shutil.rmtree(d, ignore_errors=True)
d = neues_basis(seite_rc=2)
prognose, fl, abbruch = baue_in(d)
pruefe(fl == [] and prognose is False,
       "seite.py Exitcode 2 (noch keine Prognose) ist kein Fehler")
shutil.rmtree(d, ignore_errors=True)
d = neues_basis()
prognose, fl, abbruch = baue_in(d)
pruefe(fl == [] and prognose is True, "alles gut: keine Fehler")
shutil.rmtree(d, ignore_errors=True)


print("\n6. main(): Fehler sammeln, weiterlaufen, am Ende Exitcode != 0")


def main_fahren(seite_rc=0, push_fehler=False, sicherung_fehler=None,
                sicherung_wirft=False, trocken=False):
    """main() mit Attrappen fuer Sicherung und Veroeffentlichung.
    Rueckgabe: (Ende, Aufrufprotokoll, Bauprotokoll)."""
    d = neues_basis(seite_rc=seite_rc)
    protokoll = []

    def sichern():
        protokoll.append("sicherung")
        if sicherung_wirft:
            raise RuntimeError("Sicherung kaputt (Test)")
        return list(sicherung_fehler or [])

    def veroeff(trocken_, immer=False):
        protokoll.append("veroeffentlicht")
        if push_fehler:
            raise SystemExit("Push endgueltig fehlgeschlagen (Test)")

    alt = (ausliefern.BASIS, ausliefern.sichere_zustand,
           ausliefern.veroeffentliche)
    ausliefern.BASIS = d
    ausliefern.sichere_zustand = sichern
    ausliefern.veroeffentliche = veroeff
    sicher, sys.argv = sys.argv, ["ausliefern.py"] + (
        ["--trocken"] if trocken else [])
    ende = None
    try:
        ausliefern.main()
    except SystemExit as ex:
        ende = ex
    finally:
        sys.argv = sicher
        (ausliefern.BASIS, ausliefern.sichere_zustand,
         ausliefern.veroeffentliche) = alt
    bau = gelaufen(d)
    shutil.rmtree(d, ignore_errors=True)
    return ende, protokoll, bau


ende, prot, bau = main_fahren()
pruefe(ende is None and prot == ["sicherung", "veroeffentlicht"]
       and bau == ["seite", "bewertungsseite", "bisher"],
       "alles gut: Sicherung, drei Seiten, Veroeffentlichung, Exitcode 0")

ende, prot, bau = main_fahren(seite_rc=1)
pruefe("veroeffentlicht" in prot and len(bau) == 3,
       "seite.py scheitert: Bewertungs- und Bilanzseite werden trotzdem "
       "gebaut UND veroeffentlicht")
pruefe(ende is not None and ende.code not in (None, 0)
       and "seite.py" in str(ende.code),
       "und der Lauf endet mit Exitcode != 0, mit Grund (%s)"
       % (ende.code if ende else None))

ende, prot, bau = main_fahren(push_fehler=True)
pruefe(prot[0] == "sicherung" and ende is not None
       and "Veroeffentlichen" in str(ende.code),
       "Push scheitert: Exitcode != 0 (%s)" % (ende.code if ende else None))

ende, prot, bau = main_fahren(sicherung_fehler=["Sicherung nach x fehlgeschlagen"])
pruefe(len(bau) == 3 and "veroeffentlicht" in prot and ende is not None
       and "Sicherung" in str(ende.code),
       "Sicherung meldet Fehler: Seiten laufen weiter, Exitcode != 0")

ende, prot, bau = main_fahren(sicherung_wirft=True)
pruefe(len(bau) == 3 and "veroeffentlicht" in prot and ende is not None,
       "Sicherung wirft eine Ausnahme: Seiten laufen trotzdem weiter, "
       "Exitcode != 0")

ende, prot, bau = main_fahren(trocken=True)
pruefe("sicherung" not in prot and ende is None,
       "--trocken fasst keine Sicherung an")

print("\n7. sichere_zustand: Pfade und Zusatzordner aus der Konfiguration")
d = tempfile.mkdtemp()
alt_basis = ausliefern.BASIS
try:
    ausliefern.BASIS = d
    os.makedirs(os.path.join(d, "daten"))
    with open(os.path.join(d, "daten", "zustand.json"), "w") as f:
        json.dump({"berlin": {"abende": {}}}, f)
    zusatz = os.path.join(d, "wolke")
    with open(os.path.join(d, "konfig.json"), "w") as f:
        json.dump({"sicherung_ordner": zusatz}, f)
    f = ausliefern.sichere_zustand()
    lokal = os.listdir(os.path.join(d, "daten", "sicherung"))
    pruefe(f == [] and len(lokal) == 1 and os.path.isdir(zusatz)
           and os.listdir(zusatz) == lokal,
           "lokal (daten/sicherung) UND im Zusatzordner (%s)" % f)
finally:
    ausliefern.BASIS = alt_basis
    shutil.rmtree(d, ignore_errors=True)

print("")
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
