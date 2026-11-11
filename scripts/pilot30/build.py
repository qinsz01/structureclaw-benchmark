"""Author the migration pilot. Inputs and truths are frozen before candidate use."""
import argparse
from copy import deepcopy
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import sys

os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from cases import definitions,SOURCES,rect
from independent import static,modes,transient

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'.bench-work/section-diversity-v1-final-20261027/corpora/research-300'
EXPORTED=ROOT/'.bench-work/pilot30-migration-public-20261028'
REVIEW=ROOT/'planning/research300-v2/reuse-review/review.json'


def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:f.write(obj if isinstance(obj,str) else json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def table(headers,rows):
    s=io.StringIO(newline='');w=csv.writer(s,lineterminator='\n');w.writerow(headers);w.writerows(rows);return s.getvalue()


DELIVERY='''# Pilot delivery / 试点交付
Use the documented common solver with your own model. Public files contain inputs, not reference answers. Keep the designated engine. For this pilot the authoritative output is answer.json: quantities=[{id,value,unit}], derived=[{id,value,unit,governingOperand,governingSelection}], clarifications=[{field,question}], and jobIds identifying your actual solves. See the public solver protocol for complete formats. A governing extremum must give the signed value and the winning operand request ID as governingOperand, plus its {kind,id} governingSelection. Arithmetic outputs without a governor use null for both fields. Follow each public tiePolicy; the default is the first operand in the published order, while any allows mathematically co-governing operands. Scheme tasks additionally need selectedScheme (null if none is feasible) and schemes=[{id,jobIds,maximum,volume,feasible}] for every supplied scheme. Modal tasks requesting shapes need modeShapes=[{modeNumber,values:{node:ux}}]. A signed time-history extremum also gives its time in seconds.
本试点以结构化数值和真实计算证据评分。正文摘要即可，完整数值无需在正文再次抄写。此约定覆盖迁移资料中重复列全表或强制结果图的旧交付文字；结果图可以附带，本试点暂不评分输出图件。MM表示输入图纸重建能力。
Query-only turns reuse prior jobs for the unchanged model. Essential unknown inputs require a targeted clarification; a result-query ambiguity does not invalidate already determined ordinary outputs. Do not solve uncertain physical models. Use actual source/target units and signed values. Axial-only members carry axial force, not bending; their inactive I/J fields are separately diagnostic, not an axial-response correctness gate.
All models use SI m/kN/MPa/rad and right-handed global Z-up. Use each task's declared dimension: new tasks are 2D in XZ; migrated tasks also include 3D models. Self-weight and other automatic controls follow the explicit input, not assumed defaults. Source projects are bounded analysis abstractions, not full engineering designs or safety certifications.
'''


def drawing(m,p):
    from PIL import Image,ImageDraw,ImageFont
    image=Image.new('RGB',(2000,1400),'white');d=ImageDraw.Draw(image)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',22)
    xs=[n['x'] for n in m['nodes']];zs=[n['z'] for n in m['nodes']]
    sx=930/max(max(xs)-min(xs),2);sz=900/max(max(zs)-min(zs),2)
    ns={n['id']:n for n in m['nodes']}
    def xy(n):return (100+(n['x']-min(xs))*sx,1150-(n['z']-min(zs))*sz)
    for e in m['elements']:
        a,b=[xy(ns[n]) for n in e['nodes']];d.line([a,b],fill='#334155',width=5)
        d.text(((a[0]+b[0])/2+10,(a[1]+b[1])/2+8),e['id'],font=font,fill='#64748b')
    for n in m['nodes']:
        x,y=xy(n);d.ellipse((x-6,y-6,x+6,y+6),fill='black')
        d.text((x+8,y-30),n['id'],font=font,fill='#1d4ed8')
    d.text((40,30),'Geometry: global X-Z, coordinates in m; all Y=0. Inactive uy/rx/rz fixed.',font=font,fill='black')
    d.text((40,70),'Not to scale. Member end order and all properties are in the schedules.',font=font,fill='black')
    d.text((1160,150),'Node | X (m) | Z (m) | fixed ux,uz,ry',font=font,fill='black')
    for i,n in enumerate(m['nodes']):
        mask=','.join(str(int(n['restraints'][j])) for j in [0,2,4])
        d.text((1160,210+70*i),f"{n['id']} | {n['x']:g} | {n['z']:.8g} | {mask}",font=font,fill='#1d4ed8')
    image.save(p)


def documents(case,turn,p,initial):
    m=turn['model']
    if not initial:
        # Later interaction turns contain patches, not a complete current model.
        # Reissued excitation data is itself a legitimate supplied input patch.
        if turn.get('parameters'):
            params=deepcopy(turn['parameters'])
            if 'groundMotion' in params:
                write(p/'excitation.csv',table(['sample','acceleration'],list(enumerate(params.pop('groundMotion')))))
                params['groundMotionFile']='excitation.csv'
            write(p/'analysis-parameters.json',params)
        return
    if initial:
        if case.get('visual'): drawing(m,p/'geometry.png')
        else: write(p/'nodes.csv',table(['node','x_m','y_m','z_m','ux_fixed','uy_fixed','uz_fixed','rx_fixed','ry_fixed','rz_fixed','mass_tonne'],
              [[n['id'],n['x'],n['y'],n['z'],*map(int,n['restraints']),n.get('mass','')] for n in m['nodes']]))
        write(p/'members.csv',table(['member','i','j','kind','material','section','roll_deg','local_bending_releases'],
            [[e['id'],*e['nodes'],e['type'],e['material'],e['section'],e.get('rotation_angle',0),json.dumps(e.get('releases',{}))] for e in m['elements']]))
        write(p/'materials.csv',table(['id','E_MPa','G_MPa','nu','rho_kg_per_m3'],[[x['id'],x['E'],x['G'],x['nu'],x['rho']] for x in m['materials']]))
        if case.get('visual') and any(n.get('mass') for n in m['nodes']):
            write(p/'mass.csv',table(['node','mass_tonne'],[[n['id'],n.get('mass',0)] for n in m['nodes']]))
        if case.get('sourceId'): write(p/'source-basis.json',SOURCES[case['sourceId']])
        write(p/'section-convention.json',{'units':'b,h in m; A in m2; Iy,Iz,J in m4',
            'constraint':'0 < b <= h','A':'b*h','Iy':'b*h^3/12','Iz':'h*b^3/12',
            'J':'b*h^3*(1/3 - 0.21*(b/h)*(1 - b^4/(12*h^4)))',
            'meaning':'Explicit authored uncoupled elastic constants; not a full section/code design check.'})
        if case.get('schemes'):
            schemes=[]
            for s in case['schemes']:
                v=deepcopy(m);rect(v,s['section'],s['b'],s['h'])
                schemes.append({**s,'properties':next(x for x in v['sections'] if x['id']==s['section'])['properties']})
            write(p/'schemes.json',schemes)
    # Current-state schedules are released only on this turn. No future data.
    write(p/'sections.json',m['sections'])
    write(p/'analysis-control.json',m['analysis_control'])
    write(p/'combinations.json',m['load_combinations'])
    if case['id']=='P30-STD-009':
        write(p/'surface-loads.json',{'angleDegrees':15,'tributaryWidthM':3.4,
            'D':{'pressure':.35,'unit':'kN/m2','direction':'global-down','areaBasis':'actual-roof-area'},
            'W':{'pressure':.8,'unit':'kN/m2','direction':'roof-normal-up','globalUnitVector':[-math.sin(math.radians(15)),0,math.cos(math.radians(15))]},
            'Q':{'pressure':.7,'unit':'kN/m2','direction':'global-down','areaBasis':'actual-roof-area'},
            'loadedMembers':['R1','R2'],'rule':'q=p*tributaryWidth per ACTUAL member length; apply once; no extra area load.'})
    else: write(p/'loads.json',m['load_cases'])
    if turn.get('parameters'):
        params=deepcopy(turn['parameters'])
        if 'groundMotion' in params:
            write(p/'excitation.csv',table(['sample','acceleration'],list(enumerate(params.pop('groundMotion')))))
            params['groundMotionFile']='excitation.csv'
        write(p/'analysis-parameters.json',params)


def reference(turn,schemes=None):
    ref=deepcopy(turn);ref.pop('instruction');ref['referenceChecks']=[]
    kind=turn['kind'];m=turn['model']
    if kind=='clarify':return ref
    if kind=='static':
        values={};qs=[]
        for q in turn['requests']:
            sel=q['selection'];key=sel['kind']+':'+sel['id']
            if key not in values:
                factors={sel['id']:1} if sel['kind']=='case' else next(c['factors'] for c in m['load_combinations'] if c['id']==sel['id'])
                values[key],check=static(m,factors);ref['referenceChecks'].append({'selection':sel,**check})
            qs.append({**q,'value':values[key][q['location']['id']][q['component']]})
        ref['requests']=qs
    elif kind=='modal':
        md=modes(m);ref['requests']=[]
        for i in range(turn['parameters']['numModes']):
            for field,unit,value in [('period','s',md['periods'][i]),('frequency','Hz',1/md['periods'][i]),('effectiveMass','tonne',md['effectiveMass'][i])]:
                ref['requests'].append({'id':f'mode-{i+1}-{field}','path':['modes',i,field],'unit':unit,'value':value,'tolerance':{'absolute':1e-8,'relative':1e-6}})
        ref['modalTruth']={'shape':md['shape'],'masses':{n['id']:n.get('mass',0) for n in m['nodes']}}
        ref['referenceChecks']=[{'method':'independent-condensed-K-M-eigenproblem','periods':md['periods']}]
    elif kind=='transient':
        rows,check=transient(m,turn['parameters']);fine,_=transient(m,turn['parameters'],2)
        top='F2';vals=[r['nodes'][top]['ux'] for r in rows];i=max(range(len(vals)),key=lambda i:abs(vals[i]));ref['requests']=[
            {'id':'F2-ux-at-0.4s','path':['timeHistory',19,'nodes',top,'ux'],'unit':'m','value':vals[19],'tolerance':{'absolute':1e-9,'relative':1e-6}},
            {'id':'F2-signed-peak-ux','path':['timeHistory','*','nodes',top,'ux'],'operation':'max_abs','unit':'m','value':vals[i],
             'time':rows[i]['time'],'tolerance':{'absolute':1e-9,'relative':1e-6}}]
        ref['referenceChecks']=[{**check,'halfStepMaxDifference':max(abs(a-b['nodes'][top]['ux']) for a,b in zip(vals,fine[1::2]))}]
    elif kind=='scheme':
        result=[]
        for scheme in schemes:
            variant=deepcopy(m);rect(variant,scheme['section'],scheme['b'],scheme['h']);maximum=0
            for sel in turn['schemeSelections']:
                factors=next(c['factors'] for c in m['load_combinations'] if c['id']==sel)
                v,check=static(variant,factors)
                maximum=max(maximum,max(abs(v[n][turn['constraint']['component']]) for n in turn['constraint']['nodes']))
            ns={n['id']:n for n in m['nodes']};ps={s['id']:s['properties'] for s in variant['sections']}
            volume=sum(ps[e['section']]['A']*math.dist([ns[e['nodes'][0]][k] for k in ['x','y','z']],
                                                    [ns[e['nodes'][1]][k] for k in ['x','y','z']]) for e in variant['elements'])
            result.append({'id':scheme['id'],'model':variant,'maximum':maximum,'volume':volume,'feasible':maximum<=turn['constraint']['absoluteLimit']})
        feasible=[r for r in result if r['feasible']]
        # An infeasible set is an explicit legitimate outcome, never invent a winner.
        ref['schemeTruth']=result;ref['optimalSchemes']=[r['id'] for r in feasible if abs(r['volume']-min(x['volume'] for x in feasible))<1e-12]
        ref['schemes']=deepcopy(schemes);ref['requests']=[]
        ref['referenceChecks']=[{'method':'independent-exhaustive-finite-scheme-enumeration','feasible':len(feasible),'schemes':len(result)}]
    else:raise ValueError(kind)
    ref['reportIds']=[q['id'] for q in ref['requests']]
    return ref


def legacy(out):
    rows=[]
    for oldid in read(REVIEW)['summary']['firstPilotExistingCases']:
        family=oldid.split('-')[0];ordinal=sum(r['family']==family for r in rows)+1;cid=f'P30-{family}-{ordinal:03}'
        folder=OLD/'cases'/oldid;contract=read(folder/'contract.json');truth=read(folder/'independent-reference.json')
        item={'id':cid,'title':oldid+' '+next(r['title'] for r in read(REVIEW)['cases'] if r['caseId']==oldid),
              'family':family,'origin':'legacy','legacyId':oldid,'engine':contract['plannedEngine'],'turns':[]}
        for t in contract['turns']:
            tid=t['id'];target=out/'cases'/cid/'public'/tid;target.mkdir(parents=True)
            source=EXPORTED/oldid/tid/'agent-input/cases'/oldid
            oldtask=read(source/'task.json')['turns'][0]
            for f in source.iterdir():
                if f.is_file() and f.name!='task.json':shutil.copyfile(f,target/f.name)
            ref={'kind':'clarify' if t['state'] is None else 'query' if t['expectation']=='query' else 'static',
                 'engine':item['engine'],'requests':[],'derived':[], 'clarificationFields':t.get('unresolvedFields',[])}
            if t['state'] is not None:
                state=next(s for s in truth['states'] if s['state']==t['state'])
                ref.update(model=read(folder/contract['modelStates'][t['state']-1]),requests=state['quantities'])
                outputs=[o for o in contract['requiredOutputs'] if o.get('state')==t['state'] and (not o.get('turnIds') or tid in o['turnIds'])]
                ref['reportIds']=sorted({q for o in outputs if o['kind']=='numerical' for q in o['quantityIds']})
                derivedids={q for o in outputs if o['kind']=='derived' for q in o['quantityIds']}
                ref['derived']=[d for d in state.get('derived',[]) if d['id'] in derivedids]
            pub={'caseId':cid,'turnId':tid,'engine':item['engine'],'analysis':'static',
                 'instruction':oldtask['instruction']+'\n\n交付方式以delivery.md为准。',
                 'requests':[{k:v for k,v in q.items() if k not in ['value','tolerance','rawTrace','nativeStatus']} for q in ref['requests']],
                 'reportIds':ref.get('reportIds',[]),'derived':[{k:v for k,v in d.items() if k in ['id','operation','tiePolicy','operands','unit','description']} for d in ref['derived']],
                 'attachments':oldtask['attachments']}
            write(target/'task.json',pub);write(target/'delivery.md',DELIVERY)
            private=out/'cases'/cid/'private'/f'{tid}.json';write(private,ref)
            item['turns'].append({'id':tid,'public':str(target.relative_to(out)),'private':str(private.relative_to(out))})
        write(out/'cases'/cid/'private/legacy-binding.json',{'legacyId':oldid,'sourceHash':truth['sourceHash'],
             'contractSha256':sha(folder/'contract.json'),'modelHashes':[sha(folder/f) for f in contract['modelStates']],
             'referenceSha256':sha(folder/'independent-reference.json'),'deliveryAmended':True,'oldScoreUnchanged':True})
        rows.append(item)
    return rows


def build(out):
    if out.exists():raise FileExistsError('New edition directory required; retain failed attempts')
    out.mkdir(parents=True);items=legacy(out)
    for case in definitions():
        item={k:v for k,v in case.items() if k not in ['turns','schemes']};item['turns']=[]
        for i,t in enumerate(case['turns'],1):
            tid=f't{i}';target=out/'cases'/case['id']/'public'/tid;target.mkdir(parents=True)
            documents(case,t,target,i==1);ref=reference(t,case.get('schemes'));ref['engine']='OpenSees'
            if t['kind']=='clarify':ref.pop('model',None)
            pub={'caseId':case['id'],'turnId':tid,'engine':'OpenSees','analysis':t['kind'],
                 'instruction':t['instruction'],'requests':[{k:v for k,v in q.items() if k not in ['value','tolerance','time']} for q in ref.get('requests',[])],
                 'reportIds':ref.get('reportIds',[]),'constraint':t.get('constraint'),'schemeSelections':t.get('schemeSelections'),
                 'requireShapes':t.get('requireShapes',False),'sourceId':case.get('sourceId')}
            write(target/'task.json',pub);write(target/'delivery.md',DELIVERY)
            private=out/'cases'/case['id']/'private'/f'{tid}.json';write(private,ref)
            item['turns'].append({'id':tid,'public':str(target.relative_to(out)),'private':str(private.relative_to(out))})
        items.append(item)
    assert len(items)==30 and sum(c['family']=='STD' for c in items)==10
    manifest={'schemaVersion':1,'edition':'research300-v2-pilot30-v1','status':'authored-pending-oracle-and-input-review',
              'sutCommit':'db3c0b1da44fe668a6037a6c2e7f068d14354539','candidateRunsAtAuthoring':0,'externalBlindReviews':0,
              'cases':items,'files':[{'path':p.relative_to(out).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file()]}
    write(out/'manifest.json',manifest)
    return manifest


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    m=build(a.output.resolve());print(json.dumps({'cases':len(m['cases']),'turns':sum(len(c['turns']) for c in m['cases']),'files':len(m['files'])}))
