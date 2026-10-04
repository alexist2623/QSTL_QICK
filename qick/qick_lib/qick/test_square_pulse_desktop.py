"""Run compiler imports in a fresh interpreter without PYNQ or simulator stubs."""
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest


class TestSquarePulseDesktop(unittest.TestCase):
    def test_conversion_and_assembly_without_board_imports(self):
        source = r'''
            import importlib.abc
            import platform
            import sys
            platform.machine = lambda: 'AMD64'
            attempted = []
            class NoBoardImports(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path=None, target=None):
                    if fullname == 'pynq' or fullname.startswith(('pynq.', 'qick.drivers', 'qick.sim')):
                        attempted.append(fullname)
                        raise ModuleNotFoundError(f'Blocked board dependency: {fullname}', name=fullname)
            sys.meta_path.insert(0, NoBoardImports())
            from qick import QickConfig, QickProgram
            from qick.square_pulse import frequency_word, phase_word, square_words
            from qick.precompensation import square_rc_increment
            assert frequency_word(300, 4800) == 1 << 28
            assert phase_word(-90) == 3 << 30
            gen = dict(type='axis_square_pulse_v1', tproc_ch=0, tmux_ch=3,
                       f_fabric=300., f_dds=4800., has_mixer=False, has_dds=True,
                       b_dds=32, b_phase=32, maxv=32764, samps_per_clk=16,
                       rc_precomp_version=1)
            cfg = QickConfig(dict(sw_version='test', gens=[gen], readouts=[],
                tprocs=[dict(type='axis_tproc64x32_x8', f_time=300., pmem_size=65536, dmem_size=4096)]))
            for rc in (False, True):
                step = square_rc_increment(1920, 300., 4800.) if rc else 0
                prog = QickProgram(cfg)
                prog.set_pulse_registers(0, style='square', freq=1<<28, phase=3<<30,
                                        gain=1920, rc_enable=rc, rc_increment=step)
                assert prog._gen_mgrs[0].last_cmd_words == square_words(
                    1<<28, 3<<30, 1920, tmux_ch=3, rc_enable=rc, rc_increment=step)
                prog.pulse(ch=0, t=100)
                prog.end()
                prog.compile()
                assert prog.binprog
            assert not attempted, attempted
            assert 'pynq' not in sys.modules
            assert 'qick.drivers.generator' not in sys.modules
            assert 'qick.sim' not in sys.modules
        '''
        env = os.environ.copy()
        env['PYTHONPATH'] = os.pathsep.join(filter(None, (
            str(Path(__file__).resolve().parents[1]), env.get('PYTHONPATH'))))
        result = subprocess.run([sys.executable, '-c', textwrap.dedent(source)],
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
