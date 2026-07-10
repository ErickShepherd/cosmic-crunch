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

NOTE: the ``get`` handler rebinds only the fetch globals that are read in the
PARENT process (BASE_URL, INSTRUMENT -- consumed by ``crawl_cosmic_urls``
before the pool starts). The year/date filters are compiled here and passed
through :func:`fetch.crawl_site` as worker arguments instead: a rebound module
global would be silently lost by the ``spawn``/``forkserver`` start methods
(macOS/Windows default; Linux default from Python 3.14), whose workers
re-import ``fetch`` fresh with the match-everything defaults.

'''

# %% Standard library imports.
import argparse
import logging
import re
import sys

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


# %% Function definition: _complevel
def _complevel(value : str) -> int:

    '''

    argparse ``type`` for ``--complevel``: parses an integer and rejects
    anything outside the netCDF4-valid zlib range of 1-9.

    '''

    try:

        level = int(value)

    except ValueError:

        raise argparse.ArgumentTypeError(f"{value!r} is not an integer")

    if not 1 <= level <= 9:

        raise argparse.ArgumentTypeError(
            f"compression level must be between 1 and 9, got {level} "
            "(compression is off unless --compress is given)"
        )

    return level


# %% Function definition: _year_href_regex
def _year_href_regex(year_pattern : str) -> "re.Pattern":

    '''

    Compiles the href-matching regex for a user-supplied year pattern. The
    user pattern is wrapped in a non-capturing group so alternation works:
    unwrapped, ``2006|2007`` would splice to ``y2006|2007/`` -- which matches
    neither ``y2006/`` nor ``y2007/`` in a listing.

    '''

    return re.compile(
        r"<a href=\"(?P<url>y(?:" + year_pattern + r")/)\"", re.MULTILINE
    )


# %% Function definition: _date_href_regex
def _date_href_regex(date_pattern : str) -> "re.Pattern":

    '''

    Compiles the href-matching regex for a user-supplied date pattern; wrapped
    in a non-capturing group for the same alternation reason as
    :func:`_year_href_regex`.

    '''

    return re.compile(
        r"<a href=\"(?P<url>(?:" + date_pattern + r")/)\"", re.MULTILINE
    )


# %% Function definition: _conversion_exit_code
def _conversion_exit_code(completion_codes : list) -> int:

    '''

    Maps a conversion tally to a process exit code: non-zero when nothing was
    found to convert or any file errored. The v2 fail-loud spine covered only
    ``get``; a conversion run that converted nothing must not exit 0 either
    (it silently breaks ``cosmic-crunch convert dir/ && next-step`` pipelines).

    '''

    if not completion_codes or 2 in completion_codes:

        return 1

    return 0


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
def run_get(args : argparse.Namespace) -> int:

    '''

    Handler for ``cosmic-crunch get``: crawl the site, download the ASCII data
    files, and optionally convert them to netCDF4. Returns a process exit
    code (0 on success).

    Ported from ``get_files.py``'s ``__main__`` block. The v1 ``FILES_TO_GET``
    default of ``-1`` silently dropped the last crawled URL on every run; v2
    defaults it to ``None`` (download everything) and caps at 10 only under
    ``--test``.

    '''

    # Resolve the parent-read configuration onto the fetch module globals.
    # Precedence for the base URL is: --base-url flag > COSMIC_CRUNCH_BASE_URL
    # env (already applied as fetch.BASE_URL's default at import) > built-in
    # default.
    if args.base_url is not None:

        fetch.BASE_URL = args.base_url

    fetch.INSTRUMENT = args.instrument

    # The year/date filters are threaded through crawl_site as worker
    # arguments (never module globals) so they survive spawn/forkserver
    # pools -- see the module docstring.
    year_url_regex = None
    date_url_regex = None

    if args.year_regex is not None:

        year_url_regex = _year_href_regex(args.year_regex)

    if args.date_regex is not None:

        date_url_regex = _date_href_regex(args.date_regex)

    files_to_get = fetch.FILES_TO_GET

    if args.test_run:

        year_url_regex = _year_href_regex(args.year_regex or "2019")
        date_url_regex = _date_href_regex(args.date_regex or "2019-01-03")

        fetch.INSTRUMENT = "cosmic1"
        files_to_get     = 10

    data_urls = fetch.crawl_site(
        args.processes, year_url_regex, date_url_regex
    )[:files_to_get]

    parallelize(
        fetch.download_data_file,
        data_urls,
        "Downloading data files",
        args.processes,
    )

    if args.to_netcdf4:

        completion_codes = convert.crawl_convert(
            [fetch.SAVE_DIRECTORY],
            args.processes,
            args.skip_empty,
            args.compress,
            args.complevel,
        )

        _print_conversion_summary(completion_codes)

        return _conversion_exit_code(completion_codes)

    return 0


# %% Function definition: run_convert
def run_convert(args : argparse.Namespace) -> int:

    '''

    Handler for ``cosmic-crunch convert``: convert one or more ASCII data files
    or directories of them to netCDF4. Ported from ``convert_files.py``.
    Returns a process exit code (0 on success).

    '''

    completion_codes = convert.crawl_convert(
        args.path,
        args.processes,
        args.skip_empty,
        args.compress,
        args.complevel,
    )

    _print_conversion_summary(completion_codes)

    if not completion_codes:

        print(
            "error: no convertible .txt/.txt.gz files found under the given "
            "path(s)",
            file = sys.stderr,
        )

    return _conversion_exit_code(completion_codes)


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
        "--base-url",
        dest    = "base_url",
        type    = str,
        default = None,
        help    = (
            "Override the crawl root URL. Precedence: this flag > the "
            "COSMIC_CRUNCH_BASE_URL environment variable > the built-in "
            f"default ({fetch.BASE_URL})."
        ),
    )

    get_parser.add_argument(
        "--logfile",
        type    = str,
        default = None,
        help    = (
            "A custom name to use for the log file. Overrides the default "
            f"\"{DEFAULT_LOG_FILENAME}\"."
        ),
    )

    get_parser.add_argument(
        "--instrument",
        type    = str,
        default = fetch.INSTRUMENT,
        help    = (
            "The instrument tree to crawl (a substring filter on the site's "
            f"instrument directories). Defaults to \"{fetch.INSTRUMENT}\"."
        ),
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

    get_parser.add_argument(
        "--compress",
        dest   = "compress",
        action = "store_true",
        help   = (
            "Losslessly zlib-compress the netCDF4 output. Off by default: "
            "COSMIC files are many small variables, so compression only "
            "shrinks large profiles and inflates small ones."
        ),
    )

    get_parser.add_argument(
        "--complevel",
        dest    = "complevel",
        type    = _complevel,
        default = convert.COMPRESS_COMPLEVEL,
        help    = (
            "The zlib compression level (1-9) for netCDF4 output. Defaults to "
            f"{convert.COMPRESS_COMPLEVEL}. Applies only with --compress."
        ),
    )

    get_parser.set_defaults(
        test_run   = False,
        to_netcdf4 = False,
        skip_empty = False,
        compress   = False,
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

    convert_parser.add_argument(
        "--compress",
        dest   = "compress",
        action = "store_true",
        help   = (
            "Losslessly zlib-compress the netCDF4 output. Off by default: "
            "COSMIC files are many small variables, so compression only "
            "shrinks large profiles and inflates small ones."
        ),
    )

    convert_parser.add_argument(
        "--complevel",
        dest    = "complevel",
        type    = _complevel,
        default = convert.COMPRESS_COMPLEVEL,
        help    = (
            "The zlib compression level (1-9) for netCDF4 output. Defaults to "
            f"{convert.COMPRESS_COMPLEVEL}. Applies only with --compress."
        ),
    )

    convert_parser.set_defaults(
        skip_empty = False,
        compress   = False,
        func       = run_convert,
    )

    return parser


# %% Function definition: main
def main(argv : list = None) -> None:

    '''

    Entry point for the ``cosmic-crunch`` console script.

    '''

    parser = build_parser()
    args   = parser.parse_args(argv)

    _configure_logging(getattr(args, "logfile", None))

    try:

        exit_code = args.func(args)

    except fetch.NoDataFilesFoundError as error:

        logging.getLogger("cosmic_crunch.cli").error(str(error))
        print(f"error: {error}", file = sys.stderr)

        raise SystemExit(1)

    if exit_code:

        raise SystemExit(exit_code)


# %% Console entry point.
if __name__ == "__main__":

    main()
