#!/usr/bin/env python3
"""build.py's switches, offline: the marked parts each build keeps, the markers it refuses,
and the hand-written plugin both ways (vault: no setup skill and no word of the archive without
it; python_download: off by default, and then no download in the launcher or the texts).

  python3 plugin/test_build.py      (needs PyYAML, as build.py does)
"""

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import build  # noqa: E402
import yaml  # noqa: E402

TEXT = "a\n<!-- vault -->\nb\n<!-- /vault -->\n<!-- no-vault -->\nc\n<!-- /no-vault -->\nd\n"


def refused(text):
    try:
        build.keep_parts(text, True, "t.md")
    except SystemExit:
        return True
    return False


def main():
    assert build.keep_parts(TEXT, True, "t.md") == "a\nb\nd\n"
    assert build.keep_parts(TEXT, False, "t.md") == "a\nc\nd\n"
    for bad in ("<!-- vault -->\nx\n", "x\n<!-- /vault -->\n", "<!-- vault -->\n<!-- no-vault -->\n",
                "<!-- vault -->\nx\n<!-- /no-vault -->\n"):
        assert refused(bad), bad
    assert isinstance(build.vault_default(), bool)
    import pin_marketplace  # the listing people read before installing says what the plugin has
    for vault in (True, False):
        said = pin_marketplace.marketplace("0.1.0", "0" * 40, vault=vault)["plugins"][0]["description"]
        assert ("vault" in said) == vault, said
    # What the app lists, in Italian and under the plugin's name, entry and manifest alike.
    entry = pin_marketplace.marketplace("0.1.0", "0" * 40, vault=False)["plugins"][0]
    manifest = json.loads(build.with_scope((HERE / "impresa-in-un-minuto" / ".claude-plugin" / "plugin.json").read_text(), "plugin.json"))
    for said in (entry, manifest):
        assert said["displayName"] == "Impresa in un minuto", said
        assert build.scope()["copertura"] in said["description"] and "prepares" not in said["description"].lower(), said

    # Each shipped skill's description is Italian: the app shows it, and writes its "Prova nella chat"
    # prompt from it (2026-11-07: an English "Use when … see a demo" gave "show me a demo CILA").
    import re
    english = re.compile(r"\b(the|use|when|asks|wants|show|demo|test with|made-up|set me up|or update|it isn't)\b", re.I)
    for skill in sorted((HERE / "impresa-in-un-minuto" / "skills").iterdir()):
        if skill.name == build.TEST_SKILL:  # never shipped
            continue
        front = (skill / "SKILL.md").read_text().split("---")[1]
        said = next(line for line in front.splitlines() if line.startswith("description:"))
        plain = re.sub(r"«[^»]*»", "", said)  # what the tecnico may type, quoted, is theirs
        assert not english.search(plain), f"{skill.name}: English in its description: {english.search(plain).group(0)!r}"
        # claude.ai keeps 1024 characters of it (2026-11-17: 0.8.1 shipped 1309, its placeholders filled): the
        # text with each sportello alone and with all of them, as a build carries them.
        text = (skill / "SKILL.md").read_text()
        for desks in (["sue"], ["suap"], list(build.SPORTELLO_NAMES)):
            filled = build.with_scope(text, skill.name, desks)
            kept = next(line for line in filled.split("---")[1].splitlines() if line.startswith("description:"))
            assert len(kept[len("description:"):].strip()) <= build.DESCRIPTION_MAX, \
                f"{skill.name} ({'+'.join(desks)}): description over {build.DESCRIPTION_MAX} characters"

    with tempfile.TemporaryDirectory() as tmp:
        for vault in (True, False):
            plugin = Path(tmp) / str(vault)
            shutil.copytree(HERE / "impresa-in-un-minuto", plugin)
            build.select_vault(plugin, vault)
            assert (plugin / "skills" / build.SETUP_SKILL).is_dir() == vault
            for f in plugin.rglob("*.md"):
                text = f.read_text()
                assert not any(build.MARKER.match(line.strip()) for line in text.splitlines()), f
                if not vault:
                    for word in ("pvault", "archivio", "Touch ID", build.SETUP_SKILL):
                        assert word not in text, f"{f.relative_to(plugin)} says {word!r} without the archive"
        # A text naming the archive outside a vault part stops a no-vault build.
        plugin = Path(tmp) / "leak"
        shutil.copytree(HERE / "impresa-in-un-minuto", plugin)
        (plugin / "skills" / "pratiche" / "EXTRA.md").write_text("run pvault status\n")
        try:
            build.select_vault(plugin, False)
        except SystemExit:
            pass
        else:
            raise AssertionError("a no-vault build kept a text that names pvault")

        # A private term stops the build, as a whole word (not inside a hash), and the message
        # gives its line number in the list, never the term.
        plugin = Path(tmp) / "private"
        (plugin / "s").mkdir(parents=True)
        (plugin / "s" / "schema.json").write_text('{"d": "e.g. 908", "sha": "a908b", "cf": "ABCDEF 12G34 H567I"}')
        build.check_private(plugin, ["90", "a9"])  # only inside other words: passes
        for terms, line in ((["x", "908"], 2), (["ABCDEF12G34H567I"], 1)):  # a long one also spaced out
            try:
                build.check_private(plugin, terms)
            except SystemExit as e:
                assert f"s/schema.json: [{line}]" in str(e) and terms[line - 1] not in str(e), e
            else:
                raise AssertionError(f"{terms} not found")

    # python_download: off unless build.yaml says otherwise; its parts nest inside the vault's.
    assert build.switch("python_download") is False, "plugin/build.yaml: python_download ships off"
    both = "a\n<!-- no-vault -->\n<!-- download -->\nb\n<!-- /download -->\n<!-- no-download -->\nc\n<!-- /no-download -->\n<!-- /no-vault -->\n"
    assert build.keep(build.keep_parts(both, False, "t.md"), False, "download", build.DOWNLOAD, "t.md") == "a\nc\n"
    assert build.keep(build.keep_parts(both, False, "t.md"), True, "download", build.DOWNLOAD, "t.md") == "a\nb\n"
    assert build.keep("x\n# <download>\ny\n# </download>\n", False, "download", build.DOWNLOAD_SH, "py") == "x\n"
    with tempfile.TemporaryDirectory() as tmp:
        for download in (True, False):
            plugin = Path(tmp) / str(download)
            shutil.copytree(HERE / "impresa-in-un-minuto", plugin)
            build.select_vault(plugin, False)
            build.select_download(plugin, download)
            py = (plugin / build.LAUNCHER).read_text()
            assert ("python-build-standalone" in py) == download and "# <" not in py
            skill = (plugin / "skills" / "pratiche" / "SKILL.md").read_text()
            assert ("scarico Python" in skill) == download and ("Never install Python yourself" in skill) != download
            for f in plugin.rglob("*.md"):
                assert not any(build.DOWNLOAD.match(line.strip()) for line in f.read_text().splitlines()), f
        # A text that says the plugin downloads Python, outside a download part, stops an off build.
        plugin = Path(tmp) / "leak-dl"
        shutil.copytree(HERE / "impresa-in-un-minuto", plugin)
        (plugin / "skills" / "pratiche" / "EXTRA.md").write_text("it fetches python-build-standalone\n")
        try:
            build.select_download(plugin, False)
        except SystemExit:
            pass
        else:
            raise AssertionError("an off build kept a text about downloading Python")
    # The texts say what the build carries, from build.yaml's sportelli and coverage.yaml's comuni:
    # the sportelli it lists (the SUE's and the SUAP's) of Napoli; another comune, the same texts say so.
    got = build.scope()
    assert got["copertura"] == " e ".join(n for d, n in build.SPORTELLO_NAMES.items() if d in build.sportelli()) \
        + " del Comune di Napoli" and got["comuni"] == "il Comune di Napoli" and got["città"] == "Napoli", got
    assert ("SCIA per aprire" in got["pratiche"]) == ("suap" in build.sportelli()) and "CILA" in got["pratiche"], got
    assert ("titolare di un'impresa" in got["chi"]) == ("suap" in build.sportelli()), got
    both = build.scope({"sue", "suap"}, {"F839": "Napoli", "H501": "Roma"})
    assert (both["copertura"], both["comuni"], both["città"]) == (
        "SUE e SUAP dei Comuni di Napoli e Roma", "i Comuni di Napoli e Roma", "Napoli e Roma"), both
    assert build.scope({"sue"})["chi"] == "un architetto, un geometra o un ingegnere" and "SCIA per aprire" not in build.scope({"sue"})["pratiche"]
    text = "Solo il {{copertura}}.\n<!-- no-suap -->\nIl SUAP no.\n<!-- /no-suap -->\n<!-- suap -->\nIl SUAP sì.\n<!-- /suap -->\n"
    assert build.with_scope(text, "t", {"sue"}) == "Solo il SUE del Comune di Napoli.\nIl SUAP no.\n"
    assert build.with_scope(text, "t", {"sue", "suap"}) == "Solo il SUE e SUAP del Comune di Napoli.\nIl SUAP sì.\n"
    # Every shipped text has its placeholders filled.
    for f in [*(HERE / "impresa-in-un-minuto").rglob("*.md"), HERE / "impresa-in-un-minuto" / ".claude-plugin" / "plugin.json"]:
        left = re.findall(r"\{\{(?:copertura|comuni|città|pratiche|chi)\}\}", build.with_scope(f.read_text(), f.name))
        assert not left, (f, left)
    # A table's name says its sportello (the SUAP's table stays out while it isn't carried).
    assert build.table_sportello(Path("sue-napoli-adempimenti.yaml")) == "sue"
    assert build.table_sportello(Path("suap-napoli.yaml")) == "suap"
    # The target switch: a text's parts for the other agent go with their markers; a text with none stays
    # as it is, so the claude build is the plugin it always was.
    text = "a\n<!-- claude -->\nb\n<!-- /claude -->\n<!-- openai -->\nc\n<!-- /openai -->\nd\n"
    with tempfile.TemporaryDirectory() as tmp:
        for target, want in (("claude", "a\nb\nd\n"), ("openai", "a\nc\nd\n")):
            plugin = Path(tmp) / target
            shutil.copytree(HERE / "impresa-in-un-minuto", plugin)
            (plugin / "skills" / "pratiche" / "EXTRA.md").write_text(text)
            marked = re.compile(r"^<!-- /?(?:claude|openai) -->$", re.M)
            unmarked = [f for f in plugin.rglob("*.md") if f.name != "EXTRA.md" and not marked.search(f.read_text())]
            before = {f: f.read_text() for f in unmarked}
            build.select_target(plugin, target)
            assert (plugin / "skills" / "pratiche" / "EXTRA.md").read_text() == want, target
            assert before == {f: f.read_text() for f in unmarked}, f"{target}: a text with no target marker changed"
        for bad in ("<!-- openai -->\nx\n", "x\n<!-- /claude -->\n", "<!-- claude -->\n<!-- claude -->\n"):
            plugin = Path(tmp) / "bad"
            shutil.rmtree(plugin, ignore_errors=True)
            shutil.copytree(HERE / "impresa-in-un-minuto", plugin)
            (plugin / "skills" / "pratiche" / "EXTRA.md").write_text(bad)
            try:
                build.select_target(plugin, "openai")
            except SystemExit:
                pass
            else:
                raise AssertionError(f"a target marker left open was kept: {bad!r}")
    # No text carries a target marker the build wouldn't understand (a typo like `<!-- open-ai -->` stays in).
    for f in (HERE / "impresa-in-un-minuto").rglob("*.md"):
        assert not re.search(r"^<!-- /?(?:claude|openai)\b(?! -->)", f.read_text(), re.M), f
    # The openai build's words: OpenAI's <skill-dir> for Claude's variable, the assistant as ChatGPT, and a
    # stop on what only Claude's apps have.
    said = build.openai_words('sh "${CLAUDE_SKILL_DIR}/py": Claude compila. claude-plugin, Claudette', "t")
    assert said == 'sh "<skill-dir>/py": ChatGPT compila. claude-plugin, Claudette', said
    for bad in ("usa Claude in Chrome", "dall'app Claude", "(Cowork's sandbox)", "AskUserQuestion", "`tabs_context`",
                "${CLAUDE_PLUGIN_ROOT}", "In Claude disattiva", "Claude Code nel terminale", "the Claude desktop app"):
        try:
            build.openai_words(f"a\n{bad}\n", "t")
        except SystemExit as e:
            assert str(e).startswith("t:2:"), e
        else:
            raise AssertionError(f"a Claude-only name passed: {bad!r}")
    # Every hand-written text, as the openai build keeps it (without the archive, as build.yaml ships it),
    # says nothing only Claude's apps have: the openai build doesn't stop on one, and names no Claude.
    with tempfile.TemporaryDirectory() as tmp:
        plugin = Path(tmp) / "openai"
        shutil.copytree(HERE / "impresa-in-un-minuto", plugin)
        build.select_vault(plugin, False)
        build.select_target(plugin, "openai")
        shutil.rmtree(plugin / "skills" / build.TEST_SKILL)  # as the build does before openai_texts
        build.openai_texts(plugin)
        for f in plugin.rglob("*.md"):
            text = f.read_text()
            assert "CLAUDE_" not in text and not re.search(r"\bClaude\b", text), f
            assert "<!--" not in text or "<!-- download" in text or "<!-- no-download" in text, f
        skill = (plugin / "skills" / "pratiche" / "SKILL.md").read_text()
        assert "`<skill-dir>` is this SKILL.md's directory" in skill, "the openai skill says what <skill-dir> is"
        # ChatGPT fills the portal with driver.mjs (2026-11-21): run.py chatgpt and the driver, never the pane's
        # scripts (check.js, run.js, __pv), which its read-only view can't run; a terminal with no browser checks only.
        prova = (plugin / "skills" / "pratiche" / "prova.md").read_text()
        assert "## 4. The compilation" in skill and "portal/driver.mjs" in skill and "run.py\" chatgpt" in skill, \
            "the openai skill fills through the driver"
        assert "**A check only**" in skill.split("## How you speak")[0], "the openai skill says a terminal checks only"
        steps = skill.split("## 4. The compilation")[1].split("## 7. After they send it")[0]
        for f, said in (("SKILL.md, steps 4-6", steps), ("prova.md", prova)):
            for pane in ("check.js", "run.js", "__pv", "--plain", "preview_text.js", "--after-declarations"):
                assert pane not in said, (f, pane)
        assert "`<page>` is `chatgpt`" in prova
        front = yaml.safe_load(skill.split("---")[1])
        assert set(front) == {"name", "description"} and "ChatGPT compila" in front["description"], front
        readme = (plugin / "README.md").read_text()
        assert "codex plugin marketplace add liammaher/impresa-in-un-minuto" in readme and "Fammi vedere una prova" in readme
    # The claude build keeps every Claude part as it was.
    with tempfile.TemporaryDirectory() as tmp:
        plugin = Path(tmp) / "claude"
        shutil.copytree(HERE / "impresa-in-un-minuto", plugin)
        build.select_target(plugin, "claude")
        skill = (plugin / "skills" / "pratiche" / "SKILL.md").read_text()
        assert "never Claude in Chrome" in skill and "<skill-dir>" not in skill and "driver.mjs" not in skill and "ChatGPT" not in skill
        assert "## 4. The compilation" in skill and "Entra con il tuo SPID" in skill
        front = yaml.safe_load(skill.split("---")[1])
        assert set(front) == {"name", "description"} and "Claude compila" in front["description"], front
        raw = (HERE / "impresa-in-un-minuto" / "skills" / "pratiche" / "SKILL.md").read_text().split("---", 2)[1]
        assert skill.split("---", 2)[1] == re.sub(r"\nmetadata:\n  openai-description: .*\n", "\n", raw), \
            "the claude build's frontmatter is the hand-written one, less ChatGPT's description"
    # OpenAI's manifest: the portable fields of the hand-written one, nothing of Claude's.
    manifest = json.loads(build.with_scope((HERE / "impresa-in-un-minuto" / ".claude-plugin" / "plugin.json").read_text(), "plugin.json"))
    out = build.openai_manifest(manifest)
    assert out["$schema"] == build.OPENAI_PLUGIN_SCHEMA and out["name"] == manifest["name"] and out["version"] == manifest["version"], out
    # Only the keys the Agent Plugins schema allows at the root (it has additionalProperties: false).
    assert set(out) <= {"$schema", "name", "version", "description", "author", "homepage", "repository", "license",
                        "keywords", "extensions"}, out
    assert "displayName" not in out, "displayName is Claude's; OpenAI's goes under extensions.com.openai.interface"
    openai = out["extensions"]["com.openai"]
    assert "Claude" not in out["description"] and "ChatGPT compila" in out["description"], out["description"]
    assert openai["requires_local_executor"] is True, "the runner's scripts need the desktop app: desktop only"
    face = openai["interface"]
    assert face["displayName"] == manifest["displayName"] and face["longDescription"] == out["description"] == build.openai_words(manifest["description"], "t") \
        and face["developerName"] == manifest["author"]["name"] and face["websiteURL"] == manifest["homepage"], face
    assert face["category"] in {"Productivity", "Creativity", "Developer Tools", "Business & Operations", "Data & Analytics",
                                "Communication", "Education & Research", "Security", "Finance", "Healthcare", "Travel",
                                "Entertainment", "Other"}, face["category"]
    assert len(face["defaultPrompt"]) <= 128 and "\n" not in face["defaultPrompt"], face["defaultPrompt"]
    assert set(face) <= {"displayName", "longDescription", "developerName", "category", "defaultPrompt", "websiteURL"}, \
        "a listing text the hand-written manifest doesn't hold would escape test_english and test_voice"
    for bad in ({**manifest, "name": "Impresa_In_Un_Minuto"}, {**manifest, "name": "a" * 65},
                {**manifest, "metadata": {"openai": {"description": "x" * 1025}}}, {**manifest, "displayName": "x" * 81}):
        try:
            build.openai_manifest(bad)
        except SystemExit:
            pass
        else:
            raise AssertionError(f"OpenAI's limits not held: {str(bad)[:60]}")
    # The connector, as each target's config names it.
    claude = build.connector_config("claude", "https://example.org/mcp")
    assert claude == {"mcpServers": {"impresa-in-un-minuto": {"type": "http", "url": "https://example.org/mcp"}}}, claude
    # The claude build's .mcp.json is the same bytes the build wrote before the target existed.
    assert build.as_json(claude) == build.as_json(
        {"mcpServers": {"impresa-in-un-minuto": {"type": "http", "url": "https://example.org/mcp"}}})
    for missing in ({}, {"version": "1"}, {"name": "ok-name"}):  # a manifest short of fields is refused, not a traceback
        try:
            build.openai_manifest(missing)
        except SystemExit:
            pass
        except KeyError:
            raise AssertionError(f"openai_manifest({missing}) raised KeyError")
    oai = build.connector_config("openai", "https://example.org/mcp")
    assert oai["mcpServers"]["impresa-in-un-minuto"] == {"type": "streamable-http", "url": "https://example.org/mcp"} \
        and oai["$schema"] == build.OPENAI_MCP_SCHEMA, oai
    print("ok: build.py's vault, python_download, target and sportelli switches, and private terms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
