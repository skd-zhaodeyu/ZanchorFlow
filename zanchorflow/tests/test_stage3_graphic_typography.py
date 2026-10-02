import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import runtime
import canva_bridge as bridge
from stage2_test_helpers import write_png


def _manifest(slide_id='S001', elements=None):
    return {
        'schema_version': '1.1',
        'slide_id': slide_id,
        'source_width': 1600,
        'source_height': 900,
        'text_elements': elements or [],
    }


def _inventory(slide_id='S001', items=None):
    return {'schema_version': '1.1', 'slide_id': slide_id, 'items': items or []}


def _graphic_77_element():
    return {
        'id': 'M002',
        'truth_ref': 'S001:T002',
        'truth_source': 'stage2_final_content_truth',
        'content': '77',
        'text_role': 'decorative_text',
        'representation_role': 'graphic_typography',
        'treatment': 'preserve_as_graphic',
        'visual_bbox_normalized': [0.62, 0.20, 0.34, 0.58],
        'graphic_typography_evidence': {
            'content_verified': True,
            'design_approved': True,
            'composition_critical': True,
            'native_text_substitution_material_loss': True,
        },
    }


def _graphic_77_region(treatment='preserve_as_graphic', risk='high'):
    return {
        'region_id': 'R002',
        'visual_bbox_normalized': [0.62, 0.20, 0.34, 0.58],
        'observed_text': '77',
        'detection_source': 'full_page_vision',
        'treatment': treatment,
        'linked_manifest_ids': ['M002'] if treatment != 'remove_and_drop' else [],
        'destructive_cleanup_risk': risk,
    }


def _truth():
    return {
        'slide_id': 'S001',
        'meaningful_text': [
            {'text': '庆祝中华人民共和国成立77周年'},
            {'text': '77'},
        ],
        'exact_facts': ['77'],
    }


def _ordinary_title_element():
    return {
        'id': 'M001',
        'truth_ref': 'S001:T001',
        'truth_source': 'stage2_final_content_truth',
        'content': '庆祝中华人民共和国成立77周年',
        'text_role': 'semantic_text',
        'representation_role': 'native_text',
        'treatment': 'remove_and_restore',
        'visual_bbox_normalized': [0.05, 0.25, 0.50, 0.08],
    }


def test_graphic_typography_77_is_preserved_when_all_four_evidence_conditions_hold():
    manifest = _manifest(elements=[_ordinary_title_element(), _graphic_77_element()])
    inventory = _inventory(items=[
        {'region_id':'R001','visual_bbox_normalized':[0.05,0.25,0.50,0.08],
         'observed_text':'庆祝中华人民共和国成立77周年','detection_source':'manifest_seed',
         'treatment':'remove_and_restore','linked_manifest_ids':['M001'],'destructive_cleanup_risk':'low'},
        _graphic_77_region(),
    ])
    result = runtime.validate_stage3_text_plan(manifest, inventory, _truth(), 'S001')
    assert result['status'] == 'PASS'
    assert result['preserved_graphic_typography'] == ['M002']


def test_large_or_decorative_text_alone_cannot_be_preserved():
    element = _graphic_77_element()
    element['graphic_typography_evidence']['composition_critical'] = False
    with pytest.raises(ValueError, match='GRAPHIC_TYPOGRAPHY_EVIDENCE_INCOMPLETE'):
        runtime.validate_stage3_text_plan(
            _manifest(elements=[element]), _inventory(items=[_graphic_77_region()]), _truth(), 'S001')


def test_wrong_graphic_typography_content_is_not_protected_even_if_visual_is_strong():
    element = _graphic_77_element(); element['content'] = '76'
    with pytest.raises(ValueError, match='GRAPHIC_TYPOGRAPHY_CONTENT_INVALID'):
        runtime.validate_stage3_text_plan(
            _manifest(elements=[element]), _inventory(items=[_graphic_77_region()]), _truth(), 'S001')


def test_ordinary_large_title_stays_native_remove_and_restore():
    manifest = _manifest(elements=[_ordinary_title_element()])
    inventory = _inventory(items=[{
        'region_id':'R001','visual_bbox_normalized':[0.05,0.25,0.50,0.08],
        'observed_text':'庆祝中华人民共和国成立77周年','detection_source':'manifest_seed',
        'treatment':'remove_and_restore','linked_manifest_ids':['M001'],'destructive_cleanup_risk':'low'}])
    result = runtime.validate_stage3_text_plan(manifest, inventory, _truth(), 'S001')
    assert result['status'] == 'PASS'
    assert result['preserved_graphic_typography'] == []


def test_high_risk_region_cannot_default_to_destructive_removal():
    inventory = _inventory(items=[{
        'region_id':'R9','visual_bbox_normalized':[0.55,0.15,0.4,0.6],
        'observed_text':'UNKNOWN','detection_source':'full_page_vision',
        'treatment':'remove_and_drop','linked_manifest_ids':[],
        'destructive_cleanup_risk':'high'}])
    with pytest.raises(ValueError, match='TEXT_TREATMENT_CONFLICT'):
        runtime.validate_stage3_text_plan(_manifest(), inventory, _truth(), 'S001')


def test_existing_approved_graphic_asset_exception_still_works():
    logo = {
        'id':'MLOGO','truth_ref':'brand-asset:logo-1','truth_source':'approved_graphic_asset',
        'content':'ACME','text_role':'decorative_text','representation_role':'approved_graphic_asset',
        'treatment':'preserve_as_graphic','visual_bbox_normalized':[0.9,0.02,0.08,0.04],
        'approved_graphic_evidence':{'content_verified':True,'approval_ref':'brand-asset:logo-1'},
    }
    inv = {'region_id':'RLOGO','visual_bbox_normalized':[0.9,0.02,0.08,0.04],
           'observed_text':'ACME','detection_source':'full_page_vision','treatment':'preserve_as_graphic',
           'linked_manifest_ids':['MLOGO'],'destructive_cleanup_risk':'high'}
    assert runtime.validate_stage3_text_plan(_manifest(elements=[logo]), _inventory(items=[inv]), _truth(), 'S001')['status']=='PASS'


def _ready_stage3_page(tmp_path):
    state = tmp_path/'state.json'; bridge.init(state)
    outline = tmp_path/'outline.json'
    fields = runtime.OUTLINE_FIELDS
    outline.write_text(json.dumps({'slides':[{k:k for k in fields}]},ensure_ascii=False),encoding='utf-8')
    runtime.record_stage1_draft(state, outline); runtime.present_stage1_review(state)
    runtime.handle_stage1_reply(state, '同意，按这个继续。', decision='approve')
    runtime.start_stage2_run(state)
    for kind in ('anchor','style_dna'):
        p=tmp_path/(kind+'.json');p.write_text('{}');runtime.register_stage2_artifact(state,kind,p)
    render=Path(write_png(tmp_path/'render.png'))
    cand=runtime.register_stage2_candidate(state,'S001',render,'fixture')
    runtime.review_stage2_candidate(state,cand['candidate_id'],'PASS')
    runtime.present_stage2_formal_display(state)
    runtime.seal_stage2_visual_approval(state, '确认，按这组页面进入下一阶段。')
    truth=tmp_path/'truth.json';truth.write_text(json.dumps(_truth(),ensure_ascii=False),encoding='utf-8')
    runtime.register_stage2_artifact(state,'final_content_truth:S001',truth)
    runtime.mark_stage2_text_reconciled(state,'S001')
    canvas=tmp_path/'canvas.json';canvas.write_text(json.dumps({'width':1600,'height':900}),encoding='utf-8')
    runtime.register_stage2_artifact(state,'canvas:S001',canvas)
    return state


def _write_plan(tmp_path):
    manifest=_manifest(elements=[_ordinary_title_element(),_graphic_77_element()])
    inventory=_inventory(items=[
        {'region_id':'R001','visual_bbox_normalized':[0.05,0.25,0.50,0.08],
         'observed_text':'庆祝中华人民共和国成立77周年','detection_source':'manifest_seed',
         'treatment':'remove_and_restore','linked_manifest_ids':['M001'],'destructive_cleanup_risk':'low'},
        _graphic_77_region(),
    ])
    mp=tmp_path/'manifest.json';ip=tmp_path/'inventory.json'
    mp.write_text(json.dumps(manifest,ensure_ascii=False),encoding='utf-8')
    ip.write_text(json.dumps(inventory,ensure_ascii=False),encoding='utf-8')
    return mp,ip


def test_text_clean_registration_requires_current_validated_text_plan(tmp_path):
    state=_ready_stage3_page(tmp_path)
    clean=Path(write_png(tmp_path/'clean.png'))
    with pytest.raises(ValueError, match='STAGE3_TEXT_PLAN_REQUIRED'):
        bridge.register_text_clean(state,'S001',clean)
    mp,ip=_write_plan(tmp_path)
    registered=bridge.register_text_plan(state,'S001',mp,ip)
    assert registered['status']=='TEXT_PLAN_REGISTERED'
    assert bridge.register_text_clean(state,'S001',clean)['status']=='TEXT_CLEAN_REGISTERED'


def test_replacing_text_plan_invalidates_existing_text_clean_and_attempt_state(tmp_path):
    state=_ready_stage3_page(tmp_path);mp,ip=_write_plan(tmp_path)
    bridge.register_text_plan(state,'S001',mp,ip)
    clean=Path(write_png(tmp_path/'clean.png'));bridge.register_text_clean(state,'S001',clean)
    active=bridge.begin_attempt(state,'S001')
    changed=json.loads(mp.read_text(encoding='utf-8'))
    changed['text_elements'][0]['visual_bbox_normalized']=[0.04,0.24,0.51,0.09]
    mp2=tmp_path/'manifest2.json';mp2.write_text(json.dumps(changed,ensure_ascii=False),encoding='utf-8')
    bridge.register_text_plan(state,'S001',mp2,ip)
    saved=runtime.load_runtime_state(state)
    assert 'text_clean' not in saved['slides']['S001']
    assert 'S001' not in saved.get('canva_bridge',{}).get('active',{})

def test_graphic_typography_guidance_does_not_require_graphic_integration():
    protocol = (ROOT / 'references' / '07_Stage3_文字处理_消字与复原规范_v1.5.md').read_text(encoding='utf-8')
    entry = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
    assert 'register and validate Text Manifest + Removal Inventory' in entry
    skill = protocol
    assert '空间咬合可作为证据，但不是必要条件' in protocol
    assert '独立排放的字形若其造型本身承担关键视觉表现' in protocol
    assert 'Independent placement or lack of graphic integration does not by itself disqualify `graphic_typography`.' in skill
