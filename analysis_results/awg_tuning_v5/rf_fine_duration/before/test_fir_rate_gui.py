"""Headless GUI checks for HWH-selected 1 MSPS and 50 kSPS timing.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtWidgets
import pytest

from calibration_gui import CalibrationPanel
from DCWaveform_Generator import RfReadoutPanel
from dc_waveform_core import PulseSequence
from noise_analysis import NoiseAnalysisPanel
from qick_front_panel import QickFrontPanelConfiguration
from sparameter_gui import SParameterSweepPanel
from stability_diagram import StabilityDiagramPanel


def _application():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _configuration(*, is_50_ksps: bool) -> QickFrontPanelConfiguration:
    if is_50_ksps:
        return QickFrontPanelConfiguration(
            board="ZCU216",
            firmware_timestamp="test-50k",
            outputs=(),
            inputs=(),
            fir_rate_profile="50_ksps",
            fir_sample_rate_hz=50_000.0,
            fir_sample_period_us=20.0,
            fir_trigger_delay_samples=300_000,
            fir_trigger_delay_units="s_axis_aclk_cycles",
            fir_trigger_delay_us=1000.0,
            fir_rate_label=(
                "50 kSPS (20 us/sample, FPGA delay 300000 cycles (1000 us))"
            ),
        )
    return QickFrontPanelConfiguration(
        board="ZCU216",
        firmware_timestamp="test-1m",
        outputs=(),
        inputs=(),
        fir_rate_profile="1_msps",
        fir_sample_rate_hz=1_000_000.0,
        fir_sample_period_us=1.0,
        fir_trigger_delay_samples=0,
        fir_trigger_delay_us=0.0,
        fir_rate_label=(
            "1 MSPS (1 us/sample, tProcessor FIR warm-up compensation)"
        ),
    )


@pytest.mark.parametrize(
    ("is_50_ksps", "rate_text", "trace_time_us", "sparameter_text"),
    (
        (False, "1 MSPS", 100.0, "101 samples = 101 us actual"),
        (True, "50 kSPS", 2000.0, "6 samples = 120 us actual"),
    ),
)
def test_all_fir_gui_tabs_display_hwh_selected_rate(
    is_50_ksps,
    rate_text,
    trace_time_us,
    sparameter_text,
):
    app = _application()
    configuration = _configuration(is_50_ksps=is_50_ksps)

    readout = RfReadoutPanel(PulseSequence(), time_unit="us")
    readout.samples.setValue(100)
    readout.set_front_panel_configuration(configuration)
    assert rate_text in readout.fir_profile_note.text()
    assert f"100 samples = {trace_time_us:g} us" in readout.fir_profile_note.text()
    assert readout.override_fpga_trigger_delay.isEnabled() is is_50_ksps
    readout.override_fpga_trigger_delay.setChecked(True)
    readout.fpga_trigger_delay_us.setValue(700.0)
    assert readout.configured_spec().fpga_trigger_delay_us == (
        700.0 if is_50_ksps else None
    )

    stability = StabilityDiagramPanel()
    stability.refresh_targets(("awg_0", "awg_1"), (0, 1))
    stability.trace_samples.setValue(100)
    stability.set_front_panel_configuration(configuration)
    assert rate_text in stability.fir_profile_status.text()
    assert f"100 samples = {trace_time_us:g} us" in stability.fir_profile_status.text()
    if is_50_ksps:
        assert "HWH FPGA delay 1000 us" in stability.fir_profile_status.text()
    else:
        assert (
            "no FPGA trigger-delay register"
            in stability.fir_profile_status.text()
        )
    assert stability.override_fpga_trigger_delay.isEnabled() is is_50_ksps
    stability.override_fpga_trigger_delay.setChecked(True)
    stability.fpga_trigger_delay_us.setValue(700.0)
    assert stability.config(full_scale_mv=800.0).fpga_trigger_delay_us == (
        700.0 if is_50_ksps else None
    )

    sparameter = SParameterSweepPanel()
    sparameter.scan_time_us.setValue(101.0)
    sparameter.set_front_panel_configuration(configuration)
    assert rate_text in sparameter.fir_profile_status.text()
    assert sparameter_text in sparameter.fir_profile_status.text()
    assert sparameter.override_fpga_trigger_delay.isEnabled() is is_50_ksps
    sparameter.override_fpga_trigger_delay.setChecked(True)
    sparameter.fpga_trigger_delay_us.setValue(700.0)
    assert sparameter.config().fpga_trigger_delay_us == (
        700.0 if is_50_ksps else None
    )

    calibration = CalibrationPanel()
    calibration.dc_voltage_samples.setValue(100)
    calibration.set_front_panel_configuration(configuration)
    assert rate_text in calibration.fir_profile_status.text()
    assert (
        f"DC calibration 100 samples = {trace_time_us:g} us"
        in calibration.fir_profile_status.text()
    )
    assert (
        calibration.input_override_fpga_trigger_delay.isEnabled()
        is is_50_ksps
    )
    assert (
        calibration.dc_voltage_override_fpga_trigger_delay.isEnabled()
        is is_50_ksps
    )

    noise = NoiseAnalysisPanel(default_database_path="noise.db")
    noise.fir_samples.setValue(100)
    noise.set_front_panel_configuration(configuration)
    assert noise.sample_rate.value() == configuration.fir_sample_rate_hz
    assert rate_text in noise.capture_duration.text()
    assert configuration.fir_rate_label in noise.fir_profile_status.text()
    assert noise.override_fpga_trigger_delay.isEnabled() is is_50_ksps
    noise.override_fpga_trigger_delay.setChecked(True)
    noise.fpga_trigger_delay_us.setValue(700.0)
    assert noise.acquisition_config().fpga_trigger_delay_us == (
        700.0 if is_50_ksps else None
    )

    app.processEvents()
    for widget in (readout, stability, sparameter, calibration, noise):
        widget.close()
