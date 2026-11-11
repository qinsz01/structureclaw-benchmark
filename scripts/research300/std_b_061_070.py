"""Explicit STD-061..070 source-specific builders; no numerical truth is authored.

The reusable geometry/property primitives are read from the frozen representative
script. Its hard-coded cases are never imported as source specifications.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace

from std_b_common import emit


ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("std_b_061_070_primitives", ROOT / "scripts/representative-models.py")
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)


def _model(concrete=None):
    m = R.model(concrete=bool(concrete))
    if concrete == "C30":
        m["materials"][0].update(name="C30", E=30000, G=12500)
    # These are explicit benchmark appendices, not material/section defaults.
    m["sections"] = [R.section("B1", .3, .6), R.section("C1", .5, .5)]
    return m


def _frame(xs, zs, *, concrete=None):
    """Build only a source-declared complete grid; zs includes the base level."""
    m = _model(concrete)
    for j, z in enumerate(zs):
        for i, x in enumerate(xs):
            R.node(m, f"n{i}-{j}", x, z, restraint=[True] * 6 if j == 0 else None)
    for j in range(1, len(zs)):
        for i in range(len(xs)):
            R.elem(m, f"c{i}-{j}", f"n{i}-{j-1}", f"n{i}-{j}", "column", "C1")
        for i in range(len(xs) - 1):
            R.elem(m, f"b{i}-{j}", f"n{i}-{j}", f"n{i+1}-{j}")
    return m


def _udl(m, eid, q):
    R.load(m, type="distributed", element=eid, wz=-q)


def _floor_nodes(m):
    return [n["id"] for n in m["nodes"] if n["id"].startswith("n") and not n["id"].endswith("-0")]


def _supports(m):
    return [n["id"] for n in m["nodes"] if n["id"].endswith("-0")]


def _length(m, eid):
    e = next(e for e in m["elements"] if e["id"] == eid)
    ns = {n["id"]: n for n in m["nodes"]}
    a, b = [ns[n] for n in e["nodes"]]
    return math.dist([a[k] for k in ("x", "y", "z")], [b[k] for k in ("x", "y", "z")])


class Requests:
    """Deduplicate operand quantities while retaining explicit required outputs."""

    def __init__(self, m):
        self.model = m
        self.quantities = {}
        self.derived = []
        self.outputs = []

    def node(self, nid, component):
        qid = f"D-node-{nid}-{component}"
        self.quantities[qid] = dict(id=qid, selection=dict(kind="case", id="D"),
            location=dict(kind="node", id=nid), component=component,
            unit="rad" if component.startswith("r") else "kN*m" if component.startswith("M") else "kN" if component.startswith("F") else "m",
            tolerance=dict(absolute=1e-8, relative=1e-6))
        return qid

    def member(self, eid, end, component):
        x = 0 if end == "i" else _length(self.model, eid)
        qid = f"D-member-{eid}-{end}-{component}"
        self.quantities[qid] = dict(id=qid, selection=dict(kind="case", id="D"),
            location=dict(kind="member", id=eid, positionM=x, side="right" if end == "i" else "left"),
            component=component, unit="kN*m" if component.startswith("M") or component == "T" else "kN",
            tolerance=dict(absolute=1e-8, relative=1e-6))
        return qid

    def output(self, oid, description, ids, kind="numerical"):
        self.outputs.append(dict(id=oid, description=description, state=1, quantityIds=ids, kind=kind))

    def displacements(self, nodes, *, oid="joint-displacements", description="节点 ux、uz 位移及 ry 转角", components=("ux", "uz", "ry")):
        self.output(oid, description, [self.node(n, c) for n in nodes for c in components])

    def reactions(self, nodes, description="各柱脚全局反力 Fx、Fz 和反力矩 My"):
        self.output("base-reactions", description, [self.node(n, c) for n in nodes for c in ("Fx", "Fz", "My")])

    def end_forces(self, ends, *, oid="member-end-forces", description="指定构件端截面内力 N、V3、M2"):
        self.output(oid, description, [self.member(e, end, c) for e, end in ends for c in ("N", "V3", "M2")])

    def differences(self, pairs, description="逐柱线相邻实际节点的上端减下端位移差 Δux、Δuz"):
        ids = []
        for low, high in pairs:
            for c in ("ux", "uz"):
                qid = f"D-difference-{high}-minus-{low}-{c}"
                self.derived.append(dict(id=qid, operation="difference", operands=[self.node(high, c), self.node(low, c)], unit="m",
                    description=f"{high}.{c} - {low}.{c}; upper minus lower, no division by story height"))
                ids.append(qid)
        self.output("column-displacement-differences", description, ids, "derived")

    def payload(self, number, instruction, decisions):
        return dict(number=number, model=self.model, instruction=instruction, decisions=decisions,
            quantities=list(self.quantities.values()), derived=self.derived, outputs=self.outputs)


def case061():
    m = _frame([0, 4.5, 12], [0, 3.6, 7.8])
    for e, q in (("b0-1", 8), ("b1-1", 12), ("b0-2", 6), ("b1-2", 10)):
        _udl(m, e, q)
    r = Requests(m)
    r.displacements(_floor_nodes(m), description="两层、三柱线上全部六个梁柱节点的 ux、uz 位移及 ry 转角")
    r.differences([(f"n{i}-{j-1}", f"n{i}-{j}") for j in (1, 2) for i in range(3)])
    r.reactions(_supports(m))
    return r.payload(61,
        "建立并用 OpenSees 分析附件中的两层两跨钢框架：跨长依次 4.5、7.5 m；层高依次 3.6、4.2 m，楼层标高为 3.6、7.8 m。三柱脚固定。下层左、右梁向下线载分别为 8、12 kN/m，上层分别为 6、10 kN/m，均属于工况 D。输出六个楼层柱线节点的 ux、uz、ry，逐柱线逐层的 Δux、Δuz（上端减下端），以及三柱脚 Fx、Fz、My。按附件的材料、截面、局部轴和设置进行一阶线弹性静力分析，自重关闭。",
        ["补齐单钢材料 Q355 及 B1 梁、C1 柱的数值属性；使用附件明列的矩形理想化截面。",
         "‘每层每柱线位移’明确为 ux、uz、ry；‘层间位移差’明确为逐柱列 Δux 和 Δuz，上层减下层，不除以层高。",
         "四根梁的线载分别为 8、12、6、10 kN/m，保留实际不等跨度与累计标高。"])


def case062():
    m = _model()
    # Exact setback: there is no node, column, beam, or load at the upper right.
    for name, x, z in [("n0-0", 0, 0), ("n1-0", 6, 0), ("n2-0", 12, 0),
                       ("n0-1", 0, 3.6), ("n1-1", 6, 3.6), ("n2-1", 12, 3.6),
                       ("n0-2", 0, 6.9), ("n1-2", 6, 6.9)]:
        R.node(m, name, x, z, restraint=[True] * 6 if name.endswith("-0") else None)
    for eid, a, b, kind in [("c0-1", "n0-0", "n0-1", "column"), ("c1-1", "n1-0", "n1-1", "column"),
                            ("c2-1", "n2-0", "n2-1", "column"), ("c0-2", "n0-1", "n0-2", "column"),
                            ("c1-2", "n1-1", "n1-2", "column"), ("b0-1", "n0-1", "n1-1", "beam"),
                            ("b1-1", "n1-1", "n2-1", "beam"), ("b0-2", "n0-2", "n1-2", "beam")]:
        R.elem(m, eid, a, b, kind, "C1" if kind == "column" else "B1")
    for eid in ("b0-1", "b1-1", "b0-2"):
        _udl(m, eid, 10)
    r = Requests(m)
    r.displacements(_floor_nodes(m), description="Global ux, uz and ry at all three lower-floor joints and both upper-floor joints")
    edge_nodes = {"n1-1", "n1-2", "n2-1"}
    ends = [(e["id"], end) for e in m["elements"] for end, n in zip(("i", "j"), e["nodes"]) if n in edge_nodes]
    r.end_forces(ends, description="Local N, V3 and M2 at every member end incident at setback-edge joints n1-1, n1-2 and n2-1")
    r.reactions(_supports(m), "Global Fx, Fz and My at all three fixed column bases")
    return r.payload(62,
        "Build and analyze the attached two-story steel frame in OpenSees. The lower story has two 6 m bays at elevation z=3.6 m. The upper story is 3.3 m high (z=6.9 m) and contains only the left 6 m bay. All three bases are fixed. Each of the three actual beams carries 10 kN/m vertically downward in case D. Report ux, uz and ry at all five floor joints; N, V3 and M2 at every member end incident at setback-edge joints n1-1, n1-2 and n2-1; and Fx, Fz and My at all three bases. Use the attached explicit material, section and axis definitions for first-order linear elastic static analysis with self-weight disabled.",
        ["The appendix completes the unspecified Q355 steel, B1 beam and C1 column properties with explicit idealized rectangular sections.",
         "Setback-edge response is requested at all incident ends at (6,3.6), (6,6.9) and (12,3.6) m, covering both the step corners and the exposed lower edge.",
         "The upper-right bay has no nodes, columns, beams or applied loads; the upper story exists only over x=0..6 m."])


def case063():
    m = _frame([0, 6], [0, 3.6, 7.2])
    m["sections"].append(R.section("A1", .1, .1))
    R.elem(m, "brace1", "n0-0", "n1-1", "truss", "A1")
    R.elem(m, "brace2", "n1-0", "n0-1", "truss", "A1")
    _udl(m, "b0-1", 10)
    _udl(m, "b0-2", 10)
    R.load(m, type="nodal", node="n1-2", fx=30)
    r = Requests(m)
    r.displacements(_floor_nodes(m), description="两层左右柱顶 ux 侧移及完整平面节点位移 ux、uz、ry")
    r.output("brace-axial-forces", "两根首层斜撑轴力 N，拉为正", [r.member(e, "i", "N") for e in ("brace1", "brace2")])
    r.end_forces([(e["id"], end) for e in m["elements"] if e["type"] != "truss" for end in ("i", "j")],
        description="所有梁柱两端的局部 N、V3、M2；斜撑为纯轴力杆，不承担弯矩")
    r.reactions(_supports(m))
    return r.payload(63,
        "用 OpenSees 建立附件中的两层单跨钢框架：跨度 6 m，两层层高均为 3.6 m，两柱脚固定。首层两根对角斜撑均为两端铰接的纯轴力桁架杆，在几何交叉点互不连接；其余梁柱刚接。工况 D 下，两层梁各承受向下 10 kN/m，顶层右节点承受 +X 向 30 kN。输出两层左右柱顶 ux 侧移，并列出 ux、uz、ry；两根斜撑轴力；全部梁柱两端 N、V3、M2；以及两柱脚 Fx、Fz、My。采用附件完整属性、轴定义和一阶线弹性设置，自重关闭。",
        ["补齐 Q355 钢、B1 梁、C1 柱及 A1 轴力斜撑的显式数值属性。",
         "斜撑端点共享框架节点的平移，但 truss 单元不传递转角或弯矩；交点 (3,0,1.8) m 处没有节点。",
         "30 kN 顶层水平力与两根梁的重力线载同时属于 D 工况，未添加未指定组合。"])


def case064():
    m = _frame([0, 6], [0, 3.6, 7.2])
    for j, z in ((1, 3.6), (2, 7.2)):
        R.node(m, f"tip-{j}", 7.5, z)
        R.elem(m, f"overhang-{j}", f"n1-{j}", f"tip-{j}")
        _udl(m, f"b0-{j}", 10)
        _udl(m, f"overhang-{j}", 5)
    r = Requests(m)
    r.displacements(["tip-1", "tip-2"], oid="cantilever-tip-displacements", description="Vertical uz at the free end of each 1.5 m overhang", components=("uz",))
    r.output("cantilever-root-moments", "Local M2 at the overhang side of both rigid roots", [r.member(f"overhang-{j}", "i", "M2") for j in (1, 2)])
    r.displacements(_floor_nodes(m), description="Global ux, uz and ry at the left and right column tops on both floors")
    r.reactions(_supports(m), "Global Fx, Fz and My at both fixed column bases")
    return r.payload(64,
        "Analyze the attached two-story single-bay steel frame in OpenSees. Each story is 3.6 m high and the main span is 6 m. A 1.5 m overhang extends rightward from the beam-column joint on each floor, with a rigid root and a free tip. Both column bases are fixed. In case D, each main-span beam carries 10 kN/m downward and each overhang carries 5 kN/m downward. Report the vertical displacement uz of both free tips, M2 at both overhang roots, ux/uz/ry at each left and right floor column top, and Fx/Fz/My at both bases. Use the attached properties and axes with first-order linear elastic static analysis and self-weight disabled.",
        ["The appendix supplies Q355 material and explicit B1 beam/overhang and C1 column properties.",
         "Root moment means the local M2 section force on the overhang side at position 0 m, side right; each overhang is rigidly connected to its own floor joint.",
         "The 10 and 5 kN/m loads are applied once to their respective 6 m and 1.5 m member regions."])


def case065():
    m = _frame([0, 5, 10], [0, 3.3, 6.6, 9.9])
    # Split each physical beam at its actual connected displacement observation node.
    m["elements"] = [e for e in m["elements"] if e["type"] == "column"]
    midpoints = []
    for j, (z, q) in enumerate(((3.3, 12), (6.6, 10), (9.9, 6)), 1):
        for i in (0, 1):
            mid = f"mid-{i}-{j}"
            midpoints.append(mid)
            R.node(m, mid, 5 * i + 2.5, z)
            R.elem(m, f"b{i}-{j}a", f"n{i}-{j}", mid)
            R.elem(m, f"b{i}-{j}b", mid, f"n{i+1}-{j}")
            _udl(m, f"b{i}-{j}a", q)
            _udl(m, f"b{i}-{j}b", q)
    r = Requests(m)
    r.displacements(midpoints, oid="beam-midpoint-displacements", description="三层各两跨共六个连通梁跨中节点的竖向位移 uz", components=("uz",))
    r.displacements(_floor_nodes(m), description="三层各三柱线共九个柱顶的 ux、uz、ry")
    r.reactions(_supports(m))
    return r.payload(65,
        "用 OpenSees 分析附件中的三层两跨钢框架：每层高 3.3 m，两跨均为 5 m，三个柱脚固定。D 工况下从底到顶的梁线载分别为向下 12、10、6 kN/m，每层左右两跨相同。各梁在几何跨中设置与梁连续连通、无额外支承的观测节点。输出每层每跨梁中点 uz，三层各柱线柱顶 ux、uz、ry，以及三柱脚 Fx、Fz、My。按附件明确的材料、截面与轴设置进行一阶线弹性静力分析，自重关闭。",
        ["补齐 Q355 材料、B1 梁、C1 柱的显式弹性属性。",
         "六个梁跨中均使用连通观测节点；每跨两半段分别施加相同的规定线载强度，不重复施加全跨总力。",
         "逐层线载为 12、10、6 kN/m；实际楼层标高为 3.3、6.6、9.9 m，无水平外力。"])


def case066():
    m = _frame([0, 6, 12], [0, 3.6, 7.2])
    m["sections"].extend([R.section("C2", .35, .5), R.section("B2", .3, .7)])
    for e in m["elements"]:
        if e["id"].startswith("c1-"):
            e["section"] = "C2"
        if e["id"].startswith("b1-"):
            e["section"] = "B2"
        if e["type"] == "beam":
            _udl(m, e["id"], 8)
    R.load(m, type="nodal", node="n2-2", fx=25)
    r = Requests(m)
    r.end_forces([(e, end) for e in ("c0-1", "c1-1", "b0-1", "b1-1") for end in ("i", "j")],
        description="Both-end N, V3 and M2 of group representatives c0-1 (C1), c1-1 (C2), b0-1 (B1), and b1-1 (B2)")
    r.differences([(f"n{i}-{j-1}", f"n{i}-{j}") for j in (1, 2) for i in range(3)],
        "Upper-minus-lower Δux and Δuz along each of the three column lines at both stories")
    r.reactions(_supports(m), "Global Fx, Fz and My at all three fixed column bases")
    r.output("member-section-schedule", "Return the complete member-to-section schedule, preserving exterior C1, interior C2, left-bay B1 and right-bay B2 on both stories", [], "interaction")
    return r.payload(66,
        "Build and analyze the attached two-story, two-bay steel frame in OpenSees. Both bays are 6 m and both stories are 3.6 m high; all three bases are fixed. On both stories, exterior columns use C1, the middle column uses C2, left-bay beams use B1 and right-bay beams use B2. In case D, every beam carries 8 kN/m downward and the upper-right joint carries 25 kN in +X. Report N/V3/M2 at both ends of c0-1, c1-1, b0-1 and b1-1 as the four section-group representatives; Δux and Δuz (upper minus lower) for both stories along every column line; all base Fx/Fz/My; and the complete member/section assignment table. Use the explicit appendix properties and axes for first-order linear elastic static analysis with self-weight disabled.",
        ["The appendix supplies four distinct rectangular section groups: C1=500x500 mm, C2=350x500 mm, B1=300x600 mm and B2=300x700 mm; these dimensions complete missing source appendices.",
         "The required group representatives are frozen as c0-1, c1-1, b0-1 and b1-1, with both ends requested. The complete schedule still covers every member on both stories.",
         "Column displacement differences are requested separately for every column line, without a rigid-floor constraint or averaging."])


def case067():
    m = _frame([0, 5, 10], [0, 3.6, 7.2])
    m["elements"] = [e for e in m["elements"] if e["id"] != "c1-2"]
    for e in m["elements"]:
        if e["type"] == "beam":
            _udl(m, e["id"], 10)
    r = Requests(m)
    r.displacements(["n1-2"], oid="top-beam-midpoint", description="顶层连续梁在 x=5 m 的无支承连通中点 n1-2 的竖向位移 uz", components=("uz",))
    r.displacements(["n0-1", "n2-1", "n0-2", "n2-2"], oid="side-column-displacements", description="上下两层两侧柱顶侧移 ux", components=("ux",))
    r.displacements(["n1-1"], oid="lower-middle-column-top-displacement", description="下层中柱顶 n1-1 的 ux、uz、ry")
    r.end_forces([("c1-1", "j"), ("b0-1", "j"), ("b1-1", "i")],
        description="下层中柱顶 n1-1 处下柱及左右梁端的 N、V3、M2")
    r.reactions(_supports(m))
    return r.payload(67,
        "用 OpenSees 建立附件中的两层两跨钢框架：两跨均为 5 m，两层层高均为 3.6 m。下层中柱存在，上层中柱不存在；顶层梁在 x=5 m 处保持刚接连续节点 n1-2，该节点没有额外支座。三个现有底柱脚固定。工况 D 下所有四根实际梁均承受向下 10 kN/m。输出顶层梁中点 n1-2 的 uz、两层两侧柱顶 ux、下层中柱顶 n1-1 的 ux/uz/ry 及其相邻三构件端 N/V3/M2，以及三个柱脚 Fx/Fz/My。按附件属性与轴进行一阶线弹性静力分析，自重关闭。",
        ["补齐 Q355 材料、B1 梁及 C1 柱的显式数值属性。",
         "上层 c1-2 完全缺失；顶梁中点 n1-2 由左右梁共用，平面内 ux、uz、ry 均自由。",
         "‘下层中柱顶响应’完整规定为 n1-1 的 ux、uz、ry，以及 c1-1 的 j 端、b0-1 的 j 端、b1-1 的 i 端 N、V3、M2；两侧柱顶侧移覆盖上下两层。"])


def case068():
    m = _frame([0, 6], [-1.5, 0, 2.1, 5.7])
    m["sections"].append(R.section("T1", .3, .5))
    next(e for e in m["elements"] if e["id"] == "b0-1")["section"] = "T1"
    _udl(m, "b0-2", 10)
    _udl(m, "b0-3", 10)
    r = Requests(m)
    r.displacements(_floor_nodes(m), description="Global ux, uz and ry at both ground tie-beam joints and all four upper-floor joints")
    r.differences([(f"n{i}-{j-1}", f"n{i}-{j}") for j in (1, 2, 3) for i in (0, 1)],
        "Upper-minus-lower Δux and Δuz of every actual column segment: -1.5 to 0, 0 to 2.1, and 2.1 to 5.7 m, separately on both lines")
    r.end_forces([("b0-1", "i"), ("b0-1", "j")], description="Local N, V3 and M2 at both ends of the unloaded ground tie beam b0-1")
    r.reactions(_supports(m), "Global Fx, Fz and My at both fixed bases at z=-1.5 m")
    return r.payload(68,
        "Analyze the attached 6 m single-bay steel frame in OpenSees using the stated absolute elevations. Both column bases are fixed at z=-1.5 m. An unloaded, full-span, rigidly connected ground tie beam joins the column lines at z=0; two upper floor beams are at z=2.1 m and z=5.7 m. Only these upper beams carry 10 kN/m downward in case D. Report ux/uz/ry at all ground and upper beam-column joints, separate upper-minus-lower Δux/Δuz for every actual column segment, N/V3/M2 at both tie-beam ends, and Fx/Fz/My at both bases. Use the explicit appendix properties and axes for first-order linear elastic static analysis with self-weight disabled.",
        ["The appendix supplies Q355 material, C1 column, B1 floor-beam and T1 ground tie-beam properties; T1 is an explicitly completed 300x500 mm idealized rectangle.",
         "The absolute elevations are retained. The six actual column segments have heights 1.5, 2.1 and 3.6 m on the two column lines.",
         "Ground nodes have only the planar out-of-plane constraints, with ux/uz/ry free. The tie beam has no external load and creates no ground support."])


def case069():
    m = _frame([0, 6], [0, 3.6, 7.2], concrete="C30")
    next(n for n in m["nodes"] if n["id"] == "n0-0")["restraints"] = [True, True, True, True, False, True]
    _udl(m, "b0-1", 72)
    _udl(m, "b0-2", 72)
    r = Requests(m)
    r.displacements(_floor_nodes(m), description="两层左右四节点的全局 X/Z 位移 ux、uz", components=("ux", "uz"))
    r.displacements(["n0-0"], oid="left-pinned-base-rotation", description="左侧铰支柱脚 n0-0 的自由转角 ry", components=("ry",))
    r.differences([(f"n{i}-{j-1}", f"n{i}-{j}") for j in (1, 2) for i in (0, 1)])
    r.reactions(_supports(m), "左铰、右固两柱脚的 Fx、Fz、My；必须保留左柱脚零弯矩对应量")
    return r.payload(69,
        "用 OpenSees 分析附件中的两层单跨 C30 混凝土弹性框架：跨度 6 m，两层各高 3.6 m；左柱脚铰支（ux、uz 约束，ry 自由），右柱脚固定。柱截面 500×500 mm，梁截面 300×600 mm。D 工况下两根梁各只施加一次向下 72 kN/m 线载。输出两层左右节点 ux、uz，左柱脚 ry，逐柱列逐层上端减下端 Δux、Δuz，以及两柱脚 Fx、Fz、My。采用附件给定的弹性参数及局部轴，进行一阶线弹性静力分析，自重关闭，不作配筋或承载力推断。",
        ["C30 弹性参数明确采用 E=30000 MPa、nu=0.2、G=12500 MPa、rho=2500 kg/m³；均为输入属性，不推导承载力。",
         "题定梁柱尺寸保留，截面 A、Iy、Iz、J 数值在附件中明确；材料与截面分组不互换。",
         "左柱脚仅释放平面内 ry；72 kN/m 已是线载，未再次乘以分担宽度，且自重关闭。",
         "逐层位移差为每柱列 Δux、Δuz，上端减下端；左柱脚 My 仍作为要求量以核验铰支边界。"])


def case070():
    m = _frame([0, 6], [0, 3.3, 6.6, 9.9], concrete="C35")
    for eid in ("b0-1", "b0-2", "b0-3"):
        _udl(m, eid, 60)
    r = Requests(m)
    r.displacements(_floor_nodes(m), description="Global ux, uz and ry at the left and right joints on all three floors")
    r.differences([(f"n{i}-{j-1}", f"n{i}-{j}") for j in (1, 2, 3) for i in (0, 1)],
        "Upper-minus-lower Δux and Δuz for each story, separately along both column lines")
    r.reactions(_supports(m), "Global Fx, Fz and My at both fixed column bases")
    return r.payload(70,
        "Analyze the attached three-story, single-bay C35 concrete frame in OpenSees. The span is 6 m and all three story heights are 3.3 m, giving floor elevations 3.3, 6.6 and 9.9 m. Both bases are fixed. Columns are 500x500 mm and beams are 300x600 mm. In case D, apply the already-converted downward line load of 60 kN/m once to each of the three beams. Report ux/uz/ry at all six floor joints, Δux/Δuz as upper-minus-lower displacement differences separately along each column line on each story, and Fx/Fz/My at both bases. Use the appendix elastic properties and axes, first-order linear elastic static analysis, and self-weight disabled. Do not infer reinforcement or load-carrying capacity.",
        ["C35 elastic properties are explicit inputs: E=31500 MPa, nu=0.2, G=13125 MPa and rho=2500 kg/m³.",
         "The given 500x500 mm column and 300x600 mm beam dimensions are retained as separate section groups with explicit A, Iy, Iz and J.",
         "Each 60 kN/m load is already a line load and is applied once. Floor displacements and differences retain both independent column lines without a diaphragm constraint."])


def build_cases():
    return [case061(), case062(), case063(), case064(), case065(), case066(), case067(), case068(), case069(), case070()]


if __name__ == "__main__":
    for case in build_cases():
        en = case["number"] % 2 == 0
        decisions = case["decisions"] + ([
            "Frame members use linear elastic Euler-Bernoulli bending and axial deformation. No shear deformation, end releases, member mass or additional loads are introduced. Beam/column joints and supports follow the explicit input table.",
            "The supplied torsion constant J is the frozen rectangular-section approximation in input-data.json. Use the numerical A, Iy, Iz and J values supplied, with local y and z as stated in analysis-conventions.txt."
        ] if en else [
            "梁柱采用线弹性 Euler-Bernoulli 弯曲及轴向变形模型，不计剪切变形；仅采用模型中明列的支座约束和轴力杆，不添加端释放、节点质量或额外荷载。",
            "input-data.json 中的 J 为明确冻结的矩形截面扭转常数近似值；使用附表给定的 A、Iy、Iz、J 数值，局部 y、z 轴按 analysis-conventions.txt 定义。"
        ])
        interactions = [o["description"] for o in case["outputs"] if o["kind"] == "interaction"]
        emit(case["number"], case["model"], case["instruction"],
             SimpleNamespace(quantities=case["quantities"], derived=case["derived"]),
             notes=decisions, interactions=interactions,
             extra_attachments={
                 "output-scope.json": dict(requiredOutputs=case["outputs"]),
                 "appendix-decisions.txt": "\n".join(decisions) + "\n",
             })
