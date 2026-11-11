"""Reproducible author checks for MM-089..098; writes no reference artifacts.

Run with Python 3 and NumPy from any working directory. The independent existing
Euler-Bernoulli stiffness checker is used only as a numerical author cross-check,
including for the PKPM/YJK cases. This does not validate native engine execution
or establish same-engine benchmark truth.
"""
from importlib.util import module_from_spec, spec_from_file_location
from math import isclose, isfinite
from pathlib import Path

from mm_b_89_98 import build_specs


ROOT = Path(__file__).resolve().parents[2]


def _assert_close(actual, expected, description):
    assert isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-9), (
        description, actual, expected)


def run_checks():
    source = spec_from_file_location("mm_b_independent_stiffness",
                                     ROOT / "scripts/independent-frame-reference.py")
    oracle = module_from_spec(source)
    source.loader.exec_module(oracle)
    specs = build_specs()  # Includes the source-level topology/load/axis checks.
    solved = {}
    selection_count = 0
    quantity_count = 0
    largest_imbalance = 0.

    for spec in specs:
        model = spec["model"]
        groups = {}
        for request in spec["requests"]:
            selection = request.get("selection", dict(kind="case", id="D"))
            groups.setdefault((selection["kind"], selection["id"]), []).append(request)

        for (kind, name), requests in groups.items():
            factors = {name: 1} if kind == "case" else next(
                c["factors"] for c in model["load_combinations"] if c["id"] == name)
            quantity, diagnostics = oracle.solve(model, factors,
                                                 [q["location"] for q in requests])
            for request in requests:
                # The public contract uses capitalized support components;
                # this independent checker exposes lowercase node components.
                component = request["component"]
                if request["location"]["kind"] == "node":
                    component = component.lower()
                value = quantity(request["location"], component)
                assert isfinite(value), (spec["id"], request["id"])
            imbalance = max(map(abs, diagnostics["forceMomentBalance"]))
            assert imbalance < 1e-7, (spec["id"], kind, name, diagnostics)
            largest_imbalance = max(largest_imbalance, imbalance)
            selection_count += 1
            quantity_count += len(requests)
            solved[spec["id"], kind, name] = (model, quantity)
            print(f"{spec['id']} {kind} {name}: {len(requests)} finite outputs; "
                  f"force/moment imbalance {imbalance:.3g}")

    # MM-095: two materials in series. Each segment's axial strain is P/(EA).
    _, quantity = solved["MM-095", "case", "D"]
    area = .4*.4
    _assert_close(quantity(dict(kind="node", id="interface"), "uz"),
                  -500*2/(32500*1000*area), "MM-095 interface axial shortening")
    _assert_close(quantity(dict(kind="node", id="top"), "uz"),
                  -500/area/1000*(2/32500+2.5/30000), "MM-095 series compliance")
    _assert_close(quantity(dict(kind="member", id="lower", positionM=0, side="right"), "N"),
                  -500, "MM-095 compressive base axial force")

    # MM-096: a fixed column with a lateral prop halfway to a tip force.
    # Compatibility yields prop reaction -5P/2 and tip u=7Pa^3/(12EI),
    # where a is the prop height and total length is 2a.
    _, quantity = solved["MM-096", "case", "D"]
    rigidity = 30000*1000*.45**4/12
    _assert_close(quantity(dict(kind="node", id="lateral-support"), "fx"),
                  -75, "MM-096 prop compatibility reaction")
    _assert_close(quantity(dict(kind="node", id="top"), "ux"),
                  30*2.1**3*7/(12*rigidity), "MM-096 propped column displacement")

    # MM-097: the pin-guide column bends like a simply supported beam under
    # a midpoint transverse force. The free top axial DOF permits PL/(EA).
    model, quantity = solved["MM-097", "case", "D"]
    section = model["sections"][0]["properties"]
    young = 206000*1000
    _assert_close(quantity(dict(kind="node", id="mid"), "ux"),
                  10*5**3/(48*young*section["Iy"]), "MM-097 midspan bending")
    _assert_close(quantity(dict(kind="node", id="top"), "uz"),
                  -700*5/(young*section["A"]), "MM-097 free-top axial shortening")
    for node in ("base", "top"):
        _assert_close(quantity(dict(kind="node", id=node), "fx"),
                      -5, f"MM-097 horizontal reaction at {node}")

    # MM-098: independently computed external moments about the sole support.
    # Top force contributes (-90,120,0); arm force contributes (-160,0,0).
    # Check the resulting support moments, including the explicit zero Mz.
    model, quantity = solved["MM-098", "case", "D"]
    for component, expected in [("mx", 250), ("my", -120), ("mz", 0)]:
        _assert_close(quantity(dict(kind="node", id="base"), component),
                      expected, f"MM-098 support {component} equilibrium")
    section = model["sections"][0]
    assert section["properties"]["Iy"] != section["properties"]["Iz"]
    assert section["shape"]["Bpositive3"] != section["shape"]["Bnegative3"]

    print("Analytic checks passed: two-material compliance; propped column; "
          "pin-guide bending and compression; eccentric-arm equilibrium.")
    print(f"PASS: {len(specs)} cases, {selection_count} selections, "
          f"{quantity_count} requested quantities; largest imbalance "
          f"{largest_imbalance:.3g}. No reference files written; "
          "native validation remains pending.")


if __name__ == "__main__":
    run_checks()
