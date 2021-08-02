#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''

A module to download JPL COSMIC data files.

Metadata:

    File:           get_files.py
    File version:   1.3.1
    Python version: 3.7.3
    Date created:   2020-12-11
    Last updated:   2021-08-02


Author(s):

    Erick Edward Shepherd
     - E-mail:  dev@erickshepherd.com
     - GitHub:  https://www.github.com/ErickShepherd
     - Website: https://www.ErickShepherd.com


Description:
    
    A module to crawl the JPL COSMIC website and download data files.


Copyright:
    
    Copyright (c) 2020 of Erick Edward Shepherd, all rights reserved.


License:
    
    This program is free software: you can redistribute it and/or modify it
    under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or (at your
    option) any later version.

    This program is distributed in the hope that it will be useful, but
    WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
    or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public
    License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.


To-do:

    - Document file and generalize it to allow scouring of specific years,
      months, or days.
      
    - Add argparse support for the number of processes to use.
    
    - Add logging.

'''

# %% Standard library imports.
import argparse
import multiprocessing
import os
import requests
import re
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List

# %% Third party imports.
from tqdm import tqdm

# %% Local application imports.
from convert_files import crawl_convert

# %% Dunder definitions.
__author__  = "Erick Edward Shepherd"
__version__ = "1.3.1"

# %% Constant definitions.
URL_REGEX        = r"<a href=\"(?P<url>.*?)\""
YEAR_URL_REGEX   = r"<a href=\"(?P<url>y\d{4}/)\""
DATE_URL_REGEX   = r"<a href=\"(?P<url>\d{4}-\d{2}-\d{2}/)\""
DATA_URL_REGEX   = r"<a href=\"(?P<url>\S*?\.(?:txt\.gz))\""
FORMAT_URL_REGEX = r"<a href=\"(?P<url>\w+/)\""
FILENAME_REGEX   = (r".*(?:\\|/)+cosmic\d(?:\\|/)+postproc(?:\\|/)+"
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
BASE_URL         = "https://genesis.jpl.nasa.gov/ftp/pub/genesis/glevels"
SAVE_DIRECTORY   = os.path.abspath("./jpl_cosmic")
CHUNK_SIZE       = 2 ** 13
PROCESSES        = 1
FILES_TO_GET     = -1


# %% Function definition: flatten
def flatten(list_of_lists : List[List]) -> List:
    
    '''
    
    # TODO
    
    '''
    
    return [element for sublist in list_of_lists for element in sublist]
    

# %% Function definition: parallelize
def parallelize(
        function  : Callable,
        domain    : Iterable,
        desc      : str  = None,
        processes : int  = PROCESSES,
        verbose   : bool = True,
        total     : int  = None) -> list:
    
    '''
    
    Parallelizes some task over a domain of arguments.
    
    :param function: The function to parallelize.
    :type function: Callable
    
    :param domain: The domain to use as function arguments.
    :type domain: Iterable
    
    :param processes: The number of pool processes to use for worker creation.
    :type processes: int
    
    :param desc: The description of the task being parallelized.
    :type desc: str
    
    :param verbose: Whether to print the `tqdm` progress bar.
    :type verbose: bool
    
    :param total: The total number of iterations expected.
    :type total: int
    
    :return: A list of collected return values from the paralleized function.
    :rtype: list
    
    '''
    
    # If not explicitly given, this computes the total from the length of the
    # domain.
    if total is None:
        
        total = len(domain)
    
    if processes > 1:
    
        # Instantiates the multiprocessing pool.
        with multiprocessing.Pool(processes) as pool:

            # Deterines whether or not to wrap the Pool.imap with a tqdm
            # progress bar.
            if verbose:

                results = list(tqdm(
                    pool.imap(function, domain),
                    total = total,
                    desc = desc
                ))

            else:

                results = list(pool.imap(function, domain))
                
    else:
        
        results = []
        
        # Deterines whether or not to wrap the domain with a tqdm progress bar.
        if verbose:
        
            for element in tqdm(domain, total = total, desc = desc):

                results.append(function(element))
                
        else:
            
            for element in domain:

                results.append(function(element))

    return results


# %% Function definition: retry_decorator
def retry_decorator(func : Callable) -> Callable:
    
    '''
    
    # TODO
    
    '''
    
    def wrapper(*args, **kwargs):
        
        retry    = True
        attempts = 0
        
        while retry:
            
            attempts += 1
            
            try:
        
                value = func(*args, **kwargs)
                retry = False
                
                return value
        
            except Exception:
                
                pass
        
    return wrapper
                

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
        cosmic_urls = [BASE_URL + "/" + u for u in cosmic_urls]
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
    
    return data_urls
    

# %% Main-multiprocessing hybrid entry point.
# - Allows CLI arguments to be shared between child processes.
if __name__ in ["__main__", "__mp_main__"]:
    
    parser = argparse.ArgumentParser(
        description = "A script to download COSMIC ASCII data files."
    )
    
    parser.add_argument(
        "--year_regex",
        type    = str,
        default = None,
        help    = (
            "An optional year regular expression to download. If given, all "
            "matching data files will be downloaded. Otherwise, every data "
            "file for every year will be downloaded."
        )
    )
    
    parser.add_argument(
        "--date_regex",
        type    = str,
        default = None,
        help    = (
            "An optional date regular expression to download. If given, all "
            "matching data files will be downloaded. Otherwise, every data "
            "file for every date will be downloaded."
        )
    )
    
    parser.add_argument(
        "--processes",
        type    = int,
        default = PROCESSES,
        help    = (
            "The number of processes to use in the multiprocessing pool. "
            f"Defaults to {PROCESSES}."
        )
    )
    
    parser.add_argument(
        "--test",
        dest   = "test_run",
        action = "store_true",
        help   = "Downloads a small subset of the data as a test."
    )
    
    parser.add_argument(
        "--netcdf4",
        dest   = "to_netcdf4",
        action = "store_true",
        help   = "Converts the ASCII data files to netCDF4."
    )
    
    parser.add_argument(
        "--skip_empty",
        dest   = "skip_empty",
        action = "store_true",
        help   = "Skips converting files whose arrays are all empty."
    )
    
    parser.set_defaults(test_run   = False)
    parser.set_defaults(to_netcdf4 = False)
    parser.set_defaults(skip_empty = False)
    
    argv   = parser.parse_args()
    kwargv = vars(argv)
    
    year_regex = kwargv["year_regex"]
    date_regex = kwargv["date_regex"]
    processes  = kwargv["processes"]
    test_run   = kwargv["test_run"]
    to_nc4     = kwargv["to_netcdf4"]
    skip_empty = kwargv["skip_empty"]
    
    if year_regex is not None:
        
        YEAR_URL_REGEX = r"<a href=\"(?P<url>y" + year_regex + r"/)\""
        YEAR_URL_REGEX = re.compile(YEAR_URL_REGEX, re.MULTILINE)

    if date_regex is not None:
        
        DATE_URL_REGEX = r"<a href=\"(?P<url>" + date_regex + r"/)\""
        DATE_URL_REGEX = re.compile(DATE_URL_REGEX, re.MULTILINE)
    
    if test_run:
        
        if year_regex is None:
            
            year_regex = "2019"
            
        if date_regex is None:
            
            date_regex = "2019-01-03"
        
        YEAR_URL_REGEX = r"<a href=\"(?P<url>y" + year_regex + r"/)\""
        DATE_URL_REGEX = r"<a href=\"(?P<url>" + date_regex + r"/)\""
        YEAR_URL_REGEX = re.compile(YEAR_URL_REGEX, re.MULTILINE)
        DATE_URL_REGEX = re.compile(DATE_URL_REGEX, re.MULTILINE)
        INSTRUMENT     = "cosmic1"
        FILES_TO_GET   = 10

# %% Main entry point.
# - Allows forking to start child processes.
if __name__ == "__main__":
    
    data_urls = crawl_site(processes)[:FILES_TO_GET]
    
    parallelize(
        download_data_file,
        data_urls,
        "Downloading data files",
        processes
    )
    
    if to_nc4:
        
        conversion_args  = ([SAVE_DIRECTORY], processes, skip_empty)
        completion_codes = crawl_convert(*conversion_args)
    
        total_conversions      = len(completion_codes)
        conversions_successful = completion_codes.count(0)
        conversions_skipped    = completion_codes.count(1)
        conversion_errors      = completion_codes.count(2)
        
        print(f"\nASCII to netCDF4 conversion summary:")
        print(f" - Successful conversions: {conversions_successful}")
        print(f" - Skipped conversions:    {conversions_skipped}")
        print(f" - Conversion errors:      {conversion_errors}")
        print(f" - Total number of files:  {total_conversions}")
