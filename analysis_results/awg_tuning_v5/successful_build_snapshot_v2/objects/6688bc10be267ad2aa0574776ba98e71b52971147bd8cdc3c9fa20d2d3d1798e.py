"""DC voltage calibration model, acquisition, and database tests.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from qick.sim import QickSim  # noqa: F401
from qick.qick_asm import QickConfig

from dc_voltage_calibration import (
    DcVoltageCalibration,
    DcVoltageCalibrationConfig,
    MAX_DC_VOLTAGE_SAMPLES_PER_POINT,
    build_dc_voltage_calibration_program,
    load_dc_voltage_calibration,
    run_dc_voltage_calibration,
)
from qick_qcodes_experiment import QCODES_STAGING_ENV, QickConnectionConfig
from qick_qcodes_experiment import _measurement_iq_values


def _dc_soccfg(*, is_50_ksps: bool = False):
    ddr4_buf = {
        "sample_capture": True,
        "fir_enabled": True,
        "fir_output_fs_mhz": 0.05 if is_50_ksps else 1.0,
        "fir_rate_profile": "50_ksps" if is_50_ksps else "1_msps",
        "fir_decimation": 6000 if is_50_ksps else 300,
        "fir_group_delay_input_samples": (
            296_677 if is_50_ksps else 8677
        ),
        "fir_input_fs_mhz": 300.0,
        "supports_trigger_delay": is_50_ksps,
        "trigger_delay_units": "valid_input_samples",
        "trigger_delay_default_samples": 50 if is_50_ksps else 0,
        "trigger_type": "dport",
        "trigger_port": 0,
        "trigger_bit": 1,
    }
    return QickConfig(
        {
            "sw_version": "0.2.357",
            "refclk_freq": 300.0,
            "tprocs": [
                {
                    "type": "axis_tproc64x32_x8",
                    "f_time": 300.0,
                    "pmem_size": 65536,
                    "dmem_size": 4096,
                }
            ],
            "gens": [
                {
                    "type": "axis_awg_tuning_v1",
                    "gen_type": "awg_tuning",
                    "tproc_ch": 0,
                    "tmux_ch": 0,
                    "f_fabric": 300.0,
                    "n_pts": 16,
                    "samps_per_clk": 16,
                    "frac": 16,
                    "cmd_width": 160,
                    "step_width": 24,
                    "duration_width": 23,
                    "fixed_width": 48,
                    "dac_invalid_lsb": 2,
                    "maxv": 32764,
                    "minv": -32768,
                    "has_mixer": False,
                    "has_dds": False,
                    "b_dds": 32,
                    "b_phase": 32,
                    "dac": "00",
                    "interpolation": 1,
                }
            ],
            "readouts": [
                {
                    "type": "axis_dyn_readout_v1",
                    "ro_type": "axis_dyn_readout_v1",
                    "tproc_ctrl": 1,
                    "tmux_ch": 0,
                    "f_fabric": 300.0,
                    "f_output": 300.0,
                    "f_dds": 300.0,
                    "fs_mult": 1,
                    "fs_div": 1,
                    "fdds_div": 1,
                    "b_dds": 32,
                    "b_phase": 32,
                    "adc": "00",
                    "buf_maxlen": 16384,
                    "has_weights": False,
                    "has_edge_counter": False,
                    "trigger_type": "dport",
                    "trigger_port": 0,
                    "trigger_bit": 0,
                }
            ],
            "ddr4_buf": ddr4_buf,
        }
    )


def test_dc_calibration_program_fixes_readout_frequency_to_zero():
    config = DcVoltageCalibrationConfig(
        database_path="calibration.db",
        output_ch=0,
        readout_ch=0,
        voltage_points=5,
        samples_per_point=8,
        repetitions_per_point=2,
    )
    program = build_dc_voltage_calibration_program(
        _dc_soccfg(), config, tproc_mhz=300.0
    )
    assert program.ddr_readout_config.readout_freq_mhz == 0.0
    assert program.sequence.sweep_point_count == 5
    assert program.sequence.segments[-1].name == "return_zero"
    assert program.sequence.segments[-1].amplitudes == (0.0,)


def test_dc_calibration_supports_long_periodic_fir_capture():
    config = DcVoltageCalibrationConfig(
        database_path="calibration.db",
        output_ch=0,
        readout_ch=0,
        voltage_points=3,
        samples_per_point=MAX_DC_VOLTAGE_SAMPLES_PER_POINT,
        repetitions_per_point=1,
    )
    program = build_dc_voltage_calibration_program(
        _dc_soccfg(), config, tproc_mhz=300.0
    )

    assert program.ddr_readout_config.samples_per_trigger == 1_000_000
    assert program.ddr_readout_config.readout_period_cycles == 65535
    assert program.summary()["point_end_tproc_cycles"] < (1 << 31)

    with pytest.raises(ValueError, match="samples_per_point must be <="):
        DcVoltageCalibrationConfig(
            database_path="calibration.db",
            samples_per_point=MAX_DC_VOLTAGE_SAMPLES_PER_POINT + 1,
        )


@pytest.mark.parametrize(
    ("is_50_ksps", "sample_period_us", "fpga_delay_us"),
    (
        (False, 1.0, 0.0),
        (True, 20.0, 1000.0),
    ),
)
def test_dc_calibration_hold_uses_hwh_fir_timing(
    is_50_ksps,
    sample_period_us,
    fpga_delay_us,
):
    config = DcVoltageCalibrationConfig(
        database_path="calibration.db",
        output_ch=0,
        readout_ch=0,
        voltage_points=3,
        samples_per_point=100,
        repetitions_per_point=1,
        settle_us=7.0,
        margin_input_samples=600,
    )
    program = build_dc_voltage_calibration_program(
        _dc_soccfg(is_50_ksps=is_50_ksps),
        config,
        tproc_mhz=300.0,
    )

    expected_hold_us = (
        config.settle_us
        + fpga_delay_us
        + config.samples_per_point * sample_period_us
        + config.margin_input_samples / 300.0
        + 2.0
    )
    assert program.sequence.segments[0].duration_cycles == int(
        np.ceil(expected_hold_us * 300.0)
    )
    assert program.ddr_readout_config.trigger_delay_tproc_cycles == int(
        np.ceil(config.settle_us * 300.0)
    )


def test_dc_scalar_adc_fit_recovers_voltage_and_ignores_q():
    voltage_mv = np.linspace(-800.0, 800.0, 17)
    voltage_v = voltage_mv / 1000.0
    mean_i = 120.0 + 5000.0 * voltage_v
    calibration = DcVoltageCalibration.fit(voltage_mv, mean_i)

    measured = np.column_stack((mean_i, np.full_like(mean_i, 12345.0)))
    converted = calibration.convert_iq(measured)
    np.testing.assert_allclose(converted[:, 0], voltage_v, atol=1.0e-12)
    np.testing.assert_allclose(converted[:, 1], 0.0, atol=1.0e-12)
    assert calibration.r_squared > 0.999999999


def test_calibration_fits_executed_incremental_dac_voltages(tmp_path):
    # The hardware sweep deliberately retains one rounded increment.
    # A fit against the ideal grid would therefore report a wrong gain.
    config = DcVoltageCalibrationConfig(
        database_path=str(tmp_path / 'cal.db'), output_ch=0, readout_ch=0,
        voltage_start_mv=5, voltage_stop_mv=15, voltage_points=200,
        samples_per_point=2, repetitions_per_point=1)
    program = build_dc_voltage_calibration_program(_dc_soccfg(), config)
    actual = program.dc_calibration_voltages_mv
    assert actual[-1] == pytest.approx(24.4140625)
    np.testing.assert_allclose(np.diff(actual), .09765625)
    adc = 50 + 4000 * actual / 1000
    fit = DcVoltageCalibration.fit(actual, adc)
    assert fit.response_adc_per_v == pytest.approx(4000)
    np.testing.assert_allclose(fit.convert_adc(adc)*1000, actual, atol=1e-12)
    wrong = DcVoltageCalibration.fit(config.voltages_mv, adc)
    assert wrong.response_adc_per_v != pytest.approx(4000)


@pytest.mark.parametrize('count', [5, 33, 200])
@pytest.mark.parametrize('reverse', [False, True])
def test_full_scale_calibration_keeps_constant_step_inside_dac_rails(count, reverse):
    start, stop = ((800, -800) if reverse else (-800, 800))
    config = DcVoltageCalibrationConfig(database_path='unused.db', output_ch=0,
        voltage_start_mv=start, voltage_stop_mv=stop, voltage_points=count,
        samples_per_point=2, repetitions_per_point=1)
    program = build_dc_voltage_calibration_program(_dc_soccfg(), config)
    actual = program.dc_calibration_voltages_mv
    assert np.min(actual) >= -800
    assert np.max(actual) <= 32764*800/32768
    np.testing.assert_allclose(np.diff(actual), actual[1]-actual[0])
    assert actual[-1] < actual[0] if reverse else actual[-1] > actual[0]


def test_acquisition_persists_actual_calibration_reference(tmp_path, monkeypatch):
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / 'staging'))
    config = DcVoltageCalibrationConfig(
        database_path=str(tmp_path / 'cal.db'), output_ch=0, readout_ch=0,
        voltage_start_mv=5, voltage_stop_mv=15, voltage_points=200,
        samples_per_point=2, repetitions_per_point=1)
    soc = SimpleNamespace(rfb_set_gen_dc=lambda ch: None, rfb_set_ro_dc=lambda ch, gain: gain)
    def acquire(_soc, program):
        iq = np.zeros((200, 1, 2, 2))
        iq[..., 0] = (50 + 4000*program.dc_calibration_voltages_mv/1000)[:, None, None]
        return SimpleNamespace(iq=iq)
    stored = run_dc_voltage_calibration(
        connection_config=QickConnectionConfig(host='127.0.0.1'),
        calibration_config=config, connector=lambda **kwargs: (soc, _dc_soccfg()),
        acquisition_callback=acquire)
    assert stored.result['voltages_mv'][-1] == pytest.approx(24.4140625)
    assert stored.result['calibration']['response_adc_per_v'] == pytest.approx(4000)
    import json
    metadata = json.loads(stored.dataset.get_metadata('DC_Voltage_Calibration_Config'))
    assert metadata['voltage_reference'] == 'compiled_set_codes'
    assert metadata['requested_voltages_mv'][-1] == 15
    assert metadata['fit_voltages_mv'][-1] == pytest.approx(24.4140625)
    stored.dataset.conn.close()


def test_dc_voltage_calibration_run_and_qcodes_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging"))
    database_path = tmp_path / "gain_pwr_calb.db"
    config = DcVoltageCalibrationConfig(
        database_path=str(database_path),
        output_ch=3,
        readout_ch=2,
        voltage_start_mv=-800.0,
        voltage_stop_mv=800.0,
        voltage_points=9,
        output_full_scale_mv=800.0,
        samples_per_point=8,
        repetitions_per_point=3,
        input_dc_gain_db=6.0,
        settle_us=2.0,
    )
    calls = []

    class FakeSoc:
        def rfb_set_gen_dc(self, channel):
            calls.append(("gen_dc", channel))

        def rfb_set_ro_dc(self, channel, gain):
            calls.append(("ro_dc", channel, gain))
            return float(gain)

    class FakeProgram:
        pass

    def program_factory(_soccfg, received_config, *, tproc_mhz=None):
        assert received_config == config
        assert tproc_mhz == 300.0
        # DC calibration has no RF frequency field; its readout is fixed at 0 MHz.
        return FakeProgram()

    def acquire(_soc, _program):
        voltage_v = config.voltages_mv / 1000.0
        iq = np.empty(
            (
                config.voltage_points,
                config.repetitions_per_point,
                config.samples_per_point,
                2,
            ),
            dtype=float,
        )
        iq[..., 0] = (50.0 + 4000.0 * voltage_v)[:, None, None]
        iq[..., 1] = (-25.0 + 3000.0 * voltage_v)[:, None, None]
        return SimpleNamespace(iq=iq)

    stored = run_dc_voltage_calibration(
        connection_config=QickConnectionConfig(host="127.0.0.1"),
        calibration_config=config,
        tproc_mhz=300.0,
        connector=lambda **_kwargs: (FakeSoc(), object()),
        program_factory=program_factory,
        acquisition_callback=acquire,
    )
    assert stored.run_id > 0
    assert stored.row_count == config.voltage_points
    assert calls == [("gen_dc", 3), ("ro_dc", 2, 6.0)]

    loaded = load_dc_voltage_calibration(
        database_path,
        readout_ch=2,
        input_dc_gain_db=6.0,
    )
    assert loaded.run_id == stored.run_id
    assert loaded.output_ch == 3
    test_voltage_v = np.asarray([-0.4, 0.0, 0.7])
    test_iq = np.column_stack((50.0 + 4000.0 * test_voltage_v, [9, 8, 7]))
    converted = loaded.convert_iq(test_iq)
    np.testing.assert_allclose(converted[:, 0], test_voltage_v, atol=1.0e-12)
    np.testing.assert_allclose(converted[:, 1], 0.0, atol=1.0e-12)

    stored_iq, unit, mode, metadata = _measurement_iq_values(
        test_iq.reshape(1, 1, 3, 2),
        {
            "readout_details": {
                "board_type": "DC_In",
                "ro_ch": 2,
                "commanded_dc_gain_db": 6.0,
                "dc_measure_mode": False,
                "dc_voltage_calibration_enabled": True,
                "dc_voltage_calibration_database_path": str(database_path),
                "dc_voltage_calibration_run_id": stored.run_id,
            }
        },
    )
    assert unit == "V"
    assert mode == "dc_voltage_iq"
    assert metadata["dc_voltage_calibration_run_id"] == stored.run_id
    np.testing.assert_allclose(
        stored_iq[0, 0, :, 0], test_voltage_v, atol=1.0e-12
    )
    np.testing.assert_allclose(stored_iq[0, 0, :, 1], 0.0, atol=1.0e-12)


def test_dc_voltage_calibration_rejects_disconnected_loopback(tmp_path):
    database_path = tmp_path / "disconnected.db"
    config = DcVoltageCalibrationConfig(
        database_path=str(database_path),
        output_ch=1,
        readout_ch=3,
        voltage_points=5,
        samples_per_point=2,
        repetitions_per_point=1,
    )

    class FakeSoc:
        def rfb_set_gen_dc(self, _channel):
            pass

        def rfb_set_ro_dc(self, _channel, gain):
            return float(gain)

    def acquire(_soc, _program):
        iq = np.zeros((5, 1, 2, 2), dtype=float)
        iq[..., 0] = np.asarray([99.2, 100.5, 99.8, 100.4, 100.0])[:, None, None]
        return SimpleNamespace(iq=iq)

    with pytest.raises(RuntimeError, match="selected front-panel SMA pair"):
        run_dc_voltage_calibration(
            connection_config=QickConnectionConfig(host="127.0.0.1"),
            calibration_config=config,
            tproc_mhz=300.0,
            connector=lambda **_kwargs: (FakeSoc(), object()),
            program_factory=lambda *_args, **_kwargs: object(),
            acquisition_callback=acquire,
        )
    assert database_path.exists() is False


def test_dc_voltage_calibration_cancel_discards_acquired_data(tmp_path):
    database_path = tmp_path / "cancelled_dc_voltage.db"
    config = DcVoltageCalibrationConfig(
        database_path=str(database_path),
        output_ch=1,
        readout_ch=2,
        voltage_points=3,
        samples_per_point=2,
        repetitions_per_point=1,
    )
    state = {"acquired": False}

    class CalibrationStopped(RuntimeError):
        pass

    class FakeSoc:
        def rfb_set_gen_dc(self, _channel):
            pass

        def rfb_set_ro_dc(self, _channel, gain):
            return float(gain)

    def acquire(_soc, _program):
        state["acquired"] = True
        iq = np.zeros((3, 1, 2, 2), dtype=float)
        return SimpleNamespace(iq=iq)

    def cancel_check():
        if state["acquired"]:
            raise CalibrationStopped("stopped")

    with pytest.raises(CalibrationStopped, match="stopped"):
        run_dc_voltage_calibration(
            connection_config=QickConnectionConfig(host="127.0.0.1"),
            calibration_config=config,
            connector=lambda **_kwargs: (FakeSoc(), object()),
            program_factory=lambda *_args, **_kwargs: object(),
            acquisition_callback=acquire,
            cancel_check=cancel_check,
        )

    assert state["acquired"] is True
    assert not database_path.exists()


def test_dc_voltage_config_rejects_points_outside_full_scale():
    try:
        DcVoltageCalibrationConfig(
            database_path="calibration.db",
            voltage_start_mv=-900.0,
            voltage_stop_mv=800.0,
            output_full_scale_mv=800.0,
        )
    except ValueError as exc:
        assert "+/- output full scale" in str(exc)
    else:
        raise AssertionError("out-of-range DC voltage sweep was accepted")
