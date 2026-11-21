#!/usr/bin/env python3
"""prova.py: where the Prova's folder goes. In the open folder; never inside a git repository (a code project the
session is open in: 2026-11-21 it was left in one as an untracked folder), where it goes in Documents/Impresa in un
minuto, or the home folder's, unless neither can be written.

  python3 plugin/test_prova.py      (standard library only)
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "impresa-in-un-minuto" / "skills" / "pratiche" / "prova.py"
PROVA = None  # prova.py beside a made-up case: the real one (prova/) is copied in by build.py


def made(cwd, home, *args):
    r = subprocess.run([sys.executable, "-I", str(PROVA), *args], cwd=cwd, capture_output=True, text=True,
                       env={**os.environ, "HOME": str(home)})
    assert r.returncode == 0, r.stderr
    folder = Path(r.stdout.strip())
    assert (folder / "answers.json").is_file() and (folder / "run").is_dir(), folder
    return folder


def main():
    global PROVA
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp).resolve()
        skill = tmp / "skill"
        (skill / "prova" / "files").mkdir(parents=True)
        (skill / "prova" / "answers.json").write_text("{}")
        PROVA = Path(shutil.copy(SOURCE, skill / "prova.py"))
        home, plain, repo = tmp / "home", tmp / "lavori", tmp / "progetto"
        for d in (home, plain, repo / "src"):
            d.mkdir(parents=True)
        (repo / ".git").mkdir()

        # A plain folder: the Prova goes there, -2 the second time.
        assert made(plain, home) == plain / "impresa-in-un-minuto-prova"
        assert made(plain, home) == plain / "impresa-in-un-minuto-prova-2"
        # Inside a repository, at its root or below: Documents/Impresa in un minuto, nothing in the repository.
        docs = home / "Documents" / "Impresa in un minuto"
        assert made(repo / "src", home) == docs / "impresa-in-un-minuto-prova"
        assert made(repo, home) == docs / "impresa-in-un-minuto-prova-2"
        assert sorted(p.name for p in repo.iterdir()) == [".git", "src"] and not any((repo / "src").iterdir())
        assert not list(docs.glob(".impresa-in-un-minuto-write-check")), "the write check was left behind"
        # A worktree's .git is a file: still a repository.
        wt = tmp / "worktree"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: /elsewhere\n")
        assert made(wt, home).parent == docs
        # A home that is a repository itself, or that can't be written: the open folder after all.
        (home / ".git").mkdir()
        assert made(repo, home).parent == repo
        locked = tmp / "locked"
        locked.mkdir()
        locked.chmod(0o500)
        try:
            assert made(wt, locked).parent == wt
        finally:
            locked.chmod(0o700)
        # A folder named on the command line is used as it is.
        assert made(plain, home, str(repo / "qui")) == repo / "qui"
    print("ok: prova.py's folder, in and out of git repositories")


if __name__ == "__main__":
    sys.exit(main())
