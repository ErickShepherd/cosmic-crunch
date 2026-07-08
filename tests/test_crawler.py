'''Crawler regex + URL-assembly tests over the saved listing fixtures (offline).'''

from unittest import mock

from cosmic_crunch import fetch


def _read(listings_dir, name):
    return (listings_dir / name).read_text()


def test_instrument_filter_over_root(listings_dir):
    html = _read(listings_dir, "00_glevels_root.html")
    urls = fetch.URL_REGEX.findall(html)
    cosmic = [u for u in urls if "cosmic" in u.lower()]
    assert cosmic == [f"cosmic{i}/" for i in range(1, 7)]


def test_year_regex_over_postproc(listings_dir):
    html = _read(listings_dir, "01_cosmic1_postproc.html")
    years = fetch.YEAR_URL_REGEX.findall(html)
    assert "y2006/" in years and "y2019/" in years
    assert len(years) == 14


def test_date_regex_over_year(listings_dir):
    html = _read(listings_dir, "02_cosmic1_postproc_y2006.html")
    dates = fetch.DATE_URL_REGEX.findall(html)
    assert "2006-05-01/" in dates
    assert all(d.count("-") == 2 for d in dates)


def test_format_regex_over_l2(listings_dir):
    html = _read(listings_dir, "04_cosmic1_2006-05-01_L2.html")
    formats = fetch.FORMAT_URL_REGEX.findall(html)
    assert set(formats) == {"nc/", "txt/"}


def test_data_regex_over_txt(listings_dir):
    html = _read(listings_dir, "05_cosmic1_2006-05-01_L2_txt.html")
    files = fetch.DATA_URL_REGEX.findall(html)
    assert files and all(f.endswith(".txt.gz") for f in files)
    # the .log / .glev / index siblings must be excluded
    assert not any(f.endswith(".log") or f.endswith(".glev") for f in files)


def test_crawl_cosmic_urls_assembly_single_slash(listings_dir):
    # _crawl_cosmic_urls builds ".../<instrument>/postproc" (single slash).
    html = _read(listings_dir, "00_glevels_root.html")
    response = mock.MagicMock()
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    response.raise_for_status.return_value = None
    response.content.decode.return_value = html
    with mock.patch.object(fetch.requests, "get", return_value=response):
        urls = fetch._crawl_cosmic_urls()
    assert urls[0] == "https://genesis.jpl.nasa.gov/ftp/glevels/cosmic1/postproc"
    assert "//postproc" not in urls[0]
    assert len(urls) == 6


def test_filename_regex_cosmic_and_non_cosmic():
    # FILENAME_REGEX must be instrument-agnostic (cosmic\d -> generic segment).
    cosmic = ("https://genesis.jpl.nasa.gov/ftp/glevels/cosmic1/postproc/"
              "y2006/2006-05-01/L2/txt/20060501_0632co1_g35_2p6.L2.txt.gz")
    champ = ("https://genesis.jpl.nasa.gov/ftp/glevels/champ/postproc/"
             "y2003/2003-06-15/L2/txt/20030615_1200chm_g44_1p0.L2.txt.gz")
    m1 = fetch.FILENAME_REGEX.match(cosmic)
    m2 = fetch.FILENAME_REGEX.match(champ)
    assert m1["year"] == "2006" and m1["dtg"] == "2006-05-01"
    assert m2["year"] == "2003" and m2["dtg"] == "2003-06-15"
    assert m2["filename"] == "20030615_1200chm_g44_1p0.L2.txt.gz"
