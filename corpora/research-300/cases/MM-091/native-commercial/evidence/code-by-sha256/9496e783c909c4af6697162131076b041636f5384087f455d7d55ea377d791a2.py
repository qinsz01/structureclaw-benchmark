import os,json,traceback,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA_ROOT=ROOT

def save(name,value): (ROOT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def apply_controls():
    try:
        from YJKAPI import YJKSPrePy_JSCS
        p=YJKSPrePy_JSCS()
        ints={101:10101,103:10303,603:60301,604:60401,608:0,697:0,679:67901,654:0,601:60102,630:0,696:0,2308:0,624:1,606:0,609:0,650:0}
        floats={k:1. for k in (610,611,631,658,663,694,2305,2306,2307)};floats.update({801:0.,803:0.})
        model=json.loads((ROOT/'input.json').read_text(encoding='utf-8'))
        if all(m['type']=='concrete' for m in model['materials']):ints[103]=10301
        before={'int':{str(k):p.GetSParaInt(k) for k in ints},'float':{str(k):p.GetSParaFlt(k) for k in floats}}
        for k,v in ints.items():p.SetSParInt(k,v)
        for k,v in floats.items():p.SetSParFloat(k,v)
        p.SParaSave()
        after={'int':{str(k):p.GetSParaInt(k) for k in ints},'float':{str(k):p.GetSParaFlt(k) for k in floats}}
        save('controls.json',{'pid':os.getpid(),'before':before,'requested':{'int':ints,'float':floats},'after':after})
    except BaseException:
        (ROOT/'controls-error.txt').write_text(traceback.format_exc(),encoding='utf-8');return

def safe(value):
    if value is None or isinstance(value,(str,bool,int,float)): return value
    try:return [safe(v) for v in value]
    except TypeError:return str(value)

def extract():
    try:
        from YJKAPI import YJKSDsnDataPy,YJKSPrePy
        d=YJKSDsnDataPy;init=d.dsnInitData();pre=YJKSPrePy()
        save('native-signatures.json',{cls.__name__:{n:getattr(cls,n).__doc__ for n in names} for cls,names in ((YJKSPrePy,['BeamJD','ColumnJD','BeamONO','ColumnONO','BeamIDInFlr','ColumnIDInFlr','BeamMat','ColumnMat','XYZ']),(YJKSDsnDataPy,['dsnGetLDCaseBySort','dsnGetNodeDis','dsnGetNodeReaction','dsnGetReaction','dsnGetComStdNL','dsnReadFloorPJ','dsnGetComAng']))})
        cases=safe(d.dsnGetLDCaseBySort(1));save('case-map.json',{'init':init,'cases':cases})
        text=(DATA_ROOT/'fea.dat').read_text(encoding='gb18030',errors='strict');section='';node_ids=[];frames=[]
        for line in text.splitlines():
            if line.startswith('*'):section=line.split()[0].upper()
            elif section=='*NODE' and re.match(r'^\s*\d+\s',line):node_ids.append(int(line.split()[0]))
            elif section=='*FRAME' and re.match(r'^\s*\d+\s',line):
                tag=int(line.split()[0]);kind=re.search(r'\bT=(\w+)',line)[1];frames.append({'id':tag,'kind':kind,'post_kind':{'COLUMN':3,'BEAM':1,'BRACE':5}[kind]})
        # Continuation text gives the floor; actual model SDK reports it independently.
        pre_info={}
        for frame in frames:
            tag=frame['id'];prefix={'COLUMN':'Column','BEAM':'Beam','BRACE':'Brace'}[frame['kind']]
            frame['floor']=int(getattr(pre,prefix+'Flr')(tag))
            info={'nodes':safe(getattr(pre,prefix+'JD')(tag)),'floor':frame['floor'],'original_number':safe(getattr(pre,prefix+'ONO')(tag)),'floor_sequence':safe(getattr(pre,prefix+'IDInFlr')(tag)),'material':safe(getattr(pre,prefix+'Mat')(tag))}
            if frame['kind']=='BRACE':
                info['brace_kind']=safe(d.dsnGetBraceKind(frame['floor'],tag));info['brace_column_kind']=safe(d.dsnGetBraceColKind(frame['floor'],tag));info['is_truss']=safe(pre.IsBraceTruss(tag))
            info['angle_radians']=safe(d.dsnGetComAng(frame['floor'],frame['post_kind'],tag));pre_info[str(tag)]=info
        result={'pid':os.getpid(),'nodes':node_ids,'coordinates':{str(n):safe(pre.XYZ(n)) for n in node_ids},'frames':frames,'preprocessor':pre_info,'cases':[],'invalid_node_arrays':[]}
        for cid in cases[1]:
            case={'id':cid,'name':str(d.dsnGetLDCaseName(cid)),'analysis_case':safe(d.dsnGetAnaLDCaseByLDCase(cid)),'nodes':{},'memberForces':{}}
            for nid in node_ids:
                values={'displacement':safe(d.dsnGetNodeDis(nid,cid)),'nodeReaction':safe(d.dsnGetNodeReaction(nid,cid)),'supportReaction':safe(d.dsnGetReaction(nid,cid))}
                for field,v in values.items():
                    if not isinstance(v,list) or len(v)!=6 or any(type(t) not in (float,int) for t in v):result['invalid_node_arrays'].append({'node':nid,'case':cid,'field':field,'raw':v})
                case['nodes'][str(nid)]=values
            for floor in sorted(set(f['floor'] for f in frames)):
                if not d.dsnReadFloorPJ(floor):raise RuntimeError('native floor result read false')
                for f in [f for f in frames if f['floor']==floor]:
                    raw=safe(d.dsnGetComStdNL(floor,f['post_kind'],f['id'],cid,1))
                    if not isinstance(raw,list) or len(raw)!=2 or type(raw[0])!=int or raw[0]<=0 or raw[0]>len(raw[1]):raise RuntimeError('invalid native member force count')
                    valid=raw[1][:raw[0]]
                    if any(len(v)!=6 or any(type(t) not in (float,int) for t in v) for v in valid):raise RuntimeError('invalid native member force array')
                    case['memberForces'][str(f['id'])]={'section_count':raw[0],'allocated_rows':len(raw[1]),'forces':valid}
            result['cases'].append(case)
        save('results.json',result)
    except BaseException:
        (ROOT/'extract-error.txt').write_text(traceback.format_exc(),encoding='utf-8');return
