# Image Layer Model 可编辑 PPT 重建协议 v1.1

## 1. 目标、边界与名称

Image Layer 的目标不是通过重复远程调用追求理想分层，而是在调用前通过合理的 Layer Plan 提高一次调用的有效性，并在调用后区分普通模型局限与不可交付的严重错误。普通模型局限应记录并继续；只有确认属于严重模型输出错误时，才允许在相同输入与相同 Layer Plan 下考虑最多一次质量重拆。质量重拆不是自动恢复步骤，不得形成循环。

本协议只定义 Image Layer 分支，不替代 Magic Layer 分支，不修改 Reference 01–07 的内容架构、Anchor、视觉批准、文字真值、文字恢复、5 源像素画布规则或 Merge。进入前要求全部当前 Text-Clean 完成、用户已明确选择 image_layer；不得自动切换分支。正常沟通统一使用 ZAnchorFlow / Magic Layer 分支 / Image Layer 分支；版本仅用于 manifest、测试、诊断和历史记录。

## 2. Provider、输入与调用前就绪检查

当前 Provider 为 360 Reveal-Layer，model=reveal_layer、version=v2.3.4、pipeline_type=crop、seed=42、steps=10。API Key 仅从进程环境 ZANCHORFLOW_360_API_KEY 读取，不写入 state、manifest、日志或交付包。查询及下载恢复不等于新付费 submit。

Plan 使用 Text-Clean 源像素 [x1,y1,x2,y2]，绑定当前 page_id、输入 SHA、Plan SHA、source canvas。源最短边至少128、宽高比不超过5；1–6个目标，非空且不越界；按最长边1024缩放后每框短边至少8。保留原有预览及用户批准流程。

在既有 Plan 流程内记录 LAYER_PLAN_READINESS（READY / NOT_READY），绑定输入与 Plan 哈希；不新增用户确认关卡。八项检查必须有具体原因：editing_purpose、common_edit_grouping、exclusive_structure_ownership、protected_background、over_split、adaptive_margin、target_count、whole_asset_granularity。仅明确违规或明显框选错误为 NOT_READY；模型能力风险不构成拒绝调用理由。就绪失效只处理具体问题，不进行循环框选优化；实质修改已批准 Plan 仍需按原流程重新批准。

共同移动/删除/替换的元素合理合并，专属边框、阴影、装饰和内部连接归属一致，保护背景对象，避免明显过拆。margin 由 Agent 根据对象大小、边缘复杂度、阴影范围和邻接距离有限调整，不设固定16像素补丁、不设复杂优化器。照片、截图、纹理可作为单个完整 editable asset；整体移动、替换、删除属于有效编辑能力，不强求内部原子化。

## 3. 返回身份与数据职责

正式 raw layer set 使用 layers_aug。box-guided result 必须包含 resized_image、image_boxes、resized_image_boxes、boxes_mapping_index；len(layers_aug)=layers_base_count=len(image_boxes)+1，两个 mapping 数组数量等于 image_boxes 数量。索引唯一且有效，原始请求框和 target_id 对应，返回框格式/边界有效，所有已批准目标均存在，无重复或额外对象。

请求框、返回框、boxes_mapping_index **只用于对象身份及格式、边界、数量、缺失、重复检查**。Text-Clean 和 resized_image **只用于整页 geometry**。图层实际 alpha bbox **只用于前景裁剪范围和 placement**。returned bbox 不参与 layer shape placement，也不参与 crop extent 的扩大或修正。

拿错任务结果属于身份或技术错误；正确任务返回了明显不符输入的内容才可能是严重模型质量错误。

## 4. Bundle v3 与 geometry evidence

旧 Bundle v2 按原 legacy geometry 语义验证，不静默升级、不重新解释。新打包默认 v3；validator 按 schema_version 分派，未知版本拒绝。显式 --schema-version 2 仅供旧契约回归/兼容，不能用来绕过 v3 几何验证失败。

Bundle 保留输入哈希及尺寸、provider/model/task、层像素哈希、z-order、counts、missing_targets、目标物理画布、canonical bbox。v3 geometry.mapping_evidence 引用 geometry_evidence_file 和 geometry_evidence_sha256，及 bundle 内 source_image_file / resized_image_file。证据 JSON 包含 mapping_method_version、verification_parameters、verification_windows、window_scores、residuals、source_image_sha256、resized_image_sha256、声明候选、验证结果。验证图为独立资产，不计入 layers；路径必须安全、哈希和画布一致。新 bundle 哈希使旧绑定及 QA 失效；不覆盖原始返回文件。

只允许已声明 axis-aligned scale + translation：xb=sx*xs+tx，yb=sy*ys+ty。默认整页缩放；有明确内容矩形才使用既有 padding 映射。不接受未知 crop、rotation、shear、perspective 或 nonlinear warp。

固定流程：声明候选 → 本地验证 → VERIFIED / INSUFFICIENT / CONTRADICTED。不得根据匹配结果搜索或拟合新的 tx/ty/sx/sy。初始工程参数：最长边1024验证像素、最多8个结构窗口、32×32窗口、±16局部搜索、NCC≥0.8、非邻近次优差≥0.05、至少4有效窗口且覆盖至少3空间区域、有效对应残差≤1验证像素。局部搜索只测量候选附近对应；找到的位移不写回候选。空白、重复纹理、歧义对应不能单独证明映射。以上是可追溯工程初值，不宣传为普遍验证过的标准。

INSUFFICIENT 或 CONTRADICTED 均输出 LAYER_CANVAS_MAPPING_UNRESOLVED，停止该页本地几何处理并诊断，不重新调用模型、不改走旧 v2。Pillow + NumPy 是 Image Layer 新 geometry 条件依赖；运行 --scope image_layer preflight，缺失输出 IMAGE_LAYER_GEOMETRY_DEPENDENCY_MISSING；不得因此阻断 Magic Layer。

前景继续保留 alpha-tight crop、现有 alpha 阈值、半透明边缘、原层像素和 z-order。裁剪前 bbox 逆变换 xs=(xb-tx)/sx、ys=(yb-ty)/sy、ws=wb/sx、hs=hb/sy，再放置 [xs/Ws,ys/Hs,ws/Ws,hs/Hs]。背景对应完整源内容矩形并为 [0,0,1,1]。PPTX builder 不再次按 backend 尺寸或 asset 尺寸缩放。

## 5. Visual QA 三态

目标：评估当前分层结果能够提供的实际编辑能力，识别严重错误，并登记普通模型局限。

检查 layer_isolation / background_repair / recomposite_fidelity，每项 PASS / MODEL_LIMITATION / FAIL。全 PASS 为 LAYER_VISUAL_QA_PASS；至少一个 MODEL_LIMITATION 且无 FAIL 为 LAYER_VISUAL_QA_ACCEPTED_WITH_LIMITATIONS；任意 FAIL 为 LAYER_VISUAL_QA_FAILED。前两种允许 Graphics-first binding。旧 PASS 报告兼容。

普通毛刺、halo、轻微色差、阴影变化、网格变淡、局部残留、小对象提取较差、内部粘连、仍可交付的背景修补缺陷默认登记 MODEL_LIMITATION，继续，不重拆、不强制修补、不反复征询。每项记录 limitation_id、category、affected_target_ids、description、editing_impact、visual_impact、evidence（材料路径及SHA）。背景或整页问题使用空 target_ids 并附 affected_scope=background/page，不虚构 target；每项 MODEL_LIMITATION 通过 check_limitations 引用对应 id。

完成原始层浅深底、合成及移开检查后 register-visual-qa；登记材料哈希失效则相关下游重新检查，不重新拆层。

## 6. 限制继承与不可豁免项

Four Hard Gates 仍为 PASS / FAIL。Image Layer 单页及 Deck-Level Validation 携带 accepted_limitations，绑定当前 QA 和 bundle。Agent 依据 limitation_id、category、target、原证据判断是否相同，记录 limitation_matches 的匹配理由、unchanged_extent、claimed_capability_preserved；整套必须同时标注 page_id，避免跨页同名 id 混淆。

Functional Editability / Visual Fidelity 不得仅因相同且程度未扩大的已接受缺陷再次 FAIL。新问题、程度扩大或实际能力与登记描述不符需要重新分类，不一律 FAIL：普通问题更新局限记录，严重问题或不可豁免项阻断。更新记录使相关下游检查失效并重做，绝不因此重新拆层。

MODEL_LIMITATION 不豁免 Content Truth、文字真值、关键事实、严重语义错误、错误页面/来源/task/result identity/lineage、页面缺失/错误顺序、严重 geometry 或 PPTX 文件结构错误。不得将这些登记成普通局限，也不得借 limitation_matches 豁免真实 FAIL。

## 7. 两个独立重试入口

Technical Retry（authorize-retry）仅处理技术提交失败、未知提交、terminal failure；未知付费提交仍须沿既有风险授权规则。查询/下载恢复不是新的 submit，不消费质量重拆额度。已有 task_id 只查询/续传，不能盲目补提。

Severe Quality Retry（authorize-quality-retry）独立入口，须同时满足：Provider 正常完成、拿错结果/task identity/geometry/assembly 已排除、明确严重质量证据、当前用户付费授权覆盖额外调用、相同 input+Plan+provider/model 额度尚未消费。严重错误仅限：内容明显不符输入、大面积主体丢失、主要对象被替换或凭空增加、关键结构/方向/内容严重改变、空白或严重破碎至基本不可辨认。

重拆保持同一输入、Plan、provider/model 及全部模型参数；不自动改框。Plan 本身错误需要用户修改并形成新 lineage，不属于质量重拆；不得为获得额度自动改 Plan。authorize-quality-retry 本身不发远程请求。

在现有 call ledger 记录 retry_reason=technical_failure/severe_quality_failure，独立 quality_retry_count，输入SHA、PlanSHA、provider/model、模型参数、original_result_id、severe_quality_evidence_sha。质量额度在远程提交前事务式预留并消费，最多一次；未知提交不释放、不盲目补提。质量重拆的技术失败不得借 Technical Retry 再提交第三次；现有 task_id 可继续查询/下载。

result_1/result_2 分目录保存，第一次原始文件不覆盖或删除。第二次只判断严重错误是否消失，不计算美观综合分、不自动选优。第二次 PASS 或 MODEL_LIMITATION 则使用 result_2 继续；仍严重则 STOP，保留两份证据；状态未知沿技术恢复，不自动追加付费。第二次完成后质量重拆永久关闭，即使仍 FAIL。

## 8. 后续页面与整套交付

目标 PPT 物理尺寸来自当前 run 的可信 target canvas，或一次固定的一致源比例；backend 分辨率不能决定页面。完成 canonical normalization 后才执行现有5源像素每轴画布 Gate。Text Manifest 坐标及 font_size_normalized 不乘 backend scale。保持 Native Text Visual Fit、文字真值和原 Four Hard Gates、PAGE_SEALED、Merge、Deck-Level Validation。

Image Layer 独立 layer_bridge，不伪装 Canva download provenance。每页输入/Plan/结果/bundle/QA/Graphics-first/已复原PPTX 哈希可追溯，上游改变对应下游 stale。交付说明如实列出已接受模型局限及实际编辑能力，不把普通局限当作要求重拆的理由。

主要新增状态：LAYER_PLAN_READINESS_REQUIRED、IMAGE_LAYER_GEOMETRY_DEPENDENCY_MISSING、LAYER_VISUAL_QA_ACCEPTED_WITH_LIMITATIONS、SEVERE_QUALITY_RETRY_AUTHORIZED、SEVERE_QUALITY_RETRY_EXHAUSTED。其余错误码及 Magic Layer 合约保持原语义。


## 正式画布接线

正式 Image Layer 流程统一读取当前 run 的登记 canvas。任一页包含 target_slide_width_emu / target_slide_height_emu 时，所有页面须有当前且一致的批准目标，并核对 source_width / source_height。尺寸数值不同本身不是错误：940/941 像素差异和等比例分辨率变化按既有规则继续，PPTX 使用批准物理尺寸。每轴 5 源像素门槛及 framing、裁切和既有几何证据保持。全部无显式目标时保留原一致源比例回退。

首次与重复选择、新提交预留、正式打包和绑定均核对目标。失效来源或目标不删除任务、结果、锁或重试账本；已有 task 沿原身份查询，不增加提交权限。旧状态不自动迁移。

正式打包使用：
~~~powershell
python scripts/layer_package.py --state <state.json> --slide-id <id> --source-image <current-text-clean.png> --plan <current-plan.json> --result <current-result.json> --output <new-bundle-dir>
~~~
--state / --slide-id 必须成对；脚本核对当前批准 Plan、来源、结果、task 与目标后写出 Bundle。独立旧调用兼容。显式尺寸标记 explicit_target，回退标记 source_aspect_fallback；标签本身不是批准证据。尺寸在生成时正确写入，不事后改 manifest；保留四 Hard Gates 和费用授权。

## Runtime dispatch: Image Layer onboarding, QA and retries

If the user chooses **Image Layer 分支**, Layer Plan and box review may proceed without an API key. Before the first real remote submit, if `ZANCHORFLOW_360_API_KEY` is missing, direct the user to `https://research.360.cn/workspace/apikeys` and state: **“请核实当前账户的免费权益、余额与价格，并在真实提交前确认费用授权。”** The API key stays only in the local environment; never persist it in Runtime state, manifests, logs or packaged artifacts.

**Image Layer 分支:** load Reference 08 + 07. Use `scripts/layer_review_boxes.py` for the approved Source-pixel Layer Plan; within that existing workflow record `LAYER_PLAN_READINESS` using `layer_bridge.py register-readiness --state <state> --slide-id <id> --evidence <readiness.json>`. This Agent check creates no additional user confirmation gate. Run `preflight.py --scope image_layer` before using the new geometry path (conditional Pillow + NumPy; Magic Layer stays independent). Use `layer_bridge.py` for explicit submit/query lineage, `layer_package.py` (default Bundle v3) + `layer_validate_bundle.py`, then `layer_build_pptx.py`. Geometry comes only from Text-Clean and resized_image with verified declared mapping; returned boxes are identity-only, actual alpha bbox controls crop/placement. Mapping failure is a local STOP, never a paid resubmit or a v2 fallback. Preserve the 5-source-pixel canvas invariant and original text restoration coordinates.

At `LAYER_VISUAL_QA_REQUIRED`, evaluate actual editing capability, serious errors and ordinary model limitations. Register the three checks `layer_isolation`, `background_repair`, `recomposite_fidelity` as PASS / MODEL_LIMITATION / FAIL with structured hash-bound evidence via `register-visual-qa`. Both `LAYER_VISUAL_QA_PASS` and `LAYER_VISUAL_QA_ACCEPTED_WITH_LIMITATIONS` allow binding. Ordinary defects are recorded and carried into single-page Four Hard Gates and Deck-Level Validation as `accepted_limitations`; continue without repeated calls, compulsory repair or repeated approval. Never waive Content Truth, identity/lineage, semantic, page/order, geometry or file structure errors. Gates remain PASS / FAIL; new ordinary problems update limitations rather than automatically FAIL. Report actual editable ability and accepted limitations in delivery.

Technical Retry uses existing `authorize-retry`. Severe Quality Retry alone uses `authorize-quality-retry --state <state> --slide-id <id> --evidence <severe-evidence.json> --authorization <paid-authorization.json>` and is considered only for a normally completed task with identity/geometry/assembly ruled out, severe evidence and current paid authorization. Same input, Plan, provider/model and parameters; at most one extra submit, reserved before dispatch, never automatically invoked. Keep both results; use the second if its severe error disappears, otherwise STOP, never a third call. Follow Reference 08 for schemas and evidence; normal MODEL_LIMITATION never triggers retry.


<!-- TITLE_POLICY_BEGIN -->
## Optional ordinary-heading restoration pointer

The Image Layer branch inherits the same optional Title Contract from Reference 03 and native-text metadata from Reference 07. Current finalized_manifest registration and shared seal/provenance lineage checks validate the page's adopted snapshot and primary native element IDs; Graphics-first images and original layer placement remain untouched. A local display exception is not a deck heading seed or permission to remove Graphic Typography. Preserve Native Text Visual Fit, source binding, 5-source-pixel canvas tolerance, four Gates and all existing paid/retry conditions. No new title confirmation or remote reconstruction is required.
The optional sequence is: all native text restored -> independent primary-title adjustment -> existing four Gates and seal -> final deck title notes. Intentional bound title formatting is reviewed against the common native target, while text truth/readability and non-title graphics retain their original checks. Bind reviews to final postprocessed bytes; do not rewrite frozen inputs or redo remote reconstruction. Final title residuals are disclosed without automatic page repair; PASS never means exact title identity.
<!-- TITLE_POLICY_END -->


### Native assembly application selection
Use the existing sealed-page assembly and four Gates. Codex Host §4 defines --office-host auto|powerpoint|wps: prefer PowerPoint, use capability-tested KWPP.Application as the small WPS fallback, then keep that selection for the merge. This changes the native application only, not source identities, canvas mapping, text restoration or integrity checks. Existing validated candidates resume without another merge.

## V1.0 执行补充

新任务默认按独立编辑价值优先框选形状、卡片、图标、特殊箭头和共同编辑组合；未指定编辑目标时自行判断，不增加逐页询问。依照 docs/image-layer-box-selection.md，保留原 Plan 冻结、源像素坐标、几何与文字恢复合同。照片等完整资产不机械拆分，不增加必经原生形状重建，也不默认使用 302。

新 Plan 的 editing_review_required 要求 docs/image-layer-backend.md 中的逐目标隐藏/移动证据。仍为既有三个 QA 检查及四 Hard Gates；普通瑕疵且能力保持才可 MODEL_LIMITATION，编辑目标失效不能洗成通过。QA 失败是质量结果，不是提交失败，正常保存并汇总；不合格页不进入合格封存，其他能推进的页继续。

严格禁止自动再次 submit，技术失败也不例外。只有使用者主动提出当前修订才允许相应授权入口；旧费用许可/余额/key/风险标记不足以构成主动指令。页面/run 的调用历史跨 Plan 与后端保留，来源改变不伪装首次调用。既有 task_id 仅查询/下载；不主动催促重试。本文之前的技术/质量重试说明都须同时满足这一主动指令规则。具体字段、消费及旧报告兼容见当前 Host 指导。

### 轻量维护补充

沿当前 Host 指导精简重复结果镜像和本地检查，不移除来源/文件校验或逐目标覆盖。正常/恢复/重新导出的动作映射一致，稳定未知文件如实报告。DONE 本地结果缺失仅恢复原 task_id，独立目录验证后更新引用，不降级原状态或再次 submit。总览不是通过证据，原始目标图及四 Hard Gates 保留。
