## Input t1

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Euler-Bernoulli beam/column and axial-only truss analysis.|
|outputDefinition|For every listed case and combination, report Ux, Uz and Uy at the highest real beam-column joint, selecting largest X then largest Y on that level; report global support reaction My and vertical reaction Rz=Fz at the base with smallest X then smallest Y. Use signed m, kN.m and kN values, identify the node, direction, selection and current turn. Overhang free ends are not beam-column joints.|
|executionEvidence|Retain the actual named-engine input/project, software version, effective settings, successful log and raw result-to-node/member/selection mapping for each changed state. A screenshot or another engine is not execution evidence. Keep original load cases and evaluate listed combinations separately.|
|lateralForceInterpretation|Each right-edge node at x=12 m, y=0 or 5 m receives the listed force: W-X gives +10 kN per node on story 1 and +15 kN per node at the roof; W-Y gives +8 and +12 kN per node respectively. They are node forces, not whole-story totals. D as a case and D as a combination are separate selections.|
|documentType|Public engineering input tables|

## Input t1 — Stories

|id|elevation|
|---|---|
|s1|0|
|s2|3.6|

Applies to every listed row: height = 3.6; rigid_diaphragm = false.

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

|id|x|y|z|restraints|
|---|---|---|---|---|
|n0-0-0|0|0|0|[true, true, true, true, true, true]|
|n0-1-0|0|5|0|[true, true, true, true, true, true]|
|n1-0-0|6|0|0|[true, true, true, true, true, true]|
|n1-1-0|6|5|0|[true, true, true, true, true, true]|
|n2-0-0|12|0|0|[true, true, true, true, true, true]|
|n2-1-0|12|5|0|[true, true, true, true, true, true]|
|n0-0-1|0|0|3.6|[false, false, false, false, false, false]|
|n0-1-1|0|5|3.6|[false, false, false, false, false, false]|
|n1-0-1|6|0|3.6|[false, false, false, false, false, false]|
|n1-1-1|6|5|3.6|[false, false, false, false, false, false]|
|n2-0-1|12|0|3.6|[false, false, false, false, false, false]|
|n2-1-1|12|5|3.6|[false, false, false, false, false, false]|
|n0-0-2|0|0|7.2|[false, false, false, false, false, false]|
|n0-1-2|0|5|7.2|[false, false, false, false, false, false]|
|n1-0-2|6|0|7.2|[false, false, false, false, false, false]|
|n1-1-2|6|5|7.2|[false, false, false, false, false, false]|
|n2-0-2|12|0|7.2|[false, false, false, false, false, false]|
|n2-1-2|12|5|7.2|[false, false, false, false, false, false]|

## Input t1 — Members

|id|type|nodes|section|
|---|---|---|---|
|c0-0-1|column|["n0-0-0", "n0-0-1"]|C1|
|x0-0-1|beam|["n0-0-1", "n1-0-1"]|B1|
|y0-0-1|beam|["n0-0-1", "n0-1-1"]|B1|
|c0-1-1|column|["n0-1-0", "n0-1-1"]|C1|
|x0-1-1|beam|["n0-1-1", "n1-1-1"]|B1|
|c1-0-1|column|["n1-0-0", "n1-0-1"]|C1|
|x1-0-1|beam|["n1-0-1", "n2-0-1"]|B1|
|y1-0-1|beam|["n1-0-1", "n1-1-1"]|B1|
|c1-1-1|column|["n1-1-0", "n1-1-1"]|C1|
|x1-1-1|beam|["n1-1-1", "n2-1-1"]|B1|
|c2-0-1|column|["n2-0-0", "n2-0-1"]|C1|
|y2-0-1|beam|["n2-0-1", "n2-1-1"]|B1|
|c2-1-1|column|["n2-1-0", "n2-1-1"]|C1|
|c0-0-2|column|["n0-0-1", "n0-0-2"]|C1|
|x0-0-2|beam|["n0-0-2", "n1-0-2"]|B2|
|y0-0-2|beam|["n0-0-2", "n0-1-2"]|B2|
|c0-1-2|column|["n0-1-1", "n0-1-2"]|C1|
|x0-1-2|beam|["n0-1-2", "n1-1-2"]|B2|
|c1-0-2|column|["n1-0-1", "n1-0-2"]|C1|
|x1-0-2|beam|["n1-0-2", "n2-0-2"]|B2|
|y1-0-2|beam|["n1-0-2", "n1-1-2"]|B2|
|c1-1-2|column|["n1-1-1", "n1-1-2"]|C1|
|x1-1-2|beam|["n1-1-2", "n2-1-2"]|B2|
|c2-0-2|column|["n2-0-1", "n2-0-2"]|C1|
|y2-0-2|beam|["n2-0-2", "n2-1-2"]|B2|
|c2-1-2|column|["n2-1-1", "n2-1-2"]|C1|

Applies to every listed row: material = M1.

## Input t1 — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Elastic steel|steel|200000|76923.07692307692|0.3|7850|

## Input t1 — Section table

|id|type|shape · kind|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|---|
|B1|rectangular|rectangular|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|C1|rectangular|rectangular|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|
|B2|general|—|—|—|0.18|0.004319999999999999|0.0010799999999999998|0.0037078593749999985|

Applies to every listed row: name = id.

## Input t1 — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load case table — D — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-x0-0-1 → x0-0-1, D-y0-0-1 → y0-0-1, D-x0-1-1 → x0-1-1, D-x1-0-1 → x1-0-1, D-y1-0-1 → y1-0-1, D-x1-1-1 → x1-1-1, D-y2-0-1 → y2-0-1, D-x0-0-2 → x0-0-2, D-y0-0-2 → y0-0-2, D-x0-1-2 → x0-1-2, D-x1-0-2 → x1-0-2, D-y1-0-2 → y1-0-2, D-x1-1-2 → x1-1-2, D-y2-0-2 → y2-0-2|global|distributed|-8|

## Input t1 — Load case table — W-X

|Field|Value|
|---|---|
|id|W-X|
|type|wind|

## Input t1 — Load case table — W-X — Loads

|Load ID → element / node|fx|
|---|---|
|WX-0-1 → n2-0-1, WX-1-1 → n2-1-1|10|
|WX-0-2 → n2-0-2, WX-1-2 → n2-1-2|15|

Applies to every listed row: reference_frame = global; type = nodal.

## Input t1 — Load case table — W-Y

|Field|Value|
|---|---|
|id|W-Y|
|type|wind|

## Input t1 — Load case table — W-Y — Loads

|Load ID → element / node|fy|
|---|---|
|WY-0-1 → n2-0-1, WY-1-1 → n2-1-1|8|
|WY-0-2 → n2-0-2, WY-1-2 → n2-1-2|12|

Applies to every listed row: reference_frame = global; type = nodal.

## Input t1 — Combination table

|id|factors · W-X|factors · W-Y|
|---|---|---|
|D|—|—|
|D+WX|1|—|
|D+WY|—|1|

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
|dimension|3d|
|plane|null|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input t1 — Member axis data — Element reference vectors

|Field|Value|
|---|---|
|c0-0-1|[1, 0, 0]|
|x0-0-1|[0, 0, 1]|
|y0-0-1|[0, 0, 1]|
|c0-1-1|[1, 0, 0]|
|x0-1-1|[0, 0, 1]|
|c1-0-1|[1, 0, 0]|
|x1-0-1|[0, 0, 1]|
|y1-0-1|[0, 0, 1]|
|c1-1-1|[1, 0, 0]|
|x1-1-1|[0, 0, 1]|
|c2-0-1|[1, 0, 0]|
|y2-0-1|[0, 0, 1]|
|c2-1-1|[1, 0, 0]|
|c0-0-2|[1, 0, 0]|
|x0-0-2|[0, 0, 1]|
|y0-0-2|[0, 0, 1]|
|c0-1-2|[1, 0, 0]|
|x0-1-2|[0, 0, 1]|
|c1-0-2|[1, 0, 0]|
|x1-0-2|[0, 0, 1]|
|y1-0-2|[0, 0, 1]|
|c1-1-2|[1, 0, 0]|
|x1-1-2|[0, 0, 1]|
|c2-0-2|[1, 0, 0]|
|y2-0-2|[0, 0, 1]|
|c2-1-2|[1, 0, 0]|
