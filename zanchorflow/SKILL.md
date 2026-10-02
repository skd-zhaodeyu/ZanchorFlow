---
name: zanchorflow
description: Use when a presentation must progress from structured content and approved flat 2D visuals to an editable PowerPoint deck, including resuming a partially completed deck.
metadata:
  author: "David-Z"
---

# ZAnchorFlow

The archive, directory and invocation name remain `zanchorflow`. Distinguish updates by `updated_at_utc` and ZIP hash; existing release labels describe the source baseline. Normal communication uses ZAnchorFlow, Magic Layer 分支 and Image Layer 分支.

## Entry and invariant boundaries

The eight manifest protocols are authoritative; verify hashes with `python scripts/preflight.py --skill-dir . --output-dir <work/preflight> --scope package`. Use acquisition/merge scoped preflight at their checkpoints. The installed Skill is a READ-ONLY PRODUCT; report suspected product defects as IMPLEMENTATION_DEFECT_SUSPECTED, never hot-edit it.

Initialize new state with `python scripts/canva_bridge.py init --state <work/state.json>`; resume with `status --state <state>` after checking current artifacts/lineage. Resume the earliest unresolved valid checkpoint; do not repeat completed remote work. State/metadata are not Content Truth. Status is not authorization; locks, identities, source fingerprints and budgets survive resume. Never load tests, archives or historical reports as runtime instructions. The sole docs runtime exception is `docs/codex-canva-bridge.md`, for Codex wiring and assembly only.

Outline review must show the complete current six-field review_view and wait for approval. Before reference 02 or visual actions, run `runtime.py stage2-entry`, then `canva_bridge.py start-run`; current-run PASS pages are not cleared. Anchor choice uses only the formally displayed qualified candidates. Stage 2 PASS stops automatic generation; a selected actual page stays locked. Show the complete current ordered renders and await visual approval before Stage 3; current Truth reconciliation/handoff must also PASS. See each step's Runtime dispatch for exact commands.

At every human decision gate, interpret the user's reply in the context of the decision currently pending, not by matching a fixed phrase list. Short contextual replies can express a complete decision. Questions, uncertainty, rejection, rework or concrete modification intent take priority over approval; if intent is genuinely ambiguous, keep the gate pending and clarify. The Agent carries that interpretation through the structured Runtime action/decision and passes the actual user reply alongside it; Runtime enforces state, fingerprint and display integrity rather than re-interpreting natural language.

Before destructive cleanup, register and validate Text Manifest + Removal Inventory. Frozen plans and sources cannot be silently rewritten; unknown high-impact text-like regions block cleanup. After all Text-Clean pages are current, wait at AWAITING_RECONSTRUCTION_BACKEND_SELECTION and explicitly offer A. Magic Layer 分支（推荐） / B. Image Layer 分支. 推荐使用 Magic Layer 分支。 Record the user's choice; no automatic selection or fallback. Magic = 05 + 06 + 07; Image = 08 + 07. Shared preparation before choice uses 07 only.

Restore text by current Manifest/Truth and existing Native Text Visual Fit. Clean only proven safe ordinary text; never erase protected graphics or waive four Hard Gates. Preserve original download/source/canvas bindings; both original tolerance and controlled uniform mapping remain. Bind/seal through the chosen bridge. Merge only current four-gate-sealed single pages; publish only validated exact merged bytes.

## Read only the current step

| Operation | Reference |
|---|---|
| Stage 1 content architecture | `references/01_PPT内容架构与大纲生成协议_v1.2.md` |
| Stage 1 to Stage 2 semantic interface | `references/02_Stage1至Stage2语义接口协议_v1.0.md` |
| Visual exploration and Anchor | `references/03_PPT视觉探索与Anchor延续协议_v2.12.md` |
| 2D generation and rendering | `references/04_页面二维生成前置约束与渲染协议_v2.9.md` |
| Magic Layer branch Stage 2 to Stage 3 handoff | `references/05_Stage2至Stage3_Magic_Layers接口协议_v1.4.md` |
| Magic Layer branch orchestration, gates and delivery | `references/06_Canva_Magic_Layers可编辑PPT重建协议_v2.4.md` |
| Shared text preparation or restoration | `references/07_Stage3_文字处理_消字与复原规范_v1.5.md` |
| Image Layer branch reconstruction | `references/08_Image_Layer_Model可编辑PPT重建协议_v1.1.md` |

Load the selected protocol's shared prerequisites/invariants and relevant failure/forbidden rules, then these chapters, the current step's Runtime dispatch, and applicable cross-references. Cross-step dependencies remain mandatory; no full-file reads by default.

| Current substep | Required detail / prerequisite |
|---|---|
| Text plan / cleanup | 07 §§1-11, §15 Phases A-E, §§16-19; current render/Truth, plan gate and risk check |
| Magic assessment | 05 handoff; 06 §§1-8, §§16-19; explicit branch choice and current Text-Clean |
| Download | 06 §9, §16; Host §§0, 3.1-3.6; current ACCEPT, readonly identity, permissions, intent/budgets |
| Neutrality / canvas | 06 §§9.1-9.2; 07 §§12.1-12.4, §§16-19; Host §§3.7-3.10; exact bound download and cleanup/framing proof |
| Native text restoration | 07 §§1-6, §§12-19; 06 §§9-12, §16; Host §§3.7-3.10; current Manifest/font/source and four gates |
| Seal / merge | 06 §§12-16, §18; Host §§3.7-3.10, §4 + Runtime dispatch; current page seals, trusted order and exact-byte validation |

Read only the selected backend details. Image Layer preparation/QA/retry must read 08 and its Runtime dispatch; geometry/readiness, paid-call authorization, accepted limitations and retries remain mandatory. Within one context do not reread unchanged chapters in full. After compaction, query actual status, bindings and saved evidence, then reload current prerequisites; never treat compaction as new download/rebuild permission. Execute scripts normally; inspect source only for errors or missing interface details. Full diagnostics belong in work; return concise state, key identity, conclusions, actual errors and evidence paths. Complete human review views remain complete.

## Operational Runtime Recovery

在外部工具的运行态恢复中，应先重新观察当前实际状态，而不是机械重复上一动作或过早停止。若外部工具明确提供针对当前同一受阻操作的 **same-operation recovery affordance**，且当前 identity、lineage 与目标保持不变，该动作不会跨越用户决策或权限边界，也不会启动新的生成、重建、导出任务或其他新的昂贵远程工作，则 Agent 可以自主使用该恢复入口；执行后立即重新观察真实状态，并从当前 checkpoint 继续。否则继续遵守现有 bounded recovery、`USER_ACTION_REQUIRED` 与 Hard STOP 规则。该原则只适用于 operational runtime recovery，不授权新的 ImageGen、Magic Layers、numbered acquisition、登录/2FA/权限确认、用户审批或新的内容/设计决策。

## David-Z communication

On first start and final delivery, attach “ZAnchorFlow · by David-Z” to the existing message. Existing key choice/confirmation prompts may use “David-Z 提示｜” with at most one sentence explaining that choice's effect. Do not repeat greetings on resume/compaction, or add a message, tool call or approval merely for attribution. Do not write attribution into PPT pages, file properties or watermarks; author metadata identifies the workflow author only.
