#!/usr/bin/env python3
"""Inventory commercial-case requirements locally; never submit or certify a job."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference_io import load_case, read_bytes_safe, read_json_safe, write_json_exclusive


def bending_theory(conventions):
    """Record explicit theory; linear-elastic alone specifies neither theory."""
    theories = [name for name in ("Euler-Bernoulli", "Timoshenko") if name in conventions]
    if len(theories) > 1:
        raise ValueError("Ambiguous bending convention; requires manual input review")
    return theories[0] if theories else "unspecified"


def summarize_case(case, theory, convention_sources):
    states = []
    for state in sorted(case["states"], key=lambda row: row["state"]):
        model = state["model"]
        quantities = state["quantities"]
        selections = sorted({(q["selection"]["kind"], q["selection"]["id"]) for q in quantities})
        outputs = {}
        for quantity in quantities:
            outputs.setdefault(quantity["location"]["kind"], set()).add(quantity["component"])
        material_records = {json.dumps({k: material[k] for k in ("E", "G", "nu", "rho")
                                        if k in material}, sort_keys=True)
                            for material in model["materials"]}
        states.append({
            "state": state["state"], "modelSha256": case["hashes"][state["modelPath"]],
            "dimension": model["coordinate_system"]["dimension"],
            "nodeCount": len(model["nodes"]), "memberCount": len(model["elements"]),
            "elementTypes": sorted({e["type"] for e in model["elements"]}),
            "sectionTypes": sorted({s["type"] for s in model["sections"]}),
            "sectionPropertyNames": sorted({k for s in model["sections"] for k in s.get("properties", {})}),
            "materials": [json.loads(record) for record in sorted(material_records)],
            "supportPatterns": [list(row) for row in sorted({tuple(n["restraints"]) for n in model["nodes"]})],
            "analysisControl": model.get("analysis_control", {}).copy(),
            "loadTypes": sorted({load["type"] for lc in model["load_cases"] for load in lc.get("loads", [])}),
            "selections": [{"kind": kind, "id": identifier} for kind, identifier in selections],
            "outputs": {kind: sorted(components) for kind, components in sorted(outputs.items())},
            "quantityCount": len(quantities), "derivedCount": len(state["derived"]),
            "derivedOperations": sorted({row["operation"] for row in state["derived"]}),
        })
    return {
        "id": case["id"], "engine": case["contract"]["plannedEngine"],
        "sourceHash": case["sourceHash"], "inputHashes": case["hashes"],
        "bendingTheory": theory, "bendingConventionSources": convention_sources,
        "selectionCount": sum(len(state["selections"]) for state in states),
        "quantityCount": sum(state["quantityCount"] for state in states),
        "derivedCount": sum(state["derivedCount"] for state in states), "states": states,
    }


def inventory(cases_root):
    cases = []
    for directory in sorted(Path(cases_root).iterdir()):
        if not directory.is_dir():
            continue
        contract, _ = read_json_safe(directory, "contract.json")
        if contract.get("plannedEngine") not in ("PKPM", "YJK"):
            continue
        case = load_case(directory)
        if case["id"] != directory.name:
            raise ValueError("Case directory differs from bound contract ID")
        # Different authoring families put their public convention in a text
        # appendix, a JSON analysisMethod field or the prompt. Never inspect the
        # hidden model or a generated answer to infer a public requirement.
        sources, fragments = [], []
        bound = {row["path"]: row["sha256"] for row in case["sourceManifest"]["files"]}
        for filename in sorted(set(["prompt.txt", *contract["attachments"]])):
            if Path(filename).suffix.lower() not in (".txt", ".md", ".json"):
                continue
            payload = read_bytes_safe(directory, filename)
            digest = hashlib.sha256(payload).hexdigest()
            if digest != bound[filename]:
                raise ValueError("Public input changed during inventory")
            fragment = payload.decode("utf-8")
            if "Euler-Bernoulli" in fragment or "Timoshenko" in fragment:
                fragments.append(fragment)
                sources.append({"path": filename, "sha256": digest})
        cases.append(summarize_case(case, bending_theory("\n".join(fragments)), sources))
    if not cases:
        raise ValueError("No commercial cases found")
    counts = {}
    for engine in ("PKPM", "YJK"):
        selected = [case for case in cases if case["engine"] == engine]
        counts[engine] = {"cases": len(selected), "states": sum(len(c["states"]) for c in selected),
                          "selections": sum(c["selectionCount"] for c in selected),
                          "quantities": sum(c["quantityCount"] for c in selected),
                          "derived": sum(c["derivedCount"] for c in selected),
                          "bendingTheory": {theory: sum(c["bendingTheory"] == theory for c in selected)
                                            for theory in sorted({c["bendingTheory"] for c in selected})}}
    return {"schemaVersion": 1, "kind": "commercial-requirements-inventory",
            "status": "inventory-only", "generatorSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "origins": {"bendingTheory": "bound-public-inputs", "modelSummary": "bound-model-states",
                        "blindInputReview": "not-performed-by-inventory"},
            "modelPropertyUnits": {"length": "m", "E": "MPa", "G": "MPa", "rho": "kg/m^3",
                                   "A": "m^2", "Iy": "m^4", "Iz": "m^4", "J": "m^4"},
            "counts": counts, "cases": cases}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = inventory(args.cases_root)
        write_json_exclusive(args.output, report)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"commercial inventory failed: {exc}\n")
    print(json.dumps({"output": str(args.output), "counts": report["counts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
