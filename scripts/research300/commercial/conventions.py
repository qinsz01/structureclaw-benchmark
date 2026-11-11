"""Version the commercial authoring convention without changing numeric inputs.

Shared by the author generators and the explicit corpus migration. This writes
public text and its contract only; reference/evidence regeneration is separate.
"""
from copy import deepcopy
import json
from pathlib import Path

from reference_cli import COMMERCIAL_SHEAR_CONVENTION


TEXT_EN = """Commercial elastic analysis convention: commercial-linear-static-v2

Use the specified native engine for first-order, small-displacement, linear
elastic static analysis with Timoshenko bending. For every beam and column,
the prescribed effective shear areas are Asy = Asz = 5*A/6, in m^2. A is the
explicit cross-sectional area in the currently available property appendix;
Asy acts for local-y shear V2 and Asz for local-z shear V3. This is a prescribed
benchmark idealization, including generalized numerical sections, rather than
an inference from a section name. Apply it to each newly supplied or edited
section. Truss/brace members retain their specified axial-only behavior.

Retain the supplied E, G, A, Iy, Iz and J, geometry, connectivity, supports,
loads and load selections. Use gross uncracked concrete stiffness where stated.
Preserve the stated local axes, member-end cut signs and units. Self-weight,
rigid floors, rigid offsets, P-Delta and construction stages remain off.

Use explicit elastic stiffness rather than silently substituting a native
material grade's defaults. A native representation using equivalent EA,
G*Asy, G*Asz, GJ, E*Iy and E*Iz must retain the supplied physical definitions
and report the actual native material/section values, modifiers and numerical
serialization differences. Equivalent elastic stiffness does not assert
identical literal material fields or qualify stress/design calculations.
Retain native input, settings, engine/version, logs and raw result evidence.
This appendix supplies analysis inputs, not computed answers or acceptance.
"""

TEXT_ZH = """商业引擎弹性分析约定：commercial-linear-static-v2

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
"""



def _rewrite(text):
    for old, new in (
        ("(no shear deformation)", "(with prescribed finite shear areas)"),
        ("（不计剪切变形）", "（计入规定的剪切变形）"),
        ("Euler-Bernoulli", "Timoshenko"),
        ("Euler–Bernoulli", "Timoshenko"),
        ("Euler—Bernoulli", "Timoshenko"),
    ):
        text = text.replace(old, new)
    return text


def revise_authored_case(case_dir):
    """Revise a commercial candidate's public convention; preserve numeric files.

    Call after an author generator has written all public inputs. Regenerate
    diagnostic references separately, retaining their old provenance in history.
    """
    root = Path(case_dir)
    contract_file = root / "contract.json"
    original = contract_file.read_text(encoding="utf-8")
    contract = json.loads(original)
    if contract["plannedEngine"] not in ("PKPM", "YJK"):
        return []
    source = json.dumps(contract["sourcePlan"], ensure_ascii=False)
    if any(word in source for word in ("Euler-Bernoulli", "Euler–Bernoulli", "Euler—Bernoulli", "不计剪切变形")):
        raise ValueError("Source requirements explicitly name shear-free physics; revision is not applicable")
    changes = {}
    for name in sorted(set(["prompt.txt", *contract["attachments"]])):
        if Path(name).suffix.lower() not in (".txt", ".md", ".json"):
            continue
        old = (root / name).read_text(encoding="utf-8")
        if _rewrite(old) != old:
            changes[name] = _rewrite(old)
    appendix = COMMERCIAL_SHEAR_CONVENTION["publicAttachment"]
    text = TEXT_EN if contract["locale"] == "en" else TEXT_ZH
    if not (root / appendix).exists() or (root / appendix).read_text(encoding="utf-8") != text:
        changes[appendix] = text
    for turn in contract["turns"]:
        turn["instruction"] = _rewrite(turn["instruction"])
    for attachments in (contract["attachments"], contract["turns"][0]["attachments"]):
        if appendix not in attachments:
            attachments.append(appendix)
    contract["analysisConvention"] = deepcopy(COMMERCIAL_SHEAR_CONVENTION)
    for coverage in contract.get("requirementCoverage", []):
        if coverage["sourceField"] == "engine.analysisContract":
            target = "attachment:" + appendix
            if target not in coverage["targets"]:
                coverage["targets"].append(target)
    if "authoringNotes" in contract:
        contract["authoringNotes"] = [_rewrite(note) for note in contract["authoringNotes"]]
    encoded = json.dumps(contract, ensure_ascii=False, indent=2) + "\n"
    if encoded != original:
        changes["contract.json"] = encoded
    for name, value in changes.items():
        (root / name).write_text(value, encoding="utf-8")
    return list(changes)
