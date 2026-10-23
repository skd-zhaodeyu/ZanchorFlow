import sys
from pathlib import Path
import pytest
from pptx import Presentation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import merge_pptx as m
from test_office_hosts import _mock_com,_one_page


def test_cleanup_does_not_mask_primary_merge_failure(tmp_path,monkeypatch):
 src=_one_page(tmp_path/'source.pptx');out=tmp_path/'out.pptx'
 monkeypatch.setattr(m,'_merge_input_diagnostics',lambda *_:(None,[]))
 def fail(inputs,order,target,**kwargs):
  Path(target).write_bytes(b'actual diagnostic artifact')
  raise OSError('PRIMARY COM save failure')
 monkeypatch.setattr(m,'_native_merge',fail)
 def locked(_):raise PermissionError('SECONDARY file still held')
 monkeypatch.setattr(m.shutil,'rmtree',locked)
 result=m.merge([{'slide_id':'S1','path':str(src)}],['S1'],out)
 assert result['status']=='FAIL' and result['details']==['PRIMARY COM save failure']
 assert result['workspace_cleanup']['status']=='RETAINED'
 assert 'SECONDARY' in result['workspace_cleanup']['error']
 assert Path(result['workspace_cleanup']['path'],'merged.pptx').is_file()
 assert not out.exists()


def test_cleanup_normal_and_baseexception_preserved(tmp_path):
 d={}
 with pytest.raises(KeyboardInterrupt):
  with m._merge_workspace(tmp_path,d) as folder:raise KeyboardInterrupt()
 assert d['workspace_cleanup']['status']=='REMOVED' and not folder.exists()


def test_actual_operation_failure_stage_is_preserved(tmp_path,monkeypatch):
 src=_one_page(tmp_path/'source.pptx');_mock_com(monkeypatch,src,save_error=True);d={}
 with pytest.raises(OSError,match='PRIMARY save failure'):m._native_merge([{'slide_id':'S1','path':str(src)}],['S1'],tmp_path/'out.pptx',diagnostics=d)
 assert d['primary_error']['stage']=='save_candidate'
 assert d['primary_error']['message']=='PRIMARY save failure'
