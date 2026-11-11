"""Independent author mechanics checks for the 20 root-owned cases; no truth files."""
import importlib.util,math
from mm_b_common import ROOT
from mm_b_61_70 import build_specs as batch1
from mm_b_71_78_99_100 import build_specs as batch2
from mm_b_validate import source_specific

def run():
 source_specific()
 spec=importlib.util.spec_from_file_location('author_independent_frame',ROOT/'scripts/independent-frame-reference.py');solver=importlib.util.module_from_spec(spec);spec.loader.exec_module(solver)
 largest=0.;count=0
 for s in batch1()+batch2():
  m=s['model'];sels={}
  for q in s['requests']:
   sel=q.get('selection',{'kind':'case','id':'D'});sels.setdefault((sel['kind'],sel['id']),[]).append(q)
  for (kind,name),qs in sels.items():
   fac={name:1} if kind=='case' else next(c['factors'] for c in m['load_combinations'] if c['id']==name)
   result,diag=solver.solve(m,fac,[q['location'] for q in qs]);err=max(map(abs,diag['forceMomentBalance']));assert err<1e-7,(s['id'],name,diag)
   for q in qs:assert math.isfinite(result(q['location'],q['component'].lower() if q['location']['kind']=='node' else q['component']))
   if s['id']=='MM-061':
    assert abs(result({'kind':'node','id':'n0-0'},'my'))<1e-9
    assert abs(result({'kind':'node','id':'n2-0'},'fx'))<1e-9
   if s['id']=='MM-076':assert abs(result({'kind':'node','id':'n1-0'},'my'))<1e-9
   if s['id']=='MM-100':
    # External moment about base: (-1.5)*(-100)=150 X; -2*(-200)=400 Y; -(-1.5)*10=15 Z, plus Fy-arm horizontal force at Z=5 adds 50 Y.
    for comp,expected in [('mx',-150),('my',-450),('mz',-15)]:assert math.isclose(result({'kind':'node','id':'base'},comp),expected,abs_tol=1e-8)
   largest=max(largest,err);count+=1
 print(f'PASS 20 cases / {count} selections; independent stability, finite outputs, support freedoms and force/moment balance; max imbalance {largest:.3g}. Native acceptance pending.')
if __name__=='__main__':run()
