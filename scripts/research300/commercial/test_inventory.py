"""Coverage mistakes must not allow a one-state calibration to certify a corpus."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

try:
    from . import inventory
except ImportError:
    import inventory


def case():
    return {
        "id": "INT-001", "contract": {"plannedEngine": "YJK"},
        "sourceHash": "a" * 64, "hashes": {"model-state-1.json": "b" * 64},
        "states": [{"state": 1, "modelPath": "model-state-1.json", "model": {
            "coordinate_system": {"dimension": "3d"},
            "nodes": [{"id": "a", "restraints": [True] * 6},
                      {"id": "b", "restraints": [False] * 6}],
            "elements": [{"type": "column"}],
            "materials": [{"E": 200000., "G": 80000., "nu": .25}],
            "sections": [{"type": "general", "properties": {"A": .1, "Iy": .002, "Iz": .003, "J": .001}}],
            "analysis_control": {"self_weight": False, "p_delta": False},
            "load_cases": [{"id": "D", "loads": [{"type": "nodal"}]}],
        }, "quantities": [
            {"selection": {"kind": "case", "id": "D"}, "component": "ux", "location": {"kind": "node", "id": "b"}},
            {"selection": {"kind": "case", "id": "D"}, "component": "Fx", "location": {"kind": "node", "id": "a"}},
            {"selection": {"kind": "combination", "id": "D"}, "component": "N", "location": {"kind": "member", "id": "c", "positionM": 0., "side": "right"}},
        ], "derived": [{"operation": "max_abs"}]}],
    }


class InventoryTests(unittest.TestCase):
    def test_distinguishes_selection_kind_and_does_not_collapse_revised_states(self):
        data = case()
        revised = copy.deepcopy(data["states"][0])
        revised.update(state=2, modelPath="model-state-2.json")
        revised["model"]["materials"][0]["E"] = 210000.
        data["states"].append(revised)
        data["hashes"]["model-state-2.json"] = "c" * 64
        report = inventory.summarize_case(data, "Euler-Bernoulli", "d" * 64)
        self.assertEqual(report["selectionCount"], 4)
        self.assertEqual(report["quantityCount"], 6)
        self.assertEqual(report["derivedCount"], 2)
        self.assertEqual(report["states"][1]["materials"][0]["E"], 210000.)
        self.assertEqual(report["states"][1]["modelSha256"], "c" * 64)
        self.assertEqual(report["states"][0]["selections"], [
            {"kind": "case", "id": "D"}, {"kind": "combination", "id": "D"}])
        self.assertEqual(report["states"][0]["outputs"], {"member": ["N"], "node": ["Fx", "ux"]})
        self.assertEqual(report["states"][0]["analysisControl"]["p_delta"], False)
        self.assertNotIn("nativeVerified", report)

    def test_missing_control_remains_missing_instead_of_becoming_false(self):
        result = inventory.summarize_case(case(), "Euler-Bernoulli", "d" * 64)
        self.assertNotIn("rigid_floor", result["states"][0]["analysisControl"])
        self.assertEqual(result["states"][0]["supportPatterns"], [[False]*6, [True]*6])
        self.assertEqual(result["states"][0]["sectionTypes"], ["general"])

    def test_bending_theory_never_infers_eb_from_linear_elastic_analysis(self):
        self.assertEqual(inventory.bending_theory("Analysis with Euler-Bernoulli bending (no shear deformation)."),
                         "Euler-Bernoulli")
        self.assertEqual(inventory.bending_theory("Euler-Bernoulli beam/column and axial-only truss analysis."),
                         "Euler-Bernoulli")
        self.assertEqual(inventory.bending_theory("linear static analysis"), "unspecified")
        self.assertEqual(inventory.bending_theory("Timoshenko"), "Timoshenko")
        with self.assertRaises(ValueError):
            inventory.bending_theory("Euler-Bernoulli or Timoshenko")

    def test_revised_public_inputs_declare_finite_shear_in_every_state(self):
        root = Path(__file__).resolve().parents[3] / "corpora/research-300/cases"
        with tempfile.TemporaryDirectory() as temporary:
            for identifier in ("MM-079", "INT-084"):
                shutil.copytree(root / identifier, Path(temporary) / identifier)
            report = inventory.inventory(temporary)
        indexed = {row["id"]: row for row in report["cases"]}
        self.assertEqual(indexed["MM-079"]["bendingTheory"], "Timoshenko")
        self.assertEqual(indexed["INT-084"]["bendingTheory"], "Timoshenko")
        self.assertEqual(len(indexed["INT-084"]["states"]), 2)
        for identifier in ("MM-079", "INT-084"):
            self.assertIn("analysis-conventions-v2.txt", [source["path"]
                for source in indexed[identifier]["bendingConventionSources"]])
        self.assertEqual(report["status"], "inventory-only")

    def test_hidden_model_or_generated_answers_cannot_supply_public_theory(self):
        root = Path(__file__).resolve().parents[3] / "corpora/research-300/cases"
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "MM-081"
            shutil.copytree(root / "MM-081", directory)
            # Deliberately remove public theory in this synthetic copy. Hidden
            # model metadata and generated answers must not fill the omission.
            contract_path = directory / "contract.json"
            contract = json.loads(contract_path.read_text())
            contract["attachments"] = []
            contract.pop("analysisConvention", None)
            for turn in contract["turns"]:
                turn["attachments"] = []
                turn["instruction"] = "Linear static analysis."
            contract_path.write_text(json.dumps(contract))
            (directory / "prompt.txt").write_text("Linear static analysis.\n")
            model_path = directory / "model-state-1.json"
            model = json.loads(model_path.read_text())
            model["metadata"]["privateAnalysisMethod"] = "Euler-Bernoulli"
            model_path.write_text(json.dumps(model))
            (directory / "independent-reference.json").write_text('{"theory":"Euler-Bernoulli"}')
            self.assertEqual(inventory.inventory(temporary)["cases"][0]["bendingTheory"], "unspecified")
            with (directory / "prompt.txt").open("a") as prompt:
                prompt.write("\nUse Timoshenko bending with explicitly supplied shear areas.\n")
            report = inventory.inventory(temporary)
            self.assertEqual(report["cases"][0]["bendingTheory"], "Timoshenko")
            self.assertEqual(report["cases"][0]["bendingConventionSources"][0]["path"], "prompt.txt")


if __name__ == "__main__":
    unittest.main()
