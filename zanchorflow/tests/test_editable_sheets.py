"""Offline state/processing fixtures, not model quality or Office evidence."""
import sys,json,copy
from pathlib import Path
import pytest
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import runtime as rt
import editable_assets as a
import editable_bridge as eb
import editable_split as split
import reconstruction_router as router
from test_reconstruction_backend_router import write_truth


def setup(tmp_path,n=4,same=False):
 outline={'slides':[{k:f'{k}-{i}' for k in ('page_task','title','core_expression','key_information','semantic_relation','acceptance_criteria')} for i in range(n)]}
 op=tmp_path/'outline.json';op.write_text(json.dumps(outline));state=tmp_path/'state.json';state.write_text('{"slides":{}}')
 rt.record_stage1_draft(state,op);rt.present_stage1_review(state);rt.handle_stage1_reply(state,'approve',decision='approve');rt.start_stage2_run(state)
 for kind in ('anchor','style_dna'):
  f=tmp_path/kind;f.write_bytes(kind.encode());rt.register_stage2_artifact(state,kind,f)
 for i in range(n):
  sid=f'S{i+1:03d}';f=tmp_path/(sid+'.png');Image.new('RGB',(10,10),(30 if same else 30+i,90,130)).save(f)
  c=rt.register_stage2_candidate(state,sid,f,generation_intent='OFFLINE fixture');rt.review_stage2_candidate(state,c['candidate_id'],'PASS')
 rt.present_stage2_formal_display(state);rt.seal_stage2_visual_approval(state,'OFFLINE synthetic approval fixture')
 for i in range(n):
  sid=f'S{i+1:03d}';f=write_truth(tmp_path/(sid+'-truth.json'),sid);rt.register_stage2_artifact(state,'final_content_truth:'+sid,f);rt.mark_stage2_text_reconciled(state,sid)
 eb.enable(state);router.choose_backend(state,'editable_path')
 keys=[a.register_job(state,f'S{i+1:03d}',[0,0,10,10],'foreground')['job_key'] for i in range(n)]
 return state,keys


def spec(keys,indices=None,stage='initial'):
 indices=list(range(len(keys))) if indices is None else indices
 return {'stage':stage,'size_px':[256,96],'padding_px':8,'background':'transparent','seal_reason':'queue_end','members':[{'job_key':keys[i],'sources':[{'slide_id':f'S{i+1:03d}','object_ref':'icon'}],'box':[16+48*j,16,24,24],**({'finding':'missing detached detail'} if stage=='correction' else {})} for j,i in enumerate(indices)]}


def returned(tmp_path,state,key,bad=None,reject=None):
 token=a.reserve_sheet(state,key)['token'];body=rt.load_runtime_state(state)['editable_asset_sheets'][key]['body'];im=Image.new('RGBA',(256,96));d=ImageDraw.Draw(im);objects=[]
 for j,m in enumerate(body['members']):
  box=[8+48*j,8,40,56];x,y,w,h=box
  if j!=bad:d.rectangle([x+8,y+8,x+25,y+30],fill=(20,80,140,255));d.point((x+30,y+7),fill=(180,180,180,5))
  objects.append({'job_key':m['job_key'],'name':'obj'+str(j),'box':None if j==bad else box})
 image=tmp_path/(key[:8]+'.png');im.save(image);a.record_sheet_result(state,key,token,image)
 regions=tmp_path/(key[:8]+'-regions.json');regions.write_text(json.dumps({'objects':objects}));report=tmp_path/(key[:8]+'-split.json')
 split.split_batch(image,tmp_path/(key[:8]+'-assets'),regions,report)
 evidence=tmp_path/'evidence.txt';evidence.write_text('OFFLINE fixture only; no visual/model/Office verification')
 items=[{'job_key':m['job_key'],'verdict':'failed' if j==bad or j==reject else 'accepted','finding':'missing' if j==bad else 'OFFLINE structural acceptance fixture','checks':{k:True for k in ('identity','shape','detail','edges','background')},'evidence_paths':[str(evidence)]} for j,m in enumerate(body['members'])]
 review=a.review_sheet(state,key,{'token':token,'split_report':str(report),'items':items})
 return token,review,report


def asset(state,sid,key):
 data=rt.load_runtime_state(state);accepted=data['editable_asset_jobs'][key]['sheet_accepted'];sheet=data['editable_asset_sheets'][accepted['sheet_key']]
 return {'id':'icon','type':'image','path':accepted['asset']['path'],'sha256':accepted['asset']['sha256'],'provenance':{'kind':'generated','job_key':key,'sheet_key':accepted['sheet_key'],'returned_sha256':sheet['calls'][-1]['sha256'],'review_sha256':accepted['review']['sha256'],'processing_finding':'OFFLINE split fixture'}},eb.source(data,sid)[0]


def test_three_pages_shared_call_and_fourth_next_sheet(tmp_path):
 state,keys=setup(tmp_path);key=a.register_sheet(state,spec(keys,[0,1,2]))['sheet_key'];token,review,_=returned(tmp_path,state,key)
 data=rt.load_runtime_state(state);assert {data['editable_asset_jobs'][k]['calls'][0]['token'] for k in keys[:3]}=={token};assert not data['editable_asset_jobs'][keys[3]]['calls']
 for i,k in enumerate(keys[:3]):
  item,src=asset(state,f'S{i+1:03d}',k);a.validate_assets(data,{'objects':[item]},src)
 other=a.register_sheet(state,spec(keys,[3]))['sheet_key'];assert other!=key
 with pytest.raises(ValueError,match='THREE_PAGE'):a.register_sheet(state,spec(keys))


def test_partial_failure_regroup_and_keep_accepted(tmp_path):
 state,keys=setup(tmp_path);first=a.register_sheet(state,spec(keys,[0,1]))['sheet_key'];returned(tmp_path,state,first,bad=1)
 before=copy.deepcopy(rt.load_runtime_state(state)['editable_asset_jobs'][keys[0]]['sheet_accepted'])
 second=a.register_sheet(state,spec(keys,[2,3]))['sheet_key'];returned(tmp_path,state,second,bad=0)
 correction=a.register_sheet(state,spec(keys,[1,2],'correction'))['sheet_key'];returned(tmp_path,state,correction)
 data=rt.load_runtime_state(state);assert data['editable_asset_jobs'][keys[0]]['sheet_accepted']==before
 assert [len(data['editable_asset_jobs'][k]['calls']) for k in keys]==[1,2,2,1]


@pytest.mark.parametrize('unknown',[False,True])
def test_failure_atomicity_and_exhaustion(tmp_path,unknown):
 state,keys=setup(tmp_path);key=a.register_sheet(state,spec(keys,[0,1]))['sheet_key'];token=a.reserve_sheet(state,key)['token']
 with pytest.raises(ValueError):a.reserve(state,keys[0],'bypass')
 with pytest.raises(ValueError):a.record_result(state,keys[0],token,failure='bypass')
 a.record_sheet_result(state,key,token,failure='OFFLINE tool failure',unknown=unknown)
 correction=a.register_sheet(state,spec(keys,[0,1],'correction'))['sheet_key'];token=a.reserve_sheet(state,correction)['token'];a.record_sheet_result(state,correction,token,failure='OFFLINE failure')
 before=state.read_bytes();third=a.register_sheet(state,{**spec(keys,[0,2],'correction'),'finding':'changed grouping'})['sheet_key']
 calls_before=copy.deepcopy(rt.load_runtime_state(state)['editable_asset_jobs'])
 with pytest.raises(ValueError,match='EXHAUSTED'):a.reserve_sheet(state,third)
 assert rt.load_runtime_state(state)['editable_asset_jobs']==calls_before


@pytest.mark.parametrize('change,match',[
 ('duplicate','DUPLICATE'),('small','DOWNSAMPLING'),('overlap','OVERLAP'),('finding','FINDING'),('wrong-source','SOURCE_MISMATCH')])
def test_registration_rejections(tmp_path,change,match):
 state,keys=setup(tmp_path);s=spec(keys,[0,1])
 if change=='duplicate':s['members'][1]['job_key']=keys[0]
 if change=='small':s['members'][0]['box'][2]=5
 if change=='overlap':s['members'][1]['box']=s['members'][0]['box'][:]
 if change=='finding':s['seal_reason']='capacity'
 if change=='wrong-source':s['members'][0]['sources'][0]['slide_id']='S002'
 with pytest.raises(ValueError,match=match):a.register_sheet(state,s)


def test_repeated_source_one_attempt_multiple_page_refs(tmp_path):
 state,keys=setup(tmp_path,same=True);assert len(set(keys))==1
 s=spec(keys,[0]);s['members'][0]['sources']=[{'slide_id':f'S{i:03d}','object_ref':'icon'} for i in range(1,4)]
 key=a.register_sheet(state,s)['sheet_key'];returned(tmp_path,state,key)
 assert len(rt.load_runtime_state(state)['editable_asset_jobs'][keys[0]]['calls'])==1
 # A fourth page reuses the same source object without a new call.
 item,src=asset(state,'S004',keys[0]);a.validate_assets(rt.load_runtime_state(state),{'objects':[item]},src)


@pytest.mark.parametrize('target',['asset','report','regions','returned','review','snapshot'])
def test_evidence_tamper_rejected(tmp_path,target):
 state,keys=setup(tmp_path);key=a.register_sheet(state,spec(keys,[0]))['sheet_key'];_,review,report=returned(tmp_path,state,key)
 item,src=asset(state,'S001',keys[0]);data=rt.load_runtime_state(state);sheet=data['editable_asset_sheets'][key]
 paths={'asset':item['path'],'report':str(report),'regions':json.loads(report.read_text())['regions_source'],'returned':sheet['calls'][0]['path'],'review':review['review']['path'],'snapshot':sheet['body']['members'][0]['sources'][0]['snapshot']['path']}
 Path(paths[target]).write_bytes(b'tampered')
 with pytest.raises((ValueError,OSError)):a.validate_assets(rt.load_runtime_state(state),{'objects':[item]},src)


def test_other_page_change_does_not_invalidate_accepted_asset(tmp_path):
 state,keys=setup(tmp_path);key=a.register_sheet(state,spec(keys,[0,1]))['sheet_key'];returned(tmp_path,state,key)
 data=rt.load_runtime_state(state);other=eb.source(data,'S002')[0];Image.new('RGB',(10,10),'red').save(other['render'])
 item,src=asset(state,'S001',keys[0]);a.validate_assets(rt.load_runtime_state(state),{'objects':[item]},src)
 item,src=asset(state,'S002',keys[1])
 with pytest.raises(ValueError):a.validate_assets(rt.load_runtime_state(state),{'objects':[item]},src)


def test_pending_initial_and_accepted_retry_rejected(tmp_path):
 state,keys=setup(tmp_path);key=a.register_sheet(state,spec(keys,[0]))['sheet_key'];assert a.register_sheet(state,spec(keys,[0]))['sheet_key']==key
 a.reserve_sheet(state,key)
 another=a.register_sheet(state,{**spec(keys,[0]),'background':'#ff00ff'})['sheet_key']
 with pytest.raises(ValueError,match='PENDING'):a.reserve_sheet(state,another)


def test_batch_partial_boundary_missing_and_faint_detail(tmp_path):
 im=Image.new('RGBA',(160,80));d=ImageDraw.Draw(im);d.rectangle([10,10,25,25],fill='blue');d.point((33,12),fill=(20,80,120,3));d.rectangle([60,10,75,25],fill='red');src=tmp_path/'sheet.png';im.save(src)
 regions=tmp_path/'regions.json';regions.write_text(json.dumps({'objects':[{'job_key':'good','box':[1,1,40,40]},{'job_key':'edge','box':[60,1,40,40]},{'job_key':'missing','box':None}]}))
 report=split.split_batch(src,tmp_path/'assets',regions,tmp_path/'report.json');assert report['sheet_safe'];assert [v['status'] for v in report['assets']]==['extracted','failed','failed']
 with Image.open(report['assets'][0]['path']) as out:assert out.getchannel('A').histogram()[3]>0
 with pytest.raises(ValueError):split.split_batch(src,tmp_path/'assets',regions,tmp_path/'report2.json')


def test_batch_unowned_foreground_blocks_acceptance(tmp_path):
 src=tmp_path/'sheet.png';im=Image.new('RGBA',(40,40));im.putpixel((20,20),(255,0,0,255));im.save(src);regions=tmp_path/'regions.json';regions.write_text(json.dumps({'objects':[{'job_key':'missing','box':None}]}))
 result=split.split_batch(src,tmp_path/'assets',regions,tmp_path/'report.json');assert not result['sheet_safe']


def test_source_truth_change_cannot_be_reregistered_to_reuse_old_result(tmp_path):
 state,keys=setup(tmp_path);key=a.register_sheet(state,spec(keys,[0]))['sheet_key'];returned(tmp_path,state,key)
 data=rt.load_runtime_state(state);truth=Path(data['slides']['S001']['final_content_truth']);payload=json.loads(truth.read_text());payload['extra_source_note']='changed';truth.write_text(json.dumps(payload))
 # Re-registering a source reference must not overwrite the old frozen origin.
 src=eb.source(rt.load_runtime_state(state),'S001')[0];data=rt.load_runtime_state(state);data['editable_asset_jobs'][keys[0]]['source_refs']['S001']['source_fingerprint']=src['source_fingerprint'];rt._save_runtime_state(state,data)
 item,src=asset(state,'S001',keys[0])
 with pytest.raises(ValueError,match='PAGE_SOURCE_STALE'):a.validate_assets(rt.load_runtime_state(state),{'objects':[item]},src)


def test_accepted_retry_rejected_and_local_review_can_accept_failed_without_call(tmp_path):
 state,keys=setup(tmp_path);key=a.register_sheet(state,spec(keys,[0]))['sheet_key'];returned(tmp_path,state,key)
 correction=a.register_sheet(state,spec(keys,[0],stage='correction'))['sheet_key']
 with pytest.raises(ValueError,match='ALREADY_ACCEPTED'):a.reserve_sheet(state,correction)
 assert len(rt.load_runtime_state(state)['editable_asset_jobs'][keys[0]]['calls'])==1


def test_cross_run_reserve_and_review_identity_are_blocked(tmp_path):
 state,keys=setup(tmp_path);key=a.register_sheet(state,spec(keys,[0]))['sheet_key'];data=rt.load_runtime_state(state);data['stage2_run']['run_id']='different-run';rt._save_runtime_state(state,data)
 with pytest.raises(ValueError):a.reserve_sheet(state,key)


def test_failed_review_can_be_locally_fixed_without_new_image_call(tmp_path):
 state,keys=setup(tmp_path);key=a.register_sheet(state,spec(keys,[0]))['sheet_key'];token,old,report=returned(tmp_path,state,key,reject=0)
 evidence=tmp_path/'local.txt';evidence.write_text('OFFLINE local re-review fixture, not model evidence')
 review=a.review_sheet(state,key,{'token':token,'split_report':str(report),'items':[{'job_key':keys[0],'verdict':'accepted','finding':'OFFLINE local crop now checked','evidence_paths':[str(evidence)],'checks':{k:True for k in ('identity','shape','detail','edges','background')}}]})
 data=rt.load_runtime_state(state);assert len(data['editable_asset_jobs'][keys[0]]['calls'])==1;assert len(data['editable_asset_sheets'][key]['reviews'])==2
 assert Path(old['review']['path']).exists() and review['review']['sha256']!=old['review']['sha256']


def test_failed_review_tamper_cannot_authorize_correction(tmp_path):
 state,keys=setup(tmp_path);key=a.register_sheet(state,spec(keys,[0]))['sheet_key'];_,review,_=returned(tmp_path,state,key,bad=0);Path(review['review']['path']).write_text('tampered')
 correction=a.register_sheet(state,spec(keys,[0],stage='correction'))['sheet_key']
 with pytest.raises(ValueError,match='TAMPERED'):a.reserve_sheet(state,correction)


@pytest.mark.parametrize('name',['../escape','C:stream','CON','bad.','bad?'])
def test_batch_unsafe_names_rejected(tmp_path,name):
 src=tmp_path/'sheet.png';Image.new('RGBA',(10,10)).save(src);rp=tmp_path/'regions.json';rp.write_text(json.dumps({'objects':[{'job_key':'a','name':name,'box':None}]}))
 with pytest.raises(ValueError):split.split_batch(src,tmp_path/'out',rp,tmp_path/'report.json')
 assert not (tmp_path/'out').exists()


def test_unaccepted_or_wrong_member_result_cannot_be_used(tmp_path):
 state,keys=setup(tmp_path);key=a.register_sheet(state,spec(keys,[0,1]))['sheet_key'];returned(tmp_path,state,key,bad=1)
 item,src=asset(state,'S001',keys[0]);item['provenance']['job_key']=keys[1]
 with pytest.raises(ValueError):a.validate_assets(rt.load_runtime_state(state),{'objects':[item]},src)


def test_accepted_result_cannot_be_overwritten_by_later_review(tmp_path):
 state,keys=setup(tmp_path);key=a.register_sheet(state,spec(keys,[0]))['sheet_key'];token,review,report=returned(tmp_path,state,key)
 before=state.read_bytes();e=tmp_path/'evidence.txt'
 with pytest.raises(ValueError,match='IMMUTABLE'):a.review_sheet(state,key,{'token':token,'split_report':str(report),'items':[{'job_key':keys[0],'verdict':'failed','finding':'attempt to revoke accepted result','evidence_paths':[str(e)]}]})
 assert state.read_bytes()==before
