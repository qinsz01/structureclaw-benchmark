"""Native, linear-elastic OpenSees reference; no matrix or SUT solver imports.

All domains use XYZ coordinates and six DOFs. An xz model constrains its inactive
plane DOFs. Beam observation stations and load discontinuities become real nodes.
Linear distributed loads use three Gauss point *native element loads* per segment:
their work against the cubic beam shape functions is exact. Only segment-end
responses are exposed, never forces between those quadrature points.

Native execution is evidence, not an assertion of independently reviewed truth.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
from functools import lru_cache
import hashlib
import importlib
import importlib.metadata
import json
import math
from pathlib import Path
import subprocess
import sys


DOFS = ("ux", "uy", "uz", "rx", "ry", "rz")
FORCES = ("fx", "fy", "fz", "mx", "my", "mz")
ACTIONS = ("N", "V2", "V3", "T", "M2", "M3")
TRUSSES = ("truss", "brace")
VARYING_LOADS = ("distributed", "linear", "trapezoidal", "piecewise")
CONTROLS = ("self_weight", "rigid_floor", "p_delta", "rigid_offsets", "construction_stage")
ASSUMPTIONS = [
    "Linear elastic Euler-Bernoulli beams: elasticBeamColumn excludes shear deformation (not Timoshenko).",
    "Authored tolerances are preserved; this numerical run does not establish independently reviewed native truth.",
    "OpenSees results for a different planned engine are cross-engine diagnostics only.",
]


class NativeInputError(ValueError):
    """An input asks for unsupported or ambiguous structural mechanics."""


class NativeDependencyError(RuntimeError):
    """The real native OpenSees runtime is unavailable; no substitute was used."""


def number(value, label="value"):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NativeInputError(f"{label} must be a finite number")
    value = float(value)
    if not math.isfinite(value):
        raise NativeInputError(f"{label} must be finite")
    return value


def positive(value, label):
    value = number(value, label)
    if value <= 0:
        raise NativeInputError(f"{label} must be positive")
    return value


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def scale(a, value):
    return [x * value for x in a]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def norm(a):
    return math.sqrt(dot(a, a))


def unit(a, label):
    length = norm(a)
    if length < 1e-12:
        raise NativeInputError(f"{label} is zero or parallel to the member")
    return scale(a, 1 / length)


def local(vector, axes):
    return [dot(axis, vector) for axis in axes]


def global_vector(vector, axes):
    return [sum(vector[j] * axes[j][i] for j in range(3)) for i in range(3)]


def check_keys(record, allowed, label):
    unknown = set(record) - set(allowed)
    if unknown:
        raise NativeInputError(f"Unsupported {label} fields: {', '.join(sorted(unknown))}")


def indexed(records, label):
    if not isinstance(records, list):
        raise NativeInputError(f"{label} must be an array")
    result = {}
    for record in records:
        identifier = record.get("id") if isinstance(record, dict) else None
        if not isinstance(identifier, str) or not identifier or identifier in result:
            raise NativeInputError(f"Missing or duplicate {label} ID: {identifier!r}")
        result[identifier] = record
    return result


def axes_for(model, element, a, b):
    ex = unit(sub(b, a), f"Element {element['id']} length")
    if model["coordinate_system"]["dimension"] == "2d":
        ey = [0.0, 1.0, 0.0]
    elif element["type"] in TRUSSES:
        # Truss transverse axes are immaterial: only axial force is exposed.
        ref = [0.0, 0.0, 1.0] if abs(ex[2]) < .9 else [0.0, 1.0, 0.0]
        ey = unit(cross(ref, ex), "Truss axis")
    else:
        ref = model.get("metadata", {}).get("elementReferenceVectors", {}).get(element["id"])
        if not isinstance(ref, list) or len(ref) != 3:
            raise NativeInputError(f"3D beam {element['id']} requires explicit elementReferenceVectors")
        ey = unit(cross([number(v, "Reference vector") for v in ref], ex), "Reference vector")
    ez = cross(ex, ey)
    angle = math.radians(number(element.get("rotation_angle", 0), "rotation_angle"))
    # Principal-axis quarter turns exchange planar Iy/Iz without coupling
    # active and restrained bending DOFs; arbitrary rolls remain unsupported.
    if model["coordinate_system"]["dimension"] == "2d" and abs(math.sin(2*angle)) > 1e-12:
        raise NativeInputError("A rotated 2D section would couple inactive plane DOFs")
    c, s = math.cos(angle), math.sin(angle)
    return [ex, add(scale(ey, c), scale(ez, s)), add(scale(ez, c), scale(ey, -s))]


def station(value, length, label):
    value = number(value, label)
    if value < 0 or value > length + station_tolerance(length):
        raise NativeInputError(f"{label} lies outside member [0, {length}]")
    return min(value, length)


def station_tolerance(length):
    return 32 * sys.float_info.epsilon * max(1.0, length)


def distributed_pieces(load, length):
    """Normalize uniform, endpoint-linear, vertex and nonoverlapping segment loads.

    Canonical forms: wx/wy/wz; wx_start/wx_end (and y/z); points with
    position and wx/wy/wz; or segments with start/end and the same intensity
    fields. Segment gaps are unloaded. Piecewise jumps use adjacent segments.
    """
    common = {"id", "type", "element", "reference_frame", "variation", "distribution", "start", "end"}
    intensity = {f"w{d}{suffix}" for d in "xyz" for suffix in ("", "_start", "_end")}
    check_keys(load, common | intensity | {"points", "segments"}, "distributed load")
    variation = load.get("variation", load.get("distribution"))
    if "variation" in load and "distribution" in load and load["variation"] != load["distribution"]:
        raise NativeInputError("Conflicting load variation/distribution")
    if variation not in (None, "uniform", "linear", "piecewise", "piecewise_linear"):
        raise NativeInputError(f"Unsupported distributed load variation: {variation}")
    if "points" in load and "segments" in load:
        raise NativeInputError("A distributed load cannot contain both points and segments")
    if "points" in load:
        if set(load) & intensity or "start" in load or "end" in load:
            raise NativeInputError("Piecewise points cannot be mixed with outer intensities/bounds")
        points = load["points"]
        if not isinstance(points, list) or len(points) < 2:
            raise NativeInputError("A piecewise load needs at least two points")
        parsed = []
        for point in points:
            check_keys(point, {"position", "wx", "wy", "wz"}, "load point")
            x = station(point.get("position"), length, "Load point position")
            q = [number(point.get(f"w{d}", 0), "Load intensity") for d in "xyz"]
            if parsed and x <= parsed[-1][0]:
                raise NativeInputError("Piecewise load points must be strictly increasing; use segments for jumps")
            parsed.append((x, q))
        return [(a[0], b[0], a[1], b[1]) for a, b in zip(parsed, parsed[1:])]
    if "segments" in load:
        if set(load) & intensity or "start" in load or "end" in load:
            raise NativeInputError("Piecewise segments cannot be mixed with outer intensities/bounds")
        if not isinstance(load["segments"], list) or not load["segments"]:
            raise NativeInputError("A piecewise load needs nonempty segments")
        pieces = []
        for piece in load["segments"]:
            check_keys(piece, intensity | {"start", "end"}, "load segment")
            if "start" not in piece or "end" not in piece:
                raise NativeInputError("Each piecewise segment needs explicit start and end")
            pieces.extend(distributed_pieces(dict(piece, type="distributed"), length))
        pieces.sort(key=lambda p: p[0])
        if any(b[0] < a[1] for a, b in zip(pieces, pieces[1:])):
            raise NativeInputError("Overlapping segments are ambiguous; use separate loads")
        return pieces
    if load.get("type") == "piecewise" or variation in ("piecewise", "piecewise_linear"):
        raise NativeInputError("A piecewise load needs explicit points or segments")
    a = station(load.get("start", 0), length, "Distributed start")
    b = station(load.get("end", length), length, "Distributed end")
    if b <= a:
        raise NativeInputError("A distributed load must have positive loaded length")
    q0, q1 = [], []
    for d in "xyz":
        key = f"w{d}"
        endpoints = key + "_start" in load or key + "_end" in load
        if endpoints and (key in load or key + "_start" not in load or key + "_end" not in load):
            raise NativeInputError(f"Specify both {key}_start and {key}_end, without {key}")
        left = number(load.get(key + "_start", load.get(key, 0)), key)
        right = number(load.get(key + "_end", left), key + "_end")
        q0.append(left)
        q1.append(right)
    if variation == "uniform" and q0 != q1:
        raise NativeInputError("Uniform load has unequal endpoint intensities")
    return [(a, b, q0, q1)]


def prepare_model(model, factors, stations=()):
    """Validate physics and create an explicit native mesh/load description."""
    check_keys(model, {"schema_version", "unit_system", "coordinate_system", "nodes", "elements",
                       "materials", "sections", "load_cases", "load_combinations", "analysis_control",
                       "metadata", "stories"}, "model")
    if model.get("schema_version") != "2.2.0" or model.get("unit_system") != "SI":
        raise NativeInputError("Native reference requires model 2.2.0 in m/kN/MPa SI units")
    cs = model.get("coordinate_system", {})
    dimension = cs.get("dimension")
    if dimension not in ("2d", "3d") or cs.get("semantics") != "global-z-up":
        raise NativeInputError("Only explicit 2D xz / 3D XYZ Z-up models are supported")
    if cs.get("dof_order") != list(DOFS) or (dimension == "2d" and cs.get("plane") != "xz"):
        raise NativeInputError("Unsupported coordinate plane or DOF order")
    controls = model.get("analysis_control")
    if not isinstance(controls, dict):
        raise NativeInputError("Explicit analysis_control is required")
    check_keys(controls, CONTROLS, "analysis_control")
    for key in CONTROLS:
        if controls.get(key) is not False:
            raise NativeInputError(f"{key} must explicitly be false; that physics is unsupported")
    nodes = indexed(model.get("nodes"), "node")
    elements = indexed(model.get("elements"), "element")
    materials = indexed(model.get("materials"), "material")
    sections = indexed(model.get("sections"), "section")
    cases = indexed(model.get("load_cases"), "load case")
    if not nodes or not elements:
        raise NativeInputError("A native model needs nodes and elements")
    for case_id, factor in factors.items():
        if case_id not in cases:
            raise NativeInputError(f"Unknown load case in selection: {case_id}")
        number(factor, "Selection factor")
    plan = {"nodes": {}, "members": {}, "segments": [], "pointLoads": [], "nodalLoads": [],
            "dimension": dimension, "nativeNdm": 3, "nativeNdf": 6, "addedMass": 0.0}
    for name, node in nodes.items():
        check_keys(node, {"id", "name", "x", "y", "z", "restraints"}, "node")
        xyz = [number(node.get(d), "Node coordinate") for d in "xyz"]
        fixed = node.get("restraints")
        if not isinstance(fixed, list) or len(fixed) != 6 or any(type(v) is not bool for v in fixed):
            raise NativeInputError(f"Node {name} requires six boolean restraints")
        if dimension == "2d" and (abs(xyz[1]) > 1e-10 or not all(fixed[i] for i in (1, 3, 5))):
            raise NativeInputError("2D xz nodes require y=0 and restrained uy/rx/rz")
        plan["nodes"][name] = {"tag": len(plan["nodes"]) + 1, "xyz": xyz, "fixed": fixed[:],
                                "authoredFixed": fixed[:], "authored": True}
    frame_nodes = set()
    for name, element in elements.items():
        check_keys(element, {"id", "name", "type", "nodes", "material", "section", "rotation_angle"}, "element")
        if element.get("type") not in ("beam", "column", *TRUSSES):
            raise NativeInputError(f"Unsupported element type: {element.get('type')}")
        enodes = element.get("nodes")
        if not isinstance(enodes, list) or len(enodes) != 2 or any(n not in nodes for n in enodes):
            raise NativeInputError(f"Element {name} needs two existing nodes")
        if element.get("material") not in materials or element.get("section") not in sections:
            raise NativeInputError(f"Element {name} has an unknown material/section")
        mat, sec = materials[element["material"]], sections[element["section"]]
        check_keys(mat, {"id", "name", "type", "E", "G", "nu", "rho"}, "material")
        if mat.get("type") not in ("steel", "concrete", "elastic", "isotropic"):
            raise NativeInputError(f"Unsupported material constitutive type: {mat.get('type')}")
        check_keys(sec, {"id", "name", "type", "shape", "properties"}, "section")
        prop = sec.get("properties", {})
        check_keys(prop, {"A", "Iy", "Iz", "J"}, "section property")
        properties = {"E": positive(mat.get("E"), "E") * 1000, "A": positive(prop.get("A"), "A")}
        if element["type"] not in TRUSSES:
            properties.update(G=positive(mat.get("G"), "G") * 1000,
                              **{k: positive(prop.get(k), k) for k in ("Iy", "Iz", "J")})
            frame_nodes.update(enodes)
        a, b = [plan["nodes"][n]["xyz"] for n in enodes]
        length = positive(norm(sub(b, a)), "Member length")
        plan["members"][name] = {"element": deepcopy(element), "length": length,
                                  "axes": axes_for(model, element, a, b), "properties": properties,
                                  "cuts": {0.0, length}, "stationNodes": []}
    for name, node in plan["nodes"].items():
        if name not in frame_nodes:
            node["inactiveRotations"] = True
            node["fixed"][3:] = [True] * 3
    for location in stations:
        if location.get("kind") == "node":
            if location.get("id") not in nodes:
                raise NativeInputError("Requested node does not exist")
        elif location.get("kind") == "member":
            if location.get("id") not in elements:
                raise NativeInputError("Requested member does not exist")
            member = plan["members"][location["id"]]
            x = station(location.get("positionM"), member["length"], "Observation station")
            if location.get("side") not in ("left", "right"):
                raise NativeInputError("Member observations require explicit left/right side")
            if member["element"]["type"] not in TRUSSES:
                member["cuts"].add(x)
        else:
            raise NativeInputError("Unsupported observation location")
    prepared_loads = []
    # Validate every authored load, including cases whose selection factor is zero.
    for case_id, case in cases.items():
        check_keys(case, {"id", "name", "type", "loads"}, "load case")
        indexed(case.get("loads"), "load")
        factor = number(factors.get(case_id, 0), "Load factor")
        for load in case["loads"]:
            frame = load.get("reference_frame")
            kind = load.get("type")
            if frame not in ("global", "local", "element-local"):
                raise NativeInputError("Each load requires explicit global/local/element-local reference_frame")
            if frame == "element-local":
                frame = "local"
            if kind == "nodal":
                check_keys(load, {"id", "type", "node", "reference_frame", *FORCES}, "nodal load")
                if frame != "global" or load.get("node") not in nodes:
                    raise NativeInputError("Nodal loads need global axes and an existing node")
                values = [number(load.get(k, 0), k) for k in FORCES]
                if plan["nodes"][load["node"]].get("inactiveRotations") and any(values[3:]):
                    raise NativeInputError("A pure truss node cannot carry an applied moment")
                if dimension == "2d" and any(abs(values[i]) > 1e-12 for i in (1, 3, 5)):
                    raise NativeInputError("2D model contains out-of-plane loading")
                if factor:
                    plan["nodalLoads"].append({"node": load["node"], "values": scale(values, factor)})
            elif kind == "point" or kind in VARYING_LOADS:
                if load.get("element") not in elements:
                    raise NativeInputError("Member load references an unknown member")
                member = plan["members"][load["element"]]
                if member["element"]["type"] in TRUSSES:
                    raise NativeInputError("Truss member loads are unsupported; author loads at real joints")
                if kind == "point":
                    check_keys(load, {"id", "type", "element", "reference_frame", "position", *FORCES}, "member point load")
                    x = station(load.get("position"), member["length"], "Point load position")
                    values = [number(load.get(k, 0), k) for k in FORCES]
                    if frame == "local":
                        values = global_vector(values[:3], member["axes"]) + global_vector(values[3:], member["axes"])
                    if dimension == "2d" and any(abs(values[i]) > 1e-12 for i in (1, 3, 5)):
                        raise NativeInputError("2D member point load acts out of plane")
                    if factor:
                        member["cuts"].add(x)
                        prepared_loads.append({"kind": kind, "member": load["element"], "x": x, "values": scale(values, factor)})
                else:
                    for a, b, q0, q1 in distributed_pieces(load, member["length"]):
                        if frame == "local":
                            q0, q1 = global_vector(q0, member["axes"]), global_vector(q1, member["axes"])
                        if dimension == "2d" and (abs(q0[1]) > 1e-12 or abs(q1[1]) > 1e-12):
                            raise NativeInputError("2D distributed load acts out of plane")
                        if factor:
                            member["cuts"].update((a, b))
                            prepared_loads.append({"kind": "distributed", "member": load["element"], "a": a, "b": b,
                                                   "q0": scale(q0, factor), "q1": scale(q1, factor)})
            else:
                raise NativeInputError(f"Unsupported load type: {kind}")
    for name, member in plan["members"].items():
        element, length = member["element"], member["length"]
        a = plan["nodes"][element["nodes"][0]]["xyz"]
        cuts = sorted(0.0 if abs(x) <= station_tolerance(length) else
                      length if abs(x-length) <= station_tolerance(length) else x
                      for x in member.pop("cuts"))
        unique = []
        for x in cuts:
            if not unique or abs(x - unique[-1]) > station_tolerance(length):
                unique.append(x)
        for i, x in enumerate(unique):
            if i == 0:
                node_name = element["nodes"][0]
            elif i == len(unique) - 1:
                node_name = element["nodes"][1]
            else:
                node_name = f"__native_station_{len(plan['nodes']) + 1}"
                if node_name in nodes:
                    raise NativeInputError("Authored node ID collides with native observation ID")
                plan["nodes"][node_name] = {"tag": len(plan["nodes"]) + 1,
                    "xyz": add(a, scale(member["axes"][0], x)), "authored": False,
                    "fixed": [False, True, False, True, False, True] if dimension == "2d" else [False] * 6}
            member["stationNodes"].append([x, node_name])
            if i:
                prev_x, prev_name = member["stationNodes"][-2]
                plan["segments"].append({"tag": len(plan["segments"]) + 1, "member": name,
                    "start": prev_x, "end": x, "nodes": [prev_name, node_name]})
    for load in prepared_loads:
        member = plan["members"][load["member"]]
        if load["kind"] == "point":
            node = nearest_station(member, load["x"])
            plan["nodalLoads"].append({"node": node, "values": load["values"]})
            continue
        for segment in plan["segments"]:
            if segment["member"] != load["member"]:
                continue
            a, b = segment["start"], segment["end"]
            if not load["a"] < (a + b)/2 < load["b"]:
                continue
            # Three-point Gauss-Legendre exactly integrates linear load times
            # cubic beam virtual displacement, including distributed axial load.
            for xi, weight in ((-math.sqrt(3/5), 5/9), (0, 8/9), (math.sqrt(3/5), 5/9)):
                x = (a+b)/2 + xi*(b-a)/2
                t = (x-load["a"])/(load["b"]-load["a"])
                q = add(scale(load["q0"], 1-t), scale(load["q1"], t))
                force = scale(q, weight*(b-a)/2)
                plan["pointLoads"].append({"elementTag": segment["tag"], "fraction": (x-a)/(b-a),
                                           "globalForce": force, "localForce": local(force, member["axes"]),
                                           "xyz": add(plan["nodes"][member["element"]["nodes"][0]]["xyz"],
                                                      scale(member["axes"][0], x))})
    return plan


def nearest_station(member, x):
    where, node = min(member["stationNodes"], key=lambda item: abs(item[0] - x))
    if abs(where - x) > station_tolerance(member["length"]):
        raise NativeInputError("Requested beam station was not connected to the native mesh")
    return node


@lru_cache(maxsize=1)
def native_runtime():
    """Probe in a child process: some MPI builds abort during import."""
    code = """import importlib, json
try:
    ops = importlib.import_module('openseespy.opensees')
except ModuleNotFoundError as error:
    if error.name not in ('openseespy', 'openseespy.opensees'):
        raise
    ops = importlib.import_module('openseespylinux.opensees')
print('NATIVE_RUNTIME=' + json.dumps({'module': ops.__name__, 'version': ops.version()}))
"""
    try:
        probe = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NativeDependencyError(f"Native OpenSees preflight failed: {exc}") from exc
    marker = next((line.removeprefix("NATIVE_RUNTIME=") for line in probe.stdout.splitlines()
                   if line.startswith("NATIVE_RUNTIME=")), None)
    if probe.returncode != 0 or marker is None:
        detail = (probe.stderr or probe.stdout).strip()[-3000:]
        raise NativeDependencyError("Native OpenSeesPy is unavailable or failed its isolated import probe. "
                                    "Install a working OpenSeesPy runtime in an isolated environment. "
                                    f"No numerical fallback was used. Exit {probe.returncode}: {detail}")
    info = json.loads(marker)
    return importlib.import_module(info["module"]), info


def build_domain(ops, plan):
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)
    for node in plan["nodes"].values():
        ops.node(node["tag"], *node["xyz"])
        ops.fix(node["tag"], *[int(f) for f in node["fixed"]])
    for segment in plan["segments"]:
        member = plan["members"][segment["member"]]
        p, tag = member["properties"], segment["tag"]
        n1, n2 = [plan["nodes"][n]["tag"] for n in segment["nodes"]]
        if member["element"]["type"] in TRUSSES:
            ops.uniaxialMaterial("Elastic", tag, p["E"])
            ops.element("truss", tag, n1, n2, p["A"], tag)
        else:
            ops.geomTransf("Linear", tag, *member["axes"][2])
            ops.element("elasticBeamColumn", tag, n1, n2, p["A"], p["E"], p["G"],
                        p["J"], p["Iy"], p["Iz"], tag)
    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    for load in plan["nodalLoads"]:
        ops.load(plan["nodes"][load["node"]]["tag"], *load["values"])
    for load in plan["pointLoads"]:
        px, py, pz = load["localForce"]
        ops.eleLoad("-ele", load["elementTag"], "-type", "-beamPoint", py, pz, load["fraction"], px)


def response_reader(plan, raw):
    """Read only saved native responses, never calculate stiffness or end actions."""
    def quantity(location, component):
        kind = location.get("kind")
        if kind == "node":
            node = raw["nodes"].get(location.get("id"))
            if node is None:
                raise NativeInputError("Unknown node response")
            if component in DOFS:
                source = plan["nodes"][location["id"]]
                if (component in DOFS[3:] and source.get("inactiveRotations")
                        and not source["authoredFixed"][DOFS.index(component)]):
                    raise NativeInputError("Pure truss node rotations are not physical response quantities")
                return node["displacement"][DOFS.index(component)]
            if component.lower() in FORCES:
                return node["reaction"][FORCES.index(component.lower())]
            raise NativeInputError(f"Unsupported nodal component {component}")
        if kind != "member" or location.get("id") not in plan["members"]:
            raise NativeInputError("Unknown member response")
        name = location["id"]
        member = plan["members"][name]
        x = station(location.get("positionM"), member["length"], "Response station")
        if location.get("side") not in ("left", "right"):
            raise NativeInputError("Member force responses require left/right side")
        truss = member["element"]["type"] in TRUSSES
        if component in DOFS:
            if truss:
                if component not in DOFS[:3]:
                    raise NativeInputError("Truss rotations are not physical response quantities")
                # Exact displacement field of the native linear truss; no
                # artificial intermediate joints or transverse mechanisms.
                n1, n2 = member["element"]["nodes"]
                t, index = x/member["length"], DOFS.index(component)
                return ((1-t)*raw["nodes"][n1]["displacement"][index]
                        + t*raw["nodes"][n2]["displacement"][index])
            return raw["nodes"][nearest_station(member, x)]["displacement"][DOFS.index(component)]
        if component not in ACTIONS:
            raise NativeInputError(f"Unsupported member component {component}")
        tolerance = station_tolerance(member["length"])
        segments = [s for s in plan["segments"] if s["member"] == name
                    and s["start"]-tolerance <= x <= s["end"]+tolerance]
        segment = segments[0] if location["side"] == "left" else segments[-1]
        result = raw["elements"][str(segment["tag"])]
        if truss:
            return result["axialForce"] if component == "N" else 0.0
        at_start = abs(x-segment["start"]) <= tolerance
        if not at_start and abs(x-segment["end"]) > tolerance:
            raise NativeInputError("Beam action requested away from a native observation node")
        i = ACTIONS.index(component)
        signs = (-1, 1, 1, -1, -1, -1) if at_start else (1, -1, -1, 1, 1, 1)
        return result["localForce"][i + (0 if at_start else 6)] * signs[i]
    return quantity


def equilibrium_checks(plan, raw):
    external, reactions = [0.0]*6, [0.0]*6
    scales = [0.0]*6
    for load in plan["nodalLoads"]:
        force = load["values"]
        xyz = plan["nodes"][load["node"]]["xyz"]
        resultant = force[:3] + add(force[3:], cross(xyz, force[:3]))
        external = add(external, resultant)
        scales = add(scales, [abs(v) for v in resultant])
    for load in plan["pointLoads"]:
        resultant = load["globalForce"] + cross(load["xyz"], load["globalForce"])
        external = add(external, resultant)
        scales = add(scales, [abs(v) for v in resultant])
    free_residual = 0.0
    for name, node in plan["nodes"].items():
        reaction = raw["nodes"][name]["reaction"]
        reactions = add(reactions, reaction[:3] + add(reaction[3:], cross(node["xyz"], reaction[:3])))
        free_residual = max(free_residual, max((abs(r) for r, fixed in zip(reaction, node["fixed"]) if not fixed), default=0))
    balance = add(external, reactions)
    bounds = [1e-8 + 1e-7*max(1.0, s) for s in scales]
    passed = all(abs(v) <= bound for v, bound in zip(balance, bounds))
    passed = passed and free_residual <= max(bounds)
    return {"method": "native-openseespy", "forceMomentBalance": balance, "balanceTolerance": bounds,
            "freeResidual": free_residual, "equilibriumPassed": passed,
            "nativeNodes": len(plan["nodes"]), "nativeElements": len(plan["segments"]),
            "addedMass": 0.0, "massPolicy": "No nodal or element mass; linear static, self_weight=false",
            "loadIntegration": "Three-point Gauss native beamPoint loads; exact linear-load work at segment endpoints",
            "stationPolicy": "Connected beam observation nodes; exact native linear-truss interpolation",
            "assumptions": ASSUMPTIONS[:]}


def solve(model, factors, stations=()):
    """Return (quantity(location, component), checks, raw) after a real native solve."""
    plan = prepare_model(model, factors, stations)
    ops, runtime = native_runtime()
    try:
        build_domain(ops, plan)
        ops.constraints("Plain")
        ops.numberer("RCM")
        ops.system("BandGeneral")
        ops.algorithm("Linear")
        ops.integrator("LoadControl", 1.0)
        ops.analysis("Static")
        status = ops.analyze(1)
        if status != 0:
            raise NativeInputError(f"Native OpenSees analyze failed ({status}); check stability/constraints")
        ops.reactions()
        raw = {"runtime": runtime, "analysisReturnCode": status, "nodes": {}, "elements": {}, "nativeInput": plan}
        for name, node in plan["nodes"].items():
            disp, reaction = list(ops.nodeDisp(node["tag"])), list(ops.nodeReaction(node["tag"]))
            if len(disp) != 6 or len(reaction) != 6:
                raise NativeInputError("Native node response has unexpected DOF count")
            raw["nodes"][name] = {"tag": node["tag"], "displacement": disp, "reaction": reaction}
        for segment in plan["segments"]:
            tag = segment["tag"]
            truss = plan["members"][segment["member"]]["element"]["type"] in TRUSSES
            if truss:
                force = list(ops.eleResponse(tag, "axialForce"))
                if len(force) != 1:
                    raise NativeInputError("Native truss did not expose an axialForce response")
                result = {"axialForce": force[0], "globalForce": list(ops.eleForce(tag))}
            else:
                force = list(ops.eleResponse(tag, "localForce"))
                if len(force) != 12:
                    raise NativeInputError("Native beam did not expose twelve local end actions")
                result = {"localForce": force, "globalForce": list(ops.eleForce(tag))}
            raw["elements"][str(tag)] = result
        # JSON serialization rejects NaN/Infinity before responses can become evidence.
        json.dumps(raw, allow_nan=False)
        checks = equilibrium_checks(plan, raw)
        if not checks["equilibriumPassed"]:
            raise NativeInputError(f"Native equilibrium check failed: {checks}")
        return response_reader(plan, raw), checks, raw
    finally:
        ops.wipe()


def generate(case_dir, output_root):
    try:
        from .reference_io import (load_case_inputs, selection_factors, quantity_unit,
                                   convert_value, evaluate_derived, write_json_exclusive)
    except ImportError:
        from reference_io import (load_case_inputs, selection_factors, quantity_unit,
                                  convert_value, evaluate_derived, write_json_exclusive)
    case = load_case_inputs(case_dir)
    target = Path(output_root) / case["id"]
    names = ("native-input-receipt.json", "native-solver-receipt.json", "native-raw-responses.json",
             "native-checks.json", "native-opensees-reference.json")
    for name in names:
        if (target / name).exists() or (target / name).is_symlink():
            raise FileExistsError(f"Native reference artifact already exists: {target / name}")
    state_results, raw_results, check_results = [], [], []
    for state in case["states"]:
        grouped = defaultdict(list)
        for request in state["quantities"]:
            selection = request["selection"]
            grouped[(selection["kind"], selection["id"])].append(request)
        if not grouped:
            raise NativeInputError(f"State {state['state']} has no numerical requests; no native run can be evidenced")
        results, state_checks = [], []
        for (kind, identifier), requests in grouped.items():
            selection = {"kind": kind, "id": identifier}
            factors = selection_factors(state["model"], selection)
            read, checks, raw = solve(state["model"], factors, [q["location"] for q in requests])
            for request in requests:
                value = read(request["location"], request["component"])
                value = convert_value(value, quantity_unit(request["component"]), request["unit"])
                results.append(dict(deepcopy(request), value=value))
            state_checks.append(dict(checks, selection=selection))
            raw_results.append({"state": state["state"], "selection": selection, "factors": factors, "responses": raw})
            check_results.append({"state": state["state"], "selection": selection, "checks": checks})
        state_results.append({"state": state["state"], "model": state["modelPath"], "quantities": results,
                              "derived": evaluate_derived(results, state["derived"]), "checks": state_checks})
    _, runtime = native_runtime()
    runner_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    info = dict(runtime, python=sys.version, runnerSha256=runner_hash)
    info["referenceIoSha256"] = hashlib.sha256(Path(__file__).with_name("reference_io.py").read_bytes()).hexdigest()
    native_module = importlib.import_module(runtime["module"])
    module_file = getattr(native_module, "__file__", None)
    if module_file and Path(module_file).is_file():
        info["nativeModuleSha256"] = hashlib.sha256(Path(module_file).read_bytes()).hexdigest()
    # openseespy.opensees may be a Python re-export wrapper. Bind the module
    # implementing the native version function, not just that wrapper's bytes.
    implementation_name = getattr(getattr(native_module, "version", None), "__module__", native_module.__name__)
    implementation = importlib.import_module(implementation_name)
    binary_file = getattr(implementation, "__file__", None)
    if binary_file and Path(binary_file).is_file():
        info["nativeBinaryModule"] = implementation.__name__
        info["nativeBinarySha256"] = hashlib.sha256(Path(binary_file).read_bytes()).hexdigest()
    for package in ("openseespy", "openseespylinux"):
        try:
            info[package + "PackageVersion"] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            pass
    document = {"schemaVersion": 1, "id": case["id"], "modelId": case["contract"].get("modelId", case["id"]),
                "referenceKind": "native-opensees", "method": "native-openseespy", "solver": info, "inputHashes": case["hashes"],
                "sourceHash": case["sourceHash"], "sourceManifest": case["sourceManifest"],
                "sameEngineTruthStatus": "pending", "nativeIndependentReview": "pending", "llmEndToEnd": "not-run",
                "nativeRole": "same-engine-candidate" if case["contract"].get("plannedEngine") == "OpenSees" else "cross-engine-diagnostic",
                "warnings": ASSUMPTIONS[:],
                "checks": [dict(r["checks"], state=r["state"], selection=r["selection"]) for r in check_results],
                "states": state_results}
    receipts = [
        {"schemaVersion": 1, "id": case["id"], "inputHashes": case["hashes"],
         "sourceHash": case["sourceHash"], "sourceManifest": case["sourceManifest"],
         "states": [{"state": s["state"], "model": s["model"], "modelPath": s["modelPath"]} for s in case["states"]]},
        {"schemaVersion": 1, "id": case["id"], "solver": info, "analysis": "Linear elastic static",
         "assumptions": ASSUMPTIONS[:],
         "units": {"length": "m", "force": "kN", "modulusInput": "MPa", "rotation": "rad"}},
        {"schemaVersion": 1, "id": case["id"], "runs": raw_results},
        {"schemaVersion": 1, "id": case["id"], "runs": check_results}]
    artifacts = []
    for name, payload in zip(names[:-1], receipts):
        artifact = write_json_exclusive(target / name, payload)
        artifacts.append({"path": name, "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()})
    document["artifacts"] = artifacts
    return write_json_exclusive(target / names[-1], document)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        output = generate(args.case_dir, args.output_root)
    except (ValueError, RuntimeError, OSError, KeyError) as exc:
        print(f"Native reference failed: {exc}", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
