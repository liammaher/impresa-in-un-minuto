# The plugin on OpenAI (Codex, the ChatGPT desktop app)

Status: started 2026-11-20. Claude and Cowork stay the customer path (`packaging.md`); this is a second build target for
people who use Codex or the ChatGPT desktop app. Nothing here changes what a Claude build ships: `plugin/build.py
--target claude` (the default) is byte-identical to the build before the target existed.

## What exists

- `plugin/build.py --target openai` (out: `plugin/dist/openai/`): a root `plugin.json` (Agent Plugins 1.0.0, the
  portable fields of the hand-written Claude manifest, so name and version have one source) instead of
  `.claude-plugin/`. Under `extensions.com.openai` it has `requires_local_executor: true` (the runner's scripts
  run on the computer, so ChatGPT on the web and on phones must not offer it) and an `interface` made of the
  manifest's own texts: display name, long description, developer, website, plus a category and the Prova as
  the starter prompt. It has no `shortDescription` (the portable format derives one), and no icons or
  support, privacy or terms URLs, which the public directory requires; with `--connector URL`, `mcp.json` (`streamable-http`) instead of `.mcp.json`; the texts'
  `<!-- openai -->` parts kept and their `<!-- claude -->` parts dropped (no text has either marker yet).
- It prints how many `${CLAUDE_SKILL_DIR}` uses are left in the texts: OpenAI's docs name no equivalent for skills.

## What is not known (the spike; run it before the skill text is split)

Read from developers.openai.com/plugins on 2026-11-20; none of these is stated there.

1. How a skill refers to its own folder (what replaces `${CLAUDE_SKILL_DIR}`), and whether the agent learns the path.
2. Which surfaces run shell and Python: Codex CLI, Codex in the desktop app, the ChatGPT desktop app. A headed browser?
3. The browser backend for `portal.py` (the plan's Phase 2): `pip install playwright` with the person's own Chrome
   (`channel="chrome"`, no browser download), Playwright's Chromium, or a stdlib CDP client against a Chrome started
   with `--remote-debugging-port`. The least installing one that works wins; a download is the person's call, never silent.
4. Whether the desktop app reads `.claude-plugin/plugin.json` as a fallback (the docs say only that it reads
   `.claude-plugin/marketplace.json` as a legacy-compatible marketplace).

How: hand-copy `plugin/dist/openai/impresa-in-un-minuto` as a local marketplace (`.agents/plugins/marketplace.json`,
`codex plugin marketplace add`), then try the Prova («fammi vedere una prova») and `sh <skill>/py portal/run.py preflight`.
The Codex CLI installed on the maintainer's machine on 2026-11-20 did not start (its vendor binary was missing), so
this has not been run yet.

If 1 or 2 fail, the openai target is questions-only: the connector and the coverage list, no filling.

## What the target does not do yet

- `portal.py` (the adapter that opens a local browser, runs `inpage.js`, writes the files `review.py` reads).
- The split texts (`SKILL.md`, `prova.md`, the README, `report.py`'s `dove`, the Prova card).
- Publishing: a `plugin-openai` branch, `.agents/plugins/marketplace.json`, the release workflow.
- The connector's ChatGPT side (`search`/`fetch`, origins, CORS) and a Codex run of the evals.
