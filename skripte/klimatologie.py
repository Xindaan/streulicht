"""Klimatologie des Scores und Ableitung des Schwellwerts s*.

3-Schicht-Variante auf ERA5 (`archive-api`), stuendlich, zur Sonnenuntergangs-
stunde ausgewertet.  ERA5 ist die einzige Quelle mit mehrjaehriger Tiefe -
Druckflaechen hat sie ueber Open-Meteo nicht (siehe docs/befunde-e1.md 1.3).

Zeitliche Zuordnung: naechstliegende volle Stunde.  Maximaler Versatz 30 min,
bei 30 m/s auf 300 hPa also bis 54 km.  Fuer eine Verteilungsschaetzung
unkritisch (Fehler ist zufaellig, nicht systematisch); im Betrieb wird
stattdessen semi-Lagrangesch advehiert.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import sonnenuntergang  # noqa: E402
from sonnen.score import faecherpunkte, score  # noqa: E402

GITTER = float(os.environ.get('WETTER_GITTER', '0.5'))
SCHICHTEN = ("low", "mid", "high")
VARIABLEN = ",".join("cloud_cover_%s" % s for s in SCHICHTEN)
BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def zelle(lat, lon):
    return (round(lat / GITTER), round(lon / GITTER))


def zellmitte(z):
    return (z[0] * GITTER, z[1] * GITTER)


def tage(von, bis):
    t = von
    while t <= bis:
        yield t
        t += timedelta(days=1)


def punktbedarf(von, bis, breite, laenge):
    """(Menge benoetigter Zellen, {Tag: {(d,dv): Zelle}})."""
    zellen, proTag = set(), {}
    for t in tage(von, bis):
        _, az = sonnenuntergang(t, breite, laenge)
        if az is None:
            continue
        m = {}
        for d, dv, la, lo in faecherpunkte(breite, laenge, az):
            z = zelle(la, lo)
            zellen.add(z)
            m[(d, dv)] = z
        proTag[t] = m
    return zellen, proTag


class KontingentErschoepft(Exception):
    pass


# Open-Meteo drosselt gewichtet (Orte x Variablen x Zeitraum), und ich habe die
# Formel zweimal falsch geschaetzt - erst 400 Calls je Request, dann 2500, beides
# unvereinbar mit dem beobachteten Verhalten.  Also nicht mehr modellieren:
# nehmen was geht, jeden Block cachen, bei 429 sauber aussteigen.  Der naechste
# Lauf setzt am Cache an.  Ein Skript, das das Kontingent RAET, ist schlimmer als
# eines, das es ertastet - es wartet Stunden auf ein Limit, das anders liegt.
def _hole(u, versuche=4):
    """Open-Meteo hat DREI Limits (minuetlich / stuendlich / taeglich) und sagt
    im Fehlertext, welches griff.  Nur das minuetliche lohnt Warten - 60 s.
    Beim stuendlichen oder taeglichen sauber aussteigen; der Blockcache haelt
    den Fortschritt, der naechste Lauf setzt dort an."""
    for n in range(versuche):
        try:
            with urllib.request.urlopen(u, timeout=600) as f:
                return json.load(f)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            grund = json.loads(e.read()).get("reason", "429")
            if "inutely" in grund and n < versuche - 1:
                print("      Minutenlimit, warte 65 s ...", flush=True)
                time.sleep(65)
                continue
            raise KontingentErschoepft(grund) from None
    raise KontingentErschoepft("Minutenlimit blieb bestehen")


def hole_jahr(zellen, jahr, gesucht, block=60):
    """{Zelle: {schicht: {Tag: Wert}}} - nur die gesuchten Stunden.

    gesucht: {Tag(str): "YYYY-MM-DDTHH:00"}.  Ein Jahr fuer 235 Zellen sind
    ~56 MB roh; deshalb wird blockweise geholt und sofort auf die
    Sonnenuntergangsstunden reduziert, statt ganze Jahre zu halten.
    Jeder Block wird gecacht - ein Abbruch am Kontingent kostet dann nur den
    laufenden Block, nicht alles Vorherige.
    """
    aus = {}
    liste = sorted(zellen)
    cachedir = os.path.join(BASIS, "daten", "roh")
    os.makedirs(cachedir, exist_ok=True)
    for i in range(0, len(liste), block):
        teil = liste[i:i + block]
        cache = os.path.join(cachedir, "g%g_%d_%04d.json" % (GITTER, jahr, i))
        if os.path.exists(cache):
            with open(cache) as f:
                for k, v in json.load(f).items():
                    la, lo = k.split("/")
                    aus[(int(la), int(lo))] = v
            print("      %d/%d Zellen (Cache)" % (min(i + block, len(liste)),
                                                  len(liste)), flush=True)
            continue
        mitten = [zellmitte(z) for z in teil]
        u = ("https://archive-api.open-meteo.com/v1/archive?latitude=%s&longitude=%s"
             "&hourly=%s&start_date=%d-01-01&end_date=%d-12-31"
             % (",".join("%.4f" % m[0] for m in mitten),
                ",".join("%.4f" % m[1] for m in mitten), VARIABLEN, jahr, jahr))
        d = _hole(u)
        if isinstance(d, dict):
            d = [d]
        teilaus = {}
        for z, eintrag in zip(teil, d):
            h = eintrag["hourly"]
            idx = {t: k for k, t in enumerate(h["time"])}
            teilaus["%d/%d" % z] = {
                s: {tag: h["cloud_cover_%s" % s][idx[stempel]]
                    for tag, stempel in gesucht.items() if stempel in idx}
                for s in SCHICHTEN}
            del h, idx
        del d
        with open(cache, "w") as f:
            json.dump(teilaus, f)
        for k, v in teilaus.items():
            la, lo = k.split("/")
            aus[(int(la), int(lo))] = v
        print("      %d/%d Zellen" % (min(i + block, len(liste)), len(liste)),
              flush=True)
        time.sleep(3)
    return aus


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--von", type=int, default=2022)
    p.add_argument("--bis", type=int, default=2025)
    p.add_argument("--breite", type=float, default=52.52)
    p.add_argument("--laenge", type=float, default=13.405)
    p.add_argument("--name", default="berlin")
    a = p.parse_args()

    von, bis = date(a.von, 1, 1), date(a.bis, 12, 31)
    zellen, proTag = punktbedarf(von, bis, a.breite, a.laenge)
    print("Zeitraum %s..%s, %d Abende" % (von, bis, len(proTag)))
    print("Gitter %g Grad, benoetigte Zellen: %d" % (GITTER, len(zellen)))

    ziel = os.path.join(BASIS, "daten", "score_%s_g%g_%d_%d.json" % (a.name, GITTER, a.von, a.bis))
    if os.path.exists(ziel):
        print("bereits vorhanden: %s" % ziel)
        return

    ergebnis = {}
    for jahr in range(a.von, a.bis + 1):
        gesucht = {}
        for t in tage(date(jahr, 1, 1), date(jahr, 12, 31)):
            if t not in proTag:
                continue
            std, _ = sonnenuntergang(t, a.breite, a.laenge)
            gesucht[str(t)] = "%sT%02d:00" % (t, int(round(std)) % 24)
        print("   %d laden (%d Abende) ..." % (jahr, len(gesucht)), flush=True)
        try:
            feld = hole_jahr(zellen, jahr, gesucht)
        except KontingentErschoepft as e:
            print("   Kontingent erschoepft (%s).  %d Jahre fertig, Rest beim "
                  "naechsten Lauf - der Blockcache bleibt." % (e, jahr - a.von),
                  flush=True)
            break

        for tag, karte in ((str(t), proTag[t]) for t in tage(
                date(jahr, 1, 1), date(jahr, 12, 31)) if t in proTag):

            def hole(d, dv, schicht, _t=tag, _k=karte):
                z = _k.get((d, dv))
                if z is None or z not in feld:
                    return None
                v = feld[z][schicht].get(_t)
                return None if v is None else v / 100.0

            s, det = score(hole)
            ergebnis[tag] = {"s": s, "schirm": det["schirm"] if det else None,
                             "A": det["A"] if det else None,
                             "B": det["B"] if det else None}
        del feld
    if not ergebnis:
        print("nichts gerechnet - Kontingent war sofort erschoepft.")
        return
    teil = os.path.join(BASIS, "daten", "score_%s_g%g_teil.json" % (a.name, GITTER))
    fertig = len(ergebnis) >= len(proTag) * 0.99
    with open(ziel if fertig else teil, "w") as f:
        json.dump(ergebnis, f)
    print("geschrieben: %s (%d von %d Abenden)"
          % (ziel if fertig else teil, len(ergebnis), len(proTag)))


if __name__ == "__main__":
    main()
