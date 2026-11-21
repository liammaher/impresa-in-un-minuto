// A tab shaped like ChatGPT's in-app browser tab, over Playwright for Node, for driver.mjs's offline test
// (test_driver.py). Its evaluate is read only, as ChatGPT's is: a call that changes a box's value, a tick or the
// title fails. It hides an email the page holds as ChatGPT's view does ("<redacted>"), and, as ChatGPT's browser,
// takes an action only from the call of the tool that is running (`calls` mode: an AsyncLocalStorage per call).
//
//   node driver_tab.mjs BASE_URL RUN_DIR [OPTS_JSON]     prints the driver's report as JSON
//   PLAYWRIGHT_NODE: the playwright package's folder (default: the one inside the ChatGPT app)

import { createRequire } from "node:module";
import fs from "node:fs";
import os from "node:os";
import { AsyncLocalStorage } from "node:async_hooks";

const als = new AsyncLocalStorage();
let active = null, strict = false;
const ctx = () => { if (strict && (active === null || als.getStore() !== active)) throw new Error("node_repl exec context not found"); };
const ACTIONS = new Set(["click", "fill", "press", "pressSequentially", "selectOption", "check", "uncheck", "setChecked", "waitFor", "setFiles"]);
const checked = (o) => new Proxy(o, { get(t, p) {
  const v = t[p];
  if (typeof v !== "function") return v;
  return (...a) => { if (ACTIONS.has(p)) ctx(); const r = v.apply(t, a);
    return r && typeof r === "object" && !(r instanceof Promise) && typeof r.then !== "function" ? checked(r) : r; };
} });

const [base, runDir, optsJson] = process.argv.slice(2);
const pwDir = process.env.PLAYWRIGHT_NODE || "/Applications/ChatGPT.app/Contents/Resources/cua_node/lib/node_modules/playwright";
const { chromium } = createRequire(pwDir + "/")(pwDir);
const cache = `${os.homedir()}/Library/Caches/ms-playwright`;
const exe = fs.existsSync(cache) && fs.readdirSync(cache).filter((d) => /^chromium-\d+$/.test(d)).sort().pop();
const mac = exe && `${cache}/${exe}/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`;
const browser = await chromium.launch(mac && fs.existsSync(mac) ? { executablePath: mac } : {});
const page = await browser.newPage();

const redacted = /^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i;
const tab = {
  goto: (url) => { ctx(); return page.goto(url); },
  reload: () => { ctx(); return page.reload(); },
  playwright: {
    async evaluate(fn, arg) {
      if (typeof fn !== "string") throw new Error("driver.mjs sends page code as a string (ChatGPT's REPL can't build it)");
      ctx();
      // Read only, as ChatGPT's view: while the script runs (synchronously, so the page's own handlers can't run in
      // between), setting a box's value, a tick or the title throws. An email reads "<redacted>", as ChatGPT's view.
      return page.evaluate(([src, rx]) => {
        const re = new RegExp(rx, "i");
        const trap = (proto, key, read) => {
          const d = Object.getOwnPropertyDescriptor(proto, key);
          Object.defineProperty(proto, key, { configurable: true, get() { return read ? read(d.get.call(this)) : d.get.call(this); },
            set() { throw new Error("evaluate wrote to the page: ChatGPT's view is read only"); } });
          return () => Object.defineProperty(proto, key, d);
        };
        const undo = [trap(HTMLInputElement.prototype, "value", (v) => (re.test(v) ? "<redacted>" : v)),
          trap(HTMLInputElement.prototype, "checked"), trap(HTMLTextAreaElement.prototype, "value"),
          trap(HTMLSelectElement.prototype, "value"), trap(Document.prototype, "title")];
        try { return (0, eval)(src); } finally { undo.forEach((f) => f()); }
      }, [fn, redacted.source]);
    },
    locator: (css) => checked(page.locator(css)),
    // noChooser: as ChatGPT's browser on the attachments screen, no click ever gives a file chooser.
    waitForEvent: (name, o) => { ctx(); return NO_CHOOSER && name === "filechooser"
      ? new Promise((_, no) => setTimeout(() => no(new Error(`Timed out after ${o && o.timeout}ms waiting for file chooser.`)), Math.min((o && o.timeout) || 1000, 1000)))
      : page.waitForEvent(name, o).then((c) => checked(c)); },
  },
};

const d = await import(new URL("../driver.mjs", import.meta.url).href);
await page.goto(base + "/");
const opts = optsJson ? JSON.parse(optsJson) : {};
const NO_CHOOSER = !!opts.noChooser;
let report;
if (opts.calls) {
  // As ChatGPT's tool: start() in one call returns at once, then short wait() calls, each its own call with a gap
  // between them; an action belongs to the call whose code made it, and only the running call's are taken.
  strict = true;
  let n = 0;
  active = ++n;
  als.run(active, () => d.start(tab, runDir, opts));
  active = null;
  for (;;) {
    const id = ++n;
    active = id;
    report = await als.run(id, () => d.wait(opts.calls));
    active = null;
    if (report.result !== "running") break;
    await new Promise((r) => setTimeout(r, 700));
  }
} else report = await d.run(tab, runDir, opts);
console.log(JSON.stringify(report));
await browser.close();
