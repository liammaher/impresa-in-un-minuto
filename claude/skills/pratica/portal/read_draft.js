// Read a draft's section by hand in the pane, when crawl.js isn't loaded (no bundle, no file pick): what each box is, which are switched
// off, which ticks switch them on, which the portal calls required. Paste it into the pane's JavaScript tool on the portal's page, then call
// (each call under the pane's 45 s; wait in the page, never outside it):
//
//   __draft.open("subingresso media grande")   click APRI on the newest draft whose name contains this (Pratiche in bozza), then
//                                              `await __draft.section("responsabile")` to open the section whose link contains it
//   __draft.controls()                         [type, id, DIS|"", CHK|"", value, hid|"", the text next to it] of the open section's boxes
//   __draft.toggle("r14c1p26reg:chk")          click one box (a checkbox: the real input; a radio: its visible `_clone`), wait, and say which
//                                              boxes changed from disabled to enabled or the reverse (what a tick switches on)
//   __draft.required()                         press SALVA with the section as it is and list the boxes the portal calls required
//                                              ("Il valore è obbligatorio", "deve essere selezionata almeno un'opzione"): the page re-renders
//   __draft.text(from)                         the section's visible text from the first line containing `from`
//   __draft.list() / page(n)                   the home list's drafts as "[type] name" / click its numbered link n (10 a page)
//   __draft.sections()                         an open draft's section links (Dati Dichiarazioni), upper-case titles
//   __draft.options("r2c1p2reg") / choose(frag, "tenda esterna")   a select's options / choose one and say which boxes changed (nothing saved)
//   __draft.confirm()                          press Conferma on «Proseguire senza salvare?» (leaving a section with toggled boxes)
//
// Round 10 (2026-11-16): the home page's draft list is stale after a bundle's runs (the new drafts are not in it): navigate to the home page again
// (https://suap.impresainungiorno.gov.it/fnsuap/cmd/home) before open(); that navigation drops `window.__draft`, so paste this file again after it. A click
// on APRI navigates twice (home, then the draft): the script that clicked is cut off and its value lost, so click in one call, wait ~10 s in the next, and
// then list the section links. Without the helper, `[...document.querySelectorAll("a")]` filtered on upper-case names lists the draft's sections, and
// `[...document.querySelectorAll("[name*='dynaForm']")]` its boxes (id, DIS, CHK, value, the text next to it): a box that stayed empty or a "Il valore è
// obbligatorio" beside it is the stop (the hotel's doubles, the one-off occupation's area "12.00": "il numero immesso non è valido").
// 2026-11-20 (round 21): `window.__draft` is lost at EVERY navigation, a section link's click included (the page is reloaded, not swapped): click
// the link in one call, wait ~6 s, then paste the helper (the object below, without a call that clicks) and read. A stand-alone draft is
// the way to a page: choosing the wizard's sector by clicks or `span.click()` did not register in the pane («Deve essere selezionato almeno un
// elemento», "Settore selezionato" empty), so get a draft by running a rehearsal of the pratica (bench/rerun.py) and open it here. A radio is
// switched by its visible `_clone` (`...:radio:N_clone`), not the input; SALVA on a section whose declarations are unticked answers
// «Il valore è obbligatorio» for each (the person's declarations: never ticked for them), and that is not a stop of the section's own boxes.
// 2026-11-21 (round 22), without the helper, in four calls a draft: (1) navigate to cmd/home (a bundle's new drafts are not in the list until you do),
// (2) the list is 10 per page and older drafts are on the numbered links under it (click "2", wait ~4 s: the page is reloaded), (3) click the row's APRI in
// one call and wait ~8 s, then "Dati Dichiarazioni" for the section links or "Allega Documenti" for the attachment slots (`document.body.innerText` from
// «DOCUMENTI ALLEGATI»), (4) a box is switched by the visible `*_clone` of a radio (`[id*='r4c1p4reg']` filtered on offsetParent): click it,
// wait 2.5 s and read what appeared. Nothing is saved until SALVA, so a toggle only reads; read-only is what this is for. Drafts left on the portal
// are the made-up ones ("PROVA NON INVIARE - ..."), kept so a later round can compare a section across them (the plain and the vincolo sign's attachments, round 22).
// Round 23 (2026-11-21), what bit on the dehors' hours and period: (a) on the home list APRI is a `<button>` around a `<span>` (no `<a>`): find the row,
// then the span's `closest("a,button")`, and click it inside a `setTimeout` so the call returns before the page navigates (the home list's pages: `[...document.querySelectorAll("a, span")].filter((e) => e.textContent.trim() === "3" && e.closest(".ui-paginator, [class*=paginator]"))[0].click()`, then wait ~4 s; a draft's name is in the row's text, and 10 drafts a page: 30 made-up drafts were on three pages); (b) a section link in the draft (`<a href="#">`) clicked by script works (the dehors' sections, «Allega Documenti», «Dati Dichiarazioni»); one that seemed to do nothing
// after a toggle had opened the confirm of (c) underneath: read the page's text for it before trying another way to click;
// (c) leaving a section whose boxes you toggled shows «Le informazioni inserite non sono state salvate. Proseguire senza salvare ?»: press its Conferma
// (the visible one inside the dialog), nothing was saved, the toggles are gone; (d) one attempt to tick a weekday's checkbox by script (its `.ui-chkbox-box`) did not
// register and was not investigated; the runner's `kind: checkbox` ticks them (the five dehors runs read the rows back), so read what a checkbox switches on from a run;
// (e) radios that look like one group may be five single-radio groups with the portal's own exclusion (the dehors' period): toggle each and read the
// others' checked/disabled state before writing a dictionary entry as «one of».
// Round 24 (2026-11-21): the JavaScript tool evaluates your text as a REPL (the last expression is the result, top-level `await` works): a top-level
// `return` is a SyntaxError and gives `undefined`. The home page is `cmd/home`; a pane with no tab is opened by navigating there, and navigating away from an open
// draft needs `force` (the «Leave site?» dialog). The list of drafts showing is also the check that the pane is still signed in: read it before asking for the SPID login.
// The home list's APRI is «Apri» in `textContent` (the page's CSS upper-cases it; `innerText` reads «APRI»): match it case-insensitively, a `/APRI/` on `textContent` finds no button and the click does nothing.
// Round 25: a section's ids shift when an earlier choice opens a block, and the runner can tick the id of a layout the live page does not have (`didn't stay ticked`): read the live ids with controls() and compare them with the crawl's `moved` pairs (README, round 25). A click on a checkbox's label through the pane's left_click did not tick it in one try (not investigated).
// The helper now has list(), page(n), sections(), confirm(), options(frag) and choose(frag, text) for what each of those took by hand in rounds 22-24; every click that
// navigates goes in a timeout, so the call returns, and the helper must be pasted again afterwards (the page is reloaded, not swapped).
// Written 2026-11-15 for round 7 (README): it found that the VV.F. take-over's statements a) and b) are required and b) switches on the
// previous manager's boxes, that the garage's header radio is not kept, and what the B&B variation's capacity groups need. A page that
// navigates (open, section, required) loses the return value of the call that caused it: look at the page, then call again.
window.__draft = (() => {
  const boxes = () => [...document.querySelectorAll("[name*='dynaForm']")].filter((e) => e.type !== "hidden" && !/combo_filter|combo_focus/.test(e.name));
  const id = (e) => e.name.split("dynaForm:")[1];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const near = (e) => {
    const td = e.closest("td") || e.parentElement, prev = td.previousElementSibling;
    return ((td.innerText || "").trim() || (prev && prev.innerText || "").trim()).replace(/\s+/g, " ").slice(0, 70);
  };
  const state = () => Object.fromEntries(boxes().filter((e) => !(e.type === "radio" && e.offsetParent === null)).map((e) => [id(e), !e.disabled]));
  return {
    open(name) {
      const row = [...document.querySelectorAll("tr")].find((r) => r.innerText.replace(/\s+/g, " ").toLowerCase().includes(name.toLowerCase()));
      if (!row) return "no draft row with " + name;
      // APRI is a <button> around a <span>; the click navigates twice, so it goes in a timeout and the call returns first (rounds 23 and 24).
      const apri = [...row.querySelectorAll("button,a,input")].find((e) => /APRI/i.test(e.innerText || e.textContent || e.value || ""));
      if (!apri) return "no APRI in the row";
      setTimeout(() => apri.click(), 50);
      return "clicked APRI: wait ~8 s, paste this file again (the page was reloaded), then sections() or section()";
    },
    async section(name) {
      const a = [...document.querySelectorAll("a")].find((x) => x.innerText.toLowerCase().includes(name.toLowerCase()));
      if (!a) return "no section link with " + name;
      // The page is reloaded, so the helper is gone after it: click in a timeout, wait ~6 s outside, paste the file again. A section left with
      // toggled boxes asks «Proseguire senza salvare?» first: confirm() presses Conferma (nothing is saved).
      setTimeout(() => a.click(), 50);
      return "clicking " + a.innerText.trim() + ": wait ~6 s (confirm() if the page asks to leave unsaved changes), paste this file again";
    },
    // The home list: the drafts on this page as "[type] name" (10 a page), and the numbered links under it.
    list() {
      return [...document.body.innerText.matchAll(/\[(\w\w)\] - ([^\n\t]*)\t/g)].map((m) => m[1] + " " + m[2]);
    },
    page(n) {
      const e = [...document.querySelectorAll("a, span")].find((x) => x.textContent.trim() === String(n) && x.children.length === 0);
      if (!e) return "no page link " + n;
      setTimeout(() => e.click(), 50);
      return "clicking page " + n + ": wait ~4 s, paste this file again, then list()";
    },
    // The section links of an open draft (Dati Dichiarazioni): upper-case titles.
    sections() {
      return [...document.querySelectorAll("a")].map((a) => a.innerText.trim()).filter((t) => t.length > 3 && !/^[A-Z][a-z]/.test(t));
    },
    // «Proseguire senza salvare?»: press the visible Conferma of the dialog (what leaving a section with toggled boxes shows).
    confirm() {
      const b = [...document.querySelectorAll("button, a, span")].find((x) => x.offsetParent && x.textContent.trim() === "Conferma");
      if (!b) return "no Conferma on the page";
      setTimeout(() => b.click(), 50);
      return "pressed Conferma: wait ~6 s, paste this file again";
    },
    // A select's options, and what choosing one switches. The portal's selects are PrimeFaces combos over a <select id="...:combo_input">: setting its
    // value and firing `change` is what a choice does on the client (the label follows). Round 24: none of the sign's 11 «Tipologia» options changed
    // another box, on either screen. Nothing is saved; leaving asks to confirm.
    options(frag) {
      const s = document.querySelector(`select[id*='${frag}']`);
      return s ? [...s.options].map((o) => o.text.trim()) : "no select with " + frag;
    },
    async choose(frag, optionText) {
      const s = document.querySelector(`select[id*='${frag}']`);
      if (!s) return "no select with " + frag;
      const o = [...s.options].find((x) => x.text.trim().toLowerCase() === optionText.toLowerCase());
      if (!o) return "no option " + optionText;
      const before = state();
      s.value = o.value;
      s.dispatchEvent(new Event("change", { bubbles: true }));
      await wait(2500);
      const after = state();
      return JSON.stringify({ now: s.options[s.selectedIndex].text.trim(), switched_on: Object.keys(after).filter((k) => after[k] && before[k] === false),
                              switched_off: Object.keys(after).filter((k) => !after[k] && before[k]), new_boxes: Object.keys(after).filter((k) => !(k in before)) });
    },
    controls() {
      return JSON.stringify(boxes().filter((e) => !(e.type === "radio" && e.offsetParent === null))
        .map((e) => [e.type, id(e), e.disabled ? "DIS" : "", e.checked ? "CHK" : "", (e.value || "").slice(0, 12), e.offsetParent === null ? "hid" : "", near(e)]));
    },
    async toggle(name) {
      const before = state();
      const e = boxes().find((x) => id(x) === name || (x.id || "").endsWith(name));
      if (!e) return "no box " + name;
      (e.type === "radio" ? document.querySelector(`[id$='${name.split(":radio")[0]}:radio:${(e.id.match(/:radio:(\d+)/) || [0, 0])[1]}_clone']`) || e : e).click();
      await wait(3500);
      const after = state();
      return JSON.stringify({ switched_on: Object.keys(after).filter((k) => after[k] && before[k] === false), switched_off: Object.keys(after).filter((k) => !after[k] && before[k]),
                              new_boxes: Object.keys(after).filter((k) => !(k in before)) });
    },
    async required() {
      const save = document.querySelector("[id$=':uncheckedSave']");
      if (!save) return "no SALVA";
      save.click();
      await wait(6000);
      return JSON.stringify([...document.querySelectorAll("*")].filter((e) => e.children.length === 0 && /obbligatori|almeno un'opzione|non valido|deve essere/i.test(e.innerText || "")).map((e) => {
        let p = e;
        for (let i = 0; i < 4; i++) { p = p.parentElement; const x = p && p.querySelector("[name*=dynaForm]"); if (x) return [id(x), (e.innerText || "").trim().slice(0, 80), near(x)]; }
        return ["?", (e.innerText || "").trim().slice(0, 80)];
      }));
    },
    text(from) {
      const t = document.body.innerText.replace(/[ \t]+/g, " ").replace(/\n\s*\n+/g, "\n");
      return t.slice(Math.max(0, t.lastIndexOf(from || "")), 4000);
    },
  };
})();
"__draft ready"
