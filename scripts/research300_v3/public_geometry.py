"""Reconstruct construction documents using public bytes only.

Raster decoding is font-template transcription, not a human/LLM blind review.
No expected coordinates or authoring models are passed to these readers.
"""
import csv
import json
import math
import string
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

FONT='/usr/share/fonts/truetype/dejavu/'
DOFS=['ux','uy','uz','rx','ry','rz']
def read(p):return json.loads(p.read_text())
def rows(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))

@lru_cache(None)
def glyphs(i):
    font=ImageFont.truetype(FONT+'DejaVuSansMono.ttf',28);advance=font.getlength('0');chars=' 0123456789+-.eXYZm()';x0=math.floor(i*advance);x1=math.floor((i+1)*advance);templates=[]
    for c in chars:
        p=Image.new('RGB',(800,38),'white');ImageDraw.Draw(p).text((0,0),' '*i+c,font=font,fill='#0f172a');templates.append(np.asarray(p.crop((x0,0,x1,38)).convert('L'),dtype=np.int16))
    return x0,x1,chars,np.stack(templates)

def dimension_text(im,y):
    out=''
    for i in range(39):
        x0,x1,chars,templates=glyphs(i)
        actual=np.asarray(im.crop((90+x0,y,90+x1,y+38)).convert('L'),dtype=np.int16)
        errors=np.abs(templates-actual).sum(axis=(1,2));best=int(errors.argmin());error,c=errors[best],chars[best];out+=c
        if error>1200:raise ValueError('Unreadable dimension glyph at '+str((i,error,out)))
    return out.strip()

def raster_geometry(folder,joint_ids):
    dimensions={}
    for path in sorted(folder.glob('dimensions-*.png')):
        im=Image.open(path)
        for j in range(30):
            # A blank row ends the issued key; title/header never supply values.
            crop=np.asarray(im.crop((90,195+j*43,500,233+j*43)).convert('L'))
            if crop.min()>240:break
            line=dimension_text(im,195+j*43);parts=line.split();assert len(parts)==4,line
            code,value,unit,axis=parts;assert code[0] in 'XYZ' and unit=='m' and axis=='('+code[0]+')',line
            assert code not in dimensions;dimensions[code]=float(value)
    assert dimensions
    nodes={};font=ImageFont.truetype(FONT+'DejaVuSans.ttf',22);templates={}
    for nid in joint_ids:
        im=Image.new('RGB',(105,35),'white');ImageDraw.Draw(im).text((0,0),nid,font=font,fill='#075985');templates[nid]=np.all(np.asarray(im)==[7,89,133],axis=2)
    for sheet in rows(folder/'drawing-index.csv'):
        im=Image.open(folder/sheet['sheet']).convert('RGB');pixels=np.asarray(im)
        xs=sheet['column_axes'].split(' > ');ys=sheet['row_axes'].split(' > ')
        for i,x in enumerate(xs):
            px=180+i*2020/max(len(xs)-1,1)
            for j,y in enumerate(ys):
                py=1380-j*1120/max(len(ys)-1,1)
                if not np.array_equal(pixels[round(py),round(px)],[7,89,133]):continue
                # Re-render candidate public marks at the exact issued pixel
                # origin; noninteger drawing positions affect glyph hinting.
                actual=np.all(np.asarray(im.crop((int(px+8),int(py-34),int(px+8)+105,int(py-34)+35)))==[7,89,133],axis=2)
                scored=[]
                for nid in joint_ids:
                    trial=Image.new('RGB',(105,35),'white');ImageDraw.Draw(trial).text((px+8-int(px+8),py-34-int(py-34)),nid,font=font,fill='#075985')
                    candidate=np.all(np.asarray(trial)==[7,89,133],axis=2);scored.append((np.count_nonzero(actual!=candidate),nid))
                scored.sort();error,nid=scored[0]
                # Hinting at fractional origins changes up to three core-ink
                # pixels. Require a uniquely separated glyph match, with no
                # reference coordinates/labels used as a fallback.
                assert error<=3 and (len(scored)==1 or scored[1][0]-error>=10),(sheet['sheet'],x,y,error,nid)
                coords={sheet['horizontal_axis']:dimensions[x],sheet['vertical_axis']:dimensions[y],sheet['fixed_axis'][0].lower():dimensions[sheet['fixed_axis']]}
                assert set(coords)==set('xyz')
                if nid in nodes:assert all(abs(nodes[nid][k]-coords[k])<1e-9 for k in 'xyz')
                nodes[nid]={'id':nid,**coords}
    assert set(nodes)==set(joint_ids),{'missing':sorted(set(joint_ids)-set(nodes))}
    return list(nodes.values())

def reconstruct(folder):
    folder=Path(folder);details=read(folder/'connection-details.json');seatings=rows(folder/'joint-details.csv')
    if (folder/'joint-locations.csv').is_file():
        dimensions={r['axis']:float(r['coordinate_m']) for r in rows(folder/'grid-dimensions.csv')}
        nodes=[{'id':r['joint_mark'],**{k:dimensions[r[col]] for k,col in zip('xyz',['X_axis','Y_axis','Z_level'])}} for r in rows(folder/'joint-locations.csv')]
    else:nodes=raster_geometry(folder,[r['joint_mark'] for r in seatings])
    support={r['joint_mark']:details['restrainedGlobalDofs'][r['detail']] for r in seatings}
    for n in nodes:n['restraints']=[d in support[n['id']] for d in DOFS]
    elements=[]
    for r in rows(folder/'construction-runs.csv'):
        path=r['joint_path'].split(' > ');marks=r['ordered_segment_marks'].split(' > ');directions=r['segment_directions'].split(' > ')
        assert len(path)==len(marks)+1 and len(marks)==len(directions)
        for mid,a,b,direction in zip(marks,path,path[1:],directions):
            assert direction in ['forward','reverse'];elements.append({'id':mid,'nodes':[a,b] if direction=='forward' else [b,a],'type':r['member_type'],'material':r['material_family'],'section':r['section_family'],'rotation_angle':float(r['rotation_deg'])})
    convention=read(folder/'model-conventions.json');model={k:convention[k] for k in ['schema_version','unit_system','coordinate_system','analysis_control','stories']}
    model.update(nodes=nodes,elements=elements,materials=read(folder/'materials.json'),sections=read(folder/'section-families.json'),load_cases=[],load_combinations=[])
    if (folder/'section-reference-planes.json').is_file():model['metadata']={'elementReferenceVectors':read(folder/'section-reference-planes.json')}
    return model


@lru_cache(None)
def table_glyphs(size,i,alphabet,background):
    f=ImageFont.truetype(FONT+'DejaVuSansMono.ttf',size);advance=f.getlength('0');x0=math.floor(i*advance);x1=math.floor((i+1)*advance);templates=[]
    for c in alphabet:
        p=Image.new('RGB',(2400,40),background);ImageDraw.Draw(p).text((0,0),' '*i+c,font=f,fill='#0f172a');templates.append(np.asarray(p.crop((x0,0,x1,40)).convert('L'),dtype=np.int16))
    return x0,x1,np.stack(templates)

def table_line(im,y,size,count,background,restricted=False):
    out=''
    for i in range(count):
        alphabet=string.ascii_letters+string.digits+' _-+./:;,{}[]"()'
        if restricted and 16<=i<59:alphabet=' 0123456789+-.eE'
        if restricted and 61<=i<67:alphabet=' 01'
        x0,x1,templates=table_glyphs(size,i,alphabet,background)
        actual=np.asarray(im.crop((55+x0,y,55+x1,y+40)).convert('L'),dtype=np.int16)
        errors=np.abs(templates-actual).sum(axis=(1,2));best=int(errors.argmin());out+=alphabet[best]
        assert errors[best]<1600,('Unrecognised raster table glyph',i,errors[best],out)
    return out.rstrip()

def legacy_raster_transcription(public):
    """Read the frozen low-level table carrier, without authoring-model input."""
    public=Path(public);nodes=[];hashes={}
    import hashlib
    for path in sorted(public.glob('geometry-nodes-*.png')):
        im=Image.open(path)
        for i in range(20):
            y=280+i*55;bg='#f8fafc' if i%2==0 else 'white'
            # Background stripes exist only for actual issued rows.
            crop=np.asarray(im.crop((55,y+5,300,y+35)).convert('RGB'))
            if not np.any(np.all(crop==[15,23,42],axis=2)):break
            line=table_line(im,y,28,95,bg,True);parts=line.split();assert len(parts)==6,line
            nid,x,yv,z,bits,story=parts;assert len(bits)==6 and set(bits)<={'0','1'}
            n={'id':nid,'x':float(x),'y':float(yv),'z':float(z),'restraints':[c=='1' for c in bits]}
            if story!='-':n['story']=story
            nodes.append(n)
        hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    stories=[];buffer=''
    for path in sorted(public.glob('geometry-stories-*.png')):
        im=Image.open(path)
        for i in range(26):
            y=180+i*37;crop=np.asarray(im.crop((55,y,2350,y+32)).convert('RGB'))
            if not np.any(np.all(crop==[15,23,42],axis=2)):
                if buffer:stories.append(json.loads(buffer));buffer=''
                continue
            # Adjacent text baselines are 37 px apart; a 32 px crop excludes
            # the next line while retaining every fontsize-24 glyph.
            line=table_line(im,y,24,132,'white');buffer+=line
            try:value=json.loads(buffer)
            except json.JSONDecodeError:continue
            stories.append(value);buffer=''
        hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    assert not buffer and nodes
    return {'reviewMode':'pixel-template-transcription','nodes':nodes,'stories':stories,'imageHashes':hashes}
