"""Optional page-heading policy; observations stay with the agent, provenance with code."""
import copy
import hashlib
import math
import re

NORMAL_HEADING = '正文主标题默认承担导航和层级作用，由实质信息内容承担页面主视觉；统一标题规范只能从符合这一要求的普通内容页提取，单页获准的展示性大标题不得成为后续页面的统一基准。'
GENERATION_GUIDANCE = '生成时优先保持标题区域和对齐；同一区域内可安全恢复的字体、字号、字重及轻微位置差异记录后继续，在每页全部文字恢复后独立统一主标题。'
ROLES = {'cover', 'content', 'toc', 'section', 'thanks', 'display'}


def _r():
    import runtime
    return runtime


def _digest(value):
    return hashlib.sha256(_r()._canonical(value)).hexdigest()


def initial_policy(run):
    return {'mode': 'pending', 'run_id': run['run_id'],
            'approved_outline_fingerprint': run['approved_outline_fingerprint'],
            'page_roles': {}, 'applicable_slide_ids': [], 'contracts': {},
            'default_ref': None, 'page_bindings': {}, 'history': []}


def _policy(state):
    run = state.get('stage2_run', {})
    policy = run.get('title_policy')
    if policy is None:
        return None
    _r()._current_stage2_run(state)
    if (not isinstance(policy, dict) or policy.get('mode') not in {'pending', 'uniform', 'free'}
            or policy.get('run_id') != run.get('run_id')
            or policy.get('approved_outline_fingerprint') != run.get('approved_outline_fingerprint')):
        raise ValueError('TITLE_POLICY_SOURCE_MISMATCH')
    return policy


def _approved(state, sid):
    r = _r(); run = state['stage2_run']
    record = run.get('current_approved', {}).get(sid)
    candidate = run.get('candidates', {}).get((record or {}).get('candidate_id'), {})
    if (not isinstance(record, dict) or candidate.get('status') != 'approved'
            or record.get('run_id') != run['run_id']
            or record.get('approved_outline_fingerprint') != run['approved_outline_fingerprint']
            or r._file_sha256(r._state_path(state, record['path'])) != record.get('sha256')):
        raise ValueError('TITLE_CURRENT_APPROVED_RENDER_REQUIRED')
    return record


def _eligible(policy, sid):
    return sid in policy.get('applicable_slide_ids', []) and policy['page_roles'].get(sid) == 'content'


def _check_existing_lock(state_path):
    from pathlib import Path
    path = Path(state_path).resolve()
    if any(Path(str(path)+suffix).exists() for suffix in ('.bridge-lock', '.router-lock')):
        raise ValueError('TITLE_STATE_OPERATION_RUNNING: preserve locks and existing work')


def _classify_roles(state, run, page_roles):
    if not isinstance(page_roles, dict) or set(page_roles) != set(run['page_order']) or any(v not in ROLES for v in page_roles.values()):
        raise ValueError('TITLE_PAGE_ROLES_REQUIRED: classify current page_task, do not edit Outline')
    r = _r()
    # Explicit task labels cannot be relabelled as ordinary content by the adapter.
    _, outline, _ = r._current_outline(state)
    labels = {'cover': ('封面', 'cover', 'title slide'), 'toc': ('目录', 'toc', 'agenda'),
              'section': ('章节过渡', '过渡页', 'section divider'), 'thanks': ('纯致谢', '致谢页', 'thanks')}
    for sid, page in zip(run['page_order'], outline['slides']):
        task = str(page['page_task']).strip().lower()
        for role, prefixes in labels.items():
            if any(task.startswith(prefix) for prefix in prefixes) and page_roles[sid] != role:
                raise ValueError('TITLE_PAGE_ROLE_CONFLICT: '+sid)
    applicable = [sid for sid in run['page_order'] if page_roles[sid] == 'content']
    return applicable


def set_policy(state_path, mode, page_roles=None, message=''):
    _check_existing_lock(state_path)
    r = _r(); state = r.load_runtime_state(state_path)
    r.require_stage2_entry(state_path); run = r._current_stage2_run(state)
    if mode not in {'pending', 'uniform', 'free'}:
        raise ValueError('TITLE_POLICY_MODE_INVALID')
    previous = _policy(state)
    if mode == 'pending':
        if previous is not None and previous['mode'] != 'pending':
            return copy.deepcopy(previous)
        if run.get('candidates'):
            raise ValueError('TITLE_LEGACY_RUN_UNCHANGED: no automatic migration')
        run['title_policy'] = copy.deepcopy(previous) if previous else initial_policy(run)
        if page_roles is not None:
            applicable = _classify_roles(state, run, page_roles)
            run['title_policy'].update(page_roles=copy.deepcopy(page_roles), applicable_slide_ids=applicable)
            if not applicable:
                run['title_policy'].update(mode='free', selection_origin='system_no_applicable_pages',
                                          selection_note='no_applicable_pages')
    else:
        if not str(message).strip():
            raise ValueError('TITLE_ACTUAL_USER_DECISION_REQUIRED')
        applicable = _classify_roles(state, run, page_roles)
        effective_mode = mode if applicable else 'free'
        if previous and previous.get('mode') == effective_mode and previous.get('page_roles') == page_roles:
            return copy.deepcopy(previous)
        if previous and previous.get('mode') in {'uniform', 'free'} and run.get('candidates'):
            raise ValueError('TITLE_ACTIVE_POLICY_CHANGE: use explicit page/global revision; preserve existing bindings')
        policy = initial_policy(run)
        policy.update(mode=effective_mode, page_roles=copy.deepcopy(page_roles),
                      applicable_slide_ids=applicable, user_message=str(message),
                      selection_origin='actual_user_instruction')
        if not applicable: policy['selection_note'] = 'no_applicable_pages'
        run['title_policy'] = policy
    r._save_runtime_state(state_path, state)
    return copy.deepcopy(run['title_policy'])


def _contract(policy, ref):
    snapshot = policy.get('contracts', {}).get(ref)
    if not isinstance(snapshot, dict):
        raise ValueError('TITLE_CONTRACT_REFERENCE_UNKNOWN')
    payload = {k: v for k, v in snapshot.items() if k != 'fingerprint'}
    if snapshot.get('fingerprint') != ref or _digest(payload) != ref:
        raise ValueError('TITLE_CONTRACT_SNAPSHOT_CHANGED')
    if snapshot.get('run_id') != policy['run_id'] or snapshot.get('approved_outline_fingerprint') != policy['approved_outline_fingerprint']:
        raise ValueError('TITLE_CONTRACT_SOURCE_MISMATCH')
    return snapshot


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _style(value):
    required = {'font_family', 'fallback_font_family', 'font_family_basis', 'font_weight', 'color',
                'title_region', 'alignment', 'first_line_baseline', 'visible_glyph_height',
                'line_height_ratio', 'max_lines'}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError('TITLE_STYLE_FIELDS_REQUIRED')
    if any(not isinstance(value[k], str) or not value[k].strip() for k in ('font_family', 'fallback_font_family', 'font_weight')):
        raise ValueError('TITLE_FONT_FIELDS_INVALID')
    if value['font_family_basis'] not in {'estimated', 'generation_spec', 'verified'} or value['alignment'] not in {'left', 'center', 'right'}:
        raise ValueError('TITLE_STYLE_INVALID')
    if not isinstance(value['color'], str) or re.fullmatch(r'#[0-9a-fA-F]{6}', value['color']) is None:
        raise ValueError('TITLE_COLOR_INVALID')
    box = value['title_region']
    if not isinstance(box, list) or len(box) != 4 or not all(_number(x) for x in box) or not _r()._valid_normalized_bbox(box):
        raise ValueError('TITLE_REGION_INVALID')
    baseline = value['first_line_baseline']; height = value['visible_glyph_height']; gap = value['line_height_ratio']
    if (not all(_number(x) and x > 0 for x in (baseline, height, gap))
            or not box[1] <= baseline <= box[1]+box[3] or height > box[3]
            or isinstance(value['max_lines'], bool) or value['max_lines'] != 2):
        raise ValueError('TITLE_SCALE_INVALID')
    return copy.deepcopy(value)


def bind(state_path, sid, payload, scope='prototype', message='', affected_slide_ids=None):
    _check_existing_lock(state_path)
    r = _r(); state = r.load_runtime_state(state_path)
    r.require_stage2_entry(state_path); run = r._current_stage2_run(state); policy = _policy(state)
    if not policy or policy['mode'] != 'uniform' or not _eligible(policy, sid):
        raise ValueError('TITLE_PROTOTYPE_CONTENT_PAGE_REQUIRED')
    if scope not in {'prototype', 'page_override', 'global_revision'}:
        raise ValueError('TITLE_BIND_SCOPE_INVALID')
    approved = _approved(state, sid)
    if not isinstance(payload, dict) or payload.get('source_render_sha256') != approved['sha256']:
        raise ValueError('TITLE_SOURCE_IMAGE_MISMATCH')
    assessment = payload.get('heading_assessment')
    if (not isinstance(assessment, dict) or assessment.get('role') not in {'navigation', 'display'}
            or not isinstance(assessment.get('evidence'), str) or not assessment['evidence'].strip()
            or not isinstance(assessment.get('content_is_primary'), bool)
            or not isinstance(assessment.get('display_exception'), bool)):
        raise ValueError('TITLE_EXISTING_QUALIFICATION_EVIDENCE_REQUIRED')
    normal = assessment['role'] == 'navigation' and assessment['content_is_primary'] and not assessment['display_exception']
    if scope != 'page_override' and not normal:
        raise ValueError('TITLE_DISPLAY_HEADING_CANNOT_SEED: use existing H2 or keep explicitly authorized local exception')
    if scope != 'prototype' and not str(message).strip():
        raise ValueError('TITLE_ACTUAL_REVISION_INSTRUCTION_REQUIRED')
    if not normal and (scope != 'page_override' or not assessment['display_exception']):
        raise ValueError('TITLE_UNAUTHORIZED_DISPLAY_HEADING')
    style = _style(payload.get('style')) if normal else None
    if scope == 'prototype' and policy['default_ref'] is None:
        # The first current ordinary non-exception page supplies the baseline.
        seeds = [x for x in policy['applicable_slide_ids'] if run.get('current_approved', {}).get(x)
                 and not policy['page_bindings'].get(x, {}).get('page_override')]
        if not seeds or seeds[0] != sid:
            raise ValueError('TITLE_FIRST_ORDINARY_PAGE_REQUIRED')
    snapshot = {'run_id': run['run_id'], 'approved_outline_fingerprint': run['approved_outline_fingerprint'],
                'source_slide_id': sid, 'source_render_sha256': approved['sha256'],
                'scope': scope, 'origin': 'system_derived' if scope == 'prototype' else 'actual_user_revision',
                'user_message': '' if scope == 'prototype' else str(message),
                'heading_assessment': copy.deepcopy(assessment), 'style': style}
    ref = _digest(snapshot); snapshot['fingerprint'] = ref
    old_ref = policy['default_ref']
    binding = {'contract_ref': ref, 'render_sha256': approved['sha256'],
               'page_override': scope == 'page_override'}
    if policy['page_bindings'].get(sid) == binding and ref in policy['contracts']:
        _contract(policy, ref)
        return {'status': 'TITLE_BOUND', 'slide_id': sid, 'contract_ref': ref, 'idempotent': True}
    if scope == 'prototype' and old_ref is not None:
        raise ValueError('TITLE_STANDARD_IMMUTABLE: current-page edits cannot redefine deck standard')
    targets = []
    if scope == 'global_revision':
        targets = list(affected_slide_ids) if affected_slide_ids is not None else [x for x in policy['applicable_slide_ids']
                   if x == sid or not policy['page_bindings'].get(x, {}).get('page_override')]
        if not targets or len(targets) != len(set(targets)) or any(not _eligible(policy, x) for x in targets) or sid not in targets:
            raise ValueError('TITLE_GLOBAL_REVISION_TARGETS_INVALID')
        if old_ref is None: raise ValueError('TITLE_GLOBAL_REVISION_REQUIRES_EXISTING_STANDARD')
    policy['contracts'][ref] = snapshot
    if scope in {'prototype', 'global_revision'}:
        policy['default_ref'] = ref
    old_binding = policy['page_bindings'].get(sid)
    if old_binding: policy['history'].append({'slide_id': sid, 'binding': old_binding})
    policy['page_bindings'][sid] = binding
    candidate = run['candidates'][approved['candidate_id']]
    candidate['title_contract_ref'] = ref; approved['title_contract_ref'] = ref
    if scope == 'global_revision':
        pending = set(run.get('pending_visual_revisions', []))
        for target in targets:
            if target != sid and run.get('current_approved', {}).get(target): pending.add(target)
        run['pending_visual_revisions'] = [x for x in run['page_order'] if x in pending]
        policy['history'].append({'event': 'global_revision', 'old_ref': old_ref, 'new_ref': ref,
                                  'affected_slide_ids': targets, 'actual_user_message': str(message)})
        r._invalidate_stage2_visual_approval(run, 'actual_user_global_title_revision')
    elif scope == 'page_override':
        r._invalidate_stage2_visual_approval(run, 'actual_user_page_title_override')
    r._save_runtime_state(state_path, state)
    return {'status': 'TITLE_BOUND', 'slide_id': sid, 'contract_ref': ref, 'idempotent': False,
            'pending_revision_pages': list(run.get('pending_visual_revisions', []))}


def context_from_state(state, sid=None):
    policy = _policy(state); run = state.get('stage2_run', {})
    if sid is not None and sid not in run.get('page_order', []): raise ValueError('TITLE_PAGE_NOT_CURRENT')
    if policy is None: return {'mode': 'free', 'origin': 'legacy_unchanged'}
    mode = policy['mode']
    result = {'mode': mode, 'next_action': 'choose_uniform_or_free' if mode == 'pending' else 'continue'}
    if mode != 'uniform': return result
    applies = sid is not None and _eligible(policy, sid)
    result.update(heading_requirement=NORMAL_HEADING + (GENERATION_GUIDANCE if applies else ''), applies=applies)
    if sid is None:
        result.update(default_ref=policy['default_ref'], applicable_slide_ids=list(policy['applicable_slide_ids']))
        return result
    if not _eligible(policy, sid): return result
    binding = policy['page_bindings'].get(sid)
    approved = run.get('current_approved', {}).get(sid)
    if binding and approved and binding.get('render_sha256') == approved.get('sha256') and sid not in run.get('pending_visual_revisions', []):
        ref = binding['contract_ref']
    else:
        ref = policy['default_ref']
    if ref:
        snapshot = _contract(policy, ref)
        if binding and binding.get('page_override'):
            result['actual_page_instruction'] = snapshot['user_message']
            result['heading_role'] = snapshot['heading_assessment']['role']
        result.update(contract_ref=ref, style=copy.deepcopy(snapshot['style']),
                      page_override=bool(binding and ref == binding['contract_ref'] and binding.get('page_override')),
                      overflow_action='keep_scale_wrap_two_lines_then_author_choice')
    else:
        seeds = [x for x in policy['applicable_slide_ids'] if run.get('current_approved', {}).get(x)
                 and not policy['page_bindings'].get(x, {}).get('page_override')]
        if seeds: result.update(next_action='bind_current_prototype', prototype_slide_id=seeds[0])
        else: result['next_action'] = 'generate_normal_heading_prototype'
    return result


def context(state_path, sid=None):
    r = _r(); r.require_stage2_entry(state_path)
    return context_from_state(r.load_runtime_state(state_path), sid)


def candidate_context(state, sid, requested_ref=None, override_message=None):
    policy = _policy(state)
    if not policy: return None
    if policy['mode'] == 'pending': raise ValueError('TITLE_USER_CHOICE_REQUIRED')
    if policy['mode'] != 'uniform' or not _eligible(policy, sid): return None
    ctx = context_from_state(state, sid)
    if ctx['next_action'] == 'bind_current_prototype' and not override_message:
        raise ValueError('TITLE_BIND_CURRENT_PROTOTYPE: automatic internal step, no author confirmation')
    if ctx.get('contract_ref') is not None and requested_ref is None:
        raise ValueError('TITLE_GENERATION_REFERENCE_REQUIRED: carry the pre-generation context reference')
    if requested_ref is not None and requested_ref != ctx.get('contract_ref'):
        raise ValueError('TITLE_GENERATION_REFERENCE_MISMATCH')
    return {'contract_ref': ctx.get('contract_ref'), 'actual_override_message': str(override_message or ''),
            'run_id': policy['run_id'], 'approved_outline_fingerprint': policy['approved_outline_fingerprint']}


def check_promotion(state, sid, candidate):
    policy = _policy(state)
    if not policy or policy['mode'] != 'uniform' or not _eligible(policy, sid): return
    info = candidate.get('title_context')
    if not isinstance(info, dict): raise ValueError('TITLE_CANDIDATE_CONTEXT_REQUIRED')
    current = candidate_context(state, sid, info.get('contract_ref'), info.get('actual_override_message'))
    if info != current: raise ValueError('TITLE_GENERATION_CONTEXT_STALE')


def promote(state, sid, candidate, approved):
    policy = _policy(state); info = candidate.get('title_context')
    if not policy or policy['mode'] != 'uniform' or not _eligible(policy, sid): return
    if not isinstance(info, dict) or info.get('run_id') != policy['run_id'] or info.get('approved_outline_fingerprint') != policy['approved_outline_fingerprint']:
        raise ValueError('TITLE_CANDIDATE_CONTEXT_REQUIRED')
    ref = info.get('contract_ref')
    if ref is None:
        return  # First normal source is bound immediately after qualification PASS.
    _contract(policy, ref)
    old = policy['page_bindings'].get(sid)
    if old: policy['history'].append({'slide_id': sid, 'binding': old})
    policy['page_bindings'][sid] = {'contract_ref': ref, 'render_sha256': approved['sha256'],
                                  'page_override': bool(info.get('actual_override_message')),
                                  'actual_override_message': info.get('actual_override_message', '')}
    candidate['title_contract_ref'] = ref; approved['title_contract_ref'] = ref


def pending_pages(state):
    policy = _policy(state)
    if not policy or policy['mode'] == 'free': return []
    run = state['stage2_run']
    if policy['mode'] == 'pending': return list(run['page_order'])
    missing = []
    for sid in policy['applicable_slide_ids']:
        approved = run.get('current_approved', {}).get(sid); binding = policy['page_bindings'].get(sid)
        if approved and (not binding or binding.get('render_sha256') != approved.get('sha256')): missing.append(sid)
        if binding and binding.get('actual_override_message'):
            # A user variant still needs its actual new local style/exception registered.
            snap = _contract(policy, binding['contract_ref'])
            if snap['source_render_sha256'] != binding['render_sha256']: missing.append(sid)
    return list(dict.fromkeys(missing))


def validate_manifest(state, sid, manifest):
    policy = _policy(state)
    if not policy or policy['mode'] != 'uniform' or not _eligible(policy, sid): return []
    if sid in pending_pages(state) or sid in state['stage2_run'].get('pending_visual_revisions', []):
        raise ValueError('TITLE_PAGE_BINDING_PENDING')
    approved = _approved(state, sid); binding = policy['page_bindings'].get(sid)
    if not binding or binding['render_sha256'] != approved['sha256']:
        raise ValueError('TITLE_PAGE_BINDING_SOURCE_MISMATCH')
    if not isinstance(manifest, dict) or manifest.get('slide_id') != sid or manifest.get('title_contract_ref') != binding['contract_ref']:
        raise ValueError('TITLE_MANIFEST_REFERENCE_MISMATCH')
    snapshot = _contract(policy, binding['contract_ref'])
    ids = manifest.get('title_element_ids')
    if not isinstance(ids, list) or any(not isinstance(x, str) for x in ids) or len(ids) != len(set(ids)):
        raise ValueError('TITLE_PRIMARY_ELEMENT_IDS_REQUIRED')
    if not ids and snapshot['heading_assessment']['role'] == 'navigation':
        raise ValueError('TITLE_PRIMARY_ELEMENT_IDS_REQUIRED')
    elements = {x.get('id'): x for x in manifest.get('text_elements', []) if isinstance(x, dict)}
    truth_path = state['slides'][sid].get('final_content_truth')
    import json
    truth = _r()._truth_occurrence_map(json.loads(_r()._state_path(state, truth_path).read_text(encoding='utf-8')), sid)
    for element_id in ids:
        element = elements.get(element_id)
        if (not element or element.get('representation_role') != 'native_text'
                or element.get('treatment') != 'remove_and_restore'
                or element.get('truth_source') != 'stage2_final_content_truth'
                or truth.get(element.get('truth_ref')) != element.get('content')):
            raise ValueError('TITLE_PRIMARY_NATIVE_TEXT_REQUIRED: do not change graphics, Logo or Content Truth')
    return ids
