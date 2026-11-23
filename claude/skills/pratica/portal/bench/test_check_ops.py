#!/usr/bin/env python3
"""What the drift check taught on 2026-11-23, offline, on the real catalogue (README «Round 30»).

  ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/bench/test_check_ops.py

No browser, vault or network. Check ops are built for stored crawls in the sector each was crawled in, a cover picks the fewest
crawls that vouch for the sections nothing vouches for yet, a pane bundle for a check clears today's earlier results with --fresh,
the poll script waits even in a hidden pane, and a check on a dirty scratch draft is named as one.
"""
import argparse
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.dont_write_bytecode = True
os.environ.setdefault("CATALOGUE_PRIVATE", r"\bnessun-nome-fittizio\b")
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


RICHI = "suap-common-mezzi-pubblicitari-installazione-di-mezzi-pubblicitari-richi"


class temp_catalogue:
    """catalogue.CAT with its own drift.json and same.json (copies) over the real sections, for a check to write into."""
    def __enter__(self):
        self.tmp = tempfile.mkdtemp()
        base = Path(self.tmp) / "F839"
        base.mkdir()
        (base / "sections").symlink_to(catalogue.SECTIONS)
        for f in ("drift.json", "same.json", "suap-wizard.json"):
            if (catalogue.CAT / f).exists():
                shutil.copy(catalogue.CAT / f, base / f)
        self.keep = (catalogue.CAT, catalogue.SECTIONS, catalogue.SAME)
        catalogue.CAT, catalogue.SECTIONS, catalogue.SAME = base, base / "sections", base / "same.json"
        return base

    def __exit__(self, *a):
        catalogue.CAT, catalogue.SECTIONS, catalogue.SAME = self.keep
        shutil.rmtree(self.tmp, ignore_errors=True)


@case("a stored crawl's check op is in the sector it was crawled in: the common advertising operation was «not in the tree» under the first sector")
def _():
    op = catalogue.stored_op(RICHI)
    assert op["check"] is True and op["name"] == RICHI, op
    assert op["sector"] == "Esercizio di somministrazione di alimenti e bevande in zone NON tutelate", op["sector"]
    assert op["path"].startswith("RAD: ALTRE ESIGENZE") and "teli collegati" in op["path"] and not op["path"].endswith(")"), op["path"]
    # a sector's own name may end in a parenthesis: only the one that closes «(sector …)» goes
    assert catalogue.stored_op("suap-056-aprire-l-attivita")["sector"].endswith("rifugi di montagna)"), catalogue.stored_op("suap-056-aprire-l-attivita")["sector"]
    wedge = catalogue.stored_op("suap-016-cessare-l-attivita")
    assert wedge["sector"].startswith("Vicinato") and wedge["path"].endswith("Cessare l'attività"), wedge


@case("a crawl taken with a tick on has no check op: a plain check would not read the tick's sections")
def _():
    assert catalogue.stored_op("suap-016-aprire-l-attivita-interventi") is None
    assert catalogue.stored_op("suap-060-aprire-l-attivita-interventi") is None  # by its name: its screens don't show the tick
    assert catalogue.stored_op("suap-016-aprire-l-attivita") is not None


@case("a combination, or a crawl with no path of its own, has no check op")
def _():
    combos = [p.stem for p in catalogue.SECTIONS.glob("suap-*.json")
              if "operations in one pratica" in json.loads(p.read_text()).get("pratica", "") or json.loads(p.read_text()).get("also")]
    assert combos, "no combination in the catalogue?"
    assert catalogue.stored_op(combos[0]) is None
    try:
        catalogue.check_ops([combos[0]])
    except SystemExit as e:
        assert "no check op" in str(e)
    else:
        raise AssertionError("check_ops accepted a combination")


@case("the cover vouches for every section a buildable crawl holds that no unchanged drift entry vouches for, with ops in the crawls' own sectors")
def _():
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        ops = catalogue.check_ops()
    assert ops and all(o["check"] and o["sector"] and o["path"] for o in ops), ops[:2]
    cache = {}
    secs = lambda n: {(s, f) for s, f in catalogue.stored_fingerprints(n, cache).items() if f}
    got = set().union(*[secs(o["name"]) for o in ops]) | catalogue.vouched()
    changed = {n for n, d in json.loads((catalogue.CAT / "drift.json").read_text())["pratiche"].items() if d.get("differences")}
    for p in catalogue.SECTIONS.glob("suap-*.json"):
        if catalogue.stored_op(p.stem) and p.stem not in changed:
            assert secs(p.stem) <= got, (p.stem, "has a section the cover leaves unvouched")
    assert "check cover:" in err.getvalue()
    names = [o["name"] for o in ops]
    assert len(names) == len(set(names))


@case("a pane bundle for a check: the poll waits though the pane reads hidden, and --fresh clears today's earlier check results")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        ops = [catalogue.stored_op("suap-016-cessare-l-attivita")]
        (Path(tmp) / "ops.json").write_text(json.dumps(ops))
        a = argparse.Namespace(dir=str(Path(tmp) / "pane"), bundle=str(Path(tmp) / "b.js"), ops=str(Path(tmp) / "ops.json"), draft=None, depth=3,
                               fresh=True, forget_known=False, check=True, base_only=False, interventi=False)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            catalogue.cmd_pane(a)
        assert "must be a fresh draft" in err.getvalue(), err.getvalue()
        bundle = (Path(tmp) / "b.js").read_text()
        clear = 'localStorage.removeItem("crawl:check:" + o.name)'
        assert clear in bundle, "--fresh left today's check results in the pane"
        assert "catalogo suap" in bundle
        status = (Path(tmp) / "pane" / "status.js").read_text()
        assert "document.hidden" not in status.replace("document.hidden as true", ""), status
        tree = (Path(tmp) / "pane" / "tree.js").read_text()
        assert "window.pvTree" in tree and "toScreen(\"scelta settore\")" in tree
        a.fresh = False
        a.bundle = str(Path(tmp) / "c.js")
        with contextlib.redirect_stderr(io.StringIO()):
            catalogue.cmd_pane(a)
        assert clear not in (Path(tmp) / "c.js").read_text(), "a check without --fresh cleared the earlier results"


@case("a check where the description and both domicilio sections changed together is named a dirty scratch draft")
def _():
    n = "suap-016-cessare-l-attivita"
    with temp_catalogue():
        fps = catalogue.stored_fingerprints(n)
        sections = [{"section": k, "fingerprint": ("0" * 16 if k in catalogue.DRAFT_STATE else v)} for k, v in fps.items()]
        export = Path(catalogue.CAT) / "export.json"
        export.write_text(json.dumps({"crawl:check:" + n: {"name": n, "crawled": "2026-11-23T00:00:00Z", "sections": sections}}))
        out = catalogue.cmd_drift(argparse.Namespace(export=str(export), digests=False))
        assert catalogue.DIRTY_DRAFT in out, out
        assert any(x.startswith(n + ": changed:") for x in out)
        # one changed section on its own is a change, not a draft's state
        sections = [{"section": k, "fingerprint": ("0" * 16 if k == "dati catastali" else v)} for k, v in fps.items()]
        export.write_text(json.dumps({"crawl:check:" + n: {"name": n, "crawled": "2026-11-23T00:00:00Z", "sections": sections}}))
        out = catalogue.cmd_drift(argparse.Namespace(export=str(export), digests=False))
        assert catalogue.DIRTY_DRAFT not in out, out


@case("when nearly every digest of a batch differs, the output says to suspect the scratch draft before the portal")
def _():
    names = sorted(p.stem for p in catalogue.SECTIONS.glob("suap-0*.json"))[:12]
    with temp_catalogue():
        data = {"digests": {n: {"digest": "0" * 12, "base": "1" * 12, "crawled": "2026-11-23T00:00:00Z"} for n in names}}
        export = Path(catalogue.CAT) / "digests.json"
        export.write_text(json.dumps(data))
        out = catalogue.drift_digests(str(export))
        assert any("suspect the scratch draft" in x for x in out), out
        data["digests"] = {n: d for n, d in list(data["digests"].items())[:3]}
        export.write_text(json.dumps(data))
        assert not any("suspect the scratch draft" in x for x in catalogue.drift_digests(str(export)))


if not all(results):
    sys.exit(1)
print(f"\n{len(results)} ok")
