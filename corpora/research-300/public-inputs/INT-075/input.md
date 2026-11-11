## Input t1

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Euler-Bernoulli beam/column and axial-only truss analysis.|
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

|id|x|z|restraints|
|---|---|---|---|
|n0-0|0|0|[true, true, true, true, true, true]|
|n1-0|5|0|[true, true, true, true, true, true]|
|n2-0|10|0|[true, true, true, true, true, true]|
|n3-0|15|0|[true, true, true, true, true, true]|
|n0-1|0|3.6|[false, true, false, true, false, true]|
|n1-1|5|3.6|[false, true, false, true, false, true]|
|n2-1|10|3.6|[false, true, false, true, false, true]|
|n3-1|15|3.6|[false, true, false, true, false, true]|
|n0-2|0|7.2|[false, true, false, true, false, true]|
|n1-2|5|7.2|[false, true, false, true, false, true]|
|n2-2|10|7.2|[false, true, false, true, false, true]|
|floor1-middle-bay-mid|7.5|3.6|[false, true, false, true, false, true]|

Applies to every listed row: y = 0.

## Input t1 — Members

|id|type|nodes|section|
|---|---|---|---|
|c0-1|column|["n0-0", "n0-1"]|C1|
|c1-1|column|["n1-0", "n1-1"]|C1|
|c2-1|column|["n2-0", "n2-1"]|C1|
|c3-1|column|["n3-0", "n3-1"]|C1|
|b0-1|beam|["n0-1", "n1-1"]|B1|
|b1-1a|beam|["n1-1", "floor1-middle-bay-mid"]|B1|
|b1-1b|beam|["floor1-middle-bay-mid", "n2-1"]|B1|
|b2-1|beam|["n2-1", "n3-1"]|B1|
|c0-2|column|["n0-1", "n0-2"]|C-upper|
|c1-2|column|["n1-1", "n1-2"]|C-upper|
|c2-2|column|["n2-1", "n2-2"]|C-upper|
|b0-2|beam|["n0-2", "n1-2"]|B-roof|
|b1-2|beam|["n1-2", "n2-2"]|B-roof|

Applies to every listed row: material = M1; rotation_angle = 0.

## Input t1 — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|C30|concrete|30000|12500.0|0.2|2500|

## Input t1 — Section table

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|C1|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|
|C-upper|450.0|450.0|0.2025|0.0034171875000000005|0.0034171875000000005|0.005775046875000001|
|B-roof|300.0|500.0|0.15|0.0031249999999999997|0.001125|0.0028173707999999994|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Input t1 — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load case table — D — Loads

|Load ID → element / node|type|wz|fz|
|---|---|---|---|
|D-udl-b0-1 → b0-1, D-udl-b1-1a → b1-1a, D-udl-b1-1b → b1-1b, D-udl-b2-1 → b2-1, D-udl-b0-2 → b0-2, D-udl-b1-2 → b1-2|distributed|-10|—|
|floor1-middle-bay-point → floor1-middle-bay-mid|nodal|—|-24|

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
