"""Generate bit-accurate directed vectors for the RTL testbench.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
TB_DIR = Path(__file__).resolve().parent
FIR_COEFF_FRAC = 17
SOS_COEFF_FRAC = 30
SIGNAL_FRAC = 16
STAGE_DECIMATIONS = [10, 2]
N_INPUTS = 2400


def load_coefficients() -> tuple[list[np.ndarray], np.ndarray]:
    fir_rows: dict[int, dict[int, int]] = {}
    notch_rows: dict[int, dict[int, int]] = {}
    with (ROOT / "coefficients.csv").open(newline="", encoding="ascii") as coeff_file:
        for row in csv.DictReader(coeff_file):
            stage = int(row["stage"])
            index = int(row["index"])
            value = int(row["value"])
            if row["filter"] == "fir":
                fir_rows.setdefault(stage, {})[index] = value
            elif row["filter"] == "notch":
                notch_rows.setdefault(stage, {})[index] = value

    fir = [
        np.asarray([values[index] for index in sorted(values)], dtype=object)
        for _, values in sorted(fir_rows.items())
    ]
    notch = np.asarray(
        [[values[index] for index in sorted(values)] for _, values in sorted(notch_rows.items())],
        dtype=object,
    )
    return fir, notch


def round_shift(value: int, shift: int) -> int:
    rounded = (abs(value) + (1 << (shift - 1))) >> shift
    return -rounded if value < 0 else rounded


def saturate(value: int, bits: int) -> int:
    return max(-(1 << (bits - 1)), min((1 << (bits - 1)) - 1, value))


class FirDecimModel:
    def __init__(self, coefficients: np.ndarray, decimation: int):
        self.coefficients = np.asarray(coefficients, dtype=object)
        self.decimation = decimation
        self.count = 0
        self.history = np.zeros((2, len(coefficients)), dtype=object)

    def process(self, i_value: int, q_value: int) -> tuple[int, int] | None:
        self.history[:, 1:] = self.history[:, :-1]
        self.history[0, 0] = int(i_value)
        self.history[1, 0] = int(q_value)

        if self.count != self.decimation - 1:
            self.count += 1
            return None

        self.count = 0
        output = []
        for channel in range(2):
            accumulator = sum(
                int(sample) * int(coefficient)
                for sample, coefficient in zip(self.history[channel], self.coefficients)
            )
            output.append(saturate(round_shift(accumulator, FIR_COEFF_FRAC), 16))
        return int(output[0]), int(output[1])


class SosModel:
    def __init__(self, coefficients: np.ndarray):
        self.coefficients = coefficients
        self.state = np.zeros((len(coefficients), 2, 4), dtype=object)

    def process(self, i_value: int, q_value: int) -> tuple[int, int]:
        values = [i_value << SIGNAL_FRAC, q_value << SIGNAL_FRAC]
        for section, coefficients in enumerate(self.coefficients):
            b0, b1, b2, a1, a2 = (int(value) for value in coefficients)
            for channel in range(2):
                x1, x2, y1, y2 = (int(value) for value in self.state[section, channel])
                x0 = int(values[channel])
                accumulator = b0*x0 + b1*x1 + b2*x2 - a1*y1 - a2*y2
                y0 = saturate(round_shift(accumulator, SOS_COEFF_FRAC), 32)
                self.state[section, channel] = [x0, x1, y0, y1]
                values[channel] = y0
        return tuple(saturate(round_shift(value, SIGNAL_FRAC), 16) for value in values)


def pack_iq(i_value: int, q_value: int) -> int:
    return ((q_value & 0xFFFF) << 16) | (i_value & 0xFFFF)


def main() -> None:
    fir_coefficients, notch_coefficients = load_coefficients()
    fir_stages = [
        FirDecimModel(coefficients, decimation)
        for coefficients, decimation in zip(fir_coefficients, STAGE_DECIMATIONS)
    ]
    notch = SosModel(notch_coefficients)
    rng = np.random.default_rng(0x5149434B)
    sample_index = np.arange(N_INPUTS, dtype=np.float64)

    i_values = (
        7000*np.sin(2*np.pi*1_000*sample_index/1_000_000)
        + 3000*np.sin(2*np.pi*60*sample_index/1_000_000)
        + rng.integers(-32, 33, N_INPUTS)
    )
    q_values = (
        -6000*np.cos(2*np.pi*700*sample_index/1_000_000)
        + 2500*np.sin(2*np.pi*120*sample_index/1_000_000)
        + rng.integers(-32, 33, N_INPUTS)
    )
    i_values = np.rint(i_values).astype(np.int64)
    q_values = np.rint(q_values).astype(np.int64)

    inputs: list[int] = []
    outputs: list[int] = []
    for i_value, q_value in zip(i_values, q_values):
        i_int = saturate(int(i_value), 16)
        q_int = saturate(int(q_value), 16)
        inputs.append(pack_iq(i_int, q_int))

        stage_value: tuple[int, int] | None = (i_int, q_int)
        for fir_stage in fir_stages:
            if stage_value is None:
                break
            stage_value = fir_stage.process(*stage_value)
        if stage_value is not None:
            notch_i, notch_q = notch.process(*stage_value)
            outputs.append(pack_iq(notch_i, notch_q))

    (TB_DIR / "input.hex").write_text("".join(f"{word:08x}\n" for word in inputs), encoding="ascii")
    (TB_DIR / "expected.hex").write_text("".join(f"{word:08x}\n" for word in outputs), encoding="ascii")
    (TB_DIR / "vector_counts.txt").write_text(f"inputs={len(inputs)}\noutputs={len(outputs)}\n", encoding="ascii")
    print(f"Generated {len(inputs)} input and {len(outputs)} expected output words.")


if __name__ == "__main__":
    main()
