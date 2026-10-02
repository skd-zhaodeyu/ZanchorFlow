"""Readonly acquisition handoff; connector and browser calls belong to the controller."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
import canva_bridge as bridge
import runtime


def request(state_path, slide_id, lookup_path, download_target_dir):
    current=bridge.status(state_path)
    if current.get('status')!='WAIT_DOWNLOAD' or current.get('slide_id')!=slide_id:
        raise ValueError('current page must be WAIT_DOWNLOAD')
    identity=bridge.active_identity(runtime.load_runtime_state(state_path),slide_id)
    lookup=json.loads(Path(lookup_path).read_text(encoding='utf-8-sig'))
    if (not isinstance(lookup,dict) or lookup.get('schema_version')!=1
        or lookup.get('source')!='canva_connector.get_design' or lookup.get('identity')!=identity):
        raise ValueError('trusted connector lookup identity mismatch')
    response=lookup.get('response')
    design=response.get('design') if isinstance(response,dict) else None
    if not isinstance(design,dict) or design.get('id')!=identity['design_id'] or design.get('page_count')!=1:
        raise ValueError('connector must confirm current single-page design')
    urls=design.get('urls')
    url=urls.get('edit_url') if isinstance(urls,dict) else None
    if not isinstance(url,str) or not url or any(ord(c)<33 or ord(c)==127 for c in url):
        raise ValueError('official Canva edit URL required')
    parsed=urlsplit(url)
    if (parsed.scheme!='https' or parsed.hostname not in ('canva.com','www.canva.com')
        or parsed.username is not None or parsed.password is not None or parsed.port not in (None,443)):
        raise ValueError('official HTTPS Canva URL without credentials required')
    parts=parsed.path.split('/')
    direct=len(parts)>=3 and parts[1]=='design' and parts[2]==identity['design_id']
    alias=len(parts)==3 and parts[1]=='d' and bool(parts[2]) and all(c.isascii() and (c.isalnum() or c in '_-') for c in parts[2])
    if not (direct or alias):
        raise ValueError('edit URL must identify this design or its connector-returned alias')
    target=Path(download_target_dir)
    if not target.is_absolute():
        raise ValueError('absolute finalizer target directory required')
    return {'status':'WAIT_DOWNLOAD','identity':identity,'edit_url':url,
            'download_target_dir':str(target),'lookup_path':str(Path(lookup_path).resolve()),
            'lookup_sha256':bridge.sha(lookup_path),'page_count':1}


def main():
    parser=argparse.ArgumentParser()
    for flag in ('state','slide-id','lookup','download-target-dir'):
        parser.add_argument('--'+flag,required=True)
    args=parser.parse_args()
    try:
        result=request(args.state,args.slide_id,args.lookup,args.download_target_dir)
    except (ValueError,KeyError,TypeError,OSError) as error:
        print(json.dumps({'status':'BLOCKED','detail':str(error)},ensure_ascii=False))
        return 1
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
