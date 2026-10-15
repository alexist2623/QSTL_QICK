"""Connect the production driver to retained v3/v4 and candidate v5 HWH offline."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest
from qick.sim import QickSim  # installs desktop PYNQ stubs; never a board overlay
from qick.dac_current import DacCurrentControl
from qick.drivers.generator import AbsSignalGen
from qick.ip import QickMetadata

ROOT = Path(__file__).resolve().parents[4]
HWH = {
    3: ROOT / "qick/firmware/projects/qstl_awg_v3/bitstream.hwh",
    4: ROOT / "qick/firmware/projects/qstl_awg_v4/bitstream.hwh",
    5: Path("F:/Vivado_Output/a5full1/bitstream.hwh"),
}
PAIRS = [("axis_signal_gen_v6_0", "axis_awg_tuning_v3_4", "10"),
         ("axis_signal_gen_v6_1", "axis_awg_tuning_v3_5", "11"),
         ("axis_signal_gen_v6_3", "axis_awg_tuning_v3_6", "12")]
BYPASS = [(f"axis_awg_tuning_v3_{suffix}", f"2{index}")
          for index, suffix in enumerate((8, 9, 10, 11))]
NAMES = [name for rf, awg, _ in PAIRS for name in (rf, awg)] + [
    "axis_signal_gen_v6_2", "axis_square_pulse_v1_0"] + [name for name, _ in BYPASS]


def actual_configuration(version):
    metadata = QickMetadata(SimpleNamespace(parser=SimpleNamespace(root=ET.parse(HWH[version]).getroot())))
    class Soc(dict):
        def _get_block(self, block):
            assert block == "usp_rf_data_converter_0"
            return self.rf_stub
    soc = Soc(rf={"dacs": {f"{t}{b}": dict(fs=4800., fs_mult=16, fs_div=1,
                interpolation=1, f_fabric=300.) for t in range(4) for b in range(4)}})
    soc.metadata = metadata
    soc.rf_stub = object()
    configs = {}
    for name in NAMES:
        generator = object.__new__(AbsSignalGen)
        generator._cfg = dict(fullpath=name, type=metadata.mod2type(name))
        if name.startswith("axis_awg_tuning"):
            generator._cfg["output_latency_cycles"] = 16
        for _ in range(3):
            before = dict(generator.cfg)
            AbsSignalGen.configure_connections(generator, soc)
            if "dac" in before:
                assert generator.cfg == before
        assert generator.rf is soc.rf_stub
        configs[name] = dict(generator.cfg)
    return metadata, configs


@pytest.fixture(scope="module", params=[3, 4, 5])
def firmware(request):
    return request.param, actual_configuration(request.param)


@pytest.mark.parametrize("rf,awg,dac", PAIRS)
def test_actual_pair_routes_and_native_delays(firmware, rf, awg, dac):
    version, (_, configs) = firmware
    a, r = configs[awg], configs[rf]
    if version == 3:
        assert a["output_latency_cycles"] == 16
        assert "output_latency_cycles" not in r
        assert a["dac"] == dac and r["dac"] in ("00", "01", "03")
        assert not any("output_sum_version" in cfg for cfg in configs.values())
        return
    assert a["dac"] == r["dac"] == dac
    assert a["output_latency_cycles"] == (18 if version == 4 else 31)
    assert r["output_latency_cycles"] == 31
    for cfg, role in [(a, "awg"), (r, "rf")]:
        assert cfg["output_sum_version"] == version - 3
        assert cfg["output_sum_role"] == role
        assert cfg["output_sum_awg"] == awg and cfg["output_sum_rf"] == rf
        assert cfg["output_sum_awg_delay_cycles"] == (0 if version == 4 else 13)
        assert cfg["post_output_latency_cycles"] == 2
        assert cfg["output_sum_bypass"] is False


@pytest.mark.parametrize("awg,dac", BYPASS)
def test_all_four_bypass_outputs(firmware, awg, dac):
    version, (_, configs) = firmware
    cfg = configs[awg]
    assert cfg["dac"] == dac
    assert cfg["output_latency_cycles"] == {3: 16, 4: 18, 5: 31}[version]
    if version >= 4:
        assert cfg["output_sum_bypass"] is True
        assert cfg["output_sum_rf"] is None


@pytest.mark.parametrize("name,dac", [("axis_signal_gen_v6_2", "02"), ("axis_square_pulse_v1_0", "13")])
def test_uncombined_generators_retain_original_behavior(firmware, name, dac):
    _, (_, configs) = firmware
    assert configs[name]["dac"] == dac
    assert "output_sum_version" not in configs[name]
    assert "output_latency_cycles" not in configs[name]


def test_shared_current_writes_one_actual_dac_and_rejects_mismatched_version(firmware):
    version, (_, configs) = firmware
    configs = deepcopy(configs)
    class Block:
        OutputCurr = 10000
        DACCompMode = 0
        def __init__(self): self.writes = []
        def SetDACVOP(self, current):
            self.writes.append(current)
            self.OutputCurr = current
    class Soc(DacCurrentControl, dict): pass
    soc = Soc(gens=list(configs.values()))
    soc.rf = SimpleNamespace(cfg={"ip_type": 2}, dac_tiles=[
        SimpleNamespace(blocks=[Block() for _ in range(4)]) for _ in range(4)])
    for rf, awg, dac in PAIRS:
        record = soc.get_dac_current_settings()[dac]
        assert record["dc_output"] and record["adjustable"]
        soc.set_dac_current(dac, 16000)
        assert soc.rf.dac_tiles[int(dac[0])].blocks[int(dac[1])].writes == [16000]
        if version >= 4:
            assert len(record["channels"]) == 2
            configs[rf]["output_sum_version"] = 3 if version == 5 else 2
            assert not soc.get_dac_current_settings()[dac]["adjustable"]
            with pytest.raises(ValueError, match="read-only"):
                soc.set_dac_current(dac, 17000)
