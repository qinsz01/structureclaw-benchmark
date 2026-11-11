## Input t1

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Euler-Bernoulli beam/column and axial-only truss analysis.|
|storeyHeightsM|[3.3, -3.3, 3.3]|
|elevationRule|Ground level=0. Node z is the sum of storeyHeightsM through node.level; review invalid dimensions before constructing a solvable geometry.|
|loadInterpretation|60 kN/m downward on all three storey beams, once only. The 30 kN downward nodal load is at the middle-storey midpoint and follows that storey elevation.|
|documentType|Public engineering input tables|
|combinationTable|[]|
|memberAxisData|{}|

## Input t1 — Units

|Field|Value|
|---|---|
|coordinates|m|
|member_length|m|
|E|MPa|
|G|MPa|
|rho|kg/m3|
|A|m2|
|Iy|m4|
|Iz|m4|
|J|m4|
|shape|mm|
|force|kN|
|moment|kN.m|
|line_load|kN/m of actual member length|
|rotation_angle|degree|
|displacement|m|

## Input t1 — Axis definitions

|Field|Value|
|---|---|
|globalAxes|Right-handed XYZ; Z upward.|
|planarAxes|XZ plane: local x = i to j, local y = global +Y, local z = x cross y.|
|spatialAxes|local x = i to j; y = normalize(reference cross x); z = x cross y; reference vectors are explicit per member.|
|sectionRoll|y_new=cos(theta)*y+sin(theta)*z; z_new=-sin(theta)*y+cos(theta)*z; theta in degrees.|
|reactionNaming|Rz in the task means vertical support force Fz, not nodal rotation rz.|

## Input t1 — Nodes

|id|x|restraints|level|
|---|---|---|---|
|n0-0|0|[true, true, true, true, true, true]|0|
|n1-0|6|[true, true, true, true, true, true]|0|
|n0-1|0|[false, true, false, true, false, true]|1|
|n1-1|6|[false, true, false, true, false, true]|1|
|n0-2|0|[false, true, false, true, false, true]|2|
|n1-2|6|[false, true, false, true, false, true]|2|
|n0-3|0|[false, true, false, true, false, true]|3|
|n1-3|6|[false, true, false, true, false, true]|3|
|floor2-mid|3.0|[false, true, false, true, false, true]|2|

Applies to every listed row: y = 0.

## Input t1 — Members

|id|type|nodes|section|
|---|---|---|---|
|c0-1|column|["n0-0", "n0-1"]|C1|
|c1-1|column|["n1-0", "n1-1"]|C1|
|b0-1|beam|["n0-1", "n1-1"]|B1|
|c0-2|column|["n0-1", "n0-2"]|C1|
|c1-2|column|["n1-1", "n1-2"]|C1|
|b0-2a|beam|["n0-2", "floor2-mid"]|B1|
|b0-2b|beam|["floor2-mid", "n1-2"]|B1|
|c0-3|column|["n0-2", "n0-3"]|C1|
|c1-3|column|["n1-2", "n1-3"]|C1|
|b0-3|beam|["n0-3", "n1-3"]|B1|

Applies to every listed row: material = M1; rotation_angle = 0.

## Input t1 — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|C35|concrete|31500|13125.0|0.2|2500|

## Input t1 — Section table

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|C1|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Input t1 — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load case table — D — Loads

|Load ID → element / node|type|wz|fz|
|---|---|---|---|
|D-udl-b0-1 → b0-1, D-udl-b0-2a → b0-2a, D-udl-b0-2b → b0-2b, D-udl-b0-3 → b0-3|distributed|-60|—|
|floor2-midpoint-30 → floor2-mid|nodal|—|-30|

Applies to every listed row: reference_frame = global.

## Input t1 — Analysis settings

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Input t1 — Coordinate contract

|Field|Value|
|---|---|
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|
