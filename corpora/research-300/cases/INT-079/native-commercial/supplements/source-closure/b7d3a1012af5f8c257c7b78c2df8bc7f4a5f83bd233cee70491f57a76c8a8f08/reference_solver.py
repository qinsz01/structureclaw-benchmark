"""Independent, static direct-stiffness reference mechanics (EB by default).

Units are m, kN, radians, with authored E/G in MPa. No SUT/native imports.
Every requested frame station and load discontinuity is an actual mesh node.
Linear distributed loads use exact polynomial consistent nodal loads, so the
solution at these stations includes the load particular solution (not visual
interpolation). One stiffness factorization serves all selected cases/combos.
Explicit per-member effective shear areas opt into a Timoshenko diagnostic
mode, limited to point/nodal and piecewise-constant distributed loads.
"""
from __future__ import annotations

import math
import numpy as np

try:
    import scipy.sparse as sparse
    from scipy.sparse.linalg import splu
except ImportError:  # Small models can run with only NumPy.
    sparse = None

DISPLACEMENTS = ("ux", "uy", "uz", "rx", "ry", "rz")
REACTIONS = ("fx", "fy", "fz", "mx", "my", "mz")
ACTIONS = ("N", "V2", "V3", "T", "M2", "M3")
TRUSS = ("truss", "brace")
ASSUMPTIONS = [
    "Linear elastic, small-displacement Euler-Bernoulli bending; shear deformation is omitted.",
    "EB and Timoshenko displacements can differ physically; request tolerances are not adjusted.",
    "No mass is added by observation/load subdivision; this solver performs static analysis only.",
    "Commercial-engine comparisons are diagnostic, not same-engine native truth.",
]


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def indexed(records, label):
    result = {}
    for record in records:
        key = record.get("id")
        if not isinstance(key, str) or not key or key in result:
            raise ValueError(f"Missing/duplicate {label} id: {key!r}")
        result[key] = record
    return result


def _keys(record, supported, label):
    extra = set(record)-set(supported)
    if extra:
        raise ValueError(f"Unsupported {label} fields: {sorted(extra)}")


def _in_member(x, length):
    eps = 32*np.finfo(float).eps*max(1., length)
    return -eps <= x <= length+eps


def _nonzero(value):
    if isinstance(value, dict):
        return any(_nonzero(x) for x in value.values())
    if isinstance(value, (list, tuple)):
        return any(_nonzero(x) for x in value)
    return value not in (None, False, 0, "", "none", "linear", "elastic")


def axes(model, element, a, b):
    ex = (b - a) / np.linalg.norm(b - a)
    if model["coordinate_system"]["dimension"] == "2d":
        ey = np.array([0., 1., 0.])
        if abs(ex[1]) > 1e-12:
            raise ValueError("2d xz element is not in the xz plane")
        ez = np.cross(ex, ey)
    else:
        ref = model.get("metadata", {}).get("elementReferenceVectors", {}).get(element["id"])
        if ref is None and element["type"] in TRUSS:
            # Only axial truss stiffness is used; transverse basis is immaterial.
            ref = [0., 0., 1.] if abs(ex[2]) < .9 else [0., 1., 0.]
        if ref is None or len(ref) != 3:
            raise ValueError(f"Explicit elementReferenceVectors required for 3d member {element['id']}")
        ref = np.array([number(x, "reference vector") for x in ref])
        ey = np.cross(ref, ex)
        if np.linalg.norm(ey) < 1e-12 * max(1., np.linalg.norm(ref)):
            raise ValueError("Element reference vector is parallel to member axis")
        ey /= np.linalg.norm(ey)
        ez = np.cross(ex, ey)
    angle = math.radians(number(element.get("rotation_angle", 0), "rotation_angle"))
    ey, ez = math.cos(angle)*ey + math.sin(angle)*ez, -math.sin(angle)*ey + math.cos(angle)*ez
    return np.vstack((ex, ey, ez))


def local_stiffness(element, material, section, length, shear_areas=None):
    E = material["E"] * 1000.
    p = section["properties"]
    k = np.zeros((12, 12))
    k[np.ix_([0, 6], [0, 6])] = E*p["A"]/length * np.array([[1., -1.], [-1., 1.]])
    if element["type"] in TRUSS:
        return k
    k[np.ix_([3, 9], [3, 9])] = material["G"]*1000.*p["J"]/length * np.array([[1., -1.], [-1., 1.]])
    for dofs, inertia, sign, area_key in (([1, 5, 7, 11], p["Iz"], 1, "Asy"),
                                         ([2, 4, 8, 10], p["Iy"], -1, "Asz")):
        L = length
        c = 6*L*sign
        phi = 0.
        if shear_areas is not None:
            EI = E*inertia
            GA = material["G"]*1000.*shear_areas[area_key]
            try:
                phi = 12*(EI/GA)/L/L
            except ZeroDivisionError as exc:
                raise ValueError("Finite-shear stiffness is outside numeric range") from exc
            if any(not math.isfinite(x) or x <= 0 for x in (EI, GA, phi)):
                raise ValueError("Finite-shear stiffness is outside numeric range")
        k[np.ix_(dofs, dofs)] = E*inertia/L**3/(1+phi) * np.array([
            [12, c, -12, c], [c, (4+phi)*L*L, -c, (2-phi)*L*L],
            [-12, -c, 12, -c], [c, (2-phi)*L*L, -c, (4+phi)*L*L]])
    if shear_areas is not None and not np.all(np.isfinite(k)):
        raise ValueError("Finite-shear stiffness is outside numeric range")
    return k


def _load_pieces(load, length):
    """Return (start, end, q_start, q_end), in the specified reference frame."""
    allowed = {"id", "type", "element", "reference_frame", "start", "end", "distribution", "variation", "points", "segments"}
    allowed.update(f"w{a}{suffix}" for a in "xyz" for suffix in ("", "_start", "_end"))
    extra = set(load) - allowed
    if extra:
        raise ValueError(f"Unsupported distributed load fields: {sorted(extra)}")
    distribution = load.get("distribution", load.get("variation", "uniform"))
    if "distribution" in load and "variation" in load and load["distribution"] != load["variation"]:
        raise ValueError("Conflicting load distribution/variation")
    if distribution not in ("uniform", "linear", "piecewise", "piecewise_linear"):
        raise ValueError("Unsupported distributed load distribution")
    if "segments" in load:
        if "points" in load or any(f"w{a}{suffix}" in load for a in "xyz" for suffix in ("", "_start", "_end")):
            raise ValueError("Ambiguous piecewise segments and load values")
        if not isinstance(load["segments"], list) or not load["segments"]:
            raise ValueError("Piecewise load requires nonempty segments")
        pieces = []
        for segment in load["segments"]:
            if "start" not in segment or "end" not in segment or set(segment)-{"start", "end", *(f"w{a}{suffix}" for a in "xyz" for suffix in ("", "_start", "_end"))}:
                raise ValueError("Piecewise segments need explicit start/end and supported intensities")
            pieces.extend(_load_pieces(dict(segment, type="distributed"), length))
        if any(a < previous[1] for previous, (a, _, _, _) in zip(pieces, pieces[1:])):
            raise ValueError("Piecewise segments must be ordered and nonoverlapping")
        if "start" in load and load["start"] != pieces[0][0] or "end" in load and load["end"] != pieces[-1][1]:
            raise ValueError("Piecewise overall start/end disagree with segments")
        return pieces
    if "points" in load:
        if any(f"w{a}{suffix}" in load for a in "xyz" for suffix in ("", "_start", "_end")):
            raise ValueError("Ambiguous piecewise and endpoint load values")
        points = load["points"]
        if not isinstance(points, list) or len(points) < 2:
            raise ValueError("Piecewise load needs at least two ordered points")
        values = []
        for p in points:
            if set(p) - {"position", "wx", "wy", "wz"}:
                raise ValueError("Unsupported piecewise point field")
            x = number(p["position"], "piecewise position")
            q = np.array([number(p.get("w"+a, 0), "piecewise intensity") for a in "xyz"])
            values.append((x, q))
        if "start" in load and number(load["start"], "start") != values[0][0]:
            raise ValueError("Piecewise start disagrees with first point")
        if "end" in load and number(load["end"], "end") != values[-1][0]:
            raise ValueError("Piecewise end disagrees with last point")
    else:
        if load["type"] == "piecewise" or distribution in ("piecewise", "piecewise_linear"):
            raise ValueError("Piecewise load requires points")
        a = number(load.get("start", 0), "load start")
        b = number(load.get("end", length), "load end")
        qa, qb = [], []
        for axis in "xyz":
            key = "w"+axis
            endpoints = key+"_start" in load or key+"_end" in load
            if endpoints and (key in load or key+"_start" not in load or key+"_end" not in load):
                raise ValueError(f"Specify both {key}_start and {key}_end, without {key}")
            qa.append(number(load.get(key+"_start", load.get(key, 0)), key))
            qb.append(number(load.get(key+"_end", load.get(key, 0)), key))
        values = [(a, np.array(qa)), (b, np.array(qb))]
        if ("distribution" in load or "variation" in load) and distribution == "uniform" and qa != qb:
            raise ValueError("Explicit uniform load has unequal endpoint intensities")
    pieces = []
    for (a, qa), (b, qb) in zip(values, values[1:]):
        if not a < b or not _in_member(a, length) or not _in_member(b, length):
            raise ValueError(f"Load interval [{a}, {b}] outside member [0, {length}] or not increasing")
        pieces.append((a, b, qa, qb))
    return pieces


def _consistent_load(qa, qb, L):
    """Closed-form integration of linear intensity with axial/Hermite shapes."""
    f = np.zeros(12)
    f[0], f[6] = L*(2*qa[0]+qb[0])/6, L*(qa[0]+2*qb[0])/6
    for axis, rotation, sign in ((1, 5, 1), (2, 4, -1)):
        a, b = qa[axis], qb[axis]
        f[axis] = L*(7*a+3*b)/20
        f[axis+6] = L*(3*a+7*b)/20
        f[rotation] = sign*L*L*(3*a+2*b)/60
        f[rotation+6] = -sign*L*L*(2*a+3*b)/60
    return f


def _validate(model):
    _keys(model, {"schema_version", "unit_system", "coordinate_system", "nodes", "elements", "materials", "sections",
                  "load_cases", "load_combinations", "analysis_control", "metadata", "stories",
                  "constraints", "rigid_links", "diaphragms", "springs", "support_settlements", "stages"}, "model")
    if model.get("schema_version") != "2.2.0" or model.get("unit_system") != "SI":
        raise ValueError("Requires model protocol 2.2.0 with SI m/kN/MPa units")
    cs = model.get("coordinate_system", {})
    if cs.get("dimension") not in ("2d", "3d") or (cs["dimension"] == "2d" and cs.get("plane") != "xz"):
        raise ValueError("Only XYZ Z-up 3d or 2d xz models supported")
    if cs.get("semantics", "global-z-up") != "global-z-up" or cs.get("dof_order", list(DISPLACEMENTS)) != list(DISPLACEMENTS):
        raise ValueError("Unsupported coordinate/DOF convention")
    controls = model.get("analysis_control")
    if not isinstance(controls, dict):
        raise ValueError("Explicit analysis_control is required")
    control_keys = {"self_weight", "rigid_floor", "p_delta", "rigid_offsets", "construction_stage"}
    _keys(controls, control_keys, "analysis_control")
    if any(controls.get(key) is not False for key in control_keys):
        raise ValueError("Every supported analysis_control must explicitly be false")
    for key, val in controls.items():
        if _nonzero(val):
            raise ValueError(f"Unsupported analysis_control {key}={val!r}; requires linear static explicit loads")
    for key in ("constraints", "rigid_links", "diaphragms", "springs", "support_settlements", "stages"):
        if _nonzero(model.get(key)):
            raise ValueError(f"Unsupported model physics: {key}")
    nodes = indexed(model["nodes"], "node")
    elements = indexed(model["elements"], "element")
    materials = indexed(model["materials"], "material")
    sections = indexed(model["sections"], "section")
    cases = indexed(model["load_cases"], "load case")
    if not nodes or not elements:
        raise ValueError("Model must have nodes and elements")
    xyz, restraints, lengths, rotations = {}, {}, {}, {}
    for name, n in nodes.items():
        _keys(n, {"id", "name", "x", "y", "z", "restraints", "springs", "settlements", "prescribed_displacements", "constraints"}, "node")
        xyz[name] = np.array([number(n[a], f"node {name} {a}") for a in "xyz"])
        r = n.get("restraints")
        if not isinstance(r, list) or len(r) != 6 or any(type(x) is not bool for x in r):
            raise ValueError("Node restraints must be six explicit booleans")
        restraints[name] = r[:]
        if cs["dimension"] == "2d" and not all(r[i] for i in (1, 3, 5)):
            raise ValueError("2d xz nodes require uy/rx/rz restraints")
        for key in ("springs", "settlements", "prescribed_displacements", "constraints"):
            if _nonzero(n.get(key)):
                raise ValueError(f"Unsupported node {key}")
    for name, e in elements.items():
        _keys(e, {"id", "name", "type", "nodes", "material", "section", "rotation_angle",
                  "releases", "release", "end_releases", "offsets", "rigid_offsets", "tension_only",
                  "compression_only", "shear_deformation", "nonlinear", "taper"}, "element")
        if e.get("type") not in ("beam", "column", "frame", *TRUSS):
            raise ValueError(f"Unsupported element type: {e.get('type')}")
        for key in ("releases", "release", "end_releases", "offsets", "rigid_offsets", "tension_only", "compression_only", "shear_deformation", "nonlinear", "taper"):
            if _nonzero(e.get(key)):
                raise ValueError(f"Unsupported element physics: {key}")
        pair = e.get("nodes", [])
        if len(pair) != 2 or any(n not in nodes for n in pair):
            raise ValueError("Element must connect two existing nodes")
        L = float(np.linalg.norm(xyz[pair[1]] - xyz[pair[0]]))
        if not math.isfinite(L) or L <= 1e-12:
            raise ValueError("Zero-length/nonfinite element")
        if e.get("material") not in materials or e.get("section") not in sections:
            raise ValueError("Unknown material or section")
        m, sec = materials[e["material"]], sections[e["section"]]
        _keys(m, {"id", "name", "type", "E", "G", "nu", "rho", "nonlinear", "plasticity", "orthotropic", "constitutive_model"}, "material")
        _keys(sec, {"id", "name", "type", "shape", "properties"}, "section")
        _keys(sec["properties"], {"A", "Iy", "Iz", "J", "Iyz"}, "section properties")
        for prop in ("E",) if e["type"] in TRUSS else ("E", "G"):
            if number(m[prop], prop) <= 0:
                raise ValueError(f"{prop} must be positive")
        if m.get("type", "steel") not in ("steel", "concrete", "elastic", "isotropic", "timber", "aluminum", "other", "custom"):
            raise ValueError("Unsupported nonlinear/anisotropic material")
        for key in ("nonlinear", "plasticity", "orthotropic", "constitutive_model"):
            if _nonzero(m.get(key)):
                raise ValueError(f"Unsupported material {key}")
        for prop in ("A",) if e["type"] in TRUSS else ("A", "Iy", "Iz", "J"):
            if number(sec["properties"][prop], prop) <= 0:
                raise ValueError(f"Section {prop} must be positive")
        if _nonzero(sec["properties"].get("Iyz", 0)):
            raise ValueError("Coupled section inertia Iyz is unsupported; specify principal axes")
        lengths[name], rotations[name] = L, axes(model, e, *[xyz[n] for n in pair])
    loads = []
    for cid, case in cases.items():
        _keys(case, {"id", "name", "type", "loads"}, "load case")
        for load in case.get("loads", []):
            typ = load.get("type")
            frame = load.get("reference_frame", "global")
            # Protocol uses element-local; retain local as the established alias.
            # Nodal loads have no unique member basis and must remain global.
            if frame not in ("global", "element-local", "local") or (typ == "nodal" and frame != "global"):
                raise ValueError("Unsupported load reference_frame")
            item = dict(case=cid, load=load, type=typ)
            if typ == "nodal":
                if load.get("node") not in nodes:
                    raise ValueError("Nodal load references unknown node")
            elif typ in ("point", "distributed", "linear", "trapezoidal", "piecewise"):
                eid = load.get("element")
                if eid not in elements:
                    raise ValueError("Load references unknown element")
                if elements[eid]["type"] in TRUSS:
                    raise ValueError("Truss member loads unsupported; author equivalent physical joint loads explicitly")
                if typ == "point":
                    x = number(load["position"], "point position")
                    if not _in_member(x, lengths[eid]):
                        raise ValueError("Point load outside member")
                    item["position"] = x
                else:
                    item["pieces"] = _load_pieces(load, lengths[eid])
                    if cs["dimension"] == "2d":
                        for _, _, qa, qb in item["pieces"]:
                            for q in (qa, qb):
                                global_q = q if frame == "global" else rotations[eid].T@q
                                if abs(global_q[1]) > 1e-12*max(1., np.linalg.norm(q)):
                                    raise ValueError("2d model has out-of-plane distributed loading")
            else:
                raise ValueError(f"Unsupported load type: {typ}")
            if typ in ("nodal", "point"):
                allowed = {"id", "type", "reference_frame", "node", "element", "position", *REACTIONS}
                if set(load) - allowed:
                    raise ValueError(f"Unsupported {typ} load fields: {sorted(set(load)-allowed)}")
                item["vector"] = np.array([number(load.get(k, 0), k) for k in REACTIONS])
                if typ == "point" and frame in ("element-local", "local"):
                    R = rotations[load["element"]]
                    item["vector"] = np.r_[R.T@item["vector"][:3], R.T@item["vector"][3:]]
                if cs["dimension"] == "2d" and any(abs(item["vector"][i]) > 1e-12*max(1., np.linalg.norm(item["vector"])) for i in (1, 3, 5)):
                    raise ValueError("2d model has out-of-plane force/moment loading")
            loads.append(item)
    return nodes, elements, materials, sections, cases, xyz, restraints, lengths, rotations, loads


def _shear_areas(records, elements, loads):
    """Copy explicit SI areas; never infer them from section geometry or names."""
    frames = {eid for eid, e in elements.items() if e["type"] not in TRUSS}
    if not isinstance(records, dict) or set(records) != frames:
        raise ValueError("Effective shear areas require exactly all frame member IDs")
    result = {}
    for eid, record in records.items():
        if not isinstance(record, dict) or set(record) != {"Asy", "Asz"}:
            raise ValueError(f"Effective shear areas for {eid} require exactly Asy and Asz")
        result[eid] = {key: number(value, f"{eid}.{key}") for key, value in record.items()}
        if any(value <= 0 for value in result[eid].values()):
            raise ValueError(f"Effective shear areas for {eid} must be positive m² values")
    for item in loads:
        if any(not np.array_equal(qa, qb) for _, _, qa, qb in item.get("pieces", [])):
            raise ValueError("Finite-shear audit supports only piecewise-constant distributed loads")
    return result


def solve(model, factors, stations, *, effective_shear_areas=None):
    return solve_many(model, [factors], stations, effective_shear_areas=effective_shear_areas)[0]


def solve_many(model, factors_list, stations, *, effective_shear_areas=None):
    """Solve selections in one factorization; factors map load-case IDs to scalars.

    An optional {member_id: {Asy: m², Asz: m²}} map selects finite-shear
    diagnostics for every frame member, in its authored local y/z directions.
    Omitting it preserves the existing default Euler–Bernoulli reference convention.
    """
    nodes, elements, materials, sections, cases, xyz, restraints, lengths, rotations, loads = _validate(model)
    areas = None if effective_shear_areas is None else _shear_areas(effective_shear_areas, elements, loads)
    if not factors_list:
        return []
    for factors in factors_list:
        if not isinstance(factors, dict) or set(factors) - set(cases):
            raise ValueError("Selection factors reference an unknown load case")
        for key, value in factors.items():
            number(value, f"factor {key}")
    cuts = {eid: {0., L} for eid, L in lengths.items()}
    for station in stations:
        if station.get("kind") == "node":
            if station.get("id") not in nodes:
                raise ValueError("Unknown observation node")
        elif station.get("kind") == "member":
            eid = station.get("id")
            if eid not in elements or station.get("side") not in ("left", "right"):
                raise ValueError("Invalid observation member/side")
            x = number(station["positionM"], "positionM")
            if not _in_member(x, lengths[eid]):
                raise ValueError("Observation station outside member")
            if elements[eid]["type"] not in TRUSS:
                cuts[eid].add(x)
        else:
            raise ValueError("Unsupported observation location")
    for item in loads:
        if item["type"] == "point":
            cuts[item["load"]["element"]].add(item["position"])
        elif "pieces" in item:
            for a, b, _, _ in item["pieces"]:
                cuts[item["load"]["element"]].update((a, b))
    # Collapse only floating-point roundoff (e.g. a requested geometric end
    # rounded one ULP below its computed length), not physically close stations.
    aliases = {}
    for eid, values in cuts.items():
        canonical = []
        eps = 32*np.finfo(float).eps*max(1., lengths[eid])
        for x in sorted(values):
            y = 0. if abs(x) <= eps else lengths[eid] if abs(x-lengths[eid]) <= eps else x
            if canonical and abs(y-canonical[-1]) <= eps:
                y = canonical[-1]
            else:
                canonical.append(y)
            aliases[eid, x] = y
        cuts[eid] = set(canonical)
    positions, segments, by_member = {}, [], {}
    planar = model["coordinate_system"]["dimension"] == "2d"
    for eid, e in elements.items():
        L, R = lengths[eid], rotations[eid]
        a, b = [xyz[n] for n in e["nodes"]]
        previous = None
        by_member[eid] = []
        for x in sorted(cuts[eid]):
            n = e["nodes"][0] if x == 0 else e["nodes"][1] if x == L else (eid, x)
            if n not in xyz:
                xyz[n] = a + (b-a)*x/L
                restraints[n] = [False, True, False, True, False, True] if planar else [False]*6
            positions[eid, x] = n
            if previous is not None:
                start, ni = previous
                seg = dict(element=e, start=start, end=x, nodes=[ni, n], R=R)
                segments.append(seg)
                by_member[eid].append(seg)
            previous = (x, n)
    for (eid, x), canonical in aliases.items():
        positions[eid, x] = positions[eid, canonical]
    frame_nodes = {n for s in segments if s["element"]["type"] not in TRUSS for n in s["nodes"]}
    inactive_rotations = {n for n in xyz if n not in frame_nodes}
    for n in inactive_rotations:
        # Pure truss joints have no rotational DOFs. Never discard moments there.
        if any(item["type"] == "nodal" and item["load"]["node"] == n and np.any(item["vector"][3:]) for item in loads):
            raise ValueError("Moment applied to a pure truss joint without rotational stiffness")
        restraints[n][3:] = [True]*3
    idx = {n: 6*i for i, n in enumerate(xyz)}
    ndof, nrhs = 6*len(xyz), len(factors_list)
    if sparse is None and ndof > 2400:
        raise ValueError("Large model requires SciPy sparse factorization; install scipy in an isolated venv")
    F = np.zeros((ndof, nrhs))
    rows, cols, entries = [], [], []
    K = np.zeros((ndof, ndof)) if sparse is None else None
    for item in loads:
        if item["type"] not in ("nodal", "point"):
            continue
        load = item["load"]
        n = load["node"] if item["type"] == "nodal" else positions[load["element"], item["position"]]
        weights = np.array([f.get(item["case"], 0) for f in factors_list])
        F[idx[n]:idx[n]+6] += item["vector"][:, None]*weights
    distributed = {}
    for item in loads:
        if "pieces" in item:
            distributed.setdefault(item["load"]["element"], []).append(item)
    for s in segments:
        e, R, L = s["element"], s["R"], s["end"]-s["start"]
        T = np.kron(np.eye(4), R)
        k = local_stiffness(e, materials[e["material"]], sections[e["section"]], L,
                            None if areas is None else areas.get(e["id"]))
        f = np.zeros((12, nrhs))
        mid = (s["start"]+s["end"])/2
        for item in distributed.get(e["id"], []):
            for a, b, qa, qb in item["pieces"]:
                if not a < mid < b:
                    continue
                q0 = qa+(qb-qa)*(s["start"]-a)/(b-a)
                q1 = qa+(qb-qa)*(s["end"]-a)/(b-a)
                if item["load"].get("reference_frame", "global") == "global":
                    q0, q1 = R@q0, R@q1
                weights = np.array([v.get(item["case"], 0) for v in factors_list])
                f += _consistent_load(q0, q1, L)[:, None]*weights
        dofs = np.array([idx[n]+i for n in s["nodes"] for i in range(6)])
        kg = T.T@k@T
        if sparse is None:
            K[np.ix_(dofs, dofs)] += kg
        else:
            ii, jj = np.nonzero(kg)
            rows.extend(dofs[ii]); cols.extend(dofs[jj]); entries.extend(kg[ii, jj])
        F[dofs] += T.T@f
        s.update(k=k, T=T, f=f, dofs=dofs)
    if sparse is not None:
        K = sparse.coo_matrix((entries, (rows, cols)), shape=(ndof, ndof)).tocsc()
    free = np.array([idx[n]+i for n, r in restraints.items() for i, fixed in enumerate(r) if not fixed], dtype=int)
    U = np.zeros((ndof, nrhs))
    min_pivot = None
    if len(free):
        A = K[np.ix_(free, free)] if sparse is None else K[free][:, free]
        diag = A.diagonal()
        if np.any(diag <= 0) or not np.all(np.isfinite(diag)):
            raise ValueError("Unstable structure: zero/nonpositive free-DOF stiffness")
        scale = 1/np.sqrt(diag)
        try:
            if sparse is None:
                B = scale[:, None]*A*scale[None, :]
                chol = np.linalg.cholesky(B)
                min_pivot = float(np.min(np.diag(chol)**2))
                if min_pivot < 1e-12:
                    raise ValueError("Unstable or numerically singular stiffness")
                # Batched triangular substitution avoids two extra LU factorizations.
                rhs = scale[:, None]*F[free]
                for i in range(len(free)):
                    rhs[i] = (rhs[i] - chol[i, :i]@rhs[:i])/chol[i, i]
                for i in range(len(free)-1, -1, -1):
                    rhs[i] = (rhs[i] - chol[i+1:, i]@rhs[i+1:])/chol[i, i]
                U[free] = scale[:, None]*rhs
            else:
                D = sparse.diags(scale)
                B = (D@A@D).tocsc()
                lu = splu(B, permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0., options={"SymmetricMode": True})
                min_pivot = float(np.min(lu.U.diagonal()))
                if min_pivot < 1e-12:
                    raise ValueError("Unstable or numerically singular stiffness")
                U[free] = scale[:, None]*lu.solve(scale[:, None]*F[free])
        except (np.linalg.LinAlgError, RuntimeError) as exc:
            raise ValueError("Unstable/singular structure; no pseudoinverse is permitted") from exc
    reactions = K@U-F
    for s in segments:
        s["actions"] = s["k"]@s["T"]@U[s["dofs"]]-s["f"]

    def make_quantity(column):
        def quantity(location, component):
            lower = component.lower()
            if location["kind"] == "node":
                if location["id"] not in nodes:
                    raise ValueError("Unknown output node")
                if lower in DISPLACEMENTS:
                    return float(U[idx[location["id"]]+DISPLACEMENTS.index(lower), column])
                if lower in REACTIONS:
                    return float(reactions[idx[location["id"]]+REACTIONS.index(lower), column])
                raise ValueError(f"Unsupported node component {component}")
            eid, x = location["id"], number(location["positionM"], "positionM")
            if eid not in elements or not _in_member(x, lengths[eid]) or location.get("side") not in ("left", "right"):
                raise ValueError("Invalid member output location")
            e = elements[eid]
            x = aliases.get((eid, x), x)
            if lower in DISPLACEMENTS:
                j = DISPLACEMENTS.index(lower)
                if e["type"] in TRUSS:
                    if j >= 3:
                        raise ValueError("Truss member rotations are undefined")
                    ni, nj = e["nodes"]
                    return float((1-x/lengths[eid])*U[idx[ni]+j, column]+x/lengths[eid]*U[idx[nj]+j, column])
                n = positions.get((eid, x))
                if n is None:
                    raise ValueError("Member displacement must be requested as a true observation station before solve")
                return float(U[idx[n]+j, column])
            if component not in ACTIONS:
                raise ValueError(f"Unsupported member component {component}")
            if e["type"] in TRUSS:
                return float(by_member[eid][0]["actions"][6, column]) if component == "N" else 0.
            ss = [s for s in by_member[eid] if s["start"] <= x <= s["end"]]
            s = ss[0] if location["side"] == "left" else ss[-1]
            start = x == s["start"]
            if not start and x != s["end"]:
                raise ValueError("Member actions must be requested as a true observation station before solve")
            i = ACTIONS.index(component)
            sign = [-1, 1, 1, -1, -1, -1][i] if start else [1, -1, -1, 1, 1, 1][i]
            return float(sign*s["actions"][i if start else 6+i, column])
        return quantity

    results = []
    for c in range(nrhs):
        residual = float(np.max(np.abs(reactions[free, c]))) if len(free) else 0.
        if not np.all(np.isfinite(U[:, c])) or residual > 1e-7*(1+np.max(np.abs(F[:, c]))):
            raise ValueError(f"Free equilibrium residual too large: {residual}")
        external, reaction = np.zeros(6), np.zeros(6)
        for n, position in xyz.items():
            fi, ri = F[idx[n]:idx[n]+6, c], reactions[idx[n]:idx[n]+6, c]
            external[:3] += fi[:3]
            external[3:] += fi[3:]+np.cross(position, fi[:3])
            reaction[:3] += ri[:3]
            reaction[3:] += ri[3:]+np.cross(position, ri[:3])
        balance = external+reaction
        if np.max(np.abs(balance)) > 1e-7*(1+np.max(np.abs(external))):
            raise ValueError(f"Global force/moment equilibrium failed: {balance.tolist()}")
        checks = dict(method="independent-direct-stiffness", theory="Euler-Bernoulli", freeResidual=residual,
                      forceMomentBalance=balance.tolist(), dofs=ndof, freeDofs=len(free),
                      factorization="scipy-sparse-superlu" if sparse is not None else "numpy-cholesky-batched",
                      factorizationCount=1 if len(free) else 0, rightHandSides=nrhs,
                      minimumScaledPivot=min_pivot, observationNodes=len(xyz)-len(nodes),
                      addedMass=0, assumptions=ASSUMPTIONS[:])
        if areas is not None:
            checks.update(theory="Timoshenko", effectiveShearAreasM2={eid: a.copy() for eid, a in areas.items()},
                          assumptions=[
                              "Linear elastic, small-displacement Timoshenko bending with explicit effective shear areas.",
                              "Shear areas are caller-supplied diagnostics; no native-input qualification or corpus promotion is implied.",
                              "Only nodal/point and piecewise-constant distributed loads are supported in finite-shear mode.",
                              *ASSUMPTIONS[1:],
                          ])
        results.append((make_quantity(c), checks))
    return results
