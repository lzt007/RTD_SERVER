"""Derive enemy bundle requests from freshly inspected original client loading rules."""
from pathlib import Path
import os,sys,tempfile,json,csv,collections
p=Path(__file__).parent;root=p.parents[1];sys.path.insert(0,str(root))
from rtd.services.api import API
from rtd.masters.catalog import load_catalog
from rtd.policies.quest_content import SINGLE_QUESTS,layer_quests
os.environ.update(RTD_EVENT_RECONSTRUCTION='1',RTD_SHINGETSU_RECONSTRUCTION='1')
with tempfile.TemporaryDirectory() as d:api=API(Path(d)/'audit.sqlite3')
masters,_=load_catalog();orig={e['id']:e for e in masters[20]['data_list']};effective={e['id']:e for e in api.masters[20]['data_list']};quests={q['id']:q for q in api.masters[30]['data_list']};tables={t['id']:t for t in api.masters[21]['data_list']}
local=set();unit=set();defs={}
for line in (p/'原客户端加载定义.tsv').read_text().splitlines():
 r=line.split('\t')
 if r[0]=='B':defs[r[1]]=(int(r[2]),r[3]+'/'+r[1]+'.unity3d')
 if r[0]=='L':local.add(r[1])
 if r[0]=='U':unit.add(int(r[1]))
x=json.loads((p/'独立资源重扫证据.json').read_text());index=collections.defaultdict(list)
for o in x['inventory']:index[o['name'].lower(),o['type']].append(o)
apkpaths={r['path'].lower() for r in x['resource_entries']}
ids=(SINGLE_QUESTS|api.event_quests|layer_quests(api))-api.blocked_quests;rows=[]
for qid in sorted(ids):
 if qid not in quests:continue
 q=quests[qid];t=tables[q['enemy_table_id']]
 # Actual EnemyArrangeTable ctor takes ALL 18 enemy slots + boss/death, not just map cells.
 eids={v for k,v in t.items() if k.endswith('_set_id') and v}
 for eid in sorted(eids):
  for scope,es in [('原始引用',orig),('当前修复配置',effective)]:
   e=es.get(eid,effective.get(eid))
   if not e:continue
   model=e['model'];isunit=e['type'] in unit;book='ms00_book_el_0'+str(e['chara_symbol']-9 if 10<=e['chara_symbol']<=15 else 6)
   bundles=[] if model in local else [book if isunit else model]
   if isunit and e['chara_g_id']<=0 and model not in local:bundles.append(model)
   if isunit and e['chara_g_id']>0:
    start=((e['chara_g_id']-1)//10)*10+1;bundles.append(f'{start}-{start+9}')
   if not bundles:bundles=[None]
   for b in sorted(set(bundles),key=lambda b:b or ''):
    if b is None:
     status='APK Resources路径有绑定' if ('prefab/enemies/'+model).lower() in apkpaths else 'APK预期本地资源但未找到路径绑定';path='Prefab/Enemies/'+model;version='';sources=''
    else:
     version,path=defs.get(b,('', '未在原客户端包定义找到：'+b))
     hits=index.get(('ast_'+b.lower(),'GameObject'),[])
     if isunit and b!=book:hits+=index.get((model.lower(),'GameObject'),[])
     sources='；'.join(sorted({x['sources'][o['source']]['origin'] for o in hits}))
     status='找到包内对象，缓存URL/版本命中待实机验证' if hits else '未在当前本地内容找到预期包内对象'
     # Do not equate arbitrary same-name object with a validated cache hit.
    rows.append([scope,qid,q['name'],eid,e['name'],model,e.get('texture',''),b or 'APK本地',version,path,status,sources])
with (p/'按客户端加载链推导的需求.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['引用口径','关卡ID','关卡名','敌人ID','敌人名','模型','贴图','所需包','版本号','原始相对下载路径或Resources路径','本地证据状态','对象来源']);w.writerows(rows)
print(dict(quests=len(ids),rows=len(rows),status=dict(collections.Counter(r[10] for r in rows))))
