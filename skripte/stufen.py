"""Die Stufe eines Abends - EINE Regel fuer Prognoseseite, Bewertungsseite,
Bilanz und Alarm (T-0084, Entscheidung Andre 09.10.2026, Option B).

WAS SICH GEAENDERT HAT.  Bis dahin ordnete jede Seite den MEDIAN der 51
Member in die Verteilung einzelner Analyse-Abende ein und las die Stufe an
den Zonen 0,80 und 0,95 ab - dreimal ausprogrammiert (seite.py,
bewertungsseite.py, bisher.py).  Ein Median streut weniger als ein
Einzelwert, er erreichte die oberen Raender deshalb viel zu selten: nach dem
Advektionsfix "auffaellig" in 9,5 % statt rund 20 % der Faelle, "selten" in
0,5 % (2 von 440 Vorhersagen, daten/archiv/berlin, Auswertung 09.10.2026).
Die einzelnen Member trafen die Klimatologie dagegen gut.

Jetzt zaehlt, WIE VIELE MODELLLAEUFE (Member) es so sehen:

    selten         p >= p*  (Anteil der Member ueber s*, p* aus konfig.json,
                   heute 0,5) - GENAU die Push-Bedingung des Alarms.  alarm.py
                   benutzt dieselbe Funktion `ist_selten`; Stufe und Push
                   koennen deshalb nicht auseinanderlaufen, auch wenn s* oder
                   p* sich aendern (WeatherNext 3, T-0072).
    auffaellig     mindestens Q_AUFFAELLIG der Member liegen im obersten
                   Fuenftel des Jahres (klimatologischer Rang >= 0,80)
    unauffaellig   sonst

Der Rang des Medians ("NN. Perzentil") bleibt als Zahl auf den Seiten, ist
aber nicht mehr die Grundlage der Stufe.

Rueckschau und alte Zeilen: Wo es nur EINEN Score gibt (Rueckschau) oder
die Memberdaten fehlen (Zustandseintraege vor T-0084), gilt weiter die alte
Regel `stufe_alt` - dort ist der Rang eines Einzelwerts gegen die Verteilung
einzelner Abende ja gerade das Passende.

Nur Standardbibliothek: der Alarm benutzt das Modul im Laufzeitpfad.
"""
import bisect
import json
import os

# Ab welchem klimatologischen Rang ein einzelner Member "im obersten
# Fuenftel des Jahres" liegt.  Definition des 80. Perzentils.
RANG_AUFFAELLIG = 0.80

# Anteil der Member im obersten Fuenftel, ab dem ein Abend "auffaellig" heisst.
# HERKUNFT (Auswertung 09.10.2026, docs/entscheidungen-2026-10-09.md Abschnitt 1,
# Nachtrag): von 440 Vorhersagen ab dem Advektionsfix (04.09.2026 14:50 UTC,
# 44 Zielabende, Archivlaeufe aus daten/archiv/berlin) hatten 19,3 % (85) einen
# Memberanteil >= 19/51 = 0,373, bei 18/51 waren es 21,4 %.  Das 80. Perzentil
# verlangt 20 %; 19/51 liegt am naechsten.  Der Wert ist eine SETZUNG aus
# duenner Datenbasis (44 Abende, nur Spaetsommer/Herbst, untereinander
# korreliert) und gehoert nach Winter und Fruehjahr neu gemessen.  Gerundet auf
# 0,37, damit 19 von 51 genau drueber und 18 von 51 genau drunter liegen.
Q_AUFFAELLIG = 0.37

# Die ALTE Regel, nur noch fuer Einzelscores (Rueckschau) und Zeilen ohne
# Memberdaten.
RANG_SELTEN_ALT = 0.95
RANG_AUFFAELLIG_ALT = 0.80

KLIMA_DATEI = "score_berlin_g0.5_2022_2025.json"


def klima_sortiert(basis):
    """Die Scores der Klimatologie, aufsteigend; None, wenn die Datei fehlt."""
    pfad = os.path.join(basis, "daten", KLIMA_DATEI)
    if not os.path.exists(pfad):
        return None
    with open(pfad) as f:
        return sorted(v["s"] for v in json.load(f).values())


def schwelle_p(basis):
    """p* aus konfig.json - der Anteil, ab dem der Alarm pusht."""
    with open(os.path.join(basis, "konfig.json")) as f:
        return json.load(f)["schwelle_wahrscheinlichkeit"]


def rang(alle, s):
    """Klimatologischer Rang von `s`: Anteil der Abende strikt darunter.

    `alle` ist die aufsteigend sortierte Klimatologie.  EINE Stelle fuer die
    drei Seiten; vorher stand die Rechnung dreimal da.
    """
    return bisect.bisect_left(alle, s) / len(alle)


def anteil_auffaellig(scores, alle):
    """Anteil der Member im obersten Fuenftel des Jahres, oder None ohne Member."""
    gueltig = [s for s in scores if s is not None]
    if not gueltig:
        return None
    return sum(1 for s in gueltig
               if rang(alle, s) >= RANG_AUFFAELLIG) / len(gueltig)


def ist_selten(p, schwelle):
    """Push-Bedingung des Alarms UND Stufe "selten" - dieselbe Aussage."""
    return p >= schwelle


def _anzeige(name):
    return {"selten": ("selten", "selten"),
            "auffaellig": ("auffällig", "auffaellig"),
            "unauffaellig": ("unauffällig", "unauffaellig")}[name]


def stufe(p, anteil, schwelle):
    """(Anzeigename, CSS-Klasse) nach Modelllaeufen.  Klasse ASCII."""
    if ist_selten(p, schwelle):
        return _anzeige("selten")
    if anteil >= Q_AUFFAELLIG:
        return _anzeige("auffaellig")
    return _anzeige("unauffaellig")


def stufe_alt(rang_):
    """Die alte Regel: Rang eines Einzelscores gegen die Klimatologie."""
    if rang_ >= RANG_SELTEN_ALT:
        return _anzeige("selten")
    if rang_ >= RANG_AUFFAELLIG_ALT:
        return _anzeige("auffaellig")
    return _anzeige("unauffaellig")


def stufe_eintrag(e, rang_median, schwelle):
    """(Anzeigename, CSS-Klasse, nach_modelllaeufen) fuer einen Zustandsabend.

    `nach_modelllaeufen` ist False, wenn dem Eintrag der Memberanteil fehlt
    (gerechnet vor T-0084): dann gilt die alte Regel am Rang des Medians, und
    die Seite soll das sagen.
    """
    anteil = e.get("anteil_auffaellig")
    if anteil is None or e.get("p") is None:
        name, klasse = stufe_alt(rang_median)
        return name, klasse, False
    name, klasse = stufe(e["p"], anteil, schwelle)
    return name, klasse, True
