import json, os, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import runtime
from stage2_test_helpers import write_png, write_truth


def ready_state(tmp_path, clean_count=2):
    outline={'slides':[]}
    for i in range(2):
        outline['slides'].append({k:f'{k}-{i}' for k in (
            'page_task','title','core_expression','key_information','semantic_relation','acceptance_criteria')})
    op=tmp_path/'outline.json'; op.write_text(json.dumps(outline),encoding='utf-8')
    state=tmp_path/'state.json'; state.write_text('{"slides":{}}',encoding='utf-8')
    runtime.record_stage1_draft(state,op); runtime.present_stage1_review(state)
    runtime.handle_stage1_reply(state,'同意',decision='approve'); runtime.start_stage2_run(state)
    for kind in ('anchor','style_dna'):
        p=tmp_path/kind; p.write_bytes(kind.encode()); runtime.register_stage2_artifact(state,kind,p)
    for sid in ('S001','S002'):
        render=write_png(tmp_path/f'{sid}-render.png')
        c=runtime.register_stage2_candidate(state,sid,render,generation_intent='fixture')
        runtime.review_stage2_candidate(state,c['candidate_id'],'PASS')
    runtime.present_stage2_formal_display(state); runtime.seal_stage2_visual_approval(state,'确认')
    for sid in ('S001','S002'):
        truth=write_truth(tmp_path/f'{sid}-truth.json',sid)
        runtime.register_stage2_artifact(state,f'final_content_truth:{sid}',truth)
        runtime.mark_stage2_text_reconciled(state,sid)
    for sid in ('S001','S002')[:clean_count]:
        clean=write_png(tmp_path/f'{sid}-clean.png')
        runtime.register_stage2_artifact(state,f'text_clean:{sid}',clean)
    return state


def test_backend_choice_requires_all_current_text_clean(tmp_path):
    import reconstruction_router as router
    state=ready_state(tmp_path,1)
    with pytest.raises(ValueError,match='RECONSTRUCTION_BACKEND_SELECTION_NOT_READY'):
        router.choose_backend(state,'magic_layer')
    assert router.status(state)=={'status':'PREPARE_TEXT','slide_id':'S002'}


def test_selection_prompt_contract():
    import reconstruction_router as router
    prompt=router.selection_prompt()
    assert 'Magic Layer 分支（推荐）' in prompt
    assert 'Image Layer 分支' in prompt
    assert '推荐使用 Magic Layer 分支。' in prompt
    assert 'Canva 分支' not in prompt


def test_choose_backend_keeps_canva_state_untouched(tmp_path):
    import reconstruction_router as router
    state=ready_state(tmp_path,2)
    before=runtime.load_runtime_state(state).get('canva_bridge')
    record=router.choose_backend(state,'magic_layer')
    assert record['backend']=='magic_layer'
    assert router.selected_backend(state)=='magic_layer'
    assert runtime.load_runtime_state(state).get('canva_bridge')==before


def test_image_backend_selection_and_onboarding_do_not_store_secret(tmp_path,monkeypatch):
    import reconstruction_router as router
    state=ready_state(tmp_path,2)
    router.choose_backend(state,'image_layer')
    monkeypatch.delenv(router.IMAGE_LAYER_API_KEY_ENV,raising=False)
    status=router.status(state)
    assert status=={'status':'LAYER_PLAN_REQUIRED','slide_id':'S001'}
    onboarding=router.image_layer_onboarding()
    assert onboarding['api_key_url']=='https://research.360.cn/workspace/apikeys'
    assert onboarding['message']=='请核实当前账户的免费权益、余额与价格，并在真实提交前确认费用授权。'
    monkeypatch.setenv(router.IMAGE_LAYER_API_KEY_ENV,'secret-value')
    assert 'secret-value' not in json.dumps(router.status(state),ensure_ascii=False)
    assert 'secret-value' not in state.read_text(encoding='utf-8')


def test_text_clean_change_keeps_backend_selection(tmp_path):
    import reconstruction_router as router
    state=ready_state(tmp_path,2)
    router.choose_backend(state,'image_layer')
    changed=tmp_path/'S001-clean-new.png'; changed.write_bytes(b'changed-clean')
    runtime.register_stage2_artifact(state,'text_clean:S001',changed)
    assert router.selected_backend(state)=='image_layer'


def test_new_stage2_run_makes_old_backend_selection_stale(tmp_path):
    import reconstruction_router as router
    state=ready_state(tmp_path,2)
    router.choose_backend(state,'magic_layer')
    runtime.start_stage2_run(state,restart=True)
    assert router.selected_backend(state) is None


def test_resume_stage_is_backend_neutral(tmp_path):
    import reconstruction_router as router
    state=ready_state(tmp_path,2)
    assert runtime.resume_stage({'slide_id':'S001','text_clean':True,'text_clean_fingerprint_matches':True,
                                 'approved_render':True,'final_content_truth':True},state)=='stage3_reconstruction_backend_selection'
    router.choose_backend(state,'magic_layer')
    assert runtime.resume_stage({'slide_id':'S001','text_clean':True,'text_clean_fingerprint_matches':True,
                                 'approved_render':True,'final_content_truth':True},state)=='stage3_magic_layer'
    # Context-only fallback remains conservative without trusted Runtime state and never defaults to Magic.
    assert runtime.resume_stage({'text_clean':True,'text_clean_fingerprint_matches':True,'approved_render':True,
                                 'final_content_truth':True})=='AWAITING_STAGE1_APPROVAL'


def test_image_backend_records_one_run_level_target_canvas_and_rejects_mixed_ratios(tmp_path):
    import reconstruction_router as router
    from PIL import Image
    state=ready_state(tmp_path,2)
    rec=router.choose_backend(state,'image_layer')
    assert isinstance(rec.get('target_slide_emu'),list) and len(rec['target_slide_emu'])==2
    assert all(isinstance(v,int) and v>0 for v in rec['target_slide_emu'])
    # A different current source ratio makes Image Layer target canvas unresolved.
    mixed=tmp_path/'mixed'; mixed.mkdir()
    state2=ready_state(mixed,2)
    wide=mixed/'S001-clean-wide.png'; Image.new('RGB',(1600,900),'white').save(wide)
    square=mixed/'S002-clean-square.png'; Image.new('RGB',(1000,1000),'white').save(square)
    runtime.register_stage2_artifact(state2,'text_clean:S001',wide)
    runtime.register_stage2_artifact(state2,'text_clean:S002',square)
    with pytest.raises(ValueError,match='TARGET_DECK_CANVAS_UNRESOLVED'):
        router.choose_backend(state2,'image_layer')


def test_magic_page_provenance_delegates_unchanged(tmp_path):
    import reconstruction_router as router, canva_bridge
    # Legacy/external sealed pages remain Magic-route compatible before RC18 backend binding.
    state=ready_state(tmp_path,2)
    saved=runtime.load_runtime_state(state)
    for sid in saved['stage2_run']['page_order']:
        for kind,payload in [('canvas',{'width':1,'height':1}),('finalized_manifest',{'page_id':sid}),('font_fallback',{})]:
            artifact=tmp_path/f'{sid}-{kind}.json'; artifact.write_text(json.dumps(payload),encoding='utf-8')
            runtime.register_stage2_artifact(state,f'{kind}:{sid}',artifact)
        page=tmp_path/f'{sid}.pptx'; page.write_bytes(sid.encode())
        runtime.seal_validated_single_page(state,sid,page,{k:'PASS' for k in runtime.GATE_NAMES})
    saved=runtime.load_runtime_state(state)
    for sid in saved['stage2_run']['page_order']:
        assert router.page_provenance(saved,sid)==canva_bridge.page_provenance(saved,sid)


def test_router_cli_exposes_status_and_explicit_backend_choice(tmp_path,capsys):
    import reconstruction_router as router
    state=ready_state(tmp_path,2)
    assert router.main(['status','--state',str(state)])==0
    assert json.loads(capsys.readouterr().out)['status']=='AWAITING_RECONSTRUCTION_BACKEND_SELECTION'
    assert router.main(['choose-backend','--state',str(state),'--backend','magic_layer'])==0
    assert json.loads(capsys.readouterr().out)['backend']=='magic_layer'


def test_magic_layer_selection_does_not_create_image_layer_remote_state(tmp_path):
    import reconstruction_router as router
    import runtime
    state = ready_state(tmp_path, 2)
    router.choose_backend(state, 'magic_layer')
    saved = runtime.load_runtime_state(state)
    assert saved['reconstruction_backend']['backend'] == 'magic_layer'
    assert 'layer_bridge' not in saved
