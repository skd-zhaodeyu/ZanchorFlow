# ZAnchorFlow · Image Layer 分支操作说明

本文件是实现说明；运行决策以 Reference 08 + 07 为准。保留既有 Text-Clean、分支选择及用户 Plan 批准，不增加确认关卡。

## 零安装运行与条件依赖

在解压目录运行 Python 脚本。`preflight.py --skill-dir . --output-dir <output> --scope image_layer` 检查 Pillow + NumPy；缺失报 IMAGE_LAYER_GEOMETRY_DEPENDENCY_MISSING，仅阻断新 Image Layer geometry。Magic Layer / package / merge 不因此要求 NumPy。本指南不自动安装任何依赖。

API Key 用进程环境 ZANCHORFLOW_360_API_KEY，不保存到文件、state、日志。缺失时原 onboarding 地址 `https://research.360.cn/workspace/apikeys` 保留；真实提交前核实当前账户权益、余额与价格，保留费用授权要求；不保证固定免费额度。

## 标准流程与就绪 JSON

Layer Plan / 框选预览 → 既有 Plan 批准及 Agent readiness → 显式 submit → 同一 task_id 查询/下载 → 默认 Bundle v3 打包及验证 → Graphics-first → Visual QA → bind → 原生文字恢复 → 四门 seal → assembly / 整套检查 / publish。

```json
{
  "page_id": "S001", "text_clean_sha256": "<input sha>", "plan_sha256": "<plan sha>",
  "checks": {
    "editing_purpose": "READY", "common_edit_grouping": "READY",
    "exclusive_structure_ownership": "READY", "protected_background": "READY",
    "over_split": "READY", "adaptive_margin": "READY", "target_count": "READY",
    "whole_asset_granularity": "READY"
  },
  "reasons": {
    "editing_purpose": "说明实际移动/替换/删除目的", "common_edit_grouping": "说明共同编辑分组",
    "exclusive_structure_ownership": "说明专属边框、阴影和连接归属", "protected_background": "说明背景保护",
    "over_split": "无明显过拆", "adaptive_margin": "根据本页边缘/阴影/邻接距离有限调整",
    "target_count": "1–6目标", "whole_asset_granularity": "照片/截图可整体编辑，无需内部原子化"
  }
}
```

`python scripts/layer_bridge.py register-readiness --state <state> --slide-id S001 --evidence <readiness.json>`。READY 是 Agent 就绪记录，不是新的用户确认；NOT_READY 仅用于明确违规或明显框选错误，不因模型风险拒绝调用。实质改 Plan 仍走原批准流程。

## Bundle v3 与诊断

新打包默认 v3，返回框仅身份校验；整页候选来自 Text-Clean 与 resized_image；实际 alpha bbox 控制 crop 和 placement。geometry/ 下源图、返回图和 evidence.json 不是 layers。证据安全路径、哈希及候选验证结果必须一致。旧 v2 独立按原规则验证，不静默升级；--schema-version 2 只供旧兼容，不得用于回避几何失败。

验证器只测量声明候选，不拟合新映射。INSUFFICIENT / CONTRADICTED 报 LAYER_CANVAS_MAPPING_UNRESOLVED；仅诊断本地 geometry，不重新调用模型。

## Visual QA 与普通局限

目标：评估当前分层结果能够提供的实际编辑能力，识别严重错误，并登记普通模型局限。先检查原始层浅/深底、合成和移开效果。旧全部 PASS 报告兼容；新局限示例：

```json
{
  "page_id": "S001", "bundle_manifest_sha256": "<bundle sha>",
  "checks": {"layer_isolation": "MODEL_LIMITATION", "background_repair": "PASS", "recomposite_fidelity": "PASS"},
  "evidence": {"layer_isolation": "浅深底及移开检查材料", "background_repair": "背景检查材料", "recomposite_fidelity": "合成检查材料"},
  "check_limitations": {"layer_isolation": ["L1"]},
  "limitations": [{
    "limitation_id": "L1", "category": "foreground_edge_artifact", "affected_target_ids": ["module_02"],
    "description": "少量边缘阴影残留", "editing_impact": "模块可整体移动和删除，边缘仍带相邻阴影",
    "visual_impact": "正常页面比例下轻微可见", "evidence": [{"file": "<evidence path>", "sha256": "<sha>"}]
  }]
}
```

register-visual-qa 的两种通过状态为 LAYER_VISUAL_QA_PASS / LAYER_VISUAL_QA_ACCEPTED_WITH_LIMITATIONS；任意检查 FAIL 为 LAYER_VISUAL_QA_FAILED。普通 halo、轻微色差、阴影变化、局部残留、小对象提取较差、粘连或可交付背景缺陷登记后继续，不重拆，不强制修补，不反复征询。

背景或整页问题 affected_target_ids=[]，并附 affected_scope=background/page。evidence 每项路径及 SHA 必须对应真实检查材料。证据变更使 QA 和下游 stale，不触发模型调用。

## Four Hard Gates 与 Deck-Level Validation

仍使用 PASS / FAIL；page review 与 deck review 均携带当前 accepted_limitations。每项 limitation_matches 示例：

```json
{"limitation_id":"L1","reason":"category、target及原证据一致，程度未扩大，移动能力保持","unchanged_extent":true,"claimed_capability_preserved":true}
```

整套匹配须加 page_id，防止跨页同名 id 混淆。相同、未扩大的普通局限不得重复处罚；新普通问题更新局限记录并重做相关下游检查，严重问题及不可豁免项仍 FAIL。Content Truth、文字真值/事实、来源/页面/task/result/lineage、页缺失/顺序、严重语义/geometry、PPTX 结构永不豁免。交付说明列出实际编辑能力和 accepted limitations。

## 使用者主动修订，禁止自动再次分层

第一次调用后，无论质量差、残影、未知响应或技术异常，Agent 不自行再次 submit，不主动询问重试，也不借改框、换后端、改参数或新输入伪装首次调用。可以查询同一 task_id、续传、下载、本地检查和组装。

调用 ledger 按页面及 run 保留；Plan 改变会归档请求、结果和旧 Plan，不删除已调用事实。已有 task_id/结果的旧任务也视为调用过。费用授权、API key、风险标记和未消费重试额度不是新的修订指令。

只有使用者后来主动明确提出重新分层/修订，才登记一条真实指令。authorize-resubmit --authorization <user-request.json> 本身不调用服务。指令字段包括 source=user、user_requested_relayer=true、user_message_id、user_message、authorization_id、authorized=true、remaining_image_calls，以及 page_id/run_id/text_clean_sha256/plan_sha256/provider_identity（含模型参数）。未知或仍在运行的旧调用还须真实的 accept_duplicate_charge_risk=true。不能虚构用户消息；脚本检查结构/作用域，实际消息来源由执行者核对。

每个页面的一条指令只消费一次；不能换 authorization_id 重放同一 user_message_id。授权在远程提交前事务消费，未知提交不退还。禁止把普通预算许可改写成主动重分层指令。分批修订必须在用户实际请求范围内，每页绑定自己的当前来源。

Technical Retry 保留 authorize-retry --authorization <user-request.json>，未知状态同时需要现有 --accept-duplicate-charge-risk。Severe Quality Retry 保留原严重证据与费用字段，但授权文件也必须包含上述主动指令字段。普通质量差不会自动使用任何入口。用户主动修订可用通用入口；保持费用范围明确，不推断无限调用授权。

## V1.0 逐目标编辑证据

新登记的 Plan 带 editing_review_required=true，旧已冻结 Plan 保留旧验收。运行 layer_edit_review.py --bundle <current-bundle> --output <work/editing-preview>，产生每层隐藏与移动的本地对照以及 NOT_ASSESSED 收据；不调用模型或逐页启动 PowerPoint。

新 QA 在已有三项检查内增加 target_edit_checks，每个目标一项：
target_id、requested_action（move/resize/hide/replace，与冻结 Plan 的 primary_edit_action 一致；旧的描述性 edit_action 保留说明用途，未明确主动作时缺省 move）、assessment（PASS/MODEL_LIMITATION/FAIL）、capability_preserved、actual_independence、background_residual、neighbor_impact、connector_behavior、explanation、hidden_evidence=[{file,sha256}]；move 还需 move_evidence。关联当前 page_id 和 bundle_manifest_sha256。

轻微瑕疵且约定能力仍成立可 MODEL_LIMITATION。完整对象残留、明显重影或关系破坏使目标失效时必须 FAIL，不能因“七层/可单独选中”写成成功。证据中的平移位置用于诊断，刻意造成的重叠或裁出画布不能误判成模型缺陷。

合法 FAIL 报告正常登记，返回 LAYER_VISUAL_QA_FAILED、remote_result_received=true、quality_issue=true、automatic_resubmit=false，CLI 不把它变成提交错误。不合格页保留检查用结果，不能 bind/seal 为合格页；其他可推进页继续处理。status 保留原主要字段，增加 page_statuses 与 actionable_pages。只汇总实际能力，不催促使用者修订。

原四项 Hard Gates、真实性、来源、task/result 身份、几何和整套顺序检查仍有效。新证据与历史报告按各自策略验证，补本地证据不重新分层。当前默认仍为 360；302 不进入默认或自动备用路线。

## 本地结果恢复与轻量检查

DONE 任务如果本地归一化结果或其图层缺失/损坏，可 query 原 task_id；完整有效结果直接复用。恢复使用独立目录，原 result、QA 和 ledger 保留，来源/Plan/后端/任务匹配且新文件核验完成后再换引用。恢复期间 RUNNING/FAILED/NOT_FOUND 不把原 DONE 降级，也不自动 submit；过期/无法获取要如实报告。已知原资产哈希与恢复内容不一致时保留原记录并返回恢复不符。

预览工具从冻结主动作决定是否生成移动图：隐藏证据覆盖全部目标，仅 move 生成移动模拟。已有 composite 只在实读像素完全一致时复用。缓存先核验 Bundle/Plan/真实资产和已生成证据哈希；仅 manifest 一样不足以复用。overview 为 navigation_only，不能单独替代全分辨率目标检查，疑点要看原图。工具只标 NOT_ASSESSED，原四 Hard Gates 和禁止自动重分层规则不变。
