"""Independent final delta/physics review of three repaired PKPM candidates.

No producer extraction/precision code or matrix solver is imported. Endpoint
scales are rebuilt from raw bytes using standalone closed-form coefficients.
"""
import copy,decimal,hashlib,json,math,re,struct
from pathlib import Path
REPO=Path(__file__).resolve().parents[3];BASE=REPO/'.bench-work/commercial-246';ROOT=BASE/'precision-repair';OUT=ROOT/'reviewed-v1'
REVIEWER='codex:/root/commercial_calibration_review'
OLDQUAL=BASE/'pkpm-independent-review/native-truth-qualification.json'
ACTIONS=['N','V2','V3','T','M2','M3']
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ev(p):return {'path':str(Path(p).resolve()),'sha256':sha(p)}
def ck(ok,msg):
 if not ok:raise ValueError(msg)
def exact(a,b):return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)
def verify_desc(d,root=REPO):
 p=root/d['path'];ck(sha(p)==d['sha256'],'SHA '+str(p));return p
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);ck(not p.exists(),'Refuse overwrite '+str(p));p.write_text(json.dumps(d,indent=2)+'\n')
def qualify(cid,newpath,detail,evidence):
 old=next(c for c in read(OLDQUAL)['cases'] if c['id']==cid);d=read(newpath);cp=REPO/'corpora/research-300/cases'/cid
 ck(d['sourceHash']==old['sourceHash'],'Old source changed')
 for f in d['sourceManifest']['files']:ck(sha(cp/f['path'])==f['sha256'],'Frozen source changed')
 reportpath=OUT/cid/'independent-repair-review.json';write(reportpath,detail)
 evidence += [ev(reportpath),ev(__file__),ev(newpath),ev(OLDQUAL)]
 checks=copy.deepcopy(old['checks']);checks['repairReview']=detail['summary'];checks['inputBlindReview']='pending-separate-gate';checks['acceptanceChanged']=False
 result={'schemaVersion':1,'reviewer':REVIEWER,'engine':'PKPM','reviewScope':'New named same-engine truth qualification for the exact revised candidate SHA. Prior native observations and old qualification remain historical; input blind review and agent acceptance are separate pending gates.','cases':[{'id':cid,'status':'qualified','sourceHash':d['sourceHash'],'oldSourceHash':old['sourceHash'],'candidateSha256':sha(newpath),'oldCandidateSha256':old['candidateSha256'],'reasons':[],'checks':checks,'evidence':list({e['path']:e for e in evidence}.values())}]}
 p=OUT/cid/'native-truth-qualification.json';write(p,result);return {'id':cid,'report':str(p.relative_to(REPO)),'sha256':sha(p),'candidateSha256':sha(newpath)}
def pin_reviews():
 proofpath=ROOT/'free-boundary-review.json';proof=read(proofpath);manifestpath=ROOT/'pin-candidates-v1/manifest.json';manifest=read(manifestpath)
 ck(proof['status']=='qualified-boundary-derivation' and len(proof['quantities'])==3,'Boundary proof status')
 all_sources=proof['sources']+[s for q in proof['quantities'] for s in q['sources']]
 for s in all_sources:verify_desc(s)
 ck(manifest['repairedQuantities']==3,'Repair count');verify_desc(manifest['review'])
 answers=[]
 for case in proof['cases']:
  cid=case['id'];oldpath=verify_desc(case['candidate']);verify_desc(case['qualification']);old=read(oldpath);newpath=ROOT/'pin-candidates-v1'/cid/'native-reference.json';new=read(newpath)
  manifestrow,=[r for r in manifest['results'] if r['caseId']==cid];ck(sha(newpath)==manifestrow['sha256'],'New candidate manifest mismatch')
  expected=copy.deepcopy(old);expected['status']='candidate-only; free-boundary derivation requires independent review'
  evidence=[ev(proofpath),ev(manifestpath),ev(oldpath),ev(REPO/'scripts/research300/commercial/pkpm_boundary_repair.py')]
  changes=[]
  for row in [q for q in proof['quantities'] if q['caseId']==cid]:
   ck(all(row[k] is True and row['facts'][k] is True for k in ['zeroRotationStiffness','noCoupling','noAdditionalConstraint','freeDofsRetained','noSupportNodalLoad']),'Missing boundary facts')
   state=next(s for s in expected['states'] if s['state']==row['state']);q=next(q for q in state['quantities'] if q['id']==row['quantityId'])
   ck(exact(q['value'],row['oldValue']) and exact(q['rawTrace'],row['oldRawTrace']),'Boundary original trace mismatch')
   for block in row['proof']['executedConstraintBlocks']:
    desc,=[s for s in row['sources'] if Path(s['path']).name==block['artifact'] and Path(s['path']).parent.name==row['nativeRun']]
    p=verify_desc(desc);data=p.read_bytes();compiled=Path(str(p)+'.compiled-pin').read_bytes();ck(data==compiled,'Postsolve support changed')
    v=list(struct.unpack_from('<%dd'%len(block['executedValues']),data,block['offsetBytes']));target=[1e14]*3+[0]*3 if block['artifact']=='ConstraintNode.SAT' else [1e14,0,1e14,0,0,1e14]+[0]*6
    ck(v==block['executedValues']==target,'Native rotational block nonzero')
   preserved={'value':q['value'],'rawTrace':copy.deepcopy(q['rawTrace'])}
   q.update(value=0.0,quantityStatus='derived-from-native-free-boundary',rawTrace={'origin':'derived-from-native-free-boundary','ruleVersion':proof['ruleVersion'],'review':manifest['review'],'reviewer':proof['reviewer'],'nativeRun':row['nativeRun'],'sourceModelSha256':row['modelSha256'],'sourceSelection':row['selection'],'rawMemberEndEquilibrium':preserved,'derivedValue':0.0,'unit':q['unit']})
   ck(state['derived']==[],'Unexpected derived dependency')
   changes.append({'state':row['state'],'quantityId':row['quantityId'],'oldValue':row['oldValue'],'newValue':0.0,'completeOldTracePreserved':True,'nativeZeroRotationBytesRechecked':True})
  expected['boundaryRepair']={'ruleVersion':proof['ruleVersion'],'review':manifest['review'],'oldCandidate':case['candidate'],'oldQualification':case['qualification'],'tool':{'path':'pkpm_boundary_repair.py','sha256':sha(REPO/'scripts/research300/commercial/pkpm_boundary_repair.py')},'qualificationStatus':'pending','repairedQuantities':len(changes)}
  ck(exact(expected,new),'Unapproved candidate diff '+cid)
  detail={'schemaVersion':1,'reviewer':REVIEWER,'case':cid,'summary':{'boundaryDerivedQuantities':len(changes),'allOtherQuantityValuesAndTracesUnchanged':True,'allFrozenRequestMetadataAndTolerancesUnchanged':True,'allNativeArtifactsUnchanged':True,'boundaryEvidenceDescriptorsRehashed':len(all_sources),'oldQualificationPreserved':True,'candidateStatusStillPending':True},'changes':changes,'allowedTopLevelChanges':['status','boundaryRepair'],'comparison':'Exact canonical JSON identity after applying only the independently authorized boundary operation, including signed zero.','evidence':[ev(proofpath),ev(oldpath),ev(newpath)]}
  evidence += [ev(REPO/s['path']) for r in proof['quantities'] if r['caseId']==cid for s in r['sources']]
  answers.append(qualify(cid,newpath,detail,evidence))
 return answers

def floats(path):
 b=Path(path).read_bytes();ck(len(b)%4==0,'Float record size');return struct.unpack('<%df'%(len(b)//4),b)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(v):return math.sqrt(dot(v,v))
def unit(v):d=norm(v);return [x/d for x in v]
def source_basis(model,e,nodes):
 x=unit([nodes[e['nodes'][1]][k]-nodes[e['nodes'][0]][k] for k in 'xyz']);y=unit(cross(model['metadata']['elementReferenceVectors'][e['id']],x));return [x,y,cross(x,y)]
def closed_terms(comp,end,d,loads,p):
 # Coefficients are evaluated independently in 80-digit decimal arithmetic.
 # This does not emulate or infer the native solver's floating-point sequence.
 with decimal.localcontext() as ctx:
  ctx.prec=80;D=decimal.Decimal;E,G,A,J,Iy,Iz,L=[D.from_float(p[k]) for k in ['E','G','A','J','Iy','Iz','length']]
  if comp in ['N','T']:
   z=E*A/L if comp=='N' else G*J/L;indices=[0,6] if comp=='N' else [3,9];coeff=[-z,z]
  else:
   I=Iz if comp in ['V2','M3'] else Iy;phi=D(12)*E*I/(G*(D(5)*A/D(6))*L*L);den=1+phi
   a=D(12)*E*I/(L**3*den);b=D(6)*E*I/(L**2*den);c=(4+phi)*E*I/(L*den);h=(2-phi)*E*I/(L*den)
   indices=[1,5,7,11] if comp in ['V2','M3'] else [2,4,8,10]
   if comp=='V2':coeff=[a,b,-a,b]
   elif comp=='V3':coeff=[a,-b,-a,-b]
   elif comp=='M3':coeff=[-b,-c,b,-h] if end==0 else [b,h,-b,c]
   else:coeff=[b,-c,-b,-h] if end==0 else [-b,h,b,c]
  row=ACTIONS.index(comp)+6*end;terms=[float(c0*D.from_float(d[i])) for i,c0 in zip(indices,coeff)];labels=[f'k[{row},{i}]*d[{i}]' for i in indices]
  for j,load in enumerate(loads):
   qx,qy,qz=[D.from_float(float(v)) for v in load]
   # Uniform consistent nodal loading and source inward-cut signs.
   if comp=='N':v=qx*L/D(2)*(1 if end==0 else -1)
   elif comp=='T':v=D(0)
   elif comp=='V2':v=qy*L/D(2)*(-1 if end==0 else 1)
   elif comp=='V3':v=qz*L/D(2)*(-1 if end==0 else 1)
   elif comp=='M2':v=-qz*L*L/D(12)
   else:v=qy*L*L/D(12)
   if v!=0:terms.append(float(v));labels.append(f'-fixedEndLoad[{j},{row}]')
  return terms,labels

def std_review():
 cid='STD-089';cp=REPO/'corpora/research-300/cases'/cid;oldpath=BASE/'pkpm-request-export/final03'/cid/'native-reference.json';old=read(oldpath);newpath=ROOT/'STD-089-v1/native-reference.json';new=read(newpath);certpath=ROOT/'STD-089-v1/precision/certificate.json';cert=read(certpath);receiptpath=ROOT/'STD-089-v1/precision-generation-receipt.json';receipt=read(receiptpath)
 ck(cert['oldCandidateSha256']==sha(oldpath)==receipt['oldCandidateSha256'],'Old certificate source differs');ck(sha(newpath)==receipt['candidateSha256'] and sha(certpath)==receipt['certificateSha256'],'New certificate digest')
 ck(cert['sourceHash']==old['sourceHash']==new['sourceHash'],'Source hash changed')
 sources=[]
 roots={'repository-code':REPO,'native-evidence-manifest':BASE,'old-candidate':oldpath.parent,'authored-source':REPO/'corpora/research-300/cases','native-raw':BASE,'native-stage':BASE}
 for s in cert['sources']:
  ck(s['kind'] in roots,'Unknown source kind');p=verify_desc(s,roots[s['kind']]);sources.append(ev(p))
 entry,=[r for r in read(BASE/'pkpm-candidate-evidence-manifest.json')['runs'] if r['caseId']==cid];run=BASE/entry['runRoot']/'remote-evidence'/entry['nativeIdentity'];model=read(cp/'model-state-1.json');packet=read(run/'physical-input.json');native_receipt=read(run/'frame-input-receipt.json');native_input=read(run/'frame-numeric-input.json');nodes={n['id']:n for n in model['nodes']};elements={e['id']:e for e in model['elements']}
 physical_report=BASE/'pkpm-independent-review/batch01'/f"{entry['nativeIdentity']}.json";prior=read(physical_report)
 for path,digest in prior['sources'].items():ck(sha(path)==digest,'Prior report source changed');sources.append(ev(path))
 ck(prior['nativePostsolveMaterialsSegmentsLoadsConsistent'] is True,'Physical model audit missing');sources.append(ev(physical_report))
 meshraw=(run/'MESH.SAT').read_bytes();mf=struct.unpack('<%df'%(len(meshraw)//4),meshraw);mi=struct.unpack('<%di'%(len(meshraw)//4),meshraw);mesh=[mf[i:i+5] for i in range(5,len(mf),5)];flags=[mi[i+3] for i in range(5,len(mi),5)]
 index=floats(run/'NODEINDEX.SAT');stories=len(model['stories']);counts=list(map(int,index[:stories]));ids=list(map(int,index[stories::2]));ck(len(index)==stories+2*sum(counts) and all(x==0 for x in index[stories+1::2]),'Native index structure')
 groups=[];at=0
 for count in counts:groups.append(ids[at:at+count]);at+=count
 order=[i for group in reversed(groups) for i in group];disp=floats(run/'DISP.SAT');ck(len(disp)==2*len(order)*6,'DISP size');ck(all(x==0 for x in disp[len(order)*6:]),'Unexpected native LL')
 cnraw=(run/'ConstraintNodeNo.SAT').read_bytes();cn=struct.unpack('<%di'%(len(cnraw)//4),cnraw);ck(cn[:4]==(3,20200113,len(mesh),4) and all(x==0 for x in cn[4:]),'Special constraint');ck(not (run/'ConstraintNode.SAT').exists() and not (run/'ConstraintNodeSK.SAT').exists(),'Support override')
 wm=(run/'WMASS.OUT').read_bytes().decode('gb18030');spas=(run/'spas_sat.txt').read_bytes().decode('gb18030');dofs=[int(l.split(':')[-1]) for l in wm.splitlines() if '自由度为' in l];ck(dofs==[6*len(order)]*2,'Fixed DOF count');ck(re.search(r'嵌固端所在层号:\s+MQIANGU=\s+1',wm) is not None,'Embed level');ck(re.search(r'# 约束节点类型信息\s+0\s',spas) is not None,'Native support definition')
 chunk=spas.split('# 节点信息',1)[1].split('# 网格线信息',1)[0];node_rows={int(m[1]):[float(v) for v in m[3].rstrip(',').split(',')] for m in re.finditer(r'^#(\d+):([^\r\n]+)\r?\n([^\r\n]+)',chunk,re.M)}
 displacements={};node_bindings={};fixed_proofs=[]
 for nid,node in nodes.items():
  matches=[i+1 for i,v in enumerate(mesh) if all(abs(v[j]-node[k])<1e-6 for j,k in enumerate('xyz'))];ck(len(matches)==1,'Coordinate ambiguous');mesh_id=matches[0];t=node_rows[mesh_id]
  if all(node['restraints']):
   ck(mesh_id not in ids and flags[mesh_id-1]==-1 and t[4:10]==[1]*6 and t[10:16]==[-1]*6 and t[20]==0,'Fixed boundary evidence incomplete')
   displacements[nid]=[0.0]*6;node_bindings[nid]={'node':nid,'origin':'prescribed-fixed-boundary-for-scale-only','meshIndex':mesh_id,'proof':'Six source restraints; MESH fixed flag; eliminated from NODEINDEX/DISP; no special constraints.'};fixed_proofs.append({'node':nid,'meshIndex':mesh_id,'nativePattern':t[4:16],'override':t[20]})
  else:
   ck(not any(node['restraints']) and mesh_id in order and flags[mesh_id-1]==100 and t[4:16]==[0]*12,'Unreviewed free boundary');record=order.index(mesh_id);i=record*6;displacements[nid]=[disp[i+j] for j in [0,1,5,3,4,2]];node_bindings[nid]={'node':nid,'origin':'native-DISP-DL','meshIndex':mesh_id,'record':record,'byteOffset':record*24}
 ck(len(order)+len(fixed_proofs)==len(nodes),'Native node coverage')
 for n in ['WMASS.OUT','spas_sat.txt','ConstraintNodeNo.SAT','MESH.SAT','NODEINDEX.SAT','DISP.SAT']:sources.append(ev(run/n))
 sources += [ev(BASE/'pkpm-independent-review/fixed-boundary-derived-review.json'),ev(BASE/'pkpm-independent-review/extra01/pin-control-review.json')]
 user=(run/'UserMaterial.SAT').read_bytes();head=struct.unpack_from('<4i',user);ck(head[0:2]==(3,20190824) and head[3]==96 and len(user)==16+96*head[2],'Material format');materials={}
 for i in range(head[2]):
  off=16+i*96;identity=struct.unpack_from('<i',user,off+36)[0];ck(identity not in materials,'Duplicate material');materials[identity]=struct.unpack_from('<dd',user,off+56)
 sd=(run/'SDATA.SAT').read_bytes();dt=(run/'DATA.SAT').read_bytes();params={}
 for edit in native_input['edits']:
  eid=edit['sourceId'];e=elements[eid];off=edit['offsetBytes'];A,J,ix,iy=struct.unpack_from('<4f',sd,off);ck(list((A,J,ix,iy))==edit['compiledAJIxIy']==list(struct.unpack_from('<4f',dt,off)),'Native property drift');coord=list(struct.unpack_from('<6f',sd,off-96));a,b=coord[:3],coord[3:]
  if e['type']=='column':a,b=b,a
  expected=[[nodes[n][k] for k in 'xyz'] for n in e['nodes']];ck(all(abs(x-y)<1e-6 for x,y in zip(a+b,expected[0]+expected[1])),'Native end ordering');E,nu=materials[native_receipt['materialReadbackAfterReopen'][e['material']]['nativeMaterialId']];params[eid]={'length':math.dist(a,b),'E':E,'G':E/(2*(1+nu)),'A':A,'J':J,'Iy':iy if e['type']=='column' else ix,'Iz':ix if e['type']=='column' else iy}
 certrows={(r['state'],r['id']):r for r in cert['quantities']};ck(len(certrows)==len(cert['quantities'])==120,'Precision coverage duplicates');expected=copy.deepcopy(old);covered=[];excluded=[];rounding_ulp=[];details=[]
 for state in expected['states']:
  for q in state['quantities']:
   key=(state['state'],q['id'])
   if q['location']['kind']!='member':ck(key not in certrows,'Node wrongly certified');excluded.append(q['id']);continue
   cr=certrows[key];eid=q['location']['id'];e=elements[eid];basis=source_basis(model,e,nodes);d=[]
   for nid in e['nodes']:
    u=displacements[nid];d.extend(dot(row,u[:3]) for row in basis);d.extend(dot(row,u[3:]) for row in basis)
   loads=[ [dot(row,load['vector']) for row in basis] for load in packet['loads'] if load['target']==eid]
   ck(all(load['type']=='distributed' for load in packet['loads'] if load['target']==eid),'Unexpected member load');end=q['rawTrace']['end'];p=params[eid];terms,labels=closed_terms(q['component'],end,d,loads,p);rec=cr['recovery'];meta=cr['precision']
   ck(all(cr[k]==q[k] for k in ['id','selection','component','location','unit']),'Certificate request metadata');ck(rec['nativeRun']==entry['nativeIdentity'],'Native run differs');ck(rec['nativeMechanicalParameters']==p and rec['localDisplacements']==d and rec['localUniformLoads']==loads,'Raw recovered inputs differ');ck(rec['termLabels']==labels,'Canonical term labeling/sparsity');ck(len(terms)==meta['structuralTermCount']==len(meta['terms']),'Structural count')
   for actual,want in zip(meta['terms'],terms):
    ck((actual==want==0) or abs(actual-want)<=2e-14*abs(want),'Independent closed-form term mismatch');rounding_ulp.append(abs(actual-want)/math.ulp(want) if want!=0 else 0)
   ck({m['node']:m for m in rec['nodeMappings']}=={nid:node_bindings[nid] for nid in e['nodes']},'DOF mapping differs')
   n=len(terms);u=2**-24;scale=math.fsum(abs(v) for v in meta['terms']);allowance=((2*n-1)*u/(1-(2*n-1)*u))*scale
   expected_meta={'kind':'analytical-recovery-scale','policy':'native-f32-recovery-scale-v1','nativeArithmeticBound':False,'acceptanceRegionChanges':True,'unit':q['unit'],'unitRoundoff':u,'terms':meta['terms'],'structuralTermCount':n,'recoveryScale':scale,'absoluteAllowance':allowance}
   ck(exact(expected_meta,meta),'Precision formula/flags differ');q['engineeringPrecision']=dict(expected_meta,certificateSha256=sha(certpath));covered.append(q['id']);details.append({'id':q['id'],'component':q['component'],'structuralTermCount':n,'independentDecimalTerms':terms,'certificateTerms':meta['terms'],'recoveryScale':scale,'absoluteAllowance':allowance,'nodeMappingsVerified':True})
 ck(len(covered)==120 and len(excluded)==81 and all(s['derived']==[] for s in old['states']),'Full family coverage')
 expected['nativeArtifacts']['precision']={'certificate.json':{'path':'precision/certificate.json','sha256':sha(certpath)}};expected['status']='candidate-only; engineering precision policy pending review'
 ck(exact(expected,new),'Unapproved STD candidate delta')
 # Keep two independent result channels; no native value is overwritten.
 diagnostic=read(cp/'independent-reference-matrix-diagnostic.json');dv={(s['state'],q['id']):q['value'] for s in diagnostic['states'] for q in s['quantities']};strict=[];policy=[]
 for s in new['states']:
  for q in s['quantities']:
   ref=dv[(s['state'],q['id'])];delta=abs(q['value']-ref);limit=q['tolerance']['absolute']+q['tolerance']['relative']*abs(ref);extra=q.get('engineeringPrecision',{}).get('absoluteAllowance',0)
   if delta>limit:strict.append({'id':q['id'],'delta':delta,'strictLimit':limit,'engineeringAllowance':extra})
   if delta>limit+extra:policy.append(q['id'])
 ck(len(strict)==2 and policy==[],'Unexpected diagnostic result');sources.append(ev(cp/'independent-reference-matrix-diagnostic.json'))
 detail={'schemaVersion':1,'reviewer':REVIEWER,'case':cid,'summary':{'precisionRequests':120,'excludedNodeRequests':81,'allNativeValuesRawTracesAndFrozenTolerancesUnchanged':True,'independentRecoveryUsesNoProducerOrMatrixSolverImport':True,'independentTermEvaluation':'80-digit decimal closed-form coefficients and uniform-load end terms; observed binary64 implementation differences explicitly bounded only for verification of the formula, not used as scoring allowances.','maximumTermDifferenceInBinary64ULPs':max(rounding_ulp),'metadataScaleAndAllowanceRecomputedExactly':True,'strictDiagnosticFailures':strict,'policyAwareDiagnosticFailures':policy,'acceptanceRegionChanges':True,'nativeArithmeticBound':False,'oldQualificationPreserved':True},'fixedBoundaryForScaleProof':{'nativeTotalAndExitDOFs':dofs,'fixedNodes':fixed_proofs,'completeNativePrescribedBoundaryChainVerified':True,'notAnSDKDisplacement':True,'pinCounterexampleBound':True},'coveredQuantityIds':covered,'excludedQuantityIds':excluded,'quantities':details,'limitations':['This separately versioned engineering policy changes the acceptance region and is not a vendor arithmetic error bound.','Reconstructed canonical stiffness uses native material/section geometry and declared As=5A/6, not a native stiffness matrix readback.','The two original strict failures remain failures; none of the native values or authored tolerances changed.','Certification covers this exact case, evidence and 120-row canonical decomposition. Other states, output families and future code revisions require independent certification.']}
 sources += [ev(oldpath),ev(certpath),ev(receiptpath),ev(REPO/'scripts/research300/commercial/pkpm_precision.py')]
 return qualify(cid,newpath,detail,sources)

if __name__=='__main__':
 answers=pin_reviews();answers.append(std_review());print(json.dumps(answers,indent=2))
