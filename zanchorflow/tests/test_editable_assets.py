import sys,json
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import editable_assets as assets
import editable_bridge as bridge
import reconstruction_router as router
from test_editable_bridge import source

def setup(tmp_path):
 state=source(tmp_path);router.choose_backend(state,'editable_path');return state

def test_failure_consumes_budget_and_prompt_cannot_reset(tmp_path):
 state=setup(tmp_path);key=assets.register_job(state,'S001',[0,0,1,1],'foreground')['job_key'];one=assets.reserve(state,key)
 with pytest.raises(ValueError,match='PENDING'):assets.reserve(state,key,'retry')
 assets.record_result(state,key,one['token'],failure='OFFLINE simulated tool failure')
 with pytest.raises(ValueError,match='FINDING'):assets.reserve(state,key)
 two=assets.reserve(state,key,'repair missing detached stroke');assets.record_result(state,key,two['token'],failure='OFFLINE failure')
 assert assets.register_job(state,'S001',[0,0,1,1],'foreground')['job_key']==key
 with pytest.raises(ValueError,match='EXHAUSTED'):assets.reserve(state,key,'changed prompt')

def test_overlapping_renamed_scope_cannot_reset_budget(tmp_path):
 state=setup(tmp_path);assets.register_job(state,'S001',[0,0,1,1],'foreground')
 with pytest.raises(ValueError,match='OVERLAPPING'):assets.register_job(state,'S001',[0,0,0.9,0.9],'foreground')
