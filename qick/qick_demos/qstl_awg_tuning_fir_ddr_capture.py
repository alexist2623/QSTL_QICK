"""HWH-aware qstl FIR-DDR capture example.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod

This script supports both qstl FIR DDR data paths.  The loaded HWH selects one
of the following profiles automatically:

    1 MSPS:
        readout -> axis_fir_decim_300to1_v1 -> axis_buffer_ddr_sample_v1

    50 kSPS:
        readout -> axis_fir_decim_300to1_v1
                -> axis_notch_decim_1m_to50k_v1
                -> axis_buffer_ddr_sample_v2

The DDR sample buffer uses sample_decim=1 because filtering and decimation are
performed upstream in PL.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from qick import AveragerProgram, QickSoc


class FirDdrCaptureProgram(AveragerProgram):
    """Minimal tProc program that creates a readout window and DDR trigger."""

    def initialize(self):
        cfg = self.cfg
        self.gen_ch = cfg["gen_ch"]
        self.ro_ch = cfg["ro_ch"]

        self.declare_gen(ch=self.gen_ch, nqz=1)
        self.declare_readout(
            ch=self.ro_ch,
            length=cfg["readout_length"],
            freq=cfg["pulse_freq"],
            gen_ch=self.gen_ch,
        )

        freq = self.freq2reg(cfg["pulse_freq"], gen_ch=self.gen_ch, ro_ch=self.ro_ch)
        self.default_pulse_registers(
            ch=self.gen_ch,
            freq=freq,
            phase=0,
            gain=cfg["pulse_gain"],
        )
        self.set_pulse_registers(
            ch=self.gen_ch,
            style="const",
            length=cfg["pulse_length"],
        )
        self.set_readout_registers(
            ch=self.ro_ch,
            freq=cfg["pulse_freq"],
            length=cfg["readout_length"],
            phrst=1,
        )
        self.synci(200)

    def body(self):
        self.pulse(ch=self.gen_ch, t=self.cfg["pulse_t"])
        self.readout(ch=self.ro_ch, t=self.cfg["readout_t"])
        self.trigger(
            adcs=[self.ro_ch],
            ddr4=True,
            adc_trig_offset=self.cfg["adc_trig_offset"],
        )
        self.sync_all(self.cfg["sync_delay"])


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bitfile", required=True, help="1 MSPS or 50 kSPS qstl FIR .bit file")
    parser.add_argument("--download", action="store_true", help="program the FPGA before running")
    parser.add_argument("--ch", type=int, default=0, help="readout channel index")
    parser.add_argument("--gen-ch", type=int, default=0, help="generator channel index")
    parser.add_argument("--n-samples", type=int, default=1000, help="final stored post-filter samples per trigger")
    parser.add_argument("--n-triggers", type=int, default=1, help="number of DDR trigger events")
    parser.add_argument("--pulse-freq", type=float, default=0.0, help="pulse/readout frequency in MHz")
    parser.add_argument("--pulse-gain", type=int, default=20000, help="generator gain")
    parser.add_argument("--pulse-length", type=int, default=4096, help="generator pulse length")
    parser.add_argument("--margin", type=int, default=1024, help="extra upstream readout samples")
    parser.add_argument(
        "--trigger-delay-samples",
        type=int,
        default=None,
        help="optional post-trigger delay in final valid samples (V2/50 kSPS only)",
    )
    parser.add_argument("--output", default="fir_ddr_capture.npz", help="output .npz file")
    parser.add_argument("--csv", default=None, help="optional output .csv file")
    return parser.parse_args()


def main():
    args = parse_args()
    bitfile = Path(args.bitfile)
    soc = QickSoc(bitfile=str(bitfile), download=args.download)

    print("Firmware:", bitfile)
    print("DDR buffer config:")
    for key, value in soc["ddr4_buf"].items():
        if key.startswith("fir") or key in ("sample_capture", "samples_per_axi_word"):
            print(f"  {key}: {value}")

    if not soc["ddr4_buf"].get("fir_enabled", False):
        raise RuntimeError("Loaded firmware does not expose axis_fir_decim_300to1_v1 in the DDR path.")

    rate_profile = soc["ddr4_buf"].get("fir_rate_profile")
    sample_rate_hz = soc.get_ddr4_fir_sample_rate(unit="hz")
    sample_period_us = 1_000_000.0 / sample_rate_hz
    print("Detected FIR rate profile:", rate_profile)
    print(f"Stored sample rate: {sample_rate_hz:g} S/s")
    print(f"Stored sample period: {sample_period_us:g} us")

    readout_length = soc.fir_readout_length_for_capture(args.n_samples, margin=args.margin)
    cfg = {
        "reps": args.n_triggers,
        "gen_ch": args.gen_ch,
        "ro_ch": args.ch,
        "pulse_freq": args.pulse_freq,
        "pulse_gain": args.pulse_gain,
        "pulse_length": args.pulse_length,
        "readout_length": readout_length,
        "pulse_t": 100,
        "readout_t": 120,
        "adc_trig_offset": 120,
        "sync_delay": readout_length + 1000,
    }

    prog = FirDdrCaptureProgram(soc, cfg)
    reserved_words = soc.arm_ddr4_fir_samples(
        ch=args.ch,
        n_samples=args.n_samples,
        n_triggers=args.n_triggers,
        address=0,
        force_overwrite=True,
        trigger_delay_samples=args.trigger_delay_samples,
    )
    print("Reserved physical 32-bit words including zero padding:", reserved_words)

    prog.run(soc)
    iq = soc.get_ddr4_fir_samples(
        n_samples=args.n_samples,
        n_triggers=args.n_triggers,
        start=0,
    )
    print("Captured IQ shape:", iq.shape)

    sample_time_s = np.arange(args.n_samples, dtype=np.float64) / sample_rate_hz

    np.savez(
        args.output,
        iq=iq,
        sample_time_s=sample_time_s,
        sample_rate_hz=sample_rate_hz,
        sample_period_us=sample_period_us,
        fir_rate_profile=rate_profile,
        n_samples=args.n_samples,
        n_triggers=args.n_triggers,
        readout_length=readout_length,
        ddr4_buf=soc["ddr4_buf"],
    )
    print("Saved:", args.output)

    if args.csv is not None:
        np.savetxt(args.csv, iq, delimiter=",", header="I,Q", comments="")
        print("Saved:", args.csv)


if __name__ == "__main__":
    main()
