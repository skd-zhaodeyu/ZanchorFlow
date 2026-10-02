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

## 两个独立入口与质量证据

Technical Retry：现有 authorize-retry；仅技术失败，未知提交须现有风险授权。已有 task_id 只查询/续传。

Severe Quality Retry：`authorize-quality-retry --state <state> --slide-id <id> --evidence <severe.json> --authorization <paid.json>`。授权入口自身不调用模型，随后仅一次显式 submit；普通局限不适用。

severe.json 必须绑定 page_id、text_clean_sha256、plan_sha256、result_sha256、task_id；classification=SEVERE；category 仅 input_content_mismatch / large_subject_loss / major_object_replaced_or_invented / severe_semantic_change / blank_or_unrecognizable；excluded_errors 的 wrong_result / task_identity / geometry / assembly 都为 PASS；evidence 为真实材料路径+SHA列表。拿错结果不能用 input_content_mismatch 冒充严重模型质量错误。

paid.json 记录 authorized=true、remaining_image_calls≥1、authorization_evidence（用户真实授权来源）、输入SHA、PlanSHA、provider、model，revoked 不为 true。不可编造授权、不可复用已撤销/耗尽授权。Agent 在调用前按既有用户额度核实本次额外调用仍覆盖；此文件不含 API Key。

在现有 ledger 记录 retry_reason 和 quality_retry_count；同一输入/Plan/provider/model 至多一次质量重拆，全部模型参数保持相同；事务预留在远程提交之前消费。未知提交不释放质量额度、不盲目补提，质量重拆的技术失败不能通过旧入口再付费 submit。两次结果分目录保留；第二次只判断严重错误是否消失：PASS 或 MODEL_LIMITATION 则用第二次继续，仍严重则 STOP，不第三次，不按美观分选优。
