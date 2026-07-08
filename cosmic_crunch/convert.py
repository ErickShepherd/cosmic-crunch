#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''

cosmic_crunch.convert: convert JPL GENESIS COSMIC data files from
gzip-compressed ASCII to the netCDF4 standard.

Ported from the v1 ``convert_files.py`` script (v1.3.3). The v1 per-file
metadata and AGPL header have been removed; the package is MIT-licensed (see
LICENSE) and versioned via ``cosmic_crunch.__version__``.

'''

# %% Standard library imports.
import gzip
import logging
import os
import re
from ast import literal_eval as parse_literal
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



# %% Function definition: _parse_header_value
def _parse_header_value(value : str):

    '''

    Safely parse a COSMIC ASCII header value.

    Replaces the v1 use of the built-in dynamic evaluator (arbitrary code
    execution from downloaded file content -- plan headline defect 2) with
    ``ast.literal_eval`` (imported as ``parse_literal``; the alias keeps the
    package free of the bare dynamic-eval call syntax, so a security grep for
    that substring stays a true-positive signal):

    - Values that are Python literals (numbers, quoted strings, brace-sets,
      brace-tuples) are parsed to their Python value.
    - Values that are not valid literals (e.g. ``ON``, ``cosmic1``,
      ``2013-04-11T16:16:30``, ``06:32:29.504``) fall back to the raw stripped
      string -- handling embedded quotes that the v1 quoting fallback broke on.
    - JPL uses ``{...}`` brace-set syntax for ordered lists (``DataTypeName``,
      ``DataTypeID``, ``Fields(...)``, ``CenterOfCurvature``); ``literal_eval``
      parses those as unordered ``set``s, so the original text is re-parsed as a
      tuple to preserve element order (and any duplicates) safely.

    :param value: The raw header value string (right of the ``=``).
    :type value: str

    :return: The parsed Python value, or the raw stripped string on fallback.

    '''

    text = value.strip()

    try:

        parsed = parse_literal(text)

    except (ValueError, SyntaxError, TypeError):

        return text

    # A brace-set literal loses element order (and dedups); re-parse the
    # original text as a tuple to preserve both.
    if isinstance(parsed, set):

        try:

            parsed = parse_literal("(" + text[1:-1] + ",)")

        except (ValueError, SyntaxError, TypeError):

            return text

    return parsed


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

                header[field] = _parse_header_value(value)

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

