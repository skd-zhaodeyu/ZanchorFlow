"""Reverse only this pinned download maintenance delta before inherited scope guards."""
import base64,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def data():return json.loads((ROOT/'tests/download_scope.json').read_text(encoding='utf-8'))
def restore_repo_bytes(rel,raw):
    from light_scope import restore_bytes as restore_light
    raw=restore_light(rel,raw)
    from v1_scope import restore_bytes
    raw=restore_bytes(rel,raw)
    entry=data().get(rel)
    if entry is None:return raw
    digest=hashlib.sha256(raw).hexdigest()
    if digest==entry['baseline_sha256']:return raw
    assert digest==entry['approved_sha256'],(rel,'unapproved download maintenance change')
    baseline=base64.b64decode(entry['baseline_b64'])
    assert hashlib.sha256(baseline).hexdigest()==entry['baseline_sha256']
    return baseline
def restore_repo_text(rel,text):
    from light_scope import restore_text as restore_light
    text=restore_light(rel,text)
    from v1_scope import restore_text
    text=restore_text(rel,text)
    entry=data().get(rel)
    if entry is None:return text
    text=text.replace('\r\n','\n');digest=hashlib.sha256(text.encode()).hexdigest()
    if digest==entry['baseline_text_sha256']:return text
    assert digest==entry['approved_text_sha256'],(rel,'unapproved download maintenance document change')
    return base64.b64decode(entry['baseline_b64']).decode().replace('\r\n','\n')


def new_runtime():
    from v1_scope import new_runtime as v1_new
    return {**json.loads((ROOT/'tests/download_new_files.json').read_text(encoding='utf-8')),**v1_new()}
def verify_new_runtime(rel,raw):
    from light_scope import restore_bytes as restore_light
    raw=restore_light('zanchorflow/'+rel,raw)
    expected=new_runtime()[rel]
    assert hashlib.sha256(raw).hexdigest()==expected,(rel,'new download module changed')
