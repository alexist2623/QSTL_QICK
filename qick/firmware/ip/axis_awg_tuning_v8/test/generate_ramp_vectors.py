"""Independent rational/bit-accurate oracle for v7 public command ports.

Reference is evaluated by absolute scalar index, not by DUT recurrences,
partial products, register names, or measured/fitted output latency.
"""
from pathlib import Path
import json, random, sys
from collections import deque

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / 'qick/qick_lib'))
from qick.ramp_v7 import ramp_packet


def signed(v, bits):
    return (v ^ (1 << (bits-1))) - (1 << (bits-1))


def quant(fixed):
    # Preserve the existing signed 48-bit internal RAMP arithmetic contract.
    v = signed(fixed & ((1 << 48)-1), 48) >> 18
    return max(-32768, min(32764, v)) & -4


def wave(packet, start):
    if (packet >> 151) & 1:
        peak = signed(packet & 0xffff, 16)
        final = signed((packet >> 16) & 0xffff, 16)
        up = signed((packet >> 32) & ((1<<35)-1), 35)
        down = signed((packet >> 67) & ((1<<35)-1), 35)
        r = (packet >> 102) & 15
        f = (packet >> 106) & 31
        fpos = ((packet >> 134) & 1023)*16+(f & 15)
        count = (packet >> 111) & ((1<<23)-1)
        final = peak if f == 31 else final
        result=[]
        for n in range((count+15)//16*16):
            if n >= count-1:
                y = final << 18
            elif n < r:
                y = start << 18
            else:
                a,b,s,k = (peak,final,down,n-fpos) if f!=31 and n>=fpos else (start,peak,up,n-r)
                y = (a<<18)+s*k
                y = min(y,b<<18) if b>=a else max(y,b<<18)
            result.append(quant(y))
        return result,final
    opcode=(packet>>144)&3
    target=signed(packet & 0xffffffff,32)
    if opcode==1:
        return [quant(target<<18)]*16, 0 if (packet>>146)&1 else target
    duration=max(1,(packet>>64)&((1<<23)-1))
    step=signed((packet>>96)&0xffffffff,32)
    start=max(-32768,min(32764,start))
    return [quant(target<<18 if n>=duration-1 else (start<<18)+step*n)
            for n in range((duration+15)//16*16)],target


def generate(destination):
    rng=random.Random(71027)
    queue=[];logical=0;current=0;delay=deque([[0]*16 for _ in range(11)])
    inputs=[];expected=[];labels=[];commands=0
    def tick(packet=None,override=None):
        nonlocal logical,current,queue,commands
        if packet is not None:
            assert not queue, 'test scheduling overlaps a reserved output word'
            values,logical=wave(packet,logical)
            queue=[values[i:i+16] for i in range(0,len(values),16)]
            current=quant(logical<<18);commands+=1
        word=queue.pop(0) if queue else [current]*16
        delay.append(word);out=delay.popleft()
        if override is not None:
            logical=override;current=quant(override<<18);queue=[]
            out=[current]*16;delay.clear();delay.extend([out]*11)
        inp=(int(packet is not None)<<160)|(packet or 0)
        if override is not None:inp|=(1<<193)|((override&0xffffffff)<<161)
        inputs.append(inp);expected.append(sum((v&0xffff)<<(16*i) for i,v in enumerate(out)))
    def emit(packet,label):
        labels.append(dict(cycle=len(inputs),label=label,word=f'{packet:040x}'))
        tick(packet)
        while queue:tick()
    def setv(v,hold_zero=False):
        emit((1<<144)|(int(hold_zero)<<146)|(v&0xffffffff),'set')
    def extended(**kw):
        result=ramp_packet(start=max(-32768,min(32764,logical)),**kw)
        emit(result['word'],'extended_ramp')
    for _ in range(20):tick()
    # Exhaust every first/falling lane pair, including lane15 and boundaries.
    for r in range(16):
        for f in range(16):
            for polarity in (-1,1):
                setv(0)
                r_end=r+1+r%5
                f0=f if f>=r_end else f+16
                if f0<r_end:f0+=16
                extended(target=polarity*16380,rise_start=r,rise_end=r_end,
                         fall_start=f0,fall_end=f0+1+(f%19),end_target=polarity*400)
                setv(0)  # arrives at EXACT next issue edge while tail drains
    # No falling edge: 11111 must retain target, not become lane15.
    for r in range(16):
        setv(-32768)
        extended(target=32764,rise_start=r,rise_end=r+1)
        for _ in range(5):tick()
        setv(0)
    # 1/1/1 cadence inside 10ns and immediate target changes with SET zero-hold.
    for trial in range(100):
        setv(0)
        extended(target=8000,rise_start=1,rise_end=3,fall_start=10,fall_end=15,end_target=0)
        setv(4000,trial%2==0)
        extended(target=-4000,rise_start=0,rise_end=3,fall_start=8,fall_end=15,end_target=0)
    # Cross one and many word boundaries; exercise signed 35-bit slope limits.
    for trial in range(800):
        a=rng.randrange(-8192,8192)*4;b=rng.randrange(-8192,8192)*4;c=rng.randrange(-8192,8192)*4
        r=rng.randrange(16);rend=r+rng.randrange(1,80);f=rend+rng.randrange(0,50);fend=f+rng.randrange(1,160)
        setv(a)
        extended(target=b,rise_start=r,rise_end=rend,fall_start=f,fall_end=fend,end_target=c)
    # Reaching an endpoint early must clamp BEFORE any fixed-width overflow.
    # Both signs: maximum legal hold-start offset after a one-sample full span.
    for a,b,c in [(-32768,32764,-32768),(32764,-32768,32764)]:
        setv(a)
        extended(target=b,rise_start=0,rise_end=1,
                 fall_start=16383,fall_end=16400,end_target=c)
    for trial in range(60):
        a=rng.randrange(-8192,8192)*4;b=rng.randrange(-8192,8192)*4;c=rng.randrange(-8192,8192)*4
        r=rng.randrange(16);f=rng.randrange(6000,16384)
        setv(a)
        extended(target=b,rise_start=r,rise_end=r+rng.randrange(1,4),
                 fall_start=f,fall_end=f+rng.randrange(1,100),end_target=c)
    for gap in range(15):
        setv(0)
        packet=ramp_packet(start=0,target=32764,rise_start=15,rise_end=100,
                           fall_start=127,fall_end=400,end_target=-32768)['word']
        tick(packet)
        for _ in range(gap):tick()
        tick(override=-400 if gap%2 else 0)
        for _ in range(15):tick()
    for _ in range(30):tick()
    destination=Path(destination)
    (destination/'stimulus.hex').write_text(''.join(f'{x:049x}\n' for x in inputs))
    (destination/'expected.hex').write_text(''.join(f'{x:064x}\n' for x in expected))
    (destination/'vector_count.hex').write_text(f'{len(inputs):08x}\n')
    result=dict(cycles=len(inputs),scalar_assertions=len(inputs)*16,commands=commands,
                first_fall_lane_pairs=256,polarities=2,random_trapezoids=800,
                same_word_sequences=100,long_fullspan_holds=2,long_random_holds=60,
                override_stages=15,latency=11,events=labels)
    (destination/'vector_manifest.json').write_text(json.dumps(result,indent=2))
    return result
