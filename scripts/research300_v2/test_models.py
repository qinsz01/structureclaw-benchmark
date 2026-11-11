"""Independent stability/equilibrium and topology checks for the model factories."""
from __future__ import annotations

import os
for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='1'
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/research300'))
from reference_solver import solve_many
from models import FAMILIES,VARIANTS,build_model,variant_info,topology_fingerprint,catalogue


def independent_checks():
    rows=[]
    for family in FAMILIES:
        for variant in range(VARIANTS):
            m=build_model(family,variant);info=variant_info(family,variant)
            factors=[{'D':1.},{'Q':1.},{'W':1.},{'D':1.,'Q':1.},{'D':1.,'W':-1.}]
            results=solve_many(m,factors,[])
            maxima=[]
            for value,check in results:
                response=[value({'kind':'node','id':n['id']},component) for n in m['nodes'] for component in ['ux','uy','uz']]
                assert all(math.isfinite(x) for x in response)
                maxima.append(max(abs(x) for x in response))
                assert check['minimumScaledPivot'] is None or check['minimumScaledPivot']>0
            row={**info,'allPassed':True,'rightHandSides':len(results),
                 'maximumDisplacementsM':maxima,'maximumFreeResidual':max(c['freeResidual'] for _,c in results),
                 'maximumForceMomentImbalance':max(abs(v) for _,c in results for v in c['forceMomentBalance']),
                 'minimumScaledPivot':min(c['minimumScaledPivot'] for _,c in results if c['minimumScaledPivot'] is not None)}
            rows.append(row)
    return {'models':len(rows),'uniqueTopologyFingerprints':len({r['topologyFingerprint'] for r in rows}),
            'actualSUTCalls':0,'method':'Independent Euler-Bernoulli direct stiffness, three cases and two combinations',
            'allPassed':all(r['allPassed'] for r in rows),'rows':rows}


class ModelChecks(unittest.TestCase):
    def test_all_model_families_are_stable(self):
        result=independent_checks()
        self.assertEqual(result['models'],210)
        self.assertEqual(result['uniqueTopologyFingerprints'],210)
        self.assertTrue(result['allPassed'])

    def test_fingerprint_ignores_ids_properties_scale_and_rigid_motion(self):
        for family in FAMILIES:
            m=build_model(family,11);n=deepcopy(m)
            names={v['id']:'alias-'+str(i) for i,v in enumerate(reversed(n['nodes']))}
            for v in n['nodes']:
                v['id']=names[v['id']]
                x,y,z=v['x'],v['y'],v['z']
                v['x']=2*z+7;v['y']=2*x-11;v['z']=2*y+3
            n['nodes'].reverse();n['elements'].reverse()
            for i,e in enumerate(n['elements']):e['id']='member-'+str(i);e['nodes']=[names[x] for x in e['nodes']]
            for s in n['sections']:
                for k in s['properties']:s['properties'][k]*=2
            self.assertEqual(topology_fingerprint(m),topology_fingerprint(n),family)

    def test_fingerprint_removes_unrestrained_collinear_mesh_station(self):
        for family in ['beam','frame','space_frame','mixed']:
            m=build_model(family,0);n=deepcopy(m);e=next(e for e in n['elements'] if e['type'] in ['beam','column'])
            ends=[next(v for v in n['nodes'] if v['id']==node) for node in e['nodes']]
            nid='extra-mesh-node';new={'id':nid,**{k:(ends[0][k]+ends[1][k])/2 for k in ['x','y','z']},
                                     'restraints':[False,True,False,True,False,True] if family!='space_frame' else [False]*6}
            n['nodes'].append(new);other=deepcopy(e);other['id']='extra-member';other['nodes']=[nid,e['nodes'][1]];e['nodes'][1]=nid;n['elements'].append(other)
            self.assertEqual(topology_fingerprint(m),topology_fingerprint(n),family)
            new['restraints'][2]=True
            self.assertNotEqual(topology_fingerprint(m),topology_fingerprint(n),family)

    def test_models_are_fresh_and_bounded(self):
        for family in FAMILIES:
            m=build_model(family,0);n=build_model(family,0);self.assertEqual(m,n)
            m['nodes'][0]['x']=100.;self.assertNotEqual(m,n)
        with self.assertRaises(ValueError):build_model('frame',-1)
        with self.assertRaises(ValueError):build_model('frame',35)
        with self.assertRaises(ValueError):build_model('frame',True)
        dimensions={tuple(build_model('frame',i)['sections'][0]['shape'][k] for k in ['B','H']) for i in range(VARIANTS)}
        self.assertEqual(len(dimensions),35)


if __name__=='__main__':
    if '--output' in sys.argv:
        i=sys.argv.index('--output');path=Path(sys.argv[i+1]);report=independent_checks()
        with path.open('x') as f:f.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
    else:unittest.main()
