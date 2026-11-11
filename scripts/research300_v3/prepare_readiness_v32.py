"""Prepare static prerequisites and verbatim public input delivery, without runs.

Does not import an evaluator/SUT, call a model, start a solver or run tests.
Missing operator-owned configuration/collector receipts remain unresolved.
"""
import argparse
import os
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
REVIEW = Path(os.environ.get('SCLAW_BENCH_ARCHIVE', ROOT)).expanduser().resolve() / 'docs/implementation/reviews/research300-v3-sclaw-static-scope-20261029'
PUBLISHED = '00ecd812a315a75b7714d5fc030ec3652bfaf869'
LOCAL = '0a17bfdcd1a6cfa827a0aa15c05856fa3bd0e2d1'
HISTORICAL = 'db3c0b1da44fe668a6037a6c2e7f068d14354539'
NATIVE_AUDIT = '4f63d909813f279bf310fa69154a07f9bbccd464'
PROTOCOL = 'verbatim-public-v3.2'
INLINE = ('design-catalog.json', 'engineering-brief.md',
          'primary/section-families.json', 'upper/section-families.json')
HASH = re.compile(r'[a-f0-9]{64}')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(p):
    return json.loads(Path(p).read_bytes())


def write(p, value):
    Path(p).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def relative_file(root, name):
    if not isinstance(name, str) or '\\' in name or any(x in ('', '.', '..') for x in name.split('/')):
        raise ValueError('Unsafe relative artifact path')
    current = root
    for part in Path(name).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Symlink artifacts are not accepted')
    current = current.resolve(strict=True)
    if not current.is_relative_to(root) or not current.is_file():
        raise ValueError('Artifact escaped input root')
    return current


def code_binding():
    """Literal local-require closure, matching code-closure-v32.cjs; no imports."""
    names = ('grade_candidate_v32.cjs', 'evaluate-v32.cjs', 'physical-v32.cjs',
             'audit-metadata-v32.cjs', 'controlled-evidence-v32.cjs',
             'prepare_readiness_v32.py', 'run-configuration-v32.template.json', 'publish_capture_v32.cjs',
             'prepare_native_bundle_v32.py', 'capture_structureclaw_worker_v32.py',
             'CaptureWorkerLauncher.cs', 'Build-CaptureLauncher.ps1')
    pending = [Path(__file__).with_name(n) for n in names]
    seen = {}
    while pending:
        file = pending.pop().resolve(strict=True)
        key = file.relative_to(ROOT).as_posix()
        if key in seen:
            continue
        data = file.read_bytes()
        seen[key] = sha(data)
        if file.suffix not in ('.js', '.cjs'):
            continue
        for dependency in re.findall(r'''require\(\s*['"]([^'"]+)['"]\s*\)''', data.decode()):
            if not dependency.startswith('.'):
                continue
            child = file.parent / dependency
            if not child.exists():
                child = next((Path(str(child) + ext) for ext in ('.cjs', '.js')
                              if Path(str(child) + ext).exists()), child)
            pending.append(child)
    return dict(sorted(seen.items()))


def sealed_json(control_root, descriptor):
    if control_root is None or not isinstance(descriptor, dict) or not HASH.fullmatch(str(descriptor.get('sha256', ''))):
        return None
    data = relative_file(control_root, descriptor.get('path')).read_bytes()
    if sha(data) != descriptor['sha256']:
        raise ValueError('Operator receipt digest differs')
    return json.loads(data)


def public_delivery(edition, manifest):
    seals = {x['path']: x['sha256'] for x in manifest['files']}
    rows = []
    for case in manifest['cases']:
        history = []
        for turn in case['turns']:
            base = turn['public']
            files = []
            for key in sorted(k for k in seals if k.startswith(base + '/')):
                path = relative_file(edition, key)
                if sha(path.read_bytes()) != seals[key]:
                    raise ValueError('Frozen public input changed: ' + key)
                files.append({'editionPath': key, 'packetPath': key[len(base) + 1:], 'sha256': seals[key]})
            task = read(edition / base / 'task.json')
            present = {f['packetPath'] for f in files}
            if 'task.json' not in present or set(task['attachments']) - present:
                raise ValueError('Missing issued public attachment: ' + case['id'] + '/' + turn['id'])
            inline = list(INLINE) if case['level'] == 'L4' and turn['id'] == 't1' else []
            if set(inline) - present:
                raise ValueError('Project source rule files are incomplete')
            rows.append({'caseId': case['id'], 'turnId': turn['id'], 'public': base,
                         'historyTurnIds': list(history), 'files': files, 'inlineVerbatim': inline,
                         'rawImages': [f['packetPath'] for f in files if f['packetPath'].endswith('.png')]})
            history.append(turn['id'])
    return {'kind': 'research300-v3-public-delivery', 'protocol': PROTOCOL,
            'editionManifestSha256': sha((edition / 'manifest.json').read_bytes()),
            'controllerOnly': True, 'containsPrivateFiles': False, 'turns': rows}


def packet(edition, delivery, case_id, turn_id, output):
    """Materialize only already-issued public files; never releases this index."""
    target = next(r for r in delivery['turns'] if r['caseId'] == case_id and r['turnId'] == turn_id)
    allowed = set(target['historyTurnIds'] + [turn_id])
    output = Path(output).resolve()
    # A caller may not write a candidate packet inside protected originals.
    if output.is_relative_to(edition) or output == ROOT or output.is_relative_to(REVIEW):
        raise ValueError('Packet must be outside original edition/review')
    output.mkdir(parents=True, exist_ok=False)
    for row in delivery['turns']:
        if row['caseId'] != case_id or row['turnId'] not in allowed:
            continue
        for file in row['files']:
            source = relative_file(edition, file['editionPath'])
            if sha(source.read_bytes()) != file['sha256']:
                raise ValueError('Public input changed during packet preparation')
            dest = output / row['turnId'] / file['packetPath']
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        message = f"本题 {case_id}，当前签发 {row['turnId']}。读取 task.json 及全部原始附件，保留本题已签发会话与资料。\n"
        message += '仅使用实际工具结果；按原 tool-contract.md 交付结构化答案。真实 Sclaw runId 可使用 runIds、runIdsByScenario、runIdsByModel，与对应 jobIds 字段二选一；不得改写数值或伪造作业。\n'
        if row['inlineVerbatim']:
            message += '以下为同一批原始公开附件的逐字文本，作为本轮真实用户输入提供；规则、数值及优先级遵循原题。\n'
        for name in row['inlineVerbatim']:
            message += '\n--- 原始附件：' + name + ' ---\n'
            message += (edition / row['public'] / name).read_text()
            message += '\n--- 附件结束 ---\n'
        (output / row['turnId'] / 'user-message.txt').write_text(message)
    return {'caseId': case_id, 'turnId': turn_id, 'issuedTurnIds': sorted(allowed),
            'protocol': PROTOCOL, 'packetDirectory': str(output), 'candidateInvocations': 0}


def prepare(edition, configuration, control_root=None):
    manifest = read(edition / 'manifest.json')
    manifest_sha = sha((edition / 'manifest.json').read_bytes())
    summary = read(REVIEW / 'summary.json')
    assessments = read(REVIEW / 'case-assessments.json')['cases']
    if manifest_sha != summary['manifestSha256'] or configuration.get('editionManifestSha256') != manifest_sha:
        raise ValueError('Edition is not the individually reviewed frozen version')
    if configuration.get('kind') != 'research300-v3-run-configuration':
        raise ValueError('Explicit run configuration required')
    if {c['id'] for c in manifest['cases']} != {c['caseId'] for c in assessments}:
        raise ValueError('Static review case coverage differs')
    commit = configuration['candidate']['sutCommit']
    binding = code_binding()
    # Receipts bind the execution specification; receipt descriptors themselves
    # are excluded to avoid a self-referential configuration hash.
    spec = {k: configuration.get(k) for k in ('candidate', 'inputDelivery', 'tools', 'budget', 'vision', 'engines')}
    spec_sha = sha(json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
    receipts = configuration.get('receipts', {})
    def receipt(name, kind):
        obj = sealed_json(control_root, receipts.get(name))
        return obj if (obj and obj.get('kind') == kind and obj.get('sutCommit') == commit
                       and obj.get('editionManifestSha256') == manifest_sha
                       and obj.get('executionSpecificationSha256') == spec_sha) else None

    reasons = []
    if commit not in (PUBLISHED, LOCAL, HISTORICAL, NATIVE_AUDIT):
        reasons.append('SUT_PROFILE_NOT_IN_STATIC_REVIEW')
    if not configuration['candidate'].get('modelId'):
        reasons.append('CANDIDATE_MODEL_NOT_PINNED')
    if configuration.get('inputDelivery') != {'protocol': PROTOCOL, 'realUserText': True,
                                             'preserveCaseHistory': True, 'rawImageAttachments': True}:
        reasons.append('PUBLIC_INPUT_PROTOCOL_UNRESOLVED')
    tools = configuration.get('tools', {})
    limit = tools.get('maxToolCallsPerTurn')
    if type(limit) is not int or not 1 <= limit <= 200:
        reasons.append('TOOL_LIMIT_OUTSIDE_SCLAW_SOURCE_CONTRACT')
    budget = configuration.get('budget', {})
    if any(type(budget.get(k)) is not int or budget[k] <= 0 for k in ('nativeJobsPerTurn', 'wallTimeSecondsPerTurn')):
        reasons.append('SHARED_RUN_BUDGET_NOT_DECLARED')
    if budget.get('countNestedNativeCalls') is not True:
        reasons.append('NESTED_NATIVE_COST_ACCOUNTING_UNRESOLVED')
    actual = receipt('runtimeConfiguration', 'research300-runtime-configuration')
    if not actual or actual.get('configurationApplied') is not True:
        reasons.append('APPLIED_RUNTIME_CONFIGURATION_NOT_ATTESTED')
    if not actual or actual.get('candidateIsolationVerified') is not True or actual.get('controlFilesInaccessible') is not True:
        reasons.append('CANDIDATE_CONTROL_BOUNDARY_NOT_ATTESTED')
    if tools.get('programming', {}).get('policy') == 'sclaw-shell' and (not actual or actual.get('shellIsolationVerified') is not True):
        reasons.append('PROGRAMMING_CONTROL_BOUNDARY_NOT_ATTESTED')
    collector = receipt('collectorQualification', 'research300-v3-collector-qualification')
    if (not collector or collector.get('revision') != 'v3.2' or collector.get('allPassed') is not True
            or collector.get('evaluationCode') != binding):
        reasons.append('CONTROLLED_COLLECTOR_NOT_QUALIFIED')
    qualification = sealed_json(control_root, receipts.get('policyQualification'))
    families = ('audit-metadata-equivalence', 'unknown-audit-fields', 'physical-input-strictness',
                'controlled-capture-identity', 'native-execution-bindings', 'failure-attribution', 'verbatim-public-delivery')
    qualified = (qualification and qualification.get('kind') == 'research300-v3-policy-qualification'
                 and qualification.get('revision') == 'v3.2' and qualification.get('allPassed') is True
                 and qualification.get('evaluationCode') == binding and qualification.get('manifestSha256') == manifest_sha
                 and qualification.get('inputProtocol') == PROTOCOL
                 and qualification.get('positiveTurns') == 560 and qualification.get('positivePassed') == 560
                 and type(qualification.get('controls')) is int and qualification['controls'] >= 6591
                 and qualification.get('controlsPassed') == qualification['controls']
                 and all(type(qualification.get('controlFamilies', {}).get(k, {}).get('executed')) is int
                         and qualification['controlFamilies'][k]['executed'] > 0
                         and qualification['controlFamilies'][k].get('failed') == 0 for k in families))
    if not qualified:
        reasons.append('SCORING_REVISION_NOT_RUNTIME_QUALIFIED')
    rows = []
    by_id = {c['caseId']: c for c in assessments}
    for case in manifest['cases']:
        item = by_id[case['id']]
        codes = list(reasons)
        engine = configuration.get('engines', {}).get(case['engine'], {})
        available = receipt(case['engine'], 'research300-engine-availability')
        if not engine.get('version') or not available or available.get('engine') != case['engine'] or available.get('available') is not True or available.get('version') != engine.get('version'):
            codes.append('DESIGNATED_ENGINE_AVAILABILITY_NOT_ATTESTED')
        if case['engine'] == 'PKPM' and commit == PUBLISHED:
            if str(engine.get('version', engine.get('recordedInstall', ''))).startswith('2027') or engine.get('recordedInstall') == '2027R1.0.1' and not engine.get('version'):
                codes.append('PUBLISHED_PKPM_INCOMPATIBLE_WITH_RECORDED_2027_INSTALL')
            for issue in ('PKPM-DESCRIPTIVE-GRADE', 'PKPM-GENERAL-ALIAS'):
                if issue in item['issueIds']:
                    codes.append(issue)
        if case['engine'] == 'PKPM' and (not collector or 'PKPM' not in collector.get('sectionInputBoundaryEngines', [])):
            # Both inspected source versions have a narrower PKPM section-extra
            # contract than the general agent evidence boundary. A comparison
            # normalization cannot establish native acceptance of that input.
            codes.append('PKPM_AGENT_SECTION_EVIDENCE_NATIVE_CONTRACT_UNQUALIFIED')
        if case['family'] == 'MM' and not configuration.get('vision', {}).get('modelId'):
            codes.append('VISION_MODEL_NOT_PINNED')
        if case['level'] == 'L4':
            programming = tools.get('programming', {})
            if programming.get('policy') not in ('disabled', 'sclaw-shell'):
                codes.append('PROJECT_COMPUTATION_POLICY_NOT_DECLARED')
            if programming.get('policy') == 'sclaw-shell' and (programming.get('allowShell') is not True or not programming.get('commands')):
                codes.append('PROJECT_SHELL_CONFIGURATION_INCOMPLETE')
            if programming.get('policy') == 'disabled' and programming.get('allowShell') is not False:
                codes.append('PROJECT_PROGRAMMING_POLICY_CONFLICT')
        status = 'blocked' if any(x in codes for x in ('PKPM-DESCRIPTIVE-GRADE', 'PUBLISHED_PKPM_INCOMPATIBLE_WITH_RECORDED_2027_INSTALL')) else 'conditional' if codes else 'ready'
        rows.append({'caseId': case['id'], 'family': case['family'], 'level': case['level'],
                     'engine': case['engine'], 'turns': len(case['turns']), 'status': status,
                     'reasonCodes': sorted(set(codes)), 'staticAnswerPathPresent': True})
    return {'kind': 'research300-v3-static-readiness', 'schemaVersion': 1,
            'editionManifestSha256': manifest_sha, 'sutCommit': commit, 'inputProtocol': PROTOCOL,
            'executionSpecification': spec, 'executionSpecificationSha256': spec_sha,
            'evaluationCode': binding, 'configurationReceipts': receipts,
            'runtimeQualification': receipts.get('policyQualification'),
            'formalExperimentReady': all(r['status'] == 'ready' for r in rows),
            'cases': rows, 'statusCounts': dict(Counter(r['status'] for r in rows)),
            'reasonCounts': dict(Counter(code for r in rows for code in r['reasonCodes'])),
            'candidateInvocations': 0, 'nativeSolverInvocations': 0, 'testSuitesInvoked': 0,
            'reviewSources': {name: sha((REVIEW / name).read_bytes()) for name in ('summary.json', 'case-assessments.json', 'fork-binding.json')},
            'runtimeCapabilityVerifiedByThisPreparation': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edition', type=Path, required=True)
    parser.add_argument('--configuration', type=Path, required=True)
    parser.add_argument('--control-root', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--packet-case')
    parser.add_argument('--packet-turn')
    parser.add_argument('--packet-output', type=Path)
    args = parser.parse_args()
    edition = args.edition.resolve(strict=True)
    output = args.output.resolve()
    control = args.control_root.resolve(strict=True) if args.control_root else None
    protected = (edition, REVIEW, *((control,) if control else ()))
    if output == ROOT or any(output.is_relative_to(p) for p in protected):
        parser.error('Preparation output must be new and outside originals/controlled evidence')
    packet_args = (args.packet_case, args.packet_turn, args.packet_output)
    if any(x is not None for x in packet_args) and not all(x is not None for x in packet_args):
        parser.error('Packet selection requires case, turn and a new candidate directory')
    if args.packet_output:
        p = args.packet_output.resolve()
        if output.is_relative_to(p) or p.is_relative_to(output) or any(p.is_relative_to(x) for x in protected):
            parser.error('Candidate packet and controller output/evidence must be separate')
    readiness = prepare(edition, read(args.configuration), control)
    delivery = public_delivery(edition, read(edition / 'manifest.json'))
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'readiness.json', readiness)
    write(output / 'input-delivery.json', delivery)
    if args.packet_output:
        write(output / 'packet-preparation.json', packet(edition, delivery, args.packet_case, args.packet_turn, args.packet_output))
    print(json.dumps({'output': str(output), 'cases': len(readiness['cases']),
                      'turns': len(delivery['turns']), 'statusCounts': readiness['statusCounts'],
                      'formalExperimentReady': readiness['formalExperimentReady'],
                      'readinessSha256': sha((output / 'readiness.json').read_bytes())}))


if __name__ == '__main__':
    main()
