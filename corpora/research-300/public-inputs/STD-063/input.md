## Numerical inputs

|Field|Value|
|---|---|
|title|完整数值输入附表|
|linearCombinations|[]|
|floorTable|[]|
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
|n0-1|0|0|3.6|false|true|false|true|false|true|
|n1-1|6|0|3.6|false|true|false|true|false|true|
|n0-2|0|0|7.2|false|true|false|true|false|true|
|n1-2|6|0|7.2|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-1|column|n0-0|n0-1|M1|C1|0|[0, 1, 0]|
|c1-1|column|n1-0|n1-1|M1|C1|0|[0, 1, 0]|
|b0-1|beam|n0-1|n1-1|M1|B1|0|[0, 1, 0]|
|c0-2|column|n0-1|n0-2|M1|C1|0|[0, 1, 0]|
|c1-2|column|n1-1|n1-2|M1|C1|0|[0, 1, 0]|
|b0-2|beam|n0-2|n1-2|M1|B1|0|[0, 1, 0]|
|brace1|truss|n0-0|n1-1|M1|A1|0|null|
|brace2|truss|n1-0|n0-1|M1|A1|0|null|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Numerical inputs — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|C1|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|
|A1|100.0|100.0|0.010000000000000002|8.333333333333335e-06|8.333333333333335e-06|1.4083333333333338e-05|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|type|wz|fx|
|---|---|---|---|
|D-1 → b0-1, D-2 → b0-2|distributed|-10|—|
|D-3 → n1-2|nodal|—|30|

Applies to every listed row: reference_frame = global.

## Numerical inputs — Analysis settings

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|
|figures|[]|
|interactions|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|D-node-n0-1-ux|node|n0-1|ux|m|—|—|
|D-node-n0-1-uz|node|n0-1|uz|m|—|—|
|D-node-n0-1-ry|node|n0-1|ry|rad|—|—|
|D-node-n1-1-ux|node|n1-1|ux|m|—|—|
|D-node-n1-1-uz|node|n1-1|uz|m|—|—|
|D-node-n1-1-ry|node|n1-1|ry|rad|—|—|
|D-node-n0-2-ux|node|n0-2|ux|m|—|—|
|D-node-n0-2-uz|node|n0-2|uz|m|—|—|
|D-node-n0-2-ry|node|n0-2|ry|rad|—|—|
|D-node-n1-2-ux|node|n1-2|ux|m|—|—|
|D-node-n1-2-uz|node|n1-2|uz|m|—|—|
|D-node-n1-2-ry|node|n1-2|ry|rad|—|—|
|D-member-brace1-i-N|member|brace1|N|kN|0|right|
|D-member-brace2-i-N|member|brace2|N|kN|0|right|
|D-member-c0-1-i-N|member|c0-1|N|kN|0|right|
|D-member-c0-1-i-V3|member|c0-1|V3|kN|0|right|
|D-member-c0-1-i-M2|member|c0-1|M2|kN.m|0|right|
|D-member-c0-1-j-N|member|c0-1|N|kN|3.6|left|
|D-member-c0-1-j-V3|member|c0-1|V3|kN|3.6|left|
|D-member-c0-1-j-M2|member|c0-1|M2|kN.m|3.6|left|
|D-member-c1-1-i-N|member|c1-1|N|kN|0|right|
|D-member-c1-1-i-V3|member|c1-1|V3|kN|0|right|
|D-member-c1-1-i-M2|member|c1-1|M2|kN.m|0|right|
|D-member-c1-1-j-N|member|c1-1|N|kN|3.6|left|
|D-member-c1-1-j-V3|member|c1-1|V3|kN|3.6|left|
|D-member-c1-1-j-M2|member|c1-1|M2|kN.m|3.6|left|
|D-member-b0-1-i-N|member|b0-1|N|kN|0|right|
|D-member-b0-1-i-V3|member|b0-1|V3|kN|0|right|
|D-member-b0-1-i-M2|member|b0-1|M2|kN.m|0|right|
|D-member-b0-1-j-N|member|b0-1|N|kN|6.0|left|
|D-member-b0-1-j-V3|member|b0-1|V3|kN|6.0|left|
|D-member-b0-1-j-M2|member|b0-1|M2|kN.m|6.0|left|
|D-member-c0-2-i-N|member|c0-2|N|kN|0|right|
|D-member-c0-2-i-V3|member|c0-2|V3|kN|0|right|
|D-member-c0-2-i-M2|member|c0-2|M2|kN.m|0|right|
|D-member-c0-2-j-N|member|c0-2|N|kN|3.6|left|
|D-member-c0-2-j-V3|member|c0-2|V3|kN|3.6|left|
|D-member-c0-2-j-M2|member|c0-2|M2|kN.m|3.6|left|
|D-member-c1-2-i-N|member|c1-2|N|kN|0|right|
|D-member-c1-2-i-V3|member|c1-2|V3|kN|0|right|
|D-member-c1-2-i-M2|member|c1-2|M2|kN.m|0|right|
|D-member-c1-2-j-N|member|c1-2|N|kN|3.6|left|
|D-member-c1-2-j-V3|member|c1-2|V3|kN|3.6|left|
|D-member-c1-2-j-M2|member|c1-2|M2|kN.m|3.6|left|
|D-member-b0-2-i-N|member|b0-2|N|kN|0|right|
|D-member-b0-2-i-V3|member|b0-2|V3|kN|0|right|
|D-member-b0-2-i-M2|member|b0-2|M2|kN.m|0|right|
|D-member-b0-2-j-N|member|b0-2|N|kN|6.0|left|
|D-member-b0-2-j-V3|member|b0-2|V3|kN|6.0|left|
|D-member-b0-2-j-M2|member|b0-2|M2|kN.m|6.0|left|
|D-node-n0-0-Fx|node|n0-0|Fx|kN|—|—|
|D-node-n0-0-Fz|node|n0-0|Fz|kN|—|—|
|D-node-n0-0-My|node|n0-0|My|kN.m|—|—|
|D-node-n1-0-Fx|node|n1-0|Fx|kN|—|—|
|D-node-n1-0-Fz|node|n1-0|Fz|kN|—|—|
|D-node-n1-0-My|node|n1-0|My|kN.m|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis conventions

按指定引擎进行一阶线弹性静力分析，采用Euler-Bernoulli弯曲（不计剪切变形）；关闭自重、P-Delta、刚性楼板、刚臂偏移及施工阶段。全局XYZ，Z向上；平面模型位于XZ平面。坐标/位移m，力kN，弯矩kN*m，线载kN/m（按真实杆长），E/G为MPa，密度kg/m^3，A为m^2，Iy/Iz/J为m^4，shape尺寸mm，转角rad。约束顺序ux,uy,uz,rx,ry,rz，true表示固定。梁柱共节点刚接，桁架杆仅传轴力；支座以输入表为准。局部x由构件首节点指向末节点；空间杆局部y为reference vector叉乘局部x的单位向量，局部z=x叉乘y，再按rotation_angle绕局部x转动；平面杆未转轴时局部y为全局+Y、局部z为局部x叉乘局部y，再绕局部x施加rotation_angle；Iy为绕局部y的惯性矩。平面metadata参考向量不采用上述空间叉乘公式。报告局部到全局的转换。杆件位置从首节点计量，side为截面左右极限。N以拉为正；对局部杆端抗力按N,V2,V3,T,M2,M3排序，首节点端乘(-1,+1,+1,-1,-1,-1)、末节点端乘(+1,-1,-1,+1,+1,+1)转换为要求的有符号截面内力，不能取无符号包络替代。逐项报告input.md中数值及派生量，保留符号、单位、工况/组合；绝对值控制量同时给出原符号和控制项/组合。保存可运行输入、引擎版本、/日志及带索引原始结果；这些属于待执行要求，并非已有证据。input.md为完整公开输入附表，不含答案。

## Output scope — Required outputs

|id|description|quantityIds|
|---|---|---|
|joint-displacements|两层左右柱顶 ux 侧移及完整平面节点位移 ux、uz、ry|["D-node-n0-1-ux", "D-node-n0-1-uz", "D-node-n0-1-ry", "D-node-n1-1-ux", "D-node-n1-1-uz", "D-node-n1-1-ry", "D-node-n0-2-ux", "D-node-n0-2-uz", "D-node-n0-2-ry", "D-node-n1-2-ux", "D-node-n1-2-uz", "D-node-n1-2-ry"]|
|brace-axial-forces|两根首层斜撑轴力 N，拉为正|["D-member-brace1-i-N", "D-member-brace2-i-N"]|
|member-end-forces|所有梁柱两端的局部 N、V3、M2；斜撑为纯轴力杆，不承担弯矩|["D-member-c0-1-i-N", "D-member-c0-1-i-V3", "D-member-c0-1-i-M2", "D-member-c0-1-j-N", "D-member-c0-1-j-V3", "D-member-c0-1-j-M2", "D-member-c1-1-i-N", "D-member-c1-1-i-V3", "D-member-c1-1-i-M2", "D-member-c1-1-j-N", "D-member-c1-1-j-V3", "D-member-c1-1-j-M2", "D-member-b0-1-i-N", "D-member-b0-1-i-V3", "D-member-b0-1-i-M2", "D-member-b0-1-j-N", "D-member-b0-1-j-V3", "D-member-b0-1-j-M2", "D-member-c0-2-i-N", "D-member-c0-2-i-V3", "D-member-c0-2-i-M2", "D-member-c0-2-j-N", "D-member-c0-2-j-V3", "D-member-c0-2-j-M2", "D-member-c1-2-i-N", "D-member-c1-2-i-V3", "D-member-c1-2-i-M2", "D-member-c1-2-j-N", "D-member-c1-2-j-V3", "D-member-c1-2-j-M2", "D-member-b0-2-i-N", "D-member-b0-2-i-V3", "D-member-b0-2-i-M2", "D-member-b0-2-j-N", "D-member-b0-2-j-V3", "D-member-b0-2-j-M2"]|
|base-reactions|各柱脚全局反力 Fx、Fz 和反力矩 My|["D-node-n0-0-Fx", "D-node-n0-0-Fz", "D-node-n0-0-My", "D-node-n1-0-Fx", "D-node-n1-0-Fz", "D-node-n1-0-My"]|

Applies to every listed row: state = 1; kind = numerical.

## Physical definitions

补齐 Q355 钢、B1 梁、C1 柱及 A1 轴力斜撑的显式数值属性。
斜撑端点共享框架节点的平移，但 truss 单元不传递转角或弯矩；交点 (3,0,1.8) m 处没有节点。
30 kN 顶层水平力与两根梁的重力线载同时属于 D 工况，未添加未指定组合。
梁柱采用线弹性 Euler-Bernoulli 弯曲及轴向变形模型，不计剪切变形；仅采用模型中明列的支座约束和轴力杆，不添加端释放、节点质量或额外荷载。
input.md 中的 J 为明确冻结的矩形截面扭转常数近似值；使用附表给定的 A、Iy、Iz、J 数值，局部 y、z 轴按 input.md 定义。
