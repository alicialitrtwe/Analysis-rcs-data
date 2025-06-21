import os
import json
import numpy as np
import pytest
from oct2py import Oct2Py, Oct2PyError

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from python import pyrcs  # noqa: E402

DATA_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "testDataSets",
    "Benchtop",
    "Simultaneous_RCS_and_DAQ",
    "1000Hz",
    "DeviceNPC700378H",
)
TD_FILE = os.path.join(DATA_DIR, "RawDataTD.json")
ACCEL_FILE = os.path.join(DATA_DIR, "RawDataAccel.json")


def load_json(path):
    with open(path, "r") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return data[0]
    return data


def make_faulty_struct():
    packets = []
    specs = [
        (1000, 1, 1000, 1),
        (1080, 1, -100, 2),
        (1160, 1, 1016, 3),
        (2000, 5, 1030, 4),
        (2000, 5, 1030, 4),
    ]
    for i, (sys_tick, ts, pg, dts) in enumerate(specs):
        packets.append(
            {
                "Header": {
                    "dataSize": 4,
                    "systemTick": sys_tick,
                    "timestamp": {"seconds": ts},
                    "dataTypeSequence": dts,
                },
                "PacketGenTime": pg,
                "PacketRxUnixTime": pg + 50,
                "SampleRate": 0,
                "ChannelSamples": [
                    {"Key": 0, "Value": [i * 2 + 1, i * 2 + 2]}
                ],
            }
        )
    return {"TimeDomainData": packets}


def test_python_processing_runs():
    td_struct = load_json(TD_FILE)
    df_td, _ = pyrcs.create_time_domain_table(td_struct)
    out_td = pyrcs.assign_time(df_td)
    assert not out_td.empty

    accel_struct = load_json(ACCEL_FILE)
    df_accel, _ = pyrcs.create_accel_table(accel_struct)
    out_accel = pyrcs.assign_time(df_accel)
    assert not out_accel.empty


def test_compare_with_octave_helpers():
    """Compare python output with simplified Octave implementation."""
    try:
        oc = Oct2Py()
        oc.addpath(os.path.join(os.path.dirname(__file__), "..", "code"))
        oc.addpath(os.path.join(os.path.dirname(__file__), "octave_helpers"))
        td_struct = oc.deserializeJSON(TD_FILE)
        table, _ = oc.createTimeDomainTable_simple(td_struct, nout=2)
        matlab_out = oc.assignTime_octave(table)
    except Oct2PyError:
        pytest.skip("Octave environment lacks required MATLAB features")

    py_struct = load_json(TD_FILE)
    py_table, _ = pyrcs.create_time_domain_table(py_struct)
    py_out = pyrcs.assign_time(py_table)

    assert len(matlab_out) == len(py_out)
    assert np.allclose(
        py_out["DerivedTime"].values,
        matlab_out[:, 0],
        rtol=1e-6,
    )


def test_sample_points_consistency():
    """Verify a few DerivedTime samples at important indices."""
    td_struct = load_json(TD_FILE)
    py_table, _ = pyrcs.create_time_domain_table(td_struct)
    py_out = pyrcs.assign_time(py_table)

    try:
        oc = Oct2Py()
        oc.addpath(os.path.join(os.path.dirname(__file__), "..", "code"))
        oc.addpath(os.path.join(os.path.dirname(__file__), "octave_helpers"))
        td_struct_o = oc.deserializeJSON(TD_FILE)
        table, _ = oc.createTimeDomainTable_simple(td_struct_o, nout=2)
        matlab_out = oc.assignTime_octave(table)
    except Oct2PyError:
        pytest.skip("Octave environment lacks required MATLAB features")

    check_indices = [0, 160, 161, 200, len(py_out) - 1]
    for idx in check_indices:
        assert np.isclose(
            py_out["DerivedTime"].iloc[idx], matlab_out[idx, 0], rtol=1e-6
        )


def test_faulty_packet_handling():
    struct = make_faulty_struct()
    df, _ = pyrcs.create_time_domain_table(struct)
    py_out = pyrcs.assign_time(df, short_gaps_system_tick=1)

    try:
        oc = Oct2Py()
        oc.addpath(os.path.join(os.path.dirname(__file__), "octave_helpers"))
        table, _ = oc.createTimeDomainTable_simple(struct, nout=2)
        matlab_out = oc.assignTime_octave(table, 1)
    except Oct2PyError:
        pytest.skip("Octave environment lacks required MATLAB features")

    assert np.allclose(
        py_out["DerivedTime"].values,
        matlab_out[:, 0],
        rtol=1e-6,
    )
