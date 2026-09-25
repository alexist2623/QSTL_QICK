"""Compile the production GUI exporter, not a hand-written stimulus sequence."""
import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'qstl_awg_tuning_fir_1msps_iq64_sq_pulse'
CASES = ('gui_sweep', 'gui_500us', 'gui_autonomy', 'gui_frequency',
         'gui_awg_repeat', 'gui_awg_capture_repeat')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gui', type=Path, required=True)
    parser.add_argument('--case', choices=CASES)
    args = parser.parse_args()
    sys.path.insert(0, str(args.gui / 'DCWaveformGeneratorGUI'))
    from qick.sim import QickSim, topology
    from qick.square_pulse import AxisSquarePulseV1
    from qick.drivers.readout import AxisBufferDdrSampleV3
    from qick.awg_tuning import TProcV1BehaviorModel
    from dc_waveform_core import (PulseSequence, QickRfPulseSpec, QickSweepSpec,
                                 QickRampRateSweepSpec, QickHoldDurationSweepSpec,
                                 QickDdrReadoutSpec, generate_qick_program_code)
    import numpy as np

    # Use real HWH driver discovery; only stand-in MMIO identity/capacity is
    # supplied here. QickSim is NOT the simulation DUT.
    previous = topology._iter_driver_classes
    def classes():
        yield from previous()
        yield AxisSquarePulseV1
    topology._iter_driver_classes = classes
    original = AxisBufferDdrSampleV3._init_firmware
    def initialize(self):
        self.mmio.array[10:14] = [0x5149434b, 1, 64, 46]
        original(self)
    AxisBufferDdrSampleV3._init_firmware = initialize
    soc = QickSim(BASE/'bitstream.bit', clocks={
        'default_dac': dict(fs=4800, fabric=300, interpolation=1, fs_mult=16),
        'default_adc': dict(fs=2400, fabric=300, decimation=1, fs_mult=8),
    }, strict=False, board='ZCU216')
    soc._cfg['refclk_freq'] = 300.0
    # QickSim's per-channel clock overrides do not update its RF tile cache.
    # Keep only connected converter channels, and record their tile metadata
    # from the source HWH. This describes GUI firmware discovery; the RTL DUT
    # still has no RFDC instance and uses the digital boundary BFM instead.
    rfdc=next(m for m in ET.parse(BASE/'bitstream.hwh').findall('.//MODULE')
              if m.get('MODTYPE')=='usp_rf_data_converter')
    rf_params={p.get('NAME'):p.get('VALUE') for p in rfdc.findall('./PARAMETERS/PARAMETER')}
    for kind,entries in [('dac',soc._cfg['gens']),('adc',soc._cfg['readouts'])]:
        connected={entry[kind] for entry in entries}
        soc._cfg['rf'][kind+'s']={key:value for key,value in soc._cfg['rf'][kind+'s'].items() if key in connected}
        soc._cfg['rf']['tiles'][kind]={tile:{
            'f_ref':float(rf_params[f'{kind.upper()}{tile}_Refclk_Freq']),
            'f_out':float(rf_params[f'{kind.upper()}{tile}_Outclk_Freq']),
            'fs':1000*float(rf_params[f'{kind.upper()}{tile}_Sampling_Rate'])}
            for tile in sorted({key[0] for key in connected})}
    soc._cfg['tprocs'][0]['pmem_size'] = 8192
    soc._cfg['ddr4_buf']['maxlen'] = 65536  # BFM capacity, not physical DDR size.
    (HERE/'soccfg.json').write_text(json.dumps(soc._cfg, indent=2)+'\n')
    provenance = {}
    for name in ('dc_waveform_core.py', 'qick_fine_tune_sweep.py', 'qick_square_dds.py'):
        path = args.gui/'DCWaveformGeneratorGUI'/name
        provenance[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (HERE/'gui_sources.json').write_text(json.dumps(provenance, indent=2)+'\n')

    for case in CASES:
        if args.case and case!=args.case:continue
        directory = HERE/case
        directory.mkdir(exist_ok=True)
        slow = case in ('gui_500us', 'gui_autonomy')
        hold = 325000 if case=='gui_500us' else 650000 if slow else 45000
        pulse = PulseSequence()
        pulse.t = np.array([0, hold, hold+500, hold+10000], dtype=float)
        pulse.v = np.array([10, 10, -5, -5], dtype=float)
        pulse.segment_names = ['measure', 'tail']
        square = dict(enabled=True, gen_ch=7, parameters={
            'frequency': dict(value=.002 if slow else .04, sweep=not slow,
                              start=.002 if slow else .04, stop=.004 if slow else .08, count=2),
            'amplitude': dict(value=20., sweep=case!='gui_frequency', start=20., stop=40., count=2),
            'phase': dict(value=270. if slow else 0., sweep=case=='gui_sweep',
                          start=0., stop=90., count=2),
        })
        if case == 'gui_autonomy':
            square = dict(enabled=False)
        trigger = dict(enabled=True, pin=0, scope='experiment' if slow else 'loop',
                       edge='both', width_us=.37)
        rf = QickRfPulseSpec(6, 'set_0', 3., 5., 190., 2000, 0., 0.)
        capture = QickDdrReadoutSpec(0, 'set_0', 2., 8, 190., margin_input_samples=0)
        repetitions = 1
        sweeps = ()
        awg_request = None
        if case in ('gui_awg_repeat', 'gui_awg_capture_repeat'):
            fast = case == 'gui_awg_repeat'
            repetitions = 3 if fast else 2
            pulse.t = np.array([0, 1500, 2000, 3000] if fast else
                               [0, 45000, 45500, 55000], dtype=float)
            pulse.v = np.array([-10, -10, 5, 5], dtype=float)
            sweeps = (QickSweepSpec('set_0', 'awg_0', -10/800, 10/800, 3 if fast else 2),)
            if fast:
                sweeps += (QickHoldDurationSweepSpec('set_0', 1.5, 2.5, 2),
                           QickRampRateSweepSpec('ramp_0_to_1', .5, 1., 2))
                rf = QickRfPulseSpec(6, 'set_0', .3, .5, 190., 2000, 0., 0.)
                capture = None
            square = dict(enabled=True, gen_ch=7, parameters={
                'frequency': dict(value=.04, sweep=False),
                'amplitude': dict(value=20., sweep=False),
                'phase': dict(value=0., sweep=False),
            })
            trigger = dict(enabled=True, pin=0, scope='loop', edge='both', width_us=.37)
            awg_request = dict(amplitude_mv=[-10., 0., 10.] if fast else [-10., 10.],
                               hold_us=[1.5, 2.5] if fast else [45.],
                               ramp_us=[.5, 1.] if fast else [.5],
                               tail_mv=5., tail_us=1. if fast else 9.5,
                               full_scale_mv=800., repetitions=repetitions,
                               axis_order=['ramp_us', 'hold_us', 'amplitude_mv'])
        code = generate_qick_program_code([pulse], awg_channels=(1,),
            fabric_mhz=300., tproc_mhz=300., full_scale_mv=800.,
            repetitions_per_sweep=repetitions, sweeps=sweeps,
            rf_pulse_specs=[rf], ddr_readout_spec=capture,
            square_pulse_settings=square, output_trigger_settings=trigger)
        (directory/'gui_export.py').write_text(code, encoding='utf-8')
        namespace = {'__name__': 'gui_export'}
        exec(compile(code, str(directory/'gui_export.py'), 'exec'), namespace)
        program = namespace['build_program'](soc)
        program.compile()
        words = program.binprog
        assert len(words) <= 8192
        # END padding makes an unintended fetch deterministic, not X data.
        (directory/'pmem.hex').write_text(''.join(f'{int(w):016x}\n' for w in words))
        (directory/'program.asm').write_text(program.asm())
        dmem = {int(program._runtime_dmem_base)+i: int(v)&0xffffffff
                for i,v in enumerate(program._runtime_dmem_words)}
        (directory/'dmem.txt').write_text(''.join(f'{a:08x} {w:08x}\n' for a,w in dmem.items()))
        model = TProcV1BehaviorModel(strict=True)
        program.load_runtime_dmem_into_model(model)
        model.run(program)
        events = [dict(cycle=e.cycle, port=e.tproc_ch, word=f'{e.word:040x}', kind='axis')
                  for e in model.output_events]
        events += [dict(cycle=e['cycle'], port=e['port'], word=f'{e["word"]:040x}', kind=e['kind'])
                   for e in model.output_pin_events]
        events.sort(key=lambda e: (e['cycle'], e['port']))
        meta = dict(case=case, square=square, trigger=trigger, rf=dataclasses.asdict(rf),
                    capture=dataclasses.asdict(capture) if capture else None, pmem_words=len(words),
                    dmem_words=len(dmem), events=events,
                    stop_cycle=max(e['cycle'] for e in events)+3000,
                    model_conflicts=[dataclasses.asdict(c) for c in model.timing_conflicts])
        if awg_request is not None:
            meta['awg_request'] = awg_request
            meta['repetitions_per_sweep'] = repetitions
            (directory/'gui_sources.json').write_text(json.dumps(provenance, indent=2)+'\n')
        (directory/'expected.json').write_text(json.dumps(meta, indent=2)+'\n')
        print(case, len(words), 'instructions,', len(events), 'events,',meta['stop_cycle'],'cycles')
        if case == 'gui_autonomy':
            from qick import QickProgram
            seed = QickProgram(soc)
            seed.declare_gen(ch=7)
            seed.set_pulse_registers(ch=7, style='square', freq=1790,
                                    phase=0, gain=1228, enable=True, reset_phase=False)
            seed.synci(256)
            seed.pulse(ch=7,t=0)
            seed.waiti(0,300)
            seed.end()
            seed.compile()
            (directory/'seed_pmem.hex').write_text(''.join(f'{int(w):016x}\n' for w in seed.binprog))
            (directory/'seed_program.asm').write_text(seed.asm())
    # Exact integer samples at the RFDC/PL input boundary, 190 MHz / 2.4 GHz.
    samples = np.rint(1000*np.cos(2*np.pi*19*np.arange(240)/240)).astype(int)
    (HERE/'adc190.hex').write_text(''.join(f'{sum((int(s)&0xffff) << (16*i) for i,s in enumerate(samples[k:k+8])):032x}\n' for k in range(0,240,8)))


if __name__ == '__main__':
    main()
