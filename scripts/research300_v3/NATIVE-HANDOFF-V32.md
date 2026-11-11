# 原生环境交付与证据封存

本轮仅准备源码、静态输入和本地交付文件。没有上传、部署、编译 Windows 启动器、试答题目、运行求解器或测试，也没有产生新的执行证明或验收回执。

## 执行机器和版本

PKPM/YJK 的原生分析应在装有对应软件、SDK、匹配 Python 和有效许可的 Windows 机器执行。目标仍可使用此前的 `<native-host>`，当前安装、许可和实际配置须在后续验收时重新确认。本地控制端负责题目、签发轮次、预算、原始证据和评分；候选只得到公开资料与自己的真实工具结果。

最直接的部署是把对应版本的 Sclaw 后端和分析 worker 放在原生机器，前端与评估控制端连接它。当前 Linux 后端的 builtin-PKPM 不会因为填写一个 IP 就自动变成远程原生入口；分布式运行需要实际接通 worker 传输并验收。原有 Codex 商业 broker 的远程路径不能冒充 Sclaw 自身的调用链。

本地兼容修订为 `work/native-audit-input-20261029@4f63d909`，基于本地 `0a17bfdc`，包含此前7个未上传提交和新的通用截面来源投影修复。远端 `work/research-next@00ecd812`、历史 Codex 的 `db3c0b1d` 和论文冻结版本保持原样。该修订不是已验收的新基线；后续应先验收，再冻结实际版本与环境。

新修订仅将结构符合约定的来源/引用/规则/派生标签完整保存到 `modelProjection.inputEvidence`，从商业弹性求解投影中分离；原模型、物理属性、未知 extra 和已有原生物理检查保留。来源声明仍由通用建模边界核验，投影不会把它们认证为真实证据。

## 本地交付包

`prepare_native_bundle_v32.py` 从明确的 Git 提交读取源文件，生成源码 ZIP、源文件 SHA 清单、相对发布版补丁和包含8个本地提交的 Git bundle。只准备本地文件，不连接目标机器，不包含 SDK、许可、用户设置、私有参考或答案。

```sh
python3 scripts/research300_v3/prepare_native_bundle_v32.py \
  --sut /path/to/local-native-audit-worktree \
  --commit 4f63d909813f279bf310fa69154a07f9bbccd464 \
  --output /path/to/new-local-handoff
```

Git bundle 以远端 `00ecd812` 为前提，供后续接收端取得确切的新提交。源码包是原生子系统与采集器文件，不是包含依赖的完整 Sclaw 安装包。没有自动覆盖安装或启动服务的操作。

原生源码 ZIP 按原字节交付，接收端应在新目录解压并核对清单 SHA，再配置 worker 路径；换行或其他文件内容不符时不自动放行。

## 原始 worker 采集

`capture_structureclaw_worker_v32.py` 是旧采集器的独立版本，增加独立 `captureId`、PID、起止时间与采集器源码 SHA，不改原始请求或响应。原 worker 的退出码、stdout、stderr 及 OpenSees 的 Python 原始规范化哈希字节均保留。非分析 worker 原样转发。

Windows 使用同包的 `CaptureWorkerLauncher.cs` 源码。以下命令仅供之后在新目录编译，不会启动求解器，本轮未执行：

```powershell
powershell -NoProfile -File .\collector\Build-CaptureLauncher.ps1 -OutputDirectory D:\bench-native\capture-v32-new
```

编译后的 `capture-worker.exe` 和同目录 Python 采集脚本配合使用。后续通过原有设置管理入口，把 `analysis.pythonBin` 指向启动器；`SCLAW_BENCH_PYTHON` 指向原先实际使用的 Python，`SCLAW_BENCH_CAPTURE_ROOT` 指向专用采集目录。SDK、DLL 路径和许可继续沿用实际原生配置。启动器逐字转发 stdin/stdout/stderr，并返回实际子进程退出码。Windows 的依赖、超时及进程树回收仍需验收，本轮没有编译或运行该启动器。

候选执行代码时，工作区与控制目录必须真正隔离。仅设置 cwd 不能证明隔离；默认 shell 关闭与允许编程的配置要分别记录。新的静态前提要求运行配置回执包含 `candidateIsolationVerified/controlFilesInaccessible:true`，启用 Sclaw shell 时还需要 `shellIsolationVerified:true`。隔离未确认时不取得正式评分资格。

## 原始采集清单

控制端记录会话、已签发题号/轮次、候选状态、原始结构化交付和每个分析调用。不得由候选编写此清单，不使用“最新运行”猜测关联。尚缺少轮次时，封存器保留该轮未完成状态。声明已完整采集却没有失败日志时拒绝封存。

清单必须先在候选之外固定 SHA。必要结构如下，省略号是格式说明，不是可用数据：

```json
{
  "schemaVersion": 1,
  "kind": "research300-v3-collected-session",
  "editionManifestSha256": "<冻结 manifest SHA>",
  "sutCommit": "<实际提交>",
  "inputProtocol": "verbatim-public-v3.2",
  "executionSpecificationSha256": "<运行配置 SHA>",
  "sourceManifest": {"path": "source-manifest.json", "sha256": "<源清单 SHA>"},
  "turns": [
    {
      "caseId": "<已签发题号>", "turnId": "t1",
      "captureComplete": true, "environmentStatus": "ready", "candidateStatus": "completed",
      "answer": {"path": "<原交付文件>", "sha256": "<原字节 SHA>"},
      "attempts": [
        {
          "attemptId": "<控制端调用身份>", "status": "succeeded", "engine": "PKPM",
          "archive": {"path": "<原 run.json.gz>", "sha256": "<原归档 SHA>"},
          "captures": [{"path": "<原 capture.json>", "sha256": "<采集记录 SHA>"}],
          "nativeArtifacts": [{"path": "<原生文件>", "sha256": "<与真实返回关联的 SHA>"}],
          "rawArtifacts": []
        }
      ]
    }
  ]
}
```

失败调用的 `status` 为 `failed/blocked/incomplete`，保留原 capture、原生文件和错误日志；发生在 worker 之前的失败可只有 `rawArtifacts`。`captures` 允许一个 Sclaw run 中的多个原生 worker，保留真实调用次数。候选答案缺失或无效 JSON 仍按原字节记录，封存器不替候选补答案。

## 离线封存

`publish_capture_v32.cjs` 不调用模型或求解器，不读取私有参考。它核对原请求与运行归档、模型、指定引擎、结果选择，以及真实 worker 的源文件 SHA/退出码。OpenSees 逐项核对原生规范化输入、设置、响应哈希及已使用数据；商业引擎逐项绑定原 worker 的带符号响应、截面站点、原生上下文和真实原生产物。解析不明确或绑定冲突时拒绝发布，不补值或猜测结果。

它复制原字节，生成评分侧所需的状态、证据索引和原始产物描述符，仅作身份与结构适配。失败及未引用调用仍列入本轮尝试，原生 worker 次数另列。重复 capture 身份、重复 runId、错输入、错结果选择或被改写数据不能封存。输出目录必须全新；中途失败保留现场，不覆盖重试。

```sh
node scripts/research300_v3/publish_capture_v32.cjs \
  --source-root /path/to/protected-originals \
  --inventory collection.json --inventory-sha256 OPERATOR_PIN \
  --edition /path/to/frozen-edition --output /path/to/new-controlled-index
```

此命令本轮未执行。程序不会生成策略验收、隔离验收或环境可用性证书。实际采集与会话登记、原生运行、隔离与进程回收、新评分正反例验收仍须完成，才能把附条件状态改成正式就绪。后续评分继续使用 [v3.2 协议](POLICY-V32.md) 中的外部索引 SHA、静态前提 SHA 和固定560轮分母。
