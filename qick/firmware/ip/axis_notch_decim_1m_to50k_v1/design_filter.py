"""Design and emit the fixed-point FIR and notch coefficients used by the RTL.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy import signal


IP_ROOT = Path(__file__).resolve().parent
SRC_DIR = IP_ROOT / "src"

INPUT_FS_HZ = 1_000_000.0
INTERMEDIATE_FS_HZ = 100_000.0
OUTPUT_FS_HZ = 50_000.0
TOTAL_DECIMATION = 20

# This follows axis_fir_decim_300to1_v1: Kaiser-window linear-phase FIRs,
# signed Q1.17 coefficients, 48-bit accumulators, and a multistage cascade.
FIR_KAISER_BETA = 10.0
FIR_PASSBAND_HZ = 20_000.0
FIR_STOPBAND_HZ = 25_000.0
FIR_MAX_RIPPLE_DB = 0.1
FIR_MIN_STOP_DB = 80.0
FIR_COEFF_WIDTH = 18
FIR_COEFF_FRAC_BITS = FIR_COEFF_WIDTH - 1
FIR_COEFF_SCALE = 1 << FIR_COEFF_FRAC_BITS
FIR_ACC_WIDTH = 48

FIR_STAGE_REQUIREMENTS = [
    {
        "name": "stage0",
        "fs_hz": INPUT_FS_HZ,
        "decim": 10,
        "passband_hz": FIR_PASSBAND_HZ,
        # After /10, 75 kHz is the first edge that can alias into the final
        # 0-25 kHz output band without being removed by stage 1.
        "stopband_hz": 75_000.0,
        "cutoff_hz": 47_500.0,
    },
    {
        "name": "stage1",
        "fs_hz": INTERMEDIATE_FS_HZ,
        "decim": 2,
        "passband_hz": FIR_PASSBAND_HZ,
        "stopband_hz": FIR_STOPBAND_HZ,
        "cutoff_hz": 22_500.0,
    },
]

MAINS_HZ = 60.0
HARMONICS = 20
NOTCH_BANDWIDTH_HZ = 2.0
NOTCH_REPEATS = 2
SOS_COEFF_WIDTH = 32
SOS_COEFF_FRAC_BITS = 30
SOS_COEFF_SCALE = 1 << SOS_COEFF_FRAC_BITS
SOS_ENGINE_CYCLES_PER_SECTION = 11
FIR_PIPELINE_CYCLES_PER_STAGE = 9
FABRIC_CLOCK_HZ = 300_000_000.0
UPSTREAM_FIR_GROUP_DELAY_INPUT_SAMPLES = 8677.0
UPSTREAM_FIR_INPUT_FS_HZ = 300_000_000.0


def quantize_fir(coefficients: np.ndarray) -> np.ndarray:
    """Quantize FIR coefficients exactly as axis_fir_decim_300to1_v1 does."""
    q_min = -(1 << (FIR_COEFF_WIDTH - 1))
    q_max = (1 << (FIR_COEFF_WIDTH - 1)) - 1
    quantized = np.rint(np.asarray(coefficients) * FIR_COEFF_SCALE).astype(np.int64)
    return np.clip(quantized, q_min, q_max)


def fir_stage_metrics(coefficients_q: np.ndarray, requirement: dict) -> dict:
    coefficients = np.asarray(coefficients_q, dtype=np.float64) / FIR_COEFF_SCALE
    fs_hz = float(requirement["fs_hz"])
    frequencies = np.linspace(0.0, fs_hz / 2.0, 400_001)
    _, response = signal.freqz(coefficients, worN=frequencies, fs=fs_hz)
    response_db = 20.0 * np.log10(np.maximum(np.abs(response), 1e-300))
    passband = response_db[frequencies <= float(requirement["passband_hz"])]
    stopband = response_db[frequencies >= float(requirement["stopband_hz"])]
    return {
        "passband_ripple_db": float(np.ptp(passband)),
        "passband_min_db": float(np.min(passband)),
        "stopband_max_db": float(np.max(stopband)),
        "dc_gain_db": float(20.0 * np.log10(abs(np.sum(coefficients)))),
    }


def design_fir_stages() -> tuple[list[np.ndarray], list[np.ndarray], list[dict]]:
    """Find the smallest odd tap count passing the quantized-stage limits."""
    float_coefficients: list[np.ndarray] = []
    quantized_coefficients: list[np.ndarray] = []
    metrics: list[dict] = []

    for requirement in FIR_STAGE_REQUIREMENTS:
        selected = None
        for num_taps in range(31, 258, 2):
            coefficients = signal.firwin(
                num_taps,
                float(requirement["cutoff_hz"]),
                fs=float(requirement["fs_hz"]),
                window=("kaiser", FIR_KAISER_BETA),
                scale=True,
            )
            coefficients_q = quantize_fir(coefficients)
            stage_metrics = fir_stage_metrics(coefficients_q, requirement)
            if (
                stage_metrics["passband_ripple_db"] <= FIR_MAX_RIPPLE_DB
                and stage_metrics["stopband_max_db"] <= -FIR_MIN_STOP_DB
            ):
                selected = (coefficients, coefficients_q, stage_metrics)
                break
        if selected is None:
            raise RuntimeError(f"no FIR tap count passed for {requirement['name']}")
        float_coefficients.append(selected[0])
        quantized_coefficients.append(selected[1])
        metrics.append(selected[2])

    return float_coefficients, quantized_coefficients, metrics


def design_notches() -> np.ndarray:
    notch_rows = []
    for harmonic in range(1, HARMONICS + 1):
        frequency = MAINS_HZ * harmonic
        quality = frequency / NOTCH_BANDWIDTH_HZ
        b, a = signal.iirnotch(frequency, quality, fs=OUTPUT_FS_HZ)
        row = np.concatenate((b, a))
        notch_rows.extend([row.copy() for _ in range(NOTCH_REPEATS)])
    return np.asarray(notch_rows, dtype=np.float64)


def quantize_sos(sos: np.ndarray) -> np.ndarray:
    quantized = np.rint(sos * SOS_COEFF_SCALE).astype(np.int64)
    quantized[:, 3] = SOS_COEFF_SCALE
    if np.any(quantized > np.iinfo(np.int32).max) or np.any(quantized < np.iinfo(np.int32).min):
        raise ValueError("a Q2.30 coefficient does not fit in signed 32 bits")
    return quantized


def response_db(sos: np.ndarray, frequencies: np.ndarray, fs: float) -> np.ndarray:
    _, response = signal.sosfreqz(sos, worN=frequencies, fs=fs)
    return 20.0 * np.log10(np.maximum(np.abs(response), 1e-300))


def group_delay_seconds(sos: np.ndarray, frequency: float, fs: float) -> float:
    delta = 0.001
    frequencies = np.asarray([max(0.0, frequency - delta), frequency + delta])
    _, response = signal.sosfreqz(sos, worN=frequencies, fs=fs)
    phase_delta = np.angle(response[1] / response[0])
    return float(-phase_delta / (2.0 * np.pi * (frequencies[1] - frequencies[0])))


def alias_frequency(frequencies: np.ndarray, sample_rate: float) -> np.ndarray:
    return np.abs((frequencies + sample_rate / 2.0) % sample_rate - sample_rate / 2.0)


def evaluate_fir_cascade(coefficients_q: list[np.ndarray]) -> dict:
    input_frequencies = np.linspace(0.0, INPUT_FS_HZ / 2.0, 1_000_001)
    stage0 = np.asarray(coefficients_q[0], dtype=np.float64) / FIR_COEFF_SCALE
    stage1 = np.asarray(coefficients_q[1], dtype=np.float64) / FIR_COEFF_SCALE

    grid0, response0 = signal.freqz(stage0, worN=1_048_576, fs=INPUT_FS_HZ)
    grid1, response1 = signal.freqz(stage1, worN=1_048_576, fs=INTERMEDIATE_FS_HZ)
    magnitude0 = np.interp(input_frequencies, grid0, np.abs(response0))
    stage1_frequencies = alias_frequency(input_frequencies, INTERMEDIATE_FS_HZ)
    magnitude1 = np.interp(stage1_frequencies, grid1, np.abs(response1))
    cascade_db = 20.0 * np.log10(np.maximum(magnitude0 * magnitude1, 1e-300))

    passband = cascade_db[input_frequencies <= FIR_PASSBAND_HZ]
    stopband_mask = input_frequencies >= FIR_STOPBAND_HZ
    stopband = cascade_db[stopband_mask]
    stopband_frequencies = input_frequencies[stopband_mask]
    stopband_index = int(np.argmax(stopband))
    return {
        "passband_ripple_db": float(np.ptp(passband)),
        "passband_min_db": float(np.min(passband)),
        "stopband_max_db": float(stopband[stopband_index]),
        "stopband_worst_frequency_hz": float(stopband_frequencies[stopband_index]),
        "dc_gain_db": float(cascade_db[0]),
    }


def sv_signed_literal(width: int, value: int) -> str:
    return f"-{width}'sd{abs(int(value))}" if value < 0 else f"{width}'sd{int(value)}"


def fir_coefficient_function(values: list[np.ndarray]) -> list[str]:
    lines = [
        "    function automatic logic signed [FIR_COEFF_WIDTH-1:0] fir_coeff(input int stage, input int index);",
        "        fir_coeff = '0;",
        "        case (stage)",
    ]
    for stage, coefficients in enumerate(values):
        lines.extend([f"            {stage}: begin", "                case (index)"])
        for index, value in enumerate(coefficients):
            lines.append(f"                    {index}: fir_coeff = {sv_signed_literal(FIR_COEFF_WIDTH, int(value))};")
        lines.extend(["                    default: ;", "                endcase", "            end"])
    lines.extend(["            default: ;", "        endcase", "    endfunction", ""])
    return lines


def sos_coefficient_function(values: np.ndarray) -> list[str]:
    lines = [
        "    function automatic logic signed [SOS_COEFF_WIDTH-1:0] notch_coeff(input int section, input int coefficient);",
        "        notch_coeff = '0;",
        "        case (section)",
    ]
    for section, row in enumerate(values):
        selected = [row[0], row[1], row[2], row[4], row[5]]
        lines.extend([f"            {section}: begin", "                case (coefficient)"])
        for index, value in enumerate(selected):
            lines.append(f"                    {index}: notch_coeff = {sv_signed_literal(SOS_COEFF_WIDTH, int(value))};")
        lines.extend(["                    default: ;", "                endcase", "            end"])
    lines.extend(["            default: ;", "        endcase", "    endfunction", ""])
    return lines


def write_sv_package(fir_q: list[np.ndarray], notch_q: np.ndarray, default_delay: int) -> None:
    lines = [
        "// Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod",
        "// Generated by design_filter.py. Do not edit coefficient values by hand.",
        "`timescale 1ns/1ps",
        "package notch_decim_1m_to50k_coeffs_pkg;",
        f"    localparam int FIR_COEFF_WIDTH = {FIR_COEFF_WIDTH};",
        f"    localparam int FIR_COEFF_FRAC_BITS = {FIR_COEFF_FRAC_BITS};",
        f"    localparam int FIR_ACC_WIDTH = {FIR_ACC_WIDTH};",
        f"    localparam int STAGE0_DECIM = {FIR_STAGE_REQUIREMENTS[0]['decim']};",
        f"    localparam int STAGE0_TAPS = {len(fir_q[0])};",
        f"    localparam int STAGE1_DECIM = {FIR_STAGE_REQUIREMENTS[1]['decim']};",
        f"    localparam int STAGE1_TAPS = {len(fir_q[1])};",
        f"    localparam int SOS_COEFF_WIDTH = {SOS_COEFF_WIDTH};",
        f"    localparam int SOS_COEFF_FRAC_BITS = {SOS_COEFF_FRAC_BITS};",
        f"    localparam int INPUT_SAMPLE_RATE_HZ = {int(INPUT_FS_HZ)};",
        f"    localparam int OUTPUT_SAMPLE_RATE_HZ = {int(OUTPUT_FS_HZ)};",
        f"    localparam int DECIMATION = {TOTAL_DECIMATION};",
        f"    localparam int NOTCH_SECTIONS = {len(notch_q)};",
        f"    localparam int NOTCH_HARMONICS = {HARMONICS};",
        f"    localparam int NOTCH_REPEATS = {NOTCH_REPEATS};",
        f"    localparam int DEFAULT_TRIGGER_DELAY_SAMPLES = {default_delay};",
        "",
    ]
    lines.extend(fir_coefficient_function(fir_q))
    lines.extend(sos_coefficient_function(notch_q))
    lines.append("endpackage")
    (SRC_DIR / "notch_decim_1m_to50k_coeffs_pkg.sv").write_text("\n".join(lines) + "\n", encoding="ascii")


def write_coefficient_csv(fir_q: list[np.ndarray], notch_q: np.ndarray) -> None:
    with (IP_ROOT / "coefficients.csv").open("w", newline="", encoding="ascii") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["filter", "stage", "index", "value", "fractional_bits"])
        for stage, coefficients in enumerate(fir_q):
            for index, value in enumerate(coefficients):
                writer.writerow(["fir", stage, index, int(value), FIR_COEFF_FRAC_BITS])
        for section, row in enumerate(notch_q):
            for index, value in enumerate([row[0], row[1], row[2], row[4], row[5]]):
                writer.writerow(["notch", section, index, int(value), SOS_COEFF_FRAC_BITS])


def validate_and_write_metadata(
    fir_q: list[np.ndarray],
    stage_metrics: list[dict],
    notch: np.ndarray,
) -> int:
    notch_q = quantize_sos(notch)
    notch_float_q = notch_q.astype(np.float64) / SOS_COEFF_SCALE
    notch_poles = np.concatenate([np.roots(row[3:]) for row in notch_float_q])
    if max(np.abs(notch_poles)) >= 1.0:
        raise RuntimeError("quantized notch filter is unstable")

    notch_frequencies = MAINS_HZ * np.arange(1, HARMONICS + 1)
    notch_depths = response_db(notch_float_q, notch_frequencies, OUTPUT_FS_HZ)
    if np.max(notch_depths) > -100.0:
        raise RuntimeError(f"quantized notch depth is too shallow: {np.max(notch_depths):.2f} dB")

    cascade_metrics = evaluate_fir_cascade(fir_q)
    if cascade_metrics["passband_ripple_db"] > FIR_MAX_RIPPLE_DB:
        raise RuntimeError(f"FIR passband ripple is too high: {cascade_metrics['passband_ripple_db']:.3f} dB")
    if cascade_metrics["stopband_max_db"] > -FIR_MIN_STOP_DB:
        raise RuntimeError(f"FIR stopband is too shallow: {cascade_metrics['stopband_max_db']:.2f} dB")

    fir_group_delay_input_samples = sum(
        np.prod([int(previous["decim"]) for previous in FIR_STAGE_REQUIREMENTS[:index]], dtype=np.int64)
        * (len(coefficients) - 1) / 2.0
        for index, coefficients in enumerate(fir_q)
    )
    fir_group_delay_seconds = float(fir_group_delay_input_samples / INPUT_FS_HZ)
    notch_group_delay_seconds = group_delay_seconds(notch_float_q, 1.0, OUTPUT_FS_HZ)
    implementation_pipeline_seconds = (
        FIR_PIPELINE_CYCLES_PER_STAGE * len(fir_q)
        + SOS_ENGINE_CYCLES_PER_SECTION * len(notch_q)
    ) / FABRIC_CLOCK_HZ
    post_filter_delay_seconds = (
        fir_group_delay_seconds + notch_group_delay_seconds + implementation_pipeline_seconds
    )
    upstream_fir_delay_seconds = (
        UPSTREAM_FIR_GROUP_DELAY_INPUT_SAMPLES / UPSTREAM_FIR_INPUT_FS_HZ
    )
    full_path_delay_seconds = upstream_fir_delay_seconds + post_filter_delay_seconds
    output_sample_period_seconds = 1.0 / OUTPUT_FS_HZ
    default_delay = int(math.ceil(full_path_delay_seconds / output_sample_period_seconds))

    metadata = {
        "input_sample_rate_hz": INPUT_FS_HZ,
        "intermediate_sample_rate_hz": INTERMEDIATE_FS_HZ,
        "output_sample_rate_hz": OUTPUT_FS_HZ,
        "decimation": TOTAL_DECIMATION,
        "anti_alias_fir": {
            "method": "multistage linear-phase FIR using scipy.signal.firwin with a Kaiser window",
            "kaiser_beta": FIR_KAISER_BETA,
            "coefficient_format": "signed Q1.17",
            "accumulator_width_bits": FIR_ACC_WIDTH,
            "passband_hz": FIR_PASSBAND_HZ,
            "stopband_hz": FIR_STOPBAND_HZ,
            "maximum_passband_ripple_db": FIR_MAX_RIPPLE_DB,
            "minimum_stopband_attenuation_db": FIR_MIN_STOP_DB,
            "stages": [
                {
                    **requirement,
                    "num_taps": len(coefficients),
                    "order": len(coefficients) - 1,
                    **metrics,
                }
                for requirement, coefficients, metrics in zip(
                    FIR_STAGE_REQUIREMENTS, fir_q, stage_metrics
                )
            ],
            "cascade_metrics": cascade_metrics,
            "parallel_multipliers_for_iq": int(2 * sum(len(coefficients) for coefficients in fir_q)),
            "group_delay_input_samples": float(fir_group_delay_input_samples),
            "group_delay_microseconds": fir_group_delay_seconds * 1e6,
        },
        "notch": {
            "mains_frequency_hz": MAINS_HZ,
            "harmonics": HARMONICS,
            "bandwidth_hz_per_biquad": NOTCH_BANDWIDTH_HZ,
            "cascade_repeats": NOTCH_REPEATS,
            "sections": len(notch_q),
            "coefficient_format": "Q2.30",
            "signal_format": "Q16.16",
            "max_pole_radius": float(max(np.abs(notch_poles))),
            "quantized_center_attenuation_db": notch_depths.tolist(),
        },
        "trigger_delay": {
            "post_filter_nominal_dc_seconds": post_filter_delay_seconds,
            "post_filter_nominal_dc_microseconds": post_filter_delay_seconds * 1e6,
            "upstream_fir_group_delay_seconds": upstream_fir_delay_seconds,
            "upstream_fir_group_delay_microseconds": upstream_fir_delay_seconds * 1e6,
            "full_path_nominal_dc_seconds": full_path_delay_seconds,
            "full_path_nominal_dc_microseconds": full_path_delay_seconds * 1e6,
            "default_output_samples": default_delay,
            "output_sample_period_microseconds": output_sample_period_seconds * 1e6,
            "note": "The FIR delay is exact; notch IIR group delay is frequency-dependent. Tune the DDR delay register for the measured signal band when needed.",
        },
    }
    (IP_ROOT / "filter_design.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="ascii")
    write_coefficient_csv(fir_q, notch_q)
    write_sv_package(fir_q, notch_q, default_delay)
    return default_delay


def main() -> None:
    _, fir_q, stage_metrics = design_fir_stages()
    notch = design_notches()
    default_delay = validate_and_write_metadata(fir_q, stage_metrics, notch)
    print(
        "Generated FIR stages with "
        f"{len(fir_q[0])} and {len(fir_q[1])} taps, "
        f"{len(notch)} notch SOS sections, and default DDR delay {default_delay}."
    )


if __name__ == "__main__":
    main()
