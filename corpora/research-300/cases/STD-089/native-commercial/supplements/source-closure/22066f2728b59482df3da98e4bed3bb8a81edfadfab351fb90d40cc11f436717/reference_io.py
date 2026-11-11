"""Safe reference inputs, selection handling and reporting; standard library only.

This module deliberately imports no structural solver or production converter.
All numeric solver results use m, kN, rad before conversion to requested units.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import uuid


DEFAULT_TOLERANCE = {"absolute": 1e-8, "relative": 1e-6}
CASE_ID = re.compile(r"(?:STD|INT|MM)-(?:0[0-9][1-9]|0[1-9]0|100)\Z")
UNITS = {
    "m": ("length", 1.0), "mm": ("length", .001), "cm": ("length", .01),
    "rad": ("rotation", 1.0), "mrad": ("rotation", .001),
    "deg": ("rotation", math.pi / 180),
    "kN": ("force", 1.0), "N": ("force", .001), "MN": ("force", 1000.0),
    "kN.m": ("moment", 1.0), "N.m": ("moment", .001),
    "kN.mm": ("moment", .001), "N.mm": ("moment", 1e-6),
    "MN.m": ("moment", 1000.0),
}


class ReferenceInputError(ValueError):
    """An input cannot be used without guessing or losing its meaning."""


def finite_number(value, label="value"):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReferenceInputError(f"{label} must be a finite number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ReferenceInputError(f"{label} must be finite") from exc
    if not math.isfinite(result):
        raise ReferenceInputError(f"{label} must be finite")
    return result


def _identifier(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ReferenceInputError(f"{label} must be a nonempty string")
    return value


def validate_case_id(case_id):
    if not isinstance(case_id, str) or not CASE_ID.fullmatch(case_id):
        raise ReferenceInputError(f"Invalid research-300 case ID: {case_id!r}")
    return case_id


def _relative_parts(filename):
    if (not isinstance(filename, str) or not filename or "\\" in filename
            or "\x00" in filename or PurePosixPath(filename).is_absolute()
            or any(part in ("", ".", "..") for part in filename.split("/"))
            or ":" in filename):
        raise ReferenceInputError(f"Unsafe relative input path: {filename!r}")
    return filename.split("/")


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReferenceInputError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ReferenceInputError(f"Non-finite JSON number: {value}")


def _check_finite_tree(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ReferenceInputError("JSON contains a non-finite number")
    if isinstance(value, dict):
        for item in value.values():
            _check_finite_tree(item)
    elif isinstance(value, list):
        for item in value:
            _check_finite_tree(item)


def read_bytes_safe(case_dir, filename):
    """Read a regular file through directory handles without following symlinks."""
    parts = _relative_parts(filename)
    root = Path(case_dir).absolute()
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(root, flags)
    try:
        for part in parts[:-1]:
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                  dir_fd=descriptor)
        with os.fdopen(file_descriptor, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ReferenceInputError(f"Input must be a regular file: {filename}")
            raw = source.read()
    finally:
        os.close(descriptor)
    return raw


def read_json_safe(case_dir, filename):
    """Return parsed JSON and SHA-256 of the exact bytes safely read."""
    raw = read_bytes_safe(case_dir, filename)
    try:
        parsed = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_no_duplicate_keys,
                            parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReferenceInputError(f"Invalid JSON in {filename}: {exc}") from exc
    _check_finite_tree(parsed)
    if not isinstance(parsed, dict):
        raise ReferenceInputError(f"Expected a JSON object in {filename}")
    return parsed, hashlib.sha256(raw).hexdigest()


def build_source_binding(case_dir, contract, input_hashes):
    """Bind all authored bytes with the shared compact UTF-8 manifest contract.

    Generated evidence is never an authored input. Reject an invalid whitelist
    instead of silently omitting a declared input or hashing a circular receipt.
    Recheck parsed files so a change while loading cannot bind different bytes.
    """
    attachments = contract.get("attachments")
    if not isinstance(attachments, list):
        raise ReferenceInputError("Contract attachments must be a filename array")
    paths = ["contract.json", "prompt.txt", "reference-requests.json",
             *contract["modelStates"], *attachments]
    generated = {"independent-reference.json", "reference-provenance.json",
                 "native-opensees-reference.json", "native-input-receipt.json",
                 "native-solver-receipt.json", "native-raw-responses.json", "native-checks.json"}
    for filename in paths:
        parts = _relative_parts(filename)
        if parts[-1] in generated:
            raise ReferenceInputError(f"Generated evidence cannot be an authored input: {filename}")
    files = []
    for filename in sorted(set(paths), key=lambda path: path.encode("utf-8")):
        digest = hashlib.sha256(read_bytes_safe(case_dir, filename)).hexdigest()
        if filename in input_hashes and digest != input_hashes[filename]:
            raise ReferenceInputError(f"Authored input changed while loading: {filename}")
        files.append({"path": filename, "sha256": digest})
    manifest = {"schemaVersion": 1, "files": files}
    encoded = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {"sourceManifest": manifest, "sourceHash": hashlib.sha256(encoded).hexdigest()}


def _indexed(records, label):
    if not isinstance(records, list):
        raise ReferenceInputError(f"{label} must be an array")
    result = {}
    for record in records:
        if not isinstance(record, dict):
            raise ReferenceInputError(f"{label} entries must be objects")
        key = _identifier(record.get("id"), f"{label} ID")
        if key in result:
            raise ReferenceInputError(f"Duplicate {label} ID: {key}")
        result[key] = record
    return result


def selection_factors(model, selection):
    """Resolve explicit case/combination identity; never infer from a name."""
    if not isinstance(selection, dict) or selection.get("kind") not in ("case", "combination"):
        raise ReferenceInputError("Selection kind must be case or combination")
    selected_id = _identifier(selection.get("id"), "selection ID")
    cases = _indexed(model.get("load_cases"), "load case")
    combinations = _indexed(model.get("load_combinations", []), "combination")
    if selection["kind"] == "case":
        if selected_id not in cases:
            raise ReferenceInputError(f"Unknown load case: {selected_id}")
        return {selected_id: 1.0}
    if selected_id not in combinations:
        raise ReferenceInputError(f"Unknown combination: {selected_id}")
    factors = combinations[selected_id].get("factors")
    if not isinstance(factors, dict) or not factors:
        raise ReferenceInputError(f"Combination {selected_id} needs a nonempty factors object")
    result = {}
    for case_id, factor in factors.items():
        if case_id not in cases:
            raise ReferenceInputError(f"Combination {selected_id} refers to unknown load case {case_id}")
        result[case_id] = finite_number(factor, f"factor for {case_id}")
    return result


def quantity_unit(component):
    if component in ("ux", "uy", "uz"):
        return "m"
    if component in ("rx", "ry", "rz"):
        return "rad"
    if component in ("Fx", "Fy", "Fz", "fx", "fy", "fz", "N", "V2", "V3"):
        return "kN"
    if component in ("Mx", "My", "Mz", "mx", "my", "mz", "T", "M2", "M3"):
        return "kN.m"
    raise ReferenceInputError(f"Unsupported quantity component: {component!r}")


def _unit_info(unit):
    if not isinstance(unit, str):
        raise ReferenceInputError("Unit must be a string")
    canonical = unit.replace("·", ".").replace("*", ".")
    if canonical not in UNITS:
        raise ReferenceInputError(f"Unsupported unit: {unit!r}")
    return UNITS[canonical]


def convert_value(value, from_unit, to_unit):
    from_dimension, from_scale = _unit_info(from_unit)
    to_dimension, to_scale = _unit_info(to_unit)
    if from_dimension != to_dimension:
        raise ReferenceInputError(f"Incompatible units: {from_unit} and {to_unit}")
    return finite_number(finite_number(value) * from_scale / to_scale, "converted value")


def _tolerance(record):
    tolerance = record.get("tolerance", DEFAULT_TOLERANCE)
    if not isinstance(tolerance, dict) or not {"absolute", "relative"} <= tolerance.keys():
        raise ReferenceInputError("Tolerance needs absolute and relative numbers")
    for field in ("absolute", "relative"):
        if finite_number(tolerance[field], f"tolerance.{field}") < 0:
            raise ReferenceInputError("Tolerances must be nonnegative")
    return deepcopy(tolerance)


def _validate_quantity(record, model):
    if not isinstance(record, dict):
        raise ReferenceInputError("Quantity must be an object")
    result = deepcopy(record)
    _identifier(result.get("id"), "quantity ID")
    if "value" in result:
        raise ReferenceInputError("Reference requests must not contain numerical answer values")
    selection_factors(model, result.get("selection"))
    location = result.get("location")
    if not isinstance(location, dict) or location.get("kind") not in ("node", "member"):
        raise ReferenceInputError("Location kind must be node or member")
    kind = location["kind"]
    members = _indexed(model.get("elements"), "element")
    nodes = _indexed(model.get("nodes"), "node")
    locations = nodes if kind == "node" else members
    if location.get("id") not in locations:
        raise ReferenceInputError(f"Unknown {kind} location: {location.get('id')!r}")
    component = result.get("component")
    convert_value(0, quantity_unit(component), result.get("unit"))
    if kind == "node" and component in ("N", "V2", "V3", "T", "M2", "M3"):
        raise ReferenceInputError(f"Member component {component} cannot be requested at a node")
    if kind == "member":
        if component in ("Fx", "Fy", "Fz", "fx", "fy", "fz", "Mx", "My", "Mz", "mx", "my", "mz"):
            raise ReferenceInputError(f"Support component {component} cannot be requested at a member")
        position = finite_number(location.get("positionM"), "member positionM")
        if location.get("side") not in ("left", "right"):
            raise ReferenceInputError("Member location needs explicit left/right side")
        member = members[location["id"]]
        try:
            a, b = [nodes[key] for key in member["nodes"]]
            length = math.sqrt(sum((finite_number(b[key]) - finite_number(a[key])) ** 2
                                   for key in ("x", "y", "z")))
        except (KeyError, TypeError, ValueError) as exc:
            raise ReferenceInputError(f"Invalid endpoints for member {location['id']}") from exc
        if not 0 <= position <= length + 1e-10:
            raise ReferenceInputError(f"Member position {position} is outside [0, {length}]")
    result["tolerance"] = _tolerance(result)
    return result


def evaluate_derived(quantities, records):
    """Evaluate ordered records from primitives or earlier derived values.

    Difference means first minus second; sum preserves signs after conversion.
    Extrema co-govern within the frozen derived tolerance in requested units;
    the canonical value always comes from the first co-governing operand.
    tiePolicy controls permitted reporting, not canonical reference selection.
    Extrema retain the signed value, direct governing operand and contributing
    leaf selections through every cascade.
    A cross-selection arithmetic result has no invented single selection.
    """
    if not isinstance(records, list):
        raise ReferenceInputError("Derived requests must be an array")
    indexed = defaultdict(list)
    for quantity in quantities:
        indexed[quantity["id"]].append(quantity)
    results, leaves = [], {}
    seen = set(indexed)
    definitions = set()
    for record in records:
        if not isinstance(record, dict):
            raise ReferenceInputError("Derived request must be an object")
        key = _identifier(record.get("id"), "derived ID")
        if key in seen:
            raise ReferenceInputError(f"Duplicate derived/quantity ID: {key}")
        seen.add(key)
        definitions.add(key)
    for record in records:
        key = record["id"]
        if "value" in record:
            raise ReferenceInputError("Derived requests must not contain numerical answer values")
        operation = record.get("operation")
        operands = record.get("operands")
        if operation not in ("difference", "sum", "max", "min", "max_abs"):
            raise ReferenceInputError(f"Unsupported derived operation: {operation!r}")
        if record.get("tiePolicy", "first") not in ("first", "any"):
            raise ReferenceInputError("Derived tiePolicy must be first or any")
        if not isinstance(operands, list) or not operands or (operation == "difference" and len(operands) != 2):
            raise ReferenceInputError("Difference needs two operands; sum/extrema need at least one")
        values, source_leaves, used = [], [], set()
        for operand in operands:
            _identifier(operand, "derived operand")
            if operand in used:
                raise ReferenceInputError(f"Duplicate derived operand: {operand}")
            used.add(operand)
            matches = indexed.get(operand, [])
            if len(matches) != 1:
                reason = "Ambiguous" if matches else ("Forward/cyclic" if operand in definitions else "Unknown")
                raise ReferenceInputError(f"{reason} derived operand: {operand}")
            source = matches[0]
            values.append(convert_value(source["value"], source["unit"], record.get("unit")))
            source_leaves.append(leaves.get(operand, [source]))
        result = deepcopy(record)
        result["tolerance"] = _tolerance(record)
        # Metadata is computed from leaves, never copied from request assertions.
        for field in ("selection", "operandSelections", "governingOperand", "governingSelection",
                      "governingSelections", "governingLeafOperands", "coGoverningOperands"):
            result.pop(field, None)
        if operation in ("difference", "sum"):
            try:
                value = values[0] - values[1] if operation == "difference" else math.fsum(values)
            except OverflowError as exc:
                raise ReferenceInputError("Non-finite derived sum") from exc
            result["value"] = finite_number(value, "derived value")
            selected_leaves = [leaf for group in source_leaves for leaf in group]
            result["operandSelections"] = [deepcopy(item["selection"]) for item in selected_leaves]
        else:
            scores = [abs(value) for value in values] if operation == "max_abs" else values
            best = min(scores) if operation == "min" else max(scores)
            tolerance = result["tolerance"]
            allowed = tolerance["absolute"] + tolerance["relative"] * abs(best)
            co_governing = [index for index, score in enumerate(scores) if abs(score - best) <= allowed]
            governing = co_governing[0]
            result["coGoverningOperands"] = [operands[index] for index in co_governing]
            result["value"] = values[governing]
            result["governingOperand"] = operands[governing]
            selected_leaves = source_leaves[governing]
            result["governingLeafOperands"] = [item["id"] for item in selected_leaves]
        selections = []
        for item in selected_leaves:
            if item["selection"] not in selections:
                selections.append(deepcopy(item["selection"]))
        if operation in ("difference", "sum"):
            if len(selections) == 1:
                result["selection"] = selections[0]
        else:
            result["governingSelection"] = selections[0] if len(selections) == 1 else None
            result["governingSelections"] = selections
        results.append(result)
        indexed[key].append(result)
        leaves[key] = selected_leaves
    return results


def load_case(case_dir):
    """Return validated contract, requests, models and exact source byte hashes."""
    contract, contract_hash = read_json_safe(case_dir, "contract.json")
    requests, requests_hash = read_json_safe(case_dir, "reference-requests.json")
    if contract.get("schemaVersion") != 1 or requests.get("schemaVersion") != 1:
        raise ReferenceInputError("Contract and reference requests need schemaVersion 1")
    case_id = validate_case_id(contract.get("id"))
    model_paths = contract.get("modelStates")
    if not isinstance(model_paths, list) or not model_paths:
        raise ReferenceInputError("Contract modelStates must be a nonempty filename array")
    for filename in model_paths:
        _relative_parts(filename)
    if len(set(model_paths)) != len(model_paths):
        raise ReferenceInputError("Duplicate model filename in modelStates")
    states = requests.get("states")
    if not isinstance(states, list) or len(states) != len(model_paths):
        raise ReferenceInputError("Reference states must cover all contract modelStates")
    hashes = {"contract.json": contract_hash, "reference-requests.json": requests_hash}
    result_states, seen = [], set()
    for state in states:
        if not isinstance(state, dict):
            raise ReferenceInputError("Reference state must be an object")
        number = state.get("state")
        if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= len(model_paths):
            raise ReferenceInputError(f"Invalid model state: {number!r}")
        if number in seen:
            raise ReferenceInputError(f"Duplicate reference state: {number}")
        seen.add(number)
        filename = state.get("model")
        if filename != model_paths[number - 1]:
            raise ReferenceInputError(f"State {number} model differs from contract modelStates")
        model, digest = read_json_safe(case_dir, filename)
        if model.get("schema_version") != "2.2.0":
            raise ReferenceInputError(f"State {number} needs model protocol 2.2.0")
        hashes[filename] = digest
        requested = state.get("quantities")
        if not isinstance(requested, list):
            raise ReferenceInputError("State quantities must be an array")
        quantities, identities = [], set()
        for record in requested:
            quantity = _validate_quantity(record, model)
            selection = quantity["selection"]
            identity = (selection["kind"], selection["id"], quantity["id"])
            if identity in identities:
                raise ReferenceInputError(f"Duplicate quantity ID within selection: {quantity['id']}")
            identities.add(identity)
            quantities.append(quantity)
        derived = deepcopy(state.get("derived", []))
        # Validate operand resolution, units and tolerances before invoking a solver.
        evaluate_derived([dict(item, value=0.0) for item in quantities], derived)
        result_states.append({"state": number, "modelPath": filename, "model": model,
                              "quantities": quantities, "derived": derived})
    binding = build_source_binding(case_dir, contract, hashes)
    return {"id": case_id, "contract": contract, "requests": requests,
            "states": result_states, "hashes": hashes, **binding}


load_case_inputs = load_case


def write_json_exclusive(path, payload):
    """Atomically create an artifact, rejecting existing files and symlink parents."""
    data = (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    destination = Path(path).absolute()
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(destination.anchor, flags)
    temporary = None
    try:
        for part in destination.parts[1:-1]:
            if part in (".", ".."):
                raise ReferenceInputError("Output path must not contain traversal components")
            try:
                os.mkdir(part, dir_fd=descriptor)
            except FileExistsError:
                pass
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        temporary_name = f".reference-{uuid.uuid4().hex}.tmp"
        output = os.open(temporary_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o644, dir_fd=descriptor)
        temporary = temporary_name
        with os.fdopen(output, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination.name, src_dir_fd=descriptor,
                dst_dir_fd=descriptor, follow_symlinks=False)
        os.fsync(descriptor)
    finally:
        if temporary is not None:
            os.unlink(temporary, dir_fd=descriptor)
        os.close(descriptor)
    return destination
