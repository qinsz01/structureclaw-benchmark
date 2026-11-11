"""Read-only source-specific corpus review checks; never import author/SUT code.

Run with python3 tests/review-inputs/test_pass1.py. Failures are review findings,
not implementation changes. Successful checks do not constitute case acceptance.
"""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import math
import os
import unittest
import xml.etree.ElementTree as ET

WORKTREE = Path(__file__).resolve().parents[2]
SHARED = Path(os.environ.get("REVIEW_INPUTS_SHARED_ROOT", WORKTREE.parents[1]))
REPORT = WORKTREE / "docs/implementation/reviews/review-inputs"
READ_HASHES = {}


def case_dir(case):
    family, number = case.split("-")
    role = family.lower() + ("-a" if int(number) <= 50 else "-b")
    return SHARED / ".worktrees" / role / "corpora/research-300/cases" / case


def read(path):
    data = path.read_bytes()
    READ_HASHES.setdefault(str(path), hashlib.sha256(data).hexdigest())
    return data.decode("utf-8")


def doc(case, filename="contract.json"):
    return json.loads(read(case_dir(case) / filename))


def model(case, state=1):
    return doc(case, f"model-state-{state}.json")


def input_doc(case):
    """Accept the author's table renaming without weakening numerical checks."""
    data = doc(case, "input-t1.json")
    for public, physical in [("nodeTable", "nodes"), ("memberTable", "elements"),
                             ("materialTable", "materials"), ("loadCaseTable", "load_cases")]:
        if public in data:
            data[physical] = data[public]
    return data


def by_id(rows):
    return {row["id"]: row for row in rows}


def diff(a, b, path=""):
    if type(a) is not type(b):
        return {path: (a, b)}
    if isinstance(a, dict):
        result = {}
        for key in a.keys() | b.keys():
            result.update(diff(a.get(key), b.get(key), path + "/" + key))
        return result
    if isinstance(a, list):
        if len(a) != len(b):
            return {path: (a, b)}
        result = {}
        for i, (x, y) in enumerate(zip(a, b)):
            result.update(diff(x, y, f"{path}/{i}"))
        return result
    return {} if a == b else {path: (a, b)}


def resultant_z(m, selection="D"):
    nodes, elements = by_id(m["nodes"]), by_id(m["elements"])
    total = 0
    for load in by_id(m["load_cases"])[selection]["loads"]:
        if load["type"] == "nodal":
            total += load.get("fz", 0)
        elif load["type"] == "distributed":
            a, b = [nodes[n] for n in elements[load["element"]]["nodes"]]
            length = math.sqrt(sum((a[k] - b[k]) ** 2 for k in "xyz"))
            total += load.get("wz", 0) * (load.get("end", length) - load.get("start", 0))
        else:
            raise AssertionError(f"Unsupported review load type: {load['type']}")
    return total


def svg_text(case, filename):
    root = ET.fromstring(read(case_dir(case) / filename))
    return "\n".join("".join(node.itertext()) for node in root.iter()
                     if node.tag.endswith("text"))


def dxf_entities(case):
    lines = read(case_dir(case) / "input.dxf").splitlines()
    assert len(lines) % 2 == 0, "DXF group/value pairing broken"
    pairs = [(int(lines[i]), lines[i + 1]) for i in range(0, len(lines), 2)]
    assert pairs[-1] == (0, "EOF"), "DXF EOF missing"
    entities, current = [], None
    for code, value in pairs:
        if code == 0:
            if current is not None:
                entities.append(current)
            current = {0: value}
        elif current is not None:
            current[code] = value
    return entities


class ReviewPass1(unittest.TestCase):
    def test_std_source_load_totals_and_separate_selections(self):
        totals = {"STD-001": {"D": -120}, "STD-003": {"D": -97.5},
                  "STD-006": {"D": -144}, "STD-007": {"D": -120},
                  "STD-010": {"D": -64, "L": -24}, "STD-027": {"D": -40},
                  "STD-029": {"D": -60}, "STD-030": {"D": -40},
                  "STD-032": {"LC1": -50}, "STD-035": {"LC1": -24},
                  "STD-036": {"LC1": -30}, "STD-040": {"LC1": -30},
                  "STD-051": {"D": -12 * math.sqrt(83.25), "W": 8 * math.sqrt(83.25)},
                  "STD-053": {"D": -80}, "STD-055": {"D": -720},
                  "STD-059": {"D": -288}, "STD-060": {"D": -228, "L": -182.4},
                  "STD-063": {"D": -120}, "STD-068": {"D": -120},
                  "STD-069": {"D": -864}, "STD-074": {"D": -140},
                  "STD-079": {"D": -600}, "STD-081": {"D": -1800},
                  "STD-082": {"D": -2160}}
        for case, selections in totals.items():
            for selection, expected in selections.items():
                with self.subTest(case=case, selection=selection):
                    self.assertAlmostEqual(resultant_z(model(case), selection), expected, places=7)

    def test_std_truss_distinct_topologies_and_tetrahedron_supports(self):
        for case, count in [("STD-029", (6, 10)), ("STD-030", (14, 25)),
                            ("STD-036", (10, 21)), ("STD-040", (4, 6))]:
            m = model(case)
            self.assertEqual((len(m["nodes"]), len(m["elements"])), count)
            self.assertTrue(all(e["type"] == "truss" for e in m["elements"]))
        m = model("STD-030")
        nodes = by_id(m["nodes"])
        verticals = [e for e in m["elements"] if nodes[e["nodes"][0]]["x"] == nodes[e["nodes"][1]]["x"]]
        self.assertEqual(len(verticals), 7)
        self.assertEqual({n["z"] for n in model("STD-036")["nodes"]}, {0, 2.5})
        nodes = by_id(model("STD-040")["nodes"])
        self.assertEqual([nodes[n]["restraints"][:3] for n in ["A", "B", "C", "D"]],
                         [[True, True, True], [False, True, True], [False, False, True], [False, False, False]])
        self.assertAlmostEqual(nodes["D"]["y"], 2 * math.sqrt(3) / 3)

    def test_std003_observations_and_std007_public_mixed_units(self):
        nodes = by_id(model("STD-003")["nodes"])
        qs = doc("STD-003", "reference-requests.json")["states"][0]["quantities"]
        positions = {nodes[q["location"]["id"]]["x"] for q in qs
                     if q["location"]["kind"] == "node" and q["component"] == "uz"}
        self.assertEqual(positions, {3.25, 6.5})
        c = doc("STD-007")
        public = read(case_dir("STD-007") / "prompt.txt")
        for name in c["attachments"]:
            if Path(name).suffix in [".txt", ".json", ".csv"]:
                public += read(case_dir("STD-007") / name)
        for token in ["8000", "10000", "N/mm"]:
            self.assertIn(token, public)
        qs = doc("STD-007", "reference-requests.json")["states"][0]["quantities"]
        self.assertTrue(all(q["unit"] == "mm" for q in qs if q["component"] in ["ux", "uz"]))

    def test_std059_068_unloaded_ties_and_069_pinned_left_base(self):
        for case, level in [("STD-059", 2.25), ("STD-068", 0)]:
            m = model(case)
            nodes = by_id(m["nodes"])
            ties = [e["id"] for e in m["elements"]
                    if all(nodes[n]["z"] == level for n in e["nodes"])]
            self.assertEqual(len(ties), 1)
            self.assertFalse(any(x.get("element") in ties for c in m["load_cases"] for x in c["loads"]))
            for n in nodes.values():
                if n["z"] == level:
                    self.assertFalse(any(n["restraints"][i] for i in [0, 2, 4]))
        nodes = by_id(model("STD-069")["nodes"])
        self.assertFalse(nodes["n0-0"]["restraints"][4])
        self.assertTrue(nodes["n1-0"]["restraints"][4])

    def test_source_authority_and_complete_checklist(self):
        checklist = json.loads(read(REPORT / "checklist.json"))
        plan = json.loads(read(WORKTREE / "planning/capability-coverage-300.json"))
        self.assertEqual(len(checklist["cases"]), 300)
        self.assertEqual({c["caseID"] for c in checklist["cases"]},
                         {c["id"] for c in plan["cases"]})
        source_cases = by_id(plan["cases"])
        for c in checklist["cases"]:
            source = source_cases[c["caseID"]]
            self.assertEqual(c["sourceRequirements"], source["sourceRequirements"])
            self.assertEqual(sorted(i for ids in c["requirementIdsBySourceField"].values() for i in ids),
                             sorted(r["id"] for r in source["requirements"]))
        for key in ("tasks", "models", "workbook"):
            record = checklist["authority"][key]
            self.assertEqual(hashlib.sha256(Path(record["path"]).read_bytes()).hexdigest(), record["sha256"])

    def test_int001_add_undo_preserves_original_point_and_line_load(self):
        a, b, c = [model("INT-001", i) for i in (1, 2, 3)]
        self.assertEqual(a, c)
        self.assertAlmostEqual(resultant_z(a), -132)
        self.assertAlmostEqual(resultant_z(b), -162)
        changed = diff(a, b)
        self.assertEqual(set(changed), {"/load_cases/0/loads"})
        self.assertEqual(b["load_cases"][0]["loads"][:-1], a["load_cases"][0]["loads"])

    def test_int006_length_and_stiffness_boundary_follow_edit(self):
        for state, coords in [(1, [0, 4, 8]), (2, [0, 5, 10])]:
            m = model("INT-006", state)
            self.assertEqual(sorted(n["x"] for n in m["nodes"]), coords)
            sections = by_id(m["sections"])
            for field in ["Iy", "Iz"]:
                self.assertAlmostEqual(sections["B2"]["properties"][field] / sections["B1"]["properties"][field], 1.5)
            self.assertAlmostEqual(resultant_z(m), -18 * coords[-1])

    def test_int009_last_undo_keeps_prior_force_edit(self):
        self.assertEqual(model("INT-009", 2), model("INT-009", 4))
        m = model("INT-009", 4)
        nodes = by_id(m["nodes"])
        forces = {nodes[x["node"]]["x"]: x["fz"] for x in m["load_cases"][0]["loads"]}
        self.assertEqual(forces, {2: -35, 7: -45})

    def test_int052_only_middle_section_changes(self):
        changes = diff(model("INT-052", 1), model("INT-052", 2))
        self.assertEqual(list(changes.values()), [("B2", "B4")])
        self.assertTrue(next(iter(changes)).endswith("/section"))

    def test_int056_clarification_then_vertical_only_change(self):
        turns = doc("INT-056")["turns"]
        self.assertEqual([t["expectation"] for t in turns], ["analyze", "clarify", "analyze"])
        self.assertIsNone(turns[1]["state"])
        changes = diff(model("INT-056", 1), model("INT-056", 2))
        self.assertEqual(list(changes.values()), [(-98, -117.6)])
        self.assertTrue(next(iter(changes)).endswith("/fz"))

    def test_int069_both_moduli_hidden_then_completed(self):
        initial = input_doc("INT-069")
        for material in initial["materials"]:
            self.assertIsNone(material["E"])
            self.assertIsNone(material["G"])
            self.assertNotIn("C30", material["name"])
        material = model("INT-069")["materials"][0]
        self.assertEqual((material["E"], material["G"], material["nu"]), (30000, 12500, .2))
        self.assertEqual([t["attachments"] for t in doc("INT-069")["turns"]],
                         [["input-t1.json"], ["material-t2.json"]])

    def test_int072_missing_span_not_exposed_as_node_table(self):
        initial = input_doc("INT-072")
        self.assertNotIn("nodes", initial)
        self.assertNotIn("elements", initial)
        self.assertIsNone(initial["geometry"]["totalBays"])
        self.assertIsNone(initial["geometry"]["subsequentBayLengthsM"])
        self.assertEqual(initial["geometry"]["firstBayLengthM"], 5)

    def test_int074_left_column_axis_edit_and_undo(self):
        a, b, c = [model("INT-074", i) for i in (1, 2, 3)]
        self.assertEqual(a, c)
        changes = diff(a, b)
        self.assertEqual(len(changes), 2)
        self.assertTrue(all(k.endswith("/rotation_angle") and v == (0, 90) for k, v in changes.items()))
        nodes = by_id(b["nodes"])
        for e in b["elements"]:
            if e.get("rotation_angle") == 90:
                self.assertEqual(e["type"], "column")
                self.assertTrue(all(nodes[n]["x"] == 0 for n in e["nodes"]))

    def test_int076_missing_width_not_disclosed_as_derived_line_load(self):
        initial = input_doc("INT-076")
        self.assertIsNone(initial["tributaryWidthM"]["right"])
        loads = initial["load_cases"][0]["loads"]
        self.assertEqual([x["wz"] for x in loads], [-40, -40, None, None])

    def test_int078_only_negative_wind_scales(self):
        a, b = model("INT-078", 1), model("INT-078", 2)
        changes = diff(a, b)
        self.assertEqual(len(changes), 3)
        for path, (old, new) in changes.items():
            self.assertTrue(path.startswith("/load_cases/2/loads/") and path.endswith("/fx"))
            self.assertLess(new, 0)
            self.assertAlmostEqual(new, 1.2 * old)

    def test_int079_missing_y_span_and_derived_loads_hidden(self):
        initial = input_doc("INT-079")
        self.assertEqual({n["y"] for n in initial["nodes"]}, {0, None})
        self.assertTrue(all(x["wz"] is None for x in initial["load_cases"][0]["loads"]))
        m = model("INT-079")
        nodes = by_id(m["nodes"])
        self.assertEqual(nodes["n0-0-0"]["restraints"], [True] * 3 + [False] * 3)
        self.assertAlmostEqual(resultant_z(m), -600)

    def test_int080_missing_floor_pressure_and_derived_loads_hidden(self):
        initial = input_doc("INT-080")
        loads = initial["load_cases"][0]["loads"]
        self.assertEqual([x["wz"] for x in loads], [-20] * 4 + [None] * 4)
        self.assertIsNone(initial["floorPressure"][1]["pressure"])

    def test_int082_only_upper_floor_pressure_changes(self):
        changes = diff(model("INT-082", 1), model("INT-082", 2))
        self.assertEqual(len(changes), 6)
        self.assertEqual(sorted(changes.values()), sorted([(-20., -22.5)] * 4 + [(-40., -45.)] * 2))
        self.assertTrue(all(p.endswith("/wz") for p in changes))

    def test_int088_undo_preserves_x_increase(self):
        a, b, c, d = [model("INT-088", i) for i in (1, 2, 3, 4)]
        self.assertEqual(b, d)
        xchanges = diff(a, b)
        ychanges = diff(b, c)
        self.assertTrue(xchanges and ychanges)
        for path, (old, new) in xchanges.items():
            self.assertTrue(path.endswith("/fx"))
            self.assertAlmostEqual(new, old * 1.2)
        for path, (old, new) in ychanges.items():
            self.assertTrue(path.endswith("/fy"))
            self.assertEqual(new, -old)

    def test_int090_one_column_unrotates_then_only_y_force_changes(self):
        a, b, c = [model("INT-090", i) for i in (1, 2, 3)]
        changes = diff(a, b)
        self.assertEqual(list(changes.values()), [(90, 0)])
        self.assertTrue(next(iter(changes)).endswith("/rotation_angle"))
        changes = diff(b, c)
        self.assertEqual(list(changes.values()), [(10, 11)])
        self.assertTrue(next(iter(changes)).endswith("/fy"))

    def test_int097_query_reuses_state_and_covers_both_units(self):
        c = doc("INT-097")
        self.assertEqual(len(c["modelStates"]), 1)
        self.assertEqual([(t["state"], t["expectation"]) for t in c["turns"]], [(1, "analyze"), (1, "query")])
        qs = doc("INT-097", "reference-requests.json")["states"][0]["quantities"]
        self.assertTrue({("ux", "m"), ("uz", "m"), ("ux", "mm"), ("uz", "mm")} <= {(q["component"], q["unit"]) for q in qs})

    def test_mm021_initial_conflict_and_connected_point_load(self):
        text = svg_text("MM-021", "input-initial.svg")
        self.assertIn("b3: n2 -> n3 / M1 / B2", text)
        self.assertIn("fz=-22", text)
        self.assertIn("b3: M1 / B1", read(case_dir("MM-021") / "properties.txt"))
        m = model("MM-021")
        nodes = by_id(m["nodes"])
        point = next(x for x in m["load_cases"][0]["loads"] if x["type"] == "nodal")
        self.assertEqual((nodes[point["node"]]["x"], point["fz"]), (3, -22))
        self.assertEqual(sum(point["node"] in e["nodes"] for e in m["elements"]), 2)

    def test_mm032_initial_omits_roof_elevations(self):
        text = svg_text("MM-032", "input-initial.svg")
        for label in ("U1 [height ?]", "U2 [height ?]", "U3 [height ?]", "U4 [height ?]"):
            self.assertIn(label, text)
        for leaked in ("Z=2.5", "Z=1.25", "Z=1.666", "5/3", "5/6"):
            self.assertNotIn(leaked, text)
        self.assertEqual(doc("MM-032")["turns"][0]["state"], None)

    def test_mm041_geometry_topology_loads_and_outputs(self):
        m = model("MM-041")
        n = by_id(m["nodes"])
        self.assertEqual((len(n), len(m["elements"])), (6, 13))
        self.assertEqual([n["U"][k] for k in "xyz"], [4, 2, 3])
        self.assertEqual([n["L"][k] for k in "xyz"], [3, 3, -2])
        self.assertEqual(by_id(m["elements"])["apex_link"]["nodes"], ["L", "U"])
        self.assertAlmostEqual(resultant_z(m), -50)
        qs = doc("MM-041", "reference-requests.json")["states"][0]["quantities"]
        self.assertEqual({(q["location"]["id"], q["component"]) for q in qs},
                         {(node, comp) for node in ["U", "L"] for comp in ["ux", "uy", "uz"]} | {("apex_link", "N")})

    def test_mm042_four_levels_and_designated_top_loads(self):
        m = model("MM-042")
        self.assertEqual({n["z"] for n in m["nodes"]}, {0, 2.5, 5, 7.5})
        self.assertEqual((len(m["nodes"]), len(m["elements"])), (12, 30))
        loads = m["load_cases"][0]["loads"]
        self.assertEqual([(x["node"], x["fx"], x["fy"], x["fz"]) for x in loads],
                         [("L3V1", 12, 0, -10), ("L3V2", 0, 8, -10), ("L3V3", 0, 0, -10)])

    def test_mm043_045_048_actual_slope_length_loads(self):
        expectations = {"MM-043": -12 * math.sqrt(85), "MM-045": -8 * math.sqrt(21**2 + 1.5**2), "MM-048": -12 * math.sqrt(104)}
        for case, expected in expectations.items():
            with self.subTest(case=case):
                self.assertAlmostEqual(resultant_z(model(case)), expected, places=8)

    def test_mm046_raised_middle_base_and_intermediate_load(self):
        m = model("MM-046")
        n = by_id(m["nodes"])
        self.assertEqual((n["B1"]["z"], n["P"]["z"], n["E1"]["z"]), (3, 6, 9))
        self.assertEqual(m["load_cases"][0]["loads"][-1]["node"], "P")
        self.assertAlmostEqual(resultant_z(m), -265)

    def test_mm047_cantilevers_are_disconnected_across_gap(self):
        m = model("MM-047")
        self.assertFalse(any(set(e["nodes"]) == {"TL", "TR"} for e in m["elements"]))
        self.assertAlmostEqual(resultant_z(m), -180)
        for tip in ["TL", "TR"]:
            self.assertEqual(sum(tip in e["nodes"] for e in m["elements"]), 1)

    def test_mm050_three_bay_levels_and_loads(self):
        m = model("MM-050")
        n = by_id(m["nodes"])
        self.assertEqual([(n[x]["x"], n[x]["z"]) for x in ["M0", "M1", "M2"]], [(6, 6), (21, 8), (35, 7)])
        self.assertAlmostEqual(resultant_z(m), -246)

    def test_ri001_all_declared_decimal_elevation_files_exist(self):
        missing = []
        for i in range(79, 89):
            case = f"MM-{i:03}"
            for attachment in doc(case)["attachments"]:
                if not (case_dir(case) / attachment).is_file():
                    missing.append(f"{case}/{attachment}")
        self.assertEqual(missing, [], "RI-001 declared public attachments are absent")

    def test_ri002_no_complete_topology_table_outside_drawings(self):
        for case in ["MM-051", "MM-053", "MM-079", "MM-081"]:
            with self.subTest(case=case):
                assignments = doc(case, "assignments.json")
                self.assertFalse(all(isinstance(e.get("ends"), list) and len(e["ends"]) == 2 for e in assignments),
                                 "RI-002 complete endpoint graph bypasses source modality")

    def test_ri003_png_only_mm053_loads_are_visibly_labelled(self):
        text = svg_text("MM-053", "drawing-elevation-XZ.svg")
        self.assertTrue(("-8" in text or "8 kN/m" in text) and ("12" in text),
                        "RI-003 source PNG-only loads are absent from drawing labels")
        self.assertNotIn("loads.json", doc("MM-053")["attachments"],
                         "RI-003 PNG-only evidence must not be duplicated in a public load table")

    def test_ri004_architectural_dxf_has_explicit_structural_layer(self):
        for case in ["MM-056", "MM-059", "MM-082", "MM-086"]:
            with self.subTest(case=case):
                layers = {e.get(8, "") for e in dxf_entities(case) if e[0] == "LINE"}
                self.assertTrue(any(layer.startswith(("S-", "STRUCT")) for layer in layers),
                                f"RI-004 no explicit structural line layer: {sorted(layers)}")

    def test_independent_review_checks_reject_control_mutations(self):
        baseline = model("INT-009", 4)
        wrong = deepcopy(baseline)
        wrong["load_cases"][0]["loads"][0]["fz"] = -30
        self.assertNotEqual(baseline, wrong, "Control: undo-all must not pass as undo-last")
        correct = model("MM-043")
        wrong = deepcopy(correct)
        for load in wrong["load_cases"][0]["loads"]:
            load["end"] = 9
        self.assertGreater(abs(resultant_z(correct) - resultant_z(wrong)), 1,
                           "Control: projected-length load must differ from actual-slope load")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReviewPass1)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    changed = [path for path, digest in READ_HASHES.items()
               if not Path(path).is_file() or hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest]
    payload = {
        "command": "python3 tests/review-inputs/test_pass1.py",
        "testsRun": result.testsRun,
        "failures": [{"test": str(test), "traceback": trace} for test, trace in result.failures],
        "errors": [{"test": str(test), "traceback": trace} for test, trace in result.errors],
        "readFileHashes": READ_HASHES,
        "filesChangedDuringRun": changed,
        "acceptanceClaim": "None. These source-specific checks and their failures are a partial input review, not solver or full corpus acceptance.",
    }
    (REPORT / "test-results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() and not changed else 1)
