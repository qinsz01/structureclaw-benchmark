## Numerical inputs

|Field|Value|
|---|---|
|title|Complete numerical input appendix|
|continuityNotes|{}|

## Numerical inputs — Units

|Field|Value|
|---|---|
|coordinates|m|
|forces|kN|
|moments|kN.m|
|lineLoads|kN/m|
|E|MPa|
|G|MPa|
|density|kg/m^3|
|A|m^2|
|Iy|m^4|
|Iz|m^4|
|J|m^4|
|shapeDimensions|mm|
|rotations|rad|
|sectionRoll|degree|

## Numerical inputs — Coordinate convention

|Field|Value|
|---|---|
|dimension|3d|
|plane|null|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Numerical inputs — Nodes

|id|X_m|Y_m|Z_m|fixed_ux|fixed_uy|fixed_uz|fixed_rx|fixed_ry|fixed_rz|
|---|---|---|---|---|---|---|---|---|---|
|n0-0-0|0|0|0|true|true|true|true|true|true|
|n0-1-0|0|5|0|true|true|true|true|true|true|
|n1-0-0|6|0|0|true|true|true|true|true|true|
|n1-1-0|6|5|0|true|true|true|true|true|true|
|n2-0-0|12|0|0|true|true|true|true|true|true|
|n2-1-0|12|5|0|true|true|true|true|true|true|
|n0-0-1|0|0|3.6|false|false|false|false|false|false|
|n0-1-1|0|5|3.6|false|false|false|false|false|false|
|n1-0-1|6|0|3.6|false|false|false|false|false|false|
|n1-1-1|6|5|3.6|false|false|false|false|false|false|
|n2-0-1|12|0|3.6|false|false|false|false|false|false|
|n2-1-1|12|5|3.6|false|false|false|false|false|false|
|n0-0-2|0|0|7.2|false|false|false|false|false|false|
|n0-1-2|0|5|7.2|false|false|false|false|false|false|
|n1-0-2|6|0|7.2|false|false|false|false|false|false|
|n1-1-2|6|5|7.2|false|false|false|false|false|false|
|n2-0-2|12|0|7.2|false|false|false|false|false|false|
|n2-1-2|12|5|7.2|false|false|false|false|false|false|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-0-1|column|n0-0-0|n0-0-1|M1|C1|0|[1, 0, 0]|
|x0-0-1|beam|n0-0-1|n1-0-1|M1|B1|0|[0, 0, 1]|
|y0-0-1|beam|n0-0-1|n0-1-1|M1|B2|0|[0, 0, 1]|
|c0-1-1|column|n0-1-0|n0-1-1|M1|C1|0|[1, 0, 0]|
|x0-1-1|beam|n0-1-1|n1-1-1|M1|B1|0|[0, 0, 1]|
|c1-0-1|column|n1-0-0|n1-0-1|M1|C1|0|[1, 0, 0]|
|x1-0-1|beam|n1-0-1|n2-0-1|M1|B1|0|[0, 0, 1]|
|y1-0-1|beam|n1-0-1|n1-1-1|M1|B2|0|[0, 0, 1]|
|c1-1-1|column|n1-1-0|n1-1-1|M1|C1|0|[1, 0, 0]|
|x1-1-1|beam|n1-1-1|n2-1-1|M1|B1|0|[0, 0, 1]|
|c2-0-1|column|n2-0-0|n2-0-1|M1|C1|0|[1, 0, 0]|
|y2-0-1|beam|n2-0-1|n2-1-1|M1|B2|0|[0, 0, 1]|
|c2-1-1|column|n2-1-0|n2-1-1|M1|C1|0|[1, 0, 0]|
|c0-0-2|column|n0-0-1|n0-0-2|M1|C1|0|[1, 0, 0]|
|x0-0-2|beam|n0-0-2|n1-0-2|M1|B1|0|[0, 0, 1]|
|y0-0-2|beam|n0-0-2|n0-1-2|M1|B2|0|[0, 0, 1]|
|c0-1-2|column|n0-1-1|n0-1-2|M1|C1|0|[1, 0, 0]|
|x0-1-2|beam|n0-1-2|n1-1-2|M1|B1|0|[0, 0, 1]|
|c1-0-2|column|n1-0-1|n1-0-2|M1|C1|0|[1, 0, 0]|
|x1-0-2|beam|n1-0-2|n2-0-2|M1|B1|0|[0, 0, 1]|
|y1-0-2|beam|n1-0-2|n1-1-2|M1|B2|0|[0, 0, 1]|
|c1-1-2|column|n1-1-1|n1-1-2|M1|C1|0|[1, 0, 0]|
|x1-1-2|beam|n1-1-2|n2-1-2|M1|B1|0|[0, 0, 1]|
|c2-0-2|column|n2-0-1|n2-0-2|M1|C1|0|[1, 0, 0]|
|y2-0-2|beam|n2-0-2|n2-1-2|M1|B2|0|[0, 0, 1]|
|c2-1-2|column|n2-1-1|n2-1-2|M1|C1|0|[1, 0, 0]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Numerical inputs — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|288.0|576.0|0.165888|0.0045864714|0.0011466179|0.0031492576|
|B2|288.0|672.0|0.193536|0.0072831468|0.0013377208|0.0039102065|
|C1|480.0|480.0|0.2304|0.00442368|0.00442368|0.0074760192|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-1 → x0-0-1, D-2 → y0-0-1, D-3 → x0-1-1, D-4 → x1-0-1, D-5 → y1-0-1, D-6 → x1-1-1, D-7 → y2-0-1, D-8 → x0-0-2, D-9 → y0-0-2, D-10 → x0-1-2, D-11 → x1-0-2, D-12 → y1-0-2, D-13 → x1-1-2, D-14 → y2-0-2|global|distributed|-8|

## Numerical inputs — Load cases — Wx

|Field|Value|
|---|---|
|id|Wx|
|type|wind|

## Numerical inputs — Load cases — Wx — Loads

|Load ID → element / node|fx|
|---|---|
|Wx-1 → n2-1-1|10|
|Wx-2 → n2-1-2|20|

Applies to every listed row: reference_frame = global; type = nodal.

## Numerical inputs — Load cases — Wy

|Field|Value|
|---|---|
|id|Wy|
|type|wind|

## Numerical inputs — Load cases — Wy — Loads

|Load ID → element / node|fy|
|---|---|
|Wy-1 → n2-1-1|8|
|Wy-2 → n2-1-2|16|

Applies to every listed row: reference_frame = global; type = nodal.

## Numerical inputs — Load combinations

|id|factors · Wx|factors · Wy|
|---|---|---|
|C0|—|—|
|CX|1|—|
|CY|—|1|

Applies to every listed row: factors · D = 1.

## Numerical inputs — Analysis settings

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Numerical inputs — Floor table

|id|elevation|
|---|---|
|s1|0|
|s2|3.6|

Applies to every listed row: height = 3.6; rigid_diaphragm = false.

## Requested outputs

|Field|Value|
|---|---|
|figures|[]|
|interactions|[]|

## Requested outputs — Quantities

|id|selection · id|location · id|component|unit|
|---|---|---|---|---|
|combination-C0-node-n0-0-1-ux|C0|n0-0-1|ux|m|
|combination-C0-node-n0-0-1-uy|C0|n0-0-1|uy|m|
|combination-C0-node-n0-0-1-uz|C0|n0-0-1|uz|m|
|combination-C0-node-n0-0-0-ux|C0|n0-0-0|ux|m|
|combination-C0-node-n0-0-0-uy|C0|n0-0-0|uy|m|
|combination-C0-node-n0-1-1-ux|C0|n0-1-1|ux|m|
|combination-C0-node-n0-1-1-uy|C0|n0-1-1|uy|m|
|combination-C0-node-n0-1-1-uz|C0|n0-1-1|uz|m|
|combination-C0-node-n0-1-0-ux|C0|n0-1-0|ux|m|
|combination-C0-node-n0-1-0-uy|C0|n0-1-0|uy|m|
|combination-C0-node-n1-0-1-ux|C0|n1-0-1|ux|m|
|combination-C0-node-n1-0-1-uy|C0|n1-0-1|uy|m|
|combination-C0-node-n1-0-1-uz|C0|n1-0-1|uz|m|
|combination-C0-node-n1-0-0-ux|C0|n1-0-0|ux|m|
|combination-C0-node-n1-0-0-uy|C0|n1-0-0|uy|m|
|combination-C0-node-n1-1-1-ux|C0|n1-1-1|ux|m|
|combination-C0-node-n1-1-1-uy|C0|n1-1-1|uy|m|
|combination-C0-node-n1-1-1-uz|C0|n1-1-1|uz|m|
|combination-C0-node-n1-1-0-ux|C0|n1-1-0|ux|m|
|combination-C0-node-n1-1-0-uy|C0|n1-1-0|uy|m|
|combination-C0-node-n2-0-1-ux|C0|n2-0-1|ux|m|
|combination-C0-node-n2-0-1-uy|C0|n2-0-1|uy|m|
|combination-C0-node-n2-0-1-uz|C0|n2-0-1|uz|m|
|combination-C0-node-n2-0-0-ux|C0|n2-0-0|ux|m|
|combination-C0-node-n2-0-0-uy|C0|n2-0-0|uy|m|
|combination-C0-node-n2-1-1-ux|C0|n2-1-1|ux|m|
|combination-C0-node-n2-1-1-uy|C0|n2-1-1|uy|m|
|combination-C0-node-n2-1-1-uz|C0|n2-1-1|uz|m|
|combination-C0-node-n2-1-0-ux|C0|n2-1-0|ux|m|
|combination-C0-node-n2-1-0-uy|C0|n2-1-0|uy|m|
|combination-C0-node-n0-0-2-ux|C0|n0-0-2|ux|m|
|combination-C0-node-n0-0-2-uy|C0|n0-0-2|uy|m|
|combination-C0-node-n0-0-2-uz|C0|n0-0-2|uz|m|
|combination-C0-node-n0-1-2-ux|C0|n0-1-2|ux|m|
|combination-C0-node-n0-1-2-uy|C0|n0-1-2|uy|m|
|combination-C0-node-n0-1-2-uz|C0|n0-1-2|uz|m|
|combination-C0-node-n1-0-2-ux|C0|n1-0-2|ux|m|
|combination-C0-node-n1-0-2-uy|C0|n1-0-2|uy|m|
|combination-C0-node-n1-0-2-uz|C0|n1-0-2|uz|m|
|combination-C0-node-n1-1-2-ux|C0|n1-1-2|ux|m|
|combination-C0-node-n1-1-2-uy|C0|n1-1-2|uy|m|
|combination-C0-node-n1-1-2-uz|C0|n1-1-2|uz|m|
|combination-C0-node-n2-0-2-ux|C0|n2-0-2|ux|m|
|combination-C0-node-n2-0-2-uy|C0|n2-0-2|uy|m|
|combination-C0-node-n2-0-2-uz|C0|n2-0-2|uz|m|
|combination-C0-node-n2-1-2-ux|C0|n2-1-2|ux|m|
|combination-C0-node-n2-1-2-uy|C0|n2-1-2|uy|m|
|combination-C0-node-n2-1-2-uz|C0|n2-1-2|uz|m|
|combination-C0-node-n0-0-0-Fx|C0|n0-0-0|Fx|kN|
|combination-C0-node-n0-0-0-Fy|C0|n0-0-0|Fy|kN|
|combination-C0-node-n0-0-0-Fz|C0|n0-0-0|Fz|kN|
|combination-C0-node-n0-0-0-Mx|C0|n0-0-0|Mx|kN.m|
|combination-C0-node-n0-0-0-My|C0|n0-0-0|My|kN.m|
|combination-C0-node-n0-0-0-Mz|C0|n0-0-0|Mz|kN.m|
|combination-C0-node-n0-1-0-Fx|C0|n0-1-0|Fx|kN|
|combination-C0-node-n0-1-0-Fy|C0|n0-1-0|Fy|kN|
|combination-C0-node-n0-1-0-Fz|C0|n0-1-0|Fz|kN|
|combination-C0-node-n0-1-0-Mx|C0|n0-1-0|Mx|kN.m|
|combination-C0-node-n0-1-0-My|C0|n0-1-0|My|kN.m|
|combination-C0-node-n0-1-0-Mz|C0|n0-1-0|Mz|kN.m|
|combination-C0-node-n1-0-0-Fx|C0|n1-0-0|Fx|kN|
|combination-C0-node-n1-0-0-Fy|C0|n1-0-0|Fy|kN|
|combination-C0-node-n1-0-0-Fz|C0|n1-0-0|Fz|kN|
|combination-C0-node-n1-0-0-Mx|C0|n1-0-0|Mx|kN.m|
|combination-C0-node-n1-0-0-My|C0|n1-0-0|My|kN.m|
|combination-C0-node-n1-0-0-Mz|C0|n1-0-0|Mz|kN.m|
|combination-C0-node-n1-1-0-Fx|C0|n1-1-0|Fx|kN|
|combination-C0-node-n1-1-0-Fy|C0|n1-1-0|Fy|kN|
|combination-C0-node-n1-1-0-Fz|C0|n1-1-0|Fz|kN|
|combination-C0-node-n1-1-0-Mx|C0|n1-1-0|Mx|kN.m|
|combination-C0-node-n1-1-0-My|C0|n1-1-0|My|kN.m|
|combination-C0-node-n1-1-0-Mz|C0|n1-1-0|Mz|kN.m|
|combination-C0-node-n2-0-0-Fx|C0|n2-0-0|Fx|kN|
|combination-C0-node-n2-0-0-Fy|C0|n2-0-0|Fy|kN|
|combination-C0-node-n2-0-0-Fz|C0|n2-0-0|Fz|kN|
|combination-C0-node-n2-0-0-Mx|C0|n2-0-0|Mx|kN.m|
|combination-C0-node-n2-0-0-My|C0|n2-0-0|My|kN.m|
|combination-C0-node-n2-0-0-Mz|C0|n2-0-0|Mz|kN.m|
|combination-C0-node-n2-1-0-Fx|C0|n2-1-0|Fx|kN|
|combination-C0-node-n2-1-0-Fy|C0|n2-1-0|Fy|kN|
|combination-C0-node-n2-1-0-Fz|C0|n2-1-0|Fz|kN|
|combination-C0-node-n2-1-0-Mx|C0|n2-1-0|Mx|kN.m|
|combination-C0-node-n2-1-0-My|C0|n2-1-0|My|kN.m|
|combination-C0-node-n2-1-0-Mz|C0|n2-1-0|Mz|kN.m|
|combination-CX-node-n0-0-1-ux|CX|n0-0-1|ux|m|
|combination-CX-node-n0-0-1-uy|CX|n0-0-1|uy|m|
|combination-CX-node-n0-0-1-uz|CX|n0-0-1|uz|m|
|combination-CX-node-n0-0-0-ux|CX|n0-0-0|ux|m|
|combination-CX-node-n0-0-0-uy|CX|n0-0-0|uy|m|
|combination-CX-node-n0-1-1-ux|CX|n0-1-1|ux|m|
|combination-CX-node-n0-1-1-uy|CX|n0-1-1|uy|m|
|combination-CX-node-n0-1-1-uz|CX|n0-1-1|uz|m|
|combination-CX-node-n0-1-0-ux|CX|n0-1-0|ux|m|
|combination-CX-node-n0-1-0-uy|CX|n0-1-0|uy|m|
|combination-CX-node-n1-0-1-ux|CX|n1-0-1|ux|m|
|combination-CX-node-n1-0-1-uy|CX|n1-0-1|uy|m|
|combination-CX-node-n1-0-1-uz|CX|n1-0-1|uz|m|
|combination-CX-node-n1-0-0-ux|CX|n1-0-0|ux|m|
|combination-CX-node-n1-0-0-uy|CX|n1-0-0|uy|m|
|combination-CX-node-n1-1-1-ux|CX|n1-1-1|ux|m|
|combination-CX-node-n1-1-1-uy|CX|n1-1-1|uy|m|
|combination-CX-node-n1-1-1-uz|CX|n1-1-1|uz|m|
|combination-CX-node-n1-1-0-ux|CX|n1-1-0|ux|m|
|combination-CX-node-n1-1-0-uy|CX|n1-1-0|uy|m|
|combination-CX-node-n2-0-1-ux|CX|n2-0-1|ux|m|
|combination-CX-node-n2-0-1-uy|CX|n2-0-1|uy|m|
|combination-CX-node-n2-0-1-uz|CX|n2-0-1|uz|m|
|combination-CX-node-n2-0-0-ux|CX|n2-0-0|ux|m|
|combination-CX-node-n2-0-0-uy|CX|n2-0-0|uy|m|
|combination-CX-node-n2-1-1-ux|CX|n2-1-1|ux|m|
|combination-CX-node-n2-1-1-uy|CX|n2-1-1|uy|m|
|combination-CX-node-n2-1-1-uz|CX|n2-1-1|uz|m|
|combination-CX-node-n2-1-0-ux|CX|n2-1-0|ux|m|
|combination-CX-node-n2-1-0-uy|CX|n2-1-0|uy|m|
|combination-CX-node-n0-0-2-ux|CX|n0-0-2|ux|m|
|combination-CX-node-n0-0-2-uy|CX|n0-0-2|uy|m|
|combination-CX-node-n0-0-2-uz|CX|n0-0-2|uz|m|
|combination-CX-node-n0-1-2-ux|CX|n0-1-2|ux|m|
|combination-CX-node-n0-1-2-uy|CX|n0-1-2|uy|m|
|combination-CX-node-n0-1-2-uz|CX|n0-1-2|uz|m|
|combination-CX-node-n1-0-2-ux|CX|n1-0-2|ux|m|
|combination-CX-node-n1-0-2-uy|CX|n1-0-2|uy|m|
|combination-CX-node-n1-0-2-uz|CX|n1-0-2|uz|m|
|combination-CX-node-n1-1-2-ux|CX|n1-1-2|ux|m|
|combination-CX-node-n1-1-2-uy|CX|n1-1-2|uy|m|
|combination-CX-node-n1-1-2-uz|CX|n1-1-2|uz|m|
|combination-CX-node-n2-0-2-ux|CX|n2-0-2|ux|m|
|combination-CX-node-n2-0-2-uy|CX|n2-0-2|uy|m|
|combination-CX-node-n2-0-2-uz|CX|n2-0-2|uz|m|
|combination-CX-node-n2-1-2-ux|CX|n2-1-2|ux|m|
|combination-CX-node-n2-1-2-uy|CX|n2-1-2|uy|m|
|combination-CX-node-n2-1-2-uz|CX|n2-1-2|uz|m|
|combination-CX-node-n0-0-0-Fx|CX|n0-0-0|Fx|kN|
|combination-CX-node-n0-0-0-Fy|CX|n0-0-0|Fy|kN|
|combination-CX-node-n0-0-0-Fz|CX|n0-0-0|Fz|kN|
|combination-CX-node-n0-0-0-Mx|CX|n0-0-0|Mx|kN.m|
|combination-CX-node-n0-0-0-My|CX|n0-0-0|My|kN.m|
|combination-CX-node-n0-0-0-Mz|CX|n0-0-0|Mz|kN.m|
|combination-CX-node-n0-1-0-Fx|CX|n0-1-0|Fx|kN|
|combination-CX-node-n0-1-0-Fy|CX|n0-1-0|Fy|kN|
|combination-CX-node-n0-1-0-Fz|CX|n0-1-0|Fz|kN|
|combination-CX-node-n0-1-0-Mx|CX|n0-1-0|Mx|kN.m|
|combination-CX-node-n0-1-0-My|CX|n0-1-0|My|kN.m|
|combination-CX-node-n0-1-0-Mz|CX|n0-1-0|Mz|kN.m|
|combination-CX-node-n1-0-0-Fx|CX|n1-0-0|Fx|kN|
|combination-CX-node-n1-0-0-Fy|CX|n1-0-0|Fy|kN|
|combination-CX-node-n1-0-0-Fz|CX|n1-0-0|Fz|kN|
|combination-CX-node-n1-0-0-Mx|CX|n1-0-0|Mx|kN.m|
|combination-CX-node-n1-0-0-My|CX|n1-0-0|My|kN.m|
|combination-CX-node-n1-0-0-Mz|CX|n1-0-0|Mz|kN.m|
|combination-CX-node-n1-1-0-Fx|CX|n1-1-0|Fx|kN|
|combination-CX-node-n1-1-0-Fy|CX|n1-1-0|Fy|kN|
|combination-CX-node-n1-1-0-Fz|CX|n1-1-0|Fz|kN|
|combination-CX-node-n1-1-0-Mx|CX|n1-1-0|Mx|kN.m|
|combination-CX-node-n1-1-0-My|CX|n1-1-0|My|kN.m|
|combination-CX-node-n1-1-0-Mz|CX|n1-1-0|Mz|kN.m|
|combination-CX-node-n2-0-0-Fx|CX|n2-0-0|Fx|kN|
|combination-CX-node-n2-0-0-Fy|CX|n2-0-0|Fy|kN|
|combination-CX-node-n2-0-0-Fz|CX|n2-0-0|Fz|kN|
|combination-CX-node-n2-0-0-Mx|CX|n2-0-0|Mx|kN.m|
|combination-CX-node-n2-0-0-My|CX|n2-0-0|My|kN.m|
|combination-CX-node-n2-0-0-Mz|CX|n2-0-0|Mz|kN.m|
|combination-CX-node-n2-1-0-Fx|CX|n2-1-0|Fx|kN|
|combination-CX-node-n2-1-0-Fy|CX|n2-1-0|Fy|kN|
|combination-CX-node-n2-1-0-Fz|CX|n2-1-0|Fz|kN|
|combination-CX-node-n2-1-0-Mx|CX|n2-1-0|Mx|kN.m|
|combination-CX-node-n2-1-0-My|CX|n2-1-0|My|kN.m|
|combination-CX-node-n2-1-0-Mz|CX|n2-1-0|Mz|kN.m|
|combination-CY-node-n0-0-1-ux|CY|n0-0-1|ux|m|
|combination-CY-node-n0-0-1-uy|CY|n0-0-1|uy|m|
|combination-CY-node-n0-0-1-uz|CY|n0-0-1|uz|m|
|combination-CY-node-n0-0-0-ux|CY|n0-0-0|ux|m|
|combination-CY-node-n0-0-0-uy|CY|n0-0-0|uy|m|
|combination-CY-node-n0-1-1-ux|CY|n0-1-1|ux|m|
|combination-CY-node-n0-1-1-uy|CY|n0-1-1|uy|m|
|combination-CY-node-n0-1-1-uz|CY|n0-1-1|uz|m|
|combination-CY-node-n0-1-0-ux|CY|n0-1-0|ux|m|
|combination-CY-node-n0-1-0-uy|CY|n0-1-0|uy|m|
|combination-CY-node-n1-0-1-ux|CY|n1-0-1|ux|m|
|combination-CY-node-n1-0-1-uy|CY|n1-0-1|uy|m|
|combination-CY-node-n1-0-1-uz|CY|n1-0-1|uz|m|
|combination-CY-node-n1-0-0-ux|CY|n1-0-0|ux|m|
|combination-CY-node-n1-0-0-uy|CY|n1-0-0|uy|m|
|combination-CY-node-n1-1-1-ux|CY|n1-1-1|ux|m|
|combination-CY-node-n1-1-1-uy|CY|n1-1-1|uy|m|
|combination-CY-node-n1-1-1-uz|CY|n1-1-1|uz|m|
|combination-CY-node-n1-1-0-ux|CY|n1-1-0|ux|m|
|combination-CY-node-n1-1-0-uy|CY|n1-1-0|uy|m|
|combination-CY-node-n2-0-1-ux|CY|n2-0-1|ux|m|
|combination-CY-node-n2-0-1-uy|CY|n2-0-1|uy|m|
|combination-CY-node-n2-0-1-uz|CY|n2-0-1|uz|m|
|combination-CY-node-n2-0-0-ux|CY|n2-0-0|ux|m|
|combination-CY-node-n2-0-0-uy|CY|n2-0-0|uy|m|
|combination-CY-node-n2-1-1-ux|CY|n2-1-1|ux|m|
|combination-CY-node-n2-1-1-uy|CY|n2-1-1|uy|m|
|combination-CY-node-n2-1-1-uz|CY|n2-1-1|uz|m|
|combination-CY-node-n2-1-0-ux|CY|n2-1-0|ux|m|
|combination-CY-node-n2-1-0-uy|CY|n2-1-0|uy|m|
|combination-CY-node-n0-0-2-ux|CY|n0-0-2|ux|m|
|combination-CY-node-n0-0-2-uy|CY|n0-0-2|uy|m|
|combination-CY-node-n0-0-2-uz|CY|n0-0-2|uz|m|
|combination-CY-node-n0-1-2-ux|CY|n0-1-2|ux|m|
|combination-CY-node-n0-1-2-uy|CY|n0-1-2|uy|m|
|combination-CY-node-n0-1-2-uz|CY|n0-1-2|uz|m|
|combination-CY-node-n1-0-2-ux|CY|n1-0-2|ux|m|
|combination-CY-node-n1-0-2-uy|CY|n1-0-2|uy|m|
|combination-CY-node-n1-0-2-uz|CY|n1-0-2|uz|m|
|combination-CY-node-n1-1-2-ux|CY|n1-1-2|ux|m|
|combination-CY-node-n1-1-2-uy|CY|n1-1-2|uy|m|
|combination-CY-node-n1-1-2-uz|CY|n1-1-2|uz|m|
|combination-CY-node-n2-0-2-ux|CY|n2-0-2|ux|m|
|combination-CY-node-n2-0-2-uy|CY|n2-0-2|uy|m|
|combination-CY-node-n2-0-2-uz|CY|n2-0-2|uz|m|
|combination-CY-node-n2-1-2-ux|CY|n2-1-2|ux|m|
|combination-CY-node-n2-1-2-uy|CY|n2-1-2|uy|m|
|combination-CY-node-n2-1-2-uz|CY|n2-1-2|uz|m|
|combination-CY-node-n0-0-0-Fx|CY|n0-0-0|Fx|kN|
|combination-CY-node-n0-0-0-Fy|CY|n0-0-0|Fy|kN|
|combination-CY-node-n0-0-0-Fz|CY|n0-0-0|Fz|kN|
|combination-CY-node-n0-0-0-Mx|CY|n0-0-0|Mx|kN.m|
|combination-CY-node-n0-0-0-My|CY|n0-0-0|My|kN.m|
|combination-CY-node-n0-0-0-Mz|CY|n0-0-0|Mz|kN.m|
|combination-CY-node-n0-1-0-Fx|CY|n0-1-0|Fx|kN|
|combination-CY-node-n0-1-0-Fy|CY|n0-1-0|Fy|kN|
|combination-CY-node-n0-1-0-Fz|CY|n0-1-0|Fz|kN|
|combination-CY-node-n0-1-0-Mx|CY|n0-1-0|Mx|kN.m|
|combination-CY-node-n0-1-0-My|CY|n0-1-0|My|kN.m|
|combination-CY-node-n0-1-0-Mz|CY|n0-1-0|Mz|kN.m|
|combination-CY-node-n1-0-0-Fx|CY|n1-0-0|Fx|kN|
|combination-CY-node-n1-0-0-Fy|CY|n1-0-0|Fy|kN|
|combination-CY-node-n1-0-0-Fz|CY|n1-0-0|Fz|kN|
|combination-CY-node-n1-0-0-Mx|CY|n1-0-0|Mx|kN.m|
|combination-CY-node-n1-0-0-My|CY|n1-0-0|My|kN.m|
|combination-CY-node-n1-0-0-Mz|CY|n1-0-0|Mz|kN.m|
|combination-CY-node-n1-1-0-Fx|CY|n1-1-0|Fx|kN|
|combination-CY-node-n1-1-0-Fy|CY|n1-1-0|Fy|kN|
|combination-CY-node-n1-1-0-Fz|CY|n1-1-0|Fz|kN|
|combination-CY-node-n1-1-0-Mx|CY|n1-1-0|Mx|kN.m|
|combination-CY-node-n1-1-0-My|CY|n1-1-0|My|kN.m|
|combination-CY-node-n1-1-0-Mz|CY|n1-1-0|Mz|kN.m|
|combination-CY-node-n2-0-0-Fx|CY|n2-0-0|Fx|kN|
|combination-CY-node-n2-0-0-Fy|CY|n2-0-0|Fy|kN|
|combination-CY-node-n2-0-0-Fz|CY|n2-0-0|Fz|kN|
|combination-CY-node-n2-0-0-Mx|CY|n2-0-0|Mx|kN.m|
|combination-CY-node-n2-0-0-My|CY|n2-0-0|My|kN.m|
|combination-CY-node-n2-0-0-Mz|CY|n2-0-0|Mz|kN.m|
|combination-CY-node-n2-1-0-Fx|CY|n2-1-0|Fx|kN|
|combination-CY-node-n2-1-0-Fy|CY|n2-1-0|Fy|kN|
|combination-CY-node-n2-1-0-Fz|CY|n2-1-0|Fz|kN|
|combination-CY-node-n2-1-0-Mx|CY|n2-1-0|Mx|kN.m|
|combination-CY-node-n2-1-0-My|CY|n2-1-0|My|kN.m|
|combination-CY-node-n2-1-0-Mz|CY|n2-1-0|Mz|kN.m|

Applies to every listed row: selection · kind = combination; location · kind = node.

## Requested outputs — Derived

|id|operation|operands|unit|description|
|---|---|---|---|---|
|C0-drift-n0-0-0-n0-0-1-ux|difference|["combination-C0-node-n0-0-1-ux", "combination-C0-node-n0-0-0-ux"]|m|n0-0-1 minus n0-0-0: ux; signed story displacement difference|
|C0-drift-n0-0-0-n0-0-1-uy|difference|["combination-C0-node-n0-0-1-uy", "combination-C0-node-n0-0-0-uy"]|m|n0-0-1 minus n0-0-0: uy; signed story displacement difference|
|C0-drift-n0-1-0-n0-1-1-ux|difference|["combination-C0-node-n0-1-1-ux", "combination-C0-node-n0-1-0-ux"]|m|n0-1-1 minus n0-1-0: ux; signed story displacement difference|
|C0-drift-n0-1-0-n0-1-1-uy|difference|["combination-C0-node-n0-1-1-uy", "combination-C0-node-n0-1-0-uy"]|m|n0-1-1 minus n0-1-0: uy; signed story displacement difference|
|C0-drift-n1-0-0-n1-0-1-ux|difference|["combination-C0-node-n1-0-1-ux", "combination-C0-node-n1-0-0-ux"]|m|n1-0-1 minus n1-0-0: ux; signed story displacement difference|
|C0-drift-n1-0-0-n1-0-1-uy|difference|["combination-C0-node-n1-0-1-uy", "combination-C0-node-n1-0-0-uy"]|m|n1-0-1 minus n1-0-0: uy; signed story displacement difference|
|C0-drift-n1-1-0-n1-1-1-ux|difference|["combination-C0-node-n1-1-1-ux", "combination-C0-node-n1-1-0-ux"]|m|n1-1-1 minus n1-1-0: ux; signed story displacement difference|
|C0-drift-n1-1-0-n1-1-1-uy|difference|["combination-C0-node-n1-1-1-uy", "combination-C0-node-n1-1-0-uy"]|m|n1-1-1 minus n1-1-0: uy; signed story displacement difference|
|C0-drift-n2-0-0-n2-0-1-ux|difference|["combination-C0-node-n2-0-1-ux", "combination-C0-node-n2-0-0-ux"]|m|n2-0-1 minus n2-0-0: ux; signed story displacement difference|
|C0-drift-n2-0-0-n2-0-1-uy|difference|["combination-C0-node-n2-0-1-uy", "combination-C0-node-n2-0-0-uy"]|m|n2-0-1 minus n2-0-0: uy; signed story displacement difference|
|C0-drift-n2-1-0-n2-1-1-ux|difference|["combination-C0-node-n2-1-1-ux", "combination-C0-node-n2-1-0-ux"]|m|n2-1-1 minus n2-1-0: ux; signed story displacement difference|
|C0-drift-n2-1-0-n2-1-1-uy|difference|["combination-C0-node-n2-1-1-uy", "combination-C0-node-n2-1-0-uy"]|m|n2-1-1 minus n2-1-0: uy; signed story displacement difference|
|C0-drift-n0-0-1-n0-0-2-ux|difference|["combination-C0-node-n0-0-2-ux", "combination-C0-node-n0-0-1-ux"]|m|n0-0-2 minus n0-0-1: ux; signed story displacement difference|
|C0-drift-n0-0-1-n0-0-2-uy|difference|["combination-C0-node-n0-0-2-uy", "combination-C0-node-n0-0-1-uy"]|m|n0-0-2 minus n0-0-1: uy; signed story displacement difference|
|C0-drift-n0-1-1-n0-1-2-ux|difference|["combination-C0-node-n0-1-2-ux", "combination-C0-node-n0-1-1-ux"]|m|n0-1-2 minus n0-1-1: ux; signed story displacement difference|
|C0-drift-n0-1-1-n0-1-2-uy|difference|["combination-C0-node-n0-1-2-uy", "combination-C0-node-n0-1-1-uy"]|m|n0-1-2 minus n0-1-1: uy; signed story displacement difference|
|C0-drift-n1-0-1-n1-0-2-ux|difference|["combination-C0-node-n1-0-2-ux", "combination-C0-node-n1-0-1-ux"]|m|n1-0-2 minus n1-0-1: ux; signed story displacement difference|
|C0-drift-n1-0-1-n1-0-2-uy|difference|["combination-C0-node-n1-0-2-uy", "combination-C0-node-n1-0-1-uy"]|m|n1-0-2 minus n1-0-1: uy; signed story displacement difference|
|C0-drift-n1-1-1-n1-1-2-ux|difference|["combination-C0-node-n1-1-2-ux", "combination-C0-node-n1-1-1-ux"]|m|n1-1-2 minus n1-1-1: ux; signed story displacement difference|
|C0-drift-n1-1-1-n1-1-2-uy|difference|["combination-C0-node-n1-1-2-uy", "combination-C0-node-n1-1-1-uy"]|m|n1-1-2 minus n1-1-1: uy; signed story displacement difference|
|C0-drift-n2-0-1-n2-0-2-ux|difference|["combination-C0-node-n2-0-2-ux", "combination-C0-node-n2-0-1-ux"]|m|n2-0-2 minus n2-0-1: ux; signed story displacement difference|
|C0-drift-n2-0-1-n2-0-2-uy|difference|["combination-C0-node-n2-0-2-uy", "combination-C0-node-n2-0-1-uy"]|m|n2-0-2 minus n2-0-1: uy; signed story displacement difference|
|C0-drift-n2-1-1-n2-1-2-ux|difference|["combination-C0-node-n2-1-2-ux", "combination-C0-node-n2-1-1-ux"]|m|n2-1-2 minus n2-1-1: ux; signed story displacement difference|
|C0-drift-n2-1-1-n2-1-2-uy|difference|["combination-C0-node-n2-1-2-uy", "combination-C0-node-n2-1-1-uy"]|m|n2-1-2 minus n2-1-1: uy; signed story displacement difference|
|CX-drift-n0-0-0-n0-0-1-ux|difference|["combination-CX-node-n0-0-1-ux", "combination-CX-node-n0-0-0-ux"]|m|n0-0-1 minus n0-0-0: ux; signed story displacement difference|
|CX-drift-n0-0-0-n0-0-1-uy|difference|["combination-CX-node-n0-0-1-uy", "combination-CX-node-n0-0-0-uy"]|m|n0-0-1 minus n0-0-0: uy; signed story displacement difference|
|CX-drift-n0-1-0-n0-1-1-ux|difference|["combination-CX-node-n0-1-1-ux", "combination-CX-node-n0-1-0-ux"]|m|n0-1-1 minus n0-1-0: ux; signed story displacement difference|
|CX-drift-n0-1-0-n0-1-1-uy|difference|["combination-CX-node-n0-1-1-uy", "combination-CX-node-n0-1-0-uy"]|m|n0-1-1 minus n0-1-0: uy; signed story displacement difference|
|CX-drift-n1-0-0-n1-0-1-ux|difference|["combination-CX-node-n1-0-1-ux", "combination-CX-node-n1-0-0-ux"]|m|n1-0-1 minus n1-0-0: ux; signed story displacement difference|
|CX-drift-n1-0-0-n1-0-1-uy|difference|["combination-CX-node-n1-0-1-uy", "combination-CX-node-n1-0-0-uy"]|m|n1-0-1 minus n1-0-0: uy; signed story displacement difference|
|CX-drift-n1-1-0-n1-1-1-ux|difference|["combination-CX-node-n1-1-1-ux", "combination-CX-node-n1-1-0-ux"]|m|n1-1-1 minus n1-1-0: ux; signed story displacement difference|
|CX-drift-n1-1-0-n1-1-1-uy|difference|["combination-CX-node-n1-1-1-uy", "combination-CX-node-n1-1-0-uy"]|m|n1-1-1 minus n1-1-0: uy; signed story displacement difference|
|CX-drift-n2-0-0-n2-0-1-ux|difference|["combination-CX-node-n2-0-1-ux", "combination-CX-node-n2-0-0-ux"]|m|n2-0-1 minus n2-0-0: ux; signed story displacement difference|
|CX-drift-n2-0-0-n2-0-1-uy|difference|["combination-CX-node-n2-0-1-uy", "combination-CX-node-n2-0-0-uy"]|m|n2-0-1 minus n2-0-0: uy; signed story displacement difference|
|CX-drift-n2-1-0-n2-1-1-ux|difference|["combination-CX-node-n2-1-1-ux", "combination-CX-node-n2-1-0-ux"]|m|n2-1-1 minus n2-1-0: ux; signed story displacement difference|
|CX-drift-n2-1-0-n2-1-1-uy|difference|["combination-CX-node-n2-1-1-uy", "combination-CX-node-n2-1-0-uy"]|m|n2-1-1 minus n2-1-0: uy; signed story displacement difference|
|CX-drift-n0-0-1-n0-0-2-ux|difference|["combination-CX-node-n0-0-2-ux", "combination-CX-node-n0-0-1-ux"]|m|n0-0-2 minus n0-0-1: ux; signed story displacement difference|
|CX-drift-n0-0-1-n0-0-2-uy|difference|["combination-CX-node-n0-0-2-uy", "combination-CX-node-n0-0-1-uy"]|m|n0-0-2 minus n0-0-1: uy; signed story displacement difference|
|CX-drift-n0-1-1-n0-1-2-ux|difference|["combination-CX-node-n0-1-2-ux", "combination-CX-node-n0-1-1-ux"]|m|n0-1-2 minus n0-1-1: ux; signed story displacement difference|
|CX-drift-n0-1-1-n0-1-2-uy|difference|["combination-CX-node-n0-1-2-uy", "combination-CX-node-n0-1-1-uy"]|m|n0-1-2 minus n0-1-1: uy; signed story displacement difference|
|CX-drift-n1-0-1-n1-0-2-ux|difference|["combination-CX-node-n1-0-2-ux", "combination-CX-node-n1-0-1-ux"]|m|n1-0-2 minus n1-0-1: ux; signed story displacement difference|
|CX-drift-n1-0-1-n1-0-2-uy|difference|["combination-CX-node-n1-0-2-uy", "combination-CX-node-n1-0-1-uy"]|m|n1-0-2 minus n1-0-1: uy; signed story displacement difference|
|CX-drift-n1-1-1-n1-1-2-ux|difference|["combination-CX-node-n1-1-2-ux", "combination-CX-node-n1-1-1-ux"]|m|n1-1-2 minus n1-1-1: ux; signed story displacement difference|
|CX-drift-n1-1-1-n1-1-2-uy|difference|["combination-CX-node-n1-1-2-uy", "combination-CX-node-n1-1-1-uy"]|m|n1-1-2 minus n1-1-1: uy; signed story displacement difference|
|CX-drift-n2-0-1-n2-0-2-ux|difference|["combination-CX-node-n2-0-2-ux", "combination-CX-node-n2-0-1-ux"]|m|n2-0-2 minus n2-0-1: ux; signed story displacement difference|
|CX-drift-n2-0-1-n2-0-2-uy|difference|["combination-CX-node-n2-0-2-uy", "combination-CX-node-n2-0-1-uy"]|m|n2-0-2 minus n2-0-1: uy; signed story displacement difference|
|CX-drift-n2-1-1-n2-1-2-ux|difference|["combination-CX-node-n2-1-2-ux", "combination-CX-node-n2-1-1-ux"]|m|n2-1-2 minus n2-1-1: ux; signed story displacement difference|
|CX-drift-n2-1-1-n2-1-2-uy|difference|["combination-CX-node-n2-1-2-uy", "combination-CX-node-n2-1-1-uy"]|m|n2-1-2 minus n2-1-1: uy; signed story displacement difference|
|CY-drift-n0-0-0-n0-0-1-ux|difference|["combination-CY-node-n0-0-1-ux", "combination-CY-node-n0-0-0-ux"]|m|n0-0-1 minus n0-0-0: ux; signed story displacement difference|
|CY-drift-n0-0-0-n0-0-1-uy|difference|["combination-CY-node-n0-0-1-uy", "combination-CY-node-n0-0-0-uy"]|m|n0-0-1 minus n0-0-0: uy; signed story displacement difference|
|CY-drift-n0-1-0-n0-1-1-ux|difference|["combination-CY-node-n0-1-1-ux", "combination-CY-node-n0-1-0-ux"]|m|n0-1-1 minus n0-1-0: ux; signed story displacement difference|
|CY-drift-n0-1-0-n0-1-1-uy|difference|["combination-CY-node-n0-1-1-uy", "combination-CY-node-n0-1-0-uy"]|m|n0-1-1 minus n0-1-0: uy; signed story displacement difference|
|CY-drift-n1-0-0-n1-0-1-ux|difference|["combination-CY-node-n1-0-1-ux", "combination-CY-node-n1-0-0-ux"]|m|n1-0-1 minus n1-0-0: ux; signed story displacement difference|
|CY-drift-n1-0-0-n1-0-1-uy|difference|["combination-CY-node-n1-0-1-uy", "combination-CY-node-n1-0-0-uy"]|m|n1-0-1 minus n1-0-0: uy; signed story displacement difference|
|CY-drift-n1-1-0-n1-1-1-ux|difference|["combination-CY-node-n1-1-1-ux", "combination-CY-node-n1-1-0-ux"]|m|n1-1-1 minus n1-1-0: ux; signed story displacement difference|
|CY-drift-n1-1-0-n1-1-1-uy|difference|["combination-CY-node-n1-1-1-uy", "combination-CY-node-n1-1-0-uy"]|m|n1-1-1 minus n1-1-0: uy; signed story displacement difference|
|CY-drift-n2-0-0-n2-0-1-ux|difference|["combination-CY-node-n2-0-1-ux", "combination-CY-node-n2-0-0-ux"]|m|n2-0-1 minus n2-0-0: ux; signed story displacement difference|
|CY-drift-n2-0-0-n2-0-1-uy|difference|["combination-CY-node-n2-0-1-uy", "combination-CY-node-n2-0-0-uy"]|m|n2-0-1 minus n2-0-0: uy; signed story displacement difference|
|CY-drift-n2-1-0-n2-1-1-ux|difference|["combination-CY-node-n2-1-1-ux", "combination-CY-node-n2-1-0-ux"]|m|n2-1-1 minus n2-1-0: ux; signed story displacement difference|
|CY-drift-n2-1-0-n2-1-1-uy|difference|["combination-CY-node-n2-1-1-uy", "combination-CY-node-n2-1-0-uy"]|m|n2-1-1 minus n2-1-0: uy; signed story displacement difference|
|CY-drift-n0-0-1-n0-0-2-ux|difference|["combination-CY-node-n0-0-2-ux", "combination-CY-node-n0-0-1-ux"]|m|n0-0-2 minus n0-0-1: ux; signed story displacement difference|
|CY-drift-n0-0-1-n0-0-2-uy|difference|["combination-CY-node-n0-0-2-uy", "combination-CY-node-n0-0-1-uy"]|m|n0-0-2 minus n0-0-1: uy; signed story displacement difference|
|CY-drift-n0-1-1-n0-1-2-ux|difference|["combination-CY-node-n0-1-2-ux", "combination-CY-node-n0-1-1-ux"]|m|n0-1-2 minus n0-1-1: ux; signed story displacement difference|
|CY-drift-n0-1-1-n0-1-2-uy|difference|["combination-CY-node-n0-1-2-uy", "combination-CY-node-n0-1-1-uy"]|m|n0-1-2 minus n0-1-1: uy; signed story displacement difference|
|CY-drift-n1-0-1-n1-0-2-ux|difference|["combination-CY-node-n1-0-2-ux", "combination-CY-node-n1-0-1-ux"]|m|n1-0-2 minus n1-0-1: ux; signed story displacement difference|
|CY-drift-n1-0-1-n1-0-2-uy|difference|["combination-CY-node-n1-0-2-uy", "combination-CY-node-n1-0-1-uy"]|m|n1-0-2 minus n1-0-1: uy; signed story displacement difference|
|CY-drift-n1-1-1-n1-1-2-ux|difference|["combination-CY-node-n1-1-2-ux", "combination-CY-node-n1-1-1-ux"]|m|n1-1-2 minus n1-1-1: ux; signed story displacement difference|
|CY-drift-n1-1-1-n1-1-2-uy|difference|["combination-CY-node-n1-1-2-uy", "combination-CY-node-n1-1-1-uy"]|m|n1-1-2 minus n1-1-1: uy; signed story displacement difference|
|CY-drift-n2-0-1-n2-0-2-ux|difference|["combination-CY-node-n2-0-2-ux", "combination-CY-node-n2-0-1-ux"]|m|n2-0-2 minus n2-0-1: ux; signed story displacement difference|
|CY-drift-n2-0-1-n2-0-2-uy|difference|["combination-CY-node-n2-0-2-uy", "combination-CY-node-n2-0-1-uy"]|m|n2-0-2 minus n2-0-1: uy; signed story displacement difference|
|CY-drift-n2-1-1-n2-1-2-ux|difference|["combination-CY-node-n2-1-2-ux", "combination-CY-node-n2-1-1-ux"]|m|n2-1-2 minus n2-1-1: ux; signed story displacement difference|
|CY-drift-n2-1-1-n2-1-2-uy|difference|["combination-CY-node-n2-1-2-uy", "combination-CY-node-n2-1-1-uy"]|m|n2-1-2 minus n2-1-1: uy; signed story displacement difference|
|governing-n0-0-1-ux|max_abs|["combination-C0-node-n0-0-1-ux", "combination-CX-node-n0-0-1-ux", "combination-CY-node-n0-0-1-ux"]|m|Governing signed ux at n0-0-1; retain combination|
|governing-n0-0-1-uy|max_abs|["combination-C0-node-n0-0-1-uy", "combination-CX-node-n0-0-1-uy", "combination-CY-node-n0-0-1-uy"]|m|Governing signed uy at n0-0-1; retain combination|
|governing-n0-0-1-uz|max_abs|["combination-C0-node-n0-0-1-uz", "combination-CX-node-n0-0-1-uz", "combination-CY-node-n0-0-1-uz"]|m|Governing signed uz at n0-0-1; retain combination|
|governing-n0-0-0-ux|max_abs|["combination-C0-node-n0-0-0-ux", "combination-CX-node-n0-0-0-ux", "combination-CY-node-n0-0-0-ux"]|m|Governing signed ux at n0-0-0; retain combination|
|governing-n0-0-0-uy|max_abs|["combination-C0-node-n0-0-0-uy", "combination-CX-node-n0-0-0-uy", "combination-CY-node-n0-0-0-uy"]|m|Governing signed uy at n0-0-0; retain combination|
|governing-n0-1-1-ux|max_abs|["combination-C0-node-n0-1-1-ux", "combination-CX-node-n0-1-1-ux", "combination-CY-node-n0-1-1-ux"]|m|Governing signed ux at n0-1-1; retain combination|
|governing-n0-1-1-uy|max_abs|["combination-C0-node-n0-1-1-uy", "combination-CX-node-n0-1-1-uy", "combination-CY-node-n0-1-1-uy"]|m|Governing signed uy at n0-1-1; retain combination|
|governing-n0-1-1-uz|max_abs|["combination-C0-node-n0-1-1-uz", "combination-CX-node-n0-1-1-uz", "combination-CY-node-n0-1-1-uz"]|m|Governing signed uz at n0-1-1; retain combination|
|governing-n0-1-0-ux|max_abs|["combination-C0-node-n0-1-0-ux", "combination-CX-node-n0-1-0-ux", "combination-CY-node-n0-1-0-ux"]|m|Governing signed ux at n0-1-0; retain combination|
|governing-n0-1-0-uy|max_abs|["combination-C0-node-n0-1-0-uy", "combination-CX-node-n0-1-0-uy", "combination-CY-node-n0-1-0-uy"]|m|Governing signed uy at n0-1-0; retain combination|
|governing-n1-0-1-ux|max_abs|["combination-C0-node-n1-0-1-ux", "combination-CX-node-n1-0-1-ux", "combination-CY-node-n1-0-1-ux"]|m|Governing signed ux at n1-0-1; retain combination|
|governing-n1-0-1-uy|max_abs|["combination-C0-node-n1-0-1-uy", "combination-CX-node-n1-0-1-uy", "combination-CY-node-n1-0-1-uy"]|m|Governing signed uy at n1-0-1; retain combination|
|governing-n1-0-1-uz|max_abs|["combination-C0-node-n1-0-1-uz", "combination-CX-node-n1-0-1-uz", "combination-CY-node-n1-0-1-uz"]|m|Governing signed uz at n1-0-1; retain combination|
|governing-n1-0-0-ux|max_abs|["combination-C0-node-n1-0-0-ux", "combination-CX-node-n1-0-0-ux", "combination-CY-node-n1-0-0-ux"]|m|Governing signed ux at n1-0-0; retain combination|
|governing-n1-0-0-uy|max_abs|["combination-C0-node-n1-0-0-uy", "combination-CX-node-n1-0-0-uy", "combination-CY-node-n1-0-0-uy"]|m|Governing signed uy at n1-0-0; retain combination|
|governing-n1-1-1-ux|max_abs|["combination-C0-node-n1-1-1-ux", "combination-CX-node-n1-1-1-ux", "combination-CY-node-n1-1-1-ux"]|m|Governing signed ux at n1-1-1; retain combination|
|governing-n1-1-1-uy|max_abs|["combination-C0-node-n1-1-1-uy", "combination-CX-node-n1-1-1-uy", "combination-CY-node-n1-1-1-uy"]|m|Governing signed uy at n1-1-1; retain combination|
|governing-n1-1-1-uz|max_abs|["combination-C0-node-n1-1-1-uz", "combination-CX-node-n1-1-1-uz", "combination-CY-node-n1-1-1-uz"]|m|Governing signed uz at n1-1-1; retain combination|
|governing-n1-1-0-ux|max_abs|["combination-C0-node-n1-1-0-ux", "combination-CX-node-n1-1-0-ux", "combination-CY-node-n1-1-0-ux"]|m|Governing signed ux at n1-1-0; retain combination|
|governing-n1-1-0-uy|max_abs|["combination-C0-node-n1-1-0-uy", "combination-CX-node-n1-1-0-uy", "combination-CY-node-n1-1-0-uy"]|m|Governing signed uy at n1-1-0; retain combination|
|governing-n2-0-1-ux|max_abs|["combination-C0-node-n2-0-1-ux", "combination-CX-node-n2-0-1-ux", "combination-CY-node-n2-0-1-ux"]|m|Governing signed ux at n2-0-1; retain combination|
|governing-n2-0-1-uy|max_abs|["combination-C0-node-n2-0-1-uy", "combination-CX-node-n2-0-1-uy", "combination-CY-node-n2-0-1-uy"]|m|Governing signed uy at n2-0-1; retain combination|
|governing-n2-0-1-uz|max_abs|["combination-C0-node-n2-0-1-uz", "combination-CX-node-n2-0-1-uz", "combination-CY-node-n2-0-1-uz"]|m|Governing signed uz at n2-0-1; retain combination|
|governing-n2-0-0-ux|max_abs|["combination-C0-node-n2-0-0-ux", "combination-CX-node-n2-0-0-ux", "combination-CY-node-n2-0-0-ux"]|m|Governing signed ux at n2-0-0; retain combination|
|governing-n2-0-0-uy|max_abs|["combination-C0-node-n2-0-0-uy", "combination-CX-node-n2-0-0-uy", "combination-CY-node-n2-0-0-uy"]|m|Governing signed uy at n2-0-0; retain combination|
|governing-n2-1-1-ux|max_abs|["combination-C0-node-n2-1-1-ux", "combination-CX-node-n2-1-1-ux", "combination-CY-node-n2-1-1-ux"]|m|Governing signed ux at n2-1-1; retain combination|
|governing-n2-1-1-uy|max_abs|["combination-C0-node-n2-1-1-uy", "combination-CX-node-n2-1-1-uy", "combination-CY-node-n2-1-1-uy"]|m|Governing signed uy at n2-1-1; retain combination|
|governing-n2-1-1-uz|max_abs|["combination-C0-node-n2-1-1-uz", "combination-CX-node-n2-1-1-uz", "combination-CY-node-n2-1-1-uz"]|m|Governing signed uz at n2-1-1; retain combination|
|governing-n2-1-0-ux|max_abs|["combination-C0-node-n2-1-0-ux", "combination-CX-node-n2-1-0-ux", "combination-CY-node-n2-1-0-ux"]|m|Governing signed ux at n2-1-0; retain combination|
|governing-n2-1-0-uy|max_abs|["combination-C0-node-n2-1-0-uy", "combination-CX-node-n2-1-0-uy", "combination-CY-node-n2-1-0-uy"]|m|Governing signed uy at n2-1-0; retain combination|
|governing-n0-0-2-ux|max_abs|["combination-C0-node-n0-0-2-ux", "combination-CX-node-n0-0-2-ux", "combination-CY-node-n0-0-2-ux"]|m|Governing signed ux at n0-0-2; retain combination|
|governing-n0-0-2-uy|max_abs|["combination-C0-node-n0-0-2-uy", "combination-CX-node-n0-0-2-uy", "combination-CY-node-n0-0-2-uy"]|m|Governing signed uy at n0-0-2; retain combination|
|governing-n0-0-2-uz|max_abs|["combination-C0-node-n0-0-2-uz", "combination-CX-node-n0-0-2-uz", "combination-CY-node-n0-0-2-uz"]|m|Governing signed uz at n0-0-2; retain combination|
|governing-n0-1-2-ux|max_abs|["combination-C0-node-n0-1-2-ux", "combination-CX-node-n0-1-2-ux", "combination-CY-node-n0-1-2-ux"]|m|Governing signed ux at n0-1-2; retain combination|
|governing-n0-1-2-uy|max_abs|["combination-C0-node-n0-1-2-uy", "combination-CX-node-n0-1-2-uy", "combination-CY-node-n0-1-2-uy"]|m|Governing signed uy at n0-1-2; retain combination|
|governing-n0-1-2-uz|max_abs|["combination-C0-node-n0-1-2-uz", "combination-CX-node-n0-1-2-uz", "combination-CY-node-n0-1-2-uz"]|m|Governing signed uz at n0-1-2; retain combination|
|governing-n1-0-2-ux|max_abs|["combination-C0-node-n1-0-2-ux", "combination-CX-node-n1-0-2-ux", "combination-CY-node-n1-0-2-ux"]|m|Governing signed ux at n1-0-2; retain combination|
|governing-n1-0-2-uy|max_abs|["combination-C0-node-n1-0-2-uy", "combination-CX-node-n1-0-2-uy", "combination-CY-node-n1-0-2-uy"]|m|Governing signed uy at n1-0-2; retain combination|
|governing-n1-0-2-uz|max_abs|["combination-C0-node-n1-0-2-uz", "combination-CX-node-n1-0-2-uz", "combination-CY-node-n1-0-2-uz"]|m|Governing signed uz at n1-0-2; retain combination|
|governing-n1-1-2-ux|max_abs|["combination-C0-node-n1-1-2-ux", "combination-CX-node-n1-1-2-ux", "combination-CY-node-n1-1-2-ux"]|m|Governing signed ux at n1-1-2; retain combination|
|governing-n1-1-2-uy|max_abs|["combination-C0-node-n1-1-2-uy", "combination-CX-node-n1-1-2-uy", "combination-CY-node-n1-1-2-uy"]|m|Governing signed uy at n1-1-2; retain combination|
|governing-n1-1-2-uz|max_abs|["combination-C0-node-n1-1-2-uz", "combination-CX-node-n1-1-2-uz", "combination-CY-node-n1-1-2-uz"]|m|Governing signed uz at n1-1-2; retain combination|
|governing-n2-0-2-ux|max_abs|["combination-C0-node-n2-0-2-ux", "combination-CX-node-n2-0-2-ux", "combination-CY-node-n2-0-2-ux"]|m|Governing signed ux at n2-0-2; retain combination|
|governing-n2-0-2-uy|max_abs|["combination-C0-node-n2-0-2-uy", "combination-CX-node-n2-0-2-uy", "combination-CY-node-n2-0-2-uy"]|m|Governing signed uy at n2-0-2; retain combination|
|governing-n2-0-2-uz|max_abs|["combination-C0-node-n2-0-2-uz", "combination-CX-node-n2-0-2-uz", "combination-CY-node-n2-0-2-uz"]|m|Governing signed uz at n2-0-2; retain combination|
|governing-n2-1-2-ux|max_abs|["combination-C0-node-n2-1-2-ux", "combination-CX-node-n2-1-2-ux", "combination-CY-node-n2-1-2-ux"]|m|Governing signed ux at n2-1-2; retain combination|
|governing-n2-1-2-uy|max_abs|["combination-C0-node-n2-1-2-uy", "combination-CX-node-n2-1-2-uy", "combination-CY-node-n2-1-2-uy"]|m|Governing signed uy at n2-1-2; retain combination|
|governing-n2-1-2-uz|max_abs|["combination-C0-node-n2-1-2-uz", "combination-CX-node-n2-1-2-uz", "combination-CY-node-n2-1-2-uz"]|m|Governing signed uz at n2-1-2; retain combination|
|governing-n0-0-0-Fx|max_abs|["combination-C0-node-n0-0-0-Fx", "combination-CX-node-n0-0-0-Fx", "combination-CY-node-n0-0-0-Fx"]|kN|Governing signed Fx at n0-0-0; retain combination|
|governing-n0-0-0-Fy|max_abs|["combination-C0-node-n0-0-0-Fy", "combination-CX-node-n0-0-0-Fy", "combination-CY-node-n0-0-0-Fy"]|kN|Governing signed Fy at n0-0-0; retain combination|
|governing-n0-0-0-Fz|max_abs|["combination-C0-node-n0-0-0-Fz", "combination-CX-node-n0-0-0-Fz", "combination-CY-node-n0-0-0-Fz"]|kN|Governing signed Fz at n0-0-0; retain combination|
|governing-n0-0-0-Mx|max_abs|["combination-C0-node-n0-0-0-Mx", "combination-CX-node-n0-0-0-Mx", "combination-CY-node-n0-0-0-Mx"]|kN.m|Governing signed Mx at n0-0-0; retain combination|
|governing-n0-0-0-My|max_abs|["combination-C0-node-n0-0-0-My", "combination-CX-node-n0-0-0-My", "combination-CY-node-n0-0-0-My"]|kN.m|Governing signed My at n0-0-0; retain combination|
|governing-n0-0-0-Mz|max_abs|["combination-C0-node-n0-0-0-Mz", "combination-CX-node-n0-0-0-Mz", "combination-CY-node-n0-0-0-Mz"]|kN.m|Governing signed Mz at n0-0-0; retain combination|
|governing-n0-1-0-Fx|max_abs|["combination-C0-node-n0-1-0-Fx", "combination-CX-node-n0-1-0-Fx", "combination-CY-node-n0-1-0-Fx"]|kN|Governing signed Fx at n0-1-0; retain combination|
|governing-n0-1-0-Fy|max_abs|["combination-C0-node-n0-1-0-Fy", "combination-CX-node-n0-1-0-Fy", "combination-CY-node-n0-1-0-Fy"]|kN|Governing signed Fy at n0-1-0; retain combination|
|governing-n0-1-0-Fz|max_abs|["combination-C0-node-n0-1-0-Fz", "combination-CX-node-n0-1-0-Fz", "combination-CY-node-n0-1-0-Fz"]|kN|Governing signed Fz at n0-1-0; retain combination|
|governing-n0-1-0-Mx|max_abs|["combination-C0-node-n0-1-0-Mx", "combination-CX-node-n0-1-0-Mx", "combination-CY-node-n0-1-0-Mx"]|kN.m|Governing signed Mx at n0-1-0; retain combination|
|governing-n0-1-0-My|max_abs|["combination-C0-node-n0-1-0-My", "combination-CX-node-n0-1-0-My", "combination-CY-node-n0-1-0-My"]|kN.m|Governing signed My at n0-1-0; retain combination|
|governing-n0-1-0-Mz|max_abs|["combination-C0-node-n0-1-0-Mz", "combination-CX-node-n0-1-0-Mz", "combination-CY-node-n0-1-0-Mz"]|kN.m|Governing signed Mz at n0-1-0; retain combination|
|governing-n1-0-0-Fx|max_abs|["combination-C0-node-n1-0-0-Fx", "combination-CX-node-n1-0-0-Fx", "combination-CY-node-n1-0-0-Fx"]|kN|Governing signed Fx at n1-0-0; retain combination|
|governing-n1-0-0-Fy|max_abs|["combination-C0-node-n1-0-0-Fy", "combination-CX-node-n1-0-0-Fy", "combination-CY-node-n1-0-0-Fy"]|kN|Governing signed Fy at n1-0-0; retain combination|
|governing-n1-0-0-Fz|max_abs|["combination-C0-node-n1-0-0-Fz", "combination-CX-node-n1-0-0-Fz", "combination-CY-node-n1-0-0-Fz"]|kN|Governing signed Fz at n1-0-0; retain combination|
|governing-n1-0-0-Mx|max_abs|["combination-C0-node-n1-0-0-Mx", "combination-CX-node-n1-0-0-Mx", "combination-CY-node-n1-0-0-Mx"]|kN.m|Governing signed Mx at n1-0-0; retain combination|
|governing-n1-0-0-My|max_abs|["combination-C0-node-n1-0-0-My", "combination-CX-node-n1-0-0-My", "combination-CY-node-n1-0-0-My"]|kN.m|Governing signed My at n1-0-0; retain combination|
|governing-n1-0-0-Mz|max_abs|["combination-C0-node-n1-0-0-Mz", "combination-CX-node-n1-0-0-Mz", "combination-CY-node-n1-0-0-Mz"]|kN.m|Governing signed Mz at n1-0-0; retain combination|
|governing-n1-1-0-Fx|max_abs|["combination-C0-node-n1-1-0-Fx", "combination-CX-node-n1-1-0-Fx", "combination-CY-node-n1-1-0-Fx"]|kN|Governing signed Fx at n1-1-0; retain combination|
|governing-n1-1-0-Fy|max_abs|["combination-C0-node-n1-1-0-Fy", "combination-CX-node-n1-1-0-Fy", "combination-CY-node-n1-1-0-Fy"]|kN|Governing signed Fy at n1-1-0; retain combination|
|governing-n1-1-0-Fz|max_abs|["combination-C0-node-n1-1-0-Fz", "combination-CX-node-n1-1-0-Fz", "combination-CY-node-n1-1-0-Fz"]|kN|Governing signed Fz at n1-1-0; retain combination|
|governing-n1-1-0-Mx|max_abs|["combination-C0-node-n1-1-0-Mx", "combination-CX-node-n1-1-0-Mx", "combination-CY-node-n1-1-0-Mx"]|kN.m|Governing signed Mx at n1-1-0; retain combination|
|governing-n1-1-0-My|max_abs|["combination-C0-node-n1-1-0-My", "combination-CX-node-n1-1-0-My", "combination-CY-node-n1-1-0-My"]|kN.m|Governing signed My at n1-1-0; retain combination|
|governing-n1-1-0-Mz|max_abs|["combination-C0-node-n1-1-0-Mz", "combination-CX-node-n1-1-0-Mz", "combination-CY-node-n1-1-0-Mz"]|kN.m|Governing signed Mz at n1-1-0; retain combination|
|governing-n2-0-0-Fx|max_abs|["combination-C0-node-n2-0-0-Fx", "combination-CX-node-n2-0-0-Fx", "combination-CY-node-n2-0-0-Fx"]|kN|Governing signed Fx at n2-0-0; retain combination|
|governing-n2-0-0-Fy|max_abs|["combination-C0-node-n2-0-0-Fy", "combination-CX-node-n2-0-0-Fy", "combination-CY-node-n2-0-0-Fy"]|kN|Governing signed Fy at n2-0-0; retain combination|
|governing-n2-0-0-Fz|max_abs|["combination-C0-node-n2-0-0-Fz", "combination-CX-node-n2-0-0-Fz", "combination-CY-node-n2-0-0-Fz"]|kN|Governing signed Fz at n2-0-0; retain combination|
|governing-n2-0-0-Mx|max_abs|["combination-C0-node-n2-0-0-Mx", "combination-CX-node-n2-0-0-Mx", "combination-CY-node-n2-0-0-Mx"]|kN.m|Governing signed Mx at n2-0-0; retain combination|
|governing-n2-0-0-My|max_abs|["combination-C0-node-n2-0-0-My", "combination-CX-node-n2-0-0-My", "combination-CY-node-n2-0-0-My"]|kN.m|Governing signed My at n2-0-0; retain combination|
|governing-n2-0-0-Mz|max_abs|["combination-C0-node-n2-0-0-Mz", "combination-CX-node-n2-0-0-Mz", "combination-CY-node-n2-0-0-Mz"]|kN.m|Governing signed Mz at n2-0-0; retain combination|
|governing-n2-1-0-Fx|max_abs|["combination-C0-node-n2-1-0-Fx", "combination-CX-node-n2-1-0-Fx", "combination-CY-node-n2-1-0-Fx"]|kN|Governing signed Fx at n2-1-0; retain combination|
|governing-n2-1-0-Fy|max_abs|["combination-C0-node-n2-1-0-Fy", "combination-CX-node-n2-1-0-Fy", "combination-CY-node-n2-1-0-Fy"]|kN|Governing signed Fy at n2-1-0; retain combination|
|governing-n2-1-0-Fz|max_abs|["combination-C0-node-n2-1-0-Fz", "combination-CX-node-n2-1-0-Fz", "combination-CY-node-n2-1-0-Fz"]|kN|Governing signed Fz at n2-1-0; retain combination|
|governing-n2-1-0-Mx|max_abs|["combination-C0-node-n2-1-0-Mx", "combination-CX-node-n2-1-0-Mx", "combination-CY-node-n2-1-0-Mx"]|kN.m|Governing signed Mx at n2-1-0; retain combination|
|governing-n2-1-0-My|max_abs|["combination-C0-node-n2-1-0-My", "combination-CX-node-n2-1-0-My", "combination-CY-node-n2-1-0-My"]|kN.m|Governing signed My at n2-1-0; retain combination|
|governing-n2-1-0-Mz|max_abs|["combination-C0-node-n2-1-0-Mz", "combination-CX-node-n2-1-0-Mz", "combination-CY-node-n2-1-0-Mz"]|kN.m|Governing signed Mz at n2-1-0; retain combination|
|governing-drift-n0-0-0-n0-0-1-ux|max_abs|["C0-drift-n0-0-0-n0-0-1-ux", "CX-drift-n0-0-0-n0-0-1-ux", "CY-drift-n0-0-0-n0-0-1-ux"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n0-0-0-n0-0-1-uy|max_abs|["C0-drift-n0-0-0-n0-0-1-uy", "CX-drift-n0-0-0-n0-0-1-uy", "CY-drift-n0-0-0-n0-0-1-uy"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n0-1-0-n0-1-1-ux|max_abs|["C0-drift-n0-1-0-n0-1-1-ux", "CX-drift-n0-1-0-n0-1-1-ux", "CY-drift-n0-1-0-n0-1-1-ux"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n0-1-0-n0-1-1-uy|max_abs|["C0-drift-n0-1-0-n0-1-1-uy", "CX-drift-n0-1-0-n0-1-1-uy", "CY-drift-n0-1-0-n0-1-1-uy"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n1-0-0-n1-0-1-ux|max_abs|["C0-drift-n1-0-0-n1-0-1-ux", "CX-drift-n1-0-0-n1-0-1-ux", "CY-drift-n1-0-0-n1-0-1-ux"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n1-0-0-n1-0-1-uy|max_abs|["C0-drift-n1-0-0-n1-0-1-uy", "CX-drift-n1-0-0-n1-0-1-uy", "CY-drift-n1-0-0-n1-0-1-uy"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n1-1-0-n1-1-1-ux|max_abs|["C0-drift-n1-1-0-n1-1-1-ux", "CX-drift-n1-1-0-n1-1-1-ux", "CY-drift-n1-1-0-n1-1-1-ux"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n1-1-0-n1-1-1-uy|max_abs|["C0-drift-n1-1-0-n1-1-1-uy", "CX-drift-n1-1-0-n1-1-1-uy", "CY-drift-n1-1-0-n1-1-1-uy"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n2-0-0-n2-0-1-ux|max_abs|["C0-drift-n2-0-0-n2-0-1-ux", "CX-drift-n2-0-0-n2-0-1-ux", "CY-drift-n2-0-0-n2-0-1-ux"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n2-0-0-n2-0-1-uy|max_abs|["C0-drift-n2-0-0-n2-0-1-uy", "CX-drift-n2-0-0-n2-0-1-uy", "CY-drift-n2-0-0-n2-0-1-uy"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n2-1-0-n2-1-1-ux|max_abs|["C0-drift-n2-1-0-n2-1-1-ux", "CX-drift-n2-1-0-n2-1-1-ux", "CY-drift-n2-1-0-n2-1-1-ux"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n2-1-0-n2-1-1-uy|max_abs|["C0-drift-n2-1-0-n2-1-1-uy", "CX-drift-n2-1-0-n2-1-1-uy", "CY-drift-n2-1-0-n2-1-1-uy"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n0-0-1-n0-0-2-ux|max_abs|["C0-drift-n0-0-1-n0-0-2-ux", "CX-drift-n0-0-1-n0-0-2-ux", "CY-drift-n0-0-1-n0-0-2-ux"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n0-0-1-n0-0-2-uy|max_abs|["C0-drift-n0-0-1-n0-0-2-uy", "CX-drift-n0-0-1-n0-0-2-uy", "CY-drift-n0-0-1-n0-0-2-uy"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n0-1-1-n0-1-2-ux|max_abs|["C0-drift-n0-1-1-n0-1-2-ux", "CX-drift-n0-1-1-n0-1-2-ux", "CY-drift-n0-1-1-n0-1-2-ux"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n0-1-1-n0-1-2-uy|max_abs|["C0-drift-n0-1-1-n0-1-2-uy", "CX-drift-n0-1-1-n0-1-2-uy", "CY-drift-n0-1-1-n0-1-2-uy"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n1-0-1-n1-0-2-ux|max_abs|["C0-drift-n1-0-1-n1-0-2-ux", "CX-drift-n1-0-1-n1-0-2-ux", "CY-drift-n1-0-1-n1-0-2-ux"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n1-0-1-n1-0-2-uy|max_abs|["C0-drift-n1-0-1-n1-0-2-uy", "CX-drift-n1-0-1-n1-0-2-uy", "CY-drift-n1-0-1-n1-0-2-uy"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n1-1-1-n1-1-2-ux|max_abs|["C0-drift-n1-1-1-n1-1-2-ux", "CX-drift-n1-1-1-n1-1-2-ux", "CY-drift-n1-1-1-n1-1-2-ux"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n1-1-1-n1-1-2-uy|max_abs|["C0-drift-n1-1-1-n1-1-2-uy", "CX-drift-n1-1-1-n1-1-2-uy", "CY-drift-n1-1-1-n1-1-2-uy"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n2-0-1-n2-0-2-ux|max_abs|["C0-drift-n2-0-1-n2-0-2-ux", "CX-drift-n2-0-1-n2-0-2-ux", "CY-drift-n2-0-1-n2-0-2-ux"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n2-0-1-n2-0-2-uy|max_abs|["C0-drift-n2-0-1-n2-0-2-uy", "CX-drift-n2-0-1-n2-0-2-uy", "CY-drift-n2-0-1-n2-0-2-uy"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n2-1-1-n2-1-2-ux|max_abs|["C0-drift-n2-1-1-n2-1-2-ux", "CX-drift-n2-1-1-n2-1-2-ux", "CY-drift-n2-1-1-n2-1-2-ux"]|m|Governing signed story displacement difference; retain combination|
|governing-drift-n2-1-1-n2-1-2-uy|max_abs|["C0-drift-n2-1-1-n2-1-2-uy", "CX-drift-n2-1-1-n2-1-2-uy", "CY-drift-n2-1-1-n2-1-2-uy"]|m|Governing signed story displacement difference; retain combination|

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Timoshenko bending (with prescribed finite shear areas). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.

## Native analysis conventions

Commercial elastic analysis convention: commercial-linear-static-v2

Use the specified native engine for first-order, small-displacement, linear
elastic static analysis with Timoshenko bending. For every beam and column,
the prescribed effective shear areas are Asy = Asz = 5*A/6, in m^2. A is the
explicit cross-sectional area in the currently available property appendix;
Asy acts for local-y shear V2 and Asz for local-z shear V3. This is a prescribed
benchmark idealization, including generalized numerical sections, rather than
an inference from a section name. Apply it to each newly supplied or edited
section. Truss/brace members retain their specified axial-only behavior.

Retain the supplied E, G, A, Iy, Iz and J, geometry, connectivity, supports,
loads and load selections. Use gross uncracked concrete stiffness where stated.
Preserve the stated local axes, member-end cut signs and units. Self-weight,
rigid floors, rigid offsets, P-Delta and construction stages remain off.

Use explicit elastic stiffness rather than silently substituting a native
material grade's defaults. A native representation using equivalent EA,
G*Asy, G*Asz, GJ, E*Iy and E*Iz must retain the supplied physical definitions
and report the actual native material/section values, modifiers and numerical
serialization differences. Equivalent elastic stiffness does not assert
identical literal material fields or qualify stress/design calculations.
Retain native input, settings, engine/version, logs and raw result evidence.
This appendix supplies analysis inputs, not computed answers or acceptance.
