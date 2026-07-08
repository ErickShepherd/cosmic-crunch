#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''

A module to convert JPL COSMIC data files from ASCII to netCDF4.

Metadata:

    File:           convert_files.py
    File version:   1.3.3
    Python version: 3.7.3
    Date created:   2021-01-28
    Last updated:   2021-08-02


Author(s):

    Erick Edward Shepherd
     - E-mail:  dev@erickshepherd.com
     - GitHub:  https://www.github.com/ErickShepherd
     - Website: https://www.ErickShepherd.com


Description:
    
    A module to convert JPL COSMIC data files from a gzip-compressed ASCII
    storage format to the netCDF4 standard.


Copyright:
    
    Copyright (c) 2021 of Erick Edward Shepherd, all rights reserved.


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

    - Switch from using `.endswith(".txt.gz")` to the use of a regular
      expression to better discriminate between data files during recursive
      file crawling.
            
    - Catch cases where a file is missing a header, missing data, or both
      (empty).
            
    - Update the logging to use a rotating file handler.
    
    - Add option to erase ASCII file upon conversion.

'''

# %% Standard library imports.
import argparse
import gzip
import logging
import os
import re
import sys
from functools import partial
from typing import Iterable
from typing import List
from typing import Tuple

# %% Third party imports.
import netCDF4 as nc
import pandas as pd

# %% Local application imports.
from cosmic_crunch._parallel import parallelize

# %% Dunder definitions.
__author__ = "Erick Edward Shepherd"

# %% Constant definitions.
PROCESSES     = 1
HEADER_REGEX  = re.compile(r"(?P<field>\S+)\s+=\s+(?P<value>.+)")
LOGGER_FORMAT = "%(asctime)-19s || %(levelname)-8s || %(name)s :: %(message)s"
LOG_FILENAME  = f"{os.path.basename(__file__)}.log"

# %% Logging configuration.
# - This conditional protects an overridden logging configuration.
if __name__ not in ["__main__", "__mp_main__"]:
    
    logging.basicConfig(
        level    = logging.INFO,
        format   = LOGGER_FORMAT,
        handlers = [logging.FileHandler(LOG_FILENAME)],
    )


# %% Function definition: read_cosmic_ascii_file
def read_cosmic_ascii_file(filename : str) -> Tuple[dict, dict, bool]:
    
    '''
    
    Given the name of or path to a COSMIC ASCII file, this function reads data
    from the file into a `dict` of header fields and a `dict` of
    `pandas.DataFrame`s and returns both `dict` objects.
    
    :param filename: The filename of or path to the data file.
    :type filename: str
    
    :return: The data file header, data, and whether the file is empty.
    :rtype: Tuple[dict, dict, bool]
    
    '''
    
    logger = logging.getLogger("read_cosmic_ascii_file")
    
    header     = {}
    body_index = None
    
    if filename.endswith(".gz"):
        
        open_file = partial(gzip.open, mode = "rt")
        
    else:
        
        open_file = partial(open, mode = "r")
    
    with open_file(filename) as file:
        
        for index, line in enumerate(file):
            
            match = HEADER_REGEX.match(line)
            
            if match:
                
                field = match["field"]
                value = match["value"]
                
                # Attempt to evaluate the "value" string. If the evaluation
                # fails, treat "value" as a string.
                try:
                
                    header[field] = eval(value)
                    
                except (NameError, SyntaxError):
                    
                    header[field] = eval(f"'{value}'")
                
                # If "value" evaluates as a set, order of the elements risks
                # being lost. To preserve element order, this modifies the
                # string so that it evaluates instead as a tuple.
                #
                # NOTE: This will not preserve the order of any nested sets
                #       caught in the evaluation, but such generality is not
                #       believed to be necessary at this time.
                if isinstance(header[field], set):
                    
                    value = f"({value.strip()[1:-1]},)"
                    
                    header[field] = eval(value)
                    
                body_index = index + 1
    
    data_types = {}
    
    for index, dtype_name in enumerate(header["DataTypeName"]):
        
        data_types[dtype_name] = {}
        
        dtype_id     = header["DataTypeID"][index]
        dtype_fields = header[f"Fields({dtype_id})"]
        
        data_types[dtype_name]["id"]     = dtype_id
        data_types[dtype_name]["fields"] = dtype_fields
        
    raw_data = pd.read_csv(
        filename,
        sep       = "\t",
        names     = ["Field", *data_types[dtype_name]["fields"]],
        na_values = -9999.0,
        skiprows  = body_index
    )
    
    file_is_empty = raw_data.empty
    
    if file_is_empty:
        
        logger.warning(f"The following file contains no data!: {filename}")
        
        data = None
    
    else:
    
        data = {}

        for name in data_types.keys():

            dtype_id     = data_types[name]["id"]
            dtype_fields = data_types[name]["fields"]

            data[name] = raw_data[raw_data["Field"] == dtype_id]
            data[name] = data[name].drop(["Field"], axis = 1)
            data[name] = data[name].reset_index(drop = True)
            data[name].columns = dtype_fields
            data[name].index.name = "Index"
    
    return header, data, file_is_empty


# %% Function definition: write_cosmic_netcdf4_file
def write_cosmic_netcdf4_file(filename : str, header : dict, data : dict):
    
    '''
    
    Given a filename, header data, and a `dict` of datasets, this function
    creates a new netCDF4 file of the data.
    
    :param filename: The filename of or path to the data file.
    :type filename: str
    
    :param header: The ASCII file header containing metadata about the dataset.
    :type header: dict
    
    :param data: A `dict` of `pandas.DataFrame` objects of the file data.
    :type data: dict
    
    '''
    
    base_filename = os.path.splitext(filename)[0]
    
    # Split the extension a second time if the file was compressed.
    if filename.endswith(".gz"):
        
        base_filename = os.path.splitext(base_filename)[0]
    
    save_filename = base_filename + ".nc"
    save_filename = re.sub(r"(?:\\|/)txt(?:\\|/)?", "/nc/", save_filename)
    
    with nc.Dataset(save_filename, "w") as dataset:
        
        for key, value in header.items():
        
            dataset.setncattr(key, value)
        
        if data is not None:
        
            for group_name, df in data.items():

                group = dataset.createGroup(group_name)
                group.createDimension(df.index.name, df.index.size)

                for column in df.columns:

                    variable = group.createVariable(
                        column,
                        df[column].dtype.str,
                        (df.index.name,)
                    )

                    variable[:] = df[column].values
    

# %% Function definition: convert_cosmic_file
def convert_cosmic_file(filename : str, skip_empty : bool = False) -> int:
    
    '''
    
    Given the filename of or path to a COSMIC ASCII data file, this function
    reads the file data and header and writes it to a new netCDF4 file.
    
    :param filename: The filename of or path to a COSMIC ASCII data file.
    :type filename: str
    
    :param skip_empty: Whether skip conversion of files whose arrays are empty.
    :type skip_empty: bool
    
    :return: An integer completion code. 0: converted, 1: skipped, 2: error.
    :rtype: int
    
    '''
    
    logger = logging.getLogger("convert_cosmic_file")
    
    completion_codes = {
        "converted" : 0,
        "skipped"   : 1,
        "error"     : 2,
    }
    
    try:

        header, data, file_is_empty = read_cosmic_ascii_file(filename)
        
        if file_is_empty:
            
            if skip_empty:
        
                logger.warning(
                    "The empty following empty file was skipped during "
                    f"the conversion: {filename}"
                )
            
                return completion_codes["skipped"]
            
            else:
                
                write_cosmic_netcdf4_file(filename, header, data)
                
                return completion_codes["converted"]
                
        else:
            
            write_cosmic_netcdf4_file(filename, header, data)
            
            return completion_codes["converted"]
        
    except Exception as error:
        
        logger.error(
            "An error occurred while attempting to convert the file "
            f"{filename}"
        )
        
        logger.exception(error)
        
        return completion_codes["error"]


# %% Function definition: crawl_convert
def crawl_convert(paths      : Iterable,
                  processes  : int = PROCESSES,
                  skip_empty : bool = False) -> List[int]:
    
    '''
    
    Given the path to some COSMIC ASCII data file, this function creates a
    netCDF4 formatted copy inplace. Given the path to a root directory
    containing multiple COSMIC ASCII data files, this function crawls the
    directory, identifies each .txt.gz file, and creates a netCDF4 formatted
    copy inplace.
    
    :param path: The paths to COSMIC ASCII files or directories of them.
    :type path: list
    
    :param processes: The number of multiprocessing workers to use.
    :type processes: int
    
    :param skip_empty: Whether skip conversion of files whose arrays are empty.
    :type skip_empty: bool
    
    :return: A list of integer completion codes.
    :rtype: List[int]
    
    '''
    
    path = list(paths)
    
    for path in paths:
    
        path = os.path.abspath(path)

        data_paths = []

        if not os.path.isfile(path):

            for root, directories, files in os.walk(path):
                
                for directory in directories:
                    
                    dir_path = os.path.join(root, directory)
                    
                    if re.search(r"(?:\\|/)txt(?:\\|/)?", dir_path):
                        
                        nc_dir_path = re.sub(
                            r"(?:\\|/)txt(?:\\|/)?",
                            "/nc",
                            dir_path
                        )
                    
                        if not os.path.exists(nc_dir_path):
                        
                            os.mkdir(nc_dir_path)

                for file in files:

                    if file.endswith(".txt") or file.endswith(".txt.gz"):

                        data_paths.append(os.path.join(root, file))

        else:

            data_paths.append(path)
                
        completion_codes = parallelize(
            partial(convert_cosmic_file, skip_empty = skip_empty),
            data_paths,
            "Converting ASCII to netCDF4",
            processes,
        )
        
        return completion_codes
    

# %% Main-multiprocessing hybrid entry point.
# - Allows CLI arguments to be shared between child processes.
if __name__ in ["__main__", "__mp_main__"]:
        
    parser = argparse.ArgumentParser(
        description = (
            "A script to create inplace copies of COSMIC ASCII "
            "gzip-compressed data files in netCDF4 format."
        )
    )
    
    parser.add_argument(
        "path",
        type    = str,
        nargs   = "+",
        help    = (
            "The path to one or more COSMIC ASCII gzip-compressed data files "
            "or directories containing them. If one or more directories are "
            "given, they will be crawled recursively."
        )
    )
    
    parser.add_argument(
        "--logfile",
        type    = str,
        default = None,
        help    = (
            "A custom name to use for the log file. Overrides the default "
            f"\"{LOG_FILENAME}\"."
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
        "--skip_empty",
        dest   = "skip_empty",
        action = "store_true",
        help   = "Skips converting files whose arrays are all empty."
    )
    
    parser.set_defaults(skip_empty = False)
    
    try:
    
        argv   = parser.parse_args()
        kwargv = vars(argv)
        
    except SystemExit:
        
        sys.exit()
    
    if kwargv["logfile"] is not None:
                    
        handlers = [logging.FileHandler(kwargv["logfile"])]
        
    else:
        
        handlers = [logging.FileHandler(LOG_FILENAME)]
        
    logging.basicConfig(
        level    = logging.INFO,
        format   = LOGGER_FORMAT,
        handlers = handlers,
    )
    
    logger = logging.getLogger("__main__")
    
    path       = kwargv["path"]
    processes  = kwargv["processes"]
    skip_empty = kwargv["skip_empty"]
    
# %% Main entry point.
# - Allows forking to start child processes.
if __name__ == "__main__":
    
    completion_codes = crawl_convert(path, processes, skip_empty)
    
    total_conversions      = len(completion_codes)
    conversions_successful = completion_codes.count(0)
    conversions_skipped    = completion_codes.count(1)
    conversion_errors      = completion_codes.count(2)
    
    print(f"\nASCII to netCDF4 conversion summary:")
    print(f" - Successful conversions: {conversions_successful}")
    print(f" - Skipped conversions:    {conversions_skipped}")
    print(f" - Conversion errors:      {conversion_errors}")
    print(f" - Total number of files:  {total_conversions}")
