#!/usr/bin/env python3
"""Put answers into a rehearsal's answers.json, generate its steps file and run pre-flight: what is still asked, proposed or missing.

    ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/bench/answer_case.py REHEARSAL [KEY=VALUE ...]

The loop after `derive_recipe.py` (which asks only what another rehearsal already answered): the new asks of a new dictionary entry are asked
here until `ready True`. A value `true`/`false` is the text the answers files hold; a group's answer (a list of ask keys) is edited by hand.
Run from the repo's root: an answers file names its files from there. It writes answers.json with `indent=1`, as the derived ones are.
"""
import json
import subprocess
import sys
from pathlib import Path

PORTAL = Path(__file__).resolve().parent.parent
ROOT = PORTAL.parents[3]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    folder = ROOT / "rehearsals" / sys.argv[1]
    answers = json.loads((folder / "answers.json").read_text())
    for kv in sys.argv[2:]:
        key, _, value = kv.partition("=")
        answers[key] = value
    (folder / "answers.json").write_text(json.dumps(answers, ensure_ascii=False, indent=1) + "\n")
    steps = folder / "portal-steps.generated.yaml"
    g = subprocess.run([sys.executable, str(PORTAL / "gen.py"), str(folder / "recipe.yaml"), "--out", str(steps)], capture_output=True, text=True)
    if g.returncode or g.stderr.strip():
        sys.exit("gen.py: " + (g.stderr or g.stdout)[-1500:])
    r = subprocess.run([sys.executable, str(PORTAL / "run.py"), "preflight", "--made-up", "--values", str(folder / "fixture.json"), "--steps", str(steps),
                        "--answers", str(folder / "answers.json")], capture_output=True, text=True, cwd=ROOT)
    try:
        d = json.loads(r.stdout)
    except ValueError:
        sys.exit("pre-flight: " + (r.stdout + r.stderr)[-1500:])
    print("ready", d["ready"], "unsupported", d["unsupported"])
    for q in d["questions"]:
        print("Q", q["key"], "|", q.get("question", "")[:110], "|", q.get("error", ""))
    for p in d["proposals"]:
        print("P", p.get("key"), p.get("value"))
    for f in d["files"]:
        if not f["exists"]:
            print("FILE", f["for"])


if __name__ == "__main__":
    main()
