#!/usr/bin/env python3
"""Where a portal run buys the most: the SUAP's own crawls against its same-fingerprint copies.

    ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/leverage.py [--json]

The scoreboard's "mapped" for the SUAP counts every pair of the wizard whose form is known, 1,148 on 2026-11-20: 309 crawls of
their own and 839 copies (`catalogue/F839/same.json`, the stage 2 sweep: the pair's draft showed the same sections, by
fingerprint, as a crawl we hold). The copies point at 55 of the own crawls, so what a run proves is counted per own crawl and per
section, never per pair: running a copy fills the sections of its canonical again. This module counts:

  - own crawls, those with a filled run, and the copies they stand for;
  - the canonical crawls (what the copies point at) with no filled run, by the copies riding on each: the runs that matter most;
  - the distinct sections (by fingerprint) a filled run has exercised, and the crawls that still hold one nobody exercised,
    split into those the dictionary fills (a run away) and those it doesn't (dictionary work first, a run after).

A fingerprint is what a section shows before any choice (ids, kinds, labels): it says nothing about the boxes a choice reveals
(347 section fingerprints have such choices on 2026-11-20, 215 of them in run crawls, and which options a run took is not counted
for the SUAP as it is for the SUE), so "exercised" is a floor on the first screen, not a claim about every branch.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import catalogue as cat  # noqa: E402


def fingerprints(crawl):
    """The fingerprints of a crawl's sections that a run fills (a declaration the person ticks, an error and a choice screen aren't)."""
    return {s.get("fingerprint") for s in crawl["sections"] if not (s.get("skipped") or s.get("error") or s.get("scelta"))}


def compute(stored, alias, status, ran):
    """stored: name -> crawl; alias: copy -> canonical name; status: name -> {"missing": [...]} (scoreboard.pratica_status);
    ran: the crawls some filled run was generated from."""
    suap = {n: c for n, c in stored.items() if cat.sportello(n) == "suap"}
    fillable = {n for n in suap if not (status.get(n) or {}).get("missing")}
    canon = collections.Counter(t for t in alias.values() if t in suap)
    exercised = set().union(*(fingerprints(suap[n]) for n in ran if n in suap)) if ran else set()
    every = set().union(*(fingerprints(c) for c in suap.values())) if suap else set()
    unrun = sorted(((n, k) for n, k in canon.items() if n not in ran), key=lambda nk: (-nk[1], nk[0]))
    holding = {n for n in fillable if n not in ran and fingerprints(suap[n]) - exercised}
    # The fewest fillable crawls whose runs would exercise every section a run can reach (greedy: a floor on the work, not a plan).
    left, runs = {f for n in holding for f in fingerprints(suap[n])} - exercised, []
    while left:
        n = max(sorted(holding), key=lambda k: len(fingerprints(suap[k]) & left))
        gain = fingerprints(suap[n]) & left
        if not gain:
            break
        runs.append((n, len(gain)))
        left -= gain
    return {
        "own": len(suap), "own_run": len([n for n in suap if n in ran]), "own_fillable": len(fillable),
        "copies": len(alias), "canonical": len(canon), "canonical_run": len([n for n in canon if n in ran]),
        "riding_unrun": sum(k for _, k in unrun), "unrun_canonical": unrun,
        "sections": len(every), "sections_exercised": len(every & exercised),
        "unrun_fillable": len([n for n in fillable if n not in ran]), "unrun_short": len([n for n in suap if n not in ran and n not in fillable]),
        "fillable_holding_new_sections": len(holding), "runs_to_exercise_all": runs,
        "sections_only_in_short_crawls": len(every - exercised - {f for n in fillable for f in fingerprints(suap[n])}),
    }


def lines(d):
    """The scoreboard's account of the SUAP count, in the words of this module's docstring."""
    return [
        f"SUAP, by what the count is made of: {d['own']} crawls of their own ({d['own_run']} with a filled run, {d['own_fillable']} fillable) and "
        f"{d['copies']} same-fingerprint copies of {d['canonical']} of them ({d['canonical_run']} of those run; {d['riding_unrun']} copies ride on one that isn't). "
        f"A copy is proved by its canonical's run, so \"run\" above is out of {d['own']}, not of the mapped count.",
        f"SUAP sections (by fingerprint, what each shows before any choice): {d['sections_exercised']} of {d['sections']} exercised by a filled run; "
        f"{d['fillable_holding_new_sections']} fillable crawls with no run still hold a new one ({len(d['runs_to_exercise_all'])} runs would cover them all), "
        f"and {d['sections_only_in_short_crawls']} appear only in crawls the dictionary can't fill yet.",
    ]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    import scoreboard as sb  # the CLI only: the scoreboard imports this module
    stored = cat.crawls()
    alias = json.loads(cat.SAME.read_text())["same"] if cat.SAME.exists() else {}
    _, _, reh, status = sb.build()
    ran = {v["crawl"] for v in reh.values() if v["run"] and v["crawl"]}
    d = compute(stored, alias, status, ran)
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=1))
        return
    print("\n".join(lines(d)))
    print("\nCanonical crawls with no filled run, by the copies riding on each:")
    for n, k in d["unrun_canonical"]:
        print(f"  {k:3d}  {n}  ({'fillable' if not status[n]['missing'] else str(len(status[n]['missing'])) + ' dictionary gaps'})")
    print("\nFillable crawls to run so that every reachable section is exercised (greedy; sections each adds):")
    for n, g in d["runs_to_exercise_all"]:
        print(f"  {g:3d}  {n}")


if __name__ == "__main__":
    main()
