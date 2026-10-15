"""HWH-derived FIR-DDR capture-rate and trigger-delay metadata.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite
from typing import Any, Mapping


_KNOWN_RATES_HZ = {
    "1_msps": 1_000_000.0,
    "50_ksps": 50_000.0,
}

_DEFAULT_50_KSPS_TRIGGER_DELAY_US = 704.925
_LEGACY_400_MHZ_TRIGGER_DELAY_CYCLES = 281_970
_LEGACY_TRIGGER_SYNC_CYCLES = 3


@dataclass(frozen=True)
class FirDdrProfile:
    """Normalized FIR-DDR metadata reported by the loaded HWH/QICK driver."""

    name: str
    sample_rate_hz: float
    sample_rate_msps: float
    sample_period_us: float
    decimation: int
    input_rate_mhz: float
    group_delay_input_samples: float
    uses_fpga_trigger_delay: bool
    trigger_delay_samples: int
    software_warmup_compensation: bool
    config: Mapping[str, Any]
    trigger_delay_units: str = "valid_input_samples"

    @property
    def iq_component_bits(self) -> int:
        return int(self.config.get("iq_component_bits", 16))

    @property
    def iq_scale_log2(self) -> int:
        return int(self.config.get("iq_scale_log2", 0))

    @property
    def iq_sample_bytes(self) -> int:
        return self.iq_component_bits // 4

    @property
    def format_label(self) -> str:
        return f"signed int{self.iq_component_bits} I/Q"

    def trigger_delay_us_for(self, value: int) -> float:
        """Convert a trigger-delay register value to microseconds."""

        delay = int(value)
        if delay < 0:
            raise ValueError("trigger delay must be nonnegative")
        if self.trigger_delay_units == "s_axis_aclk_cycles":
            return delay / self.input_rate_mhz
        if self.trigger_delay_units == "valid_input_samples":
            return delay * self.sample_period_us
        if self.trigger_delay_units == "none" and delay == 0:
            return 0.0
        raise RuntimeError(
            f"unsupported FIR DDR trigger-delay units {self.trigger_delay_units!r}"
        )

    def trigger_delay_input_cycles_for(self, value: int) -> int:
        """Return the delay as 300 MSPS source/readout-clock cycles."""

        delay = int(value)
        if delay < 0:
            raise ValueError("trigger delay must be nonnegative")
        if self.trigger_delay_units == "s_axis_aclk_cycles":
            return delay
        if self.trigger_delay_units == "valid_input_samples":
            return delay * self.decimation
        if self.trigger_delay_units == "none" and delay == 0:
            return 0
        raise RuntimeError(
            f"unsupported FIR DDR trigger-delay units {self.trigger_delay_units!r}"
        )

    def trigger_delay_value_for_us(self, delay_us: Any) -> int:
        """Convert a user-facing microsecond delay to the HWH register unit."""

        delay = float(delay_us)
        if not isfinite(delay) or delay < 0.0:
            raise ValueError("trigger delay in microseconds must be nonnegative")
        if not self.uses_fpga_trigger_delay:
            if delay == 0.0:
                return 0
            raise RuntimeError(
                f"{self.rate_label} HWH does not expose an FPGA trigger-delay register"
            )
        if self.trigger_delay_units == "s_axis_aclk_cycles":
            value = int(round(delay * self.input_rate_mhz))
        elif self.trigger_delay_units == "valid_input_samples":
            value = int(round(delay / self.sample_period_us))
        else:
            raise RuntimeError(
                f"unsupported FIR DDR trigger-delay units {self.trigger_delay_units!r}"
            )
        if value > 0xFFFF_FFFF:
            raise ValueError("trigger delay exceeds the 32-bit FPGA register")
        return value

    def selected_trigger_delay_value(self, delay_us: Any = None) -> int:
        """Return the HWH default or a converted user override."""

        if delay_us is None:
            return self.trigger_delay_samples
        return self.trigger_delay_value_for_us(delay_us)

    def trigger_delay_arm_kwargs(self, value: Any = None) -> dict[str, int]:
        """Build the unit-correct QICK arm keyword for this HWH generation."""

        if not self.uses_fpga_trigger_delay:
            return {}
        delay = self.trigger_delay_samples if value is None else int(value)
        if delay < 0:
            raise ValueError("trigger delay must be nonnegative")
        if self.trigger_delay_units == "s_axis_aclk_cycles":
            return {"trigger_delay_cycles": delay}
        if self.trigger_delay_units == "valid_input_samples":
            return {"trigger_delay_samples": delay}
        raise RuntimeError(
            f"unsupported FIR DDR trigger-delay units {self.trigger_delay_units!r}"
        )

    def trigger_delay_arm_kwargs_for_us(self, delay_us: Any = None) -> dict[str, int]:
        """Build arm keywords from the HWH default or a microsecond override."""

        return self.trigger_delay_arm_kwargs(
            self.selected_trigger_delay_value(delay_us)
        )

    @property
    def trigger_delay_us(self) -> float:
        return self.trigger_delay_us_for(self.trigger_delay_samples)

    @property
    def trigger_delay_input_cycles(self) -> int:
        return self.trigger_delay_input_cycles_for(self.trigger_delay_samples)

    @property
    def software_trigger_delay_output_samples(self) -> int:
        """Stored-sample periods used to align legacy 1 MSPS capture.

        The V1 DDR buffer shares its trigger with the FIR decimator.  Delaying
        that pulse by complete output periods leaves the FIR history running
        while placing the filter's main step response at stored sample zero.
        """

        if not self.software_warmup_compensation:
            return 0
        reported = self.config.get("fir_capture_skipped_outputs")
        if reported is not None:
            skipped_outputs = int(reported)
            if skipped_outputs < 0:
                raise RuntimeError(
                    "HWH fir_capture_skipped_outputs must be nonnegative"
                )
            return skipped_outputs
        first_output_phase = self.decimation - 1
        delay_after_first = max(
            0.0,
            self.group_delay_input_samples - first_output_phase,
        )
        return int(ceil(delay_after_first / self.decimation))

    @property
    def software_trigger_delay_input_samples(self) -> int:
        """External trigger offset in FIR input-sample periods.

        The legacy BD passes the tProcessor trigger through
        ``axis_trigger_sync_v1`` before it reaches both the FIR and DDR buffer.
        Account for that three-cycle synchronizer so the shared pulse, rather
        than the raw tProcessor output, lands on the requested FIR phase.
        """

        aligned_cycles = self.software_trigger_delay_output_samples * self.decimation
        sync_cycles = int(self.config.get(
            "fir_capture_trigger_sync_cycles",
            _LEGACY_TRIGGER_SYNC_CYCLES,
        ))
        if sync_cycles < 0:
            raise RuntimeError(
                "HWH fir_capture_trigger_sync_cycles must be nonnegative"
            )
        return max(0, aligned_cycles - sync_cycles)

    @property
    def software_aligned_trigger_input_samples(self) -> int:
        """Shared FIR/DDR trigger offset after source-clock synchronization."""

        return self.software_trigger_delay_output_samples * self.decimation

    @property
    def software_trigger_delay_us(self) -> float:
        """Legacy capture-trigger offset in microseconds."""

        return self.software_trigger_delay_input_samples / self.input_rate_mhz

    @property
    def software_aligned_trigger_delay_us(self) -> float:
        """Shared FIR/DDR trigger offset after source-clock synchronization."""

        return self.software_aligned_trigger_input_samples / self.input_rate_mhz

    def software_trigger_delay_tproc_cycles(self, tproc_mhz: Any) -> int:
        """Convert the legacy capture alignment to tProcessor clock cycles."""

        clock_mhz = _positive_float(tproc_mhz, "tproc_mhz")
        return int(ceil(
            self.software_trigger_delay_input_samples
            * clock_mhz
            / self.input_rate_mhz
        ))

    @property
    def rate_label(self) -> str:
        return format_sample_rate_hz(self.sample_rate_hz)

    @property
    def timing_label(self) -> str:
        if self.uses_fpga_trigger_delay:
            unit_label = (
                "source-clock cycles"
                if self.trigger_delay_units == "s_axis_aclk_cycles"
                else "valid input samples"
            )
            delay = (
                f", FPGA delay {self.trigger_delay_samples} {unit_label} "
                f"({self.trigger_delay_us:g} us)"
            )
        else:
            delay = (
                ", tProcessor trigger delay "
                f"{self.software_trigger_delay_us:g} us "
                "(shared FIR/DDR trigger "
                f"{self.software_aligned_trigger_delay_us:g} us after the signal edge)"
            )
        return (
            f"{self.rate_label}, {self.format_label} ({self.sample_period_us:g} us/sample{delay})"
        )


def _positive_float(value: Any, name: str) -> float:
    result = float(value)
    if not isfinite(result) or result <= 0.0:
        raise RuntimeError(f"HWH {name} must be positive and finite")
    return result


def format_sample_rate_hz(sample_rate_hz: Any) -> str:
    """Format supported and custom sample rates for compact GUI status text."""

    rate_hz = _positive_float(sample_rate_hz, "sample_rate_hz")
    if abs(rate_hz - 1_000_000.0) <= 0.5:
        return "1 MSPS"
    if abs(rate_hz - 50_000.0) <= 0.5:
        return "50 kSPS"
    if rate_hz >= 1_000_000.0:
        return f"{rate_hz / 1_000_000.0:g} MSPS"
    if rate_hz >= 1_000.0:
        return f"{rate_hz / 1_000.0:g} kSPS"
    return f"{rate_hz:g} S/s"


def _sample_rate_hz(ddr_cfg: Mapping[str, Any]) -> float:
    for key in (
        "stored_sample_rate_hz",
        "fir_output_sample_rate_hz",
        "fir_sample_rate_hz",
    ):
        value = ddr_cfg.get(key)
        if value is not None:
            return _positive_float(value, key)

    for key in (
        "stored_sample_rate_msps",
        "fir_output_fs_mhz",
        "fir_sample_rate_msps",
    ):
        value = ddr_cfg.get(key)
        if value is not None:
            return _positive_float(value, key) * 1_000_000.0

    raise RuntimeError("HWH does not report the FIR-DDR stored sample rate")


def _rate_profile(rate_hz: float, reported_name: Any) -> str:
    normalized_name = str(reported_name or "").strip().lower()
    for name, expected_hz in _KNOWN_RATES_HZ.items():
        if normalized_name == name:
            if abs(rate_hz - expected_hz) > max(0.5, expected_hz * 1.0e-9):
                raise RuntimeError(
                    f"HWH FIR rate profile {name!r} conflicts with "
                    f"reported rate {rate_hz:g} Hz"
                )
            return name

    for name, expected_hz in _KNOWN_RATES_HZ.items():
        if abs(rate_hz - expected_hz) <= max(0.5, expected_hz * 1.0e-9):
            return name

    supported = ", ".join(f"{value:g} Hz" for value in _KNOWN_RATES_HZ.values())
    raise RuntimeError(
        f"unsupported FIR-DDR stored sample rate {rate_hz:g} Hz; "
        f"supported HWH profiles are {supported}"
    )


def resolve_fir_ddr_profile(soccfg: Any, *, context: str = "FIR DDR") -> FirDdrProfile:
    """Resolve one supported capture profile from ``soccfg['ddr4_buf']``.

    The 1 MSPS firmware has a shared FIR/DDR trigger, so software starts the
    readout early and delays that shared trigger by complete decimated-output
    periods. The 50 kSPS firmware must expose the V2 programmable trigger-delay
    register. Legacy V2 firmware counts valid input samples; current V2
    firmware uses source AXIS clock cycles. Software must preserve the
    HWH-reported unit and must not move the tProcessor trigger by the FIR group
    delay.
    """

    try:
        ddr_cfg = dict(soccfg["ddr4_buf"])
    except (KeyError, TypeError) as exc:
        raise RuntimeError(f"{context} requires a DDR sample buffer in the HWH") from exc

    if not ddr_cfg.get("sample_capture", False):
        raise RuntimeError(f"{context} requires sample-triggered DDR firmware")
    if not ddr_cfg.get("fir_enabled", False):
        raise RuntimeError(f"{context} requires an HWH-detected FIR DDR path")

    sample_rate_hz = _sample_rate_hz(ddr_cfg)
    profile_name = _rate_profile(sample_rate_hz, ddr_cfg.get("fir_rate_profile"))
    decimation = int(ddr_cfg.get("fir_decimation", 0))
    if decimation <= 0:
        raise RuntimeError("HWH fir_decimation must be positive")
    input_rate_mhz = _positive_float(
        ddr_cfg.get("fir_input_fs_mhz", 300.0),
        "fir_input_fs_mhz",
    )
    group_delay = float(ddr_cfg.get("fir_group_delay_input_samples", 0.0))
    if not isfinite(group_delay) or group_delay < 0.0:
        raise RuntimeError("HWH fir_group_delay_input_samples must be nonnegative")

    component_bits = int(ddr_cfg.get("iq_component_bits", 16))
    scale_log2 = int(ddr_cfg.get("iq_scale_log2", 0))
    stream_bits = int(ddr_cfg.get("s_axis_data_width", component_bits*2))
    version = int(ddr_cfg.get("iq_format_version", 0))
    if (component_bits, scale_log2, version) not in ((16, 0, 0), (64, 46, 1)) or stream_bits != component_bits*2:
        raise RuntimeError("Unsupported or inconsistent FIR DDR integer format; update the QICK driver and use matching BIT/HWH files")
    if int(ddr_cfg.get("iq_sample_bytes", component_bits//4)) != component_bits//4:
        raise RuntimeError("HWH IQ byte width conflicts with component width")
    uses_fpga_trigger_delay = profile_name == "50_ksps" or bool(
        ddr_cfg.get("supports_trigger_delay", False)
        and ddr_cfg.get("decimation_phase_continuous", False)
        and not ddr_cfg.get("fir_decimation_phase_reset_on_trigger", False)
    )
    trigger_delay_samples = 0
    trigger_delay_units = "none"
    if uses_fpga_trigger_delay:
        if not ddr_cfg.get("supports_trigger_delay", False):
            raise RuntimeError(
                "50 kSPS FIR-DDR HWH requires axis_buffer_ddr_sample_v2 "
                "programmable trigger delay"
            )
        trigger_delay_units = str(
            ddr_cfg.get("trigger_delay_units") or "valid_input_samples"
        )
        if trigger_delay_units not in (
            "valid_input_samples",
            "s_axis_aclk_cycles",
        ):
            raise RuntimeError(
                "50 kSPS DDR trigger delay must use valid_input_samples or "
                "s_axis_aclk_cycles units"
            )
        default_key = (
            "trigger_delay_default_cycles"
            if trigger_delay_units == "s_axis_aclk_cycles"
            else "trigger_delay_default_samples"
        )
        trigger_delay_samples = int(ddr_cfg.get(default_key, 0))
        if trigger_delay_samples < 0:
            raise RuntimeError(f"HWH {default_key} must be nonnegative")
        if (
            profile_name == "50_ksps"
            and trigger_delay_units == "s_axis_aclk_cycles"
            and trigger_delay_samples
            == _LEGACY_400_MHZ_TRIGGER_DELAY_CYCLES
            and abs(input_rate_mhz - 300.0) <= 1.0e-9
        ):
            # The deployed HWH default was calculated with a 400 MHz clock.
            # Keep the bitstream untouched and apply the requested 704.925 us
            # default using the actual 300 MHz source clock in the GUI.
            trigger_delay_samples = int(
                round(_DEFAULT_50_KSPS_TRIGGER_DELAY_US * input_rate_mhz)
            )

    return FirDdrProfile(
        name=profile_name,
        sample_rate_hz=sample_rate_hz,
        sample_rate_msps=sample_rate_hz / 1_000_000.0,
        sample_period_us=1_000_000.0 / sample_rate_hz,
        decimation=decimation,
        input_rate_mhz=input_rate_mhz,
        group_delay_input_samples=group_delay,
        uses_fpga_trigger_delay=uses_fpga_trigger_delay,
        trigger_delay_samples=trigger_delay_samples,
        software_warmup_compensation=not uses_fpga_trigger_delay,
        config=ddr_cfg,
        trigger_delay_units=trigger_delay_units,
    )


__all__ = [
    "FirDdrProfile",
    "format_sample_rate_hz",
    "resolve_fir_ddr_profile",
    "iq_in_input_units",
    "result_iq_in_input_units",
]


def iq_in_input_units(iq: Any, scale_log2: int = 0):
    """Return a floating display/analysis copy; never modify raw integer data."""
    import numpy as np
    raw = np.asarray(iq)
    if scale_log2 and (raw.dtype.kind != 'i' or raw.dtype.itemsize != 8):
        raise RuntimeError("IQ64 firmware must return raw signed-int64 data")
    return np.ldexp(raw.astype(np.float64), -int(scale_log2))


def result_iq_in_input_units(result: Any):
    import numpy as np
    scale = int(getattr(result, "iq_scale_log2", 0))
    return iq_in_input_units(result.iq, scale) if scale else np.asarray(result.iq)
