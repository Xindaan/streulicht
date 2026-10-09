"""Der Altersstreifen und der Waechter (T-0075, Review seiten#1, tests#10).

Bis zum 09.10.2026 entstand der Streifen "Diese Zahlen sind von ..." nur
beim Bauen in seite.main() - auf dem Mac, dessen Ausfall er melden soll -,
und kein Test fuehrte diese Regel je aus.  Seitdem:

  a) veraltet_streifen() mit fester Uhr: frisch -> kein Streifen, alt ->
     Streifen; Tage in EINER Zone gezaehlt (Abruf 22-24 Uhr UTC);
  b) seite.main() baut in einem Temp-Verzeichnis eine echte Seite: alter
     Stand -> Streifen im Markup, frischer -> keiner; beide tragen den
     Abrufzeitpunkt als <meta name="streulicht-geholt">;
  c) das Inline-Skript laeuft in node:vm mit gesetzter Uhr: alt -> Streifen,
     frisch -> keiner, steht er schon da -> kein zweiter; und es kommt fuer
     dieselbe Uhr zum SELBEN Urteil und Text wie veraltet_streifen();
  d) der Waechter (skripte/waechter.py, laeuft auf GitHub) liest den
     Zeitstempel aus der gespeicherten Seite: frisch -> 0, alt/fehlt -> 1.

Kein Netz; die echte Seite in web/ wird nicht angefasst.

Lauf:  .venv/bin/python3 skripte/test_frische.py      (braucht node)
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

import seite  # noqa: E402
import waechter  # noqa: E402

fehler = []
BERLIN = ZoneInfo("Europe/Berlin")


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


def utc(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


KFG = json.load(open(os.path.join(BASIS, "konfig.json")))

# --- a) Serverregel mit fester Uhr -----------------------------------------
print("a) veraltet_streifen() mit fester Uhr")
JETZT = utc("2026-10-09T18:00")
faellig = seite.letztes_laufziel(JETZT, KFG)
pruefe(faellig is not None and faellig.date() == date(2026, 10, 9),
       "Laufziel des Abends gefunden: %s" % faellig)
pruefe(seite.veraltet_streifen(faellig, JETZT, KFG, BERLIN) == "",
       "Abruf zur Fensterzeit -> kein Streifen")
s = seite.veraltet_streifen(utc("2026-10-07T15:20"), JETZT, KFG, BERLIN)
pruefe('class="veraltet"' in s and "von vorgestern" in s
       and "15:20" not in s and "(07.10., 17:20&nbsp;Uhr)" in s,
       "Abruf von vorgestern -> Streifen mit Ortszeit: %r" % s[:90])
# 22:30 UTC am 08.10. ist in Berlin schon der 09.10., 00:30.  Vorher zaehlte
# der Streifen hier "von gestern" (Ortsdatum minus UTC-Datum).
s = seite.veraltet_streifen(utc("2026-10-08T22:30"), JETZT, KFG, BERLIN)
pruefe("von heute fr\u00fch" in s and "(09.10., 00:30" in s,
       "Abruf 22:30 UTC: Tage in derselben Zone gezaehlt: %r" % s[:60])

# --- b) seite.main() in einem Temp-Verzeichnis ------------------------------
print("b) seite.main() baut echte Seiten")


def basis_mit(geholt):
    d = tempfile.mkdtemp(prefix="frische_")
    os.makedirs(os.path.join(d, "daten"))
    os.makedirs(os.path.join(d, "web"))
    shutil.copy(os.path.join(BASIS, "konfig.json"), d)
    shutil.copy(os.path.join(BASIS, "daten", "score_berlin_g0.5_2022_2025.json"),
                os.path.join(d, "daten"))
    heute = date.today()
    abende = {}
    for k in range(1, 4):            # kuenftige Abende, damit die Seite baut
        t = (heute + timedelta(days=k)).isoformat()
        abende[t] = {"p": 0.2 * k, "median": 0.3, "stunde_utc": 16.5,
                     "azimut": 255.0, "dt_h": 12.0 + 24 * k, "schirm": "mid",
                     "A": 0.5, "sicht": 0.5, "weg": 0.5, "n_member": 51,
                     "n_member_gesamt": 51, "bewertung": None,
                     "verlauf": [{"lauf": geholt[:10], "p": 0.2 * k}]}
    z = {"berlin": {"abende": abende, "alarme": {}, "laeufe": {},
                    "stand": {"geholt": geholt,
                              "modelllauf": geholt[:11] + "00:00+00:00",
                              "fenster": "abend"}}}
    with open(os.path.join(d, "daten", "zustand.json"), "w") as f:
        json.dump(z, f)
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


basen = []
try:
    jetzt_echt = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    d_frisch = basis_mit(jetzt_echt.isoformat(timespec="minutes"))
    d_alt = basis_mit("2026-01-02T15:20+00:00")
    basen += [d_frisch, d_alt]
    html_frisch = baue(d_frisch)
    html_alt = baue(d_alt)
    pruefe('class="veraltet"' not in html_frisch, "frischer Stand: kein Streifen")
    pruefe('<p class="veraltet">Diese Zahlen sind von vor' in html_alt,
           "alter Stand: Streifen im Markup")
    pruefe(waechter.geholt(html_frisch) == jetzt_echt,
           "Meta streulicht-geholt = stand.geholt (%s)"
           % waechter.geholt(html_frisch))
    pruefe(waechter.geholt(html_alt) == utc("2026-01-02T15:20"),
           "Meta auch auf der alten Seite")

    # --- c) das Inline-Skript in node:vm ---------------------------------
    print("c) Clientpruefung in node:vm mit gesetzter Uhr")
    HARNESS = r"""
const vm = require("vm");
const fs = require("fs");
const fall = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const metas = {};
for (const m of fall.html.matchAll(/<meta name="(streulicht-[^"]+)" content="([^"]*)">/g))
  metas[m[1]] = m[2];
const skripte = [...fall.html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const skript = skripte.find(s => s.includes("streulicht-"));
const eingefuegt = [];
const korpus = {parentNode: {insertBefore: (p, k) => eingefuegt.push(p)}};
const document = {
  querySelector(sel) {
    if (sel === ".veraltet") return fall.html.includes('class="veraltet"') ? {} : null;
    if (sel === ".korpus") return korpus;
    const m = /^meta\[name="([^"]+)"\]$/.exec(sel);
    if (m) return m[1] in metas ? {getAttribute: () => metas[m[1]]} : null;
    return null;
  },
  createElement: () => ({className: "", textContent: ""}),
};
const ctx = vm.createContext({document});
vm.runInContext("Date.now = () => " + fall.jetzt + ";", ctx);
if (skript) vm.runInContext(skript, ctx);
console.log(JSON.stringify({skript: !!skript,
  streifen: eingefuegt.map(p => ({klasse: p.className, text: p.textContent}))}));
"""
    hpfad = os.path.join(d_frisch, "harness.js")
    with open(hpfad, "w") as f:
        f.write(HARNESS)

    def client(html, jetzt):
        fpfad = os.path.join(d_frisch, "fall.json")
        with open(fpfad, "w") as f:
            json.dump({"html": html, "jetzt": int(jetzt.timestamp() * 1000)}, f)
        r = subprocess.run(["node", hpfad, fpfad], capture_output=True,
                           text=True, timeout=30)
        if r.returncode != 0:
            return {"fehler": r.stderr[-300:]}
        return json.loads(r.stdout)

    r = client(html_frisch, jetzt_echt + timedelta(hours=1))
    pruefe(r.get("skript") and r.get("streifen") == [],
           "frisch (+1 h): Skript da, kein Streifen (%s)" % r)
    r = client(html_frisch, jetzt_echt + timedelta(days=3))
    st = r.get("streifen") or []
    pruefe(len(st) == 1 and st[0]["klasse"] == "veraltet"
           and st[0]["text"].startswith("Diese Zahlen sind von vor"),
           "alt (+3 Tage): Streifen eingeblendet (%s)" % st)
    r = client(html_alt, jetzt_echt + timedelta(days=3))
    pruefe(r.get("streifen") == [],
           "Streifen schon im Markup -> kein zweiter (%s)" % r.get("streifen"))
    ohne_ziele = re.sub(r'<meta name="streulicht-laufziele"[^>]*>', "",
                        html_frisch)
    r29 = client(ohne_ziele, jetzt_echt + timedelta(hours=29))
    r31 = client(ohne_ziele, jetzt_echt + timedelta(hours=31))
    pruefe(r29.get("streifen") == [] and len(r31.get("streifen") or []) == 1,
           "ohne Laufziele: Grenze 30 h (29 h %d, 31 h %d Streifen)"
           % (len(r29.get("streifen") or []), len(r31.get("streifen") or [])))

    # Dieselbe Regel wie beim Bauen: fuer jede Uhr dasselbe Urteil und
    # derselbe Text wie veraltet_streifen().  Die Stunden sind so gewaehlt,
    # dass sie Fensteranfaenge und -enden der naechsten Tage ueberstreichen.
    abweichung = []
    for h in list(range(1, 80, 1)) + [24 * 6, 24 * 13]:
        j = jetzt_echt + timedelta(hours=h, minutes=7)
        server = seite.veraltet_streifen(jetzt_echt, j, KFG, BERLIN)
        server = re.sub(r"<[^>]+>", "", server).replace("&nbsp;", " ")
        st = client(html_frisch, j).get("streifen")
        text = st[0]["text"] if st else ""
        if text != server:
            abweichung.append((h, server[:50], text[:50]))
    pruefe(not abweichung,
           "Client = Server ueber 81 Uhrzeiten (Abweichungen: %s)"
           % abweichung[:3])

    # --- d) der Waechter auf der gespeicherten Seite ----------------------
    print("d) Waechter (skripte/waechter.py) auf gespeicherter Seite")
    ok, text = waechter.urteil(html_frisch, jetzt_echt + timedelta(hours=29))
    pruefe(ok, "frisch (29 h): ok - %s" % text)
    ok, text = waechter.urteil(html_frisch, jetzt_echt + timedelta(hours=31))
    pruefe(not ok, "alt (31 h): Alarm - %s" % text)
    ok, text = waechter.urteil(re.sub(r'<meta name="streulicht-geholt"[^>]*>',
                                      "", html_frisch), jetzt_echt)
    pruefe(not ok, "Zeitstempel fehlt: Alarm - %s" % text)
    # Und als Programm, so wie der Workflow es aufruft (Exitcode).
    sp = os.path.join(d_frisch, "seite.html")
    rc = {}
    for name, html in (("frisch", html_frisch), ("alt", html_alt)):
        with open(sp, "w", encoding="utf-8") as f:
            f.write(html)
        rc[name] = subprocess.run(
            [sys.executable, "-B", os.path.join(BASIS, "skripte", "waechter.py"),
             sp, "--grenze-h", "30"], capture_output=True, text=True).returncode
    pruefe(rc == {"frisch": 0, "alt": 1}, "Exitcodes frisch 0, alt 1: %s" % rc)
finally:
    for d in basen:
        shutil.rmtree(d, ignore_errors=True)

print()
if fehler:
    print("%d FEHLER" % len(fehler))
    sys.exit(1)
print("alle Pruefungen gruen")
