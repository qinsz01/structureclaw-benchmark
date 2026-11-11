"""Area-load reconstruction, equal-total load relocation and explicit mass rules."""
from copy import deepcopy
import math

from .mechanics import (G,clean,rename,add_load,self_weight,static_solutions,
                        node_envelope,lateral_envelope,force_envelope,COMBINATIONS,SELECTIONS,length)
from .support import legacy_refs

def roof_lines(model):
    lines={}
    for n in model['nodes']:
        row=lines.setdefault(round(n['y'],8),{});x=round(n['x'],8)
        if x not in row or n['z']>row[x]['z']:row[x]=n
    return [sorted(row.values(),key=lambda n:n['x']) for _,row in sorted(lines.items()) if len(row)>=2]

def area_rules(model,seed):
    lines=roof_lines(model);assert lines
    xmin=min(line[0]['x'] for line in lines);xmax=max(line[-1]['x'] for line in lines);ys=[line[0]['y'] for line in lines]
    return {'gravityMPerS2':G,'roofJointRule':'At each issued X/Y grid location take the highest issued joint; use adjacent joints on each Y line as strip bearings.',
      'loadSharing':'One-way strip resultant to its two bounding roof joints by integrating linear distance weights. Preserve force and first moment. This is an issued lumped deck model, not a plate/shell analysis.',
      'areaBasis':{'D':'horizontal projection','Q':'horizontal projection','W':'actual surface, pressure in the upward local normal'},
      'stripWidthM':round(2.6+.2*(seed%7),3) if len(ys)==1 else None,
      'planEdgesY':None if len(ys)==1 else [round(min(ys)-.35,6),round(max(ys)+.35,6)],
      'zones':[{'id':'WEST','startX':xmin,'endX':round(xmin+.43*(xmax-xmin),8),'D':round(1.1+.1*(seed%4),3),'Q':round(2.8+.2*(seed%5),3),'W':round(.45+.05*(seed%4),3)},
               {'id':'EAST','startX':round(xmin+.43*(xmax-xmin),8),'endX':xmax,'D':round(1.35+.1*(seed%3),3),'Q':round(4.2+.2*(seed%5),3),'W':round(.7+.05*(seed%4),3)}],
      'horizontalAction':{'fxKN':round(8+seed%8,3),'fyKN':round(4+seed%5,3) if model['coordinate_system']['dimension']=='3d' else 0.,'placement':'Equally over roof joints at the largest issued Z.'},
      'memberGravity':'Uniform explicit global -Z line load rho*A*g/1000 on beams/columns; half rho*A*L*g/1000 nodal loads at each axial-bar end. Automatic self_weight stays false.'}

def widths(model,rules):
    lines=roof_lines(model)
    if len(lines)==1:return [(lines[0],rules['stripWidthM'])]
    ys=[row[0]['y'] for row in lines];edges=[rules['planEdgesY'][0],*[(a+b)/2 for a,b in zip(ys,ys[1:])],rules['planEdgesY'][1]]
    return [(line,edges[i+1]-edges[i]) for i,line in enumerate(lines)]

def areas(model,rules,zones=None):
    zones=zones or rules['zones']
    return [sum(max(0.,min(line[-1]['x'],z['endX'])-max(line[0]['x'],z['startX']))*width for line,width in widths(model,rules)) for z in zones]

def revised_rules(model,base,seed):
    r=deepcopy(base);xmin=min(z['startX'] for z in base['zones']);xmax=max(z['endX'] for z in base['zones'])
    total=sum(a*z['Q'] for a,z in zip(areas(model,base),base['zones']))
    r['liveRevision']={'splitX':round(xmin+(.58+.02*(seed%3))*(xmax-xmin),8),'westEastPressureRatio':round(1.8+.15*(seed%4),3),'totalLiveKN':total,
                       'scope':'Only Q is redistributed; preserve original D/W zones, properties and gravity.'}
    return r

def load_zones(model,rules,case):
    if case!='Q' or not rules.get('liveRevision'):return [{'startX':z['startX'],'endX':z['endX'],'pressure':z[case]} for z in rules['zones']]
    v=rules['liveRevision'];xmin=min(z['startX'] for z in rules['zones']);xmax=max(z['endX'] for z in rules['zones']);zones=[{'startX':xmin,'endX':v['splitX']},{'startX':v['splitX'],'endX':xmax}]
    aw,ae=areas(model,rules,zones);east=v['totalLiveKN']/(aw*v['westEastPressureRatio']+ae)
    return [{**zones[0],'pressure':east*v['westEastPressureRatio']},{**zones[1],'pressure':east}]

def load_model(template,rules):
    m=clean(template);self_weight(m)
    for line,width in widths(m,rules):
        for a,b in zip(line,line[1:]):
            dx=b['x']-a['x'];dz=b['z']-a['z'];assert dx>0
            for case in ['D','Q','W']:
                for zone in load_zones(m,rules,case):
                    lo=max(a['x'],zone['startX']);hi=min(b['x'],zone['endX'])
                    if hi-lo<=1e-10:continue
                    # Integral of linear nodal sharing functions in projected X.
                    int_b=((hi-a['x'])**2-(lo-a['x'])**2)/(2*dx);int_a=(hi-lo)-int_b
                    for n,weight in [(a,int_a),(b,int_b)]:
                        q=zone['pressure']*width*weight
                        if case=='W':add_load(m,case,type='nodal',node=n['id'],fx=-q*dz/dx,fz=q)
                        else:add_load(m,case,type='nodal',node=n['id'],fz=-q)
    roofs=[n for line,_ in widths(m,rules) for n in line];zmax=max(n['z'] for n in roofs);tops={n['id']:n for n in roofs if abs(n['z']-zmax)<1e-9};action=rules['horizontalAction']
    for nid in tops:add_load(m,'W',type='nodal',node=nid,fx=action['fxKN']/len(tops),**({'fy':action['fyKN']/len(tops)} if action['fyKN'] else {}))
    if rules.get('addedEquipment'):
        row=rules['addedEquipment'];node=min(roofs,key=lambda n:(abs(n['x']-row['positionX']),-n['z'],abs(n['y'])))
        add_load(m,'D',type='nodal',node=node['id'],fz=-row['weightKN'])
    return m

def checks(model,rules):
    live=sum(-l.get('fz',0) for c in model['load_cases'] if c['id']=='Q' for l in c['loads'])
    expected=sum(a*z['pressure'] for a,z in zip(areas(model,rules,load_zones(model,rules,'Q')),load_zones(model,rules,'Q')))
    assert math.isclose(live,expected,rel_tol=1e-10,abs_tol=1e-8)
    return {'method':'independent-area-and-nodal-load-total','liveResultantKN':live,'geometricAreaM2':sum(areas(model,rules))}

def static_reference(model,rules):
    m=load_model(model,rules);rows=[]
    for selection,(fn,check) in zip(SELECTIONS,static_solutions(m)):
        rows.append({'selection':selection,'uz':node_envelope(m,fn,'uz'),'lateral':lateral_envelope(m,fn),'force':force_envelope(m,fn),'referenceCheck':check})
    def win(key):
        row=max(rows,key=lambda r:abs(r[key]['value']));return {**row[key],'selection':row['selection']}
    return {'model':m,'loadRules':deepcopy(rules),'metrics':{k:win(k) for k in ['uz','lateral','force']},'selections':deepcopy(SELECTIONS),'referenceChecks':[checks(m,rules),*[r['referenceCheck'] for r in rows]]}

def mass_model(template,rules,fraction):
    m=load_model(template,rules);mass={n['id']:0. for n in m['nodes']};elements={e['id']:e for e in m['elements']}
    for c in m['load_cases']:
        if c['id'] not in ['D','Q']:continue
        factor=1. if c['id']=='D' else fraction
        for l in c['loads']:
            if l['type']=='nodal':mass[l['node']]+=-l.get('fz',0)*factor/G
            elif l['type']=='distributed':
                e=elements[l['element']];value=-l.get('wz',0)*length(m,e)*factor/G
                for nid in e['nodes']:mass[nid]+=value/2
            else:raise ValueError('Mass rule must not silently ignore an unsupported load')
    for n in m['nodes']:
        if not n['restraints'][0] and mass[n['id']]>0:n['mass']=mass[n['id']]
    m['analysis_control'].update(mass_source='nodal',mass_directions=['x'])
    return m,{'method':'gravity-derived-explicit-X-nodal-mass','fractionQ':fraction,'totalParticipatingMassTonne':sum(n.get('mass',0) for n in m['nodes']),'massFrom':'D + fractionQ*Q, divided by g; support-X-fixed masses omitted; no density-derived automatic mass.'}

def dynamic_reference(template,rules,kind,seed):
    model,check=mass_model(template,rules,.3+.05*(seed%3))
    turn={'model':model,'kind':kind,'engine':'OpenSees','requests':[],'derived':[]}
    if kind=='modal':turn.update(parameters={'analysisType':'modal','numModes':2,'direction':'x'},requireShapes=True)
    else:
        dt=.01;duration=1.2
        motion=[round(.02*(1+.04*(seed%5))*math.sin((4+.15*(seed%7))*j*dt)*math.sin(math.pi*j*dt/duration)**2,10) for j in range(122)]
        nodes=[n for n in model['nodes'] if n.get('mass')]
        turn.update(parameters={'analysisType':'time_history','timeStep':dt,'duration':duration,'dampingRatio':.04,'direction':'x','groundMotion':motion,'groundMotionUnit':'g','monitorNodeIds':[n['id'] for n in nodes],'monitorElementIds':[model['elements'][0]['id']],'monitorSupportNodeIds':[n['id'] for n in model['nodes'] if n['restraints'][0]]},monitorNode=max(nodes,key=lambda n:(n['z'],n['x']))['id'])
    ref=legacy_refs.reference(turn);ref['referenceChecks'].append(check);ref['loadRules']=deepcopy(rules);ref['massRule']={'fractionQ':check['fractionQ'],'gravityMPerS2':G,'directions':['x'],'supportMassPolicy':'omit X-fixed supports'}
    return ref
