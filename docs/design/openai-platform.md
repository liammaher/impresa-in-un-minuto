# The plugin on OpenAI (Codex, the ChatGPT desktop app)

Status: started 2026-11-20. Claude and Cowork stay the customer path (`packaging.md`); this is a second build target for
people who use Codex or the ChatGPT desktop app. **Since 2026-11-21 it fills the portal in the ChatGPT desktop app's
in-app browser** with `portal/driver.mjs` ("The fill in ChatGPT", below); in Codex in a terminal, which has no browser,
it is a check only. The Claude build says what it said before: its texts' Claude parts are
kept as they were, and only two runner messages changed («scrivilo nella chat», «nemmeno nella chat», which name no
assistant).

## What exists

- `plugin/build.py --target openai` (out: `plugin/dist/openai/`): a root `plugin.json` (Agent Plugins 1.0.0, the
  portable fields of the hand-written Claude manifest, so name and version have one source) instead of
  `.claude-plugin/`. Under `extensions.com.openai` it has `requires_local_executor: true` (the runner's scripts
  run on the computer, so ChatGPT on the web and on phones must not offer it) and an `interface` made of the
  manifest's own texts: display name, long description, developer, website, plus a category and the Prova as
  the starter prompt. It has no `shortDescription` (the portable format derives one), and no icons or
  support, privacy or terms URLs, which the public directory requires. With `--connector URL`, `mcp.json`
  (`streamable-http`) instead of `.mcp.json`. No Cowork test skill, no evals (`--cowork-test` and `--evals` are
  refused: they are Claude's).
- The texts: a part that differs between the two is written twice, `<!-- claude -->` and `<!-- openai -->`. For openai:
  an override at the top of SKILL.md (a check only: step 0, steps 1-3, the report of «A check only»), steps 4 to 7 and
  the Prova Claude's alone, prova.md's two lines instead, the no-job reply and the check's last line, what `<skill-dir>`
  is, `dove`, and the README's opening, coverage, use, data, install and privacy parts. The Cowork-only parts are
  Claude's alone. A skill's description for ChatGPT is `metadata: openai-description` in its frontmatter (markers
  would break the YAML), the manifest's `metadata.openai.description`: the build moves each into place for openai
  and drops it for both, so each has one hand-written source, which test_english and test_voice read. Then the openai build writes `<skill-dir>` for
  `${CLAUDE_SKILL_DIR}` and ChatGPT for every other Claude (`openai_words`), and stops on a name only Claude's apps
  have (`CLAUDE_ONLY`: Claude in Chrome, Claude Code, Cowork, AskUserQuestion, `tabs_context` ...) left outside a
  Claude part. `test_build.py` runs that on the hand-written texts without a build.
- `report.py` reads either manifest, and its `dove` (and the bug form's) has `ChatGPT desktop, Codex` and
  `Codex nel terminale`. `run.py`'s `published()` finds either manifest: the openai build fetches the runner from
  the same `plugin-v<version>` tag, whose files are byte for byte the same.
- Publishing: `publish_plugin.py --target openai` commits the build to the `plugin-openai` branch, tagged
  `plugin-openai-v<version>`; `pin_marketplace.py --target openai` writes `.agents/plugins/marketplace.json`, the
  same marketplace name, its entry a `url` source with that tag and SHA. The release workflow does both after the
  Claude ones (without the archive only: the setup skill has no OpenAI words yet) and pins both in one pull request.
  Nothing is published until the next release runs.

## What the spike found (2026-11-20, Codex CLI 0.171 as the ChatGPT desktop app ships it)

The CLI at `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex` (the npm one on the maintainer's machine
was 0.57, too old for plugins, and broken), with a throwaway `CODEX_HOME`.

1. **The skill's folder.** OpenAI has no variable; its own skills write `<skill-dir>` and say once that it is the
   SKILL.md's directory (the bundled `visualize` skill). With that, `codex exec "fammi vedere una prova"` found
   the skill (`impresa-in-un-minuto:pratiche`), read SKILL.md and prova.md from the install cache
   (`~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/`) and put that absolute path in every command.
2. **Shell and Python.** The Codex CLI ran `sh <skill-dir>/py` on the computer's own Python (sandbox
   `workspace-write`): `prova.py`, `check.py`, `run.py preflight` (ready) and `run.py page`. It then said, as the
   texts told it, that the fill needs the app's browser.
3. **The browser: it reads with a script and writes as a person does.** The ChatGPT desktop app has an in-app browser
   (the bundled Browser plugin, 26.1117). Its JavaScript tool (`node_repl`) is a Node process: `cua.createBrowserTab
   ("iab", url)` gives a tab, `tab.playwright` a subset of Playwright. Tested on a page of our own (2026-11-21):
   - `tab.playwright.evaluate` reads and can't write: a value set in it throws "Cannot set property value of [object
     Object] which has only a getter", and a fresh read finds the page unchanged. So `inpage.js` can't run there.
   - `locator(css).fill`, `check`, `setChecked`, `selectOption`, `click`, `press`, `pressSequentially` write, and the
     page's own handlers run (its `input` listener saw the value). A file goes in through
     `tab.playwright.waitForEvent("filechooser")` and `chooser.setFiles([absolute path])`: from disk, with no size limit.
   - The REPL has `fs` and imports a module by its absolute path (`await import(nodeRepl.homeDir + "/.codex/...")`),
     with no approval asked. A module there read a values file, filled the page and returned only `{filled, length}`:
     the conversation's record holds the value 0 times. So the values never pass through the chat, and need no
     code to seal them: the module reads them from the run's private folder.
   - A tab belongs to its turn: the next turn's call on it fails ("Tab 1 is not part of browser session ..."). A run
     must end within the turn, or take the tab again.
   - A chat whose folder no longer exists starts without the Browser plugin's server (`node_repl`: "MCP server
     startup failed ... No such file or directory"), and the CLI (`codex exec`) has no in-app browser at all
     ("The browser access host is unavailable"). Both say «no browser» to the person, never «the plugin is broken».

   Getting around the read-only evaluate (a `javascript:` address, an injected tag) is not a way: it would work against
   a limit OpenAI put on its browser on purpose. The fill uses the API as it is meant to be used.
4. **Manifests and marketplaces.** Codex installs the portable root `plugin.json`, and also a Claude-format plugin as
   it is (it read 0.8.2 from `.claude-plugin/plugin.json` through a `url` source). It reads our
   `.claude-plugin/marketplace.json` but lists no plugin from it: it has no `github` source type (its types: `local`,
   `url`, `git-subdir`, `npm`). With `.agents/plugins/marketplace.json` beside it, under the same name, Codex reads
   that one.

## The fill in ChatGPT

`inpage.js` is one script in the page: it drives the portal in a frame over the pane's page, reads and writes the DOM
directly, sets dropdowns and street lookups through PrimeFaces' own widgets (`selectItem`, `search`, `setValue`),
builds uploads with `DataTransfer`, and keeps its state in `sessionStorage`. None of those writes is open to it in
ChatGPT. So ChatGPT gets a driver in Node, `driver.mjs`, which the model imports from `<skill-dir>` and starts with
one call; the steps files, the dictionary, pre-flight, review.py and the closing lines stay the same.

- **Reads: a copy, for now.** What `inpage.js` reads (a box by its id or its label, `located`/`resolve`, the
  read-back, `errors`, `alerts`, a slot's title and types, `look`, busy, the declarations' text) is `driver.mjs`'s
  `pageApi`, sent to `evaluate` as one string with the steps' `label_js` inlined (`adaptLabelJs`: document order for
  `compareDocumentPosition`); it returns each box's full id for the driver's locator. Not yet shared with the pane: a
  fix to one of those reads goes in both files until `reads.js` takes them out of `inpage.js`.
- **Writes are a person's.** Text: `fill`, then Tab (the change and blur the portal listens to). A dropdown: a
  click on the drawn menu, then on its item (what `selectItem` did for us is what a click does). A street: typed with
  `pressSequentially` (the widget searches on keys), then a click on the one matching item, by the same matching
  rules. A box: `check`. A file: the file chooser from the run's folder, so the 256 KB and the box on the page are
  gone. Open lists and the calendar: Escape or a click elsewhere, not a style written over them.
- **Waits read.** `busy` (jQuery and PrimeFaces' queue), «Attendere prego», signed out and the portal's error page are
  read through `evaluate` in a loop; a save that reloads the page is waited out with `waitForLoadState`. The driver
  lives in Node, so a reload doesn't end it: no frame over the page.
- **The privacy contract is the same.** The model writes `const r = await (await import(<skill-dir> +
  "/portal/driver.mjs")).run(tab, <run folder>)`: values and files come from the run's private folder (run.py
  writes it), the return is `publicReport()` (no value, as now), what the reports leave out goes to that folder.
  The person still signs in, ticks the declarations, signs, pays and sends; `forbidden` and `declarations` refuse
  as they do. Values typed in the portal are on the page, so the driver never returns a snapshot of a filled box,
  as `look()` doesn't now.

Settled on the real portal (2026-11-21, six runs of the CILA rehearsal's made-up case from ChatGPT, a test module
in `~/.codex`, the values read from the run's private folder):

1. **Sign-in and long calls.** The person signs in with SPID once in the in-app browser; a new tab in a later turn is
   signed in. One call with `timeout_ms` 900000 ran 4 minutes. The REPL imports a module afresh on every call and
   `new Function`/`eval` are refused in Node too ("Code generation from strings disallowed"): a run's state lives
   on `globalThis`, and a page function built at run time goes to `evaluate` as a string expression.
2. **What the view can read.** No `offsetParent` (visibility is `getClientRects()`), no `compareDocumentPosition`
   (the label before a box goes by document order: `label_js` must not use it), no `eval`, and no page globals
   (`jQuery`, `PrimeFaces` are undefined): busy is the page's own «Attendere» boxes and `readyState`, and a list
   another choice fills (Comune after Provincia) is waited on by its options. So a section takes 25 to 45 s
   (the pane: about 5).
3. **Writes.** The wizard (description, tree, CONFERMA) in 15 s. Text: `fill`, Tab, read back; a box that comes
   back empty (the street name, the phone's number box) is typed key by key. Dropdowns: a click on the drawn menu,
   half a second, a click on the item, up to three tries (a long list missed once); `selectOption` on the hidden
   list is the fallback. The street lookup: keys, then the one matching item. Radio and date as text. An upload:
   the file box's own click opens no chooser; its button does, and `setFiles` from disk went in (the page named
   the file, Salva raised no error). The Scheda anagrafica's 17 boxes all read back after Salva.
4. **Emails and phone numbers are hidden.** The view reads them as `<redacted>`, the page script's own comparison
   too: the driver can't check them. They are listed in the report as `hidden`, and the closing lines ask the
   person to look at those boxes on the page.

Still open: the preview PDF (`fetch` in `evaluate`, or `waitForEvent("download")`).

Built: `driver.mjs` (start/wait/run on `globalThis`; `resume: true` picks a stopped run up from its own report and
private `kept.json`), `run.py chatgpt` (the run folder: `private/chatgpt-run.json`, each file by its path), review.py's
`hidden` lines, and the openai texts' steps 4 to 6 and Prova. `bench/test_driver.py` runs it on test_inpage.py's fake
portal through `bench/driver_tab.mjs`, a tab over Playwright for Node whose `evaluate` fails on any write and reads an
email as `<redacted>`. Not yet: the second compilation (after the declarations), the check of the portal's preview
against the documents (Claude's step 5), and `reads.js`. A draft whose address expired is reopened from Pratiche in
bozza by its name, as inpage.js does.

## What the target does not do yet

- A whole pratica run end to end in ChatGPT, recorded in `runs.json` (the driver ran the CILA's wizard and four of its
  sections on the portal, as the test module).
- The second compilation, the preview check, `reads.js` (above).
- The archive (`vault: true`): the setup skill and the vault parts have no OpenAI words.
- The directory listing: icons, `shortDescription`, support, privacy and terms URLs, and the plugin portal's review.
- The connector's ChatGPT side (`search`/`fetch`, origins, CORS) and a Codex run of the evals.
