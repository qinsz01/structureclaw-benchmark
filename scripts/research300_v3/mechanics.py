"""Deterministic, independent engineering construction and load transfer.

These functions author expected inputs; no production solver is imported.
All project gravity is explicit and design-dependent. Bare-frame automatic
controls remain off. Transfer is a declared one-way force transfer, not an
unimplemented displacement-compatible coupled analysis.
"""
from copy import deepcopy
import itertools
import math

try:from .support import factory,legacy_refs,legacy_tasks
except ImportError:
    from scripts.research300_v3.support import factory,legacy_refs,legacy_tasks

G=9.80665
COMBINATIONS=[{'id':'SERVICE','factors':{'D':1.,'Q':1.}},
              {'id':'WIND','factors':{'D':1.,'Q':.5,'W':1.}},
              {'id':'REVERSE','factors':{'D':1.,'Q':.25,'W':-1.}}]
SELECTIONS=[{'kind':'combination','id':row['id']} for row in COMBINATIONS]
CATALOG=[{'id':'A','widthFactor':1.,'depthFactor':.82},
         {'id':'B','widthFactor':.86,'depthFactor':1.10},
         {'id':'C','widthFactor':1.10,'depthFactor':1.10}]
DESIGNS=[dict(zip(['G0','G1','G2'],items)) for items in itertools.product('ABC',repeat=3)]

def empty_cases():return [{'id':c,'type':t,'loads':[]} for c,t in [('D','dead'),('Q','live'),('W','wind')]]

def clean(model):
    m=deepcopy(model);m['load_cases']=empty_cases();m['load_combinations']=deepcopy(COMBINATIONS)
    m['analysis_control']={k:False for k in ['self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage']}
    for node in m['nodes']:node.pop('mass',None)
    m.setdefault('metadata',{}).pop('physicalMemberSegments',None)
    return m

def rename(model):
    m=deepcopy(model);nm={n['id']:f'J{i+1:03}' for i,n in enumerate(m['nodes'])};em={e['id']:f'M{i+1:03}' for i,e in enumerate(m['elements'])}
    for n in m['nodes']:n['id']=nm[n['id']]
    for e in m['elements']:
        e['id']=em[e['id']];e['nodes']=[nm[n] for n in e['nodes']]
    for c in m.get('load_cases',[]):
        for l in c['loads']:
            if l.get('node') in nm:l['node']=nm[l['node']]
            if l.get('element') in em:l['element']=em[l['element']]
    refs=m.get('metadata',{}).get('elementReferenceVectors')
    if refs is not None:m['metadata']['elementReferenceVectors']={em[e]:v for e,v in refs.items() if e in em}
    return m

def length(m,e):
    ns={n['id']:n for n in m['nodes']};return math.dist([ns[e['nodes'][0]][k] for k in 'xyz'],[ns[e['nodes'][1]][k] for k in 'xyz'])

def split_member(model,eid,fractions=(.5,)):
    e=next(e for e in model['elements'] if e['id']==eid)
    if e.get('releases') or e.get('offsets'):raise ValueError('Do not silently subdivide released/offset members')
    ns={n['id']:n for n in model['nodes']};a,b=[ns[n] for n in e['nodes']];chain=[a['id']]
    for i,t in enumerate(fractions,1):
        n={'id':eid+'-joint-'+str(i),**{k:round(a[k]+t*(b[k]-a[k]),9) for k in 'xyz'},
           'restraints':[False,True,False,True,False,True] if model['coordinate_system']['dimension']=='2d' else [False]*6}
        if e['type'] in ['truss','brace']:n['restraints'][3:]=[True]*3
        if a.get('story') and a.get('story')==b.get('story'):n['story']=a['story']
        model['nodes'].append(n);chain.append(n['id'])
    chain.append(b['id']);index=model['elements'].index(e);children=[]
    refs=model.get('metadata',{}).get('elementReferenceVectors',{})
    for i,(na,nb) in enumerate(zip(chain,chain[1:])):
        v={**deepcopy(e),'id':eid+'-part-'+str(i+1),'nodes':[na,nb]};children.append(v)
        if eid in refs:refs[v['id']]=deepcopy(refs[eid])
    if eid in refs:del refs[eid]
    model['elements'][index:index+1]=children

def roof_line(model):
    # A roof/application line is an issued load-transfer location. Same-X
    # nodes on lower storeys never become extra bearing points.
    lines={}
    for n in model['nodes']:
        if not n['restraints'][2]:lines.setdefault(round(n['y'],8),[]).append(n)
    candidates=[]
    for y,nodes in lines.items():
        roof={}
        for n in nodes:
            x=round(n['x'],8)
            if x not in roof or n['z']>roof[x]['z']:roof[x]=n
        if len(roof)>=4:candidates.append((max(n['z'] for n in roof.values()),len(roof),-abs(y),y,roof))
    if not candidates:return []
    *_,roof=max(candidates,key=lambda v:v[:3]);nodes=sorted(roof.values(),key=lambda n:n['x'])
    return [nodes[round(i*(len(nodes)-1)/3)] for i in range(4)]

def prepare_primary(model):
    m=clean(model)
    if len(m['nodes'])<6 or len(m['elements'])<5 or any(e.get('releases') or e.get('offsets') for e in m['elements']):return None
    for attempt in range(5):
        targets=roof_line(m)
        if targets:return rename(m)
        ns={n['id']:n for n in m['nodes']};beams=[e for e in m['elements'] if e['type'] in ['beam','column'] and abs(ns[e['nodes'][1]]['x']-ns[e['nodes'][0]]['x'])>1e-8]
        if not beams:return None
        beam=max(beams,key=lambda e:(sum(ns[n]['z'] for n in e['nodes'])/2,length(m,e)))
        split_member(m,beam['id'],(.25,.5,.75))
    return None

def secondary(primary,seed,cambered=False):
    targets=roof_line(primary);assert len(targets)==4
    m=factory._model('2d');m['nodes']=[];m['elements']=[];m['load_cases']=empty_cases();m['load_combinations']=deepcopy(COMBINATIONS)
    spans=[b['x']-a['x'] for a,b in zip(targets,targets[1:])];h=round(max(.14,max(spans)/32),3);b=round(.10+.01*(seed%4),3)
    m['sections']=[factory._section('OUTER',b,h),factory._section('MIDDLE',b,h)]
    for i,n in enumerate(targets):factory._node(m,'S'+str(i),n['x'],n['z'],support='P' if i==0 else 'R')
    for j,(a,bnode) in enumerate(zip(targets,targets[1:])):
        chain=['S'+str(j)]
        for k,t in enumerate([.25,.5,.75],1):
            nid=f'U{j}-{k}';rise=.04*(bnode['x']-a['x'])*math.sin(math.pi*t) if cambered else 0.
            factory._node(m,nid,a['x']+t*(bnode['x']-a['x']),a['z']+t*(bnode['z']-a['z'])+rise);chain.append(nid)
        chain.append('S'+str(j+1))
        for k,(na,nb) in enumerate(zip(chain,chain[1:])):factory._member(m,f'U{j}-{k}',na,nb,'beam','MIDDLE' if j==1 else 'OUTER')
    return m,[{'upperSupport':'S'+str(i),'primaryJoint':n['id']} for i,n in enumerate(targets)]

def rules_for(primary,seed):
    roof=roof_line(primary)
    if not roof:
        nodes=sorted(primary['nodes'],key=lambda n:(n['x'],n['z']));xmin,xmax=min(n['x'] for n in nodes),max(n['x'] for n in nodes)
    else:xmin,xmax=roof[0]['x'],roof[-1]['x']
    span=xmax-xmin
    return {'gravityMPerS2':G,'gravityTreatment':'explicit member self weight; never enable automatic self_weight',
      'areaLoadBasis':'D and Q per horizontal projected area; W normal pressure per actual strip surface area',
      'zones':[{'id':'Z-WEST','startX':xmin,'endX':round(xmin+.43*span,8),'widthM':round(2.4+.2*(seed%5),3),'D':round(.8+.1*(seed%4),3),'Q':round(2.8+.2*(seed%5),3),'W':round(.5+.05*(seed%3),3)},
               {'id':'Z-EAST','startX':round(xmin+.43*span,8),'endX':xmax,'widthM':round(3.+.15*(seed%5),3),'D':round(1.+.1*(seed%3),3),'Q':round(4.+.25*(seed%4),3),'W':round(.65+.05*(seed%4),3)}],
      'equipmentAction':{'case':'W','fxKN':round(10+1.2*(seed%9),3),'fyKN':round(6+.7*(seed%7),3) if primary['coordinate_system']['dimension']=='3d' else 0.,'positionX':round(xmin+.67*span,8),'rule':'Distribute to the two neighbouring transfer joints by linear distance weights; conserve force and first moment.'}}

def resize_sections(m,section_ids,option):
    row=next(r for r in CATALOG if r['id']==option)
    for sid in section_ids:
        section=next(s for s in m['sections'] if s['id']==sid)
        if section.get('shape',{}).get('kind')!='rectangular':raise ValueError('Project catalog requires declared rectangular equivalents')
        legacy_tasks.resize(m,sid,row['widthFactor'],row['depthFactor'])

def add_load(m,case,**kw):
    c=next(c for c in m['load_cases'] if c['id']==case)
    c['loads'].append({'id':f'{case}-{len(c["loads"])+1}','reference_frame':'global',**kw})

def self_weight(m):
    mats={x['id']:x for x in m['materials']};secs={x['id']:x for x in m['sections']}
    for e in m['elements']:
        q=mats[e['material']]['rho']*secs[e['section']]['properties']['A']*G/1000
        if e['type'] in ['truss','brace']:
            for nid in e['nodes']:add_load(m,'D',type='nodal',node=nid,fz=-q*length(m,e)/2)
        else:add_load(m,'D',type='distributed',element=e['id'],wz=-q)

def strip_loads(m,rules):
    ns={n['id']:n for n in m['nodes']}
    for e in m['elements']:
        a,b=[ns[n] for n in e['nodes']];L=length(m,e);dx=b['x']-a['x'];dz=b['z']-a['z']
        assert dx>0 and e['type']=='beam'
        for case in ['D','Q','W']:
            for z in strip_terms(rules,case):
                left=max(a['x'],z['startX']);right=min(b['x'],z['endX'])
                if right-left<1e-9:continue
                start=(left-a['x'])/dx*L;end=(right-a['x'])/dx*L;q=z['pressure']*z['widthM']
                if case=='W':add_load(m,case,type='distributed',element=e['id'],start=start,end=end,wx=-q*dz/L,wz=q*dx/L)
                else:add_load(m,case,type='distributed',element=e['id'],start=start,end=end,wz=-q*dx/L)
    if rules.get('addedEquipment'):
        add_load(m,'D',type='nodal',node='U1-2',fz=-rules['addedEquipment']['weightKN'])

def strip_terms(rules,case):
    if case!='Q' or not rules.get('liveRevision'):
        return [{**z,'pressure':z[case]} for z in rules['zones']]
    r=rules['liveRevision'];split=r['splitX'];aw=sum(max(0.,min(z['endX'],split)-z['startX'])*z['widthM'] for z in rules['zones']);ae=sum(max(0.,z['endX']-max(z['startX'],split))*z['widthM'] for z in rules['zones'])
    pe=r['totalLiveKN']/(r['westEastPressureRatio']*aw+ae);out=[]
    for z in rules['zones']:
        for lo,hi,p in [(z['startX'],min(z['endX'],split),pe*r['westEastPressureRatio']),(max(z['startX'],split),z['endX'],pe)]:
            if hi-lo>1e-10:out.append({'startX':lo,'endX':hi,'widthM':z['widthM'],'pressure':p})
    return out

def revised_project_rules(base,seed):
    r=deepcopy(base);xmin=min(z['startX'] for z in r['zones']);xmax=max(z['endX'] for z in r['zones'])
    r['liveRevision']={'splitX':round(xmin+(.57+.02*(seed%4))*(xmax-xmin),8),'westEastPressureRatio':round(1.7+.15*(seed%5),3),'totalLiveKN':sum((z['endX']-z['startX'])*z['widthM']*z['Q'] for z in r['zones']),'scope':'Only Q moves. Keep strip geometry, widths, D/W and self weight unchanged.'}
    return r

def volume(m):
    secs={x['id']:x for x in m['sections']}
    return sum(secs[e['section']]['properties']['A']*length(m,e) for e in m['elements'])

def static_solutions(m,selections=SELECTIONS):
    stations=[]
    for e in m['elements']:
        if e['type'] not in ['truss','brace']:
            stations.extend([{'kind':'member','id':e['id'],'positionM':0.,'side':'right'},
                             {'kind':'member','id':e['id'],'positionM':length(m,e),'side':'left'}])
    q=[{'location':s} for s in stations]
    return legacy_refs.solve(m,selections,q)

def node_envelope(m,fn,component):
    vals=[(fn({'kind':'node','id':n['id']},component),n['id']) for n in m['nodes']]
    value,nid=max(vals,key=lambda row:abs(row[0]));return {'value':value,'governingJoint':nid,'unit':'m'}

def force_envelope(m,fn):
    vals=[];bending=any(e['type'] not in ['truss','brace'] for e in m['elements'])
    for e in m['elements']:
        if bending and e['type'] in ['truss','brace']:continue
        cs=['N'] if e['type'] in ['truss','brace'] else ['M2'] if m['coordinate_system']['dimension']=='2d' else ['M2','M3']
        for component in cs:
            for x,side in [(0.,'right'),(length(m,e),'left')]:
                loc={'kind':'member','id':e['id'],'positionM':x,'side':side};value=fn(loc,component)
                vals.append((value,e['id'],x,side,component))
    value,eid,x,side,component=max(vals,key=lambda r:abs(r[0]));return {'value':value,'governingMember':eid,'positionM':x,'side':side,'component':component,'unit':'kN' if component=='N' else 'kN.m'}

def lateral_envelope(m,fn):
    vals=[(math.hypot(fn({'kind':'node','id':n['id']},'ux'),fn({'kind':'node','id':n['id']},'uy')) if m['coordinate_system']['dimension']=='3d' else abs(fn({'kind':'node','id':n['id']},'ux')),n['id']) for n in m['nodes']]
    value,nid=max(vals);return {'value':value,'governingJoint':nid,'unit':'m'}

def project(primary,upper,interface,rules,choice):
    p=clean(primary);u=clean(upper)
    resize_sections(u,['OUTER'],choice['G0']);resize_sections(u,['MIDDLE'],choice['G1']);resize_sections(p,[s['id'] for s in p['sections']],choice['G2'])
    self_weight(u);strip_loads(u,rules);self_weight(p)
    primitives=[{'kind':'case','id':c} for c in ['D','Q','W']]
    us=static_solutions(u,primitives);transfer=[]
    for selection,(fn,check) in zip(primitives,us):
        values=[]
        for link in interface:
            loc={'kind':'node','id':link['upperSupport']};fx=fn(loc,'Fx');fz=fn(loc,'Fz')
            values.append({'upperSupport':link['upperSupport'],'primaryJoint':link['primaryJoint'],'fx':fx,'fz':fz})
            add_load(p,selection['id'],type='nodal',node=link['primaryJoint'],fx=-fx,fz=-fz)
        transfer.append({'selection':selection,'values':values,'referenceCheck':check})
    targets={n['id']:n for n in p['nodes']};ordered=sorted([targets[x['primaryJoint']] for x in interface],key=lambda n:n['x']);eq=rules['equipmentAction'];x=eq['positionX']
    left,right=next((a,b) for a,b in zip(ordered,ordered[1:]) if a['x']-1e-9<=x<=b['x']+1e-9)
    for n,w in [(left,(right['x']-x)/(right['x']-left['x'])),(right,(x-left['x'])/(right['x']-left['x']))]:
        add_load(p,'W',type='nodal',node=n['id'],fx=w*eq['fxKN'],**({'fy':w*eq['fyKN']} if eq['fyKN'] else {}))
    ps=static_solutions(p);umetrics=[];pmetrics=[]
    for sel,(fn,check) in zip(SELECTIONS,ps):
        pmetrics.append({'selection':sel,'uz':node_envelope(p,fn,'uz'),'ux':node_envelope(p,fn,'ux'),'lateral':lateral_envelope(p,fn),'force':force_envelope(p,fn),'referenceCheck':check})
    for combo in COMBINATIONS:
        def fn(loc,component,combo=combo):return sum(f*sol[0](loc,component) for case,f in combo['factors'].items() for sel,sol in zip(primitives,us) if sel['id']==case)
        umetrics.append({'selection':{'kind':'combination','id':combo['id']},'uz':node_envelope(u,fn,'uz')})
    return {'choice':dict(choice),'volume':volume(p)+volume(u),'transfer':transfer,'primaryMetrics':pmetrics,'upperMetrics':umetrics,
            'primarySections':p['sections'],'primaryLoadCases':p['load_cases'],'upperSections':u['sections'],'upperLoadCases':u['load_cases']}

def selected_models(ref,truth):
    if ref.get('integration')=='rigid':
        m=deepcopy(ref['combinedTemplate']);m['sections']=deepcopy(truth['combinedSections']);m['load_cases']=deepcopy(truth['combinedLoadCases']);return {'combined':m}
    p=deepcopy(ref['primaryTemplate']);u=deepcopy(ref['upperTemplate'])
    p['sections']=deepcopy(truth['primarySections']);p['load_cases']=deepcopy(truth['primaryLoadCases'])
    u['sections']=deepcopy(truth['upperSections']);u['load_cases']=deepcopy(truth['upperLoadCases'])
    return {'primary':p,'upper':u}

def rigid_eligible(primary):
    p=prepare_primary(primary)
    if not p:return False
    if p['coordinate_system']['dimension']=='2d':return True
    # A spatial axial-only system has no qualified rotational support for the
    # added rib's free torsion mode. Do not invent a rotational restraint.
    nodes={n['id'] for n in roof_line(p)}
    return all(any(nid in e['nodes'] and e['type'] not in ['truss','brace'] for e in p['elements']) for nid in nodes)

def combine_rigid(primary,upper,interface):
    p=clean(primary);u=clean(upper);out=deepcopy(p);out['nodes']=[];out['elements']=[];out['materials']=[];out['sections']=[];out['metadata']={'elementReferenceVectors':{}} if p['coordinate_system']['dimension']=='3d' else {}
    pm={n['id']:'P-'+n['id'] for n in p['nodes']};um={n['id']:'U-'+n['id'] for n in u['nodes']}
    for link in interface:um[link['upperSupport']]=pm[link['primaryJoint']]
    for n in p['nodes']:
        row=deepcopy(n);row['id']=pm[n['id']]
        if n['id'] in {r['primaryJoint'] for r in interface} and all(e['type'] in ['truss','brace'] for e in p['elements'] if n['id'] in e['nodes']):row['restraints'][4]=False
        out['nodes'].append(row)
    y=roof_line(p)[0]['y'];existing={n['id'] for n in out['nodes']}
    for n in u['nodes']:
        if um[n['id']] in existing:continue
        row=deepcopy(n);row['id']=um[n['id']];row['y']=y
        if p['coordinate_system']['dimension']=='3d':row['restraints']=[False]*6
        out['nodes'].append(row)
    maps={}
    for label,model,nm in [('P',p,pm),('U',u,um)]:
        mats={m['id']:label+'-'+m['id'] for m in model['materials']};secs={s['id']:label+'-'+s['id'] for s in model['sections']};em={e['id']:label+'-'+e['id'] for e in model['elements']};maps[label]={'nodes':nm,'elements':em}
        out['materials'] += [{**deepcopy(m),'id':mats[m['id']]} for m in model['materials']]
        out['sections'] += [{**deepcopy(s),'id':secs[s['id']]} for s in model['sections']]
        for e in model['elements']:
            row=deepcopy(e);row.update(id=em[e['id']],nodes=[nm[n] for n in e['nodes']],material=mats[e['material']],section=secs[e['section']]);out['elements'].append(row)
            if p['coordinate_system']['dimension']=='3d':out['metadata']['elementReferenceVectors'][row['id']]=deepcopy(model.get('metadata',{}).get('elementReferenceVectors',{}).get(e['id'],[0.,0.,1.]))
    return out,maps

def rigid_project(primary,upper,interface,rules,choice):
    p=clean(primary);u=clean(upper);resize_sections(u,['OUTER'],choice['G0']);resize_sections(u,['MIDDLE'],choice['G1']);resize_sections(p,[s['id'] for s in p['sections']],choice['G2'])
    combined,mapping=combine_rigid(p,u,interface);self_weight(combined);strip_loads(u,rules)
    for case in u['load_cases']:
        for load in case['loads']:
            row=deepcopy(load);row.pop('id',None)
            if 'node' in row:row['node']=mapping['U']['nodes'][row['node']]
            if 'element' in row:row['element']=mapping['U']['elements'][row['element']]
            row.pop('reference_frame',None);add_load(combined,case['id'],**row)
    targets=sorted(roof_line(p),key=lambda n:n['x']);eq=rules['equipmentAction'];x=eq['positionX'];a,b=next((a,b) for a,b in zip(targets,targets[1:]) if a['x']-1e-9<=x<=b['x']+1e-9)
    for n,w in [(a,(b['x']-x)/(b['x']-a['x'])),(b,(x-a['x'])/(b['x']-a['x']))]:add_load(combined,'W',type='nodal',node=mapping['P']['nodes'][n['id']],fx=w*eq['fxKN'],**({'fy':w*eq['fyKN']} if eq['fyKN'] else {}))
    ps=[];us=[];interfaces=[]
    for sel,(fn,check) in zip(SELECTIONS,static_solutions(combined)):
        def view(label):
            def calculate(loc,comp):
                q=deepcopy(loc);q['id']=mapping[label]['nodes' if q['kind']=='node' else 'elements'][q['id']];return fn(q,comp)
            return calculate
        pf=view('P');uf=view('U')
        ps.append({'selection':sel,'uz':node_envelope(p,pf,'uz'),'ux':node_envelope(p,pf,'ux'),'lateral':lateral_envelope(p,pf),'force':force_envelope(p,pf),'referenceCheck':check})
        us.append({'selection':sel,'uz':node_envelope(u,uf,'uz')})
        interfaces.append({'selection':sel,'values':[{'primaryJoint':r['primaryJoint'],'upperSupport':r['upperSupport'],'ux':pf({'kind':'node','id':r['primaryJoint']},'ux'),'uz':pf({'kind':'node','id':r['primaryJoint']},'uz')} for r in interface]})
    return {'choice':dict(choice),'volume':volume(combined),'transfer':interfaces,'primaryMetrics':ps,'upperMetrics':us,'combinedSections':combined['sections'],'combinedLoadCases':combined['load_cases']}
