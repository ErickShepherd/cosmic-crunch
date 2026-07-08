#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''

Command-line interface for cosmic_crunch.

A single ``cosmic-crunch`` console entry point with two subcommands:

    cosmic-crunch get      -- crawl the GENESIS site and download ASCII files
    cosmic-crunch convert  -- convert downloaded ASCII files to netCDF4

This module owns ALL logging configuration (plan item 5): logging is configured
here in ``main()`` at run time, never at import time -- importing any
``cosmic_crunch`` submodule no longer creates a stray log file in the CWD.

NOTE (v2 port): the ``get`` handler still drives the crawler by rebinding module
globals on ``cosmic_crunch.fetch`` (INSTRUMENT, the year/date regexes, ...),
mirroring v1 behavior exactly. Turning that configuration into real flags
(``--base-url``, ``--instrument``) and fixing the crawler is Phase 3 (items 7-8).

'''

# %% Standard library imports.
import argparse
import logging
import re

# %% Local application imports.
from cosmic_crunch import __version__
from cosmic_crunch import convert
from cosmic_crunch import fetch
from cosmic_crunch._parallel import parallelize

# %% Constant definitions.
LOGGER_FORMAT        = "%(asctime)-19s || %(levelname)-8s || %(name)s :: %(message)s"
DEFAULT_LOG_FILENAME = "cosmic_crunch.log"


# %% Function definition: _configure_logging
def _configure_logging(logfile : str = None) -> None:

    '''

    Configures root logging to a file. Called once from ``main()`` at run time
    (never at import time), so importing the package has no logging side effect.

    :param logfile: Optional log-file path; defaults to ``cosmic_crunch.log``.
    :type logfile: str

    '''

    logging.basicConfig(
        level    = logging.INFO,
        format   = LOGGER_FORMAT,
        handlers = [logging.FileHandler(logfile or DEFAULT_LOG_FILENAME)],
    )


# %% Function definition: _print_conversion_summary
def _print_conversion_summary(completion_codes : list) -> None:

    '''

    Prints the ASCII-to-netCDF4 conversion tally (ported from the v1 scripts).

    :param completion_codes: Integer completion codes (0 ok, 1 skip, 2 error).
    :type completion_codes: list

    '''

    total_conversions      = len(completion_codes)
    conversions_successful = completion_codes.count(0)
    conversions_skipped    = completion_codes.count(1)
    conversion_errors      = completion_codes.count(2)

    print("\nASCII to netCDF4 conversion summary:")
    print(f" - Successful conversions: {conversions_successful}")
    print(f" - Skipped conversions:    {conversions_skipped}")
    print(f" - Conversion errors:      {conversion_errors}")
    print(f" - Total number of files:  {total_conversions}")


# %% Function definition: run_get
def run_get(args : argparse.Namespace) -> None:

    '''

    Handler for ``cosmic-crunch get``: crawl the site, download the ASCII data
    files, and optionally convert them to netCDF4.

    Ported verbatim from ``get_files.py``'s ``__main__`` block, including the
    ``[:FILES_TO_GET]`` slice (v1 default -1 drops the last URL -- preserved
    here for behavior parity; a Phase-3 concern, not this port's).

    '''

    if args.year_regex is not None:

        fetch.YEAR_URL_REGEX = re.compile(
            r"<a href=\"(?P<url>y" + args.year_regex + r"/)\"", re.MULTILINE
        )

    if args.date_regex is not None:

        fetch.DATE_URL_REGEX = re.compile(
            r"<a href=\"(?P<url>" + args.date_regex + r"/)\"", re.MULTILINE
        )

    files_to_get = fetch.FILES_TO_GET

    if args.test_run:

        year_regex = args.year_regex if args.year_regex is not None else "2019"
        date_regex = args.date_regex if args.date_regex is not None else "2019-01-03"

        fetch.YEAR_URL_REGEX = re.compile(
            r"<a href=\"(?P<url>y" + year_regex + r"/)\"", re.MULTILINE
        )
        fetch.DATE_URL_REGEX = re.compile(
            r"<a href=\"(?P<url>" + date_regex + r"/)\"", re.MULTILINE
        )
        fetch.INSTRUMENT   = "cosmic1"
        files_to_get       = 10

    data_urls = fetch.crawl_site(args.processes)[:files_to_get]

    parallelize(
        fetch.download_data_file,
        data_urls,
        "Downloading data files",
        args.processes,
    )

    if args.to_netcdf4:

        completion_codes = convert.crawl_convert(
            [fetch.SAVE_DIRECTORY], args.processes, args.skip_empty
        )

        _print_conversion_summary(completion_codes)


# %% Function definition: run_convert
def run_convert(args : argparse.Namespace) -> None:

    '''

    Handler for ``cosmic-crunch convert``: convert one or more ASCII data files
    or directories of them to netCDF4. Ported from ``convert_files.py``.

    '''

    completion_codes = convert.crawl_convert(
        args.path, args.processes, args.skip_empty
    )

    _print_conversion_summary(completion_codes)


# %% Function definition: build_parser
def build_parser() -> argparse.ArgumentParser:

    '''

    Builds the ``cosmic-crunch`` argument parser with ``get`` and ``convert``
    subcommands, reusing the v1 flag set.

    '''

    parser = argparse.ArgumentParser(
        prog        = "cosmic-crunch",
        description = (
            "Download JPL GENESIS COSMIC radio-occultation ASCII data files "
            "and convert them to netCDF4."
        ),
    )

    parser.add_argument(
        "--version",
        action  = "version",
        version = f"cosmic-crunch {__version__}",
    )

    subparsers = parser.add_subparsers(dest = "command", required = True)

    # -- get --------------------------------------------------------------- #
    get_parser = subparsers.add_parser(
        "get",
        help        = "Download COSMIC ASCII data files from the GENESIS site.",
        description = "Crawl the GENESIS site and download COSMIC ASCII files.",
    )

    get_parser.add_argument(
        "--year_regex",
        type    = str,
        default = None,
        help    = (
            "An optional year regular expression to download. If given, all "
            "matching data files will be downloaded. Otherwise, every data "
            "file for every year will be downloaded."
        ),
    )

    get_parser.add_argument(
        "--date_regex",
        type    = str,
        default = None,
        help    = (
            "An optional date regular expression to download. If given, all "
            "matching data files will be downloaded. Otherwise, every data "
            "file for every date will be downloaded."
        ),
    )

    get_parser.add_argument(
        "--processes",
        type    = int,
        default = fetch.PROCESSES,
        help    = (
            "The number of processes to use in the multiprocessing pool. "
            f"Defaults to {fetch.PROCESSES}."
        ),
    )

    get_parser.add_argument(
        "--test",
        dest   = "test_run",
        action = "store_true",
        help   = "Downloads a small subset of the data as a test.",
    )

    get_parser.add_argument(
        "--netcdf4",
        dest   = "to_netcdf4",
        action = "store_true",
        help   = "Converts the ASCII data files to netCDF4 after download.",
    )

    get_parser.add_argument(
        "--skip_empty",
        dest   = "skip_empty",
        action = "store_true",
        help   = "Skips converting files whose arrays are all empty.",
    )

    get_parser.set_defaults(
        test_run   = False,
        to_netcdf4 = False,
        skip_empty = False,
        func       = run_get,
    )

    # -- convert ----------------------------------------------------------- #
    convert_parser = subparsers.add_parser(
        "convert",
        help        = "Convert COSMIC ASCII data files to netCDF4.",
        description = (
            "Create inplace netCDF4 copies of COSMIC ASCII gzip-compressed "
            "data files."
        ),
    )

    convert_parser.add_argument(
        "path",
        type  = str,
        nargs = "+",
        help  = (
            "The path to one or more COSMIC ASCII gzip-compressed data files "
            "or directories containing them. If one or more directories are "
            "given, they will be crawled recursively."
        ),
    )

    convert_parser.add_argument(
        "--logfile",
        type    = str,
        default = None,
        help    = (
            "A custom name to use for the log file. Overrides the default "
            f"\"{DEFAULT_LOG_FILENAME}\"."
        ),
    )

    convert_parser.add_argument(
        "--processes",
        type    = int,
        default = convert.PROCESSES,
        help    = (
            "The number of processes to use in the multiprocessing pool. "
            f"Defaults to {convert.PROCESSES}."
        ),
    )

    convert_parser.add_argument(
        "--skip_empty",
        dest   = "skip_empty",
        action = "store_true",
        help   = "Skips converting files whose arrays are all empty.",
    )

    convert_parser.set_defaults(skip_empty = False, func = run_convert)

    return parser


# %% Function definition: main
def main(argv : list = None) -> None:

    '''

    Entry point for the ``cosmic-crunch`` console script.

    '''

    parser = build_parser()
    args   = parser.parse_args(argv)

    _configure_logging(getattr(args, "logfile", None))

    args.func(args)


# %% Console entry point.
if __name__ == "__main__":

    main()
