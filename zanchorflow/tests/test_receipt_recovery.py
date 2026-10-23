"""Deterministic recovery/state fixtures, not model or Office validation."""
import sys,json,copy,shutil
from pathlib import Path
import pytest
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import editable_assets as a,editable_bridge as eb,runtime as rt,editable_split as split
from test_editable_sheets import setup,spec,asset


def prepare(tmp_path,sheet=True):
 state,keys=setup(tmp_path,n=2);key=keys[0]
 if sheet:key=a.register_sheet(state,spec(keys,[0]))['sheet_key'];token=a.reserve_sheet(state,key)['token']
 else:token=a.reserve(state,key)['token']
 image=tmp_path/'actual.png';im=Image.new('RGBA',(40,40));ImageDraw.Draw(im).rectangle([10,10,25,25],fill='green');im.save(image)
 return state,key,token,image,keys


def review(tmp_path,state,key,token,image,jk):
 rp=tmp_path/'regions.json';rp.write_text(json.dumps({'objects':[{'job_key':jk,'name':'icon','box':[0,0,40,40]}]}));report=tmp_path/'split.json';split.split_batch(image,tmp_path/'split',rp,report)
 evidence=tmp_path/'evidence.txt';evidence.write_text('OFFLINE review fixture, not visual model evidence')
 return a.review_sheet(state,key,{'token':token,'split_report':str(report),'items':[{'job_key':jk,'verdict':'accepted','finding':'OFFLINE fixture','evidence_paths':[str(evidence)],'checks':{k:True for k in ('identity','shape','detail','edges','background')}}]})


@pytest.mark.parametrize('sheet',[False,True])
def test_normal_replay_snapshot_query_and_conflict(tmp_path,sheet):
 state,key,token,image,keys=prepare(tmp_path,sheet);record=a.record_sheet_result if sheet else a.record_result
 first=record(state,key,token,image);assert first['status']=='returned';assert first['size_px']==[40,40];assert Path(first['path'])!=image
 other=tmp_path/'copy.png';shutil.copyfile(image,other);before=state.read_bytes();assert record(state,key,token,other)['status']=='ALREADY_RECORDED';assert before==state.read_bytes()
 assert a.reconcile_result(state,key,token,other,sheet=sheet)['status']=='ALREADY_RECORDED'
 Image.new('RGBA',(40,40),'red').save(other)
 with pytest.raises(ValueError,match='CONFLICT'):a.reconcile_result(state,key,token,other,sheet=sheet)
 image.unlink();q=a.query_result(state,key,token,sheet);assert q['evidence_status']=='AVAILABLE'
 with pytest.raises(OSError):record(state,key,token,image)


def test_approval_invalid_then_restored_can_revalidate(tmp_path):
 state,key,token,image,keys=prepare(tmp_path);data=rt.load_runtime_state(state);approval=data['stage2_run'].pop('visual_approval');rt._save_runtime_state(state,data)
 with pytest.raises(ValueError,match='APPROVAL'):a.record_sheet_result(state,key,token,image)
 result=a.reconcile_result(state,key,token,image,sheet=True);assert result['use_disposition']=='ARCHIVE_ONLY';assert not a.query_result(state,key,token,True)['eligible']
 data=rt.load_runtime_state(state);assert data['editable_asset_sheets'][key]['calls'][0]['status']=='reserved';data['stage2_run']['visual_approval']=approval;rt._save_runtime_state(state,data)
 assert a.query_result(state,key,token,True)['eligible'];review(tmp_path,state,key,token,image,keys[0]);data=rt.load_runtime_state(state);accepted=data['editable_asset_jobs'][keys[0]]['sheet_accepted'];item={'id':'icon','type':'image','sha256':accepted['asset']['sha256'],'provenance':{'kind':'generated','job_key':keys[0],'sheet_key':key,'returned_sha256':a.query_result(state,key,token,True)['effective']['sha256'],'review_sha256':accepted['review']['sha256'],'processing_finding':'OFFLINE split'}};src=eb.source(data,'S001')[0];a.validate_assets(data,{'objects':[item]},src)
 assert len(rt.load_runtime_state(state)['editable_asset_jobs'][keys[0]]['calls'])==1


def test_snapshot_damage_blocks_use_not_fact_and_restoration(tmp_path):
 state,key,token,image,keys=prepare(tmp_path);data=rt.load_runtime_state(state);snap=Path(data['editable_asset_sheets'][key]['body']['members'][0]['sources'][0]['snapshot']['path']);raw=snap.read_bytes();snap.write_bytes(b'damaged')
 with pytest.raises(ValueError,match='TAMPERED'):a.record_sheet_result(state,key,token,image)
 assert a.reconcile_result(state,key,token,image,sheet=True)['use_disposition']=='ARCHIVE_ONLY'
 with pytest.raises(ValueError):review(tmp_path,state,key,token,image,keys[0])
 snap.write_bytes(raw);assert a.query_result(state,key,token,True)['eligible']


def test_unknown_late_result_no_extra_attempt_and_review(tmp_path):
 state,key,token,image,keys=prepare(tmp_path);a.record_sheet_result(state,key,token,failure='unknown completion',unknown=True)
 a.reconcile_result(state,key,token,image,sheet=True);result=a.query_result(state,key,token,True);assert result['original_status']=='unknown' and result['effective']['status']=='returned'
 correction=a.register_sheet(state,spec(keys,[0],'correction'))['sheet_key']
 with pytest.raises(ValueError,match='FAILED_REVIEW'):a.reserve_sheet(state,correction)
 review(tmp_path,state,key,token,image,keys[0]);assert len(rt.load_runtime_state(state)['editable_asset_jobs'][keys[0]]['calls'])==1


@pytest.mark.parametrize('later_returned',[False,True])
def test_late_old_token_after_correction_is_archive_only(tmp_path,later_returned):
 state,key,token,image,keys=prepare(tmp_path);a.record_sheet_result(state,key,token,failure='unknown completion',unknown=True)
 correction=a.register_sheet(state,spec(keys,[0],'correction'))['sheet_key'];new=a.reserve_sheet(state,correction)['token']
 if later_returned:a.record_sheet_result(state,correction,new,failure='definite failure')
 result=a.reconcile_result(state,key,token,image,sheet=True);assert result['use_disposition']=='ARCHIVE_ONLY';data=rt.load_runtime_state(state);assert data['editable_asset_jobs'][keys[0]]['calls'][-1]['token']==new;assert len(data['editable_asset_jobs'][keys[0]]['calls'])==2
 with pytest.raises(ValueError):review(tmp_path,state,key,token,image,keys[0])


def test_cross_run_archive_preserves_current_run(tmp_path):
 state,key,token,image,keys=prepare(tmp_path);data=rt.load_runtime_state(state);data['stage2_run']['run_id']='new-run';rt._save_runtime_state(state,data)
 assert a.reconcile_result(state,key,token,image,sheet=True)['use_disposition']=='ARCHIVE_ONLY';assert rt.load_runtime_state(state)['stage2_run']['run_id']=='new-run'


@pytest.mark.parametrize('via_event',[False,True])
def test_failed_then_real_return_is_conflicting_evidence_not_usable(tmp_path,via_event):
 state,key,token,image,keys=prepare(tmp_path)
 if via_event:a.reconcile_result(state,key,token,failure='definite failure',sheet=True)
 else:a.record_sheet_result(state,key,token,failure='definite failure')
 assert a.reconcile_result(state,key,token,image,sheet=True)['use_disposition']=='ARCHIVE_ONLY'
 with pytest.raises(ValueError):review(tmp_path,state,key,token,image,keys[0])


@pytest.mark.parametrize('tamper',['token','body','member','identity','run'])
def test_invalid_identity_rejected_before_snapshot(tmp_path,monkeypatch,tamper):
 state,key,token,image,keys=prepare(tmp_path);data=rt.load_runtime_state(state)
 if tamper=='token':token='not-reserved'
 if tamper=='body':data['editable_asset_sheets'][key]['body']['size_px'][0]+=1
 if tamper=='member':data['editable_asset_jobs'][keys[0]]['calls'][0]['token']='wrong'
 if tamper=='identity':data['editable_asset_jobs'][keys[0]]['identity']['region_px'][2]=1
 if tamper=='run':data['editable_asset_jobs'][keys[0]]['calls'][0]['run_id']='wrong'
 rt._save_runtime_state(state,data);before=state.read_bytes()
 monkeypatch.setattr(a,'_snapshot',lambda *_:pytest.fail('snapshot before identity validation'))
 with pytest.raises(ValueError):a.reconcile_result(state,key,token,image,sheet=True)
 assert state.read_bytes()==before


def test_snapshot_orphan_after_commit_failure_is_not_receipt(tmp_path,monkeypatch):
 state,key,token,image,keys=prepare(tmp_path);before=state.read_bytes();save=rt._save_runtime_state
 def fail(*_):raise OSError('simulated commit failure')
 monkeypatch.setattr(rt,'_save_runtime_state',fail)
 with pytest.raises(OSError):a.reconcile_result(state,key,token,image,sheet=True)
 assert state.read_bytes()==before;assert a.query_result(state,key,token,True)['facts']==[]
 monkeypatch.setattr(rt,'_save_runtime_state',save);a.reconcile_result(state,key,token,image,sheet=True)
 assert a.reconcile_result(state,key,token,image,sheet=True)['status']=='ALREADY_RECORDED'


def test_legacy_records_without_new_metadata_continue_to_work(tmp_path):
 state,key,token,image,keys=prepare(tmp_path,False);data=rt.load_runtime_state(state);row=data['editable_asset_jobs'][key]['calls'][0]
 for field in ('run_id','identity_sha256','source_refs'):row.pop(field,None)
 rt._save_runtime_state(state,data);assert a.record_result(state,key,token,image)['status']=='returned';assert a.query_result(state,key,token)['evidence_status']=='AVAILABLE'


def test_query_missing_snapshot_and_conflicting_recovered_failure(tmp_path):
 state,key,token,image,keys=prepare(tmp_path);a.reconcile_result(state,key,token,failure='unknown',unknown=True,sheet=True)
 before=state.read_bytes()
 with pytest.raises(ValueError,match='CONFLICT'):a.reconcile_result(state,key,token,failure='different unknown',unknown=True,sheet=True)
 assert state.read_bytes()==before;a.reconcile_result(state,key,token,image,sheet=True);q=a.query_result(state,key,token,True);Path(q['effective']['path']).unlink();before=state.read_bytes();assert a.query_result(state,key,token,True)['evidence_status']=='MISSING';assert state.read_bytes()==before


def test_single_recovery_and_explicit_correction_finding(tmp_path):
 state,key,token,image,keys=prepare(tmp_path,False);a.reconcile_result(state,key,token,image);assert a.query_result(state,key,token)['eligible']
 with pytest.raises(ValueError,match='FINDING'):a.reserve(state,key)
 new=a.reserve(state,key,'explicit defect inspected in recovered result');assert new['token']!=token;assert a.query_result(state,key,token)['reasons']==['ARCHIVE_ONLY']


def test_normal_after_reconcile_is_idempotent(tmp_path):
 state,key,token,image,keys=prepare(tmp_path);a.reconcile_result(state,key,token,image,sheet=True);before=state.read_bytes();assert a.record_sheet_result(state,key,token,image)['status']=='ALREADY_RECORDED';assert state.read_bytes()==before


def test_recovered_accepted_sibling_survives_other_member_correction(tmp_path):
 state,keys=setup(tmp_path,n=2);key=a.register_sheet(state,spec(keys,[0,1]))['sheet_key'];token=a.reserve_sheet(state,key)['token']
 image=tmp_path/'actual.png';im=Image.new('RGBA',(80,40));draw=ImageDraw.Draw(im);draw.rectangle([10,10,25,25],fill='green');draw.rectangle([50,10,65,25],fill='blue');im.save(image);a.reconcile_result(state,key,token,image,sheet=True)
 rp=tmp_path/'regions.json';rp.write_text(json.dumps({'objects':[{'job_key':k,'name':str(i),'box':[40*i,0,40,40]} for i,k in enumerate(keys)]}));report=tmp_path/'split.json';split.split_batch(image,tmp_path/'split',rp,report);ev=tmp_path/'evidence';ev.write_text('OFFLINE fixture, not a model review')
 items=[{'job_key':k,'verdict':'accepted' if i==0 else 'failed','finding':'OFFLINE check','evidence_paths':[str(ev)],'checks':{c:True for c in ('identity','shape','detail','edges','background')}} for i,k in enumerate(keys)]
 a.review_sheet(state,key,{'token':token,'split_report':str(report),'items':items});before=copy.deepcopy(rt.load_runtime_state(state)['editable_asset_jobs'][keys[0]]['sheet_accepted'])
 other=a.register_sheet(state,spec(keys,[1],'correction'))['sheet_key'];a.reserve_sheet(state,other)
 assert a.query_result(state,keys[0],token)['eligible'];assert not a.query_result(state,key,token,True)['eligible']
 data=rt.load_runtime_state(state);assert data['editable_asset_jobs'][keys[0]]['sheet_accepted']==before
 item={'id':'icon','type':'image','sha256':before['asset']['sha256'],'provenance':{'kind':'generated','job_key':keys[0],'sheet_key':key,'returned_sha256':a.query_result(state,keys[0],token)['effective']['sha256'],'review_sha256':before['review']['sha256'],'processing_finding':'OFFLINE split'}};a.validate_assets(data,{'objects':[item]},eb.source(data,'S001')[0])


def test_source_isolation_reason_is_preserved_after_restore(tmp_path):
 state,key,token,image,keys=prepare(tmp_path);data=rt.load_runtime_state(state)
 pin=data['editable_asset_sheets'][key]['body']['members'][0]['sources'][0]['snapshot'];source=Path(pin['path']);original=source.read_bytes();source.write_bytes(b'damaged')
 a.reconcile_result(state,key,token,image,sheet=True)
 event=rt.load_runtime_state(state)['editable_asset_sheets'][key]['calls'][0]['receipt_events'][0]
 assert 'SOURCE_OR_EVIDENCE_NOT_CURRENT' in event['isolation_at_record']
 source.write_bytes(original);assert a.query_result(state,key,token,True)['eligible']
 assert rt.load_runtime_state(state)['editable_asset_sheets'][key]['calls'][0]['receipt_events'][0]==event


def test_normal_sheet_rechecks_route_inside_transaction(tmp_path,monkeypatch):
 state,key,token,image,keys=prepare(tmp_path);require=eb.require_route;seen=[]
 def guard(path):
  seen.append(str(path))
  if len(seen)>1:raise ValueError('approval changed before transaction')
  return require(path)
 monkeypatch.setattr(eb,'require_route',guard);before=state.read_bytes()
 with pytest.raises(ValueError,match='approval changed'):a.record_sheet_result(state,key,token,image)
 assert state.read_bytes()==before;assert len(seen)==2


@pytest.mark.parametrize('recovered',[False,True])
def test_single_return_evidence_must_exist_and_match_at_use(tmp_path,recovered):
 state,key,token,image,keys=prepare(tmp_path,False)
 if recovered:a.reconcile_result(state,key,token,image)
 else:a.record_result(state,key,token,image)
 data=rt.load_runtime_state(state);receipt=a.resolve_receipt(data,key,token)['effective'];src=eb.source(data,'S001')[0]
 item={'id':'icon','type':'image','sha256':receipt['sha256'],'provenance':{'kind':'generated','job_key':key,'returned_sha256':receipt['sha256']}}
 a.validate_assets(data,{'objects':[item]},src);Path(receipt['path']).write_bytes(b'tampered')
 with pytest.raises(ValueError,match='TAMPERED'):a.validate_assets(data,{'objects':[item]},src)
 Path(receipt['path']).unlink()
 with pytest.raises(OSError):a.validate_assets(data,{'objects':[item]},src)
