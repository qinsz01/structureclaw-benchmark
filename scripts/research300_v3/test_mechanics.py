import unittest
from copy import deepcopy
import math
from .support import factory
from .mechanics import prepare_primary,secondary,rules_for,project,rigid_project,COMBINATIONS,strip_terms,revised_project_rules,self_weight,clean
from .analyses import area_rules,load_model,revised_rules,mass_model,roof_lines

class EngineeringPhysicsTests(unittest.TestCase):
    def test_equal_total_live_relocation_changes_moment_and_mass_distribution(self):
        m=factory.build_model('frame',12);r=area_rules(m,12);r2=revised_rules(m,r,12)
        a=load_model(m,r);b=load_model(m,r2);nodes={n['id']:n for n in a['nodes']}
        def sums(m):
            loads=next(c['loads'] for c in m['load_cases'] if c['id']=='Q')
            return sum(-l['fz'] for l in loads),sum(-l['fz']*nodes[l['node']]['x'] for l in loads)
        x,y=sums(a),sums(b);self.assertAlmostEqual(x[0],y[0],places=9);self.assertNotAlmostEqual(x[1],y[1],places=4)
        a,ca=mass_model(m,r,.3);b,cb=mass_model(m,r2,.3)
        self.assertNotEqual([n.get('mass',0) for n in a['nodes']],[n.get('mass',0) for n in b['nodes']])
        self.assertTrue(all(n.get('mass',0)==0 for n in a['nodes'] if n['restraints'][0]))

    def test_reaction_transfer_balance_and_design_dependent_gravity(self):
        p=prepare_primary(factory.build_model('frame',12));u,links=secondary(p,12);r=rules_for(p,12)
        a=project(p,u,links,r,{'G0':'A','G1':'A','G2':'A'});b=project(p,u,links,r,{'G0':'C','G1':'B','G2':'A'})
        self.assertNotEqual(a['primaryLoadCases'],b['primaryLoadCases']);self.assertNotEqual(a['volume'],b['volume'])
        def gravity(t):
            m=deepcopy(u);m['sections']=t['upperSections'];m['load_cases']=t['upperLoadCases'];ns={n['id']:n for n in m['nodes']};total=0
            for l in next(c['loads'] for c in m['load_cases'] if c['id']=='D'):
                if l['type']=='nodal':total-=l.get('fz',0)
                else:
                    e=next(e for e in m['elements'] if e['id']==l['element']);na,nb=[ns[n] for n in e['nodes']];L=math.dist([na[k] for k in 'xyz'],[nb[k] for k in 'xyz']);total-=l.get('wz',0)*(l.get('end',L)-l.get('start',0))
            return total
        self.assertAlmostEqual(sum(v['fz'] for v in a['transfer'][0]['values']),gravity(a),places=7)
        self.assertNotAlmostEqual(gravity(a),gravity(b),places=5)

    def test_rigid_compatibility_and_no_virtual_support(self):
        p=prepare_primary(factory.build_model('truss',14));u,links=secondary(p,14,cambered=True);r=rules_for(p,14)
        from .mechanics import combine_rigid
        m,mapping=combine_rigid(p,u,links)
        self.assertEqual(len(m['nodes']),len(p['nodes'])+len(u['nodes'])-4)
        for link in links:
            self.assertEqual(mapping['U']['nodes'][link['upperSupport']],mapping['P']['nodes'][link['primaryJoint']])
            n=next(n for n in m['nodes'] if n['id']==mapping['P']['nodes'][link['primaryJoint']]);self.assertFalse(n['restraints'][4])
        t=rigid_project(p,u,links,r,{'G0':'A','G1':'B','G2':'C'})
        self.assertGreater(max(abs(v['uz']) for row in t['transfer'] for v in row['values']),0)

if __name__=='__main__':unittest.main()
