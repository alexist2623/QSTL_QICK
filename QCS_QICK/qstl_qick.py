"""QSTL Program to QICK Program Executor"""
from typing import (
    Optional,
    Any,
    Callable
)
import numpy as np

from qstl_program import Program
from qstl_channel import (
    ChannelMapper,
    Channels,
    SingleVirtualChannel,
    InstrumentEnum
)
from qstl_waveform import (
    Delay,
    HardwareOperation,
    ConstantEnvelope,
    GaussianEnvelope,
    DCWaveform,
    RFWaveform,
    Synchronize,
)
from qstl_variable import (
    Scalar,
)
from qstl_dummy import DummyQickProgram
from qick import *

class Executor:
    r"""
    QICK Executor class to convert QSTL programs to QICK programs and run them
    """
    MAX_REGISTERS = 9  # max number of variable registers in QICK (3, 4, ..., 11)
    LAST_REG = 11
    START_REG = 3

    def __init__(
        self,
        channel_mapper: ChannelMapper,
        soc: Optional[QickConfig] = None,
        hw_demod:bool = False,
    ):
        # QICK SoC object
        self._soc = soc
        # Virtual to physical channel mapper
        self._channel_mapper = channel_mapper
        # Hardware demodulation flag
        self._hw_demod = hw_demod
        # QICK program object
        self._qick_program: QickProgram = None
        # QSTL program object
        self._qstl_program: Program = None
        # Time register to control output generators
        self._time_reg_scalar: dict[SingleVirtualChannel, Scalar] = {}
        # Temporal register to control output generators
        self._temporal_reg_scalar: dict[SingleVirtualChannel, Scalar] = {}
        # Map which converts Scalar variables to QICK register values
        self._scalar_eval_map: dict[Scalar, Callable] = {}
        self._scalar_treg_map: dict[Scalar, tuple[int, int]] = {}
        self._scalar_vreg_map: dict[Scalar, tuple[int, int]] = {}

    def execute(self, program: Program) -> None | DummyQickProgram:
        r"""
        Generate QICK program and run
        """
        self._qick_program = QickProgram(self._soc) if self._soc is not None else DummyQickProgram()
        self.walk_program(program)
        self.make_program(program)

        if self._soc is None:
            return self._qick_program
        else:
            if self._hw_demod is True:
                return self._qick_program.acquire()
            else:
                return self._qick_program.acquire_trace()

    def add_vreg(self, ch:int, scalar: Scalar) -> None:
        r"""
        Add Scalar variable to QICK program as a variable register.
        Note that page should be equal to physical channel address.
        """
        values = self._scalar_vreg_map.values()
        (page, _) = self._qick_program._gen_regmap[(ch, "0")]
        count = len([1 for (p, _) in values if p == page]) + self.START_REG - 1
        if count >= self.LAST_REG:
            raise ValueError("Exceeded maximum number of variable registers in QICK.")
        self._scalar_vreg_map[scalar] = (page, count + 1)
    
    def get_reg_from_scalar(self, scalar: Scalar) -> tuple[int, int]:
        r"""
        Return QICK variable register address of Scalar variable
        """
        return self._scalar_vreg_map[scalar]

    def write_vreg2treg(self, scalar: Scalar) -> None:
        r"""
        Write Scalar variable values to QICK program variable registers
        """
        vpage, vreg = self._scalar_vreg_map[scalar]
        tpage, treg = self._scalar_treg_map[scalar]
        if vpage != tpage:
            raise ValueError("Variable and target register pages do not match.")
        # There is no direct way to move data between variable registers and target registers in QICK.
        # So, use add instruction with 0.
        self._qick_program.add(vpage, treg, vreg, 0)

    def walk_program(self, program: Program) -> None:
        r"""
        Walk through the QICK program to setup Scalar variables
        """
        # Setup time registers for output channels
        for channel in self._channel_mapper.out_channel_map:
            ch = self.get_physical_channel(channel)
            # Setup time registers for output channels
            time_reg = Scalar(
                name = f"time_reg_ch{ch}",
                value = 0,
                dtype = int,
            )

            # Setup temporal registers for output channels
            temporal_reg = Scalar(
                name = f"temporal_reg{ch}",
                value = 0,
                dtype = int,
            )

            # Set actual registers in QICK program
            self.add_vreg(ch, time_reg)
            self.add_vreg(ch, temporal_reg)

            # Map virtual channel to time and temporal registers
            self._time_reg_scalar[channel] = time_reg
            self._temporal_reg_scalar[channel] = temporal_reg

        # Walk through the program to setup Scalar variables
        for op in program.operations:
            if isinstance(op, Synchronize):
                pass
            elif op[0] in self._channel_mapper.out_channel_map:
                channel, operation = op
                if isinstance(operation, Delay):
                    if isinstance(operation.duration, Scalar):
                        self._scalar_eval_map[operation.duration] = lambda x: self._qick_program.us2cycles(x * 1e6, 0, 0)
                    else:
                        pass
                elif isinstance(operation, DCWaveform):
                    pass
                elif isinstance(operation, RFWaveform) and self.get_instrument_type(channel) is InstrumentEnum.RF:
                    freq    = operation.rf_frequency
                    phase   = operation.instantaneous_phase
                    gain    = operation.amplitude
                    length  = operation.duration
                    ch      = self.get_physical_channel(channel)
                    if isinstance(freq, Scalar) and freq not in self._scalar_eval_map:
                        self._scalar_eval_map[freq] = lambda x: self._qick_program.freq2reg(x * 1e6, 0, 0)
                        self._scalar_treg_map[freq] = self._qick_program._gen_regmap[(ch, "freq")]
                        self.add_vreg(ch, freq)
                    if isinstance(phase, Scalar) and phase not in self._scalar_eval_map:
                        self._scalar_eval_map[phase] = lambda x: self._qick_program.deg2reg(x, 0, 0)
                        self._scalar_treg_map[phase] = self._qick_program._gen_regmap[(ch, "phase")]
                        self.add_vreg(ch, phase)
                    if isinstance(gain, Scalar) and gain not in self._scalar_eval_map:
                        self._scalar_eval_map[gain] = lambda x: int(x * (32767)) & 0xFFFF
                        self._scalar_treg_map[gain] = self._qick_program._gen_regmap[(ch, "gain")]
                        self.add_vreg(ch, gain)
                    if isinstance(length, Scalar) and length not in self._scalar_eval_map:
                        self._scalar_eval_map[length] = lambda x: self._qick_program.us2cycles(x * 1e6, 0, 0)
                        self._scalar_treg_map[length] = self._qick_program._gen_regmap[(ch, "mode")]
                        self.add_vreg(ch, length)

                elif op[0] in self._channel_mapper.in_channel_map:
                    # TODO
                    pass
                else:
                    raise NotImplementedError(f"Operation {operation} not implemented")
        return

    def make_program(self, program: Program) -> None:
        r"""
        Convert QSTL program to QICK program
        """
        for op in program.operations:
            if isinstance(op, Synchronize):
                pass
            elif op[0] in self._channel_mapper.out_channel_map:
                channel, operation = op
                if isinstance(operation, Delay):
                    (_, rl) = self.get_reg_from_scalar(self._time_reg_scalar[channel])
                    rp = self.get_physical_channel(channel)
                    self._qick_program.math(rp, rl, rl, "+", rl)
                elif isinstance(operation, DCWaveform):
                    pass
                elif isinstance(operation, RFWaveform):
                    self.setup_pulse_regs(channel, operation, out=True)
                elif op[0] in self._channel_mapper.in_channel_map:
                    # TODO
                    pass
                else:
                    raise NotImplementedError(f"Operation {operation} not implemented")
        return

    def get_physical_channel(self, channel: SingleVirtualChannel) -> int:
        r"""
        Return physical channel address of virtual channel. Note that this 
        is different from output channel number.
        """
        return self._channel_mapper.get_physical_channel(channel).addr

    def get_instrument_type(self, channel: SingleVirtualChannel) -> InstrumentEnum:
        r"""
        Return instrument type of virtual channel
        """
        return self._channel_mapper.get_physical_channel(channel).inst_type
    
    def setup_pulse_regs(
        self,
        channel: SingleVirtualChannel,
        operation: HardwareOperation,
        out: bool,
    ) -> None:
        r"""
        Map pulse parameters to QICK register values
        """
        freq    = operation.rf_frequency
        phase   = operation.instantaneous_phase
        gain    = operation.amplitude
        length  = operation.duration

        if out is True:
            # Map Scalar variables to QICK register value functions
            if isinstance(freq, Scalar):
                freq = freq.get_value()
            if isinstance(phase, Scalar):
                phase = phase.get_value()
            if isinstance(gain, Scalar):
                gain = gain.get_value()
            if isinstance(length, Scalar):
                length = length.get_value()

            freq_reg    = self._qick_program.freq2reg(operation.rf_frequency * 1e-6, 0, 0)
            phase_reg   = self._qick_program.deg2reg(phase, 0, 0)
            gain_reg    = int(gain * (32767)) & 0xFFFF
            length_reg  = self._qick_program.us2cycles(length * 1e6, 0, 0) & 0xFFFF
            ch          = self.get_physical_channel(channel)
            
            if isinstance(operation.envelope, ConstantEnvelope):
                self._qick_program.set_pulse_registers(
                    ch      = ch,
                    style   = "const",
                    # Can be setup with qstl.Scalar
                    freq    = freq_reg,
                    phase   = phase_reg,
                    gain    = gain_reg,
                    length  = length_reg,
                    phrst   = 1 if channel.absolute_phase is True else 0,
                )
            elif isinstance(operation.envelope, GaussianEnvelope):
                self._qick_program.set_pulse_registers(
                    ch      = ch,
                    style   = "arb",
                    # Can be setup with qstl.Scalar
                    freq    = freq_reg,
                    phase   = phase_reg,
                    gain    = gain_reg,
                    phrst   = 1 if channel.absolute_phase is True else 0,
                    outsel  = "product",
                    waveform= operation.name,
                )
            else:
                raise NotImplementedError(f"Envelope {operation.envelope} not implemented")

            (rp,  rt)   = self._qick_program._gen_regmap[(ch, "t")]
            (rp1, rm)   = self._qick_program._gen_regmap[(ch, "mode")]
            (rp2, rl)   = self.get_reg_from_scalar(self._time_reg_scalar[channel])
            (rp3, rtemp)= self.get_reg_from_scalar(self._temporal_reg_scalar[channel])
            if rp != rp1 or rp != rp2 or rp != rp3:
                raise ValueError(
                    "Register pages do not match."
                    f"rp={rp}, rp1={rp1}, rp2={rp2}, rp3={rp3}"
            )

            next_pulse = self._qick_program._gen_mgrs[ch].next_pulse
            for regs in next_pulse["regs"]:
                # Set output time to current time register
                self._qick_program.mathi(rp, rt, rl, "+", 0)
                # Set pulse registers
                self._qick_program.set(
                    ch,
                    rp,
                    *regs,
                    rt,
                    f"ch = {ch}, pulse @t = ${rt}"
                )
                # Get pulse length
                self._qick_program.bitw(rp, rtemp, rm, "&", 0xFFFF)
                # Update time register
                self._qick_program.math(rp, rl, rt, "+", rtemp)
