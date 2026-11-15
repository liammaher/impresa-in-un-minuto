#!/usr/bin/env python3
"""The SUAP's openings, moves and take-overs with an outside sign and/or the acoustic nulla osta ticked: each a rehearsal
derived from its plain sibling (bench/derive_recipe.py) plus the sign's asks, refusals and answers, taken from the
restaurant's (rehearsals/ristorante-insegna-fittizio), with the `rules:` block the library's SUAP table routes it by.

    ~/.cache/pratica-portal/venv/bin/python claude/skills/pratica/portal/bench/derive_combos.py [NAME ...]

Written 2026-11-13, after the wizard's pairs probe (catalogue/F839/suap-pairs.md): the sign and the acoustic notice are
ticks of the «interventi eventuali» screen, whose sections the pratica borrows from the crawls taken with the tick
(gen.py `borrowed`). No NAME: every combination below. The attachments and payment screens are not read (derive_recipe.py).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import derive_recipe as dr  # noqa: E402

ROOT = dr.ROOT
ASL = "napoli/asl-napoli-1/registrazione-attivita-alimentare"
INS = "napoli/comune/insegna-esercizio"
NO = "napoli/comune/nulla-osta-impatto-acustico"
SIGN = "in caso di attività che preveda insegna esterna"
NULLA = ("richiede il rilascio del Nulla osta impatto acustico, in caso di utilizzo di impianti di diffusione sonora o di manifestazioni ed "
         "eventi con diffusione di musica o utilizzo di strumenti musicali, se si superano le soglie della zonizzazione comunale")
VVF = "napoli/vigili-del-fuoco/scia-prevenzione-incendi"
PIN2_OP = "PIN 2 - Segnalazione Certificata di Inizio Attività"  # the fire prevention's SCIA (VV.F.) as a second operation
PIN2_DONOR = "cila-fittizia"  # whose fixture-p6.json has the made-up professional `valerio`
# The made-up fire prevention case: a category A activity, new, standard approach, one electrical certificate; the professional is a person
# of their own (role `v`), never the titolare (the asseverazione is theirs: dictionary/fnsuap.yaml `vvf_*`).
PIN2_ANSWERS = {"vvf_attivita": "ristorante", "vvf_categoria": "a", "vvf_allegato": "69 _ 1 _ A", "vvf_stato": "nuova", "vvf_modifica": "false",
                "vvf_parziale": "false", "vvf_pnrr": "false", "vvf_impianti_speciali": "false", "vvf_approccio": "standard", "vvf_fotovoltaico": "false", "vvf_importo": "90",
                "vvf_versamento_numero": "0000123456", "vvf_versamento_data": "2026-10-15", "vvf_doc_atti": "1 4", "vvf_doc_strutture": "0",
                "vvf_doc_prodotti": "0", "vvf_doc_imp1": "1 0 0", **{f"vvf_doc_imp{i}": "0 0 0" for i in range(2, 9)}, "vvf_doc_altri": "0"}
PIN2_YOURS = ("Il professionista antincendio firma tu o per lui, con la sua firma digitale, l'asseverazione e le dichiarazioni dei Vigili del Fuoco: "
              "il portale le fa firmare al professionista, non al titolare",
              "Paga ai Vigili del Fuoco la tariffa della categoria (€ {{ask.vvf_importo}}) e allega la copia del versamento firmata digitalmente (.p7m)")
PIN2_SUPPORTS = (
    '  - {when: "{{ask.vvf_parziale|not}}", else: "Una SCIA antincendio parziale (lotto, stralcio, adeguamento parziale) non la preparo ancora."}',
    '  - {value: "{{ask.vvf_categoria}}", in: [a], else: "Per le attività di categoria B e C la SCIA antincendio segue l\'approvazione del progetto da parte dei Vigili del Fuoco (con il suo numero di pratica): non la preparo ancora."}',
    '  - {when: "{{ask.vvf_pnrr|not}}", else: "Un\'attività finanziata dal PNRR, PNC o ZES apre altre voci della SCIA antincendio, che non preparo ancora."}',
    '  - {when: "{{ask.vvf_impianti_speciali|not}}", else: "Impianti di idrogeno, GNL/GNC, rifiuti o le facciate e coperture di edifici civili aprono altre voci della SCIA antincendio, che non preparo ancora."}',
)
SIGN_OP = "SCIA per installazione insegna di esercizio"  # the sign as a second operation, where the screen has no tick for it
DEHORS_OP = "Domanda di occupazione suolo pubblico per area annessa ad esercizio di somministrazione di alimenti e bevande"
DEH = "napoli/comune/concessione-suolo-pubblico-dehors"
DEHORS_DONOR = "dehors-fittizio"
DEHORS_ASKS = ("coperto", "centro_storico", "nuovo_852")
DEHORS_ANSWERS = ("orario_dalle", "orario_alle", "giorno_chiusura", "dehors_lunghezza_m", "dehors_larghezza_m", "dehors_mq", "area_privata_uso_pubblico")
DONOR = "ristorante-insegna-fittizio"
SIGN_ASKS = ("insegna_consenso", "insegna_vincolo", "insegna_grande")
SIGN_ANSWERS = ("insegna", "insegna_titolo_tipo", "insegna_titolo_altro", "insegna_descrizione", "insegna_larghezza_m", "insegna_altezza_m",
                "insegna_superficie_mq", "insegna_monofacciale", "insegna_luce", "insegna_testo", "immobile_proprietario")

# name: (template, crawl, ticks, facts, handles)
def row(tpl, crawl, ticks, facts, handles, also=()):
    return dict(tpl=tpl, crawl=crawl, ticks=ticks, facts=facts, handles=handles, also=also)


S, V = "attivita: somministrazione", "attivita: vicinato_alimentare"
COMBOS = {
    # Bars and restaurants outside the protected zones (zone C)
    "ristorante-musica-fittizio": row("ristorante-fittizio", "suap-060-aprire-l-attivita-interventi", [NULLA],
                                      f'{S}, evento: apertura, insegna: "false", musica: "true"', [ASL, NO]),
    "trasferimento-ristorante-musica-fittizio": row("trasferimento-ristorante-fittizio", "suap-060-trasferire-la-sede-dell-attivita", [NULLA],
                                                    f'{S}, evento: trasferimento, insegna: "false", musica: "true"', [ASL, NO]),
    "ampliamento-ristorante-musica-fittizio": row("ampliamento-ristorante-fittizio", "suap-060-ampliamento-di-superficie", [NULLA],
                                                  f'{S}, evento: ampliamento, musica: "true"', [NO]),
    "subingresso-ristorante-insegna-fittizio": row("subingresso-ristorante-fittizio", "suap-060-subentrare-insegna", [],
                                                   f'{S}, evento: subingresso, insegna: "true"', [INS], [SIGN_OP]),
    # Bars and restaurants in zones A and B (the nulla osta is part of their authorization)
    "ristorante-centro-storico-insegna-fittizio": row("ristorante-centro-storico-fittizio", "suap-061-aprire-l-attivita", [SIGN],
                                                      f'{S}, evento: apertura, somministrazione_particolare: false, insegna: "true"', [NO, ASL, INS]),
    "trasferimento-ristorante-centro-storico-insegna-fittizio": row("trasferimento-ristorante-centro-storico-fittizio", "suap-061-trasferire-la-sede-dell-attivita", [SIGN],
                                                                    f'{S}, evento: trasferimento, somministrazione_particolare: false, insegna: "true"', [NO, ASL, INS]),
    "ampliamento-ristorante-centro-storico-musica-fittizio": row("ampliamento-ristorante-centro-storico-fittizio", "suap-061-variazioni-strutturali", [NULLA],
                                                                 f'{S}, evento: ampliamento, somministrazione_particolare: false', [NO]),
    # Bars and restaurants with the dehors' area (a second operation: the screen has no tick for it), the sign and the music as ticks
    "ristorante-dehors-fittizio": row("ristorante-fittizio", "suap-060-aprire-l-attivita-dehors", [],
                                      f'{S}, evento: apertura, dehors: "true", insegna: "false", musica: "false"', [ASL, DEH], [DEHORS_OP]),
    "ristorante-dehors-musica-fittizio": row("ristorante-fittizio", "suap-060-aprire-l-attivita-dehors", [NULLA],
                                             f'{S}, evento: apertura, dehors: "true", insegna: "false", musica: "true"', [ASL, DEH, NO], [DEHORS_OP]),
    "ristorante-dehors-insegna-fittizio": row("ristorante-fittizio", "suap-060-aprire-l-attivita-dehors", [SIGN],
                                              f'{S}, evento: apertura, dehors: "true", insegna: "true", musica: "false"', [ASL, DEH, INS], [DEHORS_OP]),
    "ristorante-dehors-insegna-musica-fittizio": row("ristorante-fittizio", "suap-060-aprire-l-attivita-dehors", [SIGN, NULLA],
                                                     f'{S}, evento: apertura, dehors: "true", insegna: "true", musica: "true"', [ASL, DEH, INS, NO], [DEHORS_OP]),
    "ristorante-centro-storico-dehors-fittizio": row("ristorante-centro-storico-fittizio", "suap-061-aprire-l-attivita-dehors", [],
                                                     f'{S}, evento: apertura, dehors: "true", somministrazione_particolare: false, insegna: "false"', [NO, ASL, DEH], [DEHORS_OP]),
    "ristorante-centro-storico-dehors-insegna-fittizio": row("ristorante-centro-storico-fittizio", "suap-061-aprire-l-attivita-dehors", [SIGN],
                                                             f'{S}, evento: apertura, dehors: "true", somministrazione_particolare: false, insegna: "true"', [NO, ASL, DEH, INS], [DEHORS_OP]),
    # Fire prevention (the SCIA VV.F., PIN 2) with an opening: a second operation of the same wizard
    "ristorante-pin-2-fittizio": row("ristorante-fittizio", "suap-060-aprire-l-attivita-pin-2", [],
                                     f'{S}, evento: apertura, insegna: "false", prevenzione_incendi: "true"', [ASL, VVF], [PIN2_OP]),
    # Food shops
    "alimentari-insegna-fittizio": row("alimentari-fittizio", "suap-017-aprire-l-attivita", [SIGN],
                                       f'{V}, evento: apertura, consumo_sul_posto: false, insegna: "true"', [ASL, INS]),
    "trasferimento-alimentari-insegna-fittizio": row("trasferimento-alimentari-fittizio", "suap-017-trasferire-la-sede-dell-attivita", [SIGN],
                                                     f'{V}, evento: trasferimento, consumo_sul_posto: false, insegna: "true"', [ASL, INS]),
    "subingresso-alimentari-insegna-fittizio": row("subingresso-alimentari-fittizio", "suap-017-subentrare-insegna", [],
                                                   f'{V}, evento: subingresso, consumo_sul_posto: false, insegna: "true"', [INS], [SIGN_OP]),
    "alimentari-centro-storico-insegna-fittizio": row("alimentari-centro-storico-fittizio", "suap-018-aprire-l-attivita", [SIGN],
                                                      f'{V}, evento: apertura, consumo_sul_posto: true, insegna: "true"', [ASL, INS]),
    "trasferimento-alimentari-centro-storico-insegna-fittizio": row("trasferimento-alimentari-centro-storico-fittizio", "suap-018-trasferire-la-sede-dell-attivita", [SIGN],
                                                                    f'{V}, evento: trasferimento, consumo_sul_posto: true, insegna: "true"', [ASL, INS]),
    # Non-food shops
    "trasferimento-negozio-insegna-fittizio": row("trasferimento-negozio-fittizio", "suap-016-trasferire-la-sede-dell-attivita", [SIGN],
                                                  'attivita: vicinato_non_alimentare, evento: trasferimento, insegna: "true"', [INS]),
    "subingresso-negozio-insegna-fittizio": row("subingresso-negozio-fittizio", "suap-016-subentrare-insegna", [],
                                                'attivita: vicinato_non_alimentare, evento: subingresso, insegna: "true"', [INS], [SIGN_OP]),
    # Hairdressers and beauticians
    "acconciatore-insegna-fittizio": row("acconciatore-fittizio", "suap-011-aprire-l-attivita-di-acconciatore-interventi", [SIGN],
                                         'attivita: acconciatore, evento: apertura, insegna: "true"', [INS]),
    "estetista-insegna-fittizio": row("estetista-fittizio", "suap-011-aprire-l-attivita-di-estetista", [SIGN],
                                      'attivita: estetista, evento: apertura, insegna: "true"', [INS]),
    "trasferimento-acconciatore-insegna-fittizio": row("trasferimento-acconciatore-fittizio", "suap-011-trasferire-la-sede-dell-attivita-di-acconciatore", [SIGN],
                                                       'attivita: acconciatore, evento: trasferimento, insegna: "true"', [INS]),
    "trasferimento-estetista-insegna-fittizio": row("trasferimento-estetista-fittizio", "suap-011-trasferire-la-sede-dell-attivita-di-estetista", [SIGN],
                                                    'attivita: estetista, evento: trasferimento, insegna: "true"', [INS]),
    "subingresso-acconciatore-insegna-fittizio": row("subingresso-acconciatore-fittizio", "suap-011-subentrare-acconciatore-insegna", [],
                                                     'attivita: acconciatore, evento: subingresso, insegna: "true"', [INS], [SIGN_OP]),
    "subingresso-estetista-insegna-fittizio": row("subingresso-estetista-fittizio", "suap-011-subentrare-estetista-insegna", [],
                                                  'attivita: estetista, evento: subingresso, insegna: "true"', [INS], [SIGN_OP]),
    # Bed and breakfast
    "affittacamere-insegna-fittizio": row("affittacamere-fittizio", "suap-056-aprire-l-attivita", [SIGN],
                                          'attivita: bed_and_breakfast, evento: apertura, insegna: "true"', [INS]),
}


def pin2_recipe(s):
    """The fire prevention's yours lines and refusals in a recipe's text."""
    s = s.replace("\nyours:\n", "\nyours:\n" + "".join(f'  - "{y}"\n' for y in PIN2_YOURS), 1)
    return s.replace("\nsupports:\n", "\nsupports:\n" + "\n".join(PIN2_SUPPORTS) + "\n", 1)


def pin2_answers(folder, d):
    """The made-up fire prevention answers, the professional's role and the professional in the fixture."""
    d.update(PIN2_ANSWERS)
    d["people"] = {**d.get("people", {}), "v": "valerio"}
    fx = folder / "fixture.json"
    fixture = json.loads(fx.read_text())
    donor_fx = json.loads((ROOT / "rehearsals" / PIN2_DONOR / "fixture-p6.json").read_text())
    have = {f[0] for f in fixture["fields"]}
    fixture["fields"] += [f for f in donor_fx["fields"] if f[0].startswith("valerio:") and f[0] not in have]
    fx.write_text(json.dumps(fixture, ensure_ascii=False, indent=1) + "\n")


# The fire prevention added to every routed opening, move and enlargement (2026-11-14): the sibling of each such recipe, on a crawl of
# its pratica with the PIN 2 as a second operation (`catalogue.py ops suap --combo`; a dehors one also lists the dehors' area).
def sibling_rows():
    """name -> row, one per routed SUAP recipe of an opening, a move or an enlargement without fire prevention, in rehearsals/."""
    import yaml
    rows = {}
    for f in sorted((ROOT / "rehearsals").glob("*/recipe.yaml")):
        r = yaml.safe_load(f.read_text(encoding="utf-8"))
        ru = r.get("rules") or {}
        if ru.get("table") != "suap-napoli" or "-pin-2" in f.parent.name or "prevenzione_incendi" in (ru.get("facts") or {}):
            continue
        facts = dict(ru.get("facts") or {})
        if facts.get("evento") not in ("apertura", "trasferimento", "ampliamento"):
            continue
        wiz = {d["screen"]: d for d in (r.get("wizard") or []) if isinstance(d, dict) and "screen" in d}
        ops = list(wiz["Scelta operazioni"]["tree"])
        ticks = [f"{t['leaf']}::{t.get('nth', 1)}" if isinstance(t, dict) else f"{t}::1" for t in (wiz.get("Scelta interventi eventuali") or {}).get("tree", [])]
        base = re.sub(r"-(interventi|procura)$", "", r["crawl"])
        crawl = base + "-pin-2"
        name = re.sub(r"-fittizi[oa]$", "", f.parent.name) + "-pin-2-fittizio"
        def fact(v):
            return str(v).lower() if isinstance(v, bool) else json.dumps(v) if isinstance(v, str) and (v in ("true", "false") or v.startswith("{{")) else str(v)
        fs = ", ".join(f"{k}: {fact(v)}" for k, v in facts.items())
        if name in COMBOS:
            continue
        rows[name] = dict(tpl=f.parent.name, crawl=crawl, ops=ops, ticks=ticks, facts=fs + ', prevenzione_incendi: "true"', handles=list(ru.get("handles") or []) + [VVF])
    return rows


def build_sibling(name):
    c = SIBLINGS[name]
    also = tuple(c["ops"][1:]) + (PIN2_OP,)
    folder = dr.derive(name, c["tpl"], c["crawl"], None, c["ticks"], c["facts"], c["handles"], (), also)
    p = folder / "recipe.yaml"
    p.write_text(pin2_recipe(p.read_text(encoding="utf-8")), encoding="utf-8")
    a = folder / "answers.json"
    d = json.loads(a.read_text())
    pin2_answers(folder, d)
    # The facts the table reads from the answers too (as overlay() does for the combinations): the zone from the name, the shop's
    # consumption on the spot from the facts, and no "fatti" asked.
    d["zona"] = "a" if "centro-storico" in name else (d.get("zona") or "c")
    m = re.search(r"consumo_sul_posto: (true|false)", c["facts"])
    if m:
        d["consumo_sul_posto"] = m.group(1)
    d.setdefault("fatti", [])
    a.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
    return dr.fill(folder)


def overlay(folder, tpl_has_sign, ticks, template, facts, also=()):
    ticks = list(ticks) + ([SIGN] if SIGN_OP in also else [])
    """The sign's asks, refusals, `yours` line and answers from the restaurant's, where the template has none; the music's and the
    bollo's where the nulla osta is ticked."""
    donor = (ROOT / "rehearsals" / DONOR / "recipe.yaml").read_text(encoding="utf-8")
    p = folder / "recipe.yaml"
    s = p.read_text(encoding="utf-8")
    s = dr.drop_asks(s, ("insegna_esterna",) + (("musica",) if NULLA in ticks and DEHORS_OP not in also else ()))
    if SIGN in ticks and not tpl_has_sign:
        asks = [l for l in donor.split("\n") if re.match(r"  (%s):" % "|".join(SIGN_ASKS), l)]
        zone_a = ('  insegna_zona_a: {group: extras, type: yes_no, item: "L\'installazione ricade in zona A del PRG (il centro storico)", '
                  'why: "In zona A la SCIA dell\'insegna ha altre condizioni, che non preparo ancora."}')
        sup = [l for l in donor.split("\n") if re.match(r"  - \{when: \"\{\{ask\.(%s)\|not\}\}\"" % "|".join(SIGN_ASKS), l)]
        sup.append('  - {when: "{{ask.insegna_zona_a|not}}", else: "In zona A del PRG (il centro storico) la SCIA dell\'insegna ha altre condizioni, che non preparo ancora."}')
        yours = [l for l in donor.split("\n") if "dichiarazioni dell'insegna" in l]
        s = s.replace("\nasks:\n", "\nasks:\n" + "\n".join(asks + [zone_a]) + "\n", 1)
        s = s.replace("\nsupports:\n", "\nsupports:\n" + "\n".join(sup) + "\n", 1)
        s = s.replace("\nyours:\n", "\nyours:\n" + "\n".join(yours) + "\n", 1)
    elif SIGN in ticks and "insegna_zona_a" not in s:
        s = s.replace("\nasks:\n", "\nasks:\n  insegna_zona_a: {group: extras, type: yes_no, item: \"L'installazione ricade in zona A del PRG (il centro storico)\", "
                      "why: \"In zona A la SCIA dell'insegna ha altre condizioni, che non preparo ancora.\"}\n", 1)
        s = s.replace("\nsupports:\n", "\nsupports:\n  - {when: \"{{ask.insegna_zona_a|not}}\", else: \"In zona A del PRG (il centro storico) la SCIA dell'insegna ha altre condizioni, che non preparo ancora.\"}\n", 1)
    if NULLA in ticks and "bollo_yours" not in s:
        s = s.replace("\nyours:\n", "\nyours:\n  - \"{{ask.bollo_marche,ask.bollo_esenzione|bollo_yours}}\"\n", 1)
    if DEHORS_OP in also:
        dd = (ROOT / "rehearsals" / DEHORS_DONOR / "recipe.yaml").read_text(encoding="utf-8").split("\n")
        asks = [l for l in dd if re.match(r"  (%s):" % "|".join(DEHORS_ASKS), l)]
        sup = [l for l in dd if re.match(r"  - \{when: \"\{\{ask\.(%s)\|not\}\}\"" % "|".join(DEHORS_ASKS), l)]
        yours = [l for l in dd if "progetto del dehors" in l or "il montaggio certificato" in l]
        s = s.replace("\nasks:\n", "\nasks:\n" + "\n".join(asks) + "\n", 1)
        s = s.replace("\nsupports:\n", "\nsupports:\n" + "\n".join(sup) + "\n", 1)
        s = s.replace("\nyours:\n", "\nyours:\n" + "\n".join(yours) + "\n", 1)
        if "bollo_yours" not in s:
            s = s.replace("\nyours:\n", "\nyours:\n  - \"{{ask.bollo_marche,ask.bollo_esenzione|bollo_yours}}\"\n", 1)
    if PIN2_OP in also:
        s = pin2_recipe(s)
    p.write_text(s, encoding="utf-8")
    a = folder / "answers.json"
    d = json.loads(a.read_text())
    don = json.loads((ROOT / "rehearsals" / DONOR / "answers.json").read_text())
    if SIGN in ticks:
        for k in SIGN_ANSWERS:
            d.setdefault(k, don[k])
        for k in SIGN_ASKS:
            d[k] = "false"
        d["insegna_zona_a"] = "false"
        d.pop("insegna_esterna", None)
    if DEHORS_OP in also:
        dehors = json.loads((ROOT / "rehearsals" / DEHORS_DONOR / "answers.json").read_text())
        for k in DEHORS_ANSWERS:
            d.setdefault(k, dehors[k])
        for k in DEHORS_ASKS:
            d[k] = "false"
        d.setdefault("bollo_marche", False)
        d.setdefault("bollo_esenzione", "no")
        d.setdefault("diritti_euro", "370")
    if PIN2_OP in also:
        pin2_answers(folder, d)
    if NULLA in ticks:
        d["bollo_marche"], d["bollo_esenzione"] = False, "no"
        if DEHORS_OP in also:
            d["musica"] = "true"  # the dehors' acoustic declaration reads it
        else:
            d.pop("musica", None)
    # The zone and the shop's consumption on the spot are facts of the case the table reads from the answers too: the template's, else
    # what the name and the recipe's facts say (the pool of other rehearsals' answers would give the first one found).
    tpl_file = next(f for f in ("answers.json", "answers-p1.json") if (ROOT / "rehearsals" / template / f).exists())
    tpl = json.loads((ROOT / "rehearsals" / template / tpl_file).read_text())
    d["zona"] = "a" if "centro-storico" in folder.name else (tpl.get("zona") or "c")
    m = re.search(r"consumo_sul_posto: (true|false)", facts)
    if m:
        d["consumo_sul_posto"] = m.group(1)
    d.setdefault("fatti", [])
    if "titolo_attivita_protocollo" in d:
        d["titolo_attivita_protocollo"] = "0666666"
    a.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n")


SIBLINGS = {}


def build(name):
    if name in SIBLINGS:
        return build_sibling(name)
    c = COMBOS[name]
    tpl_has_sign = "insegna_consenso" in (ROOT / "rehearsals" / c["tpl"] / "recipe.yaml").read_text(encoding="utf-8")
    folder = dr.derive(name, c["tpl"], c["crawl"], None, [t if t != SIGN else SIGN + "::1" for t in c["ticks"]], c["facts"], c["handles"], (), c["also"])
    overlay(folder, tpl_has_sign, c["ticks"], c["tpl"], c["facts"], c["also"])
    return dr.fill(folder)


if __name__ == "__main__":
    SIBLINGS.update(sibling_rows())
    names = sys.argv[1:] or list(COMBOS)
    for n in names:
        print(n, json.dumps(build(n), ensure_ascii=False))
