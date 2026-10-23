# Implementation notes — ZAnchorFlow

## Current revision: 0.9.0-rc19-candidate

Reference 08 v1.1 introduces Bundle v3 declared geometry verification, identity-only returned boxes, conditional Pillow/NumPy dependencies, structured ordinary model limitations with downstream inheritance, independent Severe Quality Retry (one submit reservation), and Agent readiness. Reference 01–07 and the native merge/text restoration engines are preserved. Offline validation uses existing return files and local/stub fixtures; no new model calls. Normal user communication uses ZAnchorFlow; versions remain diagnostic metadata.

## Historical RC18 implementation

# Implementation notes — Skill 0.9.0-rc18-candidate

RC18 uses `zanchorflow 0.9.0-rc17-candidate` as the frozen baseline and adds one optional Stage 3 reconstruction backend. The existing Canva implementation is user-facing **Magic Layer 分支**; the new provider-based implementation is **Image Layer 分支**.

The shared orchestration change is intentionally above the Magic backend: all current Text-Clean pages must be complete, then `reconstruction_router` waits for an explicit deck-level backend choice. Once `magic_layer` is selected, the existing `canva_bridge` / Host acquisition / retry / provenance implementation is reused unchanged. Once `image_layer` is selected, independent `layer_bridge` state owns plan, paid request, provider result, geometry, bundle and Graphics-first provenance.

Image Layer uses Reference 08 plus shared Reference 07. Magic Layer keeps References 05 + 06 + 07. Reference 05/06 and the Magic-specific scripts remain frozen. Raw provider resolution never determines PowerPoint physical slide size or text size: `layer_geometry` maps backend pixels to canonical Source-normalized geometry, then the existing Source-pixel 5px invariant and Native Text Visual Fit remain authoritative.

360 Reveal-Layer credentials are read from `ZANCHORFLOW_360_API_KEY` only at submit/query time. They are not persisted. Unit tests use fake HTTP/provider responses; real API behavior and full live E2E remain for Codex validation.


## Cross-page sparse sheets maintenance

Up to three approved source pages per foreground sheet. Shared-call receipts are atomic; object budgets and historical identities persist. Reviews are append-only; partial split failures preserve safe objects. Original route/approval checks remain mandatory. Real tool evidence is reported separately from offline fixtures. No installation or remote publication.


## COM diagnostic maintenance

Preserve primary COM/integrity errors when temporary workspace deletion fails; report retained workspace explicitly. Add failing operation stage and COM HRESULT/excepinfo. No save/reopen/close order, Office fallback, geometry gate, or automatic retry changes. Original intermittent trigger is not established; do not attribute file-lock messages to user activity.


## Receipt and interruption recovery maintenance

R01/R04: append facts through a reserved-token recovery API without granting asset use. R02: exact replay is idempotent; conflicts do not overwrite. R03: late facts bind to the original attempt and never refund/reset calls. R05: both bridge transactions use verifiable ownership and a kernel guard; only proven exited local owners are recovered. Legacy/partial/unknown locks stay blocking. Normal sheet approval checks, current asset checks and COM diagnostics remain in force. No installation, remote generation or publication is part of this maintenance.

## Route selection and GitHub synchronization

Present Magic Layer, Image Layer and Editable Path without a recommendation. Explain mechanism, editing units and cost limits at selection; the author verified the general free Canva limit of no more than 20 pages per month. Editable Path has no separate layering-service purchase; host image tools retain their own allowance and billing rules. Internal backend keys, task timing and Image-only support boundaries stay unchanged. Preserve the remote showcase and support-author material; synchronize the verified runtime, installer and both distributions.
