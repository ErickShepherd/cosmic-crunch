# cosmic-crunch

[![CI](https://github.com/ErickShepherd/cosmic-crunch/actions/workflows/ci.yml/badge.svg)](https://github.com/ErickShepherd/cosmic-crunch/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)

Download JPL GENESIS **COSMIC** radio-occultation ASCII data files and convert
them to **netCDF4**.

`cosmic-crunch` crawls the [JPL GENESIS](https://genesis.jpl.nasa.gov) data
archive, downloads the Level-2 ASCII occultation profiles, and (optionally)
converts them into self-describing netCDF4 files.

> **Site restructure note (2020 → 2026).** JPL restructured the GENESIS site: the
> old crawl root (`/ftp/pub/genesis/glevels`) is dead, so v1 of this tool silently
> "succeeded" while downloading nothing. v2 targets the current root
> `https://genesis.jpl.nasa.gov/ftp/glevels/` and **fails loudly** — a crawl that
> finds nothing exits non-zero instead of pretending to succeed.
>
> **Mission status.** COSMIC-1 (FORMOSAT-3, flight modules FM1–FM6, served here as
> `cosmic1/`–`cosmic6/`) was decommissioned in 2020, so this is a **static
> archive** — the data has stopped changing. (COSMIC-2 is a different mission on a
> different archive and is out of scope.)

## Installation

```bash
pip install cosmic-crunch
```

This installs the `cosmic-crunch` command with two subcommands, `get` and
`convert`. Python 3.10+ is required.

To hack on the package itself, install from a clone instead:
`pip install -e .` (or `pip install -e ".[test]"` to run the test suite).

## Usage

`cosmic-crunch` has a single entry point with two subcommands:

```bash
cosmic-crunch get      # crawl the GENESIS site and download ASCII files
cosmic-crunch convert  # convert downloaded ASCII files to netCDF4
```

### `cosmic-crunch get`

```
usage: cosmic-crunch get [-h] [--base-url BASE_URL] [--instrument INSTRUMENT]
                         [--year_regex YEAR_REGEX] [--date_regex DATE_REGEX]
                         [--processes PROCESSES] [--test] [--netcdf4]
                         [--skip_empty]
```

| flag | description |
|------|-------------|
| `--base-url` | Override the crawl root. Precedence: flag > `COSMIC_CRUNCH_BASE_URL` env var > built-in default (`https://genesis.jpl.nasa.gov/ftp/glevels`). |
| `--instrument` | Instrument tree to crawl (substring filter). Defaults to `cosmic` (matches `cosmic1`–`cosmic6`); the same archive also serves `champ`, `gracea`, `gracefo1`, … |
| `--year_regex` | Download only years matching this regular expression. |
| `--date_regex` | Download only dates matching this regular expression. |
| `--processes` | Worker processes for the `multiprocessing` pool (default `1`). |
| `--test` | Download a small subset (cosmic1, 2019-01-03, 10 files) as a smoke test. |
| `--netcdf4` | Convert the downloaded ASCII files to netCDF4 afterward. |
| `--skip_empty` | Skip converting files whose data arrays are all empty. |

Downloads are **atomic and resumable**: each file is streamed to a `.part`
temporary and renamed into place only once complete, and files already present
with a matching size are skipped — so an interrupted bulk pull can simply be
re-run.

A successful run resembles:

```
$ cosmic-crunch get --year_regex=2006 --date_regex=2006-05-02 --netcdf4 --skip_empty --processes=4
Crawling all ./cosmic<#>/postproc: 100%|████████████████████| 6/6 [00:03<00:00,  1.61it/s]
Crawling all ./cosmic<#>/.../<year>: 100%|██████████████████| 6/6 [00:03<00:00,  1.59it/s]
Crawling all ./cosmic<#>/.../<date>: 100%|██████████████████| 3/3 [00:03<00:00,  1.17s/it]
Crawling all ./cosmic<#>/.../L2/<format>: 100%|█████████████| 4/4 [00:04<00:00,  1.09s/it]
Downloading data files: 100%|███████████████████████████████| 20/20 [00:26<00:00,  1.33s/it]
Converting ASCII to netCDF4: 100%|██████████████████████████| 20/20 [00:03<00:00,  6.32it/s]

ASCII to netCDF4 conversion summary:
 - Successful conversions: 17
 - Skipped conversions:    3
 - Conversion errors:      0
 - Total number of files:  20
```

Downloaded files are written under `./jpl_cosmic/<year>/<date>/txt/`.

### `cosmic-crunch convert`

```
usage: cosmic-crunch convert [-h] [--logfile LOGFILE] [--processes PROCESSES]
                             [--skip_empty]
                             path [path ...]
```

Convert one or more ASCII `.txt.gz` files — or directories of them (crawled
recursively) — to netCDF4. netCDF4 files are written into a sibling `nc/`
directory (mirroring the `txt/` layout), or beside the source file otherwise.

```bash
cosmic-crunch convert ./jpl_cosmic/2006/ --skip_empty --processes=4
```

## netCDF4 output structure

Each ASCII file becomes one netCDF4 file. The ASCII header becomes **global
attributes**; each DataType profile becomes a **group** whose variables are that
profile's columns, indexed by an `Index` dimension:

```
netcdf 20060501_0632co1_g35_2p6.L2 {
  // global attributes: ProductCreationTime, ShortName, DataSetID,
  //                     PlatformShortName, Receiver, ... (the ASCII header)

  group: COSMIC1-Profile {
    dimensions:  Index = <n> ;
    variables:   Height, Lat, Lon, Refractivity, Temperature, Pressure, WV Pressure ;
  }
  group: ECMWF-Profile {
    dimensions:  Index = <n> ;
    variables:   Height, Lat, Lon, Refractivity, Temperature, Pressure, WV Pressure ;
  }
}
```

Missing values in the ASCII data (`-9999`) are stored as `NaN`.

## Security note

v1 parsed header values with `eval()`, allowing arbitrary code execution from a
malicious or corrupted data file. v2 uses `ast.literal_eval` with a raw-string
fallback — header parsing can no longer execute code.

## Development

```bash
pip install -e ".[test]"
python -m pytest -q        # offline test suite (never touches the network)
ruff check .
```

## License

MIT — see [LICENSE](LICENSE).
