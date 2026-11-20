#!/usr/bin/env python3
"""Commits a built plugin (build.py's OUT/impresa-in-un-minuto/) to this repository's `plugin` branch, one
commit per release, and tags it `plugin-v<version>`: the marketplace's source points there, pinned
to that commit (pin_marketplace.py), because the Claude app takes only git sources (github, url,
git-subdir, ./path), not a release's zip. `--target openai` (build.py --target openai) does the same on
the `plugin-openai` branch, tagged `plugin-openai-v<version>`, for Codex's marketplace.

  publish_plugin.py --version 0.4.1 --dir OUT/impresa-in-un-minuto [--target openai] [--push]

Prints the commit. Run it from a checkout of the repository; nothing in the checkout changes (the
commit is made with a separate index). Without --push it only makes the commit and the tag locally.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Each target's branch, its tag's prefix and where its build keeps the manifest (build.py --target).
BRANCHES = {"claude": "plugin", "openai": "plugin-openai"}
MANIFESTS = {"claude": Path(".claude-plugin") / "plugin.json", "openai": Path("plugin.json")}
BRANCH = BRANCHES["claude"]


def git(*args, env=None, check=True):
    r = subprocess.run(["git", *args], capture_output=True, text=True, env=env)
    if check and r.returncode:
        sys.exit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip() if r.returncode == 0 else None


def tag_name(version, target="claude"):
    return f"{BRANCHES[target]}-v{version}"


def publish(version, plugin, push=False, remote="origin", target="claude"):
    branch, manifest_file = BRANCHES[target], plugin / MANIFESTS[target]
    if not manifest_file.is_file():
        sys.exit(f"{plugin} has no {MANIFESTS[target]}: not a build for --target {target}")
    manifest = json.loads(manifest_file.read_text())
    if manifest.get("version") != version:
        sys.exit(f"{manifest_file} says {manifest.get('version')}, not {version}")
    if (plugin / "bin").exists():
        sys.exit("the plugin has a top-level bin/: the Claude app refuses such a plugin")
    tag = tag_name(version, target)
    if git("rev-parse", "-q", "--verify", f"refs/tags/{tag}", check=False) or \
            git("ls-remote", "--exit-code", remote, f"refs/tags/{tag}", check=False):
        sys.exit(f"{tag} exists already: a published plugin is never replaced, release a new version")
    # The branch's history is one commit per release, each on the one before.
    parent = None
    # Full refs: ls-remote matches a pattern's last components, so "plugin" is also claude/plugin.
    if git("ls-remote", "--exit-code", remote, f"refs/heads/{branch}", check=False):
        git("fetch", "-q", remote, f"refs/heads/{branch}")
        parent = git("rev-parse", "--verify", "FETCH_HEAD^{commit}")
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        # -f: the built plugin is exactly what ships; no ignore file of this checkout drops a part of it.
        git("--work-tree", str(plugin), "add", "-A", "-f", ".", env=env)
        tree = git("write-tree", env=env)
    commit = git("commit-tree", tree, *(["-p", parent] if parent else []),
                 "-m", f"Impresa in un minuto {version}{'' if target == 'claude' else ' for ' + target}, built from v{version}")
    git("tag", "-a", tag, commit, "-m", f"Impresa in un minuto {version}{'' if target == 'claude' else ' for ' + target}")
    if push:
        git("push", remote, f"{commit}:refs/heads/{branch}", f"refs/tags/{tag}")
    return commit


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--dir", required=True, type=Path, help="the built plugin folder (build.py's OUT/impresa-in-un-minuto)")
    ap.add_argument("--target", choices=sorted(BRANCHES), default="claude", help="the build's target (default claude)")
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()
    if not re.fullmatch(r"\d+\.\d+\.\d+([-+][0-9A-Za-z.-]+)?", a.version):
        ap.error(f"--version {a.version!r} isn't a version like 0.1.0")
    print(publish(a.version, a.dir.resolve(), push=a.push, target=a.target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
