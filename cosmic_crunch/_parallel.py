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
import logging
import multiprocessing
import time
from typing import Callable
from typing import Iterable
from typing import List

# %% Third party imports.
from tqdm import tqdm

# %% Constant definitions.
PROCESSES          = 1
RETRY_ATTEMPTS     = 3
RETRY_BACKOFF_BASE = 2  # seconds; delay before retry N is base ** (N - 1)


# %% Function definition: flatten
def flatten(list_of_lists : List[List]) -> List:

    '''

    Flatten one level of nesting: concatenate a list of lists into a single
    list, preserving order.

    :param list_of_lists: An iterable of lists to concatenate.
    :type list_of_lists: List[List]

    :return: The concatenated list.
    :rtype: List

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
def retry_decorator(
        func         : Callable,
        attempts     : int = RETRY_ATTEMPTS,
        backoff_base : float = RETRY_BACKOFF_BASE) -> Callable:

    '''

    Wraps ``func`` with bounded retry: up to ``attempts`` tries with exponential
    backoff (``backoff_base ** (n - 1)`` seconds before retry ``n``). Every
    failure is logged; after the final attempt the last exception is re-raised.

    This is the v2 fix for the v1 infinite-silent-retry defect (a permanent
    failure -- e.g. the 2020 site restructure -- used to hang forever).

    :param func: The callable to wrap.
    :type func: Callable

    :param attempts: The maximum number of attempts (default ``RETRY_ATTEMPTS``).
    :type attempts: int

    :param backoff_base: The exponential-backoff base in seconds.
    :type backoff_base: float

    :return: The wrapped callable.
    :rtype: Callable

    '''

    logger = logging.getLogger("cosmic_crunch.retry")

    def wrapper(*args, **kwargs):

        name          = getattr(func, "__name__", repr(func))
        last_exception = None

        for attempt in range(1, attempts + 1):

            try:

                return func(*args, **kwargs)

            except Exception as error:

                last_exception = error

                logger.warning(
                    "Attempt %d/%d of %s failed: %s",
                    attempt, attempts, name, error,
                )

                if attempt < attempts:

                    time.sleep(backoff_base ** (attempt - 1))

        logger.error(
            "All %d attempts of %s failed; re-raising the last exception.",
            attempts, name,
        )

        raise last_exception

    return wrapper
