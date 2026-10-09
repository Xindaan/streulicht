"""T-0087: Der Nachtlauf nach einem Ausfalltag.

Blieben Vormittags- und Abendlauf ohne Erfolg, wurde bis zum naechsten
Vormittag nichts gerechnet.  Seit T-0087 rechnet der erste Tick ab 02:00
Ortszeit (nach dem Wecken) einmal die Folgetage nach.  Geprueft wird das
VERHALTEN, nicht der Quelltext:

  1-6  `alarm.im_laufenster()` ueber alle Naechte eines Jahres (Sommer- und
       Winterzeit, beide Umstellungstage) und an den Grenzen: nur nach einem
       Ausfalltag, nur einmal, Schalter aus wirkt, nicht nach dem
       Vormittagsfenster, nicht vor 00 UTC.
  7    `alarm.main()` mit erfundenem Abruf: der Nachtlauf bucht "nachts",
       archiviert mit Modelllauf, schreibt ihn ins Log - und sendet KEINEN
       Push; der Vormittagslauf danach sendet ihn.
  8    `alarm.main()` bei aktiver Kontingentsperre: kein Abruf, keine
       Buchung; nach Ablauf der Sperre laeuft der Nachtlauf.

Wert-Huerde: Jede Bedingung in `nachtlauf()` und der Push-Riegel in `_main`
haben hier eine Pruefung, die rot wird, wenn genau diese Bedingung fehlt
(Negativproben 09.10.2026, siehe TASK.md T-0087).  test_lauffenster.py prueft
das Gegenstueck: ein lueckenloses Jahr hat keinen einzigen Nachtlauf.

Kein ntfy-POST: `alarm.sende` ist durch einen Aufzeichner ersetzt.  Kein
Netz: Abruf und Modelllauf sind erfunden.  Feste Zeiten, keine Wanduhr.

Lauf:  python3 skripte/test_nachtlauf.py
"""
import contextlib
import datetime as dt
import io
import json
import os
import shutil
import sys
import tempfile
from zoneinfo import ZoneInfo

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import alarm  # noqa: E402
import test_abruf  # noqa: E402
from zustandsdatei import lade, schreibe  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


KFG = json.load(open(os.path.join(BASIS, "konfig.json")))
ORT = KFG["orte"][0]
ZONE = ZoneInfo(ORT["zeitzone"])
UTC = dt.timezone.utc


def nacht(tag, laeufe, kfg=None, ort=None, bis_stunde=13):
    """Die Ticks (:20) von 00:20 Ortszeit an `tag` bis `bis_stunde` Uhr
    abfahren, wie der Agent: jeder Treffer wird unter dem Ortsdatum gebucht.
    Rueckgabe: [(jetzt UTC, Fenster)] der Treffer."""
    kfg = kfg or KFG
    ort = ort or ORT
    zone = ZoneInfo(ort["zeitzone"])
    zustand = {ort["name"]: {"laeufe": json.loads(json.dumps(laeufe))}}
    j = dt.datetime.combine(tag, dt.time(0, 20), zone).astimezone(UTC)
    ende = dt.datetime.combine(tag, dt.time(bis_stunde, 0), zone).astimezone(UTC)
    aus = []
    while j < ende:
        name, _ = alarm.im_laufenster(j, kfg, ort, zustand)
        if name:
            aus.append((j, name))
            lt = str(j.astimezone(zone).date())
            zustand[ort["name"]]["laeufe"].setdefault(lt, {})[name] = "x"
        j += dt.timedelta(hours=1)
    return aus


def vortag(tag, fenster):
    return {str(tag - dt.timedelta(days=1)): {f: "x" for f in fenster}}


print("T-0087  Nachtlauf nach einem Ausfalltag\n")

print("=== 1. Ein Jahr Ausfalltage: jede Nacht genau ein Nachtlauf um 02:20")
schief, winter, sommer, umstellung = [], 0, 0, []
tag = dt.date(2026, 1, 1)
while tag < dt.date(2027, 1, 1):
    treffer = nacht(tag, {})                      # Vortag ohne jeden Lauf
    namen = [n for _, n in treffer]
    if namen.count("nachts") != 1 or namen[0] != "nachts" \
            or "morgens" not in namen:
        schief.append((tag, namen))
    else:
        j = treffer[0][0]
        lokal = j.astimezone(ZONE)
        if lokal.strftime("%H:%M") != "02:20":
            umstellung.append((tag, lokal.strftime("%H:%M %Z")))
        elif lokal.utcoffset() == dt.timedelta(hours=1):
            winter += 1
            utc_w = j.strftime("%H:%M")
        else:
            sommer += 1
            utc_s = j.strftime("%H:%M")
    tag += dt.timedelta(days=1)
pruefe(not schief,
       "365 Naechte: je genau ein 'nachts', vor 'morgens' (%d Abweichungen%s)"
       % (len(schief), ", z.B. %s %s" % schief[0] if schief else ""))
pruefe(winter > 100 and sommer > 100,
       "Winterzeit %d Naechte um 02:20 MEZ (= %s UTC), Sommerzeit %d Naechte "
       "um 02:20 MESZ (= %s UTC)"
       % (winter, utc_w if winter else "-", sommer,
          utc_s if sommer else "-"))
# Am 29.03. gibt es kein 02:20 (die Uhr springt von 02:00 auf 03:00): der
# erste Tick nach dem Wecken ist 03:20 MESZ.  Sonst darf es keine Ausnahme
# geben - auch nicht am 25.10., wenn 02:20 zweimal vorkommt.
pruefe(umstellung == [(dt.date(2026, 3, 29), "03:20 CEST")],
       "einzige Ausnahme: Zeitumstellung 29.03. (%s)" % umstellung)

print("\n=== 2. Nur nach einem Ausfalltag")
T = dt.date(2026, 10, 10)                         # MESZ
T_W = dt.date(2026, 12, 10)                       # MEZ
for t in (T, T_W):
    for fenster in (["morgens"], ["abends"], ["vonhand"],
                    ["morgens", "abends"]):
        namen = [n for _, n in nacht(t, vortag(t, fenster))]
        pruefe("nachts" not in namen,
               "%s, Vortag mit %s: kein Nachtlauf (%s)"
               % (t, "+".join(fenster), namen))
# Ausfallserie: der Vortag hatte NUR einen Nachtlauf.  Der zaehlt nicht als
# Lauf - sonst bliebe ab dem zweiten Ausfalltag wieder jede Nacht leer.
namen = [n for _, n in nacht(T, vortag(T, ["nachts"]))]
pruefe(namen.count("nachts") == 1,
       "Vortag nur mit Nachtlauf (Ausfallserie): wieder ein Nachtlauf (%s)"
       % namen)
# Alter Zustand (Zeichenkette) ist Historie, kein Lauf - wie bei gelaufen().
namen = [n for _, n in nacht(T, {str(T - dt.timedelta(days=1)): "2026-10-09"})]
pruefe(namen.count("nachts") == 1,
       "alter Zustandseintrag am Vortag: zaehlt nicht als Lauf (%s)" % namen)

print("\n=== 3. Hoechstens einer je Nacht und Ort")
j = dt.datetime.combine(T, dt.time(3, 20), ZONE).astimezone(UTC)
for heute in (["nachts"], ["vonhand"]):
    z = {ORT["name"]: {"laeufe": {str(T): {f: "x" for f in heute}}}}
    name, grund = alarm.im_laufenster(j, KFG, ORT, z)
    pruefe(name is None,
           "heute schon %s gebucht: 03:20 kein Nachtlauf (%s)"
           % ("+".join(heute), grund))

print("\n=== 4. Schalter aus")
aus = dict(KFG, nachtlauf=False)
for t in (T, T_W):
    namen = [n for _, n in nacht(t, {}, kfg=aus)]
    pruefe(namen == ["morgens"],
           "%s, nachtlauf=false, Vortag leer: nur 'morgens' (%s)" % (t, namen))

print("\n=== 5. Nicht nach dem Vormittagsfenster")
# Der Nachtlauf ist kein nachgeholter Vormittagslauf.  Scheitert der
# Vormittagslauf, bleibt es beim Nachholen des ABENDlaufs.
halb = dt.timedelta(minutes=KFG["lauf_fenster_min"]) / 2
hh, mm = KFG["lauf_morgens_utc"].split(":")
morgens = dt.datetime.combine(T, dt.time(int(hh), int(mm)), UTC)
letzter = morgens - halb - dt.timedelta(minutes=30)        # 08:20 UTC
name, grund = alarm.im_laufenster(letzter, KFG, ORT, {})
pruefe(name == "nachts", "%s UTC, letzter Tick davor: nachts (%s)"
       % (letzter.strftime("%H:%M"), grund))
for j in (morgens + dt.timedelta(hours=1), morgens + dt.timedelta(hours=3)):
    name, grund = alarm.im_laufenster(j, KFG, ORT, {})
    pruefe(name is None, "%s UTC, Vormittagsfenster vorbei, nichts gelaufen: "
           "kein Nachtlauf (%s)" % (j.strftime("%H:%M"), grund))

print("\n=== 6. Nicht vor 00 UTC (neues Tageskontingent)")
# In Berlin bindet nur die Ortszeit.  Oestlich von UTC+2 laege 02:00
# Ortszeit noch im ALTEN UTC-Tag - im Kontingent des Ausfalltags.
tokio = dict(ORT, name="tokio", zeitzone="Asia/Tokyo")
tz = ZoneInfo("Asia/Tokyo")
j = dt.datetime.combine(T, dt.time(2, 20), tz).astimezone(UTC)
name, grund = alarm.im_laufenster(j, KFG, tokio, {})
pruefe(name is None, "Tokio 02:20 Ortszeit = %s UTC Vortag: kein Nachtlauf (%s)"
       % (j.strftime("%H:%M"), grund))
treffer = nacht(T, {}, ort=tokio, bis_stunde=18)
erster = [x for x in treffer if x[1] == "nachts"]
pruefe(len(erster) == 1 and erster[0][0].strftime("%H:%M") == "00:20",
       "Tokio: der Nachtlauf kommt um 00:20 UTC (%s)"
       % [(x[0].strftime("%d. %H:%M"), x[1]) for x in treffer])


# --- 7./8. alarm.main() mit Stubs ------------------------------------------

def lauf(zustand, jetzt, uhr=None, schwelle=0.0):
    """alarm.main() --geplant fahren.  Rueckgabe: dict mit Sendungen,
    Abrufen, Zustand, Log und den Archivdateien."""
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "daten"), exist_ok=True)
    kfg = json.loads(json.dumps(KFG))
    kfg["orte"][0]["ntfy_alarm"] = "t-test"
    kfg["schwelle_wahrscheinlichkeit"] = schwelle
    kp = os.path.join(d, "konfig.json")
    with open(kp, "w") as f:
        json.dump(kfg, f)
    schreibe(os.path.join(d, "daten", "zustand.json"), zustand)
    gesendet = []
    del test_abruf.ABRUFE[:]
    test_abruf.ZEITACHSE_START = jetzt.replace(hour=0, minute=0)
    alt = (alarm.BASIS, alarm.abfrage, alarm.modelllauf, alarm.warte_auf_netz,
           alarm.sende, alarm._jetzt_utc, sys.argv)
    alarm.BASIS = d
    alarm.abfrage = test_abruf.falscher_abruf
    alarm.modelllauf = lambda m: "2026-10-09T18:00+00:00"
    alarm.warte_auf_netz = lambda *a, **k: None
    alarm.sende = lambda *a, **k: gesendet.append((a, k)) or 200
    alarm._jetzt_utc = lambda: uhr or jetzt
    sys.argv = ["alarm.py", "--konfig", kp, "--geplant",
                "--jetzt", jetzt.replace(tzinfo=None).isoformat()]
    puffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(puffer):
            alarm.main()
    finally:
        (alarm.BASIS, alarm.abfrage, alarm.modelllauf, alarm.warte_auf_netz,
         alarm.sende, alarm._jetzt_utc, sys.argv) = alt
    archiv = os.path.join(d, "daten", "archiv", ORT["name"])
    aus = {"gesendet": gesendet, "abrufe": len(test_abruf.ABRUFE),
           "zustand": lade(os.path.join(d, "daten", "zustand.json")),
           "log": puffer.getvalue(),
           "archiv": {n: json.load(open(os.path.join(archiv, n)))
                      for n in (sorted(os.listdir(archiv))
                                if os.path.isdir(archiv) else [])}}
    shutil.rmtree(d, ignore_errors=True)
    return aus


print("\n=== 7. Der Nachtlauf im Betrieb: rechnet, bucht, sendet NICHT")
N = dt.datetime.combine(T, dt.time(2, 20), ZONE).astimezone(UTC)    # 00:20 UTC
leer = {ORT["name"]: {"abende": {}, "alarme": {}, "laeufe": {}}}
r = lauf(leer, N)
z = r["zustand"][ORT["name"]]
pruefe(r["abrufe"] > 0, "es wurde gerechnet (%d Abrufe)" % r["abrufe"])
pruefe(set((z.get("laeufe") or {}).get(str(T), {})) == {"nachts"},
       "gebucht als 'nachts' unter %s (%s)" % (T, z.get("laeufe")))
pruefe(len(z.get("abende") or {}) >= 2,
       "die Folgetage stehen im Zustand (%d Abende)" % len(z.get("abende") or {}))
pruefe(not r["gesendet"], "kein Push um 02:20 (%d Sendungen, Schwelle 0)"
       % len(r["gesendet"]))
pruefe(not z.get("alarme"), "kein Abend als gemeldet gebucht (%s)"
       % sorted(z.get("alarme") or {}))
a = r["archiv"].get("%s_nachts.json" % T) or {}
pruefe(a.get("modelllauf") == "2026-10-09T18:00+00:00"
       and a.get("fenster") == "nachts",
       "Archiv %s_nachts.json mit Modelllauf %s" % (T, a.get("modelllauf")))
pruefe("Modelllauf: 2026-10-09T18:00+00:00 (Fenster nachts)" in r["log"],
       "Logzeile nennt Modelllauf und Fenster")
# Der Vormittagslauf desselben Tages sendet, was nachts zurueckgestellt wurde.
M = dt.datetime.combine(T, dt.time(int(hh), int(mm)), UTC)
r2 = lauf(r["zustand"], M)
z2 = r2["zustand"][ORT["name"]]
prios = [x[0][3] if len(x[0]) > 3 else x[1].get("prio") for x in r2["gesendet"]]
pruefe(r2["gesendet"] and set(prios) == {"high"},
       "der Vormittagslauf sendet die zurueckgestellten Pushs (%d, Prioritaet %s)"
       % (len(r2["gesendet"]), sorted(set(prios))))
pruefe(set(z2["laeufe"][str(T)]) == {"nachts", "morgens"}
       and len(z2.get("alarme") or {}) == len(r2["gesendet"]),
       "und bucht sie (%d Alarme, Laeufe %s)"
       % (len(z2.get("alarme") or {}), sorted(z2["laeufe"][str(T)])))

print("\n=== 8. Kontingentsperre: kein Nachtlauf, solange sie gilt")
gesperrt = json.loads(json.dumps(leer))
gesperrt[alarm.SPERRSCHLUESSEL] = {
    "sperre_bis": (N + dt.timedelta(minutes=40)).isoformat(timespec="minutes"),
    "grund": "Hourly API request limit exceeded"}
r = lauf(gesperrt, N)
z = r["zustand"][ORT["name"]]
pruefe(r["abrufe"] == 0, "02:20 mit Sperre bis 03:00: kein Abruf (%d)"
       % r["abrufe"])
pruefe(not (z.get("laeufe") or {}).get(str(T)),
       "nichts gebucht - das Nachtfenster bleibt offen (%s)" % z.get("laeufe"))
N2 = N + dt.timedelta(hours=1)
r = lauf(r["zustand"], N2)
z = r["zustand"][ORT["name"]]
pruefe(r["abrufe"] > 0 and set(z["laeufe"].get(str(T), {})) == {"nachts"},
       "03:20 nach Ablauf der Sperre: der Nachtlauf laeuft (%d Abrufe, %s)"
       % (r["abrufe"], z["laeufe"].get(str(T))))

print("")
if fehler:
    print("FEHLGESCHLAGEN: %d" % len(fehler))
    raise SystemExit(1)
print("alle Pruefungen bestanden")
