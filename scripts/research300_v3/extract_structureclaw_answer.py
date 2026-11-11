"""Locate an unchanged final answer inside one JSON Markdown fence.

This format adapter never reads references, repairs JSON, adds fields, or chooses
between multiple blocks. Byte offsets address the complete original UTF-8 reply.
"""
import hashlib
import json
import re

FAMILIES = ('runIds', 'jobIds', 'runIdsByModel', 'jobIdsByModel',
            'runIdsByScenario', 'jobIdsByScenario')
FENCE = re.compile(r'^```(?:json)?[ \t]*\r?\n(.*?)\r?\n```[ \t]*$', re.M | re.S | re.I)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError('Non-JSON constant: ' + value)


def extract_fenced_answer(original):
    """Return a literal byte slice and receipt, or None for ambiguous/invalid text."""
    if not isinstance(original, str):
        return None
    # Both opening and closing markers count. Extra fences are ambiguous even
    # when a caller believes one of them is more likely to be the final answer.
    if len(re.findall(r'^```', original, re.M)) != 2:
        return None
    matches = list(FENCE.finditer(original))
    if len(matches) != 1:
        return None
    match = matches[0]
    body = match.group(1)
    literal = body.strip(' \t\r\n')
    try:
        value = json.loads(literal, object_pairs_hook=_unique_object,
                           parse_constant=_invalid_constant)
    except (ValueError, TypeError):
        return None
    if not isinstance(value, dict) or sum(key in value for key in FAMILIES) != 1:
        return None
    if not any(key in value for key in ('quantities', 'clarifications', 'derived')):
        return None
    leading = len(body) - len(body.lstrip(' \t\r\n'))
    start = match.start(1) + leading
    end = start + len(literal)
    raw = original.encode('utf8')
    byte_start = len(original[:start].encode('utf8'))
    byte_end = len(original[:end].encode('utf8'))
    answer = raw[byte_start:byte_end]
    assert answer == literal.encode('utf8')
    return dict(answer=answer, receipt=dict(
        kind='literal-single-json-fence-v1', originalUtf8Sha256=hashlib.sha256(raw).hexdigest(),
        answerSha256=hashlib.sha256(answer).hexdigest(), byteStart=byte_start, byteEnd=byte_end,
        fieldsAdded=0, valuesChanged=0, privateReferencesUsed=False))
