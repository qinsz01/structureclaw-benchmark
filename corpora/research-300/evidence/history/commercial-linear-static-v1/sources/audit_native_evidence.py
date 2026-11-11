#!/usr/bin/env python3
"""Independently audit retained research-300 native inputs and physical responses.

No structural solver, native extension, SUT converter, network, or acceptance writer
is imported or invoked. This deliberately supports the corpus's linear static,
global nodal/uniform member loads only. Unsupported physics fails closed. Numerical
cross-engine agreement and derived-result review belong to the separate reference
checker. A passing report is review evidence, never automatic native acceptance.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
RAW_FILES = ('native-input-receipt.json', 'native-solver-receipt.json', 'native-raw-responses.json', 'native-checks.json')
GENERATED = {*RAW_FILES, 'native-opensees-reference.json', 'independent-reference.json', 'reference-provenance.json', 'acceptance.json'}
CASE_ID = re.compile('(?:STD|INT|MM)-(?:00[1-9]|0[1-9][0-9]|100)\\Z')
errors = []
counts = collections.Counter()
maxima = collections.defaultdict(float)
cid = ''
runlabel = 'bindings'

def sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()

def directory_fd(directory):
    """Open every path component without following symlinks, including ancestors."""
    p = Path(os.path.abspath(directory))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open('/', flags)
    try:
        for part in p.parts[1:]:
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise

def safe_bytes(file):
    file = Path(file)
    descriptor = directory_fd(file.parent)
    try:
        child = os.open(file.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
        with os.fdopen(child, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= 512 * 1024 * 1024:
                raise ValueError('Expected a nonempty regular file of at most 512 MiB')
            return stream.read()
    finally:
        os.close(descriptor)

class Snapshot:

    def __init__(self):
        self.files = {}
        self.cache = {}

    def read(self, file):
        path = str(Path(os.path.abspath(file)))
        if path not in self.cache:
            raw = safe_bytes(path)
            self.cache[path] = raw
            self.files[path] = {'path': path, 'sha256': sha_bytes(raw), 'bytes': len(raw)}
        return self.cache[path]

    def document(self, file):

        def pairs(items):
            result = {}
            for (key, value) in items:
                if key in result:
                    raise ValueError('Duplicate JSON key: ' + key)
                result[key] = value
            return result

        def constant(value):
            raise ValueError('Non-finite JSON constant: ' + value)

        def finite_tree(value):
            if isinstance(value, float) and (not math.isfinite(value)):
                raise ValueError('Non-finite JSON value')
            for item in value.values() if isinstance(value, dict) else value if isinstance(value, list) else []:
                finite_tree(item)
        result = json.loads(self.read(file).decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
        finite_tree(result)
        if not isinstance(result, dict):
            raise ValueError('Expected JSON object')
        return result

    def digest(self, file):
        self.read(file)
        return self.files[str(Path(os.path.abspath(file)))]['sha256']

    def unchanged(self):
        failures = []
        for item in self.files.values():
            try:
                if sha_bytes(safe_bytes(item['path'])) != item['sha256']:
                    failures.append(item['path'])
            except (ValueError, OSError):
                failures.append(item['path'])
        return failures

def relative_path(value):
    if not isinstance(value, str) or not value or any((c in value for c in '\\:\x00')) or any((p in ('', '.', '..') for p in value.split('/'))):
        raise ValueError('Unsafe relative input path')
    return value

def indexed(records, key):
    if not isinstance(records, list):
        raise ValueError('Expected array')
    result = {}
    for item in records:
        identifier = key(item)
        if identifier in result:
            raise ValueError('Duplicate identity: ' + str(identifier))
        result[identifier] = item
    return result

def run_key(record):
    selection = record['selection']
    if set(selection) != {'kind', 'id'} or selection['kind'] not in ('case', 'combination'):
        raise ValueError('Invalid selection')
    return (record['state'], selection['kind'], selection['id'])

def source_binding(snapshot, case_dir, contract):
    names = ['contract.json', 'prompt.txt', 'reference-requests.json', *contract['modelStates'], *contract['attachments']]
    for name in names:
        relative_path(name)
        if Path(name).name in GENERATED:
            raise ValueError('Generated evidence cannot be authored source')
    files = [{'path': name, 'sha256': snapshot.digest(case_dir / name)} for name in sorted(set(names), key=lambda value: value.encode('utf-8'))]
    manifest = {'schemaVersion': 1, 'files': files}
    digest = sha_bytes(json.dumps(manifest, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    private = ['contract.json', 'reference-requests.json', *contract['modelStates']]
    return (digest, manifest, {name: snapshot.digest(case_dir / name) for name in private})

def locate_binary(root, explicit):
    if explicit:
        return Path(os.path.abspath(explicit))
    candidates = [Path(p) / 'openseespylinux/opensees.so' for p in sys.path if p]
    candidates += sorted((root / '.bench-work/venv').glob('lib/python*/site-packages/openseespylinux/opensees.so'))
    for file in candidates:
        if file.is_file():
            return file
    raise ValueError('Native binary unavailable for byte binding; supply --native-binary PATH (no import is attempted)')

def supported_model(model):
    check(set(model) <= {'schema_version', 'unit_system', 'coordinate_system', 'nodes', 'elements', 'materials', 'sections', 'load_cases', 'load_combinations', 'analysis_control', 'metadata', 'stories'}, 'unsupported-model-fields')
    check(model.get('schema_version') == '2.2.0' and model.get('unit_system') == 'SI', 'supported-model-units')
    coordinate = model['coordinate_system']
    check(coordinate.get('semantics') == 'global-z-up' and coordinate.get('dimension') in ('2d', '3d') and (coordinate.get('dof_order') == ['ux', 'uy', 'uz', 'rx', 'ry', 'rz']), 'supported-coordinate-system')
    if coordinate['dimension'] == '2d':
        check(coordinate.get('plane') == 'xz', 'supported-planar-system')
    controls = model['analysis_control']
    for key in ('self_weight', 'rigid_floor', 'p_delta', 'rigid_offsets', 'construction_stage'):
        check(controls.get(key) is False, 'unsupported-physics-control', key)
    check(set(controls) <= {'self_weight', 'rigid_floor', 'p_delta', 'rigid_offsets', 'construction_stage'}, 'unsupported-extra-control')
    for element in model['elements']:
        check(element['type'] in ('beam', 'column', 'truss', 'brace'), 'unsupported-element-type')
        check(set(element) <= {'id', 'name', 'type', 'nodes', 'material', 'section', 'rotation_angle'}, 'unsupported-element-fields')
    for node in model['nodes']:
        check(set(node) <= {'id', 'name', 'x', 'y', 'z', 'restraints'}, 'unsupported-node-fields')
        check(len(node['restraints']) == 6 and all((type(v) is bool for v in node['restraints'])), 'supported-restraints')
    for material in model['materials']:
        check(set(material) <= {'id', 'name', 'type', 'E', 'G', 'nu', 'rho'} and material.get('type') in ('steel', 'concrete', 'elastic', 'isotropic'), 'supported-material')
    for case in model['load_cases']:
        for load in case['loads']:
            allowed = {'id', 'type', 'node', 'reference_frame', 'fx', 'fy', 'fz', 'mx', 'my', 'mz'} if load['type'] == 'nodal' else {'id', 'type', 'element', 'reference_frame', 'wx', 'wy', 'wz', 'start', 'end'}
            check(load['type'] in ('nodal', 'distributed') and set(load) <= allowed, 'unsupported-load-physics')

def add(a, b):
    return [x + y for (x, y) in zip(a, b)]

def sub(a, b):
    return [x - y for (x, y) in zip(a, b)]

def mul(a, t):
    return [x * t for x in a]

def dot(a, b):
    return sum((x * y for (x, y) in zip(a, b)))

def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]

def unit(a):
    return mul(a, 1 / math.sqrt(dot(a, a)))

def check(ok, code, detail=''):
    counts[code] += 1
    if not ok:
        errors.append({'case': cid, 'run': runlabel, 'check': code, 'detail': str(detail)[:250]})

def near(a, b, code, atol=1e-09, rtol=2e-10):
    if isinstance(a, (list, tuple)):
        check(len(a) == len(b), code + '-shape')
        for (x, y) in zip(a, b):
            near(x, y, code, atol, rtol)
    else:
        delta = abs(a - b)
        maxima[code] = max(maxima[code], delta)
        check(math.isfinite(a) and math.isfinite(b) and (delta <= atol + rtol * abs(b)), code, [a, b, delta])

def sixresult(force, xyz):
    return force[:3] + add(force[3:], cross(xyz, force[:3]))

def consistent_point_loads(axes, length, loads):
    """Virtual work of retained point forces in linear/cubic beam shape functions.

    Local slopes are rz for y deflection and -ry for z deflection. This
    independent closed-form calculation does not call the native converter.
    """
    result = [0.0] * 12
    for load in loads:
        t = load['fraction']
        force = [dot(axis, load['globalForce']) for axis in axes]
        shape = [1 - 3*t*t + 2*t*t*t, length*(t - 2*t*t + t*t*t),
                 3*t*t - 2*t*t*t, length*(-t*t + t*t*t)]
        result[0] += force[0] * (1 - t)
        result[6] += force[0] * t
        for component, indices, signs in [(1, (1, 5, 7, 11), (1, 1, 1, 1)),
                                           (2, (2, 4, 8, 10), (1, -1, 1, -1))]:
            for index, sign, value in zip(indices, signs, shape):
                result[index] += sign * force[component] * value
    return result

def elastic_local_response(displacements, axes, properties, length, truss, loads):
    """Local resisting ends = elastic response minus consistent applied loads.

    The axial and torsional strains are endpoint differences. Euler-Bernoulli
    bending follows slope-deflection (4EI/L and 2EI/L), with end rotations
    measured relative to the displaced chord. This also checks unrequested
    node translations/rotations, which equilibrium alone cannot determine.
    """
    if len(displacements) != 12 or length <= 0 or not math.isfinite(length):
        raise ValueError('Invalid constitutive segment dimensions')
    required = ('E', 'A') if truss else ('E', 'A', 'G', 'J', 'Iy', 'Iz')
    if any(not math.isfinite(properties[k]) or properties[k] <= 0 for k in required):
        raise ValueError('Constitutive properties must be finite and positive')
    local = [dot(axis, displacements[offset:offset+3])
             for offset in (0, 3, 6, 9) for axis in axes]
    force = [0.0] * 12
    axial = properties['E'] * properties['A'] / length * (local[6] - local[0])
    force[0], force[6] = -axial, axial
    if truss:
        if loads:
            raise ValueError('Constitutive truss member loads are unsupported')
        return force
    torsion = properties['G'] * properties['J'] / length * (local[9] - local[3])
    force[3], force[9] = -torsion, torsion
    for inertia, displacement, rotation, sign in [('Iz', 1, 5, 1), ('Iy', 2, 4, -1)]:
        chord = (local[displacement+6] - local[displacement]) / length
        a, b = sign*local[rotation] - chord, sign*local[rotation+6] - chord
        stiffness = properties['E'] * properties[inertia] / length
        m1, m2 = stiffness * (4*a + 2*b), stiffness * (2*a + 4*b)
        force[displacement], force[displacement+6] = (m1+m2)/length, -(m1+m2)/length
        force[rotation], force[rotation+6] = sign*m1, sign*m2
    return sub(force, consistent_point_loads(axes, length, loads))

def audit_physics(receipt, rawdoc, checks):
    """Reconstruct axes, constants, load work and equilibrium without the driver.

Uniform-load power moments 0 through 3 exactly check cubic beam virtual
work. Independently reconstructed elastic segment actions check every saved
endpoint displacement, then raw forces assemble into nodal reactions."""
    global runlabel
    for run in rawdoc['runs']:
        runlabel = [run['state'], run['selection']]
        counts['runs'] += 1
        m = next((s['model'] for s in receipt['states'] if s['state'] == run['state']))
        r = run['responses']
        p = r['nativeInput']
        N = {n['id']: n for n in m['nodes']}
        E = {e['id']: e for e in m['elements']}
        M = {v['id']: v for v in m['materials']}
        S = {v['id']: v for v in m['sections']}
        check(r['analysisReturnCode'] == 0, 'return-code')
        factors = {run['selection']['id']: 1} if run['selection']['kind'] == 'case' else next((c['factors'] for c in m['load_combinations'] if c['id'] == run['selection']['id']))
        check(factors == run['factors'], 'selection-factors')
        frame_nodes = {n for e in E.values() if e['type'] not in ('truss', 'brace') for n in e['nodes']}
        check(len({n['tag'] for n in p['nodes'].values()}) == len(p['nodes']), 'unique-node-tags')
        check(len({s['tag'] for s in p['segments']}) == len(p['segments']), 'unique-element-tags')
        check(set(p['members']) == set(E), 'member-set')
        axes = {}
        lengths = {}
        starts = {}
        properties = {}
        nodal = collections.defaultdict(lambda : [0.0] * 6)
        expected = [0.0] * 6
        for (nid, n) in N.items():
            q = p['nodes'][nid]
            near(q['xyz'], [n[k] for k in 'xyz'], 'authored-xyz')
            fixed = n['restraints'][:]
            if nid not in frame_nodes:
                fixed[3:] = [True] * 3
            check(q['fixed'] == fixed, 'effective-restraints', nid)
        for (eid, e) in E.items():
            (a, b) = ([N[n][k] for k in 'xyz'] for n in e['nodes'])
            v = sub(b, a)
            L = math.sqrt(dot(v, v))
            x = unit(v)
            if m['coordinate_system']['dimension'] == '2d':
                y = [0.0, 1.0, 0.0]
            elif e['type'] in ('truss', 'brace'):
                z = [0.0, 0.0, 1.0] if abs(x[2]) < 0.9 else [0.0, 1.0, 0.0]
                y = unit(cross(z, x))
            else:
                y = unit(cross(m['metadata']['elementReferenceVectors'][eid], x))
            z = cross(x, y)
            angle = math.radians(e.get('rotation_angle', 0))
            (c, s) = (math.cos(angle), math.sin(angle))
            ax = [x, add(mul(y, c), mul(z, s)), sub(mul(z, c), mul(y, s))]
            axes[eid] = ax
            lengths[eid] = L
            starts[eid] = a
            plan = p['members'][eid]
            near(plan['length'], L, 'member-length')
            check(plan['element'] == e, 'native-member-definition')
            if e['type'] not in ('truss', 'brace'):
                near(plan['axes'], ax, 'member-axes')
            prop = {'E': M[e['material']]['E'] * 1000, 'A': S[e['section']]['properties']['A']}
            if e['type'] not in ('truss', 'brace'):
                prop.update(G=M[e['material']]['G'] * 1000, **{k: S[e['section']]['properties'][k] for k in ['Iy', 'Iz', 'J']})
            check(set(prop) == set(plan['properties']), 'property-keys')
            for (k, v) in prop.items():
                near(plan['properties'][k], v, 'property-' + k)
            properties[eid] = prop
            segs = sorted((s for s in p['segments'] if s['member'] == eid), key=lambda s: s['start'])
            near(segs[0]['start'], 0, 'segment-cover')
            near(segs[-1]['end'], L, 'segment-cover')
            check(segs[0]['nodes'][0] == e['nodes'][0] and segs[-1]['nodes'][1] == e['nodes'][1], 'segment-authored-ends')
            for (i, seg) in enumerate(segs):
                check(seg['end'] > seg['start'], 'segment-positive')
                if i:
                    near(seg['start'], segs[i - 1]['end'], 'segment-cover')
                    check(seg['nodes'][0] == segs[i - 1]['nodes'][1], 'segment-connected')
                for (where, nid) in zip(['start', 'end'], seg['nodes']):
                    near(p['nodes'][nid]['xyz'], add(a, mul(x, seg[where])), 'segment-xyz')
            for (pos, nid) in plan['stationNodes']:
                near(p['nodes'][nid]['xyz'], add(a, mul(x, pos)), 'station-xyz')
        distributed = []
        for case in m['load_cases']:
            factor = factors.get(case['id'], 0)
            for load in case['loads']:
                check(load['reference_frame'] == 'global', 'supported-source-load-frame')
                if load['type'] == 'nodal':
                    f = [load.get(k, 0) * factor for k in ['fx', 'fy', 'fz', 'mx', 'my', 'mz']]
                    nodal[load['node']] = add(nodal[load['node']], f)
                    expected = add(expected, sixresult(f, [N[load['node']][k] for k in 'xyz']))
                elif load['type'] == 'distributed':
                    eid = load['element']
                    lo = load.get('start', 0)
                    hi = load.get('end', lengths[eid])
                    q = [load.get(k, 0) * factor for k in ['wx', 'wy', 'wz']]
                    distributed.append((eid, lo, hi, q))
                    f = mul(q, hi - lo)
                    xyz = add(starts[eid], mul(axes[eid][0], (lo + hi) / 2))
                    expected = add(expected, f + cross(xyz, f))
                else:
                    check(False, 'unsupported-source-load-type', load['type'])
        actualnodal = collections.defaultdict(lambda : [0.0] * 6)
        for l in p['nodalLoads']:
            actualnodal[l['node']] = add(actualnodal[l['node']], l['values'])
        for nid in set(nodal) | set(actualnodal):
            near(actualnodal[nid], nodal[nid], 'nodal-load')
        for (nid, n) in p['nodes'].items():
            if nid not in N:
                check(n['fixed'] == ([False, True, False, True, False, True] if p['dimension'] == '2d' else [False] * 6), 'inserted-restraints')
            for (fixed, disp) in zip(n['fixed'], r['nodes'][nid]['displacement']):
                if fixed:
                    near(disp, 0, 'fixed-displacement', 1e-12, 0)
        assembly = {n: [0.0] * 6 for n in p['nodes']}
        elementApplied = {s['tag']: [0.0] * 6 for s in p['segments']}
        for seg in p['segments']:
            eid = seg['member']
            (a, b) = (seg['start'], seg['end'])
            pts = [l for l in p['pointLoads'] if l['elementTag'] == seg['tag']]
            for k in range(4):
                exact = [0.0] * 3
                for (mid, lo, hi, q) in distributed:
                    (low, high) = (max(a, lo), min(b, hi))
                    if mid == eid and high > low:
                        exact = add(exact, mul(q, (high ** (k + 1) - low ** (k + 1)) / (k + 1)))
                actual = [sum((l['globalForce'][i] * (a + l['fraction'] * (b - a)) ** k for l in pts)) for i in range(3)]
                near(actual, exact, 'load-work-moment-' + str(k), 1e-08, 5e-12)
            for l in pts:
                check(0 < l['fraction'] < 1, 'gauss-interior')
                near(l['localForce'], [dot(v, l['globalForce']) for v in axes[eid]], 'pointload-axes')
                xyz = add(starts[eid], mul(axes[eid][0], a + l['fraction'] * (b - a)))
                near(l['xyz'], xyz, 'pointload-position')
                elementApplied[seg['tag']] = add(elementApplied[seg['tag']], l['globalForce'] + cross(xyz, l['globalForce']))
            out = r['elements'][str(seg['tag'])]
            gf = out['globalForce']
            total = elementApplied[seg['tag']]
            truss = E[eid]['type'] in ('truss', 'brace')
            displacements = [value for nid in seg['nodes'] for value in r['nodes'][nid]['displacement']]
            elastic = elastic_local_response(displacements, axes[eid], properties[eid], b-a, truss, pts)
            # Existing source load-work moments bind all Hermite coefficients;
            # the constitutive comparison therefore checks the authored loads,
            # not just the retained load plan's declared resultant.
            if truss:
                axial = out['axialForce']
                near(axial, elastic[6], 'constitutive-truss-axial', 1e-06, 1e-09)
                near(gf, mul(axes[eid][0], -axial) + [0] * 3 + mul(axes[eid][0], axial) + [0] * 3, 'raw-truss-axial', 1e-07, 1e-10)
            else:
                near(out['localForce'], elastic, 'constitutive-beam-end-force', 1e-06, 1e-09)
            counts['constitutive-segments'] += 1
            for (j, nid) in enumerate(seg['nodes']):
                force = gf[6 * j:6 * j + 6]
                assembly[nid] = add(assembly[nid], force)
                total = add(total, sixresult(force, p['nodes'][nid]['xyz']))
                if 'localForce' in out:
                    localforce = out['localForce'][6 * j:6 * j + 6]
                    rotated = [sum((localforce[v + offset] * axes[eid][v][i] for v in range(3))) for offset in (0, 3) for i in range(3)]
                    near(force, rotated, 'raw-force-axes', 1e-07, 1e-10)
            near(total, [0] * 6, 'element-equilibrium', 1e-06, 0)
        reaction = [0.0] * 6
        free = 0.0
        for (nid, n) in p['nodes'].items():
            node = r['nodes'][nid]
            near(sub(assembly[nid], actualnodal[nid]), node['reaction'], 'node-equilibrium', 1e-07, 1e-10)
            reaction = add(reaction, sixresult(node['reaction'], n['xyz']))
            free = max(free, max((abs(v) for (v, f) in zip(node['reaction'], n['fixed']) if not f), default=0))
        ck = next((c['checks'] for c in checks['runs'] if c['state'] == run['state'] and c['selection'] == run['selection']))
        scales = [0.0] * 6
        for load in p['nodalLoads']:
            scales = add(scales, [abs(v) for v in sixresult(load['values'], p['nodes'][load['node']]['xyz'])])
        for load in p['pointLoads']:
            scales = add(scales, [abs(v) for v in load['globalForce'] + cross(load['xyz'], load['globalForce'])])
        bounds = [1e-08 + 1e-07 * max(1.0, value) for value in scales]
        near(ck['balanceTolerance'], bounds, 'equilibrium-tolerance-policy', 1e-16, 1e-12)
        check(ck.get('equilibriumPassed') is True and ck.get('method') == 'native-openseespy', 'equilibrium-success')
        balance = add(expected, reaction)
        near(balance, ck['forceMomentBalance'], 'source-equilibrium-reported', 1e-08, 0)
        check(all((abs(v) <= t for (v, t) in zip(balance, ck['balanceTolerance']))), 'source-equilibrium-frozen-bounds', balance)
        near(free, ck['freeResidual'], 'free-residual-reported')
        check(free <= max(bounds), 'free-residual-policy')

def saved_quantity(raw, request):
    """Extract requested components from saved vectors, independently of the driver."""
    dofs = ['ux', 'uy', 'uz', 'rx', 'ry', 'rz']
    actions = ['N', 'V2', 'V3', 'T', 'M2', 'M3']
    forces = ['fx', 'fy', 'fz', 'mx', 'my', 'mz']
    (location, component, plan) = (request['location'], request['component'], raw['nativeInput'])
    if location['kind'] == 'node':
        node = raw['nodes'][location['id']]
        value = node['displacement'][dofs.index(component)] if component in dofs else node['reaction'][forces.index(component.lower())]
    elif location['kind'] == 'member':
        member = plan['members'][location['id']]
        (x, length) = (location['positionM'], member['length'])
        tolerance = 32 * sys.float_info.epsilon * max(1, length)
        if not 0 <= x <= length + tolerance or location['side'] not in ('left', 'right'):
            raise ValueError('Invalid requested member station/side')
        truss = member['element']['type'] in ('truss', 'brace')
        if component in dofs:
            index = dofs.index(component)
            if truss:
                if index >= 3:
                    raise ValueError('Truss rotation is not a physical output')
                (a, b) = [raw['nodes'][n]['displacement'][index] for n in member['element']['nodes']]
                value = a + (b - a) * x / length
            else:
                (station, node) = min(member['stationNodes'], key=lambda item: abs(item[0] - x))
                if abs(station - x) > tolerance:
                    raise ValueError('Observation station absent from actual native mesh')
                value = raw['nodes'][node]['displacement'][index]
        else:
            segments = sorted((s for s in plan['segments'] if s['member'] == location['id'] and s['start'] - tolerance <= x <= s['end'] + tolerance), key=lambda s: s['start'])
            segment = segments[0] if location['side'] == 'left' else segments[-1]
            response = raw['elements'][str(segment['tag'])]
            if truss:
                value = response['axialForce'] if component == 'N' else 0.0
            else:
                at_start = abs(x - segment['start']) <= tolerance
                if not at_start and abs(x - segment['end']) > tolerance:
                    raise ValueError('Beam action is not at a retained native segment end')
                index = actions.index(component)
                sign = [-1, 1, 1, -1, -1, -1][index] * (1 if at_start else -1)
                value = sign * response['localForce'][index + (0 if at_start else 6)]
    else:
        raise ValueError('Unsupported quantity location')
    if component in dofs[:3]:
        units = {'m': 1, 'mm': 0.001, 'cm': 0.01}
    elif component in dofs[3:]:
        units = {'rad': 1, 'mrad': 0.001, 'deg': math.pi / 180}
    elif component in ('N', 'V2', 'V3', 'fx', 'fy', 'fz', 'Fx', 'Fy', 'Fz'):
        units = {'kN': 1, 'N': 0.001, 'MN': 1000}
    else:
        units = {'kN.m': 1, 'N.m': 0.001, 'kN.mm': 0.001, 'N.mm': 1e-06, 'MN.m': 1000}
    return value / units[request['unit'].replace('·', '.').replace('*', '.')]

def audit_case(root, native_root, independent_root, case_id, snapshot, binary):
    global errors, counts, maxima, cid, runlabel
    errors = []
    counts = collections.Counter()
    maxima = collections.defaultdict(float)
    (cid, runlabel) = (case_id, 'bindings')
    result = {'caseId': case_id, 'pass': False, 'nativeVerified': False, 'accepted': False, 'sourceHash': None, 'independentReferenceSha256': None, 'nativeReferenceSha256': None, 'artifacts': [], 'runs': [], 'solver': None}
    case_dir = root / 'corpora/research-300/cases' / case_id
    native_dir = native_root / case_id
    try:
        contract = snapshot.document(case_dir / 'contract.json')
        check(contract['id'] == cid, 'case-identity')
        (source_hash, manifest, input_hashes) = source_binding(snapshot, case_dir, contract)
        result.update(sourceHash=source_hash, sourceManifest=manifest, plannedEngine=contract['plannedEngine'])
        ref = snapshot.document(native_dir / 'native-opensees-reference.json')
        result['nativeReferenceSha256'] = snapshot.digest(native_dir / 'native-opensees-reference.json')
        for (field, expected) in [('id', cid), ('schemaVersion', 1), ('sourceHash', source_hash), ('sourceManifest', manifest), ('inputHashes', input_hashes), ('referenceKind', 'native-opensees'), ('method', 'native-openseespy')]:
            check(ref.get(field) == expected, 'native-source-' + field)
        expected_role = 'same-engine-candidate' if contract['plannedEngine'] == 'OpenSees' else 'cross-engine-diagnostic'
        check(ref.get('nativeRole') == expected_role, 'native-role')
        result['nativeRole'] = expected_role
        artifacts = indexed(ref['artifacts'], lambda item: item['path'])
        check(set(artifacts) == set(RAW_FILES), 'raw-manifest-files')
        receipts = {}
        for name in RAW_FILES:
            digest = snapshot.digest(native_dir / name)
            result['artifacts'].append({'path': name, 'sha256': digest})
            check(artifacts.get(name, {}).get('sha256') == digest, 'raw-sha', name)
            receipts[name] = snapshot.document(native_dir / name)
            check(receipts[name].get('schemaVersion') == 1 and receipts[name].get('id') == cid, 'receipt-identity', name)
        (receipt, solver_receipt, rawdoc, checks) = (receipts[name] for name in RAW_FILES)
        for (field, expected) in [('sourceHash', source_hash), ('sourceManifest', manifest), ('inputHashes', input_hashes)]:
            check(receipt.get(field) == expected, 'input-source-' + field)
        solver = ref['solver']
        result['solver'] = solver
        if not isinstance(solver, dict):
            raise ValueError('Solver metadata must be an object')
        check(solver == solver_receipt.get('solver'), 'solver-receipt-binding')
        check(solver.get('module') in ('openseespy.opensees', 'openseespylinux.opensees'), 'solver-module')
        check(isinstance(solver.get('version'), str) and bool(re.fullmatch('\\d+\\.\\d+(?:\\.\\d+)*(?:[-+].*)?', solver['version'])), 'solver-version')
        for (field, name) in [('runnerSha256', 'opensees_native.py'), ('referenceIoSha256', 'reference_io.py')]:
            check(snapshot.digest(root / 'scripts/research300' / name) == solver.get(field), 'source-code-sha', name)
        check(binary is not None, 'native-binary-available')
        if binary is not None:
            check(snapshot.digest(binary) == solver.get('nativeBinarySha256'), 'native-binary-sha')
            check(solver.get('nativeBinaryModule') == 'openseespylinux.opensees', 'native-binary-module')
            module_file = binary if solver['module'] == 'openseespylinux.opensees' else binary.parent.parent / 'openseespy/opensees/__init__.py'
            check(snapshot.digest(module_file) == solver.get('nativeModuleSha256'), 'native-wrapper-sha')
        check(solver_receipt.get('analysis') == 'Linear elastic static', 'supported-analysis')
        check(solver_receipt.get('units') == {'length': 'm', 'force': 'kN', 'modulusInput': 'MPa', 'rotation': 'rad'}, 'solver-units')
        if independent_root is not None:
            file = independent_root / cid / 'independent-reference.json'
            independent = snapshot.document(file)
            result['independentReferenceSha256'] = snapshot.digest(file)
            for (field, expected) in [('id', cid), ('sourceHash', source_hash), ('inputHashes', input_hashes)]:
                check(independent.get(field) == expected, 'independent-source-' + field)
        requests = snapshot.document(case_dir / 'reference-requests.json')
        states = indexed(receipt['states'], lambda item: item['state'])
        requested = indexed(requests['states'], lambda item: item['state'])
        check(set(states) == set(requested) == set(range(1, len(contract['modelStates']) + 1)), 'state-coverage')
        expected_runs = {}
        for (state, request) in requested.items():
            model_name = contract['modelStates'][state - 1]
            check(request['model'] == model_name and states[state]['modelPath'] == model_name, 'state-model-path')
            model = snapshot.document(case_dir / model_name)
            check(states[state]['model'] == model, 'retained-model-current')
            supported_model(model)
            for quantity in request['quantities']:
                key = run_key({'state': state, 'selection': quantity['selection']})
                expected_runs[key] = {'state': state, 'selection': quantity['selection'], 'modelSha256': snapshot.digest(case_dir / model_name)}
        raw_runs = indexed(rawdoc['runs'], run_key)
        check_runs = indexed(checks['runs'], run_key)
        reference_checks = indexed(ref['checks'], run_key)
        reference_states = indexed(ref['states'], lambda item: item['state'])
        check(set(reference_states) == set(requested), 'reference-state-coverage')
        for state, request in requested.items():
            saved_state = reference_states[state]
            check(saved_state.get('model') == request['model'], 'reference-state-model')
            nested_checks = indexed(saved_state['checks'], lambda item: run_key({'state': state, 'selection': item['selection']}))
            expected_checks = {key: {name: value for name, value in item.items() if name != 'state'}
                               for key, item in reference_checks.items() if key[0] == state}
            check(nested_checks == expected_checks, 'reference-state-checks-binding')
        check(set(raw_runs) == set(check_runs) == set(reference_checks) == set(expected_runs), 'run-selection-coverage')
        if not (set(raw_runs) == set(check_runs) == set(reference_checks) == set(expected_runs)):
            raise ValueError('Raw/check/reference run identities do not cover exactly the requested selections')
        for (key, expected) in expected_runs.items():
            raw = raw_runs[key]['responses']
            plan = raw['nativeInput']
            check(raw.get('analysisReturnCode') == 0, 'analysis-return-code')
            check(raw.get('runtime') == {'module': solver['module'], 'version': solver['version']}, 'raw-runtime')
            check(check_runs[key]['checks'] == {k: v for (k, v) in reference_checks[key].items() if k not in ('state', 'selection')}, 'raw-check-reference-binding')
            check(plan.get('nativeNdm') == 3 and plan.get('nativeNdf') == 6 and (plan.get('addedMass') == 0), 'native-domain')
            check(set(plan['nodes']) == set(raw['nodes']), 'raw-node-map')
            check({str(s['tag']) for s in plan['segments']} == set(raw['elements']), 'raw-element-map')
            check(set(plan['nodes']) == {n for s in plan['segments'] for n in s['nodes']}, 'connected-native-node-set')
            segment_tags = {s['tag'] for s in plan['segments']}
            check(all((p['elementTag'] in segment_tags for p in plan['pointLoads'])), 'native-load-segment-identity')
            for (node_id, node) in raw['nodes'].items():
                check(node['tag'] == plan['nodes'][node_id]['tag'], 'raw-node-tag')
                check(len(node['displacement']) == len(node['reaction']) == 6, 'raw-node-vector-shape')
            for element in raw['elements'].values():
                check(len(element['globalForce']) == 12, 'raw-global-force-shape')
                if 'localForce' in element:
                    check(len(element['localForce']) == 12, 'raw-local-force-shape')
                else:
                    check(isinstance(element.get('axialForce'), (int, float)), 'raw-axial-force')
            result['runs'].append(dict(expected, analysisReturnCode=raw['analysisReturnCode'], runtime=raw['runtime']))
        for (state, request) in requested.items():
            key_for_quantity = lambda item: (item['id'], item['selection']['kind'], item['selection']['id'])
            expected_quantities = indexed(request['quantities'], key_for_quantity)
            quantities = indexed(reference_states[state]['quantities'], key_for_quantity)
            check(set(quantities) == set(expected_quantities), 'raw-quantity-coverage')
            for (key, q) in expected_quantities.items():
                saved = quantities[key]
                for field in ('location', 'component', 'unit'):
                    check(saved[field] == q[field], 'raw-quantity-' + field)
                tolerance = q.get('tolerance', {'absolute': 1e-08, 'relative': 1e-06})
                check(saved.get('tolerance') == tolerance, 'raw-quantity-frozen-tolerance')
                raw = raw_runs[state, q['selection']['kind'], q['selection']['id']]['responses']
                actual = saved_quantity(raw, q)
                near(saved['value'], actual, 'raw-quantity-value', tolerance['absolute'], tolerance['relative'])
        audit_physics(receipt, rawdoc, checks)
    except (OSError, ValueError, KeyError, TypeError, IndexError, ZeroDivisionError, OverflowError, AttributeError, StopIteration) as exc:
        check(False, 'invalid-or-unreadable-input', f'{type(exc).__name__}: {exc}')
    result.update(errors=errors[:], counts=dict(counts), maxima=dict(maxima))
    result['pass'] = not errors and bool(result['runs'])
    return result

def protected_output(output, root, native_root, independent_root):
    output = Path(os.path.abspath(output))
    descriptor = directory_fd(output.parent)
    os.close(descriptor)
    for directory in [root / 'corpora', root / 'scripts', native_root, independent_root]:
        if directory is not None and (output == directory or directory in output.parents):
            raise ValueError('Output must be outside authored sources and evidence roots')
    if output.exists() or output.is_symlink():
        raise FileExistsError('Output already exists; no overwrite is permitted')
    for ancestor in output.parents:
        if (ancestor / 'backend/package.json').exists():
            raise ValueError('Output cannot be inside a SUT checkout')
    return output

def audit(root, native_root, independent_root=None, binary=None):
    snapshot = Snapshot()
    snapshot.read(Path(__file__))
    for directory in (root, native_root, independent_root):
        if directory is not None:
            descriptor = directory_fd(directory)
            os.close(descriptor)
    cases_dir = root / 'corpora/research-300/cases'
    descriptor = directory_fd(cases_dir)
    try:
        case_ids = sorted(os.listdir(descriptor))
    finally:
        os.close(descriptor)
    if not case_ids or any((not CASE_ID.fullmatch(case_id) for case_id in case_ids)):
        raise ValueError('Authored case directory must contain nonempty valid case IDs only')
    cases = [audit_case(root, native_root, independent_root, case_id, snapshot, binary) for case_id in case_ids]
    unstable = snapshot.unchanged()
    if unstable:
        for case in cases:
            case['pass'] = False
            case['errors'].append({'case': case['caseId'], 'run': 'snapshot', 'check': 'input-changed-during-audit', 'detail': unstable})
    summary = {'cases': len(cases), 'passed': sum((case['pass'] for case in cases)), 'failed': sum((not case['pass'] for case in cases)), 'runs': sum((len(case['runs']) for case in cases))}
    return {'schemaVersion': 1, 'reportKind': 'research-300-independent-native-physics-audit', 'valid': all((case['pass'] for case in cases)), 'nativeVerified': False, 'accepted': False, 'scope': 'Read-only input/raw physical audit; separate reference comparison and named reviewer decision required', 'reviewerCodeSha256': snapshot.digest(Path(__file__)), 'summary': summary, 'roots': {'benchmark': str(root), 'native': str(native_root), 'independent': str(independent_root) if independent_root else None}, 'snapshot': list(snapshot.files.values()), 'cases': cases}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path, help='Benchmark root containing corpus and pinned driver source')
    parser.add_argument('--native-root', required=True, type=Path, help='Retained native CASE directories')
    parser.add_argument('--independent-root', type=Path, help='Optional retained independent references to bind')
    parser.add_argument('--native-binary', type=Path, help='Exact installed OpenSees .so to hash; never imported')
    parser.add_argument('--output', required=True, type=Path, help='New report path with an existing parent; exclusive creation')
    args = parser.parse_args(argv)
    try:
        root = Path(os.path.abspath(args.root))
        native = Path(os.path.abspath(args.native_root))
        independent = Path(os.path.abspath(args.independent_root)) if args.independent_root else None
        output = protected_output(args.output, root, native, independent)
        try:
            binary = locate_binary(root, args.native_binary)
        except ValueError:
            binary = None
        report = audit(root, native, independent, binary)
        content = (json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
        descriptor = directory_fd(output.parent)
        try:
            file = os.open(output.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 420, dir_fd=descriptor)
            with os.fdopen(file, 'wb') as stream:
                stream.write(content)
        finally:
            os.close(descriptor)
        print(json.dumps({'output': str(output), 'valid': report['valid'], **report['summary']}))
        return 0 if report['valid'] else 1
    except (OSError, ValueError, TypeError) as exc:
        print(f'Native evidence audit error: {exc}', file=sys.stderr)
        return 2
if __name__ == '__main__':
    raise SystemExit(main())
