"""Die Alarmlaeufe muessen JEDEN Tag genau zweimal zuschlagen (T-0041/T-0045).

Seit dem 18.08.2026 ist der Lauf sonnenuntergangsrelativ: ein stuendlicher
launchd-Agent fragt in `alarm.im_laufenster()`, ob er dran ist.  Damit
haengt an einer Rechnung, was vorher an einer festen Uhrzeit hing - und
zwei Fehler waeren still:

  * FENSTER ZU SCHMAL.  Ist `lauf_fenster_min` kleiner als der Abstand
    zweier Agenten-Termine (60 Minuten), faellt an manchen Tagen KEIN Tick
    hinein.  Der Lauf bliebe aus, und zwar nur an manchen Tagen im Jahr -
    die Sorte Fehler, die man erst im Dezember bemerkt.
  * FENSTER ZU BREIT.  Passen zwei Ticks in EIN Fenster, wuerde doppelt
    gerechnet.  Das ist nicht nur Verschwendung: das Tagesbudget von
    Open-Meteo traegt knapp drei Laeufe (gemessen 18.08.2026), zwei sind
    verplant - ein dritter frisst den Nachholversuch.
  * FENSTER, DIE SICH UEBERLAPPEN.  Der Vormittagslauf steht fest in UTC,
    der Abendlauf wandert mit dem Sonnenuntergang.  Im Dezember rueckt der
    Abendlauf auf 12:53 UTC vor - noch weit genug weg, aber das ist eine
    Rechnung und keine Selbstverstaendlichkeit.

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

    print("\n=== 2. Ueber ein Jahr genau zwei Treffer pro Tag, je Fenster einer")
    minute = sorted(minuten)[0]
    schief, treffer = [], []
    tag = dt.date(2026, 1, 1)
    while tag < dt.date(2027, 1, 1):
        # Der Zustand wandert mit: ein bedientes Fenster darf nicht noch
        # einmal zuschlagen, ein anderes schon.
        zustand = {ort["name"]: {"laeufe": {}}}
        heute = []
        for stunde in range(24):
            jetzt = dt.datetime.combine(tag, dt.time(stunde, minute),
                                        dt.timezone.utc)
            name, _ = alarm.im_laufenster(jetzt, kfg, ort, zustand)
            if name:
                heute.append(name)
                treffer.append((tag, jetzt, name))
                zustand[ort["name"]]["laeufe"].setdefault(
                    str(tag), {})[name] = "x"
        if sorted(heute) != ["abends", "morgens"]:
            schief.append((tag, heute))
        tag += dt.timedelta(days=1)
    pruefe(not schief,
           "jeden Tag genau 'morgens' und 'abends' (%d Abweichungen%s)"
           % (len(schief), ", z.B. %s %s" % schief[0] if schief else ""))

    print("\n=== 3. Der Abendlauf folgt dem Sonnenuntergang")
    from zoneinfo import ZoneInfo
    BER = ZoneInfo("Europe/Berlin")
    proben = {t.month: j for t, j, n in treffer if n == "abends"}
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

    print("\n=== 4. Ein bedientes Fenster schlaegt nicht zweimal zu")
    tag0, j0, n0 = treffer[0]
    zustand = {ort["name"]: {"laeufe": {str(tag0): {n0: "x"}}}}
    name, grund = alarm.im_laufenster(j0, kfg, ort, zustand)
    pruefe(not name, "derselbe Anlauf abgelehnt: %s" % grund)
    # Der ALTE Zustandsschluessel war eine Zeichenkette. Er darf kein
    # Fenster blockieren, sonst faellt nach dem Umbau ein Tag aus.
    alt_zustand = {ort["name"]: {"laeufe": {str(tag0): "2026-01-01T00:00:00"}}}
    name, _ = alarm.im_laufenster(j0, kfg, ort, alt_zustand)
    pruefe(name == n0, "alter Zustandseintrag blockiert nicht (%s)" % name)

    print("\n=== 5. Die beiden Fenster ueberlappen nie")
    eng = []
    for tag, ziele in ((t, alarm.laufziele(
            dt.datetime.combine(t, dt.time(12), dt.timezone.utc), kfg, ort)[1])
            for t in (dt.date(2026, 1, 1) + dt.timedelta(days=k)
                      for k in range(0, 365, 7))):
        z = dict(ziele)
        abstand = abs((z["abends"] - z["morgens"]).total_seconds()) / 60
        if abstand < kfg["lauf_fenster_min"]:
            eng.append((tag, abstand))
    pruefe(not eng, "immer mehr als ein Fenster Abstand (%d zu eng%s)"
           % (len(eng), ", z.B. %s %.0f min" % eng[0] if eng else ""))

    print("\n=== 6. Die Seite misst gegen das Abendfenster")
    # letztes_laufziel() muss den Tag nennen, dessen Fenster schon zu ist.
    for tag, j, _n in [x for x in treffer if x[2] == "abends"][:3]:
        kurz_davor = j - dt.timedelta(minutes=5)
        kurz_danach = j + dt.timedelta(minutes=40)
        # letztes_laufziel() gibt seit dem 19.08.2026 einen ZEITPUNKT
        # zurueck, keinen Tag: der Altersstreifen vergleicht Zeitpunkte.
        vor = seite.letztes_laufziel(kurz_davor, kfg)
        nach = seite.letztes_laufziel(kurz_danach, kfg)
        pruefe(vor is None or vor.date() != tag,
               "%s: vor dem Fenster gilt der Vortag" % tag)
        pruefe(nach is not None and nach.date() == tag,
               "%s: nach dem Fenster gilt der Tag selbst" % tag)

    print("\n=== 7. Verschlafenes Abendfenster wird nachgeholt")
    # Am 18.08.2026 fehlte genau der eine Tick, der ins Abendfenster fiel
    # (Rechner im Ruhezustand). Ohne Nachholen faellt damit der ganze Tag
    # aus - und zwar leise.
    tag = dt.date(2026, 8, 18)
    std, _ = alarm.sonnenuntergang(tag, ort["breite"], ort["laenge"])
    su = (dt.datetime.combine(tag, dt.time(0), dt.timezone.utc)
          + dt.timedelta(hours=std))
    ziel = su - dt.timedelta(hours=kfg["lauf_vorlauf_stunden"])
    for versatz, erwartet in ((0, "abends"), (60, "abends"), (150, "abends")):
        j = ziel + dt.timedelta(minutes=versatz)
        name, grund = alarm.im_laufenster(j, kfg, ort, {})
        pruefe(name == erwartet,
               "%+4d min ums Fenster: %s (%s)" % (versatz, name, grund))
    nach_su = su + dt.timedelta(minutes=5)
    name, _ = alarm.im_laufenster(nach_su, kfg, ort, {})
    pruefe(name is None, "nach Sonnenuntergang wird NICHT mehr nachgeholt")
    # Und ein schon bedientes Abendfenster wird auch nicht nachgeholt.
    z = {ort["name"]: {"laeufe": {str(tag): {"abends": "x"}}}}
    name, _ = alarm.im_laufenster(ziel + dt.timedelta(minutes=90), kfg, ort, z)
    pruefe(name is None, "bereits gelaufen: kein Nachholen")

    print("")
    if fehler:
        print("FEHLGESCHLAGEN: %d" % len(fehler))
        raise SystemExit(1)
    print("alle Pruefungen bestanden")


if __name__ == "__main__":
    main()
