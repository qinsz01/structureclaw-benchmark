"""Observed PKPM 2027 principal-axis force slots, independently calibrated."""
import math

def source_actions(kind, slots):
    if len(slots) != 6 or any((not math.isfinite(v) or v == -99999 for v in slots)):
        raise ValueError('Missing native force component')
    if kind == 'beam':
        return [slots[0], -slots[1], -slots[2], slots[3], slots[4], slots[5]]
    if kind == 'column':
        return [slots[0], slots[2], -slots[1], slots[3], -slots[5], slots[4]]
    raise ValueError('Uncalibrated member kind')

def end_wrench(kind, basis, end, slots):
    if end not in (0, 1):
        raise ValueError('Only member ends calibrated')
    a = source_actions(kind, slots)
    sign = [-1, 1, 1, -1, -1, -1]
    s = 1 if end == 0 else -1
    a = [x * y * s for (x, y) in zip(a, sign)]
    return [sum((basis[j][i] * a[j + off] for j in range(3))) for off in (0, 3) for i in range(3)]
