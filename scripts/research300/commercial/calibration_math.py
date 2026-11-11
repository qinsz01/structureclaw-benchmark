"""Closed-form, first-order cantilever controls independent of any solver.

The prismatic member runs from its fixed end x=0 to its loaded end x=length.
All vectors use one right-handed local (x,y,z) system; positive moments and
section rotations obey the right-hand rule.  Iy and Iz are principal bending
inertias about y and z.  J is the Saint-Venant torsion constant, not a polar
moment substituted for it.  There is no distributed loading, self weight,
rigid offset, warping restraint, geometric stiffness or material nonlinearity.

Use kN and m: E,G in kN/m²; A,Asy,Asz in m²; Iy,Iz,J in m⁴; forces in kN;
moments in kN m.  Displacements are m and section rotations are radians.
Reactions are forces/moments exerted by the support ON the member at x=0.

The bending terms follow by integrating curvature with zero translation and
rotation at x=0.  Timoshenko adds the integrated constant shear strains
Fy/(G Asy) and Fz/(G Asz); it does not change section rotations.  Asy and Asz
are effective shear areas in their force directions, including any correction
factor.  They must be supplied explicitly, and have no inferred/default value.
The underlying shear/rotation kinematics are also documented in TU Delft's
"1D Problems", Beam problems:
https://interactivetextbooks.citg.tudelft.nl/computational-modelling/structural_linear/rod.html

These controls identify native engine conventions.  They do not authorize
replacing Euler-Bernoulli benchmark physics with finite-shear responses.
"""

import math
from numbers import Real


def _finite_real(name, value):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    try:
        value = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be a finite real number") from error
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite real number")
    return value


def _positive(name, value):
    value = _finite_real(name, value)
    if value <= 0.:
        raise ValueError(f"{name} must be positive")
    return value


def _check_response(result):
    for field in ("displacement", "reaction"):
        for name, value in result[field].items():
            _finite_real(f"{field}.{name}", value)
    return result


def euler_bernoulli_cantilever(*, length, E, G, A, Iy, Iz, J,
                             Fx, Fy, Fz, Mx, My, Mz):
    """Return explicit inputs, tip displacement and fixed-end reaction.

    Every input is required, including zero load components.  Material and
    section properties must be finite and positive; loads may have either
    sign or be zero.  Unsupported shear areas raise TypeError rather than
    silently changing this function's Euler-Bernoulli theory.
    """
    inputs = dict(length=length, E=E, G=G, A=A, Iy=Iy, Iz=Iz, J=J,
                  Fx=Fx, Fy=Fy, Fz=Fz, Mx=Mx, My=My, Mz=Mz)
    for name, value in inputs.items():
        validator = _positive if name in ("length", "E", "G", "A", "Iy", "Iz", "J") else _finite_real
        inputs[name] = validator(name, value)
    length, E, G, A, Iy, Iz, J = (inputs[name] for name in ("length", "E", "G", "A", "Iy", "Iz", "J"))
    Fx, Fy, Fz, Mx, My, Mz = (inputs[name] for name in ("Fx", "Fy", "Fz", "Mx", "My", "Mz"))
    EA = _positive("E*A", E * A)
    EIy = _positive("E*Iy", E * Iy)
    EIz = _positive("E*Iz", E * Iz)
    GJ = _positive("G*J", G * J)
    try:
        length2 = length ** 2
        length3 = length ** 3
        displacement = dict(
            ux=Fx * length / EA,
            uy=(Fy * length3 / 3. + Mz * length2 / 2.) / EIz,
            uz=(Fz * length3 / 3. - My * length2 / 2.) / EIy,
            rx=Mx * length / GJ,
            ry=(My * length - Fz * length2 / 2.) / EIy,
            rz=(Mz * length + Fy * length2 / 2.) / EIz,
        )
        # R=-F and M_support=-M_tip-(length,0,0) cross F_tip.
        reaction = dict(Fx=-Fx, Fy=-Fy, Fz=-Fz,
                        Mx=-Mx, My=-My + length * Fz, Mz=-Mz - length * Fy)
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError("Cantilever response exceeds floating-point range") from error
    return _check_response(dict(
        theory="Euler-Bernoulli",
        units=dict(length="m", force="kN", moment="kN*m", modulus="kN/m^2",
                   area="m^2", inertia="m^4", rotation="rad"),
        inputs=inputs,
        displacement=displacement,
        reaction=reaction,
    ))


def timoshenko_cantilever(*, length, E, G, A, Iy, Iz, J, Asy, Asz,
                         Fx, Fy, Fz, Mx, My, Mz):
    """Return the finite-shear cantilever response for explicit effective areas.

    Asy multiplies G for shear force Fy; Asz multiplies G for shear force Fz.
    Rotations are cross-section rotations, not slopes of the deflected axis.
    Finite-shear results are kept distinct from Euler-Bernoulli results.
    """
    Asy = _positive("Asy", Asy)
    Asz = _positive("Asz", Asz)
    result = euler_bernoulli_cantilever(length=length, E=E, G=G, A=A, Iy=Iy, Iz=Iz, J=J,
                                      Fx=Fx, Fy=Fy, Fz=Fz, Mx=Mx, My=My, Mz=Mz)
    inputs = result["inputs"]
    GAy = _positive("G*Asy", inputs["G"] * Asy)
    GAz = _positive("G*Asz", inputs["G"] * Asz)
    result["displacement"]["uy"] += inputs["Fy"] * inputs["length"] / GAy
    result["displacement"]["uz"] += inputs["Fz"] * inputs["length"] / GAz
    result["theory"] = "Timoshenko"
    inputs.update(Asy=Asy, Asz=Asz)
    return _check_response(result)
