"""UI/UX-Paket vom 09.10.2026 (T-0080, Review uiux#2/#4/#5/#6/#9-#13, seiten#6/#8, physik#5).

Gemessen wird, was Code TUT - nicht, was im Quelltext steht:

  A  Bilanz (bisher.py): Nenner in der Kopfzeile, Alarmabende ohne Note,
     Laufdatum, Vermerk fuer Laeufe vor der Advektionskorrektur; dazu der
     ganze Weg bisher.main() gegen eine Temp-Basis.
  B  Prognoseseite, Python-Seite: "< 6 %" statt "0 %", Vorauswahl nach
     Sonnenuntergang, Push-Auskunft bei veraltetem Stand, echte Umlaute,
     Markenfarbe durch eine kleine CSS-Kaskade, SVG-Style gegen fill-Attribut.
  C  Prognoseseite im Browser-Ersatz (node:vm mit DOM-Stubs): Hash-Auswahl,
     Vorauswahl mit der Uhr der Betrachter:innen, hashchange, Modifikator-
     tasten, preventDefault nur bei echtem Wechsel, veraltete Push-Auskunft.
  D  Push (alarm.py): Text und Klickziel; das Ziel wird der Seite als Hash
     uebergeben und waehlt dort den Abend.
  E  Faecherkarte: der ganze Faecher liegt ganzjaehrig im Bild.

Kein Netz, keine Uhr (feste Zeitpunkte), echte Seiten nur in Temp-Ordnern.

Lauf:  .venv/bin/python3 skripte/test_ui_paket.py      (braucht node)
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import alarm  # noqa: E402
import bisher  # noqa: E402
import faecher  # noqa: E402
import schnitt  # noqa: E402
import seite  # noqa: E402
import tokens  # noqa: E402
from sonnen.geometrie import sonnenuntergang  # noqa: E402
from sonnen.score import faecherpunkte  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


def utc(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


# ===========================================================================
print("A. Bilanz (bisher.py)")
# Erfundener Zustand, damit die Zahlen feststehen: drei Abende mit Note, zwei
# Alarmabende (einer ohne Note, einer mit), eine Aufforderung ohne Note.
SCORES = [i / 100.0 for i in range(100)]


def abend(median, lauf, note=None, anlass="aufgefordert"):
    e = {"median": median, "verlauf": [{"lauf": lauf, "median": median}],
         "bewertung": note}
    if note is not None:
        e["bewertung_anlass"] = anlass
    return e


def zustand():
    return {
        "abende": {
            "2026-08-25": abend(0.50, "2026-08-25", 4),     # vor der Korrektur
            "2026-09-20": abend(0.50, "2026-09-18", 3),     # Lauf 2 Tage alt
            "2026-09-26": abend(0.96, "2026-09-26"),        # Alarm, ohne Note
            "2026-09-30": abend(0.96, "2026-09-30", 2, "alarm"),
            "2026-10-12": abend(0.40, "2026-10-09"),        # Alarm, noch offen
        },
        "alarme": {"2026-08-25": {"p": 0.55}, "2026-09-26": {"p": 0.57},
                   "2026-09-30": {"p": 0.57}, "2026-10-12": {"p": 0.6}},
        "erinnerungen": {t: "x" for t in
                         ("2026-08-25", "2026-09-20", "2026-09-26",
                          "2026-09-30", "2026-10-05")},
        # Laufzeitpunkt je Lauftag: jeweils 14:25 UTC des Tages.
        "laeufe": {t: t + "T14:25:00+00:00" for t in
                   ("2026-08-25", "2026-09-18", "2026-09-26", "2026-09-30",
                    "2026-10-09")},
    }


HEUTE = date(2026, 10, 9)
z = zustand()
liste = bisher.eintraege("berlin", SCORES, z, HEUTE)
nach_tag = {e["tag"]: e for e in liste}

# --- Alarmabende ohne Note sichtbar (uiux#6) --------------------------------
pruefe(set(nach_tag) == {"2026-08-25", "2026-09-20", "2026-09-26",
                         "2026-09-30", "2026-10-12"},
       "die beiden Alarmabende ohne Note stehen in der Liste (%s)"
       % sorted(nach_tag))
ohne = nach_tag["2026-09-26"]
pruefe(ohne["ohne_note"] and ohne["note"] is None,
       "der Alarmabend ohne Note ist als solcher markiert")
k = bisher.karte(ohne)
pruefe("nicht bewertet" in k and 'class="balken"' not in k
       and "Alarm gesendet (57 %" in k,
       "seine Karte zeigt 'nicht bewertet' und den Alarm, aber keinen Balken")
pruefe("noch nicht bewertet" in bisher.karte(nach_tag["2026-10-12"])
       and "noch nicht bewertet" not in k,
       "ein Abend, der noch bevorsteht, heisst 'noch nicht', ein vergangener nicht")
pruefe("Nach Alarm bewertet" in nach_tag["2026-09-30"]["zeile"]
       and "Alarm gesendet" not in nach_tag["2026-09-30"]["zeile"],
       "Bewertung nach Alarm: 'Nach Alarm bewertet', nicht doppelt")
pruefe("Alarm gesendet" in nach_tag["2026-08-25"]["zeile"],
       "Alarm gesendet, aber auf Nachfrage bewertet: die Zeile nennt beides")
# Ein Abend ohne Note UND ohne Alarm bleibt draussen (die Aufforderung allein
# ist keine Bewertung).
z2 = zustand()
z2["abende"]["2026-10-01"] = abend(0.3, "2026-10-01")
pruefe("2026-10-01" not in {e["tag"] for e in
                            bisher.eintraege("berlin", SCORES, z2, HEUTE)},
       "ein Abend ohne Note und ohne Alarm bleibt draussen")

# --- Kopfzeile mit Nenner (uiux#6) -------------------------------------------
kopf = bisher.kopfzeile(liste, 53, date(2026, 8, 15), z)
pruefe(kopf.startswith("3 BEWERTUNGEN VON 53 AUFFORDERUNGEN SEIT DEM 15. AUGUST"),
       "Kopfzeile mit Nenner: %s" % kopf)
pruefe("2 ALARMABENDE OHNE NOTE" in kopf,
       "und die Alarmabende ohne Note werden gezaehlt")
# Waechter: "von" nur, wenn jede Bewertung auch eine Aufforderung hat.  Eine
# spontane Bewertung hat keine; "3 von 2" waere Unsinn.
z3 = zustand()
z3["erinnerungen"].pop("2026-09-20")
kopf3 = bisher.kopfzeile(bisher.eintraege("berlin", SCORES, z3, HEUTE), 4,
                         date(2026, 8, 15), z3)
pruefe(" VON " not in kopf3 and "4 AUFFORDERUNGEN" in kopf3,
       "eine Bewertung ohne Aufforderung -> kein 'von', nur aufzaehlen: %s"
       % kopf3)
pruefe(bisher.kopfzeile([], 0, date(2026, 8, 15), {}).startswith(
    "NOCH KEINE BEWERTUNG SEIT"), "leerer Zustand: unveraendert")

# --- Laufdatum (uiux#5) -------------------------------------------------------
pruefe("(Lauf vom 18.09.)" in nach_tag["2026-09-20"]["zeile"],
       "Prognose aus einem aelteren Lauf nennt das Laufdatum")
pruefe("Lauf vom" not in nach_tag["2026-09-30"]["zeile"]
       and "vorhergesagt:" in nach_tag["2026-09-30"]["zeile"],
       "Lauf am Abend selbst: kein Datum")

# --- Vermerk vor der Advektionskorrektur (uiux#5) ----------------------------
VERMERK = "Korrektur der Windverschiebung"
pruefe(VERMERK in nach_tag["2026-08-25"]["zeile"],
       "Lauf vom 25.08. (vor 04.09. 16:50): belastet vermerkt")
pruefe(VERMERK not in nach_tag["2026-09-20"]["zeile"]
       and VERMERK not in nach_tag["2026-09-30"]["zeile"],
       "Laeufe danach: kein Vermerk")
# Die Grenze auf die Minute: 14:49 UTC (= 16:49 MESZ) davor, 14:51 danach.
for zeit, erwartet in (("2026-09-04T14:49:00+00:00", True),
                       ("2026-09-04T14:51:00+00:00", False)):
    zg = {"abende": {"2026-09-05": abend(0.5, "2026-09-04", 3)},
          "laeufe": {"2026-09-04": {"morgens": "2026-09-04T09:20:00+00:00",
                                    "abends": zeit}},
          "erinnerungen": {}, "alarme": {}}
    zeile = bisher.eintraege("berlin", SCORES, zg, HEUTE)[0]["zeile"]
    pruefe((VERMERK in zeile) == erwartet,
           "Lauf am 04.09. um %s UTC -> Vermerk %s" % (zeit[11:16],
                                                       "ja" if erwartet else "nein"))
# Ohne Zeitpunkt im Zustand (alte Eintraege) entscheidet der Tag.
zg = {"abende": {"2026-09-03": abend(0.5, "2026-09-03", 3)}, "laeufe": {},
      "erinnerungen": {}, "alarme": {}}
pruefe(VERMERK in bisher.eintraege("berlin", SCORES, zg, HEUTE)[0]["zeile"],
       "ohne gespeicherten Laufzeitpunkt: der Tag entscheidet (03.09. davor)")

# --- der ganze Weg: bisher.main() gegen eine Temp-Basis ----------------------
KLIMA = os.path.join(BASIS, "daten", "score_berlin_g0.5_2022_2025.json")
d_main = tempfile.mkdtemp(prefix="uipaket_b_")
try:
    os.makedirs(os.path.join(d_main, "daten"))
    os.makedirs(os.path.join(d_main, "web"))
    shutil.copy(os.path.join(BASIS, "konfig.json"), d_main)
    shutil.copy(KLIMA, os.path.join(d_main, "daten"))
    with open(os.path.join(d_main, "daten", "zustand.json"), "w") as f:
        json.dump({"berlin": z}, f)
    alt = (bisher.BASIS, sys.argv)
    bisher.BASIS = d_main
    sys.argv = ["bisher.py", "--konfig", os.path.join(d_main, "konfig.json")]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            bisher.main()
    finally:
        bisher.BASIS, sys.argv = alt
    seite_html = open(os.path.join(d_main, "web", "bisher.html"),
                      encoding="utf-8").read()
finally:
    shutil.rmtree(d_main, ignore_errors=True)
pruefe("VON 5 AUFFORDERUNGEN" in seite_html
       and "2 ALARMABENDE OHNE NOTE" in seite_html,
       "bisher.main(): die Seite traegt Nenner und Alarmabende")
pruefe(seite_html.count('<article class="bkarte">') == 5
       and "Lauf vom 18.09." in seite_html and VERMERK in seite_html,
       "bisher.main(): fuenf Karten, Laufdatum und Vermerk stehen auf der Seite")

# ===========================================================================
print("B. Prognoseseite, Python-Seite")
# --- "0 %" bei 0 von 51 Membern (uiux#4) -------------------------------------
pruefe(seite.wahrsch_text(0.0, 51) == "< 6 %",
       "0 von 51 Membern -> '%s'" % seite.wahrsch_text(0.0, 51))
pruefe(seite.wahrsch_text(0.0, 17) == "< 18 %",
       "die Grenze folgt der Memberzahl (17 -> %s)" % seite.wahrsch_text(0.0, 17))
pruefe(seite.wahrsch_text(0.0, None) == "0 %",
       "ohne Memberzahl keine erfundene Grenze: '0 %'")
pruefe(seite.wahrsch_text(1 / 51.0, 51) == "2 %"
       and seite.wahrsch_text(0.57, 51) == "57 %",
       "von null verschiedene Werte bleiben Prozent")
pruefe(seite.wahrsch_text(None, 51) is None, "Rueckschau (None) bleibt None")

# --- Vorauswahl nach Sonnenuntergang (uiux#2) ---------------------------------
E = [{"tag": "2026-10-09", "unter": 1000}, {"tag": "2026-10-10", "unter": 2000},
     {"tag": "2026-10-11", "unter": None}, {"tag": "2026-10-12", "unter": 4000}]
E_ALLE = [dict(e, unter=e["unter"] or 3000) for e in E]


def ms(x):
    return datetime.fromtimestamp(x / 1000.0, timezone.utc)


pruefe(seite.vorwahl(E, ms(500), "2026-10-09") == 0,
       "vor dem Sonnenuntergang: der heutige Abend")
pruefe(seite.vorwahl(E, ms(1500), "2026-10-09") == 1,
       "danach: der naechste")
pruefe(seite.vorwahl(E, ms(2500), "2026-10-09") == 2,
       "Abend ohne Untergangszeit zaehlt nie als vorbei")
pruefe(seite.vorwahl(E_ALLE, ms(9000), "2026-10-09") == 3,
       "alles vorbei: der letzte Abend")
pruefe(seite.vorwahl(E, ms(0), "2026-10-10") == 1,
       "der erste Abend ab heute, auch wenn davor welche liegen")

# --- Push-Auskunft: nichts Widerspruechliches (uiux#4, seiten#6) -------------
kfg = json.load(open(os.path.join(BASIS, "konfig.json")))
still = seite.pushauskunft(0.08, 0.5, kfg)
pruefe("Es kommt kein Push" in still and "sind es nicht" not in still,
       "Normalfall: kein Push, und keine behauptete Alarmrate")
pruefe("noch nicht gemessen" in still and "Klimatologie" in still,
       "die 18 Abende stehen als Klimatologie, die Alarmrate als ungemessen")
pruefe("unter 6" in seite.pushauskunft(0.0, 0.5, kfg, n_member=51),
       "0 von 51: 'unter 6 %', nicht 'hoechstens 0 %'")
alt_text = seite.pushauskunft(0.08, 0.5, kfg, veraltet=True)
pruefe("Es kommt kein Push" not in alt_text and "letzten gerechneten" in alt_text
       and "ob inzwischen ein Push kam" in alt_text,
       "veralteter Stand: sagt nichts ueber die Zukunft, nur ueber die letzten Zahlen")
pruefe("&" not in seite.pushauskunft_veraltet(0.08, 0.5, 51)
       and "\u00df" in seite.pushauskunft_veraltet(0.0, 0.5, 51),
       "die Fassung fuer den Browser ist Klartext (kein HTML, echte Umlaute)")

# --- ASCII-Ersatz in sichtbaren Saetzen (uiux#11) ----------------------------
e_tief = {"schirm": "mid", "A": 0.6, "weg": 0.7, "sicht": 0.2}
b = alarm.begruendung(e_tief)
pruefe("tiefe Decke \u00fcber der Stadt" in b and "ueber" not in b,
       "begruendung(): echter Umlaut (%s)" % b)

# --- Seiten fuer B5/C bauen ---------------------------------------------------


def basis_mit(geholt, ps, sicht=0.2, ab=1, heute=None):
    d = tempfile.mkdtemp(prefix="uipaket_")
    os.makedirs(os.path.join(d, "daten"))
    os.makedirs(os.path.join(d, "web"))
    shutil.copy(os.path.join(BASIS, "konfig.json"), d)
    shutil.copy(KLIMA, os.path.join(d, "daten"))
    abende = {}
    for k, p in enumerate(ps, start=ab):   # kuenftige Abende, damit die Seite baut
        t = ((heute or date.today()) + timedelta(days=k)).isoformat()
        abende[t] = {"p": p, "median": 0.3, "stunde_utc": 16.5,
                     "azimut": 255.0, "dt_h": 12.0 + 24 * k, "schirm": "mid",
                     "A": 0.5, "sicht": sicht, "weg": 0.5, "n_member": 51,
                     "n_member_gesamt": 51, "bewertung": None,
                     "verlauf": [{"lauf": geholt[:10], "p": p}]}
    zs = {"berlin": {"abende": abende, "alarme": {}, "laeufe": {},
                     "stand": {"geholt": geholt,
                               "modelllauf": geholt[:11] + "00:00+00:00",
                               "fenster": "abend"}}}
    with open(os.path.join(d, "daten", "zustand.json"), "w") as f:
        json.dump(zs, f)
    return d


def baue(d):
    alt = (seite.BASIS, sys.argv)
    seite.BASIS = d
    sys.argv = ["seite.py", "--konfig", os.path.join(d, "konfig.json")]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            seite.main()
    finally:
        seite.BASIS, sys.argv = alt
    return open(os.path.join(d, "web", "index.html"), encoding="utf-8").read()


@contextlib.contextmanager
def feste_uhr(jetzt):
    """seite.main() sieht `jetzt` (aware, UTC) als Wanduhr und Ortstag."""
    tag = jetzt.astimezone(ZoneInfo("Europe/Berlin")).date()

    class D(date):
        @classmethod
        def today(cls):
            return tag

    class DT(datetime):
        @classmethod
        def now(cls, tz=None):
            return jetzt if tz is None else jetzt.astimezone(tz)

    alt = (seite.date, seite.datetime)
    seite.date, seite.datetime = D, DT
    try:
        yield
    finally:
        seite.date, seite.datetime = alt


def sichtbar(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S)
    h = re.sub(r"<svg.*?</svg>", "", h, flags=re.S)
    import html as _h
    return re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", h)))


# --- Markenfarbe durch eine kleine CSS-Kaskade (uiux#13) ---------------------
def kaskade(html, klassen, eigenschaft="color"):
    """Wert von `eigenschaft` fuer ein Element mit diesen Klassen.

    Nur Regeln aus Klassenketten (.a oder .a.b), nur Hauptstylesheet ohne
    @media-Bloecke: genau das, was fuer die Markenfarbe gilt.  Gewinner:
    hoehere Spezifitaet (Zahl der Klassen), bei Gleichstand die spaetere.
    """
    css = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    aus, i = [], 0
    while i < len(css):                       # @media-Bloecke ueberspringen
        if css[i] == "@":
            tiefe, j = 0, css.index("{", i)
            while True:
                tiefe += (css[j] == "{") - (css[j] == "}")
                j += 1
                if tiefe == 0:
                    break
            i = j
            continue
        j = css.find("{", i)
        if j < 0:
            break
        k = css.index("}", j)
        aus.append((css[i:j].strip(), css[j + 1:k]))
        i = k + 1
    bester = None
    for n, (sel, decl) in enumerate(aus):
        for s in sel.split(","):
            s = s.strip()
            if not re.fullmatch(r"(\.[\w-]+)+", s):
                continue
            cl = set(s.split(".")[1:])
            m = re.search(r"(?:^|;)\s*%s\s*:\s*([^;]+)" % eigenschaft, decl)
            if m and cl <= set(klassen):
                rang = (len(cl), n)
                if bester is None or rang > bester[0]:
                    bester = (rang, m.group(1).strip())
    return bester[1] if bester else None


basen = []
try:
    jetzt = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    d_neu = basis_mit(jetzt.isoformat(timespec="minutes"), [0.0, 0.2, 0.1])
    d_alt = basis_mit("2026-01-02T15:20+00:00", [0.0, 0.2, 0.1])
    basen += [d_neu, d_alt]
    html = baue(d_neu)
    html_alt = baue(d_alt)

    pruefe(kaskade(html, ["marke", "auffaellig"]) == "var(--akzent)",
           "Marke 'auffaellig' behaelt den Akzentring (%s)"
           % kaskade(html, ["marke", "auffaellig"]))
    pruefe(kaskade(html, ["marke", "selten"]) == "var(--akzent-tinte)",
           "Marke 'selten': Akzenttinte (%s)" % kaskade(html, ["marke", "selten"]))
    pruefe(kaskade(html, ["marke", "unauffaellig"]) == "var(--gedaempft)",
           "Marke 'unauffaellig': gedaempft (%s)"
           % kaskade(html, ["marke", "unauffaellig"]))

    # --- sichtbare Texte der gebauten Seite ----------------------------------
    t = sichtbar(html)
    pruefe("< 6 % Wahrscheinlichkeit" in t and "0 % Wahrscheinlichkeit" not in t,
           "Hero: '< 6 %' statt '0 %' bei 0 von 51 Membern")
    pruefe("Bewusst keine Prozentzahl" not in t
           and "Anteil der Modelll\u00e4ufe" in t,
           "Fusstext erklaert die Prozentzahl neben der Stufe")
    pruefe("Es kommt kein Push" in t and "Bei den letzten gerechneten" not in t,
           "frischer Stand: die normale Push-Auskunft")
    pruefe("data-veraltet=" in html,
           "frische Seite legt die Fassung fuer 'veraltet' fuer den Browser bereit")
    ta = sichtbar(html_alt)
    pruefe("Es kommt kein Push" not in ta and "Bei den letzten gerechneten" in ta,
           "alter Stand (Streifen im Markup): Push-Auskunft ohne 'kein Push'")
    pruefe("data-veraltet=" not in html_alt,
           "und ohne Attribut (der Server hat es schon entschieden)")
    pruefe("ueber" not in ta + t and "frueh" not in ta + t,
           "kein ASCII-Ersatz in den sichtbaren Saetzen")

    # --- Vorauswahl beim BAUEN (uiux#2): seite.main() mit fester Uhr ----------
    FEST = date(2026, 10, 9)
    d_fest = basis_mit("2026-10-09T10:00+00:00", [0.2, 0.1, 0.0], ab=0,
                       heute=FEST)
    basen.append(d_fest)
    su0 = seite.untergang_ms(FEST.isoformat()) / 1000.0
    for versatz_min, erwartet, wann in ((-60, 0, "vor"), (30, 1, "nach")):
        uhr = datetime.fromtimestamp(su0 + 60 * versatz_min, timezone.utc)
        with feste_uhr(uhr):
            h_fest = baue(d_fest)
        gew = int(re.search(r"let gewaehlt=(\d+);", h_fest).group(1))
        sel = [i for i, m in enumerate(re.findall(
            r'<button class="marke [^"]*" data-i="\d+" role="tab" '
            r'aria-selected="(\w+)"', h_fest)) if m == "true"]
        pruefe(gew == erwartet and sel == [erwartet],
               "seite.main(), %s dem Sonnenuntergang des heutigen Abends: "
               "Vorauswahl %d (Skript %d, Markup %s)" % (wann, erwartet, gew, sel))

    # ======================================================================
    print("C. Prognoseseite im Browser-Ersatz (node:vm)")
    HARNESS = r"""
const vm = require("vm");
const fs = require("fs");
const fall = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const skripte = [...fall.html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const haupt = skripte.find(s => s.includes("const META="));
const n = (fall.html.match(/class="marke /g) || []).length;
function elem() {
  const attrs = {}, klassen = new Set();
  return {textContent: "", innerHTML: "", className: "", tabIndex: 0,
    classList: {toggle(k, an) { an ? klassen.add(k) : klassen.delete(k); }},
    setAttribute(k, v) { attrs[k] = v; }, getAttribute: k => attrs[k],
    focus() { document.activeElement = this; }};
}
const marken = Array.from({length: n}, elem), fuesse = Array.from({length: n}, elem);
const byId = {}, doc = {}, win = {};
const document = {
  activeElement: null,
  querySelectorAll: s => s === ".marke" ? marken : s === ".achsenfuss div" ? fuesse : [],
  getElementById: id => byId[id] || (byId[id] = elem()),
  addEventListener: (t, f) => (doc[t] = doc[t] || []).push(f),
};
const window = {addEventListener: (t, f) => (win[t] = win[t] || []).push(f)};
const location = {hash: fall.hash};
const ctx = vm.createContext({document, window, location});
vm.runInContext("Date.now = () => " + fall.jetzt + ";", ctx);
vm.runInContext(haupt, ctx);
const meta = vm.runInContext("META", ctx);
const gew = () => vm.runInContext("gewaehlt", ctx);
const ausgabe = {start: gew(), tage: meta.map(m => m.tag), unter: meta.map(m => m.unter),
                 schritte: []};
for (const s of fall.schritte) {
  let vorbei = null;
  if (s.hash !== undefined) {
    location.hash = s.hash;
    (win.hashchange || []).forEach(f => f({}));
  } else {
    const e = {key: s.key, metaKey: !!s.meta, altKey: !!s.alt, ctrlKey: !!s.ctrl,
               prevented: false, preventDefault() { this.prevented = true; }};
    (doc.keydown || []).forEach(f => f(e));
    vorbei = e.prevented;
  }
  ausgabe.schritte.push({gewaehlt: gew(), prevented: vorbei,
                         selected: marken.map(m => m.getAttribute("aria-selected")).indexOf("true")});
}
console.log(JSON.stringify(ausgabe));
"""
    hpfad = os.path.join(d_neu, "harness.js")
    with open(hpfad, "w") as f:
        f.write(HARNESS)

    def browser(html, jetzt_ms, hash_="", schritte=()):
        fpfad = os.path.join(d_neu, "fall.json")
        with open(fpfad, "w") as f:
            json.dump({"html": html, "jetzt": jetzt_ms, "hash": hash_,
                       "schritte": list(schritte)}, f)
        r = subprocess.run(["node", hpfad, fpfad], capture_output=True,
                           text=True, timeout=30)
        if r.returncode != 0:
            return {"fehler": r.stderr[-400:]}
        return json.loads(r.stdout)

    r0 = browser(html, 0)
    pruefe("fehler" not in r0 and len(r0["tage"]) == 3
           and all(isinstance(u, int) for u in r0["unter"]),
           "Seite laeuft im Ersatz, drei Abende mit Untergangszeit (%s)"
           % (r0.get("fehler") or r0.get("unter")))
    T, U = r0["tage"], r0["unter"]
    pruefe(U[0] < U[1] < U[2], "Untergangszeiten steigen mit den Tagen")
    H = 3600 * 1000

    # --- Vorauswahl mit der Uhr der Betrachter:innen (uiux#2) -----------------
    pruefe(browser(html, U[0] - 3 * H)["start"] == 0,
           "vor dem Sonnenuntergang: erster Abend")
    pruefe(browser(html, U[0] + H)["start"] == 1,
           "nach dem Sonnenuntergang des ersten: der zweite")
    pruefe(browser(html, U[1] + H)["start"] == 2,
           "nach dem des zweiten: der dritte")
    pruefe(browser(html, U[2] + H)["start"] == 2,
           "alles vorbei: der letzte bleibt")
    pruefe(browser(html, U[0] + H, schritte=[{"key": "ArrowLeft"}]
                   )["schritte"][0]["gewaehlt"] == 0,
           "die Vorauswahl ist ein echter Zustand: Pfeil links geht zum ersten")

    # --- Deep-Link (uiux#9) ----------------------------------------------------
    pruefe(browser(html, U[0] - 3 * H, "#" + T[2])["start"] == 2,
           "Hash waehlt den Abend")
    pruefe(browser(html, U[0] + H, "#" + T[0])["start"] == 0,
           "der Hash schlaegt die Vorauswahl (auch nach Sonnenuntergang)")
    pruefe(browser(html, U[0] + H, "#2020-01-01")["start"] == 1,
           "unbekannter Abend im Hash: Vorauswahl bleibt")
    pruefe(browser(html, U[0] + H, "#")["start"] == 1,
           "leerer Hash: Vorauswahl bleibt")
    rh = browser(html, U[0] - 3 * H, "",
                 [{"hash": "#" + T[2]}, {"hash": "#nichts"}])
    pruefe(rh["schritte"][0]["gewaehlt"] == 2 and rh["schritte"][0]["selected"] == 2
           and rh["schritte"][1]["gewaehlt"] == 2,
           "hashchange waehlt um (und markiert die Marke); Unbekanntes ignoriert")
    # Push -> Seite: das Klickziel aus alarm.py waehlt den Abend.
    ziel = alarm.push_ziel("https://beispiel.invalid/streulicht/", T[1])
    pruefe(browser(html, U[0] - 3 * H, ziel.split("#")[1] if ziel and "#" in ziel else "")[
        "start"] == 1, "alarm.push_ziel() -> Hash -> Seite waehlt diesen Abend")

    # --- Tastatur (uiux#12) ----------------------------------------------------
    sch = [{"key": "ArrowRight", "meta": True},      # 0: Browser-Vor
           {"key": "ArrowLeft", "alt": True},        # 1: Browser-Zurueck
           {"key": "End", "ctrl": True},             # 2
           {"key": "ArrowLeft"},                     # 3: am Rand, kein Wechsel
           {"key": "Home"},                          # 4: schon am Anfang
           {"key": "ArrowRight"},                    # 5: echter Wechsel
           {"key": "End"},                           # 6: echter Wechsel
           {"key": "End"},                           # 7: schon am Ende
           {"key": "ArrowRight"},                    # 8: am Rand
           {"key": "a"},                             # 9: andere Taste
           {"key": "Home"}]                          # 10: echter Wechsel
    rt = browser(html, U[0] - 3 * H, "", sch)["schritte"]
    pruefe([s["gewaehlt"] for s in rt[:3]] == [0, 0, 0]
           and not any(s["prevented"] for s in rt[:3]),
           "Cmd/Alt/Ctrl + Taste: kein Wechsel, kein preventDefault")
    pruefe(rt[3]["gewaehlt"] == 0 and rt[3]["prevented"] is False
           and rt[4]["prevented"] is False,
           "Pfeil links / Home auf dem ersten Abend: kein preventDefault")
    pruefe(rt[5]["gewaehlt"] == 1 and rt[5]["prevented"] is True
           and rt[6]["gewaehlt"] == 2 and rt[6]["prevented"] is True,
           "Pfeil rechts / End: echter Wechsel, preventDefault")
    pruefe(rt[7]["prevented"] is False and rt[8]["prevented"] is False
           and rt[9]["prevented"] is False,
           "End/Pfeil rechts auf dem letzten und fremde Taste: kein preventDefault")
    pruefe(rt[10]["gewaehlt"] == 0 and rt[10]["prevented"] is True,
           "Home vom Ende aus: Wechsel")

    # --- veraltete Push-Auskunft im Browser (seiten#6) -------------------------
    FHARNESS = r"""
const vm = require("vm");
const fs = require("fs");
const fall = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const metas = {};
for (const m of fall.html.matchAll(/<meta name="(streulicht-[^"]+)" content="([^"]*)">/g))
  metas[m[1]] = m[2];
const skript = [...fall.html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]).find(s => s.includes("streulicht-"));
const pm = /<p class="push"( data-veraltet="([^"]*)")?>([\s\S]*?)<\/p>/.exec(fall.html);
const un = s => s.replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">")
                 .replace(/&#x27;/g, "'").replace(/&amp;/g, "&");
const push = {textContent: pm[3], getAttribute: k => k === "data-veraltet" && pm[2] ? un(pm[2]) : null};
const korpus = {parentNode: {insertBefore: () => {}}};
const document = {
  querySelector(sel) {
    if (sel === ".veraltet") return null;
    if (sel === ".korpus") return korpus;
    if (sel === ".push") return push;
    const m = /^meta\[name="([^"]+)"\]$/.exec(sel);
    if (m) return m[1] in metas ? {getAttribute: () => metas[m[1]]} : null;
    return null;
  },
  createElement: () => ({className: "", textContent: ""}),
};
const ctx = vm.createContext({document});
vm.runInContext("Date.now = () => " + fall.jetzt + ";", ctx);
vm.runInContext(skript, ctx);
console.log(JSON.stringify({vorher: pm[3].slice(0, 40), text: push.textContent}));
"""
    fpfad_h = os.path.join(d_neu, "fharness.js")
    with open(fpfad_h, "w") as f:
        f.write(FHARNESS)

    def frische(html, jetzt_dt):
        fp = os.path.join(d_neu, "ffall.json")
        with open(fp, "w") as f:
            json.dump({"html": html, "jetzt": int(jetzt_dt.timestamp() * 1000)}, f)
        r = subprocess.run(["node", fpfad_h, fp], capture_output=True, text=True,
                           timeout=30)
        return json.loads(r.stdout) if r.returncode == 0 else {"fehler": r.stderr[-300:]}

    rf = frische(html, jetzt + timedelta(hours=1))
    pruefe(rf.get("text", "").startswith("Kein Abend im Fenster"),
           "frisch im Browser: die Push-Auskunft bleibt (%s)"
           % (rf.get("text") or rf)[:40])
    rf = frische(html, jetzt + timedelta(days=3))
    pruefe("letzten gerechneten" in rf.get("text", "")
           and "Es kommt kein Push" not in rf.get("text", "")
           and "&" not in rf.get("text", ""),
           "Seite wird im Browser alt: die Auskunft wird ersetzt (%s)"
           % (rf.get("text") or rf)[:50])
finally:
    for d in basen:
        shutil.rmtree(d, ignore_errors=True)

# ===========================================================================
print("D. Push (alarm.py)")
e_push = {"schirm": "mid", "A": 0.6, "weg": 0.7, "sicht": 0.9}
text = alarm.push_text("Sa", "26.09.", "18:56", 0.5686, e_push)
pruefe(text.startswith("Sa 26.09., Sonnenuntergang 18:56 Uhr: 57 % der Modelll")
       and "Alarmschwelle" in text,
       "Text benennt Uhrzeit als Sonnenuntergang und Prozent als Anteil: %s"
       % text)
pruefe(text.endswith("Licht kommt von Westen frei durch.")
       and "Mittelhohe Wolken" in text,
       "Begruendung steht als Satz (gross, mit Punkt)")
pruefe(alarm.push_ziel("https://x.invalid/s", "2026-10-12")
       == "https://x.invalid/s/index.html#2026-10-12"
       and alarm.push_ziel("https://x.invalid/s/", "2026-10-12")
       == "https://x.invalid/s/index.html#2026-10-12",
       "Klickziel nennt den Abend (mit und ohne Schlussstrich)")
pruefe(alarm.push_ziel("", "2026-10-12") is None
       and alarm.push_ziel(None, "2026-10-12") is None,
       "ohne Basis-URL kein Ziel")

# ===========================================================================
print("E. Faecherkarte und SVG-Style")


def fan_feld(az):
    feld = {}
    for _d, _dv, la, lo in faecherpunkte(faecher.BREITE, faecher.LAENGE, az):
        feld["%d/%d" % (round(la / faecher.GITTER),
                        round(lo / faecher.GITTER))] = {"mid": 70, "low": 40,
                                                        "high": 20}
    return feld


raus = []
kleinster_massstab = 9.0
tage = [date(2026, 1, 1) + timedelta(days=k) for k in range(0, 365, 4)]
for d in tage:
    _, az = sonnenuntergang(d, faecher.BREITE, faecher.LAENGE)
    feld = fan_feld(az)
    svg = faecher.svg(feld, az, "mid", 250.0)
    VBW, VBH = faecher.VB
    rects = re.findall(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" '
                       r'height="([\d.]+)"', svg)
    if len(rects) != len(feld):
        raus.append((d.isoformat(), "Zellen", len(rects), len(feld)))
    for x, y, w, h in rects:
        x, y, w, h = float(x), float(y), float(w), float(h)
        if x < 0 or y < 0 or x + w > VBW or y + h > VBH:
            raus.append((d.isoformat(), round(az), "Zelle", round(x), round(y)))
            break
    cx, cy, sk = faecher.ansicht(az)
    kleinster_massstab = min(kleinster_massstab, sk)
    for m in re.finditer(r'<circle cx="([-\d.]+)" cy="([-\d.]+)" r="(?:3\.5|4\.5)"',
                         svg):
        if not (0 <= float(m.group(1)) <= VBW and 0 <= float(m.group(2)) <= VBH):
            raus.append((d.isoformat(), "Ort/Sonne", m.group(1), m.group(2)))
    for m in re.finditer(r'<line x1="[-\d.]+" y1="[-\d.]+" x2="([-\d.]+)" '
                         r'y2="([-\d.]+)"', svg):
        if not (0 <= float(m.group(1)) <= VBW and 0 <= float(m.group(2)) <= VBH):
            raus.append((d.isoformat(), "Strahl", m.group(1), m.group(2)))
    for m in re.finditer(r'<text x="([-\d.]+)" y="([-\d.]+)" font-size="13" '
                         r'text-anchor="middle">(\d+)</text>', svg):
        if not (10 <= float(m.group(1)) <= VBW - 10
                and 10 <= float(m.group(2)) <= VBH):
            raus.append((d.isoformat(), "Ringzahl", m.group(3), m.group(1),
                         m.group(2)))
pruefe(not raus,
       "%d Tage ueber das Jahr: Faecher, Ort, Sonne, Strahl und Ringzahlen "
       "liegen im Bild (Verstoesse: %s)" % (len(tage), raus[:3]))
pruefe(kleinster_massstab >= 0.4,
       "der Massstab bleibt lesbar (kleinster %.2f px/km)" % kleinster_massstab)
# Am Tag der Tagundnachtgleiche bleibt es beim alten Massstab (Ausschnitt wird
# nicht ohne Not verkleinert).
pruefe(abs(faecher.ansicht(270.0)[2] - faecher.SK_MAX) < 0.2,
       "um Azimut 270 kaum kleiner als der alte Massstab (%.2f)"
       % faecher.ansicht(270.0)[2])
# Die Ansicht wandert tatsaechlich mit dem Azimut (kein fester Ausschnitt).
pruefe(faecher.ansicht(231.0)[:2] != faecher.ansicht(312.0)[:2],
       "Berlin sitzt bei Suedwest und Nordwest an verschiedenen Stellen")


# --- SVG-Style gegen fill-Attribut (seiten#8) ---------------------------------
def effektives_fill(svg):
    """{Textinhalt: fill} nach der Kaskade: Stylesheet schlaegt Attribut."""
    regeln = []
    for m in re.finditer(r"<style>(.*?)</style>", svg, re.S):
        for sel, decl in re.findall(r"([^{}]+)\{([^}]*)\}", m.group(1)):
            f = re.search(r"(?:^|;)\s*fill\s*:\s*([^;]+)", decl)
            if not f:
                continue
            sel = sel.strip()
            if sel not in ("text", "text:not([fill])"):
                raise AssertionError("unbekannter Selektor %r - Test anpassen"
                                     % sel)
            regeln.append((sel, f.group(1).strip()))
    aus = {}
    for m in re.finditer(r"<text([^>]*)>([^<]*)</text>", svg):
        attr = re.search(r'\sfill="([^"]*)"', m.group(1))
        wert = attr.group(1) if attr else None
        for sel, v in regeln:
            if sel == "text" or (sel == "text:not([fill])" and attr is None):
                wert = v
        aus[m.group(2)] = wert
    return aus


_, az = sonnenuntergang(date(2026, 10, 12), faecher.BREITE, faecher.LAENGE)
feld = fan_feld(az)
TINTE2 = tokens.werte()["--tinte2"]
GEDAEMPFT = tokens.werte()["--gedaempft"]
bilder = {"Faecherkarte": faecher.svg(feld, az, "mid", 250.0),
          "Vertikalschnitt": schnitt.schnitt_neu("2026-10-12", feld)[0]}
for name, svg in bilder.items():
    fill = effektives_fill(svg)
    pruefe(fill.get("Berlin") and TINTE2 in fill["Berlin"]
           and GEDAEMPFT not in fill["Berlin"],
           "%s: 'Berlin' behaelt die Hervorhebung (%s)" % (name, fill.get("Berlin")))
    ohne_attr = [k for k, v in fill.items() if k != "Berlin"]
    pruefe(ohne_attr and all(GEDAEMPFT in (fill[k] or "") for k in ohne_attr),
           "%s: die uebrige Beschriftung bleibt gedaempft (%d Texte)"
           % (name, len(ohne_attr)))

print()
if fehler:
    print("%d FEHLER" % len(fehler))
    sys.exit(1)
print("alle Pruefungen gruen")
