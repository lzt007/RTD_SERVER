"""Inferred squirrel variants from original APK. Never alters original assets."""
import copy,hashlib,json,struct
from pathlib import Path
from PIL import Image,ImageEnhance
from prepare_monster_recovery import ROOT,extract_originals,convert_model,pointers
from prepare_wolf_closed_bundle import rebuild
POLICY='squirrel-original-lv1-scale-v2'
def visual_scale(model):
 return {'ms01_squ_lv2':1.3,'ms01_squ_lv3':1.6,'ms01_squ_lv4':1.9}.get(model,1.0)
def shadow_image(image):
 alpha=image.getchannel('A');result=ImageEnhance.Brightness(ImageEnhance.Color(image).enhance(.45)).enhance(.65);result.putalpha(alpha);return result

def build(only=None):
 import UnityPy
 out=ROOT/'resources/reconstructed/squirrel-recovery';out.mkdir(parents=True,exist_ok=True)
 normal,textures=extract_originals(out/'sources',family='squ')
 # Explicit inferred neutral palette; source attribute does not change gameplay.
 textures['un']=textures['water']
 rows=json.loads((out/"validation.json").read_text()) if only and (out/"validation.json").exists() else []
 rows=[r for r in rows if r["model"] not in (only or [])]
 for model in ['ms01_squ_lv2','ms01_squ_lv3','ms01_squ_lv4']+['ms01_squ_sh_'+a for a in ('fire','water','holy','dark')]:
  if only and model not in only:continue
  if (ROOT/'resources/bundles'/(model+'.unity3d')).exists():raise ValueError('Original exists '+model)
  attrs=[model.rsplit('_',1)[1]] if '_sh_' in model else list(textures)
  jobs={model if '_sh_' in model else model+'_'+a:textures[a] for a in attrs}
  path=out/(model+'.unity3d');row=convert_model(normal,path,model,jobs,motion_family='squ')
  env=UnityPy.load(str(path));objects={o.path_id:o for o in env.objects};ab=next(o for o in env.objects if o.type.name=='AssetBundle').read_typetree()
  root=next(v['asset']['m_PathID'] for n,v in ab['m_Container'] if n=='ast_'+model)
  root_tree=objects[root].read_typetree();transform=next(p['m_PathID'] for _,p in root_tree['m_Component'] if objects[p['m_PathID']].type.name=='Transform')
  t=objects[transform].read_typetree();t['m_LocalScale']={k:v*visual_scale(model) for k,v in t['m_LocalScale'].items()};objects[transform].save_typetree(t)
  if '_sh_' in model:
   texture_id=next(o.path_id for o in env.objects if o.type.name=='Texture2D' and o.read_typetree()['m_Name']==model)
   for material in env.objects:
    if material.type.name!='Material':continue
    t=material.read_typetree()
    for key,value in t['m_SavedProperties']['m_TexEnvs']:
     if key['name']=='_MainTex':value['m_Texture']={'m_FileID':0,'m_PathID':texture_id}
    material.save_typetree(t)
  expected={}
  for o in env.objects:
   if o.type.name=='GameObject':
    t=o.read_typetree();t['m_IsActive']=0;o.save_typetree(t)
   if o.type.name!='Texture2D':continue
   t=o.read_typetree();name=t['m_Name'];im=o.read().image.convert('RGBA')
   if '_sh_' in model:im=shadow_image(im)
   elif name.endswith('_un'):
    alpha=im.getchannel('A');im=im.convert('L').convert('RGBA');im.putalpha(alpha)
   expected[name]=im.tobytes();t['image data']=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes();o.save_typetree(t)
  path.write_bytes(env.file.save())
  final=out/'bundles'/path.name;info=rebuild(path,final,policy=POLICY)
  check=UnityPy.load(str(final));missing=[]
  ids={o.path_id for o in check.objects}
  for o in check.objects:
   for p in pointers(o.read_typetree()):
    if p['m_PathID'] and (p['m_FileID'] or p['m_PathID'] not in ids):missing.append(p)
   if o.type.name=='Texture2D' and o.read().image.convert('RGBA').tobytes()!=expected[o.read_typetree()['m_Name']]:raise ValueError('Pixels changed')
   if o.type.name=='GameObject' and o.read_typetree()['m_IsActive']!=0:raise ValueError('Activation mismatch')
  if missing:raise ValueError('Dependencies missing')
  row.update(info);row.update(inferred=True,reason='Original APK Lv1 squirrel; inferred level scale/shadow or neutral recolor.',visual_scale=visual_scale(model),shadow_saturation=.45 if '_sh_' in model else None,shadow_brightness=.65 if '_sh_' in model else None,activation_flag=0,missing_pointers=[],texture_roundtrip=True,runtime_verified=False)
  rows.append(row);print('Built',model,flush=True)
 (out/'validation.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 return rows
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--shadows-only',action='store_true');args=p.parse_args()
 build(['ms01_squ_sh_'+a for a in ('fire','water','holy','dark')] if args.shadows_only else None)
