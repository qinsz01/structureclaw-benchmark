"""Assign levels only after constructing substantive project decisions."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
from collections import Counter,defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .support import ROOT,V2,legacy_tasks,engineering,factory
from .mechanics import prepare_primary,rename,rigid_eligible
from .projects import reference as project_reference

ROUNDS={'L1':2,'L2':3,'L3':4,'L4':4}
TARGETS={'L1':10,'L2':20,'L3':40,'L4':30}

def source_specs():
    registry=json.loads((V2/'source_registry.json').read_text());rows=[]
    for i,source in enumerate(s for s in registry['sources'] if s['sourceId']!='SRC-PV-2023'):
        for sub,families in enumerate([['STD','MM'],['MM','INT'],['INT','STD']]):
            built=engineering.build_engineering(source['sourceId'],sub)
            for family in families:
                rows.append({'family':family,'origin':'source-adapted','engine':'OpenSees','sourceId':source['sourceId'],'sourceProjectGroup':source['sourceId'],
                    'sourceBasis':deepcopy(source),'baseModelGroup':built['subproblemId'],'modelFamily':source['geometryHint']['type'],
                    'sourceIndex':i,'subproblemIndex':sub,'model':built['model'],'authoringBasis':built['authoringBasis'],
                    'title':source['title']+'：'+str(sub+1)+'号分析子结构'})
    return rows

def raw_specs():
    rows=legacy_tasks.original_specs()+legacy_tasks.commercial_specs()+source_specs()
    for i,c in enumerate(rows):
        c['seed']=i;c.setdefault('engine','OpenSees');c.pop('audit',None)
        if c['origin']!='legacy-commercial':c.pop('level',None)
        if c.get('special'):
            c['replacedFactorySlot']={'modelFamily':c['modelFamily'],'variant':c.get('variant')};c['modelFamily']='beam';c['structuralVariation']={'specialFeature':c['special']}
        if c['origin']!='legacy-commercial':c['model']=rename(c['model'])
    return rows

def assign(cache):
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True);rows=raw_specs();rejected=[]
    for family in ['STD','MM','INT']:
        group=[c for c in rows if c['family']==family]
        candidates=sorted([c for c in group if c['engine']=='OpenSees' and not c.get('analysis') and not c.get('special')],
          key=lambda c:(c['origin']!='source-adapted',abs(len(c['model']['nodes'])-24),c['modelFamily'],c['seed']))
        chosen=0;rigid_count=0
        for c in candidates:
            if chosen==30:break
            if prepare_primary(c['model']) is None:continue
            try:
                ref=None
                if rigid_count<4 and chosen%10!=9 and rigid_eligible(c['model']):
                    try:ref=project_reference(c['model'],c['seed'],integration='rigid')
                    except (ValueError,AssertionError) as error:rejected.append({'seed':c['seed'],'family':family,'integration':'rigid','reason':str(error)})
                if ref is None:ref=project_reference(c['model'],c['seed'],infeasible=chosen%10==9)
            except (ValueError,AssertionError) as error:
                rejected.append({'seed':c['seed'],'family':family,'reason':str(error)});continue
            c['level']='L4';c['analysis']='project';c['projectCache']=str(cache/f'project-{c["seed"]:03}.json')
            c['integration']=ref['integration'];rigid_count+=ref['integration']=='rigid'
            Path(c['projectCache']).write_text(json.dumps(ref,ensure_ascii=False,allow_nan=False)+'\n');chosen+=1
            print(json.dumps({'projectCandidatesAccepted':chosen,'family':family,'source':c.get('sourceId'),'seed':c['seed'],'integration':ref['integration'],'essentialFamilies':ref['difficultyEvidence']['essentialConstraintFamilies']}),flush=True)
        if chosen!=30:raise ValueError(f'{family}: only {chosen}/30 genuinely coupled project cases')
        remaining=[c for c in group if 'level' not in c]
        lows=sorted([c for c in remaining if not c.get('analysis') and not c.get('special')],key=lambda c:(len(c['model']['nodes'])+len(c['model']['elements'])/3,c['origin']=='source-adapted',c['seed']))
        for c in lows[:5]:c['level']='L1'
        middle=sorted([c for c in remaining if 'level' not in c and not c.get('analysis')],key=lambda c:(not bool(c.get('special')),len(c['model']['nodes'])+len(c['model']['elements'])/3,c['seed']))
        for c in middle[:15]:c['level']='L2'
        for c in remaining:
            if 'level' not in c:c['level']='L3'
        assert Counter(c['level'] for c in group)==Counter(TARGETS),(family,Counter(c['level'] for c in group))
        ordered=sorted(group,key=lambda c:(c['level'],c['origin'],c.get('sourceId',''),c['modelFamily'],c['seed']))
        for i,c in enumerate(ordered,1):
            c['id']=f'V3-{family}-{i:03}';c['rounds']=ROUNDS[c['level']] if family=='INT' else 1
            c['analysis']=c.get('analysis','scenario' if c['level']=='L3' else 'static')
            c['topologyFingerprint']=factory.topology_fingerprint(c['model']);c['difficultyStatus']='designed-pending-isolated-candidate-calibration'
    # Source projects and shared mechanics prototypes remain whole groups.
    source_ids=sorted({c['sourceId'] for c in rows if c.get('sourceId')});dev_sources=set(source_ids[:2]);dev_targets={'L1':2,'L2':4,'L3':8,'L4':6}
    for c in rows:c['split']='dev' if c.get('sourceId') in dev_sources else 'test'
    groups=defaultdict(list)
    for c in rows:
        if not c.get('sourceId'):groups[c['baseModelGroup']].append(c)
    for _,group in sorted(groups.items(),key=lambda row:(not row[0].startswith('special:'),row[0])):
        delta=Counter((c['family'],c['level']) for c in group);current=Counter((c['family'],c['level']) for c in rows if c['split']=='dev')
        if all(current[k]+n<=dev_targets[k[1]] for k,n in delta.items()):
            for c in group:c['split']='dev'
    dev=Counter((c['family'],c['level']) for c in rows if c['split']=='dev');assert dev==Counter({(f,l):n for f in ['STD','MM','INT'] for l,n in dev_targets.items()}),dev
    assert Counter(c['level'] for c in rows)==Counter({'L1':30,'L2':60,'L3':120,'L4':90})
    return sorted(rows,key=lambda c:c['id']),rejected

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Preserve prior assignment attempts')
    cases,rejected=assign(args.cache.resolve());args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as file:file.write(json.dumps({'rows':cases,'rejected':rejected},ensure_ascii=False,allow_nan=False)+'\n')
