"""Reverse only this approved revision before checking the unchanged older pins."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def data():return json.loads((ROOT/"tests/heading_refine_scope.json").read_text(encoding="utf-8"))
def restore_bytes(rel,raw):
    from office_scope import restore_repo_bytes
    text=restore_repo_bytes("zanchorflow/"+rel,raw).decode("utf-8")
    for item in reversed(data()["patches"]):
        if item["path"]==rel:
            assert text.count(item["new"])==1,(rel,"declared refinement delta changed")
            text=text.replace(item["new"],item["old"],1)
    expected=data()["baseline"].get("zanchorflow/"+rel)
    if expected:assert hashlib.sha256(text.encode("utf-8")).hexdigest()==expected,(rel,"undeclared change")
    return text.encode("utf-8")
def restore_text(rel,text):
    from office_scope import restore_repo_text
    text=restore_repo_text("zanchorflow/"+rel,text)
    for item in reversed(data()["patches"]):
        if item["path"]==rel:
            old=item["old"].replace("\r\n","\n");new=item["new"].replace("\r\n","\n")
            assert text.count(new)==1,(rel,"declared document delta changed")
            text=text.replace(new,old,1)
    return text

def identity_manifest(root,payload=None):
    """Validate the entire allowed scope, then expose legacy identity assertions."""
    import copy,yaml
    m=copy.deepcopy(payload) if payload is not None else yaml.safe_load((Path(root)/"manifest.yaml").read_text(encoding="utf-8"))
    from office_scope import normalize_manifest
    m=normalize_manifest(m)
    d=data();expected=d["baseline_revision_scope"]+d["added_revision_scope"]
    assert m["revision_scope"]==expected,"undeclared or missing revision scope"
    previous_titles=["optional_ordinary_heading_consistency","normal_heading_seed_protection","dual_package_source_build"]
    assert d["baseline_revision_scope"][7:]==previous_titles,"locked title scope differs"
    m["revision_scope"]=m["revision_scope"][:7]
    return m
