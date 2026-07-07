"""Tests for the public qick.sim.QickSim API."""
# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _param(name, value):
    return f'<PARAMETER NAME="{name}" VALUE="{value}"/>'


def _bus(name, bus):
    return f'<BUSINTERFACE NAME="{name}" BUSNAME="{bus}"/>'


def _port(name, sig, direction="I", freq=None):
    freq_attr = "" if freq is None else f' CLKFREQUENCY="{freq}"'
    return f'<PORT NAME="{name}" SIGNAME="{sig}" DIR="{direction}"{freq_attr}/>'


def _module(fullname, modtype, version, params=None, buses=None, ports=None):
    params = [] if params is None else params
    buses = [] if buses is None else buses
    ports = [] if ports is None else ports
    return f"""
    <MODULE FULLNAME="/{fullname}" MODTYPE="{modtype}" HWVERSION="{version}" COREREVISION="1">
      <PARAMETERS>{''.join(params)}</PARAMETERS>
      <BUSINTERFACES>{''.join(buses)}</BUSINTERFACES>
      <PORTS>{''.join(ports)}</PORTS>
    </MODULE>
    """


def make_awg_hwh(path):
    text = f"""<EDKSYSTEM TIMESTAMP="sim">
    <MODULES>
    {_module('zynq_ultra_ps_e_0', 'zynq_ultra_ps_e', '3.5',
             ports=[_port('pl_clk0', 'pl_clk0', 'O', '100000000')])}
    {_module('axis_tproc64x32_x8_0', 'axis_tproc64x32_x8', '1.0',
             params=[_param('DMEM_N', '10'), _param('PMEM_N', '10')],
             buses=[_bus('m1_axis', 'tproc_m1')],
             ports=[_port('aclk', 'pl_clk0', freq='100000000')])}
    {_module('axis_tmux_v1_0', 'axis_tmux_v1', '1.0',
             buses=[_bus('s_axis', 'tproc_m1'), _bus('m0_axis', 'tmux_m0')])}
    {_module('axis_awg_tuning_v1_0', 'axis_awg_tuning_v1', '1.0',
             params=[
                 _param('N_PTS', '16'), _param('B', '16'), _param('FRAC', '16'),
                 _param('CMD_WIDTH', '160'), _param('STEP_WIDTH', '24'),
                 _param('DURATION_WIDTH', '23'), _param('FIXED_WIDTH', '48'),
                 _param('EXTRA_Y_PIPE_STAGES', '1')],
             buses=[_bus('s_axis', 'tmux_m0'), _bus('m_axis', 'awg_m')])}
    {_module('usp_rf_data_converter_0', 'usp_rf_data_converter', '2.6',
             buses=[_bus('s00_axis', 'awg_m')])}
    </MODULES>
    <EXTERNALPORTS/>
    </EDKSYSTEM>"""
    path.write_text(text)


class TestQickSim(unittest.TestCase):
    def test_package_import(self):
        from qick.sim import QickSim, WaveformResult

        self.assertIsNotNone(QickSim)
        self.assertIsNotNone(WaveformResult)

    def test_fake_mmio_driver_registers(self):
        from qick.sim.virtual_hw import install_pynq_stubs

        install_pynq_stubs()
        from qick.awg_tuning import AxisAwgTuningV1

        drv = AxisAwgTuningV1({
            "type": "QICK:QICK:axis_awg_tuning_v1:1.0",
            "fullpath": "axis_awg_tuning_v1_0",
            "parameters": {
                "N_PTS": "16",
                "B": "16",
                "FRAC": "16",
                "CMD_WIDTH": "160",
                "STEP_WIDTH": "24",
                "DURATION_WIDTH": "23",
                "FIXED_WIDTH": "48",
                "EXTRA_Y_PIPE_STAGES": "1",
            },
        })
        drv.current_value_reg = 1234
        self.assertEqual(int(drv.current_value_reg), 1234)

    def test_hwh_scan_discovers_awg_tuning_as_generator(self):
        from qick.sim import QickSim

        with tempfile.TemporaryDirectory() as tmpdir:
            bit = Path(tmpdir) / "mini.bit"
            hwh = Path(tmpdir) / "mini.hwh"
            bit.write_bytes(b"sim")
            make_awg_hwh(hwh)

            sim = QickSim(bit)

        self.assertEqual(len(sim.gens), 1)
        self.assertEqual(len(sim.awg_tunings), 1)
        self.assertEqual(sim.gens[0], sim.awg_tunings[0])
        self.assertEqual(sim["gens"][0]["gen_type"], "awg_tuning")
        self.assertEqual(sim["gens"][0]["tproc_ch"], 0)
        self.assertEqual(sim["gens"][0]["tmux_ch"], 0)

    def test_simulate_program_accepts_qickprogram_like_object(self):
        from qick.sim import QickSim

        with tempfile.TemporaryDirectory() as tmpdir:
            bit = Path(tmpdir) / "mini.bit"
            hwh = Path(tmpdir) / "mini.hwh"
            bit.write_bytes(b"sim")
            make_awg_hwh(hwh)
            sim = QickSim(bit)

            cmd = sim.gens[0].set_cmd(1000)
            cmd |= sim.gens[0]["tmux_ch"] << 152
            words = [(cmd >> (32 * i)) & 0xFFFFFFFF for i in range(5)]
            prog = type("Prog", (), {
                "prog_list": [
                    {"name": "regwi", "args": (0, 1, words[0])},
                    {"name": "regwi", "args": (0, 2, words[1])},
                    {"name": "regwi", "args": (0, 3, words[2])},
                    {"name": "regwi", "args": (0, 4, words[3])},
                    {"name": "regwi", "args": (0, 5, words[4])},
                    {"name": "regwi", "args": (0, 6, 20)},
                    {"name": "set", "args": (0, 0, 1, 2, 3, 4, 5, 6)},
                    {"name": "end", "args": ()},
                ]
            })()

            result = sim.simulate_program(prog, cycles=32)

        self.assertEqual(result.summary()["accepted"], 1)
        lanes = result.channel_results["lane_samples"]["gen0"]
        self.assertTrue(np.all(lanes[22] == 1000))


if __name__ == "__main__":
    unittest.main()
