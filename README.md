# COSMIC Crunch

A series of scripts for use with JPL COSMIC data files.

* [`get_files.py`](#get_files.py) is a module to download JPL COSMIC ASCII data files
* [`convert_files.py`](#convert_files.py) is a module to convert COSMIC ASCII data files to netCDF4 format


## <a name="get_files.py"></a>get_files.py

`get_files.py` is a module to crawl the JPL COSMIC website and download data files.

To use this module, run it directly with

```
python get_files.py
```

This module also supports an optional `-h` or `--help` flag which explains its use.

```
python get_files.py --help
usage: get_files.py [-h] [--year_regex YEAR_REGEX] [--date_regex DATE_REGEX]
                    [--processes PROCESSES] [--test] [--netcdf4]
                    [--skip_empty]

A script to download COSMIC ASCII data files.

optional arguments:
  -h, --help            show this help message and exit
  --year_regex YEAR_REGEX
                        An optional year regular expression to download. If
                        given, all matching data files will be downloaded.
                        Otherwise, every data file for every year will be
                        downloaded.
  --date_regex DATE_REGEX
                        An optional date regular expression to download. If
                        given, all matching data files will be downloaded.
                        Otherwise, every data file for every date will be
                        downloaded.
  --processes PROCESSES
                        The number of processes to use in the multiprocessing
                        pool. Defaults to 1.
  --test                Downloads a small subset of the data as a test.
  --netcdf4             Converts the ASCII data files to netCDF4.
  --skip_empty          Skips converting files whose arrays are all empty.
```

As explained in the `--help` message, there are also a few other optional flags.

* `--year_regex` selects a subset of years matching the given regular expression.
* `--date_regex` selects a subset of dates matching the given regular expression.
* `--processes` overrides the default number of processes used in the `multiprocessing.Pool`.
* `--test` downloads a small subset of the available data to test that the script is working. 
* `--netcdf4` converts the ASCII data files to netCDF4.
* `--skip_empty` skips converting files whose arrays are all empty.

As an example, a successful run resembles the following:

```
python get_files.py --year_regex=2006 --date_regex=2006-05-02 --netcdf4 --skip_empty --processes=4
Crawling all ./cosmic<#>/postproc: 100%|████████████████████████████████| 6/6 [00:03<00:00,  1.61it/s]
Crawling all ./cosmic<#>/.../<year>: 100%|██████████████████████████████| 6/6 [00:03<00:00,  1.59it/s]
Crawling all ./cosmic<#>/.../<date>: 100%|██████████████████████████████| 3/3 [00:03<00:00,  1.17s/it]
Crawling all ./cosmic<#>/.../L2/<format>: 100%|█████████████████████████| 4/4 [00:04<00:00,  1.09s/it]
Downloading data files: 100%|███████████████████████████████████████████| 20/20 [00:26<00:00,  1.33s/it]
Converting ASCII to netCDF4: 100%|██████████████████████████████████████| 20/20 [00:03<00:00,  6.32it/s]

ASCII to netCDF4 conversion summary:
 - Successful conversions: 17
 - Skipped conversions:    3
 - Conversion errors:      0
 - Total number of files:  20
```


## <a name="convert_files.py"></a>convert_files.py

A module to convert JPL COSMIC data files from a gzip-compressed ASCII storage format to the netCDF4 standard.

This module is used automatically by `get_files.py` when it is run with the `--netcdf4` flag.

This module can be run directly with the Python interpreter. The module requires a positional `path` argument for the path or paths of the COSMIC ASCII gzip-compressed data files. This argument can consist of either one or more paths to the individual file(s) or to directories containing them. If a given path is a directory, any nested directories will be searched recursively for COSMIC ASCII files. Converted files are stored beside their original ASCII file. To use,

```
python convert_files.py <path1> <path2> <path3> <...>
```

This module also supports an optional `-h` or `--help` flag which explains its use.

```
python convert_files.py --help
usage: convert_files.py [-h] [--logfile LOGFILE] [--processes PROCESSES]
                        [--skip_empty]
                        path [path ...]

A script to create inplace copies of COSMIC ASCII gzip-compressed data files
in netCDF4 format.

positional arguments:
  path                  The path to one or more COSMIC ASCII gzip-compressed
                        data files or directories containing them. If one or
                        more directories are given, they will be crawled
                        recursively.

optional arguments:
  -h, --help            show this help message and exit
  --logfile LOGFILE     A custom name to use for the log file. Overrides the
                        default "convert_files.py.log".
  --processes PROCESSES
                        The number of processes to use in the multiprocessing
                        pool. Defaults to 1.
  --skip_empty          Skips converting files whose arrays are all empty.
```

As explained in the `--help` message, there are also a few other optional flags.

* `--logfile` overrides the name of the logfile. 
* `--processes` overrides the default number of processes used in the `multiprocessing.Pool`.
* `--skip_empty` skips converting files whose arrays are all empty.

As an example, a successful run resembles the following:

```
python convert_files.py ./jpl_cosmic/2006/ --logfile=2006.log --skip_empty --processes=4
Converting ASCII to netCDF4: 100%|██████████████████████████████████| 20/20 [00:02<00:00,  8.52it/s]

ASCII to netCDF4 conversion summary:
 - Successful conversions: 17
 - Skipped conversions:    3
 - Conversion errors:      0
 - Total number of files:  20
```
