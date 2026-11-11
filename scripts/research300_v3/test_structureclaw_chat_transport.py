import json
import unittest

from scripts.research300_v3.structureclaw_chat_transport import project_sse, select_request


def wire(*events):
    return (''.join('data: ' + json.dumps(e, ensure_ascii=False) + '\n\n' for e in events) + 'data: [DONE]\n\n').encode()


class TransportContract(unittest.TestCase):
    start = {'type': 'start', 'content': {'conversationId': 'conv', 'traceId': 'trace'}}

    def test_state_routing_preserves_message_and_attachments(self):
        issued = {'message': '原消息\nunchanged', 'conversationId': 'conv',
                  'context': {'attachments': [{'fileId': 'file'}], 'runPolicy': {'budget': 24}}}
        snapshot = {'conversationId': 'conv', 'busy': False, 'waitingForReply': False}
        endpoint, body = select_request(issued, snapshot)
        self.assertEqual(endpoint, '/api/v1/chat/message')
        self.assertIs(body, issued)
        endpoint, body = select_request(issued, {**snapshot, 'waitingForReply': True})
        self.assertEqual(endpoint, '/api/v1/chat/stream/resume')
        self.assertEqual(body, {'conversationId': 'conv', 'resumeValue': issued['message'],
                                'attachments': issued['context']['attachments']})
        self.assertNotIn('runPolicy', body)

    def test_unknown_busy_and_wrong_session_fail_closed(self):
        for snapshot in [{}, {'conversationId': 'other'},
                         {'conversationId': 'conv', 'busy': True, 'waitingForReply': True},
                         {'conversationId': 'conv', 'busy': False, 'waitingForReply': None}]:
            with self.assertRaises(ValueError):
                select_request({'conversationId': 'conv'}, snapshot)

    def test_last_complete_result_preserves_text_fields_and_trace(self):
        content = {'response': '说明\n```json\n{"value":1.2345678901234567,"runId":"actual"}\n```',
                   'analysis': {'runId': 'actual'}, 'mode': 'conversation'}
        raw = wire(self.start, {'type': 'result', 'content': {'response': 'earlier'}},
                   {'type': 'result', 'content': content}, {'type': 'presentation_complete'}, {'type': 'done'})
        projected, receipt = project_sse(raw, 'conv')
        self.assertEqual(projected, {'result': content})
        self.assertEqual(receipt['selectedEventIndex'], 2)
        self.assertEqual(receipt['traceId'], 'trace')
        self.assertEqual(receipt['answerFieldsInferred'], 0)

    def test_interrupt_uses_original_question_and_never_old_result(self):
        question = {'resumeRequired': True, 'questions': [{'question': '需要哪种范围？'}]}
        projected, receipt = project_sse(wire(self.start, {'type': 'result', 'content': {'response': 'old'}},
                                            {'type': 'interaction_update', 'content': question}), 'conv')
        self.assertEqual(projected['result']['response'], question['questions'][0]['question'])
        self.assertEqual(receipt['outcome'], 'waiting_for_reply')

    def test_error_stream_never_exposes_prior_answer(self):
        failure = {'type': 'error', 'error': 'LLM_CALL_BUDGET_EXHAUSTED', 'code': 'INTERNAL_ERROR'}
        for events in [(failure,), (self.start, {'type': 'result', 'content': {'response': 'old'}}, failure)]:
            projected, receipt = project_sse(wire(*events), 'conv')
            self.assertEqual(projected, {'error': failure})
            self.assertEqual(receipt['outcome'], 'error')

    def test_truncation_duplicate_keys_conflicts_and_wrong_identity_fail(self):
        result = {'type': 'result', 'content': {'response': '{}'}}
        valid = wire(self.start, result, {'type': 'done'})
        invalid = [valid[:-1], valid.replace(b'data: [DONE]\n\n', b''),
                   valid + b'data: {}\n\n', valid.replace(b'"response": "{}"', b'"response":"{}","response":"bad"'),
                   wire(self.start, result), wire(self.start, result, {'type': 'done'}, {'type': 'done'}),
                   wire(self.start, {'type': 'interaction_update', 'content': {'resumeRequired': True}}, {'type': 'done'}),
                   valid.replace(b'"conv"', b'"other"')]
        for raw in invalid:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    project_sse(raw, 'conv')


if __name__ == '__main__':
    unittest.main()
