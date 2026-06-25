"""Simulation result containers."""

from .virtual_hw import install_pynq_stubs

install_pynq_stubs()

from qick.awg_tuning import WaveformResult as WaveformResult  # noqa: E402


SimulationResult = WaveformResult


__all__ = ["WaveformResult", "SimulationResult"]
