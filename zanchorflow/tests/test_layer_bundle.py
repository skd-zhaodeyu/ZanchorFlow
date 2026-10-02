import json,sys
from pathlib import Path
import pytest
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import layer_package as lp
import layer_validate_bundle as lv


def fixture(tmp_path,two_targets=False,mismatch=False):
    tmp_path.mkdir(parents=True,exist_ok=True)
    source=tmp_path/'source.png'; Image.new('RGBA',(1600,900),'white').save(source)
    targets=[{'id':'a','bbox':[200,100,600,500]}]
    if two_targets: targets.append({'id':'b','bbox':[800,200,1200,600]})
    plan={'schema_version':1,'page_id':'S001','max_foregrounds':6,'recommended_total_layers':1+len(targets),'targets':targets,'deferred':[]}
    pp=tmp_path/'plan.json'; pp.write_text(json.dumps(plan),encoding='utf-8')
    raw=tmp_path/'raw'; raw.mkdir()
    bg=Image.new('RGBA',(800,450),(255,255,255,255)); bg.save(raw/'bg.png')
    fg=Image.new('RGBA',(801 if mismatch else 800,450),(0,0,0,0)); d=ImageDraw.Draw(fg); d.rectangle((100,50,299,249),fill=(255,0,0,255)); fg.save(raw/'fg.png')
    result={'schema_version':1,'page_id':'S001','provider_id':'360_reveal_layer','model_id':'reveal_layer','request_id':'t',
      'backend_canvas':[800,450],'image_boxes':[[200,100,600,500]],'resized_image_boxes':[[100,50,300,250]],'boxes_mapping_index':[0],
      'layers':[{'type':'background','file':'raw/bg.png'},{'type':'foreground','target_id':'a','file':'raw/fg.png'}]}
    rp=tmp_path/'backend-result.json'; rp.write_text(json.dumps(result),encoding='utf-8')
    return source,pp,rp


def test_package_alpha_crops_and_writes_canonical_geometry(tmp_path):
    source,plan,result=fixture(tmp_path)
    manifest=lp.package_layers(source,plan,result,tmp_path/'bundle', schema_version=2)
    assert manifest['schema_version']==2
    assert manifest['source']['canvas']==[1600,900]
    assert manifest['backend']['canvas']==[800,450]
    assert manifest['missing_targets']==[]
    assert manifest['layers'][0]['z_index']==0 and manifest['layers'][0]['canonical_bbox_normalized']==[0,0,1,1]
    fg=manifest['layers'][1]
    assert fg['backend_bbox']==[100,50,200,200]
    assert fg['asset_pixel_size']==[200,200]
    assert fg['canonical_bbox_normalized']==pytest.approx([.125,50/450,.25,200/450])
    assert lv.validate_bundle(tmp_path/'bundle')['status']=='PASS'


def test_package_rejects_mismatched_canvas_and_missing_target(tmp_path):
    source,plan,result=fixture(tmp_path,mismatch=True)
    with pytest.raises(ValueError,match='LAYER_RESULT_CANVAS_INCONSISTENT'):
        lp.package_layers(source,plan,result,tmp_path/'bundle', schema_version=2)
    source,plan,result=fixture(tmp_path/'other',two_targets=True)
    with pytest.raises(ValueError,match='LAYER_TARGET_MISSING'):
        lp.package_layers(source,plan,result,(tmp_path/'other'/'bundle'), schema_version=2)


def test_bundle_validator_detects_changed_asset(tmp_path):
    source,plan,result=fixture(tmp_path)
    lp.package_layers(source,plan,result,tmp_path/'bundle', schema_version=2)
    (tmp_path/'bundle'/'foreground_01.png').write_bytes(b'changed')
    with pytest.raises(ValueError,match='asset hash mismatch'):
        lv.validate_bundle(tmp_path/'bundle')


def test_package_fit_with_padding_crops_background_padding_and_normalizes_foreground(tmp_path):
    source=tmp_path/'source.png'; Image.new('RGBA',(1600,900),'white').save(source)
    plan={'schema_version':1,'page_id':'S001','max_foregrounds':6,'recommended_total_layers':2,
          'targets':[{'id':'a','bbox':[200,100,600,500]}],'deferred':[]}
    pp=tmp_path/'plan.json'; pp.write_text(json.dumps(plan),encoding='utf-8')
    raw=tmp_path/'raw'; raw.mkdir()
    # Backend is square with vertical padding. The content rect is y=224..800.
    bg=Image.new('RGBA',(1024,1024),(0,0,0,255));
    d=ImageDraw.Draw(bg); d.rectangle((0,224,1023,799),fill=(255,255,255,255)); bg.save(raw/'bg.png')
    fg=Image.new('RGBA',(1024,1024),(0,0,0,0)); d=ImageDraw.Draw(fg); d.rectangle((128,288,383,543),fill=(255,0,0,255)); fg.save(raw/'fg.png')
    result={'schema_version':1,'page_id':'S001','provider_id':'fixture','model_id':'fixture','request_id':'t',
            'backend_canvas':[1024,1024],'source_content_rect_in_backend':[0,224,1024,576],
            'image_boxes':[[200,100,600,500]],'resized_image_boxes':[[128,288,384,544]],'boxes_mapping_index':[0],
            'layers':[{'type':'background','file':'raw/bg.png'},{'type':'foreground','target_id':'a','file':'raw/fg.png'}]}
    rp=tmp_path/'backend-result.json'; rp.write_text(json.dumps(result),encoding='utf-8')
    manifest=lp.package_layers(source,pp,rp,tmp_path/'bundle', schema_version=2)
    assert manifest['geometry']['mapping_mode']=='fit_with_padding'
    assert manifest['layers'][0]['asset_pixel_size']==[1024,576]
    assert manifest['layers'][0]['backend_bbox']==[0,224,1024,576]
    assert manifest['layers'][0]['canonical_bbox_normalized']==[0,0,1,1]
    assert manifest['layers'][1]['canonical_bbox_normalized']==pytest.approx([.125,.1111111111,.25,.4444444444],abs=1e-6)


def test_bundle_validator_recomputes_canonical_geometry_and_bbox_size(tmp_path):
    source,plan,result=fixture(tmp_path)
    lp.package_layers(source,plan,result,tmp_path/'bundle', schema_version=2)
    manifest_path=tmp_path/'bundle'/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['layers'][1]['canonical_bbox_normalized']=[.2,.2,.2,.2]
    manifest_path.write_text(json.dumps(manifest),encoding='utf-8')
    with pytest.raises(ValueError,match='geometry mismatch'):
        lv.validate_bundle(tmp_path/'bundle')

    # Restore a fresh bundle, then make backend bbox disagree with cropped asset size.
    other=tmp_path/'other'; source,plan,result=fixture(other)
    lp.package_layers(source,plan,result,other/'bundle', schema_version=2)
    manifest_path=other/'bundle'/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['layers'][1]['backend_bbox'][2] += 1
    manifest_path.write_text(json.dumps(manifest),encoding='utf-8')
    with pytest.raises(ValueError,match='bbox/asset size'):
        lv.validate_bundle(other/'bundle')
