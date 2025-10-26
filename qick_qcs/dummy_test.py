import qstl
from typing import Iterable
from pprint import pprint

mapper = qstl.ChannelMapper()
awg = qstl.Channels(
    0,
    name = "awg"
)
awg_measure = qstl.Channels(
    range(3),
    name = "awg_measure"
)
digitizer = qstl.Channels(
    range(4),
    name = "digitizer"
)

amp_scalar = qstl.Scalar(
    name = "amp_scalar",
    value = 0.6,
    dtype = float,
)

mapper.add_channel_mapping(
    awg,
    0,
    qstl.InstrumentEnum.RF
)
mapper.add_channel_mapping(
    awg_measure,
    [1,2,3],
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
    amplitude = amp_scalar,
    rf_frequency = 1e9,
    instantaneous_phase = 0.0,
    name = "test_rf"
)

sweep_rfwaveform = qstl.RFWaveform(
    duration = 300e-9,
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
    qstl.Delay(200e-9),
    awg[0]
)
program.add_waveform(
    rfwaveform,
    awg[0]
)
program.add_waveform(
    sweep_rfwaveform,
    awg[0]
)

program.add_waveform(
    rfwaveform,
    awg_measure[0]
)
program.add_waveform(
    rfwaveform,
    awg_measure[1]
)
# program.add_waveform(
#     rfwaveform,
#     awg[0],
#     new_layer = True
# )

# pprint(program.operations)

program = qstl.Executor(mapper).execute(program)
pprint(program)

