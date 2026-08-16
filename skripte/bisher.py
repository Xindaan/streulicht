"""Die Bilanzseite: was bisher gemessen ist - und was noch nicht.

WARUM SIE "BISHER" HEISST UND NICHT "RUECKSCHAU".  Der Entwurf nennt sie
Rueckschau; der Name ist aber schon vergeben.  `skripte/rueckschau.py`
erzeugt seit Wochen eine lokale DIAGNOSE ueber vier Jahre Klimatologie
(9,5 MB, gitignoriert, nie ausgeliefert - sie zeigt Andres Albumabende neben
meinen Bewertungen).  Zwei Dinge im selben Projekt gleich zu nennen ist
genau der Weg, auf dem am 15.08.2026 beinahe die falsche Datei
veroeffentlicht worden waere.  Also: Diagnose = Rueckschau, Produkt = Bisher.

WAS SIE LEISTEN SOLL.  Nicht: eine Trefferquote behaupten, die es noch nicht
gibt.  Sondern: zeigen, was da ist (die bisherigen Bewertungen), und
benennen, was fehlt, warum es fehlt und wann es kommt.  Ein leerer Zustand
mit Platzhaltern waere eine Behauptung ueber die Zukunft; ein Absatz, der
sagt "die Alarmrate ist unbekannt, nicht 18,5 pro Jahr", ist eine Messung
ueber die Gegenwart.

Lauf:  python3 skripte/bisher.py
"""
import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens  # noqa: E402
from seite import MONAT, WOCHENTAG, stufe  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Vor diesem Abend gab es die Bewertungsseite nicht.  Dieselbe Zahl steht in
# skripte/bewertungen_holen.py als ERSTER_ABEND; sie ist dort die
# Plausibilitaetsgrenze und hier die Korpusangabe.
ERSTER_ABEND = date(2026, 8, 15)

ANLASS_TEXT = {"aufgefordert": "Auf Nachfrage bewertet",
               "alarm": "Nach Alarm bewertet"}


def eintraege(ort_name, alle_scores):
    """Bewertete Abende, neueste zuerst - mit dem, was dazu prognostiziert war."""
    zp = os.path.join(BASIS, "daten", "zustand.json")
    if not os.path.exists(zp):
        return []
    with open(zp) as f:
        zustand = json.load(f)
    abende = (zustand.get(ort_name) or {}).get("abende", {})
    aus = []
    for t in sorted(abende, reverse=True):
        e = abende[t]
        if e.get("bewertung") is None:
            continue
        d = date.fromisoformat(t)
        zeile = [ANLASS_TEXT.get(e.get("bewertung_anlass"), "Spontan bewertet")]
        if e.get("median") is None:
            zeile.append("keine Prognose f&uuml;r diesen Abend gerechnet")
        else:
            rang = (sum(1 for x in alle_scores if x < e["median"])
                    / len(alle_scores))
            name, _ = stufe(rang)
            zeile.append("vorhergesagt: %s, %d. Perzentil"
                         % (name, round(rang * 100)))
        aus.append({"tag": t, "note": e["bewertung"],
                    "kopf": "%s %02d.%02d." % (WOCHENTAG[d.weekday()],
                                               d.day, d.month),
                    "zeile": " &#183; ".join(zeile)})
    return aus


def karte(e):
    """Eine Bewertungskarte.  Note 0 ist eine Antwort, kein leerer Balken."""
    if e["note"] == 0:
        zahl = ('<span class="note-null">nicht gesehen</span>')
    else:
        zahl = ('<span><b>%d</b><span class="von">/5</span></span>' % e["note"])
    balken = "".join('<i%s></i>' % (' class="voll"' if k < e["note"] else "")
                     for k in range(5))
    return ('<article class="bkarte"><div class="bkopf"><span>%s</span>%s</div>'
            '<div class="balken">%s</div><p class="bzeile">%s</p></article>'
            % (e["kopf"], zahl, balken, e["zeile"]))


VORLAGE = """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>Streulicht &mdash; bisher</title><style>
__TOKENS__
*{box-sizing:border-box}
html{color-scheme:dark}
body{margin:0;background:var(--papier);color:var(--tinte);
 font-family:var(--schrift);font-size:var(--grad-basis);
 line-height:var(--zeilen-basis);letter-spacing:var(--sperrung-eng);
 font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
.rahmen{max-width:390px;margin:0 auto;min-height:100vh;padding-bottom:var(--s8)}
.topbar{position:sticky;top:0;z-index:5;display:flex;align-items:center;
 justify-content:space-between;
 padding:calc(14px + env(safe-area-inset-top)) 18px 12px;
 background:rgba(0,0,0,.72);
 -webkit-backdrop-filter:blur(18px) saturate(1.4);
 backdrop-filter:blur(18px) saturate(1.4);
 border-bottom:1px solid var(--karte)}
.marke-wort{margin:0;font-size:17px;font-weight:800;
 letter-spacing:var(--sperrung-enger)}
.ortspille{padding:3px 11px;border-radius:var(--radius-pille);
 background:var(--karte);color:var(--tinte2);font-size:12px;font-weight:700}
.inhalt{padding:20px 18px 0}
.etikett{margin:0;color:var(--gedaempft);font-size:12px;font-weight:700;
 letter-spacing:var(--sperrung-label);text-transform:uppercase}
.bkarte{margin-top:14px;padding:16px;background:var(--karte);
 border:1px solid var(--achse);border-radius:var(--radius-karte)}
.bkopf{display:flex;justify-content:space-between;align-items:baseline;
 font-size:15px;font-weight:700}
.bkopf b{font-size:26px;font-weight:800;letter-spacing:var(--sperrung-enger);
 color:var(--akzent-tinte)}
.von{font-size:13px;font-weight:400;color:var(--gedaempft)}
.note-null{font-size:13px;font-weight:400;color:var(--gedaempft)}
.balken{display:flex;gap:3px;margin-top:12px}
.balken i{flex:1;height:6px;border-radius:var(--radius-pille);
 background:var(--flaeche2)}
.balken i.voll{background:var(--akzent-tinte)}
.bzeile{margin:12px 0 0;color:var(--gedaempft);font-size:13px}
.leer{margin:14px 0 0;padding:16px;background:var(--karte);
 border-radius:var(--radius-karte);color:var(--tinte2);font-size:14px;
 line-height:1.55}
.abschnitt{margin-top:22px}
.abschnitt p{margin:6px 0 0;color:var(--tinte2);font-size:14px;
 line-height:1.55;text-wrap:pretty}
.kasten{margin-top:14px;padding:14px 16px;background:var(--karte);
 border-radius:var(--radius-kachel);color:var(--gedaempft);font-size:13px;
 line-height:1.55;text-wrap:pretty}
.schluss{margin-top:22px;color:var(--gedaempft);font-size:13px;
 line-height:1.55}
.zurueck{display:flex;align-items:center;justify-content:center;
 margin-top:26px;min-height:var(--tastflaeche);padding:0 18px;
 border-radius:var(--radius-pille);background:var(--akzent-flaeche);
 color:var(--akzent-tinte);font-size:14px;font-weight:700;
 text-decoration:none}
</style></head><body>
<div class="rahmen">
<header class="topbar"><p class="marke-wort">Bisher</p>
<span class="ortspille">__ORT__</span></header>
<main class="inhalt">
<p class="etikett">__KORPUS__</p>
__KARTEN__
<section class="abschnitt"><p class="etikett">Was hier sp&auml;ter steht</p>
<p>Trefferquote, Alarmrate und die Schwelle, gegen die beide gemessen werden.
Alle drei brauchen Abende, die es noch nicht gibt.</p>
<div class="kasten">Die Schwelle stammt aus Analysefeldern, der Alarm rechnet
auf Ensemble-Membern. Ob dieselbe Schwelle dieselbe Rate ergibt, ist nie
gemessen worden &mdash; der Livegang ist die Messung. Nach sechs bis acht
Wochen wird sie nachgezogen.</div>
<p class="schluss">Bis dahin gilt die Alarmrate als unbekannt, nicht als 18,5
pro Jahr.</p></section>
<a class="zurueck" href="index.html">Prognose der n&auml;chsten Abende</a>
</main></div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ort", default="berlin")
    ap.add_argument("--konfig", default=os.path.join(BASIS, "konfig.json"))
    a = ap.parse_args()

    with open(a.konfig) as f:
        kfg = json.load(f)
    ort = next((o for o in kfg["orte"] if o["name"] == a.ort), None)
    anzeige = (ort or {}).get("anzeige", a.ort.capitalize())

    kp = os.path.join(BASIS, "daten", "score_berlin_g0.5_2022_2025.json")
    with open(kp) as f:
        alle = sorted(v["s"] for v in json.load(f).values())

    liste = eintraege(a.ort, alle)
    n = len(liste)
    korpus = "%s SEIT DEM %d. %s %d" % (
        "NOCH KEINE BEWERTUNG" if n == 0
        else ("1 BEWERTUNG" if n == 1 else "%d BEWERTUNGEN" % n),
        ERSTER_ABEND.day, MONAT[ERSTER_ABEND.month - 1].upper(),
        ERSTER_ABEND.year)
    if liste:
        karten = "".join(karte(e) for e in liste)
    else:
        # Kein Platzhalterraster: der leere Zustand sagt, was zu tun ist.
        karten = ('<div class="leer">Hier stehen die Abende, die Du bewertet '
                  'hast. Die erste Aufforderung kommt abends nach '
                  'Sonnenuntergang.</div>')

    html = (VORLAGE.replace("__TOKENS__", tokens.quelltext())
            .replace("__KORPUS__", korpus)
            .replace("__KARTEN__", karten)
            .replace("__ORT__", anzeige))
    ziel = os.path.join(BASIS, "web", "bisher.html")
    with open(ziel, "w", encoding="utf-8") as f:
        f.write(html)
    print("geschrieben: %s (%d Bewertungen, %.1f kB)"
          % (ziel, n, os.path.getsize(ziel) / 1000.0))


if __name__ == "__main__":
    main()
