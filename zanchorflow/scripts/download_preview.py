"""Read-only native PPTX preview. No source save, resizing, or global WPS Quit."""
import argparse
import gc
import json
from pathlib import Path
import canva_bridge as bridge
import download_evidence as de
import runtime

def render(source,output_dir,state_path,slide_id,office_host='auto'):
    source=Path(source).resolve();out=Path(output_dir).resolve();out.mkdir(parents=True,exist_ok=True)
    bridge.single_page(source);before=de.sha(source)
    identity=bridge.active_identity(runtime.load_runtime_state(state_path),slide_id)
    png=out/'page.png';receipt=out/'preview.json'
    if png.exists() or receipt.exists():raise ValueError('preview paths must be new')
    import win32com
    cache=out/"com-cache";cache.mkdir(exist_ok=True);win32com.__gen_path__=str(cache)
    import win32com.client
    app=None;doc=None;chosen=None;diagnostics=[]
    options=('powerpoint','wps') if office_host=='auto' else (office_host,)
    for kind in options:
        try:
            app=win32com.client.DispatchEx('PowerPoint.Application') if kind=='powerpoint' else win32com.client.Dispatch('KWPP.Application')
            chosen=kind;break
        except Exception as error:diagnostics.append({'host':kind,'error':str(error)})
    if app is None:raise ValueError('NATIVE_PREVIEW_UNAVAILABLE: '+json.dumps(diagnostics))
    owned_application=False
    if chosen=='powerpoint':
        try:owned_application=app.Presentations.Count==0
        except Exception:pass
    try:
        doc=app.Presentations.Open(str(source),True,False,False)
        if doc.Slides.Count!=1:raise ValueError('expected one preview page')
        slide=doc.Slides.Item(1)
        slide.Export(str(png),'PNG');slide=None
        if not png.is_file() or not png.stat().st_size:raise ValueError('native preview export failed')
    finally:
        try:
            if doc is not None:doc.Close()
        finally:
            doc=None
            if owned_application:app.Quit()
            app=None;gc.collect()
        if de.sha(source)!=before:raise ValueError('preview changed original source bytes')
    data={'schema_version':2,'identity':identity,'source_path':str(source),'source_sha256':before,
          'preview_path':str(png),'preview_sha256':de.sha(png),'office_host':chosen,
          'diagnostics':diagnostics,'owned_application':owned_application,'content_comparison':'PENDING'}
    de.write_once(receipt,data)
    return data

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output-dir',required=True)
    p.add_argument('--state',required=True);p.add_argument('--slide-id',required=True)
    p.add_argument('--office-host',choices=('auto','powerpoint','wps'),default='auto');a=p.parse_args()
    print(json.dumps(render(a.source,a.output_dir,a.state,a.slide_id,a.office_host),ensure_ascii=False))
