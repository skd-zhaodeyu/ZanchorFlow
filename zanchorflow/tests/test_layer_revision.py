"""Offline behavioral regression: no real providers, keys or paid calls."""
import json,sys,random,copy
from pathlib import Path
import pytest
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import layer_geometry as geom,layer_geometry_verify as gv,layer_package as lp,layer_validate_bundle as lv
import layer_policy as policy,layer_bridge as lb,runtime,reconstruction_router as router
from test_layer_bridge import image_state,write_plan,approve_ready_plan,seed_current_result_and_bundle,lb_sha

def write(path,data): path.write_text(json.dumps(data),encoding='utf-8'); return path

def pattern(path,size=(512,384)):
    im=Image.new('RGB',size,'white'); d=ImageDraw.Draw(im); rng=random.Random(17)
    for i in range(120):
        x=rng.randrange(20,size[0]-45); y=rng.randrange(20,size[1]-45)
        d.ellipse((x,y,x+rng.randrange(4,30),y+rng.randrange(4,30)),fill=tuple(rng.randrange(180) for _ in range(3)))
    im.save(path); return im

def fixture(tmp_path,box=(60,55,170,140)):
    src=tmp_path/'source.png'; im=pattern(src); im.save(tmp_path/'resized.png'); im.convert('RGBA').save(tmp_path/'bg.png')
    fg=Image.new('RGBA',im.size); ImageDraw.Draw(fg).rectangle((70,65,159,129),fill=(180,20,30,230)); fg.save(tmp_path/'fg.png')
    plan=write(tmp_path/'plan.json',{'page_id':'S001','targets':[{'id':'a','bbox':[60,55,170,140]}],'recommended_total_layers':2})
    result=write(tmp_path/'result.json',{'backend_canvas':list(im.size),'resized_image':'resized.png','request_id':'one',
       'image_boxes':[[60,55,170,140]],'resized_image_boxes':[list(box)],'boxes_mapping_index':[0],
       'layers':[{'type':'background','file':'bg.png'},{'type':'foreground','target_id':'a','file':'fg.png'}]})
    return src,plan,result

def test_v3_returned_box_never_changes_crop_or_placement(tmp_path):
    src,plan,result=fixture(tmp_path)
    first=lp.package_layers(src,plan,result,tmp_path/'first')
    r=json.loads(result.read_text()); r['resized_image_boxes']=[[48,48,192,160]]; write(result,r)
    second=lp.package_layers(src,plan,result,tmp_path/'second')
    assert first['schema_version']==3
    assert first['layers']==second['layers']
    assert first['layers'][1]['backend_bbox']==[70,65,90,65]
    assert first['layers'][1]['canonical_bbox_normalized']==pytest.approx([70/512,65/384,90/512,65/384])
    assert len(first['layers'])==2 and (tmp_path/'first/geometry/evidence.json').is_file()
    lv.validate_bundle(tmp_path/'first'); lv.validate_bundle(tmp_path/'second')

def test_v3_evidence_tamper_and_unknown_schema_rejected(tmp_path):
    src,plan,result=fixture(tmp_path); bundle=tmp_path/'bundle'; manifest=lp.package_layers(src,plan,result,bundle)
    proof=bundle/'geometry/evidence.json'; proof.write_text('{}')
    with pytest.raises(ValueError,match='geometry evidence'): lv.validate_bundle(bundle)
    manifest['schema_version']=44; write(bundle/'manifest.json',manifest)
    with pytest.raises(ValueError,match='schema'): lv.validate_bundle(bundle)

def test_identity_and_paths_remain_blocking(tmp_path):
    src,plan,result=fixture(tmp_path); data=json.loads(result.read_text()); data['boxes_mapping_index']=[1]; write(result,data)
    with pytest.raises(ValueError,match='mapping indices'): lp.package_layers(src,plan,result,tmp_path/'bad')
    data['boxes_mapping_index']=[0]; data['resized_image']='../outside.png'; write(result,data)
    with pytest.raises(ValueError,match='escapes'): lp.package_layers(src,plan,result,tmp_path/'bad')

def test_declared_candidate_passes_but_shift_never_refits(tmp_path):
    src=tmp_path/'source.png'; im=pattern(src); resized=tmp_path/'resized.png'; im.save(resized)
    candidate=geom.full_canvas_transform(im.size,im.size); before=copy.deepcopy(candidate)
    assert gv.verify(src,resized,candidate)['result']=='VERIFIED'
    shifted=Image.new('RGB',im.size,'white'); shifted.paste(im,(5,4)); shifted.save(resized)
    report=gv.verify(src,resized,candidate)
    assert report['result']=='CONTRADICTED'; assert candidate==before
    with pytest.raises(ValueError,match='MAPPING_UNRESOLVED'): gv.create_transform(src,resized)

@pytest.mark.parametrize('kind',['blank','repeat'])
def test_blank_and_ambiguous_texture_cannot_prove_mapping(tmp_path,kind):
    im=Image.new('RGB',(512,384),'white')
    if kind=='repeat':
        d=ImageDraw.Draw(im)
        for x in range(0,512,8): d.line((x,0,x,384),fill='black')
        for y in range(0,384,8): d.line((0,y,512,y),fill='black')
    src=tmp_path/'source.png'; resized=tmp_path/'resized.png'; im.save(src); im.save(resized)
    assert gv.verify(src,resized,geom.full_canvas_transform(im.size,im.size))['result']=='INSUFFICIENT'

def test_known_padding_is_verified_without_using_returned_boxes(tmp_path):
    src=tmp_path/'source.png'; im=pattern(src); backend=Image.new('RGB',(552,424),'white'); backend.paste(im,(20,20))
    resized=tmp_path/'resized.png'; backend.save(resized)
    transform,report=gv.create_transform(src,resized,[20,20,512,384])
    assert report['result']=='VERIFIED' and transform['tx']==20 and transform['ty']==20
    assert gv.verify(src,resized,geom.full_canvas_transform(im.size,backend.size))['result']!='VERIFIED'

def limitation(tmp_path):
    p=tmp_path/'evidence.png'; Image.new('RGB',(10,10),'red').save(p)
    return {'limitation_id':'L1','category':'foreground_edge_artifact','affected_target_ids':['a'],
        'description':'Small halo','editing_impact':'Object remains movable and removable','visual_impact':'Slightly visible',
        'evidence':[{'file':str(p),'sha256':lb_sha(p)}]}

def report(tmp_path,bundle):
    lim=limitation(tmp_path)
    return {'page_id':'S001','bundle_manifest_sha256':lb_sha(bundle/'manifest.json'),
        'checks':{'layer_isolation':'MODEL_LIMITATION','background_repair':'PASS','recomposite_fidelity':'MODEL_LIMITATION'},
        'evidence':{k:'Inspected isolated layer, composite and moved object' for k in policy.CHECKS},
        'limitations':[lim],'check_limitations':{'layer_isolation':['L1'],'recomposite_fidelity':['L1']}}

def test_limitations_continue_binding_and_tampered_evidence_invalidates(tmp_path):
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path); lb.register_plan(state,'S001',plan,overlay); approve_ready_plan(state,'S001')
    bundle,page=seed_current_result_and_bundle(state,tmp_path); lb.bind_bundle(state,'S001',bundle)
    data=report(tmp_path,bundle); qa=write(tmp_path/'qa.json',data)
    assert lb.register_visual_qa(state,'S001',qa)['status']=='LAYER_VISUAL_QA_ACCEPTED_WITH_LIMITATIONS'
    assert lb.bind_graphics_first(state,'S001',page,bundle)['status']=='LAYER_GRAPHICS_FIRST_READY'
    saved=runtime.load_runtime_state(state); assert saved['layer_bridge']['graphics_first']['S001']['accepted_limitations']==data['limitations']
    Path(data['limitations'][0]['evidence'][0]['file']).write_bytes(b'tampered')
    assert lb.graphics_first_current(runtime.load_runtime_state(state),'S001') is None

@pytest.mark.parametrize('category',policy.NON_EXEMPT+policy.SEVERE+policy.EXCLUSIONS)
def test_non_exempt_errors_cannot_be_accepted_limitations(tmp_path,category):
    data={'checks':{k:'MODEL_LIMITATION' for k in policy.CHECKS},'evidence':{k:'evidence' for k in policy.CHECKS},'limitations':[limitation(tmp_path)],'check_limitations':{k:['L1'] for k in policy.CHECKS}}
    data['limitations'][0]['category']=category
    with pytest.raises(ValueError,match='cannot be a limitation'): policy.validate_qa(data,{'a'},tmp_path)

def test_deck_context_uses_page_and_limitation_identity(tmp_path):
    lim=limitation(tmp_path); expected=[dict(lim,page_id='S001'),dict(lim,page_id='S002')]
    one={'page_id':'S001','limitation_id':'L1','reason':'Same category, target, evidence and extent','unchanged_extent':True,'claimed_capability_preserved':True}
    review={'accepted_limitations':expected,'limitation_matches':[one]}
    with pytest.raises(ValueError,match='all accepted'): policy.validate_context(review,expected)
    review['limitation_matches'].append(dict(one,page_id='S002')); policy.validate_context(review,expected)
    review['limitation_matches'][1]['unchanged_extent']=False
    with pytest.raises(ValueError,match='reclassify'): policy.validate_context(review,expected)

class Provider:
    PROVIDER_ID='offline_stub'; MODEL='mock'; VERSION='v1'; calls=0; fail=False
    @classmethod
    def submit_task(cls,*args):
        cls.calls+=1
        if cls.fail: raise OSError('uncertain transport')
        return {'task_id':'task-'+str(cls.calls)}
    @staticmethod
    def query_task(task,key): return {'task_id':task,'normalized_status':'DONE'}
    @staticmethod
    def normalize_done_result(response,plan,out):
        out.mkdir(parents=True,exist_ok=True); return write(out/'backend-result.json',{'task_id':response['task_id'],'page_id':plan['page_id']})

def completed(tmp_path,monkeypatch):
    Provider.calls=0; Provider.fail=False
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path); lb.register_plan(state,'S001',plan,overlay); approve_ready_plan(state,'S001')
    monkeypatch.setenv(router.IMAGE_LAYER_API_KEY_ENV,'offline-test-key')
    lb.submit(state,'S001',tmp_path/'work',Provider); lb.query(state,'S001',tmp_path/'work',Provider)
    saved=runtime.load_runtime_state(state); p=saved['layer_bridge']['plans']['S001']; r=saved['layer_bridge']['results']['S001']
    ep=tmp_path/'serious.png'; Image.new('RGB',(12,12),'black').save(ep)
    proof={'page_id':'S001','text_clean_sha256':p['text_clean_sha256'],'plan_sha256':p['plan_sha256'],'result_sha256':r['sha256'],
        'task_id':r['task_id'],'classification':'SEVERE','category':'blank_or_unrecognizable',
        'excluded_errors':{k:'PASS' for k in policy.EXCLUSIONS},'evidence':[{'file':str(ep),'sha256':lb_sha(ep)}]}
    auth={'authorized':True,'remaining_image_calls':1,'authorization_evidence':'Explicit offline fixture authorization',
        'text_clean_sha256':p['text_clean_sha256'],'plan_sha256':p['plan_sha256'],'provider':Provider.PROVIDER_ID,'model':Provider.MODEL}
    auth.update(source='user',user_requested_relayer=True,user_message_id='synthetic-user-retry',user_message='Synthetic fixture asks to re-layer once',authorization_id='fixture-manual-1',page_id='S001',run_id=p['run_id'],provider_identity=lb._provider_identity(Provider))
    return state,write(tmp_path/'severe.json',proof),write(tmp_path/'authorization.json',auth),r

def test_quality_retry_once_keeps_two_results_and_closes_forever(tmp_path,monkeypatch):
    state,proof,auth,original=completed(tmp_path,monkeypatch); original_bytes=Path(original['path']).read_bytes()
    lb.authorize_quality_retry(state,'S001',proof,auth); lb.submit(state,'S001',tmp_path/'work',Provider)
    saved=runtime.load_runtime_state(state); assert next(iter(saved['layer_bridge']['quality_retries'].values()))['quality_retry_count']==1
    assert saved['layer_bridge']['requests']['S001']['retry_reason']=='severe_quality_failure'
    lb.query(state,'S001',tmp_path/'work',Provider); second=runtime.load_runtime_state(state)['layer_bridge']['results']['S001']
    assert second['path']!=original['path'] and Path(original['path']).read_bytes()==original_bytes
    assert lb.submit(state,'S001',tmp_path/'work',Provider)['status']=='LAYER_RESULT_BOUND'; assert Provider.calls==2
    with pytest.raises(ValueError,match='EXHAUSTED'): lb.authorize_quality_retry(state,'S001',proof,auth)

def test_uncertain_quality_submit_consumes_budget_and_cannot_technical_resubmit(tmp_path,monkeypatch):
    state,proof,auth,original=completed(tmp_path,monkeypatch); lb.authorize_quality_retry(state,'S001',proof,auth); Provider.fail=True
    assert lb.submit(state,'S001',tmp_path/'work',Provider)['status']=='LAYER_REQUEST_UNCERTAIN'
    with pytest.raises(ValueError,match='EXHAUSTED'): lb.authorize_retry(state,'S001',accept_duplicate_charge_risk=True)
    assert Provider.calls==2 and Path(original['path']).is_file()
    assert next(iter(runtime.load_runtime_state(state)['layer_bridge']['quality_retries'].values()))['quality_retry_count']==1

@pytest.mark.parametrize('change',['ordinary','technical','unpaid','provider','evidence'])
def test_quality_retry_rejects_ineligible_or_changed_inputs(tmp_path,monkeypatch,change):
    state,proof,auth,original=completed(tmp_path,monkeypatch)
    if change in ('ordinary','technical'):
        data=json.loads(proof.read_text()); data['category']='foreground_edge_artifact' if change=='ordinary' else data['category']
        if change=='technical': data['excluded_errors']['geometry']='FAIL'
        write(proof,data)
    if change=='unpaid': data=json.loads(auth.read_text()); data['remaining_image_calls']=0; write(auth,data)
    if change in ('ordinary','technical','unpaid'):
        with pytest.raises(ValueError): lb.authorize_quality_retry(state,'S001',proof,auth)
    else:
        lb.authorize_quality_retry(state,'S001',proof,auth)
        if change=='provider': monkeypatch.setattr(Provider,'VERSION','different')
        else: Path(json.loads(proof.read_text())['evidence'][0]['file']).write_bytes(b'changed')
        with pytest.raises(ValueError): lb.submit(state,'S001',tmp_path/'work',Provider)
    assert Provider.calls==1

def test_readiness_missing_blocks_paid_submit_without_new_user_gate(tmp_path,monkeypatch):
    state=image_state(tmp_path); plan,overlay=write_plan(tmp_path); lb.register_plan(state,'S001',plan,overlay); lb.approve_plan(state,'S001')
    monkeypatch.setenv(router.IMAGE_LAYER_API_KEY_ENV,'offline'); Provider.calls=0
    with pytest.raises(ValueError,match='READINESS'): lb.submit(state,'S001',tmp_path/'work',Provider)
    assert Provider.calls==0

def test_numpy_is_conditional_geometry_dependency(tmp_path,monkeypatch):
    monkeypatch.setitem(sys.modules,'numpy',None)
    with pytest.raises(ValueError,match='GEOMETRY_DEPENDENCY_MISSING'): gv.dependencies()
    # Legacy geometry remains available and does not import NumPy.
    assert geom.full_canvas_transform((1600,900),(800,450))['sx']==0.5


def test_same_plan_registration_cannot_erase_consumed_retry(tmp_path,monkeypatch):
    state,proof,auth,original=completed(tmp_path,monkeypatch)
    lb.authorize_quality_retry(state,'S001',proof,auth); lb.submit(state,'S001',tmp_path/'work',Provider); lb.query(state,'S001',tmp_path/'work',Provider)
    lb.register_plan(state,'S001',tmp_path/'S001-plan.json',tmp_path/'S001-boxes.png')
    assert lb.submit(state,'S001',tmp_path/'work',Provider)['status']=='LAYER_RESULT_BOUND'
    assert Provider.calls==2

def test_geometry_failure_persists_local_diagnostic_not_a_bundle(tmp_path):
    src,plan,result=fixture(tmp_path); Image.new('RGB',(512,384),'white').save(tmp_path/'resized.png')
    with pytest.raises(ValueError,match='MAPPING_UNRESOLVED'): lp.package_layers(src,plan,result,tmp_path/'bad')
    assert (tmp_path/'bad/geometry-diagnostic.json').is_file()
    assert not (tmp_path/'bad/manifest.json').exists()

def test_preflight_missing_numpy_does_not_block_magic_or_package(tmp_path,monkeypatch):
    import preflight
    real=preflight.importlib.util.find_spec
    monkeypatch.setattr(preflight.importlib.util,'find_spec',lambda name: None if name=='numpy' else real(name))
    root=Path(__file__).resolve().parents[1]
    image=preflight.check(root,tmp_path/'image',scope='image_layer')
    assert any(x['code']=='IMAGE_LAYER_GEOMETRY_DEPENDENCY_MISSING' for x in image['blockers'])
    normal=preflight.check(root,tmp_path/'normal',scope='package')
    assert not any(x['code']=='IMAGE_LAYER_GEOMETRY_DEPENDENCY_MISSING' for x in normal['blockers'])
    assert 'numpy' not in normal['runtime_dependencies']

def test_limitations_survive_text_restore_seal_merge_and_delivery(tmp_path,monkeypatch):
    import assemble_deck as assembly
    from test_layer_bridge import _seed_image_restoration_inputs
    state=image_state(tmp_path)
    for sid in ('S001','S002'):
        sub=tmp_path/sid; sub.mkdir(); restored,review_path=_seed_image_restoration_inputs(state,sub,sid)
        data=report(sub,sub/'bundle'); data['page_id']=sid; qa=write(sub/'limitations.json',data)
        lb.register_visual_qa(state,sid,qa); lb.bind_graphics_first(state,sid,sub/'graphics.pptx',sub/'bundle')
        review=json.loads(review_path.read_text()); review['accepted_limitations']=data['limitations']
        review['limitation_matches']=[{'limitation_id':'L1','reason':'Same target and hashed evidence, extent unchanged, whole-object editing preserved',
            'unchanged_extent':True,'claimed_capability_preserved':True}]
        write(review_path,review); lb.seal_page(state,sid,restored,review_path)
        assert router.page_provenance(runtime.load_runtime_state(state),sid)['accepted_limitations']==data['limitations']
    monkeypatch.setattr(assembly.preflight,'check',lambda *a,**k:{'blockers':[], 'office_host':'powerpoint'})
    def merge(inputs,order,target,state_path, *, office_host='auto'):
        target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(b'offline-native-merge-contract')
        runtime.seal_merged_deck(state_path,order,inputs,target); return {'status':'PASS'}
    monkeypatch.setattr(assembly,'merge',merge)
    prepared=assembly.prepare(state,tmp_path/'work'); path=Path(prepared['validation_report']); review=json.loads(path.read_text())
    assert {x['page_id'] for x in review['accepted_limitations']}=={'S001','S002'}
    review['checks']={k:'PASS' for k in assembly.DECK_CHECKS}; review['evidence']={k:'Offline contract reviewed' for k in assembly.DECK_CHECKS}
    review['limitation_matches']=[{'page_id':sid,'limitation_id':'L1','reason':'Unchanged evidence, target, extent and editing capability',
        'unchanged_extent':True,'claimed_capability_preserved':True} for sid in ('S001','S002')]
    write(path,review); result=assembly.publish(state,path,tmp_path/'outputs/deck.pptx')
    assert len(result['accepted_limitations'])==2 and result['status']=='PASS'
