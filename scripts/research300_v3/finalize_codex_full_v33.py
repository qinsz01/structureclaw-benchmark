"""Seal the completed full-run review only after every cold replay succeeds."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import time
import zipfile

from .finish_codex_full_v32 import alive

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read(p):
    return json.loads(p.read_bytes())


def sha(p):
    digest = hashlib.sha256()
    with p.open('rb') as f:
        while block := f.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def write(p, data):
    with p.open('x') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    a = parser.parse_args()
    report, work = a.report.resolve(), a.work.resolve()
    own_source = sha(Path(__file__))
    waits = [('postprocess-launch.json', 'postprocess-summary.json'),
             ('final-review-launch.json', 'review-cold-replay.json'),
             ('policy-v33/completion-launch.json', 'policy-v33/completion-summary.json')]
    for launch_name, result_name in waits:
        pid = read(report / launch_name)['pid']
        while not (report / result_name).exists():
            if not alive(pid):
                raise RuntimeError('Required pipeline stopped without result: ' + result_name)
            time.sleep(10)
        while alive(pid):
            time.sleep(2)
    assert sha(Path(__file__)) == own_source
    raw = read(report / 'postprocess-summary.json')
    raw_replay = read(report / 'replay/cold-replay.json')
    reviewed_replay = read(report / 'review-cold-replay.json')
    revised_replay = read(report / 'policy-v33/completion-summary.json')
    controls = read(report / 'controls-summary.json')
    native = read(report / 'native-inspection-summary.json')
    failures = read(report / 'failure-review.json')
    results = read(report / 'results-summary.json')
    final = read(report / 'policy-v33/diagnostic-v33.json')
    measured = read(report / 'policy-v33/continuous-observations-v33.json')
    recovery = read(report / 'transport-recovery/candidate-rerun/recovery-complete.json')
    cleanup = read(report / 'transport-recovery/agent-socket-cleanup.json')
    extra = read(report / 'extra-review-summary.json')
    assert raw['deterministicStagesCompleted'] and not raw['nativeInspectionErrors']
    assert raw_replay['diagnosticBytesIdentical'] and raw_replay['allFieldsIdentical']
    assert reviewed_replay['allBytesIdentical'] and revised_replay['allBytesIdentical']
    assert controls['allPassed'] and final['policyRevision']['allControlsPassed']
    assert native['cases'] == 300 and native['issuedTurns'] == 560 and native['isolationChecks'] == 8400
    assert native['allSuccessfulNativeProofsValid'] and not native['inspectionErrors']
    assert failures['originalNonpassedTurns'] == 96 and failures['unresolvedAttributions'] == 0
    assert failures['reviewScriptSha256'] == sha(HERE / 'assemble_codex_full_review_v33.py')
    assert results['v33Counts'] == final['counts'] == revised_replay['counts']
    assert recovery['coldReplayIdentical'] and recovery['counts']['passed'] == 6 and not recovery['replacesOriginalScores']
    assert cleanup['aliasRemoved'] and not cleanup['originalTargetRemoved']
    assert [s['stage'] for s in extra['stages'] if s['exitCode']] == ['worked-trace']
    edge = read(report / 'edge-case-failure-review.json')
    assert len(edge['signedReportFailures']) == 2 and len(edge['rigidLoadFailures']) == 4
    assert (report / 'worked-trace-v2.md').is_file()
    source_sets = [raw['postprocessSource'], reviewed_replay['sources'], revised_replay['sources'], extra['sources']]
    for source in source_sets:
        for name, digest in source.items():
            assert sha(HERE / name) == digest, 'Final source mismatch: ' + name
    # All original execution/scoring dependencies also remain exactly bound.
    binding = read(work / 'source-binding.json')
    for relative, digest in {**binding['evaluationCode'], **binding['controllerCode']}.items():
        assert sha(ROOT / relative) == digest, 'Frozen source changed: ' + relative
    validation = subprocess.run(['git', '-c', 'safe.directory=' + str(ROOT), 'diff', '--check'], cwd=ROOT, capture_output=True, text=True)
    assert validation.returncode == 0, validation.stdout + validation.stderr
    git_head = subprocess.check_output(['git', '-c', 'safe.directory=' + str(ROOT), 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    archive = report / 'final-review-source-snapshot.zip'
    final_sources = {n: sha(HERE / n) for n in ['assemble_codex_full_review_v33.py', 'finalize_codex_full_v33.py']}
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
        for name in final_sources:
            z.write(HERE / name, (HERE / name).relative_to(ROOT).as_posix())
    counts = final['counts']
    lines = [
        '# Codex 全量实测与评估复核', '',
        f"300 题、560 轮均已由实际 Codex 尝试。冻结 v3.2 评分为 464/560 轮通过；发现并单独修正六轮工况复用误拒后，v3.3 为 **{counts['passed']}/560（{100*counts['passed']/560:.1f}%）**，{counts['candidate_failure']} 轮作答失败、{counts['blocked_configuration']} 轮环境阻塞；**257/300 题**全部轮次通过。全部原始结果和分母保留。", '',
        '本次是冻结题库与固定原生适配器上的 Codex 接入、评分和证据回归。模型为 `gpt-6.1-sol`、high，CLI 0.164.0；原生 SUT 固定为 `db3c0b1da44fe668a6037a6c2e7f068d14354539`。它不是最新 `research_next` 整系统的正式对比，也不是未见留出集成绩。v3.3 是本轮发现问题后的事后修订，`formalComparisonScore` 始终为 false。', '',
        '## 直接查看', '',
        '- [300 题／560 轮评测表：题面、原始作答、评分及证据链接](policy-v33/review/catalogue-clarified.xlsx)',
        '- [全部 96 个原始未通过轮次的逐项归因](failure-review.json)',
        '- [真实例子：软件算对，但报告抄错了弯矩符号](worked-trace-v2.md)',
        '- [完整统计与调用成本](results-summary.json)、[v3.3 诊断](policy-v33/diagnostic-v33.json)',
        '- [保留的 v3.2 表格](review-adjudicated/catalogue-clarified.xlsx)、[原始评分](diagnostic.json)、[环境归因后评分](diagnostic-reviewed.json)', '',
        '## 覆盖与难度', '',
        '| 任务族 | 轮次 | 通过 | 作答失败 | 环境阻塞 | 全题通过 |',
        '| --- | ---: | ---: | ---: | ---: | ---: |',
    ]
    for name, label in [('STD', '标准工作流'), ('INT', '交互修订'), ('MM', '多模态重建')]:
        g = results['groups']['family'][name]
        cases = [c for c in final['caseRows'] if c['family'] == name]
        o = g['outcomes']
        lines.append(f"| {label} | {g['turns']} | {o.get('passed',0)} | {o.get('candidate_failure',0)} | {o.get('blocked_configuration',0)} | {sum(c['allPassed'] for c in cases)}/{len(cases)} |")
    lines += ['', '| 设计难度 | 通过／轮次 | 环境阻塞 | 平均原生请求／轮 |', '| --- | ---: | ---: | ---: |']
    for level, g in results['groups']['level'].items():
        lines.append(f"| {level} | {g['outcomes'].get('passed',0)}/{g['turns']} | {g['outcomes'].get('blocked_configuration',0)} | {g['meanNativeRequests']:.2f} |")
    lines += ['',
        '难度标签尚不能当作模型实测难度排序：L3 通过率为 71.3%，L4 为 92.2%；L4 平均调用约 51 次原生分析，明显高于 L3 的 3.25 次。有限截面目录可以用多次求解搜索。本轮没有隔离工具能力和预算，不能据此断言工具减少后也能保持相同成绩。', '',
        '## 找到并修正了什么', '',
        '六轮误拒发生在 INT-016、019、020、023、027、029 的 t2。修改 Q 后，候选提交了完整正确的新模型并重新计算 SERVICE，同时复用未变的 D。旧评分器因旧 D 作业仍保存旧 Q 而拒绝。新政策要求至少一份完整当前模型的受保护执行证据，并逐个检查缓存计算的有效物理问题及已完成的线弹性执行设置；仍检查几何、刚度、支承、荷载和原数值容差。', '',
        '全部 560 轮先重放 v3.2，再按 [v3.3 明确政策](../../../../scripts/research300_v3/POLICY-V33.md)重评；原 464 轮通过均保留。新增通过轮次接受 48 项实际交付正反例，另有 10 项边界测试。没有按题号手工改分，也没有改原答案。', '',
        '| 原始未通过的原因 | 轮次 | 处理与证据 |', '| --- | ---: | --- |',
        '| 缓存工况误拒 | 6 | 单独版本修正，保留旧评分 |',
        '| 商业引擎 SSH 环境故障 | 5 | 依据原生故障回执及依赖关系归因，保留固定分母 |',
        '| 节点荷载错误 | 69 | 独立积分，与全部被报告执行的节点荷载比较 |',
        '| 综合题荷载分布错误 | 14 | 从公开面压、受荷宽度及修订重建密度；同合力不等于同分布 |',
        '| 报告符号错误 | 2 | 原生杆端抵抗弯矩与请求截面弯矩的符号混用 |', '',
        'INT-006 的位移正确、原生输出真实，但每轮两项弯矩报告符号相反。“软件直出”仍需绑定物理量、位置、局部方向、截面侧及符号约定；单个正确数字不能证明整份交付可靠。原预选展示脚本因整题未通过而停止，日志保留；新的逐字段示例如实展示失败。', '',
        'MM-004 首次遇到 YJK 自动分段与映射不兼容，候选增加两个度为 2 的节点、细分相应杆件后真实执行成功，最终通过。它提供了一个有效串联细分被接受的实际案例，不代表任意工程理想化均被认证等价。', '',
        '## 校验、复现与成本', '',
        f"- 原通过交付上的 {controls['controlsPassed']}/{controls['controls']} 项正反例与篡改控制通过；v3.3 新增 48/48 项通过。控制覆盖错误报告、错误物理输入、未知／跨题／未来作业、过期证据、查询轮隐藏执行，以及请求、模型、状态、回执和答案篡改。",
        f"- {native['cases']} 题、{native['issuedTurns']} 轮原生证据检查完成，{native['isolationChecks']} 项输入隔离检查通过。{native['nativeAttempts']} 次原生请求中，{native['nativeSuccessful']} 次取得成功回执，全部成功原生证明通过核验；其余 5 次原始失败记录保留。",
        '- 本地源码和远端 129 份源码在运行后均与冻结版本一致。原始评分、环境归因、连续误差、v3.3 修订及边界复核均从独立解包目录重放，JSON 逐字节一致。重放使用同一主机和运行时，不是跨平台复现或重新调用模型／求解器。',
        f"- v3.3 有 {measured['turnsWithObservations']} 轮可进行连续误差观测，{measured['turnsWithUnavailableItems']} 轮标为不可比较；{measured['observations']} 条观测中 {measured['observations']-measured['withinTolerance']} 条超限，均对应两轮报告中的四个弯矩符号错误。不可比较项没有填零；这些观测不是独立统计样本，也不替代全部动力或决策检查。",
        '- 561 次 Codex CLI 启动／续接、9,400 次 CLI 工具调用、10,161 次原生请求分别计数；CLI 启动数不是模型 API 请求数。每轮预算为 1,800 秒、128 次原生请求、200 次观测工具调用。一次模型容量故障按原规则同线程续接，总预算未重置。没有从未经确认的 usage 事件推算费用。',
        '- SSH 恢复后另用新会话补跑两个案例的六轮，6/6 通过且冷重放一致。这是单列的环境恢复试验，不替换原全量成绩；临时 SSH 别名已清理。', '',
        '[原始冷重放](replay/cold-replay.json) · [环境及连续误差重放](review-cold-replay.json) · [v3.3 完整重放](policy-v33/completion-summary.json) · [原生检查](native-inspection-summary.json) · [恢复试验](transport-recovery/candidate-rerun/recovery-complete.json) · [运行问题记录](run-validity-notes.md)', '',
        '## 能回答和仍不能回答的质疑', '',
        '本轮提供了真实 Codex 全覆盖运行、受保护原生证据、明确的等价边界、真实误拒修正、连续误差、完整分母及离线重放。它增加了对已覆盖检查的信心，不能保证评估器永远没有缺陷，也不能保证任意自由文本无幻觉。', '',
        '独立工程师盲审、旧语义裁判校准、同条件组件消融、外部领域 agent 对比、预先固定的多次重复，以及按来源／拓扑隔离的新留出集仍未完成。不能声称全部审稿意见已解决；当前不能用这次开发回归证明某个系统组件的独有贡献。', '',
        '所有改动和产物仅在本地，未 commit、未 push。[完成记录](completion.json)和[产物完整性索引](artifact-integrity.json)记录最终状态。', '',
    ]
    with (report / 'README.md').open('x') as f:
        f.write('\n'.join(lines))
    completion = {'kind': 'codex-full-review-completed', 'completedAt': time.time(), 'cases': 300, 'turns': 560,
                  'formalComparisonScore': False, 'postHocPolicyRevision': True, 'v32Counts': results['v32Counts'],
                  'v33Counts': counts, 'caseCounts': final['caseCounts'], 'allOriginalNonpassesReviewed': 96,
                  'unresolvedAttributions': 0, 'allRequiredColdReplaysIdentical': True,
                  'originalPositiveControlsPassed': controls['controlsPassed'], 'addedReuseControlsPassed': 48,
                  'originalCapturesModified': False, 'externalEngineerReview': False, 'gitDiffCheckPassed': True,
                  'benchmarkHead': git_head, 'gitCommitPerformed': False, 'gitPushPerformed': False,
                  'sourceBindingsVerified': True, 'temporarySSHAgentAliasRemoved': True,
                  'knownHistoricalOperationalFailure': 'Original worked-trace helper required INT006 to pass and correctly stopped. Replaced with signed-failure trace and independently replayed edge-case proof; original failed stage retained.',
                  'finalSources': final_sources, 'finalSourceArchiveSha256': sha(archive),
                  'evidence': {n: sha(report / n) for n in ['failure-review.json', 'results-summary.json',
                              'postprocess-summary.json', 'review-cold-replay.json', 'policy-v33/completion-summary.json']}}
    write(report / 'completion.json', completion)
    integrity = []
    for p in sorted(report.rglob('*')):
        if not p.is_file():
            continue
        assert not p.is_symlink(), 'Report symlink must not enter final inventory'
        before = p.stat()
        digest = sha(p)
        after = p.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'Report file changed during final sealing'
        integrity.append({'path': p.relative_to(report).as_posix(), 'bytes': after.st_size, 'sha256': digest})
    write(report / 'artifact-integrity.json', {'kind': 'codex-full-report-integrity-index', 'files': integrity,
          'fileCount': len(integrity), 'totalBytes': sum(r['bytes'] for r in integrity),
          'excludes': ['artifact-integrity.json', 'artifact-integrity.sha256'],
          'originalCapturePinSha256': raw_replay['operatorPinSha256'], 'finalizerSourceSha256': own_source})
    digest = sha(report / 'artifact-integrity.json')
    with (report / 'artifact-integrity.sha256').open('x') as f:
        f.write(digest + '  artifact-integrity.json\n')
    print(json.dumps({'completed': True, 'counts': counts, 'reportFiles': len(integrity), 'integrityIndexSha256': digest}), flush=True)


if __name__ == '__main__':
    main()
