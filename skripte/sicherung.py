"""Tagessicherung der Zustandsdatei - die 27+ Noten liegen sonst nur hier.

WARUM (Review 09.10.2026, betrieb#6).  Die Bewertungen sind die einzige
Messgroesse des Projekts, die sich nicht nachproduzieren laesst, und sie
stehen allein in `daten/zustand.json` - gitignoriert, ohne eigene Kopie.
Das Time-Machine-Netzziel hatte seinen letzten Snapshot am 29.05.2026
("Failed to mount destination"); die Noten vom 04. bis 06.10. waren in
keiner Sicherung.

WAS HIER PASSIERT.  Einmal je Kalendertag (Ortszeit) liegt eine Kopie in
`daten/sicherung/zustand-JJJJ-MM-TT.json`.  Ist der Zustand im Laufe des
Tages gewachsen (neue Note), wird DIE Datei des Tages ueberschrieben - sie
traegt also immer den letzten Stand des Tages, nicht den von 00:00.  Es bleiben die
letzten 14 Tageskopien.  Ist `sicherung_ordner` in
konfig.json gesetzt (etwa ein iCloud-Pfad), geschieht dasselbe zusaetzlich
dort.

VIER WAECHTER.
* Eine Zustandsdatei, die kein gueltiges JSON ist, wird NICHT kopiert: sonst
  ueberschriebe der naechste Lauf die letzte gute Tageskopie mit Muell.
* Geschrieben wird atomar (Temp-Datei, os.replace): eine abgebrochene Kopie
  hinterlaesst nie eine halbe Sicherung.
* Geloescht wird nur, was GENAU dem Namensmuster entspricht und aelter als
  die Frist ist - ein Ordner, in dem noch anderes liegt, bleibt heil.
* Der Zusatzordner wird nur selbst angelegt, nie samt Eltern: ein vertippter
  Pfad oder ein nicht eingehaengtes iCloud-Laufwerk ist ein Fehler, kein
  Anlass fuer einen neuen Verzeichnisbaum.

Ein Fehler im Zusatzordner (iCloud nicht eingehaengt, Platte voll) darf die
lokale Sicherung nicht verhindern und umgekehrt; gemeldet wird er trotzdem
(Rueckgabe, Aufrufer setzt den Exitcode).

Nur Standardbibliothek.
"""
import json
import os
import re
import tempfile
from datetime import date, datetime, timedelta

BEHALTEN_TAGE = 14
MUSTER = re.compile(r"^zustand-(\d{4})-(\d{2})-(\d{2})\.json$")


def _name(tag):
    return "zustand-%s.json" % tag.isoformat()


def _kopiere_atomar(quelle_bytes, ziel):
    """Bytes unter `ziel` ablegen: erst Temp-Datei im selben Ordner, dann replace."""
    ordner = os.path.dirname(ziel)
    fd, tmp = tempfile.mkstemp(prefix=".zustand-", suffix=".tmp", dir=ordner)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(quelle_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, ziel)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _raeume(ordner, heute, behalten=BEHALTEN_TAGE):
    """Nur die letzten `behalten` Tageskopien bleiben (heute eingerechnet).

    -> Anzahl der geloeschten.
    """
    n = 0
    grenze = heute - timedelta(days=behalten - 1)
    for name in os.listdir(ordner):
        m = MUSTER.match(name)
        if not m:
            continue
        try:
            tag = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        if tag < grenze:
            os.unlink(os.path.join(ordner, name))
            n += 1
    return n


def _in_ordner(inhalt, ordner, heute, nur_letzte_ebene=False):
    """Tageskopie in `ordner` aktualisieren und alte raeumen.

    -> "neu" (geschrieben), "gleich" (stand schon so da).

    `nur_letzte_ebene`: nur den Ordner selbst anlegen, nie seine Eltern.  Fuer
    den Zusatzordner aus der Konfiguration: ein vertippter Pfad oder ein nicht
    eingehaengtes Laufwerk soll als Fehler auffallen, nicht stillschweigend
    einen neuen Verzeichnisbaum anlegen, der nie jemand sichert.
    """
    if nur_letzte_ebene:
        eltern = os.path.dirname(os.path.abspath(ordner))
        if not os.path.isdir(eltern):
            raise FileNotFoundError("%s existiert nicht" % eltern)
    os.makedirs(ordner, exist_ok=True)
    ziel = os.path.join(ordner, _name(heute))
    status = "neu"
    try:
        with open(ziel, "rb") as f:
            if f.read() == inhalt:
                status = "gleich"
    except OSError:
        pass
    if status == "neu":
        _kopiere_atomar(inhalt, ziel)
    _raeume(ordner, heute)
    return status


def sichere(zustand_pfad, lokal, zusatz=None, heute=None):
    """Zustandsdatei in `lokal` (und `zusatz`) sichern.

    Rueckgabe: Liste der Fehler (leer = alles gut).  Wirft nicht: der
    Aufrufer (ein Agent, der eigentlich etwas anderes tut) entscheidet.
    """
    heute = heute or datetime.now().date()
    try:
        with open(zustand_pfad, "rb") as f:
            inhalt = f.read()
        json.loads(inhalt.decode("utf-8"))
    except FileNotFoundError:
        return ["Sicherung: %s fehlt" % zustand_pfad]
    except (OSError, ValueError) as ex:
        return ["Sicherung: %s nicht lesbar/ungueltig (%s: %s) - die letzte "
                "gute Kopie bleibt stehen"
                % (zustand_pfad, type(ex).__name__, ex)]
    fehler = []
    for ordner in [lokal] + ([zusatz] if zusatz else []):
        try:
            status = _in_ordner(inhalt, ordner, heute,
                                nur_letzte_ebene=(ordner == zusatz))
            if status == "neu":
                print("   Sicherung: %s" % os.path.join(ordner, _name(heute)))
        except OSError as ex:
            fehler.append("Sicherung nach %s fehlgeschlagen (%s: %s)"
                          % (ordner, type(ex).__name__, ex))
    return fehler


def aus_konfig(konfig_pfad):
    """Optionaler Zusatzordner `sicherung_ordner` (None, wenn nicht gesetzt)."""
    try:
        with open(konfig_pfad, encoding="utf-8") as f:
            wert = json.load(f).get("sicherung_ordner")
    except (OSError, ValueError):
        return None
    return os.path.expanduser(wert) if wert else None
