"""Native construction/receipt regressions and independent analytical benchmarks.

Analytical tests execute real OpenSees when available. A missing or crashing
native runtime is an explicit skip; it is never replaced by the matrix oracle.
Run: python3 -m unittest discover -s scripts/research300 -p test_reference_native.py -v
"""
from copy import deepcopy
import json
import hashlib
import importlib
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import opensees_native as native
except ImportError:
    import opensees_native as native


def model(length=6.0, simple=False, three_d=False, truss=False):
    fixed_a = [True]*6
    fixed_b = [False, True, False, True, False, True]
    if simple:
        fixed_a[4] = False
        fixed_b[2] = True
    if three_d:
        fixed_b = [False]*6
    if truss:
        fixed_b = [False, True, True, True, True, True]
    return {
        "schema_version": "2.2.0", "unit_system": "SI",
        "coordinate_system": {"dimension": "3d" if three_d else "2d",
            "plane": None if three_d else "xz", "semantics": "global-z-up", "version": 1,
            "dof_order": list(native.DOFS)},
        "nodes": [{"id": "a", "x": 0., "y": 0., "z": 0., "restraints": fixed_a},
                  {"id": "b", "x": length, "y": 0., "z": 0., "restraints": fixed_b}],
        "elements": [{"id": "beam", "type": "truss" if truss else "beam",
            "nodes": ["a", "b"], "material": "steel", "section": "section"}],
        "materials": [{"id": "steel", "type": "steel", "E": 200000., "G": 80000., "rho": 7850.}],
        "sections": [{"id": "section", "properties": {"A": .02, "Iy": .0008, "Iz": .0003, "J": .0001}}],
        "load_cases": [{"id": "D", "type": "dead", "loads": []}],
        "load_combinations": [], "analysis_control": {key: False for key in native.CONTROLS},
        "metadata": {"elementReferenceVectors": {"beam": [0., 0., 1.]}} if three_d else {},
    }


def member(x, side="left", identifier="beam"):
    return {"kind": "member", "id": identifier, "positionM": x, "side": side}


def node(identifier):
    return {"kind": "node", "id": identifier}


def loaded(structure, **load):
    structure["load_cases"][0]["loads"].append(dict(id="load", reference_frame="global", **load))
    return structure


class RecordingCommands:
    def __init__(self):
        self.commands = []

    def __getattr__(self, name):
        def record(*args):
            self.commands.append((name, args))
        return record


class NativeConstructionTests(unittest.TestCase):
    def test_partial_linear_native_loads_exactly_integrate_beam_work(self):
        structure = loaded(model(), type="distributed", element="beam", start=1, end=5,
                           wz_start=-2, wz_end=-10)
        plan = native.prepare_model(structure, {"D": 1}, [member(3.2)])
        # q(x) = -2x on [1,5]. Integrals against x**k, k<=3,
        # include every cubic Euler-Bernoulli virtual-displacement mode.
        for k in range(4):
            actual = sum(p["globalForce"][2] * p["xyz"][0]**k for p in plan["pointLoads"])
            exact = -2 * (5**(k+2)-1)/(k+2)
            self.assertAlmostEqual(actual, exact, places=10)
        self.assertEqual([x for x, _ in plan["members"]["beam"]["stationNodes"]], [0, 1, 3.2, 5, 6])

    def test_piecewise_jumps_gaps_and_negative_factor(self):
        structure = loaded(model(), type="piecewise", element="beam", segments=[
            {"start": 0, "end": 2, "wz": -3},
            {"start": 2, "end": 3, "wz_start": -1, "wz_end": -5},
            {"start": 4, "end": 6, "wz": 2}])
        plan = native.prepare_model(structure, {"D": -2}, [member(2)])
        self.assertAlmostEqual(sum(p["globalForce"][2] for p in plan["pointLoads"]), 10)
        self.assertFalse(any(3 < p["xyz"][0] < 4 for p in plan["pointLoads"]))
        self.assertEqual(len(plan["segments"]), 4)

    def test_vertex_load_schema_preserves_triangular_peak(self):
        structure = loaded(model(), type="distributed", element="beam", distribution="piecewise_linear",
                           points=[{"position": 0, "wz": 0}, {"position": 2, "wz": -6}, {"position": 6, "wz": 0}])
        plan = native.prepare_model(structure, {"D": 1})
        self.assertAlmostEqual(sum(p["globalForce"][2] for p in plan["pointLoads"]), -18)
        self.assertAlmostEqual(sum(p["xyz"][0] * p["globalForce"][2] for p in plan["pointLoads"]), -48)

    def test_point_forces_and_moments_use_true_connected_stations(self):
        structure = loaded(model(), type="point", element="beam", position=2, fz=-9, my=4)
        plan = native.prepare_model(structure, {"D": 1}, [member(3)])
        self.assertEqual(len(plan["nodes"]), 4)
        self.assertEqual(len(plan["segments"]), 3)
        point_node = native.nearest_station(plan["members"]["beam"], 2)
        self.assertEqual(plan["nodes"][point_node]["xyz"], [2, 0, 0])
        self.assertEqual(plan["nodalLoads"], [{"node": point_node, "values": [0, 0, -9, 0, 4, 0]}])
        connected = sum(point_node in segment["nodes"] for segment in plan["segments"])
        self.assertEqual(connected, 2)

    def test_subdivision_and_density_do_not_inject_mass(self):
        structure = loaded(model(), type="distributed", element="beam", wz=-2)
        for stations in ([], [member(.7), member(2.2), member(5.3)]):
            first, second = RecordingCommands(), RecordingCommands()
            native.build_domain(first, native.prepare_model(structure, {"D": 1}, stations))
            other = deepcopy(structure)
            other["materials"][0]["rho"] *= 1000
            native.build_domain(second, native.prepare_model(other, {"D": 1}, stations))
            self.assertEqual(first.commands, second.commands)
            self.assertFalse(any(name == "mass" or "-mass" in args for name, args in first.commands))

    def test_explicit_axes_and_rotation_reach_native_transformation(self):
        structure = model(three_d=True)
        structure["elements"][0]["rotation_angle"] = 30
        commands = RecordingCommands()
        plan = native.prepare_model(structure, {"D": 1})
        native.build_domain(commands, plan)
        transform = next(args for name, args in commands.commands if name == "geomTransf")
        self.assertEqual(transform[:2], ("Linear", 1))
        for actual, expected in zip(transform[2:], [0, -.5, math.sqrt(3)/2]):
            self.assertAlmostEqual(actual, expected)
        stiffness_args = next(args for name, args in commands.commands if name == "element")
        self.assertEqual(stiffness_args[5], 200000000.)  # MPa -> kN/m²

    def test_3d_local_load_rotates_to_global_before_native_application(self):
        structure = loaded(model(three_d=True), type="point", element="beam", position=3, fy=-4, mz=7)
        structure["elements"][0]["rotation_angle"] = 90
        structure["load_cases"][0]["loads"][0]["reference_frame"] = "local"
        plan = native.prepare_model(structure, {"D": 1})
        values = plan["nodalLoads"][0]["values"]
        for actual, expected in zip(values, [0, 0, -4, 0, -7, 0]):
            self.assertAlmostEqual(actual, expected)

    def test_element_local_alias_preserves_point_moments_and_distributed_forces(self):
        structure = loaded(model(three_d=True), type="point", element="beam", position=3, fy=-4, mz=7)
        structure["elements"][0]["rotation_angle"] = 90
        structure["load_cases"][0]["loads"][0]["reference_frame"] = "element-local"
        structure["load_cases"][0]["loads"].append({"id": "distributed", "type": "distributed",
            "element": "beam", "reference_frame": "element-local", "wy": -2})
        plan = native.prepare_model(structure, {"D": 1})
        for actual, expected in zip(plan["nodalLoads"][0]["values"], [0, 0, -4, 0, -7, 0]):
            self.assertAlmostEqual(actual, expected)
        self.assertAlmostEqual(sum(p["globalForce"][2] for p in plan["pointLoads"]), -12)
        self.assertAlmostEqual(sum(p["globalForce"][1] for p in plan["pointLoads"]), 0)

    def test_unknown_load_frame_and_local_nodal_load_still_fail_closed(self):
        for frame in ("element_local", "member", "unrecognized"):
            structure = loaded(model(), type="point", element="beam", position=3, fz=-4)
            structure["load_cases"][0]["loads"][0]["reference_frame"] = frame
            with self.subTest(frame=frame), self.assertRaisesRegex(native.NativeInputError, "reference_frame"):
                native.prepare_model(structure, {"D": 1})
        for frame in ("local", "element-local"):
            structure = loaded(model(), type="nodal", node="b", fz=-4)
            structure["load_cases"][0]["loads"][0]["reference_frame"] = frame
            with self.subTest(frame=frame), self.assertRaisesRegex(native.NativeInputError, "Nodal loads need global"):
                native.prepare_model(structure, {"D": 1})

    def test_planar_quarter_turn_section_is_uncoupled_and_supported(self):
        structure = model()
        structure["elements"][0]["rotation_angle"] = 90
        plan = native.prepare_model(structure, {"D": 1})
        axes = plan["members"]["beam"]["axes"]
        for actual, expected in zip(axes[1], [0, 0, 1]):
            self.assertAlmostEqual(actual, expected)
        structure["elements"][0]["rotation_angle"] = 30
        with self.assertRaisesRegex(native.NativeInputError, "couple inactive plane"):
            native.prepare_model(structure, {"D": 1})

    def test_roundoff_endpoint_does_not_make_spurious_segment(self):
        structure = model(length=math.sqrt(5))
        length = structure["nodes"][1]["x"]
        plan = native.prepare_model(structure, {"D": 1}, [member(math.nextafter(length, 0))])
        self.assertEqual(len(plan["segments"]), 1)
        self.assertEqual(plan["members"]["beam"]["stationNodes"][-1], [length, "b"])

    def test_very_close_stations_remain_distinct_and_force_sides_do_not_cross(self):
        plan = native.prepare_model(model(), {"D": 1}, [member(3), member(3+1e-10)])
        self.assertEqual(len(plan["segments"]), 3)
        raw = {"nodes": {}, "elements": {}}
        for segment, shear in zip(plan["segments"], [11., 22., 33.]):
            force = [0.]*12
            force[2], force[8] = shear, -shear
            raw["elements"][str(segment["tag"])] = {"localForce": force}
        read = native.response_reader(plan, raw)
        self.assertEqual(read(member(3+1e-10, "left"), "V3"), 22)
        self.assertEqual(read(member(3+1e-10, "right"), "V3"), 33)

    def test_truss_observation_does_not_create_transverse_mechanism(self):
        plan = native.prepare_model(model(truss=True), {"D": 1}, [member(3)])
        self.assertEqual(len(plan["nodes"]), 2)
        self.assertEqual(len(plan["segments"]), 1)
        raw = {"nodes": {"a": {"displacement": [0]*6, "reaction": [0]*6},
                         "b": {"displacement": [.006, 0, 0, 0, 0, 0], "reaction": [0]*6}},
               "elements": {"1": {"axialForce": 4}}}
        read = native.response_reader(plan, raw)
        self.assertAlmostEqual(read(member(3), "ux"), .003)
        self.assertEqual(read(member(3), "N"), 4)
        self.assertEqual(read(node("b"), "ry"), 0)
        with self.assertRaisesRegex(native.NativeInputError, "rotations"):
            read(member(3), "ry")

    def test_unsupported_physics_rejected_before_native_import(self):
        mutators = [
            lambda m: m["analysis_control"].update(self_weight=True),
            lambda m: m["analysis_control"].update(p_delta=True),
            lambda m: m["elements"][0].update(releases=[1, 1]),
            lambda m: m["elements"][0].update(type="shell"),
            lambda m: m["nodes"][1].update(spring={"uz": 10}),
            lambda m: m["sections"][0]["properties"].update(shearArea=.1),
            lambda m: m["nodes"][1]["restraints"].__setitem__(1, False),
            lambda m: m["materials"][0].update(type="plastic"),
        ]
        for mutate in mutators:
            with self.subTest(mutate=mutate):
                structure = model()
                mutate(structure)
                with patch.object(native, "native_runtime", side_effect=AssertionError("must validate first")):
                    with self.assertRaises(native.NativeInputError):
                        native.solve(structure, {"D": 1})

    def test_unselected_case_is_also_validated(self):
        structure = model()
        structure["load_cases"].append({"id": "L", "loads": [{"id": "temperature", "type": "thermal", "reference_frame": "global"}]})
        with self.assertRaisesRegex(native.NativeInputError, "Unsupported load type"):
            native.prepare_model(structure, {"D": 1})

    def test_rejects_ambiguous_loads_and_out_of_bounds_stations(self):
        loads = [
            {"wz": -1, "wz_start": -2}, {"wz_end": -3}, {"wz_start": -3},
            {"wz": 0, "wz_end": -3}, {"variation": "piecewise"},
            {"variation": "linear", "distribution": "uniform", "wz": -3},
            {"distribution": "cubic", "wz": -3},
            {"start": 3, "end": 2, "wz": -3},
            {"segments": [{"start": 0, "end": 4, "wz": 1}, {"start": 3, "end": 6, "wz": 1}]},
            {"points": [{"position": 0}, {"position": 0}]},
            {"wz": -1, "points": [{"position": 0}, {"position": 6}]},
        ]
        for fields in loads:
            with self.subTest(load=fields), self.assertRaises(native.NativeInputError):
                native.prepare_model(loaded(model(), type="distributed", element="beam", **fields), {"D": 1})
        with self.assertRaises(native.NativeInputError):
            native.prepare_model(model(), {"D": 1}, [member(7)])

    def test_rejects_missing_3d_axes_and_member_loads_on_truss(self):
        structure = model(three_d=True)
        structure["metadata"] = {}
        with self.assertRaisesRegex(native.NativeInputError, "explicit elementReferenceVectors"):
            native.prepare_model(structure, {"D": 1})
        structure = loaded(model(truss=True), type="point", element="beam", position=3, fx=10)
        with self.assertRaisesRegex(native.NativeInputError, "Truss member loads"):
            native.prepare_model(structure, {"D": 1})

    def test_native_import_abort_is_reported_without_a_fallback(self):
        native.native_runtime.cache_clear()
        self.addCleanup(native.native_runtime.cache_clear)
        failed = subprocess.CompletedProcess([], 15, "", "MPI_Init: unable to create a socket")
        with patch.object(native.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(native.NativeDependencyError, "No numerical fallback.*MPI_Init"):
                native.native_runtime()


class NativeReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.case = self.root / "cases" / "STD-001"
        self.case.mkdir(parents=True)
        self.output = self.root / "output"
        contract = {"schemaVersion": 1, "id": "STD-001", "modelId": "native-test",
            "modelStates": ["model-state-1.json"], "attachments": ["public-input.txt"],
            "plannedEngine": "OpenSees", "evaluationProfile": "engineering-v2.3"}
        structure = loaded(model(), type="nodal", node="b", fz=-10)
        requests = {"schemaVersion": 1, "states": [{"state": 1, "model": "model-state-1.json",
            "quantities": [{"id": "tip_D", "selection": {"kind": "case", "id": "D"},
                "location": node("b"), "component": "uz", "unit": "mm"}], "derived": []}]}
        for filename, payload in [("contract.json", contract), ("reference-requests.json", requests), ("model-state-1.json", structure)]:
            (self.case / filename).write_text(json.dumps(payload), encoding="utf-8")
        (self.case / "prompt.txt").write_text("Analyze the cantilever tip displacement.\n", encoding="utf-8")
        (self.case / "public-input.txt").write_text("6 m cantilever, 10 kN downward tip force.\n", encoding="utf-8")

    def test_runtime_failure_creates_no_reference_or_partial_receipts(self):
        with patch.object(native, "native_runtime", side_effect=native.NativeDependencyError("native library missing")):
            with self.assertRaisesRegex(native.NativeDependencyError, "native library missing"):
                native.generate(self.case, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_artifact_is_preserved_before_native_execution(self):
        target = self.output / "STD-001"
        target.mkdir(parents=True)
        existing = target / "native-opensees-reference.json"
        existing.write_bytes(b"untouched evidence\n")
        with patch.object(native, "native_runtime", side_effect=AssertionError("must not execute")):
            with self.assertRaises(FileExistsError):
                native.generate(self.case, self.output)
        self.assertEqual(existing.read_bytes(), b"untouched evidence\n")

    def test_empty_requests_do_not_produce_a_native_receipt(self):
        filename = self.case / "reference-requests.json"
        data = json.loads(filename.read_text())
        data["states"][0]["quantities"] = []
        filename.write_text(json.dumps(data))
        with patch.object(native, "native_runtime", side_effect=AssertionError("no runtime required")):
            with self.assertRaisesRegex(native.NativeInputError, "no numerical requests"):
                native.generate(self.case, self.output)
        self.assertFalse(self.output.exists())

    def test_receipt_writing_hashes_units_and_pending_status_with_transport_stub(self):
        # Test serialization/IO only. This deliberately labelled transport stub
        # makes no claim to have run OpenSees or verified numerical mechanics.
        runtime = (math, {"module": "math", "version": "transport-test-stub-no-native-execution"})
        fake_solve = (lambda location, component: -.001,
                      {"method": "transport-test-stub", "equilibriumPassed": True},
                      {"testFixture": "no-native-execution"})
        with patch.object(native, "native_runtime", return_value=runtime), patch.object(native, "solve", return_value=fake_solve):
            path = native.generate(self.case, self.output)
        result = json.loads(path.read_text())
        self.assertEqual(result["referenceKind"], "native-opensees")
        self.assertEqual(result["states"][0]["quantities"][0]["value"], -1)
        self.assertEqual(result["nativeIndependentReview"], "pending")
        self.assertEqual(result["sameEngineTruthStatus"], "pending")
        self.assertEqual(result["llmEndToEnd"], "not-run")
        self.assertEqual(result["solver"]["runnerSha256"], hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest())
        self.assertEqual(result["inputHashes"]["model-state-1.json"], hashlib.sha256((self.case / "model-state-1.json").read_bytes()).hexdigest())
        manifest = {"schemaVersion": 1, "files": [{"path": name,
            "sha256": hashlib.sha256((self.case / name).read_bytes()).hexdigest()}
            for name in sorted(("contract.json", "prompt.txt", "model-state-1.json", "reference-requests.json",
                                "public-input.txt"), key=lambda name: name.encode("utf-8"))]}
        expected_source_hash = hashlib.sha256(json.dumps(manifest, ensure_ascii=False,
            separators=(",", ":")).encode("utf-8")).hexdigest()
        self.assertEqual(result["sourceManifest"], manifest)
        self.assertEqual(result["sourceHash"], expected_source_hash)
        input_receipt = json.loads((path.parent / "native-input-receipt.json").read_text())
        self.assertEqual(input_receipt["sourceHash"], expected_source_hash)
        self.assertEqual(input_receipt["sourceManifest"], manifest)
        self.assertFalse((path.parent / "reference-provenance.json").exists())
        self.assertIn("Timoshenko", result["warnings"][0])
        self.assertEqual(len(list(path.parent.glob("native-*.json"))), 5)

    def test_standalone_cli_returns_error_and_preserves_existing_evidence(self):
        target = self.output / "STD-001"
        target.mkdir(parents=True)
        (target / "native-opensees-reference.json").write_text("existing", encoding="utf-8")
        run = subprocess.run([sys.executable, str(Path(native.__file__)), "--case-dir", str(self.case),
                              "--output-root", str(self.output)], capture_output=True, text=True, timeout=20)
        self.assertEqual(run.returncode, 2)
        self.assertIn("already exists", run.stderr)
        self.assertEqual((target / "native-opensees-reference.json").read_text(), "existing")

    def test_frozen_native_artifact_manifest_detects_raw_byte_mutation(self):
        runtime = (math, {"module": "math", "version": "transport-test-stub-no-native-execution"})
        fake_solve = (lambda location, component: -.001,
                      {"method": "transport-test-stub", "equilibriumPassed": True},
                      {"testFixture": "no-native-execution"})
        with patch.object(native, "native_runtime", return_value=runtime), patch.object(native, "solve", return_value=fake_solve):
            path = native.generate(self.case, self.output)
        result = json.loads(path.read_text())
        expected = ["native-input-receipt.json", "native-solver-receipt.json",
                    "native-raw-responses.json", "native-checks.json"]
        self.assertEqual([item["path"] for item in result["artifacts"]], expected)
        for item in result["artifacts"]:
            with self.subTest(artifact=item["path"]):
                artifact = path.parent / item["path"]
                raw = artifact.read_bytes()
                self.assertEqual(item["sha256"], hashlib.sha256(raw).hexdigest())
                # Even valid JSON with identical parsed content must differ
                # from the frozen raw-byte digest after a whitespace edit.
                artifact.write_bytes(raw + b"\n")
                self.assertEqual(json.loads(artifact.read_bytes()), json.loads(raw))
                self.assertNotEqual(item["sha256"], hashlib.sha256(artifact.read_bytes()).hexdigest())
        self.assertNotIn(path.name, expected)  # No reference self-hash/cycle.


class AnalyticalNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            native.native_runtime()
        except native.NativeDependencyError as exc:
            lines = str(exc).splitlines()
            detail = next((line for line in lines if "unable to create a socket" in line), lines[-1])
            raise unittest.SkipTest("Real native OpenSees unavailable; no numerical fallback: " + detail) from exc

    def assertEngineeringEqual(self, actual, expected):
        self.assertAlmostEqual(actual, expected, delta=1e-10 + abs(expected)*1e-8)

    def test_cantilever_point_force_displacement_rotation_reactions_and_actions(self):
        structure = loaded(model(), type="nodal", node="b", fz=-10)
        read, checks, raw = native.solve(structure, {"D": 1}, [member(0, "right"), member(3)])
        ei = 200000000 * .0008
        self.assertEngineeringEqual(read(node("b"), "uz"), -10*6**3/(3*ei))
        self.assertEngineeringEqual(read(node("b"), "ry"), 10*6**2/(2*ei))
        self.assertEngineeringEqual(read(node("a"), "Fz"), 10)
        self.assertEngineeringEqual(read(node("a"), "My"), -60)
        self.assertEngineeringEqual(read(member(0, "right"), "M2"), 60)
        self.assertEngineeringEqual(read(member(3), "uz"), -10*3**2*(3*6-3)/(6*ei))
        self.assertTrue(checks["equilibriumPassed"])
        self.assertEqual(raw["analysisReturnCode"], 0)

    def test_planar_quarter_turn_asymmetric_section_uses_rotated_principal_inertia(self):
        # Global vertical bending uses Iy at zero roll and Iz after a quarter
        # turn. Unequal principal inertias catch ignored rotation as well as
        # the former native guard that rejected the valid 90-degree domain.
        for angle, inertia in ((0, .0008), (90, .0003), (-90, .0003), (180, .0008), (270, .0003)):
            with self.subTest(angle=angle):
                structure = loaded(model(), type="nodal", node="b", fz=-10)
                structure["elements"][0]["rotation_angle"] = angle
                read, checks, raw = native.solve(structure, {"D": 1}, [member(3)])
                ei = 200000000 * inertia
                self.assertEngineeringEqual(read(node("b"), "uz"), -10*6**3/(3*ei))
                self.assertEngineeringEqual(read(node("b"), "ry"), 10*6**2/(2*ei))
                self.assertEngineeringEqual(read(member(3), "uz"), -10*3**2*(3*6-3)/(6*ei))
                self.assertEngineeringEqual(read(node("a"), "Fz"), 10)
                self.assertEngineeringEqual(read(node("a"), "My"), -60)
                self.assertTrue(checks["equilibriumPassed"])
                self.assertEqual(raw["analysisReturnCode"], 0)

    def test_quarter_turn_element_local_point_force_and_moment_have_signed_response(self):
        for frame in ("local", "element-local"):
            with self.subTest(frame=frame):
                structure = loaded(model(), type="point", element="beam", position=2, fy=-9, mz=-4)
                structure["elements"][0]["rotation_angle"] = 90
                structure["load_cases"][0]["loads"][0]["reference_frame"] = frame
                read, checks, _ = native.solve(structure, {"D": 1}, [member(2, "left"), member(2, "right")])
                ei = 200000000 * .0003
                # A local -z moment is global +My after +90 degrees roll.
                self.assertEngineeringEqual(read(node("b"), "uz"), -9*2**2*(3*6-2)/(6*ei)-4*2*(2*6-2)/(2*ei))
                self.assertEngineeringEqual(read(node("b"), "ry"), 9*2**2/(2*ei)+4*2/ei)
                self.assertEngineeringEqual(read(node("a"), "Fz"), 9)
                self.assertEngineeringEqual(read(node("a"), "My"), -22)
                self.assertEngineeringEqual(read(member(2, "left"), "V2"), 9)
                self.assertEngineeringEqual(read(member(2, "right"), "V2"), 0)
                self.assertTrue(checks["equilibriumPassed"])

    def test_quarter_turn_element_local_uniform_load_matches_cantilever_formula(self):
        for frame in ("local", "element-local"):
            with self.subTest(frame=frame):
                structure = loaded(model(), type="distributed", element="beam", wy=-3)
                structure["elements"][0]["rotation_angle"] = 90
                structure["load_cases"][0]["loads"][0]["reference_frame"] = frame
                read, checks, _ = native.solve(structure, {"D": 1}, [member(3)])
                ei = 200000000 * .0003
                self.assertEngineeringEqual(read(node("b"), "uz"), -3*6**4/(8*ei))
                self.assertEngineeringEqual(read(node("b"), "ry"), 3*6**3/(6*ei))
                self.assertEngineeringEqual(read(node("a"), "Fz"), 18)
                self.assertEngineeringEqual(read(node("a"), "My"), -54)
                self.assertTrue(checks["equilibriumPassed"])

    def test_simply_supported_uniform_midpoint_is_exact_native_observation(self):
        structure = loaded(model(simple=True), type="distributed", element="beam", wz=-3)
        read, checks, raw = native.solve(structure, {"D": 1}, [member(3)])
        ei = 200000000 * .0008
        self.assertEngineeringEqual(read(member(3), "uz"), -5*3*6**4/(384*ei))
        self.assertEngineeringEqual(read(member(3), "M2"), -3*6**2/8)
        self.assertEngineeringEqual(read(node("a"), "Fz"), 9)
        self.assertEqual(checks["nativeNodes"], 3)
        self.assertEqual(len(raw["nativeInput"]["segments"]), 2)

    def test_triangular_partial_and_piecewise_loads(self):
        triangular = loaded(model(simple=True), type="linear", element="beam", wz_start=0, wz_end=-6)
        read, _, _ = native.solve(triangular, {"D": 1}, [member(3)])
        ei = 200000000 * .0008
        self.assertEngineeringEqual(read(node("a"), "Fz"), 6)
        self.assertEngineeringEqual(read(node("b"), "Fz"), 12)
        self.assertEngineeringEqual(read(member(3), "uz"), -5*6*6**4/(768*ei))
        self.assertEngineeringEqual(read(member(3), "M2"), -6*6**2/16)
        partial = loaded(model(simple=True), type="distributed", element="beam", start=2, end=4, wz=-3)
        read, _, _ = native.solve(partial, {"D": 1}, [member(3)])
        self.assertEngineeringEqual(read(node("a"), "Fz"), 3)
        self.assertEngineeringEqual(read(member(3), "M2"), -7.5)
        piecewise = loaded(model(simple=True), type="piecewise", element="beam", segments=[
            {"start": 0, "end": 3, "wz_start": 0, "wz_end": -3},
            {"start": 3, "end": 6, "wz_start": -3, "wz_end": -6}])
        read, _, _ = native.solve(piecewise, {"D": 1}, [member(3)])
        self.assertEngineeringEqual(read(member(3), "uz"), -5*6*6**4/(768*ei))

    def test_point_load_shear_jump_left_and_right(self):
        structure = loaded(model(simple=True), type="point", element="beam", position=3, fz=-12)
        read, _, _ = native.solve(structure, {"D": 1}, [member(3, "left"), member(3, "right")])
        self.assertEngineeringEqual(read(member(3, "left"), "V3"), 6)
        self.assertEngineeringEqual(read(member(3, "right"), "V3"), -6)
        self.assertEngineeringEqual(read(member(3), "uz"), -12*6**3/(48*200000000*.0008))

    def test_explicit_3d_cantilever_biaxial_and_torsional_response(self):
        structure = loaded(model(three_d=True), type="nodal", node="b", fx=5, fy=7, fz=-11, mx=13)
        read, _, _ = native.solve(structure, {"D": 1}, [member(3)])
        self.assertEngineeringEqual(read(node("b"), "ux"), 5*6/(200000000*.02))
        self.assertEngineeringEqual(read(node("b"), "uy"), 7*6**3/(3*200000000*.0003))
        self.assertEngineeringEqual(read(node("b"), "uz"), -11*6**3/(3*200000000*.0008))
        self.assertEngineeringEqual(read(node("b"), "rx"), 13*6/(80000000*.0001))
        self.assertEngineeringEqual(read(node("a"), "Mx"), -13)
        self.assertEngineeringEqual(read(member(3), "T"), 13)

    def test_truss_axial_force_and_exact_linear_displacement(self):
        structure = loaded(model(truss=True), type="nodal", node="b", fx=10)
        read, checks, _ = native.solve(structure, {"D": 1}, [member(3)])
        self.assertEngineeringEqual(read(node("b"), "ux"), 10*6/(200000000*.02))
        self.assertEngineeringEqual(read(member(3), "ux"), 10*3/(200000000*.02))
        self.assertEngineeringEqual(read(member(3), "N"), 10)
        self.assertEngineeringEqual(read(node("a"), "Fx"), -10)
        self.assertEqual(checks["nativeNodes"], 2)

    def test_no_load_combination_factor_leakage_between_domains(self):
        structure = loaded(model(), type="nodal", node="b", fz=-10)
        first, _, _ = native.solve(structure, {"D": 1})
        reverse, _, _ = native.solve(structure, {"D": -.5})
        again, _, _ = native.solve(structure, {"D": 1})
        self.assertEngineeringEqual(reverse(node("b"), "uz"), -.5*first(node("b"), "uz"))
        self.assertEngineeringEqual(again(node("b"), "uz"), first(node("b"), "uz"))

    def test_native_receipts_include_version_hashes_and_exclusive_result(self):
        setup = NativeReceiptTests(methodName="test_runtime_failure_creates_no_reference_or_partial_receipts")
        setup.setUp()
        self.addCleanup(setup.doCleanups)
        path = native.generate(setup.case, setup.output)
        result = json.loads(path.read_text())
        self.assertEqual(result["referenceKind"], "native-opensees")
        self.assertEqual(result["sameEngineTruthStatus"], "pending")
        self.assertTrue(result["solver"]["version"])
        runtime_module, _ = native.native_runtime()
        implementation = importlib.import_module(runtime_module.version.__module__)
        self.assertEqual(result["solver"]["nativeBinaryModule"], implementation.__name__)
        self.assertEqual(result["solver"]["nativeBinarySha256"],
                         hashlib.sha256(Path(implementation.__file__).read_bytes()).hexdigest())
        self.assertEqual(result["solver"]["nativeModuleSha256"],
                         hashlib.sha256(Path(runtime_module.__file__).read_bytes()).hexdigest())
        self.assertEqual(len(result["inputHashes"]["model-state-1.json"]), 64)
        self.assertEqual(len(result["sourceHash"]), 64)
        self.assertEqual(len(list(path.parent.glob("native-*.json"))), 5)
        self.assertEngineeringEqual(result["states"][0]["quantities"][0]["value"], -1000*10*6**3/(3*200000000*.0008))
        with self.assertRaises(FileExistsError):
            native.generate(setup.case, setup.output)

    def test_native_generated_opposite_sign_near_tie_preserves_first_signed_governor(self):
        setup = NativeReceiptTests(methodName="test_runtime_failure_creates_no_reference_or_partial_receipts")
        setup.setUp()
        self.addCleanup(setup.doCleanups)
        # Real axial truss solves give N=Fx. A 2e-11 kN load difference is
        # deliberately resolvable but inside the unchanged frozen tolerance.
        structure = loaded(model(truss=True), type="nodal", node="b", fx=-19.2)
        structure["load_cases"].append({"id": "L", "type": "live", "loads": [
            {"id": "tension", "type": "nodal", "node": "b",
             "reference_frame": "global", "fx": 19.20000000002}]})
        (setup.case / "model-state-1.json").write_text(json.dumps(structure), encoding="utf-8")
        tolerance = {"absolute": 1e-8, "relative": 1e-6}
        requests = {"schemaVersion": 1, "states": [{"state": 1, "model": "model-state-1.json",
            "quantities": [{"id": identifier, "selection": {"kind": "case", "id": case_id},
                "location": member(3), "component": "N", "unit": "kN"}
                for identifier, case_id in (("compression", "D"), ("tension", "L"))],
            "derived": [
                {"id": "compression_total", "operation": "sum", "operands": ["compression"], "unit": "kN"},
                {"id": "axial_peak", "operation": "max_abs", "operands": ["compression", "tension"],
                 "unit": "kN", "tolerance": tolerance, "tiePolicy": "any"},
                {"id": "nested_peak", "operation": "max_abs", "operands": ["compression_total", "tension"],
                 "unit": "kN", "tolerance": tolerance}]}]}
        (setup.case / "reference-requests.json").write_text(json.dumps(requests), encoding="utf-8")
        path = native.generate(setup.case, setup.output)
        result = json.loads(path.read_text())
        state = result["states"][0]
        compression, tension = state["quantities"]
        self.assertEngineeringEqual(compression["value"], -19.2)
        self.assertEngineeringEqual(tension["value"], 19.20000000002)
        self.assertGreater(abs(tension["value"]), abs(compression["value"]))
        self.assertLess(abs(tension["value"])-abs(compression["value"]), tolerance["absolute"])
        direct, nested = state["derived"][1:]
        for derived, first_operand in ((direct, "compression"), (nested, "compression_total")):
            with self.subTest(derived=derived["id"]):
                self.assertEqual(derived["governingOperand"], first_operand)
                self.assertEqual(derived["coGoverningOperands"], [first_operand, "tension"])
                self.assertEqual(derived["value"], compression["value"])
                self.assertEqual(derived["governingLeafOperands"], ["compression"])
                self.assertEqual(derived["governingSelection"], {"kind": "case", "id": "D"})
                self.assertEqual(derived["governingSelections"], [{"kind": "case", "id": "D"}])
                self.assertEqual(derived["tolerance"], tolerance)
        self.assertEqual(direct["tiePolicy"], "any")
        self.assertEqual(result["nativeIndependentReview"], "pending")
        self.assertEqual(result["sameEngineTruthStatus"], "pending")
        self.assertFalse((path.parent / "reference-provenance.json").exists())


if __name__ == "__main__":
    unittest.main()
