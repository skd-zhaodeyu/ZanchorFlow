"""Invert this narrow delta before the unchanged WPS/title/publication guards."""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def data():return json.loads((ROOT/'zanchorflow/tests/visual_text_scope.json').read_text(encoding='utf-8'))
def restore_repo_bytes(rel,raw):
    from download_scope import restore_repo_bytes as restore_download
    raw=restore_download(rel,raw)
    import importlib.util
    spec=importlib.util.spec_from_file_location("installation_scope",ROOT/"tools/install_scope.py")
    scope=importlib.util.module_from_spec(spec);spec.loader.exec_module(scope)
    raw=scope.restore_repo_bytes(rel,raw)
    d=data()
    items=[p for p in d['patches'] if p['repo_path']==rel]
    if items:
        text=raw.decode('utf-8')
        for p in reversed(items):
            assert text.count(p['new'])==1,(rel,'declared visual/text delta changed')
            text=text.replace(p['new'],p['old'],1)
        raw=text.encode('utf-8')
    expected=d['baseline'].get(rel)
    if expected:assert hashlib.sha256(raw).hexdigest()==expected,(rel,'undeclared change')
    return raw
def restore_repo_text(rel,text):
    from download_scope import restore_repo_text as restore_download
    text=restore_download(rel,text)
    for p in reversed(data()['patches']):
        if p['repo_path']==rel:
            old=p['old'].replace('\r\n','\n');new=p['new'].replace('\r\n','\n')
            assert text.count(new)==1,(rel,'declared visual/text document delta changed')
            text=text.replace(new,old,1)
    return text
def normalize_manifest(payload):
    m=copy.deepcopy(payload);d=data()
    assert m['revision_scope']==d['baseline_revision_scope']+d['added_revision_scope'],'undeclared or missing revision scope'
    m['revision_scope']=d['baseline_revision_scope']
    return m
