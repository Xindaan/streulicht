"""T-0084: die Stufe eines Abends nach Modelllaeufen - EINE Regel fuer alle.

Bis zum 09.10.2026 ordneten Prognoseseite, Bewertungsseite und Bilanz den
Median der Member in die Verteilung einzelner Abende ein (dreimal
ausprogrammiert).  Ergebnis: "selten" in 0,5 % der Vorhersagen, "auffaellig" in
9,5 % statt rund 20 %.  Jetzt gilt (skripte/stufen.py):

    selten        p >= p*          (= Push-Bedingung des Alarms)
    auffaellig    Memberanteil im obersten Fuenftel >= Q_AUFFAELLIG
    unauffaellig  sonst

Geprueft wird Verhalten, nicht Quelltext:

  1. Die Stufe "selten" stimmt mit der Push-Bedingung ueberein - gegen ein
     vom Test selbst geschriebenes Orakel `p >= p*`, auch auf der Grenze,
     und durch einen echten Alarmlauf (Buchung der Alarme).
  2. Die Q-Grenze: 19 von 51 Membern sind auffaellig, 18 von 51 nicht.
  3. Der Memberanteil wird gespeichert und stimmt mit den Membern des
     Tagesarchivs ueberein.
  4. Alle drei Seiten (Prognose, Bewertung, Bilanz) zeigen fuer denselben
     Zustand dieselbe Stufe - auch dort, wo die alte Regel etwas anderes
     sagen wuerde (Faelle, in denen der Rang des Medians und der Memberanteil
     auseinanderlaufen).
  5. Zeilen ohne Memberanteil behalten die alte Stufe und sagen es.

Lauf:  python3 skripte/test_stufen.py
"""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import date, timedelta

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import alarm  # noqa: E402
import bewertungsseite  # noqa: E402
import bisher  # noqa: E402
import seite  # noqa: E402
import stufen  # noqa: E402
import test_abruf  # noqa: E402  (nur der erfundene Abruf, kein Netz)

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


NAME = {"selten": "selten", "auffaellig": "auffällig",
        "unauffaellig": "unauffällig"}
KLIMA = stufen.klima_sortiert(BASIS)
N = 51

print("=== 1. 'selten' ist die Push-Bedingung (gegen ein Orakel p >= p*)")
falsch = []
for schwelle in (0.5, 0.3, 0.75, 1 / 51, 26 / 51):
    for k in range(0, N + 1):
        p = k / N
        orakel = p >= schwelle
        for anteil in (0.0, 0.2, 1.0):
            name, klasse = stufen.stufe(p, anteil, schwelle)
            if (klasse == "selten") != orakel:
                falsch.append((schwelle, k, anteil, klasse))
pruefe(not falsch, "Stufe 'selten' <=> p >= p* fuer 5 Schwellen x 52 Anteile "
       "x 3 Memberanteile (Abweichungen: %s)" % falsch[:2])
pruefe(stufen.stufe(0.5, 0.0, 0.5)[1] == "selten"
       and stufen.stufe(0.4999, 1.0, 0.5)[1] != "selten",
       "auf der Grenze: p = p* ist selten, knapp darunter nicht - auch bei "
       "Memberanteil 1,0")
pruefe(stufen.stufe(0.8, 0.0, 0.5)[0] == "selten",
       "selten schlaegt den Memberanteil (p hoch, Anteil 0)")

print("\n=== 2. Die Q-Grenze: 19 von 51 auffaellig, 18 von 51 nicht")
pruefe(stufen.stufe(0.1, 19 / N, 0.5)[1] == "auffaellig",
       "19 von 51 Membern im obersten Fuenftel -> auffaellig")
pruefe(stufen.stufe(0.1, 18 / N, 0.5)[1] == "unauffaellig",
       "18 von 51 -> unauffaellig")
pruefe(stufen.stufe(0.1, 0.0, 0.5)[1] == "unauffaellig"
       and stufen.stufe(0.1, 1.0, 0.5)[1] == "auffaellig",
       "keiner / alle im obersten Fuenftel")

print("\n=== 3. Rang 0,80 zaehlt (Memberanteil aus Scores)")
klima = [i / 100.0 for i in range(100)]        # Rang(s) = Anteil darunter
pruefe(abs(stufen.rang(klima, 0.80) - 0.80) < 1e-12
       and abs(stufen.rang(klima, 0.795) - 0.80) < 1e-12
       and stufen.rang(klima, 0.79) < 0.80,
       "Rang = Anteil der Abende STRIKT darunter (wie auf den Seiten bisher)")
scores = [0.80] * 3 + [0.79] * 7           # drei auf Rang 0,80, sieben darunter
pruefe(abs(stufen.anteil_auffaellig(scores, klima) - 0.3) < 1e-12,
       "Member genau auf Rang 0,80 zaehlen, knapp darunter nicht (3 von 10)")
pruefe(stufen.anteil_auffaellig([None, None], klima) is None,
       "keine gueltigen Member -> None, keine Null")

print("\n=== 4. verdichte() liefert den Anteil, nur mit Klimatologie")
D = {"schirm": "high", "A": 0.5, "sicht": 1.0, "weg": 1.0}
werte = [(0.80, D)] * 4 + [(0.1, D)] * 6 + [(0.0, None)] * 2   # 2 ohne Daten
v = alarm.verdichte(werte, 0.6, klima)
pruefe(abs(v["anteil_auffaellig"] - 0.4) < 1e-12,
       "4 von 10 gueltigen Membern (datenlose nicht im Nenner): %.3f"
       % v["anteil_auffaellig"])
pruefe("anteil_auffaellig" not in alarm.verdichte(werte, 0.6),
       "ohne Klimatologie fehlt das Feld (kein erfundener Wert)")

print("\n=== 5. Der echte Alarmlauf: Buchung == Stufe == Orakel, Feld im Zustand")
SCHWELLE = 0.5
PS = [0.0, 0.49, 0.4999, 0.5, 0.5001, 0.51, 1.0, 0.2, 0.5, 0.75, 0.3]


def lauf():
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "daten"), exist_ok=True)
    shutil.copy(os.path.join(BASIS, "daten", stufen.KLIMA_DATEI),
                os.path.join(d, "daten"))
    kfg = json.load(open(os.path.join(BASIS, "konfig.json")))
    kfg["schwelle_wahrscheinlichkeit"] = SCHWELLE
    kfg["seiten_basis"] = "https://example.invalid"
    for o in kfg["orte"]:
        o["ntfy_alarm"] = "topic-test"
    kp = os.path.join(d, "konfig.json")
    json.dump(kfg, open(kp, "w"))

    gesendet = []
    echt = alarm.lauf_ort

    def lauf_ort_mit_p(*a, **k):
        # Die Rechnung laeuft echt (inklusive Memberanteil); nur p wird auf
        # vorgegebene Werte um die Schwelle gesetzt.
        erg = echt(*a, **k)
        for t, p in zip(sorted(erg), PS):
            erg[t]["p"] = p
        return erg

    alt = (alarm.BASIS, alarm.abfrage, alarm.modelllauf, alarm.sende,
           alarm.warte_auf_netz, alarm.lauf_ort)
    alarm.BASIS = d
    alarm.abfrage = test_abruf.falscher_abruf
    alarm.modelllauf = lambda m: "2026-01-01T00:00+00:00"
    alarm.sende = lambda topic, titel, text, prio="default", klick=None: \
        gesendet.append(text) or 200
    alarm.warte_auf_netz = lambda *a, **k: None
    alarm.lauf_ort = lauf_ort_mit_p
    sicher, sys.argv = sys.argv, ["alarm.py", "--konfig", kp]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            alarm.main()
    finally:
        sys.argv = sicher
        (alarm.BASIS, alarm.abfrage, alarm.modelllauf, alarm.sende,
         alarm.warte_auf_netz, alarm.lauf_ort) = alt
    z = json.load(open(os.path.join(d, "daten", "zustand.json")))["berlin"]
    arch = {}
    for w, _, fs in os.walk(os.path.join(d, "daten", "archiv")):
        for f in fs:
            arch = json.load(open(os.path.join(w, f)))["abende"]
    shutil.rmtree(d, ignore_errors=True)
    return z, gesendet, arch


z, gesendet, arch = lauf()
abende = {t: e for t, e in z["abende"].items() if e.get("p") in PS}
gebucht = set(z["alarme"])
orakel = {t for t, e in abende.items() if e["p"] >= SCHWELLE}
stufe_selten = {t for t, e in abende.items()
                if stufen.stufe(e["p"], e.get("anteil_auffaellig", 0.0),
                                SCHWELLE)[1] == "selten"}
pruefe(len(abende) >= 9 and 0 < len(orakel) < len(abende),
       "der Lauf deckt beide Seiten der Schwelle ab (%d Abende, %d selten)"
       % (len(abende), len(orakel)))
pruefe(gebucht == orakel,
       "gebuchte Pushs == {p >= p*} (inkl. p = p* = 0.5): %s"
       % sorted(set(gebucht) ^ orakel))
pruefe(stufe_selten == orakel, "Stufe 'selten' == {p >= p*}")
pruefe(all("anteil_auffaellig" in e for e in z["abende"].values()),
       "jeder gerechnete Abend traegt anteil_auffaellig im Zustand")
verlauf_hat = all("anteil_auffaellig" in (e.get("verlauf") or [{}])[-1]
                  for e in z["abende"].values())
pruefe(verlauf_hat, "... auch in der Verlaufszeile (Auswertung ueber Laeufe)")
gleich = True
for t, e in z["abende"].items():
    member = [m["s"] for m in arch[t]["member"]]
    soll = stufen.anteil_auffaellig(member, KLIMA)
    gleich = gleich and abs(soll - e["anteil_auffaellig"]) < 1e-9
pruefe(gleich, "gespeicherter Anteil == Anteil der Member im Tagesarchiv")

print("\n=== 6. Dieselbe Stufe auf allen drei Seiten")
# Faelle, in denen die ALTE Regel (Rang des Medians) etwas anderes sagt.
r_hoch = KLIMA[int(0.90 * len(KLIMA))]        # Median-Rang ~ 0,90
r_tief = KLIMA[int(0.30 * len(KLIMA))]        # Median-Rang ~ 0,30
FAELLE = [   # (p, anteil, median, erwartete Stufe, alte Stufe)
    (0.62, 0.10, r_tief, "selten", "unauffaellig"),
    (0.10, 0.40, r_tief, "auffaellig", "unauffaellig"),
    (0.10, 0.30, r_hoch, "unauffaellig", "auffaellig"),
    (0.50, 0.00, r_tief, "selten", "unauffaellig"),
]
heute = date.today()
tage = [(heute + timedelta(days=k + 1)).isoformat() for k in range(len(FAELLE) + 1)]


def abend_e(p, anteil, median, lauf, bewertung=None):
    e = {"p": p, "median": median, "stunde_utc": 16.5, "azimut": 255.0,
         "dt_h": 24.0, "schirm": "mid", "A": 0.5, "sicht": 0.5, "weg": 0.5,
         "n_member": 51, "n_member_gesamt": 51, "bewertung": bewertung,
         "verlauf": [{"lauf": lauf, "p": p}]}
    if anteil is not None:
        e["anteil_auffaellig"] = anteil
    return e


abende = {t: abend_e(p, a, m, heute.isoformat(), 3)
          for t, (p, a, m, _, _) in zip(tage, FAELLE)}
# Der letzte Tag: ALTE Zeile ohne Memberanteil, Median-Rang ~ 0,90
abende[tage[-1]] = abend_e(0.10, None, r_hoch, heute.isoformat(), 3)
erwartet = [f[3] for f in FAELLE] + ["auffaellig"]      # alt: Rang 0,90

d = tempfile.mkdtemp()
try:
    os.makedirs(os.path.join(d, "daten"))
    os.makedirs(os.path.join(d, "web"))
    shutil.copy(os.path.join(BASIS, "konfig.json"), d)
    shutil.copy(os.path.join(BASIS, "daten", stufen.KLIMA_DATEI),
                os.path.join(d, "daten"))
    zs = {"berlin": {"abende": abende, "alarme": {}, "laeufe": {},
                     "stand": {"geholt": "%sT12:00+00:00" % heute.isoformat(),
                               "modelllauf": "%sT00:00+00:00" % heute.isoformat(),
                               "fenster": "abend"}}}
    json.dump(zs, open(os.path.join(d, "daten", "zustand.json"), "w"))

    # --- Prognoseseite: seite.main() gegen die Temp-Basis
    alt = (seite.BASIS, sys.argv)
    seite.BASIS = d
    sys.argv = ["seite.py", "--konfig", os.path.join(d, "konfig.json")]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            seite.main()
    finally:
        seite.BASIS, sys.argv = alt
    html = open(os.path.join(d, "web", "index.html"), encoding="utf-8").read()
    meta = json.loads(re.search(r"const META=(.*?), BESTER=", html, re.S).group(1))
    auf_seite = [m["stufe"] for m in meta]

    # --- Bewertungsseite: der Prognosestand, der in die Seite geschrieben wird
    alt = bewertungsseite.BASIS
    bewertungsseite.BASIS = d
    try:
        stand = bewertungsseite.prognosestand("berlin", 0.7065)
    finally:
        bewertungsseite.BASIS = alt
    auf_bewertung = [stand[t]["stufe"] for t in tage]
finally:
    shutil.rmtree(d, ignore_errors=True)

# --- Bilanz: die Zeile "vorhergesagt: ..." je Abend
zeilen = bisher.eintraege("berlin", KLIMA, {"abende": abende, "alarme": {}},
                          heute, schwelle_p=0.5)
nach_tag = {z["tag"]: z["zeile"] for z in zeilen}
auf_bilanz = []
for t in tage:
    m = re.search(r"vorhergesagt[^:]*: ([^\s,(]+)", nach_tag[t])
    auf_bilanz.append(m.group(1))

soll = [NAME[s] for s in erwartet]
pruefe(auf_seite == soll, "Prognoseseite: %s" % auf_seite)
pruefe(auf_bewertung == soll, "Bewertungsseite: %s" % auf_bewertung)
pruefe(auf_bilanz == soll, "Bilanz: %s" % auf_bilanz)
pruefe([f[4] for f in FAELLE] != [f[3] for f in FAELLE],
       "die Faelle unterscheiden sich von der alten Regel (sonst bewiesen sie "
       "nichts)")
pruefe("__SCHWELLEP__" not in html and "__QAUFF__" not in html
       and "mindestens 37&nbsp;%" in html and "mindestens 50&nbsp;%" in html,
       "Seitentext nennt die Grenzen aus den Konstanten (37 % und 50 %)")

print("\n=== 7. Zeilen ohne Memberanteil: alte Stufe, mit Vermerk")
alte_zeile = nach_tag[tage[-1]]
pruefe("alten Verfahren" in alte_zeile,
       "die Zeile ohne Memberanteil sagt, dass sie nach altem Verfahren steht")
pruefe(all("alten Verfahren" not in nach_tag[t] for t in tage[:-1]),
       "Zeilen mit Memberanteil tragen den Vermerk nicht")
pruefe("Modelll&auml;ufe" in nach_tag[tage[1]]
       and "40 %" in nach_tag[tage[1]],
       "auffaellig nennt den Anteil der Modelllaeufe (%s)"
       % re.sub(r"&[a-z]+;", "?", nach_tag[tage[1]])[:90])
name, klasse, neu = stufen.stufe_eintrag({"p": 0.1}, 0.9, 0.5)
pruefe(klasse == "auffaellig" and neu is False,
       "stufe_eintrag ohne Anteil: Rang 0,9 -> alte Regel, nicht neu")
name, klasse, neu = stufen.stufe_eintrag({"p": 0.1, "anteil_auffaellig": 0.0},
                                         0.99, 0.5)
pruefe(klasse == "unauffaellig" and neu is True,
       "mit Anteil 0: Rang 0,99 des Medians zaehlt nicht mehr")
pruefe(stufen.stufe_alt(0.95)[1] == "selten"
       and stufen.stufe_alt(0.9499)[1] == "auffaellig"
       and stufen.stufe_alt(0.80)[1] == "auffaellig"
       and stufen.stufe_alt(0.7999)[1] == "unauffaellig",
       "stufe_alt (Rueckschau): Grenzen 0,95 und 0,80 auf der Kante")

print("\n=== 8. Rueckschau: ein Einzelscore, die Stufe bleibt am Rang")
# Ohne Ensemble gibt es weder p noch einen Memberanteil; hier ist der Rang
# gegen die Verteilung einzelner Abende die richtige Stufe.  Die Bilder
# werden durch Platzhalter ersetzt - geprueft wird nur die Stufe.
R_TAGE = {"2026-08-01": KLIMA[int(0.97 * len(KLIMA))],
          "2026-08-02": KLIMA[int(0.88 * len(KLIMA))],
          "2026-08-03": KLIMA[int(0.40 * len(KLIMA))]}
alt_r = (seite.lade_feld, seite.svg, seite._bilder)
seite.lade_feld = lambda t: {"x": 1}
seite.svg = lambda t, feld, kompakt=False: (
    None, R_TAGE[t], {"schirm": "mid", "A": 0.5, "weg": 0.5, "sicht": 0.5})
seite._bilder = lambda *a, **k: ("", "")
try:
    rueck = seite.rueckschau_eintraege(
        "2026-08-01", 3, {t: {} for t in R_TAGE},
        lambda s_: stufen.rang(KLIMA, s_), 0.7065)
finally:
    seite.lade_feld, seite.svg, seite._bilder = alt_r
pruefe([e["stufe"] for e in rueck] == ["selten", "auffällig", "unauffällig"],
       "Rueckschau: Rang 0,97 / 0,88 / 0,40 -> selten / auffaellig / "
       "unauffaellig: %s" % [e["stufe"] for e in rueck])

print()
if fehler:
    print("%d FEHLER" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen gruen")
