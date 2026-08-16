"""Das Himmelsband: der Lichteindruck eines Abends als Farbstreifen.

WOZU.  Die Seite hat bis zum 16.08.2026 nur GERECHNET ausgesehen - Achse,
Schnitt, Zahlen.  Wer sie abends aufmacht, will aber zuerst SEHEN, ob sich
etwas lohnt, und erst danach nachlesen, warum.  Das Band ist die einzige
Stelle, an der die Seite selbst schoen wird.

Und es ist kein Dekor: die Farbe interpoliert zwischen einem stumpfen und
einem gluehenden Satz, Mischanteil t = median / s*.  Eine gewoehnliche Woche
bleibt sichtbar stumpf, ein seltener Abend glueht.  Genau diese Spannweite
fehlte vorher - ein Dekorband saehe an jedem Abend gleich aus und waere
damit eine Behauptung ueber nichts.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tokens  # noqa: E402

# Die zwei Enden der Rampe, von links (Zenit) nach rechts (Horizont).
# Abgeleitet aus --wolke, --strahl-dunkel, --strahl-hell und --akzent; sie
# stehen hier und nicht in tokens.css, weil es FUENF Stopps je Satz sind und
# ein Token je Stopp die Datei mit zehn Namen fuellen wuerde, die nur diese
# eine Grafik kennt.
DUMPF = ("#1e1e22", "#26262a", "#2e2d2b", "#28282b", "#202024")
GLUT = ("#1c1226", "#5e2a28", "#c8661c", "#ffb340", "#ffe6bd")


def mische(a, b, t):
    t = max(0.0, min(1.0, t))
    ha, hb = a.lstrip("#"), b.lstrip("#")
    return "#%02x%02x%02x" % tuple(
        round(int(ha[i:i + 2], 16)
              + t * (int(hb[i:i + 2], 16) - int(ha[i:i + 2], 16)))
        for i in (0, 2, 4))


def svg(median, s_stern, nr=0, staerke=1.0):
    """Ein Band fuer diesen Abend.

    `median`  Member-Median des Scores (aus dem Zustand, nicht nachgerechnet)
    `s_stern` Schwelle s* aus konfig.json - der Bezug, gegen den gemischt wird
    `nr`      laufende Nummer; nur damit die Verlaufs-IDs eindeutig bleiben,
              wenn mehrere Baender in derselben Seite liegen
    """
    t = max(0.0, min(1.0, (median or 0.0) / s_stern * staerke))
    stopps = "".join(
        '<stop offset="%.2f" stop-color="%s"/>'
        % (i / (len(DUMPF) - 1.0), mische(DUMPF[i], GLUT[i], t))
        for i in range(len(DUMPF)))
    # Der senkrechte Verlauf gibt dem Band Volumen.  Ohne ihn liegt es flach
    # wie ein Fortschrittsbalken - und ein Fortschrittsbalken behauptet eine
    # Skala, die es hier nicht gibt.
    return ('<svg viewBox="0 0 100 20" preserveAspectRatio="none" '
            'xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="Lichteindruck, schematisch">'
            '<defs><linearGradient id="bq%d" x1="0" x2="1" y1="0" y2="0">%s'
            '</linearGradient>'
            '<linearGradient id="bs%d" x1="0" x2="0" y1="0" y2="1">'
            '<stop offset="0" stop-color="#000" stop-opacity=".55"/>'
            '<stop offset=".62" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#000" stop-opacity=".35"/>'
            '</linearGradient></defs>'
            '<rect width="100" height="20" fill="url(#bq%d)"/>'
            '<rect width="100" height="20" fill="url(#bs%d)"/></svg>'
            % (nr, stopps, nr, nr, nr))


def _selbsttest():
    """Zwei Enden pruefen: t=0 muss stumpf sein, t>=1 die volle Glut."""
    assert mische("#000000", "#ffffff", 0.5) == "#808080"
    assert GLUT[3] in svg(1.0, 1.0), "voller Median erreicht die Glut nicht"
    assert DUMPF[3] in svg(0.0, 1.0), "Median 0 ist nicht stumpf"
    assert tokens.werte()["--band-glut"], "tokens.css ohne --band-glut"
    print("band.py: Selbsttest ok")


if __name__ == "__main__":
    _selbsttest()
