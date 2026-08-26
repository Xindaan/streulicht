"""Der Alarmlauf holt Wind nur am Ort - und rechnet trotzdem richtig (T-0042).

Am 18.08.2026 gemessen: ein vollstaendiger Lauf kostete rund 5.500
Kontingenteinheiten und riss damit das Stundenlimit von 5.000 bei der
vorletzten Anfrage.  Ursache war kein Fehler in der Rechnung, sondern im
Abruf: die sechs Windvariablen wurden fuer alle 68 Faecherzellen geholt,
gelesen aber ausschliesslich am Heimatpunkt (der Advektionsversatz ist ein
Ensemble-Mittelwind je Schicht, kein Feld).  Und Open-Meteo zaehlt
Ensemble-Member wie zusaetzliche Variablen - 9 x 51 wiegt dreimal so viel
wie 3 x 51.

Dieser Test fuehrt den echten Ablauf mit erfundenen Daten aus, statt den
Quelltext zu lesen.  Er prueft genau zwei Dinge:

  * WIRD gespart - Wind nur an einer einzigen Zelle;
  * OHNE Schaden - der Wind kommt am Ort an und der Advektionsversatz ist
    nicht still null.  Genau das waere der teure Fehler: ein Lauf, der
    billiger ist und dabei die Advektion abschaltet, saehe erfolgreich aus.

Lauf:  python3 skripte/test_abruf.py
"""
import datetime as dt
import glob
import json
import os
import sys

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import alarm  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


ARCHIV_NEU = []
ZUSTAND_NACH_LAUF = "{}"
SCHREIBWEG = {"truncate": 0, "replace": 0}   # T-0051, siehe Abschnitt 6
MEMBER = [""] + ["%02d" % n for n in range(1, 51)]      # 51 wie ECMWF ENS
ABRUFE = []                                             # Protokoll der Aufrufe


def falscher_abruf(zellen, variablen, modell, tage, block=25):
    """Erfundene, aber formgleiche Antwort - und ein Protokolleintrag."""
    ABRUFE.append({"zellen": set(zellen), "variablen": list(variablen)})
    start = dt.datetime.now(dt.timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0)
    zeiten = [(start + dt.timedelta(hours=3 * k)).strftime("%Y-%m-%dT%H:%M")
              for k in range(8 * tage)]
    aus = {}
    for z in zellen:
        h = {"time": zeiten}
        for v in variablen:
            for m in MEMBER:
                if v.startswith("wind_speed"):
                    w = [40.0] * len(zeiten)          # kraeftig, damit es versetzt
                elif v.startswith("wind_direction"):
                    w = [270.0] * len(zeiten)         # aus Westen
                else:
                    w = [50.0] * len(zeiten)          # halbe Bedeckung
                h[alarm.feldname(v, m)] = w
        aus[z] = h
    return aus


def main():
    kfg = json.load(open(os.path.join(BASIS, "konfig.json")))
    ort = kfg["orte"][0]

    alarm.abfrage = falscher_abruf
    alarm.modelllauf = lambda m: "2026-01-01T00:00+00:00"   # kein Netz noetig

    # OHNE --trocken, damit auch der Schreibweg laeuft (das Archiv entsteht
    # sonst nicht und waere ungeprueft).  Zustand und die erzeugte Datei
    # werden danach zurueckgesetzt - der Pruefstand darf keine Messdaten
    # anfassen.
    global ARCHIV_NEU
    zp = os.path.join(BASIS, "daten", "zustand.json")
    sicherung = open(zp).read() if os.path.exists(zp) else None
    vorher = set(glob.glob(os.path.join(BASIS, "daten", "archiv", "*", "*.json")))
    sicher, sys.argv = sys.argv, ["alarm.py"]
    # T-0051: WIE der Lauf die Zustandsdatei anfasst, nicht nur DASS.  Ein
    # Modul kann `schreibe` importieren und trotzdem daneben mit json.dump
    # schreiben - die erste Fassung der Pruefung ist genau daran vorbei-
    # gelaufen.  Modus "w" auf der Zieldatei truncatet, os.replace tauscht.
    global SCHREIBWEG
    import builtins
    _open, _replace = builtins.open, os.replace

    def _mein_open(datei, modus="r", *aa, **kk):
        if os.path.abspath(str(datei)) == os.path.abspath(zp) \
                and "w" in str(modus):
            SCHREIBWEG["truncate"] += 1
        return _open(datei, modus, *aa, **kk)

    def _mein_replace(src, dst, *aa, **kk):
        if os.path.abspath(str(dst)) == os.path.abspath(zp):
            SCHREIBWEG["replace"] += 1
        return _replace(src, dst, *aa, **kk)

    try:
        builtins.open, os.replace = _mein_open, _mein_replace
        try:
            alarm.main()
        finally:
            builtins.open, os.replace = _open, _replace
    finally:
        sys.argv = sicher
        # Den geschriebenen Zustand FESTHALTEN, bevor er zurueckgesetzt wird -
        # sonst prueft die Leck-Kontrolle unten die Sicherung statt das, was
        # der Lauf geschrieben hat.  Genau so ist die Kontrolle beim ersten
        # Anlauf durch die Negativprobe gefallen, ohne anzuschlagen.
        global ZUSTAND_NACH_LAUF
        ZUSTAND_NACH_LAUF = open(zp).read() if os.path.exists(zp) else "{}"
        if sicherung is not None:
            open(zp, "w").write(sicherung)
    ARCHIV_NEU = sorted(
        set(glob.glob(os.path.join(BASIS, "daten", "archiv", "*", "*.json")))
        - vorher)

    print("\n=== 1. Wind wird nur an einer Zelle geholt")
    wind = [a for a in ABRUFE if any(v.startswith("wind_") for v in a["variablen"])]
    wolke = [a for a in ABRUFE if all(v.startswith("cloud_") for v in a["variablen"])]
    pruefe(len(wind) == 1, "genau ein Windabruf (%d)" % len(wind))
    pruefe(bool(wind) and len(wind[0]["zellen"]) == 1,
           "und der holt genau eine Zelle (%d)"
           % (len(wind[0]["zellen"]) if wind else -1))
    heim = alarm.zelle(ort["breite"], ort["laenge"])
    pruefe(bool(wind) and heim in wind[0]["zellen"],
           "und zwar den Heimatpunkt (%r)" % (heim,))
    pruefe(bool(wind) and not any(v.startswith("cloud_")
                                  for v in wind[0]["variablen"]),
           "keine Wolken im Windabruf")
    pruefe(all(not any(v.startswith("wind_") for v in a["variablen"])
               for a in wolke),
           "kein Wind in den Wolkenabrufen (%d Stueck)" % len(wolke))

    print("\n=== 2. Die Ersparnis, in Kontingenteinheiten")
    import math

    def gewicht(a):
        je = max(1, math.ceil(len(a["variablen"]) * len(MEMBER) / 10))
        return len(a["zellen"]) * je
    jetzt = sum(gewicht(a) for a in ABRUFE)
    # Wie es vor dem 18.08.2026 war: neun Variablen fuer ALLE Faecherzellen.
    faecher = max(len(a["zellen"]) for a in wolke)
    vorher = jetzt - gewicht(wolke[0]) + faecher * math.ceil(9 * len(MEMBER) / 10)
    pruefe(jetzt < 5000, "unter dem Stundenlimit: %d Einheiten" % jetzt)
    print("        vorher rund %d, jetzt rund %d" % (vorher, jetzt))

    print("\n=== 3. Der Wind kommt an: Advektion ist nicht still null")
    # Pass 2 gibt es nur, wenn der Versatz Zellen verschiebt.  Kaeme der
    # Wind nicht an, waere der Versatz (0,0) und es gaebe keinen zweiten
    # Wolkenabruf - der Lauf waere billig und falsch.
    pruefe(len(wolke) >= 2,
           "es gibt einen zweiten Wolkenabruf (Advektion greift): %d"
           % len(wolke))
    if len(wolke) >= 2:
        pruefe(not (wolke[-1]["zellen"] & wolke[0]["zellen"]),
               "Pass 2 holt nur Zellen, die Pass 1 nicht hatte")

    print("\n=== 4. Das Archiv faellt als Nebenprodukt an (T-0003)")
    # Die erste Fassung holte die Felder ein zweites Mal - 16.720
    # Kontingenteinheiten am Tag bei einem Budget von 10.000, und die API
    # antwortete durchgehend mit HTTP 400 "requests too much data".
    # Der Alarmlauf HAT die Daten; archiviert wird, was er ohnehin rechnet.
    import json as _json
    dateien = ARCHIV_NEU
    pruefe(len(dateien) == 1,
           "genau eine Archivdatei ist entstanden (%d)" % len(dateien))
    if dateien:
        d = _json.load(open(dateien[-1]))
        pruefe(d.get("modelllauf") and d.get("geholt"),
               "Kopf nennt Modelllauf und Abrufzeit")
        t0 = sorted(d["abende"])[0]
        e0 = d["abende"][t0]
        pruefe(len(e0.get("member") or []) == len(MEMBER),
               "je Abend eine Zeile pro Member (%d von %d)"
               % (len(e0.get("member") or []), len(MEMBER)))
        pruefe(all(set(m) >= {"s", "schirm", "A", "B"} for m in e0["member"]),
               "die Memberzeile traegt Score und Terme")
        pruefe(bool(e0.get("feld")), "das Medianfeld liegt dabei")
        pruefe(not any("segmente" in m for m in e0["member"]),
               "aber KEINE Segmentliste je Member (waere ein Vielfaches)")
    # Und der Zustand darf davon nichts abbekommen.
    z = _json.loads(ZUSTAND_NACH_LAUF)
    ab = (z.get(ort["name"]) or {}).get("abende", {})
    leck = [t for t, e in ab.items()
            if "member" in e or any("member" in v for v in (e.get("verlauf") or []))]
    pruefe(not leck, "kein Memberblock im Zustand (%s)" % (leck or "-"))

    print("\n=== 6. Die Zustandsdatei wird atomar geschrieben (T-0051)")
    # Vor dem 22.08.2026 stand hier `open(zpfad, "w")` + `json.dump`.  Stirbt
    # der Prozess dazwischen, bleibt eine halbe Datei liegen - und die legt
    # nicht diesen Lauf lahm, sondern ALLE vier Agenten, weil sieben Leser
    # sie mit blankem json.load laden.  Geprueft wird das Verhalten am
    # Dateisystem, nicht der Quelltext.
    pruefe(SCHREIBWEG["truncate"] == 0,
           "der Lauf oeffnet die Zustandsdatei nie mit Modus \"w\" (%d mal)"
           % SCHREIBWEG["truncate"])
    pruefe(SCHREIBWEG["replace"] >= 1,
           "er tauscht sie per os.replace ein (%d mal)"
           % SCHREIBWEG["replace"])
    pruefe(ZUSTAND_NACH_LAUF.strip() not in ("", "{}"),
           "und der Lauf hat wirklich geschrieben (sonst prueft das nichts)")

    for f in ARCHIV_NEU:                       # der Pruefstand raeumt auf
        os.remove(f)

    print("")
    if fehler:
        print("FEHLGESCHLAGEN: %d" % len(fehler))
        raise SystemExit(1)
    print("alle Pruefungen bestanden")


if __name__ == "__main__":
    main()
