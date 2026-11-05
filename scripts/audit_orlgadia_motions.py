import json,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import UnityPy
from prepare_monster_recovery import ROOT,WS,APK,hierarchy_paths
catalog=json.loads((ROOT/'docs/resource-audit/loading-chain/catalog.json').read_text());names={'org_wait_swd_01','org_atk_swd_01','ms03_org_run_01','el_boss_tob','el_boss_tob_6'};clips={}
with zipfile.ZipFile(APK) as z:
 for o in catalog['objects'].values():
  if o['type']!='AnimationClip' or o['name'] not in names:continue
  origins=catalog['sources'][catalog['files'][o['file']]['source']]['origins'];origin=next((s for s in origins if str(APK.relative_to(WS))+':' in s['path']),None)
  if not origin:continue
  env=UnityPy.load(z.read(origin['path'].split(':',1)[1]));t=next(v for v in env.objects if v.path_id==o['path_id']).read_typetree();clips[o['name']]=sorted({c['path'] for k in ('m_RotationCurves','m_PositionCurves','m_ScaleCurves','m_FloatCurves') for c in t[k]})
p=ROOT/'resources/reconstructed/monsters/bundles/ms03_sen_olgadia_01.unity3d';env=UnityPy.load(str(p));trees={o.path_id:(o.type.name,o.read_typetree()) for o in env.objects};subsets=hierarchy_paths(trees);rootpaths=set()
trans={i:t for i,(typ,t) in trees.items() if typ=='Transform'}
def walk(i,path):
 rootpaths.add(path)
 for c in trans[i]['m_Children']:
  j=c['m_PathID'];n=trees[trans[j]['m_GameObject']['m_PathID']][1]['m_Name'];walk(j,path+'/'+n if path else n)
root=next(i for i,t in trans.items() if trees[t['m_GameObject']['m_PathID']][1]['m_Name']=='ast_ms03_sen_olgadia_01');walk(root,'')
proof={n:dict(required=paths,missing_from_move=sorted(set(paths)-set.union(*subsets)),missing_from_root=sorted(set(paths)-rootpaths)) for n,paths in clips.items()};print(json.dumps(proof,indent=2));(ROOT/'docs/resource-audit/orlgadia-original-motion-audit.json').write_text(json.dumps(proof,indent=2)+'\n')
