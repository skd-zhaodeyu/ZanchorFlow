import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from runtime import (resume_stage, validate_deck_order, retry_transition, source_fingerprint,
                     record_stage1_draft, present_stage1_review, handle_stage1_reply,
                     start_stage2_run, register_stage2_artifact, register_stage2_candidate,
                     review_stage2_candidate, mark_stage2_text_reconciled,
                     present_stage2_formal_display, seal_stage2_visual_approval)
from stage2_test_helpers import write_png, write_truth


def test_resume_from_earliest_unresolved_state(tmp_path):
    assert resume_stage({}) == 'stage1'
    assert resume_stage({'outline': True}) == 'AWAITING_STAGE1_APPROVAL'
    outline = {'slides': [{field: field for field in (
        'page_task', 'title', 'core_expression', 'key_information',
        'semantic_relation', 'acceptance_criteria')}]}
    outline_path = tmp_path / 'outline.json'
    outline_path.write_text(json.dumps(outline), encoding='utf-8')
    state_path = tmp_path / 'state.json'
    state_path.write_text('{"slides":{}}', encoding='utf-8')
    record_stage1_draft(state_path, outline_path)
    present_stage1_review(state_path)
    handle_stage1_reply(state_path, '同意，按这个继续。', decision='approve')
    assert resume_stage({'outline': True}, state_path) == 'stage2_exploration'
    start_stage2_run(state_path)
    for kind in ('anchor', 'style_dna'):
        file = tmp_path / kind
        file.write_bytes(kind.encode())
        register_stage2_artifact(state_path, kind, file)
    assert resume_stage({'outline': True, 'anchor': True, 'style_dna': True}, state_path) == 'stage2_production'

    render = write_png(tmp_path / 'render.png')
    candidate = register_stage2_candidate(state_path, 'S001', render, generation_intent='fixture')
    review_stage2_candidate(state_path, candidate['candidate_id'], 'PASS')
    assert resume_stage({'outline': True}, state_path) == 'AWAITING_USER_VISUAL_APPROVAL'
    present_stage2_formal_display(state_path)
    seal_stage2_visual_approval(state_path, '确认，按这组页面进入下一阶段。')
    assert resume_stage({'outline': True}, state_path) == 'stage2_to_stage3_handoff'

    truth = write_truth(tmp_path / 'truth.json', 'S001')
    register_stage2_artifact(state_path, 'final_content_truth:S001', truth)
    mark_stage2_text_reconciled(state_path, 'S001')
    assert resume_stage({'approved_render': True, 'final_content_truth': True}, state_path) == 'stage3_text_preparation'

    clean = tmp_path / 'clean.png'
    clean.write_bytes(b'clean')
    register_stage2_artifact(state_path, 'text_clean:S001', clean)
    assert resume_stage({'slide_id': 'S001', 'approved_render': True, 'final_content_truth': True,
                         'text_clean': True, 'text_clean_fingerprint_matches': True}, state_path) == 'stage3_reconstruction_backend_selection'
    assert resume_stage({'validated_single_page_pptx': True}) != 'deck_merge'


def test_order_and_retry_boundaries():
    assert validate_deck_order(['S2','S1'], ['S1','S2'])
    assert not validate_deck_order(['S1','S1'], ['S1','S2'])
    assert retry_transition('available', 'structural_failure') == 'pending'
    assert retry_transition('pending', 'tool_failure') == 'pending'
    assert retry_transition('pending', 'assessable_result') == 'consumed'


def test_source_fingerprint_changes_with_inputs():
    a = source_fingerprint(b'a', {'text':'x'}, {'width':10,'height':5})
    assert a == source_fingerprint(b'a', {'text':'x'}, {'height':5,'width':10})
    assert a != source_fingerprint(b'b', {'text':'x'}, {'width':10,'height':5})
