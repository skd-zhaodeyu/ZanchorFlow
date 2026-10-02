import base64
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import runtime

PNG_1X1 = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2pFQAAAAASUVORK5CYII='
)

FIELDS = (
    'page_task', 'title', 'core_expression', 'key_information',
    'semantic_relation', 'acceptance_criteria'
)


def _case(tmp_path, n=3):
    slides = []
    for i in range(n):
        slides.append({field: f'{field}-{i+1}' for field in FIELDS})
    outline = {'slides': slides}
    outline_path = tmp_path / 'outline.json'
    outline_path.write_text(json.dumps(outline, ensure_ascii=False), encoding='utf-8')
    state_path = tmp_path / 'state.json'
    state_path.write_text('{"slides":{}}', encoding='utf-8')
    runtime.record_stage1_draft(state_path, outline_path)
    runtime.present_stage1_review(state_path)
    runtime.handle_stage1_reply(state_path, '同意，按这个继续。', decision='approve')
    return state_path, outline_path


def _png(tmp_path, name):
    path = tmp_path / f'{name}.png'
    path.write_bytes(PNG_1X1)
    return path


def _start(tmp_path, n=3):
    state_path, _ = _case(tmp_path, n=n)
    run = runtime.start_stage2_run(state_path)
    return state_path, run


def test_same_approved_outline_resumes_same_stage2_run_and_page_set(tmp_path):
    state_path, run1 = _start(tmp_path, n=3)
    run2 = runtime.start_stage2_run(state_path)
    assert run2['run_id'] == run1['run_id']
    assert run2['page_order'] == ['S001', 'S002', 'S003']
    assert list(run2['pages']) == ['S001', 'S002', 'S003']


def test_approved_render_cannot_be_directly_registered(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    fake = tmp_path / 'fake.txt'
    fake.write_text('not an image', encoding='utf-8')
    with pytest.raises(ValueError, match='APPROVED_RENDER_REQUIRES_PASS'):
        runtime.register_stage2_artifact(state_path, 'approved_render:S001', fake)


def test_candidate_requires_real_image_and_current_page(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    fake = tmp_path / 'fake.txt'
    fake.write_text('not an image', encoding='utf-8')
    with pytest.raises(ValueError, match='STAGE2_CANDIDATE_IMAGE_REQUIRED'):
        runtime.register_stage2_candidate(state_path, 'S001', fake, generation_intent='first')
    with pytest.raises(ValueError, match='STAGE2_PAGE_NOT_CURRENT'):
        runtime.register_stage2_candidate(state_path, 'S999', _png(tmp_path, 'x'), generation_intent='first')


def test_revise_requires_hard_gate_evidence_and_no_unchanged_rerun(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    first = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'first'), generation_intent='flat mooncake concept')
    with pytest.raises(ValueError, match='STAGE2_REVIEW_EVIDENCE_REQUIRED'):
        runtime.review_stage2_candidate(state_path, first['candidate_id'], 'REVISE')
    runtime.review_stage2_candidate(
        state_path, first['candidate_id'], 'REVISE',
        failed_hard_gate='H2',
        observable_evidence='月饼存在明显侧面厚度和体积阴影',
        required_correction='保持构图不变，将月饼改为正视扁平二维图形')
    with pytest.raises(ValueError, match='STAGE2_UNCHANGED_RERUN'):
        runtime.register_stage2_candidate(
            state_path, 'S001', _png(tmp_path, 'same'), generation_intent='flat mooncake concept')
    second = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'second'),
        generation_intent='replace 3D mooncake with front-view flat 2D mooncake')
    assert second['status'] == 'candidate'


def test_pass_promotes_and_stops_auto_generation_but_user_variant_preserves_old(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    first = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'first'), generation_intent='initial')
    passed = runtime.review_stage2_candidate(
        state_path, first['candidate_id'], 'PASS', review_notes=['人物局部画法与 Anchor 不完全一致'])
    assert passed['status'] == 'approved'
    current1 = runtime.current_stage2_approved_render(state_path, 'S001')
    assert current1['candidate_id'] == first['candidate_id']
    with pytest.raises(ValueError, match='STAGE2_PAGE_ALREADY_APPROVED'):
        runtime.register_stage2_candidate(
            state_path, 'S001', _png(tmp_path, 'auto-extra'), generation_intent='try prettier')

    variant = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'variant'), generation_intent='user requested variant',
        user_requested_variant=True)
    runtime.review_stage2_candidate(
        state_path, variant['candidate_id'], 'REJECT',
        failed_hard_gate='H3',
        observable_evidence='承担核心关系的主体结构整体越界裁切，剩余画面无法通过局部位移恢复完整关系',
        required_correction='重新规划主体结构后再生成完整页面',
        replan_evidence='局部移动或裁切修复无法恢复被截断的主体关系结构')
    assert runtime.current_stage2_approved_render(state_path, 'S001')['candidate_id'] == first['candidate_id']

    variant2 = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'variant2'), generation_intent='user requested second variant',
        user_requested_variant=True)
    runtime.review_stage2_candidate(state_path, variant2['candidate_id'], 'PASS')
    assert runtime.current_stage2_approved_render(state_path, 'S001')['candidate_id'] == variant2['candidate_id']
    state = runtime.load_runtime_state(state_path)
    assert state['stage2_run']['candidates'][first['candidate_id']]['status'] == 'superseded'


def test_visual_completion_and_formal_list_require_one_current_pass_per_page(tmp_path):
    state_path, _ = _start(tmp_path, n=3)
    for sid in ('S001', 'S002'):
        cand = runtime.register_stage2_candidate(
            state_path, sid, _png(tmp_path, sid), generation_intent=f'candidate {sid}')
        runtime.review_stage2_candidate(state_path, cand['candidate_id'], 'PASS')
    status = runtime.stage2_visual_status(state_path)
    assert status == {'status': 'INCOMPLETE', 'missing': ['S003']}
    listed = runtime.list_current_stage2_approved(state_path)
    assert [x['slide_id'] for x in listed] == ['S001', 'S002']

    cand = runtime.register_stage2_candidate(
        state_path, 'S003', _png(tmp_path, 'S003'), generation_intent='candidate S003')
    runtime.review_stage2_candidate(state_path, cand['candidate_id'], 'PASS')
    assert runtime.stage2_visual_status(state_path) == {'status': 'COMPLETE', 'missing': []}
    assert [x['slide_id'] for x in runtime.list_current_stage2_approved(state_path)] == ['S001', 'S002', 'S003']


def test_handoff_requires_truth_and_text_reconciliation_for_every_page(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    cand = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'S001'), generation_intent='candidate')
    runtime.review_stage2_candidate(state_path, cand['candidate_id'], 'PASS')
    assert runtime.stage2_handoff_status(state_path)['status'] == 'INCOMPLETE'

    truth = tmp_path / 'truth.json'
    truth.write_text(json.dumps({'slide_id': 'S001', 'meaningful_text': [], 'exact_facts': []}), encoding='utf-8')
    runtime.register_stage2_artifact(state_path, 'final_content_truth:S001', truth)
    assert runtime.stage2_handoff_status(state_path)['status'] == 'INCOMPLETE'
    runtime.mark_stage2_text_reconciled(state_path, 'S001')
    assert runtime.stage2_handoff_status(state_path) == {'status': 'COMPLETE', 'missing': []}


def test_anchor_page_pass_mode_locks_page_but_style_only_does_not(tmp_path):
    state_path, _ = _start(tmp_path, n=2)
    page_anchor = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'cover'), generation_intent='cover candidates')
    runtime.review_stage2_candidate(
        state_path, page_anchor['candidate_id'], 'PASS', approval_mode='user_selected_anchor_page')
    assert runtime.current_stage2_approved_render(state_path, 'S001')['approval_mode'] == 'user_selected_anchor_page'
    with pytest.raises(ValueError, match='STAGE2_PAGE_ALREADY_APPROVED'):
        runtime.register_stage2_candidate(
            state_path, 'S001', _png(tmp_path, 'cover-again'), generation_intent='batch regeneration')

    # S002 is still unresolved; merely having a style anchor elsewhere cannot approve it.
    assert runtime.current_stage2_approved_render(state_path, 'S002') is None


def test_historical_revise_does_not_block_user_variant_after_later_pass(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    first = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'bad'), generation_intent='concept A')
    runtime.review_stage2_candidate(
        state_path, first['candidate_id'], 'REVISE', failed_hard_gate='H2',
        observable_evidence='出现明显立体厚度', required_correction='改为纯二维正视表达')
    second = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'good'), generation_intent='concept B flat')
    runtime.review_stage2_candidate(state_path, second['candidate_id'], 'PASS')
    # The old unresolved retry rule ended when concept B passed; user may later request any new variant.
    third = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'variant-old-intent'), generation_intent='concept A',
        user_requested_variant=True)
    assert third['status'] == 'candidate'


def test_pass_and_truth_registration_publish_current_paths_to_trusted_slide_state(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    render = _png(tmp_path, 'published-render')
    cand = runtime.register_stage2_candidate(
        state_path, 'S001', render, generation_intent='publish fixture')
    runtime.review_stage2_candidate(state_path, cand['candidate_id'], 'PASS')
    state = runtime.load_runtime_state(state_path)
    assert state['slides']['S001']['approved_render'] == str(render.resolve())

    truth = tmp_path / 'published-truth.json'
    truth.write_text(json.dumps({'slide_id':'S001','meaningful_text':[],'exact_facts':[]}), encoding='utf-8')
    runtime.register_stage2_artifact(state_path, 'final_content_truth:S001', truth)
    state = runtime.load_runtime_state(state_path)
    assert state['slides']['S001']['final_content_truth'] == str(truth.resolve())


def test_new_approved_render_invalidates_page_truth_and_downstream_stage3_artifacts(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    first = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'first-current'), generation_intent='first')
    runtime.review_stage2_candidate(state_path, first['candidate_id'], 'PASS')
    truth = tmp_path / 'truth-v1.json'
    truth.write_text(json.dumps({'slide_id':'S001','meaningful_text':[],'exact_facts':[]}), encoding='utf-8')
    runtime.register_stage2_artifact(state_path, 'final_content_truth:S001', truth)
    runtime.mark_stage2_text_reconciled(state_path, 'S001')
    for kind in ('text_clean', 'graphics_first_pptx'):
        artifact = tmp_path / f'{kind}-v1.bin'
        artifact.write_bytes(kind.encode())
        runtime.register_stage2_artifact(state_path, f'{kind}:S001', artifact)
        assert runtime.stage2_artifact_current(state_path, f'{kind}:S001')

    variant = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'variant-current'), generation_intent='user variant',
        user_requested_variant=True)
    runtime.review_stage2_candidate(state_path, variant['candidate_id'], 'PASS')
    assert not runtime.stage2_artifact_current(state_path, 'final_content_truth:S001')
    assert not runtime.stage2_artifact_current(state_path, 'text_clean:S001')
    assert not runtime.stage2_artifact_current(state_path, 'graphics_first_pptx:S001')


def test_replacing_final_content_truth_invalidates_text_derived_page_artifacts(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    candidate = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'render'), generation_intent='render')
    runtime.review_stage2_candidate(state_path, candidate['candidate_id'], 'PASS')
    truth1 = tmp_path / 'truth-v1.json'
    truth1.write_text(json.dumps({'slide_id':'S001','meaningful_text':[],'exact_facts':[]}), encoding='utf-8')
    runtime.register_stage2_artifact(state_path, 'final_content_truth:S001', truth1)
    runtime.mark_stage2_text_reconciled(state_path, 'S001')
    clean = tmp_path / 'clean-v1.png'; clean.write_bytes(b'old-clean')
    runtime.register_stage2_artifact(state_path, 'text_clean:S001', clean)
    assert runtime.stage2_artifact_current(state_path, 'text_clean:S001')

    truth2 = tmp_path / 'truth-v2.json'
    truth2.write_text(json.dumps({'slide_id':'S001','meaningful_text':[{'text':'new'}],'exact_facts':[]}), encoding='utf-8')
    runtime.register_stage2_artifact(state_path, 'final_content_truth:S001', truth2)
    assert not runtime.stage2_artifact_current(state_path, 'text_clean:S001')


def test_reject_requires_replan_evidence(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    cand = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'reject-no-replan'),
        generation_intent='structural concept')
    with pytest.raises(ValueError, match='STAGE2_REJECT_REPLAN_EVIDENCE_REQUIRED'):
        runtime.review_stage2_candidate(
            state_path, cand['candidate_id'], 'REJECT',
            failed_hard_gate='H1',
            observable_evidence='主要视觉关系与批准语义冲突',
            required_correction='重新规划主要视觉结构')


def test_revise_cannot_contain_replan_evidence(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    cand = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'revise-with-replan'),
        generation_intent='local correction concept')
    with pytest.raises(ValueError, match='STAGE2_REVISE_CANNOT_CONTAIN_REPLAN_EVIDENCE'):
        runtime.review_stage2_candidate(
            state_path, cand['candidate_id'], 'REVISE',
            failed_hard_gate='H2',
            observable_evidence='局部对象存在明显体积',
            required_correction='仅将该对象改为扁平表达',
            replan_evidence='不应出现')


def test_valid_reject_persists_replan_evidence(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    cand = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'valid-reject'),
        generation_intent='structural relationship concept')
    reviewed = runtime.review_stage2_candidate(
        state_path, cand['candidate_id'], 'REJECT',
        failed_hard_gate='H1',
        observable_evidence='主要视觉结构编码了错误关系',
        required_correction='重新规划主要视觉结构',
        replan_evidence='修复该关系必须改变承担核心语义的主要视觉结构')
    assert reviewed['review']['replan_evidence'] == '修复该关系必须改变承担核心语义的主要视觉结构'


def test_historical_reject_without_replan_evidence_remains_loadable_and_resumable(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    candidate = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'legacy-reject'), generation_intent='historical structural concept')
    runtime.review_stage2_candidate(
        state_path, candidate['candidate_id'], 'REJECT',
        failed_hard_gate='H1',
        observable_evidence='主要视觉结构编码了错误关系',
        required_correction='重新规划主要视觉结构',
        replan_evidence='修复核心关系必须改变主要视觉结构')

    state = json.loads(state_path.read_text(encoding='utf-8'))
    state['stage2_run']['candidates'][candidate['candidate_id']]['review'].pop('replan_evidence')
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')

    loaded = runtime.load_runtime_state(state_path)
    legacy = loaded['stage2_run']['candidates'][candidate['candidate_id']]
    assert legacy['status'] == 'reject'
    assert 'replan_evidence' not in legacy['review']

    resumed = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'after-legacy-reject'), generation_intent='new concept after historical reject')
    assert resumed['status'] == 'candidate'


def test_pass_cannot_contain_replan_evidence(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    cand = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'pass-with-replan'),
        generation_intent='pass concept')
    with pytest.raises(ValueError, match='STAGE2_PASS_CANNOT_CONTAIN_HARD_FAILURE'):
        runtime.review_stage2_candidate(
            state_path, cand['candidate_id'], 'PASS',
            replan_evidence='PASS 不得携带结构性失败证据')



def test_runtime_records_but_does_not_semantically_grade_replan_evidence(tmp_path):
    state_path, _ = _start(tmp_path, n=1)
    cand = runtime.register_stage2_candidate(
        state_path, 'S001', _png(tmp_path, 'semantic-boundary'),
        generation_intent='runtime boundary fixture')
    reviewed = runtime.review_stage2_candidate(
        state_path, cand['candidate_id'], 'REJECT',
        failed_hard_gate='H2',
        observable_evidence='局部对象违反二维边界',
        required_correction='仅修改局部对象，其余构图保留',
        replan_evidence='重做更稳')
    assert reviewed['review']['replan_evidence'] == '重做更稳'
