from pathlib import Path
import runpy,json,csv
from collections import defaultdict,Counter
p=Path(__file__).parent;g=runpy.run_path(str(p/'generate.py'));api=g['api'];original=g['enemies'];effective=g['effective'];uses=defaultdict(set)
for qid in g['ids']:
 if qid not in api.levels or qid not in g['quests']:continue
 q=g['quests'][qid];t=g['tables'][q['enemy_table_id']];slots={b&31 for b in bytes.fromhex(api.levels[qid]['map_data']) if 1<=b&31<=18}
 for slot in ['boss','death']+[f'enemy{s}' for s in slots]:uses[t[slot+'_set_id']].add(qid)
evidence=json.loads((g['root']/'config/event-reconstruction-motion-evidence.json').read_text());assets=g['assets'];deps={r['enemy_id']:r for r in assets['character_dependencies']};effects={r['effect_id']:r for r in evidence['attack_effects']['effects']};rows=[]
def add(kind,name,status,eid,note):
 e=original.get(eid,effective[eid]);rows.append([kind,name,status,eid,e['name'],'；'.join(f"{qid} {g['quests'][qid]['name']}" for qid in sorted(uses[eid])),note])
for eid in sorted(uses):
 e=original.get(eid,effective.get(eid))
 if not e:continue
 if e['type'] in evidence['attack_effects']['unit_enemy_types']:
  d=deps.get(eid)
  if d:
   add('角色分组包',d['bundle'],'存在' if d['bundle_present'] else '本地缺失',eid,'依据角色分组资源清单；未验证HTTP加载')
   book=f"ms00_book_el_{d['book_color']:02}"
   present=book in assets['models'] or 'ast_'+book in assets['models']
   overlay=g['root']/'resources/reconstructed/events/bundles'/(book+'.unity3d')
   add('地图书本',book,'原始模型存在' if present else '原始缺失（有重建包）' if overlay.is_file() else '原始缺失',eid,'chara_symbol选择的书本；重建不能当作原始资源齐全')
  else:add('角色依赖','角色分组包/地图书本','待核实',eid,'该角色敌人未在已有依赖清单中')
 else:
  effect=effects.get(e['atk_ef_id'])
  if effect:
   for r in effect['resources']:
    add('攻击效果',r['path'],'代码跳过加载' if r['load_skipped_by_code'] else '原始对象存在' if r['objects'] else '未发现原始对象',eid,'依据原客户端EnemyAttackEffectAssign与APK对象证据')
  else:add('攻击效果',str(e['atk_ef_id']),'待核实',eid,'已有攻击效果映射没有覆盖此ID')
# 动作证据对所有清单项复核，不将未建立关卡映射的动作宣称为确定关卡缺口。
for r in evidence['motions']['motions']+evidence['motions']['direction_clips']:
 if not r['apk_present']:rows.append(['动作',r['path'],'待核实关卡可达性','','','尚未建立逐敌人动作索引映射','原始对象未发现；'+evidence['fish_motion']['reason'] if 'fish' in r['name'] else '未建立逐敌人动作索引映射，不能直接计入关卡缺口'])
with (p/'间接依赖核对表.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['依赖类别','原始资源引用','状态','敌人ID','敌人名称','可开放关卡','依据与限制']);w.writerows(rows)
counts=Counter(r[2] for r in rows);missing={(r[0],r[1]) for r in rows if '缺失' in r[2]}
md=['# 补充核对说明','',f'直接引用缺口209项已全部归入18个名称族；原分类遗漏的75项非lv引用现已纳入。', '',f'间接依赖表共{len(rows)}条敌人/资源关联；其中明确标为缺失的去重引用{len(missing)}项。状态统计：'+str(dict(counts)),'','缺失引用：']+[f'- {a}：{b}' for a,b in sorted(missing)]+['','动作、攻击效果采用 config/event-reconstruction-motion-evidence.json 的原客户端解析证据。存在的原始对象不会列为缺失。动作尚未全部建立逐关卡索引映射，未证明可达的动作单列待核实，不能把整个客户端动作清单算入这些关卡。角色武器/技能效果的递归依赖与实际HTTP响应尚未全面核实，因此本报告仍不宣称间接依赖已穷尽。','', '入口：','- 怪物资源分类图鉴.html：全部名称族与已有贴图','- 缺口说明表.csv：209项原始直接引用缺口','- 间接依赖核对表.csv：关卡、敌人、依赖状态和依据']
(p/'补充核对说明.md').write_text('\n'.join(md)+'\n');print(dict(rows=len(rows),missing_unique=len(missing),status=dict(counts)))
