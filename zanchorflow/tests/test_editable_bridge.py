import sys,json,copy
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import runtime as rt
import reconstruction_router as router
from test_reconstruction_backend_router import ready_state
import editable_bridge as eb

def source(tmp_path):
 state=ready_state(tmp_path,0);eb.enable(state);return state

def plan():
 return {'schema_version':1,'source_size_px':[1,1],'slide_size_emu':[6858000,6858000],'objects':[{'id':'text','type':'text','box_px':[0,0,1,1],'text':'x','occurrence_ids':['S001:T001']} ]}

def test_early_choice_without_clean(tmp_path):
 state=source(tmp_path);router.choose_backend(state,'editable_path')
 assert router.status(state)['status']=='EDITABLE_PLAN_REQUIRED'
 assert rt.resume_stage({'slide_id':'S001'},state)=='stage3_editable_path'
 assert 'text_clean' not in rt.load_runtime_state(state)['slides']['S001']

def test_plan_source_and_truth_bound(tmp_path):
 state=source(tmp_path);router.choose_backend(state,'editable_path');path=tmp_path/'plan.json';path.write_text(json.dumps(plan()))
 eb.register_plan(state,'S001',path);output=tmp_path/'built.pptx';eb.build_page(state,'S001',output)
 assert eb.status(state)['status']=='EDITABLE_REVIEW_REQUIRED'
 data=json.loads(path.read_text());data['objects'][0]['text']='wrong';bad=tmp_path/'bad.json';bad.write_text(json.dumps(data))
 with pytest.raises(ValueError,match='TRUTH'):eb.register_plan(state,'S001',bad)
 assert eb.status(state)['status']=='EDITABLE_REVIEW_REQUIRED'

def test_seal_requires_actual_evidence_and_current_bytes(tmp_path):
 state=source(tmp_path);router.choose_backend(state,'editable_path');path=tmp_path/'plan.json';path.write_text(json.dumps(plan()));eb.register_plan(state,'S001',path);eb.build_page(state,'S001',tmp_path/'built.pptx')
 review=tmp_path/'review.json';review.write_text(json.dumps({'checks':{k:'PASS' for k in rt.GATE_NAMES}}))
 with pytest.raises(ValueError):eb.seal_page(state,'S001',review)

def test_frozen_plan_tamper_is_not_reused(tmp_path):
 state=source(tmp_path);router.choose_backend(state,'editable_path');path=tmp_path/'plan.json';path.write_text(json.dumps(plan()));result=eb.register_plan(state,'S001',path)
 Path(result['path']).write_bytes(b'tampered')
 with pytest.raises(ValueError):eb.build_page(state,'S001',tmp_path/'out.pptx')
 assert not (tmp_path/'out.pptx').exists()


def test_early_image_choice_is_idempotent_before_cleanup(tmp_path):
 state=source(tmp_path)
 first=router.choose_backend(state,'image_layer')
 assert router.choose_backend(state,'image_layer')==first

def test_editable_resume_ignores_legacy_cleanup_flags(tmp_path):
 state=source(tmp_path);router.choose_backend(state,'editable_path')
 assert rt.resume_stage({'slide_id':'S001','text_clean':True},state)=='stage3_editable_path'

def test_modified_gate_evidence_invalidates_seal(tmp_path):
 state=source(tmp_path);router.choose_backend(state,'editable_path');path=tmp_path/'plan.json';path.write_text(json.dumps(plan()));eb.register_plan(state,'S001',path);eb.build_page(state,'S001',tmp_path/'built.pptx')
 data=rt.load_runtime_state(state);built=data['editable_bridge']['built']['S001'];e=tmp_path/'evidence.txt';e.write_text('offline fixture, not model or Office validation')
 review={'pptx_sha256':built['sha256'],'lineage':eb.expected_lineage(data,'S001'),'checks':{k:'PASS' for k in rt.GATE_NAMES},'evidence':{k:{'finding':'OFFLINE provenance fixture only','file':str(e),'sha256':eb.sha(e.read_bytes())} for k in rt.GATE_NAMES}}
 rp=tmp_path/'review.json';rp.write_text(json.dumps(review));eb.seal_page(state,'S001',rp)
 assert eb.page_provenance(rt.load_runtime_state(state),'S001')['backend']=='editable_path'
 e.write_text('changed')
 with pytest.raises(ValueError,match='EVIDENCE'):eb.page_provenance(rt.load_runtime_state(state),'S001')


def test_protected_graphic_text_needs_verified_preservation(tmp_path):
 p=plan();p['objects'][0].update(type='image',semantic_text='x',representation_role='graphic_typography');del p['objects'][0]['text']
 truth={'slide_id':'S001','meaningful_text':['x']}
 with pytest.raises(ValueError,match='PROTECTED'):eb.validate_truth(p,truth,'S001')
 p['objects'][0]['preservation_evidence']={k:True for k in ('content_verified','source_verified','substitution_material_loss','design_approved','composition_critical','native_text_substitution_material_loss')}
 eb.validate_truth(p,truth,'S001')

def test_unknown_protected_text_cannot_satisfy_truth(tmp_path):
 p=plan();p['objects'][0]['text']='?'
 with pytest.raises(ValueError,match='TRUTH'):eb.validate_truth(p,{'slide_id':'S001','meaningful_text':['x']},'S001')


def test_sealed_pages_enter_shared_assembly_without_cleanup(tmp_path):
 import canva_bridge
 state=source(tmp_path);router.choose_backend(state,'editable_path')
 for sid in ('S001','S002'):
  data=plan();data['objects'][0]['occurrence_ids']=[sid+':T001'];path=tmp_path/(sid+'-plan.json');path.write_text(json.dumps(data));eb.register_plan(state,sid,path);eb.build_page(state,sid,tmp_path/(sid+'.pptx'))
  now=rt.load_runtime_state(state);built=now['editable_bridge']['built'][sid];e=tmp_path/(sid+'-offline-evidence.txt');e.write_text('OFFLINE contract fixture; not actual model/Office validation')
  review={'pptx_sha256':built['sha256'],'lineage':eb.expected_lineage(now,sid),'checks':{k:'PASS' for k in rt.GATE_NAMES},'evidence':{k:{'finding':'OFFLINE contract fixture','file':str(e),'sha256':eb.sha(e.read_bytes())} for k in rt.GATE_NAMES}}
  rp=tmp_path/(sid+'-review.json');rp.write_text(json.dumps(review));eb.seal_page(state,sid,rp)
 assert canva_bridge.status(state)['status']=='PREPARE_DECK'
 assert router.status(state)['status']=='PREPARE_DECK'
 assert all('text_clean' not in v for v in rt.load_runtime_state(state)['slides'].values())
 eb.build_page(state,'S001',tmp_path/'rebuilt-S001.pptx')
 current=rt.load_runtime_state(state)
 assert 'validated_single_page' not in current['slides']['S001']
 assert current['slides']['S001']['superseded_validated_single_pages']
 assert eb.status(state)['status']=='EDITABLE_REVIEW_REQUIRED'

def test_revoked_visual_approval_invalidates_frozen_plan(tmp_path):
 state=source(tmp_path);router.choose_backend(state,'editable_path');path=tmp_path/'plan.json';path.write_text(json.dumps(plan()));eb.register_plan(state,'S001',path)
 now=rt.load_runtime_state(state);now['stage2_run']['visual_approval']=None;rt._save_runtime_state(state,now)
 with pytest.raises(ValueError,match='SOURCE_STALE'):eb.current_plan(rt.load_runtime_state(state),'S001')

def test_uniform_heading_cannot_be_changed_to_graphic(tmp_path):
 from test_title_policy import seeded,plan as legacy_plan
 state,ref=seeded(tmp_path);legacy_plan(state,tmp_path,'S002',ref);now=rt.load_runtime_state(state);p=plan();p['objects'][0].update(text='fixture heading',occurrence_ids=['S002:T001'])
 with pytest.raises(ValueError,match='TITLE'):eb.validate_title(now,'S002',p)
 p.update(title_contract_ref=ref,title_element_ids=['text']);eb.validate_title(now,'S002',p)
 p['objects'][0]['type']='image'
 with pytest.raises(ValueError,match='TITLE_PRIMARY_NATIVE'):eb.validate_title(now,'S002',p)
