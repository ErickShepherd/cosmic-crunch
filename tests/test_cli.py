'''CLI regression tests: filter splicing, exit codes, spawn-safe config
threading (offline).'''

import functools
import pickle

from unittest import mock

import pytest

from cosmic_crunch import cli
from cosmic_crunch import fetch


YEAR_LISTING = '<a href="y2006/">\n<a href="y2007/">\n<a href="y2019/">'
DATE_LISTING = '<a href="2006-05-01/">\n<a href="2006-05-02/">'


def _response(html):
    r = mock.MagicMock()
    r.__enter__.return_value = r
    r.__exit__.return_value = False
    r.raise_for_status.return_value = None
    r.content.decode.return_value = html
    return r


def test_year_regex_alternation_matches_all_alternatives():
    # Unwrapped, "2006|2007" would splice to y2006|2007/ -- matching neither.
    regex = cli._year_href_regex("2006|2007")
    assert regex.findall(YEAR_LISTING) == ["y2006/", "y2007/"]


def test_date_regex_alternation_matches_all_alternatives():
    regex = cli._date_href_regex("2006-05-01|2006-05-02")
    assert regex.findall(DATE_LISTING) == ["2006-05-01/", "2006-05-02/"]


def test_single_year_pattern_still_matches():
    assert cli._year_href_regex("2019").findall(YEAR_LISTING) == ["y2019/"]


def test_crawl_year_urls_uses_passed_regex_not_module_global():
    # The filter must arrive as a bound argument; module globals are lost
    # under the spawn/forkserver start methods (workers re-import fetch).
    with mock.patch.object(
        fetch.requests, "get", return_value=_response(YEAR_LISTING)
    ):
        urls = fetch._crawl_year_urls(
            "http://x/postproc", cli._year_href_regex("2006")
        )
    assert urls == ["http://x/postproc/y2006/"]


def test_crawl_date_urls_uses_passed_regex_not_module_global():
    with mock.patch.object(
        fetch.requests, "get", return_value=_response(DATE_LISTING)
    ):
        urls = fetch._crawl_date_urls(
            "http://x/y2006", cli._date_href_regex("2006-05-02")
        )
    assert urls == ["http://x/y2006/2006-05-02/"]


def test_custom_filter_partial_survives_pickling():
    # spawn transports the worker callable by pickling: the compiled filter
    # must round-trip with it, which is what makes the config spawn-safe.
    worker = functools.partial(
        fetch.crawl_year_urls,
        year_url_regex=cli._year_href_regex("2006|2007"),
    )
    clone = pickle.loads(pickle.dumps(worker))
    assert (clone.keywords["year_url_regex"].pattern
            == worker.keywords["year_url_regex"].pattern)
    assert clone.func is fetch.crawl_year_urls


def test_conversion_exit_code_semantics():
    assert cli._conversion_exit_code([0, 0, 1]) == 0   # skips are fine
    assert cli._conversion_exit_code([]) == 1          # nothing found
    assert cli._conversion_exit_code([0, 2]) == 1      # any error


def test_convert_zero_files_exits_nonzero(tmp_path, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(SystemExit) as excinfo:
        cli.main([
            "convert", str(empty),
            "--logfile", str(tmp_path / "cli-test.log"),
        ])
    assert excinfo.value.code == 1
    assert "no convertible" in capsys.readouterr().err
