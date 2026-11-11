"""Independent planar Euler-Bernoulli assembly and linear dynamics, no SUT imports.

Canonical planar DOFs are global ux, uz, ry. End bending releases are statically
condensed before assembly. Massless rotations are condensed for the eigenproblem.
Only the explicitly authored pilot load/element subset is accepted.
"""
import math
import numpy as np


def assembly(model, factors=None):
    assert model['coordinate_system']['dimension']=='2d'
    nodes={n['id']:n for n in model['nodes']}; ids=list(nodes); index={k:3*i for i,k in enumerate(ids)}
    mats={m['id']:m for m in model['materials']}; secs={s['id']:s for s in model['sections']}
    n=3*len(ids); K=np.zeros((n,n)); F=np.zeros(n); fixed={}; records=[]
    for nid,node in nodes.items():
        for i,j in enumerate([0,2,4]):
            if (node.get('restraints') or [False]*6)[j]: fixed[index[nid]+i]=0.
    factors=factors or {}; loads=[]
    for case in model.get('load_cases',[]):
        for load in case['loads']:
            loads.append((load,float(factors.get(case['id'],0))))
    if model.get('analysis_control',{}).get('self_weight'):
        control=model['analysis_control']; case=control['self_weight_case_id']; g=9.80665
        assert control.get('gravity_direction','-z') in ('-z',None)
        for e in model['elements']:
            w=mats[e['material']]['rho']*secs[e['section']]['properties']['A']*g/1000
            loads.append(({'type':'distributed','element':e['id'],'wz':-w},float(factors.get(case,0))))
    for load,factor in loads:
        if not factor: continue
        typ=load.get('type','nodal')
        if typ=='nodal':
            assert not load.get('element')
            F[index[load['node']]:index[load['node']]+3] += factor*np.array([load.get(k,0) for k in ['fx','fz','my']])
        elif typ=='displacement':
            for i,k in enumerate(['ux','uz','ry']):
                if k in load: fixed[index[load['node']]+i]=factor*load[k]
        elif typ!='distributed': raise ValueError('Unreviewed independent load '+typ)
    for e in model['elements']:
        a,b=[nodes[k] for k in e['nodes']]; dx=b['x']-a['x']; dz=b['z']-a['z']; L=math.hypot(dx,dz)
        c,s=dx/L,dz/L
        # Local transverse direction=(-s,c); local in-plane rotation=-global Ry.
        R=np.array([[c,s,0],[-s,c,0],[0,0,-1.]])
        T=np.zeros((6,6));T[:3,:3]=R;T[3:,3:]=R
        p=secs[e['section']]['properties']; E=mats[e['material']]['E']*1000
        k=np.zeros((6,6));k[np.ix_([0,3],[0,3])]=E*p['A']/L*np.array([[1,-1],[-1,1]])
        f=np.zeros(6)
        if e['type'] in ['beam','column']:
            assert e.get('rotation_angle',0) in [0,90]
            I=p['Iz'] if e.get('rotation_angle',0)==90 else p['Iy']
            k[np.ix_([1,2,4,5],[1,2,4,5])]=E*I/L**3*np.array([
                [12,6*L,-12,6*L],[6*L,4*L**2,-6*L,2*L**2],
                [-12,-6*L,12,-6*L],[6*L,2*L**2,-6*L,4*L**2]])
        else: assert e['type'] in ['truss','brace']
        for load,factor in loads:
            if not factor or load.get('element')!=e['id']: continue
            assert load['type']=='distributed' and not any(k in load for k in ['start','end','points','segments'])
            assert e['type'] in ['beam','column']
            wx,wz=load.get('wx',0)*factor,load.get('wz',0)*factor
            qa,qv=(wx,wz) if load.get('reference_frame','global')=='local' else (c*wx+s*wz,-s*wx+c*wz)
            f += np.array([qa*L/2,qv*L/2,qv*L**2/12,qa*L/2,qv*L/2,-qv*L**2/12])
        released=[]
        for end,j in [('i',2),('j',5)]:
            flags=(e.get('releases') or {}).get(end,{})
            if flags:
                assert flags=={'ry':True} and e.get('rotation_angle',0)==0
                released.append(j)
        k0,f0=k.copy(),f.copy()
        if released:
            rr=np.ix_(released,released);inv=np.linalg.inv(k[rr]);coupling=k[:,released].copy()
            k=k-coupling@inv@k[released,:];f=f-coupling@inv@f[released]
            k[released,:]=0;k[:,released]=0;f[released]=0
        dofs=[index[nid]+i for nid in e['nodes'] for i in range(3)]
        K[np.ix_(dofs,dofs)] += T.T@k@T;F[dofs] += T.T@f
        records.append({'element':e,'dofs':dofs,'T':T,'k':k0,'f':f0,'released':released})
    active=[i for i in range(n) if i not in fixed and np.linalg.norm(K[i])>1e-12]
    null=[i for i in range(n) if i not in fixed and i not in active]
    assert all(abs(F[i])<1e-12 for i in null),'Load on undefined DOF'
    return {'K':K,'F':F,'fixed':fixed,'free':active,'null':null,'ids':ids,'index':index,'elements':records}


def static(model,factors):
    a=assembly(model,factors); K,F=a['K'],a['F'];u=np.zeros(len(F));fixed=list(a['fixed']);free=a['free']
    u[fixed]=list(a['fixed'].values())
    if free: u[free]=np.linalg.solve(K[np.ix_(free,free)],F[free]-K[np.ix_(free,fixed)]@u[fixed])
    r=K@u-F
    assert max((abs(r[i]) for i in free),default=0)<1e-7*(1+np.max(abs(F)))
    values={}
    for nid in a['ids']:
        start=a['index'][nid]
        values[nid]={k:float(u[start+i]) for i,k in enumerate(['ux','uz','ry']) if start+i not in a['null']}
        values[nid].update({k:float(r[start+i]) for i,k in enumerate(['Fx','Fz','My'])})
    return values, {'method':'independent-planar-direct-stiffness','freeResidual':max((abs(r[i]) for i in free),default=0),'dofs':len(F)}


def modes(model):
    a=assembly(model);free=a['free'];K=a['K'][np.ix_(free,free)]
    massive=[];mass=[]
    for nid in a['ids']:
        m=next(n for n in model['nodes'] if n['id']==nid).get('mass',0)
        dof=a['index'][nid]
        if m>0 and dof in free: massive.append(free.index(dof));mass.append(m)
    assert model['analysis_control']['mass_source']=='nodal'
    assert model['analysis_control']['mass_directions']==['x']
    massless=[i for i in range(len(free)) if i not in massive]
    S=np.zeros((len(free),len(massive)));S[massive,:]=np.eye(len(massive))
    if massless:
        S[massless,:]=-np.linalg.solve(K[np.ix_(massless,massless)],K[np.ix_(massless,massive)])
    kc=S.T@K@S;m=np.array(mass);D=np.diag(1/np.sqrt(m))
    eigenvectors=np.linalg.eigh(D@kc@D)
    lam=eigenvectors[0];vectors=D@eigenvectors[1]
    assert np.all(lam>0)
    shape={nid:[float((S@vectors)[free.index(a['index'][nid]),j]) if a['index'][nid] in free else 0.
                       for j in range(len(lam))] for nid in a['ids']}
    effective=[float((m@vectors[:,j])**2/(vectors[:,j]@(m*vectors[:,j]))) for j in range(len(lam))]
    return {'periods':(2*math.pi/np.sqrt(lam)).tolist(),'omega':np.sqrt(lam).tolist(),
            'effectiveMass':effective,'totalMass':float(sum(m)),'shape':shape,
            'K':kc,'mass':m,'S':S,'free':free,'assembly':a}


def transient(model,parameters,refine=1):
    modal=modes(model);omega=modal['omega'];zeta=parameters['dampingRatio']
    if len(omega)>1: alpha=2*zeta*omega[0]*omega[1]/sum(omega[:2]);beta=2*zeta/sum(omega[:2])
    else: alpha=2*zeta*omega[0];beta=0
    K=modal['K'];M=np.diag(modal['mass']);C=alpha*M+beta*K
    dt=parameters['timeStep']/refine
    motion=np.array(parameters['groundMotion'])*(9.80665 if parameters.get('groundMotionUnit','m/s2')=='g' else 1)
    duration=parameters['duration'];steps=int(math.floor(duration/dt));u=np.zeros(len(M));v=u.copy();acc=u.copy();rows=[]
    lhs=M+C*dt/2+K*dt*dt/4
    for i in range(1,steps+1):
        ground=float(np.interp(i/refine,np.arange(len(motion)),motion,right=0))
        up=u+dt*v+dt*dt*acc/4;vp=v+dt*acc/2
        acc=np.linalg.solve(lhs,-M@np.ones(len(M))*ground-C@vp-K@up)
        u=up+dt*dt*acc/4;v=vp+dt*acc/2
        global_u=np.zeros(len(modal['assembly']['F']));global_u[modal['free']]=modal['S']@u
        nodes={nid:{'ux':float(global_u[modal['assembly']['index'][nid]])} for nid in modal['assembly']['ids']}
        rows.append({'time':i*dt,'nodes':nodes})
    return rows,{'method':'independent-condensed-linear-Newmark','dt':dt,'alphaMass':alpha,'betaCurrentStiffness':beta}
