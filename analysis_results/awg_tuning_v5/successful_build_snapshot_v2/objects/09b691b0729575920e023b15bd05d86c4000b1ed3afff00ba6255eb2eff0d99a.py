"""IQ64 metadata, integer persistence and legacy-scale analysis regression."""
import numpy as np
import pytest
from fir_ddr_profile import resolve_fir_ddr_profile, iq_in_input_units
from ddr_memory_usage import calculate_ddr_capture_memory_usage
from qick_fine_tune_sweep import FineTuneDdrResult
from qick_sparameter_sweep import SParameterSweepResult, SParameterPowerSweepResult


def iq64_config():
    return {'ddr4_buf': dict(sample_capture=True, fir_enabled=True,
        stored_sample_rate_hz=1e6, fir_rate_profile='1_msps', fir_decimation=300,
        fir_input_fs_mhz=300, fir_group_delay_input_samples=8677,
        supports_trigger_delay=True, decimation_phase_continuous=True,
        trigger_delay_units='s_axis_aclk_cycles', trigger_delay_default_cycles=8712,
        iq_component_bits=64, iq_scale_log2=46, iq_format_version=1,
        iq_sample_bytes=16, s_axis_data_width=128, samples_per_axi_word=2)}


def test_auto_detect_width_delay_and_unknown_format():
    cfg = iq64_config()
    p = resolve_fir_ddr_profile(cfg)
    assert p.iq_component_bits == 64 and p.iq_sample_bytes == 16
    assert p.uses_fpga_trigger_delay and not p.software_warmup_compensation
    assert p.trigger_delay_us == pytest.approx(29.04)
    assert p.trigger_delay_arm_kwargs() == {'trigger_delay_cycles': 8712}
    assert 'signed int64' in p.timing_label
    for field, value in [('iq_format_version', 2), ('iq_scale_log2', 0), ('iq_sample_bytes', 4)]:
        bad = iq64_config(); bad['ddr4_buf'][field] = value
        with pytest.raises(RuntimeError): resolve_fir_ddr_profile(bad)
    bad=iq64_config(); del bad['ddr4_buf']['iq_component_bits']
    with pytest.raises(RuntimeError): resolve_fir_ddr_profile(bad)


def test_odd_capture_accounting_uses_16_bytes_per_iq():
    usage=calculate_ddr_capture_memory_usage(sweep_points=2,repetitions=3,
        samples_per_trigger=13,samples_per_axi_word=2,iq_sample_bytes=16,
        capacity_words_32b=1000)
    assert usage.physical_words_per_trigger == 56
    assert usage.valid_data_bytes == 6*13*16
    assert usage.reserved_bytes == 6*7*32
    assert usage.padding_bytes == 6*16


def test_raw_integer_retained_and_means_do_not_overflow():
    # Values > 2^53 with nonzero low bits expose accidental float conversion.
    raw=np.array([2**62+3,-2**62-7,2**62+5,-2**62-9],dtype=np.int64).reshape(1,2,1,2)
    result=FineTuneDdrResult(np.array([0]),raw,iq_scale_log2=46,iq_component_bits=64)
    np.testing.assert_array_equal(result.iq,raw)
    assert result.iq.dtype == np.int64
    np.testing.assert_allclose(result.mean_iq,[[[65536,-65536]]])
    weak=np.array([[-23221685578629,2111062325329]],dtype=np.int64)
    np.testing.assert_allclose(iq_in_input_units(weak,46),[[-.33,.03]],atol=1e-13)
    with pytest.raises(RuntimeError): iq_in_input_units(weak.astype(float),46)


def test_sparameter_scaling_and_power_stack():
    raw=np.array([[[3*2**46,4*2**46]]],dtype=np.int64)
    r=SParameterSweepResult.from_iq([190],[190],raw,iq_scale_log2=46)
    assert r.iq_traces.dtype == np.int64
    np.testing.assert_array_equal(r.iq_traces,raw)
    assert r.mean_i[0] == 3 and r.mean_q[0] == 4
    assert r.adc_magnitude_db[0] == pytest.approx(20*np.log10(5))
    stacked=SParameterPowerSweepResult.from_sweeps([100,200],[r,r])
    assert stacked.iq_scale_log2==46
    np.testing.assert_array_equal(stacked.mean_i,[[3],[3]])


@pytest.mark.parametrize('power_sweep', [False, True])
def test_legacy_sparameter_positional_constructor_keeps_argument_order(power_sweep):
    # Call using the positional argument order published before IQ64 support.
    trace = np.array([[[3, 4]]], dtype=np.int16)
    single = SParameterSweepResult.from_iq([190], [190], trace,
        reserved_physical_words=128, acquisition_source='avg_buffer',
        integration_time_us=2.5, accumulation_repetitions=7)
    common = ('requested_frequencies_mhz', 'frequencies_mhz', 'iq_traces',
              'mean_i', 'mean_q', 'adc_magnitude_db', 'magnitude_db',
              'phase_unwrapped_deg', 'sample_rate_hz', 'reserved_physical_words')
    suffix = ('frequency_gain_codes', 'actual_output_powers_dbm',
              'input_powers_dbm', 'acquisition_source', 'integration_time_us',
              'accumulation_repetitions')
    if power_sweep:
        source = SParameterPowerSweepResult.from_sweeps([100], [single])
        names = ('power_gains',) + common + ('output_powers_dbm',) + suffix
    else:
        source = single
        names = common + ('output_power_dbm', 'nominal_gain_code') + suffix
    restored = type(source)(*(getattr(source, name) for name in names))
    assert restored.reserved_physical_words == source.reserved_physical_words
    assert restored.acquisition_source == 'avg_buffer'
    assert restored.integration_time_us == 2.5
    assert restored.accumulation_repetitions == 7
    assert restored.iq_scale_log2 == 0
    np.testing.assert_array_equal(restored.iq_traces, source.iq_traces)


@pytest.mark.parametrize('storage_mode', ['full_traces', 'mean_iq'])
@pytest.mark.parametrize('swept', [False, True])
def test_qcodes_roundtrip_honors_mean_only_and_preserves_full_trace_low_bits(tmp_path, monkeypatch, storage_mode, swept):
    from qick_qcodes_experiment import (store_qick_result, QcodesRunConfig,
        QickConnectionConfig, load_qick_raw_int64_arrays, load_qick_iq_arrays,
        QCODES_STAGING_ENV)
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path/'staging'))
    raw=np.array([2**62+3,-2**62-7,2**62+5,-2**62-9],dtype=np.int64).reshape(1,2,1,2)
    result=FineTuneDdrResult(np.array([0]),raw,iq_scale_log2=46,iq_component_bits=64)
    if swept:
        from dataclasses import replace
        from test_qick_qcodes_experiment import _ddr_result
        template = _ddr_result()
        raw = np.arange(template.iq.size, dtype=np.int64).reshape(template.iq.shape) + 2**62 + 3
        raw[..., 1] *= -1
        result = replace(template, iq=raw, iq_scale_log2=46, iq_component_bits=64)
    dataset,row_count=store_qick_result(result,run_config=QcodesRunConfig(str(tmp_path/'iq64.db')),
        connection_config=QickConnectionConfig('192.0.2.1',8888,'mock'),
        program_summary={},gui_settings={},rf_settings={},iq_storage_mode=storage_mode)
    loaded=load_qick_iq_arrays(dataset)
    layout = loaded['metadata']['measurement_layout']
    parameters = set(dataset.paramspecs)
    if storage_mode == 'mean_iq':
        assert {'i_mean', 'q_mean'} <= parameters
        assert not parameters.intersection({
            'i_trace', 'q_trace', 'i_raw_int64', 'q_raw_int64',
            'sample_index', 'repetition_index',
        })
        assert row_count == raw.shape[0]
        assert dataset.number_of_results == 2 * raw.shape[0]
        assert layout['raw_iq_parameters'] == []
        assert layout['raw_iq_storage'] == 'omitted_mean_iq'
    else:
        assert {'i_trace', 'q_trace', 'i_raw_int64', 'q_raw_int64'} <= parameters
        assert layout['raw_iq_storage'] == 'exact_int64_arrays'
        np.testing.assert_array_equal(load_qick_raw_int64_arrays(dataset,shape=raw.shape),raw)
    # Normalized traces remain on the established calibration scale.
    assert np.max(np.abs(loaded['iq'])) < 65537
    expected = np.ldexp(raw.astype(np.float64), -46)
    if storage_mode == 'mean_iq':
        expected = expected.mean(axis=(1, 2), keepdims=True)
    np.testing.assert_allclose(loaded['iq'], expected)


def test_sparameter_int64_database_roundtrip(tmp_path, monkeypatch):
    from qick_sparameter_sweep import store_sparameter_result, load_sparameter_run, SParameterSweepConfig
    from qick_qcodes_experiment import QcodesRunConfig, QickConnectionConfig, QCODES_STAGING_ENV
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path/'staging'))
    raw=np.array([[[2**62+3,-2**62-7]],[[3*2**46+5,4*2**46+1]]],dtype=np.int64)
    result=SParameterSweepResult.from_iq([189,190],[189,190],raw,iq_scale_log2=46)
    path=tmp_path/'sparameter64.db'
    dataset,_=store_sparameter_result(result,config=SParameterSweepConfig(frequency_points=2),
        connection_config=QickConnectionConfig('192.0.2.1'),run_config=QcodesRunConfig(str(path)),
        program_summary={},rf_settings={})
    loaded=load_sparameter_run(path,dataset.run_id).result
    assert loaded.iq_scale_log2==46
    np.testing.assert_array_equal(loaded.iq_traces,raw)
    np.testing.assert_array_equal(loaded.mean_i,result.mean_i)


@pytest.mark.parametrize('scale', [0, 46])
def test_live_power_sweep_preserves_integer_data_and_legacy_units(tmp_path, monkeypatch, scale):
    import qick_sparameter_sweep as module
    from test_qick_sparameter_sweep import _config
    from qick_qcodes_experiment import QcodesRunConfig, QickConnectionConfig, QCODES_STAGING_ENV
    monkeypatch.setenv(QCODES_STAGING_ENV, str(tmp_path/'staging'))
    config = _config(frequency_points=2, scan_time_us=4, power_sweep_enabled=True,
                     power_start_gain=100, power_end_gain=200, power_points=2,
                     settle_seconds=0)
    expected = []
    class FakeProgram:
        def __init__(self, point_config):
            self.config = point_config
        def acquire_iq(self, soc, counter_progress=None):
            raw = np.arange(16, dtype=np.int64).reshape(2, 4, 2) + self.config.gain
            if scale:
                raw += 2**62 + 3
            else:
                raw = raw.astype(np.int16)
            raw[..., 1] *= -1
            expected.append(raw)
            return SParameterSweepResult.from_iq(
                self.config.requested_frequencies_mhz, self.config.requested_frequencies_mhz,
                raw, iq_scale_log2=scale)
        def summary(self):
            return {'gain': self.config.gain}
    monkeypatch.setattr(module, 'configure_sparameter_rf_board', lambda *a: {'output': {}, 'readout': {}})
    monkeypatch.setattr(module, 'build_sparameter_program', lambda cfg, point, **k: FakeProgram(point))
    path = tmp_path/'power.db'
    stored = module.run_sparameter_sweep(connection_config=QickConnectionConfig('192.0.2.1'),
        run_config=QcodesRunConfig(str(path)), sweep_config=config,
        connector=lambda **k: (object(), {'ddr4_buf': {'iq_scale_log2': scale}}))
    loaded = module.load_sparameter_run(path, stored.run_id).result
    assert loaded.iq_scale_log2 == scale
    np.testing.assert_array_equal(loaded.iq_traces, np.stack(expected))
    from qcodes import load_by_id
    dataset = load_by_id(stored.run_id)
    assert dataset.paramspecs['i_trace'].unit == ('stored int64 codes' if scale else 'ADC units')


def test_sparameter_acquisition_detects_iq64_and_byte_address(monkeypatch):
    from test_qick_sparameter_sweep import _mock_soccfg, _config
    from qick_sparameter_sweep import SParameterSweepProgram
    cfg=_mock_soccfg(); cfg['ddr4_buf'].update(iq64_config()['ddr4_buf'])
    program=SParameterSweepProgram(cfg,_config(frequency_points=3,scan_time_us=4,address=32))
    raw=np.full((12,2),3*2**46+7,dtype=np.int64)
    class FakeSoc:
        def arm_ddr4_fir_samples(self,**kwargs): self.arm=kwargs; return 48
        def get_ddr4_fir_samples(self,**kwargs): self.read=kwargs; return raw
    soc=FakeSoc()
    monkeypatch.setattr(program,'run_rounds',lambda *a,**k:None)
    result=program.acquire_fir_ddr(soc)
    assert soc.arm['trigger_delay_cycles']==8712
    assert soc.read['start']==8
    assert result.iq_scale_log2==46
    np.testing.assert_array_equal(result.iq_traces.reshape(12,2),raw)
    np.testing.assert_allclose(result.mean_i,3)


def test_awg_iq64_chunk_offsets_preserve_raw_low_bits(monkeypatch):
    from test_qick_fine_tune_sweep import _fir_soccfg
    from qick_fine_tune_sweep import FineTuneSequence, DdrFirReadoutConfig
    cfg=_fir_soccfg(); cfg['ddr4_buf'].update(iq64_config()['ddr4_buf'])
    sequence=FineTuneSequence(('awg_0',))
    sequence.add_set('capture',(0.,),300)
    sequence.set_amplitude_sweep('capture','awg_0',-.2,.2,3)
    program=sequence.make_program(cfg,awg_channels=(0,),repetitions_per_sweep=2,
        ddr_readout=DdrFirReadoutConfig(ro_ch=0,samples_per_trigger=13,
        at_segment='capture',margin_input_samples=0,address=128,settle_seconds=0))
    class FakeSoc:
        def __init__(self): self.read_calls=[]
        def arm_ddr4_fir_samples(self,**kwargs): self.arm=kwargs; return 6*56
        def get_ddr4_fir_samples(self,**kwargs):
            self.read_calls.append(kwargs)
            first=(kwargs['start']-32)//56
            return np.array([[(2**62+first+k+3),(-2**62-first-k-7)]
                for k in range(kwargs['n_triggers']) for _ in range(13)],dtype=np.int64)
    soc=FakeSoc(); monkeypatch.setattr(program,'run_rounds',lambda *a,**k:None)
    result=program.acquire_fir_ddr(soc,readback_chunk_triggers=4)
    assert soc.arm['trigger_delay_cycles']==8712
    assert [(r['start'],r['n_triggers']) for r in soc.read_calls]==[(32,4),(256,2)]
    assert result.iq_scale_log2==46 and result.iq.dtype==np.int64
    np.testing.assert_array_equal(result.iq[:,:,0,0].ravel(),np.arange(6,dtype=np.int64)+2**62+3)
