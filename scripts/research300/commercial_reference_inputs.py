"""Explicit, physically equivalent input representations for native references.

Only inactive story grouping and continuous beam subdivisions are added. The
caller must independently compare physical models before dispatch. This helper
is never supplied to, or used to repair the output of, a candidate agent.
"""
from copy import deepcopy
import math


def published_section_model(authored, public):
    """Use the released numeric properties as the reference's actual inputs.

    Display rounding is an input change, not a solver error tolerance. Accept
    only the predeclared 8-significant-digit display budget; preserve all other
    authored mechanics and reject missing, duplicate or changed properties.
    """
    model = deepcopy(authored)
    sections = public.get('sections', [])
    by_id = {s['id']: s for s in sections}
    if len(by_id) != len(sections) or set(by_id) != {s['id'] for s in model['sections']}:
        raise ValueError('Published section identities differ')
    for section in model['sections']:
        old, new = section['properties'], by_id[section['id']]['properties']
        if set(old) != set(new) or not {'A', 'Iy', 'Iz', 'J'} <= set(new):
            raise ValueError('Published property set differs')
        for key, value in new.items():
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or abs(value-old[key]) > 5e-8*abs(old[key])):
                raise ValueError('Published property exceeds frozen display precision: '+key)
        section['properties'] = deepcopy(new)
    return model


def execution_model(authored, engine):
    model = deepcopy(authored)
    if engine != 'YJK':
        return model
    nodes = {n['id']: n for n in model['nodes']}
    columns = [e for e in model['elements'] if e['type'] == 'column']
    if not model.get('stories'):
        levels = sorted({nodes[e['nodes'][0]]['z'] for e in columns} |
                        {max(n['z'] for n in model['nodes'])})
        if not levels or levels[0] != 0:
            raise ValueError('Native reference requires ground-based natural stories')
        model['stories'] = [{'id': f's{i+1}', 'elevation': a, 'height': b-a, 'rigid_diaphragm': False}
                            for i, (a, b) in enumerate(zip(levels, levels[1:]))]
    # The native inclined-column route introduces plan joints at the lower
    # endpoint XY on the upper floor. Make any resulting continuous beam cuts
    # explicit, so input audit can prove every physical member and line load.
    projected = []
    for e in columns:
        a, b = [nodes[n] for n in e['nodes']]
        if a['x'] != b['x'] or a['y'] != b['y']:
            projected.append((a['x'], a['y'], b['z']))
    segments, elements = {}, []
    for e in model['elements']:
        if e['type'] != 'beam':
            elements.append(e); continue
        a, b = [[nodes[n][k] for k in 'xyz'] for n in e['nodes']]
        direction = [v-u for u, v in zip(a, b)]; length2 = sum(v*v for v in direction)
        cuts = {}
        for point in projected:
            t = sum((v-u)*d for u, v, d in zip(a, point, direction))/length2
            if 1e-9 < t < 1-1e-9 and math.dist(point, [u+t*d for u, d in zip(a, direction)]) < 1e-9:
                cuts[t] = point
        if not cuts:
            elements.append(e); continue
        ids = [e['nodes'][0]]
        for i, (_, xyz) in enumerate(sorted(cuts.items())):
            if any(math.dist(xyz, [n[k] for k in 'xyz']) < 1e-9 for n in nodes.values()):
                raise ValueError('Subdivision would connect an existing independent node')
            nid = f"{e['id']}-reference-cut-{i+1}"
            node = {'id': nid, **dict(zip('xyz', xyz)), 'restraints': [False]*6}
            model['nodes'].append(node);nodes[nid] = node;ids.append(nid)
        ids.append(e['nodes'][1]);children = []
        for i, pair in enumerate(zip(ids, ids[1:])):
            child = {**e, 'id': f"{e['id']}-reference-segment-{i+1}", 'nodes': list(pair)}
            if any(k in e for k in ('releases', 'offsets', 'rigid_offsets')):
                raise ValueError('Cannot subdivide a member with end conditions')
            children.append(child);elements.append(child)
            refs = model['metadata']['elementReferenceVectors']
            refs[child['id']] = deepcopy(refs[e['id']])
        del model['metadata']['elementReferenceVectors'][e['id']]
        segments[e['id']] = [c['id'] for c in children]
    model['elements'] = elements
    for case in model['load_cases']:
        loads = []
        for load in case['loads']:
            children = segments.get(load.get('element'))
            if not children:
                loads.append(load);continue
            if (load['type'] != 'distributed'
                    or load.get('distribution', 'uniform') != 'uniform'
                    or load.get('variation', 'uniform') != 'uniform'
                    or any(k in load for k in ('start', 'end', 'position', 'points', 'segments'))
                    or any(k.endswith(('_start', '_end')) for k in load)):
                raise ValueError('Only full uniform beam loads can be subdivided here')
            loads.extend({**load, 'element': eid} for eid in children)
        case['loads'] = loads
    for floor in model.get('metadata', {}).get('floorAreaLoads', []):
        floor['members'] = [{**row, 'member': eid} for row in floor['members']
                            for eid in segments.get(row['member'], [row['member']])]
    return model
