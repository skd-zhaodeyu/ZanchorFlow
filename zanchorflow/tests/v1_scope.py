"""Rollback only the approved V1 delta before inherited immutable-scope checks."""
import base64,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def data():return json.loads((ROOT/'tests/v1_scope.json').read_text(encoding='utf-8'))
def _publication_readme(rel,raw):
    if rel!='README.md':return raw
    path=ROOT.parent/'tools/publication_scope.json'
    if not path.is_file():return raw
    patch=json.loads(path.read_text(encoding='utf-8'))
    if hashlib.sha256(raw).hexdigest()!=patch['published_sha256']:return raw
    original=base64.b64decode(patch['incoming_b64'])
    assert hashlib.sha256(original).hexdigest()==patch['incoming_sha256']
    return original

def restore_bytes(rel,raw):
    raw=_publication_readme(rel,raw)
    entry=data().get(rel)
    if not entry:return raw
    digest=hashlib.sha256(raw).hexdigest()
    if digest==entry['baseline_sha256']:return raw
    assert digest==entry['approved_sha256'],(rel,'unapproved V1 change')
    return base64.b64decode(entry['baseline_b64'])
def restore_text(rel,text):
    text=_publication_readme(rel,text.replace('\r\n','\n').encode()).decode().replace('\r\n','\n')
    entry=data().get(rel)
    if not entry:return text
    digest=hashlib.sha256(text.replace('\r\n','\n').encode()).hexdigest()
    if digest==entry['baseline_text_sha256']:return text
    assert digest==entry['approved_text_sha256'],(rel,'unapproved V1 text')
    return base64.b64decode(entry['baseline_b64']).decode().replace('\r\n','\n')
def new_runtime():return json.loads((ROOT/'tests/v1_new_files.json').read_text(encoding='utf-8'))
