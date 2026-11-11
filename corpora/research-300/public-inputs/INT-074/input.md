## Input t1

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Euler-Bernoulli beam/column and axial-only truss analysis.|
|sectionRotationDefinition|Keep each section A,Iy,Iz,J and displayed B,H unchanged. Rotate the local basis using sectionRoll and rotation_angle. At zero roll in-plane bending uses Iy; at +90 degrees it uses Iz. Left columns initially use the weaker in-plane inertia; right columns initially use the stronger inertia.|
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
|n1-0|7|0|[true, true, true, true, true, true]|
|n0-1|0|3.6|[false, true, false, true, false, true]|
|n1-1|7|3.6|[false, true, false, true, false, true]|
|n0-2|0|7.2|[false, true, false, true, false, true]|
|n1-2|7|7.2|[false, true, false, true, false, true]|

Applies to every listed row: y = 0.

## Input t1 — Members

|id|type|nodes|section|
|---|---|---|---|
|c0-1|column|["n0-0", "n0-1"]|C-left|
|c1-1|column|["n1-0", "n1-1"]|C-right|
|b0-1|beam|["n0-1", "n1-1"]|B1|
|c0-2|column|["n0-1", "n0-2"]|C-left|
|c1-2|column|["n1-1", "n1-2"]|C-right|
|b0-2|beam|["n0-2", "n1-2"]|B1|

Applies to every listed row: material = M1; rotation_angle = 0.

## Input t1 — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|C30|concrete|30000|12500.0|0.2|2500|

## Input t1 — Section table

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|C-left|500.0|350.0|0.175|0.0017864583333333328|0.003645833333333333|0.0040575733442708315|
|C-right|350.0|500.0|0.175|0.003645833333333333|0.0017864583333333328|0.0040575733442708315|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Input t1 — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load case table — D — Loads

|Load ID → element / node|type|wz|fx|my|
|---|---|---|---|---|
|D-udl-b0-1 → b0-1, D-udl-b0-2 → b0-2|distributed|-10|—|—|
|roof-right-force-and-moment → n1-2|nodal|—|20|12|

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
