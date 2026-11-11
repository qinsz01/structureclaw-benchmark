"""Explicit source models for research-300 MM-031 through MM-040.

Geometry, connectivity, supports and loads follow the original task/model rows.
Only the unprovided material/section appendix and MM-035 K-member endpoint table
are author completions. These are input specifications, never numerical truth.
"""

import importlib.util
import math
from pathlib import Path


_spec = importlib.util.spec_from_file_location(
    "mm_a_31_40_primitives", Path(__file__).resolve().parents[1] / "representative-models.py"
)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)


def _model(section_count=1, spatial=False):
    m = _base.model("3d" if spatial else "2d")
    sizes = [0.10, 0.08, 0.09, 0.07]
    m["sections"] = [
        _base.section(f"A{i + 1}", sizes[i], sizes[i])
        for i in range(section_count)
    ]
    m["metadata"].update(
        authoringStatus="authored-candidate",
        trussNonparticipatingDofs="Rotations restrained at every node; global uy also restrained for XZ models.",
        sectionAppendixOrigin="Explicit new author completion; square solid sections, not engine defaults.",
    )
    return m


def _node(m, name, x, z, y=0.0, support=None):
    spatial = m["coordinate_system"]["dimension"] == "3d"
    r = [False, not spatial, False, True, True, True]
    if support == "pin":
        r[0] = r[2] = True
    elif support == "roller":
        r[2] = True
    elif support == "xyz":
        r[:3] = [True, True, True]
    return _base.node(m, name, x, z, y, restraint=r)


def _rod(m, name, start, end, section="A1"):
    return _base.elem(m, name, start, end, "truss", section)


def _force(m, node, fz):
    _base.load(m, type="nodal", node=node, fz=fz, id=f"D-{node}")


def _q(node_or_member, component, *, member=False, position=0.0, side="right"):
    location = {"kind": "member" if member else "node", "id": node_or_member}
    if member:
        location.update(positionM=position, side=side)
    return {
        "id": f"D-{node_or_member}-{component}",
        "selection": {"kind": "case", "id": "D"},
        "location": location,
        "component": component,
        "unit": "m" if component in ("ux", "uy", "uz") else "kN",
        "tolerance": {"absolute": 1e-8, "relative": 1e-6},
    }


def _n(m, member):
    # Truss force is constant; sample at the physical midpoint, away from joints.
    e = next(e for e in m["elements"] if e["id"] == member)
    nodes = {n["id"]: n for n in m["nodes"]}
    a, b = (nodes[i] for i in e["nodes"])
    length = math.sqrt(sum((a[k] - b[k]) ** 2 for k in ("x", "y", "z")))
    return _q(member, "N", member=True, position=length / 2)


def _out(description, *quantities, derived=None):
    return {
        "description": description,
        "quantities": list(quantities),
        "derived": derived or [],
        "kind": "derived" if derived else "numerical",
    }


def _descriptor(m, outputs, english=False, notes=(), drawing_notes=()):
    sizes = "; ".join(
        f'{s["id"]}: {s["shape"]["B"]:g} x {s["shape"]["H"]:g} mm, '
        f'A={s["properties"]["A"]:g} m^2'
        for s in m["sections"]
    )
    appendix = (
        "Author completion of unspecified appendix: M1 is isotropic steel with "
        "E=206000 MPa, nu=0.3, G=E/[2(1+nu)], rho=7850 kg/m^3. "
        "Explicit solid-square sections: " + sizes + ". "
        "A, Iy, Iz and J are supplied; only EA enters the truss stiffness. "
        "All rotational degrees of freedom are inactive and restrained; XZ models also restrain uy. "
        "These bookkeeping restraints do not add moment-resisting joints. "
        "First-order linear elasticity; self-weight, P-delta, rigid floors and offsets OFF."
        if english else
        "补齐源规格未定值的附录：M1为各向同性钢材，E=206000 MPa、nu=0.3、"
        "G=E/[2(1+nu)]、rho=7850 kg/m^3。显式实心方形截面：" + sizes + "。"
        "完整给出A、Iy、Iz、J，轴力单元仅使用EA。所有节点非作用转动自由度约束，"
        "XZ平面另约束uy；这些处理不引入刚接或抗弯刚度。"
        "一阶线弹性，自重、P-delta、刚性楼板与刚性偏移均关闭。"
    )
    return {
        "model": m,
        "outputs": outputs,
        "notes": [appendix, *notes],
        "drawingNotes": list(drawing_notes),
    }


def _parallel_nodes(m, xs, lower, upper, *, right_top=False):
    for i, x in enumerate(xs):
        _node(m, f"L{i}", x, lower[i], support="pin" if i == 0 else
              "roller" if i == len(xs) - 1 and not right_top else None)
        _node(m, f"U{i}", x, upper[i], support="roller" if right_top and i == len(xs) - 1 else None)


def _chords(m, count):
    for i in range(count - 1):
        _rod(m, f"LC{i}", f"L{i}", f"L{i + 1}")
        _rod(m, f"UC{i}", f"U{i}", f"U{i + 1}")


def build():
    cases = {}

    # MM-031: six panels, double diagonals crossing without a joint.
    m = _model(2)
    _parallel_nodes(m, range(0, 19, 3), [0] * 7, [3] * 7)
    _chords(m, 7)
    for i in range(7):
        _rod(m, f"V{i}", f"L{i}", f"U{i}", "A2")
    for i in range(6):
        _rod(m, f"DU{i}", f"L{i}", f"U{i + 1}", "A2")
        _rod(m, f"DD{i}", f"U{i}", f"L{i + 1}", "A2")
    for i in range(1, 6):
        _force(m, f"U{i}", -12)
    cases["MM-031"] = _descriptor(m, [
        _out("跨中上弦节点U3的全局Uz", _q("U3", "uz")),
        _out("第一格两根斜杆DU0、DD0的轴力（受拉为正）", _n(m, "DU0"), _n(m, "DD0")),
    ], drawing_notes=["每格X斜杆交叉处不连接；仅实心端点连接。", "弦杆LC、UC用A1；竖杆V、斜杆DU/DD用A2。"])

    # MM-032: offset ridge; complete numerical state is visible only after t2.
    m = _model()
    for i, x in enumerate(range(0, 16, 3)):
        _node(m, f"L{i}", x, 0, support="pin" if i == 0 else "roller" if i == 5 else None)
    for i, z in enumerate([1.25, 2.5, 5 / 3, 5 / 6], 1):
        _node(m, f"U{i}", 3 * i, z)
        _rod(m, f"V{i}", f"L{i}", f"U{i}")
        _force(m, f"U{i}", -10)
    for i in range(5):
        _rod(m, f"LC{i}", f"L{i}", f"L{i + 1}")
    roof = ["L0", "U1", "U2", "U3", "U4", "L5"]
    for i in range(5):
        _rod(m, f"UC{i}", roof[i], roof[i + 1])
    for i in range(1, 4):
        _rod(m, f"D{i}", f"L{i}", f"U{i + 1}")
    cases["MM-032"] = _descriptor(m, [
        _out("Global Uz at ridge U2 after the missing elevation is supplied", _q("U2", "uz")),
        _out("Axial force in left ridge web D1, connecting L1 to U2; tension positive", _n(m, "D1")),
    ], english=True, notes=[
        "The source's left ridge web is D1 (L1 to U2); UC1 is the roof chord and V2 is the central vertical.",
        "Turn 1 lacks only the ridge elevation H. U2's horizontal position is derivable from the bottom dimension chain and vertical alignment. "
        "All roof elevations, slopes, angles and dimensional member lengths must remain hidden until turn 2. "
        "Use a vertically distorted schematic marked 'Schematic; do not scale' so pixel ratios cannot recover H. "
        "Turn 2 supplies the ridge elevation and the complete upper-chord elevations in the delayed drawing only.",
    ], drawing_notes=["All rods use M1/A1. Solid dots identify joints.", "Roof chords are straight between labelled joints."])
    cases["MM-032"]["clarification"] = {
        "unresolvedFields": ["ridgeElevationM"],
        "expectedQuestions": ["What is the ridge elevation H above the bottom chord?"],
        "withheldNodeIds": ["U1", "U2", "U3", "U4"],
        "knownRidgeHorizontalNode": "U2",
        "supplementDrawingNotes": [
            "Ridge U2: H = 2.5 m above the bottom chord.",
            "U1: Z = 1.25 m; U2: Z = 2.5 m; U3: Z = 5/3 m; U4: Z = 5/6 m.",
        ],
    }

    # MM-033: stepped upper chord; every change of elevation is a real joint.
    m = _model()
    _parallel_nodes(m, range(0, 16, 3), [0] * 6, [2, 2, 3, 3, 2, 2])
    _chords(m, 6)
    for i in range(6):
        _rod(m, f"V{i}", f"L{i}", f"U{i}")
    for i in range(5):
        _rod(m, f"D{i}", f"L{i}", f"U{i + 1}")
    for i in range(1, 5):
        _force(m, f"L{i}", -10)
    cases["MM-033"] = _descriptor(m, [
        _out("x=6 m下弦节点L2的全局Uz", _q("L2", "uz")),
        _out("中间水平上弦UC2的轴力（受拉为正）", _n(m, "UC2")),
    ], drawing_notes=["上弦折点均为真实连接节点，不能跨越折点合并构件。", "中间水平上弦UC2连接U2与U3。"])

    # MM-034: two long webs terminate at the same ridge.
    m = _model()
    for i, x in enumerate(range(0, 17, 4)):
        _node(m, f"L{i}", x, 0, support="pin" if i == 0 else "roller" if i == 4 else None)
    for i, z in enumerate([2, 4, 2], 1):
        _node(m, f"U{i}", 4 * i, z)
        _rod(m, f"V{i}", f"L{i}", f"U{i}")
        _force(m, f"U{i}", -12)
    for i in range(4):
        _rod(m, f"LC{i}", f"L{i}", f"L{i + 1}")
    roof = ["L0", "U1", "U2", "U3", "L4"]
    for i in range(4):
        _rod(m, f"UC{i}", roof[i], roof[i + 1])
    _rod(m, "DL", "L1", "U2")
    _rod(m, "DR", "L3", "U2")
    cases["MM-034"] = _descriptor(m, [
        _out("Global Uz at ridge U2", _q("U2", "uz")),
        _out("Axial forces in the two long ridge webs DL and DR; tension positive", _n(m, "DL"), _n(m, "DR")),
    ], english=True, drawing_notes=["Long webs DL and DR connect only their labelled end joints.", "The three verticals terminate at the corresponding roof joints."])

    # MM-035: source intentionally delegates the K endpoint table to authoring.
    # All seven vertical midpoints are joints, including the two end posts.
    # Complementary end-panel K pairs stabilize the end midpoint translations.
    m = _model(2)
    _parallel_nodes(m, range(0, 19, 3), [0] * 7, [3] * 7, right_top=True)
    _chords(m, 7)
    for i in range(7):
        _node(m, f"M{i}", 3 * i, 1.5)
        _rod(m, f"VL{i}", f"L{i}", f"M{i}", "A2")
        _rod(m, f"VU{i}", f"M{i}", f"U{i}", "A2")
    k_endpoints = []
    for panel in range(6):
        outer = panel if panel < 3 else panel + 1
        middle = panel + 1 if panel < 3 else panel
        for level in ("L", "U"):
            name, start, end = f"K{panel}{level}", f"{level}{outer}", f"M{middle}"
            _rod(m, name, start, end, "A2")
            k_endpoints.append(f"{name}: {start}—{end}")
    for outer, middle in ((1, 0), (5, 6)):
        for level in ("L", "U"):
            name, start, end = f"KE{middle}{level}", f"{level}{outer}", f"M{middle}"
            _rod(m, name, start, end, "A2")
            k_endpoints.append(f"{name}: {start}—{end}")
    for i in (1, 2, 3):
        _force(m, f"U{i}", -12)
    endpoint_note = "补齐源规格未给出的K形端点表（各杆仅连接所列端点）：" + "；".join(k_endpoints) + "。"
    cases["MM-035"] = _descriptor(m, [
        _out("x=9 m上弦节点U3的全局Uz", _q("U3", "uz")),
        _out("右端上弦支座U6的全局竖向反力Fz", _q("U6", "Fz")),
    ], notes=[
        "源规格未提供K腹杆逐杆表，本附录冻结为左右镜像K布置，两个端节间采用双K补齐。"
        "全部七根竖杆均在中点M0至M6分段连接；保留六节间原镜像K杆，"
        "另以M0连接L1/U1、M6连接L5/U5，保证两个端竖杆中点也参与稳定传力。"
        "中间M3汇交两侧K杆。"
        "此为明确的拓扑补齐，须保留在公开工程图的逐杆表与详图中。",
        endpoint_note,
    ], drawing_notes=[
        "左下L0铰支；右上U6竖向滚支；其余节点无支座。",
        "全部竖杆中点M0至M6为连接节点；两个端节间为双K。",
        "弦杆LC/UC用A1；竖杆VL/VU与K杆用A2。",
    ])
    cases["MM-035"]["memberEndpointTable"] = [
        {"id": e["id"], "start": e["nodes"][0], "end": e["nodes"][1], "section": e["section"]}
        for e in m["elements"]
    ]

    # MM-036: every crossing is an actual four-member joint.
    m = _model(2)
    _parallel_nodes(m, range(0, 13, 3), [0] * 5, [2.5] * 5)
    _chords(m, 5)
    for i in range(5):
        _rod(m, f"V{i}", f"L{i}", f"U{i}", "A2")
    for i in range(4):
        _node(m, f"C{i}", 3 * i + 1.5, 1.25)
        for corner, end in (("BL", f"L{i}"), ("TL", f"U{i}"),
                            ("BR", f"L{i + 1}"), ("TR", f"U{i + 1}")):
            _rod(m, f"X{i}{corner}", end, f"C{i}", "A2")
    for i in range(1, 4):
        _force(m, f"U{i}", -10)
    balance = [
        {"id": "D-C0-diagonal-up-balance", "operation": "difference",
         "operands": ["D-X0BL-N", "D-X0TR-N"], "unit": "kN",
         "description": "Opposite collinear rods X0BL and X0TR must have equal signed axial force at C0."},
        {"id": "D-C0-diagonal-down-balance", "operation": "difference",
         "operands": ["D-X0TL-N", "D-X0BR-N"], "unit": "kN",
         "description": "Opposite collinear rods X0TL and X0BR must have equal signed axial force at C0."},
    ]
    cases["MM-036"] = _descriptor(m, [
        _out("Global Uz at upper midspan joint U2", _q("U2", "uz")),
        _out("Signed axial forces in all four rods meeting first-panel centre C0; tension positive",
             *[_n(m, f"X0{corner}") for corner in ("BL", "TL", "BR", "TR")]),
        _out("Force equilibrium at C0 along its two independent crossing-diagonal directions", derived=balance),
    ], english=True, notes=[
        "The first-panel centre has no applied force. Because its two diagonals are independent and each "
        "opposite rod pair is collinear, the two signed axial-force differences are exactly equivalent "
        "to the two components of joint force equilibrium. Report all four rod forces and both residuals.",
    ], drawing_notes=["Solid centre dots C0-C3 are connected joints; each X contains four rods.",
                      "Chord rods LC/UC use A1; vertical and X rods use A2."])

    # MM-037: staggered upper joints, unequal bottom panels, no vertical rods.
    m = _model()
    for i, x in enumerate([0, 2, 5, 9, 12]):
        _node(m, f"L{i}", x, 0, support="pin" if i == 0 else "roller" if i == 4 else None)
    for i, x in enumerate([1, 3.5, 7, 10.5]):
        _node(m, f"U{i}", x, 2.2)
        _rod(m, f"DL{i}", f"L{i}", f"U{i}")
        _rod(m, f"DR{i}", f"U{i}", f"L{i + 1}")
        _force(m, f"U{i}", -[8, 12, 10, 6][i])
    for i in range(4):
        _rod(m, f"LC{i}", f"L{i}", f"L{i + 1}")
    for i in range(3):
        _rod(m, f"UC{i}", f"U{i}", f"U{i + 1}")
    cases["MM-037"] = _descriptor(m, [
        _out("x=7 m上弦节点U2的全局Uz", _q("U2", "uz")),
        _out("最右斜杆DR3的轴力（受拉为正）", _n(m, "DR3")),
    ], drawing_notes=["上节点错列；本桁架无竖杆。", "荷载按节点标签匹配附表，不按表格行序推定。"])

    # MM-038: both chords incline; global vertical loads stay vertical.
    m = _model()
    lower = [0, 0.3, 0.6, 0.9, 1.2, 1.5]
    _parallel_nodes(m, range(0, 16, 3), lower, [z + 2 for z in lower])
    _chords(m, 6)
    for i in range(6):
        _rod(m, f"V{i}", f"L{i}", f"U{i}")
    for i in range(5):
        _rod(m, f"D{i}", f"L{i}", f"U{i + 1}")
    for i, force in ((2, -20), (3, -15), (4, -10)):
        _force(m, f"U{i}", force)
    cases["MM-038"] = _descriptor(m, [
        _out("Global Uz at the rightmost loaded upper joint U4", _q("U4", "uz")),
        _out("Global horizontal reaction Fx at left support L0", _q("L0", "Fx")),
    ], english=True, drawing_notes=["Both chords incline in global XZ; retain the support elevation difference.",
                                   "All arrows act in global -Z; the right roller restrains global uz."])

    # MM-039: three chords, two separate web layers, four property groups.
    m = _model(4)
    for row, z in (("L", 0), ("M", 1.5), ("U", 3)):
        for i in range(6):
            support = "pin" if row == "L" and i == 0 else "roller" if row == "L" and i == 5 else None
            _node(m, f"{row}{i}", 4 * i, z, support=support)
        for i in range(5):
            _rod(m, f"{row}C{i}", f"{row}{i}", f"{row}{i + 1}", {"U": "A1", "M": "A2", "L": "A3"}[row])
    for layer, rows in enumerate((("L", "M"), ("M", "U"))):
        lower_row, upper_row = rows
        for i in range(6):
            _rod(m, f"V{layer}-{i}", f"{lower_row}{i}", f"{upper_row}{i}", "A4")
        for i in range(5):
            _rod(m, f"D{layer}-{i}", f"{lower_row}{i}", f"{upper_row}{i + 1}", "A4")
    for i in range(1, 5):
        _force(m, f"U{i}", -12)
    cases["MM-039"] = _descriptor(m, [
        _out("顶排x=8 m节点U2的全局Uz", _q("U2", "uz")),
        _out("中间弦首杆MC0的轴力（受拉为正）", _n(m, "MC0")),
    ], drawing_notes=["上弦UC=A1；中弦MC=A2；下弦LC=A3；两层腹杆V/D=A4。", "三排节点均为真实传力层；仅最下排两端设支座。"])

    # MM-040: five-node square pyramid, eight rods, four fixed translations.
    m = _model(spatial=True)
    for i, (x, y) in enumerate(((0, 0), (4, 0), (4, 4), (0, 4))):
        _node(m, f"B{i}", x, 0, y, support="xyz")
    _node(m, "T", 2, 3, 2)
    for i in range(4):
        _rod(m, f"E{i}", f"B{i}", f"B{(i + 1) % 4}")
        _rod(m, f"S{i}", f"B{i}", "T")
    _force(m, "T", -30)
    cases["MM-040"] = _descriptor(m, [
        _out("Global Uz at apex T", _q("T", "uz")),
        _out("Axial forces in adjacent inclined rods S0 and S1; tension positive", _n(m, "S0"), _n(m, "S1")),
    ], english=True, drawing_notes=["All four base joints restrain global ux, uy and uz; apex translations are free.",
                                   "There are four base-edge rods and four inclined rods; no base diagonals.",
                                   "Plan uses X-Y; front elevation uses X-Z; side elevation uses Y-Z."])

    return cases
