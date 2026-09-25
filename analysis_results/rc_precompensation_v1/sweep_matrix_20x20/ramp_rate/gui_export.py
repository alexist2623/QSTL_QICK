"""Generated QICK AWG-tuning, RF pulse, and HWH-rate DDR program."""

from qick_fine_tune_sweep import (
    DdrFirReadoutConfig,
    FineTuneSequence,
    RfPulseConfig,
    cycles_from_us,
)
from dc_waveform_core import QickRfPulseSpec
from qick_qcodes_experiment import build_runtime_rf_pulses

OUTPUT_NAMES = ('awg_0', 'awg_1')
AWG_CHANNELS = {'awg_0': 1, 'awg_1': 3}
FABRIC_MHZ = 300.0
TPROC_MHZ = 300.0
FULL_SCALE_MV = 800.0
BIAS_T_COMPENSATION_ENABLED = True
BIAS_T_COMPENSATION_TYPE = 'dc_rc'
BIAS_T_COMPENSATION_VOLTAGE_MV = 80.0
BIAS_T_COMPENSATION_MODE = 'fixed_time'
BIAS_T_COMPENSATION_DURATION_US = 1.0
BIAS_T_COMPENSATION_DURATION_CYCLES = 300
BIAS_T_FILTER_TAU_US = 10.0
BIAS_T_FILTER_TAU_CYCLES = 3000.0
REPETITIONS_PER_SWEEP = 2
SWEEP_SPECS = ({'axis_kind': 'ramp_duration', 'segment_name': 'ramp_0_to_1', 'output_name': 'all_awg_outputs', 'start': 0.1, 'stop': 0.41666666666666663, 'count': 20}, {'axis_kind': 'amplitude', 'segment_name': 'set_0', 'output_name': 'awg_0', 'start': 0.00625, 'stop': 0.01875, 'count': 20})
CROSS_CAPACITANCE = ((1.0, 0.0), (0.0, 1.0))
RF_CONFIGS = ({'gen_ch': 0, 'segment_name': 'set_0', 'delay_us': 0.0, 'duration_us': 0.1, 'frequency_mhz': 190.0, 'gain': 2000, 'att1_db': 0.0, 'att2_db': 0.0, 'phase_degrees': 0.0, 'nqz': 1, 'require_within_segment': True, 'filter_type': 'bypass', 'filter_cutoff': 2.5, 'filter_bandwidth': 1.0, 'output_board_type': 'RF_Out', 'duration_sweep_enabled': False, 'duration_sweep_start_us': 1.0, 'duration_sweep_stop_us': 1.0, 'duration_sweep_count': 1, 'segment_length_mode': 'fixed', 'frequency_sweep_enabled': False, 'frequency_sweep_start_mhz': 50.0, 'frequency_sweep_stop_mhz': 50.0, 'frequency_sweep_count': 1, 'power_sweep_enabled': False, 'power_sweep_start_dbm': -20.0, 'power_sweep_stop_dbm': -20.0, 'power_sweep_count': 1, 'power_calibration_enabled': False, 'power_calibration_database_path': '', 'power_calibration_run_id': 0, 'target_output_power_dbm': -20.0, 'pulse_mode': 'single', 'pulse_name': 'RF pulse', 'frequency_parameters': (), 'duration_parameters': (), 'composite_items': ()},)
RF_CONFIG = RF_CONFIGS[0] if len(RF_CONFIGS) == 1 else None
FIR_DDR_CONFIG = None


def build_sequence() -> FineTuneSequence:
    sequence = FineTuneSequence(OUTPUT_NAMES)
    sequence.output_full_scale_mv = FULL_SCALE_MV
    sequence.set_cross_capacitance(CROSS_CAPACITANCE)
    sequence.set_rc_compensation(
        BIAS_T_FILTER_TAU_US,
        enabled=BIAS_T_COMPENSATION_ENABLED and BIAS_T_COMPENSATION_TYPE in ('filter', 'dc_rc'),
    )
    sequence.set_bias_t_compensation(
        BIAS_T_COMPENSATION_VOLTAGE_MV / FULL_SCALE_MV,
        enabled=BIAS_T_COMPENSATION_ENABLED and BIAS_T_COMPENSATION_TYPE in ('dc', 'dc_rc'),
        mode=BIAS_T_COMPENSATION_MODE,
        fixed_duration_cycles=(
            BIAS_T_COMPENSATION_DURATION_CYCLES
            if BIAS_T_COMPENSATION_MODE == 'fixed_time' else None
        ),
    )
    sequence.add_set('set_0', (0.0125, -0.00625), duration_cycles=300)
    sequence.add_ramp('ramp_0_to_1', duration_cycles=60)
    sequence.add_set('set_1', (-0.0125, 0.00625), duration_cycles=300)
    sequence.add_ramp('ramp_1_to_2', duration_cycles=60)
    sequence.add_set('set_2', (0.0, -0.0), duration_cycles=300)
    sequence.add_ramp_duration_sweep(
        segment='ramp_0_to_1',
        start_us=0.1,
        stop_us=0.41666666666666663,
        count=20,
        sequence_fabric_mhz=FABRIC_MHZ,
    )
    sequence.add_amplitude_sweep(
        segment='set_0',
        output='awg_0',
        start=0.00625,
        stop=0.01875,
        count=20,
    )
    from qick_square_dds import decode_square_settings, OutputTriggerConfig, attach_square_settings
    square_config, square_axes = decode_square_settings(None, 800.0)
    attach_square_settings(sequence, square_config, square_axes, OutputTriggerConfig(**{'enabled': True, 'pin': 0, 'scope': 'loop', 'edge': 'both', 'width_us': 0.1}))
    from qick_rc_validation import validate_sequence_rc_range
    sequence.rc_output_range_preview = validate_sequence_rc_range(sequence, FABRIC_MHZ, FULL_SCALE_MV)
    return sequence


def _delay_cycles(duration_us, clock_mhz):
    return 0 if duration_us <= 0 else cycles_from_us(duration_us, clock_mhz)


def build_rf_pulses(soccfg):
    specs = tuple(QickRfPulseSpec(**cfg) for cfg in RF_CONFIGS)
    return build_runtime_rf_pulses(
        soccfg, specs, tproc_mhz=TPROC_MHZ
    )


def build_rf_pulse(soccfg):
    pulses = build_rf_pulses(soccfg)
    return pulses[0] if len(pulses) == 1 else None


def build_ddr_readout(soccfg):
    if FIR_DDR_CONFIG is None:
        return None
    cfg = FIR_DDR_CONFIG
    return DdrFirReadoutConfig(
        ro_ch=cfg['ro_ch'],
        samples_per_trigger=cfg['samples_per_trigger'],
        at_segment=cfg['segment_name'],
        readout_freq_mhz=cfg['readout_frequency_mhz'],
        trigger_delay_tproc_cycles=_delay_cycles(
            cfg['delay_us'], TPROC_MHZ
        ),
        margin_input_samples=cfg['margin_input_samples'],
        address=cfg['address'],
        force_overwrite=cfg['force_overwrite'],
    )


def build_program(
    soccfg,
    *,
    awg_channels=AWG_CHANNELS,
    repetitions_per_sweep=REPETITIONS_PER_SWEEP,
    readout=None,
    rf_pulse=None,
    rf_pulses=None,
    ddr_readout=None,
    use_generated_aux=True,
):
    if use_generated_aux:
        if rf_pulse is None and rf_pulses is None:
            rf_pulses = build_rf_pulses(soccfg)
        if ddr_readout is None:
            ddr_readout = build_ddr_readout(soccfg)
    return build_sequence().make_program(
        soccfg,
        awg_channels=awg_channels,
        tproc_mhz=TPROC_MHZ,
        repetitions_per_sweep=repetitions_per_sweep,
        readout=readout,
        rf_pulse=rf_pulse,
        rf_pulses=rf_pulses,
        ddr_readout=ddr_readout,
    )


def configure_rf_chain(soc):
    if not RF_CONFIGS:
        return None
    actual = []
    for cfg in RF_CONFIGS:
        if cfg['output_board_type'] == 'RF_Out':
            configured = soc.rfb_set_gen_rf(
                cfg['gen_ch'], cfg['att1_db'], cfg['att2_db']
            )
        else:
            soc.rfb_set_gen_dc(cfg['gen_ch'])
            configured = (0.0, 0.0)
        actual.append(configured)
        if cfg['output_board_type'] == 'RF_Out':
            soc.rfb_set_gen_filter(
                cfg['gen_ch'],
                fc=cfg['filter_cutoff'],
                bw=cfg['filter_bandwidth'],
                ftype=cfg['filter_type'],
            )
    actual = tuple(actual)
    return actual[0] if len(actual) == 1 else actual


def configure_readout_chain(soc):
    if FIR_DDR_CONFIG is None:
        return None
    cfg = FIR_DDR_CONFIG
    if cfg['input_board_type'] == 'RF_In':
        configured = soc.rfb_set_ro_rf(cfg['ro_ch'], cfg['attenuation_db'])
    else:
        configured = soc.rfb_set_ro_dc(cfg['ro_ch'], cfg['dc_gain_db'])
    if cfg['input_board_type'] == 'RF_In':
        soc.rfb_set_ro_filter(
            cfg['ro_ch'],
            fc=cfg['filter_cutoff'],
            bw=cfg['filter_bandwidth'],
            ftype=cfg['filter_type'],
        )
    return configured


def run_experiment(soc, soccfg, *, progress=True, configure_rf=True, **run_kwargs):
    actual_outputs = configure_rf_chain(soc) if configure_rf else None
    actual_input = configure_readout_chain(soc) if configure_rf else None
    program = build_program(soccfg)
    square = getattr(program, 'square_pulse_config', None)
    if square is not None and configure_rf:
        soc.rfb_set_gen_dc(square.gen_ch)
    completed = False
    try:
        if FIR_DDR_CONFIG is not None:
            ddr_result = program.acquire_fir_ddr(
                soc, progress=progress, **run_kwargs
            )
        else:
            program.run_rounds(soc, progress=progress, **run_kwargs)
            ddr_result = None
        completed = True
    finally:
        if square is not None and (not completed or square.mute_on_finish):
            soc.stop_square_pulse(square.gen_ch)
    rf_settings = {'outputs': actual_outputs, 'readout': actual_input}
    return program, ddr_result, rf_settings
