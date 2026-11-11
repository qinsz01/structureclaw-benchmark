"""Public client: turn-scoped requests, controller-assigned execution identities."""
import argparse
import json
from pathlib import Path
import re
import time
import uuid

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('request', 'session', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--turn', required=True)
    p.add_argument('--timeout', type=float, default=600)
    a = p.parse_args()
    if not re.fullmatch(r't[1-4]', a.turn):
        p.error('Explicit issued turn required')
    # The request bytes are copied without reading any benchmark reference.
    data = a.request.read_bytes()
    json.loads(data)
    nonce = uuid.uuid4().hex
    directory = a.session / 'scratch/requests' / a.turn
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / (nonce + '.tmp')
    temporary.write_bytes(data)
    temporary.replace(directory / (nonce + '.json'))
    reply = a.session / 'solver-replies' / a.turn / (nonce + '.json')
    deadline = time.monotonic() + a.timeout
    while not reply.exists():
        if time.monotonic() > deadline:
            raise TimeoutError('Controller did not publish a completed native reply')
        time.sleep(.1)
    result = json.loads(reply.read_bytes())
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    if not result['ok']:
        raise RuntimeError(result['error'])
    print(json.dumps({'ok': True, 'jobId': result['jobId'], 'output': str(a.output)}))
