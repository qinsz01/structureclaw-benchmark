"""Project the sealed trial into read-only viewer data, never live scratch files."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


class TrialArchive:
    def __init__(self, folder):
        meta = json.loads((folder / 'evidence-meta.json').read_text())
        manifest = (folder / 'archive-manifest.json').read_bytes()
        assert sha(manifest) == meta['archiveManifestSha256'], 'Trial manifest changed'
        self.files = {r['path']: r for r in json.loads(manifest)['files']}
        self.stream = tempfile.TemporaryFile()
        digest = hashlib.sha256()
        for part in meta['parts']:
            assert Path(part['file']).name == part['file']
            data = (folder / part['file']).read_bytes()
            assert len(data) == part['bytes'] and sha(data) == part['sha256'], 'Trial part changed'
            self.stream.write(data)
            digest.update(data)
        assert self.stream.tell() == meta['bytes'] and digest.hexdigest() == meta['sha256']
        self.stream.seek(0)
        self.zip = zipfile.ZipFile(self.stream)

    def read(self, name):
        row = self.files[name]
        data = self.zip.read('blobs/' + row['sha256'])
        assert len(data) == row['bytes'] and sha(data) == row['sha256'], name
        return data

    def obj(self, name):
        return json.loads(self.read(name))

    def close(self):
        self.zip.close()
        self.stream.close()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')


def project(root, output, edition='latest', namespace='trials'):
    modern = edition != 'historical' and (root / 'docs/implementation/reviews/codex-diversity300-20261027/evidence-meta.json').exists()
    folder = root / ('docs/implementation/reviews/codex-diversity300-20261027' if modern else 'docs/implementation/reviews/codex-full300-20261027')
    summary = json.loads((folder / 'summary.json').read_text())
    archive = TrialArchive(folder)
    exported = {}

    def asset(name, data=None):
        if name in exported:
            return exported[name]
        data = archive.read(name) if data is None else data
        suffix = PurePosixPath(name).suffix.lower()
        assert suffix in {'.png', '.jpg', '.jpeg', '.svg', '.dxf', '.md', '.json', '.txt'}
        relative = namespace + '/files/' + sha(data) + suffix
        dest = output / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        exported[name] = {'name': PurePosixPath(name).name, 'path': relative,
                          'sha256': sha(data), 'bytes': len(data)}
        return exported[name]

    try:
        plan = archive.obj('work/plan.json')
        rows = []
        passed_turns = 0
        for case in plan:
            cid = case['caseId']
            report = archive.obj(f'work/assessments/{cid}-{summary["revision"]}.json')
            receipt = archive.obj(f'work/runs/{cid}/case-execution.json')
            assert receipt['status'] == 'captured' and receipt['capturedTurns'] == len(case['turns'])
            result = next(r for r in summary['caseResults'] if r['caseId'] == cid)
            assert report['status'] == result['status']
            scratch = f'public-environment/{cid}/scratch/'
            artifacts = []
            for name in archive.files:
                if name.startswith(scratch):
                    local = name[len(scratch):]
                    suffix = PurePosixPath(name).suffix.lower()
                    if suffix in {'.png', '.jpg', '.jpeg', '.svg', '.md'} or (
                            suffix == '.json' and PurePosixPath(name).name.startswith('model-')):
                        artifacts.append({**asset(name), 'scratchPath': local})
            turns = []
            for t in case['turns']:
                tid = t['id']
                prefix = f'work/runs/{cid}/{tid}'
                execution = archive.obj(prefix + '/execution.json')
                dispatch = archive.obj(prefix + '/dispatch.json')
                assert dispatch['actualModelCall'] and dispatch['publicOnly']
                assert dispatch['model'] == summary['model'] and dispatch['reasoningEffort'] == summary['reasoningEffort']
                assert sha(archive.read(prefix + '/prompt.txt')) == dispatch['promptSha256']
                events = [json.loads(line) for line in archive.read(prefix + '/events.jsonl').splitlines() if line.strip()]
                answer = archive.read(prefix + '/answer.txt').decode()
                actual = [e['item']['text'] for e in events if e.get('type') == 'item.completed'
                          and e.get('item', {}).get('type') == 'agent_message']
                assert execution['completedTurn'] and execution['exitCode'] == 0
                assert any(e.get('type') == 'turn.completed' for e in events)
                assert actual and actual[-1].rstrip('\n') == answer.rstrip('\n')
                public = f'public-environment/{cid}/{tid}/agent-input/cases/{cid}/'
                task = archive.obj(public + 'task.json')
                question = next(row for row in task['turns'] if row['id'] == tid)
                attachments = []
                for name in question['attachments']:
                    assert PurePosixPath(name).name == name
                    attachments.append(asset(public + name))
                grade = next(row for row in report['cases'][0]['evaluation']['turns'] if row['turnId'] == tid)
                turns.append({'id': tid, 'instruction': question['instruction'], 'attachments': attachments,
                              'answer': answer, 'answerSha256': sha(answer.encode()),
                              'answerFile': asset(prefix + '/answer.txt'),
                              'status': grade['status'], 'metrics': grade['evaluation']['metrics'],
                              'execution': {k: execution[k] for k in ('threadId', 'completedTurn', 'elapsedSeconds')},
                              'artifacts': [a for a in artifacts if tid in a['scratchPath']]})
                passed_turns += grade['status'] == 'passed'
            detail = {'caseId': cid, 'engine': case['engine'], 'status': report['status'],
                      'attribution': result.get('attribution'), 'turns': turns,
                      'artifacts': artifacts, 'model': summary['model'], 'revision': summary['revision'], 'edition': summary.get('edition', 'baseline'), 'sourceTrial': result.get('trialId'),
                      'sutCommit': summary['sutCommit']}
            write_json(output / f'{namespace}/cases/{cid}.json', detail)
            rows.append({'caseId': cid, 'engine': case['engine'], 'status': report['status'],
                         'turns': len(turns), 'attribution': result.get('attribution'),
                         'repaired': not modern and cid in ('INT-056', 'STD-080')})
        assert len(rows) == 300 and sum(c['turns'] for c in rows) == 420
        assert sum(c['status'] == 'passed' for c in rows) == summary['cases']['passed']
        assert passed_turns == summary['turns']['passed']
        for key, groups in (('byEngine', {r['engine'] for r in rows}), ('byFamily', {'STD', 'INT', 'MM'})):
            for group in groups:
                members = [r for r in rows if (r['engine'] if key == 'byEngine' else r['caseId'].split('-')[0]) == group]
                passed = sum(r['status'] == 'passed' for r in members)
                assert summary[key][group] == {'cases': len(members), 'passed': passed, 'notPassed': len(members) - passed}
        compact = {k: summary[k] for k in ('model', 'reasoningEffort', 'revision', 'sutCommit',
                   'cases', 'turns', 'byEngine', 'byFamily', 'attributionCounts', 'pendingReviews')}
        compact['caseResults'] = rows
        compact['externalBlindReview'] = False
        if not modern:
            fixes = root / 'docs/implementation/reviews/post300-fixes-20261027'
            verification = json.loads((fixes / 'archive-verification.json').read_text())
            data = (fixes / verification['archive']).read_bytes()
            assert sha(data) == verification['sha256']
            with tempfile.TemporaryFile() as stream:
                stream.write(data)
                stream.seek(0)
                with zipfile.ZipFile(stream) as z:
                    records = {r['path']: r for r in json.loads(z.read('manifest.json'))}
                    def repair(name):
                        data = z.read(name)
                        assert sha(data) == records[name]['sha256']
                        return data
                    interaction = json.loads(repair('review/interaction-regression.json'))
                    repair_artifacts = []
                    repair_scratch = 'public-runs/structureclaw-post300-fixes-retry1-20261027/INT-056/scratch/'
                    for name in records:
                        if name.startswith(repair_scratch) and PurePosixPath(name).name.startswith('model-') and name.endswith('.json'):
                            repair_artifacts.append({**asset(name, repair(name)), 'scratchPath': name[len(repair_scratch):]})
                    repair_turns = []
                    for tid in ('t1', 't2', 't3'):
                        prefix = 'work/interaction-retry1/runs/INT-056/' + tid
                        question = json.loads(repair('public-runs/structureclaw-post300-fixes-retry1-20261027/INT-056/'
                                                    + tid + '/agent-input/cases/INT-056/task.json'))
                        turn = next(t for t in question['turns'] if t['id'] == tid)
                        answer = repair(prefix + '/answer.txt').decode()
                        grade = next(t for t in interaction['evaluation']['turns'] if t['turnId'] == tid)
                        repair_public = 'public-runs/structureclaw-post300-fixes-retry1-20261027/INT-056/' + tid + '/agent-input/cases/INT-056/'
                        repair_turns.append({'id': tid, 'instruction': turn['instruction'], 'answer': answer,
                                             'status': grade['status'], 'metrics': grade['evaluation']['metrics'],
                                             'answerFile': asset('repair/INT-056/' + tid + '/answer.txt', answer.encode()),
                                             'attachments': [asset(repair_public + n, repair(repair_public + n)) for n in turn['attachments']],
                                             'artifacts': [a for a in repair_artifacts if tid in a['scratchPath']]})
                    fixed_sut = json.loads(repair('review/verification.json'))['sutFixedCommit']
                    write_json(output / f'{namespace}/repair-INT-056.json', {'turns': repair_turns, 'status': interaction['status'], 'artifacts': repair_artifacts, 'sutCommit': fixed_sut})
            native = json.loads((fixes / 'native-regression.json').read_text())
            compact['repairs'] = {'INT-056': {'kind': 'candidate-retest', 'status': interaction['status'], 'turns': 3},
                                  'STD-080': {'kind': 'adapter-regression', 'status': 'passed',
                                              'quantities': native['quantities']['comparedValues']}}
        else:
            compact['repairs'] = {}
        compact['edition'] = summary.get('edition', 'baseline')
        if modern:
            compact['diversity'] = summary['diversity']
            history = project(root, output, 'historical', namespace + '/historical')
            compact['historical'] = {k: history[k] for k in ['cases', 'turns', 'revision']}
        write_json(output / f'{namespace}/index.json', compact)
        return compact
    finally:
        archive.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--edition', choices=['latest', 'historical'], default='latest')
    args = parser.parse_args()
    project(args.root, args.output, args.edition)
