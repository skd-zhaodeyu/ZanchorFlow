"""Isolated installation matrix and failure/byte-preservation checks. No live installation."""
import ast
import importlib.util
import itertools
import os
import json
from pathlib import Path
import subprocess
import sys
import pytest

REPO=Path(__file__).resolve().parents[2]
INSTALLER_REPO=Path(os.environ.get('ZANCHORFLOW_TEST_INSTALLER_ROOT',str(REPO))).resolve()
spec=importlib.util.spec_from_file_location('unified_installer',INSTALLER_REPO/'tools/install.py')
i=importlib.util.module_from_spec(spec);spec.loader.exec_module(i)
BASE=i.load_baseline()
VIEWS={p:i.make_view(p,BASE) for p in ('full','qwen','workbuddy')}

def context(root):
    return {'skill_roots':[{'path':str(root),'source':'runtime_catalog','persistent':True,'writable':True}]}

def write_tree(root,files):
    root.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)

def observation(host,family,state,residue):
    env={};rows=[]
    exe={'codex':'C:/Apps/Codex/codex.exe','qwen':'C:/Apps/Qianwen/qianwen.exe','workbuddy':'C:/Apps/WorkBuddy/WorkBuddy.exe','other':'C:/Apps/Claude/claude.exe'}
    if state in ('confirmed','noise'):
        if family=='marker' and host=='codex':env['CODEX_THREAD_ID']='synthetic-session'
        elif family=='ancestor':rows=[{'pid':12,'executable':exe[host]}]
        elif family=='packed':
            packed={'codex':exe['codex'],'qwen':'C:/Apps/qwen-agent/node.exe','workbuddy':'C:/Apps/.workbuddy/python.exe','other':exe['other']}
            rows=[{'pid':12,'executable':packed[host]}]
        elif family=='installed':env['INSTALLED_AGENT_DIR']=exe[host]
        elif family=='model':env['MODEL_NAME']=host
    if state=='conflict':
        env['CODEX_THREAD_ID']='synthetic-session';rows=[{'pid':13,'executable':exe['qwen']}]
    if residue or state=='noise':
        env.update({'OLD_AGENT':'WorkBuddy','MODEL_NAME':'qwen-max','UNRELATED_PROCESS':'qianwen.exe','REPORT_HOST':'qwen'})
    # Predeclared oracle from scenario design; not derived from detect().
    strong=state in ('confirmed','noise') and (family in ('ancestor','packed') or family=='marker' and host=='codex')
    expected=host if strong and host in ('qwen','workbuddy') else 'full'
    return env,rows,expected

CASES=list(itertools.product(('codex','qwen','workbuddy','other'),('marker','ancestor','packed','installed','model'),('confirmed','absent','conflict','noise'),('fresh','identical','older'),(False,True)))

@pytest.mark.parametrize('host,family,state,existing,residue',CASES)
def test_480_install_matrix(tmp_path,host,family,state,existing,residue):
    root=tmp_path/'registered-skills';root.mkdir();target=root/'zanchorflow';work=tmp_path/'work'
    env,rows,expected=observation(host,family,state,residue)
    if existing=='identical':write_tree(target,VIEWS[expected])
    elif existing=='older':write_tree(target,{'SKILL.md':b'legacy full installation','old.bin':b'old bytes'})
    if residue:write_tree(tmp_path/'unrelated-workbuddy',{'report.txt':b'host=qwen'})
    before=i.snapshot(target);noise_before=i.snapshot(tmp_path/'unrelated-workbuddy')
    if state=='conflict':
        with pytest.raises(i.Blocked,match='HOST_EVIDENCE_CONFLICT'):i.detect(env,rows)
        assert not work.exists() and i.snapshot(target)==before
    else:
        detection=i.detect(env,rows);assert detection['profile']==expected
        result=i.install(detection,context(root),work)
        assert i.snapshot(target)==i.file_hashes(VIEWS[expected])
        if expected=='full':assert {p: (target/p).read_bytes() for p in BASE}==BASE
        if existing=='identical':assert result['status']=='ALREADY_IDENTICAL' and not work.exists()
        else:
            assert result['status']=='INSTALLED'
            receipt=Path(result['receipt']);assert root not in receipt.parents
            proof=json.loads(receipt.read_text(encoding='utf-8'))
            assert set(proof['changed_paths'])==(i.ALLOWED_DIFFS if expected!='full' else set())
            if existing=='older':assert i.snapshot(Path(result['backup']))==before
        assert i.install(detection,context(root),work)['status']=='ALREADY_IDENTICAL'
    assert i.snapshot(tmp_path/'unrelated-workbuddy')==noise_before

@pytest.mark.parametrize('profile',('full','qwen','workbuddy'))
def test_exact_files_and_quality_functions(profile):
    files=VIEWS[profile];changes={p for p in set(files)|set(BASE) if files.get(p)!=BASE.get(p)}
    assert changes==(set() if profile=='full' else i.ALLOWED_DIFFS)
    for path,data in BASE.items():
        if path not in i.ALLOWED_DIFFS:assert files[path]==data
    original={n.name:ast.dump(n) for n in ast.parse(BASE['scripts/canva_bridge.py']).body if isinstance(n,ast.FunctionDef) and n.name!='main'}
    generated={n.name:ast.dump(n) for n in ast.parse(files['scripts/canva_bridge.py']).body if isinstance(n,ast.FunctionDef) and n.name!='main'}
    assert original==generated

@pytest.mark.parametrize('profile',('qwen','workbuddy'))
@pytest.mark.parametrize('action',('begin-attempt','accept-attempt','register-design-url','bind-download','seal-page'))
def test_magic_cli_rejected_before_state_write(tmp_path,profile,action):
    view=tmp_path/'view';write_tree(view,VIEWS[profile]);state=tmp_path/'missing.json'
    result=subprocess.run([sys.executable,'-B',str(view/'scripts/canva_bridge.py'),action,'--state',str(state)],capture_output=True,text=True,encoding='utf-8')
    assert 'IMAGE_ONLY_VIEW_MAGIC_OPERATION_BLOCKED' in result.stdout and result.returncode!=0
    assert not state.exists()

@pytest.mark.parametrize('profile',('qwen','workbuddy'))
def test_router_old_magic_and_new_magic_rejected(tmp_path,profile):
    view=tmp_path/'view';write_tree(view,VIEWS[profile]);state=tmp_path/'state.json'
    state.write_text(json.dumps({'slides':{},'reconstruction_backend':{'backend':'magic_layer'}}))
    before=state.read_bytes()
    for args in (['status'],['choose-backend','--backend','magic_layer']):
        result=subprocess.run([sys.executable,'-B',str(view/'scripts/reconstruction_router.py'),*args,'--state',str(state)],capture_output=True,text=True,encoding='utf-8')
        assert ('IMAGE_ONLY_VIEW_MAGIC_' in result.stdout+result.stderr if args[0]=='status' else 'invalid choice' in result.stderr) and result.returncode!=0
        assert state.read_bytes()==before

@pytest.mark.parametrize('phase',('before_commit','after_backup','after_publish'))
@pytest.mark.parametrize('existing',(False,True))
def test_failure_rolls_back_exact_original(tmp_path,phase,existing):
    root=tmp_path/'skills';root.mkdir();target=root/'zanchorflow'
    if existing:write_tree(target,{'SKILL.md':b'old','extra.bin':b'important'})
    before=i.snapshot(target)
    def fault(at,*unused):
        if at==phase:raise OSError('synthetic interruption')
    with pytest.raises(i.Blocked,match='ROLLED_BACK'):i.install(i.detect({},[]),context(root),tmp_path/'work',fault)
    assert i.snapshot(target)==before and not (root/'.zanchorflow-install.lock').exists()

@pytest.mark.parametrize('bad',('unknown','missing','multiple','transient','owner','notpersistent','overlap'))
def test_bad_target_no_writes(tmp_path,bad):
    root=tmp_path/'skills';root.mkdir();ctx=context(root);d=i.detect({},[]);work=tmp_path/'work'
    if bad=='unknown':ctx={}
    elif bad=='missing':ctx=context(tmp_path/'missing')
    elif bad=='multiple':second=tmp_path/'second';second.mkdir();ctx['skill_roots']+=context(second)['skill_roots']
    elif bad=='transient':root=tmp_path/'plugins'/'skills';root.mkdir(parents=True);ctx=context(root)
    elif bad=='owner':root=tmp_path/'.workbuddy'/'skills';root.mkdir(parents=True);ctx=context(root);d=i.detect({'CODEX_THREAD_ID':'x'},[])
    elif bad=='notpersistent':ctx['skill_roots'][0]['persistent']=False
    elif bad=='overlap':ctx=context(INSTALLER_REPO)
    with pytest.raises(i.Blocked):i.install(d,ctx,work)
    assert not work.exists() and not (root/'zanchorflow').exists()

@pytest.mark.parametrize('old,new',(('qwen','workbuddy'),('workbuddy','qwen'),('qwen','full'),('workbuddy','full')))
def test_cross_host_upgrade_blocked(tmp_path,old,new):
    root=tmp_path/'skills';root.mkdir();target=root/'zanchorflow';write_tree(target,VIEWS[old]);before=i.snapshot(target)
    d={'host':'unknown' if new=='full' else new,'profile':new,'evidence':[]}
    with pytest.raises(i.Blocked,match='CROSS_HOST'):i.install(d,context(root),tmp_path/'work')
    assert i.snapshot(target)==before

def test_sequence_does_not_change_other_installations(tmp_path):
    snapshots={}
    for host in ('qwen','workbuddy','codex','other','unknown'):
        root=tmp_path/host/'skills';root.mkdir(parents=True)
        d={'host':host,'profile':host if host in ('qwen','workbuddy') else 'full','evidence':[]}
        i.install(d,context(root),tmp_path/'work'/host);snapshots[root]=i.snapshot(root/'zanchorflow')
        for previous,expected in snapshots.items():assert i.snapshot(previous/'zanchorflow')==expected

def test_context_cannot_override_identity(tmp_path):
    p=tmp_path/'context.json';p.write_text('{"host":"qwen","skill_roots":[]}')
    with pytest.raises(i.Blocked,match='OVERRIDE_HOST'):i.read_context(p)

def test_cli_has_no_host_or_force_override():
    result=subprocess.run([sys.executable,'-B',str(INSTALLER_REPO/'tools/install.py'),'inspect','--work',str(REPO.parent/'probe'),'--host','qwen'],capture_output=True,text=True)
    assert result.returncode==2 and 'unrecognized arguments' in result.stderr

def test_stale_lock_preserved(tmp_path):
    root=tmp_path/'skills';root.mkdir();lock=root/'.zanchorflow-install.lock';lock.write_bytes(b'other-owner')
    with pytest.raises(i.Blocked):i.install(i.detect({},[]),context(root),tmp_path/'work')
    assert lock.read_bytes()==b'other-owner' and not (root/'zanchorflow').exists()

def test_redirected_install_location(tmp_path):
    real=tmp_path/'real';real.mkdir();link=tmp_path/'redirect'
    if sys.platform=='win32':
        result=subprocess.run(['cmd','/c','mklink','/J',str(link),str(real)],capture_output=True)
        assert result.returncode==0
    else:link.symlink_to(real,target_is_directory=True)
    with pytest.raises(i.Blocked,match='REDIRECTED'):i.install(i.detect({},[]),context(link),tmp_path/'work')
    assert not (real/'zanchorflow').exists()

@pytest.mark.parametrize('phase',('before_commit','after_backup','after_publish'))
@pytest.mark.parametrize('existing',(False,True))
def test_process_termination_and_next_install_recovery(tmp_path,phase,existing):
    root=tmp_path/'skills';root.mkdir();target=root/'zanchorflow'
    old={'SKILL.md':b'original old','important.bin':b'never lose'}
    if existing:write_tree(target,old)
    program="import importlib.util,os,json;from pathlib import Path;spec=importlib.util.spec_from_file_location('i',%r);i=importlib.util.module_from_spec(spec);spec.loader.exec_module(i);i.install(i.detect({},[]),json.loads(%r),Path(%r),lambda phase,*unused: os._exit(73) if phase==%r else None)" % (str(INSTALLER_REPO/'tools/install.py'),json.dumps(context(root)),str(tmp_path/'work'),phase)
    result=subprocess.run([sys.executable,'-B','-c',program]);assert result.returncode==73
    result=i.install(i.detect({},[]),context(root),tmp_path/'work-next')
    assert i.snapshot(target)==i.file_hashes(BASE)
    receipts=[json.loads(p.read_text(encoding='utf-8')) for p in (root.parent/'.zanchorflow-installs').glob('*/receipt.json')]
    assert any(r['status']=='RECOVERED_AFTER_INTERRUPTION' for r in receipts)
    if existing:assert i.snapshot(Path(result['backup']))==i.file_hashes(old)

def test_readme_delta_keeps_old_hash_and_detects_mutation():
    spec=importlib.util.spec_from_file_location('scope',REPO/'tools/install_scope.py');scope=importlib.util.module_from_spec(spec);spec.loader.exec_module(scope)
    original=scope.restore_readme((REPO/'README.md').read_bytes())
    assert i.digest(original)==scope.DATA['README.md']['baseline_sha256']
    with pytest.raises(AssertionError):scope.restore_readme((REPO/'README.md').read_bytes()+b'undeclared')

@pytest.mark.parametrize('profile',('qwen','workbuddy'))
def test_installed_image_route_and_all_four_quality_gates(tmp_path,profile):
    view=tmp_path/'installed';write_tree(view,VIEWS[profile]);task=tmp_path/'task';task.mkdir()
    program=r'''
import sys,json,importlib.util
from pathlib import Path
repo,view,task=map(Path,sys.argv[1:])
sys.path[:0]=[str(repo/'zanchorflow/scripts'),str(repo/'zanchorflow/tests')]
import test_layer_bridge as fixtures
for name in ('reconstruction_router','layer_bridge'):
    spec=importlib.util.spec_from_file_location(name,view/'scripts'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
fixtures.router=sys.modules['reconstruction_router'];lb=sys.modules['layer_bridge']
assert Path(lb.__file__).is_relative_to(view)
state=fixtures.image_state(task)
restored,review=fixtures._seed_image_restoration_inputs(state,task)
original=json.loads(review.read_text(encoding='utf-8'));checks=0
for gate in fixtures.runtime.GATE_NAMES:
    for mutation in ('failed','missing_check','missing_evidence'):
        data=json.loads(json.dumps(original))
        if mutation=='failed':data['checks'][gate]='FAIL'
        elif mutation=='missing_check':del data['checks'][gate]
        else:del data['evidence'][gate]
        review.write_text(json.dumps(data),encoding='utf-8')
        before=state.read_bytes()
        try:lb.seal_page(state,'S001',restored,review)
        except (ValueError,KeyError):checks+=1
        else:raise AssertionError('quality waiver: '+gate+' '+mutation)
        assert state.read_bytes()==before
review.write_text(json.dumps(original),encoding='utf-8')
assert lb.seal_page(state,'S001',restored,review)['status']=='PAGE_SEALED'
print(json.dumps({'status':'PASS','negative_checks':checks,'installed_router':str(fixtures.router.__file__)}))
'''
    result=subprocess.run([sys.executable,'-B','-c',program,str(REPO),str(view),str(task)],capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)['negative_checks']==12

@pytest.mark.parametrize('backend',('magic_layer','image_layer'))
def test_full_view_keeps_both_route_choices(tmp_path,backend):
    sys.path[:0]=[str(REPO/'zanchorflow/scripts'),str(REPO/'zanchorflow/tests')]
    from test_reconstruction_backend_router import ready_state
    import reconstruction_router
    state=ready_state(tmp_path)
    assert reconstruction_router.choose_backend(state,backend)['backend']==backend
    assert VIEWS['full']==BASE

@pytest.mark.parametrize('profile',('qwen','workbuddy'))
@pytest.mark.parametrize('action',('init','start-run','status'))
@pytest.mark.parametrize('magic',({'reconstruction_backend':{'backend':'magic_layer'}},{'canva_bridge':{'active':{'S001':{'attempt_id':'old'}}}},{'reconstruction_backend':'magic_layer'}))
def test_shared_cli_cannot_reset_or_migrate_old_magic(tmp_path,profile,action,magic):
    view=tmp_path/'view';write_tree(view,VIEWS[profile]);state=tmp_path/'state.json'
    state.write_text(json.dumps({'slides':{},**magic}),encoding='utf-8');before=state.read_bytes()
    result=subprocess.run([sys.executable,'-B',str(view/'scripts/canva_bridge.py'),action,'--state',str(state)],capture_output=True,text=True,encoding='utf-8')
    assert 'IMAGE_ONLY_VIEW_MAGIC_STATE_BLOCKED' in result.stdout+result.stderr
    assert state.read_bytes()==before

def test_changed_target_before_commit_is_preserved(tmp_path):
    root=tmp_path/'skills';root.mkdir();target=root/'zanchorflow';write_tree(target,{'SKILL.md':b'old'})
    def race(at,*unused):
        if at=='before_commit':(target/'external.bin').write_bytes(b'external writer')
    with pytest.raises(i.Blocked):i.install(i.detect({},[]),context(root),tmp_path/'work',race)
    assert (target/'SKILL.md').read_bytes()==b'old' and (target/'external.bin').read_bytes()==b'external writer'

def test_corrupt_baseline_never_prepares_or_installs(tmp_path,monkeypatch):
    repo=tmp_path/'wrong-repo';(repo/'dist').mkdir(parents=True);(repo/'dist/zanchorflow.zip').write_bytes(b'wrong')
    root=tmp_path/'skills';root.mkdir();monkeypatch.setattr(i,'REPO',repo)
    with pytest.raises(i.Blocked,match='BASELINE_ARCHIVE_MISMATCH'):i.install(i.detect({},[]),context(root),tmp_path/'work')
    assert not (tmp_path/'work').exists() and not (root/'zanchorflow').exists()
