"""Fake hardware backends used by :mod:`qick.sim`.

These classes provide the small subset of PYNQ/RFSoC behavior required by QICK
driver construction and topology discovery. They do not touch real hardware.
"""

import sys
import types
from collections import OrderedDict

import numpy as np


class SimMMIO:
    """Minimal MMIO object with a uint32 backing array."""

    def __init__(self, words=4096):
        self.array = np.zeros(int(words), dtype=np.uint32)
        self.length = int(words) * 4

    def read(self, offset=0):
        return int(self.array[int(offset) // 4])

    def write(self, offset=0, data=0):
        self.array[int(offset) // 4] = np.uint32(data)


class _DefaultIP:
    """PYNQ DefaultIP stand-in used when PYNQ is unavailable."""

    bindto = []

    def __init__(self, description):
        self.description = description
        words = description.get("mmio_words", 4096) if isinstance(description, dict) else 4096
        self.mmio = SimMMIO(words=words)


def _allocate(shape, dtype=None, **kwargs):
    return np.zeros(shape, dtype=dtype)


def install_pynq_stubs():
    """Install lightweight ``pynq`` modules if the real package is absent."""
    if "pynq.overlay" not in sys.modules:
        pynq = sys.modules.setdefault("pynq", types.ModuleType("pynq"))
        overlay = types.ModuleType("pynq.overlay")
        overlay.DefaultIP = _DefaultIP
        sys.modules["pynq.overlay"] = overlay
        setattr(pynq, "overlay", overlay)
    if "pynq.buffer" not in sys.modules:
        pynq = sys.modules.setdefault("pynq", types.ModuleType("pynq"))
        buffer = types.ModuleType("pynq.buffer")
        buffer.allocate = _allocate
        sys.modules["pynq.buffer"] = buffer
        setattr(pynq, "buffer", buffer)


install_pynq_stubs()


class SimDMAChannel:
    """Fake DMA channel that records sends and fills receives from a queue."""

    def __init__(self, direction):
        self.direction = direction
        self.transfers = []
        self.recv_queue = []
        self.last_buffer = None

    def queue_recv(self, data):
        self.recv_queue.append(np.array(data, copy=True))

    def transfer(self, buffer, nbytes=None):
        self.last_buffer = buffer
        if self.direction == "send":
            self.transfers.append(np.array(buffer, copy=True))
        else:
            if self.recv_queue:
                src = self.recv_queue.pop(0)
                np.copyto(buffer[:len(src)], src.astype(buffer.dtype, copy=False))
                if len(buffer) > len(src):
                    buffer[len(src):] = 0
            else:
                buffer[...] = 0
            self.transfers.append(np.array(buffer, copy=True))

    def wait(self):
        return None


class SimDMA:
    """Fake AXI DMA block."""

    bindto = ["xilinx.com:ip:axi_dma:7.1"]

    def __init__(self, description):
        self.description = description
        self.cfg = {
            "type": description["type"].split(":")[-2],
            "fullpath": description["fullpath"],
        }
        self.mmio = SimMMIO()
        self.sendchannel = SimDMAChannel("send")
        self.recvchannel = SimDMAChannel("recv")

    def __getitem__(self, key):
        return self.cfg[key]


class SimDummyIP:
    """Visible placeholder for IPs that do not need a specialized driver."""

    bindto = []

    def __init__(self, description):
        self.description = description
        self.mmio = SimMMIO()
        self.cfg = {
            "type": description["type"].split(":")[-2] if ":" in description["type"] else description["type"],
            "fullpath": description["fullpath"],
        }
        self.NSL = int(description.get("parameters", {}).get("NUM_SI", 16))
        self.NMI = int(description.get("parameters", {}).get("NUM_MI", 16))
        self.selected = {}

    def __getitem__(self, key):
        return self.cfg[key]

    def configure_connections(self, soc):
        self.cfg["revision"] = soc.metadata.mod2rev(self["fullpath"])
        self.cfg["version"] = soc.metadata.mod2version(self["fullpath"])

    def sel(self, mst=0, slv=0):
        self.selected[int(mst)] = int(slv)

    def disable_ports(self):
        self.selected.clear()


class SimRFdc(SimDummyIP):
    """Fake RFDC config object used by generator/readout drivers."""

    bindto = [
        "xilinx.com:ip:usp_rf_data_converter:2.3",
        "xilinx.com:ip:usp_rf_data_converter:2.4",
        "xilinx.com:ip:usp_rf_data_converter:2.6",
    ]

    def __init__(self, description, rf_config=None):
        super().__init__(description)
        self.cfg.update(self._default_rf_config())
        if rf_config:
            self._deep_update(self.cfg, rf_config)
        self.mixer_freqs = {}
        self.nyquist = {}

    @staticmethod
    def _deep_update(dst, src):
        for key, value in src.items():
            if isinstance(value, dict) and isinstance(dst.get(key), dict):
                SimRFdc._deep_update(dst[key], value)
            else:
                dst[key] = value
        return dst

    @staticmethod
    def _default_rf_config():
        dacs = OrderedDict()
        adcs = OrderedDict()
        for name in ["00", "01", "02", "03", "10", "11", "12", "13", "20", "21", "22", "23", "30", "31", "32", "33"]:
            dacs[name] = {
                "fs": 6144.0,
                "fs_mult": 1,
                "fs_div": 1,
                "interpolation": 1,
                "f_fabric": 384.0,
                "f_dds": 6144.0,
                "fdds_div": 1,
            }
            adcs[name] = {
                "fs": 4096.0,
                "fs_mult": 1,
                "fs_div": 1,
                "decimation": 1,
                "f_fabric": 256.0,
                "f_output": 4096.0,
                "coupling": "DC",
            }
        return {
            "tiles": {
                "dac": {i: {"f_ref": 245.76, "f_out": 384.0, "fs": 6144.0} for i in range(4)},
                "adc": {i: {"f_ref": 245.76, "f_out": 256.0, "fs": 4096.0} for i in range(4)},
            },
            "dacs": dacs,
            "adcs": adcs,
            "clk_groups": [[("tproc", 0)], [("dac", 0)], [("adc", 0)]],
        }

    def map_clocks(self, soc):
        return None

    def configure_sample_rates(self, dac_sample_rates=None, adc_sample_rates=None):
        return None

    def set_mixer_freq(self, dac, f, phase_reset=True):
        self.mixer_freqs[dac] = float(f)

    def get_mixer_freq(self, dac):
        return self.mixer_freqs.get(dac, 0.0)

    def set_nyquist(self, dac, nqz):
        self.nyquist[dac] = int(nqz)

    def get_nyquist(self, dac):
        return self.nyquist.get(dac, 1)

    def clocks_locked(self):
        return [True], [True]


class SimTProc:
    """Small tProcessor helper for tests that do not instantiate the real driver."""

    def __init__(self):
        self.cfg = {"type": "axis_tproc64x32_x8", "f_time": 100.0, "output_pins": [], "start_pin": None}

    def __getitem__(self, key):
        return self.cfg[key]

    def configure(self, *args, **kwargs):
        self.cfg.setdefault("pmem_size", 4096)

    @staticmethod
    def port2ch(port):
        chtype = {"m": "output", "s": "input"}[port[0]]
        return int(port.split("_")[0][1:]) - 1, chtype


__all__ = [
    "SimMMIO",
    "SimDMA",
    "SimDMAChannel",
    "SimDummyIP",
    "SimRFdc",
    "SimTProc",
    "install_pynq_stubs",
]
