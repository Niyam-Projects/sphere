import os
import sys
import subprocess
import shutil
from pathlib import Path
import tempfile


def build_wheels(build_dir: Path):
    build_dir.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[1]
    # build each package wheel into build_dir
    for pkg in (repo / 'libs' / 'sphere-core', repo / 'libs' / 'sphere-data', repo / 'libs' / 'sphere-flood'):
        subprocess.run([sys.executable, '-m', 'build', '-w', '-o', str(build_dir), str(pkg)], check=True)


def build_meta(build_dir: Path):
    repo = Path(__file__).resolve().parents[1]
    # use the helper script to build the meta wheel into .build
    helper = repo / 'scripts' / 'build_meta.py'
    subprocess.run([sys.executable, str(helper)], check=True)
    # build_meta places wheel(s) into repo/.build
    meta_wheels = list((repo / '.build').glob('sphere-*.whl'))
    if not meta_wheels:
        raise RuntimeError('meta wheel not found')
    # copy meta wheel(s) into build_dir
    for w in meta_wheels:
        shutil.copy2(w, build_dir / w.name)


def create_venv(venv_dir: Path):
    subprocess.run([sys.executable, '-m', 'venv', str(venv_dir)], check=True)
    if os.name == 'nt':
        py = venv_dir / 'Scripts' / 'python.exe'
        pip = venv_dir / 'Scripts' / 'pip.exe'
    else:
        py = venv_dir / 'bin' / 'python'
        pip = venv_dir / 'bin' / 'pip'
    return py, pip


def test_meta_package_installs_and_imports(tmp_path: Path):
    repo = Path(__file__).resolve().parents[1]
    build_dir = tmp_path / 'wheels'
    build_wheels(build_dir)
    build_meta(build_dir)

    venv_dir = tmp_path / 'venv'
    py, pip = create_venv(venv_dir)

    # upgrade pip and install the wheels in the venv
    subprocess.run([str(pip), 'install', '--upgrade', 'pip'], check=True)
    wheel_files = list(build_dir.glob('*.whl'))
    assert wheel_files, 'no wheels built to install'
    subprocess.run([str(pip), 'install', *[str(p) for p in wheel_files]], check=True)

    # run import check inside venv
    code = (
        "import importlib, sys, pathlib;"
        "m1=importlib.import_module('sphere.core'); m2=importlib.import_module('sphere.flood');"
        "print(m1.__file__); print(m2.__file__);"
    )
    res = subprocess.run([str(py), '-c', code], capture_output=True, text=True, check=True)
    out = res.stdout.strip().splitlines()
    assert len(out) >= 2
    file1 = out[0]
    file2 = out[1]
    # Ensure imports come from installed wheel location, not repo 'libs' path
    assert 'libs' not in file1.replace('\\', '/'), f'source import detected: {file1}'
    assert 'libs' not in file2.replace('\\', '/'), f'source import detected: {file2}'
