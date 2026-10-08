"""Invert exactly this approved delta before inherited byte and identity checks."""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def data():return json.loads((ROOT/'tests/office_scope.json').read_text(encoding='utf-8'))
def restore_repo_bytes(rel,raw):
    from visual_text_scope import restore_repo_bytes as restore_visual
    raw=restore_visual(rel,raw)
    text=raw.decode('utf-8'); d=data()
    for item in reversed(d['patches']):
        if item['repo_path']==rel:
            assert text.count(item['new'])==1,(rel,'declared WPS delta changed')
            text=text.replace(item['new'],item['old'],1)
    expected=d['baseline'].get(rel)
    if expected:assert hashlib.sha256(text.encode('utf-8')).hexdigest()==expected,(rel,'undeclared change')
    return text.encode('utf-8')
def restore_repo_text(rel,text):
    from visual_text_scope import restore_repo_text as restore_visual
    text=restore_visual(rel,text)
    for item in reversed(data()['patches']):
        if item['repo_path']==rel:
            old=item['old'].replace('\r\n','\n'); new=item['new'].replace('\r\n','\n')
            assert text.count(new)==1,(rel,'declared WPS document delta changed')
            text=text.replace(new,old,1)
    return text

def normalize_manifest(payload):
    from visual_text_scope import normalize_manifest as normalize_visual
    m=normalize_visual(payload);d=data()
    assert m['revision_scope']==d['baseline_revision_scope']+d['added_revision_scope'],'undeclared or missing revision scope'
    m['revision_scope']=d['baseline_revision_scope']
    return m
