import hashlib
from pathlib import Path

from refinement_scope import inherited_doc

ROOT = Path(__file__).resolve().parents[1]
FROZEN = {
    'scripts/canva_bridge.py': '3d35ab9a400b05a7716b9a731893b460eb61b369091cfacc408c72da616bbf43',
    'scripts/host_acquisition.py': 'bda29d1e17c5f555416b9b5a22d7b22e7ff48ae6cf878e88b9951c0f26554ef7',
    'docs/codex-canva-bridge.md': 'c64dc68a90e3340842e0440973ec2669004f4618060304ced43defa306d70e59',
    'references/05_Stage2至Stage3_Magic_Layers接口协议_v1.4.md': '9093342b1057a902407f44e71523ba30efd2305a1f05edb1ee3a0466c0d238cf',
    'references/06_Canva_Magic_Layers可编辑PPT重建协议_v2.4.md': '162e121599391a878c8d974e5b975fc64e68a028df08a05c0fb983c3f7317d1d',
    'scripts/merge_pptx.py': 'e20887218fd4791bbdee14e0dc4751bb23498f75ceacd062a369862bdc7e05e7',
    'scripts/canva_pptx_finalize.ps1': 'c05cbcfb20a9b7144e5a0310e8e84eae5ec5ab2cccd946d198bc27a8ff808107',
}

def sha(path):
    from office_scope import restore_repo_bytes
    raw=restore_repo_bytes('zanchorflow/'+path.relative_to(ROOT).as_posix(),path.read_bytes())
    return hashlib.sha256(raw).hexdigest()

AUTHORIZED_REVISION_FILES = {
    "scripts/canva_bridge.py", "scripts/host_acquisition.py",
    "docs/codex-canva-bridge.md",
    "references/06_Canva_Magic_Layers可编辑PPT重建协议_v2.4.md",
}

def test_unrevised_magic_layer_baseline_bytes_are_unchanged():
    for rel, expected in FROZEN.items():
        if rel not in AUTHORIZED_REVISION_FILES:
            actual = sha(ROOT/rel) if rel.startswith('scripts/') else hashlib.sha256(inherited_doc(rel,(ROOT/rel).read_text(encoding='utf-8')).encode()).hexdigest()
            assert actual == expected, rel


# The approved revision opens only these functions and documentation sections.
# Hashes below are computed from the ORIGINAL source, not the candidate.
import ast
import re
import json

def _canonical_ast(node):
    if isinstance(node, ast.AST):
        return {'_type':type(node).__name__, **{
            key:_canonical_ast(value) for key,value in ast.iter_fields(node)
            if not (key=='type_params' and not value)}}
    if isinstance(node,list):
        return [_canonical_ast(value) for value in node]
    if isinstance(node,bytes):
        return {'_bytes':node.hex()}
    return node

CODE_SCOPE = {'scripts/canva_bridge.py': ({'_canvas_cleanup', 'seal_page', 'map_native_text_geometry', '_canvas_plain_text', '_canvas_error', '_canvas_shapes', 'prepare_canvas_mapping', 'page_provenance', '_positive_dimension', '_apply_canvas_plan', 'verify_canvas_mapping', '_canvas_preflight', 'plan_canvas_mapping', '_canvas_resource_signature'}, 'd957e0687885d56c31a1c61ac71b85c3d86c2dcb78b58ca31a1200f8b65be094'), 'scripts/host_acquisition.py': ({'prepare', 'main', '_strategy_record'}, '1fa209e32fbc847fb4352386211ee07ad5b353f220b448d06492f90ee2da4d11')}

def test_existing_code_outside_approved_revision_is_unchanged():
    for rel, (excluded, original_hash) in CODE_SCOPE.items():
        from title_scope import normalize_runtime_bytes
        tree = ast.parse(normalize_runtime_bytes(rel, (ROOT / rel).read_bytes()).decode('utf-8'))
        nodes = [n for n in tree.body if not (isinstance(n, ast.FunctionDef) and n.name in excluded)]
        canonical = json.dumps(_canonical_ast(ast.Module(body=nodes, type_ignores=[])),sort_keys=True).encode()
        assert hashlib.sha256(canonical).hexdigest() == original_hash, rel

DOC_SCOPE = {'docs/codex-canva-bridge.md': (['(?ms)^### 3\\.1a .*?(?=^### 3\\.2 )', '(?ms)^### 3\\.8 .*?(?=^## 4\\.)'], 'f4f7f160cf687dc66422c3f123e716a6a29b46a16ca59ffa4a6c27385ddb3915'), 'references/06_Canva_Magic_Layers可编辑PPT重建协议_v2.4.md': (['(?ms)^## 9\\.1 .*?(?=^## 9\\.2 )'], '70f852361795f132f90d2c80d699d214a7240b7a582e06fa2486173f7507dfc5')}

def test_documentation_outside_approved_sections_is_unchanged():
    for rel, (patterns, original_hash) in DOC_SCOPE.items():
        text = inherited_doc(rel,(ROOT / rel).read_text(encoding='utf-8'))
        for pattern in patterns:
            text = re.sub(pattern, '', text)
        assert hashlib.sha256(text.encode()).hexdigest() == original_hash, rel
