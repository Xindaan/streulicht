"""WeatherNext 3 als Datenquelle - der Teil, der in us-east1 laufen muss.

WARUM UEBERHAUPT.  WN3 rechnet stuendlich statt 3-stuendig, wird stuendlich
initialisiert und liefert `low/medium/high_cloud_cover` als eigene
Modellfelder statt als Feuchtediagnostik.  Gegen unseren heutigen Verzug von
9,3 bis 22,3 Stunden (T-0065) stehen gemessene 6,5 bis 7,1 Stunden.

WARUM NICHT EINFACH ABRUFEN.  Die Zarr-Chunks sind NICHT raeumlich
unterteilt: ein Chunk ist ein Member, ein Zeitblock und die GANZE ERDE
(116 MB fuer Wolken, 3,7 MB je Druckflaeche fuer Wind).  Berlin kostet damit
genauso viel wie der Planet, und unser 68-Zellen-Faecher liegt vollstaendig
in genau einem Chunk - die Faechergeometrie ist also gratis, der Zugriff
nicht.  Ueber das Internet waeren das rund 27 USD je Lauf.  Innerhalb von
us-east1, wo die Buckets liegen, kostet derselbe Verkehr NICHTS.

DARAUS FOLGT DER SCHNITT.  Dieses Modul laeuft in us-east1 und darf `numpy`
und das `zstd`-Kommando benutzen.  Es schreibt eine kleine JSON-Datei in
GENAU der Form, die `alarm.py` von Open-Meteo kennt - Schluessel je Zelle,
darin `time` und je Variable eine Reihe, Member als `_memberNN`.  Der Mac
liest nur diese Datei; sein Alarmlauf bleibt damit
standardbibliotheks-rein (siehe README).

RUECKFALL.  Faellt hier irgendetwas aus, bleibt `konfig.json` auf
`"modell": "ecmwf_ifs025"` und der Betrieb laeuft unveraendert weiter.  Dieses
Modul ist eine zusaetzliche Quelle, kein Ersatzteil.

Lauf:   python3 skripte/wn3.py --probe          # ein Chunk, zum Nachsehen
        python3 skripte/wn3.py --tage 10 --aus daten/wn3.json
"""
import argparse
import datetime as _dt
import json
import math
import os
import subprocess
import sys

BUCKET = "gs://weathernext3_spatial/weathernext_3_0_0/zarr/2026_to_present"
ABRECHNUNG = os.environ.get("WN3_PROJEKT", "gardena-wetter")

# Namen bei uns -> Namen bei Google.  Unsere Schichten heissen wie bei
# Open-Meteo, Googles `medium` heisst bei uns `mid`.
WOLKE = {"low": "low_cloud_cover",
         "mid": "medium_cloud_cover",
         "high": "high_cloud_cover"}

# Dieselben Niveaus wie in alarm.py.  Alle drei sind in WN3 vorhanden
# (geprueft 08.09.2026: 50,100,150,200,250,300,400,500,600,700,850,925,1000).
WINDNIVEAU = {"low": 925, "mid": 600, "high": 300}

GITTER = 0.25                       # Zellraster von alarm.py, nicht von WN3

# Region, in der die Buckets liegen.  Innerhalb kostet der Verkehr nichts.
REGION = "us-east1"

# Ausserhalb der Region: harte Obergrenze je Prozess, in MB.  500 MB sind
# rund 0,06 USD - genug fuer Achsen, Metadaten und ein paar Probechunks,
# zu wenig fuer irgendetwas, das wehtut.
BUDGET_MB = 500

# Das Statistik-Bucket ist NICHT requester-pays (gemessen 08.09.2026:
# `requester_pays` steht nur beim Ensemble-Bucket).  Egress zahlt dort
# Google, nicht wir - die Grenze unten ist deshalb kein Kostenriegel,
# sondern eine Reissleine gegen eine Schleife, die nicht mehr aufhoert.
STAT_BUCKET = ("gs://weathernext3_statistics_spatial/"
               "weathernext_3_0_0_statistics/zarr/2026_to_present")
STAT_BUDGET_MB = 5000


# --- Kostenriegel ------------------------------------------------------
#
# WARUM.  Ein Wolkenchunk ist 116 MB und die ganze Erde; ein voller Lauf
# sind 223 GB.  In us-east1 kostet das null, ueber das Internet rund 27 USD
# - JE LAUF.  Zwischen beiden liegt kein Schalter, sondern nur die Frage,
# wo der Prozess zufaellig laeuft.  Genau diese Art Fehler soll nicht vom
# Aufpassen abhaengen, deshalb ein Riegel, der von selbst haelt.

class Budgetueberschreitung(RuntimeError):
    pass


def in_region(_holen=None):
    """True, wenn dieser Prozess in `REGION` laeuft.

    Gefragt wird der Metadatendienst von Compute Engine - er antwortet nur
    INNERHALB von Google Cloud und ist damit ein Nachweis, keine Annahme.
    Ausserhalb schlaegt der Aufruf fehl, und das Ergebnis ist False.
    """
    if _holen is None:
        import urllib.request

        def _holen():
            r = urllib.request.Request(
                "http://metadata.google.internal/computeMetadata/v1/"
                "instance/zone", headers={"Metadata-Flavor": "Google"})
            with urllib.request.urlopen(r, timeout=2) as f:
                return f.read().decode("utf-8")
    try:
        zone = _holen()
    except Exception:                                            # noqa: BLE001
        return False
    # Antwort ist "projects/123/zones/us-east1-b"
    return zone.rsplit("/", 1)[-1].startswith(REGION + "-")


class Budget:
    """Zaehlt geholte Bytes und bricht ab, bevor es Geld kostet."""

    def __init__(self, frei, grenze_mb=BUDGET_MB):
        self.frei = frei                  # in der Region -> unbegrenzt
        self.grenze = grenze_mb * 1024 * 1024
        self.bytes = 0

    def bucht(self, n):
        self.bytes += n
        if not self.frei and self.bytes > self.grenze:
            raise Budgetueberschreitung(
                "%.0f MB angefordert (nicht uebertragen), Grenze "
                "ausserhalb %s ist %d MB. "
                "Massenabruf gehoert in die Region - dort ist er gratis, "
                "hier kostet er rund 0,12 USD je GB."
                % (self.bytes / 1048576.0, REGION, self.grenze // 1048576))


# --- Zugriff -----------------------------------------------------------

def _lauf(args, roh=False):
    """gcloud aufrufen und stdout zurueckgeben; Fehlschlag NENNT den Grund."""
    r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise RuntimeError("%s -> rc=%d: %s"
                           % (" ".join(args[:3]), r.returncode,
                              r.stderr.decode("utf-8", "replace")[:400]))
    return r.stdout if roh else r.stdout.decode("utf-8")


def _lies(pfad, entpacken=True):
    """Ein Objekt holen und auspacken.  Gibt rohe Bytes zurueck.

    `gcloud storage cat` und `zstd -d` als Rohr: kein Zwischenfile, und der
    Speicher haelt nur einen Chunk (rund 148 MB entpackt) auf einmal.

    ENTPACKEN=FALSE fuer die Metadatei.  `zarr.json` liegt im Klartext,
    NUR die Datenchunks sind zstd-gepackt - auch die winzigen Achsen.  Das
    ist am 08.09.2026 beim ersten Lauf gegen echte Daten aufgefallen: der
    kuenstliche Speicher im Test liefert beides ungepackt und konnte den
    Unterschied deshalb gar nicht zeigen.
    """
    if not entpacken:
        return _lauf(["gcloud", "storage", "cat",
                      "--billing-project=" + ABRECHNUNG, pfad], roh=True)
    p1 = subprocess.Popen(["gcloud", "storage", "cat",
                           "--billing-project=" + ABRECHNUNG, pfad],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p2 = subprocess.Popen(["zstd", "-q", "-d", "-c"],
                          stdin=p1.stdout, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    p1.stdout.close()
    aus, _ = p2.communicate()
    p1.wait()
    if p1.returncode != 0 or p2.returncode != 0:
        raise RuntimeError("Chunk %s nicht lesbar (gcloud rc=%s, zstd rc=%s)"
                           % (pfad, p1.returncode, p2.returncode))
    return aus


class _Basis:
    """Gemeinsames von beiden Quellen: Pfad, Budget, roher Zugriff.

    Beide Buckets tragen denselben WN3-Lauf, aber in verschiedener Form -
    das Ensemble mit 64 Membern und Zeitbloecken zu sechs Stunden, die
    Statistik mit Perzentilen und stuendlicher Achse.  Was sie teilen, ist
    der Weg zu den Bytes; was sie trennen, sind Achsen und Zeitrechnung.
    """

    BUCKET = None

    def __init__(self, lauf, lies=_lies, budget=None):
        self.lauf = lauf                       # z.B. "20260908_00hr"
        self._lies = lies
        self.budget = budget if budget is not None else self._budget()
        self.wurzel = "%s/%s_01_preds/predictions.zarr" % (self.BUCKET, lauf)
        self.init = _dt.datetime.strptime(lauf, "%Y%m%d_%Hhr").replace(
            tzinfo=_dt.timezone.utc)
        self.meta = json.loads(
            self._roh("zarr.json", entpacken=False).decode("utf-8")
        )["consolidated_metadata"]["metadata"]
        self._achsen()

    def _budget(self):
        raise NotImplementedError

    def _achsen(self):
        raise NotImplementedError

    def _roh(self, rel, entpacken=True, erwartet=None):
        """Ein Objekt holen und aufs Budget buchen.

        ERWARTET IST DER PUNKT.  Ein Kostenriegel, der erst nach der
        Uebertragung bucht, hat schon bezahlt, wenn er anschlaegt - genau
        das ist am 08.09.2026 im ersten Versuch passiert: Grenze 1 MB, und
        er brach nach 148 geholten MB ab.  Bei Chunks ist die Groesse aus
        den Metadaten VORHER bekannt (Form mal vier Byte), also wird vorher
        gebucht.  Nur fuer die kleinen Achsen und `zarr.json`, deren
        Groesse man erst hinterher kennt, wird nachgebucht - sie liegen
        zusammen unter einem Megabyte.
        """
        if erwartet is not None:
            self.budget.bucht(erwartet)
            return self._lies("%s/%s" % (self.wurzel, rel), entpacken)
        b = self._lies("%s/%s" % (self.wurzel, rel), entpacken)
        self.budget.bucht(len(b))
        return b

    def _achse(self, name, dtype):
        import numpy as np
        return np.frombuffer(self._roh("%s/c/0" % name), dtype=dtype)

    def form(self, var):
        return self.meta[var]["shape"]


class Quelle(_Basis):
    """Das volle 64-Member-Ensemble.  Requester-pays, teuer ausserhalb."""

    BUCKET = BUCKET

    def _budget(self):
        # Kein Budget uebergeben -> selbst feststellen, wo wir laufen.
        return Budget(in_region())

    def _achsen(self):
        self.lat01 = self._achse("lat_0p1", "<f4")
        self.lon01 = self._achse("lon_0p1", "<f4")
        self.lat025 = self._achse("lat_0p25", "<f4")
        self.lon025 = self._achse("lon_0p25", "<f4")
        self.level = self._achse("level", "<i4")
        self.lead = self._achse("lead_time", "<i8")
        self.sub = self._achse("lead_subtime", "<i8")
        self.sample = self._achse("sample", "<i8")

    # -- Zeit

    def zeiten(self, i):
        """Die sechs gueltigen Zeiten des Zeitblocks `i`.

        `lead_subtime` ist [-5,-4,-3,-2,-1,0] STUNDEN RELATIV zum Blockende,
        und das Blockende ist `init + lead_time[i]`.  Das steht so in den
        Daten und ist nicht geraten: gegengeprueft am 08.09.2026 gegen das
        Array `datetime`, das dieselbe Zeit unabhaengig noch einmal fuehrt
        (lead_time[10] = 66 h, datetime[10] = 2026-09-10T18:00Z, init war
        2026-09-08T00Z).  Ein Vorzeichenfehler hier waere ein stiller
        Versatz von bis zu fuenf Stunden.
        """
        ende = self.init + _dt.timedelta(hours=int(self.lead[i]))
        return [ende + _dt.timedelta(hours=int(s)) for s in self.sub]

    def block(self, ziel):
        """Index des Zeitblocks, der `ziel` enthaelt - oder None."""
        for i in range(len(self.lead)):
            if ziel in self.zeiten(i):
                return i
        return None

    # -- Felder

    def wolke(self, schicht, member, i):
        """Ein Wolkenchunk: (6, len(lat01), len(lon01)), Werte 0..1."""
        import numpy as np
        var = WOLKE[schicht]
        n_sub, n_lat, n_lon = self.form(var)[2:]
        b = self._roh("%s/c/%d/%d/0/0/0" % (var, member, i),
                      erwartet=n_sub * n_lat * n_lon * 4)
        return np.frombuffer(b, dtype="<f4").reshape(n_sub, n_lat, n_lon)

    def wind(self, richtung, hpa, member, i):
        """Ein Windchunk: (6, len(lat025), len(lon025)), m/s.

        ACHTUNG, andere Chunk-Form als bei den Wolken: Wind ist nach
        Druckflaeche gechunkt (`[1,1,1,lat,lon]`), Wolken nach Zeitblock
        (`[1,1,6,lat,lon]`).  Der Wind-Chunk traegt also nur EINE Stunde
        je Datei - die sechs Stunden liegen in sechs Objekten.
        """
        import numpy as np
        var = "%s_component_of_wind" % richtung
        k = int(list(self.level).index(hpa))
        n_lat, n_lon = self.form(var)[3:]
        b = self._roh("%s/c/%d/%d/%d/0/0" % (var, member, i, k),
                      erwartet=n_lat * n_lon * 4)
        return np.frombuffer(b, dtype="<f4").reshape(n_lat, n_lon)



class Statistik(_Basis):
    """Mittel und fuenf Perzentile, 0,1 Grad, stuendlich - und kostenlos.

    WOZU, wenn hier kein p herauskommt.  Unser p ist der Anteil der Member,
    deren SCORE ueber s* liegt - eine nichtlineare Funktion ueber 68
    Faecherzellen und drei Schichten.  Aus Perzentilen je Gitterpunkt laesst
    sich kein einziger kohaerenter Member rekonstruieren, also auch kein
    Score und kein p.  Diese Quelle kann den Alarm daher NICHT tragen.

    Sie kann aber die Frage beantworten, die vor der ganzen Betriebsfrage
    steht: trifft WN3 unsere Abende ueberhaupt besser als ECMWF?  Dafuer
    genuegt das Medianfeld, und es kostet nichts.  Faellt der Vergleich
    gegen ECMWF aus, eruebrigt sich der Rest.

    Andere Form als beim Ensemble: `lead_time` laeuft hier direkt stuendlich
    von 1 bis 360, es gibt kein `lead_subtime`.  Gegengeprueft am
    08.09.2026 gegen das `datetime`-Array (lead_time[66] = 67 h,
    datetime[66] = 2026-09-10T19:00Z bei Init 2026-09-08T00Z).
    """

    BUCKET = STAT_BUCKET
    STATISTIKEN = ("mean", "p10", "p25", "p50", "p75", "p90")

    def _budget(self):
        # Keine Kostenfrage, sondern eine Reissleine: das Bucket ist nicht
        # requester-pays, aber eine Schleife ohne Ende bleibt eine Schleife.
        return Budget(frei=False, grenze_mb=STAT_BUDGET_MB)

    def _achsen(self):
        self.lat01 = self._achse("lat_0p1", "<f4")
        self.lon01 = self._achse("lon_0p1", "<f4")
        self.lead = self._achse("lead_time", "<i8")

    def zeiten(self):
        return [self.init + _dt.timedelta(hours=int(h)) for h in self.lead]

    def schritt(self, ziel):
        """Index der Stunde `ziel` - oder None, wenn sie nicht drin ist."""
        for i, t in enumerate(self.zeiten()):
            if t == ziel:
                return i
        return None

    def feld(self, schicht, statistik, i):
        """Ein Stundenfeld: (len(lat01), len(lon01)), Werte 0..1."""
        import numpy as np
        var = "%s_%s" % (WOLKE[schicht], statistik)
        n_lat, n_lon = self.form(var)[1:]
        b = self._roh("%s/c/%d/0/0" % (var, i), erwartet=n_lat * n_lon * 4)
        return np.frombuffer(b, dtype="<f4").reshape(n_lat, n_lon)

    def punkte(self, zellen, ziele, schichten=("low", "mid", "high"),
               statistik="p50", melde=print):
        """Wie `abfrage()`, aber ohne Member - die Namen bleiben schlicht.

        Bewusst KEIN `_memberNN`: eine Reihe ohne Member als Member zu
        etikettieren waere die Art Etikettenschwindel, die spaeter jemand
        fuer ein Ensemble haelt.
        """
        if statistik not in self.STATISTIKEN:
            raise ValueError("unbekannte Statistik %r, moeglich sind %s"
                             % (statistik, ", ".join(self.STATISTIKEN)))
        schritte = sorted({i for i in (self.schritt(z) for z in ziele)
                           if i is not None})
        fehlend = [z for z in ziele if self.schritt(z) is None]
        if fehlend:
            melde("   Ausserhalb des Vorlaufs: %s"
                  % ", ".join(t.isoformat() for t in fehlend))
        zellen = sorted(zellen)
        idx = {z: (_index(self.lat01, mitte(z)[0]),
                   _index(self.lon01, _laenge(mitte(z)[1]))) for z in zellen}
        zeit = [self.zeiten()[i] for i in schritte]
        aus = {z: {"time": [t.strftime("%Y-%m-%dT%H:%M") for t in zeit]}
               for z in zellen}
        n = 0
        for schicht in schichten:
            reihe = {z: [] for z in zellen}
            for i in schritte:
                f = self.feld(schicht, statistik, i)
                n += 1
                for z in zellen:
                    a, b = idx[z]
                    reihe[z].append(prozent(f[a, b]))
            for z in zellen:
                aus[z]["cloud_cover_%s" % schicht] = reihe[z]
        melde("   %d Felder gelesen (%s), %.0f MB"
              % (n, statistik, self.budget.bytes / 1048576.0))
        return aus


# --- Gitter ------------------------------------------------------------

def _index(achse, wert):
    """Naechster Index auf einer aufsteigenden Achse."""
    import numpy as np
    return int(np.argmin(np.abs(achse - wert)))


def _laenge(lon):
    """Unsere Laengen sind -180..180, WN3 fuehrt 0..359,9."""
    return lon % 360.0


def mitte(z):
    return (z[0] * GITTER, z[1] * GITTER)


# --- Umrechnung --------------------------------------------------------

def prozent(x):
    """WN3 fuehrt Bedeckung als 0..1, Open-Meteo als 0..100."""
    return None if x != x else round(float(x) * 100.0, 1)


def geschwindigkeit(u, v):
    return round(math.hypot(float(u), float(v)), 2)


def richtung(u, v):
    """Meteorologische Richtung: WOHER der Wind weht, in Grad.

    Nicht die mathematische Richtung.  Ein Wind mit u>0 (nach Osten) kommt
    aus WESTEN und ist damit 270 Grad - genau das liefert die Formel.
    """
    return round((270.0 - math.degrees(math.atan2(float(v), float(u))))
                 % 360.0, 1)


# --- Hauptweg ----------------------------------------------------------

def feldname(basis, m):
    """Wie in alarm.py, nur ohne Kontrolllauf - WN3 hat keinen."""
    return "%s_member%02d" % (basis, m)


def abfrage(quelle, zellen, ziele, schichten=("low", "mid", "high"),
            member=None, wind_zelle=None, melde=print):
    """Die Form, die `alarm.py` von Open-Meteo kennt.

    `ziele` sind die gewuenschten Zeitpunkte (Sonnenuntergaenge, UTC).
    Geholt wird der Zeitblock, der sie enthaelt - mit allen sechs Stunden,
    denn sie kosten nichts extra und druecken max |dt| auf 30 Minuten.

    `wind_zelle` bekommt zusaetzlich Wind.  Genau eine Zelle, wie in
    alarm.py: der Advektionsversatz ist ein Mittelwind je Schicht, kein
    Feld - ihn fuer alle 68 Zellen zu holen waere das 68-fache an Chunks.
    """
    import numpy as np
    if member is None:
        member = range(len(quelle.sample))
    member = list(member)

    bloecke = sorted({b for b in (quelle.block(z) for z in ziele)
                      if b is not None})
    fehlend = [z for z in ziele if quelle.block(z) is None]
    if fehlend:
        melde("   Ausserhalb des Vorlaufs: %s"
              % ", ".join(t.isoformat() for t in fehlend))

    zellen = sorted(zellen)
    # Gitterindizes einmal, nicht je Chunk.
    idx01 = {z: (_index(quelle.lat01, mitte(z)[0]),
                 _index(quelle.lon01, _laenge(mitte(z)[1]))) for z in zellen}

    zeit = []
    for b in bloecke:
        zeit += quelle.zeiten(b)
    aus = {z: {"time": [t.strftime("%Y-%m-%dT%H:%M") for t in zeit]}
           for z in zellen}

    n = 0
    for schicht in schichten:
        for m in member:
            reihe = {z: [] for z in zellen}
            for b in bloecke:
                feld = quelle.wolke(schicht, m, b)
                n += 1
                for z in zellen:
                    i, j = idx01[z]
                    reihe[z] += [prozent(x) for x in feld[:, i, j]]
            name = feldname("cloud_cover_%s" % schicht, m)
            for z in zellen:
                aus[z][name] = reihe[z]
        melde("   %s: %d Member, %d Zeitbloecke" % (schicht, len(member),
                                                    len(bloecke)))

    if wind_zelle is not None:
        wi = (_index(quelle.lat025, mitte(wind_zelle)[0]),
              _index(quelle.lon025, _laenge(mitte(wind_zelle)[1])))
        for schicht in schichten:
            hpa = WINDNIVEAU[schicht]
            for m in member:
                sp, ri = [], []
                for b in bloecke:
                    u = quelle.wind("u", hpa, m, b)
                    v = quelle.wind("v", hpa, m, b)
                    n += 2
                    # Ein Windchunk traegt EINE Stunde, der Wolkenchunk
                    # sechs.  Damit die Reihen gleich lang bleiben, wird
                    # der Wert ueber den Block wiederholt - der
                    # Advektionsversatz ist ohnehin ein Blockmittel.
                    su, sv = float(u[wi]), float(v[wi])
                    sp += [geschwindigkeit(su, sv)] * len(quelle.sub)
                    ri += [richtung(su, sv)] * len(quelle.sub)
                aus[wind_zelle][feldname("wind_speed_%dhPa" % hpa, m)] = sp
                aus[wind_zelle][feldname("wind_direction_%dhPa" % hpa, m)] = ri
        melde("   Wind an einer Zelle, %d Niveaus" % len(schichten))

    melde("   %d Chunks gelesen" % n)
    return aus


def neuester_lauf(lies=None):
    """Juengster Lauf, der einen `success`-Marker traegt."""
    zeilen = _lauf(["gcloud", "storage", "ls",
                    "--billing-project=" + ABRECHNUNG, BUCKET + "/"])
    laeufe = sorted(t.rstrip("/").rsplit("/", 1)[-1].replace("_01_preds", "")
                    for t in zeilen.splitlines() if t.endswith("_preds/"))
    for lauf in reversed(laeufe):
        try:
            _lauf(["gcloud", "storage", "ls",
                   "--billing-project=" + ABRECHNUNG,
                   "%s/%s_01_preds/success" % (BUCKET, lauf)])
            return lauf
        except RuntimeError:
            continue
    raise SystemExit("kein fertiger Lauf gefunden")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lauf", help="z.B. 20260908_00hr; sonst der juengste")
    p.add_argument("--probe", action="store_true",
                   help="nur ein Chunk, zum Nachsehen")
    p.add_argument("--aus")
    p.add_argument("--budget-mb", type=int, default=BUDGET_MB,
                   help="Obergrenze ausserhalb von %s; bewusst zu setzen, "
                        "denn jenseits davon kostet es Geld" % REGION)
    a = p.parse_args()

    lauf = a.lauf or neuester_lauf()
    frei = in_region()
    print("Lauf: %s" % lauf)
    print("Ort:  %s" % ("in %s - Verkehr ist gratis" % REGION if frei else
                        "ausserhalb %s - Grenze %d MB" % (REGION, a.budget_mb)))
    q = Quelle(lauf, budget=Budget(frei, a.budget_mb))
    print("Init: %s, %d Member, %d Zeitbloecke a %d Stunden"
          % (q.init.isoformat(), len(q.sample), len(q.lead), len(q.sub)))

    if a.probe:
        i = 10
        print("Block %d gueltig fuer: %s" % (i, ", ".join(
            t.strftime("%H:%MZ") for t in q.zeiten(i))))
        z = (round(52.52 / GITTER), round(13.405 / GITTER))
        d = abfrage(q, [z], [q.zeiten(i)[3]], member=[0])
        for k, v in sorted(d[z].items()):
            print("   %-28s %s" % (k, v))
        return

    raise SystemExit("Voller Lauf noch nicht verdrahtet - siehe T-0072.")


if __name__ == "__main__":
    main()
