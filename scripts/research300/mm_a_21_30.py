"""Explicit MM-021..030 authoring inputs, read from the research-300 source rows.

This module contains no numerical reference answers and does not call a solver.
Source task/model tables, rather than representative-18 cases, define the geometry,
connectivity, supports, load positions, and requested response locations below.
"""

import importlib.util
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "mm_a_21_30_primitives", Path(__file__).resolve().parents[1] / "representative-models.py"
)
_P = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_P)

_FREE = [False, True, False, True, False, True]
_PIN = [True, True, True, True, False, True]
_ROLLER = [False, True, True, True, False, True]
_FIXED = [True] * 6
_TRUSS_FREE = [False, True, False, True, True, True]
_TRUSS_PIN = [True] * 6
_TRUSS_ROLLER = [False, True, True, True, True, True]


def _model(*section_ids):
    m = _P.model()
    m["sections"] = [s for s in m["sections"] if s["id"] in section_ids]
    return m


def _beam(xs, supports, sections=None):
    sections = sections or ["B1"] * (len(xs) - 1)
    m = _model(*set(sections))
    for i, x in enumerate(xs):
        _P.node(m, f"n{i}", x, 0, restraint=list(supports.get(i, _FREE)))
    for i, section in enumerate(sections, 1):
        _P.elem(m, f"b{i}", f"n{i - 1}", f"n{i}", sec=section)
    return m


def _udl(m, wz, case="D", members=None):
    for e in m["elements"]:
        if members is None or e["id"] in members:
            _P.load(m, case, type="distributed", element=e["id"], wz=wz)


def _selection(id="D", kind="case"):
    return {"kind": kind, "id": id}


def _quantity(id, location, component, selection=None):
    selection = dict(selection or _selection())
    unit = "m" if component.startswith("u") else "rad" if component.startswith("r") else "kN.m" if component in ("T", "M2", "M3", "Mx", "My", "Mz") else "kN"
    return {
        "id": f'{selection["kind"]}-{selection["id"]}:{id}',
        "selection": selection,
        "location": location,
        "component": component,
        "unit": unit,
        "tolerance": {"absolute": 1e-8, "relative": 1e-6},
    }


def _node(id, component, selection=None):
    return _quantity(f"{id}:{component}", {"kind": "node", "id": id}, component, selection)


def _member(id, position, component, side="right", selection=None):
    return _quantity(
        f"{id}:{component}@{position:g}:{side}",
        {"kind": "member", "id": id, "positionM": position, "side": side},
        component,
        selection,
    )


def _out(description, *quantities, derived=None):
    return {
        "description": description,
        "quantities": list(quantities),
        "derived": derived or [],
        "kind": "derived" if derived else "numerical",
    }


def _appendix(m, english=False, truss=False):
    props = {
        "B1": "B1: 0.30 m × 0.60 m",
        "B2": "B2: 0.30 m × 0.70 m",
        "A1": "A1: 0.10 m × 0.10 m",
    }
    sizes = "; ".join(props[s["id"]] for s in m["sections"])
    if english:
        notes = [
            "Author completion of the unspecified property appendix: M1 is linear elastic steel, E=206000 MPa, nu=0.30, G=79230.76923076923 MPa, density=7850 kg/m³.",
            f"Author completion: solid rectangular sections ({sizes}); A, Iy, Iz and the frozen Saint-Venant J are explicitly supplied in the property table.",
            "Units are m, kN, MPa and rad. First-order linear elastic analysis; self-weight, P-delta, rigid floors, rigid offsets and construction staging are OFF.",
        ]
        if truss:
            notes.append("All members carry axial force only. Global uy and all rotations are inactive and restrained at every node; these inactive DOFs do not create physical moment supports.")
        else:
            notes.append("Planar XZ model: global uy, rx and rz are restrained. Local 1 follows each member's first-to-second node direction, local 2 is global +Y, and local 3 completes the right-handed triad. Vertical shear is V3 and in-plane bending is M2.")
        return notes
    notes = [
        "编题补齐原计划未定的属性附录：M1采用线弹性钢材，E=206000 MPa，nu=0.30，G=79230.76923076923 MPa，密度=7850 kg/m³。",
        f"编题补齐：实心矩形截面（{sizes}）；完整属性表明确列出A、Iy、Iz及冻结的圣维南扭转常数J。",
        "单位为m、kN、MPa及rad；一阶线弹性分析，自重、P-delta、刚性楼板、刚性偏置及施工阶段均关闭。",
    ]
    if truss:
        notes.append("所有杆件仅承轴力。各节点的uy及三个转动为非作用自由度并加以约束；这些约束不表示物理弯矩支承。")
    else:
        notes.append("平面XZ模型约束uy、rx、rz。局部1轴由构件首节点指向末节点，局部2轴为全局+Y，局部3轴按右手系确定；竖向剪力取V3，平面弯矩取M2。")
    return notes


def _descriptor(m, outputs, english=False, truss=False, notes=None, drawing_notes=None):
    return {
        "model": m,
        "outputs": outputs,
        "notes": _appendix(m, english, truss) + (notes or []),
        "drawingNotes": drawing_notes or [],
    }


def _truss_nodes(m, rows):
    for id, x, z, support in rows:
        _P.node(m, id, x, z, restraint=list(support or _TRUSS_FREE))


def _truss_member(m, id, a, b):
    _P.elem(m, id, a, b, kind="truss", sec="A1")


def build():
    out = {}

    # MM-021: t1 conflict concerns only b3's section. This is the t2 confirmed model.
    m = _beam([0, 3, 6, 12], {0: _FIXED, 2: _ROLLER, 3: _ROLLER}, ["B1", "B1", "B2"])
    _udl(m, -10)
    _P.load(m, type="nodal", node="n1", fz=-22)
    qleft = _member("b1", 3, "V3", "left")
    qright = _member("b2", 0, "V3", "right")
    out["MM-021"] = _descriptor(m, [
        _out("确认后首跨x=3 m连通节点的竖向位移Uz", _node("n1", "uz")),
        _out("确认后首跨x=3 m集中力点左、右侧剪力V3", qleft, qright),
        _out("确认后左端梁截面的弯矩M2", _member("b1", 0, "M2")),
        _out("集中力点剪力跳变，取右侧减左侧", derived=[{
            "id": "case-D:shear-jump-at-n1",
            "operation": "difference",
            "operands": [qright["id"], qleft["id"]],
            "unit": "kN",
            "description": "首跨集中力点右侧V3减左侧V3，保留符号。",
        }]),
    ], notes=[
        "首轮存在截面关联冲突，不提供可执行初始模型；只有第二轮确认后才使用本模型。B1、B2属性在首轮均完整可用。",
    ], drawing_notes=[
        "首跨：B1；第二跨图签：B2。",
        "x=3 m为与左右梁段连通的节点，22 kN竖向集中力在首轮已给出。",
        "中支座保持梁连续，转角自由；无内铰。",
    ])

    # MM-022: two free overhang ends, with three supports at the source locations.
    m = _beam([-2, 0, 5, 10, 12], {1: _PIN, 2: _ROLLER, 3: _ROLLER})
    _udl(m, -8)
    _P.load(m, type="nodal", node="n0", fz=-6)
    _P.load(m, type="nodal", node="n4", fz=-10)
    out["MM-022"] = _descriptor(m, [
        _out("Vertical displacement Uz of the left free end at x=-2 m", _node("n0", "uz")),
        _out("Vertical displacement Uz of the right free end at x=12 m", _node("n4", "uz")),
        _out("Vertical support reaction Fz at x=5 m", _node("n2", "Fz")),
    ], english=True, drawing_notes=[
        "Both extreme ends are free; the left overhang has a negative X coordinate.",
        "Continuous beam through the three supports; no internal hinges.",
    ])

    # MM-023: the 30 kN force is at a supported node, not inside an adjacent span.
    m = _beam([0, 4, 7, 10], {0: _PIN, 1: _ROLLER, 3: _FIXED})
    _P.load(m, type="nodal", node="n1", fz=-30)
    _P.load(m, type="nodal", node="n2", fz=-20)
    out["MM-023"] = _descriptor(m, [
        _out("长跨中点x=7 m的竖向位移Uz", _node("n2", "uz")),
        _out("中支座x=4 m的竖向反力Fz，包含该处外加节点力", _node("n1", "Fz")),
        _out("右固定端梁截面的弯矩M2", _member("b3", 3, "M2", "left")),
    ], drawing_notes=[
        "30 kN作用于中支座节点；20 kN作用于长跨中点连通节点。",
        "右端固定；中支座转角自由且梁连续。",
    ])

    # MM-024: actual nodes at both requested midpoints; disconnected wind zones.
    m = _beam([0, 5, 7, 9, 15, 16.5, 18], {0: _PIN, 1: _ROLLER, 3: _ROLLER, 4: _ROLLER, 6: _ROLLER})
    _udl(m, -8)
    _udl(m, 6, "W", {"b2", "b3", "b5", "b6"})
    m["load_combinations"] = [{"id": "D", "factors": {"D": 1}}, {"id": "D+W", "factors": {"D": 1, "W": 1}}]
    outputs = []
    for combo in ("D", "D+W"):
        selection = _selection(combo, "combination")
        outputs.extend([
            _out(f"{combo}: midpoint Uz of span 2 at x=7 m", _node("n2", "uz", selection)),
            _out(f"{combo}: midpoint Uz of span 4 at x=16.5 m", _node("n5", "uz", selection)),
            _out(f"{combo}: signed vertical reaction Fz at the final support", _node("n6", "Fz", selection)),
        ])
    out["MM-024"] = _descriptor(m, outputs, english=True, drawing_notes=[
        "Spans are numbered 1 to 4 from left to right.",
        "Wind zones are spans 2 and 4; load values and combination factors are in the linked load table.",
        "Report D and D+W separately, including the sign of the final support reaction.",
    ])

    # MM-025: both ends fixed, continuous middle roller with a global +Y moment.
    m = _beam([0, 5, 10], {0: _FIXED, 1: _ROLLER, 2: _FIXED})
    _udl(m, -6)
    _P.load(m, type="nodal", node="n1", my=20)
    out["MM-025"] = _descriptor(m, [
        _out("中支点绕全局Y轴的转角Ry", _node("n1", "ry")),
        _out("左固定端梁截面的弯矩M2", _member("b1", 0, "M2")),
        _out("右固定端梁截面的弯矩M2", _member("b2", 5, "M2", "left")),
    ], drawing_notes=[
        "中支点为竖向滚支，转角自由且无内铰。",
        "中支点外加力矩绕全局+Y轴，按右手定则取正。",
    ])

    # MM-026: third span observation node is x=12.5; support 4 is x=15.
    m = _beam([0, 4, 10, 12.5, 15, 19, 22], {0: _PIN, 1: _ROLLER, 2: _ROLLER, 4: _ROLLER, 5: _ROLLER, 6: _ROLLER}, ["B1", "B2", "B2", "B2", "B2", "B1"])
    _udl(m, -7)
    _udl(m, -10, "L", {"b2", "b5"})
    m["load_combinations"] = [{"id": "D", "factors": {"D": 1}}, {"id": "D+L", "factors": {"D": 1, "L": 1}}]
    outputs = []
    for combo in ("D", "D+L"):
        selection = _selection(combo, "combination")
        outputs.extend([
            _out(f"{combo}: vertical displacement Uz at the midpoint of span 3", _node("n3", "uz", selection)),
            _out(f"{combo}: beam bending moment M2 at support 4, approached from the right", _member("b5", 0, "M2", "right", selection)),
        ])
    out["MM-026"] = _descriptor(m, outputs, english=True, notes=[
        "The source's fourth support is numbered from the leftmost support as support 1; it is not the fourth interior support.",
    ], drawing_notes=[
        "Spans 1 to 5 and supports 1 to 6 are numbered from left to right.",
        "Section B2 applies to spans 2, 3 and 4; section B1 applies to spans 1 and 5.",
        "Source DXF coordinates are in metres; drawing X maps to global X and drawing Y maps to global Z.",
    ])

    # MM-027: six-panel Pratt, diagonals descending toward the midspan.
    m = _model("A1")
    for i in range(7):
        _truss_nodes(m, [
            (f"l{i}", 2.5 * i, 0, _TRUSS_PIN if i == 0 else _TRUSS_ROLLER if i == 6 else None),
            (f"u{i}", 2.5 * i, 2.5, None),
        ])
        _truss_member(m, f"v{i}", f"l{i}", f"u{i}")
    for i in range(6):
        _truss_member(m, f"bc{i + 1}", f"l{i}", f"l{i + 1}")
        _truss_member(m, f"tc{i + 1}", f"u{i}", f"u{i + 1}")
        _truss_member(m, f"d{i + 1}", f"u{i}" if i < 3 else f"l{i}", f"l{i + 1}" if i < 3 else f"u{i + 1}")
    for i in range(1, 6):
        _P.load(m, type="nodal", node=f"u{i}", fz=-10)
    out["MM-027"] = _descriptor(m, [
        _out("跨中上弦节点u3的竖向位移Uz", _node("u3", "uz")),
        _out("左端斜腹杆d1的轴力N，拉力为正", _member("d1", 0, "N")),
        _out("左端竖腹杆v0的轴力N，拉力为正", _member("v0", 0, "N")),
    ], truss=True, notes=[
        "原计划“左端腹杆”未区分端竖杆和首根斜腹杆；本题明确同时报告图中v0、d1，避免静默遗漏其中一种解释。",
        "斜杆按Pratt型向跨中下倾布置，并在图中逐杆画出实际连接。",
    ], drawing_notes=[
        "各杆均为两端铰接轴力杆。",
        "六根斜杆向跨中下倾；左端腹杆输出包括斜杆d1及竖杆v0。",
    ])

    # MM-028: asymmetric upper chord and the source's lower-left to upper-right webs.
    m = _model("A1")
    heights = [1.6, 2, 2.4, 2.8, 3, 2.4, 1.6]
    for i, z in enumerate(heights):
        _truss_nodes(m, [
            (f"l{i}", 3 * i, 0, _TRUSS_PIN if i == 0 else _TRUSS_ROLLER if i == 6 else None),
            (f"u{i}", 3 * i, z, None),
        ])
        _truss_member(m, f"v{i}", f"l{i}", f"u{i}")
    for i in range(6):
        _truss_member(m, f"bc{i + 1}", f"l{i}", f"l{i + 1}")
        _truss_member(m, f"tc{i + 1}", f"u{i}", f"u{i + 1}")
        _truss_member(m, f"d{i + 1}", f"l{i}", f"u{i + 1}")
    for i in (3, 4, 5):
        _P.load(m, type="nodal", node=f"l{i}", fz=-15)
    out["MM-028"] = _descriptor(m, [
        _out("Vertical displacement Uz of the upper-chord node at x=12 m", _node("u4", "uz")),
        _out("Axial force N of the rightmost diagonal d6, positive in tension", _member("d6", 0, "N")),
    ], english=True, truss=True, drawing_notes=[
        "Every member is pin connected and carries axial force only.",
        "Each panel diagonal runs from its lower-left node to its upper-right node.",
        "The three point loads act on lower-chord nodes.",
    ])

    # MM-029: exactly seven nodes and eleven bars; no inferred extra roof web.
    m = _model("A1")
    _truss_nodes(m, [
        ("l0", 0, 0, _TRUSS_PIN), ("l1", 4, 0, None),
        ("l2", 8, 0, None), ("l3", 12, 0, _TRUSS_ROLLER),
        ("u1", 4, 2, None), ("ridge", 6, 3, None), ("u2", 8, 2, None),
    ])
    for id, a, b in [
        ("bc1", "l0", "l1"), ("bc2", "l1", "l2"), ("bc3", "l2", "l3"),
        ("tc1", "l0", "u1"), ("tc2", "u1", "ridge"),
        ("tc3", "ridge", "u2"), ("tc4", "u2", "l3"),
        ("v1", "l1", "u1"), ("v2", "l2", "u2"),
        ("d1", "l1", "ridge"), ("d2", "l2", "ridge"),
    ]:
        _truss_member(m, id, a, b)
    for id in ("u1", "ridge", "u2"):
        _P.load(m, type="nodal", node=id, fz=-20)
    out["MM-029"] = _descriptor(m, [
        _out("屋脊节点ridge的竖向位移Uz", _node("ridge", "uz")),
        _out("左侧屋脊腹杆d1的轴力N，拉力为正", _member("d1", 0, "N")),
    ], truss=True, drawing_notes=[
        "七个节点、十一根轴力杆，节点连接以逐杆图示为准。",
        "d1为左下部节点至屋脊的腹杆；各杆端铰接。",
    ])

    # MM-030: thirteen staggered nodes and twenty-three bars, with no verticals.
    m = _model("A1")
    for i in range(7):
        _truss_nodes(m, [(f"l{i}", 2 * i, 0, _TRUSS_PIN if i == 0 else _TRUSS_ROLLER if i == 6 else None)])
    for i in range(6):
        _truss_nodes(m, [(f"u{i}", 2 * i + 1, 2, None)])
        _truss_member(m, f"bc{i + 1}", f"l{i}", f"l{i + 1}")
        _truss_member(m, f"d{i + 1}L", f"l{i}", f"u{i}")
        _truss_member(m, f"d{i + 1}R", f"u{i}", f"l{i + 1}")
        if i < 5:
            _truss_member(m, f"tc{i + 1}", f"u{i}", f"u{i + 1}")
        _P.load(m, type="nodal", node=f"u{i}", fz=-8)
    out["MM-030"] = _descriptor(m, [
        _out("Vertical displacement Uz of the upper-chord node at x=5 m", _node("u2", "uz")),
        _out("Axial force N of the leftmost diagonal d1L, positive in tension", _member("d1L", 0, "N")),
    ], english=True, truss=True, drawing_notes=[
        "Upper and lower nodes are staggered by half a panel; there are no vertical members.",
        "All six upper-chord nodes carry the load indicated by their linked load label.",
        "Source DXF coordinates are in metres; drawing X maps to global X and drawing Y maps to global Z.",
    ])

    return out
