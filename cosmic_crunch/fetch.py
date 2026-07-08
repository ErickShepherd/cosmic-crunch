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
import os
import re
from typing import Callable
from typing import Dict
from typing import List

# %% Third party imports.
import requests

# %% Local application imports.
from cosmic_crunch._parallel import flatten
from cosmic_crunch._parallel import parallelize
from cosmic_crunch._parallel import retry_decorator
from cosmic_crunch.convert import crawl_convert

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
                    r"(?:\\|/)+(?:L2)*(?:\\|/)+(?P<filetype>txt)(?:\\|/)+"
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
FILES_TO_GET     = -1


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
    
    # TODO
    
    '''

    with requests.get(BASE_URL) as request:

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
def crawl_cosmic_urls(*args : List, **kwargs : Dict) -> Callable:
    
    '''
    
    Pickleable with decorator.
    
    # TODO
    
    '''
    
    return retry_decorator(_crawl_cosmic_urls)(*args, **kwargs)


# %% Function definition: _crawl_year_urls
def _crawl_year_urls(cosmic_url : str) -> List[str]:
    
    '''
        
    # TODO
    
    '''
             
    with requests.get(cosmic_url) as request:

        request.raise_for_status()

        content   = request.content.decode()
        year_urls = YEAR_URL_REGEX.findall(content)
        year_urls = [cosmic_url + "/" + year for year in year_urls]

    return year_urls


# %% Function definition: crawl_year_urls
def crawl_year_urls(*args : List, **kwargs : Dict):
    
    '''
    
    Pickleable with decorator.
    
    # TODO
    
    '''
    
    return retry_decorator(_crawl_year_urls)(*args, **kwargs)


# %% Function definition: _crawl_date_urls
def _crawl_date_urls(year_url : str) -> List[str]:
    
    '''
        
    # TODO
    
    '''
    
    with requests.get(year_url) as request:

        request.raise_for_status()

        content   = request.content.decode()
        date_urls = DATE_URL_REGEX.findall(content)
        date_urls = [year_url + "/" + date for date in date_urls]

    return date_urls


# %% Function definition: crawl_date_urls
def crawl_date_urls(*args : List, **kwargs : Dict) -> Callable:
    
    '''
    
    Pickleable with decorator.
    
    # TODO
    
    '''
    
    return retry_decorator(_crawl_date_urls)(*args, **kwargs)
          

# %% Function definition: _crawl_format_urls
def _crawl_format_urls(date_url : str) -> List[str]:
    
    '''
        
    # TODO
    
    '''
    
    with requests.get(date_url) as request:

        request.raise_for_status()

        content = request.content.decode()
        urls    = URL_REGEX.findall(content)

        if len([url for url in urls if DATA_LEVEL in url]) > 0:

            date_url += "/" + DATA_LEVEL

    with requests.get(date_url) as request:

        request.raise_for_status()

        content    = request.content.decode()
        format_urls = FORMAT_URL_REGEX.findall(content)
        format_urls = [date_url + "/" + url for url in format_urls]
                        
    return format_urls


# %% Function definition: crawl_format_urls
def crawl_format_urls(*args : List, **kwargs : Dict) -> Callable:
    
    '''
    
    Pickleable with decorator.
    
    # TODO
    
    '''
    
    return retry_decorator(_crawl_format_urls)(*args, **kwargs)
    

# %% Function definition: _crawl_data_urls
def _crawl_data_urls(format_url : str) -> List[str]:
    
    '''
        
    # TODO
    
    '''
        
    with requests.get(format_url) as request:

        request.raise_for_status()

        site_data = request.content.decode()
        filenames = DATA_URL_REGEX.findall(site_data)
        data_urls = [format_url + "/" + name for name in filenames]

    return data_urls


# %% Function definition: crawl_data_urls
def crawl_data_urls(*args : List, **kwargs : Dict) -> Callable:
    
    '''
    
    Pickleable with decorator.
    
    # TODO
    
    '''
    
    return retry_decorator(_crawl_data_urls)(*args, **kwargs)


# %% Function definition: _download_data_file
def _download_data_file(source_url : str) -> None:
    
    '''
        
    # TODO
    
    '''
    
    metadata = FILENAME_REGEX.match(source_url)

    year     = metadata["year"]
    dtg      = metadata["dtg"]
    filetype = metadata["filetype"]
    filename = metadata["filename"]
    
    dst_directory = os.path.join(SAVE_DIRECTORY, year)
    dst_directory = os.path.join(dst_directory,  dtg)
    dst_directory = os.path.join(dst_directory,  filetype)
    
    if not os.path.exists(dst_directory):
        
        os.makedirs(dst_directory)
    
    dst_path = os.path.join(dst_directory, filename)
    
    with requests.get(source_url, stream = True) as request:
            
        request.raise_for_status()
            
        with open(dst_path, "wb") as file:
                
            for chunk in request.iter_content(chunk_size = CHUNK_SIZE):
                
                file.write(chunk)


# %% Function definition: download_data_file
def download_data_file(*args : List, **kwargs : Dict) -> Callable:
    
    '''
    
    Pickleable with decorator.
    
    # TODO
    
    '''
    
    return retry_decorator(_download_data_file)(*args, **kwargs)
    

# %% Function definition: crawl_site
def crawl_site(processes : int = PROCESSES) -> List[str]:
    
    '''
    
    # TODO
    
    '''
    
    cosmic_urls = crawl_cosmic_urls()
    
    year_desc = "Crawling all ./cosmic<#>/postproc"
    year_urls = flatten(parallelize(
        crawl_year_urls, cosmic_urls, year_desc, processes
    ))
    
    date_desc = "Crawling all ./cosmic<#>/.../<year>"
    date_urls = flatten(parallelize(
        crawl_date_urls, year_urls, date_desc, processes
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

