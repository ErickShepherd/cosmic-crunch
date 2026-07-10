# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.1] — 2026-07-10

Review-driven fix batch (independent multi-model review + follow-up
audit) plus the Read the Docs site configuration in a tag, fixing
RTD's tag-based "stable" build.

### Fixed
- `--year_regex`/`--date_regex` are now threaded to multiprocessing
  workers as bound arguments instead of rebound module globals, so they
  survive the `spawn`/`forkserver` start methods (macOS/Windows default;
  Linux default from Python 3.14). Previously `--processes > 1` on those
  platforms silently ignored the filters and crawled the entire archive.
- Every `requests.get` now has a (connect, read) timeout; a stalled
  connection previously hung a worker forever with the bounded retry
  never firing.
- User patterns with alternation (`--year_regex '2006|2007'`) now match
  all alternatives; the unwrapped splice previously matched nothing.
- `cosmic-crunch convert` exits non-zero when nothing was found to
  convert or any file errored (previously exited 0 on total failure).
- The `txt` → `nc` output rewrite fires only on path segments named
  exactly `txt`; segments merely starting with `txt` (e.g.
  `txt_originals/`) are no longer mangled.
- `FILENAME_REGEX` accepts archive layouts without an `L2` level — a
  layout the crawler itself emits — instead of failing every such
  download; and no longer accepts a doubled `L2L2` segment.
- A URL outside the expected archive layout now raises a descriptive
  `ValueError` instead of an opaque, retried `TypeError`.
- Retry-wrapper return annotations corrected (they rendered wrong types
  into the API docs); module-qualified logger names in `convert`;
  user-facing typo fixes.

### Added
- Sphinx documentation site hosted on Read the Docs
  (<https://cosmic-crunch.readthedocs.io/>); `Documentation` URL in the
  PyPI project links.
- README: "Use from Python" section (library conversion + parsing, and
  the `xarray.open_dataset(..., group=...)` read-back the grouped netCDF
  layout requires), RO/GNSS-RO keywords, and a UCAR-CDAAC-vs-JPL-GENESIS
  disambiguation note.
- `cosmic-crunch get --logfile` (previously only `convert` had it;
  `get` always wrote `cosmic_crunch.log` to the working directory and
  crashed in a read-only one).

### Changed
- README converted to Markdown (renders on PyPI as `text/markdown`);
  shields.io DOI badge; `erickshepherd.com` backlink.

## [2.1.0] — 2026-07-10

### Added
- Optional lossless zlib compression of netCDF4 output: `--compress` and
  `--complevel` CLI flags (on `get` and `convert`), and `compress`/`complevel`
  parameters on `crawl_convert`, `convert_cosmic_file`, and
  `write_cosmic_netcdf4_file`. Off by default — a COSMIC file is many small
  variables, so HDF5's per-variable overhead makes compression inflate short
  profiles and only pay off for long ones (crossover ≈ 1000 levels). See the
  README "Compression" section.
- `.zenodo.json` and an author ORCID in `CITATION.cff`, so a Zenodo release
  archive registers a citable DOI with correct software metadata.

## [2.0.2] — 2026-07-09

Docs/packaging only — no code changes.

### Changed
- Added a "Problems this solves" section to the README, mapping common
  natural-language queries (bulk-downloading COSMIC-1 radio-occultation data,
  converting Level-2 ASCII profiles to netCDF4) to the tool.
- Enriched packaging metadata: trove classifiers, expanded keywords, and
  `Source` and `Bug Tracker` project URLs.

## [2.0.1] — 2026-07-08

Docs/packaging only — no code changes.

### Changed
- README now leads installation with `pip install cosmic-crunch` (the package is
  published on PyPI), keeping the editable install as the contributor path. The
  v2.0.0 PyPI page had been built before this fix and still showed
  `pip install -e .`; this release republishes with the corrected instructions.
- Repo/project URLs point at the renamed `cosmic-crunch` GitHub slug.

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
- **Security:** path traversal in downloads — a hostile or tampered directory
  listing could smuggle `../` through a filename and write outside the save
  directory. Downloaded filenames are now reduced to a bare leaf and confined
  to the save root (irreducible unsafe names are rejected before any fetch).
- The v1 `FILES_TO_GET = -1` default silently dropped the last crawled file on
  every non-test run (`[:-1]`); it now defaults to downloading everything.
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

[2.1.1]: https://github.com/ErickShepherd/cosmic-crunch/releases/tag/v2.1.1
[2.1.0]: https://github.com/ErickShepherd/cosmic-crunch/releases/tag/v2.1.0
[2.0.2]: https://github.com/ErickShepherd/cosmic-crunch/releases/tag/v2.0.2
[2.0.1]: https://github.com/ErickShepherd/cosmic-crunch/releases/tag/v2.0.1
[2.0.0]: https://github.com/ErickShepherd/cosmic-crunch/releases/tag/v2.0.0
