#!/usr/bin/env python3
"""Retain fresh commercial reference executions, separately from candidate calls.

This collector records raw native evidence and never approves a reference.
The caller must independently audit the input, extraction and numerical results.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

from reference_io import load_case
from commercial_reference_inputs import execution_model, published_section_model


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edition-root', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--remote-setup', type=Path, required=True)
    parser.add_argument('--sut', type=Path, required=True)
    parser.add_argument('--native-lock', type=Path, required=True)
    parser.add_argument('--cases')
    parser.add_argument('--published-properties', action='store_true',
                        help='Use exact released input-data.json section numbers, with a bound precision audit')
    args = parser.parse_args()
    root, work, sut = args.edition_root.resolve(), args.work.resolve(), args.sut.resolve()
    work.mkdir(parents=True, exist_ok=True)
    setup = work/'remote-setup.json'
    if setup.exists():
        assert setup.read_bytes() == args.remote_setup.read_bytes(), 'Native runtime changed'
    else:
        shutil.copyfile(args.remote_setup, setup)
    command = Path(__file__).parent/'codex_trial/commercial.py'
    jobs = []
    for folder in sorted((root/'corpora/research-300/cases').iterdir()):
        if args.cases and folder.name not in args.cases.split(','):
            continue
        contract = json.loads((folder/'contract.json').read_text())
        engine = contract['plannedEngine']
        if engine not in ('PKPM', 'YJK'):
            continue
        case = load_case(folder)
        for state in case['states']:
            selections = {(q['selection']['kind'], q['selection']['id']) for q in state['quantities']}
            for kind, identifier in sorted(selections):
                index = work/'executions'/folder.name/f"state-{state['state']}-{kind}-{identifier}.json"
                if index.exists():
                    retained = json.loads(index.read_text())
                    assert retained['sourceHash'] == case['sourceHash'], 'Reference input changed'
                    jobs.append(retained)
                    continue
                job = work/'solver-jobs'/folder.name/uuid.uuid4().hex
                job.mkdir(parents=True)
                selection = {'kind': kind, 'id': identifier}
                parameters = {'loadCaseIds': [identifier]} if kind == 'case' else {'loadCombinationId': identifier}
                authored = state['model']
                if args.published_properties:
                    public_path = folder/'input-data.json'
                    raw_public = public_path.read_bytes()
                    authored = published_section_model(authored, json.loads(raw_public))
                    write(job/'published-input.json', json.loads(raw_public))
                    write(job/'input-precision-binding.json', {
                        'policy': 'exact-published-section-properties-v1',
                        'source': public_path.name,
                        'sourceSha256': hashlib.sha256(raw_public).hexdigest(),
                        'maximumDisplayRelativeError': 5e-8,
                        'numericalToleranceChanged': False,
                        'candidateAnswersUsed': False})
                model = execution_model(authored, engine)
                write(job/'authored-model.json', state['model'])
                write(job/'request.json', {'model': model, 'selection': selection})
                write(job/'model.json', model)
                proof = subprocess.run(['node', '-e', '''const fs=require('fs');const {comparePhysicalModels}=require('./lib/physical-model-fidelity.cjs');
const a=JSON.parse(fs.readFileSync(process.argv[1])),b=JSON.parse(fs.readFileSync(process.argv[2]));
const r=comparePhysicalModels(a,b,{coordinate:1e-8,property:1e-6,load:1e-6,explicitElasticProperties:true,staticTheory:'Timoshenko'});
process.stdout.write(JSON.stringify(r));process.exitCode=r.pass?0:1;''', str(job/'model.json'), str(job/'authored-model.json')],
                    cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, check=True)
                write(job/'input-equivalence.json', json.loads(proof.stdout))
                write(job/'worker-request.json', {'action': 'analyze', 'input': {
                    'engineId': engine.lower(), 'type': 'static', 'model': model, 'parameters': parameters}})
                binding = {'caseId': folder.name, 'engine': engine, 'state': state['state'],
                           'sourceHash': case['sourceHash'], 'executionRole': 'reference-verification'}
                write(job/'reference-binding.json', binding)
                argv = [sys.executable, str(command), '--job', str(job), '--engine', engine,
                        '--sut', str(sut), '--reference-binding', str(job/'reference-binding.json'),
                        '--native-lock', str(args.native_lock.resolve())]
                started = datetime.datetime.now(datetime.timezone.utc).isoformat()
                write(job/'dispatch.json', {'command': argv, 'startedAt': started,
                                           'modelSha256': hashlib.sha256((folder/state['modelPath']).read_bytes()).hexdigest()
                                           if 'modelPath' in state else None,
                                           'actualModelCall': False, **binding})
                with (job/'execution.log').open('w') as output:
                    result = subprocess.run(argv, stdout=output, stderr=subprocess.STDOUT, timeout=1800)
                receipt = {**binding, 'selection': selection, 'job': str(job), 'exitCode': result.returncode,
                           'startedAt': started, 'completedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                           'nativeStateCaptured': (job/'state.json').exists()}
                write(index, receipt)
                jobs.append(receipt)
                print(json.dumps(receipt), flush=True)
    report = {'schemaVersion': 1, 'executionRole': 'reference-verification',
              'referenceQualification': 'pending-independent-audit', 'candidateModelCalls': 0,
              'jobs': jobs, 'passed': sum(r['exitCode'] == 0 and r['nativeStateCaptured'] for r in jobs)}
    write(work/'execution-summary.json', report)
    return 0 if report['passed'] == len(jobs) else 1


if __name__ == '__main__':
    raise SystemExit(main())
