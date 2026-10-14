"""Post-publication checks against actual v4 and retained v3 HWH, no board I/O."""
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET
import zipfile

import pytest
from qick.sim import QickSim  # desktop PYNQ stubs; never load a board overlay
from qick.ip import QickMetadata
from qick.drivers.generator import AbsSignalGen
from qick.dac_current import DacCurrentControl
from qick.output_sum import validate_shared_dac_config
from PyQt5 import QtGui, QtWidgets, sip
from qick_front_panel import QickFrontPanelControl, identify_qick_front_panel
import DCWaveform_Generator as gui
from dc_waveform_core import PulseSequence, QickRfPulseSpec
from qick_qcodes_experiment import configure_rf_output
from qick_dac_current import DacCurrentState, verify_current_settings

ROOT = Path('C:\\GIT_Workspace\\QSTL_QICK')
OUT = Path('C:\\GIT_Workspace\\QSTL_QICK\\analysis_results\\awg_tuning_v4')
PROJECT = ROOT / 'qick/firmware/projects/qstl_awg_v4'
PAIRS = [(0, 1, '10'), (2, 3, '11'), (4, 5, '12')]
NAMES = ['axis_signal_gen_v6_0', 'axis_awg_tuning_v3_4',
         'axis_signal_gen_v6_1', 'axis_awg_tuning_v3_5',
         'axis_signal_gen_v6_3', 'axis_awg_tuning_v3_6',
         'axis_signal_gen_v6_2', 'axis_square_pulse_v1_0',
         'axis_awg_tuning_v3_8', 'axis_awg_tuning_v3_9',
         'axis_awg_tuning_v3_10', 'axis_awg_tuning_v3_11']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_scope():
    spec = importlib.util.spec_from_file_location('final_v4_scope', PROJECT / 'validate_scope.py')
    scope = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scope)
    return scope


def firmware_config(version):
    """Run the production common driver connection method on real HWH nets.

    RFDC frequency attributes and daughter-card detection are desktop stand-ins;
    physical routes, IP types/revisions and sum parameters come from final HWH.
    """
    hwh = PROJECT.parent / f'qstl_awg_v{version}' / 'bitstream.hwh'
    metadata = QickMetadata(SimpleNamespace(parser=SimpleNamespace(root=ET.parse(hwh).getroot())))
    class Soc(dict):
        def _get_block(self, block):
            assert block == 'usp_rf_data_converter_0'
            return self.rf_stub
    soc = Soc(rf={'dacs': {f'{t}{b}': dict(fs=4800., fs_mult=16, fs_div=1,
        interpolation=1, f_fabric=300.) for t in range(4) for b in range(4)}})
    soc.metadata = metadata
    soc.rf_stub = object()
    generators = []
    for name in NAMES:
        # Skip MMIO initialization; the method under test only discovers wiring.
        gen = object.__new__(AbsSignalGen)
        gen._cfg = dict(fullpath=name, type=metadata.mod2type(name))
        if name.startswith('axis_awg_tuning'):
            gen._cfg['output_latency_cycles'] = 16
        AbsSignalGen.configure_connections(gen, soc)
        before = dict(gen.cfg)
        AbsSignalGen.configure_connections(gen, soc)
        assert gen.cfg == before
        assert gen.rf is soc.rf_stub
        generators.append(dict(gen.cfg))
    return dict(board='ZCU216', fw_timestamp=metadata.timestamp, gens=generators,
        readouts=[], extra_description=[
            'DAC slot 0: RF Out card has ports [0, 1, 2, 3]',
            'DAC slot 1: DC Out card has ports [4, 5, 6, 7]',
            'DAC slot 2: DC Out card has ports [8, 9, 10, 11]'])


@pytest.fixture(scope='module')
def v4():
    return firmware_config(4)


@pytest.fixture(scope='module')
def v3():
    return firmware_config(3)


@pytest.fixture(scope='module')
def app():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    app.setFont(QtGui.QFont('Segoe UI', 10))
    app.setStyle('Fusion')
    yield app
    app.processEvents()


def test_published_artifacts_and_original_evidence_are_intact():
    manifest = json.loads((PROJECT / 'build_manifest.json').read_text())
    assert json.loads((OUT / 'workflow_status.json').read_text())['complete']
    assert manifest['timing']['timing_closed'] == 'YES'
    assert float(manifest['timing']['setup_wns_ns']) >= 0
    assert float(manifest['timing']['hold_whs_ns']) >= 0
    for artifact in manifest['artifacts']:
        assert sha(artifact['path']) == artifact['sha256']
        assert Path(artifact['path']).stat().st_size == artifact['bytes']
    with zipfile.ZipFile(PROJECT / 'bitstream.xsa') as archive:
        for kind, filename in [('bit', 'bitstream.bit'), ('hwh', 'bitstream.hwh')]:
            assert archive.read(manifest['xsa_members'][kind]) == (PROJECT / filename).read_bytes()
    assert sha(manifest['functional_gate']['path']) == manifest['functional_gate']['sha256']
    assert load_scope().validate() == dict(passed=True, protected_files=59)
    gate = json.loads((OUT / 'prebuild_gate.json').read_text())
    allowed = {
        ROOT.parent / 'PulseGenerator/DCWaveformGeneratorGUI/qick_front_panel.py': 'qick_front_panel.py.before',
        ROOT / 'qick/qick_lib/qick/dac_current.py': 'dac_current.py.before',
    }
    for name, digest in gate['source_hashes'].items():
        path = Path(name)
        baseline = OUT / 'postpublish_sources' / allowed[path] if path in allowed else path
        assert sha(baseline) == digest, name
    for name, digest in gate['evidence_hashes'].items():
        assert sha(name) == digest, name


@pytest.mark.parametrize('rf,awg,dac', PAIRS)
def test_final_driver_pairs_and_physical_latency(v4, rf, awg, dac):
    r, a = v4['gens'][rf], v4['gens'][awg]
    assert r['dac'] == a['dac'] == dac
    assert r['output_sum_awg'] == a['fullpath']
    assert a['output_sum_rf'] == r['fullpath']
    assert (r['output_sum_role'], a['output_sum_role']) == ('rf', 'awg')
    assert (r['output_latency_cycles'], a['output_latency_cycles']) == (31, 18)
    for cfg in (r, a):
        validate_shared_dac_config(cfg, 1, 0)
        with pytest.raises(ValueError, match='shared baseband'):
            validate_shared_dac_config(cfg, 2, 0)
        with pytest.raises(ValueError, match='shared baseband'):
            validate_shared_dac_config(cfg, 1, 5.)


@pytest.mark.parametrize('ch,dac', [(8, '20'), (9, '21'), (10, '22'), (11, '23')])
def test_remaining_awg_outputs_have_matching_delay(v4, ch, dac):
    cfg = v4['gens'][ch]
    assert cfg['dac'] == dac and cfg['output_sum_bypass']
    assert cfg['output_sum_rf'] is None and cfg['output_latency_cycles'] == 18


@pytest.mark.parametrize('ch,dac', [(6, '02'), (7, '13')])
def test_rf4_and_square_are_unchanged(v4, v3, ch, dac):
    assert v4['gens'][ch]['dac'] == v3['gens'][ch]['dac'] == dac
    assert 'output_sum_version' not in v4['gens'][ch]


def test_v3_still_has_separate_rf_outputs(v3):
    assert [v3['gens'][i]['dac'] for i in (0, 2, 4)] == ['00', '01', '03']
    assert not any('output_sum_version' in gen for gen in v3['gens'])
    assert all(v3['gens'][i]['output_latency_cycles'] == 16 for i in (1, 3, 5, 8, 9, 10, 11))
    validate_shared_dac_config(v3['gens'][0], 2, 5.)


@pytest.mark.parametrize('rf,awg,dac', PAIRS)
def test_gui_selects_both_generators_on_the_same_physical_sma(v4, app, rf, awg, dac):
    configuration = identify_qick_front_panel(v4)
    port_index = 4 * int(dac[0]) + int(dac[1])
    port = configuration.port('output', port_index)
    assert port.qick_channels == (rf, awg)
    assert port.block_paths == (NAMES[rf], NAMES[awg])
    assert port.board_type == 'DC_Out'
    panel = QickFrontPanelControl()
    try:
        panel.set_scope('output')
        panel.set_path_values({'output_ch': rf})
        panel.set_configuration(configuration)
        assert panel.output_sma.text() == f'DAC{port_index}'
        assert panel.output_channel.currentData() == rf
        assert not panel.output_att1_db.isEnabled()
        assert not panel.output_filter_type.isEnabled()
        assert not panel.output_nqz.isEnabled()
        for channel in (rf, awg):
            panel.output_channel.setCurrentIndex(panel.output_channel.findData(channel))
            selected = panel.selected_settings()
            assert selected['output_ch'] == channel
            assert selected['output_board_type'] == 'DC_Out'
            assert selected['output_att1_db'] == selected['output_att2_db'] == 0.
            assert selected['output_filter_type'] == 'bypass'
            assert selected['output_nqz'] == 1
            assert f'RFDC DAC {dac}' in panel.summary.text()
        if rf == 0:
            panel.resize(1050, 800)
            panel.show()
            app.processEvents()
            assert panel.grab().save(str(Path('C:\\GIT_Workspace\\QSTL_QICK\\analysis_results\\awg_tuning_v4\\full_regression_20261014\\final_gui_shared_dac.png')))
    finally:
        panel.close()
        sip.delete(panel)


@pytest.mark.parametrize('rf,awg,dac', PAIRS)
def test_rf_editor_uses_the_awg_physical_card_and_preserves_legacy(v4, v3, app, rf, awg, dac):
    panel = gui.RfPulsePortPanel(PulseSequence(0., initial_duration_ns=1000.), rf // 2, default_gen_ch=rf)
    try:
        panel.setChecked(True)
        panel.set_front_panel_configuration(identify_qick_front_panel(v4))
        assert panel.output_board_type.currentText() == 'DC_Out'
        assert not panel.att1_db.isEnabled()
        assert not panel.filter_type.isEnabled()
        panel.set_front_panel_configuration(identify_qick_front_panel(v3))
        assert panel.output_board_type.currentText() == 'RF_Out'
        assert panel.att1_db.isEnabled()
        assert panel.filter_type.isEnabled()
    finally:
        panel.close()
        sip.delete(panel)


@pytest.mark.parametrize('rf,awg,dac', PAIRS)
def test_rf_setup_uses_dc_path_and_rejects_old_rf_settings(v4, rf, awg, dac):
    class Soc:
        def __init__(self): self.calls = []
        def get_cfg(self): return v4
        def rfb_set_gen_dc(self, ch): self.calls.append(('dc', ch))
        def rfb_set_gen_rf(self, *args): pytest.fail('Must not configure old RF output')
        def rfb_set_gen_filter(self, *args, **kwargs): pytest.fail('Must not configure RF filter')
    soc = Soc()
    spec = QickRfPulseSpec(rf, 'hold', 0., .1, 1., 2000, 0., 0.)
    result = configure_rf_output(soc, spec)
    assert soc.calls == [('dc', rf)]
    assert result['board_type'] == 'DC_Out' and not result['attenuators_present']
    for kwargs in [dict(att1_db=1.), dict(filter_type='lowpass'),
                   dict(power_calibration_enabled=True, power_calibration_database_path='old_rf.db')]:
        with pytest.raises(ValueError, match='v4 RF generator'):
            configure_rf_output(soc, replace(spec, **kwargs))
    assert soc.calls == [('dc', rf)]


@pytest.mark.parametrize('rf,awg,dac', PAIRS)
def test_shared_dac_current_readback_scaling_and_single_physical_write(v4, rf, awg, dac):
    class Block:
        OutputCurr = 10000
        DACCompMode = 0
        def __init__(self): self.writes = []
        def SetDACVOP(self, value):
            self.writes.append(value)
            self.OutputCurr = value
    class Soc(DacCurrentControl, dict): pass
    soc = Soc(v4)
    soc.rf = SimpleNamespace(cfg={'ip_type': 2}, dac_tiles=[
        SimpleNamespace(blocks=[Block() for _ in range(4)]) for _ in range(4)])
    records = soc.get_dac_current_settings()
    record = records[dac]
    assert record['dc_output'] and record['adjustable']
    assert record['channels'] == [rf, awg]
    assert record['full_scale_mv'] == 400.
    state = DacCurrentState()
    state.update(records)
    assert state.scale(rf) == state.scale(awg) == 400.
    saved = state.snapshot([awg])
    verify_current_settings(soc, saved)
    assert saved[dac]['channels'] == [rf, awg]
    soc.set_dac_current(dac, 16000)
    assert soc.rf.dac_tiles[int(dac[0])].blocks[int(dac[1])].writes == [16000]
    with pytest.raises(RuntimeError, match='changed'):
        verify_current_settings(soc, saved)
    # Untagged or mismatched RF metadata must retain the original read-only rule.
    soc['gens'] = [dict(gen) for gen in v4['gens']]
    soc['gens'][rf].pop('output_sum_version')
    assert not soc.get_dac_current_settings()[dac]['dc_output']
