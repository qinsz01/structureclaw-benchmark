"""Independent direct-stiffness Euler-Bernoulli reference; no production or OpenSees imports.
6 global DOFs/node, consistent distributed loads, exact stations added to the reference mesh.
It is a cross-check for commercial cases, NOT their same-engine scoring truth.
"""
import math
import numpy as np


def axes(model,element,a,b):
    ex=(b-a)/np.linalg.norm(b-a)
    if model['coordinate_system']['dimension']=='2d':ey=np.array([0.,1.,0.]);ez=np.cross(ex,ey)
    else:
        ref=np.array(model['metadata']['elementReferenceVectors'][element['id']],float)
        ey=np.cross(ref,ex);ey/=np.linalg.norm(ey);ez=np.cross(ex,ey)
    angle=math.radians(element.get('rotation_angle',0));ey,ez=math.cos(angle)*ey+math.sin(angle)*ez,-math.sin(angle)*ey+math.cos(angle)*ez
    return np.vstack([ex,ey,ez])


def local_stiffness(element,material,section,L):
    E=material['E']*1000;G=material['G']*1000;p=section['properties'];k=np.zeros((12,12))
    k[np.ix_([0,6],[0,6])]=E*p['A']/L*np.array([[1,-1],[-1,1]])
    if element['type'] in ['truss','brace']:return k
    k[np.ix_([3,9],[3,9])]=G*p['J']/L*np.array([[1,-1],[-1,1]])
    for dofs,I,sign in [([1,5,7,11],p['Iz'],1),([2,4,8,10],p['Iy'],-1)]:
        c=6*L*sign
        k[np.ix_(dofs,dofs)]=E*I/L**3*np.array([[12,c,-12,c],[c,4*L**2,-c,2*L**2],[-12,-c,12,-c],[c,2*L**2,-c,4*L**2]])
    return k


def solve(model,factors,stations):
    nodes={n['id']:np.array([n['x'],n['y'],n['z']],float) for n in model['nodes']}
    restraints={n['id']:n['restraints'][:] for n in model['nodes']}
    elements={e['id']:e for e in model['elements']};materials={m['id']:m for m in model['materials']};sections={s['id']:s for s in model['sections']}
    loads=[dict(l,factor=factors.get(c['id'],0)) for c in model['load_cases'] for l in c['loads'] if factors.get(c['id'],0)]
    splits={e['id']:{0.,float(np.linalg.norm(nodes[e['nodes'][1]]-nodes[e['nodes'][0]]))} for e in model['elements']}
    for s in stations:
        if s['kind']=='member' and elements[s['id']]['type'] not in ['truss','brace']:splits[s['id']].add(float(s['positionM']))
    for l in loads:
        if l.get('element'):
            values=splits[l['element']]
            if l['type']=='point':values.add(float(l['position']))
            else:values.update([float(l.get('start',0)),float(l.get('end',max(values)))])
    segments=[];positions={}
    for eid,cuts in splits.items():
        e=elements[eid];a,b=[nodes[n] for n in e['nodes']];length=np.linalg.norm(b-a);R=axes(model,e,a,b);prev=None
        unique=[]
        for x in sorted(cuts):
            if not unique or abs(unique[-1]-x)>1e-9:unique.append(x)
        for i,x in enumerate(unique):
            name=e['nodes'][0] if x==0 else e['nodes'][1] if abs(x-length)<1e-9 else f'__{eid}@{x:.12g}'
            if name not in nodes:
                nodes[name]=a+(b-a)*x/length
                restraints[name]=[False,True,False,True,False,True] if model['coordinate_system']['dimension']=='2d' else [False]*6
            positions[eid,x]=name
            if prev:segments.append(dict(element=e,start=prev[0],end=x,nodes=[prev[1],name],R=R))
            prev=(x,name)
    frame_nodes={n for s in segments if s['element']['type'] not in ['truss','brace'] for n in s['nodes']}
    for n in nodes:
        if n not in frame_nodes:restraints[n][3:]=[True]*3
    idx={n:i*6 for i,n in enumerate(nodes)};K=np.zeros((6*len(nodes),6*len(nodes)));F=np.zeros(len(K))
    for l in loads:
        if l['type'] not in ['nodal','point']:continue
        n=l.get('node') or positions[l['element'],float(l['position'])]
        F[idx[n]:idx[n]+6]+=np.array([l.get(k,0) for k in ['fx','fy','fz','mx','my','mz']])*l['factor']
    for s in segments:
        e=s['element'];L=s['end']-s['start'];R=s['R'];T=np.zeros((12,12))
        for i in range(4):T[i*3:i*3+3,i*3:i*3+3]=R
        k=local_stiffness(e,materials[e['material']],sections[e['section']],L);f=np.zeros(12)
        for l in loads:
            if l['type']!='distributed' or l.get('element')!=e['id']:continue
            mid=(s['start']+s['end'])/2
            if not(l.get('start',0)<=mid<=l.get('end',max(splits[e['id']]))):continue
            q=R@np.array([l.get(k,0) for k in ['wx','wy','wz']])*l['factor']
            f[:3]+=q*L/2;f[6:9]+=q*L/2
            f[5]+=q[1]*L*L/12;f[11]-=q[1]*L*L/12;f[4]-=q[2]*L*L/12;f[10]+=q[2]*L*L/12
        dofs=[idx[n]+i for n in s['nodes'] for i in range(6)]
        K[np.ix_(dofs,dofs)]+=T.T@k@T;F[dofs]+=T.T@f;s.update(k=k,T=T,f=f,dofs=dofs)
    free=[idx[n]+i for n,r in restraints.items() for i,fixed in enumerate(r) if not fixed]
    u=np.zeros(len(K));u[free]=np.linalg.solve(K[np.ix_(free,free)],F[free]);r=K@u-F
    residual=float(np.max(np.abs(r[free]))) if free else 0
    if residual>1e-7*(1+np.max(np.abs(F))):raise ValueError(f'Equilibrium residual {residual}')
    for s in segments:s['actions']=s['k']@s['T']@u[s['dofs']]-s['f']
    def quantity(location,component):
        if location['kind']=='node':
            n=location['id'];order=['ux','uy','uz','rx','ry','rz'] if component[0] in 'ur' else ['fx','fy','fz','mx','my','mz']
            return float((u if component[0] in 'ur' else r)[idx[n]+order.index(component)])
        eid=location['id'];x=float(location['positionM'])
        if component[0]=='u':
            name=next(n for (element,station),n in positions.items() if element==eid and abs(station-x)<1e-9)
            return float(u[idx[name]+['ux','uy','uz'].index(component)])
        ss=[s for s in segments if s['element']['id']==eid and s['start']-1e-9<=x<=s['end']+1e-9]
        s=ss[0] if location['side']=='left' else ss[-1];start=abs(x-s['start'])<1e-9;actions=s['actions'][:6] if start else s['actions'][6:]
        i=['N','V2','V3','T','M2','M3'].index(component)
        if s['element']['type'] in ['truss','brace'] and component=='N':return float(-actions[0] if start else actions[0])
        signs=[-1,1,1,-1,-1,-1] if start else [1,-1,-1,1,1,1]
        return float(actions[i]*signs[i])
    external=np.zeros(6);reaction=np.zeros(6)
    for n,xyz in nodes.items():
        fi=F[idx[n]:idx[n]+6];ri=r[idx[n]:idx[n]+6];external[:3]+=fi[:3];external[3:]+=fi[3:]+np.cross(xyz,fi[:3]);reaction[:3]+=ri[:3];reaction[3:]+=ri[3:]+np.cross(xyz,ri[:3])
    return quantity,dict(method='independent-direct-stiffness',freeResidual=residual,forceMomentBalance=(external+reaction).tolist(),dofs=len(K))
