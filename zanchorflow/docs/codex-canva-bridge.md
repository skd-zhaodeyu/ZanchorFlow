# Codex Canva host bridge — RC17

This file is the sole runtime exception under `docs/`. It connects existing Stage 3 operations to Codex tools; it does not redefine content, text treatment, structural assessment or any Hard Gate. The host uses its current tool schemas and supported browser controls. No standalone Python/PowerShell script can authenticate the Canva connector or click its web UI.

## 0. Initialize and resume

Run commands from the extracted Skill directory; no installation is necessary. Before `stage1-draft`, run `python scripts/canva_bridge.py init --state <project-work/state.json>`. New states contain `slides: {}` and the Codex route. Existing state is checked without modification; `--route external` applies only to a genuinely new external-adapter task, never as an escape from failed Codex provenance.

Run `python scripts/canva_bridge.py status --state <state>` before resuming. It reads current evidence and never calls tools or modifies state. `PREPARE_DECK` selects assembly even when `deck_order` is absent; `DECK_VALIDATION` selects candidate review; `COMPLETE` returns the validated delivery. Earlier page statuses identify the first unresolved page. An existing lock means running/interrupted operation: diagnose it, never automatically delete it or replay the same remote operation. The limited, explicitly terminal export-failure rule below permits a distinct download acquisition; it never unlocks the old operation. Only one writer may operate on a task; generic runtime registrations must not run concurrently with bridge/assembly commands.

Existing Codex tasks without bridge provenance are blocked, even if legacy seals say PASS. Do not reset state, relabel the route, attach a current design ID to old bytes, or reconstruct again solely to replace missing evidence. Preserve the task and diagnose its real historic records; no automatic migration is provided. Import requires a separately reviewed, evidence-backed migration. This release supplies the complete path for new tasks without guessing historic provenance.

After approving an Outline, require the original `runtime.py stage2-entry` check, then start/resume through `python scripts/canva_bridge.py start-run --state <state>`. This calls the unchanged original startup. The same approved run preserves current records. A new approved run archives old slides, bridge/deck records and old order, clears their current mappings, and creates the exact new page set. Historical files stay on disk. Successful CLI start/resume returns `status: RUN_READY`, the original run fields, and exit 0; BLOCKED returns exit 1. Do not invoke the internal `runtime.py stage2-run-start` directly for task rollover; it does not archive bridge page state.

## 1. Discover and connect without spending reconstruction quota

- Discover the Canva plugin and its `image_to_design` capability in the current tool inventory. In this environment the tool is `mcp__codex_apps__canva_image_to_design`; discover the current equivalent rather than assuming that name on another host.
- If missing, search Canva through plugin management and present its installation/connection action. If no installation tool is available, direct the user to the app's plugin catalog. Do not claim installation happened; wait for completion and rediscover tools.
- If the connector returns an authentication/connection request, guide the user to complete that flow. Never collect credentials, tokens or cookies in files. Recheck after the user completes the action.
- Verify access with the read-only `canva_search` tool, supplying a benign query and a `user_intent` explaining the connection check. A successful empty result is authenticated access, not failure. Permission, authentication and service errors remain distinct from an empty search.
- Tool presence plus read-only access establishes the connection only. It does not establish Magic Layers entitlement, remaining quota or reconstruction quality. Never invoke `image_to_design` as a probe. Respect a user's no-reconstruction/no-quota instruction even if connection checks succeeded.

## 2. Per-page Magic Layers

Consume only the canonical Formal Text-Clean Render after Stage 3 text-preparation checks pass. Original text-bearing Approved Renders are not the formal input.

Use `image_to_design(image_file=<absolute formal text-clean PNG>, title=<slide_id plus short source revision>, user_intent=<reconstruct editable visual layers>)`. Use the actual host schema. Do not pass a local path as a public URL. One call takes one image and starts a new design; three pages require three independent calls. Do not promise a batch call or exact quota price.

Before destructive cleanup, finalize the page's Text Manifest and Removal Inventory and register the current Stage 3 Text Plan:

```text

## Stage 2 formal visual approval prerequisite

Before any `register-text-plan` or `register-text-clean` call, Stage 2 must have a current Formal Display Set that was actually shown to the user and explicitly approved. `canva_bridge.py status` reports `AWAITING_USER_VISUAL_APPROVAL` when all current Approved Renders exist but that exact set is not approved; it must not infer approval from image generation success or Candidate history.

python scripts/canva_bridge.py register-text-plan --state <state> --slide-id S001 --manifest <finalized-manifest.json> --inventory <removal-inventory.json>
```

This command validates representation/treatment decisions against the current Final Content Truth. It blocks large-text heuristics from silently creating `preserve_as_graphic`, requires all four Graphic Typography evidence flags for protected graphic typography, and refuses high-impact unresolved text-like regions. A changed plan invalidates old Text-Clean and downstream reconstruction artifacts.

After the registered Text Plan is current and the canonical cleanup/integrity checks pass, register the formal PNG against the current approved source:

```text
python scripts/canva_bridge.py register-text-clean --state <state> --slide-id S001 --artifact <absolute formal text-clean PNG>
```

This replaces the generic `text_clean:S001` registration. It requires the current page's Approved Render, Final Content Truth, canvas, text reconciliation and current validated Stage 3 Text Plan; it does not add an all-pages handoff requirement to registration. The existing begin-attempt handoff gate still requires all pages. Success returns `TEXT_CLEAN_REGISTERED` and exit 0; failures return BLOCKED and exit 1 without committing state.

The binding stores `slide_id`, `run_id`, `approved_outline_fingerprint`, `source_fingerprint`, `text_clean_fingerprint` and the actual `registration` record under `canva_bridge.text_preparation`. Source, run, clean or registration changes invalidate it; an equivalent canvas mapping at another path remains valid. `--rebuild` cannot bypass this check. Registration changes neither the current attempt/design nor its retry budget, and never creates a quality PASS. Previous bindings are archived on re-registration and run rollover.

Legacy Codex tasks without this binding stop for actual local verification of the current formal PNG against its approved source; only then run the registration command. Do not infer historic proof automatically. If current fingerprints still match, reuse the existing design/download/page records. If they differ, old results remain invalid. An unresolved PENDING attempt stays blocked or waiting for diagnosis; registration does not authorize a second call. The external adapter route keeps its original registration behavior.

Before an authorized formal call, run:

```text
python scripts/canva_bridge.py begin-attempt --state <state> --slide-id S001
```

This records a unique `attempt_id` with current run/source/clean identity and PENDING status. Completed older files stay on disk but cannot enter current delivery. `--rebuild` is permitted only for an explicitly authorized new reconstruction or canonical structural recovery. An unresolved PENDING attempt blocks another begin, including with this flag. A normal resume inspects the original job/result rather than issuing another call.

After the real result arrives, perform canonical Structural Reconstruction Assessment. Create result JSON containing the returned `attempt_id`, `slide_id`, `source_fingerprint`, `text_clean_fingerprint` from begin, the actual `design_id`, `assessment` and concrete `evidence`. Use only canonical assessment states: ACCEPT, RETRY_ONCE, ASSISTED_CLEANUP_REQUIRED, RETURN_TO_STAGE_2.

```text
python scripts/canva_bridge.py accept-attempt --state <state> --slide-id S001 --attempt-id <id> --result <actual-result.json>
```

Despite its name, this command records the real assessment; only ACCEPT authorizes acquisition. Structural retry uses the existing available/pending/consumed rules; it does not add quota or retry on its own. Unknown completion or a timeout without terminal evidence leaves PENDING for diagnosis. An explicitly confirmed terminal tool failure follows the recovery section below. A recorded assisted result may be reassessed after one actual local correction; an unchanged unresolved result stops further cleanup. The helper writes attempt metadata and registers it through the existing runtime mechanism. Do not register a different attempt behind this bridge.

### Confirmed tool failure and recovery

If the tool explicitly reports terminal failure without any assessable design, record it with `accept-attempt` using result JSON containing the current `attempt_id`, `slide_id`, `source_fingerprint`, `text_clean_fingerprint`, `assessment` equal to the actual `MAGIC_LAYERS_EXECUTION_FAILED` or `MAGIC_LAYERS_TOOL_UNAVAILABLE` code, `terminal_confirmed: true`, and nonempty actual terminal-error `evidence`. Do not invent a design ID. An ambiguous timeout cannot be marked terminal. This records TOOL_FAILED and leaves the structural retry budget unchanged.

After actual environment repair (and read-only connection checks where relevant), write recovery JSON with that failed `attempt_id`, its exact `failure_code`, `terminal_confirmed: true`, and `change_evidence` describing the observed repair. Only when a new formal call is authorized run:

```text
python scripts/canva_bridge.py begin-attempt --state <state> --slide-id S001 --rebuild --recovery-evidence <actual-repair.json>
```

The command creates one new PENDING attempt; it does not call Canva. Missing/mismatched repair evidence blocks. Unknown PENDING attempts still cannot be restarted. No automatic retry, credential collection or structural budget reset is added.

## 3. Browser acquisition and local finalizer — single runtime truth

This route begins only from the current `WAIT_DOWNLOAD` ACCEPT identity. The browser UI remains a Codex Host action; local Python does not pretend to expose a browser API. `scripts/acquisition_request.py`, `scripts/host_acquisition.py`, the unchanged PowerShell finalizer and `canva_bridge.py` only validate identity, persist intent/evidence, locate the exact browser download and bind lineage.

The installed Skill is a **READ-ONLY PRODUCT** during execution. The Controller may repair a Browser session, reopen the same Design, re-observe UI, refresh readonly connector evidence, wait for files, or resume finalizer/bind on the same exact bytes. It must not edit `SKILL.md`, `references/`, production scripts, tests or manifest. If bounded recovery points to a product defect, preserve the checkpoint/evidence and report `IMPLEMENTATION_DEFECT_SUSPECTED`.

### 3.1 Preflight and trusted request

Obtain current readonly `get_design` evidence for the already accepted `design_id`, confirm one page, and create the existing acquisition request. The host report is intentionally download-stage only: it does **not** re-prove Magic Layers availability and does not preselect the browser's actual download directory.

```json
{
  "schema_version": 1,
  "route": "codex-canva",
  "checked_at": "<actual ISO UTC time>",
  "slide_id": "S001",
  "attempt_id": "<current bridge attempt ID>",
  "design_id": "<current accepted design ID>",
  "source_fingerprint": "<current source digest>",
  "text_clean_fingerprint": "<current clean digest>",
  "checks": {
    "connector_readonly": "PASS",
    "browser_session": "PASS",
    "pptx_option": "PASS"
  },
  "evidence": {
    "connector_readonly": "<successful readonly response>",
    "browser_session": "<observed current design, not a login page>",
    "pptx_option": "<observed PowerPoint/PPTX option>"
  }
}
```

Run acquisition preflight against the current runtime state:

```text
python scripts/preflight.py --skill-dir . --output-dir <project-work/graphics-first> --scope acquisition --acquisition-route codex-canva --host-report <host.json> --runtime-state <state> --slide-id S001
```

Stale/temporarily unavailable Browser or readonly evidence is recoverable: refresh it and resume. Missing authorization/login is `USER_ACTION_REQUIRED`. Identity, lineage or provenance mismatch is a Hard STOP. A simple public-page browser probe such as `example.com` is troubleshooting only when Browser Host initialization itself is suspect; it is not part of normal acquisition.

Create/reuse the local acquisition record before UI work. Here `--download-target-dir` is the **finalizer output** directory; it is not a demand that the browser download there:

```text
python scripts/host_acquisition.py prepare --record <record.json> --state <state> --slide-id S001 --lookup <trusted-get-design.json> --download-target-dir <project-work/graphics-first> --target-filename <unique-single-page.pptx>
```

### 3.1a Candidate DOM/event strategy with original observation fallback

Default to the candidate strategy only if current Host documentation exposes supported DOM locators and download events. Establish visible locator ground truth and validate unique/visible/enabled controls. Combine deterministic actions and fresh, preferably local state checks; do not blindly chain unobserved menus. The original complete AX/DOM observation, necessary screenshot, supported browser actions and bounded recovery route remains available.

Select/audit through the existing prepare command using optional `--host-strategy dom_event` or `--host-strategy legacy_observation --fallback-reason <actual observed reason>`. Old calls without these options retain their behavior. Strategy changes do not change identity, intent, numbering or retry counters. Retry reservations and strategy auditing are separate prepare operations.

Fallback timing:
- Before lock: absent capability, or a locator still ambiguous after one fresh state check -> original UI observation/actions within the same UI budget.
- After lock: listener failure, timeout, session reset, unavailable path or uncertain click -> original OBSERVATION AND RECOVERY ONLY. Never start another event/click sequence or unlock.
- Exact bytes already exist: repair finalizer/bind on the same file; never export again.
- Auth, identity and provenance problems cannot be bypassed by either strategy.

Persist the original lock immediately before the final Host call. Within ONE `cua_repl` call, first subscribe, then issue the single Download click and await both. Do not leave an unfinished listener in a previous tool call: a real microtest encountered timeout/kernel reset. The current verified Host uses a 55-second event timeout inside a 60-second call; other Hosts require explicitly documented limits, with the event timeout strictly shorter than the tool limit. Never loop additional event waits. Example after a fresh, grounded Download locator has been established:

```javascript
const eventWait = tab.playwright.waitForEvent('download', {timeoutMs:55000});
const result = await Promise.allSettled([eventWait, downloadControl.click()]);
// Event success: obtain download.path(), then correlate original History/file proof.
// Any unknown click or event timeout: same locked record, observation only.
```

The timeout value is a bounded first completion check, not a new retry budget. If a retry reservation was already consumed, its required wait is still honored; strategy switches never reset `.retries.json`. A completed event can proceed immediately to exact-file acquisition without an additional fixed sleep. On event timeout, inspect the existing operation and follow 3.3 recovery observations, not a new Download.

Canva's “completed” page message alone is NOT an actual Host file-download event. The original fallback must still obtain real Host download-event/notification evidence and exact History/file correspondence before `--event-confirmed`. A returned path alone cannot replace Design provenance, byte counts, one-page checks or SHA-256. Do not subscribe to an arbitrary next download after an uncertain click and treat it as this operation.

Validation status: one standalone real download confirmed this same-call strategy and unchanged finalizer. It did not exercise formal prepare/finish/bind wiring or every recovery branch; those require separate offline integration checks. No comparable speed baseline exists, so do not claim a speedup ratio.

### 3.2 Bounded pre-download retry

Query retry is only for transient readonly connector/network failure. UI retry is only for pre-final-Download page-not-ready/stale-locator/menu-not-ready conditions. Each reservation persists on the same record and survives a session restart.

```text
query: 2s -> 5s -> 10s -> 15s -> 20s
ui:    2s -> 5s -> 10s -> 15s -> 20s
```

Use:

```text
python scripts/host_acquisition.py prepare --state <state> --slide-id S001 --record <record.json> --retry-kind query
python scripts/host_acquisition.py prepare --state <state> --slide-id S001 --record <record.json> --retry-kind ui
```

Each successful reservation returns `wait_seconds`; the Controller must **actually wait** that interval before the corresponding re-query or UI re-observation. Do not consume several retry reservations back-to-back without the waits.

Authentication denial, permission denial, invalid evidence and identity mismatch are not transient retries. Each UI-changing action must be followed by fresh observation; never reuse a stale node.

### 3.3 Intent lock, one click, then observation

After the PowerPoint/PPTX choice is visibly ready, persist the final action intent with `lock` immediately before the one final UI click for this record:

```text
python scripts/host_acquisition.py lock --record <record.json>
```

One record owns one final Download intent forever; `.intent` is never deleted to make the same record clickable again. After `lock` succeeds, perform the actual Canva **Download** click once through the current Host UI.

After the final Download is issued, repeating the normal Download action and ordinary pre-download query/UI retry remain forbidden. If completion is not yet proven, reserve **observation only**:

`POST_CLICK_OBSERVE_DELAYS = (10, 20, 30, 45, 60)` seconds.

```text
immediate check
-> 10s
-> 20s
-> 30s
-> 45s
-> 60s
```

```text
python scripts/host_acquisition.py prepare --state <state> --slide-id S001 --record <record.json> --retry-kind observe
```

Use the returned `wait_seconds` and **actually wait** before the next Host/UI/file observation; the reservation itself is not an observation.

Each round asks only: is the export still running, visibly complete, represented by the exact download event/History/file, or independently confirmed as terminal export failure? Unknown/no event/no file is not terminal failure. A **single unknown / no-event / no-file** observation is never a STOP or user-handoff condition while the existing bounded recovery contract remains available. Five observation rounds exhausted -> diagnose/repair the runtime; do not click the normal Download again merely because the result is still unknown.

If a fresh Canva observation explicitly presents a **same-operation recovery affordance** for this already locked export (for example, a link equivalent to “if the download did not start, click here”), the Controller may use it when no matching download is running or completed, current identity/lineage/target are unchanged, and the action does not start a new export, reconstruction, authorization flow or other expensive remote task. This recovery action stays inside the current `INTENT_LOCKED` acquisition, **does not create a new numbered acquisition**, and **does not reset the existing post-click observation budget**. After every use, re-observe immediately. It may be used again only if a later scheduled fresh observation explicitly presents it again and no matching running/completed download exists; never rapid-click it or substitute the ordinary Download button.

### 3.4 Exact file proof and downstream resume

After an actual Host download event, determine the browser's **actual** profile and `Preferences.download.default_directory`, then correlate the same Design URL, intent time and Chromium History record. Only the exact `target_path` whose completed byte counts match is accepted. Normal downloads prove Design provenance by exact `tab_url == observed Design URL`. A same-operation recovery-link download may instead use the exact Chromium URL chain belonging to that same download record, but only when `tab_url` is blank/unavailable and a trusted HTTPS Canva URL in that chain unambiguously contains the current `design_id`; a nonblank mismatched `tab_url`, missing chain evidence, other-design evidence or ambiguity still fails closed. Never guess a conventional Downloads folder, newest timestamp or similar filename.

The local helper may poll the already selected exact History record/file for file settling; this does not authorize a new export. Once the Host has produced a real download event and the browser has resolved the accepted Design to its actual `/design/<design_id>/...` URL, finish the same record:

```text
python scripts/host_acquisition.py finish --record <record.json> --state <state> --profile <actual-browser-profile> --observed-url <actual-resolved-design-url> --event-confirmed --python-executable <workflow-python>
```

`finish` locates the exact History/file evidence, calls the unchanged `canva_pptx_finalize.ps1`, retains its single-page validation and SHA-256, registers the trusted `/d/<token>` association from the captured connector lookup, and binds the same bytes to current lineage. `/d/<token>` is accepted only through independently captured trusted connector association; the download submitter cannot self-certify URL/Design identity.

Finalizer or bind failure keeps the ACCEPT attempt and exact file. Repair the downstream condition and rerun `finish` on the **same record/file**. It never justifies another Download or reconstruction.

### 3.5 Limited new export after terminal failure

A different numbered acquisition is allowed only when all facts are independently confirmed: current state is `WAIT_DOWNLOAD`; ACCEPT identity matches; the previous failure checkpoint is `EXPORT_FAILED`; terminal export failure is real; permissions are valid; sources are unambiguous; no export is running/possibly running; and no completed reusable file exists. The round permits at most five real Download intents total.

<!-- download-retry-gate -->
```python
consumed_download_slots = max(intent_count, actual_download_count)
retry_allowed = (
    0 < consumed_download_slots < 5
    and current_status == 'WAIT_DOWNLOAD'
    and identity_matches is True
    and terminal_failure_confirmed is True
    and required_permissions_ok is True
    and sources_unambiguous is True
    and operation_in_progress is False
    and completed_file_available is False
    and failure_checkpoint == 'EXPORT_FAILED'
)
next_download_number = consumed_download_slots + 1 if retry_allowed else None
```

Records are `<attempt>.json`, then `-download-02.json` through `-download-05.json`. A new terminal-failure-authorized record receives a fresh local query/UI/observe budget; the previous record's retry counts are **not** carried into the new export. Within one record, consumed reservations remain consumed across restart. If completed bytes later appear for an older record, resume that original record rather than creating/continuing a new export.

### 3.6 Failure classification

The Controller uses: `RECOVER -> WAIT/RETRY -> DIAGNOSE -> RUNTIME REPAIR -> RESUME`. `USER_ACTION_REQUIRED` is limited to actual login/2FA/permission/OS approval. Hard STOP is reserved for identity/lineage/provenance ambiguity, unsafe overwrite/pollution risk, unavailable authorization, bounded recovery exhaustion with possible duplicate side effect, or `IMPLEMENTATION_DEFECT_SUSPECTED`.

### 3.7 Restore inputs and single-page sealing

For the Codex route, register `text_clean` through the existing bridge and `graphics_first_pptx` through `bind-download`. Register current `canvas`, `finalized_manifest` and `font_fallback` artifacts through the existing runtime entries. Continue Graphics-first neutrality, canvas tolerance and canonical Native Text Visual Fit. Save restored output at a new path, perform the four existing Hard Gates, then `seal-page`. Acquisition adds no new visual quality gate and never rewrites Content Truth.

### 3.8 Canvas during existing text restoration

References 06 §9.1 and 07 §12.4 remain authoritative. Use the local helpers in canva_bridge.py; no new normalization file, CLI or runtime stage is required:

```python
prs, mapping = bridge.prepare_canvas_mapping(download_path, canvas, registration, cleanup)
# Mapping registration binds download_sha256 + current text_clean_fingerprint.
# checks/evidence require same_framing, no_crop, no_expansion, no_rotation, no_relayout.
# cleanup binds download_sha256, removed_text_shape_ids and actual neutrality evidence.
for element in finalized_manifest['text_elements']:
    geometry = bridge.map_native_text_geometry(element, mapping['plan'])
    # Use bbox_emu and visible_glyph_height_pt in the existing Native Text Visual Fit.
    # Add ordinary live TextBoxes; do not mutate Final Content Truth or Manifest.
prs.save(new_restored_path)
mapping['restored_pptx_sha256'] = bridge.sha(new_restored_path)
review['canvas_mapping'] = mapping
# Complete actual four Hard Gates, persist the review, then existing seal-page.
```

Only new explicit-EMU canvas pages with export discrepancy require the adaptation proof. Existing legacy canvas representations/seals are not migrated. Seal recomputes from original bytes and the declared text-only cleanup; it rejects removed/reordered graphics, altered paths/media/relationships, additional non-text objects or a wrong target canvas. Retained graphics precede newly appended native text. Audit path/hash is stored in the existing validated-page binding and verified on later provenance checks.

### 3.9 Compact calling contracts

Read 3.1-3.6 before acquisition; read 3.7-3.10 with 06 sections 9-12 and 07 sections 12-19 before restoration/sealing. Refresh init/status and relevant failure rules on resume. This table describes existing APIs; it does not grant a new click, submit, cleanup or seal.

| Existing call | Inputs and result contract |
|---|---|
| `bridge.active_identity(state, slide_id)` | Only current ACCEPT returns seven fields: attempt_id, slide_id, run_id, approved_outline_fingerprint, source_fingerprint, text_clean_fingerprint, design_id. Preserve all seven unchanged. |
| `host.prepare(path, state_path, slide_id, lookup_path, target_dir, target_name, host_strategy=None, fallback_reason=None)` | Validates current WAIT_DOWNLOAD and readonly single-page lookup; target_dir is absolute and target_name a simple PPTX name. Existing record/intent and budgets survive resume/switch. Returns the current acquisition record; only observed READY plus successful lock permits the first normal click. |
| `host.lock(path)` | Persist exclusive intent before dispatch. Never infer permission from a timeout or delete the intent marker. |
| `host.finish(path, state_path, profile, observed_url, event_confirmed, python_executable=None, wait_seconds=120)` | Requires real Host evidence and matching History/file bytes; runs unchanged finalizer and bind. Failure reuses the same file and record, never exports again. Check the returned record/error rather than treating an event or Canva completion banner as a seal. |
| `bridge.prepare_canvas_mapping(download_pptx, canvas, registration=None, cleanup=None)` | Returns in-memory deck and mapping report; never overwrites the original. cleanup binds download_sha256, removed_text_shape_ids and evidence; only validated text-only boxes may be removed. Uniform mapping additionally needs current framing/source proof. |
| `bridge.map_native_text_geometry(element, plan)` | Returns bbox_emu and optional visible_glyph_height_pt; use both for existing Native Text Visual Fit. Does not change Manifest or fitting rules. |
| `bridge.verify_canvas_mapping(download_pptx, restored_pptx, canvas, report, expected_clean_fingerprint=None)` | Recomputes cleanup/mapping from original bytes and verifies retained objects/resources, native-only additions and output hash. |
| `bridge.seal_page(state_path, slide_id, pptx, gates_path)` | Requires current bound identities, Manifest/font fingerprint, actual four-gate PASS evidence and mapping report when applicable. Persist mapping report after ANY text cleanup, even unchanged_objects. Returns PAGE_SEALED; direct legacy sealing cannot supply Codex provenance. |

Execute scripts through their existing CLI or these existing Python functions. Do not load implementations just to discover arguments; inspect relevant functions only for an actual error or insufficient contract. Keep complete state/logs/XML in project work; return current state, key identity, result/errors and evidence path. Never truncate required human review views or omit failure evidence.

### 3.10 Readonly neutrality and original-object verification

Before any neutrality check, start from the exact hash-checked download_current file and capture its original objects. Do not inspect original shapes with .text, .text_frame or get_or_add_*: python-pptx can create empty txBody while reading. Query ONLY existing XML nodes, recursively including groups, without hiding off-canvas/hidden/transparent objects. The following inline example is not a new restoration module:

<!-- readonly-neutrality -->
```python
from pptx import Presentation
from lxml import etree
source_deck = Presentation(source_pptx)
source_slide = source_deck.slides[0]
original_shape_xml = [(shape.shape_id, etree.tostring(shape._element))
                      for shape in source_slide.shapes]
existing_text_nodes = [node.text or '' for shape in source_slide.shapes
                       for node in shape._element.xpath('.//a:t')]
```

Nonempty ordinary text invokes the existing 06 section9.2 treatment, not an automatic PASS. This checks only existing object text nodes, not raster glyphs, dynamic fields or related chart/SmartArt parts; associated content must be reviewed where present under existing neutrality/visual gates. No a:t is not comprehensive neutrality proof. Source-relative baseline is captured BEFORE inspection. Original source bytes, binding and locks remain unchanged. Safe local text-only cleanup must carry the bound download hash, removed shape IDs and actual evidence in the existing mapping report, including unchanged_objects mode. Frozen protected-graphic classification is not permission to delete or rewrite the plan.

Add and fit Manifest text boxes using the existing restoration operation; set restored canvas per unchanged 06/07 tolerance. Safe .text_frame access on the NEW text boxes is allowed. Save at a new restoration path; do not patch the frozen failed file or strip/filter empty txBody to excuse differences.

Reload the ORIGINAL bound download independently of the edited deck. With a declared cleanup/mapping, recompute the expected retained objects using the existing verifier; without that report, the strict original-object comparison permits neither deletion nor geometric change. Do not replace the source baseline with an edited file. Load canvas_mapping_review from the actual four-gate review canvas_mapping object and approved_canvas/current_text_clean_fingerprint from the current bound state. These checks do not replace Content Truth, font fit or visual review:

<!-- verify-original-objects -->
```python
from pptx import Presentation
from lxml import etree
from canva_bridge import verify_canvas_mapping
mapping_review = globals().get('canvas_mapping_review')
if mapping_review is not None:
    verify_canvas_mapping(source_pptx, restored_pptx, approved_canvas,
                          mapping_review, current_text_clean_fingerprint)
else:
    original = Presentation(source_pptx)
    restored = Presentation(restored_pptx)
    original_shape_xml = [(shape.shape_id, etree.tostring(shape._element))
                          for shape in original.slides[0].shapes]
    kept = list(restored.slides[0].shapes)[:len(original_shape_xml)]
    assert [(shape.shape_id, etree.tostring(shape._element)) for shape in kept] == original_shape_xml
```

Also verify original package hash/lineage unchanged, target restored canvas and exact Manifest native content. Structural PASS may only follow this ORIGINAL-file comparison; all visual/font gates remain separate and pending until actually reviewed.


## 4. Final ordered assembly

After every current restored page is sealed, run:

```text
python scripts/assemble_deck.py prepare --state <trusted-state.json> --work-dir <project-work/assembly-revision>
```

The new entry validates current design/download/restored-page binding as well as current seals and uses the existing `deck_order`; if absent, it adopts the current approved Stage 2 `page_order`. An empty/invalid explicit order is not silently replaced. Stale, missing, duplicate or unknown pages block. Native merge preflight is run only here, not during connection checking. A unique work directory prevents replacing a previous candidate.

Prepare calls the unchanged native merge engine and returns `AWAITING_DECK_VALIDATION`, a candidate and a `deck-review.json` template. It does not declare final delivery or auto-fill visual PASS.

If a registered valid candidate exists but its `deck-review.json` is missing after interruption, run:

```text
python scripts/assemble_deck.py recover-review --state <trusted-state.json>
```

Recovery checks candidate hash, trusted order and current page provenance, and writes only a PENDING template next to that candidate. It does not invoke PowerPoint, merge, change task state, or fill PASS. Existing pending/completed reports are never overwritten; changed/unregistered candidates and already validated decks are refused. The command returns `validation_report`; use that exact file. Prepare now writes its template before committing candidate state; ordinary write/commit failures remove only this operation's new candidate/template and leave task state unchanged. An unregistered orphan after abrupt process termination requires diagnosis rather than silent adoption.

The review must be a JSON object; `checks` and `evidence`, when present, must also be objects. Malformed types return a controlled FAIL before delivery or PASS registration.

Perform canonical Deck-Level Validation: inspect the candidate in PowerPoint/rendered previews and compare with the current validated single pages; check order/count, canvas, title hierarchy, fonts, recurring motifs, background family, page numbers/fixed elements, all page Hard Gates and editing ability. Fill each review check with PASS only when observed, plus nonempty concrete evidence. The report is bound to exact merged bytes, page order and the full per-page attempt/provenance set. Identical merged bytes after a design switch do not make an old report reusable. On failure, follow canonical source-page correction and remerge rules; do not patch final delivery or repeat unchanged actions.

Then run:

```text
python scripts/assemble_deck.py publish --state <trusted-state.json> --validation-report <completed deck-review.json> --output <project-outputs/deck.pptx>
```

Publish rechecks current seals, merged hash, current page provenance and review binding, refuses overwrite, copies the exact candidate to outputs and calls existing merge/deck seal functions. It preserves single-page sources. Its report contains the final path, hash, order and count. A PASS report is local recorded review evidence, not an automated substitute for the canonical visual inspection.

## Verification status and scope

The following paragraph records inherited baseline history, not a new release identifier or the complete current scope. Current revision scope and timestamp are in manifest.yaml; actual verification and unverified branches are recorded in the delivered validation report.

RC17 is based on the validated RC16.8 lineage and still requires independent Codex/live revalidation before stable release. Packaging alone does not prove account connection, Magic Layers, browser export or native merge. Protocol Baseline RC16 keeps the established Stage 1/2/3 architecture while making only the declared narrow changes: references 03/04 add poster/promotional Typography applicability, reference 07 clarifies acceptable native-text rendering variance, reference 06 receives pointer-only updates to 07 v1.5, the Skill adds bounded Operational Runtime Recovery guidance, and Host acquisition adds strict same-record recovery-link provenance without creating a second binding route. Merge/Assembly architecture remains unchanged.


## Runtime dispatch: provenance and final assembly

For design/download/restored-page binding, use the bridge commands in `docs/codex-canva-bridge.md`; direct legacy single-page sealing cannot establish Codex provenance. For Canva installation/connection guidance, the plugin Magic Layers entry, browser PPTX acquisition and the host preflight report, read [Codex Canva bridge](docs/codex-canva-bridge.md). The adapter supplies implementation wiring only; all current canonical protocols remain authoritative. The legacy external acquisition route remains available when explicitly selected. Never use Magic Layers as an authentication probe.

After all restored single pages have current four-gate seals, use `python scripts/assemble_deck.py prepare --state <trusted-state.json> --work-dir <project-work/assembly>`. This reads trusted page order and calls the existing native merge engine. Review the resulting candidate under canonical Deck-Level Validation, then use `python scripts/assemble_deck.py publish --state <trusted-state.json> --validation-report <deck-review.json> --output <project-outputs/deck.pptx>`. If a registered current candidate has lost its review template, run `python scripts/assemble_deck.py recover-review --state <state>`; this recreates only a PENDING template without merge or overwrite. Prepare is not final delivery; publish requires evidence-backed validation of the exact merged bytes.
