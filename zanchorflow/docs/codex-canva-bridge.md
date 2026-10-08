# Codex Canva host bridge — V1.0

Historical protocol baseline RC17 is source/compatibility information, not the current product version.

This file is the sole runtime exception under `docs/`. It connects existing Stage 3 operations to Codex tools; it does not redefine content, text treatment, structural assessment or any Hard Gate. The host uses its current tool schemas and supported browser controls. No standalone Python/PowerShell script can authenticate the Canva connector or click its web UI.

## 0. Initialize and resume

Run commands from the extracted Skill directory; no installation is necessary. Before `stage1-draft`, run `python scripts/canva_bridge.py init --state <project-work/state.json>`. New states contain `slides: {}` and the Codex route. Existing state is checked without modification; `--route external` applies only to a genuinely new external-adapter task, never as an escape from failed Codex provenance.

Run `python scripts/canva_bridge.py status --state <state>` before resuming. It reads current evidence and never calls tools or modifies state. `PREPARE_DECK` selects assembly even when `deck_order` is absent; `DECK_VALIDATION` selects candidate review; `COMPLETE` returns the validated delivery. Earlier page statuses identify the first unresolved page. An existing lock means running/interrupted operation: diagnose it, never automatically delete it or replay the same remote operation. The download identity lock permits recovery GETs, fresh-link reads and browser recovery clicks in the same acquisition; it does not permit a new Magic call. Only one writer may operate on a task; generic runtime registrations must not run concurrently with bridge/assembly commands.

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

After `begin-attempt`, run `canva_bridge.py register-upload --state <state> --slide-id <id> --artifact <actual registered Text-Clean PNG>`. Pass its exact `image_path` and `requested_title` to `image_to_design(image_file=..., title=..., user_intent=<reconstruct editable visual layers>)`. Preserve the actual call/result. Before accept-attempt, save a raw capture JSON `{tool, call_args, result}` where result is the actual returned MCP content/structured object, and run `register-upload-result --state <state> --slide-id <id> --result <raw-capture>`. The helper checks actual image_file/title and independently extracts the one returned design_id from design_id or design.id fields, including JSON text content. Accepted design_id must equal this extracted return; unknown result shapes are diagnosed without guessing or another Magic call. Legacy attempts without an upload observation retain their original result identity route. After ACCEPT, capture readonly `get_design` for the returned design_id and run `register-design-observation --state <state> --slide-id <id> --evidence <lookup.json>`. Returned titles are optional trace metadata: do not rename or render solely for download acceptance. Use the actual host schema. Do not pass a local path as a public URL. One call takes one image and starts a new design; three pages require three independent calls. Do not promise a batch call or exact quota price.

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

## 3. Browser acquisition — file completion and design identity

The installed Skill is a **READ-ONLY PRODUCT**. Controller runtime recovery never hot-edits production code. Acquisition requires current WAIT_DOWNLOAD and the existing ACCEPT seven-field identity. Browser actions belong to Host tools; Python only captures/checks local evidence. Stage 2, reconstruction quality, Text Manifest and four Hard Gates remain unchanged.

### 3.1 Identity and acquisition preparation

Preserve actual registered upload bytes -> raw Magic return -> current design_id -> current export -> owned received file. The seven-field active identity is mandatory. Readonly get_design confirms ID and one page; title may be absent or generic. design_id does not attest that remote content never changed: known edits/task switches require re-observation. Never spend Magic quota to repair downloading.

Run prepare with the current lookup, output directory and simple target filename. New records require transport_receipt; existing completed v1/v2 downloads retain their original checks. For interrupted legacy records preserve old evidence and prepare a new transport record only after verifying current identity; do not relabel old bytes. Register the current design observation before snapshot/direct. Reuse an already bound verified file.

### 3.2 Public browser export sequence

Use the existing tab, semantic controls and current Host tools: 文件 (may appear as ···) -> menu 下载 -> file-type selector -> select/scroll to PPTX if necessary -> panel 下载. Check the actual state after each action. Do not stop at a menu with 下载 visible. Establish the actual directory baseline via snapshot before ordinary export, then lock once before dispatch. The lock preserves identity, not a permanent ban on recovery. Observe actual file progress; if ordinary export already yielded a reliably associated valid file, finish it without another transfer.

A single unknown / no-event / no-file result is recoverable, not a permanent refusal. Events/History are optional. Export completion, file completion, source confirmation and DOWNLOAD_BOUND are distinct. Avoid fixed long event waits, repeated viewport resets and opening a new tab for every page.

### 3.3 Preferred direct transport

Read the actual current recovery link 如果下载没有开始，请点击这里. Check current page design_id and actual HTTPS export-download.canva.com URL containing the exact ID. Do not invent URLs, use another page's href, log signed queries, extract cookies or use the official export API.

Feed the signed href through stdin into:
python -B scripts/host_acquisition.py direct --record-detail compact --record <record> --state <state> --observed-url <current-edit-url> --work-dir <project-work> --network-timeout 30

The integrated action records a separate real GET, receives into a unique owned .part, checks response bytes/Content-Length when present, PPTX ZIP/required parts/page count and hash, closes it and atomically renames it. There is no post-stream stability sleep. It returns file_evidence on success or DIRECT_UNAVAILABLE plus browser fallback guidance on transport failure. URL read/validation or runtime capability failure also routes to browser; do not bypass permissions.

Standalone download_transport.py --design-id <id> --work-dir <work> --expected-pages <count> supports multiple pages, but its standalone receipt does not bind a formal reconstruction task. Formal acquisition/finalizer/bind still require one page. No fixed machine, browser object, IPC bridge or output drive is embedded. Scripts use standard library only.

### 3.4 Browser fallback and provenance

When direct is unavailable and no completed associated ordinary file exists, click the current recovery link. 点击这里 is an effective same-operation recovery affordance. If a supported Host link-download method returns the actual saved path, use that method on the observed link and capture the returned path without waiting for an event. Capture the current operation through supported Host tools and preserve an actual operation JSON for observe --operation-capture. Required fields: source="canva_host.download", seven-field identity, acquisition_id, operation_id, observed_url, action=normal|recovery; include the actual returned path, or exclusive_directory with directory_owned_by_operation only when actually established. If export_source is present it is recovery_url's sanitized current link metadata, never a signed URL. Capture real tool outcomes; never infer a path from a filename. A same-operation event_path can be auxiliary but is not mandatory.

Use snapshot --operation recovery --recovery-href - before recovery click, feeding href via stdin when readable; if the visible link cannot be read, the browser path/operation capture still works without href. observe --export-href - also accepts stdin. When export itself failed or a new current href needs regeneration and no file is progressing/complete, snapshot --operation export_retry records a fresh baseline for another ordinary panel Download within the same identity lock; capture action=normal. This is download recovery, not a new Magic reconstruction. Pass href in-memory to the function when available; do not expose signed links in shell arguments. observe polls actual file stats every 0.5s, requires three stable samples and validates/hashes only stable candidates. Old files, same names, duplicate suffixes, partials and multiple candidates are recorded. A skill lease coordinates its tasks; it cannot prevent unrelated downloads.

An actual operation path may identify one candidate among several. An exclusively owned empty-baseline directory can associate exactly one file when supported. A shared directory's single new file, a generic name or visual similarity is insufficient. Return FILE_SOURCE_PENDING with retained candidates; recover by getting a fresh link, supported isolated directory or actual download object. If no way to resolve remains, ask the user. Do not call it "no download" or restore forced name/visual checks.

### 3.5 Lightweight completion, finalization and recovery

Use finish with --file-evidence returned by direct/observe. Transport receipts, snapshot references, full identity, current design observation, file bytes/hash/one-page package and registered policy are verified before binding and downstream reuse. No mandatory name, core title, PowerPoint startup, preview or page_check on new receipt acquisitions. Preview remains an optional diagnostic; restoration's four existing Hard Gates remain unchanged.

New records retain schema_version=2 and add transport_receipt; policy is pinned in acquisition/state/binding. Missing, invalid, unregistered or changed receipts never fall back to old evidence. Historical completed evidence keeps its old rules. The finalizer moves the same bytes and verifies them; finalizer/bind failure resumes the exact file, including interrupted completed moves, rather than redownloading.

No fixed refusal budget. Snapshot/observation/probe calls do not count as actual GET/click attempts. For active progress, keep observing without duplicate transfer; for timeout/temporary network failure, short backoff and retry; for expired URL re-read current link; for damaged file re-acquire; for three repeated identical failures diagnose/change transport. If nothing progresses and no new recovery action exists, report retained files and ask. Do not loop blindly or spend new Magic quota. Existing legacy observation deadlines are per invocation, not permanent download bans. Identity/owned leases survive interruption; release all this acquisition's leases after bind or explicit termination, never another acquisition's leases. The explicit terminate action preserves files/evidence/intent, marks the acquisition terminated and releases owned leases. It is not an automatic reaction to failure; authorized restart prepares a new record, retaining the old policy in history.

Download recovery decision example (counts are logs, not refusal limits):

<!-- download-retry-gate -->
```python
retry_allowed = (
    current_status == 'WAIT_DOWNLOAD'
    and identity_matches is True
    and required_permissions_ok is True
    and operation_in_progress is False
    and completed_file_available is not None
    and not (completed_file_available is True and sources_unambiguous is True)
    and failure_checkpoint not in ('FINALIZER', 'BIND')
)
next_download_number = actual_download_count + 1 if retry_allowed else None
```

CLI preparation path:
```text
python -B scripts/preflight.py --skill-dir <skill> --scope acquisition --report <work/report.json>
python -B scripts/host_acquisition.py prepare --record-detail compact --record <record> --state <state> --slide-id <id> --lookup <lookup> --download-target-dir <out> --target-filename <name.pptx>
python -B scripts/host_acquisition.py snapshot --record-detail compact --record <record> --state <state> --download-dir <actual-dir> --observed-url <edit-url>
python -B scripts/host_acquisition.py lock --record-detail compact --record <record>
python -B scripts/host_acquisition.py finish --record-detail compact --record <record> --state <state> --observed-url <edit-url> --file-evidence <captured-proof>
```
An optional --event-confirmed reports a real event, never a requirement. wait_seconds bounds each observation call; actually wait only when current state warrants it. Ordinary execution treats the installed skill as a READ-ONLY PRODUCT; suspected product defects are IMPLEMENTATION_DEFECT_SUSPECTED, not permission to hot-edit.

### 3.6 Evidence and timing

Record real GET/normal click/recovery click separately; reserve_retry is diagnostic guidance, not a request counter or permission gate. Operation captures retain observed action/time and identity. Receipts preserve sanitized export source plus URL digest, actual path/bytes/hash/page count, request/operation identifiers, outcome and phase timings. Never persist full signed hrefs.

Report FILE_IN_PROGRESS, FILE_SOURCE_PENDING, FILE_COMPLETE and DOWNLOAD_BOUND accurately. Keep failed partials and receipts. Time browser actions, export waiting, transfer, validation and tool round trips separately with consistent endpoints. Current tests establish local feasibility, not universal speedup or cross-machine support. Operator missed clicks are operator errors, not site unreliability.

### 3.7 Restore inputs and single-page sealing

For the Codex route, register `text_clean` through the existing bridge and `graphics_first_pptx` through `bind-download`. Register current `canvas`, `finalized_manifest` and `font_fallback` artifacts through the existing runtime entries. Continue Graphics-first neutrality, canvas tolerance and canonical Native Text Visual Fit. Save restored output at a new path; for applicable uniform headings complete Reference 07's independent native-title postprocessing, then perform the four existing Hard Gates and `seal-page` against the final bytes. Acquisition adds no new visual quality gate and never rewrites Content Truth.

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
| `host.prepare(path, state_path, slide_id, lookup_path, target_dir, target_name, host_strategy=None, fallback_reason=None)` | Validates current WAIT_DOWNLOAD and readonly single-page lookup; target_dir is absolute and target_name a simple PPTX name. Existing record/intent and identity survive resume/switch; no refusal budget. Returns the current acquisition record; only observed READY plus successful lock permits the first normal click. |
| `host.lock(path)` | Persist exclusive intent before dispatch. Never infer permission from a timeout or delete the intent marker. |
| `host.finish(path, state_path, profile, observed_url, event_confirmed, python_executable=None, wait_seconds=120)` | Accepts optional event or new sealed file_evidence; validates current design/full identity, actual file bytes and registered transport receipt before the shared finalizer/bind. No mandatory event or History on the file-first route. Finalizer/bind failure reuses the same file; transfer failure follows state recovery. Check the returned record/error rather than treating an event or Canva completion banner as a seal. |
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

The new entry validates current design/download/restored-page binding as well as current seals and uses the existing `deck_order`; if absent, it adopts the current approved Stage 2 `page_order`. An empty/invalid explicit order is not silently replaced. Stale, missing, duplicate or unknown pages block. Native merge preflight is run only here, not during connection checking. --office-host auto (default) probes PowerPoint first, then KWPP.Application when unavailable; explicit powerpoint/wps tests only that host. The chosen application is passed to merge without a second selection probe. Probe exceptions, including document/application cleanup, remain diagnostic evidence; a successful WPS probe removes the failed PowerPoint attempt as a blocker, never relabels it PASS. Results record office_host/office_progid and diagnostics; private paths/process details belong in work only.

Standalone merge_pptx.py also accepts --office-host auto|powerpoint|wps. Its auto fallback covers application creation only, before importing actual inputs; use scoped preflight for full capability checks. Formal import/save/reopen/integrity failure never retries another application within the operation. Common Python dependency errors are diagnosed separately. WPS closes only owned documents and releases/recreates its KWPP handle before reopen, without a global Quit or process kill. Keep original input files, state/locks/budgets and existing outcomes; normal temporary candidate cleanup remains unchanged. Recover an existing valid candidate through recover-review without rerunning native merge. A unique work directory prevents replacing a previous candidate.

Prepare uses the existing native import/integrity pipeline with the application chosen by scoped preflight and returns `AWAITING_DECK_VALIDATION`, a candidate and a `deck-review.json` template. It does not declare final delivery or auto-fill visual PASS.

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


<!-- TITLE_POLICY_BEGIN -->
### Short heading-policy calls

New-task start-run accepts --title-choice-required; legacy calls stay unchanged. After approved Outline, use runtime.py stage2-title-policy --mode uniform|free --page-roles-json <work/roles.json> --message <actual-choice>. Use stage2-title-context --slide-id <id> before generation and carry its observed --title-contract-ref into candidate registration. Complete a normal-source stage2-title-bind automatically after PASS; no title review/reply endpoint exists. The authoritative payload is in Reference 03 Optional ordinary-page Title Contract, and native occurrence metadata in Reference 07. The adapter's status returns concise title_policy context only when this optional policy exists.
<!-- TITLE_POLICY_END -->

### Lightweight maintenance clarification

New Host CLI examples use --record-detail compact; omitted flags retain full legacy result mirrors. Compact keeps status, source/proof references, candidate paths, errors, observed file progress and the last operation in the authority record. Raw upload/return observations and pre-submit intent remain preserved, never synthesized.

Browser actions share one mapping: normal->normal, recovery->recovery, export_retry->normal. A valid complete candidate takes precedence over damaged candidates. Growing bytes/partial markers mean FILE_IN_PROGRESS; stable unreadable bytes without completion evidence mean FILE_UNVERIFIED. FILE_INVALID needs actual corresponding completion evidence. Stability alone is not EOF.

PPTX parsing is deduplicated only inside one operation using freshly read byte digests, not size/mtime/path cache. Independent consumers read/hash current bytes; finalization/registration boundaries remain. No persistent validation token authorizes a PASS.
