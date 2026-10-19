"""Versioned output metadata and current controls; no board connection or MMIO."""
from copy import deepcopy

import pytest

from qick.dac_current import _summed_awg_output
from qick.output_sum import (
    apply_output_sum_config, output_sum_config, validate_shared_dac_config,
)


class Metadata:
    def __init__(self, version=2, role="awg", bypass=False):
        self.kind = f"axis_output_sum_v{version}"
        self.port = "s0_axis" if role == "awg" else "s1_axis"
        self.parameters = dict(N_PTS="16", BYPASS=str(int(bypass)), PIPELINE_CYCLES="2")
        if version == 2:
            self.parameters["AWG_DELAY_CYCLES"] = "13"
        self.awg = ("awg", "m_axis", "axis_awg_tuning_v3")
        if version == 3:
            self.parameters["AWG_DELAY_CYCLES"] = "6"
            self.awg = ("awg", "m_axis", "axis_awg_tuning_v4")
        self.rf = ("rf", "m_axis", "axis_signal_gen_v6")

    def trace_forward(self, block, port, kinds):
        assert self.kind in kinds
        return "sum", self.port, self.kind

    def get_param(self, block, key):
        return self.parameters[key]

    def trace_back(self, block, port, kinds):
        result = self.awg if port == "s0_axis" else self.rf
        if result is not None:
            assert result[2] in kinds
        return result


@pytest.mark.parametrize("version,latency", [(1, 18), (2, 31)])
@pytest.mark.parametrize("role", ["awg", "rf"])
def test_role_latency_is_idempotent_and_restores_native(version, latency, role):
    original = dict(type="legacy", output_latency_cycles=16) if role == "awg" else dict(type="legacy")
    cfg = dict(original)
    route = output_sum_config(Metadata(version, role), role)
    assert route["output_sum_version"] == version
    assert route["post_output_latency_cycles"] == 2
    assert route["output_sum_awg_delay_cycles"] == (13 if version == 2 else 0)
    apply_output_sum_config(cfg, route)
    once = dict(cfg)
    for _ in range(4):
        apply_output_sum_config(cfg, route)
        assert cfg == once
    assert cfg["output_latency_cycles"] == (latency if role == "awg" else 31)
    apply_output_sum_config(cfg, {})
    assert cfg == original
    apply_output_sum_config(cfg, {})
    assert cfg == original


@pytest.mark.parametrize("role", ["awg", "rf"])
def test_version_switch_does_not_accumulate_latency(role):
    cfg = dict(output_latency_cycles=16) if role == "awg" else {}
    for version in (1, 2, 2, 1, 2, 1):
        apply_output_sum_config(cfg, output_sum_config(Metadata(version, role), role))
        assert cfg["output_latency_cycles"] == (18 if role == "awg" and version == 1 else 31)


@pytest.mark.parametrize("role", ["awg", "rf"])
def test_old_v1_config_without_native_tracking_is_supported(role):
    cfg = dict(output_sum_version=1, output_sum_role=role,
               post_output_latency_cycles=2, output_latency_cycles=18 if role == "awg" else 31)
    apply_output_sum_config(cfg, output_sum_config(Metadata(2, role), role))
    assert cfg["output_latency_cycles"] == 31
    apply_output_sum_config(cfg, {})
    assert cfg == (dict(output_latency_cycles=16) if role == "awg" else {})


def test_explicit_rf_native_latency_is_restored():
    cfg = dict(output_latency_cycles=29)
    apply_output_sum_config(cfg, output_sum_config(Metadata(2, "rf"), "rf"))
    apply_output_sum_config(cfg, {})
    assert cfg == dict(output_latency_cycles=29)


@pytest.mark.parametrize("version", [1, 2])
def test_bypass_delays_awg_and_never_claims_rf_input(version):
    route = output_sum_config(Metadata(version, bypass=True), "awg")
    assert route["output_sum_bypass"] and route["output_sum_rf"] is None
    cfg = dict(output_latency_cycles=16)
    apply_output_sum_config(cfg, route)
    assert cfg["output_latency_cycles"] == (31 if version == 2 else 18)
    with pytest.raises(RuntimeError, match="ignored bypass"):
        output_sum_config(Metadata(version, "rf", True), "rf")


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize("key,value", [("N_PTS", "8"), ("PIPELINE_CYCLES", "3"),
                                      ("BYPASS", "2"), ("N_PTS", "invalid"),
                                      ("PIPELINE_CYCLES", None)])
def test_invalid_hwh_parameters_fail_closed(version, key, value):
    metadata = Metadata(version)
    metadata.parameters[key] = value
    with pytest.raises(RuntimeError, match="combiner parameter"):
        output_sum_config(metadata, "awg")


@pytest.mark.parametrize("value", [None, "0", "12", "14", "13.5", "bad"])
def test_v2_requires_exact_13_cycle_delay(value):
    metadata = Metadata()
    if value is None:
        metadata.parameters.pop("AWG_DELAY_CYCLES")
    else:
        metadata.parameters["AWG_DELAY_CYCLES"] = value
    with pytest.raises(RuntimeError, match="combiner parameter"):
        output_sum_config(metadata, "awg")


@pytest.mark.parametrize("missing", ["awg", "rf"])
def test_missing_pair_is_rejected(missing):
    metadata = Metadata()
    setattr(metadata, missing, None)
    with pytest.raises(RuntimeError, match="Missing"):
        output_sum_config(metadata, "awg")


def test_inconsistent_identity_and_port_are_rejected():
    metadata = Metadata()
    with pytest.raises(RuntimeError, match="Inconsistent"):
        output_sum_config(metadata, "different_awg")
    metadata.port = "unsupported"
    with pytest.raises(RuntimeError, match="Unsupported output combiner input"):
        output_sum_config(metadata, "awg")


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize("role", ["awg", "rf"])
def test_shared_baseband_constraint(version, role):
    cfg = output_sum_config(Metadata(version, role), role)
    validate_shared_dac_config(cfg, 1, 0)
    validate_shared_dac_config(cfg, 1, None)
    for nqz, mixer in [(2, 0), (1, 10.)]:
        with pytest.raises(ValueError, match="shared baseband"):
            validate_shared_dac_config(cfg, nqz, mixer)
    validate_shared_dac_config({}, 2, 10.)


def test_no_combiner_does_not_change_legacy_configuration():
    metadata = Metadata()
    metadata.kind = "usp_rf_data_converter"
    assert output_sum_config(metadata, "awg") == {}
    cfg = dict(output_latency_cycles=16, unrelated="preserved")
    old = dict(cfg)
    apply_output_sum_config(cfg, {})
    assert cfg == old


@pytest.mark.parametrize("bad", [dict(output_sum_version=3), dict(output_sum_role="other"),
                                dict(post_output_latency_cycles=3), dict(output_sum_awg_delay_cycles=12)])
def test_invalid_latency_route_cannot_partially_mutate_configuration(bad):
    cfg = dict(output_latency_cycles=16)
    route = output_sum_config(Metadata(), "awg")
    route.update(bad)
    with pytest.raises(RuntimeError, match="latency profile"):
        apply_output_sum_config(cfg, route)
    assert cfg == dict(output_latency_cycles=16)


def pair(version):
    awg = dict(fullpath="awg", type="axis_awg_tuning_v4" if version == 3 else "axis_awg_tuning_v3",
               **output_sum_config(Metadata(version, "awg"), "awg"))
    rf = dict(fullpath="rf", type="axis_signal_gen_v6",
              **output_sum_config(Metadata(version, "rf"), "rf"))
    return [(0, awg), (1, rf)]


@pytest.mark.parametrize("version", [1, 2, 3])
def test_current_control_requires_consistent_hwh_linked_pair(version):
    assert _summed_awg_output(pair(version))
    for key, value in [
        ("output_sum_version", 3 - version), ("output_sum_version", 99),
        ("output_sum_block", "another_sum"), ("output_sum_awg", "wrong_awg"),
        ("output_sum_rf", "wrong_rf"), ("output_sum_role", "awg"),
        ("output_sum_bypass", True), ("type", "axis_signal_gen_v5"),
    ]:
        generators = deepcopy(pair(version))
        generators[1][1][key] = value
        assert not _summed_awg_output(generators), (key, value)
    assert not _summed_awg_output(pair(version)[:1])
    assert not _summed_awg_output(pair(version) + pair(version)[:1])


@pytest.mark.parametrize("version", [1, 2, 3])
def test_shared_awg_dac_current_write_and_hardware_readback(version):
    from types import SimpleNamespace
    from qick.dac_current import DacCurrentControl

    class Block:
        DACCompMode = 0
        OutputCurr = 20000
        writes = None

        def SetDACVOP(self, value):
            self.writes = value
            self.OutputCurr = value - value % 25

    class Soc(DacCurrentControl, dict):
        pass

    generators = [dict(g, dac="00") for _, g in pair(version)]
    block = Block()
    soc = Soc(gens=generators)
    soc.rf = SimpleNamespace(cfg={"ip_type": 2},
                             dac_tiles=[SimpleNamespace(blocks=[block])])
    actual = soc.set_dac_current("00", 30982)["00"]
    assert block.writes == 30982
    assert actual["current_ua"] == 30975
    assert actual["full_scale_mv"] == 1239
    assert actual["adjustable"] and actual["dc_output"]
    # The new version must still have an HWH-confirmed shared path.
    generators[1]["output_sum_block"] = "unrelated_sum"
    with pytest.raises(ValueError, match="read-only"):
        soc.set_dac_current("00", 20000)
    assert block.writes == 30982
