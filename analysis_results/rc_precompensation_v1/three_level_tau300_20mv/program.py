from qick_fine_tune_sweep import FineTuneSequence

def build_program(soccfg):
    sequence = FineTuneSequence(("awg_0",))
    # Voltages are normalized to the configured +/-800 mV full scale.
    sequence.add_set("30mV_100us", 30 / 800, 100 * 300)
    sequence.add_set("10mV_10us", 10 / 800, 10 * 300)
    sequence.add_set("20mV_400us", 20 / 800, 400 * 300)
    sequence.set_rc_compensation(300.0)
    # GUI default: fixed-voltage DC compensation, 10% of full scale.
    sequence.set_bias_t_compensation(80 / 800, mode="fixed_voltage")
    return sequence.make_program(soccfg, awg_channels=(1,),
        tproc_mhz=300.0, repetitions_per_sweep=200, recovery_tproc_cycles=20)
