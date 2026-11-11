"""Closed-form and representation checks independent of production solvers."""
from copy import deepcopy
import importlib.util
import math
from pathlib import Path
import unittest

from cases import definitions,oscillator
from independent import static,modes,transient
from oracle_models import canonical


class Theory(unittest.TestCase):
    def test_released_beam_midspan(self):
        m=definitions()[0]['turns'][0]['model'];v,_=static(m,{'D':1})
        E=m['materials'][0]['E']*1000;I=m['sections'][1]['properties']['Iy']
        self.assertAlmostEqual(v['M']['uz'],-5*10*6**4/(384*E*I),places=13)
        self.assertAlmostEqual(v['A']['Fz'],30,places=10)
        self.assertAlmostEqual(v['B']['Fz'],30,places=10)
        self.assertNotIn('ry',v['A'])

    def test_sdof_period_and_effective_mass(self):
        m=oscillator();md=modes(m);E=m['materials'][0]['E']*1000;I=m['sections'][0]['properties']['Iy']
        expected=2*math.pi*math.sqrt(10*3**3/(3*E*I))
        self.assertAlmostEqual(md['periods'][0],expected,places=13)
        self.assertAlmostEqual(md['effectiveMass'][0],10,places=11)

    def test_transient_converges_to_harmonic_solution(self):
        m=oscillator();omega=modes(m)['omega'][0];forcing=3.;amplitude=.3;dt=.0005;duration=.6
        par={'groundMotion':[amplitude*math.sin(forcing*i*dt) for i in range(1202)],
             'groundMotionUnit':'m/s2','timeStep':dt,'duration':duration,'dampingRatio':0}
        rows,_=transient(m,par);fine,_=transient(m,par,2)
        exact=amplitude/(omega**2-forcing**2)*(forcing/omega*math.sin(omega*duration)-math.sin(forcing*duration))
        coarse_error=abs(rows[-1]['nodes']['F1']['ux']-exact)
        fine_error=abs(fine[-1]['nodes']['F1']['ux']-exact)
        self.assertLess(fine_error,coarse_error)
        self.assertLess(fine_error,1e-8)

    def test_selfweight_tracks_area_once(self):
        case=next(c for c in definitions() if c['id']=='P30-INT-007')
        for t in case['turns']:
            m=t['model'];v,_=static(m,{'D':1.2,'W':1})
            A=m['sections'][0]['properties']['A'];weight=7850*A*3*9.80665/1000
            self.assertAlmostEqual(v['A']['Fz'],1.2*(10+weight),places=10)
            m=deepcopy(m);m['analysis_control']['gravity_direction']='-z'
            explicit,_=static(m,{'D':1.2,'W':1})
            self.assertEqual(explicit,v)

    def test_yjk_collinear_refinement_preserves_responses(self):
        # Pinned historical model from the final immutable corpus, no candidate answers.
        root=Path(__file__).resolve().parents[2]
        import json
        ref=json.loads((root/'corpora/research300-v2-pilot30-v1/cases/P30-MM-006/private/t1.json').read_text())
        m=ref['model'];refined=canonical(m,'YJK')
        self.assertEqual((len(m['nodes']),len(refined['nodes'])),(12,14))
        self.assertEqual((len(m['elements']),len(refined['elements'])),(16,18))
        spec=importlib.util.spec_from_file_location('spatial_reference',root/'scripts/independent-frame-reference.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        a,_=module.solve(m,{'D':1},[]);b,_=module.solve(refined,{'D':1},[])
        for node in m['nodes']:
            for component in ['ux','uy','uz','rx','ry','rz','fx','fy','fz','mx','my','mz']:
                loc={'kind':'node','id':node['id']};x=a(loc,component);y=b(loc,component)
                self.assertTrue(math.isclose(x,y,rel_tol=1e-9,abs_tol=1e-8),(node['id'],component,x,y))

    def test_canonical_spatial_embedding_and_planar_refinement(self):
        import json
        root=Path(__file__).resolve().parents[2]
        ref=json.loads((root/'corpora/research300-v2-pilot30-v1/cases/P30-STD-001/private/t1.json').read_text())
        m=ref['model'];spatial=deepcopy(m);spatial['coordinate_system'].update(dimension='3d',plane=None)
        ns={n['id']:n for n in m['nodes']}
        vectors={}
        for e in m['elements']:
            a,b=[ns[n] for n in e['nodes']];dx=b['x']-a['x'];dz=b['z']-a['z'];L=math.hypot(dx,dz)
            vectors[e['id']]=[-dz/L,0,dx/L]
        spatial.setdefault('metadata',{})['elementReferenceVectors']=vectors
        spec=importlib.util.spec_from_file_location('spatial_reference',root/'scripts/independent-frame-reference.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        a,_=module.solve(m,{'D':1},[]);b,_=module.solve(spatial,{'D':1},[])
        for node in m['nodes']:
            for component in ['ux','uy','uz','rx','ry','rz','fx','fy','fz','mx','my','mz']:
                loc={'kind':'node','id':node['id']}
                self.assertTrue(math.isclose(a(loc,component),b(loc,component),rel_tol=1e-11,abs_tol=1e-9))
        refined=deepcopy(m);e=refined['elements'][0];a0,b0=[ns[n] for n in e['nodes']]
        nid='equivalent-cut';eid='equivalent-part'
        refined['nodes'].append({'id':nid,'x':(a0['x']+b0['x'])/2,'y':0.,'z':(a0['z']+b0['z'])/2,
                                'restraints':[False,True,False,True,False,True]})
        e['nodes']=[a0['id'],nid];piece=deepcopy(e);piece.update(id=eid,nodes=[nid,b0['id']]);refined['elements'].append(piece)
        for c in refined['load_cases']:
            loads=[]
            for load in c['loads']:
                if load.get('element')==e['id']:
                    half=math.hypot(b0['x']-a0['x'],b0['z']-a0['z'])/2
                    loads.append({**load,'start':0,'end':half})
                    loads.append({**load,'id':load['id']+'-part','element':eid,'start':0,'end':half})
                else:loads.append(load)
            c['loads']=loads
        b,_=module.solve(refined,{'D':1},[])
        for n in m['nodes']:
            for component in ['ux','uy','uz','rx','ry','rz','fx','fy','fz','mx','my','mz']:
                loc={'kind':'node','id':n['id']}
                self.assertTrue(math.isclose(a(loc,component),b(loc,component),rel_tol=1e-11,abs_tol=1e-9))


if __name__=='__main__':unittest.main()
