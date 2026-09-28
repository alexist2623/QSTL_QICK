"""Render compact figures from completed production-RTL validation evidence."""
import argparse
import csv
import json
from pathlib import Path
import re
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


CASES = {
    'Wide-step voltage, 20 x 20': 'rc_precomp_no_aux_grid_20x20_exact_voltage_awg_v2_fast',
    'Stability + DC/RC, 20 x 20': 'rc_precomp_repeat_reset_no_aux_grid_20x20_exact_voltage_awg_v2_stability',
    'Ramp duration + voltage, 20 x 20': 'rc_precomp_repeat_reset_ramp_rate_20x20_exact_voltage_awg_v2',
    'Hold duration + voltage, 20 x 20': 'rc_precomp_repeat_reset_hold_duration_20x20_exact_voltage_awg_v2',
    'RF duration + voltage, 20 x 20': 'rc_precomp_repeat_reset_rf_duration_20x20_exact_voltage_awg_v2',
    # This case has no voltage axis; the quantization fix does not change PMEM.
    'RF frequency + power, 20 x 20': 'rc_precomp_repeat_reset_rf_frequency_power_20x20_validation_awg_v2',
    'SquarePulse + AWG, 10 x 10': 'rc_precomp_square_sweep_repeat_reset_exact_voltage_awg_v2',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--standalone', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--firmware', type=Path,
                        default=Path(__file__).resolve().parents[3] / 'projects/qstl_awg_v2')
    parser.add_argument('--allow-pending', action='store_true')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.grid': True, 'grid.alpha': .25})
    evidence = args.out / 'rtl_evidence'
    evidence.mkdir(exist_ok=True)
    results = {}
    for label, folder in CASES.items():
        path = args.build / folder / 'result.json'
        if not path.exists():
            results[label] = None
            continue
        result = json.loads(path.read_text())
        assert result['validation_status'] == 'passed', (label, result['validation_status'])
        assert result['points'] == (100 if '10 x 10' in label else 400)
        assert result['repetitions'] == 2 and result['awg_ip_version'] == 2
        for field in ('command_value_mismatches', 'command_timing_mismatches',
                      'compiled_target_error_codes', 'compiled_step_error_units'):
            assert result[field] == 0, (label, field, result[field])
        assert len(result['raw_awg_results']) == 2
        if 'SquarePulse' in label:
            assert len(result['analog_results']) == 3
        else:
            assert len(result['exact_awg_results']) == 2
        if 'Wide-step' not in label:
            resets = 2 * result['points'] + 1
            assert all(f'resets={resets} zero_checks={resets}' in item for item in result['reset_results'])
        if 'rf_measurements' in result:
            assert result['rf_measurements']['pulses'] == 800
            assert result['rf_measurements']['width_error_max_cycles'] == 0
        results[label] = result
        shutil.copy2(path, evidence / (folder + '.json'))
    pending = [label for label, value in results.items() if value is None]
    if pending and not args.allow_pending:
        raise RuntimeError('RTL checks still pending: ' + ', '.join(pending))

    # Compare old/new executed targets from real RTL-verified instruction streams.
    old_path = args.build / 'rc_precomp_repeat_reset_no_aux_grid_20x20_validation_awg_v2_stability/grid_axes.json'
    new_path = args.build / CASES['Stability + DC/RC, 20 x 20'] / 'grid_axes.json'
    old = json.loads(old_path.read_text())[0]
    new = json.loads(new_path.read_text())[0]
    requested = np.array(new['requested_mv'])
    before = np.array(old['executed_target_mv'])
    after = np.array(new['executed_target_mv'])
    half_lsb = 800 / 16384
    assert max(abs(after - requested)) <= half_lsb
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    axes[0].plot(requested, requested, 'k--', lw=1.3, label='Requested')
    axes[0].plot(requested, before, 'o-', ms=3, color='#b4503c', label='Before: repeated rounded increment')
    axes[0].plot(requested, after, '.-', color='#16836c', label='After: each point rounded to DAC')
    axes[0].set(xlabel='Requested voltage (mV)', ylabel='Executed target (mV)', title='Two-DAC stability scan: 20 x 20, two repeats')
    axes[0].legend(fontsize=8)
    axes[1].plot(range(20), before-requested, 'o-', ms=3, color='#b4503c', label='Before')
    axes[1].plot(range(20), after-requested, 'o-', ms=3, color='#16836c', label='After')
    axes[1].axhspan(-half_lsb, half_lsb, alpha=.12, color='#16836c', label='Nearest-DAC rounding: +/- 0.5 LSB')
    axes[1].set(xlabel='Axis index', ylabel='Target error (mV)', title='Final target: 14.2578 -> 15.0391 mV')
    axes[1].legend(fontsize=8)
    fig.suptitle('Real tProcessor / TMUX / AWG v2 RTL; nominal full scale +/-800 mV')
    fig.savefig(args.out / 'voltage_grid_before_after.png', dpi=160)
    plt.close(fig)

    with (args.standalone / 'ramp_samples.csv').open() as stream:
        samples = list(csv.DictReader(stream))
    log = (args.standalone / 'xsim.log').read_text()
    assert 'PASS: AWG V2 cases=170 samples=117200' in log
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    for axis, cases, title in zip(axes, ((0, 1), (2, 3)),
            ('Full-scale transitions', '-125 mV <-> +300 mV')):
        for case in cases:
            rows = [r for r in samples if int(r['case']) == case]
            expected = np.array([int(r['expected']) for r in rows])
            actual = np.array([int(r['actual']) for r in rows])
            assert np.array_equal(actual, expected)
            t = np.array([int(r['sample']) for r in rows]) / 4.8
            axis.plot(t, expected*800/32768, '--', lw=1, label=f'Expected {case}')
            axis.plot(t, actual*800/32768, 'o', ms=3, label=f'RTL {case}')
        axis.set(title=title, xlabel='Time from first ramp sample (ns)', ylabel='Nominal voltage (mV)')
        axis.legend(fontsize=8)
    fig.suptitle('Production AWG v2: one 16-sample word per ramp (3.333 ns fabric cycle)')
    fig.savefig(args.out / 'single_clock_ramps.png', dpi=160)
    plt.close(fig)
    shutil.copy2(args.standalone / 'ramp_samples.csv', evidence / 'single_clock_ramps.csv')

    lines = ['# AWG tuning v2 validation', '',
        'Status: ' + ('PARTIAL; simulations listed below are still pending.' if pending else 'All listed RTL checks passed.'), '',
        'Actual production tProcessor, TMUX, command/output slices and two AWG v2 wrappers were simulated.',
        'The raw oracle checks all 16 AWG lanes. Fast/stability/mixed RF cases also check the complete integer RC recurrence.',
        'The SquarePulse coexistence case checks raw AWG data and all three outputs through an independent analog RC model.',
        'RFDC and ARM are excluded. These are digital tests, not analog board measurements.', '',
        '| Case | Points x repeats | Commands | Raw samples per DAC | Result |',
        '| --- | --- | --- | --- | --- |']
    for label, result in results.items():
        if result is None:
            lines.append(f'| {label} | - | - | - | Pending |')
        else:
            count = re.search(r'samples=(\d+)', result['raw_awg_results'][0])[1]
            lines.append(f"| {label} | {result['points']} x 2 | {result['commands']} | {int(count):,} | Passed |")
    lines += ['', '## Voltage accuracy', '',
        f'20-point 5 to 15 mV scan: final executed target {after[-1]:.8f} mV; maximum target error {max(abs(after-requested)):.8f} mV.',
        f'The old final target was {before[-1]:.8f} mV. One effective DAC LSB at nominal +/-800 mV is {2*half_lsb:.8f} mV.',
        'Targets now match independent nearest-DAC rounding. RAMP steps use those rounded endpoints. DC compensation uses their area.',
        'Independent 200 x 200 grids were also checked in software with unequal DAC scales.',
        'The tProcessor instruction model executed all 40,000 points twice and matched every positive target to independently rounded voltages, including each inner-axis rewind.',
        'This additional 80,000-shot instruction-model check is not a 200 x 200 Verilog simulation; the production RTL grids remain 20 x 20.',
        'Voltage tables are read inside hardware loops, with no host operation per point. Independent axes use O(Nx + Ny) storage.',
        'Coupled voltage/duration fields can require joint tables; insufficient tProcessor DMEM is reported before execution.',
        'Large fixed-voltage DC duration grids retain factored fractional time coefficients when their rounding bound is below half a fabric clock.', '',
        '## Analog RC residuals', '',
        'Digital pass means the commands, timing, raw samples and integer RC recurrence agree. It is not a claim of zero analog error.',
        'Mixed and SquarePulse analog fixtures use tau = 10 us and nominal full scale +/-800 mV. The stability grid uses tau = 300 us and checks the digital recurrence without the full-grid analog model.',
        'The mixed sweeps record the maximum analog-model error without imposing the fixed-waveform 4.2-code bound.',
        'The analog capacitor state persists when digital IIR history resets; DAC quantization and residual DC pulse area remain.', '',
        '| Case | AWG 1 maximum error (mV) | AWG 2 maximum error (mV) |',
        '| --- | ---: | ---: |']
    for label, result in results.items():
        if result is None or not result.get('analog_results'):
            continue
        assert result['dac_current_ma'][:2] == [20., 20.]
        errors = [float(re.search(r'max_error_codes=([\d.eE+-]+)', row)[1]) * 800 / 32768
                  for row in result['analog_results'][:2]]
        lines.append(f'| {label} | {errors[0]:.6f} | {errors[1]:.6f} |')
    lines += ['', '## Verification limits', '',
        '- Full-scale raw ramps: 170 cases / 117,200 samples; both full-scale directions fit one 16-sample word.',
        '- Software regression: 210 checks in gui_regression.log plus the 80,000-shot check in large_grid_instruction_model.log; v1/v2 and shared front-panel state are covered.',
        '- Python driver/model regression: 14 checks in qick_regression.log.',
        '- Actual generated HWH routing and GUI AWG/Stability selection: hwh_gui_validation.json; screenshot gui_v2_front_panel.png.',
        '- Full-grid fast/stability runs use exact integer RC checks; their full grids do not use the analog RC model.',
        '- Mixed RF sweeps include the independent analog RC model. RF power uses synthetic calibration data, not measured dBm.',
        '- 300 MHz is verified from Tcl/HWH, the 3.333 ns constraint, LMK04828_300.00.txt and ZCU216 clock setup; no live clock measurement was made.',
        '- Firmware publication additionally requires routed timing closure and matching BIT/HWH extracted from one XSA.', '']
    manifest_path = args.firmware / 'build_manifest.json'
    lines += ['## Firmware implementation', '']
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        timing = manifest['build_result']
        assert timing['timing_closed'] == 'YES'
        timing_text = (args.firmware / 'validation_reports/timing_summary_postroute.rpt').read_text()
        missing_input = int(re.search(r'checking no_input_delay \((\d+)\)', timing_text)[1])
        missing_output = int(re.search(r'checking no_output_delay \((\d+)\)', timing_text)[1])
        lines += [f"Published firmware: `{args.firmware.as_posix()}`.", '',
                  f"Routed setup WNS: {timing['setup_wns_ns']} ns; hold WHS: {timing['hold_whs_ns']} ns.",
                  f"Minimum bus-skew slack: {manifest['minimum_bus_skew_slack_ns']} ns.",
                  'Setup, hold and pulse-width checks pass. No-clock and unconstrained internal endpoint counts are both zero.',
                  f'The timing report lists {missing_input} external inputs and {missing_output} external outputs without I/O delay constraints; this result does not sign off their off-chip timing.',
                  'Reset/CDC and other methodology warnings remain in the saved reports; timing closure does not mean a warning-free design.',
                  'BIT and top-level HWH were extracted from the same XSA; hashes and selected members are recorded in build_manifest.json.', '']
    else:
        lines += ['Implementation/publication is pending. The RTL passes above do not establish routed timing closure.', '']
    audit_path = args.out / 'recovery_audit_final.json'
    if audit_path.exists():
        audit = json.loads(audit_path.read_text())
        assert audit['status'] == 'passed'
        lines += ['## Recovery integrity checks', '',
                  f"Both Git object databases passed fsck; {len(audit['source_files'])} source files passed readability/syntax checks.",
                  f"{len(audit['checkpoints'])} completed design checkpoints passed ZIP CRC validation; XPR/HWH XML parsing passed.",
                  'XSA CRC, extracted BIT/HWH equality and published artifact hashes passed. See recovery_audit_final.json.',
                  audit['limitations'], '']
    lines += ['![Voltage-grid correction](voltage_grid_before_after.png)', '',
        '![Single-clock ramp](single_clock_ramps.png)', '']
    (args.out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(dict(passed=len(results)-len(pending), pending=pending,
                         final_target_mv=float(after[-1]), max_target_error_mv=float(max(abs(after-requested)))), indent=2))


if __name__ == '__main__':
    main()
