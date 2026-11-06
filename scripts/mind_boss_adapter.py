"""Keep spirit artwork, insert identity bear-control hierarchy, and reparent its real head.
The boss's immutable enemy type uses bear clips. Missing anatomical limbs remain unskinned;
real head and hip nodes receive old controls, with an unchanged rest pose and source key values.
"""
import copy,hashlib
from pathlib import Path
import UnityPy
from prepare_monster_recovery import pointers,motion_paths,WS

def adapt(source,output,source_model=None,motion_prefix="ms01_bear",bind_head=False):
 env=UnityPy.load(str(source));objects={o.path_id:o for o in env.objects};root=next(o for o in env.objects if o.type.name=='GameObject' and (o.read_typetree()['m_Name']=='ast_'+source_model if source_model else o.read_typetree()['m_Name'].startswith('ast_ms01_mind')))
 reached=set();todo=[root.path_id]
 while todo:
  i=todo.pop()
  if i in reached:continue
  reached.add(i);todo.extend(p['m_PathID'] for p in pointers(objects[i].read_typetree()) if p['m_PathID'] and not p['m_FileID'])
 transforms={i:o.read_typetree() for i,o in objects.items() if i in reached and o.type.name=='Transform'}
 moves=[i for i,t in transforms.items() if objects[t['m_GameObject']['m_PathID']].read_typetree()['m_Name']=='move']
 if len(moves)!=1:raise ValueError('Ambiguous spirit control root')
 move=moves[0];sf=objects[move].assets_file;next_id=max(objects)+1;added=[];mapping={}
 names={i:o.read_typetree()['m_Name'] for i,o in objects.items() if o.type.name=='GameObject'}
 def paths():
  result={}
  def walk(i,path):
   result[path]=i
   for p in transforms[i]['m_Children']:
    child=p['m_PathID'];name=names[transforms[child]['m_GameObject']['m_PathID']];walk(child,path+'/'+name if path else name)
  walk(move,'');return result
 required=set(motion_paths(motion_prefix))
 for path in list(required):
  parts=path.split('/')
  required.update('/'.join(parts[:i]) for i in range(1,len(parts)))
 for path in sorted(required,key=lambda p:(p.count('/'),p)):
  current=paths()
  if not path or path in current:continue
  parent_path,_,name=path.rpartition('/');parent=current.get(parent_path)
  if parent is None:raise ValueError('Missing parent '+repr((path,parent_path,sorted(current))))
  matches=[(p,i) for p,i in current.items() if p and p.rsplit('/',1)[-1]==name]
  if matches:
   if len(matches)!=1:raise ValueError('Ambiguous matching spirit node')
   old_path,tid=matches[0];old_parent=transforms[tid]['m_Father']['m_PathID'];cursor=parent
   while cursor!=old_parent:
    if cursor not in added:raise ValueError('Reparent would change rest basis')
    cursor=transforms[cursor]['m_Father']['m_PathID']
   transforms[old_parent]['m_Children']=[p for p in transforms[old_parent]['m_Children'] if p['m_PathID']!=tid]
   transforms[parent]['m_Children'].append({'m_FileID':0,'m_PathID':tid});transforms[tid]['m_Father']={'m_FileID':0,'m_PathID':parent}
   mapping[old_path]=path
  else:
   gid=next_id;tid=gid+1;next_id+=2
   template=objects[move];go=copy.copy(objects[transforms[move]['m_GameObject']['m_PathID']]);go.path_id=gid;gt=go.read_typetree();gt['m_Name']=name;gt['m_Component']=[(4,{'m_FileID':0,'m_PathID':tid})];go.save_typetree(gt)
   obj=copy.copy(template);obj.path_id=tid;t=copy.deepcopy(transforms[move]);t.update(m_GameObject={'m_FileID':0,'m_PathID':gid},m_Father={'m_FileID':0,'m_PathID':parent},m_Children=[],m_LocalPosition={'x':0.,'y':0.,'z':0.},m_LocalRotation={'x':0.,'y':0.,'z':0.,'w':1.},m_LocalScale={'x':1.,'y':1.,'z':1.})
   names[gid]=name;objects[gid]=go;objects[tid]=obj;transforms[tid]=t;sf.objects[gid]=go;sf.objects[tid]=obj;added.append(tid);transforms[parent]['m_Children'].append({'m_FileID':0,'m_PathID':tid})
 head_binding=[]
 if bind_head:
  current=paths();main=current['mn_c_main'];head=current['mn_c_main/mn_c_head']
  for i in reached:
   obj=objects[i]
   if obj.type.name!='SkinnedMeshRenderer':continue
   tree=obj.read_typetree()
   if any(p['m_PathID']!=main for p in tree['m_Bones']):raise ValueError('Fish fallback needs verified single main-bone skin')
   for pointer in tree['m_Bones']:pointer['m_PathID']=head
   obj.save_typetree(tree);head_binding.append(i)
  if not head_binding:raise ValueError('No real skin bound to fish head')
 for i,t in transforms.items():objects[i].save_typetree(t)
 changed_curves=0
 for i in reached:
  obj=objects[i]
  if obj.type.name!='AnimationClip':continue
  tree=obj.read_typetree()
  for kind in ('m_RotationCurves','m_CompressedRotationCurves','m_PositionCurves','m_ScaleCurves','m_FloatCurves'):
   for curve in tree.get(kind,[]):
    for old,new in sorted(mapping.items(),key=lambda p:-len(p[0])):
     if curve['path']==old or curve['path'].startswith(old+'/'):
      curve['path']=new+curve['path'][len(old):];changed_curves+=1;break
  obj.save_typetree(tree)
 output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(env.file.save())
 return dict(kind='onepiece-fish-controls-v1' if bind_head else 'mind-boss-bear-controls-v1',head_bound_renderers=head_binding,original_source=str(Path(source).relative_to(WS)),original_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),added_identity_bone_ids=added,reparented_paths=mapping,retargeted_curve_paths=changed_curves,rest_bone_world_matrices_unchanged=True,mesh_bindposes_weights_unchanged=True,source_curve_key_values_unchanged=True,unskinned_anatomical_controls=True)
