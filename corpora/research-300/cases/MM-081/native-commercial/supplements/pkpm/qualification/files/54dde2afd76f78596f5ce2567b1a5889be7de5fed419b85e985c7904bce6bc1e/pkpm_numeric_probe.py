"""2027 controlled SDATA experiment: own six-column specimen only."""
import hashlib,json,math,struct
from pathlib import Path
SOLVER=Path(r'C:\PKPM2027R1.0.1\Ribbon\SAT\WINSAT-A_x64.exe')
SHA='333b010d067f820c453972833e18bc9db2328059cbba83e456effd0dc79d9a4d'
def sha(b):return hashlib.sha256(b).hexdigest()
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def records(b):
    assert len(b)%4==0 and len(b)>16000
    f=struct.unpack('<'+'f'*(len(b)//4),b)
    assert f[2]==1
    def integer(x):
        assert math.isfinite(x) and int(x)==x and x>=0
        return int(x)
    h=integer(f[100]);header=f[h:h+20]
    assert header[12]==0 and header[13]==6 and header[14:17]==(0,0,0)
    base=integer(header[3]);out={}
    for i in range(6):
        off=base+60*i;row=f[off:off+60]
        assert len(row)==60 and row[34]==1 and row[8]==2 and row[11]==0
        assert row[6:8]==row[9:11] and row[35:37]==(f32(.3),f32(.6))
        xy=tuple(row[6:8]);assert xy not in out
        out[xy]=(off*4,row)
    return out

def compile(project):
    assert sha(SOLVER.read_bytes())==SHA
    project=Path(project);p=project/'SDATA.SAT';before=p.read_bytes();after=bytearray(before)
    inputs=json.loads((project/'input-receipt.json').read_text());props=json.loads((project/'sdk-properties.json').read_text())
    native={c['id']:c['properties'] for c in props['columns']};rows=records(before);edits=[]
    for i,m in enumerate(inputs['mapping']):
        xy=tuple(v/1000 for v in m['xyMm']);off,row=rows[xy];prop=native[m['columnId']]
        carrier=[prop[n] for n in ['GetArea','GetRjz','GetRjx','GetRjy']]
        assert list(row[30:34])==carrier
        requested=[.13+.04*i,.0023+.0003*i,.0041+.0004*i,.0011+.0002*i]
        packed=struct.pack('<4f',*requested);struct.pack_into('<4f',after,off+120,*requested)
        edits.append({'columnId':m['columnId'],'nativeMaterialId':m['nativeMaterialId'],'xyM':xy,'offsetBytes':off+120,'carrierAJIstrongIweak':carrier,'requestedAJIstrongIweak':requested,'compiledAJIstrongIweak':list(struct.unpack('<4f',packed))})
    allowed={index for e in edits for index in range(e['offsetBytes'],e['offsetBytes']+16)}
    assert all(i in allowed for i,(a,b) in enumerate(zip(before,after)) if a!=b)
    (project/'SDATA.SAT.before-numeric').write_bytes(before);(project/'SDATA.SAT.compiled-numeric').write_bytes(after);p.write_bytes(after)
    out={'solverSha256':SHA,'beforeSha256':sha(before),'compiledSha256':sha(after),'edits':edits,'status':'isolated input experiment; postsolve readback and closed-form verification required'}
    (project/'numeric-probe-input.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))

def verify(project):
    project=Path(project);evidence=json.loads((project/'numeric-probe-input.json').read_text());out={}
    for name in ['DATA.SAT','SDATA.SAT']:
        b=(project/name).read_bytes();r=records(b)
        for e in evidence['edits']:assert list(r[tuple(e['xyM'])][1][30:34])==e['compiledAJIstrongIweak']
        out[name]={'sha256':sha(b),'sixSectionRecordsMatch':True}
    (project/'numeric-probe-output.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
