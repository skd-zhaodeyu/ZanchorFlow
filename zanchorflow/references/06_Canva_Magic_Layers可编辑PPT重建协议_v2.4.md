# Canva Magic Layers 可编辑 PPT 重建协议 v2.4
## Stage 3 — Editable Reconstruction & PPT Delivery Protocol

**适用范围：** 将 Stage 2 已批准的 PPT 页面图像，经 Stage 3 文字预处理、Canva Magic Layers 结构恢复、单页 PPTX 获取与原生文字复原，形成最终可编辑 PPTX。  
**阶段定位：** Stage 3 负责文字接管、可编辑结构恢复、单页验证、整套装配与最终 PPTX 交付；不负责重新进行内容架构设计或视觉创作。  
**核心目标：** 在尽量保持 Stage 2 已批准视觉结果的前提下，恢复具有实际使用价值的编辑能力，并把最终正确文字作为原生 PowerPoint 文本写回 PPTX。

**规范依赖：** Stage 3 文字发现、消字、Text Manifest、Removal Inventory 与 Native Text Visual Fit 的详细规则，以《Stage3_文字处理_消字与复原规范 v1.5》为准。本文件负责 Stage 3 总体编排与质量门，不重复定义其全部内部算法。

---

# Part I. Stable Stage 3 Protocol

# 1. 核心原则

Stage 3 不执行“全图矢量化”，也不追求所有视觉细节的原子级拆解。

Stage 3 的核心任务是：

> **Separate text truth from structural reconstruction; use Magic Layers to recover useful visual structure, then restore final text as native PowerPoint text while preserving the approved design.**

中文：

> **把文字真值与图形结构重建解耦：Magic Layers 负责恢复有实际编辑价值的视觉结构，最终文字由 Stage 3 依据确定真值恢复为 PowerPoint 原生文本，同时尽量保持 Stage 2 已批准设计。**

Stage 3 最终必须同时满足：

- Content Truth；
- Semantic Fidelity；
- Functional Editability；
- Visual Fidelity。

四项均属于 Hard Gates，不使用简单优先级替代其中任意一项。

---

# 2. Stage 3 输入

Stage 3 的长期最小输入仍且仅包括：

```text
Approved Slide Render
+
Stage 2 Final Content Truth
```

## 2.1 Approved Slide Render

Stage 2 已批准的最终单页视觉结果。

作用：

- 作为 Stage 3 的视觉保真基准；
- 用于判断主构图、视觉重心、主要对象、色彩关系和信息层级是否被保留；
- 用于派生 Text Manifest 的位置、样式和可见字形几何；
- 用于派生 Text-Clean Render；
- 不作为最终文字、数字、单位或正式名称的内容真值来源。

## 2.2 Stage 2 Final Content Truth

Stage 2 已确认的最终内容真值。

至少应包含：

```yaml
stage3_content_truth:
  slide_id:
  meaningful_text:
  exact_facts:
```

其中：

- `meaningful_text` 覆盖最终 Approved Slide 中应继续存在的正式语义文字和已批准装饰文字；
- `exact_facts` 记录数字、单位、百分比、日期、正式名称、专有名称和其他必须精确保持的信息。

Content Truth 必须来自 Stage 2 已确认的文字计划、语义计划或用户批准内容，不得从最终图片反向 OCR 后生成。

---

# 3. Stage 3 输出与源文件角色

Stage 3 使用三层角色，不再把 Canva Presentation 作为最终 Canonical Editable Source。

```text
Intermediate Structural Source
= Canva Magic Layers Single-Page Design

Validated Single-Page Editable Source
= Validated Editable Single-Page PPTX

Final Canonical Delivery Artifact
= Validated Merged Editable PPTX
```

## 3.1 Intermediate Structural Source

Canva Magic Layers Single-Page Design 负责承载视觉结构恢复结果，是结构中间态。

它不承担最终文字真值，也不要求成为整套演示文稿的唯一母版。

## 3.2 Validated Single-Page Editable Source

单页 Canva 结果获得 PPTX 后，经 Native Text Visual Fit 和四个 Hard Gates 验证，形成 `Validated Editable Single-Page PPTX`。

这是进入整套合并的唯一允许页面状态。

## 3.3 Final Canonical Delivery Artifact

全部已验证单页 PPTX 按既定顺序本地合并，并通过 Deck-Level Validation 后，形成最终 Canonical Delivery Artifact。

---

# 4. Stage 3 总体流程

```text
STAGE 3A — ENTRY & TEXT PREPARATION

① Entry Validation
        ↓
② Intended Text Set / Text Manifest
        ↓
③ Full-page Text Discovery / Removal Inventory
        ↓
④ Text-only Cleanup
        ↓
⑤ Text-Clean Integrity Check
        ↓
Text-Clean Render


STAGE 3B — STRUCTURAL RECONSTRUCTION

⑥ Per-Slide Magic Layers Reconstruction
        ↓
⑦ Structural Reconstruction Assessment
        ↓
⑧ Acquire Single-Page Graphics-first PPTX


STAGE 3C — TEXT RESTORATION & SINGLE-PAGE VALIDATION

⑨ Native Text Visual Fit
        ↓
⑩ Single-Page Four Hard Gates
        ↓
Validated Editable Single-Page PPTX


STAGE 3D — DECK DELIVERY

⑪ Local PPTX Merge
        ↓
⑫ Deck-Level Validation
        ↓
Final Validated Editable PPTX
```

---

# 5. Step 1 — Entry Validation

页面进入 Stage 3 前，应确认：

```text
[ ] Approved Slide Render 已确定
[ ] Stage 2 Final Content Truth 已确定
[ ] meaningful_text 已覆盖最终应保留的正式与已批准装饰文字
[ ] 页面已经通过 Stage 2 最终视觉验收
[ ] 页面顺序已经确定
[ ] Approved Slide Render 与 Final Content Truth 属于同一 slide_id / 页面身份
[ ] 已基于 Approved Slide Render + Final Content Truth + Deck canvas 计算当前 `source_fingerprint`
[ ] 当前页画布符合整套 Deck 已固定 canvas invariant
[ ] 不再需要 Stage 3 重新决定页面语义或视觉方向
```

入口不完整属于 **Entry Block**，不是 `RETURN_TO_STAGE_2` 结构状态。至少使用：

```text
MISSING_APPROVED_SLIDE_RENDER
MISSING_STAGE2_CONTENT_TRUTH
SLIDE_PAIRING_MISMATCH
DECK_CANVAS_INVARIANT_FAILED
STAGE3_ENTRY_BLOCKED
```

处理原则：

- 缺失/错配的 Stage 2 交付物先在交付层补齐或纠正；
- canvas invariant：用户明确比例/尺寸优先；否则沿用已批准 Deck；若没有任何依据，默认 16:9；
- 不得把入口不完整、页面身份错配或画布不一致归因为 Magic Layers 失败；
- 不得为了消除入口错误直接进入 `RETURN_TO_STAGE_2` 的结构性重建分支。

## 5.1 Upstream Change Invalidation

某页 `Approved Slide Render`、`Stage 2 Final Content Truth` 或该页 canvas mapping 发生任何有效修订后，该页全部 Stage 3 派生产物立即失效：

```text
Text Manifest
Removal Inventory
Text-Clean Render
Magic Layers Design
Graphics-first PPTX
Restored / Validated Single-Page PPTX
以及包含该旧单页的 Merged PPTX
```

不得复用旧派生产物或只局部“补丁同步”。该页必须从 Entry Validation 重新执行。

### 5.2 Source Fingerprint / Revision Binding

`slide_id` 只表示稳定页面身份；同一页面的上游内容发生修订后，必须另外使用 `source_fingerprint` 区分版本。Entry Validation 为每页计算：

```text
source_fingerprint
= SHA-256(Approved Slide Render bytes
           + canonicalized Stage 2 Final Content Truth
           + Deck canvas spec)
```

规范要求的是**确定性摘要**，不限定具体序列化库；Final Content Truth 必须先使用稳定字段顺序/编码进行 canonical serialization。所有后续 Stage 3 工件与 attempt 都必须记录当前 `slide_id + source_fingerprint`。

规则：

- Approved Render、Final Content Truth 或 Deck canvas 任一有效改变 → `source_fingerprint` 必须改变；
- 旧 fingerprint 下的 Text Manifest、Removal Inventory、Text-Clean Render、Canva job/design、Graphics-first PPTX、Validated Single-Page PPTX 与包含它的 Merged PPTX 全部 stale；
- `deck_order` 仅改变页面顺序时不改变各单页 `source_fingerprint`；
- 获取 PPTX、文字恢复和 Merge 前都必须拒绝 `slide_id` 相同但 `source_fingerprint` 不一致的旧工件；
- `source_fingerprint` 是 Stage 3 运行元数据，不是 Stage 2 第三个交付物。

Stage 3 不重新定义：

- 页面任务；
- 页面核心表达；
- 语义关系；
- 页面视觉方向；
- Anchor；
- Style DNA；
- 原始构图策略。

---

# 6. Steps 2–5 — Text Preparation

Stage 3 在调用 Magic Layers 前，必须先按照《Stage3_文字处理_消字与复原规范 v1.5》完成：

```text
Approved Slide Render
+
Stage 2 Final Content Truth
        ↓
Intended Text Set
        ↓
初始化 Text Manifest 内容项（真值 / occurrence）
        ↓
Full-page Text Discovery
        ↓
Finalize Text Manifest geometry/style
+
Removal Inventory
        ↓
Representation / Treatment Validation
（含 Graphic Typography / approved graphic asset 判定）
        ↓
Stage 3 Text Plan = CURRENT
        ↓
Text-only Cleanup
        ↓
Residual Text Check
+
Non-text Preservation Check
+
Text-Clean Canvas Registration
        ↓
Formal Text-Clean Render
        ↓
text_clean_fingerprint = SHA-256(Formal Text-Clean Render bytes)
```

只有：

```text
Representation / Treatment Validation = PASS
AND
Stage 3 Text Plan = CURRENT
AND
Residual Text Check = PASS
AND
Non-text Preservation Check = PASS
AND
Text-Clean Canvas Registration = PASS
```

才允许形成正式 Text-Clean 输入并进入 Magic Layers。

`Stage 3 Text Plan` 必须绑定当前 Approved Slide Render、当前 Final Content Truth、Finalized Text Manifest 与 Removal Inventory。任何 Manifest / Inventory treatment、representation role 或上游 Truth 发生变化，旧 Text-Clean 及其全部下游工件立即 stale；不得先执行破坏性 cleanup，再补做文字表示分类。

文字预处理失败不得伪装成 Magic Layers 失败。

---

# 7. Step 6 — Per-Slide Magic Layers Reconstruction

每个已批准页面独立进行 Magic Layers 结构重建。Magic Layers job/design attempt 必须绑定当前 `slide_id + source_fingerprint + text_clean_fingerprint`；其中：

```text
text_clean_fingerprint
= SHA-256(Formal Text-Clean Render bytes)
```

若 Formal Text-Clean Render 被重新生成，即使 Approved Render / Final Content Truth 没有变化，只要 bytes 改变，`text_clean_fingerprint` 就必须改变；旧 Text-Clean 对应的 Magic Layers attempt 与其下游 PPTX 立即 superseded。

首次调用当前执行环境中的 Magic Layers 前，必须做一次能力/连接 Preflight：

```text
[ ] Magic Layers 能力当前可访问
[ ] 账号/权限/会话有效
[ ] 当前输入格式/尺寸受支持
[ ] 能创建并读取本次结构重建结果
```

若服务、权限、连接、会话或能力本身不可用，记录：

```text
MAGIC_LAYERS_TOOL_UNAVAILABLE
```

若能力可用但本次调用/job 因工具执行层原因失败，记录：

```text
MAGIC_LAYERS_EXECUTION_FAILED
```

这两类都属于工具/实现层阻断，**不得进入 Structural Reconstruction Assessment，也不得 RETURN_TO_STAGE_2**。工具/会话/服务失败也**不消耗结构性的 `RETRY_ONCE` 配额**；`RETRY_ONCE` 只统计已经成功得到结构重建结果后的偶发结构异常。

正式输入是：

```text
Text-Clean Render
        ↓
Magic Layers
        ↓
Editable Single-Page Canva Design
```

Magic Layers 的职责是：

> **恢复视觉结构和具有实际使用价值的对象层级。**

Magic Layers 不负责最终文字真值，也不以文字识别质量评价结构重建是否成功。

---

# 8. Step 7 — Structural Reconstruction Assessment

每一页完成 Magic Layers 后，只评价结构恢复结果，再决定后续动作。

仅使用四种状态：

```text
ACCEPT
RETRY_ONCE
ASSISTED_CLEANUP_REQUIRED
RETURN_TO_STAGE_2
```

## 8.1 ACCEPT

满足：

- 主要视觉对象存在；
- 核心业务模块具有与实际使用需求相匹配的独立性；
- 主体层级正确；
- 主要语义关系没有被结构重建破坏；
- 页面具有实际继续编辑价值。

允许存在：

- 少量图层层级偏差；
- 背景装饰合并；
- 非关键复杂插画保持整体对象；
- 少量几何位置偏差。

文字缺失、错字、乱码、数字或单位识别错误不属于本步骤的结构失败，因为最终文字由 Native Text Visual Fit 接管。

消字阶段误作图形保留、随后被 Magic Layers 识别为普通文本的非关键装饰性英文字形，若不属于冻结清单中显式批准的图形资产或 Graphic Typography，且可按 §9.2 在当前 PPTX 内安全清理并按现有内容规则处理，则继续文字恢复，不因此重送 Magic Layers。

## 8.2 RETRY_ONCE

仅适用于源页面与 Text-Clean Render 本身具有良好可分层条件，但本次 Magic Layers 出现明显偶发的**结构性异常**，例如：

- 明显对象错误粘连；
- 主要视觉对象异常缺失；
- 结构恢复明显偏离正常预期；
- 关键非文字对象层级发生偶发错误。

原则：

> **同一 Text-Clean 输入在没有改变条件的情况下，只允许一次合理重试。**

结构 retry budget 使用最小三态：

```text
available → pending → consumed
```

- 第一次结构异常决定 `RETRY_ONCE` 时，由 `available` 进入 `pending`；
- retry job 因工具层失败而未产出可 Assessment 的结构结果时，保持 `pending`，修复工具后仍只完成这一次已授权 retry；
- retry 成功产出可 Assessment 的结构结果后，由 `pending` 进入 `consumed`；
- `consumed` 后不得再授权第二次结构 retry。

因此，工具失败本身不消耗结构结果额度，也不会额外生成新的 retry 额度。

`RETRY_ONCE` budget 一旦进入 `consumed`，重试结果重新 Assessment 时只允许进入：

```text
ACCEPT
ASSISTED_CLEANUP_REQUIRED
RETURN_TO_STAGE_2
```

不得再次选择 `RETRY_ONCE`。

以下不得触发 RETRY_ONCE：

- 中文错字；
- 乱码；
- 文字漏识别；
- 数字、单位文字识别错误；
- 字号、字重、字距或换行差异。

## 8.3 ASSISTED_CLEANUP_REQUIRED

适用于页面本身没有明显设计缺陷，但当前结构恢复能力不足以自动完成必要结构修复的情况，例如：

- 某个必要非文字对象未被自动恢复；
- 某个必要结构关系需要少量人工或辅助补完；
- 当前自动化接口无法完成一个明确且局部的结构整理。

此类情况不应错误返回 Stage 2。

同一个未变化的局部问题不得无限循环 `ASSISTED_CLEANUP_REQUIRED → cleanup → Assessment`。完成一次针对该明确问题的辅助补完并重新 Assessment 后，若同一阻断仍存在，必须停止重复补完并重新归因：

- 工具/自动化能力仍不足 → `ASSISTED_CLEANUP_UNRESOLVED`，显式阻断并交给实现/人工能力处理；
- 事实证明源页面结构本身才是根因 → 才允许 `RETURN_TO_STAGE_2`。

## 8.4 RETURN_TO_STAGE_2

仅在 Stage 2 页面本身构成结构重建失败根因时触发，例如：

- 非文字核心对象发生大面积不可分离融合；
- 主要语义对象在源图中本身无法形成可理解的独立结构；
- Text-Clean 后仍无法在不重新设计页面的情况下获得具有实际编辑价值的视觉结构；
- Stage 3 修复成本明显高于重新生成一个视觉质量相当且更容易重建的页面。

单纯文字与背景融合、文字识别错误或合法装饰文字需要恢复，不再是 RETURN_TO_STAGE_2 的充分理由。

原则：

> **只有 Stage 2 页面本身是结构性问题根源时，Stage 3 才返回 Stage 2。**

## 8.5 状态流转

```text
ACCEPT
→ 进入单页 PPTX 获取

ASSISTED_CLEANUP_REQUIRED
→ 完成标记的局部结构补完后重新 Assessment

RETRY_ONCE
→ 重试后重新 Assessment

RETURN_TO_STAGE_2
→ 阻断当前页继续处理，先返回 Stage 2 处理根因
```

---

## 8.6 Active Reconstruction Attempt Lineage

同一 `slide_id` 在 `RETRY_ONCE`、辅助补完或重新执行 Magic Layers 后可能存在多个 job/design 结果。Stage 3 必须把工具返回的 job/design ID 作为运行级 attempt 身份，并明确唯一的 **active reconstruction attempt**。

规则：

- 只有当前通过 Structural Reconstruction Assessment、被选为继续下游处理的 attempt 才能进入 PPTX acquisition；
- active attempt 必须与当前 `slide_id + source_fingerprint + text_clean_fingerprint` 三者完全匹配；
- 同一 `slide_id` 的旧 attempt，或绑定旧 `source_fingerprint / text_clean_fingerprint` 的 attempt，必须标记为 superseded，不得继续下载、恢复文字或进入 Merge；
- retry/cleanup 产生新 Design 后，必须先更新 `slide_id → active job/design ID` 映射，再允许获取 PPTX；
- `slide_id` 负责页面身份，job/design ID 负责该页面当前重建 attempt 身份，两者不得互相替代。

这样可防止同页重试后误下载第一次、已被淘汰的 Canva Design。

---

# 9. Step 8 — Acquire Single-Page Graphics-first PPTX

结构评估通过后，将 Magic Layers 单页 Design 转换为单页 PPTX。

当前主路线：

```text
Editable Single-Page Canva Design
        ↓
Codex Browser Host（现有 Design 的 PowerPoint/PPTX UI）
        ↓
精确 Browser download event / Preferences / History / file 证据
        ↓
现有 finalizer
        ↓
Graphics-first PPTX
```

Browser UI 由执行 Host 驱动；本包内 `host_acquisition.py` 只负责可信 identity、intent、精确下载证据与下游衔接，不伪装成独立 Browser API。下载能力缺失或执行失败时记录：

```text
PPTX_ACQUISITION_FAILED
```

它属于下载/实现层失败，不属于 Magic Layers 结构失败，也不得 RETURN_TO_STAGE_2。

获取完成后，必须确认该 PPTX 属于当前 `slide_id / Canva Design` lineage，而不是浏览器下载目录中的旧文件或其他并行页面。无法建立来源对应时：

```text
PPTX_SOURCE_MISMATCH
```

停止后续处理，不得靠文件名相似或“最后下载时间”猜测。

原则：

- 不使用 `Resize to Presentation` 作为主路线；
- 不要求在 Canva 内先完成多页 Deck Assembly；
- 单页 PPTX 此时仍是 Graphics-first 中间态；
- 此时不要求 Canva 文字正确，因为最终文字尚未恢复；
- `PPTX_ACQUISITION_FAILED` 的默认动作是按 Host recovery contract 恢复运行环境、刷新可信证据、等待/有限重试或从同一 checkpoint 续跑；若证据指向正式 Skill 实现缺陷，则记录 `IMPLEMENTATION_DEFECT_SUSPECTED` 并停止热修改。除非用户明确决定改变实现路线，**不得自动改走 `Resize to Presentation`，也不得自动切换到 Canva REST API** 来掩盖当前实现失败。

Acquired Graphics-first PPTX 必须**恰好包含 1 张 slide**，并与当前 `slide_id` lineage 对应。零页、多页、额外空白页或下载到其他页面均不接受。

若文件无法打开、slide 数量不为 1、页面尺寸异常、主要图形丢失或对象结构严重损坏，记录：

```text
GRAPHICS_FIRST_PPTX_INVALID
```

并停止文字恢复。

## 9.1 Graphics-first Canvas Normalization

原下载、来源绑定、批准 canvas 和 source fingerprint 保持不变。画布适配在既有 Native Text Visual Fit 的恢复版保存中完成，不新增归一副本、独立 CLI 或正式状态阶段。

### 原容差路径

保留小数计算，两轴使用同一批准 Deck 单位：

```text
sx = target_deck_width / source_width
sy = target_deck_height / source_height
delta_width = abs(actual_slide_width / sx - source_width)
delta_height = abs(actual_slide_height / sy - source_height)
```

两轴分别 ≤5 个源像素时：保留原对象，不移动、缩放或重新布局；保存时设置目标 Deck 尺寸，新增文字映射到该目标。原路径不新增背景覆盖、对象边界或机械宽高比条件。

### 受控等比例适配路径

任一原尺寸误差 >5 源像素时，只有实际核验表明同一页面、same framing、无裁切/扩边/旋转/重新布局，且有绑定当前下载 SHA-256 和 text_clean_fingerprint 的具体证据，才考虑自动适配。不得只由比例接近推断 framing。

对下载尺寸与源图，以及目标尺寸与源图，分别计算：

```text
aspect_width_error = abs(width * source_height / height - source_width)
aspect_height_error = abs(height * source_width / width - source_height)
```

四项均须 ≤5 源像素。尺寸必须为有限正值；slide 尺寸为整数 EMU。超出比例容差返回 DECK_CANVAS_INVARIANT_FAILED；证据、对象变换或内容矩形无法确定返回 CANVAS_MAPPING_UNRESOLVED。禁止猜测 DPI 或非等比拉伸。

先按 9.2 完成文字污染清理，再建立保留图形基准。清理记录绑定原下载，列出获准清理的普通文字对象与证据；保留集合必须可从原下载和记录复算。辅助函数仅允许清理无填充、无可见线条/效果/继承样式的独立普通文本框，不允许借清理记录删除非文字图形或受保护 Graphic Typography。复杂清理不在本自动适配范围。

整页预检支持具有显式变换的 shape、picture、group。仅几何变化不能保持视觉的对象、可见线宽、效果、继承样式、扩展或特殊对象停止。通过后统一：

```text
s = min(target_width / actual_width, target_height / actual_height)
dx = (target_width - actual_width * s) / 2
dy = (target_height - actual_height * s) / 2
content_rect = [dx, dy, actual_width * s, actual_height * s]
```

组只变换顶层 off/ext，内部 chOff/chExt 和子对象保持不变。保留旋转/翻转、路径、资源及对象顺序。使用精确比例运算，仅写入时统一取最近整数（半数取偶）；几何误差不超过 1 EMU。新增文字位置和可见字形尺寸均使用同一 content_rect，再执行既有字体拟合规则。

在现有单页验收中附加 canvas_mapping（参数、清理、输入/输出哈希及注册证据）。封页复算保留对象和变换、核对目标尺寸、对象 XML、media 和关系；记录验收文件路径与 SHA-256，后续来源检查验证其未变。既有已封页成果不强制迁移。Content Truth、四 Hard Gates 和最终 Deck 尺寸标准不放宽。

Codex 的具体函数和调用方式仅见 Host adapter；此规则不为 Image Layer 新增尺寸重写路线。

## 9.2 Graphics-first Text Neutrality Check

Text-Clean 输入并不保证 Canva 永远不会重新解释出普通文本对象。因此在 Native Text Visual Fit 前，必须检查 Graphics-first PPTX：

```text
目标：除显式 `preserve_as_graphic` 的 approved graphic asset 与已批准 Graphic Typography 仍以图形存在外，
不得存在会与最终 Manifest 文字叠加的普通文本对象。
检查既包括肉眼可见文字，也包括隐藏、零透明度、画布外但仍属于页面对象树的普通文本对象，以防后续编辑/兼容转换时重新出现。
```

若发现 Magic Layers 新生成/误解释的普通文本：

§8.1 的非关键英文字形仅沿用此局部处理路径。合法文字按当前 Final Content Truth / Manifest 恢复，错误或额外文字按原规则丢弃；混合图文对象、关键 Logo、图形字标、身份不明对象不能套用该例外。Codex 自动清理仅删除现有辅助函数已验证的纯文本框，不扩大删除权限。

1. 能安全删除且不伤非文字结构 → 删除后重新检查，并重新验证 Graphics-first PPTX 的主要视觉结构仍成立；
2. 不能安全删除 → 记录：

```text
GRAPHICS_FIRST_TEXT_CONTAMINATION
```

并停止 Native Text Visual Fit。

凡执行本地文字清理，记录原下载 SHA-256、实际删除的对象 ID 和处理依据，保存既有 `canvas_mapping` 验收记录，原容差路径亦适用。封页从原下载复算合法清理和映射后核对所有保留对象；不得用清理后文件重新定义基准。

若显式 `preserve_as_graphic`（包括 approved graphic asset 或 Graphic Typography）被 Magic Layers 重新解释为普通可编辑文本，而不再作为批准图形存在，记录：

```text
PRESERVED_GRAPHIC_REINTERPRETED_AS_TEXT
```

已冻结清单若将误分类字符登记为批准图形，应报告清单冲突并保留当前文件；不得自动改清单、删除对象或重送 Magic。本轮不增加旧清单迁移机制。

不得在其上再叠加 Manifest 原生文字。对于 `representation_role=graphic_typography` 的 occurrence，Native Text Visual Fit 必须跳过；不得为了追求原子文字编辑性而把已批准的图形化字形强制替换成普通 TextBox。

---

# 10. Step 9 — Native Text Visual Fit

Graphics-first PPTX 获得后，按照《Stage3_文字处理_消字与复原规范 v1.5》恢复所有：

```text
treatment = remove_and_restore
```

的文字。正式恢复前先解析本页实际字体可用性与 Deck-scoped fallback bindings，并计算：

```text
text_restore_fingerprint
= SHA-256(canonicalized Finalized Text Manifest
           + canonicalized effective page font fallback bindings)
```

若本页没有 fallback，第二项使用稳定的空映射。Restored / Validated Single-Page PPTX 必须绑定当前 `slide_id + source_fingerprint + text_clean_fingerprint + text_restore_fingerprint`。

若 Finalized Text Manifest 的 content / geometry / style，或本页实际使用的 font fallback bindings 发生变化，旧 restored/validated PPTX 与包含它的 merged deck 立即 stale，必须重新 Native Text Visual Fit 与后续 Hard Gates；若该 Manifest 修订同时改变 treatment / cleanup 范围并导致 Formal Text-Clean 改变，则按新的 `text_clean_fingerprint` 从 Magic Layers 起重跑。不得因纯文字恢复参数变化无意义重跑 Magic Layers。

恢复原则：

- 最终内容只能来自 Text Manifest；
- 标题、正文、数字、标签、角标、品牌语和合法 slogan 使用同一套 Native Text Visual Fit；
- 以 Approved Slide Render 的可见字形包络作为视觉拟合目标；
- 允许最小字号、字距、基线、位置、TextBox 尺寸等校正；
- 不允许为了排版修改 content；
- 默认不嵌入字体；
- 每个 Manifest element 恢复一次且只能一次。

Native Text Visual Fit 结束后才进入最终单页质量门。

---

# 11. Functional Editability

Stage 3 追求 Functional Editability，而不是 Atomic Editability。

## 11.1 基本定义

最终页面至少应满足：

- 有语义作用的标题和正文可编辑；
- 数字、单位、标签和关键事实可编辑；
- 应保留且要求可编辑的角标、品牌语和合法装饰文字可编辑；
- 主要语义对象或主要语义组具有与实际使用需求相匹配的独立编辑能力；
- 主要视觉对象可以移动、缩放或替换；
- 页面可以继续用于真实汇报修改和复用；
- 背景和非关键复杂装饰不妨碍主要内容编辑。

## 11.2 Semantic Editing Granularity

编辑粒度由语义作用决定，而不是由视觉复杂度决定。

原则：

> **凡是对象的几何形态、位置关系或比例本身承载核心语义或定量信息，其编辑粒度应支持该语义的实际修改。**

例如：

- 普通背景插画可以整体作为一个对象；
- 装饰性工业园插画可以整体作为一个对象；
- 三个独立业务模块若分别承担核心语义，应尽量保持可独立调整；
- 流程箭头若表达真实流程关系，应保留可理解的流程结构；
- 柱形图的柱长若承载数据，不应仅退化为不可修改的装饰图片；
- 饼图的扇区比例若承载数据，不应仅保留为无法修改比例的静态图像。

## 11.3 不要求 Atomic Editability

默认不要求：

- 每条装饰线独立成层；
- 每个背景粒子独立成层；
- 每个复杂插画内部零件全部拆开；
- 每个工程视觉细节都成为独立对象。

原则：

> **Useful editability is more important than exhaustive decomposition.**

---

# 12. Step 10 — Single-Page Four Hard Gates

Native Text Visual Fit 完成后，每页必须同时通过四个 Hard Gates。

## 12.1 Gate A — Content Truth

要求：

- 最终应存在的正式语义文字正确；
- 最终应存在的已批准装饰文字正确；
- 数字正确；
- 单位正确；
- 日期正确；
- 正式名称和专有名称正确；
- 不存在由图像生成、Magic Layers 或恢复过程造成的内容错误；
- 不存在应永久丢弃的错字、乱码、幻觉文字重新进入页面。
- `exact_facts` 中的每一项均必须被验证，无论其最终以文字、图表、比例、几何或其他可验证形式呈现；不得因为 `exact_facts` 不是额外 TextBox 清单而跳过验证。

失败码：

```text
CONTENT_TRUTH_FAILED
```

## 12.2 Gate B — Semantic Fidelity

要求：

- 并列仍然是并列；
- 流程顺序正确；
- 层级关系正确；
- 因果关系未被改变；
- 组成关系未被改变；
- 语义分组没有因图层重建而被误解。

Stage 3 不允许通过结构整理或文字恢复制造新的：

- 因果；
- 流程；
- 层级；
- 时间顺序；
- 从属关系。

失败码：

```text
SEMANTIC_FIDELITY_FAILED
```

## 12.3 Gate C — Functional Editability

要求：

- 主要文字可编辑；
- 关键事实可修改；
- 主要语义对象达到实际使用需要的编辑粒度；
- 主要视觉对象可以进行必要调整；
- 页面可以继续用于真实业务修改，而不是只具有表面上的“可编辑”。

失败码：

```text
FUNCTIONAL_EDITABILITY_FAILED
```

## 12.4 Gate D — Visual Fidelity

Visual Fidelity 不要求 pixel-perfect。

要求保留：

- 主构图；
- 视觉重心；
- 主要对象；
- 主要色彩关系；
- 信息层级；
- Stage 2 已批准的总体设计意图；
- 最终恢复文字的可见字形位置、尺度和整体视觉关系达到可接受一致性。

允许：

- 极轻微位置变化；
- 合理换行差异；
- 轻微字体渲染差异；
- 少量非关键装饰变化；
- 不影响整体设计意图的重建差异。

不允许：

- 主构图明显改变；
- 视觉重心明显改变；
- 主要对象缺失；
- 色彩关系明显失真；
- 页面层级结构被破坏；
- 页面明显退化为另一种普通版式；
- 装饰文字因特殊处理而显著偏离原图，而普通文字恢复正常。

原则：

> **Preserve design intent, not every pixel.**

失败码：

```text
VISUAL_FIDELITY_FAILED
```

只有四个 Hard Gates 均 PASS，单页才成为：

```text
Validated Editable Single-Page PPTX
```

---

# 13. Step 11 — Local PPTX Merge Contract

本协议只定义 Local PPTX Merge 的输入、输出和验收契约，不规定具体代码实现。具体实现模块由独立工程实现。

## 13.1 输入

```text
Validated Editable Single-Page PPTX × N
+
deck_order: [slide_id_1, slide_id_2, ..., slide_id_N]
```

`deck_order` 是 Stage 3 / Deck 运行元数据，不是 Stage 2 第三个交付物。它必须与本次进入 Merge 的 validated single-page `slide_id` 集合严格一一对应：每个 ID 恰好出现一次，不得缺失、重复或出现未知 ID。页面重排只更新 `deck_order`，不得重编号既有 `slide_id`。

Local Merge 必须仅按 `deck_order` 执行，不得靠文件名、下载时间、目录排序、浏览器保存顺序或并行任务完成先后猜测页面顺序。若 `deck_order` 与输入单页集合不一致，必须在 Merge 前阻断并按 `DECK_MERGE_INTEGRITY_FAILED` 处理，不得边合并边猜测修复。

若 `deck_order` 发生变化，旧 Merged PPTX 与旧 Deck-Level Validation 结果立即 stale；只需按新列表重新 Local Merge 与 Deck-Level Validation，**不要求重新生成已验证单页 PPTX**，也不得因为纯页面重排重跑 Magic Layers / Native Text Visual Fit。

未通过单页四个 Hard Gates 的页面禁止进入 Merge。

## 13.2 必须保持

Local Merge 必须：

- 输出 slide 数量必须严格等于输入的 `Validated Editable Single-Page PPTX × N` 数量，禁止漏页、重复页或新增空白页；
- 保持 Stage 1 / Stage 2 已确定页面顺序；
- 保持统一页面尺寸与整套 Deck canvas invariant；
- 保持单页内对象的可编辑性；
- 保持原生文本为文本对象；
- 保持主要图形、媒体、层级关系和 z-order；
- 保持每页实际依赖的 OOXML package relationships 与相关 parts，包括所引用的 media、chart/workbook、hyperlink、embedded object、theme/layout/master 等（若存在）；
- 合并时正确重映射 relationship IDs、part names 与跨包引用，禁止只复制 slide XML 后留下悬空关系；
- 不重新设计页面；
- 不把页面整体栅格化；
- 不为了合并方便把页面退化成整页图片。

若单页尺寸冲突，说明 Deck canvas invariant 在更早阶段未被满足或被后续实现破坏：

```text
DECK_CANVAS_INVARIANT_FAILED
```

不得在 Merge 阶段另建第二套“页面尺寸冲突”状态。

若合并导致对象、文字、媒体/图表引用、relationship 或视觉结构明显损坏：

```text
DECK_MERGE_INTEGRITY_FAILED
```

## 13.3 输出

```text
Merged Editable PPTX
```

该文件必须继续执行 Deck-Level Validation，不能仅以“合并成功”作为完成标准。

---

# 14. Step 12 — Deck-Level Validation

对整套合并 PPTX 检查：

- slide 总数与 Merge 输入数量一致；
- 页面顺序；
- 页面尺寸；
- 每页单页 Hard Gates 是否在合并后仍成立；
- 标题层级一致性；
- 主要字体表现是否出现明显漂移；
- 重复母题是否出现明显不一致；
- 背景视觉语言是否保持家族性；
- 页面编号和固定元素是否一致；
- 整套演示文稿不存在因逐页重建或合并造成的明显风格漂移；
- 单页编辑能力没有因 Merge 被破坏。

Deck-Level Validation 只修正重建或合并造成的明显偏差，不重新进行视觉设计。

若单页分别通过，但整套出现标题层级、fallback 字体、固定元素或整体风格一致性问题，记录：

```text
DECK_LEVEL_VALIDATION_FAILED
```

恢复动作：

```text
定位受影响单页源
→ 在 Validated Single-Page PPTX 来源层修正
→ 重新执行该页 Four Hard Gates
→ 重新 Local Merge
→ 重新 Deck-Level Validation
```

不得默认直接在最终 Merged Deck 上打大规模补丁，因为那会使单页 Canonical Source 与最终 Deck 分叉。若针对同一 Deck-level 问题完成一次明确的单页源修正并重合并后，完全相同的问题仍在未发生其他条件变化的情况下重复出现，应保持 `DECK_LEVEL_VALIDATION_FAILED` 并停止自动循环，转为显式诊断。

全部通过后：

```text
Final Canonical Delivery Artifact
= Validated Merged Editable PPTX
```

---

# 15. Deck-scoped Font Fallback & PPTX Compatibility Validation

## 15.1 Deck-scoped Font Fallback

同一个目标字体在整套 Deck 中不可用时，fallback 选择必须是 **Deck-scoped**，不能逐页独立选择。

运行时维护一个最小映射：

```text
missing_font_family → chosen_fallback_font_family
```

同一缺失字体一旦选定 fallback，整套 Deck 必须复用；只有该 fallback 无法满足某个字符集或产生明确兼容问题时，才允许显式修订映射并重新验收所有受影响页面。

多页并行恢复时，不允许各 worker 独立决定 fallback。应在并行恢复前集中解析 Deck 所需字体，或由所有 worker 共享同一受控映射。

这不是新的 Stage 2 交付物，只是 Stage 3 运行级一致性约束。

## 15.2 PPTX Compatibility Validation

PPTX 在单页获取、文字恢复和最终合并后都不能以“文件能打开”作为完成标准。

应检查：

- 文字是否仍然可编辑；
- 关键数字和标签是否仍可修改；
- 主要对象是否保持合理结构；
- 页面尺寸是否正确；
- 字体是否发生明显替换；
- 文本是否异常换行；
- 元素是否错位；
- 主要色彩关系是否变化；
- 复杂图形是否发生不可接受的栅格化或结构丢失；
- 整体页面是否仍满足 Visual Fidelity；
- 页面是否仍满足 Functional Editability。

小型兼容性问题可以局部修正后重新验收；严重兼容性问题应返回其真正发生的 Stage 3 子步骤，不直接通过大规模补丁掩盖根因。

---

# 16. Failure & Recovery Logic

Stage 3 的失败必须先按根因分类，再决定动作。禁止只看到“失败”就重跑 Magic Layers 或返回 Stage 2。

| 类别 / 代码 | 根因 | 唯一默认动作 |
|---|---|---|
| `STAGE3_ENTRY_BLOCKED` / `MISSING_*` / `SLIDE_PAIRING_MISMATCH` / `DECK_CANVAS_INVARIANT_FAILED` | 入口交付/身份/画布问题 | 修正交付或运行级 invariant，重新 Entry Validation |
| `APPROVED_DECORATIVE_TEXT_UNRESOLVED` | Final Text Reconciliation 未闭合 | 补齐/确认 Stage 2 Final Content Truth，随后整页 Stage 3 lineage 重新开始 |
| `PRESERVED_GRAPHIC_CONTENT_INVALID` | 拟保护的 Logo/wordmark 内容本身错误或未批准 | 修正批准图形资产；使该页旧 Stage 3 派生产物失效后重新 Entry Validation；不使用结构性 `RETURN_TO_STAGE_2` |
| `RESTORE_BBOX_UNRESOLVED` | Final Content occurrence 与 Approved Render 无可靠位置对应 | 解决输入一致性/源区域依据；不得猜位置；修订上游输入后重新 Stage 3 lineage |
| 其余文字准备相关 code | discovery / cleanup / mapping / visual fit | 在 Stage 3 文字链对应步骤修正；非结构性 `RETURN_TO_STAGE_2` |
| `MAGIC_LAYERS_TOOL_UNAVAILABLE` / `MAGIC_LAYERS_EXECUTION_FAILED` | 工具/权限/会话/服务 | 修复能力或实现环境；不评价页面结构 |
| `RETRY_ONCE` | 单次偶发结构异常 | 同一 Text-Clean 输入最多合理重试一次 |
| `ASSISTED_CLEANUP_REQUIRED` | 局部结构需要补完 | 对同一明确问题完成一次辅助补完后重新 Assessment |
| `ASSISTED_CLEANUP_UNRESOLVED` | 同一局部问题补完后仍因工具/实现能力无法解决 | 停止重复补完，显式阻断；不误返 Stage 2 |
| `RETURN_TO_STAGE_2` | Stage 2 源页面本身结构不可重建 | 返回 Stage 2 处理结构根因 |
| `PPTX_ACQUISITION_FAILED` | 单页 PPTX 获取/下载阶段失败 | 先按 Host recovery contract 恢复、等待/重试或续跑同一 checkpoint；不重跑 Stage 2/Magic Layers |
| `PPTX_SOURCE_MISMATCH` | 下载/并发过程中页面 lineage 错配或无法确认来源 | 纠正 slide_id→Design→PPTX 映射，禁止继续文字恢复 |
| `GRAPHICS_FIRST_PPTX_INVALID` / `GRAPHICS_FIRST_TEXT_CONTAMINATION` | PPTX 中间态无效/文字污染 | 修复获取或中间态清理后再进入文字恢复 |
| `PRESERVED_GRAPHIC_REINTERPRETED_AS_TEXT` | 批准图形字标被错误转成普通文本 | 在 Graphics-first 中间态恢复/替换为已批准图形资产并重新校验；不得进入 Native Text Visual Fit，也不得结构性 `RETURN_TO_STAGE_2` |
| 四 Hard Gate failure code | 最终单页质量门失败 | 只回到对应 Stage 3 子步骤修正并重新验收 |
| `DECK_MERGE_INTEGRITY_FAILED` | Merge 输入顺序映射不合法，或 Merge 实现破坏页内对象/依赖 | 修正 `deck_order` 或 Merge 实现并重合并 |
| `DECK_LEVEL_VALIDATION_FAILED` | 单页均可接受但整套一致性失败 | 修正受影响单页源→重新单页验收→重新合并 |

最小原则：

- **结构性 No-op retry 仍禁止**：Magic Layers 结构结果仅按既有 `RETRY_ONCE` 规则处理；但 `WAIT_DOWNLOAD` acquisition 使用 `docs/codex-canva-bridge.md` 的有界恢复合同。查询/UI 临时异常先退避重试；最终 Download 后未知状态先按 10/20/30/45/60s 复查；只有独立确认的 terminal export failure 才可创建新的 numbered export，整轮最多 5 次真实 Download。普通 transient/recoverable failure 不因首次异常直接 STOP；
- 执行 Controller 采用 `RECOVER → WAIT/RETRY → DIAGNOSE → RUNTIME REPAIR → RESUME`；身份/lineage/provenance/授权不可信或恢复耗尽且继续可能产生重复副作用时才 Hard STOP；
- 已发布 Skill 在运行期是 **READ-ONLY PRODUCT**；Controller 可修 session/UI/network/file/finalizer/bind 运行现场，但不得热修改正式协议、production scripts、tests 或 manifest。若证据指向产品实现缺陷，记录 `IMPLEMENTATION_DEFECT_SUSPECTED` 并保存现场；
- 不无限重试 Magic Layers；
- 不因为文字识别问题重跑 Magic Layers；
- 不因为工具能力/下载实现不足错误返回 Stage 2；
- 不因为小型拆层问题重新生成页面；
- 不因为角标、品牌语等 decorative_text 采用特殊文字恢复分支；
- `RETURN_TO_STAGE_2` 只保留给**源页面结构本身**造成的不可重建；
- 上游 Render / Content Truth 改动后，下游派生产物全部失效，禁止混用新旧 lineage。

---

# 17. Stage 3 不负责的内容

Stage 3 不负责：

- 重新设计整套叙事；
- 重新决定页面任务；
- 重新定义语义关系；
- 新增未经批准的事实；
- 重新选择 Anchor；
- 重新生成 Style DNA；
- 为追求可编辑性而主动降低 Stage 2 已批准设计质量；
- 追求无实际价值的原子级拆层；
- 把普通 Magic Layers 误差当作 Stage 2 失败；
- 用 OCR、vision 或 Canva 文字覆盖 Stage 2 Final Content Truth。

---

# 18. 最终验收

Stage 3 完成必须同时满足：

```text
[ ] 每页 Text-Clean Integrity Check 已通过
[ ] 每页 Magic Layers 结构重建已通过 Assessment
[ ] 每页 Graphics-first PPTX 有效
[ ] 每页 Native Text Visual Fit 已完成
[ ] 所有页面通过 Content Truth Gate
[ ] 所有页面通过 Semantic Fidelity Gate
[ ] 所有页面通过 Functional Editability Gate
[ ] 所有页面通过 Visual Fidelity Gate
[ ] 只有 Validated Single-Page PPTX 进入 Local Merge
[ ] Local Merge 未破坏页面对象和编辑能力
[ ] Deck-Level Validation 已完成
[ ] 最终 PPTX 具有实际可编辑和继续使用价值
```

---

# 19. 最终原则

```text
Preserve truth.
Preserve semantic relations.
Preserve design intent.
Clean text before Canva.
Use Magic Layers for structural recovery.
Restore intended text as native PowerPoint text.
Recover useful, not atomic, editability.
Validate every single page before merging.
Treat the validated merged PPTX as the final canonical artifact.
Return upstream only when the upstream design is the true cause.
```

中文：

> **保持内容真值和真实语义关系，保持 Stage 2 已批准设计意图；Canva 前清理文字，Magic Layers 负责结构，PPTX 端恢复原生文字；追求功能性而非原子级可编辑；单页先验证再合并，最终以通过整套验收的可编辑 PPTX 为 Canonical Artifact；只有上游设计本身构成根因时才返回上游。**

---

# Part II. Current Implementation Notes

> 本部分记录当前 Canva / Magic Layers / 下载和装配能力的实现情况。  
> 这些内容属于可变实现参数，不属于前述长期语义规则。  
> 工具能力变化后优先更新本部分，不轻易修改 Part I。

---

# 20. 当前 Magic Layers 入口

当前工作流使用 Text-Clean Render 作为 Magic Layers 正式输入。

```text
Approved Slide Render
→ Stage 3 Text Preparation
→ Text-Clean Render
→ Magic Layers
```

当前 Stage 2 采用的 Strict 2D + Non-Photographic Rendering 方向与 Magic Layers 对 graphic design / illustration / stylised flat visual 的结构恢复方向相容。

---

# 21. 当前单页 PPTX 获取

历史现场曾真实验证以下行为链；RC16.2 对 Host acquisition contract 的本轮修改仍需按 manifest 状态执行 live revalidation 后才能提升为稳定发布：

```text
Magic Layers Single-Page Design
→ Canva 网页自动化
→ PPTX 下载
```

Browser UI 动作仍由 Codex Host 提供；Canonical 包内提供的是 request/intent/evidence/finalizer/bind 的本地契约，不把 Host UI 冒充为独立脚本 API。若 Host 能力缺失或执行失败，使用 `PPTX_ACQUISITION_FAILED` 并按 recovery-first 语义处理。

主路线不依赖：

```text
Resize to Presentation
```

也不以 Canva REST API 作为默认导出主路线。

下载自动化属于实现模块，可以独立替换；只要满足本协议 `Graphics-first PPTX` 输入契约，不影响 Part I。

---

# 22. 当前文字恢复位置

最终文字不在 Canva 内完成真值修复。

当前正式顺序：

```text
Graphics-first PPTX
+
Text Manifest
→ Native Text Visual Fit
→ Validated Editable Single-Page PPTX
```

因此 Canva Design 是 Intermediate Structural Source，而不是最终 Canonical Editable Source。

---

# 23. 当前多页装配策略

当前正式策略不是 Canva 内主 Deck Assembly，而是：

```text
Validated Editable Single-Page PPTX × N
→ Local PPTX Merge
→ Deck-Level Validation
```

Local PPTX Merge 的代码实现不写死在本协议中，只要满足第 13 节 Merge Contract 即可。

---

# 24. 当前实现参数原则

以下参数不固定写死在长期协议中：

- Magic Layers 支持格式；
- 最大尺寸限制；
- Canva 当前自动化接口集合；
- 网页自动化下载具体脚本；
- 单次处理页面数量；
- Canva 对某类元素的拆层表现；
- Local PPTX Merge 的具体代码库与实现语言。

执行时应以当前工具实际能力为准，但不得改变 Part I 的输入输出契约和四个 Hard Gates。

---

# 25. 版本维护原则

如果后续 Canva、PowerPoint 或自动化工具能力变化：

- 优先只更新 `Part II. Current Implementation Notes`；
- Magic Layers、下载和 Merge 的具体实现可以替换；
- 不因工具变化轻易改变 Stage 2 → Stage 3 两个核心交付物；
- 不改变 Content Truth、Semantic Fidelity、Functional Editability、Visual Fidelity 四个 Hard Gates；
- 不改变“文字真值与结构重建解耦”的主原则，除非后续真实测试证明有必要。

只有当以下内容发生根本变化时，才考虑修改 Part I：

- Stage 3 业务目标；
- 最终 Canonical Delivery Artifact；
- Functional Editability 定义；
- 四个 Hard Gates；
- Stage 3 职责边界；
- Return-to-Stage-2 根本原则。


## Runtime dispatch: Magic acquisition and restoration boundaries

**Magic Layer 分支:** Magic Layers receives the Formal Text-Clean Render; Canva restores structure only. For `WAIT_DOWNLOAD`, use the recovery-first Host contract in `docs/codex-canva-bridge.md`: trusted ACCEPT identity -> bounded query/UI recovery -> persisted `INTENT_LOCKED` -> one final Download for that acquisition -> bounded post-click observation, including a fresh explicit same-operation recovery affordance when safely available -> exact browser History/file proof -> unchanged finalizer -> bind. Query/UI retry uses 2/5/10/15/20s; after intent, observation uses 10/20/30/45/60s and never unlocks another click. Only independently confirmed terminal export failure may create the next numbered acquisition; the round permits at most five real Download clicks, while each new export record gets a fresh bounded local retry budget. Unknown, in-progress or completed download never authorizes another click. Browser session/network/UI problems are repaired and resumed from the same checkpoint where safe; identity/provenance/auth ambiguity is a Hard STOP. The executing Agent may repair runtime/session state but the installed Skill is a **READ-ONLY PRODUCT** and must not be hot-modified; suspected product defects are reported as `IMPLEMENTATION_DEFECT_SUSPECTED`. Never guess a conventional Downloads path or the newest file: establish the actual browser profile/configuration and matching completed record. Do not substitute Resize or REST API. Finalizer/bind failure reuses the same exact downloaded bytes and never triggers Magic Layers or a new Download. During text restoration, references 06/07 retain the original <=5-source-pixel path and add verified same-framing uniform adaptation for larger unit/size differences; use the shared content rectangle for graphics, native-text geometry and glyph size. Original downloads, approved canvas and source bindings remain immutable. Acquisition prefers the documented same-call DOM/download-event candidate when supported; the original UI/observation route remains a bounded fallback. After intent lock every uncertain result permits observation/recovery only, never a repeated ordinary Download. Only single-page PPTX files sealed after all four Hard Gates enter `scripts/merge_pptx.py`; Merge remains unchanged.
