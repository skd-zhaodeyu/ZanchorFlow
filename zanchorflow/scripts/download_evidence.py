"""File-first download evidence. No browser calls, History snapshots or page guessing."""
import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, unquote

IDENTITY_KEYS = ('attempt_id','slide_id','run_id','approved_outline_fingerprint',
                 'source_fingerprint','text_clean_fingerprint','design_id')
POLL_SECONDS = 0.5
RECOVERY_AFTER_SECONDS = 10

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write_once(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    return {'path':str(path.resolve()),'sha256':sha(path)}

def sealed(ref):
    if not isinstance(ref,dict) or sha(ref['path'])!=ref['sha256']:
        raise ValueError('DOWNLOAD_EVIDENCE_CHANGED')
    return read(ref['path'])

def check_identity(actual,expected):
    if not isinstance(actual,dict) or any(actual.get(k)!=expected.get(k) for k in IDENTITY_KEYS):
        raise ValueError('DOWNLOAD_IDENTITY_MISMATCH')

def design_url(url,design_id):
    p=urlsplit(url)
    if (p.scheme!='https' or p.hostname not in ('canva.com','www.canva.com')
        or p.username is not None or p.password is not None or p.port not in (None,443)
        or p.path.split('/')[1:3]!=['design',design_id]
        or any(ord(c)<33 or ord(c)==127 for c in url)):
        raise ValueError('DOWNLOAD_DESIGN_URL_MISMATCH')

def recovery_url(url,design_id):
    p=urlsplit(url)
    if (p.scheme!='https' or p.hostname!='export-download.canva.com'
        or p.username is not None or p.password is not None or p.port not in (None,443)
        or p.path.split('/')[2:3]!=[design_id] or not p.path.lower().endswith('.pptx')
        or any(ord(c)<33 or ord(c)==127 for c in url)):
        raise ValueError('RECOVERY_DESIGN_ID_MISMATCH')
    # Preserve the path and digest rather than expiring signed query parameters in logs.
    result={'host':p.hostname,'path':p.path,'url_sha256':hashlib.sha256(url.encode()).hexdigest()}
    fields=parse_qs(p.query,max_num_fields=64)
    header=fields.get('response-content-disposition',[None])[0]
    if header:
        match=re.search(r"filename\*\s*=\s*UTF-8''([^;]+)",header,re.I)
        if match:name=unquote(match.group(1).strip().strip('"'))
        else:
            match=re.search(r'filename\s*=\s*"?([^";]+)',header,re.I)
            name=match.group(1).strip() if match else None
        if name:
            if (Path(name).name!=name or any(c in name for c in '/\\<>:"|?*')
                or any(ord(c)<32 for c in name) or not name.lower().endswith('.pptx')):
                raise ValueError('unsafe actual export filename')
            result['filename']=name
    return result

def title_for(slide_id,attempt_id,image_sha256):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,24}',slide_id):raise ValueError('invalid slide id for title')
    if not re.fullmatch(r'[a-f0-9]{32}',attempt_id) or not re.fullmatch(r'[a-f0-9]{64}',image_sha256):
        raise ValueError('invalid attempt or image hash')
    # Full attempt UUID avoids collision expansion and stays below common title limits.
    return 'zf-'+slide_id+'-a'+attempt_id+'-c'+image_sha256[:12]

def inventory(directory,digest=True):
    directory=Path(directory).resolve()
    if not directory.is_dir():raise ValueError('actual download directory must exist')
    rows=[]
    for p in sorted(directory.iterdir()):
        if not p.is_file() or p.is_symlink():continue
        if p.suffix.lower() not in ('.pptx','.crdownload','.part','.download','.tmp'):continue
        try:
            st=p.stat();file_digest=sha(p) if digest and p.suffix.lower()=='.pptx' else None
            end=p.stat()
            if (st.st_size,st.st_mtime_ns)!=(end.st_size,end.st_mtime_ns):file_digest=None
            rows.append({'path':str(p),'bytes':end.st_size,'mtime_ns':end.st_mtime_ns,
                         'sha256':file_digest})
        except (OSError,PermissionError):
            rows.append({'path':str(p),'bytes':None,'mtime_ns':None,'sha256':None})
    return rows

def changes(before,after):
    old={r['path']:r for r in before}
    return [r for r in after if r['path'] not in old or any(
        r.get(k)!=old[r['path']].get(k) for k in ('bytes','mtime_ns','sha256'))]

def owned_name(path,title):
    # Only exact observed ASCII title plus the browser's numeric duplicate suffix.
    return re.fullmatch(re.escape(title)+r'(?: \([1-9][0-9]*\))?\.pptx',Path(path).name,re.I) is not None

def acquire_lease(directory,lease_dir,acquisition_id):
    lease_dir=Path(lease_dir).resolve();lease_dir.mkdir(parents=True,exist_ok=True)
    key=hashlib.sha256(os.path.normcase(str(Path(directory).resolve())).encode()).hexdigest()
    path=lease_dir/(key+'.json')
    if path.exists():
        if read(path).get('acquisition_id')!=acquisition_id:raise ValueError('DOWNLOAD_DIRECTORY_IN_USE')
    else:
        write_once(path,{'acquisition_id':acquisition_id,'directory':str(Path(directory).resolve())})
    return str(path)

def release_lease(path,acquisition_id):
    p=Path(path)
    if p.exists():
        if read(p).get('acquisition_id')!=acquisition_id:raise ValueError('DOWNLOAD_LEASE_IDENTITY_CHANGED')
        p.unlink()

def make_snapshot(record,context,directory,lease_dir,action,path):
    if action not in ('normal','recovery','direct','export_retry'):raise ValueError('unsupported acquisition action')
    check_identity(context['identity'],record['identity'])
    directory=Path(directory).resolve()
    lease=acquire_lease(directory,lease_dir,record['acquisition_id'])
    value={'schema_version':2,'acquisition_id':record['acquisition_id'],'identity':record['identity'],
           'context':context,'directory':str(directory),'action':action,'captured_ns':time.time_ns(),
           'lease_path':lease,'files':inventory(directory)}
    return write_once(path,value)

def observe_snapshot(ref,record,validator,wait_seconds=10,export_observation=None):
    if not 0<=wait_seconds<=120:raise ValueError('observation must be 0..120 seconds')
    snap=sealed(ref);check_identity(snap['identity'],record['identity'])
    if snap['acquisition_id']!=record['acquisition_id']:raise ValueError('snapshot belongs to another acquisition')
    deadline=time.monotonic()+wait_seconds;previous={};samples={}
    # Three consecutive read samples, including content digest, prevent partial-file success.
    while True:
        rows=inventory(snap['directory']);delta=changes(snap['files'],rows);complete=[];started=[];invalid=[]
        for row in delta:
            p=Path(row['path']);title=snap['context']['actual_title']
            actual=(export_observation or snap['context'].get('recovery_export') or {}).get('filename')
            if actual:title=Path(actual).stem
            if not owned_name(p,title):continue
            started.append(row)
            sig=(row['bytes'],row['mtime_ns'],row['sha256'])
            samples[str(p)]=samples.get(str(p),0)+1 if previous.get(str(p))==sig else 1
            previous[str(p)]=sig
            if not row['bytes'] or not row['sha256'] or samples[str(p)]<3:continue
            if any(Path(str(p)+s).exists() for s in ('.crdownload','.part','.download','.tmp')):continue
            try:validator(p)
            except ValueError as error:invalid.append({'path':str(p),'error':str(error)});continue
            if sha(p)!=row['sha256']:continue
            complete.append(row)
        hashes={r['sha256'] for r in complete}
        if len(hashes)>1:
            return {'status':'SOURCE_AMBIGUOUS','snapshot':ref,'candidates':complete,'delta':delta}
        if complete:
            # Byte-identical copies are logged, not mistaken for separate design identities.
            selected=sorted(complete,key=lambda r:(r['mtime_ns'],r['path']))[0]
            return {'status':'FILE_COMPLETE','snapshot':ref,'selected':selected,'duplicates':[r for r in complete if r['path']!=selected['path']],
                    'delta':delta,'observed_ns':time.time_ns()}
        partial=any(Path(r['path']).name.startswith(Path((export_observation or snap['context'].get('recovery_export') or {}).get('filename',snap['context']['actual_title'])).stem)
                    and not str(r['path']).lower().endswith('.pptx') for r in delta)
        if time.monotonic()>=deadline:
            return {'status':'FILE_IN_PROGRESS' if started or partial else 'NO_FILE_STARTED',
                    'snapshot':ref,'delta':delta,'invalid':invalid,'observed_ns':time.time_ns()}
        time.sleep(min(POLL_SECONDS,max(0,deadline-time.monotonic())))

def validate_file_proof(proof,identity,final_path=None):
    if proof.get('schema_version')!=2:raise ValueError('unsupported file evidence version')
    check_identity(proof['identity'],identity)
    snap=sealed(proof['snapshot']);check_identity(snap['identity'],identity)
    if proof['acquisition_id']!=snap['acquisition_id']:raise ValueError('file acquisition mismatch')
    context=snap['context'];design_url(context['observed_url'],identity['design_id'])
    observed=sealed(context['design_observation']);check_identity(observed['identity'],identity)
    if observed['actual_title']!=context['actual_title']:raise ValueError('design title evidence changed')
    lookup=sealed(observed['lookup']);design=lookup['response']['design']
    if lookup['identity']!=identity or design['id']!=identity['design_id'] or design.get('page_count')!=1:
        raise ValueError('trusted design observation mismatch')
    actual_title=design.get('title')
    if actual_title is None:
        host=sealed(observed['host_title']);check_identity(host['identity'],identity)
        design_url(host['observed_url'],identity['design_id'])
        capture=sealed(host['capture'])
        if (host.get('source')!='canva_host.readonly' or capture.get('observed_url')!=host['observed_url']
            or capture.get('actual_title')!=host.get('actual_title')):raise ValueError('Host title evidence mismatch')
        actual_title=host['actual_title']
    if actual_title!=context['actual_title']:raise ValueError('actual design title changed')
    if snap['action']=='recovery':
        evidence=context.get('recovery_export')
        if (not evidence or evidence['host']!='export-download.canva.com'
            or evidence['path'].split('/')[2:3]!=[identity['design_id']]):raise ValueError('recovery source mismatch')
    selected=proof['selected'];old={r['path']:r for r in snap['files']}.get(selected['path'])
    if old is not None and all(old.get(k)==selected.get(k) for k in ('bytes','mtime_ns','sha256')):
        raise ValueError('unchanged old file is not new download evidence')
    export=proof.get('export_observation') or context.get('recovery_export')
    title=context['actual_title']
    if export:
        if export.get('host')!='export-download.canva.com' or export['path'].split('/')[2:3]!=[identity['design_id']]:
            raise ValueError('actual export belongs to another design_id')
        if export.get('filename'):title=Path(export['filename']).stem
    if not owned_name(selected['path'],title):raise ValueError('download name does not belong to current design export')
    if Path(selected['path']).parent.resolve()!=Path(snap['directory']).resolve():raise ValueError('file outside actual directory')
    target=Path(final_path or selected['path'])
    if target.stat().st_size!=selected['bytes'] or sha(target)!=selected['sha256']:raise ValueError('download bytes changed')
    return snap


def source_association(proof,identity,context,file_path):
    """Completion is separate from source association; visual MATCH alone is insufficient."""
    marker='a'+identity['attempt_id']
    name=Path(proof['selected']['path']).stem
    if marker in name and owned_name(proof['selected']['path'],context['actual_title']):return 'unique_attempt_filename'
    if proof.get('download_event_confirmed') and proof.get('event_path'):
        if Path(proof['event_path']).resolve()==Path(proof['selected']['path']).resolve():return 'same_operation_host_event_path'
    import zipfile,xml.etree.ElementTree as ET
    with zipfile.ZipFile(file_path) as archive:
        if 'docProps/core.xml' in archive.namelist():
            title=ET.fromstring(archive.read('docProps/core.xml')).find('{http://purl.org/dc/elements/1.1/}title')
            if title is not None and title.text==context['actual_title']:return 'unique_design_core_title'
    raise ValueError('SOURCE_ASSOCIATION_PENDING: file downloaded; generic export name and visual similarity alone cannot establish design identity')


def returned_design_id(raw):
    """Extract actual result IDs, not the controller's proposed acceptance identity."""
    ids=set()
    def visit(value):
        if isinstance(value,dict):
            if isinstance(value.get('design_id'),str):ids.add(value['design_id'])
            design=value.get('design')
            if isinstance(design,dict) and isinstance(design.get('id'),str):ids.add(design['id'])
            if value.get('type')=='text' and isinstance(value.get('text'),str):
                try:visit(json.loads(value['text']))
                except ValueError:pass
            for child in value.values():
                if isinstance(child,(dict,list)):visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    if isinstance(raw,dict) and raw.get('isError'):raise ValueError('tool returned an error, not an assessable design')
    visit(raw)
    if len(ids)!=1 or not re.fullmatch(r'[A-Za-z0-9_-]+',next(iter(ids),'')):
        raise ValueError('actual tool result must identify exactly one design_id; inspect raw result, do not guess')
    return next(iter(ids))

def validate_transport_proof(proof,identity,final_path=None):
    """New receipt route, independent of filename/title/visual evidence."""
    check_identity(proof['identity'],identity)
    if proof.get('schema_version')!=2:raise ValueError('unsupported completion evidence version')
    snap=sealed(proof['snapshot']);check_identity(snap['identity'],identity)
    if proof['acquisition_id']!=snap['acquisition_id']:raise ValueError('acquisition mismatch')
    context=snap['context'];design_url(context['observed_url'],identity['design_id'])
    observation=sealed(context['design_observation']);check_identity(observation['identity'],identity)
    lookup=sealed(observation['lookup'])
    if lookup.get('identity')!=identity or lookup['response']['design'].get('id')!=identity['design_id'] or lookup['response']['design'].get('page_count')!=1:
        raise ValueError('trusted design observation mismatch')
    receipt=sealed(proof['transport_receipt'])
    check_identity(receipt['identity'],identity)
    if receipt.get('acquisition_id')!=proof['acquisition_id'] or receipt.get('result')!='PASS':
        raise ValueError('transport receipt mismatch')
    if receipt.get('observed_url')!=context['observed_url']:raise ValueError('receipt page mismatch')
    source=receipt.get('source')
    if source and (source.get('host')!='export-download.canva.com' or source.get('path','').split('/')[2:3]!=[identity['design_id']]):
        raise ValueError('transport design mismatch')
    selected=proof['selected']
    if receipt.get('method')=='direct':
        if not source or receipt.get('status_code')!=200 or receipt.get('get_count')!=1:
            raise ValueError('invalid direct response')
        if receipt.get('received_bytes')!=selected['bytes'] or receipt.get('stream_sha256')!=selected['sha256']:
            raise ValueError('direct stream mismatch')
        if receipt.get('content_length') is not None and receipt['content_length']!=selected['bytes']:
            raise ValueError('direct Content-Length mismatch')
        final=receipt.get('final_source')
        if not final or final.get('host')!='export-download.canva.com' or final.get('path','').split('/')[2:3]!=[identity['design_id']]:
            raise ValueError('direct redirect source mismatch')
    elif receipt.get('method')=='browser':
        operation=sealed(receipt['operation_capture'])
        check_identity(operation['identity'],identity)
        design_url(operation['observed_url'],identity['design_id'])
        if (operation.get('source')!='canva_host.download' or operation.get('acquisition_id')!=proof['acquisition_id']
            or operation.get('observed_url')!=context['observed_url'] or not operation.get('operation_id')
            or operation.get('action') not in ('normal','recovery') or operation.get('action')!=browser_action(snap['action'])):
            raise ValueError('invalid actual browser operation capture')
        if operation.get('path'):
            if Path(operation['path']).resolve()!=Path(selected['path']).resolve():raise ValueError('browser path mismatch')
        elif operation.get('exclusive_directory'):
            if (Path(operation['exclusive_directory']).resolve()!=Path(snap['directory']).resolve()
                or snap['files'] or len(proof.get('candidates',[]))!=1
                or not operation.get('directory_owned_by_operation')):
                raise ValueError('exclusive operation directory not established')
        else:raise ValueError('SOURCE_ASSOCIATION_PENDING')
        if source:
            if operation.get('export_source')!=source:raise ValueError('browser export changed')
        old={x['path']:x for x in snap['files']}.get(selected['path'])
        if old is not None and all(old.get(k)==selected.get(k) for k in ('bytes','mtime_ns','sha256')):
            raise ValueError('unchanged old file')
    else:raise ValueError('unsupported transport method')
    if receipt.get('path')!=selected['path'] or receipt.get('bytes')!=selected['bytes'] or receipt.get('sha256')!=selected['sha256'] or receipt.get('slide_count')!=1:
        raise ValueError('receipt/file mismatch')
    if Path(selected['path']).parent.resolve()!=Path(snap['directory']).resolve():
        raise ValueError('file outside acquisition directory')
    from download_transport import validate_pptx
    checked=validate_pptx(final_path or selected['path'],1)
    if checked['bytes']!=selected['bytes'] or checked['sha256']!=selected['sha256']:raise ValueError('download bytes changed')
    return snap

def browser_action(action):
    if action=='export_retry':return 'normal'
    if action in ('normal','recovery'):return action
    raise ValueError('unsupported browser acquisition action')


def observe_transport_snapshot(ref,record,wait_seconds=10,completed_paths=None):
    """Stat polling; hash only stable candidates. No title-based filtering."""
    if not 0<=wait_seconds<=120:raise ValueError('observation must be 0..120 seconds')
    snap=sealed(ref);check_identity(snap['identity'],record['identity'])
    if snap['acquisition_id']!=record['acquisition_id']:raise ValueError('acquisition mismatch')
    old={r['path']:r for r in snap['files']}
    deadline=time.monotonic()+wait_seconds;previous={};samples={};checked={}
    completed={str(Path(x).resolve()) for x in (completed_paths or [])}
    while True:
        rows=inventory(snap['directory'],False)
        delta=[r for r in rows if r['path'] not in old or any(r.get(k)!=old[r['path']].get(k) for k in ('bytes','mtime_ns'))]
        complete=[];invalid=[];growing=[];pending=[]
        for row in delta:
            path=Path(row['path']);signature=(row['bytes'],row['mtime_ns'])
            prior=previous.get(str(path))
            if prior is not None and prior!=signature:growing.append(row)
            if path.suffix.lower() in ('.crdownload','.part','.download','.tmp'):pending.append(row)
            samples[str(path)]=samples.get(str(path),0)+1 if prior==signature else 1
            previous[str(path)]=signature
            if path.suffix.lower()!='.pptx' or not row['bytes'] or samples[str(path)]<3:continue
            if any(Path(str(path)+suffix).exists() for suffix in ('.crdownload','.part','.download','.tmp')):
                pending.append(row);continue
            try:
                if checked.get(str(path),{}).get('signature')!=signature:
                    from download_transport import validate_pptx
                    checked[str(path)]={'signature':signature,'file':validate_pptx(path,1)}
                result=checked[str(path)]['file']
                end=path.stat()
                if (end.st_size,end.st_mtime_ns)!=signature:continue
                complete.append({**row,'sha256':result['sha256']})
            except (ValueError,OSError,__import__('zipfile').BadZipFile) as error:
                invalid.append({'path':str(path),'error':type(error).__name__})
        if complete:return {'status':'FILE_COMPLETE','snapshot':ref,'selected':complete[0],
            'candidates':complete,'duplicates':complete[1:],'delta':delta,'observed_ns':time.time_ns()}
        if time.monotonic()>=deadline:
            confirmed=[x for x in invalid if str(Path(x['path']).resolve()) in completed]
            status=('NO_FILE_STARTED' if not delta else
                    'FILE_IN_PROGRESS' if growing or pending else
                    'FILE_INVALID' if confirmed else 'FILE_UNVERIFIED')
            return {'status':status,'snapshot':ref,'delta':delta,'invalid':invalid,
                'completed_invalid':confirmed,'growing':growing,'pending':pending,'observed_ns':time.time_ns()}
        time.sleep(min(POLL_SECONDS,max(0,deadline-time.monotonic())))
