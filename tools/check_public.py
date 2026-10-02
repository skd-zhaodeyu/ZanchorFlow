"""Check public material without printing credential values."""
from pathlib import Path
import re,zipfile
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]
OMIT={'.git','__pycache__','.pytest_cache'}
KEY=re.compile(rb'(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|session[_-]?secret|canva[_-]?cookie)\s*[:=]\s*["\x27]?([A-Za-z0-9._-]{16,})')
SIGNED=re.compile(rb'https?://[^\s"\x27<>]+[?&](?:sig|signature|access_token|token)=[^\s"\x27<>]+',re.I)
LOCAL=re.compile(rb'(?i)(?:[A-Z]:\\(?:Users\\|Codex-Projects\\|projectv2\\)|codex://threads/)')
DESIGN=re.compile(rb'https?://(?:www\.)?canva\.com/design/[A-Za-z0-9_-]{10,}',re.I)
def scan(data,label,fixture=False):
    errors=[]
    for match in KEY.finditer(data):
        value=match.group(1).lower()
        if not value.startswith((b'synthetic',b'example',b'placeholder',b'dummy',b'fake')):
            errors.append(label+': credential-like literal')
    if SIGNED.search(data):errors.append(label+': signed URL')
    if not fixture and LOCAL.search(data):errors.append(label+': private local/thread path')
    if not fixture and DESIGN.search(data):errors.append(label+': private design URL')
    return errors
def main():
    errors=[];count=0
    for p in ROOT.rglob('*'):
        if not p.is_file() or any(part in OMIT for part in p.relative_to(ROOT).parts):continue
        rel=p.relative_to(ROOT).as_posix();count+=1
        if p.suffix.lower() in {'.md','.py','.json','.yaml','.yml','.txt','.ps1','.xml'}:
            errors+=scan(p.read_bytes(),rel,'/tests/' in rel or rel=='tools/check_public.py')
        if p.suffix.lower() in {'.pptx','.zip'}:
            with zipfile.ZipFile(p) as z:
                for name in z.namelist():
                    if name.endswith(('.xml','.rels','.md','.json','.yaml','.py','.txt','.ps1')):
                        data=z.read(name);errors+=scan(data,rel+':'+name)
                        if name.endswith('.rels') and p.suffix=='.pptx':
                            if any(x.get('TargetMode')=='External' for x in etree.fromstring(data)):
                                errors.append(rel+': external relationship')
        if p.suffix=='.pptx':
            with zipfile.ZipFile(p) as z:
                if any(n.startswith('ppt/fonts/') for n in z.namelist()):errors.append(rel+': embedded fonts')
                core=etree.fromstring(z.read('docProps/core.xml'))
                if len(core):errors.append(rel+': core metadata not scrubbed')
        if p.suffix=='.png':
            from PIL import Image
            with Image.open(p) as im:
                if any(k in im.info for k in ('Comment','Description','Author')):errors.append(rel+': PNG text metadata')
        if p.suffix=='.pdf':
            # PyMuPDF is optional locally; the mandatory checks also cover PDF bytes.
            errors+=scan(p.read_bytes(),rel)
    if errors:
        print('\n'.join(sorted(set(errors))));raise SystemExit(1)
    print('PUBLIC_TREE_PASS files='+str(count))
if __name__=='__main__':main()
