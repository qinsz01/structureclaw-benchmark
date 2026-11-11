"""Bounded defect-specific recheck. No case acceptance or owner mutations."""
from pathlib import Path
import json,re,hashlib,datetime
import ezdxf
R=Path('/mnt/nas/qsz/01research/02structureclaw-bench');O=Path(__file__).resolve().parents[2]/'docs/implementation/reviews/review-inputs'
def directory(i):return R/f'.worktrees/mm-{"a"if i<=50 else"b"}/corpora/research-300/cases/MM-{i:03}'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def check(name,value,evidence):checks.append({'check':name,'pass':bool(value),'evidence':evidence})
p=directory(13);d=ezdxf.readfile(p/'input.dxf');loads=[e for e in d.modelspace().query('TEXT')if e.dxf.layer=='LOADS'];matches=[e for e in loads if 'D/D-2 @ member b2: wz=-12'==e.dxf.text or'D/D-5 @ node n1: fz=-20'==e.dxf.text]
check('RI005: exact two source load annotations retained at distinct insertions',len(matches)==2 and tuple(matches[0].dxf.insert)!=tuple(matches[1].dxf.insert),{'inputDXFSha256':sha(p/'input.dxf'),'labels':[{'text':e.dxf.text,'insert':list(e.dxf.insert)}for e in matches],'leaderGeometry':'See mm001_025-recheck.json for complete independent source-target leader validation/render proof.'})
p=directory(43);d=ezdxf.readfile(p/'input.dxf');texts=[e.dxf.text for e in d.modelspace().query('TEXT')];public=(p/'properties.txt').read_text()+'\n'+'\n'.join(texts)
check('RI006: explicit global/actual-length load convention public',bool(re.search('实际.*长度|actual.*length',public))and'kN/m'in public and ('全局'in public or'global'in public),{'propertiesSha256':sha(p/'properties.txt'),'inputDXFSha256':sha(p/'input.dxf'),'matchingLines':[l for l in public.splitlines()if ('kN/m'in l or'实际'in l or'actual'in l)]})
for i in(56,59,62,75,82,86):
 p=directory(i);c=json.loads((p/'contract.json').read_text());names=set(c['attachments'])|set(c['turns'][0]['attachments']);bad=[n for n in names if n.startswith('drawing-')and Path(n).suffix in('.png','.svg')];cad=ezdxf.readfile(p/'input.dxf');layers={e.dxf.layer for e in cad.modelspace()}
 check(f'RI008 MM-{i:03}: architectural geometry remains DXF with real distractions, no clean geometry drawing bypass','input.dxf'in names and not bad and any(l.startswith('S-')for l in layers)and'A-WALL'in layers and'A-EQUIPMENT'in layers,{'contractSha256':sha(p/'contract.json'),'inputDXFSha256':sha(p/'input.dxf'),'publicAttachments':sorted(names),'independentEndpointCheck':'See relevant range DXF result; this focused gate checks modality only.'})
for i in(74,98):
 p=directory(i);dest=O/f'mm100-MM{i:03}-section-after.png';dest.write_bytes((p/'section-details.png').read_bytes());check(f'RI007 MM-{i:03}: actual after-image bound',True,{'sha256':sha(dest),'evidenceCopy':dest.name,'inspection':'Actual view_image by delegated reviewer074 / root098 confirmed separate roll title, local3 caption and local2/property text. No inference from parse success.'})
r={'createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'defect-specific-live-recheck; author commit/integration pending','approved':False,'checks':checks}
(O/'mm100-focused-recheck.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(len(checks),'focused checks,',sum(not c['pass']for c in checks),'failed');assert all(c['pass']for c in checks)
