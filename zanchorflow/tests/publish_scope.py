"""Approved publication deltas; inherited pins remain unchanged."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OLD_COPY='新用户当前可获得 ¥50 免费额度，最多可处理500张图片。'
NEW_COPY='请核实当前账户的免费权益、余额与价格，并在真实提交前确认费用授权。'
PROTOCOL_ADDITION='## 正式画布接线\n\n正式 Image Layer 流程统一读取当前 run 的登记 canvas。任一页包含 target_slide_width_emu / target_slide_height_emu 时，所有页面须有当前且一致的批准目标，并核对 source_width / source_height。尺寸数值不同本身不是错误：940/941 像素差异和等比例分辨率变化按既有规则继续，PPTX 使用批准物理尺寸。每轴 5 源像素门槛及 framing、裁切和既有几何证据保持。全部无显式目标时保留原一致源比例回退。\n\n首次与重复选择、新提交预留、正式打包和绑定均核对目标。失效来源或目标不删除任务、结果、锁或重试账本；已有 task 沿原身份查询，不增加提交权限。旧状态不自动迁移。\n\n正式打包使用：\n~~~powershell\npython scripts/layer_package.py --state <state.json> --slide-id <id> --source-image <current-text-clean.png> --plan <current-plan.json> --result <current-result.json> --output <new-bundle-dir>\n~~~\n--state / --slide-id 必须成对；脚本核对当前批准 Plan、来源、结果、task 与目标后写出 Bundle。独立旧调用兼容。显式尺寸标记 explicit_target，回退标记 source_aspect_fallback；标签本身不是批准证据。尺寸在生成时正确写入，不事后改 manifest；保留四 Hard Gates 和费用授权。\n\n'
def normalize_doc(rel,text):
    if rel.startswith('references/08_'):
        assert text.count(PROTOCOL_ADDITION)==1
        text=text.replace(PROTOCOL_ADDITION,'',1)
        assert text.count(NEW_COPY)==1
        text=text.replace(NEW_COPY,OLD_COPY,1)
    return text
def node_key(node):
    if isinstance(node,(ast.FunctionDef,ast.ClassDef)): return node.name
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name): return node.targets[0].id
    return ast.dump(node,include_attributes=False)
def assert_approved_runtime(rel,path,baseline_digest):
    scope=json.loads((ROOT/'tests/publish_scope.json').read_text(encoding='utf-8'))[rel]
    assert scope['baseline_sha256']==baseline_digest
    assert hashlib.sha256(path.read_bytes()).hexdigest()==scope['approved_sha256']
    observed={node_key(n):hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest() for n in ast.parse(path.read_text(encoding='utf-8')).body}
    assert set(observed)==set(scope['baseline_nodes'])|set(scope['new_nodes'])
    for key,digest in scope['baseline_nodes'].items():
        if key not in scope['allowed_changed_nodes']: assert observed[key]==digest,(rel,key)
