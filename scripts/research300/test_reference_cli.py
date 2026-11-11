"""Regression tests for the independent reference boundary, units and provenance."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import patch

try:
    from . import reference_cli as cli
    from . import reference_io as rio
except ImportError:
    import reference_cli as cli
    import reference_io as rio


def model():
    return {
        "schema_version": "2.2.0", "unit_system": "SI",
        "coordinate_system": {"dimension": "2d", "plane": "xz", "semantics": "global-z-up"},
        "nodes": [
            {"id": "a", "x": 0, "y": 0, "z": 0, "restraints": [True] * 6},
            {"id": "b", "x": 4, "y": 0, "z": 0, "restraints": [False, True, False, True, False, True]},
        ],
        "elements": [{"id": "e", "type": "beam", "nodes": ["a", "b"], "material": "mat", "section": "sec"}],
        "materials": [{"id": "mat", "E": 200000, "G": 80000, "rho": 7850}],
        "sections": [{"id": "sec", "properties": {"A": .1, "Iy": .001, "Iz": .002, "J": .001}}],
        "load_cases": [
            {"id": "D", "loads": [{"id": "p", "type": "nodal", "node": "b", "fz": -3}]},
            {"id": "L", "loads": [{"id": "p", "type": "nodal", "node": "b", "fz": 1}]},
        ],
        "load_combinations": [{"id": "D", "factors": {"D": 1, "L": 2}}],
        "analysis_control": {"self_weight": False, "rigid_floor": False, "p_delta": False,
                             "rigid_offsets": False, "construction_stage": False},
        "metadata": {},
    }


def request(key="down", selected="D", kind="case", unit="mm", component="uz"):
    return {"id": key, "selection": {"kind": kind, "id": selected},
            "location": {"kind": "node", "id": "b"}, "component": component, "unit": unit}


class ReferenceIOTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.case = self.root / "cases" / "STD-001"
        self.case.mkdir(parents=True)
        self.output = self.root / "output"
        self.contract = {"schemaVersion": 1, "id": "STD-001", "modelStates": ["model-state-1.json"],
                         "attachments": [],
                         "plannedEngine": "OpenSees", "evaluationProfile": "engineering-v2.3"}
        self.requests = {"schemaVersion": 1, "states": [{
            "state": 1, "model": "model-state-1.json", "quantities": [request()], "derived": []}]}
        self.write_inputs()

    def write_json(self, name, payload):
        (self.case / name).write_text(json.dumps(payload), encoding="utf-8")

    def write_inputs(self):
        (self.case / "prompt.txt").write_text("Analyze the authored cantilever.\n", encoding="utf-8")
        self.write_json("contract.json", self.contract)
        self.write_json("reference-requests.json", self.requests)
        self.write_json("model-state-1.json", model())

    @staticmethod
    def fake_solver(structure, factors, stations):
        # Analytic free-end bending displacement of a cantilever. Factor signs
        # must survive grouping and declared-unit conversion in the CLI.
        results = []
        for factor in factors:
            force = -3 * factor.get("D", 0) + factor.get("L", 0)
            displacement = force * 4 ** 3 / (3 * 200000 * 1000 * .001)
            def calculate(location, component, value=displacement, load=force):
                return value if component == "uz" else -load
            results.append((calculate, {"method": "analytic-cantilever", "freeResidual": 0.0}))
        return results

    def test_case_and_same_named_combination_remain_distinct(self):
        structure = model()
        self.assertEqual(rio.selection_factors(structure, {"kind": "case", "id": "D"}), {"D": 1})
        self.assertEqual(rio.selection_factors(structure, {"kind": "combination", "id": "D"}), {"D": 1, "L": 2})
        self.requests["states"][0]["quantities"] = [request(), request("combined", kind="combination")]
        self.write_inputs()
        reference = cli.generate_reference(rio.load_case(self.case), self.fake_solver)
        quantities = reference["states"][0]["quantities"]
        self.assertAlmostEqual(quantities[0]["value"], -.32)
        self.assertAlmostEqual(quantities[1]["value"], -.10666666666666667)
        self.assertEqual([item["selection"]["kind"] for item in reference["checks"]], ["case", "combination"])

    def test_default_and_frozen_tolerances_are_in_requested_units(self):
        self.requests["states"][0]["quantities"].append(request("force", unit="N", component="Fz"))
        frozen = {"absolute": .0123, "relative": 2e-5, "justification": "Frozen engineering decision"}
        self.requests["states"][0]["quantities"][1]["tolerance"] = frozen
        self.write_inputs()
        result = cli.generate_reference(rio.load_case(self.case), self.fake_solver)
        first, second = result["states"][0]["quantities"]
        self.assertEqual(first["tolerance"], {"absolute": 1e-8, "relative": 1e-6})
        self.assertEqual(second["tolerance"], frozen)
        self.assertEqual(second["value"], 3000)
        self.assertEqual(rio.convert_value(-2, "kN.m", "N.mm"), -2000000)
        self.assertAlmostEqual(rio.convert_value(3.141592653589793, "rad", "deg"), 180)
        with self.assertRaisesRegex(rio.ReferenceInputError, "Incompatible"):
            rio.convert_value(1, "m", "kN")

    def test_derived_extrema_keep_signed_governing_selection(self):
        quantities = [dict(request("down"), value=-8),
                      dict(request("up", "L", unit="m"), value=.006),
                      dict(request("smaller", kind="combination"), value=-2)]
        records = [{"id": operation, "operation": operation, "operands": ["down", "up"], "unit": "mm"}
                   for operation in ("difference", "max", "min", "max_abs")]
        result = {item["id"]: item for item in rio.evaluate_derived(quantities, records)}
        self.assertEqual(result["difference"]["value"], -14)
        self.assertEqual(result["max"]["value"], 6)
        self.assertEqual(result["min"]["value"], -8)
        self.assertEqual(result["max_abs"]["value"], -8)
        self.assertEqual(result["max_abs"]["governingOperand"], "down")
        self.assertEqual(result["max_abs"]["governingSelection"], {"kind": "case", "id": "D"})
        self.assertEqual(result["max"]["governingSelection"], {"kind": "case", "id": "L"})

    def test_opposite_signed_roundoff_ties_are_canonical_for_first_and_any(self):
        for policy in (None, "first", "any"):
            for values in ((-19.2, 19.20000000000002), (-19.20000000000002, 19.2)):
                with self.subTest(policy=policy, values=values):
                    quantities = [dict(request("TC2", unit="kN", component="N"), value=values[0]),
                                  dict(request("BC3", "L", unit="kN", component="N"), value=values[1])]
                    record = {"id": "envelope", "operation": "max_abs", "operands": ["TC2", "BC3"], "unit": "kN"}
                    if policy is not None:
                        record["tiePolicy"] = policy
                    original = deepcopy((quantities, record))
                    result, = rio.evaluate_derived(quantities, [record])
                    self.assertEqual(result["value"], values[0])
                    self.assertEqual(result["governingOperand"], "TC2")
                    self.assertEqual(result["coGoverningOperands"], ["TC2", "BC3"])
                    self.assertEqual(result["governingLeafOperands"], ["TC2"])
                    self.assertEqual(result["governingSelection"], quantities[0]["selection"])
                    self.assertEqual(result["governingSelections"], [quantities[0]["selection"]])
                    self.assertEqual(result.get("tiePolicy", "first"), policy or "first")
                    self.assertEqual((quantities, record), original)

    def test_exact_default_tie_preserves_declared_order(self):
        quantities = [dict(request(key, key, kind="combination"), value=-8) for key in ("C0", "C1", "C2")]
        result, = rio.evaluate_derived(quantities, [{"id": "envelope", "operation": "max_abs",
            "operands": ["C2", "C0", "C1"], "unit": "mm"}])
        self.assertEqual(result["coGoverningOperands"], ["C2", "C0", "C1"])
        self.assertEqual(result["governingOperand"], "C2")
        self.assertEqual(result["governingSelection"], {"kind": "combination", "id": "C2"})

    def test_extrema_tie_boundary_uses_absolute_best_score(self):
        # Exactly representable boundary: .125 + .0625 * abs(16) == 1.125.
        cases = (("max", [14.874999, 14.875, 16]),
                 ("max", [-17.125001, -17.125, -16]),
                 ("min", [-14.874999, -14.875, -16]),
                 ("min", [17.125001, 17.125, 16]),
                 ("max_abs", [-14.874999, -14.875, 16]))
        for operation, values in cases:
            with self.subTest(operation=operation, values=values):
                quantities = [dict(request(key), value=value) for key, value in zip(("outside", "boundary", "best"), values)]
                tolerance = {"absolute": .125, "relative": .0625, "justification": "Frozen before solve"}
                result, = rio.evaluate_derived(quantities, [{"id": "envelope", "operation": operation,
                    "operands": ["outside", "boundary", "best"], "unit": "mm", "tolerance": tolerance}])
                self.assertEqual(result["coGoverningOperands"], ["boundary", "best"])
                self.assertEqual(result["governingOperand"], "boundary")
                self.assertEqual(result["value"], values[1])
                self.assertEqual(result["tolerance"], tolerance)

    def test_tie_budget_is_derived_tolerance_after_requested_unit_conversion(self):
        quantities = [dict(request("negative", unit="kN", component="N"), value=-19.1995,
                           tolerance={"absolute": 1000, "relative": 1}),
                      dict(request("positive", "L", unit="N", component="N"), value=19200)]
        record = {"id": "envelope", "operation": "max_abs", "operands": ["negative", "positive"],
                  "unit": "N", "tolerance": {"absolute": .51, "relative": 0}}
        tied, = rio.evaluate_derived(quantities, [record])
        self.assertEqual(tied["coGoverningOperands"], ["negative", "positive"])
        self.assertEqual(tied["value"], quantities[0]["value"] * 1000)
        record["tolerance"]["absolute"] = .49
        outside, = rio.evaluate_derived(quantities, [record])
        self.assertEqual(outside["coGoverningOperands"], ["positive"])
        self.assertEqual(outside["value"], 19200)
        del record["tolerance"]
        default, = rio.evaluate_derived(quantities, [record])
        self.assertEqual(default["coGoverningOperands"], ["positive"])

    def test_co_governors_are_measured_from_best_without_transitive_ties(self):
        quantities = [dict(request(key), value=value) for key, value in zip(("a", "b", "c"), (9.82, 9.91, 10))]
        result, = rio.evaluate_derived(quantities, [{"id": "envelope", "operation": "max",
            "operands": ["a", "b", "c"], "unit": "mm", "tolerance": {"absolute": .1, "relative": 0}}])
        self.assertEqual(result["coGoverningOperands"], ["b", "c"])
        self.assertEqual(result["value"], 9.91)

    def test_zero_tolerance_requires_exact_score_tie(self):
        quantities = [dict(request("a"), value=-19.2), dict(request("b"), value=19.20000000000002)]
        result, = rio.evaluate_derived(quantities, [{"id": "envelope", "operation": "max_abs",
            "operands": ["a", "b"], "unit": "mm", "tolerance": {"absolute": 0, "relative": 0}}])
        self.assertEqual(result["coGoverningOperands"], ["b"])
        self.assertEqual(result["value"], quantities[1]["value"])

    def test_tie_cascade_keeps_only_canonical_leaf_identities(self):
        quantities = [dict(request("roof", kind="combination"), value=-21.2),
                      dict(request("floor", kind="combination"), value=-2),
                      dict(request("other", "L"), value=19.20000000000002)]
        records = [
            {"id": "drift", "operation": "difference", "operands": ["roof", "floor"], "unit": "mm"},
            {"id": "envelope", "operation": "max_abs", "operands": ["drift", "other"], "unit": "m", "tiePolicy": "any"},
            {"id": "nested", "operation": "max_abs", "operands": ["envelope", "other"], "unit": "mm"},
        ]
        results = rio.evaluate_derived(quantities, records)
        self.assertEqual(results[1]["coGoverningOperands"], ["drift", "other"])
        self.assertEqual(results[2]["coGoverningOperands"], ["envelope", "other"])
        for result in results[1:]:
            self.assertLess(result["value"], 0)
            self.assertEqual(result["governingLeafOperands"], ["roof", "floor"])
            self.assertEqual(result["governingSelection"], {"kind": "combination", "id": "D"})

    def test_co_governing_metadata_is_recomputed_and_removed_from_arithmetic(self):
        quantities = [dict(request("a"), value=-8), dict(request("b"), value=8)]
        records = [{"id": operation, "operation": operation, "operands": ["a", "b"], "unit": "mm",
                    "coGoverningOperands": ["invented"], "governingOperand": "invented"}
                   for operation in ("sum", "difference", "max_abs")]
        total, difference, envelope = rio.evaluate_derived(quantities, records)
        for result in (total, difference):
            self.assertNotIn("coGoverningOperands", result)
            self.assertNotIn("governingOperand", result)
        self.assertEqual(envelope["coGoverningOperands"], ["a", "b"])

    def test_invalid_tie_policies_and_tolerances_fail_before_solver(self):
        invalid = [{"tiePolicy": value} for value in (None, True, 1, "", "FIRST", "all", [], {})]
        invalid += [{"tolerance": value} for value in (None, {}, {"absolute": -1, "relative": 0},
            {"absolute": 0, "relative": -1}, {"absolute": True, "relative": 0},
            {"absolute": "1", "relative": 0})]
        for operation in ("max", "min", "max_abs", "sum", "difference"):
            for fields in invalid:
                with self.subTest(operation=operation, fields=fields):
                    self.requests["states"][0]["quantities"] = [request("a"), request("b", "L")]
                    self.requests["states"][0]["derived"] = [dict(id="envelope", operation=operation,
                        operands=["a", "b"], unit="mm", **fields)]
                    self.write_inputs()
                    with self.assertRaises(rio.ReferenceInputError):
                        cli.generate_case(self.case, self.output, lambda *args: self.fail("Invalid tie policy reached solver"))
                    self.assertFalse(self.output.exists())

    def test_ids_are_unique_per_selection_but_ambiguous_operands_fail(self):
        state = self.requests["states"][0]
        state["quantities"].append(request(kind="combination"))
        self.write_inputs()
        self.assertEqual(len(rio.load_case(self.case)["states"][0]["quantities"]), 2)
        state["derived"] = [{"id": "envelope", "operation": "max_abs", "operands": ["down"], "unit": "mm"}]
        self.write_inputs()
        with self.assertRaisesRegex(rio.ReferenceInputError, "Ambiguous derived operand"):
            rio.load_case(self.case)
        state["derived"] = []
        state["quantities"][1] = request()
        self.write_inputs()
        with self.assertRaisesRegex(rio.ReferenceInputError, "Duplicate quantity ID within selection"):
            rio.load_case(self.case)

    def test_signed_sum_converts_units_and_retains_operand_selections(self):
        quantities = [dict(request("a", unit="kN", component="Fz"), value=-8),
                      dict(request("b", unit="N", component="Fz"), value=6000),
                      dict(request("c", unit="kN", component="Fz"), value=-1)]
        result, = rio.evaluate_derived(quantities, [
            {"id": "total", "operation": "sum", "operands": ["a", "b", "c"], "unit": "N"}])
        self.assertEqual(result["value"], -3000)
        self.assertEqual(result["selection"], {"kind": "case", "id": "D"})
        self.assertEqual(result["operandSelections"], [q["selection"] for q in quantities])

    def test_cascaded_drift_envelope_retains_signed_value_and_leaf_selection(self):
        quantities = [dict(request("D-roof", kind="combination"), value=-12),
                      dict(request("D-floor", kind="combination", unit="m"), value=-.002),
                      dict(request("L-roof", "L", kind="combination"), value=9),
                      dict(request("L-floor", "L", kind="combination"), value=1)]
        records = [
            {"id": "D-drift", "operation": "difference", "operands": ["D-roof", "D-floor"], "unit": "mm"},
            {"id": "L-drift", "operation": "difference", "operands": ["L-roof", "L-floor"], "unit": "mm"},
            {"id": "drift-envelope", "operation": "max_abs", "operands": ["D-drift", "L-drift"], "unit": "m"},
            {"id": "nested", "operation": "min", "operands": ["drift-envelope", "L-drift"], "unit": "mm"},
        ]
        results = rio.evaluate_derived(quantities, records)
        self.assertEqual([r["value"] for r in results], [-10, 8, -.01, -10])
        self.assertEqual(results[2]["governingOperand"], "D-drift")
        for result in results[2:]:
            self.assertEqual(result["governingSelection"], {"kind": "combination", "id": "D"})
            self.assertEqual(result["governingLeafOperands"], ["D-roof", "D-floor"])

    def test_cascade_does_not_invent_single_selection_for_cross_case_difference(self):
        quantities = [dict(request("a"), value=-8), dict(request("b", "L"), value=2)]
        results = rio.evaluate_derived(quantities, [
            {"id": "delta", "operation": "difference", "operands": ["a", "b"], "unit": "mm"},
            {"id": "env", "operation": "max_abs", "operands": ["delta"], "unit": "mm"}])
        self.assertNotIn("selection", results[0])
        self.assertIsNone(results[1]["governingSelection"])
        self.assertEqual(results[1]["governingSelections"], [q["selection"] for q in quantities])
        self.assertEqual(results[1]["value"], -10)

    def test_malformed_sum_and_cascades_fail_before_solver(self):
        def derived(key="total", operands=None, operation="sum", unit="mm"):
            return {"id": key, "operation": operation, "operands": ["down"] if operands is None else operands, "unit": unit}
        invalid = [
            [derived(operands=[])], [derived(operands="down")], [derived(operands=["down", "down"])],
            [derived(operands=[True])], [derived(unit="kN")], [derived(unit="bogus")],
            [derived(operands=["missing"])], [derived(operands=["total"])],
            [derived(operands=["later"]), derived("later")],
            [derived(operands=["later"]), derived("later", ["total"])],
            [derived(), derived()], [derived("down")],
            [derived(operation="difference")], [dict(derived(), value=0)],
            [derived(), derived("env", ["total"], "max_abs", "kN")],
        ]
        for records in invalid:
            with self.subTest(records=records):
                self.requests["states"][0]["derived"] = records
                self.write_inputs()
                with self.assertRaises(rio.ReferenceInputError):
                    cli.generate_case(self.case, self.output, lambda *args: self.fail("Malformed derived reached solver"))
                self.assertFalse(self.output.exists())

    def test_derived_sum_cancellation_and_overflow(self):
        quantities = [dict(request(str(i)), value=value) for i, value in enumerate([1e16, 1, -1e16])]
        record = {"id": "total", "operation": "sum", "operands": ["0", "1", "2"], "unit": "mm"}
        self.assertEqual(rio.evaluate_derived(quantities, [record])[0]["value"], 1)
        for q in quantities:
            q["value"] = 1e308
        with self.assertRaises(rio.ReferenceInputError):
            rio.evaluate_derived(quantities, [record])

    def test_source_binding_covers_authored_bytes_in_utf8_path_order(self):
        names = ["附件.json", "\U00010000.png", "\ue000.bin", "A.txt"]
        for name in names:
            (self.case / name).write_bytes(b"public input \x00\xff")
        self.contract["attachments"] = names + [names[0], "prompt.txt"]
        self.write_inputs()
        result = rio.load_case(self.case)
        expected_paths = sorted(set(["contract.json", "prompt.txt", "reference-requests.json", "model-state-1.json"] + names), key=lambda s: s.encode("utf-8"))
        manifest = {"schemaVersion": 1, "files": [
            {"path": name, "sha256": hashlib.sha256((self.case / name).read_bytes()).hexdigest()}
            for name in expected_paths]}
        self.assertEqual(result["sourceManifest"], manifest)
        self.assertEqual(result["sourceHash"], hashlib.sha256(json.dumps(
            manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest())
        self.assertEqual(set(result["hashes"]), {"contract.json", "reference-requests.json", "model-state-1.json"})
        reference = cli.generate_reference(result, self.fake_solver)
        self.assertEqual(reference["sourceHash"], result["sourceHash"])
        self.assertEqual(reference["sourceManifest"], manifest)
        for name in expected_paths:
            with self.subTest(name=name):
                file = self.case / name
                previous = file.read_bytes()
                file.write_bytes(previous + b"\n")
                self.assertNotEqual(rio.load_case(self.case)["sourceHash"], result["sourceHash"])
                file.write_bytes(previous)
        (self.case / "independent-reference.json").write_text('{"value": 123}')
        (self.case / "reference-provenance.json").write_text('{"status": "validated"}')
        (self.case / "native-opensees-reference.json").write_text('{"value": 456}')
        self.assertEqual(rio.load_case(self.case)["sourceHash"], result["sourceHash"])

    def test_source_binding_rejects_missing_unsafe_and_generated_inputs(self):
        for attachment in ("missing.png", "../outside.png", "native-input-receipt.json", "independent-reference.json", "reference-provenance.json"):
            self.contract["attachments"] = [attachment]
            self.write_inputs()
            with self.subTest(attachment=attachment), self.assertRaises((rio.ReferenceInputError, OSError)):
                rio.load_case(self.case)
        self.contract["attachments"] = []
        self.write_inputs()
        (self.case / "prompt.txt").unlink()
        with self.assertRaises(OSError):
            rio.load_case(self.case)

    def test_source_binding_rejects_public_symlinks_and_nonregular_files(self):
        import os
        (self.root / "outside.png").write_bytes(b"image")
        (self.case / "image.png").symlink_to(self.root / "outside.png")
        (self.case / "directory").symlink_to(self.root, target_is_directory=True)
        os.mkfifo(self.case / "pipe.png")
        for attachment in ("image.png", "directory/outside.png", "pipe.png"):
            self.contract["attachments"] = [attachment]
            self.write_inputs()
            with self.subTest(attachment=attachment), self.assertRaises((rio.ReferenceInputError, OSError)):
                rio.load_case(self.case)
    def test_hashes_bind_exact_input_bytes(self):
        before = rio.load_case(self.case)
        for filename, digest in before["hashes"].items():
            self.assertEqual(digest, hashlib.sha256((self.case / filename).read_bytes()).hexdigest())
        filename = self.case / "model-state-1.json"
        filename.write_bytes(filename.read_bytes() + b"\n")
        after = rio.load_case(self.case)
        self.assertNotEqual(before["hashes"][filename.name], after["hashes"][filename.name])
        self.assertEqual(before["states"][0]["model"], after["states"][0]["model"])

    def test_generate_case_creates_isolated_output_and_never_overwrites(self):
        original_files = {item.name: item.read_bytes() for item in self.case.iterdir()}
        destination = cli.generate_case(self.case, self.output, self.fake_solver)
        self.assertEqual(destination, self.output / "STD-001" / "independent-reference.json")
        original_result = destination.read_bytes()
        with self.assertRaises(FileExistsError):
            cli.generate_case(self.case, self.output, lambda *args: self.fail("Should refuse before solving"))
        self.assertEqual(destination.read_bytes(), original_result)
        self.assertEqual(original_files, {item.name: item.read_bytes() for item in self.case.iterdir()})
        result = json.loads(original_result)
        self.assertEqual(result["sameEngineTruthStatus"], "pending")
        self.assertTrue(result["notCommercialScoringTruth"])
        self.assertEqual(result["inputHashes"], rio.load_case(self.case)["hashes"])

    def test_exclusive_writer_rejects_dangling_symlink_and_symlink_parent(self):
        target = self.root / "artifact.json"
        target.symlink_to(self.root / "missing.json")
        with self.assertRaises(FileExistsError):
            rio.write_json_exclusive(target, {"a": 1})
        self.assertFalse((self.root / "missing.json").exists())
        link = self.root / "linked-output"
        link.symlink_to(self.case, target_is_directory=True)
        with self.assertRaises(OSError):
            rio.write_json_exclusive(link / "escaped.json", {})
        self.assertFalse((self.case / "escaped.json").exists())

    def test_model_paths_cannot_traverse_or_follow_symlinks(self):
        for filename in ("../model.json", "/tmp/model.json", "folder/../../model.json", "folder\\model.json"):
            with self.subTest(filename=filename):
                self.contract["modelStates"] = [filename]
                self.requests["states"][0]["model"] = filename
                self.write_inputs()
                with self.assertRaisesRegex(rio.ReferenceInputError, "Unsafe relative"):
                    rio.load_case(self.case)
        self.contract["modelStates"] = ["model-state-1.json"]
        self.requests["states"][0]["model"] = "model-state-1.json"
        self.write_inputs()
        outside = self.root / "outside.json"
        outside.write_text(json.dumps(model()))
        (self.case / "model-state-1.json").unlink()
        (self.case / "model-state-1.json").symlink_to(outside)
        with self.assertRaises(OSError):
            rio.load_case(self.case)

    def test_nonregular_and_duplicate_key_json_are_rejected(self):
        (self.case / "contract.json").write_text('{"schemaVersion":1,"schemaVersion":2}')
        with self.assertRaisesRegex(rio.ReferenceInputError, "Duplicate JSON key"):
            rio.load_case(self.case)
        for number in ("NaN", "Infinity", "1e999"):
            (self.case / "contract.json").write_text('{"number":' + number + '}')
            with self.assertRaisesRegex(rio.ReferenceInputError, "[Nn]on-finite"):
                rio.load_case(self.case)
        import os
        fifo = self.case / "pipe.json"
        os.mkfifo(fifo)
        with self.assertRaisesRegex(rio.ReferenceInputError, "regular file"):
            rio.read_json_safe(self.case, fifo.name)

    def test_invalid_selections_and_factors_fail_closed(self):
        for selection in ({"kind": "case", "id": "missing"}, {"kind": "combination", "id": "L"},
                          {"kind": "auto", "id": "D"}, {"id": "D"}):
            with self.subTest(selection=selection), self.assertRaises(rio.ReferenceInputError):
                rio.selection_factors(model(), selection)
        for factors in ({"missing": 1}, {"D": True}, {"D": float("nan")}, {}):
            structure = model()
            structure["load_combinations"][0]["factors"] = factors
            with self.subTest(factors=factors), self.assertRaises(rio.ReferenceInputError):
                rio.selection_factors(structure, {"kind": "combination", "id": "D"})

    def test_wrong_units_locations_and_answer_values_fail_before_solver(self):
        bad_requests = [dict(request(), unit="kN"), dict(request(), value=1),
                        dict(request(), tolerance={"absolute": -1, "relative": 1e-6}),
                        dict(request(), location={"kind": "member", "id": "e", "positionM": 5, "side": "left"}),
                        dict(request(), location={"kind": "member", "id": "e", "positionM": 2}),
                        dict(request(), location={"kind": "node", "id": "unknown"})]
        for quantity in bad_requests:
            self.requests["states"][0]["quantities"] = [quantity]
            self.write_inputs()
            with self.subTest(quantity=quantity), self.assertRaises(rio.ReferenceInputError):
                cli.generate_case(self.case, self.output, lambda *args: self.fail("Invalid request reached solver"))

    def test_main_accepts_single_and_filtered_corpus_paths(self):
        original = cli.generate_reference
        with patch.object(cli, "generate_reference", side_effect=lambda case, solver=None: original(case, self.fake_solver)), \
                patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(cli.main(["--case-dir", str(self.case), "--output-root", str(self.output)]), 0)
            self.assertEqual(cli.main(["--cases-root", str(self.case.parent), "--case", "STD-001",
                                       "--output-root", str(self.root / "filtered")]), 0)
        with patch("sys.stderr", new_callable=io.StringIO) as error:
            self.assertEqual(cli.main(["--cases-root", str(self.case.parent), "--case", "../STD-001",
                                       "--output-root", str(self.root / "invalid")]), 1)
            self.assertIn("Invalid research-300 case ID", error.getvalue())

    def test_cli_process_reports_bad_inputs_without_writing(self):
        self.requests["states"][0]["quantities"][0]["unit"] = "kg"
        self.write_inputs()
        result = subprocess.run([sys.executable, str(Path(cli.__file__)), "--case-dir", str(self.case),
                                 "--output-root", str(self.output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unsupported unit", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(self.output.exists())

    def test_corpus_selection_cannot_redirect_to_another_contract_id(self):
        self.contract["id"] = "STD-002"
        self.write_inputs()
        with patch("sys.stderr", new_callable=io.StringIO) as error:
            result = cli.main(["--cases-root", str(self.case.parent), "--case", "STD-001",
                               "--output-root", str(self.output)])
        self.assertEqual(result, 1)
        self.assertIn("contains contract ID STD-002", error.getvalue())
        self.assertFalse(self.output.exists())

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "Independent solver needs NumPy")
    def test_real_cli_cantilever_values_derived_output_and_overwrite(self):
        state = self.requests["states"][0]
        state["quantities"] += [request("up", "L"), request("combined", kind="combination")]
        state["derived"] = [{"id": "envelope", "operation": "max_abs", "operands": ["down", "up"], "unit": "mm"}]
        self.write_inputs()
        command = [sys.executable, str(Path(cli.__file__)), "--case-dir", str(self.case),
                   "--output-root", str(self.output)]
        completed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        destination = self.output / "STD-001" / "independent-reference.json"
        original = destination.read_bytes()
        result = json.loads(original)
        quantities = result["states"][0]["quantities"]
        self.assertAlmostEqual(quantities[0]["value"], -.32, places=12)
        self.assertAlmostEqual(quantities[1]["value"], .32 / 3, places=12)
        self.assertAlmostEqual(quantities[2]["value"], -.32 / 3, places=12)
        self.assertAlmostEqual(result["states"][0]["derived"][0]["value"], -.32, places=12)
        repeated = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(repeated.returncode, 1)
        self.assertIn("Refusing to overwrite", repeated.stderr)
        self.assertEqual(destination.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
