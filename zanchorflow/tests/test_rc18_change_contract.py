from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / 'references'


def _one(pattern):
    matches = list(REFS.glob(pattern))
    assert len(matches) == 1, matches
    return matches[0].read_text(encoding='utf-8')


def test_zanchorflow_identity_and_rc18_protocol_baseline():
    raw = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
    fm = yaml.safe_load(raw.split('---', 2)[1])
    manifest = yaml.safe_load((ROOT / 'manifest.yaml').read_text(encoding='utf-8'))
    assert fm['name'] == 'zanchorflow'
    assert '# ZAnchorFlow' in raw
    assert manifest['skill_name'] == 'zanchorflow'
    assert ROOT.name == 'zanchorflow'
    assert manifest['skill_version'] == '0.9.0-rc19-candidate'
    assert manifest['protocol_baseline'] == 'RC17'
    assert '03_PPT视觉探索与Anchor延续协议_v2.12.md' in raw
    assert '04_页面二维生成前置约束与渲染协议_v2.9.md' in raw
    assert '07_Stage3_文字处理_消字与复原规范_v1.5.md' in raw
    assert '08_Image_Layer_Model可编辑PPT重建协议_v1.1.md' in raw


def test_poster_task_itself_authorizes_typography_as_candidate_carrier():
    t03 = _one('03_PPT视觉探索与Anchor延续协议_v*.md')
    t04 = _one('04_页面二维生成前置约束与渲染协议_v*.md')
    assert 'poster / promotional / display-oriented communication task' in t03
    assert '构成当前页面对展示性 Typography 作为候选 `primary_visual_carrier` 的页面级授权' in t03
    assert '不要求 Typography-first' in t03
    assert '不得仅因展示性 Typography 成为第一视觉焦点而自动判定 H2' in t04
    assert 'mandatory information' in t04


def test_native_text_visual_fit_has_positive_rendering_tolerance_examples():
    t07 = _one('07_Stage3_文字处理_消字与复原规范_v*.md')
    assert '轻微字体渲染差异本身不得单独导致 `TEXT_VISUAL_FIT_UNRESOLVED`' in t07
    assert '较大字号恢复后笔画略偏细或略偏粗' in t07
    assert '字面宽度、笔画重量或字形轮廓存在小幅差异' in t07
    assert '轻度艺术化字体无法完全复刻原图字形' in t07
    assert '明显视觉失真、层级变化、版式偏移、裁切、溢出或重叠' in t07


def test_operational_runtime_recovery_guidance_is_narrow_and_state_driven():
    skill = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
    doc = (ROOT / 'docs' / 'codex-canva-bridge.md').read_text(encoding='utf-8')
    assert 'Operational Runtime Recovery' in skill
    assert 'same-operation recovery affordance' in skill
    assert '不会跨越用户决策或权限边界' in skill
    assert '不会启动新的生成、重建、导出任务或其他新的昂贵远程工作' in skill
    assert 'single unknown / no-event / no-file' in doc
    assert 'same-operation recovery affordance' in doc
    assert 'does not reset the existing post-click observation budget' in doc
    assert 'does not create a new numbered acquisition' in doc


def test_stage3_orchestration_points_only_to_current_text_protocol():
    t06=(ROOT/'references'/'06_Canva_Magic_Layers可编辑PPT重建协议_v2.4.md').read_text(encoding='utf-8')
    assert t06.count('Stage3_文字处理_消字与复原规范 v1.5') == 3
    assert 'Stage3_文字处理_消字与复原规范 v1.4' not in t06
