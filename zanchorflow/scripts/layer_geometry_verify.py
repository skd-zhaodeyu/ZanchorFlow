"""Bounded verification of a declared geometry; never fits a new transform."""
import hashlib, json, math
from pathlib import Path
from PIL import Image
import layer_geometry as geometry

PARAMETERS = {'longest_edge':1024,'max_windows':8,'window_size':32,'search_radius':16,
              'minimum_ncc':0.8,'second_best_margin':0.05,'minimum_windows':4,
              'minimum_regions':3,'maximum_residual':1.0,'non_neighbor_radius':2}
METHOD = 'declared_geometry_edges_v1'

def dependencies():
    try:
        import numpy
        return numpy
    except ImportError as exc:
        raise ValueError('IMAGE_LAYER_GEOMETRY_DEPENDENCY_MISSING: numpy') from exc

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate_identity(source_size, backend_size, source_boxes, result, targets):
    resized=result.get('resized_image_boxes'); indices=result.get('boxes_mapping_index'); boxes=result.get('image_boxes')
    if not isinstance(resized,list) or not isinstance(indices,list) or not isinstance(boxes,list):
        raise ValueError('LAYER_RESULT_INVALID: mapping arrays required')
    if len(resized)!=len(indices) or len(boxes)!=len(indices) or len(indices)!=len(targets):
        raise ValueError('LAYER_TARGET_MISSING: mapping count')
    if any(type(i) is not int or i<0 or i>=len(targets) for i in indices) or len(set(indices))!=len(indices):
        raise ValueError('LAYER_RESULT_INVALID: mapping indices')
    for collection,size in [(boxes,source_size),(resized,backend_size)]:
        for box in collection:
            if (not isinstance(box,list) or len(box)!=4 or
                any(type(x) is not int for x in box) or
                not (0<=box[0]<box[2]<=size[0] and 0<=box[1]<box[3]<=size[1])):
                raise ValueError('LAYER_RESULT_INVALID: returned bbox boundary')
    for spec,index,box in zip(result['layers'][1:],indices,boxes):
        if spec.get('target_id')!=targets[index] or box!=source_boxes[index]:
            raise ValueError('LAYER_RESULT_INVALID: target identity')

def verify(source_path, resized_path, transform):
    np=dependencies()
    with Image.open(source_path) as image: source=image.convert('RGB')
    with Image.open(resized_path) as image: returned=image.convert('RGB')
    if list(source.size)!=transform['source_canvas'] or list(returned.size)!=transform['backend_canvas']:
        raise ValueError('LAYER_RESULT_CANVAS_INCONSISTENT: reference image')
    sx,sy,tx,ty=(transform[k] for k in ('sx','sy','tx','ty'))
    projected=source.transform(returned.size,Image.Transform.AFFINE,
        (1/sx,0,-tx/sx,0,1/sy,-ty/sy),resample=Image.Resampling.BILINEAR,fillcolor='white')
    scale=min(1,PARAMETERS['longest_edge']/max(returned.size))
    size=tuple(max(1,round(v*scale)) for v in returned.size)
    def edges(im):
        a=np.asarray(im.resize(size,Image.Resampling.LANCZOS).convert('L'),dtype=np.float32)
        dy,dx=np.gradient(a)
        return np.hypot(dx,dy)
    a,b=edges(projected),edges(returned); h,w=a.shape; n=PARAMETERS['window_size']; radius=PARAMETERS['search_radius']
    report={'mapping_method_version':METHOD,'verification_parameters':dict(PARAMETERS),
        'candidate':{k:transform[k] for k in ('sx','sy','tx','ty','source_content_rect_in_backend')},
        'source_image_sha256':sha(source_path),'resized_image_sha256':sha(resized_path),
        'validation_canvas':list(size),'verification_windows':[],'window_scores':[],'residuals':[],
        'result':'INSUFFICIENT'}
    # One strongest structural patch in each of 16 spatial cells, then select at most eight.
    candidates=[]
    cx,cy,cw,ch=transform['source_content_rect_in_backend']
    left=max(radius,math.ceil(cx*scale)+radius); top=max(radius,math.ceil(cy*scale)+radius)
    right=min(w-n-radius,math.floor((cx+cw)*scale)-n-radius)
    bottom=min(h-n-radius,math.floor((cy+ch)*scale)-n-radius)
    for row in range(4):
        for col in range(4):
            best=None
            for y in range(max(top,row*h//4),min(bottom,(row+1)*h//4),8):
                for x in range(max(left,col*w//4),min(right,(col+1)*w//4),8):
                    patch=a[y:y+n,x:x+n]; energy=float(patch.std())
                    if energy>0.5 and float((patch>2).mean())>0.01:
                        item=(energy,y,x,(int((y+n/2)>=h/2)*2+int((x+n/2)>=w/2)))
                        if best is None or item>best: best=item
            if best: candidates.append(best)
    # First cover regions, then fill by energy; ties are deterministic.
    candidates.sort(reverse=True); chosen=[]
    for region in range(4):
        item=next((v for v in candidates if v[3]==region),None)
        if item: chosen.append(item)
    chosen += [v for v in candidates if v not in chosen][:8-len(chosen)]
    valid=[]; contradictions=[]
    for energy,y,x,region in chosen:
        patch=a[y:y+n,x:x+n]; centered=patch-patch.mean(); norm=float(np.sqrt((centered*centered).sum()))
        search=b[y-radius:y+n+radius,x-radius:x+n+radius]
        views=np.lib.stride_tricks.sliding_window_view(search,(n,n))
        sums=views.sum(axis=(-2,-1)); squares=np.einsum('ijkl,ijkl->ij',views,views)
        norms=np.sqrt(np.maximum(0,squares-sums*sums/(n*n)))
        numerator=np.einsum('ijkl,kl->ij',views,centered)
        scores=np.divide(numerator,norms*norm,out=np.full(norms.shape,-1,dtype=np.float32),where=norms>1e-5)
        iy,ix=np.unravel_index(int(scores.argmax()),scores.shape); best=float(scores[iy,ix])
        other=scores.copy(); other[max(0,iy-2):iy+3,max(0,ix-2):ix+3]=-1
        second=float(other.max()); residual=float(math.hypot(ix-radius,iy-radius))
        confident=best>=0.8 and best-second>=0.05
        accepted=confident and residual<=1
        report['verification_windows'].append({'bbox':[x,y,x+n,y+n],'region':region,'accepted':accepted})
        report['window_scores'].append({'ncc':best,'second_best':second,'margin':best-second,'offset':[int(ix-radius),int(iy-radius)]})
        report['residuals'].append(residual)
        if accepted: valid.append(region)
        if confident and residual>1: contradictions.append(region)
    if len(contradictions)>=2: report['result']='CONTRADICTED'
    elif len(valid)>=4 and len(set(valid))>=3: report['result']='VERIFIED'
    return report

def create_transform(source, resized, content_rect=None):
    with Image.open(source) as im: ss=im.size
    with Image.open(resized) as im: bs=im.size
    t=(geometry.fit_with_padding_transform(ss,bs,content_rect) if content_rect is not None
       else geometry.full_canvas_transform(ss,bs))
    evidence=verify(source,resized,t)
    if evidence['result']!='VERIFIED':
        error=ValueError('LAYER_CANVAS_MAPPING_UNRESOLVED: '+evidence['result']+'; diagnose local geometry, never resubmit')
        error.geometry_evidence=evidence
        raise error
    t['mapping_evidence']={'method':METHOD}
    return t,evidence

def validate_evidence(bundle, manifest):
    g=manifest['geometry']; info=g.get('mapping_evidence',{})
    def asset(value,digest):
        rel=Path(value)
        root=Path(bundle).resolve(); path=(root/rel).resolve()
        if rel.is_absolute() or '..' in rel.parts or not path.is_relative_to(root) or not path.is_file() or sha(path)!=digest:
            raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: geometry evidence asset')
        return path
    p=asset(info.get('geometry_evidence_file',''),info.get('geometry_evidence_sha256'))
    e=json.loads(p.read_text(encoding='utf-8'))
    if e.get('mapping_method_version')!=METHOD or e.get('verification_parameters')!=PARAMETERS or e.get('result')!='VERIFIED':
        raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: geometry verification')
    source=asset(info.get('source_image_file',''),e.get('source_image_sha256'))
    resized=asset(info.get('resized_image_file',''),e.get('resized_image_sha256'))
    if e.get('source_image_sha256')!=manifest['source']['text_clean_sha256']:
        raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: geometry source identity')
    with Image.open(source) as im: ss=im.size
    with Image.open(resized) as im: bs=im.size
    if list(ss)!=manifest['source']['canvas'] or list(bs)!=manifest['backend']['canvas']:
        raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: geometry evidence canvas')
    candidate=e.get('candidate',{})
    for k in ('sx','sy','tx','ty','source_content_rect_in_backend'):
        if candidate.get(k)!=g.get(k): raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: candidate changed')
    if g.get('mapping_mode')=='full_canvas_scale': expected=geometry.full_canvas_transform(ss,bs)
    elif g.get('mapping_mode')=='fit_with_padding': expected=geometry.fit_with_padding_transform(ss,bs,g['source_content_rect_in_backend'])
    else: raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: mapping mode')
    if any(g.get(k)!=expected.get(k) for k in ('sx','sy','tx','ty')):
        raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: undeclared geometry')
    windows=e.get('verification_windows',[]); scores=e.get('window_scores',[]); residuals=e.get('residuals',[])
    if not (len(windows)==len(scores)==len(residuals)<=8): raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: windows')
    expected_canvas=[max(1,round(v*min(1,PARAMETERS['longest_edge']/max(bs)))) for v in bs]
    if e.get('validation_canvas')!=expected_canvas: raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: validation canvas')
    regions=[]; seen=set()
    for window,score,residual in zip(windows,scores,residuals):
        if window.get('accepted'):
            box=window.get('bbox'); offset=score.get('offset'); region=window.get('region')
            if (not isinstance(box,list) or len(box)!=4 or any(type(v) is not int for v in box)
                or box[2]-box[0]!=32 or box[3]-box[1]!=32 or box[0]<16 or box[1]<16
                or box[2]>expected_canvas[0]-16 or box[3]>expected_canvas[1]-16 or tuple(box) in seen
                or type(region) is not int or region not in range(4)
                or not isinstance(offset,list) or len(offset)!=2 or any(type(v) is not int or abs(v)>16 for v in offset)):
                raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: verification window')
            seen.add(tuple(box))
            actual_region=int((box[1]+16)>=expected_canvas[1]/2)*2+int((box[0]+16)>=expected_canvas[0]/2)
            if region!=actual_region: raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: spatial region')
            values=[score.get('ncc'),score.get('second_best'),score.get('margin'),residual]
            if any(type(v) not in (int,float) or not math.isfinite(v) for v in values): raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: scores')
            if abs(score['margin']-(score['ncc']-score['second_best']))>1e-6 or abs(residual-math.hypot(*offset))>1e-6:
                raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: inconsistent scores/residuals')
            if score['ncc']<0.8 or score['margin']<0.05 or residual>1 or residual<0:
                raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: invalid accepted window')
            regions.append(window['region'])
    if len(regions)<4 or len(set(regions))<3: raise ValueError('LAYER_BUNDLE_VALIDATION_FAILED: insufficient windows')
    return e
