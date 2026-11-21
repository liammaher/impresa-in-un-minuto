// A tab shaped like ChatGPT's in-app browser tab, over Playwright for Node, for driver.mjs's offline test
// (test_driver.py). Its evaluate is read only, as ChatGPT's is: a call that changes a box's value, a tick or the
// title fails. It hides an email the page holds as ChatGPT's view does ("<redacted>").
//
//   node driver_tab.mjs BASE_URL RUN_DIR [OPTS_JSON]     prints the driver's report as JSON
//   PLAYWRIGHT_NODE: the playwright package's folder (default: the one inside the ChatGPT app)

import { createRequire } from "node:module";
import fs from "node:fs";
import os from "node:os";

const [base, runDir, optsJson] = process.argv.slice(2);
const pwDir = process.env.PLAYWRIGHT_NODE || "/Applications/ChatGPT.app/Contents/Resources/cua_node/lib/node_modules/playwright";
const { chromium } = createRequire(pwDir + "/")(pwDir);
const cache = `${os.homedir()}/Library/Caches/ms-playwright`;
const exe = fs.existsSync(cache) && fs.readdirSync(cache).filter((d) => /^chromium-\d+$/.test(d)).sort().pop();
const mac = exe && `${cache}/${exe}/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`;
const browser = await chromium.launch(mac && fs.existsSync(mac) ? { executablePath: mac } : {});
const page = await browser.newPage();

const state = () => page.evaluate(() => JSON.stringify([document.title,
  ...[...document.querySelectorAll("input, select, textarea")].map((e) => [e.id, e.value, e.checked])]));
const redacted = /^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i;
const tab = {
  goto: (url) => page.goto(url),
  reload: () => page.reload(),
  playwright: {
    async evaluate(fn, arg) {
      if (typeof fn !== "string") throw new Error("driver.mjs sends page code as a string (ChatGPT's REPL can't build it)");
      const before = await state();
      // ChatGPT's view reads an email as "<redacted>": its value getter here does the same while the call runs.
      const out = await page.evaluate(([src, rx]) => {
        const re = new RegExp(rx, "i");
        const d = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
        Object.defineProperty(HTMLInputElement.prototype, "value", { configurable: true,
          get() { const v = d.get.call(this); return re.test(v) ? "<redacted>" : v; }, set(v) { d.set.call(this, v); } });
        const restore = () => Object.defineProperty(HTMLInputElement.prototype, "value", d);
        try { const r = (0, eval)(src); return Promise.resolve(r).finally(restore); } catch (e) { restore(); throw e; }
      }, [fn, redacted.source]);
      if ((await state()) !== before) throw new Error("evaluate wrote to the page: ChatGPT's view is read only");
      return out;
    },
    locator: (css) => page.locator(css),
    waitForEvent: (name, opts) => page.waitForEvent(name, opts),
  },
};

const d = await import(new URL("../driver.mjs", import.meta.url).href);
await page.goto(base + "/");
const report = await d.run(tab, runDir, optsJson ? JSON.parse(optsJson) : {});
console.log(JSON.stringify(report));
await browser.close();
