## Input

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Euler-Bernoulli beam/column and axial-only truss analysis.|
|appendixDecision|The stated roof-right-edge lateral forces act at the specified outer corner (6,10,7.2), shared with the specified torque.|
|documentType|Public engineering input tables|
|combinationTable|[]|

## Input — Stories

|id|elevation|
|---|---|
|s1|0|
|s2|3.6|

Applies to every listed row: height = 3.6; rigid_diaphragm = false.

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

## Input — Lateral load group

|Field|Value|
|---|---|
|X|["roof-X"]|
|Y|["roof-Y"]|

## Input — Nodes

|id|x|y|z|restraints|
|---|---|---|---|---|
|n0-0-0|0|0|0|[true, true, true, true, true, true]|
|n0-1-0|0|5|0|[true, true, true, true, true, true]|
|n0-2-0|0|10|0|[true, true, true, true, true, true]|
|n1-0-0|6|0|0|[true, true, true, true, true, true]|
|n1-1-0|6|5|0|[true, true, true, true, true, true]|
|n1-2-0|6|10|0|[true, true, true, true, true, true]|
|n0-0-1|0|0|3.6|[false, false, false, false, false, false]|
|n0-1-1|0|5|3.6|[false, false, false, false, false, false]|
|n0-2-1|0|10|3.6|[false, false, false, false, false, false]|
|n1-0-1|6|0|3.6|[false, false, false, false, false, false]|
|n1-1-1|6|5|3.6|[false, false, false, false, false, false]|
|n1-2-1|6|10|3.6|[false, false, false, false, false, false]|
|n0-0-2|0|0|7.2|[false, false, false, false, false, false]|
|n0-1-2|0|5|7.2|[false, false, false, false, false, false]|
|n0-2-2|0|10|7.2|[false, false, false, false, false, false]|
|n1-0-2|6|0|7.2|[false, false, false, false, false, false]|
|n1-1-2|6|5|7.2|[false, false, false, false, false, false]|
|n1-2-2|6|10|7.2|[false, false, false, false, false, false]|

## Input — Members

|id|type|nodes|section|rotation_angle|
|---|---|---|---|---|
|c0-0-1|column|["n0-0-0", "n0-0-1"]|C1|90|
|x0-0-1|beam|["n0-0-1", "n1-0-1"]|BX|—|
|y0-0-1|beam|["n0-0-1", "n0-1-1"]|BY|—|
|c0-1-1|column|["n0-1-0", "n0-1-1"]|C1|—|
|x0-1-1|beam|["n0-1-1", "n1-1-1"]|BX|—|
|y0-1-1|beam|["n0-1-1", "n0-2-1"]|BY|—|
|c0-2-1|column|["n0-2-0", "n0-2-1"]|C1|—|
|x0-2-1|beam|["n0-2-1", "n1-2-1"]|BX|—|
|c1-0-1|column|["n1-0-0", "n1-0-1"]|C1|—|
|y1-0-1|beam|["n1-0-1", "n1-1-1"]|BY|—|
|c1-1-1|column|["n1-1-0", "n1-1-1"]|C1|—|
|y1-1-1|beam|["n1-1-1", "n1-2-1"]|BY|—|
|c1-2-1|column|["n1-2-0", "n1-2-1"]|C1|—|
|c0-0-2|column|["n0-0-1", "n0-0-2"]|C1|90|
|x0-0-2|beam|["n0-0-2", "n1-0-2"]|BX|—|
|y0-0-2|beam|["n0-0-2", "n0-1-2"]|BY|—|
|c0-1-2|column|["n0-1-1", "n0-1-2"]|C1|—|
|x0-1-2|beam|["n0-1-2", "n1-1-2"]|BX|—|
|y0-1-2|beam|["n0-1-2", "n0-2-2"]|BY|—|
|c0-2-2|column|["n0-2-1", "n0-2-2"]|C1|—|
|x0-2-2|beam|["n0-2-2", "n1-2-2"]|BX|—|
|c1-0-2|column|["n1-0-1", "n1-0-2"]|C1|—|
|y1-0-2|beam|["n1-0-2", "n1-1-2"]|BY|—|
|c1-1-2|column|["n1-1-1", "n1-1-2"]|C1|—|
|y1-1-2|beam|["n1-1-2", "n1-2-2"]|BY|—|
|c1-2-2|column|["n1-2-1", "n1-2-2"]|C1|—|

Applies to every listed row: material = M1.

## Input — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|C35|concrete|31500|13125.0|0.2|2500|

## Input — Section table

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|BX|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|BY|300.0|500.0|0.15|0.0031249999999999997|0.001125|0.0028173707999999994|
|C1|400.0|500.0|0.2|0.004166666666666667|0.0026666666666666674|0.005474167466666667|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Input — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input — Load case table — D — Loads

|Load ID → element / node|type|wz|fx|fy|mz|
|---|---|---|---|---|---|
|D-x0-0-1 → x0-0-1, D-y0-0-1 → y0-0-1, D-x0-1-1 → x0-1-1, D-y0-1-1 → y0-1-1, D-x0-2-1 → x0-2-1, D-y1-0-1 → y1-0-1, D-y1-1-1 → y1-1-1, D-x0-0-2 → x0-0-2, D-y0-0-2 → y0-0-2, D-x0-1-2 → x0-1-2, D-y0-1-2 → y0-1-2, D-x0-2-2 → x0-2-2, D-y1-0-2 → y1-0-2, D-y1-1-2 → y1-1-2|distributed|-8|—|—|—|
|roof-X → n1-2-2|nodal|—|15|—|—|
|roof-Y → n1-2-2|nodal|—|—|10|—|
|roof-torque → n1-2-2|nodal|—|—|—|8|

Applies to every listed row: reference_frame = global.

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
|dimension|3d|
|plane|null|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input — Member axis data — Element reference vectors

|Field|Value|
|---|---|
|c0-0-1|[1, 0, 0]|
|x0-0-1|[0, 0, 1]|
|y0-0-1|[0, 0, 1]|
|c0-1-1|[1, 0, 0]|
|x0-1-1|[0, 0, 1]|
|y0-1-1|[0, 0, 1]|
|c0-2-1|[1, 0, 0]|
|x0-2-1|[0, 0, 1]|
|c1-0-1|[1, 0, 0]|
|y1-0-1|[0, 0, 1]|
|c1-1-1|[1, 0, 0]|
|y1-1-1|[0, 0, 1]|
|c1-2-1|[1, 0, 0]|
|c0-0-2|[1, 0, 0]|
|x0-0-2|[0, 0, 1]|
|y0-0-2|[0, 0, 1]|
|c0-1-2|[1, 0, 0]|
|x0-1-2|[0, 0, 1]|
|y0-1-2|[0, 0, 1]|
|c0-2-2|[1, 0, 0]|
|x0-2-2|[0, 0, 1]|
|c1-0-2|[1, 0, 0]|
|y1-0-2|[0, 0, 1]|
|c1-1-2|[1, 0, 0]|
|y1-1-2|[0, 0, 1]|
|c1-2-2|[1, 0, 0]|
