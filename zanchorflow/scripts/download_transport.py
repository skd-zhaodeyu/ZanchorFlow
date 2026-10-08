"""Portable Canva export GET. Signed URLs stay in stdin/memory; no browser or API calls."""
import argparse
import io
import contextvars
import contextlib
import functools
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')

def validate_url(url, design_id):
    from download_evidence import recovery_url
    return recovery_url(url, design_id)

_validation_context=contextvars.ContextVar('download_byte_validation',default=None)

@contextlib.contextmanager
def validation_session():
    """Operation-local cache indexed by actual bytes; no mtime/path PASS cache."""
    existing=_validation_context.get()
    if existing is not None:
        yield existing;return
    cache={'results':{},'reads':0,'parses':0,'hits':0}
    token=_validation_context.set(cache)
    try:yield cache
    finally:_validation_context.reset(token)

def validation_operation(function):
    @functools.wraps(function)
    def run(*args,**kwargs):
        with validation_session():return function(*args,**kwargs)
    return run

def validate_pptx_bytes(data,expected_pages=1):
    if not isinstance(expected_pages,int) or isinstance(expected_pages,bool) or expected_pages<1:
        raise ValueError('positive expected page count required')
    if not data:raise ValueError('empty PPTX')
    digest=hashlib.sha256(data).hexdigest()
    context=_validation_context.get();cache_key=(digest,len(data),expected_pages)
    if context is not None and cache_key in context['results']:
        context['hits']+=1;return dict(context['results'][cache_key])
    if context is not None:context['parses']+=1
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names=archive.namelist()
        required={'[Content_Types].xml','_rels/.rels','ppt/presentation.xml','ppt/_rels/presentation.xml.rels'}
        if len(names)!=len(set(names)) or not required.issubset(names) or archive.testzip():
            raise ValueError('invalid PPTX package')
        import xml.etree.ElementTree as ET
        presentation=ET.fromstring(archive.read('ppt/presentation.xml'))
        ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
            'r':'http://schemas.openxmlformats.org/package/2006/relationships'}
        ids=presentation.findall('p:sldIdLst/p:sldId',ns)
        rels=ET.fromstring(archive.read('ppt/_rels/presentation.xml.rels'))
        mapping={x.attrib.get('Id'):x for x in rels}
        slides=[x for x in names if re.fullmatch(r'ppt/slides/slide[0-9]+\.xml',x)]
        if len(ids)!=expected_pages or len(slides)!=expected_pages:
            raise ValueError('PPTX page count mismatch')
        import posixpath
        targets=[]
        for item in ids:
            key=item.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            rel=mapping.get(key)
            if rel is None or rel.attrib.get('TargetMode')=='External' or not rel.attrib.get('Type','').endswith('/slide'):
                raise ValueError('missing slide relationship')
            target=rel.attrib.get('Target','')
            part=posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'ppt/'+target)
            if part not in slides or part in targets:raise ValueError('invalid slide target')
            targets.append(part)
        for part in slides:ET.fromstring(archive.read(part))

    result={'bytes':len(data),'sha256':digest,'slide_count':expected_pages,'zip_integrity':'PASS'}
    if context is not None:context['results'][cache_key]=dict(result)
    return result

def validate_pptx(path,expected_pages=1):
    data=Path(path).read_bytes()
    context=_validation_context.get()
    if context is not None:context['reads']+=1
    try:return validate_pptx_bytes(data,expected_pages)
    except __import__('xml.etree.ElementTree',fromlist=['ParseError']).ParseError as error:
        raise ValueError('invalid PPTX XML') from error

class Redirect(urllib.request.HTTPRedirectHandler):
    def __init__(self,design_id,events):
        self.design_id=design_id;self.events=events
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        source=validate_url(newurl,self.design_id)
        self.events.append({'status':code,'source':source})
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def download(url,design_id,work_dir,expected_pages=1,timeout=30):
    """One actual GET attempt. Never retries invisibly, overwrites, or logs signed URLs."""
    if not 0<timeout<=600:raise ValueError('network timeout must be 0..600 seconds')
    source=validate_url(url,design_id)
    work=Path(work_dir).resolve();work.mkdir(parents=True,exist_ok=True)
    token=uuid.uuid4().hex
    temporary=work/('download-'+token+'.part')
    target=work/('download-'+token+'.pptx')
    receipt={'method':'direct','design_id':design_id,'source':source,
             'request_id':token,'started_at_utc':now(),'get_count':1,'redirects':[]}
    started=time.monotonic()
    try:
        opener=urllib.request.build_opener(Redirect(design_id,receipt['redirects']))
        with opener.open(url,timeout=timeout) as response,temporary.open('xb') as stream:
            final=validate_url(response.url,design_id)
            if response.status!=200:raise ValueError('unexpected response status')
            length=response.headers.get('Content-Length')
            if length is not None and (not length.isdigit() or int(length)<=0):
                raise ValueError('invalid Content-Length')
            receipt.update(status_code=response.status,final_source=final,
                content_length=int(length) if length is not None else None,
                headers_seconds=time.monotonic()-started)
            digest=hashlib.sha256();received=0
            while True:
                block=response.read(65536)
                if not block:break
                stream.write(block);digest.update(block);received+=len(block)
            stream.flush();os.fsync(stream.fileno())
        receipt.update(received_bytes=received,stream_sha256=digest.hexdigest(),
                       transfer_seconds=time.monotonic()-started)
        if receipt['content_length'] is not None and received!=receipt['content_length']:
            raise ValueError('incomplete response')
        checked=validate_pptx(temporary,expected_pages)
        if checked['sha256']!=receipt['stream_sha256'] or checked['bytes']!=received:
            raise ValueError('stream/file mismatch')
        # Unique name owned by this request; never replace an existing deliverable.
        if target.exists():raise ValueError('owned target unexpectedly exists')
        os.replace(temporary,target)
        receipt.update(result='PASS',path=str(target),**checked,
            completed_at_utc=now(),completion_seconds=time.monotonic()-started)
    except Exception as error:
        receipt.update(result='FAIL',error=type(error).__name__,
                       status_code=getattr(error,'code',receipt.get('status_code')),
                       completed_at_utc=now(),completion_seconds=time.monotonic()-started)
        if temporary.exists():receipt['partial_path']=str(temporary)
    return receipt

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--design-id',required=True);parser.add_argument('--work-dir',required=True)
    parser.add_argument('--expected-pages',type=int,default=1)
    parser.add_argument('--timeout',type=float,default=30)
    args=parser.parse_args()
    try:
        receipt=download(sys.stdin.readline().strip(),args.design_id,args.work_dir,args.expected_pages,args.timeout)
        from download_evidence import write_once
        ref=write_once(Path(args.work_dir)/('receipt-'+receipt['request_id']+'.json'),receipt)
        print(json.dumps({'status':receipt['result'],'receipt':ref,'path':receipt.get('path'),'error':receipt.get('error')}))
        return 0 if receipt['result']=='PASS' else 1
    except (ValueError,OSError):
        print(json.dumps({'status':'DIRECT_UNAVAILABLE','action':'USE_BROWSER_FALLBACK'}));return 1

if __name__=='__main__':sys.exit(main())
