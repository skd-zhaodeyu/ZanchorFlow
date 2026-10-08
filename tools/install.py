"""Install one immutable baseline or a narrowly generated Image Layer view.
No --host/--force override. Detection occurs only here, never in the installed full skill.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import stat
import subprocess
import sys
from uuid import uuid4
import zipfile

REPO = Path(__file__).resolve().parents[1]
SOURCE_BASE_SHA = 'c40a4adc513b83493e465860898e8da2a8c215c109ed1345b690733086e5cef7'
BASE_SHA = '0de267f9c2953c22e0dbbf45ce0e4c5de7bc549176cd876e2ccb1108d25147f1'
CODEX_MARKERS = ('CODEX_THREAD_ID','CODEX_SESSION_ID','CODEX_APP_TOOLS_PIPE_PATH')
PROFILE_HOSTS = {'qwen','workbuddy'}
ALLOWED_DIFFS = {'SKILL.md','scripts/reconstruction_router.py','scripts/canva_bridge.py','docs/host-tools.md'}
TRANSIENT_PARTS = {'cache','.cache','temp','tmp','sandbox','plugins','qwen-agent'}

class Blocked(ValueError):
    pass

def digest(data):
    return hashlib.sha256(data).hexdigest()

def inside(path,root):
    return path==root or root in path.parents

def absolute(value):
    path=Path(value)
    if not path.is_absolute():raise Blocked('ABSOLUTE_PATH_REQUIRED')
    raw=Path(os.path.abspath(path))
    if raw.resolve()!=raw:raise Blocked('REDIRECTED_PATH_BLOCKED')
    return raw

def read_context(path):
    if path is None:return {}
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(data,dict) or set(data)-{'skill_roots'}:raise Blocked('CONTEXT_CANNOT_OVERRIDE_HOST')
    return data

def ancestor_chain():
    """Observe only this process ancestry, not unrelated installed/running apps."""
    if os.name=='nt':
        script=(f'$probeId={os.getpid()}; $rows=@(); $seen=@{{}}; '
          'for($i=0;$i -lt 32 -and $probeId -gt 0;$i++){ '
          'if($seen.ContainsKey($probeId)){break};$seen[$probeId]=$true; '
          '$p=Get-CimInstance Win32_Process -Filter ("ProcessId="+$probeId) -ErrorAction SilentlyContinue; '
          'if($null -eq $p){break}; '
          '$rows+=@{pid=[int]$p.ProcessId;parent_pid=[int]$p.ParentProcessId;executable=[string]$p.ExecutablePath}; '
          '$probeId=[int]$p.ParentProcessId }; ConvertTo-Json -InputObject @($rows) -Compress')
        try:
            completed=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15)
            if completed.returncode:return []
            data=json.loads(completed.stdout)
            return data if isinstance(data,list) else []
        except (OSError,ValueError,subprocess.TimeoutExpired):return []
    rows=[];pid=os.getpid();seen=set()
    for _ in range(32):
        if pid<=0 or pid in seen:break
        seen.add(pid)
        try:
            exe=os.readlink(f'/proc/{pid}/exe')
            fields=Path(f'/proc/{pid}/stat').read_text().rpartition(')')[2].split()
            parent=int(fields[1]);rows.append({'pid':pid,'parent_pid':parent,'executable':exe});pid=parent
        except (OSError,ValueError,IndexError):break
    return rows

def executable_host(executable):
    # Exact executable families/path components; substrings and model names are not identity.
    p=PureWindowsPath(executable.replace('/','\\'))
    name=p.name.lower();parts={x.lower() for x in p.parts}
    if name in {'codex','codex.exe','codex-code-mode-host','codex-code-mode-host.exe'}:return 'codex'
    if name in {'qianwen.exe','qianwen','千问.exe','qwen-agent.exe'}:return 'qwen'
    if name in {'workbuddy.exe','workbuddy'}:return 'workbuddy'
    if name in {'node.exe','node','python.exe','python','codebuddy.exe','codebuddy'}:
        if '.workbuddy' in parts or 'workbuddy' in parts:return 'workbuddy'
        if 'qianwen' in parts or 'qwen-agent' in parts:return 'qwen'
    if name in {'claude','claude.exe','cursor.exe','windsurf.exe'}:return 'other'
    return None

def detect(env=None,ancestors=None):
    env=os.environ if env is None else env
    ancestors=ancestor_chain() if ancestors is None else ancestors
    observations=[]
    for name in CODEX_MARKERS:
        if env.get(name):observations.append({'host':'codex','source':'current_process_marker','marker':name})
    # Caller supplies ancestors only through private test injection; CLI cannot override them.
    for row in ancestors:
        host=executable_host(str(row.get('executable','')))
        if host:observations.append({'host':host,'source':'current_ancestor','pid':row.get('pid'),'executable_name':PureWindowsPath(str(row.get('executable',''))).name,'executable_path':str(row.get('executable',''))})
    hosts={x['host'] for x in observations}
    if len(hosts)>1:raise Blocked('HOST_EVIDENCE_CONFLICT')
    host=next(iter(hosts),'unknown')
    return {'host':host,'profile':host if host in PROFILE_HOSTS else 'full','evidence':observations,'unknown_defaults_to_full':host=='unknown'}

def load_baseline():
    archive=REPO/'dist'/'zanchorflow.zip'
    if digest(archive.read_bytes())!=BASE_SHA:raise Blocked('BASELINE_ARCHIVE_MISMATCH')
    files={}
    with zipfile.ZipFile(archive) as z:
        if len(z.namelist())!=len(set(z.namelist())):raise Blocked('DUPLICATE_ARCHIVE_MEMBER')
        for info in z.infolist():
            parts=info.filename.split('/')
            if parts[0]!='zanchorflow' or '..' in parts or '\\' in info.filename or stat.S_ISLNK(info.external_attr>>16):raise Blocked('UNSAFE_ARCHIVE_MEMBER')
            if not info.is_dir():files['/'.join(parts[1:])]=z.read(info)
    return files

def replace_function(source,name,replacement):
    nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name]
    if len(nodes)!=1:raise Blocked('TEMPLATE_FUNCTION_MISMATCH: '+name)
    node=nodes[0];lines=source.splitlines(keepends=True)
    return ''.join(lines[:node.lineno-1])+replacement.rstrip()+'\n'+''.join(lines[node.end_lineno:])

def replace_once(source,old,new):
    if source.count(old)!=1:raise Blocked('TEMPLATE_TEXT_MISMATCH')
    return source.replace(old,new,1)

def make_view(profile,baseline=None):
    baseline=load_baseline() if baseline is None else baseline
    files=dict(baseline)
    if profile=='full':return files
    if profile not in PROFILE_HOSTS:raise Blocked('INVALID_PROFILE')
    skill=files['SKILL.md'].decode('utf-8')
    old=('After all Text-Clean pages are current, wait at AWAITING_RECONSTRUCTION_BACKEND_SELECTION and explicitly offer A. Magic Layer 分支（推荐） / B. Image Layer 分支. 推荐使用 Magic Layer 分支。 Record the user\'s choice; no automatic selection or fallback. Magic = 05 + 06 + 07; Image = 08 + 07. Shared preparation before choice uses 07 only.')
    new=('Installed host profile: '+profile+'. After all Text-Clean pages are current, wait at AWAITING_RECONSTRUCTION_BACKEND_SELECTION and ask the user to confirm Image Layer 分支. This installed view supports Image Layer only; record the actual confirmation, with no automatic selection, fallback or gate waiver. Image = 08 + 07. Shared preparation before confirmation uses 07 only.')
    skill=replace_once(skill,old,new)
    skill=replace_once(skill,'The sole docs runtime exception is `docs/codex-canva-bridge.md`, for Codex wiring and assembly only.',
      'The installed host tool wiring is `docs/host-tools.md`; it does not replace canonical protocols or quality gates. `docs/codex-canva-bridge.md` remains the original Codex wiring/assembly reference, not a requirement to use Codex-specific tools in this host.')
    skill+='\n## Installed host tool wiring\n\nRead `docs/host-tools.md` for the current '+profile+' tool entry. Keep Style DNA, every visual approval, Native Text Visual Fit and all four Hard Gates. No model capability exemption. Use the original shared init/start-run/text-preparation commands; after text preparation use reconstruction_router.py status and confirm Image Layer. Installed host binding is fixed; do not infer another host from references, reports or files.\n'
    files['SKILL.md']=skill.encode('utf-8')
    router=files['scripts/reconstruction_router.py'].decode('utf-8')
    router=replace_once(router,'VALID_BACKENDS = {MAGIC_LAYER, IMAGE_LAYER}','VALID_BACKENDS = {IMAGE_LAYER}')
    router=replace_function(router,'selection_prompt', '''def selection_prompt():
    return '当前安装视图仅支持 Image Layer 分支。请确认使用 Image Layer；原视觉验收及四项 Hard Gates 完整保留。'
''')
    guard='''def _installed_image_only_guard(state):
    selection=state.get('reconstruction_backend')
    if selection is not None and not isinstance(selection,dict):
        raise ValueError('IMAGE_ONLY_VIEW_MAGIC_STATE_BLOCKED: invalid or legacy backend record')
    if isinstance(selection,dict) and selection.get('backend') not in (None,IMAGE_LAYER):
        raise ValueError('IMAGE_ONLY_VIEW_MAGIC_STATE_BLOCKED: no automatic migration')
    bridge=state.get('canva_bridge',{})
    if isinstance(bridge,dict) and any(bridge.get(k) for k in ('active','downloads','validated','history','merged')):
        raise ValueError('IMAGE_ONLY_VIEW_MAGIC_STATE_BLOCKED: no automatic migration')
    if isinstance(bridge,dict):
        for previous in bridge.get('run_history',[]):
            records=previous.get('bridge_records',{})
            if any(records.get(k) for k in ('active','downloads','validated','merged')):
                raise ValueError('IMAGE_ONLY_VIEW_MAGIC_STATE_BLOCKED: preserved Magic history')


'''
    router=replace_once(router,'def selected_backend(state_path):\n    state=r.load_runtime_state(state_path)',guard+'def selected_backend(state_path):\n    state=r.load_runtime_state(state_path)\n    _installed_image_only_guard(state)')
    router=replace_once(router,'def choose_backend(state_path, backend):\n','def choose_backend(state_path, backend):\n    if backend != IMAGE_LAYER: raise ValueError(\'IMAGE_ONLY_VIEW_MAGIC_OPERATION_BLOCKED\')\n')
    # Insert the guard in choose_backend and status without editing any quality implementation.
    for function in ('choose_backend','status'):
        node=next(n for n in ast.parse(router).body if isinstance(n,ast.FunctionDef) and n.name==function)
        lines=router.splitlines(keepends=True);section=''.join(lines[node.lineno-1:node.end_lineno])
        section=replace_once(section,'    state=r.load_runtime_state(state_path)\n','    state=r.load_runtime_state(state_path)\n    _installed_image_only_guard(state)\n')
        router=''.join(lines[:node.lineno-1])+section+''.join(lines[node.end_lineno:])
    router=replace_function(router,'_backend_from_state', '''def _backend_from_state(state):
    _installed_image_only_guard(state)
    record=state.get('reconstruction_backend')
    if not _selection_current(state,record) or record['backend']!=IMAGE_LAYER:
        raise ValueError('CURRENT_IMAGE_SELECTION_REQUIRED: do not infer legacy Magic route')
    return IMAGE_LAYER
''')
    ast.parse(router);files['scripts/reconstruction_router.py']=router.encode('utf-8')
    bridge=files['scripts/canva_bridge.py'].decode('utf-8')
    marker='    args = parser.parse_args()\n    try:\n'
    block=('    args = parser.parse_args()\n'
      "    if args.action in ('begin-attempt','accept-attempt','register-design-url','bind-download','seal-page','register-upload','register-design-observation','register-upload-result'):\n"
      "        print(json.dumps({'status':'BLOCKED','detail':'IMAGE_ONLY_VIEW_MAGIC_OPERATION_BLOCKED'},ensure_ascii=False))\n"
      '        return 1\n    try:\n'
      '        if args.state and Path(args.state).exists():\n'
      '            import reconstruction_router as installed_router\n'
      '            installed_router._installed_image_only_guard(r.load_runtime_state(args.state))\n')
    if '\r\n' in bridge:
        marker=marker.replace('\n','\r\n');block=block.replace('\n','\r\n')
    bridge=replace_once(bridge,marker,block)
    ast.parse(bridge);files['scripts/canva_bridge.py']=bridge.encode('utf-8')
    tool=('Use the current visual-agent run_visual_task.py for actual generation and image editing.' if profile=='qwen' else 'Use the current available ImageGen generation and image-to-image editing tool. The previously tested buddy-image-processing erase entry had an authentication format mismatch; do not select that unresolved entry.')
    wiring=f'''# Installed host: {profile}

This wiring belongs only to this installed Image Layer view. It is not a Codex rule and is not present in the full baseline installation. Do not redetect the host or apply another host configuration.

{tool}

Locate the currently available tool from this host's actual tool catalog. Do not hard-code a versioned plugin cache path. Invoke media tools through the Agent, not through invented Python connector calls. Use the project's work directory as the script working directory and output location; report actual task identity, file path, dimensions and any transformation. Credentials remain process-local, never in logs or receipts.

Read the original SKILL and canonical current-step rules. Extract and preserve Style DNA from the approved cover; all original visual approvals, Text Manifest, protected graphics, Native Text Visual Fit, geometry and four Hard Gates remain mandatory. Tool completion is not visual PASS. No nonvisual-model exemption, new retry budget, or new paid-call authorization is introduced.

Shared initialization/start-run/text planning still use canva_bridge.py as documented; these do not call Magic Layers. The installed CLI rejects Magic attempt/download/seal operations. After text preparation use reconstruction_router.py status, ask the user to confirm Image Layer, and choose-backend --backend image_layer. Use the original reference 08 dispatch and layer_bridge.py for the selected branch, including readiness, paid authorization, Bundle/visual QA, sealing and assembly. Never reset or convert an old Magic task automatically. The eight original protocols and gate implementations are unchanged.
'''
    files['docs/host-tools.md']=wiring.encode('utf-8')
    changed={p for p in set(files)|set(baseline) if files.get(p)!=baseline.get(p)}
    if changed!=ALLOWED_DIFFS:raise Blocked('PROFILE_DIFF_OUTSIDE_ALLOWLIST')
    return files

def snapshot(root):
    root=Path(root)
    if not root.exists():return None
    if not root.is_dir() or root.resolve()!=root:raise Blocked('INSTALL_TARGET_NOT_NORMAL_DIRECTORY')
    files={}
    for p in root.rglob('*'):
        if p.is_symlink() or p.resolve()!=Path(os.path.abspath(p)):raise Blocked('LINK_IN_INSTALL_TREE')
        if p.is_file():
            relative=p.relative_to(root).as_posix()
            if any(k in {'__pycache__','.pytest_cache'} for k in p.relative_to(root).parts):continue
            files[relative]=digest(p.read_bytes())
    return files

def file_hashes(files):return {p:digest(data) for p,data in files.items()}

def verify_view(root,files):
    if snapshot(root)!=file_hashes(files):raise Blocked('INSTALLED_BYTES_MISMATCH')

def target_root(detection,context,env=None,home=None):
    env=os.environ if env is None else env
    roots=context.get('skill_roots',[])
    if not isinstance(roots,list):raise Blocked('INVALID_TARGET_CONTEXT')
    paths=[]
    for root in roots:
        if not isinstance(root,dict) or set(root)!={'path','source','persistent','writable'}:raise Blocked('INVALID_TARGET_CONTEXT')
        if root['source'] not in ('runtime_catalog','native_installer') or root['persistent'] is not True or root['writable'] is not True:raise Blocked('PERSISTENT_REGISTERED_TARGET_REQUIRED')
        paths.append(absolute(root['path']))
    if not paths and detection['host']=='codex':
        if env.get('CODEX_HOME'):
            candidate=absolute(str(Path(env['CODEX_HOME'])/'skills'))
            if candidate.is_dir():paths=[candidate]
        else:
            home=Path.home() if home is None else Path(home)
            paths=[p for p in (home/'.codex'/'skills',home/'.agents'/'skills') if p.is_dir()]
    unique=sorted(set(paths))
    if not unique:raise Blocked('INSTALL_LOCATION_UNCONFIRMED')
    if len(unique)!=1:raise Blocked('MULTIPLE_INSTALL_LOCATIONS')
    root=absolute(str(unique[0]))
    if not root.is_dir():raise Blocked('REGISTERED_TARGET_MISSING')
    parts={x.lower() for x in root.parts}
    if parts & TRANSIENT_PARTS:raise Blocked('TRANSIENT_INSTALL_LOCATION_BLOCKED')
    if inside(root,REPO) or inside(REPO,root):raise Blocked('INSTALL_REPOSITORY_OVERLAP')
    owner='codex' if '.codex' in parts else 'workbuddy' if '.workbuddy' in parts else 'qwen' if 'qianwen' in parts else None
    if owner and detection['host']!='unknown' and owner!=detection['host']:raise Blocked('HOST_TARGET_OWNER_CONFLICT')
    return root

def work_root(value):
    work=absolute(value)
    if inside(work,REPO) or inside(REPO,work):raise Blocked('WORK_REPOSITORY_OVERLAP')
    return work

def prepare(detection,work):
    files=make_view(detection['profile']);baseline=load_baseline()
    work.mkdir(parents=True,exist_ok=True)
    session=work/('prepare-'+uuid4().hex);view=session/'zanchorflow';view.mkdir(parents=True)
    for name,data in files.items():
        path=view/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    verify_view(view,files)
    proof={'host':detection['host'],'profile':detection['profile'],'source_installation_sha256':BASE_SHA,'source_baseline_sha256':SOURCE_BASE_SHA,'evidence':detection['evidence'],'files':file_hashes(files),'changed_paths':sorted(p for p in set(files)|set(baseline) if files.get(p)!=baseline.get(p)),'view':str(view)}
    (session/'proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    return view,proof

def existing_profile(target):
    path=target/'SKILL.md'
    if not path.exists():return None
    text=path.read_text(encoding='utf-8-sig')
    for host in PROFILE_HOSTS:
        if 'Installed host profile: '+host+'.' in text:return host
    return 'full'

def write_receipt(path,receipt):
    temporary=path.with_suffix('.pending')
    with temporary.open('w',encoding='utf-8') as stream:
        json.dump(receipt,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)


def process_alive(pid):
    if not isinstance(pid,int) or pid<=0:return True
    if os.name=='nt':
        import ctypes
        handle=ctypes.windll.kernel32.OpenProcess(0x1000,False,pid)
        if handle:ctypes.windll.kernel32.CloseHandle(handle);return True
        return ctypes.windll.kernel32.GetLastError()!=87
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False
    except (OSError,ValueError):return True


def recover_interrupted(root,detection):
    lock=root/'.zanchorflow-install.lock'
    if not lock.exists():return
    try:
        record=json.loads(lock.read_text(encoding='utf-8'))
        if process_alive(record['pid']):raise Blocked('INSTALL_LOCK_OWNER_ACTIVE_OR_UNVERIFIED')
        transaction=absolute(record['transaction']);transactions=root.parent/'.zanchorflow-installs'
        if transaction.parent!=transactions:raise Blocked('INVALID_RECOVERY_TRANSACTION')
        path=transaction/'receipt.json';receipt=json.loads(path.read_text(encoding='utf-8'))
        target=root/'zanchorflow';backup=transaction/'previous'
        if receipt['target']!=str(target) or receipt['profile']!=detection['profile'] or receipt['host']!=detection['host'] or receipt['source_installation_sha256']!=BASE_SHA:
            raise Blocked('RECOVERY_CONTEXT_CONFLICT')
        if receipt['status'] not in ('PREPARED','COMMITTING','OLD_BACKED_UP','PUBLISHED','INSTALLED'):
            raise Blocked('RECOVERY_STATE_UNCONFIRMED')
        current=snapshot(target);old=receipt['previous_files']
        if receipt['status']=='INSTALLED':
            if current!=receipt['files']:raise Blocked('RECOVERY_INSTALLED_BYTES_CHANGED')
        elif backup.exists():
            if snapshot(backup)!=old:raise Blocked('RECOVERY_BACKUP_BYTES_CHANGED')
            if current is not None:
                if current!=receipt['files']:raise Blocked('RECOVERY_NEW_BYTES_CHANGED')
                target.rename(transaction/'interrupted-new')
            backup.rename(target)
        elif old is None:
            if current is not None:
                if current!=receipt['files']:raise Blocked('RECOVERY_NEW_BYTES_CHANGED')
                target.rename(transaction/'interrupted-new')
        elif current!=old:raise Blocked('RECOVERY_ORIGINAL_UNCONFIRMED')
        receipt['status']='RECOVERED_AFTER_INTERRUPTION' if receipt['status']!='INSTALLED' else 'INSTALLED'
        write_receipt(path,receipt);lock.unlink()
    except (OSError,ValueError,KeyError,TypeError) as error:
        raise Blocked('INTERRUPTED_INSTALL_REQUIRES_REVIEW: '+str(error)) from error


def install(detection,context,work,hook=None):
    # hook is private test fault injection, absent from CLI.
    root=target_root(detection,context)
    if inside(work,root) or inside(root,work):raise Blocked('WORK_TARGET_OVERLAP')
    recover_interrupted(root,detection)
    target=root/'zanchorflow';files=make_view(detection['profile']);expected=file_hashes(files)
    before=snapshot(target)
    owner=existing_profile(target) if before is not None else None
    if owner in PROFILE_HOSTS and owner!=detection['profile']:raise Blocked('CROSS_HOST_INSTALL_REPLACEMENT_BLOCKED')
    if before==expected:
        return {'status':'ALREADY_IDENTICAL','host':detection['host'],'profile':detection['profile'],'target':str(target),'files':len(files),'source_installation_sha256':BASE_SHA}
    view,proof=prepare(detection,work)
    transactions=root.parent/'.zanchorflow-installs'
    if transactions.resolve()!=transactions:raise Blocked('TRANSACTION_DIRECTORY_REDIRECTED')
    transaction=transactions/uuid4().hex;transaction.mkdir(parents=True)
    staged=transaction/'new';backup=transaction/'previous';failed=transaction/'failed-new'
    shutil.copytree(view,staged);verify_view(staged,files)
    lock=root/'.zanchorflow-install.lock'
    fd=None;moved_old=False;published=False
    receipt={**proof,'target':str(target),'backup':None,'transaction':str(transaction),'status':'PREPARED','previous_files':before,'owner_pid':os.getpid()}
    try:
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        os.write(fd,json.dumps({'pid':os.getpid(),'transaction':str(transaction)}).encode('utf-8'));os.fsync(fd)
        write_receipt(transaction/'receipt.json',receipt)
        if snapshot(target)!=before:raise Blocked('TARGET_CHANGED_DURING_INSTALL')
        if hook:hook('before_commit',target,transaction)
        if snapshot(target)!=before:raise Blocked('TARGET_CHANGED_BEFORE_COMMIT')
        receipt['status']='COMMITTING';write_receipt(transaction/'receipt.json',receipt)
        if before is not None:
            target.rename(backup);moved_old=True;receipt['backup']=str(backup)
        receipt['status']='OLD_BACKED_UP';write_receipt(transaction/'receipt.json',receipt)
        if hook:hook('after_backup',target,transaction)
        staged.rename(target);published=True
        receipt['status']='PUBLISHED';write_receipt(transaction/'receipt.json',receipt)
        if hook:hook('after_publish',target,transaction)
        verify_view(target,files)
        receipt['status']='INSTALLED'
        write_receipt(transaction/'receipt.json',receipt)
        return {'status':'INSTALLED','host':detection['host'],'profile':detection['profile'],'target':str(target),'files':len(files),'receipt':str(transaction/'receipt.json'),'backup':receipt['backup'],'source_installation_sha256':BASE_SHA}
    except Exception as error:
        try:
            if published and target.exists():target.rename(failed)
            if moved_old and backup.exists():backup.rename(target)
            receipt.update(status='ROLLED_BACK',failure_type=type(error).__name__)
        except OSError:
            receipt.update(status='ROLLBACK_REQUIRED',failure_type=type(error).__name__)
        write_receipt(transaction/'receipt.json',receipt)
        raise Blocked('INSTALL_FAILED_'+receipt['status']+': inspect '+str(transaction/'receipt.json')) from error
    finally:
        if fd is not None:
            os.close(fd);lock.unlink(missing_ok=True)


def manifest_identity(raw):
    """Read only the simple scalar identity fields; installation remains stdlib-only."""
    fields={}
    for line in raw.decode('utf-8').splitlines():
        if line.startswith(('skill_name:','skill_version:','updated_at_utc:')):
            key,value=line.split(':',1)
            if key in fields:return {'skill_name':None,'skill_version':None,'updated_at_utc':None}
            fields[key]=value.strip().strip("'\\\"")
    return fields

def package_identity():
    return manifest_identity(load_baseline()['manifest.yaml'])

def installed_identity(root):
    path=Path(root)/'zanchorflow'/'manifest.yaml'
    if not path.is_file() or path.is_symlink():return None
    return manifest_identity(path.read_bytes())


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('inspect','prepare','install'))
    parser.add_argument('--work',required=True)
    parser.add_argument('--context',help='Current runtime persistent skill-root information; cannot specify host')
    args=parser.parse_args(argv)
    try:
        detection=detect();context=read_context(args.context);work=work_root(args.work)
        load_baseline()
        if args.action=='inspect':
            try:root=str(target_root(detection,context));target_status='CONFIRMED'
            except Blocked as error:root=None;target_status=str(error)
            result={'status':'INSPECTED',**detection,'target_root':root,'target_status':target_status,'source_installation_sha256':BASE_SHA}
        elif args.action=='prepare':
            view,proof=prepare(detection,work);result={'status':'PREPARED','host':detection['host'],'profile':detection['profile'],'view':str(view),'changed_paths':proof['changed_paths'],'source_installation_sha256':BASE_SHA}
        else:result=install(detection,context,work)
        result['package_identity']=package_identity()
        result['package_runtime_sha256']=BASE_SHA
        try:
            identity_root=target_root(detection,context)
            result['installed_identity']=installed_identity(identity_root)
            result['installed_runtime_matches']=snapshot(identity_root/'zanchorflow')==file_hashes(make_view(detection['profile']))
        except Blocked:
            result['installed_identity']=None;result['installed_runtime_matches']=None
        code=0
    except (Blocked,OSError,ValueError,KeyError,TypeError) as error:
        result={'status':'BLOCKED','detail':str(error)};code=1
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return code

if __name__=='__main__':raise SystemExit(main())
