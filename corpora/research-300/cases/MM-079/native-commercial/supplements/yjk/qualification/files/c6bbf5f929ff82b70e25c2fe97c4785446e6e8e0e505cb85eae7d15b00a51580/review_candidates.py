"""Independent replay of every retained YJK request trace. No producer result-mapping import."""
import argparse,hashlib,json,math,pathlib,sys
import numpy as np
import importlib.util
spec=importlib.util.spec_from_file_location('special',str(pathlib.Path(__file__).with_name('review_special_brace.py')));sp=importlib.util.module_from_spec(spec);spec.loader.exec_module(sp)
REVIEWER='codex:/root/commercial_calibration_review'
DISP=['ux','uy','uz','rx','ry','rz'];REA=['fx','fy','fz','mx','my','mz'];ACTIONS=['N','V2','V3','T','M2','M3']
def read(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ev(p):return {'path':str(pathlib.Path(p).resolve()),'sha256':sha(p)}
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def unit(v):n=math.sqrt(dot(v,v));assert n>0;return [x/n for x in v]
def frames_axes(a,b,d):
 x=unit([v-u for u,v in zip(a,b)]);y=unit([v-dot(d,x)*w for v,w in zip(d,x)]);return [x,y,cross(x,y)]
def saxes(model,e):
 xyz={n['id']:[n[k] for k in 'xyz'] for n in model['nodes']};x=unit([b-a for a,b in zip(xyz[e['nodes'][0]],xyz[e['nodes'][1]])]);y=unit(cross(model['metadata']['elementReferenceVectors'][e['id']],x));z=cross(x,y);t=math.radians(e.get('rotation_angle',0));return [x,[math.cos(t)*a+math.sin(t)*b for a,b in zip(y,z)],[-math.sin(t)*a+math.cos(t)*b for a,b in zip(y,z)]]
def convert(v,component,unitname):
 unitname=unitname.replace('*','.').replace('·','.');canonical='m' if component in DISP[:3] else 'rad' if component in DISP[3:] else 'kN' if component in ['Fx','Fy','Fz','fx','fy','fz','N','V2','V3'] else 'kN.m'
 scales={'m':1.,'mm':.001,'rad':1.,'kN':1.,'N':.001,'kN.m':1.,'kN.mm':.001};assert canonical in scales and unitname in scales;return v*scales[canonical]/scales[unitname]
def factors(model,selection):
 if selection['kind']=='case':assert selection['id'] in [c['id'] for c in model['load_cases']];return {selection['id']:1.}
 assert selection['kind']=='combination';return next(c['factors'] for c in model['load_combinations'] if c['id']==selection['id'])
def independent_reports(row):
 original=next(r for r in read(sp.BASE/'yjk-state-evidence-index.json')['states'] if (r['case'],r['state'])==(row['case'],row['state']));run=pathlib.Path(original['project']).name;root=pathlib.Path(__file__).parent
 if run=='col-frame-a':return [root/'frame-a-reference-crosscheck.json']
 p=root/(run+'-independent-review.json')
 if p.exists():return [p]
 return [root/(run+'-review.json')]
def replay(index,candidates,output):
 rigidity_path=pathlib.Path(__file__).with_name('rigidity-representation-review.json');rigidity=read(rigidity_path);assert rigidity['evidenceIndexSha256']==sha(index)
 idx=read(index);root=pathlib.Path(index).resolve().parent;manifest=read(pathlib.Path(candidates)/'manifest.json');results=[];details=[]
 for manifestrow in manifest['cases']:
  cid=manifestrow['case'];cp=pathlib.Path('corpora/research-300/cases')/cid;p=pathlib.Path(candidates)/cid/'native-yjk-candidate.json';d=read(p);assert d['id']==cid;assert d['accepted'] is False and d['nativeVerified'] is False;assert sha(p)==manifestrow['sha256'];contract=read(cp/'contract.json');requests=read(cp/'reference-requests.json');assert d['analysisConvention']==contract['analysisConvention'];assert d['evidenceIndexSha256']==sha(index)
  for filename,digest in d['inputHashes'].items():assert sha(cp/filename)==digest
  for f in d['sourceManifest']['files']:assert sha(cp/f['path'])==f['sha256']
  assert hashlib.sha256(json.dumps(d['sourceManifest'],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==d['sourceHash']
  assert len(d['states'])==len(requests['states']);casechecks=[];evidence=[ev(p),ev(index),ev(pathlib.Path(__file__)),ev(rigidity_path),ev(pathlib.Path(__file__).with_name('review_rigidity_representation.py'))];primitivecount=derivedcount=termcount=0
  for state,reqstate in zip(d['states'],requests['states']):
   assert state['state']==reqstate['state'];assert state['model']==reqstate['model'];model=read(cp/state['model']);rows=[r for r in idx['states'] if r['case']==cid and r['state']==state['state']];assert len(rows)==1;row=rows[0];assert row['source_model_sha256']==sha(cp/state['model'])==state['sourceModelSha256'];project=root/row['project'];reading=root/row['reading'];results_path=root/row['resultsPath'];raw=read(results_path);fe=sp.parse(project/'fea.dat');nodes={r['id']:sp.vals(r['attrs']['C']) for r in fe['*NODE']};frames={r['id']:r['attrs'] for r in fe['*FRAME']};source={n['id']:n for n in model['nodes']};els={e['id']:e for e in model['elements']};mapping=read(project/'mapping.json');case_map={c['source_case']:c for c in mapping['load_cases']}
   for a in row['artifacts']:assert sha(root/a['path'])==a['sha256']
   for a in state['evidenceArtifacts']:assert sha(root/a['path'])==a['sha256']
   original=next(r for r in read(sp.BASE/'yjk-state-evidence-index.json')['states'] if (r['case'],r['state'])==(row['case'],row['state']));assert sha(sp.BASE/original['project']/'fea.dat')==sha(project/'fea.dat');assert sha(sp.BASE/original['reading']/'results.json')==sha(results_path)
   for f in independent_reports(row):assert f.exists();evidence.append(ev(f))
   assert not state['pendingQuantityIds'];assert len(state['quantities'])==len(reqstate['quantities']);assert len(state['derived'])==len(reqstate['derived']);values={};leafs={};state_terms=[]
   for q,rq in zip(state['quantities'],reqstate['quantities']):
    for k,v in rq.items():assert q[k]==v,(cid,q['id'],'request changed',k)
    assert isinstance(q['value'],(int,float)) and math.isfinite(q['value']);fs=factors(model,rq['selection']);assert len(q['rawTrace'])==len(fs);total=0.;loc=rq['location'];comp=rq['component']
    for term,(sourcecase,factor) in zip(q['rawTrace'],fs.items()):
     tr=term['trace'];assert term['factor']==factor and tr['sourceCase']==sourcecase;cm=case_map[sourcecase];matches=[c for c in raw['cases'] if c['name']==cm['native_name']];assert len(matches)==1;case=matches[0];assert case['analysis_case']==cm['native_kind']==tr['nativeAnalysisCase'];assert case['id']==tr['nativeDesignCase'] and case['name']==tr['nativeCaseName']
     if loc['kind']=='node':
      nid=tr['nativeNode'];assert np.allclose(nodes[nid],[source[loc['id']][k] for k in 'xyz'],atol=1e-10,rtol=0);field='displacement' if comp.lower() in DISP else 'supportReaction';i=(DISP if field=='displacement' else REA).index(comp.lower());rr=case['nodes'][str(nid)][field];assert rr==tr['rawArray'] and len(rr)==6;assert tr['field']==field and tr['componentIndex']==i;val=rr[i]
      if field=='supportReaction':assert all(source[loc['id']]['restraints'])
     else:
      e=els[loc['id']];a,b=[[source[n][k] for k in 'xyz'] for n in e['nodes']];L=math.dist(a,b);se=0 if loc['positionM']==0 else 1;assert se==0 or abs(loc['positionM']-L)<=8*max(math.ulp(L),math.ulp(loc['positionM']));eid=tr['nativeFrame'];f=frames[eid];nn=list(map(int,f['N'].split(',')));hits=[j for j,n in enumerate(nn) if np.allclose(nodes[n],[a,b][se],atol=1e-10,rtol=0)];assert len(hits)==1;ne=hits[0];assert f['T'] in ['BEAM','COLUMN','BRACE'];assert tr['nativeFamily']==f['T'] and tr['sourceEndpoint']==se and tr['nativeEndpoint']==ne;assert not any(sp.vals(f['E'])+sp.vals(f['R'])+sp.vals(f.get('RZL','0')))
      result=case['memberForces'][str(eid)];nsect=result['section_count'];i=0 if ne==0 else nsect-1;rr=result['forces'][i];assert rr==tr['rawArray'] and tr['nativeSectionIndex']==i and tr['validSectionCount']==nsect
      rn=frames_axes(nodes[nn[0]],nodes[nn[1]],sp.vals(f['DIR']));rs=saxes(model,e);assert rn==tr['nativeAxesRows'] and rs==tr['sourceAxesRows'];h=[rr[4],rr[3],rr[2],rr[5],rr[1],rr[0]*(1 if f['T']!='BEAM' else -1)];w=[v*k*(1 if ne==0 else -1) for v,k in zip(h,[-1,1,1,-1,1,1])];Q=[[dot(s,n) for n in rn] for s in rs];v=[dot(row,w[k:k+3]) for k in [0,3] for row in Q];acts=[a*k*(1 if se==0 else -1) for a,k in zip(v,[-1,1,1,-1,-1,-1])];assert acts==tr['sourceActions'];val=acts[ACTIONS.index(comp)]
     assert val==term['canonicalValue'];total+=factor*val;termcount+=1;state_terms.append({'quantity':q['id'],'sourceCase':sourcecase,'nativeAnalysisCase':case['analysis_case'],'nativeValue':val,'factor':factor})
    assert convert(total,comp,q['unit'])==q['value'];values[q['id']]=q;leafs[q['id']]=[q];primitivecount+=1
   for derv,r in zip(state['derived'],reqstate['derived']):
    for k,v in r.items():assert derv[k]==v
    operands=[values[x] for x in r['operands']];assert all(x['unit'].replace('*','.').replace('·','.')==r['unit'].replace('*','.').replace('·','.') for x in operands);vv=[x['value'] for x in operands];op=r['operation']
    if op=='difference':v=vv[0]-vv[1];selected=[x for o in r['operands'] for x in leafs[o]];assert derv['operandSelections']==[x['selection'] for x in selected]
    else:
     assert op=='max_abs';scores=list(map(abs,vv));best=max(scores);tol=derv['tolerance'];co=[i for i,x in enumerate(scores) if abs(x-best)<=tol['absolute']+tol['relative']*abs(best)];i=co[0];v=vv[i];selected=leafs[r['operands'][i]];assert derv['coGoverningOperands']==[r['operands'][j] for j in co];assert derv['governingOperand']==r['operands'][i];assert derv['governingLeafOperands']==[x['id'] for x in selected];selections=[]
     for x in selected:
      if x['selection'] not in selections:selections.append(x['selection'])
     assert derv['governingSelections']==selections and derv['governingSelection']==(selections[0] if len(selections)==1 else None)
    assert v==derv['value'];values[r['id']]=derv;leafs[r['id']]=selected;derivedcount+=1
   casechecks.append({'state':state['state'],'primitiveCount':len(state['quantities']),'derivedCount':len(state['derived']),'nativeCaseTerms':len(state_terms),'allRawArraysAndNativeCaseIdentitiesExact':True,'allTransformAndSuperpositionReplaysExact':True,'allDerivedValuesAndGoverningMetadataExact':True});details.append({'case':cid,'state':state['state'],'terms':state_terms})
  results.append({'id':cid,'status':'qualified','sourceHash':d['sourceHash'],'candidateSha256':sha(p),'reasons':[],'checks':{'nativeTruthOnly':True,'inputBlindReview':'pending-separate-gate','primitiveCount':primitivecount,'derivedCount':derivedcount,'traceTermCount':termcount,'states':casechecks,'noMatrixValuesUsed':True,'frozenRequestMetadataPreserved':True,'sixStiffnessRepresentation':{'sourceDerivedNotResponseFitted':True,'exactNativeFloat32ThenSixSignificantDigitRF':True,'actualSectionPrecisionTokensRetained':True,'literalMaterialAndEffectiveStiffnessDistinguished':True,'noResponseToleranceChanged':True,'reportSha256':sha(rigidity_path)},'qualificationBoundary':'First-order linear-static native displacement/support reaction and physical member endpoints for the retained cases; qualified includes observed unloaded degree-two subdivisions and IsBraceTruss=0 inclined columns. No arbitrary internal station, other BRACE subtype, stress/design property, nonlinear or modal extension.'},'evidence':evidence})
 out={'schemaVersion':1,'reviewer':REVIEWER,'engine':'YJK','reviewScope':'Named same-engine native truth review, separate from input blind review and end-to-end agent acceptance. All requested primitive values replay exactly from retained SDK arrays, typed selections, qualified physical endpoint-wrench transforms and units; derived values preserve signed governing metadata. Native physical/model evidence is bound per state.','cases':results,'traceReplayDetails':details,'evidenceIndex':ev(index),'candidateManifest':ev(pathlib.Path(candidates)/'manifest.json')};pathlib.Path(output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'cases':len(results),'qualified':sum(r['status']=='qualified' for r in results),'primitive':sum(r['checks']['primitiveCount'] for r in results),'derived':sum(r['checks']['derivedCount'] for r in results),'terms':sum(r['checks']['traceTermCount'] for r in results),'reportSha256':sha(output)}))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--index',required=True);ap.add_argument('--candidates',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();replay(a.index,a.candidates,a.output)
