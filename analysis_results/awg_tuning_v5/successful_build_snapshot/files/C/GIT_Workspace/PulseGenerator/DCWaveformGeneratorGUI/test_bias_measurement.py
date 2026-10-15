"""Tests for Bias sweep generation, current readers, and QCoDeS storage.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt5 import QtWidgets
import pytest

from bias_measurement import (
    BiasMeasurementCancelled,
    BiasMeasurementLiveLayout,
    BiasMeasurementLivePoint,
    CurrentReading,
    SR860_QUERY_PAUSE_S,
    SR860_RECONNECT_PAUSE_S,
    Sr860CurrentReader,
    default_bias_measurement_settings,
    make_gate_sweep,
    normalize_bias_measurement_settings,
    ramp_bias_channel,
    ramp_bias_channels,
    run_bias_measurement,
    validate_bias_sweep_voltage_limit,
)
from bias_measurement_gui import BiasMeasurementTabs
from qick_qcodes_experiment import QickConnectionConfig


def _application():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class FakeSoc:
    def __init__(self):
        self.values = {channel: 0.01 * channel for channel in range(8)}

    def rfb_get_bias(self, channel):
        return self.values[int(channel)]

    def rfb_set_bias(self, channel, voltage):
        self.values[int(channel)] = float(voltage)
        return float(voltage)


class FakeAdcReader:
    def __init__(self, soc, _soccfg, _connection, _settings, **_kwargs):
        self.soc = soc
        self.closed = False

    def read(self):
        value = float(self.soc.values[2])
        return CurrentReading(value, -value, abs(value) * np.sqrt(2.0), -45.0)

    def close(self, **_kwargs):
        self.closed = True


class FakeSr860Reference:
    def __init__(self):
        self.reference_source = "external"
        self.frequency = 1.0
        self.phase = 0.0
        self.sine_out_amplitude = 0.0


class FakeSr860Signal:
    def __init__(self):
        self.input_mode = "voltage"
        self.current_input_gain = 1e6
        self.current_sensitivity = 1e-9
        self.filter_slope = 6
        self.time_constant = 1e-3


class FakeSr860Data:
    def __init__(self, instrument):
        self.instrument = instrument

    def get_values(self, *names):
        if self.instrument.always_fail or self.instrument.fail_read:
            self.instrument.fail_read = False
            raise FakeVisaIOError("temporary timeout")
        if not 2 <= len(names) <= 3:
            raise KeyError(
                "It is only possible to request values of 2 or 3 parameters "
                "at a time."
            )
        current = float(self.instrument.ref.sine_out_amplitude) * 2.0
        values = {
            "X": current,
            "Y": 0.0,
            "R": abs(current),
            "Theta": 0.0,
        }
        self.instrument.value_requests.append(tuple(names))
        return tuple(values[name] for name in names)


class FakeSr860:
    last = None

    def __init__(self, interface_type, address):
        FakeSr860.last = self
        self.interface_type = interface_type
        self.address = address
        self.ref = FakeSr860Reference()
        self.signal = FakeSr860Signal()
        self.data = FakeSr860Data(self)
        self.closed = False
        self.value_requests = []
        self.fail_read = False
        self.always_fail = False

    def disconnect(self):
        self.closed = True


FakeVisaIOError = type(
    "VisaIOError",
    (Exception,),
    {"__module__": "pyvisa.errors"},
)


def test_nested_gate_sweep_and_ramp_are_bounded():
    values = make_gate_sweep(
        0.0,
        -0.6,
        4,
        2,
        return_leg=True,
        largest_loop_first=False,
    )
    assert values.tolist() == pytest.approx(
        [0.0, -0.1, -0.2, -0.3, -0.2, -0.1, 0.0,
         0.0, -0.2, -0.4, -0.6, -0.4, -0.2, 0.0]
    )

    soc = FakeSoc()
    writes = []
    original = soc.rfb_set_bias

    def record(channel, voltage):
        writes.append(float(voltage))
        return original(channel, voltage)

    soc.rfb_set_bias = record
    ramp_bias_channel(
        soc,
        0,
        0.025,
        max_step_v=0.01,
        pause_s=0.0,
        voltage_limit_v=0.1,
        sleeper=lambda _seconds: None,
    )
    assert writes == pytest.approx([0.0083333333, 0.0166666667, 0.025])
    assert max(np.diff([0.0, *writes])) <= 0.01


def test_vector_ramp_moves_channels_on_one_shared_fraction():
    soc = FakeSoc()
    soc.values[0] = 0.0
    soc.values[1] = 0.0
    writes = []
    pauses = []
    original = soc.rfb_set_bias

    def record(channel, voltage):
        writes.append((int(channel), float(voltage)))
        return original(channel, voltage)

    soc.rfb_set_bias = record
    result = ramp_bias_channels(
        soc,
        {0: 0.02, 1: -0.03},
        max_step_v=0.01,
        pause_s=0.001,
        voltage_limit_v=0.1,
        sleeper=pauses.append,
    )

    np.testing.assert_allclose(
        np.asarray(writes, dtype=float),
        np.asarray([
            (0, 0.02 / 3), (1, -0.01),
            (0, 0.04 / 3), (1, -0.02),
            (0, 0.02), (1, -0.03),
        ]),
    )
    assert pauses == pytest.approx([0.001, 0.001, 0.001])
    assert result == pytest.approx({0: 0.02, 1: -0.03})


def test_ramp_never_writes_when_target_or_current_voltage_exceeds_limit():
    soc = FakeSoc()
    writes = []
    original = soc.rfb_set_bias

    def record(channel, voltage):
        writes.append((int(channel), float(voltage)))
        return original(channel, voltage)

    soc.rfb_set_bias = record
    with pytest.raises(ValueError, match="target.*exceeds"):
        ramp_bias_channels(
            soc,
            {0: 0.11},
            max_step_v=0.01,
            pause_s=0.0,
            voltage_limit_v=0.1,
            sleeper=lambda _seconds: None,
        )
    assert writes == []

    soc.values[0] = 0.11
    with pytest.raises(ValueError, match="current voltage.*outside"):
        ramp_bias_channels(
            soc,
            {0: 0.0},
            max_step_v=0.01,
            pause_s=0.0,
            voltage_limit_v=0.1,
            sleeper=lambda _seconds: None,
        )
    assert writes == []


@pytest.mark.parametrize("kind", ["gate", "wall_wall", "nested"])
def test_every_bias_sweep_type_preflights_all_endpoints(kind):
    settings = default_bias_measurement_settings()[kind]
    if kind == "gate":
        settings["gate_stop_v"] = 0.51
    elif kind == "wall_wall":
        settings["fast_stop_v"] = -0.51
    else:
        settings["axes"][1]["stop_v"][1] = 0.51
    normalized = normalize_bias_measurement_settings({kind: settings})[kind]
    with pytest.raises(ValueError, match="exceeds the configured"):
        validate_bias_sweep_voltage_limit(kind, normalized, 0.5)


def test_out_of_limit_nested_sweep_fails_before_qick_connection(tmp_path):
    settings = default_bias_measurement_settings()["nested"]
    settings["database_path"] = str(tmp_path / "must_not_exist.db")
    settings["axes"][1]["stop_v"][0] = 0.2
    connected = []

    def connector(**_kwargs):
        connected.append(True)
        return FakeSoc(), {}

    with pytest.raises(ValueError, match="exceeds the configured"):
        run_bias_measurement(
            connection_config=QickConnectionConfig(
                "127.0.0.1", 8888, "myqick"
            ),
            kind="nested",
            settings=settings,
            channel_names=("",) * 8,
            voltage_limit_v=0.1,
            connector=connector,
            adc_reader_factory=FakeAdcReader,
            sleeper=lambda _seconds: None,
        )
    assert connected == []
    assert not (tmp_path / "must_not_exist.db").exists()


def test_bias_measurement_settings_round_trip_and_legacy_defaults():
    defaults = default_bias_measurement_settings()
    normalized = normalize_bias_measurement_settings({})
    assert normalized == defaults
    assert normalized["two_point"]["sr860"]["filter_slope_db_oct"] == 24
    assert normalized["wall_wall"]["fast_channel"] == 1
    assert normalized["nested"]["axes"][1]["channels"] == [0, 1]
    assert normalized["time_trace"]["samples"] == 1_000
    assert normalized["time_trace"]["sample_interval_s"] == pytest.approx(0.1)

    app = _application()
    tabs = BiasMeasurementTabs()
    tabs.set_channel_names(["P", "BL", "BR", "S0", "AccL", "AccR", "", ""])
    tabs.load_settings(defaults)
    app.processEvents()
    persisted = tabs.settings_dict()
    assert persisted == defaults
    assert tabs.pages["gate"].gate_channel_checks[1].text() == "BL"
    assert tabs.pages["gate"].gate_channel_checks[1].toolTip() == "BIAS1 | BL"
    assert "P (BIAS0)" in (
        tabs.pages["nested"].nested_axis_editors[1].channel_summary.text()
    )
    tabs.close()


def test_two_point_current_mode_hides_inactive_instrument_settings():
    app = _application()
    tabs = BiasMeasurementTabs()
    page = tabs.pages["two_point"]
    page.show()

    page.current.mode.setCurrentIndex(
        page.current.mode.findData("qick_adc")
    )
    app.processEvents()
    assert page.current.adc_group.isHidden() is False
    assert page.current.sr_group.isHidden() is True

    page.current.mode.setCurrentIndex(
        page.current.mode.findData("sr860")
    )
    app.processEvents()
    assert page.current.adc_group.isHidden() is True
    assert page.current.sr_group.isHidden() is False
    tabs.close()


def test_legacy_single_gate_channel_migrates_to_checked_channel_list():
    normalized = normalize_bias_measurement_settings({
        "gate": {
            "gate_channel": 3,
            "restore_bias_after_run": True,
        }
    })
    assert normalized["gate"]["gate_channels"] == [3]
    assert "gate_channel" not in normalized["gate"]
    assert normalized["gate"]["restore_bias_after_run"] is False

    app = _application()
    tabs = BiasMeasurementTabs()
    tabs.set_channel_names(["P", "BL", "BR", "S0", "AccL", "AccR", "", ""])
    tabs.load_settings({"gate": {"gate_channel": 3}})
    app.processEvents()
    checked = [
        index
        for index, checkbox in enumerate(tabs.pages["gate"].gate_channel_checks)
        if checkbox.isChecked()
    ]
    assert checked == [3]
    tabs.close()


def test_bias_live_plot_accumulates_repetitions_and_2d_cells():
    app = _application()
    tabs = BiasMeasurementTabs()
    page = tabs.pages["wall_wall"]
    layout = BiasMeasurementLiveLayout(
        kind="wall_wall",
        x_values=np.asarray([-0.1, 0.0, 0.1]),
        x_label="Fast voltage [V]",
        data_shape=(2, 3),
        y_values=np.asarray([0.0, 0.2]),
        y_label="Slow voltage [V]",
    )
    tabs.begin_live_plot(layout)
    tabs.update_live_point(BiasMeasurementLivePoint(
        kind="wall_wall",
        plot_index=(0, 1),
        repetition_index=0,
        magnitude_a=2.0e-9,
        completed_reads=1,
        total_reads=12,
    ))
    tabs.update_live_point(BiasMeasurementLivePoint(
        kind="wall_wall",
        plot_index=(0, 1),
        repetition_index=1,
        magnitude_a=4.0e-9,
        completed_reads=2,
        total_reads=12,
    ))
    page._flush_live_plot()
    app.processEvents()

    assert page._live_values[0, 1] == pytest.approx(3.0e-9)
    assert page._live_count[0, 1] == 2
    assert np.isnan(page._live_values[1, 2])
    assert page._live_completed_reads == 2
    assert page._live_total_reads == 12
    assert page._live_timer.isActive() is True

    tabs.set_running("wall_wall", False, "Stopped")
    assert page._live_timer.isActive() is False
    tabs.close()


def test_bias_measurement_stop_button_emits_active_kind():
    app = _application()
    tabs = BiasMeasurementTabs()
    stops = []
    tabs.stop_requested.connect(stops.append)

    tabs.set_running("gate", True, "Running")
    page = tabs.pages["gate"]
    assert page.run_button.isEnabled() is False
    assert page.stop_button.isEnabled() is True
    page.stop_button.click()
    app.processEvents()

    assert stops == ["gate"]
    tabs.set_stopping("gate", "Stopping")
    assert page.stop_button.isEnabled() is False
    tabs.set_running("gate", False, "Stopped")
    assert page.run_button.isEnabled() is True
    tabs.close()


def test_sr860_reader_reconnects_and_pauses_between_snap_queries():
    settings = default_bias_measurement_settings()["two_point"]["sr860"]
    settings = dict(settings)
    settings["settle_time_constants"] = 0.0
    instruments = []
    sleeps = []
    retries = []

    class FlakySr860(FakeSr860):
        def __init__(self, interface_type, address, *, fail_read):
            super().__init__(interface_type, address)
            self.fail_read = fail_read

    def factory(interface_type, address):
        instrument = FlakySr860(
            interface_type,
            address,
            fail_read=not instruments,
        )
        instruments.append(instrument)
        return instrument

    reader = Sr860CurrentReader(
        settings,
        instrument_factory=factory,
        sleeper=sleeps.append,
        retry_callback=lambda attempt, exc: retries.append((attempt, str(exc))),
    )
    reader.set_bias(0.125)
    reading = reader.read()

    assert len(instruments) == 2
    assert instruments[0].closed is True
    assert {item.interface_type for item in instruments} == {"visa"}
    assert instruments[1].ref.sine_out_amplitude == pytest.approx(0.125)
    assert instruments[1].value_requests == [
        ("X", "Y"),
        ("R", "Theta"),
    ]
    assert sleeps == pytest.approx([
        SR860_RECONNECT_PAUSE_S,
        SR860_QUERY_PAUSE_S,
    ])
    assert retries == [(1, "temporary timeout")]
    assert reading.r_a == pytest.approx(0.25)
    reader.close()
    assert instruments[1].closed is True


def test_sr860_reconnect_wait_can_be_cancelled():
    settings = default_bias_measurement_settings()["two_point"]["sr860"]
    settings = dict(settings)
    settings["settle_time_constants"] = 0.0
    cancelled = False

    class AlwaysFailSr860(FakeSr860):
        def __init__(self, interface_type, address):
            super().__init__(interface_type, address)
            self.always_fail = True

    def cancel_check():
        if cancelled:
            raise BiasMeasurementCancelled("stop")

    def sleeper(_seconds):
        nonlocal cancelled
        cancelled = True

    reader = Sr860CurrentReader(
        settings,
        instrument_factory=AlwaysFailSr860,
        sleeper=sleeper,
        cancel_check=cancel_check,
    )
    with pytest.raises(BiasMeasurementCancelled, match="stop"):
        reader.read()
    reader.close()


def test_nested_settings_reject_reused_channels_and_bad_vectors():
    settings = default_bias_measurement_settings()["nested"]
    settings = json.loads(json.dumps(settings))
    settings["axes"][1]["channels"] = [2]
    settings["axes"][1]["start_v"] = [0.0]
    settings["axes"][1]["stop_v"] = [0.1]
    with pytest.raises(ValueError, match="more than one nested axis"):
        normalize_bias_measurement_settings({"nested": settings})

    settings = default_bias_measurement_settings()["nested"]
    settings = json.loads(json.dumps(settings))
    settings["axes"][1]["stop_v"] = [0.1]
    with pytest.raises(ValueError, match="must contain 2 voltage values"):
        normalize_bias_measurement_settings({"nested": settings})


def test_nested_axis_gui_add_remove_and_reorder():
    app = _application()
    tabs = BiasMeasurementTabs()
    page = tabs.pages["nested"]
    page._add_nested_axis({
        "name": "third",
        "channels": [3],
        "start_v": [-0.2],
        "stop_v": [0.2],
        "points": 5,
    })
    app.processEvents()
    assert [axis["name"] for axis in page.settings_dict()["axes"]] == [
        "outer", "inner_vector", "third",
    ]

    third = page.nested_axis_editors[2]
    page._move_nested_axis(third, -1)
    assert [axis["name"] for axis in page.settings_dict()["axes"]] == [
        "outer", "third", "inner_vector",
    ]
    page._remove_nested_axis(third)
    app.processEvents()
    assert [axis["name"] for axis in page.settings_dict()["axes"]] == [
        "outer", "inner_vector",
    ]
    tabs.close()


def test_nested_axis_adds_independent_sweep_channel_rows():
    app = _application()
    tabs = BiasMeasurementTabs()
    tabs.set_channel_names(["P", "BL", "BR", "S0", "AccL", "AccR", "", ""])
    page = tabs.pages["nested"]
    axis = page.nested_axis_editors[0]
    assert len(axis.channel_rows) == 1

    axis.add_channel_button.click()
    app.processEvents()
    assert len(axis.channel_rows) == 2
    added = axis.channel_rows[1]
    added.channel.setCurrentIndex(added.channel.findData(4))
    added.start_v.setValue(-0.25)
    added.stop_v.setValue(0.35)
    first = axis.channel_rows[0]
    first.start_v.setValue(-0.1)
    first.stop_v.setValue(0.2)
    app.processEvents()

    settings = axis.settings_dict()
    assert settings["channels"] == [2, 4]
    assert settings["start_v"] == pytest.approx([-0.1, -0.25])
    assert settings["stop_v"] == pytest.approx([0.2, 0.35])
    assert added.channel.currentText() == "AccL (BIAS4)"
    assert "AccL (BIAS4)" in axis.channel_summary.text()

    added.remove_button.click()
    app.processEvents()
    assert len(axis.channel_rows) == 1
    assert axis.channel_rows[0].remove_button.isEnabled() is False
    tabs.close()


def test_gate_qick_adc_measurement_saves_bias_metadata(tmp_path):
    database = tmp_path / "bias_measurement.db"
    settings = default_bias_measurement_settings()["gate"]
    settings.update({
        "database_path": str(database),
        "sample_name": "GateTest",
        "current_mode": "qick_adc",
        "gate_channels": [1, 2],
        "gate_start_v": -0.1,
        "gate_stop_v": 0.1,
        "points_per_leg": 3,
        "loops": 1,
        "return_leg": False,
        "repetitions_per_point": 2,
        "settle_s": 0.0,
        "ramp_max_step_v": 1.0,
        "ramp_pause_s": 0.0,
    })
    soc = FakeSoc()
    initial = dict(soc.values)
    live_layouts = []
    live_points = []

    result = run_bias_measurement(
        connection_config=QickConnectionConfig("127.0.0.1", 8888, "myqick"),
        kind="gate",
        settings=settings,
        channel_names=("P", "BL", "BR", "S0", "AccL", "AccR", "", ""),
        voltage_limit_v=1.0,
        connector=lambda **_kwargs: (soc, {}),
        adc_reader_factory=FakeAdcReader,
        sleeper=lambda _seconds: None,
        live_layout_callback=live_layouts.append,
        live_point_callback=live_points.append,
    )

    assert result.run_id >= 1
    assert result.x_values.tolist() == pytest.approx([-0.1, 0.0, 0.1])
    assert result.magnitude_a.shape == (3,)
    assert len(live_layouts) == 1
    assert live_layouts[0].data_shape == (3,)
    assert live_layouts[0].x_values.tolist() == pytest.approx(
        [-0.1, 0.0, 0.1]
    )
    assert [point.plot_index for point in live_points] == [
        (0,), (0,), (1,), (1,), (2,), (2,),
    ]
    assert live_points[-1].completed_reads == 6
    assert live_points[-1].total_reads == 6
    assert soc.values[1] == pytest.approx(0.1)
    assert soc.values[2] == pytest.approx(0.1)
    for channel in set(initial) - {1, 2}:
        assert soc.values[channel] == pytest.approx(initial[channel])

    from qcodes import initialise_or_create_database_at, load_by_id

    initialise_or_create_database_at(str(database))
    dataset = load_by_id(result.run_id)
    initial_metadata = json.loads(
        dataset.get_metadata("bias_channel_voltages_initial_json")
    )
    final_metadata = json.loads(
        dataset.get_metadata("bias_channel_voltages_final_json")
    )
    assert len(initial_metadata["channels"]) == 8
    assert initial_metadata["channels"][2]["name"] == "BR"
    assert final_metadata["channels"][1]["voltage_v"] == pytest.approx(0.1)
    assert final_metadata["channels"][2]["voltage_v"] == pytest.approx(0.1)
    swept_metadata = json.loads(
        dataset.get_metadata("swept_bias_channels_json")
    )
    assert swept_metadata == [
        {"channel": 1, "hardware_name": "BIAS1", "name": "BL"},
        {"channel": 2, "hardware_name": "BIAS2", "name": "BR"},
    ]
    run_metadata = json.loads(dataset.get_metadata("bias_measurement_json"))
    assert run_metadata["configuration"]["gate_channels"] == [1, 2]
    assert run_metadata["swept_bias_channels"] == swept_metadata
    adc_metadata = json.loads(dataset.get_metadata("qick_adc_settings_json"))
    assert adc_metadata["readout_ch"] == settings["qick_adc"]["readout_ch"]
    assert adc_metadata["fir_samples"] == settings["qick_adc"]["fir_samples"]
    # QCoDeS counts the six dependent values written for each of six reads.
    assert dataset.number_of_results == 36


def test_time_trace_saves_actual_elapsed_time_and_bias_voltage_metadata(tmp_path):
    database = tmp_path / "bias_time_trace.db"
    settings = default_bias_measurement_settings()["time_trace"]
    settings.update({
        "database_path": str(database),
        "sample_name": "TimeTraceTest",
        "current_mode": "qick_adc",
        "samples": 4,
        "sample_interval_s": 0.25,
    })
    soc = FakeSoc()
    initial = dict(soc.values)
    now = [10.0]

    def clock():
        return now[0]

    def sleeper(duration_s):
        now[0] += float(duration_s)

    live_points = []
    result = run_bias_measurement(
        connection_config=QickConnectionConfig("127.0.0.1", 8888, "myqick"),
        kind="time_trace",
        settings=settings,
        channel_names=("P", "BL", "BR", "S0", "AccL", "AccR", "", ""),
        voltage_limit_v=1.0,
        connector=lambda **_kwargs: (soc, {}),
        adc_reader_factory=FakeAdcReader,
        sleeper=sleeper,
        clock=clock,
        live_point_callback=live_points.append,
    )

    assert result.x_values.tolist() == pytest.approx([0.0, 0.25, 0.5, 0.75])
    assert result.x_label == "Elapsed time [s]"
    assert result.magnitude_a.tolist() == pytest.approx(
        [np.hypot(0.02, -0.02)] * 4
    )
    assert [point.plot_index for point in live_points] == [
        (0,), (1,), (2,), (3,),
    ]
    assert soc.values == pytest.approx(initial)

    from qcodes import initialise_or_create_database_at, load_by_id

    initialise_or_create_database_at(str(database))
    dataset = load_by_id(result.run_id)
    parameter_data = dataset.get_parameter_data("i_r_a")["i_r_a"]
    assert parameter_data["sample_index"].tolist() == [0, 1, 2, 3]
    assert parameter_data["elapsed_time_s"].tolist() == pytest.approx(
        [0.0, 0.25, 0.5, 0.75]
    )
    voltage_metadata = json.loads(
        dataset.get_metadata("bias_voltage_metadata_json")
    )
    assert len(voltage_metadata["channels"]) == 8
    assert voltage_metadata["channels"][0] == {
        "channel": 0,
        "name": "P",
        "voltage_v": 0.0,
    }
    final_metadata = json.loads(
        dataset.get_metadata("bias_channel_voltages_final_json")
    )
    assert [item["voltage_v"] for item in final_metadata["channels"]] == pytest.approx(
        [initial[channel] for channel in range(8)]
    )
    assert dataset.number_of_results == 24


def test_wall_wall_result_shape_with_qick_adc(tmp_path):
    settings = default_bias_measurement_settings()["wall_wall"]
    settings.update({
        "database_path": str(tmp_path / "wall.db"),
        "sample_name": "WallTest",
        "current_mode": "qick_adc",
        "slow_channel": 1,
        "fast_channel": 2,
        "slow_start_v": 0.0,
        "slow_stop_v": 0.1,
        "slow_points": 2,
        "fast_start_v": -0.1,
        "fast_stop_v": 0.1,
        "fast_points": 3,
        "repetitions_per_point": 1,
        "settle_s": 0.0,
        "ramp_max_step_v": 1.0,
        "ramp_pause_s": 0.0,
    })
    soc = FakeSoc()
    live_points = []
    result = run_bias_measurement(
        connection_config=QickConnectionConfig("127.0.0.1", 8888, "myqick"),
        kind="wall_wall",
        settings=settings,
        channel_names=("",) * 8,
        voltage_limit_v=1.0,
        connector=lambda **_kwargs: (soc, {}),
        adc_reader_factory=FakeAdcReader,
        sleeper=lambda _seconds: None,
        live_point_callback=live_points.append,
    )
    assert result.magnitude_a.shape == (2, 3)
    assert result.x_values.tolist() == pytest.approx([-0.1, 0.0, 0.1])
    assert result.y_values.tolist() == pytest.approx([0.0, 0.1])
    assert [point.plot_index for point in live_points] == [
        (0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2),
    ]


def test_general_nested_vector_sweep_saves_all_axis_setpoints(tmp_path):
    database = tmp_path / "nested.db"
    settings = default_bias_measurement_settings()["nested"]
    settings.update({
        "database_path": str(database),
        "sample_name": "NestedTest",
        "current_mode": "qick_adc",
        "axes": [
            {
                "name": "outer_gate",
                "channels": [2],
                "start_v": [0.0],
                "stop_v": [0.2],
                "points": 2,
            },
            {
                "name": "paired_inner",
                "channels": [0, 1],
                "start_v": [-0.1, 0.1],
                "stop_v": [0.1, -0.1],
                "points": 3,
            },
        ],
        "repetitions_per_point": 2,
        "settle_s": 0.0,
        "ramp_max_step_v": 1.0,
        "ramp_pause_s": 0.0,
    })
    soc = FakeSoc()
    initial = dict(soc.values)
    result = run_bias_measurement(
        connection_config=QickConnectionConfig("127.0.0.1", 8888, "myqick"),
        kind="nested",
        settings=settings,
        channel_names=("P", "BL", "BR", "S0", "", "", "", ""),
        voltage_limit_v=1.0,
        connector=lambda **_kwargs: (soc, {}),
        adc_reader_factory=FakeAdcReader,
        sleeper=lambda _seconds: None,
    )

    assert result.magnitude_a.shape == (2, 3)
    assert result.x_values.tolist() == pytest.approx([0.0, 1.0, 2.0])
    assert result.y_values.tolist() == pytest.approx([0.0, 0.2])
    assert soc.values == pytest.approx(initial)

    from qcodes import initialise_or_create_database_at, load_by_id

    initialise_or_create_database_at(str(database))
    dataset = load_by_id(result.run_id)
    assert dataset.number_of_results == 72
    parameter_data = dataset.get_parameter_data("i_r_a")["i_r_a"]
    assert set(parameter_data) >= {
        "nested_axis_0_index",
        "nested_axis_0_bias2_voltage_v",
        "nested_axis_1_index",
        "nested_axis_1_bias0_voltage_v",
        "nested_axis_1_bias1_voltage_v",
        "repetition_index",
        "i_r_a",
    }
    assert np.unique(
        parameter_data["nested_axis_1_bias0_voltage_v"]
    ).tolist() == pytest.approx([-0.1, 0.0, 0.1])
    metadata = json.loads(dataset.get_metadata("bias_measurement_json"))
    assert metadata["configuration"]["axes"][1]["channels"] == [0, 1]


def test_two_point_sr860_sweeps_bias_and_saves_settings(tmp_path):
    settings = default_bias_measurement_settings()["two_point"]
    settings.update({
        "database_path": str(tmp_path / "two_point.db"),
        "sample_name": "TwoPointTest",
        "bias_start_v": 0.0,
        "bias_stop_v": 100e-6,
        "points": 3,
        "repetitions_per_point": 1,
    })
    settings["sr860"] = dict(settings["sr860"])
    settings["sr860"]["settle_time_constants"] = 0.0
    soc = FakeSoc()
    result = run_bias_measurement(
        connection_config=QickConnectionConfig("127.0.0.1", 8888, "myqick"),
        kind="two_point",
        settings=settings,
        channel_names=("",) * 8,
        voltage_limit_v=1.0,
        connector=lambda **_kwargs: (soc, {}),
        sr860_factory=FakeSr860,
        sleeper=lambda _seconds: None,
    )
    assert result.x_values.tolist() == pytest.approx([0.0, 50e-6, 100e-6])
    assert result.magnitude_a.tolist() == pytest.approx([0.0, 100e-6, 200e-6])
    assert FakeSr860.last.interface_type == "visa"
    assert FakeSr860.last.ref.frequency == pytest.approx(43.5371)
    assert FakeSr860.last.signal.filter_slope == 24
    assert FakeSr860.last.ref.sine_out_amplitude == pytest.approx(0.0)
    assert FakeSr860.last.closed is True
    assert FakeSr860.last.value_requests == [
        ("X", "Y"),
        ("R", "Theta"),
    ] * 3

    from qcodes import initialise_or_create_database_at, load_by_id

    initialise_or_create_database_at(settings["database_path"])
    dataset = load_by_id(result.run_id)
    sr_metadata = json.loads(dataset.get_metadata("sr860_settings_json"))
    assert sr_metadata["time_constant_s"] == pytest.approx(0.1)
    assert sr_metadata["filter_slope_db_oct"] == 24
    assert sr_metadata["sensitivity_a"] == pytest.approx(100e-9)
