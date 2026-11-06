"""Read-only audit by actual IsUnitEnemy type, never model-name prefix."""
import collections,hashlib,json,sys,urllib.request
from pathlib import Path
import UnityPy
ROOT=Path(__file__).resolve().parents[1];PRODUCTION=Path('/home/RTD_SERVER');OUT=ROOT/'docs/resource-audit'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 enemies=json.loads((ROOT/'resources/master-data/ENEMY_UNIT_MASTER.json').read_text())['result'][0]['data_list'];units=json.loads((ROOT/'resources/master-data/UNIT_MASTER.json').read_text())['result'][0]['data_list'];by_gid={r['g_id']:r for r in units if r['g_id']>0}
 unit_types={int(line.split('\t')[1]) for line in (OUT/'loading-chain/loader-definitions.tsv').read_text().splitlines() if line.startswith('U\t')};assert unit_types=={22,24,30,31,33,37}
 targets=[r for r in enemies if r['type'] in unit_types];assert len(targets)==186
 monster=json.loads((PRODUCTION/'config/monster-recovery.json').read_text());monster_names={r['bundle'] for r in monster['bundles']};event=json.loads((PRODUCTION/'config/event-reconstruction-assets.json').read_text());event_names=set(event['bundle_sources'])|{f'ms00_book_el_0{i}.unity3d' for i in range(1,7)}
 config=json.loads((PRODUCTION/'rtd.config.json').read_text());network=config['resources'];host=network['host'];host='127.0.0.1' if host=='0.0.0.0' else '::1' if host=='::' else host
 base_url='http://'+('['+host+']' if ':' in host else host)+':'+str(network['port']);opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 def locate(name):
  p=PRODUCTION/'resources/bundles'/name
  if p.is_file():return p,'原优先目录'
  if name in monster_names:
   p=PRODUCTION/'resources/reconstructed/monsters/bundles'/name
   if p.is_file():return p,'怪物兼容层'
  if name in event_names:
   p=PRODUCTION/'resources/reconstructed/events/bundles'/name
   if p.is_file():return p,'活动补充层'
  return None,None
 filenames={f'ms00_book_el_0{e["chara_symbol"]-9 if 10<=e["chara_symbol"]<=15 else 6}.unity3d' for e in targets}
 for e in targets:
  start=((e['chara_g_id']-1)//10)*10+1;filenames.add(f'{start}-{start+9}.unity3d' if e['chara_g_id']>0 else e['model']+'.unity3d')
 bundles={}
 for name in sorted(filenames):
  path,route=locate(name);entry=dict(name=name,route=route,file_present=path is not None)
  if path is not None:
   sha=digest(path);entry['sha256']=sha;env=UnityPy.load(str(path));objects={o.path_id:o for o in env.objects};ab=next(o for o in env.objects if o.type.name=='AssetBundle').read_typetree();exports=[]
   for key,value in ab['m_Container']:
    pointer=value['asset'];pid=pointer['m_PathID'];obj=objects.get(pid)
    if pointer['m_FileID'] or obj is None:exports.append(dict(name=key,external_or_missing=True));continue
    if obj.type.name!='GameObject':continue
    tree=obj.read_typetree();components=[]
    for _,p in tree['m_Component']:
     component=objects[p['m_PathID']];ct=component.read_typetree()
     if component.type.name=='Transform':components.append(dict(type='Transform',position=ct['m_LocalPosition'],rotation=ct['m_LocalRotation'],scale=ct['m_LocalScale']))
     elif component.type.name=='Animation':components.append(dict(type='Animation',clips=[objects[p['m_PathID']].read_typetree().get('m_Name') for p in ct['m_Animations'] if p['m_PathID'] in objects]))
    exports.append(dict(name=key,game_object_name=tree['m_Name'],path_id=pid,components=components))
   entry.update(exports=exports,serialized_versions=sorted({o.assets_file.header.version for o in objects.values()}))
   try:
    with opener.open(base_url+'/Android/V1011/'+name,timeout=15) as response:body=response.read();status=response.status
    entry.update(http_status=status,http_sha256_match=hashlib.sha256(body).hexdigest()==sha)
   except Exception as error:entry.update(http_status='failed',http_error_type=type(error).__name__,http_sha256_match=False)
  bundles[name]=entry;print('Audited',name,entry.get('http_status'),flush=True)
 records=[]
 for e in targets:
  group=((e['chara_g_id']-1)//10)*10+1;filename=f'{group}-{group+9}.unity3d' if e['chara_g_id']>0 else e['model']+'.unity3d';book=f'ms00_book_el_0{e["chara_symbol"]-9 if 10<=e["chara_symbol"]<=15 else 6}.unity3d';bundle=bundles[filename]
  exports=bundle.get('exports',[]);same=[x for x in exports if x['name'].lower()==e['model'].lower()];suffixed=[x for x in exports if x['name'].lower()==(e['model']+'_e').lower()];ast=[x for x in exports if x['name'].lower()==('ast_'+e['model']).lower()]
  expected=same if e['chara_g_id']>0 else ast
  root_animation=any(any(c['type']=='Animation' for c in x.get('components',[])) for x in expected)
  unit=by_gid.get(e['chara_g_id']);records.append(dict(enemy_id=e['id'],name=e['name'],model=e['model'],type=e['type'],chara_kind=e['chara_kind'],chara_symbol=e['chara_symbol'],chara_g_id=e['chara_g_id'],group_bundle=filename,book_bundle=book,player_unit=({k:unit[k] for k in ('id','name','model','g_id','attribute','kind')} if unit else None),same_name_exports=same,enemy_suffix_exports=suffixed,monster_ast_exports=ast,group_http_verified=bundle.get('http_sha256_match',False),book_http_verified=bundles[book].get('http_sha256_match',False),expected_export_name=e['model'] if e['chara_g_id']>0 else 'ast_'+e['model'],root_animation_present=root_animation,status=('named_character_export_found' if e['chara_g_id']>0 else 'direct_character_ast_export_found') if expected and root_animation else 'missing_root_animation' if expected else 'missing_character_export'))
 result=dict(unit_types=sorted(unit_types),enemy_records=len(records),distinct_models=len({r['model'] for r in records}),distinct_non_ms_models=len({r['model'] for r in records if 'ms' not in r['model']}),bundle_count=len(bundles),http_verified=sum(b.get('http_sha256_match',False) for b in bundles.values()),statuses=dict(collections.Counter(r['status'] for r in records)),bundles=bundles,enemies=records,scope='Exports/file/HTTP/facing component evidence. Full action/effect validation is separate; no Android runtime claim.')
 (OUT/'角色型敌人加载审计.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 lines=['# 角色型敌人加载审计','','按原客户端IsUnitEnemy类型判定，不按ms前缀。',f"角色型敌人{len(records)}条、{result['distinct_models']}模型；涉及{len(bundles)}个角色/直接模型/书本包，{result['http_verified']}个生产HTTP哈希匹配。",'','|敌人ID/名称|原模型|角色组/直接包|书本|角色导出|玩家角色|','|---|---|---|---|---|']
 for r in records:lines.append('|'+ '|'.join(str(v).replace('|','／') for v in [str(r['enemy_id'])+' '+r['name'],r['model'],r['group_bundle'],r['book_bundle'],r['status'],r['player_unit']['name'] if r['player_unit'] else '原gid为0，须直接模型路径'])+'|')
 lines+=['','原ChangeUnitEnemy：gid>0取组包内原名，gid=0取独立包内ast_原名；_e后缀不作为替代判定。根Animation用于AddClip(toBattle)。全部命中不代表已验收方向和全动作；JSON保留导出根旋转、缩放、Animation证据。gid=0不关联玩家UNIT_MASTER的占位gid=0记录。']
 (OUT/'角色型敌人加载审计.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('bundles','enemies')},ensure_ascii=False))
if __name__=='__main__':main()
