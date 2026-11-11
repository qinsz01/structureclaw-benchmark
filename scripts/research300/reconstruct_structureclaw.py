"""Recover canonical receipt payloads without running a solver or changing a receipt.

The upstream host archive uses JavaScript JSON serialization. That can erase
float/int distinctions and negative zero from the original Python JSON. We only
publish a candidate serialization when its SHA256 equals the native receipt.
"""
from __future__ import annotations
import base64
import gzip
import hashlib
import json
from pathlib import Path
import sys

FORMAT = 'sha256:python-json-sort-keys-utf8-compact-v1'


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf8')


def floats(value):
    """An additional serialization candidate, never an unverified conversion."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return float(value)
    if isinstance(value, list):
        return [floats(item) for item in value]
    if isinstance(value, dict):
        return {key: floats(item) for key, item in value.items()}
    return value


def typed_responses(value):
    """Known OpenSees numeric response fields are floats; mesh IDs stay integers."""
    value = json.loads(json.dumps(value))
    for key in ('displacements', 'reactions', 'forces', 'segmentResults'):
        if key in value:
            value[key] = floats(value[key])
    mesh = value.get('solverMesh')
    if isinstance(mesh, dict):
        for node in mesh.get('nodes', []):
            for key in ('x', 'y', 'z'):
                if key in node:
                    node[key] = float(node[key])
        for group in [mesh.get('elements', []), *mesh.get('physicalElements', {}).values()]:
            for element in group:
                for key in ('start', 'end', 'localAxes'):
                    if key in element:
                        element[key] = floats(element[key])
    return value


def captured_payloads(root, run, host_model):
    """Read only manifests bound to this host request; verify every copied byte."""
    if not root:
        return {}, []
    root = Path(root).resolve()
    manifests = [root / 'capture.json'] if (root / 'capture.json').is_file() else sorted(root.glob('*/capture.json'))
    payloads, issues = {}, []
    for file in manifests:
        try:
            folder = file.parent.resolve()
            if not folder.is_relative_to(root):
                raise ValueError('capture directory is outside capture root')
            manifest_path = file.resolve()
            if not manifest_path.is_relative_to(folder):
                raise ValueError('capture manifest is outside capture directory')
            manifest_bytes = manifest_path.read_bytes()
            capture = json.loads(manifest_bytes)
            if capture.get('kind') != 'structureclaw-python-worker-capture' or capture.get('exitCode') != 0:
                continue
            request_path = (folder / 'request.json').resolve()
            if not request_path.is_relative_to(folder):
                raise ValueError('request path is outside capture directory')
            raw_request = request_path.read_bytes()
            if hashlib.sha256(raw_request).hexdigest() != capture.get('requestSha256'):
                raise ValueError('captured request SHA256 mismatch')
            request = json.loads(raw_request).get('input', {})
            if request.get('model') != host_model:
                continue
            if run.get('requestId') and request.get('requestId') != run['requestId']:
                continue
            sources = [{'kind': 'structureclaw-capture-manifest', 'path': str(manifest_path),
                        'sha256': hashlib.sha256(manifest_bytes).hexdigest()},
                       {'kind': 'structureclaw-capture-request', 'path': str(request_path),
                        'sha256': hashlib.sha256(raw_request).hexdigest()}]
            for name in ('request.json', 'stdout.json', 'stderr.log'):
                expected = capture.get('files', {}).get(name)
                if expected is None:
                    continue
                source = (folder / name).resolve()
                if not source.is_relative_to(folder):
                    raise ValueError('captured stream path is outside capture directory')
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                if digest != expected:
                    raise ValueError(f'captured {name} SHA256 mismatch')
                sources.append({'kind': 'structureclaw-capture-stream', 'path': str(source), 'sha256': digest})
            for receipt in capture.get('receipts', []):
                for name, relative in receipt.get('artifacts', {}).items():
                    artifact = (folder / relative).resolve()
                    if not artifact.is_relative_to(folder):
                        raise ValueError('native artifact path is outside capture directory')
                    data = artifact.read_bytes()
                    digest = hashlib.sha256(data).hexdigest()
                    if digest != receipt.get('receipt', {}).get(name + 'Sha256'):
                        raise ValueError('captured canonical payload SHA256 mismatch')
                    payloads[(name, digest)] = {'bytes': data, 'sources': sources + [{
                        'kind': 'structureclaw-native-' + name, 'path': str(artifact), 'sha256': digest}]}
        except Exception as error:
            issues.append(f'{file.name}: {error}')
    return payloads, issues


def reconstruct(request):
    raw = request['run']
    if isinstance(raw, str):
        if raw.lstrip().startswith('{'):
            run = json.loads(raw)
        else:
            source = Path(raw)
            run = json.loads(gzip.decompress(source.read_bytes()) if source.suffix == '.gz' else source.read_bytes())
    elif isinstance(raw, dict):
        run = raw
    else:
        raise ValueError('Run must be a JSON object, JSON text, or archive path')
    host_model = run.get('modelSnapshot') or run.get('request', {}).get('model')
    captured, capture_issues = captured_payloads(request.get('captureRoot'), run, host_model)
    normalized_model = None
    normalization_issue = None
    if request.get('structureclawRoot'):
        try:
            source_root = Path(request['structureclawRoot']) / 'backend/src/skill-shared/python'
            sys.path.insert(0, str(source_root))
            from structure_protocol.migrations import migrate_v1_to_v2
            from structure_protocol.structure_model_v2 import StructureModelV2
            normalized_model = StructureModelV2.model_validate(migrate_v1_to_v2(host_model)).model_dump(mode='json', exclude_unset=True)
        except Exception as error:
            normalization_issue = 'Pydantic normalization unavailable: ' + str(error)
    selections, sources = {}, {}
    diagnostics = capture_issues
    for key, result in run.get('results', {}).items():
        data = result.get('data', result)
        execution = data.get('execution') or result.get('execution') or result.get('meta', {}).get('execution') or {}
        receipt = execution.get('artifacts') or {}
        if execution.get('solver', '').lower() != 'opensees' or receipt.get('hashFormat') != FORMAT:
            diagnostics.append(f'{key}: supported OpenSees canonical receipt unavailable')
            continue
        keys = receipt.get('solverResponseKeys')
        if not isinstance(keys, list) or len(set(keys)) != len(keys) or any(not isinstance(name, str) or name not in data for name in keys):
            diagnostics.append(f'{key}: solverResponseKeys are missing, duplicate or unavailable')
            continue
        response = {name: data[name] for name in keys}
        candidates = {
            'normalizedInput': [host_model, normalized_model],
            'settings': [receipt.get('settings')],
            'solverResponse': [response, typed_responses(response), floats(response)],
        }
        payloads = {}
        issues = []
        for name, variants in candidates.items():
            expected = receipt.get(name + 'Sha256')
            original = captured.get((name, expected))
            if original is not None:
                payloads[name] = {'base64': base64.b64encode(original['bytes']).decode('ascii'), 'sha256': expected}
                for source in original['sources']:
                    sources[source['path']] = source
                continue
            for candidate in variants:
                if candidate is None:
                    continue
                value = encoded(candidate)
                if isinstance(expected, str) and hashlib.sha256(value).hexdigest() == expected.lower():
                    payloads[name] = {'base64': base64.b64encode(value).decode('ascii'), 'sha256': expected.lower()}
                    break
            if name not in payloads:
                issues.append(f'{key}: {name} canonical bytes could not be reproduced; retain original Python payload bytes during execution')
        if 'normalizedInput' not in payloads and normalization_issue:
            issues.append(f'{key}: {normalization_issue}')
        selections[key] = {'complete': len(payloads) == 3, 'payloads': payloads, 'diagnostics': issues}
        diagnostics.extend(issues)
    return {'selections': selections, 'diagnostics': diagnostics, 'sources': list(sources.values())}


if __name__ == '__main__':
    try:
        print(json.dumps(reconstruct(json.load(sys.stdin)), ensure_ascii=False))
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
