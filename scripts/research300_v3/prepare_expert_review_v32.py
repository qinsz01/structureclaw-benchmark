"""Prepare a deterministic, outcome-blind public-input review sample locally.

The pack contains no private references, model outcomes or automatic judgments.
It does not send invitations, fill human ratings, or certify expert validation.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import shutil

from scripts.research300_v3.prepare_readiness_v32 import public_delivery, relative_file

SEED = 'research300-v3-independent-input-review-20261101'


def select_cases(manifest, per_stratum=5, seed=SEED):
    if type(per_stratum) is not int or per_stratum < 1:
        raise ValueError('Positive integer cases per stratum required')
    groups = defaultdict(list)
    for case in manifest['cases']:
        groups[(case['family'], case['level'])].append(case)
    if set(groups) != {(f, l) for f in ('STD', 'MM', 'INT') for l in ('L1', 'L2', 'L3', 'L4')}:
        raise ValueError('Expected all 12 family/level strata')
    chosen = []
    for key in sorted(groups):
        if len(groups[key]) < per_stratum:
            raise ValueError('Insufficient cases in stratum')
        chosen.extend(sorted(groups[key], key=lambda c: (hashlib.sha256((seed + '\0' + c['id']).encode()).hexdigest(), c['id']))[:per_stratum])
    return chosen


def prepare(edition, output, per_stratum=5, seed=SEED):
    edition = Path(edition).resolve(strict=True)
    output = Path(output).resolve()
    if output.is_relative_to(edition) or edition.is_relative_to(output):
        raise ValueError('New review output must be separate from the frozen edition')
    raw = (edition / 'manifest.json').read_bytes()
    manifest = json.loads(raw)
    cases = select_cases(manifest, per_stratum, seed)
    delivery = public_delivery(edition, manifest)
    selected = {c['id'] for c in cases}
    output.mkdir(parents=True, exist_ok=False)
    blinded = output / 'blinded-public-inputs'
    blinded.mkdir()
    turn_rows, files = [], []
    for row in delivery['turns']:
        if row['caseId'] not in selected:
            continue
        for file in row['files']:
            source = relative_file(edition, file['editionPath'])
            data = source.read_bytes()
            if hashlib.sha256(data).hexdigest() != file['sha256']:
                raise ValueError('Public input changed during review preparation')
            name = f"{row['caseId']}/{row['turnId']}/{file['packetPath']}"
            target = blinded / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            files.append({'path': name, 'sha256': file['sha256']})
        turn_rows.append({'caseId': row['caseId'], 'turnId': row['turnId'], 'reviewerId': None,
                          'independentOfAuthoring': None, 'sourceSufficient': None, 'ambiguities': [],
                          'interpretedModelFile': None, 'unitsAndLoadDerivationFile': None,
                          'revisionConsistency': None, 'scopeSupported': None,
                          'sourceLocations': [], 'notes': None})
    instructions = (
        '独立公开输入盲审（未完成）\n\n'
        '由两名未参与题目/参考模型编写的结构工程师分别完成。审阅前不要提供私有参考、候选身份、候选输出或成绩。\n'
        '按 t1、t2…顺序审阅每题，先独立重建几何、连接、支承、材料截面、荷载/质量及本轮变更，记录原文件位置、单位换算和歧义。\n'
        'review-template.jsonl 的空值由实际审阅者填写，不能用模型或维护者自动填充。建议分别复制为 reviewer-A/B 的工作目录。\n'
        '第一阶段提交独立解释并封存后，控制端再提供参考和比较规则进行第二阶段核对；记录分歧及第三人仲裁。\n'
        '本批按 family × level 等额抽样，适合覆盖检查；未经分层权重调整不能将样本一致率当作全库一致率。\n'
        '此包仅验证公开输入/参考的有效性，不是旧 GLM 语义裁判校准，也不是用户可用性研究。\n'
    )
    (blinded / 'REVIEW-INSTRUCTIONS.txt').write_text(instructions)
    with (blinded / 'review-template.jsonl').open('x') as handle:
        for row in turn_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    result = {'kind': 'research300-v3-expert-review-preparation', 'manifestSha256': hashlib.sha256(raw).hexdigest(),
              'selectionSeed': seed, 'selectionUsesCandidateOutcomes': False, 'casesPerStratum': per_stratum,
              'cases': len(cases), 'turns': len(turn_rows), 'selectedCaseIds': [c['id'] for c in cases],
              'engineCounts': dict(Counter(c['engine'] for c in cases)),
              'originCounts': dict(Counter(c['origin'] for c in cases)),
              'externalExpertReviewCompleted': False, 'ratingsFilled': 0, 'privateFilesCopied': 0,
              'publicFiles': files, 'candidateInvocations': 0, 'nativeSolverInvocations': 0}
    (output / 'controller-selection.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return {k: v for k, v in result.items() if k != 'publicFiles'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edition', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases-per-stratum', type=int, default=5)
    parser.add_argument('--seed', default=SEED)
    args = parser.parse_args()
    print(json.dumps(prepare(args.edition, args.output, args.cases_per_stratum, args.seed), ensure_ascii=False))
