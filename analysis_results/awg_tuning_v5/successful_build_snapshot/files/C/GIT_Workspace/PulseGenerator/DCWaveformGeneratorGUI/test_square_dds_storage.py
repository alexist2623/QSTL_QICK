"""SquarePulse axes keep physical units through QCoDeS IQ64 persistence."""
import itertools
import numpy as np
import pytest
from qick_fine_tune_sweep import FineTuneDdrResult
from qick_square_dds import SquarePulseSweep
from qick_qcodes_experiment import (
    store_qick_result, QcodesRunConfig, QickConnectionConfig,
    load_qick_iq_arrays, load_qick_raw_int64_arrays, QCODES_STAGING_ENV,
    _sweep_parameter_names,
)


@pytest.mark.parametrize('storage_mode', ['full_traces', 'mean_iq'])
def test_square_cartesian_axes_and_iq64_roundtrip(tmp_path, monkeypatch, storage_mode):
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path/'staging'))
    axes = tuple(SquarePulseSweep(name, start, stop, 2, 7,
                                 segment_name=name, output_name='square7')
                 for name, start, stop in [('frequency', 100, 190),
                                          ('amplitude', 10, 20), ('phase', -90, 90)])
    coordinates = np.array(list(itertools.product(*(axis.points for axis in axes))))
    raw = (np.arange(8*2*3*2, dtype=np.int64) + 2**60 + 3).reshape(8, 2, 3, 2)
    raw[..., 1] *= -1
    result = FineTuneDdrResult(coordinates, raw, sweep_axes=axes, sweep_shape=(2, 2, 2),
                              iq_component_bits=64, iq_scale_log2=46)
    dataset, rows = store_qick_result(result,
        run_config=QcodesRunConfig(str(tmp_path/'square.db')),
        connection_config=QickConnectionConfig(), program_summary={},
        gui_settings={}, rf_settings={}, iq_storage_mode=storage_mode)
    loaded = load_qick_iq_arrays(dataset)
    metadata = loaded['metadata']['measurement_layout']['sweep_axes']
    names = _sweep_parameter_names(axes)
    for index, (axis, name) in enumerate(zip(axes, names)):
        assert metadata[index]['axis_kind'] == axis.axis_kind
        assert metadata[index]['unit'] == axis.coordinate_unit
        assert metadata[index]['gen_ch'] == 7
        actual = loaded['sweep_coordinates'][name]
        np.testing.assert_array_equal(actual[:, 0], coordinates[:, index])
    if storage_mode == 'full_traces':
        np.testing.assert_array_equal(load_qick_raw_int64_arrays(dataset, shape=raw.shape), raw)
    else:
        assert rows == 8
        assert not set(dataset.paramspecs).intersection({'i_trace', 'q_trace', 'i_raw_int64', 'q_raw_int64'})
        assert loaded['iq'].shape == (8, 1, 1, 2)
