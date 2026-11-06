import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
class SquirrelTests(unittest.TestCase):
 def test_levels_and_shadow_alpha(self):
  from prepare_squirrel_recovery import visual_scale, shadow_image
  from PIL import Image
  self.assertEqual([visual_scale('ms01_squ_lv'+str(i)) for i in (2,3,4)],[1.3,1.6,1.9])
  im=Image.new('RGBA',(1,1),(200,100,50,73));result=shadow_image(im)
  self.assertEqual(result.getpixel((0,0))[3],73)
  self.assertLess(max(result.getpixel((0,0))[:3]),200)
 def test_built_bundles_closed_scaled_and_shadow_bound(self):
  import UnityPy,json
  from prepare_monster_recovery import pointers
  from prepare_squirrel_recovery import visual_scale
  root=Path(__file__).resolve().parents[1];out=root/'resources/reconstructed/squirrel-recovery'
  rows=json.loads((out/'validation.json').read_text());self.assertEqual(len(rows),7)
  identities=set()
  for row in rows:
   env=UnityPy.load(str(out/'bundles'/row['bundle']));obj={o.path_id:o for o in env.objects};abobj=next(o for o in env.objects if o.type.name=='AssetBundle');ab=abobj.read_typetree()
   self.assertNotIn(row['internal_file'],identities);identities.add(row['internal_file'])
   union=set()
   for name,entry in ab['m_Container']:
    seen=set();todo=[entry['asset']['m_PathID']]
    while todo:
     i=todo.pop()
     if i in seen:continue
     seen.add(i)
     for p in pointers(obj[i].read_typetree()):
      self.assertEqual(p['m_FileID'],0)
      if p['m_PathID']:todo.append(p['m_PathID'])
    actual={p['m_PathID'] for p in ab['m_PreloadTable'][entry['preloadIndex']:entry['preloadIndex']+entry['preloadSize']]}
    self.assertEqual(actual,seen);union|=seen
   self.assertEqual(set(obj),union|{abobj.path_id})
   self.assertEqual({o.read_typetree()['m_IsActive'] for o in env.objects if o.type.name=='GameObject'},{0})
   prefab=next(o for o in env.objects if o.type.name=='GameObject' and o.read_typetree()['m_Name']=='ast_'+row['model'])
   transform=next(obj[p['m_PathID']] for _,p in prefab.read_typetree()['m_Component'] if obj[p['m_PathID']].type.name=='Transform')
   scale=transform.read_typetree()['m_LocalScale']
   self.assertTrue(all(abs(scale[k]-v*visual_scale(row['model']))<1e-5 for k,v in {'x':1.,'y':1.,'z':.01}.items()))
   if '_sh_' in row['model']:
    for o in env.objects:
     if o.type.name=='Material':
      texture=next(v['m_Texture'] for k,v in o.read_typetree()['m_SavedProperties']['m_TexEnvs'] if k['name']=='_MainTex')
      self.assertEqual(obj[texture['m_PathID']].read_typetree()['m_Name'],row['model'])
 def test_effective_initial_quest_only_visual_fields_change(self):
  import copy,os
  from unittest.mock import patch
  from rtd.masters.catalog import load_catalog
  from rtd.policies.monster_recovery import apply_monster_recovery
  raw,levels=load_catalog();masters=copy.deepcopy(raw)
  # Reconstruction supplies this missing map; reference enumeration requires its presence.
  levels={**levels,20809:{"reconstructed":True}}
  original={x['id']:x for x in raw[20]['data_list']}
  for row in masters[20]['data_list']:
   if row['model'].startswith('ms01_squ_lv2'):row.update(model='ms02_four_un_01_zako',texture='na')
  before=copy.deepcopy(masters)
  with patch.dict(os.environ,{'RTD_MONSTER_RECOVERY':'1'}):report=apply_monster_recovery(masters,levels,{20809})
  by_id={x['id']:x for x in masters[20]['data_list']}
  self.assertEqual(by_id[10111],original[10111])
  self.assertEqual(by_id[10101],original[10101])
  self.assertEqual(by_id[10110],next(x for x in before[20]['data_list'] if x['id']==10110))
  for old in before[20]['data_list']:
   self.assertEqual({k:v for k,v in old.items() if k not in ('model','texture')},{k:v for k,v in by_id[old['id']].items() if k not in ('model','texture')})
  for k in before:
   if k!=20:self.assertEqual(masters[k],before[k])
