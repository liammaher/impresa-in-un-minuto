#!/usr/bin/env python3
"""derive_recipe.py offline: what it checks about a template and what it answers for itself, each learned on the real portal.

  ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/bench/test_derive.py

No browser, vault or network. 2026-11-20 (round 17, the four rehearsals round 16 had derived and left):

  - the template is picked by the crawl's sections, not by the sector's name: sector 06's move and structural variations
    are the shop's forms, and derived from the bakery's and the workshop's recipes they asked about a bakery and for a
    Reg. 852 list nobody had; `closer_siblings` names the rehearsal of the same operation whose crawl is closer;
  - a checklist answer the form refuses is cut to the keys it offers (`attivita_852` was another form's list, in the template's
    own answers and in the pool, and the form refused it);
  - `ready: false` with no question is pre-flight's `missing`: sector 20's fire-safety professional (`v:` fields) is
    `valerio` of the PIN 2 fixture, and nothing else is filled in silently;
  - 2026-11-20 (the 14 Reg. 852 and GISA notices): a template of another form brings its own claims. The `yours` line of attachments,
    and of declarations, are made from what the new crawl shows; the asks that only refuse are listed for the person to keep or drop.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import derive_recipe as dr  # noqa: E402

REH = HERE.parents[4] / "rehearsals"
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


@case("sector 06's move derived from a workshop's recipe: the shop's recipe is named as the closer template")
def _():
    names = [n for _, n in dr.closer_siblings("trasferimento-laboratorio-fittizio", "suap-006-trasferire-la-sede-dell-attivita")]
    assert "trasferimento-alimentari-fittizio" in names, names


@case("sector 06's structural variations derived from the bakery's recipe: the shop's enlargement is named")
def _():
    names = [n for _, n in dr.closer_siblings("variazione-strutturale-panificio-fittizio", "suap-006-variazioni-strutturali")]
    assert "ampliamento-alimentari-fittizio" in names, names


@case("a template on the crawl's own sections draws no warning, and never names itself")
def _():
    assert dr.closer_siblings("trasferimento-alimentari-fittizio", "suap-017-trasferire-la-sede-dell-attivita") == []
    assert "trasferimento-alimentari-fittizio" not in [n for _, n in dr.closer_siblings("trasferimento-alimentari-fittizio", "suap-006-trasferire-la-sede-dell-attivita")]


@case("a template with another operation's crawl is not compared with (only the same operation's siblings are suggested)")
def _():
    for score, name in dr.closer_siblings("variazione-strutturale-panificio-fittizio", "suap-006-variazioni-strutturali"):
        assert dr.rehearsal_crawl(name)[1] == "Variazioni strutturali", name


ASK = {"key": "attivita_852", "type": "checklist", "items": [{"key": "ristorazione"}, {"key": "forno"}]}


@case("a pooled checklist keeps only the keys the question offers")
def _():
    assert dr.pooled(ASK, {"attivita_852": ["forno", "pane", "dettaglio_alimenti"]}) == ["forno"]


@case("a pooled checklist with no key the question offers is left to the person, not answered with []")
def _():
    assert dr.pooled(ASK, {"attivita_852": ["pane"]}) is None
    assert dr.pooled(ASK, {}) is None


@case("a pooled answer to any other question is the pool's, as it was")
def _():
    assert dr.pooled({"key": "diritti_euro", "type": "number"}, {"diritti_euro": "96"}) == "96"


@case("a checklist answer the form refuses is cut to the keys it offers (the template's own answers carried another form's list)")
def _():
    assert dr.narrowed(ASK, ["forno", "pane"]) == ["forno"]
    assert dr.narrowed(ASK, ["forno"]) is None  # nothing to change
    assert dr.narrowed(ASK, ["pane"]) is None  # nothing left: the person's
    assert dr.narrowed({"key": "x", "type": "number"}, "5") is None


MISSING = [{"id": "v:identity.last_name"}, {"id": "v:albo.numero"}]
PIN2 = (REH / "negozio-pin-2-fittizio" / "fixture.json").read_text()
WORKSHOP = (REH / "laboratorio-alimentare-fittizio" / "fixture.json").read_text()


@case("only the fire-safety professional missing, and the fixture has valerio: the role goes to him")
def _():
    assert dr.people_fix({"missing": MISSING}, {}, PIN2) == {"v": "valerio"}


@case("anything else missing, a fixture without valerio, or people already answered: nothing is filled in")
def _():
    assert dr.people_fix({"missing": MISSING + [{"id": "carmela:residenza.cap"}]}, {}, PIN2) is None
    assert dr.people_fix({"missing": MISSING}, {}, WORKSHOP) is None
    assert dr.people_fix({"missing": MISSING}, {"people": {"v": "carmela"}}, PIN2) is None
    assert dr.people_fix({"missing": []}, {}, PIN2) is None


def crawl(name):
    return json.loads((dr.CRAWLS / f"{name}.json").read_text())


LINE = ('  - "Spunta tu le dichiarazioni: la casella di presa d\'atto sotto la PEC, consapevolezza (artt. 46-47), informativa privacy, '
        'norme del Comune di Napoli (normative comunali), requisiti di onorabilità e professionali, altre dichiarazioni, art. 75 DPR 445/2000"\n')


@case("the declarations line names this crawl's declarations, drops the template's others, keeps an observed detail")
def _():
    out = dr.declarations_line(LINE, crawl("suap-060-presentare-l-aggiornamento-della-registrazione-imp"))  # the Reg. 852 take-over notification
    assert out == ('  - "Spunta tu le dichiarazioni: consapevolezza (artt. 46-47), informativa privacy, art. 6 Reg. 852/2004, tasse comunali, '
                   'la casella di presa d\'atto sotto la PEC"\n'), out


@case("a crawl with the Comune's normative section keeps it in the declarations line; a recipe with no such line is untouched")
def _():
    names = dr.declaration_labels(crawl("suap-060-subentrare-nell-esercizio-dell-attivita"))
    assert "norme del Comune di Napoli (normative comunali)" in names, names
    assert dr.declarations_line("yours:\n  - \"Firma e invia\"\n", crawl("suap-060-cessare-l-attivita")) == "yours:\n  - \"Firma e invia\"\n"


@case("a template's own list of attachments becomes the generic line (the attachments screen isn't read)")
def _():
    text = 'yours:\n  - "Paga i diritti"\n  - "Allega, firmate con la tua firma digitale (.p7m): la planimetria quotata dei locali e la ricevuta della tariffa ASL"\n  - "Firma e invia"\n'
    out = dr.generic_attachments(text)
    assert "planimetria" not in out and dr.GENERIC_ATTACHMENTS in out and out.count("Allega") == 1, out
    assert dr.generic_attachments(out) == out  # idempotent


@case("asks that only refuse are listed: the bakery's ovens, flour, basements and sign, not the diritti or the name the draft reads")
def _():
    import subprocess
    import tempfile
    out = Path(tempfile.mkdtemp()) / "steps.yaml"
    r = subprocess.run([sys.executable, str(dr.PORTAL / "gen.py"), str(REH / "variazione-strutturale-panificio-fittizio" / "recipe.yaml"), "--out", str(out)],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-300:]
    only = dr.refusal_only_asks(out.read_text())
    assert {"caldaia", "farina", "sotterraneo", "insegna_esterna"} <= set(only), only
    assert "diritti_euro" not in only and "descrizione" not in only, only


@case("a group left with no ask under it is dropped with the asks (the centro storico opening's Piano group in a notification)")
def _():
    text = ('groups:\n  extras:\n    question: "Qualcuna?"\n  piano:\n    question: "I requisiti del Piano"\nasks:\n'
            '  alcolici: {group: extras, type: yes_no, item: "Alcolici"}\n  accessibile: {group: piano, type: yes_no, item: "Accessibile"}\n'
            '  punteggio: {group: piano, type: yes_no, item: "Punteggio"}\nyours:\n  - "x"\n')
    out = dr.drop_asks(text, ("accessibile", "punteggio"))
    assert "piano" not in out and "extras" in out and "alcolici" in out, out
    assert dr.drop_asks(text, ("accessibile",)) == text.replace("  accessibile: {group: piano, type: yes_no, item: \"Accessibile\"}\n", "")  # one ask left: the group stays


print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
