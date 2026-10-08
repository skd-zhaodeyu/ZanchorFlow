# PPT视觉探索与Anchor延续协议 v2.12
## Visual Exploration & Anchor Continuity Protocol

**适用范围：** 由生图模型生成 PPT 图片页面的视觉探索、Anchor 选择、风格提炼与跨页延续。  
**核心原则：** 页面语义决定“表达什么”并限定合法视觉形式空间；当前设计在该空间内选择具体视觉形式；Anchor 只决定该视觉形式“以什么视觉语言呈现”。  
**外部依赖：** 所有真实生图必须遵守《页面二维生成前置约束与渲染协议》。本文件不重复定义 2D、HUD、Glow、Pseudo-3D 等渲染边界。

---

# 1. 目标与边界

本协议服务于以下工作流：

```text
页面语义
    ↓
自由视觉探索
    ↓
生成少量有意义的候选页
    ↓
用户选择Anchor页
    ↓
提炼稀疏Style DNA
    ↓
后续每页依据当前语义重新构图
    ↓
Style DNA负责跨页视觉一致性
    ↓
二维生图协议负责生成前合法化
```

本协议不建立：

- 固定 PPT 模板；
- 强制页面版式库；
- 必须预选的 Style Family；
- 大型 Anchor 参数库；
- 自动吸收所有生成结果的风格学习机制。

---

# 2. 顶级规则

## Rule 1 — Semantic task is fixed; visual solution is open

页面主题、强制信息、事实、数量关系、因果关系、时间关系、层级关系和其他已知逻辑不得被视觉设计改变。

## Rule 2 — Semantic structure constrains the admissible visual forms

流程、比较、层级、系统、趋势、分类等真实语义关系首先限定哪些视觉形式在逻辑上成立。

在这一合法空间内，模型仍可选择不同的构图和视觉载体；不存在“某一种语义只能对应一种固定图形”的映射。

Anchor 不得为了维持风格而强迫页面使用与语义不匹配的流程图、系统图、图表、卡片或插画。

## Rule 3 — Anchor Style DNA conditions visual treatment

Anchor 主要影响：

- 色彩关系；
- 字体与标题层级气质；
- 几何语言；
- 线条语言；
- 图标与二维插画语言；
- 背景母题；
- 视觉层级与节奏；
- 图文关系的整体气质。

Anchor 不决定当前页的具体 Layout。

`NON_COVER` 指除封面 / Cover 之外的全部正式 PPT 页面。除非用户明确指定当前具体页面例外，否则章节页、过渡页、总结页等名称本身不产生自动豁免。

`typography_hierarchy` 只描述字体气质、字重关系、标题—正文的相对层级及排版节奏，不包含某一页标题的具体字号尺度、占屏比例、标题主视觉化程度或“以大字号文字作为主视觉”的页面级构图特征。Cover 页面可以使用展示性大字号标题作为主视觉；`NON_COVER` 页面默认不得使用展示性大字号标题或其他标题文字作为页面主视觉。只有用户明确要求当前具体非封面页面采用此类表达时才允许例外；不得从 Anchor、Style DNA、前页或模型自身审美偏好推导该例外。 当用户明确要求当前页面承担 poster / promotional / display-oriented communication task 时，该任务本身构成当前页面对展示性 Typography 作为候选 `primary_visual_carrier` 的页面级授权；该授权不要求 Typography-first，也不改变 mandatory information、semantic relation 或其他 Hard Gate。

## Rule 4 — Each page composes from its own semantics

后续页面必须从当前页语义重新开始，不得以“上一页长什么样”为主要构图依据。

## Rule 5 — Learn conservatively

用户选中 Anchor 后，只提炼有充分依据、能够跨语义泛化的视觉特征。宁可少学，也不把当前页偶然结构固化成风格规则。

---


# 2.1 冲突优先级

当视觉风格与页面任务发生冲突时，采用最小必要优先级：

```text
Semantic Integrity
>
Mandatory Information Completeness
>
Readability
>
Current-page Semantic Fitness
>
Anchor Style DNA
>
Novelty
```

因此不得为了维持 Anchor 的留白、视觉主导比例、插画强度或构图习惯而删除强制信息、缩小到不可读或改变真实逻辑。

---
# 3. Semantic Guard

视觉设计必须保持输入语义关系。

```text
并列 ≠ 因果
并列 ≠ 流程
无序 ≠ 时间顺序
相关 ≠ 因果
相关 ≠ 从属
分类 ≠ 层级
组成 ≠ 流程
定性 ≠ 定量
```

不得为了设计效果创造：

- 未提供的数据、百分比或趋势；
- 未提供的因果方向；
- 未提供的时间顺序；
- 未提供的层级；
- 未提供的设备连接、系统接口或输入输出关系；
- 未经支持的事实性结论或具体身份主张。

如果输入没有建立某种关系，默认保持中性与未定，不得由视觉设计自行升级为因果、流程、时间或层级关系。

允许按《Stage1至Stage2语义接口协议》定义的 Semantic Elaboration Freedom 展开；本协议不另设第二套内容扩展强度。

在该边界内，可继续采用概括、简短解释、标签、已有信息重新分组以及不增加新事实的说明性短语。

---

# 4. Mode A — Free Exploration

当用户尚未选择 Anchor 时进入 Free Exploration。

## 4.1 Exploration 输入

只使用：

```text
Page Semantic Spec
+ Mandatory Information
+ Semantic Relationships
+ Information Requirement
+ Current 2D Rendering Boundary Reference
+ Meaningful Diversity Requirement
```

候选探索阶段不应加载：

- 固定 Family；
- 完整 A01–A12 分类定义；
- 既有 PPT 模板；
- 人工 Anchor 库；
- 固定 Layout；
- 主题触发式二维对象映射表；
- 与当前任务无关的历史失败页面。

目的：避免模型在真正探索之前就获得“标准答案菜单”。

---

# 5. Design Concept — 候选生成前的轻量设计概念

候选阶段不建立详细 Production Visual Plan。

每个候选只形成简短 Design Concept：

```yaml
design_concept:
  semantic_strategy:
  primary_visual_carrier:
  composition_idea:
  information_grouping:
  visual_rhythm:
  color_direction:
```

其作用是定义“设计方向”，而不是规定元素坐标和模板骨架。

Stage 1 的 `title` 是页面语义标题。对 `NON_COVER` 页面，它承担导航、识别和层级作用，默认不得成为 `primary_visual_carrier`。Stage 2 必须根据当前页的语义结构与传播任务，让实际信息内容承担主视觉：结构、关系、流程、分类、比较、数据、机制、叙事、图解、插画或其他能够直接表达页面语义的视觉载体应按当前内容择优使用。只有用户明确要求当前具体非封面页面采用展示性文字主视觉，或明确要求当前页面承担 poster / promotional / display-oriented communication task 时，才允许将展示性 Typography 作为候选 `primary_visual_carrier`。后一类传播任务本身构成页面级授权，但不要求 Typography-first，也不改变 mandatory information、semantic relation 或其他 Hard Gate。Cover 页面不受此 `NON_COVER` 限制。

## 5.1 Color before and after Anchor

Anchor 尚未选定时，**color language 是探索变量，而不是预设常量**。

各候选应根据自身 Design Concept 独立选择合适的色彩方向；除非上游已经提供品牌色、既定视觉系统或明确色彩要求，不得仅因行业惯例、科技主题或其他候选已经采用某种配色，就默认收敛到同一色彩体系。

`color_direction` 只描述当前候选的色彩策略与气质，不要求精确色值，也不建立固定色板菜单。

候选之间可以出现相近甚至相同的色彩语言，只要这种选择能够由各自设计概念合理解释。

用户选定 Anchor 后，所选方案中真正属于风格身份的色彩关系，才可经四重过滤进入 `Anchor Style DNA` 并承担跨页连续性。

> **Before Anchor selection, color is exploratory. After Anchor selection, color may become part of style continuity.**

不得在此阶段写入：

- 精确坐标；
- 固定模块数量；
- 固定左右比例；
- 固定卡片位置；
- 页面级对象的具体摆放方式。

---

# 6. Candidate Diversity Contract

候选目标是：

> 在语义适配和信息清晰成立的前提下，探索有意义的不同视觉解。

优先级：

```text
Semantic Fitness
>
Information Clarity
>
Visual Quality
>
Meaningful Diversity
>
Novelty
```

候选差异可以来自：

- 信息组织思想；
- 主视觉载体；
- 构图拓扑；
- 图文关系；
- 视觉抽象程度；
- 信息分组方式；
- 主次关系；
- 视觉节奏。

以下变化本身不足以构成新候选：

- 只换颜色；
- 只换背景；
- 只换图标；
- 只移动少量元素；
- 同一骨架的小幅变体。

同时，候选阶段也不得把色彩视为固定背景条件。不同候选可以探索不同的色彩方向，但这种差异必须服务于各自的设计概念，不能用“换色”替代真正的构图、信息组织或视觉载体差异。

在页面语义允许多种视觉媒介成立时，二维插画与图解、信息设计、技术线稿、数据视觉、编辑型图形等属于并列的一等视觉表达方式。不得因为几何、节点、线条或模块结构更容易生成或更容易满足二维约束，就在视觉探索阶段提前排除插画型解决方案。

## 6.1 候选数量

不强制凑够固定数量。

原则：

> 生成语义空间能够支持的少量高质量候选，首轮通常以 3–5 个为探索上限。

如果真实语义只支持 2–3 个明显合理的不同方向，应停止继续凑数。

---

# 7. Candidate Validity Test

在生图前，每个 Design Concept 至少回答：

1. 当前主要表达机制是否服务于当前 `page_task`，并保持 02 定义的 `semantic invariants`？
2. 是否改变了并列、因果、层级、时间或定量关系？
3. 如果去掉配色差异，它与其他候选是否仍有明显设计思想差异？
4. 它是否只是为了新奇而牺牲信息清晰？
5. 它能否在当前二维渲染模式边界内成立？

不通过则在文本阶段淘汰，不进入生图。

## 7.1 Candidate-set Color Convergence Check

完成单个候选检查后，再从候选集整体检查一次：

> 多个候选是否在没有品牌、用户要求、语义或各自 Design Concept 依据的情况下，自动收敛到了基本相同的色彩语言？

若 YES：

> 回到 Design Concept，重新考虑其中部分候选的 `color_direction`，但不得仅靠换色制造新候选，也不得为了“颜色必须不同”而选择不合适的配色。

该检查防止的是**无理由色彩收敛**，不是要求候选拥有互不相同的色板。

## 7.2 Candidate-set Representation Convergence Check

完成单个候选检查与色彩收敛检查后，再从候选集整体检查一次：

> 当当前页面语义客观上允许多种视觉媒介时，候选是否在没有语义依据的情况下全部收敛为相近的 diagram / infographic / geometric / line-art safe solution？

若 YES：

> 回到 Design Concept，重新考虑其中部分候选的 `primary_visual_carrier` 或 `composition_idea`，探索真正不同的表达机制；不得只通过换色或局部装饰制造“不同媒介”的假象。

该检查不要求候选必须包含插画，也不要求为了媒介差异凑数。若流程、数据、结构、关系或其他真实语义本身使图解型表达明显更适合，多个候选采用图解类媒介完全合法。

当候选以二维插画作为主要表达方式时，其主要意义应由被描绘的对象、人物、环境、行为、关系、情境或视觉隐喻本身承担；仅在信息图外围加入装饰性人物、图标或小场景，不足以构成真正不同的插画表达。

该检查防止的是**无理由媒介收敛**，不是建立插画配额、固定媒介菜单或新的 Style Family。

---

## 7.3 Anchor Formal Candidate Set

Anchor / 封面自由探索阶段的“过程生图历史”与“正式供用户选择的候选”必须分开。正式候选展示只能来自当前 Stage 2 run 中已经通过最低必要 Qualification Review、并以 `approval_mode = anchor_exploration_candidate` 登记为 `qualified` 的候选。

定义：

```text
Anchor Formal Candidate Set
= current run
+ current anchor/cover slide_id
+ qualification PASS
+ approval_mode = anchor_exploration_candidate
+ current artifact bytes
```

`REVISE / REJECT`、调试图、未登记文件、历史失败图均不得进入正式候选展示。Agent 不得通过扫描目录、汇总最近 ImageGen 工具输出或复述聊天历史来重建正式候选集。宿主 UI 已经即时显示过的失败图片可以继续存在于历史消息中，但在“请从以下候选中选择 Anchor / 封面”这一正式展示中不得再次主动列出。

Anchor 探索 PASS 与正式页面 PASS 必须显式区分：

```text
candidate
  ↓ qualification review
PASS + anchor_exploration_candidate
  ↓
qualified anchor candidate
  ↓ formal display
Anchor Formal Candidate Set
  ↓ user selection
user_selected_anchor_page
  ↓
current Approved Render
```

因此，多个合格构图可以在用户选择前同时存在；`anchor_exploration_candidate` 的 PASS **不得提前晋级为该页唯一 current Approved Render**。只有用户从当前正式展示集合中明确选中某个候选后，才以 `user_selected_anchor_page` 晋级。

例如两个设计方向 A/B：若 `A1 → REVISE`、`A2 → PASS`、`B1 → PASS`，正式候选展示只能包含 `A2 + B1`，不能再次展示 A1。若存在多个失败历史稿，规则相同。

本节只治理候选身份与正式展示，不改变候选数量、设计多样性、审美标准或 Qualification H1–H4。

---

# 8. Anchor Selection Authority

只有用户明确选中的候选页拥有后续风格规范权。

以下内容不得自动影响后续 Style DNA：

- 未被选中的候选；
- 生图失败结果；
- 被用户否定的页面；
- 临时实验；
- 页面级局部修正；
- 未经用户认可的风格变化。

原则：

> Only the user-selected Anchor and explicit user-approved style changes may modify the active Style DNA.

## 8.1 Anchor 的双重身份必须显式区分

Anchor 可能承担两种不同角色：

1. `anchor_style_reference`：只提供跨页 Style DNA；
2. `anchor_page_approved_render`：同时也是某一正式页面已经被用户接受的最终视觉结果。

如果候选是在**真实 Deck 页面语义、正式画布与当前批准内容约束**下生成，而且用户面对的是“选择实际采用的页面/封面版本”这一明确任务，则用户选中的候选在通过最低必要 Qualification Review 后，同时成立：

```text
selected candidate
→ anchor_style_reference
+
anchor_page_approved_render
```

该页面随后视为已经拥有 current approved render，不得因为批量生产开始而再次自动生成。最低必要 Qualification Review 仍检查明确 Hard Failure；若不存在 Hard Failure，记录 `PASS`，并可注明 `approval_mode = user_selected_anchor_page`。

如果用户面对的任务只是“选择风格 / Anchor”，而没有明确表达正在选择实际采用的页面版本，则该选择默认只形成 `anchor_style_reference`；不得仅根据“Anchor”一词推定页面批准。探索对象若只是脱离正式页面语义的 style mockup、风格样张或纯视觉试验，同样只形成 `anchor_style_reference`。

## 8.2 Anchor 页面锁定

已经作为 `anchor_page_approved_render` 被用户接受的正式页面，只在以下情况允许重新进入生成：

- 用户明确要求重新设计或再尝试一版；
- 该页上游批准语义发生实质变化，使旧页面不再对应当前内容；
- 用户明确撤销此前页面批准。

仅因为“其他页面开始批量生成”“模型认为还能更漂亮”“希望整套更统一”不得自动重生已锁定页面。

## 8.3 Anchor Continuity 是 Family-level continuity，不是对象克隆

Style DNA 约束的是整体视觉语言，不要求跨页复刻局部对象身份。以下差异本身不得被解释为 Anchor 不一致：

- 人物长相、姿态、服装或视角不同；
- 插画主体不同；
- 图标、局部装饰、模块数量不同；
- 因当前页语义导致的不同构图。

只有当页面在色彩体系、二维/非照片化媒介、线条与几何语言、抽象程度、总体视觉气质等方面发生**实质性 Family 漂移**时，才构成 Style DNA 违规。

例如：扁平二维线稿体系突然变成写实照片、立体 3D 卡通或另一套明显不同的视觉系统，属于实质漂移；同属二维扁平体系的人物画法局部变化不属于。

在默认 `FLAT_2D` 模式下，同一 Family 内允许局部观察角度、遮挡、远近层次、斜向延伸或轻微透视线索存在适度变化；这些变化本身不得被解释为 Anchor Family 漂移。Anchor 约束的是整体二维/非照片化视觉语言，而不是要求跨页拥有相同的空间线索强度。

`ZERO_PERSPECTIVE_2D` 是显式特殊模式，只能来自用户明确要求、当前任务明确规范或既有正式视觉规范。不得仅因为 Anchor 恰好采用正视、无透视构图，就反向推定整套页面进入 `ZERO_PERSPECTIVE_2D`；没有显式上游依据时，默认模式仍为 `FLAT_2D`。

## 8.4 用户视觉选择优先于模型的 Soft Preference

当页面不存在明确的语义或冻结视觉约束违规时，用户明确表达“这张很好 / 就用这张 / 采用此版本”等视觉接受意见，拥有高于模型审美偏好的权威。

模型不得以“还能更高级、更统一、更精致、更舒服”等 Soft Preference 推翻用户已明确接受的页面。

如果候选仍存在明确 Hard Failure，应向用户指出具体冲突；只有用户明确修改相应上游语义或冻结视觉约束后，才能按新约束重新判断。

---

# 9. Semantic–Style Disentanglement

用户选中 Anchor 后，不直接复制或总结整张页面。

先对候选视觉特征进行“语义—风格解耦”。

每一个准备进入 Style DNA 的特征必须连续通过四项过滤。

## 9.1 Filter A — Semantic Dependence

问题：

> 该特征是否主要由当前页内容和关系要求造成？

例如：

- 四个模块，因为原文就是四项；
- 横向箭头，因为内容是时间流程；
- 左右对比，因为语义本身是 A vs B。

若 YES：

> 不进入 Style DNA。

## 9.2 Filter B — Cross-Semantic Persistence

问题：

> 换成完全不同类型的页面内容后，这个特征是否仍有合理机会保留？

若只能服务当前语义：

> 不进入 Style DNA。

## 9.3 Filter C — Global Redundancy

问题：

> 该特征是否已经属于全局规则，而不是 Anchor 个性？

例如：

- 禁止 Pseudo-3D；
- 禁止 HUD Glow；
- 文本必须可读；
- 必须保持语义真实。

若 YES：

> 不进入 Style DNA。

## 9.4 Filter D — Style Identity

问题：

> 去掉这个特征，会不会明显削弱所选 Anchor 的视觉身份？

若 NO：

> 不保存。

只有四项过滤全部通过，才进入 Style DNA。

---

# 10. Anchor Style DNA

Style DNA 必须保持稀疏，不要求所有字段均有内容。

推荐结构：

```yaml
anchor_style_dna:
  color_language:
  typography_hierarchy:
  geometry_language:
  line_language:
  icon_illustration_language:
  diagram_chart_language:
  background_motif:
  hierarchy_and_rhythm:
  text_graphic_relationship:
```

只有在 Anchor 中实际观察到、且通过四重过滤的内容才填写。

## 10.1 不属于 Style DNA 的内容

无条件禁止保存：

- exact layout；
- exact coordinates；
- exact element count；
- 当前页特定对象摆放；
- 当前页特定 diagram topology；
- 当前页特定插画场景；
- 当前页偶然装饰；
- 因当前语义而产生的模块数量和顺序；
- 当前页标题的具体字号尺度、占屏比例、标题主视觉化程度及展示性大字构图。

## 10.2 缺失证据处理

原则：

> Absence of evidence is not evidence of a style rule.

如果 Anchor 没有展示图表、流程、系统图、人物插画等，不建立对应规则，也不建立额外状态。

---

# 11. Anchor 原图的后续地位

Anchor 图片用于一次性提炼 Style DNA。

正式跨页生产时，应以 Style DNA 为主要视觉约束，而不是每页都强依赖原始 Anchor 图。

原因：整张 Anchor 图容易同时携带版式、对象位置和当前页结构，从而诱发 Layout 模仿。

如确需再次参考原图，只能用于核对视觉气质，不得作为当前页构图模板。

---

# 12. Mode B — Anchored Production

选择 Anchor 后进入 Anchored Production。

Anchored Production 的每个预览批次都遵循当前用户指令：若用户明确指定预览页数或页面范围，按用户指定执行；否则本次按 Deck 顺序默认生成接下来的 3 个尚无 Current Approved Render 的页面。若剩余页面不足 3 个，则生成全部剩余页面；已经批准并锁定的 Anchor / 封面页不计入该预览数量。

每页流程：

```text
CURRENT PAGE SEMANTICS
        ↓
SEMANTIC STRUCTURE
        ↓
SELECT VISUAL FORM
        ↓
NEW COMPOSITION CONCEPT
        ↓
APPLY RELEVANT STYLE DNA
        ↓
PRODUCTION VISUAL PLAN
        ↓
2D PRE-GENERATION PROTOCOL
        ↓
GENERATE CANDIDATE
        ↓
QUALIFICATION REVIEW
        ↓
PASS / TARGETED REVISION / REJECT
```

核心关系：

> Semantic structure constrains the admissible visual forms; the current design chooses among them; Anchor Style DNA conditions the visual treatment.

当上一 Candidate 被 `REJECT` 后，应从当前页面语义、仍有效的上游约束和本次 `replan_evidence` 重新规划视觉解；`REJECT` 本身不产生“更简单、更少对象或更安全媒介优先”的新设计偏好。

如果当前语义、可读性、用户要求或 `replan_evidence` 本身支持简化、换 `primary_visual_carrier` 或换构图，则这些变化完全合法。

例如：

```text
语义 = 趋势
→ 选择趋势类图表
→ Anchor决定颜色、线条、标签、强调方式
```

```text
语义 = 流程
→ 选择流程表达
→ Anchor决定节点、线条、几何和整体视觉气质
```

---

# 13. Style Extension for Unseen Visual Types

如果当前页首次需要 Anchor 未展示的视觉类型，例如图表、流程图或科学机制图：

```text
Current Semantic Need
+
Existing Style DNA
+
Global Rules
↓
Design the visual form for the current page
```

不得凭空制定一整套长期规则。

例如 Anchor 已知：

- 已确定的色彩关系与强调逻辑；
- 已确定的线条语言；
- 已确定的几何语言；
- 已确定的视觉层级气质。

第一次出现图表时，可据此设计一个兼容的二维图表。

但该图表样式默认只服务当前页，除非用户明确要求以后继续保持。

---

# 14. Anti-Cloning Principle

不建立强制“每页必须不同”的规则。

只保留一条核心判据：

> Every page composition must be independently justifiable from the current page semantics.

如果当前页与上一页布局相似：

- 若当前语义本身合理支持该结构：允许；
- 若主要原因只是上一页使用了该结构：重新规划。

因此禁止的是：

> 无语义依据的机械重复。

不是：

> 一切重复。

Previous layouts may inform continuity, but must never serve as the primary justification for the current layout.

---

# 15. Feedback Scope

用户反馈默认只作用于最小必要范围。

## Page-level

例如：

> 这页卡片太多。

默认只修改当前页。

## Style-level

只有用户明确表达跨页意图，例如：

> 整套以后都不要这种圆角卡片。

才修改 Style DNA。

## Global rendering-level

例如：

> 所有页面都禁止 HUD 发光。

应更新全局二维渲染规则，而不是 Anchor Style DNA。

原则：

> Local by default; broader scope only when explicit.

---

# 16. Runtime Contract

规范文件不应在每一页完整注入生成上下文。

正式运行时只编译当前页相关的最小信息：

```yaml
page_runtime:
  semantics:
    goal:
    relation:
    mandatory_information:

  composition_concept:

  anchor_style_dna:
    # only traits relevant to current page

  rendering_protocol:
    mode: FLAT_2D  # use ZERO_PERSPECTIVE_2D only when explicitly frozen upstream

  current_2d_risks:
    []

  page_state:
    # page identity + whether this page already has a current approved render
    # do not regenerate an already approved page without an explicit invalidation reason
```

正式运行还必须区分“风格 Anchor”与“Anchor 所在页面是否已经批准”。页面生成只处理当前尚无 `current approved render` 的页面；历史失败候选和未选候选不得因为存在文件而重新获得规范权。 Anchor 自由探索时，Qualification PASS 应使用 `anchor_exploration_candidate` 保持为 `qualified`；正式候选展示只消费 Anchor Formal Candidate Set，用户选中后再以 `user_selected_anchor_page` 晋级。

原则：

> Full specification guides the SKILL; compact runtime guides the page.

---

# 17. Interface with 2D Pre-Generation Protocol

文件 A 输出：

- resolved semantics；
- selected visual form；
- current composition concept；
- relevant Style DNA；
- mandatory information。

文件 B 负责：

- 将当前视觉计划合法化为当前二维渲染模式；
- 在 `FLAT_2D` 下区分允许的局部 Illustrative Depth Cue 与禁止的 Isometric、Axonometric、2.5D、Pseudo-3D / 实体体积模拟；
- 在上游明确冻结 `ZERO_PERSPECTIVE_2D` 时执行更严格的零透视边界；
- 处理 HUD / Glow / Neon 风险；
- 必要时对违规对象提供二维替代表达；
- 编译最终生图 Prompt；
- Preflight。

文件 B 不重新解释页面语义，不替 Anchor 决定视觉风格。

---

# 18. A01–A12：Visual Design Grammar Vocabulary

A01–A12 保留为分析与沟通词汇，不进入 Free Exploration 的强制运行上下文。

- A01 Analytical Consulting — 咨询分析思想
- A02 Swiss Rational Grid — 瑞士理性网格思想
- A03 Editorial Narrative — 编辑叙事思想
- A04 Systemic Network — 系统网络思想
- A05 Technical Schematic — 技术图解思想
- A06 Evidence-Driven Narrative — 证据驱动思想
- A07 Modular Infographic — 模块信息图思想
- A08 Geometric Constructive — 几何构成思想
- A09 Balanced Corporate — 平衡企业表达思想
- A10 Context-Adaptive 2D Flat Illustration Narrative — 二维扁平插画叙事思想
- A11 Scientific Diagrammatic — 科学图解思想
- A12 Visual Motif System — 视觉母题思想

它们可用于：

- 分析已生成页面；
- 描述 Anchor 的设计倾向；
- 用户沟通“增强/减弱某类设计气质”；
- 诊断风格漂移。

不得用于：

> 把候选生成预先切成十二个固定风格槽位。

---

# 19. Text-only Dry Run Requirements

正式生图测试前，至少验证：

## T1 — Parallel Semantics

并列信息不得因为候选多样性被转成流程或中心—外围层级。

## T2 — Hierarchical System

明确层级不得因为视觉创新被转成自由网络或等权模块。

## T3 — Anchor Distillation

四模块、左右布局、横向流程等语义驱动结构不得进入 Style DNA；色彩、线条、字体气质等可泛化特征应被正确保留。

## T4 — Unseen Chart

Anchor 未展示图表时，新页面应由数据语义决定图表形式，Style DNA 只控制视觉处理。

## T5 — Legitimate Layout Reuse

连续两页若语义均天然适合左右对比，不应为了防重复强制改变结构。

---

# 20. 冻结前检查

只有同时满足以下条件才适合冻结：

```text
[ ] 无参考PPT和预选Family也能产生候选
[ ] 候选数量服从语义空间而非固定数量
[ ] 候选差异不是简单换色
[ ] Semantic Guard高于视觉创新
[ ] Anchor提炼经过四重过滤
[ ] Style DNA保持稀疏
[ ] 未展示领域不被凭空写入规则
[ ] Semantic structure限定合法视觉形式空间，而不是固定唯一形式
[ ] Style DNA只决定视觉处理，不覆盖信息完整性与可读性
[ ] 后续页面从当前语义重新构图
[ ] 防克隆不强迫无意义变化
[ ] 未选候选和失败页面不具有规范权
[ ] Anchor 正式候选展示只包含当前 qualified 的 Anchor Formal Candidate Set，不重新汇总 REVISE / REJECT 历史图
[ ] Anchor 探索 PASS 不提前晋级；用户从正式候选集中选中后才以 user_selected_anchor_page 锁定 Approved Render
[ ] 正式页面候选被用户作为实际页面选定 Anchor 后可同时锁定为该页 Approved Render
[ ] 仅选择 style / Anchor 或 style-only mockup 不会误升级为正式页面批准
[ ] Anchor 连续性约束 Family-level 视觉语言，不要求人物/图标/局部对象克隆
[ ] 用户明确视觉接受不会被模型 Soft Preference 推翻
[ ] 页面级反馈默认不污染整套风格
[ ] Runtime Contract足够精简
[ ] 2D硬约束由文件B统一负责
```

---

# 21. 最终原则

```text
Explore broadly.
Filter semantically.
Learn sparsely.
Compose from current semantics.
Style with the Anchor without cloning page-local objects.
Lock user-approved Anchor pages.
Constrain rendering before generation.
Qualify results instead of endlessly optimizing them.
```

中文：

> **广泛探索，语义过滤，稀疏学习，逐页重构，以 Anchor 定视觉气质，在生图前完成精准约束。**


## Runtime dispatch: qualified Anchor choice

During Anchor / cover exploration, review every viable option with `stage2-candidate-review --verdict PASS --approval-mode anchor_exploration_candidate`; this PASS is non-promoting and keeps the image `qualified` so multiple good compositions can coexist before user choice. When exploration is ready, run `stage2-anchor-formal-display --state <state> --slide-id <id>` and formally show **only** the returned `candidates`. Do not reconstruct the choice set from recent ImageGen cards, folders, REVISE/REJECT history, or unregistered images. After the user chooses one of those formally displayed candidates, run `stage2-anchor-select --state <state> --slide-id <id> --candidate-id <id>`; only then is it promoted as `user_selected_anchor_page`.

When the user selects an Anchor candidate as the **actual page/cover version**, the selected formally displayed qualified candidate becomes that page's current Approved Render with `approval_mode = user_selected_anchor_page`; that page is locked and must not be regenerated merely because batch production begins. A style-only Anchor or mockup supplies Style DNA only and does not approve a page.

Before generating or reviewing Anchor images, read Reference 04 Runtime dispatch: Candidate review, formal display and handoff for the shared qualification contract.


<!-- TITLE_POLICY_BEGIN -->
## Optional ordinary-page Title Contract

正文主标题默认承担导航和层级作用，由实质信息内容承担页面主视觉；统一标题规范只能从符合这一要求的普通内容页提取，单页获准的展示性大标题不得成为后续页面的统一基准。

After Outline approval, a new task asks once: **是否统一普通内容页的主标题？A. 统一（推荐）／B. 自由。** An existing explicit instruction answers this choice without another question. Keep the existing cover/Anchor preview, preview batch size and complete-deck approval. There is no second-page sample, Title Contract display/reply gate or per-page human title approval. If there are no applicable pages, skip the choice and record free/no_applicable_pages. Existing states without title_policy stay on their original free flow.

Classify existing page_task into cover/content/toc/section/thanks/display in work/page-roles.json; this metadata does not add Outline fields or change Content Truth. Ordinary content, including substantive summaries, participates. Cover, agenda, section transitions, pure thanks and explicitly display-oriented pages do not. Their exclusion does not exempt them from the existing NON_COVER rule. A source is usually page two; skip special pages and use the first current ordinary normal-heading PASS. An explicitly accepted actual ordinary-page Anchor can supply the same source without regenerating it.

Before first source generation, compile the navigation-heading/content-primary requirement into the compact current-page prompt. Qualification already decides normal heading versus evidenced H2 dominance: prominence or size alone is not failure. When inheriting a standard, preserve the approximate title area and alignment. A material left-to-center or top-left-to-top-center change calls for an existing targeted correction; safe font/size/weight or minor position differences in the same area are review notes and native postprocessing work, not a raster-similarity failure. The bind function checks source hashes and the supplied existing visual assessment; it is not a new aesthetic classifier. An unauthorized typography-primary page follows the existing targeted H2 correction before PASS. A specifically authorized display heading remains local and cannot seed subsequent titles.

Use the current task's genuine user reply with the structured choice; do not keyword-match. Actual page roles come from the approved semantic task. Do not relabel cover or invent promotional authorization. The title policy is separate from Style DNA: fixed heading coordinates/scale do not enter Style DNA; source scene, body arrangement and layout are never propagated.

~~~powershell
python scripts/canva_bridge.py start-run --state <state> --title-choice-required
python scripts/runtime.py stage2-title-policy --state <state> --mode uniform --page-roles-json <work/page-roles.json> --message <actual-choice>
python scripts/runtime.py stage2-title-context --state <state> --slide-id <id>
~~~

A context with next_action=bind_current_prototype means an automatic internal measurement/bind step, never a request for author confirmation. After the first normal Approved Render, save a work/title-contract.json with these exact fields. source_render_sha256 is the actual current approved image hash. heading_assessment is the existing page observation, not an invented result; font_family_basis records uncertainty.

~~~json
{
  "source_render_sha256": "<current-approved-image-sha256>",
  "heading_assessment": {
    "role": "navigation", "content_is_primary": true, "display_exception": false,
    "evidence": "<actual image observation: normal heading; substantive content is primary>"
  },
  "style": {
    "font_family": "<chosen available matching family>", "fallback_font_family": "<available shared fallback>",
    "font_family_basis": "estimated", "font_weight": "bold", "color": "#203040",
    "title_region": [0.08, 0.04, 0.84, 0.17], "alignment": "left",
    "first_line_baseline": 0.10, "visible_glyph_height": 0.045,
    "line_height_ratio": 1.15, "max_lines": 2
  }
}
~~~

The numbers above are illustrative, not universal font/area limits. Measure the source in the existing mapped content rectangle. max_lines=2 is a maximum, not the observed count or an instruction to enlarge a single-line region into occupied body space. title_region and each page's actual visual_bbox_normalized are separate evidence. Never treat raster pixels as PowerPoint points. Choose common available/fallback families before Manifest freeze. Restore all page text with the original Native Text Visual Fit first, then use Reference 07's independent primary-title postprocessing with calibrated common native parameters. Long headings keep the common point size and wrap within real available space to at most two lines; further overflow uses existing author shortening/local exception. The frozen Title Contract, Manifest and source bindings stay unchanged.

~~~powershell
python scripts/runtime.py stage2-title-bind --state <state> --slide-id <source-id> --contract-json <work/title-contract.json>
~~~

The first bind has scope=prototype and origin=system_derived; user approval is the earlier uniform/free choice, not a synthetic standard approval. It snapshots source page/hash, run/Outline, style and observation. Repeating identical input is idempotent. Carry the returned ref into later candidates. Once frozen, editing the prototype page does not update the deck standard. Old snapshots remain valid historical sources; they need not match the prototype's latest image forever.

For an actual local title edit, use the existing --user-requested-variant with --title-override-message <actual-page-request>; qualify the new image, then stage2-title-bind --scope page_override --message <actual-request>. A normal local override includes measured style. A display override has role=display/content_is_primary=false/display_exception=true with actual page authorization; style is unused. A whole-deck title instruction uses --scope global_revision --message <actual-request> and optional --slide-ids-json <affected-current-content-ids>. Preserve existing local exceptions unless the new instruction explicitly includes them. Existing affected PASS pages become pending_visual_revisions; use user-requested variants, retain old files until new PASS. Before complete deck display, do not call the full-display-only revision endpoint. Neither bind nor revision grants any ImageGen/Magic/download/paid retry permission or resets a lock/budget.
No applicable ordinary pages: before asking, classify current page roles using `stage2-title-policy --mode pending --page-roles-json roles.json`. With no `content` page the policy records a system skip, requires no user message, and generation continues in free mode. Do not invent an author selection.

<!-- TITLE_POLICY_END -->
