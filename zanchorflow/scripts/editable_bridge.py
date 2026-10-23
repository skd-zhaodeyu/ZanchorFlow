"""Editable Path provenance and page transitions; image tools remain host-owned."""
import argparse,copy,hashlib,json
from pathlib import Path
import runtime as r
import reconstruction_router as router
import editable_build

def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def resolve(state,value):
 p=Path(value);return p if p.is_absolute() else Path(state['_base_dir'])/p

def enable(state_path):
 with router.transaction(state_path) as temp:
  state=r.load_runtime_state(temp);run=state['stage2_run']
  if state.get('reconstruction_backend') or router._has_backend_work(state):return {'status':'LEGACY_ROUTE_PRESERVED'}
  run['reconstruction_selection_timing']='before_cleanup';r._save_runtime_state(temp,state)
 return {'status':'EARLY_SELECTION_ENABLED'}

def source(state,sid):
 run=state['stage2_run'];slide=state['slides'][sid]
 render=resolve(state,slide['approved_render']);truth_file=resolve(state,slide['final_content_truth']);truth=read(truth_file)
 canvas=read(resolve(state,slide['canvas'])) if slide.get('canvas') else {}
 return {'run_id':run['run_id'],'slide_id':sid,'source_fingerprint':r.source_fingerprint(render.read_bytes(),truth,canvas),'render':str(render),'visual_approval':copy.deepcopy(run.get('visual_approval')),'target_slide_emu':copy.deepcopy(state.get('reconstruction_backend',{}).get('target_slide_emu')),'truth_sha256':sha(truth_file.read_bytes()),'canvas':canvas},truth

def require_route(state_path):
 r.require_stage2_visual_approval(state_path)
 if r.stage2_handoff_status(state_path)['status']!='COMPLETE':raise ValueError('EDITABLE_HANDOFF_REQUIRED')
 if router.selected_backend(state_path)!='editable_path':raise ValueError('EDITABLE_SELECTION_REQUIRED')

def text_pieces(plan):
 for item in plan['objects']:
  if item['type']=='table':
   for ri,row in enumerate(item['cells']):
    for ci,cell in enumerate(row):yield item['id']+':'+str(ri)+':'+str(ci),cell,'text'
  elif item['type'] in ('text','image'):yield item['id'],item,item['type']

def validate_truth(plan,truth,sid):
 expected=r._truth_occurrence_map(truth,sid);actual={}
 for name,piece,kind in text_pieces(plan):
  refs=piece.get('occurrence_ids',[]);value=piece.get('text','') if kind=='text' else piece.get('semantic_text','')
  if refs:
   if len(refs)!=1 or refs[0] in actual:raise ValueError('EDITABLE_TRUTH_OCCURRENCE_INVALID')
   if kind=='image':
    role=piece.get('representation_role');evidence=piece.get('preservation_evidence',{})
    if role not in ('graphic_typography','formula') or any(evidence.get(k) is not True for k in ('content_verified','source_verified','substitution_material_loss')):raise ValueError('EDITABLE_PROTECTED_TEXT_EVIDENCE_REQUIRED')
    if role=='graphic_typography' and any(evidence.get(k) is not True for k in ('design_approved','composition_critical','native_text_substitution_material_loss')):raise ValueError('EDITABLE_PROTECTED_TEXT_EVIDENCE_REQUIRED')
   if piece.get('paragraphs'):
    observed='\n'.join(''.join(run.get('text','') for run in paragraph.get('runs',[])) for paragraph in piece['paragraphs'])
    if observed!=value:raise ValueError('EDITABLE_TRUTH_FORMATTED_TEXT_MISMATCH')
   actual[refs[0]]=value
  elif value:raise ValueError('EDITABLE_TRUTH_UNBOUND_TEXT')
 if actual!=expected:raise ValueError('EDITABLE_TRUTH_MISMATCH')

def validate_title(state,sid,plan):
 if state.get('stage2_run',{}).get('title_policy',{}).get('mode')!='uniform':return
 elements=[]
 for name,piece,kind in text_pieces(plan):
  refs=piece.get('occurrence_ids',[])
  if kind=='text' and len(refs)==1:elements.append({'id':name,'content':piece.get('text',''),'truth_ref':refs[0],'representation_role':'native_text','treatment':'remove_and_restore','truth_source':'stage2_final_content_truth'})
 # Adapt only title identity checks. No cleanup inventory or text-clean artifact is fabricated.
 import title_policy
 title_policy.validate_manifest(state,sid,{'slide_id':sid,'title_contract_ref':plan.get('title_contract_ref'),'title_element_ids':plan.get('title_element_ids'),'text_elements':elements})

def register_plan(state_path,sid,plan_path):
 require_route(state_path);state=r.load_runtime_state(state_path);src,truth=source(state,sid);plan=read(plan_path)
 editable_build.validate(plan);validate_truth(plan,truth,sid);validate_title(state,sid,plan)
 if plan['slide_size_emu']!=src['target_slide_emu']:raise ValueError('EDITABLE_TARGET_CANVAS_MISMATCH')
 from editable_assets import validate_assets
 validate_assets(state,plan,src)
 from PIL import Image
 with Image.open(src['render']) as im:
  if list(im.size)!=plan['source_size_px']:raise ValueError('EDITABLE_SOURCE_SIZE_MISMATCH')
 canvas=src['canvas'];target=[canvas.get('target_slide_width_emu'),canvas.get('target_slide_height_emu')]
 if any(v is not None for v in target) and plan['slide_size_emu']!=target:raise ValueError('EDITABLE_TARGET_CANVAS_MISMATCH')
 raw=r._canonical({'source':src,'plan':plan});digest=sha(raw)
 root=Path(state_path).resolve().parent/'editable-plans'/src['run_id'];root.mkdir(parents=True,exist_ok=True);path=root/(sid+'-'+digest+'.json')
 if path.exists():
  if path.read_bytes()!=raw:raise ValueError('EDITABLE_FROZEN_PLAN_TAMPERED')
 else:
  with path.open('xb') as f:f.write(raw)
 record={'path':str(path),'sha256':digest,'source':src}
 with router.transaction(state_path) as temp:
  current=r.load_runtime_state(temp)
  if source(current,sid)[0]!=src:raise ValueError('EDITABLE_SOURCE_CHANGED')
  bridge=current.setdefault('editable_bridge',{});old=bridge.setdefault('plans',{}).get(sid)
  if old==record:return record
  if old:bridge.setdefault('plan_history',[]).append({'slide_id':sid,'record':old})
  bridge['plans'][sid]=record
  for section in ('built','validated'):
   previous=bridge.get(section,{}).pop(sid,None)
   if previous:bridge.setdefault('superseded',[]).append({'section':section,'slide_id':sid,'record':previous})
  r._save_runtime_state(temp,current)
 return record

def current_plan(state,sid):
 rec=state['editable_bridge']['plans'][sid];path=resolve(state,rec['path']);raw=path.read_bytes()
 if sha(raw)!=rec['sha256']:raise ValueError('EDITABLE_FROZEN_PLAN_TAMPERED')
 payload=json.loads(raw);src,truth=source(state,sid)
 if payload['source']!=src or rec['source']!=src:raise ValueError('EDITABLE_SOURCE_STALE')
 plan=payload['plan'];editable_build.validate(plan);validate_truth(plan,truth,sid);validate_title(state,sid,plan)
 if plan['slide_size_emu']!=src['target_slide_emu']:raise ValueError('EDITABLE_TARGET_CANVAS_MISMATCH')
 from editable_assets import validate_assets
 validate_assets(state,plan,src)
 return rec,plan

def expected_lineage(state,sid):
 record,plan=current_plan(state,sid)
 return {'slide_id':sid,'backend':'editable_path','source_fingerprint':record['source']['source_fingerprint'],'editable_plan_sha256':record['sha256'],'editable_assets_sha256':sha(r._canonical([(v['id'],v.get('sha256')) for v in plan['objects'] if v['type']=='image']))}

def build_page(state_path,sid,output):
 require_route(state_path);state=r.load_runtime_state(state_path);record,plan=current_plan(state,sid)
 result=editable_build.build(plan,output);result.update(expected_lineage(state,sid))
 with router.transaction(state_path) as temp:
  now=r.load_runtime_state(temp)
  if expected_lineage(now,sid)!=expected_lineage(state,sid):raise ValueError('EDITABLE_INPUT_CHANGED_DURING_BUILD')
  bridge=now.setdefault('editable_bridge',{});previous=bridge.setdefault('built',{}).get(sid)
  if previous:bridge.setdefault('build_history',[]).append({'slide_id':sid,'record':previous})
  bridge['built'][sid]=result
  old=bridge.get('validated',{}).pop(sid,None)
  if old:bridge.setdefault('superseded',[]).append({'section':'validated','slide_id':sid,'record':old})
  seal=now['slides'][sid].pop('validated_single_page',None)
  if seal:now['slides'][sid].setdefault('superseded_validated_single_pages',[]).append(seal)
  r._save_runtime_state(temp,now)
 return result

def review_current(state,sid,review_path):
 lineage=expected_lineage(state,sid);built=state['editable_bridge']['built'][sid]
 manifest_raw=resolve(state,built['resolved_manifest']).read_bytes()
 if sha(manifest_raw)!=built['resolved_manifest_sha256'] or json.loads(manifest_raw)['pptx_sha256']!=built['sha256']:raise ValueError('EDITABLE_RESOLVED_MANIFEST_STALE')
 raw=resolve(state,review_path).read_bytes();review=json.loads(raw)
 if sha(resolve(state,built['path']).read_bytes())!=built['sha256'] or review.get('pptx_sha256')!=built['sha256'] or review.get('lineage')!=lineage:raise ValueError('EDITABLE_REVIEW_BYTES_MISMATCH')
 if review.get('checks')!={k:'PASS' for k in r.GATE_NAMES}:raise ValueError('EDITABLE_FOUR_GATES_REQUIRED')
 for key in r.GATE_NAMES:
  evidence=review.get('evidence',{}).get(key,{})
  if not isinstance(evidence.get('finding'),str) or not evidence['finding'].strip() or not evidence.get('file') or sha(resolve(state,evidence['file']).read_bytes())!=evidence.get('sha256'):raise ValueError('EDITABLE_GATE_EVIDENCE_REQUIRED: '+key)
 return lineage,copy.deepcopy(built),sha(raw)

def seal_page(state_path,sid,review_path):
 require_route(state_path);state=r.load_runtime_state(state_path)
 initial=review_current(state,sid,review_path)
 with router.transaction(state_path) as temp:
  now=r.load_runtime_state(temp)
  if review_current(now,sid,review_path)!=initial:raise ValueError('EDITABLE_REVIEW_STALE')
  lineage,built,review_sha=initial
  r.seal_validated_single_page(temp,sid,built['path'],{k:'PASS' for k in r.GATE_NAMES});now=r.load_runtime_state(temp)
  now['editable_bridge'].setdefault('validated',{})[sid]={'pptx_sha256':built['sha256'],'review_path':str(Path(review_path).resolve()),'review_sha256':review_sha,'lineage':lineage};r._save_runtime_state(temp,now)
 return {'status':'PAGE_SEALED','slide_id':sid}

def page_provenance(state,sid):
 line=expected_lineage(state,sid);rec=state['editable_bridge']['validated'][sid]
 review_current(state,sid,rec['review_path'])
 if rec['lineage']!=line or sha(resolve(state,rec['review_path']).read_bytes())!=rec['review_sha256']:raise ValueError('EDITABLE_PAGE_REVIEW_STALE')
 sealed=state['slides'][sid]['validated_single_page']
 if r.validate_current_artifact(sealed,state,sid) or sealed['validated_pptx_sha256']!=rec['pptx_sha256']:raise ValueError('EDITABLE_PAGE_STALE')
 return {**line,'validated_pptx_sha256':rec['pptx_sha256'],'review_sha256':rec['review_sha256']}

def status(state_path):
 state=r.load_runtime_state(state_path)
 for sid in state['stage2_run']['page_order']:
  if sid not in state.get('editable_bridge',{}).get('plans',{}):return {'status':'EDITABLE_PLAN_REQUIRED','slide_id':sid}
  try:current_plan(state,sid)
  except (KeyError,ValueError,OSError):return {'status':'EDITABLE_PLAN_STALE','slide_id':sid}
  built=state['editable_bridge'].get('built',{}).get(sid)
  if not built:return {'status':'EDITABLE_BUILD_REQUIRED','slide_id':sid}
  try:
   if sha(resolve(state,built['path']).read_bytes())!=built['sha256']:return {'status':'EDITABLE_BUILD_STALE','slide_id':sid}
   page_provenance(state,sid)
  except (KeyError,ValueError,OSError):return {'status':'EDITABLE_REVIEW_REQUIRED','slide_id':sid}
 return {'status':'EDITABLE_PAGES_SEALED'}

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['enable-early-selection','register-plan','build','seal-page','status']);p.add_argument('--state',required=True);p.add_argument('--slide-id');p.add_argument('--plan');p.add_argument('--output');p.add_argument('--review');a=p.parse_args()
 try:
  if a.action=='enable-early-selection':v=enable(a.state)
  elif a.action=='register-plan':v=register_plan(a.state,a.slide_id,a.plan)
  elif a.action=='build':v=build_page(a.state,a.slide_id,a.output)
  elif a.action=='seal-page':v=seal_page(a.state,a.slide_id,a.review)
  else:v=status(a.state)
 except (KeyError,ValueError,OSError,TypeError) as e:v={'status':'FAIL','detail':str(e)}
 print(json.dumps(v,ensure_ascii=False,indent=2));return int(v.get('status')=='FAIL')
if __name__=='__main__':raise SystemExit(main())
