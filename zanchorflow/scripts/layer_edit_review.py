"""Local hide/move evidence from a verified Layer Bundle; never calls a model."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
import layer_validate_bundle

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def previews(bundle_dir,output_dir):
    root=Path(bundle_dir).resolve();out=Path(output_dir).resolve()
    layer_validate_bundle.validate_bundle(root)
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    plan_file=root/'layer-plan.json'
    plan=json.loads(plan_file.read_text(encoding='utf-8')) if plan_file.is_file() else {'targets':[]}
    actions={x['id']:x.get('primary_edit_action',x.get('edit_action') if x.get('edit_action') in ('move','resize','hide','replace') else 'move') for x in plan.get('targets',[])}
    fingerprint={'bundle_manifest_sha256':sha(root/'manifest.json'),'plan_sha256':sha(plan_file) if plan_file.is_file() else None,
                 'assets':{x['file']:sha(root/x['file']) for x in manifest['layers']},'actions':actions,'preview_parameters':{'move_fraction':0.06,'overview_tile_width':320}}
    receipt_file=out/'editing-evidence.json'
    if receipt_file.is_file():
        previous=json.loads(receipt_file.read_text(encoding='utf-8'))
        if previous.get('fingerprint')==fingerprint:
            evidence=[previous['recomposite'],previous['overview']]
            for item in previous['targets']:
                evidence.append(item['hidden'])
                if item.get('moved'):evidence.append(item['moved'])
            if all(Path(x['file']).is_file() and sha(x['file'])==x['sha256'] for x in evidence):
                return {**previous,'reused':True}
    out.mkdir(parents=True,exist_ok=True)
    size=tuple(manifest['backend']['canvas'])
    layers=[]
    for spec in manifest['layers']:
        image=Image.open(root/spec['file']).convert('RGBA')
        x,y,w,h=spec['backend_bbox']
        if image.size!=(w,h):raise ValueError('layer asset/canvas mismatch')
        canvas=Image.new('RGBA',size,(0,0,0,0));canvas.paste(image,(x,y))
        layers.append((spec,canvas))
    def render(skip=None,move=None):
        frame=Image.new('RGBA',size,(255,255,255,255))
        for spec,image in layers:
            if spec.get('target_id')==skip and skip is not None:continue
            if move and spec.get('target_id')==move[0]:
                shifted=Image.new('RGBA',size,(0,0,0,0));shifted.paste(image,(move[1],move[2]));image=shifted
            frame=Image.alpha_composite(frame,image)
        return frame
    baseline=out/'recomposite.png'
    base_image=render();existing=root/'composite.png'
    if existing.is_file():
        with Image.open(existing) as candidate:
            equal=candidate.convert('RGBA').size==base_image.size and candidate.convert('RGBA').tobytes()==base_image.tobytes()
        if equal:
            import shutil
            shutil.copyfile(existing,baseline)
        else:base_image.save(baseline)
    else:base_image.save(baseline)
    records=[]
    for index,(spec,_) in enumerate(layers[1:],1):
        target=spec['target_id'];x,y,w,h=spec['backend_bbox']
        # Pick an inward translation; its geometry is explicit, not a score threshold.
        dx=max(1,round(size[0]*0.06));dy=max(1,round(size[1]*0.06))
        if x+w+dx>size[0]:dx=-dx
        if y+h+dy>size[1]:dy=-dy
        hidden=out/('hidden-'+str(index)+'.png');moved=out/('moved-'+str(index)+'.png')
        render(skip=target).save(hidden)
        entry={'target_id':target,'primary_edit_action':actions.get(target,'move'),
               'hidden':{'file':str(hidden),'sha256':sha(hidden),'purpose':'target_hidden_full_resolution'},'assessment':'NOT_ASSESSED'}
        if actions.get(target,'move')=='move':
            render(move=(target,dx,dy)).save(moved)
            entry.update(translation_backend_px=[dx,dy],moved={'file':str(moved),'sha256':sha(moved),'purpose':'target_moved_full_resolution'})
        records.append(entry)
    # Overview is a navigation aid; original target files remain the QA evidence.
    panels=[('recomposite',baseline)]
    for item in records:
        panels.append((item['target_id']+' hidden',Path(item['hidden']['file'])))
        if item.get('moved'):panels.append((item['target_id']+' moved',Path(item['moved']['file'])))
    from PIL import ImageDraw
    tw=320;th=round(tw*size[1]/size[0])+28
    sheet=Image.new('RGB',(tw*2,th*((len(panels)+1)//2)),'white');draw=ImageDraw.Draw(sheet)
    for index,(label,path) in enumerate(panels):
        with Image.open(path) as image:
            tile=image.convert('RGB');tile.thumbnail((tw,th-28))
            x=(index%2)*tw;y=(index//2)*th
            sheet.paste(tile,(x,y+28));draw.text((x+4,y+4),label,fill='black')
    navigation=out/'overview.png';sheet.save(navigation)
    receipt={'page_id':manifest['page_id'],'bundle_manifest_sha256':sha(root/'manifest.json'),
             'fingerprint':fingerprint,'recomposite':{'file':str(baseline),'sha256':sha(baseline)},
             'overview':{'file':str(navigation),'sha256':sha(navigation),'purpose':'navigation_only'},'targets':records,
             'note':'Evidence only. Inspect vacated regions, neighbors and connectors. Deliberate movement overlap/clipping is not a model defect; these previews never grade quality automatically.'}
    (out/'editing-evidence.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return receipt

def validate_targets(report,target_ids,base,target_actions=None):
    rows=report.get('target_edit_checks')
    if not isinstance(rows,list) or len(rows)!=len(target_ids):raise ValueError('target editing checks required')
    seen=set();failed=False
    from layer_policy import evidence_assets,text
    for row in rows:
        target=row.get('target_id')
        if target not in target_ids or target in seen:raise ValueError('editing target identity mismatch')
        seen.add(target)
        if row.get('assessment') not in ('PASS','MODEL_LIMITATION','FAIL'):raise ValueError('editing assessment required')
        for field in ('requested_action','actual_independence','background_residual','neighbor_impact','connector_behavior','explanation'):
            if not text(row.get(field)):raise ValueError('editing evidence '+field+' required')
        if type(row.get('capability_preserved')) is not bool:raise ValueError('actual edit capability required')
        if target_actions and row['requested_action']!=target_actions.get(target,'move'):raise ValueError('claimed action differs from frozen Plan')
        if row['requested_action'] not in ('move','resize','hide','replace'):raise ValueError('unsupported claimed editing action')
        for item in row.get('hidden_evidence',[])+row.get('move_evidence',[]):
            if item.get('purpose')=='navigation_only':raise ValueError('overview is not full-resolution target evidence')
        evidence_assets(row.get('hidden_evidence'),base)
        if row['requested_action']=='move':evidence_assets(row.get('move_evidence'),base)
        if row['assessment']!='FAIL' and not row['capability_preserved']:
            raise ValueError('editing goal unmet cannot be PASS/MODEL_LIMITATION')
        failed=failed or row['assessment']=='FAIL'
    return failed

def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();result=previews(a.bundle,a.output)
    print(json.dumps({'status':'EDITING_EVIDENCE_READY','path':str(Path(a.output)/'editing-evidence.json'),'targets':len(result['targets'])}))
if __name__=='__main__':main()
