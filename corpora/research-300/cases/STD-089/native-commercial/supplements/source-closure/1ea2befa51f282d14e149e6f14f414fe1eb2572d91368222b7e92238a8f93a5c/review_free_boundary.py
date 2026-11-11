"""Independent qualification of executed native free-boundary consequences.

Reads original source/native/candidate evidence only; writes one new report. No
producer result mapping or solver is imported, and no small-value threshold is used.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BASE = REPO / '.bench-work/commercial-246'
REVIEWER = 'codex:/root/commercial_calibration_review'
EXPECTED = {('INT-079', 1, 'case-D--n0-0-0--My'),
            ('INT-089', 1, 'case-D--n0-0-0--My'),
            ('INT-089', 2, 'case-D--n0-0-0--My')}


def check(ok, reason):
    if not ok:
        raise ValueError(reason)


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def source(p):
    p = Path(p).resolve()
    return {'path': str(p.relative_to(REPO)), 'sha256': sha(p)}


def resolve(p):
    return Path(p) if Path(p).is_absolute() else REPO / p


def finite_floats(p, require_finite=True):
    data = Path(p).read_bytes()
    check(len(data) % 4 == 0, 'Incomplete float32 record')
    vals = struct.unpack('<%df' % (len(data)//4), data)
    check(not require_finite or all(math.isfinite(x) for x in vals), 'Nonfinite native record')
    return vals


def execute(output):
    candidate_root = BASE / 'pkpm-request-export/final03'
    manifest_path = BASE / 'pkpm-candidate-evidence-manifest.json'
    manifest = read(manifest_path)
    old_review_path = BASE / 'pkpm-independent-review/native-truth-qualification.json'
    old_review = read(old_review_path)
    candidate_manifest_path = candidate_root / 'manifest.json'
    candidate_manifest = read(candidate_manifest_path)
    rows, selected = [], set()
    for cm in candidate_manifest['results']:
        cid = cm['caseId']
        cp = REPO / 'corpora/research-300/cases' / cid
        cand_path = candidate_root / cid / 'native-reference.json'
        cand = read(cand_path)
        check(sha(cand_path) == cm['artifactSha256'], 'Old candidate SHA changed')
        old_case, = [c for c in old_review['cases'] if c['id'] == cid]
        check(old_case['status'] == 'qualified' and old_case['candidateSha256'] == sha(cand_path), 'Old candidate lacks named qualification')
        requests_path = cp / 'reference-requests.json'
        request_doc = read(requests_path)
        for state in cand['states']:
            model_path = cp / state['model']
            model = read(model_path)
            nodes = {n['id']: n for n in model['nodes']}
            qs = [q for q in state['quantities'] if q['location']['kind'] == 'node'
                  and q['component'] in ['Mx', 'My', 'Mz']
                  and any(nodes[q['location']['id']]['restraints'])
                  and not nodes[q['location']['id']]['restraints'][['Mx', 'My', 'Mz'].index(q['component'])+3]]
            for q in qs:
                key = (cid, state['state'], q['id']); selected.add(key)
                check(key in EXPECTED, 'Unreviewed free-boundary request/domain')
                entry, = [r for r in manifest['runs'] if r['caseId'] == cid and r['state'] == state['state']]
                run = BASE / entry['runRoot'] / 'remote-evidence' / entry['nativeIdentity']
                report_path = BASE / 'pkpm-independent-review/pin-batch03' / (entry['nativeIdentity']+'.json')
                report = read(report_path)
                sources = [source(p) for p in [__file__, manifest_path, candidate_manifest_path, old_review_path, cand_path, model_path, requests_path, cp/'contract.json', report_path]]
                for p, digest in report['sources'].items():
                    check(sha(resolve(p)) == digest, 'Prior physical-review source changed: '+p)
                    sources.append(source(resolve(p)))
                for record in entry['artifacts'].values():
                    check(sha(BASE/record['path']) == record['sha256'], 'Frozen native artifact changed')
                    sources.append(source(BASE/record['path']))
                for record in entry['stages']:
                    check(sha(BASE/record['path']) == record['sha256'], 'Native receipt changed')
                    receipt = read(BASE/record['path'])
                    check(receipt['status'] == 'completed' and receipt['returncode'] == 0, 'Unsuccessful native stage')
                    sources.append(source(BASE/record['path']))
                check(cand['sourceHash'] == entry['sourceHash'] == old_case['sourceHash'], 'Source identity differs')
                check(sha(model_path) == entry['sourceModelSha256'] == state['originalModelSha256'], 'Model identity differs')
                check(cand['inputHashes']['reference-requests.json'] == sha(requests_path), 'Request identity differs')
                for f in cand['sourceManifest']['files']:
                    check(sha(cp/f['path']) == f['sha256'], 'Source manifest differs')
                source_hash = hashlib.sha256(json.dumps(cand['sourceManifest'],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
                check(source_hash == cand['sourceHash'], 'Source manifest digest differs')
                rq, = [x for rs in request_doc['states'] if rs['state'] == state['state'] for x in rs['quantities'] if x['id'] == q['id']]
                check(all(q[k] == v for k,v in rq.items()), 'Frozen request changed')
                nid = q['location']['id']; node = nodes[nid]
                check(q['selection'] == {'kind':'case','id':'D'} and q['component'] == 'My' and q['unit'] == 'kN.m', 'Unqualified selection/component/unit')
                check(node['restraints'] == [True]*3+[False]*3, 'Not the reviewed three-rotation free boundary')
                check(set(model) <= {'schema_version','unit_system','coordinate_system','nodes','elements','materials','sections','load_cases','load_combinations','analysis_control','metadata','stories'}, 'Additional source mechanism')
                check(set(model['metadata']) == {'elementReferenceVectors'}, 'Additional source metadata mechanism')
                check(all(set(n) <= {'id','x','y','z','restraints'} for n in model['nodes']), 'Additional nodal mechanism')
                check(all(set(e) <= {'id','type','nodes','material','section','rotation_angle'} for e in model['elements']), 'Additional member constraint or eccentricity')
                packet = read(run/'physical-input.json')
                check(packet['analysisControl'] == {'construction_stage':False,'p_delta':False,'rigid_floor':False,'rigid_offsets':False,'self_weight':False}, 'Additional native analysis mechanism')
                check(packet['selection'] == {'kind':'case','id':'D','factors':{'D':1.0}}, 'Native selection differs')
                check(not [l for c in model['load_cases'] if c['id'] == 'D' for l in c['loads'] if l['type'] == 'nodal' and l['node'] == nid], 'Support nodal load outside this qualified domain')
                check(not [l for l in packet['loads'] if l['type'] == 'nodal' and l['target'] == nid], 'Native packet support nodal load')
                check(report['nativePostsolveMaterialsSegmentsLoadsConsistent'] is True, 'Postsolve model/load audit missing')
                audit = read(run/'native-output-audit.json')
                check(all(int(v) == 0 for v in audit['zeroSlabCounts']), 'Native slab present')
                settings = '\n'.join(audit['settingsLines'])
                check('是否对全楼强制采用刚性楼板假定:       否' in settings, 'Native diaphragm setting not excluded')
                check(settings.count('不作为刚域') == 2, 'Native member rigid offsets not excluded')
                compile_doc = read(run/'native-pin-compilation.json')
                check({r['path'] for r in compile_doc} == {'ConstraintNode.SAT','ConstraintNodeSK.SAT'}, 'Missing executed constraint artifact')
                blocks = []
                for rec in compile_doc:
                    name = rec['path']; raw = (run/name).read_bytes(); original = (run/(name+'.before-pin')).read_bytes(); compiled = (run/(name+'.compiled-pin')).read_bytes()
                    check(raw == compiled and sha(run/(name+'.compiled-pin')) == rec['compiledSha256'], 'Postsolve constraint changed')
                    check(sha(run/(name+'.before-pin')) == rec['beforeSha256'] and len(raw) == len(original) == rec['bytes'], 'Original/compiled constraint binding')
                    count = len(rec['compiledValues']); off = rec['allowedByteOffset']
                    vals = list(struct.unpack_from('<%dd'%count, raw, off))
                    expected = [1e14]*3+[0.0]*3 if name == 'ConstraintNode.SAT' else [1e14,0.0,1e14,0.0,0.0,1e14]+[0.0]*6
                    check(vals == rec['compiledValues'] == expected, 'Nonzero or coupled support rotational stiffness')
                    changed = {i for i,(a,b) in enumerate(zip(original,raw)) if a!=b}
                    check(changed <= set(range(off,off+count*8)), 'Undeclared constraint bytes changed')
                    binding, = [s for s in rec['sourceBindings'] if s['sourceNodeId'] == nid]
                    check(binding['kind'] == 1 and binding['stiffness'][3:] == [0.0]*3 and binding['guardBytesIntact'], 'Native SDK constraint subtype/binding differs')
                    check(binding in read(run/'native-constraint-readback.json'), 'SDK binding absent')
                    blocks.append({'artifact':name,'offsetBytes':off,'executedValues':vals,'postsolveEqualsCompiled':True,'definitionId':binding['definitionId'],'sourceMemberId':binding['sourceMemberId']})
                    sources += [source(run/name),source(run/(name+'.before-pin')),source(run/(name+'.compiled-pin'))]
                check(blocks[0]['definitionId'] == blocks[1]['definitionId'], 'Support definitions differ')
                sources += [source(run/'native-pin-compilation.json'),source(run/'native-constraint-readback.json'),source(run/'native-pin-postsolve.json')]
                mesh = finite_floats(run/'MESH.SAT', require_finite=False); mesh_records=[mesh[i:i+5] for i in range(5,len(mesh),5)]
                check((len(mesh)-5)%5 == 0 and all(math.isfinite(v) for r in mesh_records for v in r[:3]), 'Invalid native mesh coordinates')
                cnraw=(run/'ConstraintNodeNo.SAT').read_bytes(); cn=struct.unpack('<%di'%(len(cnraw)//4),cnraw)
                check(list(cn[:4]) == [3,20200113,len(mesh_records),4], 'Constraint node index format')
                check(all(v in [0,1] for v in cn[4:]), 'Additional native support definition')
                mapping, = [v for v in report['rawIndexMapping'] if v['sourceNode'] == nid]
                check(mapping['specialBase'] and cn[4:][mapping['meshIndex']-1] == 1, 'Requested pin lacks executed node binding')
                xyz=mesh_records[mapping['meshIndex']-1][:3]
                check(all(abs(v-node[k]) <= 1e-6 for v,k in zip(xyz,'xyz')), 'Native node coordinate mismatch')
                pin_count=sum(v!=0 for v in cn[4:]); nfree=len(report['rawIndexMapping'])
                check(pin_count == report['summary']['pinCount'], 'Additional support count')
                check(nfree == sum(not any(n['restraints']) for n in model['nodes'])+pin_count, 'Retained free-node set differs')
                wm=(run/'WMASS.OUT').read_bytes().decode('gb18030')
                dofs=[int(l.split(':')[-1]) for l in wm.splitlines() if '自由度为' in l]
                check(dofs == [nfree*6]*2, 'Retained DOF/exit DOF inconsistent; possible additional constraint')
                displacement=finite_floats(run/'DISP.SAT');check(len(displacement)==2*nfree*6,'Incomplete six-DOF result')
                i=mapping['DISPRecord']*6; raw6=[displacement[i+j] for j in [0,1,5,3,4,2]]
                old_pin, = [v for v in report['pinChecks'] if v['node']==nid]
                check(raw6==old_pin['rawSixDOF'] and raw6[4]!=0,'Free rotation not evidenced')
                trace=q['rawTrace']; check(trace['origin']=='raw-member-end-equilibrium','Original trace origin differs')
                check(trace['externalNodalLoadAtSupport']==[0]*6 and trace['externalNodalLoadSources']==[],'Unaccounted support load')
                contribution,=trace['contributions'];check(contribution['member']=='c0-0-1' and contribution['end']==0,'Unreviewed native/source endpoint')
                raw_trace,=contribution['raw'];check(raw_trace['jsonPointer']=='/members/0/forces/DL/0' and raw_trace['factor']==1.0,'Unreviewed native case')
                sdk=read(run/'sdk-results.json');check(sdk['members'][0]['sourceId']=='c0-0-1','SDK member differs')
                slots=sdk['members'][0]['forces']['DL']['0'];check(slots==raw_trace['rawSixSlots'],'Raw values differ')
                check(q['value']==-slots[5]==old_pin['reconstructedSupportWrench'][4],'Prior raw residual differs')
                facts={'zeroRotationStiffness':True,'noCoupling':True,'noAdditionalConstraint':True,'freeDofsRetained':True,'noSupportNodalLoad':True}
                unique={s['path']:s for s in sources}
                rows.append({'caseId':cid,'state':state['state'],'model':state['model'],'quantityId':q['id'],'node':nid,'component':q['component'],'selection':q['selection'],'unit':q['unit'],'derivedValue':0.0,'sourceHash':cand['sourceHash'],'modelSha256':sha(model_path),'requestSha256':sha(requests_path),'nativeRun':entry['nativeIdentity'],'oldCandidateSha256':sha(cand_path),'oldValue':q['value'],'oldRawTrace':trace,'facts':facts,**facts,'proof':{'executedConstraintBlocks':blocks,'nativeMeshIndex':mapping['meshIndex'],'nativeDISPRecord':mapping['DISPRecord'],'nativeTotalAndExitDOFs':dofs,'retainedSixDofNodes':nfree,'rawSixDOF':raw6,'nativeMemberEndResidual':q['value'],'externalNodalLoadAtSupport':[0.0]*6,'relation':'The support rotational operator and additional kinematic constraint action are zero at this retained free DOF; therefore the support moment is exactly zero. The member-end equilibrium residual is preserved separately.'},'sources':list(unique.values())})
    check(selected == EXPECTED and len(rows)==3,'The complete requested free-boundary set changed')
    # Guard against a source changing during the review, before publishing the report.
    for row in rows:
        for s in row['sources']:
            check(sha(REPO/s['path'])==s['sha256'],'Evidence changed during review')
    grouped=[]
    for cid in sorted({r['caseId'] for r in rows}):
        case_rows=[r for r in rows if r['caseId']==cid]
        grouped.append({'id':cid,'sourceHash':case_rows[0]['sourceHash'],'candidate':source(candidate_root/cid/'native-reference.json'),'qualification':source(old_review_path),'quantities':[{'state':r['state'],'quantityId':r['quantityId']} for r in case_rows]})
    out={'schemaVersion':1,'ruleVersion':'pkpm-free-rotation-reaction-v1','cases':grouped,'reviewer':REVIEWER,'engine':'PKPM','status':'qualified-boundary-derivation','valueKind':'derived-from-native-free-boundary','scope':'Exactly the three enumerated global My support requests, PKPM 2027R1.0.1, existing independently reviewed orthogonal frame/pin runs. This report adds a boundary-derived value qualification; old candidates and original raw observations are unchanged.','quantities':rows,'allPKPMRequestedFreeRotationMomentsCovered':True,'selectionRule':'Enumerate node support-moment requests whose source rotational DOF is free, then require the complete executed native zero-rotation and retained-DOF proof. Never select by magnitude or diagnostic failure.','noCouplingMeaning':'No support translation-to-rotation or rotation-to-rotation coupling, eccentric constraint, diaphragm or MPC action in this bounded executed-model domain. Ordinary structural member stiffness coupling is allowed and is not asserted to vanish.','proofBoundary':'No standalone undocumented SAT field is used as universal proof: API definition/binding, compiled-and-postsolve exact blocks, node indexing, retained full DOFs, complete model/load audit and previous independent six-DOF/force review are jointly required.','failClosed':['Unknown case/state/request/native version or changed SHA.','Any nonzero rotational stiffness, changed off-diagonal block, unbound support definition or unsupported constraint subtype.','MPC, rigid link, eccentric support, native/source origin mismatch, diaphragm or unreviewed additional mechanism.','Unavailable or inconsistent node mapping, DOF count, native result, source selection or external load.','Any support nodal load in this initial qualified domain; broader load handling requires separate review.','Member endpoint moment requests, finite translation spring displacements, or arbitrary small numerical values.'],'preservationPolicy':{'oldCandidateAndQualificationUnchanged':True,'oldRawTraceAndResidualMustBeRetained':True,'frozenRequestsAndTolerancesUnchanged':True,'derivedValueIsNotSDKReadback':True,'newCandidateRequiresNewNamedNativeQualification':True,'inputBlindReviewAndAcceptanceUnchanged':True},'sources':[source(__file__),source(manifest_path),source(candidate_manifest_path),source(old_review_path)]}
    output=Path(output)
    check(not output.exists(),'Refuse to overwrite existing boundary qualification')
    output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'report':str(output.relative_to(REPO)),'sha256':sha(output),'quantities':len(rows),'oldValues':[r['oldValue'] for r in rows]}))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=BASE/'precision-repair/free-boundary-review.json')
    args=parser.parse_args()
    execute(args.output.resolve())
