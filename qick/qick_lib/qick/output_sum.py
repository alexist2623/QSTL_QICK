"""Discover versioned AWG/RF output stages without changing legacy generators."""

SUM_TYPE = "axis_output_sum_v1"
SUM_TYPES = {SUM_TYPE: 1, "axis_output_sum_v2": 2, "axis_output_sum_v3": 3, "axis_output_sum_v7": 7}


def output_sum_config(metadata, fullpath):
    """Read physical pairing from HWH, never from logical channel numbering."""
    block, port, kind = metadata.trace_forward(
        fullpath, "m_axis", [*SUM_TYPES, "usp_rf_data_converter"])
    if kind not in SUM_TYPES:
        return {}
    version = SUM_TYPES[kind]
    keys = ["N_PTS", "BYPASS", "PIPELINE_CYCLES"]
    if version >= 2:
        keys.append("AWG_DELAY_CYCLES")
    try:
        parameters = {key: int(metadata.get_param(block, key)) for key in keys}
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Missing or invalid output combiner parameter on {block}") from exc
    if (parameters["N_PTS"] != 16 or parameters["PIPELINE_CYCLES"] != 2
            or parameters["BYPASS"] not in (0, 1)
            or (version >= 2 and parameters["AWG_DELAY_CYCLES"] != {2: 13, 3: 6, 7: 2}[version])):
        raise RuntimeError(f"Unsupported output combiner parameters on {block}: {parameters}")
    if port not in ("s0_axis", "s1_axis"):
        raise RuntimeError(f"Unsupported output combiner input {block}/{port}")
    awg = metadata.trace_back(block, "s0_axis", [{3: "axis_awg_tuning_v4", 7: "axis_awg_tuning_v7"}.get(version, "axis_awg_tuning_v3")])
    if awg is None:
        raise RuntimeError(f"Missing compatible AWG input on {block}")
    bypass = bool(parameters["BYPASS"])
    rf = None if bypass else metadata.trace_back(block, "s1_axis", ["axis_signal_gen_v6"])
    if not bypass and rf is None:
        raise RuntimeError(f"Missing DDS input on {block}")
    if bypass and port != "s0_axis":
        raise RuntimeError(f"Generator connected to ignored bypass input on {block}")
    selected = awg if port == "s0_axis" else rf
    if selected[0] != fullpath:
        raise RuntimeError(f"Inconsistent output combiner input for {fullpath} on {block}/{port}")
    return dict(output_sum_version=version, output_sum_block=block,
                output_sum_role="awg" if port == "s0_axis" else "rf",
                output_sum_bypass=bypass, output_sum_awg=awg[0],
                output_sum_rf=None if rf is None else rf[0],
                output_sum_awg_delay_cycles=parameters.get("AWG_DELAY_CYCLES", 0),
                post_output_latency_cycles=parameters["PIPELINE_CYCLES"])


def apply_output_sum_config(cfg, route):
    """Apply role-specific latency once, retaining the uncombined configuration."""
    previous_role = cfg.get("output_sum_role")
    if "output_sum_native_latency_cycles" in cfg:
        native = cfg["output_sum_native_latency_cycles"]
    elif previous_role == "awg":
        # Also accepts a configuration created by the earlier v1-only driver.
        native = (int(cfg.get("output_latency_cycles", 0))
                  - int(cfg.get("post_output_latency_cycles", 0))
                  - int(cfg.get("output_sum_awg_delay_cycles", 0)))
    elif previous_role == "rf":
        native = None  # The v1-only driver added this field to ordinary RF.
    else:
        native = cfg.get("output_latency_cycles")
    if not route:
        if previous_role is not None:
            for key in list(cfg):
                if key.startswith("output_sum_") or key == "post_output_latency_cycles":
                    cfg.pop(key)
            if native is None:
                cfg.pop("output_latency_cycles", None)
            else:
                cfg["output_latency_cycles"] = native
        return
    version = route["output_sum_version"]
    delay = route.get("output_sum_awg_delay_cycles", 0)
    if (version not in (1, 2, 3, 7) or route["output_sum_role"] not in ("awg", "rf")
            or route["post_output_latency_cycles"] != 2
            or delay != {1: 0, 2: 13, 3: 6, 7: 2}.get(version)):
        raise RuntimeError(f"Unsupported output combiner latency profile: {route}")
    cfg.update(route)
    cfg["output_sum_awg_delay_cycles"] = delay
    cfg["output_sum_native_latency_cycles"] = native
    if route["output_sum_role"] == "awg":
        cfg["output_latency_cycles"] = int(native or 0) + delay + route["post_output_latency_cycles"]
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
            "The AWG/RF output uses a shared baseband DAC; Nyquist zone 1 "
            "and zero mixer frequency are required for both generators.")
