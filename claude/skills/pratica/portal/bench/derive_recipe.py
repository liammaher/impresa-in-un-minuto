#!/usr/bin/env python3
"""A new SUAP rehearsal from the closest sibling's recipe: the recipe, a made-up answers file and a fixture.

    ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/bench/derive_recipe.py \\
        NEW TEMPLATE CRAWL [--fixture REHEARSAL] [--no-fill]

NEW is the rehearsal to make (rehearsals/NEW/), TEMPLATE the sibling whose recipe it copies (same operation, nearest
sector: the shops' from a shop's, the bars' from a bar's), CRAWL the stored crawl it is generated from
(catalogue/F839/sections/CRAWL.json). Written 2026-11-11 for the 33 wedge cells that had no rehearsal, and then run on the
portal in the pane (README, "The wedge's cells run on the portal"). What it changes in the copy:

- the crawl, the operation and the wizard's sector and operation labels (the crawl's `pratica` names both; a sector the
  tree repeats is `{leaf, nth}`, as bench/test_gen.py holds every SUAP recipe to), and the interventi screen as the crawl has it;
- the title and the header comment;
- it drops the template's `after:`, `slots`, `rules:`, `scelte:` and `first:`: the attachments and payment screens aren't read
  (their slots need a filled draft), the SUAP rules table has no event for a suspension or a change of people, and a second
  recipe for a case that one already holds makes route.py ambiguous. Add `rules:` by hand where the table decides a case no
  recipe holds yet;
- a `suap-common-*` crawl (advertising, public land: no sector index in its name) is taken under the wizard's sector the crawl names, and
  the template's own asks that mean nothing for another pratica are dropped (TEMPLATE_ONLY); pre-flight's "no field reads asks.X: drop it" drops the
  ask and its `yours` lines and goes again;
- the interventi screen is copied with no ticks: a crawl named `*-interventi` was taken with a tick on (the sign's SCIA), so give it `--tick`
  and delete the `scelte:` line it writes (the shop's template has none: the crawl's sections are the ticked ones). A sector-20 crawl has the
  fire-safety professional's section: its fixture wants `valerio` (`--fixture negozio-pin-2-fittizio`, answers `people: {v: valerio}`);
- the fixture is copied from --fixture (default: the template's own, else the family's: README).
Then, unless --no-fill, it generates the steps file and runs pre-flight, answering what it asks from the values the other
rehearsals use (a choice, a date, a file), up to four rounds, and prints what is left for a person: a case's own answers
(a food workshop's Reg. 852 list, a take-over's deed) and the refusals pre-flight names. Wording that names the template's
sector in a question stays: read the recipe. A draft's name is 60 characters at most ("PROVA NON INVIARE - " included).
"""
import argparse
import glob
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORTAL = HERE.parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(PORTAL))
sys.dont_write_bytecode = True

WIZARD = json.loads((PORTAL / "catalogue" / "F839" / "suap-wizard.json").read_text())["sectors"]
SHORT = {4: "panificio", 5: "laboratorio alimentare", 16: "negozio non alimentare", 17: "negozio alimentare o misto",
         18: "negozio alimentare, zone tutelate", 56: "struttura ricettiva extralberghiera", 60: "bar o ristorante", 61: "bar o ristorante, zone tutelate",
         3: "agriturismo", 10: "autoriparazione", 12: "tintolavanderia", 13: "lavanderia a gettone", 14: "impresa di pulizie",
         15: "hobbisti", 19: "media struttura fino a 400 mq", 20: "media struttura oltre 400 mq", 54: "albergo"}
FIXTURE = {4: "panificio-fittizio", 5: "panificio-fittizio", 11: "negozio-fittizio", 16: "negozio-fittizio", 17: "negozio-fittizio",
           18: "negozio-fittizio", 56: "affittacamere-fittizio", 60: "pizzeria-fittizia", 61: "ristorante-centro-storico-fittizio",
           3: "negozio-fittizio", 10: "negozio-fittizio", 12: "negozio-fittizio", 13: "negozio-fittizio", 14: "negozio-fittizio",
           15: "negozio-fittizio", 19: "negozio-fittizio", 20: "negozio-fittizio", 54: "affittacamere-fittizio"}
# A "suap-common-*" crawl (advertising, public land, ...) is taken under a sector of the wizard's tree by name, not by index.
COMMON_SHORT = {"Esercizio di somministrazione di alimenti e bevande in zone NON tutelate": "bar o ristorante"}
# What a template's own recipe asks and refuses that has nothing to do with another pratica derived from it (the sign's
# SCIA asks about a vincolo, zone A and a size; the dehors about a covered structure, the centro storico, music): left
# in, pre-flight asks them of a rimozione or a renewal (2026-11-12, 8 rehearsals derived from them).
TEMPLATE_ONLY = {"insegna-ristorante-scia-fittizio": ("insegna_vincolo", "insegna_zona_a", "insegna_grande"),
                 "dehors-fittizio": ("coperto", "centro_storico", "musica", "nuovo_852")}


def oggetto(op):
    """The draft's one-sentence subject: the operation and that it is a test, 300 characters at most (the portal's limit)."""
    tail = ": pratica di prova con dati inventati."
    return (op if len(op) + len(tail) <= 300 else op[:300 - len(tail) - 1].rstrip() + "…") + tail


def unsign(text, crawl_name, short):
    """A recipe derived from the sign's SCIA (or from a sibling that was) says "insegna" in the words the person reads: the group's
    question, the draft's default name, the first `yours` line (2026-11-16: the dry-cleaning plant's emissioni form said "per l'insegna").
    For a crawl that is not about a sign those words become the pratica's own."""
    if "insegn" in crawl_name:
        return text
    text = re.sub(r"(Qualcuna di queste voci vale per )l'insegna\?", r"\1questa pratica?", text)
    text = re.sub(r'(default: ")insegna [^"{]*(\{\{business\.denominazione\}\})', lambda m: f"{m.group(1)}{short} {m.group(2)}", text)
    text = re.sub(r'"Spunta tu le dichiarazioni sull\'insegna \([^)]*\) e le altre della pratica:', '"Spunta tu le dichiarazioni della pratica:', text)
    return text


def short_sector(sector):
    """A short Italian name for the title: the table's, else the wizard's own cut at its first parenthesis or comma (a
    sector with no entry took the hairdressers' words until 2026-11-12: a medium shop's title said "acconciatori")."""
    return re.split(r" \(|, ", sector)[0][:40].rstrip()


def _norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def operation_nth(crawl, op, idx):
    """The nth of an operation's label among the wizard's operations that share it (1 when it is the only one).

    The A.U.A. and the Emissioni in atmosfera both offer «Comunicare il piano di gestione solventi» and «Comunicazione messa in esercizio/a
    regime ...»: a plain label stopped the run on "2 nodes named ..." (2026-11-15). The crawl's `pratica` names the whole path, so its
    place among the operations that end in the same label is the nth (the wizard lists them in the page's order)."""
    wizard = json.loads((PORTAL / "catalogue" / "F839" / "suap-wizard.json").read_text())
    pool = wizard["common"] if idx is None else WIZARD[idx]["operations"]
    path = _norm(re.sub(r" \(sector .+\)$", "", re.sub(r"^SUAP: ", "", crawl["pratica"])))
    same = [x for x in pool if _norm(x.split("›")[-1]) == _norm(op)]
    if len(same) < 2:
        return 1
    for n, x in enumerate(same, 1):
        if _norm(re.sub(r"^[A-Z]+: ", "", x)) == _norm(re.sub(r"^[A-Z]+: ", "", path)):
            return n
    return 1


def wizard_answers(options):
    """The `answers:` a wizard step needs for the Si/No questions (type SIN) the crawl read on its screen: «No», as a made-up case
    has no reason for «Sì». A required one left unanswered stopped the garage's opening on «il valore e obbligatorio» (2026-11-15), and
    a recipe derived from another pratica's kept the other's question, which the 056 and 054 forms don't have («0 Si/No questions»)."""
    sins = [_norm(o["label"]) for o in options if o.get("type") == "SIN"]
    return ", answers: {%s}" % ", ".join("%s: \"No\"" % json.dumps(s, ensure_ascii=False) for s in sins) if sins else ""


def drop_asks(text, keys):
    """The recipe's ask lines named, and every `yours`/`supports` line that reads them."""
    for key in keys:
        text = re.sub(r"^  %s: \{.*\n" % re.escape(key), "", text, flags=re.M)
        text = re.sub(r"^  - .*ask\.%s\b.*\n" % re.escape(key), "", text, flags=re.M)
    return text


def derive(new, template, crawl_name, fixture=None, ticks=(), facts=None, handles=(), drop=(), also=()):
    crawl = json.loads((PORTAL / "catalogue" / "F839" / "sections" / f"{crawl_name}.json").read_text())
    m = re.search(r"› ([^›]+?) \(sector (.+)\)$", crawl["pratica"])
    if m:
        op, sector = m.group(1).strip(), m.group(2).strip()
    else:
        # A combination's crawl: "SUAP: 2 operations in one pratica: MAIN + OTHER", its sector the name's index.
        m = re.match(r"SUAP: \d+ operations in one pratica: (.+?) \+ ", crawl["pratica"])
        op, sector = m.group(1).strip(), WIZARD[int(re.match(r"suap-(\d+)", crawl_name)[1])]["sector"]
    m_idx = re.match(r"suap-(\d+)", crawl_name)
    idx = int(m_idx[1]) if m_idx else None
    if idx is not None:
        assert WIZARD[idx]["sector"] == sector, (crawl_name, sector)
        nth = sum(1 for s in WIZARD[:idx + 1] if s["sector"] == sector)
    else:
        nth = 1
    repeated = sum(1 for s in WIZARD if s["sector"] == sector) > 1 and idx is not None
    tree = '{leaf: "%s", nth: %d}' % (sector, nth) if repeated else ('"%s"' % sector if re.search(r"[:,#]", sector) else sector)
    screens = [s["screen"] for s in (crawl.get("screens") or [])]
    lines = (ROOT / "rehearsals" / template / "recipe.yaml").read_text(encoding="utf-8").split("\n")
    while lines and lines[0].startswith("#"):
        lines.pop(0)
    out, skip = [], False
    for ln in lines:
        if re.match(r"^(after|slots|rules|scelte|first):", ln) or (skip and ln[:1] in (" ", "\t")):
            skip = True
            continue
        skip = False
        out.append(ln)
    text = "\n".join(out)
    text = re.sub(r"(^#.*\n)+(?=wizard:|groups:|asks:|yours:|supports:)", "", text, flags=re.M)
    text = re.sub(r"^crawl: .*$", f"crawl: {crawl_name}", text, flags=re.M)
    text = re.sub(r"^operation: .*$", "operation: " + (json.dumps(op, ensure_ascii=False) if ":" in op else op), text, flags=re.M)
    text = re.sub(r"^(  - \{screen: Scelta settore attività, tree: )\[.*?\](, confirm: CONFERMA\})", lambda k: k[1] + "[" + tree + "]" + k[2], text, flags=re.M)
    # `also`: the other operations selected with it (a combination's crawl, `catalogue.py ops suap --combo`), by their leaf labels.
    nth_op = operation_nth(crawl, op, idx)
    first_op = json.dumps(op, ensure_ascii=False) if nth_op == 1 else '{leaf: %s, nth: %d}' % (json.dumps(op, ensure_ascii=False), nth_op)
    text = re.sub(r"^(  - \{screen: Scelta operazioni, tree: )\[.*\](, confirm: CONFERMA\})", lambda k: k[1] + "[" + ", ".join([first_op] + [json.dumps(x, ensure_ascii=False) for x in also]) + "]" + k[2], text, flags=re.M)
    # The Si/No questions of the two eventuali screens are the crawl's own, not the template's (see wizard_answers).
    scelte = next((s for s in (crawl.get("screens") or []) if s["screen"] == "scelte eventuali"), None)
    text = re.sub(r"^  - \{screen: Scelte eventuali.*\n", "  - {screen: Scelte eventuali%s, confirm: CONFERMA}\n" % wizard_answers((scelte or {}).get("options", [])), text, flags=re.M)
    text = re.sub(r"^  - \{screen: Scelta interventi eventuali.*\n", "", text, flags=re.M)
    if "scelta interventi eventuali" in screens:
        # `ticks`: the interventi's options this pratica ticks, as "label[:nth]" (a label that is the start of another's needs the nth
        # of its own: the sign's "...insegna esterna" and "...(dove è prevista la SCIA)").
        leaves = []
        for t in ticks:
            label, _, nth_ = t.partition("::")
            leaves.append('{leaf: "%s", nth: %s}' % (label, nth_ or 1))
        tree_part = ", tree: [%s]" % ", ".join(leaves) if leaves else ""
        interventi = next(s for s in crawl["screens"] if s["screen"] == "scelta interventi eventuali")
        text = text.replace("  - {screen: Scelta del destinatario della pratica", "  - {screen: Scelta interventi eventuali%s%s, confirm: CONFERMA}\n  - {screen: Scelta del destinatario della pratica" % (tree_part, wizard_answers(interventi["options"])), 1)
        if leaves:
            text = re.sub(r"^(wizard:)", "scelte: [%s]\n\\1" % ", ".join(json.dumps(t.partition("::")[0], ensure_ascii=False) for t in ticks), text, count=1, flags=re.M)
    elif ticks:
        raise SystemExit(f"{crawl_name} has no interventi screen: nothing to tick")
    # A short Italian sector name: the wizard's own is long ("Strutture ricettive extralberghiere (affittacamere, bed and ...") and a
    # title cut at 60 characters read as English to bench/test_gen.py's check of what the tecnico reads.
    text = drop_asks(text, tuple(TEMPLATE_ONLY.get(template, ())) + tuple(drop))
    text = unsign(text, crawl_name, SHORT.get(idx) or COMMON_SHORT.get(sector) or short_sector(sector))
    text = re.sub(r"^title: .*$", "title: " + json.dumps(f"{op}, {SHORT.get(idx) or COMMON_SHORT.get(sector) or short_sector(sector)}, SUAP Napoli", ensure_ascii=False), text, flags=re.M)
    header = (f"# {op} ({sector}), as gen.py writes its steps file from the batch crawl\n# (catalogue/F839/sections/{crawl_name}.json), for the made-up business of this folder's fixture.json.\n"
              f"# Derived from rehearsals/{template} (bench/derive_recipe.py): no `rules:` and no `after:`; the attachments and payment screens are not read.\n")
    if facts:
        # What the library's SUAP table needs to route a case to this file (the derived recipe has none by default: a second recipe
        # for a case one already holds makes route.py ambiguous): its fixed facts, and the other pratiche it files with it.
        text = text.rstrip("\n") + "\nrules:\n  table: suap-napoli\n  facts: {%s}\n" % facts
        if handles:
            text += "  handles: [%s]\n" % ", ".join(handles)
    folder = ROOT / "rehearsals" / new
    folder.mkdir(exist_ok=True)
    (folder / "recipe.yaml").write_text(header + text, encoding="utf-8")
    answers = {}
    for name in ("answers.json", "answers-p1.json"):
        if (ROOT / "rehearsals" / template / name).exists():
            answers = json.loads((ROOT / "rehearsals" / template / name).read_text())
            break
    if "insegn" not in crawl_name:
        # The sign's boxes (insegna_larghezza_m, progettista_insegna_cf, ...) copied from a template derived from it mean nothing to another pratica.
        answers = {k: v for k, v in answers.items() if "insegna_" not in k}
    short = re.sub(r"-fittizi[oa]$", "", new).replace("-", " ")[:28].rstrip()
    answers["descrizione"] = f"PROVA NON INVIARE - {short} generato"
    # A draft is found by its name (sectionOf, slotsOf and the person's list in Pratiche in bozza read the newest of a name):
    # the first 28 characters of two sibling rehearsals' names are often the same (2026-11-12: three pairs of 060/061 twins, and
    # the recognition forms of this round), so a taken name gets a hash of the full rehearsal name.
    taken = {json.loads(f.read_text()).get("descrizione") for f in (ROOT / "rehearsals").glob("*/answers*.json") if f.parent.name != new}
    if answers["descrizione"] in taken:
        import hashlib
        answers["descrizione"] = f"PROVA NON INVIARE - {short[:22].rstrip()} {hashlib.sha1(new.encode()).hexdigest()[:6]} generato"
    # The portal's "descrizione sintetica" takes 300 characters at most; an operation's name can be longer (the dry-cleaning plant's
    # adhesion, 2026-11-16: pre-flight refused the derived answer).
    answers["oggetto"] = oggetto(op)
    (folder / "answers.json").write_text(json.dumps(answers, ensure_ascii=False, indent=1) + "\n")
    source = fixture or (template if (ROOT / "rehearsals" / template / "fixture.json").exists() else FIXTURE.get(idx, "pizzeria-fittizia"))
    shutil.copy(ROOT / "rehearsals" / source / "fixture.json", folder / "fixture.json")
    return folder


def pool():
    values = {}
    for f in sorted(glob.glob(str(ROOT / "rehearsals" / "*" / "answers*.json"))):
        try:
            for k, v in json.loads(Path(f).read_text()).items():
                values.setdefault(k, v)
        except ValueError:
            pass
    return values


def fill(folder):
    py = sys.executable
    gen = subprocess.run([py, str(PORTAL / "gen.py"), str(folder / "recipe.yaml"), "--out", str(folder / "portal-steps.generated.yaml")], capture_output=True, text=True)
    if gen.returncode or gen.stderr.strip():
        return {"gen": (gen.stderr or gen.stdout)[-400:]}
    values = pool()
    for _ in range(8):
        r = subprocess.run([py, str(PORTAL / "run.py"), "preflight", "--made-up", "--values", str(folder / "fixture.json"), "--steps", str(folder / "portal-steps.generated.yaml"),
                            "--answers", str(folder / "answers.json")], capture_output=True, text=True)
        try:
            d = json.loads(r.stdout)
        except ValueError:
            # "steps file: no field reads asks.X: drop it": an ask the template had and this pratica doesn't read (a
            # shop's diritti on a rimozione with none, a bollo on a form with no bollo section): dropped, and again.
            unused = re.findall(r"no field reads asks\.(\w+)", r.stdout + r.stderr)
            if unused:
                recipe = folder / "recipe.yaml"
                recipe.write_text(drop_asks(recipe.read_text(encoding="utf-8"), unused), encoding="utf-8")
                gen = subprocess.run([py, str(PORTAL / "gen.py"), str(recipe), "--out", str(folder / "portal-steps.generated.yaml")], capture_output=True, text=True)
                if gen.returncode or gen.stderr.strip():
                    return {"gen": (gen.stderr or gen.stdout)[-400:]}
                continue
            return {"preflight": (r.stdout + r.stderr)[-400:]}
        answers = json.loads((folder / "answers.json").read_text())
        added = False
        for q in d["questions"]:
            if q["key"] not in answers and q["key"] in values:
                answers[q["key"]], added = values[q["key"]], True
        for p in d["proposals"]:
            if p.get("key") and p["key"] not in answers and (p.get("key") in values or "value" in p):
                answers[p["key"]], added = p.get("value", values.get(p["key"])), True
        if not added:
            # `errors`: an answer the pool gave that the form refuses (a protocol number over 10 characters, 2026-11-13): the pool's first value is
            # another rehearsal's, so a question still asked with an error needs its own.
            return {"ready": d["ready"], "unsupported": d["unsupported"], "questions": [q["key"] for q in d["questions"]], "proposals": [p.get("key") for p in d["proposals"]],
                    "errors": [[q["key"], q["error"]] for q in d["questions"] if q.get("error")],
                    "files": [f["for"] for f in d["files"] if not f["exists"]]}
        (folder / "answers.json").write_text(json.dumps(answers, ensure_ascii=False, indent=1) + "\n")
    return {"ready": False, "note": "still asking after eight rounds"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("new")
    ap.add_argument("template")
    ap.add_argument("crawl")
    ap.add_argument("--fixture", help="the rehearsal whose fixture.json the new one copies")
    ap.add_argument("--no-fill", action="store_true")
    ap.add_argument("--tick", action="append", default=[], metavar="LABEL[::NTH]", help="an «interventi eventuali» option to tick (repeat)")
    ap.add_argument("--drop-ask", action="append", default=[], help="an ask of the template this pratica no longer asks (the music, once its tick is ticked)")
    ap.add_argument("--also", action="append", default=[], help="another operation selected with the main one (its leaf label); repeat")
    ap.add_argument("--facts", help="the rules block's fixed facts, as YAML flow: 'attivita: somministrazione, evento: trasferimento'")
    ap.add_argument("--handles", help="the library procedures it files besides the main one, comma-separated (rules.handles)")
    a = ap.parse_args()
    folder = derive(a.new, a.template, a.crawl, a.fixture, a.tick, a.facts, [h for h in (a.handles or "").split(",") if h], a.drop_ask, a.also)
    print(f"wrote {folder.relative_to(ROOT)}: recipe.yaml, answers.json, fixture.json")
    print("then: add it to catalogue/F839/suap-unrouted.yaml with its reason unless route.py reaches it (bench/test_route.py fails otherwise), regen.py, a bundle")
    if not a.no_fill:
        print(json.dumps(fill(folder), ensure_ascii=False))


if __name__ == "__main__":
    main()
