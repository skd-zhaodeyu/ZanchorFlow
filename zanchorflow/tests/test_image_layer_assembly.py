import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from pptx import Presentation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import runtime
import reconstruction_router as router
import layer_bridge as lb
import layer_package
import layer_build_pptx
from test_reconstruction_backend_router import ready_state


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare_image_page(state, tmp_path, sid):
    saved=runtime.load_runtime_state(state); clean=Path(saved['slides'][sid]['text_clean'])
    plan = tmp_path / f'{sid}-plan.json'
    plan.write_text(json.dumps({
        'schema_version': 1, 'page_id': sid, 'max_foregrounds': 6,
        'recommended_total_layers': 2,
        'targets': [{'id': 'a', 'label': 'A', 'bbox': [100,100,500,500],
                     'edit_action': 'move', 'selection_reason': 'fixture'}],
        'deferred': []}), encoding='utf-8')
    overlay = tmp_path / f'{sid}-overlay.png'
    Image.new('RGB', (1600,900), 'white').save(overlay)
    lb.register_plan(state, sid, plan, overlay); lb.approve_plan(state, sid)
    saved = runtime.load_runtime_state(state); plan_rec = saved['layer_bridge']['plans'][sid]

    result_dir = tmp_path / f'{sid}-result'; raw = result_dir / 'raw'; raw.mkdir(parents=True)
    bg = Image.new('RGBA',(800,450),(255,255,255,255)); bg.save(raw/'bg.png')
    fg = Image.new('RGBA',(800,450),(0,0,0,0)); ImageDraw.Draw(fg).rectangle((50,50,249,249),fill=(255,0,0,255)); fg.save(raw/'fg.png')
    result = {
        'schema_version':1, 'page_id':sid, 'provider_id':'360_reveal_layer', 'model_id':'reveal_layer',
        'request_id':f'task-{sid}', 'backend_canvas':[800,450],
        'image_boxes':[[100,100,500,500]], 'resized_image_boxes':[[50,50,250,250]], 'boxes_mapping_index':[0],
        'layers':[{'type':'background','file':'raw/bg.png'}, {'type':'foreground','target_id':'a','file':'raw/fg.png'}]
    }
    rp = result_dir/'backend-result.json'; rp.write_text(json.dumps(result),encoding='utf-8')
    rec = {'status':'LAYER_RESULT_BOUND','slide_id':sid,'run_id':plan_rec['run_id'],'plan_sha256':plan_rec['plan_sha256'],
           'text_clean_sha256':plan_rec['text_clean_sha256'],'task_id':f'task-{sid}','path':str(rp),'sha256':sha(rp),'usage':{}}
    with router.transaction(state) as temp:
        cur=runtime.load_runtime_state(temp); cur.setdefault('layer_bridge',{}).setdefault('results',{})[sid]=rec; runtime._save_runtime_state(temp,cur)

    bundle = tmp_path/f'{sid}-bundle'; layer_package.package_layers(clean, plan, rp, bundle, schema_version=2)
    graphics = tmp_path/f'{sid}-graphics.pptx'; layer_build_pptx.build_page_pptx(bundle, graphics)
    lb.bind_bundle(state,sid,bundle)
    visual_qa=tmp_path/f'{sid}-visual-qa.json'; visual_qa.write_text(json.dumps({
        'page_id':sid,'bundle_manifest_sha256':sha(bundle/'manifest.json'),
        'checks':{'layer_isolation':'PASS','background_repair':'PASS','recomposite_fidelity':'PASS'},
        'evidence':{'layer_isolation':'synthetic isolation evidence','background_repair':'synthetic background evidence','recomposite_fidelity':'synthetic recomposite evidence'}
    }),encoding='utf-8')
    lb.register_visual_qa(state,sid,visual_qa); lb.bind_graphics_first(state,sid,graphics,bundle)

    for kind, obj in (
        ('canvas', {'width':1600,'height':900}),
        ('finalized_manifest', {'schema_version':1,'entries':[]}),
        ('font_fallback', {}),
    ):
        p=tmp_path/f'{sid}-{kind}.json'; p.write_text(json.dumps(obj),encoding='utf-8')
        runtime.register_stage2_artifact(state,f'{kind}:{sid}',p)

    restored=tmp_path/f'{sid}-restored.pptx'; shutil.copyfile(graphics,restored)
    # Make restored bytes/path distinct without altering the Graphics-first source.
    prs=Presentation(restored); prs.core_properties.comments='restored'; prs.save(restored)
    current=runtime.load_runtime_state(state); lineage=runtime.expected_lineage_from_state(current,sid)
    review={
        'backend':'image_layer','slide_id':sid,
        'graphics_first_sha256':sha(graphics), 'restored_pptx_sha256':sha(restored),
        'text_restore_fingerprint':lineage['text_restore_fingerprint'],
        'checks':{k:'PASS' for k in runtime.GATE_NAMES},
        'evidence':{k:'synthetic independent evidence' for k in runtime.GATE_NAMES},
    }
    review_path=tmp_path/f'{sid}-review.json'; review_path.write_text(json.dumps(review),encoding='utf-8')
    return graphics, restored, review_path


def image_deck(tmp_path):
    state=ready_state(tmp_path,2)
    for sid in ('S001','S002'):
        clean=tmp_path/f'{sid}-clean-valid.png'; Image.new('RGB',(1600,900),'white').save(clean)
        runtime.register_stage2_artifact(state,f'text_clean:{sid}',clean)
    router.choose_backend(state,'image_layer')
    pages={}
    for sid in ('S001','S002'):
        pages[sid]=prepare_image_page(state,tmp_path,sid)
    return state,pages


def test_image_seal_and_router_page_provenance_are_current(tmp_path):
    state,pages=image_deck(tmp_path)
    for sid in ('S001','S002'):
        result=lb.seal_page(state,sid,pages[sid][1],pages[sid][2])
        assert result['status']=='PAGE_SEALED'
        saved=runtime.load_runtime_state(state)
        provenance=router.page_provenance(saved,sid)
        assert provenance['backend']=='image_layer'
        assert provenance['slide_id']==sid
        assert provenance['graphics_first_sha256']==sha(pages[sid][0])
        assert provenance['visual_qa_sha256']==saved['layer_bridge']['graphics_first'][sid]['visual_qa_sha256']
        assert provenance['validated_pptx_sha256']==sha(pages[sid][1])
        assert 'attempt_id' not in provenance and 'design_id' not in provenance


def test_image_seal_rejects_restored_graphics_source_and_wrong_fingerprint(tmp_path):
    state,pages=image_deck(tmp_path); graphics,restored,review_path=pages['S001']
    data=json.loads(review_path.read_text()); data['restored_pptx_sha256']=sha(graphics)
    same=tmp_path/'same-review.json'; same.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='separate path'):
        lb.seal_page(state,'S001',graphics,same)
    data=json.loads(review_path.read_text()); data['text_restore_fingerprint']='wrong'; review_path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='restoration inputs changed'):
        lb.seal_page(state,'S001',restored,review_path)


def test_router_magic_provenance_delegates_without_changing_shape(monkeypatch):
    import canva_bridge
    state={'stage2_run':{'run_id':'r','approved_outline_fingerprint':'o','page_order':['S001']},
           'reconstruction_backend':{'schema_version':1,'backend':'magic_layer','run_id':'r','approved_outline_fingerprint':'o','page_order':['S001']}}
    state['reconstruction_backend']['selection_fingerprint']=router._fingerprint(router._selection_payload(state))
    expected={'identity':{'attempt_id':'a'},'download_sha256':'d','seal':{'slide_id':'S001'}}
    monkeypatch.setattr(canva_bridge,'page_provenance',lambda s,sid:copy.deepcopy(expected))
    assert router.page_provenance(state,'S001')==expected


def test_image_assembly_stores_merged_provenance_under_layer_bridge(tmp_path,monkeypatch):
    import assemble_deck as assembly
    state,pages=image_deck(tmp_path)
    for sid in ('S001','S002'): lb.seal_page(state,sid,pages[sid][1],pages[sid][2])
    monkeypatch.setattr(assembly.preflight,'check',lambda *_a,**_k:{'blockers':[]})
    def fake_merge(inputs,order,target,state_path):
        target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes('|'.join(order).encode())
        runtime.seal_merged_deck(state_path,order,inputs,target)
        return {'status':'PASS','path':str(target),'deck_order':order}
    monkeypatch.setattr(assembly,'merge',fake_merge)
    result=assembly.prepare(state,tmp_path/'work')
    assert result['status']=='AWAITING_DECK_VALIDATION'
    assert lb.status(state)['status']=='DECK_VALIDATION'
    saved=runtime.load_runtime_state(state)
    assert saved['layer_bridge']['merged']['pages']==router.deck_provenance(saved,['S001','S002'])
    assert 'merged' not in saved.get('canva_bridge',{})
    review=json.loads(Path(result['validation_report']).read_text())
    assert all(p['backend']=='image_layer' for p in review['page_provenance'])


def test_image_status_restores_and_seals_each_page_before_advancing(tmp_path):
    state=ready_state(tmp_path,2)
    for sid in ('S001','S002'):
        clean=tmp_path/f'{sid}-clean-valid.png'; Image.new('RGB',(1600,900),'white').save(clean)
        runtime.register_stage2_artifact(state,f'text_clean:{sid}',clean)
    router.choose_backend(state,'image_layer')
    s1=prepare_image_page(state,tmp_path,'S001')
    assert lb.status(state)=={'status':'RESTORE_TEXT','slide_id':'S001'}
    lb.seal_page(state,'S001',s1[1],s1[2])
    assert lb.status(state)=={'status':'LAYER_PLAN_REQUIRED','slide_id':'S002'}
    s2=prepare_image_page(state,tmp_path,'S002')
    assert lb.status(state)=={'status':'RESTORE_TEXT','slide_id':'S002'}
    lb.seal_page(state,'S002',s2[1],s2[2])
    assert lb.status(state)=={'status':'PREPARE_DECK','deck_order':['S001','S002']}
