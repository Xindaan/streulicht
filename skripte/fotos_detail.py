"""Erweiterte Extraktion: Favoriten und Minutenabstand zum Sonnenuntergang.

WARUM das noetig wurde (14.08.2026):
Der einfache Presence-Only-Test ist an einem KONFUNDIERTEN Label gescheitert.
An Fotoabenden ist Term B (freier Westhorizont) signifikant erhoeht (+0.068,
z = +2.77) und Term A (hohe Wolken) erniedrigt (-0.041, z = -1.76) - weil
"draussen sein" mit schoenem, also klarem Wetter korreliert und damit gegen
den Schirmterm laeuft.  Im Produkt heben sich beide auf (z = +0.57).

Das Label misst also "war draussen", nicht "hat einen Sonnenuntergang
fotografiert".  Der Ausweg ist ein Vergleich INNERHALB der Draussen-Abende:
Absichtsvolle Sonnenuntergangsaufnahmen gegen beilaeufige.  Dafuer braucht es
ein Absichtssignal, und die Mediathek hat zwei brauchbare:

  Albumzugehoerigkeit  das mit Abstand staerkste Signal - eine von Hand
                       kuratierte Auswahl schlaegt jede Heuristik.  Gemessen
                       14.08.2026: unkuratierte Fotoabende ergeben Mittelrang
                       0.510 (nichts), eine kuratierte Liste 0.677 (p = 0.04).
  ZFAVORITE            als Favorit markiert - traegt gemessen KEIN Signal
                       (z = -0.03); Favoriten sind gute Fotos von irgendwas.
  Minutenabstand       Aufnahmen dicht am Sonnenuntergang statt irgendwann
                       im Fenster

MUSS AUS Terminal.app LAUFEN.  Aus Claude Code heraus liest ein eingebettetes
Bundle (com.anthropic.claude-code) ohne Festplattenvollzugriff.

Gelesen werden weiterhin NUR Zeitstempel, Koordinaten und das Favoritenflag -
keine Dateinamen, keine Inhalte, keine Beschreibungen, keine Albennamen.
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import sonnenuntergang  # noqa: E402

CORE_DATA_EPOCHE = datetime(2001, 1, 1, tzinfo=timezone.utc)
FENSTER_MIN = 45
BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def finde_datenbank():
    basis = os.path.expanduser("~/Pictures")
    for name in sorted(os.listdir(basis)):
        if name.endswith(".photoslibrary"):
            p = os.path.join(basis, name, "database", "Photos.sqlite")
            if os.path.exists(p):
                return p
    return None


def oeffne(pfad):
    try:
        con = sqlite3.connect("file:%s?mode=ro" % pfad, uri=True)
        con.execute("select count(*) from ZASSET").fetchone()
        return con, None
    except sqlite3.Error:
        tmp = tempfile.mkdtemp()
        try:
            for e in ("", "-wal", "-shm"):
                if os.path.exists(pfad + e):
                    shutil.copy2(pfad + e, os.path.join(tmp, "Photos.sqlite" + e))
        except PermissionError:
            shutil.rmtree(tmp, ignore_errors=True)
            raise SystemExit(
                "Kein Zugriff auf die Mediathek.  Dieses Skript MUSS aus\n"
                "Terminal.app laufen - aus Claude Code heraus liest ein\n"
                "eingebettetes Bundle ohne Festplattenvollzugriff.")
        return sqlite3.connect(os.path.join(tmp, "Photos.sqlite")), tmp


def main():
    pfad = finde_datenbank()
    if not pfad:
        raise SystemExit("Keine Photos.sqlite gefunden")
    con, tmp = oeffne(pfad)
    spalten = {r[1] for r in con.execute("pragma table_info(ZASSET)")}
    dat = "ZDATECREATED" if "ZDATECREATED" in spalten else "ZSORTDATECREATED"
    fav = "ZFAVORITE" if "ZFAVORITE" in spalten else None
    print("Spalten: Datum=%s  Favorit=%s" % (dat, fav or "(nicht vorhanden)"))

    # Albumzugehoerigkeit: Z_xxASSETS verknuepft Alben (ZGENERICALBUM) mit
    # Assets. Die Spaltennamen tragen eine wechselnde Zahl, deshalb dynamisch
    # suchen statt raten.
    alben = {}
    try:
        tabellen = [r[0] for r in con.execute(
            "select name from sqlite_master where type='table' "
            "and name like 'Z_%ASSETS'")]
        for tab in tabellen:
            sp = [r[1] for r in con.execute("pragma table_info(%s)" % tab)]
            aspalte = next((c for c in sp if c.endswith("ASSETS")), None)
            bspalte = next((c for c in sp if c.endswith("ALBUMS")), None)
            if not aspalte or not bspalte:
                continue
            for aid, titel in con.execute(
                    "select t.%s, g.ZTITLE from %s t join ZGENERICALBUM g "
                    "on g.Z_PK = t.%s where g.ZTITLE is not null"
                    % (aspalte, tab, bspalte)):
                alben.setdefault(aid, set()).add(titel)
    except sqlite3.Error as e:
        print("   (Alben nicht lesbar: %s)" % e)
    if alben:
        namen = sorted({t for v in alben.values() for t in v})
        print("Alben gefunden: %d  (%s%s)"
              % (len(namen), ", ".join(namen[:6]), " ..." if len(namen) > 6 else ""))

    q = ("select Z_PK, %s, ZLATITUDE, ZLONGITUDE%s from ZASSET "
         "where ZLATITUDE is not null and ZLATITUDE > -90 and ZLATITUDE < 90 "
         "and %s is not null" % (dat, (", " + fav) if fav else "", dat))

    abende = {}
    gesamt = 0
    for zeile in con.execute(q):
        pk, ts, lat, lon = zeile[0], zeile[1], zeile[2], zeile[3]
        favorit = bool(zeile[4]) if fav else False
        meine_alben = alben.get(pk, set())
        gesamt += 1
        wann = CORE_DATA_EPOCHE + timedelta(seconds=float(ts))
        h, _ = sonnenuntergang(wann.date(), lat, lon)
        if h is None:
            continue
        su = wann.replace(hour=0, minute=0, second=0, microsecond=0) \
            + timedelta(hours=h)
        dmin = (wann - su).total_seconds() / 60.0
        if abs(dmin) > FENSTER_MIN:
            continue
        k = (str(wann.date()), round(lat, 1), round(lon, 1))
        e = abende.setdefault(k, {"n": 0, "favoriten": 0, "min_abstand": 999.0,
                                  "abstaende": [], "alben": set()})
        e["n"] += 1
        e["favoriten"] += 1 if favorit else 0
        e["alben"] |= meine_alben
        e["min_abstand"] = min(e["min_abstand"], abs(dmin))
        e["abstaende"].append(round(dmin, 1))
    con.close()
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)

    print("geotaggte Fotos gesamt: %d" % gesamt)
    print("Abende im Fenster SU +/- %d min: %d" % (FENSTER_MIN, len(abende)))
    mitfav = sum(1 for v in abende.values() if v["favoriten"] > 0)
    print("davon mit mindestens einem Favoriten: %d" % mitfav)
    inalbum = {}
    for v in abende.values():
        for t in v["alben"]:
            inalbum[t] = inalbum.get(t, 0) + 1
    if inalbum:
        print("Abende je Album (nur Alben mit >= 3 Abenden im SU-Fenster):")
        for t, k in sorted(inalbum.items(), key=lambda x: -x[1]):
            if k >= 3:
                print("   %-34s %d" % (t[:34], k))

    ziel = os.path.join(BASIS, "daten", "foto_detail.json")
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    with open(ziel, "w") as f:
        json.dump([{"tag": k[0], "lat": k[1], "lon": k[2],
                    "n": v["n"], "favoriten": v["favoriten"],
                    "min_abstand": v["min_abstand"],
                    "alben": sorted(v["alben"]),
                    "abstaende": sorted(v["abstaende"])}
                   for k, v in sorted(abende.items())], f)
    print("geschrieben: %s" % ziel)


if __name__ == "__main__":
    main()
