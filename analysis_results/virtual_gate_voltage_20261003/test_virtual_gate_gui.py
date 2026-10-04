"""Exercise actual GUI run-argument builders and saved settings with virtual gates."""
from dataclasses import replace
import numpy as np
import pytest
from qick.sim import QickSim
from dc_waveform_core import QickSweepSpec
from test_square_awg_exclusion import window, firmware
from test_dac_current import records


@pytest.mark.parametrize('reverse', [False, True])
def test_virtual_voltage_sweeps_across_gui_tabs_and_settings(window, reverse):
    window._add_port()
    config = firmware()
    outputs = tuple(replace(port, block_paths=tuple(
        path.replace('axis_awg_tuning_v1', 'axis_awg_tuning_v2')
        for path in port.block_paths)) for port in config.outputs)
    window._on_qick_configuration_identified(replace(config, outputs=outputs,
        dac_current_settings=records((20000, 10000, 20000))))
    matrix = np.array([[1., .23], [-.17, 1.]])
    window._cross_capacitance = matrix.copy()
    x = np.linspace(5., 15., 20)
    y = np.linspace(-9., 7., 20)
    if reverse:
        x, y = x[::-1], y[::-1]
    window._sweep_specs = [
        QickSweepSpec('set_0','awg_0',float(x[0]/800),float(x[-1]/800),20),
        QickSweepSpec('set_0','awg_1',float(y[0]/800),float(y[-1]/800),20)]
    panel = window._stability_panel
    for axis, channel, values in ((panel.x_axis,1,x),(panel.y_axis,3,y)):
        axis.apply_front_panel_settings({'output_ch': channel})
        axis.start_mv.setValue(float(values[0]))
        axis.stop_mv.setValue(float(values[-1]))
        axis.points.setValue(20)
    expected = np.array([(vx,vy) for vx in x for vy in y]) @ matrix.T
    for restore in (False, True):
        if restore:
            saved = window._settings_to_dict()
            window._apply_decoded_settings(window._decode_settings(saved))
        for tab in ('awg','stability','awg'):
            args = (window._stability_run_arguments(save=False) if tab=='stability' else
                    window._experiment_run_arguments(require_readout=False, require_run_config=False))
            assert args['awg_channels'] == (1,3)
            seq = args['sequence']
            np.testing.assert_array_equal(seq.cross_capacitance, matrix)
            assert seq.output_full_scales_mv == (800.,400.)
            actual = np.array([seq.amplitudes_at(p,0) for p in range(400)]) * [800.,400.]
            np.testing.assert_allclose(actual, expected, atol=1e-12)
