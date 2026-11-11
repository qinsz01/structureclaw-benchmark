## Numerical inputs

|Field|Value|
|---|---|
|title|Complete numerical input appendix|
|linearCombinations|[]|
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
|n0-2-0|0|10|0|true|true|true|true|true|true|
|n1-0-0|6|0|0|true|true|true|true|true|true|
|n1-1-0|6|5|0|true|true|true|true|true|true|
|n1-2-0|6|10|0|true|true|true|true|true|true|
|n2-0-0|12|0|0|true|true|true|true|true|true|
|n2-1-0|12|5|0|true|true|true|true|true|true|
|n0-0-1|0|0|3.6|false|false|false|false|false|false|
|n0-1-1|0|5|3.6|false|false|false|false|false|false|
|n0-2-1|0|10|3.6|false|false|false|false|false|false|
|n1-0-1|6|0|3.6|false|false|false|false|false|false|
|n1-1-1|6|5|3.6|false|false|false|false|false|false|
|n1-2-1|6|10|3.6|false|false|false|false|false|false|
|n2-0-1|12|0|3.6|false|false|false|false|false|false|
|n2-1-1|12|5|3.6|false|false|false|false|false|false|
|n0-0-2|0|0|7.2|false|false|false|false|false|false|
|n0-1-2|0|5|7.2|false|false|false|false|false|false|
|n0-2-2|0|10|7.2|false|false|false|false|false|false|
|n1-0-2|6|0|7.2|false|false|false|false|false|false|
|n1-1-2|6|5|7.2|false|false|false|false|false|false|
|n1-2-2|6|10|7.2|false|false|false|false|false|false|
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
|y0-1-1|beam|n0-1-1|n0-2-1|M1|B2|0|[0, 0, 1]|
|c0-2-1|column|n0-2-0|n0-2-1|M1|C1|0|[1, 0, 0]|
|x0-2-1|beam|n0-2-1|n1-2-1|M1|B1|0|[0, 0, 1]|
|c1-0-1|column|n1-0-0|n1-0-1|M1|C1|0|[1, 0, 0]|
|x1-0-1|beam|n1-0-1|n2-0-1|M1|B1|0|[0, 0, 1]|
|y1-0-1|beam|n1-0-1|n1-1-1|M1|B2|0|[0, 0, 1]|
|c1-1-1|column|n1-1-0|n1-1-1|M1|C1|0|[1, 0, 0]|
|x1-1-1|beam|n1-1-1|n2-1-1|M1|B1|0|[0, 0, 1]|
|y1-1-1|beam|n1-1-1|n1-2-1|M1|B2|0|[0, 0, 1]|
|c1-2-1|column|n1-2-0|n1-2-1|M1|C1|0|[1, 0, 0]|
|c2-0-1|column|n2-0-0|n2-0-1|M1|C1|0|[1, 0, 0]|
|y2-0-1|beam|n2-0-1|n2-1-1|M1|B2|0|[0, 0, 1]|
|c2-1-1|column|n2-1-0|n2-1-1|M1|C1|0|[1, 0, 0]|
|c0-0-2|column|n0-0-1|n0-0-2|M1|C1|0|[1, 0, 0]|
|x0-0-2|beam|n0-0-2|n1-0-2|M1|B1|0|[0, 0, 1]|
|y0-0-2|beam|n0-0-2|n0-1-2|M1|B2|0|[0, 0, 1]|
|c0-1-2|column|n0-1-1|n0-1-2|M1|C1|0|[1, 0, 0]|
|x0-1-2|beam|n0-1-2|n1-1-2|M1|B1|0|[0, 0, 1]|
|y0-1-2|beam|n0-1-2|n0-2-2|M1|B2|0|[0, 0, 1]|
|c0-2-2|column|n0-2-1|n0-2-2|M1|C1|0|[1, 0, 0]|
|x0-2-2|beam|n0-2-2|n1-2-2|M1|B1|0|[0, 0, 1]|
|c1-0-2|column|n1-0-1|n1-0-2|M1|C1|0|[1, 0, 0]|
|x1-0-2|beam|n1-0-2|n2-0-2|M1|B1|0|[0, 0, 1]|
|y1-0-2|beam|n1-0-2|n1-1-2|M1|B2|0|[0, 0, 1]|
|c1-1-2|column|n1-1-1|n1-1-2|M1|C1|0|[1, 0, 0]|
|x1-1-2|beam|n1-1-2|n2-1-2|M1|B1|0|[0, 0, 1]|
|y1-1-2|beam|n1-1-2|n1-2-2|M1|B2|0|[0, 0, 1]|
|c1-2-2|column|n1-2-1|n1-2-2|M1|C1|0|[1, 0, 0]|
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
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|B2|300.0|700.0|0.21|0.008574999999999998|0.0015749999999999998|0.004603782069970844|
|C1|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-1 → x0-0-1, D-2 → y0-0-1, D-3 → x0-1-1, D-4 → y0-1-1, D-5 → x0-2-1, D-6 → x1-0-1, D-7 → y1-0-1, D-8 → x1-1-1, D-9 → y1-1-1, D-10 → y2-0-1, D-11 → x0-0-2, D-12 → y0-0-2, D-13 → x0-1-2, D-14 → y0-1-2, D-15 → x0-2-2, D-16 → x1-0-2, D-17 → y1-0-2, D-18 → x1-1-2, D-19 → y1-1-2, D-20 → y2-0-2|global|distributed|-8|

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

|id|location · id|component|unit|
|---|---|---|---|
|case-D-node-n0-0-1-ux|n0-0-1|ux|m|
|case-D-node-n0-0-1-uy|n0-0-1|uy|m|
|case-D-node-n0-0-1-uz|n0-0-1|uz|m|
|case-D-node-n0-0-0-ux|n0-0-0|ux|m|
|case-D-node-n0-0-0-uy|n0-0-0|uy|m|
|case-D-node-n0-1-1-ux|n0-1-1|ux|m|
|case-D-node-n0-1-1-uy|n0-1-1|uy|m|
|case-D-node-n0-1-1-uz|n0-1-1|uz|m|
|case-D-node-n0-1-0-ux|n0-1-0|ux|m|
|case-D-node-n0-1-0-uy|n0-1-0|uy|m|
|case-D-node-n0-2-1-ux|n0-2-1|ux|m|
|case-D-node-n0-2-1-uy|n0-2-1|uy|m|
|case-D-node-n0-2-1-uz|n0-2-1|uz|m|
|case-D-node-n0-2-0-ux|n0-2-0|ux|m|
|case-D-node-n0-2-0-uy|n0-2-0|uy|m|
|case-D-node-n1-0-1-ux|n1-0-1|ux|m|
|case-D-node-n1-0-1-uy|n1-0-1|uy|m|
|case-D-node-n1-0-1-uz|n1-0-1|uz|m|
|case-D-node-n1-0-0-ux|n1-0-0|ux|m|
|case-D-node-n1-0-0-uy|n1-0-0|uy|m|
|case-D-node-n1-1-1-ux|n1-1-1|ux|m|
|case-D-node-n1-1-1-uy|n1-1-1|uy|m|
|case-D-node-n1-1-1-uz|n1-1-1|uz|m|
|case-D-node-n1-1-0-ux|n1-1-0|ux|m|
|case-D-node-n1-1-0-uy|n1-1-0|uy|m|
|case-D-node-n1-2-1-ux|n1-2-1|ux|m|
|case-D-node-n1-2-1-uy|n1-2-1|uy|m|
|case-D-node-n1-2-1-uz|n1-2-1|uz|m|
|case-D-node-n1-2-0-ux|n1-2-0|ux|m|
|case-D-node-n1-2-0-uy|n1-2-0|uy|m|
|case-D-node-n2-0-1-ux|n2-0-1|ux|m|
|case-D-node-n2-0-1-uy|n2-0-1|uy|m|
|case-D-node-n2-0-1-uz|n2-0-1|uz|m|
|case-D-node-n2-0-0-ux|n2-0-0|ux|m|
|case-D-node-n2-0-0-uy|n2-0-0|uy|m|
|case-D-node-n2-1-1-ux|n2-1-1|ux|m|
|case-D-node-n2-1-1-uy|n2-1-1|uy|m|
|case-D-node-n2-1-1-uz|n2-1-1|uz|m|
|case-D-node-n2-1-0-ux|n2-1-0|ux|m|
|case-D-node-n2-1-0-uy|n2-1-0|uy|m|
|case-D-node-n0-0-2-ux|n0-0-2|ux|m|
|case-D-node-n0-0-2-uy|n0-0-2|uy|m|
|case-D-node-n0-0-2-uz|n0-0-2|uz|m|
|case-D-node-n0-1-2-ux|n0-1-2|ux|m|
|case-D-node-n0-1-2-uy|n0-1-2|uy|m|
|case-D-node-n0-1-2-uz|n0-1-2|uz|m|
|case-D-node-n0-2-2-ux|n0-2-2|ux|m|
|case-D-node-n0-2-2-uy|n0-2-2|uy|m|
|case-D-node-n0-2-2-uz|n0-2-2|uz|m|
|case-D-node-n1-0-2-ux|n1-0-2|ux|m|
|case-D-node-n1-0-2-uy|n1-0-2|uy|m|
|case-D-node-n1-0-2-uz|n1-0-2|uz|m|
|case-D-node-n1-1-2-ux|n1-1-2|ux|m|
|case-D-node-n1-1-2-uy|n1-1-2|uy|m|
|case-D-node-n1-1-2-uz|n1-1-2|uz|m|
|case-D-node-n1-2-2-ux|n1-2-2|ux|m|
|case-D-node-n1-2-2-uy|n1-2-2|uy|m|
|case-D-node-n1-2-2-uz|n1-2-2|uz|m|
|case-D-node-n2-0-2-ux|n2-0-2|ux|m|
|case-D-node-n2-0-2-uy|n2-0-2|uy|m|
|case-D-node-n2-0-2-uz|n2-0-2|uz|m|
|case-D-node-n2-1-2-ux|n2-1-2|ux|m|
|case-D-node-n2-1-2-uy|n2-1-2|uy|m|
|case-D-node-n2-1-2-uz|n2-1-2|uz|m|
|case-D-node-n0-0-0-Fx|n0-0-0|Fx|kN|
|case-D-node-n0-0-0-Fy|n0-0-0|Fy|kN|
|case-D-node-n0-0-0-Fz|n0-0-0|Fz|kN|
|case-D-node-n0-0-0-Mx|n0-0-0|Mx|kN.m|
|case-D-node-n0-0-0-My|n0-0-0|My|kN.m|
|case-D-node-n0-0-0-Mz|n0-0-0|Mz|kN.m|
|case-D-node-n0-1-0-Fx|n0-1-0|Fx|kN|
|case-D-node-n0-1-0-Fy|n0-1-0|Fy|kN|
|case-D-node-n0-1-0-Fz|n0-1-0|Fz|kN|
|case-D-node-n0-1-0-Mx|n0-1-0|Mx|kN.m|
|case-D-node-n0-1-0-My|n0-1-0|My|kN.m|
|case-D-node-n0-1-0-Mz|n0-1-0|Mz|kN.m|
|case-D-node-n0-2-0-Fx|n0-2-0|Fx|kN|
|case-D-node-n0-2-0-Fy|n0-2-0|Fy|kN|
|case-D-node-n0-2-0-Fz|n0-2-0|Fz|kN|
|case-D-node-n0-2-0-Mx|n0-2-0|Mx|kN.m|
|case-D-node-n0-2-0-My|n0-2-0|My|kN.m|
|case-D-node-n0-2-0-Mz|n0-2-0|Mz|kN.m|
|case-D-node-n1-0-0-Fx|n1-0-0|Fx|kN|
|case-D-node-n1-0-0-Fy|n1-0-0|Fy|kN|
|case-D-node-n1-0-0-Fz|n1-0-0|Fz|kN|
|case-D-node-n1-0-0-Mx|n1-0-0|Mx|kN.m|
|case-D-node-n1-0-0-My|n1-0-0|My|kN.m|
|case-D-node-n1-0-0-Mz|n1-0-0|Mz|kN.m|
|case-D-node-n1-1-0-Fx|n1-1-0|Fx|kN|
|case-D-node-n1-1-0-Fy|n1-1-0|Fy|kN|
|case-D-node-n1-1-0-Fz|n1-1-0|Fz|kN|
|case-D-node-n1-1-0-Mx|n1-1-0|Mx|kN.m|
|case-D-node-n1-1-0-My|n1-1-0|My|kN.m|
|case-D-node-n1-1-0-Mz|n1-1-0|Mz|kN.m|
|case-D-node-n1-2-0-Fx|n1-2-0|Fx|kN|
|case-D-node-n1-2-0-Fy|n1-2-0|Fy|kN|
|case-D-node-n1-2-0-Fz|n1-2-0|Fz|kN|
|case-D-node-n1-2-0-Mx|n1-2-0|Mx|kN.m|
|case-D-node-n1-2-0-My|n1-2-0|My|kN.m|
|case-D-node-n1-2-0-Mz|n1-2-0|Mz|kN.m|
|case-D-node-n2-0-0-Fx|n2-0-0|Fx|kN|
|case-D-node-n2-0-0-Fy|n2-0-0|Fy|kN|
|case-D-node-n2-0-0-Fz|n2-0-0|Fz|kN|
|case-D-node-n2-0-0-Mx|n2-0-0|Mx|kN.m|
|case-D-node-n2-0-0-My|n2-0-0|My|kN.m|
|case-D-node-n2-0-0-Mz|n2-0-0|Mz|kN.m|
|case-D-node-n2-1-0-Fx|n2-1-0|Fx|kN|
|case-D-node-n2-1-0-Fy|n2-1-0|Fy|kN|
|case-D-node-n2-1-0-Fz|n2-1-0|Fz|kN|
|case-D-node-n2-1-0-Mx|n2-1-0|Mx|kN.m|
|case-D-node-n2-1-0-My|n2-1-0|My|kN.m|
|case-D-node-n2-1-0-Mz|n2-1-0|Mz|kN.m|

Applies to every listed row: selection · kind = case; selection · id = D; location · kind = node.

## Requested outputs — Derived

|id|operands|description|
|---|---|---|
|D-drift-n0-0-0-n0-0-1-ux|["case-D-node-n0-0-1-ux", "case-D-node-n0-0-0-ux"]|n0-0-1 minus n0-0-0: ux; signed story displacement difference|
|D-drift-n0-0-0-n0-0-1-uy|["case-D-node-n0-0-1-uy", "case-D-node-n0-0-0-uy"]|n0-0-1 minus n0-0-0: uy; signed story displacement difference|
|D-drift-n0-1-0-n0-1-1-ux|["case-D-node-n0-1-1-ux", "case-D-node-n0-1-0-ux"]|n0-1-1 minus n0-1-0: ux; signed story displacement difference|
|D-drift-n0-1-0-n0-1-1-uy|["case-D-node-n0-1-1-uy", "case-D-node-n0-1-0-uy"]|n0-1-1 minus n0-1-0: uy; signed story displacement difference|
|D-drift-n0-2-0-n0-2-1-ux|["case-D-node-n0-2-1-ux", "case-D-node-n0-2-0-ux"]|n0-2-1 minus n0-2-0: ux; signed story displacement difference|
|D-drift-n0-2-0-n0-2-1-uy|["case-D-node-n0-2-1-uy", "case-D-node-n0-2-0-uy"]|n0-2-1 minus n0-2-0: uy; signed story displacement difference|
|D-drift-n1-0-0-n1-0-1-ux|["case-D-node-n1-0-1-ux", "case-D-node-n1-0-0-ux"]|n1-0-1 minus n1-0-0: ux; signed story displacement difference|
|D-drift-n1-0-0-n1-0-1-uy|["case-D-node-n1-0-1-uy", "case-D-node-n1-0-0-uy"]|n1-0-1 minus n1-0-0: uy; signed story displacement difference|
|D-drift-n1-1-0-n1-1-1-ux|["case-D-node-n1-1-1-ux", "case-D-node-n1-1-0-ux"]|n1-1-1 minus n1-1-0: ux; signed story displacement difference|
|D-drift-n1-1-0-n1-1-1-uy|["case-D-node-n1-1-1-uy", "case-D-node-n1-1-0-uy"]|n1-1-1 minus n1-1-0: uy; signed story displacement difference|
|D-drift-n1-2-0-n1-2-1-ux|["case-D-node-n1-2-1-ux", "case-D-node-n1-2-0-ux"]|n1-2-1 minus n1-2-0: ux; signed story displacement difference|
|D-drift-n1-2-0-n1-2-1-uy|["case-D-node-n1-2-1-uy", "case-D-node-n1-2-0-uy"]|n1-2-1 minus n1-2-0: uy; signed story displacement difference|
|D-drift-n2-0-0-n2-0-1-ux|["case-D-node-n2-0-1-ux", "case-D-node-n2-0-0-ux"]|n2-0-1 minus n2-0-0: ux; signed story displacement difference|
|D-drift-n2-0-0-n2-0-1-uy|["case-D-node-n2-0-1-uy", "case-D-node-n2-0-0-uy"]|n2-0-1 minus n2-0-0: uy; signed story displacement difference|
|D-drift-n2-1-0-n2-1-1-ux|["case-D-node-n2-1-1-ux", "case-D-node-n2-1-0-ux"]|n2-1-1 minus n2-1-0: ux; signed story displacement difference|
|D-drift-n2-1-0-n2-1-1-uy|["case-D-node-n2-1-1-uy", "case-D-node-n2-1-0-uy"]|n2-1-1 minus n2-1-0: uy; signed story displacement difference|
|D-drift-n0-0-1-n0-0-2-ux|["case-D-node-n0-0-2-ux", "case-D-node-n0-0-1-ux"]|n0-0-2 minus n0-0-1: ux; signed story displacement difference|
|D-drift-n0-0-1-n0-0-2-uy|["case-D-node-n0-0-2-uy", "case-D-node-n0-0-1-uy"]|n0-0-2 minus n0-0-1: uy; signed story displacement difference|
|D-drift-n0-1-1-n0-1-2-ux|["case-D-node-n0-1-2-ux", "case-D-node-n0-1-1-ux"]|n0-1-2 minus n0-1-1: ux; signed story displacement difference|
|D-drift-n0-1-1-n0-1-2-uy|["case-D-node-n0-1-2-uy", "case-D-node-n0-1-1-uy"]|n0-1-2 minus n0-1-1: uy; signed story displacement difference|
|D-drift-n0-2-1-n0-2-2-ux|["case-D-node-n0-2-2-ux", "case-D-node-n0-2-1-ux"]|n0-2-2 minus n0-2-1: ux; signed story displacement difference|
|D-drift-n0-2-1-n0-2-2-uy|["case-D-node-n0-2-2-uy", "case-D-node-n0-2-1-uy"]|n0-2-2 minus n0-2-1: uy; signed story displacement difference|
|D-drift-n1-0-1-n1-0-2-ux|["case-D-node-n1-0-2-ux", "case-D-node-n1-0-1-ux"]|n1-0-2 minus n1-0-1: ux; signed story displacement difference|
|D-drift-n1-0-1-n1-0-2-uy|["case-D-node-n1-0-2-uy", "case-D-node-n1-0-1-uy"]|n1-0-2 minus n1-0-1: uy; signed story displacement difference|
|D-drift-n1-1-1-n1-1-2-ux|["case-D-node-n1-1-2-ux", "case-D-node-n1-1-1-ux"]|n1-1-2 minus n1-1-1: ux; signed story displacement difference|
|D-drift-n1-1-1-n1-1-2-uy|["case-D-node-n1-1-2-uy", "case-D-node-n1-1-1-uy"]|n1-1-2 minus n1-1-1: uy; signed story displacement difference|
|D-drift-n1-2-1-n1-2-2-ux|["case-D-node-n1-2-2-ux", "case-D-node-n1-2-1-ux"]|n1-2-2 minus n1-2-1: ux; signed story displacement difference|
|D-drift-n1-2-1-n1-2-2-uy|["case-D-node-n1-2-2-uy", "case-D-node-n1-2-1-uy"]|n1-2-2 minus n1-2-1: uy; signed story displacement difference|
|D-drift-n2-0-1-n2-0-2-ux|["case-D-node-n2-0-2-ux", "case-D-node-n2-0-1-ux"]|n2-0-2 minus n2-0-1: ux; signed story displacement difference|
|D-drift-n2-0-1-n2-0-2-uy|["case-D-node-n2-0-2-uy", "case-D-node-n2-0-1-uy"]|n2-0-2 minus n2-0-1: uy; signed story displacement difference|
|D-drift-n2-1-1-n2-1-2-ux|["case-D-node-n2-1-2-ux", "case-D-node-n2-1-1-ux"]|n2-1-2 minus n2-1-1: ux; signed story displacement difference|
|D-drift-n2-1-1-n2-1-2-uy|["case-D-node-n2-1-2-uy", "case-D-node-n2-1-1-uy"]|n2-1-2 minus n2-1-1: uy; signed story displacement difference|

Applies to every listed row: operation = difference; unit = m.

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
