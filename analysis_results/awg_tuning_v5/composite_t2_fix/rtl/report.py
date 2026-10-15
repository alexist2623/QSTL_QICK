"""Summarize completed new-input RTL checks and plot their measured RF windows."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    state = json.loads((HERE / 'status.json').read_text())
    proof = json.loads((HERE / 'final_source_input_equivalence_named.json').read_text())
    extra = json.loads((HERE / 'hahn_status.json').read_text())
    carrier = json.loads((HERE / 'carrier_checks.json').read_text())
    guard = json.loads((HERE / 'calibration_guard.json').read_text())
    assert state['complete'] and state['stage'] == 'passed' and len(state['cases']) == 6
    assert proof['passed'] and len(proof['cases']) == 6
    assert extra['complete'] and extra['stage'] == 'passed' and len(extra['cases']) == 1
    assert carrier['passed'] and len(carrier['cases']) == 7
    assert guard['passed'] and guard['expected_rejection'] and not guard['simulation_run']
    for path, expected in proof['source_hashes'].items():
        assert sha(path) == expected, ('source changed', path)
    manual_prepared = json.loads((HERE/'hahn_manual_prepared.json').read_text())
    for record in (manual_prepared, guard):
        for path, expected in record['source_hashes'].items():
            assert sha(path) == expected, ('extra-case source changed', path)
    for record in (*state['cases'], *extra['cases']):
        for path, expected in record['evidence_hashes'].items():
            assert sha(path) == expected, ('RTL evidence changed', path)
    fig, axes = plt.subplots(4, 1, figsize=(11, 8), sharex=True, constrained_layout=True)
    for ax, index in zip(axes, (0, 1, 4, 5)):
        case = state['cases'][index]
        out = Path(case['case'])
        blocks = case['rf_checks'][0]['blocks'][:3]
        origin = blocks[0][0]
        t, envelope = [], []
        with (out / 'physical_4.csv').open() as stream:
            for row in csv.DictReader(stream):
                cycle = int(row['cycle'])
                if origin-30 <= cycle <= origin+2350:
                    word = int(row['rf'], 16)
                    lanes = [(word >> (16*lane)) & 0xffff for lane in range(16)]
                    lanes = [value-65536 if value >= 32768 else value for value in lanes]
                    t.append((cycle-origin)/300)
                    envelope.append(max(abs(value) for value in lanes))
        ax.step(t, envelope, where='post', color='#245e87', linewidth=1)
        ax.fill_between(t, envelope, step='post', color='#245e87', alpha=.18)
        ax.axhline(0, color='#666666', linewidth=.6)
        ax.set_ylim(-150, 2600)
        ax.set_ylabel('max |DDS code|')
        ax.set_title(f"tau = {case['tau_us']:g} us, pi = {case['pi_us']:g} us, pi/2 = {case['pi_us']/2:g} us", loc='left', fontsize=10)
        for name, (start, end) in zip(('pi/2', 'pi', 'pi/2'), blocks):
            ax.text(((start+end)/2-origin)/300, 2200, name, ha='center', fontsize=9)
        ax.grid(axis='x', color='#dddddd', linewidth=.5)
    axes[-1].set_xlabel('Time from initial pi/2 output [us]')
    axes[-1].set_xlim(-.1, 7.7)
    fig.suptitle('Actual v4 RTL: T2 composite RF output\nEnvelope of all 16 parallel DDS samples; first repetition, swept RF channel', fontsize=12)
    fig.savefig(HERE / 't2_tau_actual_rtl.png', dpi=160)
    plt.close(fig)
    case = extra['cases'][0]
    blocks = case['rf_checks'][0]['blocks'][:3]
    origin = blocks[0][0]
    time_us, envelope = [], []
    with (Path(case['case']) / 'physical_4.csv').open() as stream:
        for row in csv.DictReader(stream):
            cycle = int(row['cycle'])
            if origin-30 <= cycle <= blocks[-1][1]+30:
                word = int(row['rf'], 16)
                values = [(((word >> (16*lane)) & 65535)+32768)%65536-32768 for lane in range(16)]
                time_us.append((cycle-origin)/300.)
                envelope.append(max(abs(value) for value in values))
    fig, ax = plt.subplots(figsize=(11, 3.4), constrained_layout=True)
    ax.step(time_us, envelope, where='post', color='#245e87')
    ax.fill_between(time_us, envelope, step='post', color='#245e87', alpha=.18)
    for label, (start, end), align in zip(('pi/2: a0=1500, p0=0 deg', 'pi: a1=750, p1=90 deg',
                                  'pi/2: a0=1500, p0=0 deg'), blocks, ('left', 'center', 'right')):
        ax.text(((start+end)/2-origin)/300., 1650, label, ha=align, fontsize=8)
    ax.set_ylim(-100, 1900)
    ax.set_xlabel('Time from initial pi/2 output [us]')
    ax.set_ylabel('max |DDS code|')
    ax.set_title('Actual v4 RTL: GUI Hahn -> Custom, independent named amplitude/phase\npi=.4 us, tau total=4 us; each idle interval=2 us')
    ax.grid(axis='x', color='#dddddd', linewidth=.5)
    fig.savefig(HERE / 'named_hahn_actual_rtl.png', dpi=160)
    plt.close(fig)
    lines = ['# Composite T2 / named tau: fresh GUI-to-RTL results', '',
        'PASS. Six newly compiled tau x pi coordinates plus one Hahn-to-Custom named-amplitude/phase case executed in the existing v4 real tProcessor/TMUX/DDS/AWG/output-sum RTL. These are seven new simulation runs, not reused simulation PASS, and are not v5 synthesis results.', '',
        'Input path: actual MainWindow settings -> Run Experiment arguments -> existing runtime host-coordinate resolver -> QICK PMEM/DMEM. The executor is replaced only at the board-I/O boundary with real local compilation. No board connection or output was performed.', '',
        '| tau (us) | pi (us) | pi/2 (us) | Repetitions | RF paths checked | Commands | Result |',
        '|---:|---:|---:|---:|---:|---:|---|']
    bursts = 0
    for case in state['cases']:
        assert case['passed']
        lines.append(f"| {case['tau_us']:g} | {case['pi_us']:g} | {case['pi_us']/2:g} | 2 | 3 | {case['command_count']} | PASS |")
        bursts += sum(len(check['blocks']) for check in case['rf_checks'])
    manual = extra['cases'][0]
    bursts += sum(len(check['blocks']) for check in manual['rf_checks'])
    lines += ['', 'Additional actual GUI Hahn echo -> Custom case: tau total=4 us (2 us delay on each side), pi=.4 us, enabled pi/2=.2 us. Three RF paths x two repetitions passed. Endpoints use a0=1500 and p0=0 degrees; the body uses a1=750 and p1=90 degrees. Named table references remain independent after GUI preset conversion.']
    lines += ['', f'- {bursts} actual DDS bursts: every output width and relative onset matched the requested event timing exactly in fabric clocks.',
        '- The two delays share tau. RF generator 0 sweeps tau=1/2/3 us and pi=.2/.4 us. The other two summed RF paths keep tau=1 us and pi=.2 us and exercise the same enabled endpoint sequence.',
        '- All tProcessor command values and times match the instruction-model oracle; one constant testbench origin offset is removed. No scheduling tolerance was relaxed.',
        '- All three 16-lane output-sum saturation oracles passed. All three AWG DC-area engines completed both repetitions with residual area zero and cleared IIR history.',
        '- Independent fits of all actual DDS samples verify the requested carrier frequency, gain and relative phase offsets. Bounds are <2 signed DAC codes in fitted amplitude, <1.2 code RMS carrier residual, and <0.05 degree relative phase error. These account for integer DDS/multiply quantization; command timing, burst widths and onsets still require exact clock equality.',
        '- Final-source recompilation produced byte-identical PMEM, DMEM, assembly and expected commands plus identical emitted RF events for all six original cases. Added/default serialization fields are itemized separately; see final_source_input_equivalence_named.json. Previous source proofs are preserved.',
        '- Fresh v4 RTL was elaborated in an isolated copied simulation library. Existing v5 replay/build workflows and their libraries were not changed.', '',
        'Calibration: actual GUI Hahn-to-Custom settings with named dBm amplitudes were rejected as expected by all three v4 summed-output production guards and by the actual runtime host loop. No calibration RTL case was run on those outputs, and no guard was bypassed. Ordinary RF software/compiler/preview tests separately use a synthetic known database: -30/-10 dBm at 180 MHz resolve to exactly gain100/1000. This is validation of software calibration conversion, not measured board power.', '',
        'Initial preparation evidence: prepare_1.log/a5t2gui1 retains an over-broad dataclass-equality assertion failure (inactive delay gain normalized to zero and inactive Custom template duration choice normalized to the existing pi parameter), followed by Qt teardown access violation. Preparation 2 compares emitted RF events and both hardware/software axes exactly, records gui_normalization.json, and exits zero. No waveform/sweep tolerance was weakened.', '',
        'Scope: real digital RTL checks only. These checks validate command timing and RF pulse widths/relative spacing in the existing v4 implementation; they do not claim the separate v5 absolute AWG/DDS delay change or synthesis is complete. Board analog measurement and ADC/FIR arithmetic are not tested. The sum occurs after AWG IIR; added DDS area and clipping are not covered by AWG DC-area compensation.', '',
        '[Actual tau/pi RF waveform](t2_tau_actual_rtl.png) | [Named amplitude/phase RF waveform](named_hahn_actual_rtl.png) | [Execution status](status.json) | [Final source/input proof](final_source_input_equivalence_named.json) | [DDS carrier checks](carrier_checks.json) | [Expected calibration guard](calibration_guard.json)', '']
    (HERE / 'REPORT.md').write_text('\n'.join(lines), encoding='utf8')
    summary = dict(passed=True, cases=7, repetitions_per_case=2, rf_paths=3, actual_rf_bursts=bursts,
        command_mismatches=0, rf_width_mismatches=0, rf_relative_timing_mismatches=0,
        source_hashes_match=True, hardware_access=False, expected_calibration_guard_passed=True,
        calibration_actual_rtl_run=False,
        reports={name: sha(HERE/name) for name in ('REPORT.md','status.json','hahn_status.json',
          'final_source_input_equivalence_named.json','t2_tau_actual_rtl.png','named_hahn_actual_rtl.png',
          'carrier_checks.json','calibration_guard.json')})
    (HERE / 'result.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
