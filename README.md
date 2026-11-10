# SPHERE: Spatial Platform for Hazard Evaluation and Risk Estimation

[![Open in molab](https://molab.marimo.io/molab-shield.png)](https://molab.marimo.io/notebooks/nb_VuW2QsspDTotm1GR9LD9JU)
[![CI](https://github.com/Niyam-Projects/sphere/actions/workflows/ci.yml/badge.svg)](https://github.com/Niyam-Projects/sphere/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
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
uv run examples/fast_analysis.py
```

4. Run the interactive flood analysis notebook with Marimo.

```bash
uv run marimo run ./examples/notebooks/run_sphere.py
```

The notebook provides a guided UI to configure and run a full HAZUS flood
loss analysis. You can choose between two methodologies:

- **Legacy HAZUS** (`HazusFloodAnalysis`) — the original riverine/coastal
  damage function approach.
- **Inland Consequences** (`HazusFloodAnalysis2`) — the updated methodology
  that additionally accepts **velocity** and **duration** hazard rasters for
  more detailed riverine peril classification (e.g. `RLS`, `RHL`) and updated
  coastal codes (`CST`, `CMV`, `CHW`).

The notebook also lets you declare whether your hazard rasters are in **feet**
or **meters**; values are automatically converted to feet before analysis.

Contributing
Please see `CONTRIBUTING.md` for guidelines on reporting issues, proposing
changes, running tests, and contributing patches. All contributors must
agree to the project's MIT license by submitting pull requests.

Contact
For questions and larger design discussions, please open an issue on the
project GitHub repository.

Citation
--------

If you use SPHERE in research, please cite it using `CITATION.cff`
(GitHub's "Cite this repository" button).

Security
--------

Please report vulnerabilities privately; see `SECURITY.md`.
