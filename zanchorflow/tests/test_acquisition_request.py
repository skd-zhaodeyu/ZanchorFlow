import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import canva_bridge as bridge
import runtime
from test_preflight_scope import _bridge_fixture, _accepted_attempt
SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'acquisition_request.py'

def setup(tmp_path):
    state=_bridge_fixture(tmp_path,n=1)
    identity=_accepted_attempt(state,'S001',tmp_path,design='fixture-design')
    lookup={'schema_version':1,'source':'canva_connector.get_design','identity':identity,
            'response':{'design':{'id':'fixture-design','page_count':1,'urls':{'edit_url':'https://www.canva.com/d/fixture-token'}}}}
    return state,identity,lookup

def run(state,lookup,tmp_path):
    p=tmp_path/'lookup.json';p.write_text(json.dumps(lookup),encoding='utf-8')
    return subprocess.run([sys.executable,str(SCRIPT),'--state',str(state),'--slide-id','S001',
        '--lookup',str(p),'--download-target-dir',str(tmp_path/'final')],capture_output=True,text=True)

def test_request_returns_current_alias_and_is_readonly(tmp_path):
    state,identity,lookup=setup(tmp_path)
    before=state.read_bytes()
    cp=run(state,lookup,tmp_path)
    assert cp.returncode==0,cp.stderr or cp.stdout
    result=json.loads(cp.stdout)
    assert result['status']=='WAIT_DOWNLOAD'
    assert result['identity']==identity
    assert result['edit_url']=='https://www.canva.com/d/fixture-token'
    assert result['download_target_dir']==str(tmp_path/'final')
    assert state.read_bytes()==before
    assert not (tmp_path/'final').exists()

@pytest.mark.parametrize('field',['attempt_id','source_fingerprint','text_clean_fingerprint','design_id'])
def test_request_rejects_lookup_identity_mismatch_without_writing(tmp_path,field):
    state,identity,lookup=setup(tmp_path)
    lookup['identity'][field]='wrong'
    before=state.read_bytes()
    cp=run(state,lookup,tmp_path)
    assert cp.returncode==1,cp.stderr or cp.stdout
    assert json.loads(cp.stdout)['status']=='BLOCKED'
    assert state.read_bytes()==before

@pytest.mark.parametrize('url',['http://www.canva.com/d/token','https://www.canva.com.evil.test/d/token',
                               'https://user@www.canva.com/d/token','https://www.canva.com/design/other/edit'])
def test_request_rejects_untrusted_design_url(tmp_path,url):
    state,identity,lookup=setup(tmp_path)
    lookup['response']['design']['urls']['edit_url']=url
    cp=run(state,lookup,tmp_path)
    assert cp.returncode==1,cp.stderr or cp.stdout
    assert json.loads(cp.stdout)['status']=='BLOCKED'

def test_request_rejects_multi_page_design(tmp_path):
    state,identity,lookup=setup(tmp_path)
    lookup['response']['design']['page_count']=2
    cp=run(state,lookup,tmp_path)
    assert cp.returncode==1,cp.stderr or cp.stdout

def test_request_rejects_not_wait_download(tmp_path):
    state,identity,lookup=setup(tmp_path)
    value=json.loads(state.read_text());value['canva_bridge']['active']['S001']['status']='PENDING'
    state.write_text(json.dumps(value))
    before=state.read_bytes()
    cp=run(state,lookup,tmp_path)
    assert cp.returncode==1,cp.stderr or cp.stdout
    assert state.read_bytes()==before
