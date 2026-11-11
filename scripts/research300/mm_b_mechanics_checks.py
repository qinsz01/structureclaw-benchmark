"""Independent finite/stability/equilibrium checks of EXPORTED MM-B inputs.

Diagnostic only: this does not write numerical answers or establish native truth.
"""
import importlib.util,json,math
from mm_b_common import ROOT

def main():
 s=importlib.util.spec_from_file_location('mm_b_diagnostic_stiffness',ROOT/'scripts/independent-frame-reference.py');solver=importlib.util.module_from_spec(s);s.loader.exec_module(solver)
 selections=0;largest=0.;quantities=0
 for i in range(51,101):
  cid=f'MM-{i:03}';d=ROOT/'corpora/research-300/cases'/cid;m=json.loads((d/'model-state-1.json').read_text());state=json.loads((d/'reference-requests.json').read_text())['states'][0];groups={}
  for q in state['quantities']:groups.setdefault((q['selection']['kind'],q['selection']['id']),[]).append(q)
  vals={}
  for (kind,name),qs in groups.items():
   fac={name:1} if kind=='case' else next(c['factors'] for c in m['load_combinations'] if c['id']==name)
   quantity,diag=solver.solve(m,fac,[q['location'] for q in qs]);imb=max(map(abs,diag['forceMomentBalance']));assert imb<1e-7,(cid,kind,name,diag);largest=max(largest,imb)
   for q in qs:
    val=quantity(q['location'],q['component'].lower() if q['location']['kind']=='node' else q['component']);assert math.isfinite(val),(cid,q['id']);vals[q['id']]=val;quantities+=1
   selections+=1
  for dr in state['derived']:
   operands=[vals[k] for k in dr['operands']];assert dr['operation']=='difference' and len(operands)==2
   assert math.isfinite(operands[0]-operands[1])
 print(f'PASS exported 50 models / {selections} selections / {quantities} quantities; stable finite solves and full equilibrium; maximum imbalance {largest:.3g}. No reference artifacts written; native truth pending.')
if __name__=='__main__':main()
