'''fetch: fail-loud zero-results + atomic/resumable download tests (offline).'''

from unittest import mock

import pytest

from cosmic_crunch import fetch


URL = ("https://x/ftp/glevels/cosmic1/postproc/y2006/2006-05-01/"
       "L2/txt/20060501_0632co1_g35_2p6.L2.txt.gz")


def _response(chunks, content_length, boom=False):
    r = mock.MagicMock()
    r.__enter__.return_value = r
    r.__exit__.return_value = False
    r.raise_for_status.return_value = None
    r.headers.get.return_value = content_length

    def iter_content(chunk_size=None):
        for c in chunks:
            yield c
        if boom:
            raise IOError("connection dropped")

    r.iter_content.side_effect = iter_content
    return r


def test_zero_result_crawl_raises(monkeypatch):
    monkeypatch.setattr(fetch, "crawl_cosmic_urls", lambda: [])
    monkeypatch.setattr(fetch, "parallelize", lambda *a, **k: [])
    with pytest.raises(fetch.NoDataFilesFoundError):
        fetch.crawl_site(processes=1)


def test_download_is_atomic(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "SAVE_DIRECTORY", str(tmp_path))
    payload = b"COSMIC" * 20
    dst = tmp_path / "2006" / "2006-05-01" / "txt" / "20060501_0632co1_g35_2p6.L2.txt.gz"

    with mock.patch.object(fetch.requests, "get",
                           return_value=_response([payload], str(len(payload)))):
        fetch._download_data_file(URL)

    assert dst.read_bytes() == payload
    assert not dst.with_suffix(dst.suffix + ".part").exists()


def test_download_skips_when_size_matches(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "SAVE_DIRECTORY", str(tmp_path))
    payload = b"COSMIC" * 20
    with mock.patch.object(fetch.requests, "get",
                           return_value=_response([payload], str(len(payload)))):
        fetch._download_data_file(URL)

    # second call with matching Content-Length must not re-download
    resp = _response([b"DIFFERENT"], str(len(payload)))
    with mock.patch.object(fetch.requests, "get", return_value=resp):
        fetch._download_data_file(URL)
    assert not resp.iter_content.called

    dst = tmp_path / "2006" / "2006-05-01" / "txt" / "20060501_0632co1_g35_2p6.L2.txt.gz"
    assert dst.read_bytes() == payload            # unchanged


def test_traversal_href_is_confined_to_save_directory(tmp_path, monkeypatch):
    # A hostile/tampered listing can smuggle "../" segments through the
    # <filename> regex group; the download must never write outside
    # SAVE_DIRECTORY (previously escaped via os.path.join + os.replace).
    save_dir = tmp_path / "save"
    outside  = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr(fetch, "SAVE_DIRECTORY", str(save_dir))

    evil_url = ("https://x/ftp/glevels/cosmic1/postproc/y2006/2006-05-01/"
                "L2/txt/../../../../../../outside/pwn.txt.gz")
    payload = b"owned"

    with mock.patch.object(fetch.requests, "get",
                           return_value=_response([payload], str(len(payload)))):
        fetch._download_data_file(evil_url)

    assert not (outside / "pwn.txt.gz").exists()
    confined = save_dir / "2006" / "2006-05-01" / "txt" / "pwn.txt.gz"
    assert confined.read_bytes() == payload


def test_irreducible_unsafe_filename_raises(tmp_path, monkeypatch):
    # A filename that reduces to "" / "." / ".." after stripping path
    # separators has no safe leaf to write, so it must raise rather than guess.
    monkeypatch.setattr(fetch, "SAVE_DIRECTORY", str(tmp_path))
    evil_url = ("https://x/ftp/glevels/cosmic1/postproc/y2006/2006-05-01/"
                "L2/txt/decoy/..")

    with mock.patch.object(fetch.requests, "get",
                           return_value=_response([b"x"], "1")) as get_mock:
        with pytest.raises(ValueError):
            fetch._download_data_file(evil_url)

    assert not get_mock.called                     # refused before any fetch


def test_interrupted_download_leaves_no_truncated_file(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "SAVE_DIRECTORY", str(tmp_path))
    dst = tmp_path / "2006" / "2006-05-01" / "txt" / "20060501_0632co1_g35_2p6.L2.txt.gz"
    with mock.patch.object(fetch.requests, "get",
                           return_value=_response([b"partial"], "9999", boom=True)):
        with pytest.raises(IOError):
            fetch._download_data_file(URL)
    assert not dst.exists()                        # never published a truncated file


def test_nonconforming_url_raises_descriptive_error(tmp_path, monkeypatch):
    # A mirror URL outside the .../y<YYYY>/<date>/[L2/]txt/... layout used to
    # surface as an opaque, retried TypeError on the regex match result.
    monkeypatch.setattr(fetch, "SAVE_DIRECTORY", str(tmp_path))
    with pytest.raises(ValueError, match="archive layout"):
        fetch._download_data_file("https://mirror.example/files/data.txt.gz")
