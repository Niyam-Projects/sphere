# sphere

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