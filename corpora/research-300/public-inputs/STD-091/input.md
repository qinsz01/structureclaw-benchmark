## Numerical inputs

|Field|Value|
|---|---|
|title|完整数值输入附表|
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
|c0-0-1|column|n0-0-0|n0-0-1|M1|C1|0|[1, 0, 0]|
|x0-0-1|beam|n0-0-1|n1-0-1|M1|BX|0|[0, 0, 1]|
|y0-0-1|beam|n0-0-1|n0-1-1|M1|BY|0|[0, 0, 1]|
|c0-1-1|column|n0-1-0|n0-1-1|M1|C1|0|[1, 0, 0]|
|x0-1-1|beam|n0-1-1|n1-1-1|M1|BX|0|[0, 0, 1]|
|y0-1-1|beam|n0-1-1|n0-2-1|M1|BY|0|[0, 0, 1]|
|c0-2-1|column|n0-2-0|n0-2-1|M1|C1|0|[1, 0, 0]|
|x0-2-1|beam|n0-2-1|n1-2-1|M1|BX|0|[0, 0, 1]|
|c1-0-1|column|n1-0-0|n1-0-1|M1|C1|0|[1, 0, 0]|
|x1-0-1|beam|n1-0-1|n2-0-1|M1|BX|0|[0, 0, 1]|
|y1-0-1|beam|n1-0-1|n1-1-1|M1|BY|0|[0, 0, 1]|
|c1-1-1|column|n1-1-0|n1-1-1|M1|C1|0|[1, 0, 0]|
|x1-1-1|beam|n1-1-1|n2-1-1|M1|BX|0|[0, 0, 1]|
|y1-1-1|beam|n1-1-1|n1-2-1|M1|BY|0|[0, 0, 1]|
|c1-2-1|column|n1-2-0|n1-2-1|M1|C1|0|[1, 0, 0]|
|x1-2-1|beam|n1-2-1|n2-2-1|M1|BX|0|[0, 0, 1]|
|c2-0-1|column|n2-0-0|n2-0-1|M1|C1|0|[1, 0, 0]|
|y2-0-1|beam|n2-0-1|n2-1-1|M1|BY|0|[0, 0, 1]|
|c2-1-1|column|n2-1-0|n2-1-1|M1|C1|0|[1, 0, 0]|
|y2-1-1|beam|n2-1-1|n2-2-1|M1|BY|0|[0, 0, 1]|
|c2-2-1|column|n2-2-0|n2-2-1|M1|C1|0|[1, 0, 0]|
|c0-0-2|column|n0-0-1|n0-0-2|M1|C1|0|[1, 0, 0]|
|x0-0-2|beam|n0-0-2|n1-0-2|M1|BX|0|[0, 0, 1]|
|y0-0-2|beam|n0-0-2|n0-1-2|M1|BY|0|[0, 0, 1]|
|c0-1-2|column|n0-1-1|n0-1-2|M1|C1|0|[1, 0, 0]|
|x0-1-2|beam|n0-1-2|n1-1-2|M1|BX|0|[0, 0, 1]|
|y0-1-2|beam|n0-1-2|n0-2-2|M1|BY|0|[0, 0, 1]|
|c0-2-2|column|n0-2-1|n0-2-2|M1|C1|0|[1, 0, 0]|
|x0-2-2|beam|n0-2-2|n1-2-2|M1|BX|0|[0, 0, 1]|
|c1-0-2|column|n1-0-1|n1-0-2|M1|C1|0|[1, 0, 0]|
|x1-0-2|beam|n1-0-2|n2-0-2|M1|BX|0|[0, 0, 1]|
|y1-0-2|beam|n1-0-2|n1-1-2|M1|BY|0|[0, 0, 1]|
|c1-1-2|column|n1-1-1|n1-1-2|M1|C1|0|[1, 0, 0]|
|x1-1-2|beam|n1-1-2|n2-1-2|M1|BX|0|[0, 0, 1]|
|y1-1-2|beam|n1-1-2|n1-2-2|M1|BY|0|[0, 0, 1]|
|c1-2-2|column|n1-2-1|n1-2-2|M1|C1|0|[1, 0, 0]|
|x1-2-2|beam|n1-2-2|n2-2-2|M1|BX|0|[0, 0, 1]|
|c2-0-2|column|n2-0-1|n2-0-2|M1|C1|0|[1, 0, 0]|
|y2-0-2|beam|n2-0-2|n2-1-2|M1|BY|0|[0, 0, 1]|
|c2-1-2|column|n2-1-1|n2-1-2|M1|C1|0|[1, 0, 0]|
|y2-1-2|beam|n2-1-2|n2-2-2|M1|BY|0|[0, 0, 1]|
|c2-2-2|column|n2-2-1|n2-2-2|M1|C1|0|[1, 0, 0]|

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

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-1 → x0-0-1, D-2 → y0-0-1, D-3 → x0-1-1, D-4 → y0-1-1, D-5 → x0-2-1, D-6 → x1-0-1, D-7 → y1-0-1, D-8 → x1-1-1, D-9 → y1-1-1, D-10 → x1-2-1, D-11 → y2-0-1, D-12 → y2-1-1, D-13 → x0-0-2, D-14 → y0-0-2, D-15 → x0-1-2, D-16 → y0-1-2, D-17 → x0-2-2, D-18 → x1-0-2, D-19 → y1-0-2, D-20 → x1-1-2, D-21 → y1-1-2, D-22 → x1-2-2, D-23 → y2-0-2, D-24 → y2-1-2|global|distributed|-8|

## Numerical inputs — Load cases — L

|Field|Value|
|---|---|
|id|L|
|type|live|

## Numerical inputs — Load cases — L — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|L-1 → x0-0-2, L-2 → x0-1-2, L-3 → y0-0-2, L-4 → y1-0-2|global|distributed|-6|

## Numerical inputs — Load combinations

|id|factors · L|
|---|---|
|D|—|
|D+L|1|

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
|derived|[]|
|figures|[]|
|interactions|["工况/组合索引表：明确区分case D、case L、combination D和combination D+L，并关联各原生工况/组合结果标识。"]|

## Requested outputs — Quantities

|id|selection · id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|---|
|combination-D-node-n0-0-2-ux|D|node|n0-0-2|ux|m|—|—|
|combination-D-node-n0-0-2-uy|D|node|n0-0-2|uy|m|—|—|
|combination-D-node-n0-0-2-uz|D|node|n0-0-2|uz|m|—|—|
|combination-D-node-n1-0-2-ux|D|node|n1-0-2|ux|m|—|—|
|combination-D-node-n1-0-2-uy|D|node|n1-0-2|uy|m|—|—|
|combination-D-node-n1-0-2-uz|D|node|n1-0-2|uz|m|—|—|
|combination-D-node-n0-1-2-ux|D|node|n0-1-2|ux|m|—|—|
|combination-D-node-n0-1-2-uy|D|node|n0-1-2|uy|m|—|—|
|combination-D-node-n0-1-2-uz|D|node|n0-1-2|uz|m|—|—|
|combination-D-node-n1-1-2-ux|D|node|n1-1-2|ux|m|—|—|
|combination-D-node-n1-1-2-uy|D|node|n1-1-2|uy|m|—|—|
|combination-D-node-n1-1-2-uz|D|node|n1-1-2|uz|m|—|—|
|combination-D-node-n2-1-2-ux|D|node|n2-1-2|ux|m|—|—|
|combination-D-node-n2-1-2-uy|D|node|n2-1-2|uy|m|—|—|
|combination-D-node-n2-1-2-uz|D|node|n2-1-2|uz|m|—|—|
|combination-D-node-n1-2-2-ux|D|node|n1-2-2|ux|m|—|—|
|combination-D-node-n1-2-2-uy|D|node|n1-2-2|uy|m|—|—|
|combination-D-node-n1-2-2-uz|D|node|n1-2-2|uz|m|—|—|
|combination-D-node-n2-2-2-ux|D|node|n2-2-2|ux|m|—|—|
|combination-D-node-n2-2-2-uy|D|node|n2-2-2|uy|m|—|—|
|combination-D-node-n2-2-2-uz|D|node|n2-2-2|uz|m|—|—|
|combination-D-member-x0-0-2-s0-right-N|D|member|x0-0-2|N|kN|0|right|
|combination-D-member-x0-0-2-s0-right-V2|D|member|x0-0-2|V2|kN|0|right|
|combination-D-member-x0-0-2-s0-right-V3|D|member|x0-0-2|V3|kN|0|right|
|combination-D-member-x0-0-2-s0-right-T|D|member|x0-0-2|T|kN.m|0|right|
|combination-D-member-x0-0-2-s0-right-M2|D|member|x0-0-2|M2|kN.m|0|right|
|combination-D-member-x0-0-2-s0-right-M3|D|member|x0-0-2|M3|kN.m|0|right|
|combination-D-member-x0-0-2-s6-left-N|D|member|x0-0-2|N|kN|6.0|left|
|combination-D-member-x0-0-2-s6-left-V2|D|member|x0-0-2|V2|kN|6.0|left|
|combination-D-member-x0-0-2-s6-left-V3|D|member|x0-0-2|V3|kN|6.0|left|
|combination-D-member-x0-0-2-s6-left-T|D|member|x0-0-2|T|kN.m|6.0|left|
|combination-D-member-x0-0-2-s6-left-M2|D|member|x0-0-2|M2|kN.m|6.0|left|
|combination-D-member-x0-0-2-s6-left-M3|D|member|x0-0-2|M3|kN.m|6.0|left|
|combination-D-member-x0-1-2-s0-right-N|D|member|x0-1-2|N|kN|0|right|
|combination-D-member-x0-1-2-s0-right-V2|D|member|x0-1-2|V2|kN|0|right|
|combination-D-member-x0-1-2-s0-right-V3|D|member|x0-1-2|V3|kN|0|right|
|combination-D-member-x0-1-2-s0-right-T|D|member|x0-1-2|T|kN.m|0|right|
|combination-D-member-x0-1-2-s0-right-M2|D|member|x0-1-2|M2|kN.m|0|right|
|combination-D-member-x0-1-2-s0-right-M3|D|member|x0-1-2|M3|kN.m|0|right|
|combination-D-member-x0-1-2-s6-left-N|D|member|x0-1-2|N|kN|6.0|left|
|combination-D-member-x0-1-2-s6-left-V2|D|member|x0-1-2|V2|kN|6.0|left|
|combination-D-member-x0-1-2-s6-left-V3|D|member|x0-1-2|V3|kN|6.0|left|
|combination-D-member-x0-1-2-s6-left-T|D|member|x0-1-2|T|kN.m|6.0|left|
|combination-D-member-x0-1-2-s6-left-M2|D|member|x0-1-2|M2|kN.m|6.0|left|
|combination-D-member-x0-1-2-s6-left-M3|D|member|x0-1-2|M3|kN.m|6.0|left|
|combination-D-member-y0-0-2-s0-right-N|D|member|y0-0-2|N|kN|0|right|
|combination-D-member-y0-0-2-s0-right-V2|D|member|y0-0-2|V2|kN|0|right|
|combination-D-member-y0-0-2-s0-right-V3|D|member|y0-0-2|V3|kN|0|right|
|combination-D-member-y0-0-2-s0-right-T|D|member|y0-0-2|T|kN.m|0|right|
|combination-D-member-y0-0-2-s0-right-M2|D|member|y0-0-2|M2|kN.m|0|right|
|combination-D-member-y0-0-2-s0-right-M3|D|member|y0-0-2|M3|kN.m|0|right|
|combination-D-member-y0-0-2-s5-left-N|D|member|y0-0-2|N|kN|5.0|left|
|combination-D-member-y0-0-2-s5-left-V2|D|member|y0-0-2|V2|kN|5.0|left|
|combination-D-member-y0-0-2-s5-left-V3|D|member|y0-0-2|V3|kN|5.0|left|
|combination-D-member-y0-0-2-s5-left-T|D|member|y0-0-2|T|kN.m|5.0|left|
|combination-D-member-y0-0-2-s5-left-M2|D|member|y0-0-2|M2|kN.m|5.0|left|
|combination-D-member-y0-0-2-s5-left-M3|D|member|y0-0-2|M3|kN.m|5.0|left|
|combination-D-member-y1-0-2-s0-right-N|D|member|y1-0-2|N|kN|0|right|
|combination-D-member-y1-0-2-s0-right-V2|D|member|y1-0-2|V2|kN|0|right|
|combination-D-member-y1-0-2-s0-right-V3|D|member|y1-0-2|V3|kN|0|right|
|combination-D-member-y1-0-2-s0-right-T|D|member|y1-0-2|T|kN.m|0|right|
|combination-D-member-y1-0-2-s0-right-M2|D|member|y1-0-2|M2|kN.m|0|right|
|combination-D-member-y1-0-2-s0-right-M3|D|member|y1-0-2|M3|kN.m|0|right|
|combination-D-member-y1-0-2-s5-left-N|D|member|y1-0-2|N|kN|5.0|left|
|combination-D-member-y1-0-2-s5-left-V2|D|member|y1-0-2|V2|kN|5.0|left|
|combination-D-member-y1-0-2-s5-left-V3|D|member|y1-0-2|V3|kN|5.0|left|
|combination-D-member-y1-0-2-s5-left-T|D|member|y1-0-2|T|kN.m|5.0|left|
|combination-D-member-y1-0-2-s5-left-M2|D|member|y1-0-2|M2|kN.m|5.0|left|
|combination-D-member-y1-0-2-s5-left-M3|D|member|y1-0-2|M3|kN.m|5.0|left|
|combination-D-node-n0-0-0-Fx|D|node|n0-0-0|Fx|kN|—|—|
|combination-D-node-n0-0-0-Fy|D|node|n0-0-0|Fy|kN|—|—|
|combination-D-node-n0-0-0-Fz|D|node|n0-0-0|Fz|kN|—|—|
|combination-D-node-n0-0-0-Mx|D|node|n0-0-0|Mx|kN.m|—|—|
|combination-D-node-n0-0-0-My|D|node|n0-0-0|My|kN.m|—|—|
|combination-D-node-n0-0-0-Mz|D|node|n0-0-0|Mz|kN.m|—|—|
|combination-D-node-n0-1-0-Fx|D|node|n0-1-0|Fx|kN|—|—|
|combination-D-node-n0-1-0-Fy|D|node|n0-1-0|Fy|kN|—|—|
|combination-D-node-n0-1-0-Fz|D|node|n0-1-0|Fz|kN|—|—|
|combination-D-node-n0-1-0-Mx|D|node|n0-1-0|Mx|kN.m|—|—|
|combination-D-node-n0-1-0-My|D|node|n0-1-0|My|kN.m|—|—|
|combination-D-node-n0-1-0-Mz|D|node|n0-1-0|Mz|kN.m|—|—|
|combination-D-node-n0-2-0-Fx|D|node|n0-2-0|Fx|kN|—|—|
|combination-D-node-n0-2-0-Fy|D|node|n0-2-0|Fy|kN|—|—|
|combination-D-node-n0-2-0-Fz|D|node|n0-2-0|Fz|kN|—|—|
|combination-D-node-n0-2-0-Mx|D|node|n0-2-0|Mx|kN.m|—|—|
|combination-D-node-n0-2-0-My|D|node|n0-2-0|My|kN.m|—|—|
|combination-D-node-n0-2-0-Mz|D|node|n0-2-0|Mz|kN.m|—|—|
|combination-D-node-n1-0-0-Fx|D|node|n1-0-0|Fx|kN|—|—|
|combination-D-node-n1-0-0-Fy|D|node|n1-0-0|Fy|kN|—|—|
|combination-D-node-n1-0-0-Fz|D|node|n1-0-0|Fz|kN|—|—|
|combination-D-node-n1-0-0-Mx|D|node|n1-0-0|Mx|kN.m|—|—|
|combination-D-node-n1-0-0-My|D|node|n1-0-0|My|kN.m|—|—|
|combination-D-node-n1-0-0-Mz|D|node|n1-0-0|Mz|kN.m|—|—|
|combination-D-node-n1-1-0-Fx|D|node|n1-1-0|Fx|kN|—|—|
|combination-D-node-n1-1-0-Fy|D|node|n1-1-0|Fy|kN|—|—|
|combination-D-node-n1-1-0-Fz|D|node|n1-1-0|Fz|kN|—|—|
|combination-D-node-n1-1-0-Mx|D|node|n1-1-0|Mx|kN.m|—|—|
|combination-D-node-n1-1-0-My|D|node|n1-1-0|My|kN.m|—|—|
|combination-D-node-n1-1-0-Mz|D|node|n1-1-0|Mz|kN.m|—|—|
|combination-D-node-n1-2-0-Fx|D|node|n1-2-0|Fx|kN|—|—|
|combination-D-node-n1-2-0-Fy|D|node|n1-2-0|Fy|kN|—|—|
|combination-D-node-n1-2-0-Fz|D|node|n1-2-0|Fz|kN|—|—|
|combination-D-node-n1-2-0-Mx|D|node|n1-2-0|Mx|kN.m|—|—|
|combination-D-node-n1-2-0-My|D|node|n1-2-0|My|kN.m|—|—|
|combination-D-node-n1-2-0-Mz|D|node|n1-2-0|Mz|kN.m|—|—|
|combination-D-node-n2-0-0-Fx|D|node|n2-0-0|Fx|kN|—|—|
|combination-D-node-n2-0-0-Fy|D|node|n2-0-0|Fy|kN|—|—|
|combination-D-node-n2-0-0-Fz|D|node|n2-0-0|Fz|kN|—|—|
|combination-D-node-n2-0-0-Mx|D|node|n2-0-0|Mx|kN.m|—|—|
|combination-D-node-n2-0-0-My|D|node|n2-0-0|My|kN.m|—|—|
|combination-D-node-n2-0-0-Mz|D|node|n2-0-0|Mz|kN.m|—|—|
|combination-D-node-n2-1-0-Fx|D|node|n2-1-0|Fx|kN|—|—|
|combination-D-node-n2-1-0-Fy|D|node|n2-1-0|Fy|kN|—|—|
|combination-D-node-n2-1-0-Fz|D|node|n2-1-0|Fz|kN|—|—|
|combination-D-node-n2-1-0-Mx|D|node|n2-1-0|Mx|kN.m|—|—|
|combination-D-node-n2-1-0-My|D|node|n2-1-0|My|kN.m|—|—|
|combination-D-node-n2-1-0-Mz|D|node|n2-1-0|Mz|kN.m|—|—|
|combination-D-node-n2-2-0-Fx|D|node|n2-2-0|Fx|kN|—|—|
|combination-D-node-n2-2-0-Fy|D|node|n2-2-0|Fy|kN|—|—|
|combination-D-node-n2-2-0-Fz|D|node|n2-2-0|Fz|kN|—|—|
|combination-D-node-n2-2-0-Mx|D|node|n2-2-0|Mx|kN.m|—|—|
|combination-D-node-n2-2-0-My|D|node|n2-2-0|My|kN.m|—|—|
|combination-D-node-n2-2-0-Mz|D|node|n2-2-0|Mz|kN.m|—|—|
|combination-D+L-node-n0-0-2-ux|D+L|node|n0-0-2|ux|m|—|—|
|combination-D+L-node-n0-0-2-uy|D+L|node|n0-0-2|uy|m|—|—|
|combination-D+L-node-n0-0-2-uz|D+L|node|n0-0-2|uz|m|—|—|
|combination-D+L-node-n1-0-2-ux|D+L|node|n1-0-2|ux|m|—|—|
|combination-D+L-node-n1-0-2-uy|D+L|node|n1-0-2|uy|m|—|—|
|combination-D+L-node-n1-0-2-uz|D+L|node|n1-0-2|uz|m|—|—|
|combination-D+L-node-n0-1-2-ux|D+L|node|n0-1-2|ux|m|—|—|
|combination-D+L-node-n0-1-2-uy|D+L|node|n0-1-2|uy|m|—|—|
|combination-D+L-node-n0-1-2-uz|D+L|node|n0-1-2|uz|m|—|—|
|combination-D+L-node-n1-1-2-ux|D+L|node|n1-1-2|ux|m|—|—|
|combination-D+L-node-n1-1-2-uy|D+L|node|n1-1-2|uy|m|—|—|
|combination-D+L-node-n1-1-2-uz|D+L|node|n1-1-2|uz|m|—|—|
|combination-D+L-node-n2-1-2-ux|D+L|node|n2-1-2|ux|m|—|—|
|combination-D+L-node-n2-1-2-uy|D+L|node|n2-1-2|uy|m|—|—|
|combination-D+L-node-n2-1-2-uz|D+L|node|n2-1-2|uz|m|—|—|
|combination-D+L-node-n1-2-2-ux|D+L|node|n1-2-2|ux|m|—|—|
|combination-D+L-node-n1-2-2-uy|D+L|node|n1-2-2|uy|m|—|—|
|combination-D+L-node-n1-2-2-uz|D+L|node|n1-2-2|uz|m|—|—|
|combination-D+L-node-n2-2-2-ux|D+L|node|n2-2-2|ux|m|—|—|
|combination-D+L-node-n2-2-2-uy|D+L|node|n2-2-2|uy|m|—|—|
|combination-D+L-node-n2-2-2-uz|D+L|node|n2-2-2|uz|m|—|—|
|combination-D+L-member-x0-0-2-s0-right-N|D+L|member|x0-0-2|N|kN|0|right|
|combination-D+L-member-x0-0-2-s0-right-V2|D+L|member|x0-0-2|V2|kN|0|right|
|combination-D+L-member-x0-0-2-s0-right-V3|D+L|member|x0-0-2|V3|kN|0|right|
|combination-D+L-member-x0-0-2-s0-right-T|D+L|member|x0-0-2|T|kN.m|0|right|
|combination-D+L-member-x0-0-2-s0-right-M2|D+L|member|x0-0-2|M2|kN.m|0|right|
|combination-D+L-member-x0-0-2-s0-right-M3|D+L|member|x0-0-2|M3|kN.m|0|right|
|combination-D+L-member-x0-0-2-s6-left-N|D+L|member|x0-0-2|N|kN|6.0|left|
|combination-D+L-member-x0-0-2-s6-left-V2|D+L|member|x0-0-2|V2|kN|6.0|left|
|combination-D+L-member-x0-0-2-s6-left-V3|D+L|member|x0-0-2|V3|kN|6.0|left|
|combination-D+L-member-x0-0-2-s6-left-T|D+L|member|x0-0-2|T|kN.m|6.0|left|
|combination-D+L-member-x0-0-2-s6-left-M2|D+L|member|x0-0-2|M2|kN.m|6.0|left|
|combination-D+L-member-x0-0-2-s6-left-M3|D+L|member|x0-0-2|M3|kN.m|6.0|left|
|combination-D+L-member-x0-1-2-s0-right-N|D+L|member|x0-1-2|N|kN|0|right|
|combination-D+L-member-x0-1-2-s0-right-V2|D+L|member|x0-1-2|V2|kN|0|right|
|combination-D+L-member-x0-1-2-s0-right-V3|D+L|member|x0-1-2|V3|kN|0|right|
|combination-D+L-member-x0-1-2-s0-right-T|D+L|member|x0-1-2|T|kN.m|0|right|
|combination-D+L-member-x0-1-2-s0-right-M2|D+L|member|x0-1-2|M2|kN.m|0|right|
|combination-D+L-member-x0-1-2-s0-right-M3|D+L|member|x0-1-2|M3|kN.m|0|right|
|combination-D+L-member-x0-1-2-s6-left-N|D+L|member|x0-1-2|N|kN|6.0|left|
|combination-D+L-member-x0-1-2-s6-left-V2|D+L|member|x0-1-2|V2|kN|6.0|left|
|combination-D+L-member-x0-1-2-s6-left-V3|D+L|member|x0-1-2|V3|kN|6.0|left|
|combination-D+L-member-x0-1-2-s6-left-T|D+L|member|x0-1-2|T|kN.m|6.0|left|
|combination-D+L-member-x0-1-2-s6-left-M2|D+L|member|x0-1-2|M2|kN.m|6.0|left|
|combination-D+L-member-x0-1-2-s6-left-M3|D+L|member|x0-1-2|M3|kN.m|6.0|left|
|combination-D+L-member-y0-0-2-s0-right-N|D+L|member|y0-0-2|N|kN|0|right|
|combination-D+L-member-y0-0-2-s0-right-V2|D+L|member|y0-0-2|V2|kN|0|right|
|combination-D+L-member-y0-0-2-s0-right-V3|D+L|member|y0-0-2|V3|kN|0|right|
|combination-D+L-member-y0-0-2-s0-right-T|D+L|member|y0-0-2|T|kN.m|0|right|
|combination-D+L-member-y0-0-2-s0-right-M2|D+L|member|y0-0-2|M2|kN.m|0|right|
|combination-D+L-member-y0-0-2-s0-right-M3|D+L|member|y0-0-2|M3|kN.m|0|right|
|combination-D+L-member-y0-0-2-s5-left-N|D+L|member|y0-0-2|N|kN|5.0|left|
|combination-D+L-member-y0-0-2-s5-left-V2|D+L|member|y0-0-2|V2|kN|5.0|left|
|combination-D+L-member-y0-0-2-s5-left-V3|D+L|member|y0-0-2|V3|kN|5.0|left|
|combination-D+L-member-y0-0-2-s5-left-T|D+L|member|y0-0-2|T|kN.m|5.0|left|
|combination-D+L-member-y0-0-2-s5-left-M2|D+L|member|y0-0-2|M2|kN.m|5.0|left|
|combination-D+L-member-y0-0-2-s5-left-M3|D+L|member|y0-0-2|M3|kN.m|5.0|left|
|combination-D+L-member-y1-0-2-s0-right-N|D+L|member|y1-0-2|N|kN|0|right|
|combination-D+L-member-y1-0-2-s0-right-V2|D+L|member|y1-0-2|V2|kN|0|right|
|combination-D+L-member-y1-0-2-s0-right-V3|D+L|member|y1-0-2|V3|kN|0|right|
|combination-D+L-member-y1-0-2-s0-right-T|D+L|member|y1-0-2|T|kN.m|0|right|
|combination-D+L-member-y1-0-2-s0-right-M2|D+L|member|y1-0-2|M2|kN.m|0|right|
|combination-D+L-member-y1-0-2-s0-right-M3|D+L|member|y1-0-2|M3|kN.m|0|right|
|combination-D+L-member-y1-0-2-s5-left-N|D+L|member|y1-0-2|N|kN|5.0|left|
|combination-D+L-member-y1-0-2-s5-left-V2|D+L|member|y1-0-2|V2|kN|5.0|left|
|combination-D+L-member-y1-0-2-s5-left-V3|D+L|member|y1-0-2|V3|kN|5.0|left|
|combination-D+L-member-y1-0-2-s5-left-T|D+L|member|y1-0-2|T|kN.m|5.0|left|
|combination-D+L-member-y1-0-2-s5-left-M2|D+L|member|y1-0-2|M2|kN.m|5.0|left|
|combination-D+L-member-y1-0-2-s5-left-M3|D+L|member|y1-0-2|M3|kN.m|5.0|left|
|combination-D+L-node-n0-0-0-Fx|D+L|node|n0-0-0|Fx|kN|—|—|
|combination-D+L-node-n0-0-0-Fy|D+L|node|n0-0-0|Fy|kN|—|—|
|combination-D+L-node-n0-0-0-Fz|D+L|node|n0-0-0|Fz|kN|—|—|
|combination-D+L-node-n0-0-0-Mx|D+L|node|n0-0-0|Mx|kN.m|—|—|
|combination-D+L-node-n0-0-0-My|D+L|node|n0-0-0|My|kN.m|—|—|
|combination-D+L-node-n0-0-0-Mz|D+L|node|n0-0-0|Mz|kN.m|—|—|
|combination-D+L-node-n0-1-0-Fx|D+L|node|n0-1-0|Fx|kN|—|—|
|combination-D+L-node-n0-1-0-Fy|D+L|node|n0-1-0|Fy|kN|—|—|
|combination-D+L-node-n0-1-0-Fz|D+L|node|n0-1-0|Fz|kN|—|—|
|combination-D+L-node-n0-1-0-Mx|D+L|node|n0-1-0|Mx|kN.m|—|—|
|combination-D+L-node-n0-1-0-My|D+L|node|n0-1-0|My|kN.m|—|—|
|combination-D+L-node-n0-1-0-Mz|D+L|node|n0-1-0|Mz|kN.m|—|—|
|combination-D+L-node-n0-2-0-Fx|D+L|node|n0-2-0|Fx|kN|—|—|
|combination-D+L-node-n0-2-0-Fy|D+L|node|n0-2-0|Fy|kN|—|—|
|combination-D+L-node-n0-2-0-Fz|D+L|node|n0-2-0|Fz|kN|—|—|
|combination-D+L-node-n0-2-0-Mx|D+L|node|n0-2-0|Mx|kN.m|—|—|
|combination-D+L-node-n0-2-0-My|D+L|node|n0-2-0|My|kN.m|—|—|
|combination-D+L-node-n0-2-0-Mz|D+L|node|n0-2-0|Mz|kN.m|—|—|
|combination-D+L-node-n1-0-0-Fx|D+L|node|n1-0-0|Fx|kN|—|—|
|combination-D+L-node-n1-0-0-Fy|D+L|node|n1-0-0|Fy|kN|—|—|
|combination-D+L-node-n1-0-0-Fz|D+L|node|n1-0-0|Fz|kN|—|—|
|combination-D+L-node-n1-0-0-Mx|D+L|node|n1-0-0|Mx|kN.m|—|—|
|combination-D+L-node-n1-0-0-My|D+L|node|n1-0-0|My|kN.m|—|—|
|combination-D+L-node-n1-0-0-Mz|D+L|node|n1-0-0|Mz|kN.m|—|—|
|combination-D+L-node-n1-1-0-Fx|D+L|node|n1-1-0|Fx|kN|—|—|
|combination-D+L-node-n1-1-0-Fy|D+L|node|n1-1-0|Fy|kN|—|—|
|combination-D+L-node-n1-1-0-Fz|D+L|node|n1-1-0|Fz|kN|—|—|
|combination-D+L-node-n1-1-0-Mx|D+L|node|n1-1-0|Mx|kN.m|—|—|
|combination-D+L-node-n1-1-0-My|D+L|node|n1-1-0|My|kN.m|—|—|
|combination-D+L-node-n1-1-0-Mz|D+L|node|n1-1-0|Mz|kN.m|—|—|
|combination-D+L-node-n1-2-0-Fx|D+L|node|n1-2-0|Fx|kN|—|—|
|combination-D+L-node-n1-2-0-Fy|D+L|node|n1-2-0|Fy|kN|—|—|
|combination-D+L-node-n1-2-0-Fz|D+L|node|n1-2-0|Fz|kN|—|—|
|combination-D+L-node-n1-2-0-Mx|D+L|node|n1-2-0|Mx|kN.m|—|—|
|combination-D+L-node-n1-2-0-My|D+L|node|n1-2-0|My|kN.m|—|—|
|combination-D+L-node-n1-2-0-Mz|D+L|node|n1-2-0|Mz|kN.m|—|—|
|combination-D+L-node-n2-0-0-Fx|D+L|node|n2-0-0|Fx|kN|—|—|
|combination-D+L-node-n2-0-0-Fy|D+L|node|n2-0-0|Fy|kN|—|—|
|combination-D+L-node-n2-0-0-Fz|D+L|node|n2-0-0|Fz|kN|—|—|
|combination-D+L-node-n2-0-0-Mx|D+L|node|n2-0-0|Mx|kN.m|—|—|
|combination-D+L-node-n2-0-0-My|D+L|node|n2-0-0|My|kN.m|—|—|
|combination-D+L-node-n2-0-0-Mz|D+L|node|n2-0-0|Mz|kN.m|—|—|
|combination-D+L-node-n2-1-0-Fx|D+L|node|n2-1-0|Fx|kN|—|—|
|combination-D+L-node-n2-1-0-Fy|D+L|node|n2-1-0|Fy|kN|—|—|
|combination-D+L-node-n2-1-0-Fz|D+L|node|n2-1-0|Fz|kN|—|—|
|combination-D+L-node-n2-1-0-Mx|D+L|node|n2-1-0|Mx|kN.m|—|—|
|combination-D+L-node-n2-1-0-My|D+L|node|n2-1-0|My|kN.m|—|—|
|combination-D+L-node-n2-1-0-Mz|D+L|node|n2-1-0|Mz|kN.m|—|—|
|combination-D+L-node-n2-2-0-Fx|D+L|node|n2-2-0|Fx|kN|—|—|
|combination-D+L-node-n2-2-0-Fy|D+L|node|n2-2-0|Fy|kN|—|—|
|combination-D+L-node-n2-2-0-Fz|D+L|node|n2-2-0|Fz|kN|—|—|
|combination-D+L-node-n2-2-0-Mx|D+L|node|n2-2-0|Mx|kN.m|—|—|
|combination-D+L-node-n2-2-0-My|D+L|node|n2-2-0|My|kN.m|—|—|
|combination-D+L-node-n2-2-0-Mz|D+L|node|n2-2-0|Mz|kN.m|—|—|

Applies to every listed row: selection · kind = combination.

## Analysis conventions

按指定引擎进行一阶线弹性静力分析，采用Timoshenko弯曲（计入规定的剪切变形）；关闭自重、P-Delta、刚性楼板、刚臂偏移及施工阶段。全局XYZ，Z向上；平面模型位于XZ平面。坐标/位移m，力kN，弯矩kN*m，线载kN/m（按真实杆长），E/G为MPa，密度kg/m^3，A为m^2，Iy/Iz/J为m^4，shape尺寸mm，转角rad。约束顺序ux,uy,uz,rx,ry,rz，true表示固定。梁柱共节点刚接，桁架杆仅传轴力；支座以输入表为准。局部x由构件首节点指向末节点；空间杆局部y为reference vector叉乘局部x的单位向量，局部z=x叉乘y，再按rotation_angle绕局部x转动；平面杆未转轴时局部y为全局+Y、局部z为局部x叉乘局部y，再绕局部x施加rotation_angle；Iy为绕局部y的惯性矩。平面metadata参考向量不采用上述空间叉乘公式。报告局部到全局的转换。杆件位置从首节点计量，side为截面左右极限。N以拉为正；对局部杆端抗力按N,V2,V3,T,M2,M3排序，首节点端乘(-1,+1,+1,-1,-1,-1)、末节点端乘(+1,-1,-1,+1,+1,+1)转换为要求的有符号截面内力，不能取无符号包络替代。逐项报告input.md中数值及派生量，保留符号、单位、工况/组合；绝对值控制量同时给出原符号和控制项/组合。保存可运行输入、引擎版本、/日志及带索引原始结果；这些属于待执行要求，并非已有证据。input.md为完整公开输入附表，不含答案。

## Engine mapping

|Field|Value|
|---|---|
|引擎|PKPM|
|原生执行状态|pending|
|坐标映射要求|协议全局(X,Y,Z)与原生工程全局(X,Y,Z)同向，Z向上；若原生内部轴不同，交付显式变换表。|
|单位映射要求|协议坐标m、力kN、弯矩kN*m、线载kN/m、E/G MPa、截面尺寸mm、惯性矩m^4；原生内部单位逐字段转换并记录。|
|逐构件属性和节点荷载|保留input.md的全部节点、连接、材料、截面组、局部轴、支座与荷载；记录到原生ID的完整双向映射。|
|设置要求|一阶线弹性Timoshenko杆系；关闭自重、刚性楼板、刚域、P-Delta、施工阶段及默认规范组合。|
|结果要求|各协议节点/构件、端点、局部轴分量、工况/组合、符号和单位逐项关联原生结果；不得省略柱脚六分量反力。|
|待验收缺口|实际原生接口、逐梁/节点加载、原生求解与结果索引均待验收；本附表是执行契约，不是原生计算证据。|

## Engine mapping — 工况映射要求

|协议ID|原生目标类型|
|---|---|
|D|DL|
|L|LL|

Applies to every listed row: 协议类型 = case; 加载方式 = 逐构件线载及明确节点向量；不得用整层面载覆盖、自动传载或重复添加。; 原生实际工况标识 = 待运行记录.

## Engine mapping — 组合映射要求

|协议ID|系数 · L|
|---|---|
|D|—|
|D+L|1|

Applies to every listed row: 协议类型 = combination; 系数 · D = 1; 原生实际组合标识 = 待运行记录.

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
