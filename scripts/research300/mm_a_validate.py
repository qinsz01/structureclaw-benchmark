"""Read-only structural diagnostics for authored research-300 MM-001..050.

This validates source binding, public-input boundaries and numerical model health.
The independent direct-stiffness solver is a diagnostic only. No response values,
reference files, native receipts, or acceptance claims are written by this script.
"""

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DOFS = ["ux", "uy", "uz", "rx", "ry", "rz"]
NODE_ACTIONS = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
MEMBER_ACTIONS = ["N", "V2", "V3", "T", "M2", "M3"]
HIDDEN_NAMES = {"contract.json", "reference-requests.json", "independent-reference.json"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def read_json(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def indexed(rows, label):
    require(isinstance(rows, list) and rows, f"{label}: nonempty array required")
    require(all(isinstance(r.get("id"), str) and r["id"] for r in rows), f"{label}: invalid ID")
    result = {r["id"]: r for r in rows}
    require(len(result) == len(rows), f"{label}: duplicate IDs")
    return result


def safe_file(case_dir, name):
    require(isinstance(name, str) and name and "\\" not in name, f"invalid relative file name: {name!r}")
    relative = PurePosixPath(name)
    require(not relative.is_absolute() and not any(x in (".", "..") for x in relative.parts),
            f"path traversal: {name}")
    path = case_dir / name
    require(path.is_file(), f"missing file: {name}")
    for part in [path, *path.parents]:
        if part == case_dir.parent:
            break
        require(not part.is_symlink(), f"symlink forbidden: {name}")
    require(path.resolve().is_relative_to(case_dir.resolve()), f"escaped case root: {name}")
    return path


def source_tables(root):
    plan = indexed(read_json(root / "planning/capability-coverage-300.json")["cases"], "plan")
    source = root / "planning/sources"
    if not source.exists():
        source = root.parent.parent / "planning/sources"
    tasks = indexed(read_json(source / "all-tasks-engines-v2.json"), "source tasks")
    models = {r["taskId"]: r for r in read_json(source / "all-models-engines-v2.json")}
    return plan, tasks, models


def check_contract(case_dir, contract, row, task, source_model):
    cid = case_dir.name
    require(contract.get("schemaVersion") == 1 and contract.get("evaluationProfile") == "engineering-v2.3",
            "contract schema/profile mismatch")
    for key in ("id", "modelId", "family", "language", "plannedEngine"):
        require(contract.get(key) == row[key], f"source {key} mismatch")
    require(contract["id"] == cid, "directory ID mismatch")
    require(contract.get("locale") == ("en" if row["language"] == "英文" else "zh"), "locale mismatch")
    source = contract.get("sourcePlan", {})
    require(source == row["sourceRequirements"], "sourcePlan must equal the exact flat sourceRequirements")
    # Compare the source strings against the original tables as well as the plan.
    # Numbered requirement IDs remain bound below through complete coverage.
    for field, value in row["sourceRequirements"].items():
        prefix, key = field.split(".", 1)
        original = {"task": task, "model": source_model, "engine": task["enginePlan"]}[prefix]
        require(value == original[key], f"planning/original source differs: {field}")
    for key, expected in (("status", "authored-candidate"), ("sameEngineTruthStatus", "pending"),
                          ("inputBlindReview", "pending"), ("llmEndToEnd", "not-run")):
        require(contract.get(key) == expected, f"unsupported acceptance claim: {key}")

    model_files = contract.get("modelStates", [])
    require(model_files and len(set(model_files)) == len(model_files), "modelStates missing/duplicate")
    for name in model_files:
        safe_file(case_dir, name)
    attachments = contract.get("attachments", [])
    require(attachments and len(set(attachments)) == len(attachments), "public attachments missing/duplicate")
    hidden = set(model_files) | HIDDEN_NAMES
    for name in attachments:
        path = safe_file(case_dir, name)
        require(name not in hidden and not re.search(r"model-state|reference|receipt|truth", name, re.I),
                f"hidden artifact exposed as attachment: {name}")
        require(path.suffix.lower() in (".svg", ".png", ".dxf", ".txt", ".csv"),
                f"unexpected public attachment type: {name}")
    require(any(Path(a).suffix in (".png", ".dxf") for a in attachments), "missing source drawing modality")
    if "DXF" in row["subcategory"]:
        require(any(a.endswith(".dxf") for a in attachments), "source requires DXF")
    else:
        require(any(a.endswith(".png") for a in attachments), "source requires PNG")

    turns = contract.get("turns", [])
    require(len(turns) == task["turns"], "original turn count changed")
    seen_attachments = set()
    for index, turn in enumerate(turns, 1):
        require(turn.get("id") == f"t{index}", "turn IDs/order invalid")
        require(isinstance(turn.get("instruction"), str) and turn["instruction"], "empty turn instruction")
        require(not any(name in turn["instruction"] for name in hidden), "hidden file referenced in public instruction")
        current = turn.get("attachments", [])
        require(len(current) == len(set(current)) and set(current) <= set(attachments), "invalid turn attachments")
        require(not seen_attachments.intersection(current), "turn attachment is not newly visible")
        seen_attachments.update(current)
        expectation = turn.get("expectation")
        require(expectation in ("analyze", "clarify", "query"), "unknown turn expectation")
        if expectation == "clarify":
            require(turn.get("state") is None, "clarification exposes an executable completed state")
            require(turn.get("unresolvedFields") and turn.get("expectedQuestions"), "clarification missing its question/field")
        else:
            require(type(turn.get("state")) is int and 1 <= turn["state"] <= len(model_files), "invalid turn state")
            require(not turn.get("unresolvedFields"), "analysis retains unresolved essential fields")
    require(seen_attachments == set(attachments), "attachment never introduced by a turn")
    prompt = safe_file(case_dir, "prompt.txt").read_text(encoding="utf-8")
    require(prompt.strip() == turns[0]["instruction"].strip(), "prompt.txt differs from public first turn")
    if cid in ("MM-007", "MM-021", "MM-032"):
        require(turns[0]["expectation"] == "clarify" and turns[1]["expectation"] == "analyze", "delayed-input sequence changed")
        require(not any(re.search(r"resolved|confirmed|supplement", f) for f in turns[0]["attachments"]),
                "delayed supplement exposed in first turn")
    if cid == "MM-032":
        for name in turns[0]["attachments"]:
            if Path(name).suffix in (".svg", ".txt", ".dxf"):
                text = safe_file(case_dir, name).read_text(encoding="utf-8")
                if name.endswith(".svg"):
                    text = " ".join(re.findall(r"<text\b[^>]*>(.*?)</text>", text, re.S))
                require(not re.search(r"(?<![\d.])(?:1\.25|2\.5|5\s*/\s*3|5\s*/\s*6)(?![\d.])", text),
                        f"withheld roof elevation leaks through {name}")

    outputs = indexed(contract.get("requiredOutputs", []), "required outputs")
    turn_by_id = {turn["id"]: turn for turn in turns}
    require(any(o["kind"] == "figure" for o in outputs.values()), "source-required result figure omitted")
    for output in outputs.values():
        require(output.get("kind") in ("numerical", "derived", "figure", "interaction"), "invalid output kind")
        require(isinstance(output.get("description"), str) and output["description"], "missing output description")
        turn_ids = output.get("turnIds", [])
        require(isinstance(turn_ids, list) and turn_ids and len(set(turn_ids)) == len(turn_ids),
                "required output has missing/duplicate turn binding")
        for turn_id in turn_ids:
            require(turn_id in turn_by_id, "required output references unknown turn")
            turn = turn_by_id[turn_id]
            require(turn["expectation"] != "clarify" or output["kind"] == "interaction",
                    "non-interaction output bound to clarification turn")
            require(output.get("state") == turn.get("state"), "required output state differs from bound turn")
        if output["kind"] in ("numerical", "derived"):
            require(output.get("quantityIds"), "numerical output has no quantities")
        if output["kind"] == "interaction":
            require(not output.get("quantityIds"), "interaction output exposes numerical quantities")
    if row["language"] == "英文":
        visible = [t["instruction"] for t in turns] + [o["description"] for o in outputs.values()]
        visible += [safe_file(case_dir, f).read_text(encoding="utf-8") for f in attachments
                    if Path(f).suffix in (".txt", ".svg", ".dxf")]
        require(not any(re.search(r"[\u4e00-\u9fff]", s) for s in visible), "Chinese visible text in English case")

    gates = {g["id"] for g in contract.get("acceptanceGates", [])}
    require(all(g.get("status") == "pending" for g in contract.get("acceptanceGates", [])), "unsupported acceptance gate status")
    requirements = {r["id"]: r for r in row["requirements"]}
    covered = []
    fields = set()
    for coverage in contract.get("requirementCoverage", []):
        field = coverage.get("sourceField")
        require(field in row["sourceRequirements"], "unknown coverage source field")
        fields.add(field)
        ids = coverage.get("requirementIds", [])
        require(ids and all(i in requirements and requirements[i]["sourceField"] == field for i in ids),
                "coverage requirement IDs do not belong to source field")
        covered += ids
        require(coverage.get("targets"), "coverage mapping has no target")
        for target in coverage["targets"]:
            require(isinstance(target, str), "coverage target must be a namespaced string")
            namespace, sep, identity = target.partition(":")
            require(identity not in hidden, f"hidden artifact is not public coverage evidence: {target}")
            allowed = {"gate": gates, "attachment": set(attachments),
                       "output": set(outputs), "turn": {t["id"] for t in turns}}
            require(sep and namespace in allowed and identity in allowed[namespace], f"unresolved coverage target: {target}")
    require(Counter(covered) == Counter(requirements.keys()), "source requirement numbers omitted or multiply mapped")
    require(fields == set(row["sourceRequirements"]), "source fields not completely covered")


def model_health(model):
    require(model.get("schema_version") == "2.2.0" and model.get("unit_system") == "SI", "model protocol/units mismatch")
    coordinates = model.get("coordinate_system", {})
    require(coordinates.get("dimension") in ("2d", "3d") and coordinates.get("semantics") == "global-z-up", "invalid coordinate convention")
    require(coordinates.get("dof_order") == DOFS, "DOF order changed")
    planar = coordinates["dimension"] == "2d"
    if planar:
        require(coordinates.get("plane") == "xz", "planar model is not XZ")
    for option in ("self_weight", "rigid_floor", "p_delta", "rigid_offsets", "construction_stage"):
        require(model.get("analysis_control", {}).get(option) is False, f"analysis option not explicitly OFF: {option}")
    nodes = indexed(model.get("nodes", []), "nodes")
    elements = indexed(model.get("elements", []), "elements")
    materials = indexed(model.get("materials", []), "materials")
    sections = indexed(model.get("sections", []), "sections")
    cases = indexed(model.get("load_cases", []), "load cases")
    combinations = {c["id"]: c for c in model.get("load_combinations", [])}
    require(len(combinations) == len(model.get("load_combinations", [])), "duplicate combination IDs")
    xyz = {}
    for name, node in nodes.items():
        require(all(finite(node.get(k)) for k in ("x", "y", "z")), f"nonfinite coordinate: {name}")
        xyz[name] = np.array([node[k] for k in ("x", "y", "z")], float)
        restraint = node.get("restraints")
        require(isinstance(restraint, list) and len(restraint) == 6 and all(type(v) is bool for v in restraint),
                f"invalid restraints: {name}")
        if planar:
            require(abs(node["y"]) < 1e-12 and all(restraint[i] for i in (1, 3, 5)), f"XZ inactive DOFs not restrained: {name}")
    names = list(nodes)
    for i, name in enumerate(names):
        for other in names[i + 1:]:
            require(np.linalg.norm(xyz[name] - xyz[other]) > 1e-10, f"coincident disconnected node IDs: {name}/{other}")
    for name, material in materials.items():
        require(all(finite(material.get(k)) and material[k] > 0 for k in ("E", "G", "rho")), f"nonpositive material property: {name}")
        require(finite(material.get("nu")) and -1 < material["nu"] < 0.5, f"invalid Poisson ratio: {name}")
    for name, section in sections.items():
        properties = section.get("properties", {})
        require(all(finite(properties.get(k)) and properties[k] > 0 for k in ("A", "Iy", "Iz", "J")),
                f"nonpositive section property: {name}")
    neighbors = defaultdict(set)
    frame_nodes = set()
    lengths = {}
    edge_keys = set()
    for name, element in elements.items():
        require(element.get("type") in ("beam", "column", "truss", "brace"), f"unsupported element type: {name}")
        ends = element.get("nodes")
        require(isinstance(ends, list) and len(ends) == 2 and all(n in nodes for n in ends), f"invalid member endpoints: {name}")
        a, b = ends
        direction = xyz[b] - xyz[a]
        lengths[name] = float(np.linalg.norm(direction))
        require(lengths[name] > 1e-10, f"zero-length element: {name}")
        key = tuple(sorted(ends))
        require(key not in edge_keys, f"duplicate coincident member: {name}")
        edge_keys.add(key)
        neighbors[a].add(b)
        neighbors[b].add(a)
        require(element.get("section") in sections and element.get("material") in materials, f"unknown member property: {name}")
        if element["type"] not in ("truss", "brace"):
            frame_nodes.update(ends)
        if not planar:
            ref = model.get("metadata", {}).get("elementReferenceVectors", {}).get(name)
            require(isinstance(ref, list) and len(ref) == 3 and all(finite(v) for v in ref), f"missing local axis vector: {name}")
            require(np.linalg.norm(np.cross(direction / lengths[name], ref)) > 1e-10, f"parallel/zero local axis vector: {name}")
    visited, stack = set(), [names[0]]
    while stack:
        name = stack.pop()
        if name not in visited:
            visited.add(name)
            stack.extend(neighbors[name] - visited)
    require(visited == set(nodes), "structural graph is disconnected or has an unused observation node")
    for name in set(nodes) - frame_nodes:
        require(all(nodes[name]["restraints"][3:]), f"truss-only node has unrestrained inactive rotations: {name}")
    load_norm = 0.0
    for case_name, case in cases.items():
        loads = case.get("loads", [])
        require(len({l.get("id") for l in loads}) == len(loads), f"duplicate load IDs in {case_name}")
        case_norm = 0.0
        for load in loads:
            require(isinstance(load.get("id"), str) and load["id"], "missing load ID")
            require(load.get("reference_frame") == "global", "diagnostic requires explicit global loading")
            kind = load.get("type")
            require(kind in ("nodal", "point", "distributed"), f"unsupported load type: {kind}")
            keys = ("wx", "wy", "wz") if kind == "distributed" else ("fx", "fy", "fz", "mx", "my", "mz")
            values = [load.get(k, 0) for k in keys]
            require(all(finite(v) for v in values) and any(v != 0 for v in values), f"zero/nonfinite load: {load['id']}")
            scale = 1
            if kind == "nodal":
                require(load.get("node") in nodes and "element" not in load, "invalid nodal load target")
                if load["node"] not in frame_nodes:
                    require(not any(load.get(k, 0) for k in ("mx", "my", "mz")), "moment on an inactive truss rotation")
            else:
                require(load.get("element") in elements, "unknown member load target")
                length = lengths[load["element"]]
                require(elements[load["element"]]["type"] not in ("truss", "brace"), "member load requires an explicitly connected truss node")
                if kind == "point":
                    require(finite(load.get("position")) and 0 <= load["position"] <= length, "point load outside member")
                else:
                    start, end = load.get("start", 0), load.get("end", length)
                    require(finite(start) and finite(end) and 0 <= start < end <= length + 1e-9, "distributed load interval outside member")
                    scale = end - start
            if planar:
                require(not any(load.get(k, 0) for k in ("fy", "mx", "mz", "wy")), "load acts on an inactive XZ degree of freedom")
            case_norm += sum(abs(v) for v in values) * scale
        require(case_norm > 0, f"empty/zero basic load case: {case_name}")
        load_norm += case_norm
    for name, combination in combinations.items():
        factors = combination.get("factors", {})
        require(factors and set(factors) <= set(cases), f"unknown/empty combination factors: {name}")
        require(all(finite(v) for v in factors.values()) and any(factors.values()), f"invalid/zero combination: {name}")
    return dict(nodes=nodes, elements=elements, lengths=lengths, cases=cases, combinations=combinations,
                load_norm=load_norm, extent=max(1, max(float(np.linalg.norm(v)) for v in xyz.values())))


def check_requests(contract, request, models):
    require(request.get("schemaVersion") == 1, "request schema mismatch")
    states = request.get("states", [])
    require([s.get("state") for s in states] == list(range(1, len(models) + 1)), "request state coverage/order mismatch")
    for state, (model, health) in zip(states, models):
        require(state.get("model") == contract["modelStates"][state["state"] - 1], "request model does not match state")
        quantities = indexed(state.get("quantities", []), "requested quantities")
        all_units = {}
        for qid, q in quantities.items():
            require("value" not in q, "numerical truth must not be authored into requests")
            selection = q.get("selection", {})
            kind = selection.get("kind")
            require(kind in ("case", "combination"), "invalid selection namespace")
            require(selection.get("id") in health["cases" if kind == "case" else "combinations"], "unknown requested selection")
            location = q.get("location", {})
            component = q.get("component")
            if location.get("kind") == "node":
                require(location.get("id") in health["nodes"], "unknown requested node")
                require(component in DOFS + NODE_ACTIONS, "invalid node component")
                if component in NODE_ACTIONS:
                    require(health["nodes"][location["id"]]["restraints"][NODE_ACTIONS.index(component)],
                            f"reaction requested on an unrestrained DOF: {qid}")
            else:
                require(location.get("kind") == "member" and location.get("id") in health["elements"], "unknown requested member")
                require(component in MEMBER_ACTIONS + DOFS[:3], "invalid/unsupported member component")
                position = location.get("positionM")
                require(finite(position) and 0 <= position <= health["lengths"][location["id"]] + 1e-9, "requested station outside member")
                require(location.get("side") in ("left", "right"), "station side missing")
                if health["elements"][location["id"]]["type"] in ("truss", "brace"):
                    require(component == "N" or component in DOFS[:3], "bending/shear requested from an axial-only member")
            expected_unit = "m" if component in DOFS[:3] else "rad" if component in DOFS[3:] else "kN.m" if component in ("Mx", "My", "Mz", "T", "M2", "M3") else "kN"
            require(q.get("unit") == expected_unit, f"wrong unit for {qid}; expected canonical {expected_unit}")
            require(q.get("tolerance") == {"absolute": 1e-8, "relative": 1e-6}, f"unjustified tolerance override: {qid}")
            all_units[qid] = q["unit"]
        derived_ids = set()
        for d in state.get("derived", []):
            require(isinstance(d.get("id"), str) and d["id"] not in all_units, "duplicate/invalid derived ID")
            require("value" not in d and d.get("operation") in ("difference", "sum", "max", "min", "max_abs"), "invalid derived operation")
            operands = d.get("operands", [])
            require(operands and all(i in all_units for i in operands), "unknown/forward derived operand")
            require(d["operation"] != "difference" or len(operands) == 2, "difference requires two operands")
            require(all(all_units[i] == d.get("unit") for i in operands), "derived units inconsistent")
            all_units[d["id"]] = d["unit"]
            derived_ids.add(d["id"])
        used = set()
        for output in contract["requiredOutputs"]:
            if output.get("state") != state["state"]:
                continue
            require(set(output.get("quantityIds", [])) <= set(all_units), "output references a missing requested quantity")
            used.update(output.get("quantityIds", []))
        require(set(all_units) <= used, "requested quantity not bound to a required output")


def fixed_source_invariants(cid, model):
    """Independent geometric invariants; never import/replay the author builders."""
    number = int(cid[-3:])
    if not 31 <= number <= 40:
        return
    counts = {31: (14, 31, -60), 32: (10, 17, -40), 33: (12, 21, -40), 34: (8, 13, -36),
              35: (21, 42, -36), 36: (14, 29, -30), 37: (9, 15, -36), 38: (12, 21, -45),
              39: (18, 37, -48), 40: (5, 8, -30)}
    expected_n, expected_e, expected_fz = counts[number]
    require(len(model["nodes"]) == expected_n and len(model["elements"]) == expected_e, "fixed source node/member count mismatch")
    require(all(e["type"] == "truss" for e in model["elements"]), "source requires pure axial rods")
    require([c["id"] for c in model["load_cases"]] == ["D"] and not model["load_combinations"], "source requires sole basic case D")
    loads = model["load_cases"][0]["loads"]
    require(sum(l.get("fz", 0) for l in loads) == expected_fz, "fixed source total vertical load mismatch")

    def point(x, z, y=0):
        return tuple(round(v, 9) for v in (x, y, z))

    nodes = {n["id"]: point(n["x"], n["z"], n["y"]) for n in model["nodes"]}
    def edge(a, b):
        return tuple(sorted((a, b)))

    actual_edges = {edge(nodes[e["nodes"][0]], nodes[e["nodes"][1]]): e["section"] for e in model["elements"]}
    expected_edges = {}
    def rod(a, b, section="A1"):
        expected_edges[edge(a, b)] = section

    expected_nodes, expected_loads = set(), {}
    supports = {}
    if number in (31, 33, 35, 36, 38):
        count, pitch = (7, 3) if number in (31, 35) else (5, 3) if number == 36 else (6, 3)
        lower = [point(i * pitch, 0.3 * i if number == 38 else 0) for i in range(count)]
        heights = [2, 2, 3, 3, 2, 2] if number == 33 else [0.3 * i + 2 for i in range(count)] if number == 38 else [2.5 if number == 36 else 3] * count
        upper = [point(i * pitch, heights[i]) for i in range(count)]
        expected_nodes.update(lower + upper)
        supports = {lower[0]: (True, True, True), (upper[-1] if number == 35 else lower[-1]): (False, True, True)}
        web_section = "A2" if number in (31, 35, 36) else "A1"
        for i in range(count - 1):
            rod(lower[i], lower[i + 1]); rod(upper[i], upper[i + 1])
        if number != 35:
            for a, b in zip(lower, upper):
                rod(a, b, web_section)
        if number == 31:
            for i in range(6):
                rod(lower[i], upper[i + 1], "A2"); rod(upper[i], lower[i + 1], "A2")
            expected_loads = {upper[i]: -12 for i in range(1, 6)}
        elif number in (33, 38):
            for i in range(5):
                rod(lower[i], upper[i + 1])
            expected_loads = {lower[i]: -10 for i in range(1, 5)} if number == 33 else {upper[2]: -20, upper[3]: -15, upper[4]: -10}
        elif number == 35:
            # Frozen source-authoring completion: seven joint midpoints, double-K end panels.
            mid = {i: point(3 * i, 1.5) for i in range(7)}
            expected_nodes.update(mid.values())
            for i in range(7): rod(lower[i], mid[i], "A2"); rod(mid[i], upper[i], "A2")
            for outer, centre in ((0, 1), (1, 2), (2, 3), (4, 3), (5, 4), (6, 5), (1, 0), (5, 6)):
                rod(lower[outer], mid[centre], "A2"); rod(upper[outer], mid[centre], "A2")
            expected_loads = {upper[i]: -12 for i in (1, 2, 3)}
        else:
            for i in range(4):
                centre = point(3 * i + 1.5, 1.25)
                expected_nodes.add(centre)
                for corner in (lower[i], upper[i], lower[i + 1], upper[i + 1]): rod(corner, centre, "A2")
            expected_loads = {upper[i]: -10 for i in (1, 2, 3)}
    elif number in (32, 34):
        pitch, count = (3, 6) if number == 32 else (4, 5)
        lower = [point(pitch * i, 0) for i in range(count)]
        elevations = [1.25, 2.5, 5 / 3, 5 / 6] if number == 32 else [2, 4, 2]
        upper = [point(pitch * (i + 1), z) for i, z in enumerate(elevations)]
        expected_nodes.update(lower + upper)
        for i in range(count - 1): rod(lower[i], lower[i + 1])
        roof = [lower[0], *upper, lower[-1]]
        for a, b in zip(roof, roof[1:]): rod(a, b)
        for i, b in enumerate(upper, 1): rod(lower[i], b)
        if number == 32:
            for i in range(1, 4): rod(lower[i], upper[i])
        else:
            rod(lower[1], upper[1]); rod(lower[3], upper[1])
        expected_loads = {p: -10 if number == 32 else -12 for p in upper}
        supports = {lower[0]: (True, True, True), lower[-1]: (False, True, True)}
    elif number == 37:
        lower = [point(x, 0) for x in (0, 2, 5, 9, 12)]
        upper = [point(x, 2.2) for x in (1, 3.5, 7, 10.5)]
        expected_nodes.update(lower + upper)
        for chain in (lower, upper):
            for a, b in zip(chain, chain[1:]): rod(a, b)
        for i, p in enumerate(upper): rod(lower[i], p); rod(p, lower[i + 1])
        expected_loads = dict(zip(upper, (-8, -12, -10, -6)))
        supports = {lower[0]: (True, True, True), lower[-1]: (False, True, True)}
    elif number == 39:
        rows = [[point(4 * i, z) for i in range(6)] for z in (0, 1.5, 3)]
        for row, section in zip(rows, ("A3", "A2", "A1")):
            expected_nodes.update(row)
            for a, b in zip(row, row[1:]): rod(a, b, section)
        for lower, upper in zip(rows, rows[1:]):
            for a, b in zip(lower, upper): rod(a, b, "A4")
            for i in range(5): rod(lower[i], upper[i + 1], "A4")
        expected_loads = {rows[2][i]: -12 for i in range(1, 5)}
        supports = {rows[0][0]: (True, True, True), rows[0][-1]: (False, True, True)}
    else:
        base = [point(x, 0, y) for x, y in ((0, 0), (4, 0), (4, 4), (0, 4))]
        apex = point(2, 3, 2)
        expected_nodes.update([*base, apex])
        for i, p in enumerate(base): rod(p, base[(i + 1) % 4]); rod(p, apex)
        expected_loads = {apex: -30}
        supports = {p: (True, True, True) for p in base}
    require(set(nodes.values()) == expected_nodes, "fixed source geometry mismatch")
    require(actual_edges == expected_edges, "fixed source connectivity or section-group assignment mismatch")
    actual_loads = {}
    for load in loads:
        require(load["type"] == "nodal" and not any(load.get(k, 0) for k in ("fx", "fy", "mx", "my", "mz")), "fixed source requires vertical nodal forces")
        require(nodes[load["node"]] not in actual_loads, "fixed source load duplicated")
        actual_loads[nodes[load["node"]]] = load["fz"]
    require(actual_loads == expected_loads, "fixed source load placement/magnitude mismatch")
    for node in model["nodes"]:
        expected_restraint = supports.get(nodes[node["id"]], (False, number != 40, False))
        require(tuple(node["restraints"][:3]) == expected_restraint, "fixed source support location/directions mismatch")


def diagnostics(model, health, state, oracle):
    quantities = state["quantities"]
    grouped = defaultdict(list)
    for q in quantities:
        grouped[q["selection"]["kind"], q["selection"]["id"]].append(q)
    # Check every explicitly authored basic case/combination, including those with no response request.
    selections = [("case", c) for c in health["cases"]] + [("combination", c) for c in health["combinations"]]
    values = {}
    for kind, name in selections:
        factors = {name: 1.0} if kind == "case" else health["combinations"][name]["factors"]
        selected = grouped[kind, name]
        getter, evidence = oracle.solve(model, factors, [q["location"] for q in selected])
        residual = evidence["freeResidual"]
        balance = evidence["forceMomentBalance"]
        scale = 1 + health["load_norm"] * health["extent"] * max(1, sum(abs(v) for v in factors.values()))
        require(finite(residual) and residual <= 1e-7 * scale, f"independent free-DOF equilibrium failure: {kind}/{name}")
        require(all(finite(v) and abs(v) <= 1e-7 * scale for v in balance), f"independent global force/moment imbalance: {kind}/{name}")
        for q in selected:
            component = q["component"]
            if q["location"]["kind"] == "node" and component in NODE_ACTIONS:
                component = component.lower()  # Legacy oracle readback uses lowercase nodal forces/moments.
            value = getter(q["location"], component)
            require(finite(value), f"nonfinite diagnostic response: {q['id']}")
            values[q["id"]] = value
    for derived in state.get("derived", []):
        operands = [values[q] for q in derived["operands"]]
        operation = derived["operation"]
        if operation == "difference": value = operands[0] - operands[1]
        elif operation == "sum": value = sum(operands)
        elif operation == "max": value = max(operands)
        elif operation == "min": value = min(operands)
        else: value = max(operands, key=abs)
        require(finite(value), f"nonfinite derived diagnostic: {derived['id']}")
        values[derived["id"]] = value
        if derived["id"].startswith("D-C0-diagonal-"):
            require(abs(value) <= 1e-7 * (1 + health["load_norm"]), "MM-036 centre axial-force equilibrium failed")
    # Local values intentionally go out of scope; this routine emits counts only.
    return len(selections), len(values)


def validate_case(case_dir, row, task, source_model, oracle):
    contract = read_json(case_dir / "contract.json")
    check_contract(case_dir, contract, row, task, source_model)
    models = []
    for filename in contract["modelStates"]:
        model = read_json(safe_file(case_dir, filename))
        health = model_health(model)
        fixed_source_invariants(case_dir.name, model)
        models.append((model, health))
    request = read_json(safe_file(case_dir, "reference-requests.json"))
    check_requests(contract, request, models)
    counts = [diagnostics(model, health, state, oracle)
              for (model, health), state in zip(models, request["states"])]
    return {"states": len(models), "selections": sum(c[0] for c in counts), "responses": sum(c[1] for c in counts)}


def self_test(root, plan, tasks, sources, oracle):
    """Mutation regressions against validated fixtures; all mutations stay in memory."""
    import contextlib
    import io
    from unittest.mock import patch

    case_root = root / "corpora/research-300/cases"
    for cid in ("MM-031", "MM-032", "MM-035", "MM-040"):
        validate_case(case_root / cid, plan[cid], tasks[cid], sources[cid], oracle)
    folder = case_root / "MM-031"
    contract = read_json(folder / "contract.json")
    model = read_json(folder / "model-state-1.json")
    request = read_json(folder / "reference-requests.json")
    health = model_health(model)
    passed = []

    def rejects(label, expected_message, check):
        try:
            check()
        except ValueError as error:
            require(expected_message in str(error),
                    f"self-test {label}: wrong rejection reason: {error}")
            passed.append(label)
            print(f"SELF-TEST PASS: {label}", flush=True)
        else:
            raise ValueError(f"self-test mutation escaped validation: {label}")

    def contract_check(changed):
        check_contract(folder, changed, plan["MM-031"], tasks["MM-031"], sources["MM-031"])

    changed = deepcopy(contract)
    changed["sourcePlan"] = {"sourceRequirements": changed["sourcePlan"]}
    rejects("nested source plan replaced flat binding", "exact flat sourceRequirements", lambda: contract_check(changed))

    changed = deepcopy(contract)
    changed["sourcePlan"]["task.expectedOutput"] += " changed"
    rejects("source requirement text changed", "exact flat sourceRequirements", lambda: contract_check(changed))

    changed = deepcopy(contract)
    changed["requirementCoverage"][0]["targets"].append("modelStates:model-state-1.json")
    rejects("hidden model used as coverage evidence", "hidden artifact is not public coverage evidence", lambda: contract_check(changed))

    changed = deepcopy(contract)
    changed["attachments"].append("model-state-1.json")
    rejects("hidden model exposed", "hidden artifact exposed", lambda: contract_check(changed))

    changed = deepcopy(contract)
    changed["plannedEngine"] = "SAP2000"
    rejects("wrong prescribed engine", "source plannedEngine mismatch", lambda: contract_check(changed))

    changed = deepcopy(contract)
    changed["requirementCoverage"][0]["requirementIds"].pop()
    rejects("omitted source requirement", "source requirement numbers omitted", lambda: contract_check(changed))

    changed = deepcopy(model)
    changed["nodes"].append(dict(changed["nodes"][0], id="duplicate"))
    rejects("coincident disconnected node", "coincident disconnected node IDs", lambda: model_health(changed))

    changed = deepcopy(model)
    changed["nodes"][1]["restraints"][4] = False
    rejects("inactive truss rotation free", "unrestrained inactive rotations", lambda: model_health(changed))

    changed = deepcopy(model)
    changed["load_cases"][0]["loads"][0]["fz"] = 0
    rejects("zero load record", "zero/nonfinite load", lambda: model_health(changed))

    changed = deepcopy(model)
    changed["nodes"][1]["z"] += 0.2
    rejects("source geometry drift", "fixed source geometry mismatch",
            lambda: fixed_source_invariants("MM-031", changed))

    changed = deepcopy(model)
    changed["load_cases"][0]["loads"][0]["fz"] = -11
    rejects("source load magnitude drift", "fixed source total vertical load mismatch",
            lambda: fixed_source_invariants("MM-031", changed))

    changed = deepcopy(request)
    changed["states"][0]["quantities"][1]["location"]["positionM"] = 100
    rejects("member station beyond endpoint", "requested station outside member",
            lambda: check_requests(contract, changed, [(model, health)]))

    changed = deepcopy(request)
    changed["states"][0]["quantities"][0]["unit"] = "kN"
    rejects("displacement unit changed", "wrong unit",
            lambda: check_requests(contract, changed, [(model, health)]))

    # Use a beam moment request: the truss fixture deliberately has no moments.
    moment_folder = case_root / "MM-001"
    moment_contract = read_json(moment_folder / "contract.json")
    moment_model = read_json(moment_folder / "model-state-1.json")
    moment_request = read_json(moment_folder / "reference-requests.json")
    moment_models = [(moment_model, model_health(moment_model))]
    check_requests(moment_contract, moment_request, moment_models)
    moment_quantity = next(q for q in moment_request["states"][0]["quantities"] if q["component"] == "M2")
    moment_quantity["unit"] = "kN*m"
    rejects("noncanonical moment unit reintroduced", "expected canonical kN.m",
            lambda: check_requests(moment_contract, moment_request, moment_models))

    changed = deepcopy(request)
    changed["states"][0]["quantities"][0]["selection"]["kind"] = "combination"
    rejects("case/combination namespace confused", "unknown requested selection",
            lambda: check_requests(contract, changed, [(model, health)]))

    folder32 = case_root / "MM-032"
    changed = read_json(folder32 / "contract.json")
    supplement = changed["turns"][1]["attachments"].pop()
    changed["turns"][0]["attachments"].append(supplement)
    rejects("delayed roof supplement exposed early", "delayed supplement exposed in first turn",
            lambda: check_contract(folder32, changed, plan["MM-032"], tasks["MM-032"], sources["MM-032"]))

    changed = read_json(folder32 / "contract.json")
    resolved_output = next(o for o in changed["requiredOutputs"] if o["kind"] == "numerical")
    resolved_output["turnIds"] = ["t1"]
    rejects("resolved output exposed in clarification turn", "non-interaction output bound to clarification turn",
            lambda: check_contract(folder32, changed, plan["MM-032"], tasks["MM-032"], sources["MM-032"]))

    changed = read_json(case_root / "MM-040/model-state-1.json")
    element = changed["elements"][0]
    nodes = {n["id"]: n for n in changed["nodes"]}
    a, b = [nodes[n] for n in element["nodes"]]
    changed["metadata"]["elementReferenceVectors"][element["id"]] = [b[k] - a[k] for k in ("x", "y", "z")]
    rejects("local-axis vector parallel to member", "parallel/zero local axis vector", lambda: model_health(changed))

    changed = read_json(case_root / "MM-035/model-state-1.json")
    changed["nodes"] = [n for n in changed["nodes"] if n["id"] not in ("M0", "M6")]
    changed["elements"] = [e for e in changed["elements"] if not set(e["nodes"]).intersection(("M0", "M6"))]
    for end in (0, 6):
        changed["elements"].append(dict(id=f"V{end}", type="truss", nodes=[f"L{end}", f"U{end}"],
                                         material="M1", section="A2"))
    rejects("MM-035 end midpoint joints removed", "fixed source node/member count mismatch",
            lambda: fixed_source_invariants("MM-035", changed))

    # Exercise the actual CLI return policy without deleting or moving a fixture.
    actual_is_file = Path.is_file
    missing_contract = case_root / "MM-031/contract.json"

    def simulated_is_file(path):
        return False if path == missing_contract else actual_is_file(path)

    with patch.object(Path, "is_file", simulated_is_file), contextlib.redirect_stdout(io.StringIO()):
        strict_exit = main(["--root", str(root), "--start", "31", "--end", "32"])
        authoring_exit = main(["--root", str(root), "--start", "31", "--end", "32", "--allow-missing"])
    require(strict_exit == 1 and authoring_exit == 0, "missing-case CLI exit policy regression")
    print("SELF-TEST PASS: missing requested case fails by default; --allow-missing permits authoring skips.")
    print(f"Self-tests: {len(passed)}/19 adversarial mutations rejected for the expected reasons.")
    print("All mutations stayed in memory; no model or reference files written.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=50)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--allow-missing", action="store_true",
                        help="Allow missing requested cases during authoring; default is to fail.")
    parser.add_argument("--self-test", action="store_true",
                        help="Run in-memory adversarial regressions against generated MM-001/031/032/035/040 fixtures.")
    args = parser.parse_args(argv)
    require(1 <= args.start <= args.end <= 50, "range must fall within MM-001..050")
    root = args.root.resolve()
    plan, tasks, sources = source_tables(root)
    spec = importlib.util.spec_from_file_location("mm_a_independent_diagnostic", root / "scripts/independent-frame-reference.py")
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    if args.self_test:
        return self_test(root, plan, tasks, sources, oracle)
    passed, failed, skipped = 0, [], []
    for number in range(args.start, args.end + 1):
        cid = f"MM-{number:03}"
        case_dir = root / "corpora/research-300/cases" / cid
        if not (case_dir / "contract.json").is_file():
            skipped.append(cid)
            continue
        try:
            counts = validate_case(case_dir, plan[cid], tasks[cid], sources[cid], oracle)
            passed += 1
            print(f"PASS {cid}: {counts['states']} states; {counts['selections']} selections; {counts['responses']} diagnostic responses", flush=True)
        except Exception as error:
            failed.append((cid, str(error)))
            print(f"FAIL {cid}: {type(error).__name__}: {error}", flush=True)
    print(f"Diagnostics: {passed} passed; {len(failed)} failed; {len(skipped)} not generated.")
    if skipped:
        print("Not generated: " + ", ".join(skipped))
    print("No reference values written. Independent diagnostics do not establish native or author-review acceptance.")
    return 1 if failed or not passed or (skipped and not args.allow_missing) else 0


if __name__ == "__main__":
    sys.exit(main())
