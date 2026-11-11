"""Run disjoint offline replay shards and check complete, nonduplicated coverage."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import subprocess


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def run(edition, work, answers, output, workers=6):
    edition, work, answers, output = [Path(p).resolve() for p in (edition, work, answers, output)]
    if output.exists() or type(workers) is not int or not 1 <= workers <= 16:
        raise ValueError('New output and 1..16 workers required')
    for source in (edition, work, answers):
        if output.is_relative_to(source) or source.is_relative_to(output):
            raise ValueError('Output overlaps retained originals')
    manifest = read(edition / 'manifest.json')
    output.mkdir(parents=True)
    groups, costs = [[] for _ in range(workers)], [0] * workers
    def cost(c):
        return len(c['turns']) * (5 if c['analysis'] == 'project' else 3 if c['analysis'] == 'scenario' else 1)
    for case in sorted(manifest['cases'], key=lambda c: (-cost(c), c['id'])):
        i = min(range(workers), key=costs.__getitem__)
        groups[i].append(case['id'])
        costs[i] += cost(case)
    entry = Path(__file__).with_name('replay_retained_v32.cjs')
    def execute(i, ids):
        selection = output / f'selection-{i:02}.json'
        write(selection, ids)
        target = output / f'chunk-{i:02}'
        command = ['node', '--max-old-space-size=4096', str(entry), '--edition', str(edition), '--work', str(work),
                   '--answers', str(answers), '--output', str(target), '--case-list', str(selection)]
        with (output / f'chunk-{i:02}.log').open('x') as log:
            code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        return i, code, read(target / 'summary.json')
    summaries = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(execute, i, ids) for i, ids in enumerate(groups) if ids]
        for future in as_completed(futures):
            i, code, summary = future.result()
            summaries.append((i, code, summary))
            print(json.dumps({'chunk': i, 'turns': summary['turns'], 'allPassed': summary['allPassed']}), flush=True)
    expected = [(c['id'], t['id']) for c in manifest['cases'] for t in c['turns']]
    rows = [{**r, 'details': f'chunk-{i:02}/' + r['details']} if 'details' in r else r
            for i, _, summary in summaries for r in summary['rows']]
    keyed = {(r['caseId'], r['turnId']): r for r in rows}
    if len(keyed) != len(rows) or set(keyed) != set(expected):
        raise ValueError('Incomplete, duplicate or unissued replay coverage')
    first = summaries[0][2]
    manifest_sha = hashlib.sha256((edition / 'manifest.json').read_bytes()).hexdigest()
    if any(s['sourceCode'] != first['sourceCode'] or s['manifestSha256'] != manifest_sha for _, _, s in summaries):
        raise ValueError('Source or edition changed across replay shards')
    result = {**first, 'cases': len(manifest['cases']), 'turns': len(rows),
              'positivePassed': sum(r['passed'] for r in rows), 'controls': sum(r['controls'] for r in rows),
              'controlsPassed': sum(r['controlsPassed'] for r in rows), 'fullEditionCoverage': True,
              'allPassed': all(code == 0 and s['allPassed'] for _, code, s in summaries),
              'workers': workers, 'rows': [keyed[key] for key in expected],
              'coordinatorSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    write(output / 'summary.json', result)
    return {k: v for k, v in result.items() if k not in ('rows', 'sourceCode')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('edition', 'work', 'answers', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--workers', type=int, default=6)
    a = parser.parse_args()
    result = run(a.edition, a.work, a.answers, a.output, a.workers)
    print(json.dumps(result))
    raise SystemExit(0 if result['allPassed'] else 1)
