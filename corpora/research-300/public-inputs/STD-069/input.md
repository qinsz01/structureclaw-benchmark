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
|n0-0|0|0|0|true|true|true|true|false|true|
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

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|C30|concrete|30000|12500|0.2|2500|

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

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-1 → b0-1, D-2 → b0-2|global|distributed|-72|

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
|D-node-n1-1-ux|n1-1|ux|m|
|D-node-n1-1-uz|n1-1|uz|m|
|D-node-n0-2-ux|n0-2|ux|m|
|D-node-n0-2-uz|n0-2|uz|m|
|D-node-n1-2-ux|n1-2|ux|m|
|D-node-n1-2-uz|n1-2|uz|m|
|D-node-n0-0-ry|n0-0|ry|rad|
|D-node-n0-0-ux|n0-0|ux|m|
|D-node-n0-0-uz|n0-0|uz|m|
|D-node-n1-0-ux|n1-0|ux|m|
|D-node-n1-0-uz|n1-0|uz|m|
|D-node-n0-0-Fx|n0-0|Fx|kN|
|D-node-n0-0-Fz|n0-0|Fz|kN|
|D-node-n0-0-My|n0-0|My|kN.m|
|D-node-n1-0-Fx|n1-0|Fx|kN|
|D-node-n1-0-Fz|n1-0|Fz|kN|
|D-node-n1-0-My|n1-0|My|kN.m|

Applies to every listed row: selection · kind = case; selection · id = D; location · kind = node.

## Requested outputs — Derived

|id|operands|description|
|---|---|---|
|D-difference-n0-1-minus-n0-0-ux|["D-node-n0-1-ux", "D-node-n0-0-ux"]|n0-1.ux - n0-0.ux; upper minus lower, no division by story height|
|D-difference-n0-1-minus-n0-0-uz|["D-node-n0-1-uz", "D-node-n0-0-uz"]|n0-1.uz - n0-0.uz; upper minus lower, no division by story height|
|D-difference-n1-1-minus-n1-0-ux|["D-node-n1-1-ux", "D-node-n1-0-ux"]|n1-1.ux - n1-0.ux; upper minus lower, no division by story height|
|D-difference-n1-1-minus-n1-0-uz|["D-node-n1-1-uz", "D-node-n1-0-uz"]|n1-1.uz - n1-0.uz; upper minus lower, no division by story height|
|D-difference-n0-2-minus-n0-1-ux|["D-node-n0-2-ux", "D-node-n0-1-ux"]|n0-2.ux - n0-1.ux; upper minus lower, no division by story height|
|D-difference-n0-2-minus-n0-1-uz|["D-node-n0-2-uz", "D-node-n0-1-uz"]|n0-2.uz - n0-1.uz; upper minus lower, no division by story height|
|D-difference-n1-2-minus-n1-1-ux|["D-node-n1-2-ux", "D-node-n1-1-ux"]|n1-2.ux - n1-1.ux; upper minus lower, no division by story height|
|D-difference-n1-2-minus-n1-1-uz|["D-node-n1-2-uz", "D-node-n1-1-uz"]|n1-2.uz - n1-1.uz; upper minus lower, no division by story height|

Applies to every listed row: operation = difference; unit = m.

## Analysis conventions

按指定引擎进行一阶线弹性静力分析，采用Euler-Bernoulli弯曲（不计剪切变形）；关闭自重、P-Delta、刚性楼板、刚臂偏移及施工阶段。全局XYZ，Z向上；平面模型位于XZ平面。坐标/位移m，力kN，弯矩kN*m，线载kN/m（按真实杆长），E/G为MPa，密度kg/m^3，A为m^2，Iy/Iz/J为m^4，shape尺寸mm，转角rad。约束顺序ux,uy,uz,rx,ry,rz，true表示固定。梁柱共节点刚接，桁架杆仅传轴力；支座以输入表为准。局部x由构件首节点指向末节点；空间杆局部y为reference vector叉乘局部x的单位向量，局部z=x叉乘y，再按rotation_angle绕局部x转动；平面杆未转轴时局部y为全局+Y、局部z为局部x叉乘局部y，再绕局部x施加rotation_angle；Iy为绕局部y的惯性矩。平面metadata参考向量不采用上述空间叉乘公式。报告局部到全局的转换。杆件位置从首节点计量，side为截面左右极限。N以拉为正；对局部杆端抗力按N,V2,V3,T,M2,M3排序，首节点端乘(-1,+1,+1,-1,-1,-1)、末节点端乘(+1,-1,-1,+1,+1,+1)转换为要求的有符号截面内力，不能取无符号包络替代。逐项报告input.md中数值及派生量，保留符号、单位、工况/组合；绝对值控制量同时给出原符号和控制项/组合。保存可运行输入、引擎版本、/日志及带索引原始结果；这些属于待执行要求，并非已有证据。input.md为完整公开输入附表，不含答案。

## Output scope — Required outputs

|id|description|quantityIds|kind|
|---|---|---|---|
|joint-displacements|两层左右四节点的全局 X/Z 位移 ux、uz|["D-node-n0-1-ux", "D-node-n0-1-uz", "D-node-n1-1-ux", "D-node-n1-1-uz", "D-node-n0-2-ux", "D-node-n0-2-uz", "D-node-n1-2-ux", "D-node-n1-2-uz"]|numerical|
|left-pinned-base-rotation|左侧铰支柱脚 n0-0 的自由转角 ry|["D-node-n0-0-ry"]|numerical|
|column-displacement-differences|逐柱线相邻实际节点的上端减下端位移差 Δux、Δuz|["D-difference-n0-1-minus-n0-0-ux", "D-difference-n0-1-minus-n0-0-uz", "D-difference-n1-1-minus-n1-0-ux", "D-difference-n1-1-minus-n1-0-uz", "D-difference-n0-2-minus-n0-1-ux", "D-difference-n0-2-minus-n0-1-uz", "D-difference-n1-2-minus-n1-1-ux", "D-difference-n1-2-minus-n1-1-uz"]|derived|
|base-reactions|左铰、右固两柱脚的 Fx、Fz、My；必须保留左柱脚零弯矩对应量|["D-node-n0-0-Fx", "D-node-n0-0-Fz", "D-node-n0-0-My", "D-node-n1-0-Fx", "D-node-n1-0-Fz", "D-node-n1-0-My"]|numerical|

Applies to every listed row: state = 1.

## Physical definitions

C30 弹性参数明确采用 E=30000 MPa、nu=0.2、G=12500 MPa、rho=2500 kg/m³；均为输入属性，不推导承载力。
题定梁柱尺寸保留，截面 A、Iy、Iz、J 数值在附件中明确；材料与截面分组不互换。
左柱脚仅释放平面内 ry；72 kN/m 已是线载，未再次乘以分担宽度，且自重关闭。
逐层位移差为每柱列 Δux、Δuz，上端减下端；左柱脚 My 仍作为要求量以核验铰支边界。
梁柱采用线弹性 Euler-Bernoulli 弯曲及轴向变形模型，不计剪切变形；仅采用模型中明列的支座约束和轴力杆，不添加端释放、节点质量或额外荷载。
input.md 中的 J 为明确冻结的矩形截面扭转常数近似值；使用附表给定的 A、Iy、Iz、J 数值，局部 y、z 轴按 input.md 定义。
