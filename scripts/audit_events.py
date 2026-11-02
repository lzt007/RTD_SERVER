"""Print recovered event eligibility without opening or modifying a player DB."""
import json
import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from rtd.masters.catalog import load_catalog
from rtd.policies.event_content import audit_events, recovered_asset_names

masters,levels=load_catalog()
from rtd.policies.visual_recovery import apply_visual_recovery
from rtd.config import SETTINGS
import os
from rtd.policies.event_visuals import apply_event_visuals
visual=os.environ.get('RTD_VISUAL_RECOVERY','1' if SETTINGS['features']['visual_recovery'] else '0')
if visual not in ('0','1'):raise ValueError('Invalid RTD_VISUAL_RECOVERY')
substitutions=[]
if visual=='1':
    apply_visual_recovery(masters)
    substitutions=apply_event_visuals(masters,levels)
accepted,rejected=audit_events(masters,levels,recovered_asset_names())
rows=[]
for quest in masters[30]['data_list']:
    id=quest['id']
    if quest['division']!=20000:continue
    if id==20000 or 20100<=id<=20163:status='existing_layer_protocol';reasons=[]
    elif id in accepted:status='supported';reasons=[]
    else:status='excluded';reasons=rejected.get(id,['missing map'])
    if id in SETTINGS['features'].get('blocked_quests',[]):status='excluded';reasons=['blocked by configuration']
    rows.append(dict(id=id,name=quest['name'],status=status,reasons=reasons))
print(json.dumps(dict(supported=sum(r['status']=='supported' for r in rows),visual_substitutions=substitutions,quests=rows),ensure_ascii=False,indent=2))
