# Selecting editable units and boxes

## Decision order

1. Explicit user editing goals override the default. Otherwise infer editing value without asking each page for an edit brief or strategy.
2. Prefer shapes, independently edited cards, icons, special arrows and combined graphics. A card plus its icon, border, shadow and internal decoration is normally one unit. Select separate cards when their independent editing value warrants it; do not default to an entire row.
3. Photos/textures are complete editable assets when independently moved/replaced. Background/decorative detail is not split mechanically. No automatic native shape reconstruction; PNG layers support movement/scale/hide/replace, not editable fills/strokes or automatically reattached arrows.
4. New Plan targets may set primary_edit_action=move|resize|hide|replace; descriptive edit_action remains explanation, default primary action is move. Identify internal versus external connector ownership. Record editing action, grouping reason, boundary clarity, protected neighbors and credible background repair. The local rank_edit_candidates helper ranks already recognized/grouped units; it does not detect pixels or decide grouping.
5. Within six foreground slots, combine only genuinely jointly edited objects or defer lower-value units; record recommended, selected and actual layer counts. Never absorb unrelated content in a broad box merely to meet the cap.
6. Retain source-pixel boxes, finite adaptive margins, overlays and the original approved Plan/readiness process. No new per-page confirmation. Frozen old Plans keep their grouping; changes require the user's requested revision and never erase prior paid submission history.

## Box construction

Use the source image's actual width and height; displayed previews may be scaled. Coordinates are [x1, y1, x2, y2] in source pixels with origin at upper left. A box should enclose the target's visible pixels, including thin extremities, with an adaptive context margin chosen from size, edge complexity, shadow extent and neighboring distance; no fixed pixel margin or optimizer. Inspect the numbered overlay and edge crops before submission. Do not use one broad box merely to absorb extra candidates.

Overlapping boxes can be valid for objects at different depths, but they raise separation ambiguity. Make each target's intended identity explicit and review the result. For fragmented but jointly edited elements, one group box is acceptable only if the returned layer actually contains the intended group.

## Candidate sources

- User target or manual visual inspection: authoritative for desired edit units; still verify geometry.
- Open-vocabulary object detector: useful for proposing locations of named objects. Detection score is not edit value or segmentation quality.
- Box/point-prompted segmenter: optionally preview whether a candidate can be isolated. Its mask is evidence for review, not a guaranteed decomposition result.
- No detections: continue with manual inspection, especially for illustrations, stylized graphics, and small objects.

These tools are optional aids. The backend's actual output decides whether a box worked.

## Research basis

- GitHub's [image-annotations skill](https://github.com/github/awesome-copilot/blob/main/skills/image-annotations/SKILL.md) emphasizes exact source-pixel coordinates, a coordinate grid, and crop verification. We use that to prevent preview-scale coordinate errors.
- [Grounding DINO](https://github.com/IDEA-Research/GroundingDINO) accepts image plus text and returns scored boxes; its thresholds select proposals, not final editable units.
- [Grounded SAM 2](https://github.com/IDEA-Research/Grounded-SAM-2) chains grounding boxes into masks. This supports a candidate-preview stage when available.
- A [SAM 2 issue on occluded objects](https://github.com/facebookresearch/sam2/issues/605) documents that a box prompt can still produce only a partial object. Treat this as a practical failure case, not a universal failure rate.
- A [ComfyUI discussion](https://www.reddit.com/r/comfyui/comments/1spl1dt/is_there_anything_similar_to_imagetolayersai/) notes that choosing the layer structure is a hard part of image-to-layers work. This is anecdotal practitioner input; the edit-unit rule above is our workflow design, not a cited benchmark.

No single source establishes a universal optimal layer count or box margin. Validate the chosen plan on the actual image and backend result.





## Readiness and complete assets

Use the eight LAYER_PLAN_READINESS checks in Reference 08 once within the original approved Plan workflow. Do not optimize indefinitely. Photos, screenshots and textures can be complete editable assets for whole-object movement, deletion and replacement. Group dedicated borders, shadows, decorations and internal connectors with the edited object; protect background objects. Substantive changes to an approved Plan require the existing approval process.
