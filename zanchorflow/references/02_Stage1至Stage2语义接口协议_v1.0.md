# Stage 1 → Stage 2 语义接口协议 v1.0
## Semantic Interface Contract

**适用范围：** 定义 Stage 1 内容架构输出如何交付 Stage 2 视觉生成阶段。  
**核心目标：** 在保护事实、真实语义关系和页面核心意图的同时，为 Stage 2 保留充分的内容展开、重组和视觉解释自由。

---

# 1. 接口原则

Stage 1 与 Stage 2 的职责不是“内容冻结 → 排版执行”，而是：

```text
Stage 1
定义页面语义范围与语义不变量

Original Source Materials
提供事实深度与具体细节

Stage 2
在语义范围内充分展开、重组和视觉解释
```

核心原则：

> **Stage 1 defines semantic scope and semantic invariants; source materials provide factual depth; Stage 2 has broad freedom to elaborate, reorganize and visually interpret content within that scope.**

中文：

> **Stage 1 确定页面语义范围与语义不变量，原始材料提供事实深度，Stage 2 在该范围内拥有充分的展开、重组和视觉解释自由。**

---

# 2. Stage 2 接收的输入

Stage 2 接收：

1. 用户当前明确要求；
2. Stage 1 最终完整 PPT 大纲；
3. 当前页面的六项语义信息；
4. 原始用户材料，在可用时作为事实与细节来源。

当前页面六项信息为：

```yaml
slide_semantic_contract:
  page_task:
  title:
  core_expression:
  key_information:
  semantic_relation:
  acceptance_criteria:
```

本接口不要求 Stage 1 新增额外字段。

完整大纲用于理解整套报告上下文与前后页面边界；当前页六项语义信息用于限定当前页面的主要语义范围。

## 2.1 六字段到 Stage 2 运行语义的编译映射

Stage 2 可以将既有六字段编译为运行时所需表达，但不得借编译新增语义。

```text
page_task + core_expression
→ Page Semantic Spec / page_goal / resolved semantics

key_information
→ Mandatory Information / mandatory_information

semantic_relation
→ Semantic Relationships / semantic_relation

acceptance_criteria
→ Information Requirement / validation constraints

title
→ initial title expression
  （可按本协议允许的范围压缩、改写或提炼）
```

该映射仅统一上下游字段含义，不新增 Stage 1 状态，也不要求 Stage 1 改变六字段输出格式。

---

# 3. 三类 Authority

接口不使用单一优先级链，而区分三类不同权威。

## 3.1 Semantic Scope Authority

决定当前页讲什么、承担什么传播任务：

```text
User Explicit Instructions
>
Stage 1 Final Outline
```

Stage 2 不得仅因原始材料中存在其他相关内容，就自行扩大当前页面主题。

## 3.2 Factual Authority

决定事实、数据、名称和具体细节：

```text
User Explicit Correction
>
Original Source Materials
>
Stage 1 Summary Wording
```

Stage 1 是内容架构和摘要，不替代原始材料的事实权威。

Stage 2 可以返回原始材料补取：

- 精确数据；
- 专有名称；
- 具体步骤；
- 案例；
- 子项；
- 原文关键词；
- 对当前概念的说明性细节。

## 3.3 Visual Authority

在语义范围内，Stage 2 负责：

- 具体构图；
- 视觉形式；
- 图文关系；
- 图表、图解、插画和几何表达；
- 信息视觉层级；
- 色彩；
- 背景；
- Anchor；
- Style DNA；
- 线条、符号、图标、母题；
- 页面节奏与留白。

原则：

> **Visual freedom operates inside semantic boundaries.**

---

# 4. Stage 1 提供的语义不变量

Stage 1 锁定的是语义不变量，不是最终文字表达。

## 4.1 Page Task

`page_task` 定义当前页面的语义范围与传播目的。

Stage 2 可以在该范围内充分展开，但不得将页面变成另一个主题或承担另一个主要传播任务。

## 4.2 Core Expression

`core_expression` 定义本页中心思想。

Stage 2 可以：

- 改写；
- 精简；
- 展开；
- 拆成多个短表达；
- 转化为标题、标签和辅助结论。

条件：中心含义保持一致。

## 4.3 Key Information

`key_information` 定义本页需要覆盖的内容域。

它不是最终文案，也不是最终视觉元素清单。

Stage 2 可以：

- 重组；
- 分组；
- 合并；
- 拆解；
- 排序；
- 标签化；
- 从原始材料补充细节；
- 将多个文本条目转换为不同数量的视觉节点。

最终要求是语义内容得到充分覆盖，而不是输入条目与页面元素一一对应。

## 4.4 Semantic Relation

`semantic_relation` 属于约束最强的语义信息之一。

真实的并列、对比、流程、时间、层级、因果、组成、分类、定量等关系不得因为视觉设计而改变。

关系确定以后，具体如何视觉化该关系由 Stage 2 决定。

## 4.5 Acceptance Criteria

`acceptance_criteria` 定义最低语义完成条件与禁止误解项。

它不是页面内容上限。

满足验收标准后，Stage 2 仍可在当前语义范围内继续丰富页面。

## 4.6 Title

`title` 默认不是严格语义不变量。

Stage 2 可以为了页面表现进行：

- 压缩；
- 改写；
- 提炼；
- 增强信息性。

用户明确要求保留的标题、正式名称、专有名称不得自行改变。

---

# 5. Semantic Elaboration Freedom

在 Stage 1 确定的页面语义范围内，Stage 2 可以充分进行：

- 内容展开；
- 内容重组；
- 压缩；
- 改写；
- 标签化；
- 分组；
- 排序；
- 去重；
- 说明性概括；
- 从原始材料补充当前页相关事实与细节；
- 直接、无歧义的计算；
- 视觉解释；
- 将文字转换为图形、图解、图表或插画。

原则：

> **只要含义没有改变，并且语义不变量保持成立，表达形式可以充分变化。**

Stage 2 不是将 Stage 1 机械排版，而是依据 Stage 1 的语义边界重新设计页面。

---

# 6. Derived Factual Expression

Stage 2 可以基于原始材料中的明确数据进行直接、无歧义的推导，例如：

- 差值；
- 比例；
- 百分比变化；
- 简单汇总；
- 已给数据之间的直接比较。

例如原始材料给出：

```text
42 min → 19 min
```

可以表达为：

```text
减少 23 min
```

在计算无歧义时，也可以表达为相应比例变化。

不得从数据继续推导未经材料支持的：

- 原因；
- 趋势外推；
- 机制判断；
- 预测；
- 新结论。

---

# 7. Source Retrieval Boundary

Stage 2 可以主动回到原始材料补取当前页所需的事实深度。

但必须遵守：

> **Source Retrieval ≠ Scope Expansion**

原始材料可以帮助 Stage 2 丰富当前页面，但不能成为扩展页面主题的理由。

例如：

- 当前页面要求展示三项主要成果，Stage 2 可以从原始材料补充这三项成果的精确数字；
- 原始材料中还存在其他成果时，Stage 2 不得因此自动将其他成果加入当前页面。

---

# 8. 新增或展开内容的三项检查

Stage 2 在增加、展开或重组内容时，只需检查：

```text
1. 该内容服务于当前 page_task。
2. 该内容受到原始材料、Stage 1 语义或直接可验证计算的支持。
3. 该内容保持已有 semantic invariants。
```

三项全部满足：

> 可以使用。

第 1 项失败：

> Scope Expansion

第 2 项失败：

> Unsupported Invention

第 3 项失败：

> Semantic Distortion

---

# 9. Visual Grouping 不得制造新语义

Stage 2 可以自由分组，但视觉分组本身不得制造新的事实或关系。

以下视觉手段都可能隐含语义：

- 大小差异；
- 箭头；
- 包含关系；
- 顺序编号；
- 中心—外围结构；
- 上下层级；
- 时间轴；
- 流程方向。

只有在原始材料或 Stage 1 已经支持相应关系时，才能使用这些表达传递该关系。

例如：

- 并列信息不得为了构图方便被转成流程；
- 组成关系不得为了视觉层次被转成上下级关系；
- 相关关系不得被表达成因果关系。

---

# 10. 内容过载处理

Stage 2 不应因为页面内容偏多就立即返回 Stage 1。

优先处理顺序：

```text
重组
↓
压缩
↓
合并重复表达
↓
视觉化
↓
利用图形降低文字成本
```

只有经过合理处理后，仍无法同时满足：

- page_task；
- core_expression；
- key_information；
- acceptance_criteria；
- 基本可读性；

才返回 Stage 1。

---

# 11. 返回 Stage 1 的条件

统一使用：

```text
RETURN_TO_STAGE_1
```

只在以下三类情况触发。

## 11.1 Semantic Contradiction

Stage 1 内部要求互相冲突，Stage 2 无法同时满足。

## 11.2 Irreducible Content Overload

经过合理重组、压缩和视觉化后，内容仍无法在一页清晰呈现。

## 11.3 Missing / Conflicting Required Evidence

页面要求依赖某项关键事实、数据或证据，但原始材料不存在、明显冲突或不足以支持该表达。

其他问题原则上由 Stage 2 自行解决。

---

# 12. 接口自检

Stage 2 正式进入视觉设计前，确认：

```text
[ ] 当前页 page_task 明确
[ ] 当前页 core_expression 明确
[ ] key_information 的内容域清楚
[ ] semantic_relation 已理解且未被视觉方案改变
[ ] acceptance_criteria 可验证
[ ] 原始材料仅用于补充事实深度，没有扩大页面范围
[ ] 当前视觉方案没有制造新的因果、流程、层级、时间或从属关系
[ ] Stage 2 仍保有充分的重组、展开和视觉解释自由
```

---

# 13. 最终原则

```text
Stage 1 defines the semantic field.
Source materials provide factual depth.
Stage 2 designs freely inside that field.
Freedom ends only when truth, relation, or intent would change.
```

中文：

> **Stage 1 划定语义场，原始材料提供事实深度，Stage 2 在语义场内自由设计；只有当事实、真实关系或页面核心意图将被改变时，自由才停止。**


## Runtime dispatch: approved Stage 2 entry

Immediately before loading reference 02 or any Stage 2 visual action, run `python scripts/runtime.py stage2-entry --state <trusted-state.json>` and require exit 0. On PASS, call `python scripts/canva_bridge.py start-run --state <state>`; the same approved Outline resumes the current run and stable `page_order` instead of silently clearing prior PASS state. A newly approved Outline starts a new run and archives old page/deck records without deleting files; use this wrapper rather than the internal `runtime.py stage2-run-start` entry. Register the selected Anchor and `style_dna` as ordinary run artifacts, but never register an `approved_render` path directly.
