"""Explicit research-300 authoring specifications for MM-089 through MM-098.

All geometry and loading below comes from the complete planning source rows.
The section/material completions are benchmark inputs, not inferred standards.
No numerical reference answers or claims of native validation are generated.
"""
from math import isclose, sqrt

from mm_b_common import p


def _node_request(node, component, description, selection=None):
    selection = selection or dict(kind="case", id="D")
    return dict(id=f"{selection['kind']}-{selection['id']}-{node}-{component}",
                location=dict(kind="node", id=node), component=component,
                unit="m" if component.startswith("u") else "kN*m" if component.startswith("M") else "kN",
                description=description, selection=selection)


def _member_request(member, position, component, description, side="right"):
    return dict(id=f"case-D-{member}-{component}-s{position:g}-{side}",
                location=dict(kind="member", id=member, positionM=position, side=side),
                component=component, unit="kN*m" if component.startswith("M") else "kN",
                description=description)


def _udl(m, value=8, case="D"):
    for e in m["elements"]:
        if e["type"] == "beam":
            p.load(m, case, id=f"{case}-{e['id']}", type="distributed", element=e["id"], wz=-value)


def _spec(number, m, title, requests, notes, decisions):
    return dict(id=f"MM-{number:03}", model=m, title_en=title, requests=requests,
                public_notes=notes, decisions=decisions)


def _case089():
    m = p.spatial([0, 4, 8, 12], [0, 5, 10], [3.6, 7.2])
    m["sections"] = [p.section("C1", .4, .5), p.section("C2", .45, .6),
                     p.section("C3", .5, .65), p.section("B1", .22, .45),
                     p.section("B2", .25, .5), p.section("B3", .28, .55)]
    for n in m["nodes"]:
        if n["id"] in ("n1-1-0", "n2-1-0"):
            n["restraints"] = [True, True, True, False, False, False]
    for e in m["elements"]:
        ix, iy, _ = map(int, e["id"][1:].split("-"))
        if e["type"] == "column":
            edges = int(ix in (0, 3)) + int(iy in (0, 2))
            e["section"] = {2: "C1", 1: "C2", 0: "C3"}[edges]
        elif e["id"].startswith("y"):
            e["section"] = "B1"
        else:
            e["section"] = "B3" if iy == 1 else "B2"
    _udl(m)
    p.load(m, id="D-corner", type="nodal", node="n3-2-2", fx=20, fy=10)
    req = [_node_request("n3-2-2", c, f"顶层远角节点 n3-2-2 的全局 {c}") for c in ("ux", "uy")]
    req += [_member_request(f"c{i}-1-1", 0, "N", f"内柱 c{i}-1-1 在柱脚内侧的轴力 N（受拉为正）") for i in (1, 2)]
    return _spec(89, m, "Spatial frame with pinned interior bases and six section groups", req,
                 ["材料 M1 为线弹性钢，E=206000 MPa、ν=0.30、G=E/[2(1+ν)]、ρ=7850 kg/m³。截面表内六组均为实心矩形，其数值为本题明定输入。",
                  "构件局部 1 轴由首节点指向末节点；参考向量 r 确定局部 2=(r×1)/|r×1|，局部 3=1×2。柱取 r=+X，梁取 r=+Z。",
                  "输出柱脚轴力取下层柱 s=0 的构件内侧；支座竖向反力不能替代轴力输出。"],
                 ["Completed absent M1 elastic parameters with E=206000 MPa, nu=0.30, rho=7850 kg/m3 and G=E/(2*(1+nu)).",
                  "Completed six unspecified section groups as solid rectangles: C1 400x500, C2 450x600, C3 500x650, B1 220x450, B2 250x500, B3 280x550 mm; A/I/J are explicitly calculated in the appendix.",
                  "Resolved far corner as maximum X, maximum Y on the roof. Interior column base axial forces are N at s=0+ of c1-1-1 and c2-1-1, positive in tension."])


def _case090():
    m = p.spatial([0, 6], [0, 5, 10], [3.6, 7.2])
    m["sections"] = [p.section("C1", .3, .5), p.section("B1", .25, .45)]
    for n in m["nodes"]:
        if n["id"] == "n0-0-0":
            n["restraints"] = [True, True, True, False, False, False]
    for e in m["elements"]:
        if e["type"] == "beam":
            e["section"] = "B1"
        if e["id"] in ("c0-0-2", "c1-2-2"):
            e["rotation_angle"] = 90
    _udl(m)
    p.load(m, id="D-corner", type="nodal", node="n1-2-2", fx=20, fy=15)
    req = [_node_request("n1-2-2", c, f"Global {c} at rear-right roof node n1-2-2") for c in ("ux", "uy")]
    for s, side in [(0, "right"), (3.6, "left")]:
        for c in ("M2", "M3"):
            req.append(_member_request("c0-0-2", s, c,
                        f"Front-left upper column c0-0-2: local {c} at s={s:g} m, inside the member", side))
    return _spec(90, m, "Spatial frame with a pinned corner base and rotated upper column segments", req,
                 ["M1 is elastic steel: E=206000 MPa, nu=0.30, G=E/[2(1+nu)], rho=7850 kg/m3. C1 is a solid 300 by 500 mm rectangle; B1 is a solid 250 by 450 mm rectangle.",
                  "Local axis 1 runs from the first node to the second. Before roll, axis 2 is normalized r cross 1 and axis 3 is 1 cross 2; r=+X for vertical columns and r=+Z for beams. A positive 90-degree roll gives 2'=3 and 3'=-2.",
                  "Report both M2 and M3 at both ends of the named upper column, measured on the member interior. Section orientation and member roll are shown separately in the views."],
                 ["Completed absent elastic material and rectangular section records with M1 E=206000 MPa, nu=0.30, rho=7850 kg/m3; C1 300x500 mm and B1 250x450 mm.",
                  "Frozen reference-axis convention: vertical columns use +X reference; unrolled axes are 1=+Z, 2=-Y, 3=+X. Positive 90-degree roll rotates only c0-0-2 and c1-2-2; lower segments keep zero roll.",
                  "The unspecified station for front-left upper-column biaxial moments is completed as both local M2/M3 at both s=0+ and s=3.6- m."])


def _case091():
    m = p.spatial([0, 6, 12], [0, 5, 10], [3.6, 7.2])
    m["sections"] = [p.section("C1", .35, .5), p.section("B1", .25, .45)]
    m["elements"] = [e for e in m["elements"] if e["id"] != "y1-0-2"]
    del m["metadata"]["elementReferenceVectors"]["y1-0-2"]
    for e in m["elements"]:
        if e["type"] == "beam":
            e["section"] = "B1"
    _udl(m)
    for eid in ("x1-1-2", "x1-2-2", "y1-1-2", "y2-1-2"):
        p.load(m, "L", id=f"L-{eid}", type="distributed", element=eid, wz=-6)
    m["load_combinations"] = [dict(id="D", factors={"D": 1}), dict(id="D+L", factors={"D": 1, "L": 1})]
    req = []
    for combo in ("D", "D+L"):
        for node, label in [("n2-2-2", "顶层后右既有节点"), ("n1-1-2", "顶层中心既有节点")]:
            req.append(_node_request(node, "uz", f"组合 {combo}：{label} {node} 的全局 Uz", dict(kind="combination", id=combo)))
    return _spec(91, m, "Spatial frame with a missing roof beam and one live-loaded bay", req,
                 ["M1：E=206000 MPa、ν=0.30、G=E/[2(1+ν)]、ρ=7850 kg/m³。C1/B1 分别为 350×500/250×450 mm 实心矩形。",
                  "DXF 采用 m；源坐标与全局 XYZ 同向，Z 向上。非结构图层中的荷载区域框线只作索引，不构成梁或约束。",
                  "须分别执行显式组合 D={基本工况 D:1} 与 D+L={D:1,L:1}；组合 D 和同名基本工况 D 的选择类型须保留。",
                  "局部 1 轴沿构件首节点至末节点，2=(r×1)/|r×1|，3=1×2；竖柱 r=+X、梁 r=+Z。"],
                 ["Completed M1 and missing section properties: E=206000 MPa, nu=0.30, rho=7850 kg/m3; solid C1 350x500 mm and B1 250x450 mm.",
                  "Represented the requested D and D+L as explicit combinations, with a D combination distinct from its same-name basic case.",
                  "Live loading is applied once to each of the four actual roof edges of the rear-right bay: x1-1-2, x1-2-2, y1-1-2, y2-1-2. The absent member y1-0-2 has no load or residual reference vector."])


def _case092():
    m = p.model("3d")
    m["sections"] = [p.section("C1", .35, .5), p.section("B1", .24, .45), p.section("B2", .2, .35)]
    for ix, x in enumerate((0, 6, 12)):
        for iy, y in enumerate((0, 5)):
            p.node(m, f"n{ix}-{iy}-0", x, 0, y, [True]*6)
            p.node(m, f"n{ix}-{iy}-1", x, 8 if ix == 1 else 6, y)
            p.elem(m, f"c{ix}-{iy}", f"n{ix}-{iy}-0", f"n{ix}-{iy}-1", "column", "C1")
    for ix in (0, 1):
        for iy in (0, 1):
            p.elem(m, f"x{ix}-{iy}", f"n{ix}-{iy}-1", f"n{ix+1}-{iy}-1", sec="B1")
    for ix in (0, 1, 2):
        p.elem(m, f"y{ix}", f"n{ix}-0-1", f"n{ix}-1-1", sec="B2")
    _udl(m, 6)
    req = [_node_request(f"n1-{iy}-1", "uz", f"Global Uz at {'front' if iy == 0 else 'rear'} ridge node n1-{iy}-1") for iy in (0, 1)]
    for ix in (0, 2):
        for iy in (0, 1):
            for c in ("Mx", "My"):
                req.append(_node_request(f"n{ix}-{iy}-0", c, f"Global support moment {c} at outer column base n{ix}-{iy}-0"))
    return _spec(92, m, "Double-pitched spatial roof frame", req,
                 ["M1: E=206000 MPa, nu=0.30, G=E/[2(1+nu)], rho=7850 kg/m3. Solid rectangles: C1 350 by 500 mm, B1 240 by 450 mm, B2 200 by 350 mm.",
                  "Distributed load intensity is force per metre of actual member length. Its direction is global -Z; it is neither normal to the roof nor measured per projected metre.",
                  "Local axis 1 runs from first to second node; axis 2 is normalized r cross 1; axis 3 is 1 cross 2. Reference r=+X for columns and r=+Z for all roof beams, including the sloping beams.",
                  "Outer-base moments mean both global Mx and My reactions at every outer-column base identified in the views."],
                 ["Completed material and three section records with E=206000 MPa, nu=0.30, rho=7850 kg/m3; solid C1 350x500, B1 240x450, B2 200x350 mm.",
                  "Resolved unspecified outer column foot moment directions and locations as both Mx and My support reactions at all four x=0 or x=12 m bases.",
                  "All seven roof beams carry 6 kN/m global downward on their true lengths; four sloped beams have length sqrt(40) m and three longitudinal beams have length 5 m."])


def _case093():
    m = p.spatial([0, 6], [0, 5], [3.6, 7.2])
    m["sections"] = [p.section("C1", .35, .5), p.section("B1", .25, .45), p.section("A1", .06, .06)]
    for e in m["elements"]:
        if e["type"] == "beam":
            e["section"] = "B1"
    p.elem(m, "brace-front-up", "n0-0-0", "n1-0-1", "truss", "A1")
    p.elem(m, "brace-front-down", "n1-0-0", "n0-0-1", "truss", "A1")
    p.elem(m, "brace-rear-up", "n0-1-1", "n1-1-2", "truss", "A1")
    p.elem(m, "brace-rear-down", "n1-1-1", "n0-1-2", "truss", "A1")
    _udl(m)
    p.load(m, id="D-corner", type="nodal", node="n1-1-2", fx=20, fy=15)
    req = [_node_request("n1-1-2", c, f"顶层右后角 n1-1-2 的全局 {c}") for c in ("ux", "uy")]
    req += [_member_request(eid, 0, "N", f"首层前侧支撑 {eid} 的轴力 N（拉为正、压为负）") for eid in ("brace-front-up", "brace-front-down")]
    return _spec(93, m, "Spatial frame with X bracing on opposite faces in successive stories", req,
                 ["M1：E=206000 MPa、ν=0.30、G=E/[2(1+ν)]、ρ=7850 kg/m³。实心矩形 C1=350×500 mm、B1=250×450 mm、A1=60×60 mm；A1 仅取 EA 轴向刚度。",
                  "轴力支撑只传递拉压轴力，端部不传弯矩；图中交叉不连接符号必须保留，不能以投影相交创建节点。",
                  "梁柱局部 1 轴沿首节点至末节点，2=(r×1)/|r×1|，3=1×2；柱 r=+X、梁 r=+Z。首层前侧两根支撑均需分别报告 N。"],
                 ["Completed missing M1/C1/B1/A1 records with steel E=206000 MPa, nu=0.30, rho=7850 kg/m3 and solid rectangles 350x500, 250x450, 60x60 mm respectively.",
                  "Resolved plural first-story front brace axial forces as both actual crossing members, with positive N in tension. Each brace is one unsplit axial-only member, so the geometric crossing is not a structural joint."])


def _case094():
    m = p.spatial([0, 4, 11], [0, 6], [3.5, 7.5])
    m["sections"] = [p.section("C1", .35, .5), p.section("B1", .25, .45)]
    for n in m["nodes"]:
        if n["id"].endswith("-1-0"):
            n["z"] = -1
    for e in m["elements"]:
        if e["type"] == "beam":
            e["section"] = "B1"
    _udl(m)
    # Source-to-global proper rotation: (u,v,w) -> (u,-w,v).
    source_force = (10, -20, 5)
    p.load(m, id="D-source-force", type="nodal", node="n2-0-2",
           fx=source_force[0], fy=-source_force[2], fz=source_force[1])
    req = [_node_request("n2-0-2", c, f"Global {c} at front-right roof node n2-0-2") for c in ("ux", "uy", "uz")]
    req += [_node_request("n2-1-0", c, f"Global support reaction {c} at rear-right actual base n2-1-0") for c in ("Fx", "Fy", "Fz", "Mx", "My", "Mz")]
    spec = _spec(94, m, "Spatial frame in source coordinates with staggered foundation elevations", req,
                 ["The drawings use right-handed source axes (u,v,w), with +v upward. Convert coordinates, translation constraints, force vectors and moment vectors by (X,Y,Z)=(u,-w,v). Report all requested results in global XYZ axes.",
                  "Input vectors in the drawing use source axes: the marked point force is (Fu,Fv,Fw)=(10,-20,5) kN. The marked uniform beam loads are (qu,qv,qw)=(0,-8,0) kN/m of actual beam length.",
                  "M1: E=206000 MPa, nu=0.30, G=E/[2(1+nu)], rho=7850 kg/m3. Solid rectangular sections: C1 350 by 500 mm and B1 250 by 450 mm.",
                  "Local axis 1 runs from first to second node; axis 2 is normalized r cross 1 and axis 3 is 1 cross 2. In source components, column reference r=(1,0,0), beam reference r=(0,1,0). Report all six global support reaction components at the marked rear-right base."],
                 ["Completed M1/C1/B1 with E=206000 MPa, nu=0.30, rho=7850 kg/m3 and solid rectangles 350x500 / 250x450 mm.",
                  "Applied the proper orthogonal transform X=u, Y=-w, Z=v consistently. Source force (10,-20,5) kN becomes global (10,-5,-20) kN; source distributed vector (0,-8,0) becomes global (0,0,-8).",
                  "Retained actual rear foundation Z=-1 m, producing 4.5 m rear lower columns versus 3.5 m front lower columns; upper columns are 4 m.",
                  "Completed unspecified rear-right column foot reaction components as all six global Fx/Fy/Fz/Mx/My/Mz at n2-1-0."])
    spec["source_coordinates"] = dict(axes=["u", "v", "w"], up="v",
                                     global_from_source=[[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    return spec


def _case095():
    m = p.model(concrete=True)
    m["materials"] = [dict(id="C40", name="C40", type="concrete", E=32500, G=32500/2.4, nu=.2, rho=2500),
                      dict(id="C30", name="C30", type="concrete", E=30000, G=12500, nu=.2, rho=2500)]
    m["sections"] = [p.section("C1", .4, .4)]
    p.node(m, "base", 0, 0, restraint=[True]*6)
    p.node(m, "interface", 0, 2)
    p.node(m, "top", 0, 4.5)
    p.elem(m, "lower", "base", "interface", "column", "C1")
    p.elem(m, "upper", "interface", "top", "column", "C1")
    m["elements"][0]["material"] = "C40"
    m["elements"][1]["material"] = "C30"
    p.load(m, id="D-axial", type="nodal", node="top", fz=-500)
    req = [_node_request("top", "uz", "柱顶 top 的全局 Uz"), _node_request("interface", "uz", "材料分界节点 interface 的全局 Uz"),
           _member_request("lower", 0, "N", "下段柱 lower 在柱脚内侧的轴力 N（受拉为正）")]
    return _spec(95, m, "Two-material segmented column under axial compression", req,
                 ["C40：E=32500 MPa；C30：E=30000 MPa。两材料均取 ν=0.20、ρ=2500 kg/m³，G=E/[2(1+ν)]。这些是本题给定线弹性输入，不采用自动开裂或刚度折减。",
                  "C1 为 400×400 mm 实心正方形，完整 A/I/J 见截面表。平面分析保留 X、Z 平移和 Ry，其他自由度仅作平面外约束。",
                  "轴力 N 取 lower 首端构件内侧，拉为正、压为负。"],
                 ["Completed missing elastic material constants as C40 E=32500 MPa and C30 E=30000 MPa, both nu=0.20 and rho=2500 kg/m3; G=E/(2*(1+nu)).",
                  "Used the specified 400x400 mm solid square and its explicit elastic A/I/J. The material interface is one shared connected node; no end releases or duplicate nodes.",
                  "Completed the base axial-force station as s=0+ on lower, N positive in tension."])


def _case096():
    m = p.model(concrete=True)
    m["materials"] = [dict(id="M1", name="C30", type="concrete", E=30000, G=12500, nu=.2, rho=2500)]
    m["sections"] = [p.section("C1", .45, .45)]
    p.node(m, "base", 0, 0, restraint=[True]*6)
    p.node(m, "lateral-support", 0, 2.1, restraint=[True, True, False, True, False, True])
    p.node(m, "top", 0, 4.2)
    p.elem(m, "lower", "base", "lateral-support", "column", "C1")
    p.elem(m, "upper", "lateral-support", "top", "column", "C1")
    p.load(m, id="D-top", type="nodal", node="top", fz=-600, fx=30)
    req = [_node_request("top", "ux", "Global Ux at column top node top"),
           _node_request("lateral-support", "Fx", "Global horizontal reaction Fx at node lateral-support")]
    return _spec(96, m, "Concrete column with a lateral restraint at mid-height", req,
                 ["C30 is elastic with E=30000 MPa, nu=0.20, G=12500 MPa and rho=2500 kg/m3. C1 is the specified solid 450 by 450 mm square; use the tabulated A/I/J without stiffness reductions.",
                  "Use planar XZ analysis with ux, uz and ry active. Constraints on uy, rx and rz enforce the plane only. An X-only support symbol restrains ux while leaving uz and ry free."],
                 ["Completed missing C30 elastic parameters as E=30000 MPa, nu=0.20, G=12500 MPa, rho=2500 kg/m3; calculated A/I/J for the specified 450x450 mm solid square.",
                  "The intermediate support restrains only the in-plane X displacement; uz and ry remain free, while uy/rx/rz are the global planar-model restrictions."])


def _case097():
    m = p.model()
    # Explicit idealized HW300x300x10x15 record; fillets are omitted by contract.
    h, b, tw, tf = .3, .3, .01, .015
    hw = h-2*tf
    section = dict(id="C1", name="HW300x300x10x15", type="H",
                   shape=dict(kind="H", H=300, B=300, tw=10, tf=15),
                   properties=dict(A=2*b*tf+hw*tw,
                                   Iy=(b*h**3-(b-tw)*hw**3)/12,
                                   Iz=(2*tf*b**3+hw*tw**3)/12,
                                   J=(2*b*tf**3+hw*tw**3)/3))
    m["sections"] = [section]
    p.node(m, "base", 0, 0, restraint=[True, True, True, True, False, True])
    p.node(m, "mid", 0, 2.5)
    p.node(m, "top", 0, 5, restraint=[True, True, False, True, False, True])
    p.elem(m, "lower", "base", "mid", "column", "C1")
    p.elem(m, "upper", "mid", "top", "column", "C1")
    p.load(m, id="D-axial", type="nodal", node="top", fz=-700)
    p.load(m, id="D-lateral", type="nodal", node="mid", fx=10)
    req = [_node_request("mid", "ux", "柱中点 mid 的全局 Ux"), _node_request("top", "uz", "柱顶 top 的全局 Uz")]
    req += [_node_request(n, "Fx", f"{'底端' if n == 'base' else '顶端'}节点 {n} 的全局水平反力 Fx") for n in ("base", "top")]
    return _spec(97, m, "Pinned steel column with a laterally guided top", req,
                 ["M1：E=206000 MPa、ν=0.30、G=E/[2(1+ν)]、ρ=7850 kg/m³。HW300×300 在本题明确采用 H=300、B=300、tw=10、tf=15 mm 的无圆角理想截面；完整 A/Iy/Iz/J 为给定分析值，不由软件截面库替代。",
                  "本题截面采用 A=2Btf+(H−2tf)tw，Iy=[BH³−(B−tw)(H−2tf)³]/12，Iz=[2tfB³+(H−2tf)tw³]/12，J=[2Btf³+(H−2tf)tw³]/3（计算时全部长度换为 m）。",
                  "XZ 平面分析保留 ux、uz、ry；局部 1 沿柱向上、局部 2=+Y、局部 3=−X，面内弯曲采用 Iy。图示侧向导向不限制竖向位移，两个端部均不限制 Ry。"],
                 ["Completed absent M1 properties as E=206000 MPa, nu=0.30, rho=7850 kg/m3.",
                  "The source gives only HW300x300 and requests a complete elastic record. Froze a benchmark idealization HW300x300x10x15 mm with sharp corners, explicitly computed A/Iy/Iz and thin-wall Saint-Venant J; this is not represented as an external catalogue record.",
                  "Specified planar local axes 1=+Z, 2=+Y, 3=-X; Iy is the in-plane bending inertia. Both end ry DOFs and top uz remain free."])


def _case098():
    m = p.model("3d")
    # Unequal-flange I: symmetric about local 3, asymmetric about local 2.
    # H is measured along local 3; the wider flange is on its positive side.
    h, b_plus, b_minus, tf, tw = .5, .3, .2, .02, .012
    rectangles = [(b_minus, tf, tf/2), (tw, h-2*tf, h/2), (b_plus, tf, h-tf/2)]
    area = sum(b*d for b, d, z in rectangles)
    centroid = sum(b*d*z for b, d, z in rectangles)/area
    column = dict(id="C1", name="Unequal-flange I 500x300/200x12x20", type="H",
                  shape=dict(kind="unequal-flange-I", H=500, Bpositive3=300, Bnegative3=200,
                             tw=12, tf=20, centroidFromNegative3Edge=centroid*1000),
                  properties=dict(A=area,
                                  Iy=sum(b*d**3/12+b*d*(z-centroid)**2 for b, d, z in rectangles),
                                  Iz=sum(d*b**3/12 for b, d, z in rectangles),
                                  J=((b_plus+b_minus)*tf**3+(h-2*tf)*tw**3)/3))
    m["sections"] = [column, p.section("B1", .2, .35)]
    p.node(m, "base", 0, 0, 0, [True]*6)
    p.node(m, "joint", 0, 3, 0)
    p.node(m, "top", 0, 6, 0)
    p.node(m, "tip", 0, 3, 2)
    p.elem(m, "lower-column", "base", "joint", "column", "C1")
    p.elem(m, "upper-column", "joint", "top", "column", "C1")
    p.elem(m, "side-arm", "joint", "tip", "beam", "B1")
    p.load(m, id="D-top", type="nodal", node="top", fx=20, fy=15, fz=-400)
    p.load(m, id="D-arm", type="nodal", node="tip", fz=-80)
    req = [_node_request("top", c, f"Global {c} at column top") for c in ("ux", "uy")]
    req += [_node_request("tip", "uz", "Global Uz at the free side-arm tip")]
    req += [_node_request("base", c, f"Global base reaction moment {c}" + (" as the zero-torsion equilibrium check" if c == "Mz" else "")) for c in ("Mx", "My", "Mz")]
    return _spec(98, m, "Spatial cantilever column with a rigid side arm at mid-height", req,
                 ["M1: E=206000 MPa, nu=0.30, G=E/[2(1+nu)], rho=7850 kg/m3. C1 is an unequal-flange I section: H=500 mm along local 3; flange widths 300 mm on +3 and 200 mm on -3; tw=12 mm and both tf=20 mm. B1 is a solid 200 by 350 mm rectangle.",
                  "C1 uses sharp corners. Its A and centroidal principal Iy/Iz are computed from the three non-overlapping rectangles; J=[(300+200)*20^3+460*12^3]/3 mm4 is the explicit thin-wall torsional input. Member lines pass through the section centroid; use the supplied uncoupled Euler-Bernoulli A/Iy/Iz/J record without additional offsets.",
                  "Columns: local 1=+Z, 2=-Y, 3=+X. Side arm: local 1=+Y, 2=-X, 3=+Z. Both column segments share the same unrolled section orientation.",
                  "Report Mx, My and Mz as global support reaction moments. Mz is a signed numerical equilibrium check against zero under first-order loading; the eccentric vertical arm load causes bending about X."],
                 ["Completed unspecified asymmetric C1 as an unequal-flange sharp-corner I section, H=500 mm, +3 flange width 300 mm, -3 flange width 200 mm, web 12 mm, flanges 20 mm; B1 is solid 200x350 mm. M1 E=206000 MPa, nu=0.30, rho=7850 kg/m3.",
                  "C1 is genuinely asymmetric about local 2 and has unequal centroidal principal inertias. Froze its wider flange on local +3; all A/Iy/Iz values are calculated from three rectangles and J uses the explicit thin-wall formula. The benchmark uses an uncoupled centroidal Euler-Bernoulli section record with no rigid or shear-center offsets.",
                  "Resolved column base Mx/My and zero-Mz check as global support reaction moments; all three are numerical requests. The arm is a real 2 m beam with a connected column joint, not an equivalent tip moment."])


def structural_checks(specs):
    """Source-level topology, supports, axis and load-resultant checks."""
    expected = {89: (36, 58), 90: (18, 26), 91: (27, 41), 92: (12, 13),
                93: (12, 20), 94: (18, 26), 95: (3, 2), 96: (3, 2), 97: (3, 2), 98: (4, 3)}
    for spec in specs:
        i = int(spec["id"][-3:])
        m = spec["model"]
        nodes = {n["id"]: n for n in m["nodes"]}
        elements = {e["id"]: e for e in m["elements"]}
        assert len(nodes) == len(m["nodes"]) and len(elements) == len(m["elements"])
        assert (len(nodes), len(elements)) == expected[i], spec["id"]
        assert all(e["nodes"][0] != e["nodes"][1] and all(n in nodes for n in e["nodes"]) for e in elements.values())
        assert all(sum((nodes[e["nodes"][1]][a]-nodes[e["nodes"][0]][a])**2 for a in ("x", "y", "z")) > 0 for e in elements.values())
        assert not any(m["analysis_control"].values())
        assert len({q["id"] for q in spec["requests"]}) == len(spec["requests"])
        assert all(q["location"]["id"] in (nodes if q["location"]["kind"] == "node" else elements) for q in spec["requests"])
    by_id = {int(s["id"][-3:]): s["model"] for s in specs}
    a = by_id[89]
    assert sum(n["restraints"] == [True]*3+[False]*3 for n in a["nodes"]) == 2
    assert {e["section"] for e in a["elements"]} == {"C1", "C2", "C3", "B1", "B2", "B3"}
    a = by_id[90]
    assert {e["id"] for e in a["elements"] if e.get("rotation_angle", 0)} == {"c0-0-2", "c1-2-2"}
    assert a["sections"][0]["properties"]["Iy"] != a["sections"][0]["properties"]["Iz"]
    a = by_id[91]
    assert "y1-0-2" not in {e["id"] for e in a["elements"]}
    live = next(c for c in a["load_cases"] if c["id"] == "L")["loads"]
    assert len(live) == 4 and len({l["element"] for l in live}) == 4
    assert {l["element"] for l in live} == {"x1-1-2", "x1-2-2", "y1-1-2", "y2-1-2"}
    for i, length in [(89, 152), (90, 76), (91, 127), (92, 4*sqrt(40)+15), (93, 44), (94, 80)]:
        a = by_id[i]
        n = {n["id"]: n for n in a["nodes"]}
        e = {e["id"]: e for e in a["elements"]}
        line_loads = [l for l in a["load_cases"][0]["loads"] if l["type"] == "distributed"]
        total_length = sum(sqrt(sum((n[e[l["element"]]["nodes"][1]][k]-n[e[l["element"]]["nodes"][0]][k])**2 for k in ("x", "y", "z"))) for l in line_loads)
        assert isclose(total_length, length, abs_tol=1e-10), (i, total_length, length)
        assert {l["element"] for l in line_loads} == {v["id"] for v in e.values() if v["type"] == "beam"}
    a = by_id[93]
    assert len([e for e in a["elements"] if e["type"] == "truss"]) == 4
    assert not any(isclose(n["x"], 3) for n in a["nodes"])
    a = by_id[94]
    assert sum(n["z"] == -1 for n in a["nodes"]) == 3
    f = next(l for l in a["load_cases"][0]["loads"] if l["type"] == "nodal")
    assert (f["fx"], f["fy"], f["fz"]) == (10, -5, -20)
    assert by_id[95]["elements"][0]["material"] != by_id[95]["elements"][1]["material"]
    n = {n["id"]: n for n in by_id[96]["nodes"]}
    assert [n["lateral-support"]["restraints"][j] for j in (0, 2, 4)] == [True, False, False]
    n = {n["id"]: n for n in by_id[97]["nodes"]}
    assert not n["top"]["restraints"][2] and not n["top"]["restraints"][4] and not n["base"]["restraints"][4]
    n = {n["id"]: n for n in by_id[98]["nodes"]}
    moment = [0., 0., 0.]
    for l in by_id[98]["load_cases"][0]["loads"]:
        x, y, z = (n[l["node"]][k] for k in ("x", "y", "z"))
        fx, fy, fz = (l.get(k, 0) for k in ("fx", "fy", "fz"))
        for j, value in enumerate((y*fz-z*fy, z*fx-x*fz, x*fy-y*fx)):
            moment[j] += value
    assert moment == [-250., 120., 0.]


def build_specs():
    specs = [_case089(), _case090(), _case091(), _case092(), _case093(),
             _case094(), _case095(), _case096(), _case097(), _case098()]
    structural_checks(specs)
    return specs


if __name__ == "__main__":
    from mm_b_common import export_specs
    export_specs(build_specs())
