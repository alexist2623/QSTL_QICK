from stability_diagram import (StabilityDiagramConfig, StabilitySweepAxis, build_stability_hold_sequence)
def build_program(soccfg):
    config=StabilityDiagramConfig(
        x_axis=StabilitySweepAxis('awg_0',5.,15.,20),
        y_axis=StabilitySweepAxis('awg_1',5.,15.,20),
        repetitions_per_point=2,settle_time_us=0.,trace_samples_per_point=1,
        bias_t_compensation_enabled=True,bias_t_compensation_type='dc_rc',
        bias_t_compensation_mode='fixed_time',bias_t_compensation_duration_us=2.,
        bias_t_filter_tau_us=300.)
    sequence=build_stability_hold_sequence(config,output_names=('awg_0','awg_1'),
        fabric_mhz=300.,full_scale_mv=800.,sample_period_us=1.,
        cross_capacitance=[[1.0, 0.23], [-0.17, 1.0]],
        output_full_scales_mv=(800.0, 400.0))
    return sequence.make_program(soccfg,awg_channels=(1,3),repetitions_per_sweep=2,
        compile_validation_mode='boundary')
