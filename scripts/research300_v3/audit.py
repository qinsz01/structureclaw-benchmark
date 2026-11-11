"""Source-guided edition audit with public-only geometry transcription.

This is not an external blind review. Load-conversion conservation and model
physics are tested separately; this audit does not call copied authoring loads
an independent reconstruction of the complete engineering decision.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
from .support import V2,load
from .public_geometry import reconstruct,legacy_raster_transcription

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):return math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-9)
def geometry_equal(actual,expected):
    assert actual['coordinate_system']==expected['coordinate_system'],'Coordinate convention'
    an={n['id']:n for n in actual['nodes']};en={n['id']:n for n in expected['nodes']};assert an.keys()==en.keys(),'Joint identities'
    for nid,n in en.items():
        assert all(close(an[nid][k],n[k]) for k in 'xyz'),('Joint location',nid)
        assert an[nid]['restraints']==n['restraints'],('Joint supports',nid)
    ae={e['id']:e for e in actual['elements']};ee={e['id']:e for e in expected['elements']};assert ae.keys()==ee.keys(),'Member marks'
    for eid,e in ee.items():
        assert all(ae[eid][k]==e[k] for k in ['nodes','type','material','section']),('Construction connectivity/properties',eid)
        assert close(ae[eid].get('rotation_angle',0),e.get('rotation_angle',0)),('Section orientation',eid)
    assert actual['materials']==expected['materials'] and actual['sections']==expected['sections'],'Issued properties'
    return {'joints':len(en),'members':len(ee)}

def revision_check(public,expected,base):
    task=read(public/'task.json');ordinal=int(task['turnId'][1:]);text=task['instruction']
    if ordinal in [2,3]:
        if ordinal==2:
            match=re.search(r'X=([\d.e+\-]+) m 分界，西/东面压比 ([\d.e+\-]+)，总活荷载仍为 ([\d.e+\-]+) kN',text);assert match,'Unspecified Q revision'
            for k,v in zip(['splitX','westEastPressureRatio','totalLiveKN'],map(float,match.groups())):assert close(expected['liveRevision'][k],v),(k,v)
        else:assert '保留上一轮 Q 重分布' in text and expected.get('liveRevision'),'Lost Q revision'
    else:assert not expected.get('liveRevision'),'Unexpected live revision'
    if ordinal in [3,4]:
        assert expected.get('addedEquipment'),'Lost equipment'
        if ordinal==3:
            match=re.search(r'增加设备恒载 ([\d.e+\-]+) kN',text);assert match and close(float(match[1]),expected['addedEquipment']['weightKN'])
        else:assert '保留第3轮设备恒载' in text and '恢复为第1轮' in text
    else:assert not expected.get('addedEquipment'),'Unexpected equipment'
    for key in base:
        if key not in ['liveRevision','addedEquipment']:assert expected[key]==base[key],('Unissued input change',key)

def audit(edition,output):
    edition=Path(edition).resolve();manifest=read(edition/'manifest.json');old=load('v3_frozen_public_auditor',V2/'audit.py');records=[];transcriptions={}
    for row in manifest['files']:assert sha(edition/row['path'])==row['sha256'],row['path']
    assert Counter(c['level'] for c in manifest['cases'])=={'L1':30,'L2':60,'L3':120,'L4':90}
    for c in manifest['cases']:
        first=c['turns'][0];public=edition/first['public'];ref=read(edition/first['private']);row={'caseId':c['id'],'level':c['level'],'family':c['family'],'kind':ref['kind']}
        try:
            if c['level'] in ['L1','L2']:
                manual=legacy_raster_transcription(public) if c['family']=='MM' else None
                if manual:transcriptions[c['id']]=manual
                rebuilt=old.reconstruct_initial(public,manual);row['geometry']=geometry_equal(rebuilt,ref['model'])
                assert rebuilt['load_cases']==ref['model']['load_cases'],'Low-level issued loads'
                assert rebuilt['load_combinations']==ref['model']['load_combinations'],'Low-level combinations'
                row['geometryCarrier']='raster-font-template' if manual else 'tables'
            else:
                for path in public.rglob('*.json'):assert not old.full_models(read(path)),('Full model leaked in high-level input',path.name)
                assert not any(p.name in ['nodes.csv','members.csv','loads.json'] for p in public.rglob('*'))
                row['geometry']={}
                if ref['kind']=='project':
                    assert len(ref['truths'])==27 and len(ref['designGroups'])==3 and len(ref['constraints'])==4
                    assert ref['difficultyEvidence']['reactionDesignCouplingRelative']>.01
                    if ref['optimalDesigns']:assert len(ref['difficultyEvidence']['essentialConstraintFamilies'])>=2
                    for role in ['primary','upper']:
                        expected=deepcopy(ref[role+'Template'])
                        if role=='upper' and ref['integration']=='rigid':
                            for n in expected['nodes']:n['restraints']=[False,True,False,True,False,True]
                        row['geometry'][role]=geometry_equal(reconstruct(public/role),expected)
                    base=read(public/'load-zones.json');assert base==ref['loadRules']
                    row['designEvidence']=ref['difficultyEvidence'];row['integration']=ref['integration']
                else:
                    expected=ref['scenarios'][0]['model'] if ref['kind']=='analysis' else ref['model'];row['geometry']['structure']=geometry_equal(reconstruct(public/'structure'),expected)
                    base=read(public/'load-zones.json');assert base==(ref['scenarios'][0]['loadRules'] if ref['kind']=='analysis' else ref['loadRules'])
                    if ref['kind']=='analysis' and len(ref['scenarios'])==2:assert read(public/'proposed-revision.json')==ref['scenarios'][1]['loadRules']['liveRevision']
                for t in c['turns'][1:]:
                    r=read(edition/t['private']);p=edition/t['public'];rules=r['scenarios'][0]['loadRules'] if r['kind']=='analysis' else r['loadRules'];revision_check(p,rules,base)
                    assert not any(x.is_dir() for x in p.iterdir()),'Future revision supplies full geometry'
                row['geometryCarrier']='grid-raster-font-template' if c['family']=='MM' else 'construction-documents'
            row['passed']=True
        except Exception as error:row.update(passed=False,error=repr(error))
        records.append(row);print(json.dumps({k:v for k,v in row.items() if k!='geometry'},ensure_ascii=False),flush=True)
    result={'schemaVersion':3,'manifestSha256':sha(edition/'manifest.json'),'cases':len(records),'passed':sum(r['passed'] for r in records),'failed':sum(not r['passed'] for r in records),'scope':'Public-only construction/table/raster geometry reconstruction and load/revision specification completeness. Native qualification independently checks executed physics. Font-template transcription is not external blind review.','candidateCalls':0,'rows':records}
    output=Path(output);output.mkdir(parents=True,exist_ok=False);(output/'input-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(output/'low-level-visual-transcriptions.json').write_text(json.dumps(transcriptions,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--edition',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=audit(a.edition,a.output);print(json.dumps({k:v for k,v in r.items() if k!='rows'}));raise SystemExit(bool(r['failed']))
