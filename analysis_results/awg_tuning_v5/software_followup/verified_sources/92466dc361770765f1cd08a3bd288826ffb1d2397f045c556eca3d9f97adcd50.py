"""Offline v5 package review using real HWH, fake BIT, and temporary XSA.

No SSH, FPGA loading, deployment, or repository scripts are executed. Set
QICK_V5_TEST_HWH to a preserved v5 HWH when the build drive is unavailable.
"""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET
import zipfile

import pytest

import qick_update as update


ROUTES = ((4, 0, '10'), (5, 1, '11'), (6, 3, '12'), (8, None, '20'),
          (9, None, '21'), (10, None, '22'), (11, None, '23'))


@pytest.fixture(scope='module')
def actual_hwh():
    path = Path(os.environ.get('QICK_V5_TEST_HWH', 'F:/Vivado_Output/a5full1/bitstream.hwh'))
    if not path.is_file():
        pytest.skip('Set QICK_V5_TEST_HWH to the preserved actual v5 HWH.')
    data = path.read_bytes()
    assert ET.fromstring(data).tag == 'EDKSYSTEM'
    return data


@pytest.fixture
def package(tmp_path, monkeypatch, actual_hwh):
    repo = tmp_path / 'QSTL_QICK'
    library = repo / 'qick/qick_lib'
    installed = library / 'qick'
    installed.mkdir(parents=True)
    (installed / '__init__.py').write_text('# offline fixture\n')
    (installed / 'VERSION').write_text('0.2.357\n')
    metadata = library / 'qick.egg-info'
    metadata.mkdir()
    (metadata / 'PKG-INFO').write_text('Name: qick\nVersion: 0.2.357\n')
    folder = repo / 'qick/firmware/projects/qstl_awg_v5'
    folder.mkdir(parents=True)
    bit, hwh, xsa = (folder / ('bitstream' + suffix) for suffix in ('.bit', '.hwh', '.xsa'))
    bit.write_bytes(b'OFFLINE FAKE BITSTREAM -- NEVER LOAD')
    hwh.write_bytes(actual_hwh)
    root = ET.fromstring(actual_hwh)
    pairs = []
    for awg, rf, dac in ROUTES:
        awg_name = 'axis_awg_tuning_v3_%s' % awg
        rf_name = 'axis_signal_gen_v6_%s' % rf if rf is not None else None
        pairs.append({'awg': awg_name, 'rf': rf_name, 'dac': dac,
                      'route': {'output_sum_version': 2, 'output_sum_block': 'axis_output_sum_%s' % awg,
                                'output_sum_role': 'awg', 'output_sum_bypass': rf is None,
                                'output_sum_awg': awg_name, 'output_sum_rf': rf_name,
                                'output_sum_awg_delay_cycles': 13,
                                'post_output_latency_cycles': 2}})
    manifest = {'timing': {'timing_closed': 'YES', 'setup_wns_ns': '0.028000',
                           'setup_tns_ns': '0.000000', 'hold_whs_ns': '0.009357',
                           'hold_ths_ns': '0.000000'},
                'topology': {'passed': True, 'pairs': pairs},
                'xsa_members': {'bit': 'bitstream.bit', 'hwh': 'd_1.hwh'}}
    manifest_path = folder / 'build_manifest.json'

    def save(*, xml=False, zip_hwh=None, extra_members=None):
        if xml:
            hwh.write_bytes(ET.tostring(root, encoding='utf-8', xml_declaration=True))
        with zipfile.ZipFile(xsa, 'w') as archive:
            archive.write(bit, 'bitstream.bit')
            archive.writestr('d_1.hwh', hwh.read_bytes() if zip_hwh is None else zip_hwh)
            for name, contents in extra_members or []:
                archive.writestr(name, contents)
        manifest['artifacts'] = [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': update.sha(p)}
                                 for p in (bit, hwh, xsa)]
        manifest['topology']['sha256'] = update.sha(hwh)
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

    def write_manifest():
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

    def review():
        return update.review_package(repo, active_firmware='projects/qstl_awg_v5/bitstream.bit')

    def module(name):
        return next(m for m in root.iter('MODULE') if m.get('INSTANCE') == name)

    monkeypatch.setattr(update.importlib.util, 'find_spec',
                        lambda _: SimpleNamespace(origin=str(installed / '__init__.py')))
    monkeypatch.setattr(update.BoardUpdater, '__enter__', lambda _: pytest.fail('Network forbidden'))
    save()
    return SimpleNamespace(repo=repo, folder=folder, bit=bit, hwh=hwh, xsa=xsa, root=root,
                           manifest=manifest, manifest_path=manifest_path, save=save,
                           write_manifest=write_manifest, review=review, module=module)


def test_actual_hwh_review_is_read_only_with_fake_bit_and_xsa(package):
    p = package
    before = {str(f): f.read_bytes() for f in p.repo.rglob('*') if f.is_file()}
    reviewed = p.review()
    assert reviewed['manifest']['firmware_validation'] == 'build_manifest_and_xsa'
    assert reviewed['manifest']['v5_hardware_validation'] == {
        'passed': True, 'output_sum_blocks': 7, 'output_sum_version': 2,
        'awg_delay_cycles': 13, 'pipeline_cycles': 2, 'clock_hz': 300000000,
        'dc_area_bits': 48, 'hwh_sha256': update.sha(p.hwh)}
    assert len(reviewed['manifest']['generators']) == 10
    assert reviewed['setup_wns_ns'] == '0.028000'
    assert before == {str(f): f.read_bytes() for f in p.repo.rglob('*') if f.is_file()}


def test_v5_without_manifest_is_refused(package):
    package.manifest_path.unlink()
    with pytest.raises(ValueError, match='validated v5 build_manifest'):
        package.review()


def test_candidate_artifact_dictionary_is_not_a_deployment_manifest(package):
    p = package
    p.manifest['artifacts'] = {Path(v['path']).name: v for v in p.manifest['artifacts']}
    p.write_manifest()
    with pytest.raises(ValueError, match='candidate_manifest'):
        p.review()


def test_explicit_candidate_filename_is_not_accepted(package):
    p = package
    candidate = p.folder / 'candidate_manifest.json'
    candidate.write_bytes(p.manifest_path.read_bytes())
    with pytest.raises(ValueError, match='candidate_manifest'):
        update.review_package(p.repo, candidate, active_firmware='projects/qstl_awg_v5/bitstream.bit')


def test_v5_hwh_cannot_bypass_guard_with_legacy_folder_name(package):
    p = package
    p.manifest_path.unlink()
    p.folder.rename(p.folder.with_name('renamed_legacy'))
    with pytest.raises(ValueError, match='validated v5 build_manifest'):
        update.review_package(p.repo, active_firmware='projects/renamed_legacy/bitstream.bit')


@pytest.mark.parametrize('key,value', [('timing_closed', 'NO'), ('setup_wns_ns', '-0.001'),
    ('setup_tns_ns', '-0.1'), ('hold_whs_ns', '-0.001'), ('hold_ths_ns', '0.01'),
    ('setup_wns_ns', 'NaN'), ('hold_whs_ns', 'Infinity'), ('hold_whs_ns', None)])
def test_failed_or_nonfinite_timing_is_refused(package, key, value):
    package.manifest['timing'][key] = value
    package.write_manifest()
    with pytest.raises(ValueError, match='timing'):
        package.review()


def test_missing_timing_metric_is_refused(package):
    del package.manifest['timing']['setup_wns_ns']
    package.write_manifest()
    with pytest.raises(ValueError, match='timing metric'):
        package.review()


@pytest.mark.parametrize('name,value', [('AWG_DELAY_CYCLES', '12'), ('PIPELINE_CYCLES', '3'),
                                     ('N_PTS', '8'), ('BYPASS', '1')])
def test_rehashed_hwh_invalid_sum_parameter_is_refused(package, name, value):
    package.module('axis_output_sum_4').find("./PARAMETERS/PARAMETER[@NAME='%s']" % name).set('VALUE', value)
    package.save(xml=True)
    with pytest.raises(ValueError, match=name):
        package.review()


@pytest.mark.parametrize('mutation', ['v1', 'missing', 'extra', 'duplicate', 'area', 'clock', 'clock_net',
                                    'rf_clock', 'zero', 'awg_link', 'rf_link', 'slice_link', 'dac_link'])
def test_rehashed_hwh_invalid_topology_is_refused(package, mutation):
    p = package
    output = p.module('axis_output_sum_4')
    if mutation == 'v1':
        output.set('MODTYPE', 'axis_output_sum_v1')
    elif mutation == 'missing':
        output.set('MODTYPE', 'missing')
    elif mutation in ('extra', 'duplicate'):
        extra = copy.deepcopy(output)
        if mutation == 'extra':
            extra.set('INSTANCE', 'unexpected_sum')
        next(n for n in p.root.iter() if output in list(n)).append(extra)
    elif mutation == 'area':
        p.module('axis_awg_tuning_v3_4').find("./PARAMETERS/PARAMETER[@NAME='DC_AREA_BITS']").set('VALUE', '32')
    elif mutation in ('clock', 'clock_net', 'rf_clock'):
        selected = p.module('axis_signal_gen_v6_0') if mutation == 'rf_clock' else output
        selected.find("./PORTS/PORT[@NAME='aclk']").set('SIGNAME' if mutation == 'clock_net' else 'CLKFREQUENCY',
                                                     'other_net' if mutation == 'clock_net' else '250000000')
    elif mutation == 'zero':
        p.module('sum_zero_word').find("./PARAMETERS/PARAMETER[@NAME='CONST_VAL']").set('VALUE', '1')
    else:
        selected, port = {'awg_link': (output, 's0_axis_tdata'), 'rf_link': (output, 's1_axis_tdata'),
                          'slice_link': (output, 'm_axis_tdata'),
                          'dac_link': (p.module('axis_register_slice_8'), 'm_axis_tdata')}[mutation]
        selected.find("./PORTS/PORT[@NAME='%s']/CONNECTIONS/CONNECTION" % port).set('INSTANCE', 'wrong_source')
    p.save(xml=True)
    with pytest.raises(ValueError, match='v5 firmware hardware'):
        p.review()


@pytest.mark.parametrize('mutation', ['passed', 'sha', 'count', 'duplicate', 'dac', 'rf', 'version', 'latency', 'bypass', 'delay', 'missing_delay'])
def test_manifest_topology_must_match_actual_hwh(package, mutation):
    top = package.manifest['topology']
    if mutation == 'passed':
        top['passed'] = False
    elif mutation == 'sha':
        top['sha256'] = '0' * 64
    elif mutation == 'count':
        top['pairs'].pop()
    elif mutation == 'duplicate':
        top['pairs'][-1] = copy.deepcopy(top['pairs'][0])
    elif mutation in ('dac', 'rf'):
        top['pairs'][0][mutation] = 'wrong'
    elif mutation == 'missing_delay':
        del top['pairs'][0]['route']['output_sum_awg_delay_cycles']
    else:
        key, value = {'version': ('output_sum_version', 1), 'latency': ('post_output_latency_cycles', 3),
                      'bypass': ('output_sum_bypass', 0), 'delay': ('output_sum_awg_delay_cycles', 12)}[mutation]
        top['pairs'][0]['route'][key] = value
    package.write_manifest()
    with pytest.raises(ValueError, match='v5 firmware hardware'):
        package.review()


def test_manifest_cannot_match_unrecorded_hwh_member(package):
    p = package
    p.save(zip_hwh=b'<SYSTEM TIMESTAMP="wrong"/>', extra_members=[('other.hwh', p.hwh.read_bytes())])
    with pytest.raises(ValueError, match='not the pair'):
        p.review()


def test_duplicate_named_xsa_member_is_refused(package):
    with pytest.warns(UserWarning, match='Duplicate name'):
        package.save(extra_members=[('d_1.hwh', package.hwh.read_bytes())])
    with pytest.raises(ValueError, match='ambiguous v5 XSA member'):
        package.review()


@pytest.mark.parametrize('mutation', ['missing_member', 'missing_record', 'duplicate_record', 'tampered_bit', 'wrong_size'])
def test_artifact_contract_is_required(package, mutation):
    p = package
    if mutation == 'missing_member':
        p.manifest['xsa_members']['hwh'] = 'missing.hwh'
    elif mutation == 'missing_record':
        p.manifest['artifacts'].pop()
    elif mutation == 'duplicate_record':
        p.manifest['artifacts'].append(copy.deepcopy(p.manifest['artifacts'][0]))
    elif mutation == 'tampered_bit':
        p.bit.write_bytes(b'CHANGED')
    else:
        p.manifest['artifacts'][0]['bytes'] += 1
    p.write_manifest()
    with pytest.raises(ValueError):
        p.review()


def test_v5_manifest_accepts_utf8_bom_and_uppercase_sha(package):
    p = package
    for record in p.manifest['artifacts']:
        record['sha256'] = record['sha256'].upper()
    p.manifest_path.write_text(json.dumps(p.manifest), encoding='utf-8-sig')
    assert p.review()['manifest']['v5_hardware_validation']['passed']
