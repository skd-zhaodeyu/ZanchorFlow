import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import runtime
import canva_bridge as bridge
from stage2_test_helpers import write_png, write_truth, approve_page

FIELDS = (
    'page_task', 'title', 'core_expression', 'key_information',
    'semantic_relation', 'acceptance_criteria'
)


def _start(tmp_path, n=3):
    slides = [{field: f'{field}-{i+1}' for field in FIELDS} for i in range(n)]
    outline = tmp_path / 'outline.json'
    outline.write_text(json.dumps({'slides': slides}, ensure_ascii=False), encoding='utf-8')
    state = tmp_path / 'state.json'
    state.write_text('{"slides":{},"canva_bridge":{"route":"codex-canva","schema_version":1}}', encoding='utf-8')
    runtime.record_stage1_draft(state, outline)
    runtime.present_stage1_review(state)
    runtime.handle_stage1_reply(state, '同意，按这个继续。', decision='approve')
    runtime.start_stage2_run(state)
    anchor = tmp_path / 'anchor.txt'; anchor.write_text('anchor', encoding='utf-8')
    style = tmp_path / 'style.json'; style.write_text('{}', encoding='utf-8')
    runtime.register_stage2_artifact(state, 'anchor', anchor)
    runtime.register_stage2_artifact(state, 'style_dna', style)
    return state


def _approve(runtime_state, tmp_path, sid, marker, approval_mode='qualification_review'):
    path = write_png(tmp_path / f'{sid}-{marker}.png', marker.encode())
    return approve_page(runtime, runtime_state, sid, path, intent=f'{sid}-{marker}', approval_mode=approval_mode)


def _present_and_approve(state, message='确认，按这组页面进入下一阶段。'):
    shown = runtime.present_stage2_formal_display(state)
    assert shown['status'] == 'COMPLETE'
    return runtime.seal_stage2_visual_approval(state, message)


def test_d1_formal_display_excludes_revise_reject_and_superseded_history(tmp_path):
    state = _start(tmp_path, 3)
    first = _approve(state, tmp_path, 'S001', 'cover', approval_mode='user_selected_anchor_page')

    bad = runtime.register_stage2_candidate(state, 'S002', write_png(tmp_path/'s2-bad.png'), 'bad-3d')
    runtime.review_stage2_candidate(
        state, bad['candidate_id'], 'REVISE', failed_hard_gate='H2',
        observable_evidence='出现明显立体厚度', required_correction='改为二维正视表达')
    old = _approve(state, tmp_path, 'S002', 'old-pass')
    variant = runtime.register_stage2_candidate(
        state, 'S002', write_png(tmp_path/'s2-new.png'), 'user-new', user_requested_variant=True)
    runtime.review_stage2_candidate(state, variant['candidate_id'], 'PASS')

    rejected = runtime.register_stage2_candidate(state, 'S003', write_png(tmp_path/'s3-bad.png'), 'bad-crop')
    runtime.review_stage2_candidate(
        state, rejected['candidate_id'], 'REJECT', failed_hard_gate='H3',
        observable_evidence='承担核心关系的主体结构整体被裁切，局部位移无法恢复完整关系',
        required_correction='重新规划主体结构后生成完整构图',
        replan_evidence='当前主体关系结构已被整体截断，局部修正不能恢复')
    current3 = _approve(state, tmp_path, 'S003', 'good')

    display = runtime.present_stage2_formal_display(state)
    assert display['status'] == 'COMPLETE'
    assert [item['slide_id'] for item in display['renders']] == ['S001', 'S002', 'S003']
    assert [item['candidate_id'] for item in display['renders']] == [
        first['candidate_id'], variant['candidate_id'], current3['candidate_id']]
    ids = {item['candidate_id'] for item in display['renders']}
    assert bad['candidate_id'] not in ids
    assert old['candidate_id'] not in ids
    assert rejected['candidate_id'] not in ids


def test_d2_locked_anchor_cover_is_in_formal_display_even_when_not_generated_in_batch(tmp_path):
    state = _start(tmp_path, 2)
    cover = _approve(state, tmp_path, 'S001', 'selected-cover', approval_mode='user_selected_anchor_page')
    _approve(state, tmp_path, 'S002', 'batch-page')
    display = runtime.present_stage2_formal_display(state)
    assert display['renders'][0]['slide_id'] == 'S001'
    assert display['renders'][0]['candidate_id'] == cover['candidate_id']


def test_d3_all_pages_pass_but_resume_waits_for_user_visual_approval(tmp_path):
    state = _start(tmp_path, 2)
    _approve(state, tmp_path, 'S001', 'one')
    _approve(state, tmp_path, 'S002', 'two')
    assert runtime.resume_stage({}, state) == 'AWAITING_USER_VISUAL_APPROVAL'
    assert bridge.status(state)['status'] == 'AWAITING_USER_VISUAL_APPROVAL'


def test_d4_user_approval_binds_exact_display_set_and_allows_stage3_gate(tmp_path):
    state = _start(tmp_path, 1)
    _approve(state, tmp_path, 'S001', 'one')
    shown = runtime.present_stage2_formal_display(state)
    approval = runtime.seal_stage2_visual_approval(state, '确认，按这组页面进入下一阶段。')
    assert approval['display_set_fingerprint'] == shown['display_set_fingerprint']
    assert runtime.require_stage2_visual_approval(state) == shown['display_set_fingerprint']


def test_d5_replacing_one_passed_page_makes_old_visual_approval_stale(tmp_path):
    state = _start(tmp_path, 2)
    _approve(state, tmp_path, 'S001', 'one')
    _approve(state, tmp_path, 'S002', 'two')
    _present_and_approve(state)

    variant = runtime.register_stage2_candidate(
        state, 'S002', write_png(tmp_path/'s2-replacement.png'), 'user replacement',
        user_requested_variant=True)
    runtime.review_stage2_candidate(state, variant['candidate_id'], 'PASS')
    with pytest.raises(ValueError, match='STAGE2_VISUAL_APPROVAL_(REQUIRED|STALE)'):
        runtime.require_stage2_visual_approval(state)
    assert runtime.resume_stage({}, state) == 'AWAITING_USER_VISUAL_APPROVAL'


def test_d6_user_revision_reopens_only_requested_page_and_preserves_other_passes(tmp_path):
    state = _start(tmp_path, 3)
    originals = {sid: _approve(state, tmp_path, sid, 'original') for sid in ('S001','S002','S003')}
    runtime.present_stage2_formal_display(state)
    result = runtime.request_stage2_visual_revision(state, ['S002'])
    assert result['pending_revision_pages'] == ['S002']
    assert runtime.stage2_visual_status(state) == {'status':'INCOMPLETE','missing':['S002']}
    assert runtime.current_stage2_approved_render(state, 'S001')['candidate_id'] == originals['S001']['candidate_id']
    assert runtime.current_stage2_approved_render(state, 'S003')['candidate_id'] == originals['S003']['candidate_id']

    replacement = runtime.register_stage2_candidate(
        state, 'S002', write_png(tmp_path/'s2-revised.png'), 'requested revision',
        user_requested_variant=True)
    runtime.review_stage2_candidate(state, replacement['candidate_id'], 'PASS')
    assert runtime.stage2_visual_status(state) == {'status':'COMPLETE','missing':[]}
    assert runtime.current_stage2_approved_render(state, 'S001')['candidate_id'] == originals['S001']['candidate_id']
    assert runtime.current_stage2_approved_render(state, 'S003')['candidate_id'] == originals['S003']['candidate_id']


def test_d7_text_clean_formal_display_uses_only_current_text_clean_per_page(tmp_path):
    state = _start(tmp_path, 2)
    for sid in ('S001','S002'):
        _approve(state, tmp_path, sid, 'render')
    _present_and_approve(state)

    for sid in ('S001','S002'):
        truth = Path(write_truth(tmp_path/f'{sid}-truth.json', sid, text='x'))
        runtime.register_stage2_artifact(state, f'final_content_truth:{sid}', truth)
        runtime.mark_stage2_text_reconciled(state, sid)
        old = tmp_path/f'{sid}-clean-old.png'; old.write_bytes(b'old')
        new = tmp_path/f'{sid}-clean-new.png'; new.write_bytes(b'new')
        runtime.register_stage2_artifact(state, f'text_clean:{sid}', old)
        runtime.register_stage2_artifact(state, f'text_clean:{sid}', new)

    display = runtime.build_text_clean_formal_display_set(state)
    assert display['status'] == 'COMPLETE'
    assert [x['slide_id'] for x in display['renders']] == ['S001','S002']
    assert all(x['path'].endswith('-clean-new.png') for x in display['renders'])
    assert len(display['renders']) == 2


def test_d8_direct_stage3_text_plan_registration_cannot_bypass_visual_approval(tmp_path):
    state = _start(tmp_path, 1)
    _approve(state, tmp_path, 'S001', 'one')
    truth = Path(write_truth(tmp_path/'truth.json', 'S001', text='x'))
    runtime.register_stage2_artifact(state, 'final_content_truth:S001', truth)
    runtime.mark_stage2_text_reconciled(state, 'S001')
    manifest = tmp_path/'manifest.json'; inventory = tmp_path/'inventory.json'
    manifest.write_text(json.dumps({'schema_version':'1.1','slide_id':'S001','source_width':1600,'source_height':900,'text_elements':[]}), encoding='utf-8')
    inventory.write_text(json.dumps({'schema_version':'1.1','slide_id':'S001','items':[]}), encoding='utf-8')
    with pytest.raises(ValueError, match='STAGE2_VISUAL_APPROVAL_REQUIRED'):
        bridge.register_text_plan(state, 'S001', manifest, inventory)
