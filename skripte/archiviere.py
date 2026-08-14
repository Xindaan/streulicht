"""Taegliche Ensemble-Archivierung (T-0003).

Warum das dringend ist und an keiner Entscheidung haengt: Das Ensemble-Archiv
bei Open-Meteo reicht nur 93 Tage zurueck und wandert mit.  Jeder Tag ohne
Archivierung ist ein dauerhaft verlorener Kalibrierungstag - ohne Ensemble-
historie gibt es weder Rangdiagramm noch Skill ueber Vorlauf noch die
Quantilbruecke von der GFS-Klimatologie auf den ECMWF-Betrieb.

Gespeichert wird bewusst MEHR als der aktuelle Score braucht:
low/mid/high fuer die 3-Schicht-Variante UND die Druckflaechen fuer die
niveauaufgeloeste.  Welche von beiden gewinnt, entscheidet erst die Ablation
(T-0006) - und bis dahin ist das Fenster fuer diese Tage zu.

Volumen: rund 2 MB je Lauf nach Extraktion (roh ~90 MB, wird verworfen).
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import sonnenuntergang  # noqa: E402
from sonnen.score import faecherpunkte  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELL = "ecmwf_ifs025"
NIVEAUS = (1000, 925, 850, 700, 600, 500, 400, 300, 250, 200)
SCHICHTEN = ("low", "mid", "high")
VORLAUF_TAGE = 10
GITTER = 0.25


def variablen():
    v = ["cloud_cover_%s" % s for s in SCHICHTEN]
    for p in NIVEAUS:
        v += ["relative_humidity_%dhPa" % p, "temperature_%dhPa" % p,
              "wind_speed_%dhPa" % p, "wind_direction_%dhPa" % p]
    return v


def zelle(lat, lon):
    return (round(lat / GITTER), round(lon / GITTER))


def hole(zellen, tage, block=25):
    """{Zelle: {variable: {schritt: [Member...]}}} in nativer Aufloesung."""
    aus = {}
    liste = sorted(zellen)
    vs = ",".join(variablen())
    for i in range(0, len(liste), block):
        teil = liste[i:i + block]
        u = ("https://ensemble-api.open-meteo.com/v1/ensemble?latitude=%s&longitude=%s"
             "&models=%s&hourly=%s&forecast_days=%d&temporal_resolution=native"
             % (",".join("%.4f" % (z[0] * GITTER) for z in teil),
                ",".join("%.4f" % (z[1] * GITTER) for z in teil),
                MODELL, vs, tage))
        with urllib.request.urlopen(u, timeout=600) as f:
            d = json.load(f)
        if isinstance(d, dict):
            d = [d]
        for z, eintrag in zip(teil, d):
            aus[z] = eintrag["hourly"]
        print("   %d/%d Zellen" % (min(i + block, len(liste)), len(liste)),
              flush=True)
        time.sleep(2)
    return aus


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--breite", type=float, default=52.52)
    ap.add_argument("--laenge", type=float, default=13.405)
    ap.add_argument("--name", default="berlin")
    a = ap.parse_args()

    heute = datetime.now(timezone.utc).date()
    ziel_dir = os.path.join(BASIS, "daten", "archiv", a.name)
    os.makedirs(ziel_dir, exist_ok=True)
    ziel = os.path.join(ziel_dir, "%s.json" % heute)
    if os.path.exists(ziel):
        print("Lauf %s bereits archiviert - idempotent, nichts zu tun." % heute)
        return

    # Fanpunkte fuer jeden Vorlauftag; der Azimut wandert ca. 0.5 Grad/Tag.
    zellen, proTag = set(), {}
    for k in range(1, VORLAUF_TAGE + 1):
        t = heute + timedelta(days=k)
        std, az = sonnenuntergang(t, a.breite, a.laenge)
        if std is None:
            continue
        karte = {}
        for d, dv, la, lo in faecherpunkte(a.breite, a.laenge, az):
            z = zelle(la, lo)
            zellen.add(z)
            karte["%g/%g" % (d, dv)] = "%d/%d" % z
        proTag[str(t)] = {"stunde_utc": std, "azimut": az, "punkte": karte}
    print("Lauf %s: %d Abende, %d Zellen, %d Variablen"
          % (heute, len(proTag), len(zellen), len(variablen())))

    feld = hole(zellen, VORLAUF_TAGE + 1)

    # Nur die zwei nativen Schritte um jeden Sonnenuntergang behalten.
    zeit = feld[next(iter(feld))]["time"]
    behalten = set()
    for tag, info in proTag.items():
        ziel_dt = datetime.fromisoformat(tag).replace(tzinfo=timezone.utc) \
            + timedelta(hours=info["stunde_utc"])
        paare = sorted(zeit, key=lambda s: abs(
            (datetime.fromisoformat(s).replace(tzinfo=timezone.utc) - ziel_dt)
            .total_seconds()))[:2]
        behalten.update(paare)
        info["schritte"] = sorted(paare)
    idx = {t: i for i, t in enumerate(zeit) if t in behalten}
    print("   %d native Schritte behalten von %d" % (len(idx), len(zeit)))

    kompakt = {}
    for z, h in feld.items():
        eintrag = {}
        for k, reihe in h.items():
            if k == "time":
                continue
            eintrag[k] = {t: reihe[i] for t, i in idx.items()}
        kompakt["%d/%d" % z] = eintrag

    with open(ziel, "w") as f:
        json.dump({"lauf": str(heute), "modell": MODELL, "ort": [a.breite, a.laenge],
                   "abende": proTag, "felder": kompakt}, f)
    print("geschrieben: %s (%.1f MB)" % (ziel, os.path.getsize(ziel) / 1e6))


if __name__ == "__main__":
    main()
