"""Plot measured RTL sample words; no synthetic waveform substitutes."""
import argparse
import csv
import json
from pathlib import Path

from harness import sha
from run import read_samples

HERE = Path(__file__).resolve().parent


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    parser = argparse.ArgumentParser()
    parser.add_argument('statuses',type=Path,nargs='+')
    parser.add_argument('--equivalence',type=Path,default=HERE/'final_recompile_equivalence.json')
    args = parser.parse_args()
    equivalence = json.loads(args.equivalence.read_text())
    assert equivalence['passed'] and equivalence['checked_cases'] >= 8
    cases = []
    for path in args.statuses:
        status = json.loads(path.read_text())
        assert status['complete'] and status['stage'] == 'passed', path
        cases.extend(status['cases'])
    matrix = [case for case in cases if case['name'].startswith('remainders_ch')]
    assert len(matrix) == 3, 'Need the complete all-remainder result on each real RF path'
    periodic = next(case for case in cases if case['name'].startswith('long_periodic'))
    phase = next(case for case in cases if case['name'].startswith('phase_offsets'))
    short = next(case for case in cases if case['name'].startswith('composite_short'))
    short_all = next(case for case in cases if case['name'].startswith('short_1_to_31'))
    short_carrier = next(case for case in cases if case['name'].startswith('short_carrier_1_to_31'))
    long_pair = next(case for case in cases if case['name'].startswith('long_pair'))
    for case in cases:
        assert case['command_value_errors'] == case['command_timing_errors'] == case['sum_lane_oracle_errors'] == 0
        for check in case['checks']:
            assert check['pipeline_after_tproc_samples'] == 512
            assert check['unexpected_nonzero_samples'] == 0
    fig,axes = plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    colors = ('#2463ad','#c4512c','#24876a')
    coverage = []
    for case,color in zip(matrix,colors):
        channel = int(case['name'].split('_')[1][2:])
        check = next(row for row in case['checks'] if row['channel'] == channel)
        points = [row for row in check['bursts'] if row['frequency_mhz'] == 0. and row['repetition'] == 0]
        requested = np.asarray([row['samples'] for row in points])
        measured = np.asarray([row['exact_active_sample_count'] for row in points])
        assert requested.tolist() == list(range(81,113))
        assert np.array_equal(requested,measured)
        carrier = [row for row in check['bursts'] if row['frequency_mhz'] == 190.]
        assert len(carrier) == 64
        axes[0,0].plot(requested,measured,'.-',color=color,label=f'RF channel {channel}',alpha=.8)
        axes[0,1].plot(requested,measured-requested,'.-',color=color,alpha=.8)
        coverage.append(dict(channel=channel,requested_samples=requested.tolist(),
            measured_samples=measured.tolist(),carrier_bursts=len(carrier),
            repetitions=2,frequency_axis_mhz=[0.,190.]))
    axes[0,0].set(xlabel='Requested active samples',ylabel='Measured active samples',
        title='Hardware sweep: every remainder and the 95/96 transition')
    axes[0,0].legend()
    axes[0,1].set(xlabel='Requested active samples',ylabel='Width error (samples)',
        title='Exact width at 4.8 GS/s',ylim=(-1,1))
    first = next(case for case in matrix if case['name'].startswith('remainders_ch0'))
    first_check = next(row for row in first['checks'] if row['channel'] == 0)
    origin,data = read_samples(Path(first['folder'])/'fine_0.csv')
    for samples,color in ((95,colors[0]),(96,colors[1])):
        burst = next(row for row in first_check['bursts'] if row['samples'] == samples and
                     row['frequency_mhz'] == 0. and row['repetition'] == 0)
        begin = burst['first_sample']-origin
        relative = np.arange(88,105)
        axes[1,0].step(relative/4.8,data[begin+relative],where='post',color=color,
                       label=f'{samples} active samples')
    axes[1,0].set(xlabel='Time after RF onset (ns)',ylabel='Actual SG-v6 code',
        title='Measured adjacent hardware points: one-sample edge shift')
    axes[1,0].legend()
    axes[1,0].set_xticks(np.arange(88,105,2)/4.8)
    boundary = axes[1,1].inset_axes([.07,.44,.48,.43])
    with (Path(periodic['folder'])/'rtl_events.csv').open() as stream:
        periodic_commands = list(csv.DictReader(stream))
    for check,color in zip(periodic['checks'],colors):
        burst = check['bursts'][0]
        origin,data = read_samples(Path(periodic['folder'])/f'fine_{check["channel"]}.csv')
        begin = burst['first_sample']-origin
        relative = np.arange(burst['samples']-100,burst['samples']+16)
        axes[1,1].step((relative-burst['samples'])/4.8,data[begin+relative],where='post',
            color=color,label=f'N={burst["samples"]:,}',alpha=.8)
        boundary.step((relative-burst['samples'])/4.8,data[begin+relative],where='post',
                      color=color,alpha=.8)
        commands = [row for row in periodic_commands if int(row['port']) == check['channel']//2
                    and ((int(row['word'],16)>>152)&255) == 0]
        tail_sample = 16*(int(commands[1]['cycle'])-int(commands[0]['cycle']))
        boundary.axvline((tail_sample-burst['samples'])/4.8,color=color,linestyle='--',linewidth=.8)
    boundary.set(xlim=(-22.,-.2),ylim=(3998.7,4000.3),xticks=(-20.,-10.),yticks=(3999,4000))
    boundary.tick_params(labelsize=7)
    boundary.ticklabel_format(axis='y',style='plain',useOffset=False)
    boundary.set_title('Actual tail commands: no output gap',fontsize=7)
    boundary.grid(alpha=.2)
    axes[1,1].set(xlabel='Time relative to requested RF end (ns)',ylabel='Actual SG-v6 code',
        title='300 us periodic plateau: measured masked ending')
    axes[1,1].legend()
    for ax in axes.flat:
        ax.grid(alpha=.2)
    fig.suptitle('Existing SG-v6 RTL: 208.333 ps RF width steps\n'
                 'Three shared-TMUX RF/AWG pairs · 32-clock measured output latency · no analog measurement',fontsize=13)
    figure = HERE/'actual_rf_sample_width.png'
    fig.savefig(figure,dpi=180)
    plt.close(fig)
    short_figure = HERE/'actual_short_rf_sample_width.png'
    short_fig,short_axes = plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
    for check,color in zip(short_all['checks'],colors):
        points = [row for row in check['bursts'] if row['repetition'] == 0]
        requested = [row['samples'] for row in points]
        measured = [row['exact_active_sample_count'] for row in points]
        assert requested == measured == list(range(1,32))
        short_axes[0].plot(requested,np.asarray(measured)/4.8,'.-',color=color,
                           label=f'RF channel {check["channel"]}',alpha=.8)
    short_axes[0].set(xlabel='Requested active samples',ylabel='Measured active width (ns)',
                      title='All widths 1–31: three paths, two repetitions')
    short_axes[0].legend()
    short_check = next(row for row in short_all['checks'] if row['channel'] == 0)
    origin,data = read_samples(Path(short_all['folder'])/'fine_0.csv')
    for panel,widths,relative in ((1,(1,),np.arange(-2,7)),
                                  (2,(15,16,17),np.arange(12,21))):
        for samples,color in zip(widths,colors):
            burst = next(row for row in short_check['bursts'] if row['samples'] == samples and row['repetition'] == 0)
            begin = burst['first_sample']-origin
            short_axes[panel].step(relative/4.8,data[begin+relative],where='post',
                                   color=color,label=f'{samples} sample'+('' if samples == 1 else 's'))
        short_axes[panel].set(xlabel='Time after RF onset (ns)',ylabel='Actual SG-v6 code')
        short_axes[panel].legend()
    short_axes[1].set_title('One active sample = 0.208333… ns')
    short_axes[2].set_title('Edges around the 16-lane word boundary')
    for check in short_carrier['checks']:
        for repetition in (0,1):
            points = [row for row in check['bursts'] if row['repetition'] == repetition
                      and 'reference_prediction_max_error_codes' in row]
            assert [row['samples'] for row in points] == list(range(1,32))
    carrier_check = next(row for row in short_carrier['checks'] if row['channel'] == 0)
    burst = next(row for row in carrier_check['bursts'] if row['samples'] == 1 and row['repetition'] == 0)
    origin,data = read_samples(Path(short_carrier['folder'])/'fine_0.csv')
    relative = np.arange(-2,7)
    begin = burst['first_sample']-origin
    short_axes[1].step(relative/4.8,data[begin+relative],where='post',color=colors[1],
                        linestyle='--',label='1 sample at 190 MHz')
    short_axes[1].legend(fontsize=8)
    for ax in short_axes:
        ax.grid(alpha=.2)
    short_fig.suptitle('Actual RTL active width can be below one 300 MHz clock\n'
                       'The generator still occupies at least three clocks (10 ns), including zero padding.',fontsize=12)
    short_fig.savefig(short_figure,dpi=180)
    plt.close(short_fig)
    report = dict(passed=True,case_count=len(cases),sample_rate_gsps=4.8,
        total_rf_bursts=sum(len(check['bursts']) for case in cases for check in case['checks']),
        total_command_events=sum(case['commands'] for case in cases),
        command_value_errors=sum(case['command_value_errors'] for case in cases),
        command_timing_errors=sum(case['command_timing_errors'] for case in cases),
        sum_lane_oracle_errors=sum(case['sum_lane_oracle_errors'] for case in cases),
        unexpected_nonzero_samples=sum(check['unexpected_nonzero_samples'] for case in cases for check in case['checks']),
        sample_step_ns=1/4.8,start_timestamp_step_ns=1/.3,
        envelope_samples_per_rf_channel=2048,maximum_allowed_gain_magnitude=16383,
        requested_frequency_and_phase_words_independently_checked=True,
        measured_tproc_to_sum_input_fabric_clocks=32,
        alignment_note='Widths use actual DAC-lane sample positions; pulse onset still uses the existing 300 MHz command grid. This is SG-v6/v4 sum-v1 simulation, not v5 routed timing or an analog RF measurement.',
        coverage=coverage,
        short_samples=sorted({row['samples'] for check in short['checks'] for row in check['bursts']}),
        consecutive_short_samples=list(range(1,32)),consecutive_short_bursts=186,
        short_carrier_frequency_mhz=190.,short_carrier_phase_degrees=37.,
        short_carrier_reference_samples=4801,short_carrier_prediction_bursts=186,
        maximum_short_carrier_prediction_error_codes=max(row.get('reference_prediction_max_error_codes',0.)
            for check in short_carrier['checks'] for row in check['bursts']),
        long_samples=sorted({row['samples'] for case in (long_pair,periodic) for check in case['checks'] for row in check['bursts']}),
        phase_offsets_degrees=sorted({row['phase_degrees'] for check in phase['checks'] for row in check['bursts']}),
        maximum_carrier_rms_codes=max(row.get('rms_codes',0.) for case in cases for check in case['checks'] for row in check['bursts']),
        maximum_fixed_amplitude_error_codes=max(row.get('maximum_amplitude_error_codes',0.) for case in cases for check in case['checks'] for row in check['bursts']),
        maximum_phase_error_degrees=max(abs(row.get('phase_error_degrees',0.)) for case in cases for check in case['checks'] for row in check['bursts']),
        figure=str(figure),figure_sha256=sha(figure),
        short_figure=str(short_figure),short_figure_sha256=sha(short_figure),
        final_recompile_equivalence=str(args.equivalence),final_recompile_equivalence_sha256=sha(args.equivalence),
        prepared_manifests={str(Path(case['folder']).parent/'prepared.json'):
                           sha(Path(case['folder']).parent/'prepared.json') for case in cases},
        statuses={str(path):sha(path) for path in args.statuses},helper_sha256=sha(__file__))
    (HERE/'result.json').write_text(json.dumps(report,indent=2))
    (HERE/'REPORT.md').write_text(
        '# Actual SG-v6 sample-width RTL verification\n\n'
        'The inputs passed through the staged GUI, normal experiment arguments, and real QICK compiler. '
        'Actual tProc PMEM/DMEM drives the unchanged shared-TMUX SG-v6/AWG paths. The testbench loads IQ '
        'samples through host AXI configuration and the actual AXIS data_writer/BRAM. Vendor DDS logic '
        'and the v4 output-sum RTL are included.\n\n'
        '- Every active width from 81 through 112 samples: exact on all three RF paths, twice per point.\n'
        '- Every active width from 1 through 31 samples: exact on all three RF paths, twice per width (186 bursts).\n'
        '- At 190 MHz and 37 degrees, all 1–31-sample bursts match an actual 4801-sample reference carrier extrapolated at the exact FTW and absolute sample time (186 additional bursts).\n'
        '- Hardware duration × frequency sweep: 32 × 2 points, with 0 MHz exact sample counts and 190 MHz carrier fits.\n'
        '- Requested frequency and phase words independently checked against the user coordinates.\n'
        '- Short pulses, negative gain, gain 16383, 10 us/100 us fractional endings, and all three periodic-boundary classes checked.\n'
        '- All command values/timestamps and all sum lanes checked; no unexpected nonzero sample outside requested windows.\n\n'
        f'![Actual RF sample words]({figure.name})\n\n'
        f'![Actual widths from 1 through 31 samples]({short_figure.name})\n\n'
        'The duration step is 1/4.8 ns = 0.208333… ns. Onset timing remains on the existing 300 MHz grid. '
        'The masked product path uses doubled gain and limits the requested gain magnitude to 16383; '
        'its integer multiplication can differ from the DDS plateau by a few DAC codes. '
        'The measured command-to-sum-input latency is 32 fabric clocks; this result does not claim a v5 '
        'latency change, routed timing signoff, or measured analog rise/fall time.\n',encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
