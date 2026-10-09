"""Ein 429 kostet beim naechsten Tick nur die fehlenden Bloecke (T-0074).

Bis zum 09.10.2026 verwarf ein Abbruch am Stunden- oder Tageslimit alles
schon Geholte, und jeder stuendliche Nachhol-Tick zahlte Pass 1 und Pass 2
erneut - seit 16.09. 29 volle Fehllaeufe mit zusammen 10.175 Ortsabrufen
(Review 09.10.2026, alarm#1, tests#6).

Der Test faehrt den ECHTEN alarm.main() mit einem erfundenen Netz: urlopen
ist gestubbt, antwortet formgleich wie Open-Meteo und zaehlt jeden Aufruf.
Gemessen wird die Zahl der Netzaufrufe, nicht der Quelltext:

  a) 429 "Hourly" mitten in Pass 2 -> der Folgelauf holt nur die fehlenden
     Bloecke und rechnet dieselben Zahlen wie ein ungestoerter Lauf;
  b) Sperre aktiv -> kein einziger Netzaufruf;
  c) 429 "Daily" -> Sperre bis 00:02 UTC des Folgetags;
  d) neuer Modelllauf -> der Cache wird nicht benutzt (und unbekannter
     Modelllauf -> gar kein Cache);
  e) Pass-2-Deckel greift und behaelt die naechsten Abende;
  f) Minutenlimit und "concurrent" verbrauchen keine Netzversuche (alarm#10);
  g) alte Cacheordner werden beim Start geraeumt, ein kaputter Block wird
     neu geholt statt still zu fehlen;
  h) derselbe Modelllauf an einem neuen UTC-Tag bekommt keinen Block vom
     Vortag (die Zeitachse beginnt bei Open-Meteo am Abruftag).

Alles laeuft in einem eigenen Temp-Verzeichnis (alarm.BASIS umgebogen),
ohne echte Wartezeiten und ohne Netz.

Lauf:  .venv/bin/python3 skripte/test_kontingent.py
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
from datetime import date, datetime, timedelta, timezone

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import alarm  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


MEMBER = [""] + ["%02d" % n for n in range(1, 5)]       # 5 reichen hier
JETZT = "2026-10-09T12:00"                               # vor Sonnenuntergang
INIT_A = "2026-10-09T00:00+00:00"
INIT_B = "2026-10-09T06:00+00:00"


def utc(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def wert(la, lo, var, m, k):
    """Bedeckung, die von Ort, Schicht, Member und Schritt abhaengt.

    Damit ein Block, der der falschen Zelle zugeordnet wird, ANDERE Zahlen
    ergibt - bei einem gleichfoermigen Feld waere jeder Fehler unsichtbar.
    """
    h = (int(la * 100) * 7 + int(lo * 100) * 13 + len(var) * 3
         + (int(m) if m else 0) * 11 + k * 5) % 101
    return float(h)


class Netz:
    """Erfundenes Open-Meteo: zaehlt Aufrufe, kann an Aufruf n ein 429 werfen."""

    def __init__(self, fehler_bei=None, grund=None):
        self.urls = []
        self.fehler_bei = fehler_bei
        self.grund = grund

    def __call__(self, u, timeout=None):
        self.urls.append(u)
        if self.fehler_bei is not None and len(self.urls) == self.fehler_bei:
            raise urllib.error.HTTPError(
                u, 429, "x", {},
                io.BytesIO(json.dumps({"reason": self.grund}).encode()))
        q = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
        las = [float(x) for x in q["latitude"][0].split(",")]
        los = [float(x) for x in q["longitude"][0].split(",")]
        variablen = q["hourly"][0].split(",")
        tage = int(q["forecast_days"][0])
        start = utc(JETZT).replace(hour=0)
        zeiten = [(start + timedelta(hours=3 * k)).strftime("%Y-%m-%dT%H:%M")
                  for k in range(8 * tage)]
        aus = []
        for la, lo in zip(las, los):
            h = {"time": zeiten}
            for v in variablen:
                for m in MEMBER:
                    if v.startswith("wind_speed"):
                        w = [60.0] * len(zeiten)
                    elif v.startswith("wind_direction"):
                        w = [250.0] * len(zeiten)
                    else:
                        w = [wert(la, lo, v, m, k) for k in range(len(zeiten))]
                    h[alarm.feldname(v, m)] = w
            aus.append({"latitude": la, "longitude": lo, "hourly": h})
        rumpf = json.dumps(aus[0] if len(aus) == 1 else aus).encode()

        class Antwort:
            def __enter__(self_):
                return io.BytesIO(rumpf)

            def __exit__(self_, *x):
                return False
        return Antwort()


class NetzAbruftag(Netz):
    """Wie Open-Meteo ohne `timezone`: die Zeitachse beginnt am UTC-Tag des
    ABRUFS (`tag`), und Wind wie Bedeckung haengen an der absoluten Zeit,
    nicht am Index.  Ein Block vom Vortag hat dann andere Werte am selben
    Index - bei konstantem Wind (wie in `Netz`) waere das unsichtbar.
    """

    def __init__(self, tag, **k):
        super().__init__(**k)
        self.tag = tag

    def __call__(self, u, timeout=None):
        self.urls.append(u)
        if self.fehler_bei is not None and len(self.urls) == self.fehler_bei:
            raise urllib.error.HTTPError(
                u, 429, "x", {},
                io.BytesIO(json.dumps({"reason": self.grund}).encode()))
        q = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
        las = [float(x) for x in q["latitude"][0].split(",")]
        los = [float(x) for x in q["longitude"][0].split(",")]
        variablen = q["hourly"][0].split(",")
        tage = int(q["forecast_days"][0])
        start = utc(self.tag)
        zt = [start + timedelta(hours=3 * k) for k in range(8 * tage)]
        schritt = [int(t.timestamp() // 10800) for t in zt]
        aus = []
        for la, lo in zip(las, los):
            h = {"time": [t.strftime("%Y-%m-%dT%H:%M") for t in zt]}
            for v in variablen:
                for m in MEMBER:
                    if v.startswith("wind_speed"):
                        w = [20.0 + (k % 7) * 15.0 for k in schritt]
                    elif v.startswith("wind_direction"):
                        w = [250.0] * len(zt)
                    else:
                        w = [wert(la, lo, v, m, k) for k in schritt]
                    h[alarm.feldname(v, m)] = w
            aus.append({"latitude": la, "longitude": lo, "hourly": h})
        rumpf = json.dumps(aus[0] if len(aus) == 1 else aus).encode()

        class Antwort:
            def __enter__(self_):
                return io.BytesIO(rumpf)

            def __exit__(self_, *x):
                return False
        return Antwort()


def neue_basis(**konfig):
    d = tempfile.mkdtemp(prefix="kontingent_")
    os.makedirs(os.path.join(d, "daten"))
    kfg = json.load(open(os.path.join(BASIS, "konfig.json")))
    kfg["vorlauf_tage"] = 3          # klein halten: 4 Abende statt 11
    kfg.update(konfig)
    with open(os.path.join(d, "konfig.json"), "w") as f:
        json.dump(kfg, f)
    return d


def zustand(basis):
    p = os.path.join(basis, "daten", "zustand.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def lauf(basis, uhr, init, netz, jetzt=None):
    """alarm.main() einmal fahren.  Rueckgabe: (Ausnahme oder None, Log).

    `uhr` ist die echte Uhr (_jetzt_utc), `jetzt` das --jetzt des Laufs
    (Default JETZT).
    """
    alt = (alarm.BASIS, alarm.modelllauf, alarm.warte_auf_netz, alarm.sende,
           alarm._jetzt_utc, alarm.urllib.request.urlopen, alarm.time.sleep,
           sys.argv)
    zaehler = {"modelllauf": 0}

    def mlauf(m):
        zaehler["modelllauf"] += 1
        return init
    alarm.BASIS = basis
    alarm.modelllauf = mlauf
    alarm.warte_auf_netz = lambda *a, **k: None
    alarm.sende = lambda *a, **k: 200          # Riegel: nie ein echtes Topic
    alarm._jetzt_utc = lambda: utc(uhr)
    alarm.urllib.request.urlopen = netz
    alarm.time.sleep = lambda s: None
    sys.argv = ["alarm.py", "--konfig", os.path.join(basis, "konfig.json"),
                "--jetzt", jetzt or JETZT]
    for k in alarm.LAST:
        alarm.LAST[k] = 0
    puffer = io.StringIO()
    ausnahme = None
    try:
        with contextlib.redirect_stdout(puffer):
            alarm.main()
    except SystemExit as ex:
        ausnahme = ex
    finally:
        (alarm.BASIS, alarm.modelllauf, alarm.warte_auf_netz, alarm.sende,
         alarm._jetzt_utc, alarm.urllib.request.urlopen, alarm.time.sleep,
         sys.argv) = alt
    netz.modelllauf = zaehler["modelllauf"]
    return ausnahme, puffer.getvalue()


def ist_wind(u):
    return "wind_speed" in u


def zahlen(z):
    """p und Median je Abend - der fachliche Fingerabdruck eines Laufs."""
    ab = (z.get("berlin") or {}).get("abende", {})
    return {t: (e["p"], e["median"]) for t, e in sorted(ab.items())}


def main():
    print("alarm geladen aus %s" % alarm.__file__)
    aufzuraeumen = []

    # --- Referenz: ein ungestoerter Lauf -----------------------------------
    ref = neue_basis()
    aufzuraeumen.append(ref)
    netz_ref = Netz()
    ex, log_ref = lauf(ref, "2026-10-09T14:30", INIT_A, netz_ref)
    n_ref = len(netz_ref.urls)
    w = next(i for i, u in enumerate(netz_ref.urls) if ist_wind(u))
    n_pass2 = n_ref - w - 1
    print("\nReferenz: %d Netzaufrufe, Wind an Stelle %d, %d Bloecke Pass 2"
          % (n_ref, w + 1, n_pass2))
    pruefe(ex is None, "Referenzlauf laeuft durch (%r)" % ex)
    pruefe(n_pass2 >= 3, "Pass 2 hat mindestens drei Bloecke (%d) - sonst "
           "gibt es kein 'mitten in Pass 2'" % n_pass2)
    z_ref = zahlen(zustand(ref))
    pruefe(len(z_ref) >= 3, "Referenz rechnet mehrere Abende (%d)" % len(z_ref))

    print("\n=== a) 429 'Hourly' mitten in Pass 2, Folgelauf holt nur den Rest")
    a = neue_basis()
    aufzuraeumen.append(a)
    bruch = w + 3              # Aufruf-Nr. (1-basiert): zweiter Pass-2-Block
    netz1 = Netz(fehler_bei=bruch,
                 grund="Hourly API request limit exceeded. Please try again "
                       "in the next hour.")
    ex, log1 = lauf(a, "2026-10-09T14:30", INIT_A, netz1)
    pruefe(isinstance(ex, alarm.Kontingent),
           "erster Lauf bricht am Kontingent ab (%s)" % type(ex).__name__)
    pruefe(len(netz1.urls) == bruch,
           "und hat bis dahin %d Aufrufe gemacht (%d)" % (bruch, len(netz1.urls)))
    sp = zustand(a).get(alarm.SPERRSCHLUESSEL) or {}
    pruefe(sp.get("sperre_bis") == "2026-10-09T15:02+00:00",
           "Sperre bis zur naechsten vollen Stunde + 2 min: %s"
           % sp.get("sperre_bis"))

    netz_b = Netz()
    ex, log_b = lauf(a, "2026-10-09T14:59", INIT_A, netz_b)
    print("\n=== b) Sperre aktiv: kein einziger Netzaufruf")
    pruefe(ex is None, "Lauf in der Sperre endet ohne Fehler (%r)" % ex)
    pruefe(len(netz_b.urls) == 0 and netz_b.modelllauf == 0,
           "kein Netzaufruf, auch kein Modelllauf (%d/%d)"
           % (len(netz_b.urls), netz_b.modelllauf))
    pruefe("Kontingentsperre bis 09.10. 15:02" in log_b,
           "und sagt im Log, warum")
    pruefe("laeufe" not in (zustand(a).get("berlin") or {}),
           "das Fenster wird dabei nicht verbraucht")

    netz2 = Netz()
    ex, log2 = lauf(a, "2026-10-09T15:20", INIT_A, netz2)
    print("\n=== a) Fortsetzung nach der Sperre")
    erwartet = n_ref - (bruch - 1)
    pruefe(ex is None, "Folgelauf laeuft durch (%r)" % ex)
    pruefe(len(netz2.urls) == erwartet,
           "holt nur die fehlenden Bloecke: %d Aufrufe statt %d (erwartet %d)"
           % (len(netz2.urls), n_ref, erwartet))
    pruefe(set(netz2.urls) == set(netz_ref.urls[bruch - 1:]),
           "und zwar genau den abgebrochenen Block und alle danach")
    pruefe(zahlen(zustand(a)) == z_ref,
           "rechnet dieselben Zahlen wie der ungestoerte Lauf")
    pruefe(alarm.SPERRSCHLUESSEL not in zustand(a),
           "die abgelaufene Sperre ist aus dem Zustand entfernt")
    pruefe(alarm.ABRUF_CACHE["init"] is None,
           "nach main() zeigt der Cache-Schluessel auf keinen Lauf mehr")

    print("\n=== c) 429 'Daily': Sperre bis 00:02 UTC des Folgetags")
    c = neue_basis()
    aufzuraeumen.append(c)
    netz_c = Netz(fehler_bei=1, grund="Daily API request limit exceeded. "
                                      "Please try again tomorrow.")
    ex, _ = lauf(c, "2026-10-09T14:30", INIT_A, netz_c)
    sp = zustand(c).get(alarm.SPERRSCHLUESSEL) or {}
    pruefe(isinstance(ex, alarm.Kontingent) and
           sp.get("sperre_bis") == "2026-10-10T00:02+00:00",
           "Sperre bis 10.10. 00:02 UTC (%s)" % sp.get("sperre_bis"))
    netz_c2 = Netz()
    lauf(c, "2026-10-09T23:59", INIT_A, netz_c2)
    pruefe(len(netz_c2.urls) == 0, "um 23:59 UTC kein Abruf (%d)"
           % len(netz_c2.urls))
    netz_c3 = Netz()
    lauf(c, "2026-10-10T00:03", INIT_A, netz_c3)
    pruefe(len(netz_c3.urls) > 0, "um 00:03 UTC wird wieder geholt (%d)"
           % len(netz_c3.urls))
    # Stundenlimit kurz vor Mitternacht: die Sperre geht ueber den Datumswechsel
    pruefe(alarm.sperre_bis("Hourly API request limit exceeded",
                            utc("2026-10-09T23:40"))
           == utc("2026-10-10T00:02"),
           "Stundenlimit um 23:40 sperrt bis 00:02 des Folgetags")
    pruefe(alarm.sperre_bis("Minutely API request limit exceeded",
                            utc("2026-10-09T14:30")) is None,
           "Minutenlimit setzt keine Sperre")

    print("\n=== d) Neuer Modelllauf: der Cache wird nicht benutzt")
    # Basis `ref` hat einen vollstaendigen Cache fuer INIT_A.
    netz_d1 = Netz()
    lauf(ref, "2026-10-09T16:00", INIT_A, netz_d1)
    pruefe(len(netz_d1.urls) == 0,
           "gleicher Modelllauf: alles aus dem Cache (%d Aufrufe)"
           % len(netz_d1.urls))
    netz_d2 = Netz()
    lauf(ref, "2026-10-09T16:00", INIT_B, netz_d2)
    pruefe(len(netz_d2.urls) == n_ref,
           "neuer Modelllauf: voller Abruf (%d von %d)"
           % (len(netz_d2.urls), n_ref))
    dn = neue_basis()
    aufzuraeumen.append(dn)
    lauf(dn, "2026-10-09T14:30", None, Netz())
    netz_d3 = Netz()
    _, log_d3 = lauf(dn, "2026-10-09T14:31", None, netz_d3)
    pruefe(len(netz_d3.urls) == n_ref,
           "unbekannter Modelllauf: kein Cache, voller Abruf (%d)"
           % len(netz_d3.urls))
    pruefe(not os.path.exists(os.path.join(dn, "daten", "cache")),
           "und es wird auch nichts abgelegt")

    print("\n=== e) Pass-2-Deckel behaelt die naechsten Abende")
    # Verhalten der Auswahl an einem kleinen, durchschaubaren Fall: drei
    # Abende, je zwei neue Zellen; Platz fuer drei.
    t1, t2, t3 = date(2026, 10, 9), date(2026, 10, 10), date(2026, 10, 11)
    abende = {t: {"punkte": {(10.0, 0.0): (52.5 + i, 13.5)}}
              for i, t in enumerate((t1, t2, t3))}
    karte = {(t3, "low", (10.0, 0.0)): (1, 1), (t3, "mid", (10.0, 0.0)): (1, 2),
             (t2, "low", (10.0, 0.0)): (9, 9), (t2, "mid", (10.0, 0.0)): (9, 8),
             (t1, "low", (10.0, 0.0)): (5, 5), (t1, "mid", (10.0, 0.0)): (5, 4)}
    neu = set(karte.values())
    with contextlib.redirect_stdout(io.StringIO()) as puf:
        behalten = alarm.deckle_pass2(neu, karte, abende, 3)
    pruefe(behalten == {(5, 5), (5, 4), (9, 8)},
           "behaelt beide Zellen des ersten Abends und eine des zweiten (%s)"
           % sorted(behalten))
    pruefe(karte[(t3, "low", (10.0, 0.0))] == alarm.zelle(54.5, 13.5)
           and karte[(t2, "low", (10.0, 0.0))] == alarm.zelle(53.5, 13.5),
           "verworfene Punkte zeigen auf die unversetzte Faecherzelle")
    pruefe(karte[(t1, "low", (10.0, 0.0))] == (5, 5),
           "behaltene Punkte bleiben versetzt")
    pruefe("GEDECKELT: 3 von 6" in puf.getvalue(), "laute Logzeile mit Zahl")
    pruefe(alarm.deckle_pass2(neu, dict(karte), abende, None) == neu,
           "null in konfig.json heisst: kein Deckel")

    # Und im echten Lauf.  Die Grenze wird so gesetzt, dass genau der
    # naechste Abend Platz hat: wie viele neue Zellen er braucht, liest ein
    # Mithoerer am Aufruf von deckle_pass2 ab (er aendert nichts).
    mit = {}
    echt = alarm.deckle_pass2

    def mithoerer(neu_, karte_, abende_, grenze_):
        t0 = min(t for (t, _s, _p) in karte_)
        mit["bedarf"] = len({z for (t, _s, _p), z in karte_.items()
                             if t == t0 and z in neu_})
        mit["gesamt"] = len(neu_)
        return echt(neu_, karte_, abende_, grenze_)
    alarm.deckle_pass2 = mithoerer
    try:
        lauf(neue_basis(), "2026-10-09T14:30", INIT_A, Netz())
    finally:
        alarm.deckle_pass2 = echt
    grenze = mit.get("bedarf", 0)
    print("        naechster Abend braucht %d von %d Pass-2-Zellen"
          % (grenze, mit.get("gesamt", 0)))
    e = neue_basis(pass2_max_zellen=grenze)
    aufzuraeumen.append(e)
    netz_e = Netz()
    ex, log_e = lauf(e, "2026-10-09T14:30", INIT_A, netz_e)
    w_e = next(i for i, u in enumerate(netz_e.urls) if ist_wind(u))
    zellen2 = sum(len(urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
                      ["latitude"][0].split(","))
                  for u in netz_e.urls[w_e + 1:])
    pruefe(ex is None and 0 < grenze < mit.get("gesamt", 0)
           and zellen2 == grenze,
           "echter Lauf mit Grenze %d holt in Pass 2 genau so viele Zellen (%d)"
           % (grenze, zellen2))
    pruefe("Pass 2 GEDECKELT" in log_e, "und meldet das laut")
    z_e = zahlen(zustand(e))
    pruefe(z_e.keys() == z_ref.keys(), "alle Abende werden trotzdem gerechnet")
    erster = sorted(z_ref)[0]
    pruefe(z_e.get(erster) == z_ref[erster],
           "der naechste Abend rechnet wie ohne Deckel")
    pruefe(any(z_e.get(t) != z_ref[t] for t in sorted(z_ref)[1:]),
           "ein spaeterer Abend rechnet ohne Advektion (der Deckel hat gegriffen)")

    print("\n=== f) Minutenlimit verbraucht keine Netzversuche (alarm#10)")

    def hole_gegen(antworten):
        rest = list(antworten)
        n = {"n": 0}

        def falsch(u, timeout=None):
            n["n"] += 1
            x = rest.pop(0)
            if isinstance(x, BaseException):
                raise x
            class A:
                def __enter__(s): return io.BytesIO(x)
                def __exit__(s, *y): return False
            return A()
        alt = (alarm.urllib.request.urlopen, alarm.time.sleep)
        alarm.urllib.request.urlopen, alarm.time.sleep = falsch, lambda s: None
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                return alarm._hole("http://pruefstand"), n["n"]
        except BaseException as ex:                      # noqa: BLE001
            return ex, n["n"]
        finally:
            alarm.urllib.request.urlopen, alarm.time.sleep = alt

    def h429(grund):
        return urllib.error.HTTPError("http://pruefstand", 429, "x", {},
                                      io.BytesIO(json.dumps(
                                          {"reason": grund}).encode()))
    netzfehler = urllib.error.URLError("weg")
    erg, n = hole_gegen([netzfehler, netzfehler, netzfehler,
                         h429("Minutely API request limit exceeded"),
                         b'{"gut": 1}'])
    pruefe(erg == {"gut": 1} and n == 5,
           "drei Netzfehler, dann Minutenlimit: wird abgewartet (%r, %d)"
           % (erg, n))
    erg, n = hole_gegen([h429("Too many concurrent requests"), b'{"gut": 2}'])
    pruefe(erg == {"gut": 2} and n == 2,
           "'Too many concurrent requests' wird abgewartet (%r, %d)" % (erg, n))
    erg, n = hole_gegen([h429("Minutely API request limit exceeded")
                         for _ in range(9)])
    pruefe(isinstance(erg, alarm.Kontingent) and erg.sperre_bis is None
           and n == alarm.MINUTENWARTEN + 1,
           "aber nicht endlos: nach %d Wartezeiten Abbruch ohne Sperre (%d)"
           % (alarm.MINUTENWARTEN, n))

    print("\n=== g) Cachepflege")
    g = neue_basis()
    aufzuraeumen.append(g)
    wurzel = os.path.join(g, "daten", "cache", "abruf")
    for name in ("20261006T0000Z", "20261008T1800Z"):
        os.makedirs(os.path.join(wurzel, name))
    lauf(g, "2026-10-09T14:30", INIT_A, Netz())
    pruefe(not os.path.exists(os.path.join(wurzel, "20261006T0000Z")),
           "Modelllauf von vor drei Tagen ist geraeumt")
    pruefe(os.path.exists(os.path.join(wurzel, "20261008T1800Z")),
           "Modelllauf von gestern bleibt")
    ordner = os.path.join(wurzel, "20261009T0000Z", "20261009")
    bloecke = sorted(os.listdir(ordner)) if os.path.isdir(ordner) else []
    pruefe(len(bloecke) == n_ref,
           "je Block eine Cachedatei (%d von %d)" % (len(bloecke), n_ref))
    if bloecke:
        with open(os.path.join(ordner, bloecke[0]), "w") as f:
            f.write("[]")             # formgueltig, aber leer
        netz_g = Netz()
        ex, _ = lauf(g, "2026-10-09T14:40", INIT_A, netz_g)
        pruefe(ex is None and len(netz_g.urls) == 1,
               "ein leerer Cacheblock wird neu geholt, nicht still "
               "uebernommen (%d Aufruf)" % len(netz_g.urls))

    print("\n=== h) Derselbe Modelllauf am naechsten UTC-Tag: kein Block "
          "vom Vortag")
    # Gate 09.10.2026: Hourly-429 um 23:50 mitten in Pass 2, Folgelauf um
    # 00:10 auf demselben Modelllauf.  Ohne den Abruftag im Schluessel kam
    # vor allem der Windblock (URL nur an der Heimatzelle) aus dem Cache -
    # mit der Zeitachse des Vortags; die Advektion rechnete still falsch.
    init_h = "2026-10-09T06:00+00:00"
    nach = "2026-10-10T00:10"
    ref_h = neue_basis()
    aufzuraeumen.append(ref_h)
    netz_hr = NetzAbruftag("2026-10-10T00:00")
    ex, _ = lauf(ref_h, nach, init_h, netz_hr, jetzt=nach)
    z_hr = zahlen(zustand(ref_h))
    w_h = next(i for i, u in enumerate(netz_hr.urls) if ist_wind(u))
    pruefe(ex is None and len(z_hr) >= 3,
           "Referenz ohne Cache am 10.10. rechnet %d Abende" % len(z_hr))
    h = neue_basis()
    aufzuraeumen.append(h)
    netz_h1 = NetzAbruftag("2026-10-09T00:00", fehler_bei=w_h + 3,
                           grund="Hourly API request limit exceeded.")
    ex, _ = lauf(h, "2026-10-09T23:50", init_h, netz_h1,
                 jetzt="2026-10-09T23:50")
    pruefe(isinstance(ex, alarm.Kontingent),
           "Lauf um 23:50 bricht in Pass 2 am Stundenlimit ab")
    netz_h2 = NetzAbruftag("2026-10-10T00:00")
    ex, log_h2 = lauf(h, nach, init_h, netz_h2, jetzt=nach)
    pruefe(ex is None and sorted(netz_h2.urls) == sorted(netz_hr.urls),
           "Folgelauf um 00:10 holt genau die Bloecke des ungecachten Laufs "
           "neu, den Windblock eingeschlossen (%d von %d, Wind: %s)"
           % (len(netz_h2.urls), len(netz_hr.urls),
              any(ist_wind(u) for u in netz_h2.urls)))
    pruefe(zahlen(zustand(h)) == z_hr,
           "und rechnet dieselben Zahlen wie der ungecachte Lauf")
    netz_h3 = NetzAbruftag("2026-10-10T00:00")
    lauf(h, "2026-10-10T00:20", init_h, netz_h3, jetzt="2026-10-10T00:20")
    pruefe(len(netz_h3.urls) == 0,
           "am selben UTC-Tag greift der Cache wieder (%d Aufrufe)"
           % len(netz_h3.urls))

    for d in aufzuraeumen:
        shutil.rmtree(d, ignore_errors=True)

    print("")
    if fehler:
        print("FEHLGESCHLAGEN: %d" % len(fehler))
        raise SystemExit(1)
    print("alle Pruefungen bestanden")


if __name__ == "__main__":
    main()
