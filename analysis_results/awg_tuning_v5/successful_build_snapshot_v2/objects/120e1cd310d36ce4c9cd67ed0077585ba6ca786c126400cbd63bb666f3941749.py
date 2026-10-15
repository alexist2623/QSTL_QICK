"""SquarePulse settings and exact-word tProcessor hardware sweeps."""
from dataclasses import dataclass, asdict, replace
from collections.abc import Mapping
from math import isfinite, ceil
from numbers import Integral
import numpy as np


@dataclass(frozen=True)
class SquarePulseSweep:
    parameter: str
    start: float
    stop: float
    count: int
    gen_ch: int
    segment_name: str = "SquarePulse"
    output_name: str = "square"

    def __post_init__(self):
        if self.parameter not in ("frequency", "amplitude", "phase"):
            raise ValueError("unknown SquarePulse sweep parameter")
        if isinstance(self.count, bool) or not isinstance(self.count, Integral) or self.count < 1:
            raise ValueError("SquarePulse sweep count must be a positive integer")
        if not all(isfinite(v) for v in (self.start, self.stop)):
            raise ValueError("SquarePulse sweep endpoints must be finite")

    @property
    def points(self):
        return tuple(float(x) for x in np.linspace(self.start, self.stop, self.count))

    @property
    def axis_kind(self):
        return "square_" + self.parameter

    @property
    def coordinate_unit(self):
        return {"frequency": "MHz", "amplitude": "mV", "phase": "deg"}[self.parameter]


@dataclass(frozen=True)
class SquarePulseConfig:
    gen_ch: int
    frequency_mhz: float = 0.04
    amplitude_mv: float = 10.0
    phase_deg: float = 0.0
    full_scale_mv: float = 800.0
    mute_on_finish: bool = True
    rc_enabled: bool = False
    rc_tau_us: float = 1000.0

    def __post_init__(self):
        if not isinstance(self.rc_enabled, bool):
            raise ValueError("SquarePulse rc_enabled must be boolean")
        if not isfinite(self.rc_tau_us) or not 10 <= self.rc_tau_us <= 1_000_000:
            raise ValueError("RC tau must be between 10 us and 1000 ms")
        if not isinstance(self.mute_on_finish, bool):
            raise ValueError("SquarePulse mute_on_finish must be boolean")
        if isinstance(self.gen_ch, bool) or not isinstance(self.gen_ch, Integral) or self.gen_ch < 0:
            raise ValueError("SquarePulse generator must be a nonnegative integer")
        if not all(isfinite(v) for v in (self.frequency_mhz, self.amplitude_mv, self.phase_deg, self.full_scale_mv)):
            raise ValueError("SquarePulse parameters must be finite")
        if self.full_scale_mv <= 0 or not 0 <= self.amplitude_mv <= self.full_scale_mv:
            raise ValueError("SquarePulse amplitude must be between zero and output full scale")

    def rc_step(self, gain, gencfg):
        if not self.rc_enabled:
            return 0
        if not gencfg.get("rc_precomp_version", 0):
            raise ValueError("This SquarePulse firmware does not support RC compensation")
        from qick.precompensation import square_rc_increment
        return square_rc_increment(gain, self.rc_tau_us, float(gencfg["f_dds"]))

    def word(self, parameter, value, gencfg):
        # Import only on use: older QICK installations can still open old
        # firmware and run every pre-existing GUI experiment.
        try:
            from qick.square_pulse import frequency_word, phase_word
        except ImportError as exc:
            if isinstance(exc, ModuleNotFoundError) and exc.name in ("qick", "qick.square_pulse"):
                raise RuntimeError(
                    "The GUI's QSTL_QICK Python installation lacks SquarePulse support; "
                    "update that installation and restart the GUI."
                ) from exc
            raise RuntimeError(
                f"Cannot load SquarePulse helpers in the GUI Python environment: {exc}"
            ) from exc
        if parameter == "frequency":
            return frequency_word(value, float(gencfg["f_dds"]))
        if parameter == "phase":
            return phase_word(value)
        if not isfinite(value) or not 0 <= value <= self.full_scale_mv:
            raise ValueError("SquarePulse amplitude exceeds output full scale")
        return min(32764, int(round(value / self.full_scale_mv * 32768 / 4)) * 4)


@dataclass(frozen=True)
class OutputTriggerConfig:
    enabled: bool = False
    pin: int = 0
    scope: str = "loop"
    edge: str = "start"
    width_us: float = 1.0

    def __post_init__(self):
        if not isinstance(self.enabled, bool):
            raise ValueError("output trigger enabled must be boolean")
        if self.scope not in ("loop", "experiment") or self.edge not in ("start", "end", "both"):
            raise ValueError("invalid output trigger boundary")
        if not isfinite(self.width_us) or self.width_us <= 0:
            raise ValueError("output trigger width must be positive and finite")
        if isinstance(self.pin, bool) or not isinstance(self.pin, Integral) or self.pin < 0:
            raise ValueError("output trigger pin must be a nonnegative integer")


def get_square_configs(owner):
    """Read multi-output settings, including programs saved with the old API."""
    configs = getattr(owner, "square_pulse_configs", None)
    if configs is not None:
        return tuple(configs)
    config = getattr(owner, "square_pulse_config", None)
    return () if config is None else (config,)


def attach_square_settings(sequence, config=None, sweeps=(), trigger=None, *, follow_experiment_rc=False):
    """Attach independent SquarePulse Cartesian axes to an AWG sequence."""
    sweeps = tuple(sweeps)
    configs = () if config is None else ((config,) if isinstance(config, SquarePulseConfig) else tuple(config))
    if follow_experiment_rc:
        rc = getattr(sequence, "rc_compensation", None)
        configs = tuple(replace(item, rc_enabled=rc is not None,
                               rc_tau_us=rc.tau_us if rc is not None else 1000.0) for item in configs)
    channels = {item.gen_ch for item in configs}
    if len(channels) != len(configs):
        raise ValueError("enabled SquarePulse output ports must use unique generator indices")
    if sweeps and not configs:
        raise ValueError("SquarePulse sweep requires an enabled generator")
    if len({(axis.gen_ch, axis.parameter) for axis in sweeps}) != len(sweeps):
        raise ValueError("only one sweep per SquarePulse parameter per output is allowed")
    if any(axis.gen_ch not in channels for axis in sweeps):
        raise ValueError("SquarePulse sweep generator differs from selected output")
    sequence.sweeps = [axis for axis in sequence.sweeps if not isinstance(axis, SquarePulseSweep)] + list(sweeps)
    sequence._sweep_coordinate_cache = None
    sequence.square_pulse_configs = configs
    sequence.square_pulse_config = configs[0] if configs else None
    sequence.output_trigger_config = trigger or OutputTriggerConfig()
    return sequence


def decode_square_settings(settings, full_scale_mv=800.0):
    """Decode saved/exported settings independently of Qt and firmware."""
    settings = settings or {}
    if not isinstance(settings, dict):
        raise ValueError("SquarePulse settings must be a mapping")
    enabled = settings.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("SquarePulse enabled must be boolean")
    if not enabled:
        return None, ()
    ch = settings.get("gen_ch", 7)
    parameters = settings.get("parameters", {})
    values = {}
    for name, default in (("frequency", .04), ("amplitude", 10.0), ("phase", 0.0)):
        row = parameters.get(name, {})
        fixed = row.get("value", default)
        values[name] = row.get("start", fixed) if row.get("sweep", False) else fixed
    config = SquarePulseConfig(ch, values["frequency"], values["amplitude"], values["phase"],
                               full_scale_mv, settings.get("mute_on_finish", True),
                               settings.get("rc_enabled", False), settings.get("rc_tau_us", 1000.0))
    axes = []
    for name, value in values.items():
        row = parameters.get(name, {})
        if not isinstance(row.get("sweep", False), bool):
            raise ValueError("SquarePulse sweep enabled must be boolean")
        if row.get("sweep", False):
            axes.append(SquarePulseSweep(name, row.get("start", value), row.get("stop", value),
                                        row.get("count", 11), ch, segment_name=name, output_name=f"square{ch}"))
    return config, tuple(axes)


def decode_square_outputs(settings, full_scale_mv=800.0):
    """Decode every port; legacy single-port settings remain readable."""
    settings = settings or {}
    if not isinstance(settings, dict):
        raise ValueError("SquarePulse settings must be a mapping")
    entries = settings.get("outputs", [settings])
    if not isinstance(entries, (list, tuple)) or len(entries) > 16:
        raise ValueError("SquarePulse outputs must be a list of at most 16 ports")
    configs, axes = [], []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("SquarePulse output settings must be a mapping")
        ch = entry.get("gen_ch", 7)
        if callable(full_scale_mv):
            scale = full_scale_mv(ch)
        elif isinstance(full_scale_mv, Mapping):
            scale = full_scale_mv.get(ch, full_scale_mv.get(str(ch)))
            if scale is None and entry.get("enabled", False):
                raise ValueError(f"Missing full-scale voltage for SquarePulse generator {ch}")
        else:
            scale = full_scale_mv
        config, port_axes = decode_square_settings(entry, scale)
        if config is not None:
            configs.append(config)
            axes.extend(port_axes)
    if len({config.gen_ch for config in configs}) != len(configs):
        raise ValueError("enabled SquarePulse output ports must use unique generator indices")
    return tuple(configs), tuple(axes)


class SquarePulseProgramMixin:
    """Use the existing DMEM pointer and Cartesian-loop allocator."""
    def _configure_square_pulse(self):
        self.square_pulse_configs = get_square_configs(self.sequence)
        self.square_pulse_config = next(iter(self.square_pulse_configs), None)
        self._square_initial_words = {}
        if not self.square_pulse_configs:
            if any(isinstance(axis, SquarePulseSweep) for axis in self.sequence.sweep_axes):
                raise ValueError("SquarePulse axes require generator settings")
            return
        for config in self.square_pulse_configs:
            self._configure_square_output(config)

    def _configure_square_output(self, config):
        if config.gen_ch >= len(self.soccfg["gens"]):
            raise ValueError("SquarePulse generator is absent from this firmware")
        gen = self.soccfg["gens"][config.gen_ch]
        if gen.get("type") != "axis_square_pulse_v1":
            raise ValueError("selected generator is not a SquarePulse IP in this firmware")
        if config.gen_ch in self.awg_channels or any(rf.gen_ch == config.gen_ch for rf in self.rf_pulse_configs):
            raise ValueError("SquarePulse output cannot also be an AWG or RF output")
        config.rc_step(0, gen)  # Reject unsupported firmware before emitting code.
        self.declare_gen(ch=config.gen_ch, nqz=1)
        defaults = dict(frequency=config.frequency_mhz, amplitude=config.amplitude_mv, phase=config.phase_deg)
        for axis in self.sequence.sweep_axes:
            if isinstance(axis, SquarePulseSweep) and axis.gen_ch == config.gen_ch:
                defaults[axis.parameter] = axis.start
        self._square_initial_words[config.gen_ch] = {
            name: config.word(name, value, gen) for name, value in defaults.items()
        }

    def _square_point_table_models(self, axes):
        tables=[]
        configs = {config.gen_ch: config for config in self.square_pulse_configs}
        for index,axis in enumerate(axes):
            if not isinstance(axis,SquarePulseSweep) or axis.count <= 1:
                continue
            config = configs[axis.gen_ch]
            register={"frequency":"freq", "phase":"phase", "amplitude":"gain"}[axis.parameter]
            page,reg=self._gen_regmap[(config.gen_ch,register)]
            gen = self.soccfg["gens"][config.gen_ch]
            values = tuple(config.word(axis.parameter, v, gen) for v in axis.points)
            if axis.parameter == "amplitude" and config.rc_enabled:
                steps = tuple(config.rc_step(gain, gen) for gain in values)
                values = tuple(gain | ((step & 0xffff) << 16) for gain, step in zip(values, steps))
                rpage, rreg = self._gen_regmap[(config.gen_ch, "reserved")]
                tables.append(dict(key=("square_point_table", config.gen_ch, "rc_increment"),
                    register_name="square_rc_increment", gen_ch=config.gen_ch,
                    event_indices=(), page=int(rpage), command_register=int(rreg),
                    axis_indices=(index,), axis_shape=(axis.count,), values=tuple(step >> 16 for step in steps)))
            tables.append(dict(key=("square_point_table",config.gen_ch,axis.parameter),
                register_name="square_"+axis.parameter, gen_ch=config.gen_ch,
                event_indices=(), page=int(page),command_register=int(reg),
                axis_indices=(index,),axis_shape=(axis.count,), values=values))
        return tables

    def _emit_square_update(self, *, stop=False, reset_phase=False):
        for config in self.square_pulse_configs:
            if not stop or config.mute_on_finish:
                self._emit_square_output_update(config, stop=stop, reset_phase=reset_phase)

    def _emit_square_output_update(self, config, *, stop, reset_phase):
        words=self._square_initial_words[config.gen_ch]
        if stop:
            # Keep the final point's frequency/phase/amplitude registers intact.
            # Only disable output; the accumulator continues at its last rate.
            page, reg = self._gen_regmap[(config.gen_ch, "control")]
            control = int(self.soccfg["gens"][config.gen_ch].get("tmux_ch", 0)) << 24
            self.safe_regwi(page, reg, control, "mute SquarePulse without changing phase rate")
        else:
            rc_params = {} if not config.rc_enabled else dict(rc_enable=True,
                rc_increment=config.rc_step(words["amplitude"], self.soccfg["gens"][config.gen_ch]))
            self.set_pulse_registers(ch=config.gen_ch,style="square",freq=words["frequency"],
                phase=words["phase"],gain=words["amplitude"],enable=True,reset_phase=reset_phase, **rc_params)
            for table in self._rf_point_tables:
                if table["key"][0]=="square_point_table" and table["gen_ch"] == config.gen_ch:
                    self.memr(table["page"],table["command_register"],table["pointer_register"],"load SquarePulse hardware sweep word")
        self.pulse(ch=config.gen_ch,t=0)
        # Reserve the fixed command pipeline and transport settling before
        # starting AWG/readout commands on the shared tProcessor/TMUX output.
        gen = self.soccfg["gens"][config.gen_ch]
        guard=max(8,ceil((int(gen.get("command_latency_cycles", 4)) + 4)*self.tproc_mhz/float(gen["f_fabric"])))
        self.synci(guard)
        self.reset_timestamps()

    def _square_settings_metadata(self):
        items = [{**asdict(config), "phase_continuous": True,
                  "command_latency_cycles": int(self.soccfg["gens"][config.gen_ch].get("command_latency_cycles", 4)),
                  "sweep_execution": "tProcessor Cartesian loops with exact DMEM words"}
                 for config in self.square_pulse_configs]
        return {} if not items else dict(square_pulse=items[0], square_pulses=items)
