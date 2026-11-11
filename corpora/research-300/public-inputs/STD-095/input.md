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
|base|0|0|0|true|true|true|true|true|true|
|top|0|0|4.5|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|column|column|base|top|M1|C1|0|[0, 1, 0]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|C30|concrete|30000|12500|0.2|2500|

## Numerical inputs — Sections

|id|type|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|
|C1|rectangular|400.0|400.0|0.16000000000000003|0.002133333333333334|0.002133333333333334|0.0036053333333333345|

Applies to every listed row: name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fz|
|---|---|---|---|
|D-1 → top|global|nodal|-500|

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
|interactions|["说明全局 +Z 向上、uz 负值表示向下缩短，杆轴力 N 拉为正、压为负；本题为一阶静力压缩响应。"]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case-D-node-top-uz|node|top|uz|m|—|—|
|case-D-member-column-s0-right-N|member|column|N|kN|0|right|
|case-D-member-column-s4.5-left-N|member|column|N|kN|4.5|left|
|case-D-node-base-Fz|node|base|Fz|kN|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis conventions

按指定引擎进行一阶线弹性静力分析，采用Euler-Bernoulli弯曲（不计剪切变形）；关闭自重、P-Delta、刚性楼板、刚臂偏移及施工阶段。全局XYZ，Z向上；平面模型位于XZ平面。坐标/位移m，力kN，弯矩kN*m，线载kN/m（按真实杆长），E/G为MPa，密度kg/m^3，A为m^2，Iy/Iz/J为m^4，shape尺寸mm，转角rad。约束顺序ux,uy,uz,rx,ry,rz，true表示固定。梁柱共节点刚接，桁架杆仅传轴力；支座以输入表为准。局部x由构件首节点指向末节点；空间杆局部y为reference vector叉乘局部x的单位向量，局部z=x叉乘y，再按rotation_angle绕局部x转动；平面杆未转轴时局部y为全局+Y、局部z为局部x叉乘局部y，再绕局部x施加rotation_angle；Iy为绕局部y的惯性矩。平面metadata参考向量不采用上述空间叉乘公式。报告局部到全局的转换。杆件位置从首节点计量，side为截面左右极限。N以拉为正；对局部杆端抗力按N,V2,V3,T,M2,M3排序，首节点端乘(-1,+1,+1,-1,-1,-1)、末节点端乘(+1,-1,-1,+1,+1,+1)转换为要求的有符号截面内力，不能取无符号包络替代。逐项报告input.md中数值及派生量，保留符号、单位、工况/组合；绝对值控制量同时给出原符号和控制项/组合。保存可运行输入、引擎版本、/日志及带索引原始结果；这些属于待执行要求，并非已有证据。input.md为完整公开输入附表，不含答案。

## Physical definitions

C30 明确采用 E=30000 MPa、nu=0.2、G=12500 MPa、rho=2500 kg/m³；柱为题定的 400×400 mm 实心矩形。
模型为 XZ 平面柱；柱顶仅有平面模型所需的 uy/rx/rz 约束，ux/uz/ry 自由。
柱轴力在首端 0 m 的右侧与末端 4.5 m 的左侧分别请求，避免把支座反力符号当作压缩轴力符号。
杆件采用一阶线弹性 Euler-Bernoulli 弯曲、轴向变形及有限 Saint-Venant 扭转刚度；不计剪切变形，自重关闭。本题不做二阶、屈曲、承载力或配筋分析。
截面 A、Iy、Iz、J 为附表中的显式 SI 数值，不以软件默认截面属性替换；采用矩形截面时 J 使用输入表给定的冻结近似值。

## Output scope — Required outputs

|id|description|quantityIds|kind|
|---|---|---|---|
|top-shortening|柱顶竖向位移 uz|["case-D-node-top-uz"]|numerical|
|column-axial-force|柱两端截面轴力 N，拉为正、压为负|["case-D-member-column-s0-right-N", "case-D-member-column-s4.5-left-N"]|numerical|
|vertical-base-reaction|固定柱脚竖向反力 Fz|["case-D-node-base-Fz"]|numerical|
|compression-sign-convention|说明全局 +Z 向上、uz 负值表示向下缩短，杆轴力 N 拉为正、压为负；本题为一阶静力压缩响应。|[]|interaction|

Applies to every listed row: state = 1.
