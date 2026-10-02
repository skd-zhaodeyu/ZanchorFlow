import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import layer_geometry as g


def approx_list(a,b,tol=1e-6):
    assert len(a)==len(b)
    for x,y in zip(a,b): assert abs(x-y)<=tol,(a,b)


def test_same_size_identity_and_uniform_downscale_preserve_normalized_bbox():
    t=g.full_canvas_transform((1600,900),(1600,900))
    assert (t['sx'],t['sy'],t['tx'],t['ty'])==(1,1,0,0)
    approx_list(g.backend_bbox_to_canonical([160,90,640,180],(1600,900),t),[.1,.1,.4,.2])
    t=g.full_canvas_transform((1600,900),(800,450))
    approx_list(g.backend_bbox_to_canonical([80,45,320,90],(1600,900),t),[.1,.1,.4,.2])


def test_nonuniform_resize_inverts_independent_axes():
    t=g.full_canvas_transform((1600,900),(800,600))
    assert t['sx']==.5 and t['sy']==pytest.approx(2/3)
    approx_list(g.backend_bbox_to_canonical([80,60,320,120],(1600,900),t),[.1,.1,.4,.2])


def test_provider_mapping_uses_mapping_indices_not_return_order():
    source=[[0,0,400,300],[500,100,900,400],[1000,300,1400,800]]
    # backend is exact 0.5 x scale, 0.5 y scale; returns source indices 2 then 0.
    resized=[[500,150,700,400],[0,0,200,150]]
    t=g.transform_from_provider_boxes((1600,900),(800,450),source,resized,[2,0])
    assert t['mapping_evidence']['mapping_indices']==[2,0]
    assert t['sx']==.5 and t['sy']==.5


def test_provider_mapping_accepts_integer_rounding_and_rejects_inconsistent_geometry():
    t=g.transform_from_provider_boxes((1672,941),(1024,576),[[10,20,510,420]],[[6,12,312,257]],[0])
    assert t['sx']==pytest.approx(1024/1672)
    with pytest.raises(ValueError,match='LAYER_CANVAS_MAPPING_UNRESOLVED'):
        g.transform_from_provider_boxes((1600,900),(800,450),[[0,0,400,300]],[[0,0,300,150]],[0])


def test_source_coverage_and_target_slide_size_are_backend_independent():
    t=g.full_canvas_transform((1600,900),(800,450))
    g.validate_source_coverage((1600,900),(800,450),t)
    w,h=g.resolve_target_slide_size_emu([(1600,900),(1920,1080)])
    assert h==round(7.5*914400)
    assert w==pytest.approx(round((1600/900)*7.5*914400),abs=1)
    assert g.resolve_target_slide_size_emu([(1600,900)],(w,h))==(w,h)
    with pytest.raises(ValueError,match='TARGET_DECK_CANVAS_UNRESOLVED'):
        g.resolve_target_slide_size_emu([(1600,900),(1600,1000)])


def test_fit_with_padding_transform_restores_source_normalized_geometry():
    t=g.fit_with_padding_transform((1600,900),(1024,1024),[0,224,1024,576])
    assert t['mapping_mode']=='fit_with_padding'
    assert t['sx']==pytest.approx(1024/1600)
    assert t['sy']==pytest.approx(576/900)
    assert t['tx']==0 and t['ty']==224
    # Source [160,90,640,180] -> backend [102.4,281.6,409.6,115.2]
    approx_list(g.backend_bbox_to_canonical([102.4,281.6,409.6,115.2],(1600,900),t),[.1,.1,.4,.2])
    g.validate_source_coverage((1600,900),(1024,1024),t)


def test_provider_mapping_accepts_declared_padding_content_rect():
    source=[[200,100,600,500]]
    resized=[[128,288,384,544]]
    t=g.transform_from_provider_boxes((1600,900),(1024,1024),source,resized,[0],
                                      source_content_rect_in_backend=[0,224,1024,576])
    assert t['mapping_mode']=='fit_with_padding'
    assert t['source_content_rect_in_backend']==pytest.approx([0,224,1024,576])
