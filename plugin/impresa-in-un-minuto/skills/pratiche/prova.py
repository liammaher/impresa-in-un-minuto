#!/usr/bin/env python3
"""Copy the Prova (the made-up CILA beside this script) into a new folder, for prova.md.

  prova.py [DEST]
  prova.py --files DIR

DEST defaults to impresa-in-un-minuto-prova in the current folder; when that exists, impresa-in-un-minuto-prova-2,
-3 and so on. When the current folder is inside a git repository (a code project the session happens to be open in:
the Prova was left there as an untracked folder, 2026-11-21), it goes in Documents/Impresa in un minuto instead, or the
home folder's; where neither can be written (a sandbox that writes only the open folder), in the current folder after
all. Prints the folder it made. --files copies only the Prova's made-up PDFs into DIR
(made if missing, a file there already kept), for a test of the tecnico's own case, and prints
each one's path. Never writes into the plugin's own folder: the copy is
made by this script, so the only path a command names is the new folder (a `cp` from the plugin's
folder can be refused by a session's permission rules).
"""

import shutil
import sys
from pathlib import Path

CASE = Path(__file__).resolve().parent / "prova"


def in_repository(folder):
    """Whether folder is inside a git repository: a .git (a folder, or a worktree's file) there or above it."""
    return any((p / ".git").exists() for p in (folder, *folder.parents))


def writable(folder):
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".impresa-in-un-minuto-write-check"
        probe.write_text("")
        probe.unlink()
        return True
    except OSError:
        return False


def default_place():
    """Where the Prova's folder goes when none is named: the current folder, unless it is inside a git repository."""
    here = Path.cwd()
    if not in_repository(here):
        return here
    for base in (Path.home() / "Documents", Path.home()):
        folder = base / "Impresa in un minuto"
        if not in_repository(base) and writable(folder):
            return folder
    return here


def target(base):
    dest, n = base, 1
    while dest.exists():
        n += 1
        dest = base.with_name(f"{base.name}-{n}")
    return dest


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--files":
        out = Path(sys.argv[2]).resolve()
        out.mkdir(parents=True, exist_ok=True)
        for f in sorted((CASE / "files").glob("*.pdf")):
            if not (out / f.name).exists():
                shutil.copy2(f, out / f.name)
            print(out / f.name)
        return 0
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1].startswith("-")):
        sys.exit("usage: prova.py [DEST] | prova.py --files DIR")
    dest = target(Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else default_place() / "impresa-in-un-minuto-prova")
    shutil.copytree(CASE, dest)
    (dest / "run").mkdir(exist_ok=True)
    print(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
