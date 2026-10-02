"""Pure geometry helpers for the Image Layer backend."""
import math

EMU_PER_INCH = 914400


def _size(value,name):
    if (not isinstance(value,(tuple,list)) or len(value)!=2
            or any(not isinstance(v,int) or v<=0 for v in value)):
        raise ValueError(f'{name} must be two positive integers')
    return int(value[0]),int(value[1])


def resolve_target_slide_size_emu(source_sizes, explicit_target_emu=None):
    if explicit_target_emu is not None:
        w,h=_size(explicit_target_emu,'explicit target slide size')
        return w,h
    if not isinstance(source_sizes,list) or not source_sizes:
        raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: no source sizes')
    sizes=[_size(s,'source size') for s in source_sizes]
    ratio=sizes[0][0]/sizes[0][1]
    if any(abs((w/h)-ratio)>1e-9 for w,h in sizes[1:]):
        raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: inconsistent source aspect ratios')
    short=7.5*EMU_PER_INCH
    if ratio>=1:
        return round(short*ratio),round(short)
    return round(short),round(short/ratio)


def _transform(source_size,backend_size,sx,sy,tx,ty,mode,evidence):
    ws,hs=_size(source_size,'source size'); wb,hb=_size(backend_size,'backend size')
    if sx<=0 or sy<=0: raise ValueError('LAYER_CANVAS_MAPPING_UNRESOLVED: nonpositive scale')
    return {'transform_type':'axis_aligned_scale_translate','mapping_mode':mode,
            'sx':float(sx),'sy':float(sy),'tx':float(tx),'ty':float(ty),
            'source_content_rect_in_backend':[float(tx),float(ty),float(ws*sx),float(hs*sy)],
            'mapping_evidence':evidence,'source_canvas':[ws,hs],'backend_canvas':[wb,hb]}


def full_canvas_transform(source_size,backend_size):
    ws,hs=_size(source_size,'source size'); wb,hb=_size(backend_size,'backend size')
    return _transform((ws,hs),(wb,hb),wb/ws,hb/hs,0,0,'full_canvas_scale',
                      {'method':'source_and_backend_canvas'})


def fit_with_padding_transform(source_size,backend_size,content_rect):
    ws,hs=_size(source_size,'source size'); wb,hb=_size(backend_size,'backend size')
    if (not isinstance(content_rect,(list,tuple)) or len(content_rect)!=4
            or any(not isinstance(v,(int,float)) for v in content_rect)):
        raise ValueError('LAYER_CANVAS_MAPPING_UNRESOLVED: content rect required')
    x,y,w,h=[float(v) for v in content_rect]
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x+w > wb+1e-6 or y+h > hb+1e-6:
        raise ValueError('LAYER_SOURCE_COVERAGE_FAILED: content rect outside backend canvas')
    return _transform((ws,hs),(wb,hb),w/ws,h/hs,x,y,'fit_with_padding',
                      {'method':'declared_source_content_rect','source_content_rect_in_backend':[x,y,w,h]})


def _edge_ok(actual,expected):
    return int(actual) in {math.floor(expected),round(expected),math.ceil(expected)}


def transform_from_provider_boxes(source_size,backend_size,source_boxes,resized_boxes,mapping_indices,source_content_rect_in_backend=None):
    ws,hs=_size(source_size,'source size'); wb,hb=_size(backend_size,'backend size')
    if not isinstance(source_boxes,list) or not isinstance(resized_boxes,list) or not isinstance(mapping_indices,list):
        raise ValueError('LAYER_CANVAS_MAPPING_UNRESOLVED: mapping arrays required')
    if len(resized_boxes)!=len(mapping_indices) or not resized_boxes:
        raise ValueError('LAYER_CANVAS_MAPPING_UNRESOLVED: mapping lengths differ')
    t=(fit_with_padding_transform((ws,hs),(wb,hb),source_content_rect_in_backend)
       if source_content_rect_in_backend is not None else full_canvas_transform((ws,hs),(wb,hb)))
    sx,sy,tx,ty=t['sx'],t['sy'],t['tx'],t['ty']
    for resized,index in zip(resized_boxes,mapping_indices):
        if not isinstance(index,int) or index<0 or index>=len(source_boxes):
            raise ValueError('LAYER_CANVAS_MAPPING_UNRESOLVED: mapping index invalid')
        source=source_boxes[index]
        if len(source)!=4 or len(resized)!=4:
            raise ValueError('LAYER_CANVAS_MAPPING_UNRESOLVED: bbox invalid')
        expected=[source[0]*sx+tx,source[1]*sy+ty,source[2]*sx+tx,source[3]*sy+ty]
        if not all(_edge_ok(a,e) for a,e in zip(resized,expected)):
            raise ValueError('LAYER_CANVAS_MAPPING_UNRESOLVED: provider boxes contradict canvas transform')
    t['mapping_evidence']={'method':'provider_resized_boxes','mapping_indices':list(mapping_indices),
                           'source_boxes':[list(source_boxes[i]) for i in mapping_indices],
                           'resized_boxes':[list(x) for x in resized_boxes]}
    return t


def validate_source_coverage(source_size,backend_size,transform):
    ws,hs=_size(source_size,'source size'); wb,hb=_size(backend_size,'backend size')
    if transform.get('transform_type')!='axis_aligned_scale_translate':
        raise ValueError('LAYER_UNSUPPORTED_TRANSFORM')
    sx,sy,tx,ty=(transform.get(k) for k in ('sx','sy','tx','ty'))
    if any(not isinstance(v,(int,float)) for v in (sx,sy,tx,ty)) or sx<=0 or sy<=0:
        raise ValueError('LAYER_CANVAS_MAPPING_UNRESOLVED')
    left,top,right,bottom=tx,ty,tx+ws*sx,ty+hs*sy
    if left < -1 or top < -1 or right > wb+1 or bottom > hb+1:
        raise ValueError('LAYER_SOURCE_COVERAGE_FAILED')
    return True


def backend_bbox_to_canonical(bbox,source_size,transform):
    ws,hs=_size(source_size,'source size')
    if not isinstance(bbox,(list,tuple)) or len(bbox)!=4:
        raise ValueError('LAYER_ASSET_GEOMETRY_INVALID')
    x,y,w,h=bbox
    if any(not isinstance(v,(int,float)) for v in bbox) or w<=0 or h<=0:
        raise ValueError('LAYER_ASSET_GEOMETRY_INVALID')
    sx,sy,tx,ty=(transform.get(k) for k in ('sx','sy','tx','ty'))
    if not sx or not sy: raise ValueError('LAYER_CANVAS_MAPPING_UNRESOLVED')
    xs=(x-tx)/sx; ys=(y-ty)/sy; sw=w/sx; sh=h/sy
    result=[xs/ws,ys/hs,sw/ws,sh/hs]
    if result[0] < -1e-6 or result[1] < -1e-6 or result[0]+result[2] > 1+1e-6 or result[1]+result[3] > 1+1e-6:
        raise ValueError('LAYER_ASSET_GEOMETRY_INVALID: canonical bbox outside page')
    return [0.0 if abs(v)<1e-12 else float(v) for v in result]
