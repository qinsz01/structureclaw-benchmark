"""Export pending YJK native candidates from retained numerical evidence.

No structural solver, remote service, or language model is invoked. Every value
is obtained from a typed SDK array, with actual FE connectivity/axes and explicit
linear case factors. This never writes active corpus files or accepts a case.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import sys

try:
    from .yjk_results import cross, dot, unit, native_axes, sdk_endpoint_actions, vector
    from .. import reference_io
except ImportError:
    from yjk_results import cross, dot, unit, native_axes, sdk_endpoint_actions, vector
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import reference_io

DISPLACEMENTS = ('ux', 'uy', 'uz', 'rx', 'ry', 'rz')
REACTIONS = ('fx', 'fy', 'fz', 'mx', 'my', 'mz')
ACTIONS = ('N', 'V2', 'V3', 'T', 'M2', 'M3')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def fe_records(raw):
    records = {}; section = None
    for line in raw.decode('gb18030').splitlines():
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        if line.startswith('*'):
            section = line.split()[0]
            continue
        fields = dict(re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)=([^\s&]+)', line))
        if re.match(r'^\d+\s', line):
            records.setdefault(section, []).append((int(line.split()[0]), fields))
        elif section == '*FRAME' and records.get(section):
            records[section][-1][1].update(fields)
    return records


def numbers(text):
    result = [float(v) for v in text.split(',')]
    if any(not math.isfinite(v) for v in result):
        raise ValueError('Nonfinite native input')
    return result


def source_axes(model, element):
    nodes = {n['id']:n for n in model['nodes']}
    a, b = [[nodes[n][k] for k in 'xyz'] for n in element['nodes']]
    x = unit([v-u for u,v in zip(a,b)])
    ref = model['metadata']['elementReferenceVectors'][element['id']]
    y = unit(cross(ref,x)); z = cross(x,y)
    angle = math.radians(element.get('rotation_angle',0))
    return [x, [math.cos(angle)*a+math.sin(angle)*b for a,b in zip(y,z)],
            [-math.sin(angle)*a+math.cos(angle)*b for a,b in zip(y,z)]]


def endpoint_index(position, length):
    if position == 0:
        return 0
    # A geometric endpoint computed with a different norm implementation may
    # differ by a few representational ULPs; this is not a response tolerance.
    if abs(position-length) <= 8*max(math.ulp(position),math.ulp(length)):
        return 1
    raise ValueError('Only physically identified member end sections are qualified')


class PendingOutput(ValueError):
    """A numerical result exists but its output family is not yet qualified."""


class StateEvidence:
    def __init__(self, row, index_root, model, expected_model_hash):
        self.row = row; self.model = model
        if row['source_model_sha256'] != expected_model_hash:
            raise ValueError('Native source-model hash no longer matches authored numerical inputs')
        index_root = Path(index_root).resolve(); self.index_root = index_root
        self.project = index_root/row['project']; self.reading = index_root/row['reading']
        results_path = index_root/row.get('resultsPath',str((self.reading/'results.json').relative_to(index_root)))
        audit_paths = [index_root/name for name in row['audits']]
        bindings = row.get('artifacts')
        if not isinstance(bindings,list):
            raise ValueError('Native evidence needs frozen artifact SHA-256 bindings')
        expected = {}; snapshots = {}
        for binding in bindings:
            name = binding['path']; digest = binding['sha256']
            if name in expected or not re.fullmatch(r'[0-9a-f]{64}',digest):
                raise ValueError('Invalid or duplicate evidence hash binding')
            path = index_root/name
            if Path(name).is_absolute() or '..' in Path(name).parts or index_root not in path.resolve().parents:
                raise ValueError('Evidence path escapes the index root')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=digest:
                raise ValueError('Native evidence hash changed: '+name)
            snapshots[name] = raw
            expected[name] = digest
        required = [self.project/'input.json',self.project/'fea.dat',
                    self.project/'mapping.json',results_path,*audit_paths]
        for path in required:
            resolved = path.resolve()
            if index_root not in resolved.parents:
                raise ValueError('Evidence path escapes the index root')
            name = str(path.relative_to(index_root))
            if name not in expected:
                raise ValueError('Native evidence hash changed or is unbound: '+name)
        def content(path):
            return snapshots[str(path.relative_to(index_root))]
        self.sdk = json.loads(content(results_path).decode('utf-8-sig'))
        self.mapping = json.loads(content(self.project/'mapping.json').decode('utf-8-sig'))
        self.source_nodes = {n['id']:n for n in model['nodes']}
        self.elements = {e['id']:e for e in model['elements']}
        self.fe = fe_records(content(self.project/'fea.dat'))
        self.nodes = {tag:numbers(v['C']) for tag,v in self.fe['*NODE']}
        self.frames = dict(self.fe['*FRAME'])
        self.artifacts = [{'path':name,'sha256':digest} for name,digest in expected.items()]
        audits = [json.loads(content(p).decode('utf-8-sig')) for p in audit_paths]
        if not audits or any(a['source_sha256'] != expected_model_hash for a in audits):
            raise ValueError('Missing or stale native input audit')
        for audit in audits:
            if audit.get('native_input_sha256',audit.get('native_fe_sha256')) != expected[str((self.project/'fea.dat').relative_to(index_root))]:
                raise ValueError('Input audit refers to a different native FE file')
            if audit.get('native_result_sha256') != expected[str(results_path.relative_to(index_root))]:
                raise ValueError('Input audit refers to different native results')
            if audit.get('representation_failures'):
                raise ValueError('Native input representation audit failed')
        first = audits[0]
        if 'source_member_segments' in first:
            self.node_map = first['source_node_map']; self.segments = first['source_member_segments']
        else:
            self.node_map = first['node_map']
            self.segments = {eid:[{'native_id':tag,'native_nodes':[int(x) for x in self.frames[tag]['N'].split(',')]}]
                             for eid,tag in first['frame_map'].items()}
        for nid, tag in self.node_map.items():
            if math.dist(self.nodes[tag],[self.source_nodes[nid][k] for k in 'xyz']) > 1e-10:
                raise ValueError('Audit node coordinates no longer match actual FE input')
        self.case_map = {}
        for item in self.mapping['load_cases']:
            if item['source_case'] in self.case_map:
                raise ValueError('Duplicate source load case in native mapping')
            found = [c for c in self.sdk['cases'] if c['name']==item['native_name']]
            if len(found) != 1:
                raise ValueError('Native case mapping is missing or ambiguous')
            if found[0]['analysis_case'] != item.get('native_kind'):
                raise ValueError('Native case number differs from source case mapping')
            self.case_map[item['source_case']] = found[0]

    def verify_unchanged(self):
        """Reject a changed file before publishing values from the frozen snapshot."""
        for binding in self.artifacts:
            if sha(self.index_root/binding['path']) != binding['sha256']:
                raise ValueError('Native evidence changed during export: '+binding['path'])

    def single_case(self, quantity, case_id):
        case = self.case_map[case_id]; loc = quantity['location']; comp = quantity['component']
        trace = {'sourceCase':case_id,'nativeCaseName':case['name'],
                 'nativeDesignCase':case['id'],'nativeAnalysisCase':case['analysis_case']}
        if loc['kind']=='node':
            tag = self.node_map[loc['id']]; values = case['nodes'][str(tag)]
            lower = comp.lower()
            if lower in DISPLACEMENTS:
                field = 'displacement'; index = DISPLACEMENTS.index(lower); method = 'dsnGetNodeDis'
            elif lower in REACTIONS:
                if not all(self.source_nodes[loc['id']]['restraints']):
                    raise PendingOutput('Support reaction at an unrestrained source node is not qualified')
                field = 'supportReaction'; index = REACTIONS.index(lower); method = 'dsnGetReaction'
            else:
                raise ValueError('Unsupported node component')
            raw = vector(values[field],6,'native '+field)
            trace.update(nativeNode=tag,api=method,field=field,componentIndex=index,rawArray=raw)
            return raw[index],trace
        element = self.elements[loc['id']]
        points = [[self.source_nodes[n][k] for k in 'xyz'] for n in element['nodes']]
        length = math.dist(*points); source_end = endpoint_index(loc['positionM'],length)
        tag = self.node_map[element['nodes'][source_end]]
        found = [s for s in self.segments[element['id']] if tag in s['native_nodes']]
        if len(found)!=1:
            raise ValueError('Source endpoint does not identify a unique native segment')
        segment = found[0]; native_id = segment['native_id']; frame = self.frames[native_id]
        if frame['T'] not in ('BEAM','COLUMN'):
            raise PendingOutput('Native '+frame['T']+' result convention remains pending independent qualification')
        if any(numbers(frame['E'])) or any(numbers(frame['R'])) or any(numbers(frame.get('RZL','0,0'))):
            raise ValueError('Offsets/releases require a different end-wrench mapping')
        tags = [int(x) for x in frame['N'].split(',')]; native_end = tags.index(tag)
        array = case['memberForces'][str(native_id)]
        if array['section_count']!=len(array['forces']) or array['section_count']<2:
            raise ValueError('Incomplete valid native member sections')
        index = 0 if native_end==0 else array['section_count']-1
        raw = vector(array['forces'][index],6,'native member forces')
        native_basis = native_axes(*[self.nodes[n] for n in tags],numbers(frame['DIR']))
        basis = source_axes(self.model,element)
        mapped = sdk_endpoint_actions(raw,frame['T'],native_end,source_end,native_basis,basis)
        if comp not in ACTIONS:
            raise ValueError('Unsupported requested member component')
        trace.update(api='dsnGetComStdNL',option=1,nativeFrame=native_id,nativeFamily=frame['T'],
                     nativeEndpoint=native_end,sourceEndpoint=source_end,nativeSectionIndex=index,
                     validSectionCount=array['section_count'],rawArray=raw,nativeAxesRows=native_basis,
                     sourceAxesRows=basis,sourceActions=mapped,sourceMemberSegments=self.segments[element['id']],
                     requestedPositionM=loc['positionM'],sourceLengthM=length,
                     conversion='SDK family -> FFRC diagram -> resisting end wrench -> source ACTIONS')
        return mapped[ACTIONS.index(comp)],trace

    def quantity(self, request):
        result = deepcopy(request); terms = []; canonical = 0.
        try:
            for case,factor in reference_io.selection_factors(self.model,request['selection']).items():
                value,trace = self.single_case(request,case)
                terms.append({'factor':factor,'canonicalValue':value,'trace':trace}); canonical += factor*value
        except PendingOutput as exc:
            result.update(nativeStatus='pending-output-family',pendingReason=str(exc),rawTrace=terms)
            return result
        result.update(value=reference_io.convert_value(canonical,reference_io.quantity_unit(request['component']),request['unit']),
                      nativeStatus='candidate-pending-review',rawTrace=terms,
                      selectionMethod='native case array' if request['selection']['kind']=='case' else 'explicit linear superposition of native first-order case arrays')
        return result


def export_candidates(index_path, corpus, output):
    index_path=Path(index_path).resolve(); corpus=Path(corpus).resolve(); output=Path(output).resolve()
    if output==corpus or corpus in output.parents:
        raise ValueError('Candidate output must be outside the active corpus')
    index_raw=index_path.read_bytes();index_hash=hashlib.sha256(index_raw).hexdigest()
    index=json.loads(index_raw.decode('utf-8-sig')); rows=index['states']; case_ids=sorted({r['case'] for r in rows}); summary=[]
    exporter_hash=sha(__file__);mapping_hash=sha(Path(__file__).with_name('yjk_results.py'))
    for case_id in case_ids:
        loaded=reference_io.load_case(corpus/case_id)
        if loaded['contract']['plannedEngine']!='YJK':
            raise ValueError('Evidence index contains a non-YJK case')
        states=[]; evidence_states=[]
        for state in loaded['states']:
            found=[r for r in rows if r['case']==case_id and r['state']==state['state']]
            if len(found)!=1:
                raise ValueError('Missing or duplicate native state binding')
            evidence=StateEvidence(found[0],index_path.parent,state['model'],loaded['hashes'][state['modelPath']])
            evidence_states.append(evidence)
            quantities=[evidence.quantity(q) for q in state['quantities']]
            pending=[q['id'] for q in quantities if 'value' not in q]
            derived=reference_io.evaluate_derived(quantities,state['derived']) if not pending else []
            states.append({'state':state['state'],'model':state['modelPath'],
                           'sourceModelSha256':loaded['hashes'][state['modelPath']],
                           'quantities':quantities,'derived':derived,'pendingQuantityIds':pending,
                           'derivedPendingBecauseMissingOperands':bool(pending and state['derived']),
                           'evidenceArtifacts':evidence.artifacts,'sourceNodeMap':evidence.node_map,
                           'sourceMemberSegments':evidence.segments,'nativeInputStatus':'diagnostic-audited-pending-independent-qualification'})
        candidate={'schemaVersion':1,'id':case_id,'modelId':loaded['contract'].get('modelId'),
                   'referenceKind':'native-yjk-candidate','method':'native-yjk-sdk-first-order',
                   'status':'pending-independent-review','accepted':False,'nativeVerified':False,
                   'notCommercialScoringTruth':True,'sameEngineTruthStatus':'pending',
                   'analysisConvention':deepcopy(loaded['contract']['analysisConvention']),
                   'inputHashes':loaded['hashes'],'sourceHash':loaded['sourceHash'],'sourceManifest':loaded['sourceManifest'],
                   'evidenceIndexSha256':index_hash,'exporterSha256':exporter_hash,
                   'resultMappingSha256':mapping_hash,
                   'evidencePathBase':'directory containing the bound evidence index',
                   'engineBinding':index.get('engineBinding'),'states':states}
        for evidence in evidence_states:
            evidence.verify_unchanged()
        binding=reference_io.build_source_binding(corpus/case_id,loaded['contract'],loaded['hashes'])
        if binding['sourceHash']!=loaded['sourceHash'] or sha(index_path)!=index_hash:
            raise ValueError('Source inputs or evidence index changed during export')
        destination=output/case_id/'native-yjk-candidate.json';reference_io.write_json_exclusive(destination,candidate)
        summary.append({'case':case_id,'states':len(states),'quantities':sum(len(s['quantities']) for s in states),
                        'values':sum(sum('value' in q for q in s['quantities']) for s in states),
                        'derived':sum(len(s['derived']) for s in states),'path':str(destination.relative_to(output)),'sha256':sha(destination)})
    reference_io.write_json_exclusive(output/'manifest.json',{'status':'pending-independent-review','notCommercialScoringTruth':True,'sameEngineTruthStatus':'pending','cases':summary})
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index',required=True,type=Path);parser.add_argument('--corpus',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();summary=export_candidates(args.index,args.corpus,args.output)
    print(json.dumps({'cases':len(summary),'states':sum(x['states'] for x in summary),
                      'quantities':sum(x['quantities'] for x in summary),'values':sum(x['values'] for x in summary),
                      'derived':sum(x['derived'] for x in summary)}))
