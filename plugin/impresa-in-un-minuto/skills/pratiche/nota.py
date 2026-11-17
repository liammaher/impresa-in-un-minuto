#!/usr/bin/env python3
"""A file of the details no document holds, for the tecnico to fill in, and back into the job's files.

  nota.py template PREFLIGHT.json --out FILE --map MAP.json [--pratica "CILA"]
  nota.py read FILE --map MAP.json --studio STUDIO.json --values VALUES.json

`template` reads the `missing` of a saved pre-flight (`run.py preflight ... > run/preflight.json`)
and writes FILE, a plain text file: a numbered line for each detail, by the person it belongs to,
the portal's own label before an `=` the tecnico writes after. MAP.json (numbers to field ids)
stays with the runner's files. `read` takes the filled file back: each value is held to the same
checks as check.py's (a codice fiscale, a date, a provincia), the studio's and the tecnico's go
into STUDIO.json and the others into VALUES.json, and what is still empty or wrong is printed,
by its label (never a field id). Values never reach the screen.

Why: with a folder that holds a few documents, 60 details asked in a chat message are a wall;
in a file they are a form, filled once, kept for the next job.
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import check  # noqa: E402

# The runner's own grouping of a missing detail (whose it is, the portal's label): the plugin has
# it beside this file, the repository in claude/skills/pratica.
REPO = HERE.parents[3] if len(HERE.parents) > 3 else HERE
for _portal in (HERE / "portal", REPO / "claude" / "skills" / "pratica" / "portal"):
    if (_portal / "run.py").is_file():
        sys.path.insert(0, str(_portal))
        break
import run  # noqa: E402

LINE = re.compile(r"^\s*(\d+)\.\s+(.*)$")
HEADER = """Dati per «{pratica}» che non stanno nei documenti.
Scrivi il valore dopo il segno «=» di ogni riga, salva il file e scrivimi «fatto».
Date come 05/03/1980; sesso M o F; provincia con la sigla (NA). Lascia vuoto ciò che non hai.
Le righe della prima parte sono tue e dello studio: non cambiano da una pratica all'altra.
Non scrivere mai password o PIN."""


def clean(label):
    return re.sub(r"\s+", " ", label.replace("=", "-")).strip()


OWN_HEADING = "Tuoi e dello studio"


def slug_of(fid):
    return fid.split(":", 1)[0] if ":" in fid else ""


def template(pre, pratica):
    """(text, map) for a pre-flight's missing details. A row with no `id` (a document that expired,
    a value longer than its box) names a value that is already there: it stays in the chat."""
    groups, seen = {}, set()
    for m in pre.get("missing", []):
        fid = m.get("id")
        if not fid or m["field"].startswith("*:") or fid in seen:
            continue  # nobody is the titolare yet: the skill seeds studio.json, never the tecnico
        seen.add(fid)
        label = clean(run.missing_label(m["for"]))
        if m["why"] != "empty in the vault":
            label += " (da correggere)"
        who = run.whose_of(m["field"])
        groups.setdefault(OWN_HEADING if who == run.OWN else who, []).append((fid, label))
    order = [OWN_HEADING] + [w for w in run.WHOSE_ORDER if w != run.OWN]
    lines, items, n = [HEADER.format(pratica=pratica)], [], 0
    for who in sorted(groups, key=order.index):
        lines += ["", f"== {who} =="]
        counts = {}
        for _, label in groups[who]:
            counts[label] = counts.get(label, 0) + 1
        again = {}
        for fid, label in groups[who]:
            n += 1
            again[label] = again.get(label, 0) + 1
            # The portal repeats some labels (two firms, two addresses): the person's name in the id
            # tells them apart, else their order.
            shown = label
            if counts[label] > 1:
                shown = f"{label} ({slug_of(fid) or again[label]})"
            lines.append(f"{n}. {shown} =")
            items.append({"n": n, "id": fid, "label": shown})
    return "\n".join(lines) + "\n", {"items": items}


def is_studio(fid):
    return ":" not in fid or fid.startswith("tecnico:")


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


PROBLEMS = [  # check.py's reasons are English and carry the value: the tecnico gets one plain Italian phrase
    (re.compile(r"codice fiscale|check (digit|character)|invalid (day|month)", re.I), "codice fiscale o partita IVA non valido"),
    (re.compile(r"date", re.I), "una data, come 05/03/1980"),
    (re.compile(r"CAP", re.I), "il CAP ha 5 cifre"),
    (re.compile(r"provincia", re.I), "la sigla della provincia, 2 lettere (NA)"),
    (re.compile(r"sex", re.I), "M o F"),
    (re.compile(r"not one of", re.I), "un valore tra quelli previsti"),
    (re.compile(r"password|PIN", re.I), "mai password o PIN in questo file"),
]


def problem_text(problem):
    return next((it for rx, it in PROBLEMS if rx.search(problem)), "valore non valido")


def decode(raw):
    """A form as an editor saved it: UTF-8 (with or without a BOM), UTF-16 (Notepad's «Unicode»), else Windows-1252."""
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", "replace")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", "replace")


def read(text, mapping, studio, job, schema):
    """(studio, job, filled, empty, problems): the two files updated with each value that holds. A
    value goes to one file only, whichever it was in before."""
    by_n = {i["n"]: i for i in mapping["items"]}
    given = {}
    for raw in text.splitlines():
        m = LINE.match(raw)
        if m and int(m[1]) in by_n and "=" in m[2]:
            given[int(m[1])] = m[2].split("=", 1)[1].strip()
    filled, empty, problems = 0, [], []
    for n, item in by_n.items():
        value = given.get(n, "")
        if not value:
            empty.append(item["label"])
            continue
        out, bad = check.check({item["id"]: value}, schema)
        if bad:
            problems.append(f"{item['label']}: {problem_text(bad[0])}")
            continue
        here, other = (studio, job) if is_studio(item["id"]) else (job, studio)
        here[item["id"]] = out[item["id"]]
        other.pop(item["id"], None)
        filled += 1
    return studio, job, filled, empty, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("template")
    t.add_argument("preflight", type=Path)
    t.add_argument("--out", type=Path, required=True)
    t.add_argument("--map", type=Path, required=True)
    t.add_argument("--pratica", default="questa pratica")
    r = sub.add_parser("read")
    r.add_argument("file", type=Path)
    r.add_argument("--map", type=Path, required=True)
    r.add_argument("--studio", type=Path, required=True)
    r.add_argument("--values", type=Path, required=True)
    a = ap.parse_args()
    if a.cmd == "template":
        text, mapping = template(json.loads(a.preflight.read_text(encoding="utf-8")), a.pratica)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.map.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text, encoding="utf-8")
        a.map.write_text(json.dumps(mapping, indent=1, ensure_ascii=False))
        print(f"{len(mapping['items'])} dati da compilare in {a.out.name}")
        return 0
    schema = json.loads(check.SCHEMA.read_text()) if check.SCHEMA.is_file() else \
        json.loads((REPO / "schema.json").read_text())
    studio, job, filled, empty, problems = read(decode(a.file.read_bytes()), json.loads(a.map.read_text(encoding="utf-8")),
                                                load(a.studio), load(a.values), schema)
    studio.setdefault("tecnico:ruolo.tipo", "titolare")  # without it pre-flight lists none of the tecnico's details
    a.studio.write_text(json.dumps(studio, indent=1, ensure_ascii=False), encoding="utf-8")
    a.values.write_text(json.dumps(job, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Letti {filled} dati.")
    if empty:
        print(f"Ancora vuoti ({len(empty)}): " + "; ".join(empty))
    for p in problems:
        print(f"Da correggere, {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
