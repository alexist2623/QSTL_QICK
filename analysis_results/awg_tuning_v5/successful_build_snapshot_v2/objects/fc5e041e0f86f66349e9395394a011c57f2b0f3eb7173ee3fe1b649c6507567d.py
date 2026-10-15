"""Connected SMA selection, saved settings, and tProcessor trigger routing."""
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtCore, QtTest, QtWidgets
import pytest

from qick_front_panel import QickFrontPanelCanvas, digital_trigger_outputs, identify_qick_front_panel
from qick_square_dds_panel import TriggeringPanel


@pytest.fixture
def panel():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    widget = TriggeringPanel()
    widget.resize(760, 420)
    widget.show()
    app.processEvents()
    yield widget
    widget.close()
    app.processEvents()


def firmware(*pins):
    return identify_qick_front_panel({"board": "ZCU216", "tprocs": [{"output_pins": pins}]})


def click_sma(canvas, sma):
    scale, dx, dy, ox, oy = canvas._display_transform()
    center = canvas._port_centers[("io", sma)]
    point = QtCore.QPoint(round((center.x() - ox) * scale + dx),
                         round((center.y() - oy) * scale + dy))
    QtTest.QTest.mouseClick(canvas, QtCore.Qt.LeftButton, pos=point)
    return point


def test_current_firmware_pin_zero_is_io_one_and_unused_smas_are_gray(panel):
    panel.set_configuration(firmware(("output", 7, 6, "SPARE1_1V8")))
    assert panel.pin.count() == 1
    assert panel.canvas._selected_io == 1
    point = click_sma(panel.canvas, 0)
    assert panel.config().pin == 0
    assert panel.canvas._selected_io == 1
    assert not panel.canvas.is_port_selectable("io", 0)
    assert panel.canvas.is_port_selectable("io", 1)
    # Verify the actual rendered disconnected connector is gray.
    pixel = panel.canvas.grab().toImage().pixelColor(point)
    assert pixel.red() == pixel.green() == pixel.blue()
    click_sma(panel.canvas, 1)
    panel.enabled.setChecked(True)
    assert panel.config().enabled and panel.config().pin == 0


def test_click_selects_firmware_index_not_sma_number_and_roundtrips(panel):
    cfg = firmware(("output", 7, 6, "SPARE1_1V8"), ("output", 7, 9, "SPARE4_1V8"))
    panel.set_configuration(cfg)
    click_sma(panel.canvas, 4)
    panel.enabled.setChecked(True)
    panel.scope.setCurrentIndex(1)
    panel.edge.setCurrentIndex(2)
    panel.width.setValue(2.5)
    assert panel.config().pin == 1
    saved = panel.settings_dict()
    restored = TriggeringPanel()
    restored.load_settings(saved)
    restored.set_configuration(cfg)
    assert restored.settings_dict() == saved
    assert restored.canvas._selected_io == 4
    restored.close()


def test_reidentify_keeps_same_sma_and_removal_disables_trigger(panel):
    first = ("output", 7, 6, "SPARE1_1V8")
    second = ("output", 7, 9, "SPARE4_1V8")
    panel.set_configuration(firmware(first, second))
    click_sma(panel.canvas, 4)
    panel.enabled.setChecked(True)
    panel.set_configuration(firmware(second, first))
    assert panel.config().enabled and panel.config().pin == 0
    assert panel.canvas._selected_io == 4
    panel.set_configuration(firmware(first))
    assert not panel.config().enabled
    assert panel.canvas._selected_io is None
    assert panel.pin.currentIndex() == -1
    click_sma(panel.canvas, 1)
    assert panel.enabled.isEnabled()
    assert not panel.enabled.isChecked()


@pytest.mark.parametrize("pins", [(), (("output", 7, 6, "PMOD0"),),
                                  (("input", 0, 1, "SPARE1_1V8"),),
                                  (("trig", 0, 1, "SPARE1_1V8"),)])
def test_unconnected_or_unsupported_firmware_cannot_enable(panel, pins):
    panel.set_configuration(firmware(*pins))
    panel.load_settings(dict(enabled=True, pin=0))
    assert not panel.enabled.isEnabled() and not panel.config().enabled
    for sma in range(8):
        assert not panel.canvas.is_port_selectable("io", sma)
        click_sma(panel.canvas, sma)
    assert panel.pin.currentIndex() == -1


def test_invalid_saved_pin_does_not_fall_back_to_another_output(panel):
    panel.set_configuration(firmware(("output", 7, 6, "SPARE1_1V8")))
    panel.load_settings(dict(enabled=True, pin=4))
    assert panel.pin.currentIndex() == -1
    assert not panel.config().enabled
    assert "unavailable" in panel.status.text()


def test_unidentified_panel_and_other_front_panel_editors_do_not_select_io(panel):
    assert not panel.enabled.isEnabled()
    for sma in range(8):
        assert not panel.canvas.is_port_selectable("io", sma)
    canvas = QickFrontPanelCanvas()
    canvas.set_configuration(firmware(("output", 7, 6, "SPARE1_1V8")))
    spy = QtTest.QSignalSpy(canvas.port_clicked)
    canvas.select_port("io", 1)
    assert not spy
    canvas.select_port("bias", 1)
    assert list(spy) == [["bias", 1]]
    canvas.close()


def test_ambiguous_names_are_not_exposed():
    cfg = firmware(("output", 7, 6, "SPARE1_1V8"), ("output", 7, 9, "SPARE1_1V8"))
    assert digital_trigger_outputs(cfg) == {}
    # Older config objects can still provide the existing names-only field.
    assert digital_trigger_outputs(SimpleNamespace(output_trigger_pins=("SPARE1_1V8",))) == {1: 0}


def test_selected_sma_reaches_correct_tprocessor_output_bit(panel):
    from qick.awg_tuning import TProcV1BehaviorModel
    from test_qick_fine_tune_sweep import _avg_soccfg
    from qick_fine_tune_sweep import FineTuneSequence
    from qick_square_dds import attach_square_settings
    from test_qick_output_triggers import edges_for_bit

    cfg = _avg_soccfg(1)
    cfg["board"] = "ZCU216"
    cfg["tprocs"][0]["output_pins"] = [
        ("output", 7, 6, "SPARE1_1V8"), ("output", 7, 9, "SPARE4_1V8")]
    panel.set_configuration(identify_qick_front_panel(cfg))
    click_sma(panel.canvas, 4)
    panel.enabled.setChecked(True)
    panel.width.setValue(0.1)
    sequence = FineTuneSequence(("awg",)).add_set("measure", 0.1, 200)
    attach_square_settings(sequence, trigger=panel.config())
    prog = sequence.make_program(cfg, awg_channels=(0,), repetitions_per_sweep=2)
    prog.compile()
    model = TProcV1BehaviorModel(strict=True)
    model.run(prog)
    events = [event for event in model.output_events if event.tproc_ch == 7]
    events += [SimpleNamespace(cycle=event["cycle"], word=event["word"])
               for event in model.output_pin_events if event["port"] == 7]
    events.sort(key=lambda event: event.cycle)
    edges = edges_for_bit(events, 9)
    assert len(edges) == 4
    assert [edges[i+1][0] - edges[i][0] for i in (0, 2)] == [30, 30]
    assert not edges_for_bit(events, 6)
