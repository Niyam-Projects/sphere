"""Set one version on every SPHERE package and its internal `==` pins, then relock.

Usage: uv run python scripts/set_version.py 0.4.0
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECTS = [ROOT / "pyproject.toml", *sorted((ROOT / "packages").glob("*/pyproject.toml"))]
VERSION_ARG = re.compile(r"\d+\.\d+\.\d+((a|b|rc)\d+)?")
# First `version = ...` line in each file is the [project] version.
PROJECT_VERSION = re.compile(r'^version = "[^"]*"', re.MULTILINE)
# Indented list entries only, so `name = "sphere-core"` is left alone.
INTERNAL_DEP = re.compile(r'^(\s+)"(sphere-(?:core|data|flood))(?:[<>=!~][^"]*)?"', re.MULTILINE)


def set_version(text: str, version: str) -> str:
    text = PROJECT_VERSION.sub(f'version = "{version}"', text, count=1)
    return INTERNAL_DEP.sub(rf'\1"\2=={version}"', text)


def main() -> None:
    if len(sys.argv) != 2 or not VERSION_ARG.fullmatch(sys.argv[1]):
        sys.exit("usage: set_version.py X.Y.Z   (e.g. 0.4.0 or 0.4.0rc1)")
    version = sys.argv[1]
    for path in PYPROJECTS:
        path.write_text(set_version(path.read_text(), version))
        print(f"{path.relative_to(ROOT)} -> {version}")
    subprocess.run(["uv", "lock"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
