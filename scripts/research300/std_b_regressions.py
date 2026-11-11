"""Adversarial authoring regressions: same totals cannot hide wrong physical input."""
import json
import unittest
from std_b_common import ROOT
from std_b_source_checks import check, at

def read_case(number):
    p=ROOT/'corpora/research-300/cases'/f'STD-{number:03d}'
    return json.loads((p/'model-state-1.json').read_text()),json.loads((p/'reference-requests.json').read_text())['states'][0]

class SourceRegressionTests(unittest.TestCase):
    def reject(self,number,mutate):
        model,requests=read_case(number)
        check(number,model,requests)  # unmodified positive control
        mutate(model,requests)
        with self.assertRaises(AssertionError):check(number,model,requests)

    def test_uplift_cannot_move_to_other_roof_slope(self):
        def mutate(m,r):next(c for c in m['load_cases'] if c['id']=='W')['loads'][0]['element']='slope-L'
        self.reject(51,mutate)

    def test_connected_midpoint_must_have_requested_displacement(self):
        def mutate(m,r):
            nid=at(m,(11,0,7))['id']
            r['quantities'][:]=[q for q in r['quantities'] if not(q['location'].get('id')==nid and q['component']=='uz')]
        self.reject(52,mutate)

    def test_source_hinge_cannot_be_fixed(self):
        self.reject(69,lambda m,r:at(m,(0,0,0))['restraints'].__setitem__(4,True))

    def test_omitted_strong_weak_roll_is_detected(self):
        def mutate(m,r):
            for e in m['elements']:e['rotation_angle']=0
        self.reject(74,mutate)

    def test_setback_reentrant_observation_is_required(self):
        def mutate(m,r):
            nid=at(m,(10,0,3.6))['id']
            r['quantities'][:]=[q for q in r['quantities'] if not(q['location'].get('id')==nid and q['component']=='uz')]
        self.reject(75,mutate)

    def test_lateral_load_cannot_move_floors_with_same_total(self):
        def mutate(m,r):
            w=next(c for c in m['load_cases'] if c['id']=='Wx')['loads']
            w[1]['node']=w[0]['node']
        self.reject(88,mutate)

    def test_local_floor_region_not_interchangeable(self):
        def mutate(m,r):
            l=next(c for c in m['load_cases'] if c['id']=='L')['loads']
            l[0]['element']='x1-0-2'  # equal-length adjacent beam: same resultant
        self.reject(91,mutate)

    def test_mid_column_axial_load_cannot_be_moved_to_top(self):
        def mutate(m,r):
            for l in m['load_cases'][0]['loads']:l['node']='top'
        self.reject(97,mutate)

if __name__=='__main__':unittest.main()
