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

QUERY_RETRY_DELAYS = (2, 5, 10, 15, 20)
UI_RETRY_DELAYS = (2, 5, 10, 15, 20)
POST_CLICK_OBSERVE_DELAYS = (10, 20, 30, 45, 60)
MAX_EXPORTS_PER_ROUND = 5


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
            'sha256':None,'download_evidence':None,'failure_checkpoint':None}
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

def _history(profile,workdir):
    # Live Chromium History may be locked. A local disposable readonly snapshot
    # avoids closing or altering the browser. Missing/ambiguous rows fail closed.
    fd,name=tempfile.mkstemp(prefix='download-history-',dir=workdir);os.close(fd)
    try:
        shutil.copyfile(profile/'History',name)
        db=sqlite3.connect(Path(name).as_uri()+'?mode=ro&immutable=1',uri=True)
        db.row_factory=sqlite3.Row
        try:
            rows=[dict(row) for row in db.execute('select id,guid,target_path,state,received_bytes,total_bytes,tab_url,start_time from downloads')]
            tables={row['name'] for row in db.execute("select name from sqlite_master where type='table'")}
            chains={}
            if 'downloads_url_chains' in tables:
                columns={row['name'] for row in db.execute('pragma table_info(downloads_url_chains)')}
                if {'id','chain_index','url'} <= columns:
                    for item in db.execute('select id,chain_index,url from downloads_url_chains order by id,chain_index'):
                        chains.setdefault(item['id'],[]).append(item['url'])
            for row in rows:row['url_chain']=chains.get(row['id'],[])
            return rows
        finally:db.close()
    finally:Path(name).unlink(missing_ok=True)

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


def acquire(path,state_path,profile,observed_url,event_confirmed):
    record=_read(path);identity=record['identity']
    if record['status'] not in ('INTENT_LOCKED','FAILED') or not Path(str(path)+'.intent').exists():
        raise ValueError('original download intent lock required')
    if not event_confirmed:raise ValueError('observed Host download event required')
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
    for row in _history(profile,Path(path).resolve().parent):
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
        download_evidence={'download_event_confirmed':True,'browser_profile':str(profile),
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
    """Reserve bounded Agent retry/observation work; never calls browser/network APIs."""
    delays={'query':QUERY_RETRY_DELAYS,'ui':UI_RETRY_DELAYS,'observe':POST_CLICK_OBSERVE_DELAYS}
    if kind not in delays:raise ValueError('unsupported retry kind')
    identity=_identity(path,state_path,slide_id)
    if bridge.status(state_path).get('status')!='WAIT_DOWNLOAD':raise ValueError('WAIT_DOWNLOAD required')
    intent=Path(str(path)+'.intent').exists()
    if kind=='observe' and not intent:raise ValueError('observe retry requires locked download intent')
    if kind in ('query','ui') and intent:raise ValueError('intent locked: observe only, no pre-download retry')
    budget_path=Path(str(path)+'.retries.json')
    budget=_read(budget_path) if budget_path.exists() else {'identity':identity,'query':0,'ui':0,'observe':0}
    if budget['identity']!=identity:raise ValueError('retry identity mismatch')
    for key in delays:budget.setdefault(key,0)
    count=budget[kind]
    if count>=len(delays[kind]):raise ValueError(kind+' retry budget exhausted')
    budget[kind]=count+1
    _save(budget_path,budget)
    return {'status':'RETRY_RESERVED','retry_number':count+1,'wait_seconds':delays[kind][count]}


def _strategy_record(record, strategy, fallback_reason, intent_locked):
    """Local audit metadata only; never confers click/retry permissions."""
    import copy
    from datetime import datetime, timezone
    result = copy.deepcopy(record)
    if strategy is None:
        if fallback_reason is not None:
            raise ValueError('fallback reason requires explicit host strategy')
        return result
    if strategy not in ('dom_event', 'legacy_observation'):
        raise ValueError('unsupported host strategy')
    if fallback_reason is not None and (not isinstance(fallback_reason,str) or not fallback_reason.strip()):
        raise ValueError('nonempty fallback reason required')
    if intent_locked and strategy != 'legacy_observation':
        raise ValueError('intent locked: observe only; no event/click restart')
    previous = result.get('host_strategy')
    reason = fallback_reason or ''
    if previous and previous['strategy'] != strategy and not reason:
        raise ValueError('strategy switch requires observed fallback reason')
    phase = 'observe_only' if intent_locked else 'pre_download'
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
    if not event_confirmed:raise ValueError('observed Host download event required')
    record=_read(path)
    if 'completion_deadline' in record and time.time()>=record['completion_deadline']:
        raise ValueError('same-download completion timeout')
    if 'completion_deadline' not in record:
        record['completion_deadline']=time.time()+wait_seconds
        _save(path,record)
    pending=('same-design download record pending','completed exact download required','download bytes do not match precise file')
    initial=True
    while True:
        if not initial and time.time()>=record['completion_deadline']:
            raise ValueError('same-download completion timeout')
        initial=False
        try:return acquire(path,state_path,profile,observed_url,True)
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


def finish(path,state_path,profile,observed_url,event_confirmed,python_executable=None,wait_seconds=120):
    started=time.monotonic()
    record=_read(path);identity=_identity(path,state_path,record['identity']['slide_id'])
    state=runtime.load_runtime_state(state_path)
    binding=state.get('canva_bridge',{}).get('downloads',{}).get(identity['slide_id'])
    if binding is not None:
        bound=bridge.download_current(state,identity['slide_id'])
        if record.get('sha256')!=bound['sha256'] or record.get('finalizer',{}).get('Path')!=bound['path']:
            raise ValueError('existing binding does not belong to this acquisition')
        return {'status':'DOWNLOAD_BOUND','path':bound['path'],'sha256':bound['sha256'],'reused':True}
    if not event_confirmed:raise ValueError('observed Host download event required')
    if not Path(str(path)+'.intent').exists():raise ValueError('original intent required')
    req=record.get('request')
    if not req:raise ValueError('prepare request required')
    if bridge.sha(req['lookup_path'])!=req['lookup_sha256']:raise ValueError('trusted lookup changed')
    bridge._lookup_url(_read(req['lookup_path']),identity)
    checkpoint='ACQUIRE'
    try:
        if record.get('download_evidence') is None:
            record=acquire_wait(path,state_path,profile,observed_url,event_confirmed,wait_seconds)
        current_provenance=_design_provenance(record['download_evidence']['download_record'],observed_url,identity['design_id'])
        if current_provenance is None or current_provenance!=record['download_evidence'].get('design_provenance'):
            raise ValueError('original observed Design URL/provenance changed')
        if not record.get('download_evidence',{}).get('download_event_confirmed'):
            raise ValueError('original event evidence required')
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
        return {'status':'DOWNLOAD_BOUND','path':bound['path'],'sha256':bound['sha256'],'reused':False}
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error):
        fail(path,checkpoint)
        raise


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('ready','lock','fail','acquire','prepare','finish'))
    parser.add_argument('--record',required=True)
    for name in ('request','state','profile','observed-url','checkpoint','slide-id','lookup','download-target-dir','target-filename','python-executable'):
        parser.add_argument('--'+name)
    parser.add_argument('--retry-kind',choices=('query','ui','observe'))
    parser.add_argument('--host-strategy',choices=('dom_event','legacy_observation'))
    parser.add_argument('--fallback-reason')
    parser.add_argument('--wait-seconds',type=float,default=120)
    parser.add_argument('--event-confirmed',action='store_true')
    parser.add_argument('--verbose',action='store_true')
    args=parser.parse_args()
    try:
        if args.retry_kind and (args.host_strategy is not None or args.fallback_reason is not None):
            raise ValueError('strategy audit and retry reservation are separate operations')
        if args.wait_seconds<0 or args.wait_seconds>120:raise ValueError('completion wait must be 0..120 seconds')
        if args.action=='ready':result=ready(args.record,_read(args.request))
        elif args.action=='lock':result=lock(args.record)
        elif args.action=='fail':result=fail(args.record,args.checkpoint)
        elif args.action=='acquire':result=acquire(args.record,args.state,args.profile,args.observed_url,args.event_confirmed)
        elif args.action=='prepare':
            if args.retry_kind:result=reserve_retry(args.record,args.state,args.slide_id,args.retry_kind)
            else:result=prepare(args.record,args.state,args.slide_id,args.lookup,args.download_target_dir,args.target_filename,args.host_strategy,args.fallback_reason)
        else:result=finish(args.record,args.state,args.profile,args.observed_url,args.event_confirmed,args.python_executable,args.wait_seconds)
    except (ValueError,KeyError,TypeError,OSError,sqlite3.Error) as error:
        result={'status':'BLOCKED','detail':str(error)};code=1
    else:code=0
    # Full local result is persisted; the Agent retains actual commands/UI/tool evidence.
    _save(str(args.record)+'.'+args.action+'.result.json',result)
    if args.verbose:print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        summary={k:result[k] for k in ('status','path','sha256','reused','detail','retry_number','wait_seconds','host_strategy') if k in result}
        summary['slide_id']=args.slide_id or result.get('identity',{}).get('slide_id')
        print(json.dumps(summary,ensure_ascii=False))
    return code

if __name__=='__main__':raise SystemExit(main())
