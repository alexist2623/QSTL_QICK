"""Tests for HWH-derived FIR DDR capture profiles.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import pytest

from fir_ddr_profile import resolve_fir_ddr_profile


def _soccfg(
    rate_profile: str,
    *,
    trigger_delay_units: str = "valid_input_samples",
):
    if rate_profile == "1_msps":
        ddr = {
            "sample_capture": True,
            "fir_enabled": True,
            "fir_rate_profile": "1_msps",
            "stored_sample_rate_hz": 1_000_000.0,
            "fir_decimation": 300,
            "fir_input_fs_mhz": 300.0,
            "fir_group_delay_input_samples": 8677.0,
        }
    else:
        ddr = {
            "sample_capture": True,
            "fir_enabled": True,
            "fir_rate_profile": "50_ksps",
            "stored_sample_rate_hz": 50_000.0,
            "fir_decimation": 6000,
            "fir_input_fs_mhz": 300.0,
            "fir_group_delay_input_samples": 296_677.0,
            "supports_trigger_delay": True,
            "trigger_delay_units": trigger_delay_units,
            "filter_state_continuous": True,
            "decimation_phase_continuous": True,
        }
        if trigger_delay_units == "s_axis_aclk_cycles":
            ddr["trigger_delay_default_cycles"] = 50
        else:
            ddr["trigger_delay_default_samples"] = 50
    return {"ddr4_buf": ddr}


def test_1_msps_profile_keeps_legacy_software_warmup_compensation():
    profile = resolve_fir_ddr_profile(_soccfg("1_msps"))

    assert profile.name == "1_msps"
    assert profile.sample_rate_hz == 1_000_000.0
    assert profile.sample_period_us == 1.0
    assert profile.decimation == 300
    assert profile.software_warmup_compensation is True
    assert profile.uses_fpga_trigger_delay is False
    assert profile.trigger_delay_samples == 0
    assert profile.software_trigger_delay_output_samples == 28
    assert profile.software_aligned_trigger_input_samples == 8400
    assert profile.software_trigger_delay_input_samples == 8397
    assert profile.software_trigger_delay_us == pytest.approx(27.99)
    assert profile.software_aligned_trigger_delay_us == pytest.approx(28.0)
    assert profile.software_trigger_delay_tproc_cycles(300.0) == 8397
    assert "shared FIR/DDR trigger 28 us" in profile.timing_label


def test_50_ksps_profile_uses_hwh_v2_delay_without_software_compensation():
    profile = resolve_fir_ddr_profile(_soccfg("50_ksps"))

    assert profile.name == "50_ksps"
    assert profile.sample_rate_hz == 50_000.0
    assert profile.sample_period_us == 20.0
    assert profile.decimation == 6000
    assert profile.software_warmup_compensation is False
    assert profile.uses_fpga_trigger_delay is True
    assert profile.trigger_delay_samples == 50
    assert profile.trigger_delay_units == "valid_input_samples"
    assert profile.trigger_delay_input_cycles == 300_000
    assert profile.trigger_delay_us == 1000.0
    assert profile.trigger_delay_arm_kwargs() == {
        "trigger_delay_samples": 50
    }
    assert profile.software_trigger_delay_output_samples == 0
    assert profile.software_aligned_trigger_input_samples == 0
    assert profile.software_trigger_delay_input_samples == 0
    assert profile.software_trigger_delay_tproc_cycles(300.0) == 0


def test_50_ksps_profile_supports_shift_line_clock_cycle_delay():
    profile = resolve_fir_ddr_profile(
        _soccfg(
            "50_ksps",
            trigger_delay_units="s_axis_aclk_cycles",
        )
    )

    assert profile.trigger_delay_samples == 50
    assert profile.trigger_delay_units == "s_axis_aclk_cycles"
    assert profile.trigger_delay_input_cycles == 50
    assert profile.trigger_delay_us == pytest.approx(50.0 / 300.0)
    assert profile.trigger_delay_arm_kwargs() == {
        "trigger_delay_cycles": 50
    }
    assert "source-clock cycles" in profile.timing_label


def test_gui_corrects_legacy_400_mhz_default_for_300_mhz_hwh():
    soccfg = _soccfg(
        "50_ksps",
        trigger_delay_units="s_axis_aclk_cycles",
    )
    soccfg["ddr4_buf"]["trigger_delay_default_cycles"] = 281_970

    profile = resolve_fir_ddr_profile(soccfg)

    assert profile.trigger_delay_samples == 211_478
    assert profile.trigger_delay_us == pytest.approx(211_478 / 300.0)
    assert profile.trigger_delay_arm_kwargs() == {
        "trigger_delay_cycles": 211_478
    }


def test_user_delay_microseconds_convert_to_hwh_reported_units():
    sample_profile = resolve_fir_ddr_profile(_soccfg("50_ksps"))
    cycle_profile = resolve_fir_ddr_profile(
        _soccfg(
            "50_ksps",
            trigger_delay_units="s_axis_aclk_cycles",
        )
    )

    assert sample_profile.trigger_delay_value_for_us(700.0) == 35
    assert sample_profile.trigger_delay_arm_kwargs_for_us(700.0) == {
        "trigger_delay_samples": 35
    }
    assert cycle_profile.trigger_delay_value_for_us(700.0) == 210_000
    assert cycle_profile.trigger_delay_arm_kwargs_for_us(700.0) == {
        "trigger_delay_cycles": 210_000
    }
    assert cycle_profile.trigger_delay_arm_kwargs_for_us() == {
        "trigger_delay_cycles": 50
    }


def test_1_msps_profile_rejects_nonzero_fpga_delay_override():
    profile = resolve_fir_ddr_profile(_soccfg("1_msps"))

    assert profile.trigger_delay_value_for_us(0.0) == 0
    with pytest.raises(RuntimeError, match="does not expose"):
        profile.trigger_delay_value_for_us(1.0)


def test_50_ksps_profile_rejects_hwh_without_v2_trigger_delay():
    soccfg = _soccfg("50_ksps")
    del soccfg["ddr4_buf"]["supports_trigger_delay"]

    with pytest.raises(RuntimeError, match="programmable trigger delay"):
        resolve_fir_ddr_profile(soccfg)


def test_unsupported_hwh_rate_is_rejected_explicitly():
    soccfg = _soccfg("1_msps")
    soccfg["ddr4_buf"]["fir_rate_profile"] = "custom"
    soccfg["ddr4_buf"]["stored_sample_rate_hz"] = 100_000.0

    with pytest.raises(RuntimeError, match="unsupported FIR-DDR"):
        resolve_fir_ddr_profile(soccfg)
