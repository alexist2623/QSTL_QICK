"""Prepare a single-thread retry of Vivado's failed DDR PHY helper.

Pass the generated get_cs_ip.tcl and a NEW, short ASCII work directory. This
copies the exact generated PHY constraints and preserves all IP parameters.
Run the resulting generate_phy.tcl with Vivado in that work directory, then
resume_implementation.tcl against the original project output directory.
"""
import argparse
from pathlib import Path
import re
import shutil


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('helper',type=Path)
    parser.add_argument('work',type=Path)
    args=parser.parse_args()
    helper=args.helper.resolve(); work=args.work.resolve()
    if not work.as_posix().isascii():
        raise ValueError('Use an ASCII path for this Vivado Windows workaround')
    source=helper.read_text()
    if 'set ip_vlnv xilinx.com:ip:ddr4_phy:2.2' not in source:
        raise ValueError('Expected the Vivado 2023.1 DDR4 PHY helper')
    constraints=list(helper.parent.glob('*/u_mig_ddr4_phy_phy.xdc'))
    if len(constraints)!=1:
        raise ValueError('Expected one exact generated DDR PHY constraint file')
    work.mkdir(parents=True,exist_ok=False)
    (work/'out/d_1_ddr4_0_0_phy.0').mkdir(parents=True)
    shutil.copy2(constraints[0],work/'phy.xdc')
    source=re.sub(r'(set_param general.maxThreads) \d+',r'\1 1',source)
    source=re.sub(r'(set_param chipscope.maxJobs) \d+',r'\1 1',source)
    source=re.sub(r'-jobs \d+','-jobs 1',source)
    for key,value in dict(output_xci=work/'out/d_1_ddr4_0_0_phy.0/result.xci',
                          output_dcp=work/'out/d_1_ddr4_0_0_phy.0/result.dcp',
                          output_dir=work/'out',xdc_files=work/'phy.xdc').items():
        source,count=re.subn(r'^set '+key+r' .*$',f'set {key} {{{value.as_posix()}}}',source,flags=re.M)
        if count!=1: raise ValueError(f'Missing or ambiguous helper setting {key}')
    output=work/'generate_phy.tcl'
    output.write_text(source+'\nputs "PHY_CACHE_READY"\nexit 0\n')
    print(output)


if __name__=='__main__':
    main()
