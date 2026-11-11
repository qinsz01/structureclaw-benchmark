## Input t1

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Euler-Bernoulli beam/column and axial-only truss analysis.|
|documentType|Public engineering input tables|
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
|n1-0|5.4|0|[true, true, true, true, true, true]|
|n2-0|11.4|0|[true, true, true, true, true, true]|
|n0-1|0|3.6|[false, true, false, true, false, true]|
|n1-1|5.4|3.6|[false, true, false, true, false, true]|
|n2-1|11.4|3.6|[false, true, false, true, false, true]|
|n0-2|0|7.2|[false, true, false, true, false, true]|
|n1-2|5.4|7.2|[false, true, false, true, false, true]|
|n2-2|11.4|7.2|[false, true, false, true, false, true]|

Applies to every listed row: y = 0.

## Input t1 — Members

|id|type|nodes|section|
|---|---|---|---|
|c0-1|column|["n0-0", "n0-1"]|C1|
|c1-1|column|["n1-0", "n1-1"]|C2|
|c2-1|column|["n2-0", "n2-1"]|C1|
|b0-1|beam|["n0-1", "n1-1"]|B1|
|b1-1|beam|["n1-1", "n2-1"]|B1|
|c0-2|column|["n0-1", "n0-2"]|C1|
|c1-2|column|["n1-1", "n1-2"]|C2|
|c2-2|column|["n2-1", "n2-2"]|C1|
|b0-2|beam|["n0-2", "n1-2"]|B1|
|b1-2|beam|["n1-2", "n2-2"]|B1|

Applies to every listed row: material = M1.

## Input t1 — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input t1 — Section table

|id|type|shape · kind|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|---|
|B1|rectangular|rectangular|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|B2|rectangular|rectangular|300.0|700.0|0.21|0.008574999999999998|0.0015749999999999998|0.004603782069970844|
|C1|rectangular|rectangular|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|
|A1|rectangular|rectangular|100.0|100.0|0.010000000000000002|8.333333333333335e-06|8.333333333333335e-06|1.4083333333333338e-05|
|C2|general|—|—|—|0.25|0.009375|0.009375|0.008802083333333334|

Applies to every listed row: name = id.

## Input t1 — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load case table — D — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-1 → b0-1, D-2 → b1-1, D-3 → b0-2, D-4 → b1-2|global|distributed|-10|

## Input t1 — Load case table — L

|Field|Value|
|---|---|
|id|L|
|type|live|

## Input t1 — Load case table — L — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|L-1 → b0-1, L-2 → b1-1, L-3 → b0-2, L-4 → b1-2|global|distributed|-8|

## Input t1 — Combination table

|id|factors · D|factors · L|
|---|---|---|
|1.2D+1.4L|1.2|1.4|

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
