"""Architectural geometry stays in DXF when commercial v2 text is public."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

import mm_b_architectural_checks as checks


ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "corpora/research-300/cases"
APPENDIX = "analysis-conventions-v2.txt"


class CommercialArchitecturalInputs(unittest.TestCase):
    def setUp(self):
        self.case = CASES / "MM-082"
        self.contract = json.loads((self.case / "contract.json").read_text())

    def inspect(self, contract=None, overrides=None):
        files = dict(overrides or {})
        if contract is not None:
            files["contract.json"] = json.dumps(contract).encode()
        return checks.inspect_case(self.case, files)["errors"]

    def assert_rejected(self, errors, reason):
        self.assertTrue(any(reason in error for error in errors), errors)

    def test_current_commercial_cases_reconstruct_from_dxf_with_v2_appendix(self):
        for cid, nodes, members in (("MM-082", 27, 40), ("MM-086", 36, 56)):
            with self.subTest(case=cid):
                result = checks.inspect_case(CASES / cid)
                self.assertEqual(result["errors"], [])
                self.assertEqual((result["nodeCount"], result["memberCount"]), (nodes, members))
                self.assertEqual(result["geometrySource"], "input.dxf")

    def test_original_six_file_opensees_cases_still_pass(self):
        for cid in ("MM-056", "MM-059", "MM-062", "MM-075"):
            with self.subTest(case=cid):
                self.assertEqual(checks.inspect_case(CASES / cid)["errors"], [])

    def test_chinese_v2_appendix_requires_its_matching_locale(self):
        self.contract["locale"] = "zh"
        text = (CASES / "MM-081" / APPENDIX).read_bytes()
        self.assertEqual(self.inspect(self.contract, {APPENDIX: text}), [])
        self.assert_rejected(self.inspect(overrides={APPENDIX: text}), "analysis convention text")

    def test_unknown_or_mismatched_declaration_is_rejected(self):
        original = self.contract["analysisConvention"]
        declarations = [None, {}, dict(original, id="commercial-linear-static-v3"),
                        dict(original, bendingTheory="Euler-Bernoulli"),
                        dict(original, effectiveShearAreas={"localY": "A", "localZ": "5*A/6"}),
                        dict(original, publicAttachment="other.txt"),
                        dict(original, privateModel="model-state-1.json")]
        for declaration in declarations:
            with self.subTest(declaration=declaration):
                contract = deepcopy(self.contract)
                contract["analysisConvention"] = declaration
                self.assert_rejected(self.inspect(contract), "analysis convention declaration")

    def test_convention_is_rejected_for_noncommercial_engine(self):
        self.contract["plannedEngine"] = "OpenSees"
        self.assert_rejected(self.inspect(self.contract), "analysis convention declaration")

    def test_appendix_without_declaration_does_not_extend_whitelist(self):
        del self.contract["analysisConvention"]
        self.assert_rejected(self.inspect(self.contract), "public attachment whitelist")

    def test_changed_or_extended_convention_cannot_smuggle_geometry_or_private_data(self):
        original = (self.case / APPENDIX).read_bytes()
        variants = [original.replace(b"Timoshenko", b"Euler-Bernoulli"),
                    original.replace(b"5*A/6", b"A"),
                    original + b"\nnode n1: (0, 0, 3.6); member c1: n0 -> n1\n",
                    original + (self.case / "model-state-1.json").read_bytes(),
                    (CASES / "MM-055" / "drawing-elevation-XZ.svg").read_bytes()]
        for text in variants:
            with self.subTest(length=len(text)):
                self.assert_rejected(self.inspect(overrides={APPENDIX: text}), "analysis convention text")

    def test_declared_appendix_must_exist(self):
        self.assert_rejected(self.inspect(overrides={APPENDIX: None}), "missing public attachment")

    def test_appendix_must_be_declared_once_in_public_and_turn_inputs(self):
        for scope in ("public", "turn"):
            for operation in ("remove", "duplicate"):
                with self.subTest(scope=scope, operation=operation):
                    contract = deepcopy(self.contract)
                    attachments = contract["attachments"] if scope == "public" else contract["turns"][0]["attachments"]
                    if operation == "remove":
                        attachments.remove(APPENDIX)
                    else:
                        attachments.append(APPENDIX)
                    self.assert_rejected(self.inspect(contract), "attachment whitelist")

    def test_declared_appendix_requires_analysis_coverage(self):
        for row in self.contract["requirementCoverage"]:
            if row["sourceField"] == "engine.analysisContract":
                row["targets"].remove("attachment:" + APPENDIX)
        self.assert_rejected(self.inspect(self.contract), "analysis convention coverage")

    def test_unrelated_text_and_private_model_still_fail_whitelist(self):
        for name, content in (("extra.txt", b"More public prose\n"),
                              ("model-state-1.json", (self.case / "model-state-1.json").read_bytes())):
            with self.subTest(name=name):
                contract = deepcopy(self.contract)
                contract["attachments"].append(name)
                contract["turns"][0]["attachments"].append(name)
                contract["requirementCoverage"][0]["targets"].append("attachment:" + name)
                errors = self.inspect(contract, {name: content})
                self.assert_rejected(errors, "public attachment whitelist")
                self.assert_rejected(errors, "coverage refers to removed/nonpublic")

    def test_existing_geometry_and_modality_negative_controls_still_reject(self):
        for cid in ("MM-056", "MM-082"):
            with self.subTest(case=cid):
                self.assertEqual(len(checks.negative_controls(CASES / cid)), 14)

    def test_actual_provider_preserves_declared_six_or_seven_file_boundary(self):
        result = checks.check_provider(CASES, ROOT / "lib/corpus-provider.cjs", Path("/opt/lab-node/bin/node"))
        self.assertEqual((result["cases"], result["turns"]), (6, 6))
        for turn in result["publicAttachmentsByTurn"]:
            expected = {"input.dxf", "properties.json", "assignments.json", "loads.json",
                        "section-details.png", "section-details.svg"}
            if turn["caseId"] in ("MM-082", "MM-086"):
                expected.add(APPENDIX)
            self.assertEqual(set(turn["attachments"]), expected)


if __name__ == "__main__":
    unittest.main()
