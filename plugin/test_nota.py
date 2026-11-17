#!/usr/bin/env python3
"""The plugin's nota.py: the file of missing details, and the filled file back into the job's
files. A pre-flight's `missing` in, a numbered form out; a value a line holds goes to the studio's
file or the job's by whose it is, held to check.py's rules; what is empty or wrong is named by
its label, never its field id.

  python3 plugin/test_nota.py      (no packages)
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTA = HERE / "impresa-in-un-minuto" / "skills" / "pratiche" / "nota.py"
MISSING = [
    {"field": "t:identity.sex", "id": "tecnico:identity.sex", "why": "empty in the vault", "for": "Qualifica e dati del procuratore: Sesso"},
    {"field": "t:identity.date_of_birth", "id": "tecnico:identity.date_of_birth", "why": "empty in the vault", "for": "Qualifica e dati del procuratore: il"},
    {"field": "t:residenza.indirizzo", "id": "tecnico:residenza.indirizzo", "why": "empty in the vault", "for": "Qualifica e dati del procuratore: Indirizzo"},
    {"field": "t:business.email_pec", "id": "business.email_pec", "why": "empty in the vault", "for": "Qualifica e dati del procuratore: eMail PEC"},
    {"field": "c:identity.citizenship", "id": "luca:identity.citizenship", "why": "empty in the vault", "for": "Scheda anagrafica: Cittadinanza"},
    {"field": "c:residenza.cap", "id": "luca:residenza.cap", "why": "empty in the vault", "for": "Scheda anagrafica: CAP"},
    {"field": "c:identity.phone", "id": "luca:identity.phone", "why": "empty in the vault", "for": "Scheda anagrafica: Telefono"},
    {"field": "*:ruolo.tipo", "id": "*:ruolo.tipo", "why": "empty in the vault", "for": "nobody"},
]


def run(*args):
    r = subprocess.run([sys.executable, "-I", str(NOTA), *map(str, args)], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def main():
    failed = 0

    def check(name, ok, said=None):
        nonlocal failed
        print(("ok   " if ok else "FAIL ") + name)
        if not ok:
            failed += 1
            print(said)

    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        (t / "pf.json").write_text(json.dumps({"missing": MISSING}))
        code, out, err = run("template", t / "pf.json", "--out", t / "dati.txt", "--map", t / "map.json", "--pratica", "CILA")
        text = (t / "dati.txt").read_text()
        lines = text.splitlines()
        check("a form: one numbered line for each detail, nobody's `*:` row left out", code == 0
              and sum(1 for l in lines if l[:1].isdigit()) == 7, (out, err, text))
        check("the tecnico's own come first, the client's after, each under its heading",
              lines.index(next(l for l in lines if l.startswith("== Tuoi"))) < lines.index("== Del committente =="), text)
        check("the portal's label, the section name every person shares dropped; no field id anywhere",
              "Cittadinanza =" in text and "Scheda anagrafica" not in text and "identity." not in text, text)
        check("a form addressed as tu", "scrivimi «fatto»" in text and "Lei" not in text, text)

        # The tecnico fills some lines: a valid one of each side, a wrong one, one left empty.
        n = {i["label"]: i["n"] for i in json.loads((t / "map.json").read_text())["items"]}
        values = {"Sesso": "f", "il": "05/03/1980", "Indirizzo": "via Roma 1", "eMail PEC": "",
                  "Cittadinanza": "italiana", "CAP": "8012", "Telefono": "333 1234567"}
        filled = []
        for l in lines:
            m = l.split(". ", 1)
            if l[:1].isdigit():
                label = next(k for k in values if m[1].split(": ")[-1].removesuffix(" =") == k)
                l = l + " " + values[label]
            filled.append(l)
        (t / "dati.txt").write_text("\n".join(filled))
        (t / "studio.json").write_text(json.dumps({"tecnico:ruolo.tipo": "titolare"}))
        (t / "values.json").write_text("{}")
        code, out, err = run("read", t / "dati.txt", "--map", t / "map.json", "--studio", t / "studio.json", "--values", t / "values.json")
        studio, job = json.loads((t / "studio.json").read_text()), json.loads((t / "values.json").read_text())
        check("the tecnico's go to the studio's file, normalized (sex upper case, a date as YYYY-MM-DD)",
              studio.get("tecnico:identity.sex") == "F" and studio.get("tecnico:identity.date_of_birth") == "1980-03-05"
              and studio.get("tecnico:residenza.indirizzo") == "via Roma 1" and studio["tecnico:ruolo.tipo"] == "titolare", studio)
        check("the client's go to the job's file", job.get("luca:identity.citizenship") == "italiana"
              and job.get("luca:identity.phone") == "333 1234567", job)
        check("a wrong value (a 4-digit CAP) is named by its label, not written, and the exit is 1",
              code == 1 and "Da correggere, Scheda anagrafica" not in out and "CAP" in out and "luca:" not in out
              and "luca:residenza.cap" not in job, (code, out))
        check("an empty line is said to be still empty, by its label",
              "Ancora vuoti (1): Qualifica e dati del procuratore: eMail PEC" in out, out)

    # What broke it in review: rows with no id, the wrong value on the screen, a form saved by Notepad,
    # a missing studio file, a key in both files, two firms that share a label.
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        rows = MISSING[:1] + [
            {"field": "c:cie.data_scadenza", "why": "expired on 2020-01-01", "for": "c:cie"},
            {"field": "c:x.y", "why": "at most 10 characters", "for": "Impresa: protocollo"},
            {"field": "f:business.ragione_sociale", "id": "edil:identity.last_name", "why": "empty in the vault", "for": "h) Impresa: Cognome"},
            {"field": "f2:business.ragione_sociale", "id": "impianti:identity.last_name", "why": "empty in the vault", "for": "h) Impresa: Cognome"},
            {"field": "c:identity.codice_fiscale", "id": "luca:identity.codice_fiscale", "why": "empty in the vault", "for": "Scheda anagrafica: Cod.Fiscale"},
        ]
        (t / "pf.json").write_text(json.dumps({"missing": rows}))
        code, out, err = run("template", t / "pf.json", "--out", t / "d.txt", "--map", t / "map.json")
        form = (t / "d.txt").read_text()
        items = json.loads((t / "map.json").read_text())["items"]
        check("rows with no id (an expired document, a value too long) are left in the chat, not a crash",
              code == 0 and len(items) == 4, (code, err))
        check("two firms with one label are told apart by the person's name in the id",
              "Cognome (edil) =" in form and "Cognome (impianti) =" in form, form)
        check("the form doesn't promise «una volta sola»: a single job asks again in another folder",
              "una volta sola" not in form and "prossime pratiche" not in form, form)
        n = {i["id"]: i["n"] for i in items}
        wrong = "RSSMRA80A01H501Q"  # a codice fiscale with a wrong check character
        lines = [l + (f" {wrong}" if l.startswith(f"{n['luca:identity.codice_fiscale']}.") else
                      " Esempio è" if l.startswith(f"{n['edil:identity.last_name']}.") else
                      " m" if l.startswith(f"{n['tecnico:identity.sex']}.") else "")
                 for l in form.splitlines()]
        text = "\n".join(lines)
        for name, raw in (("utf-8 with a BOM", b"\xef\xbb\xbf" + text.encode("utf-8")), ("windows-1252", text.encode("cp1252")),
                          ("utf-16", text.encode("utf-16"))):
            (t / "f.txt").write_bytes(raw)
            (t / "studio.json").write_text('{"tecnico:ruolo.tipo": "titolare"}')
            (t / "values.json").write_text('{"edil:identity.last_name": "vecchio", "tecnico:identity.sex": "F"}')
            code, out, err = run("read", t / "f.txt", "--map", t / "map.json", "--studio", t / "studio.json", "--values", t / "values.json")
            job = json.loads((t / "values.json").read_text())
            check(f"a form saved as {name} is read, with the accent intact", code == 1 and job.get("edil:identity.last_name") == "Esempio è", (code, out, err))
        check("a wrong codice fiscale is named by its label in Italian; neither the value nor a field id is printed",
              "Cod.Fiscale: codice fiscale o partita IVA non valido" in out and wrong not in out and "luca:" not in out
              and "got" not in out, out)
        studio = json.loads((t / "studio.json").read_text())
        check("the tecnico's key that sat in the job's file moves to the studio's: in one file only (check.py refuses two)",
              studio.get("tecnico:identity.sex") == "M" and "tecnico:identity.sex" not in job, (studio, job))
        (t / "none.json").unlink(missing_ok=True)
        run("read", t / "f.txt", "--map", t / "map.json", "--studio", t / "none.json", "--values", t / "values.json")
        check("with no studio file yet, the one it makes still has the tecnico as titolare",
              json.loads((t / "none.json").read_text()).get("tecnico:ruolo.tipo") == "titolare", (t / "none.json").read_text())

    print(f"{failed} failed" if failed else "all passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
