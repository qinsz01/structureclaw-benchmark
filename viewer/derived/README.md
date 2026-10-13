# Derived member responses / 构件响应派生数据

`member-responses.json` contains display data computed offline by StructureClaw's shared postprocessor. It is not a benchmark answer file and never changes scoring tolerances, solver results, or frozen reference models.

`member-responses.json` 是由 StructureClaw 公共后处理模块离线生成的展示数据，不是新的评分标答；不改变评分容差、求解结果或冻结模型。

The default viewer build uses this checked-in data and requires no parent StructureClaw checkout. Export verifies each input SHA-256 before attaching responses to the display model. The browser only reads matched data; changed inputs require a fresh offline derivation.

默认 viewer 构建使用此仓库内的数据，不依赖父级 StructureClaw 目录。导出时逐项校验输入 SHA-256；浏览器只读取匹配的数据。模型或原始结果变化后必须重新离线生成。

To refresh from a StructureClaw checkout after compiling its backend:

在 StructureClaw 主仓库编译 backend 后，可显式刷新：

```sh
node backend/scripts/export-bench-member-responses.mjs /absolute/path/to/bench
```

The artifact records source-file hashes and the shared algorithm hash. `recovered` means endpoint force, displacement and rotation checks passed; `interpolated` is only endpoint kinematic interpolation. Neither sampled plot envelopes nor interpolation are advertised as exact interior extrema.

文件记录来源文件及算法哈希。`recovered` 表示端部内力、位移与转角检查通过；`interpolated` 仅表示端部运动插值。采样包络与插值均不宣称为真实内部极值。
