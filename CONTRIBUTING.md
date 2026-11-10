# Contributing to SPHERE

Thank you for your interest in contributing! SPHERE is a modern
reimplementation of the HAZUS flood vulnerability methodology. We welcome bug
reports, feature requests, and pull requests.

By participating you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).
By contributing you agree that your contributions are licensed under the
project's [MIT License](LICENSE).

## Roles

| Role | Who | Can |
|---|---|---|
| Maintainers | [`@Niyam-Projects/opensource-maintainers`](https://github.com/orgs/Niyam-Projects/teams/opensource-maintainers) | Review and merge PRs (code owners), triage, cut releases |
| Committers | Invited collaborators with Write access | Push branches to this repo, open PRs from them, triage issues |
| Contributors | Everyone else | Open issues, open PRs from a fork |

`main` is protected: every change lands through a pull request with passing
CI and an approving review from a maintainer.

## Getting started

1. **Contributors:** fork the repository and create a topic branch from `main`.
   **Committers and maintainers:** push a branch to this repository directly
   (e.g. `feat/short-name`, `fix/issue-123`); no fork needed.
2. Keep changes small and focused: one logical change per pull request.
3. Add or update tests for bug fixes and new features.

## Development environment

The project uses [uv](https://docs.astral.sh/uv/) and a uv workspace
(`packages/core`, `packages/data`, `packages/flood`). Python 3.10+ is required.

```bash
uv sync --all-packages
uv run pytest -q
```

## Code style

- Follow the existing style. Use type annotations and clear docstrings.
- New modules need unit tests; update the README or docs when behavior changes.

## Commits and pull requests

- Write clear commit messages; we suggest
  [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:` ...).
- Pull requests are squash-merged into `main` and need passing CI and a
  maintainer review.
- In the PR description, explain the problem, how your change fixes it, and
  how you tested it. Add a line to `CHANGELOG.md` under **Unreleased** for
  user-visible changes.

## Reporting issues

File issues with the issue templates. Include a minimal reproduction and any
relevant logs or input data (with sensitive data removed).

New issues are labeled `needs-triage`. A maintainer or committer reviews them,
applies labels (`bug`, `enhancement`, `good first issue`, ...), and removes
`needs-triage`. Pull requests automatically request review from the
maintainers team via `.github/CODEOWNERS`.

## Releasing (maintainers)

Packages are published to PyPI by `.github/workflows/release.yml` using
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — there are
no API tokens.

All four distributions (`niyamit-sphere`, `sphere-core`, `sphere-data`,
`sphere-flood`) share **one version** and pin each other exactly
(`sphere-core==X.Y.Z`); `tests/test_versions_lockstep.py` fails CI otherwise.

1. Open a release PR that:
   - sets the new version everywhere and relocks:
     `uv run python scripts/set_version.py X.Y.Z`;
   - moves the **Unreleased** notes in `CHANGELOG.md` under the new version
     and updates `version`/`date-released` in `CITATION.cff`.
2. Merge it, then tag the merge commit on `main` and push the tag:

   ```bash
   git switch main && git pull
   git tag -a sphere-vX.Y.Z -m "sphere vX.Y.Z"
   git push origin sphere-vX.Y.Z
   ```

3. The workflow checks that the tag matches the `pyproject.toml` version, runs
   the tests, and then waits for a maintainer to approve the `pypi`
   environment. After approval it publishes all four packages and creates the
   GitHub Release.

To rehearse, push a `test-sphere-vX.Y.Z` tag; it publishes to TestPyPI
instead.

## Security

Never commit secrets or credentials. **Do not open public issues for
vulnerabilities** — see [SECURITY.md](SECURITY.md) for private reporting.

Thank you for helping improve SPHERE!
