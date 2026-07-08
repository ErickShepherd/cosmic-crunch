# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] — 2026-07-08

The 2020 JPL site restructure broke v1 (it silently downloaded nothing), and v1
carried latent security and correctness defects. v2 is a modernization: same
purpose, packaged, tested, and fixed.

### Added
- Packaged as the `cosmic_crunch` distribution with a single `cosmic-crunch`
  console entry point (`get` and `convert` subcommands) via `pyproject.toml`
  (hatchling); requires Python 3.10+.
- `--base-url` flag and `COSMIC_CRUNCH_BASE_URL` environment variable to override
  the crawl root.
- `--instrument` flag (default `cosmic`) to select other instrument trees
  (`champ`, `gracea`, `gracefo1`, …).
- Atomic, resumable downloads: stream to `<name>.part` then rename; skip files
  already present with a matching size.
- Offline `pytest` suite and a GitHub Actions CI workflow (ruff + pytest on
  Python 3.10–3.13 + `build`/`twine check`).
- `CHANGELOG.md` and `CITATION.cff`.

### Changed
- **New crawl root** `https://genesis.jpl.nasa.gov/ftp/glevels/` (the v1
  `/ftp/pub/genesis/glevels` root is dead).
- **Fail loud:** a crawl that finds zero data files now raises and exits
  non-zero instead of silently "succeeding" with nothing downloaded.
- **Bounded retry:** the v1 infinite silent retry is replaced with a bounded
  retry (default 3 attempts, exponential backoff, logged, re-raises on failure).
- Relicensed from AGPL-3.0 to **MIT**.
- Logging is configured only under the CLI, not at import time (importing the
  package no longer creates a stray log file).
- Deduplicated the copy-pasted `parallelize`/`flatten`/retry helpers into
  `cosmic_crunch/_parallel.py`; single-sourced `__version__`.

### Fixed
- **Security:** removed `eval()` of downloaded header content (arbitrary code
  execution); header values are parsed with `ast.literal_eval` + raw-string
  fallback, preserving brace-set element order.
- `crawl_convert` processed only the first path argument (a `return` inside the
  per-path loop, plus a `paths` shadowing typo) — it now converts all paths.
- Column-name loop-leak: rows of DataTypes with differing field counts were
  parsed with the wrong column names — each type now keeps its own columns.
- Single-file conversion creates its output directory; directory creation uses
  `os.makedirs(exist_ok=True)`.

### Migration
- The invocation changed: `python get_files.py …` / `python convert_files.py …`
  become `cosmic-crunch get …` / `cosmic-crunch convert …`. This is the breaking
  change behind the major version bump. There are no deprecation shims (the tool
  was never published and has no known downstream users).

## [1.3.x] — 2020–2021

The original two-script tool (unpackaged, AGPL-3.0, never published to PyPI):

- `get_files.py` (v1.3.1) — download JPL COSMIC ASCII data files. Created
  2020-12-11, last updated 2021-08-02.
- `convert_files.py` (v1.3.3) — convert COSMIC ASCII files to netCDF4. Created
  2021-01-28, last updated 2021-08-02.

[2.0.0]: https://github.com/ErickShepherd/cosmic_crunch/releases/tag/v2.0.0
