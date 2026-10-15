"""Regression for desktop SquarePulse compilation without PYNQ test stubs."""
import builtins
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest


def test_square_experiment_and_standalone_compile_without_pynq():
    source = r'''
        import importlib.abc
        import platform
        import sys
        platform.machine = lambda: 'AMD64'
        attempted = []
        class NoBoardImports(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == 'pynq' or fullname.startswith(('pynq.', 'qick.sim', 'qick.drivers')):
                    attempted.append(fullname)
                    raise ModuleNotFoundError(f'Blocked board dependency: {fullname}', name=fullname)
        sys.meta_path.insert(0, NoBoardImports())
        from qick import QickConfig
        from qick_fine_tune_sweep import FineTuneSequence
        from qick_square_dds import SquarePulseConfig, SquarePulseSweep, attach_square_settings
        from qick_square_wave import SquareWaveConfig, build_square_dds_program
        awg = dict(type='axis_awg_tuning_v2', gen_type='awg_tuning', tproc_ch=0,
            tmux_ch=0, f_fabric=300., f_dds=4800., n_pts=16, samps_per_clk=16,
            frac=18, cmd_width=160, step_width=32, duration_width=23, fixed_width=48,
            dac_invalid_lsb=2, maxv=32764, minv=-32768, ramp_startup_latency_cycles=7,
            ramp_guard_cycles=1, has_mixer=False, has_dds=False, b_dds=32, b_phase=32,
            dac='10', interpolation=1, rc_precomp_version=1, output_latency_cycles=11)
        square = dict(awg, type='axis_square_pulse_v1', gen_type='square_pulse',
                      tproc_ch=1, tmux_ch=1, dac='13', has_dds=True, command_latency_cycles=15)
        cfg = QickConfig(dict(sw_version='test', gens=[awg,square], readouts=[],
            tprocs=[dict(type='axis_tproc64x32_x8', f_time=300., pmem_size=65536,
                         dmem_size=4096, output_pins=[])]))
        for rc in (False, True):
            for mute in (False, True):
                for swept in (False, True):
                    seq = FineTuneSequence(('awg_0',))
                    seq.add_set('measure', .01, 300)
                    seq.set_bias_t_compensation(mode='fixed_time', fixed_duration_cycles=600)
                    if rc:
                        seq.set_rc_compensation(300.)
                    conf = SquarePulseConfig(1, mute_on_finish=mute, rc_enabled=rc, rc_tau_us=300.)
                    axes = tuple(SquarePulseSweep(name, start, stop, 3, 1) for name,start,stop in
                        [('frequency',.002,.04),('amplitude',5.,15.),('phase',-90.,90.)]) if swept else ()
                    attach_square_settings(seq, conf, axes)
                    prog = seq.make_program(cfg, awg_channels=(0,), repetitions_per_sweep=2)
                    prog.compile()
                    assert prog.cfg['expts'] == (27 if swept else 1)
                    assert prog.binprog
            standalone = build_square_dds_program(cfg, SquareWaveConfig(
                gen_ch=1, rc_enabled=rc, rc_tau_us=300., zero_code=0.))
            assert standalone.binprog
        # An old AWG-only firmware path must remain usable without SquarePulse enabled.
        cfg['gens'] = [dict(awg, type='axis_awg_tuning_v1', step_width=24, frac=16)]
        seq = FineTuneSequence(('awg_0',)).add_set('measure', .01, 300)
        prog = seq.make_program(cfg, awg_channels=(0,))
        prog.compile()
        assert prog.binprog
        assert not attempted, attempted
        assert 'pynq' not in sys.modules and 'qick.sim' not in sys.modules
    '''
    env = os.environ.copy()
    env['QT_QPA_PLATFORM'] = 'offscreen'
    env['PYTHONPATH'] = os.pathsep.join(filter(None, (
        str(Path(__file__).resolve().parent), env.get('PYTHONPATH'))))
    result = subprocess.run([sys.executable, '-c', textwrap.dedent(source)],
                            capture_output=True, text=True, env=env, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('missing', ['pynq', 'qick.square_pulse'])
def test_square_import_error_identifies_missing_dependency(monkeypatch, missing):
    from qick_square_dds import SquarePulseConfig
    original = builtins.__import__
    def fail_square(name, *args, **kwargs):
        if name == 'qick.square_pulse':
            raise ModuleNotFoundError(f"No module named '{missing}'", name=missing)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', fail_square)
    with pytest.raises(RuntimeError) as error:
        SquarePulseConfig(0).word('frequency', .04, {'f_dds':4800.})
    message = str(error.value)
    if missing == 'pynq':
        assert "No module named 'pynq'" in message
        assert 'lacks SquarePulse support' not in message
    else:
        assert "GUI's QSTL_QICK Python installation lacks SquarePulse support" in message
