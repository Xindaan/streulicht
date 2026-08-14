"""Erzeugt eine Rueckschau-Seite: was haette der Score an vergangenen Abenden gesagt?

Der direkteste verfuegbare Test von "funktioniert es": Andre schlaegt Abende
nach, an die er sich erinnert, und vergleicht mit dem Score.  Kein Kontingent
noetig - alles kommt aus dem Klimatologie-Blockcache.

Enthalten sind die Abende, an denen fotografiert wurde (die erinnerbaren),
plus die bestbewerteten und ein paar Nullabende als Gegenprobe.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schnitt import lade_feld, svg  # noqa: E402

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WOCHENTAG = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


def main():
    with open(os.path.join(BASIS, "daten",
                           "score_berlin_g0.5_2022_2025.json")) as f:
        klima = json.load(f)
    fotos = set()
    fp = os.path.join(BASIS, "daten", "foto_detail.json")
    if os.path.exists(fp):
        with open(fp) as f:
            for x in json.load(f):
                if 52.2 <= x["lat"] <= 52.8 and 13.0 <= x["lon"] <= 13.9:
                    fotos.add(x["tag"])

    top = [t for t, _ in sorted(klima.items(), key=lambda kv: -kv[1]["s"])[:30]]
    null = [t for t in sorted(klima) if klima[t]["s"] == 0.0][:10]
    tage = sorted(set(t for t in fotos if t in klima) | set(top) | set(null))
    print("%d Abende: %d mit Foto, %d Bestbewertete, %d Nullabende"
          % (len(tage), len(fotos & set(klima)), len(top), len(null)))

    bilder = {}
    for i, tag in enumerate(tage):
        feld = lade_feld(tag)
        if not feld:
            continue
        try:
            bild, s, det = svg(tag, feld)
        except Exception as e:                                  # noqa: BLE001
            print("   %s uebersprungen (%s)" % (tag, e))
            continue
        bilder[tag] = bild
        if (i + 1) % 50 == 0:
            print("   %d/%d gezeichnet" % (i + 1, len(tage)), flush=True)

    from datetime import date as _d
    zeilen = []
    for tag in sorted(bilder, reverse=True):
        v = klima[tag]
        t = _d.fromisoformat(tag)
        zeilen.append(
            '{"t":"%s","w":"%s","s":%.3f,"a":%.2f,"b":%.2f,"k":"%s","f":%d}'
            % (tag, WOCHENTAG[t.weekday()], v["s"], v["A"] or 0, v["B"] or 0,
               v["schirm"] or "", 1 if tag in fotos else 0))

    kopf = """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rueckschau</title><style>
:root{color-scheme:dark}
body{margin:0;background:#0d1117;color:#e6edf2;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{padding:1.2rem 1.5rem .6rem}
h1{margin:0;font-size:1.15rem;font-weight:500}
.sub{color:#8b949e;font-size:.85rem;margin-top:.3rem;max-width:44rem;line-height:1.5}
.wrap{display:flex;gap:1rem;padding:1rem 1.5rem 3rem;align-items:flex-start}
.liste{flex:0 0 15rem;max-height:80vh;overflow-y:auto;border:1px solid #30363d;
  border-radius:8px}
.z{position:relative;display:flex;justify-content:space-between;gap:.5rem;
  padding:.45rem .7rem;cursor:pointer;border-bottom:1px solid #21262d;
  font-size:.85rem;overflow:hidden}
.z .bar{position:absolute;left:0;top:0;bottom:0;background:#f0883e;opacity:.14}
.z:hover{background:#161b22}
.z.aktiv{background:#1f2937}
.z .d{color:#8b949e}
.z .s{font-variant-numeric:tabular-nums;font-weight:500}
.punkt{display:inline-block;width:5px;height:5px;border-radius:50%;
  background:#f0883e;margin-right:.45rem;vertical-align:middle}
.leer{display:inline-block;width:5px;margin-right:.45rem}
.bild{flex:1;min-width:0}
.bild svg{width:100%;height:auto;border-radius:8px}
.filter{display:flex;gap:.4rem;padding:0 1.5rem .6rem}
button{background:#161b22;color:#8b949e;border:1px solid #30363d;border-radius:6px;
  padding:.3rem .7rem;font-size:.8rem;cursor:pointer}
button.an{background:#f0883e;color:#0d1117;border-color:#f0883e}
</style></head><body>
<header><h1>R&uuml;ckschau &mdash; was h&auml;tte der Score gesagt?</h1>
<div class="sub">Abende aus vier Jahren ERA5. Der orange Punkt markiert Abende,
an denen bei Sonnenuntergang fotografiert wurde &mdash; die erinnerbaren.
Wenn der Score taugt, m&uuml;ssten die Abende, die Du als sch&ouml;n in
Erinnerung hast, oben stehen.</div></header>
<div class="filter">
<button class="an" data-f="alle">alle</button>
<button data-f="foto">nur Fotoabende</button>
<button data-f="top">nur Score &ge; 0,63</button>
</div>
<div class="wrap"><div class="liste" id="liste"></div><div class="bild" id="bild"></div></div>
<script>
const DATEN=["""
    fuss = """];
const SVG=__SVG_DATEN__;
const liste=document.getElementById("liste"), bild=document.getElementById("bild");
let filter="alle";
function zeichne(){
  liste.innerHTML="";
  DATEN.filter(d=>filter==="alle"||(filter==="foto"&&d.f)||(filter==="top"&&d.s>=0.6325))
   .forEach(d=>{
    const e=document.createElement("div");
    e.className="z";
    e.innerHTML='<span class="bar" style="width:'+(d.s*100).toFixed(0)+'%"></span>'+
      '<span class="d"><span class="'+(d.f?"punkt":"leer")+'"></span>'+
      d.w+" "+d.t.slice(8)+"."+d.t.slice(5,7)+"."+d.t.slice(2,4)+
      '</span><span class="s">'+d.s.toFixed(2)+"</span>";
    e.onclick=()=>{document.querySelectorAll(".z").forEach(x=>x.classList.remove("aktiv"));
      e.classList.add("aktiv"); bild.innerHTML=SVG[d.t]||"";};
    liste.appendChild(e);
  });
  const sichtbar=DATEN.filter(d=>filter==="alle"||(filter==="foto"&&d.f)||
    (filter==="top"&&d.s>=0.6325));
  if(sichtbar.length){
    const best=sichtbar.reduce((a,b)=>b.s>a.s?b:a);
    const i=sichtbar.indexOf(best);
    const el=liste.children[i];
    if(el){el.click();
      liste.scrollTop = el.offsetTop - liste.clientHeight/2 + el.offsetHeight/2;}
  }
}
document.querySelectorAll("button[data-f]").forEach(b=>b.onclick=()=>{
  document.querySelectorAll("button[data-f]").forEach(x=>x.classList.remove("an"));
  b.classList.add("an"); filter=b.dataset.f; zeichne();});
zeichne();
</script></body></html>"""

    ziel = os.path.join(BASIS, "web", "rueckschau.html")
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    with open(ziel, "w") as f:
        f.write(kopf + ",\n".join(zeilen)
                + fuss.replace("__SVG_DATEN__", json.dumps(bilder)))
    print("geschrieben: %s (%.1f MB)" % (ziel, os.path.getsize(ziel) / 1e6))


if __name__ == "__main__":
    main()
