#!/usr/bin/env python3
import tomli
from packaging.version import Version
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
files = [ROOT / 'libs' / 'sphere-core' / 'pyproject.toml',
         ROOT / 'libs' / 'sphere-data' / 'pyproject.toml',
         ROOT / 'libs' / 'sphere-flood' / 'pyproject.toml']

vers = []
for f in files:
    data = tomli.loads(f.read_text())
    vers.append(data['project']['version'])

high = max(vers, key=Version)
print('computed highest version:', high)

build_meta = ROOT / '.build' / 'meta'
if build_meta.exists():
    shutil.rmtree(build_meta)
build_meta.mkdir(parents=True)

shutil.copytree(ROOT / 'libs' / 'sphere-meta', build_meta, dirs_exist_ok=True)

py = build_meta / 'pyproject.toml'
txt = py.read_text()
import re
txt = re.sub(r'(?m)^version\s*=\s*".*"$', f'version = "{high}"', txt, count=1)
py.write_text(txt)
print('updated copied meta pyproject to version', high)

print('building meta wheel...')
# ensure README exists in the copied meta folder for build metadata
shutil.copyfile(ROOT / 'README.md', build_meta / 'README.md')
subprocess.check_call([shutil.which('python') or 'python', '-m', 'build', str(build_meta), '-w', '-o', str(ROOT / '.build')])
print('built:', list((ROOT / '.build').glob('sphere-*.whl')))
