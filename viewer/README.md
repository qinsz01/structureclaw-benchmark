# StructureClaw Benchmark Explorer

独立、只读的 benchmark 案例展示站。展示全部 150 个案例的原始输入、附件、逐轮要求、参考结构和冻结数值标答；不读取实验结果、不调用模型或求解器，也不修改原有评分逻辑。

A standalone, read-only explorer for all 150 benchmark cases: original inputs, attachments, turn-specific expectations, reference structures, and frozen numerical answers. No experimental results, model calls, solver execution, or scoring changes.

## 本地运行 / Run locally

要求 Node.js 20.19+（或 22.12+）；在本目录执行：

Requires Node.js 20.19+ (or 22.12+). Run from this directory:

```powershell
npm ci
npm run dev
```

打开 / Open **http://127.0.0.1:4173/**。端口占用时不会悄悄切换；可使用 `npm run dev -- --port 4174` 指定其他端口。

The server uses a fixed port and binds to localhost. To select another port, use `npm run dev -- --port 4174`.

## 构建与部署 / Build and deploy

```powershell
npm run build
npm run preview
```

将 `dist/` 全部内容放到任意静态 HTTP 服务即可。支持子目录部署；案例使用 `#/case/<case-id>` 链接，不需要服务端路由回退。不支持直接用 `file://` 打开 HTML。无远程字体、数据库、API key 或 StructureClaw 后端依赖。

Serve the entire `dist/` directory over HTTP. Subdirectory deployments work with hash routes (`#/case/<case-id>`); no server-side route fallback is needed. Opening the HTML via `file://` is unsupported. No remote fonts, database, API key, or StructureClaw backend is required.

## 数据边界 / Data boundaries

- `scripts/export-data.mjs` 只读取上级仓库的 `benchmark.json`、`scenarios/` 和所需的 `fixtures/`，生成 `public/data/`。执行 `npm run data` 可重新导出；开发启动和构建会自动执行。
- 保留原始案例内容与附件字节。展示索引包含源文件 SHA-256；派生数据不提交到 Git，原始数据始终是权威来源。
- 150 个案例中，106 个案例至少有一轮引用结构标答，共涉及 53 个不同参考模型。其余案例展示已有行为要求，不编造模型或标准回答。多轮案例只展示当前轮的引用，不借用后续轮次标答。
- 数值标答依次按断言 `engineId`、案例 `analysisEngineTarget`、默认 OpenSees 选择。PKPM/YJK 使用冻结的对应引擎响应，不能用 OpenSees 数值替代。
- 数值单位读取参考结果元数据，显示值适当舍入，悬停查看原始精度。完整 JSON 保留全部原始数值。未提供单位显示 `—`，不猜测。
- 结构查看器展示几何、约束和选定荷载工况，不进行结构求解或数值插值。箭头长度用于示意方向，不代表不同荷载间的比例。点击约束节点可查看完整受约束自由度。
- 材料、截面、荷载等参数保持原始记录；单位应以案例工程说明与参考元数据为准，不能仅根据 `SI` 标签推断材料属性单位。
- 图片支持放大；DXF 提供 XY 二维预览、缩放、平移、图层开关及原文件下载。预览支持冻结附件中的 LINE、TEXT、ARC、CIRCLE，遇到未支持实体会显示提示，不自动对应或补建结构构件。没有变形云图或内力曲线功能。

- The exporter only reads `benchmark.json`, `scenarios/`, and required `fixtures/` from the parent repository. `npm run data` regenerates ignored `public/data/`; development and production builds do this automatically.
- Original case content and attachment bytes are preserved. Source SHA-256 hashes appear in the provenance panel. Generated data is not committed; the original corpus remains authoritative.
- 106 of the 150 cases reference a model in at least one turn, covering 53 distinct models. Other cases show existing behavioral expectations. No models or answer prose are invented, and later-turn references never leak into earlier turns.
- Numerical references select the assertion's `engineId`, then the case's `analysisEngineTarget`, then OpenSees by default. PKPM/YJK display their own frozen responses.
- Units come from result metadata. Displayed values are rounded; hover for full precision or inspect complete JSON. Missing units display `—`.
- Geometry, constraints, and the selected load case are visualized without analysis or interpolation. Arrow lengths are illustrative, not proportional magnitudes. Select a restrained node to inspect exact DOFs.
- Model properties retain source values; use the engineering specification and reference metadata to interpret units rather than assuming material units from the `SI` label.
- Images can be enlarged. DXF previews support XY projection, zoom/pan, layer toggles, and original downloads. LINE, TEXT, ARC, and CIRCLE cover the frozen attachments; unsupported entities are reported. No member correspondence or geometry is inferred. Deformation contours and internal-force diagrams remain out of scope.

## 界面 / Interface

中英文界面切换不会翻译原始题目。案例库支持全文搜索、类别/语言/结构筛选、分页和可分享筛选链接。详情页提供逐轮切换、正视/轴测视图、缩放/旋转/平移、节点与构件属性、荷载与编号开关、全屏、PNG 导出、参考数值和原始数据下载。窄屏下采用上下布局；WebGL 不可用时回退到静态结构图。

The Chinese/English UI preserves the original task language. The library supports full-text search, family/language/structure filters, pagination, and shareable filter links. Details include turn navigation, front/isometric views, zoom/orbit/pan, node/member inspection, load and label toggles, fullscreen, PNG export, reference tables, and original JSON downloads. Narrow screens use a stacked layout; browsers without WebGL receive a static geometry fallback.

## 验证 / Verification

### 查看与出图增强 / Viewing and figure tools

- 标答摘要直接提取节点/构件数量、约束节点、模型外包尺寸和荷载工况。主要数值仍显示指定引擎冻结响应中的分量、对象、单位与工况，不生成工程结论。
- “尺寸”显示模型 X/Y/Z 外包尺寸，以及可由现有楼层和节点标高核实的层高；不把所有节点间距当成真实跨度。
- 节点或构件被选中后高亮，属性卡片展示坐标、约束、材料、截面等原始值；原始 JSON 仍可展开。
- 切换编号、荷载、语言和出图选项保留视角。“分享当前查看状态”记录轮次、参考模型、荷载工况、编号/荷载/尺寸开关及相机位置；图纸图层和出图字号不写入分享链接。
- “出图模式”使用白底，提供字号、线宽调整与正视/轴测预设。可导出 1800×1500 的单结构排版图，或 2800×1500 的原图与参考结构组合图。组合图使用当前图纸视图与可见图层，三维部分按较高像素密度重新渲染；未建立输入实体和模型构件的自动对应。

- The summary derives model counts, restrained nodes, extents, and load cases from frozen data. Numerical highlights retain their source engine, component, entity, unit, and case; no engineering conclusions are generated.
- Dimensions label overall X/Y/Z extents and story heights verified against existing node elevations, not assumed spans between arbitrary nodes.
- Selected nodes/members are highlighted and inspected in property cards; original JSON remains available.
- Camera position survives display and language changes. Shared links preserve the turn, reference model, load case, labels/loads/dimensions, and camera; drawing layers and figure typography are not included.
- Figure mode offers a white background, font and line sizing, and front/isometric presets. Export a 1800×1500 structure figure or 2800×1500 input/reference comparison. The drawing uses its current viewport and visible layers, and the structure is re-rendered at higher pixel density. No automatic entity correspondence is implied.

```powershell
npm test
npm run build
npx playwright install chromium
npm run test:browser
```

数据测试逐个核对全部原始输入、轮次引用、模型、引擎标答、附件哈希及原文件不变性。浏览器测试遍历全部案例与轮次，并检查筛选、中英文、图片/DXF、数值符号、下载和移动布局。截图保存在忽略的 `test-results/`。

Data tests verify every input, turn reference, model, engine reference, attachment hash, and original-file immutability. Browser tests visit every case and turn and exercise filtering, both locales, image/DXF attachments, numerical signs, downloads, and mobile layout. Screenshots are written to ignored `test-results/`.

原始 benchmark 校验仍可从上级目录执行 `npm run validate`。

Run the original benchmark's `npm run validate` from the parent directory as an additional corpus check.
