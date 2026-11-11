"""Author STD-031..040 inputs and requests; never author numerical truth.

The frozen legacy scenarios and DXF are read only.  The independent rigidity
check below uses translational compatibility and does not call a solver.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def square_section(name, area):
    """Complete an axial-only section record without changing its frozen area."""
    side_mm = 1000 * math.sqrt(area)
    return {"id": name, "name": name, "type": "rectangular",
            "shape": {"kind": "rectangular", "B": side_mm, "H": side_mm},
            "properties": {"A": area, "Iy": area ** 2 / 12, "Iz": area ** 2 / 12,
                           "J": 0.14083333333333334 * area ** 2}}


def truss(dimension="2d", legacy=False, grouped=False):
    e = 205000 if legacy else 206000
    areas = [("A1", 0.012), ("A2", 0.010), ("A3", 0.006)] if grouped else [("T1", 0.01)]
    return {
        "schema_version": "2.2.0",
        "unit_system": "SI",
        "coordinate_system": {
            "dimension": dimension, "plane": "xz" if dimension == "2d" else None,
            "semantics": "global-z-up", "version": 1,
            "dof_order": ["ux", "uy", "uz", "rx", "ry", "rz"],
        },
        "nodes": [], "elements": [],
        "materials": [{"id": "M1", "name": "steel", "type": "steel", "E": e,
                       "G": e / 2.6, "nu": 0.3, "rho": 7850}],
        "sections": [square_section(sid, area) for sid, area in areas],
        "load_cases": [{"id": "LC1", "type": "dead", "loads": []}],
        "load_combinations": [],
        "analysis_control": {"self_weight": False, "rigid_floor": False, "p_delta": False,
                             "rigid_offsets": False, "construction_stage": False},
        "metadata": {"elementReferenceVectors": {}} if dimension == "3d" else {},
    }


def node(m, name, x, z, y=0, fix=()):
    # Rotations are inactive truss bookkeeping DOFs; they are not rigid joints.
    restraints = [False, m["coordinate_system"]["dimension"] == "2d", False, True, True, True]
    for axis in fix:
        restraints["xyz".index(axis)] = True
    m["nodes"].append({"id": name, "x": x, "y": y, "z": z, "restraints": restraints})


def bar(m, name, a, b, section="T1"):
    m["elements"].append({"id": name, "type": "truss", "nodes": [a, b],
                          "material": "M1", "section": section})
    if m["coordinate_system"]["dimension"] == "3d":
        nodes = {n["id"]: n for n in m["nodes"]}
        u, v = nodes[a], nodes[b]
        reference = [1, 0, 0] if abs(u["x"] - v["x"]) + abs(u["y"] - v["y"]) < 1e-12 else [0, 0, 1]
        m["metadata"]["elementReferenceVectors"][name] = reference


def load(m, name, downward):
    m["load_cases"][0]["loads"].append({"id": "P-" + name, "type": "nodal", "node": name,
                                       "reference_frame": "global", "fz": -downward})


def grid(m, xs, zs):
    for i, (x, z) in enumerate(zip(xs, zs)):
        node(m, f"B{i}", x, 0, fix="xz" if i == 0 else "z" if i == len(xs) - 1 else "")
        node(m, f"T{i}", x, z)


def chords(m, panels, grouped=False):
    for i in range(panels):
        bar(m, f"BC{i + 1}", f"B{i}", f"B{i + 1}", "A2" if grouped else "T1")
        bar(m, f"TC{i + 1}", f"T{i}", f"T{i + 1}", "A1" if grouped else "T1")


def verticals(m, panels, section="T1"):
    for i in range(panels + 1):
        bar(m, f"V{i}", f"B{i}", f"T{i}", section)


def diagonals(m, endpoints, section="T1"):
    for i, (a, b) in enumerate(endpoints, 1):
        bar(m, f"D{i}", a, b, section)


def records():
    """Complete case-specific topology, loads and output selections."""
    out = []

    m = truss(legacy=True)
    grid(m, [0, 3, 6, 9, 12, 15, 18], [3] * 7)
    chords(m, 6); verticals(m, 6)
    diagonals(m, [("B0", "T1"), ("T1", "B2"), ("B2", "T3"),
                  ("T3", "B4"), ("B4", "T5"), ("T5", "B6")])
    for i in range(1, 6):
        load(m, f"T{i}", 12)
    out.append((31, m, [f"T{i}" for i in range(1, 6)], None,
        "建立跨度18 m、高3 m、六个3 m节间的平行弦屋架，按附件逐项输入。所有节点都在XZ平面，"
        "左下B0为铰支，右下B6为X向自由滚支。每个分格点保留竖杆，包括两端V0、V6；"
        "六根斜杆按D1至D6端点交替连接。只在T1至T5各施加全局向下12 kN。"
        "采用仅传轴力、可受拉压的线弹性杆，使用OpenSees完成一阶静力分析，自重关闭。"
        "分别输出五个受载上弦节点的ux、uz，全部上下弦、竖杆及斜杆轴力N，B0与B6的Fx、Fz支反力。"
        "结果采用LC1工况，位移用m、轴力与反力用kN；N正值为受拉。",
        ["几何、连接、材料E=205000 MPa及A=0.01 m²保留自旧题truss-roof-en。",
         "按新契约明确关闭自重；全部数量请求对应LC1，不将旧题结果用作真值。"], []))

    m = truss(legacy=True)
    for i, x in enumerate([0, 3, 6, 9, 12, 15]):
        node(m, f"B{i}", x, 0, fix="xz" if i == 0 else "z" if i == 5 else "")
    for name, x, z in [("T1", 3, 1), ("T2", 6, 2), ("R", 7.5, 2.5), ("T3", 9, 2), ("T4", 12, 1)]:
        node(m, name, x, z)
        load(m, name, 10)
    for i in range(5):
        bar(m, f"BC{i + 1}", f"B{i}", f"B{i + 1}")
    roof = ["B0", "T1", "T2", "R", "T3", "T4", "B5"]
    for i in range(6):
        bar(m, f"TC{i + 1}", roof[i], roof[i + 1])
    for i in range(1, 5):
        bar(m, f"V{i}", f"B{i}", f"T{i}")
    diagonals(m, [("B1", "T2"), ("B2", "R"), ("B3", "R"), ("B4", "T3")])
    out.append((32, m, ["T1", "T2", "R", "T3", "T4"], ["TC3", "TC4", "D2", "D3"],
        "Build the 15 m symmetric triangular roof truss using the complete attached tables. The bottom chord has five "
        "3 m panels; the ridge R=(7.5,0,2.5) m is independent of that grid. The five upper nodes have (x,z) coordinates "
        "(3,1), (6,2), (7.5,2.5), (9,2), and (12,1) m. Retain the four verticals at x=3,6,9,12 m and exactly these "
        "diagonals: B1-T2, B2-R, B3-R, B4-T3. The roof chord follows B0-T1-T2-R-T3-T4-B5. "
        "B0 is pinned; B5 is a roller free in global X. Apply 10 kN downward at each of the five upper nodes. "
        "Use axial-only elastic truss members in tension and compression, and run first-order static analysis in OpenSees "
        "with self-weight off. For LC1 report ux and uz at all five loaded upper nodes, axial force N in all four members "
        "meeting the ridge (TC3, TC4, D2, D3), and Fx and Fz at both supports. Use m for displacement and kN for forces, "
        "with tension positive.",
        ["The 11-node, 19-bar topology, E=205000 MPa and A=0.01 m² preserve the immutable std-truss-tri-en source.",
         "The new corpus explicitly disables self-weight and requests fresh LC1 results; no legacy answer is reused."], []))

    m = truss(legacy=True)
    grid(m, [0, 3, 6, 9, 12, 15], [2.5] * 6)
    chords(m, 5); verticals(m, 5)
    diagonals(m, [("B1", "T0"), ("B2", "T1"), ("B3", "T2"), ("B4", "T3"), ("B5", "T4")])
    for i in range(1, 5):
        load(m, f"B{i}", 10)
    out.append((33, m, [f"B{i}" for i in range(1, 5)], None,
        "按附件文字节点表和杆件端点表建立跨度15 m、高2.5 m、五个3 m节间的平行弦三角腹杆桁架。"
        "该表从原DXF的STRUCT线转录，共12节点21根杆；外轮廓为平行弦，不能据‘三角腹杆’改变外形。"
        "B0铰支，B5为X向自由滚支；只在内部下弦B1、B2、B3、B4各施加向下10 kN。"
        "用OpenSees进行仅轴力弹性杆的一阶静力分析，杆件可受拉压，自重关闭。输出LC1下四个受载"
        "下弦节点的ux、uz、全部21根杆轴力N以及两支座Fx、Fz。位移用m，力用kN，N受拉为正。",
        ["节点坐标及21根杆件端点与fixtures/drawings/truss-simple-tri.dxf的STRUCT实体逐一一致。",
         "E=205000 MPa、A=0.01 m²保留自re-dxf-truss-simple-tri；原DXF仅为作者核对来源，本题公开输入为文字表。"], []))

    m = truss()
    grid(m, [0, 4, 8, 12, 16], [2.4] * 5)
    chords(m, 4); verticals(m, 4)
    diagonals(m, [("B0", "T1"), ("B1", "T2"), ("T2", "B3"), ("T3", "B4")])
    for i in range(1, 4):
        load(m, f"T{i}", 12)
    out.append((34, m, ["T1", "T2", "T3"], ["D1", "D2", "D3", "D4"],
        "Build the 16 m span, 2.4 m high parallel-chord Howe-type truss with four 4 m panels using the attached tables. "
        "The four diagonals are exactly B0-T1, B1-T2, T2-B3, T3-B4; use these endpoints rather than inferring a pattern "
        "from the truss name. Retain all five verticals, including both end verticals. B0 is pinned and B4 is a roller "
        "free in global X. Apply 12 kN downward at each of T1, T2, T3; T0 and T4 have no applied load. Use elastic "
        "axial-only members capable of tension and compression, self-weight off, and first-order static analysis in "
        "OpenSees. For LC1 report ux and uz at the three loaded upper nodes, N for each diagonal D1-D4, and Fx and Fz "
        "at both supports. Report displacement in m and force in kN, with tension-positive N.",
        ["Missing appendix completed with E=206000 MPa, nu=0.3, rho=7850 kg/m³ and A=0.01 m² for every bar.",
         "The explicit four diagonal endpoints define the reverse-Pratt orientation; no name-based topology inference is required."], []))

    m = truss()
    grid(m, [0, 3, 6, 9, 12, 15, 18], [3] * 7)
    chords(m, 6)
    for i in [0, 6]:
        bar(m, f"V{i}", f"B{i}", f"T{i}")
    for i in range(1, 6):
        node(m, f"M{i}", 3 * i, 1.5)
        bar(m, f"V{i}L", f"B{i}", f"M{i}")
        bar(m, f"V{i}U", f"M{i}", f"T{i}")
    k_pairs = [("B0", "M1"), ("T0", "M1"), ("B1", "M2"), ("T1", "M2"),
               ("B2", "M3"), ("T2", "M3"), ("M3", "B4"), ("M3", "T4"),
               ("M4", "B5"), ("M4", "T5"), ("M5", "B6"), ("M5", "T6")]
    for i, (a, b) in enumerate(k_pairs, 1):
        bar(m, f"K{i:02d}", a, b)
    for name in ["T1", "T2"]:
        load(m, name, 12)
    out.append((35, m, ["T1", "T2"], [e["id"] for e in m["elements"] if e["id"].startswith(("K", "V"))],
        "建立跨度18 m、高3 m、六个3 m节间的平行弦K形腹杆桁架，全部节点与杆件端点见附件。"
        "内部五根竖杆在M1至M5处真实分为上下两段，中点坐标分别为(3,0,1.5)、(6,0,1.5)、"
        "(9,0,1.5)、(12,0,1.5)、(15,0,1.5)m。十二根K形斜杆K01至K12的端点必须逐项采用表中数据；"
        "M3同时连接左右两格的四支K斜杆。B0铰支，B6为X向自由滚支。仅T1(x=3 m)和T2(x=6 m)"
        "各向下加载12 kN。用OpenSees进行仅轴力、可受拉压弹性杆的一阶静力分析，自重关闭。"
        "输出LC1下T1、T2的ux、uz，每一支K斜杆及所有竖杆分段的轴力N，两个支座的Fx、Fz。"
        "位移用m、力用kN，N受拉为正，并核对中点真实连接与结构稳定性。",
        ["补齐的连接表含19节点36杆：12弦杆、12竖杆分段/端竖杆及12支K斜杆。",
         "五个内部竖杆中点均为真实节点；给定对称K连接在中竖杆存在一阶超静定性，约束后刚度满秩。",
         "未给定属性补齐为E=206000 MPa、nu=0.3、rho=7850 kg/m³、全杆A=0.01 m²。"], []))

    m = truss()
    grid(m, [0, 3, 6, 9, 12], [2.5] * 5)
    chords(m, 4); verticals(m, 4)
    for i in range(4):
        bar(m, f"DU{i + 1}", f"B{i}", f"T{i + 1}")
        bar(m, f"DD{i + 1}", f"T{i}", f"B{i + 1}")
    for i in range(1, 4):
        load(m, f"T{i}", 10)
    out.append((36, m, [f"T{i}" for i in range(5)], [e["id"] for e in m["elements"] if e["id"].startswith("D")],
        "Build the 12 m span, 2.5 m high parallel-chord truss with four 3 m panels from the complete attached tables. "
        "Each panel has both diagonal members DU1-DU4 and DD1-DD4. Their geometric crossings have no node, no "
        "connection and no shared degrees of freedom; retain each diagonal as one endpoint-to-endpoint truss member. "
        "Keep all five verticals. B0 is pinned and B4 is a roller free in global X. Apply 10 kN downward only at T1, T2 "
        "and T3. All members are axial-only elastic bars capable of tension and compression. Run first-order static "
        "analysis with OpenSees and self-weight off. For LC1 report ux and uz for every top node T0-T4, N for all eight "
        "crossing diagonals, and Fx and Fz at both supports. Include an explicit statement that the four crossing points "
        "are not connections. Use m and kN, with tension-positive N.",
        ["Missing appendix completed with E=206000 MPa, nu=0.3, rho=7850 kg/m³ and A=0.01 m² for all bars.",
         "The model has exactly ten chord nodes and 21 bars; none of the four diagonal crossings is a node."],
        [{"id": "crossing-nonconnection", "description": "Explicitly state that all four X-diagonal crossings have no structural node or connection.", "state": 1, "quantityIds": [], "kind": "interaction"}]))

    m = truss()
    grid(m, [0, 2, 5, 9, 12], [2.2] * 5)
    chords(m, 4); verticals(m, 4)
    diagonals(m, [("B0", "T1"), ("T1", "B2"), ("B2", "T3"), ("T3", "B4")])
    for name, p in [("T1", 10), ("T2", 18), ("T3", 12)]:
        load(m, name, p)
    out.append((37, m, ["T1", "T2", "T3"], [e["id"] for e in m["elements"] if not e["id"].startswith("V")],
        "按附件完整端点表建立高2.2 m的平行弦桁架。四个节间依次为2、3、4、3 m，下弦与上弦的"
        "x坐标均为0、2、5、9、12 m，必须按累计坐标建模。B0铰支，B4为X向自由滚支。"
        "上弦T1(x=2 m)、T2(x=5 m)、T3(x=9 m)分别向下10、18、12 kN。全部杆件仅传轴力，"
        "可受拉压，采用OpenSees一阶线弹性静力分析，自重关闭。输出LC1下三受载点ux、uz，"
        "各根上弦、下弦及斜杆轴力N和两支座Fx、Fz；位移用m，力用kN，N受拉为正。",
        ["未给定的连接表采用四格交替斜杆并保留五根竖杆，附件明确列出各杆端点。",
         "未给定属性补齐为E=206000 MPa、nu=0.3、rho=7850 kg/m³、全杆A=0.01 m²。"], []))

    m = truss()
    grid(m, [0, 3, 6, 9, 12, 15], [1.5, 1.8, 2.1, 2.4, 2.7, 3])
    chords(m, 5); verticals(m, 5)
    diagonals(m, [("B0", "T1"), ("B1", "T2"), ("T2", "B3"), ("B3", "T4"), ("T4", "B5")])
    for name, p in [("T1", 12), ("T3", 18), ("T4", 10)]:
        load(m, name, p)
    out.append((38, m, ["T1", "T3", "T4"], [e["id"] for e in m["elements"] if e["id"].startswith(("D", "V"))],
        "Build the 15 m truss from the complete attached endpoint tables. The bottom chord is horizontal with five "
        "3 m panels. Upper-node heights increase linearly from 1.5 m at x=0 to 3 m at x=15: 1.5,1.8,2.1,2.4,2.7,3 m. "
        "Preserve the asymmetric diagonal sequence B0-T1, B1-T2, T2-B3, B3-T4, T4-B5, and all six vertical web bars. "
        "B0 is pinned and B5 is a roller free in global X. Apply downward nodal loads of 12,18,10 kN at T1(x=3), "
        "T3(x=9),T4(x=12) m respectively. Use axial-only elastic bars that can carry tension and compression; run "
        "first-order static analysis in OpenSees with self-weight off. For LC1 report ux and uz at all three loaded "
        "nodes, N in every diagonal and vertical web bar, and Fx and Fz at both supports. Use m and kN, with positive "
        "N for tension. Check the supplied connectivity for stability.",
        ["The previously missing asymmetric connection table is frozen explicitly, with 12 nodes and 21 bars.",
         "Missing properties completed as E=206000 MPa, nu=0.3, rho=7850 kg/m³, and A=0.01 m² for every bar."], []))

    m = truss(grouped=True)
    grid(m, [0, 4, 8, 12, 16, 20], [3] * 6)
    chords(m, 5, grouped=True); verticals(m, 5, "A3")
    diagonals(m, [("T0", "B1"), ("T1", "B2"), ("B2", "T3"), ("B3", "T4"), ("B4", "T5")], "A3")
    for i, p in enumerate([8, 12, 16, 10], 1):
        load(m, f"T{i}", p)
    out.append((39, m, ["T1", "T2", "T3", "T4"], None,
        "按附件节点、杆件与截面指派表建立跨度20 m、高3 m、五个4 m节间的平行弦桁架。上弦TC1至TC5"
        "统一用A1=0.012 m²，下弦BC1至BC5用A2=0.010 m²，全部竖杆V0至V5与斜杆D1至D5用"
        "A3=0.006 m²。B0铰支，B5为X向自由滚支。内部上弦T1、T2、T3、T4依次向下8、12、16、10 kN。"
        "所有杆件仅传轴力并可受拉压，用OpenSees进行一阶线弹性静力分析，自重关闭。输出LC1下四个"
        "受载点ux、uz、全部21根杆轴力N及两支座Fx、Fz；另标出三组代表杆TC3、BC3、D3的轴力与组别。"
        "附完整组别索引，明确每根杆的截面组、A值与材料。位移用m，力用kN，N受拉为正。",
        ["未给定截面面积显式补齐为上弦A1=.012、下弦A2=.010、腹杆A3=.006 m²，三组不同。",
         "全杆同材料E=206000 MPa、nu=.3、rho=7850 kg/m³；三组代表杆TC3、BC3、D3属于全杆数量请求的显式子集。"],
        [{"id": "section-group-index", "description": "附完整杆件组别索引：上弦A1、下弦A2、竖杆/斜杆A3；逐杆列面积和材料，突出代表杆TC3、BC3、D3。", "state": 1, "quantityIds": [], "kind": "interaction"}]))

    m = truss("3d")
    node(m, "A", 0, 0, y=0, fix="xyz")
    node(m, "B", 4, 0, y=0, fix="yz")
    node(m, "C", 2, 0, y=2 * math.sqrt(3), fix="z")
    node(m, "D", 2, 3, y=2 * math.sqrt(3) / 3)
    for a, b in [("A", "B"), ("B", "C"), ("C", "A"), ("A", "D"), ("B", "D"), ("C", "D")]:
        bar(m, a + b, a, b)
    load(m, "D", 30)
    out.append((40, m, ["D"], None,
        "Build the four-node, six-member tetrahedral space truss using the complete attached tables. In global XYZ "
        "coordinates with Z upward: A=(0,0,0), B=(4,0,0), C=(2,2√3,0), D=(2,2√3/3,3) m. Use members AB, BC, CA, AD, "
        "BD and CD; D projects to the centroid of the equilateral base. Restrain translations X,Y,Z at A, Y,Z at B, "
        "and only Z at C. All other translations are free. Apply 30 kN downward at D. Members are axial-only elastic "
        "bars capable of both tension and compression. Rotations are inactive truss bookkeeping degrees of freedom. "
        "Use OpenSees for first-order static analysis with self-weight off. For LC1 report D's ux, uy, uz, axial N for "
        "all six bars, and the full global reaction vector (Fx,Fy,Fz) at each of A, B and C, including zero components. "
        "Use m and kN, with tension positive. Check spatial stability and global equilibrium.",
        ["Exact radical coordinates are written to numerical precision in the table; the symbolic values in the prompt define the geometry.",
         "Missing EA appendix completed as E=206000 MPa and A=0.01 m²; nu=.3 and rho=7850 kg/m³ are explicit, with self-weight disabled."], []))
    return out


def matrix_rank(a, tolerance=1e-10):
    """Partial-pivot elimination on a dimensionless compatibility matrix."""
    a = [list(row) for row in a]
    rank = 0
    for col in range(len(a[0]) if a else 0):
        pivot = max(range(rank, len(a)), key=lambda row: abs(a[row][col]), default=rank)
        if rank == len(a) or abs(a[pivot][col]) <= tolerance:
            continue
        a[rank], a[pivot] = a[pivot], a[rank]
        value = a[rank][col]
        a[rank] = [v / value for v in a[rank]]
        for row in range(rank + 1, len(a)):
            factor = a[row][col]
            if abs(factor) > tolerance:
                a[row] = [x - factor * y for x, y in zip(a[row], a[rank])]
        rank += 1
    return rank


def rigidity_check(m):
    axes = [0, 2] if m["coordinate_system"]["dimension"] == "2d" else [0, 1, 2]
    nodes = {n["id"]: n for n in m["nodes"]}
    free = [(n["id"], axis) for n in m["nodes"] for axis in axes if not n["restraints"][axis]]
    indices = {dof: i for i, dof in enumerate(free)}
    matrix = []
    edges = set()
    connected = set()
    for member in m["elements"]:
        assert member["type"] == "truss"
        a, b = member["nodes"]
        assert a != b and a in nodes and b in nodes
        edge = tuple(sorted([a, b])); assert edge not in edges
        edges.add(edge); connected.update([a, b])
        delta = [nodes[b][key] - nodes[a][key] for key in ["x", "y", "z"]]
        length = math.sqrt(sum(v * v for v in delta)); assert length > 0
        row = [0.] * len(free)
        for axis in axes:
            if (a, axis) in indices:
                row[indices[a, axis]] = -delta[axis] / length
            if (b, axis) in indices:
                row[indices[b, axis]] = delta[axis] / length
        matrix.append(row)
    assert connected == set(nodes)
    rank = matrix_rank(matrix)
    assert rank == len(free), f"Mechanism: rank={rank}, free translation DOFs={len(free)}"
    return {"nodes": len(nodes), "members": len(edges), "freeTranslations": len(free), "compatibilityRank": rank}


def structural_edges(m):
    nodes = {n["id"]: (n["x"], n["z"]) for n in m["nodes"]}
    return {tuple(sorted((nodes[e["nodes"][0]], nodes[e["nodes"][1]]))) for e in m["elements"]}


def dxf_structural_edges(path):
    lines = path.read_text().splitlines()
    pairs = zip(lines[::2], lines[1::2])
    entities = []; current = None
    for code, value in pairs:
        code, value = code.strip(), value.strip()
        if code == "0":
            if current:
                entities.append(current)
            current = (value, {})
        elif current:
            current[1][code] = value
    return {tuple(sorted(((float(d["10"]), float(d["20"])), (float(d["11"]), float(d["21"])))))
            for kind, d in entities if kind == "LINE" and d.get("8") == "STRUCT"}


def validate_records(data):
    expected = {31: (14, 25, 60), 32: (11, 19, 50), 33: (12, 21, 40), 34: (10, 17, 36),
                35: (19, 36, 24), 36: (10, 21, 30), 37: (10, 17, 40), 38: (12, 21, 40),
                39: (12, 21, 46), 40: (4, 6, 30)}
    checks = {}
    for number, m, *_ in data:
        check = rigidity_check(m)
        count_n, count_e, downward = expected[number]
        assert (check["nodes"], check["members"]) == (count_n, count_e)
        assert sum(p["fz"] for p in m["load_cases"][0]["loads"]) == -downward
        checks[f"STD-{number:03d}"] = check
    by_id = {number: m for number, m, *_ in data}
    dxf = ROOT / "fixtures/drawings/truss-simple-tri.dxf"
    assert structural_edges(by_id[33]) == dxf_structural_edges(dxf), "STD-033 differs from legacy DXF"
    tri = ROOT / "scenarios/standard_workflow/std-truss-tri-en.json"
    original = json.loads(tri.read_text())
    assert "(7.5,2.5)" in original["message"]
    assert "from bottom x = 6m and 9m to the apex" in original["message"]
    assert {(e["nodes"][0], e["nodes"][1]) for e in by_id[32]["elements"] if e["id"].startswith("D")} == {
        ("B1", "T2"), ("B2", "R"), ("B3", "R"), ("B4", "T3")}
    checks["legacySourceHashes"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in [dxf, tri, ROOT / "scenarios/standard_workflow/truss-roof-en.json"]}
    return checks


def author():
    from std_a_core import emit, qnode, qmember
    data = records()
    checks = validate_records(data)
    selection = {"kind": "case", "id": "LC1"}
    for number, m, observed, requested_bars, prompt, notes, extra_outputs in data:
        section_note_en = (
            "The property appendix completes each area A as a solid square with side sqrt(A), "
            "Iy=Iz=A²/12 and J=0.14083333333333334 A². These are explicit authored section "
            "properties. All elements remain axial-only trusses; bending and torsion constants "
            "are inactive and axial stiffness remains EA.")
        section_note_zh = (
            "属性附表将每个给定面积A补齐为边长sqrt(A)的实心正方形截面，Iy=Iz=A²/12，"
            "J=0.14083333333333334 A²。这些截面参数为明确编制的附录数据；全部构件仍为"
            "仅轴力桁架杆，弯曲和扭转常数不参与本题计算，轴向刚度仍为EA。")
        prompt += "\n\n" + (section_note_en if number in [32, 34, 36, 38, 40] else section_note_zh)
        notes.append(section_note_en)
        quantities = []
        components = ["ux", "uy", "uz"] if number == 40 else ["ux", "uz"]
        for name in observed:
            quantities.extend(qnode(m, name, component, selection=selection, unit="m") for component in components)
        selected = set(requested_bars) if requested_bars is not None else {e["id"] for e in m["elements"]}
        nodes = {n["id"]: n for n in m["nodes"]}
        for e in m["elements"]:
            if e["id"] in selected:
                a, b = (nodes[name] for name in e["nodes"])
                length = math.sqrt(sum((a[key] - b[key]) ** 2 for key in ["x", "y", "z"]))
                quantities.append(qmember(m, e["id"], length / 2, "N", selection=selection, unit="kN"))
        supports = ["A", "B", "C"] if number == 40 else ["B0", f"B{max(int(n['id'][1:]) for n in m['nodes'] if n['id'].startswith('B'))}"]
        for support in supports:
            for component in (["Fx", "Fy", "Fz"] if number == 40 else ["Fx", "Fz"]):
                quantities.append(qnode(m, support, component, selection=selection, unit="kN"))
        notes += [f"Author-only independent connectivity/stability check: {checks[f'STD-{number:03d}']}; native execution, numerical reference and blind input review remain pending."]
        if number in [31, 32, 33]:
            source = {31: "scenarios/standard_workflow/truss-roof-en.json",
                      32: "scenarios/standard_workflow/std-truss-tri-en.json",
                      33: "fixtures/drawings/truss-simple-tri.dxf"}[number]
            notes.append({"sourcePath": source, "sourceSha256": checks["legacySourceHashes"][source],
                          "retained": "Geometry, topology, supports, nodal loads, E and A",
                          "newCorpusContract": "Self-weight disabled; only the LC1 load case; no default combination or legacy answer reused."})
        emit(number, m, prompt, quantities, extra_outputs=extra_outputs, notes=notes)
    return checks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    checks = validate_records(records()) if args.check_only else author()
    print(json.dumps(checks, ensure_ascii=False, indent=2))
