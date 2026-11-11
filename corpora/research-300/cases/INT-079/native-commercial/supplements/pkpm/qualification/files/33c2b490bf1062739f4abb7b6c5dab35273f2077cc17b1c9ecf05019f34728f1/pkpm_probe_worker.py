"""Owned, non-benchmark PKPM 2027 characterization specimen."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
BASE = Path(r'C:\PKPM2027R1.0.1')
handles = [os.add_dll_directory(str(BASE / sub)) for sub in
           ['Ribbon/PythonEnv', 'Ribbon', 'Ribbon/PM', 'Ribbon/P-TRANS/x64',
            'Ribbon/SAT', 'Ribbon/PMSAP64', 'CFG/X64']]
import APIPyInterface as api

mode, identity = sys.argv[1:3]
assert identity.startswith('c30-') and '/' not in identity and '\\' not in identity
project = ROOT / identity

if mode == 'build':
    height = float(sys.argv[3])
    project.mkdir(exist_ok=False)
    model = api.Model()
    model.CreatNewModel(str(project), 'case1')
    assert model.OpenPMModel(str(project / 'case1.JWS'))
    floor_id = model.AddStandFloor()
    model.SetCurrentStandFloor(floor_id)
    floor = model.GetCurrentStandFloor()
    shape = api.SectionShape()
    shape.Set_M(6)
    shape.Set_B(300)
    shape.Set_H(600)
    section = api.ColumnSection()
    section.SetUserSect(api.SectionKind.IDSec_Rectangle, shape)
    section_id = model.AddColumnSection(section)
    # Native point-load order is PZ, MX, MY, PX, PY, MZ.
    specimens = [((0, 0), [0, 0, 0, 11, 0, 0]),
                 ((4000, 0), [0, 0, 0, 0, 17, 0]),
                 ((0, 4000), [23, 0, 0, 0, 0, 0]),
                 ((4000, 4000), [0, 0, 0, 0, 0, 13])]
    mapping = []
    for xy, load in specimens:
        node = floor.AddNode(*xy)
        column = floor.AddColumn(section_id, node.GetID())
        column.SetConcreteGrade(30)
        column.SetSeisGrade(5)
        definition = api.LoadDefineData()
        definition.Set(-1, load)
        load_id = model.AddLoadDefine(definition)
        node.SetLoad([1], [load_id])
        mapping.append({'xyMm': xy, 'nodeId': node.GetID(), 'columnId': column.GetID(),
                        'nativeLoad': load, 'loadReadback': node.GetLoad(),
                        'loadDefinitionReadback': model.GetLoadDefine(load_id).Get()})
    floor.SetInfoValue(0, 0)
    floor.SetDeadLive(0, 0)
    for slab in floor.GetSlabs():
        floor.DeleteSlab(slab.GetID())
    model.SaveOneStandFloor(floor_id)
    real = api.RealFloor()
    real.SetFloorHeight(height * 1000)
    real.SetBottomElevation(0)
    real.SetStandFloorIndex(floor_id)
    model.AddNaturalFloor(real)
    for key, value in {0: 0, 1: 0, 4: 0, 10: 0, 12: 0, 27: 5, 29: 5}.items():
        model.SetOneDesignParaValue(key, value)
    para = model.GetProjectPara()
    ints = {101: 0, 103: 0, 106: 0, 601: 1, 603: 0, 604: 0,
            606: 0, 607: 0, 608: 0, 609: 0, 624: 1, 626: 0, 630: 0,
            641: 0, 701: 5, 703: 5, 100000: 0}
    doubles = {501: 1., 502: 1., 610: 1., 611: 1., 612: 1., 801: 0., 803: 0.}
    for key, value in ints.items():
        para.SetParaInt(key, value)
    for key, value in doubles.items():
        para.SetParaDouble(key, value)
    model.SaveProjectPara()
    model.SavePMModel()
    assert model.OpenPMModel(str(project / 'case1.JWS'))
    para = model.GetProjectPara()
    receipt = {'heightM': height, 'E_MPa': 30000, 'nu': .2,
               'Bmm': 300, 'Hmm': 600, 'mapping': mapping,
               'parametersInt': {str(k): para.GetPara_Int(k) for k in ints},
               'parametersDouble': {str(k): para.GetPara_Double(k) for k in doubles}}
    (project / 'input-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
    (project / 'WORK.FNM').write_bytes(b'case1\0'.ljust(256, b' ') + b'\r\n           1           5\r\n')
    print(json.dumps(receipt))
elif mode == 'extract':
    result = api.ResultData()
    status = result.InitialResult(str(project / 'case1.JWS'))
    nodes = []
    for node in result.GetPyNodeInResult():
        nodes.append({'pmId': node.GetPmID(), 'floor': node.GetFloorNo(),
                      'coordinates': [node.GetCoordinateX(), node.GetCoordinateY(), node.GetCoordinateZ()],
                      'cases': {name: [d.GetDispX(), d.GetDispY(), d.GetDispZ()]
                                for name, d in node.GetNodeDisp().items()}})
    receipt = json.loads((project / 'input-receipt.json').read_text())
    columns = []
    for row in receipt['mapping']:
        for column in result.GetDesignColumnsViaPmid(row['columnId']):
            columns.append({'pmId': row['columnId'], 'floor': column.GetFloorNo(),
                            'forces': column.GetForce()})
    out = {'initialResultStatus': status, 'caseNames': result.GetAllLoadCaseName(),
           'nodes': nodes, 'columns': columns}
    (project / 'sdk-results.json').write_text(json.dumps(out, indent=2), encoding='utf8')
    print(json.dumps(out))
elif mode == 'properties':
    model = api.Model()
    assert model.OpenPMModel(str(project / 'case1.JWS'))
    model.SetCurrentStandFloor(1)
    floor = model.GetCurrentStandFloor()
    columns = floor.GetColumns()
    output = {'materialDataDoc': api.MaterialData.__doc__, 'materialMethods': dir(api.MaterialData()), 'columns': []}
    mat=api.MaterialData()
    output['getEcResult']=repr(mat.getEc())
    for column in columns:
        section=model.GetColumnSection(column.GetSect())
        props=api.Bardata().GetSectProperty_column(section,mat)
        output['columns'].append({'id':column.GetID(),'grade':column.GetConcreteGrade(),'segment':column.GetSeg(),
          'sectionType':str(section.GetUserSect()[0]),'shapeB':section.GetUserSect()[1].Get_B(),'shapeH':section.GetUserSect()[1].Get_H(),
          'properties':{name:getattr(props,name)() for name in dir(props) if name.startswith('Get')}})
    (project/'sdk-properties.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(output,ensure_ascii=False))
else:
    raise ValueError(mode)
