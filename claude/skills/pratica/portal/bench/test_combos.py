#!/usr/bin/env python3
"""Offline tests of what the portal taught about combined SUAP pratiche (2026-11-13): the sign, the acoustic nulla osta and the
dehors filed with an opening, a move or a take-over.

  ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/bench/test_combos.py

No browser, vault or network. Each test is a thing the portal cost a run (or a crawl) to find; see README, "SUAP combinations".
"""
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import catalogue as cat  # noqa: E402
import derive_combos as dc  # noqa: E402
import gen  # noqa: E402

ROOT = HERE.parents[4]
REHEARSALS = ROOT / "rehearsals"


def recipe(name):
    return yaml.safe_load((REHEARSALS / name / "recipe.yaml").read_text(encoding="utf-8"))


def steps(name):
    return yaml.safe_load((REHEARSALS / name / "portal-steps.generated.yaml").read_text(encoding="utf-8"))


def no_recipe_rests_on_a_ticked_crawl():
    """A crawl taken with an «interventi» option left ticked has its sections in its base. gen.py refuses a recipe on one unless it
    says `crawl_ticked`; the stored crawls that are such are named here, so a new one is noticed."""
    known = {"suap-004-aprire-l-attivita-interventi", "suap-016-aprire-l-attivita-interventi",
             "suap-017-aprire-l-attivita-interventi", "suap-056-aprire-l-attivita-interventi"}
    ticked = {p.stem for p in cat.SECTIONS.glob("*.json") if cat.ticked_interventi(json.loads(p.read_text()).get("screens"))}
    assert ticked == known, f"crawls taken with a tick left: {sorted(ticked ^ known)}"
    for f in REHEARSALS.glob("*/recipe.yaml"):
        r = yaml.safe_load(f.read_text(encoding="utf-8"))
        if r.get("crawl") in ticked:
            assert r.get("crawl_ticked"), f"{f.parent.name} rests on {r['crawl']}, taken with a tick: say why in `crawl_ticked`, or use the plain crawl"
    # import refuses one
    assert cat.ticked_interventi([{"screen": "scelta interventi eventuali", "options": [{"label": "x", "selected": True}]}]) == ["x"]
    assert not cat.ticked_interventi([{"screen": "scelta interventi eventuali", "options": [{"label": "x"}]}])
    assert not cat.ticked_interventi([{"screen": "scelte eventuali", "options": [{"label": "x", "selected": True}]}])  # a scelta's tick is the batch's own


def gen_refuses_a_ticked_crawl():
    r = recipe("alimentari-insegna-fittizio")
    r["crawl"] = "suap-017-aprire-l-attivita-interventi"
    r.pop("crawl_ticked", None)
    try:
        gen.generate(r)
        raise AssertionError("a recipe on a crawl with a leftover tick should be refused")
    except gen.GenError as e:
        assert "ticked" in str(e), e
    r["crawl_ticked"] = "for the test"
    try:
        gen.generate(r)  # allowed past the guard; it may still fail on the crawl's own sections, but not on the tick
    except gen.GenError as e:
        assert "ticked" not in str(e), e


def every_reference_resolves():
    """A section's `same_as` names a crawl that is in the repo and holds it (import names the first crawl with a fingerprint: a crawl deleted
    afterwards, the contaminated dehors ones, left the take-overs' sign sections pointing at nothing: gen.py "isn't in the catalogue")."""
    crawls = {p.stem: json.loads(p.read_text()) for p in cat.SECTIONS.glob("*.json")}
    for name, d in crawls.items():
        for s in d["sections"]:
            ref = s.get("same_as")
            if not ref or "#" not in ref:
                continue
            target, section = ref.split("#", 1)
            if target == name:
                continue
            assert target in crawls, f"{name}: {s['section']} is the same as {ref}, a crawl that is not in the repo"
            assert section in {x["section"] for x in crawls[target]["sections"]}, f"{name}: {ref} holds no such section"


def combinations_are_what_the_probe_took():
    """Every recipe that selects two operations in the wizard (the dehors' area, the sign) is a pair the probe took together."""
    probed = {tuple(p["operations"]) for p in json.loads((cat.CAT / "suap-pairs.json").read_text())["pairs"] if p["accepted"]}
    leaves = {main for main, _ in probed} | {other for _, other in probed}
    two = 0
    for f in REHEARSALS.glob("*/recipe.yaml"):
        r = yaml.safe_load(f.read_text(encoding="utf-8"))
        for st in r.get("wizard") or []:
            tree = st.get("tree") if isinstance(st, dict) and st.get("screen") == "Scelta operazioni" else None
            if tree and len(tree) > 1 and (dc.SIGN_OP in tree or dc.DEHORS_OP in tree):
                two += 1
                assert (tree[0], tree[1]) in probed, f"{f.parent.name}: {tree} is not a pair the wizard probe took together"
    assert two >= 9, two


def every_combination_has_a_filled_run_and_its_rules():
    """Each recipe derive_combos.py builds files the library's SUAP table's case (its `rules:` block says which procedures it files), and
    has a run on the portal that filled. A combination whose run stopped is left out of routing (no rules block) and named in
    catalogue/F839/suap-unrouted.yaml, never routed on a guess."""
    for name, c in dc.COMBOS.items():
        r = recipe(name)
        assert r["rules"]["handles"] == c["handles"], (name, r["rules"]["handles"])
        runs = json.loads((REHEARSALS / name / "runs.json").read_text())
        assert any(x["result"] == "filled" for x in runs["runs"] if "result" in x) if isinstance(runs, dict) and "runs" in runs else \
            any(x.get("result") == "filled" for x in runs), f"{name}: no filled run on the portal"


def one_bollo_when_two_adempimenti_want_it():
    """The dehors' area and the nulla osta each want the bollo declaration: the draft shows one, under the tick's title."""
    for name in ("ristorante-dehors-musica-fittizio", "ristorante-dehors-insegna-musica-fittizio"):
        titles = [s["section"] for s in steps(name)["sections"] if "bollo" in s["section"].lower()]
        assert titles == ["dichiarazione relativa all'imposta di bollo"], (name, titles)
    # without the tick the base's own title stays
    titles = [s["section"] for s in steps("ristorante-dehors-fittizio")["sections"] if "bollo" in s["section"].lower()]
    assert titles == ["Dichiarazione relativa all'assolvimento dell'imposta di bollo"], titles


def the_signs_form_is_the_pages_when_both_ticks_are_ticked():
    """The bar's opening with the sign and the nulla osta, on the opening's `-interventi` crawl, got the other dictionary entry for «Caratteristiche
    del manufatto» and stopped on «num. progressivo» (2026-11-13); the page shows «Tipologia» first, as in every sign recipe that filled."""
    for name in ("ristorante-insegna-fittizio", "ristorante-insegna-musica-fittizio", "trasferimento-ristorante-insegna-musica-fittizio",
                 "ristorante-dehors-insegna-musica-fittizio"):
        sec = next(s for s in steps(name)["sections"] if s["section"] == "Caratteristiche del manufatto da installare")
        assert sec["fields"][0]["label"] == "Tipologia", (name, sec["fields"][0]["label"])
    assert recipe("ristorante-insegna-musica-fittizio")["crawl"] == "suap-060-aprire-l-attivita"


def the_pane_code_keeps_what_it_learned():
    """Text checks of the pane's scripts: a leftover interventi tick is cleared by the wizard, a stale busy flag doesn't hold the next bundle,
    a pair can name its sector, a batch's skips are shown."""
    wiz = (HERE.parent / "wizard.js").read_text()
    assert 'title().includes("scelte eventuali") || title().includes("interventi eventuali")' in wiz
    assert "a.sector || opts.sector" in wiz
    src = (HERE.parent / "catalogue.py").read_text()
    assert "window.__crawlBusy && window.__crawl && (window.__crawl.report() || {}).done === false" in src
    assert "skipped: r.skipped" in src
    assert "--base-only" in src and "--interventi" in src and "--suap" in src
    # The PrimeFaces dropdown has no stand-in in bench/portal.html: its code-prefixed items («69 _ 1 _ A: Locali di esposizione...») were
    # proved on the portal (2026-11-14), and the rule is held here as text.
    inpage = (HERE.parent / "inpage.js").read_text()
    assert 'startsWith(value + ":")' in inpage and "coded.length === 1" in inpage
    run_py = (HERE.parent / "run.py").read_text()
    assert '"w1"' in run_py and '"w2"' in run_py and '"w3"' in run_py


VVF_PROCEDURE = "napoli/vigili-del-fuoco/scia-prevenzione-incendi"


def fire_prevention_combinations():
    """The opening, move and enlargement filed with the SCIA VV.F. (PIN 2), 2026-11-14: 48 rehearsals, each filled on the portal.
    What each cost a run: the crawl is the combination's own (`suap-NNN-...-pin-2`, else import files it as the SUE's); in zones A/B the
    nulla osta has its own bollo, so the plain crawl's `scelte_none` must be in the -pin-2 crawl too (two recipes stopped at «no section
    dichiarazione relativa all'imposta di bollo»); the antincendio professional is the `v:` person; only category A, whole SCIA."""
    folders = sorted(REHEARSALS.glob("*-pin-2-fittizio"))
    assert len(folders) >= 48, len(folders)
    for d in folders:
        r = recipe(d.name)
        crawl = r["crawl"]
        assert crawl.startswith("suap-") and crawl.endswith("-pin-2") and (cat.SECTIONS / f"{crawl}.json").exists(), (d.name, crawl)
        assert r["rules"]["facts"]["prevenzione_incendi"] in (True, "true"), d.name
        assert VVF_PROCEDURE in r["rules"]["handles"], d.name
        assert dc.PIN2_OP in next(st["tree"] for st in r["wizard"] if st.get("screen") == "Scelta operazioni"), d.name
        assert json.loads((d / "answers.json").read_text()).get("people", {}).get("v"), f"{d.name}: no antincendio professional (`v:`)"
        refused = " ".join(str(x.get("else", "")) for x in r.get("supports", []))
        assert "categoria B e C" in refused and "parziale" in refused, f"{d.name}: B/C and SCIA parziale must be refused"
        runs = json.loads((d / "runs.json").read_text())
        assert any(x.get("result") == "filled" for x in (runs["runs"] if isinstance(runs, dict) else runs)), f"{d.name}: no filled run"
        # the plain crawl's scelte_none (a tick that adds no section) is inherited
        base = json.loads((cat.SECTIONS / f"{crawl[:-len('-pin-2')]}.json").read_text()) if (cat.SECTIONS / f"{crawl[:-len('-pin-2')]}.json").exists() else {}
        mine = json.loads((cat.SECTIONS / f"{crawl}.json").read_text())
        for k in base.get("scelte_none", {}):
            assert k in mine.get("scelte_none", {}), f"{crawl}: «{k[:50]}» adds no section in the plain crawl; inherit scelte_none from it"
    # The distinta's counts: each impianti row by its number, the structure and product counts only when their tick is set
    # (the portal switches them off otherwise, and a bare «n°» also matches «n. atti», «n. elaborati»).
    sec = next(s for s in steps("ristorante-pin-2-fittizio")["sections"] if s["section"].upper().startswith("DISTINTA DELLA DOCUMENTAZIONE TECNICA"))
    rows = [f for f in sec["fields"] if f.get("kind") == "number" and str(f.get("label", "")).startswith("4.")]
    assert len(rows) == 24, len(rows)
    ticked_only = [f for f in sec["fields"] if f.get("kind") == "number" and f.get("label") == "n°" and f.get("nth") in (3, 4)]
    assert len(ticked_only) == 2 and all(f.get("when") for f in ticked_only), ticked_only


def import_refuses_a_suap_crawl_named_as_the_sue_s():
    """A SUAP crawl (it has a sector) whose name lacks `suap-NNN-` was filed as «SUE:» and no recipe found its sections (2026-11-14)."""
    import os
    import tempfile
    os.environ.setdefault("CATALOGUE_PRIVATE", r"\b(nomeprova)\b")  # import checks every crawl against the login's name: a placeholder here
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / "export.json"
        f.write_text(json.dumps({"crawl:op:ristorante-pin-2": {"name": "ristorante-pin-2", "sector": 60, "operation": "x", "sections": []}}))
        try:
            cat.cmd_import(type("a", (), {"export": str(f), "depth": None}))
            raise AssertionError("a SUAP crawl named without suap- should be refused")
        except SystemExit as e:
            assert "suap-NNN" in str(e), e


def dictionary_entries_are_where_gen_reads_them():
    """An entry written under `after:` (the screens after the form: they have `go`) is never matched as a section: gen.py said only «no
    dictionary entry» (2026-11-14, the VV.F. entries). Now it says where it is, and every `after:` item has `go`."""
    d = yaml.safe_load((HERE.parent / "dictionary" / "fnsuap.yaml").read_text(encoding="utf-8"))
    assert all("go" in a for a in d["after"]), [a.get("section") for a in d["after"] if "go" not in a]
    assert "belongs under `sections:`" in (HERE.parent / "gen.py").read_text()


def a_bundle_holds_at_most_a_dozen_runs():
    """The pane's storage takes about 12 runs a bundle (README, «Checking them all»): rerun.py refuses more rather than failing in the pane."""
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        v = Path(t) / "values.json"
        v.write_text("{}")
        p = subprocess.run([sys.executable, str(HERE / "rerun.py"), "--values", str(v), "--out", str(Path(t) / "out"),
                            "--bundle", str(Path(t) / "b.js"), *[f"x{i}:answers.json" for i in range(13)]], capture_output=True, text=True)
        assert p.returncode == 2 and "at most 12 runs" in p.stderr, (p.returncode, p.stderr[-300:])


def main():
    for t in (no_recipe_rests_on_a_ticked_crawl, gen_refuses_a_ticked_crawl, every_reference_resolves, combinations_are_what_the_probe_took,
              every_combination_has_a_filled_run_and_its_rules, one_bollo_when_two_adempimenti_want_it, the_signs_form_is_the_pages_when_both_ticks_are_ticked, the_pane_code_keeps_what_it_learned,
              fire_prevention_combinations, import_refuses_a_suap_crawl_named_as_the_sue_s, dictionary_entries_are_where_gen_reads_them,
              a_bundle_holds_at_most_a_dozen_runs):
        t()
        print("ok ", t.__name__)
    print("done")


if __name__ == "__main__":
    main()
