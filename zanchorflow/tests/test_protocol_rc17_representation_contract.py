from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / 'references'


def test_04_v2_9_preserves_rendering_boundaries_and_uses_single_primary_gate():
    p04 = REFS / '04_页面二维生成前置约束与渲染协议_v2.9.md'
    assert p04.exists()
    text = p04.read_text(encoding='utf-8')
    assert 'failed_hard_gate: H1 | H2 | H3 | H4' in text
    assert 'primary Hard Gate' in text
    assert '如存在多个 Hard Failure，可列出多个 gate' not in text
    assert 'preserve the upstream-selected primary visual carrier and expressive mechanism' in text.lower()
    assert 'OPAQUE_FULL_SLIDE' in text
    assert 'NON_COVER' in text
    assert 'Irreducible Content Overload' in text


def test_04_v2_9_makes_revise_gate_agnostic_and_reject_require_replan_evidence():
    text = (REFS / '04_页面二维生成前置约束与渲染协议_v2.9.md').read_text(encoding='utf-8')
    assert '任何局部 Hard Failure' in text
    assert '不得仅因 Gate 类型扩大 correction scope' in text
    assert 'replan_evidence' in text
    assert 'targeted revision' in text
    assert '为什么 targeted revision' in text
    assert '只需局部修改' in text and '不得 `REJECT`' in text


def test_04_v2_9_uses_generic_h2_patterns_and_removes_duplicate_summary_gate():
    text = (REFS / '04_页面二维生成前置约束与渲染协议_v2.9.md').read_text(encoding='utf-8')
    assert '月饼型案例' not in text
    assert '背景长城型案例' not in text
    assert 'NON_COVER 技术流程页—大标题主导案例' not in text
    assert 'minor illustrative depth cue' in text
    assert 'volumetric primary object' in text
    assert 'whole-page isometric / axonometric spatial mechanism' in text
    assert '# 17.10 生成后最低必要重大违规清单' not in text
    assert 'no additional summary gate exists' in text
