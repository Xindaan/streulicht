"""Das Aufforderungsfenster - und das Nachholen danach (T-0067).

WARUM DAS EINEN TEST BRAUCHT.  Die Bewertungen sind die einzige Messgroesse
des Projekts, die sich nicht nachproduzieren laesst: fuer einen Abend ohne
Note gibt es keinen zweiten Abruf und keine zweite Quelle.  Das Fenster ist
75 Minuten breit, der Agent tickt stuendlich - schlaeft der Rechner darueber
hinweg, faellt der ganze Abend aus.  Seit dem 02.09.2026 wird bis zum
lokalen Mitternacht nachgeholt.

Die Grenze ist der Punkt: nachgeholt wird der HEUTIGE lokale Abend, nie der
von gestern.  Nach Mitternacht bewertet niemand mehr den vorletzten
Sonnenuntergang, und die Frage waere dann irrefuehrend statt hilfreich.

Kein Netz, kein Zugriff auf Betriebsdaten: eigenes Temp-Verzeichnis, eigener
Zustand, `sende` durch eine Attrappe ersetzt.

KONFIGURATION (T-0079, Review bewertung#9): der Test liest NICHT die
Produktiv-`konfig.json`, sondern TESTKONFIG weiter unten.  Vorher uebernahm er
sie samt `bewertung_tage_pro_woche`; jeder Wert unter 7 (die Wochenstichprobe,
die Andre jederzeit einstellen darf) machte die Suite rot, obwohl
erinnerung.py stimmte - bei 2 bis 6 Tagen fielen 2 Pruefungen durch, bei 1 Tag
sechs.  Wert-Huerde: eine Aenderung an der Betriebskonfiguration (Wochen-
stichprobe, Vorlauf, Fenster, Topic-Name) darf diesen Test nicht mehr
beruehren; rot wird er nur noch, wenn erinnerung.py sich aendert.

Lauf:  .venv/bin/python3 skripte/test_erinnerung.py
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import urllib.error

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import erinnerung  # noqa: E402
from zustandsdatei import lade, schreibe  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


# Feste Testkonfiguration - dieselben Felder wie die Betriebskonfiguration,
# soweit erinnerung.py sie liest, aber mit eigenen Werten.  7 = jeden Abend
# fragen: die Faelle unten setzen genau das voraus.
TESTKONFIG = {
    "lauf_vorlauf_stunden": 3,
    "lauf_fenster_min": 60,
    "seiten_basis": "https://beispiel.invalid/streulicht",
    "bewertung_tage_pro_woche": 7,
    "orte": [{"name": "berlin", "anzeige": "Berlin", "breite": 52.52,
              "laenge": 13.405, "zeitzone": "Europe/Berlin",
              "ntfy_bewertung": "test-bewertung-oeffentlich"}],
}

# Berlin, 02.09.2026: Sonnenuntergang 17:52 UTC (19:52 Ortszeit).
# Fenster: Start 18:22 UTC, Ende 19:37 UTC.
GESENDET = []
EREIGNISSE = []        # Reihenfolge: "netz" (Warten) und "sende" (Versand)
ENDE = [None]          # wie der letzte Lauf endete: None oder SystemExit
WIRFT = [False]        # soll der Versand scheitern?


def falscher_versand(topic, titel, text, klick=None):
    EREIGNISSE.append("sende")
    if WIRFT[0]:
        raise urllib.error.URLError("ntfy weg (Test)")
    GESENDET.append({"topic": topic, "titel": titel, "klick": klick})


def falsches_warten(*a, **k):
    # Kein DNS im Test (und die Netzsperre der Pruefumgebung wirft hier).
    EREIGNISSE.append("netz")
    return True


AUSGABE = [""]         # was der letzte Lauf auf stdout schrieb


def lauf(jetzt_iso, vorzustand=None, geheim=None):
    """Einen Erinnerungslauf fahren.  Rueckgabe: (Zahl Sendungen, Zustand).

    `geheim`: Inhalt einer konfig_geheim.json im Temp-Verzeichnis (str = roher
    Dateitext, sonst wird json.dump benutzt); None = Datei fehlt."""
    GESENDET.clear()
    EREIGNISSE.clear()
    ENDE[0] = None
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "daten"), exist_ok=True)
    kp = os.path.join(d, "konfig.json")
    with open(kp, "w") as f:
        json.dump(TESTKONFIG, f)
    zp = os.path.join(d, "daten", "zustand.json")
    schreibe(zp, vorzustand or {})
    if geheim is not None:
        with open(os.path.join(d, "konfig_geheim.json"), "w") as f:
            f.write(geheim if isinstance(geheim, str) else json.dumps(geheim))

    alt_basis, alt_sende = erinnerung.BASIS, erinnerung.sende
    alt_netz = erinnerung.warte_auf_netz
    erinnerung.BASIS = d
    erinnerung.sende = falscher_versand
    erinnerung.warte_auf_netz = falsches_warten
    sicher, sys.argv = sys.argv, ["erinnerung.py", "--konfig", kp,
                                  "--jetzt", jetzt_iso]
    puffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(puffer):
            erinnerung.main()
    except SystemExit as ex:
        ENDE[0] = ex
    finally:
        AUSGABE[0] = puffer.getvalue()
        sys.argv = sicher
        erinnerung.BASIS, erinnerung.sende = alt_basis, alt_sende
        erinnerung.warte_auf_netz = alt_netz
    return len(GESENDET), lade(zp)


print("1. Im Fenster wird gefragt (unveraendert)")
n, z = lauf("2026-09-02T18:40")
pruefe(n == 1, "eine Aufforderung im Fenster (%d)" % n)
pruefe("2026-09-02" in (z.get("berlin") or {}).get("erinnerungen", {}),
       "und sie ist fuer den 02.09. gebucht")

print("\n2. Vor dem Fenster wird nicht gefragt")
n, _ = lauf("2026-09-02T16:00")
pruefe(n == 0, "nichts vor Sonnenuntergang (%d)" % n)

print("\n3. NACH dem Fenster wird nachgeholt - solange es lokal derselbe Tag ist")
# 21:30 UTC = 23:30 Ortszeit, also fast vier Stunden nach Fensterende und
# eine halbe Stunde vor dem lokalen Tageswechsel.  Genau der Fall, der
# bis zum 02.09.2026 ersatzlos ausfiel.
n, z = lauf("2026-09-02T21:30")
pruefe(n == 1, "eine nachgeholte Aufforderung (%d)" % n)
pruefe("2026-09-02" in (z.get("berlin") or {}).get("erinnerungen", {}),
       "und zwar fuer den HEUTIGEN Abend, nicht fuer gestern")

print("\n4. Nach lokalem Mitternacht wird NICHT mehr nachgeholt")
# 22:30 UTC = 00:30 Ortszeit des 03.09.  Der Abend des 02.09. ist damit
# vorbei; eine Frage danach waere irrefuehrend.  Zugleich liegt der
# Sonnenuntergang des 03.09. noch 17 Stunden in der Zukunft.
n, z = lauf("2026-09-02T22:30")
pruefe(n == 0, "keine Aufforderung nach Mitternacht (%d)" % n)

print("\n5. Idempotenz: der naechste Tick fragt nicht noch einmal")
vor = {"berlin": {"abende": {}, "alarme": {},
                  "erinnerungen": {"2026-09-02": "2026-09-02T18:40:00+00:00"}}}
n, _ = lauf("2026-09-02T21:30", vor)
pruefe(n == 0, "schon gefragt, also Ruhe (%d)" % n)

print("\n6. Der Winterabend wird genauso nachgeholt")
# 21.12.2026, Sonnenuntergang 14:53 UTC.  Fensterende 16:38 UTC; 22:00 UTC
# ist 23:00 Ortszeit, also noch derselbe lokale Tag.  Eine feste Uhrzeit
# haette hier entweder im Sommer oder im Winter danebengelegen.
n, z = lauf("2026-12-21T22:00")
pruefe(n == 1, "auch im Dezember nachgeholt (%d)" % n)
pruefe("2026-12-21" in (z.get("berlin") or {}).get("erinnerungen", {}),
       "und fuer den richtigen Abend gebucht")

print("\n7. Netz abwarten VOR dem Versand, Exitcode bei Versandfehler (T-0081)")
# Review 09.10.2026, bewertung#5: der Agent wartete nie aufs Netz (26
# Fehlversuche an 13 Abenden, einmal ging ein Abend ganz verloren) und endete
# bei jedem Versandfehler mit Exitcode 0 - launchd zeigte "last exit code = 0".
n, z = lauf("2026-09-02T18:40")
pruefe(EREIGNISSE == ["netz", "sende"],
       "erst aufs Netz warten, dann senden (%s)" % EREIGNISSE)
pruefe(ENDE[0] is None, "gelungener Versand: Exitcode 0")
n, _ = lauf("2026-09-02T16:00")
pruefe(EREIGNISSE == [],
       "nichts zu senden: auch kein Warten auf das Netz (%s) - 23 von 24 "
       "Ticks haben nichts zu tun" % EREIGNISSE)
WIRFT[0] = True
n, z = lauf("2026-09-02T18:40")
pruefe(n == 0 and not (z.get("berlin") or {}).get("erinnerungen"),
       "Versandfehler: nichts gebucht, der naechste Tick holt nach")
pruefe(isinstance(ENDE[0], SystemExit) and ENDE[0].code not in (None, 0),
       "Versandfehler: Exitcode != 0, mit Grund (%s)"
       % (ENDE[0].code if ENDE[0] else "-"))
WIRFT[0] = False
n, z = lauf("2026-09-02T18:55", z)
pruefe(n == 1 and ENDE[0] is None,
       "der naechste Tick sendet nach, wenn das Netz da ist (%d)" % n)

print("\n8. Erinnerung geht auf das GEHEIME Topic (T-0077, bewertung#3)")
# Das oeffentliche Bewertungs-Topic steht im Klartext in der Seite; wer es
# kennt, kann Pushs mit Klickziel auf Andres Telefon schicken.  Die Erinnerung
# soll deshalb ueber `ntfy_erinnerung` in konfig_geheim.json laufen.
oeffentlich = TESTKONFIG["orte"][0]["ntfy_bewertung"]   # steht im Klartext in der Seite
GEHEIM = "sl-erinnerung-testtopic-geheim"
n, _ = lauf("2026-09-02T18:40", geheim={"ntfy_erinnerung": {"berlin": GEHEIM}})
pruefe(n == 1 and GESENDET[0]["topic"] == GEHEIM,
       "mit Eintrag: gesendet wird auf das geheime Topic")
pruefe(GESENDET[0]["topic"] != oeffentlich,
       "und NICHT auf das oeffentliche Bewertungs-Topic")
pruefe("WARNUNG" not in AUSGABE[0],
       "ohne Warnzeile, wenn das geheime Topic gesetzt ist")
pruefe(GEHEIM not in AUSGABE[0],
       "das geheime Topic steht nicht im Log")
n, _ = lauf("2026-09-02T18:40")
pruefe(n == 1 and GESENDET[0]["topic"] == oeffentlich,
       "ohne konfig_geheim.json: wie bisher ueber das oeffentliche Topic")
pruefe("oeffentliche Topic" in AUSGABE[0] and "WARNUNG" in AUSGABE[0],
       "und mit Warnzeile im Log")

for bild, geh in (("Schluessel fehlt", {"ntfy_alarm": {"berlin": "x"}}),
                  ("anderer Ort", {"ntfy_erinnerung": {"hamburg": GEHEIM}}),
                  ("leerer Wert", {"ntfy_erinnerung": {"berlin": "  "}}),
                  ("falscher Typ", {"ntfy_erinnerung": GEHEIM}),
                  ("kaputtes JSON", "{nicht json")):
    n, _ = lauf("2026-09-02T18:40", geheim=geh)
    pruefe(n == 1 and GESENDET[0]["topic"] == oeffentlich
           and "WARNUNG" in AUSGABE[0],
           "%s: Rueckfall auf das oeffentliche Topic mit Warnung, kein Absturz"
           % bild)

print("")
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
