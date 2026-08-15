"""Holt Bewertungen vom ntfy-Topic und traegt sie in die Zustandsdatei ein.

WICHTIG zur Taktung: ntfy.sh haelt Nachrichten nur begrenzt vor (Standard
12 Stunden).  Ein taeglicher Lauf verliert also Bewertungen, die mehr als
einen halben Tag alt sind.  Dieses Skript gehoert deshalb alle 3 Stunden in
den Cron, nicht einmal taeglich.

Der Rueckkanal ist bewusst blind: die Bewertungsseite zeigt keine Prognose.
Wer vorher auf die Prognoseseite schaut, ist geankert - dagegen hilft nur
Disziplin, nicht Technik.  Deshalb bleibt der ankerfreie Fotoarchiv-Test die
eigentliche Validierung, und die Bewertungen sind Zusatzsignal mit bekanntem
Bias.
"""
import argparse
import json
import os
import urllib.request

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def hole(topic, seit="12h"):
    u = "https://ntfy.sh/%s/json?poll=1&since=%s" % (topic, seit)
    with urllib.request.urlopen(u, timeout=60) as f:
        roh = f.read().decode("utf-8")
    aus = []
    for zeile in roh.splitlines():
        if not zeile.strip():
            continue
        try:
            n = json.loads(zeile)
        except ValueError:
            continue
        if n.get("event") != "message":
            continue
        m = _nutzlast(n.get("message", ""))
        if m is not None:
            aus.append((n["time"], m))
    return aus


def _nutzlast(text):
    """Die Maschinendaten aus einer Bewertungsnachricht.

    Seit 15.08.2026 traegt die Nachricht ZWEI Leser: Zeile 1 ist der Text,
    den Andre auf dem Sperrbildschirm sieht, Zeile 2 das JSON fuer dieses
    Skript.  Vorher war die ganze Nachricht JSON - deshalb wird von hinten
    nach vorn probiert, damit alte Eintraege im Topic weiter gelesen werden.
    """
    zeilen = [z for z in (text or "").splitlines() if z.strip()]
    for z in reversed(zeilen):
        try:
            m = json.loads(z)
        except ValueError:
            continue
        if isinstance(m, dict) and m.get("tag"):
            return m
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seit", default="12h")
    ap.add_argument("--konfig", default=os.path.join(BASIS, "konfig.json"))
    a = ap.parse_args()

    with open(a.konfig) as f:
        kfg = json.load(f)
    zpfad = os.path.join(BASIS, "daten", "zustand.json")
    zustand = {}
    if os.path.exists(zpfad):
        with open(zpfad) as f:
            zustand = json.load(f)

    neu = 0
    for ort in kfg["orte"]:
        topic = ort.get("ntfy_bewertung")
        if not topic:
            continue
        eintrag = zustand.setdefault(ort["name"], {"abende": {}, "alarme": {}})
        for zeit, m in hole(topic, a.seit):
            if m.get("ort") and m["ort"] != ort["name"]:
                continue
            tag, note = m.get("tag"), m.get("note")
            if not tag or note is None:
                continue
            abend = eintrag["abende"].setdefault(tag, {})
            # Spaetere Bewertung desselben Abends ueberschreibt - eine
            # Korrektur ist gewollt, ein Duplikat schadet nicht.  Genau
            # deshalb darf die Seite beliebig oft nachsenden (T-0023).
            if abend.get("bewertung") != note:
                neu += 1
            abend["bewertung"] = note
            abend["bewertung_zeit"] = zeit
            # T-0021: kam die Note auf Aufforderung, nach einem Alarm, oder
            # spontan?  Ohne diese Unterscheidung ist die Stichprobe nicht
            # auswertbar - wer nur nach Alarmen bewertet, liefert keine
            # Basisrate, sondern dieselbe Presence-only-Falle wie das Album.
            if m.get("anlass"):
                abend["bewertung_anlass"] = m["anlass"]
            if m.get("erfasst"):
                # Zeitpunkt am GERAET, nicht der Empfang bei ntfy.  Bei einer
                # nachgesendeten Bewertung liegen die beiden Tage auseinander,
                # und nur der erste sagt, wann tatsaechlich bewertet wurde.
                abend["bewertung_erfasst"] = m["erfasst"]
    with open(zpfad, "w") as f:
        json.dump(zustand, f, indent=1)

    gesamt = sum(1 for o in zustand.values()
                 for v in o.get("abende", {}).values()
                 if v.get("bewertung") is not None)
    print("neu oder geaendert: %d   Bewertungen gesamt: %d" % (neu, gesamt))
    if gesamt:
        noten = [v["bewertung"] for o in zustand.values()
                 for v in o.get("abende", {}).values()
                 if v.get("bewertung") is not None]
        for n in range(0, 6):
            k = noten.count(n)
            print("   %s %2d  %s" % ("nicht gesehen" if n == 0 else "Note %d" % n,
                                     k, "#" * k))


if __name__ == "__main__":
    main()
