"""Revert only approved light-maintenance changes before inherited checks."""
import json,hashlib,base64
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def data():return json.loads((ROOT/'tests/light_scope.json').read_text(encoding='utf-8'))
def restore_bytes(rel,raw):
    raw=_restore_media(rel,raw)
    entry=data().get(rel)
    if not entry:return raw
    digest=hashlib.sha256(raw).hexdigest()
    if digest==entry['baseline_sha256']:return raw
    assert digest==entry['approved_sha256'],(rel,'unapproved light change')
    return base64.b64decode(entry['baseline_b64'])
def restore_text(rel,text):
    text=_restore_media(rel,text,True)
    entry=data().get(rel)
    if not entry:return text
    digest=hashlib.sha256(text.replace('\r\n','\n').encode()).hexdigest()
    if digest==entry['baseline_text_sha256']:return text
    assert digest==entry['approved_text_sha256'],(rel,'unapproved light text')
    return base64.b64decode(entry['baseline_b64']).decode().replace('\r\n','\n')

def _restore_media(rel,raw,text_mode=False):
    """Reverse only the pinned media-neutrality delta before all historical checks."""
    from editable_scope import restore_bytes as restore_editable
    raw=restore_editable(rel,raw,text_mode)
    entries=json.loads((ROOT/'tests/media_scope.json').read_text(encoding='utf-8'))
    entry=entries.get(rel)
    if entry is None:return raw
    baseline=base64.b64decode(entry['baseline_b64'])
    assert hashlib.sha256(baseline).hexdigest()==entry['baseline_sha256'],(rel,'corrupt media baseline')
    if text_mode:
        baseline=baseline.decode('utf-8').replace('\r\n','\n')
        observed=raw.replace('\r\n','\n')
        digest=hashlib.sha256(observed.encode()).hexdigest()
        assert digest in (entry['baseline_text_sha256'],entry['approved_text_sha256']),(rel,'unapproved media text')
    else:
        digest=hashlib.sha256(raw).hexdigest()
        assert digest in (entry['baseline_sha256'],entry['approved_sha256']),(rel,'unapproved media change')
    return baseline


def normalize_media_manifest(payload):
    """Remove exactly the approved ordered revision entries; reject unknown scopes."""
    from editable_scope import normalize_manifest as normalize_editable
    payload=normalize_editable(payload)
    import copy,yaml
    entry=json.loads((ROOT/'tests/media_scope.json').read_text(encoding='utf-8'))['zanchorflow/manifest.yaml']
    raw=base64.b64decode(entry['baseline_b64'])
    assert hashlib.sha256(raw).hexdigest()==entry['baseline_sha256'],'corrupt media baseline'
    baseline=yaml.safe_load(raw)['revision_scope']
    added=['symmetric_visual_medium_convergence','medium_neutral_render_fragment']
    m=copy.deepcopy(payload)
    assert m['revision_scope'] in (baseline,added+baseline),'undeclared or missing revision scope'
    m['revision_scope']=baseline
    return m
