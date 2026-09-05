r"""Every import in the package must be a declared dependency.

WHY THIS EXISTS. `from IPython.display import Image` survived a notebook
extraction into lithium-optsc-energies-2024, unused. IPython was not in
pyproject.toml, so a clean `pip install` produced a package that could not import
its own model - and it was invisible on Colab, which ships IPython, and fatal
anywhere else. The failure surfaced three layers from its cause.

WHY IT READS pyproject.toml RATHER THAN LISTING THE NAMES. The first version of
this test hard-coded `declared = {"pandas", "gurobipy", ...}`. That is a second
copy of the dependency list, kept in agreement by nothing - so a guard against
undeclared dependencies was itself an undeclared dependency list, and would have
gone wrong in exactly the direction it exists to catch. Caught in review by a
peer session, 2026-09-05.

WHY IT PARSES RATHER THAN IMPORTS. Importing the package executes the model.

KNOWN LIMIT, stated rather than hidden: a distribution name is not always the
module name it installs (`scikit-learn` gives you `sklearn`). Every dependency in
these repositories happens to match after normalising case and `-`/`_`. If that
stops being true, add an explicit mapping here - do not loosen the check.
"""
import ast
import os
import re
import sys

import pytest

try:                                    # tomllib is stdlib from 3.11
    import tomllib
except ModuleNotFoundError:             # 3.10 - declared supported, so keep the
    tomllib = pytest.importorskip(      # guard alive rather than skipping it
        "tomli", reason="3.10 needs tomli; it is in the dev extra")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _norm(name):
    return re.split(r"[<>=!~\[;]", name)[0].strip().lower().replace("-", "_")


def _declared():
    """The one home for the list: pyproject.toml, runtime plus every extra."""
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as fh:
        cfg = tomllib.load(fh)
    project = cfg["project"]
    names = {_norm(d) for d in project.get("dependencies", [])}
    for extra in project.get("optional-dependencies", {}).values():
        names |= {_norm(d) for d in extra}
    return names


def _package_dir():
    src = os.path.join(ROOT, "src")
    pkgs = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))
            and not d.endswith(".egg-info")]
    assert len(pkgs) == 1, "expected one package under src/, found %r" % pkgs
    return os.path.join(src, pkgs[0]), pkgs[0]


def test_every_import_is_a_declared_dependency():
    pkg_dir, pkg_name = _package_dir()
    declared = _declared()
    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    assert stdlib, "needs Python 3.10+ for sys.stdlib_module_names"

    undeclared = {}
    for fn in sorted(os.listdir(pkg_dir)):
        if not fn.endswith(".py"):
            continue
        with open(os.path.join(pkg_dir, fn), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                # level > 0 is a relative import: our own package, by definition.
                names = [node.module or ""] if node.level == 0 else []
            else:
                continue
            for raw in names:
                top = _norm(raw.split(".")[0])
                if not top or top == _norm(pkg_name) or top in stdlib:
                    continue
                if top not in declared:
                    undeclared.setdefault(top, set()).add(fn)

    assert not undeclared, (
        "imported but not declared in pyproject.toml: "
        + "; ".join("%s (%s)" % (mod, ", ".join(sorted(files)))
                    for mod, files in sorted(undeclared.items()))
        + ".\nEither add it to [project] dependencies or remove the import. "
          "A clean `pip install` of this package cannot satisfy it.")


def test_the_guard_reads_the_real_dependency_list():
    """The guard is only worth having if it tracks pyproject.toml.

    A hard-coded list would pass this file's other test forever while drifting
    from what a clean install actually provides.
    """
    declared = _declared()
    assert declared, "no dependencies parsed - pyproject.toml layout changed?"
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as fh:
        raw = tomllib.load(fh)
    first = _norm(raw["project"]["dependencies"][0])
    assert first in declared
