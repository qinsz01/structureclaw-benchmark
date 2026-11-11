#!/usr/bin/env python3
"""Run independent matrix/native OpenSees checks for a new isolated edition.

For PKPM/YJK this is explicitly a cross-engine diagnostic, not commercial truth.
No historical reference values, reviews or candidate responses are imported.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
import math
import os
from pathlib import Path

from section_diversity import read, write, sha, require, encoded, public_sections, used_sections


def compare(expected, actual):
    failures, count, worst = [], 0, 0.
    require([s['state'] for s in expected['states']] == [s['state'] for s in actual['states']], 'State mismatch')
    for old, new in zip(expected['states'], actual['states']):
        for group in ('quantities', 'derived'):
            index = {(q['id'], json.dumps(q.get('selection'), sort_keys=True)): q for q in new.get(group, [])}
            require(len(index) == len(old.get(group, [])), 'Quantity coverage mismatch')
            for q in old.get(group, []):
                target = index[(q['id'], json.dumps(q.get('selection'), sort_keys=True))]
                for key in ('selection', 'location', 'component', 'unit'):
                    require(q.get(key) == target.get(key), f'Quantity selector changed: {q["id"]}/{key}')
                t = q.get('tolerance', {'absolute': 1e-8, 'relative': 1e-6})
                limit = t['absolute'] + t['relative'] * abs(q['value'])
                error = abs(q['value'] - target['value'])
                count += 1; worst = max(worst, error/limit)
                if error > limit:
                    failures.append({'state': old['state'], 'id': q['id'], 'expected': q['value'],
                                     'actual': target['value'], 'error': error, 'limit': limit})
    return {'quantities': count, 'failures': failures, 'maximumToleranceFraction': worst}


def run_case(args):
    folder, output = map(Path, args)
    from reference_io import load_case
    from reference_cli import generate_reference
    from opensees_native import generate as generate_native
    case = load_case(folder)
    target = output/case['id']
    require(not target.exists(), f'Refusing to overwrite diagnostic evidence: {target}')
    matrix = generate_reference(case)
    native = read(generate_native(folder, output))
    write(target/'independent-reference.json', matrix)
    # Test the response effect of the public presentation budget as well as the
    # exact hidden authoring model. This is not a relaxation of result tolerances.
    rounded_case = deepcopy(case)
    records = [(name, sid, props) for name in case['contract']['attachments']
               for sid, props in public_sections(name, (folder/name).read_bytes())]
    bindings = []
    for state in rounded_case['states']:
        for section in used_sections(state['model']):
            matches = [(name, props) for name, sid, props in records if sid == section['id'] and
                       set(props) == set(section['properties']) and
                       all(math.isclose(section['properties'][k], v, rel_tol=1e-6, abs_tol=1e-12) for k, v in props.items())]
            require(matches, f'No actual public property record for state {state["state"]}/{section["id"]}')
            name, props = min(matches, key=lambda m: max(abs(v/section['properties'][k]-1) for k, v in m[1].items()))
            section['properties'] = deepcopy(props)
            bindings.append({'state': state['state'], 'section': section['id'], 'publicSource': name,
                             'publicSourceSha256': sha((folder/name).read_bytes())})
    write(target/'presentation-inputs.json', {'states': [{'state': s['state'], 'model': s['model']}
                                                        for s in rounded_case['states']], 'bindings': bindings})
    rounded = generate_reference(rounded_case)
    rounded['referenceKind'] = 'presentation-precision-diagnostic'
    # Rounded models differ from the source-bound reference; bind the actual
    # numeric inputs separately, never certify this as the canonical reference.
    rounded.pop('sourceHash', None); rounded.pop('sourceManifest', None); rounded.pop('inputHashes', None)
    rounded['modelSha256ByState'] = [{'state': s['state'], 'sha256': sha(encoded(s['model']))}
                                   for s in rounded_case['states']]
    write(target/'presentation-precision.json', rounded)
    result = {'caseId': case['id'], 'engine': case['contract']['plannedEngine'],
              'sourceHash': case['sourceHash'], 'states': len(case['states']),
              'nativeRole': native['nativeRole'], 'nativeSolver': native['solver'],
              'nativeVsMatrix': compare(matrix, native), 'presentationVsFullPrecision': compare(matrix, rounded),
              'nativeEquilibriumPassed': all(c['equilibriumPassed'] for c in native['checks']),
              'independentReview': 'pending', 'candidateTrial': 'not-run'}
    result['passed'] = (result['nativeEquilibriumPassed'] and not result['nativeVsMatrix']['failures']
                        and not result['presentationVsFullPrecision']['failures'])
    write(target/'verification.json', result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--edition-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--workers', type=int, default=3)
    args = p.parse_args()
    require(1 <= args.workers <= 4, 'Use 1..4 isolated solver processes')
    require(not args.output.exists(), 'Output must be a new directory')
    args.output.mkdir(parents=True)
    for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[key] = '1'
    plan = read(args.edition_root/'diversity-plan.json')
    jobs = [(str(args.edition_root/'corpora/research-300/cases'/r['caseId']), str(args.output)) for r in plan['cases']]
    results, errors = [], []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_case, job): Path(job[0]).name for job in jobs}
        for f in as_completed(futures):
            try:
                result = f.result(); results.append(result)
                print(json.dumps({'caseId': result['caseId'], 'passed': result['passed'],
                                  'quantities': result['nativeVsMatrix']['quantities']}), flush=True)
            except Exception as exc:
                errors.append({'caseId': futures[f], 'error': str(exc)})
                print(json.dumps(errors[-1]), flush=True)
    result = {'schemaVersion': 1, 'edition': plan['edition'], 'planSha256': sha(encoded(plan)),
              'cases': sorted(results, key=lambda r: r['caseId']), 'errors': errors,
              'summary': {'cases': len(results), 'states': sum(r['states'] for r in results),
                          'passed': sum(r['passed'] for r in results),
                          'quantities': sum(r['nativeVsMatrix']['quantities'] for r in results),
                          'sameEngineOpenSeesCases': sum(r['engine'] == 'OpenSees' for r in results),
                          'commercialCrossEngineDiagnosticCases': sum(r['engine'] != 'OpenSees' for r in results),
                          'commercialSameEngineReferences': 0, 'formalScoringReady': False}}
    write(args.output/'verification.json', result)
    print(json.dumps(result['summary']), flush=True)
    return 0 if len(results) == 300 and all(r['passed'] for r in results) and not errors else 1


if __name__ == '__main__':
    raise SystemExit(main())
