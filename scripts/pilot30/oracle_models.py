"""Maintainer-only legal representations; never used by the public solver broker."""
from copy import deepcopy
import math


def canonical(model,engine):
    m=deepcopy(model)
    if m['coordinate_system']['dimension']=='2d':
        m.get('metadata',{}).pop('elementReferenceVectors',None)
    if engine!='YJK':return m
    # The existing YJK adapter verifies executed physical members one-to-one.
    # Its native building mesh intersects a roof beam with lower-story grid
    # lines. State those cuts explicitly, rather than changing any stiffness or
    # accepting an unverifiable native model. Only whole-member uniform loads
    # are supported by this scoped maintainer transformation.
    nodes={n['id']:n for n in m['nodes']};original=list(m['nodes']);elements=[];mapping={}
    for e in m['elements']:
        a,b=[nodes[n] for n in e['nodes']]
        if e['type']!='beam' or abs(a['z']-b['z'])>1e-10:
            elements.append(e);continue
        delta=[b[k]-a[k] for k in ['x','y','z']];length=math.sqrt(sum(v*v for v in delta));cuts={}
        for n in original:
            if n['z']>=a['z']-1e-10:continue
            p=[n['x'],n['y'],a['z']];t=sum((p[i]-a[k])*delta[i] for i,k in enumerate(['x','y','z']))/length**2
            if 1e-9<t<1-1e-9 and math.dist(p,[a[k]+t*delta[i] for i,k in enumerate(['x','y','z'])])<1e-9:cuts[round(t,12)]=p
        if not cuts:elements.append(e);continue
        assert not e.get('releases') and not e.get('offsets')
        chain=[e['nodes'][0]];positions=[0.]
        for j,(t,p) in enumerate(sorted(cuts.items()),1):
            nid=f"cut-{e['id']}-{j}"
            new={'id':nid,**dict(zip(['x','y','z'],p)),'restraints':[False]*6}
            if a.get('story'):new['story']=a['story']
            m['nodes'].append(new);chain.append(nid);positions.append(t*length)
        chain.append(e['nodes'][1]);positions.append(length);parts=[]
        for i,(n1,n2) in enumerate(zip(chain,chain[1:])):
            piece=deepcopy(e);piece['id']=e['id'] if i==0 else f"{e['id']}-part-{i+1}";piece['nodes']=[n1,n2];elements.append(piece)
            parts.append({'element':piece['id'],'startM':positions[i],'endM':positions[i+1]})
            vectors=m.get('metadata',{}).get('elementReferenceVectors',{})
            if e['id'] in vectors:vectors[piece['id']]=deepcopy(vectors[e['id']])
        mapping[e['id']]=parts
    m['elements']=elements
    if mapping:
        for case in m['load_cases']:
            loads=[]
            for load in case['loads']:
                if load.get('element') not in mapping:loads.append(load);continue
                assert load['type']=='distributed' and not any(k in load for k in ['start','end','points','segments'])
                for part in mapping[load['element']]:
                    v=deepcopy(load);v['element']=part['element'];loads.append(v)
            case['loads']=loads
        m.setdefault('metadata',{})['physicalMemberSegments']=mapping
    return m
