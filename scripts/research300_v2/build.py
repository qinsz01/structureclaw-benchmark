"""Build all 300 concrete tasks into a fresh immutable edition directory."""
import argparse
from collections import Counter,defaultdict
from copy import deepcopy
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil

os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from tasks import original_specs,commercial_specs,make_turns,difficulty_evidence,resize,OLD
from models import topology_fingerprint
from references import reference

ROOT=Path(__file__).resolve().parents[2]
SUT='db3c0b1da44fe668a6037a6c2e7f068d14354539'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:f.write(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def engineering_specs():
    from engineering import build_engineering
    registry=json.loads((Path(__file__).with_name('source_registry.json')).read_text())
    sources=[s for s in registry['sources'] if s['sourceId']!='SRC-PV-2023']
    assert len(sources)==10
    rows=[]
    for index,source in enumerate(sources):
        for sub,mapping in enumerate([[('STD','L3'),('MM','L4')],[('MM','L3'),('INT','L4')],[('INT','L3'),('STD','L4')]]):
            built=build_engineering(source['sourceId'],sub)
            for family,level in mapping:
                row={'family':family,'level':level,'origin':'source-adapted','sourceId':source['sourceId'],
                    'sourceProjectGroup':source['sourceId'],'sourceBasis':deepcopy(source),'baseModelGroup':built['subproblemId'],
                    'subproblemId':built['subproblemId'],'title':source['title']+'：子问题'+str(sub+1),
                    'model':deepcopy(built['model']),'loadRecipe':deepcopy(built['loadRecipe']),
                    'authoringBasis':deepcopy(built['authoringBasis']),'modelFamily':source['geometryHint']['type'],
                    'sourceIndex':index,'subproblemIndex':sub}
                if level=='L4':
                    schemes=index<({'STD':8,'MM':8,'INT':9}[family])
                    if schemes:
                        model=row['model'];used={e['section'] for e in model['elements']};sid='B' if 'B' in used else model['elements'][0]['section']
                        catalog=[]
                        for label,factor in zip('ABC',[.8,1.,1.2]):
                            variant=deepcopy(model);section=next(s for s in variant['sections'] if s['id']==sid)
                            if section.get('shape',{}).get('kind')=='rectangular':resize(variant,sid,1.,factor)
                            else:resize(variant,sid,properties_factor=factor)
                            s=next(s for s in variant['sections'] if s['id']==sid)
                            catalog.append({'id':label,'section':sid,'properties':s['properties'],**({'shape':s['shape']} if s.get('shape') else {})})
                        hint=built.get('constraintHint')
                        if not hint:
                            nodes=[n for n in model['nodes'] if not n['restraints'][2]]
                            if not nodes:nodes=[n for n in model['nodes'] if not n['restraints'][0]];component='ux'
                            else:component='uz'
                            hint={'nodes':[n['id'] for n in sorted(nodes,key=lambda n:(n['z'],n['x']))[-3:]],'component':component}
                        row['schemes']=catalog;row['constraint']={**hint,'absoluteLimit':0.}
                        probe=reference({'model':model,'kind':'scheme','engine':'OpenSees','schemes':catalog,'constraint':row['constraint'],
                                         'schemeSelections':['SERVICE','REVERSE'],'requests':[]})
                        maxima=sorted(s['maximum'] for s in probe['schemeTruth']);assert maxima[-1]>1e-10
                        # Design an explicit analysis-only service limit, before
                        # any candidate run. Vary feasibility instead of making
                        # every task have the same winning catalogue entry.
                        target=(index+sub)%4
                        limit=[.7*maxima[0],(maxima[0]+maxima[1])/2,(maxima[1]+maxima[2])/2,1.1*maxima[2]][target]
                        row['constraint']['absoluteLimit']=float(f'{limit:.6g}')
                        row['authoringBasis'].append('位移限值为题设的线弹性方案筛选条件，不是规范安全结论；数值在候选运行前固定。')
                        row['title']+='：有限截面方案与约束比选'
                    else:row['audit']=3;row['title']+='：多类模型错误审查与组合复核'
                rows.append(row)
    return rows


def assign(rows):
    for family in ['STD','MM','INT']:
        group=sorted([r for r in rows if r['family']==family],key=lambda r:(r['level'],r['origin'],r.get('sourceId',''),r.get('modelFamily',''),r.get('variant',0),r.get('legacyId',''),r.get('subproblemIndex',0)))
        assert len(group)==100
        for i,r in enumerate(group,1):
            r['id']=f'V2-{family}-{i:03}';r.setdefault('engine','OpenSees');r.setdefault('analysis','scheme' if r.get('schemes') else 'static')
            r['difficultyEvidence']=difficulty_evidence(r);r['difficultyStatus']='designed-not-empirically-calibrated'
            r['topologyFingerprint']=topology_fingerprint(r['model']);r['split']='test'
            r['inputMode']='tables' if family!='MM' else 'png-tables'
        if family=='MM':
            # Prefer 3D models for multi-view; DXF is a genuine geometry exchange
            # condition, not an XML/vector answer alongside a raster task.
            spatial=[r for r in group if r['model']['coordinate_system']['dimension']=='3d']
            for r in spatial[-20:]:r['inputMode']='multiview'
            pool=[r for r in group if r['inputMode']!='multiview']
            for r in pool[-20:]:r['inputMode']='dxf'
            for r in [r for r in group if r['inputMode']=='png-tables'][:30]:r['inputMode']='png'
    # Source projects and shared authored prototypes are indivisible groups.
    # Pick two complete source groups (12 tasks), then 48 other tasks. The
    # per-family/per-level target is tracked, with shared prototypes excluded
    # from a split across development and held-out sets.
    source_ids=sorted({r['sourceId'] for r in rows if r.get('sourceId')})
    dev_sources=set(source_ids[:2])
    for r in rows:
        if r.get('sourceId') in dev_sources:r['split']='dev'
    bygroup=defaultdict(list)
    for r in rows:
        if not r.get('sourceId'):bygroup[r['baseModelGroup']].append(r)
    targets={'L1':4,'L2':8,'L3':6,'L4':2}
    # Whole shared special-feature groups (one per family) can be selected first.
    for key,group in sorted(bygroup.items(),key=lambda kv:(not kv[0].startswith('special:'),not kv[0].startswith('legacy:'),kv[0])):
        increments=Counter((r['family'],r['level']) for r in group)
        current=Counter((r['family'],r['level']) for r in rows if r['split']=='dev')
        if all(current[k]+n<=targets[k[1]] for k,n in increments.items()):
            for r in group:r['split']='dev'
    counts=Counter((r['family'],r['level']) for r in rows if r['split']=='dev')
    assert counts==Counter({(f,l):n for f in ['STD','MM','INT'] for l,n in targets.items()}),counts
    assert Counter(r['level'] for r in rows)==Counter({'L1':60,'L2':120,'L3':90,'L4':30})
    assert Counter(r['engine'] for r in rows)==Counter({'OpenSees':270,'PKPM':15,'YJK':15})
    return sorted(rows,key=lambda r:r['id'])


def build(out):
    from public import write_public
    if out.exists():raise FileExistsError('Use a new edition directory; failed authoring attempts remain inspectable')
    out.mkdir(parents=True);rows=assign(original_specs()+commercial_specs()+engineering_specs());items=[];schemes=[]
    for index,case in enumerate(rows,1):
        item={k:deepcopy(v) for k,v in case.items() if k not in ['model','states','sourceBasis','loadRecipe','schemes','constraint']}
        if case.get('special'):
            # Factory slot identity only determined stable allocation/order;
            # it does not describe the replacement's actual beam mechanics.
            item['replacedFactorySlot']={'modelFamily':item['modelFamily'],'variant':item.pop('variant')}
            item['modelFamily']='beam'
            item['structuralVariation']={'specialFeature':case['special'],'baseModelGroup':case['baseModelGroup']}
        item['turns']=[]
        for ordinal,turn in enumerate(make_turns(case),1):
            tid=f't{ordinal}';folder=out/'cases'/case['id'];pub=folder/'public'/tid;pub.mkdir(parents=True)
            ref=reference(turn);write_public(pub,case,turn,ordinal,ref)
            private=folder/'private'/f'{tid}.json';write(private,ref)
            item['turns'].append({'id':tid,'public':pub.relative_to(out).as_posix(),'private':private.relative_to(out).as_posix()})
            if ref['kind']=='scheme':schemes.append({'id':case['id'],'turnId':tid,'optimalSchemes':ref['optimalSchemes'],'feasible':sum(s['feasible'] for s in ref['schemeTruth'])})
        if case['origin']=='legacy-commercial':
            source=OLD/case['legacyId'];contract=json.loads((source/'contract.json').read_text())
            for name in ['contract.json','independent-reference.json',*contract['modelStates']]:
                # Retain the exact selected authoring seeds, so regeneration
                # does not depend on an untracked .bench-work directory.
                p=out/'legacy-source'/case['legacyId']/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,p)
        items.append(item);print(json.dumps({'authored':index,'id':case['id'],'level':case['level'],'turns':len(item['turns'])}),flush=True)
    unique=Counter(c['topologyFingerprint'] for c in items)
    assert len(unique)>=180,len(unique)
    summary={'cases':len(items),'turns':sum(len(c['turns']) for c in items),'levels':dict(Counter(c['level'] for c in items)),
        'family':dict(Counter(c['family'] for c in items)),'engines':dict(Counter(c['engine'] for c in items)),
        'origins':dict(Counter(c['origin'] for c in items)),'analyses':dict(Counter(c['analysis'] for c in items)),
        'split':dict(Counter(c['split'] for c in items)),'uniqueTopologyFingerprints':len(unique),'maximumTopologyMultiplicity':max(unique.values()),
        'sourceProjects':len({c['sourceId'] for c in items if c.get('sourceId')}),'schemeOutcomes':schemes}
    assert summary['cases']==300 and summary['turns']==540
    write(out/'catalogue.json',{'schemaVersion':1,'summary':summary,'cases':items})
    csvfile=io.StringIO();w=csv.writer(csvfile,lineterminator='\n');w.writerow(['id','family','level','engine','analysis','origin','sourceProjectGroup','baseModelGroup','split','turns','title'])
    for c in items:w.writerow([c[k] if k in c else '' for k in ['id','family','level','engine','analysis','origin','sourceProjectGroup','baseModelGroup','split']]+[len(c['turns']),c['title']])
    write(out/'catalogue.csv',csvfile.getvalue())
    lines=['# Research300 v2：完整题目索引','','难度是预先设计标签，尚未用候选模型校准。工程来源事实与作者设定见各题首轮 source-basis.json。','',
           '| ID | 类别/难度 | 分组 | 引擎/分析 | 轮数 | 题目 |','| --- | --- | --- | --- | ---: | --- |']
    for c in items:lines.append(f"| [{c['id']}]({c['turns'][0]['public']}/task.json) | {c['family']}/{c['level']} | {c['split']} | {c['engine']}/{c['analysis']} | {len(c['turns'])} | {c['title']} |")
    write(out/'catalogue.md','\n'.join(lines)+'\n')
    manifest={'schemaVersion':1,'edition':'research300-v2-v1','status':'authored-pending-native-and-input-qualification','sutCommit':SUT,
              'candidateRunsAtAuthoring':0,'externalBlindReviews':0,'summary':summary,'cases':items,
              'files':[{'path':p.relative_to(out).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file()]}
    write(out/'manifest.json',manifest);return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.output.resolve()),ensure_ascii=False))
