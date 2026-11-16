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
//
// Round 10 (2026-11-16): the home page's draft list is stale after a bundle's runs (the new drafts are not in it): navigate to the home page again
// (https://suap.impresainungiorno.gov.it/fnsuap/cmd/home) before open(); that navigation drops `window.__draft`, so paste this file again after it. A click
// on APRI navigates twice (home, then the draft): the script that clicked is cut off and its value lost, so click in one call, wait ~10 s in the next, and
// then list the section links. Without the helper, `[...document.querySelectorAll("a")]` filtered on upper-case names lists the draft's sections, and
// `[...document.querySelectorAll("[name*='dynaForm']")]` its boxes (id, DIS, CHK, value, the text next to it): a box that stayed empty or a "Il valore è
// obbligatorio" beside it is the stop (the hotel's doubles, the one-off occupation's area "12.00": "il numero immesso non è valido").
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
      [...row.querySelectorAll("button,a,input")].find((e) => /APRI/i.test(e.innerText || e.value || "")).click();
      return "clicked APRI: wait ~8 s, then section()";
    },
    async section(name) {
      const a = [...document.querySelectorAll("a")].find((x) => x.innerText.toLowerCase().includes(name.toLowerCase()));
      if (!a) return "no section link with " + name;
      a.click();
      await wait(5000);
      return "opened " + a.innerText.trim();
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
