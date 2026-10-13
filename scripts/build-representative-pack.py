"""Freeze authored inputs, independent references and tolerances before testing the candidate.
Does not invoke a model API, the candidate solver or any production postprocessor.
"""
import csv, hashlib, importlib.util, json, math
from pathlib import Path
from html import escape

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;DEST=ROOT/'acceptance'/'representative-18'
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
models=module('authoring','representative-models.py');independent=module('reference','independent-frame-reference.py')
prompts=module('prompts','representative-prompts.py')
PLAN=json.loads((ROOT/'planning/capability-coverage-300.json').read_text(encoding='utf-8'))
TOL=dict(absolute=1e-8,relative=1e-6)


def write_json(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def hashfile(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def quantities(case,model):
    specs=[]
    def add(kind,id,component,x=None,side='right'):
        location=dict(kind=kind,id=id)
        if kind=='member':location.update(positionM=x,side=side)
        unit='m' if component.startswith('u') else 'rad' if component.startswith('r') else 'kN.m' if component[0] in 'mMT' else 'kN'
        specs.append(dict(id=f'{id}:{component}'+(f'@{x}:{side}' if x is not None else ''),location=location,component=component,unit=unit,tolerance=TOL))
    # Full nodal table explicitly includes all task-selected values, rotations and reactions.
    for n in model['nodes']:
        for c in ['ux','uy','uz','rx','ry','rz']:add('node',n['id'],c)
        if any(n['restraints'][i] for i in [0,2]):
            for c in ['fx','fy','fz','mx','my','mz']:add('node',n['id'],c)
    nodes={n['id']:n for n in model['nodes']}
    for e in model['elements']:
        a,b=[nodes[n] for n in e['nodes']];L=math.dist([a[k] for k in ['x','y','z']],[b[k] for k in ['x','y','z']])
        if e['type']=='truss':add('member',e['id'],'N',L/2);continue
        for x,side in [(0,'right'),(L,'left')]:
            for c in ['N','V2','V3','T','M2','M3']:add('member',e['id'],c,x,side)
        add('member',e['id'],'uz',L/2)
    extras={'STD-008':[('b1',x,'uz','right') for x in [2,4.5,7]]+[('b1',x,'M2','right') for x in [2,7]],
        'INT-001':[('b1',3,'uz','right')],'INT-008':[('b1',4.5,'uz','right')],
        'INT-019':[('b2',3,'uz','right')], 'MM-004':[('b1',6,'uz','right'),('b1',4,'V3','left'),('b1',4,'V3','right')]}
    for e,x,c,side in extras.get(case,[]):add('member',e,c,x,side)
    return list({q['id']:q for q in specs}.values())


def svg(model,title,view='xz',hide_supports=False):
    axes={'xz':('x','z'),'yz':('y','z'),'xy':('x','y')}[view];ns=model['nodes'];width=1600;height=1250
    lo=[min(n[k] for n in ns) for k in axes];hi=[max(n[k] for n in ns) for k in axes];scale=min(1250/max(hi[0]-lo[0],1),680/max(hi[1]-lo[1],1))
    point=lambda n:(140+(n[axes[0]]-lo[0])*scale,820-(n[axes[1]]-lo[1])*scale)
    ids={n['id']:n for n in ns};parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#f6f8fc"/><g font-family="Arial,Microsoft YaHei,sans-serif"><text x="65" y="65" font-size="28" fill="#17314d">{escape(title)} · {view.upper()} projection</text><text x="65" y="110" font-size="20">Dimensions m / 尺寸 m · Global Z up / 全局 Z 向上 · labels identify physical objects</text>']
    for e in model['elements']:
        a,b=[point(ids[i]) for i in e['nodes']];parts.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="#1b5274" stroke-width="4"/>')
        if math.dist(a,b)>20:parts.append(f'<text x="{(a[0]+b[0])/2+7}" y="{(a[1]+b[1])/2-8}" font-size="15" fill="#39566c">{escape(e["id"])}</text>')
    # Coincident projections retain separate IDs; other views resolve their connectivity.
    grouped={}
    for n in ns:grouped.setdefault(point(n),[]).append(n)
    for (x,y),group in grouped.items():
        n=group[0];label='/'.join(n['id'] for n in group);coord=f'({n[axes[0]]:g},{n[axes[1]]:g})'
        parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#d46d30"/><text x="{x+8}" y="{y-14}" font-size="15">{escape(label)} {coord}</text>')
        if not hide_supports and any(g['restraints'][0] and g['restraints'][2] for g in group):
            r=group[0]['restraints'];label='FIXED / 固定' if all(r) else 'PIN / 铰' if r[0] else 'ROLLER / 滚支'
            parts.append(f'<text x="{x-35}" y="{y+30}" font-size="16" fill="#9b5029">{label}</text>')
        elif not hide_supports and n['restraints'][2] and n['z']==0:parts.append(f'<text x="{x-35}" y="{y+30}" font-size="16" fill="#9b5029">ROLLER / 滚支</text>')
    if hide_supports:parts.append('<rect x="55" y="815" width="1490" height="70" fill="#eef1f6"/><text x="65" y="858" font-size="20">Lower drawing region not supplied / 图纸底部区域未提供</text>')
    loadtext=[]
    for c in model['load_cases']:
        for l in c['loads']:
            target=l.get('node',l.get('element'));fields=', '.join(f'{k}={v}' for k,v in l.items() if k not in ['id','node','element','reference_frame','type'])
            loadtext.append(f'{c["id"]} · {target}: {fields}')
    # Large cases use a tagged load schedule attachment, rather than unreadably tiny labels.
    for i,text in enumerate(loadtext[:10]):parts.append(f'<text x="65" y="{920+i*26}" font-size="18">{escape(text)}</text>')
    if len(loadtext)>10:parts.append('<text x="840" y="1205" font-size="18">Complete loads: loads.csv / 完整荷载见表</text>')
    parts.append('</g></svg>');return ''.join(parts)


def main():
    DEST.mkdir(parents=True,exist_ok=True);entries=[]
    for case,snapshots in sorted(models.states().items()):
        planned=next(c for c in PLAN['cases'] if c['id']==case);folder=DEST/case;folder.mkdir(exist_ok=True)
        qsets=[];evidence=[];state_files=[]
        for i,m in enumerate(snapshots,1):
            path=folder/f'model-state-{i}.json';write_json(path,m);state_files.append(path.name)
            specs=quantities(case,m);states=[]
            selections=[dict(kind='case',id=c['id'],factors={c['id']:1}) for c in m['load_cases']]+[dict(kind='combination',id=c['id'],factors=c['factors']) for c in m['load_combinations']]
            for selection in selections:
                value,check=independent.solve(m,selection['factors'],[q['location'] for q in specs]);evidence.append(dict(state=i,selection={k:v for k,v in selection.items() if k!='factors'},**check))
                states.extend(dict(q,selection={k:v for k,v in selection.items() if k!='factors'},value=value(q['location'],q['component'])) for q in specs)
            qsets.append(dict(state=i,quantities=states))
        write_json(folder/'independent-reference.json',dict(referenceKind='independent-elastic-matrix',notCommercialScoringTruth=planned['plannedEngine']!='OpenSees',toleranceFrozenBeforeCandidate=True,states=qsets,checks=evidence))
        m=snapshots[0]
        # User appendix contains explicit material/section information; MM geometry stays in drawings.
        write_json(folder/'properties.json',dict(units=dict(E='MPa',G='MPa',rho='kg/m3',shape='mm',A='m2',Iy='m4',Iz='m4',J='m4'),coordinate_system=m['coordinate_system'],materials=m['materials'],sections=m['sections'],analysis_control=m['analysis_control'],load_combinations=m['load_combinations'],memberAssignments=[{k:e[k] for k in ['id','type','material','section']} for e in m['elements']],localAxes=m['metadata'],sectionRollConvention='ey_new=cos(theta)*ey+sin(theta)*ez; ez_new=-sin(theta)*ey+cos(theta)*ez; positive theta in degrees about member i-to-j axis'))
        with (folder/'loads.csv').open('w',encoding='utf-8-sig',newline='') as f:
            fields=['case','id','type','node','element','position','start','end','fx','fy','fz','mx','my','mz','wx','wy','wz'];w=csv.DictWriter(f,fields);w.writeheader()
            for c in m['load_cases']:
                for l in c['loads']:w.writerow({k:(c['id'] if k=='case' else l.get(k,'')) for k in fields})
        attachments=['properties.json','loads.csv']
        if case.startswith('MM'):
            views=['xz','yz','xy'] if m['coordinate_system']['dimension']=='3d' else ['xz']
            for view in views:
                name=f'drawing-{view}.svg';(folder/name).write_text(svg(m,case+' '+planned['title'],view),encoding='utf-8');attachments.append(name.replace('.svg','.png'))
            if case=='MM-058':(folder/'drawing-incomplete.svg').write_text(svg(m,case,'xz',True),encoding='utf-8');attachments.append('drawing-incomplete.png')
            if case=='MM-081':
                import ezdxf
                doc=ezdxf.new();doc.units=6;block=doc.blocks.new('STRUCTURE');nodes={n['id']:n for n in m['nodes']}
                for e in m['elements']:
                    pts=[tuple(nodes[n][k] for k in ['x','y','z']) for n in e['nodes']];block.add_line(*pts,dxfattribs={'layer':'STRUCTURE'})
                    mid=tuple(sum(p[k] for p in pts)/2 for k in range(3));block.add_text(e['id'],dxfattribs={'height':.15,'insert':mid,'layer':'LABELS'})
                for n in m['nodes']:
                    xyz=tuple(n[k] for k in ['x','y','z'])
                    label=n['id']+(' FIXED UX UY UZ RX RY RZ' if all(n['restraints']) else '')
                    block.add_text(label,dxfattribs={'height':.15,'insert':xyz,'layer':'NODES_SUPPORTS'})
                doc.modelspace().add_blockref('STRUCTURE',(0,0,0));doc.saveas(folder/'structure.dxf');attachments=['properties.json','loads.csv','structure.dxf']
        else:
            # Engineering input tables are separated from the hidden canonical answer.
            initial_nodes=[dict(n) for n in m['nodes']]
            if case=='INT-079':
                for n in initial_nodes:
                    if n['y']!=0:n['y']=None
            write_json(folder/'geometry-input.json',dict(nodes=initial_nodes,elements=m['elements']))
            attachments.append('geometry-input.json')
            if case=='INT-079':
                # Do not leak the missing span through its already multiplied tributary line load.
                (folder/'loads.csv').write_text('floor,pressure_kN_per_m2,distribution\nF1,10,X beams using adjacent Y half span\nF2,10,X beams using adjacent Y half span\n',encoding='utf-8')
        turn_text=prompts.instructions(case,planned)
        prompt=turn_text[0]
        (folder/'prompt.txt').write_text(prompt+'\n',encoding='utf-8')
        contract=dict(id=case,modelId=planned['modelId'],plannedEngine=planned['plannedEngine'],family=planned['family'],language=planned['language'],modelStates=state_files,attachments=attachments,
            sourcePlan=planned['sourceRequirements'],stateCount=len(snapshots),requiredOutput=planned['sourceRequirements']['task.expectedOutput'],
            status='candidate-inputs-frozen-needs-independent-review',sameEngineTruthStatus='matrix-reference-ready-native-comparison-pending' if planned['plannedEngine']=='OpenSees' else 'native-commercial-reference-required',
            inputBlindReview='pending',llmEndToEnd='not-run',numericalReference='independent-reference.json',mandatoryAssertions=['physical_model','requested_quantities','execution_evidence_every_selection','report_body_quantities'])
        contract['turns']=[dict(state=i+1,attachments=attachments if i==0 else [],instruction=turn_text[min(i,len(turn_text)-1)]) for i in range(len(snapshots))]
        if case=='MM-058':
            contract['attachments']=['properties.json','loads.csv','drawing-incomplete.png']
            contract['turns']=[dict(state=None,mustNotAnalyze=True,attachments=contract['attachments'],instruction='Please analyze the supplied incomplete drawing. / 请分析这张不完整图纸。'),dict(state=1,attachments=['drawing-xz.png'],instruction='The complete drawing is now supplied. / 已补充完整图纸。')]
        if case=='INT-079':
            contract['turns']=[dict(state=None,mustNotAnalyze=True,attachments=attachments,instruction='Y span is unspecified; do not infer it. / Y向跨度暂未给出，不得推测。'),dict(state=1,attachments=[],instruction='The missing Y span is 5 m. / Y向跨度为5米。')]
        write_json(folder/'contract.json',contract);entries.append(dict(id=case,engine=planned['plannedEngine'],contract=f'{case}/contract.json'))
    # Candidate execution must verify these hashes; references cannot be changed by the runner.
    files={str(p.relative_to(DEST)).replace('\\','/'):hashfile(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    write_json(DEST/'manifest.json',dict(schemaVersion=1,evaluationProfile='engineering-v2.2',cases=entries,counts=dict(total=18,OpenSees=12,PKPM=3,YJK=3),
        status='candidate-pack-not-accepted-corpus',sourcePlanUnchanged=True,independentReferenceMethod='Direct stiffness and consistent nodal loads, computed without importing production or OpenSees; commercial values are diagnostics only.',
        sourceHashes={p.name:hashfile(p) for p in [HERE/'representative-models.py',HERE/'independent-frame-reference.py',HERE/'representative-prompts.py',Path(__file__)]},sha256=files))
    print(json.dumps(dict(cases=len(entries),files=len(files),status='frozen-before-candidate'),ensure_ascii=False))

if __name__=='__main__':main()
