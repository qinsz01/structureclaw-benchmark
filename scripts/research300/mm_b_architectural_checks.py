"""RI-008: architectural DXF remains the sole public structural geometry source.

Reconstruct labelled directed geometry from the actual DXF before comparing it
with the private model as an author diagnostic. No generator helpers, solver,
provider changes, reference values or acceptance claims are involved.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import io
import json
import math
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import ezdxf
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
CASE_IDS = tuple(f"MM-{n:03d}" for n in (56, 59, 62, 75, 82, 86))
PUBLIC_FILES = {"input.dxf", "properties.json", "assignments.json", "loads.json",
                "section-details.png", "section-details.svg"}
COMMERCIAL_CONVENTION = {
    "id": "commercial-linear-static-v2",
    "bendingTheory": "Timoshenko",
    "effectiveShearAreas": {"localY": "5*A/6", "localZ": "5*A/6"},
    "publicAttachment": "analysis-conventions-v2.txt",
}
# Reviewed v2 appendix bytes, independent of the authoring generator. A filename
# or matching phrase alone must never admit extra geometry or private answers.
CONVENTION_SHA256 = {
    "en": "9629fdf21147ce9e824418679e65d181a1a6b30d8bc5e79ab81d9d39f3d51ed9",
    "zh": "c9303e7eb89248c6abb62f30788c19ac7142a4f4fdba164d01c94ff975c1cde8",
}
# Original integrated e65fd4a inputs: this disposition must preserve every DXF
# byte, including all architectural distraction and annotation entities.
DXF_SHA256 = {
    "MM-056": "d95f0c10f6ab5577d666d7fbcbb4f1910de8f587a6e9de08db4a94d2ffdbd53b",
    "MM-059": "0b2ed00e679353c82ef18f6af74cf82df6703ef4f799170436523edb2af26ba8",
    "MM-062": "5179306f45142952be74c0c1bee73882fbaac0d0daf531dfe5fe90f41df594c8",
    "MM-075": "c01d05365819579c4397731739e4c3596954d130b6d1e0c9e75a4d295ac6bdda",
    "MM-082": "98d1edddc57798dfb3a2e8330e03c46252e91c6589c8d22ffc43681681d7f138",
    "MM-086": "01934adc57e142fd3c435a8ffb828f5023bc32ad280a4327391194807afcad8f",
}
GRAPH_SIZES = dict(zip(CASE_IDS, ((6, 5), (7, 6), (9, 9), (14, 15), (27, 40), (36, 56))))
DOFS = ("ux", "uy", "uz", "rx", "ry", "rz")


def point(vector):
    return tuple(round(float(vector[index]), 8) for index in range(2))


def footprint_centres(entities):
    """Find closed architectural column footprints without consulting the model."""
    adjacency = defaultdict(set)
    for entity in entities:
        if entity.dxftype() == "LINE" and entity.dxf.layer == "A-COLUMN":
            a, b = point(entity.dxf.start), point(entity.dxf.end)
            adjacency[a].add(b)
            adjacency[b].add(a)
    centres = []
    remaining = set(adjacency)
    while remaining:
        pending, component = [next(iter(remaining))], set()
        while pending:
            vertex = pending.pop()
            if vertex not in component:
                component.add(vertex)
                pending.extend(adjacency[vertex] - component)
        remaining -= component
        if len(component) == 4 and all(len(adjacency[p]) == 2 for p in component):
            centres.append(tuple(sum(p[k] for p in component) / 4 for k in range(2)))
    return centres


def reconstruct_dxf(text, dimension):
    """Recover coordinates and directed connections solely from public DXF data."""
    errors = []
    doc = ezdxf.read(io.StringIO(text))
    views = []
    for entity in doc.modelspace():
        if (entity.dxftype() == "TEXT" and entity.dxf.layer == "ANNOTATION"
                and " | units m |" in entity.dxf.text):
            title = entity.dxf.text.split(" |", 1)[0]
            axes = ("x", "y") if title.startswith("plan-") else (
                ("y", "z") if title.startswith("elevation-YZ-") else ("x", "z"))
            views.append({"title": title, "axes": axes,
                          "offset": float(entity.dxf.insert.x), "entities": []})
        elif views:
            views[-1]["entities"].append(entity)
    if not views:
        errors.append("architectural DXF has no named orthographic views")
    nodes, members = {}, {}
    layers = Counter(e.dxf.layer for e in doc.modelspace())
    for layer in ("A-WALL", "A-COLUMN", "A-EQUIPMENT", "A-EQUIPMENT-TAG", "A-DIM", "A-SUPPORT"):
        if not layers[layer]:
            errors.append(f"architectural distractor/annotation layer missing: {layer}")
    for view in views:
        entities, title = view["entities"], view["title"]
        centres = footprint_centres(entities)
        local_nodes = {}
        for entity in entities:
            if entity.dxftype() != "TEXT" or entity.dxf.layer != "S-NODE-TAG":
                continue
            ident, anchor = entity.dxf.text, point(entity.dxf.insert)
            if not centres:
                errors.append(f"{title}: node {ident} has no architectural footprint")
                continue
            centre = min(centres, key=lambda p: math.dist(p, anchor))
            if math.dist(centre, anchor) > .5:
                errors.append(f"{title}: node {ident} has no associated footprint")
                continue
            local_nodes[ident] = centre
            coordinates = dict(zip(view["axes"], (centre[0] - view["offset"], centre[1])))
            if dimension == "2d":
                coordinates["y"] = 0.0
            elif title.startswith("plan-"):
                match = re.fullmatch(r"plan-\d+-Z(-?[\d.]+)", title)
                if match:
                    coordinates["z"] = float(match[1])
            previous = nodes.setdefault(ident, {})
            for axis, value in coordinates.items():
                if axis in previous and not math.isclose(previous[axis], value, abs_tol=1e-7):
                    errors.append(f"{title}: node {ident} has inconsistent {axis} across views")
                previous[axis] = value
        lines = [e for e in entities if e.dxftype() == "LINE" and e.dxf.layer.startswith("S-")]
        tags = [e for e in entities if e.dxftype() == "TEXT" and e.dxf.layer == "S-MEMBER-TAG"]
        used = set()
        for tag in tags:
            ident = tag.dxf.text
            # Tags sit above their member midpoint; match to physical strokes,
            # never to the private model's member endpoint list.
            anchor = point(tag.dxf.insert)
            candidates = [(i, line) for i, line in enumerate(lines)
                          if math.dist(anchor, tuple((a + b) / 2 for a, b in
                                       zip(point(line.dxf.start), point(line.dxf.end)))) < .4]
            if len(candidates) != 1:
                errors.append(f"{title}: unmatched/ambiguous structural member tag {ident}")
                continue
            index, line = candidates[0]
            used.add(index)
            ends = []
            for endpoint in (point(line.dxf.start), point(line.dxf.end)):
                matches = [nid for nid, p in local_nodes.items() if math.dist(endpoint, p) < 1e-7]
                if len(matches) != 1:
                    errors.append(f"{title}: member {ident} endpoint lacks one labelled node")
                else:
                    ends.append(matches[0])
            if len(ends) == 2:
                if ident in members and members[ident] != ends:
                    errors.append(f"{title}: member {ident} directed endpoints disagree across views")
                members[ident] = ends
        if len(used) != len(lines):
            errors.append(f"{title}: structural geometry has unlabelled member lines")
    for ident, coordinates in nodes.items():
        if set(coordinates) != {"x", "y", "z"}:
            errors.append(f"node {ident} lacks complete spatial coordinates in DXF views")
    return errors, nodes, members, dict(sorted(layers.items())), len(views)


def inspect_case(case, overrides=None, *, preserve_bytes=True):
    """Read public input and diagnostic model; mutations can be supplied in memory."""
    overrides = overrides or {}

    def read(name):
        if name in overrides and overrides[name] is None:
            raise FileNotFoundError(name)
        return overrides[name] if name in overrides else (case / name).read_bytes()

    def data(name):
        return json.loads(read(name))

    errors = []
    contract, model = data("contract.json"), data("model-state-1.json")
    allowed = PUBLIC_FILES
    if "analysisConvention" in contract:
        if (contract.get("plannedEngine") not in ("PKPM", "YJK")
                or contract["analysisConvention"] != COMMERCIAL_CONVENTION):
            errors.append("analysis convention declaration must match the supported commercial v2 definition")
        else:
            allowed = PUBLIC_FILES | {COMMERCIAL_CONVENTION["publicAttachment"]}
    public = contract["attachments"]
    if set(public) != allowed or len(public) != len(allowed):
        errors.append("public attachment whitelist must contain only DXF, appendices and section details")
    missing = []
    for name in set(public).union(*(set(t["attachments"]) for t in contract["turns"])):
        try:
            read(name)
        except FileNotFoundError:
            errors.append(f"missing public attachment: {name}")
            missing.append(name)
    if missing:
        return {"caseId": case.name, "geometrySource": "input.dxf", "errors": errors}
    appendix = COMMERCIAL_CONVENTION["publicAttachment"]
    if appendix in allowed:
        try:
            digest = hashlib.sha256(read(appendix)).hexdigest()
        except FileNotFoundError:
            errors.append(f"missing public attachment: {appendix}")
        else:
            if digest != CONVENTION_SHA256.get(contract.get("locale")):
                errors.append("analysis convention text does not match the preserved v2 appendix for its locale")
        convention_rows = [r for r in contract["requirementCoverage"]
                           if r["sourceField"] == "engine.analysisContract"]
        if len(convention_rows) != 1 or "attachment:" + appendix not in convention_rows[0]["targets"]:
            errors.append("analysis convention coverage must target its public appendix")
    for turn in contract["turns"]:
        if set(turn["attachments"]) != allowed or len(turn["attachments"]) != len(allowed):
            errors.append(f"turn {turn['id']} attachment whitelist exposes extra files or lacks required DXF/appendices")
        if "input.dxf" not in turn["instruction"]:
            errors.append(f"turn {turn['id']} must explicitly identify input.dxf as the geometry source")
    if "input.dxf" not in read("prompt.txt").decode():
        errors.append("prompt must identify input.dxf as the geometry source")
    required_targets = {"attachment:" + name for name in PUBLIC_FILES}
    input_rows = [r for r in contract["requirementCoverage"] if r["sourceField"] == "task.inputForm"]
    if len(input_rows) != 1 or not required_targets <= set(input_rows[0]["targets"]):
        errors.append("inputForm coverage must target DXF, property, assignment, load and section inputs")
    for row in contract["requirementCoverage"]:
        if any(isinstance(t, str) and t.startswith("attachment:") and t[11:] not in allowed
               for t in row["targets"]):
            errors.append("coverage refers to removed/nonpublic geometry attachments")
    properties, assignments, loads = (data(name) for name in ("properties.json", "assignments.json", "loads.json"))
    direction = properties.get("localAxes", {}).get("beam", "")
    if not all(token in direction for token in ("DXF LINE", "10/20/30", "11/21/31")):
        errors.append("public local-axis direction must follow directed DXF LINE group codes")
    mapping = properties.get("dxfMapping", {})
    if not all(token in mapping.get("structuralLayers", "") for token in
               ("S-MEMBER-TAG", "S-NODE-TAG", "A-WALL", "A-COLUMN", "A-EQUIPMENT", "A-DIM", "A-SUPPORT")):
        errors.append("public DXF layer mapping lacks structural tags/distractor/annotation distinctions")
    if "labelled nodes" not in mapping.get("connectivity", ""):
        errors.append("public DXF mapping must explain labelled-node connectivity")
    if properties["materials"] != model["materials"] or properties["sections"] != model["sections"]:
        errors.append("public material/section stiffness differs from diagnostic model")
    boundaries = [{"node": n["id"], "restrainedDOFs": [d for d, r in zip(DOFS, n["restraints"]) if r]}
                  for n in model["nodes"]]
    if properties.get("boundaryConditions") != boundaries:
        errors.append("public support appendix differs from diagnostic model")
    expected_assignments = [{"id": e["id"], "type": e["type"], "material": e["material"],
                             "section": e["section"], "rotation_angle": e.get("rotation_angle", 0),
                             "referenceVector": model.get("metadata", {}).get("elementReferenceVectors", {}).get(e["id"])}
                            for e in model["elements"]]
    if assignments != expected_assignments:
        errors.append("public member property mapping differs from diagnostic model or exposes connectivity")
    for key in ("load_cases", "load_combinations"):
        if loads[key] != model[key]:
            errors.append(f"public {key} differ from diagnostic model")
    if loads.get("floorAreaLoads") != model.get("metadata", {}).get("floorAreaLoads"):
        errors.append("public tributary-floor-load appendix differs from diagnostic model")
    if "actual member length" not in loads["units"] or "global axes" not in loads["units"]:
        errors.append("public line-load basis/frame is incomplete")
    for name in ("properties.json", "assignments.json", "loads.json"):
        def no_geometry(value):
            if isinstance(value, dict):
                if {"x", "y", "z"} <= value.keys() or "nodes" in value or "elements" in value:
                    errors.append(f"{name} contains a coordinate/connectivity JSON bypass")
                for child in value.values():
                    no_geometry(child)
            elif isinstance(value, list):
                for child in value:
                    no_geometry(child)
        no_geometry(data(name))
    section = ET.fromstring(read("section-details.svg"))
    with Image.open(io.BytesIO(read("section-details.png"))) as image:
        image.load()
        if image.size != (int(section.get("width")), int(section.get("height"))):
            errors.append("section-details.png does not match its section SVG dimensions")
    if list(section.iter("{http://www.w3.org/2000/svg}circle")) or any(
            (e.text or "").endswith(" [m]") for e in section.iter("{http://www.w3.org/2000/svg}text")):
        errors.append("section-details.svg contains structural geometry rather than section properties")
    dxf_bytes = read("input.dxf")
    digest = hashlib.sha256(dxf_bytes).hexdigest()
    if preserve_bytes and digest != DXF_SHA256[case.name]:
        errors.append("architectural DXF bytes differ from the preserved original input")
    found_errors, nodes, members, layers, views = reconstruct_dxf(dxf_bytes.decode(), model["coordinate_system"]["dimension"])
    errors.extend(found_errors)
    if (len(nodes), len(members)) != GRAPH_SIZES[case.name]:
        errors.append("reconstructed architectural graph has missing/extra nodes or members")
    expected_nodes = {n["id"]: {axis: n[axis] for axis in ("x", "y", "z")} for n in model["nodes"]}
    if set(nodes) != set(expected_nodes):
        errors.append("DXF node identifiers differ from diagnostic model")
    for ident in nodes.keys() & expected_nodes.keys():
        if any(axis not in nodes[ident] or not math.isclose(nodes[ident][axis], value, abs_tol=1e-7)
               for axis, value in expected_nodes[ident].items()):
            errors.append(f"DXF node {ident} coordinates differ from diagnostic model")
    if members != {e["id"]: e["nodes"] for e in model["elements"]}:
        errors.append("DXF directed endpoints differ from diagnostic model")
    return {"caseId": case.name, "geometrySource": "input.dxf", "dxfSha256": digest,
            "views": views, "nodeCount": len(nodes), "memberCount": len(members),
            "layerEntityCounts": layers, "publicAttachments": public, "errors": errors}


def negative_controls(case):
    """Exercise meaningful failures without letting frozen-byte checks mask them."""
    records = []
    original = json.loads((case / "contract.json").read_text())
    # Existing, valid clean structural drawings give injection controls actual
    # content, rather than relying on a nonexistent filename being rejected.
    clean = {suffix: (case.parent / "MM-055" / f"drawing-elevation-XZ.{suffix}").read_bytes()
             for suffix in ("png", "svg")}

    def reject(name, overrides, expected, *, preserve_bytes=True):
        errors = inspect_case(case, overrides, preserve_bytes=preserve_bytes)["errors"]
        if not any(expected in error for error in errors):
            raise AssertionError(f"{name}: expected {expected!r}, got {errors}")
        records.append({"caseId": case.name, "name": name, "rejectedBy": expected})

    def encoded(value):
        return json.dumps(value).encode()

    for suffix in ("png", "svg"):
        contract = deepcopy(original)
        name = f"renamed-site-overview.{suffix}"
        contract["attachments"].append(name)
        contract["turns"][0]["attachments"].append(name)
        reject(f"renamed-clean-{suffix}", {"contract.json": encoded(contract), name: clean[suffix]}, "public attachment whitelist")
    contract = deepcopy(original)
    contract["turns"].append({**contract["turns"][0], "id": "t2", "attachments": ["later-overview.png"]})
    reject("clean-graphic-on-later-turn", {"contract.json": encoded(contract), "later-overview.png": clean["png"]}, "turn t2 attachment whitelist")
    reject("clean-geometry-disguised-as-section-svg", {"section-details.svg": clean["svg"]}, "contains structural geometry")
    reject("clean-geometry-disguised-as-section-png", {"section-details.png": clean["png"]}, "section SVG dimensions")
    contract = deepcopy(original)
    contract["attachments"].remove("input.dxf")
    for turn in contract["turns"]:
        turn["attachments"].remove("input.dxf")
    reject("missing-public-dxf", {"contract.json": encoded(contract)}, "public attachment whitelist")
    reject("missing-actual-dxf-file", {"input.dxf": None}, "missing public attachment: input.dxf")
    contract = deepcopy(original)
    for row in contract["requirementCoverage"]:
        if row["sourceField"] == "task.inputForm":
            row["targets"].remove("attachment:input.dxf")
    reject("coverage-missing-dxf", {"contract.json": encoded(contract)}, "inputForm coverage")
    properties = json.loads((case / "properties.json").read_text())
    properties["localAxes"]["beam"] = "follow arrows in the removed clean drawing"
    reject("removed-arrow-direction", {"properties.json": encoded(properties)}, "public local-axis direction")
    properties = json.loads((case / "properties.json").read_text())
    properties["coordinates"] = json.loads((case / "model-state-1.json").read_text())["nodes"]
    reject("hidden-coordinate-json-bypass", {"properties.json": encoded(properties)}, "coordinate/connectivity JSON bypass")

    def mutate_dxf(change):
        doc = ezdxf.readfile(case / "input.dxf")
        change(doc.modelspace())
        stream = io.StringIO()
        doc.write(stream)
        return {"input.dxf": stream.getvalue().encode()}

    def strip_distractors(space):
        for entity in list(space):
            if entity.dxf.layer.startswith("A-"):
                space.delete_entity(entity)
    reject("stripped-architectural-distractors", mutate_dxf(strip_distractors), "distractor/annotation layer missing", preserve_bytes=False)

    def drop_member(space):
        space.delete_entity(next(e for e in space if e.dxftype() == "LINE" and e.dxf.layer.startswith("S-")))
    reject("missing-structural-line", mutate_dxf(drop_member), "unmatched/ambiguous structural member tag", preserve_bytes=False)

    def break_connection(space):
        line = next(e for e in space if e.dxftype() == "LINE" and e.dxf.layer.startswith("S-"))
        line.dxf.end = line.dxf.end + (.05, 0, 0)
    reject("disconnected-structural-line", mutate_dxf(break_connection), "endpoint lacks one labelled node", preserve_bytes=False)

    def reverse_connection(space):
        line = next(e for e in space if e.dxftype() == "LINE" and e.dxf.layer.startswith("S-"))
        line.dxf.start, line.dxf.end = line.dxf.end, line.dxf.start
    reject("reversed-local-axis", mutate_dxf(reverse_connection), "directed endpoints", preserve_bytes=False)
    return records


def check_provider(cases_root, provider, node):
    """Audit the frozen source-format payload; concise editions are checked separately."""
    script = r"""
const p = require(process.argv[1]);
const corpus = p.loadCorpus({corpus:'research-300', root:process.argv[2]});
const result = JSON.parse(process.argv[3]).map(id => {
  const record = p.loadCase(corpus, id);
  return {caseId:id, turns:record.contract.turns.map((_,i)=>p.getFrozenPublicTurnInput(record,i))};
});
process.stdout.write(JSON.stringify(result));
"""
    process = subprocess.run([str(node), "-e", script, str(provider.resolve()),
                              str(cases_root.resolve().parents[2]), json.dumps(CASE_IDS)],
                             text=True, capture_output=True, check=True)
    records = json.loads(process.stdout)
    public_turns = []
    for record in records:
        case = cases_root / record["caseId"]
        inspected = inspect_case(case)
        if inspected["errors"]:
            raise AssertionError(f"{record['caseId']}: invalid authored public input: {inspected['errors']}")
        allowed = set(inspected["publicAttachments"])
        for turn in record["turns"]:
            if ({a["relPath"] for a in turn["attachments"]} != allowed
                    or len(turn["attachments"]) != len(allowed)):
                raise AssertionError(f"{record['caseId']}/{turn['turnId']}: provider exposes unexpected attachments")
            for attachment in turn["attachments"]:
                if Path(attachment["path"]).resolve() != (case / attachment["relPath"]).resolve():
                    raise AssertionError("provider attachment path differs from authored public input")
            def no_private(value):
                if isinstance(value, dict):
                    if {"nodes", "elements", "models", "modelStates", "referenceRequests"} & value.keys():
                        raise AssertionError("provider public payload exposes private geometry/reference keys")
                    for child in value.values():
                        no_private(child)
                elif isinstance(value, list):
                    for child in value:
                        no_private(child)
            no_private(turn)
            public_turns.append({"caseId": record["caseId"], "turnId": turn["turnId"],
                                 "attachments": sorted(allowed)})
    return {"module": str(provider), "sha256": hashlib.sha256(provider.read_bytes()).hexdigest(),
            "inputEdition": "frozen", "scope": "Frozen architectural source-format audit",
            "cases": len(records), "turns": sum(len(r["turns"]) for r in records),
            "publicAttachmentsByTurn": public_turns}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-root", type=Path, default=ROOT / "corpora/research-300/cases")
    parser.add_argument("--provider", type=Path)
    parser.add_argument("--node", type=Path, default=Path("/opt/lab-node/bin/node"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    records = [inspect_case(args.cases_root / cid) for cid in CASE_IDS]
    errors = [f"{r['caseId']}: {error}" for r in records for error in r["errors"]]
    controls = []
    provider = None
    if not errors:
        controls = negative_controls(args.cases_root / "MM-056") + negative_controls(args.cases_root / "MM-082")
        if args.provider:
            provider = check_provider(args.cases_root, args.provider, args.node)
    report = {"schemaVersion": 1, "cases": len(records), "records": records,
              "negativeControls": controls, "provider": provider,
              "errorCount": len(errors), "errors": errors,
              "scope": "Author input regression diagnostics only; no blind/native/reference acceptance."}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"PASS {len(records)} architectural-DXF cases; complete directed geometry and appendices; "
          f"preserved DXF bytes and distractors; {len(controls)} targeted mutations rejected"
          + (f"; frozen provider {provider['cases']} cases/{provider['turns']} turns" if provider else ""))


if __name__ == "__main__":
    main()
