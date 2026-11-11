"""Independent final PKPM trace replay; imports no candidate/result producer or solver."""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path

REVIEWER = 'codex:/root/commercial_calibration_review'
ROOT = Path('.bench-work/commercial-246').resolve()
OWN = Path(__file__).resolve().parent
ACTIONS = ['N', 'V2', 'V3', 'T', 'M2', 'M3']
REACTIONS = ['Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz']
SOLVER = '333b010d067f820c453972833e18bc9db2328059cbba83e456effd0dc79d9a4d'


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ev(path):
    return {'path': str(Path(path).resolve()), 'sha256': sha(path)}


def pointer(document, path):
    value = document
    for key in path.strip('/').split('/'):
        key = key.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def unit(v):
    n = math.sqrt(dot(v, v))
    assert n > 0
    return [x/n for x in v]


def source_axes(model, e):
    xyz = {n['id']: [n[k] for k in 'xyz'] for n in model['nodes']}
    a, b = [xyz[n] for n in e['nodes']]
    x = unit([v-u for u, v in zip(a, b)])
    y = unit(cross(model['metadata']['elementReferenceVectors'][e['id']], x))
    z = cross(x, y)
    assert e.get('rotation_angle', 0) == 0
    if e['type'] == 'column':
        assert x == [0, 0, 1]
    else:
        assert e['type'] == 'beam' and x in ([1, 0, 0], [0, 1, 0])
    return [x, y, z]


def actions(kind, slots):
    assert len(slots) == 6 and all(math.isfinite(v) and v != -99999 for v in slots)
    # Separately reviewed source diagrams: index/sign permutation, NOT global vectors.
    indices, signs = (([0, 1, 2, 3, 4, 5], [1, -1, -1, 1, 1, 1])
                      if kind == 'beam' else ([0, 2, 1, 3, 5, 4], [1, 1, -1, 1, -1, 1]))
    assert kind in ['beam', 'column']
    return [slots[i]*sign for i, sign in zip(indices, signs)]


def wrench(kind, basis, end, slots):
    cut = actions(kind, slots)
    physical = [v*s*(1 if end == 0 else -1) for v, s in zip(cut, [-1, 1, 1, -1, -1, -1])]
    # Basis rows are local axes in global coordinates; rotate physical force/moment.
    return [sum(basis[j][i]*physical[off+j] for j in range(3)) for off in (0, 3) for i in range(3)]


def factors(model, packet, selection):
    if selection['kind'] == 'case':
        assert selection['id'] in [c['id'] for c in model['load_cases']]
        source = {selection['id']: 1.0}
    else:
        assert selection['kind'] == 'combination'
        source = next(c['factors'] for c in model['load_combinations'] if c['id'] == selection['id'])
    p = packet['selection']
    if p['kind'] == 'basic-cases':
        native = {p['nativeCases'][k]['name']: v for k, v in source.items()}
        assert {k: (v['id'], v['name']) for k, v in p['nativeCases'].items()} == {'D': (1, 'DL'), 'L': (2, 'LL')}
    else:
        assert selection == {'kind': p['kind'], 'id': p['id']} and source == p['factors']
        native = {'DL': 1.0}
    return source, native


def raw_member(sdk, sid, end, native, retained):
    hits = [(i, m) for i, m in enumerate(sdk['members']) if m['sourceId'] == sid]
    assert len(hits) == 1
    i, m = hits[0]
    last = 8 if m['kind'] == 'beam' else 1
    station = str(0 if end == 0 else last)
    assert len(retained) == len(native)
    total = [0.0]*6
    for tr, (name, factor) in zip(retained, native.items()):
        path = f'/members/{i}/forces/{name}/{station}'
        assert tr == {'artifact': 'sdk-results.json', 'jsonPointer': path, 'nativeCase': name, 'factor': factor, 'rawSixSlots': m['forces'][name][station]}
        assert sorted(map(int, m['forces'][name])) == list(range(last+1))
        values = pointer(sdk, path)
        assert len(values) == 6 and all(math.isfinite(v) and v != -99999 for v in values)
        total = [v+factor*w for v, w in zip(total, values)]
    return total


def physical_report(entry):
    group = entry['runRoot']
    if group == 'pkpm-batch01':
        return OWN/'batch01'/f"{entry['nativeIdentity']}.json", OWN/'review_batch01.py'
    if group == 'pkpm-pin-batch03':
        return OWN/'pin-batch03'/f"{entry['nativeIdentity']}.json", OWN/'review_pin_batch03.py'
    assert group == 'pkpm-extra01' and entry['caseId'] == 'STD-091'
    return OWN/'extra01/std091-basic-direct-review.json', OWN/'review_extra01.py'


def main(candidate_dir, output):
    assert __debug__, 'Run this review without Python -O; every guard must execute.'
    candidate_dir = Path(candidate_dir)
    mp = ROOT/'pkpm-candidate-evidence-manifest.json'
    manifest = read(mp)
    candidates_manifest = read(candidate_dir/'manifest.json')
    boundary_path = ROOT/manifest['boundaryReview']['path']
    assert sha(boundary_path) == manifest['boundaryReview']['sha256']
    boundary = read(boundary_path)
    counts = collections.Counter()
    reviewed = []
    all_details = []
    for mr in candidates_manifest['results']:
        cid = mr['caseId']
        candidate_path = candidate_dir/cid/'native-reference.json'
        candidate = read(candidate_path)
        assert sha(candidate_path) == mr['artifactSha256']
        cp = Path('corpora/research-300/cases')/cid
        contract, req = read(cp/'contract.json'), read(cp/'reference-requests.json')
        assert candidate['id'] == cid and candidate['accepted'] is False and candidate['nativeVerified'] is False
        assert candidate['analysisConvention'] == contract['analysisConvention']
        assert candidate['frozenEvidenceManifestSha256'] == sha(mp)
        for f, digest in candidate['inputHashes'].items():
            assert sha(cp/f) == digest
        for f in candidate['sourceManifest']['files']:
            assert sha(cp/f['path']) == f['sha256']
        assert hashlib.sha256(json.dumps(candidate['sourceManifest'], ensure_ascii=False, separators=(',', ':')).encode()).hexdigest() == candidate['sourceHash'] == mr['sourceHash']
        assert candidate['solver']['solverSha256'] == SOLVER
        assert candidate['solver']['exporterSha256'] == sha('scripts/research300/commercial/pkpm_candidates.py')
        assert candidate['solver']['slotMappingSha256'] == sha('scripts/research300/commercial/pkpm_results.py')
        assert candidate['solver']['referenceIoSha256'] == sha('scripts/research300/reference_io.py')
        evidence = [ev(candidate_path), ev(mp), ev(__file__), ev(OWN/'custom6b-l2-review.json'), ev(OWN/'numeric6-l2-review.json'), ev(OWN/'c30-l2-l4-review.json')]
        statechecks = []
        origins = collections.Counter()
        primitive = derived = termcount = 0
        assert len(candidate['states']) == len(req['states']) == mr['states']
        for state, rs in zip(candidate['states'], req['states']):
            assert state['state'] == rs['state'] and state['model'] == rs['model']
            model = read(cp/state['model'])
            entry, = [r for r in manifest['runs'] if r['caseId'] == cid and r['state'] == state['state']]
            run = ROOT/entry['runRoot']/'remote-evidence'/entry['nativeIdentity']
            assert state['nativeRun'] == entry['nativeIdentity']
            assert state['originalModelSha256'] == entry['sourceModelSha256'] == sha(cp/state['model'])
            assert entry['sourceHash'] == candidate['sourceHash']
            assert state['solverBinarySha256'] == entry['solverBinarySha256'] == SOLVER
            assert state['engineVersion'] == entry['engineVersion'] == 'PKPM 2027R1.0.1'
            assert candidate['nativeArtifacts'][entry['nativeIdentity']] == entry['artifacts']
            for name, a in entry['artifacts'].items():
                assert (ROOT/a['path']).resolve() == (run/name).resolve()
                assert sha(ROOT/a['path']) == a['sha256']
            expected_stages = []
            for stage in entry['stages']:
                assert sha(ROOT/stage['path']) == stage['sha256']
                receipt = read(ROOT/stage['path'])
                assert receipt['status'] == 'completed' and receipt['returncode'] == 0
                expected_stages.append({'stage': stage['stage'], 'receiptPath': stage['path'], 'receiptSha256': stage['sha256'], 'executableSha256': receipt['executableSha256']})
            assert state['nativeStageReceipts'] == expected_stages
            assert {'build', 'model', 'data', 'compile', 'analysis', 'extract', 'audit', 'outputguard'} <= {s['stage'] for s in expected_stages}
            pr, script = physical_report(entry)
            independent = read(pr)
            for path, digest in independent['sources'].items():
                assert sha(path) == digest, (cid, path, 'independent report source changed')
            assert independent['nativePostsolveMaterialsSegmentsLoadsConsistent'] is True
            evidence += [ev(pr), ev(script)]
            packet, sdk = read(run/'physical-input.json'), read(run/'sdk-results.json')
            assert sha(run/'physical-input.json') == entry['physicalPacketSha256']
            source_nodes = {n['id']: n for n in model['nodes']}
            source_elements = {e['id']: e for e in model['elements']}
            packet_members = {m['id']: m for m in packet['members']}
            assert set(source_elements) == set(packet_members) == {m['sourceId'] for m in sdk['members']}
            bases = {sid: source_axes(model, e) for sid, e in source_elements.items()}
            for sid, basis in bases.items():
                assert basis == packet_members[sid]['basisGlobal']
            source_native_nodes = {}
            for sid, n in source_nodes.items():
                found = [(i, sn) for i, sn in enumerate(sdk['nodes']) if all(math.isclose(sn['coordinates'][j]/1000, n[k], abs_tol=1e-6, rel_tol=0) for j, k in enumerate('xyz'))]
                assert len(found) == 1
                source_native_nodes[sid] = found[0]
            assert len({i for i, n in source_native_nodes.values()}) == len(source_nodes) == len(sdk['nodes'])
            selected = sorted({(q['selection']['kind'], q['selection']['id']) for q in rs['quantities']})
            executions = []
            for kind, identity in selected:
                selection = {'kind': kind, 'id': identity}
                sf, nf = factors(model, packet, selection)
                executions.append({'selection': selection, 'sourceFactors': sf, 'nativeBasicFactors': nf, 'origin': 'derived-native-superposition' if kind == 'combination' else 'native-basic-case'})
            assert executions == state['selectionExecutions']
            assert len(state['quantities']) == len(rs['quantities']) and len(state['derived']) == len(rs['derived'])
            values, leaves, state_details = {}, {}, []
            for q, rq in zip(state['quantities'], rs['quantities']):
                assert all(q[k] == v for k, v in rq.items())
                assert math.isfinite(q['value'])
                t = q['rawTrace']
                origin = t['origin']
                sf, nf = factors(model, packet, rq['selection'])
                assert t['nativeRun'] == entry['nativeIdentity'] and t['sourceModelSha256'] == entry['sourceModelSha256']
                sid, component = rq['location']['id'], rq['component']
                terms = 0
                if origin == 'derived-from-native-prescribed-boundary':
                    assert cid in ['STD-080', 'STD-082', 'STD-083', 'STD-086'] and component in ['ux', 'uy']
                    assert all(source_nodes[sid]['restraints'])
                    assert not (run/'ConstraintNode.SAT').exists() and not (run/'ConstraintNodeSK.SAT').exists()
                    assert q['quantityStatus'] == origin and t['rawSdkStatus'] == 'unavailable'
                    assert t['boundaryReviewSha256'] == sha(boundary_path)
                    item, = [v for v in boundary['quantities'] if v['case'] == cid and v['state'] == state['state'] and v['quantityId'] == q['id']]
                    assert t['reviewedQuantity'] == item and item['node'] == sid and item['selection'] == q['selection']
                    assert item['proposedValueKind'] == origin and item['SDKRawValue'] == -99999 and item['proposedSeparateBoundaryDerivedValue'] == 0
                    row, = [v for v in boundary['runs'] if v['case'] == cid and v['nativeIdentity'] == entry['nativeIdentity']]
                    assert row['noSpecialSupportDefinitionOrOverride'] is True
                    sources = dict(row['sources']); sources.update(boundary['pinCounterexample']['sources'])
                    assert t['nativeBoundaryEvidenceSha256'] == sources
                    for path, digest in sources.items():
                        assert sha(path) == digest
                    rawt = t['rawSdk']; idx, sn = source_native_nodes[sid]; name = next(iter(nf)); j = ['ux', 'uy', 'uz'].index(component)
                    assert len(nf) == 1 and rawt['jsonPointer'] == f'/nodes/{idx}/cases/{name}/{j}'
                    assert pointer(sdk, rawt['jsonPointer']) == rawt['rawValue'] == -99999
                    assert rawt['sourceSelection'] == q['selection'] and rawt['sourceFactors'] == sf and rawt['nativeBasicFactors'] == nf
                    assert rawt['nativeRun'] == entry['nativeIdentity'] and rawt['sourceModelSha256'] == entry['sourceModelSha256']
                    value = 0.0
                    evidence += [ev(boundary_path), ev(OWN/'review_fixed_boundaries.py')]
                else:
                    assert t['sourceSelection'] == q['selection'] and t['sourceFactors'] == sf and t['nativeBasicFactors'] == nf
                    if q['selection']['kind'] == 'combination':
                        assert t['combinationMethod'] == 'derived-native-superposition'
                    if origin == 'raw-sdk-node-translation':
                        assert rq['location']['kind'] == 'node'
                        idx, sn = source_native_nodes[sid]; j = ['ux', 'uy', 'uz'].index(component)
                        assert t['coordinatesMm'] == sn['coordinates'] and len(t['raw']) == len(nf)
                        value = 0.0
                        for r, (name, factor) in zip(t['raw'], nf.items()):
                            expected = f'/nodes/{idx}/cases/{name}/{j}'
                            assert r == {'artifact': 'sdk-results.json', 'jsonPointer': expected, 'nativeCase': name, 'factor': factor, 'rawValue': sn['cases'][name][j]}
                            v = pointer(sdk, expected)
                            assert math.isfinite(v) and v != -99999
                            value += factor*v; terms += 1
                        assert t['crosscheckArtifacts'] == ['DISP.SAT', 'MESH.SAT', 'NODEINDEX.SAT']
                    elif origin == 'raw-sdk-member-end-cut':
                        assert rq['location']['kind'] == 'member'
                        e = source_elements[sid]
                        xyz = [[source_nodes[n][k] for k in 'xyz'] for n in e['nodes']]
                        L = math.dist(*xyz); pos = rq['location']['positionM']
                        end = 0 if pos == 0 else 1
                        assert (end == 0 and rq['location']['side'] == 'right') or (abs(pos-L) < 1e-9 and rq['location']['side'] == 'left')
                        assert t['end'] == end and t['sourceEndNodes'] == e['nodes']
                        assert t['memberKind'] == e['type'] and t['basisGlobal'] == bases[sid] and t['sourceComponentOrder'] == ACTIONS
                        raw = raw_member(sdk, sid, end, nf, t['raw'])
                        a = actions(e['type'], raw)
                        assert a == t['sourceActions']; value = a[ACTIONS.index(component)]; terms += len(nf)
                    else:
                        assert origin == 'raw-member-end-equilibrium' and any(source_nodes[sid]['restraints'])
                        adjacent = [(eid, e) for eid, e in source_elements.items() if sid in e['nodes']]
                        assert len(t['contributions']) == len(adjacent)
                        total = [0.0]*6
                        for c, (eid, e) in zip(t['contributions'], adjacent):
                            end = e['nodes'].index(sid)
                            assert c['member'] == eid and c['end'] == end and c['basisGlobal'] == bases[eid]
                            raw = raw_member(sdk, eid, end, nf, c['raw'])
                            w = wrench(e['type'], bases[eid], end, raw)
                            assert w == c['globalEndWrench']
                            total = [v+w0 for v, w0 in zip(total, w)]; terms += len(nf)
                        point = [0.0]*6; point_sources = []
                        for lc in model['load_cases']:
                            if lc['id'] not in sf: continue
                            for load in lc['loads']:
                                if load['type'] != 'nodal' or load['node'] != sid: continue
                                assert load.get('reference_frame', 'global') == 'global'
                                vec = [load.get(k, 0)*sf[lc['id']] for k in ['fx', 'fy', 'fz', 'mx', 'my', 'mz']]
                                point = [v+w for v, w in zip(point, vec)]
                                point_sources.append({'case': lc['id'], 'id': load['id'], 'factor': sf[lc['id']], 'globalVector': vec})
                        assert t['externalNodalLoadAtSupport'] == point and t['externalNodalLoadSources'] == point_sources
                        assert t['globalReactionComponents'] == REACTIONS and t['sourceRestraints'] == source_nodes[sid]['restraints']
                        reaction = [v-w for v, w in zip(total, point)]
                        assert reaction == t['globalReaction']; value = reaction[REACTIONS.index(component)]
                    canonical = 'm' if component in ['ux', 'uy', 'uz'] else 'kN' if component in ['N', 'V2', 'V3', 'Fx', 'Fy', 'Fz'] else 'kN.m'
                    assert t['nativeUnit'] == canonical and t['requestedUnit'] == q['unit'] and t['nativeValue'] == value
                assert q['unit'].replace('*', '.') == ('m' if component in ['ux', 'uy', 'uz'] else 'kN' if component in ['N', 'V2', 'V3', 'Fx', 'Fy', 'Fz'] else 'kN.m')
                assert value == q['value']
                values[q['id']] = q; leaves[q['id']] = [q]
                origins[origin] += 1; counts[origin] += 1; primitive += 1; termcount += terms
                state_details.append({'id': q['id'], 'origin': origin, 'value': value, 'rawCaseTermCount': terms, 'replayExact': True})
            for d, rd in zip(state['derived'], rs['derived']):
                assert all(d[k] == v for k, v in rd.items())
                assert rd['operation'] == 'difference' and len(rd['operands']) == 2
                operands = [values[k] for k in rd['operands']]
                assert all(q['unit'].replace('*', '.') == d['unit'].replace('*', '.') for q in operands)
                assert d['value'] == operands[0]['value']-operands[1]['value']
                selected = [q for key in rd['operands'] for q in leaves[key]]
                assert d['operandSelections'] == [q['selection'] for q in selected]
                selections = []
                for q in selected:
                    if q['selection'] not in selections: selections.append(q['selection'])
                assert len(selections) == 1 and d['selection'] == selections[0]
                values[d['id']] = d; leaves[d['id']] = selected; derived += 1
                state_details.append({'id': d['id'], 'operation': 'difference', 'value': d['value'], 'operandTraceRetained': True, 'replayExact': True})
            statechecks.append({'state': state['state'], 'nativeRun': entry['nativeIdentity'], 'primitiveCount': len(state['quantities']), 'derivedCount': len(state['derived']), 'rawSourceAndStageArtifactsRehashed': True, 'originalPhysicalIndependentReportSourcesUnchanged': True, 'allTraceReplayExact': True})
            all_details.append({'case': cid, 'state': state['state'], 'quantities': state_details})
        assert primitive == mr['quantities'] and derived == mr['derived']
        assert origins['derived-from-native-prescribed-boundary'] == mr['boundaryDerivedQuantities']
        assert mr['unavailableQuantities'] == mr['unavailableDerived'] == 0
        unique_evidence = {e['path']: e for e in evidence}
        reviewed.append({'id': cid, 'status': 'qualified', 'sourceHash': candidate['sourceHash'], 'candidateSha256': sha(candidate_path), 'reasons': [], 'checks': {'nativeTruthOnly': True, 'inputBlindReview': 'pending-separate-gate', 'primitiveCount': primitive, 'derivedCount': derived, 'traceTermCount': termcount, 'traceOrigins': dict(origins), 'states': statechecks, 'noMatrixValuesUsed': True, 'frozenRequestMetadataAndTolerancesPreserved': True, 'qualificationBoundary': 'PKPM 2027R1.0.1 observed first-order orthogonal positive-X/Y zero-roll beams and vertical positive-Z columns; source inward endpoint cuts only. Explicit custom E/nu and numeric A/J/I compiled/read back; no stress/design/other-section or axis generalization.', 'finiteShearEvidence': {'nativeScalarAsReadbackAvailable': False, 'declaredAs': 'Asy=Asz=5A/6', 'qualificationBasis': 'Bounded behavioral qualification from independent two-length, six-material and six-numeric-section controls plus complete six-DOF/end-force/equilibrium review of every retained state. No response-fitted material/section/shear parameter and no tolerance change.'}, 'supportOrigin': 'Reconstructed from native member resisting-end wrenches minus explicit point load, not SDK node reaction.', 'fixedMissingTranslations': 'Only explicitly named reviewed homogeneous fixed-boundary consequences may be derived; raw SDK -99999 is preserved. Finite pin translations are excluded.', 'pinRepresentation': 'Where present: native 1e14 translational springs and zero rotational springs are retained; independent spring-vs-ideal differences quantified, no exact-zero claim.'}, 'evidence': list(unique_evidence.values())})
    out = {'schemaVersion': 1, 'reviewer': REVIEWER, 'engine': 'PKPM', 'reviewScope': 'Named same-engine native truth qualification, separate from input blind review and end-to-end agent acceptance. Historical diagnostic reports retain their former zero-qualification status; this report adds the final request-trace/source-binding decision without rewriting them.', 'cases': reviewed, 'traceReplayDetails': all_details, 'evidenceManifest': ev(mp), 'candidateManifest': ev(candidate_dir/'manifest.json'), 'crossEngineDiagnosticExceptions': {'case': 'STD-089', 'quantityIds': ['case-D-member-x0-0-1-s0-right-M3', 'case-D-member-x0-0-2-s0-right-M3'], 'treatment': 'Original native values and frozen tolerances retained. Native slot/source endpoint identity and equilibrium were independently qualified; the two small cross-engine relative-tolerance differences do not invalidate native truth provenance, and remain diagnostic failures rather than being rounded or replaced.'}, 'scopeLimitations': ['No actual native As scalar readback is claimed.', 'Raw native values remain finite-precision observations; member-force-derived supports inherit that precision.', 'The 58 boundary-derived values are not direct SDK observations and retain the complete executed native boundary/DOF evidence plus pin counterexample.', 'Old built-in C30 control material uncertainty is historical; production runs use separately bound custom native materials.']}
    Path(output).write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps({'cases': len(reviewed), 'qualified': sum(r['status'] == 'qualified' for r in reviewed), 'primitive': sum(r['checks']['primitiveCount'] for r in reviewed), 'derived': sum(r['checks']['derivedCount'] for r in reviewed), 'terms': sum(r['checks']['traceTermCount'] for r in reviewed), 'origins': counts, 'reportSha256': sha(output)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--candidates', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    main(a.candidates, a.output)
