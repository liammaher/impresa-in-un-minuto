#!/usr/bin/env python3
"""Writes .claude-plugin/marketplace.json for one release: the marketplace people add
(in the Claude app, or `claude plugin marketplace add liammaher/impresa-in-un-minuto`) and the one entry in
it, the Impresa in un minuto plugin, as the release's commit on the `plugin` branch (publish_plugin.py),
tagged plugin-v<version> and pinned by its commit SHA, so a moved tag installs nothing else.

  pin_marketplace.py --version 0.4.1 --commit <40 hex of plugin-v0.4.1's commit> [--out FILE]
  pin_marketplace.py --target openai --version 0.4.1 --commit <40 hex of plugin-openai-v0.4.1's commit>

`--target openai` writes .agents/plugins/marketplace.json, Codex's (`codex plugin marketplace add
liammaher/impresa-in-un-minuto`, the ChatGPT desktop app): the same marketplace name, its one entry the
release's commit on the `plugin-openai` branch as a `url` source with its tag and SHA. Codex reads our
.claude-plugin/marketplace.json too, but skips its entry: it has no `github` source (tried 2026-11-20).

A git source, not the release's zip (`archive`, Claude Code only): the Claude app (chat, Cowork)
syncs only `github`, `url`, `git-subdir` and `./` sources (claude.com/docs/plugins/org-sync); with
the `archive` source, "Add marketplace" failed in the app (2026-11-06). The release workflow
(.github/workflows/release.yml) runs it after publishing the plugin and opens a pull request.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO = "liammaher/impresa-in-un-minuto"
DISPLAY_NAME = "Impresa in un minuto"  # shown in place of the id; the entry's wins over plugin.json's
HERE = Path(__file__).resolve().parent


def vault():
    """build.yaml's `vault`: whether the release's plugin ships the archive (the listing says so)."""
    sys.path.insert(0, str(HERE))
    import build
    return build.vault_default()


def copertura():
    """What the plugin covers, as its texts say it (build.py scope)."""
    sys.path.insert(0, str(HERE))
    import build
    return build.scope()["copertura"]


def marketplace(version, commit, repo=REPO, vault=True):
    return {
        "name": "impresa-in-un-minuto",
        "description": "Per tecnici e professionisti (architetti, geometri, ingegneri, commercialisti, consulenti) che queste pratiche "
                       "le presentano già: Claude le compila sui portali della "
                       "pubblica amministrazione, fino ai passi che spettano solo a te (accesso con SPID, dichiarazioni, firma, "
                       "pagamento, invio). Non è una consulenza: Claude può sbagliare, il controllo è tuo.",
        "owner": {"name": "Liam Maher"},
        "plugins": [{
            "name": "impresa-in-un-minuto",
            "displayName": DISPLAY_NAME,
            "description": f"Per chi presenta già queste pratiche: compila quelle del {copertura()}, su impresainungiorno, dai "
                           f"documenti del cliente{' o dal tuo archivio cifrato (vault)' if vault else ''}, con la "
                           "biblioteca pratiche-napoli di regole e procedure. Non è una consulenza: il controllo è tuo.",
            "source": {
                "source": "github",
                "repo": repo,
                "ref": f"plugin-v{version}",
                "sha": commit,
            },
        }],
    }


def openai_category():
    """The listing's category, as the openai build's manifest says it (build.py)."""
    sys.path.insert(0, str(HERE))
    import build
    return build.OPENAI_CATEGORY


def openai_marketplace(version, commit, repo=REPO):
    """Codex's marketplace (developers.openai.com/plugins/build/plugins): each entry needs its policy
    and category; the source is the plugin-openai branch's commit, pinned as the Claude one is."""
    return {
        "name": "impresa-in-un-minuto",
        "interface": {"displayName": DISPLAY_NAME},
        "plugins": [{
            "name": "impresa-in-un-minuto",
            "source": {"source": "url", "url": f"https://github.com/{repo}.git",
                       "ref": f"plugin-openai-v{version}", "sha": commit},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": openai_category(),
        }],
    }


OUT = {"claude": HERE.parent / ".claude-plugin" / "marketplace.json",
       "openai": HERE.parent / ".agents" / "plugins" / "marketplace.json"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--commit", required=True, help="the plugin branch's commit for this version")
    ap.add_argument("--target", choices=sorted(OUT), default="claude", help="whose marketplace (default claude)")
    ap.add_argument("--out", type=Path, help="default: the target's marketplace file in this repository")
    a = ap.parse_args()
    if not re.fullmatch(r"\d+\.\d+\.\d+([-+][0-9A-Za-z.-]+)?", a.version):
        ap.error(f"--version {a.version!r} isn't a version like 0.1.0")
    if not re.fullmatch(r"[0-9a-f]{40}", a.commit):
        ap.error("--commit must be a full commit SHA, 40 lower-case hex characters")
    a.out = a.out or OUT[a.target]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    made = marketplace(a.version, a.commit, vault=vault()) if a.target == "claude" else openai_marketplace(a.version, a.commit)
    a.out.write_text(json.dumps(made, indent=2, ensure_ascii=False) + "\n")
    print(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
