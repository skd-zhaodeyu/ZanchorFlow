"""Protocol contracts only; not a model-behavior or visual-quality evaluation."""
from pathlib import Path
import base64, hashlib, json
import pytest
ROOT = Path(__file__).resolve().parents[1]

def protocol(prefix):
    return next((ROOT/'references').glob(prefix+'*')).read_text(encoding='utf-8')

def section(text, start, end):
    return text.split(start,1)[1].split(end,1)[0]

def test_candidate_convergence_check_is_symmetric_and_bounded():
    current=section(protocol('03_'),'## 7.2 Candidate-set Representation Convergence Check','## 7.3')
    assert '该检查对插画、图解、信息图、几何构成、技术线稿及其他合法媒介对称适用' in current
    assert '不得仅因候选采用相同媒介而自动增加候选、生图或返工' in current
    assert '不要求候选必须包含插画' in current
    assert '不是建立插画配额、固定媒介菜单或新的 Style Family' in current

def test_generic_render_fragment_inherits_medium_without_illustration_directive():
    fragment=section(protocol('04_'),'# 15. Standard Negative Boundary Fragment','# 16.')
    assert 'Render the selected concept in the upstream-selected visual medium, preserving its expressive mechanism within the current 2D and non-photographic boundaries.' in fragment
    assert 'Local perspective, side faces and thickness cues may support that expression when permitted by the current rendering mode.' in fragment
    assert 'graphic layering and illustration' not in fragment
    assert 'Do not use photographs, stock-photo aesthetics, photo collage,' in fragment
    assert 'Do not use HUD glow, neon glow, luminous nodes, luminous lines,' in fragment


def media_entries():
    return json.loads((ROOT/'tests/media_scope.json').read_text(encoding='utf-8'))

@pytest.mark.parametrize('prefix',['03_','04_'])
def test_only_approved_protocol_delta_restores_and_rejects_tampering(prefix):
    from light_scope import _restore_media
    path=next((ROOT/'references').glob(prefix+'*'))
    rel='zanchorflow/'+path.relative_to(ROOT).as_posix()
    entry=media_entries()[rel];raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==entry['approved_sha256']
    baseline=base64.b64decode(entry['baseline_b64'])
    assert _restore_media(rel,raw)==baseline
    assert _restore_media(rel,baseline)==baseline
    assert _restore_media(rel,path.read_text(encoding='utf-8'),True)==baseline.decode().replace('\r\n','\n')
    for bad in (raw+b'\n# undeclared',raw.replace(b'Runtime',b'AlteredRuntime',1)):
        assert bad!=raw
        with pytest.raises(AssertionError,match='unapproved (media|editable)'):_restore_media(rel,bad)
    with pytest.raises(AssertionError,match='unapproved (media|editable)'):
        _restore_media(rel,path.read_text(encoding='utf-8')+'\n# undeclared',True)

def test_generic_negative_boundaries_unchanged_after_first_two_sentences():
    path=next((ROOT/'references').glob('04_*'));rel='zanchorflow/'+path.relative_to(ROOT).as_posix()
    old=base64.b64decode(media_entries()[rel]['baseline_b64']).decode()
    new=path.read_bytes().decode()
    marker='Do not make isometric/axonometric space'
    assert old.split(marker,1)[1]==new.split(marker,1)[1]

def test_all_runtime_scripts_keep_pre_revision_bytes():
    pinned=media_entries()['protected_runtime_scripts']
    paths={p.relative_to(ROOT.parent).as_posix():p for p in (ROOT/'scripts').iterdir() if p.is_file()}
    from editable_scope import new_runtime,restore_bytes
    added={'zanchorflow/'+rel:digest for rel,digest in new_runtime().items()}
    assert set(paths)==set(pinned)|set(added)
    for rel,path in paths.items():
        if rel in added:assert hashlib.sha256(path.read_bytes()).hexdigest()==added[rel],rel
        else:assert hashlib.sha256(restore_bytes(rel,path.read_bytes())).hexdigest()==pinned[rel],rel


def test_manifest_scope_normalization_retains_exact_order_and_rejects_unknown_changes():
    import copy,yaml
    from light_scope import normalize_media_manifest
    payload=yaml.safe_load((ROOT/'manifest.yaml').read_text(encoding='utf-8'))
    original=copy.deepcopy(payload)
    baseline=yaml.safe_load(base64.b64decode(media_entries()['zanchorflow/manifest.yaml']['baseline_b64']))
    assert normalize_media_manifest(payload)['revision_scope']==baseline['revision_scope']
    assert payload==original
    for bad in (payload['revision_scope']+['unapproved'],payload['revision_scope'][1:],list(reversed(payload['revision_scope']))):
        altered=copy.deepcopy(payload);altered['revision_scope']=bad
        with pytest.raises(AssertionError,match='undeclared or missing'):normalize_media_manifest(altered)


@pytest.mark.parametrize('rel',['zanchorflow/manifest.yaml','tools/install.py','zanchorflow/tests/office_scope.py'])
def test_maintenance_adapters_restore_exact_baselines_and_reject_tampering(rel):
    from light_scope import _restore_media
    entry=media_entries()[rel];raw=(ROOT.parent/rel).read_bytes()
    baseline=base64.b64decode(entry['baseline_b64'])
    assert _restore_media(rel,raw)==baseline
    assert _restore_media(rel,baseline)==baseline
    assert _restore_media(rel,raw.decode(),True)==baseline.decode().replace('\r\n','\n')
    with pytest.raises(AssertionError,match='unapproved (media|editable)'):_restore_media(rel,raw+b'\n# undeclared')
