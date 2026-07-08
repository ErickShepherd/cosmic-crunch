'''Header/body parser tests over the committed ASCII fixtures (offline).'''

import os

import pytest

from cosmic_crunch import convert


# --- _parse_header_value units ------------------------------------------- #

@pytest.mark.parametrize("text, expected", [
    ("286.764427", 286.764427),
    ("2", 2),
    ('"a string"', "a string"),
    ("ON", "ON"),                       # bare token -> raw string fallback
    ("cosmic1", "cosmic1"),
    ("2013-04-11T16:16:30", "2013-04-11T16:16:30"),
    ("06:32:29.504", "06:32:29.504"),
])
def test_parse_header_value_scalars(text, expected):
    assert convert._parse_header_value(text) == expected


def test_parse_header_value_brace_set_preserves_order():
    # A brace-set must become an ORDERED tuple (not an unordered set).
    result = convert._parse_header_value('{ "COSMIC1-Profile", "ECMWF-Profile" }')
    assert result == ("COSMIC1-Profile", "ECMWF-Profile")
    assert isinstance(result, tuple)


def test_parse_header_value_brace_set_of_ints_order():
    assert convert._parse_header_value("{ 68, 82 }") == (68, 82)


# --- read_cosmic_ascii_file over real fixtures --------------------------- #

def test_real_2006_multitype_order(real_2006):
    header, data, empty = convert.read_cosmic_ascii_file(str(real_2006))
    assert not empty and data is not None
    assert header["DataTypeName"] == ("COSMIC1-Profile", "ECMWF-Profile")
    assert header["DataTypeID"] == (68, 82)
    # DataTypeName[i] corresponds to DataTypeID[i]
    assert list(data["COSMIC1-Profile"].columns)[0] == "Height"
    assert header["Receiver"] == "cosmic1"     # raw-string fallback


def test_real_2019_multitype(real_2019):
    header, data, empty = convert.read_cosmic_ascii_file(str(real_2019))
    assert not empty
    assert header["DataTypeID"] == (68, 83)
    assert set(data.keys()) == {"COSMIC1-Profile", "NCEP_FNL-Profile"}


def test_empty_data_file_flagged(synthetic_empty):
    header, data, empty = convert.read_cosmic_ascii_file(str(synthetic_empty))
    assert empty is True
    assert data is None


def test_differing_width_columns_not_leaked(synthetic_differing_width):
    # The v1 loop-leak assigned the LAST type's fields to every row. With the
    # fix, each type keeps its own (differing) width and names.
    header, data, empty = convert.read_cosmic_ascii_file(str(synthetic_differing_width))
    assert not empty
    assert list(data["TypeWide"].columns) == ["a", "b", "c", "d", "e", "f"]
    assert list(data["TypeNarrow"].columns) == ["x", "y", "z"]
    assert data["TypeWide"].shape == (2, 6)
    assert data["TypeNarrow"].shape == (2, 3)
    assert data["TypeWide"].iloc[0].tolist() == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    assert data["TypeNarrow"].iloc[1].tolist() == [16.0, 17.0, 18.0]


def test_malicious_header_is_not_executed(synthetic_malicious, tmp_path):
    # Proof the eval() -> ast.literal_eval fix closed the ACE hole: the header
    # value is an __import__(...).system(...) expression; parsing must return it
    # as an inert string and execute nothing.
    sentinel = "/tmp/COSMIC_PWNED"
    if os.path.exists(sentinel):
        os.remove(sentinel)
    header, data, empty = convert.read_cosmic_ascii_file(str(synthetic_malicious))
    assert isinstance(header["EvilValue"], str)
    assert "__import__" in header["EvilValue"]
    assert not os.path.exists(sentinel), "malicious header executed!"
    assert not empty
