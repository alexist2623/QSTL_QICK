"""Quantify the preserved constant-increment policy separately from RTL pass/fail.

The historical 20 mV fixed-voltage example predates the minimum SET guard and
is now rejected. Use the default 0.1 mV for a supported current-software grid;
write to a new output directory to preserve the historical report evidence.
"""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--gui',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--dc-voltage-mv',type=float,default=.1,
                        help='Fixed compensation magnitude in mV; 20 mV is rejected by the SET-spacing guard.')
    args=parser.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(args.gui/'DCWaveformGeneratorGUI'))
    from qick.sim import QickSim  # noqa
    from qick_fine_tune_sweep import FineTuneSequence
    from test_incremental_virtual_grid import firmware, MATRIX, SCALES
    reports=[]
    for mode in ('fixed_time','fixed_voltage'):
        seq=FineTuneSequence(('x','y'))
        seq.set_cross_capacitance(MATRIX);seq.set_voltage_scales(800.,SCALES)
        seq.add_set('gate',(0.,0.),300)
        seq.add_ramp('return',30).add_set('zero',(0.,0.),500)
        seq.add_amplitude_sweep('gate','x',5/800,15/800,200)
        seq.add_amplitude_sweep('gate','y',-9/800,7/800,200)
        seq.set_bias_t_compensation(args.dc_voltage_mv/800.,mode=mode,
            fixed_duration_cycles=600 if mode=='fixed_time' else None)
        seq.set_rc_compensation(300.)
        p=seq.make_program(firmware(),awg_channels=(0,1),compile_validation_mode='boundary')
        fig,axs=plt.subplots(2,3,figsize=(13,7),constrained_layout=True)
        for ch,scale in enumerate(SCALES):
            x=np.linspace(5,15,200);y=np.linspace(-9,7,200)
            requested=MATRIX[ch,0]*x[:,None]+MATRIX[ch,1]*y[None,:]
            field=p._sweep_models[(0,ch,0,'target')]
            codes=np.array([p._sweep_model_value(field,i) for i in range(40000)]).reshape(200,200)
            actual=codes*scale/32768
            comp=p._bias_t_fields[ch]
            comp_values=np.array([p._sweep_model_value(comp,i) for i in range(40000)]).reshape(200,200)
            area=codes*315.  # Intentional hold + linear return, code*fabric cycles.
            if mode=='fixed_time':
                comp_area=comp_values*600
                optimal=np.rint(-area/600/4)*4
                comp_error=float(np.max(abs(comp_values-optimal))*scale/32768)
            else:
                qscale=1<<comp['duration_frac_bits']
                times=(abs(comp_values)+qscale//2)//qscale
                positive,negative=p._bias_t_comp_codes[ch]
                comp_codes=np.where(comp_values<0,positive,negative)
                comp_area=comp_codes*times
                comp_error=None
            residual=(area+comp_area)*scale/32768/300
            reports.append(dict(mode=mode,channel=ch,full_scale_mv=scale,
                dc_voltage_mv=args.dc_voltage_mv,
                target_base_code=int(field['base']),axis_deltas_codes=list(field['axis_deltas']),
                requested_last_mv=float(requested[-1,-1]),actual_last_mv=float(actual[-1,-1]),
                max_target_error_mv=float(np.max(abs(actual-requested))),
                max_compensation_target_error_mv=comp_error,
                max_planned_area_residual_mv_us=float(np.max(abs(residual))),
                dmem_table_words=len(p._runtime_dmem_words)))
            for ax,data,title in zip(axs[ch],(requested,actual,actual-requested),
                ('Requested physical voltage','Executed incremental target','Target error')):
                im=ax.imshow(data.T,origin='lower',aspect='auto',extent=(5,15,-9,7))
                ax.set_title(f'DAC {ch+1}: {title}')
                ax.set_xlabel('Virtual X (mV)');ax.set_ylabel('Virtual Y (mV)')
                fig.colorbar(im,ax=ax,label='mV')
        fig.suptitle('200 x 200 virtual gate | constant integer increments | software command model\n'
                     'Ramp Q18 does not change SET target resolution; not an analog or RTL measurement')
        fig.savefig(args.out/f'virtual_grid_{mode}.png',dpi=150);plt.close(fig)
    (args.out/'increment_errors.json').write_text(json.dumps(reports,indent=2))
    print(json.dumps(reports,indent=2))


if __name__=='__main__':main()
