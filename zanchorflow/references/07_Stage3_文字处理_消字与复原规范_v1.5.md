# Stage 3 — 文字处理（消字与复原）规范 v1.5

> 状态：正式冻结规范  
> 用途：Stage 3 文字处理专项执行规范  
> 适用对象：Approved Slide Render → Text-Clean Render → Magic Layers → Graphics-first PPTX → 原生文字恢复  
> 不包含：Canva 网页自动下载实现、Recraft、Qwen、Scene JSON、整页 SVG tracing、多页 Deck Assembly

---

# 0. 版本定位与继承关系

v1.1 在 v1.0 已验证主路线之上补充 **Graphic Typography（图形化文字）** 的表示角色与破坏性消字安全门。它不新增 Stage 2 交付物，不新增第四种 treatment，也不把 OCR / vision 提升为内容真值；修订只解决“内容正确但字形本身承担关键视觉构图”的 occurrence 被错误删除后难以恢复的问题。

正式规范继承并冻结以下必要修正：

1. 保留 `Text Manifest` 与 `Removal Inventory` 分离；
2. 保留 `remove_and_restore / remove_and_drop / preserve_as_graphic` 三种 treatment；
3. 明确**合法角标、品牌语、slogan、装饰性短句只要最终应存在且可编辑，就必须进入 Text Manifest 并恢复**；
4. `semantic_text` 与 `decorative_text` 只描述角色，不得决定不同恢复算法；
5. 所有 `remove_and_restore` 统一采用同一套 **Native Text Visual Fit**；
6. 原图测量对象明确为“可见字形视觉包络”，而不是假定存在的原始 TextBox 边界；
7. 补清字距、基线、文本框 margin、混合样式顺序、画布映射与字体不嵌入规则；
8. 继续禁止 OCR / vision / Canva 文字成为最终内容真值。

---

# 1. 目标

文字处理链的目标是：

> 在进入 Canva/Magic Layers 前，把所有需要由最终文字系统接管的文字从图形重建输入中清除；错误、乱码和幻觉文字永久丢弃；最终应存在的语义文字和合法装饰文字，在 Graphics-first PPTX 中统一恢复为正确、原生、可编辑的 PowerPoint 文本。

目标主链：

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
Text-only Cleanup
        ↓
Residual Text Check
+
Non-text Preservation Check
        ↓
Text-Clean Render
        ↓
Magic Layers
        ↓
Graphics-first PPTX
        ↓
Native Text Visual Fit
        ↓
Validated Editable PPTX
```

---

# 2. Stage 2 → Stage 3 数据契约

Stage 2 仍只交付：

```text
Approved Slide Render
+
Stage 2 Final Content Truth
```

不得新增第三个 Stage 2 强制交付物。

`Text Manifest`、`Removal Inventory`、Text-Clean Render 均由 Stage 3 内部生成。

## 2.1 Stage 2 Final Content Truth 的覆盖范围

正式流程中，`Stage 2 Final Content Truth` 应覆盖最终 Approved Slide 中**应以文字内容身份继续存在的全部有效文字**，包括：

- 标题、正文、标签、流程节点、数据、单位等正式语义文字；
- 已批准的角标、品牌语、合法 slogan、装饰性短句等最终设计文字。

这只是明确既有 `meaningful_text` 的覆盖范围，不增加新文件或新接口。

### 2.1.1 occurrence 不得去重

`meaningful_text` 必须保留每一个合法可见 occurrence。若相同字符串在同页两个模块各出现一次，它们是两个恢复对象；不得因文本相同而去重。

Stage 3 为 occurrence 生成 `truth_ref` 时应使用稳定顺序（例如 `slide_id + Stage 2 truth occurrence ordinal`），不得按 OCR / vision 检测先后动态编号，否则同页重复文字在不同运行中可能错配。

### 2.1.2 `exact_facts` 不是第二份可见文字清单

`exact_facts` 只负责验证数字、单位、名称等内容必须精确，不因其存在而额外生成 Text Manifest element。可见文字 occurrence 仍以 `meaningful_text` 为准，避免同一数字因同时出现在两字段而被恢复两次。

## 2.2 历史测试页兼容

PNG1 / PNG2 / PNG3 等历史页面若缺失装饰文字真值记录，可做一次性回填：

```text
Approved Slide Render 中发现候选装饰文字
→ OCR / vision / 原图观察仅提供候选
→ 人工或既有设计上下文确认
→ Approved Design Backfill
→ 进入 Intended Text Set
```

OCR / vision 本身不得直接升级为最终真值。

---

# 3. Intended Text Set

定义：

```text
Intended Text Set
=
Stage 2 Final Content Truth
```

在正式流程中，已批准的角标、品牌语、合法 slogan 与装饰性短句已经属于 `Stage 2 Final Content Truth.meaningful_text`，不得再建立与 Content Truth 并列的第二常规真值源。

仅对 PNG1 / PNG2 / PNG3 等历史页面，若旧数据契约漏记已批准装饰文字，允许一次性：

```text
Legacy Intended Text Set
=
Stage 2 Final Content Truth
+
Approved Design Backfill
```

该 Backfill 只用于历史迁移，且必须经既有设计上下文或人工确认；OCR / vision 只能提供候选。

Intended Text Set 回答：

> 最终页面中哪些文字应该存在。

包括两种角色：

```text
semantic_text
decorative_text
```

## 3.1 semantic_text

包括：

- 标题；
- 正文；
- 标签；
- 流程节点；
- 数据；
- 单位；
- 百分比；
- 日期；
- 正式名称；
- 专有名称。

`content` 必须来自 Stage 2 Final Content Truth。

## 3.2 decorative_text

包括：

- 已批准角标；
- 品牌语；
- 合法 slogan；
- 装饰性短句；
- 页面辅助语句；
- 其他最终明确希望保留且可编辑的文字元素。

内容来源规则：

- 正式新流程：来自 `Stage 2 Final Content Truth.meaningful_text`；
- 历史缺失页：只允许经确认的 `approved_design_backfill_legacy`。

原则：

> 装饰作用不等于图形保留。

只要最终希望它仍为可编辑文字，就应进入 Text Manifest，并使用与普通文字完全相同的恢复算法。

## 3.3 Content Role 与 Representation Role 正交

`semantic_text / decorative_text` 只描述**内容角色**，不能决定该 occurrence 最终必须以普通 TextBox 还是图形字形存在。Stage 3 另使用 `representation_role` 描述**表现形式**：

```text
native_text
    最终由 Native Text Visual Fit 恢复为原生 PowerPoint 文本

graphic_typography
    内容属于 Final Content Truth，但字形本身承担关键视觉构图；
    通过严格证据门后以 preserve_as_graphic 保留

approved_graphic_asset
    已明确批准的 Logo / wordmark / 字形图标等不可拆图形资产
```

`Content Truth` 与 `Representation Method` 必须分离：同一字符串的两个 occurrence 可以一个是 `native_text`，另一个是 `graphic_typography`；不得因为字符串相同而去重，也不得由表现形式反向改变内容真值。

---

# 4. Text Manifest

## 4.1 职责

Text Manifest 只回答：

1. 最终 PPT 中应该存在什么文字；
2. 文字在 Approved Slide Render 中的视觉位置与视觉尺寸；
3. 应以什么样式恢复；
4. 最终是原生文字还是严格图形字标例外。

它不记录应永久丢弃的错字、乱码、幻觉文字。

Text Manifest 的构建不是“一次先验完成”，而是两步收敛：

```text
Stage 2 Final Content Truth
→ 初始化 content / occurrence / truth_ref

Full-page Text Discovery + Approved Render observation
→ 关联源区域
→ 补齐/确认 visual bbox 与样式
→ Finalize Text Manifest
```

因此不得要求在 Full-page Text Discovery 之前就凭空得到完整 bbox / style。

Text Manifest 中只允许：

```text
remove_and_restore
preserve_as_graphic   # 仅 approved_graphic_asset 或满足严格证据门的 graphic_typography
```

`remove_and_drop` 只属于 Removal Inventory，不得进入 Text Manifest。

## 4.2 最小结构

```yaml
text_manifest:
  schema_version: "1.0"
  slide_id:
  source_width:
  source_height:
  text_elements:
    - id:
      truth_ref:
      truth_source:
      content:
      text_role:
      representation_role:
      treatment:
      graphic_typography_evidence:
        content_verified:
        design_approved:
        composition_critical:
        native_text_substitution_material_loss:
      approved_graphic_evidence:
        content_verified:
        approval_ref:
      text_group_id:
      group_sequence:
      visual_bbox_normalized: [x, y, w, h]
      font_family:
      font_size_normalized:
      font_weight:
      font_style:
      color:
      alignment:
      vertical_alignment:
      rotation:
      line_height_ratio:
      letter_spacing_em:
      baseline_offset_ratio:
      opacity:
      paint_order:
```

## 4.3 truth_source

只允许：

```text
stage2_final_content_truth
approved_design_backfill_legacy
approved_graphic_asset   # 仅 treatment=preserve_as_graphic
```

其中：

- `stage2_final_content_truth`：所有正常可编辑文字以及 `graphic_typography` occurrence 的唯一正式内容来源；
- `approved_design_backfill_legacy`：只服务历史数据迁移；
- `approved_graphic_asset`：只允许显式批准的 Logo / wordmark / 字形图标等不可拆图形资产；它不是新的文字真值源，也不得用于普通角标、品牌语或 slogan。其批准依据只能来自用户明确指定的品牌/图形资产、当前任务中已明确批准的设计资产，或可追溯的既有设计上下文。

对于 `representation_role=graphic_typography`：`truth_ref` 必须指向 `Stage 2 Final Content Truth` 中对应的 `meaningful_text` occurrence，`content` 必须与该 occurrence 精确一致；不得使用 OCR / vision 识别结果作为真值。它虽然以图形形式保留，但内容权威仍是 Final Content Truth。

对于 `representation_role=approved_graphic_asset`：`truth_ref` 指向可追溯的批准资产/批准依据；`content` 若填写，只记录已经确认正确的可见 wordmark 字样用于审计，不参与 Native Text 恢复。若该对象只是纯图形且不存在 text-like glyph，则本来就不属于文字处理 Manifest。

禁止：

```text
ocr
vision_guess
observed_text
canva_text
```

作为最终文字内容来源。

## 4.4 visual_bbox_normalized

定义为：

> Approved Slide Render 中该文字**实际可见字形的视觉包络区域**。

不是：

> 假定存在但无法从 PNG 直接观测的原始 PPT TextBox 外框。

归一化：

```text
x_norm = x / source_width
y_norm = y / source_height
w_norm = w / source_width
h_norm = h / source_height
```

## 4.5 font_size_normalized

不得直接把 PNG 像素字号当作 PowerPoint point。

定义：

```text
font_size_normalized
=
estimated_visible_glyph_height_px / source_height
```

它是初始恢复尺度，不是最终固定点值。

## 4.6 混合样式文字

同一逻辑短语若存在明显样式变化，应拆成多个 element，不新增复杂 Rich Text 树。

例如：

```text
提升 35%
```

可拆为：

```yaml
- id: M021
  text_group_id: G007
  group_sequence: 1
  content: "提升"
  ...

- id: M022
  text_group_id: G007
  group_sequence: 2
  content: "35%"
  ...
```

---

# 5. Removal Inventory

## 5.1 职责

Removal Inventory 回答：

> 原始 Approved Slide Render 当前有哪些可见文字、错字、乱码、伪文字或 text-like glyph，以及它们在清除阶段如何处理。

它可以包含：

- 正确 semantic_text；
- 正确 decorative_text；
- 原图错字；
- 乱码；
- imagegen 自发但未批准的标语；
- 伪文字；
- 孤立字符；
- 残留扫描新发现的字符。

`observed_text` 没有最终真值地位。

## 5.2 最小结构

```yaml
removal_inventory:
  schema_version: "1.0"
  slide_id:
  items:
    - region_id:
      visual_bbox_normalized: [x, y, w, h]
      observed_text:
      detection_source:
      treatment:
      linked_manifest_ids: []
```

## 5.3 detection_source

允许：

```text
manifest_seed
full_page_vision
residual_scan
```

## 5.4 关联规则

Removal Inventory 与 Text Manifest 的对应优先级：

```text
空间区域 / visual bbox 对应
>
局部版式关系
>
字符串相似度
```

字符串只能辅助，禁止以：

```text
observed_text == content
```

作为唯一对应条件。

## 5.5 双向覆盖不变量

关联完整性必须双向成立：

```text
Removal → Manifest:
每个 remove_and_restore region 至少关联一个 Manifest ID

Manifest → Source:
每个 remove_and_restore Manifest element 必须关联至少一个 Approved Render 源区域，
并具有可解析 visual bbox
```

如果 Content Truth 中存在最终文字，但 Approved Render 中完全找不到该 occurrence 或无法建立位置依据：

```text
RESTORE_BBOX_UNRESOLVED
```

不得凭空猜位置，也不得直接进入文字恢复。

同一句文字出现多次时按 occurrence 分别建立 `truth_ref` / region link；不得按字符串合并。

## 5.6 项目符号与编号列表

PNG 只能证明“看见了某些符号/编号及其视觉位置”，不能单凭图像推断 PowerPoint 的自动列表语义。

默认规则：

- Content Truth 已明确保留的 `•`、`-`、`1.`、`①` 等可见标记，可作为普通可编辑文字/独立 element 恢复；
- **不得仅凭 PNG 自动转换成 PowerPoint automatic bullets / auto-numbering**；
- 只有上游 Content Truth / 明确用户要求已经定义列表语义和顺序时，才允许使用自动列表能力；
- 使用自动编号后必须验证不会发生重新编号、缩进漂移或跨页序号污染。

---

# 6. 三种且仅三种 treatment

```text
remove_and_restore
remove_and_drop
preserve_as_graphic
```

## 6.1 remove_and_restore

```text
原图中删除
→ 不交给 Canva 作为最终文字处理
→ 最终依据 Text Manifest 恢复为 PPT 原生可编辑文字
```

适用于绝大多数：

- semantic_text；
- decorative_text；
- 原图写错但最终有正确真值的文字。

## 6.2 remove_and_drop

```text
原图中删除
→ 最终不恢复
```

适用于：

- 未批准 imagegen 自发文字；
- 乱码；
- 幻觉标语；
- 无意义伪文字；
- 违背页面语义的额外字符。

## 6.3 preserve_as_graphic

```text
不作为普通文字删除
→ 不恢复为普通 PPT TextBox
→ 继续作为视觉图形存在
```

`preserve_as_graphic` 仍是窄例外，只允许两类：

1. `representation_role=approved_graphic_asset`：显式批准的 Logo / wordmark / 字形图标、文字与图形不可拆分的品牌资产等；
2. `representation_role=graphic_typography`：内容正确且已批准、字形本身承担关键视觉构图，普通 TextBox 替代会造成实质视觉损失的图形化文字/数字。

### 6.3.1 Graphic Typography 严格四条件

`graphic_typography` 只有在以下四项**同时为真**时才能 `preserve_as_graphic`：

```text
content_verified = true
AND
design_approved = true
AND
composition_critical = true
AND
native_text_substitution_material_loss = true
```

其中：

- `content_verified`：该可见 occurrence 的内容与 Stage 2 Final Content Truth 精确一致；
- `design_approved`：该字形作为当前 Approved Render 的视觉表现具有可追溯的批准/设计依据；
- `composition_critical`：删除该区域会实质破坏页面视觉重心、平衡、空间张力或主构图；
- `native_text_substitution_material_loss`：用普通 PowerPoint TextBox 替代会显著损失已批准的字形轮廓、倾斜/变形、尺度比例、特殊填充或其他关键字形视觉特征；与其他图形发生空间咬合可作为证据，但不是必要条件，独立排放的字形若其造型本身承担关键视觉表现，同样按替代损失判断。

任一条件缺失时不得把普通文字升级为 `graphic_typography`。特别强调：**大字号、装饰字体、渐变、粗体、位置醒目、看起来“像艺术字”都不是充分条件**；它们最多只是触发进一步判定的证据。

若拟保护的 Graphic Typography 内容与 Truth 不一致，记录：

```text
GRAPHIC_TYPOGRAPHY_CONTENT_INVALID
```

不得因为视觉效果好而保护错误内容。若错误字形已成为主构图，简单删除会造成巨大空洞或结构崩坏，应回到当前页源视觉纠正该内容后重新进入 Stage 3；不得让 Stage 3 以 `remove_and_drop` 强行挖掉主视觉。

### 6.3.2 Approved Graphic Asset

Logo / wordmark 等已批准图形资产进入白名单前必须同时满足：

```text
可见内容 / 品牌字样已经被确认正确
AND
存在可追溯 approval_ref
```

若该对象含错字、乱码、错误品牌字样或未经批准内容，记录：

```text
PRESERVED_GRAPHIC_CONTENT_INVALID
```

不得因为“像 Logo”就保护它。

以下都不是 `preserve_as_graphic` 的充分条件：

- 角标；
- 品牌语；
- slogan；
- 大字号；
- 装饰字体；
- 页面边角位置；
- 单纯颜色/渐变特殊；
- 单纯 OCR / vision 判断“像艺术字”。

---

# 7. Full-page Text Discovery

必须扫描整张 Approved Slide Render，而不是只扫描 Content Truth 已知区域。

检测目标：

- Intended Text；
- 错字；
- 乱码；
- imagegen 自发标语；
- 未批准角标；
- 多余标签；
- 数字 / 单位；
- 孤立字符；
- pseudo-text / text-like glyph。

检测策略允许偏向“不漏字”，但不能把普通图形当文字删除。

默认非文字包括：

- 箭头；
- 连接线；
- 电力符号；
- 图标；
- 波形；
- 齿轮；
- 卡片边框；
- 普通装饰短线；
- 非字符型几何纹理。

---

# 8. 分类规则

对每个检测区域先确认内容归属，再确认表现形式；不得仅凭“像文字/像艺术字”直接决定删除或保护。

```text
Q0. 是否存在明确 approved_graphic_asset 批准依据？
    ├─ YES 且内容正确 → preserve_as_graphic
    ├─ YES 但内容错误/未确认 → PRESERVED_GRAPHIC_CONTENT_INVALID
    └─ NO → Q1

Q1. 它是否属于 Intended Text Set / Final Content Truth 的某个 occurrence？
    ├─ YES → Q2
    └─ NO  → Q4

Q2. 是否同时满足 Graphic Typography 四条件？
    ├─ YES → representation_role=graphic_typography → preserve_as_graphic
    └─ NO  → Q3

Q3. 是否存在高破坏风险且 representation role 仍无法确定？
    ├─ YES → GRAPHIC_TYPOGRAPHY_UNRESOLVED（阻断，不默认删除）
    └─ NO  → representation_role=native_text → remove_and_restore

Q4. 是否存在已确认设计上下文的正面证据表明它可能是漏记的 approved decorative text？
    ├─ YES → APPROVED_DECORATIVE_TEXT_UNRESOLVED（回 Final Text Reconciliation）
    └─ NO  → Q5

Q5. 删除该非 Truth text-like region 是否会实质破坏主构图？
    ├─ YES → TEXT_TREATMENT_CONFLICT（源视觉先纠正，不能盲删）
    └─ NO  → remove_and_drop
```

## 8.1 Destructive Cleanup Risk Check

在任何 `remove_and_restore / remove_and_drop` 真正执行之前，对高影响 text-like region 执行 **Destructive Cleanup Risk Check**。以下任一现象可触发“高风险候选”，但都不能单独证明应保护：

- 占据显著页面面积；
- 与圆环、插画、背景、留白或其他图形深度耦合；
- 删除后可能造成明显视觉空洞或失衡；
- 字形轮廓本身承担主要视觉焦点；
- 普通 TextBox 很可能无法复现其造型。

高风险区域必须先得到确定的 Representation / Treatment 结论。若内容属于 Truth 但是否为 `graphic_typography` 仍无法确定，记录：

```text
GRAPHIC_TYPOGRAPHY_UNRESOLVED
```

并阻断 Text-only Cleanup。**高影响歧义默认 BLOCK，而不是默认 DELETE。**

`APPROVED_DECORATIVE_TEXT_UNRESOLVED` 仍保持窄触发：只有既有用户批准、当前任务设计记录、固定品牌/页脚规范或其他已确认设计上下文提供正面证据时，才说明 Content Truth 可能漏记；仅 OCR / vision 观察到额外字符串不构成该阻断条件。

---

# 9. Text-only Cleanup

## 9.1 输入

```text
Original Approved Slide Render
+
Finalized Text Manifest
+
Removal Inventory
+
Representation / Treatment Validation = PASS
```

Text Manifest 与 Removal Inventory 的 treatment / representation role 必须在 cleanup 前完成并封存为当前 Stage 3 Text Plan；不得先消字再事后决定哪些对象其实应该保留。

## 9.2 目标

一次全页语义级 text-only cleanup：

```text
删除：
- remove_and_restore
- remove_and_drop

保留：
- preserve_as_graphic 白名单
- 所有非文字视觉结构
```

必须保留：

- 图形；
- 箭头；
- 连接线；
- 图标；
- 边框；
- 填充；
- 插画；
- 背景；
- 颜色；
- 间距；
- 主构图。

只重建原文字遮挡的局部背景或图形。

禁止：

- 重新设计；
- 新增文字；
- 新增标语；
- 新增符号；
- 大面积无关重绘。

## 9.3 清除次数上限

最多：

```text
Pass 1：一次全页 Text-only Cleanup
+
Pass 2：至多一次残留区域局部补清
```

Pass 2 只能处理 Residual Scan 新发现的残留区域。

第二次后仍有明显未授权文字残留：

```text
RESIDUAL_TEXT_REMAINS
```

停止后续阶段。

---

# 10. Text-Clean Integrity Check

## 10.1 Residual Text Check

除经当前 Stage 3 Text Plan 明确授权的 `preserve_as_graphic`（approved graphic asset 或 Graphic Typography）外：

> 页面不应继续存在可见文字或 text-like glyph。

```text
PASS / FAIL
```

## 10.2 Non-text Preservation Check

对照 Original Approved Slide Render 检查：

- 箭头；
- 连接线；
- 边框；
- 图标；
- 圆环；
- 卡片；
- 插画主体；
- 关键背景纹理；
- 主要色彩关系；
- 关键间距；
- 主构图。

要求：

> 视觉和结构保持，不要求逐像素一致。

## 10.3 Text-Clean Canvas Registration

Text-Clean Render 必须与 Original Approved Slide Render 使用同一页面坐标基准。正式进入 Magic Layers 前必须满足：

- 输出画布保持 `source_width × source_height`；
- 全页 framing 与源图一致，页面边界和整体构图注册不变；
- 不得裁切、扩边、旋转或整体平移页面；
- 不得因为消字操作改变整页缩放比例或重新排版非文字对象。

若消字工具仅改变 raster 分辨率，但能够确认内容几何注册、宽高比和 framing 均未改变，可在形成正式 Text-Clean Render **之前**采用确定性的非生成式缩放归一回原 `source_width × source_height`；归一化不得再次调用生成式重绘。

若无法确认同画布注册，视为 Non-text Preservation 失败并使用：

```text
NON_TEXT_PRESERVATION_FAILED
```

阻断后续 Magic Layers，不得依赖后续 bbox 微调补偿整页坐标漂移。

## 10.4 Formal Text-Clean Render

只有：

```text
Residual Text Check = PASS
AND
Non-text Preservation Check = PASS
AND
Text-Clean Canvas Registration = PASS
```

才生成正式：

```text
Text-Clean Render
```

若 `preserve_as_graphic` 白名单为空，则同时满足真正的 Text-Free Render 定义；若存在批准的 Graphic Typography，则 Formal Text-Clean Render 可以继续包含这些字形，它们是已授权图形对象而非待恢复普通文字。

## 10.5 Stage 3 Formal Display Contract

Text-Clean 完成后的正式用户展示必须从当前可信运行状态确定性派生，不得扫描目录或复用生成历史。定义：

```text
Stage 3 Text-Clean Formal Display Set
= current Stable Page Order
+ 每页 current Text-Clean Render
```

正式展示必须严格按页序，仅包含每页 current Text-Clean Render。以下对象不得混入：

- Stage 2 `REVISE / REJECT / superseded / historical candidate`；
- 旧 Text-Clean Render；
- 调试图、临时图、失败清理图；
- 为凑齐页数而回退使用的旧 Approved Render。

若 current page set 中任一页尚无 current Text-Clean Render，则该正式集合为 `INCOMPLETE`，必须报告缺失 `slide_id`，不得使用历史候选补位。

本 Formal Display Set 是运行时派生视图，不新增 Stage 3 正式交付物、不复制图片、不改变 Text-Clean lineage。宿主 UI 已经显示过的历史工具卡片可以继续存在于聊天历史中，但 Agent 的正式阶段展示和汇总不得再次主动混入这些历史对象。

---

# 11. Text-Clean Render → Magic Layers

只有 Integrity Check 通过后才进入：

```text
Text-Clean Render
→ Magic Layers
→ Stage 3 总协议定义的单页 PPTX 获取能力
  （网页自动化行为链已验证，但脚本实现不随本规范提供）
→ Graphics-first PPTX
```

检查：

- 主要对象完整；
- 核心业务模块合理拆分；
- Visual Fidelity 无明显下降；
- Functional Editability 无明显下降。

若 Text-Clean 输入明显破坏拆层质量：

```text
TEXT_CLEAN_INPUT_UNSAFE
```

不得错误归因于 Stage 1 / Stage 2。

---

# 12. PPTX Native Text Visual Fit

## 12.1 统一原则

所有：

```text
treatment = remove_and_restore
```

无论：

- semantic_text；
- decorative_text；
- 标题；
- 正文；
- 数字；
- 角标；
- 品牌语；
- slogan；

**必须使用同一套 Native Text Visual Fit 算法。**

禁止因为 `text_role = decorative_text` 进入特殊恢复、图片恢复、艺术字重绘或其他独立路径。

`representation_role=graphic_typography` 与 `approved_graphic_asset` 不进入 Native Text Visual Fit 循环，也不得在其位置再叠加同内容普通 TextBox；它们已通过 `preserve_as_graphic` 在 Graphics-first 结构中保留。

## 12.2 恢复驱动

恢复循环必须：

```text
遍历 Text Manifest 中 treatment = remove_and_restore 的 element
→ 每个 element 恢复一次且只能恢复一次
```

Removal Inventory 只用于清除与审计，不得驱动最终恢复循环。

## 12.3 内容规则

最终文字只能来自：

```text
Text Manifest.content
```

禁止使用：

- Canva OCR；
- observed_text；
- Removal Inventory.observed_text；
- 模型重新改写；
- 为排版自动删字或摘要。

## 12.4 画布映射

Magic Layer 按总协议 9.1 分为原容差路径与受控等比例适配路径。批准目标、原下载和源指纹不可改写。Image Layer 保持其既有已验证内容矩形和 5 源像素 invariant，不通过 Magic 适配补救其映射失败。

原容差路径两轴分别 ≤5 源像素时，保存为目标 Deck 大小但不改变已有对象；文字仍使用目标矩形。受控适配须先完成 Graphics-first neutrality 并通过 framing、比例和对象预检，统一使用变换后的 content_rect：

```text
x = content_left + x_norm * content_width
y = content_top + y_norm * content_height
w = w_norm * content_width
h = h_norm * content_height
visible_glyph_height = font_size_normalized * content_height
```

font_size_normalized 只用于可见字形高度初值；字体、字距、基线的后续 Native Text Visual Fit 规则不变。不能只调整文本框位置而仍以整张目标页面高度拟合字形。Manifest 内容/geometry/style 不因画布单位换算而改写。

已知且可验证的内部 inset/letterbox 按既有内容矩形映射；不能推测未验证 inset 或以其隐藏尺寸冲突。新 Magic 适配只接受同 framing，不处理新增裁切或内容重排。

比例超过容差 → DECK_CANVAS_INVARIANT_FAILED；证据、对象支持或内容矩形不明 → CANVAS_MAPPING_UNRESOLVED。所有合法角标、品牌语及普通正文采用同一映射，继续通过既有文字和视觉验收。

## 12.5 Native Text Visual Fit 执行顺序

每个 `remove_and_restore` element 按以下顺序恢复：

```text
1. 固定 content，不允许改写
2. 将 visual_bbox_normalized 映射到 PPTX 内容画布
3. 创建原生 PowerPoint TextBox
4. 统一控制 TextBox 内部 margin
5. 应用 font_family / weight / style / color / alignment / rotation / opacity
6. 以原图可见字形高度为目标拟合 font size
7. 以原图可见字形宽度为目标拟合 letter spacing
8. 以原图上下边界与基线为目标调整 baseline / y-position
9. 必要时最小调整 TextBox x / y / width / height
10. 检查字形视觉包络与 Approved Slide Render 的对应区域
```

### 错误/漏字原图的 bbox 使用边界

`visual_bbox_normalized` 默认是最终文字恢复的重要视觉目标，但它来自 Approved Render 中**实际被画出来的字形**。因此，若 `observed_text` 与最终 `content` 在长度、行数或可见结构上存在明显差异（例如原图漏字、多字、整段截断），visual bbox 只作为初始位置/尺度证据，不再视为必须逐字形严格复现的最终宽度目标。

此时仍保持：

- content 绝对固定；
- 原区域的位置、层级、字号气质和局部版式关系优先保持；
- 允许在第 9 步范围内做最小 TextBox 几何调整；
- 不得通过极端压缩字号或字距强行塞入错误文本留下的包络；
- 若正确 content 无法在不破坏局部布局的情况下合理恢复，使用既有 `TEXT_VISUAL_FIT_UNRESOLVED`，不得改写真值。

这不新增恢复分支，只限定 bbox 证据的权重。

对于已经按现有规则确定为 `native_text / remove_and_restore` 的文字，“可接受视觉一致性”不要求字形轮廓的像素级复刻。轻微字体渲染差异本身不得单独导致 `TEXT_VISUAL_FIT_UNRESOLVED`。例如：较大字号恢复后笔画略偏细或略偏粗；粗体、展示型或特殊字体的字面宽度、笔画重量或字形轮廓存在小幅差异；轻度艺术化字体无法完全复刻原图字形，但整体字号气质、位置、占位、层级和局部版式关系仍基本保持。只有这些差异已经造成明显视觉失真、层级变化、版式偏移、裁切、溢出或重叠时，才应视为 Visual Fit 未解决。

Visual Fit 必须是有限迭代过程。实现可以选择合适的局部优化方法，但必须声明有限终止条件；达到终止条件仍无法满足可接受视觉一致性时，记录：

```text
TEXT_VISUAL_FIT_UNRESOLVED
```

停止继续无界微调，不得通过改写 content 来“让它通过”。

## 12.6 文本框 margin

PNG 中无法知道原编辑器 TextBox 的隐藏 margin。

因此恢复时：

> 不反推原始 TextBox margin；统一采用受控 margin，再以**实际可见字形包络**作为视觉拟合目标。

这样避免正文和角标因不同默认 margin 产生系统性位置偏差。

## 12.7 字号拟合

`font_size_normalized` 只用于初值。

最终字号以：

> 实际渲染后可见字形高度是否接近原图 visual bbox 高度

为判断依据。

禁止：

```text
PNG 26 px → PowerPoint 26 pt
```

的机械转换。

## 12.8 字距拟合

字距是正式恢复参数，不再只作为可选美化项。

初始使用 Manifest 的：

```text
letter_spacing_em
```

再根据：

> 恢复后可见字形总宽度与原图 visual bbox 宽度

做最小校正。

这条规则对角标、品牌语、短标签与标题同样适用。

## 12.9 基线与垂直位置

恢复时必须区分：

- TextBox y；
- 可见字形上边界；
- 可见字形下边界；
- 视觉基线。

使用：

```text
baseline_offset_ratio
```

作为初始依据，再按原图可见字形位置做最小校正。

不得仅以 TextBox 外框中心对齐代替视觉基线校准。

## 12.10 多行文字

多行文本优先：

```text
固定 content
→ 固定 visual bbox
→ font size
→ line_height_ratio
→ width / height
```

若仍溢出，再进行最小几何校正。

不得通过删字或改写解决溢出。

## 12.11 混合样式文字

同一 `text_group_id` 的多个 element：

- 按 `group_sequence` 保持顺序；
- 各自恢复样式；
- 最终整体检查视觉间距和对齐。

## 12.12 z-order

`paint_order` 是层级证据。

默认文字位于对应容器图形之上；若 Approved Render 明确存在文字与前景对象交叠，只做必要局部 z-order 校正。

---

# 13. 字体原则

## 13.1 默认不嵌入字体

最终文字恢复默认：

```text
不把字体文件嵌入 PPTX
```

避免重新制造 Canva 原始导出中的大体积中文字体包。

## 13.2 字体不可得

优先使用目标 `font_family`。

若本机不可得：

```text
使用 Deck-scoped 兼容 fallback
→ 再做同一套 Native Text Visual Fit
```

同一缺失 `font_family` 的 fallback 必须在整套 Deck 中一致。第一次选择后形成运行级映射：

```text
missing_font_family → chosen_fallback_font_family
```

后续页面复用该选择，不能每页各自挑一个“局部最像”的字体；若必须修订 fallback，则所有受影响页面重新执行 Visual Fit 与 Deck-Level Validation。多页并行时必须共享同一 fallback map，不能让并行 worker 各自决策。

在本页真正进入 Native Text Visual Fit 前，必须基于 Finalized Text Manifest 与本页实际采用的 Deck-scoped fallback bindings 计算恢复输入版本：

```text
text_restore_fingerprint
= SHA-256(canonicalized Finalized Text Manifest
           + canonicalized effective page font fallback bindings)
```

若没有 fallback，使用稳定空映射。Restored / Validated Single-Page PPTX 必须记录该 fingerprint。Finalized Text Manifest 或有效 fallback bindings 变化时，旧 restored/validated PPTX 与包含它的 merged deck 失效，重新执行 Native Text Visual Fit 与后续 Hard Gates；只有当修订同时改变 Text-Clean 输入时，才需要回退重跑 Magic Layers。

字体不可得不得成为：

- 转图片；
- 改写文字；
- 默认重新嵌入巨大字体包；
- decorative_text 特殊处理；

的理由。

---

# 14. 文件体积检查

Text-Clean 输入经 Magic Layers 下载 PPTX 后记录：

- PPTX 总体积；
- `ppt/fonts/` 是否存在；
- 嵌入字体总体积；
- `ppt/media/` 体积；
- 与原始有字 Magic Layers PPTX 的差异。

该项不是第五个 Hard Gate，只用于验证文字预清除是否解决字体膨胀。

---

# 15. 标准单页执行顺序

## Phase A — Intended Text Set / Text Manifest Initialization

```text
Current Slide Stage 2 Final Content Truth
+
必要时的历史 Approved Design Backfill
→ 初始化 Text Manifest 的 content / occurrence / truth_ref
```

## Phase B — Full-page Text Discovery / Manifest Finalization

```text
Current Approved Slide Render
→ 全页文字发现
→ region association
→ Finalize Text Manifest geometry/style
→ Removal Inventory v1.0
```

不得在 Full-page Text Discovery 之前猜测完整 visual bbox。

## Phase C — Treatment Assignment

每个区域只能得到：

```text
remove_and_restore
remove_and_drop
preserve_as_graphic
```

检查：

- `remove_and_restore` 必须链接至少一个 Manifest ID；
- `remove_and_drop` 不得进入最终恢复清单；
- `preserve_as_graphic` 只允许 approved graphic asset 或通过严格四条件的 Graphic Typography；
- 对高影响区域执行 Destructive Cleanup Risk Check；
- `GRAPHIC_TYPOGRAPHY_UNRESOLVED` / `TEXT_TREATMENT_CONFLICT` 未解决时不得开始 cleanup。

非关键英文字形不得仅因特殊字体或图标外观被登记为批准图形；确认属于普通文字时，按既有内容规则分配恢复或丢弃，仍须满足图形字标和高影响区域的原保护条件。

Phase C 完成后，将 Finalized Text Manifest + Removal Inventory + 当前 Approved Render / Final Content Truth 绑定为当前 **Stage 3 Text Plan**；Text Plan 变化会使旧 Text-Clean 及全部下游派生产物 stale。

## Phase D — Text-only Cleanup

```text
Original Approved Slide Render
+
Removal Inventory
→ Pass 1 Cleanup
→ Residual Scan
→ 必要时 Pass 2 局部补清
→ Text-Clean Render
```

## Phase E — Integrity Check

```text
Residual Text Check
+
Non-text Preservation Check
```

均 PASS 才继续。

当 current page set 的 Text-Clean 页面需要向用户正式展示时，只能使用 §10.5 定义的 Stage 3 Text-Clean Formal Display Set；不得把 Candidate History 或旧清理图汇总进正式输出。

## Phase F — Magic Layers / Graphics-first PPTX

```text
Text-Clean Render
→ Magic Layers
→ 当前已验证的 Canva 单页 PPTX 获取链
→ Graphics-first PPTX
```

检查拆层质量、PPTX 有效性、文件体积，并由 Stage 3 总协议执行 **Graphics-first Text Neutrality Check**。只有中间 PPTX 不含会与 Manifest 叠加的普通可见文本后，才允许进入文字恢复。

## Phase G — Native Text Visual Fit

```text
Graphics-first PPTX
+
Text Manifest v1.1
→ 仅对 representation_role=native_text 且 treatment=remove_and_restore 的 occurrence 统一原生文字恢复
```

特别检查：

- 普通正文；
- 标题；
- 数字；
- 角标；
- 品牌语；
- 合法 slogan；

是否使用完全相同的 Native Text Visual Fit 机制。

最后执行 Stage 3 四个 Hard Gates。

# 16. 逻辑不变量

正式执行前必须满足：

```text
R1. Text Manifest 只包含 remove_and_restore 或极少数 preserve_as_graphic；remove_and_drop 不得进入 Manifest。
R2. Removal Inventory 可包含全部观察到的文字、错字、乱码和伪文字，并拥有三种 treatment。
R3. observed_text 永远不能覆盖 Text Manifest.content。
R4. 正常可编辑文字与 graphic_typography 的内容真值不得来自 OCR / vision / Canva text；approved_graphic_asset 只允许 preserve_as_graphic。
R5. 每个 remove_and_restore Removal item 必须关联至少一个 Manifest ID。
R6. 每个 remove_and_restore Manifest element 必须反向关联至少一个源区域并具有可解析 visual bbox。
R7. 每个 remove_and_restore Manifest element 最终恢复一次且只能一次。
R8. remove_and_drop 永远不生成最终文本。
R9. preserve_as_graphic 永远不重复生成普通 TextBox，且可见内容必须已确认正确；graphic_typography 必须同时满足四项证据门。
R10. semantic_text 与 decorative_text 均可且通常应 remove_and_restore。
R11. decorative_text 不得触发特殊恢复算法。
R12. 所有 remove_and_restore 使用同一 Native Text Visual Fit。
R13. 大字号、装饰字体、品牌语、角标不能自动触发 preserve_as_graphic；这些特征不是充分条件。
R14. Text-Clean Render 除显式且内容正确的 approved graphic asset / Graphic Typography 外不得有文字残留。
R14a. 高影响 text-like region 在 Representation / Treatment 未确定时必须 BLOCK，不得默认删除。
R14b. Stage 3 Text Plan 必须在任何破坏性 cleanup 前完成并绑定当前 Render + Truth。
R15. 最终恢复不得通过修改 content 解决版式问题。
R16. 混合样式片段按 text_group_id + group_sequence 恢复，不得重复。
R17. 同字符串的多个合法 occurrence 不得去重。
R18. exact_facts 不单独生成额外 TextBox。
R19. PNG 项目符号/编号不得自动推断为 PowerPoint 自动列表。
R20. 默认不嵌入字体；同一缺失字体的 fallback 在 Deck 内一致。
R21. PNG 像素字号不得直接作为 PPT point。
R22. 源图与最终 Deck canvas 允许 Canva/PPTX 导出造成的单轴绝对尺寸差异不超过 5 个源像素；该微小差异不得单独阻断文字恢复。content rectangle 只允许处理已知内部 inset/letterbox，不得掩盖超过容差或已有证据表明的真实整体缩放/重排。
R23. 视觉恢复目标是原图可见字形包络，而不是假定原始 TextBox 外框。
R24. 正文、标题、角标、品牌语使用同一字距/字号/基线/位置拟合规则。
```

---

# 17. Failure Attribution

本规范只定义文字链相关归因；Magic Layers 工具、下载、Hard Gates、Merge 与 Deck-Level code 由《Canva Magic Layers 可编辑 PPT 重建协议 v2.4》统一定义，避免同一失败在两份协议中产生不同 code。

## 17.1 Blocking failures

```text
MISSING_STAGE2_CONTENT_TRUTH
APPROVED_DECORATIVE_TEXT_UNRESOLVED
TEXT_MANIFEST_FAILED
FULL_PAGE_TEXT_DETECTION_FAILED
REMOVAL_INVENTORY_FAILED
TEXT_TREATMENT_CONFLICT
TEXT_REGION_LINK_FAILED
RESTORE_BBOX_UNRESOLVED
CANVAS_MAPPING_UNRESOLVED
PRESERVED_GRAPHIC_CONTENT_INVALID
TEXT_ONLY_REMOVAL_FAILED
RESIDUAL_TEXT_REMAINS
NON_TEXT_PRESERVATION_FAILED
TEXT_CLEAN_INPUT_UNSAFE
PRESERVED_GRAPHIC_REINTERPRETED_AS_TEXT
GRAPHICS_FIRST_TEXT_CONTAMINATION
TEXT_RESTORATION_FAILED
TEXT_VISUAL_FIT_UNRESOLVED
TEXT_OVERFLOW_UNRESOLVED
```

其中：

- `PRESERVED_GRAPHIC_CONTENT_INVALID` → 修正对应批准图形资产，不得继续保护错误字标；
- `RESTORE_BBOX_UNRESOLVED` → 不猜位置，先解决 Content Truth occurrence 与 Approved Render 的源区域对应；
- `GRAPHICS_FIRST_TEXT_CONTAMINATION` → 在原生文字恢复前清除/解决中间 PPTX 异常文本。

## 17.2 Non-blocking diagnostics

以下不是第五个 Hard Gate，也不应单独阻断交付：

```text
FILE_SIZE_NOT_IMPROVED
```

它只用于判断文字预清除是否达到体积优化预期。只要四 Hard Gates 与兼容性验收成立，文件体积未改善本身不等于页面失败。

---

# 18. 禁止事项

本规范禁止：

- 新增 Stage 2 第三个交付物；
- 把 OCR / vision 自动升级为最终文字真值；
- 仅按字符串匹配原图文字与最终真值；
- 因 decorative_text、角标或大字号而启用特殊恢复；
- 把恢复困难的文字直接转图片规避；
- 无限循环去字；
- 为排版改写文字内容；
- 默认嵌入字体；
- 重新研究 Canva 下载链；
- 扩展 Recraft / Qwen / Scene JSON 等其他路线。

---

# 19. 最终执行原则

```text
Text Manifest answers what must exist in the final slide.
Removal Inventory answers what exists in the current raster and how to treat it.
They are different artifacts.

Approved semantic text and approved decorative text both belong in the final Manifest.
Wrong text, hallucinated text and pseudo-text belong only in the Removal Inventory.

Remove-and-restore is the default for intended editable text.
Remove-and-drop is the default for unintended text.
Preserve-as-graphic is a strict exception.

Clean text before Canva.
Restore truth after Canva.
Restore all editable text with the same Native Text Visual Fit algorithm.
Fit to visible glyph geometry, not to an assumed original textbox.
Never change content to solve layout.
Do not embed fonts by default.
Keep the pipeline minimal, deterministic and testable.
```

---


## Runtime dispatch: Text Plan and formal Text-Clean display

Before creating a Formal Text-Clean Render, finalize the current page's Text Manifest and Removal Inventory, then register them with `python scripts/canva_bridge.py register-text-plan --state <state> --slide-id <id> --manifest <manifest.json> --inventory <inventory.json>`. The plan must PASS the Stage 3 representation/treatment gate before `register-text-clean`. Ordinary editable text remains `remove_and_restore`; wrong/unapproved text remains `remove_and_drop`; `preserve_as_graphic` is limited to approved graphic assets and strictly evidenced `graphic_typography`. Large size, decorative font, gradient or prominence alone never authorizes preservation; judge whether the specific glyph form itself is composition-critical and would suffer material loss under native TextBox substitution. Independent placement or lack of graphic integration does not by itself disqualify `graphic_typography`. A high-impact text-like region whose representation is unresolved blocks destructive cleanup rather than being deleted by default.
After Text-Clean processing, use `stage3-text-clean-display --state <state>` for any formal user-facing cleanup review; it returns only current Text-Clean Render artifacts in stable page order. Never mix Stage 2 failed/superseded Candidates, old Text-Clean files, debug images, or fallback Approved Renders into that formal display. If it reports INCOMPLETE, report the missing slide IDs instead of filling gaps with history.


## Runtime dispatch: reconstruction branch selection

After **all Text-Clean pages are current**, run `python scripts/reconstruction_router.py status --state <state>`. At `AWAITING_RECONSTRUCTION_BACKEND_SELECTION`, show the user exactly these two reconstruction paths and wait for an explicit choice:

```text
A. Magic Layer 分支（推荐）
B. Image Layer 分支

推荐使用 Magic Layer 分支。
```

Record the decision with `python scripts/reconstruction_router.py choose-backend --state <state> --backend magic_layer|image_layer`. Do not silently select or automatically fall back between branches. Protocol loading is branch-specific: **Magic Layer 分支 = 05 + 06 + 07**; **Image Layer 分支 = 08 + 07**. Before a branch is selected, reuse the existing text-plan/Text-Clean implementation only for shared text preparation; never call a Magic reconstruction attempt before the explicit branch decision.
