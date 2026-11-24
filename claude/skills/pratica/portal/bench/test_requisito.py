#!/usr/bin/env python3
"""Who holds the professional requirement, when it isn't the one declaring (README «Round 31»), offline.

  ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/bench/test_requisito.py

No browser, vault or network. The acconciatore's and estetista's «che il/i Responsabile/i tecnico/i è/sono:» and the tatuatore's two
declarations read the other person from the vault as the role `q:` (answers.json people): surname, name, codice fiscale, birth and
residence from `identity` and `residenza`, «in qualità di» and the rapporto di lavoro from `ruolo.tipo`. A case that names nobody, a
person with no surname, or both of the form's radios (it takes one) is refused, and a case that never names someone else is unchanged.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.dont_write_bytecode = True
import gen  # noqa: E402
import run  # noqa: E402

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


def load(rehearsal, answers, drop=(), **over):
    """(steps, values) of one rehearsal's case, on its own fixture, with the answers changed by `over` (None drops a key)."""
    d = REH / rehearsal
    steps = gen.generate(gen.load_yaml(d / "recipe.yaml"))
    a = json.loads((d / answers).read_text())
    for k in drop:
        a.pop(k, None)
    for k, v in over.items():
        a.pop(k, None) if v is None else a.__setitem__(k, v)
    fields = dict(json.loads((d / "fixture.json").read_text())["fields"])
    return steps, run.Values(a, fields=fields, asks=steps.get("asks"))


def preflight(rehearsal, answers, **over):
    steps, values = load(rehearsal, answers, **over)
    return run.preflight(steps, values, made_up=True)


def plan_of(rehearsal, answers, **over):
    steps, values = load(rehearsal, answers, **over)
    return run.plan(steps, values)


def box(plan, section, label, nth=0):
    rows = [p for p in plan if p["section"].startswith(section) and p["label"] == label]
    return rows[nth]["value"]


HAIR = ("acconciatore-senza-procura-fittizio", "answers-requisito-dipendente.json")
BEAUTY = ("estetista-fittizio", "answers-requisito-socio.json")
TATTOO = ("tatuatore-apertura-fittizio", "answers-requisito-socio.json")
TATTOO2 = ("tatuatore-apertura-fittizio", "answers-requisito-dipendente.json")
HAIRSEC = "Dichiarazione sul possesso dei requisiti professionali (attività di acconciatore)"


@case("«in qualità di» comes from ruolo.tipo: titolare, socio, dipendente; the rest is asked (familiare coadiuvante has no vault ruolo)")
def _():
    f = run.FILTERS["requisito_qualita"]
    assert f("titolare") == "Titolare" and f("socio") == "Socio partecipante al lavoro" and f("dipendente") == "Dipendente"
    assert f("socio,amministratore") == "Socio partecipante al lavoro" and f("dipendente, responsabile_tecnico") == "Dipendente"
    assert f("titolare,legale_rappresentante") == "Titolare"
    for none in ("legale_rappresentante", "responsabile_tecnico", "collaboratore", "amministratore", "altro", ""):
        assert f(none) is None, none
    g = run.FILTERS["rapporto_lavoro"]
    assert g("socio,amministratore") == "socio" and g("collaboratore") == "collaboratore" and g("dipendente") == "dipendente"
    assert g("legale_rappresentante") is None


@case("the holder check refuses only when someone else holds the requirement and the case names nobody")
def _():
    f = run.FILTERS["requisito_holder"]
    assert f("true/Fittizio") == "true" and f("false/") == "true" and f("/") == "true"
    assert f("true/") == "false" and f("true/  ") == "false"


@case("the hairdresser: the other person's surname, name and ruolo, the Allegato B file; the applicant's own boxes stay unticked")
def _():
    r = preflight(*HAIR)
    assert r["ready"] and not r["unsupported"] and not r["missing"], r
    plan = plan_of(*HAIR)
    assert box(plan, HAIRSEC, "Cognome") == "Fittizio" and box(plan, HAIRSEC, "Nome") == "Quinto"
    assert box(plan, HAIRSEC, "in qualità di") == "Dipendente"
    labels = [p["label"] for p in plan if p["section"] == HAIRSEC]
    assert "che il/i Responsabile/i tecnico/i è/sono:" in labels and "di essere Responsabile tecnico" not in labels, labels
    assert box(plan, HAIRSEC, "Tipologie ammesse").endswith("allegato-b-quinto.pdf")


@case("«in qualità di» is proposed from the person's ruolo, to confirm")
def _():
    r = preflight(*HAIR, tipo_qualita_responsabile_tecnico=None)
    assert [p["key"] for p in r["proposals"]] == ["tipo_qualita_responsabile_tecnico"], r["proposals"]
    assert r["proposals"][0]["proposal"] == "Dipendente" and not r["ready"]
    # a ruolo that says nothing (a legale rappresentante) leaves the question, with no proposal
    steps, values = load(*HAIR, tipo_qualita_responsabile_tecnico=None)
    values.fields["quinto:ruolo.tipo"] = "legale_rappresentante"
    r = run.preflight(steps, values, made_up=True)
    assert [q["key"] for q in r["questions"]] == ["tipo_qualita_responsabile_tecnico"] and not r["proposals"], r


@case("hairdresser and beautician: no `q` person, a `q` that is nobody, or no surname: refused, and the message says where the person goes")
def _():
    for rehearsal, answers in (HAIR, BEAUTY):
        for over in ({"people": None}, {"people": {"q": "nessuno"}}):
            r = preflight(rehearsal, answers, **over)
            assert not r["ready"] and len(r["unsupported"]) == 1 and "lettera q" in r["unsupported"][0], (rehearsal, over, r["unsupported"])
        steps, values = load(rehearsal, answers)
        slug = values.answers["people"]["q"]
        values.fields[f"{slug}:identity.last_name"] = ""
        r = run.preflight(steps, values, made_up=True)
        assert not r["ready"] and "lettera q" in r["unsupported"][0], r["unsupported"]


@case("hairdresser and beautician: the form takes one of its two radios, so both true (and both false) are refused")
def _():
    for rehearsal, answers in (HAIR, BEAUTY):
        for rt, multi in (("true", "true"), ("false", "false")):
            r = preflight(rehearsal, answers, responsabile_tecnico=rt, multi_responsabili_tecnici=multi)
            assert not r["ready"] and any("una sola delle due" in u for u in r["unsupported"]), (rehearsal, rt, multi, r["unsupported"])


@case("the beautician: a holder who is the person declaring is unchanged (no `q` needed), the other holder fills Cognome, Nome, qualità, tick, file")
def _():
    own = preflight("estetista-fittizio", "answers.json")
    assert own["ready"] and not own["unsupported"], own
    plan = plan_of(*BEAUTY)
    sec = "Dichiarazione sul possesso dei requisiti professionali (attività di estetista)"
    assert box(plan, sec, "Cognome") == "Fittizia" and box(plan, sec, "Nome") == "Quirina"
    assert box(plan, sec, "in qualità di") == "Socio partecipante al lavoro"
    assert box(plan, sec, "Tipologie ammesse").endswith("allegato-c-quirina.pdf")
    assert "di essere Responsabile tecnico" not in [p["label"] for p in plan if p["section"] == sec]


@case("the tatuatore: the person's identity and residence fill the declaration, both attestati, the REA by its radio")
def _():
    r = preflight(*TATTOO)
    assert r["ready"] and not r["unsupported"] and not r["missing"], r
    plan = plan_of(*TATTOO)
    s1 = "DICHIARAZIONE RELATIVA AI REQUISITI PROFESSIONALI"
    got = {p["label"]: p["value"] for p in plan if p["section"].startswith(s1) and p["label"] in ("cognome", "nome", "codice fiscale", "data di nascita", "cittadinanza", "Stato")}
    assert got["cognome"] == "Fittizio" and got["nome"] == "Tullio" and got["codice fiscale"] == "FTTTLL85D12F839J", got
    assert got["data di nascita"] == "12/04/1985" and got["Stato"] == "Italia", got
    assert [p["label"] for p in plan if p["section"].startswith(s1) and p["kind"] == "checkbox"] == ["socio"]
    assert [p["label"] for p in plan if p["section"].startswith(s1) and p["kind"] == "radio"] == ["M"]
    assert box(plan, s1, "Comune", 0) == "Napoli" and box(plan, s1, "Provincia", 1) == "NA" and box(plan, s1, "C.A.P.") == "80127"
    assert box(plan, s1, "con il numero identificativo:", 0) == "CAM-2019-0001"
    assert box(plan, s1, "In possesso di attestato di frequenza di corso abilitante all’attività di tatuatore/percing organizzato dall’ASL di") == "Napoli 1 Centro (inventata)"
    assert box(plan, s1, "con il numero identificativo:", 1) == "ASL-2021-0002", "both attestati are filled: the portal wants both"
    s2 = "dichiarazione di qualifica professionale del responsabile tecnico"
    assert box(plan, s2, "Sig./sig.a") == "Tullio Fittizio" and box(plan, s2, "che nei confronti dell'impresa ha il seguente rapporto di lavoro") == "socio"
    assert box(plan, s2, "numero REA") == "123456789" and box(plan, s2, "in data") == "14/02/2018"
    steps, _ = load(*TATTOO)
    sec = next(s for s in steps["sections"] if s["section"] == s2)
    assert {(f.get("nth", 1), f["when"].split("|")[-1].strip("}")) for f in sec["fields"] if f["label"] == "in data"} == {(1, "is_iscritto"), (2, "is_domanda")}
    assert "Ha presentato domanda di iscrizione al REA" not in [p["label"] for p in plan if p["section"] == s2]


@case("the tatuatore's other person: the third checkbox, F, her own attestati, a REA application with no number")
def _():
    plan = plan_of(*TATTOO2)
    s1 = "DICHIARAZIONE RELATIVA AI REQUISITI PROFESSIONALI"
    assert [p["label"] for p in plan if p["section"].startswith(s1) and p["kind"] == "checkbox"] == ["familiare coadiuvante/ collaboratore/ dipendende dell'impresa"]
    assert [p["label"] for p in plan if p["section"].startswith(s1) and p["kind"] == "radio"] == ["F"]
    assert box(plan, s1, "Rilasciato in data:") == "18/06/2021" and box(plan, s1, "con il numero identificativo:", 0) == "CAM-2020-0007"
    s2 = "dichiarazione di qualifica professionale del responsabile tecnico"
    labels = [p["label"] for p in plan if p["section"] == s2]
    assert "Ha presentato domanda di iscrizione al REA" in labels and "numero REA" not in labels
    dates = [p for p in plan if p["section"] == s2 and p["label"] == "in data"]
    assert len(dates) == 1 and dates[0]["value"] == "20/10/2026", "the REA application's date is the second «in data» box"


@case("the tatuatore with no `q`: each choice refused on its own; with neither choice the pratica is the opening as it was")
def _():
    for over in ({"tat_conduzione_rt": "false"}, {"tat_altri_qualificati": "false"}):
        r = preflight(*TATTOO, **over, people=None)
        assert not r["ready"] and len(r["unsupported"]) == 1 and "lettera q" in r["unsupported"][0], (over, r["unsupported"])
    plain = preflight("tatuatore-apertura-fittizio", "answers.json")
    assert plain["ready"] and not plain["unsupported"]
    # the two sections stay in the steps behind their choice, and add nothing to the plan
    assert not [p for p in plan_of("tatuatore-apertura-fittizio", "answers.json") if "REQUISITI PROFESSIONALI" in p["section"] or "responsabile tecnico" in p["section"]]


@case("the person declaring is still found when the other holder is a titolare too (a `q` the job names is not the declarant)")
def _():
    for rehearsal, answers in (HAIR, BEAUTY):
        steps, values = load(rehearsal, answers, tipo_qualita_responsabile_tecnico=None)
        slug = values.answers["people"]["q"]
        for ruolo, option in (("titolare", "Titolare"), ("legale_rappresentante,socio", "Socio partecipante al lavoro")):
            values.fields[f"{slug}:ruolo.tipo"] = ruolo
            values.cache.clear()
            r = run.preflight(steps, values, made_up=True)
            assert not r["missing"], (ruolo, r["missing"])
            assert [p["proposal"] for p in r["proposals"]] == [option], (ruolo, r["proposals"])
            assert values.titolare == "carmela", values.titolare
    # without a `q` in people the two would be ambiguous, as before
    steps, values = load(*HAIR, people=None)
    values.fields["quinto:ruolo.tipo"] = "titolare"
    try:
        values.titolare
    except run.StepError as e:
        assert "want one titolare" in str(e)
    else:
        raise AssertionError("two titolari and no `t` must still be refused")


@case("a recipe with its own wizard that names a scelte no screen ticks is refused by gen.py (the tatuatore's draft had the base's 17 sections, 2026-11-23)")
def _():
    recipe = gen.load_yaml(REH / "tatuatore-apertura-fittizio" / "recipe.yaml")
    assert gen.generate(dict(recipe))["wizard"][-1]["tree"], "the recipe ticks both"
    broken = dict(recipe, wizard=[{k: v for k, v in w.items() if k != "tree"} if w["screen"] == "Scelte eventuali" else w for w in recipe["wizard"]])
    try:
        gen.generate(broken)
    except gen.GenError as e:
        assert "ticks" in str(e) and "nella conduzione dell'attività partecipano" in str(e), e
    else:
        raise AssertionError("a scelta nobody ticks must be refused")
    # a Si/No screen that answers it by its label is a tick too
    si_no = dict(recipe, wizard=[dict(w, answers={s["option"]: "Sì" for s in recipe["scelte"]}) if w["screen"] == "Scelte eventuali" else w for w in broken["wizard"]])
    gen.generate(si_no)


@case("the tatuatore wants BOTH attestati: any one of the eight answers missing is a question, never a run that stops on the portal's «il valore e obbligatorio» (2026-11-23)")
def _():
    keys = ("tat_corso_ente", "tat_corso_data", "tat_corso_regione", "tat_corso_regione_data", "tat_corso_numero", "tat_asl_ente", "tat_asl_data", "tat_asl_numero")
    rehearsal, answers = TATTOO
    assert preflight(rehearsal, answers)["ready"]
    for k in keys:
        r = preflight(rehearsal, answers, **{k: None})
        assert not r["ready"] and [q["key"] for q in r["questions"]] == [k], (k, r["questions"])


@case("the tatuatore's name limits are the form's: a surname of 26 characters is a missing detail naming the limit, not a run that stops on the portal (2026-11-23)")
def _():
    def missing(n):  # a fresh load each time: a pre-flight leaves its asked questions on the values
        steps, values = load(*TATTOO)
        values.fields[f"{values.answers['people']['q']}:identity.last_name"] = "X" * n
        r = run.preflight(steps, values, made_up=True)
        return r["ready"], [m["why"].split(": ", 1)[1] for m in r["missing"]]
    assert missing(23) == (True, [])
    # «Tullio » + the surname is the «Sig./sig.a» box (30); the declaration's own cognome box takes 25
    assert missing(24) == (False, ["Sig./sig.a takes at most 30 characters"])
    assert missing(26) == (False, ["cognome takes at most 25 characters", "Sig./sig.a takes at most 30 characters"])


@case("the missing details of `q` are named as theirs, not the tecnico's")
def _():
    assert run.whose_of("q:identity.last_name") == "Di chi ha il requisito professionale al posto tuo"
    assert run.whose_of("v:identity.last_name") == "Del professionista antincendio"


print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
