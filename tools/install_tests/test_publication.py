from pathlib import Path
import importlib.util
import pytest
ROOT=Path(__file__).resolve().parents[2]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
def test_publication_readme_still_rejects_unregistered_changes():
    scope=load('install_scope')
    raw=(ROOT/'README.md').read_bytes()
    assert scope.restore_readme(raw)
    with pytest.raises(AssertionError):scope.restore_readme(raw+b'unregistered')
    spec=importlib.util.spec_from_file_location('publication_v1',ROOT/'zanchorflow/tests/v1_scope.py')
    v1=importlib.util.module_from_spec(spec);spec.loader.exec_module(v1)
    assert v1.restore_bytes('README.md',raw)
    with pytest.raises(AssertionError):v1.restore_bytes('README.md',raw+b'unregistered')

def test_source_includes_current_public_assets_and_checksums():
    paths={p.relative_to(ROOT).as_posix() for p in load('build').full_source_files()}
    assert 'docs/assets/support-wechat.png' in paths
    assert 'examples/image-layer/presentation.pptx.sha256' in paths
    assert 'examples/page-generation/pages/page-10.png' in paths
    assert 'tools/publication_scope.json' in paths
