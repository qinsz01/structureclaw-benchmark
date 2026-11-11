"""Classify CLI protocol outcomes; never interpret engineering task content."""
import json
import re

TRANSIENT = re.compile(r'429|too many requests|rate.limit|model is at capacity|stream.*disconnect|connection.*(?:reset|closed|refused)|temporar.*unavail|overload|status[: =]+50[0234]', re.I)
CONFIGURATION = re.compile(r'401|403|unauthorized|authentication|invalid.api.key|model.*(?:not.supported|not.found|does.not.exist)', re.I)
CONTEXT = re.compile(r'context.(?:window|length)|maximum.context|input.*too.long|token.limit', re.I)


def classify(execution, events):
    terminal_errors = [e for e in events if e.get('type') in ('error', 'turn.failed')]
    completed = any(e.get('type') == 'turn.completed' for e in events)
    if execution.get('malformedEvents'):
        return 'interrupted', False, 'MALFORMED_EVENT_STREAM'
    if execution.get('stopReason'):
        return 'candidate_failed', False, execution['stopReason']
    if completed and execution['exitCode'] == 0:
        return 'completed', False, None
    message = json.dumps(terminal_errors, ensure_ascii=False)
    if CONTEXT.search(message):
        return 'candidate_failed', False, 'CONTEXT_BUDGET_EXCEEDED'
    if TRANSIENT.search(message):
        return 'service_blocked', True, 'TRANSIENT_MODEL_SERVICE_ERROR'
    if CONFIGURATION.search(message):
        return 'service_blocked', False, 'MODEL_CONFIGURATION_ERROR'
    return 'interrupted', False, 'UNCLASSIFIED_EXECUTION_INTERRUPTION'
