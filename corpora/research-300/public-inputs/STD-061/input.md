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
|n1-0|4.5|0|0|true|true|true|true|true|true|
|n2-0|12|0|0|true|true|true|true|true|true|
|n0-1|0|0|3.6|false|true|false|true|false|true|
|n1-1|4.5|0|3.6|false|true|false|true|false|true|
|n2-1|12|0|3.6|false|true|false|true|false|true|
|n0-2|0|0|7.8|false|true|false|true|false|true|
|n1-2|4.5|0|7.8|false|true|false|true|false|true|
|n2-2|12|0|7.8|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-1|column|n0-0|n0-1|M1|C1|0|[0, 1, 0]|
|c1-1|column|n1-0|n1-1|M1|C1|0|[0, 1, 0]|
|c2-1|column|n2-0|n2-1|M1|C1|0|[0, 1, 0]|
|b0-1|beam|n0-1|n1-1|M1|B1|0|[0, 1, 0]|
|b1-1|beam|n1-1|n2-1|M1|B1|0|[0, 1, 0]|
|c0-2|column|n0-1|n0-2|M1|C1|0|[0, 1, 0]|
|c1-2|column|n1-1|n1-2|M1|C1|0|[0, 1, 0]|
|c2-2|column|n2-1|n2-2|M1|C1|0|[0, 1, 0]|
|b0-2|beam|n0-2|n1-2|M1|B1|0|[0, 1, 0]|
|b1-2|beam|n1-2|n2-2|M1|B1|0|[0, 1, 0]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Numerical inputs — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|C1|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|wz|
|---|---|
|D-1 → b0-1|-8|
|D-2 → b1-1|-12|
|D-3 → b0-2|-6|
|D-4 → b1-2|-10|

Applies to every listed row: reference_frame = global; type = distributed.

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
|figures|[]|
|interactions|[]|

## Requested outputs — Quantities

|id|location · id|component|unit|
|---|---|---|---|
|D-node-n0-1-ux|n0-1|ux|m|
|D-node-n0-1-uz|n0-1|uz|m|
|D-node-n0-1-ry|n0-1|ry|rad|
|D-node-n1-1-ux|n1-1|ux|m|
|D-node-n1-1-uz|n1-1|uz|m|
|D-node-n1-1-ry|n1-1|ry|rad|
|D-node-n2-1-ux|n2-1|ux|m|
|D-node-n2-1-uz|n2-1|uz|m|
|D-node-n2-1-ry|n2-1|ry|rad|
|D-node-n0-2-ux|n0-2|ux|m|
|D-node-n0-2-uz|n0-2|uz|m|
|D-node-n0-2-ry|n0-2|ry|rad|
|D-node-n1-2-ux|n1-2|ux|m|
|D-node-n1-2-uz|n1-2|uz|m|
|D-node-n1-2-ry|n1-2|ry|rad|
|D-node-n2-2-ux|n2-2|ux|m|
|D-node-n2-2-uz|n2-2|uz|m|
|D-node-n2-2-ry|n2-2|ry|rad|
|D-node-n0-0-ux|n0-0|ux|m|
|D-node-n0-0-uz|n0-0|uz|m|
|D-node-n1-0-ux|n1-0|ux|m|
|D-node-n1-0-uz|n1-0|uz|m|
|D-node-n2-0-ux|n2-0|ux|m|
|D-node-n2-0-uz|n2-0|uz|m|
|D-node-n0-0-Fx|n0-0|Fx|kN|
|D-node-n0-0-Fz|n0-0|Fz|kN|
|D-node-n0-0-My|n0-0|My|kN.m|
|D-node-n1-0-Fx|n1-0|Fx|kN|
|D-node-n1-0-Fz|n1-0|Fz|kN|
|D-node-n1-0-My|n1-0|My|kN.m|
|D-node-n2-0-Fx|n2-0|Fx|kN|
|D-node-n2-0-Fz|n2-0|Fz|kN|
|D-node-n2-0-My|n2-0|My|kN.m|

Applies to every listed row: selection · kind = case; selection · id = D; location · kind = node.

## Requested outputs — Derived

|id|operands|description|
|---|---|---|
|D-difference-n0-1-minus-n0-0-ux|["D-node-n0-1-ux", "D-node-n0-0-ux"]|n0-1.ux - n0-0.ux; upper minus lower, no division by story height|
|D-difference-n0-1-minus-n0-0-uz|["D-node-n0-1-uz", "D-node-n0-0-uz"]|n0-1.uz - n0-0.uz; upper minus lower, no division by story height|
|D-difference-n1-1-minus-n1-0-ux|["D-node-n1-1-ux", "D-node-n1-0-ux"]|n1-1.ux - n1-0.ux; upper minus lower, no division by story height|
|D-difference-n1-1-minus-n1-0-uz|["D-node-n1-1-uz", "D-node-n1-0-uz"]|n1-1.uz - n1-0.uz; upper minus lower, no division by story height|
|D-difference-n2-1-minus-n2-0-ux|["D-node-n2-1-ux", "D-node-n2-0-ux"]|n2-1.ux - n2-0.ux; upper minus lower, no division by story height|
|D-difference-n2-1-minus-n2-0-uz|["D-node-n2-1-uz", "D-node-n2-0-uz"]|n2-1.uz - n2-0.uz; upper minus lower, no division by story height|
|D-difference-n0-2-minus-n0-1-ux|["D-node-n0-2-ux", "D-node-n0-1-ux"]|n0-2.ux - n0-1.ux; upper minus lower, no division by story height|
|D-difference-n0-2-minus-n0-1-uz|["D-node-n0-2-uz", "D-node-n0-1-uz"]|n0-2.uz - n0-1.uz; upper minus lower, no division by story height|
|D-difference-n1-2-minus-n1-1-ux|["D-node-n1-2-ux", "D-node-n1-1-ux"]|n1-2.ux - n1-1.ux; upper minus lower, no division by story height|
|D-difference-n1-2-minus-n1-1-uz|["D-node-n1-2-uz", "D-node-n1-1-uz"]|n1-2.uz - n1-1.uz; upper minus lower, no division by story height|
|D-difference-n2-2-minus-n2-1-ux|["D-node-n2-2-ux", "D-node-n2-1-ux"]|n2-2.ux - n2-1.ux; upper minus lower, no division by story height|
|D-difference-n2-2-minus-n2-1-uz|["D-node-n2-2-uz", "D-node-n2-1-uz"]|n2-2.uz - n2-1.uz; upper minus lower, no division by story height|

Applies to every listed row: operation = difference; unit = m.

## Analysis conventions

按指定引擎进行一阶线弹性静力分析，采用Euler-Bernoulli弯曲（不计剪切变形）；关闭自重、P-Delta、刚性楼板、刚臂偏移及施工阶段。全局XYZ，Z向上；平面模型位于XZ平面。坐标/位移m，力kN，弯矩kN*m，线载kN/m（按真实杆长），E/G为MPa，密度kg/m^3，A为m^2，Iy/Iz/J为m^4，shape尺寸mm，转角rad。约束顺序ux,uy,uz,rx,ry,rz，true表示固定。梁柱共节点刚接，桁架杆仅传轴力；支座以输入表为准。局部x由构件首节点指向末节点；空间杆局部y为reference vector叉乘局部x的单位向量，局部z=x叉乘y，再按rotation_angle绕局部x转动；平面杆未转轴时局部y为全局+Y、局部z为局部x叉乘局部y，再绕局部x施加rotation_angle；Iy为绕局部y的惯性矩。平面metadata参考向量不采用上述空间叉乘公式。报告局部到全局的转换。杆件位置从首节点计量，side为截面左右极限。N以拉为正；对局部杆端抗力按N,V2,V3,T,M2,M3排序，首节点端乘(-1,+1,+1,-1,-1,-1)、末节点端乘(+1,-1,-1,+1,+1,+1)转换为要求的有符号截面内力，不能取无符号包络替代。逐项报告input.md中数值及派生量，保留符号、单位、工况/组合；绝对值控制量同时给出原符号和控制项/组合。保存可运行输入、引擎版本、/日志及带索引原始结果；这些属于待执行要求，并非已有证据。input.md为完整公开输入附表，不含答案。

## Output scope — Required outputs

|id|description|quantityIds|kind|
|---|---|---|---|
|joint-displacements|两层、三柱线上全部六个梁柱节点的 ux、uz 位移及 ry 转角|["D-node-n0-1-ux", "D-node-n0-1-uz", "D-node-n0-1-ry", "D-node-n1-1-ux", "D-node-n1-1-uz", "D-node-n1-1-ry", "D-node-n2-1-ux", "D-node-n2-1-uz", "D-node-n2-1-ry", "D-node-n0-2-ux", "D-node-n0-2-uz", "D-node-n0-2-ry", "D-node-n1-2-ux", "D-node-n1-2-uz", "D-node-n1-2-ry", "D-node-n2-2-ux", "D-node-n2-2-uz", "D-node-n2-2-ry"]|numerical|
|column-displacement-differences|逐柱线相邻实际节点的上端减下端位移差 Δux、Δuz|["D-difference-n0-1-minus-n0-0-ux", "D-difference-n0-1-minus-n0-0-uz", "D-difference-n1-1-minus-n1-0-ux", "D-difference-n1-1-minus-n1-0-uz", "D-difference-n2-1-minus-n2-0-ux", "D-difference-n2-1-minus-n2-0-uz", "D-difference-n0-2-minus-n0-1-ux", "D-difference-n0-2-minus-n0-1-uz", "D-difference-n1-2-minus-n1-1-ux", "D-difference-n1-2-minus-n1-1-uz", "D-difference-n2-2-minus-n2-1-ux", "D-difference-n2-2-minus-n2-1-uz"]|derived|
|base-reactions|各柱脚全局反力 Fx、Fz 和反力矩 My|["D-node-n0-0-Fx", "D-node-n0-0-Fz", "D-node-n0-0-My", "D-node-n1-0-Fx", "D-node-n1-0-Fz", "D-node-n1-0-My", "D-node-n2-0-Fx", "D-node-n2-0-Fz", "D-node-n2-0-My"]|numerical|

Applies to every listed row: state = 1.

## Physical definitions

补齐单钢材料 Q355 及 B1 梁、C1 柱的数值属性；使用附件明列的矩形理想化截面。
‘每层每柱线位移’明确为 ux、uz、ry；‘层间位移差’明确为逐柱列 Δux 和 Δuz，上层减下层，不除以层高。
四根梁的线载分别为 8、12、6、10 kN/m，保留实际不等跨度与累计标高。
梁柱采用线弹性 Euler-Bernoulli 弯曲及轴向变形模型，不计剪切变形；仅采用模型中明列的支座约束和轴力杆，不添加端释放、节点质量或额外荷载。
input.md 中的 J 为明确冻结的矩形截面扭转常数近似值；使用附表给定的 A、Iy、Iz、J 数值，局部 y、z 轴按 input.md 定义。
