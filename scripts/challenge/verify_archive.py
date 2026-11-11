"""Verify retained pilot bytes/calls and optionally replay all final v3 scores offline."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--replay', action='store_true')
    args = parser.parse_args()
    review = args.review.resolve()
    meta = json.loads((review / 'archive.json').read_text())
    file = review / meta['file']
    assert file.name == meta['file']
    assert sha(file.read_bytes()) == meta['sha256']
    manifest = json.loads((review / 'archive-manifest.json').read_text())
    assert sha((review / 'archive-manifest.json').read_bytes()) == meta['manifestSha256']
    names = [row['path'] for row in manifest['files']]
    assert len(names) == len(set(names))
    assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in names)
    with zipfile.ZipFile(file) as archive:
        assert sorted(archive.namelist()) == sorted(names)
        for row in manifest['files']:
            data = archive.read(row['path'])
            assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
        def read(name):
            return json.loads(archive.read(name))
        plan = read('trial/plan.json')
        source = read('trial/source-binding.json')
        edition = read('edition/manifest.json')
        assert source['manifestSha256'] == sha(archive.read('edition/manifest.json'))
        assert len(plan) == len(edition['cases']) == 6
        calls, threads = 0, set()
        for case in plan:
            thread = None
            for turn in case['turns']:
                prefix = f'trial/runs/{case["caseId"]}/{turn["id"]}/'
                dispatch = read(prefix + 'dispatch.json')
                capture = read(prefix + 'capture.json')
                events = [json.loads(line) for line in archive.read(prefix + 'events.jsonl').splitlines() if line]
                assert dispatch['actualModelCall'] and dispatch['publicOnly']
                assert dispatch['model'] == 'gpt-6.1-sol' and dispatch['reasoningEffort'] == 'high'
                assert dispatch['promptSha256'] == sha(archive.read(prefix + 'prompt.txt'))
                assert any(e.get('type') == 'turn.completed' for e in events)
                assert capture['manifestSha256'] == source['manifestSha256']
                if thread is None:
                    assert dispatch['parentThread'] is None and capture['threadId'] not in threads
                    threads.add(capture['threadId'])
                else:
                    assert dispatch['parentThread'] == thread == capture['threadId']
                thread = capture['threadId']
                answers = [e['item']['text'] for e in events if e.get('type') == 'item.completed'
                           and e.get('item', {}).get('type') == 'agent_message']
                assert answers and archive.read(prefix + 'answer.txt').decode().rstrip('\n') == answers[-1].rstrip('\n')
                isolation = read(prefix + 'isolation.json')
                assert isolation['exitCode'] == 0
                probes = json.loads(isolation['stdout'])
                assert probes[:3] == [True]*3 and not any(probes[3:])
                calls += 1
        assert calls == 18 and len(threads) == 6
        result = {'filesVerified': len(names), 'actualCallsVerified': calls, 'caseThreadsVerified': len(threads)}
        if args.replay:
            for source in meta['implementationFiles']:
                assert sha((ROOT / source['path']).read_bytes()) == source['sha256'], source['path']
            replay = []
            with tempfile.TemporaryDirectory(prefix='challenge-offline-') as tmp:
                tmp = Path(tmp)
                for name in names:
                    if name.startswith(('edition/', 'trial/')):
                        dest = tmp / name
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(archive.read(name))
                for case in plan:
                    for turn in case['turns']:
                        prefix = f'trial/runs/{case["caseId"]}/{turn["id"]}/'
                        output = tmp / (case['caseId']+'-'+turn['id']+'-replay.json')
                        process = subprocess.run(['node', str(ROOT / 'scripts/challenge/evaluate-v3.cjs'),
                                                  '--edition', str(tmp / 'edition'), '--run', str(tmp / 'trial'),
                                                  '--case', case['caseId'], '--turn', turn['id'], '--output', str(output)],
                                                 capture_output=True, text=True, timeout=90)
                        assert process.returncode in (0, 1), process.stderr
                        actual = json.loads(output.read_text())
                        expected = read(prefix + 'evaluation-v3.json')
                        assert actual == expected, (case['caseId'], turn['id'], 'replay differs')
                        replay.append({'caseId': case['caseId'], 'turnId': turn['id'], 'passed': actual['passed']})
            result['offlineReplay'] = replay
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
