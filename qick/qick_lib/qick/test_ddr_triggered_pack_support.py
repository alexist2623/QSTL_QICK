"""Pure-Python tests for trigger-aligned DDR packer support."""
# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

import sys
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np


class _DefaultIP:
    bindto = []

    def __init__(self, description):
        self.description = description


class _Overlay:
    pass


def _install_pynq_stub():
    pynq = sys.modules.setdefault("pynq", types.ModuleType("pynq"))
    overlay = sys.modules.setdefault(
        "pynq.overlay", types.ModuleType("pynq.overlay")
    )
    buffer = sys.modules.setdefault(
        "pynq.buffer", types.ModuleType("pynq.buffer")
    )
    overlay.DefaultIP = _DefaultIP
    overlay.Overlay = _Overlay
    buffer.allocate = lambda shape, dtype=None, **kwargs: np.zeros(shape, dtype=dtype)
    pynq.overlay = overlay

    sys.modules.setdefault("xrfclk", types.ModuleType("xrfclk"))
    xrfdc = sys.modules.setdefault("xrfdc", types.ModuleType("xrfdc"))
    if not hasattr(xrfdc, "RFdc"):
        xrfdc.RFdc = type("RFdc", (), {})


_install_pynq_stub()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qick.drivers.readout import (  # noqa: E402
    AxisBufferDdrSampleV1,
    AxisBufferDdrSampleV2,
    AxisBufferDdrV1,
    _trace_trigger,
)
from qick.ip import QickMetadata  # noqa: E402
from qick.qick import QickSoc  # noqa: E402


def make_metadata(modtypes, bus_map, params=None):
    metadata = object.__new__(QickMetadata)
    metadata.modinfo = {
        name: {
            "type": modtype,
            "version": "1.0",
            "revision": 0,
            "params": (params or {}).get(name, {}),
        }
        for name, modtype in modtypes.items()
    }

    def trace_bus(blockname, portname):
        return bus_map.get((blockname, portname), [])

    metadata.trace_bus = trace_bus
    return metadata


def make_ddr_helper(burst_len=128):
    ddr = object.__new__(AxisBufferDdrV1)
    ddr._cfg = {"burst_len": burst_len}
    return ddr


def make_sample_ddr(max_words=4096):
    ddr = object.__new__(AxisBufferDdrSampleV1)
    object.__setattr__(ddr, "_cfg", {
        "samples_per_axi_word": 8,
        "bytes_per_axi_word": 32,
        "sample_capture": True,
        "maxlen": max_words,
    })
    object.__setattr__(ddr, "REGISTERS", {
        "control_reg": 0,
        "waddr_reg": 1,
        "nsamp_reg": 2,
        "ntrig_reg": 3,
        "stride_reg": 4,
        "status_reg": 5,
        "sample_count_reg": 6,
        "trigger_count_reg": 7,
        "sample_decim_reg": 8,
    })
    object.__setattr__(ddr, "mmio", types.SimpleNamespace(array=np.zeros(9, dtype=np.uint32)))
    object.__setattr__(ddr, "ddr4_array", np.zeros(max_words, dtype=np.uint32))
    return ddr


def make_sample_ddr_v2(max_words=4096):
    ddr = object.__new__(AxisBufferDdrSampleV2)
    object.__setattr__(ddr, "_cfg", {
        "samples_per_axi_word": 8,
        "bytes_per_axi_word": 32,
        "sample_capture": True,
        "supports_trigger_delay": True,
        "maxlen": max_words,
    })
    object.__setattr__(ddr, "REGISTERS", {
        "control_reg": 0,
        "waddr_reg": 1,
        "nsamp_reg": 2,
        "ntrig_reg": 3,
        "stride_reg": 4,
        "status_reg": 5,
        "sample_count_reg": 6,
        "trigger_count_reg": 7,
        "sample_decim_reg": 8,
        "trigger_delay_samples_reg": 9,
    })
    object.__setattr__(ddr, "mmio", types.SimpleNamespace(array=np.zeros(10, dtype=np.uint32)))
    object.__setattr__(ddr, "ddr4_array", np.zeros(max_words, dtype=np.uint32))
    return ddr


def make_rate_detection_ddr(fullpath="ddr"):
    ddr = object.__new__(AxisBufferDdrSampleV1)
    object.__setattr__(ddr, "_cfg", {
        "fullpath": fullpath,
        "fir_enabled": False,
        "fir_rate_detected_from_hwh": False,
    })
    return ddr


class _RateMetadata:
    def __init__(self, modtypes, bus_map, params, clocks=None):
        self.modtypes = modtypes
        self.bus_map = bus_map
        self.params = params
        self.clocks = clocks or {}

    def trace_bus(self, block, port):
        return self.bus_map.get((block, port), [])

    def mod2type(self, block):
        return self.modtypes[block]

    def get_param(self, block, name):
        return self.params[block][name]

    def get_fclk(self, block, port):
        return self.clocks[(block, port)]


def make_rate_soc(modtypes, bus_map, params, clocks=None):
    return types.SimpleNamespace(
        metadata=_RateMetadata(modtypes, bus_map, params, clocks)
    )


def load_hwh_metadata(path):
    parser = types.SimpleNamespace(root=ET.parse(path).getroot())
    return QickMetadata(types.SimpleNamespace(parser=parser))


class TestTriggeredPackMetadata(unittest.TestCase):
    def test_group_delay_compensated_fir_trigger_traces_back_to_tproc(self):
        signal_map = {
            ("ddr", "trigger"): [("fir", "capture_trigger")],
            ("fir", "trigger"): [("sync", "trigger_pulse")],
            ("sync", "trigger_in"): [("vec", "dout5")],
            ("vec", "din"): [("tproc", "m8_axis")],
        }
        block_types = {
            "ddr": "axis_buffer_ddr_sample_v1",
            "fir": "axis_fir_decim_300to1_v1",
            "sync": "axis_trigger_sync_v1",
            "vec": "qick_vec2bit",
            "tproc": "axis_tproc64x32_x8",
        }

        class Metadata:
            @staticmethod
            def trace_sig(block, port):
                return signal_map.get((block, port), [])

            @staticmethod
            def mod2type(block):
                return block_types[block]

        class TProc:
            @staticmethod
            def port2ch(port):
                if port != "m8_axis":
                    raise ValueError(port)
                return 8, "output"

        class Soc:
            metadata = Metadata()

            @staticmethod
            def _get_block(block):
                if block != "tproc":
                    raise KeyError(block)
                return TProc()

        self.assertEqual(_trace_trigger(Soc(), "ddr"), ("output", 8, 5))

    def test_trace_back_treats_triggered_pack_as_pass_through(self):
        metadata = make_metadata(
            {
                "ddr": "axis_buffer_ddr_v1",
                "clk": "axis_clock_converter",
                "pack": "axis_triggered_pack_32to256_v1",
                "sw": "axis_switch",
            },
            {
                ("ddr", "s_axis"): [("clk", "M_AXIS")],
                ("clk", "S_AXIS"): [("pack", "M_AXIS")],
                ("pack", "S_AXIS"): [("sw", "M00_AXIS")],
            },
        )

        self.assertEqual(
            metadata.trace_back("ddr", "s_axis", ["axis_switch"]),
            ("sw", "M00_AXIS", "axis_switch"),
        )

    def test_trace_forward_treats_triggered_pack_as_pass_through(self):
        metadata = make_metadata(
            {
                "ro": "axis_dyn_readout_v1",
                "pack": "axis_triggered_pack_32to256_v1",
                "ddr": "axis_buffer_ddr_v1",
            },
            {
                ("ro", "m_axis"): [("pack", "S_AXIS")],
                ("pack", "M_AXIS"): [("ddr", "s_axis")],
            },
        )

        self.assertEqual(
            metadata.trace_forward("ro", "m_axis", ["axis_buffer_ddr_v1"]),
            ("ddr", "s_axis", "axis_buffer_ddr_v1"),
        )

    def test_trace_back_treats_continuous_notch_decimator_as_pass_through(self):
        metadata = make_metadata(
            {
                "ddr": "axis_buffer_ddr_sample_v2",
                "notch": "axis_notch_decim_1m_to50k_v1",
                "fir": "axis_fir_decim_300to1_v1",
                "sw": "axis_switch",
            },
            {
                ("ddr", "s_axis"): [("notch", "m_axis")],
                ("notch", "s_axis"): [("fir", "m_axis")],
                ("fir", "s_axis"): [("sw", "M00_AXIS")],
            },
        )

        self.assertEqual(
            metadata.trace_back("ddr", "s_axis", ["axis_switch"]),
            ("sw", "M00_AXIS", "axis_switch"),
        )


class TestAxisBufferDdrSampleHelpers(unittest.TestCase):
    def test_bursts_for_samples_uses_32bit_sample_burst_alignment(self):
        ddr = make_ddr_helper(burst_len=128)

        self.assertEqual(ddr.samples_per_burst(), 128)
        self.assertEqual(ddr.bursts_for_samples(128), 1)
        self.assertEqual(ddr.bursts_for_samples(256), 2)

        with self.assertRaises(ValueError):
            ddr.bursts_for_samples(127)

    def test_arm_samples_calls_existing_arm_with_burst_count(self):
        ddr = make_ddr_helper(burst_len=128)
        calls = []

        def fake_arm(self, nt, force_overwrite=False):
            calls.append((nt, force_overwrite))

        ddr.arm = types.MethodType(fake_arm, ddr)

        self.assertEqual(ddr.arm_samples(256, force_overwrite=True), 2)
        self.assertEqual(calls, [(2, True)])


class TestFirSampleRateDetection(unittest.TestCase):
    def test_mock_hwh_detects_1msps_path(self):
        ddr = make_rate_detection_ddr()
        soc = make_rate_soc(
            {
                "ddr": "axis_buffer_ddr_sample_v1",
                "fir": "axis_fir_decim_300to1_v1",
            },
            {("ddr", "s_axis"): [("fir", "m_axis")]},
            {"fir": {"DECIM0": "10", "DECIM1": "10", "DECIM2": "3"}},
            {("fir", "aclk"): 300.0},
        )

        ddr._configure_fir_capture_path(soc)

        self.assertTrue(ddr.cfg["fir_rate_detected_from_hwh"])
        self.assertEqual(ddr.cfg["fir_rate_profile"], "1_msps")
        self.assertEqual(ddr.cfg["fir_decimation"], 300)
        self.assertEqual(ddr.cfg["fir_decimation_stages"], [10, 10, 3])
        self.assertAlmostEqual(ddr.cfg["stored_sample_rate_hz"], 1_000_000.0)
        self.assertAlmostEqual(ddr.cfg["stored_sample_period_us"], 1.0)

    def test_mock_hwh_detects_50ksps_path(self):
        ddr = make_rate_detection_ddr()
        soc = make_rate_soc(
            {
                "ddr": "axis_buffer_ddr_sample_v2",
                "notch": "axis_notch_decim_1m_to50k_v1",
                "fir": "axis_fir_decim_300to1_v1",
            },
            {
                ("ddr", "s_axis"): [("notch", "m_axis")],
                ("notch", "s_axis"): [("fir", "m_axis")],
            },
            {
                "notch": {"DECIMATION_PARAM": "20"},
                "fir": {"DECIM0": "10", "DECIM1": "10", "DECIM2": "3"},
            },
            {("fir", "aclk"): 300.0, ("notch", "aclk"): 300.0},
        )

        ddr._configure_fir_capture_path(soc)

        self.assertTrue(ddr.cfg["fir_rate_detected_from_hwh"])
        self.assertEqual(ddr.cfg["fir_rate_profile"], "50_ksps")
        self.assertEqual(ddr.cfg["fir_decimation"], 6000)
        self.assertEqual(ddr.cfg["fir_decimation_stages"], [10, 10, 3, 20])
        self.assertEqual(ddr.cfg["fir_hwh_chain"], ["fir", "notch"])
        self.assertAlmostEqual(ddr.cfg["stored_sample_rate_hz"], 50_000.0)
        self.assertAlmostEqual(ddr.cfg["stored_sample_period_us"], 20.0)
        self.assertAlmostEqual(
            ddr.cfg["fir_full_path_nominal_delay_us"],
            988.8903705411955,
        )

    def test_repository_hwh_files_identify_both_rate_profiles(self):
        qick_root = Path(__file__).resolve().parents[2]
        cases = [
            (
                qick_root / "firmware/projects/qstl_awg_tuning_fir/bitstream.hwh",
                "ddr4/axis_buffer_ddr_sample_v1_0",
                "1_msps",
                1_000_000.0,
            ),
            (
                qick_root / "firmware/projects/qstl_awg_tuning_fir_50ksps_notch/bitstream.hwh",
                "ddr4/axis_buffer_ddr_sample_v2_0",
                "50_ksps",
                50_000.0,
            ),
        ]

        for hwh_path, ddr_path, expected_profile, expected_rate_hz in cases:
            with self.subTest(hwh=str(hwh_path)):
                self.assertTrue(hwh_path.exists())
                ddr = make_rate_detection_ddr(ddr_path)
                ddr._configure_fir_capture_path(
                    types.SimpleNamespace(metadata=load_hwh_metadata(hwh_path))
                )
                self.assertNotIn("fir_detect_error", ddr.cfg)
                self.assertEqual(ddr.cfg["fir_rate_profile"], expected_profile)
                self.assertAlmostEqual(
                    ddr.cfg["stored_sample_rate_hz"], expected_rate_hz
                )


class TestQickSocFirRateApi(unittest.TestCase):
    @staticmethod
    def make_soc(rate_hz):
        soc = object.__new__(QickSoc)
        soc._cfg = {
            "readouts": [
                {"f_output": 300.0, "avgbuf_fullpath": "axis_avg_buffer_0"}
            ]
        }
        calls = []
        soc.ddr4_buf = types.SimpleNamespace(
            cfg={
                "sample_capture": True,
                "stored_sample_rate_hz": rate_hz,
            },
            set_switch=lambda path: calls.append(("switch", path)),
            arm_samples=lambda n_samples, **kwargs: calls.append(
                ("arm", n_samples, kwargs)
            ) or n_samples,
        )
        return soc, calls

    def test_rate_accessor_uses_hwh_detected_rate(self):
        for rate_hz, expected_profile_rate in (
            (1_000_000.0, 1.0),
            (50_000.0, 0.05),
        ):
            with self.subTest(rate_hz=rate_hz):
                soc, _ = self.make_soc(rate_hz)
                self.assertEqual(soc.get_ddr4_capture_rate(unit="hz"), rate_hz)
                self.assertEqual(
                    soc.get_ddr4_capture_rate(unit="msps"),
                    expected_profile_rate,
                )

    def test_target_rate_decimates_from_50ksps_not_raw_readout_rate(self):
        soc, calls = self.make_soc(50_000.0)

        result = soc.arm_ddr4_samples(
            ch=0,
            n_samples=128,
            target_rate=0.025,
        )

        self.assertEqual(result, 128)
        self.assertEqual(calls[0], ("switch", "axis_avg_buffer_0"))
        self.assertEqual(calls[1][0:2], ("arm", 128))
        self.assertEqual(calls[1][2]["sample_decim"], 2)


class TestAxisBufferDdrSampleV1(unittest.TestCase):
    def test_sample_arm_programs_sample_count_registers(self):
        ddr = make_sample_ddr()

        reserved = ddr.arm_samples(10, n_triggers=2, address=32, stride_bytes=64, sample_decim=300)

        self.assertEqual(reserved, 32)
        self.assertEqual(ddr.mmio.array[0], 1)
        self.assertEqual(ddr.mmio.array[1], 32)
        self.assertEqual(ddr.mmio.array[2], 10)
        self.assertEqual(ddr.mmio.array[3], 2)
        self.assertEqual(ddr.mmio.array[4], 64)
        self.assertEqual(ddr.mmio.array[8], 300)

    def test_sample_arm_rejects_unaligned_address_and_stride(self):
        ddr = make_sample_ddr()

        with self.assertRaises(ValueError):
            ddr.arm_samples(10, address=4)

        with self.assertRaises(ValueError):
            ddr.arm_samples(10, stride_bytes=40)

    def test_get_mem_samples_trims_zero_padding_per_trigger(self):
        ddr = make_sample_ddr()
        ddr.ddr4_array[:32] = np.arange(100, 132, dtype=np.uint32)

        data = ddr.get_mem_samples(10, n_triggers=2, start=0, stride_bytes=64)

        self.assertEqual(data.shape, (20, 2))
        self.assertEqual(data[0].tolist(), [100, 0])
        self.assertEqual(data[9].tolist(), [109, 0])
        self.assertEqual(data[10].tolist(), [116, 0])
        self.assertEqual(data[-1].tolist(), [125, 0])

    def test_compat_arm_interprets_nt_as_128_sample_transfers(self):
        ddr = make_sample_ddr()

        reserved = ddr.arm(2)

        self.assertEqual(reserved, 256)
        self.assertEqual(ddr.mmio.array[2], 256)
        self.assertEqual(ddr.mmio.array[3], 1)


class TestAxisBufferDdrSampleV2(unittest.TestCase):
    def test_arm_programs_trigger_delay_register(self):
        ddr = make_sample_ddr_v2()

        reserved = ddr.arm_samples(
            10,
            n_triggers=2,
            trigger_delay_samples=18,
        )

        self.assertEqual(reserved, 32)
        self.assertEqual(ddr.mmio.array[0], 1)
        self.assertEqual(ddr.mmio.array[2], 10)
        self.assertEqual(ddr.mmio.array[3], 2)
        self.assertEqual(ddr.mmio.array[8], 1)
        self.assertEqual(ddr.mmio.array[9], 18)

    def test_none_preserves_existing_trigger_delay(self):
        ddr = make_sample_ddr_v2()
        ddr.mmio.array[9] = 7

        ddr.arm_samples(8, trigger_delay_samples=None)

        self.assertEqual(ddr.mmio.array[9], 7)

    def test_negative_trigger_delay_is_rejected(self):
        ddr = make_sample_ddr_v2()

        with self.assertRaises(ValueError):
            ddr.arm_samples(8, trigger_delay_samples=-1)

        with self.assertRaisesRegex(ValueError, 'fit in 32 bits'):
            ddr.arm_samples(8, trigger_delay_samples=0x1_0000_0000)

    def test_rearm_while_busy_is_rejected(self):
        ddr = make_sample_ddr_v2()
        ddr.mmio.array[5] = 1

        with self.assertRaisesRegex(RuntimeError, 'previous capture is busy'):
            ddr.arm_samples(8, trigger_delay_samples=18)


if __name__ == "__main__":
    unittest.main()
