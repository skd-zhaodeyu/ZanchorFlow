"""Validate Image Layer source-pixel plans and optionally render a numbered overlay."""
import argparse
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

MAX_FOREGROUNDS = 6


def validate_plan(plan, width, height):
    if not isinstance(width,int) or not isinstance(height,int) or width<=0 or height<=0:
        raise ValueError('source canvas must be positive integers')
    if min(width,height) < 128:
        raise ValueError('source image shortest side must be at least 128 px')
    if max(width,height)/min(width,height) > 5.0:
        raise ValueError('source image aspect ratio must not exceed 5.0')
    if not isinstance(plan,dict) or plan.get('schema_version') != 1:
        raise ValueError('layer plan schema_version must be 1')
    targets=plan.get('targets')
    limit=plan.get('max_foregrounds',MAX_FOREGROUNDS)
    if not isinstance(targets,list) or not isinstance(limit,int) or limit<1 or limit>MAX_FOREGROUNDS:
        raise ValueError('targets must be a list and max_foregrounds in 1..6')
    if not (1 <= len(targets) <= min(limit,MAX_FOREGROUNDS)):
        raise ValueError('selected boxes count must be in 1..6')
    ids=set(); scale=1024/max(width,height)
    for target in targets:
        target_id=target.get('id')
        if not isinstance(target_id,str) or not target_id or target_id in ids:
            raise ValueError('target ids must be unique nonempty strings')
        ids.add(target_id)
        box=target.get('bbox')
        if not isinstance(box,list) or len(box)!=4 or not all(isinstance(v,int) for v in box):
            raise ValueError(f'{target_id}: bbox must contain four integer source-pixel coordinates')
        x1,y1,x2,y2=box
        if not (0<=x1<x2<=width and 0<=y1<y2<=height):
            raise ValueError(f'{target_id}: bbox is outside the {width}x{height} source canvas')
        if min((x2-x1)*scale,(y2-y1)*scale) < 8:
            raise ValueError(f'{target_id}: scaled box short side must be at least 8 px')
    return targets


def draw_overlay(image_path, plan_path, output_path):
    image=Image.open(image_path).convert('RGB')
    plan=json.loads(Path(plan_path).read_text(encoding='utf-8'))
    targets=validate_plan(plan,*image.size)
    draw=ImageDraw.Draw(image)
    colors=('#e53935','#1565c0','#00897b','#8e24aa','#ef6c00','#6d4c41')
    for index,target in enumerate(targets,1):
        color=colors[(index-1)%len(colors)]; box=target['bbox']
        draw.rectangle(box,outline=color,width=max(2,round(min(image.size)/400)))
        label=f"{index}. {target.get('label',target['id'])}"
        x,y=box[:2]; tb=draw.textbbox((x,y),label); th=tb[3]-tb[1]
        yl=max(0,y-th-5)
        draw.rectangle((x,yl,x+tb[2]-tb[0]+4,yl+th+4),fill=color)
        draw.text((x+2,yl+2),label,fill='white')
    output_path=Path(output_path); output_path.parent.mkdir(parents=True,exist_ok=True); image.save(output_path)
    return {'targets':len(targets),'width':image.width,'height':image.height,'path':str(output_path)}


def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument('--image',required=True,type=Path); parser.add_argument('--plan',required=True,type=Path); parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    try: result=draw_overlay(args.image,args.plan,args.output)
    except (ValueError,OSError,KeyError,json.JSONDecodeError) as exc:
        print(f'Error: {exc}',file=sys.stderr); return 2
    print(json.dumps(result,ensure_ascii=False)); return 0

if __name__=='__main__': raise SystemExit(main())
