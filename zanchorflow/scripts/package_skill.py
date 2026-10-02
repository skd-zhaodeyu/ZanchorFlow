"""Build a clean installable Skill ZIP after hash and privacy checks."""
import argparse
import re
import zipfile
from pathlib import Path
from runtime import validate_manifest_hashes

OMIT = {'__pycache__','.pytest_cache','.git'}
SECRET_PATTERNS = [
    re.compile(rb'(?i)(access[_-]?token|refresh[_-]?token|session[_-]?secret|canva[_-]?cookie)\s*[:=]\s*["\x27]?[A-Za-z0-9._-]{12,}'),
    re.compile(rb'(?i)https?://[^\s"\x27]+(?:signature|sig|token)=[^\s"\x27]+'),
    re.compile(rb'(?i)C:\\Users\\[^\\\s]+\\'),
]

def build(root, output):
    root, output = Path(root), Path(output)
    if validate_manifest_hashes(root):
        raise RuntimeError('CANONICAL_HASH_MISMATCH')
    files = [p for p in root.rglob('*') if p.is_file() and not any(x in OMIT for x in p.parts) and p.suffix not in {'.pyc','.pyo'}]
    for path in files:
        data = path.read_bytes()
        if path.suffix.lower() in {'.md','.yaml','.py','.txt','.json'}:
            for pat in SECRET_PATTERNS:
                if pat.search(data):
                    raise RuntimeError(f'PUBLISH_PRIVACY_BLOCKER: {path.relative_to(root)}')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(files):
            z.write(path, f'{root.name}/{path.relative_to(root).as_posix()}')
    return len(files)

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('skill_dir')
    p.add_argument('output_zip')
    a=p.parse_args()
    count=build(a.skill_dir,a.output_zip)
    print(f'PACKAGE_PASS files={count} zip={a.output_zip}')
