"""Independent pin-batch review, coordinates and native support records bind raw DOFs."""
import importlib.util,json,pathlib,struct,re
import numpy as np
s=importlib.util.spec_from_file_location('extra',str(pathlib.Path(__file__).with_name('review_extra01.py')));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
ROOT=pathlib.Path('.bench-work/commercial-246/pkpm-pin-batch03');OUT=pathlib.Path('.bench-work/commercial-246/pkpm-independent-review/pin-batch03');OUT.mkdir(exist_ok=True);m.ROOT=ROOT
import openseespy.opensees as ops
def penalty_solve(actual,areas,pins,packet):
 ops.wipe();ops.model('basic','-ndm',3,'-ndf',6);tags={n['id']:i+1 for i,n in enumerate(actual['nodes'])};mats={x['id']:x for x in actual['materials']};secs={x['id']:x['properties'] for x in actual['sections']};els={};pm={e['id']:e for e in packet['members']}
 for n in actual['nodes']:
  ops.node(tags[n['id']],*[n[a] for a in 'xyz']);ops.fix(tags[n['id']],*([0]*6 if n['id'] in pins else list(map(int,n['restraints']))))
 ops.uniaxialMaterial('Elastic',1000,1e14)
 for i,nid in enumerate(pins,1000):
  n=next(x for x in actual['nodes'] if x['id']==nid);ops.node(i,*[n[a] for a in 'xyz']);ops.fix(i,1,1,1,1,1,1);ops.element('zeroLength',i,i,tags[nid],'-mat',1000,1000,1000,'-dir',1,2,3)
 for i,e in enumerate(actual['elements'],1):
  v=secs[e['section']];mat=mats[e['material']];sh=areas[e['id']];R=pm[e['id']]['basisGlobal'];ops.geomTransf('Linear',i,*R[2]);ops.element('ElasticTimoshenkoBeam',i,*[tags[n] for n in e['nodes']],1000*mat['E'],1000*mat['G'],v['A'],v['J'],v['Iy'],v['Iz'],sh['Asy'],sh['Asz'],i);els[e['id']]=i
 ops.timeSeries('Linear',1);ops.pattern('Plain',1,1)
 for ld in packet['loads']:
  if ld['type']=='nodal':ops.load(tags[ld['target']],*ld['vector'])
  else:
   local=np.array(pm[ld['target']]['basisGlobal'])@ld['vector'];ops.eleLoad('-ele',els[ld['target']],'-type','-beamUniform',local[1],local[2],local[0])
 ops.constraints('Plain');ops.numberer('RCM');ops.system('UmfPack');ops.integrator('LoadControl',1);ops.algorithm('Linear');ops.analysis('Static');assert ops.analyze(1)==0
 u={nid:np.array(ops.nodeDisp(t)) for nid,t in tags.items()};ops.wipe();return u
results=[]
for bind in m.read(ROOT/'local-bindings.json'):
 base=ROOT/'remote-evidence'/bind['nativeIdentity']
 if not (base/'sdk-results.json').exists():results.append({'case':bind['caseId'],'state':bind['state'],'status':'not downloaded'});continue
 src=pathlib.Path('corpora/research-300/cases')/bind['caseId']/('model-state-%d.json'%bind['state']);assert m.sha(src)==bind['sourceModelSha256'];assert m.sha(base/'physical-input.json')==bind['physicalPacketSha256'];model=m.read(src);actual,areas,packet,sdk,report=m.prepare(base,model);assert packet['selection']=={'kind':'case','id':'D','factors':{'D':1.0}}
 pins=[n['id'] for n in model['nodes'] if any(n['restraints']) and not all(n['restraints'])];assert pins and all(next(n['restraints'] for n in model['nodes'] if n['id']==nid)==[True]*3+[False]*3 for nid in pins)
 assert sorted(x['sourceNodeId'] for x in m.read(base/'native-pin-compilation.json')[0]['sourceBindings'])==sorted(pins)
 for rec in m.read(base/'native-pin-compilation.json'):
  name=rec['path'];b=(base/(name+'.before-pin')).read_bytes();c=(base/(name+'.compiled-pin')).read_bytes();a=(base/name).read_bytes();assert m.sha(base/(name+'.before-pin'))==rec['beforeSha256'] and m.sha(base/(name+'.compiled-pin'))==rec['compiledSha256'];assert a==c and len(b)==len(c);off=rec['allowedByteOffset'];nv=len(rec['compiledValues']);assert list(struct.unpack_from('<%dd'%nv,a,off))==rec['compiledValues'];assert rec['compiledValues']==([1e14]*3+[0]*3 if nv==6 else [1e14,0,1e14,0,0,1e14]+[0]*6);assert {i for i,(x,y) in enumerate(zip(b,c)) if x!=y}<=set(range(off,off+8*nv));report['sources'].update({str(base/n):m.sha(base/n) for n in [name,name+'.before-pin',name+'.compiled-pin']})
 coords={n['id']:np.array([n[a] for a in 'xyz']) for n in model['nodes']};mesh=m.floats(base/'MESH.SAT')[5:].reshape(-1,5);ni=m.floats(base/'NODEINDEX.SAT');st=len(packet['stories']);counts=list(map(int,ni[:st]));ids=list(map(int,ni[st::2]));groups=[];o=0
 for n in counts:groups.append(ids[o:o+n]);o+=n
 order=[i for g in reversed(groups) for i in g];cn=np.frombuffer((base/'ConstraintNodeNo.SAT').read_bytes(),dtype='<i4');assert cn[:4].tolist()==[3,20200113,len(mesh),4];pinindices=[i+1 for i,v in enumerate(cn[4:]) if v];assert len(pinindices)==len(pins);assert all(cn[4:][i-1]==1 for i in pinindices);order+=pinindices;rawmat=m.floats(base/'DISP.SAT').reshape(2,len(order),6)[:,:,[0,1,5,3,4,2]];raw={};indexmap=[]
 for k,idx in enumerate(order):
  hit=[nid for nid,xyz in coords.items() if np.allclose(mesh[idx-1,:3],xyz,atol=1e-6,rtol=0)];assert len(hit)==1;raw[hit[0]]=rawmat[:,k];indexmap.append({'sourceNode':hit[0],'meshIndex':idx,'DISPRecord':k,'specialBase':idx in pinindices})
 assert {x['sourceNode'] for x in indexmap if x['specialBase']}==set(pins);assert all(np.all(v[1]==0) for v in raw.values());wm=(base/'WMASS.OUT').read_bytes().decode('gb18030');assert [int(l.split(':')[-1]) for l in wm.splitlines() if '自由度为' in l]==[6*len(order)]*2
 # Public numerical source loads and native packet agree by global vector/target.
 want=[]
 for l in next(c for c in model['load_cases'] if c['id']=='D')['loads']:
  if l['type']=='distributed':want.append({'type':'distributed','target':l['element'],'vector':[l.get('w'+a,0) for a in 'xyz']})
  else:assert l['type']=='nodal';want.append({'type':'nodal','target':l['node'],'vector':[l.get(k,0) for k in ['fx','fy','fz','mx','my','mz']]})
 assert packet['loads']==want
 cmp=m.compare(base,actual,areas,packet,sdk,raw,{'D':1},{0:1},packet['loads']);pen=penalty_solve(actual,areas,pins,packet);pencmp=[];shift=[];pinchecks=[]
 for r in cmp['nodeComparisons']:
  u=pen[r['node']];pencmp.append({'node':r['node'],'error':(np.array(r['raw6'])-u).tolist()});shift.append({'node':r['node'],'error':(u-r['idealConstraintPrediction']).tolist()})
 for nid in pins:
  w=next(x['assembledNativeWrench'] for x in cmp['jointComparisons'] if x['node']==nid);u=raw[nid][0];pinchecks.append({'node':nid,'rawSixDOF':u.tolist(),'reconstructedSupportWrench':w,'reactionPlusKTimesTranslation':(np.array(w[:3])+1e14*u[:3]).tolist(),'maxFreeRotationSupportMoment':max(abs(x) for x in w[3:])})
 report['sources'][str(src)]=m.sha(src);report['sources'][str(pathlib.Path(__file__))]=m.sha(pathlib.Path(__file__));report['sources'].update({str(base/n):m.sha(base/n) for n in ['native-pin-compilation.json','native-pin-postsolve.json','ConstraintNodeNo.SAT','WMASS.OUT']});report.update(case=bind['caseId'],state=bind['state'],nativeIdentity=bind['nativeIdentity'],benchmarkCasesQualified=0,scope='Actual native E/nu/float32 AJI, As5A/6 hypothesis, pinned bases have finite1e14 translation springs and exact zero rotation stiffness. Ideal Dirichlet and finite penalty predictions both reported, no acceptance promotion.',rawIndexMapping=indexmap,comparison=cmp,pinChecks=pinchecks,penaltyComparison=pencmp,penaltyMinusIdeal=shift)
 summary=cmp['summary']|{'case':bind['caseId'],'state':bind['state'],'nativeIdentity':bind['nativeIdentity'],'pinCount':len(pins),'nativePenaltyMaxDOFAbs':m.maxabs(pencmp),'maxPenaltyMinusIdeal':m.maxabs(shift),'maxPinReactionPlusKu':max(abs(v) for x in pinchecks for v in x['reactionPlusKTimesTranslation']),'maxPinMoment':max(x['maxFreeRotationSupportMoment'] for x in pinchecks)};report['summary']=summary;(OUT/(bind['nativeIdentity']+'.json')).write_text(json.dumps(report,indent=2)+'\n');results.append(summary);print(json.dumps(summary))
(OUT/'summary.json').write_text(json.dumps({'benchmarkCasesQualified':0,'results':results},indent=2)+'\n')
