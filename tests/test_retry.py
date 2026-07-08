'''Bounded-retry behavior tests (offline; time.sleep mocked).'''

from unittest import mock

import pytest

from cosmic_crunch import _parallel


def test_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"

    with mock.patch.object(_parallel.time, "sleep") as sleep:
        assert _parallel.retry_decorator(flaky)() == "ok"

    assert calls["n"] == 3
    assert sleep.call_count == 2                    # one sleep before each retry


def test_retry_reraises_after_max_attempts():
    calls = {"n": 0}

    def always_fail():
        calls["n"] += 1
        raise RuntimeError("permanent")

    with mock.patch.object(_parallel.time, "sleep") as sleep:
        with pytest.raises(RuntimeError, match="permanent"):
            _parallel.retry_decorator(always_fail, attempts=3)()

    assert calls["n"] == 3                          # bounded: no infinite loop
    assert sleep.call_count == 2


def test_retry_exponential_backoff_delays():
    def always_fail():
        raise RuntimeError("x")

    with mock.patch.object(_parallel.time, "sleep") as sleep:
        with pytest.raises(RuntimeError):
            _parallel.retry_decorator(always_fail, attempts=3, backoff_base=2)()

    # delay before retry n is backoff_base ** (n - 1): 2**0, 2**1
    assert [c.args[0] for c in sleep.call_args_list] == [1, 2]
