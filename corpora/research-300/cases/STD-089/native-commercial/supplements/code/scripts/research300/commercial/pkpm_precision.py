"""Generate an explicit engineering comparison policy; never replace native values.

The allowance uses an independently constructed canonical recovery expression.
It is NOT a proved error bound for PKPM's unknown internal arithmetic. It changes
the acceptance region, so consumers must retain the original strict comparison.
Only previously reviewed principal-axis, fixed-base, single native DL runs are
currently supported. No solve, remote execution, or acceptance promotion occurs.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np

REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference_io import (convert_value, load_case, quantity_unit,
                          write_json_exclusive)
from reference_solver import local_stiffness, _consistent_load
try:
    from .pkpm_candidates import Run, checked_path, read, sha
except ImportError:
    from pkpm_candidates import Run, checked_path, read, sha

ACTIONS = ('N', 'V2', 'V3', 'T', 'M2', 'M3')
U = 2.0 ** -24
POLICY = 'native-f32-recovery-scale-v1'
CANONICAL = {
    'id': 'source-local-timoshenko-12dof-row-v1',
    'dofOrder': ['ux_i', 'uy_i', 'uz_i', 'rx_i', 'ry_i', 'rz_i',
                 'ux_j', 'uy_j', 'uz_j', 'rx_j', 'ry_j', 'rz_j'],
    'expression': 'source cut sign * (canonical stiffness row dot native local DISP - consistent fixed-end load)',
    'termOrder': 'Increasing stiffness-row column index, then input packet distributed-load order.',
    'structuralTerms': 'Include every nonzero stiffness coefficient even when its displacement is zero. Include each nonzero fixed-end-load contribution separately. No merging, thresholding, or algebraic rewriting.',
    'shearAreas': 'Asy=Asz=5*A/6: published convention and response-checked hypothesis, not a raw native scalar readback.',
    'geometry': 'Length from the source-oriented float32 SDATA endpoints; principal-axis basis from the validated physical packet.',
    'allowance': 'gamma_(2*n-1) * sum(abs(terms)); gamma_m=m*u/(1-m*u), u=2^-24.',
}
LIMITS = [
    'A new conservative engineering comparison policy; the acceptance region changes.',
    'Keep authored strict-tolerance results separately; native values and tolerances are unchanged.',
    'This is an analytical recovery scale, not a proved vendor arithmetic error bound.',
    'Vendor internal stiffness, operation ordering and factorization precision are unobserved.',
    'No input-error, displacement-quantization or observed-discrepancy allowance is added.',
    'Only raw member endpoint requests are covered; node translations, reactions and derived quantities are excluded.',
    'Only reviewed principal axes, fixed bases, uniform line loads, first-order linear response, and a single native DL selection are supported.',
]


def _numbers(values, label):
    if any(isinstance(x, bool) or not isinstance(x, (int, float, np.floating))
           or not math.isfinite(float(x)) or x == -99999 for x in values):
        raise ValueError(f'Missing or nonfinite {label}')


def precision_metadata(terms, unit):
    terms = list(terms)
    if not terms:
        raise ValueError('A canonical recovery requires structural terms')
    _numbers(terms, 'recovery term')
    count = len(terms)
    operations = 2 * count - 1
    if operations * U >= 1:
        raise ValueError('Recovery term count exceeds policy domain')
    scale = math.fsum(abs(float(x)) for x in terms)
    allowance = operations * U / (1 - operations * U) * scale
    if not math.isfinite(scale) or not math.isfinite(allowance):
        raise ValueError('Recovery scale overflows')
    return {'kind': 'analytical-recovery-scale', 'policy': POLICY,
            'nativeArithmeticBound': False, 'acceptanceRegionChanges': True,
            'unit': unit, 'unitRoundoff': U, 'terms': [float(x) for x in terms],
            'structuralTermCount': count, 'recoveryScale': scale,
            'absoluteAllowance': allowance}


def endpoint_terms(component, end, displacement_local, distributed_local, *,
                   length, E, G, A, J, Iy, Iz):
    """Canonical signed cut terms, using kN/m units; no measured force argument."""
    if component not in ACTIONS or end not in (0, 1):
        raise ValueError('Only calibrated member endpoint actions are supported')
    if len(displacement_local) != 12:
        raise ValueError('Twelve native local displacement components are required')
    _numbers(displacement_local, 'native displacement')
    parameters = (length, E, G, A, J, Iy, Iz)
    _numbers(parameters, 'mechanical parameter')
    if any(x <= 0 for x in parameters):
        raise ValueError('Mechanical parameters must be positive')
    k = local_stiffness({'type': 'beam'}, {'E': E / 1000., 'G': G / 1000.},
                        {'properties': {'A': A, 'J': J, 'Iy': Iy, 'Iz': Iz}},
                        length, {'Asy': 5 * A / 6, 'Asz': 5 * A / 6})
    index = ACTIONS.index(component)
    row = index + 6 * end
    sign = (-1, 1, 1, -1, -1, -1)[index] if end == 0 else (1, -1, -1, 1, 1, 1)[index]
    terms, labels = [], []
    for column, coefficient in enumerate(k[row]):
        if coefficient != 0:  # Structural sparsity; never filter by product value.
            terms.append(float(sign * coefficient * displacement_local[column]))
            labels.append(f'k[{row},{column}]*d[{column}]')
    for ordinal, load in enumerate(distributed_local):
        if len(load) != 3:
            raise ValueError('Uniform local loads require three components')
        _numbers(load, 'distributed load')
        f = _consistent_load(np.array(load), np.array(load), length)
        if f[row] != 0:
            terms.append(float(-sign * f[row]))
            labels.append(f'-fixedEndLoad[{ordinal},{row}]')
    return terms, labels


def _floats(path):
    raw = path.read_bytes()
    if len(raw) % 4:
        raise ValueError(f'Unaligned float32 native file: {path.name}')
    values = np.frombuffer(raw, dtype='<f4').astype(float)
    if not np.all(np.isfinite(values)):
        raise ValueError(f'Nonfinite native file: {path.name}')
    return values


def native_displacements(run):
    """Reviewed NODEINDEX floor order and ordinary fixed boundary only."""
    constraints = np.frombuffer((run.path / 'ConstraintNodeNo.SAT').read_bytes(), dtype='<i4')
    mesh_bytes = (run.path / 'MESH.SAT').read_bytes()
    if len(mesh_bytes) < 20 or (len(mesh_bytes) - 20) % 20:
        raise ValueError('Invalid mixed-field native MESH layout')
    mesh = np.frombuffer(mesh_bytes, dtype='<f4')[5:].reshape(-1, 5)[:, :3].astype(float)
    mesh_flags = np.frombuffer(mesh_bytes, dtype='<i4')[5:].reshape(-1, 5)[:, 3]
    if not np.all(np.isfinite(mesh)):
        raise ValueError('Nonfinite native mesh coordinates')
    if len(constraints) != len(mesh) + 4 or np.any(constraints[4:]):
        raise ValueError('Special/native spring constraints are outside precision policy scope')
    if any((run.path / name).exists() for name in ('ConstraintNode.SAT', 'ConstraintNodeSK.SAT')):
        raise ValueError('Special boundary override is outside precision policy scope')
    story_count = len(run.packet['stories'])
    index = _floats(run.path / 'NODEINDEX.SAT')
    counts = [int(x) for x in index[:story_count]]
    if any(x < 0 for x in counts) or len(index) != story_count + 2 * sum(counts):
        raise ValueError('Invalid native NODEINDEX layout')
    ids = [int(x) for x in index[story_count::2]]
    if len(set(ids)) != len(ids) or any(x < 1 or x > len(mesh) for x in ids):
        raise ValueError('Invalid native mesh index')
    groups, position = [], 0
    for count in counts:
        groups.append(ids[position:position + count])
        position += count
    order = [i for group in reversed(groups) for i in group]
    raw = _floats(run.path / 'DISP.SAT')
    if raw.size != 2 * len(order) * 6:
        raise ValueError('Only the reviewed two-case native DISP layout is supported')
    raw = raw.reshape(2, len(order), 6)
    result, mapping = {}, []
    for record, mesh_id in enumerate(order):
        xyz = mesh[mesh_id - 1, :3]
        matches = [nid for nid, node in run.nodes.items()
                   if np.allclose(xyz, [node[c] for c in 'xyz'], atol=1e-6, rtol=0)]
        if len(matches) != 1 or matches[0] in result:
            raise ValueError('Ambiguous native node identity')
        nid = matches[0]
        if any(run.nodes[nid]['restraints']) or mesh_flags[mesh_id - 1] != 100:
            raise ValueError('Unexpected active native boundary node')
        result[nid] = raw[0, record, [0, 1, 5, 3, 4, 2]].tolist()
        mapping.append({'node': nid, 'origin': 'native-DISP-DL', 'meshIndex': mesh_id,
                        'record': record, 'byteOffset': record * 24})
    for nid, node in run.nodes.items():
        if nid in result:
            continue
        matches = [i for i, row in enumerate(mesh)
                   if np.allclose(row[:3], [node[c] for c in 'xyz'], atol=1e-6, rtol=0)]
        if not all(node['restraints']) or len(matches) != 1 or mesh_flags[matches[0]] != -1:
            raise ValueError('Missing native DOF without an ordinary fixed boundary')
        result[nid] = [0.] * 6
        mapping.append({'node': nid, 'origin': 'prescribed-fixed-boundary-for-scale-only',
                        'meshIndex': matches[0] + 1,
                        'proof': 'Six source restraints; MESH fixed flag; eliminated from NODEINDEX/DISP; no special constraints.'})
    return result, mapping


def native_properties(run):
    document = read(run.path / 'frame-numeric-input.json')
    data = {name: (run.path / name).read_bytes() for name in ('SDATA.SAT', 'DATA.SAT')}
    user = (run.path / 'UserMaterial.SAT').read_bytes()
    _, version, count, stride = struct.unpack_from('<4i', user)
    if version != 20190824 or stride != 96 or len(user) != 16 + count * stride:
        raise ValueError('Unsupported native material record layout')
    materials = {}
    for i in range(count):
        offset = 16 + i * stride
        material_id = struct.unpack_from('<i', user, offset + 36)[0]
        materials[material_id] = struct.unpack_from('<dd', user, offset + 56)
    answer = {}
    for edit in document['edits']:
        eid = edit['sourceId']
        element = run.elements[eid]
        offset = edit['offsetBytes']
        values = list(struct.unpack_from('<4f', data['SDATA.SAT'], offset))
        if values != edit['compiledAJIxIy'] or values != list(struct.unpack_from('<4f', data['DATA.SAT'], offset)):
            raise ValueError('Native mechanical property changed after compilation')
        if values != list(struct.unpack('<4f', struct.pack('<4f', *edit['requestedAJIxIy']))):
            raise ValueError('Invalid native property compilation')
        endpoints = np.array(struct.unpack_from('<6f', data['SDATA.SAT'], offset - 96)).reshape(2, 3)
        if element['type'] == 'column':
            endpoints = endpoints[::-1]
        expected = [[run.nodes[n][c] for c in 'xyz'] for n in element['nodes']]
        if not np.allclose(endpoints, expected, atol=1e-6, rtol=0):
            raise ValueError('Native member geometry differs from source identity')
        saved = run.receipt['materialReadbackAfterReopen'][element['material']]
        E, nu = materials[saved['nativeMaterialId']]
        if E != saved['nativeValues'][1] * 1000 or nu != saved['nativeValues'][2]:
            raise ValueError('Native material readback mismatch')
        A, J, strong, weak = values
        answer[eid] = dict(length=float(np.linalg.norm(endpoints[1] - endpoints[0])), E=E,
                           G=E / (2 * (1 + nu)), A=A, J=J,
                           Iy=weak if element['type'] == 'column' else strong,
                           Iz=strong if element['type'] == 'column' else weak)
    if set(answer) != set(run.elements):
        raise ValueError('Incomplete native property bindings')
    return answer


def _descriptor(path, root, kind):
    return {'kind': kind, 'path': str(path.resolve().relative_to(root.resolve())), 'sha256': sha(path)}


def generate(evidence_root, corpus, candidate_path, output):
    evidence_root, corpus, candidate_path, output = map(Path, (evidence_root, corpus, candidate_path, output))
    if output.exists():
        raise ValueError('New precision output directory already exists')
    candidate_hash = sha(candidate_path)
    candidate = read(candidate_path)
    loaded = load_case(corpus / candidate['id'])
    manifest_path = evidence_root / 'pkpm-candidate-evidence-manifest.json'
    manifest_hash = sha(manifest_path)
    if (candidate['sourceHash'] != loaded['sourceHash']
            or candidate['inputHashes'] != loaded['hashes']
            or candidate['frozenEvidenceManifestSha256'] != manifest_hash):
        raise ValueError('Frozen candidate/source/manifest hash mismatch')
    if candidate.get('analysisConvention', {}).get('id') != 'commercial-linear-static-v2':
        raise ValueError('The published finite-shear convention is required')
    if 'precision' in candidate['nativeArtifacts']:
        raise ValueError('Candidate already carries a precision certificate')
    certificate = {'schemaVersion': 1, 'engine': 'PKPM', 'caseId': candidate['id'],
                   'sourceHash': loaded['sourceHash'], 'oldCandidateSha256': candidate_hash,
                   'canonicalDecomposition': CANONICAL, 'sources': [],
                   'limits': LIMITS, 'quantities': []}
    sources = certificate['sources']
    for path in [Path(__file__), Path(__file__).with_name('pkpm_candidates.py'),
                 Path(__file__).with_name('pkpm_results.py'),
                 Path(__file__).parents[1] / 'reference_solver.py',
                 Path(__file__).parents[1] / 'reference_io.py']:
        sources.append(_descriptor(path, REPOSITORY, 'repository-code'))
    sources.append(_descriptor(manifest_path, evidence_root, 'native-evidence-manifest'))
    sources.append({'kind': 'old-candidate', 'path': candidate_path.name, 'sha256': candidate_hash})
    for name in loaded['hashes']:
        sources.append(_descriptor(corpus / candidate['id'] / name, corpus, 'authored-source'))
    entries = read(manifest_path)['runs']
    result = copy.deepcopy(candidate)
    runs = []
    if len(result['states']) != len(loaded['states']):
        raise ValueError('Candidate state count mismatch')
    for state, source_state in zip(result['states'], loaded['states']):
        matches = [entry for entry in entries if entry['caseId'] == candidate['id'] and entry['state'] == state['state']]
        if len(matches) != 1 or state['state'] != source_state['state']:
            raise ValueError('Ambiguous candidate native run')
        entry = matches[0]
        if (entry['sourceHash'] != loaded['sourceHash']
                or entry['sourceModelSha256'] != loaded['hashes'][source_state['modelPath']]
                or state['nativeRun'] != entry['nativeIdentity']):
            raise ValueError('Candidate native identity mismatch')
        run = Run(evidence_root, entry, source_state['model'])
        runs.append(run)
        if run.packet['selection']['kind'] != 'case':
            raise ValueError('Precision policy currently supports one native case per run')
        for record in entry['artifacts'].values():
            sources.append({'kind': 'native-raw', **record})
        for record in entry['stages']:
            sources.append({'kind': 'native-stage', 'path': record['path'], 'sha256': record['sha256']})
        displacement, mapping = native_displacements(run)
        properties = native_properties(run)
        requests = {q['id']: q for q in source_state['quantities']}
        if (len(state['quantities']) != len(requests)
                or {q['id'] for q in state['quantities']} != set(requests)):
            raise ValueError('Candidate request identity/count mismatch')
        for q in state['quantities']:
            if 'engineeringPrecision' in q or q['id'] not in requests:
                raise ValueError('Candidate has unexpected quantity metadata')
            request = requests[q['id']]
            if any(q.get(key) != value for key, value in request.items()):
                raise ValueError('Candidate request metadata mismatch')
            if request['location']['kind'] != 'member':
                continue
            if q != run.quantity(request):
                raise ValueError('Candidate differs from raw native member extraction')
            _, factors = run.factors(q['selection'])
            if factors != {'DL': 1.0}:
                raise ValueError('Only a single native DL record is in scope')
            eid = q['location']['id']
            member = run.physical[eid]
            end = q['rawTrace']['end']
            basis = np.array(member['basisGlobal'])
            d = np.concatenate([displacement[nid] for nid in member['nodes']])
            local = np.kron(np.eye(4), basis) @ d
            loads = []
            for load in run.packet['loads']:
                if load['target'] != eid:
                    continue
                if load['type'] != 'distributed':
                    raise ValueError('Unsupported member load in precision policy')
                loads.append((basis @ np.array(load['vector'])).tolist())
            terms, labels = endpoint_terms(q['component'], end, local.tolist(), loads, **properties[eid])
            terms = [convert_value(value, quantity_unit(q['component']), q['unit']) for value in terms]
            metadata = precision_metadata(terms, q['unit'])
            q['engineeringPrecision'] = metadata
            certificate['quantities'].append({
                'state': state['state'], **{key: copy.deepcopy(q[key]) for key in ('id', 'selection', 'component', 'location', 'unit')},
                'precision': copy.deepcopy(metadata),
                'recovery': {'nativeRun': run.identity, 'termLabels': labels,
                             'nativeMechanicalParameters': properties[eid],
                             'localDisplacements': local.tolist(), 'localUniformLoads': loads,
                             'nodeMappings': [m for m in mapping if m['node'] in member['nodes']]}})
    if not certificate['quantities']:
        raise ValueError('No eligible member endpoint requests')
    if sha(candidate_path) != candidate_hash or sha(manifest_path) != manifest_hash:
        raise ValueError('Candidate/evidence manifest changed during extraction')
    if load_case(corpus / candidate['id'])['sourceHash'] != loaded['sourceHash']:
        raise ValueError('Authored input changed during extraction')
    for run in runs:
        run.verify()
    # All guards complete before creating the new candidate directory.
    certpath = output / 'precision/certificate.json'
    write_json_exclusive(certpath, certificate)
    certificate_hash = sha(certpath)
    for state in result['states']:
        for q in state['quantities']:
            if 'engineeringPrecision' in q:
                q['engineeringPrecision']['certificateSha256'] = certificate_hash
    result['nativeArtifacts']['precision'] = {'certificate.json': {
        'path': 'precision/certificate.json', 'sha256': certificate_hash}}
    result.update(accepted=False, nativeVerified=False, notCommercialScoringTruth=True,
                  sameEngineTruthStatus='pending', nativeIndependentReview='pending',
                  status='candidate-only; engineering precision policy pending review')
    write_json_exclusive(output / 'native-reference.json', result)
    receipt = {'caseId': candidate['id'], 'status': 'candidate-only; pending independent review',
               'precisionQuantityCount': len(certificate['quantities']),
               'certificateSha256': certificate_hash,
               'candidateSha256': sha(output / 'native-reference.json'),
               'oldCandidateSha256': candidate_hash,
               'nativeArithmeticBound': False, 'acceptanceRegionChanges': True}
    write_json_exclusive(output / 'precision-generation-receipt.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', required=True, type=Path)
    parser.add_argument('--corpus', type=Path, default=REPOSITORY / 'corpora/research-300/cases')
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.evidence_root, args.corpus, args.candidate, args.output), indent=2))


if __name__ == '__main__':
    main()
