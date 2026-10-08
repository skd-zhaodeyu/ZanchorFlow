"""Build and verify the fixed-name installation archive from a runtime whitelist."""
import argparse,hashlib,json,shutil,stat,sys,tempfile,zipfile
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
FULL_ROOT={'.gitattributes','.gitignore','LICENSE','README.md','requirements-dev.txt'}
OMIT={'.git','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','work','outputs'}

def full_source_files():
    paths=set(source_files())
    for name in FULL_ROOT:
        p=REPO/name
        if not p.is_file():raise ValueError('required repository file missing: '+name)
        paths.add(p)
    groups=[(SKILL/'tests',{'.py','.json','.md','.txt'}),(SKILL/'docs',{'.md'}),(REPO/'docs',{'.md'}),
            (REPO/'tools',{'.py'}),(REPO/'.github'/'workflows',{'.yml','.yaml'}),
            (REPO/'examples',{'.md','.txt','.png','.pptx','.pdf','.sha256'}),
            (REPO/'docs'/'assets',{'.png'})]
    for folder,suffixes in groups:
        for p in folder.rglob('*'):
            if p.is_file() and p.suffix.lower() in suffixes and not any(x in OMIT for x in p.relative_to(REPO).parts):paths.add(p)
    publication=REPO/'tools'/'publication_scope.json'
    if publication.is_file():paths.add(publication)
    for name in ('pytest.ini',):
        p=SKILL/name
        if p.is_file():paths.add(p)
    for name in ('zanchorflow.zip','zanchorflow.zip.sha256'):
        p=REPO/'dist'/name
        if not p.is_file():raise ValueError('current dist package required: '+name)
        paths.add(p)
    if any(p.is_symlink() for p in paths):raise ValueError('source package cannot follow symlinks')
    return sorted(paths)

def check_source(archive):
    check(REPO/'dist'/'zanchorflow.zip')
    expected={'ZanchorFlow/'+p.relative_to(REPO).as_posix():p for p in full_source_files()}
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None,'source archive CRC failure'
        assert len(z.namelist())==len(set(z.namelist())),'duplicate source member'
        assert set(z.namelist())==set(expected),'source whitelist differs'
        for name,p in expected.items():assert z.read(name)==p.read_bytes(),name
        assert z.read('ZanchorFlow/dist/zanchorflow.zip')==(REPO/'dist/zanchorflow.zip').read_bytes(),'embedded ZIP differs'
    sha=digest(Path(archive).read_bytes());sidecar=Path(archive).with_suffix('.zip.sha256')
    assert sidecar.read_text(encoding='ascii')==sha+'  '+Path(archive).name+'\n','source checksum differs'
    return {'status':'PASS','file_count':len(expected),'sha256':sha,'embedded_installation_sha256':digest((REPO/'dist/zanchorflow.zip').read_bytes())}

def build_source(work,output):
    work=Path(work).resolve();output=Path(output).resolve()
    if output==REPO or REPO in output.parents:raise ValueError('source archive output must be outside repository')
    if work==REPO or REPO in work.parents:raise ValueError('source staging must be outside repository')
    check(REPO/'dist'/'zanchorflow.zip')
    work.mkdir(parents=True,exist_ok=True);output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='source-',dir=work) as tmp:
        staging=Path(tmp)/'ZanchorFlow'
        for p in full_source_files():
            dest=staging/p.relative_to(REPO);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(staging.rglob('*')):
                if p.is_file():z.write(p,'ZanchorFlow/'+p.relative_to(staging).as_posix())
    sha=digest(output.read_bytes());output.with_suffix('.zip.sha256').write_text(sha+'  '+output.name+'\n',encoding='ascii')
    return check_source(output)

SLIM_MAP={
    'README.md':'docs/slim-readme.md',
    'LICENSE':'LICENSE',
    'docs/unified-install.md':'docs/unified-install.md',
    'tools/install.py':'tools/install.py',
    'dist/zanchorflow.zip':'dist/zanchorflow.zip',
    'dist/zanchorflow.zip.sha256':'dist/zanchorflow.zip.sha256',
}

def slim_files():
    check(REPO/'dist/zanchorflow.zip')
    import importlib.util
    spec=importlib.util.spec_from_file_location("installer_baseline",REPO/"tools/install.py")
    installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
    BASE_SHA=installer.BASE_SHA
    if digest((REPO/'dist/zanchorflow.zip').read_bytes())!=BASE_SHA:
        raise ValueError('immutable baseline hash differs')
    files={}
    for target,source in SLIM_MAP.items():
        p=REPO/source
        if not p.is_file() or p.is_symlink() or p.resolve()!=p:
            raise ValueError('slim source missing or redirected: '+source)
        files['ZanchorFlow/'+target]=p.read_bytes()
    return files

def check_slim(archive):
    archive=Path(archive).resolve();expected=slim_files()
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('slim archive CRC failure')
        if len(z.namelist())!=len(set(z.namelist())):raise ValueError('duplicate slim member')
        if set(z.namelist())!=set(expected):raise ValueError('slim six-file whitelist differs')
        if any(stat.S_ISLNK(info.external_attr>>16) for info in z.infolist()):raise ValueError('slim symlink member forbidden')
        for name,data in expected.items():
            if z.read(name)!=data:raise ValueError('slim source bytes differ: '+name)
    sha=digest(archive.read_bytes())
    if archive.with_suffix('.zip.sha256').read_text(encoding='ascii')!=sha+'  '+archive.name+'\n':
        raise ValueError('slim checksum differs')
    return {'status':'PASS','file_count':6,'sha256':sha,
            'embedded_installation_sha256':digest(expected['ZanchorFlow/dist/zanchorflow.zip'])}

def build_slim(work,output):
    work=Path(work).resolve();output=Path(output).resolve()
    if output==REPO or REPO in output.parents:raise ValueError('slim output must be outside repository')
    if work==REPO or REPO in work.parents:raise ValueError('slim staging must be outside repository')
    expected=slim_files()
    work.mkdir(parents=True,exist_ok=True);output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='slim-',dir=work) as td:
        temporary=Path(td)/'zanchorflow.zip'
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in sorted(expected.items()):
                info=zipfile.ZipInfo(name);info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=0o100644<<16;z.writestr(info,data)
        shutil.copyfile(temporary,output)
    sha=digest(output.read_bytes());output.with_suffix('.zip.sha256').write_text(sha+'  '+output.name+'\n',encoding='ascii')
    return check_slim(output)

def main():
    p=argparse.ArgumentParser();p.add_argument('--work');p.add_argument('--output');p.add_argument('--check');mode=p.add_mutually_exclusive_group();mode.add_argument('--source',action='store_true',help='build/check the complete public source archive');mode.add_argument('--slim',action='store_true',help='build/check the six-file automatic installation wrapper')
    a=p.parse_args()
    if a.check:result=check_slim(a.check) if a.slim else check_source(a.check) if a.source else check(a.check)
    elif a.work and a.output:result=build_slim(a.work,a.output) if a.slim else build_source(a.work,a.output) if a.source else build(a.work,a.output)
    else:p.error('use --check or both --work and --output')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
