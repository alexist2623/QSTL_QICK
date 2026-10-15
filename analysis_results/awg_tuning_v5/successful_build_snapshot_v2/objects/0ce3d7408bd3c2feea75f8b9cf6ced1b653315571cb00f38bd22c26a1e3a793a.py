"""Loop semantics, real Qt edits and production compilation; no board writes."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json

import numpy as np
import pytest
from PyQt5 import QtWidgets, QtCore

from quantum_circuit_model import validate_document, build_timeline
from quantum_circuit_loops import sweep_values, point_document, MAX_EXPANDED_GATES
from quantum_circuit_widgets import LoopEditor, QuantumCircuitPanel, QuantumCircuitView
from test_quantum_circuit_execution import config, arguments, awg, rf, gate
from qick_qcodes_experiment import QickConnectionConfig, QcodesRunConfig
from qick_fine_tune_sweep import FineTuneDdrResult
import quantum_circuit_execution as bridge


def loop_document(n=3, sweep=None):
    return dict(version=2, shots=2, qubits=[dict(id='q1', name='q1'), dict(id='q2', name='q2')],
                awg_baselines=[dict(channel=1, voltage_mv=0), dict(channel=2, voltage_mv=0)],
                gates=[gate('Init', 0, 5, awg=[awg(1, 10), awg(2, -10)], qubits=('q1', 'q2')),
                       gate('X', 5, 2, awg=[awg(1, 1, 'relative', .1), awg(2, -1, 'relative', .1)], rf=[rf(.5, .5)]),
                       gate('Y', 7, 3, rf=[rf(.5, .5)]),
                       gate('Readout', 10, 20, acquisition=dict(delay_us=0, duration_us=20))],
                loops=[dict(id='loop1', name='Drive', gate_ids=['X', 'Y'], count=n, sweep=sweep)])


def loop_config():
    cfg = config()
    cfg['tprocs'][0]['pmem_size'] = 65536
    return cfg


@pytest.mark.parametrize('n', [0, 1, 2, 10, 100])
def test_expansion_continues_relative_voltage_and_moves_readout(n):
    doc = loop_document(n)
    before = deepcopy(doc)
    timeline = build_timeline(doc)
    assert doc == before
    assert len(timeline['gates']) == 2 + 2 * n
    assert timeline['duration_us'] == 25 + 5 * n
    assert timeline['acquisition'][0]['start_us'] == 5 + 5 * n
    assert timeline['acquisition'][0]['end_us'] == 25 + 5 * n
    assert timeline['awg'][0]['points'][-1][1] == 10 + n
    assert timeline['awg'][1]['points'][-1][1] == -10 - n
    assert len(timeline.get('rf', [])[0]['events']) == 2 * n if n else timeline['rf'] == []
    assert [r['target_mv'] for r in timeline['awg'][0]['events']] == [10] + list(range(11, 11 + n))
    assert set(timeline['gate_origins'].values()) == ({'X', 'Y'} if n else set())


def test_sequential_loops_shift_independently_and_zero_preserves_preceding_idle():
    doc = loop_document(2)
    doc['gates'].insert(3, gate('Wait', 10, 3))
    doc['gates'][-1]['start_us'] = 13
    doc['loops'].append(dict(id='l2', name='Idle', gate_ids=['Wait'], count=3))
    assert build_timeline(doc)['acquisition'][0]['start_us'] == 24
    doc = loop_document(0)
    doc['gates'] = doc['gates'][1:3]
    assert build_timeline(doc)['duration_us'] == 5  # Keep the initial 5 us idle.


@pytest.mark.parametrize('start,stop,step,expected', [(0, 4, 2, [0, 2, 4]), (5, 1, -2, [5, 3, 1]), (2, 2, 1, [2])])
def test_exact_integer_sweep_and_independent_documents(start, stop, step, expected):
    doc = loop_document(sweep=dict(start=start, stop=stop, step=step))
    assert sweep_values(doc['loops'][0]['sweep']) == expected
    assert validate_document(doc) == validate_document(validate_document(doc))
    for index, n in enumerate(expected):
        point = point_document(doc, index)
        assert point['loops'][0]['count'] == n
        assert point['loops'][0]['sweep'] is None
        assert build_timeline(point)['acquisition'][0]['start_us'] == 5 + 5 * n
    assert doc['loops'][0]['count'] == 3


@pytest.mark.parametrize('mutate', [
    lambda d: d['loops'][0].update(gate_ids=['X']),  # X alone is valid; force overlap below.
    lambda d: d['loops'][0].update(gate_ids=['missing']),
    lambda d: d['loops'][0].update(count=True),
    lambda d: d['loops'][0].update(count=-1),
    lambda d: d['loops'][0].update(count=MAX_EXPANDED_GATES),
    lambda d: d['loops'][0].update(sweep=dict(start=0, stop=5, step=2)),
    lambda d: d['loops'][0].update(sweep=dict(start=0, stop=5, step=-1)),
    lambda d: d['loops'][0].update(sweep=dict(start=0, stop=5, step=0)),
])
def test_bad_loop_transactions_reject_without_mutation(mutate):
    doc = loop_document()
    mutate(doc)
    if doc['loops'][0]['gate_ids'] == ['X']:
        doc['gates'].append(gate('simultaneous', 5, 2, qubits=('q2',)))
    before = deepcopy(doc)
    with pytest.raises(ValueError):
        validate_document(doc)
    assert doc == before


def test_nested_or_overlapping_loops_and_two_sweeps_reject():
    doc = loop_document()
    doc['loops'].append(dict(id='second', name='nested', gate_ids=['X'], count=2))
    with pytest.raises(ValueError, match='overlap'):
        validate_document(doc)
    doc = loop_document(sweep=dict(start=0, stop=2, step=1))
    doc['loops'].append(dict(id='second', name='other', gate_ids=['Init'], count=2,
                             sweep=dict(start=0, stop=1, step=1)))
    with pytest.raises(ValueError, match='one loop'):
        validate_document(doc)


@pytest.fixture(scope='module')
def app():
    instance = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield instance


def test_loop_editor_accept_cancel_and_invalid_step(app):
    doc = loop_document()
    editor = LoopEditor(doc, loop=doc['loops'][0])
    editor.count_spin.setValue(4)
    editor.sweep_group.setChecked(True)
    editor.sweep_spins['start'].setValue(0)
    editor.sweep_spins['stop'].setValue(4)
    editor.sweep_spins['step'].setValue(0)
    editor.accept()
    assert editor.result() != QtWidgets.QDialog.Accepted
    assert editor.error_label.text()
    editor.sweep_spins['step'].setValue(2)
    editor.accept()
    assert editor.result() == QtWidgets.QDialog.Accepted
    assert editor.result_document['loops'][0]['count'] == 4
    assert doc['loops'][0]['count'] == 3
    cancelled = LoopEditor(doc, loop=doc['loops'][0])
    cancelled.count_spin.setValue(99)
    cancelled.reject()
    assert cancelled.result_document is None


def test_preview_selection_loop_drawing_and_delete_preserves_source_gates(app):
    doc = loop_document(sweep=dict(start=0, stop=4, step=2))
    panel, view = QuantumCircuitPanel(), QuantumCircuitView()
    panel.preview_changed.connect(view.set_document)
    panel.load_document(doc)
    assert panel.preview_combo.count() == 3
    assert view._document['loops'][0]['count'] == 0
    panel.preview_combo.setCurrentIndex(2)
    assert view._document['loops'][0]['count'] == 4
    assert panel.document()['loops'][0]['count'] == 3
    scene = view.graphics_view.scene()
    assert any(item.data(1) == 'loop1' for item in scene.items())
    assert any(item.data(0) == 'X' for item in scene.items())
    panel.set_running(True)
    panel.delete_loop('loop1')
    assert panel.document()['loops']
    panel.set_running(False)
    panel.delete_loop('loop1')
    assert panel.document()['loops'] == []
    assert panel.document()['gates'] == validate_document(doc)['gates']
    panel.close()
    view.close()


@pytest.mark.parametrize('n', [0, 1, 3, 100])
def test_loop_compiles_exact_rf_awg_and_acquisition_times(n):
    result = bridge.build_circuit_execution(loop_document(n), loop_config(), **arguments())
    assert result.repetitions_per_sweep == 2  # Shots is independent of loop n.
    assert result.metadata['rf_pulse_count'] == n * 2
    assert result.metadata['acquisition_input_start_us'] == 5 + 5 * n
    assert result.metadata['acquisition_input_end_us'] == 25 + 5 * n
    assert result.metadata['circuit_duration_us'] == 25 + 5 * n
    origin = result.metadata['circuit_origin_us']
    actual = [(entry['start'] + 42) / 300 - origin for entry in result.program.aux_timing['rf_pulses']]
    expected = [value for i in range(n) for value in (5.5 + 5 * i, 7.5 + 5 * i)]
    assert actual == pytest.approx(expected)
    if n:
        assert len(result.rf_specs[0].frequency_parameters) == 1
    assert result.metadata['expanded_gate_count'] == 2 + n * 2


def test_loop_program_memory_capacity_and_repeated_acquisition_reject():
    cfg = loop_config()
    cfg['tprocs'][0]['pmem_size'] = 8
    with pytest.raises(RuntimeError, match='program memory'):
        bridge.build_circuit_execution(loop_document(), cfg, **arguments())
    doc = loop_document()
    doc['gates'][1]['acquisition'] = dict(delay_us=0, duration_us=1)
    with pytest.raises(ValueError, match='exactly one'):
        bridge.build_circuit_execution(doc, loop_config(), **arguments())


@pytest.mark.parametrize('kind,mode', [('filter', 'fixed_voltage'), ('dc_rc', 'fixed_time'), ('dc_rc', 'fixed_voltage')])
def test_loop_preserves_existing_compensation_mode(kind, mode):
    options = dict(bias_t_compensation_enabled=True, bias_t_compensation_type=kind,
                   bias_t_compensation_mode=mode, bias_t_compensation_voltage_mv=20,
                   bias_t_compensation_duration_us=100, bias_t_filter_tau_us=1000)
    result = bridge.build_circuit_execution(loop_document(), loop_config(), compensation=options, **arguments())
    assert result.sequence.rc_compensation.tau_us == 1000
    assert (result.sequence.bias_t_compensation is None) == (kind == 'filter')
    assert result.metadata['rf_pulse_count'] == 6


def sweep_arguments(tmp_path):
    return dict(document=loop_document(sweep=dict(start=0, stop=4, step=2)),
                connection_config=QickConnectionConfig(),
                run_config=QcodesRunConfig(str(tmp_path/'loop.db')),
                gui_settings={}, connector=lambda **kw: (object(), loop_config()), **arguments())


def test_all_sweep_points_preflight_before_first_acquisition(tmp_path, monkeypatch):
    args = sweep_arguments(tmp_path)
    # The last n=4 alone exceeds the calibrated target range.
    args['document']['gates'][1]['awg'][0]['value_mv'] = 250
    monkeypatch.setattr(bridge.experiment, 'run_qick_qcodes_experiment',
                        lambda **kw: pytest.fail('Hardware runner started before full preflight'))
    with pytest.raises(ValueError, match='full scale'):
        bridge.run_quantum_circuit_experiment(**args)
    assert not list(tmp_path.glob('*.json'))


def test_real_qcodes_n_sweep_saves_linked_runs_and_coordinates(tmp_path, monkeypatch):
    args = sweep_arguments(tmp_path)
    monkeypatch.setenv(bridge.experiment.QCODES_STAGING_ENV, str(tmp_path/'staging'))
    executed = []
    def acquire(soc, cfg, sequence, **kw):
        program = bridge.experiment.build_qick_program(
            cfg, sequence, awg_channels=kw['awg_channels'], repetitions_per_sweep=kw['repetitions_per_sweep'],
            tproc_mhz=kw['tproc_mhz'], rf_specs=kw['rf_specs'], readout_spec=kw['readout_spec'],
            compile_validation_mode=kw['compile_validation_mode'])
        program.compile()
        executed.append(len(program.aux_timing['rf_pulses']))
        return program, FineTuneDdrResult(sweep_points=np.asarray([0.]),
            iq=np.zeros((1, 2, 20, 2), dtype=np.int32), cross_capacitance=np.eye(2)), {}
    monkeypatch.setattr(bridge.experiment, 'execute_qick_sequence', acquire)
    result = bridge.run_quantum_circuit_experiment(**args)
    summary = result.circuit_loop_sweep
    assert executed == [0, 4, 8]
    assert summary['status'] == 'complete'
    assert [point['n'] for point in summary['points']] == [0, 2, 4]
    assert len({point['run_id'] for point in summary['points']}) == 3
    assert json.loads(Path(summary['manifest_path']).read_text())['status'] == 'complete'
    from qcodes.dataset import load_by_id
    for point in summary['points']:
        dataset = load_by_id(point['run_id'])
        metadata = json.loads(dataset.get_metadata('qick_experiment_json'))['gui_settings']
        assert metadata['quantum_circuit_execution']['loop_count_sweep']['n'] == point['n']
        assert metadata['quantum_circuit_execution']['acquisition_input_start_us'] == 5 + 5 * point['n']
        dataset.conn.close()


@pytest.mark.parametrize('cancelled', [True, False])
def test_partial_sweep_keeps_saved_runs_and_stops(tmp_path, monkeypatch, cancelled):
    args = sweep_arguments(tmp_path)
    calls = []
    def run(**kwargs):
        context = kwargs['gui_settings']['quantum_circuit_execution']['loop_count_sweep']
        calls.append(context['n'])
        if len(calls) == 2:
            if cancelled:
                raise bridge.experiment.ExperimentCancelled('test stop')
            raise ValueError('test failure')
        return SimpleNamespace(run_id=11, database_path=tmp_path/'loop.db', detach_dataset=lambda: None)
    monkeypatch.setattr(bridge.experiment, 'run_qick_qcodes_experiment', run)
    with pytest.raises(bridge.experiment.ExperimentCancelled if cancelled else RuntimeError, match='1/3 Runs saved'):
        bridge.run_quantum_circuit_experiment(**args)
    assert calls == [0, 2]
    manifest = json.loads(next(tmp_path.glob('*.json')).read_text())
    assert manifest['status'] == ('cancelled' if cancelled else 'failed')
    assert manifest['points'] == [dict(index=0, n=0, run_id=11, database_path=str(tmp_path/'loop.db'))]
