"""Physical-canvas support for vendored advisory ink measurements."""
import os
from pathlib import Path

def choose_preview_font(preferred):
 candidates=[preferred,os.environ.get('ZANCHORFLOW_MEASUREMENT_FONT'),r'C:\Windows\Fonts\msyh.ttc',r'C:\Windows\Fonts\arial.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/System/Library/Fonts/STHeiti Medium.ttc']
 return next((str(p) for p in candidates if p and Path(p).is_file()),None)

def content_box_for_manifest(manifest):
 if manifest.get('content_box'):return manifest['content_box']
 source=manifest['source'];slide=manifest['slide'];sw,sh=source['width_px'],source['height_px'];tw,th=slide['width'],slide['height'];scale=min(tw/sw,th/sh)
 return {'left':(tw-sw*scale)/2,'top':(th-sh*scale)/2,'width':sw*scale,'height':sh*scale}
