from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import platform
import sys
from pathlib import Path
from typing import Any, Dict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one ground-truth model in OpenSeesPy")
    parser.add_argument("--sclaw-root", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def configure_imports(root: Path) -> None:
    paths = [
        root / "backend" / "src" / "agent-skills" / "analysis" / "opensees-static",
        root / "backend" / "src" / "agent-skills" / "analysis" / "runtime",
        root / "backend" / "src" / "skill-shared" / "python",
    ]
    for path in reversed(paths):
        sys.path.insert(0, str(path))


def ensure_finite(value: Any, path: str = "result") -> None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise ValueError(f"{path} is not finite")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            ensure_finite(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            ensure_finite(item, f"{path}.{key}")
        return
    raise TypeError(f"{path} contains unsupported value type {type(value).__name__}")


def solver_configuration(execution_variant: str, truss: bool) -> Dict[str, str]:
    if execution_variant == "canonical-order":
        return {
            "system": "BandGeneral",
            "numberer": "Plain",
            "constraints": "Plain",
            "algorithm": "Linear" if truss else "Newton",
        }
    return {
        "system": "FullGeneral",
        "numberer": "RCM",
        "constraints": "Plain",
        "algorithm": "Newton" if truss else "Linear",
    }


def configure_static_analysis(ops: Any, configuration: Dict[str, str]) -> None:
    ops.system(configuration["system"])
    ops.numberer(configuration["numberer"])
    ops.constraints(configuration["constraints"])
    ops.integrator("LoadControl", 1.0)
    ops.algorithm(configuration["algorithm"])
    ops.analysis("Static")


def select_control(entries: list[tuple[str, float]]) -> tuple[float, str]:
    if not entries:
        return 0.0, ""
    maximum = max(value for _, value in entries)
    tie_tolerance = max(1e-12, maximum * 1e-10)
    controls = sorted(identifier for identifier, value in entries if maximum - value <= tie_tolerance)
    return maximum, controls[0]


def build_canonical_envelope(
    displacements: Dict[str, Any],
    forces: Dict[str, Any],
    reactions: Dict[str, Any],
) -> Dict[str, Any]:
    displacement_entries = []
    for node_id, value in displacements.items():
        displacement_entries.append((
            str(node_id),
            math.sqrt(sum(float(value.get(axis, 0.0)) ** 2 for axis in ("ux", "uy", "uz"))),
        ))
    axial_entries = []
    shear_entries = []
    moment_entries = []
    for element_id, value in forces.items():
        if not isinstance(value, dict):
            continue
        axial_entries.append((str(element_id), abs(float(value.get("axial", 0.0)))))
        for end in ("n1", "n2"):
            response = value.get(end)
            if isinstance(response, dict):
                shear_entries.append((str(element_id), abs(float(response.get("V", 0.0)))))
                moment_entries.append((str(element_id), abs(float(response.get("M", 0.0)))))
    reaction_entries = []
    for node_id, value in reactions.items():
        if isinstance(value, dict):
            components = [abs(float(component)) for component in value.values() if isinstance(component, (int, float))]
            if components:
                reaction_entries.append((str(node_id), max(components)))

    max_disp, control_disp = select_control(displacement_entries)
    max_axial, control_axial = select_control(axial_entries)
    max_shear, control_shear = select_control(shear_entries)
    max_moment, control_moment = select_control(moment_entries)
    max_reaction, control_reaction = select_control(reaction_entries)
    return {
        "maxAbsDisplacement": max_disp,
        "maxAbsAxialForce": max_axial,
        "maxAbsShearForce": max_shear,
        "maxAbsMoment": max_moment,
        "maxAbsReaction": max_reaction,
        "controlNodeDisplacement": control_disp,
        "controlElementAxialForce": control_axial,
        "controlElementShearForce": control_shear,
        "controlElementMoment": control_moment,
        "controlNodeReaction": control_reaction,
    }


def canonicalize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    canonical = dict(result)
    for field in ("displacements", "forces", "reactions"):
        values = canonical.get(field, {})
        if not isinstance(values, dict):
            raise ValueError(f"OpenSees result field '{field}' must be an object")
        canonical[field] = dict(sorted(values.items(), key=lambda item: str(item[0])))
    canonical["envelope"] = build_canonical_envelope(
        canonical["displacements"],
        canonical["forces"],
        canonical["reactions"],
    )
    canonical["summary"] = {
        "maxDisplacement": canonical["envelope"]["maxAbsDisplacement"],
        "maxDisplacementNode": canonical["envelope"]["controlNodeDisplacement"],
        "nodeCount": len(canonical["displacements"]),
        "elementCount": len(canonical["forces"]),
    }
    return canonical


def normalize_response_coordinates(result: Dict[str, Any]) -> Dict[str, Any]:
    """Map OpenSees' 2-D X-Z rotational sign to the global X-Y-Z convention."""
    normalized = dict(result)
    if normalized.get("analysisMode") == "opensees_2d_frame":
        displacements = {}
        for node_id, value in normalized.get("displacements", {}).items():
            node_value = dict(value)
            node_value["ry"] = -float(node_value.get("ry", 0.0))
            displacements[node_id] = node_value
        reactions = {}
        for node_id, value in normalized.get("reactions", {}).items():
            node_value = dict(value)
            node_value["my"] = -float(node_value.get("my", 0.0))
            reactions[node_id] = node_value
        normalized["displacements"] = displacements
        normalized["reactions"] = reactions
    normalized["responseCoordinateConvention"] = "global-xyz"
    return normalized


def run_truss(
    model: Any,
    analyzer: Any,
    ops: Any,
    parameters: Dict[str, Any],
    configuration: Dict[str, str],
) -> Dict[str, Any]:
    dimension = model.coordinate_system.dimension
    ndm = 2 if dimension == "2d" else 3
    ndf = ndm
    ops.wipe()
    ops.model("basic", "-ndm", ndm, "-ndf", ndf)

    for node in model.nodes:
        tag = analyzer._ops_node_tag(node.id)
        coordinates = [float(node.x), float(node.z)] if ndm == 2 else [float(node.x), float(node.y), float(node.z)]
        ops.node(tag, *coordinates)
        restraints = node.restraints or [False] * 6
        fixed = [restraints[0], restraints[2]] if ndm == 2 else restraints[:3]
        ops.fix(tag, *[int(bool(value)) for value in fixed])

    for material in model.materials:
        elastic_modulus = float(material.E) * 1000.0
        if not math.isfinite(elastic_modulus) or elastic_modulus <= 0:
            raise ValueError(f"Material '{material.id}' requires finite E > 0")
        ops.uniaxialMaterial("Elastic", analyzer._ops_material_tag(material.id), elastic_modulus)

    for element in model.elements:
        section = analyzer.sections.get(element.section)
        area = float(section.properties.get("A", 0.0)) if section else 0.0
        if not math.isfinite(area) or area <= 0:
            raise ValueError(f"Element '{element.id}' requires finite section A > 0")
        ops.element(
            "truss",
            analyzer._ops_element_tag(element.id),
            analyzer._ops_node_tag(element.nodes[0]),
            analyzer._ops_node_tag(element.nodes[1]),
            area,
            analyzer._ops_material_tag(element.material),
        )

    loads = analyzer._collect_nodal_loads(parameters)
    if any(load.get("type") != "nodal" for load in loads):
        raise ValueError("OpenSees truss truth generation supports nodal loads only")
    if loads:
        ops.timeSeries("Linear", 1)
        ops.pattern("Plain", 1, 1)
        for load in loads:
            values = [float(load.get("fx", 0.0)), float(load.get("fz", 0.0))] if ndm == 2 else [
                float(load.get("fx", 0.0)),
                float(load.get("fy", 0.0)),
                float(load.get("fz", 0.0)),
            ]
            ops.load(analyzer._ops_node_tag(load["node"]), *values)

    configure_static_analysis(ops, configuration)
    status = int(ops.analyze(1))
    if status != 0:
        raise RuntimeError(f"OpenSees truss analysis failed with code {status}")

    ops.reactions()
    displacements: Dict[str, Dict[str, float]] = {}
    reactions: Dict[str, Dict[str, float]] = {}
    for node in model.nodes:
        tag = analyzer._ops_node_tag(node.id)
        displacement = [float(value) for value in ops.nodeDisp(tag)]
        reaction = [float(value) for value in ops.nodeReaction(tag)]
        if ndm == 2:
            displacements[node.id] = {
                "ux": displacement[0], "uy": 0.0, "uz": displacement[1],
                "rx": 0.0, "ry": 0.0, "rz": 0.0,
            }
            if any(node.restraints or []):
                reactions[node.id] = {"fx": reaction[0], "fz": reaction[1]}
        else:
            displacements[node.id] = {
                "ux": displacement[0], "uy": displacement[1], "uz": displacement[2],
                "rx": 0.0, "ry": 0.0, "rz": 0.0,
            }
            if any(node.restraints or []):
                reactions[node.id] = {"fx": reaction[0], "fy": reaction[1], "fz": reaction[2]}

    forces: Dict[str, Dict[str, float]] = {}
    for element in model.elements:
        raw = ops.eleResponse(analyzer._ops_element_tag(element.id), "axialForce")
        axial = float(raw[0] if isinstance(raw, (list, tuple)) else raw)
        area = float(analyzer.sections[element.section].properties["A"])
        forces[element.id] = {"axial": axial, "stress": axial / area}

    return {
        "status": "success",
        "analysisMode": f"opensees_{dimension}_truss",
        "displacements": displacements,
        "forces": forces,
        "reactions": reactions,
    }


def main() -> None:
    args = parse_args()
    root = Path(args.sclaw_root).resolve()
    configure_imports(root)

    import openseespy.opensees as ops
    from opensees_static_analysis import OpenSeesStaticExecutor
    from runtime import OpenSeesStaticAnalyzer
    from structure_protocol.structure_model_v2 import StructureModelV2

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    model = StructureModelV2.model_validate(payload["model"])
    analyzer = OpenSeesStaticAnalyzer(model)
    if len(model.load_combinations) != 1:
        raise ValueError("Numerical truth requires exactly one explicitly selected load combination")
    combination = model.load_combinations[0]
    parameters = {"loadCombinationId": combination.id}
    is_truss = bool(model.elements) and all(element.type == "truss" for element in model.elements)
    configuration = solver_configuration(payload["executionVariant"], is_truss)
    try:
        if is_truss:
            result = run_truss(model, analyzer, ops, parameters, configuration)
        else:
            class TruthOpenSeesStaticExecutor(OpenSeesStaticExecutor):
                def _run_static_analysis(self, active_ops: Any) -> int:
                    configure_static_analysis(active_ops, configuration)
                    return int(active_ops.analyze(1))

            result = TruthOpenSeesStaticExecutor(analyzer).run(parameters)
        if result.get("status") != "success":
            raise RuntimeError(f"OpenSees returned status {result.get('status')!r}")
        if not str(result.get("analysisMode", "")).startswith("opensees_"):
            raise RuntimeError("Truth generation rejected a non-OpenSees analysis path")
        result = normalize_response_coordinates(result)
        result = canonicalize_result(result)
        ensure_finite(result)
        runtime_package = "openseespywin" if platform.system() == "Windows" else "openseespylinux"
        output = {
            "modelId": payload["modelId"],
            "executionVariant": payload["executionVariant"],
            "solverConfiguration": configuration,
            "analysisSelection": {
                "loadCombinationId": combination.id,
                "factors": combination.factors,
            },
            "solver": {
                "name": "OpenSeesPy",
                "packageVersion": importlib.metadata.version("openseespy"),
                "runtimePackage": runtime_package,
                "runtimePackageVersion": importlib.metadata.version(runtime_package),
                "version": str(ops.version()),
            },
            "result": result,
        }
        Path(args.output).write_text(
            json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
    finally:
        ops.wipe()


if __name__ == "__main__":
    main()
