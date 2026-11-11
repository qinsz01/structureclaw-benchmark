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
        save('native-signatures.json',{cls.__name__:{n:getattr(cls,n).__doc__ for n in names} for cls,names in ((YJKSPrePy,['FlrColumns','NColumn','ColumnJD','ColumnONO','ColumnIDInFlr','XYZ','NJD']),(YJKSDsnDataPy,['dsnGetLDCaseBySort','dsnGetNodeDis','dsnGetNodeReaction','dsnGetReaction','dsnGetComStdNL','dsnReadFloorPJ']))})
        cases=safe(d.dsnGetLDCaseBySort(1));save('case-map.json',{'init':init,'cases':cases})
        node_ids=set();fea=list(DATA_ROOT.rglob('fea.dat'))
        for file in fea:
            section=''
            for line in file.read_text(encoding='gb18030',errors='replace').splitlines():
                if line.startswith('*'):section=line.split()[0].upper()
                elif section=='*NODE' and re.match(r'^\s*\d+\s',line): node_ids.add(int(line.split()[0]))
        nnode=int(pre.NJD())
        columns=safe(pre.FlrColumns(1,int(pre.NColumn(1))))
        if len(columns)==2 and isinstance(columns[1],list): columns=columns[1]
        for c in columns: node_ids.update(map(int,safe(pre.ColumnJD(c))))
        if not node_ids: raise RuntimeError('No actual native node tags')
        d.dsnReadFloorPJ(1)
        result={'pid':os.getpid(),'cases':[],'nodes':sorted(node_ids),'fea':[str(p) for p in fea],
                'nnode':nnode,'columnIds':columns,'coordinates':{str(n):safe(pre.XYZ(n)) for n in node_ids},
                'columns':{str(c):{'nodes':safe(pre.ColumnJD(c)),'originalNumber':safe(pre.ColumnONO(c)),'floorSequence':safe(pre.ColumnIDInFlr(c))} for c in columns}}

        for cid in cases[1]:
            case={'id':cid,'name':str(d.dsnGetLDCaseName(cid)),'analysis_case':safe(d.dsnGetAnaLDCaseByLDCase(cid)),'nodes':{}}
            for nid in sorted(node_ids):
                case['nodes'][str(nid)]={'displacement':safe(d.dsnGetNodeDis(nid,cid)),'nodeReaction':safe(d.dsnGetNodeReaction(nid,cid)),'supportReaction':safe(d.dsnGetReaction(nid,cid))}
            case['columnForces']={str(c):safe(d.dsnGetComStdNL(1,3,int(c),cid,1)) for c in columns}
            result['cases'].append(case)
        save('results.json',result)
    except BaseException:
        (ROOT/'extract-error.txt').write_text(traceback.format_exc(),encoding='utf-8');return

def signatures():
    try:
        from YJKAPI import YJKSPrePy,YJKSDsnDataPy
        save('native-signatures.json',{cls.__name__:{n:getattr(cls,n).__doc__ for n in names} for cls,names in ((YJKSPrePy,['FlrColumns','NColumn','ColumnJD','ColumnONO','ColumnIDInFlr','XYZ','NJD']),(YJKSDsnDataPy,['dsnGetLDCaseBySort','dsnGetLDCaseName','dsnGetAnaLDCaseByLDCase','dsnGetNodeDis','dsnGetNodeReaction','dsnGetReaction','dsnGetComStdNL','dsnReadFloorPJ']))})
    except BaseException:
        (ROOT/'signatures-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
