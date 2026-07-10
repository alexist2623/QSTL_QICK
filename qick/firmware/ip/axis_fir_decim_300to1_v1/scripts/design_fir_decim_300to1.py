# Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""Design and export coefficients for axis_fir_decim_300to1_v1."""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import freqz

from fir_decim_300to1_model import (
    COEFF_DIR,
    REPORT_DIR,
    STAGE_SPECS,
    design_float_coefficients,
    ensure_dirs,
    export_filter_config,
    frequency_response_metrics,
    quantize_coefficients,
    write_sv_coeff_package,
)


def main() -> None:
    ensure_dirs()
    coeffs_f = design_float_coefficients()
    coeffs_q = [quantize_coefficients(c) for c in coeffs_f]

    for spec, coeff in zip(STAGE_SPECS, coeffs_q):
        np.savetxt(COEFF_DIR / f"{spec['name']}_coeffs.txt", coeff, fmt="%d")

    config = export_filter_config(coeffs_f, coeffs_q)
    write_sv_coeff_package(coeffs_q)

    metrics = frequency_response_metrics(coeffs_f)
    with (REPORT_DIR / "frequency_response_metrics.json").open("w", encoding="ascii") as f:
        json.dump(metrics, f, indent=2)

    fig, axes = plt.subplots(len(STAGE_SPECS) + 1, 1, figsize=(10, 10), constrained_layout=True)
    for ax, spec, coeff in zip(axes[:-1], STAGE_SPECS, coeffs_f):
        w, h = freqz(coeff, worN=65536, fs=spec["fs_hz"])
        ax.plot(w / 1e6, 20 * np.log10(np.maximum(np.abs(h), 1e-14)))
        ax.set_title(f"{spec['name']} FIR, decim={spec['decim']}, taps={spec['num_taps']}")
        ax.set_xlabel("frequency (MHz)")
        ax.set_ylabel("magnitude (dB)")
        ax.grid(True)
        ax.set_ylim(-140, 5)

    tone_response = metrics["tone_response_db"]
    freqs = np.array([float(k) for k in tone_response.keys()])
    gains = np.array([float(v) for v in tone_response.values()])
    order = np.argsort(freqs)
    axes[-1].semilogx(freqs[order] / 1e6, gains[order], marker="o")
    axes[-1].set_title("End-to-end multirate tone response")
    axes[-1].set_xlabel("input tone frequency (MHz)")
    axes[-1].set_ylabel("output amplitude (dBFS relative)")
    axes[-1].grid(True, which="both")
    axes[-1].set_ylim(-140, 5)
    fig.savefig(REPORT_DIR / "python_frequency_response.png", dpi=160)
    plt.close(fig)

    with (REPORT_DIR / "coefficient_design_summary.txt").open("w", encoding="ascii") as f:
        f.write("axis_fir_decim_300to1_v1 coefficient design\n")
        f.write("================================================\n\n")
        f.write(json.dumps(config, indent=2))
        f.write("\n\nMetrics\n-------\n")
        f.write(json.dumps(metrics, indent=2))
        f.write("\n")

    print("Wrote FIR coefficients, config, SV package, and frequency-response reports.")


if __name__ == "__main__":
    main()
