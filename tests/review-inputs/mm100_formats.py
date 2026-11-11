"""Decode/hash check all declared PNG/SVG against frozen source snapshot.
Successful parsing does not assert visual readability or blind recoverability.
"""
from pathlib import Path
import json,hashlib,io,xml.etree.ElementTree as ET
from PIL import Image
P=Path(__file__).resolve().parents[2]/'docs/implementation/reviews/review-inputs'
snap=json.loads((P/'mm100-snapshot.json').read_text());rows=[]
for case in snap['cases']:
 for f in case['files']:
  ext=Path(f['path']).suffix
  if ext not in('.png','.svg'):continue
  b=(Path(case['authorRoot'])/f['path']).read_bytes();row={'caseId':case['caseId'],'file':f['path'],'sha256':hashlib.sha256(b).hexdigest(),'format':ext,'matchesSnapshot':hashlib.sha256(b).hexdigest()==f['sha256']}
  try:
   if ext=='.png':
    with Image.open(io.BytesIO(b))as im:row['size']=im.size;im.verify()
   else:row['rootTag']=ET.fromstring(b).tag
   row['valid']=True
  except Exception as ex:row['valid']=False;row['error']=str(ex)
  rows.append(row)
report={'kind':'format integrity only, not actual image inspection','pngCount':sum(r['format']=='.png'for r in rows),'svgCount':sum(r['format']=='.svg'for r in rows),'rows':rows}
(P/'mm100-format-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(report['pngCount'],report['svgCount'],sum(not r['valid']or not r['matchesSnapshot']for r in rows),'errors/drift')
assert all(r['valid']and r['matchesSnapshot']for r in rows)
