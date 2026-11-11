"""Source-based structural checks for the MM-079..088 authoring batch.

Run with Python 3 from any working directory. These checks integrate applied
loads and compare coordinate topology; they do not solve a structural model,
generate reference answers, or establish native-engine acceptance.
"""

from copy import deepcopy
import math

from mm_b_79_88 import build_specs


def _point(n):
    return tuple(round(n[k], 10) for k in ("x", "y", "z"))


def _edge(kind, a, b):
    return kind, tuple(sorted((a, b)))


def _grid(xs, ys, z):
    points = {(x, y, z) for x in xs for y in ys}
    edges = {_edge("beam", (a, y, z), (b, y, z))
             for a, b in zip(xs, xs[1:]) for y in ys}
    edges |= {_edge("beam", (x, a, z), (x, b, z))
              for x in xs for a, b in zip(ys, ys[1:])}
    return points, edges


def _source_topology(case):
    """Independent source geometry in coordinates, without author IDs/helpers."""
    if case == 79:
        xs, ys, zs = [0, 6], [0, 5], [0, 3.6, 7.2]
    elif case in (80, 84, 88):
        xs, ys, zs = [0, 6, 12], [0, 5], [0, 3.6, 7.2]
    elif case == 81:
        xs, ys, zs = [0, 6], [0, 5, 10], [0, 3.3, 6.6, 9.9]
    elif case in (82, 87):
        xs, ys, zs = [0, 6, 12], [0, 5, 10], [0, 3.6, 7.2]
    elif case == 83:
        xs, ys, zs = [0, 6, 12], [0, 5], [0, 3.6, 7.2, 10.8]
    elif case == 85:
        xs, ys, zs = [0, 4, 11], [0, 3, 9], [0, 3.4, 7.5]
    elif case == 86:
        xs, ys, zs = [0, 4, 8, 12], [0, 5, 10], [0, 3.6, 7.2]
    else:
        raise AssertionError(f"Unexpected case {case}")

    bases, _ = _grid(xs, ys, 0)
    points, edges = set(bases), set()
    for z in zs[1:]:
        fx = [0, 6] if case == 83 and z == 10.8 else xs
        fy = [0, 5] if case == 81 and z == 9.9 else ys
        floor_points, floor_edges = _grid(fx, fy, z)
        if case == 86:
            # Five retained cells leave every grid vertex, but no rear middle edge.
            floor_edges.remove(_edge("beam", (4, 10, z), (8, 10, z)))
        elif case == 87 and z == 7.2:
            # Two explicit perimeter loops sharing exactly their central vertex.
            loops = [((0, 0, z), (6, 0, z), (6, 5, z), (0, 5, z)),
                     ((6, 5, z), (12, 5, z), (12, 10, z), (6, 10, z))]
            floor_points = {pt for loop in loops for pt in loop}
            floor_edges = {_edge("beam", a, b) for loop in loops
                           for a, b in zip(loop, loop[1:] + loop[:1])}
        elif case == 80 and z == 7.2:
            floor_edges.remove(_edge("beam", (6, 0, z), (6, 5, z)))
        elif case == 82 and z == 7.2:
            floor_edges -= {_edge("beam", (6, 0, z), (6, 5, z)),
                            _edge("beam", (6, 5, z), (6, 10, z))}
        points |= floor_points
        edges |= floor_edges

    # Columns join only actual retained upper vertices to the preceding floor.
    for below, above in zip(zs, zs[1:]):
        for x, y, z in points.copy():
            if z == above and (x, y, below) in points:
                edges.add(_edge("column", (x, y, below), (x, y, above)))
    if case == 84:
        edges.remove(_edge("column", (6, 0, 3.6), (6, 0, 7.2)))
    if case == 88:
        edges.add(_edge("truss", (0, 0, 7.2), (12, 5, 7.2)))

    # Apply the actual source-defined displacement only after connecting floors.
    def transform(pt):
        x, y, z = pt
        if case == 79 and z == 7.2:
            return x + 1, y, z
        if case == 85 and pt == (0, 0, 7.5):
            return 1, 1, z
        return pt

    return ({transform(pt) for pt in points},
            {_edge(kind, transform(a), transform(b)) for kind, (a, b) in edges}, bases)


def check_topology(spec):
    case = int(spec["id"][-3:])
    model = spec["model"]
    nodes = {n["id"]: n for n in model["nodes"]}
    members = {e["id"]: e for e in model["elements"]}
    expected_points, expected_edges, expected_bases = _source_topology(case)
    actual_points = {_point(n) for n in nodes.values()}
    actual_edges = {_edge(e["type"], *[_point(nodes[n]) for n in e["nodes"]])
                    for e in members.values()}
    assert len(nodes) == len(model["nodes"]) == len(actual_points), (case, "duplicate nodes")
    assert len(members) == len(model["elements"]) == len(actual_edges), (case, "duplicate members")
    assert actual_points == expected_points, (case, "coordinate topology", actual_points ^ expected_points)
    assert actual_edges == expected_edges, (case, "member topology", actual_edges ^ expected_edges)
    fixed = {_point(n) for n in nodes.values() if all(n["restraints"])}
    assert fixed == expected_bases, (case, "base support locations")
    for n in nodes.values():
        assert n["restraints"] == [(_point(n) in expected_bases)] * 6, (case, "support DOFs")
    sections = {s["id"]: s for s in model["sections"]}
    for e in members.values():
        assert e["section"] in sections, (case, "undefined section", e["id"])
        assert e["id"] in model["metadata"]["elementReferenceVectors"], (case, "missing local-axis vector")
        a, b = [nodes[n] for n in e["nodes"]]
        assert math.dist(_point(a), _point(b)) > 0, (case, "zero-length member")
        if e["type"] == "column":
            assert e["section"] == "C1"
        elif e["type"] == "truss":
            assert e["section"] == "A1"
        elif case == 84 and a["y"] == b["y"] == 0 and a["z"] == b["z"] == 7.2:
            assert e["section"] == "BT", (case, "transfer section assignment")
        elif case in (79, 80, 81, 82):
            assert e["section"] == ("B1" if a["y"] == b["y"] else "B2")
        else:
            assert e["section"] == "B1"
    assert model["analysis_control"]["self_weight"] is False
    assert model["analysis_control"]["rigid_floor"] is False
    assert model["analysis_control"]["p_delta"] is False


def _integrated_loads(model):
    """Integrate actual distributed loads about the global origin, by case."""
    nodes = {n["id"]: n for n in model["nodes"]}
    members = {e["id"]: e for e in model["elements"]}
    result = {}
    for case in model["load_cases"]:
        total = [0.0] * 6
        for load in case["loads"]:
            assert load["reference_frame"] == "global"
            if load["type"] == "nodal":
                r = _point(nodes[load["node"]])
                f = [load.get("f" + k, 0) for k in "xyz"]
                applied_moment = [load.get("m" + k, 0) for k in "xyz"]
            else:
                assert load["type"] == "distributed" and not any(k in load for k in ("start", "end"))
                a, b = [_point(nodes[n]) for n in members[load["element"]]["nodes"]]
                length = math.dist(a, b)
                r = [(a[k] + b[k]) / 2 for k in range(3)]
                f = [load.get("w" + k, 0) * length for k in "xyz"]
                applied_moment = [0, 0, 0]
            moment = [r[1] * f[2] - r[2] * f[1],
                      r[2] * f[0] - r[0] * f[2],
                      r[0] * f[1] - r[1] * f[0]]
            for k in range(3):
                total[k] += f[k]
                total[k + 3] += moment[k] + applied_moment[k]
        result[case["id"]] = total
    return result


def check_resultants(spec):
    # These values follow directly from source floor areas/centroids and forces,
    # not from model reactions or from the authoring distribution metadata.
    # 079: two 30 m2 floors, centers X=3 and 4, Y=2.5.
    # 080: two 60 m2 floors; Fy=20 at (12,5,7.2).
    # 081: 60+60+30 m2 at 10 kPa, retaining the smaller upper floor centroid.
    # 082: 120 m2 at 10 and 8 kPa, plus the two corner lateral components.
    # 083: 2*60 m2 at 12 kPa and 30 m2 at 6 kPa.
    # 084: 60 m2 at 12 and 10 kPa.
    # 085: regular beam length 120 m, replace 4+3 by sqrt(10)+sqrt(5).
    # 086: 72 m of beams per floor; extra left strip 32 m, centroid (2,5).
    # 087: lower beams 66 m at 10, upper loops 22 m at 8 and at 6.
    # 088: 39 m of beams on each floor at 8; brace has no gravity load.
    s10, s5 = math.sqrt(10), math.sqrt(5)
    expected = {
        79: [0, 0, -600, -1500, 2100, 0],
        80: [0, 20, -960, -2544, 5760, 240],
        81: [0, 0, -1500, -6750, 4500, 0],
        82: [15, 10, -2160, -10872, 13068, -30],
        83: [0, 0, -1620, -4050, 9180, 0],
        84: [0, 0, -1320, -3300, 7920, 0],
        85: [10, 0, -8 * (113 + s10 + s5), -8 * (502.5 + .5 * s10 + 2 * s5),
             8 * (625 + 2.5 * s10 + .5 * s5) + 75, -10],
        86: [0, 0, -1280, -6080, 7168, 0],
        87: [0, 0, -968, -4730, 5676, 0],
        88: [0, 0, -624, -1560, 3744, 0],
    }
    case = int(spec["id"][-3:])
    actual = _integrated_loads(spec["model"])
    for got, want in zip(actual["D"], expected[case]):
        assert math.isclose(got, want, rel_tol=1e-12, abs_tol=1e-9), (case, "D resultant", actual["D"], expected[case])
    if case == 88:
        assert actual["WX"] == [20, 0, 0, 0, 144, -100]
        assert actual["WY"] == [0, 15, 0, -108, 0, 0]
    else:
        assert set(actual) == {"D"}, (case, "unexpected additional load cases")
    return actual


def check_requests(spec):
    model = spec["model"]
    nodes = {n["id"]: n for n in model["nodes"]}
    members = {e["id"]: e for e in model["elements"]}
    quantities = {q["id"]: q for q in spec["requests"]}
    assert len(quantities) == len(spec["requests"]), (spec["id"], "duplicate quantities")
    for q in quantities.values():
        loc = q["location"]
        assert "value" not in q
        assert loc["id"] in (nodes if loc["kind"] == "node" else members)
        if loc["kind"] == "member":
            a, b = [_point(nodes[n]) for n in members[loc["id"]]["nodes"]]
            assert 0 <= loc["positionM"] <= math.dist(a, b)
            assert loc["side"] in ("left", "right")
    for d in spec.get("derived", []):
        assert set(d["operands"]) <= set(quantities)
    if spec["id"] == "MM-080":
        d, = spec["derived"]
        assert d["operation"] == "difference"
        back, front = [quantities[q] for q in d["operands"]]
        assert _point(nodes[back["location"]["id"]]) == (6, 5, 7.2)
        assert _point(nodes[front["location"]["id"]]) == (6, 0, 7.2)
        assert back["component"] == front["component"] == "uy"
    elif spec["id"] == "MM-088":
        assert model["load_combinations"] == [
            dict(id="D", factors={"D": 1}),
            dict(id="D+WX", factors={"D": 1, "WX": 1}),
            dict(id="D+WY", factors={"D": 1, "WY": 1}),
        ]
        assert {(q["selection"]["kind"], q["selection"]["id"], q["component"])
                for q in quantities.values()} == {
                    ("combination", c, component)
                    for c in ("D", "D+WX", "D+WY") for component in ("ux", "uy", "N")}


def check_area_distribution(spec):
    case = int(spec["id"][-3:])
    if case > 84:
        return
    model = spec["model"]
    nodes = {n["id"]: n for n in model["nodes"]}
    pressures = {
        79: {3.6: 10, 7.2: 10}, 80: {3.6: 8, 7.2: 8},
        81: {3.3: 10, 6.6: 10, 9.9: 10}, 82: {3.6: 10, 7.2: 8},
        83: {3.6: 12, 7.2: 12, 10.8: 6}, 84: {3.6: 12, 7.2: 10},
    }
    expected = {}
    for e in model["elements"]:
        a, b = [nodes[n] for n in e["nodes"]]
        if e["type"] != "beam" or a["y"] != b["y"]:
            continue
        z, y = a["z"], a["y"]
        pressure = pressures[case][z]
        width = 5 if y == 5 and (case == 82 or case == 81 and z < 9) else 2.5
        expected[e["id"]] = pressure, width
    actual = {l["element"]: l for c in model["load_cases"] for l in c["loads"]
              if l["type"] == "distributed"}
    line_count = sum(l["type"] == "distributed" for c in model["load_cases"] for l in c["loads"])
    assert set(actual) == set(expected) and line_count == len(expected), (case, "one-way loaded members")
    for eid, (pressure, width) in expected.items():
        assert actual[eid]["wz"] == -pressure * width, (case, "source tributary load", eid)
        assert actual[eid].get("wx", 0) == actual[eid].get("wy", 0) == 0
    provenance = {v["member"]: (floor["pressureKNPerM2"], v["tributaryWidthM"])
                  for floor in model["metadata"]["floorAreaLoads"] for v in floor["members"]}
    assert provenance == expected, (case, "area-load provenance")


def check_line_distribution(spec):
    case = int(spec["id"][-3:])
    if case < 85:
        return
    model = spec["model"]
    nodes = {n["id"]: n for n in model["nodes"]}
    expected = {}
    for e in model["elements"]:
        if e["type"] != "beam":
            continue
        a, b = [nodes[n] for n in e["nodes"]]
        q = 8
        if case == 86 and a["z"] == 7.2 and max(a["x"], b["x"]) <= 4:
            q = 12
        elif case == 87:
            q = 10 if a["z"] == 3.6 else 8 if max(a["x"], b["x"]) <= 6 and max(a["y"], b["y"]) <= 5 else 6
        expected[e["id"]] = -q
    actual = {}
    for load_case in model["load_cases"]:
        for load in load_case["loads"]:
            if load["type"] == "distributed":
                assert load_case["id"] == "D"
                assert load.get("wx", 0) == load.get("wy", 0) == 0
                actual[load["element"]] = actual.get(load["element"], 0) + load["wz"]
    assert actual == expected, (case, "source line-load allocation")


def _must_fail(check, spec, label):
    try:
        check(spec)
    except AssertionError:
        return
    raise AssertionError(f"Negative control escaped detection: {label}")


def main():
    specs = build_specs()
    assert [s["id"] for s in specs] == [f"MM-{i:03d}" for i in range(79, 89)]
    for spec in specs:
        check_topology(spec)
        result = check_resultants(spec)
        check_requests(spec)
        check_area_distribution(spec)
        check_line_distribution(spec)
        print(spec["id"], "PASS exact topology, restraints, sections, resultants, requests;",
              "D applied [Fx,Fy,Fz,Mx,My,Mz] =", [round(v, 8) for v in result["D"]])

    # Check that the audits reject plausible mistakes, including unchanged force
    # sum with an incorrect distribution and a reversed signed derived output.
    bad = deepcopy(specs[0])
    bad["model"]["elements"].pop()
    _must_fail(check_topology, bad, "omitted member")
    bad = deepcopy(specs[0])
    loads = bad["model"]["load_cases"][0]["loads"]
    loads[0]["wz"] -= 1
    loads[1]["wz"] += 1
    _must_fail(check_resultants, bad, "same force sum but wrong gravity moment")
    bad = deepcopy(specs[7])
    bad["model"]["load_cases"][0]["loads"].append(
        deepcopy(bad["model"]["load_cases"][0]["loads"][0]))
    _must_fail(check_resultants, bad, "duplicate shared-edge loading")
    bad = deepcopy(specs[1])
    bad["derived"][0]["operands"].reverse()
    _must_fail(check_requests, bad, "reversed signed relative Uy")
    print("PASS four negative controls. No solver/reference/native acceptance claimed.")


if __name__ == "__main__":
    main()
