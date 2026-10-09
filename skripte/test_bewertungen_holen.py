"""Der Bewertungs-Poller echt ausgefuehrt: ntfy-Parser und die vier Eingangswaechter.

T-0079 (Review 09.10.2026: tests#7, bewertung#8).  Bis hierher ersetzten ALLE
Tests (`test_bewertung_nutzlast.py`, `test_zustandsdatei.py`) `hole()` samt
ntfy-Antwort durch ein Lambda, das schon fertige Nutzlasten liefert.  Der
Parser - JSON-Zeilen lesen, Ereignisse filtern, Klickziel gegen Nachrichten-
text, `plausibel()` - lief nie.  Ebenso ungeschuetzt waren vier Eingangs-
waechter in `main()`; entfernte man einen, blieb jede Suite gruen.

Hier laeuft der PRODUKTIONSCODE: `urllib.request.urlopen` liefert eine erfundene
ntfy-Antwort (JSON-Zeilen), `hole()` und `main()` laufen echt, danach wird der
Zustand gelesen.  "Jetzt" ist fest (kein date.today()/datetime.now() im Test):
bewertungen_holen bekommt eine Uhr-Attrappe fuer `date.today()` und
`datetime.now()`.  Kein Netz.

Wert-Huerde je Block (welche Regression macht ihn rot):
* Parser: hole() wird auf Epochen-Zeit, Ereignisfilter oder Klickziel-Vorrang
  umgebaut - ohne diesen Block liefe der ntfy-Weg nur im Betrieb.
* Waechter 1 sonnenuntergang_vorbei: ein Abend wird bewertet, bevor er
  stattgefunden hat (18.08.2026: Note um 04:26 fuer 18:00).
* Waechter 2 plausibel: ein Phantomabend (2099-01-01, vor dem Projektstart,
  kein ISO-Datum) wird in die Zustandsdatei geholt - und weil ntfy 12 h
  vorhaelt, bei JEDEM Abruf wieder.  Der Abend VOR dem Projektstart ist der
  Fall, den Waechter 1 NICHT faengt (er liegt in der Vergangenheit).
* Waechter 3 Selbsttest-Filter: eine Probe-Note ueberschreibt Andres echte.
* Waechter 4 Ort-Filter: die Note eines Ortes landet beim anderen.

Lauf:  .venv/bin/python3 skripte/test_bewertungen_holen.py
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import bewertungen_holen as bh  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


# ----------------------------------------------------------------------
# feste Uhr
# ----------------------------------------------------------------------
HEUTE = date(2026, 9, 20)
# Sonnenuntergaenge am 20.09.2026 (sonnen.geometrie): Berlin 17:10 UTC,
# Bilbao 18:13 UTC.
VOR_ALLEM = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
ZWISCHEN = datetime(2026, 9, 20, 17, 40, tzinfo=timezone.utc)   # nur Berlin
NACH_ALLEM = datetime(2026, 9, 20, 22, 0, tzinfo=timezone.utc)


def uhr(jetzt):
    """Ersatz fuer date/datetime in bewertungen_holen (feste Zeit)."""
    class FesterTag(date):
        @classmethod
        def today(cls):
            return jetzt.date()

    class FesteUhr(datetime):
        @classmethod
        def now(cls, tz=None):
            return jetzt if tz is None else jetzt.astimezone(tz)

    return FesterTag, FesteUhr


# ----------------------------------------------------------------------
# erfundene ntfy-Antwort
# ----------------------------------------------------------------------
EPOCHE = 1789948800        # 2026-09-21 00:00 UTC, bewusst eine ZAHL (wie ntfy)


def klickziel(m):
    return "https://x.invalid/bewerten.html?d=" + urllib.parse.quote(
        json.dumps(m))


def ntfy(m, wie="klick", zeit=EPOCHE):
    """Eine ntfy-Zeile (JSON) fuer die Nutzlast `m`.
    wie: klick (seit 16.08.), zwei (Text + JSON-Zeile), alt (nur JSON)."""
    n = {"id": "abc", "time": zeit, "event": "message", "topic": "t"}
    if wie == "klick":
        n["message"] = "Berlin 19.09.: Note 4"
        n["click"] = klickziel(m)
    elif wie == "zwei":
        n["message"] = "Berlin 19.09.: Note 4\n" + json.dumps(m)
    else:
        n["message"] = json.dumps(m)
    return json.dumps(n)


class Antwort:
    def __init__(self, text):
        self.roh = text.encode("utf-8")

    def read(self):
        return self.roh

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def mit_antwort(text, fn):
    """fn() mit urlopen = feste Antwort.  -> (Ergebnis, [(url, timeout)])."""
    aufrufe = []

    def urlopen(u, timeout=None, **kw):
        aufrufe.append((u, timeout))
        return Antwort(text(u) if callable(text) else text)

    echt = urllib.request.urlopen
    urllib.request.urlopen = urlopen
    try:
        return fn(), aufrufe
    finally:
        urllib.request.urlopen = echt


def mit_uhr(jetzt, fn):
    alt = (bh.date, bh.datetime)
    bh.date, bh.datetime = uhr(jetzt)
    try:
        return fn()
    finally:
        bh.date, bh.datetime = alt


def holen(text, topic="t", seit="12h", jetzt=NACH_ALLEM):
    """bh.hole() echt gegen eine feste ntfy-Antwort.  -> (Liste, Aufrufe)."""
    return mit_uhr(jetzt, lambda: mit_antwort(
        text, lambda: bh.hole(topic, seit)))


G = str(NACH_ALLEM.date() - timedelta(days=1))      # 2026-09-19
OK = {"ort": "berlin", "tag": G, "note": 4}


# ----------------------------------------------------------------------
print("1. hole(): der ntfy-Parser, echt ausgefuehrt")
# ----------------------------------------------------------------------
antwort = "\n".join([
    json.dumps({"id": "o", "time": EPOCHE - 5, "event": "open", "topic": "t"}),
    "",
    "das ist kein JSON",
    # Ereignisse, die KEINE Nachricht sind, aber eine lesbare Nutzlast tragen
    # (harmloser Testkoerper waere eine leere Zeile): ohne den Ereignisfilter
    # kaemen sie als Noten durch.
    ntfy(dict(OK, note=0)).replace('"event": "message"',
                                   '"event": "message_delete"'),
    ntfy(dict(OK, note=0), wie="zwei").replace('"event": "message"',
                                               '"event": "keepalive"'),
    ntfy(dict(OK, note=1), wie="klick", zeit=EPOCHE + 1),
    json.dumps({"id": "k", "time": EPOCHE, "event": "keepalive"}),
    ntfy(dict(OK, note=2), wie="zwei", zeit=EPOCHE + 2),
    ntfy(dict(OK, note=3), wie="alt", zeit=EPOCHE + 3),
    json.dumps({"id": "l", "time": EPOCHE, "event": "message",
                "message": json.dumps([1, 2, 3])}),            # JSON, kein dict
    json.dumps({"id": "x", "time": EPOCHE, "event": "message",
                "message": "nur Text, kein JSON"}),
])
erg, aufrufe = holen(antwort, "mein-topic", "3h")
pruefe(len(aufrufe) == 1 and aufrufe[0][0] ==
       "https://ntfy.sh/mein-topic/json?poll=1&since=3h"
       and aufrufe[0][1] == 60,
       "Abruf: Topic und `seit` in der URL, Zeitgrenze 60 s (%s)" % (aufrufe,))
pruefe([m["note"] for _, m in erg] == [1, 2, 3],
       "alle drei Schreibweisen (Klickziel, Text+JSON, nur JSON) kommen "
       "durch, in Reihenfolge; open/keepalive/Muell/Liste/Text nicht "
       "(%s)" % [m["note"] for _, m in erg])
pruefe([z for z, _ in erg] == [EPOCHE + 1, EPOCHE + 2, EPOCHE + 3]
       and all(isinstance(z, int) for z, _ in erg),
       "die Zeit ist die Epochensekunde aus ntfy (Zahl), kein Text (%s)"
       % [z for z, _ in erg])
# Klickziel hat Vorrang vor dem Nachrichtentext
doppelt = json.dumps({
    "id": "d", "time": EPOCHE, "event": "message",
    "click": klickziel(dict(OK, note=5)),
    "message": "x\n" + json.dumps(dict(OK, note=1))})
erg, _ = holen(doppelt)
pruefe([m["note"] for _, m in erg] == [5],
       "steht die Nutzlast in Klickziel UND Text, gilt das Klickziel (%s)"
       % [m["note"] for _, m in erg])
pruefe(holen("")[0] == [], "leere Antwort: leere Liste")

print("\n2. Waechter 2 - plausibel(): kein Phantomabend (am Parser gemessen)")
heute_p = lambda tag: mit_uhr(NACH_ALLEM, lambda: bh.plausibel(tag))  # noqa: E731
pruefe(heute_p(G), "gestern ist plausibel")
pruefe(heute_p(str(HEUTE + timedelta(days=1))),
       "morgen ist plausibel (ein Tag Luft: Seite in Ortszeit, Poller in UTC)")
for tag, grund in ((str(HEUTE + timedelta(days=2)), "uebermorgen"),
                   ("2099-01-01", "2099-01-01 (der Testeintrag vom 15.08.)"),
                   ("2026-08-14", "ein Tag VOR dem Projektstart"),
                   ("20260919", "Kurzschreibweise"),
                   ("2026-13-45", "kein Datum"),
                   (None, "kein Text"), (20260919, "eine Zahl")):
    pruefe(not heute_p(tag), "%s wird verworfen" % grund)
pruefe(heute_p("2026-08-15"), "der Projektstart selbst (15.08.) ist erlaubt")
phantom = "\n".join(ntfy(dict(OK, tag=t), wie=w) for t, w in (
    ("2099-01-01", "klick"), ("2026-08-14", "zwei"), ("20260919", "alt"),
    (str(HEUTE + timedelta(days=2)), "klick")))
erg, _ = holen(phantom)
pruefe(erg == [], "hole() reicht keine dieser Phantomabende weiter (%d)"
       % len(erg))
erg, _ = holen(phantom + "\n" + ntfy(OK))
pruefe(len(erg) == 1 and erg[0][1]["tag"] == G,
       "Gegenprobe: derselbe Abruf MIT einem echten Abend liefert genau ihn")


# ----------------------------------------------------------------------
# main() mit echtem hole(), Zustand lesen
# ----------------------------------------------------------------------
ORTE = [
    {"name": "berlin", "anzeige": "Berlin", "breite": 52.52, "laenge": 13.405,
     "zeitzone": "Europe/Berlin", "ntfy_bewertung": "topic-berlin"},
    {"name": "bilbao", "anzeige": "Bilbao", "breite": 43.263, "laenge": -2.935,
     "zeitzone": "Europe/Madrid", "ntfy_bewertung": "topic-bilbao"},
]


def lauf(nachrichten, jetzt=NACH_ALLEM, orte=ORTE, vorbelegt=None,
         je_topic=None):
    """main() mit echtem hole().  `nachrichten`: ntfy-Zeilen fuer beide Topics
    (oder `je_topic` = {topic: Zeilen}).  -> (zustand, urls, ausgabe)."""
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "daten"))
    kp = os.path.join(d, "konfig.json")
    with open(kp, "w") as f:
        json.dump({"orte": orte}, f)
    zp = os.path.join(d, "daten", "zustand.json")
    start = vorbelegt or {o["name"]: {"abende": {}, "alarme": {}}
                          for o in orte}
    with open(zp, "w") as f:
        json.dump(start, f)

    def antwort_zu(u):
        topic = u.split("/")[3]
        return "\n".join((je_topic or {}).get(topic, nachrichten))

    alt = (bh.BASIS, bh.warte_auf_netz)
    bh.BASIS = d
    bh.warte_auf_netz = lambda *a, **k: None
    sicher, sys.argv = sys.argv, ["bewertungen_holen.py", "--konfig", kp]
    puffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(puffer):
            _, aufrufe = mit_uhr(jetzt, lambda: mit_antwort(
                antwort_zu, bh.main))
    finally:
        sys.argv = sicher
        bh.BASIS, bh.warte_auf_netz = alt
    with open(zp) as f:
        zustand = json.load(f)
    return zustand, [u for u, _ in aufrufe], puffer.getvalue()


def abend(zustand, ort, tag):
    return zustand.get(ort, {}).get("abende", {}).get(tag, {})


print("\n3. main() echt: eine gueltige Note kommt an (sonst prueft der Rest "
      "nichts)")
z, urls, aus = lauf([ntfy(dict(OK, anlass="aufgefordert",
                               erfasst="2026-09-19T19:30:00+02:00"))])
a = abend(z, "berlin", G)
pruefe(a.get("bewertung") == 4 and a.get("bewertung_zeit") == EPOCHE
       and a.get("bewertung_anlass") == "aufgefordert"
       and a.get("bewertung_erfasst") == "2026-09-19T19:30:00+02:00",
       "Note, Epochenzeit, Anlass und Geraetezeit stehen im Zustand (%s)" % a)
pruefe(abend(z, "bilbao", G) == {},
       "die Note mit ort=berlin steht NICHT bei bilbao")
pruefe(sorted(urls) == ["https://ntfy.sh/topic-berlin/json?poll=1&since=12h",
                        "https://ntfy.sh/topic-bilbao/json?poll=1&since=12h"],
       "je Ort wird das eigene Topic abgerufen (%s)" % sorted(urls))
orte_ohne = [dict(ORTE[0]), {k: v for k, v in ORTE[1].items()
                             if k != "ntfy_bewertung"}]
z, urls, aus = lauf([ntfy(OK)], orte=orte_ohne)
pruefe(urls == ["https://ntfy.sh/topic-berlin/json?poll=1&since=12h"],
       "ein Ort ohne Topic wird nicht abgerufen (%s)" % urls)

print("\n4. Waechter 1 - sonnenuntergang_vorbei(): kein Abend vor seinem "
      "Sonnenuntergang")
heute_tag = str(HEUTE)
nachricht = ntfy(dict(OK, tag=heute_tag, note=2))
z, _, aus = lauf([nachricht], jetzt=VOR_ALLEM)
pruefe(abend(z, "berlin", heute_tag) == {},
       "12:00 UTC am 20.09. (Sonnenuntergang 17:10): Note fuer HEUTE wird "
       "verworfen (%s)" % abend(z, "berlin", heute_tag))
pruefe("Sonnenuntergang war noch nicht" in aus,
       "und der Grund steht im Log (sonst koennte ein anderer Waechter "
       "ablehnen)")
pruefe(mit_uhr(VOR_ALLEM, lambda: bh.plausibel(heute_tag)),
       "Ursachenprobe: plausibel() laesst den Tag durch - es ist allein der "
       "Sonnenuntergangs-Waechter")
z, _, aus = lauf([nachricht], jetzt=NACH_ALLEM)
pruefe(abend(z, "berlin", heute_tag).get("bewertung") == 2,
       "22:00 UTC (Sonnenuntergang vorbei): dieselbe Note wird uebernommen")
z, _, aus = lauf([ntfy(dict(OK, note=2))], jetzt=VOR_ALLEM)
pruefe(abend(z, "berlin", G).get("bewertung") == 2,
       "ein Abend von GESTERN geht auch um 12:00 UTC durch")
# Der Waechter rechnet mit den Koordinaten des jeweiligen Ortes: um 17:40 UTC
# ist Berlin (17:10) vorbei, Bilbao (18:13) noch nicht.
ohne_ort = ntfy({"tag": heute_tag, "note": 3})
z, _, aus = lauf([ohne_ort], jetzt=ZWISCHEN)
pruefe(abend(z, "berlin", heute_tag).get("bewertung") == 3
       and abend(z, "bilbao", heute_tag) == {},
       "17:40 UTC: bei Berlin angenommen, bei Bilbao verworfen "
       "(Koordinaten je Ort)")

print("\n5. Waechter 2 - plausibel() im Lauf: Phantomabende bleiben draussen")
phantome = [ntfy(dict(OK, tag=t, note=5), wie=w) for t, w in (
    ("2099-01-01", "klick"), ("2026-08-14", "klick"), ("20260919", "zwei"),
    ("2026-09-22", "alt"))]
z, _, aus = lauf(phantome + [ntfy(OK)])
pruefe(sorted(z["berlin"]["abende"]) == [G],
       "nur der echte Abend steht im Zustand (%s)"
       % sorted(z["berlin"]["abende"]))
z, _, aus = lauf(phantome)
pruefe(z["berlin"]["abende"] == {} and z["bilbao"]["abende"] == {},
       "ohne echten Abend bleibt der Zustand leer - bei beiden Orten")
# der Abend vor dem Projektstart: Waechter 1 laesst ihn durch (er liegt in der
# Vergangenheit), nur plausibel() faengt ihn
pruefe(mit_uhr(NACH_ALLEM, lambda: bh.sonnenuntergang_vorbei(
    "2026-08-14", ORTE[0])),
       "Ursachenprobe: sonnenuntergang_vorbei() liesse 2026-08-14 durch")

print("\n6. Waechter 3 - Selbsttest-Filter: Probe-Noten sind keine Messdaten")
z, _, aus = lauf([ntfy(dict(OK, note=5, anlass="selbsttest"))])
pruefe(abend(z, "berlin", G) == {},
       "eine Selbsttest-Note legt keinen Abend an (%s)" % abend(z, "berlin", G))
echte_note = ntfy(dict(OK, note=3, anlass="aufgefordert"), zeit=EPOCHE)
probe = ntfy(dict(OK, note=5, anlass="selbsttest"), zeit=EPOCHE + 60)
z, _, aus = lauf([echte_note, probe])
pruefe(abend(z, "berlin", G).get("bewertung") == 3
       and abend(z, "berlin", G).get("bewertung_zeit") == EPOCHE,
       "und ueberschreibt eine echte Note NICHT, auch wenn sie spaeter "
       "kommt (%s)" % abend(z, "berlin", G))
z, _, aus = lauf([ntfy(dict(OK, note=5, anlass="alarm"))])
pruefe(abend(z, "berlin", G).get("bewertung") == 5,
       "Gegenprobe: dieselbe Note mit anderem Anlass kommt durch")

print("\n7. Waechter 4 - Ort-Filter: die Note gehoert dem Ort, fuer den sie "
      "gesendet wurde")
z, _, aus = lauf([ntfy(dict(OK, ort="bilbao", note=2))])
pruefe(abend(z, "bilbao", G).get("bewertung") == 2
       and abend(z, "berlin", G) == {},
       "ort=bilbao landet bei bilbao und nicht bei berlin (%s / %s)"
       % (abend(z, "bilbao", G), abend(z, "berlin", G)))
z, _, aus = lauf([ntfy(dict(OK, ort="berlin", note=5))],
                 je_topic={"topic-berlin": [ntfy(dict(OK, ort="berlin",
                                                      note=5))],
                           "topic-bilbao": [ntfy(dict(OK, ort="berlin",
                                                      note=1))]})
pruefe(abend(z, "berlin", G).get("bewertung") == 5
       and abend(z, "bilbao", G) == {},
       "auch im Topic des anderen Ortes gilt das Feld ort, nicht das Topic "
       "(%s / %s)" % (abend(z, "berlin", G), abend(z, "bilbao", G)))
z, _, aus = lauf([ntfy({"tag": G, "note": 3})])
pruefe(abend(z, "berlin", G).get("bewertung") == 3
       and abend(z, "bilbao", G).get("bewertung") == 3,
       "ohne Feld ort (alte Nachrichten) wird sie bei dem Ort uebernommen, "
       "dessen Topic sie lieferte")

print()
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
