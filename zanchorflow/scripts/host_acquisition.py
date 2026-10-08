"""Local evidence/intent helpers. Browser actions belong exclusively to Host tools."""
import base64
import subprocess
import sys
import argparse
import json
import os
import re
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time
from urllib.parse import urlsplit
import uuid
import canva_bridge as bridge
import runtime
import acquisition_request
import download_transport as transport

QUERY_RETRY_DELAYS = (1, 2, 4, 8)
UI_RETRY_DELAYS = (1, 2, 4, 8)
POST_CLICK_OBSERVE_DELAYS = (1, 2, 4, 8)



def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def _save(path,data):
    path=Path(path)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temp.open('x',encoding='utf-8') as out:
            json.dump(data,out,ensure_ascii=False,indent=2);out.flush();os.fsync(out.fileno())
        os.replace(temp,path)
    finally:
        if temp.exists():temp.unlink()

def ready(path,request):
    if request.get('status')!='WAIT_DOWNLOAD':raise ValueError('WAIT_DOWNLOAD required')
    record={'acquisition_id':uuid.uuid4().hex,'identity':request['identity'],
            'edit_url':request['edit_url'],'status':'READY','download_path':None,
            'sha256':None,'download_evidence':None,'failure_checkpoint':None,
            'require_transport_receipt':True}
    with Path(path).open('x',encoding='utf-8') as out:json.dump(record,out,indent=2)
    return record

def lock(path):
    record=_read(path)
    if record['status']!='READY':raise ValueError('final download may not be repeated')
    # Exclusive marker survives an interruption between claiming intent and saving record.
    marker=Path(str(path)+'.intent')
    try:
        with marker.open('x',encoding='utf-8') as out:
            out.write(record['acquisition_id']);out.flush();os.fsync(out.fileno())
    except FileExistsError as error:raise ValueError('download intent already locked') from error
    record.update(status='INTENT_LOCKED',locked_at_chrome=int((time.time()+11644473600)*1000000))
    _save(path,record)
    return record

def fail(path,checkpoint):
    record=_read(path);record.update(status='FAILED',failure_checkpoint=checkpoint)
    _save(path,record)
    return record

def _history(profile,workdir,start_time=0):
    """Optional bounded readonly rows. Never copy History, use immutable, or stop the browser."""
    db=sqlite3.connect((Path(profile)/'History').resolve().as_uri()+'?mode=ro',uri=True,timeout=1)
    db.row_factory=sqlite3.Row
    try:
        rows=[dict(row) for row in db.execute(
            'select id,guid,target_path,state,received_bytes,total_bytes,tab_url,start_time from downloads where start_time>=? order by start_time,id limit 6',(start_time,))]
        tables={row['name'] for row in db.execute("select name from sqlite_master where type='table'")}
        for row in rows:
            row['url_chain']=[]
            if 'downloads_url_chains' in tables:
                row['url_chain']=[item['url'] for item in db.execute('select url from downloads_url_chains where id=? order by chain_index limit 16',(row['id'],))]
        return rows
    finally:db.close()


def _trusted_canva_url(url):
    if not isinstance(url,str) or not url:return False
    parsed=urlsplit(url)
    host=(parsed.hostname or '').lower()
    return (parsed.scheme=='https' and (host=='canva.com' or host.endswith('.canva.com'))
            and parsed.username is None and parsed.password is None and parsed.port in (None,443)
            and not any(ord(ch)<33 or ord(ch)==127 for ch in url))


def _design_provenance(row,observed_url,design_id):
    if row.get('tab_url')==observed_url:
        return {'method':'tab_url','design_id':design_id,'evidence_url':observed_url}
    # A nonblank mismatched tab_url is contradictory evidence and may not fall back.
    if row.get('tab_url') not in (None,''):
        return None
    matches=[]
    for url in row.get('url_chain') or []:
        if not _trusted_canva_url(url):continue
        # Match the opaque design id as a complete URL token, not a substring.
        if design_id in re.split(r'[^A-Za-z0-9_-]+',url):matches.append(url)
    unique=list(dict.fromkeys(matches))
    if not unique:return None
    return {'method':'recovery_download_url','design_id':design_id,'evidence_url':unique[0]}


def acquire(path,state_path,profile,observed_url,event_confirmed=False,file_evidence=None):
    record=_read(path);identity=record['identity']
    if record['status'] not in ('INTENT_LOCKED','FAILED') or not Path(str(path)+'.intent').exists():
        raise ValueError('original download intent lock required')
    if file_evidence is not None:
        return acquire_files(path,state_path,file_evidence,event_confirmed)
    if record.get('require_transport_receipt'):raise ValueError('TRANSPORT_RECEIPT_REQUIRED: observe files or use direct; History is optional')
    state=runtime.load_runtime_state(state_path)
    if identity!=bridge.active_identity(state,identity['slide_id']):raise ValueError('current identity mismatch')
    if bridge.status(state_path).get('status')!='WAIT_DOWNLOAD':raise ValueError('WAIT_DOWNLOAD required')
    parsed=urlsplit(observed_url)
    if (parsed.scheme!='https' or parsed.hostname not in ('www.canva.com','canva.com')
        or parsed.username is not None or parsed.password is not None or parsed.port not in (None,443)
        or any(ord(ch)<33 or ord(ch)==127 for ch in observed_url)
        or parsed.path.split('/')[1:3]!=['design',identity['design_id']]):
        raise ValueError('resolved Design URL identity mismatch')
    profile=Path(profile).resolve()
    preferences=_read(profile/'Preferences')
    directory=preferences.get('download',{}).get('default_directory')
    if not isinstance(directory,str) or not Path(directory).is_absolute():
        raise ValueError('actual browser default directory not established')
    candidates=[]
    for row in _history(profile,Path(path).resolve().parent,record['locked_at_chrome']):
        if row['start_time']<record['locked_at_chrome']:continue
        provenance=_design_provenance(row,observed_url,identity['design_id'])
        if provenance is not None:candidates.append((row,provenance))
    if not candidates:raise ValueError('same-design download record pending')
    if len(candidates)!=1:raise ValueError('exactly one same-design download record required')
    row,provenance=candidates[0];file=Path(row['target_path'])
    selected={k:row[k] for k in ('id','guid','target_path','tab_url','start_time')}
    selected.update(browser_profile=str(profile),design_provenance=provenance)
    if 'selected_download' in record and record['selected_download']!=selected:
        raise ValueError('same-download record identity changed')
    if 'selected_download' not in record:
        record['selected_download']=selected
        _save(path,record)
    if row['state'] not in (0,1):raise ValueError('download cancelled or interrupted')
    if not file.is_absolute() or row['state']!=1 or not file.is_file():raise ValueError('completed exact download required')
    size=file.stat().st_size
    if not size or size!=row['received_bytes'] or size!=row['total_bytes']:
        raise ValueError('download bytes do not match precise file')
    bridge.single_page(file)
    record.update(status='ACQUIRED',download_path=str(file),sha256=bridge.sha(file),failure_checkpoint=None,
        download_evidence={'download_event_confirmed':bool(event_confirmed),'browser_profile':str(profile),
                           'browser_default_directory':directory,'download_record':row,
                           'design_provenance':provenance})
    _save(path,record)
    return record


def _identity(path,state_path,slide_id):
    identity=bridge.active_identity(runtime.load_runtime_state(state_path),slide_id)
    if Path(path).exists() and _read(path)['identity']!=identity:
        raise ValueError('current acquisition identity mismatch')
    return identity


def reserve_retry(path,state_path,slide_id,kind):
    """Record guidance reservations, not actual requests/clicks; no refusal budget."""
    delays={'query':QUERY_RETRY_DELAYS,'ui':UI_RETRY_DELAYS,'observe':POST_CLICK_OBSERVE_DELAYS}
    if kind not in delays:raise ValueError('unsupported retry kind')
    identity=_identity(path,state_path,slide_id)
    if bridge.status(state_path).get('status')!='WAIT_DOWNLOAD':raise ValueError('WAIT_DOWNLOAD required')
    intent=Path(str(path)+'.intent').exists()
    if kind=='observe' and not intent:raise ValueError('observe retry requires locked download intent')
    budget_path=Path(str(path)+'.retries.json')
    budget=_read(budget_path) if budget_path.exists() else {'identity':identity,'query':0,'ui':0,'observe':0}
    if budget['identity']!=identity:raise ValueError('retry identity mismatch')
    for key in delays:budget.setdefault(key,0)
    count=budget[kind]
    budget[kind]=count+1
    _save(budget_path,budget)
    return {'status':'RETRY_RESERVED','retry_number':count+1,'wait_seconds':delays[kind][min(count,len(delays[kind])-1)]}


def _strategy_record(record, strategy, fallback_reason, intent_locked):
    """Local audit metadata only; never confers click/retry permissions."""
    import copy
    from datetime import datetime, timezone
    result = copy.deepcopy(record)
    if strategy is None:
        if fallback_reason is not None:
            raise ValueError('fallback reason requires explicit host strategy')
        return result
    if strategy not in ('dom_event', 'legacy_observation','direct','browser'):
        raise ValueError('unsupported host strategy')
    if fallback_reason is not None and (not isinstance(fallback_reason,str) or not fallback_reason.strip()):
        raise ValueError('nonempty fallback reason required')
    previous = result.get('host_strategy')
    reason = fallback_reason or ''
    if previous and previous['strategy'] != strategy and not reason:
        raise ValueError('strategy switch requires observed fallback reason')
    phase = 'recovery' if intent_locked else 'pre_download'
    event = {'strategy':strategy, 'reason':reason, 'phase':phase}
    if previous is None or any(previous.get(k) != v for k,v in event.items()):
        event['recorded_at_utc'] = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        result.setdefault('host_strategy_history',[]).append(event)
        result['host_strategy'] = event.copy()
    return result


def prepare(path,state_path,slide_id,lookup_path,target_dir,target_name,host_strategy=None,fallback_reason=None):
    identity=_identity(path,state_path,slide_id)
    req=acquisition_request.request(state_path,slide_id,lookup_path,target_dir)
    # Validate the evidence needed by later provenance registration before Download.
    bridge._lookup_url(_read(lookup_path),identity)
    name=Path(target_name)
    if (not target_name or name.name!=target_name or target_name in ('.','..')
            or not target_name.lower().endswith('.pptx') or any(c in target_name for c in '<>:"/\\|?*')):
        raise ValueError('simple PPTX target filename required')
    _strategy_record(_read(path) if Path(path).exists() else {},host_strategy,fallback_reason,Path(str(path)+'.intent').exists())
    record=_read(path) if Path(path).exists() else ready(path,req)
    planned={'download_target_dir':str(Path(target_dir).resolve()),'target_filename':target_name,
             'lookup_path':req['lookup_path'],'lookup_sha256':req['lookup_sha256']}
    if 'request' in record and record['request']!=planned:
        raise ValueError('fixed acquisition request cannot change on recovery')
    if record['edit_url']!=req['edit_url']:raise ValueError('fixed connector URL changed')
    record=_strategy_record(record,host_strategy,fallback_reason,Path(str(path)+'.intent').exists())
    record['request']=planned
    _save(path,record)
    return record


def acquire_wait(path,state_path,profile,observed_url,event_confirmed,wait_seconds=120):
    record=_read(path)
    record['completion_deadline']=time.time()+wait_seconds
    _save(path,record)
    pending=('same-design download record pending','completed exact download required','download bytes do not match precise file')
    initial=True
    while True:
        if not initial and time.time()>=record['completion_deadline']:
            raise ValueError('same-download completion timeout')
        initial=False
        try:return acquire(path,state_path,profile,observed_url,event_confirmed)
        except ValueError as error:
            if str(error) not in pending:raise
            remaining=record['completion_deadline']-time.time()
            if remaining<=0:raise ValueError('same-download completion timeout') from error
            time.sleep(min(2,remaining))


def _finalize(file,target_dir,target_name,python_executable):
    # Supported local PowerShell only; no Python Browser API or process enumeration.
    quote=lambda value: "'"+str(value).replace("'","''")+"'"
    script=Path(__file__).with_name('canva_pptx_finalize.ps1')
    command="$ErrorActionPreference='Stop'; & "+quote(script)+" -DownloadedFile "+quote(file)+" -OutputDirectory "+quote(target_dir)+" -TargetFileName "+quote(target_name)+" -PythonExecutable "+quote(python_executable)+" | ConvertTo-Json -Compress"
    encoded=base64.b64encode(command.encode('utf-16le')).decode('ascii')
    result=subprocess.run([shutil.which('pwsh') or shutil.which('powershell') or 'powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',encoded],capture_output=True,text=True,encoding='utf-8',errors='replace')
    if result.returncode:raise ValueError('finalizer failed: '+result.stderr.strip())
    return json.loads(result.stdout.lstrip('\ufeff'))


@transport.validation_operation
def finish(path,state_path,profile,observed_url,event_confirmed=False,python_executable=None,wait_seconds=120,file_evidence=None):
    started=time.monotonic()
    record=_read(path);identity=_identity(path,state_path,record['identity']['slide_id'])
    state=runtime.load_runtime_state(state_path)
    binding=state.get('canva_bridge',{}).get('downloads',{}).get(identity['slide_id'])
    if binding is not None:
        bound=bridge.download_current(state,identity['slide_id'])
        if record.get('sha256')!=bound['sha256'] or record.get('finalizer',{}).get('Path')!=bound['path']:
            raise ValueError('existing binding does not belong to this acquisition')
        if record.get('lease_path'):
            import download_evidence as de
            for lease in set(record.get('lease_paths',[])+[record['lease_path']]):de.release_lease(lease,record['acquisition_id'])
        return {'status':'DOWNLOAD_BOUND','path':bound['path'],'sha256':bound['sha256'],'reused':True}
    if not Path(str(path)+'.intent').exists():raise ValueError('original intent required')
    req=record.get('request')
    if not req:raise ValueError('prepare request required')
    if bridge.sha(req['lookup_path'])!=req['lookup_sha256']:raise ValueError('trusted lookup changed')
    bridge._lookup_url(_read(req['lookup_path']),identity)
    checkpoint='ACQUIRE'
    try:
        if record.get('download_evidence') is None:
            record=(acquire_files(path,state_path,file_evidence,event_confirmed) if file_evidence is not None else
                    acquire_wait(path,state_path,profile,observed_url,event_confirmed,wait_seconds))
        payload=record['download_evidence']
        if payload.get('schema_version')==2:
            import download_evidence as de
            de.design_url(observed_url,identity['design_id'])
            snap=de.sealed(payload['snapshot'])
            de.design_url(snap['context']['observed_url'],identity['design_id'])
            # Benign edit/share URL token changes do not change design_id; retain original evidence.
            # Source may already have been moved by an interrupted finalizer.
            source=Path(record['download_path']);target=Path(req['download_target_dir'])/req['target_filename']
            bridge.validate_completion_evidence(state,identity,payload,source if source.exists() else target)
        else:
            current_provenance=_design_provenance(payload['download_record'],observed_url,identity['design_id'])
            if current_provenance is None or current_provenance!=payload.get('design_provenance'):
                raise ValueError('original observed Design URL/provenance changed')
        checkpoint='FINALIZER'
        target=Path(req['download_target_dir'])/req['target_filename']
        source=Path(record['download_path']);digest=record['sha256']
        if 'finalizer' not in record:
            if 'finalizer_intent' not in record:
                if bridge.sha(source)!=digest:raise ValueError('download changed')
                if target.exists() and target.resolve()!=source.resolve():raise ValueError('refusing existing target')
                record['finalizer_intent']={'target_path':str(target),'sha256':digest}
                _save(path,record)
            if record['finalizer_intent']!={'target_path':str(target),'sha256':digest}:
                raise ValueError('finalizer intent mismatch')
            if not source.exists() and target.is_file():
                bridge.single_page(target)
                if bridge.sha(target)!=digest:raise ValueError('moved file changed')
                final={'Status':'RecoveredExactMove','Path':str(target),'SHA256':digest,'ValidPptx':True,'SlideCount':1}
            else:
                if bridge.sha(source)!=digest:raise ValueError('download changed')
                final=_finalize(source,req['download_target_dir'],req['target_filename'],python_executable or sys.executable)
            if (final.get('ValidPptx') is not True or final.get('SlideCount')!=1
                or Path(final['Path']).resolve()!=target.resolve() or final['SHA256'].lower()!=digest):
                raise ValueError('finalizer result mismatch')
            record['finalizer']=final;_save(path,record)
        final=record['finalizer'];exact=Path(final['Path'])
        bridge.single_page(exact)
        if bridge.sha(exact)!=digest:raise ValueError('finalized file changed')
        _identity(path,state_path,identity['slide_id'])
        checkpoint='BIND'
        bridge.register_design_url(state_path,identity['slide_id'],req['lookup_path'])
        evidence={k:identity[k] for k in ('attempt_id','slide_id','design_id')}
        evidence.update(edit_url=record['edit_url'],pptx_sha256=digest,
            download_entry='Canva PowerPoint; '+observed_url,
            completion_evidence=json.dumps(record['download_evidence'],ensure_ascii=False))
        evidence_path=Path(str(path)+'.binding.json');_save(evidence_path,evidence)
        bridge.bind_download(state_path,identity['slide_id'],exact,evidence_path)
        bound=bridge.download_current(runtime.load_runtime_state(state_path),identity['slide_id'])
        record.update(status='ACQUIRED',failure_checkpoint=None,local_finish_seconds=time.monotonic()-started,binding_evidence=str(evidence_path))
        _save(path,record)
        if record.get('lease_path'):
            import download_evidence as de
            for lease in set(record.get('lease_paths',[])+[record['lease_path']]):
                de.release_lease(lease,record['acquisition_id'])
        return {'status':'DOWNLOAD_BOUND','path':bound['path'],'sha256':bound['sha256'],'reused':False}
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error):
        fail(path,checkpoint)
        raise


def snapshot(path,state_path,directory,observed_url,action='normal',recovery_href=None,lease_dir=None):
    import download_evidence as de
    record=_read(path);identity=_identity(path,state_path,record['identity']['slide_id'])
    state=runtime.load_runtime_state(state_path)
    if bridge.status(state_path).get('status')!='WAIT_DOWNLOAD':raise ValueError('WAIT_DOWNLOAD required')
    de.design_url(observed_url,identity['design_id'])
    ref=state.get('canva_bridge',{}).get('design_observations',{}).get(identity['slide_id'])
    observed=de.sealed(ref);de.check_identity(observed['identity'],identity)
    if record.get('require_transport_receipt'):bridge.register_transport_requirement(state_path,identity,record['acquisition_id'])
    context={'identity':identity,'actual_title':observed.get('actual_title'),'observed_url':observed_url,
             'design_observation':ref}
    if action=='normal':
        if record['status']!='READY' or Path(str(path)+'.intent').exists():raise ValueError('normal baseline precedes intent')
    else:
        if not Path(str(path)+'.intent').exists():raise ValueError('recovery requires original intent')
        if recovery_href:context['recovery_export']=de.recovery_url(recovery_href,identity['design_id'])
        elif not record.get('require_transport_receipt'):raise ValueError('legacy recovery source required')
    if action=='normal':
        existing=[ref for ref in record.get('snapshots',[]) if de.sealed(ref)['action']=='normal']
        if existing:
            saved=de.sealed(existing[0])
            if saved['context']!=context or Path(saved['directory'])!=Path(directory).resolve():raise ValueError('original baseline cannot change on resume')
            return {'status':'SNAPSHOT_READY','snapshot':existing[0],'actual_title':context['actual_title']}
    index=len(record.get('snapshots',[]))+1
    output=Path(str(path)+'.snapshot-'+str(index)+'.json')
    ref=de.make_snapshot(record,context,directory,lease_dir or Path(path).resolve().parent/'download-leases',action,output)
    record.setdefault('snapshots',[]).append(ref);record['lease_path']=de.sealed(ref)['lease_path']
    record.setdefault('lease_paths',[])
    if record['lease_path'] not in record['lease_paths']:record['lease_paths'].append(record['lease_path'])
    _save(path,record)
    return {'status':'SNAPSHOT_READY','snapshot':ref,'actual_title':context['actual_title']}


def observe(path,state_path,snapshot_path,wait_seconds=10,event_confirmed=False,export_href=None,event_path=None,operation_capture=None):
    import download_evidence as de
    record=_read(path);identity=_identity(path,state_path,record['identity']['slide_id'])
    if not Path(str(path)+'.intent').exists():raise ValueError('observation requires original intent')
    if record['status']=='TERMINATED':raise ValueError('acquisition explicitly terminated')
    matches=[ref for ref in record.get('snapshots',[]) if Path(ref['path']).resolve()==Path(snapshot_path).resolve()]
    if len(matches)!=1:raise ValueError('snapshot must be registered on this acquisition')
    snap=de.sealed(matches[0])
    if de.read(snap['lease_path']).get('acquisition_id')!=record['acquisition_id']:raise ValueError('download directory lease lost')
    export=de.recovery_url(export_href,identity['design_id']) if export_href else None
    if record.get('require_transport_receipt'):
        bridge.register_transport_requirement(state_path,identity,record['acquisition_id'])
        completed=[]
        if operation_capture:
            op=de.read(operation_capture)
            de.check_identity(op['identity'],identity);de.design_url(op['observed_url'],identity['design_id'])
            if (op.get('source')!='canva_host.download' or not op.get('operation_id') or op.get('observed_url')!=snap['context']['observed_url'] or op.get('acquisition_id')!=record['acquisition_id'] or op.get('action')!=de.browser_action(snap['action'])):raise ValueError('invalid actual browser operation capture: identity mismatch')
            if op.get('completed') is True and op.get('path'):completed.append(op['path'])
        result=de.observe_transport_snapshot(matches[0],record,wait_seconds,completed)
        if result['status']!='FILE_COMPLETE':return result
        if operation_capture:
            operation=de.read(operation_capture)
            operation_ref={'path':str(Path(operation_capture).resolve()),'sha256':de.sha(operation_capture)}
        elif event_confirmed and event_path:
            operation={'source':'canva_host.download','identity':identity,'acquisition_id':record['acquisition_id'],
                'operation_id':uuid.uuid4().hex,'observed_url':snap['context']['observed_url'],
                'action':de.browser_action(snap['action']),'path':str(Path(event_path).resolve()),'export_source':export}
            operation_ref=de.write_once(Path(str(path)+'.operation-'+operation['operation_id']+'.json'),operation)
        else:
            return {**result,'status':'FILE_SOURCE_PENDING','detail':'Files complete; actual operation/path or exclusive directory capture required'}
        selected=next((x for x in result['candidates'] if Path(x['path']).resolve()==Path(operation.get('path','')).resolve()),None) if operation.get('path') else result['selected']
        if selected is None:return {**result,'status':'FILE_SOURCE_PENDING','detail':'Operation file not among stable candidates'}
        from download_transport import now
        if not any(x.get('operation_id')==operation.get('operation_id') for x in record.get('actions',[])):
            record.setdefault('actions',[]).append({'method':'browser','action':operation.get('action'),'operation_id':operation.get('operation_id'),'captured_at_utc':now()})
            _save(path,record)
        receipt={'method':'browser','result':'PASS','identity':identity,'acquisition_id':record['acquisition_id'],
            'observed_url':snap['context']['observed_url'],'source':export or operation.get('export_source'),
            'operation_capture':operation_ref,'download_event_confirmed':bool(event_confirmed),'path':selected['path'],'bytes':selected['bytes'],
            'sha256':selected['sha256'],'slide_count':1,'completed_at_utc':now()}
        try:return _register_transport_proof(path,state_path,record,matches[0],selected,receipt,result)
        except ValueError as error:
            if str(error) not in ('exclusive operation directory not established','SOURCE_ASSOCIATION_PENDING'):raise
            return {**result,'status':'FILE_SOURCE_PENDING','detail':str(error)}
    result=de.observe_snapshot(matches[0],record,bridge.single_page,wait_seconds,export)
    if result['status']=='FILE_COMPLETE':
        proof={'schema_version':2,'identity':identity,'acquisition_id':record['acquisition_id'],
               'snapshot':matches[0],'selected':result['selected'],'duplicates':result['duplicates'],
               'observed_ns':result['observed_ns'],'download_event_confirmed':bool(event_confirmed)}
        if export:proof['export_observation']=export
        if event_path:
            if not event_confirmed or Path(event_path).resolve()!=Path(result['selected']['path']).resolve():raise ValueError('actual same-operation event path must match selected file')
            proof['event_path']=str(Path(event_path).resolve())
        proof['evidence_digest']=__import__('hashlib').sha256(json.dumps(proof,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        proof_path=Path(str(path)+'.file-'+str(len(record.get('file_proofs',[]))+1)+'.json')
        proof_ref=de.write_once(proof_path,proof);record.setdefault('file_proofs',[]).append(proof_ref);_save(path,record)
        result['file_evidence']=proof_ref['path']
    return result


def register_page_check(path,state_path,file_evidence,review_path):
    import download_evidence as de
    record=_read(path);identity=_identity(path,state_path,record['identity']['slide_id'])
    if record['status']=='TERMINATED':raise ValueError('acquisition explicitly terminated')
    refs=[ref for ref in record.get('file_proofs',[]) if Path(ref['path']).resolve()==Path(file_evidence).resolve()]
    if len(refs)!=1:raise ValueError('review requires this acquisition file proof')
    proof=de.sealed(refs[0]);de.validate_file_proof(proof,identity)
    review=de.read(review_path);de.check_identity(review['identity'],identity)
    if review.get('file_sha256')!=proof['selected']['sha256']:raise ValueError('review belongs to another file')
    if review.get('input_sha256')!=identity['text_clean_fingerprint']:raise ValueError('review input page mismatch')
    if review.get('assessment')!='MATCH' or not isinstance(review.get('evidence'),str) or not review['evidence'].strip():
        raise ValueError('page comparison not confirmed; preserve downloaded file and diagnose, do not redownload')
    preview=de.sealed(review['preview_receipt']);de.check_identity(preview['identity'],identity)
    if preview['source_sha256']!=proof['selected']['sha256'] or de.sha(preview['preview_path'])!=preview['preview_sha256']:
        raise ValueError('preview bytes changed or belong to another file')
    input_ref=review['input_render']
    if de.sha(input_ref['path'])!=input_ref['sha256'] or input_ref['sha256']!=identity['text_clean_fingerprint']:
        raise ValueError('comparison input bytes changed')
    check_path=Path(str(path)+'.page-check-'+proof['selected']['sha256'][:12]+'.json')
    check_ref={'path':str(check_path),'sha256':de.sha(check_path)} if check_path.exists() else de.write_once(check_path,review)
    if de.sealed(check_ref)!=review:raise ValueError('immutable page review changed')
    enriched=dict(proof);enriched['page_check']=check_ref;enriched.pop('evidence_digest',None)
    enriched['evidence_digest']=__import__('hashlib').sha256(json.dumps(enriched,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    reviewed_path=Path(str(path)+'.reviewed-'+proof['selected']['sha256'][:12]+'.json')
    ref={'path':str(reviewed_path),'sha256':de.sha(reviewed_path)} if reviewed_path.exists() else de.write_once(reviewed_path,enriched)
    if de.sealed(ref)!=enriched:raise ValueError('immutable reviewed evidence changed')
    if ref not in record.setdefault('file_proofs',[]):record['file_proofs'].append(ref)
    _save(path,record)
    return {'status':'PAGE_CHECK_REGISTERED','file_evidence':ref['path']}


def acquire_files(path,state_path,file_evidence,event_confirmed=False):
    import download_evidence as de
    record=_read(path);identity=_identity(path,state_path,record['identity']['slide_id'])
    if not Path(str(path)+'.intent').exists():raise ValueError('original download intent required')
    if bridge.status(state_path).get('status')!='WAIT_DOWNLOAD':raise ValueError('WAIT_DOWNLOAD required')
    if record['status']=='TERMINATED':raise ValueError('acquisition explicitly terminated')
    refs=[ref for ref in record.get('file_proofs',[]) if Path(ref['path']).resolve()==Path(file_evidence).resolve()]
    if len(refs)!=1:raise ValueError('file evidence must be captured by this acquisition')
    proof=de.sealed(refs[0])
    if record.get('require_transport_receipt') and not proof.get('transport_receipt'):raise ValueError('TRANSPORT_RECEIPT_REQUIRED')
    snap=(de.validate_transport_proof(proof,identity) if record.get('require_transport_receipt') else de.validate_file_proof(proof,identity))
    if proof['acquisition_id']!=record['acquisition_id']:raise ValueError('acquisition mismatch')
    if de.read(snap['lease_path']).get('acquisition_id')!=record['acquisition_id']:raise ValueError('download directory lease lost')
    source=Path(proof['selected']['path']);bridge.single_page(source)
    bridge.validate_completion_evidence(runtime.load_runtime_state(state_path),identity,proof,source)
    if record.get('download_path') and (record['download_path']!=str(source) or record['sha256']!=de.sha(source)):
        raise ValueError('selected original file cannot change on resume')
    record.update(status='ACQUIRED',download_path=str(source),sha256=de.sha(source),
                  download_evidence=proof,failure_checkpoint=None)
    _save(path,record);return record


def _register_transport_proof(path,state_path,record,snapshot_ref,selected,receipt,result=None):
    import download_evidence as de
    receipt_ref=de.write_once(Path(str(path)+'.transport-'+uuid.uuid4().hex+'.json'),receipt)
    proof={'schema_version':2,'identity':record['identity'],'acquisition_id':record['acquisition_id'],
        'snapshot':snapshot_ref,'selected':selected,'transport_receipt':receipt_ref,
        'candidates':(result or {}).get('candidates',[selected]),
        'download_event_confirmed':bool(receipt.get('download_event_confirmed')),'observed_ns':time.time_ns()}
    de.validate_transport_proof(proof,record['identity'])
    proof['evidence_digest']=__import__('hashlib').sha256(json.dumps(proof,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    ref=de.write_once(Path(str(path)+'.file-'+uuid.uuid4().hex+'.json'),proof)
    record.setdefault('file_proofs',[]).append(ref);_save(path,record)
    bridge.register_transport_requirement(state_path,record['identity'],record['acquisition_id'],receipt_ref)
    return {**(result or {}),'status':'FILE_COMPLETE','selected':selected,'file_evidence':ref['path']}

def direct(path,state_path,observed_url,href,work_dir,timeout=30):
    import download_evidence as de
    import download_transport as dt
    record=_read(path);identity=_identity(path,state_path,record['identity']['slide_id'])
    if not record.get('require_transport_receipt'):raise ValueError('prepare a new transport acquisition; retain legacy evidence')
    if not Path(str(path)+'.intent').exists():raise ValueError('original intent required')
    if bridge.status(state_path).get('status')!='WAIT_DOWNLOAD':raise ValueError('WAIT_DOWNLOAD required')
    if record['status']=='TERMINATED':raise ValueError('acquisition explicitly terminated; prepare a new record on authorized restart')
    de.design_url(observed_url,identity['design_id'])
    for ref in reversed(record.get('file_proofs',[])):
        try:
            proof=de.sealed(ref)
            if not proof.get('transport_receipt'):continue
            de.validate_transport_proof(proof,identity)
        except (ValueError,OSError,KeyError):continue
        bridge.register_transport_requirement(state_path,identity,record['acquisition_id'],proof['transport_receipt'])
        return {'status':'FILE_COMPLETE','selected':proof['selected'],'file_evidence':ref['path'],'reused':True}
    de.recovery_url(href,identity['design_id'])
    observation=runtime.load_runtime_state(state_path)['canva_bridge']['design_observations'][identity['slide_id']]
    observed=de.sealed(observation);de.check_identity(observed['identity'],identity)
    bridge.register_transport_requirement(state_path,identity,record['acquisition_id'])
    directory=Path(work_dir).resolve()/('transfer-'+uuid.uuid4().hex);directory.mkdir(parents=True)
    context={'identity':identity,'observed_url':observed_url,'actual_title':observed.get('actual_title'),'design_observation':observation}
    snap=de.make_snapshot(record,context,directory,Path(path).resolve().parent/'download-leases','direct',Path(str(path)+'.snapshot-'+uuid.uuid4().hex+'.json'))
    record.setdefault('snapshots',[]).append(snap);record['lease_path']=de.sealed(snap)['lease_path']
    record.setdefault('lease_paths',[]).append(record['lease_path'])
    record.setdefault('actions',[]).append({'method':'direct','started_at_utc':dt.now()});_save(path,record)
    receipt=dt.download(href,identity['design_id'],directory,1,timeout)
    receipt.update(identity=identity,acquisition_id=record['acquisition_id'],observed_url=observed_url)
    record['actions'][-1].update(result=receipt['result'],get_count=receipt['get_count'],error=receipt.get('error'),status_code=receipt.get('status_code'),completed_at_utc=receipt['completed_at_utc'])
    _save(path,record)
    if receipt['result']!='PASS':
        ref=de.write_once(Path(str(path)+'.failed-'+receipt['request_id']+'.json'),receipt)
        de.release_lease(record['lease_path'],record['acquisition_id'])
        same=record['actions'][-3:]
        diagnose=len(same)==3 and all(x.get('result')=='FAIL' and (x.get('error'),x.get('status_code'))==(receipt.get('error'),receipt.get('status_code')) for x in same)
        return {'status':'DIRECT_UNAVAILABLE','receipt':ref,'action':'USE_BROWSER_FALLBACK','detail':receipt['error'],'diagnose_before_repeat':diagnose}
    source=Path(receipt['path']);st=source.stat()
    selected={'path':str(source),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'sha256':receipt['sha256']}
    return _register_transport_proof(path,state_path,record,snap,selected,receipt)


def terminate(path,state_path):
    """Explicit termination only; preserve evidence and intent, release owned leases."""
    import download_evidence as de
    record=_read(path);identity=_identity(path,state_path,record['identity']['slide_id'])
    state=runtime.load_runtime_state(state_path)
    bound=state.get('canva_bridge',{}).get('downloads',{}).get(identity['slide_id'])
    if bound and bound.get('identity')==identity:raise ValueError('bound output remains current; termination is for pending acquisitions')
    for lease in set(record.get('lease_paths',[])+([record['lease_path']] if record.get('lease_path') else [])):
        de.release_lease(lease,record['acquisition_id'])
    with bridge.transaction(state_path) as temp:
        current=runtime.load_runtime_state(temp)
        if bridge.active_identity(current,identity['slide_id'])!=identity:raise ValueError('termination identity changed')
        requirement=current['canva_bridge'].get('transport_requirements',{}).get(identity['slide_id'])
        if requirement and requirement.get('acquisition_id')==record['acquisition_id']:
            requirement['terminated']=True;runtime._save_runtime_state(temp,current)
    record['status']='TERMINATED';_save(path,record)
    return {'status':'TERMINATED','acquisition_id':record['acquisition_id'],'evidence_retained':True}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('ready','lock','fail','acquire','prepare','finish','snapshot','observe','register-page-check','direct','terminate'))
    parser.add_argument('--record',required=True)
    for name in ('request','state','profile','observed-url','checkpoint','slide-id','lookup','download-target-dir','target-filename','python-executable','file-evidence','download-dir','snapshot','recovery-href','lease-dir','review','export-href','event-path'):
        parser.add_argument('--'+name)
    parser.add_argument('--work-dir');parser.add_argument('--operation-capture');parser.add_argument('--network-timeout',type=float,default=30)
    parser.add_argument('--operation',choices=('normal','recovery','export_retry'),default='normal')
    parser.add_argument('--retry-kind',choices=('query','ui','observe'))
    parser.add_argument('--host-strategy',choices=('dom_event','legacy_observation','direct','browser'))
    parser.add_argument('--fallback-reason')
    parser.add_argument('--wait-seconds',type=float,default=None)
    parser.add_argument('--event-confirmed',action='store_true')
    parser.add_argument('--record-detail',choices=('compact','full'),default='full')
    parser.add_argument('--verbose',action='store_true')
    args=parser.parse_args()
    if args.wait_seconds is None:args.wait_seconds=10 if args.action=='observe' else 120
    try:
        if args.retry_kind and (args.host_strategy is not None or args.fallback_reason is not None):
            raise ValueError('strategy audit and retry reservation are separate operations')
        if args.wait_seconds<0 or args.wait_seconds>120:raise ValueError('completion wait must be 0..120 seconds')
        if args.recovery_href=='-':args.recovery_href=sys.stdin.readline().strip()
        if args.export_href=='-':args.export_href=sys.stdin.readline().strip()
        if args.action=='terminate':result=terminate(args.record,args.state)
        elif args.action=='ready':result=ready(args.record,_read(args.request))
        elif args.action=='lock':result=lock(args.record)
        elif args.action=='fail':result=fail(args.record,args.checkpoint)
        elif args.action=='acquire':result=acquire(args.record,args.state,args.profile,args.observed_url,args.event_confirmed,args.file_evidence)
        elif args.action=='snapshot':result=snapshot(args.record,args.state,args.download_dir,args.observed_url,args.operation,args.recovery_href,args.lease_dir)
        elif args.action=='observe':result=observe(args.record,args.state,args.snapshot,args.wait_seconds,args.event_confirmed,args.export_href,args.event_path,args.operation_capture)
        elif args.action=='direct':result=direct(args.record,args.state,args.observed_url,sys.stdin.readline().strip(),args.work_dir,args.network_timeout)
        elif args.action=='register-page-check':result=register_page_check(args.record,args.state,args.file_evidence,args.review)
        elif args.action=='prepare':
            if args.retry_kind:result=reserve_retry(args.record,args.state,args.slide_id,args.retry_kind)
            else:result=prepare(args.record,args.state,args.slide_id,args.lookup,args.download_target_dir,args.target_filename,args.host_strategy,args.fallback_reason)
        else:result=finish(args.record,args.state,args.profile,args.observed_url,args.event_confirmed,args.python_executable,args.wait_seconds,args.file_evidence)
    except (ValueError,KeyError,TypeError,OSError,sqlite3.Error) as error:
        result={'status':'BLOCKED','detail':str(error)};code=1
    else:code=0
    # Full local result is persisted; the Agent retains actual commands/UI/tool evidence.
    if args.record_detail=='full':
        _save(str(args.record)+'.'+args.action+'.result.json',result)
    else:
        compact={k:result[k] for k in ('status','path','sha256','file_evidence','receipt','snapshot','selected','candidates','duplicates','delta','invalid','completed_invalid','growing','pending','detail','action','retry_number','wait_seconds','reused','acquisition_id') if k in result}
        _save(str(args.record)+'.'+args.action+'.result.json',compact)
        if Path(args.record).is_file():
            journal=_read(args.record);journal['last_operation']={'action':args.action,**compact}
            _save(args.record,journal)
    if args.verbose:print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        summary={k:result[k] for k in ('status','path','sha256','reused','detail','retry_number','wait_seconds','host_strategy') if k in result}
        summary['slide_id']=args.slide_id or result.get('identity',{}).get('slide_id')
        print(json.dumps(summary,ensure_ascii=False))
    return code

if __name__=='__main__':raise SystemExit(main())
