'''Full ASCII -> netCDF4 -> read-back round-trip test (offline).'''

import os
import shutil

import netCDF4 as nc
import numpy as np

from cosmic_crunch import convert


def test_ascii_to_netcdf4_roundtrip_preserves_values(tmp_path, real_2006):
    # Convert a real ASCII file and read the netCDF4 back, asserting the values
    # survive the round-trip.
    txt_dir = tmp_path / "L2" / "txt"
    txt_dir.mkdir(parents=True)
    src = txt_dir / "rt.L2.txt.gz"
    shutil.copy(str(real_2006), str(src))

    rc = convert.convert_cosmic_file(str(src))
    assert rc == 0

    ncf = tmp_path / "L2" / "nc" / "rt.L2.nc"
    assert ncf.exists()

    # expected values straight from the parser
    _, data, _ = convert.read_cosmic_ascii_file(str(src))

    with nc.Dataset(str(ncf)) as ds:
        for group_name, frame in data.items():
            assert group_name in ds.groups
            group = ds.groups[group_name]
            for column in frame.columns:
                assert column in group.variables
                round_tripped = np.asarray(group.variables[column][:], dtype=float)
                original = frame[column].to_numpy(dtype=float)
                # NaN-aware comparison (missing values are -9999 -> NaN)
                assert np.allclose(round_tripped, original, equal_nan=True)


def test_netcdf4_preserves_header_attributes(tmp_path, real_2006):
    txt_dir = tmp_path / "L2" / "txt"
    txt_dir.mkdir(parents=True)
    src = txt_dir / "rt.L2.txt.gz"
    shutil.copy(str(real_2006), str(src))
    convert.convert_cosmic_file(str(src))

    header, _, _ = convert.read_cosmic_ascii_file(str(src))
    ncf = tmp_path / "L2" / "nc" / "rt.L2.nc"
    with nc.Dataset(str(ncf)) as ds:
        assert ds.getncattr("Receiver") == header["Receiver"]
        assert int(ds.getncattr("ProcessingLevel")) == header["ProcessingLevel"]
