from datetime import datetime
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]

def test_revision_uses_utc_time_and_preserves_source_compatibility_identifiers():
    from heading_refine_scope import identity_manifest
    m=identity_manifest(ROOT)
    stamp=m['updated_at_utc'];assert isinstance(stamp,str) and stamp.endswith('Z')
    assert datetime.fromisoformat(stamp.replace('Z','+00:00')).utcoffset().total_seconds()==0
    assert m['skill_name']=='zanchorflow' and m['skill_version']=='1.0'
    assert m['protocol_baseline']=='RC17'
    assert m['revision_scope']==['controlled_magic_canvas_mapping','host_dom_event_candidate_with_original_fallback',
        'noncritical_glyph_local_handling','progressive_context_loading','david_z_attribution','approved_image_target_wiring','github_distribution']
