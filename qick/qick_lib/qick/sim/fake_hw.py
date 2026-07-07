"""Backward-compatible alias for the simulator virtual hardware stubs.

``virtual_hw`` is the primary module name used by the simulator. This module
exists so older examples that referenced ``qick.sim.fake_hw`` keep working.
"""
# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

from .virtual_hw import *  # noqa: F401,F403
