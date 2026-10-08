import copy,hashlib,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import runtime,canva_bridge as bridge
from test_stage3_graphic_typography import (_manifest,_inventory,_truth,_graphic_77_element,
    _graphic_77_region,_ordinary_title_element,_ready_stage3_page)
from stage2_test_helpers import write_png

def asset():
    return {'id':'ART','truth_source':'approved_graphic_asset','truth_ref':'design:object',
        'representation_role':'approved_graphic_asset','treatment':'preserve_as_graphic',
        'visual_bbox_normalized':[0.1,0.2,0.3,0.4],
        'approved_graphic_evidence':{'verification_kind':'graphic_identity','approval_ref':'design:object'}}
def region(element):
    return {'region_id':'R-'+element['id'],'visual_bbox_normalized':element['visual_bbox_normalized'],
        'treatment':element['treatment'],'linked_manifest_ids':[element['id']],
        'destructive_cleanup_risk':'high' if element['treatment']=='preserve_as_graphic' else 'low'}
def validate(elements,truth=None):
    return runtime.validate_stage3_text_plan(_manifest(elements=elements),
        _inventory(items=[region(e) for e in elements]),truth or _truth(),'S001')

@pytest.mark.parametrize('content',['missing','','Aa'])
def test_graphic_identity_needs_no_invented_transcript(content):
    e=asset()
    if content!='missing':e['content']=content
    assert validate([e])=={'status':'PASS','preserved_graphic_typography':[],
                         'manifest_elements':1,'inventory_regions':1}
@pytest.mark.parametrize('content',[None,12,{},[]])
def test_graphic_identity_content_if_provided_is_a_string(content):
    e=asset();e['content']=content
    with pytest.raises(ValueError,match='graphic content must be string'):validate([e])
@pytest.mark.parametrize('value',['missing',False])
def test_identity_verification_does_not_claim_word_correctness(value):
    e=asset()
    if value!='missing':e['approved_graphic_evidence']['content_verified']=value
    assert validate([e])['status']=='PASS'
@pytest.mark.parametrize('ref',[None,'','   ',23])
def test_graphic_identity_still_requires_original_approval_ref(ref):
    e=asset();e['approved_graphic_evidence']['approval_ref']=ref
    with pytest.raises(ValueError,match='PRESERVED_GRAPHIC_CONTENT_INVALID'):validate([e])
@pytest.mark.parametrize('kind',['missing','graphic_identitY','content',None])
def test_only_explicit_identity_marker_selects_relaxed_branch(kind):
    e=asset();ev=e['approved_graphic_evidence']
    if kind=='missing':ev.pop('verification_kind')
    else:ev['verification_kind']=kind
    with pytest.raises(ValueError,match='manifest content required'):validate([e])
    e['content']='ACME'
    with pytest.raises(ValueError,match='PRESERVED_GRAPHIC_CONTENT_INVALID'):validate([e])
    ev['content_verified']=True
    assert validate([e])['status']=='PASS'
@pytest.mark.parametrize('role',['native_text','graphic_typography'])
def test_identity_marker_does_not_bypass_exact_copy_roles(role):
    e=_ordinary_title_element() if role=='native_text' else _graphic_77_element()
    e['approved_graphic_evidence']=asset()['approved_graphic_evidence'];e['content']='wrong'
    expected='STAGE3_TEXT_PLAN_CONTENT_INVALID' if role=='native_text' else 'GRAPHIC_TYPOGRAPHY_CONTENT_INVALID'
    with pytest.raises(ValueError,match=expected):validate([e])
    e['content']=''
    with pytest.raises(ValueError,match='manifest content required'):validate([e])
@pytest.mark.parametrize('fault',['source','treatment','bbox','unlink'])
def test_identity_branch_preserves_source_region_and_treatment_checks(fault):
    e=asset();inv=region(e)
    if fault=='source':e['truth_source']='stage2_final_content_truth'
    elif fault=='treatment':e['treatment']='remove_and_restore';inv['treatment']='remove_and_restore'
    elif fault=='bbox':e['visual_bbox_normalized']=[0,0,-1,1]
    else:inv['linked_manifest_ids']=[]
    with pytest.raises(ValueError):runtime.validate_stage3_text_plan(
        _manifest(elements=[e]),_inventory(items=[inv]),_truth(),'S001')

def test_mixed_graphic_icon_and_reading_caption_keep_separate_occurrences():
    e=asset();e['content']='T';caption=_ordinary_title_element()
    out=validate([e,caption]);assert out['manifest_elements']==2 and out['preserved_graphic_typography']==[]

def test_repeated_reading_strings_remain_two_independent_occurrences():
    first=_ordinary_title_element();second=copy.deepcopy(first)
    second.update(id='M003',truth_ref='S001:T002',visual_bbox_normalized=[0.05,0.5,0.5,0.08])
    truth={'slide_id':'S001','meaningful_text':[{'text':first['content']},{'text':first['content']}],
           'exact_facts':[first['content']]}
    out=validate([asset(),first,second],truth)
    assert out['manifest_elements']==3 and out['inventory_regions']==3

def test_local_artistic_word_keeps_all_four_existing_conditions():
    e=_graphic_77_element();e['visual_bbox_normalized']=[0.15,0.3,0.1,0.05]
    assert validate([e])['preserved_graphic_typography']==['M002']
    for key in e['graphic_typography_evidence']:
        bad=copy.deepcopy(e);bad['graphic_typography_evidence'][key]=False
        with pytest.raises(ValueError,match='GRAPHIC_TYPOGRAPHY_EVIDENCE_INCOMPLETE'):validate([bad])

def put_plan(tmp_path,e,name='manifest'):
    mp=tmp_path/(name+'.json');ip=tmp_path/(name+'-inventory.json')
    mp.write_text(json.dumps(_manifest(elements=[e])),encoding='utf-8')
    ip.write_text(json.dumps(_inventory(items=[region(e)])),encoding='utf-8')
    return mp,ip

def test_identity_plan_change_uses_original_fingerprint_and_invalidates_downstream(tmp_path):
    state=_ready_stage3_page(tmp_path);e=asset();mp,ip=put_plan(tmp_path,e)
    first=bridge.register_text_plan(state,'S001',mp,ip)
    clean=Path(write_png(tmp_path/'clean.png'));bridge.register_text_clean(state,'S001',clean)
    bridge.begin_attempt(state,'S001')
    e['approved_graphic_evidence']['approval_ref']='design:new-object'
    mp2,ip2=put_plan(tmp_path,e,'changed');second=bridge.register_text_plan(state,'S001',mp2,ip2)
    assert first['text_plan_fingerprint']!=second['text_plan_fingerprint']
    saved=runtime.load_runtime_state(state)
    assert 'text_clean' not in saved['slides']['S001']
    assert 'S001' not in saved['canva_bridge'].get('active',{})

def test_tampered_registered_identity_evidence_is_stale_without_rewriting_snapshot(tmp_path):
    state=_ready_stage3_page(tmp_path);e=asset();mp,ip=put_plan(tmp_path,e)
    bridge.register_text_plan(state,'S001',mp,ip)
    saved=runtime.load_runtime_state(state);frozen=Path(saved['slides']['S001']['finalized_manifest'])
    original=frozen.read_bytes();edited=json.loads(original)
    edited['text_elements'][0]['approved_graphic_evidence']['approval_ref']='tampered'
    frozen.write_text(json.dumps(edited),encoding='utf-8')
    with pytest.raises(ValueError,match='STAGE3_TEXT_PLAN_REQUIRED'):bridge._check_text_plan(runtime.load_runtime_state(state),'S001')
    assert frozen.read_bytes()!=original

def test_declared_delta_restores_baseline_and_rejects_unregistered_mutations():
    from visual_text_scope import data,restore_repo_bytes
    d=data();repo=ROOT.parent
    for rel in {p['repo_path'] for p in d['patches']}:
        assert hashlib.sha256(restore_repo_bytes(rel,(repo/rel).read_bytes())).hexdigest()==d['baseline'][rel]
    for rel in ['zanchorflow/scripts/runtime.py','zanchorflow/scripts/canva_bridge.py',
                'zanchorflow/references/04_页面二维生成前置约束与渲染协议_v2.9.md']:
        with pytest.raises(AssertionError):restore_repo_bytes(rel,(repo/rel).read_bytes()+b'\n# undeclared\n')

def test_all_unmodified_runtime_files_keep_original_bytes():
    from visual_text_scope import data,restore_repo_bytes
    d=data()
    for p in (ROOT/'scripts').iterdir():
        if p.is_file():
            rel='zanchorflow/'+p.relative_to(ROOT).as_posix()
            from download_scope import new_runtime, verify_new_runtime
            if p.relative_to(ROOT).as_posix() in new_runtime():
                verify_new_runtime(p.relative_to(ROOT).as_posix(),p.read_bytes());continue
            assert hashlib.sha256(restore_repo_bytes(rel,p.read_bytes())).hexdigest()==d['baseline'][rel]
