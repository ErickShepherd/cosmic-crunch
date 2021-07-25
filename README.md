# Cosmic Crunch

A series of scripts for use with JPL COSMIC data files.

* `get_files.py` is a module to download JPL COSMIC ASCII data files
* `convert_files.py` is a module to convert COSMIC ASCII data files to netCDF4 format


## get_files.py

`get_files.py` is a module to crawl the JPL COSMIC website and download data files.

To use this module, run it directly with

```
python get_files.py
```


## convert_files.py

A module to convert JPL COSMIC data files from a gzip-compressed ASCII storage format to the netCDF4 standard.

This module can be run directly with the Python interpreter. The module requires a positional `path` argument for the path or paths of the COSMIC ASCII gzip-compressed data files. This argument can consist of either one or more paths to the individual file(s) or to directories containing them. If a given path is a directory, any nested directories will be searched recursively for COSMIC ASCII files. Converted files are stored beside their original ASCII file. To use,

```
python convert_files.py <path1> <path2> <path3> <...>
```

This module also supports an optional `-h` or `--help` flag which explains its use.

```
python convert_files.py --help
usage: convert_files.py [-h] path [path ...]

A script to create inplace copies of COSMIC ASCII gzip-compressed data files
in netCDF4 format.

positional arguments:
  path        The path to one or more COSMIC ASCII gzip-compressed data files
              or directories containing them. If one or more directories are
              given, they will be crawled recursively.

optional arguments:
  -h, --help  show this help message and exit
```
