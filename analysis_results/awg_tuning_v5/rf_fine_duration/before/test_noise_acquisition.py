"""Direct FIR-DDR Noise Analysis acquisition tests.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import numpy as np

from qick.sim import QickSim  # noqa: F401
from qick.qick_asm import QickConfig

from noise_acquisition import (
    NoiseAcquisitionConfig,
    acquire_noise_fir_trace,
    build_noise_fir_program,
)


class _FakeSoc:
    def __init__(self, samples: int):
        self.samples = samples
        self.calls = []

    def set_nyquist(self, ch, nqz, *, blocktype):
        self.calls.append(("nyquist", ch, nqz, blocktype))

    def rfb_set_ro_rf(self, ch, attenuation):
        self.calls.append(("rf", ch, attenuation))
        return attenuation

    def rfb_set_ro_dc(self, ch, gain):
        self.calls.append(("dc", ch, gain))
        return gain

    def rfb_set_ro_filter(self, ch, *, fc, bw, ftype):
        self.calls.append(("filter", ch, fc, bw, ftype))

    def arm_ddr4_fir_samples(self, **kwargs):
        self.calls.append(("arm", kwargs))
        return 512

    def get_ddr4_fir_samples(self, **kwargs):
        self.calls.append(("read", kwargs))
        values = np.arange(self.samples, dtype=np.int64)
        return np.column_stack((values, -values))


class _FakeProgram:
    def __init__(self):
        self.calls = []

    def run_rounds(self, soc, *, progress):
        self.calls.append((soc, progress))


def _soccfg(*, fir_rate_profile="1_msps"):
    is_50_ksps = fir_rate_profile == "50_ksps"
    return {
        "ddr4_buf": {
            "sample_capture": True,
            "fir_enabled": True,
            "fir_rate_profile": fir_rate_profile,
            "stored_sample_rate_hz": (
                50_000.0 if is_50_ksps else 1_000_000.0
            ),
            "fir_output_fs_mhz": 0.05 if is_50_ksps else 1.0,
            "fir_decimation": 6000 if is_50_ksps else 300,
            "fir_input_fs_mhz": 300.0,
            "fir_group_delay_input_samples": (
                296_677.0 if is_50_ksps else 8677.0
            ),
            "supports_trigger_delay": is_50_ksps,
            "trigger_delay_units": (
                "s_axis_aclk_cycles"
                if is_50_ksps
                else "valid_input_samples"
            ),
            "trigger_delay_default_cycles": 50 if is_50_ksps else 0,
            "trigger_delay_default_samples": 0,
            "trigger_port": 0,
            "trigger_bit": 1,
        },
        "readouts": [{
            "type": "axis_dyn_readout_v1",
            "ro_type": "axis_dyn_readout_v1",
            "tproc_ctrl": 1,
            "tmux_ch": 0,
            "f_fabric": 300.0,
            "buf_maxlen": 4096,
            "b_dds": 32,
            "b_phase": 32,
            "f_dds": 300.0,
            "f_output": 300.0,
            "fs_mult": 1,
            "fs_div": 1,
            "fdds_div": 1,
            "adc": "00",
            "has_weights": False,
            "has_edge_counter": False,
            "trigger_port": 0,
            "trigger_bit": 0,
        }],
        "gens": [],
        "tprocs": [{
            "type": "axis_tproc64x32_x8",
            "f_time": 300.0,
            "pmem_size": 65536,
            "dmem_size": 4096,
            "output_pins": [],
        }],
    }


def test_direct_noise_acquisition_uses_only_requested_input_and_fir_length():
    config = NoiseAcquisitionConfig(
        host="noise-qick",
        ns_port=9999,
        proxy_name="noise-proxy",
        ro_ch=0,
        input_board_type="RF_In",
        nqz=2,
        fir_samples=128,
        readout_frequency_mhz=43.5,
        attenuation_db=12.25,
        filter_type="bandpass",
        filter_cutoff_ghz=0.5,
        filter_bandwidth_ghz=0.2,
        margin_input_samples=600,
        post_run_read_delay_seconds=0.25,
    )
    soc = _FakeSoc(config.fir_samples)
    program = _FakeProgram()
    connection_calls = []
    sleeps = []
    progress = []

    def connector(**kwargs):
        connection_calls.append(kwargs)
        return soc, _soccfg()

    result = acquire_noise_fir_trace(
        config,
        connector=connector,
        program_factory=lambda soccfg, received: (
            program
            if soccfg is not None and received is config
            else None
        ),
        sleeper=sleeps.append,
        progress_callback=lambda percent, message: progress.append(
            (percent, message)
        ),
    )

    assert connection_calls == [{
        "ns_host": "noise-qick",
        "ns_port": 9999,
        "proxy_name": "noise-proxy",
    }]
    assert ("nyquist", 0, 2, "adc") in soc.calls
    assert ("rf", 0, 12.25) in soc.calls
    assert ("filter", 0, 0.5, 0.2, "bandpass") in soc.calls
    arm = next(call[1] for call in soc.calls if call[0] == "arm")
    read = next(call[1] for call in soc.calls if call[0] == "read")
    assert arm["n_samples"] == read["n_samples"] == 128
    assert arm["n_triggers"] == read["n_triggers"] == 1
    assert program.calls == [(soc, False)]
    assert len(sleeps) == 1
    assert sleeps[0] > 0.25
    assert result.iq.shape == (128, 2)
    assert result.sample_rate_hz == 1_000_000.0
    assert result.reserved_physical_words == 512
    assert progress[-1] == (100, "Noise trace acquired")


def test_direct_noise_acquisition_supports_dc_input_without_rf_filter():
    config = NoiseAcquisitionConfig(
        ro_ch=0,
        input_board_type="DC_In",
        dc_gain_db=6.0,
        fir_samples=32,
        post_run_read_delay_seconds=0.0,
    )
    soc = _FakeSoc(config.fir_samples)
    program = _FakeProgram()
    acquire_noise_fir_trace(
        config,
        connector=lambda **_kwargs: (soc, _soccfg()),
        program_factory=lambda _soccfg, _config: program,
        sleeper=lambda _seconds: None,
    )

    assert ("dc", 0, 6.0) in soc.calls
    assert not any(call[0] == "filter" for call in soc.calls)


def test_direct_noise_acquisition_uses_50_ksps_hwh_and_v2_trigger_delay():
    config = NoiseAcquisitionConfig(
        fir_samples=100,
        post_run_read_delay_seconds=0.0,
    )
    soc = _FakeSoc(config.fir_samples)
    program = _FakeProgram()
    sleeps = []

    result = acquire_noise_fir_trace(
        config,
        connector=lambda **_kwargs: (
            soc,
            _soccfg(fir_rate_profile="50_ksps"),
        ),
        program_factory=lambda _soccfg, _config: program,
        sleeper=sleeps.append,
    )

    arm = next(call[1] for call in soc.calls if call[0] == "arm")
    assert arm["trigger_delay_cycles"] == 50
    assert result.sample_rate_hz == 50_000.0
    assert result.iq.shape == (100, 2)
    expected_sleep = (
        100 / 50_000.0
        + 50 / 300_000_000.0
        + (296_677.0 + config.margin_input_samples) / 300_000_000.0
    )
    assert abs(sleeps[0] - expected_sleep) < 1.0e-12
    assert "50_ksps" in result.source


def test_noise_program_delays_only_the_1_msps_tprocessor_trigger():
    one_msps = build_noise_fir_program(
        QickConfig(_soccfg(fir_rate_profile="1_msps")),
        NoiseAcquisitionConfig(fir_samples=8),
    )
    fifty_ksps = build_noise_fir_program(
        QickConfig(_soccfg(fir_rate_profile="50_ksps")),
        NoiseAcquisitionConfig(fir_samples=8),
    )

    assert one_msps.noise_fir_software_trigger_delay_tproc_cycles == 8397
    assert fifty_ksps.noise_fir_software_trigger_delay_tproc_cycles == 0


def test_noise_acquisition_rejects_non_fir_hwh():
    config = NoiseAcquisitionConfig(fir_samples=16)
    soccfg = _soccfg()
    soccfg["ddr4_buf"]["fir_enabled"] = False
    try:
        acquire_noise_fir_trace(
            config,
            connector=lambda **_kwargs: (_FakeSoc(16), soccfg),
            sleeper=lambda _seconds: None,
        )
    except RuntimeError as exc:
        assert "FIR DDR path" in str(exc)
    else:
        raise AssertionError("non-FIR HWH was accepted")
