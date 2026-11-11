"""Independent attachment/source invariants for the MM-A authored candidates.

DXF physical entities are parsed back rather than trusting the authoring builder.
PNG/SVG pairing, locale, turn secrecy and fixed source-load totals are checked.
This does not claim an independent image reconstruction or native acceptance.
"""
from pathlib import Path
import argparse, json, math, re, xml.etree.ElementTree as ET
from PIL import Image, ImageFont

ROOT=Path(__file__).resolve().parents[2]
CASES=ROOT/'corpora/research-300/cases'

# Independently transcribed force resultants from the planning source rows.
# Moments and topology have separate checks; a resultant is not proof of a model.
SOURCE_FZ={
 1:{'D':-120},2:{'D':0},3:{'D':-85},4:{'D':-131},5:{'D':-25},
 6:{'D':-60},7:{'D':-15},8:{'D':-54},9:{'D':-15},10:{'D':-32,'L':-24},
 11:{'D':-90},12:{'D':-20},13:{'D':-128},14:{'D':-45},15:{'D':-132},
 16:{'D':-152},17:{'D':-195},18:{'D':-107},19:{'D':-112,'L':-60,'W':16},20:{'D':-166},
 21:{'D':-142},22:{'D':-128},23:{'D':-50},24:{'D':-144,'W':42},25:{'D':-60},
 26:{'D':-154,'L':-100},27:{'D':-50},28:{'D':-45},29:{'D':-60},30:{'D':-48},
 31:{'D':-60},32:{'D':-40},33:{'D':-40},34:{'D':-36},35:{'D':-36},
 36:{'D':-30},37:{'D':-36},38:{'D':-45},39:{'D':-48},40:{'D':-30},
 41:{'D':-50},42:{'D':-30},43:{'D':-12*math.hypot(9,2)},
 44:{'D':-108-12*math.hypot(9,2)},45:{'D':-8*math.hypot(21,1.5)},
 46:{'D':-265},47:{'D':-180},48:{'D':-12*math.hypot(10,2)},
 49:{'D':-5*(math.hypot(6,2)+math.hypot(8,1))-7*(math.hypot(4,2)+math.hypot(6,3))},
 50:{'D':-246},
}
SOURCE_MOMENT_Y={2:12,9:15,14:25,25:20}

def check(condition,message):
    if not condition:raise AssertionError(message)

def dxf_entities(path):
    lines=path.read_text(encoding='ascii').splitlines()
    check(len(lines)%2==0,'DXF requires code/value pairs')
    pairs=list(zip(lines[::2],lines[1::2]));entities=[];entity=None
    for code,value in pairs:
        int(code)
        if code=='0':
            if entity is not None:entities.append(entity)
            entity={'type':value}
        elif entity is not None:entity[code]=value
    check(pairs[-1]==('0','EOF'),'DXF EOF missing')
    return entities

def texts(path):
    if path.suffix=='.svg':
        tree=ET.parse(path)
        check(not any('metadata' in e.tag for e in tree.iter()),'SVG hidden metadata')
        return '\n'.join(e.text or '' for e in tree.iter() if e.tag.endswith('text'))
    return path.read_text() if path.suffix in ['.txt','.dxf'] else ''

def check_projection_labels(path):
    """Check actual glyph extents, including partial overlaps and clipping.

    Applied to the separated multiview sheets, where every label must have its
    own readable space. This does not replace viewing the rendered PNG.
    """
    tree=ET.parse(path);root=tree.getroot();boxes=[];fonts={}
    font_path=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    if not font_path.exists():font_path=font_path.with_name('NotoSerifCJK-Regular.ttc')
    for e in tree.iter():
        if not e.tag.endswith('text') or not (e.text or '').strip():continue
        size=int(e.attrib['font-size'])
        if size not in fonts:fonts[size]=ImageFont.truetype(str(font_path),size)
        x=float(e.attrib['x']);y=float(e.attrib['y'])-size
        left,top,right,bottom=fonts[size].getbbox(e.text)
        box=(x+left,y+top,x+right,y+bottom)
        check(0<=box[0]<box[2]<=float(root.attrib['width']) and
              0<=box[1]<box[3]<=float(root.attrib['height']),f'{path.name}: clipped label {e.text}')
        for other,text in boxes:
            overlap_x=min(box[2],other[2])-max(box[0],other[0])
            overlap_y=min(box[3],other[3])-max(box[1],other[1])
            check(overlap_x<=1 or overlap_y<=1,f'{path.name}: overprinted labels {text!r} / {e.text!r}')
        boxes.append((box,e.text))
    return len(boxes)

def check_text_anchors(tree,name):
    anchors={}
    for e in tree.iter():
        if e.tag.endswith('text'):
            anchor=(round(float(e.attrib['x']),3),round(float(e.attrib['y']),3))
            anchors.setdefault(anchor,set()).add(e.text or '')
    for anchor,labels in anchors.items():
        check(len(labels)==1,f'{name}: distinct labels overprint at {anchor}: {sorted(labels)}')

def audit(path):
    cid=path.name;num=int(cid[3:]);contract=json.loads((path/'contract.json').read_text());model=json.loads((path/'model-state-1.json').read_text())
    nodes={n['id']:n for n in model['nodes']};elements={e['id']:e for e in model['elements']}
    actual={}
    for case in model['load_cases']:
        fz=0
        for load in case['loads']:
            if load['type']=='nodal':fz+=load.get('fz',0)
            else:
                e=elements[load['element']];a,b=[nodes[n] for n in e['nodes']]
                length=math.dist([a[k] for k in 'xyz'],[b[k] for k in 'xyz'])
                fz+=load.get('wz',0)*(load.get('end',length)-load.get('start',0))
        actual[case['id']]=fz
    check(set(actual)==set(SOURCE_FZ[num]),'Source case set changed')
    for k,v in actual.items():check(math.isclose(v,SOURCE_FZ[num][k],abs_tol=1e-9,rel_tol=1e-12),'Source vertical resultant mismatch')
    applied_my=sum(l.get('my',0) for c in model['load_cases'] for l in c['loads'])
    check(applied_my==SOURCE_MOMENT_Y.get(num,0),'Source applied moment mismatch')
    for attachment in contract['attachments']:
        file=path/attachment
        if file.suffix=='.png':
            with Image.open(file) as im:
                check(im.format=='PNG' and im.width>=2000 and im.height>=1400,'Undersized/non-PNG image')
                check(not im.info,'Unexpected PNG metadata')
            check(file.with_suffix('.svg').name in contract['attachments'],'PNG missing exact SVG partner')
        if file.suffix=='.svg':
            tree=ET.parse(file)
            check_text_anchors(tree,f'{cid}/{attachment}')
            for e in tree.iter():
                check('display:none' not in e.attrib.get('style','') and e.attrib.get('opacity')!='0','Hidden SVG text')
                if e.tag.endswith('text'):
                    check(0<=float(e.attrib['y'])<float(tree.getroot().attrib['height']),'Clipped SVG text baseline')
        if contract['locale']=='en':check(not re.search(r'[\u4e00-\u9fff]',texts(file)),'Non-English public attachment')
    if contract['locale']=='en':check(not re.search(r'[\u4e00-\u9fff]',(path/'prompt.txt').read_text()),'Non-English prompt')
    if num in [42,49]:
        visible=[]
        for view in ['xy','xz','yz']:
            name=f'view-{view}.svg'
            check(name in contract['attachments'],f'Missing source orthographic view {view}')
            check_projection_labels(path/name)
            visible.append(texts(path/name))
        combined='\n'.join(visible)
        for identity in list(nodes)+list(elements):
            check(re.search(r'(?<![\w])'+re.escape(identity)+r'(?![\w])',combined),
                  f'Separated views omit node/member label {identity}')
        if num==49:
            side=visible[2]
            for i,magnitude in [(1,5),(2,5),(3,7),(4,7)]:
                check(re.search(r'roof'+str(i)+r'[^\n]*wz=-'+str(magnitude)+r'(?![\d])',side),
                      f'YZ view loses explicit roof{i} load identity/value')
    if (path/'input.dxf').exists():
        entities=dxf_entities(path/'input.dxf')
        physical=[e for e in entities if e['type']=='LINE' and e.get('8')=='STRUCTURE']
        check(len(physical)==len(elements),'DXF structural entity count differs')
        recovered={tuple(round(float(e[k]),10) for k in ['10','20','11','21']) for e in physical}
        expected={tuple(round(float(v),10) for v in [nodes[e['nodes'][0]]['x'],nodes[e['nodes'][0]]['z'],nodes[e['nodes'][1]]['x'],nodes[e['nodes'][1]]['z']]) for e in elements.values()}
        check(recovered==expected,'DXF centreline geometry differs from authored physical model')
        if num in [43,47]:
            check(any(e.get('8')=='A_WALL' for e in entities),'Architectural wall context missing')
            check(any(e.get('8')=='A_EQUIPMENT' for e in entities),'Architectural equipment context missing')
        check(not any(a.endswith('.png') for a in contract['attachments']),'DXF category bypassed with image alternative')
    if num in [7,21,32]:
        t1,t2=contract['turns'];check(t1['state'] is None and t1['expectation']=='clarify','Missing-data analysis exposed')
        initial='\n'.join(texts(path/f) for f in t1['attachments'])+t1['instruction']
        later='\n'.join(texts(path/f) for f in t2['attachments'])+t2['instruction']
        if num==7:
            check('fz=-15' not in initial and '-15 kN' not in initial,'MM007 force leaked')
            check('fz=?' in initial and 'fz=-15' in later,'MM007 blur/resolution missing')
        if num==21:
            check('b3: n2 -> n3 / M1 / B2' in texts(path/'input-initial.svg'),'MM021 image conflict missing')
            check('b3: M1 / B1' in texts(path/'properties.txt'),'MM021 table conflict missing')
            check('fz=-22' in initial,'MM021 known point load incorrectly withheld')
            check('b3: M1 / B2' in later,'MM021 assignment resolution missing')
        if num==32:
            check(not any(s in initial for s in ['1.25','2.5','5/3','5/6']),'MM032 roof height leaked')
            check(all(s in later for s in ['1.25','2.5','5/3','5/6']),'MM032 incomplete roof supplement')
    return len(contract['attachments'])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,default=1);ap.add_argument('--end',type=int,default=50);args=ap.parse_args()
    total=0
    for i in range(args.start,args.end+1):
        p=CASES/f'MM-{i:03d}';total+=audit(p);print('PASS',p.name)
    print(f'Public/source checks passed: {args.end-args.start+1} cases, {total} attachments. Input blind review still pending.')

if __name__=='__main__':main()
