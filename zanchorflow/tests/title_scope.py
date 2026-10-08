"""Invert only declared title edits; keep all inherited expectations and pins intact."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def data(): return json.loads((ROOT/'tests/title_scope.json').read_text(encoding='utf-8'))

def normalize_runtime_bytes(rel,raw):
    from heading_refine_scope import restore_bytes
    text=restore_bytes(rel,raw).decode('utf-8')
    for item in reversed(data()['patches']):
        if item['path']==rel:
            assert text.count(item['new'])==1,(rel,'declared title delta missing/changed')
            text=text.replace(item['new'],item['old'],1)
    result=text.encode('utf-8')
    expected=data()['baseline'].get('zanchorflow/'+rel)
    if expected:assert hashlib.sha256(result).hexdigest()==expected,(rel,'undeclared source change')
    return result

def normalize_doc(rel,text):
    from heading_refine_scope import restore_text
    text=restore_text(rel,text)
    for item in reversed(data()['patches']):
        if item['path']==rel:
            before=item['old'].replace('\r\n','\n');after=item['new'].replace('\r\n','\n')
            assert text.count(after)==1,(rel,'declared document addition missing/changed')
            text=text.replace(after,before,1)
    return text

def check_new_runtime():
    for rel,digest in data()['new_runtime_files'].items():
        from heading_refine_scope import restore_bytes
        assert hashlib.sha256(restore_bytes(rel,(ROOT/rel).read_bytes())).hexdigest()==digest,(rel,'declared new module changed')
