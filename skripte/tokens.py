"""Zugriff auf stil/tokens.css -- die einzige Quelle fuer Farbe und Mass.

Zwei Zugaenge, und der Unterschied ist wichtig:

  quelltext()  liefert die Datei als Text.  seite.py inlined sie in den
               Style-Block der erzeugten Seite; damit bleibt die Seite
               self-contained, ohne Stylesheet-Verweis und ohne Netzzugriff.
               Das ist das Muster aus poisson-dor/assets/tokens.css.

  werte()      liefert {name: wert} fuer die Faelle, in denen Python selbst
               rechnen muss -- der Beleuchtungsstrahl in schnitt.py
               interpoliert seine Farbe je Abschnitt aus der verbleibenden
               Transmission, und dafuer braucht er Zahlen, kein var().

Ueberall sonst gilt: var(--name) schreiben, nicht den Wert einsetzen.  Ein
eingesetzter Wert ist eine Kopie, und Kopien laufen auseinander.
"""
import os
import re

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PFAD = os.path.join(BASIS, "stil", "tokens.css")

_ZWISCHENSPEICHER = {}


def quelltext():
    """Die Token-Datei als Text, zum Inlinen in die erzeugte Seite."""
    if "text" not in _ZWISCHENSPEICHER:
        with open(PFAD, encoding="utf-8") as f:
            _ZWISCHENSPEICHER["text"] = f.read()
    return _ZWISCHENSPEICHER["text"]


def werte():
    """{'--papier': '#000000', ...} -- nur fuer Rechnungen, sonst var()."""
    if "werte" in _ZWISCHENSPEICHER:
        return _ZWISCHENSPEICHER["werte"]
    text = quelltext()
    # Kommentare zuerst raus, sonst verschluckt ein '*/' den naechsten Wert.
    ohne = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    d = {}
    for name, wert in re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", ohne):
        d[name] = " ".join(wert.split())
    if not d:
        raise RuntimeError("keine Tokens in %s gefunden" % PFAD)
    _ZWISCHENSPEICHER["werte"] = d
    return d


def rgb(name):
    """Token als (r, g, b).  Nur Sechsstellen-Hex, alles andere faellt auf."""
    h = werte()[name].strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", h):
        raise ValueError("%s ist kein #rrggbb: %r" % (name, h))
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mischen(name_dunkel, name_hell, anteil):
    """Linear zwischen zwei Tokens, anteil 0 = dunkel, 1 = hell -> 'rgb(...)'.

    Fuer den Beleuchtungsstrahl: die Helligkeit je Abschnitt IST die
    verbleibende Transmission, also muss die Farbe stetig laufen und kann
    nicht aus einer festen Stufenliste kommen.
    """
    a = max(0.0, min(1.0, anteil))
    d, h = rgb(name_dunkel), rgb(name_hell)
    return "rgb(%d,%d,%d)" % tuple(int(round(d[i] + a * (h[i] - d[i])))
                                   for i in range(3))
