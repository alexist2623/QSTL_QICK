# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""Fixed-point model and coefficient helpers for axis_fir_decim_300to1_v1."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.signal import firwin, freqz, lfilter


IP_ROOT = Path(__file__).resolve().parents[1]
COEFF_DIR = IP_ROOT / "coeffs"
VECTOR_DIR = IP_ROOT / "vectors"
REPORT_DIR = IP_ROOT / "reports"
SRC_DIR = IP_ROOT / "src"

COEF_WIDTH = 18
COEF_FRAC_BITS = COEF_WIDTH - 1
ACC_WIDTH = 48
OUT_WIDTH = 16

STAGE_SPECS = [
    {
        "name": "stage0",
        "fs_hz": 300e6,
        "decim": 10,
        "num_taps": 95,
        "cutoff_hz": 12e6,
        "kaiser_beta": 10.0,
    },
    {
        "name": "stage1",
        "fs_hz": 30e6,
        "decim": 10,
        "num_taps": 127,
        "cutoff_hz": 1.2e6,
        "kaiser_beta": 10.0,
    },
    {
        "name": "stage2",
        "fs_hz": 3e6,
        "decim": 3,
        "num_taps": 161,
        "cutoff_hz": 0.43e6,
        "kaiser_beta": 10.0,
    },
]


def ensure_dirs() -> None:
    for directory in [COEFF_DIR, VECTOR_DIR, REPORT_DIR, SRC_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def design_float_coefficients() -> list[np.ndarray]:
    coeffs = []
    for spec in STAGE_SPECS:
        coeffs.append(
            firwin(
                spec["num_taps"],
                spec["cutoff_hz"],
                fs=spec["fs_hz"],
                window=("kaiser", spec["kaiser_beta"]),
                scale=True,
            )
        )
    return coeffs


def quantize_coefficients(coeffs: np.ndarray, coef_width: int = COEF_WIDTH) -> np.ndarray:
    scale = 1 << (coef_width - 1)
    q_min = -(1 << (coef_width - 1))
    q_max = (1 << (coef_width - 1)) - 1
    q = np.rint(np.asarray(coeffs) * scale).astype(np.int64)
    return np.clip(q, q_min, q_max).astype(np.int64)


def load_quantized_coefficients() -> list[np.ndarray]:
    coeffs = []
    for spec in STAGE_SPECS:
        path = COEFF_DIR / f"{spec['name']}_coeffs.txt"
        coeffs.append(np.loadtxt(path, dtype=np.int64))
    return coeffs


def round_shift_signed(value: int, shift: int) -> int:
    """Round half away from zero, matching the RTL."""
    if shift <= 0:
        return int(value)
    offset = 1 << (shift - 1)
    if value >= 0:
        return int((value + offset) >> shift)
    return int(-(((-value) + offset) >> shift))


def saturate_signed(value: int, width: int = OUT_WIDTH) -> int:
    lo = -(1 << (width - 1))
    hi = (1 << (width - 1)) - 1
    return int(min(max(int(value), lo), hi))


def fir_decimate_fixed_lane(
    samples: np.ndarray,
    coeffs_q: np.ndarray,
    decim: int,
    coef_frac_bits: int = COEF_FRAC_BITS,
    out_width: int = OUT_WIDTH,
) -> np.ndarray:
    samples_i = np.asarray(samples, dtype=np.int64)
    coeffs_i = np.asarray(coeffs_q, dtype=np.int64)
    history = np.zeros(len(coeffs_i), dtype=np.int64)
    decim_count = 0
    output: list[int] = []

    for sample in samples_i:
        history[1:] = history[:-1]
        history[0] = int(sample)

        if decim_count == decim - 1:
            acc = int(np.dot(history, coeffs_i))
            rounded = round_shift_signed(acc, coef_frac_bits)
            output.append(saturate_signed(rounded, out_width))
            decim_count = 0
        else:
            decim_count += 1

    return np.asarray(output, dtype=np.int64)


def cascade_decim_300to1_fixed(lane0: np.ndarray, lane1: np.ndarray, coeffs_q: list[np.ndarray] | None = None) -> tuple[np.ndarray, np.ndarray]:
    if coeffs_q is None:
        coeffs_q = load_quantized_coefficients()
    y0 = np.asarray(lane0, dtype=np.int64)
    y1 = np.asarray(lane1, dtype=np.int64)
    for spec, coeff in zip(STAGE_SPECS, coeffs_q):
        y0 = fir_decimate_fixed_lane(y0, coeff, int(spec["decim"]))
        y1 = fir_decimate_fixed_lane(y1, coeff, int(spec["decim"]))
    return y0, y1


def cascade_decim_float(samples: np.ndarray, coeffs_f: list[np.ndarray] | None = None) -> np.ndarray:
    if coeffs_f is None:
        coeffs_f = design_float_coefficients()
    y = np.asarray(samples, dtype=np.float64)
    for spec, coeff in zip(STAGE_SPECS, coeffs_f):
        y = lfilter(coeff, [1.0], y)[int(spec["decim"]) - 1 :: int(spec["decim"])]
    return y


def pack_iq(lane0: np.ndarray, lane1: np.ndarray) -> np.ndarray:
    lane0_i = np.asarray(lane0, dtype=np.int64) & 0xFFFF
    lane1_i = np.asarray(lane1, dtype=np.int64) & 0xFFFF
    return ((lane1_i << 16) | lane0_i).astype(np.uint32)


def unpack_iq(words: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    words_u = np.asarray(words, dtype=np.uint32)
    lane0 = (words_u & 0xFFFF).astype(np.int32)
    lane1 = ((words_u >> 16) & 0xFFFF).astype(np.int32)
    lane0 = np.where(lane0 >= 0x8000, lane0 - 0x10000, lane0)
    lane1 = np.where(lane1 >= 0x8000, lane1 - 0x10000, lane1)
    return lane0.astype(np.int64), lane1.astype(np.int64)


def write_hex_words(path: Path, words: np.ndarray) -> None:
    with path.open("w", encoding="ascii") as f:
        for word in np.asarray(words, dtype=np.uint32):
            f.write(f"{int(word):08X}\n")


def read_hex_words(path: Path) -> np.ndarray:
    values = []
    with path.open("r", encoding="ascii") as f:
        for line in f:
            line = line.strip()
            if line:
                values.append(int(line, 16))
    return np.asarray(values, dtype=np.uint32)


def group_delay_input_samples() -> float:
    scale = 1
    total = 0.0
    for spec in STAGE_SPECS:
        total += scale * (int(spec["num_taps"]) - 1) / 2.0
        scale *= int(spec["decim"])
    return total


def export_filter_config(coeffs_f: list[np.ndarray], coeffs_q: list[np.ndarray]) -> dict:
    config = {
        "fs_input_hz": 300e6,
        "fs_output_hz": 1e6,
        "total_decimation": 300,
        "coef_width": COEF_WIDTH,
        "coef_frac_bits": COEF_FRAC_BITS,
        "acc_width": ACC_WIDTH,
        "out_width": OUT_WIDTH,
        "rounding": "round half away from zero before coefficient-scale right shift",
        "saturation": "signed 16-bit saturation",
        "group_delay_input_samples": group_delay_input_samples(),
        "stages": [],
    }
    for spec, coeff_f, coeff_q in zip(STAGE_SPECS, coeffs_f, coeffs_q):
        config["stages"].append(
            {
                **spec,
                "coefficient_file": f"{spec['name']}_coeffs.txt",
                "coefficient_sum_float": float(np.sum(coeff_f)),
                "coefficient_sum_quantized": int(np.sum(coeff_q)),
                "coefficient_scale": 1 << COEF_FRAC_BITS,
                "max_quantization_error": float(np.max(np.abs(coeff_f - coeff_q / float(1 << COEF_FRAC_BITS)))),
            }
        )
    with (COEFF_DIR / "filter_config.json").open("w", encoding="ascii") as f:
        json.dump(config, f, indent=2)
    return config


def frequency_response_metrics(coeffs_f: list[np.ndarray]) -> dict:
    points_hz = [0.5e6, 0.75e6, 1e6, 2e6, 5e6, 10e6, 30e6, 80e6, 120e6]
    metrics: dict[str, float | dict[str, float]] = {}

    # End-to-end tone response captures the multirate alias behavior directly.
    fs = 300e6
    n = 300_000
    t = np.arange(n) / fs

    def tone_amp_db(freq_hz: float) -> float:
        x = np.sin(2 * np.pi * freq_hz * t)
        y = cascade_decim_float(x, coeffs_f)
        y = y[len(y) // 2 :]
        amp = np.sqrt(2.0) * np.sqrt(np.mean(y * y))
        return float(20 * np.log10(amp + 1e-18))

    response_points = [0.1e6, 0.2e6, 0.3e6, 0.4e6] + points_hz
    metrics["tone_response_db"] = {f"{p:g}": tone_amp_db(p) for p in response_points}
    pb = [metrics["tone_response_db"][f"{p:g}"] for p in [0.0 + 0.1e6, 0.2e6, 0.3e6, 0.4e6]]
    metrics["passband_ripple_db"] = float(max(pb) - min(pb))
    metrics["gain_100khz_db"] = float(metrics["tone_response_db"][f"{0.1e6:g}"])
    metrics["gain_400khz_db"] = float(metrics["tone_response_db"][f"{0.4e6:g}"])

    metrics["per_stage_response_db"] = {}
    for spec, coeff in zip(STAGE_SPECS, coeffs_f):
        w, h = freqz(coeff, worN=65536, fs=spec["fs_hz"])
        stage_metrics = {}
        for freq_hz in [0.1e6, 0.4e6, 0.5e6, 1e6, 2e6, 5e6, 10e6, min(15e6, spec["fs_hz"] / 2 - 1)]:
            idx = int(np.argmin(np.abs(w - freq_hz)))
            stage_metrics[f"{freq_hz:g}"] = float(20 * np.log10(abs(h[idx]) + 1e-18))
        metrics["per_stage_response_db"][spec["name"]] = stage_metrics

    return metrics


def write_sv_coeff_package(coeffs_q: list[np.ndarray]) -> None:
    def sv_signed_literal(value: int) -> str:
        value = int(value)
        if value < 0:
            return f"-{COEF_WIDTH}'sd{abs(value)}"
        return f"{COEF_WIDTH}'sd{value}"

    lines: list[str] = []
    lines.append("// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod")
    lines.append("// Generated by scripts/design_fir_decim_300to1.py. Do not edit coefficient values by hand.")
    lines.append("`timescale 1ns/1ps")
    lines.append("package fir_decim_300to1_coeffs_pkg;")
    lines.append(f"    localparam int COEF_WIDTH = {COEF_WIDTH};")
    lines.append(f"    localparam int COEF_FRAC_BITS = {COEF_FRAC_BITS};")
    for idx, (spec, coeff) in enumerate(zip(STAGE_SPECS, coeffs_q)):
        lines.append(f"    localparam int STAGE{idx}_DECIM = {int(spec['decim'])};")
        lines.append(f"    localparam int STAGE{idx}_TAPS = {len(coeff)};")
    lines.append("")
    lines.append("    function automatic logic signed [COEF_WIDTH-1:0] fir_coeff(input int stage, input int idx);")
    lines.append("        fir_coeff = '0;")
    lines.append("        case (stage)")
    for stage_idx, coeff in enumerate(coeffs_q):
        lines.append(f"            {stage_idx}: begin")
        lines.append("                case (idx)")
        for tap_idx, value in enumerate(coeff):
            lines.append(f"                    {tap_idx}: fir_coeff = {sv_signed_literal(int(value))};")
        lines.append("                    default: fir_coeff = '0;")
        lines.append("                endcase")
        lines.append("            end")
    lines.append("            default: fir_coeff = '0;")
    lines.append("        endcase")
    lines.append("    endfunction")
    lines.append("endpackage")
    lines.append("")
    (SRC_DIR / "fir_decim_300to1_coeffs_pkg.sv").write_text("\n".join(lines), encoding="ascii")
