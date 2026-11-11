"""Build a proposed 300-case catalogue, without modifying a released corpus."""
from collections import Counter
import csv
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'planning' / 'research300-v2'
SUT = 'db3c0b1da44fe668a6037a6c2e7f068d14354539'

# Each line is an individually proposed task, not a generated numerical case.
# The six blocks per family have 15/20/15/30/10/10 entries respectively.
BRIEFS = {
 'STD': [
 """简支梁全跨均布荷载的反力与挠度
悬臂梁端力的位移与根部弯矩|point
双端固定梁跨中集中力|point
简支梁非对称节点集中力
两跨连续梁单跨加载
外伸梁端部节点力
竖直杆轴向伸长与约束反力
平面折梁刚接节点的位移连续
局部均布荷载下的观测截面|interior
分段线性荷载的合力与弯矩|interior
误将梁端铰当支座铰的定位与修正|release,audit
连续梁单支座显式沉降|settlement
异材分段梁的刚度与连续条件
连续梁多活载布置的控制工况|selections
三个定截面梁方案的挠度及材料用量比选|choose""",
 """单层单跨平面框架的水平节点力
两跨等高框架的竖向荷载
不等跨裸框架的支反力
坡顶刚接框架的节点位移
带外伸梁的平面设备架
双层框架分层材料与指定工况的自动自重|gravity
框架局部梁端弯曲释放|release
坡梁全局荷载被错误局部化的定位与修复|axes,audit
跨内点载及部分线载联合加载|interior
框架恒活载明示组合的有符号结果|selections
单层框架显式节点质量的第一周期|modal
两层框架两种质量分配的周期比较|modal
双跨框架支座不均匀沉降|settlement
冷库横向定截面分析子问题的雪活载互斥|selections
不等高设备架的分组截面修订
三层框架刚度分布与模态参与质量|modal
显式单向输入下平面框架线弹性时程|transient
两个平面框架备选方案的位移约束比选|choose
工业裸框架时程的相对位移与绝对加速度|transient
多跨设备架的工况包络及方案选择|choose,selections""",
 """三角桁架的节点荷载平衡
四节间平行弦桁架的杆轴力
人字形桁架的节点位移
单斜杆体系的轴向刚度
非对称三角桁架的支反力
Pratt 桁架非均匀节点荷载
Howe 桁架上弦节点荷载
Warren 桁架分区材料
扇形桁架的端点连接与力流
双坡屋架按明示规则分配屋面节点力
桁架节点荷载工况组合|selections
屋架设备节点力重复计入的审查与重算|audit
不同弦杆截面的变形与轴力分配
三个桁架截面分组方案的线弹性比选|choose
带非对称腹杆的屋架偏载与控制杆件|selections""",
 """单层空间裸框架的显式节点质量|modal
双层空间框架的双向周期及质量来源|modal
矩形空间框架双向节点力
空间框架分层材料与截面
空间框架局部坐标与扭转|axes
空间框架屋面设备偏置节点力
三层办公裸框架恒活载分离|selections
小型教学楼裸框架双向显式水平力
四层仓储裸框架楼层截面分组
设备楼裸框架屋面附加节点荷载
等高双跨裸框架柱截面朝向|axes
不等跨裸框架明示受荷宽度
三层裸框架自定义带符号组合|selections
两翼裸框架指定支座六分量
空间裸框架单向线弹性输入的指定节点响应|transient
非共面设备架的局部轴及六分量荷载|axes
空间设备架有限长度外伸段连接错误审查|audit
三个空间框架截面方案的位移限值比选|choose
偏载楼层裸框架跨内荷载与观测|interior
局部屋面设备裸框架正反水平力|selections
分区办公裸框架材料清单重建
不同柱刚度裸框架的荷载分配
厂房附属裸框架多组合控制位置|selections
机房裸框架显式自重折算与附加恒载分离
双向支承裸框架的局部截面力符号|axes
楼层分段截面裸框架的工程修订单
设备楼裸框架备选截面的响应约束比选|choose
仓储裸框架多区荷载包络与关键构件|selections
教学楼裸框架多资料修订后的响应复核
办公楼裸框架资料重建与明示限值筛查""",
 """四杆空间星形桁架的节点平衡
四角锥桁架的竖向节点力
双四角锥桁架的连接表
空间桁架顶点偏心节点力
空间桁架不同杆组截面
空间桁架显式节点质量的模态|modal
桁架三向节点力与局部轴力符号|axes
设备支承空间桁架的多工况|selections
空间桁架的受限截面方案比较|choose
多单元空间桁架的节点载荷传递与控制杆件""",
 """单斜撑弹性框架的侧向刚度
双向弹性斜撑与柱弯曲共同受力
框架与轴力杆连接的转角自由度
设备支架异材杆组与恒活载|selections
带双向弹性斜撑框架的线性时程|transient
光伏支架线弹性子模型的面载传递
通廊裸框架与双向弹性支撑的偏载
光伏支架截面备选方案的位移约束比选|choose
设备平台轴力杆误建为梁的定位与修正|audit
工业支架多工况、局部轴与方案比较|choose,selections""",
 ],
 'MM': [
 """从简支符号图恢复梁支承自由度
从悬臂图识别端部力的方向
从双端固支图读取跨中集中力|point
从外伸梁图识别加载端点
从连续梁图区分跨中节点与支座
从折梁图识别真正的刚接节点
从分段梁图绑定两种截面
从竖直杆图识别轴向受力
从荷载阴影图读取局部受荷区间|interior
从多段箭头图读取分段线载|interior
从连接详图识别梁端弯曲释放|release
从修订标注图读取显式支座位移|settlement
根据反向编号图修正候选模型的局部力符号|axes,audit
从多跨荷载图选择控制工况|selections
从三个梁方案图比较明示挠度与用量|choose""",
 """从立面图重建单层单跨框架
从两跨立面图恢复真实共节点
从坡顶图读取节点标高
从带悬臂图识别连接与外伸段
从框架表格绑定柱梁截面
从节点详图区分局部铰与支座铰|release
根据不等高框架图定位候选模型的标高错误|audit
从梁荷载图读取跨内点载位置|interior
从两份荷载表绑定工况和组合|selections
从多视图恢复设备框架及指定工况的自动自重|gravity
从质量标注图建立单层框架模态模型|modal
从两层质量表与立面恢复模态模型|modal
从地基变位通知图录入支座位移|settlement
从冷库横向资料提取定截面雪载子问题|selections
从截面修订图定位受影响构件组
从不规则层高图与节点质量表求模态|modal
从设备架双立面辨认两个横向振型|modal
从方案图表选择满足位移限制的轻量框架|choose
从振动输入附件与立面重建线性时程模型|transient
从工业框架图纸、修订单与组合表完成复核""",
 """从三角桁架图恢复杆件连接
从平行弦桁架图读取加载节点
从人字形桁架图识别顶点位置
从拉压杆简图区分节点力与杆力
从非对称桁架图识别铰滚支座
从 Pratt 屋架标注图恢复节间
从 Howe 屋架图读取腹杆方向
从 Warren 图与杆组表绑定面积
从扇形桁架图读取汇交关系
从屋面图按指定分担规则生成节点力
根据断开的交叉线修正候选模型的伪连接|audit
从桁架 DXF 过滤非结构尺寸线
从屋架设备表定位下弦节点力
从两组屋架方案图比较位移及杆件用量|choose
从不对称屋架图与偏载表提取控制轴力|selections""",
 """从空间裸框架图与显式质量表求模态|modal
从双层框架多视图识别双向周期|modal
从轴测图恢复空间框架节点
从楼层表与平面图绑定截面
从构件截面方向图解释双轴弯曲|axes
从屋面设备坐标表恢复偏置荷载
从办公裸框架平立面分离恒活载|selections
从教学楼裸框架图读取双向水平力
从仓储裸框架截面表恢复楼层分组
从机房裸框架图绑定设备节点力
从柱截面朝向图选择正确弯曲轴|axes
从不等跨裸框架图提取受荷宽度
从裸框架组合表保持反向荷载符号|selections
从支座详图恢复空间框架反力分量
从设备楼图与输入记录恢复线弹性时程|transient
从非正交设备架图恢复显式局部参考轴|axes
根据多视图修正候选模型缺失的有限外伸段|audit
从备选截面表选择满足裸框架位移限值的方案|choose
从楼层偏载图读取部分线载及观测点|interior
从屋面设备布置与正反水平力表形成组合|selections
从图纸和材料表识别分区裸框架
从不同柱尺寸图检查侧向荷载分配
从厂房附属框架图筛选控制工况|selections
从机房恒载表识别显式自重是否重复
从杆件编号与局部轴图读取端力符号|axes
从签发修订单重建楼层分段截面
从设备楼方案图完成响应约束比选|choose
从仓储区多图识别控制荷载区域|selections
从教学楼裸框架多视图与修订表建立终版模型
从办公裸框架图纸包完成明示限值筛查""",
 """从四杆星形轴测图恢复节点坐标
从四角锥图识别受力节点
从双四角锥图识别共边与共节点
从空间桁架图读取偏置节点力
从杆组表区分空间桁架截面
从节点质量图恢复空间桁架模态|modal
从反向编号图恢复轴力符号|axes
从设备支承空间桁架图绑定多个工况|selections
从备选杆组图比较空间桁架用量与位移|choose
从网架式杆系多视图与节点力表核对力流""",
 """从斜撑框架图区分轴力杆与梁柱
从双向弹性支撑图恢复连接关系
从交叉支撑投影图区分相交与连接
从设备支架图绑定异材杆组
从支撑框架图与激励附件求线性时程|transient
从光伏支架图与面载表重建线性子问题
从通廊支架图识别显式偏载工况|selections
从光伏截面目录图选择满足位移限值的方案|choose
根据设备平台图修正误建为梁的轴力杆|audit
从工业支架图纸包完成多工况方案复核|choose,selections""",
 ],
 'INT': [
 """简支梁荷载确认后只修改荷载大小
悬臂梁端力修改后查询旧位置
固定梁补齐明确截面参数再计算
外伸梁端点编号确认后求解
连续梁追加工况并保留原工况|selections
折梁确认连接节点后修订节点力
轴向杆补齐 E 与 A 后计算
分段梁只替换指定截面
部分线载重复录入的定位、删除与局部更新|interior,audit
分段线载替换一段并保留其他段|interior
梁端弯曲释放确认及撤销|release
支座沉降确认后只修改位移值|settlement
分段梁自动自重工况与截面更新|gravity
梁工况与同名组合的定向修改|selections
梁方案位移限值更新后重新比较|choose""",
 """单跨框架只修改柱高
两跨框架只替换一根梁截面
坡顶框架补齐一个节点标高
设备架确认新增构件的端点
框架查询从位移改为反力且不改模型
框架局部梁端铰确认后求解|release
双层框架材料更新与成员组消歧
跨内点载位置误写后的定位、修正与撤销|interior,audit
明示水平力反向后保留竖向工况|selections
框架线载作用长度基准确认|interior
节点质量来源确认后求框架周期|modal
框架质量更新但保持刚度的模态比较|modal
支座沉降后撤销截面修改但保留沉降|settlement
冷库分析子问题中雪活载互斥条件更新|selections
不等高框架几何修订与荷载归属保持
三层框架仅修改一层质量后比较模态|modal
双向振型查询单位修改且保持质量模型|modal
框架备选方案可行域改变后重新选择|choose
时程激励单位确认后再分析|transient
工业裸框架六轮几何、荷载及选择性撤销""",
 """三角桁架只修改一个节点力
平行弦桁架补齐杆面积后求解
人字形桁架确认顶点坐标
轴力杆体系查询保留正负号
非对称桁架确认滚支方向
Pratt 屋架新增节点力并保留旧载荷
Howe 屋架只修改一组腹杆面积
Warren 桁架截面组目标消歧
扇形桁架修订一个连接端点
屋架受荷宽度更新后重建节点力
桁架组合引用错误工况的定位与定向修复|selections,audit
屋架设备荷载移位后保留屋面工况
桁架弦杆改材与腹杆改截面分别撤销
桁架方案位移限值改变后的比选|choose
不对称屋架偏载修订与控制杆件复核|selections""",
 """空间裸框架补齐质量来源后求模态|modal
空间框架修改一个方向质量设置后查询周期|modal
空间框架双向节点力分别更新
空间框架仅修改指定楼层材料
柱截面转角冲突确认后计算|axes
设备节点力迁移但保持构件拓扑
办公裸框架恒活载工况定向替换|selections
教学楼裸框架只修改 X 向水平力
仓储裸框架楼层截面组目标确认
设备楼裸框架追加设备节点力
裸框架柱截面转向与材料修改分别撤销|axes
裸框架受荷宽度更新与荷载替换
裸框架组合重命名但不更改系数|selections
裸框架结果单位修改而保持物理状态
空间裸框架替换激励记录后重算时程|transient
空间设备架错误局部参考轴的修正与载荷保持|axes,audit
外伸设备架改长后保持指定物理观测位置
空间框架方案目录修订后的可行性重选|choose
裸框架局部线载位置与大小分别修改|interior
裸框架正反水平力工况追加与撤销|selections
分区办公裸框架材料修订单局部覆盖
裸框架改柱截面后保留既有荷载
厂房附属框架组合系数修订与包络复查|selections
机房裸框架删除重复显式自重并保持附加载荷|audit
裸框架改编号后查询同一物理端截面|axes
楼层截面和节点力更新后选择性撤销
设备楼备选截面与位移限值连续修订|choose
仓储裸框架六轮荷载区域更新与控制工况|selections
教学楼裸框架多份修订单优先级确认后求解
办公裸框架分步补齐资料、修订及终版筛查""",
 """空间星形桁架补齐一个节点坐标
四角锥桁架修改竖向节点力
双四角锥桁架确认共节点关系
空间桁架节点力移位与截面保持
空间桁架杆组改材与轴力查询
空间桁架质量来源更正后的模态比较|modal
空间桁架重新编号后保持力的正负号|axes
设备支承桁架追加并撤回一个组合|selections
空间桁架方案约束更新后的比选|choose
空间多单元桁架跨视图连接冲突确认及修复""",
 """弹性斜撑框架改杆面积但保持梁柱
支撑框架轴力杆类型确认后求解
交叉支撑修改端点且保持交叉不连接
设备支架分组材料与节点力分别更新
支撑框架阻尼比更改后的线性时程|transient
光伏支架线性子问题改倾角后重建明示荷载
通廊支架新增工况与旧组合保持|selections
光伏支架方案目录修订及位移约束比选|choose
设备平台多轮改材、移载及局部撤销
工业支架六轮方案选择与最终响应复核|choose,selections""",
 ],
}

STRUCTURES = [
 ('beam', '梁与折梁', '2D', [(8,'L1'),(5,'L2'),(2,'L3')]),
 ('planar-frame', '平面框架', '2D', [(5,'L1'),(7,'L2'),(6,'L3'),(2,'L4')]),
 ('planar-truss', '平面桁架', '2D', [(5,'L1'),(6,'L2'),(4,'L3')]),
 ('spatial-frame', '空间裸框架', '3D', [(14,'L2'),(12,'L3'),(4,'L4')]),
 ('spatial-truss', '空间桁架', '3D', [(2,'L1'),(4,'L2'),(3,'L3'),(1,'L4')]),
 ('mixed-frame-brace', '梁柱与双向弹性轴力杆', '3D', [(4,'L2'),(3,'L3'),(3,'L4')]),
]
EXTRA_CAPABILITIES = {
 'point': 'member-point-load', 'interior': 'member-interior-loads',
 'release': 'elastic-bending-release', 'settlement': 'prescribed-displacement',
 'axes': 'explicit-local-axes', 'selections': 'explicit-cases-combinations',
 'gravity': 'explicit-self-weight-case',
 'modal': 'elastic-modal', 'transient': 'elastic-time-history',
}
COMMERCIAL_POSITIONS = list(range(6,14)) + list(range(18,30))
SOURCE_REVIEW = '../../docs/implementation/reviews/external-challenge-sources-20261028/README.md'


def build():
    rows = []
    for family, blocks in BRIEFS.items():
        sequence = 0
        for block, (structure, label, dimension, levels) in zip(blocks, STRUCTURES):
            briefs = block.strip().splitlines()
            difficulties = [level for count, level in levels for _ in range(count)]
            assert len(briefs) == len(difficulties), (family, structure, len(briefs))
            for position, (brief, difficulty) in enumerate(zip(briefs, difficulties)):
                sequence += 1
                title, _, suffix = brief.partition('|')
                tags = suffix.split(',') if suffix else []
                assert set(tags) <= set(EXTRA_CAPABILITIES) | {'choose','audit'}
                engine = 'OpenSees'
                if structure == 'spatial-frame' and position in COMMERCIAL_POSITIONS:
                    engine = ('PKPM','YJK')[COMMERCIAL_POSITIONS.index(position) % 2]
                analysis = 'modal' if 'modal' in tags else 'linear-time-history' if 'transient' in tags else 'linear-static'
                task = 'bounded-scheme-selection' if 'choose' in tags else 'model-audit' if 'audit' in tags else 'reconstruct-and-analyze'
                capabilities = [f'elastic-{structure}', 'explicit-properties', 'signed-results', 'actual-execution']
                capabilities += [EXTRA_CAPABILITIES[t] for t in tags if t in EXTRA_CAPABILITIES]
                if analysis != 'linear-static': capabilities += ['explicit-mass-source']
                if engine != 'OpenSees': capabilities += ['native-rectangular-frame-subset']
                case = {
                    'id': f'R300V2-{family}-{sequence:03}', 'family': family,
                    'title': title, 'structure': structure, 'structureLabel': label,
                    'dimension': dimension, 'difficulty': difficulty,
                    'engine': engine, 'analysis': analysis, 'task': task,
                    'requiredCapabilities': capabilities,
                    'plannedTurns': {'L1':2,'L2':3,'L3':4,'L4':6}[difficulty] if family == 'INT' else 1,
                    'input': 'text-and-explicit-tables' if family != 'MM' else 'unassigned',
                    'provenance': 'unassigned', 'sourceId': None,
                    'sourceStatus': 'not-selected', 'sourceProjectGroup': None,
                    'topologyFingerprint': None, 'split': 'unassigned',
                    'referenceMethod': 'independent-K-M-eigenproblem' if analysis == 'modal' else
                        'independent-linear-EOM-and-time-step-check' if analysis == 'linear-time-history' else
                        'closed-form-or-independent-matrix-plus-same-engine-reference',
                    'gradingProfile': 'finite-scheme-feasibility-and-minimum-volume' if 'choose' in tags else
                        'modal-frequency-mass-and-sign-invariant-shape' if analysis == 'modal' else
                        'time-series-units-reference-frame-and-equilibrium' if analysis != 'linear-static' else
                        'physical-equivalence-signed-response-and-evidence',
                    'toolchainStatus': 'requires-case-specific-public-worker-preflight',
                    'evaluatorStatus': 'profile-implementation-and-positive-negative-controls-required',
                    'authored': False, 'referenceReady': False,
                    'nativeVerified': False, 'inputReviewed': False,
                    'accepted': False, 'modelTrialStatus': 'not-run',
                }
                rows.append(case)
        assert sequence == 100
        family_rows = [r for r in rows if r['family'] == family]
        # The engineering quota is a sourcing target, never an authenticity claim.
        for difficulty, count in [('L1',20),('L2',10),('L3',10),('L4',10)]:
            candidates = [r for r in family_rows if r['difficulty'] == difficulty]
            candidates.sort(key=lambda r: (not any(word in r['title'] for word in ('光伏','冷库')), r['id']))
            for r in candidates[:count]:
                r['provenance'] = 'original-teaching' if difficulty == 'L1' else 'engineering-adaptation-target'
                if difficulty == 'L1': r['sourceStatus'] = 'original-brief-to-author'
        for r in family_rows:
            if r['provenance'] == 'unassigned':
                r['provenance'] = 'original-composite'
                r['sourceStatus'] = 'original-brief-to-author'
            if r['provenance'] == 'engineering-adaptation-target':
                if '光伏' in r['title']:
                    r['sourceId'] = 'S02'
                    r['sourceStatus'] = 'public-report-read-native-model-not-qualified'
                elif '冷库' in r['title']:
                    r['sourceId'] = 'S03'
                    r['sourceStatus'] = 'public-report-read-complete-input-not-qualified'
        mm = [r for r in family_rows if family == 'MM']
        for i, r in enumerate(mm):
            r['input'] = ('raster-schematic-and-properties' if i < 30 else
                'raster-drawings-with-tables' if i < 60 else
                'dxf-with-explicit-analysis-appendix' if i < 80 else 'raster-multiview-with-tables')
    counts = {field: dict(Counter(r[field] for r in rows)) for field in
              ['family','difficulty','engine','analysis','dimension','structure','provenance','task']}
    return {
        'schemaVersion': 1, 'edition': 'research300-v2-proposal-20261028',
        'status': 'planning-only-not-a-runnable-corpus', 'sutCommit': SUT,
        'sourceReview': SOURCE_REVIEW, 'cases': rows,
        'summary': {'cases': len(rows), 'plannedTurns': sum(r['plannedTurns'] for r in rows),
                    'authored': 0, 'accepted': 0, 'candidateRuns': 0, 'counts': counts},
    }


def validate(data):
    rows = data['cases']
    counts = data['summary']['counts']
    assert len(rows) == len({r['id'] for r in rows}) == len({r['title'] for r in rows}) == 300
    assert counts['family'] == {'STD':100,'MM':100,'INT':100}
    assert counts['difficulty'] == {'L1':60,'L2':120,'L3':90,'L4':30}
    assert counts['engine'] == {'OpenSees':240,'PKPM':30,'YJK':30}
    assert counts['analysis'] == {'linear-static':270,'modal':20,'linear-time-history':10}
    assert counts['dimension'] == {'2D':150,'3D':150}
    assert counts['provenance'] == {'original-teaching':60,'original-composite':150,'engineering-adaptation-target':90}
    assert counts['task'] == {'reconstruct-and-analyze':260,'bounded-scheme-selection':25,'model-audit':15}
    assert data['summary']['plannedTurns'] == 540
    for family in BRIEFS:
        subset = [r for r in rows if r['family'] == family]
        assert Counter(r['difficulty'] for r in subset) == {'L1':20,'L2':40,'L3':30,'L4':10}
        assert Counter(r['engine'] for r in subset) == {'OpenSees':80,'PKPM':10,'YJK':10}
    for r in rows:
        if r['engine'] != 'OpenSees':
            assert r['structure'] == 'spatial-frame' and r['analysis'] == 'linear-static'
            assert not {'elastic-bending-release','prescribed-displacement','elastic-modal','elastic-time-history'} & set(r['requiredCapabilities'])
        assert not any(r[k] for k in ['authored','referenceReady','nativeVerified','inputReviewed','accepted'])
        assert r['modelTrialStatus'] == 'not-run'
        assert r['topologyFingerprint'] is None and r['sourceProjectGroup'] is None
    return data


def write(data):
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST/'catalogue.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    fields = ['id','family','title','structureLabel','dimension','difficulty','engine','analysis',
              'task','plannedTurns','input','provenance','sourceId','sourceStatus','referenceMethod',
              'gradingProfile','toolchainStatus','evaluatorStatus','authored','accepted']
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out,fieldnames=fields,extrasaction='ignore',lineterminator='\n')
    writer.writeheader(); writer.writerows(data['cases'])
    (DEST/'catalogue.csv').write_text('\ufeff'+out.getvalue())
    lines = ['# 新版 300 题逐题规划目录', '',
             '规划稿：未编制正式题面、未生成参考解、未逐题验收，也没有候选成绩。见 [规划说明](README.md)。','']
    for family in BRIEFS:
        lines += [f'## {family}', '', '| 编号 | 题目 | 难度 | 引擎 | 分析 | 轮数 |', '| --- | --- | --- | --- | --- | ---: |']
        lines += [f"| {r['id']} | {r['title']} | {r['difficulty']} | {r['engine']} | {r['analysis']} | {r['plannedTurns']} |"
                  for r in data['cases'] if r['family'] == family]
        lines.append('')
    (DEST/'catalogue.md').write_text('\n'.join(lines).rstrip()+'\n')


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write',action='store_true',help='Write the proposed catalogue, never a released corpus')
    args=p.parse_args()
    proposed=validate(build())
    if args.write: write(proposed)
    else:
        assert json.loads((DEST/'catalogue.json').read_text()) == proposed, 'Catalogue differs from source briefs'
    print(json.dumps(proposed['summary'],ensure_ascii=False,indent=2))
