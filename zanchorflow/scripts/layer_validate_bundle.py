"""Validate a Layer Bundle v2/v3 before Graphics-first PPTX construction."""
import argparse
import hashlib,json
from pathlib import Path
from PIL import Image
import layer_geometry


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def validate_bundle(bundle_dir):
    bundle=Path(bundle_dir).resolve(); manifest_path=bundle/'manifest.json'
    if not manifest_path.is_file(): raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: manifest missing')
    m=json.loads(manifest_path.read_text(encoding='utf-8'))
    if m.get('schema_version') not in (2,3): raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: schema')
    if m.get('missing_targets'): raise ValueError('LAYER_TARGET_MISSING')
    layers=m.get('layers'); counts=m.get('counts',{})
    if not isinstance(layers,list) or not layers or counts.get('actual_total_layers')!=len(layers): raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: count')
    if layers[0].get('type')!='background' or layers[0].get('z_index')!=0: raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: background')
    source=m.get('source',{}).get('canvas'); backend=m.get('backend',{}).get('canvas'); geometry=m.get('geometry')
    if not isinstance(geometry,dict): raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: geometry')
    try: layer_geometry.validate_source_coverage(source,backend,geometry)
    except ValueError as exc: raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: geometry') from exc
    if m['schema_version']==3:
        from layer_geometry_verify import validate_evidence
        validate_evidence(bundle,m)
        plan_file=bundle/'layer-plan.json'
        if not plan_file.is_file() or sha(plan_file)!=m['source'].get('layer_plan_sha256'):
            raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: plan identity')
        plan=json.loads(plan_file.read_text(encoding='utf-8'))
        if plan.get('page_id')!=m.get('page_id') or {x.get('id') for x in plan.get('targets',[])}!={x.get('target_id') for x in layers[1:]}:
            raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: plan targets')
    bw,bh=backend; target_ids=set()
    for idx,spec in enumerate(layers):
        if spec.get('z_index')!=idx: raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: z-order')
        rel=Path(spec.get('file',''))
        if rel.is_absolute() or '..' in rel.parts: raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: asset path')
        p=bundle/rel
        if not p.is_file() or sha(p)!=spec.get('sha256'): raise ValueError('asset hash mismatch')
        try:
            with Image.open(p) as img: size=list(img.size)
        except Exception as exc: raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: invalid image') from exc
        if size!=spec.get('asset_pixel_size'): raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: asset size')
        backend_box=spec.get('backend_bbox')
        if (not isinstance(backend_box,list) or len(backend_box)!=4
                or any(not isinstance(v,(int,float)) for v in backend_box)):
            raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: backend bbox')
        bx,by,bww,bhh=backend_box
        if bx<0 or by<0 or bww<=0 or bhh<=0 or bx+bww>bw+1e-6 or by+bhh>bh+1e-6:
            raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: backend bbox')
        if size != [round(bww),round(bhh)]:
            raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: bbox/asset size')
        box=spec.get('canonical_bbox_normalized')
        if not isinstance(box,list) or len(box)!=4 or any(not isinstance(v,(int,float)) for v in box): raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: canonical bbox')
        x,y,w,h=box
        if x<0 or y<0 or w<=0 or h<=0 or x+w>1+1e-6 or y+h>1+1e-6: raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: canonical bbox outside page')
        if idx==0:
            if any(abs(a-b)>1e-9 for a,b in zip(box,[0,0,1,1])):
                raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: geometry mismatch')
        else:
            target_id=spec.get('target_id')
            if not isinstance(target_id,str) or not target_id or target_id in target_ids:
                raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: target id')
            target_ids.add(target_id)
            expected=layer_geometry.backend_bbox_to_canonical(backend_box,source,geometry)
            if any(abs(float(a)-float(b))>1e-6 for a,b in zip(box,expected)):
                raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: geometry mismatch')
    ppt=m.get('ppt',{})
    if any(not isinstance(ppt.get(k),int) or ppt[k]<=0 for k in ('slide_width_emu','slide_height_emu')): raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: target canvas')
    return {'status':'PASS','page_id':m.get('page_id'),'actual_total_layers':len(layers),'manifest':m}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--bundle',required=True); args=parser.parse_args(argv)
    try: result=validate_bundle(args.bundle)
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc: result={'status':'FAIL','details':[str(exc)]}
    print(json.dumps(result,ensure_ascii=False,indent=2,default=str)); return 1 if result.get('status')=='FAIL' else 0

if __name__=='__main__': raise SystemExit(main())
