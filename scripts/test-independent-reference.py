"""Independent oracle checks against closed-form formulas, before candidate solver comparison."""
import importlib.util
from pathlib import Path
import unittest

def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
m=load('representative-models');ref=load('independent-frame-reference')

class Theory(unittest.TestCase):
    def test_midspan_uniform(self):
        model=m.beam([6]);m.beams_udl(model,20);station=dict(kind='member',id='b1',positionM=3,side='right')
        value,evidence=ref.solve(model,{'D':1},[station]);I=model['sections'][0]['properties']['Iy'];E=model['materials'][0]['E']*1000
        self.assertAlmostEqual(value(station,'uz'),-5*20*6**4/(384*E*I),places=12)
        self.assertAlmostEqual(value(dict(kind='node',id='n0'),'fz'),60,places=9)
        self.assertLess(max(abs(v) for v in evidence['forceMomentBalance']),1e-8)
    def test_partial_and_point(self):
        model=m.beam([4]);m.load(model,type='point',element='b1',position=2,fz=-.5)
        station=dict(kind='member',id='b1',positionM=2,side='left');value,_=ref.solve(model,{'D':1},[station]);I=model['sections'][0]['properties']['Iy'];E=model['materials'][0]['E']*1000
        self.assertAlmostEqual(value(station,'uz'),-.5*4**3/(48*E*I),places=12)
        self.assertAlmostEqual(value(station,'V3')-value(dict(station,side='right'),'V3'),.5,places=10)
    def test_cantilever_3d(self):
        model=m.model('3d');m.node(model,'a',0,0,0,[True]*6);m.node(model,'b',0,5);m.elem(model,'c','a','b','column','C1');m.load(model,type='nodal',node='b',fx=10)
        value,evidence=ref.solve(model,{'D':1},[]);E=model['materials'][0]['E']*1000;I=next(s for s in model['sections'] if s['id']=='C1')['properties']['Iy']
        self.assertAlmostEqual(value(dict(kind='node',id='b'),'ux'),10*5**3/(3*E*I),places=12)
        self.assertAlmostEqual(value(dict(kind='node',id='a'),'my'),-50,places=9)

if __name__=='__main__':unittest.main()
