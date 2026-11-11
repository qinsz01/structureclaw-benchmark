"""Deterministic line-member model families for research300 v2 authoring.

No production solver imports.  Variants change connectivity or supports, not
merely numerical properties.  Models contain D (gravity), Q (partial gravity),
W (horizontal) and SERVICE=D+Q / REVERSE=D-W.  All actions are explicit.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import itertools
import json
import math

FAMILIES = ('beam', 'frame', 'truss', 'space_frame', 'space_truss', 'mixed')
VARIANTS = 35


def _section(identifier, b, h):
    large, small = max(b, h), min(b, h)
    return {'id':identifier,'name':identifier,'type':'custom',
            'shape':{'kind':'rectangular','B':b*1000,'H':h*1000},
            'properties':{'A':b*h,'Iy':b*h**3/12,'Iz':h*b**3/12,
                          'J':large*small**3*(1/3-.21*small/large*(1-small**4/(12*large**4)))}}


def _model(dimension):
    return {'schema_version':'2.2.0','unit_system':'SI',
      'coordinate_system':{'dimension':dimension,'plane':'xz' if dimension=='2d' else None,
          'semantics':'global-z-up','version':1,'dof_order':['ux','uy','uz','rx','ry','rz']},
      'nodes':[],'elements':[],
      'materials':[{'id':'S','name':'Explicit elastic steel','type':'steel','E':206000.,
                    'G':206000/(2*1.3),'nu':.3,'rho':7850.}],
      'sections':[_section('B',.18,.32),_section('C',.25,.4),_section('A',.08,.1)],
      'load_cases':[{'id':'D','type':'dead','loads':[]},{'id':'Q','type':'live','loads':[]},
                    {'id':'W','type':'wind','loads':[]}],
      'load_combinations':[{'id':'SERVICE','factors':{'D':1.,'Q':1.}},
                           {'id':'REVERSE','factors':{'D':1.,'W':-1.}}],
      'analysis_control':{k:False for k in ['self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage']},
      'metadata':{'elementReferenceVectors':{}} if dimension=='3d' else {}}


def _node(m, identifier, x, z, y=0., support=None, axial=False):
    dim=m['coordinate_system']['dimension']
    r=[False,True,False,True,False,True] if dim=='2d' else [False]*6
    if axial:r[3:]=[True]*3
    if support=='F':r=[True]*6
    elif support=='P':r[0]=r[2]=True
    elif support=='R':r[2]=True
    elif support=='T':r[:3]=[True]*3
    m['nodes'].append({'id':identifier,'x':round(float(x),6),'y':round(float(y),6),
                       'z':round(float(z),6),'restraints':r})
    return identifier


def _member(m, identifier, a, b, kind='beam', section='B'):
    e={'id':identifier,'type':kind,'nodes':[a,b],'material':'S','section':section}
    m['elements'].append(e)
    if m['coordinate_system']['dimension']=='3d':
        ns={n['id']:n for n in m['nodes']};p,q=ns[a],ns[b]
        # Production schema's explicit reference-plane vector convention.
        ref=[1.,0.,0.] if abs(q['x']-p['x'])+abs(q['y']-p['y'])<1e-12 else [0.,0.,1.]
        m['metadata']['elementReferenceVectors'][identifier]=ref
    return e


def _load(m, case, **kw):
    c=next(c for c in m['load_cases'] if c['id']==case)
    c['loads'].append({'id':f'{case}-{len(c["loads"])+1}','reference_frame':'global',**kw})


def _frame_loads(m):
    beams=[e for e in m['elements'] if e['type']=='beam']
    for i,e in enumerate(beams):
        _load(m,'D',type='distributed',element=e['id'],wz=-8.)
        if i%2==0:_load(m,'Q',type='distributed',element=e['id'],wz=-5.)
    free=[n for n in m['nodes'] if not n['restraints'][0]]
    zmax=max(n['z'] for n in free)
    roof=[n for n in free if n['z']==zmax]
    for i,n in enumerate(roof):
        _load(m,'W',type='nodal',node=n['id'],fx=6.,**({'fy':3.} if m['coordinate_system']['dimension']=='3d' and i%2==0 else {}))
    if not beams:
        for n in roof:_load(m,'D',type='nodal',node=n['id'],fz=-8.)
        _load(m,'Q',type='nodal',node=roof[-1]['id'],fz=-5.)


def _beam_words():
    # Internal observation stations are inserted below but do not count as new
    # topology: the fingerprint removes collinear, unrestrained degree-two nodes.
    initial=['FU','PR','FR','FF','PRU','FRU']
    words=initial[:]
    seen={min(w,w[::-1]) for w in initial}
    for size in range(3,7):
        for first in ['P','F']:
            for rest in itertools.product('RF',repeat=size-1):
                w=first+''.join(rest);key=min(w,w[::-1])
                if key not in seen:seen.add(key);words.append(w)
    return words


def _beam(spec):
    m=_model('2d');word=spec
    for i,s in enumerate(word):_node(m,f'N{i}',4.*i,0.,support=s if s!='U' else None)
    for i in range(len(word)-1):
        mid=_node(m,f'M{i}',4.*i+2.,0.)
        _member(m,f'B{i}a',f'N{i}',mid);_member(m,f'B{i}b',mid,f'N{i+1}')
    for e in m['elements']:_load(m,'D',type='distributed',element=e['id'],wz=-10.)
    for i in range(len(word)-1):
        if i%2==0:_load(m,'Q',type='nodal',node=f'M{i}',fz=-12.)
    _load(m,'W',type='nodal',node=f'M{len(word)-2}',fx=4.,fz=3.)
    return m


def _frame(spec, mixed=False):
    bays,stories,extra=spec;m=_model('2d')
    for j in range(stories+1):
        for i in range(bays+1):_node(m,f'N{i}-{j}',5.*i,3.2*j,support='F' if j==0 else None)
    for j in range(1,stories+1):
        for i in range(bays+1):_member(m,f'C{i}-{j}',f'N{i}-{j-1}',f'N{i}-{j}','column','C')
        for i in range(bays):
            if mixed and extra==1 and i==(j-1)%bays:
                mid=_node(m,f'H{j}',5.*i+2.5,3.2*j)
                _member(m,f'B{i}-{j}a',f'N{i}-{j}',mid)
                _member(m,f'B{i}-{j}b',mid,f'N{i+1}-{j}')
                _member(m,f'V{j}a',f'N{i}-{j-1}',mid,'truss','A')
                _member(m,f'V{j}b',f'N{i+1}-{j-1}',mid,'truss','A')
            else:_member(m,f'B{i}-{j}',f'N{i}-{j}',f'N{i+1}-{j}')
        if mixed and extra==0:
            i=(j-1)%bays
            _member(m,f'D{j}',f'N{i}-{j-1}',f'N{i+1}-{j}','truss','A')
    if not mixed and extra:
        tip=_node(m,'OVERHANG',5.*bays+2.2,3.2*stories)
        _member(m,'OVERHANG-B',f'N{bays}-{stories}',tip)
    _frame_loads(m);return m


def _truss(spec):
    panels,pattern=spec;m=_model('2d')
    for i in range(panels+1):
        _node(m,f'L{i}',3.*i,0.,support='P' if i==0 else 'R' if i==panels else None,axial=True)
        _node(m,f'U{i}',3.*i,2.4,axial=True)
        _member(m,f'V{i}',f'L{i}',f'U{i}','truss','A')
    for i in range(panels):
        for level in ['L','U']:_member(m,f'{level}C{i}',f'{level}{i}',f'{level}{i+1}','truss','A')
        up=pattern==0 or pattern==2 or i%2==0
        a,b=(f'L{i}',f'U{i+1}') if up else (f'U{i}',f'L{i+1}')
        _member(m,f'D{i}',a,b,'truss','A')
        if pattern==2:_member(m,f'X{i}',f'U{i}',f'L{i+1}','truss','A')
    for i in range(panels+1):
        _load(m,'D',type='nodal',node=f'U{i}',fz=-6. if i in [0,panels] else -12.)
        if 0<i<=panels//2:_load(m,'Q',type='nodal',node=f'U{i}',fz=-8.)
    _load(m,'W',type='nodal',node=f'U{panels}',fx=8.)
    return m


def _space_frame(spec):
    nx,ny,stories=spec;m=_model('3d')
    for j in range(stories+1):
        for i in range(nx+1):
            for k in range(ny+1):_node(m,f'N{i}-{k}-{j}',5.*i,3.2*j,4.*k,support='F' if j==0 else None)
    for j in range(1,stories+1):
        for i in range(nx+1):
            for k in range(ny+1):
                cur=f'N{i}-{k}-{j}'
                _member(m,f'C{i}-{k}-{j}',f'N{i}-{k}-{j-1}',cur,'column','C')
                if i<nx:_member(m,f'X{i}-{k}-{j}',cur,f'N{i+1}-{k}-{j}')
                if k<ny:_member(m,f'Y{i}-{k}-{j}',cur,f'N{i}-{k+1}-{j}')
    m['stories']=[{'id':f'S{j}','elevation':round(3.2*(j-1),6),'height':3.2,'rigid_diaphragm':False} for j in range(1,stories+1)]
    _frame_loads(m);return m


def _space_truss(spec):
    stories,pattern=spec;m=_model('3d');xy=[(0.,0.),(4.,0.),(1.5,3.)]
    for j in range(stories+1):
        for i,(x,y) in enumerate(xy):_node(m,f'N{i}-{j}',x,3.*j,y,support='T' if j==0 else None,axial=True)
    for j in range(1,stories+1):
        for i in range(3):
            k=(i+1)%3
            _member(m,f'H{i}-{j}',f'N{i}-{j}',f'N{k}-{j}','truss','A')
            _member(m,f'V{i}-{j}',f'N{i}-{j-1}',f'N{i}-{j}','truss','A')
            _member(m,f'D{i}-{j}',f'N{i}-{j-1}',f'N{k}-{j}','truss','A')
            if pattern in [1,2,3] and i<pattern:
                _member(m,f'X{i}-{j}',f'N{k}-{j-1}',f'N{i}-{j}','truss','A')
        if pattern==4:
            center=_node(m,f'CORE{j}',1.833333,3.*j-1.5,1.,axial=True)
            for k in range(3):
                for level in [j-1,j]:_member(m,f'CORE{j}-{k}-{level}',center,f'N{k}-{level}','truss','A')
        if pattern==5:
            tip=_node(m,f'OUT{j}',2.,3.*j-1.5,-1.5,axial=True)
            for suffix,n in [('a',f'N0-{j-1}'),('b',f'N1-{j-1}'),('c',f'N0-{j}')]:
                _member(m,f'OUT{j}-{suffix}',tip,n,'truss','A')
            _load(m,'Q',type='nodal',node=tip,fz=-4.)
    for i in range(3):_load(m,'D',type='nodal',node=f'N{i}-{stories}',fz=-12.)
    _load(m,'Q',type='nodal',node=f'N1-{stories}',fz=-7.)
    _load(m,'W',type='nodal',node=f'N2-{stories}',fx=8.,fy=5.)
    return m


def topology_fingerprint(model):
    """Conservative graph fingerprint, invariant to IDs/rigid transforms/scale.

    A color-refinement collision can undercount different graphs, never invent a
    difference between isomorphic colored graphs. Numerical geometry is used
    only to remove collinear free degree-two subdivision points. Materials,
    section dimensions, load magnitudes and family/variant labels are excluded.
    """
    m=deepcopy(model);nodes={n['id']:n for n in m['nodes']}
    dim=m['coordinate_system']['dimension'];only_axial=all(e['type'] in ['truss','brace'] for e in m['elements'])
    def color(n):
        r=n.get('restraints',[False]*6)
        return (sum(r[i] for i in ([0,2] if dim=='2d' else [0,1,2])),
                0 if only_axial else sum(r[i] for i in ([4] if dim=='2d' else [3,4,5])))
    edges=[(e['nodes'][0],e['nodes'][1],'axial' if e['type'] in ['truss','brace'] else 'frame') for e in m['elements']]
    changed=True
    while changed:
        changed=False
        for nid,n in list(nodes.items()):
            incidence=[(i,e) for i,e in enumerate(edges) if nid in e[:2]]
            if len(incidence)!=2 or color(n)!=(0,0):continue
            (i,e),(j,f)=incidence
            if e[2]!=f[2]:continue
            a=e[1] if e[0]==nid else e[0];b=f[1] if f[0]==nid else f[0]
            if a==b:continue
            va=[nodes[a][k]-n[k] for k in ['x','y','z']];vb=[nodes[b][k]-n[k] for k in ['x','y','z']]
            la=math.sqrt(sum(x*x for x in va));lb=math.sqrt(sum(x*x for x in vb));dot=sum(x*y for x,y in zip(va,vb))
            if la*lb and abs(dot/(la*lb)+1)<1e-10:
                edges=[v for k,v in enumerate(edges) if k not in [i,j]]+[(a,b,e[2])];del nodes[nid];changed=True;break
    attrs={nid:color(n) for nid,n in nodes.items()}
    unique=sorted(set(attrs.values()));labels={nid:unique.index(v) for nid,v in attrs.items()}
    for _ in range(len(nodes)):
        keys={nid:(labels[nid],tuple(sorted((typ,labels[b if a==nid else a]) for a,b,typ in edges if nid in [a,b]))) for nid in nodes}
        unique=sorted(set(keys.values()));labels={nid:unique.index(v) for nid,v in keys.items()}
    payload={'n':len(nodes),'e':len(edges),'vertices':sorted((attrs[nid],labels[nid]) for nid in nodes),
             'edges':sorted((min(labels[a],labels[b]),max(labels[a],labels[b]),typ) for a,b,typ in edges)}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _candidates(family):
    if family=='beam':return _beam_words()
    if family in ['frame','mixed']:return [(b,s,x) for s in range(1,7) for b in range(1,4) for x in [0,1]]
    if family=='truss':return [(n,p) for n in range(2,15) for p in range(3)]
    if family=='space_frame':return [(x,y,s) for s in range(1,7) for x,y in [(1,1),(1,2),(1,3),(2,2),(2,3),(3,3)]]
    if family=='space_truss':return [(s,p) for s in range(1,7) for p in range(6)]
    raise ValueError('Unknown family: '+family)


_FACTORIES={'beam':_beam,'frame':_frame,'truss':_truss,'space_frame':_space_frame,'space_truss':_space_truss,
            'mixed':lambda spec:_frame(spec,True)}
_SPECS={}


def _specs(family):
    if family not in _SPECS:
        found=[];seen=set()
        for spec in _candidates(family):
            fingerprint=topology_fingerprint(_FACTORIES[family](spec))
            if fingerprint in seen:continue
            seen.add(fingerprint);found.append(spec)
            if len(found)==VARIANTS:break
        if len(found)!=VARIANTS:raise AssertionError(f'{family}: only {len(found)} distinct conservative fingerprints')
        _SPECS[family]=found
    return _SPECS[family]


def build_model(family: str, variant: int, dimension: str='2d') -> dict:
    """Return a fresh model, variant 0..34; space_* families always use 3D."""
    if family not in FAMILIES:raise ValueError(f'family must be one of {FAMILIES}')
    if isinstance(variant,bool) or not isinstance(variant,int) or not 0<=variant<VARIANTS:raise ValueError('variant must be an integer in 0..34')
    if dimension not in ['2d','3d']:raise ValueError('dimension must be 2d or 3d')
    if not family.startswith('space_') and dimension!='2d':raise ValueError('Use a space_* family for three-dimensional models')
    m=_FACTORIES[family](_specs(family)[variant])
    # The topology catalogue is independent of this explicit engineering-size
    # catalogue. Different tasks need not repeatedly copy one identical A/I/J.
    group,column=divmod(variant,5)
    m['sections']=[_section('B',round(.16+.02*column,3),round(.28+.04*group,3)),
                   _section('C',round(.22+.025*column,3),round(.36+.04*group,3)),
                   _section('A',round(.06+.01*column,3),round(.08+.01*group,3))]
    return m


def variant_info(family: str, variant: int) -> dict:
    m=build_model(family,variant);spec=_specs(family)[variant]
    if family=='beam':meaning={'supportWord':spec,'supportCodes':{'F':'ux/uz/ry fixed','P':'ux/uz fixed','R':'uz fixed','U':'free end'},'observationNodes':'Each span has a free midspan station, removed in topology hashing.'}
    elif family in ['frame','mixed']:meaning={'bays':spec[0],'stories':spec[1],
        'feature':('alternating-bay chevron axial braces' if spec[2] else 'alternating-bay single axial braces') if family=='mixed' else ('roof overhang' if spec[2] else 'complete moment frame')}
    elif family=='truss':meaning={'panels':spec[0],'webPattern':['one ascending diagonal per panel','alternating diagonals','two crossing unconnected diagonals per panel'][spec[1]]}
    elif family=='space_frame':meaning={'xBays':spec[0],'yBays':spec[1],'stories':spec[2],'feature':'Complete rectangular bare frame; no rigid floor.'}
    else:meaning={'stories':spec[0],'pattern':['triangulated triangular prism','one double-diagonal face','two double-diagonal faces','three double-diagonal faces','additional interior six-bar node','additional external three-bar support node'][spec[1]]}
    return {'family':family,'variant':variant,'dimension':m['coordinate_system']['dimension'],'nodes':len(m['nodes']),
            'elements':len(m['elements']),'topologyFingerprint':topology_fingerprint(m),'structuralVariation':meaning,
            'sectionDimensionsMM':{s['id']:{'B':s['shape']['B'],'H':s['shape']['H']} for s in m['sections']},
            'commercialCompatible':family=='space_frame',
            'commercialQualification':'Geometry/section subset only; actual PKPM/YJK native verification still required.' if family=='space_frame' else 'OpenSees authoring subset'}


def catalogue():
    return [variant_info(f,v) for f in FAMILIES for v in range(VARIANTS)]


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output');a=p.parse_args();rows=catalogue()
    value={'models':len(rows),'uniqueTopologyFingerprints':len({r['topologyFingerprint'] for r in rows}),'rows':rows}
    raw=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    if a.output:
        with open(a.output,'x') as f:f.write(raw)
    else:print(raw)
