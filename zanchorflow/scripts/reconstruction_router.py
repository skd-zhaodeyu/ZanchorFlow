"""Backend-neutral Stage 3 reconstruction routing and shared state transaction."""
import argparse
import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
import tempfile

import runtime as r

MAGIC_LAYER = 'magic_layer'
IMAGE_LAYER = 'image_layer'
VALID_BACKENDS = {MAGIC_LAYER, IMAGE_LAYER}
IMAGE_LAYER_API_KEY_ENV = 'ZANCHORFLOW_360_API_KEY'
IMAGE_LAYER_API_KEY_URL = 'https://research.360.cn/workspace/apikeys'
IMAGE_LAYER_FREE_COPY = '请核实当前账户的免费权益、余额与价格，并在真实提交前确认费用授权。'


def selection_prompt():
    return ('请选择 PPTX 重建方式：\n\n'
            'A. Magic Layer 分支（推荐）\n   使用现有 Magic Layers 路线完成图形结构重建。\n\n'
            'B. Image Layer 分支\n   对消字后的页面进行对象选框，并通过图像分层模型 API 拆成独立图层后重建为可编辑 PPTX。\n\n'
            '推荐使用 Magic Layer 分支。')


def image_layer_onboarding():
    return {'status':'IMAGE_LAYER_API_KEY_REQUIRED', 'api_key_url':IMAGE_LAYER_API_KEY_URL,
            'message':IMAGE_LAYER_FREE_COPY, 'api_key_env':IMAGE_LAYER_API_KEY_ENV}


def _run(state):
    run=state.get('stage2_run')
    if not isinstance(run,dict) or not run.get('run_id') or not isinstance(run.get('page_order'),list):
        raise ValueError('STAGE2_RUN_REQUIRED')
    return run


def _selection_payload(state):
    run=_run(state)
    return {'run_id':run['run_id'], 'approved_outline_fingerprint':run.get('approved_outline_fingerprint'),
            'page_order':list(run['page_order'])}


def _fingerprint(payload):
    raw=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(raw).hexdigest()


def selection_fingerprint(state_path):
    return _fingerprint(_selection_payload(r.load_runtime_state(state_path)))


def _selection_current(state, record):
    if not isinstance(record,dict) or record.get('backend') not in VALID_BACKENDS:
        return False
    payload=_selection_payload(state)
    return (record.get('run_id')==payload['run_id']
            and record.get('approved_outline_fingerprint')==payload['approved_outline_fingerprint']
            and record.get('page_order')==payload['page_order']
            and record.get('selection_fingerprint')==_fingerprint(payload))


def selected_backend(state_path):
    state=r.load_runtime_state(state_path)
    record=state.get('reconstruction_backend')
    return record.get('backend') if _selection_current(state,record) else None


def _first_missing_text_clean(state_path, state=None):
    state=state or r.load_runtime_state(state_path)
    for sid in _run(state)['page_order']:
        if not r.stage2_artifact_current(state_path,f'text_clean:{sid}'):
            return sid
    return None


def _has_backend_work(state):
    cb=state.get('canva_bridge',{})
    if isinstance(cb,dict) and any(cb.get(k) for k in ('active','downloads','validated')):
        return True
    lb=state.get('layer_bridge',{})
    return isinstance(lb,dict) and any(lb.get(k) for k in ('plans','requests','results','bundles','graphics_first','validated'))


@contextmanager
def transaction(state_path):
    """Use the same <state>.bridge-lock contract as canva_bridge without importing it."""
    path=Path(state_path).resolve(); lock=path.with_name(path.name+'.bridge-lock')
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY); os.close(fd)
    temporary=None
    try:
        before=path.read_bytes()
        with tempfile.NamedTemporaryFile(dir=path.parent,suffix='.json',prefix='.router-state-',delete=False) as stream:
            temporary=Path(stream.name); stream.write(before)
        yield temporary
        r.load_runtime_state(temporary)
        if path.read_bytes()!=before:
            raise ValueError('runtime state changed during operation; stop and inspect')
        os.replace(temporary,path)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def validate_image_target_emu(value):
    """Validate a physical target without treating a boolean as an EMU."""
    from pptx.oxml.simpletypes import ST_SlideSizeCoordinate
    if (not isinstance(value,(list,tuple)) or len(value)!=2
        or any(type(v) is not int for v in value)):
        raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: target requires two integer EMUs')
    for v in value:
        ST_SlideSizeCoordinate.validate(v)
    return list(value)


def _image_target_slide_emu(state_path, state):
    from PIL import Image
    import layer_geometry
    sizes=[]; canvases=[]
    run=_run(state)
    for sid in run['page_order']:
        slide=state.get('slides',{}).get(sid,{})
        value=slide.get('text_clean')
        record=run.get('artifacts',{}).get('text_clean:'+sid,{})
        if (not value or not record.get('path')
            or resolve(state,value).resolve()!=resolve(state,record['path']).resolve()
            or not r.stage2_artifact_current(state_path,'text_clean:'+sid)):
            raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: current text-clean required')
        with Image.open(resolve(state,value)) as image:
            sizes.append(tuple(image.size))
        canvas_value=slide.get('canvas')
        canvas_record=run.get('artifacts',{}).get('canvas:'+sid)
        if canvas_value is None and canvas_record is None:
            canvases.append(None); continue
        if (not canvas_value or not isinstance(canvas_record,dict) or not canvas_record.get('path')
            or resolve(state,canvas_value).resolve()!=resolve(state,canvas_record['path']).resolve()
            or not r.stage2_artifact_current(state_path,'canvas:'+sid)):
            raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: current registered canvas required')
        canvas=json.loads(resolve(state,canvas_value).read_text(encoding='utf-8'))
        if not isinstance(canvas,dict):
            raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: canvas object required')
        canvases.append(canvas)
    keys=('target_slide_width_emu','target_slide_height_emu')
    explicit=any(c is not None and any(k in c for k in keys) for c in canvases)
    if not explicit:
        return validate_image_target_emu(layer_geometry.resolve_target_slide_size_emu(sizes))
    targets=[]
    from fractions import Fraction
    for size,canvas in zip(sizes,canvases):
        if canvas is None or any(k not in canvas for k in keys):
            raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: explicit target missing on a page')
        target=validate_image_target_emu([canvas[k] for k in keys])
        sw,sh=size; tw,th=target
        if any(type(canvas.get(k)) is not int for k in ('source_width','source_height')):
            raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: registered source dimensions required')
        if [canvas['source_width'],canvas['source_height']]!=list(size):
            raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: registered source dimensions differ')
        if abs(Fraction(tw*sh,th)-sw)>5 or abs(Fraction(th*sw,tw)-sh)>5:
            raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: target aspect exceeds five source pixels')
        targets.append(target)
    if any(t!=targets[0] for t in targets[1:]):
        raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: approved page targets conflict')
    return targets[0]


def require_image_target(state_path, state=None):
    """Read-only current-target guard; never changes selection or retry state."""
    state=state or r.load_runtime_state(state_path)
    selection=state.get('reconstruction_backend')
    if not _selection_current(state,selection) or selection['backend']!=IMAGE_LAYER:
        raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: current Image Layer selection required')
    target=_image_target_slide_emu(state_path,state)
    if validate_image_target_emu(selection.get('target_slide_emu'))!=target:
        raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: selected target differs from approved canvas')
    return target


def choose_backend(state_path, backend):
    if backend not in VALID_BACKENDS:
        raise ValueError('invalid reconstruction backend')
    state=r.load_runtime_state(state_path)
    missing=_first_missing_text_clean(state_path,state)
    if missing:
        raise ValueError('RECONSTRUCTION_BACKEND_SELECTION_NOT_READY: '+missing)
    current=state.get('reconstruction_backend')
    if _selection_current(state,current):
        if current['backend']==backend:
            if backend==IMAGE_LAYER: require_image_target(state_path,state)
            return current
        if _has_backend_work(state):
            raise ValueError('BACKEND_SWITCH_REQUIRES_EXPLICIT_RESET')
    payload=_selection_payload(state)
    record={'schema_version':1,'backend':backend,**payload,'selection_fingerprint':_fingerprint(payload)}
    if backend==IMAGE_LAYER:
        record['target_slide_emu']=_image_target_slide_emu(state_path,state)
    with transaction(state_path) as temp:
        current_state=r.load_runtime_state(temp)
        old=current_state.get('reconstruction_backend')
        if isinstance(old,dict): current_state.setdefault('reconstruction_backend_history',[]).append(old)
        if backend==IMAGE_LAYER and _image_target_slide_emu(temp,current_state)!=record['target_slide_emu']:
            raise ValueError('TARGET_DECK_CANVAS_UNRESOLVED: canvas changed before selection')
        current_state['reconstruction_backend']=record
        r._save_runtime_state(temp,current_state)
    return record



def resolve(state, value):
    p=Path(value)
    return p if p.is_absolute() else Path(state['_base_dir'])/p


def _backend_from_state(state):
    record=state.get('reconstruction_backend')
    if _selection_current(state,record):
        return record['backend']
    # Backward-compatible external/synthetic route: before RC18, pages could be
    # sealed without a reconstruction backend binding. Never infer Image Layer.
    return MAGIC_LAYER


def page_provenance(state, slide_id):
    backend=_backend_from_state(state)
    if backend==IMAGE_LAYER:
        import layer_bridge
        return layer_bridge.page_provenance(state,slide_id)
    import canva_bridge
    return canva_bridge.page_provenance(state,slide_id)


def deck_provenance(state, order):
    return [page_provenance(state,sid) for sid in order]


def merged_provenance(state):
    backend=_backend_from_state(state)
    root='layer_bridge' if backend==IMAGE_LAYER else 'canva_bridge'
    value=state.get(root,{}).get('merged')
    return value if isinstance(value,dict) else {}


def set_merged_provenance(state, pages, merged_sha256):
    backend=_backend_from_state(state)
    root='layer_bridge' if backend==IMAGE_LAYER else 'canva_bridge'
    state.setdefault(root,{})['merged']={'pages':pages,'merged_pptx_sha256':merged_sha256}
    return state[root]['merged']

def status(state_path):
    state=r.load_runtime_state(state_path)
    missing=_first_missing_text_clean(state_path,state)
    if missing: return {'status':'PREPARE_TEXT','slide_id':missing}
    backend=selected_backend(state_path)
    if backend is None:
        return {'status':'AWAITING_RECONSTRUCTION_BACKEND_SELECTION','prompt':selection_prompt()}
    if backend==IMAGE_LAYER:
        try:
            import layer_bridge
            layer_status=layer_bridge.status(state_path)
        except ImportError:
            layer_status={'status':'LAYER_PLAN_REQUIRED','slide_id':_run(state)['page_order'][0]}
        if layer_status.get('status')=='LAYER_REQUEST_READY' and not os.environ.get(IMAGE_LAYER_API_KEY_ENV):
            return image_layer_onboarding()
        return layer_status
    import canva_bridge
    return canva_bridge.status(state_path)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('status'); p.add_argument('--state',required=True)
    p=sub.add_parser('choose-backend'); p.add_argument('--state',required=True); p.add_argument('--backend',choices=sorted(VALID_BACKENDS),required=True)
    args=parser.parse_args(argv)
    try:
        result=status(args.state) if args.action=='status' else choose_backend(args.state,args.backend)
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        result={'status':'FAIL','details':[str(exc)]}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 1 if result.get('status')=='FAIL' else 0

if __name__=='__main__': raise SystemExit(main())
