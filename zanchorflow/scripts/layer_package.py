"""Package normalized full-canvas Image Layer results into a canonical Layer Bundle v3 (v2 legacy explicitly supported)."""
import argparse
import hashlib
import json
import shutil
import layer_geometry_verify
from pathlib import Path
from PIL import Image
import layer_geometry


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def safe_child(base,value):
    rel=Path(value)
    if rel.is_absolute() or '..' in rel.parts: raise ValueError('LAYER_RESULT_INVALID: layer path escapes result directory')
    path=(Path(base)/rel).resolve(); root=Path(base).resolve()
    if root not in path.parents and path!=root: raise ValueError('LAYER_RESULT_INVALID: layer path escapes result directory')
    return path


def package_layers(source_image,plan_path,backend_result_path,output_dir, *, schema_version=3, explicit_target_emu=None):
    source_image=Path(source_image).resolve(); plan_path=Path(plan_path).resolve(); backend_result_path=Path(backend_result_path).resolve(); output_dir=Path(output_dir).resolve()
    plan=json.loads(plan_path.read_text(encoding='utf-8')); result=json.loads(backend_result_path.read_text(encoding='utf-8'))
    with Image.open(source_image) as im: source_size=im.size
    if explicit_target_emu is not None:
        from reconstruction_router import validate_image_target_emu
        explicit_target_emu=validate_image_target_emu(explicit_target_emu)
        sw,sh=source_size; tw,th=explicit_target_emu
        from fractions import Fraction
        if abs(Fraction(tw*sh,th)-sw)>5 or abs(Fraction(th*sw,tw)-sh)>5:
            raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: target aspect exceeds five source pixels')
    backend_size=tuple(result.get('backend_canvas',[]))
    if len(backend_size)!=2: raise ValueError('LAYER_RESULT_INVALID: backend_canvas required')
    layers=result.get('layers')
    if not isinstance(layers,list) or len(layers)<2 or layers[0].get('type')!='background': raise ValueError('LAYER_RESULT_INVALID: background-first layers required')
    selected={x['id']:x for x in plan.get('targets',[])}; returned=[x.get('target_id') for x in layers[1:]]
    missing=[x for x in selected if x not in returned]
    if missing: raise ValueError('LAYER_TARGET_MISSING: '+','.join(missing))
    if len(returned)!=len(set(returned)) or any(x not in selected for x in returned): raise ValueError('LAYER_RESULT_INVALID: foreground target mapping invalid')
    raw=[]
    for spec in layers:
        p=safe_child(backend_result_path.parent,spec['file'])
        with Image.open(p) as img:
            rgba=img.convert('RGBA'); size=rgba.size
        if tuple(size)!=tuple(backend_size): raise ValueError('LAYER_RESULT_CANVAS_INCONSISTENT')
        raw.append((spec,p,rgba))
    source_boxes=[selected[x]['bbox'] for x in selected]
    if schema_version not in (2,3): raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: schema')
    evidence=None
    if schema_version==2:
        transform=layer_geometry.transform_from_provider_boxes(source_size,backend_size,source_boxes,
            result.get('resized_image_boxes',[]),result.get('boxes_mapping_index',[]),
            source_content_rect_in_backend=result.get('source_content_rect_in_backend'))
    else:
        layer_geometry_verify.validate_identity(source_size,backend_size,source_boxes,result,list(selected))
        resized=safe_child(backend_result_path.parent,result.get('resized_image',''))
        if not resized.is_file(): raise ValueError('LAYER_RESULT_INVALID: resized_image required')
        try:
            transform,evidence=layer_geometry_verify.create_transform(source_image,resized,result.get('source_content_rect_in_backend'))
        except ValueError as exc:
            if hasattr(exc,'geometry_evidence'):
                output_dir.mkdir(parents=True,exist_ok=True)
                diagnostic=output_dir/'geometry-diagnostic.json'
                diagnostic.write_text(json.dumps(exc.geometry_evidence,indent=2),encoding='utf-8')
            raise
    layer_geometry.validate_source_coverage(source_size,backend_size,transform)
    slide_w,slide_h=layer_geometry.resolve_target_slide_size_emu([source_size],explicit_target_emu)
    output_dir.mkdir(parents=True,exist_ok=True)
    if evidence is not None:
        proof=output_dir/'geometry'; proof.mkdir(exist_ok=True)
        shutil.copyfile(source_image,proof/'source.png'); shutil.copyfile(resized,proof/'resized.png')
        ep=proof/'evidence.json'; ep.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
        transform['mapping_evidence'].update(geometry_evidence_file='geometry/evidence.json',
            geometry_evidence_sha256=sha(ep),source_image_file='geometry/source.png',resized_image_file='geometry/resized.png')
    composite=Image.new('RGBA',backend_size,(255,255,255,255)); out_layers=[]
    for idx,(spec,path,image) in enumerate(raw):
        composite=Image.alpha_composite(composite,image)
        if idx==0:
            cx,cy,cw,ch=transform['source_content_rect_in_backend']
            bbox=(round(cx),round(cy),round(cx+cw),round(cy+ch)); filename='background.png'; canonical=[0,0,1,1]
        else:
            bbox=image.getchannel('A').getbbox()
            if bbox is None: raise ValueError('LAYER_ASSET_GEOMETRY_INVALID: fully transparent foreground')
            filename=f'foreground_{idx:02d}.png'
            canonical=layer_geometry.backend_bbox_to_canonical([bbox[0],bbox[1],bbox[2]-bbox[0],bbox[3]-bbox[1]],source_size,transform)
        crop=image.crop(bbox); out=output_dir/filename; crop.save(out)
        record={'file':filename,'sha256':sha(out),'type':spec['type'],'target_id':spec.get('target_id'),'z_index':idx,
                'asset_pixel_size':list(crop.size),'backend_bbox':[bbox[0],bbox[1],bbox[2]-bbox[0],bbox[3]-bbox[1]],
                'canonical_bbox_normalized':canonical}
        out_layers.append(record)
    composite.convert('RGB').save(output_dir/'composite.png')
    manifest={'schema_version':schema_version,'page_id':plan.get('page_id'),
      'source':{'text_clean_path':str(source_image),'text_clean_sha256':sha(source_image),'canvas':list(source_size)},
      'backend':{'provider_id':result.get('provider_id'),'model_id':result.get('model_id'),'request_id':result.get('request_id'),'canvas':list(backend_size)},
      'geometry':{k:transform[k] for k in ('transform_type','mapping_mode','sx','sy','tx','ty','source_content_rect_in_backend','mapping_evidence')},
      'ppt':{'slide_width_emu':slide_w,'slide_height_emu':slide_h,'target_canvas_source':'explicit_target' if explicit_target_emu is not None else 'source_aspect_fallback'},
      'counts':{'recommended_total_layers':plan.get('recommended_total_layers'),'selected_total_layers':1+len(selected),'actual_total_layers':len(out_layers)},
      'missing_targets':missing,'layers':out_layers}
    if schema_version==3:
        manifest['source']['layer_plan_sha256']=sha(plan_path)
        manifest['backend']['result_sha256']=sha(backend_result_path)
    (output_dir/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    if schema_version==3: shutil.copyfile(plan_path,output_dir/'layer-plan.json')
    else: (output_dir/'layer-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest


def _formal_target(state_path,slide_id,source_image,plan_path,result_path):
    import runtime as r
    import reconstruction_router as router
    import layer_bridge
    state=r.load_runtime_state(state_path)
    target=router.require_image_target(state_path,state)
    if slide_id not in state['stage2_run']['page_order']:
        raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: page not in current run')
    plan=layer_bridge._plan_current(state,slide_id)
    result=layer_bridge.result_current(state,slide_id)
    if plan is None or not plan.get('approved') or result is None:
        raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: current approved plan/result required')
    expected=((source_image,state['slides'][slide_id]['text_clean'],plan['text_clean_sha256']),
              (plan_path,plan['plan_path'],plan['plan_sha256']),
              (result_path,result['path'],result['sha256']))
    for supplied,registered,digest in expected:
        if Path(supplied).resolve()!=router.resolve(state,registered).resolve() or sha(supplied)!=digest:
            raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: supplied source/plan/result differs')
    payload=json.loads(Path(plan_path).read_text(encoding='utf-8'))
    backend=json.loads(Path(result_path).read_text(encoding='utf-8'))
    if payload.get('page_id')!=slide_id or backend.get('page_id') not in (None,slide_id):
        raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: page identity')
    if backend.get('request_id') and result.get('task_id') and backend['request_id']!=result['task_id']:
        raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: provider task identity')
    return target


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-image',required=True)
    parser.add_argument('--plan',required=True)
    parser.add_argument('--result',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--schema-version',type=int,choices=(2,3),default=3)
    parser.add_argument('--state')
    parser.add_argument('--slide-id')
    args=parser.parse_args(argv)
    if bool(args.state)!=bool(args.slide_id): parser.error('--state and --slide-id must be used together')
    try:
        target=_formal_target(args.state,args.slide_id,args.source_image,args.plan,args.result) if args.state else None
        manifest=package_layers(args.source_image,args.plan,args.result,args.output,schema_version=args.schema_version,explicit_target_emu=target)
        result={'status':'PASS','page_id':manifest.get('page_id'),'bundle_dir':str(Path(args.output).resolve())}
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        result={'status':'FAIL','details':[str(exc)]}
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 1 if result.get('status')=='FAIL' else 0

if __name__=='__main__': raise SystemExit(main())
