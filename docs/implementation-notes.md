# Implementation notes — ZAnchorFlow

## Current revision: 0.9.0-rc19-candidate

Reference 08 v1.1 introduces Bundle v3 declared geometry verification, identity-only returned boxes, conditional Pillow/NumPy dependencies, structured ordinary model limitations with downstream inheritance, independent Severe Quality Retry (one submit reservation), and Agent readiness. Reference 01–07 and the native merge/text restoration engines are preserved. Offline validation uses existing return files and local/stub fixtures; no new model calls. Normal user communication uses ZAnchorFlow; versions remain diagnostic metadata.

## Historical RC18 implementation

# Implementation notes — Skill 0.9.0-rc18-candidate

RC18 uses `zanchorflow 0.9.0-rc17-candidate` as the frozen baseline and adds one optional Stage 3 reconstruction backend. The existing Canva implementation is user-facing **Magic Layer 分支**; the new provider-based implementation is **Image Layer 分支**.

The shared orchestration change is intentionally above the Magic backend: all current Text-Clean pages must be complete, then `reconstruction_router` waits for an explicit deck-level backend choice. Once `magic_layer` is selected, the existing `canva_bridge` / Host acquisition / retry / provenance implementation is reused unchanged. Once `image_layer` is selected, independent `layer_bridge` state owns plan, paid request, provider result, geometry, bundle and Graphics-first provenance.

Image Layer uses Reference 08 plus shared Reference 07. Magic Layer keeps References 05 + 06 + 07. Reference 05/06 and the Magic-specific scripts remain frozen. Raw provider resolution never determines PowerPoint physical slide size or text size: `layer_geometry` maps backend pixels to canonical Source-normalized geometry, then the existing Source-pixel 5px invariant and Native Text Visual Fit remain authoritative.

360 Reveal-Layer credentials are read from `ZANCHORFLOW_360_API_KEY` only at submit/query time. They are not persisted. Unit tests use fake HTTP/provider responses; real API behavior and full live E2E remain for Codex validation.
