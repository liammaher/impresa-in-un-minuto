#!/usr/bin/env python3
"""leverage.py offline: the SUAP count, taken apart (2026-11-20, when "246 run" was read against 1,119 fillable).

  ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/bench/test_leverage.py

No browser, vault or network. The counts move with every round, so what is held is how they relate to each other: copies are
pointed at canonical crawls that exist, a copy is never counted as a crawl of its own, a canonical's run is what proves its
copies, and the crawls to run are fillable ones that hold a section no run has exercised.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.dont_write_bytecode = True
import catalogue as cat  # noqa: E402
import leverage  # noqa: E402
import scoreboard as sb  # noqa: E402

results = []


def case(name):
    def deco(fn):
        try:
            fn()
            print(f"ok    {name}")
            results.append(True)
        except Exception as e:  # noqa: BLE001
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
            results.append(False)
    return deco


stored = cat.crawls()
alias = json.loads(cat.SAME.read_text())["same"]
_, _, reh, status = sb.build()
ran = {v["crawl"] for v in reh.values() if v["run"] and v["crawl"]}
d = leverage.compute(stored, alias, status, ran)


@case("every copy points at a crawl of its own, and no copy is also a crawl")
def _():
    assert all(t in stored for t in alias.values()), [t for t in alias.values() if t not in stored][:3]
    assert not (set(alias) & set(stored)), sorted(set(alias) & set(stored))[:3]
    assert d["copies"] == len(alias)


@case("the own crawls, the ones with a run and the canonical ones add up")
def _():
    assert d["own_run"] <= d["own"] and d["own_fillable"] <= d["own"]
    assert d["canonical_run"] + len(d["unrun_canonical"]) == d["canonical"], d
    assert d["riding_unrun"] == sum(k for _, k in d["unrun_canonical"]) <= d["copies"]
    ranked = [k for _, k in d["unrun_canonical"]]
    assert ranked == sorted(ranked, reverse=True), "the canonicals with no run are listed by the copies they carry"


@case("the crawls to run are fillable, have no run, and each adds a section no run has exercised")
def _():
    seen = set().union(*(leverage.fingerprints(stored[n]) for n in ran if n in stored))
    for name, gain in d["runs_to_exercise_all"]:
        assert not status[name]["missing"] and name not in ran, name
        assert gain >= 1 and leverage.fingerprints(stored[name]) - seen, name
        seen |= leverage.fingerprints(stored[name])


@case("a crawl's declarations, errors and choice screens are not sections a run exercises")
def _():
    crawl = {"sections": [{"section": "a", "fingerprint": "1"}, {"section": "b", "fingerprint": "2", "skipped": "the person's declarations"},
                          {"section": "c", "fingerprint": "3", "error": "x"}, {"section": "d", "fingerprint": "4", "scelta": True}]}
    assert leverage.fingerprints(crawl) == {"1"}


@case("the scoreboard says what its SUAP count is made of")
def _():
    text = "\n".join(leverage.lines(d))
    assert f"{d['own']} crawls of their own" in text and f"{d['copies']} same-fingerprint copies" in text
    assert "run\" above is out of" in text
    assert "SUAP, by what the count is made of" in sb.render("2026-01-01")


print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
