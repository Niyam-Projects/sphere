# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Full-replacement cost basis option for NSI 2026 buildings.
- Interactive Marimo notebook, multi-raster analysis, and feet/meters unit conversion.
- DuckDB-based flood analysis pipeline with updated damage function methodology.
- `CITATION.cff`, `CHANGELOG.md`, Dependabot, CodeQL, and CODEOWNERS.

### Changed
- All packages now share one version (next release: 0.3.0) and pin each other
  exactly (`sphere-core==0.3.0`), so installs always get a tested-together set.
- Releases publish to PyPI via Trusted Publishing (OIDC) instead of API tokens.
- Expanded `SECURITY.md`, `CODE_OF_CONDUCT.md`, and `CONTRIBUTING.md`.

## [0.2.0] - 2025-09-22

- Latest published release of `niyamit-sphere` and `sphere-core`
  (`sphere-data` and `sphere-flood` at 0.1.3).

[Unreleased]: https://github.com/Niyam-Projects/sphere/compare/sphere-v0.2.0...HEAD
[0.2.0]: https://github.com/Niyam-Projects/sphere/releases/tag/sphere-v0.2.0
