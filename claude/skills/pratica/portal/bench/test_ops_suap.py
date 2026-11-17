#!/usr/bin/env python3
"""`catalogue.py ops suap` offline: the batch leaves out what is known, on the real catalogue.

  ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/bench/test_ops_suap.py

No browser, vault or network. The default batch skips a pair already stored (by name) or recorded `same` in
same.json, turns one whose operation path another sector crawled into a fingerprint check `like` that crawl,
and crawls the rest in full; `--all`, `--sectors` with it, `--common` and `--combo` are as they were.
"""
import argparse
import collections
import contextlib
import io
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.dont_write_bytecode = True
import catalogue  # noqa: E402

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


def ops(**kw):
    """catalogue.cmd_ops with these options: (ops, stderr text)."""
    a = dict(sportello="suap", sectors=None, common=False, all=False, combo=None, scelta=None, combo_scelta=None)
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        out = catalogue.cmd_ops(argparse.Namespace(**{**a, **kw}))
    return out, err.getvalue()


WIZ = json.loads((catalogue.CAT / "suap-wizard.json").read_text())
HAVE = {p.stem for p in catalogue.SECTIONS.glob("*.json")}
PAIRS = sum(len(s["operations"]) for s in WIZ["sectors"])
SAME = json.loads(catalogue.SAME.read_text()) if catalogue.SAME.exists() else {}
default, summary = ops()
everything, _ = ops(all=True)


def counts(text):
    """The summary's numbers, in its order: pairs, stored, same.json, checks, full, different, no-crawl paths."""
    m = re.fullmatch(r"suap: (\d+) pairs; skipped (\d+) stored \+ (\d+) in same\.json; (\d+) checks, (\d+) full crawls "
                     r"\((\d+) listed `different`\); (\d+) distinct paths with no stored crawl\n", text)
    assert m, text
    return [int(x) for x in m.groups()]


@case("the summary's counts reconcile: skipped + checks + full = pairs")
def _():
    pairs, stored, same, checks, full, differ, nopath = counts(summary)
    assert pairs == PAIRS == len(everything), (pairs, PAIRS, len(everything))
    assert stored + same + checks + full == pairs
    assert checks == sum(1 for o in default if o.get("check")) and full == sum(1 for o in default if not o.get("check"))
    assert len(default) == checks + full
    assert stored == sum(1 for o in everything if o["name"] in HAVE), stored
    assert differ <= full


@case("every `like` names a stored crawl, a single-operation one of the same path")
def _():
    paths = catalogue.stored_paths()
    for o in default:
        if not o.get("check"):
            assert "like" not in o, o["name"]
            continue
        assert o["like"] in HAVE, o
        assert o["like"] in paths[o["path"]], (o["name"], o["like"])  # not a combination, not another operation
        assert o["name"] not in HAVE and o["like"] != o["name"]


@case("nothing stored is emitted again; a path with no crawl is a full crawl, one with a crawl a check")
def _():
    paths = catalogue.stored_paths()
    same = set(SAME.get("same", {}))
    for o in default:
        assert o["name"] not in HAVE and o["name"] not in same, o["name"]
        assert bool(o.get("check")) == (o["path"] in paths and o["name"] not in SAME.get("different", {})), o["name"]
    assert len({o["name"] for o in default}) == len(default)
    nopath = {o["path"] for o in default if o["path"] not in paths}
    assert counts(summary)[6] == len(nopath)


@case("a combination or a variant named in prose is no stand-in for a path")
def _():
    paths = catalogue.stored_paths()
    stored = collections.Counter(n for names in paths.values() for n in names)
    for name in HAVE:
        if name.startswith("suap-"):
            c = json.loads((catalogue.SECTIONS / f"{name}.json").read_text())
            if c.get("also") or "operations in one pratica" in c.get("pratica", ""):
                assert name not in stored, name


@case("same.json: an entry `same` is skipped, one `different` is a full crawl (checked on a temporary same.json)")
def _():
    some = [o for o in default if o.get("check")][:2]
    old = catalogue.SAME
    tmp = Path(__import__("tempfile").mkdtemp()) / "same.json"
    tmp.write_text(json.dumps({"same": {some[0]["name"]: some[0]["like"]},
                               "different": {some[1]["name"]: {"like": some[1]["like"], "differences": ["changed: x"]}}}))
    catalogue.SAME = tmp
    try:
        out, text = ops()
    finally:
        catalogue.SAME = old
    names = {o["name"]: o for o in out}
    assert some[0]["name"] not in names
    assert some[1]["name"] in names and not names[some[1]["name"]].get("check") and "like" not in names[some[1]["name"]]
    pairs, stored, same, checks, full, differ, _ = counts(text)
    assert same == 1 and differ == 1 and stored + same + checks + full == pairs


@case("--all is every pair, none skipped and none a check, in the old names")
def _():
    assert len(everything) == PAIRS and not any(o.get("check") or "like" in o for o in everything)
    s = WIZ["sectors"]
    want = [f"suap-{i:03d}-" + catalogue.slug(o.split(": ", 1)[1].split(" › ")[-1], 50) for i, x in enumerate(s) for o in x["operations"]]
    got = [re.sub(r"-\d+$", "", o["name"]) if o["name"] not in want else o["name"] for o in everything]
    assert got == want
    assert [o["path"] for o in everything] == [o for x in s for o in x["operations"]]
    assert all(set(o) == {"name", "sector", "sector_nth", "path"} for o in everything)


@case("--sectors with --all is those sectors' pairs; without --all it is a subset of the default batch")
def _():
    sub, text = ops(all=True, sectors="3,7")
    want = sum(len(WIZ["sectors"][i]["operations"]) for i in (3, 7))
    assert len(sub) == want and text == ""
    part, _t = ops(sectors="3,7")
    full_names = {o["name"]: o for o in default}
    assert all(full_names.get(o["name"]) == o for o in part)
    assert counts(_t)[0] == want


@case("--common and --combo are as before: no skipping, no checks, no summary")
def _():
    com, text = ops(common=True, sectors="0")
    assert len(com) == len(WIZ["common"]) and text == "" and not any("check" in o for o in com)
    assert all(o["name"].startswith("suap-common-") for o in com)
    # a combination of the sector 11's (acconciatore) opening with the PIN 2, by the start of the leaf labels
    i = next(k for k, s in enumerate(WIZ["sectors"]) if any("Aprire l'attività di acconciatore" in o for o in s["operations"]))
    out, text = ops(combo=[["x-combo", str(i), "Aprire l'attività di acconciatore", "PIN 2 - "]])
    assert text == "" and len(out) == 1 and out[0]["name"] == "x-combo" and len(out[0]["also"]) == 1 and "check" not in out[0], out


@case("drift records a check `like` a crawl older than the variants as same when only a scelta's new sections differ")
def _():
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    (tmp / "sections").mkdir()
    sec = lambda n, f, **k: {"section": n, "fingerprint": f, **k}
    (tmp / "sections" / "suap-x-old.json").write_text(json.dumps({"sections": [sec("A", "f1"), sec("B", "f2")]}))
    check = lambda name, sections: {"crawled": "2026-11-17T00:00:00Z", "name": name, "like": "suap-x-old", "sections": sections}
    export = tmp / "export.json"
    export.write_text(json.dumps({
        "crawl:check:y-aside": check("y-aside", [sec("A", "f1"), sec("B", "f2"), sec("Procura", "f9", scelta="procura")]),
        "crawl:check:y-changed": check("y-changed", [sec("A", "f1"), sec("B", "fX"), sec("Procura", "f9", scelta="procura")]),
        "crawl:check:y-newplain": check("y-newplain", [sec("A", "f1"), sec("B", "f2"), sec("C", "f3")]),
        "crawl:check:y-gone": check("y-gone", [sec("A", "f1")]),
    }))
    keep = catalogue.CAT, catalogue.SECTIONS, catalogue.SAME
    catalogue.CAT, catalogue.SECTIONS, catalogue.SAME = tmp, tmp / "sections", tmp / "same.json"
    try:
        catalogue.cmd_drift(argparse.Namespace(export=str(export), digests=False))
        got = json.loads((tmp / "same.json").read_text())
    finally:
        catalogue.CAT, catalogue.SECTIONS, catalogue.SAME = keep
    assert got["same"] == {"y-aside": "suap-x-old"}, got
    assert set(got["different"]) == {"y-changed", "y-newplain", "y-gone"}, got


if not all(results):
    sys.exit(1)
print(f"\n{len(results)} ok")
