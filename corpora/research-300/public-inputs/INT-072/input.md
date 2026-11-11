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

## Input t1 — Geometry

|Field|Value|
|---|---|
|storeyHeightsM|[3.3, 4.0, 3.1]|
|firstBayLengthM|5|
|totalBays|null|
|subsequentBayLengthsM|null|
|connectivity|null|
|supports|All ground-level columns fixed in ux,uz,ry.|

## Input t1 — Member assignment rules

|Field|Value|
|---|---|
|columns|C1, material M1|
|beams|B1, material M1|
|jointType|rigid|
|initialRollDegrees|0|

## Input t1 — Load rules

|Field|Value|
|---|---|
|D|Every beam: downward 8 kN/m.|
|L|No live load on the first (leftmost) bay. Load group R has downward 6 kN/m on every storey; its span membership and connectivity remain to be supplied with the missing bay geometry.|

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

## Input t1 — Combination table

|id|factors · D|factors · L|
|---|---|---|
|D+L|1|1|

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
