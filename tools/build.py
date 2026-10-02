"""Build and verify the fixed-name installation archive from a runtime whitelist."""
import argparse,hashlib,json,shutil,sys,tempfile,zipfile
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
SKILL=REPO/'zanchorflow'
ROOT_FILES={'SKILL.md','manifest.yaml','LICENSE','requirements-base.txt','requirements-image.txt','requirements-office.txt'}
DOC_FILES={'installation.md','codex-canva-bridge.md','image-layer-backend.md','image-layer-box-selection.md'}
def digest(data):return hashlib.sha256(data).hexdigest()
def source_files():
    paths=[p for p in SKILL.rglob('*') if p.is_file() and (
        (p.parent==SKILL and p.name in ROOT_FILES) or
        (p.parent==SKILL/'references' and p.suffix=='.md') or
        (p.parent==SKILL/'scripts' and p.suffix in {'.py','.ps1'}) or
        (p.parent==SKILL/'docs' and p.name in DOC_FILES))]
    assert {p.name for p in paths if p.parent==SKILL}==ROOT_FILES,'required root file missing'
    assert len([p for p in paths if p.parent==SKILL/'references'])==8,'eight protocols required'
    return sorted(paths)
def build(work,output):
    work=Path(work).resolve();output=Path(output).resolve();work.mkdir(parents=True,exist_ok=True)
    if output==SKILL or SKILL in output.parents:raise ValueError('archive output must be outside skill')
    with tempfile.TemporaryDirectory(prefix='package-',dir=work) as tmp:
        staging=Path(tmp)/'zanchorflow'
        assert work in staging.resolve().parents
        for path in source_files():
            dest=staging/path.relative_to(SKILL);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
        sys.path.insert(0,str(SKILL/'scripts'))
        from package_skill import build as original_build
        original_build(staging,output)
    sha=digest(output.read_bytes());output.with_suffix('.zip.sha256').write_text(sha+'  '+output.name+'\n',encoding='ascii')
    return check(output)
def check(archive):
    archive=Path(archive).resolve();expected={'zanchorflow/'+p.relative_to(SKILL).as_posix():p for p in source_files()}
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist())==len(set(z.namelist())),'duplicate archive member'
        assert set(z.namelist())==set(expected),'archive whitelist differs'
        for name,path in expected.items():assert z.read(name)==path.read_bytes(),name
        import yaml
        manifest=yaml.safe_load(z.read('zanchorflow/manifest.yaml'))
        for item in manifest['canonical_protocols']:assert digest(z.read('zanchorflow/'+item['path']))==item['sha256'],item['path']
        assert manifest['updated_at_utc'].endswith('Z'),'UTC timestamp required'
    sha=digest(archive.read_bytes());sidecar=archive.with_suffix('.zip.sha256')
    assert sidecar.read_text(encoding='ascii')==sha+'  '+archive.name+'\n','ZIP checksum differs'
    return {'status':'PASS','file_count':len(expected),'sha256':sha,'updated_at_utc':manifest['updated_at_utc']}
def main():
    p=argparse.ArgumentParser();p.add_argument('--work');p.add_argument('--output');p.add_argument('--check')
    a=p.parse_args()
    if a.check:result=check(a.check)
    elif a.work and a.output:result=build(a.work,a.output)
    else:p.error('use --check or both --work and --output')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
