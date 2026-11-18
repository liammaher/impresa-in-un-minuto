#!/usr/bin/env python3
"""The SUAP crawls that still have no rehearsal, and a sibling to derive each from.

    ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/bench/remaining.py [--json]

The scoreboard's "fillable" counts the same-fingerprint copies in catalogue/F839/same.json (the stage 2 sweep), so it says
nothing about what is left: this lists the crawls of their own (not an alias) whose sections the dictionary covers and that
no recipe names, grouped by sector, and for each the filled rehearsal of the same operation in the nearest sector number
(a hint: check it is the same kind of business before bench/derive_recipe.py NEW TEMPLATE CRAWL). A `suap-common-*` crawl
has no sector in its name and gets no hint. It reads scoreboard.build(), so it takes about three minutes (2026-11-18: 58
left after round 14, 48 after round 15; the by-hand count in the task was the same).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.dont_write_bytecode = True
import scoreboard  # noqa: E402

CRAWL = re.compile(r"^suap-(\d{3})-(.+)$")


def remaining():
    """[(crawl, hint rehearsal or None)] for every own SUAP crawl that is fillable and that no recipe names."""
    _, _, reh, status = scoreboard.build()
    named = {v["crawl"] for v in reh.values() if v["crawl"]}
    left = sorted(n for n, s in status.items()
                  if s["sportello"] == "suap" and not s["alias"] and not s["missing"] and n not in named)
    filled = [(name, m) for name, v in reh.items() if v["run"] and v["crawl"] and (m := CRAWL.match(v["crawl"]))]
    out = []
    for crawl in left:
        m, best = CRAWL.match(crawl), None
        if m:
            same = [(abs(int(k.group(1)) - int(m.group(1))), name) for name, k in filled if k.group(2) == m.group(2)]
            best = min(same)[1] if same else None
        out.append((crawl, best))
    return out


if __name__ == "__main__":
    rows = remaining()
    if "--json" in sys.argv:
        print(json.dumps([{"crawl": c, "template": t} for c, t in rows], indent=1))
    else:
        print(f"{len(rows)} own SUAP crawls with no rehearsal")
        for crawl, template in rows:
            print(f"{crawl}  <-  {template or 'no sibling of this operation: a recipe by hand'}")
