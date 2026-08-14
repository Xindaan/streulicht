"""Diagnoseseite: Foto neben Vertikalschnitt, sortiert nach Fehlgriff.

Der Punkt, an dem Statistik aufhoert und Hinsehen anfaengt.  Wenn auf dem Foto
eine Wolkenbank steht, wo ERA5 klaren Himmel meldet, ist das eine ganz andere
Diagnose als ein Modellierungsfehler - und man sieht es in zwei Sekunden.

Erwartet den Fotoexport in Album/ mit einem Unterordner je Abend, benannt wie
"Berlin, 10. Juli 2025" oder "7. Juni 2023".

Die Fotos bleiben lokal.  Erzeugt werden nur verkleinerte Vorschauen in
daten/thumbs/ (gitignoriert), und die Seite laeuft im Browser auf dem eigenen
Rechner.  Nichts davon geht ins Repo oder ins Netz.
"""
import json
import os
import re
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schnitt import lade_feld, svg  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALBUM = os.path.join(BASIS, "Album")
THUMBS = os.path.join(BASIS, "daten", "thumbs")
MONATE = {"januar": 1, "februar": 2, "maerz": 3, "märz": 3, "april": 4, "mai": 5,
          "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
          "november": 11, "dezember": 12}
ZIRKULAER = {"2025-06-29", "2023-06-14", "2023-05-29", "2022-11-11"}


def datum_aus_ordner(name):
    m = re.search(r"(\d{1,2})\.\s*([A-Za-zäöüÄÖÜ]+)\s*(\d{4})", name)
    if not m:
        return None
    mon = MONATE.get(m.group(2).lower())
    if not mon:
        return None
    try:
        return date(int(m.group(3)), mon, int(m.group(1))).isoformat()
    except ValueError:
        return None


def vorschau(quelle, ziel, breite=760):
    if os.path.exists(ziel):
        return True
    r = subprocess.run(["sips", "-Z", str(breite), quelle, "--out", ziel],
                       capture_output=True)
    return r.returncode == 0 and os.path.exists(ziel)


def main():
    if not os.path.isdir(ALBUM):
        raise SystemExit("Album/ nicht gefunden")
    with open(os.path.join(BASIS, "daten",
                           "score_berlin_g0.5_2022_2025.json")) as f:
        klima = json.load(f)

    def tag_im_jahr(s):
        return date.fromisoformat(s).timetuple().tm_yday

    nach = {}
    for t, v in klima.items():
        nach.setdefault(tag_im_jahr(t), []).append(v["s"])

    def rang(t):
        j = tag_im_jahr(t)
        v = []
        for dd in range(-21, 22):
            v += nach.get((j + dd - 1) % 365 + 1, [])
        w = klima[t]["s"]
        return (sum(1 for x in v if x < w) + 0.5 * sum(1 for x in v if x == w)) / len(v)

    os.makedirs(THUMBS, exist_ok=True)
    eintraege = []
    for ordner in sorted(os.listdir(ALBUM)):
        pfad = os.path.join(ALBUM, ordner)
        if not os.path.isdir(pfad):
            continue
        tag = datum_aus_ordner(ordner)
        if not tag or tag not in klima or tag in ZIRKULAER:
            continue
        bilder = sorted(x for x in os.listdir(pfad)
                        if x.lower().endswith((".jpg", ".jpeg", ".heic", ".png")))
        if not bilder:
            continue
        ziel = os.path.join(THUMBS, "%s.jpg" % tag)
        if not vorschau(os.path.join(pfad, bilder[0]), ziel):
            continue
        feld = lade_feld(tag)
        if not feld:
            continue
        try:
            bild, s, det = svg(tag, feld)
        except Exception:                                        # noqa: BLE001
            continue
        eintraege.append({"tag": tag, "s": s, "rang": rang(tag),
                          "schirm": det["schirm"], "sicht": det["sicht"],
                          "weg": det["weg"], "A": klima[tag]["A"],
                          "n_bilder": len(bilder), "svg": bild})
    eintraege.sort(key=lambda e: e["rang"])
    print("%d Abende mit Foto und Schnitt" % len(eintraege))
    if not eintraege:
        raise SystemExit("nichts zu zeigen")

    teile = ["""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Diagnose</title><style>
:root{color-scheme:dark}
body{margin:0;background:#0d1117;color:#e6edf2;
 font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{padding:1.2rem 1.5rem}
h1{margin:0;font-size:1.15rem;font-weight:500}
.sub{color:#8b949e;font-size:.85rem;margin-top:.35rem;max-width:46rem;line-height:1.55}
.fall{border-top:1px solid #21262d;padding:1.2rem 1.5rem}
.kopf{display:flex;align-items:baseline;gap:1rem;margin-bottom:.7rem;flex-wrap:wrap}
.d{font-size:1rem;font-weight:500}
.r{font-variant-numeric:tabular-nums}
.gut{color:#3fb950}.schlecht{color:#f85149}.mittel{color:#d29922}
.paar{display:grid;grid-template-columns:1fr 1fr;gap:1rem;align-items:start}
.paar img{width:100%;border-radius:8px;display:block}
.paar svg{width:100%;height:auto;border-radius:8px}
@media (max-width:900px){.paar{grid-template-columns:1fr}}
.meta{color:#8b949e;font-size:.8rem}
</style></head><body>
<header><h1>Diagnose &mdash; Foto gegen Modell</h1>
<div class="sub">Albumabende, schlechtester Perzentilrang zuerst. Links das Foto,
rechts was ERA5 zur Sonnenuntergangsstunde sah. Die Frage bei jedem Fall:
steht auf dem Foto eine Wolkenbank, die das Modell nicht hat? Dann ist es ein
Datenproblem. Sieht das Modell die Wolken richtig und der Score bewertet sie
falsch? Dann ist es ein Modellproblem. Das sind zwei verschiedene
Baustellen.</div></header>"""]
    for e in eintraege:
        kl = "schlecht" if e["rang"] < 0.4 else ("mittel" if e["rang"] < 0.7 else "gut")
        teile.append(
            '<div class="fall"><div class="kopf">'
            '<span class="d">%s</span>'
            '<span class="r %s">Rang %.2f</span>'
            '<span class="meta">S = %.3f &middot; Schirm %s &middot; A %.2f &middot; '
            'Sicht %.2f &middot; Weg %.2f &middot; %d Fotos</span></div>'
            '<div class="paar"><img loading="lazy" src="../daten/thumbs/%s.jpg" alt="">'
            '%s</div></div>'
            % (e["tag"], kl, e["rang"], e["s"], e["schirm"], e["A"] or 0,
               e["sicht"], e["weg"], e["n_bilder"], e["tag"], e["svg"]))
    teile.append("</body></html>")
    ziel = os.path.join(BASIS, "web", "diagnose.html")
    with open(ziel, "w") as f:
        f.write("\n".join(teile))
    print("geschrieben: %s (%.1f MB)" % (ziel, os.path.getsize(ziel) / 1e6))
    print("Vorschauen in %s" % THUMBS)


if __name__ == "__main__":
    main()
