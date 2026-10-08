"""Reconstruct the pinned inherited docs by removing only authorized refinements.
Moved runtime blocks are checked against their ORIGINAL SKILL payload hashes.
No frozen original expectation is replaced with a candidate-derived hash.
"""
import hashlib,re
MIGRATED_BLOCKS = {'references/01_PPT内容架构与大纲生成协议_v1.2.md': {'Runtime dispatch: Outline review and reply': '608aae91318e49f26dabb651c0545f6c098f568fbd737ce248d1388182cc3b32'}, 'references/02_Stage1至Stage2语义接口协议_v1.0.md': {'Runtime dispatch: approved Stage 2 entry': '23d42626ebb61a79895b022f764948fe4467efd1722fe2ba92f8a25835eb2800'}, 'references/03_PPT视觉探索与Anchor延续协议_v2.12.md': {'Runtime dispatch: qualified Anchor choice': '97047bc65d8020e7f3385dc4c6713516214d39c3bbb3418ed3c1af4c9f62b794'}, 'references/04_页面二维生成前置约束与渲染协议_v2.9.md': {'Runtime dispatch: Candidate review, formal display and handoff': 'de2e1d77e33e6dca1d7913117ad87261b47ad2438d8e2e8749cc59c78cd67a16'}, 'references/07_Stage3_文字处理_消字与复原规范_v1.5.md': {'Runtime dispatch: Text Plan and formal Text-Clean display': 'ed7c6801f03f7beccb9e2aa50f9aac8de86d865990d0173b36e58e316bc0037d', 'Runtime dispatch: reconstruction branch selection': '261e9572fdcc1104ca3c9b64c8e26e41cc9227865c274862ea8f96ed730d6ff4'}, 'references/06_Canva_Magic_Layers可编辑PPT重建协议_v2.4.md': {'Runtime dispatch: Magic acquisition and restoration boundaries': '18eadf26a11a076b2574f790a21c01ec17fff2158b5300a859c25e235839501e'}, 'references/08_Image_Layer_Model可编辑PPT重建协议_v1.1.md': {'Runtime dispatch: Image Layer onboarding, QA and retries': 'e6e61423ec40b14002a7c0fd2f8defd818f169a6124592ccb25a1e9ddc90696e'}, 'docs/codex-canva-bridge.md': {'Runtime dispatch: provenance and final assembly': '9c97fd73cb42cef5e42f83ff7a6511dd019dc7cfabd9f1f438f06afc00e4b3e6'}}
PINNED_RUNTIME_FILES = {'scripts/acquisition_request.py': '5696a4c475ea7796c24b0db9c562ef5f54b4e44f679f86755b4d4d79fa5ac949', 'scripts/assemble_deck.py': '9d557fe6f6e862d4bfe0459182f4bec627f1e3e1c16c20253cdd37a51023e994', 'scripts/canva_bridge.py': '99fb099a770ac3dc18607e8252eefc4d958c8a829cc7e7b33f55e68875fc3422', 'scripts/canva_pptx_finalize.ps1': 'c05cbcfb20a9b7144e5a0310e8e84eae5ec5ab2cccd946d198bc27a8ff808107', 'scripts/host_acquisition.py': 'a5374798c7e176f14be7cf132b345c1e9a03cd17e1b2025f37cd88173eb77a6f', 'scripts/layer_bridge.py': 'd79de7a2a3cabdad9150b131274afe2165467a1aa6f8736c54bdd278bdf17639', 'scripts/layer_build_pptx.py': '47668f8b423ec8d8f2215d6c0a48f588ffb11166deb6ee2a04e73f225c659132', 'scripts/layer_geometry.py': 'bca60be7be50e4d62b7c0dd571f928e29b42a11c8a088b0ef09c38a10501ae3d', 'scripts/layer_geometry_verify.py': '8331242ca29dcbb4bc45d9bcfb25b439cec0c09b9a4b29f09f2d97e4d459c756', 'scripts/layer_package.py': '1b16a4480e51ce03d865e795f645c74d30b901ae870ff60e63ad3b087e957cf1', 'scripts/layer_policy.py': '9a5f35e44de84147d9424d63d81352e1c11fd0661b66a1dcf4bd3a8366efc904', 'scripts/layer_provider_360.py': '94e2283a6d1465a02381139d7d9cd1de8bcd4f93364e3aa37f9cf05d6beaa658', 'scripts/layer_review_boxes.py': '55fb595e12f8634c944c1e0ed15d19500fafb7cb92fbe53eb1f7815abe3ab060', 'scripts/layer_validate_bundle.py': 'f17ac3a44b9ec39609108ba18e4704b107bacf47fcbc34821216f81c702bc9d7', 'scripts/merge_pptx.py': 'e20887218fd4791bbdee14e0dc4751bb23498f75ceacd062a369862bdc7e05e7', 'scripts/package_skill.py': '566aa5ee56dbaea0a69e78efcd9399d5afcf1c23262c7020706ff2bec785c037', 'scripts/preflight.py': '4fdebf04442adc6b8f0fca611b59ca24ef1a6d50a439eb109e5ff1a980741cc6', 'scripts/reconstruction_router.py': '85c0a7e8c1d0832f42af50f99e5e3c5f93b54e2928822f68d000732142d3c04a', 'scripts/runtime.py': 'a81f6e5acca73bffbca7c87bf0976e55cd5e9bcc191cfe6c7a532e620b032d83'}

ANCHOR_LINK='Before generating or reviewing Anchor images, read Reference 04 Runtime dispatch: Candidate review, formal display and handoff for the shared qualification contract.'
HANDOFF_LINK='For the formal display and approved-render/Truth reconciliation prerequisite, read Reference 04 Runtime dispatch: Candidate review, formal display and handoff. Do not enter Stage 3 until its current visual approval and handoff are complete.'
CLASSIFY='非关键英文字形不得仅因特殊字体或图标外观被登记为批准图形；确认属于普通文字时，按既有内容规则分配恢复或丢弃，仍须满足图形字标和高影响区域的原保护条件。'
ACCEPT='消字阶段误作图形保留、随后被 Magic Layers 识别为普通文本的非关键装饰性英文字形，若不属于冻结清单中显式批准的图形资产或 Graphic Typography，且可按 §9.2 在当前 PPTX 内安全清理并按现有内容规则处理，则继续文字恢复，不因此重送 Magic Layers。'
LOCAL='§8.1 的非关键英文字形仅沿用此局部处理路径。合法文字按当前 Final Content Truth / Manifest 恢复，错误或额外文字按原规则丢弃；混合图文对象、关键 Logo、图形字标、身份不明对象不能套用该例外。Codex 自动清理仅删除现有辅助函数已验证的纯文本框，不扩大删除权限。'
FROZEN_CONFLICT='已冻结清单若将误分类字符登记为批准图形，应报告清单冲突并保留当前文件；不得自动改清单、删除对象或重送 Magic。本轮不增加旧清单迁移机制。'
CLEANUP_RECORD='凡执行本地文字清理，记录原下载 SHA-256、实际删除的对象 ID 和处理依据，保存既有 `canvas_mapping` 验收记录，原容差路径亦适用。封页从原下载复算合法清理和映射后核对所有保留对象；不得用清理后文件重新定义基准。'
HISTORY_NOTE='The following paragraph records inherited baseline history, not a new release identifier or the complete current scope. Current revision scope and timestamp are in manifest.yaml; actual verification and unverified branches are recorded in the delivered validation report.'
ADDED_CLEANUP=' Safe local text-only cleanup must carry the bound download hash, removed shape IDs and actual evidence in the existing mapping report, including unchanged_objects mode. Frozen protected-graphic classification is not permission to delete or rewrite the plan.'
NEW_EXPLANATION='Reload the ORIGINAL bound download independently of the edited deck. With a declared cleanup/mapping, recompute the expected retained objects using the existing verifier; without that report, the strict original-object comparison permits neither deletion nor geometric change. Do not replace the source baseline with an edited file. Load canvas_mapping_review from the actual four-gate review canvas_mapping object and approved_canvas/current_text_clean_fingerprint from the current bound state. These checks do not replace Content Truth, font fit or visual review:'
OLD_EXPLANATION='Then reload the ORIGINAL bound download, independently of the edited in-memory deck, and the saved restoration. Original object order/IDs/subtrees must match exactly; this assertion does not replace native-text truth, font fit or visual review:'
OLD_CODE="""from pptx import Presentation
from lxml import etree
original = Presentation(source_pptx)
restored = Presentation(restored_pptx)
original_shape_xml = [(shape.shape_id, etree.tostring(shape._element))
                      for shape in original.slides[0].shapes]
kept = list(restored.slides[0].shapes)[:len(original_shape_xml)]
assert [(shape.shape_id, etree.tostring(shape._element)) for shape in kept] == original_shape_xml"""
NEW_CODE="""from pptx import Presentation
from lxml import etree
from canva_bridge import verify_canvas_mapping
mapping_review = globals().get('canvas_mapping_review')
if mapping_review is not None:
    verify_canvas_mapping(source_pptx, restored_pptx, approved_canvas,
                          mapping_review, current_text_clean_fingerprint)
else:
    original = Presentation(source_pptx)
    restored = Presentation(restored_pptx)
    original_shape_xml = [(shape.shape_id, etree.tostring(shape._element))
                          for shape in original.slides[0].shapes]
    kept = list(restored.slides[0].shapes)[:len(original_shape_xml)]
    assert [(shape.shape_id, etree.tostring(shape._element)) for shape in kept] == original_shape_xml"""

def remove_once(text,fragment):
    assert text.count(fragment)==1, fragment[:90]
    return text.replace(fragment,'',1)

def inherited_doc(rel,text):
    from title_scope import normalize_doc as normalize_title_doc
    text=normalize_title_doc(rel,text)
    from publish_scope import normalize_doc
    text=normalize_doc(rel,text)
    if rel.startswith('references/03_'):
        text=remove_once(text,'\n'+ANCHOR_LINK+'\n')
    if rel.startswith('references/05_'):
        text=remove_once(text,'\n'+HANDOFF_LINK+'\n')
    expected=MIGRATED_BLOCKS.get(rel,{})
    observed=re.findall(r'(?m)^## (Runtime dispatch:.*)$',text)
    assert len(observed)==len(expected) and set(observed)==set(expected), rel
    for heading,digest in expected.items():
        pattern=r'(?ms)^## '+re.escape(heading)+r'\n\n(.*?)(?=^## Runtime dispatch:|\Z)'
        match=re.search(pattern,text);assert match,heading
        assert hashlib.sha256(match.group(1).strip().encode()).hexdigest()==digest,heading
    if expected:
        text=text[:text.index('\n\n## Runtime dispatch:')].rstrip()+'\n'
    if rel.startswith('references/06_'):
        for fragment in (ACCEPT,LOCAL,FROZEN_CONFLICT,CLEANUP_RECORD):text=remove_once(text,fragment+'\n\n')
    if rel.startswith('references/07_'):
        text=remove_once(text,CLASSIFY+'\n\n')
    if rel=='docs/codex-canva-bridge.md':
        text=remove_once(text,'\n'+HISTORY_NOTE+'\n')
        start=text.index('### 3.9 Compact calling contracts');end=text.index('## 4. Final ordered assembly')
        moved=text[text.index('### 3.10 Readonly neutrality'):end].rstrip()+'\n'
        text=text[:start]+text[end:]
        moved=moved.replace('### 3.10 Readonly neutrality','### Readonly neutrality',1)
        moved=remove_once(moved,ADDED_CLEANUP)
        moved=moved.replace(NEW_EXPLANATION,OLD_EXPLANATION,1)
        moved=moved.replace(NEW_CODE,OLD_CODE,1)
        text=text.rstrip()+'\n\n'+moved
    return text
