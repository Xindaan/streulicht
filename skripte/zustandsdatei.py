"""Atomar schreiben - damit ein abgebrochener Lauf nicht alles stilllegt.

WARUM (22.08.2026, externer Review Befund 2, T-0051).  Drei Agenten haben
`daten/zustand.json` mit `open(pfad, "w")` + `json.dump` ueberschrieben.
Zwischen dem Truncate durch `"w"` und dem letzten Byte des Dumps liegt ein
Fenster, in dem die Datei unvollstaendig auf der Platte steht.  Stirbt der
Prozess dort - Strom, Ruhezustand, OOM, `kill` -, bleibt sie so liegen.

Der Schaden ist nicht lokal.  SIEBEN Leser laden diese Datei mit blankem
`json.load`: alarm, bewertungen_holen, erinnerung, seite (zweimal), bisher,
faecher, bewertungsseite.  Vier launchd-Agenten haengen daran.  Eine halbe
Datei heisst deshalb nicht "ein Lauf faellt aus", sondern: kein Alarm, keine
Erinnerung, keine Bewertungsabholung, keine Seitenaktualisierung - und jede
Instanz stirbt beim naechsten Start sofort wieder, bis jemand von Hand
repariert.  Genau der stille Gesamtausfall, gegen den das Projekt sonst
ueberall gebaut ist.

`os.replace` ist auf POSIX atomar: der Leser sieht entweder den alten oder
den neuen Inhalt, nie einen halben.  Deshalb bleibt die Leserseite
unveraendert - sie braucht keine Sonderbehandlung, wenn niemand mehr einen
halben Puffer hinterlaesst.

`fsync` auf Datei UND Verzeichnis: ohne das erste kann der Inhalt nach einem
Stromausfall fehlen, obwohl der Name schon da ist; ohne das zweite kann der
Verzeichniseintrag fehlen, obwohl der Inhalt geschrieben ist.
"""
import fcntl
import json
import os
from contextlib import contextmanager


def schreibe(pfad, daten, indent=1, separators=None):
    """`daten` als JSON nach `pfad` - ganz oder gar nicht.

    `indent`/`separators` werden an `json.dump` durchgereicht: die
    Zustandsdatei will `indent=1` (lesbar im Diff), Archiv und Klimatologie
    wollen es kompakt.  Ohne das Durchreichen waere das Tagesarchiv rund
    15 % groesser geworden - eine stille Regression durch einen Fix.
    """
    os.makedirs(os.path.dirname(pfad) or ".", exist_ok=True)
    ordner = os.path.dirname(os.path.abspath(pfad))
    # Die temporaere Datei MUSS im selben Verzeichnis liegen: os.replace ist
    # nur innerhalb eines Dateisystems atomar, ueber Grenzen hinweg faellt es
    # auf Kopieren zurueck - und dann ist das Fenster wieder da.
    tmp = os.path.join(ordner, ".%s.tmp" % os.path.basename(pfad))
    try:
        with open(tmp, "w") as f:
            json.dump(daten, f, indent=indent, separators=separators)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, pfad)
        d = os.open(ordner, os.O_RDONLY)
        try:
            os.fsync(d)
        finally:
            os.close(d)
    except BaseException:
        # Auch bei KeyboardInterrupt und SystemExit: eine liegengebliebene
        # .tmp waere kein Schaden, aber Muell, den niemand mehr zuordnet.
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass
        raise


@contextmanager
def gesperrt(pfad):
    """Exklusive Sperre auf `pfad` - fuer Lesen UND Schreiben zusammen.

    WARUM (23.08.2026, T-0058).  Drei Agenten machen dasselbe: Datei lesen,
    den eigenen Ausschnitt aendern, alles zurueckschreiben.  Ueberlappen zwei,
    gewinnt der langsamere - und die Aenderung des anderen ist weg, lautlos.
    Nachgestellt: der Bewertungsabruf traegt eine Note ein, waehrend der
    Alarmlauf rechnet; der Alarmlauf schreibt danach seinen (aelteren) Stand
    und die Note ist verschwunden.

    `os.replace` (siehe schreibe()) schuetzt davor NICHT.  Es garantiert, dass
    kein Leser eine halbe Datei sieht - nicht, dass zwischen Lesen und
    Schreiben niemand dazwischenkommt.  Das sind zwei verschiedene Probleme,
    und sie brauchen zwei verschiedene Mittel.

    Die Sperre sitzt auf einer eigenen `.lock`-Datei, nicht auf der
    Zustandsdatei selbst: `os.replace` ersetzt die Datei durch eine ANDERE,
    ein Lock auf ihrem alten Inode wuerde damit ins Leere zeigen.  Die
    Lockdatei bleibt liegen und ist leer - sie traegt keinen Inhalt, nur den
    Namen.

    `flock` ist beratend, kein Zwang: es wirkt nur zwischen Prozessen, die es
    auch benutzen.  Wer die Datei ohne Sperre schreibt, kommt weiterhin durch.
    Deshalb gehoert `aktualisiere()` in JEDEN Schreiber, nicht in manche.
    """
    ordner = os.path.dirname(os.path.abspath(pfad))
    os.makedirs(ordner or ".", exist_ok=True)
    sperre = os.path.join(ordner, ".%s.lock" % os.path.basename(pfad))
    fd = os.open(sperre, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def lade(pfad, vorgabe=None):
    """Zustandsdatei lesen; fehlt sie, die Vorgabe (Standard: leeres dict)."""
    if not os.path.exists(pfad):
        return {} if vorgabe is None else vorgabe
    with open(pfad) as f:
        return json.load(f)


def aktualisiere(pfad, aendern, indent=1, separators=None):
    """Unter Sperre: frisch laden, `aendern(zustand)` anwenden, atomar schreiben.

    Der Punkt ist das FRISCH: `aendern` bekommt den Stand von JETZT, nicht den,
    den der Aufrufer vor seiner Rechnung gelesen hat.  Wer minutenlang rechnet
    (der Alarmlauf), muss seine Ergebnisse deshalb im Callback einmergen und
    darf sie nicht vorher in den alten Zustand geschrieben haben.

    Rueckgabe: der geschriebene Zustand - fuer Aufrufer, die danach noch
    daraus berichten wollen.
    """
    with gesperrt(pfad):
        zustand = lade(pfad)
        aendern(zustand)
        schreibe(pfad, zustand, indent, separators)
    return zustand
