## Numerical inputs

|Field|Value|
|---|---|
|title|完整数值输入附表|
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
|base-L|0|0|0|true|true|true|true|true|true|
|eave-L|0|0|6|false|true|false|true|false|true|
|ridge|9|0|7.5|false|true|false|true|false|true|
|eave-R|18|0|6|false|true|false|true|false|true|
|base-R|18|0|0|true|true|true|true|true|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|column-L|column|base-L|eave-L|M1|C1|0|[0, 1, 0]|
|slope-L|beam|eave-L|ridge|M1|B1|0|[0, 1, 0]|
|slope-R|beam|ridge|eave-R|M1|B1|0|[0, 1, 0]|
|column-R|column|base-R|eave-R|M1|C1|0|[0, 1, 0]|

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

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-1 → slope-L, D-2 → slope-R|global|distributed|-6|

## Numerical inputs — Load cases — W

|Field|Value|
|---|---|
|id|W|
|type|wind|

## Numerical inputs — Load cases — W — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|W-1 → slope-R|global|distributed|8|

## Numerical inputs — Load combinations

|id|factors · W|
|---|---|
|C0|—|
|C1|1|

Applies to every listed row: factors · D = 1.

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

|id|selection · id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|---|
|combination-C0-node-ridge-ux|C0|node|ridge|ux|m|—|—|
|combination-C0-node-ridge-uz|C0|node|ridge|uz|m|—|—|
|combination-C0-node-ridge-ry|C0|node|ridge|ry|rad|—|—|
|combination-C1-node-ridge-ux|C1|node|ridge|ux|m|—|—|
|combination-C1-node-ridge-uz|C1|node|ridge|uz|m|—|—|
|combination-C1-node-ridge-ry|C1|node|ridge|ry|rad|—|—|
|combination-C0-node-base-L-Fx|C0|node|base-L|Fx|kN|—|—|
|combination-C0-node-base-L-Fz|C0|node|base-L|Fz|kN|—|—|
|combination-C0-node-base-L-My|C0|node|base-L|My|kN.m|—|—|
|combination-C0-node-base-R-Fx|C0|node|base-R|Fx|kN|—|—|
|combination-C0-node-base-R-Fz|C0|node|base-R|Fz|kN|—|—|
|combination-C0-node-base-R-My|C0|node|base-R|My|kN.m|—|—|
|combination-C1-node-base-L-Fx|C1|node|base-L|Fx|kN|—|—|
|combination-C1-node-base-L-Fz|C1|node|base-L|Fz|kN|—|—|
|combination-C1-node-base-L-My|C1|node|base-L|My|kN.m|—|—|
|combination-C1-node-base-R-Fx|C1|node|base-R|Fx|kN|—|—|
|combination-C1-node-base-R-Fz|C1|node|base-R|Fz|kN|—|—|
|combination-C1-node-base-R-My|C1|node|base-R|My|kN.m|—|—|
|combination-C0-member-slope-R-s0-right-N|C0|member|slope-R|N|kN|0|right|
|combination-C0-member-slope-R-s0-right-V3|C0|member|slope-R|V3|kN|0|right|
|combination-C0-member-slope-R-s0-right-M2|C0|member|slope-R|M2|kN.m|0|right|
|combination-C0-member-slope-R-s9.12414379545-left-N|C0|member|slope-R|N|kN|9.12414379544733|left|
|combination-C0-member-slope-R-s9.12414379545-left-V3|C0|member|slope-R|V3|kN|9.12414379544733|left|
|combination-C0-member-slope-R-s9.12414379545-left-M2|C0|member|slope-R|M2|kN.m|9.12414379544733|left|
|combination-C1-member-slope-R-s0-right-N|C1|member|slope-R|N|kN|0|right|
|combination-C1-member-slope-R-s0-right-V3|C1|member|slope-R|V3|kN|0|right|
|combination-C1-member-slope-R-s0-right-M2|C1|member|slope-R|M2|kN.m|0|right|
|combination-C1-member-slope-R-s9.12414379545-left-N|C1|member|slope-R|N|kN|9.12414379544733|left|
|combination-C1-member-slope-R-s9.12414379545-left-V3|C1|member|slope-R|V3|kN|9.12414379544733|left|
|combination-C1-member-slope-R-s9.12414379545-left-M2|C1|member|slope-R|M2|kN.m|9.12414379544733|left|

Applies to every listed row: selection · kind = combination.

## Analysis conventions

按指定引擎进行一阶线弹性静力分析，采用Euler-Bernoulli弯曲（不计剪切变形）；关闭自重、P-Delta、刚性楼板、刚臂偏移及施工阶段。全局XYZ，Z向上；平面模型位于XZ平面。坐标/位移m，力kN，弯矩kN*m，线载kN/m（按真实杆长），E/G为MPa，密度kg/m^3，A为m^2，Iy/Iz/J为m^4，shape尺寸mm，转角rad。约束顺序ux,uy,uz,rx,ry,rz，true表示固定。梁柱共节点刚接，桁架杆仅传轴力；支座以输入表为准。局部x由构件首节点指向末节点；空间杆局部y为reference vector叉乘局部x的单位向量，局部z=x叉乘y，再按rotation_angle绕局部x转动；平面杆未转轴时局部y为全局+Y、局部z为局部x叉乘局部y，再绕局部x施加rotation_angle；Iy为绕局部y的惯性矩。平面metadata参考向量不采用上述空间叉乘公式。报告局部到全局的转换。杆件位置从首节点计量，side为截面左右极限。N以拉为正；对局部杆端抗力按N,V2,V3,T,M2,M3排序，首节点端乘(-1,+1,+1,-1,-1,-1)、末节点端乘(+1,-1,-1,+1,+1,+1)转换为要求的有符号截面内力，不能取无符号包络替代。逐项报告input.md中数值及派生量，保留符号、单位、工况/组合；绝对值控制量同时给出原符号和控制项/组合。保存可运行输入、引擎版本、/日志及带索引原始结果；这些属于待执行要求，并非已有证据。input.md为完整公开输入附表，不含答案。

## Input decisions

源规划未给定材料及截面数值，现将属性附表明确冻结：Q355钢，E=206000 MPa，nu=0.30，G=E/[2(1+nu)]，密度7850 kg/m^3。实心矩形截面，B为局部y方向宽度、H为局部z方向高度；A、Iy、Iz、J采用附表明示值。采用Euler-Bernoulli弯曲，不计剪切变形；全部构件材料M1。除下列逐题说明另有规定外，梁B1宽0.30m、高0.60m；柱C1为0.50m方形。平面杆局部x由首节点指向末节点，局部y为全局+Y，局部z=x叉乘y；平面内力分量为N、V3、M2。未指定分量的节点位移向量报告ux、uz及转角ry；杆件内力为input.md指定侧的有符号截面合力。跨中观测点通过分段构件真实接入，分段保持原截面和线载强度。除明确支座释放外，全部节点刚接。

屋面梁采用B1，柱采用C1。位移向量补充约定为ux、uz、ry；右坡端力明确为平面内N、V3、M2，输出位置覆盖其两端。均布载荷按坡长，不按水平投影折算。
