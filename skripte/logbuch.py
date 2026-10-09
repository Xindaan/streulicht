"""Logzeilen mit Datum und Uhrzeit, und eine Rotation, die zu launchd passt.

WARUM (Review 09.10.2026, architektur#14, betrieb#9, seiten#15).  Nur
`alarm.melde()` stempelte, und nur mit HH:MM:SS; seite.log (3,4 MB, 78.733
Zeilen), bewertung.log und erinnerung.log hatten gar keinen Laufzeitstempel -
die ISO-Daten darin sind Inhalte (Zielabende), keine Laufzeiten.  Eine
Rotation gab es nicht.  Wer fragt "wann ist das passiert?", konnte nur aus
der Reihenfolge raten.

STEMPEL AM AUSGABEKANAL, NICHT AN JEDEM print.  `einrichten()` ersetzt
sys.stdout und sys.stderr durch einen Schreiber, der jede neue Zeile mit
"JJJJ-MM-TT HH:MM:SS " beginnt.  Das erfasst auch Tracebacks, SystemExit-
Meldungen und das, was Unterprozesse durchreichen - ohne dass jede der rund
hundert Stellen einzeln angefasst werden muss (und ohne dass die naechste
neue Stelle den Stempel vergisst).

ROTATION PASST ZU LAUNCHD.  launchd oeffnet StandardOutPath/StandardErrorPath
VOR dem Start des Prozesses und haelt die Datei nur waehrend des Laufs
offen.  Benennt der Lauf die Datei einfach um, schreibt er selbst danach in
die umbenannte Datei (sein Dateideskriptor zeigt auf den alten Inode) - das
eigene Log stuende dann in `<name>.log.1`.  Darum: umbenennen UND den
eigenen Kanal (fd 1 und 2) danach auf die frische Datei umlenken.  Der
naechste Lauf oeffnet ohnehin die neue Datei.  Gedreht wird nur, wenn
stdout wirklich diese Logdatei IST (gleicher Inode): ein Lauf im Terminal
oder in einem Test fasst kein Betriebslog an.

EINE Generation (`<name>.1`, wird beim naechsten Drehen ueberschrieben):
reicht fuer die Frage "was war letzte Woche", und mehr Pflegeaufwand soll es
nicht geben.
"""
import os
import re
import sys
from datetime import datetime

GRENZE_BYTES = 1000000            # ~1 MB
STEMPEL = "%Y-%m-%d %H:%M:%S"
# Eine Zeile, die schon mit Datum UND Uhrzeit beginnt (alarm.melde, oder ein
# Unterprozess, der selbst stempelt), wird nicht doppelt gestempelt.
_SCHON = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")


def jetzt_text():
    return datetime.now().strftime(STEMPEL)


class Stempelschreiber:
    """Datei-Attrappe, die jeden Zeilenanfang mit Datum+Uhrzeit versieht.

    Reicht alles andere (encoding, fileno, isatty ...) an den echten Kanal
    durch.  Jede vollstaendige Zeile wird sofort geflusht: ein Lauf, der
    mitten drin stirbt (Schlaf, kill, OOM), hinterlaesst sonst genau die
    letzten Zeilen nicht, die erklaeren, warum.
    """

    def __init__(self, ziel, uhr=jetzt_text):
        self._ziel = ziel
        self._uhr = uhr
        self._anfang = True

    def write(self, s):
        if not s:
            return 0
        for stueck in s.splitlines(keepends=True):
            if self._anfang and not _SCHON.match(stueck):
                self._ziel.write(self._uhr() + " ")
            self._ziel.write(stueck)
            self._anfang = stueck.endswith("\n")
        if "\n" in s:
            self._ziel.flush()
        return len(s)

    def flush(self):
        self._ziel.flush()

    def __getattr__(self, name):
        return getattr(self._ziel, name)


def melde(text):
    """Eine Zeile ausgeben; stempelt selbst, wenn kein Stempelschreiber aktiv ist."""
    if isinstance(sys.stdout, Stempelschreiber):
        print(text, flush=True)
    else:
        print("%s %s" % (jetzt_text(), text), flush=True)


def ist_dieselbe_datei(pfad, fd):
    """Zeigt der Dateideskriptor `fd` auf die Datei `pfad`?"""
    try:
        a, b = os.stat(pfad), os.fstat(fd)
    except OSError:
        return False
    return (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino)


def rotiere(pfad, grenze=GRENZE_BYTES):
    """Ist die Logdatei groesser als `grenze`, nach `<pfad>.1` verschieben.

    True, wenn gedreht wurde.  Ein Fehler hier darf den Lauf nie verhindern.
    """
    try:
        if os.path.getsize(pfad) <= grenze:
            return False
        os.replace(pfad, pfad + ".1")
        return True
    except OSError:
        return False


def _auf_frische_datei_umlenken(pfad):
    """fd 1 und 2 dieses Prozesses auf die neu angelegte Logdatei legen."""
    for kanal in (sys.stdout, sys.stderr):
        try:
            kanal.flush()
        except Exception:                                    # noqa: BLE001
            pass
    fd = os.open(pfad, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.dup2(fd, 1)
        os.dup2(fd, 2)
    finally:
        os.close(fd)


def einrichten(logpfad=None, grenze=GRENZE_BYTES):
    """Am Anfang von main() eines Agenten: ggf. drehen, dann stempeln.

    `logpfad` ist die Datei, die die plist als StandardOutPath setzt.  Ohne
    Pfad (oder wenn stdout nicht diese Datei ist) wird nur gestempelt.
    """
    if logpfad and ist_dieselbe_datei(logpfad, 1):
        if rotiere(logpfad, grenze):
            try:
                _auf_frische_datei_umlenken(logpfad)
            except OSError:
                pass
    for name in ("stdout", "stderr"):
        kanal = getattr(sys, name)
        if not isinstance(kanal, Stempelschreiber):
            setattr(sys, name, Stempelschreiber(kanal))
