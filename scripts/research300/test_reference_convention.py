"""A declared commercial physics revision must select and bind its diagnostic."""
from copy import deepcopy
import unittest

import reference_cli as cli
import reference_io as rio
import test_reference_cli as fixtures


CONVENTION = {
    "id": "commercial-linear-static-v2",
    "bendingTheory": "Timoshenko",
    "effectiveShearAreas": {"localY": "5*A/6", "localZ": "5*A/6"},
    "publicAttachment": "analysis-conventions-v2.txt",
}


class CommercialConvention(unittest.TestCase):
    setUp = fixtures.ReferenceIOTests.setUp
    write_json = fixtures.ReferenceIOTests.write_json
    write_inputs = fixtures.ReferenceIOTests.write_inputs

    def declared_case(self, engine="YJK"):
        self.contract.update(plannedEngine=engine, analysisConvention=deepcopy(CONVENTION))
        self.contract["attachments"] = [CONVENTION["publicAttachment"]]
        self.contract["turns"] = [{"id": "t1", "attachments": [CONVENTION["publicAttachment"]]}]
        self.write_inputs()
        (self.case / CONVENTION["publicAttachment"]).write_text(
            "Timoshenko bending: Asy = Asz = 5*A/6 in member local y/z, in m².\n")
        return rio.load_case(self.case)

    def test_declared_shear_changes_answer_and_preserves_frozen_request(self):
        self.requests["states"][0]["quantities"] += [fixtures.request("combination", kind="combination")]
        for engine in ("YJK", "PKPM"):
            with self.subTest(engine=engine):
                case = self.declared_case(engine)
                result = cli.generate_reference(case)
                for row, force in zip(result["states"][0]["quantities"], [-3, -1]):
                    wanted = 1000*force*(4**3/(3*200e6*.001)+4/(80e6*(5*.1/6)))
                    self.assertAlmostEqual(row["value"], wanted, delta=1e-12)
                    self.assertEqual(row["tolerance"], {"absolute": 1e-8, "relative": 1e-6})
                self.assertEqual(result["analysisConvention"], CONVENTION)
                self.assertTrue(result["notCommercialScoringTruth"])
                self.assertEqual(result["sameEngineTruthStatus"], "pending")
                self.assertTrue(all(c["theory"] == "Timoshenko" for c in result["checks"]))
                self.assertEqual(result["sourceHash"], case["sourceHash"])

    def test_existing_undeclared_case_keeps_default_physics(self):
        result = cli.generate_reference(rio.load_case(self.case))
        self.assertAlmostEqual(result["states"][0]["quantities"][0]["value"], -.32)
        self.assertEqual(result["checks"][0]["theory"], "Euler-Bernoulli")
        self.assertNotIn("analysisConvention", result)

    def test_revision_is_not_silently_applied_to_opensees(self):
        case = self.declared_case("OpenSees")
        with self.assertRaisesRegex(rio.ReferenceInputError, "commercial"):
            cli.generate_reference(case)

    def test_unknown_incomplete_or_ambiguous_convention_fails_closed(self):
        case = self.declared_case()
        malformed = [False, {}, dict(CONVENTION, id="future"),
                     dict(CONVENTION, effectiveShearAreas={"localY": "A", "localZ": "5*A/6"}),
                     dict(CONVENTION, bendingTheory="Euler-Bernoulli"),
                     dict(CONVENTION, fallback="default")]
        for convention in malformed:
            with self.subTest(convention=convention), self.assertRaises(rio.ReferenceInputError):
                candidate = deepcopy(case)
                candidate["contract"]["analysisConvention"] = convention
                cli.generate_reference(candidate)

    def test_hidden_or_delayed_convention_is_not_an_implicit_public_requirement(self):
        for mutate in (lambda c: c["attachments"].clear(),
                       lambda c: c["turns"][0]["attachments"].clear()):
            case = self.declared_case()
            mutate(case["contract"])
            with self.assertRaisesRegex(rio.ReferenceInputError, "public"):
                cli.generate_reference(case)


if __name__ == "__main__":
    unittest.main()
