import io, json, sys
from pathlib import Path
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import layer_provider_360 as p


def png(size=(800,450), color=(255,0,0,255)):
    buf=io.BytesIO(); Image.new('RGBA',size,color).save(buf,format='PNG'); return buf.getvalue()


def plan():
    return {'page_id':'S001','targets':[{'id':'a','bbox':[0,0,400,300]},{'id':'b','bbox':[500,100,900,400]}]}


def test_submit_uses_reveal_contract_and_never_returns_secret(tmp_path):
    image=tmp_path/'clean.png'; image.write_bytes(png((1600,900)))
    seen={}
    def post(url,headers,body):
        seen.update(url=url,headers=headers,body=body)
        return {'data':{'response_status':0,'task_id':'task-1','message':'success','model':'reveal_layer','version':'v2.3.4'}}
    result=p.submit_task(image,[[0,0,400,300]],'secret-value',http_post=post)
    assert seen['url'].endswith('/submit_task')
    assert seen['headers']['Authorization']=='Bearer secret-value'
    assert seen['body']['model']=='reveal_layer' and seen['body']['version']=='v2.3.4'
    assert seen['body']['pipeline_type']=='crop' and seen['body']['steps']==10
    assert seen['body']['input'][0]['image_url'].startswith('data:image/png;base64,')
    assert result['task_id']=='task-1'
    assert 'secret-value' not in json.dumps(result)


def test_query_request_includes_model_version_and_task_id():
    import layer_provider_360 as p
    seen={}
    def fake(url,headers,body):
        seen.update(body); return {'response_status':0,'status':'in_queue','task_id':'task-1'}
    p.query_task('task-1','key',http_post=fake)
    assert seen=={'model':'reveal_layer','version':'v2.3.4','task_id':'task-1'}


def test_query_maps_statuses():
    for raw,expected in [('in_queue','RUNNING'),('generating','RUNNING'),('done','DONE'),('failed','FAILED'),('not_found','NOT_FOUND')]:
        def post(url,headers,body,raw=raw):
            return {'data':{'response_status':0,'task_id':'t','status':raw,'message':'x'}}
        assert p.query_task('t','k',http_post=post)['normalized_status']==expected


def test_done_result_requires_layers_aug_and_count_invariants(tmp_path):
    response={'status':'done','task_id':'t','output':{'layers_base_count':3,'layers_base':['b','a','c'],
              'image_boxes':[[0,0,400,300],[500,100,900,400]],'resized_image_boxes':[[0,0,200,150],[250,50,450,200]],
              'boxes_mapping_index':[0,1],'resized_image':'https://x.example/resized.png'}}
    with pytest.raises(ValueError,match='LAYER_RESULT_INVALID'):
        p.normalize_done_result(response,plan(),tmp_path,fetch_bytes=lambda _:png())


def test_done_result_maps_filtered_targets_and_writes_full_canvas_layers(tmp_path):
    response={'model':'reveal_layer','version':'v2.3.4','status':'done','task_id':'t','usage':{'total_tokens':123},
      'output':{'layers_base_count':2,'layers_base':['base0','base1'],'layers_aug':['https://x.example/bg.png','https://x.example/fg.png'],
                'image_boxes':[[500,100,900,400]],'resized_image_boxes':[[250,50,450,200]],
                'boxes_mapping_index':[1],'resized_image':'https://x.example/resized.png'}}
    def fetch(url): return png((800,450))
    path=p.normalize_done_result(response,plan(),tmp_path,fetch_bytes=fetch)
    data=json.loads(path.read_text(encoding='utf-8'))
    assert data['backend_canvas']==[800,450]
    assert data['boxes_mapping_index']==[1]
    assert data['layers'][0]['type']=='background'
    assert data['layers'][1]['target_id']=='b'
    assert len(data['layers'])==2
    assert data['usage']=={'total_tokens':123}


def test_result_urls_must_be_http_https(tmp_path):
    response={'status':'done','task_id':'t','output':{'layers_base_count':2,'layers_base':['x','y'],
      'layers_aug':['file:///tmp/a.png','https://x.example/b.png'],'image_boxes':[[0,0,400,300]],
      'resized_image_boxes':[[0,0,200,150]],'boxes_mapping_index':[0],'resized_image':'https://x.example/r.png'}}
    with pytest.raises(ValueError,match='unsafe provider result URL'):
        p.normalize_done_result(response,{'page_id':'S001','targets':[{'id':'a','bbox':[0,0,400,300]}]},tmp_path,fetch_bytes=lambda _:png())
