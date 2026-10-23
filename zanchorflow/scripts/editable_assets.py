"""Persistent per-source image budget. Host calls tools only after a reservation."""
import argparse,hashlib,json,uuid
from pathlib import Path
import runtime as r
import reconstruction_router as router
import editable_bridge as bridge

def digest(value):return hashlib.sha256(r._canonical(value)).hexdigest()

def register_job(state_path,sid,region,role):
 bridge.require_route(state_path)
 if role not in ('foreground','background'):raise ValueError('asset role required')
 state=r.load_runtime_state(state_path);src,_=bridge.source(state,sid)
 from PIL import Image
 with Image.open(src['render']) as im:sw,sh=im.size
 from editable_build import numbers
 x,y,w,h=numbers(region,4)
 if min(x,y)<0 or min(w,h)<=0 or x+w>sw or y+h>sh:raise ValueError('invalid source region')
 region=[float(v) for v in region]
 identity={'source_sha256':bridge.sha(Path(src['render']).read_bytes()),'role':role,'region_px':region}
 key=digest(identity)
 with router.transaction(state_path) as temp:
  current=r.load_runtime_state(temp);jobs=current.setdefault('editable_asset_jobs',{})
  if bridge.source(current,sid)[0]!=src:raise ValueError('asset source changed')
  for oldkey,old in jobs.items():
   prior=old['identity']
   if prior['source_sha256']==identity['source_sha256'] and prior['role']==role:
    a,b,c,d=prior['region_px']
    if max(a,x)<min(a+c,x+w) and max(b,y)<min(b+d,y+h) and oldkey!=key:raise ValueError('OVERLAPPING_JOB_SCOPE: reuse the original stable job; changing prompts or boxes does not reset its budget')
  job=jobs.setdefault(key,{'identity':identity,'calls':[],'run_ids':[]})
  run_id=current['stage2_run']['run_id']
  if run_id not in job.setdefault('run_ids',[]):job['run_ids'].append(run_id)
  job.setdefault('source_refs',{})[sid]={'run_id':run_id,'source_fingerprint':src['source_fingerprint']}
  r._save_runtime_state(temp,current)
 return {'job_key':key,'identity':identity}

def reserve(state_path,key,correction_finding=None):
 bridge.require_route(state_path)
 with router.transaction(state_path) as temp:
  state=r.load_runtime_state(temp);job=state['editable_asset_jobs'][key];calls=job['calls']
  if state['stage2_run']['run_id'] not in job.get('run_ids',[]):raise ValueError('CURRENT_IMAGE_JOB_REGISTRATION_REQUIRED')
  if len(calls)>=2:raise ValueError('IMAGE_CORRECTION_BUDGET_EXHAUSTED')
  if any(c.get('sheet_key') for c in calls):raise ValueError('SHEET_MANAGED_JOB: use sheet interfaces')
  resolved=resolve_receipt(state,key,calls[-1]['token']) if calls else None
  if resolved and resolved['recovered'] and not resolved['eligible']:raise ValueError('RECOVERY_REQUIRES_REVALIDATION')
  if resolved and resolved['effective']['status']=='reserved':raise ValueError('IMAGE_CALL_PENDING: record the actual result or failure, never reissue automatically')
  if calls and (not isinstance(correction_finding,str) or not correction_finding.strip()):raise ValueError('TARGETED_CORRECTION_FINDING_REQUIRED')
  call={'run_id':state['stage2_run']['run_id'],'identity_sha256':digest(job['identity']),'source_refs':json.loads(json.dumps(job.get('source_refs',{}))),'token':uuid.uuid4().hex,'status':'reserved','call_number':len(calls)+1,'correction_finding':correction_finding or ''};calls.append(call);r._save_runtime_state(temp,state)
 return call

def record_result(state_path,key,token,returned_path=None,failure=None):
 return _record_receipt(state_path,key,token,returned_path,failure,sheet=False)


def validate_assets(state,plan,src):
 source_sha=bridge.sha(Path(src['render']).read_bytes())
 formula_ids={v['object_id'] for v in plan.get('formula_inventory',[]) if v['decision']=='latex_rendered'}
 for item in plan['objects']:
  if item['type']!='image':continue
  provenance=item.get('provenance',{})
  if item['id'] in formula_ids:continue
  if provenance.get('kind')=='source_preserved':
   if provenance.get('source_sha256')!=source_sha:raise ValueError('EDITABLE_ASSET_SOURCE_STALE')
   if not provenance.get('finding'):raise ValueError('EDITABLE_SOURCE_ASSET_EVIDENCE_REQUIRED')
  elif provenance.get('kind')=='generated':
   job=state.get('editable_asset_jobs',{}).get(provenance.get('job_key'),{})
   if job.get('identity',{}).get('source_sha256')!=source_sha:raise ValueError('EDITABLE_ASSET_JOB_SOURCE_MISMATCH')
   if provenance.get('sheet_key') or any(c.get('sheet_key') for c in job.get('calls',[])):
    validate_sheet_asset(state,item,src)
   receipts=[]
   for c in job.get('calls',[]):
    v=resolve_receipt(state,provenance['job_key'],c['token'])
    if (v['eligible'] or c.get('sheet_key')) and v['effective'].get('status')=='returned':
     if v['effective']['sha256']==provenance.get('returned_sha256'):_check_file(v['effective'])
     receipts.append(v['effective']['sha256'])
   if provenance.get('returned_sha256') not in receipts:raise ValueError('EDITABLE_ACTUAL_TOOL_RESULT_REQUIRED')
   if item['sha256']!=provenance['returned_sha256'] and not provenance.get('processing_finding'):raise ValueError('EDITABLE_ASSET_DERIVATION_REQUIRED')
  else:raise ValueError('EDITABLE_ASSET_PROVENANCE_REQUIRED')


def _pin(path):
 path=Path(path).resolve()
 return {'path':str(path),'sha256':bridge.sha(path.read_bytes())}


def _check_file(entry):
 path=Path(entry['path'])
 if bridge.sha(path.read_bytes())!=entry['sha256']:raise ValueError('SHEET_EVIDENCE_TAMPERED')
 return path


def _snapshot(state_path,path):
 path=Path(path).resolve();raw=path.read_bytes();sha=bridge.sha(raw)
 root=Path(state_path).resolve().parent/'editable-assets'/'blobs';root.mkdir(parents=True,exist_ok=True)
 dest=root/(sha+path.suffix.lower())
 if dest.exists():
  if dest.read_bytes()!=raw:raise ValueError('SHEET_SNAPSHOT_TAMPERED')
 else:
  with dest.open('xb') as f:f.write(raw)
 return {'path':str(dest),'sha256':sha}


def _sheet(state,key):
 sheet=state['editable_asset_sheets'][key]
 if digest(sheet['body'])!=key:raise ValueError('SHEET_DEFINITION_TAMPERED')
 for entry in sheet['body']['references']:_check_file(entry)
 for member in sheet['body']['members']:
  for source in member['sources']:_check_file(source['snapshot'])
 return sheet


def _current_sheet(state,sheet):
 body=sheet['body']
 if body['run_id']!=state['stage2_run']['run_id']:raise ValueError('SHEET_RUN_STALE')
 for member in body['members']:
  job=state['editable_asset_jobs'][member['job_key']]
  if body['run_id'] not in job.get('run_ids',[]):raise ValueError('CURRENT_IMAGE_JOB_REGISTRATION_REQUIRED')
  for source in member['sources']:
   src,_=bridge.source(state,source['slide_id'])
   if src['source_fingerprint']!=source['source_fingerprint'] or bridge.sha(Path(src['render']).read_bytes())!=source['snapshot']['sha256']:raise ValueError('SHEET_SOURCE_STALE')


def register_sheet(state_path,spec):
 """Freeze a host-designed layout; this is not an automatic packing algorithm."""
 bridge.require_route(state_path)
 if not isinstance(spec,dict):raise ValueError('SHEET_SPEC_REQUIRED')
 from editable_build import numbers
 size=numbers(spec.get('size_px'),2)
 if any(type(v) is not int or v<=0 for v in spec['size_px']):raise ValueError('SHEET_SIZE_INVALID')
 padding=spec.get('padding_px',16)
 if type(padding) is not int or padding<1:raise ValueError('SHEET_PADDING_REQUIRED')
 if spec.get('stage') not in ('initial','correction'):raise ValueError('SHEET_STAGE_REQUIRED')
 if spec.get('seal_reason') not in ('queue_end','page_limit','capacity','incompatible'):raise ValueError('SHEET_SEAL_REASON_REQUIRED')
 if spec['seal_reason'] in ('capacity','incompatible') and not str(spec.get('finding','')).strip():raise ValueError('SHEET_SEAL_FINDING_REQUIRED')
 if not isinstance(spec.get('background'),str) or not spec['background'].strip():raise ValueError('SHEET_BACKGROUND_REQUIRED')
 if not isinstance(spec.get('members'),list) or not spec['members']:raise ValueError('SHEET_MEMBERS_REQUIRED')
 with router.transaction(state_path) as temp:
  state=r.load_runtime_state(temp);members=[];keys=set();pages=set();boxes=[]
  for item in spec['members']:
   key=item['job_key']
   if key in keys:raise ValueError('SHEET_DUPLICATE_MEMBER')
   keys.add(key);job=state['editable_asset_jobs'][key]
   if job['identity']['role']!='foreground':raise ValueError('SHEET_FOREGROUND_ONLY')
   sources=[];seen=set()
   if not item.get('sources'):raise ValueError('SHEET_MEMBER_SOURCES_REQUIRED')
   for ref in item['sources']:
    sid=ref['slide_id'];obj=ref['object_ref']
    if sid not in state['stage2_run'].get('page_order',[]):raise ValueError('SHEET_PAGE_OUTSIDE_CURRENT_RUN')
    if not isinstance(obj,str) or not obj.strip() or sid in seen:raise ValueError('SHEET_SOURCE_REF_INVALID')
    seen.add(sid);pages.add(sid);src,_=bridge.source(state,sid)
    if bridge.sha(Path(src['render']).read_bytes())!=job['identity']['source_sha256']:raise ValueError('SHEET_MEMBER_SOURCE_MISMATCH')
    sources.append({'slide_id':sid,'object_ref':obj,'source_fingerprint':src['source_fingerprint'],'snapshot':_snapshot(state_path,src['render'])})
   x,y,w,h=numbers(item.get('box'),4)
   if x<padding or y<padding or x+w+padding>size[0] or y+h+padding>size[1] or min(w,h)<=0:raise ValueError('SHEET_LAYOUT_BOUNDS')
   if w<job['identity']['region_px'][2] or h<job['identity']['region_px'][3]:raise ValueError('SHEET_LAYOUT_DOWNSAMPLING')
   for a,b,c,d in boxes:
    if max(x-padding/2,a-padding/2)<min(x+w+padding/2,a+c+padding/2) and max(y-padding/2,b-padding/2)<min(y+h+padding/2,b+d+padding/2):raise ValueError('SHEET_LAYOUT_OVERLAP')
   boxes.append((x,y,w,h));member={'job_key':key,'sources':sources,'box':[x,y,w,h]}
   if spec['stage']=='correction':
    if not isinstance(item.get('finding'),str) or not item['finding'].strip():raise ValueError('TARGETED_CORRECTION_FINDING_REQUIRED')
    member['finding']=item['finding']
   members.append(member)
  if len(pages)>3:raise ValueError('SHEET_THREE_PAGE_LIMIT')
  body={'run_id':state['stage2_run']['run_id'],'stage':spec['stage'],'members':members,'size_px':spec['size_px'],'padding_px':padding,'background':spec['background'],'seal_reason':spec['seal_reason'],'finding':spec.get('finding',''),'references':[_snapshot(state_path,f) for f in spec.get('reference_paths',[])]}
  sheet={'body':body,'calls':[],'reviews':[]};_current_sheet(state,sheet);key=digest(body)
  result=state.setdefault('editable_asset_sheets',{}).setdefault(key,sheet)
  r._save_runtime_state(temp,state)
 return {'sheet_key':key,'body':result['body']}


def reserve_sheet(state_path,key):
 bridge.require_route(state_path)
 with router.transaction(state_path) as temp:
  state=r.load_runtime_state(temp);sheet=_sheet(state,key);_current_sheet(state,sheet)
  if sheet['calls']:raise ValueError('SHEET_ALREADY_RESERVED: regroup correction in a new sheet')
  for member in sheet['body']['members']:
   job=state['editable_asset_jobs'][member['job_key']];calls=job['calls']
   if len(calls)>=2:raise ValueError('IMAGE_CORRECTION_BUDGET_EXHAUSTED')
   effective=resolve_receipt(state,member['job_key'],calls[-1]['token'])['effective'] if calls else None
   if effective and effective['status']=='reserved':raise ValueError('IMAGE_CALL_PENDING')
   if job.get('sheet_accepted'):raise ValueError('SHEET_MEMBER_ALREADY_ACCEPTED')
   if sheet['body']['stage']=='initial' and calls:raise ValueError('SHEET_INITIAL_ALREADY_ATTEMPTED')
   if sheet['body']['stage']=='correction':
    if not calls:raise ValueError('SHEET_CORRECTION_WITHOUT_ATTEMPT')
    if effective['status']=='returned':
     latest=job.get('sheet_reviews',[])
     if not latest or latest[-1]['token']!=calls[-1]['token'] or latest[-1]['verdict']!='failed':raise ValueError('SHEET_FAILED_REVIEW_REQUIRED')
     previous=_sheet(state,latest[-1]['sheet_key']);_review_payload(state,previous,latest[-1]['review'])
  token=uuid.uuid4().hex
  for member in sheet['body']['members']:
   job=state['editable_asset_jobs'][member['job_key']]
   job['calls'].append({'run_id':sheet['body']['run_id'],'identity_sha256':digest(job['identity']),'token':token,'sheet_key':key,'status':'reserved','call_number':len(job['calls'])+1,'correction_finding':member.get('finding','')})
  sheet['calls'].append({'run_id':sheet['body']['run_id'],'token':token,'status':'reserved'});r._save_runtime_state(temp,state)
 return {'sheet_key':key,'token':token,'status':'reserved','member_count':len(sheet['body']['members'])}


def record_sheet_result(state_path,key,token,returned_path=None,failure=None,unknown=False):
 bridge.require_route(state_path)
 return _record_receipt(state_path,key,token,returned_path,failure,unknown,sheet=True)


def _review_payload(state,sheet,entry):
 path=_check_file(entry);payload=bridge.read(path)
 if payload['sheet_key']!=digest(sheet['body']):raise ValueError('SHEET_REVIEW_MISMATCH')
 call=resolve_receipt(state,digest(sheet['body']),payload['token'],sheet=True)['effective']
 if call['status']!='returned':raise ValueError('SHEET_REVIEW_TOKEN_MISMATCH')
 _check_file(call)
 for pin in payload['files']:_check_file(pin)
 return payload


def review_sheet(state_path,key,submission):
 bridge.require_route(state_path)
 with router.transaction(state_path) as temp:
  bridge.require_route(temp)
  state=r.load_runtime_state(temp);sheet=_sheet(state,key);_current_sheet(state,sheet);resolved=resolve_receipt(state,key,submission['token'],sheet=True);call=resolved['effective']
  if not resolved['eligible'] or call['status']!='returned':raise ValueError('SHEET_REVIEW_TOKEN_MISMATCH')
  _check_file(call)
  report_path=Path(submission['split_report']);report=bridge.read(report_path)
  if report.get('batch_mode') is not True or not report.get('sheet_safe'):raise ValueError('SHEET_SPLIT_NOT_SAFE')
  processed=_check_file({'path':report['source'],'sha256':report['source_sha256']})
  if report['source_sha256']!=call['sha256'] and not str(submission.get('processing_finding','')).strip():raise ValueError('SHEET_PROCESSING_FINDING_REQUIRED')
  expected={m['job_key'] for m in sheet['body']['members']}
  reports={a['job_key']:a for a in report['assets']};items=submission['items']
  if len(reports)!=len(report['assets']) or set(reports)!=expected or len(items)!=len(expected) or {v['job_key'] for v in items}!=expected:raise ValueError('SHEET_REVIEW_MEMBERS_MISMATCH')
  regions_pin={'path':report['regions_source'],'sha256':report['regions_sha256']};_check_file(regions_pin)
  files=[_pin(report_path),_pin(processed),regions_pin];results=[]
  for item in items:
   jk=item['job_key'];asset=reports[jk];job=state['editable_asset_jobs'][jk]
   if job['calls'][-1]['token']!=call['token']:raise ValueError('SHEET_REVIEW_SUPERSEDED_ATTEMPT')
   if item.get('verdict') not in ('accepted','failed') or not str(item.get('finding','')).strip():raise ValueError('SHEET_OBJECT_REVIEW_REQUIRED')
   evidence=item.get('evidence_paths',[])
   if not evidence:raise ValueError('SHEET_OBJECT_EVIDENCE_REQUIRED')
   files.extend(_pin(f) for f in evidence)
   result={'job_key':jk,'verdict':item['verdict'],'finding':item['finding']}
   if item['verdict']=='accepted':
    if asset.get('status')!='extracted' or any(item.get('checks',{}).get(c) is not True for c in ('identity','shape','detail','edges','background')):raise ValueError('SHEET_OBJECT_ACCEPTANCE_REQUIRED')
    pin={'path':asset['path'],'sha256':asset['sha256']};_check_file(pin);files.append(pin);result['asset']=pin;result['checks']=item['checks']
   accepted=job.get('sheet_accepted')
   if accepted and (result['verdict']!='accepted' or result['asset']!=accepted['asset']):raise ValueError('SHEET_ACCEPTED_ASSET_IMMUTABLE')
   results.append(result)
  payload={'sheet_key':key,'token':call['token'],'returned_sha256':call['sha256'],'files':files,'results':results,'processing_finding':submission.get('processing_finding','')}
  raw=r._canonical(payload);sha=bridge.sha(raw);dest=Path(state_path).resolve().parent/'editable-assets'/'reviews'/(sha+'.json');dest.parent.mkdir(parents=True,exist_ok=True)
  if dest.exists():
   if dest.read_bytes()!=raw:raise ValueError('SHEET_REVIEW_TAMPERED')
  else:
   with dest.open('xb') as f:f.write(raw)
  pin={'path':str(dest),'sha256':sha}
  if pin not in sheet['reviews']:sheet['reviews'].append(pin)
  for result in results:
   job=state['editable_asset_jobs'][result['job_key']];receipt={'sheet_key':key,'token':call['token'],'review':pin,'verdict':result['verdict']}
   if not job.get('sheet_reviews') or job['sheet_reviews'][-1]!=receipt:job.setdefault('sheet_reviews',[]).append(receipt)
   if result['verdict']=='accepted' and not job.get('sheet_accepted'):job['sheet_accepted']={**receipt,'asset':result['asset']}
  r._save_runtime_state(temp,state)
 return {'review':pin,'results':results}


def validate_sheet_asset(state,item,src):
 p=item['provenance'];key=p.get('sheet_key');sheet=_sheet(state,key)
 accepted=state['editable_asset_jobs'][p['job_key']].get('sheet_accepted')
 if not accepted or accepted['sheet_key']!=key or p.get('review_sha256')!=accepted['review']['sha256']:raise ValueError('SHEET_ACCEPTED_RESULT_REQUIRED')
 payload=_review_payload(state,sheet,accepted['review'])
 resolved=resolve_receipt(state,p['job_key'],payload['token'])
 if resolved['recovered'] and (sheet['body']['run_id']!=src['run_id'] or state['editable_asset_jobs'][p['job_key']]['calls'][-1]['token']!=payload['token'] or resolved['original_status']=='failed'):raise ValueError('RECOVERED_ASSET_ARCHIVE_ONLY')
 result=next(v for v in payload['results'] if v['job_key']==p['job_key'])
 if result['verdict']!='accepted' or item['sha256']!=result['asset']['sha256']:raise ValueError('SHEET_ASSET_MISMATCH')
 member=next(v for v in sheet['body']['members'] if v['job_key']==p['job_key'])
 refs=[ref for ref in member['sources'] if ref['slide_id']==src['slide_id']]
 registered=state['editable_asset_jobs'][p['job_key']].get('source_refs',{}).get(src['slide_id'],{})
 if (refs and refs[0]['source_fingerprint']!=src['source_fingerprint']) or (not refs and (registered.get('run_id')!=src['run_id'] or registered.get('source_fingerprint')!=src['source_fingerprint'])):raise ValueError('SHEET_PAGE_SOURCE_STALE')
 if p.get('returned_sha256')!=payload.get('returned_sha256',resolve_receipt(state,key,payload['token'],sheet=True)['effective'].get('sha256')):raise ValueError('SHEET_RETURN_MISMATCH')



def _sheet_identity(state,key):
 sheet=state['editable_asset_sheets'][key]
 if digest(sheet['body'])!=key:raise ValueError('SHEET_DEFINITION_TAMPERED')
 members=sheet['body']['members'];keys=[m['job_key'] for m in members]
 if not keys or len(keys)!=len(set(keys)):raise ValueError('SHEET_MEMBER_IDENTITY_INVALID')
 for member in members:
  identity=state['editable_asset_jobs'][member['job_key']]['identity']
  if digest(identity)!=member['job_key'] or any(ref['snapshot']['sha256']!=identity['source_sha256'] for ref in member['sources']):raise ValueError('SHEET_MEMBER_IDENTITY_INVALID')
 return sheet


def _locate(state,key,token,sheet=False):
 if not isinstance(token,str) or not token:raise ValueError('IMAGE_RESERVATION_MISMATCH')
 if sheet:
  group=_sheet_identity(state,key);matches=[c for c in group['calls'] if c['token']==token]
 else:
  job=state['editable_asset_jobs'][key]
  if digest(job['identity'])!=key:raise ValueError('IMAGE_JOB_IDENTITY_INVALID')
  matches=[c for c in job['calls'] if c['token']==token]
 if len(matches)!=1:raise ValueError('IMAGE_RESERVATION_MISMATCH')
 call=matches[0]
 if not sheet and call.get('sheet_key'):return _locate(state,call['sheet_key'],token,True)
 copies=[call]
 if sheet:
  for member in group['body']['members']:
   job=state['editable_asset_jobs'][member['job_key']];rows=[c for c in job['calls'] if c['token']==token]
   if len(rows)!=1 or rows[0].get('sheet_key')!=key:raise ValueError('SHEET_MEMBER_RESERVATION_MISMATCH')
   row=rows[0]
   if call.get('run_id',group['body']['run_id'])!=group['body']['run_id'] or row.get('run_id',group['body']['run_id'])!=group['body']['run_id']:raise ValueError('SHEET_RESERVATION_RUN_MISMATCH')
   if row.get('identity_sha256',member['job_key'])!=member['job_key']:raise ValueError('IMAGE_JOB_IDENTITY_INVALID')
   for field in ('status','sha256','failure','path','receipt_events'):
    if row.get(field)!=call.get(field):raise ValueError('SHEET_MEMBER_RESERVATION_MISMATCH')
   copies.append(row)
 elif call.get('identity_sha256',key)!=key:raise ValueError('IMAGE_JOB_IDENTITY_INVALID')
 return key,call,copies,sheet


def resolve_receipt(state,key,token,sheet=False):
 """Single source of truth: original state, facts, latest attempt and current use."""
 focus=key if not sheet else None
 key,call,copies,sheet=_locate(state,key,token,sheet)
 effective=dict(call);events=call.get('receipt_events',[])
 if not isinstance(events,list):raise ValueError('RECEIPT_EVENTS_INVALID')
 facts=[]
 if call['status'] in ('returned','failed','unknown'):facts.append(call)
 for event in events:
  if event.get('token')!=token or event.get('fingerprint')!=_result_fingerprint(event):raise ValueError('RECEIPT_EVENT_TAMPERED')
  facts.append(event)
 if events and call['status'] in ('reserved','unknown'):
  effective.update(events[-1]);effective['token']=token
 eligible=True;reasons=[]
 if sheet:
  group=_sheet_identity(state,key)
  members=[m for m in group['body']['members'] if focus is None or m['job_key']==focus]
  latest=all(state['editable_asset_jobs'][m['job_key']]['calls'][-1]['token']==token for m in members)
  if events:
   try:
    _current_sheet(state,{'body':{**group['body'],'members':members}});_sheet(state,key)
   except (ValueError,OSError,KeyError,TypeError):eligible=False;reasons.append('SOURCE_OR_EVIDENCE_NOT_CURRENT')
  run=group['body']['run_id']
 else:
  job=state['editable_asset_jobs'][key];latest=job['calls'][-1]['token']==token;run=call.get('run_id')
  if events:
   refs=call.get('source_refs',{});valid=False
   for sid,ref in refs.items():
    try:
     src,_=bridge.source(state,sid)
     if ref['run_id']==run and ref['source_fingerprint']==src['source_fingerprint'] and bridge.sha(Path(src['render']).read_bytes())==job['identity']['source_sha256']:valid=True
    except (OSError,ValueError,KeyError,TypeError):pass
   if not valid:eligible=False;reasons.append('SOURCE_NOT_CURRENT')
 if events and (not latest or not run or run!=state.get('stage2_run',{}).get('run_id') or call['status']=='failed' or (effective.get('status')=='returned' and any(f['status']=='failed' for f in facts))):
  eligible=False;reasons.append('ARCHIVE_ONLY')
 return {'original_status':call['status'],'effective':effective,'facts':facts,'eligible':eligible,'reasons':reasons,'recovered':bool(events),'latest':latest}


def _result_fingerprint(value):
 return digest({'status':value['status'],'value':value.get('sha256') if value['status']=='returned' else value.get('failure')})


def _record_receipt(state_path,key,token,returned_path=None,failure=None,unknown=False,sheet=False,reconcile=False):
 if bool(returned_path)==bool(failure):raise ValueError('record exactly one actual file result or failure')
 if unknown and returned_path:raise ValueError('SHEET_UNKNOWN_WITH_FILE')
 with router.transaction(state_path) as temp:
  state=r.load_runtime_state(temp);actual_key,call,copies,actual_sheet=_locate(state,key,token,sheet)
  if actual_sheet and not sheet:raise ValueError('SHEET_MANAGED_JOB: use sheet interfaces')
  if not reconcile and sheet:
   bridge.require_route(temp);_sheet(state,key)
  update={'status':'unknown' if unknown else 'failed','failure':str(failure)}
  if returned_path:
   from PIL import Image
   path=Path(returned_path).resolve()
   with Image.open(path) as im:im.verify()
   with Image.open(path) as im:size=list(im.size)
   update={'status':'returned',**_pin(path),'size_px':size}
  fingerprint=_result_fingerprint(update);resolved=resolve_receipt(state,key,token,sheet)
  matching=[f for f in resolved['facts'] if _result_fingerprint(f)==fingerprint]
  if matching:return {'status':'ALREADY_RECORDED','token':token,'receipt':dict(matching[0])}
  if any(f['status']=='returned' for f in resolved['facts']):raise ValueError('RECEIPT_CONFLICT')
  if not reconcile and call['status']!='reserved':raise ValueError('RECEIPT_CONFLICT')
  if reconcile and update['status']=='unknown' and resolved['facts']:raise ValueError('RECEIPT_CONFLICT')
  if reconcile and call['status']=='failed' and update['status']!='returned':raise ValueError('RECEIPT_CONFLICT')
  if update['status']=='returned':
   pin=_snapshot(state_path,returned_path)
   if pin['sha256']!=update['sha256']:raise ValueError('ACTUAL_RESULT_CHANGED_DURING_SNAPSHOT')
   update.update(pin)
  if reconcile:
   issues=[]
   try:bridge.require_route(temp)
   except (ValueError,OSError,KeyError,TypeError):issues.append('CURRENT_ROUTE_OR_APPROVAL_INVALID')
   event={**update,'token':token,'fingerprint':fingerprint,'origin':'reconcile-result','isolation_at_record':issues}
   for row in copies:row.setdefault('receipt_events',[]).append(dict(event))
   qualification=resolve_receipt(state,key,token,sheet)
   issues.extend(reason for reason in qualification['reasons'] if reason not in issues)
   for row in copies:row['receipt_events'][-1]['isolation_at_record']=list(issues)
  else:
   for row in copies:row.update(update)
  r._save_runtime_state(temp,state);result=resolve_receipt(state,key,token,sheet)
  if reconcile and issues:result['eligible']=False;result['reasons']+=issues
 return {'status':'RECONCILED','token':token,'receipt':dict(update),'use_disposition':'PENDING_REVALIDATION' if result['eligible'] else 'ARCHIVE_ONLY','reasons':result['reasons']} if reconcile else dict(call)


def reconcile_result(state_path,key,token,returned_path=None,failure=None,unknown=False,sheet=False):
 return _record_receipt(state_path,key,token,returned_path,failure,unknown,sheet,reconcile=True)


def query_result(state_path,key,token,sheet=False):
 state=r.load_runtime_state(state_path);result=resolve_receipt(state,key,token,sheet)
 if result['recovered']:
  try:bridge.require_route(state_path)
  except (ValueError,OSError,KeyError,TypeError):result['eligible']=False;result['reasons'].append('CURRENT_ROUTE_OR_APPROVAL_INVALID')
 result['evidence_status']='NOT_RETURNED'
 for fact in result['facts']:
  if fact['status']=='returned':
   try:_check_file(fact);result['evidence_status']='AVAILABLE'
   except OSError:result['evidence_status']='MISSING'
   except ValueError:result['evidence_status']='TAMPERED'
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['register-job','reserve','record-result','register-sheet','reserve-sheet','record-sheet-result','review-sheet','reconcile-result','query-result']);p.add_argument('--state',required=True);p.add_argument('--slide-id');p.add_argument('--region',nargs=4,type=float);p.add_argument('--role',choices=['foreground','background']);p.add_argument('--job-key');p.add_argument('--finding');p.add_argument('--token');p.add_argument('--returned-path');p.add_argument('--failure');p.add_argument('--unknown',action='store_true');p.add_argument('--sheet-key');p.add_argument('--spec');a=p.parse_args()
 try:
  if a.action=='register-job':result=register_job(a.state,a.slide_id,a.region,a.role)
  elif a.action=='reserve':result=reserve(a.state,a.job_key,a.finding)
  elif a.action=='record-result':result=record_result(a.state,a.job_key,a.token,a.returned_path,a.failure)
  elif a.action=='register-sheet':result=register_sheet(a.state,bridge.read(a.spec))
  elif a.action=='reserve-sheet':result=reserve_sheet(a.state,a.sheet_key)
  elif a.action=='record-sheet-result':result=record_sheet_result(a.state,a.sheet_key,a.token,a.returned_path,a.failure,a.unknown)
  elif a.action=='review-sheet':result=review_sheet(a.state,a.sheet_key,bridge.read(a.spec))
  elif a.action=='reconcile-result':result=reconcile_result(a.state,a.sheet_key or a.job_key,a.token,a.returned_path,a.failure,a.unknown,bool(a.sheet_key))
  else:result=query_result(a.state,a.sheet_key or a.job_key,a.token,bool(a.sheet_key))
 except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:result={'status':'FAIL','detail':str(exc)}
 print(json.dumps(result,ensure_ascii=False,indent=2));return int(result.get('status')=='FAIL')
if __name__=='__main__':raise SystemExit(main())
