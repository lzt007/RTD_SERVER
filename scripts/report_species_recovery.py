"""Write the per-species evidence/status report from generated manifests and originals."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'resources/reconstructed/species-recovery'
 audit=json.loads((ROOT/'docs/resource-audit/全种族四来源审计.json').read_text())
 installed={r['model']:r for r in json.loads((ROOT/'config/monster-recovery.json').read_text())['bundles']}
 rows=[]
 for species in audit:
  family=species['family']
  if not re.match(r'ms\d+_',family) or family in ('ms00_floor','ms00_wall','ms00_kaidan'):continue
  directory=base/family
  candidates=json.loads((directory/'validation.json').read_text()) if (directory/'validation.json').exists() else []
  failures=json.loads((directory/'failures.json').read_text()) if (directory/'failures.json').exists() else []
  exact=sum(not r.get('inferred',True) for r in candidates)
  rows.append(dict(family=family,requested_models=len(species['models']),validated=len(candidates),exact_artwork_without_inference=exact,inferred=len(candidates)-exact,locally_installed=sum(installed.get(r['model'],{}).get('sha256')==r['sha256'] for r in candidates),cross_species=[r['model'] for r in candidates if r.get('cross_species_fallback')],failures=failures))
 result=dict(policy='原始精确素材优先；种族＞属性＞等级；仅缺失等级的手动替代缩放：lv2=1.3、lv3=1.6、lv4=1.9；染色保留alpha',runtime_verified=False,rows=rows)
 receipt_path=ROOT/'docs/resource-audit/species-deployment-20261104.json'
 receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else None
 if receipt:result['production']={k:v for k,v in receipt.items() if k!='bundles'}
 scale_status_path=ROOT/'docs/resource-audit/level-scale-deployment-20261105.json'
 if scale_status_path.exists():result['level_scale_production']={k:v for k,v in json.loads(scale_status_path.read_text()).items() if k!='bundles'}
 (ROOT/'docs/resource-audit/逐种族修复结果.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 text=['# 逐种族修复结果','','原APK、旧缓存、新APK、新缓存的命名对象检索见全种族四来源审计。已有原始APK内置模型及原优先目录资源保持原样；下表只计新增或重做的兼容包，不把源文件命中当作实机验收。','','仅缺失原模型且手动缩放修补的等级版本使用lv2=1.3、lv3=1.6、lv4=1.9（相对lv1）；原始等级模型保留原大小。缺属性染色保留alpha；影型降低饱和度和明度。原始敌人非外观字段保持原值。','','|家族|客户端模型需求|候选通过|不含推测的精确图稿|含推测|本地接入|构建阻塞|','|---|---:|---:|---:|---:|---:|---:|']
 text += [f"|{r['family']}|{r['requested_models']}|{r['validated']}|{r['exact_artwork_without_inference']}|{r['inferred']}|{r['locally_installed']}|{len(r['failures'])}|" for r in rows]
 text+=['','例外与兼容说明：','','- ms01_fish 四来源未找到同族图稿，采用河豚外观的异族推测；不冒充原鱼类。','- ms03_mind Boss 采用同类精灵；补入旧熊类动作所需控制骨骼，真实头部接入；无皮肤权重的新增四肢控制不代表恢复了原Boss解剖结构。','- 西瓜为单骨骼模型，将真实网格绑定到新增的同静止基准头骨。','- 550狼等级对应未确认，采用330 lv1五属性素材并按缺失等级放大。','- 候选通过代表格式、闭包、像素、骨骼路径等离线检查通过。实机显示、动态表现、通关和资源释放分别待验收；原有通关闪退未在本工作中修复。','','重建：`scripts/prepare_all_species_recovery.py`；验证：`tests/test_species_candidate_bundles.py`；逐族本地接入：`scripts/install_species_recovery.py <family>`。原始资源和其他工作区改动不随此清单自动发布。']
 if receipt:
  text+=['','## 生产发布验证','',f"生产收据记录：{receipt['http_bundles_verified']}个包HTTP哈希一致，{receipt['changed_visual_records']}条外观引用恢复，{receipt['original_resources_preserved']}个原优先资源未改变；发布前{receipt['tests_passed']}项测试通过。备份：`{receipt['backup']}/`。尚无本批实机验收，刷新缓存并重启后复测。收据与当前候选分别保存，新生成候选不自动视为已发布。"]
 scale_receipt_path=ROOT/'docs/resource-audit/level-scale-deployment-20261105.json'
 if scale_receipt_path.exists():
  scaled=json.loads(scale_receipt_path.read_text())
  text+=['',f"后续等级缩放修订（2026-11-05）：仅{scaled['http_bundles_verified']}个缺失等级手动替代包调整为1.3/1.6/1.9，并完成生产HTTP哈希核对。原始模型与其余兼容包保持原样。见等级缩放调整-20261105.md。"]
 (ROOT/'docs/resource-audit/逐种族修复结果.md').write_text('\n'.join(text)+'\n')
 print(json.dumps(dict(families=len(rows),validated=sum(r['validated'] for r in rows),installed=sum(r['locally_installed'] for r in rows),blocked=sum(len(r['failures']) for r in rows)),ensure_ascii=False))
if __name__=='__main__':main()
