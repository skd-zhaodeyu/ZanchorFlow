import base64
import json

PNG_1X1 = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2pFQAAAAASUVORK5CYII='
)


def write_png(path, marker=b''):
    path.write_bytes(PNG_1X1 + marker)
    return str(path)


def write_truth(path, slide_id, text='x'):
    payload = {
        'slide_id': slide_id,
        'meaningful_text': [] if text is None else [{'text': text}],
        'exact_facts': [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    return str(path)


def approve_page(runtime, state_path, slide_id, image_path, intent=None, approval_mode='qualification_review'):
    candidate = runtime.register_stage2_candidate(
        state_path, slide_id, image_path,
        generation_intent=intent or f'fixture {slide_id}')
    runtime.review_stage2_candidate(
        state_path, candidate['candidate_id'], 'PASS', approval_mode=approval_mode)
    return candidate


def complete_stage2_page(runtime, state_path, slide_id, image_path, truth_path, intent=None):
    approve_page(runtime, state_path, slide_id, image_path, intent=intent)
    runtime.register_stage2_artifact(state_path, f'final_content_truth:{slide_id}', truth_path)
    runtime.mark_stage2_text_reconciled(state_path, slide_id)
    # Legacy downstream fixtures represent a user-approved visual set once the last page is ready.
    if runtime.stage2_visual_status(state_path)['status'] == 'COMPLETE':
        runtime.present_stage2_formal_display(state_path)
        try:
            runtime.require_stage2_visual_approval(state_path)
        except ValueError:
            runtime.seal_stage2_visual_approval(state_path, '确认，按这组页面进入下一阶段。')


def write_stage3_text_plan(manifest_path, inventory_path, slide_id, text):
    manifest = {
        'schema_version':'1.1','slide_id':slide_id,'source_width':1600,'source_height':900,
        'text_elements':[{
            'id':'M001','truth_ref':f'{slide_id}:T001','truth_source':'stage2_final_content_truth',
            'content':text,'text_role':'semantic_text','representation_role':'native_text',
            'treatment':'remove_and_restore','visual_bbox_normalized':[0.1,0.1,0.4,0.1],
        }],
    }
    inventory = {
        'schema_version':'1.1','slide_id':slide_id,'items':[{
            'region_id':'R001','visual_bbox_normalized':[0.1,0.1,0.4,0.1],
            'observed_text':text,'detection_source':'manifest_seed','treatment':'remove_and_restore',
            'linked_manifest_ids':['M001'],'destructive_cleanup_risk':'low',
        }],
    }
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False),encoding='utf-8')
    inventory_path.write_text(json.dumps(inventory,ensure_ascii=False),encoding='utf-8')
    return str(manifest_path), str(inventory_path)
