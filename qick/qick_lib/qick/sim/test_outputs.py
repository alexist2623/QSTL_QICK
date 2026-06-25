"""Tests for RFDC-facing QickSim outputs, clocks, plotting, and CSV export."""

import csv
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


def make_mixed_hwh(path):
    text = f"""<EDKSYSTEM TIMESTAMP="sim">
    <MODULES>
    {_module('zynq_ultra_ps_e_0', 'zynq_ultra_ps_e', '3.5',
             ports=[_port('pl_clk0', 'pl_clk0', 'O', '100000000')])}
    {_module('axis_tproc64x32_x8_0', 'axis_tproc64x32_x8', '1.0',
             params=[_param('DMEM_N', '10'), _param('PMEM_N', '10')],
             buses=[_bus('m1_axis', 'tproc_m1')],
             ports=[_port('aclk', 'pl_clk0', freq='100000000')])}
    {_module('axis_tmux_v1_0', 'axis_tmux_v1', '1.0',
             buses=[_bus('s_axis', 'tproc_m1'), _bus('m0_axis', 'tmux_m0'), _bus('m1_axis', 'tmux_m1')])}
    {_module('axis_signal_gen_v6_0', 'axis_signal_gen_v6', '1.0',
             params=[_param('N', '10'), _param('N_DDS', '4'), _param('GEN_DDS', 'TRUE'), _param('ENVELOPE_TYPE', 'COMPLEX')],
             buses=[_bus('s0_axis', 'dma_gen'), _bus('s1_axis', 'tmux_m0'), _bus('m_axis', 'sig_m')])}
    {_module('axi_dma_gen', 'axi_dma', '7.1',
             buses=[_bus('M_AXIS', 'dma_gen')])}
    {_module('axis_awg_tuning_v1_4', 'axis_awg_tuning_v1', '1.0',
             params=[
                 _param('N_PTS', '4'), _param('B', '16'), _param('FRAC', '16'),
                 _param('CMD_WIDTH', '160'), _param('STEP_WIDTH', '24'),
                 _param('DURATION_WIDTH', '23'), _param('FIXED_WIDTH', '48'),
                 _param('EXTRA_Y_PIPE_STAGES', '1')],
             buses=[_bus('s_axis', 'tmux_m1'), _bus('m_axis', 'awg_m')])}
    {_module('usp_rf_data_converter_0', 'usp_rf_data_converter', '2.6',
             buses=[_bus('s00_axis', 'sig_m'), _bus('s10_axis', 'awg_m')])}
    </MODULES>
    <EXTERNALPORTS/>
    </EDKSYSTEM>"""
    path.write_text(text)


def cmd_words(cmd):
    return [(int(cmd) >> (32 * i)) & 0xFFFFFFFF for i in range(5)]


def append_set_instruction(prog, tproc_ch, cmd, t, base=1):
    for idx, word in enumerate(cmd_words(cmd)):
        prog.append({"name": "regwi", "args": (0, base + idx, word)})
    prog.append({"name": "regwi", "args": (0, base + 5, int(t))})
    prog.append({"name": "set", "args": (int(tproc_ch), 0, base, base + 1, base + 2, base + 3, base + 4, base + 5)})


class TestQickSimOutputs(unittest.TestCase):
    def make_sim(self, **kwargs):
        tmpdir = tempfile.TemporaryDirectory()
        bit = Path(tmpdir.name) / "mixed.bit"
        hwh = Path(tmpdir.name) / "mixed.hwh"
        bit.write_bytes(b"sim")
        make_mixed_hwh(hwh)
        sim = self._qicksim()(bit, strict=False, **kwargs)
        self.addCleanup(tmpdir.cleanup)
        return sim

    @staticmethod
    def _qicksim():
        from qick.sim import QickSim

        return QickSim

    def test_clock_config(self):
        sim = self.make_sim(dac_clk=5000.0, adc_clk=2500.0, fabric_clk=250.0, tproc_clk=125.0)

        self.assertEqual(sim["rf"]["dacs"]["00"]["fs"], 5000.0)
        self.assertEqual(sim["rf"]["dacs"]["00"]["f_fabric"], 250.0)
        self.assertEqual(sim["rf"]["adcs"]["00"]["fs"], 2500.0)
        self.assertEqual(sim["tprocs"][0]["f_time"], 125.0)

    def test_awg_and_signalgen_outputs_and_topology(self):
        sim = self.make_sim(clocks={
            "tproc": 200.0,
            "default_dac": {"fs": 4000.0, "fabric": 250.0, "interpolation": 4},
            "default_adc": {"fs": 2000.0, "fabric": 125.0, "decimation": 2},
        })
        self.assertEqual([gen["fullpath"] for gen in sim["gens"]], ["axis_signal_gen_v6_0", "axis_awg_tuning_v1_4"])
        self.assertEqual(sim["gens"][0]["dac"], "00")
        self.assertEqual(sim["gens"][1]["dac"], "10")

        sig_cmd = (
            0x04000000
            | (30000 << 96)
            | (8 << 128)
            | (1 << 144)
            | (1 << 148)
            | (sim["gens"][0]["tmux_ch"] << 152)
        )
        awg_cmd = sim.gens[1].set_cmd(1000) | (sim["gens"][1]["tmux_ch"] << 152)
        prog = []
        append_set_instruction(prog, sim["gens"][0]["tproc_ch"], sig_cmd, 10, base=1)
        append_set_instruction(prog, sim["gens"][1]["tproc_ch"], awg_cmd, 20, base=10)
        prog.append({"name": "end", "args": ()})

        result = sim.simulate_program(type("Prog", (), {"prog_list": prog})(), cycles=48)

        self.assertIn("axis_signal_gen_v6_0", result.outputs)
        self.assertIn("axis_awg_tuning_v1_4", result.outputs)
        self.assertEqual(result.outputs["axis_signal_gen_v6_0"].dac, "00")
        self.assertEqual(result.outputs["axis_awg_tuning_v1_4"].dac, "10")
        self.assertEqual(result.outputs["axis_signal_gen_v6_0"].lane_samples.shape, (48, 4))
        self.assertGreater(np.count_nonzero(result.get_output_samples("axis_signal_gen_v6_0", valid_only=True)), 0)
        self.assertTrue(np.all(result.outputs["axis_awg_tuning_v1_4"].lane_samples[22] == 1000))
        self.assertAlmostEqual(result.outputs["axis_signal_gen_v6_0"].sample_times_us[0, 1], 1.0 / 4000.0)

    def test_plot_and_csv(self):
        sim = self.make_sim()
        awg_cmd = sim.gens[1].set_cmd(512) | (sim["gens"][1]["tmux_ch"] << 152)
        prog = []
        append_set_instruction(prog, sim["gens"][1]["tproc_ch"], awg_cmd, 4)
        prog.append({"name": "end", "args": ()})
        result = sim.simulate_program(type("Prog", (), {"prog_list": prog})(), cycles=16)

        try:
            fig, _ = result.plot_outputs(show=False, samples=16)
            self.assertIsNotNone(fig)
        except RuntimeError as exc:
            self.assertIn("matplotlib", str(exc))

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = result.to_csv(Path(tmpdir) / "sim_out")
            self.assertTrue(paths["packed"])
            self.assertTrue(paths["lanes"])
            self.assertTrue(paths["events"].exists())
            with paths["lanes"][0].open() as f:
                header = next(csv.reader(f))
            self.assertEqual(header, ["sample_index", "slow_word", "lane", "time_us", "value"])


if __name__ == "__main__":
    unittest.main()
