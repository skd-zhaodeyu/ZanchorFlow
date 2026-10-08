"""V1 mechanical regression; all providers and user authorizations are synthetic."""
import json,copy,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import layer_bridge as lb,layer_policy as policy,layer_edit_review as edit,layer_review_boxes as boxes,runtime
from test_layer_bridge import image_state,write_plan,approve_ready_plan,seed_current_result_and_bundle,human_request

class FakeProvider:
    PROVIDER_ID='synthetic';MODEL='synthetic';VERSION='fixture';calls=0
    @staticmethod
    def submit_task(*a,**k):
        FakeProvider.calls+=1;return {'task_id':'fixture-'+str(FakeProvider.calls)}

def ready(tmp_path,monkeypatch):
    state=image_state(tmp_path);plan,overlay=write_plan(tmp_path)
    lb.register_plan(state,'S001',plan,overlay);approve_ready_plan(state,'S001',new_policy=True)
    monkeypatch.setenv('ZANCHORFLOW_360_API_KEY','fixture-not-a-key')
    FakeProvider.calls=0
    return state,plan,overlay

def report(state,bundle,output,status='PASS'):
    evidence=edit.previews(bundle,output)
    rows=[]
    for item in evidence['targets']:
        rows.append({'target_id':item['target_id'],'requested_action':'move','assessment':status,
            'capability_preserved':status!='FAIL','actual_independence':'Synthetic independent selection',
            'background_residual':'Synthetic complete original remains' if status=='FAIL' else 'Synthetic checked clean',
            'neighbor_impact':'Synthetic checked','connector_behavior':'No automatic connector claim',
            'explanation':'Offline test judgment, not live model quality','hidden_evidence':[item['hidden']],
            'move_evidence':[item['moved']]})
    return {'page_id':'S001','bundle_manifest_sha256':edit.sha(Path(bundle)/'manifest.json'),
            'checks':{'layer_isolation':'PASS','background_repair':'FAIL' if status=='FAIL' else 'PASS','recomposite_fidelity':'PASS'},
            'evidence':{x:'Synthetic evidence' for x in policy.CHECKS},'target_edit_checks':rows}

def bound_bundle(tmp_path,monkeypatch):
    state,plan,overlay=ready(tmp_path,monkeypatch)
    bundle,page=seed_current_result_and_bundle(state,tmp_path)
    lb.bind_bundle(state,'S001',bundle)
    return state,plan,bundle,page

def test_default_priorities_and_explicit_photo_override():
    candidates=[{'id':'photo','kind':'photo'},{'id':'icon','kind':'icon'},
        {'id':'card','kind':'card'},{'id':'bg','kind':'shape','protected_background':True},
        {'id':'requested','kind':'photo','user_explicit':True}]
    result=boxes.rank_edit_candidates(candidates,3)
    assert [x['id'] for x in result['selected']]==['requested','icon','card']
    assert result['recommended_total_layers']==5 and len(result['deferred'])==2

def test_six_slots_do_not_merge_unrelated_units():
    result=boxes.rank_edit_candidates([{'id':str(i),'kind':'card'} for i in range(9)])
    assert len(result['selected'])==6 and result['recommended_total_layers']==10
    assert len(result['deferred'])==3

def test_second_call_requires_active_user_even_with_budget_flags(tmp_path,monkeypatch):
    state,plan,overlay=ready(tmp_path,monkeypatch)
    lb.submit(state,'S001',tmp_path/'work',FakeProvider)
    with pytest.raises(ValueError,match='USER_INITIATED'):lb.submit(state,'S001',tmp_path/'work',FakeProvider)
    assert FakeProvider.calls==1

@pytest.mark.parametrize('change',['plan','input','backend','restore'])
def test_changes_do_not_create_a_new_first_call(tmp_path,monkeypatch,change):
    state,plan,overlay=ready(tmp_path,monkeypatch);lb.submit(state,'S001',tmp_path/'work',FakeProvider)
    if change in ('plan','input'):
        data=json.loads(plan.read_text());data['targets'][0]['bbox']=[110,110,510,510]
        if change=='input':
            from PIL import Image
            image=tmp_path/'new-clean.png';Image.new('RGB',(1600,900),'black').save(image)
            runtime.register_stage2_artifact(state,'text_clean:S001',image)
        revised=tmp_path/'revised-plan.json';revised.write_text(json.dumps(data))
        lb.register_plan(state,'S001',revised,overlay);approve_ready_plan(state,'S001',new_policy=True)
    if change=='backend':monkeypatch.setattr(FakeProvider,'MODEL','different')
    if change=='restore':state=Path(str(state))
    with pytest.raises(ValueError,match='USER_INITIATED'):lb.submit(state,'S001',tmp_path/'work',FakeProvider)
    assert FakeProvider.calls==1

def test_generic_fee_authorization_not_a_relayer_instruction(tmp_path,monkeypatch):
    state,plan,overlay=ready(tmp_path,monkeypatch);lb.submit(state,'S001',tmp_path/'work',FakeProvider)
    path=human_request(state,'S001',FakeProvider)
    data=json.loads(path.read_text());data.pop('user_requested_relayer');path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='USER_INITIATED'):lb.authorize_resubmit(state,'S001',path,FakeProvider)

def test_explicit_instruction_consumed_and_cannot_replay(tmp_path,monkeypatch):
    state,plan,overlay=ready(tmp_path,monkeypatch);lb.submit(state,'S001',tmp_path/'work',FakeProvider)
    # technical failure confirmed for fixture; no real model was called
    data=runtime.load_runtime_state(state);data['layer_bridge']['requests']['S001']['status']='LAYER_RETRY_APPROVAL_REQUIRED'
    runtime._save_runtime_state(state,data)
    path=human_request(state,'S001',FakeProvider)
    lb.authorize_resubmit(state,'S001',path,FakeProvider)
    lb.submit(state,'S001',tmp_path/'work',FakeProvider)
    with pytest.raises(ValueError,match='USER_INITIATED'):lb.submit(state,'S001',tmp_path/'work',FakeProvider)
    with pytest.raises(ValueError,match='consumed'):lb.authorize_resubmit(state,'S001',path,FakeProvider)
    assert FakeProvider.calls==2

def test_legacy_task_id_counts_without_new_ledger(tmp_path,monkeypatch):
    state,plan,overlay=ready(tmp_path,monkeypatch)
    data=runtime.load_runtime_state(state)
    data['layer_bridge']['requests']['S001']={'status':'LAYER_REQUEST_UNCERTAIN','task_id':'old-task'}
    runtime._save_runtime_state(state,data)
    with pytest.raises(ValueError,match='USER_INITIATED'):lb.submit(state,'S001',tmp_path/'work',FakeProvider)
    assert FakeProvider.calls==0

def test_target_hide_and_move_evidence_not_an_automatic_pass(tmp_path,monkeypatch):
    state,plan,bundle,page=bound_bundle(tmp_path,monkeypatch)
    data=edit.previews(bundle,tmp_path/'preview')
    assert data['targets'][0]['assessment']=='NOT_ASSESSED'
    assert Path(data['targets'][0]['hidden']['file']).is_file()
    qa=report(state,bundle,tmp_path/'review');path=tmp_path/'qa.json';path.write_text(json.dumps(qa))
    assert lb.register_visual_qa(state,'S001',path)['status']=='LAYER_VISUAL_QA_PASS'

def test_complete_residual_not_success_and_no_resubmit_prompt(tmp_path,monkeypatch):
    state,plan,bundle,page=bound_bundle(tmp_path,monkeypatch)
    qa=report(state,bundle,tmp_path/'review','FAIL');path=tmp_path/'qa.json';path.write_text(json.dumps(qa))
    result=lb.register_visual_qa(state,'S001',path)
    assert result['status']=='LAYER_VISUAL_QA_FAILED' and result['remote_result_received']
    assert not result['automatic_resubmit']
    status=lb.status(state)
    assert status['page_statuses'][0]['follow_up']=='report_actual_result_without_retry_prompt'
    assert 'S002' in status['actionable_pages']
    with pytest.raises(ValueError):lb.bind_graphics_first(state,'S001',page,bundle)
    assert FakeProvider.calls==0

@pytest.mark.parametrize('change',['missing','bad_id','tamper','capability','action'])
def test_missing_false_or_changed_editing_evidence_rejected(tmp_path,monkeypatch,change):
    state,plan,bundle,page=bound_bundle(tmp_path,monkeypatch)
    qa=report(state,bundle,tmp_path/'review')
    if change=='missing':qa.pop('target_edit_checks')
    elif change=='bad_id':qa['target_edit_checks'][0]['target_id']='wrong'
    elif change=='tamper':Path(qa['target_edit_checks'][0]['hidden_evidence'][0]['file']).write_bytes(b'changed')
    elif change=='capability':qa['target_edit_checks'][0]['capability_preserved']=False
    elif change=='action':qa['target_edit_checks'][0]['requested_action']='hide'
    path=tmp_path/'qa.json';path.write_text(json.dumps(qa))
    with pytest.raises(ValueError):lb.register_visual_qa(state,'S001',path)

def test_received_result_reused_without_key_or_another_call(tmp_path,monkeypatch):
    state,plan,bundle,page=bound_bundle(tmp_path,monkeypatch)
    monkeypatch.delenv('ZANCHORFLOW_360_API_KEY',raising=False)
    result=lb.submit(state,'S001',tmp_path/'work',FakeProvider)
    assert result['reused'] and result['status']=='LAYER_RESULT_BOUND'
    assert FakeProvider.calls==0

def test_done_record_missing_bytes_is_local_recovery_not_success_or_resubmit(tmp_path,monkeypatch):
    state,plan,overlay=ready(tmp_path,monkeypatch)
    lb.submit(state,'S001',tmp_path/'work',FakeProvider)
    data=runtime.load_runtime_state(state);data['layer_bridge']['requests']['S001']['status']='DONE'
    runtime._save_runtime_state(state,data)
    result=lb.submit(state,'S001',tmp_path/'work',FakeProvider)
    assert result['status']=='LAYER_LOCAL_RESULT_RECOVERY_REQUIRED'
    assert FakeProvider.calls==1
