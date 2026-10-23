"""Local bridge ownership locks. Unknown/legacy locks fail closed."""
import os,json,uuid,hashlib,platform,time,sys
from pathlib import Path
from contextlib import contextmanager


def host_identity():
    if os.name=='nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Cryptography',0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as k:
                raw=winreg.QueryValueEx(k,'MachineGuid')[0]
        except OSError:return None
    elif sys.platform.startswith('linux'):
        try:raw=Path('/etc/machine-id').read_text().strip()
        except OSError:return None
    else:return None
    return hashlib.sha256((platform.system()+':'+raw).encode()).hexdigest() if raw else None


def process_identity(pid):
    """None proves absence; errors mean unknown, never absence."""
    if type(pid) is not int or pid<=0:raise ValueError('invalid pid')
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes as w
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];api.OpenProcess.restype=w.HANDLE
        api.GetProcessTimes.argtypes=[w.HANDLE,ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME)]
        api.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
        api.CloseHandle.argtypes=[w.HANDLE]
        handle=api.OpenProcess(0x1000,False,pid)
        if not handle:
            error=ctypes.get_last_error()
            if error==87:return None
            raise OSError(error,'process identity unavailable')
        try:
            exitcode=w.DWORD()
            if not api.GetExitCodeProcess(handle,ctypes.byref(exitcode)):raise ctypes.WinError(ctypes.get_last_error())
            if exitcode.value!=259:return None
            born,ended,kernel,user=(w.FILETIME() for _ in range(4))
            if not api.GetProcessTimes(handle,*[ctypes.byref(v) for v in (born,ended,kernel,user)]):raise ctypes.WinError(ctypes.get_last_error())
            return str((born.dwHighDateTime<<32)|born.dwLowDateTime)
        finally:api.CloseHandle(handle)
    if sys.platform.startswith('linux'):
        try:
            raw=Path('/proc',str(pid),'stat').read_text();born=raw[raw.rfind(')')+2:].split()[19]
            return Path('/proc/sys/kernel/random/boot_id').read_text().strip()+':'+born
        except FileNotFoundError:
            if not Path('/proc',str(pid)).exists():return None
            raise
    raise OSError('process identity unsupported')


def _path(state):return Path(state).resolve().with_name(Path(state).name+'.bridge-lock')


def inspect_lock(state):
    path=_path(state)
    if Path(str(Path(state).resolve())+'.router-lock').exists():return {'status':'UNKNOWN','detail':'legacy router lock exists'}
    try:raw=path.read_bytes()
    except FileNotFoundError:return {'status':'CLEAR'}
    try:
        data=json.loads(raw)
        if data.get('format')!=1 or data.get('state')!=str(Path(state).resolve()) or not isinstance(data.get('id'),str) or len(data['id'])!=32 or any(c not in '0123456789abcdef' for c in data['id']):raise ValueError('invalid lock')
        local=host_identity()
        if not local or data.get('host')!=local or not data.get('start'):raise ValueError('unknown owner')
        current=process_identity(data['pid'])
        status='ACTIVE' if current==data['start'] else 'RECOVERABLE'
        return {'status':status,'owner':data,'raw':raw}
    except (OSError,ValueError,KeyError,TypeError):return {'status':'UNKNOWN','detail':'lock ownership cannot be verified'}


@contextmanager
def _guard(state,wait=False):
    path=Path(str(Path(state).resolve())+'.bridge-lock.guard')
    stream=path.open('a+b');locked=False
    try:
        if stream.seek(0,2)==0:stream.write(b'0');stream.flush()
        deadline=time.monotonic()+(2 if wait else 0)
        while True:
            try:
                stream.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                locked=True;break
            except OSError:
                if time.monotonic()>=deadline:raise FileExistsError('STATE_LOCK_GUARD_BUSY')
                time.sleep(.01)
        yield
    finally:
        if locked:
            stream.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
        stream.close()


def _recover(state):
    result=inspect_lock(state)
    if result['status']=='CLEAR':return
    if result['status']!='RECOVERABLE':raise FileExistsError('STATE_LOCK_'+result['status'])
    path=_path(state);raw=result['raw'];history=path.parent/(path.name+'-history');history.mkdir(exist_ok=True)
    record=history/(result['owner']['id']+'-'+uuid.uuid4().hex+'.json')
    # Persist the exact original ownership evidence before removing the stale claim.
    with record.open('xb') as f:f.write(raw)
    again=inspect_lock(state)
    if again.get('raw')!=raw or again['status']!='RECOVERABLE':raise FileExistsError('STATE_LOCK_CHANGED_DURING_RECOVERY')
    if path.read_bytes()!=raw:raise FileExistsError('STATE_LOCK_CHANGED_DURING_RECOVERY')
    path.unlink()


def prepare_write(state):
    with _guard(state):_recover(state)


@contextmanager
def ownership(state):
    path=_path(state);claim=None;failure=None
    with _guard(state):
        _recover(state)
        try:start=process_identity(os.getpid())
        except OSError:start=None
        data={'format':1,'id':uuid.uuid4().hex,'pid':os.getpid(),'start':start,'host':host_identity(),'state':str(Path(state).resolve()),'created_utc_epoch':time.time()}
        claim=json.dumps(data,sort_keys=True).encode()
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        with os.fdopen(fd,'wb') as f:f.write(claim);f.flush();os.fsync(f.fileno())
    try:yield data
    except BaseException as exc:failure=exc;raise
    finally:
        try:
            with _guard(state,wait=True):
                if not path.exists() or path.read_bytes()!=claim:raise ValueError('STATE_LOCK_OWNERSHIP_CHANGED')
                path.unlink()
        except (OSError,ValueError) as exc:
            if failure is None:raise
            failure.add_note('Lock release requires inspection: '+str(exc))
