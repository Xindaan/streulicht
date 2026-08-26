"""T-0021: Bewertungsaufforderung an JEDEM Abend, unabhaengig vom Alarm.

WARUM DAS DER WICHTIGSTE TEIL DES LIVEGANGS IST.  Wer nur nach einem Alarm
bewertet, erzeugt genau die Falle, an der der erste Abbruchtest gescheitert
ist: eine Stichprobe ohne Negative.  Aus "an 14 % der Alarmabende war es
schoen" laesst sich ohne Basisrate nichts folgern - vielleicht sind 14 % aller
Abende schoen.  Erst die bewerteten NICHT-Alarmabende machen aus dem
Rueckkanal eine Messung.

Rechnung dazu: bei rund 9-18 Ausloesungen im Jahr liefert ein alarmgebundener
Rueckkanal einstellig viele bewertete Abende pro Saison.  Taegliche
Aufforderung liefert rund 245.  Derselbe Aufwand, Faktor 15.

TAKTUNG.  Der Cron laeuft stuendlich; das Skript prueft selbst, ob der
Sonnenuntergang gerade im Fenster liegt.  Grund: die Sonnenuntergangszeit
wandert ueber das Jahr um mehr als vier Stunden, eine feste Cron-Zeit passt
hoechstens im Fruehling.

IDEMPOTENZ.  Je (Ort, Abend) hoechstens eine Aufforderung, vermerkt in
daten/zustand.json.  Ein stuendlicher Cron darf also gefahrlos mehrfach ins
Fenster fallen.

STICHPROBE STATT TAEGLICH.  Wer nicht jeden Abend gefragt werden will, setzt
`bewertung_tage_pro_woche` in konfig.json.  Die Auswahl ist deterministisch
aus Datum und Ortsname gezogen - dieselbe Woche ergibt immer dieselben Tage,
und die Auswahl ist damit nachvollziehbar statt zufaellig.  WICHTIG: das
Ergebnis bleibt eine Zufallsstichprobe der Abende, NICHT eine Auswahl nach
Wetter - sonst waere die Basisrate wieder verzerrt.
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sonnen.geometrie import sonnenuntergang  # noqa: E402
from zustandsdatei import aktualisiere, lade  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NTFY = "https://ntfy.sh"
# Fenster nach Sonnenuntergang, in dem gefragt wird.  Frueher waere zu frueh
# (das Farbenspiel kommt erst nach dem Untergang - Cirrus glueht rund 28 min
# weiter), spaeter verliert man Leute an den Abend.
VERSATZ_MIN, FENSTER_MIN = 30, 75   # 75 statt 60: ein verspaeteter Cron
#                                     trifft sonst knapp daneben; Doppelte
#                                     faengt die Idempotenz ab.


def im_fenster(jetzt_utc, tag, breite, laenge):
    """Liegt jetzt im Aufforderungsfenster des Abends? (Minuten seit Start)"""
    stunde, _ = sonnenuntergang(tag, breite, laenge)
    if stunde is None:
        return None
    su = datetime.combine(tag, datetime.min.time(), tzinfo=timezone.utc) \
        + timedelta(hours=stunde)
    start = su + timedelta(minutes=VERSATZ_MIN)
    d = (jetzt_utc - start).total_seconds() / 60.0
    return d if 0 <= d <= FENSTER_MIN else None


def gezogen(ort_name, tag, pro_woche):
    """Deterministische Wochenstichprobe: welche Tage der Woche werden gefragt?

    Der Schluessel ist (Ortsname, ISO-Jahr, ISO-Woche) - fuer dieselbe Woche
    kommt immer dieselbe Auswahl heraus, auch nach einem Neustart und ohne
    gespeicherten Zustand.
    """
    if not pro_woche or pro_woche >= 7:
        return True
    jahr, woche, wochentag = tag.isocalendar()
    h = hashlib.sha256(("%s|%d|%d" % (ort_name, jahr, woche)).encode()).digest()
    # Wochentage 1..7 nach dem Hash sortieren, die ersten `pro_woche` nehmen.
    ordnung = sorted(range(1, 8), key=lambda d: h[d])
    return wochentag in ordnung[:pro_woche]


def sende(topic, titel, text, klick=None):
    kopf = {"Title": titel.encode("utf-8"), "Tags": "sunny", "Priority": "low"}
    if klick:
        kopf["Click"] = klick
    r = urllib.request.Request("%s/%s" % (NTFY, topic),
                               data=text.encode("utf-8"), headers=kopf)
    with urllib.request.urlopen(r, timeout=30) as f:
        f.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trocken", action="store_true")
    ap.add_argument("--konfig", default=os.path.join(BASIS, "konfig.json"))
    ap.add_argument("--jetzt", help="ISO-Zeit UTC statt jetzt (fuer Tests)")
    a = ap.parse_args()

    with open(a.konfig) as f:
        kfg = json.load(f)
    zpfad = os.path.join(BASIS, "daten", "zustand.json")
    # T-0058: Nur LESEN, um zu entscheiden, wer dran ist.  Gebucht wird ganz
    # am Ende unter Sperre gegen den frischen Stand - der Versand liegt
    # dazwischen und darf die Datei nicht blockieren.
    zustand = lade(zpfad)

    jetzt = (datetime.fromisoformat(a.jetzt).replace(tzinfo=timezone.utc)
             if a.jetzt else datetime.now(timezone.utc))
    basis_url = (kfg.get("seiten_basis") or "").rstrip("/")
    gesendet = 0
    gebucht = []                  # [(ort, tag)] - was wirklich rausging

    for ort in kfg["orte"]:
        topic = ort.get("ntfy_bewertung")
        if not topic:
            continue
        zone = ZoneInfo(ort.get("zeitzone", "UTC"))
        # Der Abend ist der LOKALE Tag - um 22 Uhr Berlin ist es UTC schon
        # derselbe Tag, im Winter aber nicht immer.
        tag = jetzt.astimezone(zone).date()
        d = im_fenster(jetzt, tag, ort["breite"], ort["laenge"])
        if d is None:
            # auch den Vortag pruefen: kurz nach Mitternacht lokal
            tag = tag - timedelta(days=1)
            d = im_fenster(jetzt, tag, ort["breite"], ort["laenge"])
        if d is None:
            print("   %s: ausserhalb des Fensters" % ort["name"])
            continue

        eintrag = zustand.setdefault(ort["name"], {"abende": {}, "alarme": {}})
        erinnert = eintrag.setdefault("erinnerungen", {})
        if str(tag) in erinnert:
            print("   %s %s: schon aufgefordert" % (ort["name"], tag))
            continue
        if not gezogen(ort["name"], tag, kfg.get("bewertung_tage_pro_woche")):
            print("   %s %s: nicht in der Wochenstichprobe" % (ort["name"], tag))
            continue

        # ?a=2 statt ?a=1, wenn fuer DIESEN Abend ein Alarm rausging.
        #
        # Ohne das konnte der Anlass "alarm" nie entstehen: gesetzt wird er
        # allein ueber diesen Parameter, und der Alarm selbst geht Stunden
        # VOR dem Sonnenuntergang raus (seit T-0041 sonnenuntergangsrelativ,
        # davor fest um 7:30) - zu beiden Zeitpunkten bewertet niemand einen
        # Sonnenuntergang, der noch nicht stattgefunden hat.  Die
        # Unterscheidung ist aber der Kern der Auswertung: bewertet Andre
        # nach einem Alarm systematisch anders als an einem gewoehnlichen
        # Abend, ist die Bewertungsreihe verzerrt und muss getrennt
        # ausgewertet werden.
        alarmiert = str(tag) in eintrag.get("alarme", {})
        klick = ("%s/bewerten-%s.html?a=%d"
                 % (basis_url, ort["name"], 2 if alarmiert else 1)
                 if basis_url else None)
        titel = "Wie war er?"
        text = ("Sonnenuntergang %s ist durch. Eine Zahl von 1 bis 5 - "
                "und ein Foto nach Westen, wenn Du magst." % ort["anzeige"])
        if a.trocken:
            print("   [trocken] %s %s (+%.0f min): %s | %s"
                  % (ort["name"], tag, d, text, klick or "kein Link"))
            continue
        # T-0055, gleiche Klasse wie in alarm.py: ein Versandfehler darf die
        # Schleife nicht abbrechen.  Bei EINEM Ort war das folgenlos (nichts
        # gesendet, nichts gebucht, naechster Tick versucht es erneut) - ab
        # dem zweiten geht die Buchung des ERSTEN verloren, und der bekommt
        # seine Aufforderung ein zweites Mal.  Gebucht wird weiterhin nur,
        # was wirklich rausging.
        try:
            sende(topic, titel, text, klick)
        except Exception as ex:
            print("   %s %s: Versand fehlgeschlagen (%s: %s) - nicht gebucht"
                  % (ort["name"], tag, type(ex).__name__, ex))
            continue
        erinnert[str(tag)] = jetzt.isoformat(timespec="seconds")
        gebucht.append((ort["name"], str(tag)))
        gesendet += 1
        print("   %s %s: aufgefordert" % (ort["name"], tag))

    if not a.trocken and gebucht:
        def buchen(z):
            # Nur HINZUFUEGEN, nie ueberschreiben: was ein anderer Agent
            # inzwischen geschrieben hat, bleibt unangetastet.
            zeit = jetzt.isoformat(timespec="seconds")
            for name, tag in gebucht:
                e = z.setdefault(name, {"abende": {}, "alarme": {}})
                e.setdefault("erinnerungen", {})[tag] = zeit
        aktualisiere(zpfad, buchen)   # T-0051 atomar, T-0058 unter Sperre
    print("Aufforderungen gesendet: %d" % gesendet)


if __name__ == "__main__":
    main()
