// Regressionstest fuer die Warteschlange der Bewertungsseite (T-0023).
//
// Warum das ein eigener Test ist: die Warteschlange greift NUR im Fehlerfall.
// Steht das NAS still oder ist das Netz weg, verschwindet eine Bewertung
// sonst ohne Meldung - der stille Ausfall des Livegangs schlechthin. Genau
// solcher Code wird nie von Hand geprueft, weil im Normalbetrieb alles
// funktioniert.
//
// Geprueft wird gegen die ERZEUGTE Seite, nicht gegen die Vorlage: nur so
// faellt auf, wenn der Generator etwas kaputtmacht.
//
// Lauf:  node skripte/test_bewertungsseite.js

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const BASIS = path.dirname(__dirname);
const SEITE = path.join(BASIS, "web", "bewerten-berlin.html");

let fehler = [];
function pruefe(bed, text) {
  console.log("   " + (bed ? "ok  " : "FEHL") + "  " + text);
  if (!bed) fehler.push(text);
}

// --- Minimalumgebung: nur so viel DOM, wie die Seite anfasst ---------------
function knopfAttrappe(text) {
  return {textContent: text, disabled: false, title: "", style: {},
          classList: {_s: new Set(), add(c) { this._s.add(c); },
                      contains(c) { return this._s.has(c); }},
          onclick: null, click() { this.onclick && this.onclick(); }};
}

function umgebung({speicherGeht = true, fetchOk = true} = {}) {
  const knoepfe = [];
  const speicher = {};
  const el = {
    datum: knopfAttrappe(""), status: knopfAttrappe(""),
    nachsenden: knopfAttrappe(""), knoepfe: {
      appendChild(b) { knoepfe.push(b); },
      querySelectorAll() { return knoepfe; }
    }
  };
  const ctx = {
    console,
    document: {
      getElementById: (id) => el[id],
      createElement: () => knopfAttrappe("")
    },
    location: {search: "?a=1"},
    URLSearchParams: URLSearchParams,
    Date: Date,
    JSON: JSON,
    Array: Array,
    Promise: Promise,
    String: String,
    setTimeout: setTimeout,
    // Die Seite bricht die Uebertragung nach 12 s ab (kein Timeout waere
    // ein Haenger ohne Ende). Ohne AbortSignal im Kontext wirft uebertrage
    // sofort, und alle Sendepruefungen schlagen fehl - ein Loch im
    // PRUEFSTAND, das wie ein Codefehler aussieht.
    AbortSignal: AbortSignal,
    getComputedStyle: (n) => ({display: n.style.display || "none"}),
    localStorage: speicherGeht ? {
      getItem: (k) => (k in speicher ? speicher[k] : null),
      setItem: (k, v) => { speicher[k] = v; },
      removeItem: (k) => { delete speicher[k]; }
    } : {
      getItem() { throw new Error("Storage disabled"); },
      setItem() { throw new Error("Storage disabled"); }
    },
    _gesendet: [],
    fetch: async function (url, opt) {
      if (!fetchOk) throw new Error("simulierter Netzausfall");
      // ntfy-JSON-Publizieren: der Rumpf traegt topic/title/tags und das
      // eigentliche Datum als JSON-ZEICHENKETTE in `message`. Der Test
      // packt es aus, damit die Pruefungen die Note direkt sehen.
      const aussen = JSON.parse(opt.body);
      // Die Nachricht hat ZWEI Leser: Zeile 1 Text fuer den Sperrbildschirm,
      // Zeile 2 das JSON. Wie bewertungen_holen.py von hinten nach vorn
      // probieren - damit prueft der Test denselben Vertrag wie der Poller.
      const zeilen = aussen.message.split("\n").filter(z => z.trim());
      let innen = null;
      for (let i = zeilen.length - 1; i >= 0; i--) {
        try { const m = JSON.parse(zeilen[i]); if (m && m.tag) { innen = m; break; } }
        catch (e) { /* keine JSON-Zeile */ }
      }
      if (!innen) throw new Error("keine Maschinenzeile in der Nachricht");
      ctx._gesendet.push(Object.assign({_topic: aussen.topic,
                                        _titel: aussen.title,
                                        _text: zeilen[0]}, innen));
      return {ok: true, status: 200};
    }
  };
  ctx.window = ctx;
  return {ctx, el, knoepfe, speicher};
}

const html = fs.readFileSync(SEITE, "utf8");
const js = html.split("<script>")[1].split("</script>")[0];

async function lauf(opt) {
  const u = umgebung(opt);
  vm.createContext(u.ctx);
  vm.runInContext(js, u.ctx);
  await new Promise(r => setTimeout(r, 10));
  return u;
}

(async () => {
  console.log("=== 1. Normalfall: Bewertung geht raus");
  let u = await lauf({});
  u.knoepfe[2].click();                       // Note 3
  await new Promise(r => setTimeout(r, 20));
  pruefe(u.ctx._gesendet.length === 1, "genau eine Nachricht gesendet");
  pruefe(u.ctx._gesendet[0] && u.ctx._gesendet[0].note === 3,
         "Note 3 uebertragen");
  pruefe(u.ctx._gesendet[0] && u.ctx._gesendet[0].anlass === "aufgefordert",
         "Anlass aus ?a=1 mitgeschickt: " +
         (u.ctx._gesendet[0] || {}).anlass);
  pruefe(u.ctx._gesendet[0] && !!u.ctx._gesendet[0].erfasst,
         "Erfassungszeitpunkt mitgeschickt");
  pruefe(getComputedStyleDisplay(u) === "none",
         "kein Nachsende-Knopf, wenn nichts offen ist");
  const g = u.ctx._gesendet[0] || {};
  pruefe(/^Bewertet: 3 von 5$/.test(g._titel || ""),
         "Titel ist lesbar: \"" + g._titel + "\"");
  pruefe(!/[{}\"]/.test(g._text || "x{"),
         "erste Zeile ohne JSON-Zeichen: \"" + g._text + "\"");
  pruefe(/August/.test(g._text || ""),
         "erste Zeile nennt das Datum ausgeschrieben");
  pruefe(/auf Nachfrage/.test(g._text || ""),
         "erste Zeile nennt den Anlass in Worten");

  console.log("\n=== 2. Netzausfall: nichts geht verloren");
  u = await lauf({fetchOk: false});
  u.knoepfe[4].click();                       // Note 5
  await new Promise(r => setTimeout(r, 20));
  pruefe(u.ctx._gesendet.length === 0, "nichts gesendet (erwartet)");
  const gespeichert = JSON.parse(u.speicher["su-bewertungen-berlin"] || "[]");
  pruefe(gespeichert.length === 1 && gespeichert[0].note === 5,
         "Bewertung liegt lokal: " + JSON.stringify(gespeichert[0] || {}));
  pruefe(gespeichert[0] && gespeichert[0].gesendet === false,
         "als unbestaetigt markiert");
  pruefe(getComputedStyleDisplay(u) !== "none",
         "Nachsende-Knopf sichtbar");
  pruefe(u.el.status.textContent.toLowerCase().indexOf("noch nicht angekommen") >= 0,
         "Status sagt die Wahrheit: \"" + u.el.status.textContent + "\"");

  console.log("\n=== 3. Neustart nach Netzausfall: wird nachgesendet");
  const u2 = umgebung({});
  u2.speicher["su-bewertungen-berlin"] = JSON.stringify(
    [{tag: "2026-08-14", note: 4, anlass: "spontan",
      erfasst: "2026-08-14T20:10:00Z", gesendet: false}]);
  vm.createContext(u2.ctx);
  vm.runInContext(js, u2.ctx);
  await new Promise(r => setTimeout(r, 20));
  pruefe(u2.ctx._gesendet.length === 1,
         "beim Oeffnen still nachgesendet");
  pruefe(u2.ctx._gesendet[0] && u2.ctx._gesendet[0].tag === "2026-08-14",
         "und zwar der ALTE Abend, nicht heute");

  console.log("\n=== 4. Ohne localStorage trotzdem senden");
  u = await lauf({speicherGeht: false});
  u.knoepfe[1].click();                       // Note 2
  await new Promise(r => setTimeout(r, 20));
  pruefe(u.ctx._gesendet.length === 1,
         "gesendet, obwohl kein Speicher da ist");
  pruefe(u.ctx._gesendet[0] && u.ctx._gesendet[0].note === 2,
         "richtige Note");

  console.log("\n=== 5. Zweite Note am selben Tag ersetzt die erste");
  u = await lauf({});
  u.knoepfe[0].click();
  await new Promise(r => setTimeout(r, 20));
  const liste = JSON.parse(u.speicher["su-bewertungen-berlin"] || "[]");
  pruefe(liste.length === 1, "genau ein Eintrag je Tag (%d)".replace("%d", liste.length));

  console.log("");
  if (fehler.length) {
    console.log("FEHLGESCHLAGEN: " + fehler.length);
    process.exit(1);
  }
  console.log("alle Pruefungen bestanden");
})();

function getComputedStyleDisplay(u) {
  return u.el.nachsenden.style.display || "none";
}
