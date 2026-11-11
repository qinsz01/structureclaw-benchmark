## Appendix b

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Timoshenko beam/column and axial-only truss analysis.|
|outputDefinition|逐一报告全部明示工况及组合：最高层实际梁柱节点中先取X最大、再取Y最大的节点Ux、Uz、Uy；最底层先取X最小、再取Y最小的柱底全局支反力矩My及竖向反力Rz=Fz。采用带符号的m、kN.m、kN，标明节点、方向、工况或组合及当前轮次；外挑自由端不是梁柱节点。|
|executionEvidence|各变更状态保存题定引擎的实际输入或原生工程、软件版本、有效设置、成功日志以及原始结果到节点/构件/工况的映射；截屏或其他引擎结果不能替代执行证据。保留原始工况并单独执行明示组合。|
|changeInstruction|附件B为第二轮完整替换表：仅将屋面Y上边界由10m缩至5m，删除屋面y=10两节点、接至它们的上层柱及屋面梁，并删除这些梁的6kN/m线载。首层全部节点梁柱、8kN/m线载及外边柱加强截面保持。|
|documentType|Public engineering input tables|
|combinationTable|[]|

## Appendix b — Stories

|id|elevation|
|---|---|
|s1|0|
|s2|3.6|

Applies to every listed row: height = 3.6; rigid_diaphragm = false.

## Appendix b — Units

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

## Appendix b — Axis definitions

|Field|Value|
|---|---|
|globalAxes|Right-handed XYZ; Z upward.|
|planarAxes|XZ plane: local x = i to j, local y = global +Y, local z = x cross y.|
|spatialAxes|local x = i to j; y = normalize(reference cross x); z = x cross y; reference vectors are explicit per member.|
|sectionRoll|y_new=cos(theta)*y+sin(theta)*z; z_new=-sin(theta)*y+cos(theta)*z; theta in degrees.|
|reactionNaming|Rz in the task means vertical support force Fz, not nodal rotation rz.|

## Appendix b — Floor boundaries

|story|polygonXY|
|---|---|
|1|[[0, 0], [12, 0], [12, 10], [0, 10]]|
|2|[[0, 0], [6, 0], [6, 5], [0, 5]]|

Applies to every listed row: unit = m.

## Appendix b — Nodes

|id|x|y|z|restraints|
|---|---|---|---|---|
|n0-0-0|0|0|0|[true, true, true, true, true, true]|
|n0-1-0|0|5|0|[true, true, true, true, true, true]|
|n0-2-0|0|10|0|[true, true, true, true, true, true]|
|n1-0-0|6|0|0|[true, true, true, true, true, true]|
|n1-1-0|6|5|0|[true, true, true, true, true, true]|
|n1-2-0|6|10|0|[true, true, true, true, true, true]|
|n2-0-0|12|0|0|[true, true, true, true, true, true]|
|n2-1-0|12|5|0|[true, true, true, true, true, true]|
|n2-2-0|12|10|0|[true, true, true, true, true, true]|
|n0-0-1|0|0|3.6|[false, false, false, false, false, false]|
|n0-1-1|0|5|3.6|[false, false, false, false, false, false]|
|n0-2-1|0|10|3.6|[false, false, false, false, false, false]|
|n1-0-1|6|0|3.6|[false, false, false, false, false, false]|
|n1-1-1|6|5|3.6|[false, false, false, false, false, false]|
|n1-2-1|6|10|3.6|[false, false, false, false, false, false]|
|n2-0-1|12|0|3.6|[false, false, false, false, false, false]|
|n2-1-1|12|5|3.6|[false, false, false, false, false, false]|
|n2-2-1|12|10|3.6|[false, false, false, false, false, false]|
|n0-0-2|0|0|7.2|[false, false, false, false, false, false]|
|n0-1-2|0|5|7.2|[false, false, false, false, false, false]|
|n1-0-2|6|0|7.2|[false, false, false, false, false, false]|
|n1-1-2|6|5|7.2|[false, false, false, false, false, false]|

## Appendix b — Members

|id|type|nodes|section|
|---|---|---|---|
|c0-0-1|column|["n0-0-0", "n0-0-1"]|C_edge|
|x0-0-1|beam|["n0-0-1", "n1-0-1"]|B1|
|y0-0-1|beam|["n0-0-1", "n0-1-1"]|B1|
|c0-1-1|column|["n0-1-0", "n0-1-1"]|C_edge|
|x0-1-1|beam|["n0-1-1", "n1-1-1"]|B1|
|y0-1-1|beam|["n0-1-1", "n0-2-1"]|B1|
|c0-2-1|column|["n0-2-0", "n0-2-1"]|C_edge|
|x0-2-1|beam|["n0-2-1", "n1-2-1"]|B1|
|c1-0-1|column|["n1-0-0", "n1-0-1"]|C_edge|
|x1-0-1|beam|["n1-0-1", "n2-0-1"]|B1|
|y1-0-1|beam|["n1-0-1", "n1-1-1"]|B1|
|c1-1-1|column|["n1-1-0", "n1-1-1"]|C1|
|x1-1-1|beam|["n1-1-1", "n2-1-1"]|B1|
|y1-1-1|beam|["n1-1-1", "n1-2-1"]|B1|
|c1-2-1|column|["n1-2-0", "n1-2-1"]|C_edge|
|x1-2-1|beam|["n1-2-1", "n2-2-1"]|B1|
|c2-0-1|column|["n2-0-0", "n2-0-1"]|C_edge|
|y2-0-1|beam|["n2-0-1", "n2-1-1"]|B1|
|c2-1-1|column|["n2-1-0", "n2-1-1"]|C_edge|
|y2-1-1|beam|["n2-1-1", "n2-2-1"]|B1|
|c2-2-1|column|["n2-2-0", "n2-2-1"]|C_edge|
|c0-0-2|column|["n0-0-1", "n0-0-2"]|C1|
|x0-0-2|beam|["n0-0-2", "n1-0-2"]|B1|
|y0-0-2|beam|["n0-0-2", "n0-1-2"]|B1|
|c0-1-2|column|["n0-1-1", "n0-1-2"]|C1|
|x0-1-2|beam|["n0-1-2", "n1-1-2"]|B1|
|c1-0-2|column|["n1-0-1", "n1-0-2"]|C1|
|y1-0-2|beam|["n1-0-2", "n1-1-2"]|B1|
|c1-1-2|column|["n1-1-1", "n1-1-2"]|C1|

Applies to every listed row: material = M1.

## Appendix b — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Elastic steel|steel|200000|76923.07692307692|0.3|7850|

## Appendix b — Section table

|id|type|shape · kind|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|---|
|B1|rectangular|rectangular|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|C1|rectangular|rectangular|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|
|C_edge|general|—|—|—|0.25|0.0078125|0.0078125|0.008802083333333334|

Applies to every listed row: name = id.

## Appendix b — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Appendix b — Load case table — D — Loads

|Load ID → element / node|wz|
|---|---|
|D-x0-0-1 → x0-0-1, D-y0-0-1 → y0-0-1, D-x0-1-1 → x0-1-1, D-y0-1-1 → y0-1-1, D-x0-2-1 → x0-2-1, D-x1-0-1 → x1-0-1, D-y1-0-1 → y1-0-1, D-x1-1-1 → x1-1-1, D-y1-1-1 → y1-1-1, D-x1-2-1 → x1-2-1, D-y2-0-1 → y2-0-1, D-y2-1-1 → y2-1-1|-8|
|D-x0-0-2 → x0-0-2, D-y0-0-2 → y0-0-2, D-x0-1-2 → x0-1-2, D-y1-0-2 → y1-0-2|-6|

Applies to every listed row: reference_frame = global; type = distributed.

## Appendix b — Analysis settings

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Appendix b — Coordinate contract

|Field|Value|
|---|---|
|dimension|3d|
|plane|null|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Appendix b — Member axis data — Element reference vectors

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
|x1-0-1|[0, 0, 1]|
|y1-0-1|[0, 0, 1]|
|c1-1-1|[1, 0, 0]|
|x1-1-1|[0, 0, 1]|
|y1-1-1|[0, 0, 1]|
|c1-2-1|[1, 0, 0]|
|x1-2-1|[0, 0, 1]|
|c2-0-1|[1, 0, 0]|
|y2-0-1|[0, 0, 1]|
|c2-1-1|[1, 0, 0]|
|y2-1-1|[0, 0, 1]|
|c2-2-1|[1, 0, 0]|
|c0-0-2|[1, 0, 0]|
|x0-0-2|[0, 0, 1]|
|y0-0-2|[0, 0, 1]|
|c0-1-2|[1, 0, 0]|
|x0-1-2|[0, 0, 1]|
|c1-0-2|[1, 0, 0]|
|y1-0-2|[0, 0, 1]|
|c1-1-2|[1, 0, 0]|
