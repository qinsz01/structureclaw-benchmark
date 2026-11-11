## Numerical inputs

|Field|Value|
|---|---|
|title|完整数值输入附表|
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
|n1-0-0|6|0|0|true|true|true|true|true|true|
|n1-1-0|6|5|0|true|true|true|true|true|true|
|n0-0-1|0|0|3.6|false|false|false|false|false|false|
|n0-1-1|0|5|3.6|false|false|false|false|false|false|
|n1-0-1|6|0|3.6|false|false|false|false|false|false|
|n1-1-1|6|5|3.6|false|false|false|false|false|false|
|n0-0-2|0|0|7.2|false|false|false|false|false|false|
|n0-1-2|0|5|7.2|false|false|false|false|false|false|
|n1-0-2|6|0|7.2|false|false|false|false|false|false|
|n1-1-2|6|5|7.2|false|false|false|false|false|false|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-0-1|column|n0-0-0|n0-0-1|M1|C1|0|[1, 0, 0]|
|x0-0-1|beam|n0-0-1|n1-0-1|M1|BX|0|[0, 0, 1]|
|y0-0-1|beam|n0-0-1|n0-1-1|M1|BY|0|[0, 0, 1]|
|c0-1-1|column|n0-1-0|n0-1-1|M1|C1|0|[1, 0, 0]|
|x0-1-1|beam|n0-1-1|n1-1-1|M1|BX|0|[0, 0, 1]|
|c1-0-1|column|n1-0-0|n1-0-1|M1|C1|0|[1, 0, 0]|
|y1-0-1|beam|n1-0-1|n1-1-1|M1|BY|0|[0, 0, 1]|
|c1-1-1|column|n1-1-0|n1-1-1|M1|C1|0|[1, 0, 0]|
|c0-0-2|column|n0-0-1|n0-0-2|M1|C1|0|[1, 0, 0]|
|x0-0-2|beam|n0-0-2|n1-0-2|M1|BX|0|[0, 0, 1]|
|y0-0-2|beam|n0-0-2|n0-1-2|M1|BY|0|[0, 0, 1]|
|c0-1-2|column|n0-1-1|n0-1-2|M1|C1|0|[1, 0, 0]|
|x0-1-2|beam|n0-1-2|n1-1-2|M1|BX|0|[0, 0, 1]|
|c1-0-2|column|n1-0-1|n1-0-2|M1|C1|0|[1, 0, 0]|
|y1-0-2|beam|n1-0-2|n1-1-2|M1|BY|0|[0, 0, 1]|
|c1-1-2|column|n1-1-1|n1-1-2|M1|C1|0|[1, 0, 0]|
|brace-1|truss|n0-0-0|n1-0-1|M1|A_BRACE|0|[0, 0, 1]|
|brace-2|truss|n0-0-1|n1-0-2|M1|A_BRACE|0|[0, 0, 1]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Numerical inputs — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|BX|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|BY|250.0|500.0|0.125|0.0026041666666666665|0.0006510416666666666|0.0017881266276041667|
|C1|400.0|500.0|0.2|0.004166666666666667|0.0026666666666666674|0.005474167466666667|
|A_BRACE|100.0|100.0|0.010000000000000002|8.333333333333335e-06|8.333333333333335e-06|1.4083333333333338e-05|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|type|wz|fx|fy|
|---|---|---|---|---|
|D-1 → x0-0-1, D-2 → y0-0-1, D-3 → x0-1-1, D-4 → y1-0-1, D-5 → x0-0-2, D-6 → y0-0-2, D-7 → x0-1-2, D-8 → y1-0-2|distributed|-8|—|—|
|D-9 → n1-1-2|nodal|—|20|20|

Applies to every listed row: reference_frame = global.

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
|derived|[]|
|figures|[]|
|interactions|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case-D-node-n0-0-2-ux|node|n0-0-2|ux|m|—|—|
|case-D-node-n0-0-2-uy|node|n0-0-2|uy|m|—|—|
|case-D-node-n0-1-2-ux|node|n0-1-2|ux|m|—|—|
|case-D-node-n0-1-2-uy|node|n0-1-2|uy|m|—|—|
|case-D-node-n1-0-2-ux|node|n1-0-2|ux|m|—|—|
|case-D-node-n1-0-2-uy|node|n1-0-2|uy|m|—|—|
|case-D-node-n1-1-2-ux|node|n1-1-2|ux|m|—|—|
|case-D-node-n1-1-2-uy|node|n1-1-2|uy|m|—|—|
|case-D-member-c0-0-1-s0-right-N|member|c0-0-1|N|kN|0|right|
|case-D-member-c0-0-1-s0-right-V2|member|c0-0-1|V2|kN|0|right|
|case-D-member-c0-0-1-s0-right-V3|member|c0-0-1|V3|kN|0|right|
|case-D-member-c0-0-1-s0-right-T|member|c0-0-1|T|kN.m|0|right|
|case-D-member-c0-0-1-s0-right-M2|member|c0-0-1|M2|kN.m|0|right|
|case-D-member-c0-0-1-s0-right-M3|member|c0-0-1|M3|kN.m|0|right|
|case-D-member-c0-0-1-s3.6-left-N|member|c0-0-1|N|kN|3.6|left|
|case-D-member-c0-0-1-s3.6-left-V2|member|c0-0-1|V2|kN|3.6|left|
|case-D-member-c0-0-1-s3.6-left-V3|member|c0-0-1|V3|kN|3.6|left|
|case-D-member-c0-0-1-s3.6-left-T|member|c0-0-1|T|kN.m|3.6|left|
|case-D-member-c0-0-1-s3.6-left-M2|member|c0-0-1|M2|kN.m|3.6|left|
|case-D-member-c0-0-1-s3.6-left-M3|member|c0-0-1|M3|kN.m|3.6|left|
|case-D-member-x0-0-1-s0-right-N|member|x0-0-1|N|kN|0|right|
|case-D-member-x0-0-1-s0-right-V2|member|x0-0-1|V2|kN|0|right|
|case-D-member-x0-0-1-s0-right-V3|member|x0-0-1|V3|kN|0|right|
|case-D-member-x0-0-1-s0-right-T|member|x0-0-1|T|kN.m|0|right|
|case-D-member-x0-0-1-s0-right-M2|member|x0-0-1|M2|kN.m|0|right|
|case-D-member-x0-0-1-s0-right-M3|member|x0-0-1|M3|kN.m|0|right|
|case-D-member-x0-0-1-s6-left-N|member|x0-0-1|N|kN|6.0|left|
|case-D-member-x0-0-1-s6-left-V2|member|x0-0-1|V2|kN|6.0|left|
|case-D-member-x0-0-1-s6-left-V3|member|x0-0-1|V3|kN|6.0|left|
|case-D-member-x0-0-1-s6-left-T|member|x0-0-1|T|kN.m|6.0|left|
|case-D-member-x0-0-1-s6-left-M2|member|x0-0-1|M2|kN.m|6.0|left|
|case-D-member-x0-0-1-s6-left-M3|member|x0-0-1|M3|kN.m|6.0|left|
|case-D-member-y0-0-1-s0-right-N|member|y0-0-1|N|kN|0|right|
|case-D-member-y0-0-1-s0-right-V2|member|y0-0-1|V2|kN|0|right|
|case-D-member-y0-0-1-s0-right-V3|member|y0-0-1|V3|kN|0|right|
|case-D-member-y0-0-1-s0-right-T|member|y0-0-1|T|kN.m|0|right|
|case-D-member-y0-0-1-s0-right-M2|member|y0-0-1|M2|kN.m|0|right|
|case-D-member-y0-0-1-s0-right-M3|member|y0-0-1|M3|kN.m|0|right|
|case-D-member-y0-0-1-s5-left-N|member|y0-0-1|N|kN|5.0|left|
|case-D-member-y0-0-1-s5-left-V2|member|y0-0-1|V2|kN|5.0|left|
|case-D-member-y0-0-1-s5-left-V3|member|y0-0-1|V3|kN|5.0|left|
|case-D-member-y0-0-1-s5-left-T|member|y0-0-1|T|kN.m|5.0|left|
|case-D-member-y0-0-1-s5-left-M2|member|y0-0-1|M2|kN.m|5.0|left|
|case-D-member-y0-0-1-s5-left-M3|member|y0-0-1|M3|kN.m|5.0|left|
|case-D-member-c0-1-1-s0-right-N|member|c0-1-1|N|kN|0|right|
|case-D-member-c0-1-1-s0-right-V2|member|c0-1-1|V2|kN|0|right|
|case-D-member-c0-1-1-s0-right-V3|member|c0-1-1|V3|kN|0|right|
|case-D-member-c0-1-1-s0-right-T|member|c0-1-1|T|kN.m|0|right|
|case-D-member-c0-1-1-s0-right-M2|member|c0-1-1|M2|kN.m|0|right|
|case-D-member-c0-1-1-s0-right-M3|member|c0-1-1|M3|kN.m|0|right|
|case-D-member-c0-1-1-s3.6-left-N|member|c0-1-1|N|kN|3.6|left|
|case-D-member-c0-1-1-s3.6-left-V2|member|c0-1-1|V2|kN|3.6|left|
|case-D-member-c0-1-1-s3.6-left-V3|member|c0-1-1|V3|kN|3.6|left|
|case-D-member-c0-1-1-s3.6-left-T|member|c0-1-1|T|kN.m|3.6|left|
|case-D-member-c0-1-1-s3.6-left-M2|member|c0-1-1|M2|kN.m|3.6|left|
|case-D-member-c0-1-1-s3.6-left-M3|member|c0-1-1|M3|kN.m|3.6|left|
|case-D-member-x0-1-1-s0-right-N|member|x0-1-1|N|kN|0|right|
|case-D-member-x0-1-1-s0-right-V2|member|x0-1-1|V2|kN|0|right|
|case-D-member-x0-1-1-s0-right-V3|member|x0-1-1|V3|kN|0|right|
|case-D-member-x0-1-1-s0-right-T|member|x0-1-1|T|kN.m|0|right|
|case-D-member-x0-1-1-s0-right-M2|member|x0-1-1|M2|kN.m|0|right|
|case-D-member-x0-1-1-s0-right-M3|member|x0-1-1|M3|kN.m|0|right|
|case-D-member-x0-1-1-s6-left-N|member|x0-1-1|N|kN|6.0|left|
|case-D-member-x0-1-1-s6-left-V2|member|x0-1-1|V2|kN|6.0|left|
|case-D-member-x0-1-1-s6-left-V3|member|x0-1-1|V3|kN|6.0|left|
|case-D-member-x0-1-1-s6-left-T|member|x0-1-1|T|kN.m|6.0|left|
|case-D-member-x0-1-1-s6-left-M2|member|x0-1-1|M2|kN.m|6.0|left|
|case-D-member-x0-1-1-s6-left-M3|member|x0-1-1|M3|kN.m|6.0|left|
|case-D-member-c1-0-1-s0-right-N|member|c1-0-1|N|kN|0|right|
|case-D-member-c1-0-1-s0-right-V2|member|c1-0-1|V2|kN|0|right|
|case-D-member-c1-0-1-s0-right-V3|member|c1-0-1|V3|kN|0|right|
|case-D-member-c1-0-1-s0-right-T|member|c1-0-1|T|kN.m|0|right|
|case-D-member-c1-0-1-s0-right-M2|member|c1-0-1|M2|kN.m|0|right|
|case-D-member-c1-0-1-s0-right-M3|member|c1-0-1|M3|kN.m|0|right|
|case-D-member-c1-0-1-s3.6-left-N|member|c1-0-1|N|kN|3.6|left|
|case-D-member-c1-0-1-s3.6-left-V2|member|c1-0-1|V2|kN|3.6|left|
|case-D-member-c1-0-1-s3.6-left-V3|member|c1-0-1|V3|kN|3.6|left|
|case-D-member-c1-0-1-s3.6-left-T|member|c1-0-1|T|kN.m|3.6|left|
|case-D-member-c1-0-1-s3.6-left-M2|member|c1-0-1|M2|kN.m|3.6|left|
|case-D-member-c1-0-1-s3.6-left-M3|member|c1-0-1|M3|kN.m|3.6|left|
|case-D-member-y1-0-1-s0-right-N|member|y1-0-1|N|kN|0|right|
|case-D-member-y1-0-1-s0-right-V2|member|y1-0-1|V2|kN|0|right|
|case-D-member-y1-0-1-s0-right-V3|member|y1-0-1|V3|kN|0|right|
|case-D-member-y1-0-1-s0-right-T|member|y1-0-1|T|kN.m|0|right|
|case-D-member-y1-0-1-s0-right-M2|member|y1-0-1|M2|kN.m|0|right|
|case-D-member-y1-0-1-s0-right-M3|member|y1-0-1|M3|kN.m|0|right|
|case-D-member-y1-0-1-s5-left-N|member|y1-0-1|N|kN|5.0|left|
|case-D-member-y1-0-1-s5-left-V2|member|y1-0-1|V2|kN|5.0|left|
|case-D-member-y1-0-1-s5-left-V3|member|y1-0-1|V3|kN|5.0|left|
|case-D-member-y1-0-1-s5-left-T|member|y1-0-1|T|kN.m|5.0|left|
|case-D-member-y1-0-1-s5-left-M2|member|y1-0-1|M2|kN.m|5.0|left|
|case-D-member-y1-0-1-s5-left-M3|member|y1-0-1|M3|kN.m|5.0|left|
|case-D-member-c1-1-1-s0-right-N|member|c1-1-1|N|kN|0|right|
|case-D-member-c1-1-1-s0-right-V2|member|c1-1-1|V2|kN|0|right|
|case-D-member-c1-1-1-s0-right-V3|member|c1-1-1|V3|kN|0|right|
|case-D-member-c1-1-1-s0-right-T|member|c1-1-1|T|kN.m|0|right|
|case-D-member-c1-1-1-s0-right-M2|member|c1-1-1|M2|kN.m|0|right|
|case-D-member-c1-1-1-s0-right-M3|member|c1-1-1|M3|kN.m|0|right|
|case-D-member-c1-1-1-s3.6-left-N|member|c1-1-1|N|kN|3.6|left|
|case-D-member-c1-1-1-s3.6-left-V2|member|c1-1-1|V2|kN|3.6|left|
|case-D-member-c1-1-1-s3.6-left-V3|member|c1-1-1|V3|kN|3.6|left|
|case-D-member-c1-1-1-s3.6-left-T|member|c1-1-1|T|kN.m|3.6|left|
|case-D-member-c1-1-1-s3.6-left-M2|member|c1-1-1|M2|kN.m|3.6|left|
|case-D-member-c1-1-1-s3.6-left-M3|member|c1-1-1|M3|kN.m|3.6|left|
|case-D-member-c0-0-2-s0-right-N|member|c0-0-2|N|kN|0|right|
|case-D-member-c0-0-2-s0-right-V2|member|c0-0-2|V2|kN|0|right|
|case-D-member-c0-0-2-s0-right-V3|member|c0-0-2|V3|kN|0|right|
|case-D-member-c0-0-2-s0-right-T|member|c0-0-2|T|kN.m|0|right|
|case-D-member-c0-0-2-s0-right-M2|member|c0-0-2|M2|kN.m|0|right|
|case-D-member-c0-0-2-s0-right-M3|member|c0-0-2|M3|kN.m|0|right|
|case-D-member-c0-0-2-s3.6-left-N|member|c0-0-2|N|kN|3.6|left|
|case-D-member-c0-0-2-s3.6-left-V2|member|c0-0-2|V2|kN|3.6|left|
|case-D-member-c0-0-2-s3.6-left-V3|member|c0-0-2|V3|kN|3.6|left|
|case-D-member-c0-0-2-s3.6-left-T|member|c0-0-2|T|kN.m|3.6|left|
|case-D-member-c0-0-2-s3.6-left-M2|member|c0-0-2|M2|kN.m|3.6|left|
|case-D-member-c0-0-2-s3.6-left-M3|member|c0-0-2|M3|kN.m|3.6|left|
|case-D-member-x0-0-2-s0-right-N|member|x0-0-2|N|kN|0|right|
|case-D-member-x0-0-2-s0-right-V2|member|x0-0-2|V2|kN|0|right|
|case-D-member-x0-0-2-s0-right-V3|member|x0-0-2|V3|kN|0|right|
|case-D-member-x0-0-2-s0-right-T|member|x0-0-2|T|kN.m|0|right|
|case-D-member-x0-0-2-s0-right-M2|member|x0-0-2|M2|kN.m|0|right|
|case-D-member-x0-0-2-s0-right-M3|member|x0-0-2|M3|kN.m|0|right|
|case-D-member-x0-0-2-s6-left-N|member|x0-0-2|N|kN|6.0|left|
|case-D-member-x0-0-2-s6-left-V2|member|x0-0-2|V2|kN|6.0|left|
|case-D-member-x0-0-2-s6-left-V3|member|x0-0-2|V3|kN|6.0|left|
|case-D-member-x0-0-2-s6-left-T|member|x0-0-2|T|kN.m|6.0|left|
|case-D-member-x0-0-2-s6-left-M2|member|x0-0-2|M2|kN.m|6.0|left|
|case-D-member-x0-0-2-s6-left-M3|member|x0-0-2|M3|kN.m|6.0|left|
|case-D-member-y0-0-2-s0-right-N|member|y0-0-2|N|kN|0|right|
|case-D-member-y0-0-2-s0-right-V2|member|y0-0-2|V2|kN|0|right|
|case-D-member-y0-0-2-s0-right-V3|member|y0-0-2|V3|kN|0|right|
|case-D-member-y0-0-2-s0-right-T|member|y0-0-2|T|kN.m|0|right|
|case-D-member-y0-0-2-s0-right-M2|member|y0-0-2|M2|kN.m|0|right|
|case-D-member-y0-0-2-s0-right-M3|member|y0-0-2|M3|kN.m|0|right|
|case-D-member-y0-0-2-s5-left-N|member|y0-0-2|N|kN|5.0|left|
|case-D-member-y0-0-2-s5-left-V2|member|y0-0-2|V2|kN|5.0|left|
|case-D-member-y0-0-2-s5-left-V3|member|y0-0-2|V3|kN|5.0|left|
|case-D-member-y0-0-2-s5-left-T|member|y0-0-2|T|kN.m|5.0|left|
|case-D-member-y0-0-2-s5-left-M2|member|y0-0-2|M2|kN.m|5.0|left|
|case-D-member-y0-0-2-s5-left-M3|member|y0-0-2|M3|kN.m|5.0|left|
|case-D-member-c0-1-2-s0-right-N|member|c0-1-2|N|kN|0|right|
|case-D-member-c0-1-2-s0-right-V2|member|c0-1-2|V2|kN|0|right|
|case-D-member-c0-1-2-s0-right-V3|member|c0-1-2|V3|kN|0|right|
|case-D-member-c0-1-2-s0-right-T|member|c0-1-2|T|kN.m|0|right|
|case-D-member-c0-1-2-s0-right-M2|member|c0-1-2|M2|kN.m|0|right|
|case-D-member-c0-1-2-s0-right-M3|member|c0-1-2|M3|kN.m|0|right|
|case-D-member-c0-1-2-s3.6-left-N|member|c0-1-2|N|kN|3.6|left|
|case-D-member-c0-1-2-s3.6-left-V2|member|c0-1-2|V2|kN|3.6|left|
|case-D-member-c0-1-2-s3.6-left-V3|member|c0-1-2|V3|kN|3.6|left|
|case-D-member-c0-1-2-s3.6-left-T|member|c0-1-2|T|kN.m|3.6|left|
|case-D-member-c0-1-2-s3.6-left-M2|member|c0-1-2|M2|kN.m|3.6|left|
|case-D-member-c0-1-2-s3.6-left-M3|member|c0-1-2|M3|kN.m|3.6|left|
|case-D-member-x0-1-2-s0-right-N|member|x0-1-2|N|kN|0|right|
|case-D-member-x0-1-2-s0-right-V2|member|x0-1-2|V2|kN|0|right|
|case-D-member-x0-1-2-s0-right-V3|member|x0-1-2|V3|kN|0|right|
|case-D-member-x0-1-2-s0-right-T|member|x0-1-2|T|kN.m|0|right|
|case-D-member-x0-1-2-s0-right-M2|member|x0-1-2|M2|kN.m|0|right|
|case-D-member-x0-1-2-s0-right-M3|member|x0-1-2|M3|kN.m|0|right|
|case-D-member-x0-1-2-s6-left-N|member|x0-1-2|N|kN|6.0|left|
|case-D-member-x0-1-2-s6-left-V2|member|x0-1-2|V2|kN|6.0|left|
|case-D-member-x0-1-2-s6-left-V3|member|x0-1-2|V3|kN|6.0|left|
|case-D-member-x0-1-2-s6-left-T|member|x0-1-2|T|kN.m|6.0|left|
|case-D-member-x0-1-2-s6-left-M2|member|x0-1-2|M2|kN.m|6.0|left|
|case-D-member-x0-1-2-s6-left-M3|member|x0-1-2|M3|kN.m|6.0|left|
|case-D-member-c1-0-2-s0-right-N|member|c1-0-2|N|kN|0|right|
|case-D-member-c1-0-2-s0-right-V2|member|c1-0-2|V2|kN|0|right|
|case-D-member-c1-0-2-s0-right-V3|member|c1-0-2|V3|kN|0|right|
|case-D-member-c1-0-2-s0-right-T|member|c1-0-2|T|kN.m|0|right|
|case-D-member-c1-0-2-s0-right-M2|member|c1-0-2|M2|kN.m|0|right|
|case-D-member-c1-0-2-s0-right-M3|member|c1-0-2|M3|kN.m|0|right|
|case-D-member-c1-0-2-s3.6-left-N|member|c1-0-2|N|kN|3.6|left|
|case-D-member-c1-0-2-s3.6-left-V2|member|c1-0-2|V2|kN|3.6|left|
|case-D-member-c1-0-2-s3.6-left-V3|member|c1-0-2|V3|kN|3.6|left|
|case-D-member-c1-0-2-s3.6-left-T|member|c1-0-2|T|kN.m|3.6|left|
|case-D-member-c1-0-2-s3.6-left-M2|member|c1-0-2|M2|kN.m|3.6|left|
|case-D-member-c1-0-2-s3.6-left-M3|member|c1-0-2|M3|kN.m|3.6|left|
|case-D-member-y1-0-2-s0-right-N|member|y1-0-2|N|kN|0|right|
|case-D-member-y1-0-2-s0-right-V2|member|y1-0-2|V2|kN|0|right|
|case-D-member-y1-0-2-s0-right-V3|member|y1-0-2|V3|kN|0|right|
|case-D-member-y1-0-2-s0-right-T|member|y1-0-2|T|kN.m|0|right|
|case-D-member-y1-0-2-s0-right-M2|member|y1-0-2|M2|kN.m|0|right|
|case-D-member-y1-0-2-s0-right-M3|member|y1-0-2|M3|kN.m|0|right|
|case-D-member-y1-0-2-s5-left-N|member|y1-0-2|N|kN|5.0|left|
|case-D-member-y1-0-2-s5-left-V2|member|y1-0-2|V2|kN|5.0|left|
|case-D-member-y1-0-2-s5-left-V3|member|y1-0-2|V3|kN|5.0|left|
|case-D-member-y1-0-2-s5-left-T|member|y1-0-2|T|kN.m|5.0|left|
|case-D-member-y1-0-2-s5-left-M2|member|y1-0-2|M2|kN.m|5.0|left|
|case-D-member-y1-0-2-s5-left-M3|member|y1-0-2|M3|kN.m|5.0|left|
|case-D-member-c1-1-2-s0-right-N|member|c1-1-2|N|kN|0|right|
|case-D-member-c1-1-2-s0-right-V2|member|c1-1-2|V2|kN|0|right|
|case-D-member-c1-1-2-s0-right-V3|member|c1-1-2|V3|kN|0|right|
|case-D-member-c1-1-2-s0-right-T|member|c1-1-2|T|kN.m|0|right|
|case-D-member-c1-1-2-s0-right-M2|member|c1-1-2|M2|kN.m|0|right|
|case-D-member-c1-1-2-s0-right-M3|member|c1-1-2|M3|kN.m|0|right|
|case-D-member-c1-1-2-s3.6-left-N|member|c1-1-2|N|kN|3.6|left|
|case-D-member-c1-1-2-s3.6-left-V2|member|c1-1-2|V2|kN|3.6|left|
|case-D-member-c1-1-2-s3.6-left-V3|member|c1-1-2|V3|kN|3.6|left|
|case-D-member-c1-1-2-s3.6-left-T|member|c1-1-2|T|kN.m|3.6|left|
|case-D-member-c1-1-2-s3.6-left-M2|member|c1-1-2|M2|kN.m|3.6|left|
|case-D-member-c1-1-2-s3.6-left-M3|member|c1-1-2|M3|kN.m|3.6|left|
|case-D-member-brace-1-s0-right-N|member|brace-1|N|kN|0|right|
|case-D-member-brace-1-s6.99714227381-left-N|member|brace-1|N|kN|6.997142273814361|left|
|case-D-member-brace-2-s0-right-N|member|brace-2|N|kN|0|right|
|case-D-member-brace-2-s6.99714227381-left-N|member|brace-2|N|kN|6.997142273814361|left|
|case-D-node-n0-0-0-Fx|node|n0-0-0|Fx|kN|—|—|
|case-D-node-n0-0-0-Fy|node|n0-0-0|Fy|kN|—|—|
|case-D-node-n0-0-0-Fz|node|n0-0-0|Fz|kN|—|—|
|case-D-node-n0-0-0-Mx|node|n0-0-0|Mx|kN.m|—|—|
|case-D-node-n0-0-0-My|node|n0-0-0|My|kN.m|—|—|
|case-D-node-n0-0-0-Mz|node|n0-0-0|Mz|kN.m|—|—|
|case-D-node-n0-1-0-Fx|node|n0-1-0|Fx|kN|—|—|
|case-D-node-n0-1-0-Fy|node|n0-1-0|Fy|kN|—|—|
|case-D-node-n0-1-0-Fz|node|n0-1-0|Fz|kN|—|—|
|case-D-node-n0-1-0-Mx|node|n0-1-0|Mx|kN.m|—|—|
|case-D-node-n0-1-0-My|node|n0-1-0|My|kN.m|—|—|
|case-D-node-n0-1-0-Mz|node|n0-1-0|Mz|kN.m|—|—|
|case-D-node-n1-0-0-Fx|node|n1-0-0|Fx|kN|—|—|
|case-D-node-n1-0-0-Fy|node|n1-0-0|Fy|kN|—|—|
|case-D-node-n1-0-0-Fz|node|n1-0-0|Fz|kN|—|—|
|case-D-node-n1-0-0-Mx|node|n1-0-0|Mx|kN.m|—|—|
|case-D-node-n1-0-0-My|node|n1-0-0|My|kN.m|—|—|
|case-D-node-n1-0-0-Mz|node|n1-0-0|Mz|kN.m|—|—|
|case-D-node-n1-1-0-Fx|node|n1-1-0|Fx|kN|—|—|
|case-D-node-n1-1-0-Fy|node|n1-1-0|Fy|kN|—|—|
|case-D-node-n1-1-0-Fz|node|n1-1-0|Fz|kN|—|—|
|case-D-node-n1-1-0-Mx|node|n1-1-0|Mx|kN.m|—|—|
|case-D-node-n1-1-0-My|node|n1-1-0|My|kN.m|—|—|
|case-D-node-n1-1-0-Mz|node|n1-1-0|Mz|kN.m|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis conventions

按指定引擎进行一阶线弹性静力分析，采用Euler-Bernoulli弯曲（不计剪切变形）；关闭自重、P-Delta、刚性楼板、刚臂偏移及施工阶段。全局XYZ，Z向上；平面模型位于XZ平面。坐标/位移m，力kN，弯矩kN*m，线载kN/m（按真实杆长），E/G为MPa，密度kg/m^3，A为m^2，Iy/Iz/J为m^4，shape尺寸mm，转角rad。约束顺序ux,uy,uz,rx,ry,rz，true表示固定。梁柱共节点刚接，桁架杆仅传轴力；支座以输入表为准。局部x由构件首节点指向末节点；空间杆局部y为reference vector叉乘局部x的单位向量，局部z=x叉乘y，再按rotation_angle绕局部x转动；平面杆未转轴时局部y为全局+Y、局部z为局部x叉乘局部y，再绕局部x施加rotation_angle；Iy为绕局部y的惯性矩。平面metadata参考向量不采用上述空间叉乘公式。报告局部到全局的转换。杆件位置从首节点计量，side为截面左右极限。N以拉为正；对局部杆端抗力按N,V2,V3,T,M2,M3排序，首节点端乘(-1,+1,+1,-1,-1,-1)、末节点端乘(+1,-1,-1,+1,+1,+1)转换为要求的有符号截面内力，不能取无符号包络替代。逐项报告input.md中数值及派生量，保留符号、单位、工况/组合；绝对值控制量同时给出原符号和控制项/组合。保存可运行输入、引擎版本、/日志及带索引原始结果；这些属于待执行要求，并非已有证据。input.md为完整公开输入附表，不含答案。
