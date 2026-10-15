"""Output-scope and input-ADC calibration tests.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt5 import QtWidgets
import pytest
import qick.asm_v1 as qick_asm_v1

import calibration_gui as calibration_gui_module
import qick_power_calibration as calibration_module
from calibration_gui import (
    CalibrationCancelled,
    CalibrationPanel,
    CalibrationWorker,
    dc_voltage_calibration_plot_data,
    input_calibration_plot_data,
)
from power_calibration import CalibrationDatabase, MAX_QICK_GAIN
from qick_power_calibration import (
    InputPowerCalibrationConfig,
    InvalidOscilloscopePowerError,
    KeysightFftPowerMeter,
    OscilloscopeConfig,
    OutputPowerCalibrationConfig,
    run_input_power_calibration,
    run_output_power_calibration,
)
from qick_qcodes_experiment import QCODES_STAGING_ENV, QickConnectionConfig
from qick_sparameter_sweep import SParameterSweepResult, apply_power_calibration


def _application():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_calibration_panel_stop_button_tracks_running_state():
    app = _application()
    panel = CalibrationPanel()
    stops = []
    panel.stop_requested.connect(lambda: stops.append(True))

    assert panel.stop_button.isHidden()
    assert not panel.stop_button.isEnabled()

    panel.set_running(True, "Running")
    app.processEvents()
    assert not panel.stop_button.isHidden()
    assert panel.stop_button.isEnabled()
    panel.stop_button.click()
    assert stops == [True]

    panel.set_stopping("Stopping safely")
    assert not panel.stop_button.isEnabled()
    assert panel.status.text() == "Stopping safely"

    panel.set_running(False, "Stopped")
    app.processEvents()
    assert panel.stop_button.isHidden()
    assert not panel.stop_button.isEnabled()
    panel.close()


def test_input_calibration_avg_source_round_trip_and_disables_fir_delay(tmp_path):
    _application()
    panel = CalibrationPanel()
    panel.database_path.setText(str(tmp_path / "gain_pwr_calb.db"))
    panel.input_override_fpga_trigger_delay.setChecked(True)
    panel.input_acquisition_source.setCurrentIndex(
        panel.input_acquisition_source.findData("avg_buffer")
    )

    config = panel.input_config()
    sweep = config.sweep_config(1234)
    assert config.acquisition_source == "avg_buffer"
    assert sweep.acquisition_source == "avg_buffer"
    assert sweep.avg_repetitions == 1
    assert sweep.fpga_trigger_delay_us is None
    assert not panel.input_override_fpga_trigger_delay.isEnabled()
    assert panel.run_input_button.text() == "Run AVG-Buffer Input Calibration"

    settings = panel.settings_dict()
    restored = CalibrationPanel()
    restored.load_settings(settings)
    assert restored.input_config().acquisition_source == "avg_buffer"
    assert restored.run_input_button.text() == "Run AVG-Buffer Input Calibration"
    panel.close()
    restored.close()


def test_input_calibration_rejects_unknown_acquisition_source(tmp_path):
    with pytest.raises(ValueError, match="acquisition_source"):
        InputPowerCalibrationConfig(
            database_path=str(tmp_path / "gain_pwr_calb.db"),
            acquisition_source="unknown",
        )


def test_calibration_worker_emits_cancelled(monkeypatch):
    def cancelled_runner(**kwargs):
        kwargs["cancel_check"]()
        raise AssertionError("cancel_check should have raised")

    monkeypatch.setattr(
        calibration_gui_module,
        "run_output_power_calibration",
        cancelled_runner,
    )
    worker = CalibrationWorker("output", {})
    cancellations = []
    failures = []
    worker.cancelled.connect(cancellations.append)
    worker.failed.connect(failures.append)
    worker.request_cancel()
    worker.run()

    assert cancellations == ["Calibration stopped by user"]
    assert failures == []


class _FakeSoc:
    def rfb_set_gen_rf(self, _channel, att1, att2):
        return float(att1), float(att2)

    def rfb_set_gen_filter(self, *_args, **_kwargs):
        return None

    def rfb_set_ro_rf(self, _channel, attenuation):
        return float(attenuation)

    def rfb_set_ro_filter(self, *_args, **_kwargs):
        return None


def test_keysight_fft_adapter_uses_original_notebook_scpi(monkeypatch):
    class Instrument:
        def __init__(self):
            self.commands = []
            self.responses = iter(("-20", "-22"))
            self.timeout = None
            self.write_termination = None
            self.read_termination = None

        def write(self, command):
            self.commands.append(command)

        def query(self, command):
            self.commands.append(command)
            if command == "*IDN?":
                return "AGILENT TECHNOLOGIES,DSO-X 6004A,TEST,1.0"
            return next(self.responses)

        def close(self):
            self.commands.append("CLOSE")

    instrument = Instrument()

    class ResourceManager:
        def open_resource(self, resource):
            assert resource == "USB::TEST"
            return instrument

        def close(self):
            pass

    monkeypatch.setitem(
        sys.modules,
        "pyvisa",
        SimpleNamespace(ResourceManager=ResourceManager),
    )
    config = OscilloscopeConfig(
        visa_resource="USB::TEST",
        average_count=2,
        settle_seconds=0.0,
        sample_interval_seconds=0.0,
    )
    with KeysightFftPowerMeter(config) as meter:
        assert meter.measure_power_dbm(450.0) == -21.0

    assert ":FUNCtion1:OPERation FFT" in instrument.commands
    assert ":FUNCtion1:SOURce CHANnel2" in instrument.commands
    assert ":MARKer:X1Position 450000000" in instrument.commands
    assert instrument.commands.count(":MARKer:Y1Position?") == 2


def test_keysight_fft_adapter_rejects_absurd_power(monkeypatch):
    class Instrument:
        def __init__(self):
            self.timeout = None
            self.write_termination = None
            self.read_termination = None

        def write(self, _command):
            pass

        def query(self, command):
            if command == "*IDN?":
                return "AGILENT TECHNOLOGIES,DSO-X 6004A,TEST,1.0"
            return "1e30"

        def close(self):
            pass

    class ResourceManager:
        def open_resource(self, _resource):
            return Instrument()

        def close(self):
            pass

    monkeypatch.setitem(
        sys.modules,
        "pyvisa",
        SimpleNamespace(ResourceManager=ResourceManager),
    )
    config = OscilloscopeConfig(
        visa_resource="USB::TEST",
        average_count=1,
        settle_seconds=0.0,
        sample_interval_seconds=0.0,
    )
    with KeysightFftPowerMeter(config) as meter:
        with pytest.raises(
            InvalidOscilloscopePowerError,
            match="outside the valid calibration range",
        ):
            meter.measure_power_dbm(450.0)


def test_keysight_fft_adapter_averages_remaining_valid_readings(monkeypatch):
    class Instrument:
        def __init__(self):
            self.responses = iter(("-20", "1e30", "-22"))
            self.timeout = None
            self.write_termination = None
            self.read_termination = None

        def write(self, _command):
            pass

        def query(self, command):
            if command == "*IDN?":
                return "AGILENT TECHNOLOGIES,DSO-X 6004A,TEST,1.0"
            return next(self.responses)

        def close(self):
            pass

    class ResourceManager:
        def open_resource(self, _resource):
            return Instrument()

        def close(self):
            pass

    monkeypatch.setitem(
        sys.modules,
        "pyvisa",
        SimpleNamespace(ResourceManager=ResourceManager),
    )
    config = OscilloscopeConfig(
        visa_resource="USB::TEST",
        average_count=3,
        settle_seconds=0.0,
        sample_interval_seconds=0.0,
    )
    with KeysightFftPowerMeter(config) as meter:
        assert meter.measure_power_dbm(450.0) == -21.0
        assert meter.last_reading_count == 3
        assert meter.last_rejected_reading_count == 1


def test_output_calibration_clamps_periodic_word_not_total_tone_time(monkeypatch):
    pulse_registers = []

    class FakeProgram:
        def __init__(self, _soccfg):
            pass

        def declare_gen(self, **_kwargs):
            pass

        def freq2reg(self, frequency_mhz, **_kwargs):
            return int(round(float(frequency_mhz) * 1000.0))

        def set_pulse_registers(self, **kwargs):
            pulse_registers.append(dict(kwargs))

        def pulse(self, **_kwargs):
            pass

        def end(self):
            pass

        def run(self, _soc):
            pass

        def reg2freq(self, word, **_kwargs):
            return float(word) / 1000.0

    monkeypatch.setattr(qick_asm_v1, "QickProgram", FakeProgram)

    actual_frequency = calibration_module._run_tone_program(
        object(),
        object(),
        output_ch=0,
        nqz=1,
        frequency_mhz=450.0,
        gain=20_000,
        length_cycles=300_000,
    )
    calibration_module._run_tone_program(
        object(),
        object(),
        output_ch=0,
        nqz=1,
        frequency_mhz=450.0,
        gain=0,
        length_cycles=300_000,
    )

    assert actual_frequency == 450.0
    assert pulse_registers[0]["mode"] == "periodic"
    assert pulse_registers[0]["length"] == 65535
    assert pulse_registers[1]["mode"] == "oneshot"
    assert pulse_registers[1]["length"] == 3


def test_input_calibration_plot_data_restores_positive_linear_quantities():
    frequencies, gains, input_mw, adc_magnitude = input_calibration_plot_data(
        {
            "frequencies_mhz": [400.0, 500.0],
            "gains": [1000, 2000],
            "input_power_dbm": [[-30.0, -20.0], [-20.0, -10.0]],
            "adc_magnitude_db": [
                [0.0, 20.0],
                [20.0 * np.log10(2.0), 40.0],
            ],
        }
    )

    np.testing.assert_array_equal(frequencies, [400.0, 500.0])
    np.testing.assert_array_equal(gains, [1000.0, 2000.0])
    np.testing.assert_allclose(input_mw, [[0.001, 0.01], [0.01, 0.1]])
    np.testing.assert_allclose(adc_magnitude, [[1.0, 10.0], [2.0, 100.0]])


def test_input_calibration_result_plot_has_independent_axis_scales(tmp_path):
    app = _application()
    panel = CalibrationPanel()
    stored = SimpleNamespace(
        run_id=17,
        row_count=8,
        board_type="RF_In",
        database_path=tmp_path / "gain_pwr_calb.db",
        result={
            "frequencies_mhz": [400.0, 500.0],
            "gains": [1000, 2000, 3000],
            "input_power_dbm": [
                [-40.0, -39.0],
                [-30.0, -29.0],
                [-20.0, -19.0],
            ],
            "adc_magnitude_db": [
                [10.0, 11.0],
                [20.0, 21.0],
                [30.0, 31.0],
            ],
        },
    )

    panel.show_result(stored)
    app.processEvents()

    plot = panel.input_response_plot
    assert panel.tabs.currentIndex() == 1
    assert plot.x_scale_mode == "log"
    assert plot.y_scale_mode == "log"
    np.testing.assert_array_equal(plot.displayed_frequency_indices, [0, 1])
    plot.set_axis_scales("linear", "log")
    assert plot.x_scale_mode == "linear"
    assert plot.y_scale_mode == "log"
    assert panel.settings_dict()["input_plot"] == {
        "x_scale": "linear",
        "y_scale": "log",
    }
    panel.close()


def test_dc_voltage_calibration_result_plots_adc_against_voltage(tmp_path):
    app = _application()
    result = {
        "voltages_mv": [-800.0, 0.0, 800.0],
        "mean_adc": [-1590.0, 10.0, 1610.0],
        "std_adc": [3.0, 2.0, 4.0],
        "calibration": {
            "offset_adc": 10.0,
            "response_adc_per_v": 2000.0,
            "r_squared": 1.0,
            "rmse_adc": 0.0,
        },
    }
    voltage, mean_adc, std_adc, fitted_adc = dc_voltage_calibration_plot_data(
        result
    )
    np.testing.assert_allclose(voltage, [-800.0, 0.0, 800.0])
    np.testing.assert_allclose(mean_adc, [-1590.0, 10.0, 1610.0])
    np.testing.assert_allclose(std_adc, [3.0, 2.0, 4.0])
    np.testing.assert_allclose(fitted_adc, mean_adc)

    database_path = tmp_path / "dc_voltage_calibration.db"
    stored = SimpleNamespace(
        result=result,
        database_path=database_path,
        run_id=37,
        board_type="DC_In",
        row_count=3,
    )
    panel = CalibrationPanel()
    panel.show_result(stored)
    app.processEvents()

    plot = panel.dc_voltage_response_plot
    assert panel.tabs.currentIndex() == 2
    np.testing.assert_allclose(plot.voltages_mv, voltage)
    np.testing.assert_allclose(plot.mean_adc, mean_adc)
    np.testing.assert_allclose(plot.std_adc, std_adc)
    np.testing.assert_allclose(plot.fitted_adc, fitted_adc)
    assert "2000 ADC/V" in plot.status.text()
    assert panel.dc_application_run_id.value() == 37
    panel.close()


def test_dc_calibration_application_is_owned_by_calibration_tab(tmp_path):
    app = _application()
    database_path = tmp_path / "dc_voltage_calibration.db"
    panel = CalibrationPanel()
    changes = []
    panel.dc_application_changed.connect(
        lambda enabled, path, run_id: changes.append(
            (enabled, path, run_id)
        )
    )
    panel.set_dc_application_selection(True, str(database_path), 19)
    app.processEvents()

    assert panel.tabs.tabText(2) == "DC Voltage"
    assert panel.dc_application_group.isChecked() is True
    assert panel.dc_application_path.text() == str(database_path)
    assert panel.dc_application_run_id.value() == 19
    assert changes[-1] == (True, str(database_path), 19)
    settings = panel.settings_dict()
    assert settings["dc_voltage_application"] == {
        "enabled": True,
        "database_path": str(database_path),
        "run_id": 19,
    }

    restored = CalibrationPanel()
    restored.load_settings(settings)
    assert restored.settings_dict() == settings
    panel.close()
    restored.close()


def test_calibration_subtab_paths_round_trip_independently(tmp_path):
    _application()
    panel = CalibrationPanel()
    panel.database_path.setText(str(tmp_path / "gain_pwr_calb.db"))
    output_path = panel.path_diagram_for("output").applied_values()
    output_path.update(
        output_ch=2,
        output_att1_db=3.25,
        output_att2_db=4.5,
    )
    input_path = panel.path_diagram_for("input").applied_values()
    input_path.update(
        output_ch=4,
        readout_ch=3,
        output_att1_db=8.0,
        readout_attenuation_db=11.25,
    )
    dc_path = panel.path_diagram_for("dc_voltage").applied_values()
    dc_path.update(
        output_ch=6,
        readout_ch=5,
        readout_dc_gain_db=12.0,
    )
    panel.apply_path_settings(output_path, mode="output")
    panel.apply_path_settings(input_path, mode="input")
    panel.apply_path_settings(dc_path, mode="dc_voltage")

    settings = panel.settings_dict()
    restored = CalibrationPanel()
    restored.load_settings(settings)

    assert restored.path_diagram_for("output").applied_values() == output_path
    assert restored.path_diagram_for("input").applied_values() == input_path
    assert restored.path_diagram_for("dc_voltage").applied_values() == dc_path
    assert restored.output_ch.value() == 2
    assert restored.input_output_ch.value() == 4
    assert restored.input_readout_ch.value() == 3
    assert restored.dc_voltage_output_ch.value() == 6
    assert restored.dc_voltage_readout_ch.value() == 5

    legacy = dict(settings)
    legacy.pop("paths")
    migrated = CalibrationPanel()
    migrated.load_settings(legacy)
    assert migrated.path_diagram_for("output").applied_values()["output_ch"] == 2
    assert migrated.path_diagram_for("input").applied_values()["output_ch"] == 4
    assert migrated.path_diagram_for("dc_voltage").applied_values()["output_ch"] == 6
    panel.close()
    restored.close()
    migrated.close()


def test_dc_voltage_uses_front_panel_path_and_long_sample_count(tmp_path):
    _application()
    panel = CalibrationPanel()
    panel.database_path.setText(str(tmp_path / "gain_pwr_calb.db"))
    dc_path = panel.path_diagram_for("dc_voltage").applied_values()
    dc_path.update(
        output_ch=3,
        readout_ch=3,
        readout_dc_gain_db=6.0,
    )
    panel.path_diagram_for("dc_voltage").apply_external_settings(dc_path)

    # Stale compatibility widgets must not override the visible front-panel path.
    panel.dc_voltage_output_ch.setValue(1)
    panel.dc_voltage_readout_ch.setValue(2)
    panel.dc_voltage_input_gain.setValue(0.0)
    panel.dc_voltage_samples.setValue(250_000)
    config = panel.dc_voltage_config()

    assert config.output_ch == 3
    assert config.readout_ch == 3
    assert config.input_dc_gain_db == 6.0
    assert config.samples_per_point == 250_000
    assert panel.dc_voltage_samples.maximum() == 1_000_000
    assert "generator 3 -> DC input readout 3" in panel.dc_voltage_path_note.text()
    panel.close()


def _create_output_calibration(tmp_path, monkeypatch):
    database_path = tmp_path / "gain_pwr_calb.db"
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging"))
    state = {"gain": 0}
    tone_calls = []

    def tone_runner(
        _soc,
        _soccfg,
        output_ch,
        nqz,
        frequency_mhz,
        gain,
        length_cycles,
    ):
        state["gain"] = int(gain)
        tone_calls.append((output_ch, nqz, frequency_mhz, gain, length_cycles))
        return float(frequency_mhz)

    class Meter:
        idn = "AGILENT TECHNOLOGIES,DSO-X 6004A,TEST,1.0"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def measure_power_dbm(self, frequency_mhz):
            response = -10.0 - 0.02 * (float(frequency_mhz) - 400.0)
            return response + 20.0 * np.log10(state["gain"] / MAX_QICK_GAIN)

    config = OutputPowerCalibrationConfig(
        database_path=str(database_path),
        output_board_type="RF_Out",
        frequency_start_mhz=400.0,
        frequency_end_mhz=420.0,
        frequency_points=3,
        gain_start=1000,
        gain_end=10000,
        gain_points=3,
        oscilloscope=OscilloscopeConfig(visa_resource="MOCK"),
    )
    stored = run_output_power_calibration(
        connection_config=QickConnectionConfig(host="127.0.0.1"),
        calibration_config=config,
        connector=lambda **_kwargs: (_FakeSoc(), object()),
        power_meter_factory=lambda _config: Meter(),
        tone_runner=tone_runner,
    )
    assert stored.run_id > 0
    assert stored.row_count == 9
    assert tone_calls[-1][3] == 0
    return database_path, stored


def test_output_calibration_cancel_stops_tone_without_saving(tmp_path):
    database_path = tmp_path / "cancelled_gain_pwr_calb.db"
    state = {"gain": 0, "measurements": 0}
    tone_calls = []

    def tone_runner(
        _soc,
        _soccfg,
        output_ch,
        nqz,
        frequency_mhz,
        gain,
        length_cycles,
    ):
        state["gain"] = int(gain)
        tone_calls.append((output_ch, nqz, frequency_mhz, gain, length_cycles))
        return float(frequency_mhz)

    class Meter:
        idn = "MOCK"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def measure_power_dbm(self, _frequency_mhz):
            state["measurements"] += 1
            return -30.0

    def cancel_check():
        if state["measurements"] >= 1:
            raise CalibrationCancelled("Calibration stopped by user")

    config = OutputPowerCalibrationConfig(
        database_path=str(database_path),
        output_board_type="RF_Out",
        frequency_start_mhz=400.0,
        frequency_end_mhz=420.0,
        frequency_points=3,
        gain_start=1000,
        gain_end=10_000,
        gain_points=3,
        oscilloscope=OscilloscopeConfig(visa_resource="MOCK"),
    )

    with pytest.raises(CalibrationCancelled, match="stopped by user"):
        run_output_power_calibration(
            connection_config=QickConnectionConfig(host="127.0.0.1"),
            calibration_config=config,
            connector=lambda **_kwargs: (_FakeSoc(), object()),
            power_meter_factory=lambda _config: Meter(),
            tone_runner=tone_runner,
            cancel_check=cancel_check,
        )

    assert state["measurements"] == 1
    assert tone_calls[-1][3] == 0
    assert not database_path.exists()


def test_output_calibration_excludes_absurd_scope_point(tmp_path, monkeypatch):
    database_path = tmp_path / "filtered_gain_pwr_calb.db"
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path / "staging"))
    state = {"gain": 0, "frequency_mhz": 0.0}

    def tone_runner(
        _soc,
        _soccfg,
        _output_ch,
        _nqz,
        frequency_mhz,
        gain,
        _length_cycles,
    ):
        state["gain"] = int(gain)
        state["frequency_mhz"] = float(frequency_mhz)
        return float(frequency_mhz)

    class Meter:
        idn = "AGILENT TECHNOLOGIES,DSO-X 6004A,TEST,1.0"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def measure_power_dbm(self, _frequency_mhz):
            if state["gain"] == 10_000 and state["frequency_mhz"] == 420.0:
                return 1.0e30
            return -10.0 + 20.0 * np.log10(state["gain"] / MAX_QICK_GAIN)

    config = OutputPowerCalibrationConfig(
        database_path=str(database_path),
        output_board_type="RF_Out",
        frequency_start_mhz=400.0,
        frequency_end_mhz=420.0,
        frequency_points=2,
        gain_start=1000,
        gain_end=10_000,
        gain_points=2,
        oscilloscope=OscilloscopeConfig(visa_resource="MOCK"),
    )
    stored = run_output_power_calibration(
        connection_config=QickConnectionConfig(host="127.0.0.1"),
        calibration_config=config,
        connector=lambda **_kwargs: (_FakeSoc(), object()),
        power_meter_factory=lambda _config: Meter(),
        tone_runner=tone_runner,
    )

    assert stored.row_count == 3
    assert stored.result["valid_point_count"] == 3
    assert stored.result["excluded_point_count"] == 1
    assert stored.result["powers_dbm"][1][1] is None
    assert "1e+30" in stored.result["excluded_points"][0]["reason"]

    loaded = CalibrationDatabase(database_path).output_calibration(
        "RF_Out",
        [400.0, 420.0],
    )
    assert loaded.summary.row_count == 3
    assert np.all(
        np.isfinite(loaded.output_power_dbm([400.0, 420.0], [1000, 1000]))
    )

    app = _application()
    panel = CalibrationPanel()
    panel.show_result(stored)
    app.processEvents()
    assert "Excluded 1 invalid oscilloscope power point" in panel.status.text()
    panel.close()


def test_output_and_input_calibration_db_round_trip(tmp_path, monkeypatch):
    database_path, output_stored = _create_output_calibration(tmp_path, monkeypatch)
    frequencies = np.asarray([400.0, 410.0, 420.0])
    catalog = CalibrationDatabase(database_path)
    output_calibration = catalog.output_calibration("RF_Out", frequencies)
    strict_output_calibration = catalog.output_calibration(
        "RF_Out",
        frequencies,
        run_id=output_stored.run_id,
        nqz=1,
        output_filter_type="bypass",
        output_filter_cutoff_ghz=2.5,
        output_filter_bandwidth_ghz=1.0,
    )
    assert strict_output_calibration.summary.output_nqz == 1
    assert strict_output_calibration.summary.output_filter_type == "bypass"
    assert strict_output_calibration.summary.output_filter_cutoff_ghz == 2.5
    assert strict_output_calibration.summary.output_filter_bandwidth_ghz == 1.0
    np.testing.assert_allclose(
        output_calibration.output_power_dbm(frequencies, MAX_QICK_GAIN),
        [-10.0, -10.2, -10.4],
        atol=1.0e-9,
    )
    np.testing.assert_allclose(
        output_calibration.output_power_dbm([405.0, 415.0], MAX_QICK_GAIN),
        [-10.1, -10.3],
        atol=1.0e-9,
    )

    slopes_expected = np.asarray([1.0, 1.1, 1.2])
    intercepts_expected = np.asarray([-60.0, -61.0, -62.0])
    acquisition_events = []
    progress_events = []

    class Program:
        def __init__(self, config):
            self.sweep = config
            self.frequencies_mhz = frequencies.copy()

        def acquire_fir_ddr(
            self,
            _soc,
            *,
            counter_progress=None,
            cancel_check=None,
        ):
            acquisition_events.append(("arm", int(self.sweep.gain)))
            if cancel_check is not None:
                cancel_check()
            if counter_progress is not None:
                for completed in range(frequencies.size + 1):
                    counter_progress(completed, frequencies.size)
            actual_output = output_calibration.output_power_dbm(
                frequencies,
                self.sweep.gain,
            )
            known_input = actual_output - 3.0
            adc_db = (known_input - intercepts_expected) / slopes_expected
            amplitude = np.power(10.0, adc_db / 20.0)
            iq = np.zeros((frequencies.size, 4, 2), dtype=float)
            iq[:, :, 0] = amplitude[:, np.newaxis]
            return SParameterSweepResult.from_iq(
                frequencies,
                frequencies,
                iq,
            )

    def program_factory(_soccfg, config, **_kwargs):
        acquisition_events.append(("build", int(config.gain)))
        return Program(config)

    input_config = InputPowerCalibrationConfig(
        database_path=str(database_path),
        output_board_type="RF_Out",
        input_board_type="RF_In",
        frequency_start_mhz=400.0,
        frequency_end_mhz=420.0,
        frequency_points=3,
        gain_start=1000,
        gain_end=10000,
        gain_points=3,
        path_loss_db=3.0,
        scan_time_us=1_000_000.0,
        settle_seconds=0.0,
    )
    input_stored = run_input_power_calibration(
        connection_config=QickConnectionConfig(host="127.0.0.1"),
        calibration_config=input_config,
        connector=lambda **_kwargs: (_FakeSoc(), object()),
        program_factory=program_factory,
        progress_callback=lambda percent, message: progress_events.append(
            (percent, message)
        ),
    )
    assert acquisition_events == [
        ("build", 1000),
        ("arm", 1000),
        ("build", 5500),
        ("arm", 5500),
        ("build", 10000),
        ("arm", 10000),
    ]
    assert any(
        "Arming FIR DDR" in message and "1000000 us" in message
        for _percent, message in progress_events
    )
    assert any(
        "FIR point 1/3" in message for _percent, message in progress_events
    )
    assert any(
        "acquisition complete; reading FIR DDR" in message
        for _percent, message in progress_events
    )
    assert [percent for percent, _message in progress_events] == sorted(
        percent for percent, _message in progress_events
    )
    assert input_stored.run_id > output_stored.run_id
    input_calibration = CalibrationDatabase(database_path).input_calibration(
        "RF_In",
        frequencies,
    )
    slopes, intercepts = input_calibration.coefficients(frequencies)
    np.testing.assert_allclose(slopes, slopes_expected, rtol=0.0, atol=1.0e-10)
    np.testing.assert_allclose(
        intercepts,
        intercepts_expected,
        rtol=0.0,
        atol=1.0e-9,
    )
    assert input_calibration.summary.source_output_run_id == output_stored.run_id
    assert input_calibration.summary.path_loss_db == 3.0

    gains = np.asarray([5000, 6000, 7000])
    desired_adc_db = np.asarray([20.0, 21.0, 22.0])
    iq = np.zeros((3, 2, 2), dtype=float)
    iq[:, :, 0] = np.power(10.0, desired_adc_db / 20.0)[:, np.newaxis]
    raw_result = SParameterSweepResult.from_iq(
        frequencies,
        frequencies,
        iq,
        output_power_dbm=-20.0,
        nominal_gain_code=7000,
        frequency_gain_codes=gains,
    )
    calibrated = apply_power_calibration(
        raw_result,
        output_calibration=output_calibration,
        input_calibration=input_calibration,
        output_att1_db=0.0,
        output_att2_db=0.0,
        input_attenuation_db=0.0,
    )
    expected_input = slopes_expected * desired_adc_db + intercepts_expected
    expected_output = output_calibration.output_power_dbm(frequencies, gains)
    assert calibrated.physical_power_calibrated
    np.testing.assert_allclose(calibrated.adc_magnitude_db, desired_adc_db)
    np.testing.assert_allclose(calibrated.input_powers_dbm, expected_input)
    np.testing.assert_allclose(calibrated.actual_output_powers_dbm, expected_output)
    np.testing.assert_allclose(
        calibrated.magnitude_db,
        expected_input - expected_output,
    )

    deembedded = apply_power_calibration(
        raw_result,
        output_calibration=output_calibration,
        input_calibration=input_calibration,
        output_att1_db=0.0,
        output_att2_db=0.0,
        input_attenuation_db=0.0,
        loss1_db=2.0,
        loss2_db=3.0,
        amplifier_gain_db=10.0,
    )
    np.testing.assert_allclose(
        deembedded.dut_input_powers_dbm,
        expected_output - 2.0,
    )
    np.testing.assert_allclose(
        deembedded.dut_output_powers_dbm,
        expected_input + 3.0 - 10.0,
    )
    np.testing.assert_allclose(
        deembedded.magnitude_db,
        expected_input - expected_output - 5.0,
    )


def test_input_calibration_uses_one_avg_capture_per_gain(tmp_path, monkeypatch):
    database_path, output_stored = _create_output_calibration(tmp_path, monkeypatch)
    frequencies = np.asarray([400.0, 410.0, 420.0])
    output_calibration = CalibrationDatabase(database_path).output_calibration(
        "RF_Out",
        frequencies,
    )
    acquisition_events = []
    progress_events = []

    class Program:
        def __init__(self, config):
            self.sweep = config
            self.frequencies_mhz = frequencies.copy()

        def acquire_avg_buffer(
            self,
            _soc,
            *,
            counter_progress=None,
            cancel_check=None,
        ):
            acquisition_events.append(("avg", int(self.sweep.gain)))
            if cancel_check is not None:
                cancel_check()
            if counter_progress is not None:
                counter_progress(0, frequencies.size)
                counter_progress(frequencies.size, frequencies.size)
            known_input = output_calibration.output_power_dbm(
                frequencies,
                self.sweep.gain,
            )
            adc_db = known_input + 50.0
            amplitude = np.power(10.0, adc_db / 20.0)
            iq = np.zeros((frequencies.size, 1, 2), dtype=float)
            iq[:, 0, 0] = amplitude
            return SParameterSweepResult.from_iq(
                frequencies,
                frequencies,
                iq,
                acquisition_source="avg_buffer",
                integration_time_us=125.0,
                accumulation_repetitions=1,
            )

    def program_factory(_soccfg, config, **_kwargs):
        acquisition_events.append(("build", int(config.gain)))
        assert config.acquisition_source == "avg_buffer"
        assert config.avg_repetitions == 1
        return Program(config)

    config = InputPowerCalibrationConfig(
        database_path=str(database_path),
        output_board_type="RF_Out",
        input_board_type="RF_In",
        frequency_start_mhz=400.0,
        frequency_end_mhz=420.0,
        frequency_points=3,
        gain_start=1000,
        gain_end=10_000,
        gain_points=2,
        acquisition_source="avg_buffer",
        scan_time_us=123.0,
        settle_seconds=0.0,
    )
    stored = run_input_power_calibration(
        connection_config=QickConnectionConfig(host="127.0.0.1"),
        calibration_config=config,
        connector=lambda **_kwargs: (_FakeSoc(), object()),
        program_factory=program_factory,
        progress_callback=lambda percent, message: progress_events.append(
            (percent, message)
        ),
    )

    assert acquisition_events == [
        ("build", 1000),
        ("avg", 1000),
        ("build", 10_000),
        ("avg", 10_000),
    ]
    assert stored.run_id > output_stored.run_id
    assert stored.result["acquisition_source"] == "avg_buffer"
    assert stored.result["acquisition_details"] == {
        "source": "avg_buffer",
        "requested_integration_time_us": 123.0,
        "actual_integration_time_us": 125.0,
        "accumulation_repetitions": 1,
    }
    assert any(
        "Starting AVG buffer" in message
        for _percent, message in progress_events
    )
    assert any(
        "AVG buffer acquisition complete" in message
        for _percent, message in progress_events
    )
