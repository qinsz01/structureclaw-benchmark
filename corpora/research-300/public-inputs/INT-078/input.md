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
|n1-0|6|0|[true, true, true, true, true, true]|
|n0-1|0|3.6|[false, true, false, true, false, true]|
|n1-1|6|3.6|[false, true, false, true, false, true]|
|n0-2|0|7.2|[false, true, false, true, false, true]|
|n1-2|6|7.2|[false, true, false, true, false, true]|
|n0-3|0|10.8|[false, true, false, true, false, true]|
|n1-3|6|10.8|[false, true, false, true, false, true]|

Applies to every listed row: y = 0.

## Input t1 — Members

|id|type|nodes|section|
|---|---|---|---|
|c0-1|column|["n0-0", "n0-1"]|C1|
|c1-1|column|["n1-0", "n1-1"]|C1|
|b0-1|beam|["n0-1", "n1-1"]|B1|
|c0-2|column|["n0-1", "n0-2"]|C1|
|c1-2|column|["n1-1", "n1-2"]|C1|
|b0-2|beam|["n0-2", "n1-2"]|B1|
|c0-3|column|["n0-2", "n0-3"]|C1|
|c1-3|column|["n1-2", "n1-3"]|C1|
|b0-3|beam|["n0-3", "n1-3"]|B1|

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

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Input t1 — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load case table — D — Loads

|Load ID → element / node|wz|start|end|
|---|---|---|---|
|D-udl-b0-1 → b0-1|-12|—|—|
|D-udl-b0-2 → b0-2|-10|—|—|
|D-udl-b0-3 → b0-3|-8|—|—|
|middle-left-half-additional → b0-2|-5|0|3|

Applies to every listed row: reference_frame = global; type = distributed.

## Input t1 — Load case table — W+

|Field|Value|
|---|---|
|id|W+|
|type|wind|

## Input t1 — Load case table — W+ — Loads

|Load ID → element / node|fx|
|---|---|
|Wplus-storey-1 → n1-1|10|
|Wplus-storey-2 → n1-2|15|
|Wplus-storey-3 → n1-3|20|

Applies to every listed row: reference_frame = global; type = nodal.

## Input t1 — Load case table — W-

|Field|Value|
|---|---|
|id|W-|
|type|wind|

## Input t1 — Load case table — W- — Loads

|Load ID → element / node|fx|
|---|---|
|Wminus-storey-1 → n1-1|-10|
|Wminus-storey-2 → n1-2|-15|
|Wminus-storey-3 → n1-3|-20|

Applies to every listed row: reference_frame = global; type = nodal.

## Input t1 — Combination table

|id|factors · W+|factors · W-|
|---|---|---|
|D|—|—|
|D+W+|1|—|
|D+W-|—|1|

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
