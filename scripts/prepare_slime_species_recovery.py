"""Prefer native ordinary and cached metallic slimes; infer only missing levels/palettes."""
import json
from prepare_monster_recovery import ROOT,extract_originals,convert_model
from prepare_species_recovery import polish

def build_slimes():
 raw=json.loads((ROOT/'resources/master-data/ENEMY_UNIT_MASTER.json').read_text())['result'][0]['data_list'];active={}
 for r in raw:
  if r['model'].startswith('ms01_sla_'):active.setdefault(r['model'],set()).add(r['texture'])
 out=ROOT/'resources/reconstructed/species-recovery/ms01_sla';out.mkdir(parents=True,exist_ok=True);(out/'bundles').mkdir(exist_ok=True)
 normal,textures=extract_originals(out/'sources');textures['un']=textures['water'];rows=[]
 for model,requested in sorted(active.items()):
  if model in ('ms01_sla_lv1','ms01_sla_lv1_gold','ms01_sla_lv4_gold'):continue
  if (ROOT/'resources/bundles'/(model+'.unity3d')).exists():continue
  metal=model.endswith(('_silver','_gold'));source_model='ms01_sla_lv4' if metal and 'lv4' in model else 'ms01_sla_lv1';tints={}
  if metal:
   source=ROOT/('resources/bundles/ms01_sla_lv'+('4' if 'lv4' in model else '1')+'_gold.unity3d');jobs={model:source}
  elif '_sh_' in model:source=normal;jobs={model:textures[model.rsplit('_',1)[1]]}
  else:
   source=normal;jobs={model+'_'+a:p for a,p in textures.items() if model+'_'+a in requested}
   if model+'_un' in jobs:tints[model+'_un']='un'
  temp=out/(model+'.unity3d');row=convert_model(source,temp,model,jobs,motion_family='sla');info=polish(temp,out/'bundles'/temp.name,model,source_model,tints,shadow='_sh_' in model)
  row.update(info);row.update(status='validated_candidate',source_model=source_model,inferred=True,reason='Original APK ordinary slime / original cached metallic slime; inferred level scaling and shadow/silver/neutral recolor.')
  rows.append(row);print('Validated',model,'from native slime',flush=True)
  (out/'validation.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 return rows
if __name__=='__main__':build_slimes()
