"""Explicit source-faithful spatial-frame data, STD-079 through STD-088."""
from std_b_common import *

# Each row fixes the original grid, elevations, material and loading scheme.
SPECS = {
79: dict(xs=[0,6], ys=[0,5], zs=[3.6,7.2], qx=[[25,25],[25,25]], material='steel'),
80: dict(xs=[0,6,12], ys=[0,5], zs=[3.6,7.2], qx=[[20,20],[20,20]], material='steel'),
81: dict(xs=[0,6], ys=[0,5,10], zs=[3.3,6.6,9.9], qx=[[25,50,25]]*3, material='steel'),
82: dict(xs=[0,6,12], ys=[0,5,10], zs=[3.6,7.2], qx=[[25,50,25],[20,40,20]], material='steel'),
83: dict(xs=[0,6,12], ys=[0,5], zs=[3.6,7.2], qx=[[30,30],[30,30]], material='C40/C30'),
84: dict(xs=[0,6,12], ys=[0,5], zs=[3.6,7.2], qx=[[30,30],[25,25]], material='C30'),
85: dict(xs=[0,4,11], ys=[0,3,9], zs=[3.4,7.5], qxy=(10,6), material='steel'),
86: dict(xs=[0,6,12], ys=[0,5,10], zs=[3.6,7.2], qall=8, material='steel', absent='northeast-cell'),
87: dict(xs=[0,6,12], ys=[0,5,10], zs=[3.6,7.2], qall=10, material='steel', absent='upper-east-bays'),
88: dict(xs=[0,6,12], ys=[0,5], zs=[3.6,7.2], qall=8, material='steel', lateral=[(1,10,8),(2,20,16)]),
}

PROMPTS = {
79: '建立两层空间钢框架：X向6m一跨、Y向5m一跨，两层层高各3.6m。柱脚六自由度固定，楼层无刚性楼板。每层楼面10kN/m²单向传给X梁，两条Y轴线各取2.5m受荷宽度，每根X梁向下25kN/m；Y梁不重复加载。计算工况D，报告每层四角节点三向位移、全部四柱列逐层X/Y层间位移差、四柱脚六分量反力及X/Y梁两端六分量内力。',
80: 'Use PKPM native analysis for a two-story steel space frame: X bays 6+6 m, one Y bay 5 m, story heights 3.6+3.6 m. All six bases are fixed in six DOFs; floors have no diaphragm constraints. Each floor has 8 kN/m² carried one-way by X beams: 20 kN/m downward on every X beam, with no duplicate Y-beam load. Analyze D. Report the three translations of all six nodes at each floor, X/Y story displacement differences on every column line, six-component reactions at all six bases, and all beam/column end-force components (covering the representative members requested).',
81: '采用YJK原生计算三层空间钢框架：X向一跨6m、Y向两跨5+5m，层高均3.3m。全部柱脚六自由度固定，无刚性楼板。每层面载10kN/m²单向分配给X梁，Y=0/5/10m轴线的X梁分别向下25/50/25kN/m；Y梁不重复加载。计算D，报告每层六节点三向位移、六柱列逐层X/Y层间位移差、全部底层柱两端六分量内力和六柱脚反力。',
82: 'Use PKPM native analysis for a two-story steel space frame with X bays 6+6 m, Y bays 5+5 m and story heights 3.6+3.6 m. All nine bases are fixed in six DOFs; do not impose floor diaphragm constraints. Floor loads are 10 and 8 kN/m². Load only X beams: at Y=0/5/10 m, downward line loads are 25/50/25 kN/m on floor 1 and 20/40/20 kN/m on floor 2. Analyze D. Report all nine floor-node translations at each level, X/Y story differences for every column line, all corner/edge/interior base reactions and every beam end-force vector, including both beam directions.',
83: '采用PKPM原生计算两层空间混凝土框架：X=0/6/12m，Y=0/5m，层高各3.6m，六柱脚固定，无刚性楼板。首层柱用C40（E=32500MPa），上层柱与全部梁用C30（E=30000MPa），两材料ν=0.2、密度2500kg/m³，G由E/[2(1+ν)]给出。各层楼面12kN/m²单向传给X梁，每根X梁向下30kN/m，Y梁不加载。计算D，报告每层六节点三向位移、六柱列X/Y层间差、所有首层与上层柱端力及全部柱脚六分量反力，并列出材料分配。',
84: 'Use YJK native analysis for a two-story concrete space frame: X bays 6+6 m, Y bay 5 m, story heights 3.6+3.6 m. All six bases are fixed, with no floor diaphragms. All members use C30 concrete: E=30000 MPa, nu=0.2, G=12500 MPa and density 2500 kg/m³. Floor loads 12 and 10 kN/m² act one-way on X beams, giving 30 kN/m on floor 1 and 25 kN/m on floor 2, downward. Y beams are unloaded. Analyze D and report the three translations of each of the six floor nodes, X/Y story differences along all column lines, six-component base reactions and both-end forces of every column by floor.',
85: '采用YJK原生计算不等网格两层空间钢框架：X=0/4/11m，Y=0/3/9m，层高3.4m、4.1m，楼层标高3.4m、7.5m。全部柱脚固定；完整构件连接表中同层相邻轴线间梁实际存在，按表连接，不另加对角梁。各X梁向下10kN/m，各Y梁向下6kN/m。计算D，报告每层九节点三向位移、所有柱列X/Y层间位移差、九柱脚反力和所有长短跨梁两端六分量内力。',
86: 'Use PKPM native analysis for a two-story L-plan steel frame. Start from grid X=0/6/12 m and Y=0/5/10 m; remove the northeast cell region at both floors. The actual member table is authoritative: the line at X=12 m stops at Y=5 m and the line at Y=10 m stops at X=6 m; the re-entrant corner (6,5) remains. Story heights are 3.6+3.6 m. All eight existing bases are fixed in six DOFs. Apply 8 kN/m downward to each existing floor beam only. Analyze D and report three translations at every outer and re-entrant floor corner, X/Y story differences along every existing column line, and all base-reaction components.',
87: '采用YJK原生计算退台空间钢框架：首层X向6+6m、Y向5+5m，二层仅保留左侧X=0至6m的1×2跨；两层层高各3.6m。首层九柱脚全部固定，二层仅X=0/6m轴线有上层柱和楼层梁，X=12m柱线在首层终止。每根实际楼层梁向下10kN/m。计算D，报告退台边与各层角点三向位移、实际柱列X/Y层间位移差、全部支反力和退台转接节点所有入射梁柱两端内力。无刚性楼板。',
88: 'Use YJK native analysis for a two-story steel space frame with X bays 6+6 m, Y bay 5 m and 3.6 m story heights. All six bases are fixed in six DOFs. D is 8 kN/m downward on every floor beam. At the right rear corner (12,5), apply Wx in +X: 10 kN at floor 1 and 20 kN at floor 2; Wy is a separate +Y case with 8 and 16 kN at those same levels. Analyze combinations C0=D, CX=D+Wx and CY=D+Wy independently. Report X/Y corner displacements at both levels, X/Y story differences on all column lines, six-component base reactions and the governing combination for each requested displacement, drift and reaction component. Retain the signed value of each maximum-absolute response.',
}

def build(number):
    s=SPECS[number]
    keep=None
    if number==86: keep=lambda ix,iy,j:not(ix==2 and iy==2)
    if number==87: keep=lambda ix,iy,j:j<2 or ix<2
    m=spatial(s['xs'],s['ys'],s['zs'],keep=keep,concrete=s['material']!='steel')
    # Frozen missing appendix: fully elastic rectangular solid sections, explicitly supplied.
    m['sections']=[section('B1',.3,.6),section('B2',.3,.7),section('C1',.5,.5)]
    if number in (83,84):
        m['materials']=[dict(id='M1',name='C30',type='concrete',E=30000,G=12500,nu=.2,rho=2500)]
    if number==83:
        m['materials'].append(dict(id='M2',name='C40',type='concrete',E=32500,G=32500/2.4,nu=.2,rho=2500))
        for e in m['elements']:
            if e['type']=='column' and e['id'].endswith('-1'): e['material']='M2'
    for e in m['elements']:
        if e['type']!='beam':continue
        j=int(e['id'].split('-')[-1]); iy=int(e['id'].split('-')[1])
        q=0
        if 'qx' in s and e['id'].startswith('x'): q=s['qx'][j-1][iy]
        if 'qxy' in s: q=s['qxy'][0 if e['id'].startswith('x') else 1]
        if 'qall' in s:q=s['qall']
        if q:load(m,type='distributed',element=e['id'],wz=-q)
    selections=['D']
    if number==88:
        for j,fx,fy in s['lateral']:
            load(m,'Wx',type='nodal',node=f'n2-1-{j}',fx=fx)
            load(m,'Wy',type='nodal',node=f'n2-1-{j}',fy=fy)
        m['load_combinations']=[dict(id='C0',factors={'D':1}),dict(id='CX',factors={'D':1,'Wx':1}),dict(id='CY',factors={'D':1,'Wy':1})]
        selections=['C0','CX','CY']
    r=Requests(m); ids={n['id'] for n in m['nodes']}
    for sel in selections:
        for j in range(1,len(s['zs'])+1):
            for ix in range(len(s['xs'])):
                for iy in range(len(s['ys'])):
                    nid=f'n{ix}-{iy}-{j}'; lower=f'n{ix}-{iy}-{j-1}'
                    if nid not in ids:continue
                    r.node(nid,('ux','uy','uz'),sel)
                    if lower in ids:r.drift(lower,nid,('ux','uy'),sel)
        r.supports(sel)
        for e in m['elements']:
            needed=(number in (79,82,85) and e['type']=='beam') or number==80 or (number==81 and e['type']=='column' and e['id'].endswith('-1')) or (number in (83,84) and e['type']=='column')
            if number==87:
                edge={f'n1-{iy}-{j}' for iy in range(3) for j in (1,2)}
                needed=bool(set(e['nodes']) & edge)
            if needed:r.ends(e['id'],selection=sel)
    if number==88:
        # Across selections, freeze a separate governing request per physical location/component.
        groups={}
        for q in r.quantities:
            key=(q['location']['id'],q['component'])
            groups.setdefault(key,[]).append(q['id'])
        for (nid,c),ops in groups.items():
            unit=next(q['unit'] for q in r.quantities if q['id']==ops[0])
            r.derive(f'governing-{nid}-{c}','max_abs',ops,f'Governing signed {c} at {nid}; retain combination',unit)
        groups={}
        for d in list(r.derived):
            if '-drift-' in d['id']:groups.setdefault(d['id'].split('-drift-',1)[1],[]).append(d['id'])
        for key,ops in groups.items(): r.derive('governing-drift-'+key,'max_abs',ops,'Governing signed story displacement difference; retain combination')
    notes=[
        'The source leaves the property appendix to the author. Frozen sections: X beams B1 solid rectangle 300x600 mm, Y beams B2 solid rectangle 300x700 mm, columns C1 solid square 500x500 mm. E/G, A/Iy/Iz/J and local reference vectors are explicit in public input; no section catalog or solver defaults apply.',
        'All story drift requests are signed upper-node displacement minus lower-node displacement, for every existing column line. No diaphragm average replaces column-line results.',
        'Broad source terms such as representative beam/column end forces are resolved by requesting all relevant members, rather than omitting an unspecified representative location.',
    ]
    if number==86:notes.append('The northeast cell is absent: omit only the corner column line (12,10) and its incident edge beams; retain the re-entrant corner (6,5) and boundary beams of the remaining three cells. No duplicate nodes or phantom fourth-cell elements.')
    if number==87:notes.append('Upper east bays are absent; transfer-node end forces include every member incident to X=6 at levels 3.6 and 7.2 m. The source does not designate a single transfer member, so all are covered.')
    interactions=[]
    if number==83:interactions=['列出首层柱C40与上层柱/全部梁C30的材料分配表。']
    emit(number,m,PROMPTS[number],r,notes=notes,interactions=interactions)
    return m,r

if __name__=='__main__':
    # Commercial cases are authored first; then the corresponding OpenSees case.
    for number in [80,81,82,83,84,85,86,87,88,79]:build(number)
