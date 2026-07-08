# Parser fixtures — provenance

Trimmed real GENESIS L2 ASCII files (plus one synthetic) for the offline parser tests
(items 12, 10). **Tests never touch the network** (design §Key decisions); these committed
fixtures are the parser's ground truth.

**Retrieved:** 2026-07-08, read-only GET from `https://genesis.jpl.nasa.gov/ftp/glevels/`.
**Trim:** each real file keeps its **full header** (all `key = value` lines, 63 of them)
plus the **first 20 data rows**, re-gzipped. The header is preserved verbatim; only the
long data body is truncated, so header-parsing and multi-DataType body-parsing are both
exercised while the fixtures stay small (<2 KB each). Trim is loss-of-tail only — no field
was edited.

| file | source URL (under the glevels root) | real? | DataTypes | rows kept | purpose |
|------|-------------------------------------|-------|-----------|-----------|---------|
| `20060501_0632co1_g35_2p6.L2.txt.gz` | `cosmic1/postproc/y2006/2006-05-01/L2/txt/20060501_0632co1_g35_2p6.L2.txt.gz` | real | `COSMIC1-Profile` (68) + `ECMWF-Profile` (82) | 20 (10×68, 10×82) | early-mission multi-DataType parse |
| `20190103_0000co1_g72_2p6.L2.txt.gz` | `cosmic1/postproc/y2019/2019-01-03/L2/txt/20190103_0000co1_g72_2p6.L2.txt.gz` | real | `COSMIC1-Profile` (68) + `NCEP_FNL-Profile` (83) | 20 (10×68, 10×83) | late-mission multi-DataType parse (different second type) |
| `cosmic1_SYNTHETIC_empty-data.L2.txt.gz` | derived from the 2006 file above | **synthetic** | header declares 68 + 82 | 0 | the empty-data / `--skip_empty` path (`raw_data.empty`) |
| `cosmic1_SYNTHETIC_multitype-differing-width.L2.txt.gz` | hand-authored | **synthetic** | `TypeWide` (68, 6 fields) + `TypeNarrow` (82, 3 fields) | 4 (2×68, 2×82) | the column-name loop-leak fix (item 10) — needs *differing* field counts, which no real file has |

## Notes for downstream items

- **Header shape (for the `eval`→`literal_eval` fix, item 9):** header values include
  Python-literal-ish forms the old `eval()` consumed — quoted strings, numbers, brace
  **sets** (`ParameterName = {"Atmosphere", ...}`, `DataTypeName = { "COSMIC1-Profile",
  "ECMWF-Profile" }`), brace **tuples of numbers** (`CenterOfCurvature = { -.33E+01, ... }`),
  and bare tokens that are *not* valid literals (`AS = ON`, `Receiver = cosmic1`,
  `TrackingModes = Closedloop_Openloop`) which must fall back to raw string. The set→tuple
  order-preserving case (v1 `convert_files.py:166`) is present. Any malicious-header test
  fixture (item 12) should be authored separately and labeled — do not fetch one.
- **Column-leak fix (item 10) — synthetic differing-width fixture PROVIDED**
  (`cosmic1_SYNTHETIC_multitype-differing-width.L2.txt.gz`, added in item 10). Both real
  files above have two DataTypes with the *same* 7 fields
  (`Height, Lat, Lon, Refractivity, Temperature, Pressure, WV Pressure`), so the loop-leak
  bug (`names=[..., *data_types[dtype_name]["fields"]]` using the post-loop `dtype_name`)
  was **invisible** on them — every row parses identically regardless of the bug. The
  synthetic file has DataTypes of *differing* field counts (6 vs 3) so item 12 can
  actually expose/verify the fix (design §Key decisions permits labeled synthetics).
- **Missing value sentinel** is `-9999` (mapped to NaN via `na_values` in the reader).
- Full site layout + naming grammar: `docs/site-notes.md`.
