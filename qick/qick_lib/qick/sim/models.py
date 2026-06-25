"""Behavior models for QICK simulation.

The public user API is :class:`qick.sim.QickSim`. These model classes are kept
internal so tests and advanced debugging can exercise individual IP behavior.
"""

from .virtual_hw import install_pynq_stubs

install_pynq_stubs()

from qick.awg_tuning import (  # noqa: E402
    AwgTuningBehaviorModel as _AwgTuningBehaviorModel,
    AxisAvgBufferV13BehaviorModel as _AxisAvgBufferV13BehaviorModel,
    AxisBroadcasterBehaviorModel as _AxisBroadcasterBehaviorModel,
    AxisClockConverterBehaviorModel as _AxisClockConverterBehaviorModel,
    AxisDynReadoutV1BehaviorModel as _AxisDynReadoutV1BehaviorModel,
    AxisRegisterSliceBehaviorModel as _AxisRegisterSliceBehaviorModel,
    AxisSignalGenV6BehaviorModel as _AxisSignalGenV6BehaviorModel,
    AxisSwitchBehaviorModel as _AxisSwitchBehaviorModel,
    AxisTmuxV1BehaviorModel as _AxisTmuxV1BehaviorModel,
    RfdcAdcSourceModel,
    RfdcDacSinkModel,
    TimedCommandEvent,
)


class AxisAwgTuningBehaviorModel(_AwgTuningBehaviorModel):
    """qick.sim wrapper for the AWG tuning behavior model."""


class AxisTmuxV1BehaviorModel(_AxisTmuxV1BehaviorModel):
    """qick.sim wrapper for the axis_tmux_v1 behavior model."""


class AxisRegisterSliceBehaviorModel(_AxisRegisterSliceBehaviorModel):
    """qick.sim wrapper for AXIS register slices."""


class AxisRegisterSliceNbBehaviorModel(_AxisRegisterSliceBehaviorModel):
    """qick.sim wrapper for QICK non-blocking AXIS register slices."""


class AxisSwitchBehaviorModel(_AxisSwitchBehaviorModel):
    """qick.sim wrapper for AXIS switches."""


class AxisBroadcasterBehaviorModel(_AxisBroadcasterBehaviorModel):
    """qick.sim wrapper for AXIS broadcasters."""


class AxisClockConverterBehaviorModel(_AxisClockConverterBehaviorModel):
    """qick.sim wrapper for AXIS clock converters."""


class AxisSignalGenV6BehaviorModel(_AxisSignalGenV6BehaviorModel):
    """qick.sim wrapper for axis_signal_gen_v6 behavior."""


class AxisDynReadoutV1BehaviorModel(_AxisDynReadoutV1BehaviorModel):
    """qick.sim wrapper for axis_dyn_readout_v1 behavior."""


class AxisAvgBufferV13BehaviorModel(_AxisAvgBufferV13BehaviorModel):
    """qick.sim wrapper for axis_avg_buffer v1.3 behavior."""

__all__ = [
    "TimedCommandEvent",
    "AxisAwgTuningBehaviorModel",
    "AxisTmuxV1BehaviorModel",
    "AxisRegisterSliceBehaviorModel",
    "AxisRegisterSliceNbBehaviorModel",
    "AxisSwitchBehaviorModel",
    "AxisBroadcasterBehaviorModel",
    "AxisClockConverterBehaviorModel",
    "RfdcDacSinkModel",
    "RfdcAdcSourceModel",
    "AxisSignalGenV6BehaviorModel",
    "AxisDynReadoutV1BehaviorModel",
    "AxisAvgBufferV13BehaviorModel",
]
