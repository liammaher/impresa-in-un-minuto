#!/usr/bin/env python3
"""Does the dictionary fill a crawled section, and if not, what is unaccounted for?

    ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/bench/section_check.py CRAWL::SECTION [...]
    ... --dump CRAWL::SECTION      the section's boxes and what each choice opens (label, kind, max, options), to write its entry from

CRAWL is a stored crawl's name (catalogue/F839/sections/CRAWL.json, or an alias of `same.json`), SECTION the section's name in it; a section that
is `same_as` another is read there. `check` prints one line per dictionary entry that matches the section's name (the first without problems wins
in gen.py, so an OK after some BAD is a pass): the problems are gen.py's own («no text labelled ...», «... is in no dictionary entry»).
It is the quick loop before `gen.py` and a rehearsal (round 7, 2026-11-15: 19 sections written this way).
"""
import argparse
import json
import sys
from pathlib import Path

PORTAL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PORTAL))
sys.dont_write_bytecode = True
import catalogue as cat  # noqa: E402
import gen  # noqa: E402


def load(spec):
    crawl, _, name = spec.partition("::")
    stored = cat.crawls()
    alias = json.loads(cat.SAME.read_text())["same"] if cat.SAME.exists() else {}
    c = stored.get(crawl) or stored[alias[crawl]]
    s = next(x for x in c["sections"] if x["section"] == name)
    r = cat.resolve(s["same_as"], stored) if s.get("same_as") else s
    return {**r, "section": name}


def check(spec):
    sec = load(spec)
    d = gen.load_yaml(PORTAL / "dictionary" / "fnsuap.yaml")
    entries = list(gen.dictionary_entries(d["sections"], sec["section"]))
    if not entries:
        print("NO ENTRY", sec["section"])
        return
    for entry, as_name in entries:
        _, problems, _ = gen.fill(entry, as_name, sec, {}, sec["section"])
        print("OK " if not problems else "BAD", sec["section"][:60], problems[:6])


def dump(spec):
    sec = load(spec)
    print("##", spec)
    for f in sec.get("fields", []):
        print("  F", f["kind"], "|", f.get("label"), "|", f.get("max", ""), f.get("context", ""), "opts=%s" % f["options"] if f.get("options") else "")
    for b in sec.get("branches", []):
        print("  B", b["choice"][:80], "->", [(x["kind"], x.get("label"), x.get("max", "")) for x in b.get("reveals", [])], "plus" if b.get("plus") else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("specs", nargs="+", metavar="CRAWL::SECTION")
    ap.add_argument("--dump", action="store_true")
    a = ap.parse_args()
    for spec in a.specs:
        (dump if a.dump else check)(spec)


if __name__ == "__main__":
    main()
