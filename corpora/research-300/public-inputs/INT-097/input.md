## Input

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Euler-Bernoulli beam/column and axial-only truss analysis.|
|appendixDecision|Idealized HW300x300: B=300,H=300,tw=10,tf=15 mm, sharp corners without fillets. Explicit A/Iy/Iz/J govern; dimensions and thicknesses complete the omitted appendix. Q355 E=206000 MPa, nu=0.3, G=206000/2.6 MPa, rho=7850 kg/m3.|
|sectionAxisExplanation|Vertical 2D column local x=global +Z, local y=global +Y, local z=global -X; flange width B is local y and section depth H is local z.|
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
|mid|2|[false, true, false, true, false, true]|
|top|5|[false, true, false, true, false, true]|

Applies to every listed row: x = 0; y = 0.

## Input — Members

|id|nodes|
|---|---|
|column1|["base", "mid"]|
|column2|["mid", "top"]|

Applies to every listed row: type = column; material = M1; section = HW300.

## Input — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input — Section table

|id|name|type|shape · B|shape · H|shape · tw|shape · tf|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|---|---|---|
|HW300|HW300x300|i_section|300|300|10|15|0.011699999999999999|0.00019932749999999983|6.752249999999999e-05|7.649999999999999e-07|

Applies to every listed row: shape · kind = type.

## Input — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input — Load case table — D — Loads

|Load ID → element / node|fz|fx|
|---|---|---|
|top-compression → top|-700|—|
|mid-lateral → mid|—|12|

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
