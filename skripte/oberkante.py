"""T-0028: sitzt die Wolke am Toeter-Segment ueber oder unter dem Strahl?

DIE FRAGE.  Befund 35 hat gezeigt, dass die Wolken auf dem Lichtweg WIRKLICH
da waren - kein Phantom.  Damit blieben zwei Erklaerungen fuer die toten
Fenster uebrig, und die Wolkenmaske kann sie nicht trennen, weil sie nur
"Wolke ja/nein" kennt:

    (a) Der TERM ist zu hart: vier Segmente mit 66-91 % ergeben als
        unabhaengiges Produkt 0.001 (T-0029).
    (b) Die HOEHE stimmt nicht: das Modell steckt die Wolke in die falsche
        Schicht, oder sie liegt schlicht unter dem Strahl.

ERGEBNIS VORWEG, WEIL ES DEN ZWECK DIESES SKRIPTS AENDERT (15.08.2026):

**Die Wolkenoberkante ist fuer diese Frage das falsche Instrument.**  Der
Gedanke war: liegt die Oberkante UNTER der Strahlhoehe, kann die Wolke nicht
blockieren.  Einseitig sauber - aber praktisch machtlos, und zwar aus der
Geometrie heraus:

    Der Strahl laeuft an den Toeter-Segmenten bei 0.00 bis 1.54 km.  Nahe
    dem Tangentenpunkt IST er bodennah.  Damit liegt praktisch jede
    Wolkenoberkante ueber ihm - gemessen 0 von 48 darunter.

Das ist kein Freispruch fuer den Term, sondern eine Blindheit des Tests.

Schlimmer: CTH liefert je Pixel nur die OBERSTE Wolke.  An den Toeter-
Segmenten sind das 3-11 km, also mittlere und hohe Schichten.  Blockiert wird
laut Modell aber die TIEFE Decke darunter (47 von 48 Segmenten fragen die
Schicht "low" ab, was bei Strahlhoehe 0-1.5 km richtig ist).  Ob unter dem
gemessenen hohen Deckel noch eine tiefe Decke sitzt, sagt CTH prinzipiell
nicht - "nur hohe Wolke" und "hohe ueber tiefer" sehen im Produkt gleich aus.

WAS ES STATTDESSEN BRAUCHT: Wolkenunterkante, oder ein Wolkentyp-Produkt,
das low/mid/high trennt.  Das Skript bleibt, weil es die Strahlgeometrie und
die Schichtzuordnung belegt - beides war vorher nur behauptet.

PRODUKT.  `EO:EUM:DAT:MSG:CTH`, Wolkenoberkantenhoehe aus SEVIRI, alle
15 min, 1237 x 1237 Punkte (rund 9 km ueber Mitteleuropa).  Kosten 0 EUR.
Wolkenfreie Punkte tragen keinen Wert (Bitmap) und sind hier NaN - nicht 0,
das waere "Oberkante auf Meereshoehe".

STRAHLHOEHE.  z(d) = (D - d)^2 / (2 R_eff) mit D = Tangentendistanz des
Schirmniveaus.  Der Strahl laeuft vom Tangentenpunkt zum Schirm; nahe der
Tangente ist er bodennah, beim Schirm auf Schirmhoehe.
"""
import argparse
import io
import json
import os
import sys
import urllib.parse
import zipfile
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sonnen.geometrie import (sonnenuntergang, strahlhoehe_km,
                              tangentendistanz_km, zielpunkt)  # noqa: E402
from sonnen.grib2 import werte, wert_bei  # noqa: E402
from sonnen.score import FAECHER_AZIMUTE, SCHIRME  # noqa: E402
from satellit import API, CACHE, _hol  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOLLEKTION = "EO:EUM:DAT:MSG:CTH"


def naechstes_cth(zeitpunkt, fenster_min=40):
    von = zeitpunkt - timedelta(minutes=fenster_min)
    bis = zeitpunkt + timedelta(minutes=fenster_min)
    q = urllib.parse.urlencode({
        "format": "json", "pi": KOLLEKTION,
        "dtstart": von.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dtend": bis.strftime("%Y-%m-%dT%H:%M:%SZ")})
    d = _hol(API + "/data/search-products/1.0.0/os?" + q)
    best, bestd = None, None
    for f in d.get("features", []):
        s = (f.get("properties", {}).get("date") or "").split("/")[0]
        try:
            t = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            continue
        dt = abs((t - zeitpunkt).total_seconds())
        if bestd is None or dt < bestd:
            best, bestd = f["id"], dt
    return best, (bestd / 60.0 if bestd is not None else None)


def hoehenfeld(produkt):
    """Wolkenoberkante in km ueber Grund, NaN wo wolkenfrei.  Gecacht."""
    p = os.path.join(CACHE, produkt + ".zip")
    if not os.path.exists(p):
        u = ("%s/data/download/1.0.0/collections/%s/products/%s"
             % (API, urllib.parse.quote(KOLLEKTION, safe=""),
                urllib.parse.quote(produkt, safe="")))
        os.makedirs(CACHE, exist_ok=True)
        with open(p, "wb") as f:
            f.write(_hol(u, roh=True))
    with open(p, "rb") as f:
        z = zipfile.ZipFile(io.BytesIO(f.read()))
    name = [n for n in z.namelist() if n.endswith(".grb")][0]
    feld, gp, _ = werte(z.read(name), 0)      # Feld 0 = Hoehe, Feld 1 = Status
    return feld / 1000.0, gp                  # Meter -> Kilometer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--breite", type=float, default=52.52)
    ap.add_argument("--laenge", type=float, default=13.405)
    ap.add_argument("--nur-cache", action="store_true")
    a = ap.parse_args()

    with open(os.path.join(BASIS, "daten", "fensterterm_satellit.json")) as f:
        fw = json.load(f)

    print("Toeter-Segmente: Wolkenoberkante gegen Strahlhoehe")
    print("Ein Segment gilt als Toeter, wenn das Modell dort >= 50 % blockt.\n")
    print("%-12s %-6s %6s %8s %8s %9s  %s"
          % ("Abend", "Segm", "Modell", "Strahl", "Oberk.", "Differenz", "Urteil"))

    zeilen, unter, ueber, ohne = [], 0, 0, 0
    for tag in sorted(fw):
        e = fw[tag]
        segm = e.get("segmente_modell") or []
        toeter = [s for s in segm if s[2] >= 0.5]
        if not toeter:
            continue
        d = date.fromisoformat(tag)
        std, azimut = sonnenuntergang(d, a.breite, a.laenge)
        ziel = (datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
                + timedelta(hours=std))
        pid, abstand = naechstes_cth(ziel)
        if pid is None:
            print("%-12s  kein CTH-Produkt im Fenster" % tag)
            continue
        p = os.path.join(CACHE, pid + ".zip")
        if a.nur_cache and not os.path.exists(p):
            print("%-12s  nicht im Cache (ohne --nur-cache wird geladen)" % tag)
            continue
        feld, gp = hoehenfeld(pid)

        # Schirmhoehe dieses Abends aus dem gespeicherten Detail
        hoehe = dict(SCHIRME)[e["schirm"]]
        d_tan = tangentendistanz_km(hoehe)

        for d_nah, d_fern, c in toeter:
            z = strahlhoehe_km(d_fern, d_tan)
            # Oberkanten ueber den Faecherazimuten dieses Rings
            werte_ok = []
            for dv in FAECHER_AZIMUTE:
                la, lo = zielpunkt(a.breite, a.laenge, azimut + dv, d_fern)
                v = wert_bei(feld, gp, la, lo)
                if v is not None and v == v:      # nicht NaN
                    werte_ok.append(v)
            if not werte_ok:
                ohne += 1
                urteil = "keine Oberkante (wolkenfrei laut CTH)"
                ok = float("nan")
            else:
                ok = max(werte_ok)                # die hoechste zaehlt
                if ok < z:
                    unter += 1
                    urteil = "UNTER dem Strahl - blockiert nicht"
                else:
                    ueber += 1
                    # BEWUSST nicht "Blockade moeglich": das klaenge nach
                    # Befund. Der Test ist hier schlicht blind.
                    urteil = "oberste Wolke ueber dem Strahl - unentscheidbar"
            print("%-12s %3.0f km %5.0f %% %7.2f km %7s %9s  %s"
                  % (tag, d_fern, 100 * c, z,
                     "%.2f km" % ok if ok == ok else "-",
                     "%+.2f km" % (ok - z) if ok == ok else "-", urteil))
            zeilen.append({"tag": tag, "d_km": d_fern, "modell": c,
                           "strahl_km": z, "oberkante_km": None if ok != ok else ok,
                           "produkt": pid, "abstand_min": abstand})

    gesamt = unter + ueber + ohne
    print()
    print("=== Bilanz ueber %d Toeter-Segmente" % gesamt)
    print("   Oberkante UNTER dem Strahl (Blockade geometrisch unmoeglich): %d" % unter)
    print("   Oberkante ueber dem Strahl (Blockade moeglich, nicht belegt): %d" % ueber)
    print("   CTH sieht dort gar keine Wolke:                               %d" % ohne)
    print()
    print("Der Test ist EINSEITIG: 'unter' widerlegt die Blockade, 'ueber'")
    print("beweist sie nicht - dafuer fehlt die Unterkante.")

    p = os.path.join(BASIS, "daten", "oberkante_toeter.json")
    with open(p, "w") as f:
        json.dump({"segmente": zeilen,
                   "bilanz": {"unter": unter, "ueber": ueber, "ohne": ohne}},
                  f, indent=1)
    print("\ngeschrieben: %s" % os.path.relpath(p, BASIS))


if __name__ == "__main__":
    main()
