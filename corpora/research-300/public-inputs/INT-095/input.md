## Input

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Euler-Bernoulli beam/column and axial-only truss analysis.|
|documentType|Public engineering input tables|
|combinationTable|[]|
|memberAxisData|{}|

## Input — Units

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

## Input — Axis definitions

|Field|Value|
|---|---|
|globalAxes|Right-handed XYZ; Z upward.|
|planarAxes|XZ plane: local x = i to j, local y = global +Y, local z = x cross y.|
|spatialAxes|local x = i to j; y = normalize(reference cross x); z = x cross y; reference vectors are explicit per member.|
|sectionRoll|y_new=cos(theta)*y+sin(theta)*z; z_new=-sin(theta)*y+cos(theta)*z; theta in degrees.|
|reactionNaming|Rz in the task means vertical support force Fz, not nodal rotation rz.|

## Input — Reported height

|Field|Value|
|---|---|
|value|0|
|unit|m|
|status|requires correction|

## Input — Nodes

|id|z|restraints|
|---|---|---|
|base|0|[true, true, true, true, true, true]|
|mid|H/2|[false, true, false, true, false, true]|
|top|H|[false, true, false, true, false, true]|

Applies to every listed row: x = 0; y = 0.

## Input — Members

|id|nodes|
|---|---|
|column1|["base", "mid"]|
|column2|["mid", "top"]|

Applies to every listed row: type = column; material = M1; section = C1.

## Input — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|C35|concrete|31500|13125.0|0.2|2500|

## Input — Section table

|id|type|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|
|C1|rectangular|400.0|400.0|0.16000000000000003|0.002133333333333334|0.002133333333333334|0.0036053333333333345|

Applies to every listed row: name = id; shape · kind = type.

## Input — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input — Load case table — D — Loads

|Load ID → element / node|fz|
|---|---|
|top-compression → top|-500|
|mid-compression → mid|-100|

Applies to every listed row: reference_frame = global; type = nodal.

## Input — Analysis settings

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Input — Coordinate contract

|Field|Value|
|---|---|
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|
