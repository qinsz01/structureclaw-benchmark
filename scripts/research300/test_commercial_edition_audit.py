"""Negative controls for the independent retained-native readers (synthetic data)."""
from copy import deepcopy
import json
from pathlib import Path
import struct
import tempfile
import unittest

from audit_commercial_edition import pkpm, yjk, sha, DISP, REACTIONS, COMPONENTS, serialization_interval
from test_reference_solver import beam


def write(path, value):path.write_text(json.dumps(value))


def fixture():
    m=beam(dimension='3d',cantilever=True)
    m['sections'][0]['properties']={'A':.02,'Iy':.0006,'Iz':.0002,'J':.001,'Asy':.016,'Asz':.014}
    z={k:0. for k in DISP};r={k:0. for k in REACTIONS}
    rows=[{'positionM':x,'nativeComponents':[0.]*6,'components':dict.fromkeys(COMPONENTS,0.)} for x in [0.,6.]]
    result={'caseResults':{'D':{'displacements':{'a':z.copy(),'b':z.copy()},'reactions':{'a':r.copy(),'b':r.copy()},'memberStations':{'beam':rows}}},
            'summary':{'nativeLoadMapping':{'cases':{'D':{'nativeLabel':'DL'}}},'nativeMaterialVerification':{'materials':{'mat':{'nativeMaterialId':1}}}}}
    return m,result


class RetainedReaders(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
        self.m,self.r=fixture()

    def pkpm_files(self):
        p=self.p;s=self.m['sections'][0]['properties'];raw=struct.pack('<4f',*(s[k] for k in ['A','J','Iy','Iz']))
        (p/'SDATA.SAT').write_bytes(raw);(p/'SDATA.SAT.compiled').write_bytes(raw)
        write(p/'native-section-compilation.json',{'afterSha256':sha(p/'SDATA.SAT.compiled'),'members':{'beam':{'byteOffset':0}}})
        write(p/'native-stage-evidence.json',{'status':'completed','phases':[{'returncode':0}]})
        material=bytearray(112);struct.pack_into('<4i',material,0,3,20190824,1,96);struct.pack_into('<i',material,52,1);struct.pack_into('<dd',material,72,200000000.,.25)
        (p/'UserMaterial.SAT').write_bytes(material)
        (p/'MESH.SAT').write_bytes(bytes(20)+struct.pack('<3f2i',0,0,0,0,0)+struct.pack('<3f2i',6,0,0,0,0))
        (p/'NODEINDEX.SAT').write_bytes(struct.pack('<3f',1,2,0));(p/'ConstraintNodeNo.SAT').write_bytes(struct.pack('<6i',3,20200113,2,4,1,0))
        (p/'WDISPGKNO.OUT').write_text('DISP1.SAT DL\n');(p/'DISP.SAT').write_bytes(bytes(48))

    def yjk_files(self):
        p=self.p
        (p/'fea.dat').write_text('''*NODE
1 C=0,0,0
2 C=6,0,0
3 C=6,0,0
*FRAME
1 N=1,2 T=BEAM M=1 SEC=1 DIR=0,0,1 E=0,0 R=0,0 RF=1,1,1,1,1,1
*SECTION
1 P=0.02,0.0006,0.0002,0.001,0.014,0.016
*MATERIAL
1 P=2e8,0.25
*CONSTRAINT
1 R=1,1,1,1,1,1
''')
        sdk={'nodes':[{'id':i,**dict(zip('xyz',[x,0,0]))} for i,x in [(1,0),(2,6)]],
             'load_cases':[{'name':'SC_D','key':'d'}],
             'node_disp':{'d':[{'id':i,**dict.fromkeys(DISP,0.)} for i in [1,2]]},
             'node_reactions':{'d':[{'id':i,**dict.fromkeys(REACTIONS,0.)} for i in [1,2]]},
             'member_forces':{'beams':{'d':[{'id':1,'sections':[[0.]*6,[0.]*6]}]}}}
        write(p/'results.json',sdk);write(p/'mapping.json',{'load_cases':[{'sourceCaseId':'D','nativeName':'SC_D'}]});write(p/'native-physics-audit.json',{'passed':True})

    def test_pkpm_binary_inputs_displacements_and_reaction_tampering(self):
        self.pkpm_files();self.assertGreater(pkpm(self.p,self.m,self.r)['rawValuesChecked'],0)
        for kind in ['J','E','displacement','force','reaction']:
            with self.subTest(kind=kind):
                self.pkpm_files();m,r=deepcopy(self.m),deepcopy(self.r)
                if kind=='J':m['sections'][0]['properties']['J']*=1.1
                elif kind=='E':m['materials'][0]['E']*=1.1
                elif kind=='displacement':r['caseResults']['D']['displacements']['b']['rz']=.001
                elif kind=='force':r['caseResults']['D']['memberStations']['beam'][0]['components']['T']=1
                else:r['caseResults']['D']['reactions']['a']['mx']=1
                with self.assertRaises(ValueError):pkpm(self.p,m,r)

    def test_yjk_unused_coincident_nodes_are_allowed_but_input_and_sdk_changes_fail(self):
        self.yjk_files();self.assertGreater(yjk(self.p,self.m,self.r)['rawValuesChecked'],0)
        for kind in ['axis','rigidity','restraint','case','sdk']:
            with self.subTest(kind=kind):
                self.yjk_files();file=self.p/'fea.dat'
                if kind=='axis':file.write_text(file.read_text().replace('DIR=0,0,1','DIR=0,1,0'))
                elif kind=='rigidity':file.write_text(file.read_text().replace('RF=1,1,1,1,1,1','RF=1,1,1,1.01,1,1'))
                elif kind=='restraint':file.write_text(file.read_text().replace('R=1,1,1,1,1,1','R=1,1,1,1,0,1'))
                else:
                    file=self.p/'results.json';d=json.loads(file.read_text())
                    if kind=='case':d['load_cases'][0]['name']='OTHER'
                    else:d['node_disp']['d'][1]['uz']=.001
                    write(file,d)
                with self.assertRaises(ValueError):yjk(self.p,self.m,self.r)

    def test_text_rounding_interval_is_not_a_blanket_relative_tolerance(self):
        lo,hi=serialization_interval('.161333');self.assertLess(lo,.161333333333);self.assertGreater(hi,.161333333333)
        self.assertLess(hi,.161334)
        lo,hi=serialization_interval('1');self.assertLess(hi-lo,1.1e-5)


if __name__=='__main__':unittest.main()
