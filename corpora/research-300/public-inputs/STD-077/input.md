## Numerical inputs

|Field|Value|
|---|---|
|title|完整数值输入附表|
|linearCombinations|[]|
|floorTable|[]|

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
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Numerical inputs — Nodes

|id|X_m|Y_m|Z_m|fixed_ux|fixed_uy|fixed_uz|fixed_rx|fixed_ry|fixed_rz|
|---|---|---|---|---|---|---|---|---|---|
|n0-0|0|0|0|true|true|true|true|true|true|
|n1-0|6|0|0|true|true|true|true|true|true|
|n2-0|12|0|0|true|true|true|true|true|true|
|n0-1|0|0|3.3|false|true|false|true|false|true|
|n1-1|6|0|3.3|false|true|false|true|false|true|
|n2-1|12|0|3.3|false|true|false|true|false|true|
|n0-2|0|0|6.6|false|true|false|true|false|true|
|n1-2|6|0|6.6|false|true|false|true|false|true|
|n2-2|12|0|6.6|false|true|false|true|false|true|
|n0-3|0|0|9.9|false|true|false|true|false|true|
|n1-3|6|0|9.9|false|true|false|true|false|true|
|n2-3|12|0|9.9|false|true|false|true|false|true|
|mid-b0-3|3.0|0|9.9|false|true|false|true|false|true|
|mid-b1-3|9.0|0|9.9|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-1|column|n0-0|n0-1|C30|C1|0|[0, 1, 0]|
|c1-1|column|n1-0|n1-1|C30|C1|0|[0, 1, 0]|
|c2-1|column|n2-0|n2-1|C30|C1|0|[0, 1, 0]|
|b0-1|beam|n0-1|n1-1|C30|B1|0|[0, 1, 0]|
|b1-1|beam|n1-1|n2-1|C30|B1|0|[0, 1, 0]|
|c0-2|column|n0-1|n0-2|C30|C2|0|[0, 1, 0]|
|c1-2|column|n1-1|n1-2|C30|C2|0|[0, 1, 0]|
|c2-2|column|n2-1|n2-2|C30|C2|0|[0, 1, 0]|
|b0-2|beam|n0-2|n1-2|C30|B1|0|[0, 1, 0]|
|b1-2|beam|n1-2|n2-2|C30|B1|0|[0, 1, 0]|
|c0-3|column|n0-2|n0-3|C30|C2|0|[0, 1, 0]|
|c1-3|column|n1-2|n1-3|C30|C2|0|[0, 1, 0]|
|c2-3|column|n2-2|n2-3|C30|C2|0|[0, 1, 0]|
|b0-3-a|beam|n0-3|mid-b0-3|C30|B2|0|[0, 1, 0]|
|b0-3-b|beam|mid-b0-3|n1-3|C30|B2|0|[0, 1, 0]|
|b1-3-a|beam|n1-3|mid-b1-3|C30|B2|0|[0, 1, 0]|
|b1-3-b|beam|mid-b1-3|n2-3|C30|B2|0|[0, 1, 0]|

## Numerical inputs — Materials

|id|type|E|G|nu|rho|
|---|---|---|---|---|---|
|C30|concrete|30000|12500.0|0.2|2500|

Applies to every listed row: name = id.

## Numerical inputs — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|B2|300.0|700.0|0.21|0.008574999999999998|0.0015749999999999998|0.004603782069970844|
|C1|600.0|600.0|0.36|0.010799999999999997|0.010799999999999997|0.01825199999999999|
|C2|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-1 → b0-1, D-2 → b1-1, D-3 → b0-2, D-4 → b1-2, D-5 → b0-3-a, D-6 → b0-3-b, D-7 → b1-3-a, D-8 → b1-3-b|global|distributed|-10|

## Numerical inputs — Analysis settings

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Numerical inputs — Continuity notes — Physical beams — B0 3

|Field|Value|
|---|---|
|nodes|["n0-3", "n1-3"]|
|segments|["b0-3-a", "b0-3-b"]|
|midpointNode|mid-b0-3|
|joint|continuous-rigid|
|addedMass|0|

## Numerical inputs — Continuity notes — Physical beams — B1 3

|Field|Value|
|---|---|
|nodes|["n1-3", "n2-3"]|
|segments|["b1-3-a", "b1-3-b"]|
|midpointNode|mid-b1-3|
|joint|continuous-rigid|
|addedMass|0|

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|
|figures|[]|
|interactions|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case-D-node-n0-1-ux|node|n0-1|ux|m|—|—|
|case-D-node-n0-1-uz|node|n0-1|uz|m|—|—|
|case-D-node-n0-1-ry|node|n0-1|ry|rad|—|—|
|case-D-node-n1-1-ux|node|n1-1|ux|m|—|—|
|case-D-node-n1-1-uz|node|n1-1|uz|m|—|—|
|case-D-node-n1-1-ry|node|n1-1|ry|rad|—|—|
|case-D-node-n2-1-ux|node|n2-1|ux|m|—|—|
|case-D-node-n2-1-uz|node|n2-1|uz|m|—|—|
|case-D-node-n2-1-ry|node|n2-1|ry|rad|—|—|
|case-D-node-n0-2-ux|node|n0-2|ux|m|—|—|
|case-D-node-n0-2-uz|node|n0-2|uz|m|—|—|
|case-D-node-n0-2-ry|node|n0-2|ry|rad|—|—|
|case-D-node-n1-2-ux|node|n1-2|ux|m|—|—|
|case-D-node-n1-2-uz|node|n1-2|uz|m|—|—|
|case-D-node-n1-2-ry|node|n1-2|ry|rad|—|—|
|case-D-node-n2-2-ux|node|n2-2|ux|m|—|—|
|case-D-node-n2-2-uz|node|n2-2|uz|m|—|—|
|case-D-node-n2-2-ry|node|n2-2|ry|rad|—|—|
|case-D-node-n0-3-ux|node|n0-3|ux|m|—|—|
|case-D-node-n0-3-uz|node|n0-3|uz|m|—|—|
|case-D-node-n0-3-ry|node|n0-3|ry|rad|—|—|
|case-D-node-n1-3-ux|node|n1-3|ux|m|—|—|
|case-D-node-n1-3-uz|node|n1-3|uz|m|—|—|
|case-D-node-n1-3-ry|node|n1-3|ry|rad|—|—|
|case-D-node-n2-3-ux|node|n2-3|ux|m|—|—|
|case-D-node-n2-3-uz|node|n2-3|uz|m|—|—|
|case-D-node-n2-3-ry|node|n2-3|ry|rad|—|—|
|case-D-member-c0-1-s0-right-N|member|c0-1|N|kN|0|right|
|case-D-member-c0-1-s0-right-V3|member|c0-1|V3|kN|0|right|
|case-D-member-c0-1-s0-right-M2|member|c0-1|M2|kN.m|0|right|
|case-D-member-c0-1-s3.3-left-N|member|c0-1|N|kN|3.3|left|
|case-D-member-c0-1-s3.3-left-V3|member|c0-1|V3|kN|3.3|left|
|case-D-member-c0-1-s3.3-left-M2|member|c0-1|M2|kN.m|3.3|left|
|case-D-member-c1-1-s0-right-N|member|c1-1|N|kN|0|right|
|case-D-member-c1-1-s0-right-V3|member|c1-1|V3|kN|0|right|
|case-D-member-c1-1-s0-right-M2|member|c1-1|M2|kN.m|0|right|
|case-D-member-c1-1-s3.3-left-N|member|c1-1|N|kN|3.3|left|
|case-D-member-c1-1-s3.3-left-V3|member|c1-1|V3|kN|3.3|left|
|case-D-member-c1-1-s3.3-left-M2|member|c1-1|M2|kN.m|3.3|left|
|case-D-member-c2-1-s0-right-N|member|c2-1|N|kN|0|right|
|case-D-member-c2-1-s0-right-V3|member|c2-1|V3|kN|0|right|
|case-D-member-c2-1-s0-right-M2|member|c2-1|M2|kN.m|0|right|
|case-D-member-c2-1-s3.3-left-N|member|c2-1|N|kN|3.3|left|
|case-D-member-c2-1-s3.3-left-V3|member|c2-1|V3|kN|3.3|left|
|case-D-member-c2-1-s3.3-left-M2|member|c2-1|M2|kN.m|3.3|left|
|case-D-member-c0-2-s0-right-N|member|c0-2|N|kN|0|right|
|case-D-member-c0-2-s0-right-V3|member|c0-2|V3|kN|0|right|
|case-D-member-c0-2-s0-right-M2|member|c0-2|M2|kN.m|0|right|
|case-D-member-c0-2-s3.3-left-N|member|c0-2|N|kN|3.3|left|
|case-D-member-c0-2-s3.3-left-V3|member|c0-2|V3|kN|3.3|left|
|case-D-member-c0-2-s3.3-left-M2|member|c0-2|M2|kN.m|3.3|left|
|case-D-member-c1-2-s0-right-N|member|c1-2|N|kN|0|right|
|case-D-member-c1-2-s0-right-V3|member|c1-2|V3|kN|0|right|
|case-D-member-c1-2-s0-right-M2|member|c1-2|M2|kN.m|0|right|
|case-D-member-c1-2-s3.3-left-N|member|c1-2|N|kN|3.3|left|
|case-D-member-c1-2-s3.3-left-V3|member|c1-2|V3|kN|3.3|left|
|case-D-member-c1-2-s3.3-left-M2|member|c1-2|M2|kN.m|3.3|left|
|case-D-member-c2-2-s0-right-N|member|c2-2|N|kN|0|right|
|case-D-member-c2-2-s0-right-V3|member|c2-2|V3|kN|0|right|
|case-D-member-c2-2-s0-right-M2|member|c2-2|M2|kN.m|0|right|
|case-D-member-c2-2-s3.3-left-N|member|c2-2|N|kN|3.3|left|
|case-D-member-c2-2-s3.3-left-V3|member|c2-2|V3|kN|3.3|left|
|case-D-member-c2-2-s3.3-left-M2|member|c2-2|M2|kN.m|3.3|left|
|case-D-member-c0-3-s0-right-N|member|c0-3|N|kN|0|right|
|case-D-member-c0-3-s0-right-V3|member|c0-3|V3|kN|0|right|
|case-D-member-c0-3-s0-right-M2|member|c0-3|M2|kN.m|0|right|
|case-D-member-c0-3-s3.3-left-N|member|c0-3|N|kN|3.3000000000000007|left|
|case-D-member-c0-3-s3.3-left-V3|member|c0-3|V3|kN|3.3000000000000007|left|
|case-D-member-c0-3-s3.3-left-M2|member|c0-3|M2|kN.m|3.3000000000000007|left|
|case-D-member-c1-3-s0-right-N|member|c1-3|N|kN|0|right|
|case-D-member-c1-3-s0-right-V3|member|c1-3|V3|kN|0|right|
|case-D-member-c1-3-s0-right-M2|member|c1-3|M2|kN.m|0|right|
|case-D-member-c1-3-s3.3-left-N|member|c1-3|N|kN|3.3000000000000007|left|
|case-D-member-c1-3-s3.3-left-V3|member|c1-3|V3|kN|3.3000000000000007|left|
|case-D-member-c1-3-s3.3-left-M2|member|c1-3|M2|kN.m|3.3000000000000007|left|
|case-D-member-c2-3-s0-right-N|member|c2-3|N|kN|0|right|
|case-D-member-c2-3-s0-right-V3|member|c2-3|V3|kN|0|right|
|case-D-member-c2-3-s0-right-M2|member|c2-3|M2|kN.m|0|right|
|case-D-member-c2-3-s3.3-left-N|member|c2-3|N|kN|3.3000000000000007|left|
|case-D-member-c2-3-s3.3-left-V3|member|c2-3|V3|kN|3.3000000000000007|left|
|case-D-member-c2-3-s3.3-left-M2|member|c2-3|M2|kN.m|3.3000000000000007|left|
|case-D-member-b0-3-a-s0-right-N|member|b0-3-a|N|kN|0|right|
|case-D-member-b0-3-a-s0-right-V3|member|b0-3-a|V3|kN|0|right|
|case-D-member-b0-3-a-s0-right-M2|member|b0-3-a|M2|kN.m|0|right|
|case-D-member-b0-3-b-s3-left-N|member|b0-3-b|N|kN|3|left|
|case-D-member-b0-3-b-s3-left-V3|member|b0-3-b|V3|kN|3|left|
|case-D-member-b0-3-b-s3-left-M2|member|b0-3-b|M2|kN.m|3|left|
|case-D-member-b0-3-a-s3-left-N|member|b0-3-a|N|kN|3|left|
|case-D-member-b0-3-a-s3-left-V3|member|b0-3-a|V3|kN|3|left|
|case-D-member-b0-3-a-s3-left-M2|member|b0-3-a|M2|kN.m|3|left|
|case-D-member-b1-3-a-s0-right-N|member|b1-3-a|N|kN|0|right|
|case-D-member-b1-3-a-s0-right-V3|member|b1-3-a|V3|kN|0|right|
|case-D-member-b1-3-a-s0-right-M2|member|b1-3-a|M2|kN.m|0|right|
|case-D-member-b1-3-b-s3-left-N|member|b1-3-b|N|kN|3|left|
|case-D-member-b1-3-b-s3-left-V3|member|b1-3-b|V3|kN|3|left|
|case-D-member-b1-3-b-s3-left-M2|member|b1-3-b|M2|kN.m|3|left|
|case-D-member-b1-3-a-s3-left-N|member|b1-3-a|N|kN|3|left|
|case-D-member-b1-3-a-s3-left-V3|member|b1-3-a|V3|kN|3|left|
|case-D-member-b1-3-a-s3-left-M2|member|b1-3-a|M2|kN.m|3|left|
|case-D-node-mid-b0-3-ux|node|mid-b0-3|ux|m|—|—|
|case-D-node-mid-b0-3-uz|node|mid-b0-3|uz|m|—|—|
|case-D-node-mid-b0-3-ry|node|mid-b0-3|ry|rad|—|—|
|case-D-node-mid-b1-3-ux|node|mid-b1-3|ux|m|—|—|
|case-D-node-mid-b1-3-uz|node|mid-b1-3|uz|m|—|—|
|case-D-node-mid-b1-3-ry|node|mid-b1-3|ry|rad|—|—|
|case-D-node-n0-0-Fx|node|n0-0|Fx|kN|—|—|
|case-D-node-n0-0-Fz|node|n0-0|Fz|kN|—|—|
|case-D-node-n0-0-My|node|n0-0|My|kN.m|—|—|
|case-D-node-n1-0-Fx|node|n1-0|Fx|kN|—|—|
|case-D-node-n1-0-Fz|node|n1-0|Fz|kN|—|—|
|case-D-node-n1-0-My|node|n1-0|My|kN.m|—|—|
|case-D-node-n2-0-Fx|node|n2-0|Fx|kN|—|—|
|case-D-node-n2-0-Fz|node|n2-0|Fz|kN|—|—|
|case-D-node-n2-0-My|node|n2-0|My|kN.m|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis conventions

按指定引擎进行一阶线弹性静力分析，采用Euler-Bernoulli弯曲（不计剪切变形）；关闭自重、P-Delta、刚性楼板、刚臂偏移及施工阶段。全局XYZ，Z向上；平面模型位于XZ平面。坐标/位移m，力kN，弯矩kN*m，线载kN/m（按真实杆长），E/G为MPa，密度kg/m^3，A为m^2，Iy/Iz/J为m^4，shape尺寸mm，转角rad。约束顺序ux,uy,uz,rx,ry,rz，true表示固定。梁柱共节点刚接，桁架杆仅传轴力；支座以输入表为准。局部x由构件首节点指向末节点；空间杆局部y为reference vector叉乘局部x的单位向量，局部z=x叉乘y，再按rotation_angle绕局部x转动；平面杆未转轴时局部y为全局+Y、局部z为局部x叉乘局部y，再绕局部x施加rotation_angle；Iy为绕局部y的惯性矩。平面metadata参考向量不采用上述空间叉乘公式。报告局部到全局的转换。杆件位置从首节点计量，side为截面左右极限。N以拉为正；对局部杆端抗力按N,V2,V3,T,M2,M3排序，首节点端乘(-1,+1,+1,-1,-1,-1)、末节点端乘(+1,-1,-1,+1,+1,+1)转换为要求的有符号截面内力，不能取无符号包络替代。逐项报告input.md中数值及派生量，保留符号、单位、工况/组合；绝对值控制量同时给出原符号和控制项/组合。保存可运行输入、引擎版本、/日志及带索引原始结果；这些属于待执行要求，并非已有证据。input.md为完整公开输入附表，不含答案。
