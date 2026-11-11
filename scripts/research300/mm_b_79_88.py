"""Explicit research-300 authoring for MM-079 through MM-088.

Source: the approved coverage plan and original task/model workbook rows.
No numerical answers are authored here; native truth and input review are pending.
"""

from mm_b_common import p


def _node_request(identifier, node, component, description, selection=None):
    result = dict(id=identifier, location=dict(kind="node", id=node),
                  component=component, unit="m" if component[0] == "u" else
                  "kN" if component[0] == "F" else "kN*m", description=description)
    if selection is not None:
        result["selection"] = selection
    return result


def _member_request(identifier, member, station, component, description,
                    side="right", selection=None):
    result = dict(id=identifier,
                  location=dict(kind="member", id=member, positionM=station, side=side),
                  component=component, unit="kN" if component in ("N", "V2", "V3") else "kN*m",
                  description=description)
    if selection is not None:
        result["selection"] = selection
    return result


def _properties(m, concrete=False, directional=True, transfer=False, brace=False):
    """Freeze missing appendix properties rather than inherit unlisted defaults."""
    E, nu, rho = (30000.0, 0.2, 2500.0) if concrete else (206000.0, 0.3, 7850.0)
    m["materials"] = [dict(id="M1", name="C30" if concrete else "Steel M1",
                           type="concrete" if concrete else "steel", E=E,
                           G=E / (2 * (1 + nu)), nu=nu, rho=rho)]
    m["sections"] = [p.section("C1", .5, .5), p.section("B1", .3, .6)]
    if directional:
        m["sections"].append(p.section("B2", .3, .7))
    if transfer:
        m["sections"].append(p.section("BT", .4, .8))
    if brace:
        m["sections"].append(p.section("A1", .1, .1))
    if not directional:
        for element in m["elements"]:
            if element["type"] == "beam":
                element["section"] = "B1"
    return [
        ("C30 appendix completed explicitly: E=30000 MPa, nu=0.2, G=12500 MPa, rho=2500 kg/m^3; "
         "gross uncracked sections, no stiffness reductions." if concrete else
         "Missing steel M1 appendix completed explicitly: E=206000 MPa, nu=0.3, "
         "G=79230.76923076923 MPa, rho=7850 kg/m^3; linear elastic response."),
        "Section dimensions are explicit case inputs: C1=500x500 mm, B1=300x600 mm"
        + (", B2=300x700 mm" if directional else "")
        + (", BT=400x800 mm" if transfer else "")
        + (", A1=100x100 mm solid axial brace" if brace else "")
        + "; A, Iy, Iz and Saint-Venant J are frozen in the appendix. "
        "Beam H is the vertical depth; B is the horizontal width.",
        "Use first-order linear elasticity, global Z up, self-weight off, no rigid diaphragm, "
        "no rigid offsets, no automatic combinations, no earthquake cases and no stiffness modifiers.",
    ]


def _remove(m, member_ids):
    m["elements"] = [e for e in m["elements"] if e["id"] not in member_ids]
    for member in member_ids:
        m["metadata"]["elementReferenceVectors"].pop(member, None)


def _area_floor_load(m, level, pressure, members_and_widths):
    """Retain the original area pressure and exact one-way conversion provenance."""
    mappings = []
    for member, width in members_and_widths:
        q = pressure * width
        p.load(m, id=f"D-area-{member}", type="distributed", element=member, wz=-q)
        mappings.append(dict(member=member, tributaryWidthM=width,
                             lineLoadKNPerM=q, globalDirection=[0, 0, -1]))
    m["metadata"].setdefault("floorAreaLoads", []).append(dict(
        level=level, case="D", pressureKNPerM2=pressure,
        distribution="X beams only; sum of half-spans of adjacent retained Y bays",
        members=mappings))


def _spec(identifier, title, m, requests, public_notes, decisions, derived=None):
    result = dict(id=identifier, title_en=title, model=m, requests=requests,
                  public_notes=public_notes, decisions=decisions)
    if derived:
        result["derived"] = derived
    return result


def _mm079():
    m = p.spatial([0, 6], [0, 5], [3.6, 7.2],
                  shift=lambda ix, iy, j, x, y: (x + 1, y) if j == 2 else (x, y))
    decisions = _properties(m)
    for level in (1, 2):
        _area_floor_load(m, level, 10, [(f"x0-{iy}-{level}", 2.5) for iy in (0, 1)])
    requests = [
        _node_request("D-top-ux", "n1-1-2", "ux", "顶层图示后右角节点 n1-1-2 的全局 Ux"),
        _node_request("D-top-uz", "n1-1-2", "uz", "顶层图示后右角节点 n1-1-2 的全局 Uz"),
        _member_request("D-front-right-base-M2", "c1-0-1", 0, "M2", "前右首层柱 c1-0-1 柱底截面 0+ 的局部 M2"),
        _member_request("D-front-right-base-M3", "c1-0-1", 0, "M3", "前右首层柱 c1-0-1 柱底截面 0+ 的局部 M3"),
    ]
    decisions.append("Unspecified front-right column-base bending output completed as both local M2 and M3 at the first-story column base, x=6, y=0, z=0, sampled inside the member at 0+.")
    return _spec("MM-079", "Spatial frame with a translated upper floor and inclined columns", m, requests, [
        "视图约定：前侧为较小 Y，右侧为较大 X；位移按右手全局轴取正。",
        "两层实际楼面的 D 面载均为 10 kN/m²；仅传给图中 X 梁，各梁受荷宽度为相邻实际 Y 跨长的一半之和，Y 梁不重复受荷。",
        "本题柱底弯矩要求 c1-0-1 的局部 M2、M3，取柱内侧 0+；竖柱局部轴 1=+Z、2=-Y、3=+X。",
    ], decisions)


def _mm080():
    m = p.spatial([0, 6, 12], [0, 5], [3.6, 7.2])
    _remove(m, {"y1-0-2"})
    decisions = _properties(m)
    for level in (1, 2):
        _area_floor_load(m, level, 8, [(f"x{ix}-{iy}-{level}", 2.5)
                                      for ix in (0, 1) for iy in (0, 1)])
    p.load(m, id="D-lateral", type="nodal", node="n2-1-2", fy=20)
    requests = [
        _node_request("D-loaded-corner-uy", "n2-1-2", "uy", "Global Uy of the laterally loaded top corner n2-1-2"),
        _node_request("D-gap-back-uy", "n1-1-2", "uy", "Global Uy of n1-1-2, the back endpoint of the missing beam"),
        _node_request("D-gap-front-uy", "n1-0-2", "uy", "Global Uy of n1-0-2, the front endpoint of the missing beam"),
    ]
    derived = [dict(id="D-gap-relative-uy", operation="difference",
                    operands=["D-gap-back-uy", "D-gap-front-uy"], unit="m",
                    description="Signed relative Uy across the missing beam: Uy(n1-1-2) minus Uy(n1-0-2)")]
    decisions.append("The source leaves the relative-displacement order unspecified. Freeze signed DeltaUy=Uy(back endpoint at y=5)-Uy(front endpoint at y=0); do not take an absolute value.")
    return _spec("MM-080", "Spatial frame with a missing top-floor transverse beam", m, requests, [
        "Front is the smaller-Y side. All displacements use the right-handed global axes.",
        "Both retained floors carry D=8 kN/m². Distribute only to X beams using the sum of adjacent retained Y half-spans; do not also load Y beams.",
        "Report signed relative Uy as Uy(n1-1-2) - Uy(n1-0-2), in addition to the Uy at the loaded corner. All stated gravity and lateral loads act together in the basic case D.",
    ], decisions, derived)


def _mm081():
    m = p.spatial([0, 6], [0, 5, 10], [3.3, 6.6, 9.9],
                  keep=lambda ix, iy, j: j < 3 or iy < 2)
    decisions = _properties(m)
    for level in (1, 2):
        _area_floor_load(m, level, 10, [(f"x0-{iy}-{level}", width)
                                       for iy, width in ((0, 2.5), (1, 5), (2, 2.5))])
    _area_floor_load(m, 3, 10, [("x0-0-3", 2.5), ("x0-1-3", 2.5)])
    requests = [
        _node_request("D-top-uz", "n1-1-3", "uz", "第三层图示后右角 n1-1-3 的全局 Uz"),
        _node_request("D-second-back-left-uz", "n0-2-2", "uz", "第二层后侧左端节点 n0-2-2 的全局 Uz"),
        _node_request("D-second-back-right-uz", "n1-2-2", "uz", "第二层后侧右端节点 n1-2-2 的全局 Uz"),
    ]
    decisions.append("The unspecified second-floor rear node output is completed by reporting both retained rear-edge nodes, at x=0 and 6, y=10, z=6.6.")
    return _spec("MM-081", "Three-story spatial frame with a Y-direction roof setback", m, requests, [
        "前侧为较小 Y，后侧为较大 Y；第二层后侧节点 Uz 须分别报告图示 n0-2-2、n1-2-2。",
        "各层实际保留楼面 D=10 kN/m²；仅按相邻实际 Y 半跨之和传给 X 梁，Y 梁不重复受荷。退台外无楼面荷载。",
    ], decisions)


def _mm082():
    m = p.spatial([0, 6, 12], [0, 5, 10], [3.6, 7.2])
    _remove(m, {"y1-0-2", "y1-1-2"})
    decisions = _properties(m)
    for level, pressure in ((1, 10), (2, 8)):
        _area_floor_load(m, level, pressure, [(f"x{ix}-{iy}-{level}", width)
                                             for ix in (0, 1)
                                             for iy, width in ((0, 2.5), (1, 5), (2, 2.5))])
    p.load(m, id="D-corner-lateral", type="nodal", node="n2-2-2", fx=15, fy=10)
    requests = [
        _node_request("D-loaded-corner-ux", "n2-2-2", "ux", "Global Ux of the loaded top corner n2-2-2"),
        _node_request("D-loaded-corner-uy", "n2-2-2", "uy", "Global Uy of the loaded top corner n2-2-2"),
        _node_request("D-top-center-uy", "n1-1-2", "uy", "Global Uy of the top-floor center node n1-1-2"),
    ]
    return _spec("MM-082", "Spatial frame with an entire top-floor Y beam line missing", m, requests, [
        "First-floor D pressure is 10 kN/m² and second-floor D pressure is 8 kN/m². Distribute each only to actual X beams using adjacent retained Y half-spans. Y beams receive no duplicate floor load.",
        "All gravity loads and the two global force components at the marked corner act together in basic case D. Architectural grid, enclosure and equipment layers do not define structural members or supports.",
    ], decisions)


def _mm083():
    m = p.spatial([0, 6, 12], [0, 5], [3.6, 7.2, 10.8],
                  keep=lambda ix, iy, j: j < 3 or ix < 2, concrete=True)
    decisions = _properties(m, concrete=True, directional=False)
    for level in (1, 2):
        _area_floor_load(m, level, 12, [(f"x{ix}-{iy}-{level}", 2.5)
                                       for ix in (0, 1) for iy in (0, 1)])
    _area_floor_load(m, 3, 6, [("x0-0-3", 2.5), ("x0-1-3", 2.5)])
    requests = [
        _node_request("D-top-uz", "n1-1-3", "uz", "第三层图示后右角 n1-1-3 的全局 Uz"),
        _member_request("D-right-front-base-N", "c2-0-1", 0, "N", "右侧前柱 c2-0-1 柱底 0+ 截面轴力 N，受拉为正"),
        _member_request("D-right-back-base-N", "c2-1-1", 0, "N", "右侧后柱 c2-1-1 柱底 0+ 截面轴力 N，受拉为正"),
    ]
    decisions.append("The unspecified right-side bottom-column axial force is completed by requesting both right-side first-story columns at y=0 and 5, base section 0+, with tension-positive N.")
    return _spec("MM-083", "Three-story concrete spatial frame with a partial roof setback", m, requests, [
        "首两层实际楼面 D=12 kN/m²，第三层实际楼面 D=6 kN/m²；仅按实际相邻 Y 半跨之和传给 X 梁，Y 梁不重复受荷。",
        "右侧底柱轴力分别报告图示 c2-0-1、c2-1-1 的柱底 0+ 截面 N，受拉为正、受压为负。混凝土按附录完整毛截面刚度分析。",
    ], decisions)


def _mm084():
    m = p.spatial([0, 6, 12], [0, 5], [3.6, 7.2], concrete=True)
    _remove(m, {"c1-0-2"})
    decisions = _properties(m, concrete=True, directional=False, transfer=True)
    for e in m["elements"]:
        if e["id"] in ("x0-0-2", "x1-0-2"):
            e["section"] = "BT"
    for level, pressure in ((1, 12), (2, 10)):
        _area_floor_load(m, level, pressure, [(f"x{ix}-{iy}-{level}", 2.5)
                                             for ix in (0, 1) for iy in (0, 1)])
    requests = [
        _node_request("D-transfer-midpoint-uz", "n1-0-2", "uz", "Global Uz at the connected midpoint node n1-0-2 of the front transfer beam"),
        _member_request("D-transfer-midpoint-left-M2", "x0-0-2", 6, "M2", "Transfer beam midpoint bending M2 approached from the left: x0-0-2 at s=6 m, side left", side="left"),
        _member_request("D-transfer-midpoint-right-M2", "x1-0-2", 0, "M2", "Transfer beam midpoint bending M2 approached from the right: x1-0-2 at s=0 m, side right"),
    ]
    decisions.append("The 12 m transfer beam is two connected 6 m BT segments at the real transverse-beam junction. Midpoint bending means vertical-bending local M2; request both one-sided midpoint sections because the connected Y beam can transfer a concentrated joint moment.")
    return _spec("MM-084", "Spatial transfer frame with a missing upper edge-middle column", m, requests, [
        "First-floor D pressure is 12 kN/m²; second-floor D pressure is 10 kN/m². Distribute only to X beams using adjacent retained Y half-spans. Y beams receive no duplicate floor load.",
        "The transfer midpoint output includes local M2 on both sides of the marked connected node: x0-0-2 at s=6 m from the left and x1-0-2 at s=0 m from the right. For these +X members, local 2=+Y and local 3=+Z.",
        "BT denotes the 400 by 800 mm transfer section; all other beams use B1. Use gross uncracked concrete section properties.",
    ], decisions)


def _mm085():
    m = p.spatial([0, 4, 11], [0, 3, 9], [3.4, 7.5],
                  shift=lambda ix, iy, j, x, y: (1, 1) if (ix, iy, j) == (0, 0, 2) else (x, y))
    decisions = _properties(m, directional=False)
    for e in m["elements"]:
        if e["type"] == "beam":
            p.load(m, id=f"D-line-{e['id']}", type="distributed", element=e["id"], wz=-8)
    p.load(m, id="D-corner-lateral", type="nodal", node="n0-0-2", fx=10)
    requests = [
        _node_request("D-shifted-corner-ux", "n0-0-2", "ux", "移位顶角 n0-0-2 的全局 Ux"),
        _node_request("D-shifted-corner-uz", "n0-0-2", "uz", "移位顶角 n0-0-2 的全局 Uz"),
        _member_request("D-shifted-corner-base-M2", "c0-0-1", 0, "M2", "该角首层柱 c0-0-1 柱底 0+ 截面的局部 M2"),
        _member_request("D-shifted-corner-base-M3", "c0-0-1", 0, "M3", "该角首层柱 c0-0-1 柱底 0+ 截面的局部 M3"),
    ]
    decisions += [
        "Complete the unspecified base bending output as both local M2 and M3 in first-story corner column c0-0-1 at its base section 0+.",
        "The 8 kN/m load is global -Z per metre of each actual beam's true length, including both non-orthogonal roof beams; it is not an area load or a projected-length load.",
    ]
    return _spec("MM-085", "Irregular spatial frame with one shifted roof corner", m, requests, [
        "所有实际梁的向下 8 kN/m 按构件实际长度计，荷载方向为全局 -Z；包括图中非正交梁。",
        "该角底柱弯矩分别报告 c0-0-1 柱内侧 0+ 的 M2、M3；竖柱局部轴 1=+Z、2=-Y、3=+X。全部线载与角点侧力共同作用于 D 工况。",
    ], decisions)


def _mm086():
    # Build the retained-cell union explicitly; keep each shared edge exactly once.
    xs, ys = [0, 4, 8, 12], [0, 5, 10]
    cells = [(0, 0), (1, 0), (2, 0), (0, 1), (2, 1)]
    vertices, edges = set(), set()
    for ix, iy in cells:
        corners = [(ix, iy), (ix + 1, iy), (ix + 1, iy + 1), (ix, iy + 1)]
        vertices.update(corners)
        for a, b in zip(corners, corners[1:] + corners[:1]):
            edges.add(tuple(sorted((a, b))))
    m = p.model("3d")
    for level, z in enumerate((0, 3.6, 7.2)):
        for ix, iy in sorted(vertices):
            p.node(m, f"n{ix}-{iy}-{level}", xs[ix], z, ys[iy], [True] * 6 if level == 0 else None)
    for level in (1, 2):
        for ix, iy in sorted(vertices):
            p.elem(m, f"c{ix}-{iy}-{level}", f"n{ix}-{iy}-{level-1}", f"n{ix}-{iy}-{level}", "column", "C1")
        for (ix, iy), (jx, jy) in sorted(edges):
            axis = "x" if ix != jx else "y"
            member = f"{axis}{ix}-{iy}-{level}"
            p.elem(m, member, f"n{ix}-{iy}-{level}", f"n{jx}-{jy}-{level}")
            p.load(m, id=f"D-line-{member}", type="distributed", element=member, wz=-8)
            # Freeze the source's unspecified left-wing group as the full left strip.
            if level == 2 and max(xs[ix], xs[jx]) <= 4:
                p.load(m, id=f"D-left-wing-{member}", type="distributed", element=member, wz=-4)
    m["stories"] = [dict(id=f"s{j}", elevation=(j - 1) * 3.6, height=3.6, rigid_diaphragm=False) for j in (1, 2)]
    m["metadata"]["retainedFloorCells"] = [dict(level=j, cells=cells) for j in (1, 2)]
    decisions = _properties(m, directional=False)
    requests = [
        _node_request("D-notch-left-uz", "n1-2-2", "uz", "Global Uz at the left notch-mouth endpoint n1-2-2"),
        _node_request("D-notch-right-uz", "n2-2-2", "uz", "Global Uz at the right notch-mouth endpoint n2-2-2"),
    ]
    for iy in (0, 1, 2):
        for component in ("Fx", "Fy", "Fz", "Mx", "My", "Mz"):
            requests.append(_node_request(f"D-left-outer-{iy}-{component}", f"n0-{iy}-0", component,
                                          f"Global support reaction {component} at left outer-column base n0-{iy}-0"))
    decisions += [
        "Complete the source's unspecified left-wing extra-load boundary as all seven upper-floor beams wholly in the left strip X=0..4 m, including the front-left cell. Apply extra -4 kN/m once per actual beam, in addition to the base -8 kN/m.",
        "Interpret the two notch ends as the mouth endpoints at (4,10,7.2) and (8,10,7.2). Complete the unspecified left-wing outer base reaction by reporting all six global support components at all three X=0 bases, Y=0,5,10.",
    ]
    return _spec("MM-086", "Two-story U-shaped spatial frame from architectural DXF", m, requests, [
        "Use the structural layers and their node/member labels. Architectural enclosure, grid and equipment lines are nonstructural.",
        "The upper left-wing extra-load group is x0-0-2, x0-1-2, x0-2-2, y0-0-2, y0-1-2, y1-0-2 and y1-1-2. Add 4 kN/m downward to the 8 kN/m already on each of those beams, once per member.",
        "The two notch-mouth observation nodes are n1-2-2 and n2-2-2. Report all six global reaction components at each marked outer-left base n0-0-0, n0-1-0 and n0-2-0.",
    ], decisions)


def _mm087():
    upper_vertices = {(0, 0), (1, 0), (0, 1), (1, 1), (2, 1), (1, 2), (2, 2)}
    m = p.spatial([0, 6, 12], [0, 5, 10], [3.6, 7.2],
                  keep=lambda ix, iy, j: j < 2 or (ix, iy) in upper_vertices)
    decisions = _properties(m, directional=False)
    front_left = {"x0-0-2", "x0-1-2", "y0-0-2", "y1-0-2"}
    back_right = {"x1-1-2", "x1-2-2", "y1-1-2", "y2-1-2"}
    for e in m["elements"]:
        if e["type"] != "beam":
            continue
        q = 10 if e["id"].endswith("-1") else 8 if e["id"] in front_left else 6
        if e["id"].endswith("-2"):
            assert e["id"] in front_left | back_right
        p.load(m, id=f"D-line-{e['id']}", type="distributed", element=e["id"], wz=-q)
    m["metadata"]["retainedFloorCells"] = [dict(level=1, cells=[(0, 0), (1, 0), (0, 1), (1, 1)]),
                                            dict(level=2, cells=[(0, 0), (1, 1)])]
    requests = [
        _node_request("D-front-left-wing-outer-uz", "n0-0-2", "uz", "前左顶翼外角 n0-0-2 的全局 Uz"),
        _node_request("D-back-right-wing-outer-uz", "n2-2-2", "uz", "后右顶翼外角 n2-2-2 的全局 Uz"),
        _node_request("D-shared-center-ux", "n1-1-2", "ux", "两顶翼共享中心节点 n1-1-2 的全局 Ux"),
    ]
    decisions.append("Complete the unspecified external wing corners as (0,0,7.2) for the front-left wing and (12,10,7.2) for the back-right wing; the common center is a single node, not coincident disconnected nodes.")
    return _spec("MM-087", "Spatial frame with two diagonal top-floor wings", m, requests, [
        "前侧为较小 Y，左侧为较小 X；两个顶翼外角输出采用图示 n0-0-2、n2-2-2，共享中心输出采用 n1-1-2。",
        "首层各实际梁向下 10 kN/m；顶层前左翼四边梁向下 8 kN/m，后右翼四边梁向下 6 kN/m；按实际长度加载，共同作用于 D 工况。",
    ], decisions)


def _mm088():
    m = p.spatial([0, 6, 12], [0, 5], [3.6, 7.2])
    decisions = _properties(m, directional=False, brace=True)
    p.elem(m, "roof-brace", "n0-0-2", "n2-1-2", "truss", "A1")
    for e in m["elements"]:
        if e["type"] == "beam":
            p.load(m, id=f"D-line-{e['id']}", type="distributed", element=e["id"], wz=-8)
    p.load(m, "WX", id="WX-top-corner", type="nodal", node="n2-1-2", fx=20)
    p.load(m, "WY", id="WY-top-corner", type="nodal", node="n0-1-2", fy=15)
    m["load_combinations"] = [dict(id="D", factors={"D": 1}),
                              dict(id="D+WX", factors={"D": 1, "WX": 1}),
                              dict(id="D+WY", factors={"D": 1, "WY": 1})]
    requests = []
    for combination in ("D", "D+WX", "D+WY"):
        selection = dict(kind="combination", id=combination)
        for component in ("ux", "uy"):
            requests.append(_node_request(f"comb-{combination}-top-{component}", "n2-1-2", component,
                                          f"Combination {combination}: global {component} at roof node n2-1-2", selection))
        requests.append(_member_request(f"comb-{combination}-brace-N", "roof-brace", 6.5, "N",
                                        f"Combination {combination}: axial force N in roof-brace at midlength, tension positive",
                                        selection=selection))
    decisions += [
        "The axial-only roof brace is one 13 m truss from n0-0-2 to n2-1-2. Its crossing with the intermediate transverse beam creates no node or connection. Brace N is sampled at s=6.5 m, tension positive.",
        "Execute all three prescribed combinations. Include baseline D outputs as well as both requested lateral combinations; distinguish the D combination selection from the basic D case.",
    ]
    return _spec("MM-088", "Spatial frame with an axial-only roof-plane brace", m, requests, [
        "The marked roof-brace carries axial force only. A crossing without a connection symbol transfers no force between crossing members; the brace is connected only at its two labeled endpoints.",
        "Execute combinations D, D+WX and D+WY separately using the listed unit factors. Report top-node Ux/Uy and tension-positive brace N for each; D is the baseline and both lateral combinations are required.",
        "The 8 kN/m D load acts along every actual beam in global -Z, per metre of actual member length. No gravity line load is assigned to the axial-only brace.",
    ], decisions)


def build_specs():
    return [_mm079(), _mm080(), _mm081(), _mm082(), _mm083(),
            _mm084(), _mm085(), _mm086(), _mm087(), _mm088()]


if __name__ == "__main__":
    from mm_b_common import export_specs
    export_specs(build_specs())
