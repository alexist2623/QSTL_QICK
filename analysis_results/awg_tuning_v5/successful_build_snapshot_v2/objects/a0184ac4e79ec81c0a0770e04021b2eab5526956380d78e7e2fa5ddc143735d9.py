"""PL DDR capture-memory accounting shared by the GUI and tests.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DdrCaptureMemoryUsage:
    """Exact sample-buffer allocation for one AWG sweep acquisition."""

    sweep_points: int
    repetitions: int
    trigger_count: int
    samples_per_trigger: int
    samples_per_axi_word: int
    physical_words_per_trigger: int
    valid_data_bytes: int
    padding_bytes: int
    reserved_bytes: int
    start_address_bytes: int
    end_address_bytes: int
    capacity_bytes: Optional[int]
    force_overwrite: bool

    @property
    def address_usage_fraction(self) -> Optional[float]:
        """Fraction of PL DDR below the final byte touched by the capture."""
        if self.capacity_bytes is None:
            return None
        return self.end_address_bytes / self.capacity_bytes

    @property
    def address_usage_percent(self) -> Optional[float]:
        fraction = self.address_usage_fraction
        return None if fraction is None else 100.0 * fraction

    @property
    def exceeds_capacity(self) -> bool:
        return (
            self.capacity_bytes is not None
            and self.end_address_bytes > self.capacity_bytes
        )


def calculate_ddr_capture_memory_usage(
    *,
    sweep_points: int,
    repetitions: int,
    samples_per_trigger: int,
    start_address_bytes: int = 0,
    capacity_words_32b: Optional[int] = None,
    samples_per_axi_word: int = 8,
    iq_sample_bytes: int = 4,
    force_overwrite: bool = False,
) -> DdrCaptureMemoryUsage:
    """Match ``AxisBufferDdrSampleV1.arm_samples`` allocation semantics.

    A legacy IQ sample is 4 bytes; V3 IQ64 is 16 bytes. Each trigger is padded
    to 256-bit AXI words (eight legacy samples or two IQ64 samples). Physical
    word counts and capacity are always expressed in uint32 words.
    """

    for name, value, minimum in (
        ("sweep_points", sweep_points, 1),
        ("repetitions", repetitions, 1),
        ("samples_per_trigger", samples_per_trigger, 1),
        ("start_address_bytes", start_address_bytes, 0),
        ("samples_per_axi_word", samples_per_axi_word, 1),
        ("iq_sample_bytes", iq_sample_bytes, 4),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
        if value < minimum:
            raise ValueError(f"{name} must be >= {minimum}")

    if capacity_words_32b is not None:
        if (
            isinstance(capacity_words_32b, bool)
            or not isinstance(capacity_words_32b, int)
        ):
            raise TypeError("capacity_words_32b must be an integer or None")
        if capacity_words_32b <= 0:
            raise ValueError("capacity_words_32b must be positive")

    if iq_sample_bytes not in (4, 16) or samples_per_axi_word * iq_sample_bytes != 32:
        raise ValueError("IQ format must pack exactly one 256-bit AXI word")
    trigger_count = sweep_points * repetitions
    physical_words_per_trigger = (
        (samples_per_trigger + samples_per_axi_word - 1)
        // samples_per_axi_word
        * samples_per_axi_word
        * (iq_sample_bytes // 4)
    )
    valid_data_bytes = trigger_count * samples_per_trigger * iq_sample_bytes
    reserved_bytes = trigger_count * physical_words_per_trigger * 4
    padding_bytes = reserved_bytes - valid_data_bytes
    end_address_bytes = start_address_bytes + reserved_bytes
    capacity_bytes = (
        None if capacity_words_32b is None else capacity_words_32b * 4
    )

    return DdrCaptureMemoryUsage(
        sweep_points=sweep_points,
        repetitions=repetitions,
        trigger_count=trigger_count,
        samples_per_trigger=samples_per_trigger,
        samples_per_axi_word=samples_per_axi_word,
        physical_words_per_trigger=physical_words_per_trigger,
        valid_data_bytes=valid_data_bytes,
        padding_bytes=padding_bytes,
        reserved_bytes=reserved_bytes,
        start_address_bytes=start_address_bytes,
        end_address_bytes=end_address_bytes,
        capacity_bytes=capacity_bytes,
        force_overwrite=bool(force_overwrite),
    )


def format_binary_bytes(value: int) -> str:
    """Format a non-negative byte count with IEC units."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("value must be an integer")
    if value < 0:
        raise ValueError("value must be non-negative")
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
    scaled = float(value)
    unit = units[0]
    for unit in units:
        if scaled < 1024.0 or unit == units[-1]:
            break
        scaled /= 1024.0
    if unit == "B":
        return f"{value:,} B"
    return f"{scaled:.3f} {unit}"
