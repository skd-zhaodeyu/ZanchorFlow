"""Actual local PowerPoint diagnostics. Never assigns semantic or visual PASS."""
import argparse,hashlib,json,time
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def audit(pptx,work,width=1600,image_names=()):
 import pythoncom
 import win32com.client
 pptx=Path(pptx).resolve();work=Path(work).resolve()
 if work.exists():raise ValueError('audit directory exists; preserve old evidence')
 before=sha(pptx);work.mkdir(parents=True);pythoncom.CoInitialize();app=None;pres=None;reopened=None
 report={'source':str(pptx),'source_sha256':before,'renderer':'Microsoft PowerPoint COM','visual_judgment':'REQUIRED','text_bounds':[],'edit_checks':[]}
 try:
  app=win32com.client.DispatchEx('PowerPoint.Application')
  pres=app.Presentations.Open(str(pptx),False,False,False)
  if pres.Slides.Count!=1:raise ValueError('expected one-page build')
  slide=pres.Slides(1);height=round(width*pres.PageSetup.SlideHeight/pres.PageSetup.SlideWidth)
  preview=work/'preview.png';slide.Export(str(preview),'PNG',width,height)
  edits=[];seen=set()
  for shape in slide.Shapes:
   name=str(shape.Name)
   if shape.HasTable:
    table=shape.Table
    for ri in range(1,table.Rows.Count+1):
     for ci in range(1,table.Columns.Count+1):
      cell=table.Cell(ri,ci).Shape
      if cell.HasTextFrame and cell.TextFrame.HasText:
       report['text_bounds'].append(text_bounds(cell,name+':'+str(ri)+':'+str(ci)))
    if 'table' not in seen:
     cell=table.Cell(1,1).Shape;original=cell.TextFrame.TextRange.Text;value=original+' [edit]';cell.TextFrame.TextRange.Text=value
     edits.append({'shape':name,'shape_id':int(shape.Id),'kind':'table','cell':[1,1],'expected':value});seen.add('table')
   elif shape.HasTextFrame and shape.TextFrame.HasText:
    report['text_bounds'].append(text_bounds(shape,name))
    if 'text' not in seen:
     value=shape.TextFrame.TextRange.Text+' [edit]';shape.TextFrame.TextRange.Text=value
     edits.append({'shape':name,'shape_id':int(shape.Id),'kind':'text','expected':value});seen.add('text')
   elif shape.Type==13:
    if 'image' not in seen or name in image_names:
     shape.Left=shape.Left+1;edits.append({'shape':name,'shape_id':int(shape.Id),'kind':'image','expected':float(shape.Left)});seen.add('image')
   else:
    kind='path' if shape.Type==5 else 'geometry'
    if kind not in seen:
     shape.Left=shape.Left+1;shape.Line.Weight=float(shape.Line.Weight)+0.25
     node_info={}
     if kind=='path':
      node=shape.Nodes.Item(1).Points[0];shape.Nodes.SetPosition(1,float(node[0])+1,float(node[1])+1)
      node_info={'node_count':int(shape.Nodes.Count),'expected_first_node':[float(v) for v in shape.Nodes.Item(1).Points[0]]}
     edits.append({'shape':name,'shape_id':int(shape.Id),'kind':kind,'expected':float(shape.Left),'expected_line_weight':float(shape.Line.Weight),**node_info});seen.add(kind)
  edited=work/'edited-copy.pptx';pres.SaveAs(str(edited));pres.Close();pres=None
  reopened=app.Presentations.Open(str(edited),True,False,False);shapes={int(s.Id):s for s in reopened.Slides(1).Shapes}
  for edit in edits:
   shape=shapes[edit['shape_id']]
   if edit['kind']=='table':observed=shape.Table.Cell(*edit['cell']).Shape.TextFrame.TextRange.Text
   elif edit['kind']=='text':observed=shape.TextFrame.TextRange.Text
   else:observed=float(shape.Left)
   verified=observed==edit['expected'] if isinstance(observed,str) else abs(observed-edit['expected'])<0.01
   if 'expected_line_weight' in edit:verified=verified and abs(float(shape.Line.Weight)-edit['expected_line_weight'])<0.01
   if 'expected_first_node' in edit:verified=verified and all(abs(float(a)-b)<0.01 for a,b in zip(shape.Nodes.Item(1).Points[0],edit['expected_first_node']))
   report['edit_checks'].append({**edit,'observed':observed,'verified':verified})
  reopened.Slides(1).Export(str(work/'edited-preview.png'),'PNG',width,height)
  report.update(status='OFFICE_DIAGNOSTICS_COMPLETE',preview=str(preview),preview_sha256=sha(preview),edited_copy=str(edited),edited_copy_sha256=sha(edited))
 finally:
  for obj in (reopened,pres):
   if obj is not None:
    try:obj.Close()
    except Exception:pass
  if app is not None:
   try:app.Quit()
   except Exception:pass
  pythoncom.CoUninitialize()
 if sha(pptx)!=before:raise ValueError('source changed during audit')
 report['source_preserved']=True
 (work/'office-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 return report

def text_bounds(shape,name):
 frame=shape.TextFrame;ran=frame.TextRange
 available=[float(shape.Width-frame.MarginLeft-frame.MarginRight),float(shape.Height-frame.MarginTop-frame.MarginBottom)]
 measured=[float(ran.BoundWidth),float(ran.BoundHeight)]
 return {'shape':name,'text':str(ran.Text),'available_pt':available,'measured_pt':measured,'possible_overflow':any(m>a+1.0 for m,a in zip(measured,available))}

def main():
 p=argparse.ArgumentParser();p.add_argument('--pptx',required=True);p.add_argument('--work',required=True);p.add_argument('--width',type=int,default=1600);p.add_argument('--image-name',action='append',default=[]);a=p.parse_args()
 try:result=audit(a.pptx,a.work,a.width,a.image_name)
 except Exception as exc:result={'status':'OFFICE_DIAGNOSTICS_FAILED','error':str(exc),'visual_judgment':'UNVERIFIED'}
 print(json.dumps(result,ensure_ascii=False,indent=2));return int(result['status']=='OFFICE_DIAGNOSTICS_FAILED')
if __name__=='__main__':raise SystemExit(main())
