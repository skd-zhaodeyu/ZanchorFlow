"""Outer slim packaging checks. No production host override or live installation."""
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys
import zipfile
import pytest

REPO=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('pack_builder',REPO/'tools/build.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

@pytest.fixture
def archive(tmp_path):
    output=tmp_path/'out/zanchorflow.zip'
    result=b.build_slim(tmp_path/'staging',output)
    assert result['status']=='PASS' and result['file_count']==6
    return output

def test_exact_six_files_and_required_installer_bytes(archive):
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())=={'ZanchorFlow/'+p for p in b.SLIM_MAP}
        assert len(z.namelist())==6 and z.testzip() is None
        assert z.read('ZanchorFlow/tools/install.py')==(REPO/'tools/install.py').read_bytes()
        assert z.read('ZanchorFlow/docs/unified-install.md')==(REPO/'docs/unified-install.md').read_bytes()
        assert b.digest(z.read('ZanchorFlow/dist/zanchorflow.zip'))=='0de267f9c2953c22e0dbbf45ce0e4c5de7bc549176cd876e2ccb1108d25147f1'
        assert 'tests/' not in '\n'.join(z.namelist()) and 'examples/' not in '\n'.join(z.namelist())

@pytest.mark.parametrize('mutation',('extra','missing','duplicate','unsafe','installer_changed','baseline_changed','symlink','checksum'))
def test_archive_tampering_rejected(archive,mutation):
    if mutation=='checksum':archive.with_suffix('.zip.sha256').write_text('wrong')
    else:
        with zipfile.ZipFile(archive) as z:members={n:z.read(n) for n in z.namelist()}
        if mutation=='extra':members['ZanchorFlow/tests/test.py']=b'extra'
        elif mutation=='missing':del members['ZanchorFlow/LICENSE']
        elif mutation=='unsafe':members['ZanchorFlow/../outside.txt']=b'bad'
        elif mutation=='installer_changed':members['ZanchorFlow/tools/install.py']+=b'\n# changed'
        elif mutation=='baseline_changed':members['ZanchorFlow/dist/zanchorflow.zip']+=b'changed'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in members.items():
                info=zipfile.ZipInfo(name)
                if mutation=='symlink' and name=='ZanchorFlow/LICENSE':info.external_attr=(stat.S_IFLNK|0o777)<<16
                z.writestr(info,data)
            if mutation=='duplicate':z.writestr('ZanchorFlow/LICENSE',members['ZanchorFlow/LICENSE'])
        archive.with_suffix('.zip.sha256').write_text(b.digest(archive.read_bytes())+'  '+archive.name+'\n',encoding='ascii')
    with pytest.raises((ValueError,AssertionError)):b.check_slim(archive)

@pytest.mark.parametrize('mode',('output','staging'))
def test_cannot_overwrite_repository_or_inner_baseline(tmp_path,mode):
    inner=REPO/'dist/zanchorflow.zip';before=inner.read_bytes()
    with pytest.raises(ValueError):
        b.build_slim(REPO/'dist' if mode=='staging' else tmp_path/'stage',inner if mode=='output' else tmp_path/'out.zip')
    assert inner.read_bytes()==before

def test_modes_mutually_exclusive(tmp_path):
    result=subprocess.run([sys.executable,'-B',str(REPO/'tools/build.py'),'--slim','--source','--work',str(tmp_path/'stage'),'--output',str(tmp_path/'out.zip')],capture_output=True,text=True)
    assert result.returncode==2 and not (tmp_path/'out.zip').exists()

def test_repeat_build_is_identical(archive,tmp_path):
    second=tmp_path/'second/zanchorflow.zip';b.build_slim(tmp_path/'second-stage',second)
    assert archive.read_bytes()==second.read_bytes()

def test_all_generated_views_identical_in_slim_and_source(archive,tmp_path):
    extracted=tmp_path/'slim';extracted.mkdir()
    with zipfile.ZipFile(archive) as z:z.extractall(extracted)
    modules=[]
    for n,root in enumerate((REPO,extracted/'ZanchorFlow')):
        spec=importlib.util.spec_from_file_location('installer_'+str(n),root/'tools/install.py')
        i=importlib.util.module_from_spec(spec);spec.loader.exec_module(i);modules.append(i)
    for profile in ('full','qwen','workbuddy'):
        assert modules[0].make_view(profile)==modules[1].make_view(profile)
    for host in ('codex','other','unknown'):
        env={'CODEX_THREAD_ID':'synthetic'} if host=='codex' else {}
        ancestors=[{'pid':15,'executable':'C:/Apps/claude.exe'}] if host=='other' else []
        for i in modules:
            d=i.detect(env,ancestors);assert d['host']==host and d['profile']=='full'
            assert i.make_view(d['profile'])==i.load_baseline()

def test_installer_and_skill_runtime_match_verified_candidate():
    assert b.digest((REPO/'tools/install.py').read_bytes())=='ed524c6c6ef43cf3c91fb9026d7bbb95f68e0ac5b508984ba3d05b57a901eda1'
    with zipfile.ZipFile(REPO/'dist/zanchorflow.zip') as z:
        for name in z.namelist():
            assert z.read(name)==(REPO/name).read_bytes(),name
