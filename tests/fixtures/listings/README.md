# Crawler listing fixtures — provenance

Raw Apache autoindex HTML for each directory level the crawler traverses, so the crawler
regex tests (item 12) run **fully offline**. **Retrieved:** 2026-07-08, read-only GET from
`https://genesis.jpl.nasa.gov/ftp/glevels/`. Saved verbatim (unmodified bytes).

## Why six listings, not the plan's illustrative "four levels"

Item 3 names "glevels root, an instrument, a year, a date dir" as *illustrative*. The v1
crawler (`get_files.py`) actually parses **six** distinct listings, and the literal-four
set would leave two regexes untestable, so the fixtures follow the crawler:

- The crawler **never lists the bare instrument dir** (`cosmic1/`): `_crawl_cosmic_urls`
  filters the root for `cosmic` substrings and *constructs* `…/cosmic1/postproc` directly
  (`DATA_DIRECTORY = "postproc"`), then lists `postproc/`. So `YEAR_URL_REGEX` runs on the
  **postproc** listing, not on `cosmic1/`.
- The `.txt.gz` files sit **two levels below** the date dir (`…/<date>/L2/txt/`), reached
  via `DATA_LEVEL = "L2"` detection then `FORMAT_URL_REGEX`. So `DATA_URL_REGEX` runs on the
  **L2/txt** listing.

| file | source path (under glevels root) | crawler step / regex it feeds | verified match |
|------|----------------------------------|-------------------------------|----------------|
| `00_glevels_root.html` | `/` | `_crawl_cosmic_urls`: `URL_REGEX` + `cosmic` substring filter | `cosmic1/`…`cosmic6/` found |
| `01_cosmic1_postproc.html` | `cosmic1/postproc/` | `_crawl_year_urls`: `YEAR_URL_REGEX` (`y\d{4}/`) | 14 years (y2006–y2019) |
| `02_cosmic1_postproc_y2006.html` | `cosmic1/postproc/y2006/` | `_crawl_date_urls`: `DATE_URL_REGEX` (`\d{4}-\d{2}-\d{2}/`) | 181 dates |
| `03_cosmic1_2006-05-01_date.html` | `cosmic1/postproc/y2006/2006-05-01/` | `_crawl_format_urls`: `URL_REGEX`, detect `DATA_LEVEL="L2"` | `L2/` present |
| `04_cosmic1_2006-05-01_L2.html` | `…/2006-05-01/L2/` | `_crawl_format_urls`: `FORMAT_URL_REGEX` (`\w+/`) | `nc/`, `txt/` |
| `05_cosmic1_2006-05-01_L2_txt.html` | `…/2006-05-01/L2/txt/` | `_crawl_data_urls`: `DATA_URL_REGEX` (`\S*?\.txt\.gz`) | 8 `.txt.gz` files |

## Notes for items 7 & 12

- **`FORMAT_URL_REGEX` (`\w+/`) matches BOTH `nc/` and `txt/`** at the L2 level, so the v1
  crawler descends into `nc/` too (where `DATA_URL_REGEX` finds zero `.txt.gz` — harmless
  but wasteful). Item 7 may want to restrict the format step to `txt/`; item 12 can assert
  the current both-formats behavior or the fixed txt-only behavior.
- **`DATA_URL_REGEX` correctly excludes** the sibling `.L2.txt.log`, `.L2.txt.glev`, and
  index files in the txt listing — the 8 matches are exactly the data files.
- The date-dir listing also contains `L1a/`, `L1b/`, `*.elog`, `doit.log`; `FORMAT_URL_REGEX`
  would match `L1a/`/`L1b/` too, but the `DATA_LEVEL="L2"` step scopes the descent to `L2/`.
- Full site map + naming grammar: `docs/site-notes.md`.
