# Codex v3.2 本地接入诊断

这是新协议的小批量开发诊断入口，不授予正式评测资格，也不替代 `grade_candidate_v32.cjs` 的资格检查。只接受明确选择的 OpenSees dev 题；原生后端固定为干净的 `db3c0b1da44fe668a6037a6c2e7f068d14354539`。不能将结果称为最新版 StructureClaw 的系统成绩。

## 执行边界

- 使用 `prepare_readiness_v32.packet` 逐轮投递原始公开文件，L4 首轮四份规则原文进入实际 prompt，原图以 `--image` 输入。后续轮次续接同一 thread，未来公开目录到签发时才生成。
- Codex 忽略用户配置、规则和 host skills；禁用多智能体、hooks、apps、plugins、网络。当前/历史公开资料只读，scratch 可写，控制记录、私有参考、评分器及原生 OpenSees 包不可访问。每轮真实 sandbox 探针必须先通过；负例文件与网络端点均有沙箱外正对照。
- 客户端增加必填 `--turn tN`，请求字节一次性采集，作业 ID 由控制端生成。失败、超预算、迟交和未在答案中引用的请求均登记。迟交仍归旧轮次并拒绝执行；原生请求预算在执行前检查。
- 工具调用数从 CLI 的 JSONL 事件计数，超过限制后终止进程；首次超额事件可能已经启动。这是**观测后终止**，不是与其他 runtime 等价的硬工具预算，不能据此宣称正式资源匹配。
- 固定全部预选轮次的分母。服务阻塞、采集未完成和候选失败分开记录。不对模型失败进行外部重试；CLI 自身的传输重试保留在原始事件流中。
- 原始作答、请求、规范化输入、worker 请求/输出、原生 canonical 字节、分析结果及全部调用事件由控制端封存。评分只使用原始交付，不修正数值、不返回评分反馈。

## 运行

从仓库根目录运行；以下目录名仅为示例，必须不存在。实际调用模型和原生求解器会产生资源费用。

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /home/openclaw/.structureclaw/.venv/bin/python \
  -m scripts.research300_v3.run_codex_v32 \
  --edition corpora/research300-v3-v1 \
  --work .bench-work/codex-v32-new-run \
  --base .bench-work/codex-v32-new-sessions \
  --sut .worktrees/structureclaw-pkpm-shear-fix-20261027 \
  --cases V3-INT-006,V3-MM-016,V3-STD-031,V3-STD-035,V3-INT-032,V3-STD-071,V3-MM-035
```

默认模型 `gpt-6.1-sol/high`，两个候选并行；每轮 1800 秒、128 次原生请求、200 次观测工具调用。无模型启动前先运行解析悬臂梁预检。任何源码更改均需要新运行目录；不能用修改后的源码冒充旧结果的原版执行环境。

完成后，运行目录旁生成独立的 `codex-v32-new-run-operator-pin.json`。先用 `sha256sum` 获取并保留其摘要，再以该摘要运行诊断评分；输出必须放在原始题库和 capture 目录之外：

```sh
node scripts/research300_v3/grade_codex_smoke_v32.cjs \
  --edition corpora/research300-v3-v1 \
  --control-root .bench-work/codex-v32-new-run \
  --pin .bench-work/codex-v32-new-run-operator-pin.json \
  --pin-sha256 REPLACE_WITH_OPERATOR_SHA256 \
  --output .bench-work/codex-v32-diagnostic.json
```

`audit_codex_smoke_v32.cjs` 使用相同参数，另选 `--output`，核对实际投递、续接、原生原件和身份，并在副本上做评分/伪造引用对照。通过的原始候选轮次才参与“从正确变为错误”的对照；候选错误不修正后再充当正例。两个入口始终输出 `formalComparisonScore:false`。

`npm run test:research300-v32-codex` 运行合成的采集、进程预算及评分入口测试，不调用模型或求解器。测试通过与真实试答成功是不同证据。

## 尚未覆盖

本入口没有验收商业引擎、最新版 Sclaw 原生采集、外部领域 agent、匹配消融、独立工程师审核或未见测试集泛化。它核对已声明结构化工程交付与受控原生证据；不证明所有自由文本无幻觉，也不证明人类审核效率提高。
