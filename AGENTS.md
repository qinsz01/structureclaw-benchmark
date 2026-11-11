# 仓库约定

本仓库只放代码、题库和说明文档，保持可以直接公开。

- 不提交运行证据：原始会话、模型输出、原生求解输入输出、评分明细、压缩包和分卷一律不进 git。
- 运行产物写到 `.bench-work/`（已忽略）。需要长期保留的证据只放 NAS，不另行提交。
- `docs/implementation/reviews/` 已忽略，审查记录留在本地。提交前用 `git status` 和 `git diff --cached --stat` 确认没有证据或大文件。
- 原生求解主机只写在已忽略的 `native-host.local.json`（`{"sshTarget": "...", "sshJump": "..."}`）或环境变量 `SCLAW_NATIVE_SSH_TARGET`、`SCLAW_NATIVE_SSH_JUMP`、`SCLAW_NATIVE_HOST` 中，不写进代码和文档。
- `corpora/` 中的题库文件按字节绑定哈希，不直接修改；需要修订时建立新的版本目录。
- 2026-11-12 之前的完整开发历史和全部证据保存在 NAS 档案仓库 `02structureclaw-bench-archive` 中。
