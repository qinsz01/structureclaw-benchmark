"""Behavioral regressions for the new read-only native evidence auditor."""
import copy, hashlib, importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'scripts/research300/audit_native_evidence.py'
def native_binary():
 explicit=os.environ.get('NATIVE_AUDIT_BINARY')
 if explicit:return pathlib.Path(explicit)
 spec=importlib.util.find_spec('openseespylinux')
 if spec and spec.origin:return pathlib.Path(spec.origin).parent/'opensees.so'
 raise unittest.SkipTest('Install the pinned Linux OpenSeesPy dependency or set NATIVE_AUDIT_BINARY')

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class NativeBundleTests(unittest.TestCase):
 case_id='STD-003'
 def setUp(self):
  self.case_id=getattr(self,'case_id','STD-003')
  self.binary=native_binary(); self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup);self.base=pathlib.Path(self.temp.name);self.root=self.base/'bench';self.native=self.base/'native';self.case=self.root/'corpora/research-300/cases'/self.case_id;self.raw=self.native/self.case_id
  shutil.copytree(ROOT/'corpora/research-300/cases'/self.case_id,self.case);self.raw.mkdir(parents=True)
  evidence_root=os.environ.get('NATIVE_AUDIT_EVIDENCE_ROOT')
  retained=pathlib.Path(evidence_root)/self.case_id if evidence_root else self.case
  for name in ['native-opensees-reference.json','native-input-receipt.json','native-solver-receipt.json','native-raw-responses.json','native-checks.json']:
   shutil.copyfile(retained/name,self.raw/name)
  (self.root/'scripts/research300').mkdir(parents=True)
  for f in ['opensees_native.py','reference_io.py']:shutil.copyfile(ROOT/'scripts/research300'/f,self.root/'scripts/research300'/f)
  # Preserve current exact code bindings in this synthetic review bundle. No solve is performed.
  for file in ['native-opensees-reference.json','native-solver-receipt.json']:
   d=self.read(file);d['solver']['runnerSha256']=digest(self.root/'scripts/research300/opensees_native.py');d['solver']['referenceIoSha256']=digest(self.root/'scripts/research300/reference_io.py');self.write(file,d)
  self.rehash()
 def read(self,name):return json.loads((self.raw/name).read_text())
 def write(self,name,value):(self.raw/name).write_text(json.dumps(value))
 def rehash(self):
  d=self.read('native-opensees-reference.json')
  for a in d['artifacts']:a['sha256']=digest(self.raw/a['path'])
  self.write('native-opensees-reference.json',d)
 def cli(self,output=None):
  out=output or self.base/'report.json';r=subprocess.run([sys.executable,str(SCRIPT),'--root',str(self.root),'--native-root',str(self.native),'--native-binary',str(self.binary),'--output',str(out)],capture_output=True,text=True)
  self.assertNotEqual(r.returncode,2,r.stderr)
  return r,json.loads(out.read_text()) if out.exists() else None

class AuditTests(NativeBundleTests):
 def test_valid_retained_bundle_and_per_case_binding(self):
  r,d=self.cli();self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(d['valid']);c=d['cases'][0];self.assertTrue(c['pass']);self.assertEqual(c['caseId'],'STD-003');self.assertEqual(c['nativeReferenceSha256'],digest(self.raw/'native-opensees-reference.json'));self.assertEqual(len(c['artifacts']),4);self.assertEqual(len(c['runs']),1);self.assertEqual(c['runs'][0]['analysisReturnCode'],0);self.assertTrue(d['snapshot'])
 def mutate_plan(self,fn):
  d=self.read('native-raw-responses.json');fn(d['runs'][0]['responses']['nativeInput']);self.write('native-raw-responses.json',d);self.rehash()
 def test_rehashed_wrong_material_is_rejected(self):
  self.mutate_plan(lambda p:p['members'][next(iter(p['members']))]['properties'].__setitem__('E',1));r,d=self.cli();self.assertEqual(r.returncode,1);self.assertTrue(any('property-E' in e['check'] for e in d['cases'][0]['errors']))
 def test_rehashed_wrong_restraint_is_rejected(self):
  self.mutate_plan(lambda p:p['nodes']['N0']['fixed'].__setitem__(0,False));r,d=self.cli();self.assertEqual(r.returncode,1);self.assertTrue(any('effective-restraints' in e['check'] for e in d['cases'][0]['errors']))
 def test_rehashed_wrong_load_work_is_rejected(self):
  self.mutate_plan(lambda p:p['pointLoads'][0]['globalForce'].__setitem__(2,0));r,d=self.cli();self.assertEqual(r.returncode,1);self.assertTrue(any('load-work' in e['check'] for e in d['cases'][0]['errors']))
 def test_stale_authored_bytes_are_rejected(self):
  (self.case/'prompt.txt').write_text('changed prompt');r,d=self.cli();self.assertEqual(r.returncode,1);self.assertTrue(any('source' in e['check'] for e in d['cases'][0]['errors']))
 def test_stale_driver_bytes_are_rejected(self):
  (self.root/'scripts/research300/opensees_native.py').write_text('changed driver');r,d=self.cli();self.assertEqual(r.returncode,1);self.assertTrue(any('code' in e['check'] for e in d['cases'][0]['errors']))
 def test_unbound_raw_bytes_are_rejected(self):
  d=self.read('native-checks.json');d['x']='changed';self.write('native-checks.json',d);r,d=self.cli();self.assertEqual(r.returncode,1);self.assertTrue(any('raw-sha' in e['check'] for e in d['cases'][0]['errors']))
 def test_declared_equilibrium_tolerance_cannot_be_inflated(self):
  for name in ['native-checks.json','native-opensees-reference.json']:
   d=self.read(name)
   if name=='native-checks.json':d['runs'][0]['checks']['balanceTolerance']=[1e30]*6
   else:
    d['checks'][0]['balanceTolerance']=[1e30]*6;d['states'][0]['checks'][0]['balanceTolerance']=[1e30]*6
   self.write(name,d)
  self.rehash();r,d=self.cli();self.assertEqual(r.returncode,1);self.assertTrue(any('tolerance-policy' in e['check'] for e in d['cases'][0]['errors']))
 def test_native_result_cannot_change_while_raw_stays_fixed(self):
  d=self.read('native-opensees-reference.json');d['states'][0]['quantities'][0]['value']+=999;self.write('native-opensees-reference.json',d)
  r,d=self.cli();self.assertEqual(r.returncode,1);self.assertTrue(any('raw-quantity' in e['check'] for e in d['cases'][0]['errors']))
 def test_unsupported_self_weight_fails_even_after_rebinding_source(self):
  d=self.read('native-input-receipt.json');d['states'][0]['model']['analysis_control']['self_weight']=True;self.write('native-input-receipt.json',d);self.rehash()
  (self.case/'model-state-1.json').write_text(json.dumps(d['states'][0]['model']))
  r,d=self.cli();self.assertEqual(r.returncode,1);self.assertTrue(any('unsupported-physics-control' in e['check'] for e in d['cases'][0]['errors']))
 def test_missing_case_is_rejected(self):
  shutil.rmtree(self.raw);r,d=self.cli();self.assertEqual(r.returncode,1);self.assertFalse(d['valid'])
 def test_output_is_exclusive(self):
  p=self.base/'report.json';p.write_text('sentinel');r=subprocess.run([sys.executable,str(SCRIPT),'--root',str(self.root),'--native-root',str(self.native),'--output',str(p)],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertEqual(p.read_text(),'sentinel')
 def test_output_cannot_create_in_evidence(self):
  p=self.native/'new.json';r=subprocess.run([sys.executable,str(SCRIPT),'--root',str(self.root),'--native-root',str(self.native),'--output',str(p)],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertFalse(p.exists())
 def test_symlink_raw_file_is_rejected(self):
  p=self.raw/'native-checks.json';other=self.base/'checks.json';p.rename(other);p.symlink_to(other);r,d=self.cli();self.assertEqual(r.returncode,1);self.assertFalse(d['cases'][0]['pass'])
 def test_euler_bundle_cannot_add_ignored_uniform_loads(self):
  self.mutate_plan(lambda p:p.__setitem__('uniformLoads',[{'elementTag':p['segments'][0]['tag'],'length':1,'globalIntensity':[0,0,1],'localIntensity':[0,0,1],'midpoint':[0,0,0]}]));r,d=self.cli();self.assertEqual(r.returncode,1);self.assertTrue(any(e['check']=='beam-load-representation' for e in d['cases'][0]['errors']))

class CommercialAuditTests(NativeBundleTests):
 case_id='STD-080'
 def test_declared_timoshenko_bundle_passes_independent_physics(self):
  r,d=self.cli();self.assertEqual(r.returncode,0,str(d['cases'][0]['errors'][:5]));self.assertTrue(d['valid']);self.assertGreater(d['cases'][0]['counts']['constitutive-segments'],0)
 def mutate(self,fn):
  d=self.read('native-raw-responses.json');fn(d['runs'][0]['responses']);self.write('native-raw-responses.json',d);self.rehash()
 def assert_rejected(self,check):
  r,d=self.cli();self.assertEqual(r.returncode,1);self.assertTrue(any(check in e['check'] for e in d['cases'][0]['errors']),str(d['cases'][0]['errors'][:5]))
 def test_rehashed_shear_area_cannot_override_public_rule(self):
  def change(r):
   p=r['nativeInput'];member=next(iter(p['members']));p['members'][member]['properties']['Asy']*=2;p['effectiveShearAreasM2'][member]['Asy']*=2
  self.mutate(change);self.assert_rejected('shear')
 def test_rehashed_uniform_load_work_is_rejected(self):
  self.mutate(lambda r:r['nativeInput']['uniformLoads'][0]['globalIntensity'].__setitem__(2,0));self.assert_rejected('load-work')
 def test_rehashed_uniform_local_axis_is_rejected(self):
  self.mutate(lambda r:r['nativeInput']['uniformLoads'][0]['localIntensity'].__setitem__(2,0));self.assert_rejected('uniform-load-axes')
 def test_rehashed_uniform_midpoint_is_rejected(self):
  self.mutate(lambda r:r['nativeInput']['uniformLoads'][0]['midpoint'].__setitem__(0,999));self.assert_rejected('uniform-load-midpoint')
 def test_rehashed_constitutive_displacement_is_rejected(self):
  def change(r):
   p=r['nativeInput'];node=next(n for n,v in p['nodes'].items() if not v['fixed'][2]);r['nodes'][node]['displacement'][2]+=.01
  self.mutate(change);self.assert_rejected('constitutive-beam-end-force')
 def test_rehashed_wrong_beam_theory_is_rejected(self):
  self.mutate(lambda r:r['nativeInput'].__setitem__('theory','Euler-Bernoulli'));self.assert_rejected('beam-theory')
 def test_unknown_uniform_element_is_rejected(self):
  self.mutate(lambda r:r['nativeInput']['uniformLoads'][0].__setitem__('elementTag',999999));self.assert_rejected('uniform-load-segment')
if __name__=='__main__':unittest.main()
