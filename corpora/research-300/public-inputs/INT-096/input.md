## Input

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Euler-Bernoulli beam/column and axial-only truss analysis.|
|sectionAxisExplanation|Columns run from bottom to top: local x=global +Z, local y=global +Y, local z=global -X. Rectangular B is along local y; H is along local z. Upper C2 B=350 mm, H=450 mm; lower C1 B=H=450 mm.|
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

## Input — Nodes

|id|z|restraints|
|---|---|---|
|base|0|[true, true, true, true, true, true]|
|mid|2.1|[false, true, false, true, false, true]|
|top|4.2|[false, true, false, true, false, true]|

Applies to every listed row: x = 0; y = 0.

## Input — Members

|id|nodes|section|
|---|---|---|
|column1|["base", "mid"]|C1|
|column2|["mid", "top"]|C2|

Applies to every listed row: type = column; material = M1.

## Input — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|C35|concrete|31500|13125.0|0.2|2500|

## Input — Section table

|id|shape · B|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|
|C1|450.0|0.2025|0.0034171875000000005|0.0034171875000000005|0.005775046875000001|
|C2|350.0|0.1575|0.0026578125000000005|0.0016078124999999996|0.0033760394828341706|

Applies to every listed row: type = rectangular; shape · H = 450.0; name = id; shape · kind = type.

## Input — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input — Load case table — D — Loads

|Load ID → element / node|reference_frame|type|fx|fz|
|---|---|---|---|---|
|top-load → top|global|nodal|30|-600|

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
