"""Local source-guided reconstruction, not an external/blind review.

Four image coordinate tables are manually transcribed after visual inspection.
The reviewer reads released schedules and applies only each released patch; it
does not use the authoring model generator to create the reviewed model.
"""
import argparse
from copy import deepcopy
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
GEOMETRY={
 'P30-MM-007':[('A',0,0,[1,1,0]),('C',4,0,[0,1,0]),('B',9,0,[0,1,0])],
 'P30-MM-008':[('A',0,0,[1,1,1]),('F1',0,3,[0,1,0]),('F2',0,6.8,[0,1,0])],
 'P30-MM-009':[('A0',0,0,[1,1,1]),('A1',23.61,0,[1,1,1]),('A2',55.82,0,[1,1,1]),
   ('R0',0,31.2,[0,0,0]),('R1',11.805,31.2,[0,0,0]),('R2',23.61,31.2,[0,0,0]),('R3',39.715,31.2,[0,0,0]),('R4',55.82,31.2,[0,0,0])],
 'P30-MM-010':[('A',0,0,[1,1,1]),('B',2.6,0,[1,1,1]),('P',0,1.5,[0,0,0]),('M',1.3,1.848334,[0,0,0]),('Q',2.6,2.196668,[0,0,0])],
}
def read(p):return json.loads(p.read_text())
def csvrows(p):return list(csv.DictReader(p.open()))
def section(m,b,h):
    # Public section convention, independently implemented from its equations.
    v={'A':b*h,'Iy':b*h*h*h/12,'Iz':h*b*b*b/12,
       'J':b*h*h*h*(1/3-.21*b/h*(1-(b/h)**4/12))}
    next(s for s in m['sections'] if s['id']=='B')['properties']=v
def initial(folder,cid):
    if cid in GEOMETRY:
        nodes=[{'id':i,'x':x,'y':0.,'z':z,'restraints':[bool(r[0]),True,bool(r[1]),True,bool(r[2]),True]} for i,x,z,r in GEOMETRY[cid]]
        mass=folder/'mass.csv'
        if mass.exists():
            mm={r['node']:float(r['mass_tonne']) for r in csvrows(mass)}
            for n in nodes:
                if mm[n['id']]>0:n['mass']=mm[n['id']]
    else:
        nodes=[]
        for r in csvrows(folder/'nodes.csv'):
            n={'id':r['node'],'x':float(r['x_m']),'y':float(r['y_m']),'z':float(r['z_m']),
               'restraints':[bool(int(r[k+'_fixed'])) for k in ['ux','uy','uz','rx','ry','rz']]}
            if r['mass_tonne']!='':n['mass']=float(r['mass_tonne'])
            nodes.append(n)
    elements=[]
    for r in csvrows(folder/'members.csv'):
        e={'id':r['member'],'nodes':[r['i'],r['j']],'type':r['kind'],'material':r['material'],'section':r['section'],'rotation_angle':float(r['roll_deg'])}
        releases=json.loads(r['local_bending_releases'])
        if releases:e['releases']=releases
        elements.append(e)
    materials=[{'id':r['id'],'name':r['id'],'type':'steel','E':float(r['E_MPa']),'G':float(r['G_MPa']),'nu':float(r['nu']),'rho':float(r['rho_kg_per_m3'])} for r in csvrows(folder/'materials.csv')]
    m={'schema_version':'2.2.0','unit_system':'SI','coordinate_system':{'semantics':'global-z-up','version':1,'dimension':'2d','plane':'xz','dof_order':['ux','uy','uz','rx','ry','rz']},
       'nodes':nodes,'elements':elements,'materials':materials,'sections':read(folder/'sections.json'),
       'load_combinations':read(folder/'combinations.json'),'analysis_control':read(folder/'analysis-control.json')}
    if (folder/'surface-loads.json').exists():
        d=read(folder/'surface-loads.json');cases=[]
        for name in ['D','W','Q']:
            record=d[name];q=record['pressure']*d['tributaryWidthM']
            v=record.get('globalUnitVector',[0,0,-1])
            cases.append({'id':name,'type':{'D':'dead','W':'wind','Q':'live'}[name],
                'loads':[{'type':'distributed','element':e,'wx':q*v[0],'wz':q*v[2]} for e in d['loadedMembers']]})
        m['load_cases']=cases
    else:m['load_cases']=read(folder/'loads.json')
    return m


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--edition',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    ed=a.edition.resolve();manifest=read(ed/'manifest.json');reviews=[];comparisons=[]
    for case in manifest['cases']:
        if case['origin']!='new':continue
        m=None
        for i,t in enumerate(case['turns'],1):
            folder=ed/t['public'];pub=read(folder/'task.json');ref=read(ed/t['private'])
            if i==1:m=initial(folder,case['id'])
            else:
                assert not any((folder/n).exists() for n in ['nodes.csv','members.csv','loads.json','sections.json','analysis-control.json']), 'Full-state interaction leak'
                if case['id']=='P30-INT-007':
                    sec=next(s for s in m['sections'] if s['id']=='C')
                    if i==2:sec['properties']['A']*=1.25
                    if i==3:sec['properties']['A']/=1.25;m['load_cases'][1]['loads'][0]['fx']=11
                if case['id']=='P30-INT-009':
                    if i==2:
                        for load in m['load_cases'][1]['loads']:load['wz']*=1.2
                    if i==3:section(m,.4,1.)
                    if i==4:
                        for load in m['load_cases'][1]['loads']:load['wz']/=1.2
                if case['id']=='P30-INT-010':
                    if i==2:
                        for load in m['load_cases'][2]['loads']:load['wz']*=1.15
                    if i==4:
                        for load in m['load_cases'][2]['loads']:load['wz']/=1.15
            if ref['kind']!='clarify':comparisons.append({'id':case['id']+'/'+t['id'],'actual':deepcopy(m),'expected':ref['model']})
            if (folder/'analysis-parameters.json').exists():
                par=read(folder/'analysis-parameters.json')
                file=par.pop('groundMotionFile',None)
                if file:par['groundMotion']=[float(r['acceleration']) for r in csvrows(folder/file)]
                assert par==ref['parameters'],'Public parameters differ from reference'
            if ref['kind']=='scheme':
                assert pub['constraint']==ref['constraint'] and pub['schemeSelections']==ref['schemeSelections']
                catalog=read(ed/case['turns'][0]['public']/'schemes.json')
                assert {s['id'] for s in catalog}=={s['id'] for s in ref['schemeTruth']}
                for s in catalog:
                    variant=deepcopy(m);section(variant,s['b'],s['h'])
                    properties=next(v for v in variant['sections'] if v['id']==s['section'])['properties']
                    assert properties.keys()==s['properties'].keys() and all(math.isclose(v,s['properties'][k],rel_tol=1e-14,abs_tol=1e-20) for k,v in properties.items())
                    truth=next(v for v in ref['schemeTruth'] if v['id']==s['id'])
                    comparisons.append({'id':case['id']+'/'+t['id']+'/scheme-'+s['id'],'actual':variant,'expected':truth['model']})
            reviews.append({'caseId':case['id'],'turnId':t['id'],'source':'released schedules + manual raster transcription + explicit patch reconstruction','reviewer':'local author/operator; not blind','passed':True})
    code="const fs=require('fs'),{physical}=require(process.argv[1]);const rows=JSON.parse(fs.readFileSync(0));const bad=rows.map(r=>({id:r.id,...physical(r.actual,r.expected)})).filter(r=>!r.pass);console.log(JSON.stringify(bad));process.exitCode=bad.length?1:0;"
    result=subprocess.run(['node','-e',code,str(Path(__file__).with_name('evaluate.cjs').resolve())],input=json.dumps(comparisons),capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    report={'manifestSha256':hashlib.sha256((ed/'manifest.json').read_bytes()).hexdigest(),'review':'local-source-guided-not-blind',
            'newCases':12,'newTurns':len(reviews),'modelComparisons':len(comparisons),'allPassed':True,'rows':reviews}
    with a.output.open('x') as f:f.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
