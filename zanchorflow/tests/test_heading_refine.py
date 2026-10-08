"""Real local PPTX mutations and independent property oracles; no remote calls.
Visual qualification fixtures are labeled; program PASS is not aesthetic proof.
"""
import copy, hashlib, json, re, subprocess, sys, types
from pathlib import Path
import pytest
from PIL import Image
from lxml import etree
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Pt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import runtime as r, title_policy as t, canva_bridge as cb, layer_bridge as lb

def example():
    text=next((ROOT/"references").glob("07_*.md")).read_text(encoding="utf-8")
    start=text.index("# TITLE_POSTPROCESS_EXAMPLE_BEGIN")
    end=text.index("# TITLE_POSTPROCESS_EXAMPLE_END")+len("# TITLE_POSTPROCESS_EXAMPLE_END")
    m=types.ModuleType("title_example")
    exec(compile(text[start:end],"<protocol07 executed example>","exec"),m.__dict__)
    return m

def xml_sha(shape):
    return hashlib.sha256(etree.tostring(shape._element,method="c14n")).hexdigest()

def request_for(source,manifest,mapping,protected,created,font="Arial",rect=None,run="offline",ref="offline-contract"):
    m=example();prs=Presentation(source)
    binding={"run_id":run,"slide_id":manifest["slide_id"],"contract_ref":ref,
             "canvas_size_emu":[prs.slide_width,prs.slide_height],"effective_font":font,
             "restored_input_sha256":m._title_file_sha(source),"manifest_digest":m._title_digest(manifest)}
    native={"identity":{k:binding[k] for k in ("run_id","contract_ref","canvas_size_emu","effective_font")},
            "max_lines":2,"style":{"title_region":[.08,.04,.84,.17],"font_size_pt":24*prs.slide_height/6858000,
            "bold":True,"color":"#203040","alignment":"left","first_line_baseline":.10,
            "first_line_offset_emu":int(Pt(20*prs.slide_height/6858000)),"line_height_ratio":1.15}}
    shapes={s.shape_id:s for s in prs.slides[0].shapes}
    return {"binding":binding,"native_snapshot":native,"native_snapshot_sha256":m._title_digest(native),
            "manifest":manifest,"element_shapes":mapping,
            "restored_shape_xml_sha256":{i:xml_sha(shapes[sid]) for i,sid in mapping.items()},
            "protected_shape_ids":protected,"created_native_shape_ids":created,
            "content_rect_emu":rect or [0,0,prs.slide_width,prs.slide_height]}

def native_case(tmp_path,text="A navigation heading",multi=False,font="Arial",rect=None):
    tmp_path.mkdir(parents=True,exist_ok=True)
    prs=Presentation();prs.slide_width=12192000;prs.slide_height=6858000
    slide=prs.slides.add_slide(prs.slide_layouts[6])
    graphic=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,10000,3200000,300000,200000)
    image=tmp_path/"asset.png";Image.new("RGB",(20,20),"orange").save(image)
    picture=slide.shapes.add_picture(str(image),10000,3500000,width=250000)
    body=slide.shapes.add_textbox(800000,4200000,5000000,1300000);body.text=text
    for p in body.text_frame.paragraphs:
        for run in p.runs:run.font.name="Arial";run.font.size=Pt(12)
    elements=[];mapping={}
    for i,part in enumerate(["First part","Second part"] if multi else [text]):
        box=slide.shapes.add_textbox(1000000,800000+i*int(Pt(32)),6500000,int(Pt(28)) if multi else 650000)
        box.text=part
        for p in box.text_frame.paragraphs:
            for run in p.runs:run.font.name="Times New Roman";run.font.size=Pt(24 if multi else 36)
        eid="H"+str(i+1);mapping[eid]=box.shape_id
        e={"id":eid,"content":part,"representation_role":"native_text","treatment":"remove_and_restore"}
        if multi:e.update(text_group_id="title-group",group_sequence=i)
        elements.append(e)
    source=tmp_path/"restored.pptx";prs.save(source)
    manifest={"slide_id":"S002","title_contract_ref":"offline-contract",
              "title_element_ids":list(mapping),"text_elements":elements}
    req=request_for(source,manifest,mapping,[graphic.shape_id,picture.shape_id],
                    [body.shape_id,*mapping.values()],font,rect)
    return source,req,body.shape_id

def apply(tmp_path,source,req,stem="normalized"):
    return example().adjust_primary_title(source,tmp_path/(stem+".pptx"),tmp_path/(stem+".json"),req)

def assert_actual(source,output,req):
    a,b=Presentation(source).slides[0],Presentation(output).slides[0]
    targets=set(req["element_shapes"].values())
    assert [s.shape_id for s in a.shapes]==[s.shape_id for s in b.shapes]
    original={s.shape_id:s for s in a.shapes}
    assert example()._title_resources(source)==example()._title_resources(output)
    for s in b.shapes:
        if s.has_text_frame:assert s.text==original[s.shape_id].text
        if s.shape_id not in targets:assert xml_sha(s)==xml_sha(original[s.shape_id])
        else:
            assert s.text_frame.auto_size is not None  # explicit NONE, not font shrink
            for p in s.text_frame.paragraphs:
                assert p.alignment==PP_ALIGN.LEFT
                for run in p.runs:
                    assert run.font.size==Pt(req["native_snapshot"]["style"]["font_size_pt"])
                    assert run.font.name==req["binding"]["effective_font"]

@pytest.mark.parametrize("text,font",[("A navigation heading","Arial"),
    ("Two lines\nSame native point size","Arial"),("原生标题\n共同后备字体","Microsoft YaHei")])
def test_document_example_changes_real_title_only_and_keeps_same_text_body(tmp_path,text,font):
    src,req,body=native_case(tmp_path,text=text,font=font);before=src.read_bytes()
    note=apply(tmp_path,src,req);assert note["status"]=="adjusted",note
    assert_actual(src,tmp_path/"normalized.pptx",req)
    assert src.read_bytes()==before
    target=Presentation(tmp_path/"normalized.pptx").slides[0].shapes[-1]
    assert target.left==round(.08*12192000)
    assert target.top==round(.1*6858000-int(Pt(20)))
    assert note["visual_review"]=="pending"
    assert note["output_sha256"]==example()._title_file_sha(tmp_path/"normalized.pptx")

def test_content_rectangle_not_full_slide_controls_geometry(tmp_path):
    rect=[600000,300000,10800000,6000000]
    src,req,_=native_case(tmp_path,rect=rect)
    assert apply(tmp_path,src,req)["status"]=="adjusted"
    title=Presentation(tmp_path/"normalized.pptx").slides[0].shapes[-1]
    assert title.left==round(rect[0]+.08*rect[2])
    assert title.top==round(rect[1]+.10*rect[3]-int(Pt(20)))
    assert title.width==round(.84*rect[2])
    assert title.left!=round(.08*12192000)

def test_multiple_title_boxes_translate_as_block_not_overlaid(tmp_path):
    src,req,_=native_case(tmp_path,multi=True)
    before=Presentation(src).slides[0].shapes
    delta=before[-1].top-before[-2].top
    assert apply(tmp_path,src,req)["status"]=="adjusted"
    after=Presentation(tmp_path/"normalized.pptx").slides[0].shapes
    assert after[-1].top-after[-2].top==delta
    assert after[-1].top!=after[-2].top
    assert_actual(src,tmp_path/"normalized.pptx",req)

@pytest.mark.parametrize("bad",["same_text_body","unknown_id","protected","graphic_role","drop_role",
    "duplicate","unknown_group","wrong_title_content","snapshot","run","contract","canvas","font",
    "source_hash","manifest_hash","three_lines"])
def test_wrong_inputs_do_not_silently_modify_or_claim_visual_pass(tmp_path,bad):
    src,req,body=native_case(tmp_path,multi=bad=="unknown_group",text="one\ntwo\nthree" if bad=="three_lines" else "Same exact text")
    before=src.read_bytes()
    if bad=="same_text_body":req["element_shapes"]["H1"]=body
    elif bad=="unknown_id":req["element_shapes"]["H1"]=9999
    elif bad=="protected":req["protected_shape_ids"].append(req["element_shapes"]["H1"])
    elif bad=="graphic_role":req["manifest"]["text_elements"][0]["representation_role"]="graphic_typography"
    elif bad=="drop_role":req["manifest"]["text_elements"][0]["treatment"]="remove_and_drop"
    elif bad=="duplicate":req["manifest"]["title_element_ids"].append("H1")
    elif bad=="unknown_group":req["manifest"]["text_elements"][1].pop("text_group_id")
    elif bad=="wrong_title_content":req["manifest"]["text_elements"][0]["content"]="Wrong expected content"
    elif bad=="snapshot":req["native_snapshot"]["style"]["font_size_pt"]=30
    elif bad in {"run","contract","canvas","font"}:
        key={"run":"run_id","contract":"contract_ref","canvas":"canvas_size_emu","font":"effective_font"}[bad]
        req["binding"][key]=[1,1] if bad=="canvas" else "changed"
    elif bad=="source_hash":req["binding"]["restored_input_sha256"]="0"*64
    elif bad=="manifest_hash":req["binding"]["manifest_digest"]="0"*64
    elif bad=="three_lines":req["manifest"]["text_elements"][0]["content"]="one\ntwo\nthree"
    if bad not in {"manifest_hash","snapshot"}:
        req["binding"]["manifest_digest"]=example()._title_digest(req["manifest"])
    note=apply(tmp_path,src,req)
    assert note["status"]=="not_adjusted",bad
    assert note["visual_review"]=="pending"
    assert src.read_bytes()==before and not (tmp_path/"normalized.pptx").exists()

def test_graphic_or_local_display_exception_not_converted(tmp_path):
    src,req,_=native_case(tmp_path)
    req["manifest"]["title_element_ids"]=[]
    req["binding"]["manifest_digest"]=example()._title_digest(req["manifest"])
    assert apply(tmp_path,src,req)["status"]=="not_adjusted"
    assert not (tmp_path/"normalized.pptx").exists()

def test_cache_reuses_only_verified_same_bytes_and_parameters(tmp_path):
    src,req,_=native_case(tmp_path);apply(tmp_path,src,req)
    out=tmp_path/"normalized.pptx";record=tmp_path/"normalized.json"
    original=(out.read_bytes(),out.stat().st_mtime_ns,record.read_bytes())
    assert apply(tmp_path,src,req)["reused"] is True
    assert (out.read_bytes(),out.stat().st_mtime_ns,record.read_bytes())==original
    # Real mutation: same filename is no longer the verified output.
    prs=Presentation(out);prs.slides[0].shapes[-1].text="Tampered title";prs.save(out)
    changed=out.read_bytes()
    assert apply(tmp_path,src,req)["status"]=="not_adjusted"
    assert out.read_bytes()==changed and record.read_bytes()==original[2]

@pytest.mark.parametrize("changed",["source","parameters","missing_output"])
def test_changed_or_missing_cache_is_not_unconditionally_reused(tmp_path,changed):
    src,req,_=native_case(tmp_path);apply(tmp_path,src,req)
    if changed=="source":
        prs=Presentation(src);prs.slides[0].shapes[-1].text="Changed source";prs.save(src)
        assert apply(tmp_path,src,req)["status"]=="not_adjusted"
    elif changed=="parameters":
        req["native_snapshot"]["style"]["font_size_pt"]=28
        assert apply(tmp_path,src,req)["status"]=="not_adjusted"
    else:
        receipt=(tmp_path/"normalized.json").read_bytes()
        (tmp_path/"normalized.pptx").unlink()
        assert apply(tmp_path,src,req)["status"]=="not_adjusted"
        assert (tmp_path/"normalized.json").read_bytes()==receipt
        assert apply(tmp_path,src,req,stem="regenerated")["reused"] is False
        assert_actual(src,tmp_path/"regenerated.pptx",req)

def test_original_source_cannot_be_overwritten(tmp_path):
    src,req,_=native_case(tmp_path);before=src.read_bytes()
    note=example().adjust_primary_title(src,src,tmp_path/"note.json",req)
    assert note["status"]=="not_adjusted" and src.read_bytes()==before

def route_request(state,sid,source):
    saved=r.load_runtime_state(state)
    manifest=json.loads(Path(saved["slides"][sid]["finalized_manifest"]).read_text(encoding="utf-8"))
    shapes=list(Presentation(source).slides[0].shapes)
    assert len(manifest["title_element_ids"])==1
    return request_for(source,manifest,{manifest["title_element_ids"][0]:shapes[-1].shape_id},
        [s.shape_id for s in shapes[:-1]],[shapes[-1].shape_id],
        run=saved["stage2_run"]["run_id"],ref=t.context(state,sid)["contract_ref"])

@pytest.mark.parametrize("backend",["magic_layer","image_layer"])
def test_actual_postprocessed_bytes_enter_both_sealers_and_old_review_fails(tmp_path,backend):
    from test_title_routes import restored_pages
    state,pages=restored_pages(tmp_path,backend)
    gf,src,rp=pages["S002"];req=route_request(state,"S002",src)
    out=tmp_path/"normalized.pptx";note=apply(tmp_path,src,req)
    assert note["status"]=="adjusted";assert_actual(src,out,req)
    seal=cb.seal_page if backend=="magic_layer" else lb.seal_page
    before=state.read_bytes()
    with pytest.raises(ValueError,match="hash mismatch"):seal(state,"S002",out,rp)
    assert state.read_bytes()==before
    review=json.loads(rp.read_text(encoding="utf-8"))
    review["restored_pptx_sha256"]=cb.sha(out)
    review["evidence"]["visual_fidelity"]="OFFLINE native title attributes and non-title object/resource oracle passed; aesthetic assessment remains a fixture."
    review["title_postprocessing"]=note
    rp.write_text(json.dumps(review),encoding="utf-8")
    assert seal(state,"S002",out,rp)["status"]=="PAGE_SEALED"
    assert r.load_runtime_state(state)["slides"]["S002"]["validated_single_page"]["validated_pptx_sha256"]==cb.sha(out)

@pytest.mark.parametrize("original", [True,False])
def test_two_canvas_paths_recompute_original_graphics_and_reject_real_graphic_damage(tmp_path,original):
    from test_canvas_adaptation import sealed_fixture
    state,download,src,canvas,review,rp=sealed_fixture(tmp_path,ordinary_text=True,original_tolerance=original)
    frozen=json.loads(Path(r.load_runtime_state(state)["slides"]["S001"]["finalized_manifest"]).read_text(encoding="utf-8"))
    # Complete the synthetic recovery with the actual frozen content, not a fake label.
    prs=Presentation(src);title=prs.slides[0].shapes[-1]
    title.text=frozen["text_elements"][0]["content"];prs.save(src)
    manifest=copy.deepcopy(frozen);manifest.update(title_contract_ref="offline-contract",title_element_ids=[manifest["text_elements"][0]["id"]])
    req=request_for(src,manifest,{manifest["title_element_ids"][0]:title.shape_id},
        [s.shape_id for s in list(prs.slides[0].shapes)[:-1]],[title.shape_id],rect=review["canvas_mapping"]["plan"]["content_rect_emu"])
    out=tmp_path/"normalized.pptx"
    assert apply(tmp_path,src,req)["status"]=="adjusted"
    assert_actual(src,out,req)
    mapping=copy.deepcopy(review["canvas_mapping"]);mapping["restored_pptx_sha256"]=cb.sha(out)
    cb.verify_canvas_mapping(download,out,canvas,mapping)
    # Updating a hash cannot hide a genuine retained-graphic modification.
    bad=tmp_path/"damaged.pptx";prs=Presentation(out);prs.slides[0].shapes[0].left+=10000;prs.save(bad)
    mapping["restored_pptx_sha256"]=cb.sha(bad)
    with pytest.raises(ValueError,match="retained object differs"):cb.verify_canvas_mapping(download,bad,canvas,mapping)
    mapping["restored_pptx_sha256"]=cb.sha(out)
    review.update(restored_pptx_sha256=cb.sha(out),canvas_mapping=mapping)
    rp.write_text(json.dumps(review),encoding="utf-8")
    assert cb.seal_page(state,"S001",out,rp)["status"]=="PAGE_SEALED"

@pytest.mark.parametrize("gate",["content_truth","visual_fidelity"])
def test_unification_metadata_does_not_override_real_failed_gate(tmp_path,gate):
    from test_title_routes import restored_pages
    state,pages=restored_pages(tmp_path,"magic_layer");gf,src,rp=pages["S002"]
    req=route_request(state,"S002",src);apply(tmp_path,src,req)
    out=tmp_path/"normalized.pptx";prs=Presentation(out)
    if gate=="content_truth":
        prs.slides[0].shapes[-1].text="Actual wrong text";prs.save(out)
        assert prs.slides[0].shapes[-1].text!=req["manifest"]["text_elements"][0]["content"]
    else:
        prs.slides[0].shapes[-1].top=prs.slide_height;prs.save(out)
        assert prs.slides[0].shapes[-1].top>=prs.slide_height
    review=json.loads(rp.read_text());review.update(restored_pptx_sha256=cb.sha(out),title_postprocessing={"status":"adjusted"})
    review["checks"][gate]="FAIL";review["evidence"][gate]="Actual wrong content/off-canvas geometry observed in saved PPTX."
    rp.write_text(json.dumps(review));before=state.read_bytes()
    with pytest.raises(ValueError,match="four Hard Gates"):cb.seal_page(state,"S002",out,rp)
    assert state.read_bytes()==before

def test_partial_title_notes_publish_without_repair_or_seal_changes(tmp_path,monkeypatch):
    import assemble_deck as assembly
    from test_title_routes import restored_pages,offline_native
    from test_merge import _complete_deck_review
    state,pages=restored_pages(tmp_path,"magic_layer")
    for sid,(gf,src,rp) in pages.items():
        if sid!="S001":
            req=route_request(state,sid,src)
            note=apply(tmp_path,src,req,stem=sid+"-normalized");out=tmp_path/(sid+"-normalized.pptx")
            assert_actual(src,out,req)
            if sid=="S003":
                prs=Presentation(out)
                for p in prs.slides[0].shapes[-1].text_frame.paragraphs:
                    for run in p.runs:run.font.size=Pt(24.5)
                prs.save(out)  # actual small residual, reported honestly
            review=json.loads(rp.read_text());review["restored_pptx_sha256"]=cb.sha(out)
            review["evidence"]["visual_fidelity"]="OFFLINE native properties inspected; S003 has a declared 0.5-point residual. Image aesthetics are a fixture."
            rp.write_text(json.dumps(review));src=out
        cb.seal_page(state,sid,src,rp)
    before=r.load_runtime_state(state)
    hashes={sid:r.load_runtime_state(state)["slides"][sid]["validated_single_page"]["validated_pptx_sha256"] for sid in pages}
    offline_native(monkeypatch);made=assembly.prepare(state,tmp_path/"assembly")
    report=Path(made["validation_report"]);_complete_deck_review(report)
    review=json.loads(report.read_text());review["title_notes"]=[{"page":"S003","status":"partial","difference":"24.5 pt versus 24 pt","manual_location":"native primary title"}]
    review["evidence"]["font_consistency"]="OFFLINE measured minor native-title residual disclosed; content remains readable; no exact-consistency claim."
    report.write_text(json.dumps(review))
    assert assembly.publish(state,report,tmp_path/"outputs/final.pptx")["status"]=="PASS"
    after=r.load_runtime_state(state)
    assert before["slides"]==after["slides"]
    for sid in pages:
        record=after["slides"][sid]["validated_single_page"]
        assert record["validated_pptx_sha256"]==hashes[sid]
        assert cb.sha(record["path"])==hashes[sid]

def test_uniform_context_guidance_is_readonly_and_legacy_free_cover_unchanged(tmp_path):
    from test_title_policy import setup,choose
    from heading_refine_scope import restore_bytes
    old=types.ModuleType("baseline_titles")
    exec(compile(restore_bytes("scripts/title_policy.py",(ROOT/"scripts/title_policy.py").read_bytes()),"<locked baseline>","exec"),old.__dict__)
    state=setup(tmp_path);choose(state);before=state.read_bytes()
    saved=r.load_runtime_state(state)
    assert t.context_from_state(saved,"S001")==old.context_from_state(saved,"S001")
    current=t.context(state,"S002");assert "标题区域和对齐" in current["heading_requirement"]
    assert "独立统一主标题" in current["heading_requirement"]
    assert state.read_bytes()==before
    legacy=copy.deepcopy(saved);legacy["stage2_run"].pop("title_policy")
    assert t.context_from_state(legacy,"S002")==old.context_from_state(legacy,"S002")
    free=copy.deepcopy(saved);free["stage2_run"]["title_policy"]["mode"]="free"
    assert t.context_from_state(free,"S002")==old.context_from_state(free,"S002")

def test_six_field_example_executes_and_extra_field_is_still_rejected(tmp_path):
    from test_title_policy import setup
    doc=next((ROOT/"references").glob("01_*.md")).read_text(encoding="utf-8")
    sample=json.loads(re.search(r"~~~json\n(.+?)\n~~~",doc,re.S).group(1))
    state=setup(tmp_path);op=tmp_path/"new-outline.json";op.write_text(json.dumps(sample,ensure_ascii=False),encoding="utf-8")
    assert r.record_stage1_draft(state,op)
    view=r.present_stage1_review(state);assert "从内容到交付" in json.dumps(view,ensure_ascii=False)
    sample["slides"][0]["slide_id"]="S001";op.write_text(json.dumps(sample));before=state.read_bytes()
    with pytest.raises(ValueError,match="exactly six fields"):r.record_stage1_draft(state,op)
    assert state.read_bytes()==before

def test_pass_notes_execute_but_failure_evidence_still_rejected(tmp_path):
    from test_title_policy import setup,choose
    from stage2_test_helpers import write_png
    state=setup(tmp_path);choose(state)
    png=write_png(tmp_path/"heading.png",b"offline")
    candidate=r.register_stage2_candidate(state,"S002",png,"OFFLINE font-size residual fixture")
    with pytest.raises(ValueError,match="PASS_CANNOT"):r.review_stage2_candidate(state,candidate["candidate_id"],"PASS",observable_evidence="Misused note")
    result=r.review_stage2_candidate(state,candidate["candidate_id"],"PASS",review_notes=["same area; native size alignment deferred"])
    assert result["review"]["review_notes"][0]
    assert result["status"]=="approved"

def test_cli_help_and_old_parser_contract(tmp_path):
    done=subprocess.run([sys.executable,"-B",str(ROOT/"scripts/runtime.py"),"--help"],capture_output=True,text=True,encoding="utf-8")
    assert done.returncode==0 and "max_lines=2 is a ceiling" in " ".join(done.stdout.split())
    assert "PASS observations" in done.stdout
    from test_title_policy import seeded,payload
    state,ref=seeded(tmp_path);bad=payload(state,"S002");bad["style"]["max_lines"]=1
    before=state.read_bytes()
    with pytest.raises(ValueError,match="TITLE_SCALE_INVALID"):t.bind(state,"S002",bad)
    assert state.read_bytes()==before

def test_declared_deltas_restore_locked_bytes_and_detect_unapproved_changes():
    from heading_refine_scope import data,restore_bytes
    approved=data()
    for rel in {x["path"] for x in approved["patches"] if x["repo_path"].startswith("zanchorflow/")}:
        restored=restore_bytes(rel,(ROOT/rel).read_bytes())
        assert hashlib.sha256(restored).hexdigest()==approved["baseline"]["zanchorflow/"+rel]
    with pytest.raises(AssertionError):
        restore_bytes("scripts/runtime.py",(ROOT/"scripts/runtime.py").read_bytes()+b"\n# undeclared behavior\n")

@pytest.mark.integration
def test_office_actual_title_bounds_font_and_save_reopen_copy(tmp_path):
    import win32com.client
    src,req,_=native_case(tmp_path,text="第一行标题\n第二行说明",font="Microsoft YaHei")
    note=apply(tmp_path,src,req);assert note["status"]=="adjusted"
    final=tmp_path/"normalized.pptx";final_sha=cb.sha(final)
    office_copy=tmp_path/"office-copy.pptx";office_copy.write_bytes(final.read_bytes())
    def pids():
        text=subprocess.run(["powershell.exe","-NoProfile","-Command","Get-Process -Name POWERPNT -ErrorAction SilentlyContinue | ForEach-Object Id"],capture_output=True,text=True).stdout
        return {int(x) for x in text.split() if x.isdigit()}
    previous=pids();app=win32com.client.DispatchEx("PowerPoint.Application");pres=None
    try:
        pres=app.Presentations.Open(str(office_copy),False,False,False)
        title=pres.Slides(1).Shapes(pres.Slides(1).Shapes.Count)
        assert abs(title.TextFrame.TextRange.Font.Size-24)<.01
        assert title.TextFrame.TextRange.Font.Name in {"Microsoft YaHei","微软雅黑"}
        assert abs(title.Left-note["applied_geometry_emu"][str(title.Id)][0]/12700)<.1
        glyph=title.TextFrame2.TextRange
        assert glyph.BoundHeight<=title.Height+1
        assert glyph.BoundTop+glyph.BoundHeight<4200000/12700
        pres.Slides(1).Export(str(tmp_path/"native-title.png"),"PNG",1280,720)
        title.TextFrame.TextRange.Font.Size=25
        pres.Save();pres.Close();pres=None
        pres=app.Presentations.Open(str(office_copy),False,False,False)
        title=pres.Slides(1).Shapes(pres.Slides(1).Shapes.Count)
        assert abs(title.TextFrame.TextRange.Font.Size-25)<.01
        assert title.TextFrame.TextRange.Text.replace("\r","\n")=="第一行标题\n第二行说明"
        assert cb.sha(final)==final_sha
    finally:
        if pres is not None:pres.Close()
        # PowerPoint may share a process; never quit a pre-existing application.
        if pids()-previous:app.Quit()

def test_actual_cli_review_notes_array_and_invalid_object(tmp_path):
    from test_title_policy import setup,choose
    from stage2_test_helpers import write_png
    state=setup(tmp_path);choose(state)
    png=write_png(tmp_path/"cli-title.png",b"offline-cli")
    candidate=r.register_stage2_candidate(state,"S002",png,"OFFLINE CLI notes fixture")
    notes=tmp_path/"notes.json";notes.write_text(json.dumps({"title":"invalid object"}),encoding="utf-8")
    command=[sys.executable,"-B",str(ROOT/"scripts/runtime.py"),"stage2-candidate-review",
             "--state",str(state),"--candidate-id",candidate["candidate_id"],"--verdict","PASS",
             "--review-notes-json",str(notes)]
    before=state.read_bytes()
    rejected=subprocess.run(command,capture_output=True,text=True,encoding="utf-8")
    assert rejected.returncode!=0 and "STAGE2_REVIEW_NOTES_INVALID" in rejected.stdout
    assert state.read_bytes()==before
    notes.write_text(json.dumps(["同一区域的字号差异，待原生标题后处理"],ensure_ascii=False),encoding="utf-8")
    actual=subprocess.run(command,capture_output=True,text=True,encoding="utf-8")
    assert actual.returncode==0,actual.stdout+actual.stderr
    saved=r.load_runtime_state(state)["stage2_run"]["candidates"][candidate["candidate_id"]]
    assert saved["status"]=="approved"
    assert saved["review"]["review_notes"]==["同一区域的字号差异，待原生标题后处理"]

def test_actual_revision_scope_checked_exactly_without_overwriting_old_identity_expectations():
    from heading_refine_scope import identity_manifest,data
    import yaml
    raw=yaml.safe_load((ROOT/"manifest.yaml").read_text(encoding="utf-8"))
    from office_scope import normalize_manifest
    assert normalize_manifest(raw)["revision_scope"]==data()["baseline_revision_scope"]+data()["added_revision_scope"]
    assert len(identity_manifest(ROOT)["revision_scope"])==7
    for bad in [raw["revision_scope"]+["unapproved"],raw["revision_scope"][:-1],list(reversed(raw["revision_scope"]))]:
        payload=copy.deepcopy(raw);payload["revision_scope"]=bad
        with pytest.raises(AssertionError,match="undeclared or missing"):identity_manifest(ROOT,payload)
