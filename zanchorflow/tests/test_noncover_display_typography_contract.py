from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / 'references'


def _read_one(prefix: str) -> str:
    matches = list(REFS.glob(prefix))
    assert len(matches) == 1, matches
    return matches[0].read_text(encoding='utf-8')


def test_noncover_title_cannot_be_default_primary_visual_carrier():
    text = _read_one('03_PPT视觉探索与Anchor延续协议_v*.md')
    assert 'NON_COVER' in text
    assert '默认不得成为 `primary_visual_carrier`' in text
    assert '只有用户明确要求当前具体非封面页面' in text


def test_page_local_oversized_title_composition_is_excluded_from_style_dna():
    text = _read_one('03_PPT视觉探索与Anchor延续协议_v*.md')
    assert '标题的具体字号尺度、占屏比例、标题主视觉化程度及展示性大字构图' in text
    assert '不得从 Anchor、Style DNA、前页或模型自身审美偏好推导该例外' in text


def test_h2_rejects_noncover_title_dominance_without_user_exception():
    text = _read_one('04_页面二维生成前置约束与渲染协议_v*.md')
    assert 'NON_COVER' in text
    assert '第一视觉焦点' in text
    assert '实际 `primary_visual_carrier`' in text
    assert '用户明确例外要求' in text


def test_h2_keeps_normal_noncover_title_hierarchy_legal():
    text = _read_one('04_页面二维生成前置约束与渲染协议_v*.md')
    assert '明显高于正文的正常标题层级' in text
    assert '不属于 H2' in text
    assert 'NON_COVER normal heading hierarchy' in text


def test_noncover_scope_is_defined_without_auto_exceptions():
    t03 = _read_one('03_PPT视觉探索与Anchor延续协议_v*.md')
    t04 = _read_one('04_页面二维生成前置约束与渲染协议_v*.md')
    scope = '`NON_COVER` 指除封面 / Cover 之外的全部正式 PPT 页面'
    assert scope in t03
    assert scope in t04
    assert '章节页自动例外' not in t03
    assert '过渡页自动例外' not in t03
