import math
import unittest
from .audit_load_arithmetic import reconstruct


def fixture():
    model={'nodes':[{'id':'a','x':0.,'y':0.,'z':1.},{'id':'b','x':4.,'y':0.,'z':3.}],
           'materials':[{'id':'m','rho':0.}], 'sections':[{'id':'s','properties':{'A':.002}}],
           'elements':[{'id':'e','type':'truss','nodes':['a','b'],'material':'m','section':'s'}]}
    rules={'gravityMPerS2':9.80665,'stripWidthM':2.,'planEdgesY':None,
           'zones':[{'startX':0.,'endX':4.,'D':5.,'Q':7.,'W':3.}],
           'horizontalAction':{'fxKN':10.,'fyKN':0.}}
    return model,rules


class PublicLoadArithmeticTest(unittest.TestCase):
    def test_sloped_normal_pressure_and_highest_joint_horizontal_action(self):
        model,rules=fixture();nodal,_=reconstruct(model,rules)
        self.assertAlmostEqual(nodal['D']['a'][2],-20.)
        self.assertAlmostEqual(nodal['D']['b'][2],-20.)
        self.assertAlmostEqual(nodal['Q']['a'][2],-28.)
        self.assertAlmostEqual(nodal['W']['a'][0],-6.)
        self.assertAlmostEqual(nodal['W']['b'][0],4.)
        self.assertAlmostEqual(nodal['W']['a'][2],12.)
        self.assertAlmostEqual(nodal['W']['b'][2],12.)

    def test_zone_split_preserves_analytic_resultant_and_first_moment(self):
        model,rules=fixture()
        rules['zones']=[{'startX':0.,'endX':1.,'D':2.,'Q':0.,'W':0.},
                        {'startX':1.,'endX':4.,'D':5.,'Q':0.,'W':0.}]
        nodal,_=reconstruct(model,rules)
        self.assertAlmostEqual(nodal['D']['a'][2],-14.75)
        self.assertAlmostEqual(nodal['D']['b'][2],-19.25)
        self.assertAlmostEqual(-4*nodal['D']['b'][2],77.)

    def test_axial_bar_weight_and_unresolved_equipment_tie(self):
        model,rules=fixture();model['materials'][0]['rho']=7850.
        for zone in rules['zones']:
            zone.update(D=0.,Q=0.,W=0.)
        rules['horizontalAction']['fxKN']=0.
        nodal,_=reconstruct(model,rules)
        total=7850*.002*math.sqrt(20)*9.80665/1000
        self.assertAlmostEqual(nodal['D']['a'][2],-total/2)
        self.assertAlmostEqual(nodal['D']['b'][2],-total/2)
        model['nodes'][1]['z']=1.
        rules['addedEquipment']={'positionX':2.,'weightKN':11.}
        with self.assertRaisesRegex(ValueError,'unresolved issued tie'):
            reconstruct(model,rules)


if __name__=='__main__':unittest.main()
