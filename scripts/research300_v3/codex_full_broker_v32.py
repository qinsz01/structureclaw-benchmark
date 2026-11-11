"""Three-engine extension of the frozen smoke transport, with bounded polling."""
import json

from .codex_broker_v32 import Broker, sha, write


class FullBroker(Broker):
    def __init__(self, *args, engines, **kwargs):
        super().__init__(*args, **kwargs)
        if not engines or any(e not in ('OpenSees', 'PKPM', 'YJK') for e in engines.values()):
            raise ValueError('Explicit designated engines required')
        self.engines, self.retired = dict(engines), {}

    def open_turn(self, case_id, turn_id):
        if case_id not in self.engines or (case_id, turn_id) in self.retired:
            raise ValueError('Unknown or already sealed case/turn')
        return super().open_turn(case_id, turn_id)

    def _execute(self, job, raw, attempt, error):
        engine = self.engines[attempt['caseId']]
        try:
            if error:
                raise ValueError(error)
            reply = self.executor(json.loads(raw), job, self.sut, engine, role='candidate')
        except Exception as exc:
            reply = {'ok': False, 'error': str(exc)}
        reply['jobId'] = attempt['evidenceId']
        receipt = {'role': 'candidate', 'caseId': attempt['caseId'], 'turnId': attempt['turnId'],
                   'engine': engine, 'ok': reply['ok'], 'error': reply.get('error'),
                   'requestSha256': sha(raw), 'sutCommit': self.binding['sutCommit'],
                   'executionSpecificationSha256': self.binding['executionSpecificationSha256'],
                   'stateSha256': sha((job / 'state.json').read_bytes()) if reply['ok'] else None}
        write(job / 'broker-receipt.json', receipt)
        target = self.base / attempt['caseId'] / 'solver-replies' / attempt['turnId'] / (attempt['requestNonce'] + '.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix('.tmp')
        write(temporary, reply)
        if target.exists():
            raise ValueError('Reply identity reused')
        temporary.replace(target)

    def retire_case(self, case_id):
        # Called only after owned CLI processes are closed. Retired spools can
        # no longer execute. Keep the original attempt ledger for final sealing,
        # without repeatedly listing hundreds of completed NAS directories.
        with self.lock:
            self._scan()
            keys = [key for key in self.turns if key[0] == case_id]
            if any(self.turns[key]['open'] for key in keys):
                raise ValueError('Cannot retire an open turn')
            for key in keys:
                self.retired[key] = self.turns.pop(key)
        for cid, _, future in self.futures:
            if cid == case_id:
                future.result()

    def attempts(self, case_id, turn_id):
        with self.lock:
            value = self.turns.get((case_id, turn_id), self.retired.get((case_id, turn_id), {}))
            return list(value.get('attempts', []))
