Thank you for your interest in contributing to this project!

This repository contains a modern reimplementation of HAZUS flood
vulnerability methodology. We welcome bug reports, feature requests, and
pull requests. By contributing you agree that your contributions will be
licensed under the project's MIT License.

Getting started
- Fork the repository and create a topic branch for your change.
- Keep changes small and focused — one logical change per branch/PR.
- Write tests for bug fixes and new features where applicable.

Development environment
1. Create and activate a virtual environment (Python 3.10+).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .[dev]
```

2. Run tests:

```powershell
pytest
```

Code style
- Follow existing project style. We use type annotations and aim for
  clear, well-documented code.
- If adding new modules, include unit tests and update the README or other
  documentation if necessary.

Commit messages and PRs
- Use clear, descriptive commit messages. Keep commits focused and logical.
- When opening a PR, describe the problem, how your change fixes it, and
  any testing instructions.

Reporting issues
- Please file issues using the issue tracker. Include a minimal reproduction
  case and any relevant logs or input data.

Security
- Do not include secrets or credentials in the repository. If you discover a
  security vulnerability, please report it privately via the repository
  maintainer contact instead of opening a public issue.

License and Copyright
- By contributing, you agree that your contributions are licensed under the
  MIT License included with the project.

Code of Conduct
- Be respectful and helpful in discussions and reviews. Maintainers reserve
  the right to close or reject contributions that do not adhere to project
  standards or community guidelines.

Thank you for helping improve this project!
