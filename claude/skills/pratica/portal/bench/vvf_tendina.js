// The option codes of the VV.F. tendina («attività - sotto classe - categoria - descrizione») on an open payment slip
// (PIN 3-6), for the category radio now chosen. Run it in the pane's page after choosing A, B or C (click the radio at
// the full-frame coordinates: a script's click() on the input does not change the choice), once per category, and
// compare with catalogue/F839/vvf-attivita.json (README, "Round 13"). It reads only the select's options, never a value.
(() => {
  const selects = [...document.querySelectorAll("select")].filter((s) => [...s.options].some((o) => / _ \d+ _ [ABC]\b/.test(o.text) || /^\d+ _ \d+ _ [ABC]:/.test(o.text)));
  return JSON.stringify(selects.map((s) => {
    const codes = [...s.options].map((o) => (o.text.match(/^(\d+ _ \d+ _ [ABC])\b/) || [])[1]).filter(Boolean);
    return { id: s.id.slice(-30), categories: [...new Set(codes.map((c) => c.slice(-1)))], count: codes.length, codes };
  }));
})()
