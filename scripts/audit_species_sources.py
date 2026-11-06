import json,collections,re,pathlib
r=pathlib.Path('/home/workspace/RTD_SERVER');old=json.load(open(r/'docs/resource-audit/独立资源重扫证据.json'));new=json.load(open(r/'docs/resource-audit/new-backup/新备份资源索引.json'));apk=json.load(open(r/'docs/resource-audit/全种族APK内置扫描.json'));raw=json.load(open(r/'resources/master-data/ENEMY_UNIT_MASTER.json'))['result'][0]['data_list'];policy=json.load(open(r/'config/monster-recovery.json'))
def family(s):
 m=re.search(r'ms\d+_[^_]+',s);return m[0] if m else 'character_or_other'
cache={i for i,s in enumerate(old['sources']) if any(p.startswith('RTD_CLIENT/resources/UnityCache/Shared/') for p in [s['origin']]+s.get('duplicates',[]))};sources={'旧APK':apk[0]['objects'],'旧缓存':[x for x in old['inventory'] if x['source'] in cache],'新APK':apk[1]['objects'],'新缓存':new['assets']};grouped={}
for label,assets in sources.items():
 g=collections.defaultdict(set)
 for x in assets:
  if x['type'] in ('GameObject','Mesh','Texture2D') and not any(t in x['name'] for t in ('_wait','_atk')):g[family(x['name'])].add((x['type'],x['name']))
 grouped[label]=g
result=[]
for f in sorted({family(x['model']) for x in raw}):
 enemies=[x for x in raw if family(x['model'])==f]
 entry=dict(family=f,models=sorted({x['model'] for x in enemies}),textures=sorted({x['texture'] for x in enemies}-{'na'}),enemy_ids=[x['id'] for x in enemies],current_substitutes=[x for x in policy['bundles'] if family(x['model'])==f],sources={label:sorted(g[f]) for label,g in grouped.items()});result.append(entry)
(r/'docs/resource-audit/全种族四来源审计.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('families',len(result))
for e in result:
 if e['family']!='character_or_other':print(e['family'],len(e['models']),{k:len(v) for k,v in e['sources'].items()})
