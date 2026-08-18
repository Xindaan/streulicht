"""Erzeugt je konfiguriertem Ort eine Bewertungsseite aus der Vorlage.

WARUM ES DAS BRAUCHT (15.08.2026).  `web/bewerten.html` war immer schon eine
Vorlage mit Platzhaltern, aber es gab kein Skript, das sie fuellt -
`bewerten-berlin.html` war von Hand ausgefuellt.  Das faellt spaetestens bei
Entscheidung D4 auf die Fuesse: der Ort ist ein Parameter, und fuer
Freund:innen an anderen Orten muesste jemand die Datei kopieren und zwei
Zeichenketten tauschen, ohne sie zu vergessen.

Ein Ort, der in `konfig.json` steht, hat ab jetzt automatisch eine Seite.

NEU AM 16.08.2026: die Seite legt die Prognose NACH der Abgabe frei.  Dafuer
schreibt dieses Skript den Prognosestand je Abend mit - Stufe, Perzentil,
Wahrscheinlichkeit und das Himmelsband.  Er steht in einer Skriptkonstante,
nicht im sichtbaren Dokument: vor der Abgabe ist nichts davon auf dem Schirm,
und geladen wird auch nichts nach.  Wer den Quelltext oeffnet, findet ihn -
bewusst in Kauf genommen (siehe Kommentar in der Vorlage).

Lauf:  python3 skripte/bewertungsseite.py
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import date, datetime, timedelta, timezone
from datetime import time as dtzeit

import band  # noqa: E402
from seite import stufe  # noqa: E402
from sonnen.geometrie import sonnenuntergang  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VORLAGE = os.path.join(BASIS, "web", "bewerten.html")
PLATZHALTER = ("__NTFY_BEWERTUNG__", "__ORT__", "__ANZEIGE__", "__SEITE__",
               "__PROGNOSE__", "__PROGNOSESEITE__", "__SONNE__")


def prognosestand(ort_name, s_stern):
    """{tag: {band, stufe, klasse, p, wahrsch}} - was der Alarm gerechnet hat.

    Nur Abende MIT Prognose landen hier.  Ein Abend, den es im Zustand gibt,
    weil er bewertet wurde, aber fuer den nie gerechnet wurde, fehlt bewusst -
    die Seite sagt dann "keine Prognose fuer diesen Abend gerechnet", statt
    einen Platzhalter zu zeigen.  Genau der Fall des 15.08.2026.
    """
    zp = os.path.join(BASIS, "daten", "zustand.json")
    kp = os.path.join(BASIS, "daten", "score_berlin_g0.5_2022_2025.json")
    if not (os.path.exists(zp) and os.path.exists(kp)):
        return {}
    with open(kp) as f:
        alle = sorted(v["s"] for v in json.load(f).values())
    with open(zp) as f:
        zustand = json.load(f)
    abende = (zustand.get(ort_name) or {}).get("abende", {})
    aus = {}
    for i, t in enumerate(sorted(abende)):
        e = abende[t]
        if e.get("median") is None:
            continue
        rang = sum(1 for x in alle if x < e["median"]) / len(alle)
        name, klasse = stufe(rang)
        aus[t] = {"band": band.svg(e["median"], s_stern, i),
                  "stufe": name, "klasse": klasse,
                  "p": round(rang, 4), "wahrsch": e.get("p")}
    return aus


def sonnentafel(ort, tage=4):
    """{Tag: Sonnenuntergang als ISO-UTC} fuer die Tage um heute.

    WOZU (18.08.2026).  Die Seite muss wissen, WELCHEN Abend eine Bewertung
    meint.  Sie hat das bis heute an einer festen Uhrzeit entschieden: "vor
    04:00 zaehlt der Abend als gestern".  Am 18.08. um 04:26 hat Andre den
    Sonnenuntergang des 17. bewertet - die Regel hat daraus den 18. gemacht,
    also einen Abend, der noch gar nicht stattgefunden hatte.

    Mit dieser Tafel entscheidet die Seite richtig: gemeint ist der LETZTE
    Sonnenuntergang, der schon vorbei ist.  Das gilt im Dezember (SU 15:53)
    genauso wie im Juni (21:33), wo jede feste Grenze schiefliegt.
    """
    aus = {}
    heute = date.today()
    for k in range(-tage, tage + 1):
        t = heute + timedelta(days=k)
        std, _ = sonnenuntergang(t, ort["breite"], ort["laenge"])
        if std is None:
            continue
        aus[t.isoformat()] = (datetime.combine(t, dtzeit(0), timezone.utc)
                              + timedelta(hours=std)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return aus


def erzeuge(ort, vorlage):
    fehlend = [s for s in PLATZHALTER if s not in vorlage]
    if fehlend:
        raise SystemExit("Vorlage ohne Platzhalter %s - schon gefuellt?"
                         % ", ".join(fehlend))
    seite = vorlage
    for schluessel, wert in (
            ("__NTFY_BEWERTUNG__", ort["ntfy_bewertung"]),
            ("__ANZEIGE__", ort.get("anzeige", ort["name"])),
            ("__SEITE__", ort.get("_seite", "")),
            ("__PROGNOSESEITE__", ort.get("_prognoseseite", "")),
            ("__PROGNOSE__", ort.get("_prognose", "{}")),
            ("__SONNE__", ort.get("_sonne", "{}")),
            # __ORT__ ZULETZT: es ist ein Teilstring von nichts, aber die
            # anderen Schluessel enthalten "__ORT__" nicht - waere einer
            # frueher dran, ersetzte er in bereits eingesetztem Inhalt.
            ("__ORT__", ort["name"])):
        seite = seite.replace(schluessel, wert)
    return seite


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--konfig", default=os.path.join(BASIS, "konfig.json"))
    a = ap.parse_args()

    with open(a.konfig) as f:
        kfg = json.load(f)
    with open(VORLAGE) as f:
        vorlage = f.read()

    basis_url = (kfg.get("seiten_basis") or "").rstrip("/")
    s_stern = kfg["schwelle_score"]
    for ort in kfg["orte"]:
        # Klickziel der Quittung: dieselbe Seite. Leer, solange nichts
        # ausgeliefert ist - dann faellt die Seite auf location.href zurueck.
        ort["_seite"] = ("%s/bewerten-%s.html" % (basis_url, ort["name"])
                         if basis_url else "")
        ort["_prognoseseite"] = "%s/index.html" % basis_url if basis_url else ""
        stand = prognosestand(ort["name"], s_stern)
        ort["_prognose"] = json.dumps(stand, ensure_ascii=False)
        ort["_sonne"] = json.dumps(sonnentafel(ort), ensure_ascii=False)
        fehlt = [k for k in ("name", "ntfy_bewertung") if not ort.get(k)]
        if fehlt:
            print("   %s: uebersprungen, %s fehlt"
                  % (ort.get("name", "?"), ", ".join(fehlt)))
            continue
        ziel = os.path.join(BASIS, "web", "bewerten-%s.html" % ort["name"])
        seite = erzeuge(ort, vorlage)
        with open(ziel, "w", encoding="utf-8") as f:
            f.write(seite)
        print("   %-10s -> %s (%.1f kB, %d Abende mit Prognose)"
              % (ort["name"], os.path.relpath(ziel, BASIS),
                 len(seite.encode()) / 1000, len(stand)))

    # Gegenprobe: keine erzeugte Seite darf noch einen Platzhalter tragen.
    rest = []
    for ort in kfg["orte"]:
        p = os.path.join(BASIS, "web", "bewerten-%s.html" % ort["name"])
        if os.path.exists(p):
            with open(p) as f:
                s = f.read()
            if any(x in s for x in PLATZHALTER):
                rest.append(ort["name"])
    if rest:
        raise SystemExit("Platzhalter uebrig in: %s" % ", ".join(rest))
    print("Alle Seiten ohne Platzhalter.")


if __name__ == "__main__":
    main()
