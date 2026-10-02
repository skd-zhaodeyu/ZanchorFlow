"""360 Reveal-Layer provider adapter. Secrets are passed in memory only."""
import base64
import json
import mimetypes
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from PIL import Image

DEFAULT_BASE_URL='https://api.research.360.cn/v1'
PROVIDER_ID='360_reveal_layer'
MODEL_PARAMETERS={'pipeline_type':'crop','seed':42,'steps':10,'time_out':3600}
MODEL='reveal_layer'
VERSION='v2.3.4'


def _unwrap(data):
    if isinstance(data,dict) and isinstance(data.get('data'),dict): return data['data']
    if not isinstance(data,dict): raise ValueError('LAYER_RESULT_INVALID: provider response must be an object')
    return data


def _post_json(url,headers,body):
    req=Request(url,data=json.dumps(body,ensure_ascii=False).encode('utf-8'),headers=headers,method='POST')
    with urlopen(req,timeout=120) as resp:
        return json.loads(resp.read().decode('utf-8'))


def image_data_url(path):
    path=Path(path); mime=mimetypes.guess_type(path.name)[0] or 'image/png'
    return f"data:{mime};base64,"+base64.b64encode(path.read_bytes()).decode('ascii')


def _headers(api_key):
    if not isinstance(api_key,str) or not api_key.strip(): raise ValueError('IMAGE_LAYER_API_KEY_REQUIRED')
    return {'accept':'application/json','Content-Type':'application/json','Authorization':f'Bearer {api_key}'}


def submit_task(image_path,boxes,api_key,base_url=DEFAULT_BASE_URL,http_post=None):
    body={'model':MODEL,'version':VERSION,'time_out':MODEL_PARAMETERS['time_out'],
          'input':[{'type':'input_image','image_url':image_data_url(image_path)}],
          'pipeline_type':MODEL_PARAMETERS['pipeline_type'],'image_boxes':boxes,'seed':MODEL_PARAMETERS['seed'],'steps':MODEL_PARAMETERS['steps']}
    raw=(http_post or _post_json)(base_url.rstrip('/')+'/submit_task',_headers(api_key),body)
    data=_unwrap(raw)
    if data.get('response_status') != 0 or not isinstance(data.get('task_id'),str) or not data['task_id']:
        raise ValueError('LAYER_REQUEST_FAILED: '+str(data.get('message','provider rejected submit')))
    return {k:data.get(k) for k in ('task_id','model','version','message','response_status')}


def query_task(task_id,api_key,base_url=DEFAULT_BASE_URL,http_post=None):
    if not isinstance(task_id,str) or not task_id: raise ValueError('task_id required')
    body={'model':MODEL,'version':VERSION,'task_id':task_id}
    raw=(http_post or _post_json)(base_url.rstrip('/')+'/query_task',_headers(api_key),body)
    data=_unwrap(raw)
    if data.get('response_status') not in (0,None):
        raise ValueError('LAYER_REQUEST_FAILED: '+str(data.get('message','query failed')))
    status=data.get('status')
    mapping={'in_queue':'RUNNING','generating':'RUNNING','done':'DONE','failed':'FAILED','not_found':'NOT_FOUND'}
    if status not in mapping: raise ValueError('LAYER_RESULT_INVALID: unknown provider status')
    result=dict(data); result['normalized_status']=mapping[status]; return result


def _safe_result_url(url):
    if not isinstance(url,str): return False
    p=urlsplit(url)
    return p.scheme in ('http','https') and bool(p.hostname) and p.username is None and p.password is None


def _fetch(url):
    if not _safe_result_url(url): raise ValueError('unsafe provider result URL')
    with urlopen(url,timeout=120) as resp: return resp.read()


def _image_size(path):
    with Image.open(path) as img: return img.size


def normalize_done_result(response,plan,output_dir,fetch_bytes=None):
    data=_unwrap(response); output=data.get('output')
    if data.get('status')!='done' or not isinstance(output,dict):
        raise ValueError('LAYER_RESULT_INVALID: terminal done output required')
    required=('layers_base_count','layers_base','layers_aug','image_boxes','resized_image_boxes','boxes_mapping_index','resized_image')
    if any(k not in output for k in required): raise ValueError('LAYER_RESULT_INVALID: provider output fields missing')
    count=output['layers_base_count']; base=output['layers_base']; aug=output['layers_aug']; boxes=output['image_boxes']; resized=output['resized_image_boxes']; mapping=output['boxes_mapping_index']
    if (not isinstance(count,int) or count<2 or not isinstance(base,list) or not isinstance(aug,list)
            or len(base)!=count or len(aug)!=count or len(boxes)!=count-1
            or len(resized)!=len(boxes) or len(mapping)!=len(boxes)):
        raise ValueError('LAYER_RESULT_INVALID: layer/box count invariants failed')
    targets=plan.get('targets') if isinstance(plan,dict) else None
    if not isinstance(targets,list): raise ValueError('LAYER_RESULT_INVALID: plan targets required')
    if any(not isinstance(i,int) or i<0 or i>=len(targets) for i in mapping):
        raise ValueError('LAYER_RESULT_INVALID: boxes_mapping_index invalid')
    urls=[output['resized_image']]+aug
    if any(not _safe_result_url(u) for u in urls): raise ValueError('unsafe provider result URL')
    output_dir=Path(output_dir); rawdir=output_dir/'raw'; rawdir.mkdir(parents=True,exist_ok=True)
    fetch_bytes=fetch_bytes or _fetch
    resized_path=rawdir/'resized_image.png'; resized_path.write_bytes(fetch_bytes(output['resized_image']))
    backend_size=_image_size(resized_path)
    layers=[]
    for i,url in enumerate(aug):
        path=rawdir/f'layer_{i:02d}.png'; path.write_bytes(fetch_bytes(url))
        if _image_size(path)!=backend_size: raise ValueError('LAYER_RESULT_CANVAS_INCONSISTENT')
        item={'type':'background' if i==0 else 'foreground','file':str(path.relative_to(output_dir))}
        if i>0: item['target_id']=targets[mapping[i-1]]['id']
        layers.append(item)
    normalized={'schema_version':1,'page_id':plan.get('page_id'),'provider_id':'360_reveal_layer','model_id':MODEL,
                'version':data.get('version',VERSION),'request_id':data.get('task_id'),'usage':data.get('usage',{}),
                'backend_canvas':list(backend_size),'resized_image':str(resized_path.relative_to(output_dir)),
                'image_boxes':boxes,'resized_image_boxes':resized,'boxes_mapping_index':mapping,'layers':layers}
    path=output_dir/'backend-result.json'; path.write_text(json.dumps(normalized,ensure_ascii=False,indent=2),encoding='utf-8'); return path

