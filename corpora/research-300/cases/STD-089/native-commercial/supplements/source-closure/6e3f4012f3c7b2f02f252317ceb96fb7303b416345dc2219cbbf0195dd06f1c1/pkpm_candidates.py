"""Local-only frozen-request extraction; no structural solver, remote call or acceptance mutation."""
import argparse, copy, hashlib, json, math, sys
from pathlib import Path
REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference_io import ReferenceInputError, load_case, selection_factors, quantity_unit, convert_value, evaluate_derived, write_json_exclusive
try:
    from .pkpm_results import source_actions, end_wrench
except ImportError:
    from pkpm_results import source_actions, end_wrench
ACTIONS = ['N', 'V2', 'V3', 'T', 'M2', 'M3']
REACTIONS = ['Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz']
DISPLACEMENTS = ['ux', 'uy', 'uz']

def read(p):
    return json.loads(p.read_text())

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

class Run:

    def __init__(self, evidence_root, entry, model, boundary=None):
        self.evidence_root = Path(evidence_root)
        self.entry = entry
        self.boundary = boundary
        runroot = checked_path(self.evidence_root, entry['runRoot'])
        identity = entry['nativeIdentity']
        source_hash = entry['sourceModelSha256']
        self.expected = entry['artifacts']
        self.stage_artifacts = {row['stage']: row for row in entry.get('stages', [])}
        if entry.get('engineVersion') != 'PKPM 2027R1.0.1' or 'analysis' not in self.stage_artifacts:
            raise ValueError('Missing executed engine/stage identity')
        verify_artifacts(self.evidence_root, self.stage_artifacts)
        self.execution = []
        for stage, record in self.stage_artifacts.items():
            receipt = read(checked_path(self.evidence_root, record['path']))
            if receipt.get('status') != 'completed' or receipt.get('returncode') != 0:
                raise ValueError('Native stage did not complete successfully')
            self.execution.append({'stage': stage, 'receiptPath': record['path'], 'receiptSha256': record['sha256'], 'executableSha256': receipt['executableSha256']})
        verify_artifacts(self.evidence_root, self.expected)
        self.root = runroot
        self.path = runroot / 'remote-evidence' / identity
        self.identity = identity
        if Path(identity).name != identity or not identity.startswith('c30-'):
            raise ValueError('Invalid native identity')
        required = ('physical-input.json', 'frame-input-receipt.json', 'frame-after-solve-input-audit.json', 'native-output-audit.json', 'frame-numeric-input.json', 'frame-numeric-output.json', 'sdk-results.json')
        if any(n not in self.expected for n in required):
            raise ValueError('Frozen manifest lacks required native inputs')
        for name, record in self.expected.items():
            if checked_path(self.evidence_root, record['path']) != (self.path / name).resolve():
                raise ValueError('Artifact path differs from native run binding')
        self.source_hash = source_hash
        self.model = model
        self.packet = read(self.path / 'physical-input.json')
        self.sdk = read(self.path / 'sdk-results.json')
        self.receipt = read(self.path / 'frame-input-receipt.json')
        solver_sha = read(self.path / 'frame-numeric-input.json')['solverSha256']
        if solver_sha != entry['solverBinarySha256'] or solver_sha != '333b010d067f820c453972833e18bc9db2328059cbba83e456effd0dc79d9a4d':
            raise ValueError('Executed solver binary identity differs from frozen manifest')
        if not self.receipt['inputSha256'] == sha(self.path / 'physical-input.json'):
            raise ValueError("Native input guard failed: self.receipt['inputSha256'] == sha(self.path / 'physical-input.json')")
        if not read(self.path / 'frame-after-solve-input-audit.json')['parametersMatchBefore']:
            raise ValueError("Native input guard failed: read(self.path / 'frame-after-solve-input-audit.json')['parametersMatchBefore']")
        if not read(self.path / 'native-output-audit.json')['sourceMembersCovered'] == len(model['elements']):
            raise ValueError("Native input guard failed: read(self.path / 'native-output-audit.json')['sourceMembersCovered'] == len(model['elements'])")
        for row in read(self.path / 'frame-numeric-output.json').values():
            if not row['allMechanicalRecordsMatch']:
                raise ValueError("Native input guard failed: row['allMechanicalRecordsMatch']")
        self.members = {m['sourceId']: (i, m) for (i, m) in enumerate(self.sdk['members'])}
        self.physical = {m['id']: m for m in self.packet['members']}
        self.elements = {m['id']: m for m in model['elements']}
        self.nodes = {n['id']: n for n in model['nodes']}
        self.sdk_nodes = {}
        if not set(self.members) == set(self.elements) == set(self.physical):
            raise ValueError('Native input guard failed: set(self.members) == set(self.elements) == set(self.physical)')
        for (eid, e) in self.elements.items():
            (a, b) = [self.nodes[n] for n in e['nodes']]
            d = [b[k] - a[k] for k in 'xyz']
            R = self.physical[eid]['basisGlobal']
            kind = e['type']
            if not e.get('rotation_angle', 0) == 0:
                raise ValueError("Native input guard failed: e.get('rotation_angle', 0) == 0")
            if kind == 'column':
                if not (d[0] == d[1] == 0 and d[2] > 0):
                    raise ValueError('Native input guard failed: d[0] == d[1] == 0 and d[2] > 0')
                expected = [[0, 0, 1], [0, -1, 0], [1, 0, 0]]
            else:
                if not (kind == 'beam' and d[2] == 0 and (d[0] > 0 and d[1] == 0 or (d[1] > 0 and d[0] == 0))):
                    raise ValueError("Native input guard failed: kind == 'beam' and d[2] == 0 and (d[0] > 0 and d[1] == 0 or (d[1] > 0 and d[0] == 0))")
                expected = [[1, 0, 0], [0, 1, 0], [0, 0, 1]] if d[0] > 0 else [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]
            if not R == expected:
                raise ValueError('Native input guard failed: R == expected')
        for (i, n) in enumerate(self.sdk['nodes']):
            matches = [sid for (sid, s) in self.nodes.items() if all((math.isclose(n['coordinates'][j] / 1000, s[k], rel_tol=0, abs_tol=1e-06) for (j, k) in enumerate('xyz')))]
            if not len(matches) == 1:
                raise ValueError('Native input guard failed: len(matches) == 1')
            sid = matches[0]
            if not sid not in self.sdk_nodes:
                raise ValueError('Native input guard failed: sid not in self.sdk_nodes')
            self.sdk_nodes[sid] = (i, n)
        self.artifacts = copy.deepcopy(self.expected)

    def verify(self):
        verify_artifacts(self.evidence_root, self.expected)
        verify_artifacts(self.evidence_root, self.stage_artifacts)

    def factors(self, selection):
        factors = selection_factors(self.model, selection)
        if self.packet['selection']['kind'] == 'basic-cases':
            return (factors, {self.packet['selection']['nativeCases'][k]['name']: v for (k, v) in factors.items()})
        if not selection == {k: self.packet['selection'][k] for k in ['kind', 'id']}:
            raise ValueError("Native input guard failed: selection == {k: self.packet['selection'][k] for k in ['kind', 'id']}")
        if not factors == self.packet['selection']['factors']:
            raise ValueError("Native input guard failed: factors == self.packet['selection']['factors']")
        return (factors, {'DL': 1.0})

    def raw_member(self, eid, end, native_factors):
        (idx, m) = self.members[eid]
        last = 8 if m['kind'] == 'beam' else 1
        station = '0' if end == 0 else str(last)
        values = [0.0] * 6
        trace = []
        for (case, factor) in native_factors.items():
            rows = m['forces'][case]
            if not sorted(map(int, rows)) == list(range(last + 1)):
                raise ValueError('Native input guard failed: sorted(map(int, rows)) == list(range(last + 1))')
            raw = rows[station]
            source_actions(m['kind'], raw)
            values = [a + factor * b for (a, b) in zip(values, raw)]
            trace.append({'artifact': 'sdk-results.json', 'jsonPointer': f'/members/{idx}/forces/{case}/{station}', 'nativeCase': case, 'factor': factor, 'rawSixSlots': raw})
        return (values, trace)

    def quantity(self, q):
        (source_factors, native_factors) = self.factors(q['selection'])
        location = q['location']
        component = q['component']
        sid = location['id']
        trace = {'nativeRun': self.identity, 'sourceModelSha256': self.source_hash, 'sourceSelection': q['selection'], 'sourceFactors': source_factors, 'nativeBasicFactors': native_factors}
        if location['kind'] == 'member':
            member = self.physical[sid]
            L = member['lengthM']
            x = location['positionM']
            if not (x == 0 and location['side'] == 'right' or (math.isclose(x, L, rel_tol=0, abs_tol=1e-09) and location['side'] == 'left')):
                raise ValueError('Only inward member-end cuts calibrated')
            end = 0 if x == 0 else 1
            (raw, rows) = self.raw_member(sid, end, native_factors)
            actions = source_actions(member['type'], raw)
            value = actions[ACTIONS.index(component)]
            trace.update(origin='raw-sdk-member-end-cut', raw=rows, memberKind=member['type'], basisGlobal=member['basisGlobal'], sourceActions=actions, sourceComponentOrder=ACTIONS, end=end, sourceEndNodes=member['nodes'])
        elif component in DISPLACEMENTS:
            (idx, n) = self.sdk_nodes[sid]
            j = DISPLACEMENTS.index(component)
            values = []
            for (case, factor) in native_factors.items():
                raw = n['cases'][case][j]
                if not math.isfinite(raw) or raw == -99999:
                    result = copy.deepcopy(q)
                    result.update(value=None, quantityStatus='unavailable', rawTrace={**trace, 'origin': 'raw-sdk-node-translation', 'reason': 'native missing sentinel; no fixed-boundary zero imputed', 'artifact': 'sdk-results.json', 'jsonPointer': f'/nodes/{idx}/cases/{case}/{j}', 'rawValue': raw})
                    if self.boundary:
                        derived = self.boundary.derive(self, q, result)
                        if derived is not None:
                            return derived
                    return result
                values.append((factor, raw))
            value = sum((f * v for (f, v) in values))
            trace.update(origin='raw-sdk-node-translation', raw=[{'artifact': 'sdk-results.json', 'jsonPointer': f'/nodes/{idx}/cases/{case}/{j}', 'nativeCase': case, 'factor': factor, 'rawValue': n['cases'][case][j]} for (case, factor) in native_factors.items()], coordinatesMm=n['coordinates'], crosscheckArtifacts=['DISP.SAT', 'MESH.SAT', 'NODEINDEX.SAT'])
        else:
            if not (component in REACTIONS and any(self.nodes[sid]['restraints'])):
                raise ValueError('Reaction requires declared support')
            total = [0.0] * 6
            contributions = []
            for (eid, e) in self.elements.items():
                if sid not in e['nodes']:
                    continue
                end = e['nodes'].index(sid)
                (raw, rows) = self.raw_member(eid, end, native_factors)
                basis = self.physical[eid]['basisGlobal']
                w = end_wrench(e['type'], basis, end, raw)
                total = [a + b for (a, b) in zip(total, w)]
                contributions.append({'member': eid, 'end': end, 'basisGlobal': basis, 'raw': rows, 'globalEndWrench': w})
            if not contributions:
                raise ValueError('Missing native member ends at support')
            point = [0.0] * 6
            point_sources = []
            for case in self.model['load_cases']:
                if case['id'] not in source_factors:
                    continue
                for ld in case['loads']:
                    if ld['type'] == 'nodal' and ld['node'] == sid:
                        if not ld.get('reference_frame', 'global') == 'global':
                            raise ValueError("Native input guard failed: ld.get('reference_frame', 'global') == 'global'")
                        v = [ld.get(k, 0) * source_factors[case['id']] for k in ['fx', 'fy', 'fz', 'mx', 'my', 'mz']]
                        point = [a + b for (a, b) in zip(point, v)]
                        point_sources.append({'case': case['id'], 'id': ld['id'], 'factor': source_factors[case['id']], 'globalVector': v})
            reaction = [a - b for (a, b) in zip(total, point)]
            value = reaction[REACTIONS.index(component)]
            trace.update(origin='raw-member-end-equilibrium', contributions=contributions, externalNodalLoadAtSupport=point, externalNodalLoadSources=point_sources, globalReactionComponents=REACTIONS, globalReaction=reaction, sourceRestraints=self.nodes[sid]['restraints'])
        if q['selection']['kind'] == 'combination':
            trace['combinationMethod'] = 'derived-native-superposition'
        trace.update(nativeUnit=quantity_unit(component), requestedUnit=q['unit'], nativeValue=value)
        result = copy.deepcopy(q)
        result['value'] = convert_value(value, quantity_unit(component), q['unit'])
        result['rawTrace'] = trace
        return result


def checked_path(root, relative):
    root = Path(root).resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError('Evidence path escapes its root')
    return candidate


def verify_artifacts(root, artifacts):
    for name, record in artifacts.items():
        path = checked_path(root, record['path'])
        if not path.is_file() or sha(path) != record['sha256']:
            raise ValueError(f'Native artifact SHA mismatch: {name}')


class BoundaryReview:
    """Optional reviewed boundary consequence; never changes raw SDK status."""
    def __init__(self, path, expected, evidence_root, corpus):
        self.path = Path(path)
        self.expected = expected
        self.root = Path(evidence_root)
        self.corpus = Path(corpus)
        self.document = None
        self.reason = 'No frozen boundary review binding'
        if expected and self.path.is_file() and sha(self.path) == expected.get('sha256'):
            self.document = read(self.path)
            self.reason = None

    def source_path(self, name):
        corpus_prefix = 'corpora/research-300/cases/'
        evidence_prefix = '.bench-work/commercial-246/'
        if name.startswith(corpus_prefix):
            return checked_path(self.corpus, name[len(corpus_prefix):])
        if name.startswith(evidence_prefix):
            return checked_path(self.root, name[len(evidence_prefix):])
        raise ValueError('Unrecognized boundary evidence path')

    def derive(self, run, request, unavailable):
        if self.document is None or sha(self.path) != self.expected['sha256']:
            return None
        if not all(run.nodes[request['location']['id']]['restraints']):
            return None
        if any((run.path / n).exists() for n in ('ConstraintNode.SAT', 'ConstraintNodeSK.SAT')):
            return None
        matches = [q for q in self.document['quantities']
                   if q['case'] == run.entry['caseId'] and q['state'] == run.entry['state']
                   and q['quantityId'] == request['id'] and q['selection'] == request['selection']
                   and q['node'] == request['location']['id'] and q['component'] == request['component']]
        rows = [r for r in self.document['runs']
                if r['case'] == run.entry['caseId'] and r['nativeIdentity'] == run.identity]
        if len(matches) != 1 or len(rows) != 1:
            return None
        item, row = matches[0], rows[0]
        if (item['proposedValueKind'] != 'derived-from-native-prescribed-boundary'
                or item['proposedSeparateBoundaryDerivedValue'] != 0
                or item['SDKRawValue'] != -99999
                or not row['noSpecialSupportDefinitionOrOverride']):
            return None
        sources = dict(row['sources'])
        sources.update(self.document['pinCounterexample']['sources'])
        try:
            if any(not self.source_path(p).is_file() or sha(self.source_path(p)) != digest
                   for p, digest in sources.items()):
                return None
        except ValueError:
            return None
        result = copy.deepcopy(request)
        result.update(value=0.0, quantityStatus='derived-from-native-prescribed-boundary', rawTrace={
            'origin': 'derived-from-native-prescribed-boundary',
            'nativeRun': run.identity, 'sourceModelSha256': run.source_hash,
            'rawSdk': unavailable['rawTrace'], 'rawSdkStatus': 'unavailable',
            'boundaryReviewSha256': self.expected['sha256'], 'reviewedQuantity': item,
            'nativeBoundaryEvidenceSha256': sources,
            'reason': 'Homogeneous prescribed boundary excluded from solved unknowns; independently reviewed executed input/DOF chain.',
            'limits': self.document['limitations'],
        })
        return result


def export_candidates(evidence_root, corpus, output, boundary_review=None):
    """Export only SHA-bound native data, preserving requested metadata and missing values."""
    evidence_root, corpus, output = map(Path, (evidence_root, corpus, output))
    manifest_path = evidence_root / 'pkpm-candidate-evidence-manifest.json'
    manifest_hash = sha(manifest_path)
    manifest = read(manifest_path)
    if manifest.get('schemaVersion') != 1 or not manifest.get('runs'):
        raise ValueError('Invalid frozen evidence manifest')
    boundary = BoundaryReview(boundary_review, manifest.get('boundaryReview'), evidence_root, corpus) if boundary_review else None
    bindings = {}
    for entry in manifest['runs']:
        key = (entry['caseId'], entry['state'])
        if key in bindings:
            raise ValueError('Duplicate case/state evidence binding')
        bindings[key] = entry
    loaded_cases, runs, payloads, summary = {}, [], {}, []
    for case_id in sorted({k[0] for k in bindings}):
        loaded = load_case(corpus / case_id)
        loaded_cases[case_id] = loaded
        states, artifacts = [], {}
        for state in loaded['states']:
            entry = bindings[(case_id, state['state'])]
            if (entry['sourceHash'] != loaded['sourceHash']
                    or entry['sourceModelSha256'] != loaded['hashes'][state['modelPath']]):
                raise ValueError(f'Authored source SHA mismatch: {case_id} state {state["state"]}')
            run = Run(evidence_root, entry, state['model'], boundary)
            runs.append(run)
            quantities = [run.quantity(q) for q in state['quantities']]
            derived, valid_definitions = [], []
            for definition in state['derived']:
                try:
                    evaluated = evaluate_derived([q for q in quantities if q['value'] is not None], valid_definitions + [definition])
                    derived.append(evaluated[-1])
                    valid_definitions.append(definition)
                except ReferenceInputError as error:
                    derived.append({**copy.deepcopy(definition), 'value': None,
                                    'quantityStatus': 'unavailable-dependent-operand', 'reason': str(error)})
            states.append({'state': state['state'], 'model': state['modelPath'],
                           'originalModelSha256': entry['sourceModelSha256'],
                           'engineVersion': entry['engineVersion'], 'solverBinarySha256': entry['solverBinarySha256'],
                           'nativeRun': entry['nativeIdentity'], 'nativeStageReceipts': run.execution,
                           'selectionExecutions': [{'selection': selection, 'sourceFactors': run.factors(selection)[0], 'nativeBasicFactors': run.factors(selection)[1], 'origin': 'derived-native-superposition' if selection['kind'] == 'combination' else 'native-basic-case'} for selection in [dict(kind=kind, id=identity) for kind, identity in sorted({(q['selection']['kind'], q['selection']['id']) for q in quantities})]],
                           'quantities': quantities, 'derived': derived})
            artifacts[entry['nativeIdentity']] = run.artifacts
        payload = {
            'schemaVersion': 1, 'id': case_id, 'modelId': loaded['contract']['modelId'],
            'referenceKind': 'native-pkpm-candidate', 'method': 'native-pkpm2027-api-and-member-end-equilibrium',
            'sameEngineTruthStatus': 'pending', 'nativeIndependentReview': 'pending',
            'status': 'candidate-only; no acceptance', 'notCommercialScoringTruth': True,
            'accepted': False, 'nativeVerified': False,
            'analysisConvention': copy.deepcopy(loaded['contract'].get('analysisConvention')),
            'inputHashes': loaded['hashes'], 'sourceHash': loaded['sourceHash'],
            'sourceManifest': loaded['sourceManifest'], 'frozenEvidenceManifestSha256': manifest_hash,
            'solver': {'product': 'PKPM', 'version': '2027R1.0.1',
                       'solverSha256': '333b010d067f820c453972833e18bc9db2328059cbba83e456effd0dc79d9a4d',
                       'materialDllSha256': '0045850ca7dfa7f2f3a71fd6b6f807d1be432974f30e388a520185dbf60a00f9',
                       'exporterSha256': sha(Path(__file__)),
                       'slotMappingSha256': sha(Path(__file__).with_name('pkpm_results.py')),
                       'referenceIoSha256': sha(Path(__file__).resolve().parents[1] / 'reference_io.py')},
            'nativeArtifacts': artifacts, 'states': states,
            'limits': ['SDK missing values remain unavailable unless a separately bound boundary review explicitly supports a derived value.',
                       'Support reactions are raw-member-end-equilibrium reconstructions, not a node-reaction API return.',
                       'Only calibrated principal axes and inward member-end cuts are supported.',
                       'Pinned translations retain finite native 1e14 stiffness; three rotational springs are zero.',
                       'As=5A/6 is prescribed and response-checked; direct native scalar As readback is unavailable.',
                       'STD091 combinations are explicit derived-native-superposition of native DL/LL.']}
        payloads[case_id] = payload
        summary.append({'caseId': case_id, 'states': len(states),
                        'quantities': sum(len(s['quantities']) for s in states),
                        'derived': sum(len(s['derived']) for s in states),
                        'unavailableQuantities': sum(q['value'] is None for s in states for q in s['quantities']),
                        'boundaryDerivedQuantities': sum(q.get('quantityStatus') == 'derived-from-native-prescribed-boundary' for s in states for q in s['quantities']),
                        'unavailableDerived': sum(q['value'] is None for s in states for q in s['derived']),
                        'sourceHash': loaded['sourceHash']})
    # Revalidate every authored and native byte after extraction, before publishing candidates.
    if sha(manifest_path) != manifest_hash:
        raise ValueError('Frozen evidence manifest changed during extraction')
    for case_id, before in loaded_cases.items():
        if load_case(corpus / case_id)['sourceHash'] != before['sourceHash']:
            raise ValueError('Authored source changed during extraction')
    for run in runs:
        run.verify()
    if boundary and boundary.document is not None:
        for run in runs:
            for state in payloads[run.entry['caseId']]['states']:
                if state['state'] != run.entry['state']:
                    continue
                for quantity in state['quantities']:
                    if quantity.get('quantityStatus') == 'derived-from-native-prescribed-boundary':
                        if boundary.derive(run, quantity, {'rawTrace': quantity['rawTrace']['rawSdk']}) is None:
                            raise ValueError('Boundary evidence changed during extraction')
    if output.exists():
        raise ValueError('Candidate output directory already exists')
    for row in summary:
        path = output / row['caseId'] / 'native-reference.json'
        write_json_exclusive(path, payloads[row['caseId']])
        row['artifactSha256'] = sha(path)
    result = {'status': 'candidate-only; no acceptance', 'results': summary,
              'totalStates': sum(r['states'] for r in summary),
              'totalQuantities': sum(r['quantities'] for r in summary),
              'unavailableQuantities': sum(r['unavailableQuantities'] for r in summary),
              'boundaryDerivedQuantities': sum(r['boundaryDerivedQuantities'] for r in summary)}
    write_json_exclusive(output / 'manifest.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=Path, default=REPOSITORY / '.bench-work/commercial-246')
    parser.add_argument('--corpus', type=Path, default=REPOSITORY / 'corpora/research-300/cases')
    parser.add_argument('--output', type=Path, default=REPOSITORY / '.bench-work/commercial-246/pkpm-native-candidates')
    parser.add_argument('--boundary-review', type=Path)
    args = parser.parse_args()
    print(json.dumps(export_candidates(args.evidence_root, args.corpus, args.output, args.boundary_review), indent=2))


if __name__ == '__main__':
    main()
