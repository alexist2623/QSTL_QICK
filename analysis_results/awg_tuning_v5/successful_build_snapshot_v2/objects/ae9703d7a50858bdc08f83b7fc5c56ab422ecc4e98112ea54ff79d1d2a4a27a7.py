"""Discover the optional v4 output stage without changing legacy generators."""

SUM_TYPE = "axis_output_sum_v1"


def output_sum_config(metadata, fullpath):
    """Read physical pairing from HWH, never from logical channel numbering."""
    block, port, kind = metadata.trace_forward(
        fullpath, "m_axis", [SUM_TYPE, "usp_rf_data_converter"])
    if kind != SUM_TYPE:
        return {}
    parameters = {key: int(metadata.get_param(block, key))
                  for key in ("N_PTS", "BYPASS", "PIPELINE_CYCLES")}
    if (parameters["N_PTS"] != 16 or parameters["PIPELINE_CYCLES"] != 2
            or parameters["BYPASS"] not in (0, 1)):
        raise RuntimeError(f"Unsupported output combiner parameters on {block}: {parameters}")
    if port not in ("s0_axis", "s1_axis"):
        raise RuntimeError(f"Unsupported output combiner input {block}/{port}")
    awg = metadata.trace_back(block, "s0_axis", ["axis_awg_tuning_v3"])
    if awg is None:
        raise RuntimeError(f"Missing v3 AWG input on {block}")
    bypass = bool(parameters["BYPASS"])
    rf = None if bypass else metadata.trace_back(block, "s1_axis", ["axis_signal_gen_v6"])
    if not bypass and rf is None:
        raise RuntimeError(f"Missing DDS input on {block}")
    if bypass and port != "s0_axis":
        raise RuntimeError(f"Generator connected to ignored bypass input on {block}")
    return dict(output_sum_version=1, output_sum_block=block,
                output_sum_role="awg" if port == "s0_axis" else "rf",
                output_sum_bypass=bypass, output_sum_awg=awg[0],
                output_sum_rf=None if rf is None else rf[0],
                post_output_latency_cycles=parameters["PIPELINE_CYCLES"])


def apply_output_sum_config(cfg, route):
    """Apply the additional AWG latency once, even when reconnected."""
    if not route:
        return
    base = int(cfg.get("output_latency_cycles", 0)) - int(cfg.get("post_output_latency_cycles", 0))
    cfg.update(route)
    if route["output_sum_role"] == "awg":
        cfg["output_latency_cycles"] = base + route["post_output_latency_cycles"]
    else:
        # axis_signal_gen_v6 has 29 clocks from its command input to samples.
        # The existing three command-routing and ten output-slice clocks are
        # common to AWG and RF and are excluded from both waveform references.
        cfg["output_latency_cycles"] = 29 + route["post_output_latency_cycles"]


def validate_shared_dac_config(gencfg, nqz, mixer_freq):
    """The AWG physical output must stay baseband, including RF-only programs."""
    if not gencfg.get("output_sum_version"):
        return
    if int(nqz) != 1 or mixer_freq not in (None, 0, 0.0):
        raise ValueError(
            "The v4 AWG/RF output uses a shared baseband DAC; Nyquist zone 1 "
            "and zero mixer frequency are required for both generators.")
