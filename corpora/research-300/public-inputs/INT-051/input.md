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
|leftBase|0|0|[true, true, true, true, true, true]|
|leftEave|0|6|[false, true, false, true, false, true]|
|ridge|9|7.5|[false, true, false, true, false, true]|
|rightEave|18|6|[false, true, false, true, false, true]|
|rightBase|18|0|[true, true, true, true, true, true]|

Applies to every listed row: y = 0.

## Input t1 — Members

|id|type|nodes|section|
|---|---|---|---|
|leftColumn|column|["leftBase", "leftEave"]|C1|
|rightColumn|column|["rightBase", "rightEave"]|C1|
|leftSlope|beam|["leftEave", "ridge"]|B1|
|rightSlope|beam|["ridge", "rightEave"]|B1|

Applies to every listed row: material = M1.

## Input t1 — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

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

|Load ID → element / node|type|wz|fz|
|---|---|---|---|
|D-1 → leftSlope, D-2 → rightSlope|distributed|-5|—|
|ridge-dead → ridge|nodal|—|-12|

Applies to every listed row: reference_frame = global.

## Input t1 — Load case table — W

|Field|Value|
|---|---|
|id|W|
|type|wind|

## Input t1 — Load case table — W — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|right-uplift → rightSlope|global|distributed|4|

## Input t1 — Combination table

|id|factors · W|
|---|---|
|D|—|
|D+W|1|

Applies to every listed row: factors · D = 1.

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
