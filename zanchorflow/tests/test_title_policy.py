"""Behavioral heading-policy tests; all approvals/images here are explicit offline fixtures."""
import copy
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import runtime as r
import canva_bridge as cb
import title_policy as t
from stage2_test_helpers import write_png, write_truth, write_stage3_text_plan


def setup(tmp_path, tasks=None, required=True):
    tasks = tasks or ['封面', '普通内容页', '普通内容页']
    op=tmp_path/'outline.json'
    op.write_text(json.dumps({'slides':[{k:(task if k=='page_task' else f'{k}-{i}') for k in r.OUTLINE_FIELDS} for i,task in enumerate(tasks)]},ensure_ascii=False),encoding='utf-8')
    state=tmp_path/'state.json';cb.init(state,'external')
    r.record_stage1_draft(state,op);r.present_stage1_review(state);r.handle_stage1_reply(state,'fixture outline approved',decision='approve')
    cb.start_run(state,title_choice_required=required)
    return state


def choose(state, roles=None, mode='uniform'):
    order=r.load_runtime_state(state)['stage2_run']['page_order']
    return t.set_policy(state,mode,roles or {sid:('cover' if i==0 else 'content') for i,sid in enumerate(order)},'fixture: uniform headings' if mode=='uniform' else 'fixture: free headings')


def page(state,tmp_path,sid,variant=False,override=None,marker=''):
    png=write_png(tmp_path/(sid+'-'+str(marker)+'.png'),(sid+str(marker)).encode())
    c=r.register_stage2_candidate(state,sid,png,'fixture '+sid+str(marker),user_requested_variant=variant,title_override_message=override,
        title_contract_ref=t.context(state,sid).get('contract_ref'))
    r.review_stage2_candidate(state,c['candidate_id'],'PASS')
    return png


def payload(state,sid,**assessment):
    a={'role':'navigation','content_is_primary':True,'display_exception':False,'evidence':'fixture: heading remains navigation, information occupies main region'}
    a.update(assessment)
    return {'source_render_sha256':r.current_stage2_approved_render(state,sid)['sha256'],
            'heading_assessment':a,'style':{'font_family':'Arial','fallback_font_family':'Arial',
            'font_family_basis':'estimated','font_weight':'bold','color':'#203040',
            'title_region':[0.08,0.04,0.84,0.17],'alignment':'left','first_line_baseline':0.10,
            'visible_glyph_height':0.045,'line_height_ratio':1.15,'max_lines':2}}


def seeded(tmp_path):
    state=setup(tmp_path);choose(state);page(state,tmp_path,'S001');page(state,tmp_path,'S002')
    result=t.bind(state,'S002',payload(state,'S002'))
    return state,result['contract_ref']


def plan(state,tmp_path,sid,ref,text='fixture heading'):
    truth=write_truth(tmp_path/(sid+'-truth.json'),sid,text)
    r.register_stage2_artifact(state,'final_content_truth:'+sid,truth);r.mark_stage2_text_reconciled(state,sid)
    m=tmp_path/(sid+'-manifest.json');inv=tmp_path/(sid+'-inventory.json');write_stage3_text_plan(m,inv,sid,text)
    data=json.loads(m.read_text());data.update(title_contract_ref=ref,title_element_ids=['M001']);m.write_text(json.dumps(data),encoding='utf-8')
    return m,inv


def test_choice_persists_on_resume_without_extra_standard_approval(tmp_path):
    state=setup(tmp_path);original=r.load_runtime_state(state)['stage2_run']['run_id']
    assert t.context(state)['mode']=='pending'
    assert cb.status(state)['title_policy']['next_action']=='choose_uniform_or_free'
    choose(state);cb.start_run(state,title_choice_required=True)
    assert r.load_runtime_state(state)['stage2_run']['run_id']==original
    assert t.context(state)['mode']=='uniform'
    assert 'title_approval' not in r.load_runtime_state(state)['stage2_run']


def test_old_state_and_old_call_remain_free_without_new_fields(tmp_path):
    state=setup(tmp_path,required=False)
    assert 'title_policy' not in r.load_runtime_state(state)['stage2_run']
    assert t.context(state)=={'mode':'free','origin':'legacy_unchanged'}
    page(state,tmp_path,'S001');page(state,tmp_path,'S002');page(state,tmp_path,'S003')
    assert r.stage2_visual_status(state)['status']=='COMPLETE'
    assert all('title_context' not in c for c in r.load_runtime_state(state)['stage2_run']['candidates'].values())


def test_free_mode_keeps_normal_generation_without_binding(tmp_path):
    state=setup(tmp_path);choose(state,mode='free')
    for sid in ('S001','S002','S003'):page(state,tmp_path,sid)
    assert r.stage2_visual_status(state)['status']=='COMPLETE'


def test_no_applicable_pages_skip_uniformity(tmp_path):
    state=setup(tmp_path,['封面','纯致谢']);choose(state,{'S001':'cover','S002':'thanks'})
    assert t.context(state)['mode']=='free'
    for sid in ('S001','S002'):page(state,tmp_path,sid)
    assert r.stage2_visual_status(state)['status']=='COMPLETE'


def test_pending_choice_does_not_grant_generation(tmp_path):
    state=setup(tmp_path);before=state.read_bytes()
    with pytest.raises(ValueError,match='TITLE_USER_CHOICE_REQUIRED'):page(state,tmp_path,'S001')
    assert state.read_bytes()==before


def test_initial_context_has_protection_before_any_prototype(tmp_path):
    state=setup(tmp_path);choose(state)
    ctx=t.context(state,'S002')
    assert ctx['next_action']=='generate_normal_heading_prototype'
    assert '由实质信息内容承担页面主视觉' in ctx['heading_requirement']
    assert 'contract_ref' not in ctx


def test_normal_prominent_heading_seeds_then_inherits_without_new_human_gate(tmp_path):
    state,ref=seeded(tmp_path)
    ctx=t.context(state,'S003');assert ctx['contract_ref']==ref
    assert ctx['style']['max_lines']==2
    assert ctx['overflow_action']=='keep_scale_wrap_two_lines_then_author_choice'
    page(state,tmp_path,'S003')
    run=r.load_runtime_state(state)['stage2_run']
    assert run['current_approved']['S003']['title_contract_ref']==ref
    assert r.stage2_visual_status(state)['status']=='COMPLETE'
    assert r.present_stage2_formal_display(state)['status']=='COMPLETE'
    r.seal_stage2_visual_approval(state,'fixture final set approved')


@pytest.mark.parametrize('task,role',[('目录','toc'),('章节过渡','section'),('明确展示性表达','display')])
def test_page_two_special_role_is_skipped_as_prototype(tmp_path,task,role):
    state=setup(tmp_path,['封面',task,'普通内容页']);choose(state,{'S001':'cover','S002':role,'S003':'content'})
    page(state,tmp_path,'S001');page(state,tmp_path,'S002');page(state,tmp_path,'S003')
    with pytest.raises(ValueError,match='CONTENT_PAGE'):t.bind(state,'S002',payload(state,'S002'))
    assert t.bind(state,'S003',payload(state,'S003'))['status']=='TITLE_BOUND'


def test_cover_cannot_seed_or_be_relabelled_content(tmp_path):
    state=setup(tmp_path);before=state.read_bytes()
    with pytest.raises(ValueError,match='ROLE_CONFLICT'):choose(state,{'S001':'content','S002':'content','S003':'content'})
    assert state.read_bytes()==before
    choose(state);page(state,tmp_path,'S001')
    with pytest.raises(ValueError,match='CONTENT_PAGE'):t.bind(state,'S001',payload(state,'S001'))


@pytest.mark.parametrize('assessment',[{'role':'display','content_is_primary':False,'display_exception':False},
                                     {'role':'display','content_is_primary':False,'display_exception':True},
                                     {'role':'navigation','content_is_primary':False}])
def test_title_dominance_cannot_seed_even_if_page_was_passed(tmp_path,assessment):
    state=setup(tmp_path);choose(state);page(state,tmp_path,'S002');before=state.read_bytes()
    with pytest.raises(ValueError,match='CANNOT_SEED'):t.bind(state,'S002',payload(state,'S002',**assessment))
    assert state.read_bytes()==before


def test_unauthorized_title_dominance_uses_existing_h2_not_new_gate(tmp_path):
    state=setup(tmp_path);choose(state)
    c=r.register_stage2_candidate(state,'S002',write_png(tmp_path/'bad.png'),'fixture dominant heading')
    result=r.review_stage2_candidate(state,c['candidate_id'],'REVISE',failed_hard_gate='H2',
        observable_evidence='fixture title dominates layout and substantive information is secondary',required_correction='restore heading navigation and content dominance')
    assert result['review']['failed_hard_gate']=='H2'
    assert r.current_stage2_approved_render(state,'S002') is None
    assert r.GATE_NAMES==('content_truth','semantic_fidelity','functional_editability','visual_fidelity')


def test_authorized_display_exception_remains_local_and_next_page_seeds(tmp_path):
    state=setup(tmp_path);choose(state);page(state,tmp_path,'S001');page(state,tmp_path,'S002')
    p=payload(state,'S002',role='display',content_is_primary=False,display_exception=True)
    result=t.bind(state,'S002',p,'page_override','fixture: this page is explicitly promotional')
    assert t.context(state,'S002')['heading_role']=='display'
    assert 'promotional' in t.context(state,'S002')['actual_page_instruction']
    assert t.context(state,'S003')['next_action']=='generate_normal_heading_prototype'
    page(state,tmp_path,'S003');t.bind(state,'S003',payload(state,'S003'))
    assert t.context(state,'S003')['contract_ref']!=result['contract_ref']
    assert t.context(state,'S002')['contract_ref']==result['contract_ref']


def test_bind_is_idempotent_and_does_not_rewrite_downloads_or_budget(tmp_path):
    state,ref=seeded(tmp_path);before=state.read_bytes()
    result=t.bind(state,'S002',payload(state,'S002'))
    assert result['idempotent'] and result['contract_ref']==ref
    assert state.read_bytes()==before


def test_stale_source_and_missing_evidence_leave_state_unchanged(tmp_path):
    state=setup(tmp_path);choose(state);page(state,tmp_path,'S002')
    for edit in ('source','evidence'):
        data=payload(state,'S002')
        if edit=='source':data['source_render_sha256']='wrong'
        else:data['heading_assessment']['evidence']=''
        before=state.read_bytes()
        with pytest.raises(ValueError):t.bind(state,'S002',data)
        assert state.read_bytes()==before


@pytest.mark.parametrize('field,value',[('first_line_baseline',True),('visible_glyph_height',float('nan')),
 ('title_region',[0,0,1,False]),('max_lines',True),('max_lines',3),('font_family_basis','exact_from_png')])
def test_invalid_style_is_not_registered(tmp_path,field,value):
    state=setup(tmp_path);choose(state);page(state,tmp_path,'S002');p=payload(state,'S002');p['style'][field]=value
    before=state.read_bytes()
    with pytest.raises(ValueError):t.bind(state,'S002',p)
    assert state.read_bytes()==before


def test_next_page_waits_only_for_automatic_binding_not_author_confirmation(tmp_path):
    state=setup(tmp_path);choose(state);page(state,tmp_path,'S002')
    assert t.context(state,'S003')['next_action']=='bind_current_prototype'
    before=state.read_bytes()
    with pytest.raises(ValueError,match='BIND_CURRENT_PROTOTYPE'):page(state,tmp_path,'S003')
    assert state.read_bytes()==before
    t.bind(state,'S002',payload(state,'S002'));page(state,tmp_path,'S003')


def test_local_base_page_change_keeps_deck_standard_snapshot(tmp_path):
    state,ref=seeded(tmp_path);page(state,tmp_path,'S002',True,'fixture: change only this heading',marker='local')
    assert 'S002' in t.pending_pages(r.load_runtime_state(state))
    p=payload(state,'S002');p['style']['font_weight']='regular'
    local=t.bind(state,'S002',p,'page_override','fixture: change only this heading')
    assert t.context(state,'S003')['contract_ref']==ref
    assert t.context(state,'S002')['contract_ref']==local['contract_ref']!=ref
    assert t.pending_pages(r.load_runtime_state(state))==[]
    with pytest.raises(ValueError,match='IMMUTABLE'):t.bind(state,'S002',p)


def test_global_revision_marks_affected_pass_pages_without_whole_deck_reopen_gate(tmp_path):
    state,ref=seeded(tmp_path);page(state,tmp_path,'S003')
    page(state,tmp_path,'S002',True,'fixture: all content headings bold blue',marker='global')
    p=payload(state,'S002');p['style']['color']='#0000FF'
    result=t.bind(state,'S002',p,'global_revision','fixture: all content headings bold blue')
    assert result['pending_revision_pages']==['S003']
    assert r.stage2_visual_status(state)['status']=='INCOMPLETE'
    assert r.present_stage2_formal_display(state)['status']=='INCOMPLETE'
    assert t.context(state,'S003')['contract_ref']==result['contract_ref']
    page(state,tmp_path,'S003',True,marker='new-global')
    assert r.stage2_visual_status(state)['status']=='COMPLETE'
    assert ref in r.load_runtime_state(state)['stage2_run']['title_policy']['contracts']


def test_inflight_candidate_cannot_pass_with_stale_global_reference(tmp_path):
    state,ref=seeded(tmp_path)
    old=r.register_stage2_candidate(state,'S003',write_png(tmp_path/'old-candidate.png'),'fixture before change',title_contract_ref=ref)
    page(state,tmp_path,'S002',True,'fixture global change',marker='new')
    p=payload(state,'S002');p['style']['color']='#112233';t.bind(state,'S002',p,'global_revision','fixture global change')
    before=state.read_bytes()
    with pytest.raises(ValueError,match='REFERENCE_MISMATCH'):r.review_stage2_candidate(state,old['candidate_id'],'PASS')
    assert state.read_bytes()==before


def test_new_run_archives_standard_and_stale_snapshot_is_rejected(tmp_path):
    state,ref=seeded(tmp_path);old=copy.deepcopy(r.load_runtime_state(state)['stage2_run']['title_policy'])
    r.start_stage2_run(state,restart=True,title_choice_required=True)
    saved=r.load_runtime_state(state);assert saved['stage2_history'][-1]['title_policy']==old
    saved['stage2_run']['title_policy']=old;r._save_runtime_state(state,saved)
    with pytest.raises(ValueError,match='SOURCE_MISMATCH'):t.context(state)


def test_snapshot_tampering_is_detected(tmp_path):
    state,ref=seeded(tmp_path);saved=r.load_runtime_state(state)
    saved['stage2_run']['title_policy']['contracts'][ref]['style']['color']='#FFFFFF';r._save_runtime_state(state,saved)
    with pytest.raises(ValueError,match='SNAPSHOT_CHANGED'):t.context(state,'S003')


def test_native_manifest_preserves_actual_bbox_and_only_explicit_title_ids(tmp_path):
    state,ref=seeded(tmp_path);m,inv=plan(state,tmp_path,'S002',ref)
    manifest=json.loads(m.read_text());first=manifest['text_elements'][0]
    # Same text in a second occurrence must not be mistaken for the page heading.
    saved=r.load_runtime_state(state);tp=Path(saved['slides']['S002']['final_content_truth'])
    truth=json.loads(tp.read_text());truth['meaningful_text'].append({'text':'fixture heading'})
    tp.write_text(json.dumps(truth));r.register_stage2_artifact(state,'final_content_truth:S002',tp)
    extra=copy.deepcopy(first);extra.update(id='M002',truth_ref='S002:T002',visual_bbox_normalized=[0.2,0.4,0.5,0.05]);manifest['text_elements'].append(extra)
    assert t.validate_manifest(r.load_runtime_state(state),'S002',manifest)==['M001']
    assert first['visual_bbox_normalized']!=t.context(state,'S002')['style']['title_region']
    assert extra['visual_bbox_normalized']==[0.2,0.4,0.5,0.05]


@pytest.mark.parametrize('change',['reference','ids','graphics','truth','duplicate','wrong_page'])
def test_bad_manifest_rejected_before_artifact_replacement(tmp_path,change):
    state,ref=seeded(tmp_path);m,inv=plan(state,tmp_path,'S002',ref)
    r.register_stage2_artifact(state,'finalized_manifest:S002',m)
    data=json.loads(m.read_text())
    if change=='reference':data['title_contract_ref']='wrong'
    elif change=='ids':data['title_element_ids']=['missing']
    elif change=='duplicate':data['title_element_ids']=['M001','M001']
    elif change=='graphics':data['text_elements'][0]['representation_role']='approved_graphic_asset'
    elif change=='truth':data['text_elements'][0]['content']='wrong'
    else:data['slide_id']='S003'
    bad=tmp_path/'bad-manifest.json';bad.write_text(json.dumps(data));before=state.read_bytes()
    with pytest.raises(ValueError):r.register_stage2_artifact(state,'finalized_manifest:S002',bad)
    assert state.read_bytes()==before


def test_cli_three_actions_and_short_context(tmp_path,capsys):
    state=setup(tmp_path);rp=tmp_path/'roles.json';rp.write_text(json.dumps({'S001':'cover','S002':'content','S003':'content'}))
    assert r.main(['stage2-title-policy','--state',str(state),'--mode','uniform','--page-roles-json',str(rp),'--message','fixture uniform'])==0
    capsys.readouterr();page(state,tmp_path,'S002');p=tmp_path/'contract.json';p.write_text(json.dumps(payload(state,'S002')))
    assert r.main(['stage2-title-bind','--state',str(state),'--slide-id','S002','--contract-json',str(p)])==0
    ref=json.loads(capsys.readouterr().out)['contract_ref']
    assert r.main(['stage2-title-context','--state',str(state),'--slide-id','S003'])==0
    ctx=json.loads(capsys.readouterr().out);assert ctx['contract_ref']==ref and len(json.dumps(ctx))<1800


@pytest.mark.parametrize('suffix',['.bridge-lock','.router-lock'])
def test_title_mutation_preserves_existing_operation_lock(tmp_path,suffix):
    state=setup(tmp_path);lock=Path(str(state)+suffix);lock.write_text('fixture active operation');before=state.read_bytes()
    with pytest.raises(ValueError,match='OPERATION_RUNNING'):choose(state)
    assert state.read_bytes()==before and lock.read_text()=='fixture active operation'


def test_pre_generation_reference_must_be_carried_for_uniform_following_page(tmp_path):
    state,ref=seeded(tmp_path);before=state.read_bytes()
    with pytest.raises(ValueError,match='REFERENCE_REQUIRED'):
        r.register_stage2_candidate(state,'S003',write_png(tmp_path/'unbound-generation.png'),'fixture missing observed reference')
    assert state.read_bytes()==before


def test_scope_normalization_retains_old_pins_and_detects_unrelated_changes():
    from title_scope import normalize_runtime_bytes, data
    import hashlib
    skill=Path(__file__).resolve().parents[1]
    for rel in ('scripts/runtime.py','scripts/canva_bridge.py'):
        original=normalize_runtime_bytes(rel,(skill/rel).read_bytes())
        assert hashlib.sha256(original).hexdigest()==data()['baseline']['zanchorflow/'+rel]
    bad=(skill/'scripts/runtime.py').read_bytes().replace(b"GATE_NAMES = (",b"GATE_NAMES = ('unauthorized_gate', ",1)
    with pytest.raises(AssertionError):normalize_runtime_bytes('scripts/runtime.py',bad)


def test_no_content_page_classification_skips_choice_without_user_message(tmp_path):
    state=setup(tmp_path,['封面','目录','纯致谢'])
    policy=t.set_policy(state,'pending',{'S001':'cover','S002':'toc','S003':'thanks'})
    assert policy['mode']=='free'
    assert policy['selection_origin']=='system_no_applicable_pages'
    assert 'user_message' not in policy
    for sid in ('S001','S002','S003'):page(state,tmp_path,sid)
    assert r.stage2_visual_status(state)['status']=='COMPLETE'
