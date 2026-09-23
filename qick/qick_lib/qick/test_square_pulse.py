"""Square DDS driver/assembler contract, without a PYNQ board."""
import unittest
from qick.test_awg_tuning_asmv1 import make_soccfg
from qick.asm_v1 import QickProgram, SquarePulseGenManager
from qick.square_pulse import frequency_word, phase_word, square_words, AxisSquarePulseV1


class TestSquarePulse(unittest.TestCase):
    def test_units(self):
        self.assertEqual(frequency_word(300,4800), 1<<28)
        self.assertEqual(phase_word(180), 1<<31)
        self.assertEqual(phase_word(-90), 3<<30)
        self.assertEqual(phase_word(720), 0)
        self.assertEqual(square_words(1,2,800,tmux_ch=3), (1,2,800,0,0x03000001))
        self.assertEqual(square_words(1,2,800,reset_phase=True)[4],3)

    def test_bad_parameters(self):
        for amplitude in (-1,1,32768,2.0,True):
            with self.assertRaises(ValueError): square_words(0,0,amplitude)
        for freq in (-1,2400,float('nan'),float('inf')):
            with self.assertRaises(ValueError): frequency_word(freq,4800)
        with self.assertRaises(ValueError): phase_word(float('nan'))
        with self.assertRaises(ValueError): square_words(2**32,0,0)

    def test_assembler(self):
        cfg=make_soccfg(tmux_ch=3)
        cfg['tprocs'][0]['pmem_size']=65536
        cfg['gens'][0].update(type='axis_square_pulse_v1',gen_type='square_pulse',has_dds=True)
        prog=QickProgram(cfg)
        self.assertIsInstance(prog._gen_mgrs[0],SquarePulseGenManager)
        prog.set_pulse_registers(0,style='square',freq=0x71234567,phase=0x80000000,gain=1920)
        self.assertEqual(prog._gen_mgrs[0].last_cmd_words, (0x71234567,0x80000000,1920,0,0x03000001))
        prog.pulse(ch=0,t=100)
        prog.set_pulse_registers(0,style='square',freq=5,phase=6,gain=320,enable=False)
        prog.pulse(ch=0,t=200)
        prog.end()
        prog.compile()
        self.assertGreater(len(prog.binprog),0)
        self.assertEqual(prog._gen_mgrs[0].last_cmd_words[-1], 0x03000000)

    def test_driver_description(self):
        ip=AxisSquarePulseV1(dict(type='QICK:QICK:axis_square_pulse_v1:1.0',fullpath='square',parameters={}))
        self.assertEqual(ip['gen_type'],'square_pulse')
        self.assertTrue(ip['phase_continuous'])
        self.assertEqual(ip['command_latency_cycles'],4)
        self.assertEqual(ip['maxv'],32764)

    def test_standalone_example(self):
        import importlib.util
        from pathlib import Path
        from qick.awg_tuning import TProcV1BehaviorModel
        path=Path(__file__).resolve().parents[2]/'qick_demos/square_pulse_dds.py'
        spec=importlib.util.spec_from_file_location('square_demo',path)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        cfg=make_soccfg(tmux_ch=1)
        cfg['tprocs'][0]['pmem_size']=65536
        cfg['gens'][0].update(type='axis_square_pulse_v1',gen_type='square_pulse',has_dds=True,f_dds=4800)
        prog=module.SquarePulseUpdate(cfg,0,190,1920,90)
        prog.compile(); model=TProcV1BehaviorModel(strict=True); model.run(prog)
        self.assertEqual(len(model.output_events),1)
        expected=square_words(frequency_word(190,4800),phase_word(90),1920,tmux_ch=1)
        self.assertEqual(model.output_events[0].word,sum(w<<(32*i) for i,w in enumerate(expected)))


if __name__=='__main__': unittest.main()
