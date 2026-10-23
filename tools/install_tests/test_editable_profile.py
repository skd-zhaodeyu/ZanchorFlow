"""The third backend must stay unavailable in Image-only installed profiles."""
from pathlib import Path
import subprocess,sys
import pytest
from test_install import VIEWS,write_tree

@pytest.mark.parametrize('host',['qwen','workbuddy'])
def test_image_only_profile_rejects_editable_cli_before_creating_state(tmp_path,host):
 view=tmp_path/host;write_tree(view,VIEWS[host]);state=tmp_path/'nonexistent-state.json'
 done=subprocess.run([sys.executable,'-B',str(view/'scripts/reconstruction_router.py'),'choose-backend','--state',str(state),'--backend','editable_path'],capture_output=True,text=True,encoding='utf-8')
 assert done.returncode==2 and 'invalid choice' in done.stderr
 assert not state.exists()
