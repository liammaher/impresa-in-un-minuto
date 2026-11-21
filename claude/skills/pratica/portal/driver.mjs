// Fills a portal pratica from ChatGPT's in-app browser (the Browser plugin's JavaScript tool, a Node REPL), as
// inpage.js does in the Claude pane: the same steps, the same refusals, the same report. Its view of the page reads
// and can't write (tab.playwright.evaluate is a read-only scope), so this module reads there and writes as a person
// does: fill and keys, clicks on the drawn widgets, the file chooser (docs/design/openai-platform.md).
//
//   const d = await import("<skill-dir>/portal/driver.mjs");
//   d.start(tab, "<run folder>")    the run folder run.py chatgpt wrote; returns at once
//   await d.wait(20000)             runs it for up to ms, then the report (no value in it); call it until it isn't running
//   d.start(tab, dir, {resume: true, fixes: [{section, field, set}]})   a stopped run again, on its draft
//
// The values come from <run folder>/private/chatgpt-run.json and stay in this process: nothing this module returns
// holds one, and what the reports leave out goes to <run folder>/private/ (kept.json, held.json, declarations.json,
// anteprima.pdf), as run.py run writes them. <run folder>/report.json is the public report, for review.py.
// It never declares, signs, pays or sends: a button the steps' `forbidden` names is refused, a declarations section
// is never opened to fill. ChatGPT's view hides emails and phone numbers ("<redacted>", to the page's own script
// too): those boxes are typed but can't be read back, and the report lists them as `hidden` for the person.
//
// Each call of the REPL imports this module afresh, so a run lives on globalThis; and neither the REPL nor the
// page may build code from a string, so a page function goes to evaluate as a string expression.

const G = (globalThis.__impresaDriver = globalThis.__impresaDriver || { run: null });
// ChatGPT's browser acts only for the call of the JavaScript tool that is running, and an action belongs to the call
// whose code made it ("Browser Use could not read requirements", then "node_repl exec context not found", 2026-11-21):
// a run started in one call can't act in the next. So the run queues each browser action, and wait() (or run()), in
// the call that is running, performs them: they belong to that call.
G.exec = G.exec || { queue: [], inflight: 0 };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const norm = (s) => (s || "").normalize("NFKD").replace(/[^\x00-\x7f]/g, "").replace(/\s+/g, " ").trim().toLowerCase();
class StepError extends Error {}
const fail = (m) => { throw new StepError(m); };
// What a report says of an error: ours whole; another's (Playwright's carries a call log with the page's HTML, so
// values) its first line only.
const said = (e) => e instanceof StepError ? e.message : `${(e && e.name) || "Error"}: ${String(e && e.message || e).split("\n")[0]}`;

// The steps' label reader asks a node for compareDocumentPosition, which ChatGPT's view of a node lacks: the label
// before a box goes by document order instead (the same answer).
const LABEL_BEFORE = "l.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING && !l.contains(el)";
export function adaptLabelJs(labelJs) {
  const out = labelJs.replace(LABEL_BEFORE, "__before(l, el)");
  if (out === labelJs) fail("label_js: not the reader driver.mjs adapts (run.py's LABEL_JS changed)");
  return out;
}

// --- the page: read only ------------------------------------------------------------------------------------
// Runs in ChatGPT's view of the page. Everything it returns is plain data; a box is named by its full id, any
// other element by its place in a CSS list. Written as a function so it is checked like the rest; sent as text.
function pageApi(cfg) {
  const norm = (s) => (s || "").normalize("NFKD").replace(/[^\x00-\x7f]/g, "").replace(/\s+/g, " ").trim().toLowerCase();
  const startsLabel = (t, label) => {
    const a = norm(t), b = norm(label);
    return a.startsWith(b) && (!["si", "no"].includes(b) || a.length === b.length || !/[a-z0-9]/.test(a[b.length]));
  };
  let order = null;
  const pos = (e) => {
    if (!order) { order = new Map(); [...document.querySelectorAll("*")].forEach((x, i) => order.set(x, i)); }
    return order.has(e) ? order.get(e) : -1;
  };
  const within = (e, a) => { for (let p = e; p; p = p.parentElement) if (p === a) return true; return false; };
  const __before = (l, el) => pos(l) < pos(el) && !within(el, l);
  const labelOf = __LABEL_JS__;
  const texts = (e) => { try { return labelOf(e); } catch (x) { return []; } };
  const vis = (e) => !!e && e.getClientRects().length > 0;
  const shown = (e) => vis(e) || vis(e.closest(".ui-radiobutton, .ui-chkbox, .ui-selectonemenu, .ui-fileupload-choose, .ui-fileupload"));
  const el = (id) => document.querySelector(`[id$="dynaForm:${id}"]`);
  const short = (e) => e.id.split("dynaForm:")[1].replace(/:combo_input$/, "");
  const kindOf = (e) => e.tagName === "SELECT" ? "select" : e.type === "radio" ? "radio" : e.type === "checkbox" ? "checkbox"
    : e.type === "file" ? "file" : /txtws_input$/.test(e.id) ? "lookup" : "text";
  const inputs = () => [...document.querySelectorAll('[id*="dynaForm:"]')].filter((e) => /^(INPUT|SELECT|TEXTAREA)$/.test(e.tagName) &&
    e.type !== "hidden" && !/combo_focus$|combo_filter$|editor_file_dropzone$/.test(e.id) && shown(e));
  const MESSAGE = /^(il valore e obbligatorio|deve essere selezionata)/;
  const OPTIONS = /^selezionare un valore/;
  const labelRank = (e, label) => {
    const t = texts(e);
    if (e.title) t.unshift(e.title);
    while (t.length && MESSAGE.test(norm(t[0]))) t.shift();
    return t.filter((x, i) => !x || t.indexOf(x) === i).slice(0, 3).findIndex((x) => startsLabel(x, label));
  };
  const labelled = (e, label) => labelRank(e, label) >= 0;
  const ownLabel = (e) => [e.title, ...texts(e)].find((t) => norm(t) && !MESSAGE.test(norm(t)) && !(e.tagName === "SELECT" && OPTIONS.test(norm(t))));
  const blockStarts = (list, anchor) => {
    const ranks = list.map((e) => labelRank(e, anchor));
    const best = Math.min(...ranks.filter((r) => r >= 0));
    return ranks.map((r, i) => (r === best || r > 0 && startsLabel(ownLabel(list[i]), anchor) ? i : -1)).filter((i) => i >= 0);
  };
  const nthOf = (css, e) => [...document.querySelectorAll(css)].indexOf(e);
  const slotOf = (box) => {
    const t = texts(box);
    const types = t.map((x) => /Tipologie ammesse:\s*([\w.;]+)/i.exec(x)).find(Boolean);
    const accepts = types ? types[1].split(";").filter(Boolean) : [];
    const title = t.find((x) => x && !/^(il valore|la descrizione|tipologie ammesse|scarica il documento|true$|false$)/.test(norm(x)) &&
      !/rimuovi|\.(pdf|p7m|jpe?g|png|dwf|svg|xml|zip|tiff?)\b/i.test(x)) || "";
    const cell = box.closest("td");
    return { title, accepts, signed_only: accepts.length > 0 && accepts.every((x) => x.endsWith(".p7m")),
      required: t.some((x) => MESSAGE.test(norm(x))), holds: !!cell && /\bRimuovi\b/.test(cell.innerText) };
  };
  const fail = (why) => ({ why });

  function resolve(f) {
    let list = inputs();
    if (f.anchor) {
      const starts = blockStarts(list, f.anchor);
      const b = (f.block || 1) - 1;
      if (b >= starts.length) return fail(`${f.label}: no block ${f.block} of ${f.anchor} (found ${starts.length})`);
      list = list.slice(starts[b], starts[b + 1]);
    }
    const want = f.kind === "number" || f.kind === "date" ? "text" : f.kind;
    let hits = list.filter((e) => kindOf(e) === want && labelled(e, f.label));
    const labelledAll = hits;
    const own = hits.filter((e) => startsLabel(ownLabel(e), f.label));
    if (own.length >= (f.nth || 1)) hits = own;
    else if (hits.length > 1) {
      const best = Math.min(...hits.map((e) => labelRank(e, f.label)));
      hits = hits.filter((e) => labelRank(e, f.label) === best);
    }
    const cell = (e) => (e.closest("td") || {}).innerText || "";
    const inCell = labelledAll.filter((e) => startsLabel(cell(e), f.label));
    const at = f.at !== undefined ? f.at : f.last ? labelledAll.indexOf((inCell.length ? inCell : labelledAll).slice(-1)[0]) : undefined;
    const e = at !== undefined ? labelledAll[at] : hits[(f.nth || 1) - 1];
    if (!e) return fail(`${f.label}: ${hits.length} fields with this label${f.anchor ? ` in block ${f.block || 1}` : ""}`);
    return { id: short(e), ...(at !== undefined ? { at } : {}) };
  }

  return {
    state() {
      const d = document;
      const wait = [...d.querySelectorAll(".ui-dialog, .ui-blockui, .ui-overlay-visible, .ui-outputpanel-loading")]
        .some((e) => vis(e) && /attendere|caricamento|composizione della pratica/i.test(e.innerText || ""));
      const path = location.pathname;
      return { busy: d.readyState !== "complete" || wait, url: location.href,
        signedOut: /login|spid|idp/i.test(path),
        portalError: !d.querySelector(".content-title, li#corrente") && /^(internal server error|service unavailable|bad gateway|gateway time-?out)/i.test(((d.body || {}).innerText || "").trim()),
        composing: /Composizione della pratica/i.test((d.body || {}).innerText || ""),
        title: norm((d.querySelector(".content-title") || {}).innerText) };
    },
    screenHas(text) { return norm(document.body.innerText).includes(norm(text)); },
    button(text) {
      const css = "button, a, input[type=submit]";
      const b = [...document.querySelectorAll(css)].find((e) => vis(e) && norm(e.textContent || e.value) === norm(text));
      return b ? { css, nth: nthOf(css, b), text: [b.textContent, b.value, b.title].join(" "), ...(b.textContent ? { expect: b.textContent } : {}) } : fail(`no ${text} button`);
    },
    stepLink(text) {
      const css = "a";
      const a = [...document.querySelectorAll(css)].filter((x) => vis(x) && norm(x.textContent) === norm(text)).pop();
      return a ? { css, nth: nthOf(css, a), text: a.textContent, expect: a.textContent } : null;
    },
    tree({ leaf, nth }) {
      const css = ".ui-tree .tree-content > span";
      const hits = [...document.querySelectorAll(css)].filter((x) => x.textContent.trim() === leaf);
      if (nth ? hits.length < nth : hits.length !== 1) return fail(`tree: ${hits.length} nodes named ${leaf}`);
      const node = hits[nth ? nth - 1 : 0];
      const li = node.closest("li.ui-treenode");
      const chain = [];
      for (let p = li.parentElement && li.parentElement.closest("li.ui-treenode"); p; p = p.parentElement && p.parentElement.closest("li.ui-treenode")) chain.unshift(p);
      const closed = chain.find((p) => p.querySelector(":scope > .ui-treenode-content").getAttribute("aria-expanded") !== "true");
      if (closed) return { css: ".ui-treenode-label", nth: nthOf(".ui-treenode-label", closed.querySelector(":scope > .ui-treenode-content .ui-treenode-label")) };
      if (li.classList.contains("ui-treenode-selected")) return { selected: true };
      return { css, nth: nthOf(css, node) };
    },
    siNo({ question, answer }) {
      const q = [...document.querySelectorAll('table[id$=":sinCond"]')].filter((t) => norm(t.closest("li, tr, div").innerText).includes(norm(question)));
      if (q.length !== 1) return fail(`${q.length} Si/No questions ${question}`);
      const td = [...q[0].querySelectorAll("td")].find((c) => norm(c.innerText) === norm(answer));
      if (!td) return fail(`${question}: no ${answer}`);
      const box = td.querySelector(".ui-radiobutton-box") || td.querySelector("input");
      const css = ".ui-radiobutton-box, input";
      return { css, nth: nthOf(css, box) };
    },
    isOpen(name) { const cur = document.querySelector("li#corrente"); return !!cur && norm(cur.innerText).startsWith(norm(name)); },
    stillClosed(name) {
      const cur = document.querySelector("li#corrente");
      const link = [...document.querySelectorAll("a.linkmenu")].some((x) => norm(x.textContent).startsWith(norm(name)));
      return !!cur && link && !(norm(cur.innerText).startsWith(norm(name)));
    },
    link(name) {
      const css = "a.linkmenu";
      const a = [...document.querySelectorAll(css)].find((x) => norm(x.textContent).startsWith(norm(name)));
      return a ? { css, nth: nthOf(css, a), text: a.textContent, expect: a.textContent } : null;
    },
    // Pratiche in bozza: the newest draft named so (its Apri), else the paginator's page p.
    draftOpen({ name, p }) {
      const row = [...document.querySelectorAll("tr")].find((t) => norm(t.innerText).includes(norm(name)));
      if (row) {
        const css = "a, button";
        const b = [...row.querySelectorAll(css)].find((x) => norm(x.title || x.textContent) === "apri");
        return b ? { css, nth: nthOf(css, b) } : fail(`${name}: no Apri`);
      }
      const next = [...document.querySelectorAll(".ui-paginator-page")].find((a) => a.textContent.trim() === String(p));
      return next ? { page: { css: ".ui-paginator-page", nth: nthOf(".ui-paginator-page", next) } } : fail(`no draft named ${name} in Pratiche in bozza`);
    },
    hasOpenSection() { return !!document.querySelector("li#corrente"); },
    centre(full) {
      const e = document.getElementById(full);
      if (!e) return null;
      const r = e.getBoundingClientRect();
      return r.width && r.height ? { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2), inView: r.top >= 0 && r.bottom <= ((typeof window !== "undefined" && window.innerHeight) || 0) } : null;
    },
    // A file box's widget as tags, classes and sizes (no value, no file name): what a failed upload reports.
    fileWidget(full) {
      const e = document.getElementById(full);
      if (!e) return null;
      const shape = (x) => `${x.tagName.toLowerCase()}${x.id ? "#…" + x.id.split(":").pop() : ""}${x.className && typeof x.className === "string" ? "." + x.className.trim().split(/\s+/).slice(0, 3).join(".") : ""}` +
        (() => { const r = x.getBoundingClientRect(); return ` ${Math.round(r.width)}x${Math.round(r.height)}`; })();
      const up = [];
      for (let x = e, k = 0; x && k < 5; x = x.parentElement, k++) up.push(shape(x));
      const td = e.closest("td");
      return { box: up, accept: e.getAttribute("accept"), multiple: e.multiple, disabled: e.disabled,
        cell: td ? [...td.querySelectorAll("*")].slice(0, 25).map(shape) : [] };
    },
    menuNames() { return [...document.querySelectorAll("a.linkmenu")].map((a) => a.textContent.replace(/\s+/g, " ").trim()); },
    resolve,
    // An id the crawl saw, held to the box's kind and label: else the box by its label (a move), else the id as it is.
    located(f) {
      const e = el(f.kind === "select" ? f.id + ":combo_input" : f.id);
      const want = f.kind === "number" || f.kind === "date" ? "text" : f.kind;
      const kind = e && kindOf(e) === "lookup" && want === "text" ? "text" : e && kindOf(e);
      if (e && kind === want && labelled(e, f.label)) return { id: f.id };
      const { id, ...byLabel } = f;
      const found = resolve(byLabel);
      if (found.why) return e ? { id: f.id, loose: true } : found;
      return { ...found, ...(e && found.id !== id ? { moved: true } : {}), byLabel: true };
    },
    box(id) {
      const e = el(id);
      if (!e) return null;
      return { full: e.id, kind: kindOf(e), checked: e.checked, disabled: e.disabled, readOnly: e.readOnly, tag: e.tagName };
    },
    tick(id) {
      const e = el(id);
      if (!e) return fail("no box");
      if (e.checked) return { already: true };
      if (e.disabled) return fail("switched off (a choice before it, which the steps file doesn't make, switches it on)");
      const w = e.closest(".ui-radiobutton, .ui-chkbox");
      const box = w && w.querySelector(".ui-radiobutton-box, .ui-chkbox-box");
      const css = ".ui-radiobutton-box, .ui-chkbox-box";
      return box ? { css, nth: nthOf(css, box) } : { full: e.id };
    },
    checked(id) { const e = el(id); return !!e && e.checked; },
    // inpage.js checkLabel: the box (a dropdown's label) carries the label among its texts.
    checkLabel({ id, label, kind }) {
      const e = kind === "select" ? el(id + ":combo_label") || el(id + ":combo_input") : el(id);
      if (!e || !label) return { ok: true };
      const t = texts(e);
      return t.some((x) => norm(x).includes(norm(label))) ? { ok: true } : fail(`expected the label ${label} by this field, found [${t.slice(0, 3).map((x) => `"${x}"`).join(", ")}]`);
    },
    // The document's identity, from what the view has (no `performance` there, 2026-11-21): its address, when it was
    // made, and JSF's view state, which a new page renews. Each read on its own, so a missing one costs nothing.
    origin() {
      const part = (f) => { try { return String(f()); } catch (e) { return ""; } };
      return [part(() => location.href), part(() => document.lastModified),
        part(() => document.querySelector('input[name="javax.faces.ViewState"]').value)].join("|");
    },
    options(id) { const s = el(id + ":combo_input"); return s ? s.options.length : -1; },
    select({ id, value }) {
      const s = el(id + ":combo_input");
      if (!s) return fail("no dropdown");
      const opts = [...s.options];
      let i = opts.findIndex((o) => o.value === value || o.text.trim().toUpperCase() === value.toUpperCase());
      const numbered = /\.$/.test(value) ? opts.filter((o) => o.text.trim().startsWith(value + " ")) : [];
      if (i < 0 && numbered.length === 1) i = opts.indexOf(numbered[0]);
      const coded = opts.filter((o) => o.text.trim().startsWith(value + ":"));
      if (i < 0 && coded.length === 1) i = opts.indexOf(coded[0]);
      if (i < 0) return fail(`none of its ${opts.length} options is the value`);
      const menu = s.closest(".ui-selectonemenu");
      return { i, want: opts[i].value, text: opts[i].text.trim(), already: s.value === opts[i].value, menu: menu && menu.id, input: s.id };
    },
    chosen({ id, want }) { const s = el(id + ":combo_input"); return !!s && s.value === want; },
    value({ id, want }) { const e = el(id); return e ? { got: e.value, same: e.value === want, full: e.id } : { got: null }; },
    panelOpen() {
      return [...document.querySelectorAll(".ui-autocomplete-panel, .ui-selectonemenu-panel")].some(vis) ||
        vis(document.getElementById("ui-datepicker-div"));
    },
    lookupHits({ id, dug, street, words }) {
      const n = (x) => norm(x).toUpperCase();
      const panel = el(id.replace(/_input$/, "_panel"));
      const lis = panel ? [...panel.querySelectorAll("li")] : [];
      const items = lis.map((l) => n(l.textContent));
      const PARTICLES = new Set(["DI", "D", "DA", "DE", "DEL", "DELLO", "DELLA", "DEI", "DEGLI", "DELLE"]);
      const bare = (s) => n(s).split(/[^A-Z0-9]+/).filter((w) => w && !PARTICLES.has(w)).join(" ");
      let hits = items.filter((t) => t.split(" ")[0] === dug && words.every((w) => t.split(" ").includes(w)));
      const exact = hits.filter((t) => t === n(`${dug} ${street}`));
      if (hits.length > 1 && exact.length === 1) hits = exact;
      if (!hits.length) { const loose = items.filter((t) => t.split(" ")[0] === dug && bare(t) === bare(`${dug} ${street}`)); if (loose.length === 1) hits = loose; }
      return { listed: items.length, hits: hits.length, name: hits[0], panel: panel && panel.id, nth: hits.length === 1 ? items.indexOf(hits[0]) : -1 };
    },
    slotRows(title) {
      const heads = [...document.querySelectorAll("span.input-label")].filter((x) => startsLabel(x.textContent, title));
      const head = heads.find((x) => norm(x.textContent) === norm(title)) || heads[0];
      if (!head || !head.closest("tr")) return fail(`${title}: no such slot`);
      const files = [];
      for (let tr = head.closest("tr").nextElementSibling; tr; tr = tr.nextElementSibling) {
        const plus = [...tr.querySelectorAll("button")].find((b) => b.textContent.trim() === "+");
        if (plus) return { files: files.map((b) => ({ id: short(b), cell: (b.closest("td") || {}).innerText || "" })), plus: { css: "button", nth: nthOf("button", plus), expect: "+" } };
        if (tr.querySelector("span.input-label") && !tr.querySelector("input, select, textarea")) break;
        files.push(...tr.querySelectorAll("input[type=file]"));
      }
      return { files: files.map((b) => ({ id: short(b), cell: (b.closest("td") || {}).innerText || "" })), plus: null };
    },
    blocks(anchor) { return blockStarts(inputs(), anchor).length; },
    plusFor({ anchor, nth }) {
      const css = '[id*="dynaForm"] button';
      const plus = [...document.querySelectorAll(css)].filter((b) => shown(b) && b.textContent.trim() === "+");
      if (!plus.length) return fail(`no + to add a block of ${anchor}`);
      const list = inputs();
      const last = list[blockStarts(list, anchor).pop()];
      const after = last ? plus.filter((b) => pos(last) < pos(b)) : [];
      const own = after[(nth || 1) - 1];
      if (nth > 1 && !own) return fail(`no + number ${nth} after ${anchor}'s last block`);
      return { css, nth: nthOf(css, own || plus[plus.length - 1]), expect: "+" };
    },
    // What may open the file chooser for a file box, in order: PrimeFaces' Choose button (a quadro's upload), the
    // attachments screen's drop zone beside it, a label for it, the clickable things in its cell; the box itself last.
    fileBox({ id, css }) {
      const e = css ? document.querySelector(css) : el(id);
      if (!e) return fail(`${css || id}: no file box`);
      if (e.type !== "file") return fail(`${css || id}: not a file box`);
      const ways = [];
      const add = (x, how) => { if (x && vis(x) && !ways.some((w) => w.el === x)) ways.push({ el: x, how }); };
      const w = e.closest(".ui-fileupload");
      add(w && w.querySelector(".ui-fileupload-choose"), "choose");
      add(document.getElementById(e.id.replace(/upload\d*_input$/, "editor_file_dropzone")), "dropzone");
      for (const l of e.labels || []) add(l, "label");
      const cell = e.closest("td");
      if (cell) for (const x of cell.querySelectorAll("button, a, label, .ui-button, [id*=dropzone], [class*=drop], [class*=upload]")) {
        // never one that removes, downloads, or is the person's step (send, pay, sign), never a "+"
        const t = (x.textContent || "").trim();
        if (!/rimuovi|scarica|elimina|invia|paga|firma/i.test(t) && t !== "+") add(x, `cell ${x.tagName.toLowerCase()}`);
      }
      return { full: e.id, ways: ways.slice(0, 6).map(({ el: x, how }) => (x.id ? { full: x.id, how }
        : how === "choose" ? { css: ".ui-fileupload-choose", nth: nthOf(".ui-fileupload-choose", x), how } : null)).filter(Boolean) };
    },
    uploaded(name) {
      const refused = [...document.querySelectorAll(".ui-growl-item")].map((g) => g.textContent.replace(/\s+/g, " ").trim()).filter((t) => /non è stato accettato/i.test(t));
      return { named: norm(document.body.innerText).includes(norm(name)), refused };
    },
    describeBox({ id, css }) {
      const e = (id && el(id)) || (css && document.querySelector(css));
      const td = e && e.closest("td");
      const box = td && [...td.querySelectorAll("input[type=text], textarea")].find((x) => !/dropzone/.test(x.id));
      return box ? { full: box.id } : fail("no description box");
    },
    errors(theirs) {
      const titles = [...document.querySelectorAll("input[type=file]")].map((b) => norm(slotOf(b).title));
      const owns = (title, t) => norm(title).startsWith(norm(t)) && (norm(title) === norm(t) || !titles.includes(norm(t)));
      return [...document.querySelectorAll(".ui-message-error, .ui-messages-error, .ui-growl-message-error, [id*=\"dynaForm\"] .error-message-text")]
        .filter((e) => e.getClientRects().length && norm(e.textContent))
        .filter((e) => {
          const box = e.closest("td") && e.closest("td").querySelector("input, select, textarea");
          if (box && slotOf(box).signed_only) return false;
          if (box && box.type === "file") return !theirs.some((t) => box.id.endsWith("dynaForm:" + t) || owns(slotOf(box).title, t));
          return !(box && theirs.some((t) => box.id.endsWith("dynaForm:" + t) || texts(box).some((x) => norm(x).includes(norm(t)))));
        })
        .map((e) => norm(e.textContent));
    },
    alerts() {
      return [...document.querySelectorAll(".alert-message-text")].filter((e) => e.getClientRects().length && norm(e.textContent)).map((e) => {
        const box = e.closest("td") && e.closest("td").querySelector("input, select, textarea");
        const text = e.textContent.replace(/\s+/g, " ").trim();
        const own = box ? [box.title, ...texts(box)].map(norm).filter((x) => x && x !== norm(text) && !MESSAGE.test(x)) : [];
        return { id: box ? box.id.split("dynaForm:")[1].replace(/:combo_input$/, "") : null, label: own[0] || null, text };
      });
    },
    // Each item: {id, kind, typed, label}. A value ChatGPT's view hides reads as {hidden}.
    readBack(items) {
      const bodyText = norm(document.body.innerText);
      return items.map((f) => {
        if (f.kind === "file") return { got: bodyText.includes(norm(f.typed)) ? f.typed : null };
        if (f.kind === "radio" || f.kind === "checkbox") { const e = el(f.id); return { got: e && e.checked ? "checked" : "unchecked" }; }
        const e = el(f.kind === "select" ? f.id + ":combo_input" : f.id);
        if (!e) return { got: null };
        if (e.value === "<redacted>") return { hidden: true };
        let ok = norm(e.value) === norm(f.typed);
        // ChatGPT's view lacks the global number parser: a number by arithmetic ("12,5" and "12.50" alike).
        const num = (x) => { const t = String(x).trim().replace(",", "."); return /^-?\d+(\.\d+)?$/.test(t) ? +t : null; };
        if (!ok && f.kind === "number") ok = num(e.value) !== null && num(e.value) === num(f.typed);
        return ok ? { ok: true } : { got: e.value, ro: e.readOnly };
      });
    },
    look() {
      const flagged = (e) => [e.title, ...texts(e)].some((t) => MESSAGE.test(norm(t)));
      const boxes = [...document.querySelectorAll("input, select, textarea")]
        .filter((e) => e.type !== "hidden" && (e.type === "file" || shown(e))).slice(0, 150).map((e) => {
          const kind = kindOf(e);
          const slot = kind === "file" || /file_dropzone/.test(e.id) ? slotOf(e) : null;
          const state = kind === "radio" || kind === "checkbox" ? (e.checked ? "checked" : "unchecked")
            : kind === "file" ? (slot.holds ? "filled" : "empty") : e.value ? "filled" : "empty";
          const lab = norm(texts(e).find((t) => norm(t) && !MESSAGE.test(norm(t))) || "");
          return { id: e.id.replace(/^.*dynaForm:/, ""), label: slot ? norm(slot.title) : lab, kind, state,
            ...(kind === "select" ? { options: e.options.length } : {}),
            ...(e.readOnly && kind === "text" && !/calendar_input/.test(e.id) ? { readonly: true } : {}),
            ...(!slot && flagged(e) ? { required: true } : {}),
            ...(slot && slot.accepts.length ? { accepts: slot.accepts.join(";"), required: slot.required } : {}) };
        });
      const open = document.querySelector("li#corrente");
      const messages = [...document.querySelectorAll(".ui-message-error, .ui-messages-error, .ui-growl-message-error, [id*=\"dynaForm\"] .error-message-text")]
        .filter((e) => e.getClientRects().length && norm(e.textContent)).map((e) => norm(e.textContent)).slice(0, 10);
      return { section: open ? norm(open.textContent) : null, boxes, messages };
    },
    declarations(name) {
      const cur = document.querySelector("li#corrente");
      if (!cur) return fail(`${name}: no open section to read`);
      const label = (e) => {
        if (e.labels && e.labels[0] && e.labels[0].innerText.trim()) return e.labels[0].innerText;
        const own = e.type === "radio" && e.closest("div[title]") && e.closest("div[title]").querySelector("label");
        if (own && own.innerText.trim()) return own.innerText;
        return texts(e)[0] || "";
      };
      const buttons = new Set([...cur.querySelectorAll("button, input[type=submit]")].map((b) => (b.innerText || b.value || "").trim()).filter(Boolean));
      const text = cur.innerText.split("\n").filter((l) => !buttons.has(l.trim())).join("\n");
      return { section: name, text: text.replace(/\n{3,}/g, "\n\n").trim().slice(0, 20000),
        boxes: [...cur.querySelectorAll("input[type=checkbox], input[type=radio]")].filter((e) => !/_clone$/.test(e.id))
          .map((e) => ({ label: label(e).replace(/\s+/g, " ").trim().slice(0, 300), kind: e.type, ticked: e.checked })) };
    },
  };
}

// --- a run --------------------------------------------------------------------------------------------------

const PENDING = new Set(["click", "dblclick", "fill", "press", "pressSequentially", "type", "selectOption", "check", "uncheck",
  "setChecked", "waitFor", "evaluate", "goto", "reload", "waitForEvent", "setFiles", "count", "isVisible", "textContent",
  "innerText", "getAttribute"]);
const NO_CALL = /could not read requirements|browser actions are blocked|access host is unavailable|exec context not found/i;
const enqueue = (fn, gen) => new Promise((res, rej) => G.exec.queue.push({ fn, res, rej, gen }));
// The tab, its playwright, locators and file choosers: each action queued for the running call (and queued again on a
// gap between calls); the rest (locator, nth, first) as they are.
function gated(obj, gen) {
  return new Proxy(obj, {
    get(t, p) {
      const v = t[p];
      if (typeof v !== "function") return v && typeof v === "object" && (p === "playwright" || p === "cua") ? gated(v, gen) : v;
      if (PENDING.has(p)) {
        return async (...a) => {
          for (let k = 0; ; k++) {
            try {
              const r = await enqueue(() => v.apply(t, a), gen);
              return r && typeof r === "object" && typeof r.setFiles === "function" ? gated(r, gen) : r;
            } catch (e) {
              if (k < 8 && NO_CALL.test(e.message || "")) { await sleep(500); continue; }
              throw e;
            }
          }
        };
      }
      return (...a) => { const r = v.apply(t, a); return r && typeof r === "object" ? gated(r, gen) : r; };
    },
  });
}
// Performs the queued actions from the running call until stop(); then lets those under way finish (none new).
async function serve(stop, drainMs = 25000) {
  while (!stop()) {
    while (G.exec.queue.length) {
      const j = G.exec.queue.shift();
      // An earlier run's action (one under way when a new run began): never performed for it.
      if (j.gen !== G.exec.gen) { j.rej(new StepError("superseded by a newer run")); continue; }
      G.exec.inflight++;
      let p;
      try { p = Promise.resolve(j.fn()); } catch (e) { p = Promise.reject(e); }
      p.then(j.res, j.rej).finally(() => { G.exec.inflight--; });
    }
    await sleep(15);
  }
  for (const end = Date.now() + drainMs; G.exec.inflight > 0 && Date.now() < end;) await sleep(15);
}

export function start(tab, runDir, opts = {}) {
  if (G.run && !G.run.settled) return "a run is already going: wait for it";
  if (!tab || !tab.playwright) return "no tab: open the portal in a tab first";
  G.exec.gen = (G.exec.gen || 0) + 1;
  for (const j of G.exec.queue) j.rej(new StepError("superseded by a newer run"));
  G.exec.queue = [];
  const run = (G.run = { gen: G.exec.gen, settled: false, report: { result: "running", sections: [], at: null, browser: "chatgpt" },
    scrub: (s) => String(s), promise: null });
  run.promise = attempt(gated(tab, run.gen), runDir, opts, run).catch((e) => {
    run.report.result = "stopped";
    run.report.error = run.scrub(said(e));
  }).finally(() => { run.settled = true; });
  return "started";
}

// Performs the run's browser actions for ms (the run moves only meanwhile), then lets the action under way finish:
// keep ms well under the call's timeout (the JavaScript tool's default is 30 s).
export async function wait(ms = 20000) {
  const run = G.run;
  if (!run) return { result: "none" };
  const end = Date.now() + ms;
  await serve(() => run.settled || Date.now() > end);
  // "running" until the run has written its files: a stop is said only once there is a report.json to read.
  const out = publicReport(run);
  return run.settled ? out : { ...out, result: "running" };
}

// The whole run in one call (give the call a long timeout_ms).
export async function run(tab, runDir, opts = {}) {
  const said = start(tab, runDir, opts);
  if (said !== "started") return { result: "refused", error: said };
  const r = G.run;
  await serve(() => r.settled);
  return publicReport(r);
}

function publicReport(run) {
  const out = { ...run.report };
  delete out.kept;
  if (out.error) out.error = run.scrub(out.error);
  out.sections = (out.sections || []).map((s) => ({ ...s, errors: (s.errors || []).map(run.scrub) }));
  if (out.retries) out.retries = out.retries.map((r) => ({ ...r, error: run.scrub(r.error) }));
  if (out.snapshot) {
    const cut = (t) => (t == null ? t : run.scrub(t).slice(0, 80));
    out.snapshot = { ...out.snapshot, section: cut(out.snapshot.section), boxes: (out.snapshot.boxes || []).map((b) => ({ ...b, label: cut(b.label) })),
      messages: (out.snapshot.messages || []).map(cut) };
  }
  return JSON.parse(JSON.stringify(out));
}

const TRANSIENT = /didn't open|stayed busy|\b0 fields with this label|expected the screen|no section |error page|has expired/;

async function attempt(tab, runDir, opts, run) {
  const fs = await import("node:fs");
  const path = await import("node:path");
  const priv = path.join(runDir, "private");
  const { procedure, steps, values } = JSON.parse(fs.readFileSync(path.join(priv, "chatgpt-run.json"), "utf8"));
  steps.forbidden = new RegExp(steps.forbidden, "i");
  steps.declarations = new RegExp(steps.declarations, "i");
  // resume: true picks the last stopped run up on its draft, from the section it stopped in, with what each section
  // before it kept: from this folder's report.json and private/kept.json, so nothing typed passes through the chat.
  // fixes: [{section, field, set}], what the page really has for a field (a moved id, a renamed label).
  let resume0 = typeof opts.resume === "object" ? { ...opts.resume } : {};
  if (opts.resume === true) {
    // The last stop a run can go on from (private/resume.json): a later run that failed before it began (not logged
    // in) doesn't erase it.
    const point = path.join(priv, "resume.json");
    const last = fs.existsSync(point) ? JSON.parse(fs.readFileSync(point, "utf8")) : JSON.parse(fs.readFileSync(path.join(runDir, "report.json"), "utf8"));
    if (!last.at || !last.url) fail("no stopped run in this folder to resume");
    const keptFile = path.join(priv, "kept.json");
    resume0 = { url: last.url, from: { [last.at.phase === "section" ? "section" : "wizard"]: last.at.index },
      kept: fs.existsSync(keptFile) ? JSON.parse(fs.readFileSync(keptFile, "utf8")) : [], carry: last.carry || {} };
  }
  if (opts.fixes) resume0.fixes = opts.fixes;
  if (opts.only) resume0.only = opts.only;
  for (const x of resume0.fixes || []) Object.assign(steps.sections[x.section].fields[x.field], x.set);
  if (resume0.reopen) fail("the second run (after the declarations) isn't in the ChatGPT driver yet: attach those files on the portal");
  // The values, as whole words, to scrub from anything a report says.
  const out = new Set();
  const add = (v) => { if (typeof v === "string") { if (norm(v).length >= 4) out.add(v.trim()); } else if (Array.isArray(v)) v.forEach(add); else if (v && typeof v === "object") add(v.name); };
  add([values.wizard, values.sections]);
  const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const secrets = [...out].flatMap((s) => [s, norm(s)]).filter(Boolean).sort((a, b) => b.length - a.length)
    .map((t) => new RegExp("(?<![\\p{L}\\p{N}])" + esc(t).replace(/\s+/g, "\\s+") + "(?![\\p{L}\\p{N}])", "giu"));
  run.scrub = (s) => secrets.reduce((t, rx) => t.replace(rx, "‹value›"), String(s));
  run.report.procedure = procedure;
  if (resume0.url) run.report.resumed = true;
  // What the earlier stretches of this pratica found (a resume): the closing lines are the whole pratica's.
  for (const [k, v] of Object.entries(resume0.carry || {})) if (v !== undefined && v !== null) run.report[k] = v;
  const t0 = Date.now();
  const held = { details: [], declarations: [] };
  let resume = { ...resume0 };
  try {
   try {
    for (let n = 0; ; n++) {
      await fill(tab, steps, values, resume, run, held, { fs, path, priv });
      const r = run.report, at = r.at;
      // A stop on the portal's error page is an expired address whatever failed first (inpage.js: onError).
      const onError = /\/cmd\/error/.test(r.url || "");
      if (r.result !== "stopped" || !at || n >= (opts.retries ?? 2) || /^signed out/.test(r.error || "") || !(onError || TRANSIENT.test(r.error || ""))) break;
      if (at.phase !== "section" || !r.url) break;
      run.report = { ...r, result: "running", error: undefined, snapshot: undefined, resumed: true,
        retries: (r.retries || []).concat([{ error: r.error, at }]) };
      await sleep(opts.retry_wait_ms ?? 10000);
      resume = { ...resume, url: r.url, from: { section: at.index }, kept: r.kept || [], reopen_draft: /\/cmd\/error/.test(r.url) };
    }
   } catch (e) {
    run.report.result = "stopped";
    run.report.error = said(e);
   }
  } finally {
    run.report.total_seconds = +((Date.now() - t0) / 1000).toFixed(1);
    const write = (name, data) => { fs.mkdirSync(priv, { recursive: true, mode: 0o700 }); fs.writeFileSync(path.join(priv, name), data, { mode: 0o600 }); };
    const r = run.report;
    if (r.result === "running") { r.result = "stopped"; r.error = r.error || "the run ended without a result"; }
    // A run a newer one replaced writes nothing; a run that never began (not logged in, no draft) only its report.
    const mine = G.run === run, began = !!r.at || (r.sections || []).length > 0 || r.result === "filled";
    if (mine && !began) fs.writeFileSync(path.join(runDir, "report.json"), JSON.stringify(publicReport(run), null, 2));
    if (mine && began) {
    if (r.result === "stopped" && r.at && r.url) {
      const carry = {};
      for (const k of ["hidden", "alerts", "attach_yours", "sections", "declarations_read", "declarations_note", "wizard_seconds", "verify_seconds", "moved", "loose", "skipped_sections"])
        if (r[k] !== undefined) carry[k] = r[k];
      write("resume.json", JSON.stringify({ at: r.at, url: r.url, carry }));
    }
    if (r.result === "filled") fs.rmSync(path.join(priv, "resume.json"), { force: true });
    if ((r.kept || []).length || !fs.existsSync(path.join(priv, "kept.json"))) write("kept.json", JSON.stringify(r.kept || [], null, 2));
    write("held.json", JSON.stringify(held.details, null, 2));
    if (held.declarations.length || !fs.existsSync(path.join(priv, "declarations.json"))) write("declarations.json", JSON.stringify(held.declarations, null, 2));
    if (held.preview) write("anteprima.pdf", held.preview);
    if ((held.yours || []).length || !fs.existsSync(path.join(priv, "attach_yours.json"))) write("attach_yours.json", JSON.stringify(held.yours || [], null, 2));
    fs.writeFileSync(path.join(runDir, "report.json"), JSON.stringify(publicReport(run), null, 2));
    }
  }
}

async function fill(tab, steps, values, resume, run, held, { fs, path, priv }) {
  const report = run.report;
  report.result = "running";
  report.sections = report.sections || [];
  const pw = tab.playwright;
  const labelJs = adaptLabelJs(steps.label_js);
  held.yours = held.yours || [];
  if (resume.url && !held.yours.length) {
    try { held.yours = JSON.parse(fs.readFileSync(path.join(priv, "attach_yours.json"), "utf8")); } catch (e) { /* none yet */ }
  }
  const page = async (method, arg) => {
    const src = `(${pageApi.toString().replace("__LABEL_JS__", () => `(${labelJs})`)})({}).${method}(${arg === undefined ? "" : JSON.stringify(arg)})`;
    for (let i = 0; ; i++) {
      try { return await pw.evaluate(src); }
      catch (e) {
        // a page between two loads has no document to read: try again for a while
        if (i < 60 && /context|navigat|destroyed|detached|target|document/i.test(e.message)) { await sleep(250); continue; }
        throw e;
      }
    }
  };
  const need = (r, what) => { if (r && r.why) fail(what ? `${what}: ${r.why}` : r.why); return r; };
  const click = async (where, what, opts = {}) => {
    if (where.text !== undefined && steps.forbidden.test(where.text)) fail(`refused to click ${what}: that step is the person's`);
    const loc = where.full ? pw.locator(`[id="${where.full}"]`) : pw.locator(where.css).nth(where.nth);
    // A place in a list was read one round trip ago, and a redraw this view can't see may have moved it: what is
    // there now is read again, held to the forbidden steps and to the text it had.
    if (!where.full) {
      const now = norm(await loc.textContent({ timeout: 5000 }).catch(() => "") || "");
      if (steps.forbidden.test(now)) fail(`refused to click ${what}: that step is the person's`);
      if (where.expect !== undefined && now !== norm(where.expect)) fail(`${what}: the page changed under it`);
    }
    await loc.click({ timeout: opts.timeout || 20000 });
  };
  const kept = [];
  const keep = (si, done) => {
    const i = kept.findIndex((k) => k.si === si);
    if (i >= 0) kept.splice(i, 1);
    kept.push({ si, done });
    report.kept = (report.kept || []).filter((k) => k.section !== si)
      .concat([{ section: si, fields: done.map((d) => d.spec && d.spec.at !== undefined ? [d.field, d.typed, d.spec.at] : [d.field, d.typed]) }]);
  };
  const QUIET = 20000;
  async function idle(ms = 180000) {
    const start = Date.now();
    for (let quiet = 0; quiet < 3;) {
      const s = await page("state");
      if (s.signedOut && Date.now() - start > 2000) fail("signed out: the portal sent the page to its sign-in; sign in again, then rerun");
      if (s.portalError && Date.now() - start > 2000) fail("no page to read");
      if (Date.now() - start > ms) fail("the portal stayed busy");
      quiet = s.busy ? 0 : quiet + 1;
      await sleep(150);
    }
  }
  async function until(done, why, cap = 300000) {
    const start = Date.now();
    let last = start;
    while (!(await done())) {
      const s = await page("state");
      if (s.busy || s.composing) last = Date.now();
      if (s.signedOut && Date.now() - start > 2000) fail("signed out: the portal sent the page to its sign-in; sign in again, then rerun");
      if (s.portalError && Date.now() - start > 2000) fail("no page to read");
      if (Date.now() - last > QUIET) fail(`${why} (nothing happening for ${QUIET / 1000} s)`);
      if (Date.now() - start > cap) fail(`${why} (still working after ${Math.round(cap / 60000)} minutes)`);
      await sleep(250);
    }
  }
  // After a click that may load a page: let it start, then wait for the page to settle.
  // After a click that may load a page: until a new document is there or the portal shows it is working (a save
  // that reloads reads, a moment after the click, as the old page complete), then until it settles.
  async function act(fn) {
    const before = await page("origin");
    await fn();
    for (const end = Date.now() + 1500; Date.now() < end;) {
      await sleep(150);
      if ((await page("origin")) !== before || (await page("state")).busy) break;
    }
    await idle();
  }
  async function sweep() {
    if (await page("panelOpen")) { await pw.locator("body").press("Escape").catch(() => {}); await idle(); }
  }
  const button = async (text) => click(need(await page("button", text)), text);
  async function openSection(name) {
    const a = await page("link", name);
    if (!a) return false;
    await act(() => click(a, name));
    // As inpage.js: open once nothing loads and the page doesn't mark another section open with this one's link still there.
    await until(async () => !(await page("state")).busy && !(await page("stillClosed", name)), `${name}: the section didn't open`, 120000);
    await idle();
    return true;
  }

  // the fields
  // A field as the page reads it: its spec, without what the run added (typed, field, spec, slotted).
  const spot = ({ typed, field, spec, slotted, ...g }) => g;
  async function located(f) {
    let r;
    for (const end = Date.now() + REDRAW_MS; ;) {
      r = await page("located", spot(f));
      if (!(r.why ? LATE.test(r.why) : r.loose) || Date.now() > end) break;
      await sleep(400);
    }
    if (r.why) fail(r.why);
    if (r.loose) need(await page("checkLabel", { id: f.id, label: f.label, kind: f.kind }));
    const note = (k) => { const x = { label: f.label, id: f.id, ...(k === "moved" ? { to: r.id } : {}) };
      if (!(report[k] = report[k] || []).some((y) => y.label === x.label && y.id === x.id)) report[k].push(x); };
    if (r.loose) { note("loose"); return f; }
    if (r.moved) note("moved");
    if (!r.byLabel) return f;
    const { id, ...byLabel } = f;
    return { ...f, id: r.id, spec: byLabel };
  }
  // A box a choice just before it shows (the INAIL's "sede di" once INAIL is ticked) can come a moment after the
  // page looks idle here: this view can't see the portal's own request queue, as inpage.js does. So a box found by its
  // label is looked for again for a few seconds before the run says it isn't there.
  const LATE = /fields with this label|no block /;
  // How long a redraw this view can't see coming (rows a tick or a "+" adds) is waited for: section h's grew past 8 s
  // as it filled (2026-11-21).
  const REDRAW_MS = 20000;
  async function resolveSoon(f) {
    let r;
    for (const end = Date.now() + REDRAW_MS; ;) {
      r = await page("resolve", f);
      if (!r.why || !LATE.test(r.why) || Date.now() > end) return r;
      await sleep(400);
    }
  }
  async function bySpec(f, soon = true) {
    const r = soon ? await resolveSoon(f) : await page("resolve", f);
    if (r.why) fail(r.why);
    return { ...f, id: r.id, ...(r.at !== undefined ? { at: r.at } : {}), spec: r.at !== undefined ? { ...f, last: false, at: r.at } : f };
  }
  async function text(f, v) {
    const b = await page("box", f.id);
    if (!b) fail(`${f.id}: no field`);
    if (b.disabled) fail(`${f.label || f.id}: switched off (a choice before it, which the steps file doesn't make, switches it on)`);
    if (b.readOnly && !/calendar_input$/.test(f.id)) fail(`${f.label || f.id}: read-only: the portal fills it itself (\`leave\` it in the dictionary)`);
    const box = pw.locator(`[id$="dynaForm:${f.id}"]`).first();
    await sweep();
    await box.fill(String(v), { timeout: 20000 });
    await box.press("Tab");
    if (/calendar_input$/.test(f.id) || f.kind === "date") await box.press("Escape").catch(() => {});
    await idle();
    const r = await page("value", { id: f.id, want: String(v) });
    if (r.got === "<redacted>" || r.same || norm(r.got) === norm(String(v))) return String(v);
    if (f.kind === "number" && parseFloat(r.got) === parseFloat(v)) return String(v);
    // A widget that keeps its own value (a number box, a masked one) takes keys, not a fill.
    await box.fill("");
    await box.pressSequentially(String(v), { delay: 40 });
    await box.press("Tab");
    await idle();
    return String(v);
  }
  async function select(f, v) {
    for (const end = Date.now() + 20000; Date.now() < end;) {
      const n = await page("options", f.id);
      if (n > 1 || n < 0) break;
      await sleep(400);
    }
    const r = need(await page("select", { id: f.id, value: v }), f.label || f.id);
    if (r.already) return r.want;
    if (!r.menu) fail(`${f.id}: no dropdown widget`);
    let ok = false;
    for (let k = 0; k < 3 && !ok; k++) {
      try {
        await sweep();
        await pw.locator(`[id="${r.menu}"]`).click({ timeout: 10000 });
        const item = pw.locator(`[id="${r.menu}_panel"] li`).nth(r.i);
        await item.waitFor({ state: "attached", timeout: 8000 });
        await sleep(500);
        await item.click({ timeout: 10000 });
        await idle();
        ok = await page("chosen", { id: f.id, want: r.want });
      } catch (e) { await pw.locator("body").press("Escape").catch(() => {}); await sleep(300); }
    }
    if (!ok) {
      await pw.locator(`[id="${r.input}"]`).selectOption(r.want, { timeout: 10000 });
      await idle();
      ok = await page("chosen", { id: f.id, want: r.want });
    }
    if (!ok) fail(`${f.id}: the chosen option didn't stay selected`);
    return r.want;
  }
  async function tick(f) {
    const r = need(await page("tick", f.id), f.label || f.id);
    if (!r.already) { await click(r, f.label || f.id); await idle(); }
    // A box that opens rows renumbers itself (INPS adds its "sede di": r27 became r28, 2026-11-21): found again by its
    // label, for a few seconds, since the re-drawn rows come after the page looks idle to this view.
    let id = f.id;
    for (const end = Date.now() + REDRAW_MS; !(id && (await page("checked", id))) && Date.now() < end;) {
      if (f.spec) { const r = await page("resolve", f.spec); if (!r.why) id = r.id; }
      if (!(id && (await page("checked", id)))) await sleep(400);
    }
    if (!id || !(await page("checked", id))) fail(`${f.id}: didn't stay ticked`);
    return "checked";
  }
  async function lookup(f, value) {
    const parts = value.split(/\s+/);
    const [dug, street] = parts.length > 1 ? [parts[0].toUpperCase(), parts.slice(1).join(" ")] : ["", value];
    const words = street.toUpperCase().split(/\W+/).filter((w) => w.length > 2).sort((a, b) => b.length - a.length);
    const box = pw.locator(`[id$="dynaForm:${f.id}"]`).first();
    let hit = { hits: 0, listed: 0 };
    for (const query of words) {
      await box.fill("");
      await box.pressSequentially(query, { delay: 60 });
      await sleep(400);
      await idle();
      hit = await page("lookupHits", { id: f.id, dug, street, words });
      if (hit.hits) break;
    }
    if (hit.hits !== 1) fail(`${f.id}: the value matches ${hit.hits} of ${hit.listed} listed`);
    await pw.locator(`[id="${hit.panel}"] li`).nth(hit.nth).click({ timeout: 20000 });
    await idle();
    await sweep();
    return hit.name;
  }
  async function slotBox(f) {
    let s = need(await page("slotRows", f.label));
    if (f.empty) {
      if (s.files.some((x) => norm(x.cell).includes(norm(f.name)))) return { ...f, already: true };
      const free = s.files.findIndex((x) => !/\bRimuovi\b/.test(x.cell));
      f = { ...f, nth: free >= 0 ? free + 1 : s.plus ? s.files.length + 1 : 1 };
    }
    while (s.files.length < f.nth) {
      if (!s.plus) fail(`${f.label}: no + to add a file`);
      const before = s.files.length;
      await click(s.plus, `+ ${f.label}`);
      await idle();
      s = need(await page("slotRows", f.label));
      for (const end = Date.now() + REDRAW_MS; s.files.length === before && Date.now() < end;) { await sleep(400); s = need(await page("slotRows", f.label)); }
      if (s.files.length !== before + 1) fail(`${f.label}: + didn't add a file box`);
    }
    return { ...f, id: s.files[f.nth - 1].id, slotted: true };
  }
  async function addBlock(f) {
    const before = await page("blocks", f.anchor);
    if (f.block && before >= f.block) return `block ${f.block}`;
    await click(need(await page("plusFor", { anchor: f.anchor, nth: f.nth })), `+ ${f.anchor}`);
    await idle();
    // The new block's rows can come a moment after the page looks idle here (as a box a choice shows: resolveSoon).
    let now = await page("blocks", f.anchor);
    for (const end = Date.now() + REDRAW_MS; now === before && Date.now() < end; now = await page("blocks", f.anchor)) await sleep(400);
    if (now !== before + 1) fail(`+ didn't add a block of ${f.anchor}`);
    return `block ${before + 1}`;
  }
  // A file whose box ChatGPT's browser won't open a chooser for (the attachments screen's, 2026-11-21: every way
  // clicked, no chooser) is the tecnico's to attach: listed for review.py, never a stop. After the first such box on
  // a screen the rest aren't tried (each costs a minute of tries).
  const yours = [];
  let noChooser = null;
  async function attach(f, v) {
    if (noChooser === report.at.section) return handOver(f, v);
    const b = need(await page("fileBox", { id: f.id, css: f.css }));
    let file = v.path;
    if (!file && v.b64) {
      const dir = path.join(priv, "upload");
      fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
      file = path.join(dir, path.basename(v.name));
      fs.writeFileSync(file, Buffer.from(v.b64, "base64"), { mode: 0o600 });
    }
    if (!file || !fs.existsSync(file)) fail(`${f.label}: the file isn't in the run's folder`);
    // The file box's own click opens no chooser on this portal: what does is its button, or the drop zone beside it.
    let chooser = null;
    const tried = [];
    // The button, the drop zone, a label and the box, each plain then forced (to its centre, past the check of
    // what is on top). The cell's other elements and a mouse click at a point (no tab.cua on ChatGPT's tab) never
    // opened one (2026-11-21), and each try costs 6 s.
    const ways = [...b.ways.filter((w) => ["choose", "dropzone", "label"].includes(w.how)), { full: b.full, how: "box" }]
      .flatMap((w) => [{ ...w }, { ...w, force: true }, ...(tab.cua ? [{ ...w, mouse: true }] : [])]);
    for (const target of ways) {
      const how = target.how + (target.force ? " forced" : target.mouse ? " mouse" : "");
      // The chooser's promise is settled here whatever the click does: an unhandled rejection resets ChatGPT's whole
      // JavaScript session (2026-11-21).
      const p = pw.waitForEvent("filechooser", { timeout: 6000 }).then((c) => c, (e) => e);
      try {
        if (target.mouse) {
          // A real mouse click at its centre, past Playwright's checks: what a person's click reaches.
          if (!target.full) throw new Error("no id to find its centre by");
          const c = await page("centre", target.full);
          if (!c || !c.inView) throw new Error(c ? "not in view" : "no box to click");
          await tab.cua.click({ x: c.x, y: c.y });
        } else {
          const loc = target.full ? pw.locator(`[id="${target.full}"]`) : pw.locator(target.css).nth(target.nth);
          await loc.click({ timeout: 6000, ...(target.force ? { force: true } : {}) });
        }
        // A chooser by its shape: an error from the browser's service is of another realm (not instanceof Error here).
        const c = await p;
        if (!c || typeof c.setFiles !== "function") throw new Error(String((c && c.message) || "no file chooser"));
        chooser = c;
        (report.upload_ways = report.upload_ways || {})[how] = ((report.upload_ways || {})[how] || 0) + 1;
        break;
      } catch (e) { tried.push(`${how}: ${String(e && e.message || e).split("\n")[0].slice(0, 80)}`); await p; }
    }
    if (!chooser) {
      report.upload_tried = tried.map(run.scrub);
      report.upload_widget = await page("fileWidget", b.full).catch(() => null);
      noChooser = report.at.section;
      return handOver(f, v);
    }
    await chooser.setFiles([file]);
    await idle();
    let u = { named: false, refused: [] };
    for (const end = Date.now() + 10000; Date.now() < end && !u.named && !u.refused.length;) { u = await page("uploaded", v.name); await sleep(200); }
    if (u.refused.length) fail(`${f.label}: the portal refused ${v.name}: ${u.refused.join("; ")}`);
    if (f.describe) {
      const d = need(await page("describeBox", { id: f.id, css: f.css }), f.label);
      const box = pw.locator(`[id="${d.full}"]`);
      await box.fill(f.describe);
      await box.press("Tab");
      await idle();
    }
    return v.name;
  }
  function handOver(f, v) {
    yours.push({ section: report.at.section, slot: f.label, name: v.name, path: v.path || null });
    held.yours = held.yours.filter((x) => !(x.section === report.at.section && x.slot === f.label && x.name === v.name))
      .concat([{ section: report.at.section, slot: f.label, name: v.name }]);
    report.attach_yours = (report.attach_yours || []).filter((x) => !(x.section === report.at.section && x.slot === f.label))
      .concat([{ section: report.at.section, slot: f.label }]);
    return null; // not attached: no read-back
  }

  // A draft whose address expired (the portal's /cmd/error), opened again by its name from Pratiche in bozza.
  async function reopen(name) {
    await act(() => tab.goto(new URL("/fnsuap/cmd/home", steps.logged_in).href));
    for (let p = 2; ; p++) {
      const r = need(await page("draftOpen", { name, p }));
      if (!r.page) { await act(() => click(r, `${name}: Apri`)); break; }
      await click(r.page, `Pratiche in bozza, page ${p}`);
      await idle();
    }
    await until(() => page("hasOpenSection"), `${name}: the draft didn't open`, 60000);
    await idle();
    report.reopened_draft = true;
    return (await page("state")).url;
  }

  // the wizard
  async function wizard(step, value, wi) {
    report.at = { phase: "wizard", index: wi, screen: step.screen };
    if (!(await page("screenHas", step.screen))) fail(`expected the screen ${step.screen}`);
    if (step.fill) {
      const box = pw.locator(step.fill.css).first();
      await box.fill(value);
      await box.press("Tab");
      await idle();
    }
    for (const item of [].concat(step.tree || [])) {
      const leaf = typeof item === "string" ? item : item.leaf, nth = typeof item === "string" ? 0 : item.nth;
      for (let k = 0; ; k++) {
        const r = need(await page("tree", { leaf, nth }));
        if (r.selected) break;
        if (k > 8) fail(`tree: ${leaf} didn't stay selected`);
        await click(r, `tree: ${leaf}`);
        await idle();
      }
    }
    for (const [question, answer] of Object.entries(step.answers || {})) {
      await click(need(await page("siNo", { question, answer })), `${question}: ${answer}`);
      await idle();
    }
    const before = (await page("state")).title;
    if (!before) { await act(() => button(step.confirm)); return; }
    await button(step.confirm);
    await sleep(400);
    await until(async () => { const s = await page("state"); return !s.busy && s.title !== before; }, `still on ${step.screen} after ${step.confirm}`, 300000)
      .catch((e) => { if (/still on/.test(e.message)) fail(`still on ${step.screen} after ${step.confirm}`); throw e; });
    await idle();
  }

  // a section
  async function section(sec, vals, si) {
    const t0 = Date.now();
    report.at = { phase: "section", index: si, section: sec.section };
    if (steps.declarations.test(sec.section)) fail(`refused to open ${sec.section}: the person's declarations`);
    if (sec.go) {
      const here = async () => (await page("state")).title.includes(norm(sec.section));
      for (let t = 0; t < 2 && !(await here()) && sec.step && report.resumed; t++) {
        const a = await page("stepLink", sec.step);
        if (!a) break;
        await act(() => click(a, sec.step));
      }
      if (!(await here())) await act(() => button(sec.go));
      if (!(await here())) fail(`expected the screen ${sec.section}`);
    } else if (sec.open !== false) {
      const opened = await openSection(sec.section);
      if (/\/cmd\/error/.test((await page("state")).url)) fail("the draft's address has expired (the portal's error page)");
      if (!opened && !(await page("isOpen", sec.section))) {
        if (sec.optional) { (report.skipped_sections = report.skipped_sections || []).push(sec.section); return; }
        fail(`no section ${sec.section}`);
      }
    }
    const done = [], attached = {}, hidden = [];
    for (let [i, f] of sec.fields.entries()) {
      const v = vals[i];
      if (v === false) continue;
      report.at.field = i;
      report.at.label = f.label || f.id || f.css;
      let typed;
      if (f.kind === "add") { await addBlock(f); continue; }
      if (f.kind === "file" && !f.id && report.reopened && v !== null && v !== "") {
        f = await slotBox({ ...f, empty: true, name: v.name });
        if (f.already) { attached[norm(f.label)] = (attached[norm(f.label)] || 0) + 1; done.push({ ...f, kind: "file", typed: v.name, field: i }); continue; }
      } else if (f.kind === "file" && !f.id && attached[norm(f.label)] && v !== null && v !== "") f = await slotBox({ ...f, nth: attached[norm(f.label)] + 1 });
      if (f.id && f.label && !f.slotted) f = await located(f);
      if (!f.id && !f.css && f.if_present) {
        try { f = await bySpec(f, false); } catch (e) { if (e instanceof StepError) continue; throw e; }
      }
      if (!f.id && !f.css) f = await bySpec(f);
      await sweep();
      if (f.kind === "radio" || f.kind === "checkbox") typed = await tick(f);
      else if (v === null || v === "") continue;
      else if (f.kind === "select") typed = await select(f, v);
      else if (f.kind === "lookup") typed = await lookup(f, v);
      else if (f.kind === "file") {
        typed = await attach(f, v);
        if (typed === null) continue; // the tecnico's to attach
        attached[norm(f.label)] = (attached[norm(f.label)] || 0) + 1;
      }
      else typed = await text(f, v);
      done.push({ ...f, kind: f.kind === "date" ? "text" : f.kind, typed, field: i });
    }
    delete report.at.field;
    delete report.at.label;
    await sweep();
    if (sec.save !== false) await act(() => button(sec.save || "Salva"));
    // A slot whose file was handed over is the tecnico's: the portal's "required" under it isn't the run's error.
    const mine = yours.filter((y) => y.section === sec.section).map((y) => y.slot);
    const errs = await page("errors", [...(sec.theirs || []), ...mine]);
    for (const a of await page("alerts")) {
      const label = (done.find((d) => d.id === a.id) || {}).label || a.label;
      const x = { section: sec.section, label: label && run.scrub(label), text: run.scrub(a.text) };
      if (!(report.alerts = report.alerts || []).some((y) => y.section === x.section && y.label === x.label && y.text === x.text)) report.alerts.push(x);
    }
    const checks = await readBack(done, true);
    const bad = checks.filter((c) => !c.ok && !c.hidden);
    for (const c of checks.filter((c) => c.hidden)) hidden.push(c.label);
    held.details.push(...bad.map((c) => ({ section: sec.section, ...c })));
    const gone = bad.map(redact);
    if (hidden.length) report.hidden = (report.hidden || []).filter((h) => h.section !== sec.section).concat([{ section: sec.section, labels: hidden.map(run.scrub) }]);
    report.sections = report.sections.filter((x) => x.section !== sec.section)
      .concat([{ section: sec.section, seconds: +((Date.now() - t0) / 1000).toFixed(1), errors: errs, bad: gone }]);
    if (errs.length || bad.length) fail(`${sec.section}: portal errors ${JSON.stringify(errs)}, not kept ${JSON.stringify(gone)}`);
    keep(si, done);
  }
  const redact = (c) => ({ label: c.label, why: c.hiddenByChoice ? "hidden by a later choice" : c.ro ? "read-only: the portal fills it itself (`leave` it in the dictionary)" : c.got === null ? "missing" : c.got === "" || c.got === "unchecked" ? "empty" : "different" });
  async function readBack(done, own) {
    const items = [];
    const out = [];
    for (const f of done) {
      let g = f;
      if (f.kind !== "file" && f.spec) {
        const r = await page("resolve", f.spec);
        if (r.why) {
          if (own && /fields with this label/.test(r.why)) { out.push({ label: f.label || f.id, want: f.typed, got: null, ok: false, hiddenByChoice: true }); continue; }
          fail(r.why);
        }
        g = { ...f, id: r.id };
      } else if (f.kind !== "file" && f.id && f.label && !f.slotted) {
        const r = await page("located", spot(f));
        if (!r.why) g = { ...f, id: r.id };
      }
      items.push({ f: g, slot: out.length });
      out.push(null);
    }
    const res = await page("readBack", items.map(({ f }) => ({ id: f.id, kind: f.kind, typed: f.typed, label: f.label })));
    items.forEach(({ f }, k) => {
      const r = res[k];
      const label = f.label || f.css || f.id;
      out[items[k].slot] = r.hidden ? { label, hidden: true, ok: true } : r.ok ? { label, want: f.typed, got: f.typed, ok: true }
        : f.kind === "file" ? { label, want: f.typed, got: r.got, ok: r.got !== null }
        : f.kind === "radio" || f.kind === "checkbox" ? { label, want: "checked", got: r.got, ok: r.got === "checked" }
        : { label, want: f.typed, got: r.got, ok: false, ...(r.ro ? { ro: true } : {}) };
    });
    return out;
  }
  async function verify() {
    const t0 = Date.now();
    const url = (await page("state")).url;
    const u = new URL(url);
    const route = /^#[!/]/.test(u.hash);
    if (!route) u.hash = "";
    await act(() => (route ? tab.reload() : tab.goto(u.href)));
    if (/\/cmd\/error/.test((await page("state")).url)) fail("fresh load of the draft: the portal's error page (the sections are saved; open the draft from Pratiche in bozza)");
    const bad = [], hiddenAgain = [];
    for (const { si, done } of kept) {
      const sec = steps.sections[si];
      if (sec.go) continue;
      if (!(await openSection(sec.section)) && sec.open !== false && !(await page("isOpen", sec.section))) fail(`fresh load of the draft: no section ${sec.section}`);
      for (const c of await readBack(done)) { if (c.hidden) hiddenAgain.push(c.label); else if (!c.ok) bad.push({ section: sec.section, ...c }); }
    }
    report.verify_seconds = +((Date.now() - t0) / 1000).toFixed(1);
    if (bad.length) {
      held.details.push(...bad);
      fail(`fresh load of the draft: not kept ${JSON.stringify(bad.map(({ section, ...c }) => ({ section, ...redact(c) })))}`);
    }
  }
  async function readDeclarations() {
    const names = (await page("menuNames")).filter((n) => steps.declarations.test(n));
    const back = kept.filter((k) => !steps.sections[k.si].go).map((k) => steps.sections[k.si].section).pop();
    held.declarations = [];
    try {
      for (const name of names) {
        if (!(await openSection(name)) && !(await page("isOpen", name))) continue;
        held.declarations.push(need(await page("declarations", name)));
      }
      report.declarations_read = held.declarations.length;
    } catch (e) {
      report.declarations_read = held.declarations.length;
      report.declarations_note = run.scrub(said(e));
    }
    try { if (names.length && back) await openSection(back); }
    catch (e) { report.declarations_note = report.declarations_note || run.scrub(`could not go back to ${back}: ${e.message}`); }
  }
  async function fetchPreview() {
    delete report.preview_note;
    try {
      const url = new URL(steps.preview_url || "/fnsuap/preview.do", (await page("state")).url).href;
      const b64 = await pw.evaluate(`fetch(${JSON.stringify(url)}, { credentials: "include" }).then((r) => r.ok ? r.arrayBuffer() : Promise.reject(new Error("the portal answered " + r.status))).then((b) => { const u = new Uint8Array(b); let s = ""; for (let i = 0; i < u.length; i += 32768) s += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); return btoa(s); })`);
      const bytes = Buffer.from(b64, "base64");
      if (bytes.subarray(0, 5).toString() !== "%PDF-") fail("what it sent isn't a PDF");
      held.preview = bytes;
    } catch (e) {
      report.preview_note = run.scrub(said(e));
    }
    report.preview_pdf = !!held.preview;
  }

  const t0 = Date.now();
  const secs = () => +((Date.now() - t0) / 1000).toFixed(1);
  try {
    await tab.goto(resume.url || steps.start);
    await idle();
    let url = (await page("state")).url;
    if (!url.startsWith(steps.logged_in)) fail("not logged in to the portal");
    // A draft's address lasts only as long as the portal's session: a resume that doesn't land on the draft opens
    // it again from Pratiche in bozza, by its name.
    if (resume.url && (resume.reopen_draft || /\/cmd\/error/.test(url) || !(await page("hasOpenSection")))) url = await reopen(values.wizard[0]);
    if (/\/cmd\/error/.test(url)) fail("the draft's address has expired: open it again from Pratiche in bozza");
    const from = resume.from || {};
    for (const k of resume.kept || []) {
      keep(k.section, k.fields.map(([field, typed, at]) => {
        const def = steps.sections[k.section].fields[field];
        return { ...def, typed, field, ...(def.id || def.css ? {} : { spec: at !== undefined ? { ...def, last: false, at } : def }) };
      }));
    }
    if (from.section === undefined) {
      for (const [i, w] of steps.wizard.entries()) if (i >= (from.wizard || 0)) await wizard(w, values.wizard[i], i);
      await until(async () => { const s = await page("state"); return !s.composing && !s.busy; }, "the page didn't load: the portal was composing the pratica", 300000);
      await idle();
    }
    report.wizard_seconds = secs();
    const only = resume.only ? new Set(resume.only) : null;
    for (const [i, s] of steps.sections.entries()) if (!s.go && i >= (from.section || 0) && (!only || only.has(i))) await section(s, values.sections[i], i);
    if (!only && (steps.sections.some((s, i) => !s.go && i >= (from.section || 0)) || !steps.sections.some((s) => s.go))) {
      await verify();
      await readDeclarations();
    }
    for (const [i, s] of steps.sections.entries()) if (s.go && i >= (from.section || 0) && (!only || only.has(i))) await section(s, values.sections[i], i);
    if (!only) await fetchPreview();
    report.result = only ? "partial" : "filled";
    report.at = null;
  } catch (e) {
    report.result = "stopped";
    // As inpage.js fail(): a stop on the sign-in or on the portal's error page is that, whatever failed first.
    let why = said(e);
    try {
      const st = await page("state");
      if (st.signedOut && !/^signed out/.test(why)) why = `signed out: the portal sent the page to its sign-in (${why}); sign in again, then rerun`;
      else if (st.portalError && !/error page/.test(why)) why = `the portal answered an error page (${why}); wait a while, then rerun`;
    } catch (x) { /* the page is gone */ }
    report.error = why;
    try { report.snapshot = await page("look"); report.snapshot.boxes.forEach((b) => { b.label = run.scrub(b.label); }); } catch (x) { /* the page is gone */ }
  } finally {
    try { report.url = (await page("state")).url; } catch (e) { /* the page is gone */ }
  }
}
