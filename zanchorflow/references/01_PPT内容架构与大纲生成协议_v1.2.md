# PPT内容架构与大纲生成协议 v1.2
## Stage 1 — Content Architecture & Outline Generation Protocol

**适用范围：** 基于用户上传的文档、材料或内容描述，生成完整 PPT 大纲。  
**阶段定位：** Stage 1 仅负责内容架构，不负责视觉设计。  
**核心目标：** 确定整套报告如何讲述、每一页承担什么传播任务、必须表达什么内容，以及关键信息之间是什么真实关系。

---

# 1. Stage 1 职责

Stage 1 需要完成：

1. 确定整套报告的整体叙事逻辑；
2. 根据用户指定页数或实际内容体量，将报告合理拆分为相应页面；
3. 确定每一页承担的主要传播任务；
4. 确定每一页必须表达的核心内容；
5. 明确页面关键信息之间的真实语义关系；
6. 为 Stage 2 提供足够明确的语义输入，同时保留充分的视觉设计自由。

Stage 1 不负责：

- 具体版式；
- 配色；
- 背景；
- 插画形式；
- 图表样式；
- 具体视觉构图；
- Anchor；
- Style DNA；
- 矢量化方式；
- 其他具体视觉设计方案。

原则：

> **Stage 1 defines content architecture, not visual design.**

---

# 2. 整体大纲要求

- 整套 PPT 应形成清晰、连续的叙事链，各页之间自然承接，不得只是若干孤立页面的堆叠。
- 每一页原则上只承担一个主要传播任务；如果一页同时包含多个彼此独立的传播任务，应进行合理拆分。
- 根据材料内容、汇报目的和目标受众选择必要的页面类型，不得为了凑页面类型机械增加页面。
- 常见页面类型可以包括封面、背景/问题、方法/流程、系统/机制、职责/分工、成果/验证、价值、总结等，但这些仅作为常见类型参考，不作为强制清单。
- 封面主要负责建立主题和第一印象。
- 问题页主要负责建立冲突、现状差距或改进必要性。
- 方法/流程页主要负责解释解决思路和实施过程。
- 系统/机制页主要负责解释组成关系和作用逻辑。
- 分工页主要负责降低复杂职责和协作关系的理解成本。
- 成果/验证页主要负责提供事实、数据或证据。
- 价值页主要负责总结实际效果、意义或应用价值。
- 其他页面类型应根据材料内容自行确定。

---

# 3. 每页必须输出的内容

每页至少给出以下六项：

```yaml
slide:
  page_task:
  title:
  core_expression:
  key_information:
  semantic_relation:
  acceptance_criteria:
```

## 3.1 页面任务 `page_task`

- 明确本页在整套报告中的作用。
- 明确本页需要完成的主要传播任务。
- 页面任务应体现本页独立存在的必要性。
- 不使用具体视觉形式描述页面任务。

## 3.2 页面标题 `title`

- 准确概括本页核心内容。
- 避免过于空泛、宽泛或仅使用章节名称。
- 标题服务于内容表达，不承担视觉设计职责。

## 3.3 核心表达 `core_expression`

- 用简洁语言给出本页最重要的核心观点、方法、结论或信息。
- 核心表达代表本页最主要的传播重点。
- 一页原则上只有一个主要核心表达。

## 3.4 关键信息 `key_information`

- 列出支撑本页核心表达所必须呈现的主要内容。
- 信息量应足以支撑完整的一页 PPT。
- `key_information` 必须提供超出 `title` 与 `core_expression` 同义复述之外的实质性支撑内容。
- 在当前语义和事实边界允许时，应展开形成具有实际信息增量的子观点、组成维度、步骤、机制、差异、条件、说明或证据；这些只是可用的语义形态，不要求每页机械齐备。
- 避免用若干泛化短语重复核心表达，也避免塞入过多彼此独立的内容。
- 关键信息是内容域，不是最终页面文案，也不是最终视觉元素清单。

## 3.5 主要语义关系 `semantic_relation`

- 明确本页关键信息之间的真实关系。
- 可以使用并列、对比、流程、时间、层级、因果、组成、分类、定量、叙事或复合关系等描述。
- 复合关系可以直接使用自然语言说明。
- 原始材料未建立明确关系时，应保持中性，不得自行推断为因果、流程、层级或时间顺序。

## 3.6 验收标准 `acceptance_criteria`

- 明确本页最终必须传达的核心认识。
- 明确不得遗漏的关键信息。
- 明确不得被错误表达的语义关系。
- 必要时明确本页无需展开的次要内容。
- 验收标准定义最低语义完成条件，不限制 Stage 2 在语义范围内进行合理展开。

---

# 4. 内容边界

允许对用户提供的材料进行：

- 归纳；
- 压缩；
- 重组；
- 合并；
- 拆分；
- 标题优化；
- 去除重复表达。

不得自行增加缺乏材料依据的：

- 事实；
- 数据；
- 因果关系；
- 时间关系；
- 层级关系；
- 系统关系；
- 定量结论；
- 其他实质性结论。

原始材料信息不足时，不得为了让大纲显得完整而虚构具体事实、数据、案例、因果关系、时间关系、层级关系、系统关系、定量结论或其他需要来源支持的实质性结论。若用户仅提供主题或简述，且未明确要求仅限所给材料，可在不引入上述未经支持内容的前提下，围绕当前主题进行中性的概念分解、说明维度组织和内容层次展开。

---

# 5. 信息密度要求

默认目标为中等偏高的信息密度。每页仍聚焦一个主要传播任务，但应在该任务范围内形成足够完整的内容层次与支撑信息，避免只有一个核心表达和少量泛化说明。

同时避免：

- 一页包含多个彼此独立的主题；
- 单页内容过度复杂；
- 大量文字堆积；
- 为增加信息量而重复表达；
- 将本应分开的不同传播任务强行塞入同一页。

原则：

> **One slide, one primary communication task.**

这一原则用于控制内容架构，不用于提前限制 Stage 2 的视觉丰富度。

---

# 6. 输出前自检

大纲完成后，至少进行一轮完整自检与优化，并检查以下内容。

## 6.1 Coverage

- 检查原始材料中的重要内容是否得到覆盖。
- 检查是否遗漏影响报告完整性的关键事实、方法、结果或结论。

## 6.2 Narrative

- 检查整套报告是否形成清晰、连续的叙事逻辑。
- 检查相邻页面之间是否具有合理承接关系。

## 6.3 Page Necessity

- 检查每一页是否具有明确、独立的存在价值。
- 删除仅为凑页数或凑页面类型而产生的无必要页面。

## 6.4 Task Purity

- 检查每页是否聚焦一个主要传播任务。
- 对包含多个独立传播任务的页面进行必要拆分。

## 6.5 Duplication

- 检查不同页面之间是否存在明显内容重复。
- 对重复内容进行合并、删减或重新分配。

## 6.6 Semantic Integrity

- 检查并列、对比、流程、层级、因果、时间、组成、分类、定量等关系是否准确。
- 删除未经原始材料支持的关系推断。

## 6.7 Information Density

- 检查每页信息量是否足以支撑完整页面。
- 若去除标题与 `core_expression` 后，剩余 `key_information` 仍不足以形成有实质内容的完整页面，则该页信息密度不足；应在现有语义和事实边界内继续展开后再进入 Stage 2。
- 避免单页过度复杂或文字过载。

## 6.8 Stage-2 Readiness

- 确保 Stage 2 仅根据本页大纲即可明确本页必须表达的内容、核心重点和不可改变的语义关系。
- 确保 Stage 1 没有提前限定具体视觉形式。
- 确保 Stage 2 仍拥有充分的视觉设计与语义范围内展开自由。

完成自检与必要优化后，再输出最终 PPT 大纲。

---

# 7. 最终原则

```text
Define the narrative.
Define each slide's task.
Define the semantic scope.
Define the semantic relations.
Do not design the visuals.
```

中文：

> **Stage 1 负责报告怎么讲、每页为什么存在、必须讲什么以及这些信息之间是什么关系；具体怎么画，留给 Stage 2。**


## Runtime dispatch: Outline review and reply

### Minimal six-field input and Windows encoding

The package manifest is manifest.yaml. Before these Python commands in a Windows session:
~~~powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
~~~
A minimal valid JSON shape (expand content for the real task; do not add slide_id):
~~~json
{"slides":[{"page_task":"说明工作流程","title":"从内容到交付","core_expression":"先明确内容，再生产页面","key_information":["确认内容与语义关系","确定视觉方向","逐页生产与验收"],"semantic_relation":"顺序流程","acceptance_criteria":["三个步骤完整且关系正确"]}]}
~~~
Runtime manages page identity separately. Keep the actual author review and approval below.

After Stage 1 creates the ordered six-field Outline, register it with `python scripts/runtime.py stage1-draft --state <trusted-state.json> --outline <outline.json>`, then run `stage1-review --state ...`. Send the returned **complete** `review_view` to the user and STOP at `AWAITING_STAGE1_APPROVAL`. It shows every page's task, title, core expression, key information, semantic relation, and acceptance criteria. Do not load reference 02, compile the semantic interface, explore visuals, or call image generation before approval. On resume, reuse and show the current review draft. Process only the user's reply to that displayed review with `stage1-reply --state ... --message <actual-user-reply> --decision <approve|revise|rework|unclear>`; for precise edits, pass a JSON patch file with `--edits-json`. The `decision` is the Agent's contextual interpretation of the user's actual reply, not a transcription of keywords: `approve` accepts the current displayed version (or requested edits and then continues), `revise` applies requested edits but keeps review pending, `rework` returns to Stage 1, and `unclear` keeps the gate pending. Approval still requires the current displayed fingerprint, so the same words outside that live review cannot approve a stale or undisplayed Outline. An initially supplied, explicitly final direct-use outline may use `stage1-preapproved --state ... --outline ... --message <actual-user-instruction>` after faithful six-field validation; call that structured action only when the user's contextual intent is unambiguously direct-use/final.
