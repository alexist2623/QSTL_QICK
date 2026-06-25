"""Hardware-free QICK simulator built from a bit/HWH pair."""

import os
from collections import defaultdict

import numpy as np

from .virtual_hw import SimDMA, SimDummyIP, SimRFdc, install_pynq_stubs
from .models import (
    AxisAvgBufferV13BehaviorModel,
    AxisAwgTuningBehaviorModel,
    AxisDynReadoutV1BehaviorModel,
    RfdcDacSinkModel,
    AxisSignalGenV6BehaviorModel,
    AxisTmuxV1BehaviorModel,
)
from .results import SimulationResult
from .topology import SimHwhParser, build_ip_dict, locate_hwh
from .tproc_v1 import TProcV1Sim

install_pynq_stubs()

from qick.awg_tuning import AxisAwgTuningV1, TimedCommandEvent  # noqa: E402
from qick.drivers.generator import AbsPulsedSignalGen, AxisConstantIQ, AxisSignalGen  # noqa: E402
from qick.drivers.readout import AbsReadout, AxisAvgBuffer, AxisBufferDdrV1, MrBufferEt  # noqa: E402
from qick import get_version  # noqa: E402
from qick.ip import QickMetadata  # noqa: E402
from qick.qick_asm import QickConfig  # noqa: E402


class QickSim(QickConfig):
    """Simulation-side subset of ``QickSoc``.

    ``QickSim`` parses an HWH file, instantiates fake-backed QICK IP drivers,
    reuses normal connection discovery, and executes compiled ASM v1 programs
    through Python behavior models. It never downloads a bitstream or touches
    PYNQ hardware APIs.
    """

    def __init__(self, bitfile, *, hwhfile=None, rf_config=None, clocks=None,
                 dac_clk=None, adc_clk=None, fabric_clk=None, tproc_clk=None,
                 strict=True, board=None, **kwargs):
        bitpath, hwhpath = locate_hwh(bitfile, hwhfile)
        self.bitfile = str(bitpath)
        self.hwhfile = str(hwhpath)
        self.strict = bool(strict)
        self.parser = SimHwhParser(hwhpath)
        self.ip_dict, self.unmatched_ips = build_ip_dict(self.parser.root, strict=strict)
        self.clock_config = self._normalize_clocks(
            clocks=clocks,
            dac_clk=dac_clk,
            adc_clk=adc_clk,
            fabric_clk=fabric_clk,
            tproc_clk=tproc_clk,
        )
        rf_config = self._rf_config_from_clocks(rf_config, self.clock_config)

        self._cfg = {
            "board": board or os.getenv("BOARD", "SIM"),
            "sw_version": get_version(),
            "fw_timestamp": self.parser.root.get("TIMESTAMP", "unknown"),
            "extra_description": [
                "QickSim is hardware-free and uses user-configurable MHz clocks.",
                "RFDC-facing samples are digital AXIS words, not analog RFDC output.",
            ],
        }
        self.metadata = QickMetadata(self)

        self._blocks = {}
        self._instantiate_blocks(rf_config=rf_config)

        self.gens = []
        self.awg_tunings = []
        self.iqs = []
        self.avg_bufs = []
        self.readouts = []

        self.rf = self._find_or_create_rf(rf_config)
        self["rf"] = self.rf.cfg
        self._tproc = self._find_or_create_tproc()
        self.TPROC_VERSION = 1 if self._tproc is not None else 0
        self._apply_tproc_clock()

        self.map_signal_paths()
        self._apply_tproc_clock()
        self["tprocs"] = [self.tproc.cfg] if self.tproc is not None else []

    @staticmethod
    def _compute_ratio(fs, fabric, default=1):
        if fs is None or fabric in (None, 0):
            return int(default)
        return max(1, int(round(float(fs) / float(fabric))))

    @classmethod
    def _normalize_clocks(cls, clocks=None, dac_clk=None, adc_clk=None, fabric_clk=None, tproc_clk=None):
        """Normalize user clock settings. All frequencies are in MHz."""
        clocks = {} if clocks is None else dict(clocks)
        default_dac = dict(clocks.get("default_dac", {}))
        default_adc = dict(clocks.get("default_adc", {}))
        if dac_clk is not None:
            default_dac["fs"] = float(dac_clk)
        if adc_clk is not None:
            default_adc["fs"] = float(adc_clk)
        if fabric_clk is not None:
            default_dac["fabric"] = float(fabric_clk)
            default_adc["fabric"] = float(fabric_clk)
        default_dac.setdefault("fs", 300.0)
        default_dac.setdefault("fabric", 300.0)
        default_dac.setdefault("interpolation", cls._compute_ratio(default_dac["fs"], default_dac["fabric"], 1))
        default_adc.setdefault("fs", 300.0)
        default_adc.setdefault("fabric", 300.0 if fabric_clk is None else float(fabric_clk))
        default_adc.setdefault("decimation", cls._compute_ratio(default_adc["fs"], default_adc["fabric"], 1))

        dac_overrides = {str(k): dict(v) for k, v in dict(clocks.get("dac", {})).items()}
        adc_overrides = {str(k): dict(v) for k, v in dict(clocks.get("adc", {})).items()}
        tproc = float(tproc_clk if tproc_clk is not None else clocks.get("tproc", 300.0))
        return {
            "tproc": tproc,
            "default_dac": default_dac,
            "default_adc": default_adc,
            "dac": dac_overrides,
            "adc": adc_overrides,
        }

    @classmethod
    def _dac_cfg_from_clock(cls, base, override=None):
        cfg = dict(base)
        if override:
            cfg.update(override)
        fs = float(cfg.get("fs", 300.0))
        fabric = float(cfg.get("fabric", cfg.get("f_fabric", 300.0)))
        interpolation = int(cfg.get("interpolation", cls._compute_ratio(fs, fabric, 1)))
        fs_div = int(cfg.get("fs_div", 1))
        return {
            "fs": fs,
            "fs_mult": int(cfg.get("fs_mult", 1)),
            "fs_div": fs_div,
            "interpolation": interpolation,
            "f_fabric": fabric,
            "f_dds": fs / max(1, interpolation),
            "fdds_div": fs_div * max(1, interpolation),
        }

    @classmethod
    def _adc_cfg_from_clock(cls, base, override=None):
        cfg = dict(base)
        if override:
            cfg.update(override)
        fs = float(cfg.get("fs", 300.0))
        fabric = float(cfg.get("fabric", cfg.get("f_fabric", 300.0)))
        decimation = int(cfg.get("decimation", cls._compute_ratio(fs, fabric, 1)))
        return {
            "fs": fs,
            "fs_mult": int(cfg.get("fs_mult", 1)),
            "fs_div": int(cfg.get("fs_div", 1)),
            "decimation": decimation,
            "f_fabric": fabric,
            "f_output": fs / max(1, decimation),
            "coupling": cfg.get("coupling", "DC"),
        }

    @classmethod
    def _rf_config_from_clocks(cls, rf_config, clock_config):
        cfg = {} if rf_config is None else dict(rf_config)
        dac_names = ["00", "01", "02", "03", "10", "11", "12", "13", "20", "21", "22", "23", "30", "31", "32", "33"]
        adc_names = list(dac_names)
        dacs = {
            name: cls._dac_cfg_from_clock(clock_config["default_dac"], clock_config["dac"].get(name))
            for name in dac_names
        }
        adcs = {
            name: cls._adc_cfg_from_clock(clock_config["default_adc"], clock_config["adc"].get(name))
            for name in adc_names
        }
        cfg.setdefault("dacs", {}).update(dacs)
        cfg.setdefault("adcs", {}).update(adcs)
        cfg.setdefault("clk_groups", [[("tproc", 0)], [("dac", 0)], [("adc", 0)]])
        return cfg

    def _apply_tproc_clock(self):
        if self._tproc is not None:
            self._tproc.cfg["f_time"] = float(self.clock_config["tproc"])

    @property
    def tproc(self):
        return self._tproc

    def _describe_dac(self, dacname):
        if self["board"] == "SIM":
            tile, block = [int(c) for c in dacname]
            return "DAC tile %d, blk %d is simulated RFDC DAC %s" % (tile, block, dacname)
        return super()._describe_dac(dacname)

    def _describe_adc(self, adcname):
        if self["board"] == "SIM":
            tile, block = [int(c) for c in adcname]
            return "ADC tile %d, blk %d is simulated RFDC ADC %s" % (tile, block, adcname)
        return super()._describe_adc(adcname)

    def _instantiate_blocks(self, rf_config=None):
        for fullpath, desc in self.ip_dict.items():
            driver = desc["driver"]
            if driver is SimRFdc:
                block = driver(desc, rf_config=rf_config)
            else:
                block = driver(desc)
            self._blocks[fullpath] = block
            self._set_block_attr(fullpath, block)

    def _set_block_attr(self, fullpath, block):
        obj = self
        parts = fullpath.split("/")
        for part in parts[:-1]:
            if not hasattr(obj, part):
                holder = type("SimHierarchy", (), {})()
                setattr(obj, part, holder)
            obj = getattr(obj, part)
        setattr(obj, parts[-1], block)

    def _get_block(self, fullpath):
        if fullpath in self._blocks:
            return self._blocks[fullpath]
        block = self
        for part in fullpath.split("/"):
            block = getattr(block, part)
        return block

    def _find_or_create_rf(self, rf_config=None):
        for fullpath, desc in self.ip_dict.items():
            if desc["driver"] is SimRFdc or "usp_rf_data_converter" in desc["type"]:
                block = self._get_block(fullpath)
                if not isinstance(block, SimRFdc):
                    block = SimRFdc(desc, rf_config=rf_config)
                    self._blocks[fullpath] = block
                    self._set_block_attr(fullpath, block)
                return block
        desc = {
            "fullpath": "usp_rf_data_converter_0",
            "type": "xilinx.com:ip:usp_rf_data_converter:2.6",
            "parameters": {},
            "driver": SimRFdc,
        }
        self.ip_dict[desc["fullpath"]] = desc
        block = SimRFdc(desc, rf_config=rf_config)
        self._blocks[desc["fullpath"]] = block
        self._set_block_attr(desc["fullpath"], block)
        return block

    def _find_or_create_tproc(self):
        if "axis_tproc64x32_x8_0" in self.ip_dict:
            tproc = self._get_block("axis_tproc64x32_x8_0")
            mem = self._blocks.get("axi_bram_ctrl_0", SimDummyIP({
                "fullpath": "axi_bram_ctrl_0",
                "type": "xilinx.com:ip:axi_bram_ctrl:4.1",
                "parameters": {},
            }))
            dma = self._blocks.get("axi_dma_tproc", SimDMA({
                "fullpath": "axi_dma_tproc",
                "type": "xilinx.com:ip:axi_dma:7.1",
                "parameters": {},
            }))
            if hasattr(tproc, "configure"):
                tproc.configure(mem, dma)
            return tproc
        return None

    def map_signal_paths(self):
        """Reuse the real ``QickSoc.map_signal_paths`` discovery behavior."""
        for key, val in self.ip_dict.items():
            if hasattr(val["driver"], "configure_connections"):
                self._get_block(val["fullpath"]).configure_connections(self)

        ddr4_buf = []
        mr_buf = []
        for key, val in self.ip_dict.items():
            driver = val["driver"]
            if issubclass(driver, AbsPulsedSignalGen):
                block = self._get_block(key)
                self.gens.append(block)
                if isinstance(block, AxisAwgTuningV1):
                    self.awg_tunings.append(block)
            elif driver == AxisConstantIQ:
                self.iqs.append(self._get_block(key))
            elif issubclass(driver, AbsReadout):
                self.readouts.append(self._get_block(key))
            elif issubclass(driver, AxisAvgBuffer):
                self.avg_bufs.append(self._get_block(key))
            elif issubclass(driver, AxisBufferDdrV1):
                ddr4_buf.append(self._get_block(key))
            elif issubclass(driver, MrBufferEt):
                mr_buf.append(self._get_block(key))

        for buf in self.avg_bufs:
            if hasattr(buf, "readout") and buf.readout not in self.readouts:
                self.readouts.append(buf.readout)

        self.gens.sort(key=lambda x: (x["tproc_ch"], x._cfg.get("tmux_ch")))
        self.avg_bufs.sort(key=lambda x: x.switch_ch if x.switch_ch is not None else -1)
        self.iqs.sort(key=lambda x: x["dac"])
        self.readouts.sort(key=lambda x: x["adc"])

        for i, gen in enumerate(self.gens):
            gen.configure(i, self.rf)
        for i, iq in enumerate(self.iqs):
            iq.configure(i, self.rf)
        for readout in self.readouts:
            readout.configure(self.rf)

        if len(mr_buf) == 1:
            self.mr_buf = mr_buf[0]
            self["mr_buf"] = self.mr_buf.cfg
        if len(ddr4_buf) == 1:
            self.ddr4_buf = ddr4_buf[0]
            self["ddr4_buf"] = self.ddr4_buf.cfg

        self["gens"] = [gen.cfg for gen in self.gens]
        self["awg_tunings"] = [awg.cfg for awg in self.awg_tunings]
        self["iqs"] = [iq.cfg for iq in self.iqs]
        self["avg_bufs"] = [buf.cfg for buf in self.avg_bufs]
        self["readouts"] = [self._readout_cfg(buf) for buf in self.avg_bufs] or [ro.cfg for ro in self.readouts]
        self["tprocs"] = [self.tproc.cfg] if self.tproc is not None else []

    @staticmethod
    def _readout_cfg(buf):
        if not hasattr(buf, "readout"):
            return buf.cfg
        bufcfg = buf.cfg
        rocfg = buf.readout.cfg
        merged = {**bufcfg, **rocfg}
        for key in set(bufcfg) & set(rocfg):
            del merged[key]
            merged["avgbuf_" + key] = bufcfg[key]
            merged["ro_" + key] = rocfg[key]
        return merged

    def _program_instructions(self, program):
        if isinstance(program, (list, tuple)):
            return list(program)
        for attr in ("prog_list", "program"):
            if hasattr(program, attr):
                value = getattr(program, attr)
                if value is not None:
                    return list(value)
        if hasattr(program, "compile"):
            program.compile()
            for attr in ("prog_list", "program"):
                if hasattr(program, attr):
                    value = getattr(program, attr)
                    if value is not None:
                        return list(value)
        raise ValueError("program object does not expose compiled ASM v1 instructions")

    def simulate_program(self, program, *, cycles=None, strict=None):
        """Execute a compiled QickProgram/AveragerProgram-like object."""
        instructions = self._program_instructions(program)
        return self.simulate_tproc_instructions(instructions, cycles=cycles, strict=strict)

    def simulate_tproc_instructions(self, instructions, *, cycles=None, strict=None):
        """Run ASM v1 instructions through the tProc simulator."""
        tproc = TProcV1Sim(strict=self.strict if strict is None else strict)
        tproc.run(instructions)
        return self.simulate_events(tproc.output_events, cycles=cycles, tproc=tproc)

    @staticmethod
    def _signal_gen_memory_from_dma(gen):
        words = []
        dma = getattr(gen, "dma", None)
        send = getattr(dma, "sendchannel", None)
        for transfer in getattr(send, "transfers", []):
            words.extend(int(x) for x in np.asarray(transfer).reshape(-1))
        return words

    def _model_for_gen(self, gen, idx):
        n_pts = int(gen.cfg.get("n_pts", gen.cfg.get("samps_per_clk", 16)))
        if isinstance(gen, AxisSignalGen):
            n_pts = int(gen.description.get("parameters", {}).get("N_DDS", n_pts))
        params = {
            "n_pts": n_pts,
            "b": int(gen.cfg.get("b", 16)),
        }
        if isinstance(gen, AxisAwgTuningV1):
            return AxisAwgTuningBehaviorModel(
                n_pts=params["n_pts"],
                b=params["b"],
                extra_y_pipe_stages=int(gen.cfg.get("extra_y_pipe_stages", 1)),
                channel=idx,
            )
        if isinstance(gen, AxisSignalGen):
            model = AxisSignalGenV6BehaviorModel(
                n_dds=params["n_pts"],
                b=params["b"],
                strict=self.strict,
                latency=int(gen.cfg.get("sim_latency_cycles", 0)),
                name=gen.cfg.get("fullpath", "axis_signal_gen_v6"),
                channel=idx,
            )
            memory = self._signal_gen_memory_from_dma(gen)
            if memory:
                model.load_memory(memory, addr=0)
            return model
        return None

    def _output_metadata_for_gen(self, gen, idx):
        fullpath = gen.cfg.get("fullpath", "gen%d" % idx)
        dac = str(gen.cfg.get("dac", "unknown"))
        n_lanes = int(gen.cfg.get("n_pts", gen.cfg.get("samps_per_clk", 16)))
        if isinstance(gen, AxisSignalGen):
            n_lanes = int(gen.description.get("parameters", {}).get("N_DDS", n_lanes))
        bits = int(gen.cfg.get("b", 16))
        daccfg = self["rf"]["dacs"].get(dac, {})
        metadata = {
            "gen_index": idx,
            "tproc_ch": gen.cfg.get("tproc_ch"),
            "tmux_ch": gen.cfg.get("tmux_ch"),
            "packed_width": n_lanes * bits,
            "n_lanes": n_lanes,
            "bits": bits,
            "sample_rate_mhz": daccfg.get("fs", gen.cfg.get("fs")),
            "fabric_clk_mhz": daccfg.get("f_fabric", gen.cfg.get("f_fabric")),
        }
        if isinstance(gen, AxisSignalGen):
            metadata["dds_model"] = "deterministic approximation; not bit-exact DDS Compiler output"
        if isinstance(gen, AxisAwgTuningV1):
            metadata["awg_model"] = "follows axis_awg_tuning_v1 command semantics"
        return {
            "name": fullpath,
            "dac": dac,
            "source_path": fullpath,
            "source_type": gen.cfg.get("type", type(gen).__name__),
            "n_lanes": n_lanes,
            "bits": bits,
            "dac_fs_mhz": float(daccfg.get("fs", gen.cfg.get("fs", 300.0))),
            "fabric_clk_mhz": float(daccfg.get("f_fabric", gen.cfg.get("f_fabric", 300.0))),
            "tproc_clk_mhz": float(self.clock_config["tproc"]),
            "metadata": metadata,
        }

    def _make_rfdc_output(self, gen, idx, model, model_result):
        meta = self._output_metadata_for_gen(gen, idx)
        valid = None
        if hasattr(model, "_valid_cycles"):
            valid = np.array([cycle in model._valid_cycles for cycle in range(len(model_result.packed_words))], dtype=bool)
        sink = RfdcDacSinkModel(**meta)
        return sink.collect(model_result.packed_words, tvalid=valid)

    def _event_to_gen_fabric_clock(self, event, gen):
        tproc_clk = float(self.clock_config["tproc"])
        fabric_clk = float(gen.cfg.get("f_fabric", tproc_clk))
        if tproc_clk <= 0:
            scale = 1.0
        else:
            scale = fabric_clk / tproc_clk
        source_cycle = event.source_cycle if event.source_cycle is not None else event.cycle
        return TimedCommandEvent(
            cycle=int(round(int(event.cycle) * scale)),
            word=int(event.word),
            channel=event.channel,
            tproc_ch=event.tproc_ch,
            tmux_ch=event.tmux_ch,
            label=event.label,
            source_cycle=int(round(int(source_cycle) * scale)),
            route_latency=event.route_latency,
        )

    def _route_to_gens(self, events):
        by_gen = defaultdict(list)
        tmux = AxisTmuxV1BehaviorModel()
        for event in events:
            for idx, gen in enumerate(self.gens):
                if event.tproc_ch is not None and int(event.tproc_ch) != int(gen.cfg.get("tproc_ch", -999)):
                    continue
                tmux_ch = gen.cfg.get("tmux_ch")
                routed = self._event_to_gen_fabric_clock(event, gen)
                if tmux_ch is not None:
                    select = (int(routed.word) >> 152) & 0xFF
                    if select != int(tmux_ch):
                        continue
                    routed = tmux.route(routed)
                    routed.channel = idx
                else:
                    routed = TimedCommandEvent(
                        cycle=int(routed.cycle),
                        word=int(routed.word),
                        channel=idx,
                        tproc_ch=routed.tproc_ch,
                        tmux_ch=None,
                        label=routed.label,
                        source_cycle=routed.source_cycle,
                        route_latency=routed.route_latency,
                    )
                by_gen[idx].append(routed)
        return by_gen

    def simulate_events(self, events, *, cycles=None, tproc=None):
        """Simulate already-timed tProcessor output events."""
        events = list(events)
        if cycles is None:
            cycles = max([event.cycle for event in events], default=0) + 64
        cycles = int(cycles)

        routed = self._route_to_gens(events)
        packed_by_name = {}
        lanes_by_name = {}
        outputs = {}
        command_events = []
        accepted_commands = []
        dropped_commands = []
        timing_conflicts = []
        unsupported_modes = []

        for idx, gen in enumerate(self.gens):
            model = self._model_for_gen(gen, idx)
            if model is None:
                continue
            result = model.run(cycles, routed.get(idx, []))
            name = f"gen{idx}"
            packed_by_name[name] = result.packed_words
            lanes_by_name[name] = result.lane_samples
            output = self._make_rfdc_output(gen, idx, model, result)
            outputs[output.name] = output
            command_events.extend(result.command_events)
            accepted_commands.extend(result.accepted_commands)
            dropped_commands.extend(result.dropped_commands)
            timing_conflicts.extend(result.timing_conflicts)
            unsupported_modes.extend(result.unsupported_modes)

        readout_data = {}
        for idx, readout in enumerate(self.readouts):
            model = AxisDynReadoutV1BehaviorModel(name=f"readout{idx}")
            readout_data[f"readout{idx}"] = model.captured

        avg_data = {}
        for idx, _buf in enumerate(self.avg_bufs):
            model = AxisAvgBufferV13BehaviorModel(name=f"avg_buffer{idx}")
            avg_data[f"avg_buffer{idx}"] = {
                "raw_buffer": model.raw_buffer,
                "avg_memory": model.avg_memory,
                "feedback_events": model.feedback_events,
            }

        ordered_gen_names = sorted(
            packed_by_name,
            key=lambda name: int(name[3:]) if name.startswith("gen") and name[3:].isdigit() else name,
        )
        if ordered_gen_names:
            packed_words = np.stack([packed_by_name[name] for name in ordered_gen_names], axis=1).astype(object)
            lane_samples = np.stack([lanes_by_name[name] for name in ordered_gen_names], axis=1)
        else:
            packed_words = np.array([], dtype=object)
            lane_samples = np.array([], dtype=np.int64)

        result = SimulationResult(
            packed_words=packed_words,
            lane_samples=lane_samples,
            command_events=command_events,
            accepted_commands=accepted_commands,
            dropped_commands=dropped_commands,
            timing_conflicts=timing_conflicts,
            unsupported_ips=list(self.unmatched_ips) if not self.strict else [],
            unsupported_instructions=[] if tproc is None else list(tproc.unsupported_instructions),
            unsupported_modes=unsupported_modes,
            channel_results={
                "packed_words": packed_by_name,
                "lane_samples": lanes_by_name,
                "readouts": readout_data,
                "avg_buffers": avg_data,
                "outputs": outputs,
            },
            outputs=outputs,
            metadata={
                "bitfile": self.bitfile,
                "hwhfile": self.hwhfile,
                "clocks": self.clock_config,
                "output_names": list(outputs),
            },
        )
        return result


__all__ = ["QickSim"]
