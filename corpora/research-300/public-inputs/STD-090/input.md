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
|n0-0-1|0|0|3.6|false|false|false|false|false|false|
|n0-1-1|0|5|3.6|false|false|false|false|false|false|
|n0-2-1|0|10|3.6|false|false|false|false|false|false|
|n1-0-1|6|0|3.6|false|false|false|false|false|false|
|n1-1-1|6|5|3.6|false|false|false|false|false|false|
|n1-2-1|6|10|3.6|false|false|false|false|false|false|
|n0-0-2|0|0|7.2|false|false|false|false|false|false|
|n0-1-2|0|5|7.2|false|false|false|false|false|false|
|n0-2-2|0|10|7.2|false|false|false|false|false|false|
|n1-0-2|6|0|7.2|false|false|false|false|false|false|
|n1-1-2|6|5|7.2|false|false|false|false|false|false|
|n1-2-2|6|10|7.2|false|false|false|false|false|false|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-0-1|column|n0-0-0|n0-0-1|M1|C1|90|[1, 0, 0]|
|x0-0-1|beam|n0-0-1|n1-0-1|M1|BX|0|[0, 0, 1]|
|y0-0-1|beam|n0-0-1|n0-1-1|M1|BY|0|[0, 0, 1]|
|c0-1-1|column|n0-1-0|n0-1-1|M1|C1|0|[1, 0, 0]|
|x0-1-1|beam|n0-1-1|n1-1-1|M1|BX|0|[0, 0, 1]|
|y0-1-1|beam|n0-1-1|n0-2-1|M1|BY|0|[0, 0, 1]|
|c0-2-1|column|n0-2-0|n0-2-1|M1|C1|0|[1, 0, 0]|
|x0-2-1|beam|n0-2-1|n1-2-1|M1|BX|0|[0, 0, 1]|
|c1-0-1|column|n1-0-0|n1-0-1|M1|C1|90|[1, 0, 0]|
|y1-0-1|beam|n1-0-1|n1-1-1|M1|BY|0|[0, 0, 1]|
|c1-1-1|column|n1-1-0|n1-1-1|M1|C1|0|[1, 0, 0]|
|y1-1-1|beam|n1-1-1|n1-2-1|M1|BY|0|[0, 0, 1]|
|c1-2-1|column|n1-2-0|n1-2-1|M1|C1|0|[1, 0, 0]|
|c0-0-2|column|n0-0-1|n0-0-2|M1|C1|90|[1, 0, 0]|
|x0-0-2|beam|n0-0-2|n1-0-2|M1|BX|0|[0, 0, 1]|
|y0-0-2|beam|n0-0-2|n0-1-2|M1|BY|0|[0, 0, 1]|
|c0-1-2|column|n0-1-1|n0-1-2|M1|C1|0|[1, 0, 0]|
|x0-1-2|beam|n0-1-2|n1-1-2|M1|BX|0|[0, 0, 1]|
|y0-1-2|beam|n0-1-2|n0-2-2|M1|BY|0|[0, 0, 1]|
|c0-2-2|column|n0-2-1|n0-2-2|M1|C1|0|[1, 0, 0]|
|x0-2-2|beam|n0-2-2|n1-2-2|M1|BX|0|[0, 0, 1]|
|c1-0-2|column|n1-0-1|n1-0-2|M1|C1|90|[1, 0, 0]|
|y1-0-2|beam|n1-0-2|n1-1-2|M1|BY|0|[0, 0, 1]|
|c1-1-2|column|n1-1-1|n1-1-2|M1|C1|0|[1, 0, 0]|
|y1-1-2|beam|n1-1-2|n1-2-2|M1|BY|0|[0, 0, 1]|
|c1-2-2|column|n1-2-1|n1-2-2|M1|C1|0|[1, 0, 0]|

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

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fx|fy|
|---|---|---|---|---|
|D-1 → n1-2-2|global|nodal|20|15|

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
|interactions|["Report each member ID, ordered endpoints, reference vector, roll angle in degrees and final local x/y/z unit vectors in global XYZ."]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case-D-node-n1-2-2-ux|node|n1-2-2|ux|m|—|—|
|case-D-node-n1-2-2-uy|node|n1-2-2|uy|m|—|—|
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
|case-D-member-c0-2-1-s0-right-N|member|c0-2-1|N|kN|0|right|
|case-D-member-c0-2-1-s0-right-V2|member|c0-2-1|V2|kN|0|right|
|case-D-member-c0-2-1-s0-right-V3|member|c0-2-1|V3|kN|0|right|
|case-D-member-c0-2-1-s0-right-T|member|c0-2-1|T|kN.m|0|right|
|case-D-member-c0-2-1-s0-right-M2|member|c0-2-1|M2|kN.m|0|right|
|case-D-member-c0-2-1-s0-right-M3|member|c0-2-1|M3|kN.m|0|right|
|case-D-member-c0-2-1-s3.6-left-N|member|c0-2-1|N|kN|3.6|left|
|case-D-member-c0-2-1-s3.6-left-V2|member|c0-2-1|V2|kN|3.6|left|
|case-D-member-c0-2-1-s3.6-left-V3|member|c0-2-1|V3|kN|3.6|left|
|case-D-member-c0-2-1-s3.6-left-T|member|c0-2-1|T|kN.m|3.6|left|
|case-D-member-c0-2-1-s3.6-left-M2|member|c0-2-1|M2|kN.m|3.6|left|
|case-D-member-c0-2-1-s3.6-left-M3|member|c0-2-1|M3|kN.m|3.6|left|
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
|case-D-member-c1-2-1-s0-right-N|member|c1-2-1|N|kN|0|right|
|case-D-member-c1-2-1-s0-right-V2|member|c1-2-1|V2|kN|0|right|
|case-D-member-c1-2-1-s0-right-V3|member|c1-2-1|V3|kN|0|right|
|case-D-member-c1-2-1-s0-right-T|member|c1-2-1|T|kN.m|0|right|
|case-D-member-c1-2-1-s0-right-M2|member|c1-2-1|M2|kN.m|0|right|
|case-D-member-c1-2-1-s0-right-M3|member|c1-2-1|M3|kN.m|0|right|
|case-D-member-c1-2-1-s3.6-left-N|member|c1-2-1|N|kN|3.6|left|
|case-D-member-c1-2-1-s3.6-left-V2|member|c1-2-1|V2|kN|3.6|left|
|case-D-member-c1-2-1-s3.6-left-V3|member|c1-2-1|V3|kN|3.6|left|
|case-D-member-c1-2-1-s3.6-left-T|member|c1-2-1|T|kN.m|3.6|left|
|case-D-member-c1-2-1-s3.6-left-M2|member|c1-2-1|M2|kN.m|3.6|left|
|case-D-member-c1-2-1-s3.6-left-M3|member|c1-2-1|M3|kN.m|3.6|left|
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
|case-D-member-c0-2-2-s0-right-N|member|c0-2-2|N|kN|0|right|
|case-D-member-c0-2-2-s0-right-V2|member|c0-2-2|V2|kN|0|right|
|case-D-member-c0-2-2-s0-right-V3|member|c0-2-2|V3|kN|0|right|
|case-D-member-c0-2-2-s0-right-T|member|c0-2-2|T|kN.m|0|right|
|case-D-member-c0-2-2-s0-right-M2|member|c0-2-2|M2|kN.m|0|right|
|case-D-member-c0-2-2-s0-right-M3|member|c0-2-2|M3|kN.m|0|right|
|case-D-member-c0-2-2-s3.6-left-N|member|c0-2-2|N|kN|3.6|left|
|case-D-member-c0-2-2-s3.6-left-V2|member|c0-2-2|V2|kN|3.6|left|
|case-D-member-c0-2-2-s3.6-left-V3|member|c0-2-2|V3|kN|3.6|left|
|case-D-member-c0-2-2-s3.6-left-T|member|c0-2-2|T|kN.m|3.6|left|
|case-D-member-c0-2-2-s3.6-left-M2|member|c0-2-2|M2|kN.m|3.6|left|
|case-D-member-c0-2-2-s3.6-left-M3|member|c0-2-2|M3|kN.m|3.6|left|
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
|case-D-member-c1-2-2-s0-right-N|member|c1-2-2|N|kN|0|right|
|case-D-member-c1-2-2-s0-right-V2|member|c1-2-2|V2|kN|0|right|
|case-D-member-c1-2-2-s0-right-V3|member|c1-2-2|V3|kN|0|right|
|case-D-member-c1-2-2-s0-right-T|member|c1-2-2|T|kN.m|0|right|
|case-D-member-c1-2-2-s0-right-M2|member|c1-2-2|M2|kN.m|0|right|
|case-D-member-c1-2-2-s0-right-M3|member|c1-2-2|M3|kN.m|0|right|
|case-D-member-c1-2-2-s3.6-left-N|member|c1-2-2|N|kN|3.6|left|
|case-D-member-c1-2-2-s3.6-left-V2|member|c1-2-2|V2|kN|3.6|left|
|case-D-member-c1-2-2-s3.6-left-V3|member|c1-2-2|V3|kN|3.6|left|
|case-D-member-c1-2-2-s3.6-left-T|member|c1-2-2|T|kN.m|3.6|left|
|case-D-member-c1-2-2-s3.6-left-M2|member|c1-2-2|M2|kN.m|3.6|left|
|case-D-member-c1-2-2-s3.6-left-M3|member|c1-2-2|M3|kN.m|3.6|left|
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

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.

## Local axes

LOCAL AXIS APPENDIX
All vectors are in global XYZ. B is along local y; H is along local z. Section rolls are in degrees, result rotations in radians.
Local x follows the ordered endpoints. Before roll, y=unit(reference cross x), z=x cross y. Positive roll theta gives y_new=cos(theta)*y+sin(theta)*z and z_new=-sin(theta)*y+cos(theta)*z.
All vertical columns use reference=(1,0,0). The unrolled basis is x=(0,0,1), y=(0,-1,0), z=(1,0,0).
Only c0-0-1, c1-0-1, c0-0-2 and c1-0-2 have roll=90, hence x=(0,0,1), y=(1,0,0), z=(0,1,0). All other columns have roll=0.
C1 is the same 400x500 mm rectangle on every column; Iy=0.004166666666666667 m^4 and Iz=0.002666666666666667 m^4. Do not swap these section values in addition to rolling.
X beams: reference=(0,0,1), roll=0, x=(1,0,0), y=(0,1,0), z=(0,0,1).
Y beams: reference=(0,0,1), roll=0, x=(0,1,0), y=(-1,0,0), z=(0,0,1).
There is no gravity line load, area load or self-weight load in this task.
