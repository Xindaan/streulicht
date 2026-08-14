"""Gate: wie viele geotaggte Abendfotos liegen in der Fotomediathek?

Liest NUR (Zeitstempel, Breite, Laenge) - keine Dateinamen, keine Inhalte, keine
Beschreibungen.  Ergebnis ist der Presence-Only-Datensatz aus E0: ein Abend, an
dem fotografiert wurde, ist ein positives Label.

Abbruchschwelle laut E0:  n >= 40 komfortabel, n >= 20 grenzwertig, darunter
faellt der Test aus.
"""
import os
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import sonnenuntergang  # noqa: E402

CORE_DATA_EPOCHE = datetime(2001, 1, 1, tzinfo=timezone.utc)
FENSTER_MIN = 30  # +/- um den Sonnenuntergang


def finde_datenbank():
    basis = os.path.expanduser("~/Pictures")
    for name in sorted(os.listdir(basis)):
        if name.endswith(".photoslibrary"):
            p = os.path.join(basis, name, "database", "Photos.sqlite")
            if os.path.exists(p):
                return p
    return None


def oeffne(pfad):
    """Read-only. Faellt auf eine Kopie zurueck, wenn WAL-Sperren stoeren."""
    try:
        con = sqlite3.connect("file:%s?mode=ro" % pfad, uri=True)
        con.execute("select count(*) from ZASSET").fetchone()
        return con, None
    except sqlite3.Error:
        tmp = tempfile.mkdtemp()
        try:
            for endung in ("", "-wal", "-shm"):
                if os.path.exists(pfad + endung):
                    shutil.copy2(pfad + endung,
                                 os.path.join(tmp, "Photos.sqlite" + endung))
        except PermissionError:
            shutil.rmtree(tmp, ignore_errors=True)
            raise SystemExit(
                "Kein Zugriff auf die Fotomediathek (macOS-Datenschutz, TCC).\n"
                "Systemeinstellungen > Datenschutz & Sicherheit > Festplattenvollzugriff\n"
                "-> die Terminal-App (bzw. Claude Code) eintragen und aktivieren,\n"
                "danach die App neu starten und dieses Skript erneut laufen lassen.")
        return sqlite3.connect(os.path.join(tmp, "Photos.sqlite")), tmp


def hole_punkte(con):
    spalten = {r[1] for r in con.execute("pragma table_info(ZASSET)")}
    dat = "ZDATECREATED" if "ZDATECREATED" in spalten else "ZSORTDATECREATED"
    if "ZLATITUDE" not in spalten:
        raise SystemExit("ZASSET hat keine ZLATITUDE - unerwartetes Schema")
    q = ("select %s, ZLATITUDE, ZLONGITUDE from ZASSET "
         "where ZLATITUDE is not null and ZLATITUDE > -90 and ZLATITUDE < 90 "
         "and %s is not null" % (dat, dat))
    for ts, lat, lon in con.execute(q):
        yield CORE_DATA_EPOCHE + timedelta(seconds=float(ts)), float(lat), float(lon)


def main():
    pfad = finde_datenbank()
    if not pfad:
        raise SystemExit("Keine Photos.sqlite gefunden")
    print("Mediathek: %s" % pfad)
    try:
        con, tmp = oeffne(pfad)
    except sqlite3.OperationalError as e:
        raise SystemExit("Kein Zugriff (%s).  Terminal braucht 'Festplattenvollzugriff' "
                         "in den Systemeinstellungen." % e)

    gesamt = geotaggt = 0
    treffer = []
    for wann, lat, lon in hole_punkte(con):
        gesamt += 1
        geotaggt += 1
        h, _ = sonnenuntergang(wann.date(), lat, lon)
        if h is None:
            continue
        su = wann.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=h)
        if abs((wann - su).total_seconds()) <= FENSTER_MIN * 60:
            treffer.append((wann, lat, lon))
    con.close()
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)

    print("geotaggte Fotos gesamt: %d" % geotaggt)
    print("im Fenster SU +/- %d min: %d Fotos" % (FENSTER_MIN, len(treffer)))

    abende = {}
    for wann, lat, lon in treffer:
        abende.setdefault((wann.date(), round(lat, 1), round(lon, 1)), 0)
        abende[(wann.date(), round(lat, 1), round(lon, 1))] += 1
    print("eindeutige (Abend, Ort)-Paare: %d" % len(abende))

    berlin = {k: v for k, v in abende.items() if 52.2 <= k[1] <= 52.8 and 13.0 <= k[2] <= 13.9}
    print("davon Raum Berlin: %d Abende" % len(berlin))
    print()
    print("Jahresverteilung (alle Orte):")
    for jahr, n in sorted(Counter(k[0].year for k in abende).items()):
        nb = sum(1 for k in berlin if k[0].year == jahr)
        print("   %d: %3d Abende  (Berlin %d)" % (jahr, n, nb))
    print()
    print("Monatsverteilung Berlin (Saisonbias sichtbar machen):")
    mc = Counter(k[0].month for k in berlin)
    print("   " + "  ".join("%02d:%d" % (m, mc.get(m, 0)) for m in range(1, 13)))


if __name__ == "__main__":
    main()
