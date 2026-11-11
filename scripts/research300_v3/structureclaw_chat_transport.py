"""Transport-only selection and lossless SSE event projection for StructureClaw.

Callers retain the wire bytes and this receipt. No candidate answer fields are
inferred from tools, artifacts, session snapshots, or benchmark references.
"""
import hashlib
import json


def select_request(issued, snapshot):
    """Use only the canonical conversation state to select the existing API."""
    if snapshot.get('conversationId') != issued.get('conversationId'):
        raise ValueError('SESSION_CONVERSATION_MISMATCH')
    if snapshot.get('busy') is not False:
        raise ValueError('SESSION_BUSY_OR_UNKNOWN')
    waiting = snapshot.get('waitingForReply')
    if not isinstance(waiting, bool):
        raise ValueError('SESSION_WAITING_STATE_UNKNOWN')
    if not waiting:
        return '/api/v1/chat/message', issued
    return '/api/v1/chat/stream/resume', {
        'conversationId': issued['conversationId'],
        'resumeValue': issued['message'],
        'attachments': issued.get('context', {}).get('attachments', []),
    }


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def project_sse(raw, conversation_id):
    """Project the public terminal event, preserving its decoded fields exactly.

    The protocol's last result is authoritative only after normal completion.
    An interrupt instead exposes its original guidance/question, and an error
    exposes no answer. A missing end marker or malformed event fails closed.
    """
    wire = raw.decode('utf8').replace('\r\n', '\n')
    if not wire.endswith('\n\n'):
        raise ValueError('SSE_INCOMPLETE_EVENT')
    events = []
    ended = False
    for block in wire.split('\n\n'):
        lines = [line for line in block.split('\n') if line and not line.startswith(':')]
        if not lines:
            continue
        if ended:
            raise ValueError('SSE_DATA_AFTER_END')
        if any(not line.startswith('data:') for line in lines):
            raise ValueError('SSE_UNEXPECTED_FIELD')
        data = '\n'.join(line[5:].removeprefix(' ') for line in lines)
        if data == '[DONE]':
            ended = True
            continue
        event = json.loads(data, object_pairs_hook=_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NON_JSON_CONSTANT')))
        if not isinstance(event, dict) or not isinstance(event.get('type'), str):
            raise ValueError('SSE_INVALID_EVENT')
        events.append(event)
    if not ended:
        raise ValueError('SSE_END_MARKER_MISSING')
    starts = [(i, e) for i, e in enumerate(events) if e['type'] == 'start']
    errors = [(i, e) for i, e in enumerate(events) if e['type'] == 'error']
    # Rejections before start are valid error streams, but cannot expose answers.
    if len(starts) > 1 or (not starts and not errors):
        raise ValueError('SSE_START_AMBIGUOUS_OR_MISSING')
    trace_id = None
    if starts:
        start = starts[0][1].get('content')
        if not isinstance(start, dict) or start.get('conversationId') != conversation_id:
            raise ValueError('SSE_CONVERSATION_MISMATCH')
        trace_id = start.get('traceId')
        if not isinstance(trace_id, str) or not trace_id:
            raise ValueError('SSE_TRACE_MISSING')
    receipt = {'wireSha256': hashlib.sha256(raw).hexdigest(), 'wireBytes': len(raw),
               'events': len(events), 'traceId': trace_id, 'answerFieldsInferred': 0}
    if errors:
        index, event = errors[-1]
        receipt.update(outcome='error', selectedEventIndex=index)
        return {'error': event}, receipt
    results = [(i, e) for i, e in enumerate(events) if e['type'] == 'result']
    interactions = [(i, e) for i, e in enumerate(events) if e['type'] == 'interaction_update']
    completions = [(i, e) for i, e in enumerate(events) if e['type'] == 'done']
    if interactions and (not results or interactions[-1][0] > results[-1][0]):
        if completions:
            raise ValueError('SSE_INTERRUPT_AND_COMPLETION_CONFLICT')
        index, event = interactions[-1]
        content = event.get('content')
        if not isinstance(content, dict) or content.get('resumeRequired') is not True:
            raise ValueError('SSE_INVALID_INTERRUPT')
        guidance = content.get('guidanceText')
        field = 'guidanceText'
        if not isinstance(guidance, str):
            questions = content.get('questions')
            guidance = questions[0].get('question') if isinstance(questions, list) and questions and isinstance(questions[0], dict) else None
            field = 'questions[0].question'
        if not isinstance(guidance, str):
            raise ValueError('SSE_INTERRUPT_TEXT_MISSING')
        receipt.update(outcome='waiting_for_reply', selectedEventIndex=index, responseSourceField=field)
        return {'result': {**content, 'response': guidance}}, receipt
    if len(completions) != 1 or not results or completions[0][0] != len(events) - 1:
        raise ValueError('SSE_COMPLETION_MISSING_OR_AMBIGUOUS')
    index, event = results[-1]
    content = event.get('content')
    if not isinstance(content, dict) or not isinstance(content.get('response'), str):
        raise ValueError('SSE_RESULT_TEXT_MISSING')
    receipt.update(outcome='completed', selectedEventIndex=index, responseSourceField='response')
    return {'result': content}, receipt
