"""E2: der taegliche Alarmlauf.

Ablauf je Ort:
  1. Fanpunkte fuer jeden Vorlaufabend aus dem Sonnenuntergangsazimut.
  2. Pass 1 - Bewoelkung und Wind an den Fanpunkten, native 3-h-Schritte.
  3. Advektionsversatz je Schicht und Abend aus dem Ensemble-MITTELwind.
  4. Pass 2 - Bewoelkung an den versetzten Punkten.
  5. Score je Member, p = Anteil der Member ueber s*.
  6. Push, falls p >= p* und dieser Abend noch nicht gemeldet wurde.

ENTSCHEIDUNGEN, bewusst getroffen:

* Betriebsscore ist die 3-SCHICHT-Variante, nicht die niveauaufgeloeste.
  Grund: s* = 0.6325 ist auf der 3-Schicht-Klimatologie kalibriert.  Ein
  Betrieb auf der anderen Variante haette einen Schwellwert, der nicht zu
  ihm gehoert.  Wechsel erst, wenn die Ablation (T-0006) zeigt, dass die
  Rangfolgen zusammenfallen.

* Advektion mit dem Ensemble-MITTELwind je Schicht, nicht je Member.  Pro
  Member waeren es 40 Punkte x 3 Schichten x 51 Member x 10 Abende = 61 200
  Abfragepositionen; mit Mittelwind sind es 1 200 vor Dedup.  Preis: die
  Streuung der Verlagerung zwischen Membern (auf 300 hPa etwa +/- 30 km bei
  1.5 h) geht verloren, die Verlagerung selbst (rund 160 km) nicht.  Der
  zweitbeste Weg, aber um Groessenordnungen billiger als der beste.

* Der Score wird PRO MEMBER gerechnet, nie aus Mittelfeldern.  S ist ein
  Produkt nichtlinearer Terme; der Score des Mittelfelds ist nicht der
  Mittelwert der Scores (Jensen).

* Idempotenz ueber die Zustandsdatei: je (Ort, Abend) hoechstens ein Alarm.
"""
import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import sonnenuntergang, zielpunkt  # noqa: E402
import sonnen.score as sc  # noqa: E402
from sonnen.score import score  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITTER = 0.25
SCHICHTEN = ("low", "mid", "high")
# Repraesentatives Windniveau je Schicht (Schichtmitte)
WINDNIVEAU = {"low": 925, "mid": 600, "high": 300}
NTFY = "https://ntfy.sh"
WOCHENTAG = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


def fan_setzen(kfg):
    """Optionaler Sparfaecher aus der Konfiguration.

    ACHTUNG: s* = 0.6325 gilt fuer den Faecher der Klimatologie (5 Azimute,
    8 Distanzen).  Ein anderer Faecher liefert eine andere Score-Verteilung
    und damit einen anderen Schwellwert - wer hier reduziert, MUSS die
    Klimatologie mit demselben Faecher neu rechnen.  Deshalb steht der
    Hinweis hier und nicht in der README.
    """
    f = kfg.get("faecher")
    if not f:
        return False
    sc.FAECHER_AZIMUTE = tuple(float(x) for x in f["azimute"])
    sc.DISTANZEN_KM = tuple(float(x) for x in f["distanzen_km"])
    return True


def zelle(lat, lon):
    return (round(lat / GITTER), round(lon / GITTER))


def mitte(z):
    return (z[0] * GITTER, z[1] * GITTER)


def _hole(u, versuche=4):
    for n in range(versuche):
        try:
            with urllib.request.urlopen(u, timeout=600) as f:
                return json.load(f)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            grund = json.loads(e.read()).get("reason", "429")
            if "inutely" in grund and n < versuche - 1:
                print("   Minutenlimit, warte 65 s ...", flush=True)
                time.sleep(65)
                continue
            raise SystemExit("Kontingent: %s" % grund)
    raise SystemExit("unerreichbar")


def abfrage(zellen, variablen, modell, tage, block=25):
    aus = {}
    liste = sorted(zellen)
    for i in range(0, len(liste), block):
        teil = liste[i:i + block]
        u = ("https://ensemble-api.open-meteo.com/v1/ensemble?latitude=%s&longitude=%s"
             "&models=%s&hourly=%s&forecast_days=%d&temporal_resolution=native"
             % (",".join("%.4f" % mitte(z)[0] for z in teil),
                ",".join("%.4f" % mitte(z)[1] for z in teil),
                modell, ",".join(variablen), tage))
        d = _hole(u)
        if isinstance(d, dict):
            d = [d]
        for z, e in zip(teil, d):
            aus[z] = e["hourly"]
        time.sleep(1)
    return aus


def member_liste(h):
    return sorted({k.split("_member")[1] for k in h if "_member" in k})


def versatz_km(sp_kmh, richtung_grad, stunden):
    """Meteorologische Windrichtung: Richtung, AUS der es weht."""
    ms = sp_kmh / 3.6
    return (-ms * math.sin(math.radians(richtung_grad)) * stunden * 3.6,
            -ms * math.cos(math.radians(richtung_grad)) * stunden * 3.6)


def naechster_schritt(zeiten, ziel_dt):
    best, bi = None, None
    for i, t in enumerate(zeiten):
        dt = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        d = abs((dt - ziel_dt).total_seconds())
        if best is None or d < best:
            best, bi = d, i
    return bi, best / 3600.0


def lauf_ort(ort, kfg, zustand, trocken):
    breite, laenge = ort["breite"], ort["laenge"]
    heute = datetime.now(timezone.utc).date()
    km_lon = 111.32 * math.cos(math.radians(breite))

    abende = {}
    fan_zellen = set()
    for k in range(1, kfg["vorlauf_tage"] + 1):
        t = heute + timedelta(days=k)
        std, az = sonnenuntergang(t, breite, laenge)
        if std is None:
            continue
        punkte = {}
        for dv in sc.FAECHER_AZIMUTE:
            for d in sc.DISTANZEN_KM:
                p = ((breite, laenge) if d == 0.0
                     else zielpunkt(breite, laenge, (az + dv) % 360.0, d))
                punkte[(d, dv)] = p
                fan_zellen.add(zelle(*p))
        abende[t] = {"stunde": std, "azimut": az, "punkte": punkte}

    varn = ["cloud_cover_%s" % s for s in SCHICHTEN]
    for s in SCHICHTEN:
        varn += ["wind_speed_%dhPa" % WINDNIVEAU[s],
                 "wind_direction_%dhPa" % WINDNIVEAU[s]]
    print("   Pass 1: %d Zellen, %d Variablen" % (len(fan_zellen), len(varn)),
          flush=True)
    feld = abfrage(fan_zellen, varn, kfg["modell"], kfg["vorlauf_tage"] + 1)
    zeiten = feld[next(iter(feld))]["time"]
    mem = member_liste(feld[next(iter(feld))])
    print("   %d Member, %d native Schritte" % (len(mem), len(zeiten)), flush=True)

    # Advektionsversatz je (Abend, Schicht) aus dem Ensemble-Mittelwind am Ort
    zentrum = feld[zelle(breite, laenge)]
    versatz = {}
    for t, info in abende.items():
        ziel_dt = datetime(t.year, t.month, t.day, tzinfo=timezone.utc) \
            + timedelta(hours=info["stunde"])
        i, dt_h = naechster_schritt(zeiten, ziel_dt)
        info["schritt"], info["dt_h"] = i, dt_h
        vz = ziel_dt - datetime.fromisoformat(zeiten[i]).replace(tzinfo=timezone.utc)
        stunden = vz.total_seconds() / 3600.0
        for s in SCHICHTEN:
            sp = [zentrum.get("wind_speed_%dhPa_member%s" % (WINDNIVEAU[s], m), [None])[i]
                  for m in mem]
            ri = [zentrum.get("wind_direction_%dhPa_member%s" % (WINDNIVEAU[s], m), [None])[i]
                  for m in mem]
            sp = [x for x in sp if x is not None]
            ri = [x for x in ri if x is not None]
            if not sp:
                versatz[(t, s)] = (0.0, 0.0)
                continue
            # Richtungsmittel ueber Einheitsvektoren, nicht ueber Grad
            sx = sum(math.sin(math.radians(x)) for x in ri) / len(ri)
            cy = sum(math.cos(math.radians(x)) for x in ri) / len(ri)
            versatz[(t, s)] = versatz_km(sum(sp) / len(sp),
                                         math.degrees(math.atan2(sx, cy)) % 360.0,
                                         stunden)

    # Pass 2: versetzte Positionen
    versetzt_zellen, karte = set(), {}
    for t, info in abende.items():
        for s in SCHICHTEN:
            dx, dy = versatz[(t, s)]
            for schl, (la, lo) in info["punkte"].items():
                z = zelle(la + dy / 111.32, lo + dx / km_lon)
                karte[(t, s, schl)] = z
                versetzt_zellen.add(z)
    neu = versetzt_zellen - fan_zellen
    if kfg.get("advektion", True) and neu:
        print("   Pass 2: %d zusaetzliche Zellen" % len(neu), flush=True)
        feld.update(abfrage(neu, ["cloud_cover_%s" % s for s in SCHICHTEN],
                            kfg["modell"], kfg["vorlauf_tage"] + 1))

    ergebnisse = {}
    for t, info in abende.items():
        i = info["schritt"]
        werte = []
        for m in mem:
            def hole(d, dv, schicht, _i=i, _m=m, _t=t):
                z = (karte.get((_t, schicht, (d, dv))) if kfg.get("advektion", True)
                     else zelle(*info["punkte"][(d, dv)]))
                e = feld.get(z)
                if e is None:
                    return None
                r = e.get("cloud_cover_%s_member%s" % (schicht, _m))
                if r is None or _i >= len(r) or r[_i] is None:
                    return None
                return r[_i] / 100.0
            s, det = score(hole)
            werte.append((s, det))
        punkte_s = sorted(x[0] for x in werte)
        p = sum(1 for x in punkte_s if x >= kfg["schwelle_score"]) / len(punkte_s)
        med = punkte_s[len(punkte_s) // 2]
        besterdet = max(werte, key=lambda x: x[0])[1]
        ergebnisse[str(t)] = {
            "p": p, "median": med, "stunde_utc": info["stunde"],
            "azimut": info["azimut"], "dt_h": info["dt_h"],
            "schirm": besterdet["schirm"] if besterdet else None,
            "A": besterdet["A"] if besterdet else None,
            "sicht": besterdet["sicht"] if besterdet else None,
            "weg": besterdet["weg"] if besterdet else None,
            "n_member": len(punkte_s)}
    return ergebnisse


def begruendung(e):
    """Halbsatz fuers Push.

    Bewusst NICHT "klarer Westhorizont": der Score prueft nicht, ob man den
    Horizont sieht, sondern ob das Licht 200-400 km westlich in 1-2 km Hoehe
    durchkommt.  Man muss die Sonne gar nicht sehen koennen - und sie darf
    laengst untergegangen sein, waehrend hohe Wolken noch eine halbe Stunde
    weiterglueht.  Die alte Formulierung behauptete eine Sichtbedingung, die
    das Modell nirgends stellt.
    """
    teile = []
    schirm = {"high": "hohe Wolken", "mid": "mittelhohe Wolken"}.get(e["schirm"], "Wolken")
    teile.append(schirm if (e["A"] or 0) >= 0.35 else "wenig " + schirm)
    if (e["weg"] or 0) >= 0.6:
        teile.append("Licht kommt von Westen frei durch")
    elif (e["weg"] or 0) >= 0.3:
        teile.append("Lichtweg nach Westen teils frei")
    if (e["sicht"] or 1) < 0.5:
        teile.append("aber tiefe Decke ueber der Stadt")
    return ", ".join(teile)


def lokalzeit(tag, stunde_utc, zone):
    dt = datetime(int(tag[:4]), int(tag[5:7]), int(tag[8:]), tzinfo=timezone.utc) \
        + timedelta(hours=stunde_utc)
    try:
        from zoneinfo import ZoneInfo
        dt = dt.astimezone(ZoneInfo(zone))
    except Exception:
        pass
    return dt


def sende(topic, titel, text, prio="default"):
    req = urllib.request.Request(
        "%s/%s" % (NTFY, topic), data=text.encode("utf-8"),
        headers={"Title": titel.encode("utf-8").decode("latin-1", "replace"),
                 "Priority": prio, "Tags": "sunrise"})
    with urllib.request.urlopen(req, timeout=30) as f:
        return f.status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trocken", action="store_true",
                    help="rechnen und anzeigen, aber nichts senden")
    ap.add_argument("--konfig", default=os.path.join(BASIS, "konfig.json"))
    a = ap.parse_args()

    with open(a.konfig) as f:
        kfg = json.load(f)
    if fan_setzen(kfg):
        print("Sparfaecher aktiv: %d Azimute x %d Distanzen - s* ist damit "
              "NICHT mehr gueltig, Klimatologie neu rechnen!"
              % (len(sc.FAECHER_AZIMUTE), len(sc.DISTANZEN_KM)))
    zpfad = os.path.join(BASIS, "daten", "zustand.json")
    zustand = {}
    if os.path.exists(zpfad):
        with open(zpfad) as f:
            zustand = json.load(f)

    for ort in kfg["orte"]:
        name = ort["name"]
        print("=== %s" % ort["anzeige"], flush=True)
        erg = lauf_ort(ort, kfg, zustand, a.trocken)
        eintrag = zustand.setdefault(name, {"abende": {}, "alarme": {}})

        for tag in sorted(erg):
            e = erg[tag]
            alt = eintrag["abende"].get(tag, {})
            e["bewertung"] = alt.get("bewertung")
            e["verlauf"] = (alt.get("verlauf") or []) + [
                {"lauf": str(date.today()), "p": e["p"]}]
            eintrag["abende"][tag] = e
            lz = lokalzeit(tag, e["stunde_utc"], ort.get("zeitzone", "UTC"))
            marke = "*" if e["p"] >= kfg["schwelle_wahrscheinlichkeit"] else " "
            print("   %s %s %s %2.0f %%  Median %.2f  (%s, dt %.1f h)"
                  % (marke, WOCHENTAG[lz.weekday()], lz.strftime("%d.%m. %H:%M"),
                     100 * e["p"], e["median"], e["schirm"], e["dt_h"]))

            if e["p"] < kfg["schwelle_wahrscheinlichkeit"]:
                continue
            if tag in eintrag["alarme"]:
                continue          # Idempotenz: je Abend hoechstens ein Alarm
            titel = "Sonnenuntergang %s" % ort["anzeige"]
            text = "%s %s, %s Uhr - %.0f %%. %s" % (
                WOCHENTAG[lz.weekday()], lz.strftime("%d.%m."),
                lz.strftime("%H:%M"), 100 * e["p"], begruendung(e))
            if a.trocken:
                print("     [trocken] wuerde senden: %s" % text)
            else:
                sende(ort["ntfy_alarm"], titel, text, "high")
                eintrag["alarme"][tag] = {"gesendet": datetime.now(
                    timezone.utc).isoformat(timespec="seconds"), "p": e["p"]}
                print("     -> Push gesendet")

    if not a.trocken:
        os.makedirs(os.path.dirname(zpfad), exist_ok=True)
        with open(zpfad, "w") as f:
            json.dump(zustand, f, indent=1)
        print("\nZustand: %s" % zpfad)


if __name__ == "__main__":
    main()
