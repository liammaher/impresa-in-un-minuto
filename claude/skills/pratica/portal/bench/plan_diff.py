#!/usr/bin/env python3
"""What a dictionary, gen.py or recipe change does to each case: its fill plan before and after.

    ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/bench/plan_diff.py [--since REF] [rehearsal ...]

A steps file's diff is noisy (ids that go by label, conditions reworded); a case's plan is what
the run types and ticks for its answers (run.py plan, on the P6 fixture). For every answers file
of the rehearsals whose steps file changed since REF (default HEAD), or those named, this prints
the plan's lines that differ, and a case that is new or no longer plans. A new question answered
as the case did before leaves its plan unchanged: that is how existing cases keep their recorded
runs (2026-11-01: 119 cases, only a box those forms don't have dropped). No browser, no network.

Each rehearsal is planned on its own fixture, the one its recorded runs name, or (SUAP) the pizzeria's: see fixture_for. A case that plans on
neither side is counted as «NOT compared» in the last line (it used to pass silently).

A NEW answers file prints «new», and «new (no plan: ...)» when it does not plan on its fixture: that is a real stop of the case (before round 25 it
was the P6 fixture's refusal of every SUAP recipe, and was ignored). A whole run takes about 9 minutes.

The steps files are built, never committed (steps.lock holds their hashes): now's come from the
recipes as they are, REF's from REF's own gen.py in a temporary worktree (a REF from before
2026-11-04 still has them in git). A rehearsal changed when its steps file's hash differs from
REF's steps.lock line.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
RUN = HERE.parent / "run.py"
FIXTURE = "rehearsals/cila-fittizia/fixture-p6.json"
sys.path.insert(0, str(HERE.parent))
sys.dont_write_bytecode = True
import gen  # noqa: E402


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


SUAP_FIXTURE = "rehearsals/pizzeria-fittizia/fixture.json"  # the made-up ditta individuale every SUAP rehearsal's runs borrowed or had


def fixture_for(name):
    """The values a rehearsal's cases are planned on: its own fixture.json, else the `values` a recorded run of it names
    (bench/rerun.py --record --values), else a SUAP rehearsal's the pizzeria's, else the CILA architect's P6. Round 25: on P6 every SUAP
    recipe stops first (\u00abPer ora per una ditta individuale...\u00bb), so each case printed «no plan» before and after and the tool reported
    «0 cases plan differently» for the SUAP without comparing anything."""
    d = ROOT / "rehearsals" / name
    if (d / "fixture.json").is_file():
        return str((d / "fixture.json").relative_to(ROOT))
    runs = d / "runs.json"
    for r in json.loads(runs.read_text()) if runs.is_file() else []:
        if r.get("values") and (ROOT / r["values"]).is_file():
            return r["values"]
    try:
        if gen.resolved(gen.load_yaml(d / "recipe.yaml")).get("sportello") == "suap":
            return SUAP_FIXTURE
    except Exception:  # noqa: BLE001  (a recipe gen.py refuses is reported elsewhere)
        pass
    return FIXTURE


def plan(steps, answers, fixture=FIXTURE):
    """run.py plan's lines, or its error as one line."""
    r = subprocess.run([sys.executable, str(RUN), "plan", "--steps", steps, "--answers", answers,
                        "--values", fixture, "--made-up"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else [f"(no plan: {(r.stderr or r.stdout).strip().splitlines()[-1:]})"]


def now_steps():
    """{rehearsal: its steps file's text, from its recipe now} (a refused recipe is left out)."""
    out = {}
    for d in sorted(p for p in (ROOT / "rehearsals").iterdir() if (p / "recipe.yaml").is_file()):
        try:
            out[d.name] = gen.dump(gen.generate(gen.load_yaml(d / "recipe.yaml")))
        except gen.GenError as e:
            print(f"== {d.name}: gen.py refuses it now: {e}")
    return out


def then_steps(ref, names, tmp):
    """{rehearsal: its steps file's text at REF}: from git where REF has them, else built by REF's
    regen.py in a temporary worktree."""
    out, build = {}, []
    for name in names:
        old = git("show", f"{ref}:rehearsals/{name}/{gen.STEPS}")
        if old.returncode == 0:
            out[name] = old.stdout
        elif git("cat-file", "-e", f"{ref}:rehearsals/{name}/recipe.yaml").returncode == 0:
            build.append(name)
    if build:
        tree = Path(tmp, "ref")
        if git("worktree", "add", "--detach", str(tree), ref).returncode:
            sys.exit(f"can't check out {ref}")
        try:
            subprocess.run([sys.executable, str(tree / HERE.relative_to(ROOT) / "regen.py"), *build],
                           cwd=tree, capture_output=True, text=True)
            for name in build:
                f = tree / "rehearsals" / name / gen.STEPS
                if f.is_file():
                    out[name] = f.read_text()
        finally:
            git("worktree", "remove", "--force", str(tree))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default="HEAD")
    ap.add_argument("rehearsals", nargs="*")
    a = ap.parse_args()
    now = now_steps()
    if a.rehearsals:
        names = a.rehearsals
    else:
        lock = git("show", f"{a.since}:rehearsals/{gen.LOCK.name}")
        if lock.returncode == 0:
            with tempfile.NamedTemporaryFile("w", suffix=".lock") as f:
                f.write(lock.stdout)
                f.flush()
                then_lock = gen.read_lock(Path(f.name))
            names = sorted(n for n, text in now.items() if gen.sha256(text) != then_lock.get(n))
        else:  # a REF from before the lock: its committed steps files
            names = sorted(n for n, text in now.items() if git("show", f"{a.since}:rehearsals/{n}/{gen.STEPS}").stdout != text)
    changed = blind = 0
    with tempfile.TemporaryDirectory() as tmp:
        then = then_steps(a.since, names, tmp)
        for name in names:
            steps, old_steps = Path(tmp, f"{name}.yaml"), Path(tmp, f"{name}.old.yaml")
            steps.write_text(now.get(name, ""))
            old_steps.write_text(then.get(name, ""))
            for answers in sorted((ROOT / "rehearsals" / name).glob("answers*.json")):
                rel = os.path.relpath(answers, ROOT)
                was = git("show", f"{a.since}:{rel}")
                fx = fixture_for(name)
                after = plan(str(steps), rel, fx)
                if was.returncode != 0 or name not in then:
                    print(f"== {rel}: new" + ("" if not after[0].startswith("(no plan") else f" {after[0]}"))
                    continue
                old_answers = Path(tmp, "answers.json")
                old_answers.write_text(was.stdout)
                before = plan(str(old_steps), str(old_answers), fx)
                if before[0].startswith("(no plan") and after[0].startswith("(no plan"):
                    blind += 1  # planned on neither side: nothing was compared
                    print(f"== {rel}: no plan before or after on {fx} {after[0]}")
                    continue
                if before != after:
                    changed += 1
                    gone = [x for x in before if x not in after]
                    came = [x for x in after if x not in before]
                    print(f"== {rel}")
                    print("\n".join([f"  - {x}" for x in gone] + [f"  + {x}" for x in came]))
    print(f"{changed} case(s) plan differently since {a.since}" + (f"; {blind} could not be planned on either side, so were NOT compared" if blind else ""))


if __name__ == "__main__":
    main()
