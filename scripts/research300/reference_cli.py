#!/usr/bin/env python3
"""Generate isolated research-300 independent references without overwriting files."""
from __future__ import annotations

import argparse
from copy import deepcopy
import math
import os
from pathlib import Path
import sys

try:
    from .reference_io import (ReferenceInputError, convert_value, evaluate_derived,
                               load_case, quantity_unit, selection_factors,
                               validate_case_id, write_json_exclusive)
except ImportError:
    from reference_io import (ReferenceInputError, convert_value, evaluate_derived,
                              load_case, quantity_unit, selection_factors,
                              validate_case_id, write_json_exclusive)


COMMERCIAL_SHEAR_CONVENTION = {
    "id": "commercial-linear-static-v2",
    "bendingTheory": "Timoshenko",
    "effectiveShearAreas": {"localY": "5*A/6", "localZ": "5*A/6"},
    "publicAttachment": "analysis-conventions-v2.txt",
}


def declared_convention(case):
    contract = case["contract"]
    if "analysisConvention" not in contract:
        return None
    if contract["plannedEngine"] not in ("PKPM", "YJK"):
        raise ReferenceInputError("This analysis convention is restricted to commercial cases")
    convention = contract["analysisConvention"]
    if convention != COMMERCIAL_SHEAR_CONVENTION:
        raise ReferenceInputError("Unsupported or incomplete explicit analysis convention")
    attachment = convention["publicAttachment"]
    turns = contract.get("turns", [])
    if (attachment not in contract.get("attachments", []) or not turns
            or attachment not in turns[0].get("attachments", [])
            or attachment not in {row["path"] for row in case["sourceManifest"]["files"]}):
        raise ReferenceInputError("The analysis convention requires a bound public first-turn appendix")
    return deepcopy(convention)


def prescribed_shear_areas(model):
    """Evaluate the explicit v2 public rule, not an inferred section default."""
    sections = {section["id"]: section for section in model["sections"]}
    result = {}
    for element in model["elements"]:
        if element["type"] in ("truss", "brace"):
            continue
        area = sections[element["section"]]["properties"]["A"]
        if isinstance(area, bool) or not isinstance(area, (int, float)) or not math.isfinite(area) or area <= 0:
            raise ReferenceInputError("Prescribed shear areas require positive finite section A")
        result[element["id"]] = dict(Asy=5*area/6, Asz=5*area/6)
    return result


def generate_reference(case, solve_many=None):
    if solve_many is None:
        try:
            from .reference_solver import solve_many
        except ImportError:
            from reference_solver import solve_many
    convention = declared_convention(case)
    states, checks = [], []
    for state in case["states"]:
        selections = {}
        for quantity in state["quantities"]:
            selection = quantity["selection"]
            selections.setdefault((selection["kind"], selection["id"]), selection)
        factors = [selection_factors(state["model"], selection) for selection in selections.values()]
        stations = [quantity["location"] for quantity in state["quantities"]]
        kwargs = {"effective_shear_areas": prescribed_shear_areas(state["model"])} if convention else {}
        solved = solve_many(state["model"], factors, stations, **kwargs) if factors else []
        if len(solved) != len(selections):
            raise ReferenceInputError("Solver returned an unexpected number of selections")
        calculators = {}
        for (key, selection), (calculate, evidence) in zip(selections.items(), solved):
            calculators[key] = calculate
            checks.append(dict(evidence, state=state["state"], selection=deepcopy(selection)))
        quantities = []
        for request in state["quantities"]:
            quantity = deepcopy(request)
            selection = quantity["selection"]
            calculate = calculators[(selection["kind"], selection["id"])]
            quantity["value"] = convert_value(calculate(quantity["location"], quantity["component"]),
                                             quantity_unit(quantity["component"]), quantity["unit"])
            quantities.append(quantity)
        states.append({"state": state["state"], "quantities": quantities,
                       "derived": evaluate_derived(quantities, state["derived"])})
    warning = ("Timoshenko diagnostic uses publicly prescribed Asy=Asz=5*A/6; native serialization differences require separate input review. Frozen request tolerances are unchanged."
               if convention else "Euler-Bernoulli reference omits shear deformation; Timoshenko displacements may differ physically. Frozen request tolerances are unchanged.")
    result = {"schemaVersion": 1, "id": case["id"], "evaluationProfile": "engineering-v2.3",
            "referenceKind": "independent-elastic-matrix",
            "notCommercialScoringTruth": True, "sameEngineTruthStatus": "pending",
            "warnings": [warning,
                         "Commercial-engine references remain diagnostic pending independently reviewed same-engine native truth."],
            "toleranceFrozenBeforeCandidate": True,
            "inputHashes": deepcopy(case["hashes"]),
            "sourceHash": case["sourceHash"], "sourceManifest": deepcopy(case["sourceManifest"]),
            "states": states, "checks": checks}
    if convention:
        result["analysisConvention"] = convention
    return result


def generate_case(case_dir, output_root, solve_many=None, expected_case_id=None):
    case = load_case(case_dir)
    if expected_case_id is not None and case["id"] != expected_case_id:
        raise ReferenceInputError(f"Selected case {expected_case_id} contains contract ID {case['id']}")
    destination = Path(output_root) / case["id"] / "independent-reference.json"
    if os.path.lexists(destination):
        raise FileExistsError(f"Refusing to overwrite existing reference: {destination}")
    result = generate_reference(case, solve_many)
    return write_json_exclusive(destination, result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument("--case-dir", type=Path)
    sources.add_argument("--cases-root", type=Path)
    parser.add_argument("--case", action="append", default=[], help="Case ID under --cases-root; repeatable")
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.case and not args.cases_root:
        parser.error("--case requires --cases-root")
    try:
        if args.case_dir:
            directories = [args.case_dir]
        else:
            ids = args.case or sorted(path.name for path in args.cases_root.iterdir() if path.is_dir())
            if not ids:
                raise ReferenceInputError("No cases were selected")
            if len(ids) != len(set(ids)):
                raise ReferenceInputError("Duplicate --case ID")
            directories = [args.cases_root / validate_case_id(case_id) for case_id in ids]
        for directory in directories:
            destination = generate_case(directory, args.output_root,
                                        expected_case_id=directory.name if args.cases_root else None)
            print(destination)
    except (ReferenceInputError, OSError, KeyError, TypeError, ValueError, ImportError) as exc:
        print(f"reference generation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
