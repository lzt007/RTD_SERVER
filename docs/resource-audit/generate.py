import sys,json,os,tempfile,csv,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rtd.services.api import API
from rtd.masters.catalog import load_catalog
from rtd.policies.quest_content import SINGLE_QUESTS,layer_quests
root=Path(__file__).resolve().parents[2]
os.environ.update(RTD_EVENT_RECONSTRUCTION='1',RTD_SHINGETSU_RECONSTRUCTION='1')
with tempfile.TemporaryDirectory() as tmp: api=API(Path(tmp)/'audit.sqlite3')
original,_=load_catalog(); enemies={e['id']:e for e in original[20]['data_list']}; effective={e['id']:e for e in api.masters[20]['data_list']}
quests={q['id']:q for q in api.masters[30]['data_list']}; tables={t['id']:t for t in api.masters[21]['data_list']}
ids=(SINGLE_QUESTS|api.event_quests|layer_quests(api)) - api.blocked_quests
assets=json.loads((root/'config/event-reconstruction-assets.json').read_text()); models=set(assets['models']); textures=set(assets['textures']); found={};uses=[]
for qid in sorted(ids):
 if qid not in api.levels or qid not in quests:continue
 q=quests[qid];table=tables[q['enemy_table_id']];slots={b&31 for b in bytes.fromhex(api.levels[qid]['map_data']) if 1<=b&31<=18}
 for slot in ['boss','death']+[f'enemy{s}' for s in sorted(slots)]:
  eid=table[slot+'_set_id'];e=enemies.get(eid,effective.get(eid))
  if not e or e['type'] in (20,21):continue
  for kind,pool in [('model',models),('texture',textures)]:
   name=e.get(kind,'').lower()
   if not name or name=='na' or name in pool or (kind=='model' and 'ast_'+name in pool):continue
   key=(kind,name);found.setdefault(key,[]).append((qid,eid,slot));uses.append([kind,name,qid,q['name'],eid,e['name'],slot,effective[eid].get(kind,'')])
rows=[]
for (kind,name),refs in sorted(found.items()):
 pool=models if kind=='model' else textures; family='_'.join(name.removeprefix('ast_').split('_')[:2]); candidates=sorted({n.removeprefix('ast_') for n in pool if n.removeprefix('ast_').startswith(family+'_')})
 def rank(n):
  level=lambda value: int(re.search(r'_lv(\d+)',value)[1]) if re.search(r'_lv(\d+)',value) else 0
  return (n.split('_')[-1]!=name.split('_')[-1],abs(level(n)-level(name)),-len(os.path.commonprefix([name,n])),n)
 candidates=sorted(candidates,key=rank)
 def describe(n):
  tags=[]
  if kind=='texture':
   tags.append('同属性' if n.split('_')[-1]==name.split('_')[-1] else '异属性')
   a=re.search(r'_lv(\d+)',name);b=re.search(r'_lv(\d+)',n)
   if a and b:tags.append('同等级' if a[1]==b[1] else '等级'+a[1]+'→'+b[1])
  return n+('（'+ '，'.join(tags)+'）' if tags else '')
 candidate_text='；'.join(map(describe,candidates)) or '未找到同族现有候选'

 desc='；'.join(sorted({f"{quests[q]['name']}（{q}）／{enemies.get(e,effective[e])['name']}（{e}）" for q,e,s in refs}))
 current='；'.join(sorted({effective[e].get(kind,'') for q,e,s in refs}))
 part=('整体怪物（含头、躯干及附肢），不是单独贴图部位；中等置信度：model字段' if kind=='model' else '推测为整只怪物的属性配色贴图，可能共用图集覆盖头、躯干及附肢；低置信度：按怪物族/等级/属性命名，无head/body标记，未验证材质绑定')
 rows.append([kind,name,candidate_text,desc,part,'整体模型' if kind=='model' else '敌人换装贴图；具体头/身材质分区待核实', current,'优先评估同族复用；需核对骨骼/UV' if candidates else '优先补绘/补模或人工寻找跨族候选'])
out=Path(__file__).parent
for filename,header,data in [('缺口说明表.csv',['类型','原始引用资源名','近名替换候选（现有资源，按优先级）','引用关卡与怪物','推测部位（含依据及置信度）','用途及部位','当前有效引用','决策参考'],rows),('引用明细.csv',['类型','原始引用','关卡ID','关卡名','敌人ID','敌人名','出场槽位','当前有效引用'],uses)]:
 with (out/filename).open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(header);w.writerows(data)
md=['# 可开放关卡敌人资源缺口','',f'审计范围：{len(ids)} 个主线/已支持活动及已完成修复活动关卡（含层级关卡），排除 blocked_quests；不计尚未修复活动。按修复开关开启后的可开放集合统计，不代表每位玩家当前已解锁或活动已排期。',f'原始引用缺口共 {len(rows)} 项：模型 {sum(r[0]=="model" for r in rows)} 项，贴图 {sum(r[0]=="texture" for r in rows)} 项。','', '缺失判定以 config/event-reconstruction-assets.json 的原始模型和贴图分类清单为依据，包含角色资源；不是仅按文件名判断。未逐个重扫二进制、HTTP依赖及材质槽位，因此本表是主表直接引用缺口，不声称覆盖间接动作/效果/书本依赖。部位无法证实时保留待核实，不能由贴图名武断认定头部。近名替换候选紧随原始引用列，列出同族全部现有资源，优先同属性、再按等级距离排序；异属性和等级差异明确标注。候选未经视觉及UV兼容性验证。当前引用用于揭示已有占位替换，不能据此认为原资源已补齐。','', '完整可筛选数据见同目录 CSV；引用明细保留出场槽位。','','|类型|原始引用|近名替换候选（按优先级）|关卡／怪物|推测部位（依据及置信度）|部位|当前引用|建议|','|---|---|---|---|---|---|---|---|']
md += ['|'+'|'.join(str(v).replace('|','/').replace('\n',' ') for v in r)+'|' for r in rows]
(out/'缺口说明表.md').write_text('\n'.join(md)+'\n')
print(json.dumps({'quests':len(ids),'resources':len(rows),'models':sum(r[0]=='model' for r in rows),'textures':sum(r[0]=='texture' for r in rows),'references':len(uses)},ensure_ascii=False))
