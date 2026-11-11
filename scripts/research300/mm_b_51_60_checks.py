"""Source and mechanics checks for MM-051..060; never writes reference values.

The stiffness implementation is an independent diagnostic, not prescribed-engine
acceptance. Expected force/moment resultants below are integrated directly from
the planning source. No production converter, solver or result reader is used.
"""
from collections import Counter
import importlib.util
import json
import math
from pathlib import Path

from mm_b_51_60 import build_specs


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('/mnt/nas/qsz/01research/02structureclaw-bench/planning/sources')
if (ROOT / 'planning/sources').exists():
    SOURCE = ROOT / 'planning/sources'


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def close(actual, expected, label, absolute=1e-8):
    require(math.isclose(actual, expected, rel_tol=1e-10, abs_tol=absolute),
            f'{label}: actual {actual!r}, expected {expected!r}')


def source_review():
    ids = {f'MM-{i:03d}' for i in range(51, 61)}
    tasks = {r['id']: r for r in json.loads((SOURCE / 'all-tasks-engines-v2.json').read_text()) if r['id'] in ids}
    models = {r['taskId']: r for r in json.loads((SOURCE / 'all-models-engines-v2.json').read_text()) if r['taskId'] in ids}
    plan = json.loads((ROOT / 'planning/capability-coverage-300.json').read_text())
    rows = {r['id']: r for r in plan['cases'] if r['id'] in ids}
    require(set(tasks) == set(models) == set(rows) == ids, 'Missing source rows')
    for cid, row in rows.items():
        for key, value in row['sourceRequirements'].items():
            group, field = key.split('.', 1)
            source_row = tasks[cid] if group == 'task' else models[cid] if group == 'model' else tasks[cid]['enginePlan']
            require(source_row[field] == value, f'{cid}: retained source field differs: {key}')
        req_ids = [r['id'] for r in row['requirements']]
        require(len(req_ids) == len(set(req_ids)), f'{cid}: duplicate requirement IDs')
        require(all(r['sourceField'] in row['sourceRequirements'] for r in row['requirements']), f'{cid}: orphan source requirement')
    return rows


def expected_resultants():
    # Each tuple is (global Fx, global Fz, global My about the origin).
    # Positive My = z*Fx - x*Fz. Distributed loads use actual member length.
    roof_slope_length = math.hypot(9, 1.5)
    eave_length = math.hypot(2, 1/3)
    right_roof_length = math.hypot(6, 1.2)
    roof_moment_integral = 2*5.4*2.7 + 6*8.4 + right_roof_length*8.4
    return {
        51: {'D': (0, -6*(2*roof_slope_length+eave_length), 108*roof_slope_length+114*eave_length),
             'W': (0, 10*eave_length, -190*eave_length)},
        52: {'D': (15, -176, 2041)},
        53: {'D': (12, -128, 1096)},
        54: {'D': (0, -162, 2187), 'L': (0, -35, 584.5), 'W': (12, 0, 84)},
        55: {'D': (0, -792, 4536)},
        56: {'D': (10, -746, 7746)},
        57: {'D': (45, -300, 1980)},
        58: {'D': (50, -64, 456)},
        59: {'D': (0, -288, 864)},
        60: {'D': (0, -10*(16.8+right_roof_length), 10*roof_moment_integral),
             'L': (0, -8*(16.8+right_roof_length), 8*roof_moment_integral)},
    }


def validate_graph_and_requests(s):
    m = s['model']
    cid = s['id']
    number = int(cid[-3:])
    nodes = {n['id']: n for n in m['nodes']}
    elements = {e['id']: e for e in m['elements']}
    expected_sizes = {51: (6, 5), 52: (9, 8), 53: (6, 6), 54: (8, 7), 55: (9, 9),
                      56: (6, 5), 57: (12, 14), 58: (5, 4), 59: (7, 6), 60: (10, 11)}
    require((len(nodes), len(elements)) == expected_sizes[number], f'{cid}: physical graph size changed')
    require(len(nodes) == len(m['nodes']) and len(elements) == len(m['elements']), f'{cid}: duplicate graph IDs')
    require(not any(m['analysis_control'].values()), f'{cid}: unexpected analysis option enabled')
    require(all(n['y'] == 0 for n in nodes.values()), f'{cid}: node outside XZ plane')
    sections = {sec['id'] for sec in m['sections']}
    materials = {mat['id'] for mat in m['materials']}
    adjacency = {nid: set() for nid in nodes}
    lengths = {}
    for eid, element in elements.items():
        a, b = element['nodes']
        require(a in nodes and b in nodes and a != b, f'{cid}/{eid}: invalid endpoints')
        require(element['section'] in sections and element['material'] in materials, f'{cid}/{eid}: unresolved properties')
        lengths[eid] = math.dist([nodes[a][k] for k in ('x', 'y', 'z')], [nodes[b][k] for k in ('x', 'y', 'z')])
        require(lengths[eid] > 0, f'{cid}/{eid}: zero length')
        adjacency[a].add(b)
        adjacency[b].add(a)
    visited = set()
    pending = [next(iter(nodes))]
    while pending:
        nid = pending.pop()
        if nid not in visited:
            visited.add(nid)
            pending.extend(adjacency[nid] - visited)
    require(visited == set(nodes), f'{cid}: disconnected structural nodes')
    case_ids = {c['id'] for c in m['load_cases']}
    combinations = {c['id']: c['factors'] for c in m['load_combinations']}
    for combo, factors in combinations.items():
        require(set(factors) <= case_ids, f'{cid}/{combo}: unresolved load cases')
    seen_requests = set()
    for request in s['requests']:
        loc = request['location']
        selection = request.get('selection', {'kind': 'case', 'id': 'D'})
        key = (selection['kind'], selection['id'], request['id'])
        require(key not in seen_requests, f'{cid}: duplicate request key {key}')
        seen_requests.add(key)
        require(selection['id'] in (case_ids if selection['kind'] == 'case' else combinations), f'{cid}: unknown request selection')
        if loc['kind'] == 'node':
            require(loc['id'] in nodes, f'{cid}: unknown observation node')
        else:
            require(loc['id'] in elements, f'{cid}: unknown observation member')
            require(-1e-10 <= loc['positionM'] <= lengths[loc['id']]+1e-10, f'{cid}: station outside member')
            require(loc['side'] in ('left', 'right'), f'{cid}: missing station side')
        require('value' not in request, f'{cid}: numerical truth must not be authored')
    return nodes, elements, adjacency, lengths


def check_source_load_resultants(s, nodes, elements, lengths):
    cid = s['id']
    expected = expected_resultants()[int(cid[-3:])]
    require({c['id'] for c in s['model']['load_cases']} == set(expected), f'{cid}: basic case set differs from source')
    for case in s['model']['load_cases']:
        fx = fz = my = 0
        for load in case['loads']:
            require(load['reference_frame'] == 'global', f'{cid}: source loads must use global directions')
            if load['type'] == 'distributed':
                element = elements[load['element']]
                a, b = [nodes[nid] for nid in element['nodes']]
                length = lengths[element['id']]
                start, end = load.get('start', 0), load.get('end', length)
                require(0 <= start < end <= length, f'{cid}: distributed load interval is invalid')
                x = a['x'] + (b['x']-a['x'])*(start+end)/(2*length)
                z = a['z'] + (b['z']-a['z'])*(start+end)/(2*length)
                force_x = load.get('wx', 0)*(end-start)
                force_z = load.get('wz', 0)*(end-start)
                moment = z*force_x - x*force_z
            elif load['type'] == 'nodal':
                node = nodes[load['node']]
                force_x, force_z = load.get('fx', 0), load.get('fz', 0)
                moment = node['z']*force_x - node['x']*force_z + load.get('my', 0)
            else:
                raise AssertionError(f'{cid}: unexpected source load type {load["type"]}')
            fx += force_x
            fz += force_z
            my += moment
        for actual, target, component in zip((fx, fz, my), expected[case['id']], ('Fx', 'Fz', 'My')):
            close(actual, target, f'{cid}/{case["id"]} source load resultant {component}')


def check_distinctive_topology(s, nodes, elements, adjacency, lengths):
    i = int(s['id'][-3:])
    m = s['model']
    all_loads = [load for case in m['load_cases'] for load in case['loads']]
    if i == 51:
        close(nodes['E']['z'], 17/3, 'MM-051 continued roof slope')
        close(nodes['E']['x'], 20, 'MM-051 extension end')
        require({load['element'] for case in m['load_cases'] if case['id'] == 'W' for load in case['loads']} == {'RE'}, 'MM-051 wind extends beyond the specified zone')
        require({c['id']: c['factors'] for c in m['load_combinations']} == {'D': {'D': 1}, 'D+W': {'D': 1, 'W': 1}}, 'MM-051 combinations changed')
    elif i == 52:
        require(adjacency['M'] == {'P', 'Q'}, 'MM-052 midpoint must connect both roof halves')
        close(nodes['M']['x'], 11, 'MM-052 roof midpoint')
        require({eid: e['section'] for eid, e in elements.items()} == {'CAL': 'C1', 'CAU': 'C2', 'CBL': 'C1', 'CBU': 'C2', 'R1': 'B1', 'R2a': 'B2', 'R2b': 'B2', 'R3': 'B1'}, 'MM-052 column/roof section assignment changed')
        require(not nodes['AS']['restraints'][4] and not nodes['BS']['restraints'][4], 'MM-052 section boundary must not become a support')
    elif i == 53:
        require(elements['T']['nodes'] == ['AM', 'BM'], 'MM-053 intermediate beam omitted or misconnected')
        require(all(load.get('element') != 'T' for load in all_loads), 'MM-053 intermediate beam must remain unloaded')
        require(not nodes['A0']['restraints'][4] and nodes['B0']['restraints'][4], 'MM-053 pin/fixed boundary mismatch')
    elif i == 54:
        require(elements['CB']['section'] == 'C2' and elements['OL']['section'] == elements['OR']['section'] == 'B2', 'MM-054 member roles changed')
        require({c['id']: c['factors'] for c in m['load_combinations']} == {'D+L': {'D': 1, 'L': 1}, 'D+W': {'D': 1, 'W': 1}}, 'MM-054 combination selection mismatch')
        require(all(not nodes[nid]['restraints'][k] for nid in ('EL', 'ER') for k in (0, 2, 4)), 'MM-054 free eave gained a support')
    elif i == 55:
        require(all(not (n['x'] == 0 and n['z'] > 3.6) for n in nodes.values()), 'MM-055 phantom upper-left frame')
        require(adjacency['M2'] == {'B2', 'C2'}, 'MM-055 midpoint disconnected')
        close(nodes['M2']['x'], 8, 'MM-055 upper midpoint')
    elif i == 56:
        require(elements['HC']['nodes'] == ['M', 'H'] and elements['HC']['section'] == 'C2', 'MM-056 hanging-column stiffness/connectivity changed')
        close(lengths['HC'], 3, 'MM-056 hanging-column length')
        require(all(not nodes['H']['restraints'][k] for k in (0, 2, 4)), 'MM-056 hanging end gained a restraint')
    elif i == 57:
        require(not any(set(e['nodes']) == {'B2', 'C2'} for e in elements.values()), 'MM-057 deleted beam reappeared')
        require(adjacency['C2'] == {'C1', 'C3'}, 'MM-057 continuous right column lost its floor node')
        require(any(load.get('node') == 'C2' and load.get('fx') == 15 for load in all_loads), 'MM-057 second-floor lateral load missing')
    elif i == 58:
        require(all(not nodes['E']['restraints'][k] for k in (0, 2, 4)), 'MM-058 free extension gained a restraint')
        require(any(load.get('node') == 'E' and load.get('fx') == 50 for load in all_loads), 'MM-058 force moved from free end')
        require(all(all(nodes[nid]['restraints']) for nid in ('A0', 'B0')), 'MM-058 final model lacks fixed bases')
        require('clarify' in s and s['clarify']['field'] == 'column-base-restraints', 'MM-058 required clarification missing')
    elif i == 59:
        require(elements['RR']['nodes'] == ['B1', 'C1'], 'MM-059 unloaded right span omitted')
        require(all(load.get('element') != 'RR' for load in all_loads), 'MM-059 right span gained a load')
        require(adjacency['M'] == {'A1', 'B1'}, 'MM-059 midpoint disconnected')
        close(nodes['M']['x'], 3, 'MM-059 left-span midpoint')
    elif i == 60:
        require(adjacency['M'] == {'B2', 'C2'}, 'MM-060 sloping-beam midpoint disconnected')
        close(lengths['B22a'], math.hypot(3, .6), 'MM-060 sloping half-beam actual length')
        close(nodes['M']['x'], 8.4, 'MM-060 midpoint X')
        close(nodes['M']['z'], 7.8, 'MM-060 midpoint Z')
        require(m['load_combinations'] == [dict(id='1.2D+1.4L', factors={'D': 1.2, 'L': 1.4})], 'MM-060 explicit factors changed')


def independent_equilibrium(s, solver):
    m = s['model']
    selections = {tuple(sorted(r.get('selection', {'kind': 'case', 'id': 'D'}).items())) for r in s['requests']}
    for selection_items in selections:
        selection = dict(selection_items)
        factors = ({selection['id']: 1} if selection['kind'] == 'case'
                   else next(c['factors'] for c in m['load_combinations'] if c['id'] == selection['id']))
        quantity, diagnostics = solver.solve(m, factors, [r['location'] for r in s['requests']])
        require(max(abs(v) for v in diagnostics['forceMomentBalance']) < 1e-7, f'{s["id"]}: independent global force/moment balance failed: {diagnostics}')
        for request in s['requests']:
            component = request['component']
            if request['location']['kind'] == 'node' and component[0].isupper():
                component = component.lower()
            value = quantity(request['location'], component)
            require(math.isfinite(value), f'{s["id"]}: nonfinite requested result')
        if s['id'] == 'MM-053':
            close(quantity({'kind': 'node', 'id': 'A0'}, 'my'), 0, 'MM-053 pinned-base reaction moment')
        if s['id'] == 'MM-056':
            left = quantity(dict(kind='member', id='RL', positionM=12, side='left'), 'M2')
            right = quantity(dict(kind='member', id='RR', positionM=0, side='right'), 'M2')
            # The free-end Fx=10 kN acts 3 m below the roof; joint moment jump
            # follows equilibrium independently of roof stiffness or deflection.
            close(abs(left-right), 10*3, 'MM-056 one-sided roof moment jump', absolute=1e-7)


def check_exported_contracts(rows):
    root = ROOT / 'corpora/research-300/cases'
    for cid, row in rows.items():
        folder = root / cid
        contract = json.loads((folder / 'contract.json').read_text())
        requests = json.loads((folder / 'reference-requests.json').read_text())
        require(contract['sourcePlan']['sourceRequirements'] == row['sourceRequirements'], f'{cid}: exported source text changed')
        covered = [rid for coverage in contract['requirementCoverage'] for rid in coverage['requirementIds']]
        require(Counter(covered) == Counter(r['id'] for r in row['requirements']), f'{cid}: numbered coverage omitted or duplicated')
        qs = requests['states'][0]['quantities']
        require(len({q['id'] for q in qs}) == len(qs), f'{cid}: exported request IDs collide')
        require(all('value' not in q for q in qs), f'{cid}: reference values authored in requests')
        require(contract['sameEngineTruthStatus'] == contract['inputBlindReview'] == 'pending', f'{cid}: unsupported acceptance claim')
    folder = root / 'MM-058'
    contract = json.loads((folder / 'contract.json').read_text())
    first, second = contract['turns']
    require(first['state'] is None and first['expectation'] == 'clarify', 'MM-058 first turn must clarify before analysis')
    require(second['state'] == 1 and second['expectation'] == 'analyze', 'MM-058 second turn must analyze supplied model')
    require(set(first['attachments']).isdisjoint(second['attachments']), 'MM-058 complete image exposed on first turn')
    for name in first['attachments']:
        if name.endswith(('.svg', '.json')):
            text = (folder / name).read_text()
            # The known out-of-plane planar constraint convention is allowed.
            # Reject actual per-node restraint records or visible in-plane support labels.
            require('FIXED' not in text and 'LOCK ' not in text and '"restraints"' not in text
                    and '"boundaryConditions"' not in text, f'MM-058 support leak in {name}')
    require(any('FIXED' in (folder / name).read_text() for name in second['attachments'] if name.endswith('.svg')), 'MM-058 completed drawing lacks support evidence')


def main():
    rows = source_review()
    module_spec = importlib.util.spec_from_file_location('mm_b_51_60_independent', ROOT / 'scripts/independent-frame-reference.py')
    solver = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(solver)
    specs = build_specs()
    require({s['id'] for s in specs} == set(rows), 'Authored case IDs differ from assigned batch')
    for s in specs:
        nodes, elements, adjacency, lengths = validate_graph_and_requests(s)
        check_source_load_resultants(s, nodes, elements, lengths)
        check_distinctive_topology(s, nodes, elements, adjacency, lengths)
        independent_equilibrium(s, solver)
        print(s['id'], 'PASS: source topology, load force/moment totals, stations and independent equilibrium')
    check_exported_contracts(rows)
    print('PASS: exported numbered coverage, unique requests, pending acceptance and MM-058 delayed supports')
    print('Diagnostic checks only. No numerical reference files written; prescribed-engine validation remains pending.')


if __name__ == '__main__':
    main()
