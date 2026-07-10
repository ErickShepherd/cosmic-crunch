#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''

cosmic_crunch.fetch: crawl the JPL GENESIS site and download COSMIC
radio-occultation ASCII data files.

Ported from the v1 ``get_files.py`` script (v1.3.1). The v1 per-file metadata
and AGPL header have been removed; the package is MIT-licensed (see LICENSE)
and versioned via ``cosmic_crunch.__version__``.

'''

# %% Standard library imports.
import functools
import logging
import os
import re
from typing import List
from typing import Optional
from typing import Pattern

# %% Third party imports.
import requests

# %% Local application imports.
from cosmic_crunch._parallel import flatten
from cosmic_crunch._parallel import parallelize
from cosmic_crunch._parallel import retry_decorator

# %% Dunder definitions.
__author__ = "Erick Edward Shepherd"

# %% Constant definitions.
URL_REGEX        = r"<a href=\"(?P<url>.*?)\""
YEAR_URL_REGEX   = r"<a href=\"(?P<url>y\d{4}/)\""
DATE_URL_REGEX   = r"<a href=\"(?P<url>\d{4}-\d{2}-\d{2}/)\""
DATA_URL_REGEX   = r"<a href=\"(?P<url>\S*?\.(?:txt\.gz))\""
FORMAT_URL_REGEX = r"<a href=\"(?P<url>\w+/)\""
# NOTE: the instrument segment is matched as a generic path segment
# (``[^\\/]+``) rather than a hardcoded ``cosmic\d``, so ``--instrument`` can
# select non-COSMIC trees (champ, gracea, ...). The URLs fed to this regex are
# already instrument-filtered upstream, so it only needs to extract the path
# fields, not re-validate the instrument.
FILENAME_REGEX   = (r".*(?:\\|/)+[^\\/]+(?:\\|/)+postproc(?:\\|/)+"
                    r"y(?P<year>\d{4})(?:\\|/)+(?P<dtg>\d{4}-\d{2}-\d{2})"
                    r"(?:\\|/)+(?:L2(?:\\|/)+)?(?P<filetype>txt)(?:\\|/)+"
                    r"(?P<filename>.*)")
URL_REGEX        = re.compile(URL_REGEX,        re.MULTILINE)
YEAR_URL_REGEX   = re.compile(YEAR_URL_REGEX,   re.MULTILINE)
DATE_URL_REGEX   = re.compile(DATE_URL_REGEX,   re.MULTILINE)
FORMAT_URL_REGEX = re.compile(FORMAT_URL_REGEX, re.MULTILINE)
DATA_URL_REGEX   = re.compile(DATA_URL_REGEX,   re.MULTILINE)
FILENAME_REGEX   = re.compile(FILENAME_REGEX,   re.DOTALL)
INSTRUMENT       = "cosmic"
DATA_DIRECTORY   = "postproc"
DATA_LEVEL       = "L2"
# New v2 crawl root (the v1 /ftp/pub/genesis/glevels root is dead -- see
# docs/site-notes.md). Overridable via the COSMIC_CRUNCH_BASE_URL env var and,
# with higher precedence, the `--base-url` CLI flag (handled in cli.run_get).
# No trailing slash: crawl functions build URLs as ``BASE_URL + "/" + segment``.
BASE_URL         = os.environ.get(
    "COSMIC_CRUNCH_BASE_URL",
    "https://genesis.jpl.nasa.gov/ftp/glevels",
)
SAVE_DIRECTORY   = os.path.abspath("./jpl_cosmic")
CHUNK_SIZE       = 2 ** 13
PROCESSES        = 1
FILES_TO_GET     = None
# (connect, read) timeout passed to every requests.get. requests has NO
# default timeout, so without this a black-holed connection blocks a worker
# forever -- and the bounded-retry wrapper never fires because no exception
# is raised. The read timeout applies per-chunk on streamed downloads, so
# large files are unaffected.
REQUEST_TIMEOUT  = (10, 60)


# %% Exception definitions.
class NoDataFilesFoundError(RuntimeError):

    '''

    Raised when a crawl completes successfully but finds zero data files.

    This is the v2 "fail loud" fix (design spine): the v1 crawler returned an
    empty list and the script exited *successfully having downloaded nothing*
    when the site moved. A zero-result crawl is now a loud error, not a silent
    no-op.

    '''


# %% Function definition: _crawl_cosmic_urls
def _crawl_cosmic_urls() -> List[str]:
    '''

    Crawl the site root (``BASE_URL``) and return the ``postproc`` directory
    URL for each instrument directory whose name contains ``INSTRUMENT``.

    '''

    with requests.get(BASE_URL, timeout = REQUEST_TIMEOUT) as request:

        request.raise_for_status()

        content     = request.content.decode()
        urls        = URL_REGEX.findall(content)
        cosmic_urls = [u for u in urls if INSTRUMENT in u.lower()]
        # rstrip the instrument segment's trailing "/" so the join yields
        # ".../<instrument>/postproc" (single slash), matching the reachable
        # URL confirmed in docs/site-notes.md -- not ".../<instrument>//postproc".
        cosmic_urls = [BASE_URL + "/" + u.rstrip("/") for u in cosmic_urls]
        cosmic_urls = [u + "/" + DATA_DIRECTORY for u in cosmic_urls]
    
    return cosmic_urls


# %% Function definition: crawl_cosmic_urls
def crawl_cosmic_urls(*args, **kwargs) -> List[str]:
    '''

    Retry-wrapped, pickleable wrapper around :func:`_crawl_cosmic_urls`
    (safe to use as a ``multiprocessing`` worker).

    '''

    return retry_decorator(_crawl_cosmic_urls)(*args, **kwargs)


# %% Function definition: _crawl_year_urls
def _crawl_year_urls(cosmic_url     : str,
                     year_url_regex : Optional[Pattern] = None) -> List[str]:
    '''

    Given an instrument ``postproc`` URL, return the URL of each of its year
    (``y<YYYY>/``) directories.

    The regex is a PARAMETER (defaulting to the module constant) rather than a
    module-global read so that a CLI-customized filter travels with the worker
    callable into ``multiprocessing`` pools under every start method: under
    ``spawn``/``forkserver`` (macOS/Windows default; Linux default from Python
    3.14) workers re-import this module fresh, so a rebound module global would
    be silently lost and the crawl would match everything.

    '''

    regex = YEAR_URL_REGEX if year_url_regex is None else year_url_regex

    with requests.get(cosmic_url, timeout = REQUEST_TIMEOUT) as request:

        request.raise_for_status()

        content   = request.content.decode()
        year_urls = regex.findall(content)
        year_urls = [cosmic_url.rstrip("/") + "/" + year for year in year_urls]

    return year_urls


# %% Function definition: crawl_year_urls
def crawl_year_urls(*args, **kwargs) -> List[str]:
    '''

    Retry-wrapped, pickleable wrapper around :func:`_crawl_year_urls`.

    '''

    return retry_decorator(_crawl_year_urls)(*args, **kwargs)


# %% Function definition: _crawl_date_urls
def _crawl_date_urls(year_url       : str,
                     date_url_regex : Optional[Pattern] = None) -> List[str]:
    '''

    Given a year-directory URL, return the URL of each of its date
    (``YYYY-MM-DD/``) directories.

    The regex is a parameter for the same spawn-safety reason as
    :func:`_crawl_year_urls`.

    '''

    regex = DATE_URL_REGEX if date_url_regex is None else date_url_regex

    with requests.get(year_url, timeout = REQUEST_TIMEOUT) as request:

        request.raise_for_status()

        content   = request.content.decode()
        date_urls = regex.findall(content)
        date_urls = [year_url.rstrip("/") + "/" + date for date in date_urls]

    return date_urls


# %% Function definition: crawl_date_urls
def crawl_date_urls(*args, **kwargs) -> List[str]:
    '''

    Retry-wrapped, pickleable wrapper around :func:`_crawl_date_urls`.

    '''

    return retry_decorator(_crawl_date_urls)(*args, **kwargs)
          

# %% Function definition: _crawl_format_urls
def _crawl_format_urls(date_url : str) -> List[str]:
    '''

    Given a date-directory URL, descend into the ``L2`` level and return the
    URL of each format (``txt/``, ``nc/``) directory beneath it.

    '''
    
    with requests.get(date_url, timeout = REQUEST_TIMEOUT) as request:

        request.raise_for_status()

        content = request.content.decode()
        urls    = URL_REGEX.findall(content)

        if len([url for url in urls if DATA_LEVEL in url]) > 0:

            date_url += "/" + DATA_LEVEL

    with requests.get(date_url, timeout = REQUEST_TIMEOUT) as request:

        request.raise_for_status()

        content    = request.content.decode()
        format_urls = FORMAT_URL_REGEX.findall(content)
        format_urls = [date_url.rstrip("/") + "/" + url for url in format_urls]
                        
    return format_urls


# %% Function definition: crawl_format_urls
def crawl_format_urls(*args, **kwargs) -> List[str]:
    '''

    Retry-wrapped, pickleable wrapper around :func:`_crawl_format_urls`.

    '''
    
    return retry_decorator(_crawl_format_urls)(*args, **kwargs)
    

# %% Function definition: _crawl_data_urls
def _crawl_data_urls(format_url : str) -> List[str]:
    '''

    Given a format-directory URL (e.g. ``.../L2/txt/``), return the URL of
    each ``.txt.gz`` data file it contains.

    '''
        
    with requests.get(format_url, timeout = REQUEST_TIMEOUT) as request:

        request.raise_for_status()

        site_data = request.content.decode()
        filenames = DATA_URL_REGEX.findall(site_data)
        data_urls = [format_url.rstrip("/") + "/" + name for name in filenames]

    return data_urls


# %% Function definition: crawl_data_urls
def crawl_data_urls(*args, **kwargs) -> List[str]:
    '''

    Retry-wrapped, pickleable wrapper around :func:`_crawl_data_urls`.

    '''
    
    return retry_decorator(_crawl_data_urls)(*args, **kwargs)


# %% Function definition: _download_data_file
def _download_data_file(source_url : str) -> None:

    '''

    Download a single COSMIC data file to ``SAVE_DIRECTORY/<year>/<dtg>/<type>/``.

    The download is **atomic**: content is streamed to a ``<name>.part``
    temporary file and then atomically ``os.replace``\\d into place, so an
    interrupted download never leaves a truncated final file (it restarts
    from scratch on the next run). A file that already exists with a size
    matching the server's ``Content-Length`` is skipped, so re-running a
    bulk pull only fetches what is missing.

    :param source_url: The fully-qualified URL of the data file to download.
    :type source_url: str

    '''

    logger = logging.getLogger("cosmic_crunch.fetch")

    metadata = FILENAME_REGEX.match(source_url)

    # A URL that does not follow the expected .../y<YYYY>/<date>/[L2/]txt/...
    # layout (plausible with --base-url mirrors) would otherwise surface as an
    # opaque, retried TypeError on the subscript below.
    if metadata is None:

        raise ValueError(
            f"URL does not match the expected COSMIC archive layout "
            f"(.../y<YYYY>/<YYYY-MM-DD>/[L2/]txt/<file>): {source_url!r}"
        )

    year     = metadata["year"]
    dtg      = metadata["dtg"]
    filetype = metadata["filetype"]
    filename = metadata["filename"]

    # The <filename> group is greedy and the listing it ultimately comes from
    # is remote content: a hostile or tampered listing could smuggle path
    # separators or ".." through an href and turn this into an arbitrary
    # filesystem write. Reduce it to a bare leaf name and refuse anything that
    # would resolve outside the save directory.
    filename = re.split(r"[\\/]+", filename)[-1]

    if filename in ("", ".", ".."):

        raise ValueError(
            f"Refusing unsafe filename derived from URL: {source_url!r}"
        )

    dst_directory = os.path.join(SAVE_DIRECTORY, year, dtg, filetype)
    dst_path      = os.path.join(dst_directory, filename)

    save_root = os.path.abspath(SAVE_DIRECTORY)

    if os.path.commonpath([os.path.abspath(dst_path), save_root]) != save_root:

        raise ValueError(
            f"Refusing to write outside the save directory: {dst_path!r} "
            f"(from URL {source_url!r})"
        )

    os.makedirs(dst_directory, exist_ok = True)

    part_path = dst_path + ".part"

    with requests.get(source_url, stream = True,
                      timeout = REQUEST_TIMEOUT) as request:

        request.raise_for_status()

        # Skip if the finished file already exists and its size matches the
        # server's Content-Length (a completed download; .part is never left in
        # place, so an existing dst_path is known-complete).
        expected_size = request.headers.get("Content-Length")

        if (os.path.exists(dst_path)
                and expected_size is not None
                and os.path.getsize(dst_path) == int(expected_size)):

            logger.info("Skipping already-downloaded file: %s", dst_path)

            return

        with open(part_path, "wb") as file:

            for chunk in request.iter_content(chunk_size = CHUNK_SIZE):

                file.write(chunk)

    # Atomic publish: rename the completed .part over the destination.
    os.replace(part_path, dst_path)


# %% Function definition: download_data_file
def download_data_file(*args, **kwargs) -> None:
    '''

    Retry-wrapped, pickleable wrapper around :func:`_download_data_file`.

    '''
    
    return retry_decorator(_download_data_file)(*args, **kwargs)
    

# %% Function definition: crawl_site
def crawl_site(processes      : int = PROCESSES,
               year_url_regex : Optional[Pattern] = None,
               date_url_regex : Optional[Pattern] = None) -> List[str]:
    '''

    Crawl the full instrument tree (root -> postproc -> year -> date -> L2 ->
    format) and return the URL of every ``.txt.gz`` data file found. Raises
    :class:`NoDataFilesFoundError` if the crawl finds nothing.

    Custom year/date filters are threaded to the pool workers as bound
    arguments (``functools.partial``), never as rebound module globals, so
    they survive every ``multiprocessing`` start method (compiled patterns
    pickle cleanly).

    '''

    cosmic_urls = crawl_cosmic_urls()

    year_desc = "Crawling all ./cosmic<#>/postproc"
    year_urls = flatten(parallelize(
        functools.partial(crawl_year_urls, year_url_regex = year_url_regex),
        cosmic_urls, year_desc, processes
    ))

    date_desc = "Crawling all ./cosmic<#>/.../<year>"
    date_urls = flatten(parallelize(
        functools.partial(crawl_date_urls, date_url_regex = date_url_regex),
        year_urls, date_desc, processes
    ))
    
    format_desc = "Crawling all ./cosmic<#>/.../<date>"
    format_urls = flatten(parallelize(
        crawl_format_urls, date_urls, format_desc, processes
    ))
    
    data_desc = "Crawling all ./cosmic<#>/.../L2/<format>"
    data_urls = flatten(parallelize(
        crawl_data_urls, format_urls, data_desc, processes
    ))

    # Fail loud: a crawl that found nothing is an error, not a silent success.
    if not data_urls:

        raise NoDataFilesFoundError(
            f"No data files found crawling {BASE_URL} for instrument "
            f"'{INSTRUMENT}'. The site layout may have changed, or the "
            f"year/date filters matched nothing. Check --base-url / "
            f"--instrument / --year_regex / --date_regex."
        )

    return data_urls

