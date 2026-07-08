'''Shared pytest fixtures for the cosmic_crunch offline test suite.

Every test in this suite runs OFFLINE -- the network is never touched. Real data
is provided by the committed, trimmed fixtures under ``tests/fixtures/`` and the
saved Apache directory listings under ``tests/fixtures/listings/``.
'''

import pathlib

import pytest

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
LISTINGS = FIXTURES / "listings"


@pytest.fixture
def fixtures_dir() -> pathlib.Path:
    return FIXTURES


@pytest.fixture
def listings_dir() -> pathlib.Path:
    return LISTINGS


@pytest.fixture
def real_2006() -> pathlib.Path:
    '''A real, trimmed cosmic1 2006 L2 file (multi-DataType 68 + 82).'''
    return FIXTURES / "20060501_0632co1_g35_2p6.L2.txt.gz"


@pytest.fixture
def real_2019() -> pathlib.Path:
    '''A real, trimmed cosmic1 2019 L2 file (multi-DataType 68 + 83).'''
    return FIXTURES / "20190103_0000co1_g72_2p6.L2.txt.gz"


@pytest.fixture
def synthetic_empty() -> pathlib.Path:
    '''Synthetic file with a real header and zero data rows.'''
    return FIXTURES / "cosmic1_SYNTHETIC_empty-data.L2.txt.gz"


@pytest.fixture
def synthetic_differing_width() -> pathlib.Path:
    '''Synthetic file whose two DataTypes have differing field counts (6 vs 3).'''
    return FIXTURES / "cosmic1_SYNTHETIC_multitype-differing-width.L2.txt.gz"


@pytest.fixture
def synthetic_malicious() -> pathlib.Path:
    '''Synthetic file whose header value is a code-execution expression.'''
    return FIXTURES / "cosmic1_SYNTHETIC_malicious-header.L2.txt.gz"
