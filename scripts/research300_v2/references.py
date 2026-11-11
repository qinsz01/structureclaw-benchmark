"""Independent references for the full edition; no production solver imports."""
from copy import deepcopy
import importlib.util
import math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
static_ref=module('v2_static_reference',ROOT/'scripts/research300/reference_solver.py')
planar=module('v2_planar_reference',ROOT/'scripts/pilot30/independent.py')


def factors(model,selection):
    return {selection['id']:1.} if selection['kind']=='case' else next(c['factors'] for c in model['load_combinations'] if c['id']==selection['id'])


def solve(model,selections,requests):
    special=model['analysis_control'].get('self_weight') or any(e.get('releases') for e in model['elements']) or any(l['type']=='displacement' for c in model['load_cases'] for l in c['loads'])
    if special:
        rows=[]
        for sel in selections:
            values,check=planar.static(model,factors(model,sel))
            def quantity(loc,comp,values=values):
                assert loc['kind']=='node','Special planar references expose nodes only'
                return values[loc['id']][comp]
            rows.append((quantity,check))
        return rows
    stations=[q['location'] for q in requests]
    solved=static_ref.solve_many(model,[factors(model,s) for s in selections],stations)
    # General independent solver uses lowercase global support-force labels.
    return [(lambda loc,comp,fn=fn:fn(loc,comp.lower() if loc['kind']=='node' and comp[0] in 'FM' else comp),check) for fn,check in solved]


def reference(turn):
    ref={k:deepcopy(v) for k,v in turn.items() if k not in ['instruction','changeOrder','suspectModel','suspectExcerpt']}
    ref.setdefault('engine','OpenSees');ref.setdefault('derived',[]);ref.setdefault('clarificationFields',[])
    kind=ref['kind'];model=ref.get('model');ref['referenceChecks']=[]
    if kind=='clarify':
        ref.pop('model',None);ref['requests']=[];ref['reportIds']=[];return ref
    if ref.get('nativeReferenceBinding'):
        # Exact prior same-engine inputs/quantities are frozen, never regenerated
        # from Euler-Bernoulli values or from a candidate's output.
        assert all('value' in q for q in ref['requests'])
        ref['referenceChecks']=[{'method':'unchanged-previous-qualified-same-engine-native','binding':ref['nativeReferenceBinding']}]
    elif kind in ['static','query']:
        selections=list({s['kind']+':'+s['id']:s for s in [q['selection'] for q in ref['requests']]}.values())
        results=solve(model,selections,ref['requests']);calculators={s['kind']+':'+s['id']:fn for s,(fn,_) in zip(selections,results)}
        for q in ref['requests']:
            q['value']=calculators[q['selection']['kind']+':'+q['selection']['id']](q['location'],q['component'])
        ref['referenceChecks']=[{'selection':s,**check} for s,(_,check) in zip(selections,results)]
    elif kind=='modal':
        md=planar.modes(model);n=ref['parameters']['numModes'];ref['requests']=[]
        assert len(md['periods'])>=n
        assert all(abs(a-b)>1e-4*max(a,b) for a,b in zip(md['omega'][:n],md['omega'][1:n+1])),'Near repeated modes require a separate subspace metric'
        for i in range(n):
            for field,unit,value in [('period','s',md['periods'][i]),('frequency','Hz',1/md['periods'][i]),('effectiveMass','tonne',md['effectiveMass'][i])]:
                ref['requests'].append({'id':f'mode-{i+1}-{field}','path':['modes',i,field],'unit':unit,'value':value,'tolerance':{'absolute':1e-8,'relative':1e-6}})
        ref['modalTruth']={'shape':md['shape'],'masses':{n['id']:n.get('mass',0) for n in model['nodes']}}
        ref['referenceChecks']=[{'method':'independent-condensed-K-M','totalMass':md['totalMass'],'effectiveMassSum':sum(md['effectiveMass']),'firstPeriods':md['periods'][:n]}]
        assert math.isclose(sum(md['effectiveMass']),md['totalMass'],rel_tol=1e-8,abs_tol=1e-8)
    elif kind=='transient':
        rows,check=planar.transient(model,ref['parameters']);fine,_=planar.transient(model,ref['parameters'],2)
        nid=ref.pop('monitorNode');series=[r['nodes'][nid]['ux'] for r in rows];peak=max(range(len(series)),key=lambda i:abs(series[i]))
        sample=min(len(rows)-1,round(.4/ref['parameters']['timeStep'])-1)
        ref['requests']=[{'id':nid+'-ux-at-sample','path':['timeHistory',sample,'nodes',nid,'ux'],'unit':'m','value':series[sample],
                         'tolerance':{'absolute':1e-8,'relative':1e-6}},
                        {'id':nid+'-signed-peak-ux','path':['timeHistory','*','nodes',nid,'ux'],'operation':'max_abs','unit':'m','value':series[peak],
                         'time':rows[peak]['time'],'tolerance':{'absolute':1e-8,'relative':1e-6}}]
        delta=max(abs(v-f['nodes'][nid]['ux']) for v,f in zip(series,fine[1::2]))
        ref['referenceChecks']=[{**check,'halfStepMaxDifference':delta,'halfStepDifferenceOverPeak':delta/max(max(map(abs,series)),1e-12),
                                'scope':'Fixed-step discrete comparison; refinement difference is not called floating-point error.'}]
    elif kind=='scheme':
        rows=[];ns={n['id']:n for n in model['nodes']};sels=[{'kind':'combination','id':s} for s in ref['schemeSelections']]
        qs=[{'location':{'kind':'node','id':n},'component':ref['constraint']['component']} for n in ref['constraint']['nodes']]
        for scheme in ref['schemes']:
            variant=deepcopy(model);section=next(s for s in variant['sections'] if s['id']==scheme['section']);section['properties']=deepcopy(scheme['properties'])
            if scheme.get('shape'):section['shape']=deepcopy(scheme['shape'])
            else:section.pop('shape',None)
            results=solve(variant,sels,qs)
            maximum=max(abs(fn(q['location'],q['component'])) for fn,_ in results for q in qs)
            ps={s['id']:s['properties'] for s in variant['sections']}
            volume=sum(ps[e['section']]['A']*math.dist([ns[e['nodes'][0]][k] for k in 'xyz'],[ns[e['nodes'][1]][k] for k in 'xyz']) for e in variant['elements'])
            rows.append({'id':scheme['id'],'model':variant,'maximum':maximum,'volume':volume,'feasible':maximum<=ref['constraint']['absoluteLimit'],
                         'referenceChecks':[{'selection':s,**check} for s,(_,check) in zip(sels,results)]})
        ref['schemeTruth']=rows;feasible=[r for r in rows if r['feasible']]
        ref['optimalSchemes']=[r['id'] for r in feasible if math.isclose(r['volume'],min(v['volume'] for v in feasible),rel_tol=1e-10,abs_tol=1e-12)]
        ref['requests']=[];ref['referenceChecks']=[{'method':'independent-exhaustive-finite-scheme-enumeration','schemes':len(rows),'feasible':len(feasible)}]
    else:raise ValueError(kind)
    ref.setdefault('reportIds',[q['id'] for q in ref['requests']]);return ref
