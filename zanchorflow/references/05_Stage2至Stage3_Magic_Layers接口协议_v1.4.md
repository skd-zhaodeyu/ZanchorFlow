# Stage 2 → Stage 3 Magic Layers 接口协议 v1.4
## Magic Layers Reconstruction Interface Contract

**适用范围：** 定义 Stage 2 视觉生成结果如何交付 Stage 3，并通过 Canva Magic Layers 转换为可编辑分层设计。  
**阶段定位：** 本协议只定义 Stage 2 与 Stage 3 之间的交付边界，不定义 Stage 3 内部完整重建流程。  
**核心目标：** 在不牺牲 Stage 2 语义质量与视觉质量的前提下，提高最终页面进入 Magic Layers 后的可编辑化质量与后续整理效率。

---

# 1. 核心原则

Stage 2 的首要任务仍然是生成优秀的 PPT 页面视觉结果。

Stage 3 的任务是把已经确认的扁平页面图像转换为具有实际使用价值的可编辑设计；文字预清除、Magic Layers 结构恢复和最终原生文字恢复均属于 Stage 3 内部职责。

二者关系为：

```text
Stage 2
高质量视觉设计
        ↓
Stage 2 → Stage 3 Interface
交付最终页面图像与内容真值
        ↓
Stage 3 Internal Preparation
Approved Slide Render → Text-Clean Render
        ↓
Magic Layers
Text-Clean Render → 可编辑视觉结构
        ↓
Stage 3 Text Restoration + Validation
获得功能性可编辑 PPTX
```

本接口遵循：

> **Editability is a downstream optimization objective, not the primary design objective.**

中文：

> **可编辑性是下游优化目标，不得反向取代 Stage 2 的语义表达与视觉质量目标。**

特别说明：

- `Approved Slide Render` 是 Stage 2 候选经过资格审核 PASS 后形成的正式交付物和 Stage 3 的视觉保真基准；它不是可由文件路径直接登记获得的状态；
- `Text-Clean Render` 是 Stage 3 内部派生工件，不是 Stage 2 第三个交付物；
- Magic Layers 的正式输入由 Stage 3 从 `Approved Slide Render` 派生，不要求 Stage 2 预先消字、分层或输出坐标。

# 2. Stage 2 → Stage 3 最小交付物

Stage 2 向 Stage 3 仍且仅交付两个核心对象。

## 2.1 Approved Slide Render

Stage 2 最终确认的单页 PPT 页面图像。

要求：

- 页面已经通过 Stage 2 Qualification Review，且当前 verdict = PASS；
- 一页对应一个独立图像；
- 默认优先使用 PNG 作为中间格式；
- 应保持完整页面，不裁掉任何最终批准内容；
- 应足以作为 Stage 3 的视觉保真、文字几何测量和 Text-Clean 派生基准。

本接口不要求 Stage 2 额外输出：

- Background PNG；
- Foreground PNG；
- Mask；
- Layer JSON；
- Object Coordinates；
- Background ID；
- SVG Manifest；
- 元素层级树；
- Text Manifest；
- Removal Inventory；
- Text-Clean Render；
- Magic Layers 预测图层结构。

原则：

> **Stage 2 delivers the approved visual result, not a manually pre-separated reconstruction package.**

### 2.1.1 Stable Page Set

Stage 2 正式生产开始时，应从**当前已批准的大纲**建立本次 Deck 的稳定页面集合和顺序。

若上游已有稳定页面 ID，直接复用；若没有，则在 Stage 2 run 建立时按当前批准页集合分配运行内唯一 `slide_id`（如 `S001`、`S002`…）。

`slide_id` 表示页面身份，页面顺序表示交付顺序，二者必须分离：

- 后续换序不得重新编号既有页面；
- 新增页面获得新 ID；
- 删除页面使其退出 current page set，但历史记录可以保留；
- Candidate、Review、Approved Render 和 Final Content Truth 均必须绑定明确 `slide_id`。

### 2.1.2 每页唯一 Current Approved Render

Stage 2 的 **Visual Production Complete** 条件为：

```text
对于 current page set 中每一个 slide_id：
current approved render 数量 == 1
```

`candidate`、`REVISE`、`REJECT`、`superseded`、调试图或历史生成图均不属于正式交付集合。

如果三页大纲仅有两页通过：

```text
Stage 2 Visual Production = INCOMPLETE
missing = 尚无 current approved render 的 slide_id
```

不得把失败候选或旧版本补进最终清单，也不得宣称“0 张通过”后又把所有候选一起作为正式结果展示。

### 2.1.3 正式用户展示与 Candidate History 分离

Stage 2 `Visual Production Complete` 后的默认用户展示只包含：

> **Current Approved Slides**

并严格按 current page order 展示每页唯一 current approved render。

只有用户明确要求查看失败版本、历史版本或调试过程时，才展示 `REVISE / REJECT / superseded` Candidate History。

工程追溯历史不得污染正式交付。

### 2.1.4 Anchor 页面进入正式集合的条件

如果用户在真实 Deck 页面语义和正式画布下，从“实际采用的页面/封面版本”候选中选择某一方案作为 Anchor，并且最低必要 Qualification Review 不存在 Hard Failure，则该候选按《PPT视觉探索与Anchor延续协议》成为对应 `slide_id` 的 current approved render；该用户选择记录为 PASS 来源。

如果用户只是选择 style / Anchor，而未明确选择实际采用的页面版本，或 Anchor 只是 style mockup / 风格样张，则只提供 Style DNA，不进入 Approved Render Set。

### 2.1.5 Formal Display Set 与用户视觉确认关口

`Visual Production Complete` 后，Stage 2 必须从可信运行状态确定性构造 **Stage 2 Formal Display Set**：

```text
current Stable Page Order
+
每页唯一 current Approved Slide Render
→
Stage 2 Formal Display Set
```

正式展示不得从最近一次生图工具输出、工作目录扫描、Candidate History、生成先后顺序或文件名推断。已经锁定且本轮未重新生成的 Anchor/封面，只要仍是该页 current Approved Render，就必须出现在正式展示中；`REVISE / REJECT / superseded / debug / historical candidate` 不得进入正式展示。

宿主界面可能已经在历史对话中显示过 Candidate 工具卡片，Skill 不负责删除既有 UI 历史；本协议约束的是 Agent 主动形成的正式审核展示、阶段性正式输出和最终汇总，它们只能消费 current authoritative set。

正式展示完成后必须暂停在 **Human Visual Approval Gate**。Agent 的 Qualification PASS 只表示页面达到自动资格门槛，不等于用户已批准整套视觉结果。用户可：

- 明确批准当前整套页面，进入后续 Stage 2 内容交接并允许 Stage 3；
- 指定一个或多个 `slide_id` 修改，仅重新打开这些页面，其他 current PASS 页面继续保持有效；修改页重新 PASS 后重新构造并展示完整 Formal Display Set，再次等待用户确认。

用户批准必须绑定被展示的具体集合：

```text
display_set_fingerprint
= SHA-256(
    current page order
    + 每个 slide_id
    + 对应 current Approved Render SHA-256
  )
```

任一页 current Approved Render、页面顺序或 current page set 发生变化，旧用户视觉批准立即 stale。不得使用简单 `visual_approved = true` 跨版本复用。

在 current Formal Display Set 尚未获得用户明确批准时：

```text
AWAITING_USER_VISUAL_APPROVAL
```

Stage 3 Text Preparation / Text-Clean / Magic Layers 均不得开始。

### 2.1.6 Stage 2 → Stage 3 Handoff Complete

`Visual Production Complete` 只说明所有 current 页面都有唯一 current approved render。正式声明 Stage 2 → Stage 3 交付完成，还必须对 current page set 中每一页同时具备：

```text
1 × current Approved Slide Render
+
1 × current Stage 2 Final Content Truth
+
Final Text Reconciliation complete
```

因此图片全部通过不等于整个 Stage 2 → Stage 3 接口已经完成；二者状态不得混用。

---

## 2.2 Stage 2 Final Content Truth

Stage 2 页面正式确认后，记录该页面最终**应以文字内容身份继续存在的全部有效文字**和需要精确保持的事实信息。

建议继续使用最小结构：

```yaml
stage3_content_truth:
  slide_id:
  meaningful_text:
  exact_facts:
```

`slide_id` 在同一 Deck 内必须唯一，并作为 Stage 3 全部派生产物的页面身份键；不得依赖文件名或下载先后顺序猜测页面归属。

`slide_id` 应来自 Stage 2 run 开始时已经建立的 Stable Page Set；不得等到文件下载、Approved Render 形成或 Stage 3 入口时再根据文件名和处理顺序猜测页面身份。Approved Slide Render / Final Content Truth 只消费该稳定身份，不重新编号。

### `meaningful_text`

记录最终 Approved Slide 中应以文字内容身份继续存在的全部有效文字，包括：

- 标题；
- 正文；
- 标签；
- 图示文字；
- 流程节点文字；
- 关键说明；
- Stage 2 在语义范围内合法展开后形成的新表达；
- 已批准的角标；
- 品牌语；
- 合法 slogan；
- 装饰性短句及其他明确应保留的设计文字。

这里的“装饰性”只描述文字在设计中的角色，不意味着它可以脱离 Content Truth，也不意味着 Stage 3 必须将其保留为图形。

### 图形化文字 occurrence

若某个**承担准确内容职责的文字/数字本身也是已批准页面的重要视觉构图**，例如超大纪念数字、定制字形、与圆环/插画/留白共同形成主视觉的 Graphic Typography，则它仍属于一个独立的 `meaningful_text` occurrence。即使相同内容已经在标题、正文或 `exact_facts` 中出现，也不得因为字符串重复而省略该可见 occurrence。

Stage 2 只负责确认：

> **这个可见 occurrence 的内容是否应当存在且是否正确。**

Stage 2 不在 Content Truth 中决定其最终采用普通 TextBox 还是图形化字形表示；`native_text / graphic_typography / approved_graphic_asset` 属于 Stage 3 的 Representation Role。Content Truth 与 Representation Method 必须分离。

图形资产：已批准的不可拆 Logo / wordmark，以及按设计上下文承担对象身份或艺术表达的字形、图标字符、文稿笔迹和字形纹理，由 Stage 3 的 `approved_graphic_asset / preserve_as_graphic` 管理，不因能读出字符而自动新增 `meaningful_text`。其中品牌字样或指定文字仍按准确内容核验；没有独立准确文案职责的图形按身份核验，见协议 07 §6.3.2。图形描述不冒充文字真值，整页批准不自动确认任意新文案。混合对象中的阅读文字单独进入 Truth；相同字样在其他位置承担文字职责时仍为独立 occurrence。

### `exact_facts`

记录必须精确保持的信息，例如：

- 数字；
- 单位；
- 百分比；
- 日期；
- 专有名称；
- 正式名称；
- 精确数据表达；
- 不允许被近义改写的关键事实。

### `meaningful_text` 的 occurrence 规则

`meaningful_text` 不是去重后的字符串集合。若同一句合法文字在同一页面多个位置分别出现，必须保留每一次可见 occurrence；不得因为字符串相同而只保留一份。

Stage 3 可以使用 occurrence index / `truth_ref` 区分这些重复出现项。字符串相同不代表同一个文字对象。

### `exact_facts` 与可见文字 occurrence 的关系

`exact_facts` 是精确性约束，不是额外的文字对象生成清单。一个数字、单位或正式名称只有在 `meaningful_text` 中存在对应可见 occurrence 时，才生成/恢复相应文本对象；不得因为同一内容同时出现在 `exact_facts` 中而重复创建 TextBox。

`Stage 2 Final Content Truth` 的作用为：

> **作为 Stage 3 派生 Intended Text Set / Text Manifest、恢复原生文字并执行最终 Content Truth Gate 的内容权威。**

其来源必须是 Stage 2 已确认的最终文字计划、语义计划及用户批准的内容调整，而不是从最终页面图像反向 OCR、识别或猜测得到。

如果页面图像中的文字、数字或名称与 `Stage 2 Final Content Truth` 不一致，应以 Content Truth 作为 Stage 3 内容真值，不得把图像生成错误反向写入真值。

它不是：

- 页面坐标说明；
- 图层说明；
- 布局 JSON；
- 样式 Manifest；
- Stage 2 视觉方案的重复描述。

## 2.3 Stage 2 Final Text Reconciliation

`Approved Slide Render` 确认后、正式交付 Stage 3 前，应做一次轻量 Final Text Reconciliation，用于保证 `Stage 2 Final Content Truth` 真正覆盖已批准页面中最终应保留的文字。

该步骤只解决：

> **最终批准页面里哪些文字应继续存在。**

若生图过程中出现角标、品牌语、slogan 或其他设计文字：

```text
Approved Slide Render 中发现候选文字
        ↓
结合 Stage 2 已确认设计上下文判断
        ↓
应以准确文字身份保留 → 写入 meaningful_text
应按已批准图形身份保留 → 沿用设计资产依据，由 Stage 3 现有清单管理
不应保留的阅读文字 / 错字 / 乱码 / 幻觉文案 → 不写入 Content Truth
```

OCR / vision 可以辅助发现候选位置和可见文字，但不得自动把其识别结果升级为 Content Truth。`Approved Slide Render` 被整体批准，也不等于其中每一条 imagegen 自发字符串都自动获得内容真值地位；候选装饰文字仍必须能由已确认的设计意图/上下文支持。

Final Text Reconciliation 还必须检查**承担准确内容职责、构图关键的字形**是否属于已批准设计。若它的内容正确、设计意图明确且最终应继续存在，则应作为独立 `meaningful_text` occurrence 记录；不得因为它“像图形”而从 Content Truth 漏掉。反过来，若这种大尺度字形内容错误或未经批准，又已经成为主构图的一部分，则必须在 Stage 2 修正源视觉，不得把“删掉一个主视觉后留下巨大空洞”的责任推给 Stage 3。

反向同样成立：ImageGen 中出现局部错字、乱码、非核心收束文案或可局部清除的多余文字，**本身不应成为 Stage 2 反复重生整页的理由**。只要这些 Raster text 不构成核心语义主张、不改变页面关系、不成为删除后必然破坏构图的主体元素，允许当前视觉页面保持 Approved，并由 Stage 3 按 Content Truth 执行 `remove_and_restore / remove_and_drop`。

还必须检查 Render 与 Truth 是否能同时成立：被拒绝的文字若只是局部噪声，可由 Stage 3 `remove_and_drop`；但被拒绝的文字若已成为主构图或视觉平衡的重要组成，直接删除会必然显著改变已批准设计，则该页面尚不能作为 Stage 3 正式交付。应在 Stage 2 当前页先消除/替换该未批准内容并重新完成视觉验收与 Final Text Reconciliation。不得把这种 Render / Truth 内部矛盾推给 Stage 3。

该步骤不新增第三个交付物。

# 3. 为什么必须使用 Final Content Truth

Stage 1 只定义页面语义范围和语义不变量。

Stage 2 被允许在该范围内进行：

- 展开；
- 改写；
- 标签化；
- 重组；
- 数据表达；
- 视觉化解释。

因此 Stage 3 不能仅依赖 Stage 1 大纲恢复页面文字。

最终页面中可能存在 Stage 1 未逐字记录、但经过 Stage 2 合法生成的表达。

所以 Stage 3 的内容校核基准应当是：

```text
Stage 2 Final Content Truth
```

而不是简单回退到 Stage 1 原始措辞。

---

# 4. Functional Editability

Stage 3 的目标不是 Atomic Editability，而是 Functional Editability。

## 4.1 Functional Editability

最终设计应优先保证：

- 标题可编辑；
- 正文可编辑；
- 数字、单位和标签可编辑；
- 关键文本事实可修改；
- 主要视觉对象可以移动、缩放或替换；
- 承担核心语义或定量信息的主要对象，应具备与其实际修改需求相匹配的编辑粒度；
- 主要内容组之间可以重新调整；
- 背景与主要前景内容具有基本独立性；
- 页面可以继续用于实际汇报修改和复用。

## 4.2 不要求 Atomic Editability

默认不要求：

- 每一条装饰线独立可编辑；
- 每一个背景粒子独立成层；
- 每一个复杂插画内部零件全部拆散；
- 每一个工程图细节独立成为 PPT/Canva 原子对象。

例如，一个复杂二维工业插画在不承担需要独立修改的核心语义或定量结构时，可以作为整体可编辑视觉对象存在，只要其文字、数据和主要页面结构仍具有实际编辑价值。

原则：

> **Useful editability is more important than exhaustive decomposition.**

---

# 5. Layer Separability

Layer Separability 指主要视觉对象之间具有足够清晰的视觉边界，使后续 Magic Layers 更容易恢复合理的可编辑结构。

它是：

> **Soft Downstream Preference**

不是 Stage 2 的硬性视觉约束。

时间位置：`Layer Separability` 是本接口中唯一需要在 Stage 2 生成与方案选优阶段提前可见的下游软偏好；其余交付规则在页面通过 Stage 2 最终验收后执行。

---

# 6. Layer Separability 的使用原则

当多个设计方案在以下方面基本同等成立时：

- Semantic Integrity；
- Information Clarity；
- Visual Quality；
- Anchor / Style DNA Consistency；

可以优先选择主要视觉对象边界更清晰、更利于后续编辑化重建的方案。

可以适度鼓励：

- 文字与复杂背景保持足够识别度；
- 主要对象边界清楚；
- 主插画形成相对完整视觉对象；
- 主要语义组之间能够辨识；
- 装饰元素尽量形成少数完整母题；
- 避免大量细碎元素无意义地相互缠绕；
- 避免文字被大量无关线条、纹理或噪点穿过。

但不得为了 Layer Separability 机械禁止：

- 元素重叠；
- 大型插画；
- 复杂系统图；
- 信息丰富的流程图；
- 不规则构图；
- 背景视觉母题；
- 图文融合；
- 大尺度几何关系；
- 合理透明度；
- 精细二维工程视觉。

原则：

> **Layer Separability must never force the design back into blank-background card layouts.**

---

# 7. Stage 2 优先级

Stage 2 不因 Stage 3 的存在改变自身主要优先级。

建议保持：

```text
Semantic Integrity
>
Information Clarity
>
Visual Quality
>
Style Continuity
>
Layer Separability
>
Reconstruction Convenience
```

当视觉质量与后续拆层便利发生明显冲突时，优先保证前者。

Stage 3 应服务于已经成立的视觉设计，而不是反过来主导 Stage 2。

---

# 8. Background Visual Language / Reusable Background Motif 的接口定位

Stage 2 中已有的背景视觉语言与 `Style DNA.background_motif` 复用逻辑保留，但不新增独立的 Background System 状态，也不作为 Stage 2 → Stage 3 的硬性交付格式。

它主要承担：

- 整套 PPT 的视觉家族性；
- 背景语言统一；
- 可复用视觉母题；
- 后续重复资产整理基础。

可以包含：

- 统一底色语言；
- 边角线条；
- 几何结构；
- 电力或行业线稿母题；
- 页脚语言；
- 装饰节点；
- 轻量背景纹样。

不同页面可以对背景母题进行：

- 移位；
- 镜像；
- 缩放；
- 裁切；
- 调整密度；
- 重新组合。

因此本接口不要求 Stage 2 输出固定的 BG-A / BG-B / BG-C 文件，也不要求提前将背景与前景物理分离。

Magic Layers 完成后，如发现某些背景母题频繁出现，可以在 Stage 3 再整理为共享可复用资产。

原则：

> **Background reuse is a visual-language and motif-reuse concept, not a new mandatory state or pre-separated file system.**

---

# 9. Magic Layers 实际结果优先于预判

本接口不建立复杂规则预测某一页面是否一定能够被 Magic Layers 正确拆层。

真实处理结果优先于主观推测。

Stage 3 内部实际路径为：

```text
Approved Slide Render
        ↓
Stage 3 Text Preparation
        ↓
Text-Clean Integrity Check
        ↓
Text-Clean Render
        ↓
Magic Layers
        ↓
拆层质量良好
→ 继续 Stage 3

拆层质量一般但可整理
→ Stage 3 Cleanup

拆层严重失败，且根因明确来自源页面非文字核心视觉对象过度融合
→ 必要时返回 Stage 2 调整
```

不得仅因为理论上“可能不好拆”，提前限制一个语义和视觉都明显更优的方案。

文字识别质量不属于 Magic Layers 结构重建是否成功的主要判据，因为最终可编辑文字由 Stage 3 在 PPTX 端依据 Text Manifest 恢复。

# 10. 返回 Stage 2 的边界

Stage 3 默认自行处理文字清除、Magic Layers 普通拆层误差和原生文字恢复。

仅在以下情况可以考虑返回 Stage 2：

1. 源页面的**非文字核心视觉对象**存在大面积不可分离融合，导致 Magic Layers 无法形成具有实际编辑价值的结构；
2. 核心语义对象的几何关系在源图中本身不可分辨，Stage 3 无法在不重新设计页面的情况下恢复；
3. Text-Clean 处理后，源页面固有的视觉融合仍直接阻碍主要结构编辑，且 Stage 3 修复成本明显高于重新生成一个视觉质量相当的页面。

以下问题本身不构成返回 Stage 2 的理由：

- 中文错字；
- 乱码；
- 文字漏识别；
- 数字或单位识别错误；
- 合法角标或品牌语需要恢复；
- 少量图层需要合并；
- 某个复杂非关键插画被识别为一个整体对象；
- 背景装饰未完全拆散；
- 少量对象层级需要人工或自动整理。

原则：

> **只有 Stage 2 页面本身构成结构性重建失败根因时，才返回 Stage 2；文字问题优先由 Stage 3 文字链处理。**

# 11. Stage 3 入口检查

Stage 2 页面正式进入 Stage 3 前，确认：

```text
[ ] 页面已通过 Stage 2 Qualification Review，且 verdict = PASS
[ ] 当前 slide_id 属于 current Stable Page Set
[ ] 当前页恰好存在一个 current Approved Slide Render
[ ] 单页 Approved Slide Render 已确定
[ ] Stage 2 Final Content Truth 已生成
[ ] meaningful_text 已覆盖最终应继续存在的正式语义文字和已批准装饰文字
[ ] 构图关键且内容正确的 Graphic Typography 已作为独立 meaningful_text occurrence 记录；表示方式留给 Stage 3 决定
[ ] 精确数字、单位、名称和关键事实已记录
[ ] 已完成 Stage 2 Final Text Reconciliation
[ ] 没有为了提高可编辑性而明显牺牲视觉质量
[ ] 页面仍符合 Strict 2D + Non-Photographic Rendering 基线
[ ] Approved Slide Render 与 Stage 2 Final Content Truth 属于同一 slide_id / 页面身份
[ ] 当前页画布与整套 Deck 已固定的 canvas invariant 一致
[ ] 已从 current Stable Page Set 构造并向用户展示完整 Stage 2 Formal Display Set；未混入 REVISE / REJECT / superseded / historical Candidate
[ ] 当前 Stage 2 Formal Display Set 已获得用户明确视觉批准，且批准所绑定的 display_set_fingerprint 与当前集合一致
[ ] 若声明整套 Deck 的 Stage 2 → Stage 3 Handoff Complete，则 current page set 每页均同时具备唯一 current Approved Slide Render、current Final Content Truth，且 Final Text Reconciliation 已完成
```

其中 Deck canvas 在运行级必须先固定：用户明确比例/尺寸优先；否则沿用已有已批准 Deck；若仍无依据，默认 16:9。Stage 2 不因此新增第三个交付物。

页面身份错配或画布不一致时，Stage 3 必须阻断入口；不得把它误判为 Magic Layers 或结构重建失败。

Stage 3 再自行检查其派生的 Text-Clean Render 是否满足当前 Magic Layers 的实际输入要求。

# 12. 当前实现说明

当前 Stage 3 使用 Canva Magic Layers 作为视觉结构恢复能力。

Stage 2 默认优先交付 PNG，以减少文字、线条和几何图形的有损压缩；Stage 3 从 Approved Slide Render 派生 Text-Clean Render，再将 Text-Clean Render 送入 Magic Layers。

Magic Layers 的具体支持格式、尺寸上限和产品行为可能随 Canva 更新而变化。

因此：

> **这些属于可变实现参数，不属于本协议的长期语义规则。**

执行时应以当前 Canva Magic Layers 实际能力为准。

# 13. 最终接口结构

```text
STAGE 2
Visual Exploration + Rendering
        ↓

Current Approved Render Set
（每个 current slide_id 恰好一张）
+
Per-slide Stage 2 Final Content Truth
        ↓

STAGE 2 → STAGE 3
Interface Contract
        ↓

STAGE 3 INTERNAL PREPARATION
Text Manifest + Removal Inventory
        ↓
Text-Clean Render
        ↓

Canva Magic Layers
        ↓
Editable Visual Structure
        ↓

Graphics-first PPTX
        ↓
Native Text Restoration
        ↓
Validated Editable PPTX
```

本接口只规定 Stage 2 的交付边界；Text Manifest、Removal Inventory、Text-Clean Render、Graphics-first PPTX 和 Native Text Visual Fit 均属于 Stage 3 内部工件或步骤。

# 14. 最终原则

```text
Design quality first.
Deliver only current PASS renders.
Preserve final content truth.
Keep candidate history separate from formal delivery.
Prefer separable visual objects when quality is equal.
Use Magic Layers for structural recovery.
Pursue functional, not atomic, editability.
```

中文：

> **优先保证设计质量；Stage 2 正式交付只包含每页唯一的 current PASS 页面，失败候选与历史版本不得混入；保存 Stage 2 最终内容真值；在设计质量相当时优先选择更利于拆层的视觉表达；利用 Magic Layers 恢复视觉结构，由 Stage 3 恢复最终文字；追求功能性可编辑，而不是所有细节的原子级拆解。**

For the formal display and approved-render/Truth reconciliation prerequisite, read Reference 04 Runtime dispatch: Candidate review, formal display and handoff. Do not enter Stage 3 until its current visual approval and handoff are complete.
