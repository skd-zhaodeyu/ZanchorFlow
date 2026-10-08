import json, os, sys
from pathlib import Path
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import runtime
import reconstruction_router as router
from test_reconstruction_backend_router import ready_state


def write_plan(tmp_path, slide='S001'):
    p=tmp_path/f'{slide}-plan.json'
    p.write_text(json.dumps({'schema_version':1,'page_id':slide,'max_foregrounds':6,'recommended_total_layers':2,
        'targets':[{'id':'a','label':'A','bbox':[100,100,500,500],'edit_action':'move','selection_reason':'fixture'}],
        'deferred':[]}),encoding='utf-8')
    overlay=tmp_path/f'{slide}-boxes.png'; Image.new('RGB',(1600,900),'white').save(overlay)
    return p,overlay


def image_state(tmp_path):
    state=ready_state(tmp_path,2)
    # Backend selection happens only after all current Text-Clean pages are final.
    for sid in ('S001','S002'):
        image=tmp_path/f'{sid}-valid-clean.png'; Image.new('RGB',(1600,900),'white').save(image)
        runtime.register_stage2_artifact(state,f'text_clean:{sid}',image)
    router.choose_backend(state,'image_layer')
    return state


def approve_ready_plan(state,slide_id,new_policy=False):
    import layer_bridge as lb, layer_policy
    rec=lb.approve_plan(state,slide_id)
    saved=runtime.load_runtime_state(state); plan=saved['layer_bridge']['plans'][slide_id]
    if not new_policy:
        # Simulate a pre-V1 persisted Plan for inherited compatibility tests.
        plan.pop('editing_review_required',None);plan.pop('selection_policy',None)
        runtime._save_runtime_state(state,saved)
    evidence=Path(plan['plan_path']).parent/(slide_id+'-readiness.json')
    evidence.write_text(json.dumps({'page_id':slide_id,'text_clean_sha256':plan['text_clean_sha256'],
        'plan_sha256':plan['plan_sha256'],'checks':{k:'READY' for k in layer_policy.READINESS},
        'reasons':{k:'fixture explicitly checked' for k in layer_policy.READINESS}}),encoding='utf-8')
    lb.register_readiness(state,slide_id,evidence)
    return rec

def human_request(state,slide_id,provider,path=None):
    """Synthetic offline human instruction; never a real user authorization."""
    import layer_bridge as lb
    saved=runtime.load_runtime_state(state);plan=saved['layer_bridge']['plans'][slide_id]
    data={'source':'user','user_requested_relayer':True,'authorized':True,
          'user_message_id':'synthetic-user-request','user_message':'Offline fixture: re-layer this page once',
          'authorization_id':'fixture-'+str(lb._submission_count(saved,slide_id)),
          'remaining_image_calls':1,'accept_duplicate_charge_risk':True,'page_id':slide_id,'run_id':plan['run_id'],
          'text_clean_sha256':plan['text_clean_sha256'],'plan_sha256':plan['plan_sha256'],
          'provider_identity':lb._provider_identity(provider)}
    path=Path(path or Path(state).parent/'human-request.json');path.write_text(json.dumps(data),encoding='utf-8')
    return path


def test_plan_binds_text_clean_and_becomes_stale_when_clean_changes(tmp_path):
    import layer_bridge as lb
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path)
    rec=lb.register_plan(state,'S001',plan,overlay)
    assert rec['status']=='LAYER_PLAN_READY' and rec['source_canvas']==[1600,900]
    assert lb.status(state)['status']=='LAYER_PLAN_APPROVAL_REQUIRED'
    changed=tmp_path/'changed.png'; Image.new('RGB',(1600,900),'black').save(changed)
    runtime.register_stage2_artifact(state,'text_clean:S001',changed)
    assert {k:v for k,v in lb.status(state).items() if k not in ('page_statuses','actionable_pages','automatic_resubmit')}=={'status':'LAYER_PLAN_REQUIRED','slide_id':'S001'}


def test_submit_requires_approval_and_api_key_without_remote_call(tmp_path,monkeypatch):
    import layer_bridge as lb
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path); lb.register_plan(state,'S001',plan,overlay)
    class Provider:
        calls=0
        @staticmethod
        def submit_task(*a,**k): Provider.calls+=1; return {'task_id':'x'}
    with pytest.raises(ValueError,match='LAYER_PLAN_NOT_APPROVED'):
        lb.submit(state,'S001',tmp_path/'work',Provider)
    approve_ready_plan(state,'S001'); monkeypatch.delenv(router.IMAGE_LAYER_API_KEY_ENV,raising=False)
    assert lb.submit(state,'S001',tmp_path/'work',Provider)['status']=='IMAGE_LAYER_API_KEY_REQUIRED'
    assert Provider.calls==0


def test_submit_uncertain_blocks_blind_retry_and_requires_duplicate_risk_authorization(tmp_path,monkeypatch):
    import layer_bridge as lb
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path); lb.register_plan(state,'S001',plan,overlay); approve_ready_plan(state,'S001')
    monkeypatch.setenv(router.IMAGE_LAYER_API_KEY_ENV,'secret')
    class Provider:
        calls=0
        @staticmethod
        def submit_task(*a,**k): Provider.calls+=1; raise OSError('lost response')
    assert lb.submit(state,'S001',tmp_path/'work',Provider)['status']=='LAYER_REQUEST_UNCERTAIN'
    with pytest.raises(ValueError,match='USER_INITIATED_RELAYER_REQUIRED'):
        lb.submit(state,'S001',tmp_path/'work',Provider)
    with pytest.raises(ValueError,match='duplicate charge risk'):
        lb.authorize_retry(state,'S001')
    auth=lb.authorize_retry(state,'S001',accept_duplicate_charge_risk=True,authorization_path=human_request(state,'S001',Provider))
    assert auth['status']=='RETRY_AUTHORIZED'


def test_successful_submit_query_running_and_done_bind_result_without_secret(tmp_path,monkeypatch):
    import layer_bridge as lb
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path); lb.register_plan(state,'S001',plan,overlay); approve_ready_plan(state,'S001')
    monkeypatch.setenv(router.IMAGE_LAYER_API_KEY_ENV,'secret-value')
    class Provider:
        queries=0
        @staticmethod
        def submit_task(image,boxes,key):
            assert key=='secret-value'; return {'task_id':'task-1'}
        @staticmethod
        def query_task(task,key):
            Provider.queries+=1
            if Provider.queries==1:return {'task_id':task,'normalized_status':'RUNNING','status':'generating'}
            return {'task_id':task,'normalized_status':'DONE','status':'done','usage':{'total_tokens':10},'output':{}}
        @staticmethod
        def normalize_done_result(response,plan,output_dir):
            output_dir.mkdir(parents=True,exist_ok=True); p=output_dir/'backend-result.json'
            p.write_text(json.dumps({'page_id':plan['page_id'],'backend_canvas':[800,450],'layers':[]}),encoding='utf-8'); return p
    assert lb.submit(state,'S001',tmp_path/'work',Provider)['status']=='LAYER_REQUEST_PENDING'
    assert lb.query(state,'S001',tmp_path/'work',Provider)['status']=='LAYER_REQUEST_PENDING'
    done=lb.query(state,'S001',tmp_path/'work',Provider)
    assert done['status']=='LAYER_RESULT_BOUND'
    saved=runtime.load_runtime_state(state)
    assert 'secret-value' not in json.dumps(saved)
    assert saved['layer_bridge']['results']['S001']['usage']=={'total_tokens':10}
    assert lb.result_current(saved,'S001')


def test_terminal_failure_needs_explicit_retry_authorization(tmp_path,monkeypatch):
    import layer_bridge as lb
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path); lb.register_plan(state,'S001',plan,overlay); approve_ready_plan(state,'S001')
    monkeypatch.setenv(router.IMAGE_LAYER_API_KEY_ENV,'k')
    class Provider:
        @staticmethod
        def submit_task(*a,**k): return {'task_id':'task-1'}
        @staticmethod
        def query_task(*a,**k): return {'task_id':'task-1','normalized_status':'FAILED','status':'failed'}
    lb.submit(state,'S001',tmp_path/'work',Provider)
    assert lb.query(state,'S001',tmp_path/'work',Provider)['status']=='LAYER_RETRY_APPROVAL_REQUIRED'
    with pytest.raises(ValueError,match='USER_INITIATED_RELAYER_REQUIRED'):
        lb.submit(state,'S001',tmp_path/'work',Provider)
    assert lb.authorize_retry(state,'S001',authorization_path=human_request(state,'S001',Provider))['status']=='RETRY_AUTHORIZED'


def seed_current_result_and_bundle(state,tmp_path,slide_id='S001'):
    import reconstruction_router as router
    import layer_package, layer_build_pptx
    saved=runtime.load_runtime_state(state); plan_rec=saved['layer_bridge']['plans'][slide_id]
    plan_path=Path(plan_rec['plan_path']); source=Path(saved['slides'][slide_id]['text_clean'])
    result_dir=tmp_path/'seed-result'; raw=result_dir/'raw'; raw.mkdir(parents=True,exist_ok=True)
    from PIL import Image,ImageDraw
    bg=Image.new('RGBA',(800,450),(255,255,255,255)); bg.save(raw/'bg.png')
    fg=Image.new('RGBA',(800,450),(0,0,0,0)); ImageDraw.Draw(fg).rectangle((50,50,249,249),fill=(255,0,0,255)); fg.save(raw/'fg.png')
    result={'schema_version':1,'page_id':slide_id,'provider_id':'360_reveal_layer','model_id':'reveal_layer','request_id':'task-seed',
      'backend_canvas':[800,450],'image_boxes':[[100,100,500,500]],'resized_image_boxes':[[50,50,250,250]],'boxes_mapping_index':[0],
      'layers':[{'type':'background','file':'raw/bg.png'},{'type':'foreground','target_id':'a','file':'raw/fg.png'}]}
    rp=result_dir/'backend-result.json'; rp.write_text(json.dumps(result),encoding='utf-8')
    rec={'status':'LAYER_RESULT_BOUND','slide_id':slide_id,'run_id':plan_rec['run_id'],'plan_sha256':plan_rec['plan_sha256'],
         'text_clean_sha256':plan_rec['text_clean_sha256'],'task_id':'task-seed','path':str(rp),'sha256':lb_sha(rp),'usage':{}}
    with router.transaction(state) as temp:
        cur=runtime.load_runtime_state(temp); cur.setdefault('layer_bridge',{}).setdefault('results',{})[slide_id]=rec; runtime._save_runtime_state(temp,cur)
    bundle=tmp_path/'bundle'; layer_package.package_layers(source,plan_path,rp,bundle, schema_version=2)
    page=tmp_path/'graphics.pptx'; layer_build_pptx.build_page_pptx(bundle,page)
    return bundle,page


def lb_sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def register_good_visual_qa(state,tmp_path,bundle,slide_id='S001'):
    import layer_bridge as lb
    qa=Path(tmp_path)/f'{slide_id}-visual-qa.json'
    qa.write_text(json.dumps({
        'page_id':slide_id,
        'bundle_manifest_sha256':lb_sha(Path(bundle)/'manifest.json'),
        'checks':{'layer_isolation':'PASS','background_repair':'PASS','recomposite_fidelity':'PASS'},
        'evidence':{'layer_isolation':'synthetic isolation evidence','background_repair':'synthetic background evidence','recomposite_fidelity':'synthetic recomposite evidence'}
    }),encoding='utf-8')
    return lb.register_visual_qa(state,slide_id,qa),qa


def test_bind_bundle_and_graphics_first_register_shared_artifact(tmp_path):
    import layer_bridge as lb
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path); lb.register_plan(state,'S001',plan,overlay); approve_ready_plan(state,'S001')
    bundle,page=seed_current_result_and_bundle(state,tmp_path)
    assert lb.bind_bundle(state,'S001',bundle)['status']=='LAYER_BUNDLE_READY'
    register_good_visual_qa(state,tmp_path,bundle)
    bound=lb.bind_graphics_first(state,'S001',page,bundle)
    assert bound['status']=='LAYER_GRAPHICS_FIRST_READY'
    assert runtime.stage2_artifact_current(state,'graphics_first_pptx:S001')
    saved=runtime.load_runtime_state(state); record=saved['layer_bridge']['graphics_first']['S001']
    assert 'source_to_output_scale' not in json.dumps(record)
    assert 'font_scale' not in json.dumps(record)


def test_bind_graphics_first_applies_source_pixel_5px_gate_after_normalization(tmp_path):
    import layer_bridge as lb
    from pptx import Presentation
    from pptx.util import Inches
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path); lb.register_plan(state,'S001',plan,overlay); approve_ready_plan(state,'S001')
    bundle,page=seed_current_result_and_bundle(state,tmp_path); lb.bind_bundle(state,'S001',bundle); register_good_visual_qa(state,tmp_path,bundle)
    prs=Presentation(page); prs.slide_width=Inches(14); prs.save(page)
    with pytest.raises(ValueError,match='LAYER_GRAPHICS_FIRST_GATE_FAILED'):
        lb.bind_graphics_first(state,'S001',page,bundle)


def test_bind_bundle_requires_run_level_target_canvas_match(tmp_path):
    import layer_bridge as lb
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path); lb.register_plan(state,'S001',plan,overlay); approve_ready_plan(state,'S001')
    bundle,page=seed_current_result_and_bundle(state,tmp_path)
    manifest_path=Path(bundle)/'manifest.json'; manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['ppt']['slide_width_emu'] += 10000
    manifest_path.write_text(json.dumps(manifest),encoding='utf-8')
    # Repair asset-independent manifest hash validation is intentionally not used here; bind must reject target canvas first.
    with pytest.raises(ValueError,match='TARGET_DECK_CANVAS_UNRESOLVED'):
        lb.bind_bundle(state,'S001',bundle)


def test_graphics_first_5px_gate_rejects_same_ratio_whole_canvas_scaling(tmp_path):
    import layer_bridge as lb
    from pptx import Presentation
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path); lb.register_plan(state,'S001',plan,overlay); approve_ready_plan(state,'S001')
    bundle,page=seed_current_result_and_bundle(state,tmp_path); lb.bind_bundle(state,'S001',bundle); register_good_visual_qa(state,tmp_path,bundle)
    manifest=json.loads((Path(bundle)/'manifest.json').read_text(encoding='utf-8'))
    prs=Presentation(page)
    # Preserve the same aspect ratio but enlarge both axes by 2%; this must not bypass the Source-pixel 5px invariant.
    prs.slide_width=round(manifest['ppt']['slide_width_emu']*1.02)
    prs.slide_height=round(manifest['ppt']['slide_height_emu']*1.02)
    prs.save(page)
    with pytest.raises(ValueError,match='LAYER_GRAPHICS_FIRST_GATE_FAILED'):
        lb.bind_graphics_first(state,'S001',page,bundle)


def _seed_image_restoration_inputs(state,tmp_path,slide_id='S001'):
    import shutil
    import layer_bridge as lb
    plan,overlay=write_plan(tmp_path,slide_id)
    lb.register_plan(state,slide_id,plan,overlay); approve_ready_plan(state,slide_id)
    bundle,page=seed_current_result_and_bundle(state,tmp_path,slide_id); lb.bind_bundle(state,slide_id,bundle); register_good_visual_qa(state,tmp_path,bundle,slide_id); lb.bind_graphics_first(state,slide_id,page,bundle)
    canvas=tmp_path/f'{slide_id}-canvas.json'; canvas.write_text(json.dumps({'width':1600,'height':900}),encoding='utf-8')
    runtime.register_stage2_artifact(state,f'canvas:{slide_id}',canvas)
    for kind,payload in [('finalized_manifest',{'page_id':slide_id}),('font_fallback',{})]:
        p=tmp_path/f'{slide_id}-{kind}.json'; p.write_text(json.dumps(payload),encoding='utf-8')
        runtime.register_stage2_artifact(state,f'{kind}:{slide_id}',p)
    restored=tmp_path/f'{slide_id}-restored.pptx'; shutil.copyfile(page,restored)
    current=runtime.load_runtime_state(state); gf=current['layer_bridge']['graphics_first'][slide_id]
    review={'backend':'image_layer','slide_id':slide_id,'graphics_first_sha256':gf['sha256'],
            'restored_pptx_sha256':lb_sha(restored),
            'text_restore_fingerprint':runtime.expected_lineage_from_state(current,slide_id)['text_restore_fingerprint'],
            'checks':{k:'PASS' for k in runtime.GATE_NAMES},
            'evidence':{k:'synthetic Image Layer gate evidence' for k in runtime.GATE_NAMES}}
    review_path=tmp_path/f'{slide_id}-review.json'; review_path.write_text(json.dumps(review),encoding='utf-8')
    return restored,review_path


def test_image_layer_seal_page_produces_backend_specific_provenance(tmp_path):
    import layer_bridge as lb
    state=image_state(tmp_path)
    restored,review=_seed_image_restoration_inputs(state,tmp_path)
    assert lb.seal_page(state,'S001',restored,review)['status']=='PAGE_SEALED'
    saved=runtime.load_runtime_state(state)
    prov=lb.page_provenance(saved,'S001')
    assert prov['backend']=='image_layer'
    assert prov['slide_id']=='S001'
    assert prov['validated_pptx_sha256']==saved['slides']['S001']['validated_single_page']['validated_pptx_sha256']
    assert 'design_id' not in json.dumps(prov)


def test_image_layer_assembly_uses_shared_merge_and_layer_merged_provenance(tmp_path,monkeypatch):
    import layer_bridge as lb
    import assemble_deck as assembly
    state=image_state(tmp_path)
    for sid in ('S001','S002'):
        sub=tmp_path/sid; sub.mkdir()
        restored,review=_seed_image_restoration_inputs(state,sub,sid)
        lb.seal_page(state,sid,restored,review)
    monkeypatch.setattr(assembly.preflight,'check',lambda *_args,**_kwargs:{'blockers':[], 'office_host':'powerpoint'})
    def fake_merge(inputs,order,output,state_path, *, office_host='auto'):
        output.parent.mkdir(parents=True,exist_ok=True); output.write_bytes('|'.join(order).encode())
        runtime.seal_merged_deck(state_path,order,inputs,output)
        return {'status':'PASS','path':str(output),'deck_order':order}
    monkeypatch.setattr(assembly,'merge',fake_merge)
    prepared=assembly.prepare(state,tmp_path/'work')
    saved=runtime.load_runtime_state(state)
    assert saved['layer_bridge']['merged']['pages']==assembly.bridge.deck_provenance(saved,['S001','S002'])
    assert not saved.get('canva_bridge',{}).get('merged')
    review_path=Path(prepared['validation_report']); review=json.loads(review_path.read_text(encoding='utf-8'))
    review['checks']={k:'PASS' for k in assembly.DECK_CHECKS}; review['evidence']={k:'synthetic deck evidence' for k in assembly.DECK_CHECKS}
    review_path.write_text(json.dumps(review),encoding='utf-8')
    final=tmp_path/'outputs'/'deck.pptx'
    assert assembly.publish(state,review_path,final)['status']=='PASS'
    assert final.read_bytes()==b'S001|S002'


def test_layer_bridge_cli_binds_bundle_and_graphics_first(tmp_path,capsys):
    import layer_bridge as lb
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path); lb.register_plan(state,'S001',plan,overlay); approve_ready_plan(state,'S001')
    bundle,page=seed_current_result_and_bundle(state,tmp_path)
    assert lb.main(['bind-bundle','--state',str(state),'--slide-id','S001','--bundle',str(bundle)])==0
    assert json.loads(capsys.readouterr().out)['status']=='LAYER_BUNDLE_READY'
    _,qa=register_good_visual_qa(state,tmp_path,bundle)
    # Exercise the CLI action too with a fresh evidence file bound to the same current bundle.
    assert lb.main(['register-visual-qa','--state',str(state),'--slide-id','S001','--evidence',str(qa)])==0
    assert json.loads(capsys.readouterr().out)['status']=='LAYER_VISUAL_QA_PASS'
    assert lb.main(['bind-graphics-first','--state',str(state),'--slide-id','S001','--bundle',str(bundle),'--pptx',str(page)])==0
    assert json.loads(capsys.readouterr().out)['status']=='LAYER_GRAPHICS_FIRST_READY'


def test_explicit_provider_submit_failure_needs_retry_authorization_without_duplicate_risk(tmp_path,monkeypatch):
    import layer_bridge as lb
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path); lb.register_plan(state,'S001',plan,overlay); approve_ready_plan(state,'S001')
    monkeypatch.setenv(router.IMAGE_LAYER_API_KEY_ENV,'k')
    class Provider:
        @staticmethod
        def submit_task(*_a,**_k):
            raise ValueError('LAYER_REQUEST_FAILED: provider rejected submit')
    result=lb.submit(state,'S001',tmp_path/'work',Provider)
    assert result=={'status':'LAYER_RETRY_APPROVAL_REQUIRED','slide_id':'S001'}
    assert lb.authorize_retry(state,'S001',authorization_path=human_request(state,'S001',Provider))['status']=='RETRY_AUTHORIZED'


def test_graphics_first_requires_current_visual_qa_bound_to_bundle(tmp_path):
    import layer_bridge as lb
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path); lb.register_plan(state,'S001',plan,overlay); approve_ready_plan(state,'S001')
    bundle,page=seed_current_result_and_bundle(state,tmp_path); lb.bind_bundle(state,'S001',bundle)
    assert {k:v for k,v in lb.status(state).items() if k not in ('page_statuses','actionable_pages','automatic_resubmit')}=={'status':'LAYER_VISUAL_QA_REQUIRED','slide_id':'S001'}
    with pytest.raises(ValueError,match='LAYER_VISUAL_QA_FAILED'):
        lb.bind_graphics_first(state,'S001',page,bundle)
    manifest_sha=lb_sha(Path(bundle)/'manifest.json')
    bad=tmp_path/'qa-bad.json'; bad.write_text(json.dumps({
        'page_id':'S001','bundle_manifest_sha256':manifest_sha,
        'checks':{'layer_isolation':'PASS','background_repair':'FAIL','recomposite_fidelity':'PASS'},
        'evidence':{'layer_isolation':'checked','background_repair':'ghost remains','recomposite_fidelity':'checked'}}),encoding='utf-8')
    assert lb.register_visual_qa(state,'S001',bad)['status']=='LAYER_VISUAL_QA_FAILED'
    good=tmp_path/'qa-good.json'; good.write_text(json.dumps({
        'page_id':'S001','bundle_manifest_sha256':manifest_sha,
        'checks':{'layer_isolation':'PASS','background_repair':'PASS','recomposite_fidelity':'PASS'},
        'evidence':{'layer_isolation':'target isolated','background_repair':'background clean','recomposite_fidelity':'composite matches text-clean'}}),encoding='utf-8')
    qa=lb.register_visual_qa(state,'S001',good)
    assert qa['status']=='LAYER_VISUAL_QA_PASS'
    assert {k:v for k,v in lb.status(state).items() if k not in ('page_statuses','actionable_pages','automatic_resubmit')}=={'status':'LAYER_GRAPHICS_FIRST_REQUIRED','slide_id':'S001'}
    bound=lb.bind_graphics_first(state,'S001',page,bundle)
    assert bound['visual_qa_sha256']==lb_sha(good)
