"""Offline diagnostic only; calibrated orthogonal-frame output families, no acceptance."""
import copy,hashlib,json,pathlib,struct,sys,traceback
import numpy as np
sys.path.insert(0,str(pathlib.Path('scripts/research300').resolve()))
from reference_solver import solve,DISPLACEMENTS,ACTIONS,REACTIONS
PathSolver=pathlib.Path('scripts/research300/reference_solver.py')
ROOT=pathlib.Path('.bench-work/commercial-246/pkpm-batch01');OUT=pathlib.Path('.bench-work/commercial-246/pkpm-independent-review/batch01');OUT.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def floats(p):return np.frombuffer(p.read_bytes(),dtype='<f4').astype(float)
def magnitude(rows,field='error'):return max((abs(v) for r in rows for v in r[field]),default=0)
def review(binding):
 base=ROOT/'remote-evidence'/binding['nativeIdentity'];source=pathlib.Path('corpora/research-300/cases')/binding['caseId']/('model-state-%d.json'%binding['state'])
 assert sha(source)==binding['sourceModelSha256'],'source sha mismatch'
 packet=read(base/'physical-input.json');assert sha(base/'physical-input.json')==binding['physicalPacketSha256'],'packet sha mismatch'
 model=read(source);sdk=read(base/'sdk-results.json');inp=read(base/'frame-input-receipt.json');audit=read(base/'frame-after-solve-input-audit.json');editdoc=read(base/'frame-numeric-input.json');edits=editdoc['edits'];edmap={e['sourceId']:e for e in edits}
 assert inp['inputSha256']==sha(base/'physical-input.json')
 assert packet['selection']=={'kind':binding['selectionKind'],'id':binding['selectionId'],'factors':binding['nativeCasePlan']['explicitSourceFactors']}
 assert binding['selectionKind']=='case' and binding['nativeCasePlan']['explicitSourceFactors']=={binding['selectionId']:1.0}
 nodes={n['id']:np.array([n[a] for a in 'xyz'],float) for n in model['nodes']};els={e['id']:e for e in model['elements']};sections={s['id']:s for s in model['sections']};pm={m['id']:m for m in packet['members']}
 assert set(els)==set(edmap)==set(pm)=={s['sourceId'] for s in sdk['members']}
 # Model basis class is a hard scope gate, never inferred from response.
 for eid,e in els.items():
  d=nodes[e['nodes'][1]]-nodes[e['nodes'][0]];R=np.array(pm[eid]['basisGlobal'])
  if e['type']=='column':assert np.allclose(d[:2],0) and d[2]>0;expected=[[0,0,1],[0,-1,0],[1,0,0]]
  elif e['type']=='beam':
   assert d[2]==0 and ((d[0]>0 and d[1]==0) or (d[1]>0 and d[0]==0))
   expected=[[1,0,0],[0,1,0],[0,0,1]] if d[0]>0 else [[0,1,0],[-1,0,0],[0,0,1]]
  else:raise AssertionError('unqualified element type')
  assert np.allclose(R,expected,atol=1e-12,rtol=0),'unqualified basis'
  assert e.get('rotation_angle',0)==0,'roll outside reviewed frame class'
 # Actual solver mechanical inputs, not rectangular carrier properties.
 actual=copy.deepcopy(model);actual['sections']=[];areas={};sectionchecks=[]
 rawdata={n:(base/n).read_bytes() for n in ['SDATA.SAT','DATA.SAT','SDATA.SAT.compiled-numeric','SDATA.SAT.before-numeric']}
 assert hashlib.sha256(rawdata['SDATA.SAT.compiled-numeric']).hexdigest()==editdoc['compiledSha256']
 assert hashlib.sha256(rawdata['SDATA.SAT.before-numeric']).hexdigest()==editdoc['beforeSha256']
 allowed=set()
 for ed in edits:
  a,j,ix,iy=ed['compiledAJIxIy'];eid=ed['sourceId'];offset=ed['offsetBytes'];allowed.update(range(offset,offset+16))
  assert list(struct.unpack('<4f',struct.pack('<4f',*ed['requestedAJIxIy'])))==ed['compiledAJIxIy']
  for name in ['SDATA.SAT','DATA.SAT','SDATA.SAT.compiled-numeric']:assert list(struct.unpack_from('<4f',rawdata[name],offset))==ed['compiledAJIxIy']
  sec=copy.deepcopy(sections[els[eid]['section']]);sec['id']=eid;sec['properties']={'A':a,'J':j,'Iy':iy if ed['kind']=='column' else ix,'Iz':ix if ed['kind']=='column' else iy};actual['sections'].append(sec)
  want=sections[els[eid]['section']]['properties'];requested=[want['A'],want['J'],want['Iz'] if ed['kind']=='column' else want['Iy'],want['Iy'] if ed['kind']=='column' else want['Iz']];assert np.allclose(ed['requestedAJIxIy'],requested,atol=1e-15,rtol=0)
  geo=np.array(struct.unpack_from('<6f',rawdata['SDATA.SAT'],offset-120+24)).reshape(2,3);expected=ed['endpointsM'][::-1] if ed['kind']=='column' else ed['endpointsM'];assert np.allclose(geo,expected,atol=1e-6,rtol=0)
  areas[eid]={'Asy':5*a/6,'Asz':5*a/6};sectionchecks.append({'member':eid,'actualAJIxIy':ed['compiledAJIxIy'],'nativeEndpointsM':geo.tolist()})
 before,compiled=rawdata['SDATA.SAT.before-numeric'],rawdata['SDATA.SAT.compiled-numeric'];assert len(before)==len(compiled);changed={i for i,(x,y) in enumerate(zip(before,compiled)) if x!=y};assert changed<=allowed
 for e in actual['elements']:e['section']=e['id']
 matbytes=(base/'UserMaterial.SAT').read_bytes();_,version,nmat,stride=struct.unpack_from('<4i',matbytes);assert version==20190824 and stride==96 and len(matbytes)==16+nmat*96
 materials=[];native_mat={}
 for i in range(nmat):
  pos=16+i*96;mid=struct.unpack_from('<i',matbytes,pos+36)[0];E,nu=struct.unpack_from('<dd',matbytes,pos+56);native_mat[mid]=(E,nu)
 for m in actual['materials']:
  rd=inp['materialReadbackAfterReopen'][m['id']];E,nu=native_mat[rd['nativeMaterialId']];assert E==1000*rd['nativeValues'][1] and nu==rd['nativeValues'][2]
  target=next(x for x in model['materials'] if x['id']==m['id']);assert np.isclose(E,target['E']*1000,atol=0,rtol=1e-14)
  G=E/(2*(1+nu));assert np.isclose(G,target['G']*1000,atol=0,rtol=1e-14),'native G differs source G'
  m.update(E=E/1000,G=G/1000,nu=nu);materials.append({'id':m['id'],'nativeId':rd['nativeMaterialId'],'E_kN_m2':E,'nu':nu,'G_derived_kN_m2':G})
 for m in audit['members']:
  bef=next(v for v in inp['members'] if v['sourceId']==m['sourceId']);assert m['segment']==bef['segmentReadback'];assert m['nativeMaterialId']==inp['materialReadbackAfterReopen'][els[m['sourceId']]['material']]['nativeMaterialId']
 for bef,aft in zip(inp['loads'],audit['loads']):assert bef['target']==aft['target'] and bef['definitionReadback']==aft['definition'] and bef['assignmentReadback']==aft['assignment']
 assert len(inp['loads'])==len(audit['loads'])==len(packet['loads'])
 assert audit['parametersMatchBefore']
 # Use NODEINDEX/MESH connectivity; DISP's observed floor groups are reversed.
 storycount=len(packet['stories']);ni=floats(base/'NODEINDEX.SAT');counts=[int(x) for x in ni[:storycount]];assert len(ni)==storycount+2*sum(counts)
 mesh=floats(base/'MESH.SAT')[5:].reshape(-1,5);nids=[int(x) for x in ni[storycount::2]];groups=[];pos=0
 for n in counts:groups.append(nids[pos:pos+n]);pos+=n
 raworder=[n for group in reversed(groups) for n in group];raw=floats(base/'DISP.SAT').reshape(-1,sum(counts),6);assert raw.shape[0]==2
 source_to_raw={}
 for i,idx in enumerate(raworder):
  xyz=mesh[idx-1,:3];matches=[nid for nid,v in nodes.items() if np.allclose(xyz,v,atol=1e-6,rtol=0)];assert len(matches)==1;source_to_raw[matches[0]]=i
 assert len(source_to_raw)==sum(not all(n['restraints']) for n in model['nodes'])
 sdktrans=[]
 for n in sdk['nodes']:
  if n['floor']==0:assert n['cases']['DL']==[-99999]*3;continue
  xyz=np.array(n['coordinates'])/1000;matches=[nid for nid,v in nodes.items() if np.allclose(xyz,v,atol=1e-6,rtol=0)];assert len(matches)==1;sid=matches[0];v=raw[0,source_to_raw[sid]][[0,1,5]];sdktrans.append({'node':sid,'sdk':n['cases']['DL'],'raw':v.tolist(),'error':(np.array(n['cases']['DL'])-v).tolist()})
 assert magnitude(sdktrans)<1e-10,'SDK and raw translation mismatch'
 assert np.all(raw[1]==0),'unexpected LL response'
 factors=binding['nativeCasePlan']['explicitSourceFactors'];q,checks=solve(actual,factors,[],effective_shear_areas=areas);qeb,_=solve(actual,factors,[])
 comparisons=[]
 for nid,i in source_to_raw.items():
  obs=raw[0,i][[0,1,5,3,4,2]];pred=np.array([q({'kind':'node','id':nid},c) for c in DISPLACEMENTS]);eb=np.array([qeb({'kind':'node','id':nid},c) for c in DISPLACEMENTS]);comparisons.append({'node':nid,'raw6':obs.tolist(),'predicted6':pred.tolist(),'error':(obs-pred).tolist(),'EBerror':(obs-eb).tolist()})
 # End forces and physical global joint equilibrium under calibrated source axes.
 endcmp=[];stationcmp=[];acc={nid:np.zeros(6) for nid in nodes};packet_loads={l['target']:l for l in packet['loads'] if l['type']=='distributed'}
 for m in sdk['members']:
  eid=m['sourceId'];e=els[eid];R=np.array(pm[eid]['basisGlobal']);L=pm[eid]['lengthM'];r=m['forces']['DL'];last=max(map(int,r));assert last==(8 if e['type']=='beam' else 1)
  h=[]
  for i in range(last+1):
   s=np.array(r[str(i)]);h.append(s*np.array([1,-1,-1,1,1,1]) if e['type']=='beam' else s[[0,2,1,3,5,4]]*np.array([1,1,-1,1,-1,1]))
  for i,x in [(0,0.),(last,L)]:
   pred=np.array([q({'kind':'element','id':eid,'positionM':x,'side':'right' if i==0 else 'left'},c) for c in ACTIONS]);endcmp.append({'member':eid,'positionM':x,'sourceACTIONS':h[i].tolist(),'predicted':pred.tolist(),'error':(h[i]-pred).tolist()});a=h[i]*np.array([-1,1,1,-1,-1,-1])*(1 if i==0 else -1);g=np.r_[R.T@a[:3],R.T@a[3:]];acc[e['nodes'][0 if i==0 else 1]]+=g
  if e['type']=='beam':
   load=packet_loads.get(eid,{'vector':[0,0,0]});wx,wy,wz=R@np.array(load['vector']);assert wx==wy==0,'uniform transverse z-only scope'
   for i,obs in enumerate(h):
    x=L*i/8;pred=h[0].copy();pred[2]+=wz*x;pred[4]-=h[0][2]*x+wz*x*x/2;pred[5]+=h[0][1]*x;stationcmp.append({'member':eid,'candidatePositionM':x,'error':(obs-pred).tolist()})
 external=np.zeros(6);point={nid:np.zeros(6) for nid in nodes}
 for ld in packet['loads']:
  if ld['type']=='nodal':f=np.array(ld['vector']);xyz=nodes[ld['target']];point[ld['target']]+=f
  else:m=pm[ld['target']];f=np.r_[np.array(ld['vector'])*m['lengthM'],[0,0,0]];xyz=np.mean(m['endpointsM'],axis=0)
  external+=np.r_[f[:3],f[3:]+np.cross(xyz,f[:3])]
 assembly=[];supports=np.zeros(6)
 for n in model['nodes']:
  nid=n['id'];target=point[nid].copy();g=acc[nid]
  if all(n['restraints']):target+=np.array([q({'kind':'node','id':nid},c) for c in REACTIONS]);supports+=np.r_[g[:3],g[3:]+np.cross(nodes[nid],g[:3])]
  assembly.append({'node':nid,'assembledNativeWrench':g.tolist(),'pointLoadOrIndependentSupport':target.tolist(),'error':(g-target).tolist()})
 summary={'case':binding['caseId'],'state':binding['state'],'selection':packet['selection'],'nativeIdentity':binding['nativeIdentity'],'nodeComponents':len(comparisons)*6,'maxDisplacementRotationAbs':magnitude(comparisons),'maxEulerBernoulliAbs':magnitude(comparisons,'EBerror'),'SDKtoDISPmaxAbs':magnitude(sdktrans),'endForceComponents':len(endcmp)*6,'maxEndForceAbs':magnitude(endcmp),'maxJointEquilibriumResidual':magnitude(assembly),'globalForceMomentResidual':(supports+external).tolist(),'maxGlobalEquilibriumResidual':float(np.max(np.abs(supports+external))),'maxCandidateStationIntegralResidual':magnitude(stationcmp),'benchmarkCasesQualified':0}
 report={'summary':summary,'scope':'Orthogonal frame diagnostic only. Asy=Asz=5A/6 explicit hypothesis; beam nine positions iL/8 diagnostic candidate; no case acceptance.','basisAndSigns':'Only positive global X/Y horizontal beams and +Z columns with packet reference basis. Beam SDK->source [s0,-s1,-s2,s3,s4,s5]; column [s0,s2,-s1,s3,-s5,s4], SDK bottom-to-top.','sources':{str(p):sha(p) for p in [source,PathSolver,ROOT/'local-bindings.json',*[base/n for n in ['physical-input.json','frame-input-receipt.json','frame-after-solve-input-audit.json','frame-numeric-input.json','SDATA.SAT','DATA.SAT','UserMaterial.SAT','DISP.SAT','MESH.SAT','NODEINDEX.SAT','sdk-results.json']]]},'checks':checks,'nativeMaterials':materials,'nativeSectionAndGeometry':sectionchecks,'compiledChangedByteCount':len(changed),'nativePostsolveMaterialsSegmentsLoadsConsistent':True,'freeNodeComparisons':comparisons,'SDKRawCrosscheck':sdktrans,'memberEndpointComparisons':endcmp,'candidateStationEquilibrium':stationcmp,'assembledNodeEquilibrium':assembly,'externalForceMomentAboutOrigin':external.tolist(),'nativeReconstructedSupportForceMoment':supports.tolist()}
 (OUT/(binding['nativeIdentity']+'.json')).write_text(json.dumps(report,indent=2)+'\n');return summary
rows=[]
for b in read(ROOT/'local-bindings.json'):
 p=ROOT/'remote-evidence'/b['nativeIdentity']
 if not (p/'sdk-results.json').exists():rows.append({'case':b['caseId'],'state':b['state'],'status':'not downloaded'});continue
 try:rows.append(review(b))
 except Exception as e:rows.append({'case':b['caseId'],'state':b['state'],'nativeIdentity':b['nativeIdentity'],'status':'independent audit stopped','error':repr(e),'traceback':traceback.format_exc()})
(OUT/'summary.json').write_text(json.dumps({'benchmarkCasesQualified':0,'results':rows},indent=2)+'\n')
for r in rows:print(json.dumps(r,ensure_ascii=False))
