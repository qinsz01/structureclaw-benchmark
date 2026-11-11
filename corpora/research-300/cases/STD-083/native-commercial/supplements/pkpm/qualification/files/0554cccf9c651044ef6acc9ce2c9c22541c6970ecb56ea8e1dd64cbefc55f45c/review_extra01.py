"""Independent offline extra controls. Uses raw native inputs, no SUT or acceptance writes."""
import copy,hashlib,json,pathlib,struct,sys
import numpy as np
sys.path.insert(0,str(pathlib.Path('scripts/research300').resolve()))
from reference_solver import solve,DISPLACEMENTS,ACTIONS,REACTIONS
ROOT=pathlib.Path('.bench-work/commercial-246/pkpm-extra01'); OUT=pathlib.Path('.bench-work/commercial-246/pkpm-independent-review/extra01');OUT.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def floats(p):return np.frombuffer(p.read_bytes(),dtype='<f4').astype(float)
def maxabs(rows,key='error'):return max((abs(x) for row in rows for x in row[key]),default=0.)
def prepare(base,model):
 packet=read(base/'physical-input.json');inp=read(base/'frame-input-receipt.json');post=read(base/'frame-after-solve-input-audit.json');edoc=read(base/'frame-numeric-input.json');sdk=read(base/'sdk-results.json')
 assert inp['inputSha256']==sha(base/'physical-input.json'); assert post['parametersMatchBefore']
 els={e['id']:e for e in model['elements']};pn={n['id']:n for n in packet['nodes']};pm={m['id']:m for m in packet['members']};sections={s['id']:s for s in model['sections']};nodes={n['id']:np.array([n[x] for x in 'xyz']) for n in model['nodes']}
 assert set(pn)==set(nodes);assert set(els)==set(pm)=={e['sourceId'] for e in edoc['edits']}=={e['sourceId'] for e in sdk['members']}
 for n in model['nodes']:
  assert [pn[n['id']][x] for x in 'xyz']==[n[x] for x in 'xyz'];assert pn[n['id']]['restraints']==n['restraints']
 for eid,e in els.items():
  d=nodes[e['nodes'][1]]-nodes[e['nodes'][0]];R=np.array(pm[eid]['basisGlobal'])
  if e['type']=='column':assert np.allclose(d[:2],0) and d[2]>0;expected=[[0,0,1],[0,-1,0],[1,0,0]]
  elif e['type']=='beam':
   assert d[2]==0 and ((d[0]>0 and d[1]==0) or (d[1]>0 and d[0]==0));expected=[[1,0,0],[0,1,0],[0,0,1]] if d[0]>0 else [[0,1,0],[-1,0,0],[0,0,1]]
  else:raise AssertionError('unqualified element class')
  assert np.allclose(R,expected,atol=1e-12,rtol=0);assert e.get('rotation_angle',0)==0
 actual=copy.deepcopy(model);actual['sections']=[];areas={};sectionchecks=[];allowed=set()
 raw={n:(base/n).read_bytes() for n in ['SDATA.SAT','DATA.SAT','SDATA.SAT.before-numeric','SDATA.SAT.compiled-numeric']}
 assert sha(base/'SDATA.SAT.before-numeric')==edoc['beforeSha256'];assert sha(base/'SDATA.SAT.compiled-numeric')==edoc['compiledSha256']
 for ed in edoc['edits']:
  eid=ed['sourceId'];off=ed['offsetBytes'];allowed.update(range(off,off+16));a,j,ix,iy=ed['compiledAJIxIy'];iscol=els[eid]['type']=='column';assert ed['kind']==els[eid]['type']
  want=sections[els[eid]['section']]['properties'];req=[want['A'],want['J'],want['Iz'] if iscol else want['Iy'],want['Iy'] if iscol else want['Iz']];assert np.allclose(req,ed['requestedAJIxIy'],atol=1e-15,rtol=0)
  assert list(struct.unpack('<4f',struct.pack('<4f',*req)))==ed['compiledAJIxIy']
  for n in ['SDATA.SAT','DATA.SAT','SDATA.SAT.compiled-numeric']:assert list(struct.unpack_from('<4f',raw[n],off))==ed['compiledAJIxIy']
  geo=np.array(struct.unpack_from('<6f',raw['SDATA.SAT'],off-120+24)).reshape(2,3);expected=[nodes[x].tolist() for x in els[eid]['nodes']];assert np.allclose(geo,expected[::-1] if iscol else expected,atol=1e-6,rtol=0)
  s=copy.deepcopy(sections[els[eid]['section']]);s.update(id=eid,properties={'A':a,'J':j,'Iy':iy if iscol else ix,'Iz':ix if iscol else iy});actual['sections'].append(s);areas[eid]={'Asy':5*a/6,'Asz':5*a/6};sectionchecks.append({'id':eid,'AJIxIy':ed['compiledAJIxIy'],'nativeGeometryM':geo.tolist()})
 before,compiled=raw['SDATA.SAT.before-numeric'],raw['SDATA.SAT.compiled-numeric'];assert len(before)==len(compiled);changed={i for i,(a,b) in enumerate(zip(before,compiled)) if a!=b};assert changed<=allowed
 for e in actual['elements']:e['section']=e['id']
 mb=(base/'UserMaterial.SAT').read_bytes();_,version,n,stride=struct.unpack_from('<4i',mb);assert version==20190824 and stride==96 and len(mb)==16+n*stride
 native={struct.unpack_from('<i',mb,16+i*stride+36)[0]:struct.unpack_from('<dd',mb,16+i*stride+56) for i in range(n)};materials=[]
 for m in actual['materials']:
  rd=inp['materialReadbackAfterReopen'][m['id']];E,nu=native[rd['nativeMaterialId']];G=E/(2*(1+nu));assert E==1000*rd['nativeValues'][1] and nu==rd['nativeValues'][2];assert np.isclose(E,1000*m['E'],rtol=1e-14,atol=0) and np.isclose(G,1000*m['G'],rtol=1e-14,atol=0)
  m.update(E=E/1000,G=G/1000,nu=nu);materials.append({'id':m['id'],'nativeId':rd['nativeMaterialId'],'nativeE_kN_m2':E,'nativeNu':nu,'derivedG_kN_m2':G})
 for a in post['members']:
  bef=next(x for x in inp['members'] if x['sourceId']==a['sourceId']);assert a['segment']==bef['segmentReadback'];assert a['nativeMaterialId']==inp['materialReadbackAfterReopen'][els[a['sourceId']]['material']]['nativeMaterialId']
 assert len(inp['loads'])==len(post['loads'])==len(packet['loads'])
 for a,b in zip(inp['loads'],post['loads']):assert a['target']==b['target'] and a['definitionReadback']==b['definition'] and a['assignmentReadback']==b['assignment']
 sources={str(p):sha(p) for p in [pathlib.Path(__file__),pathlib.Path('scripts/research300/reference_solver.py'),ROOT/'local-bindings.json',*[base/n for n in ['physical-input.json','frame-input-receipt.json','frame-after-solve-input-audit.json','frame-numeric-input.json','SDATA.SAT','DATA.SAT','SDATA.SAT.before-numeric','SDATA.SAT.compiled-numeric','UserMaterial.SAT','DISP.SAT','MESH.SAT','NODEINDEX.SAT','sdk-results.json']]]}
 return actual,areas,packet,sdk,{'sources':sources,'nativeMaterials':materials,'nativeSections':sectionchecks,'onlyDeclaredNumericBytesChanged':True,'nativePostsolveMaterialsSegmentsLoadsConsistent':True}
def raw_nodes(base,model,pin=None):
 packet=read(base/'physical-input.json');count=len(packet['stories']);ni=floats(base/'NODEINDEX.SAT');counts=[int(x) for x in ni[:count]];assert len(ni)==count+2*sum(counts)
 ids=[int(x) for x in ni[count::2]];groups=[];offset=0
 for n in counts:groups.append(ids[offset:offset+n]);offset+=n
 order=[i for g in reversed(groups) for i in g];mesh=floats(base/'MESH.SAT')[5:].reshape(-1,5);coords={n['id']:np.array([n[x] for x in 'xyz']) for n in model['nodes']};mapping={}
 for i,k in enumerate(order):
  matches=[nid for nid,xyz in coords.items() if np.allclose(xyz,mesh[k-1,:3],atol=1e-6,rtol=0)];assert len(matches)==1;mapping[matches[0]]=i
 if pin:mapping[pin]=len(order)
 raw=floats(base/'DISP.SAT').reshape(2,len(mapping),6)[:,:,[0,1,5,3,4,2]]
 return {nid:raw[:,i] for nid,i in mapping.items()}
def compare(base,actual,areas,packet,sdk,raw,factors,weights,selectedloads):
 q,checks=solve(actual,factors,[],effective_shear_areas=areas);qeb,_=solve(actual,factors,[]);nodes={n['id']:np.array([n[x] for x in 'xyz']) for n in actual['nodes']};els={e['id']:e for e in actual['elements']};pm={m['id']:m for m in packet['members']};comparisons=[];endcmp=[];acc={nid:np.zeros(6) for nid in nodes}
 for nid,rr in raw.items():
  obs=sum(weights[k]*rr[k] for k in weights);pred=np.array([q({'kind':'node','id':nid},c) for c in DISPLACEMENTS]);eb=np.array([qeb({'kind':'node','id':nid},c) for c in DISPLACEMENTS]);comparisons.append({'node':nid,'raw6':obs.tolist(),'idealConstraintPrediction':pred.tolist(),'error':(obs-pred).tolist(),'EBerror':(obs-eb).tolist()})
 for m in sdk['members']:
  eid=m['sourceId'];e=els[eid];R=np.array(pm[eid]['basisGlobal']);L=float(np.linalg.norm(nodes[e['nodes'][1]]-nodes[e['nodes'][0]]));last=8 if e['type']=='beam' else 1
  for i,x in [(0,0.),(last,L)]:
   s=sum(w*np.array(m['forces'][['DL','LL'][k]][str(i)]) for k,w in weights.items());h=s*np.array([1,-1,-1,1,1,1]) if e['type']=='beam' else s[[0,2,1,3,5,4]]*np.array([1,1,-1,1,-1,1]);pred=np.array([q({'kind':'element','id':eid,'positionM':x,'side':'right' if i==0 else 'left'},c) for c in ACTIONS]);endcmp.append({'member':eid,'positionM':x,'sourceACTIONS':h.tolist(),'predicted':pred.tolist(),'error':(h-pred).tolist()});a=h*np.array([-1,1,1,-1,-1,-1])*(1 if i==0 else -1);acc[e['nodes'][0 if i==0 else 1]]+=np.r_[R.T@a[:3],R.T@a[3:]]
 external=np.zeros(6);point={nid:np.zeros(6) for nid in nodes}
 for ld in selectedloads:
  if ld['type']=='nodal':f=np.array(ld['vector']);xyz=nodes[ld['target']];point[ld['target']]+=f
  else:
   e=els[ld['target']];L=np.linalg.norm(nodes[e['nodes'][1]]-nodes[e['nodes'][0]]);f=np.r_[np.array(ld['vector'])*L,[0,0,0]];xyz=np.mean([nodes[n] for n in e['nodes']],axis=0)
  external+=np.r_[f[:3],f[3:]+np.cross(xyz,f[:3])]
 assembly=[];supports=np.zeros(6)
 for n in actual['nodes']:
  nid=n['id'];target=point[nid].copy();g=acc[nid]
  if any(n['restraints']):target+=np.array([q({'kind':'node','id':nid},c) for c in REACTIONS]);supports+=np.r_[g[:3],g[3:]+np.cross(nodes[nid],g[:3])]
  assembly.append({'node':nid,'assembledNativeWrench':g.tolist(),'pointLoadOrIdealSupport':target.tolist(),'error':(g-target).tolist()})
 return {'factors':factors,'rawCaseWeights':weights,'nodeComparisons':comparisons,'endpointComparisons':endcmp,'jointComparisons':assembly,'checks':checks,'summary':{'nodeComponents':len(comparisons)*6,'nodeMaxAbs':maxabs(comparisons),'EBmaxAbs':maxabs(comparisons,'EBerror'),'endpointComponents':len(endcmp)*6,'endpointMaxAbs':maxabs(endcmp),'jointMaxAbs':maxabs(assembly),'externalForceMomentAboutOrigin':external.tolist(),'nativeReconstructedSupportForceMoment':supports.tolist(),'globalResidual':(supports+external).tolist(),'benchmarkCasesQualified':0}}
def pin_review():
 base=ROOT/'remote-evidence/c30-b-pincontrol';p=read(base/'physical-input.json');model={'schema_version':'2.2.0','unit_system':'SI','coordinate_system':{'dimension':'3d'},'nodes':p['nodes'],'elements':[{k:m[k] for k in ['id','type','nodes','material','section']} for m in p['members']],'materials':p['materials'],'sections':p['sections'],'analysis_control':p['analysisControl'],'metadata':{'elementReferenceVectors':{m['id']:m['basisGlobal'][2] for m in p['members']}},'load_combinations':[],'load_cases':[{'id':'CONTROL','type':'other','loads':[dict(id='P1',type='nodal',node='n001',reference_frame='global',**dict(zip(['fx','fy','fz','mx','my','mz'],p['loads'][0]['vector'])))]}]}
 actual,areas,packet,sdk,report=prepare(base,model);raw=raw_nodes(base,model,'n000');assert all(np.all(v[1]==0) for v in raw.values());cmp=compare(base,actual,areas,packet,sdk,raw,{'CONTROL':1},{0:1},p['loads']);report.update(scope='Independent pin control; As=5A/6 hypothesis, finite translation penalty distinguished from ideal fixed translations. Not benchmark acceptance.',comparison=cmp)
 # Verify exact allowed native constraint edits and unchanged post-solve payload.
 constraints=[]
 for rec in read(base/'native-pin-compilation.json'):
  name=rec['path'];before=(base/(name+'.before-pin')).read_bytes();compiled=(base/(name+'.compiled-pin')).read_bytes();after=(base/name).read_bytes();assert len(before)==len(compiled)==rec['bytes'];assert sha(base/(name+'.before-pin'))==rec['beforeSha256'];assert sha(base/(name+'.compiled-pin'))==rec['compiledSha256'];assert after==compiled
  off=rec['allowedByteOffset'];n=len(rec['compiledValues']);assert list(struct.unpack_from('<%dd'%n,compiled,off))==rec['compiledValues'];changed={i for i,(a,b) in enumerate(zip(before,compiled)) if a!=b};assert changed<=set(range(off,off+8*n));assert rec['compiledValues']==([1e14]*3+[0.]*3 if n==6 else [1e14,0,1e14,0,0,1e14]+[0.]*6)
  constraints.append({'file':name,'compiledSha256':rec['compiledSha256'],'postSolveUnchanged':True,'values':rec['compiledValues'],'changedByteCount':len(changed)});report['sources'].update({str(base/x):sha(base/x) for x in [name,name+'.before-pin',name+'.compiled-pin','native-pin-compilation.json','native-pin-postsolve.json','native-constraint-readback.json']})
 # Direct native OpenSees independent penalty control, separate from ideal-pin matrix result.
 import openseespy.opensees as ops
 ops.wipe();ops.model('basic','-ndm',3,'-ndf',6);tags={n['id']:i+1 for i,n in enumerate(actual['nodes'])};secs={s['id']:s['properties'] for s in actual['sections']};mats={m['id']:m for m in actual['materials']}
 for n in actual['nodes']:
  t=tags[n['id']];ops.node(t,*[n[x] for x in 'xyz']);ops.fix(t,*([0]*6 if n['id']=='n000' else [int(x) for x in n['restraints']]))
 ops.node(1000,0,0,0);ops.fix(1000,1,1,1,1,1,1);ops.uniaxialMaterial('Elastic',1000,1e14);ops.element('zeroLength',1000,1000,tags['n000'],'-mat',1000,1000,1000,'-dir',1,2,3)
 for i,e in enumerate(actual['elements'],1):
  s=secs[e['section']];m=mats[e['material']];ops.geomTransf('Linear',i,*actual['metadata']['elementReferenceVectors'][e['id']]);ops.element('ElasticTimoshenkoBeam',i,*[tags[x] for x in e['nodes']],1000*m['E'],1000*m['G'],s['A'],s['J'],s['Iy'],s['Iz'],areas[e['id']]['Asy'],areas[e['id']]['Asz'],i)
 ops.timeSeries('Linear',1);ops.pattern('Plain',1,1);ops.load(tags['n001'],*p['loads'][0]['vector']);ops.constraints('Plain');ops.numberer('RCM');ops.system('UmfPack');ops.integrator('LoadControl',1);ops.algorithm('Linear');ops.analysis('Static');assert ops.analyze(1)==0;ops.reactions();pencmp=[];idealshift=[]
 for row in cmp['nodeComparisons']:
  u=np.array(ops.nodeDisp(tags[row['node']]));pencmp.append({'node':row['node'],'prediction':u.tolist(),'error':(np.array(row['raw6'])-u).tolist()});idealshift.append({'node':row['node'],'error':(u-np.array(row['idealConstraintPrediction'])).tolist()})
 pinraw=raw['n000'][0];wrench=next(x['assembledNativeWrench'] for x in cmp['jointComparisons'] if x['node']=='n000');penres=np.array(wrench[:3])+1e14*pinraw[:3]
 report['pin']={'constraints':constraints,'rawSixDOF':pinraw.tolist(),'SDKReportsPinTranslations':[n['cases']['DL'] for n in sdk['nodes'] if np.allclose(np.array(n['coordinates'])/1000,[0,0,0])],'nativeReconstructedReaction':wrench,'reactionPlusKTimesDisplacement':penres.tolist(),'maxPenaltyEquilibriumResidual':float(max(abs(penres))),'freeRotationMaxAbsSupportMoment':max(abs(x) for x in wrench[3:]),'penaltyK_kN_per_m':1e14,'nativeOpenSeesPenaltyComparison':pencmp,'nativeOpenSeesPenaltyMaxAbs':maxabs(pencmp),'finitePenaltyMinusIdealElimination':idealshift,'finitePenaltyMaxDisplacementRotationChange':maxabs(idealshift),'interpretation':'Three rotations nonzero and three support moments zero to float32 endpoint force precision. Translation penalty is finite; SDK rounded translations to zero, raw DISP resolves compliance. Special support is final DISP record after four roof records, not listed by NODEINDEX; correspondence crosschecked by independent penalty response and R=-k*u.'}
 ops.wipe();(OUT/'pin-control-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'pin':cmp['summary'],'penaltyMaxAbs':report['pin']['nativeOpenSeesPenaltyMaxAbs'],'penaltyShift':report['pin']['finitePenaltyMaxDisplacementRotationChange'],'pinWrench':wrench,'penaltyResidual':penres.tolist()}))
if __name__=='__main__':pin_review()

def basic_and_sum_review():
 binding=read(ROOT/'local-bindings.json')['STD-091'];source=pathlib.Path('corpora/research-300/cases/STD-091/model-state-1.json');assert sha(source)==binding['sourceModelSha256'];model=read(source);base=ROOT/'remote-evidence'/binding['basicNativeIdentity'];direct=ROOT/'remote-evidence'/binding['directSumIdentity'];actual,areas,packet,sdk,report=prepare(base,model);actual2,areas2,packet2,sdk2,report2=prepare(direct,model)
 assert actual==actual2 and areas==areas2,'direct and separate case stiffness differs'
 assert packet['selection']=={'kind':'basic-cases','ids':['D','L'],'nativeCases':{'D':{'id':1,'name':'DL'},'L':{'id':2,'name':'LL'}}}
 assert packet2['selection']=={'kind':'case','id':'CONTROL_D_PLUS_L','sourceCombination':{'kind':'combination','id':'D+L','factors':{'D':1,'L':1}}}
 assert [(x['kind'],x['id'],x['sourceFactors']) for x in binding['typedSelections']]==[('combination','D',{'D':1}),('combination','D+L',{'D':1,'L':1})]
 case_loads={}
 for c in model['load_cases']:
  case_loads[c['id']]=[]
  for l in c['loads']:
   assert l['type']=='distributed' and l.get('reference_frame')=='global';assert set(l)<={'id','type','element','reference_frame','wx','wy','wz'};v=[l.get('w'+a,0) for a in 'xyz'];case_loads[c['id']].append({'type':'distributed','target':l['element'],'vector':v})
 expected=[dict(ld,nativeCaseId=1 if cid=='D' else 2,sourceCaseId=cid) for cid in ['D','L'] for ld in case_loads[cid]];assert packet['loads']==expected
 total={}
 for cid in ['D','L']:
  for ld in case_loads[cid]:total.setdefault(ld['target'],np.zeros(3));total[ld['target']]+=ld['vector']
 expected2=[{'type':'distributed','target':k,'vector':v.tolist()} for k,v in total.items()];assert packet2['loads']==expected2
 for native,pp in [(base,packet),(direct,packet2)]:
  receipt=read(native/'frame-input-receipt.json');post=read(native/'frame-after-solve-input-audit.json')
  for ld,rd,after in zip(pp['loads'],receipt['loads'],post['loads']):
   assert rd['kind']==12 and rd['definitionReadback']==[12,[1.,-ld['vector'][2],0.,0.,0.,0.]];assert ld['vector'][:2]==[0,0];cid=ld.get('nativeCaseId',1);cnt,cases,defs=after['assignment'];assert cnt==len(defs)==len(cases);assert (rd['definitionId'],cid) in list(zip(defs,cases))
 raw=raw_nodes(base,model);raw2=raw_nodes(direct,model);assert set(raw)==set(raw2);assert all(np.all(v[1]==0) for v in raw2.values());sdkraw=[]
 for native,ss,rr in [(base,sdk,raw),(direct,sdk2,raw2)]:
  coords={n['id']:np.array([n[x] for x in 'xyz']) for n in model['nodes']}
  for n in ss['nodes']:
   candidates=[nid for nid,v in coords.items() if np.allclose(v,np.array(n['coordinates'])/1000,rtol=0,atol=1e-6)];assert len(candidates)==1;nid=candidates[0]
   for k,name in enumerate(['DL','LL']):
    if nid not in rr:assert n['cases'][name]==[-99999]*3;continue
    sdkraw.append({'run':native.name,'node':nid,'case':name,'error':(np.array(n['cases'][name])-rr[nid][k,:3]).tolist()})
 assert maxabs(sdkraw)<1e-10
 results={}
 results['basicD']=compare(base,actual,areas,packet,sdk,raw,{'D':1},{0:1},case_loads['D'])
 results['basicL']=compare(base,actual,areas,packet,sdk,raw,{'L':1},{1:1},case_loads['L'])
 results['derivedDplusL']=compare(base,actual,areas,packet,sdk,raw,{'D':1,'L':1},{0:1,1:1},expected2)
 results['directDplusL']=compare(direct,actual2,areas2,packet2,sdk2,raw2,{'D':1,'L':1},{0:1},expected2)
 supernodes=[{'node':nid,'error':(rr[0]+rr[1]-raw2[nid][0]).tolist()} for nid,rr in raw.items()];superforces=[];sdkmap={m['sourceId']:m for m in sdk2['members']}
 for m in sdk['members']:
  mm=sdkmap[m['sourceId']];assert set(m['forces']['DL'])==set(m['forces']['LL'])==set(mm['forces']['DL'])
  for i,d in m['forces']['DL'].items():superforces.append({'member':m['sourceId'],'stationIndex':i,'error':(np.array(d)+m['forces']['LL'][i]-np.array(mm['forces']['DL'][i])).tolist()})
 report['sources'].update(report2['sources']);report['sources'][str(source)]=sha(source);report.update(scope='STD091 source typed combination D and D+L; independently matched D->DL, L->LL and direct combined input. Explicit As=5A/6 hypothesis with actual native material/float32 section. No report-level support reduction substituted. Pending benchmark acceptance.',typedSelections=[{k:s[k] for k in ['kind','id','sourceFactors']} for s in binding['typedSelections']],results=results,SDKRawCrosscheck=sdkraw,sourceNativeLoadDefinitionsAndAssignmentsVerified=True,superposition={'rawNodeComparison':supernodes,'allSDKForceSlotComparison':superforces,'maxNodeAbs':maxabs(supernodes),'maxForceAbs':maxabs(superforces)},benchmarkCasesQualified=0)
 (OUT/'std091-basic-direct-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'STD091':{k:v['summary'] for k,v in results.items()},'superposition':{k:v for k,v in report['superposition'].items() if k.startswith('max')}}))
if __name__=='__main__':basic_and_sum_review()
