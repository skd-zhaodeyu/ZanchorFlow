"""Image Layer readiness, structured limitations, and downstream review context."""
import hashlib,json
from pathlib import Path

CHECKS=('layer_isolation','background_repair','recomposite_fidelity')
READINESS=('editing_purpose','common_edit_grouping','exclusive_structure_ownership',
           'protected_background','over_split','adaptive_margin','target_count','whole_asset_granularity')
SEVERE=('input_content_mismatch','large_subject_loss','major_object_replaced_or_invented',
        'severe_semantic_change','blank_or_unrecognizable')
EXCLUSIONS=('wrong_result','task_identity','geometry','assembly')
NON_EXEMPT=('content_truth','text_truth','key_fact_error','wrong_page','wrong_source','task_identity','result_identity','lineage','missing_page','wrong_order','pptx_structure','severe_geometry','severe_semantic_error')
ACCEPTED=('LAYER_VISUAL_QA_PASS','LAYER_VISUAL_QA_ACCEPTED_WITH_LIMITATIONS')

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def text(value): return isinstance(value,str) and bool(value.strip())

def evidence_assets(items,base):
    if not isinstance(items,list) or not items: raise ValueError('limitation evidence required')
    for item in items:
        if not isinstance(item,dict) or not text(item.get('file')) or not text(item.get('sha256')):
            raise ValueError('evidence file/hash required')
        p=Path(item['file']); p=p if p.is_absolute() else Path(base)/p
        if not p.is_file() or sha(p)!=item['sha256']: raise ValueError('evidence hash mismatch')

def validate_qa(report,target_ids,base):
    checks=report.get('checks'); evidence=report.get('evidence')
    if not isinstance(checks,dict) or not isinstance(evidence,dict): raise ValueError('checks/evidence required')
    for name in CHECKS:
        if checks.get(name) not in ('PASS','MODEL_LIMITATION','FAIL') or not text(evidence.get(name)):
            raise ValueError('invalid visual check: '+name)
    limitations=report.get('limitations',[]); references=report.get('check_limitations',{})
    if not isinstance(limitations,list) or not isinstance(references,dict): raise ValueError('invalid limitations')
    ids=set()
    for limitation in limitations:
        if not isinstance(limitation,dict): raise ValueError('invalid limitation')
        lid=limitation.get('limitation_id')
        if not text(lid) or lid in ids: raise ValueError('limitation identity')
        ids.add(lid)
        for k in ('category','description','editing_impact','visual_impact'):
            if not text(limitation.get(k)): raise ValueError('limitation '+k+' required')
        affected=limitation.get('affected_target_ids')
        if not isinstance(affected,list) or len(affected)!=len(set(affected)) or any(x not in target_ids for x in affected):
            raise ValueError('limitation target identity')
        if not affected and limitation.get('affected_scope') not in ('background','page'):
            raise ValueError('background/page limitation scope required')
        if limitation['category'] in SEVERE or limitation['category'] in EXCLUSIONS or limitation['category'] in NON_EXEMPT:
            raise ValueError('severe/identity error cannot be a limitation')
        evidence_assets(limitation.get('evidence'),base)
    used=set()
    for name in CHECKS:
        if checks[name]=='MODEL_LIMITATION':
            refs=references.get(name)
            if not isinstance(refs,list) or not refs or any(x not in ids for x in refs): raise ValueError('check limitation references required')
            used.update(refs)
    if used!=ids: raise ValueError('unreferenced limitation')
    if 'FAIL' in checks.values(): status='LAYER_VISUAL_QA_FAILED'
    elif 'MODEL_LIMITATION' in checks.values(): status='LAYER_VISUAL_QA_ACCEPTED_WITH_LIMITATIONS'
    else: status='LAYER_VISUAL_QA_PASS'
    return status,limitations

def validate_context(review,expected):
    """Context is provenance, not a waiver of a FAIL or a content/identity gate."""
    if not expected: return
    if review.get('accepted_limitations')!=expected: raise ValueError('accepted limitations context missing/stale')
    matches=review.get('limitation_matches')
    if not isinstance(matches,list): raise ValueError('limitation matching reasons required')
    deck=any('page_id' in x for x in expected)
    def identity(x): return (x.get('page_id'),x.get('limitation_id')) if deck else x.get('limitation_id')
    expected_ids={identity(x) for x in expected}; actual=set()
    for m in matches:
        if not isinstance(m,dict) or identity(m) not in expected_ids or not text(m.get('reason')):
            raise ValueError('invalid limitation match')
        if m.get('unchanged_extent') is not True or m.get('claimed_capability_preserved') is not True:
            raise ValueError('limitation expanded or capability changed: reclassify and review')
        actual.add(identity(m))
    if actual!=expected_ids: raise ValueError('all accepted limitations need review')
