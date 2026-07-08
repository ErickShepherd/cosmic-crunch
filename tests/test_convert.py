'''crawl_convert multi-path / single-file conversion tests (offline).'''

import os
import shutil

from cosmic_crunch import convert


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
