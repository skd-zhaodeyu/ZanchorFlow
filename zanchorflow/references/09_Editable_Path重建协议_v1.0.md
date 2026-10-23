# 09 · Editable Path 可编辑 PPT 重建协议 v1.0

## 1. 范围、选择与不变量

第三条重建路径的公开名称为 **Editable Path**，内部值 `editable_path`。适用于新建 full Codex 任务；Qwen、WorkBuddy 的 Image-only 安装视图继续仅支持 Image Layer。用户必须明确选择，不能因服务不可用或模型偏好自动切换。选择时使用路由器当前提示，简述三条路径的原理、编辑单位与费用条件，不推荐或预选路线。无需额外购买分层服务；必要的图像编辑使用当前宿主的生图能力，受现有套餐额度及计费规则约束。

新任务在完整 Stage 2 正式页面组已展示、用户视觉批准和 Final Content Truth 对账完成之后、第一次消字之前选择路径。Magic Layer、Image Layer 继续按原协议 05—08 消字与恢复。Editable Path 直接使用已批准的含字原图与 Truth，不制造 Text-Clean 文件，不把普通原图登记为消字成果。旧任务、旧选择、旧签章和旧消字顺序保持原语义，不自动迁移。

保留 01—04 的语义、Anchor、二维非照片化和视觉审批约束。保留原四项 Hard Gates 的名称与要求：`content_truth`、`semantic_fidelity`、`functional_editability`、`visual_fidelity`。本路径不要求全元素矢量化；图片资产可独立移动缩放，原生文字、表格和结构对象承担实质编辑价值。

## 2. 原图分析与文字测量

先观察当前批准原图，盘点文字的逐次出现、表格、结构形状/线条、图标、纹理背景、图形化文字和公式。重复词、相同数值各有独立 occurrence ID，不按字符串去重。Truth 是最终内容依据；OCR 只辅助定位与字号，不得覆盖 Truth。错字、缺字或分辨率不足需核对，不用问号或占位符代替关键内容。

`editable_text_hints.py` 基于本地分块、XY-cut 与墨迹测量，输出候选框、字号与字号组；同层级字号须结合物理页面尺寸、字体和原图核对。检测漏行或把线条当字不是内容增删依据。测量前在页面工作目录 `page_request.json` 写实际 `slide.width/height`（英寸）；默认 13.333 × 7.5 只适用于该画布。最终构建计划中的坐标统一为原图像素，页面物理大小为 EMU。分支选择时从当前注册画布确定全套物理页面；未显式注册目标时沿用短边 7.5 英寸的既有推导。每页计划必须匹配该选择，不能各自猜测物理尺寸。

可选 `editable_ocr.py` 使用 PaddleOCR；仅在用户允许该来源图片上传且配置 `PADDLE_OCR_TOKEN` 时运行。凭据只从环境读取，不写入项目、命令行参数、日志或报告。无 Token、网络失败或用户拒绝上传时继续本地测量与人工/模型读图，不强制注册、不降低内容核对要求。OCR 返回文本仍需和 Truth 逐项核对。

## 3. 按编辑价值选择表示

- 普通可读文字恢复为原生文本框或原生表格单元格，支持中英文、混排、段落、局部字体/字号/颜色/粗斜体/下划线、上下标和字距。每次文本出现与一个 Truth occurrence 精确对应。多段文字可属于一次 occurrence，但不能把多次出现合并去重。
- 普通行列表格使用 PowerPoint 原生表格：行列比例、矩形合并、文字与基础填充/边框样式。被合并覆盖的格不得藏文字或 occurrence。复杂视觉表格可采用混合对象，但需说明编辑范围；不能以整页截图冒充原生表格。
- 结构矩形、圆角矩形、椭圆与可编辑路径用原生对象。路径用连续 `moveTo/lnTo/quadBezTo/cubicBezTo/close`，保留虚线和端点箭头，不把曲线拆成大量小线段。可以编辑顶点与线条样式；不宣称它是数据驱动图表或会自动重连的连接器。
- 图标、纹理、复杂视觉对象允许作为带来源的独立图片；已有有效源素材优先复用，不要求重生成。已确认均匀背景、纯色前景且可用重新合成误差核验时，可局部恢复透明度；不能把这一方法无条件用于照片、复杂叠层或未知颜色。背景需符合原图，不默认换成纯色。含字全页原图不能放在原生文字下方造成重影，也不能用遮盖层假装已恢复全部对象。
- 图形化文字可保留为图，但必须记录 `representation_role=graphic_typography`、`semantic_text`、Truth occurrence 与 `preservation_evidence`，其中 `content_verified/source_verified/substitution_material_loss` 均为真，图形化文字还须保留既有 `design_approved/composition_critical/native_text_substitution_material_loss` 证据要求；实际视觉审查需支持这些判断。标题主元素仍须满足既有 Title Contract 的原生文字身份约束。

## 4. 公式与特殊字形

构建计划为每个公式写 `formula_inventory`，列 `object_id` 与决策：`native_text`、`latex_rendered` 或 `source_preserved`。简单 Unicode 公式可原生文字；复杂公式可从 LaTeX 渲染为图像，保留 `.tex` 与内容哈希；源图保留方案需内容与来源证据。公式图片不是可直接修改表达式的 Office 公式对象，不作此承诺。

`editable_formula.py` 支持 xelatex/lualatex/pdflatex 或显式指定便携 Tectonic，转换通过 PyMuPDF，输出可为 SVG/PNG/PDF。PowerPoint 图片对象使用 PNG，同时保留 SVG/PDF 与 TeX 作为可再生成来源。临时文件和 Tectonic 资源缓存放在输出目录内，不安装全局工具。渲染失败时保留源并修复、核验源图保留或报告阻塞；关键公式不允许仅写警告后遗漏。未知高影响字形不能以 OCR 猜测替代。

## 5. 素材、实际返回值与有限修正

图像工具由宿主 Agent 调用，不编造上传平台、URL、Python 连接器或下载路径。使用实际返回的本地文件，校验真实尺寸与 SHA-256。优先请求透明背景；保留已有 alpha。需要色键方案时，选与前景不同的颜色，再用 `editable_chroma.py` 去背，检查浅色边缘与颜色损伤。

### 5.1 跨页稀疏素材板

先登记确实需要图像编辑分离的前景对象；原生结构、公式渲染与已有合格素材不进入队列。按当前页面顺序从最早待处理对象组板，同页连续处理；仍有容量时继续登记后续已批准页面，每板最多 3 个来源页面，首次板与修正板相同。不跨项目、运行或等待未批准页面凑板。对象数量少不等于有余量；按细节、有效分辨率、完整边界、必要留白及透明底/色键兼容性判断。默认布局不将对象区域缩小到低于原页裁片有效像素尺寸；单个对象过大时换宿主支持的尺寸或报告限制，不强行缩小。达到 3 页、容量不足、条件冲突或队列结束即封板，可留下空白；提前分板需说明原因。脚本验证布局与页数，不声称自动判断语义或求最优排布。

可本地裁切、简单拼接参考区域，保留原页—对象—参考区域映射；必要时附完整原页。标签放在对象外，不要求生成图画编号。提示词要求保真分离而非重绘，保持形状、比例、笔画、颜色、纹理及分离小细节，对象完整、互不接触且留足空白。返回后按实际内容确认身份，不能仅按位置或顺序认领，也不能把参考裁片冒充提取结果。

### 5.2 身份、调用与接口

沿用 register-job 的原图哈希、角色、冻结原页区域形成 job_key；改名、提示词、拼板位置、分组或重叠源区域不能重置额度。原页区域用于来源身份，返回板区域用于拆图。重复源对象可共享结果，但需分别登记页面引用并核对各页适用性；同一任务一板只扣一次。最多 3 页按实际来源页面数计算。

先逐页 register-job，再 register-sheet、reserve-sheet、实际工具调用、record-sheet-result、拆图及 review-sheet。每次板调用只有一个 token，但每个成员各记一次尝试；每个任务最多首次加一次定向修正。失败、未知完成均计次，不自动重发；任一成员待确认、额度耗尽或阶段不符，整板预留拒绝而不部分扣次。板 token 必须整体记录，不能借旧单对象接口改写。实际调用数按 token 去重，与对象尝试次数分开报告。正常板登记及资产验收保留既有路由审批校验；已发生调用因来源或审批变化无法正常入账时，使用下述受限 reconcile-result，只记录事实，不重发、不退款、不直接构建。

新增四个 CLI 操作：register-sheet、reserve-sheet、record-sheet-result、review-sheet。多对象输入使用 --spec JSON。register-sheet 输入包含 stage（initial/correction）、size_px:[w,h]、padding_px（默认16，至少1）、background（透明或具体色键说明）、seal_reason（queue_end/page_limit/capacity/incompatible），后两者需 finding。reference_paths 为参考文件路径；members 每项含 job_key、sources:[{slide_id,object_ref}]、计划板区域 box:[x,y,w,h]；修正成员另附逐对象 finding。同一 job_key 只列一项，多页复用写多个 sources。注册返回稳定 sheet_key，reserve-sheet --sheet-key 返回 token。record-sheet-result --sheet-key --token 使用 --returned-path 或 --failure，未知状态另带 --unknown。板定义冻结；修改分组注册新板但沿用成员次数。背景修复仍走旧单对象任务，不混进前景板。

来源参考存为内容哈希快照。每个成员绑定所属页和来源指纹，不能把整板当成来自某一页。某页当前来源变化只阻止旧资产进入该页新计划，不使其他页合格结果自动失效；原始板、快照或共同证据篡改则拒绝依赖它的结果。旧单对象命令与记录继续兼容；旧整片区域任务不自动拆分，不迁移释放额度。来源校验通过现有 validate_assets 接入。

### 5.3 部分失败与逐对象验收

原 editable_split.py --regions 严格模式保持。素材板使用显式 --batch --regions JSON --manifest report；JSON 为 objects:[{job_key,name,box:[x,y,w,h]}]，缺失对象用 box:null，不伪造空区域。区域包含完整对象、分离小点、笔画和浅色细节，互不重叠且前景不触边。局部空区域或触边记为对象失败，可保留其他可安全拆分结果；归属重叠直接拒绝，未归属前景使整板不能自动接受。保留既有浅色残余的窄例外，不放宽到忽略笔画。输出目录和报告必须新建，不覆盖历史结果。

逐对象查看透明底与实色背景，核验身份、形状、细节、边缘及背景残留。拆分报告绑定输入、区域文件和裁片哈希。review-sheet 输入包含 token、split_report、items:[{job_key,verdict:accepted/failed,finding,evidence_paths}]；接受项另需 checks:{identity:true,shape:true,detail:true,edges:true,background:true}。去背等导致处理输入与原返回哈希不同时补 processing_finding。这是人工/模型审查证据，不是自动视觉判分。记录追加且不可覆盖；合格资产保留原文件与验收哈希，不允许后续 review 替换。失败对象可先修复本地裁切/去背，用新报告重新验收，不增加生图次数。

确实需重生的失败对象，依据实际缺陷和剩余额度，按来源页顺序重组修正板；可来自不同首板，仍最多3页。不混入首次对象或合格对象，不为凑板等待更多失败。以原图为保真依据，失败图只作缺陷说明；修正仍失败则保留证据并阻塞，不能第三次调用或降级交付。生成图片 provenance 增加 sheet_key/review_sha256，保留 job_key/returned_sha256/processing_finding；计划固定所选资产及证据哈希。换资产需重新登记计划、构建与验收。页面独立对账、封存、合并。

### 5.4 回执恢复与幂等

正常 record-sheet-result 保留审批检查，旧单对象 record-result 不新增当前审批限制。所有新返回保存为项目内不可变快照，绑定实际尺寸及哈希。按原任务/板标识与 token 查找调用；相同结果类型和内容指纹返回 ALREADY_RECORDED（相同字节不同路径亦可），不同结果返回 RECEIPT_CONFLICT，不覆盖原记录。请求文件丢失时不能凭 token 假定重放相同；使用 query-result 只读查看已存事实和证据可用性。

补录命令：`editable_assets.py reconcile-result --state <state> --sheet-key <sheet> --token <token> --returned-path <actual>`；单对象改用 --job-key。失败用 --failure，未知完成另用 --unknown。只读查询为 query-result 加相同身份参数。补录不要求当前页面仍批准，但必须验证原任务、预留 token、冻结定义及全体成员对应关系。账本/冻结身份不可信时拒绝；源快照损坏、审批失效或运行变化则隔离记录，不能授予使用权限。成员与板一次事务入账。新快照存在不代表已入账，提交失败可重放但不得直接构建。

补录追加 receipt_events，保留原 reserved/unknown/failed 历史，尝试次数按原 calls 计，补录不增减额度。共享解析供登记、查询、预留、验收及来源校验使用，不能自行把最后一条原状态视为全部事实。reserved/unknown 的实际迟到返回且无更新尝试，可在当前运行、来源、审批、证据和 Truth 核验恢复后进入原验收；补录本身不构成验收。已有修正、跨运行、或明确失败后的矛盾返回只归档，不替换结果、不取消修正、不自动迁移。历史 token 的材料不能绑定较新调用。同板合格对象独立保留，另一对象修正不使其自动失效。

板修正预留必须先处理已补录返回，并沿用逐对象失败证据要求；旧单对象沿用明确修正缺陷说明，不因原 unknown 状态自动再调用。来源改变或证据未恢复时继续隔离，不能删除原篡改检查。查询和记录返回 eligible/use_disposition、reasons 仅说明当前结构/恢复资格；最终资产仍必须经当前审批、逐对象验收和页面 Hard Gates。

## 6. 冻结计划与本地构建

按当前步骤安装所需依赖可用 `python -m pip install -r requirements-editable.txt`；OCR 凭据和外部 TeX 引擎仍按需配置，不自动注册服务或全局安装。

计划 `schema_version: 1`，含 `source_size_px`、`slide_size_emu`、按 `z_index` 排列的 `objects`。圆角矩形可用 `source_corner_radius_px` 明确记录原图圆角；不要把微圆角、显著圆角和胶囊统一成默认形状。对象有唯一 `id/type/box_px`，类型为 `text/table/shape/path/image`。文字和单元格用 `text/occurrence_ids`；混排可用 `paragraphs[].runs[]`，拼接内容必须与 `text` 相同。单元格支持 `row_span/col_span/style`。路径属性遵循内置几何模块。图片用实际绝对 `file/sha256`，`fit` 为 `contain`（默认）、`cover` 或明确的 `stretch`。

图片 `provenance.kind` 为 `source_preserved`（`source_sha256/finding`）或 `generated`（`job_key/returned_sha256`，派生图再附 `processing_finding`）；LaTeX 渲染图由公式清单中的实际 `.tex` 哈希绑定。保留图形文字或公式有 `semantic_text/occurrence_ids/representation_role/preservation_evidence`。带统一标题的计划另含当前 `title_contract_ref/title_element_ids`；表格内标题元素名为 `table_id:row:column`。标题主元素不得改成图片。

`register-plan` 验证当前批准原图、Truth、画布、标题和资产，保存不可变计划。`build` 生成一页 PPTX 及 `.manifest.json`，清单记录完整最终计划、实际形状 ID、物理坐标、旋转、occurrence—对象/单元格映射与 PPTX 哈希。源、Truth、画布、计划、资产或公式源变化会使下游证据失效。修订保存历史；不用相同文件名覆盖已有构建。可从最终计划复建相同对象结构，不承诺 ZIP 字节完全相同。

## 7. 实际验收、签章与合并

本地打开 PowerPoint，渲染整页，再检查文字框溢出、换行、表格合并、路径样式、图片比例/边缘、层叠、背景、受保护字形和公式。选择有代表性的文字、表格单元格、形状、曲线、图片做实际编辑、保存和重开，确认对象能力；修改副本不得替代已绑定的交付构建。

真实视觉审查对照当前批准原图和 Truth，记录具体缺陷与局部修复。不用 XML 解析成功、Pillow 预览、对象数、手工填 PASS 或字符串测试冒充实际 Office/模型视觉验证。`editable_office.py` 的尺寸/溢出和编辑诊断也不能自动授予视觉 PASS。文本测量只是建议；必要时修正计划中的字体、字号、框或间距，再重新构建与渲染，不能无依据统一缩小全页字号。

页面 review JSON 必须绑定实际 `pptx_sha256`、当前 `lineage`、四项 `checks`，每项 `evidence` 包含非空 `finding` 与真实 `file/sha256`。`seal-page` 只在全部 PASS 且来源、构建、最终清单、审查与证据文件仍相符时签章；更改任一证据即失效。脚本只强制证据契约，判断真实性由实际审查负责。

通过 `assemble_deck.py` 复用现有页面顺序、原生合并、整套验收和精确字节交付；不得绕开整套 review。保留原 Hard Gates、审批与发布边界。

## 8. Runtime dispatch

```text
python scripts/canva_bridge.py start-run --state <state> --title-choice-required --early-reconstruction-selection
python scripts/reconstruction_router.py status --state <state>
python scripts/reconstruction_router.py choose-backend --state <state> --backend editable_path
python scripts/editable_text_hints.py <page-work> --source <approved-render.png>
# optional only: explicitly permitted upload and environment credential
python scripts/editable_ocr.py <page-work> --source <approved-render.png> --upload-approved
python scripts/editable_assets.py register-job --state <state> --slide-id S001 --region <x> <y> <w> <h> --role foreground
python scripts/editable_assets.py reserve --state <state> --job-key <key>
# Host performs one actual tool call, then records its actual returned file or failure.
python scripts/editable_assets.py record-result --state <state> --job-key <key> --token <token> --returned-path <actual-file>
python scripts/editable_formula.py --tex <formula-body.txt> --output <formula.png> --engine <engine-path>
python scripts/editable_bridge.py register-plan --state <state> --slide-id S001 --plan <plan.json>
python scripts/editable_bridge.py build --state <state> --slide-id S001 --output <new-page.pptx>
python scripts/editable_office.py --pptx <new-page.pptx> --work <new-audit-dir>
python scripts/editable_bridge.py seal-page --state <state> --slide-id S001 --review <review.json>
python scripts/assemble_deck.py prepare --state <state> --work-dir <new-merge-work>
```

执行前查询实际 CLI 参数。修正图像的第二次 reserve 需 `--finding`，第三次拒绝。若在旧任务发现已完成消字或分支工作，不启用新时间顺序，不清空旧状态；尊重现有任务，另行明确设计迁移才可转换。

## 9. 能力与来源声明

借鉴固定上游 `ningzimu/image-to-editable-ppt-skill` 提交 `b7be494e31a0ed56ef98716891db5474606b8cdf`，MIT 归属见根目录 `THIRD_PARTY_NOTICES.md`。保留测量驱动文字、原生表格和曲线路径、整对象素材区域、公式来源与局部修复的优点；不依赖私有 OAuth、强制上传平台或全元素矢量化。

新增严格来源/Truth/审批契约能改善可追溯性，但不能单凭契约声称重建质量超过上游。是否更优须由同输入、同字体/Office、同模型和可比图像额度的实际对照支持；离线契约测试与真实生成/视觉效果结论分别报告。
