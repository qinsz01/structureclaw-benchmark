"""Offline, proof-bound derivation of three reviewed free-support My quantities.

No solver, threshold, SDK mutation, tolerance change or scoring qualification is
performed. A complete new two-case candidate tree is published atomically.
"""
import argparse
import copy
import ctypes
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference_io import (evaluate_derived, finite_number, load_case,
                          read_bytes_safe, read_json_safe, selection_factors,
                          write_json_exclusive)

RULE = 'pkpm-free-rotation-reaction-v1'
VALUE_KIND = 'derived-from-native-free-boundary'
FLAGS = ('zeroRotationStiffness', 'noCoupling', 'noAdditionalConstraint',
         'freeDofsRetained', 'noSupportNodalLoad')
QID = 'case-D--n0-0-0--My'
SCOPE = {('INT-079', 1, QID), ('INT-089', 1, QID), ('INT-089', 2, QID)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact(a, b):
    """Preserve signed zero and boolean distinctions in frozen JSON metadata."""
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def local_path(path):
    path = Path(path).absolute()
    require('..' not in path.parts, 'Parent traversal is not allowed')
    for part in [*reversed(path.parents), path]:
        require(not part.is_symlink(), f'Symlink is not allowed: {part}')
    return path


class BoundFiles:
    def __init__(self, root):
        self.root = local_path(root)
        require(self.root.is_dir(), 'Evidence root must be an existing directory')
        self.bound = {}
        self.raw = {}

    def bind(self, descriptor):
        require(isinstance(descriptor, dict), 'Missing evidence descriptor')
        path, digest = descriptor.get('path'), descriptor.get('sha256')
        require(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest), 'Missing or invalid SHA-256')
        # read_bytes_safe rejects absolute paths, traversal, symlinks and nonfiles.
        raw = read_bytes_safe(self.root, path)
        require(hashlib.sha256(raw).hexdigest() == digest, f'Evidence SHA mismatch: {path}')
        require(path not in self.bound or self.bound[path] == digest, f'Conflicting SHA binding: {path}')
        self.bound[path], self.raw[path] = digest, raw
        return raw

    def json(self, descriptor):
        raw = self.bind(descriptor)
        # The strict shared reader rejects duplicate keys and nonfinite values.
        document, digest = read_json_safe(self.root, descriptor['path'])
        require(digest == descriptor['sha256'] and raw == self.raw[descriptor['path']], 'JSON SHA changed while reading')
        return document

    def sources(self, records):
        require(isinstance(records, list), 'Evidence sources must be an array')
        for descriptor in records:
            self.bind(descriptor)

    def verify(self):
        for path, digest in self.bound.items():
            require(hashlib.sha256(read_bytes_safe(self.root, path)).hexdigest() == digest,
                    f'Evidence SHA changed before publication: {path}')


def unique(records, key, label):
    require(isinstance(records, list), f'Missing {label} array')
    result = {}
    for row in records:
        require(isinstance(row, dict), f'Invalid {label} entry')
        identity = key(row)
        require(identity not in result, f'Duplicate {label} identity')
        result[identity] = row
    return result


def zeros(values, count, label):
    require(isinstance(values, list) and len(values) == count, f'Missing {label}')
    require(all(finite_number(value) == 0 for value in values), f'Nonzero {label}')


def verify_native_proof(row, files):
    require(all(row.get(flag) is True and row.get('facts', {}).get(flag) is True for flag in FLAGS),
            'Incomplete boolean free-boundary proof')
    proof = row.get('proof', {})
    blocks = unique(proof.get('executedConstraintBlocks'), lambda b: b.get('artifact'), 'constraint block')
    expected = {'ConstraintNode.SAT': (88, [1e14]*3+[0.]*3),
                'ConstraintNodeSK.SAT': (16, [1e14, 0., 1e14, 0., 0., 1e14]+[0.]*6)}
    require(set(blocks) == set(expected), 'Both executed native support matrices are required')
    for name, (offset, values) in expected.items():
        block = blocks[name]
        require(block.get('postsolveEqualsCompiled') is True and block.get('offsetBytes') == offset,
                'Native matrix offset or compiled/executed equality is unproved')
        actual = block.get('executedValues')
        require(isinstance(actual, list) and len(actual) == len(values) and
                all(finite_number(a) == b for a, b in zip(actual, values)),
                'Native stiffness is nonzero or outside the reviewed matrix scope')
        matches = [d for d in row['sources'] if Path(d['path']).name == name and
                   Path(d['path']).parent.name == row['nativeRun']]
        require(len(matches) == 1, 'Executed support matrix lacks a unique run-bound source')
        descriptor = matches[0]
        compiled = [d for d in row['sources'] if d['path'] == descriptor['path']+'.compiled-pin']
        require(len(compiled) == 1, 'Compiled native support matrix is missing')
        raw = files.raw[descriptor['path']]
        require(raw == files.raw[compiled[0]['path']], 'Compiled and executed support matrices differ')
        require(len(raw) >= offset+8*len(values), 'Truncated native support matrix')
        require(list(struct.unpack_from('<%dd' % len(values), raw, offset)) == values,
                'Executed native support matrix disagrees with reviewed stiffness')
    require(blocks['ConstraintNode.SAT'].get('definitionId') == blocks['ConstraintNodeSK.SAT'].get('definitionId') and
            isinstance(blocks['ConstraintNode.SAT'].get('definitionId'), int) and
            blocks['ConstraintNode.SAT']['definitionId'] > 0, 'Support definition identity is missing')
    require(blocks['ConstraintNode.SAT'].get('sourceMemberId') == blocks['ConstraintNodeSK.SAT'].get('sourceMemberId'),
            'Support matrices bind different members')
    count = proof.get('retainedSixDofNodes')
    require(type(count) is int and count > 0 and proof.get('nativeTotalAndExitDOFs') == [6*count]*2,
            'Retained free DOFs are not established')
    dofs = proof.get('rawSixDOF')
    require(isinstance(dofs, list) and len(dofs) == 6, 'Native six-DOF observation is missing')
    for value in dofs:
        finite_number(value)
    zeros(proof.get('externalNodalLoadAtSupport'), 6, 'reviewed external support load')


def verify_source_and_quantity(row, state, quantity, case_entry, loaded):
    require(row.get('component') == 'My' and row.get('node') == 'n0-0-0' and
            row.get('selection') == {'kind': 'case', 'id': 'D'} and row.get('unit') == 'kN.m',
            'Unreviewed component, node, selection or unit')
    require(finite_number(row.get('derivedValue')) == 0, 'Derived value must be zero by the boundary rule')
    require(row.get('sourceHash') == loaded['sourceHash'] and
            row.get('model') == state['modelPath'] and row.get('modelSha256') == loaded['hashes'][state['modelPath']] and
            row.get('requestSha256') == loaded['hashes']['reference-requests.json'] and
            row.get('oldCandidateSha256') == case_entry['candidate']['sha256'], 'Source/model/request/candidate SHA mismatch')
    require(quantity.get('component') == 'My' and quantity.get('location') == {'kind': 'node', 'id': row['node']} and
            exact(quantity.get('selection'), row['selection']) and quantity.get('unit') == row['unit'],
            'Authorized quantity identity differs from frozen request')
    require(exact(quantity.get('value'), row.get('oldValue')) and
            isinstance(row.get('oldRawTrace'), dict) and bool(row['oldRawTrace']) and
            exact(quantity.get('rawTrace'), row['oldRawTrace']), 'Old value/rawTrace is missing or differs')
    finite_number(quantity['value'])
    trace = quantity['rawTrace']
    require(trace.get('origin') == 'raw-member-end-equilibrium' and
            trace.get('nativeRun') == row.get('nativeRun') and
            trace.get('sourceModelSha256') == row['modelSha256'] and
            trace.get('sourceSelection') == row['selection'], 'Old trace source/selection/native run mismatch')
    model = state['model']
    nodes = unique(model.get('nodes'), lambda n: n.get('id'), 'source node')
    require(row['node'] in nodes, 'Source support node is missing')
    restraints = nodes[row['node']].get('restraints')
    require(isinstance(restraints, list) and len(restraints) == 6 and
            all(type(value) is bool for value in restraints) and restraints == [True]*3+[False]*3,
            'Source rotations are not explicitly free in the reviewed support scope')
    require(exact(trace.get('sourceRestraints'), restraints), 'Native trace source restraints mismatch')
    factors = selection_factors(model, row['selection'])
    require(trace.get('sourceFactors') == factors, 'Source load factors differ')
    for case in model['load_cases']:
        if not factors.get(case['id'], 0):
            continue
        for load in case['loads']:
            if load.get('type') == 'nodal' and load.get('node') == row['node']:
                zeros(load.get('values'), 6, 'source support nodal load')
    zeros(trace.get('externalNodalLoadAtSupport'), 6, 'raw external support load')
    require(trace.get('globalReactionComponents') == ['Fx','Fy','Fz','Mx','My','Mz'] and
            isinstance(trace.get('globalReaction'), list) and len(trace['globalReaction']) == 6 and
            exact(trace['globalReaction'][4], row['oldValue']) and
            exact(row['proof'].get('nativeMemberEndResidual'), row['oldValue']),
            'Native member-end residual differs from archived My')
    member = row['proof']['executedConstraintBlocks'][0]['sourceMemberId']
    elements = [e for e in model['elements'] if e['id'] == member and row['node'] in e['nodes']]
    require(len(elements) == 1, 'Native support definition is not bound to an incident source member')


def publish_no_replace(temporary, output):
    """Publish all files together; never replace a pre-existing destination.

    NFS may reject RENAME_NOREPLACE. There we first reserve the *empty* output
    directory with exclusive mkdir, then atomically rename onto our reservation.
    An observer can briefly see an empty directory, never a partly written batch.
    Failure removes that reservation only while its inode still belongs to us.
    """
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is not None:
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
    parent = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if rename is not None:
            if rename(parent, os.fsencode(temporary.name), parent, os.fsencode(output.name), 1) == 0:
                return
            error = ctypes.get_errno()
            if error not in (errno.EINVAL, errno.ENOSYS, errno.EOPNOTSUPP):
                raise OSError(error, os.strerror(error), str(output))
        os.mkdir(output.name, mode=0o700, dir_fd=parent)
        owned = os.stat(output.name, dir_fd=parent, follow_symlinks=False)
        try:
            os.rename(temporary.name, output.name, src_dir_fd=parent, dst_dir_fd=parent)
        except BaseException:
            try:
                current = os.stat(output.name, dir_fd=parent, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
                    os.rmdir(output.name, dir_fd=parent)
            except FileNotFoundError:
                pass
            raise
    finally:
        os.close(parent)


def repair_candidates(review, evidence_root, corpus, output):
    files = BoundFiles(evidence_root)
    review, corpus, output = map(local_path, (review, corpus, output))
    require(corpus.is_dir(), 'Corpus must exist')
    require(not output.exists() and output.parent.is_dir(), 'Output must be new with an existing parent')
    require(not output.is_relative_to(corpus), 'Output cannot be inside the authored corpus')
    review_relative = review.relative_to(files.root).as_posix()
    document, review_sha = read_json_safe(files.root, review_relative)
    review_descriptor = {'path': review_relative, 'sha256': review_sha}
    files.bind(review_descriptor)
    require(document.get('schemaVersion') == 1 and document.get('ruleVersion') == RULE and
            document.get('engine') == 'PKPM' and document.get('status') == 'qualified-boundary-derivation' and
            document.get('valueKind') == VALUE_KIND and isinstance(document.get('reviewer'), str) and
            bool(document['reviewer'].strip()), 'Unqualified or unsupported boundary review')
    files.sources(document.get('sources'))
    rows = unique(document.get('quantities'), lambda r: (r.get('caseId'), r.get('state'), r.get('quantityId')), 'repair')
    require(set(rows) == SCOPE, 'Review must authorize exactly the three bounded requests')
    cases = unique(document.get('cases'), lambda r: r.get('id'), 'case')
    require(set(cases) == {'INT-079', 'INT-089'}, 'Review must bind both complete cases')
    for row in rows.values():
        files.sources(row.get('sources'))
        verify_native_proof(row, files)
    payloads, loaded_cases, summaries = {}, {}, []
    for case_id, entry in cases.items():
        case_dir = local_path(corpus/case_id)
        loaded = load_case(case_dir)
        loaded_cases[case_id] = loaded
        for source in loaded['sourceManifest']['files']:
            path = (case_dir/source['path']).relative_to(files.root).as_posix()
            files.bind({'path': path, 'sha256': source['sha256']})
        original = files.json(entry.get('candidate'))
        qualification = files.json(entry.get('qualification'))
        require(qualification.get('engine') == 'PKPM' and isinstance(qualification.get('reviewer'), str) and
                bool(qualification['reviewer'].strip()), 'Original named PKPM qualification is missing')
        qualified = [q for q in qualification.get('cases', []) if q.get('id') == case_id]
        require(len(qualified) == 1 and qualified[0].get('status') == 'qualified' and
                qualified[0].get('sourceHash') == loaded['sourceHash'] and
                qualified[0].get('candidateSha256') == entry['candidate']['sha256'],
                'Original qualification source/candidate SHA mismatch')
        require(original.get('id') == case_id and original.get('modelId') == loaded['contract']['modelId'] and
                entry.get('sourceHash') == loaded['sourceHash'] == original.get('sourceHash') and
                original.get('inputHashes') == loaded['hashes'] and original.get('sourceManifest') == loaded['sourceManifest'] and
                original.get('analysisConvention') == loaded['contract'].get('analysisConvention'),
                'Candidate source/model/convention SHA binding differs from authored inputs')
        candidate = copy.deepcopy(original)
        candidate.update(sameEngineTruthStatus='pending', nativeIndependentReview='pending',
                         status='candidate-only; free-boundary derivation requires independent review',
                         notCommercialScoringTruth=True, accepted=False, nativeVerified=False)
        states = unique(candidate.get('states'), lambda s: s.get('state'), 'candidate state')
        require(set(states) == {s['state'] for s in loaded['states']}, 'Candidate states are incomplete')
        authorized = {(r['state'], r['quantityId']) for r in rows.values() if r['caseId'] == case_id}
        require(isinstance(entry.get('quantities'), list) and len(entry['quantities']) == len(authorized) and
                {(q.get('state'), q.get('quantityId')) for q in entry['quantities']} == authorized,
                'Case authorization differs from review quantities')
        for source_state in loaded['states']:
            state = states[source_state['state']]
            require(state.get('model') == source_state['modelPath'] and
                    state.get('originalModelSha256') == loaded['hashes'][source_state['modelPath']], 'Candidate model SHA mismatch')
            quantities = state.get('quantities')
            require(isinstance(quantities, list) and len(quantities) == len(source_state['quantities']), 'Candidate request coverage differs')
            for q, request in zip(quantities, source_state['quantities']):
                require(exact({k: v for k, v in q.items() if k not in ('value','rawTrace','quantityStatus')}, request),
                        'Frozen request identity, unit or tolerance differs')
                finite_number(q.get('value'))
            require(exact(state.get('derived'), evaluate_derived(quantities, source_state['derived'])),
                    'Original derived values differ from frozen definitions')
            for q in quantities:
                row = rows.get((case_id, state['state'], q['id']))
                if row is None:
                    continue
                require(state.get('nativeRun') == row.get('nativeRun'), 'Candidate native run differs from review')
                verify_source_and_quantity(row, source_state, q, entry, loaded)
                old = {'value': q['value'], 'rawTrace': copy.deepcopy(q['rawTrace'])}
                q.update(value=0.0, quantityStatus=VALUE_KIND, rawTrace={
                    'origin': VALUE_KIND, 'ruleVersion': RULE, 'review': copy.deepcopy(review_descriptor),
                    'reviewer': document['reviewer'], 'nativeRun': row['nativeRun'],
                    'sourceModelSha256': row['modelSha256'], 'sourceSelection': copy.deepcopy(row['selection']),
                    'rawMemberEndEquilibrium': old, 'derivedValue': 0.0, 'unit': q['unit']})
            state['derived'] = evaluate_derived(quantities, source_state['derived'])
        candidate['boundaryRepair'] = {'ruleVersion': RULE, 'review': copy.deepcopy(review_descriptor),
            'oldCandidate': copy.deepcopy(entry['candidate']), 'oldQualification': copy.deepcopy(entry['qualification']),
            'tool': {'path': Path(__file__).name, 'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            'qualificationStatus': 'pending', 'repairedQuantities': len(authorized)}
        payloads[case_id] = candidate
    # Complete validation precedes all output, then repeat every source digest.
    files.verify()
    temporary = output.parent/('.pkpm-boundary-repair-'+uuid.uuid4().hex)
    temporary.mkdir(mode=0o700)
    try:
        for case_id, candidate in payloads.items():
            path = temporary/case_id/'native-reference.json'
            write_json_exclusive(path, candidate)
            summaries.append({'caseId': case_id, 'path': f'{case_id}/native-reference.json',
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'sourceHash': candidate['sourceHash']})
        result = {'schemaVersion': 1, 'status': 'candidate-only; no acceptance', 'ruleVersion': RULE,
                  'review': review_descriptor, 'results': summaries, 'repairedQuantities': len(rows)}
        write_json_exclusive(temporary/'manifest.json', result)
        files.verify()
        for case_id, loaded in loaded_cases.items():
            require(load_case(corpus/case_id)['sourceHash'] == loaded['sourceHash'], 'Authored source SHA changed')
        local_path(output)
        publish_no_replace(temporary, output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('review', 'evidence-root', 'corpus', 'output'):
        parser.add_argument('--'+flag, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(repair_candidates(args.review, args.evidence_root, args.corpus, args.output), indent=2))


if __name__ == '__main__':
    main()
