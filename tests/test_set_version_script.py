"""scripts/set_version.py rewrites versions and internal pins, nothing else."""

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "set_version.py"
_spec = importlib.util.spec_from_file_location("set_version", _SCRIPT)
set_version_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(set_version_module)

PYPROJECT = '''[project]
name = "sphere-flood"
version = "0.3.0"
dependencies = [
    "numpy>=2.2.6",
    "sphere-core==0.3.0",
    "sphere-data",
]

[project.scripts]
sphere-flood = "sphere.flood:main"

[tool.uv.sources]
sphere-core = { workspace = true }
'''


def test_sets_project_version_and_pins_internal_deps():
    result = set_version_module.set_version(PYPROJECT, "0.4.0")

    assert 'version = "0.4.0"' in result
    assert '    "sphere-core==0.4.0",' in result
    assert '    "sphere-data==0.4.0",' in result


def test_leaves_name_scripts_sources_and_external_deps_alone():
    result = set_version_module.set_version(PYPROJECT, "0.4.0")

    assert 'name = "sphere-flood"' in result
    assert 'sphere-flood = "sphere.flood:main"' in result
    assert "sphere-core = { workspace = true }" in result
    assert '"numpy>=2.2.6"' in result
