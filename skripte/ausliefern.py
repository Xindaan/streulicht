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
import signal
import subprocess
import sys
import tempfile
import time

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logbuch  # noqa: E402
import sicherung  # noqa: E402

# Die Datei, die betrieb/de.greatbelow.streulicht.seite.plist als
# StandardOutPath setzt (T-0081: Stempel + Rotation).
LOGDATEI = os.path.join(BASIS, "daten", "seite.log")
# Push (T-0081, seiten#9): hoechstens PUSH_VERSUCHE Versuche, jeder hoechstens
# PUSH_FRIST Sekunden, dazwischen PUSH_PAUSE Sekunden.  Ein haengender Push
# haette den Seiten-Agenten unbegrenzt blockiert - launchd startet in der
# Zeit keine zweite Instanz.  Schlimmstenfalls 3 x 120 s + 2 x 60 s = 8
# Minuten, also weniger als ein Tick (10 Minuten).
PUSH_VERSUCHE = 3
PUSH_FRIST = 120
PUSH_PAUSE = 60
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


def _seitenskript(name):
    """Ein Seitenbauer als Unterprozess: (Exitcode, stdout, stderr)."""
    r = subprocess.run([sys.executable, os.path.join(BASIS, "skripte", name)],
                       cwd=BASIS, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def baue(trocken):
    """Alle Seiten erzeugen.  Rueckgabe: (Prognose gebaut?, Fehlerliste).

    JEDER Seitenbauer laeuft fuer sich (T-0081, seiten#4/architektur#6).
    Frueher brach ein Fehler von seite.py per SystemExit ab, bevor
    Bewertungs- und Bilanzseite gebaut und veroeffentlicht wurden - ein Fehler
    in der Prognoseseite fror so auch die Seite ein, auf der Andre seine
    Noten abgibt.  Jetzt wird weitergebaut, der Fehler steht im Log, und
    main() beendet den Lauf am Ende mit Exitcode != 0.  Eine Seite, deren
    Bauer scheitert, bleibt in der alten Fassung stehen (der Fingerabdruck in
    veroeffentliche() merkt keine Aenderung).  Exitcode 2 von seite.py heisst
    "noch keine Prognose" und ist kein Fehler.
    """
    fehler = []
    prognose = False
    rc, aus, err = _seitenskript("seite.py")
    if rc == 2:
        print("   Prognoseseite: noch keine Prognose vorhanden, wird "
              "ausgelassen")
    elif rc != 0:
        print("   Prognoseseite FEHLGESCHLAGEN (%d):\n%s"
              % (rc, (err or aus or "").strip()[-800:]))
        fehler.append("seite.py (Exitcode %d)" % rc)
    else:
        zeilen = aus.strip().splitlines()
        print("   Prognoseseite: " + (zeilen[-1] if zeilen else "ok"))
        prognose = True
    rc, aus, err = _seitenskript("bewertungsseite.py")
    if rc != 0:
        print("   Bewertungsseiten FEHLGESCHLAGEN (%d):\n%s"
              % (rc, (err or aus or "").strip()[-800:]))
        fehler.append("bewertungsseite.py (Exitcode %d)" % rc)
    else:
        print("   Bewertungsseiten:\n" + "\n".join(
            "      " + z for z in aus.strip().splitlines()))
    rc, aus, err = _seitenskript("bisher.py")
    if rc != 0:
        print("   Bilanzseite FEHLGESCHLAGEN (%d):\n%s"
              % (rc, (err or aus or "").strip()[-800:]))
        fehler.append("bisher.py (Exitcode %d)" % rc)
    else:
        zeilen = aus.strip().splitlines()
        print("   " + (zeilen[-1] if zeilen else "Bilanzseite: ok"))
    return prognose, fehler


def lauf_mit_frist(befehl, cwd, frist):
    """Befehl mit Zeitgrenze: (Exitcode, Ausgabe); Exitcode None bei Fristablauf.

    `subprocess.run(timeout=...)` allein reicht NICHT: es toetet nur den
    direkten Kindprozess.  `git push` startet `git-remote-https` als Enkel,
    der die Ausgaberohre weiter offen haelt - das anschliessende
    communicate() wartet dann doch, bis der Enkel von selbst endet.  Darum
    eigene Prozessgruppe (start_new_session) und bei Fristablauf die ganze
    Gruppe beenden.
    """
    p = subprocess.Popen(befehl, cwd=cwd, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True,
                         start_new_session=True)
    try:
        aus, err = p.communicate(timeout=frist)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            p.kill()
        try:
            p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        return None, ""
    return p.returncode, (err or aus or "")


def pushe(fern, cwd):
    """Den Wegwerfzweig pushen: Zeitgrenze je Versuch, wenige Wiederholungen.

    Wiederholen, aber nur ein paar Mal: der haeufigste Fehlschlag ist kein
    Zugriffsproblem, sondern ein Rechner, der noch kein Netz hat.  Am
    17.08.2026 war der Mac von 07:30 bis nach 08:15 ohne Namensaufloesung -
    Alarm, Archiv, Bewertungsabruf und dieser Push sind alle vier daran
    gescheitert, jeder genau einmal.  Ein Versuch, der haengt (T-0081,
    seiten#9), zaehlt wie ein fehlgeschlagener.
    """
    for versuch in range(1, PUSH_VERSUCHE + 1):
        rc, grund = lauf_mit_frist(
            ["git", "push", "--force", "-q", fern, "%s:%s" % (ZWEIG, ZWEIG)],
            cwd, PUSH_FRIST)
        if rc == 0:
            return
        if rc is None:
            grund = "keine Antwort nach %d s (abgebrochen)" % PUSH_FRIST
        grund = (grund or "").strip()
        print("   Push-Versuch %d fehlgeschlagen: %s"
              % (versuch, grund.splitlines()[-1] if grund else "?"))
        if versuch == PUSH_VERSUCHE:
            raise SystemExit("Push endgueltig fehlgeschlagen:\n" + grund)
        time.sleep(PUSH_PAUSE)


def sichere_zustand():
    """Tageskopie der Zustandsdatei (T-0081, betrieb#6).  -> Fehlerliste."""
    zusatz = sicherung.aus_konfig(os.path.join(BASIS, "konfig.json"))
    return sicherung.sichere(os.path.join(BASIS, "daten", "zustand.json"),
                             os.path.join(BASIS, "daten", "sicherung"),
                             zusatz)


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
        pushe(fern, tmp)
        with open(stempel, "w") as f:
            f.write(fingerabdruck + "\n")
        print("   nach %s gepusht (Wegwerfzweig, ein Commit)" % ZWEIG)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def ein_ort_pruefen():
    """Warnt, wenn mehr als ein Ort konfiguriert ist (T-0071).

    DIE SEITEN KOENNEN NUR EINEN ORT.  `konfig.json` fuehrt `orte[]` als
    Liste, und Alarm, Erinnerung und Bewertungsseite arbeiten sie auch
    wirklich durch - die Prognoseseite, die Bilanz, der Vertikalschnitt und
    die Faecherkarte nicht: Berlins Koordinaten und die Berliner
    Klimatologie stehen dort fest im Quelltext (`skripte/seite.py`,
    `skripte/bisher.py`, `skripte/schnitt.py`, `skripte/faecher.py`).

    Ein zweiter Ort bekaeme deshalb Pushs, die gegen Berlins s* gerechnet
    sind, und eine Prognoseseite, die Berlin zeigt.  Das faellt nirgends
    auf - beide Laeufe enden mit Exitcode 0.

    Bewusst eine WARNUNG und kein Abbruch: die Mehrortfaehigkeit ist ein
    erklaertes Ziel (E0, "Ort als Parameter, auch fuer Freunde"), und ein
    harter Riegel wuerde den halb fertigen Weg dorthin versperren.
    """
    import json
    with open(os.path.join(BASIS, "konfig.json")) as f:
        orte = json.load(f).get("orte") or []
    if len(orte) > 1:
        print("   WARNUNG: %d Orte konfiguriert (%s), aber Prognoseseite, "
              "Bilanz, Schnitt und Karte sind auf Berlin fest verdrahtet - "
              "die ausgelieferten Seiten zeigen NUR den ersten Ort."
              % (len(orte), ", ".join(o.get("name", "?") for o in orte)))
    return len(orte)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trocken", action="store_true")
    ap.add_argument("--immer", action="store_true",
                    help="auch pushen, wenn sich nichts geaendert hat")
    a = ap.parse_args()
    # Fehler sammeln statt beim ersten abzubrechen (T-0081): jeder Schritt
    # laeuft, soweit er von den vorigen nicht abhaengt; der Exitcode am Ende
    # sagt, ob IRGENDETWAS schiefging.
    fehler = []
    if not a.trocken:
        print("Sichern ...")
        try:
            fehler += sichere_zustand()
        except Exception as ex:                              # noqa: BLE001
            fehler.append("Sicherung (%s: %s)" % (type(ex).__name__, ex))
        for f in fehler:
            print("   FEHLER: " + f)
    print("Bauen ...")
    ein_ort_pruefen()
    _, baufehler = baue(a.trocken)
    fehler += baufehler
    print("Veroeffentlichen ...")
    try:
        veroeffentliche(a.trocken, a.immer)
    except SystemExit as ex:
        print("   FEHLER: %s" % ex)
        fehler.append("Veroeffentlichen")
    if fehler:
        raise SystemExit("Lauf mit Fehlern: " + "; ".join(fehler))


if __name__ == "__main__":
    logbuch.einrichten(LOGDATEI)      # T-0081: Datum+Uhrzeit, Rotation
    main()
