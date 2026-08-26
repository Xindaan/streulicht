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
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from netz import warte_auf_netz  # noqa: E402
from zustandsdatei import aktualisiere  # noqa: E402

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
        m = _nutzlast_klick(n.get("click", "")) or _nutzlast(n.get("message", ""))
        if m is not None:
            aus.append((n["time"], m))
    return aus


def _nutzlast_klick(url):
    """Maschinendaten aus dem Klickziel - seit 16.08.2026 der Transportweg.

    Der Nachrichtenkoerper ist ANZEIGE, kein Transport: iOS zeigt ihn ganz,
    also stand dort erst rohes JSON und danach Text plus JSON - beides falsch.
    `click` wird von ntfy mitgefuehrt, beim Abholen zurueckgegeben und im
    Sperrbildschirm NICHT dargestellt.
    """
    if not url or "?d=" not in url:
        return None
    roh = urllib.parse.unquote(url.split("?d=", 1)[1])
    try:
        m = json.loads(roh)
    except ValueError:
        return None
    return m if isinstance(m, dict) and plausibel(m.get("tag")) else None


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
        if isinstance(m, dict) and plausibel(m.get("tag")):
            return m
    return None


# Vor diesem Tag gab es das Projekt nicht; danach kann kein Abend liegen,
# der schon bewertet waere.
ERSTER_ABEND = date(2026, 8, 15)


def sonnenuntergang_vorbei(tag, ort, jetzt=None):
    """Hat der Sonnenuntergang dieses Abends schon stattgefunden?

    Ein Riegel gegen genau den Fall vom 18.08.2026: eine Bewertung traf um
    04:26 ein und war fuer den 18. datiert - fuer einen Abend, der erst
    16 Stunden spaeter kommen sollte.  Die Seite datiert seitdem nach dem
    letzten VERGANGENEN Sonnenuntergang; dieser Riegel faengt ab, was aus
    alten, im Cache liegenden Seiten noch nachkommt.

    Bewusst hier UND dort: die Seite kann veraltet sein, der Poller nicht.
    """
    from sonnen.geometrie import sonnenuntergang
    try:
        d = date.fromisoformat(tag)
    except (TypeError, ValueError):
        return False
    std, _ = sonnenuntergang(d, ort["breite"], ort["laenge"])
    if std is None:
        return True                       # Polarnacht: nichts zu pruefen
    su = (datetime.combine(d, time(0), timezone.utc)
          + timedelta(hours=std))
    return su <= (jetzt or datetime.now(timezone.utc))


def plausibel(tag):
    """Ist `tag` ein Abend, den es geben kann?

    Ohne diese Pruefung schleust jede verstuemmelte oder versehentlich
    gesendete Nachricht einen Phantomabend in die Zustandsdatei - und weil
    ntfy rund 12 h vorhaelt, holt ihn JEDER weitere Abruf erneut herein.
    Genau so ist am 15.08.2026 ein Testeintrag mit dem Datum 2099-01-01
    dreimal zurueckgekommen, nachdem er von Hand entfernt worden war.
    """
    if not isinstance(tag, str):
        return False
    try:
        d = date.fromisoformat(tag)
    except ValueError:
        return False
    # Ein Tag Luft nach vorn: die Seite rechnet in Ortszeit, der Poller in UTC.
    return ERSTER_ABEND <= d <= date.today() + timedelta(days=1)


# Was die Bewertungsseite ueberhaupt senden kann: fuenf Notenknoepfe und
# "Nicht gesehen" (0).  `anlass` entsteht allein aus dem URL-Parameter ?a=1/2
# der Erinnerung.  Alles andere ist nicht von der Seite gekommen.
NOTEN = frozenset(range(0, 6))
ANLAESSE = frozenset(("aufgefordert", "alarm"))


def gueltige_note(note):
    """Ist `note` eine Note, die die Bewertungsseite senden koennte?

    T-0052.  Bis zum 22.08.2026 wurde hier nur gegen `None` geprueft - das
    Topic steht aber im Klartext in jeder ausgelieferten Seite, und wer sie
    liest, kann per ntfy-POST beliebige Werte schicken.  Eine Note 99 lief
    unbesehen in die Zustandsdatei, `bisher.py` rendert daraus "99 von 5" mit
    vollem Balken, und jede Auswertung (Trefferquote, Brier) rechnet danach
    auf vergifteten Labels.  Stille Datenkorruption im Kern der Messung.

    `isinstance(note, bool)` MUSS zuerst stehen: in Python ist `True` ein
    `int` mit dem Wert 1 und `False` einer mit 0 - ohne diese Zeile saehe ein
    gesendetes `false` aus wie die gueltige Antwort "nicht gesehen".

    EHRLICH ZUM RESTRISIKO: das haelt Unfug und Versehen ab, keinen Willens-
    angreifer.  Wer das Topic kennt, kann weiterhin eine PLAUSIBLE Note fuer
    einen vergangenen Abend setzen und die echte ueberschreiben.  Dagegen
    hilft nur Authentifizierung, und die Seite kann kein Geheimnis tragen -
    sie ist statisch und oeffentlich.  Diese Grenze ist bekannt und
    akzeptiert (siehe konfig.json, "_hinweis").
    """
    return not isinstance(note, bool) and isinstance(note, int) \
        and note in NOTEN


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seit", default="12h")
    ap.add_argument("--konfig", default=os.path.join(BASIS, "konfig.json"))
    a = ap.parse_args()

    # Erst Netz, dann rechnen: der Rechner kann gerade erst
    # aufgewacht sein (siehe skripte/netz.py).
    warte_auf_netz()

    with open(a.konfig) as f:
        kfg = json.load(f)
    zpfad = os.path.join(BASIS, "daten", "zustand.json")

    # T-0058: der ntfy-Abruf steht VOR der Sperre.  Ihn darin zu halten hiesse,
    # den Alarmlauf fuer die Dauer eines Netzabrufs zu blockieren - und der
    # Abruf braucht den Zustand gar nicht.
    post = []
    for ort in kfg["orte"]:
        topic = ort.get("ntfy_bewertung")
        if topic:
            post.append((ort, hole(topic, a.seit)))

    zaehler = {"neu": 0}

    def eintragen(zustand):
        neu = 0
        for ort, nachrichten in post:
            eintrag = zustand.setdefault(ort["name"],
                                         {"abende": {}, "alarme": {}})
            for zeit, m in nachrichten:
                if m.get("ort") and m["ort"] != ort["name"]:
                    continue
                # Selbsttests gehoeren nicht in die Messdaten.  Zweimal am
                # 15./16.08. habe ich beim Vorfuehren echte Noten ins
                # Produktivtopic geschickt - einmal mit heutigem Datum, was
                # Andres eigene Bewertung ueberschrieben haette.  ntfy haelt
                # rund 12 h vor, ein Loeschen im Zustand allein reicht also
                # nicht: der naechste Abruf holt sie zurueck.
                if m.get("anlass") == "selbsttest":
                    continue
                # WIDERRUF: loescht die Bewertung des Tages.  Ueberspringen allein
                # genuegt nicht - der Poller liest bei jedem Lauf ALLE Nachrichten
                # des Fensters chronologisch, eine falsche aeltere setzt die Note
                # also immer wieder neu.  Nur ein spaeterer Widerruf kommt dagegen
                # an.  Gebraucht am 16.08., als ein Selbsttest mit heutigem Datum
                # im Produktivtopic landete; taugt aber auch fuer den Fall, dass
                # Andre sich vertippt.
                if m.get("anlass") == "widerruf":
                    ab = eintrag["abende"].get(m.get("tag"))
                    if ab:
                        for k in ("bewertung", "bewertung_anlass",
                                  "bewertung_zeit", "bewertung_erfasst"):
                            ab.pop(k, None)
                    continue
                tag, note = m.get("tag"), m.get("note")
                if not tag or note is None:
                    continue
                # T-0052: erst pruefen, dann uebernehmen.  `tag` ist ueber
                # plausibel() schon durch, `note` war es bis zum 22.08.2026 nicht.
                if not gueltige_note(note):
                    print("   %s %s: Note %r ist keine Note 0-5 - verworfen"
                          % (ort["name"], tag, note))
                    continue
                if not sonnenuntergang_vorbei(tag, ort):
                    print("   %s %s: Sonnenuntergang war noch nicht - verworfen"
                          % (ort["name"], tag))
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
                # Gleiche Fehlerklasse wie bei `note`: ein Feld aus einer
                # oeffentlichen Nachricht wandert ungeprueft in den Zustand.
                # `anlass` steuert die Auswertung (wer nur nach Alarmen bewertet,
                # liefert keine Basisrate), also gilt die Liste der Werte, die
                # die Erinnerung ueberhaupt erzeugen kann.
                # isinstance ZUERST: `x in frozenset` wirft TypeError, wenn x
                # unhashbar ist (Liste, dict) - die Pruefung selbst waere
                # sonst der Absturz, den sie verhindern soll.
                if isinstance(m.get("anlass"), str) and m["anlass"] in ANLAESSE:
                    abend["bewertung_anlass"] = m["anlass"]
                # `erfasst` ist ein ISO-Zeitstempel vom Geraet.  Als Text
                # begrenzter Laenge uebernehmen - er wird nicht gerechnet,
                # sondern nur festgehalten, aber ein Objekt oder eine 10-MB-
                # Zeichenkette gehoert trotzdem nicht in die Zustandsdatei.
                if isinstance(m.get("erfasst"), str) and len(m["erfasst"]) <= 40:
                    # Zeitpunkt am GERAET, nicht der Empfang bei ntfy.  Bei einer
                    # nachgesendeten Bewertung liegen die beiden Tage auseinander,
                    # und nur der erste sagt, wann tatsaechlich bewertet wurde.
                    abend["bewertung_erfasst"] = m["erfasst"]
        zaehler["neu"] = neu

    # T-0051 atomar UND T-0058 unter Sperre, gegen den frischen Stand.
    zustand = aktualisiere(zpfad, eintragen)
    neu = zaehler["neu"]

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
