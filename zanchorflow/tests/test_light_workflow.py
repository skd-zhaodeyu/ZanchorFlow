"""Light-workflow behavior checks. Local fixtures only; no service submissions."""
import sys,json,copy
from pathlib import Path
from unittest.mock import patch
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import download_evidence as de,download_transport as dt,host_acquisition as h
import layer_review_boxes as boxes,layer_bridge as lb,layer_edit_review as edit,runtime
from test_v1_image_workflow import ready,bound_bundle,FakeProvider
from test_file_first_download import make_ppt
from test_download_transport import fixture as download_fixture

def test_shape_icon_alias_preserves_raw_kind_and_priority():
    candidates=[{'id':'photo','kind':'photo'},{'id':'shape','kind':'shape_icon'}]
    result=boxes.rank_edit_candidates(candidates,1)
    assert result['selected'][0]['id']=='shape' and result['selected'][0]['kind']=='shape_icon'
    assert candidates[1]['kind']=='shape_icon'
    candidates[0]['user_explicit']=True
    assert boxes.rank_edit_candidates(candidates,1)['selected'][0]['id']=='photo'

def test_unknown_type_not_assumed_shape():
    assert boxes.rank_edit_candidates([{'id':'a','kind':'unknown'},{'id':'b','kind':'icon'}],1)['selected'][0]['id']=='b'

@pytest.mark.parametrize('action,expected',[('normal','normal'),('recovery','recovery'),('export_retry','normal')])
def test_shared_action_mapping(action,expected):assert de.browser_action(action)==expected

def test_reexport_event_path_accepted(tmp_path,monkeypatch):
    state,identity,record,directory,url,snap=download_fixture(tmp_path)
    retry=h.snapshot(record,state,directory,url,'export_retry')
    file=make_ppt(directory/'generic.pptx');monkeypatch.setattr(de.time,'sleep',lambda _:None)
    result=h.observe(record,state,retry['snapshot']['path'],1,True,event_path=str(file))
    assert result['status']=='FILE_COMPLETE'

def observed_invalid(tmp_path,monkeypatch,completed=False,partial=False):
    state,identity,record,directory,url,snap=download_fixture(tmp_path)
    file=directory/'bad.pptx';file.write_bytes(b'bad package')
    if partial:(directory/'bad.pptx.crdownload').write_bytes(b'partial')
    monkeypatch.setattr(de.time,'sleep',lambda _:None)
    return de.observe_transport_snapshot(snap['snapshot'],h._read(record),1,[str(file)] if completed else [])

def test_stable_bad_file_not_claimed_complete_or_growing(tmp_path,monkeypatch):
    result=observed_invalid(tmp_path,monkeypatch)
    assert result['status']=='FILE_UNVERIFIED' and result['invalid']

def test_finished_bad_file_is_invalid(tmp_path,monkeypatch):
    assert observed_invalid(tmp_path,monkeypatch,True)['status']=='FILE_INVALID'

def test_partial_marker_remains_in_progress(tmp_path,monkeypatch):
    assert observed_invalid(tmp_path,monkeypatch,False,True)['status']=='FILE_IN_PROGRESS'

def test_good_candidate_not_blocked_by_bad_file(tmp_path,monkeypatch):
    state,identity,record,directory,url,snap=download_fixture(tmp_path)
    (directory/'bad.pptx').write_bytes(b'bad');make_ppt(directory/'good.pptx')
    monkeypatch.setattr(de.time,'sleep',lambda _:None)
    assert de.observe_transport_snapshot(snap['snapshot'],h._read(record),1)['status']=='FILE_COMPLETE'

def test_validation_context_exact_bytes_not_stat(tmp_path):
    file=make_ppt(tmp_path/'source.pptx')
    with dt.validation_session() as context:
        first=dt.validate_pptx(file);second=dt.validate_pptx(file)
        assert first==second and context['parses']==1 and context['hits']==1
        file.write_bytes(b'bad')
        with pytest.raises(Exception):dt.validate_pptx(file)
    with dt.validation_session() as fresh:
        good=make_ppt(file);dt.validate_pptx(good)
        assert fresh['parses']==1 and fresh['hits']==0

def test_preview_reuse_and_nonmove_omission(tmp_path,monkeypatch):
    state,plan,bundle,page=bound_bundle(tmp_path,monkeypatch)
    payload=json.loads((bundle/'layer-plan.json').read_text());payload['targets'][0]['primary_edit_action']='hide'
    (bundle/'layer-plan.json').write_text(json.dumps(payload))
    first=edit.previews(bundle,tmp_path/'review')
    assert 'moved' not in first['targets'][0] and first['overview']['purpose']=='navigation_only'
    second=edit.previews(bundle,tmp_path/'review')
    assert second['reused']
    file=bundle/'foreground_01.png';file.write_bytes(b'changed')
    with pytest.raises(ValueError):edit.previews(bundle,tmp_path/'review')

class RecoveryProvider(FakeProvider):
    query_status='DONE';wrong_task=False;queries=0
    @staticmethod
    def query_task(task,key):
        RecoveryProvider.queries+=1
        return {'normalized_status':RecoveryProvider.query_status,'task_id':'wrong' if RecoveryProvider.wrong_task else task,'usage':{}}
    @staticmethod
    def normalize_done_result(response,plan,output_dir):
        output_dir.mkdir(parents=True);raw=output_dir/'raw';raw.mkdir()
        Image.new('RGBA',(800,450),'white').save(raw/'bg.png')
        Image.new('RGBA',(800,450),(0,0,0,0)).save(raw/'fg.png')
        result={'page_id':plan['page_id'],'request_id':response['task_id'],'backend_canvas':[800,450],
                'layers':[{'type':'background','file':'raw/bg.png'},{'type':'foreground','target_id':'a','file':'raw/fg.png'}]}
        path=output_dir/'backend-result.json';path.write_text(json.dumps(result));return path

def recover_fixture(tmp_path,monkeypatch):
    state,plan,overlay=ready(tmp_path,monkeypatch)
    RecoveryProvider.query_status='DONE';RecoveryProvider.wrong_task=False;RecoveryProvider.queries=0
    lb.submit(state,'S001',tmp_path/'work',RecoveryProvider)
    lb.query(state,'S001',tmp_path/'work',RecoveryProvider)
    previous=copy.deepcopy(runtime.load_runtime_state(state)['layer_bridge']['results']['S001'])
    (Path(previous['path']).parent/'raw/bg.png').unlink()
    return state,previous

def test_done_recovery_no_submit_and_distinct_directory(tmp_path,monkeypatch):
    state,old=recover_fixture(tmp_path,monkeypatch)
    calls=FakeProvider.calls
    assert lb.query(state,'S001',tmp_path/'work',RecoveryProvider)['status']=='LAYER_RESULT_BOUND'
    now=runtime.load_runtime_state(state)
    new=now['layer_bridge']['results']['S001']
    assert new['task_id']==old['task_id'] and new['path']!=old['path'] and Path(old['path']).exists()
    assert FakeProvider.calls==calls and now['layer_bridge']['requests']['S001']['status']=='DONE'
    queries=RecoveryProvider.queries
    assert lb.query(state,'S001',tmp_path/'work',RecoveryProvider)['reused']
    assert RecoveryProvider.queries==queries

@pytest.mark.parametrize('status',['RUNNING','NOT_FOUND','FAILED'])
def test_done_recovery_does_not_downgrade_or_submit(tmp_path,monkeypatch,status):
    state,old=recover_fixture(tmp_path,monkeypatch)
    RecoveryProvider.query_status=status;calls=FakeProvider.calls
    result=lb.query(state,'S001',tmp_path/'work',RecoveryProvider)
    data=runtime.load_runtime_state(state)
    assert result['status'].startswith('LAYER_RESULT_RECOVERY')
    assert data['layer_bridge']['requests']['S001']['status']=='DONE'
    assert data['layer_bridge']['results']['S001']==old and FakeProvider.calls==calls

def test_wrong_task_recovery_rejected(tmp_path,monkeypatch):
    state,old=recover_fixture(tmp_path,monkeypatch);RecoveryProvider.wrong_task=True
    with pytest.raises(ValueError,match='identity mismatch'):lb.query(state,'S001',tmp_path/'work',RecoveryProvider)
    assert runtime.load_runtime_state(state)['layer_bridge']['results']['S001']==old

def test_compact_cli_keeps_recovery_data_without_full_record_mirror(tmp_path,monkeypatch):
    state,identity,record,directory,url,snap=download_fixture(tmp_path)
    result={'status':'FILE_UNVERIFIED','delta':[{'path':'candidate','bytes':1}],
            'invalid':[{'path':'candidate','error':'BadZipFile'}],'identity':identity,
            'large_debug_context':'x'*20000}
    monkeypatch.setattr(h,'observe',lambda *a,**k:copy.deepcopy(result))
    args=['host_acquisition.py','observe','--record',str(record),'--state',str(state),
          '--snapshot',snap['snapshot']['path']]
    monkeypatch.setattr(sys,'argv',args);h.main()
    full=Path(str(record)+'.observe.result.json').read_bytes()
    monkeypatch.setattr(sys,'argv',args+['--record-detail','compact']);h.main()
    compact=Path(str(record)+'.observe.result.json').read_bytes()
    data=json.loads(compact)
    assert len(compact)<len(full) and data['invalid']==result['invalid']
    assert 'large_debug_context' not in data and h._read(record)['last_operation']['status']=='FILE_UNVERIFIED'

def test_completed_invalid_capture_requires_current_operation(tmp_path,monkeypatch):
    state,identity,record,directory,url,snap=download_fixture(tmp_path)
    file=directory/'bad.pptx';file.write_bytes(b'bad')
    op=tmp_path/'operation.json'
    data={'source':'canva_host.download','identity':identity,'acquisition_id':h._read(record)['acquisition_id'],
          'operation_id':'fixture-event','action':'normal','observed_url':url,'path':str(file),'completed':True}
    op.write_text(json.dumps(data));monkeypatch.setattr(de.time,'sleep',lambda _:None)
    assert h.observe(record,state,snap['snapshot']['path'],1,operation_capture=op)['status']=='FILE_INVALID'
    data['acquisition_id']='wrong';op.write_text(json.dumps(data))
    with pytest.raises(ValueError):h.observe(record,state,snap['snapshot']['path'],1,operation_capture=op)

def test_recovery_content_mismatch_does_not_replace_old_record(tmp_path,monkeypatch):
    state,old=recover_fixture(tmp_path,monkeypatch)
    original=RecoveryProvider.normalize_done_result
    def wrong(response,plan,output_dir):
        path=original(response,plan,output_dir)
        Image.new('RGBA',(800,450),'black').save(path.parent/'raw/bg.png')
        return path
    monkeypatch.setattr(RecoveryProvider,'normalize_done_result',wrong)
    result=lb.query(state,'S001',tmp_path/'work',RecoveryProvider)
    assert result['status']=='LAYER_RESULT_RECOVERY_MISMATCH'
    assert runtime.load_runtime_state(state)['layer_bridge']['results']['S001']==old

@pytest.mark.parametrize('field',['run_id','plan_sha256','text_clean_sha256','task_id'])
def test_done_reuse_rejects_mismatched_record_lineage(tmp_path,monkeypatch,field):
    state,old=recover_fixture(tmp_path,monkeypatch)
    Image.new('RGBA',(800,450),'white').save(Path(old['path']).parent/'raw/bg.png')
    data=runtime.load_runtime_state(state)
    data['layer_bridge']['results']['S001'][field]='other'
    runtime._save_runtime_state(state,data)
    queries=RecoveryProvider.queries;calls=FakeProvider.calls
    with pytest.raises(ValueError,match='lineage mismatch'):
        lb.query(state,'S001',tmp_path/'work',RecoveryProvider)
    assert RecoveryProvider.queries==queries and FakeProvider.calls==calls

@pytest.mark.parametrize('paused,expected',[(False,'FILE_IN_PROGRESS'),(True,'FILE_UNVERIFIED')])
def test_growth_and_pause_remain_distinct(tmp_path,monkeypatch,paused,expected):
    state,identity,record,directory,url,snap=download_fixture(tmp_path)
    file=directory/'candidate.pptx';file.write_bytes(b'incomplete')
    clock=[0.0];writes=[0]
    def tick(seconds):
        clock[0]+=seconds
        if not paused or writes[0]==0:
            file.write_bytes(file.read_bytes()+b'x')
            writes[0]+=1
    monkeypatch.setattr(de.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(de.time,'sleep',tick)
    result=de.observe_transport_snapshot(snap['snapshot'],h._read(record),3)
    assert result['status']==expected
    assert bool(result['growing']) is (not paused)

def test_tampered_preview_regenerated_without_quality_pass(tmp_path,monkeypatch):
    state,plan,bundle,page=bound_bundle(tmp_path,monkeypatch)
    first=edit.previews(bundle,tmp_path/'review')
    Path(first['targets'][0]['hidden']['file']).write_bytes(b'tampered')
    second=edit.previews(bundle,tmp_path/'review')
    assert not second.get('reused',False)
    assert all(x['assessment']=='NOT_ASSESSED' for x in second['targets'])
    assert all(x['hidden']['sha256']==edit.sha(x['hidden']['file']) for x in second['targets'])
