"""Revert only approved light-maintenance changes before inherited checks."""
import json,hashlib,base64
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def data():return json.loads((ROOT/'tests/light_scope.json').read_text(encoding='utf-8'))
def restore_bytes(rel,raw):
    entry=data().get(rel)
    if not entry:return raw
    digest=hashlib.sha256(raw).hexdigest()
    if digest==entry['baseline_sha256']:return raw
    assert digest==entry['approved_sha256'],(rel,'unapproved light change')
    return base64.b64decode(entry['baseline_b64'])
def restore_text(rel,text):
    entry=data().get(rel)
    if not entry:return text
    digest=hashlib.sha256(text.replace('\r\n','\n').encode()).hexdigest()
    if digest==entry['baseline_text_sha256']:return text
    assert digest==entry['approved_text_sha256'],(rel,'unapproved light text')
    return base64.b64decode(entry['baseline_b64']).decode().replace('\r\n','\n')
