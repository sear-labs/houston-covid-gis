"""No committed file carries an absolute path from the machine that wrote it.

This repository is clean, and this guard exists so it stays that way.

Two of the six DOI'd repositories under this release process shipped an author's
home directory into an immutable Zenodo deposit before anything checked for it.
Four of the six, this one included, had no guard at all.

One detail matters more here than in the others: this repository tracks fourteen
paths containing spaces. An enumeration that splits `git ls-files` on whitespace
would silently skip every one of them and still report a plausible file count,
so the guard enumerates with `-z` and asserts every listed path resolves.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "check_no_machine_paths.py"


def test_the_guard_script_exists():
    assert GUARD.exists(), f"{GUARD.name} is missing - the sweep is the whole protection"


def test_no_committed_file_carries_a_machine_path():
    result = subprocess.run([sys.executable, str(GUARD)], cwd=ROOT,
                            capture_output=True, text=True)
    assert result.returncode == 0, (
        "a committed file carries an absolute home path:\n"
        f"{result.stdout}{result.stderr}\n"
        "Fix it where the string is produced, not by normalising the artifact - "
        "a normaliser hides it from every reader who is not diffing bytes."
    )
