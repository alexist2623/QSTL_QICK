"""PYNQ driver for the phase-continuous SquarePulse generator."""
from .generator import AbsPulsedSignalGen
from ..square_pulse import frequency_word, phase_word, square_words


class AxisSquarePulseV1(AbsPulsedSignalGen):
    bindto = ["QICK:QICK:axis_square_pulse_v1:1.0"]
    TPROC_PORT = "s_axis"
    HAS_MIXER = False
    HAS_DDS = True
    B_DDS = B_PHASE = 32
    MAXV = 32764

    def _init_config(self, description):
        super()._init_config(description)
        params = description.get("parameters", {})
        n = int(params.get("N_PTS", 16))
        if n not in (1, 2, 4, 8, 16) or int(params.get("B", 16)) != 16 or int(params.get("CMD_WIDTH", 160)) != 160:
            raise ValueError("unsupported square DDS hardware parameters")
        self.REGISTERS = {"mute_reg": 0, "identity_reg": 0, "status_reg": 1, "latency_reg": 2}
        self.cfg.update(gen_type="square_pulse", n_pts=n, samps_per_clk=n,
                        cmd_width=160, minv=-32764, dac_invalid_lsb=2,
                        dac_effective_bits=14, continuous_output=True,
                        command_latency_cycles=4, phase_continuous=True)
        rc_version = int(params.get("RC_PRECOMP_VERSION", 0))
        self.cfg.update(rc_precomp_version=rc_version, output_latency_cycles=11 if rc_version else 0,
                        command_latency_cycles=15 if rc_version else 4, rc_fraction_bits=48 if rc_version else 0)

    def mute(self):
        """Mute independently of tProc; stop_tproc() first to prevent re-enable."""
        self.mute_reg = 0

    def get_status(self, decode=False):
        status = int(self.status_reg)
        return (dict(raw=status, enabled=bool(status & 1),
                     rc_clipped=bool(status & 4)) if decode else status)

    def words(self, freq_mhz, amplitude, phase_deg=0.0, *, enable=True, reset_phase=False,
              rc_tau_us=None, reset_rc=False):
        from ..precompensation import square_rc_increment
        if (rc_tau_us is not None or reset_rc) and not self.cfg.get("rc_precomp_version"):
            raise ValueError("This firmware does not support RC precompensation")
        step = 0 if rc_tau_us is None else square_rc_increment(amplitude, rc_tau_us, self["f_dds"])
        return square_words(frequency_word(freq_mhz, self["f_dds"]),
                            phase_word(phase_deg), amplitude, enable=enable,
                            reset_phase=reset_phase, tmux_ch=self.cfg.get("tmux_ch"),
                            rc_enable=rc_tau_us is not None,rc_increment=step,reset_rc=reset_rc)
