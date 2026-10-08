"""Ordered assembly using current seals; visual validation remains an explicit review."""
import argparse
import copy
import hashlib
import json
import shutil
from pathlib import Path
import preflight
import reconstruction_router as bridge
from merge_pptx import merge
from runtime import (load_runtime_state, _save_runtime_state, require_stage2_entry,
                     validate_deck_order, validate_current_artifact, stage2_handoff_status,
                     validate_current_merged_deck, seal_merged_deck, seal_validated_deck)

DECK_CHECKS = ('single_page_hard_gates', 'page_count', 'page_order', 'canvas',
               'title_hierarchy', 'font_consistency', 'motif_consistency',
               'background_family', 'page_numbers_fixed_elements',
               'functional_editability', 'visual_fidelity')


def current_inputs(state):
    run_order = state.get('stage2_run', {}).get('page_order')
    order = state.get('deck_order', run_order)
    if not isinstance(run_order, list) or not run_order or not isinstance(order, list):
        raise ValueError('trusted page order missing')
    if not validate_deck_order(run_order, order) or not validate_deck_order(list(state['slides']), order):
        raise ValueError('missing, duplicate or unknown current page identity')
    inputs = []
    for slide_id in order:
        record = state['slides'][slide_id].get('validated_single_page')
        errors = validate_current_artifact(record, state, slide_id)
        if errors:
            raise ValueError(slide_id + ': ' + ', '.join(errors))
        bridge.page_provenance(state,slide_id)
        inputs.append(copy.deepcopy(record))
    return order, inputs


def accepted_limitations(pages):
    return [{**limitation,'page_id':page['slide_id']} for page in pages
            if page.get('backend')=='image_layer' for limitation in page.get('accepted_limitations',[])]


def _review_template(state, order):
    return {
        'merged_pptx_sha256':state['merged_deck']['merged_pptx_sha256'],
        'deck_order':order,
        'page_provenance':bridge.merged_provenance(state)['pages'],
        **({'accepted_limitations':accepted_limitations(bridge.merged_provenance(state)['pages']),
            'limitation_matches':[]} if accepted_limitations(bridge.merged_provenance(state)['pages']) else {}),
        'checks':{key:'PENDING' for key in DECK_CHECKS},
        'evidence':{key:'' for key in DECK_CHECKS},
    }


def recover_review(state_path):
    require_stage2_entry(state_path)
    if stage2_handoff_status(state_path)['status'] != 'COMPLETE':
        raise ValueError('current Stage 2 handoff incomplete')
    state = load_runtime_state(state_path)
    errors = validate_current_merged_deck(state)
    if errors:
        raise ValueError(', '.join(errors))
    order,_ = current_inputs(state)
    provenance = bridge.merged_provenance(state)
    if (provenance.get('pages') != bridge.deck_provenance(state,order)
            or provenance.get('merged_pptx_sha256') != state['merged_deck']['merged_pptx_sha256']):
        raise ValueError('candidate provenance changed')
    if state.get('validated_deck',{}).get('status') == 'PASS':
        raise ValueError('deck already validated; no pending review needed')
    candidate = bridge.resolve(state,state['merged_deck']['merged_pptx_path'])
    review_path = candidate.parent/'deck-review.json'
    if review_path.exists():
        raise ValueError('review already exists; never overwrite completed or pending observations')
    try:
        review_path.write_text(json.dumps(_review_template(state,order),ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:
        review_path.unlink(missing_ok=True)
        raise
    return {'status':'AWAITING_DECK_VALIDATION','path':str(candidate),'validation_report':str(review_path)}


def prepare(state_path, work_dir, *, office_host='auto'):
    state_path = Path(state_path).resolve()
    require_stage2_entry(state_path)
    if stage2_handoff_status(state_path)['status'] != 'COMPLETE':
        raise ValueError('current Stage 2 handoff incomplete')
    state = load_runtime_state(state_path)
    order, inputs = current_inputs(state)
    work_dir = Path(work_dir).resolve()
    if 'outputs' in (part.lower() for part in work_dir.parts):
        raise ValueError('candidate must be prepared in work, not outputs')
    candidate = work_dir/'deck-candidate.pptx'
    review_path = work_dir/'deck-review.json'
    if review_path.exists():
        raise ValueError('review exists; preserve it and use a new work directory')
    if candidate.exists():
        raise ValueError('candidate exists; use a new work directory')
    report = preflight.check(Path(__file__).parent.parent, work_dir, scope='merge', office_host=office_host)
    if preflight.exit_code(report):
        return {'status':'FAIL', 'code':'MERGE_PREFLIGHT_FAILED', 'preflight':report}
    candidate_created = False
    review_created = False
    try:
        with bridge.transaction(state_path) as temp:
            current = load_runtime_state(temp)
            new_order, new_inputs = current_inputs(current)
            if new_order != order or new_inputs != inputs:
                raise ValueError('assembly inputs changed during preflight')
            if 'deck_order' not in current:
                current['deck_order'] = list(order)
                _save_runtime_state(temp,current)
            result = merge(inputs,order,candidate,temp,office_host=report['office_host'])
            candidate_created = candidate.exists()
            if result['status'] != 'PASS':
                raise ValueError('native merge failed: '+str(result))
            current = load_runtime_state(temp)
            pages = bridge.deck_provenance(current,order)
            bridge.set_merged_provenance(current,pages,current['merged_deck']['merged_pptx_sha256'])
            _save_runtime_state(temp,current)
            review_created = True
            review = _review_template(current,order)
            review['native_merge'] = {key:result[key] for key in ('office_host','office_progid','office_attempts','cleanup_errors') if key in result}
            review_path.write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:
        if candidate_created:
            candidate.unlink(missing_ok=True)
        if review_created:
            review_path.unlink(missing_ok=True)
        raise
    return {**result, 'status':'AWAITING_DECK_VALIDATION', 'validation_report':str(review_path), 'preflight':report}


def publish(state_path, validation_report, output):
    state_path = Path(state_path).resolve()
    require_stage2_entry(state_path)
    if stage2_handoff_status(state_path)['status'] != 'COMPLETE':
        raise ValueError('current Stage 2 handoff incomplete')
    state = load_runtime_state(state_path)
    errors = validate_current_merged_deck(state)
    if errors:
        raise ValueError(', '.join(errors))
    order, inputs = current_inputs(state)
    pages = bridge.deck_provenance(state,order)
    merged_provenance = bridge.merged_provenance(state)
    if merged_provenance.get('pages') != pages or merged_provenance.get('merged_pptx_sha256') != state['merged_deck']['merged_pptx_sha256']:
        raise ValueError('merged design provenance changed')
    review = json.loads(Path(validation_report).read_text(encoding='utf-8'))
    if not isinstance(review,dict):
        raise ValueError('Deck-Level Validation report must be a JSON object')
    for section in ('checks','evidence'):
        if section in review and not isinstance(review[section],dict):
            raise ValueError('Deck-Level Validation '+section+' must be a JSON object')
    if review.get('page_provenance') != pages:
        raise ValueError('Deck-Level Validation belongs to old design attempts')
    if (review.get('deck_order') != order or review.get('merged_pptx_sha256') != state['merged_deck']['merged_pptx_sha256']):
        raise ValueError('Deck-Level Validation is not bound to current merged bytes/order')
    limitations=accepted_limitations(pages)
    if limitations:
        from layer_policy import validate_context
        validate_context(review,limitations)
    for key in DECK_CHECKS:
        if review.get('checks',{}).get(key) != 'PASS' or not isinstance(review.get('evidence',{}).get(key),str) or not review['evidence'][key].strip():
            raise ValueError('Deck-Level Validation incomplete: ' + key)
    source = Path(state['merged_deck']['merged_pptx_path'])
    if not source.is_absolute():
        source = Path(state['_base_dir'])/source
    output = Path(output).resolve()
    if 'outputs' not in (part.lower() for part in output.parent.parts):
        raise ValueError('final delivery must be under outputs')
    if output.suffix.lower() != '.pptx' or output.exists():
        raise ValueError('use a new .pptx output path; no overwrite')
    output.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation protects an existing delivery, including between checks.
    created = False
    try:
        with output.open('xb') as dest:
            created = True
            with source.open('rb') as src:
                shutil.copyfileobj(src,dest)
        digest = hashlib.sha256()
        with output.open('rb') as delivered:
            for chunk in iter(lambda: delivered.read(1024 * 1024), b''):
                digest.update(chunk)
        delivered_hash = digest.hexdigest()
        if delivered_hash != review['merged_pptx_sha256']:
            raise ValueError('copied deck differs from reviewed bytes')
        with bridge.transaction(state_path) as temp:
            current = load_runtime_state(temp)
            if bridge.deck_provenance(current,order) != pages or validate_current_merged_deck(current):
                raise ValueError('current sources changed during publication')
            if current['merged_deck']['merged_pptx_sha256'] != review['merged_pptx_sha256']:
                raise ValueError('current merged bytes changed during publication')
            seal_merged_deck(temp,order,inputs,output)
            seal_validated_deck(temp,'PASS')
    except Exception:
        if created:
            output.unlink(missing_ok=True)
        raise
    return {'status':'PASS','path':str(output),'slides':len(order),'deck_order':order,
            'merged_pptx_sha256':state['merged_deck']['merged_pptx_sha256'],
            **({'accepted_limitations':limitations} if limitations else {})}


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action',required=True)
    build = sub.add_parser('prepare')
    build.add_argument('--state',required=True)
    build.add_argument('--work-dir',required=True)
    build.add_argument('--office-host',choices=('auto','powerpoint','wps'),default='auto')
    deliver = sub.add_parser('publish')
    deliver.add_argument('--state',required=True)
    deliver.add_argument('--validation-report',required=True)
    deliver.add_argument('--output',required=True)
    recovery = sub.add_parser('recover-review')
    recovery.add_argument('--state',required=True)
    args = parser.parse_args()
    try:
        if args.action == 'prepare':
            result = prepare(args.state,args.work_dir,office_host=args.office_host)
        elif args.action == 'recover-review':
            result = recover_review(args.state)
        else:
            result = publish(args.state,args.validation_report,args.output)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {'status':'FAIL','code':'DECK_LEVEL_VALIDATION_FAILED' if args.action == 'publish' else 'DECK_MERGE_INTEGRITY_FAILED','details':[str(exc)]}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 1 if result['status']=='FAIL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
