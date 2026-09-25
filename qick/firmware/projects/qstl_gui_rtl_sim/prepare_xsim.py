"""Scope legacy IP HDL names in simulation without changing RTL logic.

Legacy IP packages reuse names such as fifo/bram_dp/dds_compiler_0 and omit
some top-level simulation files. Synthesis isolates these in OOC runs; a
flat mixed-language simulator does not. Include the synthesis HDL file list
and prefix HDL unit identifiers per IP family, recording every transformation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
NS={'s':'http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009'}


def units(text):
    # Strip comments before finding declarations, not before copying files.
    clean=re.sub(r'/\*.*?\*/|//[^\n]*|--[^\n]*','',text,flags=re.S)
    return set(re.findall(r'\bmodule\s+(\w+)|\bentity\s+(\w+)\s+is|\bpackage\s+(\w+)\s*;',clean,re.I))


def transform(text,mapping):
    tokens=re.compile(r'"(?:[^"\n]|"")*"|\b[A-Za-z_]\w*\b')
    return tokens.sub(lambda m: mapping.get(m[0].lower(),m[0]) if not m[0].startswith('"') else m[0],text)


def main():
    p=argparse.ArgumentParser();p.add_argument('project',type=Path);args=p.parse_args()
    run=args.project/'qstl_gui_rtl_sim.sim/sim_1/behav/xsim'
    out=args.project/'namespaced';out.mkdir(exist_ok=True)
    topology=json.loads((HERE/'topology.json').read_text())
    types={c['type'] for c in topology['cells'].values()}
    families={}
    for component in (REPO/'qick/firmware/ip').glob('*/component.xml'):
        root=ET.parse(component)
        name=root.findtext('s:name',namespaces=NS)
        if name not in types:continue
        fs=next((x for x in root.findall('.//s:fileSet',NS) if x.findtext('s:name',namespaces=NS)=='xilinx_anylanguagesynthesis_view_fileset'),None)
        if fs is None:continue
        paths=[component.parent/x.findtext('s:name',namespaces=NS) for x in fs.findall('s:file',NS)]
        families[name]=[x.resolve() for x in paths if x.suffix.lower() in ('.v','.sv','.vhd')]
    # The generated simulator project supplies the vendor IP models/wrappers.
    old=[]
    for filename in ('tb_gui_vlog.prj','tb_gui_vhdl.prj'):
        for s in re.findall(r'"([^"\n]+)"',(run/filename).read_text()):
            path=(run/s).resolve()
            fresh=Path(path.as_posix().replace('qstl_gui_rtl_sim.ip_user_files/bd/',
                                               'qstl_gui_rtl_sim.gen/sources_1/bd/'))
            if fresh.is_file():path=fresh
            if path.suffix.lower() in ('.v','.sv','.vhd') and path not in old:old.append(path)
    def family_for(path):
        s=path.as_posix()
        match=re.search(r'/ip/(sim_bd_[^/]+)/',s)
        if match:
            name=match[1]
            for cell,data in topology['cells'].items():
                if name==f'sim_bd_{cell}_0' and data['type'] in families:return data['type']
        return None
    for path in old:
        family=family_for(path)
        if family and '/src/' in path.as_posix() and '/ipshared/' not in path.as_posix():
            families[family].append(path)
    maps={}
    for family,paths in families.items():
        names={n for path in paths for row in units(path.read_text(errors='replace')) for n in row if n}
        maps[family]={n.lower():f'sim_{family}_{n}' for n in names}
    # This synthesis-only package has no simulation modelName; Vivado invents
    # qick_vec2bit_v1_0 in its sim wrapper. Bind it to the actual synthesis top.
    maps['qick_vec2bit']['qick_vec2bit_v1_0']=maps['qick_vec2bit']['qick_vec2bit']
    files=[];manifest=[]
    def copy(path,family):
        target=out/f'{len(files):03d}_{path.name}'
        source=path.read_text(errors='replace')
        result=transform(source,maps[family]) if family else source
        if not target.exists() or target.read_text()!=result:
            target.write_text(result)
        files.append(target)
        manifest.append(dict(source=str(path),copy=target.name,family=family,
            source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            copied_sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    for family,paths in families.items():
        for path in paths:copy(path,family)
    for path in old:
        if '/ipshared/' in path.as_posix():continue
        family=family_for(path)
        if family and path in families[family]:continue
        copy(path,family)
    # Vendor BD IPs also have shared wrappers outside the custom IP repository.
    # Keep any vendor ipshared file which was not one of our custom families.
    custom_names={n for m in maps.values() for n in m}
    for path in old:
        if '/ipshared/' not in path.as_posix():continue
        names={n.lower() for row in units(path.read_text(errors='replace')) for n in row if n}
        if not names.intersection(custom_names):copy(path,None)
    (HERE/'namespace_manifest.json').write_text(json.dumps(dict(mappings=maps,files=manifest),indent=2)+'\n')
    for suffix,kind in (('vlog','sv'),('vhdl','vhdl')):
        selected=[f for f in files if (f.suffix=='.vhd')==(suffix=='vhdl')]
        lines=[]
        for f in selected:
            lang='vhdl' if f.suffix=='.vhd' else 'sv' if f.suffix=='.sv' else 'verilog'
            lines.append(f'{lang} xil_defaultlib "{f.as_posix()}"')
        (run/f'isolated_{suffix}.prj').write_text('\n'.join(lines)+'\nnosort\n')
    if not (out/'tb_body.svh').exists() or (out/'tb_body.svh').read_bytes()!=(HERE/'tb_body.svh').read_bytes():
        shutil.copyfile(HERE/'tb_body.svh',out/'tb_body.svh')
    for directory in re.findall(r'(?:-i|--include) "([^"]+)"',(run/'tb_gui_vlog.prj').read_text()):
        for header in (run/directory).resolve().glob('*.vh'):
            if not (out/header.name).exists() or (out/header.name).read_bytes()!=header.read_bytes():
                shutil.copyfile(header,out/header.name)
    print(len(files),'HDL files,',len(maps),'namespaced IP families; run dir',run)


if __name__=='__main__':main()
