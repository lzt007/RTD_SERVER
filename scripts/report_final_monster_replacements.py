"""Read-only production audit; write full model and enemy/texture replacement reports."""
import collections,csv,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PRODUCTION=Path('/home/RTD_SERVER')
OUT=ROOT/'docs/resource-audit'
LABELS={'ms00_death':'Death类','ms01_akb':'AKB联动龙','ms01_bd':'BD联动小怪（golem/kap/man分开）','ms03_bd':'BD联动Boss','ms01_bear':'熊','ms01_bee':'蜂','ms01_bird':'鸟','ms01_crab':'蟹','ms01_dra':'小龙','ms01_fish':'鱼（无同族图稿）','ms01_fly':'普通飞行怪','ms01_fugu':'河豚','ms01_golem':'石像/魔像','ms01_kame':'龟','ms01_mind':'Mind灵体系','ms01_neko':'猫','ms01_pumpkin':'南瓜','ms01_sco':'蝎子','ms01_sen':'sen联动小怪（cat/drome/sheep分开）','ms01_sla':'史莱姆','ms01_slawing':'带翼史莱姆','ms01_squ':'松鼠','ms01_sr':'SR联动小怪（lev/yan分开）','ms01_suika':'西瓜','ms01_tatu':'犰狳类','ms01_wolf':'狼','ms02_dra':'二足龙Boss','ms02_four':'四足兽/巴哈姆顿系Boss','ms03_akb':'AKB大型龙Boss','ms03_dra':'大型二足龙Boss','ms03_fly':'飞龙/维弗尔Boss','ms03_four':'法夫尼尔等四足Boss','ms03_kra':'kra Boss','ms03_mind':'Mind Boss','ms03_oct':'章鱼Boss','ms03_sea':'海洋Boss','ms03_sen':'sen联动Boss','ms03_sr':'SR联动Boss','ms04_dra':'分段巨龙（头/翼/尾）','ms04_legend':'达哈卡/机械巨龙系','ms05_ryu':'神龙'}
def family(name):
 m=re.search(r'ms\d+_[^_]+',name);return m[0] if m else ''
def lineage(name):
 f=family(name)
 if f in ('ms01_mind','ms03_mind'):return 'mind'
 if f=='ms04_dra' or f.endswith(('_bd','_sen','_sr')):return f+'_'+name.split(f+'_')[-1].split('_')[0]
 return f
def mesh_source(row):
 source=row['source'];stem=Path(source).stem
 # Metallic slime provenance must follow the real file, not the generic rig label.
 if 'ms01_sla_lv' in stem and stem.endswith('_gold'):return stem
 if 'original-squ-lv1' in stem:return 'ms01_squ_lv1'
 if 'original-sla-lv1' in stem:return 'ms01_sla_lv1'
 return row.get('source_model') or stem

def origin(path):
 if '/resources/unpacked/' in '/'+path:return '新缓存'
 if '/squirrel-recovery/sources/' in '/'+path or '/ms01_sla/sources/' in '/'+path:return '旧APK提取'
 if '/resources/bundles/' in '/'+path:return '原优先目录原包'
 return '适配中间包（原来源见骨骼证据）'
def esc(value):return str(value).replace('|','／').replace('\n',' ').replace('\r',' ')
def main():
 manifest_path=PRODUCTION/'config/monster-recovery.json';manifest=json.loads(manifest_path.read_text());raw=json.loads((ROOT/'resources/master-data/ENEMY_UNIT_MASTER.json').read_text())['result'][0]['data_list'];by_model=collections.defaultdict(list)
 for e in raw:by_model[e['model']].append(e)
 records=[];groups=collections.defaultdict(list)
 for row in manifest['bundles']:
  assert hashlib.sha256((PRODUCTION/'resources/reconstructed/monsters/bundles'/row['bundle']).read_bytes()).hexdigest()==row['sha256'],row['model']
  model=row['model'];source=mesh_source(row);cross=lineage(model)!=lineage(source)
  assert cross==bool(row.get('cross_species_fallback')),('Unclassified species mismatch',model,source)
  textures=[];tints=row.get('recolored_textures') or {}
  for target,evidence in row['textures'].items():
   source_name=(row.get('texture_source_names') or {}).get(target) or (row.get('texture_source_models') or {}).get(target) or Path(evidence['source']).stem
   tint=tints.get(target)
   if model.startswith('ms01_squ_') and target.endswith('_un'):tint='un（原水图灰度化）'
   if '_silver' in model and source.endswith('_gold'):tint='silver（金图灰度化）'
   textures.append(dict(target=target,source_name=source_name,source_file=evidence['source'],source_origin=origin(evidence['source']),recolor=tint))
  shadow=bool(row.get('shadow_recolor') or row.get('shadow_saturation') is not None)
  methods=['异族河豚替代（缺鱼类图稿）' if cross else '同名模型图稿' if source==model else '同族异模型复用']
  scale=row.get('visual_scale',1.)
  if scale!=1:methods.append(f'手动等级缩放×{scale:g}')
  elif source!=model:methods.append('保持来源模型原尺寸')
  tinted=[t['target'] for t in textures if t['recolor']]
  if tinted:methods.append('缺属性/银色推测染色（见贴图表）')
  if shadow:methods.append('普通同属性图降饱和度0.45、明度0.65，保留alpha')
  if '_sh_' in model and source==model and not shadow:methods.append('原始影型，未额外压暗')
  adaptations=row.get('skeleton_adaptations') or []
  for adaptation in adaptations:
   kind=adaptation.get('kind') or ('尾骨重命名 '+adaptation['before']+'→'+adaptation['after']+'（ID/静止变换/权重不变）' if 'before' in adaptation and 'after' in adaptation else '其他骨骼适配')
   methods.append({'mind-boss-bear-controls-v1':'精灵头部接入旧熊型动作控制，新增四肢控制无蒙皮','onepiece-fish-controls-v1':'河豚真实网格绑定旧鱼类头部控制','suika-real-head-binding-v1':'新增同静止基准头骨并绑定真实网格'}.get(kind,kind))
  source_file=next((a['original_source'] for a in adaptations if a.get('original_source')),row['source'])
  record=dict(model=model,family=family(model),label=LABELS.get(family(model),family(model)),mesh_source=source,mesh_source_file=source_file,source_origin=origin(source_file),cross_species=cross,visual_scale=scale,methods=methods,textures=textures,enemy_records=[{k:e[k] for k in ('id','name','model','texture','attribute','type')} for e in by_model[model]],bundle_sha256=row['sha256'],runtime_verified=False)
  records.append(record);groups[record['family']].append(record)
 native_scan=json.loads((OUT/'全种族APK内置扫描.json').read_text());native={o['name'].removeprefix('ast_') for o in native_scan[0]['objects'] if o['type']=='GameObject'}
 published={r['model'] for r in records};preserved=[];utilities={'ms00_floor','ms00_wall','ms00_kaidan'}
 for model in sorted(by_model):
  if not family(model) or family(model) in utilities or model in published:continue
  canonical=(PRODUCTION/'resources/bundles'/(model+'.unity3d')).exists()
  assert canonical or model in native,('Uncovered creature model',model)
  preserved.append(dict(model=model,route='原优先目录原包' if canonical else '旧APK内置',enemy_records=[{k:e[k] for k in ('id','name','texture')} for e in by_model[model]]))
 no_species=[r for r in records if r['cross_species']]
 fish_audit=next(r for r in json.loads((OUT/'全种族四来源审计.json').read_text()) if r['family']=='ms01_fish');assert all(not v for v in fish_audit['sources'].values())
 counts=dict(published_bundles=len(records),families=len(groups),named_same_model=sum(r['mesh_source']==r['model'] for r in records),same_lineage_reuse=sum(not r['cross_species'] and r['mesh_source']!=r['model'] for r in records),cross_species=len(no_species),scaled=sum(r['visual_scale']!=1 for r in records),recolored=sum(any(t['recolor'] for t in r['textures']) for r in records),derived_shadows=sum('普通同属性图' in ';'.join(r['methods']) for r in records),preserved_original_models=len(preserved),non_ms_models_audited_separately=len({r['model'] for r in raw if not family(r['model'])}))
 result=dict(date='2026-11-05',scope='当前生产普通怪物/模型式Boss兼容清单；不等于全部角色型敌人资源审计',production_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),counts=counts,missing_same_species=no_species,models=records,preserved_originals=preserved)
 unit_audit=json.loads((OUT/'角色型敌人加载审计.json').read_text())
 result['character_enemy_audit']={k:unit_audit[k] for k in ('enemy_records','distinct_models','distinct_non_ms_models','bundle_count','http_verified','statuses')}
 result['character_enemy_audit']['report']='角色型敌人加载审计.json'
 (OUT/'最终敌人替换报告.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 with (OUT/'最终敌人替换明细.csv').open('w',encoding='utf-8-sig',newline='') as stream:
  writer=csv.writer(stream,lineterminator="\n");writer.writerow(['敌人ID','敌人原名','原需求模型','原需求贴图','采用网格','网格原来源','贴图来源对象','贴图原文件','处理方案','倍率','异族替代','生产包SHA256'])
  for record in records:
   for enemy in record['enemy_records']:
    texture=next((t for t in record['textures'] if t['target']==enemy['texture']),None)
    if texture is None and enemy['texture']=='na':texture=next((t for t in record['textures'] if t['target']==record['model']),None)
    writer.writerow([enemy['id'],enemy['name'],record['model'],enemy['texture'],record['mesh_source'],record['mesh_source_file'],texture['source_name'] if texture else '',texture['source_file'] if texture else '', '；'.join(record['methods']),record['visual_scale'],'是' if record['cross_species'] else '否',record['bundle_sha256']])
 lines=['# 最终敌人替换报告（当前生产）','','日期：2026-11-05。读取生产清单并核对全部包文件SHA256后生成。278包清单涵盖普通怪物及模型式Boss；角色型敌人按原IsUnitEnemy加载类型另附审计，不按ms前缀排除。','','## 结论','',f"生产共{len(records)}包、{len(groups)}个模型家族：{counts['named_same_model']}个采用同名模型图稿，{counts['same_lineage_reuse']}个同族异模型复用，{counts['cross_species']}个异族替代。分类按实际几何来源名称及子类匹配；同名图稿仍可能需要补属性，并不等于整个包未经推测。",'',f"手动等级放大{counts['scaled']}包；涉及推测染色{counts['recolored']}包；从普通型派生影型{counts['derived_shadows']}包。上述处理可重叠，不能相加作为总数。另有{len(preserved)}个本来可用的原始模型未替换。",'','只有缺失原模型且需要手工放大的等级版本采用Lv2=1.3、Lv3=1.6、Lv4=1.9（相对来源Lv1）。原始等级模型保留原尺寸。','','## 没有同族图稿的条目','','四来源命名对象审计中，ms01_fish未找到可用同族模型/贴图，目前5项全部使用河豚。其余本轮生产条目没有明确跨族映射；同族不同变体的替代仍单独标记。','','|敌人ID / 原名|原模型|采用模型|补色|','|---|---|---|---|']
 for r in no_species:
  enemy=r['enemy_records'][0];lines.append('|'+ '|'.join(map(esc,[str(enemy['id'])+' '+enemy['name'],r['model'],r['mesh_source'],'；'.join(str(t['recolor']) for t in r['textures'] if t['recolor']) or '使用原属性图']))+'|')
 lines+=['','鱼类是异族水生替代，不是找回原鱼类；新增控制骨骼只保证旧动作有绑定目标，不代表恢复原鱼类鳍/下颌的完整真实动作。','','## 逐族概览','','下表计生产包，不是敌人记录数；同一个包可供多个敌人ID和属性使用。','','|种族 / 家族|包数|实际使用的网格来源|处理|','|---|---:|---|---|']
 for f,rs in sorted(groups.items()):
  sources=sorted({r['mesh_source'] for r in rs});actions=[]
  if any(r['mesh_source']==r['model'] for r in rs):actions.append('含同名图稿')
  if any(not r['cross_species'] and r['mesh_source']!=r['model'] for r in rs):actions.append('含同族复用')
  if any(r['cross_species'] for r in rs):actions.append('异族')
  if any(r['visual_scale']!=1 for r in rs):actions.append('缺等级放大')
  if any(any(t['recolor'] for t in r['textures']) for r in rs):actions.append('补色')
  if any('普通同属性图' in ';'.join(r['methods']) for r in rs):actions.append('派生影型')
  lines.append('|'+ '|'.join(map(esc,[LABELS.get(f,f)+' / '+f,len(rs),'、'.join(sources),'；'.join(actions)]))+'|')
 lines+=['','## 重点说明','','- 蝎子已无“没有蝎子素材”的缺口：使用四属性ms01_sco_*_02，缺无属性用染色；Lv2/3/4是手动等级替代，影型由对应属性普通型派生。','- 狼使用330系列Lv1模型及对应属性原图；骨架来源可能统一为暗型，但火、水、光、暗、无属性贴图分别选择，不是全部染成暗狼。550系列等级关系未确认，未当作真实Lv3。','- 松鼠使用旧APK Lv1网格与四属性原图；缺无属性由水图灰度化；高等级放大、影型降饱和度/明度。','- 史莱姆普通型用旧APK模型；金属型使用原金史莱姆Lv1/Lv4实际包。银色为金图灰度化。清单source_model的通用骨架标签会省略gold，本报告已按真实源文件纠正显示。原金Lv4及据其派生的银Lv4不被强行放大。','- 熊和小龙的已找到等级/影型原图直接使用，不能把它们都算作Lv1放大。','- Mind Boss=ms03_mind_01使用普通暗Mind，推测无属性染色并增加旧熊型动作控制；这不是原Boss几何。','- 分段巨龙：头用330火头染无属性，尾/翼使用各自同名原图；绝不互换身体部件。头部同名源包和610无属性源包仍有未验证shader，不冒充精确恢复。','- 达哈卡01/02/樱花型复用330暗型并推测无属性配色；03用同名素材。樱花型没有恢复专属樱花图稿。神龙用330光型染无属性，未恢复原01专属图稿。','- 11011水巴哈姆顿使用590_ms02_four_w_01；20020红维弗尔使用230_ms03_fly_lv1_f_01，均为同族属性素材复用。','','## 保留原始资源而未替换的模型','','|模型|加载来源|原敌人名称举例|','|---|---|---|']
 for r in preserved:lines.append('|'+ '|'.join(map(esc,[r['model'],r['route'],'、'.join(dict.fromkeys(e['name'] for e in r['enemy_records']))]))+'|')
 lines+=['','## 逐模型替换与贴图明细','','下面逐一列出278包。完整敌人ID/名称及其实际贴图映射另见同目录CSV；JSON保留每项来源路径、SHA及全部敌人记录。CSV关联原始主表全部引用，不表示823条记录都已开放或逐一实机验收。']
 for f,rs in sorted(groups.items()):
  lines+=['','### '+LABELS.get(f,f)+' / '+f,'','|原需求模型|敌人原名举例|采用网格|实际处理|','|---|---|---|---|']
  for r in rs:
   names=list(dict.fromkeys(e['name'] for e in r['enemy_records']));sample='、'.join(names[:2])+(' 等'+str(len(r['enemy_records']))+'条敌人记录' if len(r['enemy_records'])>2 else '')
   lines.append('|'+ '|'.join(map(esc,[r['model'],sample,r['mesh_source'],'；'.join(r['methods'])]))+'|')
  lines+=['','贴图映射：','','|目标贴图|真实来源对象/文件|处理|','|---|---|---|']
  seen=set()
  for r in rs:
   for t in r['textures']:
    key=(t['target'],t['source_name'],str(t['recolor']))
    if key in seen:continue
    seen.add(key);shadow='；普通图降饱和度/明度' if '普通同属性图' in ';'.join(r['methods']) else ''
    lines.append('|'+ '|'.join(map(esc,[t['target'],t['source_name']+'（'+t['source_origin']+'）',('染色→'+str(t['recolor']) if t['recolor'] else '原图')+shadow]))+'|')
 lines+=['','## 验证范围和未覆盖范围','','当前278包文件哈希与生产清单一致；最近等级修订31项测试通过，17包HTTP哈希核对通过。原始敌人属性、等级、战斗数值、掉落、地图和开放条件未改。','','清单、骨架路径及离线包验证不等于Android实机逐项验收；通关闪退未在本工作中修复。',f"另附角色型敌人审计：{unit_audit['enemy_records']}条记录、{unit_audit['distinct_models']}个模型，其中{unit_audit['distinct_non_ms_models']}个不带ms。角色/直接模型/书本{unit_audit['bundle_count']}包，{unit_audit['http_verified']}包生产HTTP哈希匹配。非ms不是排除条件；逐条导出及根Animation见《角色型敌人加载审计》，Boss原图稿缺口见《Boss资源缺口复核》。这仍不等于全动作和Android实机验收。",'','生产清单SHA256：`'+result['production_manifest_sha256']+'`。']
 (OUT/'最终敌人替换报告.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps(counts,ensure_ascii=False))
if __name__=='__main__':main()
