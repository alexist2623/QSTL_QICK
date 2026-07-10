# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""Generate deterministic Verilog test vectors for axis_fir_decim_300to1_v1."""

from __future__ import annotations

import json

import numpy as np

from fir_decim_300to1_model import (
    COEF_FRAC_BITS,
    OUT_WIDTH,
    STAGE_SPECS,
    VECTOR_DIR,
    cascade_decim_300to1_fixed,
    load_quantized_coefficients,
    pack_iq,
    round_shift_signed,
    saturate_signed,
    write_hex_words,
)


FS_IN = 300e6


def make_tone(freq_hz: float, n: int, amp0: float, amp1: float, phase1: float = 0.35) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(n) / FS_IN
    lane0 = np.rint(amp0 * np.sin(2 * np.pi * freq_hz * t)).astype(np.int64)
    lane1 = np.rint(amp1 * np.cos(2 * np.pi * freq_hz * t + phase1)).astype(np.int64)
    return lane0, lane1


def write_case(name: str, lane0: np.ndarray, lane1: np.ndarray, coeffs_q: list[np.ndarray], valid_gap: str = "none") -> dict:
    lane0 = np.clip(np.asarray(lane0, dtype=np.int64), -32768, 32767)
    lane1 = np.clip(np.asarray(lane1, dtype=np.int64), -32768, 32767)
    out0, out1 = cascade_decim_300to1_fixed(lane0, lane1, coeffs_q)
    input_words = pack_iq(lane0, lane1)
    expected_words = pack_iq(out0, out1)
    input_path = VECTOR_DIR / f"{name}_input.txt"
    expected_path = VECTOR_DIR / f"{name}_expected.txt"
    write_hex_words(input_path, input_words)
    write_hex_words(expected_path, expected_words)
    return {
        "name": name,
        "input_file": input_path.name,
        "expected_file": expected_path.name,
        "input_samples": int(len(input_words)),
        "expected_samples": int(len(expected_words)),
        "valid_gap": valid_gap,
    }


class StatefulFirStage:
    def __init__(self, coeffs: np.ndarray, decim: int):
        self.coeffs = np.asarray(coeffs, dtype=np.int64)
        self.decim = int(decim)
        self.history = np.zeros(len(self.coeffs), dtype=np.int64)
        self.decim_count = 0

    def reset_phase_only(self) -> None:
        self.decim_count = 0

    def push(self, sample: int) -> int | None:
        self.history[1:] = self.history[:-1]
        self.history[0] = int(sample)

        if self.decim_count == self.decim - 1:
            acc = int(np.dot(self.history, self.coeffs))
            rounded = round_shift_signed(acc, COEF_FRAC_BITS)
            self.decim_count = 0
            return saturate_signed(rounded, OUT_WIDTH)

        self.decim_count += 1
        return None


def cascade_phase_reset_expected(pre: np.ndarray, post: np.ndarray, coeffs_q: list[np.ndarray]) -> np.ndarray:
    stages0 = [StatefulFirStage(coeff, spec["decim"]) for coeff, spec in zip(coeffs_q, STAGE_SPECS)]
    stages1 = [StatefulFirStage(coeff, spec["decim"]) for coeff, spec in zip(coeffs_q, STAGE_SPECS)]
    outputs: list[tuple[int, int]] = []

    def feed_pair(sample0: int, sample1: int, collect: bool) -> None:
        vals0: list[int | None] = [int(sample0)]
        vals1: list[int | None] = [int(sample1)]
        for stage_idx in range(len(STAGE_SPECS)):
            in0 = vals0[-1]
            in1 = vals1[-1]
            if in0 is None or in1 is None:
                vals0.append(None)
                vals1.append(None)
                continue
            vals0.append(stages0[stage_idx].push(in0))
            vals1.append(stages1[stage_idx].push(in1))
        if collect and vals0[-1] is not None and vals1[-1] is not None:
            outputs.append((int(vals0[-1]), int(vals1[-1])))

    for sample0, sample1 in pre:
        feed_pair(int(sample0), int(sample1), collect=False)

    for stage in [*stages0, *stages1]:
        stage.reset_phase_only()

    for sample0, sample1 in post:
        feed_pair(int(sample0), int(sample1), collect=True)

    if not outputs:
        return np.zeros(0, dtype=np.uint32)
    out0 = np.asarray([item[0] for item in outputs], dtype=np.int64)
    out1 = np.asarray([item[1] for item in outputs], dtype=np.int64)
    return pack_iq(out0, out1)


def write_trigger_align_case(coeffs_q: list[np.ndarray]) -> dict:
    pre0, pre1 = make_tone(2.3e6, 4_800, 15000, 11000, phase1=1.1)
    post0, post1 = make_tone(100e3, 60_000, 12000, 9000)
    pre = np.column_stack((pre0, pre1))
    post = np.column_stack((post0, post1))

    expected_words = cascade_phase_reset_expected(pre, post, coeffs_q)
    pre_words = pack_iq(pre0, pre1)
    post_words = pack_iq(post0, post1)

    pre_path = VECTOR_DIR / "trigger_align_pre_input.txt"
    post_path = VECTOR_DIR / "trigger_align_post_input.txt"
    expected_path = VECTOR_DIR / "trigger_align_expected.txt"
    write_hex_words(pre_path, pre_words)
    write_hex_words(post_path, post_words)
    write_hex_words(expected_path, expected_words)
    return {
        "name": "trigger_align",
        "pre_input_file": pre_path.name,
        "input_file": post_path.name,
        "expected_file": expected_path.name,
        "pre_input_samples": int(len(pre_words)),
        "input_samples": int(len(post_words)),
        "expected_samples": int(len(expected_words)),
        "description": "pre-trigger data fills FIR history; trigger resets only decimation phase before post input",
    }


def main() -> None:
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    coeffs_q = load_quantized_coefficients()
    cases = []

    n_impulse = 12_000
    impulse0 = np.zeros(n_impulse, dtype=np.int64)
    impulse1 = np.zeros(n_impulse, dtype=np.int64)
    impulse0[0] = 16000
    impulse1[0] = -12000
    cases.append(write_case("impulse", impulse0, impulse1, coeffs_q))

    tone0, tone1 = make_tone(100e3, 60_000, 12000, 9000)
    cases.append(write_case("tone", tone0, tone1, coeffs_q))

    rng = np.random.default_rng(20260708)
    n_noisy = 60_000
    t = np.arange(n_noisy) / FS_IN
    desired0 = 9000 * np.sin(2 * np.pi * 100e3 * t)
    desired1 = 7000 * np.cos(2 * np.pi * 100e3 * t + 0.4)
    noisy0 = desired0 + 4500 * np.sin(2 * np.pi * 2e6 * t + 0.2) + 3000 * np.sin(2 * np.pi * 80e6 * t)
    noisy1 = desired1 + 3800 * np.sin(2 * np.pi * 5e6 * t + 1.1) + 2600 * np.sin(2 * np.pi * 120e6 * t)
    noisy0 += rng.normal(0, 1000, n_noisy)
    noisy1 += rng.normal(0, 1000, n_noisy)
    cases.append(write_case("noisy", np.rint(noisy0), np.rint(noisy1), coeffs_q))

    gap0, gap1 = make_tone(400e3, 18_000, 10000, 8000)
    cases.append(write_case("valid_gap", gap0, gap1, coeffs_q, valid_gap="drive valid low every 7th and 19th cycle without consuming input"))

    reset0, reset1 = make_tone(100e3, 18_000, 9000, 6000)
    cases.append(write_case("reset_after", reset0, reset1, coeffs_q))
    cases.append(write_trigger_align_case(coeffs_q))

    manifest = {
        "description": "Deterministic vectors for axis_fir_decim_300to1_v1. Expected files are packed 32-bit lane1:lane0 words.",
        "total_decimation": 300,
        "cases": cases,
    }
    with (VECTOR_DIR / "vector_manifest.json").open("w", encoding="ascii") as f:
        json.dump(manifest, f, indent=2)

    print("Wrote Verilog vectors.")


if __name__ == "__main__":
    main()
