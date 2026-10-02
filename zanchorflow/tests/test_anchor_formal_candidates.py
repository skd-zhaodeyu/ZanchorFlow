import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import runtime
from stage2_test_helpers import write_png

FIELDS = ('page_task','title','core_expression','key_information','semantic_relation','acceptance_criteria')


def _start(tmp_path):
    outline = tmp_path / 'outline.json'
    outline.write_text(json.dumps({'slides': [{f: f'{f}-1' for f in FIELDS}]}, ensure_ascii=False), encoding='utf-8')
    state = tmp_path / 'state.json'
    state.write_text('{"slides":{}}', encoding='utf-8')
    runtime.record_stage1_draft(state, outline)
    runtime.present_stage1_review(state)
    runtime.handle_stage1_reply(state, '同意，按这个继续。', decision='approve')
    runtime.start_stage2_run(state)
    return state


def _candidate(state, tmp_path, name, intent):
    return runtime.register_stage2_candidate(state, 'S001', write_png(tmp_path/f'{name}.png', name.encode()), intent)


def test_anchor_formal_set_excludes_revise_and_keeps_two_qualified_compositions(tmp_path):
    state = _start(tmp_path)
    a1 = _candidate(state, tmp_path, 'A1', 'composition A initial')
    runtime.review_stage2_candidate(
        state, a1['candidate_id'], 'REVISE', failed_hard_gate='H3',
        observable_evidence='核心装饰被裁切', required_correction='保持构图 A，仅修正裁切')
    a2 = _candidate(state, tmp_path, 'A2', 'composition A corrected crop')
    runtime.review_stage2_candidate(state, a2['candidate_id'], 'PASS', approval_mode='anchor_exploration_candidate')
    b1 = _candidate(state, tmp_path, 'B1', 'composition B')
    runtime.review_stage2_candidate(state, b1['candidate_id'], 'PASS', approval_mode='anchor_exploration_candidate')

    display = runtime.present_anchor_formal_candidates(state, 'S001')
    assert display['status'] == 'COMPLETE'
    assert [x['candidate_id'] for x in display['candidates']] == [a2['candidate_id'], b1['candidate_id']]
    assert a1['candidate_id'] not in {x['candidate_id'] for x in display['candidates']}
    assert runtime.current_stage2_approved_render(state, 'S001') is None


def test_anchor_formal_set_excludes_multiple_failed_history_and_does_not_scan_files(tmp_path):
    state = _start(tmp_path)
    failed_ids = []
    revise = _candidate(state, tmp_path, 'bad1', 'local volumetric object')
    failed_ids.append(revise['candidate_id'])
    runtime.review_stage2_candidate(
        state, revise['candidate_id'], 'REVISE', failed_hard_gate='H2',
        observable_evidence='局部主对象存在明显实体厚度',
        required_correction='保留主要构图，仅将该对象改为扁平二维表达')

    reject = _candidate(state, tmp_path, 'bad2', 'whole-page volumetric spatial mechanism')
    failed_ids.append(reject['candidate_id'])
    runtime.review_stage2_candidate(
        state, reject['candidate_id'], 'REJECT', failed_hard_gate='H2',
        observable_evidence='整页主要空间机制依赖等距透视和实体体积',
        required_correction='重新规划不依赖三维空间的主要视觉机制',
        replan_evidence='局部扁平化无法保留当前以三维空间为主体的视觉机制')
    good = _candidate(state, tmp_path, 'good', 'qualified flat concept')
    runtime.review_stage2_candidate(state, good['candidate_id'], 'PASS', approval_mode='anchor_exploration_candidate')
    write_png(tmp_path/'unregistered-history.png', b'history')
    display = runtime.present_anchor_formal_candidates(state, 'S001')
    assert [x['candidate_id'] for x in display['candidates']] == [good['candidate_id']]
    assert not ({*failed_ids} & {x['candidate_id'] for x in display['candidates']})


def test_anchor_selection_requires_formally_displayed_qualified_candidate(tmp_path):
    state = _start(tmp_path)
    a = _candidate(state, tmp_path, 'A', 'composition A')
    runtime.review_stage2_candidate(state, a['candidate_id'], 'PASS', approval_mode='anchor_exploration_candidate')
    b = _candidate(state, tmp_path, 'B', 'composition B')
    runtime.review_stage2_candidate(state, b['candidate_id'], 'PASS', approval_mode='anchor_exploration_candidate')
    shown = runtime.present_anchor_formal_candidates(state, 'S001')
    assert shown['candidate_set_fingerprint']
    selected = runtime.select_anchor_candidate(state, 'S001', a['candidate_id'])
    assert selected['candidate_id'] == a['candidate_id']
    current = runtime.current_stage2_approved_render(state, 'S001')
    assert current['candidate_id'] == a['candidate_id']
    assert current['approval_mode'] == 'user_selected_anchor_page'


def test_normal_page_pass_semantics_are_unchanged(tmp_path):
    state = _start(tmp_path)
    c = _candidate(state, tmp_path, 'normal', 'normal page candidate')
    runtime.review_stage2_candidate(state, c['candidate_id'], 'PASS')
    assert runtime.current_stage2_approved_render(state, 'S001')['candidate_id'] == c['candidate_id']
