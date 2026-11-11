"""Real OpenSees finite-shear diagnostics with independent closed-form oracles."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import opensees_native as native
import reference_cli as cli
import reference_io as rio
import test_reference_native as fixtures


AREAS = {"beam": {"Asy": .007, "Asz": .004}}


class ExplicitNativeShearInputs(unittest.TestCase):
    def test_opt_in_changes_native_element_and_keeps_default_eb(self):
        structure = fixtures.model(three_d=True)
        default = native.prepare_model(structure, {"D": 1})
        recorder = fixtures.RecordingCommands()
        native.build_domain(recorder, default)
        self.assertEqual(next(a[0] for n, a in recorder.commands if n == "element"), "elasticBeamColumn")
        areas = deepcopy(AREAS)
        plan = native.prepare_model(structure, {"D": 1}, effective_shear_areas=areas)
        areas["beam"]["Asy"] = 99
        recorder = fixtures.RecordingCommands()
        native.build_domain(recorder, plan)
        command = next(a for n, a in recorder.commands if n == "element")
        self.assertEqual(command, ("ElasticTimoshenkoBeam", 1, 1, 2,
            200e6, 80e6, .02, .0001, .0008, .0003, .007, .004, 1))
        self.assertEqual(plan["theory"], "Timoshenko")
        self.assertEqual(plan["effectiveShearAreasM2"], AREAS)

    def test_map_requires_exact_frame_members_and_positive_finite_values_before_runtime(self):
        bad = [{}, {"other": AREAS["beam"]}, {"beam": {"Asy": .007}},
               {"beam": dict(AREAS["beam"], extra=1)}, []]
        bad += [{"beam": dict(AREAS["beam"], Asz=x)} for x in (0, -1, True, "0.1", float("nan"), float("inf"))]
        for areas in bad:
            with self.subTest(areas=areas), patch.object(native, "native_runtime", side_effect=AssertionError("validate before runtime")):
                with self.assertRaises(native.NativeInputError):
                    native.solve(fixtures.model(), {"D": 1}, effective_shear_areas=areas)
        truss = fixtures.model(truss=True)
        with self.assertRaises(native.NativeInputError):
            native.prepare_model(truss, {"D": 1}, effective_shear_areas=AREAS)
        plan = native.prepare_model(truss, {"D": 1}, effective_shear_areas={})
        recorder = fixtures.RecordingCommands()
        native.build_domain(recorder, plan)
        self.assertEqual(next(a[0] for n, a in recorder.commands if n == "element"), "truss")

    def test_varying_distributed_load_is_rejected_even_in_unselected_case(self):
        structure = fixtures.model()
        structure["load_cases"].append({"id": "unused", "loads": [{"id": "varying", "type": "linear",
            "element": "beam", "reference_frame": "global", "wz_start": -2, "wz_end": -4}]})
        with patch.object(native, "native_runtime", side_effect=AssertionError("validate before runtime")):
            with self.assertRaisesRegex(native.NativeInputError, "piecewise-constant"):
                native.solve(structure, {"D": 1}, effective_shear_areas=AREAS)


class AnalyticalNativeShear(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            native.native_runtime()
        except native.NativeDependencyError as exc:
            raise unittest.SkipTest(str(exc)) from exc

    def close(self, actual, expected):
        self.assertAlmostEqual(actual, expected, delta=1e-12+1e-9*abs(expected))

    def test_skew_rolled_signed_six_dof_cantilever_and_end_wrenches(self):
        # Length seven, reference +Z, then a 27-degree roll; basis independent of native.axes_for.
        structure = fixtures.model(length=7, three_d=True)
        structure["nodes"][1].update(x=2, y=3, z=6)
        structure["elements"][0]["rotation_angle"] = 27
        t = math.sqrt(13)
        ex, ey, ez = [2/7, 3/7, 6/7], [-3/t, 2/t, 0], [-12/(7*t), -18/(7*t), t/7]
        c, s = math.cos(math.radians(27)), math.sin(math.radians(27))
        basis = [ex, [c*y+s*z for y, z in zip(ey, ez)], [-s*y+c*z for y, z in zip(ey, ez)]]
        def glob(v):
            return [sum(basis[j][i]*v[j] for j in range(3)) for i in range(3)]
        loads = [5, -7, 11, 13, -17, 19]
        fg = glob(loads[:3])+glob(loads[3:])
        fixtures.loaded(structure, type="nodal", node="b", **dict(zip(native.FORCES, fg)))
        for factor in (1, -1.7):
            with self.subTest(factor=factor):
                read, checks, raw = native.solve(structure, {"D": factor}, [fixtures.member(2.8)],
                                                 effective_shear_areas=AREAS)
                fx, fy, fz, mx, my, mz = [v*factor for v in loads]
                L, E, G, A, Iy, Iz, J = 7, 200e6, 80e6, .02, .0008, .0003, .0001
                local_u = [fx*L/(E*A), (fy*L**3/3+mz*L**2/2)/(E*Iz)+fy*L/(G*.007),
                           (fz*L**3/3-my*L**2/2)/(E*Iy)+fz*L/(G*.004)]
                local_r = [mx*L/(G*J), (my*L-fz*L**2/2)/(E*Iy), (mz*L+fy*L**2/2)/(E*Iz)]
                for dof, want in zip(native.DOFS, glob(local_u)+glob(local_r)):
                    self.close(read(fixtures.node("b"), dof), want)
                local_support = [-fx, -fy, -fz, -mx, -my+L*fz, -mz-L*fy]
                for dof, want in zip(native.FORCES, glob(local_support[:3])+glob(local_support[3:])):
                    self.close(read(fixtures.node("a"), dof), want)
                for dof, want in zip(native.ACTIONS, [fx, -fy, -fz, mx, my-L*fz, mz+L*fy]):
                    self.close(read(fixtures.member(0, "right"), dof), want)
                self.assertEqual(raw["nativeInput"]["theory"], "Timoshenko")
                self.assertEqual(checks["effectiveShearAreasM2"], AREAS)
                self.assertEqual(checks["addedMass"], 0)
                self.assertTrue(checks["equilibriumPassed"])

    def test_uniform_load_and_observation_partition_use_native_uniform_loading(self):
        structure = fixtures.loaded(fixtures.model(), type="distributed", element="beam", wz=-3)
        for stations in ([], [fixtures.member(.7), fixtures.member(3), fixtures.member(5.1)]):
            read, checks, raw = native.solve(structure, {"D": -2}, stations, effective_shear_areas=AREAS)
            q, L, EI, GA = 6, 6, 200e6*.0008, 80e6*.004
            self.close(read(fixtures.node("b"), "uz"), q*L**4/(8*EI)+q*L**2/(2*GA))
            self.close(read(fixtures.node("b"), "ry"), -q*L**3/(6*EI))
            self.close(read(fixtures.node("a"), "fz"), -q*L)
            self.close(read(fixtures.node("a"), "my"), q*L**2/2)
            self.assertEqual(raw["nativeInput"]["pointLoads"], [])
            self.assertEqual(len(raw["nativeInput"]["uniformLoads"]), len(raw["nativeInput"]["segments"]))
            self.assertIn("beamUniform", checks["loadIntegration"])

    def test_piecewise_constant_gaps_have_exact_tip_work_and_true_load_nodes(self):
        structure = fixtures.loaded(fixtures.model(), type="piecewise", element="beam", segments=[
            {"start": 0, "end": 2, "wz": -3}, {"start": 4, "end": 6, "wz": 2}])
        read, _, raw = native.solve(structure, {"D": 1}, [fixtures.member(3)], effective_shear_areas=AREAS)
        # Integrate the independent cantilever point-load influence function over each loaded interval.
        L, EI, GA = 6, 200e6*.0008, 80e6*.004
        expected = sum(q*((L*(b**3-a**3)/6-(b**4-a**4)/24)/EI+(b*b-a*a)/(2*GA))
                       for a, b, q in [(0, 2, -3), (4, 6, 2)])
        self.close(read(fixtures.node("b"), "uz"), expected)
        self.assertEqual([x for x, _ in raw["nativeInput"]["members"]["beam"]["stationNodes"]], [0, 2, 3, 4, 6])
        self.assertEqual(len(raw["nativeInput"]["uniformLoads"]), 2)

    def test_member_point_force_remains_nodal_and_preserves_shear_jump(self):
        structure = fixtures.loaded(fixtures.model(), type="point", element="beam", position=2, fz=-9, my=4)
        read, _, raw = native.solve(structure, {"D": 1}, [fixtures.member(2, "left"), fixtures.member(2, "right")],
                                   effective_shear_areas=AREAS)
        EI, GA, a, L = 200e6*.0008, 80e6*.004, 2, 6
        expected = -9*a*a*(3*L-a)/(6*EI)-9*a/GA-4*a*(2*L-a)/(2*EI)
        self.close(read(fixtures.node("b"), "uz"), expected)
        self.close(read(fixtures.member(2, "left"), "V3"), 9)
        self.close(read(fixtures.member(2, "right"), "V3"), 0)
        self.assertEqual(raw["nativeInput"]["pointLoads"], [])
        self.assertEqual(len(raw["nativeInput"]["nodalLoads"]), 1)

    def test_declared_commercial_generation_has_actual_theory_areas_and_pending_role(self):
        setup = fixtures.NativeReceiptTests()
        setup.setUp()
        self.addCleanup(setup.doCleanups)
        contract_path = setup.case / "contract.json"
        contract = json.loads(contract_path.read_text())
        convention = deepcopy(cli.COMMERCIAL_SHEAR_CONVENTION)
        appendix = convention["publicAttachment"]
        contract.update(plannedEngine="YJK", analysisConvention=convention,
                        turns=[{"id": "t1", "attachments": [appendix]}])
        contract["attachments"].append(appendix)
        contract_path.write_text(json.dumps(contract))
        (setup.case / appendix).write_text("Timoshenko: Asy=Asz=5*A/6, m^2; local shear axes.\n")
        model_bytes = (setup.case / "model-state-1.json").read_bytes()
        path = native.generate(setup.case, setup.output)
        result = json.loads(path.read_text())
        want = -1000*10*(6**3/(3*200e6*.0008)+6/(80e6*(5*.02/6)))
        self.close(result["states"][0]["quantities"][0]["value"], want)
        self.assertEqual(result["analysisConvention"], convention)
        self.assertEqual(result["nativeRole"], "cross-engine-diagnostic")
        self.assertEqual(result["sameEngineTruthStatus"], "pending")
        self.assertEqual(result["nativeIndependentReview"], "pending")
        self.assertEqual((setup.case / "model-state-1.json").read_bytes(), model_bytes)
        for name in ("native-input-receipt.json", "native-solver-receipt.json"):
            receipt = json.loads((path.parent / name).read_text())
            self.assertEqual(receipt["analysisConvention"], convention)
            self.assertEqual(receipt["theory"], "Timoshenko")
        raw = json.loads((path.parent / "native-raw-responses.json").read_text())["runs"][0]["responses"]
        self.assertEqual(raw["nativeInput"]["effectiveShearAreasM2"], {"beam": {"Asy": 5*.02/6, "Asz": 5*.02/6}})
        for record in result["artifacts"]:
            self.assertEqual(record["sha256"], hashlib.sha256((path.parent / record["path"]).read_bytes()).hexdigest())

    def test_missing_public_release_rejected_before_native_execution(self):
        setup = fixtures.NativeReceiptTests()
        setup.setUp()
        self.addCleanup(setup.doCleanups)
        p = setup.case / "contract.json"
        contract = json.loads(p.read_text())
        contract.update(plannedEngine="PKPM", analysisConvention=deepcopy(cli.COMMERCIAL_SHEAR_CONVENTION))
        p.write_text(json.dumps(contract))
        with patch.object(native, "native_runtime", side_effect=AssertionError("must reject before native runtime")):
            with self.assertRaisesRegex(rio.ReferenceInputError, "public"):
                native.generate(setup.case, setup.output)
        self.assertFalse(setup.output.exists())


if __name__ == "__main__":
    unittest.main()
