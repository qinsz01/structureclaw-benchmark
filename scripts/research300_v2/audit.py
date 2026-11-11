"""Source-guided, non-blind audit of the full v2 edition.

Counts are checked against actual models/references/files, not task titles.
Public table reconstruction never imports the authoring model/task generator.
Raster geometry can be reviewed through separately supplied manual transcriptions;
absence of those transcriptions is reported explicitly, never called a blind pass.
"""
from __future__ import annotations

import argparse
import os
from collections import Counter,defaultdict
from copy import deepcopy
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

from models import topology_fingerprint

ROOT=Path(__file__).resolve().parents[2]
EXPECTED_LEVELS={'L1':60,'L2':120,'L3':90,'L4':30}
EXPECTED_FAMILIES={'STD':100,'MM':100,'INT':100}
EXPECTED_ENGINES={'OpenSees':270,'PKPM':15,'YJK':15}
EXPECTED_INT_TURNS={'L1':2,'L2':3,'L3':4,'L4':6}
SUT_COMMIT='db3c0b1da44fe668a6037a6c2e7f068d14354539'
# Public protocol copied from the pinned SUT. The public package initializer
# intentionally stays empty; these bindings avoid an untracked authoring cache.
SCHEMA_SHA256={
 'structure_protocol/__init__.py':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
 'structure_protocol/structure_model_v2.py':'eb10f3c473820dd49ded3bdc62adc8ca25adf3a42474cb2d482521077c36c3b6',
 'structure_protocol/design_properties.py':'6fddc2d8b1ea4799d1f7102599d73c9949ee3c586668e2ae7e6eee8e8a65b0a7',
 'structure_protocol/section_properties.py':'4b8b92d620a182e952864676decbf31498c0e42e58625663b584c8b9107c7319',
 'structure_protocol/load_contract.py':'15563a91e68f00f7174ad93828d3f1e8e5e82632cc9e94b176d4d3ac28d2a90e',
}


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def rows(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))
def inside(root,name):
    path=(root/name).resolve()
    if not path.is_relative_to(root):raise ValueError('Path escapes frozen edition: '+str(name))
    return path


def geometry_objects(value):
    found=[]
    if isinstance(value,dict):
        if {'x','y','z'}<=value.keys() and ('id' in value or 'node' in value):found.append(value)
        for item in value.values():found.extend(geometry_objects(item))
    elif isinstance(value,list):
        for item in value:found.extend(geometry_objects(item))
    return found


def full_models(value):
    if isinstance(value,dict):
        if {'nodes','elements','materials','sections'}<=value.keys():return True
        return any(full_models(v) for v in value.values())
    return isinstance(value,list) and any(full_models(v) for v in value)


def read_dxf_geometry(path):
    """Read issued ASCII DXF entities; never consult private coordinates."""
    raw=path.read_text().splitlines()
    if len(raw)%2:raise ValueError('DXF has an incomplete group-code pair')
    entities=[];entity={};active=False
    for code,value in zip(raw[::2],raw[1::2]):
        code=int(code.strip())
        if code==2 and value=='ENTITIES':active=True;continue
        if code==0:
            if entity:entities.append(entity)
            entity={0:value} if active and value not in ['ENDSEC','EOF'] else {}
            if value=='ENDSEC':active=False
        elif entity:entity[code]=value
    def point(e):return tuple(float(e.get(c,0)) for c in [10,20,30])
    points=Counter(point(e) for e in entities if e[0]=='POINT' and e.get(8)=='NODE')
    nodes={};restraints={};coordinates={};stories=[];node_stories={};lines=[]
    for e in entities:
        if e[0]=='LINE' and e.get(8)=='STRUCT':lines.append((point(e),tuple(float(e.get(c,0)) for c in [11,21,31])))
        if e[0]!='TEXT':continue
        layer=e.get(8);value=e.get(1,'')
        if layer=='NODE_ID':
            if value in nodes:raise ValueError('DXF repeats a node ID')
            xyz=point(e)
            if points[xyz]!=1:raise ValueError('DXF node label does not bind one POINT')
            nodes[value]={'id':value,**dict(zip('xyz',xyz))}
        elif layer=='RESTRAINT':
            nid,bits=value.split(' FIXED=')
            if len(bits)!=6 or set(bits)-{'0','1'}:raise ValueError('Invalid DXF support mask')
            restraints[nid]=[b=='1' for b in bits]
        elif layer=='NODE_COORD':
            nid,values=value.split(' XYZ_m=');coordinates[nid]=tuple(float(v) for v in values.split(','))
        elif layer=='NODE_STORY':
            nid,story=value.split(' STORY=');node_stories[nid]=story
        elif layer=='STORY':stories.append(json.loads(value))
    if not nodes or len(nodes)!=sum(points.values()) or nodes.keys()!=restraints.keys() or nodes.keys()!=coordinates.keys():
        raise ValueError('DXF node coordinates/support labels are incomplete')
    for nid,node in nodes.items():
        if len(coordinates[nid])!=3 or any(not math.isclose(node[k],v,rel_tol=0,abs_tol=1e-9) for k,v in zip('xyz',coordinates[nid])):
            raise ValueError('DXF coordinate text disagrees with POINT')
        node['restraints']=restraints[nid]
        if nid in node_stories:node['story']=node_stories[nid]
    return list(nodes.values()),stories,lines


def reconstruct_initial(public,manual=None):
    """Rebuild only from issued schedules/recipe and optional manual drawing read."""
    convention=read(public/'model-convention.json')
    dxf_stories=None;dxf_lines=None
    if (public/'nodes.csv').exists():
        nodes=[]
        for r in rows(public/'nodes.csv'):
            node={'id':r['node'],**{k:float(r[k+'_m']) for k in ['x','y','z']},
                  'restraints':[bool(int(r[k+'_fixed'])) for k in ['ux','uy','uz','rx','ry','rz']]}
            if r.get('mass_tonne','')!='':node['mass']=float(r['mass_tonne'])
            if r.get('story'):node['story']=r['story']
            nodes.append(node)
    elif (public/'geometry.dxf').exists():
        nodes,dxf_stories,dxf_lines=read_dxf_geometry(public/'geometry.dxf')
        if (public/'mass.csv').exists():
            masses={r['node']:float(r['mass_tonne']) for r in rows(public/'mass.csv') if r.get('mass_tonne','')!=''}
            for n in nodes:
                if n['id'] in masses:n['mass']=masses[n['id']]
    elif manual:
        if manual.get('reviewMode') not in ['manual-image-transcription','pixel-template-transcription','pixel-ocr-with-manual-corrections']:
            raise ValueError('Geometry transcription must identify its actual review mode')
        for name,digest in manual.get('imageHashes',{}).items():
            if sha(public/name)!=digest:raise ValueError('Manual geometry image binding differs: '+name)
        if not manual.get('imageHashes'):raise ValueError('Manual geometry needs reviewed image hashes')
        nodes=deepcopy(manual['nodes'])
        if (public/'mass.csv').exists():
            masses={r['node']:float(r['mass_tonne']) for r in rows(public/'mass.csv') if r.get('mass_tonne','')!=''}
            for n in nodes:
                if n['id'] in masses:n['mass']=masses[n['id']]
    else:raise ValueError('Geometry requires manual raster/DXF review; no CSV substitute exists')
    if (public/'node-extra.json').exists():
        extra=read(public/'node-extra.json')
        for n in nodes:n.update(extra.get(n['id'],{}))
    elements=[]
    for r in rows(public/'members.csv'):
        e={'id':r['member'],'nodes':[r['i'],r['j']],'type':r['kind'],'material':r['material'],'section':r['section']}
        if r.get('roll_deg','')!='':e['rotation_angle']=float(r['roll_deg'])
        for field,column in [('releases','local_bending_releases'),('offsets','offsets')]:
            value=json.loads(r.get(column) or '{}')
            if value:e[field]=value
        if r.get('story'):e['story']=r['story']
        elements.append(e)
    if (public/'element-extra.json').exists():
        extra=read(public/'element-extra.json')
        for e in elements:e.update(extra.get(e['id'],{}))
    if dxf_lines is not None:
        lookup={n['id']:tuple(n[k] for k in 'xyz') for n in nodes}
        edge=lambda pair:tuple(sorted(tuple(round(v,8) for v in xyz) for xyz in pair))
        expected=Counter(edge([lookup[nid] for nid in e['nodes']]) for e in elements)
        if Counter(edge(pair) for pair in dxf_lines)!=expected:raise ValueError('DXF STRUCT lines disagree with member endpoint schedule')
    materials=read(public/'materials.json')
    # The redundant human-readable material table must agree with its full record.
    material_map={m['id']:m for m in materials}
    for r in rows(public/'materials.csv'):
        for column,key in [('E_MPa','E'),('G_MPa','G'),('nu','nu'),('rho_kg_per_m3','rho')]:
            if r.get(column,'')!='' and not math.isclose(float(r[column]),material_map[r['id']][key],rel_tol=1e-12,abs_tol=1e-14):
                raise ValueError('Material CSV/JSON conflict: '+r['id']+'/'+key)
    model={**convention,'nodes':nodes,'elements':elements,'materials':materials,
           'sections':read(public/'sections.json'),'analysis_control':read(public/'analysis-control.json'),
           'load_combinations':read(public/'combinations.json')}
    if (public/'model-extra.json').exists():model.update(read(public/'model-extra.json'))
    for field in ['metadata','stories']:
        if (public/(field+'.json')).exists():model[field]=read(public/(field+'.json'))
        elif field=='stories' and dxf_stories:model[field]=dxf_stories
        elif field=='stories' and manual and 'stories' in manual:model[field]=deepcopy(manual['stories'])
    if (public/'load-recipe.json').exists():
        recipe=read(public/'load-recipe.json');cases=[]
        for case in recipe['cases']:
            loads=[]
            for term in case['terms']:
                if term['kind']=='surface-on-members':
                    q=term['pressureKNM2']*term['tributaryWidthM'];v=term['globalUnitVector']
                    if len(v)!=3:raise ValueError('Surface load vector must have three components')
                    for eid in term['members']:
                        loads.append({'type':'distributed','element':eid,'reference_frame':'global',
                                      **{k:q*x for k,x in zip(['wx','wy','wz'],v)}})
                elif term['kind']=='nodal':
                    loads.append({'type':'nodal','reference_frame':'global',
                                  **{k:v for k,v in term.items() if k!='kind'}})
                else:raise ValueError('Unreviewed public load recipe: '+str(term['kind']))
            for i,load in enumerate(loads,1):load.setdefault('id',case['id']+'-'+str(i))
            cases.append({'id':case['id'],'type':case['type'],'loads':loads})
        model['load_cases']=cases
    else:model['load_cases']=read(public/'loads.json')
    return model


def apply_change(model,order,history):
    """Interpret only the documented public edit language, independently."""
    model=deepcopy(model);constraints=[]
    force_keys={f'{p}{axis}{suffix}' for p in ['f','m','w'] for axis in ['x','y','z'] for suffix in ['','_start','_end']}
    def scale_force(value,factor):
        if isinstance(value,list):return [scale_force(v,factor) for v in value]
        if isinstance(value,dict):
            return {k:v*factor if k in force_keys and isinstance(v,(int,float)) else scale_force(v,factor) for k,v in value.items()}
        return value
    operations=order if isinstance(order,list) else order.get('operations',order.get('patch',[]))
    if not isinstance(operations,list):raise ValueError('Change operations must be an array')
    for op in operations:
        action=op['op']
        if action in ['replace','add','remove']:
            pointer=op['path'];parts=[s.replace('~1','/').replace('~0','~') for s in pointer.strip('/').split('/')]
            if not pointer.startswith('/') or not parts:raise ValueError('Invalid JSON pointer')
            target=model
            for part in parts[:-1]:target=target[int(part)] if isinstance(target,list) else target[part]
            key=parts[-1]
            if isinstance(target,list):
                i=len(target) if key=='-' else int(key)
                if action=='remove':del target[i]
                elif action=='add':target.insert(i,deepcopy(op['value']))
                else:target[i]=deepcopy(op['value'])
            elif action=='remove':del target[key]
            else:target[key]=deepcopy(op['value'])
        elif action=='scale-load-case':
            case=next(c for c in model['load_cases'] if c['id']==op['caseId'])
            case['loads']=[load if load.get('type')=='displacement' else scale_force(load,op['factor']) for load in case['loads']]
        elif action=='restore-load-case':
            original=history[op.get('fromTurn','t1')]
            source=next(c for c in original['load_cases'] if c['id']==op['caseId'])
            i=next(i for i,c in enumerate(model['load_cases']) if c['id']==op['caseId']);model['load_cases'][i]=deepcopy(source)
        elif action=='resize-section':
            section=next(s for s in model['sections'] if s['id']==op['sectionId']);shape=section.get('shape')
            if shape and shape.get('kind')=='rectangular':
                shape['B']*=op['widthFactor'];shape['H']*=op['depthFactor'];b=shape['B']/1000;h=shape['H']/1000
                large,small=max(b,h),min(b,h)
                section['properties'].update(A=b*h,Iy=b*h**3/12,Iz=h*b**3/12,
                  J=large*small**3*(1/3-.21*small/large*(1-small**4/(12*large**4))))
            elif 'propertiesFactor' in op:
                section['properties']={k:v*op['propertiesFactor'] for k,v in section['properties'].items()}
            else:raise ValueError('Rectangular resize needs shape or explicit propertiesFactor')
        elif action=='scale-nodal-masses':
            for node in model['nodes']:
                if 'mass' in node:node['mass']*=op['factor']
        elif action=='restore-nodal-masses':
            original={n['id']:n for n in history[op.get('fromTurn','t1')]['nodes']}
            for node in model['nodes']:
                if 'mass' in original[node['id']]:node['mass']=original[node['id']]['mass']
                else:node.pop('mass',None)
        elif action=='set-constraint-limit':constraints.append(op['absoluteLimit'])
        else:raise ValueError('Unreviewed public change operation: '+str(action))
    return model,constraints


def _flat(value,prefix=''):
    if isinstance(value,dict):
        return {path:v for k,x in value.items() for path,v in _flat(x,prefix+'/'+str(k)).items()}
    if isinstance(value,list):
        return {path:v for i,x in enumerate(value) for path,v in _flat(x,prefix+'/'+str(i)).items()}
    return {prefix:value}


def _same(a,b):
    if isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) and not isinstance(b,bool):
        return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)
    return a==b


def reconstruct_parameters(public):
    parameters=read(public/'analysis-parameters.json')
    if 'groundMotionFile' in parameters:
        filename=parameters.pop('groundMotionFile');record=rows(inside(public.resolve(),filename))
        if [int(r['sample']) for r in record]!=list(range(len(record))):raise ValueError('Excitation sample indices must be contiguous from zero')
        parameters['groundMotion']=[float(r['acceleration']) for r in record]
    return parameters


def features(references,public_tasks,public_dirs):
    selections=[];kinds=set();models=[];issue_paths=set();derived=0;scheme_count=0
    for ref in references:
        kinds.add(ref['kind']);request_map={q['id']:q for q in ref.get('requests',[])};request_ids=set(request_map)
        valid_derived=[q for q in ref.get('derived',[]) if q.get('operation') in ['difference','sum','max','min','max_abs']
                       and len(set(q.get('operands',[])))>=2 and set(q['operands'])<=request_ids
                       and {request_map[operand].get('unit') for operand in q['operands']}=={q.get('unit')}]
        derived=max(derived,len(valid_derived))
        issue_paths.update(ref.get('expectedIssuePaths',[]))
        selected={json.dumps(q['selection'],sort_keys=True) for q in ref.get('requests',[]) if q.get('selection')}
        selected.update('combination:'+s for s in ref.get('schemeSelections',[]));selections.append(len(selected))
        scheme_count=max(scheme_count,len(ref.get('schemes',[])))
        if ref.get('model'):models.append(ref['model'])
    changes=[];selective_undo=False;categories=set()
    flattened=[_flat(m) for m in models]
    for previous,current in zip(flattened,flattened[1:]):
        changed={p for p in previous.keys()|current.keys() if not _same(previous.get(p),current.get(p))}
        changes.append(len(changed));categories.update(p.split('/')[1] for p in changed)
    if len(flattened)>=3:
        original=flattened[0]
        for before,after in zip(flattened[1:],flattened[2:]):
            restored=any(not _same(before.get(p),original[p]) and _same(after.get(p),original[p]) for p in original)
            retained=any(not _same(before.get(p),original[p]) and _same(after.get(p),before.get(p)) for p in original)
            selective_undo|=restored and retained
    surface=any((d/'load-recipe.json').exists() and any(t.get('kind')=='surface-on-members' for c in read(d/'load-recipe.json')['cases'] for t in c['terms']) for d in public_dirs)
    issue_categories={p.strip('/').split('/')[0] for p in issue_paths}
    extra=[]
    if max(selections,default=0)>=2:extra.append('multiple_actual_selections')
    if derived:extra.append('signed_derived_outputs')
    if issue_paths:extra.append('diagnose_and_correct_physical_input')
    if 'modal' in kinds:extra.append('explicit_mass_modal_analysis')
    if 'transient' in kinds:extra.append('explicit_record_linear_transient')
    if any(r.get('kind')=='modal' and r.get('requireShapes') and r.get('parameters',{}).get('numModes',0)>=2
           and any(q.get('path',[])[-1:] == ['effectiveMass'] for q in r.get('requests',[]))
           and any(n.get('mass',0)>0 for n in r.get('model',{}).get('nodes',[])) for r in references):
        extra.append('multiple_mode_shapes_and_effective_masses')
    if any(r.get('kind')=='transient' and r.get('parameters',{}).get('groundMotion')
           and any(q.get('operation')=='max_abs' and isinstance(q.get('time'),(int,float)) for q in r.get('requests',[])) for r in references):
        extra.append('signed_record_peak_and_occurrence_time')
    if 'scheme' in kinds:extra.append('finite_feasible_scheme_selection')
    if surface:extra.append('surface_to_member_load_transfer')
    if any(changes):extra.append('retain_and_update_interaction_state')
    if selective_undo:extra.append('selective_undo')
    return {'kinds':sorted(kinds),'maxActualSelections':max(selections,default=0),'derivedOutputs':derived,
            'expectedIssuePaths':sorted(issue_paths),'issueCategories':sorted(issue_categories),'maxSchemes':scheme_count,
            'surfaceLoadTransfer':surface,'stateChangeCounts':changes,'changedPhysicalCategories':sorted(categories),
            'selectiveUndo':selective_undo,'actualAdditionalOperations':extra}


def audit(edition,registry_path,manual_path=None,schema_root=None,schema_python=None):
    manifest=read(edition/'manifest.json');cases=manifest['cases'];checks=[];case_rows=[];comparisons=[]
    def check(name,passed,detail=None,severity='mandatory'):checks.append({'name':name,'passed':bool(passed),'detail':detail,'severity':severity})
    registry={s['sourceId']:s for s in read(registry_path)['sources']}
    manual=read(manual_path) if manual_path else {}
    check('case_count',len(cases)==300,len(cases))
    check('pinned_sut_commit',manifest.get('sutCommit')==SUT_COMMIT)
    check('unique_case_ids',len({c['id'] for c in cases})==300)
    for name,key,expected in [('family_distribution','family',EXPECTED_FAMILIES),('level_distribution','level',EXPECTED_LEVELS),('engine_distribution','engine',EXPECTED_ENGINES)]:
        actual=dict(Counter(c.get(key) for c in cases));check(name,actual==expected,actual)
    split_counts=dict(Counter(c.get('split') for c in cases));check('split_distribution',split_counts=={'dev':60,'test':240},split_counts)
    paths=[f['path'] for f in manifest['files']];check('unique_file_manifest',len(paths)==len(set(paths)))
    hashed=set(paths)
    actual_files={p.relative_to(edition).as_posix() for p in edition.rglob('*') if p.is_file() and p!=edition/'manifest.json'}
    check('complete_file_manifest',hashed==actual_files,{'missing':sorted(actual_files-hashed),'nonexistent':sorted(hashed-actual_files)})
    for f in manifest['files']:
        p=inside(edition,f['path']);check('file:'+f['path'],p.is_file() and not p.is_symlink() and sha(p)==f['sha256'])
    groups={'sourceProjectGroup':defaultdict(set),'baseModelGroup':defaultdict(set)}
    fingerprints=defaultdict(list);engineering=[];real=[];source_counts=Counter();reconstruction=[];case_models={};case_details={};schema_models=[];reference_check_rows=[]
    for case in cases:
        cid=case['id'];level=case.get('level');refs=[];pubs=[];dirs=[];first_model=None
        before=len(checks)
        check(cid+':difficulty_evidence',isinstance(case.get('difficultyEvidence'),list) and bool(case['difficultyEvidence'])
              and all(isinstance(v,str) and len(v.strip())>2 for v in case['difficultyEvidence']))
        check(cid+':base_group',isinstance(case.get('baseModelGroup'),str) and bool(case['baseModelGroup']))
        for name in groups:
            if case.get(name):groups[name][case[name]].add(case.get('split'))
        count=len(case['turns']);check(cid+':turn_count',count==(EXPECTED_INT_TURNS.get(level) if case['family']=='INT' else 1),count)
        check(cid+':unique_turn_ids',len({t['id'] for t in case['turns']})==count)
        for i,t in enumerate(case['turns']):
            public=inside(edition,t['public']);ref=read(inside(edition,t['private']));pub=read(public/'task.json')
            refs.append(ref);pubs.append(pub);dirs.append(public)
            if first_model is None and ref.get('model'):first_model=ref['model']
            if ref.get('model'):schema_models.append({'id':cid+'/'+t['id'],'model':ref['model']})
            evidence_rows=list(ref.get('referenceChecks',[]))
            for scheme in ref.get('schemeTruth',[]):
                if scheme.get('model'):schema_models.append({'id':cid+'/'+t['id']+'/scheme:'+scheme['id'],'model':scheme['model']})
                evidence_rows.extend({'schemeId':scheme['id'],**item} for item in scheme.get('referenceChecks',[]))
            for j,evidence in enumerate(evidence_rows):
                numbers={p:v for p,v in _flat(evidence).items() if isinstance(v,(int,float)) and not isinstance(v,bool)}
                check(cid+'/'+t['id']+':reference_check_finite:'+str(j),all(math.isfinite(v) for v in numbers.values()))
                if 'freeResidual' in evidence:check(cid+'/'+t['id']+':reference_residual_absolute_bound:'+str(j),0<=evidence['freeResidual']<=1e-7)
                if 'forceMomentBalance' in evidence:check(cid+'/'+t['id']+':reference_balance_absolute_bound:'+str(j),len(evidence['forceMomentBalance'])==6 and max(map(abs,evidence['forceMomentBalance']))<=1e-7)
                if evidence.get('minimumScaledPivot') is not None:check(cid+'/'+t['id']+':reference_positive_pivot:'+str(j),evidence['minimumScaledPivot']>=1e-12)
                reference_check_rows.append({'id':cid+'/'+t['id'],'index':j,**evidence})
            check(cid+'/'+t['id']+':reference_values_finite',all(isinstance(q.get('value'),(int,float)) and math.isfinite(q['value']) for q in ref.get('requests',[])))
            if ref.get('parameters') is not None:
                try:
                    actual=_flat(reconstruct_parameters(public));expected=_flat(ref['parameters'])
                    check(cid+'/'+t['id']+':public_analysis_parameters',actual.keys()==expected.keys() and all(_same(actual[k],expected[k]) for k in expected))
                except (KeyError,ValueError,FileNotFoundError) as exc:check(cid+'/'+t['id']+':public_analysis_parameters',False,str(exc))
            public_request_keys={'id','selection','location','component','unit','path','operation','description'}
            check(cid+'/'+t['id']+':public_request_identity',pub.get('requests',[])==[{k:v for k,v in q.items() if k in public_request_keys} for q in ref.get('requests',[])])
            check(cid+'/'+t['id']+':public_report_ids',pub.get('reportIds')==ref.get('reportIds',[q['id'] for q in ref.get('requests',[])]))
            for q in pub.get('requests',[]):check(cid+'/'+t['id']+':no_request_truth',not(set(q)&{'value','tolerance','time','rawTrace','nativeStatus'}))
            for q in pub.get('derived',[]):check(cid+'/'+t['id']+':no_derived_truth',not(set(q)&{'value','governingOperand','governingSelection','coGoverningOperands'}))
            for p in public.rglob('*'):
                if not p.is_file():continue
                name=p.relative_to(edition).as_posix();check('public_manifest:'+name,name in hashed and not p.is_symlink())
                check('no_authoring_svg:'+name,p.suffix.lower()!='.svg')
                if p.suffix.lower()=='.json':
                    data=read(p)
                    if case['family']=='MM':check('mm_no_coordinate_json:'+name,not geometry_objects(data))
                    if i:check('interaction_no_full_snapshot:'+name,not full_models(data))
            if case['family']=='MM':
                check(cid+'/'+t['id']+':visual_geometry',any(p.suffix.lower() in ['.png','.dxf'] for p in public.iterdir()))
                check(cid+'/'+t['id']+':no_nodes_csv',not (public/'nodes.csv').exists())
            if case['family']=='INT' and i:
                forbidden=['nodes.csv','members.csv','sections.json','loads.json','analysis-control.json','materials.json','metadata.json','stories.json','suspect-model.json']
                check(cid+'/'+t['id']+':patch_only',not any((public/n).exists() for n in forbidden))
        check(cid+':has_computed_model',first_model is not None)
        if first_model:
            fingerprint=topology_fingerprint(first_model);fingerprints[fingerprint].append(cid)
            case_models[cid]=first_model
            case_details[cid]={k:case.get(k) for k in ['origin','baseModelGroup','sourceProjectGroup','split']}
            if case.get('topologyFingerprint'):check(cid+':topology_binding',case['topologyFingerprint']==fingerprint)
        feature=features(refs,pubs,dirs);ops=feature['actualAdditionalOperations'];maxsel=feature['maxActualSelections']
        if level=='L1':sufficient=not set(feature['kinds'])&{'scheme','transient','modal'} and maxsel<=1 and not feature['expectedIssuePaths']
        elif level=='L2':sufficient=len(ops)>=1
        elif level=='L3':sufficient=len(ops)>=2
        elif level=='L4':
            scheme='scheme' in feature['kinds'] and feature['maxSchemes']>=2 and maxsel>=2
            review=len(feature['expectedIssuePaths'])>=3 and len(feature['issueCategories'])>=3 and maxsel>=3 and feature['derivedOutputs']>=1
            interactive=case['family']=='INT' and count==6 and feature['selectiveUndo'] and len(feature['changedPhysicalCategories'])>=2
            sufficient=scheme or review or interactive
        else:sufficient=False
        check(cid+':level_has_actual_operations',sufficient,feature)
        source_id=case.get('sourceId')
        if source_id:
            engineering.append(cid);source_counts[source_id]+=1;source=registry.get(source_id)
            check(cid+':known_source',source is not None)
            if source:
                if source.get('realProjectEligible'):real.append(cid)
                check(cid+':source_group',case.get('sourceProjectGroup') in [source_id,source.get('projectGroup')])
                basis=case.get('sourceBasis') or (read(dirs[0]/'source-basis.json') if (dirs[0]/'source-basis.json').exists() else None)
                check(cid+':source_basis',isinstance(basis,dict) and bool(basis.get('facts')) and bool(basis.get('authoringAssumptions') or basis.get('authoredAssumptions') or basis.get('adaptation') or basis.get('authoredScope') or basis.get('subproblems')))
                if isinstance(basis,dict):
                    authoritative={f['factId']:f for f in source['facts']}
                    facts=basis.get('facts',[])
                    check(cid+':source_fact_integrity',bool(facts) and all(f.get('factId') in authoritative and f==authoritative[f['factId']] for f in facts)
                          and basis.get('sourceId')==source_id and basis.get('url')==source.get('url'))
                if isinstance(basis,dict) and basis.get('usedFactIds'):
                    known={f['factId'] for f in source['facts']};check(cid+':fact_bindings',set(basis['usedFactIds'])<=known)
        # Reconstruction is attempted wherever the public schedules suffice.
        initial_ref=refs[0]
        if (dirs[0]/'model-convention.json').exists():
            try:
                model=reconstruct_initial(dirs[0],manual.get(cid));history={}
                for t,ref,public in zip(case['turns'],refs,dirs):
                    if (public/'change-order.json').exists():
                        model,limits=apply_change(model,read(public/'change-order.json'),history)
                        if limits:check(cid+'/'+t['id']+':constraint_update',ref.get('constraint',{}).get('absoluteLimit')==limits[-1])
                    if ref.get('model'):comparisons.append({'id':cid+'/'+t['id'],'actual':deepcopy(model),'expected':ref['model']})
                    history[t['id']]=deepcopy(model)
                reconstruction.append({'caseId':cid,'status':'reconstructed','turns':len(case['turns']),
                                       'method':'public tables/recipe and public patch interpretation'+(' + '+manual[cid]['reviewMode'] if cid in manual else ' + independently parsed DXF entities' if (dirs[0]/'geometry.dxf').exists() else '')})
            except ValueError as exc:
                if case['family']=='MM' and cid not in manual and not (dirs[0]/'geometry.dxf').exists():reconstruction.append({'caseId':cid,'status':'manual-geometry-review-pending','reason':str(exc)})
                else:check(cid+':public_reconstruction',False,str(exc))
            except (KeyError,FileNotFoundError) as exc:check(cid+':public_reconstruction',False,str(exc))
        else:reconstruction.append({'caseId':cid,'status':'not-covered-by-table-reconstructor','reason':'Legacy text packet or initial clarification; no completeness claim'})
        case_rows.append({'caseId':cid,'level':level,'features':feature,'passed':all(c['passed'] for c in checks[before:])})
    for field,mapping in groups.items():
        leaks={k:sorted(v) for k,v in mapping.items() if len(v)>1};check(field+':split_isolation',not leaks,leaks)
    check('engineering_adaptation_count',len(engineering)==60,len(engineering))
    check('real_project_adaptation_count',len(real)==60,len(real))
    check('source_project_case_cap',all(n<=6 for n in source_counts.values()),dict(source_counts))
    check('at_least_180_topologies',len(fingerprints)>=180,len(fingerprints))
    repeated={k:v for k,v in fingerprints.items() if len(v)>3}
    check('topology_case_cap',not repeated,{'target':3,'groups':repeated,'disposition':'Diversity exception requiring explicit documentation; previous native-qualified models retained unchanged.'},'documented-diversity-target')
    origin_stats={}
    for origin in sorted({d['origin'] for d in case_details.values()}):
        counts=Counter(fp for fp,ids in fingerprints.items() for cid in ids if case_details[cid]['origin']==origin)
        origin_stats[origin]={'cases':sum(counts.values()),'uniqueTopologies':len(counts),'maximumCasesPerTopology':max(counts.values(),default=0)}
    def geometry_signature(model):
        nodes=sorted(model['nodes'],key=lambda n:tuple(n[k] for k in 'xyz'))
        ids={n['id']:i for i,n in enumerate(nodes)}
        return {'nodes':[(n['x'],n['y'],n['z'],tuple(n['restraints'])) for n in nodes],
                'edges':sorted((e['type'],*sorted(ids[n] for n in e['nodes'])) for e in model['elements'])}
    topology_pairs=[]
    for fp,ids in fingerprints.items():
        for i,a in enumerate(ids):
            for b in ids[i+1:]:
                topology_pairs.append({'id':'topology:'+a+':'+b,'actual':case_models[a],'expected':case_models[b],
                   'fingerprint':fp,'a':a,'b':b,'sameGeometry':geometry_signature(case_models[a])==geometry_signature(case_models[b]),
                   'crossSplit':case_details[a]['split']!=case_details[b]['split']})
    if comparisons or topology_pairs:
        code="const fs=require('fs'),{physical}=require(process.argv[1]);const rows=JSON.parse(fs.readFileSync(0));const result=rows.map(r=>({id:r.id,...physical(r.actual,r.expected)}));console.log(JSON.stringify(result.map(r=>({id:r.id,passed:r.pass,failures:r.failures}))));"
        result=subprocess.run(['node','-e',code,str(Path(__file__).with_name('evaluate.cjs'))],input=json.dumps(comparisons+topology_pairs),capture_output=True,text=True,timeout=600)
        check('public_reconstruction_comparator',result.returncode==0,result.stderr)
        all_comparison_rows=json.loads(result.stdout) if result.returncode==0 else []
        comparison_rows=all_comparison_rows[:len(comparisons)]
        for row in comparison_rows:check(row['id']+':reconstructed_physical_model',row['passed'],row['failures'])
    else:comparison_rows=[];all_comparison_rows=[]
    by_pair={r['id']:r for r in all_comparison_rows[len(comparisons):]};pair_rows=[]
    for pair in topology_pairs:
        outcome=by_pair.get(pair['id'],{})
        pair_rows.append({k:pair[k] for k in ['fingerprint','a','b','sameGeometry','crossSplit']}|
                         {'physicallyEquivalent':outcome.get('passed'),'physicsDifferenceCount':len(outcome.get('failures',[]))})
    clone_leaks=[p for p in pair_rows if p['crossSplit'] and p['physicallyEquivalent']]
    check('physical_clone_split_isolation',not clone_leaks,clone_leaks)
    schema_result={'attempted':0,'passed':0,'scope':'schema only; zero native solver calls','status':'not-run'}
    if schema_root:
        schema_root=Path(schema_root).resolve()
        check('pinned_schema_source_binding',all((schema_root/name).is_file() and sha(schema_root/name)==digest for name,digest in SCHEMA_SHA256.items()))
        code="import sys,json;sys.path.insert(0,sys.argv[1]);from structure_protocol.structure_model_v2 import StructureModelV2\nrows=json.load(sys.stdin);results=[]\nfor row in rows:\n try:StructureModelV2.model_validate(row['model']);results.append({'id':row['id'],'passed':True})\n except Exception as exc:results.append({'id':row['id'],'passed':False,'error':str(exc)})\nprint(json.dumps(results))"
        process=subprocess.run([schema_python or sys.executable,'-c',code,str(schema_root)],input=json.dumps(schema_models),capture_output=True,text=True,timeout=600)
        check('pinned_schema_validator',process.returncode==0,process.stderr)
        schema_rows=json.loads(process.stdout) if process.returncode==0 else []
        for row in schema_rows:check(row['id']+':pinned_schema_valid',row['passed'],row.get('error'))
        schema_result.update(attempted=len(schema_models),passed=sum(r['passed'] for r in schema_rows),status='completed' if process.returncode==0 else 'failed',rows=schema_rows)
    guard=read(Path(os.environ.get('SCLAW_BENCH_ARCHIVE', ROOT)).expanduser()/'docs/implementation/reviews/codex-diversity300-20261027/source-integrity.json')['files']
    for row in guard:check('legacy_frozen:'+row['path'],sha(ROOT/row['path'])==row['sha256'])
    failed=[c for c in checks if not c['passed']]
    for row in case_rows:
        cid=row['caseId']
        row['passed'] &= not any(c['name'].startswith(cid+':') or c['name'].startswith(cid+'/') for c in failed)
    residual_rows=[r for r in reference_check_rows if 'freeResidual' in r]
    balance_rows=[r for r in reference_check_rows if 'forceMomentBalance' in r]
    pivots=[r['minimumScaledPivot'] for r in reference_check_rows if r.get('minimumScaledPivot') is not None]
    reference_summary={'count':len(reference_check_rows),'methodCounts':dict(Counter(r.get('method') for r in reference_check_rows)),
       'recordedFreeResiduals':len(residual_rows),'maximumFreeResidual':max((r['freeResidual'] for r in residual_rows),default=None),
       'recordedForceMomentBalances':len(balance_rows),'maximumForceMomentImbalance':max((abs(v) for r in balance_rows for v in r['forceMomentBalance']),default=None),
       'minimumScaledPivot':min(pivots,default=None),
       'absoluteResidualAuditLimit':1e-7,'absoluteBalanceAuditLimit':1e-7,
       'scope':'Every recorded residual/balance is independently checked against absolute 1e-7. This is sufficient for the authoring direct-stiffness thresholds 1e-7*(1+max(abs(F))) and 1e-7*(1+max(abs(external))) without reconstructing missing load norms. Missing native/dynamic/special-planar balance records remain explicitly counted.',
       'rows':reference_check_rows}
    return {'manifestSha256':sha(edition/'manifest.json'),'scope':'source-guided-not-blind; no candidate execution or external independent review',
      'allPassed':not failed,'allMandatoryChecksPassed':not any(c['severity']=='mandatory' for c in failed),
      'documentedExceptions':[c for c in failed if c['severity']!='mandatory'],
      'cases':len(cases),'turns':sum(len(c['turns']) for c in cases),'levels':dict(Counter(c.get('level') for c in cases)),
      'families':dict(Counter(c.get('family') for c in cases)),'engines':dict(Counter(c.get('engine') for c in cases)),
      'splits':split_counts,'engineeringAdaptations':len(engineering),'realProjectEligibleAdaptations':len(real),
      'sourceProjects':dict(source_counts),'uniqueTopologyFingerprints':len(fingerprints),'maximumCasesPerTopology':max(map(len,fingerprints.values()),default=0),
      'topologyGroups':dict(fingerprints),'checkCount':len(checks),'failedChecks':failed,'caseRows':case_rows,
      'originTopologyStats':origin_stats,'topologyPairComparisons':pair_rows,
      'geometryComparisonScope':'Exact issued coordinates, member connectivity/type and support masks; ignores IDs and properties, preserves observation stations.',
      'physicalComparisonScope':'Qualified evaluator physical equivalence; includes active material/section properties, loading and control, not graph shape alone.',
      'schemaValidation':schema_result,'referenceChecks':reference_summary,
      'visualTranscriptionBinding':{'path':str(manual_path),'sha256':sha(manual_path),'cases':len(manual)} if manual_path else None,
      'publicReconstruction':{'attempted':len(comparisons),'passed':sum(r['passed'] for r in comparison_rows),'rows':reconstruction,'comparisons':comparison_rows},
      'frozenLegacyFilesChecked':len(guard),'externalBlindReviews':0,'candidateCalls':0}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--edition',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source-registry',type=Path,default=Path(__file__).with_name('source_registry.json'))
    p.add_argument('--manual-geometry',type=Path)
    p.add_argument('--schema-root',type=Path,help='Pinned Python package parent containing structure_protocol')
    p.add_argument('--schema-python',type=Path,help='Python environment containing pydantic v2; defaults to the audit interpreter')
    a=p.parse_args()
    result=audit(a.edition.resolve(),a.source_registry.resolve(),a.manual_geometry,a.schema_root,a.schema_python)
    with a.output.open('x') as f:f.write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['caseRows','topologyGroups','topologyPairComparisons','publicReconstruction','failedChecks','documentedExceptions','schemaValidation','referenceChecks']}))
    if result['failedChecks']:print(json.dumps(result['failedChecks'],ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['allPassed'] else 1)
