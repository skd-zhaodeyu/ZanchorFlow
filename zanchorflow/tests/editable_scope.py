"""Reverse only the exact registered editable-path maintenance delta."""
import base64,copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def data():return json.loads((ROOT/'zanchorflow/tests/editable_scope.json').read_text(encoding='utf-8'))
def new_runtime():return data()['new_runtime']
def restore_bytes(rel,raw,text_mode=False):
 entry=data()['changed'].get(rel)
 if entry is None:return raw
 historical=json.loads((ROOT/'zanchorflow/tests/media_scope.json').read_text(encoding='utf-8')).get(rel,{})
 if historical:
  key='baseline_text_sha256' if text_mode else 'baseline_sha256'
  observed=raw.replace('\r\n','\n').encode() if text_mode else raw
  if hashlib.sha256(observed).hexdigest()==historical[key]:return raw
 original=base64.b64decode(entry['baseline_b64'])
 assert hashlib.sha256(original).hexdigest()==entry['baseline_sha256'],(rel,'corrupt editable baseline')
 if text_mode:
  observed=raw.replace('\r\n','\n');digest=hashlib.sha256(observed.encode()).hexdigest()
  assert digest in (entry['baseline_text_sha256'],entry['approved_text_sha256']),(rel,'unapproved editable text')
  return original.decode('utf-8').replace('\r\n','\n')
 digest=hashlib.sha256(raw).hexdigest()
 assert digest in (entry['baseline_sha256'],entry['approved_sha256']),(rel,'unapproved editable change')
 return original

def normalize_manifest(payload):
 import yaml
 entry=data()['changed']['zanchorflow/manifest.yaml'];old=yaml.safe_load(base64.b64decode(entry['baseline_b64']));approved=data()['manifest_approved'];result=copy.deepcopy(payload)
 changed=[key for key in set(old)|set(approved) if old.get(key)!=approved.get(key)]
 baseline_mode=all(result.get(key)==old.get(key) for key in changed)
 for key in changed:
  assert result.get(key)==(old.get(key) if baseline_mode else approved.get(key)),(key,'undeclared or missing editable manifest change')
  if key in old:result[key]=copy.deepcopy(old[key])
  else:result.pop(key,None)
 return result
