"""Tests for AWG Experiment PL DDR memory accounting.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import pytest

from ddr_memory_usage import (
    calculate_ddr_capture_memory_usage,
    format_binary_bytes,
)


def test_ddr_usage_includes_cartesian_sweeps_repetitions_and_axi_padding():
    usage = calculate_ddr_capture_memory_usage(
        sweep_points=101 * 101 * 401,
        repetitions=3,
        samples_per_trigger=10,
        capacity_words_32b=1 << 30,
    )

    assert usage.sweep_points == 4_090_601
    assert usage.trigger_count == 12_271_803
    assert usage.physical_words_per_trigger == 16
    assert usage.valid_data_bytes == 12_271_803 * 10 * 4
    assert usage.reserved_bytes == 12_271_803 * 16 * 4
    assert usage.padding_bytes == usage.reserved_bytes - usage.valid_data_bytes
    assert usage.end_address_bytes == usage.reserved_bytes
    assert usage.capacity_bytes == 4 * (1 << 30)
    assert usage.address_usage_percent == pytest.approx(
        100.0 * usage.reserved_bytes / usage.capacity_bytes
    )
    assert not usage.exceeds_capacity


def test_ddr_usage_matches_nonzero_address_and_capacity_overflow_check():
    usage = calculate_ddr_capture_memory_usage(
        sweep_points=10,
        repetitions=2,
        samples_per_trigger=8,
        start_address_bytes=4096,
        capacity_words_32b=1100,
        force_overwrite=True,
    )

    assert usage.reserved_bytes == 20 * 8 * 4
    assert usage.end_address_bytes == 4096 + usage.reserved_bytes
    assert usage.exceeds_capacity
    assert usage.force_overwrite


def test_ddr_usage_rejects_invalid_inputs_and_formats_binary_sizes():
    with pytest.raises(ValueError, match="samples_per_trigger"):
        calculate_ddr_capture_memory_usage(
            sweep_points=1,
            repetitions=1,
            samples_per_trigger=0,
        )

    assert format_binary_bytes(0) == "0 B"
    assert format_binary_bytes(1024) == "1.000 KiB"
    assert format_binary_bytes(5 * 1024**3) == "5.000 GiB"
