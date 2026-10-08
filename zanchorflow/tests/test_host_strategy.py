import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import host_acquisition as h
import canva_bridge as b
from test_host_compact import prepare_fixture


def prepare(tmp_path,state,rec,lp,strategy=None,reason=None):
    return h.prepare(rec,state,'S001',lp,tmp_path/'out','S001.pptx',strategy,reason)


def test_original_prepare_remains_compatible(tmp_path):
    state,rec,lp=prepare_fixture(tmp_path)
    result=prepare(tmp_path,state,rec,lp)
    assert 'host_strategy' not in result
    assert prepare(tmp_path,state,rec,lp)==result


@pytest.mark.parametrize('reason',['Host event API unavailable','DOM still ambiguous after fresh observation'])
def test_preclick_fallback_preserves_identity_request_and_ui_budget(tmp_path,reason):
    state,rec,lp=prepare_fixture(tmp_path);before=state.read_bytes()
    first=prepare(tmp_path,state,rec,lp,'dom_event')
    h.reserve_retry(rec,state,'S001','ui');budget=Path(str(rec)+'.retries.json').read_bytes()
    second=prepare(tmp_path,state,rec,lp,'legacy_observation',reason)
    assert second['acquisition_id']==first['acquisition_id'] and second['identity']==first['identity']
    assert second['request']==first['request'] and second['status']=='READY'
    assert second['host_strategy']['phase']=='pre_download'
    assert len(second['host_strategy_history'])==2
    assert Path(str(rec)+'.retries.json').read_bytes()==budget and state.read_bytes()==before
    assert h.reserve_retry(rec,state,'S001','ui')['retry_number']==2


@pytest.mark.parametrize('failure',['listener timeout','unknown click','kernel reset','path unavailable'])
def test_postlock_fallback_is_observation_only_and_does_not_reset_budget(tmp_path,failure):
    state,rec,lp=prepare_fixture(tmp_path)
    prepare(tmp_path,state,rec,lp,'dom_event');h.lock(rec)
    marker=Path(str(rec)+'.intent').read_bytes()
    h.reserve_retry(rec,state,'S001','observe');budget=Path(str(rec)+'.retries.json').read_bytes()
    h.fail(rec,'DOWNLOAD_UNKNOWN')
    result=prepare(tmp_path,state,rec,lp,'legacy_observation',failure)
    assert result['status']=='FAILED' and result['failure_checkpoint']=='DOWNLOAD_UNKNOWN'
    assert result['host_strategy']['phase']=='recovery'
    assert Path(str(rec)+'.intent').read_bytes()==marker
    assert Path(str(rec)+'.retries.json').read_bytes()==budget
    with pytest.raises(ValueError):h.lock(rec)
    assert prepare(tmp_path,state,rec,lp,'dom_event','retry after diagnosis')['host_strategy']['strategy']=='dom_event'
    assert h.reserve_retry(rec,state,'S001','ui')['retry_number']==1
    assert h.reserve_retry(rec,state,'S001','observe')['retry_number']==2


def test_invalid_strategy_does_not_create_record(tmp_path):
    state,rec,lp=prepare_fixture(tmp_path)
    with pytest.raises(ValueError):prepare(tmp_path,state,rec,lp,'invented')
    assert not rec.exists()


def test_switch_requires_reason_and_never_changes_record_on_error(tmp_path):
    state,rec,lp=prepare_fixture(tmp_path);prepare(tmp_path,state,rec,lp,'dom_event');before=rec.read_bytes()
    with pytest.raises(ValueError):prepare(tmp_path,state,rec,lp,'legacy_observation')
    assert rec.read_bytes()==before


def test_same_strategy_audit_is_idempotent(tmp_path):
    state,rec,lp=prepare_fixture(tmp_path)
    first=prepare(tmp_path,state,rec,lp,'dom_event')
    assert prepare(tmp_path,state,rec,lp,'dom_event')==first


def test_formal_finish_and_same_file_resume_after_strategy_fallback(tmp_path,monkeypatch):
    from test_host_compact import finish_fixture
    state,rec,profile,file,url=finish_fixture(tmp_path)
    record=h._read(rec);lp=Path(record['request']['lookup_path']);target=Path(record['request']['download_target_dir'])
    # This fixture already locked the intent; only observation fallback is permitted.
    h.prepare(rec,state,'S001',lp,target,record['request']['target_filename'],'legacy_observation','event path requires History confirmation')
    result=h.finish(rec,state,profile,url,True,python_executable=sys.executable)
    assert result['status']=='DOWNLOAD_BOUND'
    assert h.finish(rec,state,profile,url,True)['reused'] is True
    assert b.sha(Path(result['path']))==result['sha256'] and not file.exists()
    with pytest.raises(ValueError):h.lock(rec)
