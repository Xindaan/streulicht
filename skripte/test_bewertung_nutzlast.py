"""T-0052: die Bewertungs-Nutzlast wird geprueft, bevor sie Messdaten wird.

Das Bewertungs-Topic steht im Klartext in der ausgelieferten Seite
(`web/bewerten-berlin.html`) - das ist dokumentierte Absicht, es laesst sich
nicht verbergen.  Genau deshalb muss die Eingangsseite pruefen: wer die Seite
liest, kann per ntfy-POST beliebige Nachrichten schicken.  Bis zum 22.08.2026
prueefte `bewertungen_holen.py` nur das DATUM (`plausibel`) und ob `note`
nicht `None` ist.  Eine Note 99, `True` oder `"5"` lief unbesehen in die
Zustandsdatei - und damit in Trefferquote, Brier und Bilanzseite.

Der Test fuehrt `main()` mit gestubbtem ntfy-Abruf aus und liest danach den
Zustand.  Kein Quelltext-Match.

Lauf:  python3 skripte/test_bewertung_nutzlast.py
"""
import datetime as dt
import json
import os
import sys
import tempfile

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import bewertungen_holen as bh  # noqa: E402
import bisher  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


GESTERN = str(dt.date.today() - dt.timedelta(days=1))


def lauf(nachricht, vorbelegt=None):
    """`main()` mit EINER erfundenen ntfy-Nachricht.  Rueckgabe: der Abend."""
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "daten"), exist_ok=True)
    kfg = {"orte": [{"name": "berlin", "anzeige": "Berlin", "breite": 52.52,
                     "laenge": 13.405, "zeitzone": "Europe/Berlin",
                     "ntfy_bewertung": "topic-test"}]}
    kp = os.path.join(d, "konfig.json")
    with open(kp, "w") as f:
        json.dump(kfg, f)
    zp = os.path.join(d, "daten", "zustand.json")
    with open(zp, "w") as f:
        json.dump({"berlin": {"abende": ({GESTERN: vorbelegt} if vorbelegt
                                         else {}), "alarme": {}}}, f)
    alt_basis, alt_hole, alt_netz = bh.BASIS, bh.hole, bh.warte_auf_netz
    bh.BASIS = d
    bh.warte_auf_netz = lambda *a, **k: None
    bh.hole = lambda topic, seit="12h": [("2026-08-23T18:00:00Z", nachricht)]
    sicher, sys.argv = sys.argv, ["bewertungen_holen.py", "--konfig", kp]
    try:
        bh.main()
    finally:
        sys.argv = sicher
        bh.BASIS, bh.hole, bh.warte_auf_netz = alt_basis, alt_hole, alt_netz
    with open(zp) as f:
        return json.load(f)["berlin"]["abende"].get(GESTERN, {})


def note(**zusatz):
    m = {"ort": "berlin", "tag": GESTERN}
    m.update(zusatz)
    return m


print("T-0052  Validierung der Bewertungs-Nutzlast\n")

print("1. Gueltige Noten kommen durch (sonst prueft der Rest nichts)")
for n in (0, 1, 2, 3, 4, 5):
    pruefe(lauf(note(note=n)).get("bewertung") == n,
           "Note %d wird uebernommen" % n)

print("\n2. Unfug wird verworfen")
faelle = [
    (99, "ausserhalb 0..5 (99)"),
    (-1, "negativ (-1)"),
    (6, "knapp darueber (6)"),
    (3.7, "Gleitkomma (3.7)"),
    ("5", "Zeichenkette (\"5\")"),
    (True, "bool True - IST in Python ein int, faellt sonst durch"),
    (False, "bool False - saehe sonst aus wie \"nicht gesehen\""),
    ([5], "Liste"),
    ({"note": 5}, "verschachteltes Objekt"),
]
for wert, text in faelle:
    e = lauf(note(note=wert))
    pruefe("bewertung" not in e, "%s wird verworfen" % text)

print("\n3. Eine gueltige Note wird nicht von Unfug ueberschrieben")
alt = {"bewertung": 4, "bewertung_zeit": "2026-08-22T18:00:00Z"}
e = lauf(note(note=99), vorbelegt=dict(alt))
pruefe(e.get("bewertung") == 4, "die echte 4 steht noch da")
e = lauf(note(note=2), vorbelegt=dict(alt))
pruefe(e.get("bewertung") == 2, "eine gueltige Korrektur greift weiterhin")

print("\n4. Widerruf bleibt moeglich (T-0023 darf nicht kaputtgehen)")
e = lauf(note(anlass="widerruf"), vorbelegt=dict(alt))
pruefe("bewertung" not in e, "Widerruf loescht die Note")

print("\n5. Nebenfelder: Fremdtypen landen nicht im Zustand")
e = lauf(note(note=3, anlass=["alarm"]))
pruefe(not isinstance(e.get("bewertung_anlass"), list),
       "anlass als Liste wird nicht uebernommen")
e = lauf(note(note=3, erfasst={"x": 1}))
pruefe(not isinstance(e.get("bewertung_erfasst"), dict),
       "erfasst als Objekt wird nicht uebernommen")
e = lauf(note(note=3, anlass="alarm", erfasst="2026-08-22T19:00:00Z"))
pruefe(e.get("bewertung_anlass") == "alarm", "gueltiger anlass kommt durch")
pruefe(e.get("bewertung_erfasst") == "2026-08-22T19:00:00Z",
       "gueltiges erfasst kommt durch")

print("\n6. Die Bilanzseite ueberlebt Altbestand mit Fremdtypen")
# Zweite Verteidigungslinie: was vor dem Fix in die Datei gelaufen ist,
# liegt noch darin.  bisher.py formatiert mit %d und vergleicht k < note -
# eine Zeichenkette liess frueher den SEITENBAU sterben, also den
# 10-Minuten-Agenten, nicht nur diese eine Karte.
for wert, text in ((99, "Note 99"), ("5", "Note als Zeichenkette"),
                   (True, "Note True"), (None, "Note None")):
    try:
        h = bisher.karte({"tag": GESTERN, "note": wert, "kopf": "Sa 22.08.",
                          "zeile": "Test"})
        pruefe(isinstance(h, str) and "<article" in h,
               "%s laesst den Seitenbau nicht sterben" % text)
    except Exception as ex:
        pruefe(False, "%s laesst den Seitenbau sterben: %s"
               % (text, type(ex).__name__))

print()
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
