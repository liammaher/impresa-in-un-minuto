#!/usr/bin/env python3
"""The SUAP pratiche still short of fillable, by how many dictionary sections each lacks, and the sections by how many of them need it.

    ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/bench/gaps.py [--max N] [--sue]

The same count as scoreboard.py's «cheapest gaps» line, but naming the pratiche and sections (about a minute, where `scoreboard.py` takes
eight): the list round 7 (2026-11-15) worked from. Write the sections that top the second list first: each also fixes every other pratica that has it.
"""
import argparse
import collections
import sys
from pathlib import Path

PORTAL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PORTAL))
sys.dont_write_bytecode = True
import catalogue as cat  # noqa: E402
import gen  # noqa: E402
import scoreboard as sb  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--max", type=int, default=2, help="list the pratiche short at most this many sections (default 2)")
    ap.add_argument("--sue", action="store_true", help="the SUE's, not the SUAP's")
    a = ap.parse_args()
    stored = cat.crawls()
    alias = cat.json.loads(cat.SAME.read_text())["same"] if cat.SAME.exists() else {}
    status = sb.pratica_status(stored, alias, gen.load_yaml(PORTAL / "dictionary" / "fnsuap.yaml"))
    short = {n: s["missing"] for n, s in status.items() if s["sportello"] == ("sue" if a.sue else "suap") and s["missing"]}
    print(f"{len(short)} pratiche short at least one section; those short at most {a.max}:")
    for n, ms in sorted(short.items(), key=lambda kv: (len(kv[1]), kv[0])):
        if len(ms) <= a.max:
            print(f"  {len(ms)} {n}: {ms}")
    near = collections.Counter(m for ms in short.values() if len(ms) <= a.max for m in ms)
    every = collections.Counter(m for ms in short.values() for m in ms)
    print("\nsections (pratiche that are near / pratiche short of it in all):")
    for m, k in near.most_common():
        print(f"  {k} / {every[m]}  {m}")


if __name__ == "__main__":
    main()
