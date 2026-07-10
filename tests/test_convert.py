'''crawl_convert multi-path / single-file conversion tests (offline).'''

import os
import shutil

import netCDF4

from cosmic_crunch import convert


def _first_variable_filters(ncf):
    '''Return the HDF5 filter dict of the first variable in the first group.'''
    with netCDF4.Dataset(ncf) as dataset:
        group    = next(iter(dataset.groups.values()))
        variable = next(iter(group.variables.values()))
        return variable.filters()


def _make_tree(root, src, name):
    txt_dir = os.path.join(root, "L2", "txt")
    os.makedirs(txt_dir)
    dst = os.path.join(txt_dir, name)
    shutil.copy(src, dst)
    return dst


def test_crawl_convert_processes_all_paths(tmp_path, real_2006):
    # v1 returned inside the per-path loop -> only the first path converted.
    paths = []
    for i in (1, 2, 3):
        p = tmp_path / f"path{i}"
        _make_tree(str(p), str(real_2006), f"file{i}.L2.txt.gz")
        paths.append(str(p))

    codes = convert.crawl_convert(paths, processes=1)

    assert len(codes) == 3                 # all three paths, not just the first
    assert all(c == 0 for c in codes)
    for i in (1, 2, 3):
        ncf = tmp_path / f"path{i}" / "L2" / "nc" / f"file{i}.L2.nc"
        assert ncf.exists()


def test_single_file_conversion_creates_output_dir(tmp_path, real_2006):
    dst = _make_tree(str(tmp_path / "solo"), str(real_2006), "solo.L2.txt.gz")
    rc = convert.crawl_convert([dst], processes=1)
    assert rc == [0]
    assert (tmp_path / "solo" / "L2" / "nc" / "solo.L2.nc").exists()


def test_skip_empty_file(tmp_path, synthetic_empty):
    dst = _make_tree(str(tmp_path / "empty"), str(synthetic_empty), "empty.L2.txt.gz")
    # skip_empty=True -> code 1 (skipped)
    codes = convert.crawl_convert([dst], processes=1, skip_empty=True)
    assert codes == [1]


def test_output_is_uncompressed_by_default(tmp_path, real_2006):
    # Compression is opt-in: COSMIC files are many small variables, so zlib
    # inflates the common (small-profile) case. Default output stays raw.
    dst = _make_tree(str(tmp_path / "raw"), str(real_2006), "raw.L2.txt.gz")
    assert convert.crawl_convert([dst], processes=1) == [0]
    ncf = tmp_path / "raw" / "L2" / "nc" / "raw.L2.nc"
    assert _first_variable_filters(str(ncf))["zlib"] is False


def test_compress_opt_in_sets_zlib_and_level(tmp_path, real_2006):
    dst = _make_tree(str(tmp_path / "zip"), str(real_2006), "zip.L2.txt.gz")
    assert convert.crawl_convert(
        [dst], processes=1, compress=True, complevel=4
    ) == [0]
    filters = _first_variable_filters(
        str(tmp_path / "zip" / "L2" / "nc" / "zip.L2.nc")
    )
    assert filters["zlib"] is True
    assert filters["complevel"] == 4
