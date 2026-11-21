#!/usr/bin/env python3
"""Offline tests of driver.mjs (the fill from ChatGPT's in-app browser) on test_inpage.py's fake portal.

  ~/.cache/pratica-portal/venv/bin/python -I claude/skills/pratica/portal/bench/test_driver.py

run.py chatgpt writes the run folder; driver_tab.mjs runs driver.mjs in Node over a tab shaped like ChatGPT's,
whose evaluate is read only (a write fails the run) and reads an email as "<redacted>". Needs Node and Playwright
for Node (PLAYWRIGHT_NODE, default the one inside the ChatGPT app): without them it says so and passes.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import run  # noqa: E402
import test_inpage as bench  # noqa: E402

PW = os.environ.get("PLAYWRIGHT_NODE", "/Applications/ChatGPT.app/Contents/Resources/cua_node/lib/node_modules/playwright")


def drive(base, st, answers, out, opts=None):
    values = run.Values(answers, fields={"x:ruolo.tipo": "titolare"})
    run.chatgpt_run(st, values, out)
    p = subprocess.run(["node", str(HERE / "driver_tab.mjs"), base, str(out)] + ([json.dumps(opts)] if opts else []),
                       capture_output=True, text=True, timeout=600)
    if p.returncode:
        raise AssertionError(f"driver_tab.mjs failed: {p.stderr[-1500:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def main():
    if not shutil.which("node") or not Path(PW).exists():
        print("skipped: needs node and Playwright for Node (PLAYWRIGHT_NODE)")
        return 0
    tmp = Path(tempfile.mkdtemp(prefix="driver-bench-"))
    planimetria, ricevuta = tmp / "planimetria.pdf", tmp / "ricevuta-asl.pdf.p7m"
    planimetria.write_bytes(b"%PDF-1.4\n" + os.urandom(3 * 1024 * 1024))
    ricevuta.write_bytes(b"finta ricevuta firmata\n")
    sha = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (planimetria, ricevuta)}
    answers = {"den": "PIZZERIA FITTIZIA DI GENNARO FITTIZIO", "planimetria": str(planimetria),
               "ricevuta": str(ricevuta), "impresa": "EDIL FITTIZIA DI MARCO ESEMPIO"}
    server = ThreadingHTTPServer(("127.0.0.1", 0), bench.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    failed = []

    def case(name, check):
        out = Path(tempfile.mkdtemp(prefix="run-", dir=tmp))
        try:
            check(out)
            print(f"ok    {name}")
        except AssertionError as e:
            failed.append(name)
            print(f"FAIL  {name}: {e}")

    def kept(out):
        bench.PORTAL.reset()
        r = drive(base, bench.steps(base), answers, out)
        assert r["result"] == "filled", r.get("error")
        assert r.get("verify_seconds") is not None, "no fresh load of the draft"
        assert bench.PORTAL.fields.get(bench.DEN) == answers["den"], f"stored {bench.PORTAL.fields}"
        assert bench.PORTAL.fields.get(bench.IMPRESA) == answers["impresa"], f"stored {bench.PORTAL.fields}"
        got = {f["name"]: f["sha256"] for f in bench.PORTAL.files}
        assert got == sha, f"received {got}"
        assert not bench.PORTAL.sent, "Firma e invio was clicked"
        public = (out / "report.json").read_text()
        for v in ("PIZZERIA", "EDIL FITTIZIA", "planimetria.pdf"):
            assert v not in public, f"report.json holds {v}"
        for name in ("kept.json", "held.json", "shown.json"):
            f = out / "private" / name
            assert f.exists() and oct(f.stat().st_mode & 0o777) == "0o600", f"private/{name}"
    case("fills from disk, attaches 3 MB byte-exact through the chooser, and the fresh load finds it all", kept)

    def dropped(out):
        bench.PORTAL.reset(drop=True)
        r = drive(base, bench.steps(base), answers, out)
        assert r["result"] == "stopped" and "fresh load of the draft: not kept" in r.get("error", ""), r
        assert "PIZZERIA" not in json.dumps(r), "the error names the value"
    case("a value the portal shows but never stores stops the run, without the value", dropped)

    def hidden(out):
        bench.PORTAL.reset()
        r = drive(base, bench.steps(base), answers | {"impresa": "edil.fittizia@pec.example.it"}, out)
        assert r["result"] == "filled", r.get("error")
        assert bench.PORTAL.fields.get(bench.IMPRESA) == "edil.fittizia@pec.example.it", f"stored {bench.PORTAL.fields}"
        assert any("Impresa esecutrice" in h["labels"] for h in r.get("hidden", [])), r.get("hidden")
        assert "edil.fittizia" not in json.dumps(r)
    case("an email ChatGPT's view hides is typed, kept, and listed as hidden for the person", hidden)

    def forbidden(out):
        bench.PORTAL.reset()
        st = bench.steps(base)
        st["sections"][1]["save"] = "Firma e invio"
        r = drive(base, st, answers, out)
        assert r["result"] == "stopped" and "refused to click" in r.get("error", ""), r
        assert not bench.PORTAL.sent, "Firma e invio was clicked"
    case("a button that is the person's step is refused", forbidden)

    def label_reader(out):
        # run.py's LABEL_JS is adapted to ChatGPT's view by a fixed replacement: a change there must change it too.
        p = subprocess.run(["node", "-e", "import(process.argv[1]).then((d) => console.log(d.adaptLabelJs(process.argv[2]).includes('__before(l, el)')))",
                            str(HERE.parent / "driver.mjs"), run.LABEL_JS], capture_output=True, text=True)
        assert p.stdout.strip() == "true", p.stderr or p.stdout
    case("run.py's label reader is the one driver.mjs adapts", label_reader)

    server.shutdown()
    print(f"{len(failed)} failed" if failed else "all passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
