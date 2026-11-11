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

## Input t1 — Height statements

|Field|Value|
|---|---|
|storyHeightsM|[3.6, 4.2]|
|roofElevationHeaderM|4.2|
|precedence|null|

## Input t1 — Nodes

|id|x|z|restraints|
|---|---|---|---|
|n0-0|0|0|[true, true, true, true, true, true]|
|n1-0|4.5|0|[true, true, true, true, true, true]|
|n2-0|12|0|[true, true, true, true, true, true]|
|n0-1|0|3.6|[false, true, false, true, false, true]|
|n1-1|4.5|3.6|[false, true, false, true, false, true]|
|n2-1|12|3.6|[false, true, false, true, false, true]|
|n0-2|0|null|[false, true, false, true, false, true]|
|n1-2|4.5|null|[false, true, false, true, false, true]|
|n2-2|12|null|[false, true, false, true, false, true]|

Applies to every listed row: y = 0.

## Input t1 — Members

|id|type|nodes|material|section|
|---|---|---|---|---|
|c0-1|column|["n0-0", "n0-1"]|M1|C1|
|c1-1|column|["n1-0", "n1-1"]|M1|C1|
|c2-1|column|["n2-0", "n2-1"]|M1|C1|
|b0-1|beam|["n0-1", "n1-1"]|M2|B1|
|b1-1|beam|["n1-1", "n2-1"]|M2|B1|
|c0-2|column|["n0-1", "n0-2"]|M1|C1|
|c1-2|column|["n1-1", "n1-2"]|M1|C1|
|c2-2|column|["n2-1", "n2-2"]|M1|C1|
|b0-2|beam|["n0-2", "n1-2"]|M1|B1|
|b1-2|beam|["n1-2", "n2-2"]|M1|B1|

## Input t1 — Material table

|id|name|E|G|
|---|---|---|---|
|M1|Elastic steel E200000|200000|76923.07692307692|
|M2|First-story beam steel|210000|80769.23076923077|

Applies to every listed row: type = steel; nu = 0.3; rho = 7850.

## Input t1 — Section table

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|B2|300.0|700.0|0.21|0.008574999999999998|0.0015749999999999998|0.004603782069970844|
|C1|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|
|C2|350.0|500.0|0.175|0.003645833333333333|0.0017864583333333328|0.0040575733442708315|
|A1|100.0|100.0|0.010000000000000002|8.333333333333335e-06|8.333333333333335e-06|1.4083333333333338e-05|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Input t1 — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load case table — D — Loads

|Load ID → element / node|wz|
|---|---|
|D-1 → b0-1, D-2 → b1-1|-8|
|D-3 → b0-2, D-4 → b1-2|-12|

Applies to every listed row: reference_frame = global; type = distributed.

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
