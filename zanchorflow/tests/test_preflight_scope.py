import json, os, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import preflight
ROOT=Path(__file__).resolve().parents[1]


def test_package_scope_ignores_merge_and_acquisition(monkeypatch,tmp_path):
    monkeypatch.delenv('CANVA_PPTX_ACQUISITION_ADAPTER',raising=False)
    def forbidden(_output_dir): raise AssertionError('PowerPoint probed in package scope')
    monkeypatch.setattr(preflight,'_probe_powerpoint',forbidden,raising=False)
    result=preflight.check(ROOT,tmp_path,scope='package')
    assert result['blockers']==[]
    assert result['powerpoint_com']=='NOT_REQUIRED'
    assert preflight.exit_code(result)==0


def test_merge_scope_failed_com_is_nonzero(monkeypatch,tmp_path):
    original=preflight.importlib.util.find_spec
    monkeypatch.setattr(preflight.importlib.util,'find_spec',
                        lambda name: object() if name == 'win32com' else original(name))
    monkeypatch.setattr(preflight,'_probe_powerpoint',lambda _output_dir: (False,'synthetic unavailable'),raising=False)
    result=preflight.check(ROOT,tmp_path,scope='merge')
    assert any(x['code']=='POWERPOINT_NATIVE_IMPORT_UNAVAILABLE' for x in result['blockers'])
    assert preflight.exit_code(result)!=0


def test_acquisition_scope_missing_adapter_is_nonzero(monkeypatch,tmp_path):
    monkeypatch.delenv('CANVA_PPTX_ACQUISITION_ADAPTER',raising=False)
    result=preflight.check(ROOT,tmp_path,scope='acquisition')
    assert any(x['code']=='PPTX_ACQUISITION_FAILED' for x in result['blockers'])
    assert preflight.exit_code(result)!=0


def test_test_only_dependencies_do_not_block_runtime(monkeypatch,tmp_path):
    original=preflight.importlib.util.find_spec
    monkeypatch.setattr(preflight.importlib.util,'find_spec',lambda name: None if name in ('PIL','pytest') else original(name))
    result=preflight.check(ROOT,tmp_path,scope='package')
    assert result['test_dependencies']['PIL']=='FAIL'
    assert result['test_dependencies']['pytest']=='FAIL'
    assert not any(x['code']=='PYTHON_DEPENDENCY_MISSING' for x in result['blockers'])
    assert preflight.exit_code(result)==0


def test_cli_json_and_exit_agree_for_acquisition(tmp_path):
    env=os.environ.copy();env.pop('CANVA_PPTX_ACQUISITION_ADAPTER',None)
    cp=subprocess.run([sys.executable,str(ROOT/'scripts'/'preflight.py'),'--skill-dir',str(ROOT),'--output-dir',str(tmp_path),'--scope','acquisition'],capture_output=True,text=True,env=env)
    result=json.loads(cp.stdout)
    assert cp.returncode!=0
    assert result['scope']=='acquisition'
    assert result['blockers']

def test_invalid_manifest_still_returns_json_blocker(tmp_path):
    import shutil
    copied=tmp_path/'skill';shutil.copytree(ROOT,copied,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache'))
    (copied/'manifest.yaml').write_text('canonical_protocols: [broken',encoding='utf-8')
    result=preflight.check(copied,tmp_path/'out',scope='package')
    assert any(x['code']=='MANIFEST_INVALID' for x in result['blockers'])
    assert preflight.exit_code(result)!=0


def _bridge_fixture(tmp_path, n=3):
    import runtime, canva_bridge as bridge
    from PIL import Image
    from stage2_test_helpers import write_stage3_text_plan
    state_path=tmp_path/'state.json'
    bridge.init(state_path)
    outline=tmp_path/'outline.json'
    outline.write_text(json.dumps({'slides':[{k:k+' synthetic page '+str(i) for k in runtime.OUTLINE_FIELDS} for i in range(n)]}),encoding='utf-8')
    runtime.record_stage1_draft(state_path,outline)
    runtime.present_stage1_review(state_path)
    runtime.handle_stage1_reply(state_path,'同意，按这个继续。', decision='approve')
    run=runtime.start_stage2_run(state_path)
    for kind in ('anchor','style_dna'):
        p=tmp_path/(kind+'.json');p.write_text('{}')
        runtime.register_stage2_artifact(state_path,kind,p)
    for sid in run['page_order']:
        p=tmp_path/(sid+'-render.png');Image.new('RGB',(16,9),'red').save(p)
        candidate=runtime.register_stage2_candidate(state_path,sid,p,'synthetic fixture')
        runtime.review_stage2_candidate(state_path,candidate['candidate_id'],'PASS')
        truth={'slide_id':sid,'meaningful_text':['synthetic'],'exact_facts':[]}
        for kind,value in [('final_content_truth',truth),('canvas',{'width':1600,'height':900})]:
            p=tmp_path/(sid+'-'+kind+'.json');p.write_text(json.dumps(value))
            runtime.register_stage2_artifact(state_path,kind+':'+sid,p)
        runtime.mark_stage2_text_reconciled(state_path,sid)
    runtime.present_stage2_formal_display(state_path)
    runtime.seal_stage2_visual_approval(state_path,'确认，按这组页面进入下一阶段。')
    for sid in run['page_order']:
        manifest,inventory=write_stage3_text_plan(tmp_path/(sid+'-manifest.json'),tmp_path/(sid+'-inventory.json'),sid,'synthetic')
        bridge.register_text_plan(state_path,sid,manifest,inventory)
        p=tmp_path/(sid+'-font_fallback.json');p.write_text('{}');runtime.register_stage2_artifact(state_path,'font_fallback:'+sid,p)
        p=tmp_path/(sid+'-text_clean.png');Image.new('RGB',(16,9),'red').save(p)
        bridge.register_text_clean(state_path,sid,p)
    return state_path


def _accepted_attempt(state_path, slide_id, tmp_path, design='design-A', rebuild=False):
    import canva_bridge as bridge
    active=bridge.begin_attempt(state_path,slide_id,rebuild)
    result={**active,'design_id':design,'assessment':'ACCEPT','evidence':'synthetic offline structural assessment'}
    path=tmp_path/(active['attempt_id']+'-result.json');path.write_text(json.dumps(result))
    bridge.accept_attempt(state_path,slide_id,active['attempt_id'],path)
    return bridge.active_identity(preflight.load_runtime_state(state_path),slide_id)


def _host_fixture(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    state_path=_bridge_fixture(tmp_path,n=1)
    identity=_accepted_attempt(state_path,'S001',tmp_path)
    host={**identity,'schema_version':1,'route':'codex-canva',
          'checked_at':datetime.now(timezone.utc).isoformat(),'download_directory':str(tmp_path),
          'checks':{k:'PASS' for k in ('connector_readonly','magic_layers_tool','browser_session','pptx_option')},
          'evidence':{k:'synthetic offline observation' for k in ('connector_readonly','magic_layers_tool','browser_session','pptx_option')}}
    host_path=tmp_path/'host.json';host_path.write_text(json.dumps(host))
    monkeypatch.setattr(preflight.shutil,'which',lambda _: 'synthetic-powershell')
    return state_path,host_path,host


def test_codex_acquisition_without_report_is_blocked(tmp_path):
    result = preflight.check(ROOT,tmp_path,'acquisition',acquisition_route='codex-canva')
    assert preflight.exit_code(result) != 0
    assert result['canva_pptx_acquisition']=='HOST_CHECK_REQUIRED'


def test_codex_host_accepts_bound_local_evidence_not_live_claim(tmp_path, monkeypatch):
    state, path, host = _host_fixture(tmp_path,monkeypatch)
    result = preflight.check(ROOT,tmp_path,'acquisition','codex-canva',path,state,'S001')
    assert result['blockers']==[]
    assert result['canva_pptx_acquisition']=='HOST_EVIDENCE_ACCEPTED_LIVE_UNVERIFIED'


def test_codex_host_rejects_identity_stale_source_and_missing_observation(tmp_path, monkeypatch):
    state, path, host = _host_fixture(tmp_path,monkeypatch)
    for field, value in [('design_id','wrong-design'),('source_fingerprint','old')]:
        changed = dict(host); changed[field] = value
        path.write_text(json.dumps(changed),encoding='utf-8')
        result = preflight.check(ROOT,tmp_path,'acquisition','codex-canva',path,state,'S001')
        assert preflight.exit_code(result) != 0
    path.write_text(json.dumps(host),encoding='utf-8')
    original_clean=(tmp_path/'S001-text_clean.png').read_bytes()
    (tmp_path/'S001-text_clean.png').write_bytes(b'changed after report')
    assert preflight.exit_code(preflight.check(ROOT,tmp_path,'acquisition','codex-canva',path,state,'S001')) != 0
    (tmp_path/'S001-text_clean.png').write_bytes(original_clean)
    host['evidence']['browser_session']=''
    path.write_text(json.dumps(host),encoding='utf-8')
    assert preflight.exit_code(preflight.check(ROOT,tmp_path,'acquisition','codex-canva',path,state,'S001')) != 0


def test_codex_host_rejects_old_checks(tmp_path, monkeypatch):
    state, path, host = _host_fixture(tmp_path,monkeypatch)
    host['checked_at']='2000-01-01T00:00:00Z'
    path.write_text(json.dumps(host),encoding='utf-8')
    assert preflight.exit_code(preflight.check(ROOT,tmp_path,'acquisition','codex-canva',path,state,'S001')) != 0



def test_acquisition_preflight_does_not_require_magic_layers_tool(tmp_path, monkeypatch):
    state,path,host=_host_fixture(tmp_path,monkeypatch)
    host['checks'].pop('magic_layers_tool',None);host['evidence'].pop('magic_layers_tool',None)
    path.write_text(json.dumps(host),encoding='utf-8')
    result=preflight.check(ROOT,tmp_path,'acquisition','codex-canva',path,state,'S001')
    assert result['blockers']==[]

def test_acquisition_preflight_does_not_require_preselected_browser_download_directory(tmp_path, monkeypatch):
    state,path,host=_host_fixture(tmp_path,monkeypatch)
    host.pop('download_directory',None);path.write_text(json.dumps(host),encoding='utf-8')
    result=preflight.check(ROOT,tmp_path,'acquisition','codex-canva',path,state,'S001')
    assert result['blockers']==[]

def test_acquisition_preflight_still_requires_current_browser_and_pptx_evidence(tmp_path, monkeypatch):
    state,path,host=_host_fixture(tmp_path,monkeypatch)
    for key in ('connector_readonly','browser_session','pptx_option'):
        changed=json.loads(json.dumps(host));changed['checks'][key]='FAIL';path.write_text(json.dumps(changed),encoding='utf-8')
        result=preflight.check(ROOT,tmp_path,'acquisition','codex-canva',path,state,'S001')
        assert preflight.exit_code(result)!=0,key

def test_rc7_init_preserves_existing_state_and_blocks_unapproved_stage(tmp_path):
    import pytest,canva_bridge as bridge,runtime
    state=tmp_path/'fresh'/'state.json'
    assert bridge.init(state)['status']=='INITIALIZED'
    before=state.read_bytes()
    assert bridge.init(state,route='external')['status']=='EXISTING_STATE_UNCHANGED'
    assert state.read_bytes()==before
    assert bridge.status(state)['status']=='AWAITING_STAGE1_APPROVAL'
    with pytest.raises(ValueError): bridge.begin_attempt(state,'S001')
    assert state.read_bytes()==before


def test_rc7_host_report_old_attempt_rejected_after_same_input_rebuild(tmp_path,monkeypatch):
    state,path,host=_host_fixture(tmp_path,monkeypatch)
    _accepted_attempt(state,'S001',tmp_path,design='design-B',rebuild=True)
    assert preflight.exit_code(preflight.check(ROOT,tmp_path,'acquisition','codex-canva',path,state,'S001')) != 0



def test_rc9_codex_acquisition_dependencies_do_not_change_other_routes(tmp_path,monkeypatch):
    state,path,host=_host_fixture(tmp_path,monkeypatch)
    original=preflight.importlib.util.find_spec
    adapter=tmp_path/'external-adapter.py';adapter.write_text('# synthetic provided adapter')
    monkeypatch.setenv('CANVA_PPTX_ACQUISITION_ADAPTER',str(adapter))
    for missing in ('pptx','lxml'):
        with monkeypatch.context() as m:
            m.setattr(preflight.importlib.util,'find_spec',lambda name:None if name==missing else original(name))
            codex=preflight.check(ROOT,tmp_path/'codex','acquisition','codex-canva',path,state,'S001')
            assert preflight.exit_code(codex)!=0
            assert any(x['code']=='PYTHON_DEPENDENCY_MISSING' and x['stage']=='pptx_acquisition' for x in codex['blockers'])
            assert preflight.exit_code(preflight.check(ROOT,tmp_path/'external','acquisition','external'))==0
            assert preflight.exit_code(preflight.check(ROOT,tmp_path/'package','package'))==0



def test_rc10_acquisition_uses_preparation_binding_and_is_readonly(tmp_path,monkeypatch):
    import runtime
    state,path,host=_host_fixture(tmp_path,monkeypatch)
    saved=runtime.load_runtime_state(state);saved['canva_bridge'].pop('text_preparation')
    runtime._save_runtime_state(state,saved);before=state.read_bytes()
    result=preflight.check(ROOT,tmp_path,'acquisition','codex-canva',path,state,'S001')
    assert preflight.exit_code(result)!=0 and state.read_bytes()==before


def test_rc10_unapproved_registration_and_external_route_remain_blocked(tmp_path):
    state=tmp_path/'state.json';artifact=tmp_path/'clean.png';artifact.write_bytes(b'OFFLINE')
    import canva_bridge as bridge
    bridge.init(state);before=state.read_bytes()
    cp=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/canva_bridge.py'),
         'register-text-clean','--state',str(state),'--slide-id','S001','--artifact',str(artifact)],capture_output=True,text=True,encoding='utf-8')
    assert cp.returncode==1 and cp.stderr=='' and json.loads(cp.stdout)['status']=='BLOCKED'
    assert state.read_bytes()==before
    external=tmp_path/'external.json';bridge.init(external,route='external');before=external.read_bytes()
    cp=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/canva_bridge.py'),
         'register-text-clean','--state',str(external),'--slide-id','S001','--artifact',str(artifact)],capture_output=True,text=True,encoding='utf-8')
    assert cp.returncode==1 and json.loads(cp.stdout)['status']=='BLOCKED' and external.read_bytes()==before
