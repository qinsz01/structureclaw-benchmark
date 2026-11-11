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
|n0-2-0|0|10|0|true|true|true|true|true|true|
|n1-0-0|6|0|0|true|true|true|true|true|true|
|n1-1-0|6|5|0|true|true|true|true|true|true|
|n1-2-0|6|10|0|true|true|true|true|true|true|
|n2-0-0|12|0|0|true|true|true|true|true|true|
|n2-1-0|12|5|0|true|true|true|true|true|true|
|n2-2-0|12|10|0|true|true|true|true|true|true|
|n0-0-1|0|0|3.6|false|false|false|false|false|false|
|n0-1-1|0|5|3.6|false|false|false|false|false|false|
|n0-2-1|0|10|3.6|false|false|false|false|false|false|
|n1-0-1|6|0|3.6|false|false|false|false|false|false|
|n1-1-1|6|5|3.6|false|false|false|false|false|false|
|n1-2-1|6|10|3.6|false|false|false|false|false|false|
|n2-0-1|12|0|3.6|false|false|false|false|false|false|
|n2-1-1|12|5|3.6|false|false|false|false|false|false|
|n2-2-1|12|10|3.6|false|false|false|false|false|false|
|n0-0-2|0|0|7.2|false|false|false|false|false|false|
|n0-1-2|0|5|7.2|false|false|false|false|false|false|
|n0-2-2|0|10|7.2|false|false|false|false|false|false|
|n1-0-2|6|0|7.2|false|false|false|false|false|false|
|n1-1-2|6|5|7.2|false|false|false|false|false|false|
|n1-2-2|6|10|7.2|false|false|false|false|false|false|
|n2-0-2|12|0|7.2|false|false|false|false|false|false|
|n2-1-2|12|5|7.2|false|false|false|false|false|false|
|n2-2-2|12|10|7.2|false|false|false|false|false|false|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-0-1|column|n0-0-0|n0-0-1|M1|C_CORNER|0|[1, 0, 0]|
|x0-0-1|beam|n0-0-1|n1-0-1|M1|BX|0|[0, 0, 1]|
|y0-0-1|beam|n0-0-1|n0-1-1|M1|BY|0|[0, 0, 1]|
|c0-1-1|column|n0-1-0|n0-1-1|M1|C_EDGE|0|[1, 0, 0]|
|x0-1-1|beam|n0-1-1|n1-1-1|M1|BX|0|[0, 0, 1]|
|y0-1-1|beam|n0-1-1|n0-2-1|M1|BY|0|[0, 0, 1]|
|c0-2-1|column|n0-2-0|n0-2-1|M1|C_CORNER|0|[1, 0, 0]|
|x0-2-1|beam|n0-2-1|n1-2-1|M1|BX|0|[0, 0, 1]|
|c1-0-1|column|n1-0-0|n1-0-1|M1|C_EDGE|0|[1, 0, 0]|
|x1-0-1|beam|n1-0-1|n2-0-1|M1|BX|0|[0, 0, 1]|
|y1-0-1|beam|n1-0-1|n1-1-1|M1|BY|0|[0, 0, 1]|
|c1-1-1|column|n1-1-0|n1-1-1|M1|C_INTERIOR|0|[1, 0, 0]|
|x1-1-1|beam|n1-1-1|n2-1-1|M1|BX|0|[0, 0, 1]|
|y1-1-1|beam|n1-1-1|n1-2-1|M1|BY|0|[0, 0, 1]|
|c1-2-1|column|n1-2-0|n1-2-1|M1|C_EDGE|0|[1, 0, 0]|
|x1-2-1|beam|n1-2-1|n2-2-1|M1|BX|0|[0, 0, 1]|
|c2-0-1|column|n2-0-0|n2-0-1|M1|C_CORNER|0|[1, 0, 0]|
|y2-0-1|beam|n2-0-1|n2-1-1|M1|BY|0|[0, 0, 1]|
|c2-1-1|column|n2-1-0|n2-1-1|M1|C_EDGE|0|[1, 0, 0]|
|y2-1-1|beam|n2-1-1|n2-2-1|M1|BY|0|[0, 0, 1]|
|c2-2-1|column|n2-2-0|n2-2-1|M1|C_CORNER|0|[1, 0, 0]|
|c0-0-2|column|n0-0-1|n0-0-2|M1|C_CORNER|0|[1, 0, 0]|
|x0-0-2|beam|n0-0-2|n1-0-2|M1|BX|0|[0, 0, 1]|
|y0-0-2|beam|n0-0-2|n0-1-2|M1|BY|0|[0, 0, 1]|
|c0-1-2|column|n0-1-1|n0-1-2|M1|C_EDGE|0|[1, 0, 0]|
|x0-1-2|beam|n0-1-2|n1-1-2|M1|BX|0|[0, 0, 1]|
|y0-1-2|beam|n0-1-2|n0-2-2|M1|BY|0|[0, 0, 1]|
|c0-2-2|column|n0-2-1|n0-2-2|M1|C_CORNER|0|[1, 0, 0]|
|x0-2-2|beam|n0-2-2|n1-2-2|M1|BX|0|[0, 0, 1]|
|c1-0-2|column|n1-0-1|n1-0-2|M1|C_EDGE|0|[1, 0, 0]|
|x1-0-2|beam|n1-0-2|n2-0-2|M1|BX|0|[0, 0, 1]|
|y1-0-2|beam|n1-0-2|n1-1-2|M1|BY|0|[0, 0, 1]|
|c1-1-2|column|n1-1-1|n1-1-2|M1|C_INTERIOR|0|[1, 0, 0]|
|x1-1-2|beam|n1-1-2|n2-1-2|M1|BX|0|[0, 0, 1]|
|y1-1-2|beam|n1-1-2|n1-2-2|M1|BY|0|[0, 0, 1]|
|c1-2-2|column|n1-2-1|n1-2-2|M1|C_EDGE|0|[1, 0, 0]|
|x1-2-2|beam|n1-2-2|n2-2-2|M1|BX|0|[0, 0, 1]|
|c2-0-2|column|n2-0-1|n2-0-2|M1|C_CORNER|0|[1, 0, 0]|
|y2-0-2|beam|n2-0-2|n2-1-2|M1|BY|0|[0, 0, 1]|
|c2-1-2|column|n2-1-1|n2-1-2|M1|C_EDGE|0|[1, 0, 0]|
|y2-1-2|beam|n2-1-2|n2-2-2|M1|BY|0|[0, 0, 1]|
|c2-2-2|column|n2-2-1|n2-2-2|M1|C_CORNER|0|[1, 0, 0]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Numerical inputs — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|BX|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|BY|250.0|500.0|0.125|0.0026041666666666665|0.0006510416666666666|0.0017881266276041667|
|C_CORNER|400.0|400.0|0.16000000000000003|0.002133333333333334|0.002133333333333334|0.0036053333333333345|
|C_EDGE|450.0|500.0|0.225|0.0046875|0.0037968750000000003|0.007047011010937501|
|C_INTERIOR|550.0|550.0|0.30250000000000005|0.007625520833333337|0.007625520833333337|0.012887130208333339|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|type|wz|fx|fy|
|---|---|---|---|---|
|D-1 → x0-0-1, D-2 → y0-0-1, D-3 → x0-1-1, D-4 → y0-1-1, D-5 → x0-2-1, D-6 → x1-0-1, D-7 → y1-0-1, D-8 → x1-1-1, D-9 → y1-1-1, D-10 → x1-2-1, D-11 → y2-0-1, D-12 → y2-1-1, D-13 → x0-0-2, D-14 → y0-0-2, D-15 → x0-1-2, D-16 → y0-1-2, D-17 → x0-2-2, D-18 → x1-0-2, D-19 → y1-0-2, D-20 → x1-1-2, D-21 → y1-1-2, D-22 → x1-2-2, D-23 → y2-0-2, D-24 → y2-1-2|distributed|-8|—|—|
|D-25 → n2-2-2|nodal|—|20|15|

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
|case-D-node-n0-0-2-uz|node|n0-0-2|uz|m|—|—|
|case-D-node-n0-1-2-ux|node|n0-1-2|ux|m|—|—|
|case-D-node-n0-1-2-uy|node|n0-1-2|uy|m|—|—|
|case-D-node-n0-1-2-uz|node|n0-1-2|uz|m|—|—|
|case-D-node-n0-2-2-ux|node|n0-2-2|ux|m|—|—|
|case-D-node-n0-2-2-uy|node|n0-2-2|uy|m|—|—|
|case-D-node-n0-2-2-uz|node|n0-2-2|uz|m|—|—|
|case-D-node-n1-0-2-ux|node|n1-0-2|ux|m|—|—|
|case-D-node-n1-0-2-uy|node|n1-0-2|uy|m|—|—|
|case-D-node-n1-0-2-uz|node|n1-0-2|uz|m|—|—|
|case-D-node-n1-1-2-ux|node|n1-1-2|ux|m|—|—|
|case-D-node-n1-1-2-uy|node|n1-1-2|uy|m|—|—|
|case-D-node-n1-1-2-uz|node|n1-1-2|uz|m|—|—|
|case-D-node-n1-2-2-ux|node|n1-2-2|ux|m|—|—|
|case-D-node-n1-2-2-uy|node|n1-2-2|uy|m|—|—|
|case-D-node-n1-2-2-uz|node|n1-2-2|uz|m|—|—|
|case-D-node-n2-0-2-ux|node|n2-0-2|ux|m|—|—|
|case-D-node-n2-0-2-uy|node|n2-0-2|uy|m|—|—|
|case-D-node-n2-0-2-uz|node|n2-0-2|uz|m|—|—|
|case-D-node-n2-1-2-ux|node|n2-1-2|ux|m|—|—|
|case-D-node-n2-1-2-uy|node|n2-1-2|uy|m|—|—|
|case-D-node-n2-1-2-uz|node|n2-1-2|uz|m|—|—|
|case-D-node-n2-2-2-ux|node|n2-2-2|ux|m|—|—|
|case-D-node-n2-2-2-uy|node|n2-2-2|uy|m|—|—|
|case-D-node-n2-2-2-uz|node|n2-2-2|uz|m|—|—|
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
|case-D-node-n0-2-0-Fx|node|n0-2-0|Fx|kN|—|—|
|case-D-node-n0-2-0-Fy|node|n0-2-0|Fy|kN|—|—|
|case-D-node-n0-2-0-Fz|node|n0-2-0|Fz|kN|—|—|
|case-D-node-n0-2-0-Mx|node|n0-2-0|Mx|kN.m|—|—|
|case-D-node-n0-2-0-My|node|n0-2-0|My|kN.m|—|—|
|case-D-node-n0-2-0-Mz|node|n0-2-0|Mz|kN.m|—|—|
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
|case-D-node-n1-2-0-Fx|node|n1-2-0|Fx|kN|—|—|
|case-D-node-n1-2-0-Fy|node|n1-2-0|Fy|kN|—|—|
|case-D-node-n1-2-0-Fz|node|n1-2-0|Fz|kN|—|—|
|case-D-node-n1-2-0-Mx|node|n1-2-0|Mx|kN.m|—|—|
|case-D-node-n1-2-0-My|node|n1-2-0|My|kN.m|—|—|
|case-D-node-n1-2-0-Mz|node|n1-2-0|Mz|kN.m|—|—|
|case-D-node-n2-0-0-Fx|node|n2-0-0|Fx|kN|—|—|
|case-D-node-n2-0-0-Fy|node|n2-0-0|Fy|kN|—|—|
|case-D-node-n2-0-0-Fz|node|n2-0-0|Fz|kN|—|—|
|case-D-node-n2-0-0-Mx|node|n2-0-0|Mx|kN.m|—|—|
|case-D-node-n2-0-0-My|node|n2-0-0|My|kN.m|—|—|
|case-D-node-n2-0-0-Mz|node|n2-0-0|Mz|kN.m|—|—|
|case-D-node-n2-1-0-Fx|node|n2-1-0|Fx|kN|—|—|
|case-D-node-n2-1-0-Fy|node|n2-1-0|Fy|kN|—|—|
|case-D-node-n2-1-0-Fz|node|n2-1-0|Fz|kN|—|—|
|case-D-node-n2-1-0-Mx|node|n2-1-0|Mx|kN.m|—|—|
|case-D-node-n2-1-0-My|node|n2-1-0|My|kN.m|—|—|
|case-D-node-n2-1-0-Mz|node|n2-1-0|Mz|kN.m|—|—|
|case-D-node-n2-2-0-Fx|node|n2-2-0|Fx|kN|—|—|
|case-D-node-n2-2-0-Fy|node|n2-2-0|Fy|kN|—|—|
|case-D-node-n2-2-0-Fz|node|n2-2-0|Fz|kN|—|—|
|case-D-node-n2-2-0-Mx|node|n2-2-0|Mx|kN.m|—|—|
|case-D-node-n2-2-0-My|node|n2-2-0|My|kN.m|—|—|
|case-D-node-n2-2-0-Mz|node|n2-2-0|Mz|kN.m|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis conventions

按指定引擎进行一阶线弹性静力分析，采用Timoshenko弯曲（计入规定的剪切变形）；关闭自重、P-Delta、刚性楼板、刚臂偏移及施工阶段。全局XYZ，Z向上；平面模型位于XZ平面。坐标/位移m，力kN，弯矩kN*m，线载kN/m（按真实杆长），E/G为MPa，密度kg/m^3，A为m^2，Iy/Iz/J为m^4，shape尺寸mm，转角rad。约束顺序ux,uy,uz,rx,ry,rz，true表示固定。梁柱共节点刚接，桁架杆仅传轴力；支座以输入表为准。局部x由构件首节点指向末节点；空间杆局部y为reference vector叉乘局部x的单位向量，局部z=x叉乘y，再按rotation_angle绕局部x转动；平面杆未转轴时局部y为全局+Y、局部z为局部x叉乘局部y，再绕局部x施加rotation_angle；Iy为绕局部y的惯性矩。平面metadata参考向量不采用上述空间叉乘公式。报告局部到全局的转换。杆件位置从首节点计量，side为截面左右极限。N以拉为正；对局部杆端抗力按N,V2,V3,T,M2,M3排序，首节点端乘(-1,+1,+1,-1,-1,-1)、末节点端乘(+1,-1,-1,+1,+1,+1)转换为要求的有符号截面内力，不能取无符号包络替代。逐项报告input.md中数值及派生量，保留符号、单位、工况/组合；绝对值控制量同时给出原符号和控制项/组合。保存可运行输入、引擎版本、/日志及带索引原始结果；这些属于待执行要求，并非已有证据。input.md为完整公开输入附表，不含答案。

## Engine mapping

|Field|Value|
|---|---|
|引擎|PKPM|
|原生执行状态|pending|
|坐标映射要求|协议全局(X,Y,Z)与原生工程全局(X,Y,Z)同向，Z向上；若原生内部轴不同，交付显式变换表。|
|单位映射要求|协议坐标m、力kN、弯矩kN*m、线载kN/m、E/G MPa、截面尺寸mm、惯性矩m^4；原生内部单位逐字段转换并记录。|
|组合映射要求|[]|
|逐构件属性和节点荷载|保留input.md的全部节点、连接、材料、截面组、局部轴、支座与荷载；记录到原生ID的完整双向映射。|
|设置要求|一阶线弹性Timoshenko杆系；关闭自重、刚性楼板、刚域、P-Delta、施工阶段及默认规范组合。|
|结果要求|各协议节点/构件、端点、局部轴分量、工况/组合、符号和单位逐项关联原生结果；不得省略柱脚六分量反力。|
|待验收缺口|实际原生接口、逐梁/节点加载、原生求解与结果索引均待验收；本附表是执行契约，不是原生计算证据。|

## Engine mapping — 工况映射要求

|协议类型|协议ID|原生目标类型|加载方式|原生实际工况标识|
|---|---|---|---|---|
|case|D|DL|逐构件线载及明确节点向量；不得用整层面载覆盖、自动传载或重复添加。|待运行记录|

## Native analysis conventions

商业引擎弹性分析约定：commercial-linear-static-v2

采用指定原生引擎进行一阶、小位移、线弹性静力分析，梁柱采用 Timoshenko
弯曲。对每根梁、柱明确规定有效剪切面积 Asy = Asz = 5*A/6，单位 m^2；
A 为当前已公开属性附表中的截面面积，Asy 对应局部 y 方向剪力 V2，Asz
对应局部 z 方向剪力 V3。这是本基准规定的理想化，包括只给数值属性的
广义截面，并非按截面名称推测；后续新增或修改的截面同样采用此明确公式。
桁架或支撑杆仍按题目规定仅承受轴力。

保留题定 E、G、A、Iy、Iz、J、几何、连接、支座、荷载及工况/组合。
题定采用混凝土未开裂毛截面时保留该刚度；局部轴、杆端截面内力符号及
单位仍按原附表。自重、刚性楼板、刚域、P-Delta 和施工阶段保持关闭。

显式实现题定弹性刚度，不以原生材料牌号的默认值替代。采用等效 EA、
G*Asy、G*Asz、GJ、E*Iy、E*Iz 的原生表达时，须保留题定物理参数，
同时报告实际原生材料/截面参数、修正系数及数值序列化差异。弹性刚度
等效不代表原生材料字段逐字相同，也不代表已验证应力或设计计算。
保存原生输入、设置、引擎版本、日志和原始结果证据。本附表提供分析输入，
不提供计算答案或验收结论。
