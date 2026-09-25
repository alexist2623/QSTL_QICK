"""RC command ABI, coefficient precision, and old-HWH compatibility."""
from fractions import Fraction
import unittest
from qick.test_awg_tuning_asmv1 import make_soccfg
from qick.asm_v1 import QickProgram
from qick.awg_tuning import AxisAwgTuningV1
from qick.square_pulse import AxisSquarePulseV1, square_words
from qick.precompensation import rc_coefficient, square_rc_increment, awg_rc_words


class TestPrecompensation(unittest.TestCase):
    def test_coefficient_precision_and_nonzero_small_step(self):
        for tau in (10, 100, 1000, 100000, 1000000):
            exact=Fraction(1 << 48, 2*tau*4800)
            self.assertLessEqual(abs(rc_coefficient(tau,4800)-exact), Fraction(1,2))
            for gain in (4, 408, 32764):
                step=square_rc_increment(gain,tau,4800)
                self.assertGreater(step, 0)
                self.assertLessEqual(abs(step-gain*exact), Fraction(1,2))

    def test_abi_and_assembler_preserve_every_bit(self):
        coeff=rc_coefficient(10,4800)
        cfg=make_soccfg(tmux_ch=7)
        cfg['gens'][0]['rc_precomp_version']=1
        program=QickProgram(cfg)
        program.set_pulse_registers(0,style='awg_rc',coefficient=coeff,enable=True,reset=True)
        self.assertEqual(tuple(program._gen_mgrs[0].last_cmd_words), awg_rc_words(coeff,enable=True,reset=True,tmux_ch=7))
        words=awg_rc_words(coeff,enable=True,reset=True,tmux_ch=7)
        command=sum(w<<(32*i) for i,w in enumerate(words))
        self.assertEqual(command & 0xffffffff,coeff)
        self.assertEqual(command>>144 & 63,0b101111)
        step=square_rc_increment(32764,10,4800)
        words=square_words(123,456,32764,rc_enable=True,rc_increment=step,reset_rc=True)
        command=sum(w<<(32*i) for i,w in enumerate(words))
        self.assertEqual(command>>64 & 65535,32764)
        self.assertEqual(command>>80 & ((1<<48)-1),step)
        self.assertEqual(command>>128 & 15,13)

    def test_parameter_detection_and_legacy_rejection(self):
        for cls,name in ((AxisAwgTuningV1,'axis_awg_tuning_v1'),(AxisSquarePulseV1,'axis_square_pulse_v1')):
            for params,version in (({},0),({'RC_PRECOMP_VERSION':'1'},1)):
                driver=cls(dict(type=f'QICK:QICK:{name}:1.0',fullpath='gen',parameters=params))
                self.assertEqual(driver['rc_precomp_version'],version)
                self.assertEqual(driver['output_latency_cycles'],11 if version else 0)
        prog=QickProgram(make_soccfg())
        with self.assertRaises(ValueError):
            prog.set_pulse_registers(0,style='awg_rc',coefficient=123,enable=True)

    def test_bad_input(self):
        for tau in (0, 1, 1000001, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):rc_coefficient(tau,4800)
        for gain in (-1,32768,True,4.0):
            with self.assertRaises(ValueError):square_rc_increment(gain,10,4800)
        with self.assertRaises(ValueError):awg_rc_words(0,enable=True)
        with self.assertRaises(ValueError):awg_rc_words(1<<32)


if __name__=='__main__':unittest.main()
