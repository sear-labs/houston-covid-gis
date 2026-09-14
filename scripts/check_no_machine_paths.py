#!/usr/bin/env python
"""No committed file may carry an absolute path from the machine that wrote it.

    python scripts/check_no_machine_paths.py

A user's home directory path in a committed file publishes their username. This
repository is clean and this guard exists to keep it that way: two sibling
repositories under the same DOI'd release process each shipped one into an
immutable Zenodo deposit before anything checked.

Taken from ``sav-osemosys-trd-2019`` rather than rewritten. Three things in it were
each found the hard way and are worth not re-learning:

**Enumerate with ``git ls-files -z``, not a whitespace split.** A path containing a
space breaks apart under ``.split()`` into fragments that do not exist; ``is_file()``
then returns False for each and the file is skipped with no message at all. This
repository tracks fourteen such paths, so the failure is real here, not theoretical.
A "scanned N files" count cannot catch it - a skip and a scan look identical from
the summary line - which is why every listed path is asserted to resolve.

**Read binary files too.** A text-only scan skips what does not look like text,
which here is the bulk of the repository - eleven PNGs, fourteen JPEGs and two
GeoPackages. A ``.gpkg`` is a SQLite database, so a path stored inside one as
table data would still be visible to a raw-bytes scan, but one stored in a
compressed page would not.

**Prove the pattern can match before trusting that it did not.** A regex built to
match one-or-two literal backslashes silently matches nothing if a single character
is wrong, and reports success while doing it. ``_probe`` constructs a known match
with the same machinery the real patterns use, every run, before the sweep is
trusted.

Limit, stated rather than implied: this reads raw bytes plus gzip members. A path
inside a zip container (``.xlsx``), a zlib-compressed PDF stream, or a PNG ``zTXt``
chunk would not be seen.
"""
from __future__ import annotations

import gzip
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Built with chr(92), never a literal backslash in source: a Windows path written
# directly into a Python string is a trap where `\U` and `\1` are escapes rather
# than the characters they look like - and only one of those two fails loudly.
_BACKSLASH = re.escape(chr(92))

_PATTERNS = [
    re.compile(rb"[A-Za-z]:" + _BACKSLASH.encode() + rb"+Users" + _BACKSLASH.encode()
               + rb"+[A-Za-z0-9_.-]+"),
    re.compile(rb"/home/[a-z][a-z0-9_-]*/"),
    re.compile(rb"/Users/[A-Za-z0-9_.-]+/"),
]

def _probe() -> None:
    """The pattern must be shown capable of matching before its silence means anything."""
    sample = ("C:" + chr(92) + "Users" + chr(92) + "probe" + chr(92) + "leak.txt").encode()
    assert any(p.search(sample) for p in _PATTERNS), (
        "the machine-path pattern does not match its own probe string - "
        "fix the pattern before trusting any 'no matches' result"
    )


def _tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                         capture_output=True, text=True, check=True)
    return [f for f in out.stdout.split("\0") if f]


def _prove_the_distinction_matters(names: list[str]) -> None:
    """Demonstrate the whitespace-split bug on this repository's own tracked paths.

    A fix has to be exercised on the case it was broken for. This repo tracks
    fourteen paths containing spaces, so the demonstration uses them rather than a
    synthetic stand-in: a naive enumeration would silently skip every one.
    """
    spaced = [n for n in names if " " in n]
    assert spaced, (
        "no tracked path contains a space, so this demonstration cannot run on the "
        "real tree - replace it with a synthetic one rather than deleting it"
    )
    naive = " ".join(names).split()
    lost = [n for n in spaced if n not in naive]
    assert lost, (
        "a whitespace split did not lose any spaced path - the demonstration itself "
        "is broken, not just the thing it demonstrates"
    )


def _every_listed_path_resolves(names: list[str]) -> None:
    """A path git names but the filesystem does not have means enumeration and
    filesystem disagree. Continuing past it silently is the whitespace-split failure
    arriving by another route."""
    for name in names:
        assert (ROOT / name).is_file(), (
            f"{name!r} was listed by git but does not resolve to a file"
        )


def sweep() -> str:
    _probe()
    names = _tracked_files()
    _prove_the_distinction_matters(names)
    _every_listed_path_resolves(names)

    hits: list[tuple[str, str]] = []
    for name in names:
        raw = (ROOT / name).read_bytes()
        blobs = [raw]
        if name.endswith(".gz"):
            try:
                blobs.append(gzip.decompress(raw))
            except OSError:
                pass  # not actually gzip; the raw-bytes scan above still covers it
        for blob in blobs:
            for pattern in _PATTERNS:
                for match in set(pattern.findall(blob)):
                    hits.append((name, match.decode("utf-8", "replace")))

    assert not hits, "machine path(s) found in committed files:\n" + "\n".join(
        f"  {name}: {text}" for name, text in hits
    )
    return f"{len(names)} tracked files swept, 0 machine paths found"

def main() -> int:
    try:
        detail = sweep()
    except AssertionError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(f"ok   {detail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
