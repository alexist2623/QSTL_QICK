"""Independent FIR-DDR acquisition for the Noise Analysis tab.

This module intentionally has no dependency on the GUI experiment, stability,
or S-parameter models.  It configures one readout, arms the FIR-backed DDR
buffer, emits one tProcessor DDR trigger, and returns the captured I/Q trace.

Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite
import time
from typing import Any, Callable, Optional, Tuple

import numpy as np

try:
    from .dc_waveform_core import QickDdrReadoutSpec
    from .fir_ddr_profile import resolve_fir_ddr_profile
    from .qick_qcodes_experiment import (
        QickConnectionConfig,
        configure_rf_board,
        connect_qick,
    )
except ImportError:
    from dc_waveform_core import QickDdrReadoutSpec
    from fir_ddr_profile import resolve_fir_ddr_profile
    from qick_qcodes_experiment import (
        QickConnectionConfig,
        configure_rf_board,
        connect_qick,
    )


def _bounded_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    result = int(value)
    if result < minimum or result > maximum:
        raise ValueError(f"{name} must be in [{minimum}, {maximum}]")
    return result


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


@dataclass(frozen=True)
class NoiseAcquisitionConfig:
    """Self-contained settings for one direct FIR-DDR noise acquisition."""

    host: str = "192.168.2.99"
    ns_port: int = 8888
    proxy_name: str = "myqick"
    ro_ch: int = 0
    input_board_type: str = "RF_In"
    nqz: int = 1
    fir_samples: int = 1_000_000
    readout_frequency_mhz: float = 0.0
    attenuation_db: float = 20.0
    dc_gain_db: float = 0.0
    filter_type: str = "bypass"
    filter_cutoff_ghz: float = 2.5
    filter_bandwidth_ghz: float = 1.0
    margin_input_samples: int = 1024
    fpga_trigger_delay_us: Optional[float] = None
    address: int = 0
    force_overwrite: bool = True
    post_run_read_delay_seconds: float = 0.1

    def __post_init__(self) -> None:
        QickConnectionConfig(self.host, self.ns_port, self.proxy_name)
        _bounded_int(self.ro_ch, "readout channel", 0, 255)
        if self.input_board_type not in {"RF_In", "DC_In"}:
            raise ValueError("input_board_type must be RF_In or DC_In")
        _bounded_int(self.nqz, "ADC Nyquist zone", 1, 2)
        _bounded_int(self.fir_samples, "FIR samples", 2, 100_000_000)
        _finite(self.readout_frequency_mhz, "readout frequency")
        attenuation = _finite(self.attenuation_db, "input attenuation")
        if attenuation < 0.0 or attenuation > 31.75:
            raise ValueError("input attenuation must be in [0, 31.75] dB")
        dc_gain = _finite(self.dc_gain_db, "DC input gain")
        if dc_gain < -6.0 or dc_gain > 26.0:
            raise ValueError("DC input gain must be in [-6, 26] dB")
        if self.filter_type not in {"bypass", "lowpass", "highpass", "bandpass"}:
            raise ValueError("unsupported input filter type")
        cutoff = _finite(self.filter_cutoff_ghz, "filter cutoff/center")
        bandwidth = _finite(self.filter_bandwidth_ghz, "filter bandwidth")
        if cutoff < 0.0:
            raise ValueError("filter cutoff/center must be nonnegative")
        if bandwidth <= 0.0:
            raise ValueError("filter bandwidth must be positive")
        _bounded_int(
            self.margin_input_samples,
            "FIR input margin",
            0,
            1 << 30,
        )
        if self.fpga_trigger_delay_us is not None:
            fpga_delay = _finite(
                self.fpga_trigger_delay_us,
                "FPGA trigger delay",
            )
            if fpga_delay < 0.0:
                raise ValueError("FPGA trigger delay must be nonnegative")
        _bounded_int(self.address, "DDR address", 0, (1 << 63) - 1)
        if not isinstance(self.force_overwrite, bool):
            raise TypeError("force_overwrite must be boolean")
        delay = _finite(
            self.post_run_read_delay_seconds,
            "post-run read delay",
        )
        if delay < 0.0:
            raise ValueError("post-run read delay must be nonnegative")

    @property
    def connection_config(self) -> QickConnectionConfig:
        return QickConnectionConfig(
            host=self.host,
            ns_port=self.ns_port,
            proxy_name=self.proxy_name,
        )

    def readout_spec(self) -> QickDdrReadoutSpec:
        """Build the shared RF-board configuration object for this input."""
        return QickDdrReadoutSpec(
            ro_ch=self.ro_ch,
            segment_name="noise_capture",
            delay_us=0.0,
            samples_per_trigger=self.fir_samples,
            readout_frequency_mhz=self.readout_frequency_mhz,
            margin_input_samples=self.margin_input_samples,
            fpga_trigger_delay_us=self.fpga_trigger_delay_us,
            address=self.address,
            force_overwrite=self.force_overwrite,
            post_run_read_delay_seconds=self.post_run_read_delay_seconds,
            attenuation_db=self.attenuation_db,
            filter_type=self.filter_type,
            filter_cutoff=self.filter_cutoff_ghz,
            filter_bandwidth=self.filter_bandwidth_ghz,
            input_board_type=self.input_board_type,
            dc_gain_db=self.dc_gain_db,
            nqz=self.nqz,
        )


@dataclass(frozen=True)
class NoiseAcquisitionResult:
    """One direct FIR-DDR I/Q capture and its HWH-derived timing metadata."""

    iq: np.ndarray
    sample_rate_hz: float
    reserved_physical_words: Optional[int]
    capture_seconds: float
    source: str
    iq_scale_log2: int = 0
    iq_component_bits: int = 16

    def __post_init__(self) -> None:
        iq = np.asarray(self.iq)
        if iq.ndim != 2 or iq.shape[1] != 2 or iq.shape[0] < 2:
            raise ValueError("noise I/Q must have shape (sample, 2)")


def _validate_fir_ddr(soccfg: Any, config: NoiseAcquisitionConfig):
    profile = resolve_fir_ddr_profile(
        soccfg,
        context="noise acquisition",
    )
    if config.ro_ch >= len(soccfg["readouts"]):
        raise IndexError("noise readout channel is out of range")
    return profile


def build_noise_fir_program(soccfg: Any, config: NoiseAcquisitionConfig):
    """Build a minimal ASM-v1 program that only starts DDC and DDR capture."""
    try:
        from qick import AveragerProgram
    except ImportError:
        try:
            from qick.averager_program import AveragerProgram
        except ImportError as exc:
            raise RuntimeError(
                "QICK Python library is required for direct noise acquisition"
            ) from exc

    profile = _validate_fir_ddr(soccfg, config)
    trigger_delay_value = profile.selected_trigger_delay_value(
        config.fpga_trigger_delay_us
    )
    readout_cfg = soccfg["readouts"][config.ro_ch]
    tproc_mhz = float(soccfg["tprocs"][0]["f_time"])
    group_delay = int(ceil(profile.group_delay_input_samples))
    warmup_cycles = (
        int(ceil(group_delay * tproc_mhz / profile.input_rate_mhz))
        if profile.software_warmup_compensation
        else 0
    )
    software_trigger_delay_cycles = profile.software_trigger_delay_tproc_cycles(
        tproc_mhz
    )
    monitor_length = min(
        config.fir_samples,
        int(readout_cfg.get("buf_maxlen", config.fir_samples)),
    )

    class DirectNoiseFirProgram(AveragerProgram):
        def initialize(self):
            self.declare_readout(ch=config.ro_ch, length=max(1, monitor_length))
            try:
                freq_word = self.freq2reg_adc(
                    config.readout_frequency_mhz,
                    ro_ch=config.ro_ch,
                    gen_ch=None,
                )
            except KeyError as exc:
                if exc.args != ("refclk_freq",):
                    raise
                b_dds = int(readout_cfg["b_dds"])
                freq_word = int(round(
                    config.readout_frequency_mhz
                    * (1 << b_dds)
                    / float(readout_cfg["f_dds"])
                )) % (1 << b_dds)
            self.set_readout_registers(
                ch=config.ro_ch,
                freq=freq_word,
                length=65535,
                mode="periodic",
                phrst=0,
            )

        def body(self):
            self.readout(ch=config.ro_ch, t=0)
            self.trigger(
                ddr4=True,
                adc_trig_offset=0,
                t=software_trigger_delay_cycles,
                width=12,
            )
            # Queue both timed events before the program ends.  Long capture
            # completion is awaited on the host, avoiding tProcessor immediate
            # width limits for multi-second traces.
            self.synci(max(1, software_trigger_delay_cycles + 13))

    program = DirectNoiseFirProgram(soccfg, {"reps": 1})
    program.noise_fir_warmup_tproc_cycles = warmup_cycles
    program.noise_fir_software_trigger_delay_tproc_cycles = (
        software_trigger_delay_cycles
    )
    program.noise_fir_rate_profile = profile.name
    program.noise_fir_fpga_trigger_delay_samples = trigger_delay_value
    program.noise_fir_fpga_trigger_delay_units = profile.trigger_delay_units
    program.noise_fir_fpga_trigger_delay_us = profile.trigger_delay_us_for(
        trigger_delay_value
    )
    return program


def acquire_noise_fir_trace(
    config: NoiseAcquisitionConfig,
    *,
    connector: Optional[Callable[..., Tuple[Any, Any]]] = None,
    program_factory: Optional[Callable[[Any, NoiseAcquisitionConfig], Any]] = None,
    sleeper: Callable[[float], None] = time.sleep,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> NoiseAcquisitionResult:
    """Acquire one FIR-decimated trace without using any other GUI tab state."""

    def progress(percent: int, message: str) -> None:
        if progress_callback is not None:
            progress_callback(int(percent), str(message))

    progress(2, "Connecting to QICK")
    soc, soccfg = connect_qick(config.connection_config, connector=connector)
    profile = _validate_fir_ddr(soccfg, config)
    trigger_delay_value = profile.selected_trigger_delay_value(
        config.fpga_trigger_delay_us
    )
    trigger_delay_us = profile.trigger_delay_us_for(trigger_delay_value)
    progress(8, "Configuring the selected ADC input")
    configure_rf_board(soc, (), config.readout_spec())
    progress(12, "Compiling the independent FIR-DDR capture program")
    factory = build_noise_fir_program if program_factory is None else program_factory
    program = factory(soccfg, config)

    output_rate_hz = profile.sample_rate_hz
    input_rate_hz = profile.input_rate_mhz * 1.0e6
    group_delay_input_samples = profile.group_delay_input_samples
    capture_seconds = (
        config.fir_samples / output_rate_hz
        + trigger_delay_us / 1.0e6
        + (group_delay_input_samples + config.margin_input_samples)
        / input_rate_hz
    )

    progress(15, "Arming FIR DDR capture")
    arm_kwargs = dict(
        ch=config.ro_ch,
        n_samples=config.fir_samples,
        n_triggers=1,
        address=config.address,
        stride_bytes=None,
        force_overwrite=config.force_overwrite,
    )
    if profile.uses_fpga_trigger_delay:
        arm_kwargs.update(
            profile.trigger_delay_arm_kwargs(trigger_delay_value)
        )
    reserved = soc.arm_ddr4_fir_samples(**arm_kwargs)
    progress(18, "Starting readout and DDR trigger")
    program.run_rounds(soc, progress=False)
    # The DDR writer runs independently after the short tProcessor program.
    # Waiting on the host supports captures far longer than a waiti immediate.
    sleeper(capture_seconds + config.post_run_read_delay_seconds)
    progress(92, "Reading FIR samples from DDR")
    raw = np.asarray(soc.get_ddr4_fir_samples(
        n_samples=config.fir_samples,
        n_triggers=1,
        start=config.address // 4,
        stride_bytes=None,
    ))
    expected_shape = (config.fir_samples, 2)
    if profile.iq_component_bits == 64 and raw.dtype != np.dtype("int64"):
        raise RuntimeError("IQ64 firmware did not return raw signed-int64 samples")
    if raw.shape != expected_shape:
        raise RuntimeError(
            f"unexpected FIR DDR shape {raw.shape}; expected {expected_shape}"
        )
    progress(100, "Noise trace acquired")
    return NoiseAcquisitionResult(
        iq=raw,
        iq_scale_log2=profile.iq_scale_log2,
        iq_component_bits=profile.iq_component_bits,
        sample_rate_hz=output_rate_hz,
        reserved_physical_words=(
            None if reserved is None else int(reserved)
        ),
        capture_seconds=capture_seconds,
        source=(
            f"Direct FIR-DDR readout {config.ro_ch} at "
            f"{config.readout_frequency_mhz:g} MHz | "
            f"{profile.sample_rate_hz:g} S/s ({profile.name})"
        ),
    )


__all__ = [
    "NoiseAcquisitionConfig",
    "NoiseAcquisitionResult",
    "acquire_noise_fir_trace",
    "build_noise_fir_program",
]
