"""Die eigentliche Produktseite: was Andre abends anschaut.

Bewusst KEINE Prozentzahl als Hauptaussage.  Nach allem, was gemessen ist,
kann der Score aussergewoehnliche Abende von gewoehnlichen trennen
(Anreicherung n = 43, p = 0.0001), aber ob er unter den guten ordnet, ist
offen.  Eine Zahl wie "71 %" behauptet eine Trennschaerfe, die nicht belegt
ist.  Deshalb drei Stufen, an Perzentilen der Klimatologie festgemacht:

    unauffaellig   unter dem 80. Perzentil
    auffaellig     80. bis 95.
    selten         ab dem 95. (= s*, rund 18 Abende im Jahr)

Der Balken darunter zeigt den Score als Position in der Jahresverteilung -
das ist ehrlicher als eine Prozentzahl, weil es die Bezugsgroesse mitliefert.

Laeuft mit historischen Abenden (Kennzeichnung "Rueckschau") und spaeter
unveraendert mit Prognosedaten.
"""
import argparse
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schnitt import lade_feld, svg  # noqa: E402
sys.path.insert(0, BASIS_ELTERN := os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from sonnen.geometrie import sonnenuntergang  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WOCHENTAG = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


def lokalzeit(tag):
    """Sonnenuntergang in Ortszeit - Sommerzeit nicht raten, sondern rechnen."""
    from datetime import datetime, timezone
    std, _ = sonnenuntergang(date.fromisoformat(tag), 52.52, 13.405)
    dt = datetime.fromisoformat(tag + "T00:00").replace(tzinfo=timezone.utc) \
        + timedelta(hours=std)
    try:
        from zoneinfo import ZoneInfo
        dt = dt.astimezone(ZoneInfo("Europe/Berlin"))
    except Exception:
        pass
    return dt.strftime("%H:%M")


def stufe(rang):
    if rang >= 0.95:
        return "selten", "#f0883e"
    if rang >= 0.80:
        return "auffällig", "#d29922"
    return "unauffällig", "#8b949e"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--von", default="2025-08-25")
    ap.add_argument("--tage", type=int, default=10)
    a = ap.parse_args()
    with open(os.path.join(BASIS, "daten",
                           "score_berlin_g0.5_2022_2025.json")) as f:
        klima = json.load(f)
    alle = sorted(v["s"] for v in klima.values())

    def perzentil(s):
        return sum(1 for x in alle if x < s) / len(alle)

    tage = [(date.fromisoformat(a.von) + timedelta(days=k)).isoformat()
            for k in range(a.tage)]
    tage = [t for t in tage if t in klima]
    eintraege = []
    for t in tage:
        feld = lade_feld(t)
        if not feld:
            continue
        try:
            bild, s, det = svg(t, feld)
        except Exception:                                        # noqa: BLE001
            continue
        p = perzentil(s)
        st, farbe = stufe(p)
        d = date.fromisoformat(t)
        eintraege.append({"tag": t, "wt": WOCHENTAG[d.weekday()],
                          "kurz": d.strftime("%d.%m."), "s": s, "p": p,
                          "stufe": st, "farbe": farbe,
                          "zeit": lokalzeit(t),
                          "schirm": det["schirm"], "svg": bild})
    if not eintraege:
        raise SystemExit("keine Abende")

    beste = max(range(len(eintraege)), key=lambda i: eintraege[i]["p"])
    kacheln = "".join(
        '<button class="k" data-i="%d" style="--f:%s">'
        '<span class="wt">%s</span><span class="dt">%s</span>'
        '<span class="bar"><i style="height:%.0f%%"></i></span>'
        '<span class="st">%s</span></button>'
        % (i, e["farbe"], e["wt"], e["kurz"], 100 * e["p"], e["stufe"])
        for i, e in enumerate(eintraege))
    svgs = json.dumps({str(i): e["svg"] for i, e in enumerate(eintraege)})
    meta = json.dumps([{k: e[k] for k in ("tag", "wt", "kurz", "s", "p",
                                          "stufe", "farbe", "zeit", "schirm")}
                       for e in eintraege])

    html = """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sonnenuntergang Berlin</title><style>
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#0d1117;color:#e6edf2;
 font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{padding:1.4rem 1.5rem .4rem;display:flex;align-items:baseline;gap:.8rem}
h1{margin:0;font-size:1.05rem;font-weight:500;letter-spacing:.02em}
.ort{color:#8b949e;font-size:.85rem}
.hinweis{margin:0 1.5rem;padding:.5rem .8rem;border:1px solid #30363d;
 border-radius:8px;color:#8b949e;font-size:.78rem}
.streifen{display:flex;gap:.5rem;padding:1rem 1.5rem;overflow-x:auto}
.k{flex:0 0 5.2rem;background:#161b22;border:1px solid #30363d;border-radius:10px;
 padding:.6rem .4rem;display:flex;flex-direction:column;align-items:center;gap:.35rem;
 cursor:pointer;color:inherit;font:inherit}
.k:hover{border-color:#484f58}
.k.an{border-color:var(--f);background:#1c2128}
.wt{font-size:.75rem;color:#8b949e}
.dt{font-size:.85rem;font-weight:500}
.bar{width:100%;height:56px;background:#0d1117;border-radius:4px;
 display:flex;align-items:flex-end;overflow:hidden}
.bar i{display:block;width:100%;background:var(--f);opacity:.85}
.st{font-size:.68rem;color:var(--f)}
.haupt{padding:0 1.5rem 2.5rem}
.kopf{display:flex;align-items:baseline;gap:1rem;flex-wrap:wrap;margin:.6rem 0 .9rem}
.gross{font-size:1.5rem;font-weight:500}
.stufe{font-size:1.1rem;font-weight:500}
.klein{color:#8b949e;font-size:.85rem}
svg{width:100%;height:auto;border-radius:10px}
.fuss{color:#484f58;font-size:.72rem;margin-top:.8rem;line-height:1.55;max-width:44rem}
</style></head><body>
<header><h1>SONNENUNTERGANG</h1><span class="ort">Berlin</span></header>
<div class="hinweis">R&uuml;ckschau &mdash; echte Abende aus dem Archiv, keine
Vorhersage. Die Seite rendert sp&auml;ter unver&auml;ndert mit Prognosedaten.</div>
<div class="streifen" id="streifen">__KACHELN__</div>
<div class="haupt"><div class="kopf" id="kopf"></div><div id="bild"></div>
<div class="fuss">Die Stufe kommt aus der Position in der Jahresverteilung:
<b>selten</b> ab dem 95. Perzentil (rund 18 Abende im Jahr), <b>auff&auml;llig</b>
ab dem 80. Bewusst keine Prozentzahl &mdash; belegt ist, dass der Score
au&szlig;ergew&ouml;hnliche Abende von gew&ouml;hnlichen trennt, nicht dass er
unter den guten ordnet.</div></div>
<script>
const SVG=__SVGS__, META=__META__;
const streifen=document.getElementById("streifen");
function waehle(i){
  document.querySelectorAll(".k").forEach(x=>x.classList.remove("an"));
  streifen.children[i].classList.add("an");
  const m=META[i];
  document.getElementById("kopf").innerHTML=
    '<span class="gross">'+m.wt+' '+m.kurz+'</span>'+
    '<span class="stufe" style="color:'+m.farbe+'">'+m.stufe+'</span>'+
    '<span class="klein">Sonnenuntergang '+m.zeit+' Uhr &middot; Schirm '+
    m.schirm+' &middot; Perzentil '+Math.round(m.p*100)+'</span>';
  document.getElementById("bild").innerHTML=SVG[i];
}
document.querySelectorAll(".k").forEach(b=>b.onclick=()=>waehle(+b.dataset.i));
waehle(__BESTE__);
</script></body></html>"""
    html = (html.replace("__KACHELN__", kacheln).replace("__SVGS__", svgs)
            .replace("__META__", meta).replace("__BESTE__", str(beste)))
    ziel = os.path.join(BASIS, "web", "index.html")
    with open(ziel, "w") as f:
        f.write(html)
    print("geschrieben: %s (%d Abende, %.1f MB)"
          % (ziel, len(eintraege), os.path.getsize(ziel) / 1e6))


if __name__ == "__main__":
    main()
