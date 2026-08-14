"""Holt ICON-D2 (2.2 km) ueber den Faecher - fuer den Aufloesungstest.

WARUM (14.08.2026):
Abschnitt 25 von docs/befunde-e1.md hat die Saettigungshypothese widerlegt:
ueber Berlin allein traegt die Feuchtediagnostik deutlich mehr Wolke als das
Bedeckungsfeld, ueber den ganzen Faecher aber nicht.  Beide Darstellungen
DESSELBEN Modells verfehlen Andres beste Abende.  Offen blieb damit die
Frage, die eine Ebene tiefer liegt: liegt es an der AUFLOESUNG?  GFS und ERA5
rechnen auf 25-30 km und mitteln Strukturen weg, die genau das Ereignis sind -
eine Wolkenbank mit scharfer Westkante, ein Loch im Stratocumulus.

ICON-D2 rechnet auf 2.2 km und liefert Bewoelkung sowohl als drei Schichten
als auch auf neun Druckflaechen.  Damit sind ZWEI Faktoren trennbar, die
sonst vermischt waeren:

    (a) Aufloesung   ICON-D2 3-Schicht  gegen  ERA5 3-Schicht
    (b) Niveaus      ICON-D2 niveauaufgeloest  gegen  ICON-D2 3-Schicht

Ohne (a) waere jeder Gewinn dem falschen Faktor zugeschrieben worden.

GRENZEN, die das Ergebnis von vornherein einschraenken:
- ICON-D2 reicht nur bis 2023 zurueck.  Von 80 Albumabenden bleiben 38.
- Die Domaene ist Mitteleuropa.  Alle Faecherecken liegen drin (geprueft:
  55.95 N / 10.69 E im Juni, 49.11 N / 10.82 E im Dezember), aber bei einer
  freien Ortswahl fuer Freunde faellt das Modell aus.
- Vorlauf nur 48 h.  Fuer den ALARM also nicht brauchbar, fuer die
  VALIDIERUNG sehr wohl: die Frage ist, ob es das Ereignis ueberhaupt
  gaebe, wenn das Modell fein genug waere.
"""
import argparse
import json
import math
import os
import random
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import sonnenuntergang, zielpunkt  # noqa: E402
from sonnen.score import DISTANZEN_KM, FAECHER_AZIMUTE  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(BASIS, "daten", "roh_icond2")
BASIS_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"

NIVEAUS_HPA = (900, 800, 700, 600, 500, 400, 300, 250, 200)
VARIABLEN = (["cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"]
             + ["cloud_cover_%dhPa" % p for p in NIVEAUS_HPA])

# ICON-D2 beginnt im Archiv 2023; 2022-09-20 lieferte 0/24 Stunden.
FRUEHESTER = "2023-01-01"
ZIRKULAER = {"2025-06-29", "2023-06-14", "2023-05-29", "2022-11-11"}

# Minuetliches Limit ist 600.  9/s laesst Luft fuer Nachzuegler.
_takt = threading.Semaphore(1)
_letzte = [0.0]
ABSTAND_S = 1.0 / 7.0


def _bremse():
    with _takt:
        warte = _letzte[0] + ABSTAND_S - time.time()
        if warte > 0:
            time.sleep(warte)
        _letzte[0] = time.time()


class Erschoepft(Exception):
    pass


def _hole(lat, lon, tag):
    u = ("%s?latitude=%.4f&longitude=%.4f&start_date=%s&end_date=%s"
         "&hourly=%s&models=icon_d2"
         % (BASIS_URL, lat, lon, tag, tag, ",".join(VARIABLEN)))
    for versuch in range(5):
        _bremse()
        try:
            with urllib.request.urlopen(u, timeout=120) as f:
                return json.load(f)["hourly"]
        except urllib.error.HTTPError as e:
            try:
                grund = json.loads(e.read()).get("reason", "")
            except Exception:                                    # noqa: BLE001
                grund = ""
            # 429 ist NICHT gleich 429.  Open-Meteo verwendet denselben Code
            # fuer drei verschiedene Dinge, und nur eines davon ist terminal:
            #   "Too many concurrent requests"  - zu viele gleichzeitig, kurz warten
            #   "Minutely ... limit exceeded"   - Minutenfenster voll, 20 s warten
            #   "Daily/Hourly ... exceeded"     - Kontingent, hier ist Schluss
            # Der erste Lauf am 14.08. brach nach 5 von 166 Abenden ab, weil
            # alle drei als "erschoepft" galten.
            if e.code == 429 and "oncurrent" in grund:
                time.sleep(2.0 + 2.0 * versuch)
                continue
            if e.code == 429 and "inutely" in grund:
                time.sleep(20)
                continue
            if e.code == 429:
                raise Erschoepft(grund or "429")
            if versuch < 4:
                time.sleep(3)
                continue
            raise
        except Exception:                                        # noqa: BLE001
            if versuch < 4:
                time.sleep(3)
                continue
            raise
    raise Erschoepft("unerreichbar")


def faecherzellen(tag, breite=52.52, laenge=13.405):
    """Eindeutige Faecherpunkte fuer einen Abend.  d=0 nur einmal."""
    _, azimut = sonnenuntergang(date.fromisoformat(tag), breite, laenge)
    if azimut is None:
        return None, None
    zellen = {}
    for dv in FAECHER_AZIMUTE:
        for d in DISTANZEN_KM:
            if d == 0.0 and dv != 0.0:
                continue
            la, lo = ((breite, laenge) if d == 0.0
                      else zielpunkt(breite, laenge, azimut + dv, d))
            zellen["%.1f_%.1f" % (d, dv)] = (round(la, 4), round(lo, 4))
    return zellen, azimut


def hole_abend(tag):
    """Ein Abend, alle Faecherzellen, zur Sonnenuntergangsstunde. Gecacht."""
    ziel = os.path.join(CACHE, "%s.json" % tag)
    if os.path.exists(ziel):
        with open(ziel) as f:
            return json.load(f)
    zellen, azimut = faecherzellen(tag)
    if zellen is None:
        return None
    stunde, _ = sonnenuntergang(date.fromisoformat(tag), 52.52, 13.405)
    marke = "%sT%02d:00" % (tag, int(round(stunde)) % 24)

    ergebnis = {}
    for schluessel, (la, lo) in zellen.items():
        h = _hole(la, lo, tag)
        try:
            i = h["time"].index(marke)
        except ValueError:
            i = None
        ergebnis[schluessel] = {
            "lat": la, "lon": lo,
            "w": None if i is None else {
                v: h[v][i] for v in VARIABLEN if h.get(v)}}
    daten = {"tag": tag, "azimut": azimut, "stunde": marke,
             "zellen": ergebnis}
    os.makedirs(CACHE, exist_ok=True)
    with open(ziel, "w") as f:
        json.dump(daten, f)
    return daten


def tagesliste(n_kontrollen=4, saat=20260814):
    """Albumabende ab 2023 plus gepaarte Kontrollabende (+/- 21 Tage)."""
    with open(os.path.join(BASIS, "daten", "foto_detail.json")) as f:
        detail = json.load(f)
    album = {x["tag"] for x in detail
             if "Sonnenuntergänge" in x.get("alben", [])
             and 52.2 <= x["lat"] <= 52.8 and 13.0 <= x["lon"] <= 13.9}
    album -= ZIRKULAER
    ziel = sorted(t for t in album if t >= FRUEHESTER)

    jahre = sorted({t[:4] for t in ziel})
    rng = random.Random(saat)
    paare = {}
    for t in ziel:
        d = date.fromisoformat(t)
        kand = []
        for jahr in jahre:
            for versatz in range(-21, 22):
                try:
                    k = date(int(jahr), d.month, d.day) + timedelta(days=versatz)
                except ValueError:
                    continue
                s = k.isoformat()
                if s in album or s < FRUEHESTER or s > "2026-08-13":
                    continue
                kand.append(s)
        rng.shuffle(kand)
        paare[t] = sorted(set(kand[:n_kontrollen]))
    return ziel, paare


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kontrollen", type=int, default=4)
    ap.add_argument("--faeden", type=int, default=3)
    ap.add_argument("--nur-planen", action="store_true")
    a = ap.parse_args()

    ziel, paare = tagesliste(a.kontrollen)
    alle = sorted(set(ziel) | {k for v in paare.values() for k in v})
    offen = [t for t in alle
             if not os.path.exists(os.path.join(CACHE, "%s.json" % t))]
    n_zellen = len(faecherzellen(alle[0])[0])
    print("Albumabende ab %s: %d" % (FRUEHESTER, len(ziel)))
    print("Kontrollabende:      %d" % (len(alle) - len(ziel)))
    print("Abende gesamt:       %d   davon offen: %d" % (len(alle), len(offen)))
    print("Faecherzellen:       %d" % n_zellen)
    print("Calls offen:         %d  (Tagesbudget 10000)"
          % (len(offen) * n_zellen))
    with open(os.path.join(BASIS, "daten", "icond2_plan.json"), "w") as f:
        json.dump({"ziel": ziel, "paare": paare}, f, indent=1)
    if a.nur_planen:
        return

    fertig = [0]
    sperre = threading.Lock()
    abbruch = threading.Event()
    t0 = time.time()

    def arbeite(tag):
        if abbruch.is_set():
            return None
        try:
            hole_abend(tag)
        except Erschoepft as e:
            abbruch.set()
            return "ERSCHOEPFT %s" % e
        except Exception as e:                                   # noqa: BLE001
            return "FEHLER %s %s" % (tag, str(e)[:60])
        with sperre:
            fertig[0] += 1
            if fertig[0] % 10 == 0:
                v = fertig[0] / max(time.time() - t0, 1e-9)
                print("   %d/%d  %.1f Abende/min  Rest %.0f min"
                      % (fertig[0], len(offen), v * 60,
                         (len(offen) - fertig[0]) / max(v, 1e-9) / 60),
                      flush=True)
        return None

    with ThreadPoolExecutor(max_workers=a.faeden) as ex:
        for meldung in ex.map(arbeite, offen):
            if meldung:
                print("  " + meldung, flush=True)

    da = len([t for t in alle
              if os.path.exists(os.path.join(CACHE, "%s.json" % t))])
    print("Im Cache: %d von %d Abenden (%.0f %%)"
          % (da, len(alle), 100.0 * da / len(alle)))


if __name__ == "__main__":
    main()
