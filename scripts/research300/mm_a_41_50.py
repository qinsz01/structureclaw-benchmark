"""Source-faithful authoring descriptors for research-300 MM-041..MM-050.

The material/section numbers complete appendices left unspecified by the plan.
No numerical responses are embedded, and this module does not certify an engine.
Only the primitive constructors in representative-models.py are reused.
"""

import importlib.util
import math
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "research300_mm_a_41_50_primitives",
    Path(__file__).resolve().parents[1] / "representative-models.py",
)
_P = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_P)

_FIXED = [True] * 6
_PIN_XZ = [True, True, True, True, False, True]
_TRUSS_FREE = [False, False, False, True, True, True]
_TRUSS_FIXED = [True] * 6


def _model(spatial=False, truss=False):
    m = _P.model("3d" if spatial else "2d")
    if truss:
        m["sections"] = [
            _P.section("A1", .1, .1),
            _P.section("A2", .08, .08),
            _P.section("A3", .07, .07),
        ]
    return m


def _node(m, name, x, z, y=0, restraint=None):
    return _P.node(m, name, x, z, y, restraint)


def _member(m, name, start, end, section="B1", kind="beam"):
    return _P.elem(m, name, start, end, kind, section)


def _length(m, eid):
    e = next(e for e in m["elements"] if e["id"] == eid)
    ns = {n["id"]: n for n in m["nodes"]}
    a, b = [ns[n] for n in e["nodes"]]
    return math.sqrt(sum((b[k] - a[k]) ** 2 for k in ("x", "y", "z")))


def _udl(m, eid, magnitude):
    # Global vertical load per ACTUAL member length, including sloping members.
    _P.load(m, type="distributed", element=eid, start=0.0,
            end=_length(m, eid), wx=0.0, wy=0.0, wz=-magnitude)


def _q(node_or_member, component, *, member=False, position=0.0, side="right"):
    location = dict(kind="member" if member else "node", id=node_or_member)
    if member:
        location.update(positionM=position, side=side)
    unit = "m" if component.startswith("u") else (
        "rad" if component.startswith("r") else (
            "kN.m" if component.startswith("M") or component == "T" else "kN"))
    station = f":{position:g}:{side}" if member else ""
    return dict(
        id=f"D:{'member' if member else 'node'}:{node_or_member}:{component}{station}",
        selection=dict(kind="case", id="D"), location=location,
        component=component, unit=unit,
        tolerance=dict(absolute=1e-8, relative=1e-6),
    )


def _output(description, *quantities):
    return dict(description=description, quantities=list(quantities),
                derived=[], kind="numerical")


def _base_moments(english, label, node, member):
    description = (
        f"{label}: global support reaction My and column-section M2 just above the base"
        if english else f"{label}：全局支座反力矩My及紧邻柱底上方截面内力矩M2"
    )
    return _output(description, _q(node, "My"), _q(member, "M2", member=True))


def _descriptor(m, outputs, *, english=False, truss=False, notes=(), drawing=()):
    # Publish only properties that are actually assigned in this case.
    used = {e["section"] for e in m["elements"]}
    m["sections"] = [s for s in m["sections"] if s["id"] in used]
    if english:
        common = [
            "Appendix completion: M1 is linear elastic steel, E=206000 MPa, "
            "nu=0.30, G=79230.76923076923 MPa, rho=7850 kg/m3. "
            "These values were unspecified by the source plan and are explicit case inputs.",
            "Use first-order Euler-Bernoulli frame theory or axial-only truss theory as assigned. "
            "Self-weight, P-Delta, rigid floors, rigid offsets and staged construction are OFF. "
            "All stated loads act together in basic case D; there are no load combinations.",
        ]
        common.append(
            "Pure trusses carry only axial force. Inactive nodal rotations are restrained; "
            "this adds no translational restraint or beam bending stiffness."
            if truss else
            "All frame joints are rigid. The planar model retains ux, uz and ry; "
            "uy, rx and rz are inactive. Local axis 1 follows member i to j, "
            "axis 2 is global +Y, and axis 3 is axis 1 cross axis 2. "
            "Member M2 is a section force and support My is a global reaction."
        )
    else:
        common = [
            "附录补全：M1为线弹性钢材，E=206000 MPa，nu=0.30，"
            "G=79230.76923076923 MPa，rho=7850 kg/m3。"
            "原规划未给数值，此处明确编定为本题输入。",
            "采用一阶Euler-Bernoulli梁柱或指定的纯轴力桁架理论。"
            "自重、P-Delta、刚性楼板、刚臂和施工阶段均关闭。"
            "全部题定荷载共同组成基本工况D，无荷载组合。",
        ]
        common.append(
            "纯桁架杆仅承受轴力；约束节点非作用转动自由度，"
            "不增加平移约束，不引入梁弯曲刚度。"
            if truss else
            "全部梁柱节点为刚接。平面模型保留ux、uz、ry，"
            "约束非作用自由度uy、rx、rz。局部1轴沿杆件i端至j端，"
            "局部2轴为全局+Y，局部3轴为1轴叉乘2轴。"
            "构件M2为截面内力矩，支座My为全局反力矩。"
        )
    for s in m["sections"]:
        b, h = s["shape"]["B"], s["shape"]["H"]
        if english:
            common.append(
                f"Appendix completion: {s['id']} is a solid rectangular section, "
                f"B={b:g} mm and H={h:g} mm; its explicit A/Iy/Iz/J values "
                "are supplied in the property table. The source specified only the section code."
            )
        else:
            common.append(
                f"附录补全：{s['id']}为实心矩形截面，B={b:g} mm、H={h:g} mm；"
                "完整A/Iy/Iz/J数值见属性表，原规划仅给截面代号。"
            )
    return dict(model=m, outputs=outputs, notes=common + list(notes),
                drawingNotes=list(drawing))


def _case041():
    m = _model(spatial=True, truss=True)
    for name, x, y in [("B1", 0, 0), ("B2", 6, 0),
                       ("B3", 6, 6), ("B4", 0, 6)]:
        _node(m, name, x, 0, y, _TRUSS_FIXED.copy())
    _node(m, "U", 4, 3, 2, _TRUSS_FREE.copy())
    _node(m, "L", 3, -2, 3, _TRUSS_FREE.copy())
    bases = ["B1", "B2", "B3", "B4"]
    for i, a in enumerate(bases):
        _member(m, f"ring{i+1}", a, bases[(i+1) % 4], "A1", "truss")
        _member(m, f"upper{i+1}", a, "U", "A1", "truss")
        _member(m, f"lower{i+1}", a, "L", "A1", "truss")
    _member(m, "apex_link", "L", "U", "A1", "truss")
    _P.load(m, type="nodal", node="U", fx=10.0, fy=0.0, fz=-30.0)
    _P.load(m, type="nodal", node="L", fx=0.0, fy=8.0, fz=-20.0)
    outputs = [
        _output("上顶点U的Ux、Uy、Uz", *[_q("U", c) for c in ("ux", "uy", "uz")]),
        _output("下顶点L的Ux、Uy、Uz", *[_q("L", c) for c in ("ux", "uy", "uz")]),
        _output("上下顶点连杆apex_link轴力N，拉力为正",
                _q("apex_link", "N", member=True)),
    ]
    return _descriptor(m, outputs, truss=True, drawing=[
        "B1—B4为底面四角；U为上顶点，L为下顶点。",
        "全部为纯轴力杆，交叉投影不自动相连；apex_link穿越底平面处不设节点。",
        "底面四角三向平移固定；顶点平移自由。",
    ])


def _case042():
    m = _model(spatial=True, truss=True)
    triangle = [(0.0, 0.0), (4.0, 0.0), (2.0, 2*math.sqrt(3))]
    for level in range(4):
        for vertex, (x, y) in enumerate(triangle, 1):
            _node(m, f"L{level}V{vertex}", x, 2.5*level, y,
                  (_TRUSS_FIXED if level == 0 else _TRUSS_FREE).copy())
        for vertex in range(1, 4):
            following = vertex % 3 + 1
            _member(m, f"ring_{level}_{vertex}", f"L{level}V{vertex}",
                    f"L{level}V{following}", "A2", "truss")
            if level:
                _member(m, f"vertical_{level}_{vertex}", f"L{level-1}V{vertex}",
                        f"L{level}V{vertex}", "A1", "truss")
                _member(m, f"diagonal_{level}_{vertex}", f"L{level-1}V{vertex}",
                        f"L{level}V{following}", "A3", "truss")
    for v in range(1, 4):
        _P.load(m, type="nodal", node=f"L3V{v}",
                fx=12.0 if v == 1 else 0.0,
                fy=8.0 if v == 2 else 0.0, fz=-10.0)
    outputs = [
        _output("Top-level vertex 1: Ux", _q("L3V1", "ux")),
        _output("Top-level vertex 2: Uy", _q("L3V2", "uy")),
        _output("Axial forces N in all three bottom-storey side diagonals; tension positive",
                *[_q(f"diagonal_1_{v}", "N", member=True) for v in range(1, 4)]),
    ]
    return _descriptor(m, outputs, english=True, truss=True, notes=[
        "Appendix completion: the plan leaves triangular orientation and the cyclic "
        "diagonal direction unspecified; the dimensioned views define them. "
        "All three bottom-storey side-diagonal axial forces are requested because "
        "the source does not identify an individual bottom-side diagonal.",
    ], drawing=[
        "Vertices V1, V2, V3 run counterclockwise in plan; V1-V2 points along +X.",
        "Four ring levels: L0, L1, L2, L3. Keep nodes at different levels distinct.",
        "Each side diagonal runs from lower Vi to upper V(i+1), with V4=V1.",
        "Verticals: A1; rings: A2; diagonals: A3. Every member is axial-only.",
    ])


def _case043():
    m = _model()
    for name, x, z, fix in [
        ("BL", 0, 0, _PIN_XZ), ("BR", 18, 0, _FIXED),
        ("EL", 0, 7, None), ("ER", 18, 7, None), ("R", 9, 9, None),
    ]:
        _node(m, name, x, z, restraint=None if fix is None else fix.copy())
    _member(m, "column_left", "BL", "EL", "C1", "column")
    _member(m, "column_right", "BR", "ER", "C1", "column")
    _member(m, "roof_left", "EL", "R")
    _member(m, "roof_right", "R", "ER")
    for eid in ("roof_left", "roof_right"):
        _udl(m, eid, 6.0)
    return _descriptor(m, [
        _output("屋脊R的Uz", _q("R", "uz")),
        _base_moments(False, "右柱脚", "BR", "column_right"),
    ], notes=["柱脚弯矩的输出约定补全：同时报告支座My和紧邻柱底截面的M2，分别注明符号定义。"], drawing=[
        "仅结构层实体为杆件；围护和设备层均不参与分析。",
        "左柱脚铰接，右柱脚固接；檐口与屋脊均刚接。",
        "两坡梁线载均沿全局-Z，按实际坡长计6 kN/m。",
    ])


def _case044():
    m = _model()
    for i, x in enumerate((0, 18, 36)):
        _node(m, f"B{i}", x, 0, restraint=_FIXED.copy())
        _node(m, f"E{i}", x, 9)
        _member(m, f"column{i}", f"B{i}", f"E{i}", "C1", "column")
    _node(m, "M", 9, 9)
    _node(m, "R", 27, 11)
    for eid, a, b, section in [
        ("flat_left", "E0", "M", "B1"),
        ("flat_right", "M", "E1", "B1"),
        ("slope_left", "E1", "R", "B2"),
        ("slope_right", "R", "E2", "B2"),
    ]:
        _member(m, eid, a, b, section)
        _udl(m, eid, 6.0)
    return _descriptor(m, [
        _output("Left-span connected midpoint M: Uz", _q("M", "uz")),
        _output("Right roof ridge R: Uz", _q("R", "uz")),
        _output("Middle column axial force N at its base; tension positive",
                _q("column1", "N", member=True)),
    ], english=True, drawing=[
        "The flat roof and pitched roof share rigid joint E1 at the middle column.",
        "M is a connected midpoint observation node, with no support or hinge.",
        "Flat roof: B1. Pitched roof: B2. Columns: C1. All bases fixed.",
        "All roof loads act along global -Z: 6 kN/m per actual member length.",
    ])


def _case045():
    m = _model()
    for name, x, z, fix in [
        ("BL", 0, 0, _PIN_XZ), ("BR", 21, 0, _FIXED),
        ("EL", 0, 6, None), ("ER", 21, 7.5, None),
        ("M", 10.5, 6.75, None),
    ]:
        _node(m, name, x, z, restraint=None if fix is None else fix.copy())
    _member(m, "column_left", "BL", "EL", "C1", "column")
    _member(m, "column_right", "BR", "ER", "C1", "column")
    for eid, a, b in [("roof_left", "EL", "M"), ("roof_right", "M", "ER")]:
        _member(m, eid, a, b)
        _udl(m, eid, 8.0)
    return _descriptor(m, [
        _output("屋面几何中点M的Uz", _q("M", "uz")),
        _base_moments(False, "右柱脚", "BR", "column_right"),
    ], notes=["柱脚弯矩的输出约定补全：同时报告支座My和紧邻柱底截面的M2，分别注明符号定义。"], drawing=[
        "左柱脚铰接，右柱脚固接；两檐口及梁中点均连续刚接。",
        "M为斜屋面几何中点，是连通观测节点，无支座或释放。",
        "坡梁线载沿全局-Z，按实际坡长计8 kN/m，不是杆件法向载荷。",
    ])


def _case046():
    m = _model()
    for i, x in enumerate((0, 18, 36)):
        _node(m, f"B{i}", x, 3 if i == 1 else 0, restraint=_FIXED.copy())
        _node(m, f"E{i}", x, 9)
        if i != 1:
            _member(m, f"column{i}", f"B{i}", f"E{i}", "C1", "column")
    _node(m, "P", 18, 6)
    _member(m, "column1_lower", "B1", "P", "C1", "column")
    _member(m, "column1_upper", "P", "E1", "C1", "column")
    for i in (0, 1):
        _member(m, f"roof{i}", f"E{i}", f"E{i+1}")
        _udl(m, f"roof{i}", 6.0)
    _P.load(m, type="nodal", node="P", fx=4.9, fy=0.0, fz=-49.0)
    return _descriptor(m, [
        _output("Middle-column load node P at z=6 m: Ux", _q("P", "ux")),
        _base_moments(True, "Middle-column base", "B1", "column1_lower"),
    ], english=True, notes=[
        "Output convention completion: report both support My and column-root section "
        "M2 for the requested column-base moment, with their distinct sign conventions.",
    ], drawing=[
        "The middle base B1, load node P and roof joint E1 are distinct connected nodes.",
        "All three actual column bases are fixed. Do not extend the middle column below B1.",
        "P: Fx=+4.9 kN and Fz=-49 kN. Both roof spans: global -Z 6 kN/m.",
    ])


def _case047():
    m = _model()
    for side, x in [("L", 0), ("R", 18)]:
        _node(m, f"B{side}", x, 0, restraint=_FIXED.copy())
        _node(m, f"J{side}", x, 3)
        _node(m, f"E{side}", x, 7)
        _member(m, f"column_{side}_lower", f"B{side}", f"J{side}", "C1", "column")
        _member(m, f"column_{side}_upper", f"J{side}", f"E{side}", "C1", "column")
    _node(m, "TL", 6, 3)
    _node(m, "TR", 12, 3)
    for eid, a, b, section, q in [
        ("roof", "EL", "ER", "B1", 6.0),
        ("mezzanine_left", "JL", "TL", "B2", 4.0),
        ("mezzanine_right", "JR", "TR", "B2", 8.0),
    ]:
        _member(m, eid, a, b, section)
        _udl(m, eid, q)
    return _descriptor(m, [
        _output("左夹层自由端TL的Uz", _q("TL", "uz")),
        _output("右夹层自由端TR的Uz", _q("TR", "uz")),
        _output("右夹层根部JR处M2，沿JR至TR方向取s=0+",
                _q("mezzanine_right", "M2", member=True)),
    ], drawing=[
        "仅结构层实体参与分析；围护和设备线不构成杆件或支座。",
        "TL与TR之间留空且不连接；左右夹层均为独立悬挑。",
        "右夹层杆件方向为JR至TR；根部弯矩取JR侧s=0+的M2。",
        "屋面6、左夹层4、右夹层8 kN/m，均沿全局-Z。",
    ])


def _case048():
    m = _model()
    for i, (x, z) in enumerate(((0, 6), (10, 8), (20, 6))):
        _node(m, f"B{i}", x, 0, restraint=_FIXED.copy())
        _node(m, f"E{i}", x, z)
        _member(m, f"column{i}", f"B{i}", f"E{i}",
                "C2" if i == 1 else "C1", "column")
    for i in (0, 1):
        _member(m, f"roof{i}", f"E{i}", f"E{i+1}")
        _udl(m, f"roof{i}", 6.0)
    return _descriptor(m, [
        _output("Supported roof ridge E1: Uz", _q("E1", "uz")),
        _output("Middle column axial force N at its base; tension positive",
                _q("column1", "N", member=True)),
        _output("Column-base reactions at B0, B1 and B2: global Fx, Fz and My",
                *[_q(f"B{i}", c) for i in range(3) for c in ("Fx", "Fz", "My")]),
    ], english=True, notes=[
        "Output-scope completion: the source does not identify a subset of column "
        "bases or reaction components, so report Fx, Fz and My at all three bases.",
    ], drawing=[
        "E1 is the shared rigid joint of the middle column and both roof slopes.",
        "Outer columns: C1; middle column: C2; roof slopes: B1. All bases fixed.",
        "Both slopes carry global -Z 6 kN/m, measured per actual slope length.",
    ])


def _case049():
    m = _model()
    _node(m, "BL", 0, 0, restraint=_FIXED.copy())
    _node(m, "BR", 24, 0, restraint=_FIXED.copy())
    roof = [("EL", 0, 6), ("PL", 6, 8), ("V", 14, 7),
            ("PR", 18, 9), ("ER", 24, 6)]
    for name, x, z in roof:
        _node(m, name, x, z)
    _member(m, "column_left", "BL", "EL", "C1", "column")
    _member(m, "column_right", "BR", "ER", "C1", "column")
    for i in range(4):
        _member(m, f"roof{i+1}", roof[i][0], roof[i+1][0])
        _udl(m, f"roof{i+1}", 5.0 if i < 2 else 7.0)
    return _descriptor(m, [
        _output("谷点V的Uz", _q("V", "uz")),
        _output("右峰PR的Ux、Uz", _q("PR", "ux"), _q("PR", "uz")),
    ], drawing=[
        "本题为XZ平面杆系；平面图用于核对朝向与投影，不增加空间杆件。",
        "PL、V、PR均为刚接折点；三个折点下方均无柱。",
        "屋面从左到右前两段5、后两段7 kN/m，均沿全局-Z并按实际杆长计。",
        "仅左右外柱脚固接。",
    ])


def _case050():
    m = _model()
    for i, x in enumerate((0, 12, 30, 40)):
        _node(m, f"B{i}", x, 0, restraint=_FIXED.copy())
    for name, x, z in [
        ("E0", 0, 6), ("J16", 12, 6), ("J18", 12, 8),
        ("J27", 30, 7), ("J28", 30, 8), ("E3", 40, 7),
        ("M0", 6, 6), ("M1", 21, 8), ("M2", 35, 7),
    ]:
        _node(m, name, x, z)
    for eid, a, b in [
        ("column0", "B0", "E0"),
        ("column1_lower", "B1", "J16"), ("column1_upper", "J16", "J18"),
        ("column2_lower", "B2", "J27"), ("column2_upper", "J27", "J28"),
        ("column3", "B3", "E3"),
    ]:
        _member(m, eid, a, b, "C1", "column")
    for i, (a, midpoint, b, q) in enumerate([
        ("E0", "M0", "J16", 5.0),
        ("J18", "M1", "J28", 7.0),
        ("J27", "M2", "E3", 6.0),
    ]):
        for suffix, start, end in [("left", a, midpoint), ("right", midpoint, b)]:
            eid = f"roof{i}_{suffix}"
            _member(m, eid, start, end)
            _udl(m, eid, q)
    return _descriptor(m, [
        _output("Connected geometric roof midpoints M0, M1 and M2: Uz",
                *[_q(f"M{i}", "uz") for i in range(3)]),
        _base_moments(True, "First interior column base", "B1", "column1_lower"),
        _base_moments(True, "Second interior column base", "B2", "column2_lower"),
    ], english=True, notes=[
        "Output convention completion: report both support My and column-root "
        "section M2 at each requested interior column base, with their sign conventions.",
    ], drawing=[
        "Keep both column segments between J16/J18 and J27/J28; all joints are rigid.",
        "M0, M1 and M2 are connected midpoint observation nodes without supports or releases.",
        "Roof loads from left to right: global -Z 5, 7 and 6 kN/m. All four bases fixed.",
    ])


def build():
    """Return fresh, explicit model/output descriptors for the ten assigned cases."""
    builders = [_case041, _case042, _case043, _case044, _case045,
                _case046, _case047, _case048, _case049, _case050]
    return {f"MM-{i:03d}": fn() for i, fn in enumerate(builders, 41)}


def render_multiview(path, case, desc, en, view, Canvas, num):
    """Separate coincident projections without changing the physical model.

    These are graphical input sheets: dimensions stay on the actual orthographic
    views, while visible endpoint keys identify each projected member uniquely.
    """
    if case not in {"MM-042", "MM-049"}:
        return False
    if case == "MM-042":
        _render042(path, desc, view, Canvas, num)
    else:
        _render049(path, desc, view, Canvas, num)
    return True


def _view_header(cv, case, view, english=True):
    axes = ''.join(view).upper()
    cv.text(45, 25, f'{case} | {axes} ' + ('ORTHOGRAPHIC INPUT' if english else '正交输入图'), 38)
    cv.text(45, 88, 'Schematic: use dimensions, do not scale. Dots are joints; crossings without dots are not joints.' if english else
            '示意图：以标注尺寸为准，禁止量图。实心点为节点，无点交叉不连接。', 25)
    cv.text(45, 130, 'Length m; force kN; line load kN/m per actual member length. Global Z up.' if english else
            '长度 m；力 kN；线载 kN/m 按实际杆长。全局 Z 向上。', 25)


def _view_pin(cv, x, y, label='PIN xyz'):
    cv.line([(x, y+9), (x-18, y+38), (x+18, y+38), (x, y+9)], '#328044', 3)
    cv.line([(x-25, y+43), (x+25, y+43)], '#328044', 2)
    cv.text(x-45, y+48, label, 21, '#24683a')


def _view_member_key(cv, x, y, elements, size=22, step=34):
    for j, e in enumerate(elements):
        cv.text(x, y+j*step, f'{e["id"]}: {e["nodes"][0]} -> {e["nodes"][1]} / {e["section"]}', size, '#15648c')


def _view042_loads(cv, y):
    cv.text(45, y, 'Case D: all listed loads act together. Unlisted components are zero. Forces use global axes.', 25)
    for j, line in enumerate([
        'D-1 at L3V1: Fx=12 kN, Fy=0, Fz=-10 kN.',
        'D-2 at L3V2: Fx=0, Fy=8 kN, Fz=-10 kN.',
        'D-3 at L3V3: Fx=0, Fy=0, Fz=-10 kN.',
    ]):
        cv.text(55+j*950, y+44, line, 23, '#a62c23')
    cv.text(45, y+93, 'All members: M1, axial-only. Verticals A1; rings A2; diagonals A3. Base L0V1/L0V2/L0V3: Ux=Uy=Uz=0.', 24)
    cv.text(45, y+132, 'All other translations are free; all nodal rotations are inactive and restrained. Repeated nodes in different panels are the same joints.', 23)


def _render042(path, desc, view, Canvas, num):
    m = desc['model']
    nodes = {n['id']: n for n in m['nodes']}
    elements = m['elements']
    cv = Canvas(3000, 2220)
    _view_header(cv, 'MM-042', view)
    if view == ('x', 'y'):
        cv.text(45, 184, 'Four separate ring-level plans. Interlevel verticals and cyclic diagonals are defined by the XZ/YZ side-face sheets.', 25)
        for level in range(4):
            ox, oy = 45+(level % 2)*1490, 250+(level // 2)*830
            cv.text(ox, oy, f'L{level} ring | Z={num(2.5*level)} m | vertices V1 -> V2 -> V3 counterclockwise', 27)
            def point(n):
                return ox+180+n['x']*245, oy+470-n['y']*90
            members = [e for e in elements if e['id'].startswith(f'ring_{level}_')]
            for e in members:
                u, v = [point(nodes[n]) for n in e['nodes']]
                cv.line([u, v], '#24394b', 5)
                x, y = (u[0]+v[0])/2, (u[1]+v[1])/2
                cv.text(x-60, y+15 if e['id'].endswith('_1') else y-65, e['id'], 23, '#15648c')
            for vertex in range(1, 4):
                n = nodes[f'L{level}V{vertex}']; x, y = point(n)
                cv.circle(x, y)
                cv.text(x+20 if vertex == 2 else x-70, y-42, n['id'], 25)
                if vertex == 3:
                    cv.text(x+100, y-42, 'Y=2*sqrt(3) m', 23)
                else:
                    cv.text(x-65, y+25 if level else y+102, 'Y=0 m', 22)
                if level == 0:
                    _view_pin(cv, x, y)
                if level == 3:
                    cv.text(x-70, y-85, f'D-{vertex}', 23, '#a62c23')
                    if vertex == 1:
                        cv.arrow((x-100, y), (x, y))
                    elif vertex == 2:
                        cv.arrow((x, y+95), (x, y))
            chain_y = oy+620
            cv.line([(ox+180, chain_y), (ox+1160, chain_y)], '#7e8a91', 2)
            for x in (0, 2, 4):
                px = ox+180+x*245
                cv.line([(px, chain_y-10), (px, chain_y+10)], '#7e8a91', 2)
                cv.text(px-12, chain_y+16, num(x), 23)
            cv.text(ox+1200, chain_y+8, 'X (m)', 23)
            _view_member_key(cv, ox+15, oy+685, members, 23, 32)
        _view042_loads(cv, 1970)
    else:
        a, _ = view
        cv.text(45, 184, f'Three side faces projected on {a.upper()}Z. Each panel retains its actual axis coordinates; shared edges are repeated.', 25)
        for side, (va, vb) in enumerate([(1, 2), (2, 3), (3, 1)]):
            ox = 45+side*990
            cv.text(ox, 245, f'Side V{va} -> V{vb}', 31)
            lower = nodes[f'L0V{va}'][a]; upper = nodes[f'L0V{vb}'][a]
            amin, amax = min(lower, upper), max(lower, upper)
            degenerate = abs(amax-amin) < 1e-10
            cv.text(ox, 292, f'{a.upper()} projection: '+('coincident endpoints at 0 m' if degenerate else f'{num(amin)} to {num(amax)} m'), 24)
            if degenerate:
                cv.text(ox, 330, 'Both vertices retain distinct IDs; rings project to points.', 22)
            def point(n):
                x = ox+445 if degenerate else ox+180+(n[a]-amin)/(amax-amin)*590
                return x, 1120-n['z']*90
            members = [e for e in elements if
                       (e['id'].startswith('ring_') and e['id'].endswith(f'_{va}')) or
                       (e['id'].startswith('vertical_') and e['id'].rsplit('_', 1)[-1] in {str(va), str(vb)}) or
                       (e['id'].startswith('diagonal_') and e['id'].endswith(f'_{va}'))]
            # Tags are intentionally short on the graph. The complete IDs and
            # endpoints immediately below prevent long-label collisions.
            for e in members:
                u, v = [point(nodes[n]) for n in e['nodes']]
                color = '#936019' if e['id'].startswith('diagonal') else '#24394b'
                cv.line([u, v], color, 5)
            for level in range(4):
                if degenerate:
                    x, y = point(nodes[f'L{level}V{va}']); cv.circle(x, y)
                    cv.text(x+35, y-32, f'L{level}V{va} / L{level}V{vb}', 24)
                    cv.text(x-200, y-32, f'Z={num(2.5*level)} m', 24)
                    cv.text(x+35, y+12, f'ring_{level}_{va} (point)', 21, '#15648c')
                    if level == 0:
                        _view_pin(cv, x, y, 'Both PIN xyz')
                else:
                    for vertex in (va, vb):
                        n = nodes[f'L{level}V{vertex}']; x, y = point(n)
                        cv.circle(x, y)
                        cv.text(x-115 if x < ox+475 else x+20, y-17, n['id'], 23)
                        if level == 0:
                            _view_pin(cv, x, y)
                    cv.text(ox+25, 1120-2.5*level*90-15, num(2.5*level), 23)
                    cv.text(ox+430, 1120-2.5*level*90+10, f'R{level}', 21, '#15648c')
                if level:
                    y = 1120-(level-.5)*2.5*90
                    if degenerate:
                        cv.text(ox+70, y-15, f'V{level}a, V{level}b, D{level}', 21, '#15648c')
                    else:
                        cv.text(ox+445, y-60, f'D{level}', 23, '#936019')
                        for letter, vertex in [('a', va), ('b', vb)]:
                            x, _ = point(nodes[f'L0V{vertex}'])
                            cv.text(x+16, y-15, f'V{level}{letter}', 22, '#15648c')
            if not degenerate:
                cv.text(ox+12, 395, 'Z (m)', 23)
            cv.line([(ox+180, 1235), (ox+770, 1235)], '#7e8a91', 2)
            for coordinate in sorted({lower, upper}):
                px = ox+445 if degenerate else ox+180+(coordinate-amin)/(amax-amin)*590
                cv.line([(px, 1225), (px, 1245)], '#7e8a91', 2)
                cv.text(px-35, 1260, num(coordinate), 23)
            cv.text(ox+830, 1300, a.upper()+' (m)', 23)
            cv.text(ox, 1320, 'Key: ID : start -> end / section (all M1)', 23)
            key_rows = []
            for level in range(4):
                key_rows.append((f'R{level}', f'ring_{level}_{va}'))
            for level in range(1, 4):
                key_rows.extend([(f'V{level}a', f'vertical_{level}_{va}'),
                                 (f'V{level}b', f'vertical_{level}_{vb}'),
                                 (f'D{level}', f'diagonal_{level}_{va}')])
            by_id = {e['id']: e for e in members}
            for j, (tag, eid) in enumerate(key_rows):
                e = by_id[eid]
                cv.text(ox, 1363+j*34, f'{tag} = {eid}: {e["nodes"][0]} -> {e["nodes"][1]} / {e["section"]}', 21, '#15648c')
        _view042_loads(cv, 1970)
    cv.save(path)


def _render049(path, desc, view, Canvas, num):
    m = desc['model']; nodes = {n['id']: n for n in m['nodes']}
    a, b = view
    cv = Canvas(2700, 1830)
    _view_header(cv, 'MM-049', view, False)
    cv.text(45, 185, '本题为 XZ 平面刚架，全部 Y=0。投影重合的节点仍保留各自 ID；各折点均刚接，折点下方无柱。', 25)
    cv.text(45, 228, '绿色为 BL/BR 固支；红色荷载由独立引线及构件 ID 指明，全部组成工况 D。未列荷载分量为零。', 25)
    amin, amax = min(n[a] for n in nodes.values()), max(n[a] for n in nodes.values())
    bmin, bmax = min(n[b] for n in nodes.values()), max(n[b] for n in nodes.values())
    degenerate = abs(amax-amin) < 1e-10
    def point(n):
        x = 610 if degenerate else 180+(n[a]-amin)/max(amax-amin, 1)*1770
        y = 1010 if bmax == bmin else 1060-(n[b]-bmin)/(bmax-bmin)*640
        return x, y
    for e in m['elements']:
        cv.line([point(nodes[n]) for n in e['nodes']], '#24394b', 5)
    groups = {}
    for n in nodes.values():
        groups.setdefault(point(n), []).append(n)
    # Coordinate labels belong to the geometric view. Coincident IDs are one
    # combined annotation, with a leader to the projected joint.
    for (x, y), group in groups.items():
        cv.circle(x, y)
        label = '/'.join(n['id'] for n in group)+f' [{b.upper()}={num(group[0][b])}]'
        if degenerate:
            tx, ty = x-370, y-15
            cv.line([(tx+320, ty+17), (x-12, y)], '#7e8a91', 2)
        else:
            tx, ty = x-65, y+25
            if any(all(n['restraints']) for n in group):
                ty += 65
            if bmax != bmin and group[0]['z'] == 0:
                ty = y+90
        cv.text(tx, ty, label, 24)
        fixed = [n['id'] for n in group if all(n['restraints'])]
        if fixed:
            cv.line([(x-23, y+8), (x+23, y+8), (x+23, y+28), (x-23, y+28), (x-23, y+8)], '#328044', 3)
            for dx in [-16, -5, 6, 17]:
                cv.line([(x+dx, y+9), (x+dx-10, y+27)], '#328044', 2)
            cv.text(x-50, y+48, '/'.join(fixed)+' 固支', 22, '#24683a')
    # Four separate rows are essential in the YZ projection: roof2 and roof4
    # have coincident projected load-label anchors but different magnitudes.
    for j, l in enumerate(m['load_cases'][0]['loads']):
        e = next(e for e in m['elements'] if e['id'] == l['element'])
        u, v = [point(nodes[n]) for n in e['nodes']]
        anchor = ((u[0]+v[0])/2, (u[1]+v[1])/2)
        if degenerate:
            tx, ty = 1090, 385+j*160
            cv.line([(tx-20, ty+20), (880+j*32, ty+20), anchor], '#b8342b', 2)
        else:
            tx, ty = 150+j*620, 325+(j % 2)*105
            cv.line([(tx+125, ty+65), (tx+125, ty+92), anchor], '#b8342b', 2)
        cv.text(tx, ty, f'D/{l["id"]} | {e["id"]} | wz={num(l["wz"])} kN/m', 25, '#a62c23')
        cv.text(tx, ty+36, '全杆、全局 -Z，按实际杆长计。', 23, '#a62c23')
        cv.circle(*anchor, 5, '#b8342b')
        # The arrow uses the actual projected force direction; out-of-plane
        # loads are explicitly identified by their global component above.
        if b == 'z':
            ax, ay = u[0]+.85*(v[0]-u[0]), u[1]+.85*(v[1]-u[1])
            cv.arrow((ax-18, ay-55), (ax-18, ay-12))
    cy = 1250
    cv.line([(180, cy), (1950, cy)], '#7e8a91', 2)
    for coordinate in sorted(set(n[a] for n in nodes.values())):
        px = 610 if degenerate else 180+(coordinate-amin)/max(amax-amin, 1)*1770
        cv.line([(px, cy-10), (px, cy+10)], '#7e8a91', 2)
        cv.text(px-15, cy+16, num(coordinate), 23)
    cv.text(2000, cy+5, a.upper()+' (m)', 24)
    if degenerate:
        cv.text(1090, 1100, 'YZ 为真实侧投影：各节点均在 Y=0，构件投影可重合。', 24)
        cv.text(1090, 1140, '完整 X 坐标与折线连接关系请联合读取 XZ / XY 图。', 24)
    cv.text(45, 1365, '构件索引：ID : 起点 -> 终点 / 截面；全部材料 M1。各投影中的同名节点表示同一节点。', 25)
    for j, e in enumerate(m['elements']):
        _view_member_key(cv, 55+(j % 2)*1290, 1420+(j//2)*46, [e], 25, 36)
    cv.text(45, 1600, '屋面从左到右 roof1/roof2 向下 5 kN/m；roof3/roof4 向下 7 kN/m，均按实际杆长。', 25)
    cv.text(45, 1648, '仅 BL/BR 全固定；所有其他节点均为刚接自由节点。XZ 平面外 uy/rx/rz 为非作用自由度。', 25)
    cv.text(45, 1696, 'PL、V、PR 三个屋面折点下方均无柱；不得将重叠投影误认为连接或附加空间杆件。', 25)
    cv.save(path)
