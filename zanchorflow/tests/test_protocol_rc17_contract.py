import hashlib
from pathlib import Path

from refinement_scope import inherited_doc

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / 'references'

FROZEN = {
    '01_PPT内容架构与大纲生成协议_v1.2.md': '62bf923e7365cbbae3083c381153e8e878cf09ef053ecd7354dd2296e4b9f9f2',
    '02_Stage1至Stage2语义接口协议_v1.0.md': '94a8348df76474d5ffd918338faa4020b36962c1a837facd7eb6e1b4f95ba17a',
    '05_Stage2至Stage3_Magic_Layers接口协议_v1.4.md': '9093342b1057a902407f44e71523ba30efd2305a1f05edb1ee3a0466c0d238cf',
}
FROZEN_PRODUCTION = {
    'scripts/acquisition_request.py': '5696a4c475ea7796c24b0db9c562ef5f54b4e44f679f86755b4d4d79fa5ac949',
    'scripts/canva_pptx_finalize.ps1': 'c05cbcfb20a9b7144e5a0310e8e84eae5ec5ab2cccd946d198bc27a8ff808107',
    'scripts/merge_pptx.py': 'e20887218fd4791bbdee14e0dc4751bb23498f75ceacd062a369862bdc7e05e7',
    # RC19 intentionally changes preflight for conditional Image Layer geometry dependencies.
    'scripts/package_skill.py': '566aa5ee56dbaea0a69e78efcd9399d5afcf1c23262c7020706ff2bec785c037',
}


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def test_rc17_frozen_protocol_and_unrelated_production_hashes():
    for name, expected in FROZEN.items():
        assert hashlib.sha256(inherited_doc('references/'+name,(REFS/name).read_text(encoding='utf-8')).encode()).hexdigest() == expected
    for rel, expected in FROZEN_PRODUCTION.items():
        assert _sha(ROOT / rel) == expected


def test_03_v2_12_semantic_guard_and_replan_neutrality_contract():
    p03 = REFS / '03_PPT视觉探索与Anchor延续协议_v2.12.md'
    assert p03.exists()
    text = p03.read_text(encoding='utf-8')
    assert '未经支持的事实性结论或具体身份主张' in text
    assert '- 未提供的实体或结论。' not in text
    assert 'Semantic Elaboration Freedom' in text
    assert '本协议不另设第二套内容扩展强度' in text
    assert 'page_task' in text and 'semantic invariants' in text
    assert '`REJECT` 本身不产生' in text
    assert 'replan_evidence' in text
    assert '用户要求' in text and '简化' in text and 'carrier' in text and '构图' in text


def test_03_v2_12_preserves_representation_convergence_without_quota():
    text = (REFS / '03_PPT视觉探索与Anchor延续协议_v2.12.md').read_text(encoding='utf-8')
    assert 'Candidate-set Representation Convergence Check' in text
    assert '不得因为几何、节点、线条或模块结构更容易生成或更容易满足二维约束' in text
    assert '不要求候选必须包含插画' in text
    assert '流程、数据、结构、关系' in text
    assert '装饰性人物、图标或小场景' in text


def test_rc17_noncover_title_contract_remains_present():
    t03=(REFS/'03_PPT视觉探索与Anchor延续协议_v2.12.md').read_text(encoding='utf-8')
    t04=(REFS/'04_页面二维生成前置约束与渲染协议_v2.9.md').read_text(encoding='utf-8')
    assert '默认不得使用展示性大字号标题或其他标题文字作为页面主视觉' in t03
    assert '默认不得成为 `primary_visual_carrier`' in t03
    assert '第一视觉焦点、主要构图主体或实际 `primary_visual_carrier`' in t04
    assert '明显高于正文的正常标题层级也不属于 H2' in t04
