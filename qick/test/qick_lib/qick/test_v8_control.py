"""Desktop MMIO models test abort ACK/errors and atomic AWG clipping configuration."""
import types
import numpy as np
import pytest
from test_ddr_triggered_pack_support import _install_pynq_stub, QickSoc
from qick.awg_tuning import AxisAwgTuningV8
from qick.drivers.readout import AxisBufferDdrSampleV4
from qick.asm_v1 import QickProgram
from test_awg_tuning_asmv1 import make_soccfg


class Registers:
    def __init__(self, kind, stuck=False):
        self.data = np.zeros(16, dtype=np.uint32)
        self.kind, self.stuck = kind, stuck
        self.writes = []
        self.remaining = 0
        if kind == 'clip':
            self.data[2:5] = [0xFFFF8000, 32764, 0xC1080000]
        else:
            self.data[10:15] = [0x5149434B, 1, 64, 46, 0xAB040000]
    def __getitem__(self, key):
        if key == (4 if self.kind == 'clip' else 14) and self.remaining and not self.stuck:
            self.remaining -= 1
            if self.remaining == 0:
                if self.kind == 'clip':
                    self.data[4] &= np.uint32(0xFFFFFFFD)
                else:
                    self.data[14], self.data[5] = 0xAB040002, 0
        return self.data[key]
    def __setitem__(self, key, value):
        self.writes.append((key, int(value)))
        if self.kind == 'clip' and key == 4:
            self.data[key] = 0xC1080002 | (int(value) & 1)
            self.remaining = 3
        elif self.kind == 'abort' and key == 14:
            self.data[14], self.data[5] = 0xAB040001, 9
            self.remaining = 3
        else:
            self.data[key] = value


def awg(stuck=False):
    drv = AxisAwgTuningV8(dict(type='QICK:QICK:axis_awg_tuning_v8:1.0', fullpath='awg',
        parameters=dict(RC_PRECOMP_VERSION='1', DC_AREA_VERSION='1', DC_AREA_BITS='48')))
    drv.mmio = types.SimpleNamespace(array=Registers('clip', stuck))
    return drv


def ddr(stuck=False):
    drv = object.__new__(AxisBufferDdrSampleV4)
    object.__setattr__(drv, '_cfg', {})
    drv._init_config(dict(parameters=dict(TARGET_SLAVE_BASE_ADDR='0', ID_WIDTH='1',
        S_AXIS_DATA_WIDTH='128', M_AXI_DATA_WIDTH='256', IQ_COMPONENT_BITS='64',
        IQ_SCALE_LOG2='46', FORMAT_VERSION='1', DEFAULT_TRIGGER_DELAY_CYCLES='8712')))
    drv.mmio = types.SimpleNamespace(array=Registers('abort', stuck))
    drv._init_firmware()
    return drv


def test_clipping_commit_readback_and_zero_disable():
    drv = awg()
    assert drv.cfg['output_latency_cycles'] == 27
    for lo, hi in [(-32768, 32764), (-400, 800), (0, 0), (0, 4), (-4, 0)]:
        actual = drv.set_output_limits(lo, hi, True)
        assert actual == dict(enabled=True, pending=False, configuration_error=False,
                              clipped=False, min_code=lo, max_code=hi)
        assert drv.mmio.array.writes[-3:] == [(2, lo & 0xFFFFFFFF), (3, hi), (4, 3)]
    assert not drv.set_output_limits()['enabled']


@pytest.mark.parametrize('lo,hi', [(1,100),(-4,-4),(-32772,4),(-4,32768),(-1,4),(-4,5),(False,4),(-4,4.0)])
def test_invalid_clip_never_writes(lo, hi):
    drv = awg()
    with pytest.raises(ValueError): drv.set_output_limits(lo, hi, True)
    assert drv.mmio.array.writes == []


def test_signatures_pending_and_timeouts():
    drv = awg(True)
    with pytest.raises(TimeoutError): drv.set_output_limits(-4,4,True,timeout=.002)
    before = list(drv.mmio.array.writes)
    with pytest.raises(RuntimeError, match='pending'): drv.set_output_limits(-4,4,True)
    assert drv.mmio.array.writes == before
    drv.mmio.array.data[4] = 0
    with pytest.raises(RuntimeError, match='BIT/HWH'): drv.set_output_limits()
    capture = ddr(True)
    with pytest.raises(TimeoutError, match='do not re-arm'): capture.abort(timeout=.002)
    capture.mmio.array.data[14] = 0
    with pytest.raises(RuntimeError, match='BIT/HWH'): capture.abort()


def test_cancel_busy_missing_triggers_then_rearm():
    capture = ddr()
    capture.mmio.array.data[5] = 9
    result = capture.abort()
    assert result == dict(pending=False, acknowledged=True, busy=False, armed=False)
    capture.cfg['maxlen'] = 1024
    assert capture.arm_samples(3, n_triggers=2) == 32  # two padded 16-word trigger records
    assert capture.cfg['supports_abort']


def test_soc_apis_and_legacy_rejection():
    soc = object.__new__(QickSoc)
    soc.ddr4_buf, soc.gens = ddr(), [awg()]
    assert soc.abort_ddr4_capture()['acknowledged']
    assert soc.set_awg_output_limits(0, -100, 400, True)['enabled']
    assert soc.get_awg_output_limits(0)['min_code'] == -100
    soc.ddr4_buf.cfg.pop('supports_abort')
    with pytest.raises(RuntimeError, match='v4'): soc.abort_ddr4_capture()


def test_v8_uses_same_fine_packet_and_manager():
    cfg = make_soccfg(tmux_ch=1)
    cfg['tprocs'][0]['pmem_size'] = 16384
    cfg['gens'][0].update(type='axis_awg_tuning_v8', frac=18, step_width=32,
                         extended_ramp_version=1, ramp_guard_cycles=0, ramp_startup_latency_cycles=0)
    p = QickProgram(cfg)
    p.set_pulse_registers(0, style='awg_set', value=0, duration=1)
    p.pulse(0, t=0)
    p.set_pulse_registers(0, style='awg_ramp', target=100, rise_start=15, rise_end=16,
                         fall_start=20, fall_end=35, end_target=-100)
    p.pulse(0, t=1)
    p.end()
    p.compile()
    assert p.binprog
