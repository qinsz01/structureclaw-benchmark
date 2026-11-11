## Input t1

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Euler-Bernoulli beam/column and axial-only truss analysis.|
|sectionGroups|Lower columns are ground-to-first-storey only; columns in storeys 2 and 3 remain C1=500x500 mm. B3 is the initial roof beam record. C-new=650x650 mm and B4=350x650 mm are complete alternative records, not initial assignments.|
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
|n1-0|6|0|[true, true, true, true, true, true]|
|n2-0|12|0|[true, true, true, true, true, true]|
|n0-1|0|3.6|[false, true, false, true, false, true]|
|n1-1|6|3.6|[false, true, false, true, false, true]|
|n2-1|12|3.6|[false, true, false, true, false, true]|
|n0-2|0|7.2|[false, true, false, true, false, true]|
|n1-2|6|7.2|[false, true, false, true, false, true]|
|n2-2|12|7.2|[false, true, false, true, false, true]|
|n0-3|0|10.8|[false, true, false, true, false, true]|
|n1-3|6|10.8|[false, true, false, true, false, true]|
|n2-3|12|10.8|[false, true, false, true, false, true]|
|roof-left-mid|3.0|10.8|[false, true, false, true, false, true]|

Applies to every listed row: y = 0.

## Input t1 — Members

|id|type|nodes|section|
|---|---|---|---|
|c0-1|column|["n0-0", "n0-1"]|C-lower|
|c1-1|column|["n1-0", "n1-1"]|C-lower|
|c2-1|column|["n2-0", "n2-1"]|C-lower|
|b0-1|beam|["n0-1", "n1-1"]|B1|
|b1-1|beam|["n1-1", "n2-1"]|B1|
|c0-2|column|["n0-1", "n0-2"]|C1|
|c1-2|column|["n1-1", "n1-2"]|C1|
|c2-2|column|["n2-1", "n2-2"]|C1|
|b0-2|beam|["n0-2", "n1-2"]|B1|
|b1-2|beam|["n1-2", "n2-2"]|B1|
|c0-3|column|["n0-2", "n0-3"]|C1|
|c1-3|column|["n1-2", "n1-3"]|C1|
|c2-3|column|["n2-2", "n2-3"]|C1|
|b0-3a|beam|["n0-3", "roof-left-mid"]|B3|
|b0-3b|beam|["roof-left-mid", "n1-3"]|B3|
|b1-3|beam|["n1-3", "n2-3"]|B3|

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
|C-lower|600.0|600.0|0.36|0.010799999999999997|0.010799999999999997|0.01825199999999999|
|C-new|650.0|650.0|0.42250000000000004|0.014875520833333334|0.014875520833333334|0.02513963020833333|
|B3|300.0|500.0|0.15|0.0031249999999999997|0.001125|0.0028173707999999994|
|B4|350.0|650.0|0.22749999999999998|0.008009895833333334|0.002322395833333333|0.006160347270060862|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Input t1 — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load case table — D — Loads

|Load ID → element / node|type|wz|fz|
|---|---|---|---|
|D-udl-b0-1 → b0-1, D-udl-b1-1 → b1-1, D-udl-b0-2 → b0-2, D-udl-b1-2 → b1-2, D-udl-b0-3a → b0-3a, D-udl-b0-3b → b0-3b, D-udl-b1-3 → b1-3|distributed|-10|—|
|roof-left-point → roof-left-mid|nodal|—|-15|

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
