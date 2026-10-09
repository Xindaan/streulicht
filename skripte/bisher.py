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

Lauf:  .venv/bin/python3 skripte/bisher.py
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens  # noqa: E402
from seite import MONAT, WOCHENTAG, stufe  # noqa: E402
# EINE Quelle fuer das Anfangsdatum (T-0071).  Es stand hier als zweite
# Kopie: dort die Plausibilitaetsgrenze des Pollers, hier die Korpusangabe
# der Bilanzseite.  Zwei Zahlen mit derselben Bedeutung laufen auseinander,
# und die Bilanz behauptete dann einen Zeitraum, den der Poller gar nicht
# durchlaesst.  Der Import zieht nur stdlib nach, kein Netz.
from bewertungen_holen import ERSTER_ABEND  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ANLASS_TEXT = {"aufgefordert": "Auf Nachfrage bewertet",
               "alarm": "Nach Alarm bewertet"}

# Ab diesem Zeitpunkt rechnet der Alarmlauf die Advektion richtig (T-0063,
# Vorzeichen des Windversatzes): 04.09.2026, 16:50 Ortszeit (MESZ) = 14:50
# UTC.  Jede Zahl davor beschreibt einen verschobenen Faecher - die Bilanz
# nennt sie, statt sie wie die anderen zu zeigen (Review uiux#5).
ADVEKTIONSFIX = datetime(2026, 9, 4, 14, 50, tzinfo=timezone.utc)


def lauf_zeitpunkt(ort_zustand, lauf_tag):
    """Letzter Zeitpunkt (UTC), zu dem am Tag `lauf_tag` gerechnet wurde, oder None.

    `laeufe[tag]` ist je nach Alter eine Zeichenkette oder {morgens, abends}.
    """
    e = ((ort_zustand or {}).get("laeufe") or {}).get(lauf_tag)
    roh = list(e.values()) if isinstance(e, dict) else [e]
    zeiten = []
    for w in roh:
        try:
            z = datetime.fromisoformat(w)
        except (TypeError, ValueError):
            continue
        zeiten.append(z if z.tzinfo else z.replace(tzinfo=timezone.utc))
    return max(zeiten) if zeiten else None


def vor_advektionsfix(lauf_tag, zeit):
    """True, wenn der Lauf vor der Advektionskorrektur gerechnet wurde.

    Mit Zeitpunkt exakt; ohne (aeltere Zustaende) nur der Tag - am Tag der
    Korrektur selbst ohne Zeit "nicht belegt", also False statt geraten.
    """
    if zeit is not None:
        return zeit < ADVEKTIONSFIX
    return lauf_tag < ADVEKTIONSFIX.date().isoformat()


def vorhersage_zeile(e, tag, ort_zustand, alle_scores):
    """Der Satzteil "vorhergesagt: ..." samt Laufdatum und Korrekturvermerk.

    Das Laufdatum steht nur, wenn der Lauf nicht am Abend selbst war: bei
    6 von 26 Karten stammte die Prognose aus einem 1-3 Tage aelteren Lauf, am
    Abend selbst lief keiner (Review uiux#5).
    """
    rang = (sum(1 for x in alle_scores if x < e["median"])
            / len(alle_scores))
    name, _ = stufe(rang)
    lauf = ((e.get("verlauf") or [{}])[-1]).get("lauf")
    wann = ""
    if lauf and lauf != tag:
        d = date.fromisoformat(lauf)
        wann = " (Lauf vom %02d.%02d.)" % (d.day, d.month)
    text = "vorhergesagt%s: %s, %d. Perzentil" % (wann, name, round(rang * 100))
    if lauf and vor_advektionsfix(lauf, lauf_zeitpunkt(ort_zustand, lauf)):
        text += (" &#183; vor der Korrektur der Windverschiebung (Advektion) vom "
                 "04.09.2026 gerechnet, die Zahl ist belastet")
    return text


def ort_zustand_laden(ort_name):
    """Der Zustandseintrag des Ortes aus daten/zustand.json, oder {}."""
    zp = os.path.join(BASIS, "daten", "zustand.json")
    if not os.path.exists(zp):
        return {}
    with open(zp) as f:
        return json.load(f).get(ort_name) or {}


def eintraege(ort_name, alle_scores, ort_zustand=None, heute=None):
    """Abende mit Bewertung ODER Alarm, neueste zuerst - mit der Prognose dazu.

    Ein Alarmabend ohne Note gehoert auf die Bilanz (Review uiux#6): beide
    bisherigen Alarme (26.09., 30.09.) fehlten, weil der Abend ohne Note
    uebersprungen wurde - dabei sind sie die Faelle, an denen die Alarmrate
    haengt.  Sie tragen `ohne_note`.
    """
    z = ort_zustand if ort_zustand is not None else ort_zustand_laden(ort_name)
    heute = heute or date.today()
    abende = z.get("abende") or {}
    alarme = z.get("alarme") or {}
    aus = []
    for t in sorted(set(abende) | set(alarme), reverse=True):
        e = abende.get(t) or {}
        hat_note = e.get("bewertung") is not None
        if not hat_note and t not in alarme:
            continue
        d = date.fromisoformat(t)
        zeile = []
        if hat_note:
            zeile.append(ANLASS_TEXT.get(e.get("bewertung_anlass"),
                                         "Spontan bewertet"))
            if t in alarme and e.get("bewertung_anlass") != "alarm":
                zeile.append("Alarm gesendet")
        else:
            wahr = (alarme[t] or {}).get("p")
            zeile.append("Alarm gesendet%s" % (
                "" if wahr is None
                else " (%d %% der Modelll&auml;ufe &uuml;ber der Schwelle)"
                % round(wahr * 100)))
        if e.get("median") is None:
            zeile.append("keine Prognose f&uuml;r diesen Abend gerechnet")
        else:
            zeile.append(vorhersage_zeile(e, t, z, alle_scores))
        aus.append({"tag": t, "note": e.get("bewertung") if hat_note else None,
                    "ohne_note": not hat_note,
                    "offen": not hat_note and d >= heute,
                    "kopf": "%s %02d.%02d." % (WOCHENTAG[d.weekday()],
                                               d.day, d.month),
                    "zeile": " &#183; ".join(zeile)})
    return aus


def kopfzeile(liste, n_aufforderungen, erster_abend, ort_zustand=None):
    """Die Zeile ueber den Karten: Bewertungen MIT Nenner (Review uiux#6).

    "27 BEWERTUNGEN" ohne Nenner liess offen, ob das alle sind.  Der Nenner
    sind die Aufforderungen (`erinnerungen`, ein Eintrag je gesendeter
    Abenderinnerung).  "von" steht nur, wenn jede Bewertung auch zu einer
    Aufforderung gehoert - sonst waere der Nenner kleiner als der Zaehler
    oder nicht der der Bewertungen, und die Zeile faellt auf die blosse
    Aufzaehlung zurueck.
    """
    bewertet = [e for e in liste if not e.get("ohne_note")]
    n = len(bewertet)
    ohne = len(liste) - n
    erinnert = set(((ort_zustand or {}).get("erinnerungen") or {}))
    wort = ("NOCH KEINE BEWERTUNG" if n == 0
            else ("1 BEWERTUNG" if n == 1 else "%d BEWERTUNGEN" % n))
    if n_aufforderungen:
        auff = "%d AUFFORDERUNG%s" % (n_aufforderungen,
                                      "" if n_aufforderungen == 1 else "EN")
        alle_zu_aufforderung = (not ort_zustand
                                or all(e["tag"] in erinnert for e in bewertet))
        wort += (" VON " if alle_zu_aufforderung else " &#183; ") + auff
    wort = "%s SEIT DEM %d. %s %d" % (
        wort, erster_abend.day, MONAT[erster_abend.month - 1].upper(),
        erster_abend.year)
    if ohne:
        wort += " &#183; %d ALARMABEND%s OHNE NOTE" % (ohne, "" if ohne == 1 else "E")
    return wort


def karte(e):
    """Eine Bewertungskarte.  Note 0 ist eine Antwort, kein leerer Balken.

    T-0052, zweite Verteidigungslinie: `bewertungen_holen.py` laesst seit dem
    22.08.2026 nur noch Noten 0-5 herein, aber was VORHER hereinkam, liegt
    noch in `daten/zustand.json`.  Ohne die Pruefung unten stirbt hier der
    ganze Seitenbau: `%d` auf einer Zeichenkette und `k < e["note"]` gegen
    einen Nicht-Integer werfen beide TypeError - und `bisher.py` laeuft im
    10-Minuten-Agenten, also faellt damit die Auslieferung aus, nicht nur
    diese eine Karte.  Eine unbrauchbare Note wird gezeigt als das, was sie
    ist, statt die Seite mitzunehmen.
    """
    if e.get("ohne_note"):
        # Alarmabend ohne Note: kein Balken - ein leerer waere von "nicht
        # gesehen" (Note 0) nicht zu unterscheiden.
        return ('<article class="bkarte"><div class="bkopf"><span>%s</span>'
                '<span class="note-null">%s</span></div>'
                '<p class="bzeile">%s</p></article>'
                % (e["kopf"], "noch nicht bewertet" if e.get("offen")
                   else "nicht bewertet", e["zeile"]))
    n = e.get("note")
    if isinstance(n, bool) or not isinstance(n, int) or not 0 <= n <= 5:
        return ('<article class="bkarte"><div class="bkopf"><span>%s</span>'
                '<span class="note-null">unbrauchbar</span></div>'
                '<div class="balken">%s</div><p class="bzeile">%s</p></article>'
                % (e["kopf"], "".join("<i></i>" for _ in range(5)), e["zeile"]))
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
.topbar{position:sticky;top:0;z-index:5;
 padding:calc(14px + env(safe-area-inset-top)) 18px 12px;
 background:rgba(0,0,0,.72);
 -webkit-backdrop-filter:blur(18px) saturate(1.4);
 backdrop-filter:blur(18px) saturate(1.4);
 border-bottom:1px solid var(--karte)}
.topbar-inhalt{display:flex;align-items:center;justify-content:space-between}
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

/* Desktopfassung.  Kein eigener Entwurf - die Bilanzseite hat einen
   Bruchteil des Inhalts der Prognoseseite und braucht kein Raster.  Sie
   bekommt nur, was sie sonst neben der neuen Prognoseseite wie ein
   Telefon-Bildschirmfoto aussehen liesse: dieselbe Kopfleiste im
   1240er-Container und eine lesbare Spaltenbreite statt 390 px.
   Derselbe Breakpoint wie dort, damit beide Seiten gleichzeitig
   umschalten. */
@media (min-width:1000px){
 .rahmen{max-width:none;padding-bottom:72px}
 .topbar{padding:0}
 .topbar-inhalt{display:flex;align-items:center;justify-content:space-between;
  height:56px;max-width:var(--breite-gross);margin:0 auto;
  padding:0 var(--rand-gross)}
 .inhalt{max-width:720px;margin:0 auto;padding:34px var(--rand-gross) 0}
 .bkarte{padding:20px}
 .zurueck{max-width:340px}
}
</style></head><body>
<div class="rahmen">
<header class="topbar"><div class="topbar-inhalt">
<p class="marke-wort">Bisher</p>
<span class="ortspille">__ORT__</span></div></header>
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

    zustand = ort_zustand_laden(a.ort)
    liste = eintraege(a.ort, alle, zustand)
    n = len(liste)
    korpus = kopfzeile(liste, len(zustand.get("erinnerungen") or {}),
                       ERSTER_ABEND, zustand)
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
    print("geschrieben: %s (%d Karten, %.1f kB)"
          % (ziel, n, os.path.getsize(ziel) / 1000.0))


if __name__ == "__main__":
    main()
