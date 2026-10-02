# RC16.8 Stage 2 Fixed-Input Behavior Eval

**Classification:** non-runtime test/evaluation artifact. Do not load this file as runtime instruction during normal PPT production.

**Purpose:** isolate Stage 2 semantic classification, disposition, and post-REJECT re-planning from ImageGen randomness. Run the same fixed inputs against RC16.7 and RC16.8, then compare to the target behavior below. Do not alter targets to match baseline behavior.

## Output schema

```yaml
case_id:
hard_gate: PASS | H1 | H2 | H3 | H4
disposition: PASS | REVISE | REJECT | HAND_BACK
observable_evidence:
required_correction:
replan_evidence:
successor_plan_summary:
result: PASS | FAIL
```

Rules for recording:
- `replan_evidence` must be empty unless disposition is `REJECT`.
- `HAND_BACK` is an eval label for an explicit cross-stage return, not a new Runtime verdict.
- Do not award PASS merely because wording matches a target phrase; judge the substance of the classification/disposition.

---

## Case A — Legal visual expression absent from literal source

### Fixed input
Page task: communicate a broad approved concept with no specific real-world scene, identity, causal chain, or quantitative mechanism supplied by the source.

Candidate: uses a neutral flat visual metaphor and environmental objects not literally enumerated in the source. The image does not imply a specific real identity, causal mechanism, time sequence, hierarchy, or data point. All mandatory information is present.

### Target
```yaml
hard_gate: PASS
disposition: PASS
replan_evidence: ""
result: PASS
```

### Failure signals
- H1 solely because a depicted neutral object was not literally named in the source.
- Demanding one-to-one source mapping for decorative or open metaphorical objects.

---

## Case B — Actual unsupported core fact or relation

### Fixed input
Page task: present two approved peer concepts without a stated causal or hierarchical relation.

Candidate: the primary visual unmistakably depicts concept A causing concept B through a directional mechanism, making that causal relation part of the main claim.

### Target
```yaml
hard_gate: H1
disposition: REVISE | REJECT
result: PASS
```

Disposition must be decided separately from H1:
- `REVISE` if the causal cue can be removed while retaining the main valid design.
- `REJECT` only if the primary visual structure itself is the unsupported causal mechanism and targeted revision is not a reasonable recovery path; then substantive `replan_evidence` is mandatory.

### Failure signals
- PASS despite the unsupported causal claim.
- Automatic REJECT merely because the gate is H1.

---

## Case C — Local recoverable Hard Failure

### Fixed input
Candidate: overall composition, information hierarchy and semantic structure are valid. One local primary object violates a frozen rendering boundary. The object can be replaced or flattened without rebuilding the main composition.

Run this pattern across H1/H2/H3/H4 variants where the failure remains local and the main valid design remains recoverable.

### Target
```yaml
hard_gate: H1 | H2 | H3 | H4
disposition: REVISE
replan_evidence: ""
result: PASS
```

### Failure signals
- REJECT because the gate type sounds severe.
- Expanding correction scope beyond the local failure without evidence.

---

## Case D — Structural non-recoverability

### Fixed input
Candidate: the primary visual structure itself encodes an invalid core relation. Correcting the defect requires changing the structure that carries the page's core meaning; a local object/text substitution cannot recover it.

### Target
```yaml
hard_gate: H1
disposition: REJECT
observable_evidence: <specific structural conflict>
required_correction: <re-plan the core visual structure>
replan_evidence: <why targeted revision cannot preserve the current core structure>
result: PASS
```

### Failure signals
- REJECT with only a restatement of the Hard Failure.
- Generic tautology such as “re-plan because re-planning is needed”.
- `replan_evidence` that says only “safer”, “better”, “cleaner”, or “more polished”.

---

## Case E — Contradictory local-correction + REJECT

### Fixed input
Review reasoning says:
- only one local object must change;
- the remaining composition and information structure can be preserved;
- required correction is explicitly local.

The same review nevertheless outputs REJECT with a generic statement such as “rebuilding is safer”.

### Target
```yaml
result: FAIL
```

Expected corrected behavior:
```yaml
disposition: REVISE
replan_evidence: ""
```

Unless new evidence separately proves why the stated local correction is insufficient.

---

## Case F — REJECT successor Re-plan Neutrality

Use the same approved semantics, mandatory information, information requirement, Style DNA, rendering constraints and REJECT record for both F1 and F2.

### F1 — Unjustified safe shrink
Successor plan discards valid information or switches to a generic low-information safe medium solely because it is easier to avoid another Hard Gate.

Target:
```yaml
result: FAIL
```

### F2 — Justified simplification
`replan_evidence`, semantics, readability, or an explicit user request positively supports a simpler composition/carrier. Mandatory information and semantic relations remain intact.

Target:
```yaml
result: PASS
```

### F3 — User explicitly requests simplification
User explicitly asks that the current page be simpler. The successor honors that request without dropping mandatory information or changing semantic invariants.

Target:
```yaml
result: PASS
```

### F4 — Carrier change is justified
`replan_evidence` shows the previous carrier itself cannot support the required correction. The successor chooses a different carrier while preserving approved semantics and remaining constraints.

Target:
```yaml
result: PASS
```

### F5 — Carrier change is only risk avoidance
Previous carrier is not shown to be defective. Successor changes to a generic safer carrier solely because it is easier to qualify.

Target:
```yaml
result: FAIL
```

---

## Case G — Explicit cross-stage handback

### Fixed input
After reasonable Stage 2 regrouping, compression and visualization, mandatory content still cannot be made readable without changing the approved content architecture. The existing protocol identifies this as Irreducible Content Overload.

### Target
```yaml
hard_gate: H3
disposition: HAND_BACK
successor_plan_summary: return to Stage 1 under the existing cross-stage boundary
result: PASS
```

### Failure signals
- Infinite Stage 2 REVISE loop.
- REJECT followed by repeated visual re-planning when the canonical contract requires Stage 1 handback.

---

# Evaluation acceptance

RC16.8 passes this fixed-input behavior eval only if:
1. A does not over-classify legal visual freedom as H1.
2. B still blocks real unsupported core facts/relations.
3. C chooses REVISE across gate types when the Candidate remains a reasonable repair base.
4. D uses substantive, non-tautological `replan_evidence`.
5. E rejects contradictory “local fix is enough” + REJECT reasoning.
6. F distinguishes unjustified safe shrink from justified/user-requested simplification and justified carrier changes.
7. G preserves the existing Stage 1 handback.

If `replan_evidence` becomes generic boilerplate in repeated runs, stop and return to design review. Do not add severity, confidence, repairability scores or additional Runtime fields as a patch.
