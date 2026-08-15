"""T-0019: die Wolkenmaske von MSG als Beobachtungswahrheit.

DIE FRAGE, DIE NUR SIE BEANTWORTET.  Die Bewertungen sagen, WIE OFT der Score
trifft.  Sie sagen nicht, WARUM er verfehlt - dafuer braeuchte es die
Trennung zwischen "das Modell hatte die Wolke nicht" und "das Modell hatte sie,
der Score hat sie falsch gewichtet".  Am 14.08. habe ich das fuenfmal von Hand
am Foto entschieden.  Die Satellitenmaske entscheidet es fuer jeden Abend seit
2004.

WAS DAS PRODUKT IST.  `EO:EUM:DAT:MSG:CLM`, die operationelle Wolkenmaske aus
SEVIRI, alle 15 Minuten, volle Scheibe, 3712 x 3712 Punkte, rund 3 km ueber
Mitteleuropa.  Vier Klassen: 0 klar ueber Wasser, 1 klar ueber Land, 2 Wolke,
3 nicht bestimmbar.  Die 3 ist nicht selten (rund 30 % der Scheibe, vor allem
in der Daemmerung und an den Raendern) und wird als FEHLEND behandelt, nicht
als "keine Wolke" - sonst waere es dieselbe Fehlerklasse wie viermal zuvor.

KOSTEN.  0 EUR.  Meteosat-Daten ab einer Stunde Latenz sind ohne Gebuehr fuer
jede Nutzung freigegeben; wir fragen ausschliesslich Vergangenes ab.

ZUGANG.  Consumer Key und Secret aus konfig_geheim.json (gitignoriert).
Kein `eumdac` noetig - die API ist gewoehnliches HTTP, und der GRIB2-Leser
steht in sonnen/grib2.py.

WARUM NICHT DER ALARM DAVON PROFITIERT.  Die Maske ist Beobachtung, keine
Vorhersage.  Sie taugt zur Validierung und nur dazu.
"""
import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import sonnenuntergang, zielpunkt  # noqa: E402
from sonnen.grib2 import werte, wert_bei  # noqa: E402
from sonnen.score import DISTANZEN_KM, FAECHER_AZIMUTE  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(BASIS, "daten", "satellit")
KOLLEKTION = "EO:EUM:DAT:MSG:CLM"
API = "https://api.eumetsat.int"
KLAR_WASSER, KLAR_LAND, WOLKE, UNBESTIMMT = 0, 1, 2, 3

_token = {"wert": None, "bis": 0.0}


def token():
    """Zugangstoken, rund 50 min gueltig; wird bei Bedarf erneuert."""
    if _token["wert"] and time.time() < _token["bis"] - 120:
        return _token["wert"]
    p = os.path.join(BASIS, "konfig_geheim.json")
    if not os.path.exists(p):
        raise SystemExit(
            "konfig_geheim.json fehlt.  Anlegen mit:\n"
            '  {"eumetsat": {"consumer_key": "...", "consumer_secret": "..."}}\n'
            "Schluessel holen unter https://api.eumetsat.int/api-key/")
    with open(p) as f:
        g = json.load(f)["eumetsat"]
    auth = base64.b64encode(
        ("%s:%s" % (g["consumer_key"], g["consumer_secret"])).encode()).decode()
    r = urllib.request.Request(
        API + "/token",
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        headers={"Authorization": "Basic %s" % auth,
                 "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(r, timeout=60) as f:
        d = json.load(f)
    _token["wert"] = d["access_token"]
    _token["bis"] = time.time() + float(d.get("expires_in", 3000))
    return _token["wert"]


def _hol(u, roh=False, versuche=4):
    for n in range(versuche):
        r = urllib.request.Request(u, headers={"Authorization": "Bearer %s" % token()})
        try:
            with urllib.request.urlopen(r, timeout=300) as f:
                return f.read() if roh else json.load(f)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403) and n < versuche - 1:
                _token["wert"] = None      # Token abgelaufen, einmal erneuern
                continue
            if e.code in (429, 500, 502, 503) and n < versuche - 1:
                time.sleep(5 * (n + 1))
                continue
            raise
    raise SystemExit("unerreichbar: %s" % u)


def naechstes_produkt(zeitpunkt, fenster_min=40):
    """Produktkennung, die dem Zeitpunkt am naechsten liegt, oder None."""
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


def maske(produkt):
    """Wertefeld und Gitter zu einer Produktkennung.  Gecacht als ZIP."""
    p = os.path.join(CACHE, produkt + ".zip")
    if not os.path.exists(p):
        u = ("%s/data/download/1.0.0/collections/%s/products/%s"
             % (API, urllib.parse.quote(KOLLEKTION, safe=""),
                urllib.parse.quote(produkt, safe="")))
        roh = _hol(u, roh=True)
        os.makedirs(CACHE, exist_ok=True)
        with open(p, "wb") as f:
            f.write(roh)
    with open(p, "rb") as f:
        z = zipfile.ZipFile(io.BytesIO(f.read()))
    name = [n for n in z.namelist() if n.endswith(".grb")][0]
    return werte(z.read(name))


def faecher_anteil(feld, gp, tag, breite, laenge, nur_nahbereich=None):
    """Wolkenanteil ueber den Faecherpunkten.  (Anteil, Deckung)

    Unbestimmte Pixel zaehlen NICHT als wolkenfrei, sondern gar nicht - der
    Nenner schrumpft.  Die zurueckgegebene Deckung sagt, wie viel des Faechers
    ueberhaupt entschieden werden konnte; unter etwa 0.6 ist der Anteil
    Rauschen.
    """
    _, azimut = sonnenuntergang(tag, breite, laenge)
    wolke = gesamt = 0
    for dv in FAECHER_AZIMUTE:
        for d in DISTANZEN_KM:
            if d == 0.0 and dv != 0.0:
                continue
            if nur_nahbereich is not None and d > nur_nahbereich:
                continue
            la, lo = ((breite, laenge) if d == 0.0
                      else zielpunkt(breite, laenge, azimut + dv, d))
            v = wert_bei(feld, gp, la, lo)
            if v is None or int(v) == UNBESTIMMT:
                continue
            gesamt += 1
            wolke += 1 if int(v) == WOLKE else 0
    if gesamt == 0:
        return None, 0.0
    n_moeglich = (len(FAECHER_AZIMUTE) *
                  len([d for d in DISTANZEN_KM
                       if nur_nahbereich is None or d <= nur_nahbereich]) -
                  (len(FAECHER_AZIMUTE) - 1))
    return wolke / gesamt, gesamt / n_moeglich


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tage", nargs="*", help="ISO-Daten; leer = die Problemabende")
    ap.add_argument("--breite", type=float, default=52.52)
    ap.add_argument("--laenge", type=float, default=13.405)
    a = ap.parse_args()

    tage = a.tage or ["2022-09-20", "2023-04-24", "2024-05-03",
                      "2024-09-15", "2025-09-15"]
    with open(os.path.join(BASIS, "daten",
                           "score_berlin_g0.5_2015_2025.json")) as f:
        klima = json.load(f)
    with open(os.path.join(BASIS, "daten", "bewertung_andre.json")) as f:
        noten = json.load(f)

    print("%-12s %4s %8s %8s %8s   %s"
          % ("Abend", "Note", "Modell", "Satellit", "Deckung", "Abstand"))
    aus = {}
    for t in tage:
        d = date.fromisoformat(t)
        std, _ = sonnenuntergang(d, a.breite, a.laenge)
        if std is None:
            continue
        ziel = (datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
                + timedelta(hours=std))
        pid, abstand = naechstes_produkt(ziel)
        if pid is None:
            print("%-12s  kein Produkt im Fenster" % t)
            continue
        feld, gp = maske(pid)
        anteil, deckung = faecher_anteil(feld, gp, d, a.breite, a.laenge)
        modell = klima.get(t, {}).get("A")
        aus[t] = {"satellit": anteil, "deckung": deckung, "modell": modell,
                  "produkt": pid}
        print("%-12s %4s %8s %8s %7.0f %%   %+.0f min"
              % (t, noten.get(t, "-"),
                 "%.2f" % modell if modell is not None else "-",
                 "%.2f" % anteil if anteil is not None else "-",
                 100 * deckung, abstand))

    p = os.path.join(BASIS, "daten", "satellit_vergleich.json")
    with open(p, "w") as f:
        json.dump(aus, f, indent=1)
    print("\ngeschrieben: %s" % os.path.relpath(p, BASIS))


if __name__ == "__main__":
    main()
