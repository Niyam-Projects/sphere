# SPHERE: Spatial Platform for Hazard Evaluation and Risk Estimation

[![Open in molab](https://molab.marimo.io/molab-shield.png)](https://molab.marimo.io/notebooks/nb_VuW2QsspDTotm1GR9LD9JU)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Niyam-Projects/sphere/blob/main/examples/hazus_csv_sample.ipynb)



A modern Python implementation of the HAZUS flood methodology for building
vulnerability and loss estimation. This repository packages a set of libraries
(`sphere-core`, `sphere-data`, `sphere-flood`) that implement flood
vulnerability functions, lookup tables, and analysis scripts suitable for
research and operational use.

This project is a newer reimplementation of HAZUS flood vulnerability logic
with a focus on clarity, type annotations, and tested, modular code.

Key features
- Building vulnerability functions (HAZUS-derived)
- Flood damage cross-reference and interpolation utilities
- Example analysis scripts in `examples/`
- Test coverage under `tests/`

License
This code is released under the MIT License — see `LICENSE` for details.

Quick start
1. Create a virtual environment (Python 3.10+).

```powershell
uv sync --all-packages
```

2. Run tests

```powershell
uv run pytest -q
```

3. Explore examples in the `examples/` directory.

```powershell
uv run examples\fast_analysis.py
```

Contributing
Please see `CONTRIBUTING.md` for guidelines on reporting issues, proposing
changes, running tests, and contributing patches. All contributors must
agree to the project's MIT license by submitting pull requests.

Contact
For questions and larger design discussions, please open an issue on the
project GitHub repository.

Development
-----------

There are two convenient ways to work with the workspace packages locally:

- Lightweight dev environment using `PYTHONPATH` (recommended for quick development):

	- Linux/macOS:

		```bash
		source scripts/dev.env
		uv run pytest -q
		```

	- Windows PowerShell:

		```powershell
		.\scripts\dev.env.ps1
		uv run pytest -q
		```

	This sets `PYTHONPATH` so imports like `import sphere.core` resolve against the
	in-repo sources without installing packages into your virtualenv.

-- Meta package (`sphere-meta`): a minimal aggregator distribution that depends on
	`sphere-core`, `sphere-data`, and `sphere-flood`. You can build and install
	`libs/sphere-meta` if you want a single installable package that pulls the
	three distributions from PyPI.

	```powershell
	cd libs/sphere-meta
	uv run python -m build -w
	python -m pip install dist\sphere_meta-0.1.0-py3-none-any.whl
	```

CI notes
--------

In CI, prefer one of these two approaches:

- Set `PYTHONPATH` (fast): add the paths to `GITHUB_ENV` so tests can import the
	in-repo packages.
- Build wheels for each package and install them (strict): build and install
	wheels in the job before running tests.
