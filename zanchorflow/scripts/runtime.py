"""Minimal Protocol Baseline RC8 orchestration metadata. Canonical protocols remain authoritative."""
import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path


GATE_NAMES = ('content_truth', 'semantic_fidelity', 'functional_editability', 'visual_fidelity')
LINEAGE_FIELDS = ('source_fingerprint', 'text_clean_fingerprint', 'text_restore_fingerprint')
OUTLINE_FIELDS = ('page_task', 'title', 'core_expression', 'key_information',
                  'semantic_relation', 'acceptance_criteria')


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _hash_parts(*parts):
    h = hashlib.sha256()
    for part in parts:
        h.update(len(part).to_bytes(8, 'big'))
        h.update(part)
    return h.hexdigest()


def _file_sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def source_fingerprint(render_bytes, final_truth, canvas):
    return _hash_parts(render_bytes, _canonical(final_truth), _canonical(canvas))


def text_clean_fingerprint(text_clean_bytes):
    return hashlib.sha256(text_clean_bytes).hexdigest()


def text_restore_fingerprint(finalized_manifest, deck_font_fallback):
    return _hash_parts(_canonical(finalized_manifest), _canonical(deck_font_fallback))


def stage3_text_plan_fingerprint(finalized_manifest, removal_inventory):
    """Bind the destructive-cleanup plan to the exact manifest and inventory bytes-as-data."""
    return _hash_parts(_canonical(finalized_manifest), _canonical(removal_inventory))


def _truth_occurrence_map(final_truth, slide_id):
    if not isinstance(final_truth, dict) or final_truth.get('slide_id') != slide_id:
        raise ValueError('STAGE3_TEXT_PLAN_TRUTH_INVALID: slide_id mismatch')
    meaningful = final_truth.get('meaningful_text')
    if not isinstance(meaningful, list):
        raise ValueError('STAGE3_TEXT_PLAN_TRUTH_INVALID: meaningful_text list required')
    result = {}
    for index, item in enumerate(meaningful, 1):
        if isinstance(item, str):
            content, truth_ref = item, f'{slide_id}:T{index:03d}'
        elif isinstance(item, dict):
            content = item.get('text', item.get('content'))
            truth_ref = item.get('truth_ref') or f'{slide_id}:T{index:03d}'
        else:
            raise ValueError('STAGE3_TEXT_PLAN_TRUTH_INVALID: meaningful_text occurrence invalid')
        if not isinstance(content, str) or not content:
            raise ValueError('STAGE3_TEXT_PLAN_TRUTH_INVALID: occurrence content required')
        if not isinstance(truth_ref, str) or not truth_ref or truth_ref in result:
            raise ValueError('STAGE3_TEXT_PLAN_TRUTH_INVALID: truth_ref invalid or duplicate')
        result[truth_ref] = content
    return result


def _valid_normalized_bbox(value):
    return (isinstance(value, list) and len(value) == 4
            and all(isinstance(x, (int, float)) and 0 <= x <= 1 for x in value)
            and value[2] > 0 and value[3] > 0
            and value[0] + value[2] <= 1.000001 and value[1] + value[3] <= 1.000001)


def validate_stage3_text_plan(finalized_manifest, removal_inventory, final_truth, slide_id):
    """Validate representation-vs-treatment before any destructive text cleanup.

    Semantic/visual evidence is supplied by the agent; this function enforces that high-impact
    preservation/removal decisions cannot be represented by an internally contradictory plan.
    """
    if not isinstance(finalized_manifest, dict) or finalized_manifest.get('slide_id') != slide_id:
        raise ValueError('STAGE3_TEXT_PLAN_INVALID: manifest slide_id mismatch')
    if not isinstance(removal_inventory, dict) or removal_inventory.get('slide_id') != slide_id:
        raise ValueError('STAGE3_TEXT_PLAN_INVALID: inventory slide_id mismatch')
    elements = finalized_manifest.get('text_elements')
    items = removal_inventory.get('items')
    if not isinstance(elements, list) or not isinstance(items, list):
        raise ValueError('STAGE3_TEXT_PLAN_INVALID: text_elements/items lists required')
    truth = _truth_occurrence_map(final_truth, slide_id)
    allowed_treatments = {'remove_and_restore', 'remove_and_drop', 'preserve_as_graphic'}
    allowed_roles = {'native_text', 'graphic_typography', 'approved_graphic_asset'}
    by_id = {}
    preserved_graphic_typography = []
    for element in elements:
        if not isinstance(element, dict):
            raise ValueError('STAGE3_TEXT_PLAN_INVALID: manifest element must be object')
        element_id = element.get('id')
        if not isinstance(element_id, str) or not element_id or element_id in by_id:
            raise ValueError('STAGE3_TEXT_PLAN_INVALID: manifest id missing or duplicate')
        if not _valid_normalized_bbox(element.get('visual_bbox_normalized')):
            raise ValueError('STAGE3_TEXT_PLAN_INVALID: visual bbox invalid')
        treatment = element.get('treatment')
        role = element.get('representation_role')
        if treatment not in allowed_treatments or role not in allowed_roles:
            raise ValueError('STAGE3_TEXT_PLAN_INVALID: treatment/representation_role invalid')
        content = element.get('content')
        if not isinstance(content, str) or not content:
            raise ValueError('STAGE3_TEXT_PLAN_INVALID: manifest content required')
        truth_source = element.get('truth_source')
        truth_ref = element.get('truth_ref')
        if role == 'native_text':
            if treatment != 'remove_and_restore' or truth_source != 'stage2_final_content_truth':
                raise ValueError('STAGE3_NATIVE_TEXT_TREATMENT_INVALID')
            if truth.get(truth_ref) != content:
                raise ValueError('STAGE3_TEXT_PLAN_CONTENT_INVALID: native text does not match Content Truth')
        elif role == 'graphic_typography':
            if treatment != 'preserve_as_graphic' or truth_source != 'stage2_final_content_truth':
                raise ValueError('GRAPHIC_TYPOGRAPHY_TREATMENT_INVALID')
            if truth.get(truth_ref) != content:
                raise ValueError('GRAPHIC_TYPOGRAPHY_CONTENT_INVALID')
            evidence = element.get('graphic_typography_evidence')
            required = ('content_verified', 'design_approved', 'composition_critical',
                        'native_text_substitution_material_loss')
            if not isinstance(evidence, dict) or any(evidence.get(key) is not True for key in required):
                raise ValueError('GRAPHIC_TYPOGRAPHY_EVIDENCE_INCOMPLETE')
            preserved_graphic_typography.append(element_id)
        else:  # approved_graphic_asset
            if treatment != 'preserve_as_graphic' or truth_source != 'approved_graphic_asset':
                raise ValueError('PRESERVED_GRAPHIC_CONTENT_INVALID')
            evidence = element.get('approved_graphic_evidence')
            if (not isinstance(evidence, dict) or evidence.get('content_verified') is not True
                    or not isinstance(evidence.get('approval_ref'), str) or not evidence['approval_ref'].strip()):
                raise ValueError('PRESERVED_GRAPHIC_CONTENT_INVALID')
        by_id[element_id] = element

    linked = {element_id: 0 for element_id in by_id}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('region_id'), str):
            raise ValueError('STAGE3_TEXT_PLAN_INVALID: inventory region invalid')
        if not _valid_normalized_bbox(item.get('visual_bbox_normalized')):
            raise ValueError('STAGE3_TEXT_PLAN_INVALID: inventory bbox invalid')
        treatment = item.get('treatment')
        if treatment not in allowed_treatments:
            raise ValueError('STAGE3_TEXT_PLAN_INVALID: inventory treatment invalid')
        risk = item.get('destructive_cleanup_risk', 'low')
        if risk not in {'low', 'high'}:
            raise ValueError('STAGE3_TEXT_PLAN_INVALID: destructive cleanup risk invalid')
        links = item.get('linked_manifest_ids', [])
        if not isinstance(links, list) or any(link not in by_id for link in links):
            raise ValueError('STAGE3_TEXT_PLAN_INVALID: linked manifest id invalid')
        if risk == 'high' and treatment != 'preserve_as_graphic':
            raise ValueError('TEXT_TREATMENT_CONFLICT: high-impact text-like region cannot be destructively removed without resolution')
        if treatment in {'remove_and_restore', 'preserve_as_graphic'} and not links:
            raise ValueError('STAGE3_TEXT_PLAN_INVALID: retained/restored region requires manifest link')
        if treatment == 'remove_and_drop' and links:
            raise ValueError('STAGE3_TEXT_PLAN_INVALID: dropped region cannot link final manifest text')
        for link in links:
            if by_id[link]['treatment'] != treatment:
                raise ValueError('STAGE3_TEXT_PLAN_INVALID: region/manifest treatment mismatch')
            linked[link] += 1
    if any(count == 0 for count in linked.values()):
        raise ValueError('STAGE3_TEXT_PLAN_INVALID: manifest element has no source region')
    return {'status': 'PASS', 'preserved_graphic_typography': preserved_graphic_typography,
            'manifest_elements': len(elements), 'inventory_regions': len(items)}


def load_runtime_state(path):
    path = Path(path).resolve()
    state = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(state.get('slides'), dict):
        raise ValueError('runtime state has no slides mapping')
    state['_base_dir'] = str(path.parent)
    return state


def _state_path(state, value):
    p = Path(value)
    return p if p.is_absolute() else Path(state.get('_base_dir', '.')) / p


def _save_runtime_state(path, state):
    """Commit one complete runtime state; never expose a partial JSON write."""
    path = Path(path).resolve()
    data = {key: value for key, value in state.items() if key != '_base_dir'}
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix='.runtime-state-', suffix='.tmp', delete=False) as stream:
            temp_path = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, sort_keys=True, indent=2)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _read_outline(path):
    outline = json.loads(Path(path).read_text(encoding='utf-8'))
    pages = outline.get('slides') if isinstance(outline, dict) else None
    if not isinstance(outline, dict) or set(outline) != {'slides'} or not isinstance(pages, list) or not pages:
        raise ValueError('Stage 1 outline requires an ordered nonempty slides list')
    for page in pages:
        if not isinstance(page, dict) or set(page) != set(OUTLINE_FIELDS):
            raise ValueError('Stage 1 outline requires exactly six fields per page')
        if any(value is None or value == '' or value == [] for value in page.values()):
            raise ValueError('Stage 1 outline has an empty required field')
    return outline


def _outline_fingerprint(outline):
    return hashlib.sha256(_canonical(outline)).hexdigest()


def _current_outline(state):
    entry = state.get('stage1_outline')
    if not isinstance(entry, dict) or not entry.get('path'):
        raise ValueError('STAGE1_APPROVAL_REQUIRED: no current Stage 1 outline')
    outline = _read_outline(_state_path(state, entry['path']))
    return entry, outline, _outline_fingerprint(outline)


def _outline_review_view(outline):
    labels = {
        'page_task': '页面任务', 'title': '标题', 'core_expression': '核心表达',
        'key_information': '关键信息', 'semantic_relation': '语义关系',
        'acceptance_criteria': '验收要求',
    }
    lines = ['Stage 1 大纲审核版：请逐页审核全部内容，明确同意或提出修改。']
    for index, page in enumerate(outline['slides'], 1):
        lines.append(f'\n第 {index} 页')
        for field in OUTLINE_FIELDS:
            value = page[field]
            shown = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
            lines.append(f'{labels[field]}（{field}）：{shown}')
    return '\n'.join(lines)


def record_stage1_draft(runtime_state_path, outline_path):
    """Register a complete Stage 1 draft; approval never survives a new draft."""
    path = Path(runtime_state_path).resolve()
    outline_path = Path(outline_path).resolve()
    fingerprint = _outline_fingerprint(_read_outline(outline_path))
    state = load_runtime_state(path)
    state['stage1_outline'] = {
        'path': str(outline_path), 'status': 'review_pending',
        'outline_fingerprint': fingerprint, 'displayed_outline_fingerprint': None,
        'approval': None,
    }
    _save_runtime_state(path, state)
    return fingerprint


def present_stage1_review(runtime_state_path):
    """Return every semantic field for display and bind the displayed version."""
    path = Path(runtime_state_path).resolve()
    state = load_runtime_state(path)
    entry, outline, fingerprint = _current_outline(state)
    view = _outline_review_view(outline)
    entry.update(status='review_pending', outline_fingerprint=fingerprint,
                 displayed_outline_fingerprint=fingerprint, approval=None)
    _save_runtime_state(path, state)
    return view


def _seal_outline_approval(entry, fingerprint, mode):
    record = {'outline_fingerprint': fingerprint, 'status': 'approved',
              'approval_mode': mode, 'approval_id': uuid.uuid4().hex}
    entry.update(status='approved', outline_fingerprint=fingerprint, approval=record)
    return record


def _normalize_stage1_decision(decision):
    """Require the Agent's structured interpretation of the current human decision gate."""
    value = str(decision or '').strip().lower()
    allowed = {'approve', 'revise', 'rework', 'unclear'}
    if value not in allowed:
        raise ValueError('STAGE1_DECISION_REQUIRED: use approve|revise|rework|unclear')
    return value


def handle_stage1_reply(runtime_state_path, user_text, edits=None, decision=None):
    """Apply the Agent-resolved human intent while Runtime enforces live-review integrity."""
    decision = _normalize_stage1_decision(decision)
    path = Path(runtime_state_path).resolve()
    state = load_runtime_state(path)
    entry, outline, fingerprint = _current_outline(state)
    review_current = (entry.get('status') == 'review_pending'
                      and entry.get('displayed_outline_fingerprint') == fingerprint)

    if decision == 'rework':
        entry.update(status='stage1_revision', approval=None,
                     displayed_outline_fingerprint=None)
        _save_runtime_state(path, state)
        return {'status': 'stage1_revision'}

    if edits:
        if not review_current:
            raise ValueError('STAGE1_APPROVAL_REQUIRED: edits need the current displayed review')
        for edit in edits:
            page_number, field, value = edit['page'], edit['field'], edit['value']
            if not isinstance(page_number, int) or not 1 <= page_number <= len(outline['slides']):
                raise ValueError('invalid Stage 1 page edit')
            if field not in OUTLINE_FIELDS or value is None or value == '' or value == []:
                raise ValueError('invalid Stage 1 field edit')
            outline['slides'][page_number - 1][field] = value
        # Keep the original document until all requested patches validate.
        updated = _read_outline_from_value(outline)
        outline_path = _state_path(state, entry['path'])
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=outline_path.parent,
                                         prefix='.stage1-outline-', suffix='.tmp', delete=False) as stream:
            temp = Path(stream.name)
            json.dump(updated, stream, ensure_ascii=False, sort_keys=True, indent=2)
        try:
            os.replace(temp, outline_path)
        finally:
            if temp.exists():
                temp.unlink()
        new_fingerprint = _outline_fingerprint(updated)
        entry.update(outline_fingerprint=new_fingerprint, approval=None,
                     displayed_outline_fingerprint=new_fingerprint, status='review_pending')
        if decision == 'approve':
            record = _seal_outline_approval(entry, new_fingerprint, 'user_edited_and_approved')
            _save_runtime_state(path, state)
            return {'status': 'approved', 'approval': record,
                    'review_view': _outline_review_view(updated)}
        _save_runtime_state(path, state)
        return {'status': 'review_pending', 'review_view': _outline_review_view(updated)}

    if decision == 'approve' and review_current:
        record = _seal_outline_approval(entry, fingerprint, 'explicit_approval')
        _save_runtime_state(path, state)
        return {'status': 'approved', 'approval': record}
    return {'status': 'review_pending', 'review_view': _outline_review_view(outline)}


def accept_preapproved_outline(runtime_state_path, outline_path, user_instruction):
    """Seal a direct-use outline after the Agent has resolved explicit preapproval intent."""
    if not str(user_instruction or '').strip():
        raise ValueError('STAGE1_APPROVAL_REQUIRED: direct-use approval needs the actual user instruction')
    fingerprint = record_stage1_draft(runtime_state_path, outline_path)
    path = Path(runtime_state_path).resolve()
    state = load_runtime_state(path)
    entry = state['stage1_outline']
    record = _seal_outline_approval(entry, fingerprint, 'preapproved_supplied_outline')
    _save_runtime_state(path, state)
    return record

def _read_outline_from_value(outline):
    """Validate an edited in-memory outline without changing its field contract."""
    pages = outline.get('slides') if isinstance(outline, dict) else None
    if not isinstance(outline, dict) or set(outline) != {'slides'} or not isinstance(pages, list) or not pages or any(
            not isinstance(page, dict) or set(page) != set(OUTLINE_FIELDS)
            or any(value is None or value == '' or value == [] for value in page.values())
            for page in pages):
        raise ValueError('invalid edited Stage 1 outline')
    return outline


def require_stage2_entry(runtime_state_path):
    state = load_runtime_state(runtime_state_path)
    entry, _, fingerprint = _current_outline(state)
    approval = entry.get('approval')
    if not isinstance(approval, dict) or approval.get('status') != 'approved':
        raise ValueError('STAGE1_APPROVAL_REQUIRED: show and approve the current outline')
    if (entry.get('status') != 'approved'
            or approval.get('outline_fingerprint') != fingerprint
            or entry.get('outline_fingerprint') != fingerprint):
        raise ValueError('STAGE1_APPROVAL_STALE: outline changed after approval')
    if (approval.get('approval_mode') != 'preapproved_supplied_outline'
            and entry.get('displayed_outline_fingerprint') != fingerprint):
        raise ValueError('STAGE1_APPROVAL_STALE: approved version was not displayed')
    return fingerprint


def _stage2_page_set(outline, state=None):
    """Create the stable page set for one approved Stage 2 run."""
    trusted_order = state.get('deck_order') if isinstance(state, dict) else None
    if (isinstance(trusted_order, list) and len(trusted_order) == len(outline['slides'])
            and len(trusted_order) == len(set(trusted_order))
            and all(isinstance(x, str) and x for x in trusted_order)):
        order = list(trusted_order)
    else:
        order = [f'S{index:03d}' for index in range(1, len(outline['slides']) + 1)]
    pages = {slide_id: {'outline_index': index} for index, slide_id in enumerate(order, 1)}
    return order, pages


def _current_stage2_run(state, fingerprint=None):
    run = state.get('stage2_run')
    if not isinstance(run, dict):
        raise ValueError('STAGE2_RUN_REQUIRED: begin a current Stage 2 run first')
    if fingerprint is None:
        entry, _, fingerprint = _current_outline(state)
    approval = state.get('stage1_outline', {}).get('approval', {})
    if (run.get('approved_outline_fingerprint') != fingerprint
            or run.get('approval_id') != approval.get('approval_id')):
        raise ValueError('STAGE1_APPROVAL_STALE: begin a current Stage 2 run first')
    return run


def start_stage2_run(runtime_state_path, restart=False):
    """Start or resume the current Stage 2 run without silently clearing PASS state."""
    path = Path(runtime_state_path).resolve()
    fingerprint = require_stage2_entry(path)
    state = load_runtime_state(path)
    existing = state.get('stage2_run')
    approval_id = state['stage1_outline']['approval']['approval_id']
    if (not restart and isinstance(existing, dict)
            and existing.get('approved_outline_fingerprint') == fingerprint
            and existing.get('approval_id') == approval_id):
        return existing

    if isinstance(existing, dict):
        state.setdefault('stage2_history', []).append(existing)

    _, outline, _ = _current_outline(state)
    page_order, pages = _stage2_page_set(outline, state)
    record = {
        'approved_outline_fingerprint': fingerprint,
        'approval_id': approval_id,
        'run_id': uuid.uuid4().hex,
        'page_order': page_order,
        'pages': pages,
        'artifacts': {},
        'candidates': {},
        'candidate_seq': 0,
        'anchor_candidate_displays': {},
        'current_approved': {},
        'pending_visual_revisions': [],
        'displayed_visual_fingerprint': None,
        'visual_approval': None,
        'visual_approval_history': [],
        'text_reconciliation': {},
    }
    state['stage2_run'] = record
    _save_runtime_state(path, state)
    return record


def _parse_page_artifact_kind(kind):
    if ':' not in kind:
        return kind, None
    base, slide_id = kind.split(':', 1)
    return base, slide_id




def _invalidate_page_artifacts(run, state, slide_id, preserve=()):
    """Archive current page-scoped derived artifacts after an upstream page change."""
    preserve = set(preserve)
    artifacts = run.setdefault('artifacts', {})
    for key in list(artifacts):
        base_kind, key_slide_id = _parse_page_artifact_kind(key)
        if key_slide_id != slide_id or base_kind in preserve:
            continue
        old = artifacts.pop(key)
        run.setdefault('artifact_history', {}).setdefault(key, []).append(old)
        state.setdefault('slides', {}).setdefault(slide_id, {}).pop(base_kind, None)
    run.setdefault('text_reconciliation', {}).pop(slide_id, None)

def register_stage2_artifact(runtime_state_path, kind, artifact_path):
    """Register non-render Stage 2/3 artifacts bound to the current approved run."""
    path = Path(runtime_state_path).resolve()
    fingerprint = require_stage2_entry(path)
    state = load_runtime_state(path)
    run = _current_stage2_run(state, fingerprint)
    base_kind, slide_id = _parse_page_artifact_kind(kind)
    if base_kind == 'approved_render':
        raise ValueError('STAGE2_APPROVED_RENDER_REQUIRES_PASS: promote a reviewed candidate instead')
    if slide_id is not None and slide_id not in run.get('page_order', []):
        raise ValueError(f'STAGE2_PAGE_NOT_CURRENT: {slide_id}')

    artifact_path = Path(artifact_path).resolve()
    if not artifact_path.is_file():
        raise ValueError(f'STAGE2_ARTIFACT_MISSING: {artifact_path}')

    if base_kind == 'final_content_truth':
        if slide_id is None:
            raise ValueError('STAGE2_PAGE_NOT_CURRENT: Final Content Truth requires slide_id')
        if current_stage2_approved_render(runtime_state_path, slide_id) is None:
            raise ValueError('STAGE2_APPROVED_RENDER_REQUIRED: approve the page before Final Content Truth')
        try:
            truth = json.loads(artifact_path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError('STAGE2_FINAL_CONTENT_TRUTH_INVALID: expected JSON') from exc
        if (not isinstance(truth, dict) or truth.get('slide_id') != slide_id
                or not isinstance(truth.get('meaningful_text'), list)
                or not isinstance(truth.get('exact_facts'), list)):
            raise ValueError('STAGE2_FINAL_CONTENT_TRUTH_INVALID: slide_id/meaningful_text/exact_facts required')

    record = {
        'path': str(artifact_path),
        'sha256': _file_sha256(artifact_path),
        'approved_outline_fingerprint': fingerprint,
        'run_id': run['run_id'],
    }
    old = run.setdefault('artifacts', {}).get(kind)
    if old is not None:
        run.setdefault('artifact_history', {}).setdefault(kind, []).append(old)
    run['artifacts'][kind] = record
    if slide_id is not None:
        state.setdefault('slides', {}).setdefault(slide_id, {})[base_kind] = str(artifact_path)
    if base_kind == 'final_content_truth':
        _invalidate_page_artifacts(run, state, slide_id, preserve={'final_content_truth'})
    _save_runtime_state(path, state)
    return record


def _image_kind(path):
    header = Path(path).read_bytes()[:16]
    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if header.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    if header.startswith((b'GIF87a', b'GIF89a')):
        return 'gif'
    if header.startswith(b'RIFF') and header[8:12] == b'WEBP':
        return 'webp'
    return None


def _latest_candidate_for_page(run, slide_id):
    candidates = [candidate for candidate in run.get('candidates', {}).values()
                  if candidate.get('slide_id') == slide_id]
    if not candidates:
        return None
    return max(candidates, key=lambda item: int(item.get('sequence', 0)))


def register_stage2_candidate(runtime_state_path, slide_id, artifact_path,
                              generation_intent, user_requested_variant=False):
    """Register one generated image as a candidate, never as an Approved Render."""
    path = Path(runtime_state_path).resolve()
    fingerprint = require_stage2_entry(path)
    state = load_runtime_state(path)
    run = _current_stage2_run(state, fingerprint)
    if slide_id not in run.get('page_order', []):
        raise ValueError(f'STAGE2_PAGE_NOT_CURRENT: {slide_id}')
    artifact_path = Path(artifact_path).resolve()
    if not artifact_path.is_file() or _image_kind(artifact_path) is None:
        raise ValueError('STAGE2_CANDIDATE_IMAGE_REQUIRED: candidate must be a supported image')
    current = current_stage2_approved_render(runtime_state_path, slide_id)
    if current is not None and not user_requested_variant:
        raise ValueError('STAGE2_PAGE_ALREADY_APPROVED: automatic generation must stop after PASS')
    intent = (generation_intent or '').strip()
    if not intent:
        raise ValueError('STAGE2_GENERATION_INTENT_REQUIRED')
    latest = _latest_candidate_for_page(run, slide_id)
    if (latest is not None and latest.get('status') == 'revise'
            and latest.get('generation_intent', '').strip() == intent):
        raise ValueError('STAGE2_UNCHANGED_RERUN: provide a new corrective delta before regenerating')

    candidate_id = uuid.uuid4().hex
    run['candidate_seq'] = int(run.get('candidate_seq', 0)) + 1
    record = {
        'sequence': run['candidate_seq'],
        'candidate_id': candidate_id,
        'slide_id': slide_id,
        'path': str(artifact_path),
        'sha256': _file_sha256(artifact_path),
        'image_kind': _image_kind(artifact_path),
        'generation_intent': intent,
        'user_requested_variant': bool(user_requested_variant),
        'status': 'candidate',
        'run_id': run['run_id'],
        'approved_outline_fingerprint': fingerprint,
    }
    run.setdefault('candidates', {})[candidate_id] = record
    _save_runtime_state(path, state)
    return record


def _normalize_review_notes(review_notes):
    if review_notes is None:
        return []
    if isinstance(review_notes, str):
        return [review_notes]
    if isinstance(review_notes, list) and all(isinstance(x, str) for x in review_notes):
        return review_notes
    raise ValueError('STAGE2_REVIEW_NOTES_INVALID')


def review_stage2_candidate(runtime_state_path, candidate_id, verdict,
                            failed_hard_gate=None, observable_evidence=None,
                            required_correction=None, replan_evidence=None, review_notes=None,
                            approval_mode='qualification_review'):
    """Qualification review: PASS by absence of evidenced H1-H4; no aesthetic scoring."""
    path = Path(runtime_state_path).resolve()
    fingerprint = require_stage2_entry(path)
    state = load_runtime_state(path)
    run = _current_stage2_run(state, fingerprint)
    candidate = run.get('candidates', {}).get(candidate_id)
    if not isinstance(candidate, dict):
        raise ValueError(f'STAGE2_CANDIDATE_NOT_FOUND: {candidate_id}')
    if candidate.get('status') != 'candidate':
        raise ValueError('STAGE2_CANDIDATE_ALREADY_REVIEWED')
    verdict = str(verdict).upper()
    if verdict not in {'PASS', 'REVISE', 'REJECT'}:
        raise ValueError('STAGE2_REVIEW_VERDICT_INVALID')
    notes = _normalize_review_notes(review_notes)

    review = {'verdict': verdict, 'review_notes': notes, 'approval_mode': approval_mode}
    if verdict in {'REVISE', 'REJECT'}:
        if (failed_hard_gate not in {'H1', 'H2', 'H3', 'H4'}
                or not str(observable_evidence or '').strip()
                or not str(required_correction or '').strip()):
            raise ValueError('STAGE2_REVIEW_EVIDENCE_REQUIRED: H1-H4, evidence and correction are mandatory')
        replan = str(replan_evidence or '').strip()
        if verdict == 'REVISE' and replan:
            raise ValueError('STAGE2_REVISE_CANNOT_CONTAIN_REPLAN_EVIDENCE')
        if verdict == 'REJECT' and not replan:
            raise ValueError('STAGE2_REJECT_REPLAN_EVIDENCE_REQUIRED')
        review.update(
            failed_hard_gate=failed_hard_gate,
            observable_evidence=str(observable_evidence).strip(),
            required_correction=str(required_correction).strip(),
        )
        if verdict == 'REJECT':
            review['replan_evidence'] = replan
        candidate['status'] = verdict.lower()
        candidate['review'] = review
        _save_runtime_state(path, state)
        return candidate

    if failed_hard_gate or observable_evidence or required_correction or replan_evidence:
        raise ValueError('STAGE2_PASS_CANNOT_CONTAIN_HARD_FAILURE')
    if approval_mode == 'anchor_exploration_candidate':
        candidate['status'] = 'qualified'
        candidate['review'] = review
        run.setdefault('anchor_candidate_displays', {}).pop(candidate['slide_id'], None)
        _save_runtime_state(path, state)
        return candidate
    slide_id = candidate['slide_id']
    old = run.setdefault('current_approved', {}).get(slide_id)
    if isinstance(old, dict) and old.get('candidate_id') != candidate_id:
        old_candidate = run.get('candidates', {}).get(old.get('candidate_id'))
        if isinstance(old_candidate, dict):
            old_candidate['status'] = 'superseded'
            old_candidate['superseded_by'] = candidate_id
    candidate['status'] = 'approved'
    candidate['review'] = review
    approved = {
        'slide_id': slide_id,
        'candidate_id': candidate_id,
        'path': candidate['path'],
        'sha256': candidate['sha256'],
        'approval_mode': approval_mode,
        'run_id': run['run_id'],
        'approved_outline_fingerprint': fingerprint,
    }
    run['current_approved'][slide_id] = approved
    pending = [sid for sid in run.get('pending_visual_revisions', []) if sid != slide_id]
    run['pending_visual_revisions'] = pending
    _invalidate_stage2_visual_approval(run, 'approved_render_changed')
    _invalidate_page_artifacts(run, state, slide_id)
    state.setdefault('slides', {}).setdefault(slide_id, {})['approved_render'] = candidate['path']
    _save_runtime_state(path, state)
    return candidate


def _anchor_candidate_set_fingerprint(slide_id, candidates):
    payload = {
        'slide_id': slide_id,
        'candidates': [
            {'candidate_id': item['candidate_id'], 'sha256': item['sha256']}
            for item in candidates
        ],
    }
    return hashlib.sha256(_canonical(payload)).hexdigest()


def build_anchor_formal_candidate_set(runtime_state_path, slide_id):
    """Return only current qualified Anchor candidates; never scan files/history."""
    fingerprint = require_stage2_entry(runtime_state_path)
    state = load_runtime_state(runtime_state_path)
    run = _current_stage2_run(state, fingerprint)
    if slide_id not in run.get('page_order', []):
        raise ValueError(f'STAGE2_PAGE_NOT_CURRENT: {slide_id}')
    candidates = []
    for candidate in sorted(run.get('candidates', {}).values(), key=lambda x: int(x.get('sequence', 0))):
        if candidate.get('slide_id') != slide_id or candidate.get('status') != 'qualified':
            continue
        review = candidate.get('review', {})
        if (review.get('verdict') != 'PASS'
                or review.get('approval_mode') != 'anchor_exploration_candidate'
                or candidate.get('run_id') != run.get('run_id')
                or candidate.get('approved_outline_fingerprint') != fingerprint):
            continue
        try:
            if candidate.get('sha256') != _file_sha256(_state_path(state, candidate['path'])):
                continue
        except (KeyError, OSError, ValueError, TypeError):
            continue
        candidates.append({
            'candidate_id': candidate['candidate_id'],
            'slide_id': slide_id,
            'path': candidate['path'],
            'sha256': candidate['sha256'],
            'sequence': candidate['sequence'],
        })
    result = {
        'status': 'COMPLETE' if candidates else 'INCOMPLETE',
        'slide_id': slide_id,
        'candidates': candidates,
    }
    if candidates:
        result['candidate_set_fingerprint'] = _anchor_candidate_set_fingerprint(slide_id, candidates)
    return result


def present_anchor_formal_candidates(runtime_state_path, slide_id):
    """Bind the exact qualified Anchor candidate set formally shown to the user."""
    path = Path(runtime_state_path).resolve()
    display = build_anchor_formal_candidate_set(path, slide_id)
    if display['status'] != 'COMPLETE':
        return display
    state = load_runtime_state(path)
    run = _current_stage2_run(state)
    run.setdefault('anchor_candidate_displays', {})[slide_id] = {
        'candidate_set_fingerprint': display['candidate_set_fingerprint'],
        'candidate_ids': [x['candidate_id'] for x in display['candidates']],
    }
    _save_runtime_state(path, state)
    return display


def select_anchor_candidate(runtime_state_path, slide_id, candidate_id):
    """Promote one formally displayed qualified Anchor candidate to the page render."""
    path = Path(runtime_state_path).resolve()
    fingerprint = require_stage2_entry(path)
    display = build_anchor_formal_candidate_set(path, slide_id)
    if display['status'] != 'COMPLETE':
        raise ValueError('ANCHOR_FORMAL_CANDIDATE_SET_REQUIRED: no qualified candidates')
    state = load_runtime_state(path)
    run = _current_stage2_run(state, fingerprint)
    shown = run.get('anchor_candidate_displays', {}).get(slide_id, {})
    if (shown.get('candidate_set_fingerprint') != display.get('candidate_set_fingerprint')
            or candidate_id not in shown.get('candidate_ids', [])):
        raise ValueError('ANCHOR_FORMAL_CANDIDATE_SET_STALE: show the current candidate set before selection')
    candidate = run.get('candidates', {}).get(candidate_id)
    if not isinstance(candidate, dict) or candidate.get('status') != 'qualified':
        raise ValueError('ANCHOR_CANDIDATE_NOT_QUALIFIED')

    old = run.setdefault('current_approved', {}).get(slide_id)
    if isinstance(old, dict) and old.get('candidate_id') != candidate_id:
        old_candidate = run.get('candidates', {}).get(old.get('candidate_id'))
        if isinstance(old_candidate, dict):
            old_candidate['status'] = 'superseded'
            old_candidate['superseded_by'] = candidate_id
    candidate['status'] = 'approved'
    candidate.setdefault('review', {})['approval_mode'] = 'user_selected_anchor_page'
    approved = {
        'slide_id': slide_id,
        'candidate_id': candidate_id,
        'path': candidate['path'],
        'sha256': candidate['sha256'],
        'approval_mode': 'user_selected_anchor_page',
        'run_id': run['run_id'],
        'approved_outline_fingerprint': fingerprint,
    }
    run['current_approved'][slide_id] = approved
    run.setdefault('anchor_candidate_displays', {}).pop(slide_id, None)
    pending = [sid for sid in run.get('pending_visual_revisions', []) if sid != slide_id]
    run['pending_visual_revisions'] = pending
    _invalidate_stage2_visual_approval(run, 'approved_render_changed')
    _invalidate_page_artifacts(run, state, slide_id)
    state.setdefault('slides', {}).setdefault(slide_id, {})['approved_render'] = candidate['path']
    _save_runtime_state(path, state)
    return approved


def current_stage2_approved_render(runtime_state_path, slide_id):
    try:
        fingerprint = require_stage2_entry(runtime_state_path)
        state = load_runtime_state(runtime_state_path)
        run = _current_stage2_run(state, fingerprint)
        if slide_id not in run.get('page_order', []):
            return None
        approved = run.get('current_approved', {}).get(slide_id)
        if not isinstance(approved, dict):
            return None
        candidate = run.get('candidates', {}).get(approved.get('candidate_id'))
        if (not isinstance(candidate, dict) or candidate.get('status') != 'approved'
                or approved.get('run_id') != run.get('run_id')
                or approved.get('approved_outline_fingerprint') != fingerprint
                or approved.get('sha256') != _file_sha256(_state_path(state, approved['path']))):
            return None
        return approved
    except (KeyError, OSError, ValueError, TypeError):
        return None


def stage2_artifact_current(runtime_state_path, kind):
    base_kind, slide_id = _parse_page_artifact_kind(kind)
    if base_kind == 'approved_render':
        return slide_id is not None and current_stage2_approved_render(runtime_state_path, slide_id) is not None
    try:
        fingerprint = require_stage2_entry(runtime_state_path)
        state = load_runtime_state(runtime_state_path)
        run = _current_stage2_run(state, fingerprint)
        if slide_id is not None and slide_id not in run.get('page_order', []):
            return False
        record = run.get('artifacts', {}).get(kind, {})
        return (record.get('approved_outline_fingerprint') == fingerprint
                and record.get('run_id') == run.get('run_id')
                and record.get('sha256') == _file_sha256(_state_path(state, record['path'])))
    except (KeyError, OSError, ValueError, TypeError):
        return False


def _invalidate_stage2_visual_approval(run, reason):
    approval = run.pop('visual_approval', None)
    if isinstance(approval, dict):
        archived = dict(approval)
        archived['invalidation_reason'] = reason
        run.setdefault('visual_approval_history', []).append(archived)
    run['displayed_visual_fingerprint'] = None


def _stage2_display_fingerprint(page_order, renders):
    payload = {
        'page_order': list(page_order),
        'renders': [
            {'slide_id': item['slide_id'], 'sha256': item['sha256']}
            for item in renders
        ],
    }
    return hashlib.sha256(_canonical(payload)).hexdigest()


def build_stage2_formal_display_set(runtime_state_path):
    """Derive the only formal Stage 2 review set from current Approved Renders."""
    fingerprint = require_stage2_entry(runtime_state_path)
    state = load_runtime_state(runtime_state_path)
    run = _current_stage2_run(state, fingerprint)
    pending = set(run.get('pending_visual_revisions', []))
    renders = []
    missing = []
    for slide_id in run.get('page_order', []):
        approved = current_stage2_approved_render(runtime_state_path, slide_id)
        if approved is None or slide_id in pending:
            missing.append(slide_id)
            continue
        renders.append({
            'slide_id': slide_id,
            'candidate_id': approved['candidate_id'],
            'path': approved['path'],
            'sha256': approved['sha256'],
            'approval_mode': approved.get('approval_mode'),
        })
    complete = not missing and len(renders) == len(run.get('page_order', []))
    result = {
        'status': 'COMPLETE' if complete else 'INCOMPLETE',
        'page_order': list(run.get('page_order', [])),
        'renders': renders,
        'missing': missing,
    }
    if complete:
        result['display_set_fingerprint'] = _stage2_display_fingerprint(run['page_order'], renders)
    return result


def present_stage2_formal_display(runtime_state_path):
    """Bind the exact complete formal set shown to the user."""
    path = Path(runtime_state_path).resolve()
    display = build_stage2_formal_display_set(path)
    if display['status'] != 'COMPLETE':
        return display
    state = load_runtime_state(path)
    run = _current_stage2_run(state)
    run['displayed_visual_fingerprint'] = display['display_set_fingerprint']
    _save_runtime_state(path, state)
    return display


def seal_stage2_visual_approval(runtime_state_path, user_text):
    """Approve only the exact complete set that was formally displayed."""
    path = Path(runtime_state_path).resolve()
    display = build_stage2_formal_display_set(path)
    if display['status'] != 'COMPLETE':
        raise ValueError('STAGE2_VISUAL_APPROVAL_REQUIRED: formal display set is incomplete')
    state = load_runtime_state(path)
    run = _current_stage2_run(state)
    display_fp = display['display_set_fingerprint']
    if run.get('displayed_visual_fingerprint') != display_fp:
        raise ValueError('STAGE2_VISUAL_APPROVAL_REQUIRED: current formal display set was not shown')
    if not str(user_text or '').strip():
        raise ValueError('STAGE2_VISUAL_APPROVAL_REQUIRED: actual user reply required')
    record = {
        'status': 'approved',
        'display_set_fingerprint': display_fp,
        'approval_id': uuid.uuid4().hex,
        'approval_mode': 'explicit_user_visual_approval',
    }
    run['visual_approval'] = record
    _save_runtime_state(path, state)
    return record


def require_stage2_visual_approval(runtime_state_path):
    """Return the current approved display fingerprint or block Stage 3."""
    path = Path(runtime_state_path).resolve()
    display = build_stage2_formal_display_set(path)
    if display['status'] != 'COMPLETE':
        raise ValueError('STAGE2_VISUAL_APPROVAL_REQUIRED: formal display set is incomplete')
    state = load_runtime_state(path)
    run = _current_stage2_run(state)
    approval = run.get('visual_approval')
    if not isinstance(approval, dict) or approval.get('status') != 'approved':
        raise ValueError('STAGE2_VISUAL_APPROVAL_REQUIRED: user has not approved the current formal display set')
    if approval.get('display_set_fingerprint') != display['display_set_fingerprint']:
        raise ValueError('STAGE2_VISUAL_APPROVAL_STALE: formal display set changed after user approval')
    return display['display_set_fingerprint']


def request_stage2_visual_revision(runtime_state_path, slide_ids):
    """Reopen only user-requested pages while preserving other current PASS renders."""
    path = Path(runtime_state_path).resolve()
    display = build_stage2_formal_display_set(path)
    state = load_runtime_state(path)
    run = _current_stage2_run(state)
    if display.get('status') != 'COMPLETE' or run.get('displayed_visual_fingerprint') != display.get('display_set_fingerprint'):
        raise ValueError('STAGE2_VISUAL_APPROVAL_REQUIRED: show the current formal display set before requesting revisions')
    if not isinstance(slide_ids, list) or not slide_ids or any(
            slide_id not in run.get('page_order', []) for slide_id in slide_ids):
        raise ValueError('STAGE2_VISUAL_REVISION_INVALID: use current slide ids')
    requested = set(run.get('pending_visual_revisions', [])) | set(slide_ids)
    run['pending_visual_revisions'] = [sid for sid in run.get('page_order', []) if sid in requested]
    _invalidate_stage2_visual_approval(run, 'user_requested_visual_revision')
    _save_runtime_state(path, state)
    return {'status': 'REVISION_PENDING', 'pending_revision_pages': list(run['pending_visual_revisions'])}


def build_text_clean_formal_display_set(runtime_state_path):
    """Derive Stage 3 formal Text-Clean display from current page-scoped artifacts only."""
    require_stage2_visual_approval(runtime_state_path)
    fingerprint = require_stage2_entry(runtime_state_path)
    state = load_runtime_state(runtime_state_path)
    run = _current_stage2_run(state, fingerprint)
    renders = []
    missing = []
    for slide_id in run.get('page_order', []):
        kind = f'text_clean:{slide_id}'
        if not stage2_artifact_current(runtime_state_path, kind):
            missing.append(slide_id)
            continue
        record = run.get('artifacts', {}).get(kind, {})
        renders.append({
            'slide_id': slide_id,
            'path': record['path'],
            'sha256': record['sha256'],
        })
    return {
        'status': 'COMPLETE' if not missing else 'INCOMPLETE',
        'page_order': list(run.get('page_order', [])),
        'renders': renders,
        'missing': missing,
    }


def stage2_visual_status(runtime_state_path):
    fingerprint = require_stage2_entry(runtime_state_path)
    state = load_runtime_state(runtime_state_path)
    run = _current_stage2_run(state, fingerprint)
    pending = set(run.get('pending_visual_revisions', []))
    missing = [slide_id for slide_id in run.get('page_order', [])
               if current_stage2_approved_render(runtime_state_path, slide_id) is None
               or slide_id in pending]
    return {'status': 'COMPLETE' if not missing else 'INCOMPLETE', 'missing': missing}


def list_current_stage2_approved(runtime_state_path):
    fingerprint = require_stage2_entry(runtime_state_path)
    state = load_runtime_state(runtime_state_path)
    run = _current_stage2_run(state, fingerprint)
    result = []
    for slide_id in run.get('page_order', []):
        approved = current_stage2_approved_render(runtime_state_path, slide_id)
        if approved is not None:
            result.append(dict(approved))
    return result


def mark_stage2_text_reconciled(runtime_state_path, slide_id):
    path = Path(runtime_state_path).resolve()
    fingerprint = require_stage2_entry(path)
    state = load_runtime_state(path)
    run = _current_stage2_run(state, fingerprint)
    approved = current_stage2_approved_render(runtime_state_path, slide_id)
    truth_kind = f'final_content_truth:{slide_id}'
    if approved is None or not stage2_artifact_current(runtime_state_path, truth_kind):
        raise ValueError('STAGE2_HANDOFF_INCOMPLETE: current Approved Render and Final Content Truth required')
    truth = run['artifacts'][truth_kind]
    record = {
        'slide_id': slide_id,
        'approved_render_sha256': approved['sha256'],
        'final_content_truth_sha256': truth['sha256'],
        'run_id': run['run_id'],
    }
    run.setdefault('text_reconciliation', {})[slide_id] = record
    _save_runtime_state(path, state)
    return record


def _stage2_reconciliation_current(runtime_state_path, slide_id):
    try:
        fingerprint = require_stage2_entry(runtime_state_path)
        state = load_runtime_state(runtime_state_path)
        run = _current_stage2_run(state, fingerprint)
        approved = current_stage2_approved_render(runtime_state_path, slide_id)
        truth_kind = f'final_content_truth:{slide_id}'
        if approved is None or not stage2_artifact_current(runtime_state_path, truth_kind):
            return False
        truth = run['artifacts'][truth_kind]
        record = run.get('text_reconciliation', {}).get(slide_id, {})
        return (record.get('run_id') == run.get('run_id')
                and record.get('approved_render_sha256') == approved.get('sha256')
                and record.get('final_content_truth_sha256') == truth.get('sha256'))
    except (KeyError, OSError, ValueError, TypeError):
        return False


def stage2_handoff_status(runtime_state_path):
    fingerprint = require_stage2_entry(runtime_state_path)
    state = load_runtime_state(runtime_state_path)
    run = _current_stage2_run(state, fingerprint)
    missing = []
    for slide_id in run.get('page_order', []):
        if (current_stage2_approved_render(runtime_state_path, slide_id) is None
                or not stage2_artifact_current(runtime_state_path, f'final_content_truth:{slide_id}')
                or not _stage2_reconciliation_current(runtime_state_path, slide_id)):
            missing.append(slide_id)
    return {'status': 'COMPLETE' if not missing else 'INCOMPLETE', 'missing': missing}

def expected_lineage_from_state(state, slide_id):
    """Recompute expected lineage from current approved upstream artifacts."""
    slide = state['slides'][slide_id]
    def read_json(key):
        return json.loads(_state_path(state, slide[key]).read_text(encoding='utf-8'))
    return {
        'slide_id': slide_id,
        'source_fingerprint': source_fingerprint(
            _state_path(state, slide['approved_render']).read_bytes(),
            read_json('final_content_truth'), read_json('canvas')),
        'text_clean_fingerprint': text_clean_fingerprint(_state_path(state, slide['text_clean']).read_bytes()),
        'text_restore_fingerprint': text_restore_fingerprint(read_json('finalized_manifest'), read_json('font_fallback')),
    }


def seal_validated_single_page(runtime_state_path, slide_id, pptx_path, gate_results):
    """Seal only after four Hard Gates; a stale prior seal may be superseded."""
    if not isinstance(gate_results, dict) or any(gate_results.get(gate) != 'PASS' for gate in GATE_NAMES):
        raise ValueError('four Hard Gates must all be PASS before sealing')
    state_path = Path(runtime_state_path).resolve()
    state = load_runtime_state(state_path)
    slide = state['slides'][slide_id]
    old_record = slide.get('validated_single_page')
    if old_record is not None:
        if not validate_current_artifact(old_record, state, slide_id):
            raise ValueError('current validated PPTX record is already sealed')
        slide.setdefault('superseded_validated_single_pages', []).append(old_record)
    pptx_path = Path(pptx_path).resolve()
    lineage = expected_lineage_from_state(state, slide_id)
    record = {
        **lineage, 'path': str(pptx_path), 'validated': True,
        'validated_pptx_sha256': _file_sha256(pptx_path),
    }
    slide['validated_single_page'] = record
    state.pop('_base_dir', None)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=state_path.parent,
                                     prefix='.runtime-state-', suffix='.tmp', delete=False) as stream:
        temp_path = Path(stream.name)
        json.dump(state, stream, ensure_ascii=False, sort_keys=True, indent=2)
    os.replace(temp_path, state_path)
    return record


def validate_current_artifact(record, state, slide_id):
    """Use the same sealed-artifact check for Resume and Merge entry."""
    errors = []
    if not isinstance(record, dict):
        return ['unsealed_validated_pptx']
    try:
        sealed = state['slides'][slide_id]['validated_single_page']
        expected = expected_lineage_from_state(state, slide_id)
    except (KeyError, OSError, ValueError, TypeError):
        return ['trusted_runtime_state_unavailable']
    if record.get('slide_id') != slide_id or sealed.get('slide_id') != slide_id:
        errors.append('slide_id_mismatch')
    if record.get('validated') is not True or sealed.get('validated') is not True:
        errors.append('four_gates_not_validated')
    for field in LINEAGE_FIELDS:
        if record.get(field) != expected[field] or sealed.get(field) != expected[field]:
            errors.append('stale_' + field)
    if record.get('path') != sealed.get('path'):
        errors.append('validated_pptx_path_mismatch')
    if not record.get('validated_pptx_sha256') or record.get('validated_pptx_sha256') != sealed.get('validated_pptx_sha256'):
        errors.append('validated_pptx_hash_mismatch')
    try:
        actual_hash = _file_sha256(_state_path(state, sealed['path']))
        if actual_hash != sealed.get('validated_pptx_sha256'):
            errors.append('validated_pptx_hash_mismatch')
    except (OSError, KeyError, TypeError):
        errors.append('validated_pptx_missing')
    return list(dict.fromkeys(errors))


def _current_deck_inputs(state, deck_order):
    """Read ordered identities from trusted current single-page records."""
    if not isinstance(deck_order, list) or not deck_order or not validate_deck_order(
            list(state['slides']), deck_order):
        raise ValueError('trusted_deck_order_invalid')
    ordered = []
    for slide_id in deck_order:
        record = state['slides'][slide_id].get('validated_single_page')
        if validate_current_artifact(record, state, slide_id):
            raise ValueError('single_page_artifact_changed')
        ordered.append({'slide_id': slide_id,
                        'validated_pptx_sha256': record['validated_pptx_sha256']})
    return ordered


def invalidate_merged_deck(runtime_state_path, deck_order, inputs):
    """Before output publication, atomically remove the old deck and validation."""
    state_path = Path(runtime_state_path).resolve()
    state = load_runtime_state(state_path)
    if state.get('deck_order') != deck_order:
        raise ValueError('deck_order_mismatch')
    ordered = _current_deck_inputs(state, deck_order)
    if [item.get('slide_id') for item in inputs] != deck_order:
        raise ValueError('deck_order_mismatch')
    if any(validate_current_artifact(item, state, item['slide_id']) for item in inputs):
        raise ValueError('single_page_artifact_changed')
    if ordered != [{'slide_id': item['slide_id'],
                    'validated_pptx_sha256': item['validated_pptx_sha256']} for item in inputs]:
        raise ValueError('single_page_artifact_changed')
    state.pop('merged_deck', None)
    state.pop('validated_deck', None)
    _save_runtime_state(state_path, state)


def seal_merged_deck(runtime_state_path, deck_order, inputs, merged_pptx_path):
    """Seal only the already verified and published merge output."""
    state_path = Path(runtime_state_path).resolve()
    state = load_runtime_state(state_path)
    if state.get('deck_order') != deck_order:
        raise ValueError('deck_order_mismatch')
    ordered = _current_deck_inputs(state, deck_order)
    if [item.get('slide_id') for item in inputs] != deck_order:
        raise ValueError('deck_order_mismatch')
    if any(validate_current_artifact(item, state, item['slide_id']) for item in inputs):
        raise ValueError('single_page_artifact_changed')
    if ordered != [{'slide_id': item['slide_id'],
                    'validated_pptx_sha256': item['validated_pptx_sha256']} for item in inputs]:
        raise ValueError('single_page_artifact_changed')
    merged_path = Path(merged_pptx_path).resolve()
    record = {
        'deck_order': list(deck_order),
        'slide_inputs': ordered,
        'merged_pptx_path': str(merged_path),
        'merged_pptx_sha256': _file_sha256(merged_path),
    }
    state['merged_deck'] = record
    state.pop('validated_deck', None)
    _save_runtime_state(state_path, state)
    return record


def validate_current_merged_deck(state):
    """Return stale reasons for the trusted deck seal, without modifying it."""
    record = state.get('merged_deck')
    if not isinstance(record, dict):
        return ['merged_deck_record_missing']
    order = state.get('deck_order')
    errors = []
    if order != record.get('deck_order'):
        errors.append('deck_order_mismatch')
    try:
        current_inputs = _current_deck_inputs(state, order)
        if current_inputs != record.get('slide_inputs'):
            errors.append('single_page_artifact_changed')
    except (KeyError, ValueError, TypeError):
        errors.append('single_page_artifact_changed')
    try:
        actual_hash = _file_sha256(_state_path(state, record['merged_pptx_path']))
        if actual_hash != record.get('merged_pptx_sha256'):
            errors.append('merged_pptx_hash_mismatch')
    except (OSError, KeyError, TypeError):
        errors.append('merged_pptx_hash_mismatch')
    return list(dict.fromkeys(errors))


def seal_validated_deck(runtime_state_path, status):
    """Bind a Deck-Level Validation PASS to the current merged bytes."""
    if status != 'PASS':
        raise ValueError('Deck-Level Validation must be PASS')
    state_path = Path(runtime_state_path).resolve()
    state = load_runtime_state(state_path)
    reasons = validate_current_merged_deck(state)
    if reasons:
        raise ValueError(','.join(reasons))
    record = {'status': 'PASS',
              'merged_pptx_sha256': state['merged_deck']['merged_pptx_sha256']}
    state['validated_deck'] = record
    _save_runtime_state(state_path, state)
    return record


def _current_reconstruction_backend(state):
    record=state.get('reconstruction_backend')
    run=state.get('stage2_run')
    if not isinstance(record,dict) or not isinstance(run,dict):
        return None
    if (record.get('run_id') != run.get('run_id')
            or record.get('approved_outline_fingerprint') != run.get('approved_outline_fingerprint')
            or record.get('page_order') != run.get('page_order')):
        return None
    backend=record.get('backend')
    return backend if backend in ('magic_layer','image_layer') else None


def resume_stage(a, runtime_state_path=None):
    """Return earliest unresolved stage; a flag alone never validates a PPTX."""
    if runtime_state_path is None:
        return 'AWAITING_STAGE1_APPROVAL' if any(
            value for key, value in a.items() if key != 'slide_id') else 'stage1'
    current = False
    if runtime_state_path is not None:
        try:
            state = load_runtime_state(runtime_state_path)
        except (KeyError, OSError, ValueError, TypeError):
            return 'AWAITING_STAGE1_APPROVAL'
        try:
            if 'stage1_outline' not in state:
                return 'AWAITING_STAGE1_APPROVAL'
            if 'stage1_outline' in state:
                try:
                    require_stage2_entry(runtime_state_path)
                except (OSError, ValueError, KeyError, TypeError):
                    return 'AWAITING_STAGE1_APPROVAL'
                run = state.get('stage2_run')
                approval_id = state['stage1_outline']['approval']['approval_id']
                if not isinstance(run, dict) or run.get('approval_id') != approval_id:
                    return 'stage2_exploration'
                # Exploration is current only after the user-selected Anchor and Style DNA are recorded.
                if not (stage2_artifact_current(runtime_state_path, 'anchor')
                        and stage2_artifact_current(runtime_state_path, 'style_dna')):
                    return 'stage2_exploration'
                visual = stage2_visual_status(runtime_state_path)
                if visual['status'] != 'COMPLETE':
                    return 'stage2_production'
                try:
                    require_stage2_visual_approval(runtime_state_path)
                except (OSError, ValueError, KeyError, TypeError):
                    return 'AWAITING_USER_VISUAL_APPROVAL'
                handoff = stage2_handoff_status(runtime_state_path)
                if handoff['status'] != 'COMPLETE':
                    return 'stage2_to_stage3_handoff'
                # Once the Stage 2 handoff is current, page-local Stage 3 artifacts may resume independently.
                if a.get('slide_id'):
                    for flag, kind in (('text_clean', 'text_clean'), ('graphics_first_pptx', 'graphics_first_pptx')):
                        if a.get(flag) and not stage2_artifact_current(
                                runtime_state_path, f'{kind}:{a["slide_id"]}'):
                            return 'stage3_text_preparation'
            if a.get('slide_id'):
                record = state['slides'][a['slide_id']].get('validated_single_page')
                current = not validate_current_artifact(record, state, a['slide_id'])
            order = state.get('deck_order')
            if isinstance(order, list) and order:
                if all(not validate_current_artifact(
                        state['slides'][slide_id].get('validated_single_page'),
                        state, slide_id) for slide_id in order):
                    if validate_current_merged_deck(state):
                        return 'deck_merge'
                    validated = state.get('validated_deck')
                    if (isinstance(validated, dict) and validated.get('status') == 'PASS'
                            and validated.get('merged_pptx_sha256')
                            == state['merged_deck']['merged_pptx_sha256']):
                        return 'complete'
                    return 'deck_validation'
                current = False
            if a.get('slide_id') and a.get('graphics_first_pptx') and stage2_artifact_current(
                    runtime_state_path, f'graphics_first_pptx:{a["slide_id"]}'):
                return 'stage3_text_restoration'
            missing_clean = next((sid for sid in run.get('page_order', [])
                                  if not stage2_artifact_current(runtime_state_path, f'text_clean:{sid}')), None)
            if missing_clean is not None:
                return 'stage3_text_preparation'
            backend = _current_reconstruction_backend(state)
            if backend is None:
                return 'stage3_reconstruction_backend_selection'
            return 'stage3_magic_layer' if backend == 'magic_layer' else 'stage3_image_layer'
        except (KeyError, OSError, ValueError, TypeError):
            current = False
    if current and a.get('validated_single_page_pptx'):
        return 'deck_merge'
    if a.get('graphics_first_pptx'):
        return 'stage3_text_restoration'
    if a.get('text_clean') and a.get('text_clean_fingerprint_matches') and a.get('approved_render') and a.get('final_content_truth'):
        backend = a.get('reconstruction_backend')
        if backend == 'magic_layer':
            return 'stage3_magic_layer'
        if backend == 'image_layer':
            return 'stage3_image_layer'
        return 'stage3_reconstruction_backend_selection'
    if a.get('approved_render') and a.get('final_content_truth'):
        return 'stage3_text_preparation'
    if a.get('anchor') and a.get('style_dna'):
        return 'stage2_production'
    if a.get('outline'):
        return 'stage2_exploration'
    return 'stage1'


def validate_deck_order(input_ids, deck_order):
    return (len(input_ids) == len(set(input_ids)) == len(deck_order) == len(set(deck_order))
            and set(input_ids) == set(deck_order))


def retry_transition(status, event):
    if status not in {'available','pending','consumed'}:
        raise ValueError('invalid retry state')
    if event == 'tool_failure':
        return status
    if event == 'structural_failure' and status == 'available':
        return 'pending'
    if event == 'assessable_result' and status == 'pending':
        return 'consumed'
    return status


def active_attempt_matches(attempt, slide_id, source_fp, clean_fp):
    return all(attempt.get(k) == v for k, v in [('slide_id',slide_id),('source_fingerprint',source_fp),('text_clean_fingerprint',clean_fp)])


def validate_manifest_hashes(skill_dir):
    import yaml
    root = Path(skill_dir)
    manifest = yaml.safe_load((root/'manifest.yaml').read_text(encoding='utf-8'))
    errors = []
    for ref in manifest['canonical_protocols']:
        path = root/ref['path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != ref['sha256']:
            errors.append(ref['path'])
    return errors


def main(argv=None):
    """Small machine-facing gate for the Skill's Stage 1/2 navigation."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=(
        'stage1-draft', 'stage1-review', 'stage1-reply', 'stage1-preapproved',
        'stage2-entry', 'stage2-run-start', 'stage2-artifact-register',
        'stage2-candidate-register', 'stage2-candidate-review',
        'stage2-anchor-formal-display', 'stage2-anchor-select', 'stage2-approved-list', 'stage2-visual-status', 'stage2-formal-display',
        'stage2-visual-approve', 'stage2-visual-revise', 'stage2-text-reconciled',
        'stage2-handoff-status', 'stage3-text-clean-display', 'resume'))
    parser.add_argument('--state', required=True)
    parser.add_argument('--outline')
    parser.add_argument('--message')
    parser.add_argument('--decision', choices=('approve', 'revise', 'rework', 'unclear'))
    parser.add_argument('--edits-json')
    parser.add_argument('--kind')
    parser.add_argument('--artifact')
    parser.add_argument('--flags-json')
    parser.add_argument('--slide-id')
    parser.add_argument('--candidate-id')
    parser.add_argument('--verdict')
    parser.add_argument('--failed-hard-gate')
    parser.add_argument('--evidence')
    parser.add_argument('--correction')
    parser.add_argument('--replan-evidence')
    parser.add_argument('--review-notes-json')
    parser.add_argument('--slide-ids-json')
    parser.add_argument('--generation-intent')
    parser.add_argument('--approval-mode', default='qualification_review')
    parser.add_argument('--user-requested-variant', action='store_true')
    parser.add_argument('--restart', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.action == 'stage1-draft':
            result = {'outline_fingerprint': record_stage1_draft(args.state, args.outline)}
        elif args.action == 'stage1-review':
            result = {'status': 'review_pending', 'review_view': present_stage1_review(args.state)}
        elif args.action == 'stage1-reply':
            edits = json.loads(Path(args.edits_json).read_text(encoding='utf-8')) if args.edits_json else None
            result = handle_stage1_reply(args.state, args.message or '', edits, decision=args.decision)
        elif args.action == 'stage1-preapproved':
            result = accept_preapproved_outline(args.state, args.outline, args.message or '')
        elif args.action == 'stage2-entry':
            result = {'status': 'PASS', 'approved_outline_fingerprint': require_stage2_entry(args.state)}
        elif args.action == 'stage2-run-start':
            result = start_stage2_run(args.state, restart=args.restart)
        elif args.action == 'stage2-artifact-register':
            result = register_stage2_artifact(args.state, args.kind, args.artifact)
        elif args.action == 'stage2-candidate-register':
            result = register_stage2_candidate(
                args.state, args.slide_id, args.artifact, args.generation_intent,
                user_requested_variant=args.user_requested_variant)
        elif args.action == 'stage2-candidate-review':
            notes = json.loads(Path(args.review_notes_json).read_text(encoding='utf-8')) if args.review_notes_json else None
            result = review_stage2_candidate(
                args.state, args.candidate_id, args.verdict,
                failed_hard_gate=args.failed_hard_gate,
                observable_evidence=args.evidence,
                required_correction=args.correction,
                replan_evidence=args.replan_evidence,
                review_notes=notes,
                approval_mode=args.approval_mode)
        elif args.action == 'stage2-anchor-formal-display':
            result = present_anchor_formal_candidates(args.state, args.slide_id)
        elif args.action == 'stage2-anchor-select':
            result = select_anchor_candidate(args.state, args.slide_id, args.candidate_id)
        elif args.action == 'stage2-approved-list':
            result = {'approved': list_current_stage2_approved(args.state)}
        elif args.action == 'stage2-visual-status':
            result = stage2_visual_status(args.state)
        elif args.action == 'stage2-formal-display':
            result = present_stage2_formal_display(args.state)
        elif args.action == 'stage2-visual-approve':
            result = seal_stage2_visual_approval(args.state, args.message or '')
        elif args.action == 'stage2-visual-revise':
            if not args.slide_ids_json:
                raise ValueError('STAGE2_VISUAL_REVISION_INVALID: --slide-ids-json required')
            slide_ids = json.loads(Path(args.slide_ids_json).read_text(encoding='utf-8'))
            result = request_stage2_visual_revision(args.state, slide_ids)
        elif args.action == 'stage2-text-reconciled':
            result = mark_stage2_text_reconciled(args.state, args.slide_id)
        elif args.action == 'stage2-handoff-status':
            result = stage2_handoff_status(args.state)
        elif args.action == 'stage3-text-clean-display':
            result = build_text_clean_formal_display_set(args.state)
        else:
            flags = json.loads(Path(args.flags_json).read_text(encoding='utf-8')) if args.flags_json else {}
            result = {'next_stage': resume_stage(flags, args.state)}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'BLOCKED', 'code': str(error)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
