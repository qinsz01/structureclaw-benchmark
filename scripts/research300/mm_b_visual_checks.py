"""Check authored MM-B drawing artifacts, independently of the drawing generator.

These checks detect coincident identifiers, dropped geometry and misleading axis
projections. They do not grant blind-input-review or native-engine acceptance.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image

from mm_b_architectural_checks import CASE_IDS as ARCHITECTURAL_CASE_IDS, inspect_case as inspect_architectural_case


ROOT = Path(__file__).resolve().parents[2]
NS = "{http://www.w3.org/2000/svg}"
AXES = {"X": ("x", 1), "Y": ("y", 1), "Z": ("z", 1),
        "u": ("x", 1), "v": ("z", 1), "w": ("y", -1)}


def structural_labels(svg, model):
    ids = {item["id"] for item in model["nodes"] + model["elements"]}
    return [(text, (text.text or "").split(" roll=")[0])
            for text in svg.iter(NS + "text")
            if (text.text or "").split(" roll=")[0] in ids]


def inspect_svg(svg, model, *, schematic=False):
    """Match labelled member lines to labelled node dots and physical projections."""
    errors = []
    labels = structural_labels(svg, model)
    positions = defaultdict(set)
    for text, ident in labels:
        positions[(float(text.get("x")), float(text.get("y")))].add(ident)
    for position, ids in positions.items():
        if len(ids) > 1:
            errors.append(f"coincident identifiers at {position}: {sorted(ids)}")

    nodes = {n["id"]: n for n in model["nodes"]}
    members = {e["id"]: e for e in model["elements"]}
    circles = [(float(c.get("cx")), float(c.get("cy")))
               for c in svg.iter(NS + "circle")]
    points = {}
    for text, ident in labels:
        if ident not in nodes:
            continue
        anchor = (float(text.get("x")), float(text.get("y")))
        if not circles:
            errors.append(f"node {ident} has no physical node dot")
            continue
        nearest = min(circles, key=lambda p: math.dist(p, anchor))
        if math.dist(nearest, anchor) > 30:
            errors.append(f"node {ident} label is detached from every node dot")
        points[ident] = nearest

    lines = [((float(line.get("x1")), float(line.get("y1"))),
              (float(line.get("x2")), float(line.get("y2"))))
             for line in svg.iter(NS + "line")]
    for _, ident in labels:
        if ident not in members:
            continue
        ends = members[ident]["nodes"]
        if any(end not in points for end in ends):
            errors.append(f"member {ident} is missing a labelled endpoint")
            continue
        a, b = (points[end] for end in ends)
        if math.dist(a, b) < .001:
            errors.append(f"member {ident} has a zero-length visible projection")
        elif not any((math.dist(a, u) < .002 and math.dist(b, v) < .002) or
                     (math.dist(a, v) < .002 and math.dist(b, u) < .002)
                     for u, v in lines):
            errors.append(f"member {ident} has no line joining its physical endpoints")

    axes = [text for text in svg.iter(NS + "text")
            if (text.text or "").endswith(" [m]")]
    if len(axes) != 2:
        errors.append("drawing must identify both projection axes and metre units")
    elif points and not schematic:
        # The horizontal axis label is right of the plot, vertical is at its left.
        axes.sort(key=lambda t: float(t.get("x")), reverse=True)
        for dimension, label in enumerate(axes):
            name = label.text.removesuffix(" [m]")
            if name not in AXES:
                errors.append(f"unknown drawing axis {name}")
                continue
            axis, sign = AXES[name]
            values = {ident: nodes[ident][axis] * sign for ident in points}
            lo, hi = min(values.values()), max(values.values())
            pmin = min(p[dimension] for p in points.values())
            pmax = max(p[dimension] for p in points.values())
            if hi == lo:
                if pmax - pmin > .002:
                    errors.append(f"constant {name} coordinates are drawn at different positions")
                continue
            if pmax - pmin < .002:
                errors.append(f"distinct {name} coordinates collapse to one position")
                continue
            for ident, point in points.items():
                fraction = (values[ident] - lo) / (hi - lo)
                expected = pmin + (fraction if dimension == 0 else 1 - fraction) * (pmax - pmin)
                if abs(point[dimension] - expected) > .003:
                    errors.append(f"node {ident} does not preserve its {name} coordinate ratio")
    return errors, {ident for _, ident in labels}


def missing_labels(model, diagrams):
    expected = {item["id"] for item in model["nodes"] + model["elements"]}
    found = set().union(*(structural_labels_set(svg, model) for svg in diagrams))
    return sorted(expected - found)


def structural_labels_set(svg, model):
    return {ident for _, ident in structural_labels(svg, model)}


def negative_controls(model, diagrams):
    """Reject the reported overprint, a dropped member, and a broken member line."""
    candidate = next(svg for svg in diagrams if len(structural_labels(svg, model)) > 3)
    duplicate = deepcopy(candidate)
    labels = structural_labels(duplicate, model)
    first, second = next((a, b) for a in labels for b in labels if a[1] != b[1])
    second[0].set("x", first[0].get("x"))
    second[0].set("y", first[0].get("y"))
    assert any("coincident identifiers" in error for error in inspect_svg(duplicate, model)[0]), \
        "coincident-label negative control was accepted"

    dropped = [deepcopy(svg) for svg in diagrams]
    ident = "c2-1-1"
    assert ident in {e["id"] for e in model["elements"]}
    for svg in dropped:
        for parent in svg.iter():
            for child in list(parent):
                if child.tag == NS + "text" and child.text == ident:
                    parent.remove(child)
    assert ident in missing_labels(model, dropped), "dropped-member negative control was accepted"

    broken = deepcopy(candidate)
    # A structural stroke joins two node dots; arrows and dimension ticks do not.
    circles = {(c.get("cx"), c.get("cy")) for c in broken.iter(NS + "circle")}
    line = next(line for line in broken.iter(NS + "line")
                if (line.get("x1"), line.get("y1")) in circles
                and (line.get("x2"), line.get("y2")) in circles)
    line.set("x2", str(float(line.get("x2")) + 7))
    assert any("no line joining" in error for error in inspect_svg(broken, model)[0]), \
        "broken-member-line negative control was accepted"
    return 3


def check(cases_root):
    errors = []
    records = []
    architectural = []
    controls = 0
    for number in range(51, 101):
        case = cases_root / f"MM-{number:03d}"
        contract = json.loads((case / "contract.json").read_text())
        model = json.loads((case / "model-state-1.json").read_text())
        if case.name in ARCHITECTURAL_CASE_IDS:
            # These source cases deliberately require interpreting architectural
            # DXF. Reconstruct that actual public source; do not demand or expose
            # a clean structural answer diagram to satisfy drawing completeness.
            record = inspect_architectural_case(case)
            architectural.append(record)
            errors.extend(f"{case.name}: {error}" for error in record["errors"])
            continue
        svgs = sorted(name for name in contract["attachments"]
                      if name.endswith(".svg") and name.startswith(("drawing-", "initial-")))
        complete = []
        yz_views = []
        for name in svgs:
            path = case / name
            svg = ET.parse(path).getroot()
            found_errors, found = inspect_svg(svg, model,
                schematic=case.name == "MM-072" and name.startswith("initial-"))
            errors.extend(f"{case.name}/{name}: {error}" for error in found_errors)
            png = path.with_suffix(".png")
            with Image.open(png) as image:
                image.load()
                expected_size = (int(svg.get("width")), int(svg.get("height")))
                if image.size != expected_size:
                    errors.append(f"{case.name}/{name}: PNG/SVG dimension mismatch")
            if name.startswith("drawing-"):
                complete.append(svg)
                if "elevation-YZ" in name:
                    yz_views.append((name, found))
            records.append({"caseId": case.name, "svg": name,
                            "pngSha256": hashlib.sha256(png.read_bytes()).hexdigest(),
                            "svgSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "structuralLabelCount": len(found), "errors": found_errors})
        missing = missing_labels(model, complete)
        if missing:
            errors.append(f"{case.name}: node/member identifiers absent from all complete views: {missing}")
        if case.name == "MM-085":
            target = {f"c{i}-1-1" for i in range(3)}
            if set().union(*(ids & target for _, ids in yz_views)) != target:
                errors.append("MM-085: the three X-station columns must remain visible in YZ elevations")
            for name, ids in yz_views:
                if len(ids & target) > 1:
                    errors.append(f"MM-085/{name}: distinct X-station columns share one YZ elevation")
            controls = negative_controls(model, complete)
    return {"schemaVersion": 1, "cases": 50, "drawings": len(records),
            "architecturalDxfCases": len(architectural), "architecturalRecords": architectural,
            "negativeControls": controls, "errorCount": len(errors),
            "errors": errors, "records": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-root", type=Path, default=ROOT / "corpora/research-300/cases")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = check(args.cases_root)
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if report["errors"]:
        print("\n".join(report["errors"]))
        raise SystemExit(f"FAIL {report['errorCount']} visual artifact errors")
    print(f"PASS {report['cases']} cases / {report['drawings']} decoded PNG/SVG pairs; "
          f"{report['architecturalDxfCases']} architectural DXF geometry sources; "
          f"distinct labels, member connectivity, axis projections, complete geometry; "
          f"{report['negativeControls']} deliberate errors rejected. Visual acceptance remains separate.")


if __name__ == "__main__":
    main()
