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
import shutil
import sys
import tempfile

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
# Beginn der erfundenen Zeitachse (UTC-Mitternacht).  None = heutiger Tag nach
# der Wanduhr (Verhalten dieses Tests); test_ortsfilter.py setzt einen festen
# Tag, damit seine Zeitachse zu seinem festen "jetzt" passt (T-0079).
ZEITACHSE_START = None


def falscher_abruf(zellen, variablen, modell, tage, block=25):
    """Erfundene, aber formgleiche Antwort - und ein Protokolleintrag."""
    ABRUFE.append({"zellen": set(zellen), "variablen": list(variablen)})
    start = ZEITACHSE_START or dt.datetime.now(dt.timezone.utc).replace(
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

    # EIGENES BASISVERZEICHNIS (T-0068, 04.09.2026).  Bis dahin lief dieser
    # Test gegen `daten/zustand.json` des Betriebs: er startete einen echten
    # `alarm.main()` OHNE --trocken, sicherte die Datei vorher weg und schrieb
    # sie danach mit `open(zp, "w")` zurueck - truncierend und ohne Sperre.
    # Faellt in diese Sekunden ein Bewertungsabruf oder eine Erinnerung, ist
    # deren Schreibvorgang verloren.  Ausserdem ueberschrieb der Lauf ein
    # eventuell vorhandenes `<heute>_vonhand.json` im echten Tagesarchiv.
    #
    # Ein Pruefstand darf Messdaten nicht anfassen - auch nicht kurz.  Das
    # Muster steht seit T-0058 in test_zustandspflege.py; hier fehlte es.
    pruefbasis = tempfile.mkdtemp()
    os.makedirs(os.path.join(pruefbasis, "daten"), exist_ok=True)
    kp = os.path.join(pruefbasis, "konfig.json")
    with open(kp, "w") as f:
        json.dump(kfg, f)

    alt = (alarm.BASIS, alarm.abfrage, alarm.modelllauf,
           alarm.warte_auf_netz, alarm.sende)
    alarm.BASIS = pruefbasis
    alarm.abfrage = falscher_abruf
    alarm.modelllauf = lambda m: "2026-01-01T00:00+00:00"   # kein Netz noetig
    alarm.warte_auf_netz = lambda *a_, **k_: None
    # Riegel, keine Erwartung: bei halber Bewoelkung reisst kein Abend die
    # Schwelle, ein Push kaeme also gar nicht vor.  Sollte sich das je
    # aendern, geht er hier ins Leere statt an ein echtes Topic.
    alarm.sende = lambda *a_, **k_: 200

    # OHNE --trocken, damit auch der Schreibweg laeuft (das Archiv entsteht
    # sonst nicht und waere ungeprueft).
    global ARCHIV_NEU
    zp = os.path.join(pruefbasis, "daten", "zustand.json")
    vorher = set(glob.glob(os.path.join(pruefbasis, "daten", "archiv",
                                        "*", "*.json")))
    sicher, sys.argv = sys.argv, ["alarm.py", "--konfig", kp]
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
        # Den geschriebenen Zustand FESTHALTEN - die Leck-Kontrolle weiter
        # unten prueft, was der Lauf wirklich abgelegt hat.
        global ZUSTAND_NACH_LAUF
        ZUSTAND_NACH_LAUF = open(zp).read() if os.path.exists(zp) else "{}"
        (alarm.BASIS, alarm.abfrage, alarm.modelllauf,
         alarm.warte_auf_netz, alarm.sende) = alt
    ARCHIV_NEU = sorted(
        set(glob.glob(os.path.join(pruefbasis, "daten", "archiv",
                                   "*", "*.json")))
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

    shutil.rmtree(pruefbasis, ignore_errors=True)   # der Pruefstand raeumt auf

    print("\n=== 7. Voruebergehende Stoerungen kippen den Lauf nicht (T-0069)")
    # Bis zum 04.09.2026 behandelte _hole() NUR 429.  Ein Timeout, ein
    # abgebrochener Verbindungsaufbau oder ein 502 riss den ganzen Lauf mit
    # Traceback ab - und jeder gescheiterte Versuch hatte sein Kontingent
    # schon verbraucht.  Der Abendlauf wird vom naechsten Tick nachgeholt,
    # der Vormittagslauf nicht.
    #
    # Geprueft wird das VERHALTEN von _hole(): was kommt zurueck, wie oft
    # wurde es versucht, und welche Fehler duerfen NICHT wiederholt werden.
    import io
    import urllib.error

    def _lauf_hole(antworten):
        """_hole() gegen eine Liste vorgegebener Antworten laufen lassen.

        Rueckgabe: (Ergebnis oder Ausnahme, Zahl der Versuche).
        """
        rest = list(antworten)
        zaehler = {"n": 0}

        def falscher_urlopen(u, timeout=None):
            zaehler["n"] += 1
            a = rest.pop(0)
            if isinstance(a, Exception):
                raise a
            class Antwort:
                def __enter__(self_): return io.BytesIO(a)
                def __exit__(self_, *x): return False
            return Antwort()

        alt_open = alarm.urllib.request.urlopen
        alt_sleep = alarm.time.sleep
        alarm.urllib.request.urlopen = falscher_urlopen
        alarm.time.sleep = lambda s: None      # keine echten Wartezeiten
        try:
            return alarm._hole("http://pruefstand"), zaehler["n"]
        except BaseException as ex:            # SystemExit ist kein Exception
            return ex, zaehler["n"]
        finally:
            alarm.urllib.request.urlopen = alt_open
            alarm.time.sleep = alt_sleep

    def http(code, rumpf=b"{}"):
        return urllib.error.HTTPError("http://pruefstand", code, "x", {},
                                      io.BytesIO(rumpf))

    erg, n = _lauf_hole([http(502), http(502), b'{"gut": 1}'])
    pruefe(erg == {"gut": 1} and n == 3,
           "ein 502 wird wiederholt und kommt durch (%r nach %d Versuchen)"
           % (erg, n))

    erg, n = _lauf_hole([urllib.error.URLError("nodename nor servname"),
                         b'{"gut": 2}'])
    pruefe(erg == {"gut": 2} and n == 2,
           "ein Namensfehler wird wiederholt (%r nach %d Versuchen)" % (erg, n))

    erg, n = _lauf_hole([TimeoutError("zu langsam"), b'{"gut": 3}'])
    pruefe(erg == {"gut": 3} and n == 2,
           "ein Timeout wird wiederholt (%r nach %d Versuchen)" % (erg, n))

    # Der Gegenfall, und er ist der wichtigere: eine kaputte ANFRAGE wird beim
    # Wiederholen nicht besser.  Wer 4xx mitwiederholt, verbrennt Kontingent
    # und verdeckt den eigenen Fehler.
    erg, n = _lauf_hole([http(400, b'{"reason": "too much data"}')])
    pruefe(isinstance(erg, urllib.error.HTTPError) and erg.code == 400
           and n == 1,
           "ein 400 wird NICHT wiederholt, sondern durchgereicht (%d Versuch)"
           % n)

    # Kontingent bleibt terminal - sonst laeuft der Lauf in eine Schleife
    # gegen eine Wand, die sich erst um Mitternacht UTC oeffnet.
    erg, n = _lauf_hole([http(429, b'{"reason": "Daily API request limit '
                              b'exceeded"}')])
    pruefe(isinstance(erg, SystemExit) and n == 1,
           "das Tageslimit beendet den Lauf sofort (%d Versuch)" % n)

    # Und ein 429 OHNE lesbaren Rumpf darf nicht am JSON-Parser sterben:
    # vorher kam hier ein JSONDecodeError statt der gemeinten Meldung.
    erg, n = _lauf_hole([http(429, b"<html>rate limited</html>")])
    pruefe(isinstance(erg, SystemExit) and "429" in str(erg),
           "ein 429 ohne JSON-Rumpf meldet Kontingent, nicht JSONDecodeError "
           "(%s)" % type(erg).__name__)

    # Minutenlimit: wartet und versucht es erneut.
    erg, n = _lauf_hole([http(429, b'{"reason": "Minutely API request limit '
                              b'exceeded"}'), b'{"gut": 4}'])
    pruefe(erg == {"gut": 4} and n == 2,
           "das Minutenlimit wird abgewartet (%r nach %d Versuchen)" % (erg, n))

    print("")
    if fehler:
        print("FEHLGESCHLAGEN: %d" % len(fehler))
        raise SystemExit(1)
    print("alle Pruefungen bestanden")


if __name__ == "__main__":
    main()
