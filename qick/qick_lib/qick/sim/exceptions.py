"""Exceptions used by the hardware-free QICK simulator."""
# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

try:
    from qick.awg_tuning import (
        UnsupportedIPError,
        UnsupportedInstructionError,
        UnsupportedModeError,
    )
except Exception:  # pragma: no cover - import fallback for unusual packaging.
    class UnsupportedIPError(RuntimeError):
        """Raised when a project IP is not modeled in strict simulation mode."""

    class UnsupportedInstructionError(NotImplementedError):
        """Raised when a tProcessor instruction has no simulator handler."""

    class UnsupportedModeError(RuntimeError):
        """Raised when a modeled IP receives an unsupported command mode."""


class QickSimError(RuntimeError):
    """Base class for qick.sim errors."""


class TopologyError(QickSimError):
    """Raised when HWH topology discovery cannot be completed."""


class TimingConflictError(QickSimError):
    """Raised when strict simulation detects an illegal timing conflict."""


__all__ = [
    "QickSimError",
    "UnsupportedIPError",
    "UnsupportedInstructionError",
    "UnsupportedModeError",
    "TopologyError",
    "TimingConflictError",
]
