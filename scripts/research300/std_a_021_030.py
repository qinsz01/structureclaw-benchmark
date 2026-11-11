"""Explicit source-based authoring for research-300 STD-021 through STD-030.

Only this shard's candidate inputs are written. No numerical truth is generated.
Legacy source scenarios are read-only provenance, never imported as solver models.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from std_a_core import emit, qmember, qnode


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("representative_primitives", ROOT / "scripts/representative-models.py")
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)

CASE_D = {"kind": "case", "id": "D"}


def beam_model(spans, section_ids, *, overhang=0):
    """Real, connected midpoint nodes retain beam rotations and span continuity."""
    m = rm.model()
    m["sections"] = [rm.section("B1", .3, .6)]
    if "B2" in section_ids:
        m["sections"].append(rm.section("B2", .3, .7))
    x = 0
    rm.node(m, "S0", x, 0, restraint=[True, True, True, True, False, True])
    for i, (length, section_id) in enumerate(zip(spans, section_ids), 1):
        rm.node(m, f"P{i}", x + length / 2, 0)
        rm.node(m, f"S{i}", x + length, 0,
                restraint=[False, True, True, True, False, True])
        rm.elem(m, f"B{i}a", f"S{i-1}", f"P{i}", sec=section_id)
        rm.elem(m, f"B{i}b", f"P{i}", f"S{i}", sec=section_id)
        x += length
    if overhang:
        rm.node(m, "TIP", x + overhang, 0)
        rm.elem(m, "OH", f"S{len(spans)}", "TIP", sec=section_ids[-1])
    m["metadata"] = {
        "spanLengthsM": spans,
        "spanSectionIds": section_ids,
        "observationNodes": {f"span-{i}-midpoint": f"P{i}" for i in range(1, len(spans) + 1)},
        "beamTheory": "Euler-Bernoulli",
        "localAxes": "Each beam runs along +global X; local 1=+X, local 2=+Y, local 3=+Z.",
        "continuity": "Every support and midpoint is one shared node; no member end releases.",
    }
    return m


def udl(m, magnitude, case="D", spans=None):
    for e in m["elements"]:
        if spans is None or e["id"][:-1] in {f"B{i}" for i in spans}:
            rm.load(m, case, id=f"{case}-{e['id']}", type="distributed", element=e["id"], wz=magnitude)


def beam_outputs(m, *, selection=CASE_D, internal_moments=True):
    """Complete in-plane support force vectors and all span midpoints."""
    n = len(m["metadata"]["spanLengthsM"])
    q = [qnode(m, f"S{i}", "Fz", selection) for i in range(n + 1)]
    q.extend(qnode(m, f"S{i}", "Fx", selection) for i in range(n + 1))
    q.extend(qnode(m, f"P{i}", "uz", selection) for i in range(1, n + 1))
    if internal_moments:
        for i in range(1, n):
            q.append(qmember(m, f"B{i}b", m["metadata"]["spanLengthsM"][i - 1] / 2,
                             "M2", selection, side="left"))
            q.append(qmember(m, f"B{i+1}a", 0, "M2", selection, side="right"))
    return q


BEAM_CHOICES_EN = (
    "The planning appendix did not supply material or section numbers. Frozen author choices: "
    "steel M1, E=206000 MPa, nu=0.3, G=79230.76923076923 MPa, rho=7850 kg/m3. "
    "B1 is a 0.3 m by 0.6 m solid rectangle; B2, where used, is a 0.3 m by 0.7 m solid rectangle. "
    "Their independent A, Iy, Iz and J values are explicit in the public properties table. "
    "Euler-Bernoulli, first-order linear static analysis; self-weight is disabled. "
    "All midpoint nodes are connected mesh nodes, not interpolation labels. "
    "Use local M2 section actions, not raw element end-force signs."
)
BEAM_CHOICES_ZH = (
    "规划中的材料截面附表尚未给定数值；本题冻结的编题选择为钢材M1：E=206000MPa、"
    "nu=0.3、G=79230.76923076923MPa、rho=7850kg/m³。B1为0.3m×0.6m实心矩形；"
    "使用B2时其为0.3m×0.7m实心矩形，A、Iy、Iz、J分别明示于公共属性表。"
    "采用Euler-Bernoulli一阶线弹性静力，自重关闭；跨中是实际连接节点。弯矩采用局部M2截面内力符号。"
)


def make_021():
    m = beam_model([6, 6], ["B1", "B2"])
    udl(m, -10)
    prompt = (
        "建立X-Z平面的两跨连续梁，跨度6m、6m，节点S0、S1、S2位于x=0、6、12m，z=0。"
        "S0铰支，S1、S2为仅约束竖向位移的双向滚支，所有支座绕Y转角自由。第一跨B1、第二跨B2，"
        "S1为两跨共用节点且无端释放。D工况全梁施加全局-Z方向10kN/m均布荷载。"
        "使用附件的完整几何、连接、材料、截面及荷载数据，以OpenSees完成一阶线弹性静力分析，自重关闭。"
        "输出D工况三个支座的Fx、Fz支反力、x=3m和9m实际跨中节点P1/P2的uz，"
        "以及x=6m中支座两侧的M2截面弯矩。所有结果保留符号，并标明位置、工况和单位。"
    )
    emit(21, m, prompt, beam_outputs(m), notes=[BEAM_CHOICES_ZH])


def make_022():
    m = beam_model([5, 5], ["B1", "B1"], overhang=2)
    udl(m, -8)
    rm.load(m, id="D-tip-force", type="nodal", node="TIP", fz=-10)
    q = beam_outputs(m, internal_moments=False)
    q += [qnode(m, "TIP", "uz", CASE_D),
          qmember(m, "B2b", 2.5, "M2", CASE_D, side="left"),
          qmember(m, "OH", 0, "M2", CASE_D, side="right")]
    prompt = (
        "Analyze a continuous beam in the global X-Z plane using OpenSees. Supports are at x=0, 5 and 10 m; "
        "the beam continues to the free tip at x=12 m. The left support is a pin and the other two are "
        "bilateral vertical rollers. All support rotations about Y remain free; all beam joints are continuous. "
        "Use material M1 and section B1 throughout, exactly as supplied in the public attachments. "
        "Load case D has 8 kN/m downward (global -Z) over the entire 12 m, including the overhang, and "
        "a separate 10 kN downward nodal force at the free tip x=12 m. Perform first-order linear static "
        "Euler-Bernoulli analysis with self-weight disabled. Report D: all three vertical support reactions "
        "and all horizontal support reactions; signed uz at the two supported-span midpoints x=2.5 and 7.5 m "
        "and at the free tip; and signed local M2 at the x=10 m support section on both sides. "
        "Identify locations, selection and units in the narrative and structured results."
    )
    emit(22, m, prompt, q, notes=[BEAM_CHOICES_EN, "The 10 kN tip-force direction was not separately stated in the short planning row; it is explicitly fixed as downward global -Z in this appendix."])


def make_023():
    m = beam_model([4, 6], ["B1", "B1"])
    rm.load(m, id="D-support-force", type="nodal", node="S1", fz=-30)
    rm.load(m, id="D-span-force", type="nodal", node="P2", fz=-20)
    prompt = (
        "建立两跨连续梁，跨度4m和6m，梁沿全局+X，Z向上。S0=(0,0,0)为铰支；"
        "S1=(4,0,0)、S2=(10,0,0)为双向竖向滚支，所有支座绕Y转角自由，无端释放。"
        "全梁使用附件M1/B1。在D工况分别于中支座S1施加全局-Z方向30kN节点力，"
        "于第二跨中点P2=(7,0,0)施加全局-Z方向20kN节点力，无均布荷载。"
        "按附件用OpenSees作一阶线弹性静力分析，自重关闭。输出三个支座的Fx、Fz支反力、"
        "第一跨中P1(x=2m)与第二跨中P2(x=7m)的uz，以及x=4m中支座两侧M2截面弯矩。"
        "保留符号和单位，并区分支座节点的30kN与跨内20kN：30kN应计入S1反力平衡，不得挪到跨内。"
    )
    emit(23, m, prompt, beam_outputs(m), notes=[BEAM_CHOICES_ZH,
         "规划短句未逐个重申点载方向；本题明确两个节点力均沿全局-Z向下。"],
         extra_outputs=[{"id": "support-load-distinction", "description": "区分S1的30kN支座节点力与P2的20kN跨内节点力；说明支座力进入反力平衡。", "state": 1, "quantityIds": [], "kind": "interaction"}])


def make_024():
    m = beam_model([5, 5, 5], ["B1", "B1", "B1"])
    udl(m, -8)
    udl(m, 6, "W", spans=[2])
    m["load_combinations"] = [{"id": "C0", "factors": {"D": 1}},
                              {"id": "C1", "factors": {"D": 1, "W": 1}}]
    q = [item for cid in ["C0", "C1"] for item in beam_outputs(m, selection={"kind": "combination", "id": cid})]
    prompt = (
        "Using the attached complete property and geometry tables, analyze a three-span continuous beam "
        "with spans 5, 5 and 5 m along global X. Global +Z is upward. S0 at x=0 is a pin; S1/S2/S3 at "
        "x=5/10/15 m are bilateral vertical rollers. Every support rotation about global Y remains free; "
        "the beam is continuous without end releases. All spans use M1/B1. Case D is -8 kN/m in global Z "
        "over all spans; case W is +6 kN/m in global Z only over the middle span x=5 to 10 m. "
        "Define exactly C0=D and C1=D+W. Run first-order linear static Euler-Bernoulli analysis in OpenSees "
        "with self-weight disabled. For each of C0 and C1 separately, report all four signed vertical "
        "support reactions and all horizontal support reactions, signed uz at x=2.5, 7.5 and 12.5 m, "
        "and signed local M2 on both sides of the two internal supports at x=5 and 10 m. "
        "Retain signs, including any negative reactions; the rollers restrain both vertical directions. "
        "Label every value with its combination, location and unit."
    )
    emit(24, m, prompt, q, notes=[BEAM_CHOICES_EN])


def make_025():
    m = beam_model([5, 5], ["B1", "B1"])
    udl(m, -6)
    rm.load(m, id="D-end-moment", type="nodal", node="S2", my=20)
    q = beam_outputs(m)
    q.append(qnode(m, "S2", "ry", CASE_D))
    q += [qmember(m, "B1a", 0, "M2", CASE_D, side="right"),
          qmember(m, "B1a", 2.5, "M2", CASE_D, side="left"),
          qmember(m, "B2a", 2.5, "M2", CASE_D, side="left"),
          qmember(m, "B2b", 2.5, "M2", CASE_D, side="left")]
    prompt = (
        "建立沿全局+X的两跨连续梁，跨度5m、5m，Z向上。S0(x=0m)铰支，"
        "S1(x=5m)、S2(x=10m)为双向竖向滚支；所有支座的绕Y转角自由，无端释放。"
        "全梁使用附件M1/B1，D工况全长施加全局-Z方向6kN/m均布荷载，右端S2另外施加"
        "绕全局+Y方向的20kN·m节点力矩，正号服从右手定则。按附件用OpenSees作"
        "一阶线弹性Euler-Bernoulli静力分析，自重关闭。输出D工况三个支座的Fx、Fz支反力、"
        "两跨中P1(x=2.5m)/P2(x=7.5m)的uz、右端S2的ry(rad)，并输出局部M2截面弯矩："
        "x=0右侧、x=2.5、x=5左右两侧、x=7.5和x=10左侧。所有数值保留符号，标明位置及单位。"
    )
    emit(25, m, prompt, q, notes=[BEAM_CHOICES_ZH,
         "原规划仅称‘截面弯矩’，未列全部截面。本附表冻结为两端、两跨中及中支座左右两侧，包含受外加力矩的右端。"])


def make_026():
    m = beam_model([4, 6, 5, 4], ["B1", "B2", "B2", "B1"])
    udl(m, -8)
    udl(m, -10, "L", spans=[2, 4])
    m["load_combinations"] = [{"id": "C0", "factors": {"D": 1}},
                              {"id": "C1", "factors": {"D": 1.2, "L": 1.4}}]
    q = [item for cid in ["C0", "C1"] for item in beam_outputs(m, selection={"kind": "combination", "id": cid})]
    prompt = (
        "Analyze the attached four-span continuous beam in OpenSees. Span lengths from left to right are "
        "4, 6, 5 and 4 m, with supports S0/S1/S2/S3/S4 at global x=0/4/10/15/19 m, z=0. "
        "S0 is a pin; S1 through S4 are bilateral vertical rollers. All support rotations about Y are free, "
        "and every shared support node is continuous without member releases. Use material M1 throughout. "
        "Spans 1 and 4 use section B1; spans 2 and 3 use section B2, with the independent properties supplied. "
        "Case D applies -8 kN/m in global Z over the whole beam. Case L applies -10 kN/m in global Z "
        "only in spans 2 and 4. Define exactly C0=D and C1=1.2D+1.4L. Use first-order linear static "
        "Euler-Bernoulli analysis with self-weight disabled. For C0 and C1 separately, report all five "
        "vertical support reactions and all horizontal support reactions; signed uz at the four connected "
        "midpoint nodes P1/P2/P3/P4 (x=2/7/12.5/17 m); and signed local M2 on both sides of every "
        "internal support at x=4, 10 and 15 m. Identify each span, location, combination and unit."
    )
    emit(26, m, prompt, q, notes=[BEAM_CHOICES_EN])


def truss_model(coordinates, endpoints, supports):
    m = rm.model()
    # These property values are retained from the immutable legacy scenarios.
    m["materials"] = [{"id": "M1", "name": "steel", "type": "steel", "E": 205000,
                        "nu": .3, "G": 205000 / 2.6, "rho": 7850}]
    # Complete the public section appendix without activating beam behavior.
    # The exact source area remains 0.01 m²; Iy/Iz/J are inactive for truss elements.
    m["sections"] = [rm.section("T1", .1, .1)]
    m["sections"][0]["properties"].update(A=.01, Iy=.01**2 / 12, Iz=.01**2 / 12,
                                          J=.14083333333333334 * .01**2)
    for name, x, z in coordinates:
        # Truss rotations have no stiffness and are suppressed; this adds no translational support.
        support = supports.get(name)
        restraint = [support == "pin", True, support is not None, True, True, True]
        rm.node(m, name, x, z, restraint=restraint)
    for eid, a, b in endpoints:
        rm.elem(m, eid, a, b, "truss", "T1")
    m["metadata"] = {
        "trussContract": "Axial-only, pin-jointed elements. Only shared endpoint IDs connect members; geometric crossings do not add nodes.",
        "axialForceConvention": "N > 0 is tension; N < 0 is compression; report the signed value.",
        "inactiveDofs": "uy, rx, ry and rz are suppressed at every node; free in-plane translations remain ux and uz.",
    }
    return m


def truss_outputs(m, loaded_nodes, supports, member_ids=None):
    q = [qmember(m, e["id"], 0, "N", CASE_D) for e in m["elements"]
         if member_ids is None or e["id"] in member_ids]
    q.extend(qnode(m, nid, component, CASE_D) for nid in loaded_nodes for component in ["ux", "uz"])
    q.extend(qnode(m, nid, component, CASE_D) for nid in supports for component in ["Fx", "Fz"])
    return q


TRUSS_CHOICES_EN = (
    "Read-only legacy scenario properties are retained: steel E=205000 MPa, nu=0.3, "
    "rho=7850 kg/m3 and every rod area A=0.01 m2; G=78846.15384615384 MPa is explicitly completed. "
    "To complete the section appendix, T1 is explicitly a solid 0.1 m square with "
    "Iy=Iz=A^2/12 and frozen Saint-Venant J=0.14083333333333334*A^2; "
    "these bending and torsion constants are inactive because every element remains axial-only. "
    "The new planning contract overrides the legacy self-weight ambiguity: self-weight is disabled. "
    "Case D is the sole applied-load selection; no legacy default ULS combination is carried over. "
    "Requested in-plane node displacements are explicitly ux and uz. Reactions are Fx and Fz at both "
    "supports, including the zero free-X roller reaction. Non-translational truss DOFs are suppressed."
)
TRUSS_CHOICES_ZH = (
    "从只读旧题保留材料截面：E=205000MPa、nu=0.3、rho=7850kg/m³、全杆A=0.01m²；"
    "明确补齐G=78846.15384615384MPa。新规划契约要求自重关闭，优先于旧题关于后端自重的模糊说明。"
    "完整截面附表明确T1为边长0.1m的实心正方形，Iy=Iz=A²/12，Saint-Venant常数"
    "J=0.14083333333333334A²；这些弯曲和扭转常数在全部仅轴力桁架单元中不参与刚度。"
    "仅分析本题D工况，不沿用旧题默认ULS组合。所称节点位移明确包括ux、uz；左右支反力包括Fx、Fz，"
    "右端自由X方向反力亦列出。纯桁架非轴向运动自由度uy、rx、ry、rz作平面/无刚度自由度抑制。"
)


def make_027():
    # The asymmetric central-diagonal direction is copied exactly from both legacy prompts.
    coords = [(f"{level}{i}", x, z) for i, x in enumerate([0, 3, 6, 9, 12, 15])
              for level, z in [("B", 0), ("T", 2.5)]]
    endpoints = [(f"BC{i}", f"B{i}", f"B{i+1}") for i in range(5)]
    endpoints += [(f"TC{i}", f"T{i}", f"T{i+1}") for i in range(5)]
    endpoints += [(f"V{i}", f"B{i}", f"T{i}") for i in range(6)]
    endpoints += [("D0", "T0", "B1"), ("D1", "T1", "B2"), ("D2", "T2", "B3"),
                  ("D3", "B3", "T4"), ("D4", "B4", "T5")]
    m = truss_model(coords, endpoints, {"B0": "pin", "B5": "roller"})
    loaded = ["T1", "T2", "T3", "T4"]
    for nid in loaded:
        rm.load(m, id=f"D-{nid}", type="nodal", node=nid, fz=-10)
    q = truss_outputs(m, loaded, ["B0", "B5"])
    prompt = (
        "按附件明确节点和杆件端点表建立15m跨度、2.5m高、5个3m节间的平行弦Pratt桁架，"
        "位于X-Z平面，Z向上。下弦B0至B5和上弦T0至T5的x分别为0、3、6、9、12、15m；"
        "下弦z=0，上弦z=2.5m。上下弦分别连接相邻节点，每条节间线设Bi-Ti竖杆；"
        "五根斜杆严格依次为T0-B1、T1-B2、T2-B3、B3-T4、B4-T5，不按桁架名称修改连接。"
        "B0铰支，B5为全局X自由、Z双向约束的滚支。所有21根杆均为仅承轴力的铰接杆。"
        "D工况只在T1、T2、T3、T4各施加全局-Z方向10kN节点力。使用附件完整材料截面，"
        "以OpenSees作一阶线弹性静力分析，自重关闭。输出全部21根杆的有符号轴力N并逐杆标识拉/压/零力，"
        "N正为拉、负为压，绝对值不超过1e-8kN标为零力；输出四个受载上弦节点的ux和uz，"
        "以及B0、B5的Fx、Fz支反力，标明D工况、节点/杆号和单位。"
    )
    emit(27, m, prompt, q, notes=[TRUSS_CHOICES_ZH,
         "拓扑逐项读取scenarios/standard_workflow/truss-pratt-static.json与std-truss-pratt-15m.json；12节点21杆，第三斜杆为T2-B3。"],
         extra_outputs=[{"id": "member-tension-compression", "description": "逐杆提供全部21根杆的拉力/压力/零力标识；按有符号N判别，零力阈值1e-8kN。", "state": 1, "quantityIds": [qv["id"] for qv in q if qv["component"] == "N"], "kind": "interaction"}])


def make_028():
    coords = [(f"{level}{i}", x, z) for i, (x, height) in enumerate(
        [(0, 1.6), (3, 1.9), (6, 2.2), (9, 2.5), (12, 2.2), (15, 1.9), (18, 1.6)])
        for level, z in [("B", 0), ("T", height)]]
    endpoints = [(f"BC{i}", f"B{i}", f"B{i+1}") for i in range(6)]
    endpoints += [(f"TC{i}", f"T{i}", f"T{i+1}") for i in range(6)]
    endpoints += [(f"V{i}", f"B{i}", f"T{i}") for i in range(7)]
    endpoints += [(f"D{i}", f"T{i}", f"B{i+1}") for i in range(6)]
    m = truss_model(coords, endpoints, {"B0": "pin", "B6": "roller"})
    loaded = ["B1", "B2", "B3", "B4", "B5"]
    for nid in loaded:
        rm.load(m, id=f"D-{nid}", type="nodal", node=nid, fz=-15)
    prompt = (
        "Analyze the attached 18 m symmetric double-slope trapezoidal truss in the global X-Z plane. "
        "The horizontal bottom chord has six 3 m panels: B0 through B6 at x=0,3,6,9,12,15,18 m and z=0. "
        "Top nodes T0 through T6 have the same x coordinates and z=1.6,1.9,2.2,2.5,2.2,1.9,1.6 m. "
        "The top slope is +1/10 from x=0 to 9 m and -1/10 from x=9 to 18 m. Connect adjacent nodes "
        "along each chord, add all seven verticals Bi-Ti including both end verticals, and add exactly "
        "T0-B1, T1-B2, T2-B3, T3-B4, T4-B5 and T5-B6 as web diagonals. Use the full 25-member endpoint "
        "table and axial-only, pin-jointed rods. B0 is a pin; B6 is a bilateral vertical roller free in global X. "
        "Case D applies 15 kN downward (global -Z) only at each of B1 through B5. Use the supplied "
        "material and area records and run first-order linear static analysis in OpenSees with self-weight "
        "disabled. Report signed ux and uz of all five loaded bottom nodes, signed N for every bottom-chord, "
        "top-chord and web member, and Fx/Fz reactions at both supports. N is positive in tension. "
        "Identify D, node/member IDs and units for every output."
    )
    emit(28, m, prompt, truss_outputs(m, loaded, ["B0", "B6"]), notes=[TRUSS_CHOICES_EN,
         "The complete slopes and web endpoints are retained from the read-only legacy truss-trapezoidal-static.json prompt; no roof-template topology is inferred."])


def make_029():
    coords = [("B0", 0, 0), ("B1", 6, 0), ("B2", 12, 0),
              ("T1", 3, 1.5), ("T2", 6, 3), ("T3", 9, 1.5)]
    endpoints = [("BC0", "B0", "B1"), ("BC1", "B1", "B2"),
                 ("TC0", "B0", "T1"), ("TC1", "T1", "T2"),
                 ("TC2", "T2", "T3"), ("TC3", "T3", "B2"),
                 ("W1", "T1", "B1"), ("W2", "T2", "B1"),
                 ("W3", "T3", "B1"), ("H", "T1", "T3")]
    m = truss_model(coords, endpoints, {"B0": "pin", "B2": "roller"})
    loaded = ["T1", "T2", "T3"]
    for nid in loaded:
        rm.load(m, id=f"D-{nid}", type="nodal", node=nid, fz=-20)
    prompt = (
        "建立附件所列6节点10杆的对称三角桁架，跨度12m、高3m，位于X-Z平面。下弦节点"
        "B0=(0,0,0)、B1=(6,0,0)、B2=(12,0,0)m，上弦节点T1=(3,0,1.5)、"
        "T2=(6,0,3)、T3=(9,0,1.5)m。下弦为B0-B1和B1-B2；屋面上弦为B0-T1、"
        "T1-T2、T2-T3、T3-B2；另有T1-B1、T2-B1、T3-B1三根腹杆以及T1-T3水平连杆H。"
        "H与T2-B1的几何交叉处不设连接节点，保留6节点10杆。B0铰支，B2为X自由、Z双向约束滚支；"
        "全部构件为仅承轴力的铰接杆，材料和统一面积按附件。D工况在T1、T2、T3各施加全局-Z方向20kN节点力。"
        "以OpenSees作一阶线弹性静力分析，自重关闭。输出T1/T2/T3的ux、uz，水平连杆H及其余全部杆的"
        "有符号轴力N（正拉负压），以及B0/B2的Fx、Fz支反力；按D工况标明位置、杆号和单位。"
    )
    emit(29, m, prompt, truss_outputs(m, loaded, ["B0", "B2"]), notes=[TRUSS_CHOICES_ZH,
         "节点及十根杆端点逐项读取只读旧题truss-triangle-static.json。H和中央竖杆交叉不相连，避免擅增第七节点。"])


def make_030():
    coords = [(f"{level}{i}", x, z) for i, x in enumerate([0, 2, 4, 6, 8, 10, 12])
              for level, z in [("B", 0), ("T", 2)]]
    endpoints = [(f"BC{i}", f"B{i}", f"B{i+1}") for i in range(6)]
    endpoints += [(f"TC{i}", f"T{i}", f"T{i+1}") for i in range(6)]
    endpoints += [(f"V{i}", f"B{i}", f"T{i}") for i in range(7)]
    endpoints += [("D0", "B0", "T1"), ("D1", "T1", "B2"), ("D2", "B2", "T3"),
                  ("D3", "T3", "B4"), ("D4", "B4", "T5"), ("D5", "T5", "B6")]
    m = truss_model(coords, endpoints, {"B0": "pin", "B6": "roller"})
    loaded = ["B1", "B2", "B3", "B4", "B5"]
    for nid in loaded:
        rm.load(m, id=f"D-{nid}", type="nodal", node=nid, fz=-8)
    web_members = [e["id"] for e in m["elements"] if e["id"].startswith(("D", "V"))]
    prompt = (
        "Build the attached 12 m parallel-chord Warren-type truss in the global X-Z plane with six 2 m "
        "panels and a constant 2 m height. B0 through B6 are at x=0,2,4,6,8,10,12 m and z=0; "
        "T0 through T6 are directly above them at z=2 m. Connect adjacent nodes along both chords, "
        "provide every vertical Bi-Ti including the two end verticals, and use exactly the alternating "
        "diagonals B0-T1, T1-B2, B2-T3, T3-B4, B4-T5, T5-B6. All 25 members are pin-jointed axial-only "
        "rods with the supplied steel material and common area. B0 is pinned; B6 is a bilateral vertical "
        "roller free in global X. Case D applies 8 kN downward in global -Z at each internal bottom node "
        "B1 through B5 only. Run first-order linear static analysis using OpenSees, with self-weight "
        "disabled. Report signed ux and uz at all five loaded bottom nodes, signed axial force N in all "
        "six diagonals and seven verticals, and Fx/Fz support reactions at B0 and B6. Positive N is tension. "
        "Label every result with its node/member ID, load case D and unit."
    )
    emit(30, m, prompt, truss_outputs(m, loaded, ["B0", "B6"], web_members), notes=[TRUSS_CHOICES_EN,
         "The exact alternating diagonal sequence and all panel-line verticals are retained from the read-only legacy truss-warren-en.json prompt."])


if __name__ == "__main__":
    for number in range(21, 31):
        globals()[f"make_{number:03d}"]()
