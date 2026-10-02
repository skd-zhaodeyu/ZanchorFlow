import json, sys, sqlite3, shutil
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import host_acquisition as host
import canva_bridge as bridge
import runtime
from test_acquisition_request import setup
from test_host_acquisition import fixture

def prepare_fixture(tmp_path):
    state,identity,lookup=setup(tmp_path)
    lookup['observation']='fixture readonly connector response'
    lp=tmp_path/'lookup.json';lp.write_text(json.dumps(lookup))
    rec=tmp_path/'record.json'
    return state,rec,lp

def test_prepare_is_readonly_and_reuses_record(tmp_path):
    state,rec,lp=prepare_fixture(tmp_path);before=state.read_bytes()
    assert hasattr(host,'prepare'), 'prepare entry missing'
    first=host.prepare(rec,state,'S001',lp,tmp_path/'out','S001.pptx')
    second=host.prepare(rec,state,'S001',lp,tmp_path/'out','S001.pptx')
    assert first['acquisition_id']==second['acquisition_id']
    assert state.read_bytes()==before
    host.lock(rec)
    assert host.prepare(rec,state,'S001',lp,tmp_path/'out','S001.pptx')['status']=='INTENT_LOCKED'
    with pytest.raises(ValueError):host.lock(rec)

@pytest.mark.parametrize('kind,waits',[('query',[2,5,10,15,20]),('ui',[2,5,10,15,20])])
def test_retry_budget_survives_reentry_and_stops_seventh_attempt(tmp_path,kind,waits):
    state,rec,lp=prepare_fixture(tmp_path)
    assert hasattr(host,'reserve_retry'), 'durable retry budget missing'
    for n,delay in enumerate(waits,1):
        result=host.reserve_retry(rec,state,'S001',kind)
        assert result['retry_number']==n and result['wait_seconds']==delay
    with pytest.raises(ValueError,match='exhausted'):host.reserve_retry(rec,state,'S001',kind)
    host.prepare(rec,state,'S001',lp,tmp_path/'out','S001.pptx')
    with pytest.raises(ValueError,match='exhausted'):host.reserve_retry(rec,state,'S001',kind)

def test_no_ui_retry_after_intent_but_observe_is_allowed(tmp_path):
    state,rec,lp=prepare_fixture(tmp_path)
    host.prepare(rec,state,'S001',lp,tmp_path/'out','S001.pptx');host.lock(rec)
    with pytest.raises(ValueError):host.reserve_retry(rec,state,'S001','ui')
    waits=[]
    for n,delay in enumerate([10,20,30,45,60],1):
        result=host.reserve_retry(rec,state,'S001','observe')
        waits.append(result['wait_seconds']);assert result['retry_number']==n
        assert host._read(rec)['status']=='INTENT_LOCKED' and Path(str(rec)+'.intent').exists()
    assert waits==[10,20,30,45,60]
    with pytest.raises(ValueError,match='exhausted'):host.reserve_retry(rec,state,'S001','observe')

def test_new_numbered_export_gets_fresh_local_retry_budget(tmp_path):
    state,first,lp=prepare_fixture(tmp_path)
    for _ in range(5):
        host.reserve_retry(first,state,'S001','query');host.reserve_retry(first,state,'S001','ui')
    host.prepare(first,state,'S001',lp,tmp_path/'out','S001.pptx');host.lock(first);host.fail(first,'EXPORT_FAILED')
    second=tmp_path/'record-download-02.json'
    assert host.reserve_retry(second,state,'S001','query')['retry_number']==1
    assert host.reserve_retry(second,state,'S001','ui')['retry_number']==1


@pytest.mark.parametrize('event',[True,False])
def test_finish_real_finalizer_bind_and_reuse(tmp_path,event):
    if event and not (shutil.which('pwsh') or shutil.which('powershell')): pytest.skip('PowerShell integration unavailable')
    state,rec,profile,file,url=fixture(tmp_path)
    identity=host._read(rec)['identity']
    lookup={'schema_version':1,'source':'canva_connector.get_design','identity':identity,
            'observation':'fixture connector response', 'response':{'design':{'id':identity['design_id'],'page_count':1,'urls':{'edit_url':'https://www.canva.com/d/fixture-token'}}}}
    lp=tmp_path/'lookup.json';lp.write_text(json.dumps(lookup))
    assert hasattr(host,'prepare'), 'prepare entry missing'
    host.prepare(rec,state,'S001',lp,tmp_path/'a different user output','S001.pptx')
    before=state.read_bytes()
    if not event:
        with pytest.raises(ValueError):host.finish(rec,state,profile,url,False,wait_seconds=0)
        assert state.read_bytes()==before and file.exists()
        return
    result=host.finish(rec,state,profile,url,True,python_executable=sys.executable)
    assert result['status']=='DOWNLOAD_BOUND'
    dest=Path(result['path']);assert dest.is_file() and not file.exists()
    assert bridge.sha(dest)==result['sha256']
    again=host.finish(rec,state,profile,url,True)
    assert again['reused'] and again['path']==str(dest)
    assert bridge.download_current(runtime.load_runtime_state(state),'S001')['sha256']==result['sha256']
    with pytest.raises(ValueError):host.lock(rec)

def test_poll_delayed_completion_and_timeout(tmp_path,monkeypatch):
    state,rec,profile,file,url=fixture(tmp_path)
    assert hasattr(host,'acquire_wait'), 'same-download bounded wait missing'
    db=sqlite3.connect(profile/'History');db.execute('update downloads set state=0');db.commit();db.close()
    sleeps=[]
    def complete(seconds):
        sleeps.append(seconds)
        db=sqlite3.connect(profile/'History');db.execute('update downloads set state=1');db.commit();db.close()
    monkeypatch.setattr(host.time,'sleep',complete)
    assert host.acquire_wait(rec,state,profile,url,True,4)['status']=='ACQUIRED'
    assert sleeps==[2]

def test_ambiguity_never_polls(tmp_path,monkeypatch):
    state,rec,profile,file,url=fixture(tmp_path)
    assert hasattr(host,'acquire_wait'), 'same-download bounded wait missing'
    db=sqlite3.connect(profile/'History');db.execute('insert into downloads select 2,guid,target_path,state,received_bytes,total_bytes,tab_url,start_time from downloads');db.commit();db.close()
    monkeypatch.setattr(host.time,'sleep',lambda _:pytest.fail('ambiguity retried'))
    with pytest.raises(ValueError):host.acquire_wait(rec,state,profile,url,True,4)

def test_poll_timeout_retains_accept_and_lock(tmp_path,monkeypatch):
    state,rec,profile,file,url=fixture(tmp_path);before=state.read_bytes()
    assert hasattr(host,'acquire_wait'), 'same-download bounded wait missing'
    db=sqlite3.connect(profile/'History');db.execute('update downloads set state=0');db.commit();db.close()
    monkeypatch.setattr(host.time,'sleep',lambda _:None)
    with pytest.raises(ValueError,match='timeout'):host.acquire_wait(rec,state,profile,url,True,0)
    assert state.read_bytes()==before and Path(str(rec)+'.intent').exists()


def finish_fixture(tmp_path):
    state,rec,profile,file,url=fixture(tmp_path)
    identity=host._read(rec)['identity']
    lookup={'schema_version':1,'source':'canva_connector.get_design','identity':identity,'observation':'fixture actual lookup',
        'response':{'design':{'id':identity['design_id'],'page_count':1,'urls':{'edit_url':'https://www.canva.com/d/fixture-token'}}}}
    lp=tmp_path/'lookup.json';lp.write_text(json.dumps(lookup))
    host.prepare(rec,state,'S001',lp,tmp_path/'final','S001.pptx')
    return state,rec,profile,file,url

@pytest.mark.parametrize('checkpoint',['finalizer','bind','after_move'])
def test_failure_resume_does_not_redownload_or_repeat_move(tmp_path,monkeypatch,checkpoint):
    if not (shutil.which('pwsh') or shutil.which('powershell')): pytest.skip('PowerShell integration unavailable')
    state,rec,profile,file,url=finish_fixture(tmp_path)
    original=host._finalize
    calls=[]
    def finalize(*args):
        calls.append(str(args[0]))
        if checkpoint=='finalizer' and len(calls)==1:raise ValueError('injected finalizer failure')
        value=original(*args)
        if checkpoint=='after_move' and len(calls)==1:raise ValueError('injected interruption after move')
        return value
    monkeypatch.setattr(host,'_finalize',finalize)
    original_bind=bridge.bind_download
    def denied(*args):raise ValueError('injected bind failure')
    if checkpoint=='bind':monkeypatch.setattr(bridge,'bind_download',denied)
    with pytest.raises(ValueError):host.finish(rec,state,profile,url,True)
    assert bridge.status(state)['status']=='WAIT_DOWNLOAD'
    assert host._read(rec)['status']=='FAILED'
    with pytest.raises(ValueError):host.lock(rec)
    monkeypatch.setattr(bridge,'bind_download',original_bind)
    result=host.finish(rec,state,profile,url,True)
    assert result['status']=='DOWNLOAD_BOUND'
    assert len(calls)==(2 if checkpoint=='finalizer' else 1)
    assert bridge.sha(result['path'])==host._read(rec)['sha256']

def test_cli_concise_and_full_evidence(tmp_path):
    import subprocess
    state,rec,lp=prepare_fixture(tmp_path)
    cmd=[sys.executable,str(Path(host.__file__)),'prepare','--record',str(rec),'--state',str(state),
        '--slide-id','S001','--lookup',str(lp),'--download-target-dir',str(tmp_path/'out'),'--target-filename','S001.pptx']
    cp=subprocess.run(cmd,capture_output=True,text=True)
    assert cp.returncode==0,cp.stderr
    summary=json.loads(cp.stdout);full=host._read(str(rec)+'.prepare.result.json')
    assert 'identity' not in summary and full['identity']['slide_id']=='S001'
    verbose=subprocess.run(cmd+['--verbose'],capture_output=True,text=True)
    assert json.loads(verbose.stdout)['identity']==full['identity']

def test_prepare_rejects_changed_identity_or_target(tmp_path):
    state,rec,lp=prepare_fixture(tmp_path)
    host.prepare(rec,state,'S001',lp,tmp_path/'out','S001.pptx')
    before=rec.read_bytes()
    with pytest.raises(ValueError):host.prepare(rec,state,'S001',lp,tmp_path/'elsewhere','S001.pptx')
    assert rec.read_bytes()==before
    lookup=json.loads(lp.read_text());lookup['identity']['design_id']='other';lp.write_text(json.dumps(lookup))
    with pytest.raises(ValueError):host.prepare(rec,state,'S001',lp,tmp_path/'out','S001.pptx')


def test_cancelled_record_stops_without_poll(tmp_path,monkeypatch):
    state,rec,profile,file,url=fixture(tmp_path)
    db=sqlite3.connect(profile/'History');db.execute('update downloads set state=2');db.commit();db.close()
    monkeypatch.setattr(host.time,'sleep',lambda _:pytest.fail('cancelled download polled'))
    with pytest.raises(ValueError,match='cancelled'):host.acquire_wait(rec,state,profile,url,True,4)

def test_acquired_resume_rejects_changed_observed_url(tmp_path,monkeypatch):
    state,rec,profile,file,url=finish_fixture(tmp_path)
    host.acquire(rec,state,profile,url,True)
    monkeypatch.setattr(host,'_finalize',lambda *a:pytest.fail('wrong observed URL reached finalizer'))
    with pytest.raises(ValueError,match='URL'):host.finish(rec,state,profile,'https://www.canva.com/design/other/edit',True)


def test_pending_download_identity_cannot_be_replaced(tmp_path,monkeypatch):
    state,rec,profile,file,url=fixture(tmp_path)
    db=sqlite3.connect(profile/'History');db.execute('update downloads set state=0');db.commit();db.close()
    def replace(seconds):
        db=sqlite3.connect(profile/'History');db.execute("update downloads set state=1,id=2,guid='different-download'");db.commit();db.close()
    monkeypatch.setattr(host.time,'sleep',replace)
    with pytest.raises(ValueError,match='record identity changed'):host.acquire_wait(rec,state,profile,url,True,4)
    assert bridge.status(state)['status']=='WAIT_DOWNLOAD'

def test_expired_wait_budget_does_not_accept_late_completion(tmp_path):
    state,rec,profile,file,url=fixture(tmp_path)
    record=host._read(rec);record['completion_deadline']=0;host._save(rec,record)
    with pytest.raises(ValueError,match='timeout'):host.acquire_wait(rec,state,profile,url,True,120)


def test_slow_poll_cannot_accept_completion_after_deadline(tmp_path,monkeypatch):
    state,rec,profile,file,url=fixture(tmp_path)
    db=sqlite3.connect(profile/'History');db.execute('update downloads set state=0');db.commit();db.close()
    clock=[100.0]
    monkeypatch.setattr(host.time,'time',lambda:clock[0])
    def wake_late(seconds):
        clock[0]=105.0
        db=sqlite3.connect(profile/'History');db.execute('update downloads set state=1');db.commit();db.close()
    monkeypatch.setattr(host.time,'sleep',wake_late)
    with pytest.raises(ValueError,match='timeout'):host.acquire_wait(rec,state,profile,url,True,4)
