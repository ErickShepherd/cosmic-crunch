#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''

A module to convert JPL COSMIC data files from ASCII to netCDF4.

File:           convert_files.py
File version:   1.1.2
Python version: 3.7.3
Date created:   2021-01-28
Last updated:   2021-01-31

Author:  Erick Edward Shepherd
E-mail:  dev@erickshepherd.com
GitHub:  https://www.github.com/ErickShepherd
Website: https://www.ErickShepherd.com


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

    # TODO: Switch from using `.endswith(".txt.gz")` to the use of a regular
            expression to better discriminate between data files during
            recursive file crawling.

'''

# %% Standard library imports.
import argparse
import gzip
import logging
import multiprocessing
import os
import re
from functools import partial
from typing import Callable
from typing import Iterable

# %% Third party imports.
import netCDF4 as nc
import pandas as pd
from tqdm import tqdm

# %% Dunder definitions.
__author__  = "Erick Edward Shepherd"
__version__ = "1.1.2"

# %% Constant definitions.
PROCESSES      = 16
HEADER_REGEX   = re.compile(r"(?P<field>\S+)\s+=\s+(?P<value>.+)")

logging.basicConfig(
    filename = f"{os.path.basename(__file__)}.log",
    level    = logging.INFO,
    format   = "%(asctime)-19s || %(levelname)-8s || %(name)s :: %(message)s"
)


# %% Function definition: read_cosmic_ascii_file
def read_cosmic_ascii_file(filename : str) -> (dict, dict):
    
    '''
    
    Given the name of or path to a COSMIC ASCII file, this function reads data
    from the file into a `dict` of header fields and a `dict` of
    `pandas.DataFrame`s and returns both `dict` objects.
    
    :param filename: The filename of or path to the data file.
    :type filename: str
    
    :return: The data file header and data.
    :rtype: (dict, dict)
    
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
                
                try:
                
                    header[field] = eval(value)
                    
                except (NameError, SyntaxError):
                    
                    header[field] = eval(f"'{value}'")
                    
                if isinstance(header[field], set):
                        
                    header[field] = tuple(header[field])
                    
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
    
    if raw_data.empty:
        
        logger.warning(f"{filename} contains no data!")
        
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
    
    return header, data


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
def convert_cosmic_file(filename : str):
    
    '''
    
    Given the filename of or path to a COSMIC ASCII data file, this function
    reads the file data and header and writes it to a new netCDF4 file.
    
    :param filename: The filename of or path to a COSMIC ASCII data file.
    :type filename: str
    
    '''
    
    logger = logging.getLogger("convert_cosmic_file")
    
    try:

        header, data = read_cosmic_ascii_file(filename)

        write_cosmic_netcdf4_file(filename, header, data)
        
    except Exception as error:
        
        logger.error(
            f"An error occurred while attempting to convert the file "
            f"{filename}"
        )
        
        logger.exception(error)


# %% Function definition: parallelize
def parallelize(
        function  : Callable,
        domain    : Iterable,
        desc      : str = None,
        processes : int = PROCESSES) -> list:
    
    '''
    
    Parallelizes some task over a domain of arguments using a
    `multiprocessing.Pool`.
    
    :param function: The function to parallelize.
    :type function: Callable
    
    :param domain: The domain to use as function arguments.
    :type domain: Iterable
    
    :param processes: The number of pool processes to use for worker creation.
    :type processes: int
    
    :param desc: The description of the task being parallelized.
    :type desc: str
    
    :return: A list of collected return values from the paralleized function.
    :rtype: list
    
    '''
    
    with multiprocessing.Pool(processes) as pool:
        
        # Variable aliasing for brevity.
        f = function
        D = domain
        d = desc
        p = pool
    
        return list(tqdm(p.imap(f, D), total = len(D), desc = d))
    

# %% Function definition: crawl_convert
def crawl_convert(paths : Iterable):
    
    '''
    
    Given the path to some COSMIC ASCII data file, this function creates a
    netCDF4 formatted copy inplace. Given the path to a root directory
    containing multiple COSMIC ASCII data files, this function crawls the
    directory, identifies each .txt.gz file, and creates a netCDF4 formatted
    copy inplace.
    
    :param path: The paths to COSMIC ASCII files or directories of them.
    :type path: list
    
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

        parallelize(
            convert_cosmic_file,
            data_paths,
            "Converting ASCII to netCDF4"
        )
    

# %% Main entry point.
if __name__ == "__main__":
    
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
    
    argv   = parser.parse_args()
    kwargv = vars(argv)
    
    crawl_convert(kwargv["path"])
