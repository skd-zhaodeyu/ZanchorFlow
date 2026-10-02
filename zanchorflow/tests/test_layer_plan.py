import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import layer_review_boxes as rb


def plan(boxes):
    return {'schema_version':1,'page_id':'S001','max_foregrounds':6,'recommended_total_layers':1+len(boxes),
            'targets':[{'id':f't{i}','label':f'T{i}','bbox':b,'edit_action':'move','selection_reason':'fixture'} for i,b in enumerate(boxes)],
            'deferred':[]}


def test_validate_plan_keeps_source_pixel_boxes_and_counts():
    p=plan([[10,20,210,220],[500,100,900,500]])
    targets=rb.validate_plan(p,1600,900)
    assert targets[0]['bbox']==[10,20,210,220]
    assert p['recommended_total_layers']==3
    assert 1+len(targets)==3


def test_provider_input_constraints_fail_before_submit():
    with pytest.raises(ValueError,match='shortest side'):
        rb.validate_plan(plan([[0,0,20,20]]),100,200)
    with pytest.raises(ValueError,match='aspect ratio'):
        rb.validate_plan(plan([[0,0,20,20]]),1000,150)
    with pytest.raises(ValueError,match='1..6'):
        rb.validate_plan(plan([]),1600,900)
    with pytest.raises(ValueError,match='1..6'):
        rb.validate_plan(plan([[i*10,0,i*10+9,20] for i in range(7)]),1600,900)
    with pytest.raises(ValueError,match='scaled box short side'):
        rb.validate_plan(plan([[0,0,5,5]]),1600,900)


def test_bbox_must_be_inside_source_and_unique_ids():
    p=plan([[0,0,100,100]])
    p['targets'][0]['bbox']=[-1,0,100,100]
    with pytest.raises(ValueError,match='outside'):
        rb.validate_plan(p,1600,900)
    p=plan([[0,0,100,100],[200,0,300,100]])
    p['targets'][1]['id']=p['targets'][0]['id']
    with pytest.raises(ValueError,match='unique'):
        rb.validate_plan(p,1600,900)
