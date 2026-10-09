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

// Dieselbe Liste wie in der Seite (web/bewerten.html).  Sie steht hier
// bewusst noch einmal: der Test soll nicht aus der Seite ableiten, was die
// Seite schreiben darf.
const MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
                "August", "September", "Oktober", "November", "Dezember"];

let fehler = [];
function pruefe(bed, text) {
  console.log("   " + (bed ? "ok  " : "FEHL") + "  " + text);
  if (!bed) fehler.push(text);
}

// --- Minimalumgebung: nur so viel DOM, wie die Seite anfasst ---------------
function knopfAttrappe(text) {
  return {textContent: text, innerHTML: "", className: "", href: "",
          disabled: false, title: "", style: {},
          classList: {_s: new Set(), add(c) { this._s.add(c); },
                      remove(c) { this._s.delete(c); },
                      toggle(c, an) { an ? this._s.add(c) : this._s.delete(c); },
                      contains(c) { return this._s.has(c); }},
          onclick: null, click() { this.onclick && this.onclick(); }};
}

function umgebung({speicherGeht = true, fetchOk = true} = {}) {
  const knoepfe = [];
  const speicher = {};
  const el = {
    datum: knopfAttrappe(""), status: knopfAttrappe(""),
    nachsenden: knopfAttrappe(""), nichtgesehen: knopfAttrappe("Nicht gesehen"),
    knoepfe: {
      appendChild(b) { knoepfe.push(b); },
      querySelectorAll() { return knoepfe; }
    }
  };
  // Die fuenf Ziffern stehen seit 16.08.2026 im Markup.  Der Pruefstand
  // legt sie deshalb vorher an, statt auf createElement zu warten.
  for (let n = 1; n <= 5; n++) {
    const b = knopfAttrappe(String(n));
    b.value = String(n);
    knoepfe.push(b);
  }
  // Die Quittung (Schirm 3 des Entwurfs): dieselben Attrappen, damit
  // freilegen() nicht an einem fehlenden Knoten scheitert - und damit der
  // Test SIEHT, was dort steht.
  for (const id of ["erfassen", "quittung", "qkopf", "qdanke", "qwann",
                    "qband", "qstufe", "qzahlen", "qtext", "qcta",
                    "qstatus", "nachsenden2"]) {
    el[id] = knopfAttrappe("");
  }
  const ctx = {
    console,
    document: {
      getElementById: (id) => el[id],
      createElement: () => knopfAttrappe("")
    },
    location: {search: "?a=1"},
    URLSearchParams: URLSearchParams,
    decodeURIComponent: decodeURIComponent,
    encodeURIComponent: encodeURIComponent,
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
      // Die Maschinendaten reisen im KLICKZIEL, nicht im Nachrichtenkoerper -
      // der ist Anzeige (iOS zeigt ihn ganz). Derselbe Vertrag wie in
      // bewertungen_holen.py: ?d=<urlencodiertes JSON>.
      const q = (aussen.click || "").split("?d=")[1];
      if (!q) throw new Error("kein Klickziel mit Nutzlast");
      const innen = JSON.parse(decodeURIComponent(q));
      if (/[{}]/.test(aussen.message || ""))
        throw new Error("JSON im sichtbaren Nachrichtentext: " + aussen.message);
      ctx._gesendet.push(Object.assign({_topic: aussen.topic,
                                        _titel: aussen.title,
                                        _text: aussen.message,
                                        _prio: aussen.priority,
                                        _klick: aussen.click}, innen));
      return {ok: true, status: 200};
    }
  };
  ctx.window = ctx;
  return {ctx, el, knoepfe, speicher};
}

const html = fs.readFileSync(SEITE, "utf8");
const jsRoh = html.split("<script>")[1].split("</script>")[0];

// Die erzeugte Seite traegt eine Sonnentafel von +-4 Tagen um ihren Bauzeitpunkt.
// Seit T-0077 verweigert die Seite ausserhalb davon die Antwort - ein Test
// gegen die Datei auf der Platte wuerde also nach fuenf Tagen von selbst
// rot, ohne dass sich am Code etwas geaendert haette.  Deshalb laufen alle
// Pruefungen gegen eine Tafel, die um JETZT gelegt wird; nur 6b liest die
// echte, eingebettete Tafel.
const SONNENTAFEL = /const SONNE\s*=\s*\{[^\n]*\};/;
function tafelUm(zeit, tage) {
  // Ein Sonnenuntergang je Tag um 16:00 UTC; Genauigkeit ist hier egal,
  // es zaehlt nur die Reihenfolge.
  const t = {};
  for (let k = -tage; k <= tage; k++) {
    const d = new Date(Date.UTC(zeit.getUTCFullYear(), zeit.getUTCMonth(),
                                zeit.getUTCDate() + k, 16, 0, 0));
    t[d.toISOString().slice(0, 10)] = d.toISOString().slice(0, 19) + "Z";
  }
  return t;
}
function mitTafel(tafel) {
  return jsRoh.replace(SONNENTAFEL, "const SONNE = " + JSON.stringify(tafel) + ";");
}
const js = mitTafel(tafelUm(new Date(), 4));

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
         "sichtbarer Text ohne JSON-Zeichen: \"" + g._text + "\"");
  pruefe((g._text || "").split("\n").length === 1,
         "sichtbarer Text ist EINE Zeile (iOS zeigt den ganzen Koerper)");
  pruefe(/\?d=/.test(g._klick || ""),
         "Maschinendaten stecken im Klickziel");
  pruefe(/bewerten-berlin\.html/.test(g._klick || ""),
         "Klickziel oeffnet die Bewertungsseite");
  // KEIN fester Monatsname (T-0068, 02.09.2026).  Hier stand /August/ -
  // geprueft wird aber die Seite MIT dem heutigen Datum, also war der Test
  // ab dem 1. September rot, ohne dass sich etwas geaendert haette.  Ein
  // Test, der einmal im Monat von selbst umkippt, wird nicht mehr gelesen.
  // Die Eigenschaft ist "Tag und Monat ausgeschrieben", nicht "August".
  pruefe(new RegExp("\\d{1,2}\\. (" + MONATE.join("|") + ")").test(g._text || ""),
         "erste Zeile nennt das Datum ausgeschrieben: \"" + g._text + "\"");
  pruefe(/auf Nachfrage/.test(g._text || ""),
         "erste Zeile nennt den Anlass in Worten");
  // Prioritaet 1 = min: die Quittung geht an dasselbe Geraet zurueck, von
  // dem sie kommt, solange Andre dieses Topic noch abonniert hat (bis
  // T-0077 lief die Abenderinnerung darueber). Bei min stellt ntfy zu, ohne zu
  // benachrichtigen - der Poller liest weiter, das Telefon schweigt.
  pruefe(g._prio === 1, "Quittung mit min-Prioritaet (ist: " + g._prio + ")");

  console.log("\n=== 1b. Nach der Abgabe wird die Prognose freigelegt");
  pruefe(u.el.erfassen.style.display === "none", "Erfassungsschirm weg");
  pruefe(u.el.quittung.classList.contains("an"), "Quittung sichtbar");
  pruefe(/3 von 5/.test(u.el.qdanke.textContent || ""),
         "Quittung nennt die Note: \"" + u.el.qdanke.textContent + "\"");
  const hatPrognose = /Perzentil|keine Prognose/.test(
    u.el.qzahlen.textContent || "");
  pruefe(hatPrognose, "Prognosezeile gefuellt: \""
         + u.el.qzahlen.textContent + "\"");
  pruefe(!!(u.el.qstufe.textContent || "").trim(), "Stufe gesetzt");

  console.log("\n=== 1c. Vor der Abgabe steht die Prognose NICHT im Dokument");
  {
    const vorher = umgebung({});
    vm.createContext(vorher.ctx);
    vm.runInContext(js, vorher.ctx);
    await new Promise(r => setTimeout(r, 10));
    pruefe(vorher.el.qstufe.textContent === "" &&
           vorher.el.qzahlen.textContent === "" &&
           vorher.el.qband.innerHTML === "",
           "Quittungsfelder leer, solange nichts abgegeben ist");
    // Und im ausgelieferten HTML darf ausserhalb des Skriptblocks keine
    // Stufe stehen - sonst waere die Blindheit nur optisch.
    // NUR das Markup, nicht der Style-Block: dort stehen die Stufenklassen
    // .auffaellig/.unauffaellig als CSS-Selektor, und ein Selektor ist kein
    // sichtbarer Text.  Die erste Fassung dieser Pruefung hat genau darauf
    // angeschlagen und einen Fehler gemeldet, den es nicht gab.
    const koerper = html.split("</style>")[1].split("<script>")[0];
    pruefe(!/unauff|auff\u00e4llig|Perzentil des Jahres|selten/.test(koerper),
           "kein Prognosetext im sichtbaren Dokument");
  }

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
  // Nach der Abgabe traegt die QUITTUNG den Zustand - der Erfassungsschirm
  // ist weg.  Genau hier lag der Fehler, den dieser Test gefunden hat: der
  // Nachsende-Knopf sass auf dem verschwundenen Schirm.
  pruefe(/noch nicht angekommen/i.test(u.el.qkopf.textContent || ""),
         "Quittung sagt die Wahrheit: \"" + u.el.qkopf.textContent + "\"");
  pruefe(u.el.nachsenden2.style.display !== "none",
         "Nachsende-Knopf auch auf der Quittung erreichbar");

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

  console.log("\n=== 3b. Stilles Nachsenden korrigiert auch die Quittung (T-0077, bewertung#6)");
  // Liegt fuer den HEUTIGEN Abend eine ungesendete Note vor, legt die Seite
  // beim Oeffnen die Quittung frei ("Gespeichert, noch nicht angekommen") und
  // sendet danach still nach.  Kommt die Note an, durfte die Quittung bis
  // dahin weiter "noch nicht angekommen" behaupten.
  {
    const probe = umgebung({});
    vm.createContext(probe.ctx);
    vm.runInContext(js, probe.ctx);
    const heuteTag = probe.ctx.abendVonJetzt(new Date());
    pruefe(/^\d{4}-\d{2}-\d{2}$/.test(heuteTag || ""),
           "Voraussetzung: die Seite kennt den heutigen Abend (" + heuteTag + ")");
    const ungesendet = JSON.stringify(
      [{tag: heuteTag, note: 4, anlass: "aufgefordert",
        erfasst: new Date().toISOString(), gesendet: false}]);

    const ok = umgebung({});
    ok.speicher["su-bewertungen-berlin"] = ungesendet;
    vm.createContext(ok.ctx);
    vm.runInContext(js, ok.ctx);
    await new Promise(r => setTimeout(r, 30));
    pruefe(ok.ctx._gesendet.length === 1 && ok.ctx._gesendet[0].tag === heuteTag,
           "die Note des heutigen Abends wurde still nachgesendet");
    pruefe(ok.el.quittung.classList.contains("an"),
           "die Quittung ist sichtbar");
    pruefe(ok.el.qkopf.textContent === "Angekommen",
           "Kopfzeile sagt nach dem Nachsenden \"Angekommen\" (ist: \""
           + ok.el.qkopf.textContent + "\")");
    pruefe(ok.el.qstatus.textContent === "",
           "Statuszeile ist leer (ist: \"" + ok.el.qstatus.textContent + "\")");
    pruefe(ok.el.nachsenden2.style.display === "none",
           "und der Nachsende-Knopf ist weg");

    // Gegenprobe: schlaegt das Nachsenden fehl, darf die Quittung NICHT
    // "Angekommen" sagen - sonst waere der Fix nur eine andere Luege.
    const aus = umgebung({fetchOk: false});
    aus.speicher["su-bewertungen-berlin"] = ungesendet;
    vm.createContext(aus.ctx);
    vm.runInContext(js, aus.ctx);
    await new Promise(r => setTimeout(r, 30));
    pruefe(/noch nicht angekommen/i.test(aus.el.qkopf.textContent || ""),
           "bei weiterem Netzausfall bleibt die Kopfzeile ehrlich (\""
           + aus.el.qkopf.textContent + "\")");
    pruefe(aus.el.qstatus.textContent !== "",
           "und die Statuszeile erklaert, dass die Note lokal liegt");
  }

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

  console.log("\n=== 6. \"Nicht gesehen\" ist Note 0, keine Abwesenheit");
  u = await lauf({});
  u.el.nichtgesehen.click();
  await new Promise(r => setTimeout(r, 20));
  pruefe(u.ctx._gesendet.length === 1, "Note 0 wird gesendet");
  pruefe(u.ctx._gesendet[0] && u.ctx._gesendet[0].note === 0,
         "note === 0 im Rumpf (ist: " +
         JSON.stringify((u.ctx._gesendet[0] || {}).note) + ")");
  pruefe((u.ctx._gesendet[0] || {})._titel === "Bewertet: nicht gesehen",
         "eigener Titel: \"" + (u.ctx._gesendet[0] || {})._titel + "\"");
  pruefe(u.el.nichtgesehen.classList.contains("gewaehlt"),
         "Pille traegt den Auswahlzustand");
  pruefe(/nicht gesehen/.test(u.el.qdanke.textContent || ""),
         "Quittung sagt \"nicht gesehen\": \"" + u.el.qdanke.textContent + "\"");

  console.log("\n=== 6b. Welcher Abend gemeint ist, entscheidet die Sonne");
  {
    const u2 = umgebung({});
    vm.createContext(u2.ctx);
    vm.runInContext(jsRoh, u2.ctx);
    await new Promise(r => setTimeout(r, 10));
    // `const` im VM-Skript landet NICHT auf dem Kontextobjekt (anders als
    // Funktionsdeklarationen).  Die Tafel wird deshalb aus der Seite
    // gelesen - und das prueft nebenbei, dass sie ueberhaupt drinsteht.
    const roh = (jsRoh.match(/const SONNE\s*=\s*(\{[^\n]*\});/) || [])[1];
    const sonne = roh ? JSON.parse(roh) : {};
    const tage = Object.keys(sonne).sort();
    pruefe(tage.length >= 3,
           "Sonnentafel ist eingebettet (" + tage.length + " Tage)");
    if (tage.length >= 3) {
      const mitte = tage[Math.floor(tage.length / 2)];
      const su = new Date(sonne[mitte]);
      // Der eigentliche Fall vom 18.08.2026: 04:26 Ortszeit am Folgetag.
      const nachts = new Date(su.getTime() + 8 * 3600e3);
      pruefe(u2.ctx.abendVonJetzt(nachts) === mitte,
             "acht Stunden nach Sonnenuntergang gilt noch der Vorabend ("
             + u2.ctx.abendVonJetzt(nachts) + " statt " + mitte + ")");
      // Und kurz VOR dem Sonnenuntergang darf es nicht schon der Tag sein.
      const vorher = new Date(su.getTime() - 3600e3);
      pruefe(u2.ctx.abendVonJetzt(vorher) !== mitte,
             "eine Stunde vor Sonnenuntergang gilt der Tag noch nicht ("
             + u2.ctx.abendVonJetzt(vorher) + ")");
    }
  }

  console.log("\n=== 6c. Rand der Sonnentafel: ausserhalb gibt es keine Antwort (T-0077)");
  {
    // Feste Tafel, 10.-18.01.2026, Sonnenuntergang jeweils 16:00 UTC.
    const fest = {};
    for (let t = 10; t <= 18; t++) fest["2026-01-" + t] = "2026-01-" + t + "T16:00:00Z";
    const ctxF = umgebung({});
    vm.createContext(ctxF.ctx);
    vm.runInContext(mitTafel(fest), ctxF.ctx);
    await new Promise(r => setTimeout(r, 10));
    const abend = (iso) => ctxF.ctx.abendVonJetzt(new Date(iso));
    pruefe(abend("2026-01-14T17:00:00Z") === "2026-01-14",
           "mitten in der Tafel: der letzte vergangene Abend");
    pruefe(abend("2026-01-17T17:00:00Z") === "2026-01-17",
           "vorletzter Tafeltag nach Sonnenuntergang: noch eindeutig");
    pruefe(abend("2026-01-18T17:00:00Z") === null,
           "nach dem Sonnenuntergang des LETZTEN Tafeltags: null, nicht dieser Tag ("
           + abend("2026-01-18T17:00:00Z") + ")");
    pruefe(abend("2026-01-23T10:00:00Z") === null,
           "fuenf Tage hinter dem Tafelende: null, nicht der letzte Tafeltag ("
           + abend("2026-01-23T10:00:00Z") + ")");
    pruefe(abend("2026-01-10T10:00:00Z") === null,
           "vor dem ersten Eintrag: null");
    const leer = umgebung({});
    vm.createContext(leer.ctx);
    vm.runInContext(mitTafel({}), leer.ctx);
    await new Promise(r => setTimeout(r, 10));
    pruefe(leer.ctx.abendVonJetzt(new Date()) === null,
           "ohne Tafel: null - kein stiller 04:00-Rueckfall mehr");
  }

  console.log("\n=== 6d. Veraltete Seite: Hinweis, nichts wird gespeichert oder gesendet (T-0077)");
  {
    const frisch = await lauf({});
    pruefe(!/veraltet/i.test(frisch.el.datum.textContent || "")
           && !/neu laden/i.test(frisch.el.status.textContent || ""),
           "frische Seite zeigt keinen Veraltet-Hinweis");
    pruefe(frisch.knoepfe.every(b => !b.disabled) && !frisch.el.nichtgesehen.disabled,
           "und alle Knoepfe sind benutzbar");

    // Tafel von vor zehn Tagen: jetzt liegt weit hinter ihrem Ende.
    const alt = tafelUm(new Date(Date.now() - 10 * 86400e3), 4);
    const a = umgebung({});
    vm.createContext(a.ctx);
    vm.runInContext(mitTafel(alt), a.ctx);
    await new Promise(r => setTimeout(r, 10));
    pruefe(/veraltet/i.test(a.el.datum.textContent || ""),
           "Kopf nennt den Zustand: \"" + a.el.datum.textContent + "\"");
    pruefe(/Seite veraltet, bitte neu laden/.test(a.el.status.textContent || ""),
           "Hinweis \"Seite veraltet, bitte neu laden\": \""
           + a.el.status.textContent + "\"");
    pruefe(a.knoepfe.every(b => b.disabled) && a.el.nichtgesehen.disabled,
           "alle Notenknoepfe und \"Nicht gesehen\" sind gesperrt");
    // Ein Browser feuert click bei gesperrten Knoepfen gar nicht; die
    // Attrappe feuert immer.  Genau deshalb prueft das den zweiten Riegel
    // in senden() - fuer den Fall, dass die Sperre je verloren geht.
    a.knoepfe[2].click();
    a.el.nichtgesehen.click();
    await new Promise(r => setTimeout(r, 30));
    pruefe(a.ctx._gesendet.length === 0, "nichts gesendet");
    pruefe(JSON.parse(a.speicher["su-bewertungen-berlin"] || "[]").length === 0,
           "und nichts als Note fuer irgendeinen Abend gespeichert");
    pruefe(!a.el.quittung.classList.contains("an")
           && a.el.erfassen.style.display !== "none",
           "keine Quittung - die Seite tut nicht so, als waere bewertet");

    // Schon gespeicherte, unbestaetigte Noten alter Abende tragen ihr EIGENES
    // Datum; sie gehen weiter raus, sonst ginge hier eine Messung verloren.
    const q = umgebung({});
    q.speicher["su-bewertungen-berlin"] = JSON.stringify(
      [{tag: "2026-08-14", note: 4, anlass: "spontan",
        erfasst: "2026-08-14T20:10:00Z", gesendet: false}]);
    vm.createContext(q.ctx);
    vm.runInContext(mitTafel(alt), q.ctx);
    await new Promise(r => setTimeout(r, 30));
    pruefe(q.ctx._gesendet.length === 1 && q.ctx._gesendet[0].tag === "2026-08-14",
           "bereits gespeicherte Note eines alten Abends wird weiter nachgesendet");
  }

  console.log("\n=== 7. Abend ohne Prognose wird benannt, nicht geschaetzt");
  {
    const ohne = umgebung({});
    vm.createContext(ohne.ctx);
    // PROGNOSE leeren, bevor das Skript laeuft: genau der Fall 15.08.2026,
    // an dem es die Seite schon gab und den Alarmlauf noch nicht.
    vm.runInContext(js.replace(/const PROGNOSE = .*;/, "const PROGNOSE = {};"),
                    ohne.ctx);
    await new Promise(r => setTimeout(r, 10));
    ohne.knoepfe[3].click();
    await new Promise(r => setTimeout(r, 20));
    pruefe(/keine Prognose f\u00fcr diesen Abend gerechnet/.test(
             ohne.el.qzahlen.textContent || ""),
           "sagt es im Klartext: \"" + ohne.el.qzahlen.textContent + "\"");
    pruefe(ohne.el.qband.innerHTML === "",
           "und zeigt kein erfundenes Himmelsband");
  }

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
