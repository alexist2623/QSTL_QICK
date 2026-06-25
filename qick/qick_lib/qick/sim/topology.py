"""HWH scanning and driver binding for :class:`qick.sim.QickSim`."""

import inspect
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from .virtual_hw import SimDMA, SimDummyIP, SimRFdc, install_pynq_stubs

install_pynq_stubs()


class SimHwhParser:
    """Small parser shim exposing ``root`` like PYNQ's HWH parser."""

    def __init__(self, hwhfile):
        self.hwhfile = str(hwhfile)
        self.root = ElementTree.parse(hwhfile).getroot()


def _module_parameters(module):
    return {
        param.get("NAME"): param.get("VALUE")
        for param in module.findall("./PARAMETERS/PARAMETER")
        if param.get("NAME") is not None
    }


def _vlnv_for_module(module):
    modtype = module.get("MODTYPE")
    version = module.get("HWVERSION") or "1.0"
    if modtype is None:
        return "unknown:unknown:unknown:0.0"
    if modtype.startswith("axi_") or modtype in {
        "axis_clock_converter",
        "axis_broadcaster",
        "axis_register_slice",
        "axis_switch",
        "blk_mem_gen",
        "smartconnect",
        "usp_rf_data_converter",
        "zynq_ultra_ps_e",
        "proc_sys_reset",
        "xlconstant",
        "xlconcat",
        "util_ds_buf",
        "c_shift_ram",
        "ddr4",
    }:
        return f"xilinx.com:ip:{modtype}:{version}"
    return f"QICK:QICK:{modtype}:{version}"


def _iter_driver_classes():
    from qick import awg_tuning  # noqa: WPS433
    from qick.drivers import generator, readout, tproc  # noqa: WPS433

    modules = [awg_tuning, generator, readout, tproc]
    for module in modules:
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if hasattr(cls, "bindto"):
                yield cls
    yield SimRFdc
    yield SimDMA


def build_driver_registry():
    """Build ``VLNV -> driver class`` from imported QICK drivers."""
    registry = {}
    for cls in _iter_driver_classes():
        for vlnv in getattr(cls, "bindto", []):
            registry[vlnv] = cls
    return registry


def build_ip_dict(root, *, strict=False):
    """Build a PYNQ-like ``ip_dict`` from HWH XML modules."""
    registry = build_driver_registry()
    ip_dict = {}
    unmatched = []
    for module in root.findall("./MODULES/MODULE"):
        fullpath = module.get("FULLNAME", "").lstrip("/")
        if not fullpath:
            continue
        vlnv = _vlnv_for_module(module)
        driver = registry.get(vlnv, SimDummyIP)
        if driver is SimDummyIP:
            unmatched.append(f"{fullpath} ({vlnv})")
        ip_dict[fullpath] = {
            "fullpath": fullpath,
            "type": vlnv,
            "parameters": _module_parameters(module),
            "driver": driver,
        }
    return ip_dict, unmatched


def locate_hwh(bitfile, hwhfile=None):
    """Return the matching HWH path for a bitfile."""
    bitpath = Path(bitfile)
    if hwhfile is not None:
        hwhpath = Path(hwhfile)
    else:
        hwhpath = bitpath.with_suffix(".hwh")
    if not bitpath.exists():
        raise FileNotFoundError(f"bitfile does not exist: {bitpath}")
    if not hwhpath.exists():
        raise FileNotFoundError(f"matching HWH file does not exist: {hwhpath}")
    return bitpath, hwhpath


__all__ = [
    "SimHwhParser",
    "build_driver_registry",
    "build_ip_dict",
    "locate_hwh",
]
