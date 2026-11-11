"""Independent FE/DB/SDK and physical-wrench review of two inclined-column runs."""
import copy,hashlib,json,pathlib,re,struct,sys
import numpy as np
sys.path.insert(0,str(pathlib.Path('scripts/research300').resolve()))
from reference_solver import solve,axes,DISPLACEMENTS,ACTIONS
BASE=pathlib.Path('.bench-work/commercial-246/yjk-calibration-2');OUT=pathlib.Path('.bench-work/commercial-246/yjk-independent-review')
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def vals(s):return [float(v) for v in s.split(',')]
def parse(p):
 groups={};group='';case=None;last=None
 for line in p.read_text().splitlines():
  line=line.strip()
  if line.startswith('*USE-STLD'):case=int(re.search('LCID=(\\d+)',line)[1])
  if line.startswith('*'):group=line.split()[0];groups.setdefault(group,[]);last=None;continue
  if not line or line.startswith('//'):continue
  attrs=dict(re.findall(r'(\w+)=([^\s&]+)',line))
  if re.match(r'^\d+(?:\s|$)',line):last={'id':int(line.split()[0]),'attrs':attrs,'case':case};groups[group].append(last)
  elif last is not None:last['attrs'].update(attrs)
 return groups
def database(p):
 b=p.read_bytes();off=56;records={}
 while off+17<len(b):
  tag,a,c,flag,n=struct.unpack_from('<4siiBI',b,off);assert off+17+n<=len(b);assert (tag,a,c) not in records;records[tag,a,c]={'offset':off,'payload':b[off+17:off+17+n]};off+=17+n
  if tag==b'INDX':break
 return records
def maximum(rows,key='error'):return max((abs(x) for r in rows for x in r[key]),default=0)
def review(run,caseid,bind=None,binding_path=None):
 binding_path=binding_path or BASE/'special-bindings.json';bind=bind or next(x for x in read(binding_path) if x['case']==caseid);src=pathlib.Path(bind['source']);assert sha(src)==bind['source_sha256'];assert sha(BASE/bind['packet'])==bind['packet_sha256'];source=read(src);p=BASE/'downloaded'/run;g=parse(p/'fea.dat');sdk=read(p/'results.json');mapping=read(p/'mapping.json');dbpath=next(p.rglob('M0.RESULT.DB'));db=database(dbpath)
 frames={r['id']:r['attrs'] for r in g['*FRAME']};nativeNodes={r['id']:np.array(vals(r['attrs']['C'])) for r in g['*NODE']};physical={int(n) for f in frames.values() for n in f['N'].split(',')};constraints={r['id']:vals(r['attrs']['R']) for r in g['*CONSTRAINT']};sourceNodes={n['id']:np.array([n[x] for x in 'xyz']) for n in source['nodes']};els={e['id']:e for e in source['elements']};secs={r['id']:vals(r['attrs']['P']) for r in g['*SECTION']};mats={r['id']:vals(r['attrs']['P']) for r in g['*MATERIAL']};sourceSec={s['id']:s['properties'] for s in source['sections']};sourceMat={m['id']:m for m in source['materials']}
 # Coordinate-based node and collinear-segment map, independent of producer's audit.
 nmap={}
 for sid,xyz in sourceNodes.items():
  hits=[nid for nid in physical if np.allclose(nativeNodes[nid],xyz,rtol=0,atol=1e-10)];assert len(hits)==1;(nmap.update({sid:hits[0]}))
 for n in source['nodes']:assert [bool(x) for x in constraints.get(nmap[n['id']],[0]*6)]==n['restraints']
 segments={sid:[] for sid in els};owner={};sourceAxes={sid:axes(source,e,*[sourceNodes[n] for n in e['nodes']]) for sid,e in els.items()}
 for eid,f in frames.items():
  nn=list(map(int,f['N'].split(',')));xyz=[nativeNodes[n] for n in nn];hits=[]
  for sid,e in els.items():
   a,b=[sourceNodes[n] for n in e['nodes']];L=np.linalg.norm(b-a);ex=(b-a)/L;xx=[np.dot(v-a,ex) for v in xyz]
   if all(-1e-9<=x<=L+1e-9 for x in xx) and all(np.linalg.norm(v-(a+x*ex))<1e-9 for v,x in zip(xyz,xx)):hits.append((sid,xx))
  assert len(hits)==1,(eid,hits);sid,xx=hits[0];segments[sid].append({'native':eid,'nodes':nn,'positionsM':xx});owner[eid]=sid
 for sid,ss in segments.items():
  L=np.linalg.norm(sourceNodes[els[sid]['nodes'][1]]-sourceNodes[els[sid]['nodes'][0]]);intervals=sorted(sorted(s['positionsM']) for s in ss);assert intervals and abs(intervals[0][0])<1e-9 and abs(intervals[-1][1]-L)<1e-9;assert all(abs(a[1]-b[0])<1e-9 for a,b in zip(intervals,intervals[1:]));assert all(b-a>1e-9 for a,b in intervals)
 extra=[]
 for nid in physical-set(nmap.values()):
  incident=[eid for eid,f in frames.items() if nid in list(map(int,f['N'].split(',')))];assert len(incident)==2 and len({owner[e] for e in incident})==1;assert not any(constraints.get(nid,[0]*6));assert not any(r['id']==nid and any(vals(r['attrs']['F'])) for r in g.get('*NODELOAD',[]));extra.append({'nativeNode':nid,'coordinates':nativeNodes[nid].tolist(),'incidentFrames':incident,'sourceMember':owner[incident[0]],'freeUnloadedDegreeTwo':True})
 # AXSI's final integer is a zero-based AXD2 index; all native axes checked against FE geometry/DIR.
 idx=np.frombuffer(db[b'AXSI',0,0]['payload'],dtype='<i4');assert len(idx)==1+3*idx[0];axisindex={int(eid):int(k) for typ,eid,k in idx[1:].reshape(-1,3)};ax=np.frombuffer(db[b'AXD2',0,0]['payload'],dtype='<f8').reshape(-1,12);nativeAxes={};props=[]
 actual={'schema_version':'2.2.0','unit_system':'SI','coordinate_system':{'dimension':'3d'},'nodes':[],'elements':[],'sections':[],'materials':[],'load_cases':[],'load_combinations':[],'analysis_control':source['analysis_control'],'metadata':{'elementReferenceVectors':{}}};areas={}
 for nid in sorted(physical):actual['nodes'].append(dict(id=str(nid),**dict(zip('xyz',nativeNodes[nid])),restraints=[bool(x) for x in constraints.get(nid,[0]*6)]))
 for eid,f in frames.items():
  sid=owner[eid];nn=list(map(int,f['N'].split(',')));ex=nativeNodes[nn[1]]-nativeNodes[nn[0]];ex/=np.linalg.norm(ex);ey=np.array(vals(f['DIR']));ey-=ex*np.dot(ex,ey);ey/=np.linalg.norm(ey);rn=np.array([ex,ey,np.cross(ex,ey)]);R=ax[axisindex[eid],:9].reshape(3,3);assert np.allclose(R@R.T,np.eye(3),rtol=0,atol=1e-12);assert np.linalg.det(R)>0;assert np.max(abs(R-rn))<1e-7;assert np.all(ax[axisindex[eid],9:]==0);nativeAxes[eid]=R
  assert all(v==0 for key in ['E','R','RZL'] for v in vals(f.get(key,'0')));assert f['T'] in ['BEAM','COLUMN','BRACE'];pre=sdk['preprocessor'][str(eid)];assert pre['nodes']==nn
  if f['T']=='BRACE':assert pre['is_truss']==0
  P=secs[int(f['SEC'])];RF=vals(f['RF']);E,nu=mats[int(f['M'])][:2];G=E/(2*(1+nu));prop={'A':P[0]*RF[0],'Iy':P[2]*RF[2],'Iz':P[1]*RF[1],'J':P[3]*RF[3]};sh={'Asy':P[4]*RF[4],'Asz':P[5]*RF[5]};areas[str(eid)]=sh
  actual['sections'].append({'id':str(eid),'type':'general','properties':prop});actual['materials'].append({'id':str(eid),'type':'steel','E':E/1000,'G':G/1000,'nu':nu});actual['elements'].append({'id':str(eid),'type':'beam','nodes':list(map(str,nn)),'section':str(eid),'material':str(eid)});actual['metadata']['elementReferenceVectors'][str(eid)]=R[2].tolist()
  sm=sourceMat[els[sid]['material']];sp=sourceSec[els[sid]['section']];Q=sourceAxes[sid]@R.T;rot=Q[1:,1:];ei=rot@np.diag([E*prop['Iy'],E*prop['Iz']])@rot.T;ga=rot@np.diag([G*sh['Asy'],G*sh['Asz']])@rot.T;expected_ei=1000*sm['E']*np.diag([sp['Iy'],sp['Iz']]);expected_ga=1000*sm['G']*(5*sp['A']/6)*np.eye(2)
  props.append({'sourceMember':sid,'nativeFrame':eid,'nativeKind':f['T'],'AXD2IndexZeroBased':axisindex[eid],'axisRowsFromDB':R.tolist(),'axisRowsFromFE':rn.tolist(),'sourceProjection':Q.tolist(),'literalP':P,'literalMaterial':mats[int(f['M'])],'RF':RF,'actualEffectiveSection':prop,'actualEffectiveShearAreas':sh,'sourceToNativeStiffness':{'EARelativeDifference':E*prop['A']/(1000*sm['E']*sp['A'])-1,'GJRelativeDifference':G*prop['J']/(1000*sm['G']*sp['J'])-1,'sourceEItensor':expected_ei.tolist(),'nativeEItensorInSourceAxes':ei.tolist(),'sourceGAtensor':expected_ga.tolist(),'nativeGAtensorInSourceAxes':ga.tolist()}})
 # Bind every requested source load to all and only its native segments.
 for cm in mapping['load_cases']:
  cid=cm['source_case'];nc=cm['native_kind'];lc=next(c for c in source['load_cases'] if c['id']==cid);nloads=[];wantedf=[];wantedn=[]
  for l in lc['loads']:
   assert l.get('reference_frame')=='global'
   if l['type']=='distributed':
    assert set(l)<={'id','type','element','reference_frame','wz'}
    for seg in segments[l['element']]:wantedf.append((seg['native'],l['wz']))
   elif l['type']=='nodal':wantedn.append((nmap[l['node']],[l.get(k,0) for k in ['fx','fy','fz','mx','my','mz']]))
   else:raise AssertionError('unreviewed load type')
  nfr=[r for r in g.get('*FRAMELOAD',[]) if r['case']==nc];nnl=[r for r in g.get('*NODELOAD',[]) if r['case']==nc];assert len(nfr)==len(wantedf) and len(nnl)==len(wantedn)
  for eid,w in wantedf:
   matches=[r for r in nfr if r['id']==eid];assert len(matches)==1;ld=matches[0]['attrs'];assert ld['T']=='UNILOAD' and ld['DIR']=='GZ' and vals(ld['F'])==[0,w,-1,w];nloads.append({'id':'w'+str(eid),'type':'distributed','reference_frame':'global','element':str(eid),'wz':w})
  for nid,v in wantedn:
   matches=[r for r in nnl if r['id']==nid];assert len(matches)==1 and vals(matches[0]['attrs']['F'])==v;nloads.append(dict(id='p'+str(nid),type='nodal',reference_frame='global',node=str(nid),**dict(zip(['fx','fy','fz','mx','my','mz'],v))))
  actual['load_cases'].append({'id':cid,'type':'other','loads':nloads})
 checks=[];dbchecks=[]
 for sc in sdk['cases']:
  nc=sc['analysis_case'];matches=[]
  for eid,f in frames.items():
   rec=db[b'FFRC',eid,nc];bb=rec['payload'];rid,nsect,ncomp=struct.unpack_from('<3i',bb);assert rid==eid and ncomp==6 and len(bb)==12+4*nsect*ncomp;h=np.frombuffer(bb,dtype='<f4',offset=12).astype(float).reshape(nsect,ncomp);rr=sc['memberForces'][str(eid)];s=np.array(rr['forces'][:rr['section_count']]);assert len(s)==nsect
   predicted=h[:,[5,4,2,1,0,3]].copy()
   if f['T']=='BEAM':predicted[:,0]*=-1
   diff=s-predicted;matches.append({'nativeFrame':eid,'kind':f['T'],'sectionCount':nsect,'componentsExactlyEqual':int(np.count_nonzero(s==predicted)),'componentsCompared':int(s.size),'FFRCRecordOffset':rec['offset'],'maxAbsDifference':float(np.max(abs(diff))),'differences':[{'section':int(i),'SDKcomponent':int(j),'SDK':float(s[i,j]),'DBconverted':float(predicted[i,j])} for i,j in zip(*np.where(s!=predicted))]});assert np.max(abs(diff))<1e-10,'material SDK/DB disagreement'
  dbchecks.append({'analysisCase':nc,'members':matches,'allSDKValidRowsExactlyMatchDB':all(r['componentsExactlyEqual']==r['componentsCompared'] for r in matches),'maxAbsDifference':max(r['maxAbsDifference'] for r in matches)})
 for cm in mapping['load_cases']:
  cid,nc=cm['source_case'],cm['native_kind'];sc=next(c for c in sdk['cases'] if c['analysis_case']==nc);q,solverchecks=solve(actual,{cid:1},[],effective_shear_areas=areas);nodecmp=[];endcmp=[];acc={n:np.zeros(6) for n in physical};altacc={n:np.zeros(6) for n in physical}
  for nid in sorted(physical):
   obs=sc['nodes'][str(nid)]['displacement'];pred=[q({'kind':'node','id':str(nid)},k) for k in DISPLACEMENTS];nodecmp.append({'nativeNode':nid,'sourceNode':next((s for s,n in nmap.items() if n==nid),None),'observed':obs,'prediction':pred,'error':(np.array(obs)-pred).tolist()})
  sourceendpoint=[]
  for eid,f in frames.items():
   rr=sc['memberForces'][str(eid)];s=np.array(rr['forces'][:rr['section_count']]);h=s[:,[4,3,2,5,1,0]].copy()
   if f['T']=='BEAM':h[:,5]*=-1
   nn=list(map(int,f['N'].split(',')));R=nativeAxes[eid];L=np.linalg.norm(nativeNodes[nn[1]]-nativeNodes[nn[0]]);sid=owner[eid];Rs=sourceAxes[sid]
   for j,i in [(0,0),(1,-1)]:
    # Diagram -> physical resisting wrench, then vector rotation, then source cut sign.
    w=h[i]*np.array([-1,1,1,-1,1,1])*(1 if j==0 else -1);gw=np.r_[R.T@w[:3],R.T@w[3:]];acc[nn[j]]+=gw;aw=w.copy()
    if f['T']=='BRACE':aw[5]*=-1
    altacc[nn[j]]+=np.r_[R.T@aw[:3],R.T@aw[3:]]
    nativeactions=h[i]*np.array([1,1,1,1,-1,-1]);pred=np.array([q({'kind':'element','id':str(eid),'positionM':0. if j==0 else L,'side':'right' if j==0 else 'left'},k) for k in ACTIONS]);endcmp.append({'nativeFrame':eid,'sourceMember':sid,'kind':f['T'],'nativeEndpoint':j,'nativeACTIONS':nativeactions.tolist(),'prediction':pred.tolist(),'error':(nativeactions-pred).tolist(),'globalWrench':gw.tolist()})
    for se in [0,1]:
     if nn[j]==nmap[els[sid]['nodes'][se]]:
      sw=np.r_[Rs@gw[:3],Rs@gw[3:]];sa=sw*np.array([-1,1,1,-1,-1,-1])*(1 if se==0 else -1);pw=pred*np.array([-1,1,1,-1,-1,-1])*(1 if j==0 else -1);pg=np.r_[R.T@pw[:3],R.T@pw[3:]];ps=np.r_[Rs@pg[:3],Rs@pg[3:]]*np.array([-1,1,1,-1,-1,-1])*(1 if se==0 else -1);sourceendpoint.append({'sourceMember':sid,'sourceEndpoint':se,'nativeFrame':eid,'nativeEndpoint':j,'nativeKind':f['T'],'sourceACTIONS':sa.tolist(),'independentActualFE':ps.tolist(),'error':(sa-ps).tolist()})
  assert len(sourceendpoint)==2*len(els)
  point={n:np.zeros(6) for n in physical};external=np.zeros(6)
  for l in next(x for x in actual['load_cases'] if x['id']==cid)['loads']:
   if l['type']=='nodal':nid=int(l['node']);v=np.array([l.get(k,0) for k in ['fx','fy','fz','mx','my','mz']]);xyz=nativeNodes[nid];point[nid]+=v
   else:f=frames[int(l['element'])];a,b=[nativeNodes[int(n)] for n in f['N'].split(',')];v=np.array([0,0,l['wz']*np.linalg.norm(b-a),0,0,0]);xyz=(a+b)/2
   external+=np.r_[v[:3],v[3:]+np.cross(xyz,v[:3])]
  supports=np.zeros(6);joints=[];alt=[]
  for nid in sorted(physical):
   target=point[nid].copy();sr=sc['nodes'][str(nid)]['supportReaction']
   if sr is not None:sr=np.array(sr);target+=sr;supports+=np.r_[sr[:3],sr[3:]+np.cross(nativeNodes[nid],sr[:3])]
   joints.append({'nativeNode':nid,'assembled':acc[nid].tolist(),'target':target.tolist(),'error':(acc[nid]-target).tolist()});alt.append({'nativeNode':nid,'error':(altacc[nid]-target).tolist()})
  stat={'sourceCase':cid,'physicalNodeComponents':len(nodecmp)*6,'nodeMaxAbs':maximum(nodecmp),'nativeEndpointComponents':len(endcmp)*6,'endpointMaxAbs':maximum(endcmp),'sourceEndpointComponents':len(sourceendpoint)*6,'sourceEndpointMaxAbs':maximum(sourceendpoint),'jointWrenchMaxAbs':maximum(joints),'incorrectBraceFirstMomentSignJointMaxAbs':maximum(alt),'globalSDKSupportResidual':(external+supports).tolist()};checks.append({'summary':stat,'solverChecks':solverchecks,'nodes':nodecmp,'nativeEndpoints':endcmp,'sourceEndpoints':sourceendpoint,'jointWrenches':joints});print(run,stat)
 report={'kind':'Independent inclined-column native BRACE qualification within observed first-order 6DOF frame domain','benchmarkCasesQualified':0,'run':run,'case':caseid,'scope':'BEAM/COLUMN/BRACE SDK and FFRC valid rows crosschecked. BRACE IsBraceTruss=0, unreleased/zero offsets, actual AXD2 rows. No arbitrary internal station, other BRACE subtype, offset or nonlinear qualification. MM079 original col-special-01 remains historically input-gate rejected; this review binds only new col-special-01b and proves two benign degree-2 beam subdivisions.','sourceFiles':{str(f):sha(f) for f in [src,BASE/bind['packet'],binding_path,p/'fea.dat',p/'results.json',p/'mapping.json',dbpath,p/'中间数据/Yjkcombine_M0/M0.MPC.Data.txt',pathlib.Path(__file__),pathlib.Path('scripts/research300/reference_solver.py')]},'sourceNodes':nmap,'sourceSegments':segments,'extraConnectedNodes':extra,'nativePropertiesAndAxes':props,'sdkDatabaseCrosschecks':dbchecks,'diagramConvention':{'SDKColumnAndBrace':'[M3,M2,V3,V2,N,T] from FFRC [N,V2,V3,T,M2,M3]','SDKBeam':'[-M3,M2,V3,V2,N,T]','nativeFirstDiagramToWrench':[-1,1,1,-1,1,1],'nativeLast':'negative first','sourceFirstWrenchToACTIONS':[-1,1,1,-1,-1,-1],'sourceLast':'negative first','transform':'physical endpoint match; global wrench=blockdiag(Rn.T,Rn.T)*Dn*h; source ACTIONS=Ds*blockdiag(Rs,Rs)*global wrench'},'cases':checks,'actualNativeModel':actual,'explicitActualNativeShearAreas':areas};(OUT/(run+'-independent-review.json')).write_text(json.dumps(report,indent=2)+'\n');return {'run':run,'case':caseid,'cases':[c['summary'] for c in checks]}
if __name__=='__main__':
 results=[review('col-special-01b','MM-079'),review('col-special-02','MM-085')];(OUT/'special-brace-independent-summary.json').write_text(json.dumps(results,indent=2)+'\n')
