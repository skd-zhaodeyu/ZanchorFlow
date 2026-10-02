from pathlib import Path
import yaml

def test_skill_frontmatter_and_runtime_governance():
    root = Path(__file__).resolve().parents[1]
    raw = (root/'SKILL.md').read_text(encoding='utf-8')
    assert raw.startswith('---\n')
    fm = yaml.safe_load(raw.split('---',2)[1])
    assert fm['name'] == 'zanchorflow'
    assert '# ZAnchorFlow' in raw
    assert fm['description'].startswith('Use when ')
    manifest = yaml.safe_load((root/'manifest.yaml').read_text(encoding='utf-8'))
    assert manifest['skill_version'] == '0.9.0-rc19-candidate'
    assert manifest['protocol_baseline'] == 'RC17'
    refs = manifest['canonical_protocols']
    assert len(refs) == 8
    assert {x['path'] for x in refs} == {f'references/{p.name}' for p in (root/'references').glob('*.md')}
    assert all(x['classification'] == 'runtime' for x in refs)
    assert not (root/'archive').exists()
    assert 'validation/' not in raw


def test_rc18_has_exactly_one_image_layer_protocol():
    root=Path(__file__).resolve().parents[1]
    names=[p.name for p in (root/'references').glob('08_*')]
    assert names == ['08_Image_Layer_Model可编辑PPT重建协议_v1.1.md']
