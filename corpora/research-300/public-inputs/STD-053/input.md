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
|roof-n0|0|0|6|false|true|false|true|false|true|
|roof-n1|16|0|6|false|true|false|true|false|true|
|base-L|0|0|0|true|true|true|true|false|true|
|base-R|16|0|0|true|true|true|true|true|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|roof-1|beam|roof-n0|roof-n1|M1|B1|0|[0, 1, 0]|
|column-L|column|base-L|roof-n0|M1|C1|0|[0, 1, 0]|
|column-R|column|base-R|roof-n1|M1|C1|0|[0, 1, 0]|

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

|Load ID → element / node|type|wz|fx|
|---|---|---|---|
|D-1 → roof-1|distributed|-5|—|
|D-2 → roof-n1|nodal|—|20|

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

|id|location · id|component|unit|
|---|---|---|---|
|case-D-node-roof-n0-ux|roof-n0|ux|m|
|case-D-node-roof-n0-uz|roof-n0|uz|m|
|case-D-node-roof-n0-ry|roof-n0|ry|rad|
|case-D-node-roof-n1-ux|roof-n1|ux|m|
|case-D-node-roof-n1-uz|roof-n1|uz|m|
|case-D-node-roof-n1-ry|roof-n1|ry|rad|
|case-D-node-base-L-ry|base-L|ry|rad|
|case-D-node-base-L-Fx|base-L|Fx|kN|
|case-D-node-base-L-Fz|base-L|Fz|kN|
|case-D-node-base-L-My|base-L|My|kN.m|
|case-D-node-base-R-Fx|base-R|Fx|kN|
|case-D-node-base-R-Fz|base-R|Fz|kN|
|case-D-node-base-R-My|base-R|My|kN.m|

Applies to every listed row: selection · kind = case; selection · id = D; location · kind = node.

## Analysis conventions

按指定引擎进行一阶线弹性静力分析，采用Euler-Bernoulli弯曲（不计剪切变形）；关闭自重、P-Delta、刚性楼板、刚臂偏移及施工阶段。全局XYZ，Z向上；平面模型位于XZ平面。坐标/位移m，力kN，弯矩kN*m，线载kN/m（按真实杆长），E/G为MPa，密度kg/m^3，A为m^2，Iy/Iz/J为m^4，shape尺寸mm，转角rad。约束顺序ux,uy,uz,rx,ry,rz，true表示固定。梁柱共节点刚接，桁架杆仅传轴力；支座以输入表为准。局部x由构件首节点指向末节点；空间杆局部y为reference vector叉乘局部x的单位向量，局部z=x叉乘y，再按rotation_angle绕局部x转动；平面杆未转轴时局部y为全局+Y、局部z为局部x叉乘局部y，再绕局部x施加rotation_angle；Iy为绕局部y的惯性矩。平面metadata参考向量不采用上述空间叉乘公式。报告局部到全局的转换。杆件位置从首节点计量，side为截面左右极限。N以拉为正；对局部杆端抗力按N,V2,V3,T,M2,M3排序，首节点端乘(-1,+1,+1,-1,-1,-1)、末节点端乘(+1,-1,-1,+1,+1,+1)转换为要求的有符号截面内力，不能取无符号包络替代。逐项报告input.md中数值及派生量，保留符号、单位、工况/组合；绝对值控制量同时给出原符号和控制项/组合。保存可运行输入、引擎版本、/日志及带索引原始结果；这些属于待执行要求，并非已有证据。input.md为完整公开输入附表，不含答案。

## Input decisions

源规划未给定材料及截面数值，现将属性附表明确冻结：Q355钢，E=206000 MPa，nu=0.30，G=E/[2(1+nu)]，密度7850 kg/m^3。实心矩形截面，B为局部y方向宽度、H为局部z方向高度；A、Iy、Iz、J采用附表明示值。采用Euler-Bernoulli弯曲，不计剪切变形；全部构件材料M1。除下列逐题说明另有规定外，梁B1宽0.30m、高0.60m；柱C1为0.50m方形。平面杆局部x由首节点指向末节点，局部y为全局+Y，局部z=x叉乘y；平面内力分量为N、V3、M2。未指定分量的节点位移向量报告ux、uz及转角ry；杆件内力为input.md指定侧的有符号截面合力。跨中观测点通过分段构件真实接入，分段保持原截面和线载强度。除明确支座释放外，全部节点刚接。

屋面梁B1，左右柱C1；左柱脚仅平面转角ry自由，其My反力也必须报告以检查铰支。平面外自由度依二维约定约束，不形成空间结构。
