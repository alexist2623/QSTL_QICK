"""Boundary markers that preserve readout bits on the shared trigger port."""
from math import ceil
from dataclasses import asdict
try:
    from .qick_square_dds import OutputTriggerConfig
except ImportError:
    from qick_square_dds import OutputTriggerConfig


class OutputTriggerProgramMixin:
    def _configure_output_trigger(self):
        self.output_trigger_config=getattr(self.sequence,'output_trigger_config',OutputTriggerConfig())
        self._marker_label_count=0
        self._marker=None
        config=self.output_trigger_config
        if not config.enabled: return
        pins=self.tproccfg.get('output_pins',())
        if config.pin >= len(pins):
            raise ValueError('selected external trigger pin is absent from this firmware')
        pin=pins[config.pin]
        if pin[0] not in ('output','dport'):
            raise ValueError('external markers require a tProcessor digital output pin')
        width=ceil(config.width_us*self.tproc_mhz)
        if not 1 <= width < 2**30:
            raise ValueError('output trigger width exceeds the tProcessor timestamp range')
        self._marker=dict(port=int(pin[1]),bit=1<<int(pin[2]),width=width,name=str(pin[-1]))

    def _marker_start_enabled(self):
        return self._marker is not None and self.output_trigger_config.edge in ('start','both')

    def _marker_start_time(self):
        return int(self.timing['segment_starts'][0])

    def _marker_shared_readout_port(self):
        if not self._marker_start_enabled(): return False
        if self.ddr_readout_config is not None:
            cfg=self.soccfg['ddr4_buf']
        elif self.readout_config is not None:
            cfg=self.soccfg['readouts'][self.readout_config.ro_ch]
        else: return False
        return self._marker['port']==int(cfg['trigger_port'])

    def _marker_label(self):
        self._marker_label_count+=1
        return f'OUTPUT_MARKER_{self._marker_label_count}'

    def _emit_unshared_start_marker(self):
        if not self._marker_start_enabled() or self._marker_shared_readout_port(): return
        done=self._marker_label()
        if self.output_trigger_config.scope=='experiment':
            self.condj(0,13,'!=',0,done)
        self.trigger(pins=[self.output_trigger_config.pin],t=self._marker_start_time(),width=self._marker['width'])
        if self.output_trigger_config.scope=='experiment': self.label(done)

    def _emit_end_marker(self,scope):
        cfg=self.output_trigger_config
        if self._marker is None or cfg.scope!=scope or cfg.edge not in ('end','both'): return
        self.trigger(pins=[cfg.pin],t=0,width=self._marker['width'])
        self.synci(self._marker['width']+1,'complete external end marker')
        # Advance the timeline without blocking instruction execution here.
        # Waiting inside every repetition would discard command lookahead for
        # the next shot. make_program() waits once at the final epilogue.

    def _emit_marker_readout_trigger(self,normal_emit,*,t,width,port,bit,field_key=None,ro_ch=None):
        """Merge two pulse intervals, including a register-swept readout time.

        The shared axis_set_reg consumes a complete bit vector. Sending two
        independent trigger() calls could clear the other pulse. This emits
        their union, in timestamp order, with one event at equal boundaries.
        r0:16..20 are reserved by the sweep allocator. DMEM[0] is scratch;
        runtime tables start at 16 and spilled states never use addresses 0/1.
        """
        if not self._marker_shared_readout_port():
            normal_emit(); return
        prefix=self._marker_label()
        done=prefix+'_DONE'
        if self.output_trigger_config.scope=='experiment':
            self.condj(0,13,'==',0,prefix+'_MERGED')
            old_trigs = None if ro_ch is None else self.ro_chs[ro_ch]['trigs']
            normal_emit()
            if ro_ch is not None: self.ro_chs[ro_ch]['trigs'] = old_trigs
            self.condj(0,0,'==',0,done)
            self.label(prefix+'_MERGED')
        if ro_ch is not None:
            self.ro_chs[ro_ch]['trigs']+=1
            ro=self.soccfg['readouts'][ro_ch]
            self.set_timestamp(t+self.ro_chs[ro_ch]['length']*self.tproc_mhz/ro['f_output'],ro_ch=ro_ch)
        field=self._sweep_field_by_key.get(field_key)
        if field is None:
            self.safe_regwi(0,17,int(t),'readout trigger start')
        else:
            page=int(field['page']); reg=int(field['command_register'])
            self._write_swept_or_static_register(field_key,page,reg,int(t),'readout trigger start')
            self.memwi(page,reg,0,'transfer trigger timestamp to marker page')
            self.memri(0,17,0)
        self.mathi(0,18,17,'+',int(width),'readout trigger end')
        start = self._marker_start_time()
        self.safe_regwi(0,19,start+self._marker['width'],'external marker end')
        self.safe_regwi(0,20,start,'external marker start')
        marker=self._marker['bit']; readout=1<<int(bit)
        def edge(time_register,value):
            self.safe_regwi(0,16,value,'combined external/readout trigger bits')
            self.set(int(port),0,16,0,0,0,0,time_register,'merged trigger edge')
        # Skip a separate start edge when readout and marker begin together.
        self.condj(0,17,'==',20,prefix+'_NO_START')
        edge(20,marker)
        self.label(prefix+'_NO_START')
        self.condj(0,17,'>',19,prefix+'_AFTER')
        self.condj(0,17,'==',19,prefix+'_TOUCH')
        edge(17,marker|readout)
        self.condj(0,18,'>',19,prefix+'_STRADDLE')
        self.condj(0,18,'==',19,prefix+'_SAME_END')
        edge(18,marker)
        self.label(prefix+'_SAME_END')
        edge(19,0)
        self.condj(0,0,'==',0,done)
        self.label(prefix+'_STRADDLE')
        edge(19,readout); edge(18,0)
        self.condj(0,0,'==',0,done)
        self.label(prefix+'_AFTER')
        edge(19,0)
        self.label(prefix+'_TOUCH')
        edge(17,readout); edge(18,0)
        self.label(done)

    def _trigger_settings_metadata(self):
        if self._marker is None: return {}
        return dict(output_trigger={**asdict(self.output_trigger_config),**self._marker,
                                   'start_reference':'first AWG sequence timestamp',
                                   'end_reference':'after readout, compensation and recovery'})
