"""One realtime update starts a continuous square output without a CPU loop.

Import this file in a board notebook after constructing soc and soccfg.
Generator numbers must come from the loaded firmware's soccfg['gens'] list.
"""
from qick.asm_v1 import QickProgram
from qick.square_pulse import frequency_word, phase_word


class SquarePulseUpdate(QickProgram):
    def __init__(self, soccfg, ch, frequency_mhz, amplitude, phase_deg=0.0,
                 *, enable=True, reset_phase=False):
        super().__init__(soccfg)
        gen = soccfg['gens'][ch]
        if gen['type'] != 'axis_square_pulse_v1':
            raise ValueError('Select a SquarePulse generator from the loaded firmware')
        self.declare_gen(ch=ch, nqz=1)
        self.synci(200)
        self.set_pulse_registers(ch=ch, style='square',
            freq=frequency_word(frequency_mhz, gen['f_dds']),
            phase=phase_word(phase_deg), gain=amplitude,
            enable=enable, reset_phase=reset_phase)
        self.pulse(ch=ch, t=0)
        self.waiti(0, 200)
        self.end()


# Example, after loading the matching firmware and board-side Python library:
# ch = next(i for i, g in enumerate(soccfg['gens'])
#           if g['type'] == 'axis_square_pulse_v1')
# soc.rfb_set_gen_dc(ch)
# SquarePulseUpdate(soccfg, ch, 0.04, 800).run(soc)
# SquarePulseUpdate(soccfg, ch, 190.0, 1600, 90).run(soc)
# The second update preserves the running accumulator; it adds a 90-degree offset.
# soc.stop_square_pulse(ch)
