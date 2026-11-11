"""Independent ezdxf entity inspection against source-directed endpoints.
Use PYTHONPATH=<root>/.bench-work/venv/lib/python3.10/site-packages python3 ...
No author renderer/check imports. Architecture view separation reconstructed from
DXF named view headers, each checked against physical source edges, not model JSON.
"""
import json,hashlib,collections,re,sys,datetime
from pathlib import Path
import ezdxf
from mm076_100_review import ROOT,OUT,expected,edge,pt
results=[]
for i in (81,82,84,86,91):
 p=ROOT/f'.worktrees/mm-b/corpora/research-300/cases/MM-{i:03}/input.dxf';data=p.read_bytes();d=ezdxf.readfile(p);ms=d.modelspace();en,ee=expected(i);checks=[]
 def ck(name,ok,detail=None):checks.append({'check':name,'pass':bool(ok),**({'detail':detail}if detail is not None else{})})
 lines=[e for e in ms.query('LINE')if e.dxf.layer in('S-BEAM','S-COLUMN','S-TRUSS')]
 if i in(81,84,91):
  got=collections.Counter((edge(e.dxf.start,e.dxf.end),e.dxf.layer)for e in lines)
  want=collections.Counter((ab,'S-'+kind.upper())for ab,kind in ee.items());ck('full structural XYZ endpoints/types/multiplicity match original source geometry',got==want)
  labels={e.dxf.text:pt(e.dxf.insert)for e in ms.query('TEXT')if e.dxf.layer=='NODE'}
  ck('all physical node labels present',len(labels)==len(en))
 else:
  headers=[e for e in ms.query('TEXT')if e.dxf.layer=='ANNOTATION'];total=0
  for h in headers:
   name=h.dxf.text.split(' |')[0];offset=h.dxf.insert.x
   if name.startswith('plan'):
    z=float(name.split('-Z')[1]);filter_fn=lambda a,b:a[2]==z and b[2]==z;project=lambda a:(a[0],a[1],0)
   elif name.startswith('elevation-YZ'):
    x=float(name.split('-X')[1]);filter_fn=lambda a,b:a[0]==x and b[0]==x;project=lambda a:(a[1],a[2],0)
   else:
    y=float(name.split('-Y')[1]);filter_fn=lambda a,b:a[1]==y and b[1]==y;project=lambda a:(a[0],a[2],0)
   want=collections.Counter((edge(project(a),project(b)),'S-'+kind.upper())for (a,b),kind in ee.items()if filter_fn(a,b)and project(a)!=project(b))
   chosen=[e for e in lines if offset-.001<=e.dxf.start.x<offset+39 and offset-.001<=e.dxf.end.x<offset+39];total+=len(chosen)
   got=collections.Counter((edge((e.dxf.start.x-offset,e.dxf.start.y,0),(e.dxf.end.x-offset,e.dxf.end.y,0)),e.dxf.layer)for e in chosen)
   ck(name+': projected endpoints/type/multiplicity under explicit40m-offset mapping',got==want,{'expectedCount':sum(want.values()),'actualCount':sum(got.values())})
  ck('all structural lines accounted for in named views',total==len(lines))
  layers=collections.Counter(e.dxf.layer for e in ms)
  ck('wall and equipment distractions are real separate nonstructural entities',layers['A-WALL']>0 and layers['A-EQUIPMENT']>0)
 # Save direct raw DXF evidence; no solver-bound artifact is modified.
 (OUT/f'mm076_100-MM{i:03}-input.dxf').write_bytes(data)
 results.append({'caseId':f'MM-{i:03}','path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'ezdxfVersion':ezdxf.__version__,'entityCounts':{str(k):v for k,v in collections.Counter((e.dxftype(),e.dxf.layer)for e in ms).items()},'checks':checks})
 print(i,[x for x in checks if not x['pass']])
(OUT/'mm076_100-dxf.json').write_text(json.dumps({'createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewKind':'independent DXF entity inspection; no CAD-editor or blind acceptance','cases':results},indent=2)+'\n')
sys.exit(int(any(not c['pass']for r in results for c in r['checks'])))
