"""Observed YJK BEAM/COLUMN end diagrams -> canonical resisting-wrench convention.

This module qualifies endpoint conversion only. Internal station abscissae are not
inferred. BRACE and other output families are deliberately not accepted.
"""
import math


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def vector(v, size, label):
    if not isinstance(v, (list, tuple)) or len(v) != size:
        raise ValueError(label+' has invalid shape')
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in v):
        raise ValueError(label+' must contain finite real numbers')
    return list(v)


def unit(v):
    v = vector(v, 3, 'axis')
    length = math.sqrt(dot(v, v))
    if not math.isfinite(length) or length <= 1e-12:
        raise ValueError('degenerate native axis')
    return [x/length for x in v]


def native_axes(first_xyz, last_xyz, direction):
    """FE DIR is native local 2; N connectivity determines native local 1."""
    first_xyz = vector(first_xyz, 3, 'first endpoint')
    last_xyz = vector(last_xyz, 3, 'last endpoint')
    direction = vector(direction, 3, 'native DIR')
    x = unit([b-a for a, b in zip(first_xyz, last_xyz)])
    if abs(dot(x, unit(direction))) > 1e-6:
        raise ValueError('FE DIR is not perpendicular to member; unsupported geometry')
    y = unit([v-dot(direction, x)*w for v, w in zip(direction, x)])
    return [x, y, cross(x, y)]


def sdk_to_ffrc(sdk, native_kind):
    sdk = vector(sdk, 6, 'SDK end diagram')
    if native_kind not in ('BEAM', 'COLUMN'):
        raise ValueError('uncalibrated native output family: '+native_kind)
    # BEAM reverses only its first SDK moment relative to the FFRC M3 diagram.
    return [sdk[4], sdk[3], sdk[2], sdk[5], sdk[1], sdk[0]*(1 if native_kind == 'COLUMN' else -1)]


def sdk_endpoint_actions(sdk, native_kind, native_endpoint, source_endpoint,
                         native_basis, source_basis):
    """Return source [N,V2,V3,T,M2,M3] at one physically matched endpoint.

    Endpoint indices refer to actual connectivity, not array order guesses.
    Offsets/releases must be excluded by the caller's input audit.
    """
    if type(native_endpoint) is not int or type(source_endpoint) is not int or native_endpoint not in (0, 1) or source_endpoint not in (0, 1):
        raise ValueError('only end sections are calibrated')
    for basis in (native_basis, source_basis):
        if not isinstance(basis, (list, tuple)) or len(basis) != 3:
            raise ValueError('invalid basis')
        for row in basis:
            vector(row, 3, 'basis row')
        if any(abs(dot(basis[i], basis[j])-(i == j)) > 1e-6 for i in range(3) for j in range(3)):
            raise ValueError('non-orthonormal basis')
        if dot(cross(basis[0], basis[1]), basis[2]) < 1-1e-6:
            raise ValueError('basis must be right handed')
    native = sdk_to_ffrc(sdk, native_kind)
    dn = [-1, 1, 1, -1, 1, 1]
    ds = [-1, 1, 1, -1, -1, -1]
    wrench = [v*sign*(1 if native_endpoint == 0 else -1) for v, sign in zip(native, dn)]
    rotation = [[dot(s, n) for n in native_basis] for s in source_basis]
    rotated = [dot(row, wrench[offset:offset+3]) for offset in (0, 3) for row in rotation]
    return [v*sign*(1 if source_endpoint == 0 else -1) for v, sign in zip(rotated, ds)]
