#!/usr/bin/env python3
"""No English or software word reaches the tecnico. Looks at what they read:

  - the plugin's README, the plugin's description and each skill's description (the app shows these);
  - every sentence a skill has Claude say in Italian («...» in SKILL.md, prova.md, setup);
  - the Italian strings of the scripts whose output Claude gives as written (review.py, route.py, check.py, report.py,
    prova.py, nota.py, intake.py, rules.py, run.py);
  - the user-facing fields of the steps files and the rules tables (question, yours, theirs, refuse, else, why ...);
  - and that the skill's prose never names the first check «pre-flight» (Claude repeats the words it reads), except in
    the table of words it must not say.

Words Italians use every day stay (file, email, PDF, SPID, PEC, online, browser, plugin, server, open source, upload ...); the app's own English labels, which the README
gives in brackets so a tecnico finds the button, are not looked at. What a quoted law or portal label says in its own
words is not looked at either (a label is the portal's).

  ~/.cache/pratica-portal/venv/bin/python -I claude/skills/pratica/portal/bench/test_english.py
"""
import ast
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.dont_write_bytecode = True
import gen  # noqa: E402

ROOT = HERE.parents[4]
PRATICA = ROOT / "claude" / "skills" / "pratica"
PLUGIN = ROOT / "plugin" / "impresa-in-un-minuto"
SKILLS = PLUGIN / "skills"

BANNED = re.compile(
    r"\b(pre-?flight|runner|steps? files?|draft|slots?|pane|bundle|made-up|json|single job|run\.js|check\.js|"
    r"readback|read-back|fillable|folders?|jobs?|errors?|warnings?|blocked|missing|ready|fill|filling|label|"
    r"fields?|check(?!-?list))\b", re.I)
ITALIAN = re.compile(
    r"\b(il|la|le|lo|di|che|per|non|un|una|è|sono|del|della|dei|delle|con|nel|nella|hai|tuo|tua|tu|sul|alla|al|da|"
    r"se|come|ma|più|già|ancora|portale|pratica|ti|ci|puoi|devi|serve|mi|ho|ha|può|tutti|tutte|ogni)\b", re.I)
# The fields of a steps file or a rules table that the tecnico reads (what is checked is only what is in Italian).
USER_KEYS = {"question", "yours", "theirs", "refuse", "else", "why", "how", "choices", "what", "works", "title",
             "options", "message", "hint", "note", "notes", "proposal", "reason"}


def clean(text):
    """The words a person reads: no code spans, no links, no HTML comments."""
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`|https?://\S+", " ", text)
    # the app's own English labels, in brackets after the Italian ones: «Verifica aggiornamenti (Check for updates)»
    return re.sub(r"\([A-Z][A-Za-z ,/'-]*\)", " ", text)


def code_strings(path):
    tree = ast.parse(path.read_text())
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Module)) and n.body
            and ast.get_docstring(n, clean=False) is not None}
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
            yield n.value


def yaml_strings(node, key=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from yaml_strings(v, str(k))
    elif isinstance(node, list):
        for v in node:
            yield from yaml_strings(v, key)
    elif isinstance(node, str) and key in USER_KEYS:
        yield node


def frontmatter_description(path):
    """The skill's description, and ChatGPT's (`metadata: openai-description`, plugin/build.py) after it."""
    m = re.match(r"---\n(.*?)\n---", path.read_text(), re.S)
    said = re.findall(r"^(?:description|  openai-description):\s*(.*)$", m.group(1), re.M) if m else []
    return "\n".join(said)


def main():
    bad = []

    def look(where, text):
        for m in BANNED.finditer(clean(text)):
            bad.append(f"{where}: «{m.group(0)}» in {clean(text)[max(0, m.start() - 40):m.end() + 40]!r}")

    n = 0
    look("plugin README", (PLUGIN / "README.md").read_text())
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    look("plugin description", manifest["description"])
    look("plugin description for ChatGPT", manifest.get("metadata", {}).get("openai", {}).get("description", ""))
    for sk in sorted(SKILLS.glob("*/SKILL.md")):
        if sk.parent.name == "cowork-test":  # the maintainers' own test: a release ships neither it nor its text
            continue
        look(f"{sk.parent.name} description", frontmatter_description(sk))
    for f in [SKILLS / "pratiche" / "SKILL.md", SKILLS / "pratiche" / "prova.md", SKILLS / "setup" / "SKILL.md"]:
        for q in re.findall(r"«([^»]{3,500})»", f.read_text(), re.S):
            look(f"{f.name} (sentence in Italian)", q)
        n += 1
        # Claude repeats the words it reads: the first check is never named «pre-flight» in the prose, only in the table
        # of words it must not say.
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if re.search(r"pre-flight", clean(line), re.I) and "steps file" not in line:
                bad.append(f"{f.name}:{i}: the prose names the first check «pre-flight»: {line.strip()[:90]!r}")
    for f in [PRATICA / "review.py", PRATICA / "portal" / "route.py", PRATICA / "portal" / "rules.py",
              PRATICA / "portal" / "run.py", PRATICA / "intake" / "intake.py",
              SKILLS / "pratiche" / "check.py", SKILLS / "pratiche" / "report.py", SKILLS / "pratiche" / "prova.py",
              SKILLS / "pratiche" / "nota.py"]:
        for s in code_strings(f):
            if re.search(r"catch \(|=>|function ?\(|\bconst \w+ =", s):  # a script the page runs, not words
                continue
            if len(ITALIAN.findall(s)) >= 2 or "«" in s:
                look(f.name, s)
        n += 1
    for f in [*sorted((ROOT / "rehearsals").glob("*/portal-steps*.yaml")),
              *sorted((PRATICA / "portal" / "rules").glob("*.yaml")), *sorted((PRATICA / "portal" / "parts").glob("*.yaml")),
              PRATICA / "portal" / "defects.yaml", *sorted((ROOT / "library" / "rules").glob("*.yaml"))]:
        for s in yaml_strings(gen.load_yaml(f)):
            if len(ITALIAN.findall(s)) >= 2:
                look(f"{f.parent.name}/{f.name}", s)
        n += 1
    seen = set()
    for b in bad:
        k = b.split(": ", 1)[1][:60] if ": " in b else b
        if k in seen:
            continue
        seen.add(k)
        print("FAIL", b[:240])
        if len(seen) >= 60:
            break
    print(f"{n} sources read, {len(bad)} English or software words")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
