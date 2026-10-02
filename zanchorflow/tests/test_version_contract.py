from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]

def test_rc18_version_and_protocol_baseline():
    manifest=yaml.safe_load((ROOT/'manifest.yaml').read_text(encoding='utf-8'))
    assert manifest['skill_version']=='0.9.0-rc19-candidate'
    assert manifest['protocol_baseline']=='RC17'
    paths={x['path'] for x in manifest['canonical_protocols']}
    assert 'references/01_PPT内容架构与大纲生成协议_v1.2.md' in paths
    assert 'references/03_PPT视觉探索与Anchor延续协议_v2.12.md' in paths
    assert 'references/04_页面二维生成前置约束与渲染协议_v2.9.md' in paths
    assert 'references/06_Canva_Magic_Layers可编辑PPT重建协议_v2.4.md' in paths
    assert 'references/07_Stage3_文字处理_消字与复原规范_v1.5.md' in paths
    assert 'references/08_Image_Layer_Model可编辑PPT重建协议_v1.1.md' in paths

def test_skill_routes_to_rc16_single_acquisition_contract():
    raw=(ROOT/'SKILL.md').read_text(encoding='utf-8')
    assert 'existing release labels describe the source baseline' in raw
    assert '01_PPT内容架构与大纲生成协议_v1.2.md' in raw
    assert '03_PPT视觉探索与Anchor延续协议_v2.12.md' in raw
    assert '04_页面二维生成前置约束与渲染协议_v2.9.md' in raw
    content=(ROOT/'references'/'01_PPT内容架构与大纲生成协议_v1.2.md').read_text(encoding='utf-8')
    assert "See each step's Runtime dispatch for exact commands" in raw
    assert '--decision <approve|revise|rework|unclear>' in content
    assert 'not by matching a fixed phrase list' in raw
    magic=(ROOT/'references'/'06_Canva_Magic_Layers可编辑PPT重建协议_v2.4.md').read_text(encoding='utf-8')
    assert 'recovery-first' in magic.lower() or '恢复优先' in magic
    assert 'spent query/UI budgets carried forward' not in raw


def test_runtime_bridge_and_installation_are_current():
    bridge=(ROOT/'docs/codex-canva-bridge.md').read_text(encoding='utf-8')
    install=(ROOT/'docs/installation.md').read_text(encoding='utf-8')
    assert bridge.startswith('# Codex Canva host bridge — RC17')
    assert '0.9.0-rc19-candidate' in install
    assert 'Protocol Baseline RC17' in install
    assert 'Protocol Baseline RC11' not in install


def test_legacy_current_protocol_versions_are_not_packaged():
    names={p.name for p in (ROOT/'references').glob('*.md')}
    assert '03_PPT视觉探索与Anchor延续协议_v2.10.md' not in names
    assert '04_页面二维生成前置约束与渲染协议_v2.7.md' not in names
