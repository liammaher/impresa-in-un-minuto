# The plugin on OpenAI (Codex, the ChatGPT desktop app)

Status: started 2026-11-20. Claude and Cowork stay the customer path (`packaging.md`); this is a second build target for
people who use Codex or the ChatGPT desktop app. **In ChatGPT it is a check only, for now**: it reads a job's folder and
says which pratica, which files the sportello would refuse and what is missing, and never opens or fills the portal
(why: "The browser", below). The Claude build says what it said before: its texts' Claude parts are
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
3. **The browser: it can't fill a page.** The ChatGPT desktop app has an in-app browser (the bundled Browser plugin,
   driven from a Node REPL), but its `tab.playwright.evaluate` runs a script in a read-only sandbox: the service
   (`browser-service.mjs`) wraps every DOM node and `window` in read-only proxies in an isolated execution context,
   and a string script must be one expression (`return (<script>)`). Nothing else in its API runs a script; what writes
   is clicks and typing, one node at a time. So `inpage.js` can't run there. The way that remains is `run.py run`
   (inpage.js in a Playwright window; `--cdp` attaches to the person's own Chrome, so no browser download), which
   needs the Python `playwright` package (about 40 MB), installed once with the person's yes: the plugin's
   launcher has no packages today. Not built: until it is, the openai target is a check only.
4. **Manifests and marketplaces.** Codex installs the portable root `plugin.json`, and also a Claude-format plugin as
   it is (it read 0.8.2 from `.claude-plugin/plugin.json` through a `url` source). It reads our
   `.claude-plugin/marketplace.json` but lists no plugin from it: it has no `github` source type (its types: `local`,
   `url`, `git-subdir`, `npm`). With `.agents/plugins/marketplace.json` beside it, under the same name, Codex reads
   that one.

## What the target does not do yet

- The compilation (and so the Prova): `run.py run --cdp` from the launcher with `playwright` installed on a yes
  (step 3 above), then the override at the top of SKILL.md goes and steps 4 to 7 come back for openai.
- The archive (`vault: true`): the setup skill and the vault parts have no OpenAI words.
- The directory listing: icons, `shortDescription`, support, privacy and terms URLs, and the plugin portal's review.
- The connector's ChatGPT side (`search`/`fetch`, origins, CORS) and a Codex run of the evals.
