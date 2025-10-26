"""Qick Pyro connection test"""
import numpy as np
import matplotlib.pyplot as plt

from qick import *
from qick.averager_program import QickSweep
from qick.pyro import make_proxy

import qstl
from typing import Iterable
from pprint import pprint

def test_qstl(soccfg: QickConfig):
    mapper = qstl.ChannelMapper()
    awg = qstl.Channels(
        0,
        name = "awg"
    )
    digitizer = qstl.Channels(
        range(4),
        name = "digitizer"
    )

    awg_meas = qstl.Channels(
        0,
        name = "awg_meas"
    )

    mapper.add_channel_mapping(
        awg,
        0,
        qstl.InstrumentEnum.RF
    )
    mapper.add_channel_mapping(
        awg_meas,
        1,
        qstl.InstrumentEnum.RF
    )
    mapper.add_channel_mapping(
        digitizer,
        [0,1,2,3],
        qstl.InstrumentEnum.Digitizer
    )

    # pprint(mapper.in_channel_map)

    rfwaveform = qstl.RFWaveform(
        duration = 100e-9,
        envelope = qstl.ConstantEnvelope(),
        amplitude = 0.5,
        rf_frequency = 1e9,
        instantaneous_phase = 0.0,
        name = "test_rf"
    )
    program = qstl.Program()
    program.add_waveform(
        rfwaveform,
        awg[0]
    )
    program.add_waveform(
        rfwaveform,
        awg_meas[0]
    )
    program.add_waveform(
        qstl.Delay(200e-9),
        awg[0]
    )
    program.add_waveform(
        rfwaveform,
        awg[0],
        new_layer = True
    )

    # pprint(program.operations)

    executor = qstl.Executor(soccfg, mapper)
    executor.execute(program)
    print(executor._qick_program)

if __name__ == "__main__":
    # Qick version : 0.2.357
    (soc, soccfg) = make_proxy("192.168.2.99")
    test_qstl(soccfg)
