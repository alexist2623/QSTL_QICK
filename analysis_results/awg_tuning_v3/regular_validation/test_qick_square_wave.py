"""Full-scale DAC levels, infinite edge timing, and GUI start/stop lifecycle."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import replace
from threading import Event, Thread
from types import SimpleNamespace

import pytest
from PyQt5 import QtCore, QtTest, QtWidgets
from qick.sim.tproc_v1 import TProcV1Sim
from qick.qick_asm import QickConfig

import qick_square_wave as square


def soccfg():
    return QickConfig(dict(sw_version="0.2.357", refclk_freq=300.0,
        tprocs=[dict(type="axis_tproc64x32_x8", f_time=300.0, pmem_size=65536, dmem_size=4096)],
        gens=[dict(type="axis_awg_tuning_v1", gen_type="awg_tuning", tproc_ch=0,
            tmux_ch=0, f_fabric=300.0, n_pts=16, samps_per_clk=16, frac=16,
            cmd_width=160, step_width=24, duration_width=23, fixed_width=48,
            dac_invalid_lsb=2, maxv=32764, minv=-32768, has_mixer=False,
            has_dds=False, b_dds=32, b_phase=32, dac="00", interpolation=1)],
        readouts=[]))


def square_soccfg():
    cfg = soccfg()
    cfg['gens'][0].update(type='axis_square_pulse_v1', gen_type='square_pulse',
                          has_dds=True, f_dds=4800., command_latency_cycles=4)
    cfg['board'] = 'ZCU216'
    cfg['extra_description'] = ['DAC slot 0: DC Out card has ports [0, 1, 2, 3]']
    return cfg


@pytest.fixture
def square_config():
    return square.SquareWaveConfig(gen_ch=0)


def test_full_scale_and_integer_quantization(square_config):
    cfg = soccfg()
    assert square_config.full_scale_mv == square.DEFAULT_QICK_FULL_SCALE_MV == 800
    assert square_config.codes(cfg["gens"][0]) == (1528, 712)
    # A fractional multiplication is rounded to the actual DAC quantum.
    config = replace(square_config, full_scale_mv=750, offset_mv=0.17, zero_code=1121.3)
    high, low = config.codes(cfg["gens"][0])
    for code, voltage in zip((high, low), (10.17, -9.83)):
        assert type(code) is int and code % 4 == 0
        assert abs(code - (voltage / 750 * 32768 + 1121.3)) <= 2


@pytest.mark.parametrize("amplitude,expected", [(400, (16384, -16384)), (800, (32764, -32768))])
def test_zero_offset_matches_awg_tuning_full_scale(square_config, amplitude, expected):
    config = replace(square_config, amplitude_mv=amplitude, zero_code=0)
    assert config.codes(soccfg()["gens"][0]) == expected


def test_program_uses_selected_full_scale_without_calibration(square_config):
    for frequency in (40000, 12345):
        program = square.build_square_wave_program(soccfg(), replace(
            square_config, full_scale_mv=400, frequency_hz=frequency))
        assert program.summary["high_code"] == 1940
        assert program.summary["low_code"] == 300
        assert program.summary["full_scale_mv"] == 400
        assert "calibration" not in program.summary


def test_legacy_settings_drop_calibration_and_preserve_waveform():
    values = square.normalize_square_wave_settings(dict(
        calibration_database_path="missing.db", calibration_run_id=112,
        calibration_reference_ohm=50, codes_per_mv=80, frequency_hz=25000,
        amplitude_mv=12.5, offset_mv=1.5, zero_code=1104))
    assert values == dict(gen_ch=1, frequency_hz=25000, amplitude_mv=12.5,
                         offset_mv=1.5, duty_percent=50, zero_code=1104, full_scale_mv=800,
                         phase_deg=0., rc_enabled=False, rc_tau_us=1000.0)


@pytest.mark.parametrize("kwargs", [dict(amplitude_mv=1000), dict(amplitude_mv=1e-8),
    dict(amplitude_mv=790, offset_mv=20), dict(amplitude_mv=800),
    dict(zero_code=32768), dict(zero_code=-32768)])
def test_out_of_range_and_unresolvable_levels_are_rejected(kwargs, square_config):
    with pytest.raises(ValueError):
        square.build_square_wave_program(soccfg(), replace(square_config, **kwargs))


@pytest.mark.parametrize("kwargs", [dict(frequency_hz=0), dict(amplitude_mv=-1),
    dict(duty_percent=100), dict(full_scale_mv=0), dict(zero_code=float("nan")),
    dict(gen_ch=True), dict(full_scale_mv=None), dict(full_scale_mv=float("inf"))])
def test_invalid_inputs_are_rejected(kwargs):
    with pytest.raises(ValueError):
        square.SquareWaveConfig(**kwargs)


class ReferenceTimeInterpreter(TProcV1Sim):
    def _exec_waiti(self, port, imm):
        # The stock event interpreter conflates wall time and t_ref on WAIT.
        # RTL WAIT stalls execution but leaves t_ref unchanged; only SYNC
        # advances the reference used for the following SET timestamps.
        self.pc += 1

    def _exec_wait(self, page, port, reg):
        self.pc += 1


@pytest.mark.parametrize("frequency,duty", [(40000, 50), (12345, 37), (500000, 95)])
def test_compiled_infinite_loop_preserves_edges_without_readout(frequency, duty, square_config):
    config = replace(square_config, frequency_hz=frequency, duty_percent=duty)
    program = square.build_square_wave_program(soccfg(), config)
    model = ReferenceTimeInterpreter()
    with pytest.raises(RuntimeError, match="exceeded max_steps"):
        model.run(program, max_steps=20000)
    events = model.output_events
    assert len(events) > 100 and not model.ended
    assert not program.ro_chs
    period = round(300e6/frequency)
    high_ticks = round(period*duty/100)
    codes = [e.word & 0xffffffff for e in events]
    assert codes == [1528 if i % 2 == 0 else 712 for i in range(len(events))]
    for i in range(len(events)-1):
        assert events[i+1].cycle-events[i].cycle == (high_ticks if i % 2 == 0 else period-high_ticks)
    assert all(e.tproc_ch == 0 for e in events)
    waits = [i for i in program.prog_list if i["name"] == "waiti"]
    assert waits[0]["args"][0] != 0
    assert program.summary["actual_frequency_hz"] == 300e6/period
    assert program.binprog


def test_clock_override_and_firmware_validation(square_config):
    cfg = soccfg()
    cfg["tprocs"][0]["f_time"] = 400.0
    program = square.build_square_wave_program(cfg, square_config, tproc_mhz=300)
    assert program.summary["period_cycles"] == 7500
    assert cfg["tprocs"][0]["f_time"] == 400.0
    for config in (square.SquareWaveConfig(gen_ch=2),
                   square.SquareWaveConfig(gen_ch=0, frequency_hz=1e7),
                   square.SquareWaveConfig(gen_ch=0, frequency_hz=.001),
                   square.SquareWaveConfig(gen_ch=0, duty_percent=.001)):
        with pytest.raises(ValueError):
            square.build_square_wave_program(cfg, config)
    cfg["gens"][0]["type"] = "axis_signal_gen_v6"
    with pytest.raises(ValueError, match="Select an AWG tuning DAC generator"):
        square.build_square_wave_program(cfg, square.SquareWaveConfig(gen_ch=0))


class FakeSoc:
    def __init__(self):
        self.calls = []
        self.stop_failures = 0
        self.start_error = False

    def rfb_set_gen_dc(self, ch):
        self.calls.append(("dc", ch))

    def start_src(self, source):
        self.calls.append(("source", source))

    def start_tproc(self):
        self.calls.append(("start",))
        if self.start_error:
            raise RuntimeError("start transport error")

    def stop_square_pulse(self, ch):
        self.calls.append(("mute", ch))
        if self.stop_failures:
            self.stop_failures -= 1
            raise RuntimeError("stop transport error")


def fake_factory(cfg, config, **kwargs):
    return SimpleNamespace(summary=dict(actual_frequency_hz=40000, actual_duty_percent=50,
        high_code=1528, low_code=712, tproc_mhz=300, full_scale_mv=config.full_scale_mv),
        config_all=lambda soc, reset: soc.calls.append(("load", reset)))


def worker_for(soc):
    return square.SquareWaveWorker(None, square.SquareWaveConfig(gen_ch=0, zero_code=0), tproc_mhz=300,
        connector=lambda connection: (soc, square_soccfg()), program_factory=fake_factory)


def test_worker_retries_failed_cleanup_after_start_error():
    soc = FakeSoc()
    soc.stop_failures = 1
    soc.start_error = True
    worker = worker_for(soc)
    started, stop_failed, finished = Event(), Event(), Event()
    worker.started.connect(lambda _: started.set(), QtCore.Qt.DirectConnection)
    worker.stop_failed.connect(lambda _: stop_failed.set(), QtCore.Qt.DirectConnection)
    worker.finished.connect(lambda _: finished.set(), QtCore.Qt.DirectConnection)
    worker.failed.connect(lambda _: finished.set(), QtCore.Qt.DirectConnection)
    thread = Thread(target=worker.run, daemon=True)
    thread.start()
    try:
        assert stop_failed.wait(3)
        assert thread.is_alive() and not finished.is_set()
        worker.request_stop()
        assert finished.wait(3)
        thread.join(3)
        assert soc.calls == [("load", True), ("dc", 0), ("source", "internal"), ("start",), ("mute", 0), ("mute", 0)]
    finally:
        worker.request_stop()
        thread.join(3)


def test_cancel_before_start_and_cleanup_after_start_error():
    soc = FakeSoc()
    worker = worker_for(soc)
    worker.request_stop()
    worker.run()
    assert soc.calls == []
    soc.start_error = True
    worker = worker_for(soc)
    errors = []
    worker.failed.connect(errors.append, QtCore.Qt.DirectConnection)
    worker.run()
    assert soc.calls[-1] == ("mute", 0)
    assert "start transport error" in errors[0]


def test_cancel_during_program_load_does_not_start_output():
    soc = FakeSoc()
    worker = worker_for(soc)
    worker.program_factory = lambda *a, **k: SimpleNamespace(
        config_all=lambda *a, **k: worker.request_stop())
    worker.run()
    assert ("start",) not in soc.calls
    assert soc.calls[-1] == ("mute", 0)


def qt_until(predicate):
    for _ in range(300):
        if predicate():
            return
        QtTest.QTest.qWait(10)
    assert predicate()


def test_gui_tab_settings_start_stop_and_close(monkeypatch):
    import DCWaveform_Generator as gui
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    soc = FakeSoc()
    monkeypatch.setattr(square, "connect_qick", lambda _: (soc, square_soccfg()))
    monkeypatch.setattr(square, "build_square_wave_program", fake_factory)
    window = gui.MainWindow()
    panel = window._square_wave_panel
    from qick_front_panel import identify_qick_front_panel
    window._on_qick_configuration_identified(identify_qick_front_panel(square_soccfg()))
    try:
        assert window._control_tabs.tabText(window._control_tabs.indexOf(panel)) == "QICK Square Wave"
        assert not hasattr(panel, "codes_per_mv")
        assert not hasattr(panel, "calibration_database_path")
        assert not hasattr(panel, "calibration_run")
        assert panel.full_scale_mv.value() == 800
        current_records = {'00': dict(converter_id='00', channels=[0],
                                     dc_output=True, current_ua=10000,
                                     adjustable=True, reason='')}
        monkeypatch.setattr(soc, 'get_dac_current_settings', lambda: current_records, raising=False)
        window._dac_current_state.update(current_records)
        window._calibration_panel.database_path.setText("missing.db")
        assert panel.full_scale_mv.value() == 400
        assert window._experiment_panel.full_scale_mv.value() == 800
        panel.amplitude_mv.setValue(12.5)
        panel.phase_deg.setValue(45)
        payload = window._settings_to_dict()
        decoded = window._decode_settings(payload)
        assert decoded["square_wave"]["amplitude_mv"] == 12.5
        assert decoded["square_wave"]["zero_code"] == 0
        assert decoded["square_wave"]["phase_deg"] == 45
        assert decoded["square_wave"]["full_scale_mv"] == 400
        panel.load_settings(decoded["square_wave"])
        del payload["square_wave"]
        assert window._decode_settings(payload)["square_wave"] == square.normalize_square_wave_settings()
        panel.start_button.click()
        qt_until(lambda: "Running:" in panel.status.text())
        qt_until(lambda: window._experiment_thread is None)
        assert "maximum output +/-400 mV" in panel.status.text()
        assert panel.start_button.isEnabled() and panel.stop_button.isEnabled()
        assert not any(call[0]=='mute' for call in soc.calls)
        assert soc.calls.count(("start",)) == 1
        panel.stop_button.click()
        qt_until(lambda: window._experiment_thread is None)
        assert panel.start_button.isEnabled() and panel.stop_button.isEnabled()
        assert soc.calls[-1] == ("mute", 0)
        # Stop also mutes output left enabled by a different completed program.
        panel.stop_button.click()
        qt_until(lambda: window._experiment_thread is None)
        assert soc.calls[-1] == ("mute", 0)
        panel.start_button.click()
        qt_until(lambda: "Running:" in panel.status.text())
        qt_until(lambda: window._experiment_thread is None)
        panel.stop_button.click()
        qt_until(lambda: window._experiment_thread is None)
        assert soc.calls[-1] == ("mute", 0)
    finally:
        if window._experiment_worker is not None:
            window._experiment_worker.request_stop()
            qt_until(lambda: window._experiment_thread is None)
        window.close()
        app.processEvents()


def test_invalid_output_range_prevents_hardware_configuration():
    soc = FakeSoc()
    worker = worker_for(soc)
    worker.program_factory = square.build_square_wave_program
    worker.config = replace(worker.config, amplitude_mv=801)
    errors = []
    worker.failed.connect(errors.append, QtCore.Qt.DirectConnection)
    worker.run()
    assert soc.calls == []
    assert "SquarePulse amplitude" in errors[0]


def test_worker_rechecks_ip_identity_before_touching_hardware():
    soc = FakeSoc()
    worker = worker_for(soc)
    worker.connector = lambda _: (soc, soccfg())
    errors = []
    worker.failed.connect(errors.append, QtCore.Qt.DirectConnection)
    worker.run()
    assert soc.calls == []
    assert 'dedicated SquarePulse IP' in errors[0]


def test_dedicated_program_reaches_end_without_mute():
    from qick.awg_tuning import TProcV1BehaviorModel
    from qick.square_pulse import frequency_word, phase_word
    cfg = square_soccfg()
    config = square.SquareWaveConfig(gen_ch=0, zero_code=0, frequency_hz=2000,
                                    amplitude_mv=20, phase_deg=45)
    program = square.build_square_wave_program(cfg, config)
    model = TProcV1BehaviorModel(strict=True)
    model.run(program)
    assert len(model.output_events) == 1
    word = model.output_events[0].word
    assert word & 0xffffffff == frequency_word(.002, 4800)
    assert word >> 32 & 0xffffffff == phase_word(45)
    assert word >> 64 & 0xffffffff == 820
    assert word >> 128 & 3 == 1
    assert program.prog_list[-1]['name'] == 'end'
