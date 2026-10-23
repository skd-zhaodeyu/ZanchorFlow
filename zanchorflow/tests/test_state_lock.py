"""Own-process lock lifecycle fixtures; no user process is terminated."""
import sys,os,json,subprocess,time,uuid
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import state_lock as sl,reconstruction_router as router,canva_bridge as cb
SCRIPTS=Path(sl.__file__).parent


def state(tmp_path):
 f=tmp_path/'state.json';f.write_text('{"slides":{}}');return f


def child(f,body):
 code="import sys,os,json,time;from pathlib import Path;sys.path.insert(0,"+repr(str(SCRIPTS))+");import state_lock as sl,reconstruction_router as r,canva_bridge as cb;state=Path("+repr(str(f))+");ready=state.parent/'ready';\n"+body
 return subprocess.Popen([sys.executable,'-B','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE)


def ready(p,f):
 deadline=time.monotonic()+10
 while not (f.parent/'ready').exists():
  if p.poll() is not None:pytest.fail(p.communicate()[1].decode(errors='replace'))
  if time.monotonic()>deadline:p.kill();p.wait();pytest.fail('own child readiness timeout')
  time.sleep(.01)


def test_normal_exception_cleanup_and_read_only_status(tmp_path):
 f=state(tmp_path)
 with pytest.raises(ValueError):
  with sl.ownership(f):
   before=sl._path(f).read_bytes();assert sl.inspect_lock(f)['status']=='ACTIVE';assert sl._path(f).read_bytes()==before;raise ValueError('own fixture')
 assert sl.inspect_lock(f)['status']=='CLEAR'


def test_forced_exit_metadata_recovers_without_state_changes(tmp_path):
 f=state(tmp_path);before=f.read_bytes();p=child(f,"with sl.ownership(state):\n ready.write_text('ready')\n time.sleep(30)");ready(p,f)
 try:
  assert sl.inspect_lock(f)['status']=='ACTIVE'
  with pytest.raises(FileExistsError):
   with sl.ownership(f):pass
 finally:p.kill();p.wait()
 assert sl.inspect_lock(f)['status']=='RECOVERABLE';assert cb.status(f)['status']=='LOCK_RECOVERY_AVAILABLE'
 with router.transaction(f) as temp:assert temp.read_bytes()==before
 assert f.read_bytes()==before and sl.inspect_lock(f)['status']=='CLEAR';assert list(tmp_path.glob('state.json.bridge-lock-history/*.json'))


@pytest.mark.parametrize('kind',['empty','partial','foreign','unknown','router'])
def test_unverifiable_locks_are_preserved(tmp_path,kind):
 f=state(tmp_path);path=sl._path(f)
 if kind=='router':path=Path(str(f)+'.router-lock');path.write_bytes(b'')
 elif kind in ('empty','partial'):path.write_bytes(b'' if kind=='empty' else b'{')
 else:
  with sl.ownership(f) as owner:data=dict(owner)
  data['host']='foreign' if kind=='foreign' else sl.host_identity();data['start']=data['start'] if kind=='foreign' else None;path.write_text(json.dumps(data))
 raw=path.read_bytes()
 with pytest.raises(FileExistsError):sl.prepare_write(f)
 assert path.read_bytes()==raw


def test_pid_reuse_is_not_mistaken_for_old_owner(tmp_path,monkeypatch):
 f=state(tmp_path)
 with sl.ownership(f) as owner:data=dict(owner)
 sl._path(f).write_text(json.dumps(data));monkeypatch.setattr(sl,'process_identity',lambda _: 'different-start')
 assert sl.inspect_lock(f)['status']=='RECOVERABLE';sl.prepare_write(f);assert not sl._path(f).exists()


def test_permission_unknown_does_not_mean_dead(tmp_path,monkeypatch):
 f=state(tmp_path)
 with sl.ownership(f) as owner:data=dict(owner)
 sl._path(f).write_text(json.dumps(data))
 def denied(_):raise PermissionError('fixture')
 monkeypatch.setattr(sl,'process_identity',denied)
 assert sl.inspect_lock(f)['status']=='UNKNOWN'
 with pytest.raises(FileExistsError):sl.prepare_write(f)


def test_release_cannot_delete_replacement_lock(tmp_path):
 f=state(tmp_path)
 with pytest.raises(ValueError,match='OWNERSHIP_CHANGED'):
  with sl.ownership(f) as owner:
   data=dict(owner);data['id']=uuid.uuid4().hex;sl._path(f).write_text(json.dumps(data))
 assert sl._path(f).exists()


def test_shared_transaction_entrypoints_mutually_exclude(tmp_path):
 f=state(tmp_path)
 with router.transaction(f):
  with pytest.raises(FileExistsError):
   with cb.transaction(f):pass
 with cb.transaction(f):
  with pytest.raises(FileExistsError):
   with router.transaction(f):pass


@pytest.mark.parametrize('committed',[False,True])
def test_termination_before_and_after_commit_never_restores_temp(tmp_path,committed):
 f=state(tmp_path)
 if committed:body="with sl.ownership(state):\n t=state.parent/'new.json';t.write_text('{\"slides\":{},\"committed\":true}');os.replace(t,state);os._exit(17)"
 else:body="with r.transaction(state) as t:\n t.write_text('{\"slides\":{},\"committed\":true}');os._exit(17)"
 p=child(f,body);p.wait(timeout=10);assert p.returncode==17
 with router.transaction(f):pass
 assert json.loads(f.read_text()).get('committed',False)==committed


def test_recovery_rechecks_ownership_before_removing(tmp_path,monkeypatch):
 f=state(tmp_path)
 with sl.ownership(f) as owner:data=dict(owner)
 sl._path(f).write_text(json.dumps(data));real=sl.inspect_lock;count=[0]
 def changing(state):
  count[0]+=1
  if count[0]==2:return {'status':'ACTIVE','raw':b'new-owner'}
  return {'status':'RECOVERABLE','raw':sl._path(f).read_bytes(),'owner':data}
 monkeypatch.setattr(sl,'inspect_lock',changing)
 with pytest.raises(FileExistsError,match='CHANGED'):sl.prepare_write(f)
 assert sl._path(f).exists()


def test_new_lock_excludes_old_client_process(tmp_path):
 f=state(tmp_path)
 with sl.ownership(f):
  p=child(f,"try:\n fd=os.open(sl._path(state),os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)\nexcept FileExistsError:sys.exit(21)")
  p.wait(timeout=10);assert p.returncode==21


def test_old_empty_lock_excludes_new_client_process(tmp_path):
 f=state(tmp_path);path=sl._path(f);fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
 p=child(f,"try:\n with sl.ownership(state):pass\nexcept FileExistsError:sys.exit(21)");p.wait(timeout=10);assert p.returncode==21 and path.exists()


def test_crash_before_metadata_write_stays_unknown(tmp_path):
 f=state(tmp_path);p=child(f,"fd=os.open(sl._path(state),os.O_CREAT|os.O_EXCL|os.O_WRONLY);os._exit(17)");p.wait(timeout=10)
 assert p.returncode==17 and sl.inspect_lock(f)['status']=='UNKNOWN'
 with pytest.raises(FileExistsError):sl.prepare_write(f)


def test_two_recoverers_cannot_overlap(tmp_path):
 f=state(tmp_path);p=child(f,"with sl.ownership(state):os._exit(17)");p.wait(timeout=10);assert sl.inspect_lock(f)['status']=='RECOVERABLE'
 body="try:\n with r.transaction(state):\n  ready.write_text(str(os.getpid()))\n  while not (state.parent/'release').exists():time.sleep(.01)\nexcept FileExistsError:sys.exit(21)"
 first=child(f,body);ready(first,f);second=child(f,body)
 try:second.wait(timeout=10);assert second.returncode==21
 finally:(tmp_path/'release').write_text('go');first.wait(timeout=10)
 assert first.returncode==0 and sl.inspect_lock(f)['status']=='CLEAR'
