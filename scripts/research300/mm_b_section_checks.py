"""Check MM-B section-sheet text legibility using real font and raster extents.

Checks authored PNG/SVG pairs independently of the section renderer. This is
focused visual evidence, not blind reconstruction or native-engine acceptance.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image, ImageFont


ROOT = Path(__file__).resolve().parents[2]
NS = "{http://www.w3.org/2000/svg}"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
TITLE = re.compile(r"^(.+) \| roll (-?[0-9.]+) deg$")


def text_boxes(svg, *, raster):
    """Use ink extents, including ascenders/descenders, not anchor equality."""
    boxes = []
    for text in svg.iter(NS + "text"):
        label = text.text or ""
        size = int(text.get("font-size"))
        font = ImageFont.truetype(FONT, size)
        x, y = float(text.get("x")), float(text.get("y"))
        if raster:
            # The paired PNG uses Pillow's top-origin default text anchor;
            # SVG uses an alphabetic baseline. Check both real font layouts.
            y -= size
            left, top, right, bottom = font.getbbox(label)
        else:
            left, top, right, bottom = font.getbbox(label, anchor="ls")
        boxes.append((label, (x + left, y + top, x + right, y + bottom), text))
    return boxes


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def inspect(svg, model, png=None):
    errors = []
    width, height = int(svg.get("width")), int(svg.get("height"))
    expected = {(e["section"], float(e.get("rotation_angle", 0)))
                for e in model["elements"]}
    titles = [TITLE.fullmatch(text.text or "") for text in svg.iter(NS + "text")]
    actual = Counter((m.group(1), float(m.group(2))) for m in titles if m)
    if actual != Counter({key: 1 for key in expected}):
        errors.append("section/roll title inventory differs from assigned sections")
    labels = Counter(text.text for text in svg.iter(NS + "text"))
    for caption in ("2 before roll", "3 before roll", "Iy about local 2", "Iz about local 3"):
        if labels[caption] != len(expected):
            errors.append(f"missing or repeated section caption: {caption}")

    for raster in (False, True):
        medium = "PNG" if raster else "SVG"
        boxes = text_boxes(svg, raster=raster)
        for index, (label, box, _) in enumerate(boxes):
            if box[0] < 0 or box[1] < 0 or box[2] > width or box[3] > height:
                errors.append(f"{medium} text clipped: {label}")
            for other, other_box, _ in boxes[index + 1:]:
                if overlaps(box, other_box):
                    errors.append(f"{medium} text overlap: {label} / {other}")
        if raster and png is not None:
            if png.size != (width, height):
                errors.append("PNG/SVG dimensions differ")
            else:
                for label, box, text in boxes:
                    # Verify actual decoded raster text ink exists where the SVG
                    # claims it does; no fabricated layout-only PNG acceptance.
                    color = tuple(bytes.fromhex(text.get("fill", "#102030")[1:]))
                    crop = png.crop(tuple(int(value) for value in box))
                    ink = sum(count for count, pixel in crop.getcolors(crop.width * crop.height)
                              if pixel == color)
                    if ink < 5:
                        errors.append(f"PNG has no corresponding text ink: {label}")
    return errors


def negative_controls(svg, model):
    controls = []

    def rejected(name, changed, expected_error):
        errors = inspect(changed, model)
        assert any(expected_error in error for error in errors), \
            f"negative control accepted: {name}"
        controls.append(name)

    collision = deepcopy(svg)
    title = next(t for t in collision.iter(NS + "text") if TITLE.fullmatch(t.text or ""))
    local3 = next(t for t in collision.iter(NS + "text") if t.text == "3 before roll")
    # Restore the exact old RI-007 placement relative to its original title.
    local3.set("x", str(float(title.get("x")) + 85))
    local3.set("y", str(float(title.get("y")) - 21 + 14))
    rejected("RI007 old local-3/title collision", collision, "text overlap")

    collision = deepcopy(svg)
    title = next(t for t in collision.iter(NS + "text") if TITLE.fullmatch(t.text or ""))
    iy = next(t for t in collision.iter(NS + "text") if t.text == "Iy about local 2")
    iy.set("x", str(float(title.get("x")) + 240))
    rejected("old local-2/property collision", collision, "text overlap")

    clipped = deepcopy(svg)
    local3 = next(t for t in clipped.iter(NS + "text") if t.text == "3 before roll")
    local3.set("x", str(float(clipped.get("width")) - 5))
    rejected("clipped local-3 caption", clipped, "text clipped")

    missing = deepcopy(svg)
    local3 = next(t for t in missing.iter(NS + "text") if t.text == "3 before roll")
    missing.remove(local3)
    rejected("missing local-3 caption", missing, "missing or repeated section caption")

    changed_roll = deepcopy(svg)
    title = next(t for t in changed_roll.iter(NS + "text")
                 if TITLE.fullmatch(t.text or "") and "roll 90 deg" in t.text)
    title.text = title.text.replace("roll 90 deg", "roll 0 deg")
    rejected("MM090 erased 90-degree roll", changed_roll, "title inventory")

    blank = Image.new("RGB", (int(svg.get("width")), int(svg.get("height"))), "white")
    assert any("no corresponding text ink" in error for error in inspect(svg, model, blank)), \
        "blank PNG negative control accepted"
    controls.append("blank PNG with valid SVG")
    return controls


def check(cases_root):
    errors, records, controls = [], [], []
    for number in range(51, 101):
        case = cases_root / f"MM-{number:03d}"
        model = json.loads((case / "model-state-1.json").read_text())
        svg_path, png_path = case / "section-details.svg", case / "section-details.png"
        svg = ET.parse(svg_path).getroot()
        with Image.open(png_path) as source:
            source.load()
            png = source.convert("RGB")
            found = inspect(svg, model, png)
        errors.extend(f"{case.name}: {error}" for error in found)
        records.append({"caseId": case.name, "textCount": len(text_boxes(svg, raster=True)),
                        "pngSha256": hashlib.sha256(png_path.read_bytes()).hexdigest(),
                        "svgSha256": hashlib.sha256(svg_path.read_bytes()).hexdigest(),
                        "errors": found})
        if case.name == "MM-090":
            controls = negative_controls(svg, model)
    return {"schemaVersion": 1, "cases": len(records), "pngSvgPairs": len(records),
            "font": FONT, "negativeControls": controls, "errorCount": len(errors),
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
        raise SystemExit(f"FAIL {report['errorCount']} section-sheet errors")
    print(f"PASS {report['cases']} section PNG/SVG pairs: font-extents overlap/clipping, "
          f"decoded text ink, section/roll/caption inventory; "
          f"{len(report['negativeControls'])} deliberate errors rejected.")


if __name__ == "__main__":
    main()
