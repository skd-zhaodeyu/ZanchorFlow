import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import runtime
from stage2_test_helpers import write_png

FIELDS = (
    'page_task', 'title', 'core_expression', 'key_information',
    'semantic_relation', 'acceptance_criteria'
)


def _outline_case(tmp_path, n=3):
    outline = {'slides': [
        {field: f'{field}-{i+1}' for field in FIELDS}
        for i in range(n)
    ]}
    outline_path = tmp_path / 'outline.json'
    outline_path.write_text(json.dumps(outline, ensure_ascii=False), encoding='utf-8')
    state_path = tmp_path / 'state.json'
    state_path.write_text('{"slides":{}}', encoding='utf-8')
    runtime.record_stage1_draft(state_path, outline_path)
    runtime.present_stage1_review(state_path)
    return state_path, outline_path


def _start_stage2(tmp_path, n=1):
    state, _ = _outline_case(tmp_path, n)
    runtime.handle_stage1_reply(state, '好', decision='approve')
    runtime.start_stage2_run(state)
    return state


def test_stage1_reply_uses_structured_contextual_decision_not_phrase_whitelist(tmp_path):
    state, _ = _outline_case(tmp_path)
    result = runtime.handle_stage1_reply(state, '好', decision='approve')
    assert result['status'] == 'approved'


def test_stage1_reply_requires_explicit_structured_decision(tmp_path):
    state, _ = _outline_case(tmp_path)
    with pytest.raises(ValueError, match='STAGE1_DECISION_REQUIRED'):
        runtime.handle_stage1_reply(state, '可以，继续。')


def test_stage1_unclear_decision_keeps_gate_pending_even_if_words_sound_positive(tmp_path):
    state, _ = _outline_case(tmp_path)
    result = runtime.handle_stage1_reply(state, '好', decision='unclear')
    assert result['status'] == 'review_pending'


def test_stage1_cli_carries_structured_decision_instead_of_keyword_matching(tmp_path):
    state, _ = _outline_case(tmp_path)
    command = [sys.executable, str(ROOT / 'scripts' / 'runtime.py'), 'stage1-reply',
               '--state', str(state), '--message', '好', '--decision', 'approve']
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload['status'] == 'approved'


def test_stage1_cli_missing_structured_decision_is_blocked(tmp_path):
    state, _ = _outline_case(tmp_path)
    command = [sys.executable, str(ROOT / 'scripts' / 'runtime.py'), 'stage1-reply',
               '--state', str(state), '--message', '可以，继续。']
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'STAGE1_DECISION_REQUIRED' in result.stdout


def test_preapproved_outline_action_does_not_reparse_user_words(tmp_path):
    state, outline = _outline_case(tmp_path)
    record = runtime.accept_preapproved_outline(state, outline, '照这份做，不再审了。')
    assert record['approval_mode'] == 'preapproved_supplied_outline'


def test_visual_approval_action_does_not_reparse_user_words(tmp_path):
    state = _start_stage2(tmp_path, 1)
    candidate_path = write_png(tmp_path / 'S001.png', b'candidate')
    candidate = runtime.register_stage2_candidate(state, 'S001', candidate_path, 'test')
    runtime.review_stage2_candidate(state, candidate['candidate_id'], 'PASS')
    shown = runtime.present_stage2_formal_display(state)
    assert shown['status'] == 'COMPLETE'
    approval = runtime.seal_stage2_visual_approval(state, '好')
    assert approval['status'] == 'approved'


def test_protocol_rc17_pre_stage3_behavior_is_explicit():
    p01 = ROOT / 'references' / '01_PPT内容架构与大纲生成协议_v1.2.md'
    p03 = ROOT / 'references' / '03_PPT视觉探索与Anchor延续协议_v2.12.md'
    assert p01.exists() and p03.exists()
    t01 = p01.read_text(encoding='utf-8')
    t03 = p03.read_text(encoding='utf-8')
    assert '同义复述' in t01
    assert '实际信息增量' in t01
    assert '去除标题与 `core_expression`' in t01
    assert '默认不得成为 `primary_visual_carrier`' in t03
    assert '默认不得使用展示性大字号标题或其他标题文字作为页面主视觉' in t03
    assert '不得从 Anchor、Style DNA、前页或模型自身审美偏好推导该例外' in t03
    assert 'primary_visual_carrier' in t03
    assert '默认生成接下来的 3 个' in t03
    assert '用户明确指定预览页数或页面范围' in t03
    assert '不计入该预览数量' in t03
    t04 = (ROOT / 'references' / '04_页面二维生成前置约束与渲染协议_v2.9.md').read_text(encoding='utf-8')
    assert '第一视觉焦点、主要构图主体或实际 `primary_visual_carrier`' in t04
    assert '明显高于正文的正常标题层级也不属于 H2' in t04


def test_rc18_manifest_keeps_rc17_protocols_and_adds_image_layer_08():
    manifest = yaml.safe_load((ROOT / 'manifest.yaml').read_text(encoding='utf-8'))
    assert manifest['skill_version'] == '1.0'
    assert manifest['protocol_baseline'] == 'RC17'
    paths = {item['path'] for item in manifest['canonical_protocols']}
    assert 'references/01_PPT内容架构与大纲生成协议_v1.2.md' in paths
    assert 'references/03_PPT视觉探索与Anchor延续协议_v2.12.md' in paths
    assert 'references/02_Stage1至Stage2语义接口协议_v1.0.md' in paths
    assert 'references/04_页面二维生成前置约束与渲染协议_v2.9.md' in paths
    assert 'references/05_Stage2至Stage3_Magic_Layers接口协议_v1.4.md' in paths
    assert 'references/06_Canva_Magic_Layers可编辑PPT重建协议_v2.4.md' in paths
    assert 'references/07_Stage3_文字处理_消字与复原规范_v1.5.md' in paths
    assert 'references/08_Image_Layer_Model可编辑PPT重建协议_v1.1.md' in paths
    assert len(paths) == 8
