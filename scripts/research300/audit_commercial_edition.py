"""Offline independent checks of retained production-native reference runs.

No production result normalizer is imported. Native binary/SDK arrays, physical
coordinates, section constants and calibrated endpoint transformations are
checked separately from the independent matrix comparison. Driver settings/load
readback remains explicitly attributed to the retained production input audit.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parent/'commercial'))
from commercial.pkpm_results import source_actions, end_wrench
from yjk_candidates import fe_records, numbers, source_axes
from commercial.yjk_results import native_axes, sdk_endpoint_actions, dot

DISP = ('ux', 'uy', 'uz', 'rx', 'ry', 'rz')
REACTIONS = ('fx', 'fy', 'fz', 'mx', 'my', 'mz')
COMPONENTS = ('N', 'Vy', 'Vz', 'T', 'My', 'Mz')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(ok, message):
    if not ok:
        raise ValueError(message)


def same(a, b, label, relative=1e-11, absolute=1e-10):
    check(math.isfinite(a) and math.isfinite(b) and abs(a-b) <= absolute+relative*abs(b),
          f'{label}: {a} != {b}')


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def serialization_interval(token):
    value=float(token)
    # The FE text uses at least six significant digits but elides trailing
    # zeroes. Include the prior float32 cast. This bounds INPUT serialization;
    # it never changes a reference request or candidate response tolerance.
    half_step=min(.5*10.**Decimal(token).as_tuple().exponent,abs(value)*5e-6)
    error=half_step+abs(value)*2**-24
    return value-error,value+error


def xyz(node):
    return [node[k] for k in 'xyz']


def pkpm(project, model, result):
    sections = {s['id']: s['properties'] for s in model['sections']}
    elements = {e['id']: e for e in model['elements']}
    compilation = read(project/'native-section-compilation.json')
    raw = (project/'SDATA.SAT').read_bytes()
    material_bytes=(project/'UserMaterial.SAT').read_bytes()
    _,version,count,stride=struct.unpack_from('<4i',material_bytes)
    check(version==20190824 and stride==96 and len(material_bytes)==16+count*stride,
          'native material binary layout')
    native_materials={struct.unpack_from('<i',material_bytes,16+i*stride+36)[0]:
                      struct.unpack_from('<dd',material_bytes,16+i*stride+56) for i in range(count)}
    for material in model['materials']:
        identity=result['summary']['nativeMaterialVerification']['materials'][material['id']]['nativeMaterialId']
        E,nu=native_materials[identity]
        same(E,material['E']*1000,'native elastic modulus')
        same(nu,material['nu'],'native Poisson ratio')
        same(E/(2*(1+nu)),material['G']*1000,'native shear modulus')
    check(sha(project/'SDATA.SAT.compiled') == compilation['afterSha256'], 'compiled section bytes changed')
    # SATWE updates other SDATA fields during analysis. Read properties again
    # from the final file, while retaining the exact pre-analysis compiled copy.
    check(set(compilation['members']) == set(elements), 'native section member coverage')
    for eid, row in compilation['members'].items():
        source = sections[elements[eid]['section']]
        actual = struct.unpack_from('<4f', raw, row['byteOffset'])
        axes=source_axes(model,elements[eid])
        swap=elements[eid]['type']=='column' and abs(abs(axes[2][0])-1)<1e-10
        keys=('A','J','Iz','Iy') if swap else ('A','J','Iy','Iz')
        check(actual == tuple(f32(source[k]) for k in keys), 'native section float32 readback '+eid)
    stages = read(project/'native-stage-evidence.json')
    check(stages['status'] == 'completed' and all(r['returncode'] == 0 for r in stages['phases']), 'native process stages failed')
    mesh = (project/'MESH.SAT').read_bytes()
    check((len(mesh)-20) % 20 == 0, 'mesh binary record length')
    coordinates = {i+1: list(struct.unpack_from('<3f2i', mesh, 20+i*20)[:3]) for i in range((len(mesh)-20)//20)}
    source_nodes = {tuple(f32(v) for v in xyz(n)): n['id'] for n in model['nodes']}
    check(len(source_nodes) == len(model['nodes']), 'ambiguous source coordinates')
    check(set(map(tuple, coordinates.values())) == set(source_nodes), 'native physical node coordinates/coverage')
    index = (project/'NODEINDEX.SAT').read_bytes()
    index = struct.unpack('<'+'f'*(len(index)//4), index)
    candidates = [i for i in range(1, min(50, len(index))+1) if all(v>0 and v==int(v) for v in index[:i]) and i+2*sum(map(int,index[:i]))==len(index)]
    check(len(candidates) == 1, 'ambiguous native floor/node index')
    nf = candidates[0]; cursor = nf; floors = []
    for count in map(int,index[:nf]):
        pairs = list(zip(index[cursor:cursor+2*count:2], index[cursor+1:cursor+2*count:2])); cursor += 2*count
        check(all(tag==int(tag) and int(tag) in coordinates and master==0 for tag, master in pairs), 'unqualified diaphragm or native node')
        floors.append([int(tag) for tag, _ in pairs])
    order = [tag for floor in reversed(floors) for tag in floor]
    constraints = (project/'ConstraintNodeNo.SAT').read_bytes()
    check(struct.unpack_from('<4i',constraints) == (3,20200113,len(coordinates),4), 'constraint node header')
    flags = struct.unpack_from('<'+'i'*len(coordinates),constraints,16)
    check(all(v in (0,1) for v in flags), 'unqualified native constraints')
    order += [i+1 for i, flag in enumerate(flags) if flag]
    case_files = {}
    for line in (project/'WDISPGKNO.OUT').read_text(encoding='gb18030').splitlines():
        if line.strip():
            name, label = line.split();case_files.setdefault(name, []).append(label)
    vectors = {}
    for name, labels in case_files.items():
        blob = (project/name.replace('DISP1', 'DISP')).read_bytes(); records = []
        if name == 'DISP1_ZDY.SAT':
            while blob:
                size = struct.unpack_from('<i',blob)[0]
                check(size>0 and len(blob)>=size+8 and struct.unpack_from('<i',blob,size+4)[0]==size, 'custom displacement record')
                records.append(blob[4:size+4]);blob=blob[size+8:]
        else:
            check(name == 'DISP1.SAT' and len(blob)%len(labels)==0, 'displacement case layout')
            width=len(blob)//len(labels);records=[blob[i*width:(i+1)*width] for i in range(len(labels))]
        check(len(records)==len(labels), 'displacement case count')
        vectors.update(zip(labels, records))
    values_checked = 0; slots = ('ux','uy','rz','rx','ry','uz')
    for cid, case in result['caseResults'].items():
        native = result['summary']['nativeLoadMapping']['cases'][cid]['nativeLabel']
        blob = vectors[native]
        check(len(blob)==len(order)*24, 'displacement node vector coverage')
        for i, tag in enumerate(order):
            nid=source_nodes[tuple(coordinates[tag])]
            for key,value in zip(slots,struct.unpack_from('<6f',blob,i*24)):
                same(case['displacements'][nid][key],value,f'raw displacement {cid}/{nid}/{key}',relative=0,absolute=0);values_checked+=1
        for eid, rows in case['memberStations'].items():
            for row in rows:
                expected=source_actions(elements[eid]['type'],row['nativeComponents'])
                for key,value in zip(COMPONENTS,expected):
                    same(row['components'][key],value,f'PKPM native slots {cid}/{eid}/{key}');values_checked+=1
        # Independently recover constrained reactions from signed physical end
        # wrenches. Raw API force extraction remains a driver-attributed step.
        for node in model['nodes']:
            nid=node['id']
            if not any(node['restraints']):continue
            total=[0.]*6
            for eid,element in elements.items():
                if nid not in element['nodes']:continue
                end=element['nodes'].index(nid)
                row=sorted(case['memberStations'][eid],key=lambda r:r['positionM'])[0 if end==0 else -1]
                wrench=end_wrench(element['type'],source_axes(model,element),end,row['nativeComponents'])
                total=[a+b for a,b in zip(total,wrench)]
            for source_case in model['load_cases']:
                if source_case['id']!=cid:continue
                for load in source_case['loads']:
                    if load['type']=='nodal' and load['node']==nid:
                        check(load.get('reference_frame','global')=='global','reaction load frame')
                        total=[a-load.get(key,0) for a,key in zip(total,REACTIONS)]
            for i,key in enumerate(REACTIONS):
                if node['restraints'][i]:
                    same(case['reactions'][nid][key],total[i],f'endpoint equilibrium reaction {cid}/{nid}/{key}')
                    values_checked+=1
    return {'nativeSectionMembers':len(elements),'nativeNodes':len(coordinates),'rawValuesChecked':values_checked,
            'independentScope':['compiled binary section constants','binary material E/G/nu','mesh coordinates','six-DOF native displacement file','calibrated native force slots','constrained reaction endpoint equilibrium'],
            'driverScope':['load and settings readback','native API force-array extraction']}


def yjk(project, model, result):
    sdk=read(project/'results.json');mapping=read(project/'mapping.json');fe=fe_records((project/'fea.dat').read_bytes())
    nodes={tag:numbers(row['C']) for tag,row in fe['*NODE']};frames=dict(fe['*FRAME'])
    sections={tag:numbers(row['P']) for tag,row in fe['*SECTION']};materials={tag:numbers(row['P']) for tag,row in fe['*MATERIAL']}
    source_nodes={n['id']:n for n in model['nodes']};source_sections={s['id']:s['properties'] for s in model['sections']};source_materials={m['id']:m for m in model['materials']}
    used_nodes={tag for frame in frames.values() for tag in map(int,frame['N'].split(','))}
    node_map={}
    for nid,n in source_nodes.items():
        matches=[tag for tag,p in nodes.items() if tag in used_nodes and math.dist(p,xyz(n))<1e-9]
        check(len(matches)==1,'native node identity '+nid);node_map[nid]=matches[0]
        native=next(n for n in sdk['nodes'] if n['id']==matches[0])
        check(xyz(native)==[f32(v) for v in xyz(n)],'SDK coordinate float32 readback '+nid)
    frame_map={};rigidity_max=0.
    for e in model['elements']:
        endpoints=[node_map[n] for n in e['nodes']]
        matches=[(tag,row) for tag,row in frames.items() if set(map(int,row['N'].split(',')))==set(endpoints)]
        check(len(matches)==1,'native frame identity '+e['id']);tag,row=matches[0];frame_map[e['id']]=(tag,row)
        check(row['T'] in ('BEAM','COLUMN','BRACE') and not any(numbers(row['E'])+numbers(row['R'])+numbers(row.get('RZL','0'))), 'native end releases/offsets/type')
        if row['T']=='BRACE':
            member=next(r for r in sdk['members']['braces'] if r['id']==tag)
            geometry=member['native_geometry']
            check(e['type']=='column' and geometry['brace_kind']==2 and geometry['is_truss']==0,
                  'unqualified ordinary inclined column')
        nn=list(map(int,row['N'].split(',')));nb=native_axes(nodes[nn[0]],nodes[nn[1]],numbers(row['DIR']));sb=source_axes(model,e)
        material=source_materials[e['material']];prop=source_sections[e['section']];E=material['E']*1000;G=material['G']*1000
        # FE DIR is the section height axis. P[1]/P[2] are inertia about
        # width/height axes, distinct from the signed SDK force-coordinate order.
        iy=sum(prop[k]*dot(nb[2],sb[i])**2 for k,i in [('Iy',1),('Iz',2)])
        iz=sum(prop[k]*dot(nb[1],sb[i])**2 for k,i in [('Iy',1),('Iz',2)])
        asy=sum(prop.get(k,5*prop['A']/6)*dot(nb[2],sb[i])**2 for k,i in [('Asy',1),('Asz',2)])
        asz=sum(prop.get(k,5*prop['A']/6)*dot(nb[1],sb[i])**2 for k,i in [('Asy',1),('Asz',2)])
        expected=[E*prop['A'],E*iy,E*iz,G*prop['J'],G*asz,G*asy]
        mat=materials[int(row['M'])];elastic=[mat[0]]*3+[mat[0]/(2*(1+mat[1]))]*3
        actual=[a*b*c for a,b,c in zip(sections[int(row['SEC'])],numbers(row['RF']),elastic)]
        p_tokens=dict(fe['*SECTION'])[int(row['SEC'])]['P'].split(',');rf_tokens=row['RF'].split(',')
        for a,b,p_token,r_token,modulus in zip(actual,expected,p_tokens,rf_tokens,elastic):
            error=abs(a/b-1);rigidity_max=max(rigidity_max,error)
            pl,pu=serialization_interval(p_token);rl,ru=serialization_interval(r_token)
            check(pl*rl*modulus-1e-9<=b<=pu*ru*modulus+1e-9,'native effective rigidity serialization '+e['id'])
    check(len(frame_map)==len(frames),'extra native frames')
    constraints=dict(fe['*CONSTRAINT'])
    for nid,n in source_nodes.items():
        restraint=[bool(v) for v in numbers(constraints[node_map[nid]]['R'])] if node_map[nid] in constraints else [False]*6
        check(restraint==n['restraints'],'native restraints '+nid)
    values_checked=0
    for cid, case in result['caseResults'].items():
        cm=next(r for r in mapping['load_cases'] if r['sourceCaseId']==cid)
        matches=[r for r in sdk['load_cases'] if r['name']==cm['nativeName']]
        check(len(matches)==1,'native load identity '+cid);key=matches[0]['key']
        for source_key,raw_key,components in [('displacements','node_disp',DISP),('reactions','node_reactions',REACTIONS)]:
            native={r['id']:r for r in sdk[raw_key][key]}
            for nid,values in case[source_key].items():
                for c in components:
                    same(values[c],native[node_map[nid]][c],f'SDK node {cid}/{nid}/{c}');values_checked+=1
        for eid,rows in case['memberStations'].items():
            e=next(e for e in model['elements'] if e['id']==eid);tag,row=frame_map[eid];nn=list(map(int,row['N'].split(',')))
            family={'BEAM':'beams','COLUMN':'columns','BRACE':'braces'}[row['T']]
            native=next(r for r in sdk['member_forces'][family][key] if r['id']==tag)
            nb=native_axes(nodes[nn[0]],nodes[nn[1]],numbers(row['DIR']));sb=source_axes(model,e)
            length=math.dist(xyz(source_nodes[e['nodes'][0]]),xyz(source_nodes[e['nodes'][1]]))
            for station in rows:
                se=0 if abs(station['positionM'])<1e-10 else 1 if abs(station['positionM']-length)<1e-9 else None
                if se is None:continue
                ne=nn.index(node_map[e['nodes'][se]]);idx=0 if ne==0 else len(native['sections'])-1
                slots=native['sections'][idx]
                check(station['nativeComponents']==slots,'SDK force array binding '+eid)
                expected=sdk_endpoint_actions(slots,'COLUMN' if row['T']=='BRACE' else row['T'],ne,se,nb,sb)
                for c,v in zip(COMPONENTS,expected):
                    same(station['components'][c],v,f'SDK endpoint {cid}/{eid}/{c}');values_checked+=1
    production=read(project/'native-physics-audit.json')
    check(production['passed'] is True,'retained production physics audit failed')
    return {'nativeNodes':len(node_map),'nativeFrameMembers':len(frame_map),'rawValuesChecked':values_checked,
            'maximumNativeRigiditySerializationError':rigidity_max,
            'independentScope':['native FE geometry/restraints/offsets','six effective rigidities','typed SDK node vectors','physical endpoint force rotation/signs'],
            'driverScope':['selected load arrays and selfweight/settings readback']}


def audit(job):
    job=Path(job);model=read(job/'model.json');binding=read(job/'binding.json');result=read(job/'native/result.json')
    projects=list((job/'native/projects').iterdir());check(len(projects)==1,'native project count')
    check(binding['executionRole']=='reference-verification','wrong execution role')
    project=projects[0]
    report=(pkpm if binding['engine']=='PKPM' else yjk)(project,model,result)
    report.update(job=str(job.resolve()),binding=binding,modelSha256=sha(job/'model.json'),
                  nativeResultSha256=sha(job/'native/result.json'),nativeArchiveSha256=sha(job/'remote-evidence.zip.bin'),
                  auditorSha256=sha(__file__),passed=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    reports=[]
    for receipt in sorted((a.work/'executions').glob('*/*.json')):
        row=read(receipt)
        if row['exitCode']!=0:continue
        try:report=audit(row['job'])
        except Exception as exc:report={'job':row['job'],'caseId':row['caseId'],'state':row['state'],'passed':False,'error':str(exc)}
        reports.append(report);print(json.dumps({k:report[k] for k in ['job','passed','error'] if k in report}),flush=True)
    with a.output.open('x') as f:json.dump({'valid':bool(reports) and all(r['passed'] for r in reports),'runs':reports},f,ensure_ascii=False,indent=2)
