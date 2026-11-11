"""Public physics revisions must preserve numeric inputs and turn disclosure."""
import json
from pathlib import Path
import tempfile
import unittest

from commercial.conventions import revise_authored_case


class ConventionMigration(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.contract = {
            "plannedEngine": "PKPM", "locale": "en",
            "sourcePlan": {"engine.analysisContract": "First-order linear elastic static analysis"},
            "attachments": ["properties.json", "future.json", "drawing.png"],
            "turns": [
                {"id": "t1", "instruction": "Use Euler-Bernoulli bending (no shear deformation)",
                 "attachments": ["properties.json", "drawing.png"], "state": 1},
                {"id": "t2", "instruction": "Replace the section with the newly supplied one.",
                 "attachments": ["future.json"], "state": 2}],
            "requirementCoverage": [{"sourceField": "engine.analysisContract", "targets": ["turn:t1"]}],
            "modelStates": ["model-state-1.json", "model-state-2.json"],
        }
        files = {
            "prompt.txt": b"Use Euler-Bernoulli bending (no shear deformation)\n",
            "properties.json": b'{"analysis":"Euler-Bernoulli", "A":1.800000000e-1, "E":206000.0}\n',
            "future.json": b'{"A":2.35e-1, "Iy":0.001267}\n',
            "model-state-1.json": b'{"section":{"A":0.18}, "loads":[-8.0,15]}\n',
            "model-state-2.json": b'{"section":{"A":0.235}, "loads":[-8.0,15]}\n',
            "reference-requests.json": b'{"tolerance":{"absolute":1e-8,"relative":1e-6}}\n',
            "drawing.png": b"\x89PNG\r\n\x1a\n\x00geometry-byte-evidence",
            "input.dxf": b"0\r\nLINE\r\n10\r\n6.0\r\n",
            "author-review.json": b'{"historicalDecision":"Euler-Bernoulli"}\n',
        }
        for name, data in files.items():
            (self.root / name).write_bytes(data)
        self.save_contract()

    def save_contract(self):
        (self.root / "contract.json").write_text(json.dumps(self.contract, ensure_ascii=False) + "\n")

    def files(self):
        return {p.name: p.read_bytes() for p in self.root.iterdir()}

    def test_revision_changes_public_physics_without_reauthoring_numeric_inputs(self):
        before = self.files()
        revise_authored_case(self.root)
        after = self.files()
        for name in before.keys() - {"contract.json", "prompt.txt", "properties.json"}:
            self.assertEqual(after[name], before[name], name)
        properties = json.loads(after["properties.json"])
        self.assertEqual(properties["A"], .18)
        self.assertEqual(properties["E"], 206000)
        self.assertIn(b'1.800000000e-1', after["properties.json"])
        self.assertEqual(properties["analysis"], "Timoshenko")
        self.assertNotIn(b"no shear deformation", after["prompt.txt"])
        contract = json.loads(after["contract.json"])
        self.assertEqual(contract["sourcePlan"], self.contract["sourcePlan"])
        self.assertEqual(contract["modelStates"], self.contract["modelStates"])
        self.assertEqual(contract["analysisConvention"]["bendingTheory"], "Timoshenko")

    def test_appendix_is_released_first_without_releasing_future_values(self):
        revise_authored_case(self.root)
        contract = json.loads((self.root / "contract.json").read_text())
        appendix = contract["analysisConvention"]["publicAttachment"]
        self.assertEqual(contract["turns"][0]["attachments"], ["properties.json", "drawing.png", appendix])
        self.assertEqual(contract["turns"][1], self.contract["turns"][1])
        self.assertIn(appendix, contract["attachments"])
        self.assertIn("attachment:" + appendix, contract["requirementCoverage"][0]["targets"])
        self.assertNotIn("0.235", (self.root / appendix).read_text())

    def test_reapplying_does_not_duplicate_release_or_change_bytes(self):
        revise_authored_case(self.root)
        before = self.files()
        self.assertEqual(revise_authored_case(self.root), [])
        self.assertEqual(self.files(), before)

    def test_opensees_public_and_private_files_remain_byte_identical(self):
        self.contract["plannedEngine"] = "OpenSees"
        self.save_contract()
        before = self.files()
        self.assertEqual(revise_authored_case(self.root), [])
        self.assertEqual(self.files(), before)

    def test_original_requirement_for_shear_free_physics_blocks_revision_before_writes(self):
        for token in ("Euler-Bernoulli", "Euler–Bernoulli", "Euler—Bernoulli", "不计剪切变形"):
            with self.subTest(token=token):
                self.contract["sourcePlan"]["engine.analysisContract"] = token
                self.save_contract()
                before = self.files()
                with self.assertRaisesRegex(ValueError, "Source"):
                    revise_authored_case(self.root)
                self.assertEqual(self.files(), before)

    def test_chinese_instruction_has_no_conflicting_old_convention(self):
        self.contract.update(plannedEngine="YJK", locale="zh")
        self.contract["turns"][0]["instruction"] = "采用Euler-Bernoulli弯曲（不计剪切变形）"
        self.save_contract()
        revise_authored_case(self.root)
        contract = json.loads((self.root / "contract.json").read_text())
        self.assertEqual(contract["turns"][0]["instruction"], "采用Timoshenko弯曲（计入规定的剪切变形）")
        self.assertEqual(contract["sourcePlan"], self.contract["sourcePlan"])


if __name__ == "__main__":
    unittest.main()
