
from __future__ import annotations
import numpy as np
from typing import (
    Optional,
)
# Reg[0:7][3:11] is free.

ns = 1e-9
us = 1e-6
ms = 1e-3
s  = 1.0
GHz = 1e9
MHz = 1e6
kHz = 1e3
Hz  = 1.0

class DummyChannel:
    r"""
    Dummy channel class to allow Executor to run without generating a QICK program
    """
    def __init__(self, prog: DummyQickProgram, ch: int = 0):
        self._prog = prog
        self.next_pulse = {"regs": []}
        self.ch = ch
        self.rp = self._prog._gen_regmap[(ch, "0")][0]
        self.regmap = {}

    def set_reg(self, reg, value, defaults=None) -> None:
        self._prog.regwi(self.rp, self.regmap[(self.ch, reg)][1], value) # regwi channel, page, register, value

    def get_mode_code(self, length, mode=None, outsel=None, stdysel=None, phrst=None):
        """Creates mode code for the mode register in the set command, by setting flags and adding the pulse length.

        Parameters
        ----------
        length : int
            The number of DAC fabric cycles in the pulse
        mode : str
            Selects whether the output is "oneshot" or "periodic". The default is "oneshot".
        outsel : str
            Selects the output source. The output is complex. Tables define envelopes for I and Q.
            The default is "product".

            * If "product", the output is the product of table and DDS. 

            * If "dds", the output is the DDS only. 

            * If "input", the output is from the table for the real part, and zeros for the imaginary part. 
            
            * If "zero", the output is always zero.

        stdysel : str
            Selects what value is output continuously by the signal generator after the generation of a pulse.
            The default is "zero".

            * If "last", it is the last calculated sample of the pulse.

            * If "zero", it is a zero value.

        phrst : int
            If 1, it resets the phase coherent accumulator. The default is 0.

        Returns
        -------
        int
            Compiled mode code in binary

        """
        if mode is None: mode = "oneshot"
        if outsel is None: outsel = "product"
        if stdysel is None: stdysel = "zero"
        if phrst is None: phrst = 0
        if length >= 2**16 or length < 3:
            raise RuntimeError("Pulse length of %d is out of range (exceeds 16 bits, or less than 3) - use multiple pulses, or zero-pad the waveform" % (length))
        stdysel_reg = {"last": 0, "zero": 1}[stdysel]
        mode_reg = {"oneshot": 0, "periodic": 1}[mode]
        outsel_reg = {"product": 0, "dds": 1, "input": 2, "zero": 3}[outsel]
        mc = phrst*0b10000+stdysel_reg*0b01000+mode_reg*0b00100+outsel_reg
        return mc << 16 | int(np.uint16(length))

    def set_registers(self, params, defaults=None) -> None:
        for parname in ['freq', 'phase', 'gain']:
            if parname in params:
                self.set_reg(parname, params[parname], defaults=defaults)
        if 'waveform' in params:
            pinfo = self.envelopes[params['waveform']]
            wfm_length = pinfo['data'].shape[0] // self.gencfg['samps_per_clk']
            addr = pinfo['addr'] // self.gencfg['samps_per_clk']
            self.set_reg('addr', addr, defaults=defaults)

        style = params['style']
        # these mode bits could be defined, or left as None
        phrst, stdysel, mode, outsel = [params.get(x) for x in ['phrst', 'stdysel', 'mode', 'outsel']]

        self.next_pulse = {}
        self.next_pulse['rp'] = self.rp
        self.next_pulse['regs'] = []
        if style=='const':
            mc = self.get_mode_code(phrst=phrst, stdysel=stdysel, mode=mode, outsel="dds", length=params['length'])
            self.set_reg('mode', mc, f'phrst| stdysel | mode | | outsel = 0b{mc//2**16:>05b} | length = {mc % 2**16} ')
            self.next_pulse['regs'].append([self.regmap[(self.ch,x)][1] for x in ['freq', 'phase', '0', 'gain', 'mode']])
            self.next_pulse['length'] = params['length']
        elif style=='arb':
            mc = self.get_mode_code(phrst=phrst, stdysel=stdysel, mode=mode, outsel=outsel, length=wfm_length)
            self.set_reg('mode', mc, f'phrst| stdysel | mode | | outsel = 0b{mc//2**16:>05b} | length = {mc % 2**16} ')
            self.next_pulse['regs'].append([self.regmap[(self.ch,x)][1] for x in ['freq', 'phase', 'addr', 'gain', 'mode']])
            self.next_pulse['length'] = wfm_length
        elif style=='flat_top':
            # address for ramp-down
            self.set_reg('addr2', addr+(wfm_length+1)//2)
            # gain for flat segment
            self.set_reg('gain2', params['gain']//2)
            # mode for ramp up
            mc = self.get_mode_code(phrst=phrst, stdysel=stdysel, mode='oneshot', outsel='product', length=wfm_length//2)
            self.set_reg('mode2', mc, f'phrst| stdysel | mode | | outsel = 0b{mc//2**16:>05b} | length = {mc % 2**16} ')
            # mode for flat segment
            mc = self.get_mode_code(phrst=False, stdysel=stdysel, mode='oneshot', outsel='dds', length=params['length'])
            self.set_reg('mode', mc, f'phrst| stdysel | mode | | outsel = 0b{mc//2**16:>05b} | length = {mc % 2**16} ')
            # mode for ramp down
            mc = self.get_mode_code(phrst=False, stdysel=stdysel, mode='oneshot', outsel='product', length=wfm_length//2)
            self.set_reg('mode3', mc, f'phrst| stdysel | mode | | outsel = 0b{mc//2**16:>05b} | length = {mc % 2**16} ')

            self.next_pulse['regs'].append([self.regmap[(self.ch,x)][1] for x in ['freq', 'phase', 'addr', 'gain', 'mode2']])
            self.next_pulse['regs'].append([self.regmap[(self.ch,x)][1] for x in ['freq', 'phase', '0', 'gain2', 'mode']])
            self.next_pulse['regs'].append([self.regmap[(self.ch,x)][1] for x in ['freq', 'phase', 'addr2', 'gain', 'mode3']])
            self.next_pulse['length'] = (wfm_length//2)*2 + params['length']

class DummyQickProgram:
    r"""
    Dummy QICK program class to allow Executor to run without generating a QICK program
    """
    instructions = {'pushi': {'type': "I", 'bin': 0b00010000, 'fmt': ((0, 53), (1, 41), (2, 36), (3, 0)), 'repr': "{0}, ${1}, ${2}, {3}"},
                    'popi':  {'type': "I", 'bin': 0b00010001, 'fmt': ((0, 53), (1, 41)), 'repr': "{0}, ${1}"},
                    'mathi': {'type': "I", 'bin': 0b00010010, 'fmt': ((0, 53), (1, 41), (2, 36), (3, 46), (4, 0)), 'repr': "{0}, ${1}, ${2} {3} {4}"},
                    'seti':  {'type': "I", 'bin': 0b00010011, 'fmt': ((1, 53), (0, 50), (2, 36), (3, 0)), 'repr': "{0}, {1}, ${2}, {3}"},
                    'synci': {'type': "I", 'bin': 0b00010100, 'fmt': ((0, 0),), 'repr': "{0}"},
                    'waiti': {'type': "I", 'bin': 0b00010101, 'fmt': ((0, 50), (1, 0)), 'repr': "{0}, {1}"},
                    'bitwi': {'type': "I", 'bin': 0b00010110, 'fmt': ((0, 53), (3, 46), (1, 41), (2, 36), (4, 0)), 'repr': "{0}, ${1}, ${2} {3} {4}"},
                    'memri': {'type': "I", 'bin': 0b00010111, 'fmt': ((0, 53), (1, 41), (2, 0)), 'repr': "{0}, ${1}, {2}"},
                    'memwi': {'type': "I", 'bin': 0b00011000, 'fmt': ((0, 53), (1, 31), (2, 0)), 'repr': "{0}, ${1}, {2}"},
                    'regwi': {'type': "I", 'bin': 0b00011001, 'fmt': ((0, 53), (1, 41), (2, 0)), 'repr': "{0}, ${1}, {2}"},
                    'setbi': {'type': "I", 'bin': 0b00011010, 'fmt': ((0, 53), (1, 41), (2, 0)), 'repr': "{0}, ${1}, {2}"},

                    'loopnz': {'type': "J1", 'bin': 0b00110000, 'fmt': ((0, 53), (1, 41), (1, 36), (2, 0)), 'repr': "{0}, ${1}, @{2}"},
                    'end':    {'type': "J1", 'bin': 0b00111111, 'fmt': (), 'repr': ""},

                    'condj':  {'type': "J2", 'bin': 0b00110001, 'fmt': ((0, 53), (2, 46), (1, 36), (3, 31), (4, 0)), 'repr': "{0}, ${1}, {2}, ${3}, @{4}"},

                    'math':  {'type': "R", 'bin': 0b01010000, 'fmt': ((0, 53), (3, 46), (1, 41), (2, 36), (4, 31)), 'repr': "{0}, ${1}, ${2} {3} ${4}"},
                    'set':  {'type': "R", 'bin': 0b01010001, 'fmt': ((1, 53), (0, 50), (2, 36), (7, 31), (3, 26), (4, 21), (5, 16), (6, 11)), 'repr': "{0}, {1}, ${2}, ${3}, ${4}, ${5}, ${6}, ${7}"},
                    'sync': {'type': "R", 'bin': 0b01010010, 'fmt': ((0, 53), (1, 31)), 'repr': "{0}, ${1}"},
                    'read': {'type': "R", 'bin': 0b01010011, 'fmt': ((1, 53), (0, 50), (2, 46), (3, 41)), 'repr': "{0}, {1}, {2} ${3}"},
                    'wait': {'type': "R", 'bin': 0b01010100, 'fmt': ((1, 53), (0, 50), (2, 31)), 'repr': "{0}, {1}, ${2}"},
                    'bitw': {'type': "R", 'bin': 0b01010101, 'fmt': ((0, 53), (1, 41), (2, 36), (3, 46), (4, 31)), 'repr': "{0}, ${1}, ${2} {3} ${4}"},
                    'memr': {'type': "R", 'bin': 0b01010110, 'fmt': ((0, 53), (1, 41), (2, 36)), 'repr': "{0}, ${1}, ${2}"},
                    'memw': {'type': "R", 'bin': 0b01010111, 'fmt': ((0, 53), (2, 36), (1, 31)), 'repr': "{0}, ${1}, ${2}"},
                    'setb': {'type': "R", 'bin': 0b01011000, 'fmt': ((0, 53), (2, 36), (1, 31)), 'repr': "{0}, ${1}, ${2}"},
                    'comment': {'fmt': ()}
                    }

    # op codes for math and bitwise operations
    op_codes = {">": 0b0000, ">=": 0b0001, "<": 0b0010, "<=": 0b0011, "==": 0b0100, "!=": 0b0101,
                "+": 0b1000, "-": 0b1001, "*": 0b1010,
                "&": 0b0000, "|": 0b0001, "^": 0b0010, "~": 0b0011, "<<": 0b0100, ">>": 0b0101,
                "upper": 0b1010, "lower": 0b0101
                }
    def __init__(self):
        self._dac_sample_rate = 400 * MHz
        self._adc_sample_rate = 300 * MHz
        self._gen_regmap = {
            (x, "0"): (x + 2, 0) for x in range(8)
        }
        self._gen_regmap.update({
            (x, "freq"): (x + 2, 21) for x in range(8)
        })
        self._gen_regmap.update({
            (x, "phase"): (x + 2, 22) for x in range(8)
        })
        self._gen_regmap.update({
            (x, "gain"): (x + 2, 23) for x in range(8)
        })
        self._gen_regmap.update({
            (x, "mode"): (x + 2, 24) for x in range(8)
        })
        self._gen_regmap.update({
            (x, "addr"): (x + 2, 25) for x in range(8)
        })
        self._gen_regmap.update({
            (x, "addr2"): (x + 2, 26) for x in range(8)
        })
        self._gen_regmap.update({
            (x, "gain2"): (x + 2, 27) for x in range(8)
        })
        self._gen_regmap.update({
            (x, "mode2"): (x + 2, 28) for x in range(8)
        })
        self._gen_regmap.update({
            (x, "mode3"): (x + 2, 29) for x in range(8)
        })
        self._gen_regmap.update({
            (x, "t"): (x + 2, 30) for x in range(8)
        })

        self._gen_mgrs = [DummyChannel(self, ch) for ch in range(8)]
        self._ro_mgrs = [DummyChannel(self, ch) for ch in range(8)]

        for ch in range(8):
            self._gen_mgrs[ch].regmap.update(self._gen_regmap)
        self._label_next = None
        self.prog_list = []

    def append_instruction(self, name, *args):
        """Append instruction to the program list

        Parameters
        ----------
        name : str
            Instruction name
        *args : dict
            Instruction arguments
        """
        n_args = max([f[0] for f in self.instructions[name]['fmt']]+[-1])+1
        if len(args)==n_args:
            inst = {'name': name, 'args': args}
        elif len(args)==n_args+1:
            inst = {'name': name, 'args': args[:n_args], 'comment': args[n_args]}
        else:
            raise RuntimeError("wrong number of args:", name, args)
        if self._label_next is not None:
            # store the label with the instruction, for printing
            inst['label'] = self._label_next
            self._label_next = None
        self.prog_list.append(inst)
    
    def us2cycles(self, value: float, gen_ch: Optional[int] = None, ro_ch: Optional[int] = None) -> int:
        r"""
        Convert microseconds to QICK clock cycles
        """
        return int(value * 1e-6 * self._dac_sample_rate)

    def freq2reg(self, value: float, gen_ch: Optional[int] = None, ro_ch: Optional[int] = None) -> int:
        r"""
        Convert frequency in Hz to QICK frequency register value
        """
        return int((value / self._dac_sample_rate) * (2**32)) & 0xFFFFFFFF

    def deg2reg(self, value: float, gen_ch: Optional[int] = None, ro_ch: Optional[int] = None) -> int:
        r"""
        Convert phase in degrees to QICK phase register value
        """
        return int((value % 360) / 360 * (2**16)) & 0xFFFF

    def set_pulse_registers(
        self,
        ch: int,
        **kwargs
    ) -> None:
        r"""
        Set pulse registers for a given channel
        """
        self._gen_mgrs[ch].set_registers(kwargs)

    def _inst2asm(self, inst, max_label_len):
        if inst['name']=='comment':
            return "// "+inst['comment']
        template = inst['name'] + " " + self.__class__.instructions[inst['name']]['repr'] + ";"
        line = " "*(max_label_len+2) + template.format(*inst['args'])
        if 'comment' in inst:
            line += " "*(48-len(line)) + "//" + (inst['comment'] if inst['comment'] is not None else "")
        if 'label' in inst:
            label = inst['label']
            line = label + ": " + line[len(label)+2:]
        return line

    def asm(self):
        """Returns assembly representation of program as string, should be compatible with the parse_prog from the parser module.

        Returns
        -------
        str
            asm file
        """
        label_list = [inst['label'] for inst in self.prog_list if 'label' in inst]
        if label_list:
            max_label_len = max([len(label) for label in label_list])
        else:
            max_label_len = 0
        s = "\n// Program\n\n"
        lines = [self._inst2asm(inst, max_label_len) for inst in self.prog_list]
        return s+"\n".join(lines)

    def __getattr__(self, a):
        """
        Uses instructions dictionary to automatically generate methods for the standard instruction set.

        Also include all QickConfig methods as methods of the QickProgram.
        This allows e.g. this.freq2reg(f) instead of this.soccfg.freq2reg(f).

        :param a: Instruction name
        :type a: str
        :return: Instruction arguments
        :rtype: *args object
        """
        if a in self.__class__.instructions:
            return lambda *args: self.append_instruction(a, *args)
        else:
            return object.__getattribute__(self, a)

    def __str__(self):
        """
        Print as assembly by default.

        :return: The asm file associated with the class
        :rtype: str
        """
        return self.asm()

    def __repr__(self):
        """
        Print as assembly by default.

        :return: The asm file associated with the class
        :rtype: str
        """
        return self.asm()

    def __len__(self):
        """
        :return: number of instructions in the program
        :rtype: int
        """
        return len(self.prog_list)

    def __enter__(self):
        """
        Enter the runtime context related to this object.

        :return: self
        :rtype: self
        """
        return self

    def __exit__(self, type, value, traceback):
        """
        Exit the runtime context related to this object.

        :param type: type of error
        :type type: type
        :param value: value of error
        :type value: int
        :param traceback: traceback of error
        :type traceback: str
        """
        pass