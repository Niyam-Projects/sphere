"""All SPHERE distributions share one version and pin each other exactly."""

import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pytest depends on tomli for Python < 3.11
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
PYPROJECTS = [ROOT / "pyproject.toml", *sorted((ROOT / "packages").glob("*/pyproject.toml"))]
INTERNAL = {"sphere-core", "sphere-data", "sphere-flood"}


def _projects():
    return [tomllib.loads(path.read_text())["project"] for path in PYPROJECTS]


def test_all_packages_share_one_version():
    versions = {p["name"]: p["version"] for p in _projects()}

    assert len(set(versions.values())) == 1, versions


def test_internal_dependencies_are_pinned_to_the_shared_version():
    projects = _projects()
    version = projects[0]["version"]

    for project in projects:
        for dep in project.get("dependencies", []):
            name = re.split(r"[<>=!~ ;\[]", dep, maxsplit=1)[0]
            if name in INTERNAL:
                assert dep == f"{name}=={version}", f"{project['name']}: {dep}"
