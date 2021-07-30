# COSMIC Crunch

A series of scripts for use with JPL COSMIC data files.

* `get_files.py` is a module to download JPL COSMIC ASCII data files
* `convert_files.py` is a module to convert COSMIC ASCII data files to netCDF4 format


## get_files.py

`get_files.py` is a module to crawl the JPL COSMIC website and download data files.

To use this module, run it directly with

```
python get_files.py
```

This module also supports an optional `-h` or `--help` flag which explains its use.

```
python get_files.py --help
usage: get_files.py [-h] [--processes PROCESSES] [--test]

A script to download COSMIC ASCII data files.

optional arguments:
  -h, --help            show this help message and exit
  --processes PROCESSES
                        The number of processes to use in the multiprocessing
                        pool. Defaults to 1.
  --test                Whether to download a small subset of the data as a
                        test.
```

As explained in the `--help` message, there are also a few other optional flags.

* `--test` downloads a small subset of the available data to test that the script is working. 
* `--processes` overrides the default number of processes used in the `multiprocessing.Pool`.

As an example, a successful test run resembles the following:

```
python get_files.py --test
Crawling all ./cosmic<#>/postproc: 100%|████████████████████████████████| 1/1 [00:00<00:00,  2.06it/s]
Crawling all ./cosmic<#>/.../<year>: 100%|██████████████████████████████| 1/1 [00:00<00:00,  1.94it/s]
Crawling all ./cosmic<#>/.../<date>: 100%|██████████████████████████████| 1/1 [00:01<00:00,  1.05s/it]
Crawling all ./cosmic<#>/.../L2/<format>: 100%|█████████████████████████| 1/1 [00:00<00:00,  2.02it/s]
Downloading data files:   9%|████████                                   | 13/151 [00:06<01:05,  2.09it/s]
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
usage: convert_files.py [-h] [--logfile LOGFILE] [--processes PROCESSES]
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
```

As explained in the `--help` message, there are also a few other optional flags.

* `--logfile` overrides the name of the logfile. 
* `--processes` overrides the default number of processes used in the `multiprocessing.Pool`.

As an example, a successful run resembles the following:

```
python convert_files.py ./jpl_cosmic/2019/ --logfile=2019.log --processes=4
Converting ASCII to netCDF4: 100%|██████████████████████████████████| 151/151 [00:04<00:00, 36.79it/s]
```
