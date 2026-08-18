"""Der Alarmlauf muss JEDEN Tag genau einmal zuschlagen (T-0041).

Seit dem 18.08.2026 ist der Lauf sonnenuntergangsrelativ: ein stuendlicher
launchd-Agent fragt in `alarm.im_laufenster()`, ob er dran ist.  Damit
haengt an einer Rechnung, was vorher an einer festen Uhrzeit hing - und
zwei Fehler waeren still:

  * FENSTER ZU SCHMAL.  Ist `lauf_fenster_min` kleiner als der Abstand
    zweier Agenten-Termine (60 Minuten), faellt an manchen Tagen KEIN Tick
    hinein.  Der Lauf bliebe aus, und zwar nur an manchen Tagen im Jahr -
    die Sorte Fehler, die man erst im Dezember bemerkt.
  * FENSTER ZU BREIT.  Passen zwei Ticks hinein, wuerde zweimal gerechnet.
    Der zweite Lauf ist nicht nur Verschwendung: das Tagesbudget von
    Open-Meteo traegt genau zwei Laeufe (gemessen 18.08.2026), ein
    doppelter Lauf frisst also den Nachholversuch mit.

Geprueft wird ueber ein ganzes Jahr, nicht an einem Stichtag - der
Sonnenuntergang wandert in Berlin um mehr als fuenfeinhalb Stunden.

Lauf:  python3 skripte/test_lauffenster.py
"""
import datetime as dt
import json
import os
import plistlib
import sys

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASIS, "skripte"))
sys.path.insert(0, BASIS)

import alarm  # noqa: E402
import seite  # noqa: E402

fehler = []


def pruefe(bed, text):
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler.append(text)


def agenten_minute(datei):
    """Zu welcher Minute feuert der Agent, und wie viele Termine hat er?"""
    d = plistlib.load(open(os.path.join(BASIS, "betrieb", datei), "rb"))
    termine = d["StartCalendarInterval"]
    return {t["Minute"] for t in termine}, len(termine), d["ProgramArguments"]


def main():
    kfg = json.load(open(os.path.join(BASIS, "konfig.json")))
    ort = kfg["orte"][0]

    print("=== 1. Der Agent passt zur Rechnung")
    minuten, anzahl, args = agenten_minute("de.greatbelow.streulicht.alarm.plist")
    pruefe(anzahl == 24 and len(minuten) == 1,
           "stuendlich, eine feste Minute (%d Termine, Minuten %s)"
           % (anzahl, sorted(minuten)))
    pruefe("--geplant" in args,
           "der Agent uebergibt --geplant (sonst ignoriert er das Fenster)")
    pruefe(kfg["lauf_fenster_min"] >= 60,
           "Fenster mindestens so breit wie der Agentenabstand (%d min)"
           % kfg["lauf_fenster_min"])

    print("\n=== 2. Ueber ein Jahr genau ein Treffer pro Tag")
    minute = sorted(minuten)[0]
    ohne, doppelt, treffer = [], [], []
    tag = dt.date(2026, 1, 1)
    while tag < dt.date(2027, 1, 1):
        zustand = {}
        n = 0
        for stunde in range(24):
            jetzt = dt.datetime.combine(tag, dt.time(stunde, minute),
                                        dt.timezone.utc)
            ja, _ = alarm.im_laufenster(jetzt, kfg, ort, zustand)
            if ja:
                n += 1
                treffer.append((tag, jetzt))
        if n == 0:
            ohne.append(tag)
        elif n > 1:
            doppelt.append((tag, n))
        tag += dt.timedelta(days=1)
    pruefe(not ohne, "kein Tag ohne Lauf (%d Ausfaelle%s)"
           % (len(ohne), ", z.B. " + str(ohne[0]) if ohne else ""))
    pruefe(not doppelt, "kein Tag mit zwei Laeufen (%d)" % len(doppelt))

    print("\n=== 3. Die Laufzeit folgt dem Sonnenuntergang")
    from zoneinfo import ZoneInfo
    BER = ZoneInfo("Europe/Berlin")
    proben = {t.month: j for t, j in treffer}
    for m in (1, 6, 12):
        j = proben[m]
        ortszeit = j.astimezone(BER)
        std, _ = alarm.sonnenuntergang(j.date(), ort["breite"], ort["laenge"])
        su = (dt.datetime.combine(j.date(), dt.time(0), dt.timezone.utc)
              + dt.timedelta(hours=std))
        abstand = (su - j).total_seconds() / 3600
        pruefe(2.0 <= abstand <= 4.0,
               "Monat %2d: Lauf %s Ortszeit, %.1f h vor Sonnenuntergang"
               % (m, ortszeit.strftime("%H:%M"), abstand))

    print("\n=== 4. Zweimal am selben Tag wird verhindert")
    j = treffer[0][1]
    zustand = {ort["name"]: {"laeufe": {str(treffer[0][0]): "x"}}}
    ja, grund = alarm.im_laufenster(j, kfg, ort, zustand)
    pruefe(not ja, "zweiter Anlauf abgelehnt: %s" % grund)

    print("\n=== 5. Die Seite misst gegen dasselbe Fenster")
    # letztes_laufziel() muss den Tag nennen, dessen Fenster schon zu ist.
    for tag, j in treffer[:3]:
        kurz_davor = j - dt.timedelta(minutes=5)
        kurz_danach = j + dt.timedelta(minutes=40)
        pruefe(seite.letztes_laufziel(kurz_davor, kfg) != tag,
               "%s: vor dem Fenster gilt der Vortag" % tag)
        pruefe(seite.letztes_laufziel(kurz_danach, kfg) == tag,
               "%s: nach dem Fenster gilt der Tag selbst" % tag)

    print("")
    if fehler:
        print("FEHLGESCHLAGEN: %d" % len(fehler))
        raise SystemExit(1)
    print("alle Pruefungen bestanden")


if __name__ == "__main__":
    main()
