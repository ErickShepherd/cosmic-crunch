#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''

Shared parallelism helpers for the cosmic_crunch package.

De-duplicates the ``parallelize`` implementation that was copy-pasted between
``get_files.py`` and ``convert_files.py`` in v1, and gathers the ``flatten`` and
``retry_decorator`` helpers alongside it.

NOTE (v2 port): the helpers are moved verbatim from v1 -- behavior is unchanged
in this packaging step. In particular ``retry_decorator`` still retries forever
and swallows every exception; the bounded-retry fix is Phase 3 (plan item 8).

'''

# %% Standard library imports.
import multiprocessing
from typing import Callable
from typing import Iterable
from typing import List

# %% Third party imports.
from tqdm import tqdm

# %% Constant definitions.
PROCESSES = 1


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
                    desc  = desc
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
