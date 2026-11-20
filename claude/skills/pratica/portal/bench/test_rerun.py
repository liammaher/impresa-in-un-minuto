#!/usr/bin/env python3
"""rerun.py offline: what a batch for the pane holds, and what it refuses before anyone picks a file.

  ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/bench/test_rerun.py

No browser, vault or network. Each case was learned on the real portal (2026-11-11, the procura variants):

  - two steps files of one procedure (a pratica and its procura variant) in one batch are keyed apart in the
    pane (run.py page_bundle: the procedure and a hash of what it fills); until that key, the last one's steps
    ran for both (2026-11-11);
  - a SUAP rehearsal answers in answers.json (the SUE's in answers-p6.json): named alone it is found, and
    recorded under its own file;
  - values that are the rehearsal's own fixture.json are what its run is recorded on (no "@" in the name);
  - a client company with a REA can't pass the portal's check with made-up data: refused, not sent;
  - a second build into the same --out folder or over the same --bundle file is refused (2026-11-18: a second run with
    other specs clobbered a Desktop bundle the person had been asked to pick), unless --overwrite.
"""
import io
import json
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import rerun  # noqa: E402

ROOT = HERE.parents[4]
REH = ROOT / "rehearsals"
OWN = "ristorante-procura-fittizio"
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


def batch(*args, values=None):
    """rerun.py's main with these arguments: (exit message or None, the queue file's text)."""
    out = Path(tempfile.mkdtemp())
    argv = ["rerun.py", "--values", str(values or REH / "pizzeria-fittizia" / "fixture.json"), "--out", str(out), *args]
    old, here = sys.argv, os.getcwd()
    sys.argv = argv
    os.chdir(ROOT)
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            try:
                rerun.main()
                msg = None
            except SystemExit as e:
                msg = str(e.code) if e.code not in (0, None) else None
    finally:
        sys.argv = old
        os.chdir(here)
    batch.out = out
    q = out / "queue-0.js"
    batch.steps = sorted(p.name for p in (out / "steps").glob("*.js")) if (out / "steps").is_dir() else []
    return msg, q.read_text() if q.exists() else None


@case("two steps files of one procedure in one batch are keyed apart: each runs on its own steps")
def _():
    own = lambda n: f"{n}:answers.json:rehearsals/{n}/fixture.json"
    msg, q = batch("ristorante-fittizio", own(OWN))
    assert msg is None and q, msg
    assert len(batch.steps) == 2 and len(set(batch.steps)) == 2, batch.steps  # two steps files, two keys
    msg, q = batch(own("subingresso-ristorante-procura-fittizio"), own("subingresso-negozio-procura-fittizio"))
    assert msg is None and len(batch.steps) == 2, (msg, batch.steps)


@case("each of them alone builds")
def _():
    msg, q = batch("ristorante-fittizio")
    assert msg is None and q, msg
    for n in (OWN, "subingresso-negozio-procura-fittizio"):
        msg, q = batch(f"{n}:answers.json:rehearsals/{n}/fixture.json")
        assert msg is None and q, (n, msg)


@case("a SUAP rehearsal is found by its answers.json, and its own fixture keeps its name for the record")
def _():
    msg, q = batch(f"{OWN}:answers.json:rehearsals/{OWN}/fixture.json", values=REH / OWN / "fixture.json")
    assert msg is None and q, msg
    assert f"{OWN}/answers" in q and "@fixture" not in q, q[:200]  # recorded: not "...answers@fixture"
    # other values than the rehearsal's own are another case: named by them, and not recorded
    other = Path(tempfile.mkdtemp()) / "other.json"
    shutil.copy(REH / OWN / "fixture.json", other)
    msg, q = batch(f"{OWN}:answers.json:{other}", values=REH / OWN / "fixture.json")
    assert msg is None and "@other" in q, msg


@case("a client company with a REA can't pass the portal with made-up data: refused before a file is picked")
def _():
    fixture = json.loads((REH / OWN / "fixture.json").read_text())
    fixture["fields"] += [["trattoria:business.rea", "NA-1234567"], ["trattoria:business.cciaa", "NA"]]
    tmp = Path(tempfile.mkdtemp()) / "fixture.json"
    tmp.write_text(json.dumps(fixture))
    msg, q = batch(OWN, values=tmp)
    assert msg and "made-up data can't pass" in msg and q is None, msg
    # It says what to leave out (2026-11-12: a visura camerale's REA stopped a shop's made-up run, and the message had to be read twice).
    assert "business.rea" in msg and "business.cciaa" in msg and "data_iscrizione_rea" in msg, msg


@case("an answers file outside the rehearsal's folder is another case, named so that --record skips it (2026-11-12)")
def _():
    # A messy folder's case, answers.json in a scratch folder: by its name alone it was `negozio-fittizio/answers`, the name
    # --record files under the rehearsal as its own run.
    other = Path(tempfile.mkdtemp()) / "answers.json"
    shutil.copy(REH / "negozio-fittizio" / "answers.json", other)
    msg, q = batch(f"negozio-fittizio:{other}", values=REH / "negozio-fittizio" / "fixture.json")
    assert msg is None and q, msg
    assert "negozio-fittizio/answers@elsewhere" in q, q[:200]
    real = rerun.REHEARSALS
    tmp = Path(tempfile.mkdtemp())
    (tmp / "negozio-fittizio").mkdir()
    (tmp / "negozio-fittizio" / "answers.json").write_text("{}")
    rerun.REHEARSALS = tmp
    try:
        with redirect_stdout(io.StringIO()):
            rerun.record([{"name": "negozio-fittizio/answers@elsewhere", "result": "filled", "total_seconds": 7.0}], "answers-p6.json", "2026-11-12")
        assert not (tmp / "negozio-fittizio" / "runs.json").exists(), "an answers file from elsewhere is not the rehearsal's run"
    finally:
        rerun.REHEARSALS = real
        shutil.rmtree(tmp, ignore_errors=True)


@case("check.js on a sign-in page says to sign in, and that a provider's home page is not a sign-in (2026-11-12)")
def _():
    import subprocess
    msg, q = batch("ristorante-fittizio")
    check = (batch.out / "check.js").read_text()
    assert "this page is a sign-in" in check and "sielte" in check and "did not log in" in check, check[-900:]
    node = shutil.which("node")
    if node:  # run it as the pane would, on a page of the SPID provider's
        js = "const location={origin:'https://identity.sieltecloud.it',hostname:'identity.sieltecloud.it'};const localStorage={getItem:()=>null};" \
             "const crypto=require('crypto').webcrypto;const TextEncoder=globalThis.TextEncoder;(" + check.strip() + ").then(r=>console.log(r))"
        out = subprocess.run([node, "-e", js], capture_output=True, text=True).stdout
        assert "go to https://suap.impresainungiorno.gov.it first" in out and "sign-in" in out, out


@case("record: a SUAP rehearsal's run is filed under its own answers file, once")
def _():
    real = rerun.REHEARSALS
    tmp = Path(tempfile.mkdtemp())
    (tmp / "suap-x").mkdir()
    (tmp / "suap-x" / "answers.json").write_text("{}")
    (tmp / "sue-x").mkdir()
    (tmp / "sue-x" / "answers-p6.json").write_text("{}")
    rerun.REHEARSALS = tmp
    try:
        with redirect_stdout(io.StringIO()):
            for _ in range(2):
                rerun.record([{"name": "suap-x", "result": "filled", "total_seconds": 5.0},
                              {"name": "sue-x", "result": "filled", "total_seconds": 6.0},
                              {"name": "suap-x/answers@fixture", "result": "filled"}], "answers-p6.json", "2026-11-11")
        suap = json.loads((tmp / "suap-x" / "runs.json").read_text())
        sue = json.loads((tmp / "sue-x" / "runs.json").read_text())
        assert [r["answers"] for r in suap] == ["answers.json"] and [r["answers"] for r in sue] == ["answers-p6.json"], (suap, sue)
    finally:
        rerun.REHEARSALS = real
        shutil.rmtree(tmp, ignore_errors=True)


@case("loop.js refuses a pane whose stored runner isn't the one the batch was built for (2026-11-11: the pane held another checkout's, 86,595 characters against 80,592)")
def _():
    import re
    import subprocess
    msg, q = batch("ristorante-fittizio")
    assert msg is None, msg
    loop = (batch.out / "loop.js").read_text()
    # the sha check.js holds for the stored runner (runner.js is the script that stores it)
    want = re.search(r'"pv-runner": "([0-9a-f]{64})"', (batch.out / "check.js").read_text())[1]
    assert want in loop and "__RUNNER_SHA__" not in loop, "loop.js doesn't name the runner it was built for"
    if not shutil.which("node"):
        return
    # loop.js in node with a stub page whose stored runner is another: it must not start a run.
    harness = (
        "global.window = {pvBatch: [['x', 'p', {}]]}; global.document = {querySelectorAll: () => []};\n"
        "const store = {'pv-runner': 'window.__pv = {start() { window.started = true; }, wait: async () => ({result: \"filled\"})};'};\n"
        "global.localStorage = {getItem: (k) => store[k] ?? null}; const ss = {}; global.sessionStorage = {getItem: (k) => ss[k] ?? null, setItem: (k, v) => { ss[k] = v; }};\n"
        "global.window.__pv = null; (0, eval)(" + json.dumps(loop) + ");\n"
        "window.pvBatchRun.then((r) => console.log(JSON.stringify({r, started: !!window.started, halted: window.pvBatchHalted})));\n"
    )
    out = subprocess.run(["node", "-e", harness], capture_output=True, text=True, timeout=30)
    got = json.loads(out.stdout.strip().splitlines()[-1]) if out.stdout.strip() else out.stderr
    assert got == {"r": "refused", "started": False, "halted": got["halted"]} and "runner" in got["halted"], got


@case("results.js says when the page was reloaded under the batch (2026-11-17: another chat used the portal, the queue was gone, `done` 0 and `running` false)")
def _():
    msg, q = batch("ristorante-fittizio")
    assert msg is None, msg
    res = (batch.out / "results.js").read_text()
    assert "reloaded" in res and "pv-report" in res, "results.js doesn't read the last report of a reloaded page"
    if not shutil.which("node"):
        return
    import subprocess
    body = res.split("setTimeout(r, 35000));\n", 1)[1]  # the statement that waits 35 s while the pane shows the page
    harness = (
        "global.window = {}; global.document = {hidden: true};\n"
        "const ss = {'pv-report': JSON.stringify({result: 'stopped', error: 'Attestato: 0 fields with this label', at: {section: 'distinta di versamento'}, url: 'https://x/cmd/error'})};\n"
        "global.sessionStorage = {getItem: (k) => ss[k] ?? null};\n"
        "console.log((0, eval)(" + json.dumps(body) + "));\n"
    )
    out = subprocess.run(["node", "-e", harness], capture_output=True, text=True, timeout=30)
    got = json.loads(out.stdout.strip().splitlines()[-1]) if out.stdout.strip() else out.stderr
    assert got["reloaded"] and got["reloaded"]["last"]["at"] == "distinta di versamento" and got["done"] == 0 and not got["running"], got
    # a live runner (the page was not reloaded): no such note
    harness = harness.replace("global.window = {};", "global.window = {__pv: {}};")
    out = subprocess.run(["node", "-e", harness], capture_output=True, text=True, timeout=30)
    assert json.loads(out.stdout.strip().splitlines()[-1])["reloaded"] is None, out.stdout


@case("round 13: a spec that names no rehearsal (zsh read \"$n:answers.json\" as the :a modifier) is refused with a message naming it, not a traceback; vvf_tendina.js parses")
def _():
    import subprocess
    out = subprocess.run([sys.executable, str(HERE / "rerun.py"), "--values", str(HERE.parents[4] / "rehearsals" / "pin-4-deroga-fittizio" / "fixture.json"), "--out", tempfile.mkdtemp(),
                          "pin-3-rinnovo-fittizionswers-b.json:rehearsals/x/fixture.json"], capture_output=True, text=True, timeout=60)
    assert out.returncode != 0 and "Traceback" not in out.stderr and "no rehearsal named" in out.stderr and "${n}" in out.stderr, out.stderr[-400:]
    js = subprocess.run(["node", "--check", str(HERE / "vvf_tendina.js")], capture_output=True, text=True, timeout=30)
    assert js.returncode == 0, js.stderr


@case("a second build into the same --out folder, or over the same --bundle file, is refused unless --overwrite (a Desktop bundle was clobbered 2026-11-18)")
def _():
    import subprocess
    out, bundle = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp()) / "bundle.js"
    spec = f"{OWN}:answers.json:rehearsals/{OWN}/fixture.json"
    argv = [sys.executable, str(HERE / "rerun.py"), "--values", str(REH / OWN / "fixture.json"), "--out", str(out), "--bundle", str(bundle)]
    first = subprocess.run([*argv, spec], capture_output=True, text=True, timeout=300, cwd=ROOT)
    assert first.returncode == 0 and bundle.exists(), first.stderr[-400:]
    kept = bundle.read_text()
    again = subprocess.run([*argv, spec], capture_output=True, text=True, timeout=300, cwd=ROOT)
    assert again.returncode != 0 and "already exists" in again.stderr and "--overwrite" in again.stderr and "Traceback" not in again.stderr, again.stderr[-400:]
    assert bundle.read_text() == kept  # refused before anything was written
    # a new bundle path with the same --out folder is refused too (the folder is what a half-picked batch reads)
    other = subprocess.run([*argv[:-1], str(bundle.with_name("other.js")), spec], capture_output=True, text=True, timeout=300, cwd=ROOT)
    assert other.returncode != 0 and "--out folder" in other.stderr, other.stderr[-400:]
    forced = subprocess.run([*argv, "--overwrite", spec], capture_output=True, text=True, timeout=300, cwd=ROOT)
    assert forced.returncode == 0, forced.stderr[-400:]


def node(js):
    """The result of a script as the pane runs it (REPL semantics, top-level await), under a fake page."""
    import subprocess
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60)
    return out.returncode, (out.stdout + out.stderr).strip()


def built(**kw):
    out, bundle = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp()) / "bundle.js"
    import subprocess
    spec = f"{OWN}:answers.json:rehearsals/{OWN}/fixture.json"
    r = subprocess.run([sys.executable, str(HERE / "rerun.py"), "--values", str(REH / OWN / "fixture.json"), "--out", str(out), "--bundle", str(bundle), spec],
                       capture_output=True, text=True, timeout=300, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-400:]
    return out


@case("pick.js refuses the sign-in page and says so (2026-11-20: the pane starts on InfoCamere's login; the bundle path skips check.js)")
def _():
    pick = (built() / "pick.js").read_text()
    page = lambda origin, host: ("globalThis.window = {}; globalThis.document = {querySelectorAll: () => [], createElement: () => ({style: {}, querySelector: () => ({addEventListener() {}})}), "
                                 "body: {appendChild() {}}}; globalThis.location = {origin: %s, hostname: %s};" % (json.dumps(origin), json.dumps(host)))
    code, out = node(page("https://iasu.infocamere.it", "iasu.infocamere.it") + "try { (0, eval)(%s) } catch (e) { console.log('THROWN ' + e.message) }" % json.dumps(pick))
    assert "THROWN go to https://suap.impresainungiorno.gov.it first" in out and "sign-in" in out and "SPID" in out, out
    # on the portal it gets as far as the box
    code, out = node(page("https://suap.impresainungiorno.gov.it", "suap.impresainungiorno.gov.it") + "console.log((0, eval)(%s))" % json.dumps(pick))
    assert "box shown" in out, out


@case("check.js says the same on the sign-in page, in the same words")
def _():
    check = (built() / "check.js").read_text()
    code, out = node("globalThis.localStorage = {getItem: () => null}; globalThis.location = {origin: 'https://iasu.infocamere.it', hostname: 'iasu.infocamere.it'};"
                     "(0, eval)(%s).then(console.log)" % json.dumps(check))
    assert out.startswith("go to https://suap.impresainungiorno.gov.it first") and "SPID" in out, out


@case("results.js shows the run in progress and whether the tab is hidden (2026-11-20: a 148 s first run showed done 0 and nothing else)")
def _():
    res = (built() / "results.js").read_text()
    body = res[:res.rindex("\nJSON.stringify(") + 1] + "return " + res[res.rindex("\nJSON.stringify(") + 1:]
    fake = ("globalThis.document = {hidden: true}; const store = {}; globalThis.sessionStorage = {getItem: (k) => store[k] ?? null};"
            "globalThis.window = globalThis; window.pvBatch = [1, 2]; window.pvBatchBusy = true; window.pvBatchNow = 'x/answers';"
            "window.__pv = {last: () => ({result: 'running', at: {section: 'dati catastali'}, sections: [1, 2, 3]})};")
    code, out = node(fake + "(async () => { %s })().then(console.log)" % body)
    data = json.loads(out)
    assert data["now"] == {"run": "x/answers", "result": "running", "at": "dati catastali", "sections": 3}, data
    assert data["hidden"] is True and data["running"] is True and data["done"] == 0, data


@case("results.js gives the record once the batch has ended, ready for --record, and doesn't wait 35 s for nothing (2026-11-20)")
def _():
    res = (built() / "results.js").read_text()
    body = res[:res.rindex("\nJSON.stringify(") + 1] + "return " + res[res.rindex("\nJSON.stringify(") + 1:]
    fake = ("globalThis.document = {hidden: false}; const store = {'pv-batch': JSON.stringify([{name: 'a/answers', result: 'filled', total_seconds: 61.2, moved: [], loose: []},"
            "{name: 'b/answers', result: 'stopped', total_seconds: 12, error: 'x', at: {section: 's'}}])};"
            "globalThis.sessionStorage = {getItem: (k) => store[k] ?? null}; globalThis.window = globalThis; window.pvBatch = [1, 2]; window.pvBatchBusy = false;")
    import time
    t0 = time.time()
    code, out = node(fake + "(async () => { %s })().then(console.log)" % body)
    assert time.time() - t0 < 20, "waited for a batch that had ended"
    data = json.loads(out)
    assert data["record"] == [{"name": "a/answers", "result": "filled", "total_seconds": 61.2}, {"name": "b/answers", "result": "stopped", "total_seconds": 12}], data
    assert data["running"] is False and data["filled"] == 1, data


print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
